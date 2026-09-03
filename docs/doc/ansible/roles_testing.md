---
title: "Ansible — Roles y testing con Molecule"
description: "Estructura de un rol, los cuatro niveles de comprobación (sintaxis, lint, idempotencia y verificación funcional), ansible-lint sin ruido, escenarios y drivers de Molecule, el test de idempotencia explicado y la integración en CI."
keywords: "ansible, molecule, testing, ansible-lint, idempotencia, testinfra, roles, assert, github actions, ci"
tags: ['ansible', 'testing', 'automation', 'ci-cd']
updated: 2026-09-02
difficulty: intermediate
estimated_time: 25 min
category: DevOps
status: published
last_reviewed: 2026-09-02
prerequisites:
  - "[Ansible — Automatización de Infraestructura](ansible_base.md)"
  - "Python y pip"
  - "Docker o Podman funcionando en local"
reviewers: ["@rasty94"]
contributors: ["@rasty94"]
---

# Ansible — Roles y testing con Molecule

## El problema

El playbook funcionó: lo lanzaste contra la máquina nueva, salió verde, el servicio respondió. Y de ahí sacas una conclusión que no toca — que el rol *funciona*. Lo que has demostrado es que funciona **una vez**, **en esa máquina**, **desde ese estado inicial concreto**. Lo que no sabes todavía: qué pasa en la segunda ejecución, qué pasa en Debian si lo escribiste mirando a Rocky, y qué pasa cuando el fichero que gestionas ya existía con contenido distinto. Ansible se vende como idempotente, pero la idempotencia no es una propiedad del motor: es una propiedad de **tus tareas**, y se pierde con un `shell` mal escrito. Probar un rol es cerrar ese hueco de forma repetible: máquina limpia, aplicar el rol, aplicarlo otra vez, comprobar que el sistema quedó como dices que queda.

!!! note "Qué cubre y qué no"
    Esta página continúa donde acaba [Ansible — Automatización de Infraestructura](ansible_base.md): asume que sabes escribir un playbook y quieres empaquetarlo como rol probado. No cubre colecciones, AWX/AAP ni publicación firmada en Galaxy.

## 📋 Tabla de Contenidos

