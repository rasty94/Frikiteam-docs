---
title: "Backup de Kubernetes: Velero y snapshots de etcd"
description: "Proteger un clúster Kubernetes propio: qué copiar y qué no con GitOps, snapshots de etcd (kubeadm y k3s), Velero con MinIO, volúmenes por snapshot CSI o File System Backup, hooks de consistencia y prueba de restauración."
keywords: "kubernetes, backup, velero, etcd, etcdctl, k3s, minio, csi, snapshot, kopia, restic, gitops, restauración"
tags: ['kubernetes', 'backups', 'storage']
updated: 2026-10-11
difficulty: advanced
estimated_time: 32 min
category: Copias de Seguridad
status: published
last_reviewed: 2026-10-11
prerequisites:
  - "Un clúster Kubernetes (kubeadm, k3s u otro) y acceso con kubectl"
  - "[Estrategia de Backup 3-2-1](strategy_321.md)"
  - "Un almacenamiento compatible con S3 (MinIO u otro) fuera del clúster"
reviewers: ["@rasty94"]
contributors: ["@rasty94"]
---

# Backup de Kubernetes: Velero y snapshots de etcd

## El problema

Un clúster parece fácil de respaldar porque "todo es YAML". Entonces falla el único nodo de control, o alguien ejecuta `kubectl delete namespace` en el contexto equivocado, y descubres que el YAML que tenías no es todo lo que había: faltaban los Secrets que nunca pasaron por Git, los datos de las bases de datos que viven en volúmenes persistentes, los certificados que emitió cert-manager y el estado de los objetos que creó un operador. Y descubres también que tus backups de VMs con [PBS](pbs.md) copian el disco del nodo, no la intención del clúster: restaurar un nodo de control de hace tres días en un clúster de tres nodos que ha seguido vivo produce un etcd que contradice al resto.

Un clúster tiene tres capas con riesgos y herramientas distintas: el **estado de la API** (objetos guardados en etcd), los **datos de los volúmenes** y la **configuración que reconstruye el clúster** (certificados, tokens, manifiestos del plano de control). Esta página explica cómo proteger cada una con snapshots de etcd y Velero, y cómo encaja el resultado en una [estrategia 3-2-1](strategy_321.md).

!!! note "Qué cubre y qué no"
    Aquí se trata el **backup y la restauración del clúster**. Qué es un driver CSI y cómo se crean StorageClasses está en [Kubernetes CSI](../storage/kubernetes_csi.md); el modelo de objetos de Kubernetes, en [Kubernetes base](../kubernetes/kubernetes_base.md). La lógica de copias, medios y ubicación no se repite: está en [Estrategia de Backup 3-2-1](strategy_321.md), y el cifrado e inmutabilidad del destino en [Backup Seguro](../cybersecurity/backup_seguro.md).

## 📋 Tabla de Contenidos

- [Qué hay que proteger](#que-hay-que-proteger)
- [Snapshots de etcd](#snapshots-de-etcd)
- [etcd en k3s](#etcd-en-k3s)
- [Velero: arquitectura](#velero-arquitectura)
- [Instalar Velero con MinIO](#instalar-velero-con-minio)
- [Backups, schedules y restauración](#backups-schedules-y-restauracion)
- [Volúmenes: snapshots CSI o copia de ficheros](#volumenes-snapshots-csi-o-copia-de-ficheros)
- [Consistencia: hooks pre y post](#consistencia-hooks-pre-y-post)
- [Probar la restauración](#probar-la-restauracion)
- [Encaje con la regla 3-2-1](#encaje-con-la-regla-3-2-1)
- [Troubleshooting](#troubleshooting)
- [Buenas prácticas](#buenas-practicas)
- [Referencias](#referencias)

## Qué hay que proteger

| Capa | Dónde vive | Cómo se protege |
|---|---|---|
| Objetos de la API (Deployments, Services, ConfigMaps, CRDs, RBAC) | etcd | Git si usas GitOps; snapshot de etcd o Velero en caso contrario |
| Secrets | etcd, y en Git solo si están cifrados | Ver el matiz más abajo |
| Datos de volúmenes persistentes | El backend de almacenamiento (Ceph, NFS, discos locales) | Velero con snapshots CSI o File System Backup; backup nativo de la base de datos |
| PKI, tokens y configuración del plano de control | Disco de los nodos de control (`/etc/kubernetes/pki` en kubeadm) | Copia de ficheros con [restic o Borg](restic_borg.md) |
| Los propios nodos | Discos de las VMs o máquinas | Opcional: se reinstalan; es más barato reconstruir que restaurar |

### Qué no hace falta copiar con GitOps

Si el clúster se gestiona con [Argo CD](../cicd/argocd.md) o similar, los Deployments, Services, Ingress y ConfigMaps ya están en Git, que es mejor backup que cualquier snapshot: tiene historial, revisión y vive fuera del clúster. Reconstruir es instalar el clúster vacío, instalar Argo CD y dejar que sincronice. Eso te ahorra copiar casi todo el estado de la API, pero **no te ahorra tres cosas**:

1. **Los datos.** Git guarda el manifiesto del `StatefulSet` de PostgreSQL, no sus tablas. Los volúmenes siguen necesitando backup.
2. **Los Secrets.** Si los Secrets están en el clúster y nunca en Git, se pierden con él. Si usas SOPS o Sealed Secrets, lo que hay que respaldar fuera del clúster es la **clave de descifrado** (clave age o clave privada del controlador): sin ella, los ficheros cifrados de Git son irrecuperables. Ver [Secretos en GitOps](../cybersecurity/secrets_gitops.md).
3. **El estado generado.** Certificados emitidos por cert-manager (se reemiten, pero con límites de tasa de Let's Encrypt), recursos que crea un operador (la base de datos que un operador levanta a partir de un CR) y objetos creados a mano con `kubectl apply` que nunca llegaron a Git.

!!! warning "Un snapshot de etcd contiene los Secrets"
    Sin cifrado de Secrets en reposo configurado en la API, los Secrets están en etcd en claro (codificados en base64, que no es cifrado). Lo mismo vale para un backup de Velero: los Secrets del namespace viajan al bucket tal cual. Cifra el destino y restringe quién lee el bucket; ver [Backup Seguro](../cybersecurity/backup_seguro.md).

## Snapshots de etcd

etcd es la base de datos que guarda el estado completo del clúster. Un snapshot es una copia consistente de esa base de datos en un instante. Es la herramienta más simple para el desastre total del plano de control, y la menos selectiva: o recuperas todo el clúster a ese instante, o nada.

### Crear el snapshot

En un clúster de kubeadm, etcd corre como pod estático y sus certificados están en `/etc/kubernetes/pki/etcd/`. Ejecuta desde un nodo de control (o desde un pod con `etcdctl` y esos ficheros montados):

```bash
ETCDCTL_API=3 etcdctl \
  --endpoints=https://127.0.0.1:2379 \
  --cacert=/etc/kubernetes/pki/etcd/ca.crt \
  --cert=/etc/kubernetes/pki/etcd/server.crt \
  --key=/etc/kubernetes/pki/etcd/server.key \
  snapshot save /var/backups/etcd/etcd-$(date +%F-%H%M).db
```

Un snapshot se toma desde un solo miembro y contiene los datos de todo el clúster; no hace falta repetirlo en cada nodo de control. Sí conviene tomarlo desde un miembro sano y comprobar que el fichero resultante es válido:

```bash
etcdutl snapshot status /var/backups/etcd/etcd-2026-10-11-0300.db --write-out=table
```

La salida es una tabla con el hash, la revisión, el número de claves y el tamaño. Una revisión y un número de claves razonables (no cero) indican que el fichero es legible; no prueba que sea restaurable.

!!! warning "Depende de la versión"
    En etcd 3.5 el subcomando `snapshot status` de `etcdctl` está marcado como obsoleto a favor de `etcdutl`, y `snapshot restore` también; en versiones posteriores puede no existir ya en `etcdctl`. Comprueba con `etcdctl snapshot --help` y `etcdutl snapshot --help` qué ofrece tu versión. Los puertos, rutas de certificados y nombres de fichero de arriba son los de kubeadm; en otras distribuciones cambian.

Un snapshot que vive en el nodo de control solo sobrevive mientras el nodo exista. Programa la toma con un timer de systemd (o un CronJob con `hostNetwork` en el nodo de control), y copia el fichero a un destino externo con [restic o Borg](restic_borg.md) o con `rclone`. La rotación local es simple: conserva los últimos N ficheros y deja el historial al repositorio de backup.

### Restaurar etcd

Restaurar un snapshot **no es una operación sobre un nodo, sino sobre el clúster entero**. El snapshot contiene el estado de todos los objetos en un instante: restaurarlo en un solo miembro de un etcd de tres crea un miembro que contradice a los otros dos. Por eso el procedimiento general es:

1. Detener el API server y etcd en **todos** los nodos de control (en kubeadm, mover los manifiestos de `/etc/kubernetes/manifests/` fuera de ese directorio).
2. Restaurar el snapshot en un directorio de datos nuevo, en cada miembro, con `etcdutl snapshot restore`, indicando el nombre del miembro, la lista de miembros iniciales y las URLs del clúster.
3. Apuntar el manifiesto de etcd (el `hostPath` del directorio de datos) al directorio restaurado.
4. Volver a poner los manifiestos y esperar a que el clúster forme quorum.

Con un único nodo de control es más corto: restaurar a un directorio nuevo, cambiar el `hostPath` en el manifiesto de etcd y arrancar. Consecuencias que conviene tener claras antes de necesitarlo:

- **Se pierde todo lo creado después del snapshot.** Si un Pod se programó, un PVC se creó o un Secret rotó después, el clúster no lo sabe. Los volúmenes reales pueden existir en el backend sin objeto que los reclame.
- **Los nodos trabajadores no se tocan**, pero el estado que reportan (kubelet) puede discrepar del restaurado hasta que se reconcilia.
- **Los certificados del snapshot pueden haber caducado** si es antiguo. Guarda también la PKI del plano de control.

!!! warning "Depende de la distribución y la versión"
    Los flags exactos de `etcdutl snapshot restore`, la ubicación del manifiesto de etcd y el orden de arranque cambian entre kubeadm, RKE2, k3s, Talos y los servicios gestionados. Consulta el procedimiento de **tu** distribución y versión y ensáyalo en un clúster de pruebas antes de necesitarlo. En un servicio gestionado (EKS, GKE, AKS) no tienes acceso a etcd: ahí solo sirve Velero o GitOps.

## etcd en k3s

k3s tiene dos modos de almacenamiento y el procedimiento depende de cuál usas.

**SQLite (por defecto con un solo servidor).** No hay etcd: el estado está en un fichero de base de datos SQLite dentro del directorio de datos del servidor (`/var/lib/rancher/k3s/server/db/`). `k3s etcd-snapshot` **no aplica**. La copia consiste en parar el servicio y copiar el directorio `db/` junto con `/var/lib/rancher/k3s/server/token`, o bien copiar un fichero SQLite en caliente con la herramienta de backup de SQLite; copiar un fichero SQLite abierto con `cp` puede dar una copia inconsistente.

**etcd embebido (`--cluster-init`, o clústeres HA).** k3s ofrece su propio comando:

```bash
k3s etcd-snapshot save --name antes-de-actualizar
k3s etcd-snapshot ls
k3s etcd-snapshot prune --name antes-de-actualizar --etcd-snapshot-retention 3
```

Con etcd embebido k3s además toma snapshots programados por su cuenta, configurables en `/etc/rancher/k3s/config.yaml`:

```yaml
etcd-snapshot-schedule-cron: "0 */6 * * *"
etcd-snapshot-retention: 14
etcd-snapshot-dir: /var/backups/k3s
# Copia a un bucket S3 compatible (MinIO) fuera del clúster
etcd-s3: true
etcd-s3-endpoint: minio.ejemplo.lan:9000
etcd-s3-bucket: k3s-etcd
etcd-s3-access-key: "<access-key>"
etcd-s3-secret-key: "<secret-key>"
```

Para restaurar se detiene k3s y se arranca el servidor con el modo de reinicio de clúster y la ruta del snapshot:

```bash
systemctl stop k3s
k3s server --cluster-reset --cluster-reset-restore-path=/var/backups/k3s/<snapshot>
```

Tras ese arranque, en un clúster de varios servidores, los demás nodos de control hay que borrarles el directorio de datos de etcd y volverlos a unir. Guarda también el token del servidor: sin él, los datos de arranque cifrados dentro del snapshot no se pueden descifrar.

!!! warning "Depende de la versión"
    Los nombres de los flags de `etcd-snapshot` y `etcd-s3` han cambiado entre versiones de k3s, y el valor por defecto de la programación y la retención también. Comprueba `k3s etcd-snapshot --help` y la documentación de tu versión. Los snapshots de k3s con S3 y el contenido de `/etc/rancher/k3s/config.yaml` de arriba son una referencia, no una receta que copiar sin verificar.

## Velero: arquitectura

Velero resuelve lo que etcd no puede: restaurar **un namespace, un recurso o un volumen** sin tocar el resto, e incluso en otro clúster. Trabaja con la API de Kubernetes (no con etcd directamente) y guarda los objetos como ficheros en almacenamiento de objetos.

| Pieza | Qué es |
|---|---|
| **Servidor de Velero** | Un Deployment en el namespace `velero`, con controladores para backups, schedules y restauraciones |
| **CLI `velero`** | Cliente que crea los objetos (`Backup`, `Schedule`, `Restore`) en el clúster |
| **BackupStorageLocation (BSL)** | Dónde se guardan los objetos del backup: un bucket S3 compatible (MinIO, Ceph RGW, AWS S3) |
| **VolumeSnapshotLocation (VSL)** | Dónde van los snapshots de volúmenes de proveedores que Velero gestiona con plugin propio (discos de nube); con CSI se usan `VolumeSnapshot` de Kubernetes |
| **Plugin de proveedor** | Imagen que enseña a Velero a hablar con un almacenamiento concreto; para S3 y MinIO, el plugin de AWS |
| **Node agent** | DaemonSet que realiza la copia a nivel de fichero de volúmenes (File System Backup) |

Todo lo que Velero crea son recursos del propio clúster (CRDs), lo que implica que el estado de qué backups existen se reconstruye leyendo el bucket: un Velero nuevo apuntando al mismo BSL "descubre" los backups existentes.

## Instalar Velero con MinIO

Necesitas un bucket y unas credenciales dedicadas con permisos solo sobre ese bucket. Crea el fichero de credenciales con el formato de AWS:

```ini
[default]
aws_access_key_id = <access-key>
aws_secret_access_key = <secret-key>
```

Y lanza la instalación contra un MinIO que corre **fuera del clúster protegido** (otro host, la NAS, otro clúster):

```bash
velero install \
  --provider aws \
  --plugins velero/velero-plugin-for-aws:<versión> \
  --bucket velero-backups \
  --secret-file ./credentials-velero \
  --backup-location-config region=minio,s3ForcePathStyle=true,s3Url=https://minio.ejemplo.lan:9000 \
  --use-node-agent \
  --use-volume-snapshots=false
```

`<versión>` es la del plugin compatible con tu versión de Velero; la tabla de compatibilidad está en el repositorio del plugin. `s3ForcePathStyle=true` es necesario con MinIO porque no usa direccionamiento por subdominio. `--use-node-agent` despliega el DaemonSet para la copia de ficheros; omítelo si solo vas a usar snapshots CSI. Si MinIO usa una CA propia, añade `--cacert` con la CA.

Comprueba que el servidor está listo y que el BSL llega al bucket:

```bash
kubectl -n velero get pods
velero backup-location get
```

El BSL debe aparecer como `Available`. Si queda en `Unavailable`, la causa es casi siempre el endpoint, las credenciales o la CA.

!!! warning "Depende de la versión"
    Velero cambia flags y comportamientos entre versiones menores: `--use-node-agent` sustituyó a `--use-restic`, el soporte CSI estuvo en un plugin aparte antes de integrarse, y algunas versiones exigen `--features=EnableCSI`. Lee las notas de la versión que instales y verifica `velero install --help`.

## Backups, schedules y restauración

Un backup de un namespace, con sus volúmenes según la configuración por defecto:

```bash
velero backup create app-prod-manual --include-namespaces app-prod
velero backup describe app-prod-manual --details
velero backup logs app-prod-manual
```

`describe --details` muestra la fase (`Completed`, `PartiallyFailed`, `Failed`), el número de recursos y, con `--details`, los volúmenes copiados. `logs` muestra el detalle de lo que falló. Un backup en `PartiallyFailed` **no es un backup bueno**: algo no se copió, y suele ser justo lo que importa.

Para programar copias recurrentes, un `schedule` con cron y retención con `--ttl`:

```bash
velero schedule create app-prod-diario \
  --schedule="0 3 * * *" \
  --include-namespaces app-prod \
  --ttl 720h0m0s
velero schedule get
velero backup get
```

`--ttl` es la vida del backup: pasado ese tiempo, Velero lo borra del bucket. Es tu política de retención y se aplica por schedule, de modo que puedes tener un schedule diario con TTL corto y otro semanal con TTL largo (una versión sencilla de GFS). Los backups creados por un schedule llevan el nombre del schedule más una marca de tiempo.

Para restaurar:

```bash
velero restore create --from-backup app-prod-diario-<marca-de-tiempo>
velero restore describe <nombre-del-restore>
velero restore logs <nombre-del-restore>
```

Comportamientos que sorprenden:

- **No sobrescribe lo que ya existe.** Si el recurso está en el clúster, Velero lo omite y avisa en los logs. Para recuperar un objeto modificado hay que borrarlo antes.
- **Si el clúster usa GitOps**, restaurar objetos con Velero compite con el controlador: Argo CD los volverá a sincronizar contra Git. Restaura solo los datos (volúmenes y recursos que no están en Git) y deja los manifiestos a Argo CD.

## Volúmenes: snapshots CSI o copia de ficheros

Velero tiene dos mecanismos para los datos de un PV, con consecuencias distintas.

| Aspecto | Snapshot CSI | File System Backup (Kopia) |
|---|---|---|
| Qué hace | Pide al driver CSI un `VolumeSnapshot` del PV | Un pod del node agent lee los ficheros del volumen montado y los sube al bucket |
| Dónde queda el dato | En el backend de almacenamiento, no en el bucket | En el bucket, cifrado y deduplicado |
| Velocidad | Segundos: es una operación del backend | Proporcional al volumen; la primera pasada es la lenta |
| Sobrevive a perder el backend | **No** (equivale a un snapshot de ZFS, no es copia) | **Sí**: el dato está en otro sitio |
| Requisitos | Driver CSI con soporte de snapshots y `VolumeSnapshotClass`; ver [Kubernetes CSI](../storage/kubernetes_csi.md) | Cualquier volumen montable por un pod; `hostPath` y NFS incluidos |
| Consistencia | A nivel de bloque: consistente ante fallos, no de aplicación | A nivel de fichero con la app en marcha: puede ver ficheros a medio escribir |

La consecuencia para el 3-2-1 es clara: un snapshot CSI sin más es la primera línea de defensa, no una copia. Si el backend (el pool de Ceph, el servidor NFS) desaparece, los snapshots desaparecen con él. Para que el dato llegue al bucket hay dos caminos: el File System Backup, o el movimiento de datos de snapshots CSI (`--snapshot-move-data` en versiones recientes), que sube el contenido del snapshot al almacén de backup.

El File System Backup se activa por volumen anotando el pod, o para todos con un flag:

```bash
# Por pod: lista de volúmenes a copiar
kubectl -n app-prod annotate pod/postgres-0 backup.velero.io/backup-volumes=datos

# Para todos los volúmenes del backup
velero backup create app-prod-fs \
  --include-namespaces app-prod \
  --default-volumes-to-fs-backup
```

!!! warning "Depende de la versión"
    El File System Backup se llamó antes integración con Restic (`--use-restic`, `--default-volumes-to-restic`). En versiones recientes el motor por defecto es Kopia y los flags usan `fs-backup` o `node-agent`; en versiones antiguas conviven los nombres viejos. Si lees tutoriales con `restic` en los flags de Velero, son anteriores al cambio. Comprueba `velero backup create --help` y el valor de `--uploader-type` en tu versión.

## Consistencia: hooks pre y post

Un snapshot o una copia de ficheros de un volumen con una base de datos escribiendo captura un instante cualquiera: puede dar un volumen que PostgreSQL recupera de un fallo (consistente ante fallos) o, peor, ficheros de distintos momentos. Hay tres estrategias, de más a menos recomendable para bases de datos:

1. **Backup lógico de la aplicación** (`pg_dump`, `mysqldump`) en un CronJob que escribe en un volumen o en el bucket, y Velero respalda el resultado. Es independiente del motor de volúmenes y restaurable en otra versión.
2. **Hooks de Velero** que congelan o preparan la aplicación antes del snapshot y la liberan después.
3. **Aceptar la consistencia ante fallos**, que funciona con motores diseñados para recuperarse de un corte (PostgreSQL, MySQL/InnoDB) pero no es una garantía formal.

Los hooks se declaran como anotaciones del pod. Un ejemplo con `fsfreeze` (el patrón que usa la propia documentación de Velero):

```yaml
metadata:
  annotations:
    pre.hook.backup.velero.io/container: fsfreeze
    pre.hook.backup.velero.io/command: '["/sbin/fsfreeze", "--freeze", "/var/lib/postgresql/data"]'
    post.hook.backup.velero.io/container: fsfreeze
    post.hook.backup.velero.io/command: '["/sbin/fsfreeze", "--unfreeze", "/var/lib/postgresql/data"]'
```

`fsfreeze` necesita un contenedor con privilegios que comparta el volumen, normalmente un sidecar; tenlo en cuenta con las políticas de seguridad del namespace (ver [Seguridad en Kubernetes](../cybersecurity/kubernetes_security.md)). Un hook `pre` que falla puede, según su configuración, abortar el backup o ignorarse: revisa el campo de error del hook y los logs del backup. Con un operador de bases de datos (CloudNativePG y similares), su mecanismo nativo de backup suele ser mejor que un hook.

## Probar la restauración

Un backup que nunca se ha restaurado es una hipótesis. Dos pruebas, de menor a mayor coste:

**Mismo clúster, otro namespace.** Restaura el backup renombrando el namespace y comprueba que la aplicación arranca y que los datos están:

```bash
velero restore create prueba-restore \
  --from-backup app-prod-diario-<marca-de-tiempo> \
  --namespace-mappings app-prod:app-prod-restore
```

Cuidado con lo que no es del namespace: un Ingress con el mismo host o un Service de tipo LoadBalancer pueden chocar con producción. Revisa qué se restaura antes de dejar que reciba tráfico.

**Otro clúster.** Es la prueba que realmente valida el desastre. En un clúster limpio (una VM con k3s basta), instala Velero apuntando al **mismo bucket** pero con el BSL en solo lectura, para que la prueba no pueda borrar ni modificar backups reales:

```bash
velero backup-location create produccion-ro \
  --provider aws \
  --bucket velero-backups \
  --config region=minio,s3ForcePathStyle=true,s3Url=https://minio.ejemplo.lan:9000 \
  --access-mode=ReadOnly
velero backup get
velero restore create --from-backup <backup-de-produccion>
```

Esto comprueba además lo que más se olvida: que las credenciales y el endpoint del bucket están **documentados fuera del clúster**. Si solo estaban en un Secret del clúster que murió, no hay restauración. Cronometra la prueba: es tu RTO real. Que el clúster limpio tenga la misma StorageClass (o un mapa de StorageClass en un ConfigMap de Velero) es necesario para que los PVC se asignen.

## Encaje con la regla 3-2-1

Aplicando la lógica de [Estrategia de Backup 3-2-1](strategy_321.md) a un clúster:

| Elemento | ¿Cuenta como copia? | Por qué |
|---|---|---|
| Datos vivos en los PV | Es la copia 1 (producción) | Es el origen |
| Snapshot CSI en el mismo backend | **No**, es primera línea de defensa | Muere con el pool o el servidor NFS |
| Snapshot de etcd en el nodo de control | **No** | Muere con el nodo |
| Bucket MinIO **dentro** del clúster protegido | **No** | Si el clúster cae, cae el bucket |
| Bucket MinIO en otro host con Velero y snapshots de etcd | **Sí**, es la copia 2 | Otro dispositivo, otro dominio de fallo |
| Réplica del bucket a otro sitio (replicación de MinIO, `rclone`, restic sobre el bucket) | **Sí**, es la copia 3 fuera del sitio | Otra ubicación física y administrativa |

El patrón completo: Velero y los snapshots de etcd escriben en un MinIO que corre fuera del clúster (copia 2), y ese bucket se replica a un destino externo con credenciales distintas (copia 3). El "1 fuera del sitio" se rompe con facilidad: si las credenciales de Velero tienen permiso de borrado sobre el bucket y el clúster se compromete, el atacante borra los backups. Usa credenciales con el mínimo permiso y, para la copia remota, inmutabilidad como se explica en [Backup Seguro](../cybersecurity/backup_seguro.md). Ojo con la interacción: el TTL de Velero borra backups caducados, lo que choca con un bucket con Object Lock; decide qué componente gobierna la retención y verifica el comportamiento en tu versión.

Las claves cuentan igual que en cualquier backup: la contraseña del repositorio de Kopia y las credenciales del bucket deben existir fuera del clúster. Un backup perfecto con la clave dentro del clúster perdido es un backup perdido.

## Troubleshooting

| Síntoma | Causa | Arreglo |
|---|---|---|
| El BSL queda en `Unavailable` | Endpoint, credenciales o CA incorrectos; falta `s3ForcePathStyle=true` con MinIO | Revisar `velero backup-location get` y los logs del pod de Velero; probar el endpoint con `mc` o `aws s3` desde un pod |
| El backup termina en `PartiallyFailed` | Un hook falló, un volumen no se pudo copiar o falta permiso RBAC | `velero backup describe --details` y `velero backup logs`; tratarlo como backup no válido hasta corregirlo |
| Los PVC no se copian aunque el backup es `Completed` | No hay `VolumeSnapshotClass` ni File System Backup activado | Anotar los pods o usar `--default-volumes-to-fs-backup`; comprobar que el node agent corre |
| La restauración omite los recursos y no hace nada | Los recursos ya existen en el clúster | Borrar los objetos antes, o restaurar en otro namespace con `--namespace-mappings` |
| El PVC restaurado queda en `Pending` | La StorageClass del backup no existe en el clúster destino | Crear la StorageClass o mapearla con un ConfigMap de cambio de StorageClass de Velero |
| La restauración trae la base de datos corrupta | Copia de ficheros sin hook ni quiesce | Backup lógico (`pg_dump`) o hooks de congelado; ver el apartado de consistencia |
| Restaurar etcd en un solo miembro rompe el clúster | El miembro restaurado contradice al resto | Restaurar en todos los miembros de forma coordinada, o reconstruir los miembros restantes |
| Argo CD revierte lo que Velero acaba de restaurar | Ambos gestionan los mismos objetos | Restaurar solo datos con Velero y dejar los manifiestos a Argo CD, o pausar la sincronización durante la prueba |

## Buenas prácticas

- **GitOps para el estado, Velero para los datos.** Lo que está en Git no necesita backup de objetos; lo que no está, sí.
- **Respalda la clave de los secretos** (SOPS, Sealed Secrets) fuera del clúster, junto con la PKI del plano de control.
- **El almacén de backup, fuera del clúster.** Un MinIO dentro del clúster protegido no es una copia.
- **Snapshot CSI no es copia.** Úsalo por velocidad; añade File System Backup o movimiento de datos para que el dato llegue a otro dominio de fallo.
- **Consistencia explícita en bases de datos**: backup lógico o hooks. No asumas que el snapshot sirve.
- **Un backup `PartiallyFailed` es un fallo.** Alerta sobre ello igual que sobre un backup que no se ejecuta.
- **Credenciales mínimas y rotadas** para Velero, sin permiso de borrado si el destino admite inmutabilidad.
- **Restaura de verdad, en otro clúster, con un BSL de solo lectura,** y cronométralo. Documenta el procedimiento fuera del clúster.

## Referencias

- [Estrategia de Backup 3-2-1](strategy_321.md) · [Restic y Borg](restic_borg.md) · [Proxmox Backup Server](pbs.md)
- [Kubernetes CSI](../storage/kubernetes_csi.md) · [Kubernetes base](../kubernetes/kubernetes_base.md) · [Probes](../kubernetes/probes.md)
- [Argo CD](../cicd/argocd.md) · [Secretos en GitOps](../cybersecurity/secrets_gitops.md)
- [Backup Seguro: cifrado, inmutabilidad y testing](../cybersecurity/backup_seguro.md) · [Seguridad en Kubernetes](../cybersecurity/kubernetes_security.md)
- [Velero: documentación oficial](https://velero.io/docs/)
- [Kubernetes: operar un clúster etcd](https://kubernetes.io/docs/tasks/administer-cluster/configure-upgrade-etcd/)
- [K3s: backup y restauración](https://docs.k3s.io/datastore/backup-restore)