- [Anatomía de un rol](#anatomia-de-un-rol)
- [Por qué un playbook que funciona no está probado](#por-que-un-playbook-que-funciona-no-esta-probado)
- [Los cuatro niveles de comprobación](#los-cuatro-niveles-de-comprobacion)
- [ansible-lint sin ruido](#ansible-lint-sin-ruido)
- [Molecule: escenarios y drivers](#molecule-escenarios-y-drivers)
- [El ciclo de un escenario](#el-ciclo-de-un-escenario)
- [Idempotencia de verdad](#idempotencia-de-verdad)
- [Verificación funcional: assert o Testinfra](#verificacion-funcional-assert-o-testinfra)
- [Variables de prueba y matriz de distribuciones](#variables-de-prueba-y-matriz-de-distribuciones)
- [CI con GitHub Actions](#ci-con-github-actions)
- [Qué no merece la pena probar](#que-no-merece-la-pena-probar)
- [Troubleshooting](#troubleshooting)
- [Buenas prácticas](#buenas-practicas)
- [Referencias](#referencias)

## Anatomía de un rol

Un rol es un directorio con nombres reservados. Ansible carga el `main.yml` de cada uno automáticamente: no hay fichero índice ni configuración que lo declare.

```
roles/nginx/
├── defaults/main.yml    # variables por defecto — precedencia MÁS BAJA
├── vars/main.yml        # constantes internas — precedencia MUY ALTA
├── tasks/main.yml       # punto de entrada del rol
├── handlers/main.yml    # tareas disparadas por notify (reload, restart)
├── templates/           # ficheros .j2 renderizados con template
├── files/               # ficheros estáticos servidos con copy
├── meta/main.yml        # metadatos, dependencias, plataformas soportadas
└── molecule/default/    # escenario de prueba
```

La distinción que más problemas causa es `defaults/` frente a `vars/`. `defaults/` tiene la precedencia más baja de todas: cualquiera la sobrescribe desde el inventario, `group_vars` o el play. `vars/` está por encima de casi todo, incluidos los `vars` del propio play. Si dudas, va en `defaults/`: una variable en `vars/` deja al usuario del rol convencido de que su configuración se ignora — porque se ignora. Y las dependencias declaradas en `meta/main.yml` se ejecutan **antes** que el rol y en cada invocación; para lógica condicional casi siempre es preferible `include_role` dentro de `tasks/`.

## Por qué un playbook que funciona no está probado

Cuatro fallos que una ejecución manual exitosa no detecta:

1. **No idempotencia.** La primera pasada crea el fichero; la segunda reporta `changed` otra vez porque usaste `shell`. En producción son handlers disparándose y servicios reiniciándose en cada ejecución.
2. **Dependencia del estado inicial.** Tu máquina de pruebas ya tenía `curl`, `python3-apt` o el usuario creado. La máquina nueva, no.
3. **Deriva entre distribuciones.** `apache2` frente a `httpd`, `sites-available` frente a `conf.d`, `firewalld` frente a `nftables`.
4. **Regresión al cambiar una variable.** Alguien toca un default seis meses después y nadie vuelve a aplicar el rol sobre una máquina limpia hasta el día del despliegue.

## Los cuatro niveles de comprobación

Cada nivel cuesta más y coge cosas distintas. En este orden: el barato primero.

| Nivel | Comando | Qué coge | Qué NO coge |
|---|---|---|---|
| **Sintaxis** | `ansible-playbook --syntax-check` | YAML inválido, módulos inexistentes, parámetros mal anidados | Todo lo semántico |
| **Lint** | `ansible-lint` | Antipatrones, `shell` evitable, permisos implícitos, nombres ausentes | Que el rol haga lo que dice |
| **Idempotencia** | `molecule idempotence` | Tareas que cambian algo en cada pasada | Que el resultado sea correcto |
| **Verificación funcional** | `molecule verify` | Que el servicio esté instalado, activo y escuchando | Rendimiento y carga real |

Existe además el *check mode* (`ansible-playbook --check --diff`), útil contra máquinas reales para ver qué cambiaría antes de tocar nada. Pero **no es un test**: no todos los módulos lo soportan con fidelidad, y cualquier tarea que dependa del `register` de una anterior que en check mode no llegó a ejecutarse da un resultado falso. Sirve para revisar un cambio, no para validar un rol.

## ansible-lint sin ruido

Sin configuración, `ansible-lint` sobre un rol existente escupe cientos de avisos —la mitad irrelevantes para ti— y el equipo aprende a ignorarlo en una semana. La configuración es lo que lo hace útil.

```yaml
# .ansible-lint
profile: moderate          # conjunto progresivo de reglas, no todas de golpe
skip_list:
  - yaml[line-length]      # decisión de estilo, no un fallo
  - package-latest         # deliberado en el rol de estaciones de trabajo
warn_list: ["name[casing]"] # avisa, no rompe el build
```

Empezar por un perfil laxo y subirlo cuando el rol esté limpio es más realista que arrancar con todo encendido. Las reglas que más ruido dan:

| Regla | De qué se queja | Trato razonable |
|---|---|---|
| `name[missing]`, `name[casing]` | Tareas sin nombre o en minúscula | Arreglar: el nombre es lo que lees cuando falla |
| `fqcn[action-core]` | `copy:` en vez de `ansible.builtin.copy:` | Arreglar de una vez con `--fix` y olvidarse |
| `no-changed-when` | `command`/`shell` sin `changed_when` | **Arreglar siempre**: es lo que rompe la idempotencia |
| `risky-file-permissions` | `copy`/`file` sin `mode` | Arreglar: el modo implícito depende del umask remoto |
| `package-latest` | `state: latest` | Legítimo en workstations, mal en servidores |
| `yaml[line-length]` | Líneas largas | Silenciar sin remordimientos |

Ojo con `ansible-lint --fix`: además de corregir reglas reformatea el YAML. Ejecútalo con el árbol de trabajo limpio y revisa el diff antes de commitear — no es una operación cosmética inocua.

## Molecule: escenarios y drivers

Molecule automatiza el bucle "levanta, aplica, comprueba, destruye". Un **escenario** es un directorio bajo `molecule/` con su configuración (`molecule.yml`), el playbook que aplica el rol (`converge.yml`) y las comprobaciones (`verify.yml`). El llamado `default` es el que se ejecuta si no dices otra cosa.

```bash
molecule init scenario -s proxy   # añadir escenario a un rol existente
molecule test                     # escenario default; -s proxy para otro, --all para todos
```

El **driver** decide sobre qué se prueba:

| Driver | Aísla | Coste | Cuándo |
|---|---|---|---|
| Contenedor (Docker/Podman) | Procesos y ficheros | Segundos | El 90 % de los roles: paquetes, ficheros, plantillas, usuarios |
| Máquina virtual (Vagrant, libvirt, nube) | Kernel completo | Minutos | Módulos de kernel, cortafuegos, particiones, systemd real |
| `delegated` / `default` | Nada: los hosts los pones tú | Variable | Infraestructura existente o tecnologías sin driver |

La limitación del contenedor no es un detalle menor: no hay `systemd` de serie, no hay `/sys` completo y no hay reglas de cortafuegos aplicables. Un rol que instala paquetes y despliega plantillas se prueba perfectamente en contenedor; uno que gestiona `nftables` o monta volúmenes necesita VM, o estarás probando la mitad que da igual.

!!! danger "Aquí es donde te muerde la versión"
    La estructura de configuración de Molecule **ha cambiado entre versiones mayores**. Lo que depende de tu versión y no debes copiar a ciegas de un blog: los drivers dejaron de venir en el paquete principal (una época sueltos —`molecule-docker`, `molecule-podman`, `molecule-vagrant`— y después agrupados en `molecule-plugins`); versiones recientes empujan hacia el driver `default` con tus propios playbooks `create.yml`/`destroy.yml` en lugar de un driver por tecnología; y la clave `lint:` dentro de `molecule.yml` existió, cambió de forma y acabó desapareciendo. Antes de escribir tu `molecule.yml`, ejecuta `molecule --version` y `molecule drivers`, y lee la documentación **de esa versión**. Lo estable en todas: la estructura de directorios de escenarios, los nombres de las fases y el concepto de idempotencia. Lanzar `ansible-lint` como paso propio en CI, fuera de Molecule, funciona con cualquier versión y te ahorra el problema entero.

## El ciclo de un escenario

`molecule test` encadena las fases del escenario en orden: `create` → `converge` → `idempotence` → `verify` → `destroy`.

| Fase | Qué hace |
|---|---|
| `dependency` | Descarga roles y colecciones de `requirements.yml`; `create` levanta las instancias de `platforms` y `prepare` prepara el terreno |
| `converge` | Aplica el rol — tu playbook de verdad |
| `idempotence` | Repite `converge` y falla si algo reporta `changed` |
| `verify` | Ejecuta las comprobaciones, y `destroy` elimina las instancias |

Durante el desarrollo **no ejecutes `molecule test`**: destruye la instancia al terminar, justo cuando querías inspeccionarla. El bucle rápido es `molecule converge` para aplicar, `molecule login` para entrar, `molecule verify` para comprobar y `molecule destroy` al acabar; `molecule test` es para CI y para la validación final.

## Idempotencia de verdad

La fase `idempotence` hace algo muy simple: ejecuta `converge` **una segunda vez** y mira el resumen. Si alguna tarea reporta `changed`, falla.

No es un tecnicismo: un rol no idempotente reescribe ficheros y reinicia servicios en cada ejecución sobre tu flota, la pasada "de comprobación" pasa a ser destructiva y la gente deja de lanzar Ansible por miedo.

**1. `command` y `shell` sin declarar cuándo cambian algo.** Siempre reportan `changed`, porque Ansible no puede saber qué hicieron. Si el comando produce un artefacto, lo resuelve `creates:` (o su gemelo `removes:`); si no, lo decide su salida — `changed_when: false` para lo que sólo consulta, una expresión sobre `stdout` o `rc` para lo que actúa:

{% raw %}
```yaml
- name: Compile the assets
  ansible.builtin.command: npm run build
  args: { chdir: /opt/app, creates: /opt/app/dist/index.html }   # sin creates: changed siempre

- name: Check the pending migrations
  ansible.builtin.command: /opt/app/bin/migrate --status
  register: migracion
  changed_when: false

- name: Apply the migrations
  ansible.builtin.command: /opt/app/bin/migrate --apply
  when: migracion.rc == 2
  register: resultado
  changed_when: "'applied' in resultado.stdout"
```
{% endraw %}

**2. `lineinfile` con una expresión que no reconoce lo que escribe.** Si la `regexp` busca un patrón y la `line` escribe otro que ya no encaja, la segunda pasada no la encuentra y la añade otra vez: a las veinte ejecuciones tienes veinte líneas. La `regexp` debe casar con la **clave**; la `line` lleva clave y valor.

```yaml
- name: Set the port
  ansible.builtin.lineinfile:
    path: /etc/app.conf
    regexp: '^port\s*='      # ✅ casa con la clave; con '^port = 8080' se duplicaría
    line: 'port = 9090'
```

Si vas a tocar más de dos líneas del mismo fichero, abandona `lineinfile` y usa `template`: el fichero entero pasa a ser tuyo y la idempotencia sale gratis.

**3. Plantillas con contenido volátil.** Una plantilla que renderiza {% raw %}`{{ ansible_date_time.iso8601 }}`{% endraw %} o un valor aleatorio produce un fichero distinto en cada pasada, y por tanto `changed` eterno. La cabecera de "generado por Ansible" va sin fecha.

**4. `state: latest` y descargas sin condición.** `package: state=latest` reporta `changed` cada vez que el repositorio publica una actualización: correcto, pero no idempotente por definición. En cualquier cosa que deba ser reproducible, `state: present` con la versión fijada. Cuando `idempotence` falla, la salida señala la tarea pero no siempre el motivo: el diagnóstico directo es repetir la pasada mostrando el diff con `molecule converge -- --diff -v`, que sobre `template`, `copy` y `lineinfile` enseña el diff del fichero — ahí suele aparecer el espacio en blanco, el salto de línea final o el permiso que baila.

## Verificación funcional: assert o Testinfra

Tras `converge` toca comprobar que el sistema quedó como dices. Dos caminos, ambos válidos. **Con el módulo `assert`** (verifier `ansible`, el de por defecto): sin dependencias nuevas y en el lenguaje que ya usas.

{% raw %}
```yaml
# molecule/default/verify.yml
---
- name: Verify
  hosts: all
  tasks:
    - name: Gather the package facts
      ansible.builtin.package_facts: { manager: auto }

    - name: The package must be installed
      ansible.builtin.assert:
        that: "'nginx' in ansible_facts.packages"

    - name: The site must answer
      ansible.builtin.uri: { url: "http://localhost/", status_code: 200 }
```
{% endraw %}

**Con Testinfra** (ficheros `test_*.py` dentro del escenario): pytest con una API de introspección del sistema; compensa cuando las comprobaciones tienen lógica, parametrización o mucho volumen.

```python
# molecule/default/tests/test_nginx.py
def test_service(host):
    svc = host.service("nginx")
    assert host.package("nginx").is_installed
    assert svc.is_running and svc.is_enabled
    assert host.socket("tcp://0.0.0.0:80").is_listening


def test_config(host):
    conf = host.file("/etc/nginx/nginx.conf")
    assert conf.user == "root" and conf.mode == 0o644
```

Elección honesta: **empieza con `assert`**. Una dependencia menos, lo entiende cualquiera del equipo y cubre la inmensa mayoría de roles. Pásate a Testinfra cuando el `verify.yml` empiece a pedir bucles y condicionales — la señal de que estás programando en YAML.

!!! tip "Comprueba el comportamiento, no la implementación"
    Que el paquete esté instalado y el puerto escuche, bien; que exista exactamente la línea 42 del fichero de configuración, no. El test debe romperse cuando el servicio deje de funcionar, no cuando reescribas la plantilla.

## Variables de prueba y matriz de distribuciones

El `converge.yml` es un playbook normal: ahí van las variables con las que quieres probar el rol.

```yaml
# molecule/default/converge.yml
---
- name: Converge
  hosts: all
  become: true
  vars: { nginx_port: 8080 }
  tasks:
    - name: Apply the role
      ansible.builtin.include_role: { name: nginx }
```

Un escenario por **combinación significativa**, no por variable: `default` con los valores de fábrica y `proxy` con la configuración de proxy inverso aportan; doce escenarios para doce banderas booleanas son doce formas de que el CI tarde media hora. Las plataformas van en `molecule.yml`: la sintaxis exacta depende del driver y de la versión, pero la idea es estable — una entrada por sistema soportado, con imágenes preparadas para Ansible (Python y systemd ya dentro) en vez de las oficiales peladas.

```yaml
# molecule/default/molecule.yml — fragmento; ajústalo a tu driver y versión
platforms:
  - { name: debian12, image: "geerlingguy/docker-debian12-ansible:latest", pre_build_image: true }
  - { name: rocky9, image: "geerlingguy/docker-rockylinux9-ansible:latest", pre_build_image: true }
```

Prueba lo que declaras en `meta/main.yml` y nada más. Si los metadatos dicen Debian y RHEL, la matriz son esos dos; añadir Ubuntu, Alpine y Arch "por si acaso" multiplica el tiempo de CI para cubrir plataformas que nadie te va a reclamar.

## CI con GitHub Actions

El patrón mínimo que funciona: lint como job separado y una matriz de escenarios.

{% raw %}
```yaml
# .github/workflows/molecule.yml
name: Molecule
on: [push, pull_request]

jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: '3.11' }
      - run: pip install ansible-lint && ansible-lint

  molecule:
    runs-on: ubuntu-latest
    needs: lint
    strategy:
      fail-fast: false                       # ver todas las plataformas, no la primera
      matrix: { scenario: [default, proxy] }
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: '3.11', cache: pip }
      - run: pip install -r requirements-test.txt   # versiones fijadas
      - run: molecule test -s ${{ matrix.scenario }}
```
{% endraw %}

Las tres decisiones que importan ahí: `fail-fast: false`, porque quieres saber si falla en Debian *y* en Rocky; versiones fijadas en `requirements-test.txt`, porque Molecule y sus plugins rompen compatibilidad entre mayores y un `pip install molecule` sin fijar convierte el CI en una bomba de relojería; y el lint antes que Molecule, porque tarda segundos y evita levantar contenedores para descubrir un error de estilo. Los runners `ubuntu-latest` traen Docker preinstalado, así que el driver de contenedor funciona sin preparativos; el de VM no, porque necesita virtualización anidada y runner propio. Más contexto de workflows en [Introducción a GitHub Actions](../cicd/github_actions.md).

## Qué no merece la pena probar

- **Que Ansible funcione.** Si `package: state=present` instala paquetes es problema de Ansible, no tuyo.
- **Cada valor de cada plantilla.** Comprueba que el servicio arranca con la configuración generada; comparar el fichero renderizado línea a línea es duplicar la plantilla dentro del test.
- **Roles de una sola tarea.** Uno que instala un paquete y termina no necesita escenario: con el lint basta. Ni los servicios externos: que la base de datos remota conteste no depende de tu rol.
- **Combinaciones que nadie usa.** Prueba la configuración por defecto y la que despliegas de verdad; el resto es hipótesis. Y si un test no puede fallar por un cambio en el rol, bórralo.

## Troubleshooting

| Síntoma | Causa | Arreglo |
|---|---|---|
| `idempotence` falla y `converge` va bien | Una tarea reporta `changed` siempre | `molecule converge -- --diff` y buscar la tarea en la salida |
| El contenedor arranca y muere al instante | Imagen sin init y el rol usa `service` | Imagen con systemd (`*-ansible`) o driver de VM |
| `Failed to connect to the host via ssh` | El escenario usa transporte SSH contra un contenedor | Revisar la conexión del driver: en contenedor debe ser la nativa |
| `verify` pasa pero producción rompe | La instancia no representa al destino | Igualar distribución y versión con `meta/main.yml` |
| Todo falla tras `pip install --upgrade` | Cambio de versión mayor de Molecule o sus plugins | Fijar versiones y leer las notas de esa versión |
| `ansible-lint` saca cientos de avisos | Sin configuración: todas las reglas activas | Crear `.ansible-lint` con un `profile` laxo |
| Variable ignorada al probar el rol | Está en `vars/`, no en `defaults/` | Mover a `defaults/main.yml` |

Cuando nada tiene sentido: `molecule --debug converge` y `molecule login -h debian12` para entrar a mirar.

## Buenas prácticas

- **Un escenario `default` en todo rol que vaya a sobrevivir a esta semana**, y **`ansible-lint` en CI desde el primer commit.** Añadirlo a un rol de 400 líneas es un día de trabajo; tenerlo desde el principio es gratis.
- **Ningún `command` ni `shell` sin `creates`, `changed_when` o ambos.** Causa número uno de no idempotencia.
- **`defaults/` por defecto; `vars/` sólo para constantes internas.**
- **Versiones fijadas en las dependencias de test.** Que decida tu CI cuándo actualizar, no PyPI.
- **`molecule converge` al desarrollar, `molecule test` en CI**, sobre las plataformas de `meta/main.yml` y ni una más: cada fila de la matriz se paga en cada push.

## Referencias

- [Roles de Ansible — doc oficial](https://docs.ansible.com/ansible/latest/playbook_guide/playbooks_reuse_roles.html)
- [Molecule](https://ansible.readthedocs.io/projects/molecule/) · [ansible-lint — reglas y perfiles](https://ansible.readthedocs.io/projects/lint/) · [Testinfra](https://testinfra.readthedocs.io/)
- [Ansible — Automatización de Infraestructura](ansible_base.md) · [Introducción a GitHub Actions](../cicd/github_actions.md) · [Terraform](../terraform/terraform_base.md) · [Podman Quadlet](../docker/quadlets.md)
