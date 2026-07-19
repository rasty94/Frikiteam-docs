---
title: "Criptografía Aplicada: primitivas, hashing y gestión de claves"
description: "Qué primitiva criptográfica usar para cada problema: simétrico vs asimétrico vs hashing, hashing de contraseñas con Argon2, cifrado autenticado (AEAD), cifrado at-rest con LUKS, gestión de claves y los errores que se repiten en producción."
keywords: "criptografia aplicada, argon2, bcrypt, aead, aes-gcm, chacha20, ed25519, luks, dm-crypt, gestion de claves, kdf, hashing de contraseñas, nonce, timing attack"
date: 2026-07-19
tags: [cybersecurity, cryptography, hashing, encryption, key-management]
draft: false
updated: 2026-07-19
difficulty: intermediate
estimated_time: "16 min"
category: Ciberseguridad
status: published
last_reviewed: 2026-07-19
prerequisites:
  - "Linux intermedio"
  - "Conocimientos básicos de DevOps"
reviewers: ["@rasty94"]
contributors: ["@rasty94"]
---

## Alcance: lo que este documento sí cubre

La mayoría de guías de criptografía en un contexto DevOps empiezan por TLS y acaban en Let's Encrypt. Ese terreno ya está cubierto en este repositorio y no se repite aquí. Este documento es la **capa que esas guías dan por sabida**: qué primitiva resuelve qué problema, por qué elegir una u otra, y cuáles son los errores que llevan años repitiéndose en código real.

!!! info "Dónde está lo demás"
    - **TLS, cadenas de certificado, Let's Encrypt, cipher suites, OCSP, HSTS** → [Certificados TLS](../networking/certificados_tls.md).
    - **VPNs y WireGuard en la práctica** → [Tailscale](../networking/tailscale.md), [NetBird](../networking/netbird.md) y [Migración de VPN a mesh](../networking/vpn_to_mesh_migration.md).
    - **Dónde guardar las claves y secretos** → [Gestión de Secretos](gestion_secretos.md) y [Secretos en GitOps](secrets_gitops.md).

Aquí hablamos de las decisiones que se toman *antes* de configurar cualquiera de esas herramientas.

## Cifrar, hashear y codificar no son lo mismo

Es el malentendido más caro y el más frecuente. Tres operaciones distintas, con propiedades distintas:

| Operación | ¿Reversible? | ¿Necesita clave? | Para qué sirve |
| --- | --- | --- | --- |
| **Codificar** (base64, hex, URL-encoding) | Sí, por cualquiera | No | Transportar bytes por un canal que espera texto |
| **Hashear** (SHA-256, BLAKE2, Argon2) | No, por diseño | No (salvo HMAC) | Verificar integridad o comprobar contraseñas |
| **Cifrar** (AES-GCM, ChaCha20-Poly1305) | Sí, con la clave | Sí | Ocultar el contenido a quien no tenga la clave |

!!! danger "base64 no es cifrado"
    Un `Secret` de Kubernetes en base64 es texto plano con un paso extra. Cualquiera con el YAML tiene el valor. Este punto se desarrolla en [Secretos en GitOps](secrets_gitops.md), y es la razón de existir de SOPS, Sealed Secrets y ESO.

Corolario práctico: si alguien dice "la contraseña está encriptada en base64", no está encriptada. Si dice "guardamos la contraseña cifrada con AES", probablemente también esté mal — las contraseñas se **hashean**, no se cifran, porque nadie debería poder recuperarlas.

## Primitivas: cuándo usar cada una

### Cifrado simétrico

La misma clave cifra y descifra. Es rápido y es lo que usas para volúmenes de datos reales.

- **AES-256-GCM**: el estándar por defecto. Con aceleración por hardware (AES-NI, presente en cualquier CPU de servidor moderna) es extremadamente rápido.
- **ChaCha20-Poly1305**: alternativa de rendimiento equivalente o mejor **sin** aceleración hardware. Es la elección típica en móviles, routers y dispositivos embebidos. Es también lo que usa WireGuard.

Ambos son AEAD (ver más abajo), y esa es la razón principal para preferirlos sobre modos antiguos.

### Cifrado asimétrico

Dos claves: una pública que se reparte, una privada que no sale de su sitio. Es lento comparado con el simétrico, así que **casi nunca se usa para cifrar datos directamente**. Se usa para acordar una clave simétrica o para firmar.

- **Ed25519**: la opción moderna para firmas. Claves cortas, rápido, sin parámetros que puedas configurar mal. Es lo que deberías generar para claves SSH nuevas.
- **X25519**: intercambio de claves (Diffie-Hellman sobre curva 25519). Es el mecanismo detrás de WireGuard y de las suites modernas de TLS.
- **RSA**: sigue siendo omnipresente por compatibilidad. Si tienes que usarlo, no bajes de 2048 bits y prefiere 4096 para claves de larga vida. Para lo demás, curvas elípticas.
- **ECDSA (P-256, P-384)**: común en certificados TLS. Funciona, pero es más frágil de implementar que Ed25519 porque una firma con nonce repetido filtra la clave privada.

### Hashing

Función de un solo sentido. Dos familias que la gente mezcla constantemente:

- **Hashes de propósito general** (SHA-256, SHA-512, BLAKE2, SHA-3): diseñados para ser **rápidos**. Sirven para integridad de ficheros, deduplicación, firmas, Merkle trees, identificadores de contenido en Git.
- **Hashes de contraseñas** (Argon2, scrypt, bcrypt): diseñados para ser **lentos y caros en memoria**. Sirven solo para contraseñas.

Usar el primero donde toca el segundo es un fallo grave, y merece su propia sección.

!!! warning "MD5 y SHA-1 están rotos para uso criptográfico"
    Ambos tienen colisiones prácticas demostradas. Siguen siendo aceptables como checksum contra corrupción accidental (no maliciosa), pero nunca para firmas, certificados ni verificación de integridad frente a un atacante.

## Hashing de contraseñas

### Por qué SHA-256 está mal aquí

SHA-256 es rápido, y ese es exactamente el problema. Una GPU moderna calcula miles de millones de SHA-256 por segundo. Si te roban la base de datos, un atacante prueba diccionarios enteros en minutos.

Los algoritmos de hashing de contraseñas invierten la propiedad deseada: son **deliberadamente lentos** y, en el caso de Argon2 y scrypt, **deliberadamente caros en memoria**, lo que anula buena parte de la ventaja del hardware especializado (GPU, FPGA, ASIC).

### Los tres candidatos

- **Argon2id**: la recomendación por defecto para sistemas nuevos. Combina resistencia a ataques por canal lateral y a ataques con hardware especializado.
- **scrypt**: también con coste de memoria configurable. Opción razonable si Argon2 no está disponible en tu stack.
- **bcrypt**: veterano, ampliamente disponible y todavía aceptable. Su límite conocido es que **trunca la entrada** (los bytes más allá de 72 se ignoran en las implementaciones habituales), lo que importa si permites contraseñas largas o si pre-hasheas antes de bcrypt.

!!! warning "Los parámetros cambian con el tiempo"
    El work factor correcto depende del hardware del año en curso y del presupuesto de latencia de tu login. No copies números de un blog (ni de este documento). Consulta la **guía OWASP vigente de almacenamiento de contraseñas** y mide en tu propio hardware: si un login tarda menos de unas decenas de milisegundos en calcular el hash, probablemente los parámetros son demasiado bajos.

### Salt: no es opcional y no lo gestionas tú

Un salt es un valor aleatorio único **por contraseña**, que se almacena junto al hash. Impide que dos usuarios con la misma contraseña tengan el mismo hash y hace inservibles las rainbow tables.

La buena noticia: cualquier librería seria de hashing de contraseñas genera el salt automáticamente y lo empotra en la cadena de salida. Si estás escribiendo código para generar y concatenar salts a mano, casi seguro te estás complicando y equivocando.

```python
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, VerificationError

# argon2-cffi usa Argon2id y genera el salt por ti.
# Los parámetros por defecto se actualizan con las versiones de la librería;
# ajústalos midiendo en tu hardware y siguiendo la guía OWASP vigente.
ph = PasswordHasher()

def registrar(password: str) -> str:
    # La cadena resultante incluye algoritmo, parámetros, salt y hash.
    # Guarda esa cadena entera: no separes el salt en otra columna.
    return ph.hash(password)

def verificar(hash_guardado: str, password: str) -> bool:
    try:
        ph.verify(hash_guardado, password)
    except (VerifyMismatchError, VerificationError):
        return False
    if ph.check_needs_rehash(hash_guardado):
        # Los parámetros han subido desde que se creó este hash.
        # Aquí tienes la contraseña en claro: es el momento de re-hashear.
        guardar_nuevo_hash(ph.hash(password))
    return True
```

`check_needs_rehash` es la pieza que casi todo el mundo se salta, y es la que mantiene tu base de datos al día sin migraciones masivas.

### Migrar hashes antiguos sin romper logins

El escenario real: tienes una tabla con miles de `sha256(password)` y quieres llegar a Argon2id. No puedes recalcular nada porque no tienes las contraseñas.

Hay dos estrategias, y conviene entender el compromiso de cada una.

**Migración perezosa (lazy)**: marcas cada fila con el algoritmo que usa, y en el siguiente login exitoso re-hasheas con el nuevo. Es simple y sin riesgo, pero los usuarios inactivos se quedan con el hash débil indefinidamente. Necesitas una fecha de corte y una política para las cuentas que nunca vuelven.

**Envolver (wrapping)**: aplicas Argon2 **sobre el hash antiguo**, sin necesidad de la contraseña. Migras el 100% de las filas de golpe, en un solo `UPDATE`, y a partir de ese momento nadie tiene hashes débiles.

```python
import hashlib
from argon2 import PasswordHasher

ph = PasswordHasher()

def envolver(sha256_hex: str) -> str:
    # Migración masiva: no requiere la contraseña del usuario.
    return ph.hash(sha256_hex)

def verificar_envuelto(hash_guardado: str, password: str) -> bool:
    # Se reproduce el hash legado y se verifica contra el envoltorio.
    legado = hashlib.sha256(password.encode()).hexdigest()
    try:
        ph.verify(hash_guardado, legado)
        return True
    except Exception:
        return False
```

!!! warning "El wrapping tiene coste operativo"
    Quedas con dos formatos vivos en producción y con una columna que indica cuál es cuál. Documenta el esquema, marca cada fila, y planifica el paso a Argon2 puro en el siguiente login. Si no llevas la cuenta de qué fila está en qué formato, la migración se vuelve irreversible por confusión, no por criptografía.

## AEAD: cifrar sin autenticar es un fallo

Cifrar oculta el contenido. **No impide que el atacante lo modifique.** Con modos antiguos como CBC sin MAC, un atacante que no puede leer el mensaje sí puede alterar bits del texto cifrado de forma controlada, y el receptor descifrará basura sin enterarse — o algo peor que basura.

AEAD (*Authenticated Encryption with Associated Data*) resuelve esto: cifra y autentica en la misma operación. Si un solo bit ha cambiado, el descifrado **falla** en vez de devolver datos manipulados.

Salvo que tengas un motivo muy concreto y sepas exactamente lo que haces, tu cifrado simétrico debe ser AEAD: **AES-GCM** o **ChaCha20-Poly1305**.

### Nonces: la trampa que hunde el sistema

Un nonce (*number used once*) acompaña a cada operación de cifrado. La regla es literal: **jamás repitas un nonce con la misma clave**.

Con AES-GCM, reutilizar un nonce no es una debilidad teórica. Permite recuperar información del texto plano y, peor, permite recuperar la clave de autenticación, con lo que el atacante pasa a poder **falsificar mensajes válidos**. Es un fallo catastrófico, no gradual.

Dos formas seguras de generarlos: aleatorio con un CSPRNG, o un contador que nunca se reinicie. El contador es tentador y es exactamente lo que se rompe cuando restauras un backup, clonas una VM o reinicias un contenedor sin estado persistente.

```python
import os
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

# Genera y guarda esta clave con un gestor de secretos, no en el código.
key = AESGCM.generate_key(bit_length=256)
aesgcm = AESGCM(key)

def cifrar(mensaje: bytes, contexto: bytes) -> bytes:
    nonce = os.urandom(12)  # 96 bits, aleatorio, uno nuevo por mensaje
    # 'contexto' son datos asociados: se autentican pero NO se cifran.
    # Sirve para atar el mensaje a su destino (ID de tenant, versión, etc.).
    ct = aesgcm.encrypt(nonce, mensaje, contexto)
    return nonce + ct  # el nonce no es secreto: viaja con el mensaje

def descifrar(blob: bytes, contexto: bytes) -> bytes:
    nonce, ct = blob[:12], blob[12:]
    # Lanza InvalidTag si el mensaje o el contexto han sido alterados.
    return aesgcm.decrypt(nonce, ct, contexto)
```

!!! tip "Si cifras mucho con la misma clave, usa XChaCha20-Poly1305"
    El nonce de 96 bits de AES-GCM da un margen limitado para nonces aleatorios: a partir de cierto volumen de mensajes bajo la misma clave, la probabilidad de colisión deja de ser despreciable. XChaCha20-Poly1305 (disponible en libsodium) usa un nonce de 192 bits, donde la colisión aleatoria es un no-problema. La alternativa es rotar la clave con más frecuencia.

Los *datos asociados* del último parámetro son una herramienta infrautilizada: te permiten atar un texto cifrado a su contexto legítimo. Un registro cifrado del tenant A no se podrá descifrar como si fuera del tenant B, aunque un atacante lo mueva de sitio en la base de datos.

## Cifrado at-rest: qué protege y qué no

### Cifrado de disco: LUKS/dm-crypt

LUKS es el estándar de facto en Linux para cifrado de bloque completo. Cifra el dispositivo entero, de forma transparente para el sistema de ficheros.

```bash
# Formatear un dispositivo con LUKS2 (destruye los datos existentes)
sudo cryptsetup luksFormat --type luks2 /dev/sdb1

# Abrirlo: crea /dev/mapper/datos
sudo cryptsetup open /dev/sdb1 datos
sudo mkfs.ext4 /dev/mapper/datos
sudo mount /dev/mapper/datos /mnt/datos

# Inspeccionar cabecera, algoritmo y slots de clave
sudo cryptsetup luksDump /dev/sdb1

# Añadir una segunda passphrase (clave de recuperación) y luego rotar la primera
sudo cryptsetup luksAddKey /dev/sdb1
sudo cryptsetup luksChangeKey /dev/sdb1 -S 0

# Copia de seguridad de la cabecera: sin ella los datos son irrecuperables
sudo cryptsetup luksHeaderBackup /dev/sdb1 --header-backup-file luks-header.img

# Cerrar
sudo umount /mnt/datos && sudo cryptsetup close datos
```

!!! danger "La cabecera LUKS es un punto único de fallo"
    Contiene el material de clave envuelto. Si se corrompe, ninguna passphrase sirve y el volumen se pierde entero. Haz backup de la cabecera y guárdala **cifrada y fuera del disco que protege** — es tan sensible como una clave privada. Ver [Backup Seguro](backup_seguro.md).

### Lo que el cifrado de disco NO protege

Aquí es donde falla la intuición de mucha gente, y donde se firman auditorías con una casilla marcada que no significa lo que parece:

- **Con el sistema arrancado y el volumen montado, no protege nada.** La clave está en RAM y el sistema de ficheros está en claro para cualquier proceso con permisos. Un atacante con RCE en tu servidor ve los datos igual que si no hubiera cifrado.
- **No protege frente a un administrador del sistema**, ni frente a un compromiso de root.
- **No protege frente al hipervisor** ni frente al proveedor cloud, que controla la máquina por debajo.
- **No protege backups**: si el proceso de backup lee ficheros del volumen montado, se lleva los datos en claro salvo que cifres el backup por separado.

Lo que sí protege, y no es poco: **discos apagados**. Robo del portátil, retirada de hardware, un disco de datacenter que sale por RMA, un array desmontado. Ese es su modelo de amenaza real.

### Cifrado a nivel de aplicación

Cifrar campos concretos dentro de la aplicación antes de guardarlos protege lo que el disco no: los datos siguen cifrados frente al DBA, frente a un dump de la base de datos, frente a réplicas, backups y logs de auditoría, y frente a un atacante que llegue a la base de datos pero no al servicio que tiene la clave.

El precio es real y hay que aceptarlo antes de empezar:

- **Pierdes consultas sobre esos campos.** No hay `WHERE`, ni `LIKE`, ni ordenación, ni índices útiles sobre datos cifrados. Para búsqueda por igualdad exacta se puede indexar un HMAC determinista del valor (con una clave distinta), asumiendo que eso filtra qué filas comparten valor.
- **La gestión de claves pasa a ser tu problema**, incluida la rotación con datos históricos ya cifrados.
- **Un error de implementación es tuyo**, no del kernel.

La regla razonable: cifrado de disco **siempre** (es casi gratis), y cifrado a nivel de aplicación **selectivo**, solo para los campos que de verdad lo justifican — tokens, claves de terceros, datos de salud, documentos de identidad.

## Gestión de claves: el problema de verdad

Elegir AES-256 es la parte fácil y la que menos importa. Nadie rompe AES: entran por la clave. La pregunta seria es dónde vive, quién puede leerla y qué pasa el día que se filtra.

Este documento no repite el catálogo de herramientas: Vault, AWS Secrets Manager y Kubernetes Secrets están comparados en [Gestión de Secretos](gestion_secretos.md), y el caso concreto de secretos versionados en Git en [Secretos en GitOps](secrets_gitops.md). Lo que sigue son los conceptos criptográficos que esas guías dan por conocidos.

### Derivación de claves (KDF)

Una KDF convierte material de entrada en una clave criptográfica. Dos casos distintos que no se deben confundir:

- **De una contraseña a una clave**: entrada de baja entropía, hace falta una KDF **lenta** con salt: Argon2id, scrypt o PBKDF2. Es lo que hace LUKS con tu passphrase.
- **De una clave a varias claves**: entrada ya de alta entropía, basta con una KDF **rápida**: HKDF. Sirve para derivar subclaves por propósito desde una clave maestra.

```python
import os
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

master = os.urandom(32)  # clave maestra: del KMS/HSM, nunca hardcodeada

def subclave(proposito: str) -> bytes:
    # 'info' separa dominios: la misma maestra produce claves
    # independientes para cifrar, para HMAC, para tokens...
    return HKDF(
        algorithm=hashes.SHA256(),
        length=32,
        salt=None,
        info=proposito.encode(),
    ).derive(master)

clave_datos = subclave("cifrado-datos-v1")
clave_indice = subclave("hmac-indice-busqueda-v1")
```

Derivar subclaves por propósito es una costumbre barata que evita el error de reutilizar la misma clave para cifrar y para firmar, y convierte la rotación en un cambio de sufijo de versión.

### Rotación: el sufijo de versión

Rotar una clave sin planificarlo antes es doloroso, porque los datos cifrados con la clave vieja siguen ahí. La solución es tan simple como incómoda de retrofitear: **etiqueta cada texto cifrado con el identificador de la clave que lo cifró**. Un byte de versión al principio del blob basta.

Con eso, la rotación es: generar la clave nueva, cifrar todo lo nuevo con ella, seguir aceptando la vieja para descifrar, y re-cifrar lo antiguo en segundo plano. Sin el identificador de versión, esto es imposible y acabas con un big bang de migración.

!!! warning "Rotar la clave no rota el secreto"
    Si una credencial se ha filtrado, re-cifrarla con una clave nueva no sirve de nada: el atacante ya tiene el valor en claro. Hay que **cambiar la credencial** en el sistema de origen. Son dos operaciones distintas y se confunden a menudo.

### Custodia: HSM y KMS

El objetivo es que la clave **nunca esté en un fichero ni en una variable de entorno**. Un HSM (hardware) o un KMS gestionado (AWS KMS, GCP KMS, Azure Key Vault) guardan la clave y exponen operaciones, no el material: pides "cifra esto" y te devuelven el resultado, pero no puedes exportar la clave.

El patrón habitual con estos servicios es **envelope encryption**: generas una clave de datos aleatoria, cifras los datos con ella localmente (rápido), y pides al KMS que cifre esa clave de datos. Guardas juntos el dato cifrado y la clave de datos cifrada. Para leer, el KMS descifra la clave de datos y tú descifras el contenido. Así solo la clave maestra vive en el KMS y no mandas gigabytes por su API.

## Errores comunes en producción

### Implementar tu propia criptografía

La regla más repetida y la más ignorada. No escribas tu propio cifrado, ni tu propio modo de operación, ni "AES pero con una vuelta extra por si acaso". Los fallos criptográficos no se manifiestan como bugs: el código funciona perfectamente, cifra, descifra, pasa los tests, y es inseguro.

Usa `cryptography` en Python, libsodium en C/C++/Rust, la librería estándar de tu plataforma. Y dentro de esas librerías, prefiere las APIs de alto nivel: `cryptography` separa deliberadamente su capa `hazmat` ("hazardous materials") precisamente porque usarla mal es fácil.

### Modo ECB

Cifrar cada bloque de forma independiente hace que **bloques de texto plano idénticos produzcan bloques cifrados idénticos**. La estructura de los datos se transparenta a través del cifrado: es el ejemplo clásico de la imagen cifrada en ECB en la que se sigue viendo el dibujo. Nunca es la respuesta correcta. Usa AEAD.

### Comparar secretos con `==`

Comparar bytes con el operador habitual sale del bucle en cuanto encuentra una diferencia. El tiempo de ejecución depende de cuántos bytes iniciales coinciden, y un atacante que pueda medirlo reconstruye el valor byte a byte. Aplica a tokens de API, firmas HMAC, códigos de verificación y cookies de sesión.

### Aleatoriedad débil

`random` en Python, `Math.random()` en JavaScript o `rand()` en C son generadores **predecibles** por diseño: están pensados para simulaciones, no para seguridad. Con suficientes salidas observadas se reconstruye el estado interno y se predicen las siguientes. Para cualquier cosa que deba ser impredecible —tokens, nonces, salts, claves, contraseñas temporales, identificadores de sesión— usa un CSPRNG.

```python
import hmac
import secrets

# CORRECTO: CSPRNG. En Linux se alimenta de getrandom()//dev/urandom.
token = secrets.token_urlsafe(32)
clave = secrets.token_bytes(32)

# CORRECTO: comparación en tiempo constante.
def token_valido(recibido: str, esperado: str) -> bool:
    return hmac.compare_digest(recibido, esperado)

# INCORRECTO, para que quede claro qué evitar:
#   import random; token = random.randint(0, 10**12)   # predecible
#   if recibido == esperado:                            # timing attack
```

!!! note "/dev/urandom es la respuesta correcta en Linux"
    La vieja discusión sobre `/dev/random` frente a `/dev/urandom` está resuelta desde hace años en los kernels actuales: `urandom` es criptográficamente seguro una vez el pool se ha inicializado, y no bloquea. El único caso delicado es el arranque temprano de un sistema sin entropía —una VM recién clonada, un dispositivo embebido sin RTC—, y ahí la solución es `getrandom()`, que sí espera a la inicialización. Ver [Hardening de Linux](hardening_linux.md).

### Otros que se repiten

- **Claves en el repositorio o en variables de entorno del Dockerfile.** Quedan en el historial y en las capas de la imagen.
- **Registrar datos sensibles en logs** después de descifrarlos. El cifrado se anula en la línea siguiente.
- **Reutilizar la misma clave para todo.** Deriva subclaves por propósito con HKDF.
- **Confiar en un `Content-Type` o en el nombre del fichero** para decidir si algo está cifrado. Usa un identificador de formato explícito.
- **No verificar la firma** al descifrar porque "ya funciona". Si ignoras el error de autenticación, no tienes AEAD, tienes cifrado sin integridad.

## Tabla de referencia rápida: qué usar para qué

| Necesito... | Usa | No uses | Nota |
| --- | --- | --- | --- |
| Guardar contraseñas de usuarios | Argon2id (o scrypt / bcrypt) | SHA-256, MD5, cifrado reversible | Salt automático; revisa parámetros con OWASP |
| Cifrar datos en reposo en la app | AES-256-GCM o ChaCha20-Poly1305 | AES-CBC sin MAC, ECB | Nonce único por mensaje |
| Cifrar un disco o volumen | LUKS2 / dm-crypt | — | No protege el sistema en caliente |
| Cifrar muchísimos mensajes con una clave | XChaCha20-Poly1305 | AES-GCM con nonce aleatorio | Nonce de 192 bits, sin riesgo de colisión |
| Verificar integridad de un fichero | SHA-256, BLAKE2 | MD5, SHA-1 | Rápido a propósito |
| Autenticar un mensaje con clave compartida | HMAC-SHA256 | Hash de clave concatenada | Comparar con `compare_digest` |
| Firmar (clave pública) | Ed25519 | RSA-1024, DSA | Claves cortas, sin parámetros que romper |
| Clave SSH nueva | Ed25519 | RSA < 3072, DSA, ECDSA | `ssh-keygen -t ed25519` |
| Intercambio de claves | X25519 | DH con grupos pequeños | Base de WireGuard y TLS moderno |
| Derivar clave desde contraseña | Argon2id, scrypt, PBKDF2 | SHA-256 iterado a mano | KDF lenta, con salt |
| Derivar subclaves desde una clave | HKDF | Trocear la clave maestra | Separa dominios con `info` |
| Token de sesión o API | `secrets` / CSPRNG | `random`, timestamps, UUIDv1 | Mínimo 128 bits de entropía |
| Comparar un secreto | `hmac.compare_digest` | `==` | Tiempo constante |
| Proteger tráfico entre servicios | mTLS o WireGuard | Cifrado propio sobre TCP | Ver enlaces relacionados |
| Guardar la clave maestra | KMS / HSM / Vault | Fichero, env var, repo | Envelope encryption |

## Lo que este documento no cubre

Honestidad sobre los límites, para que nadie asuma cobertura que no hay:

- **Configuración de TLS en servidores**, cadenas, ACME y renovación: está entero en [Certificados TLS](../networking/certificados_tls.md).
- **Despliegue de VPNs**: en las guías de [Tailscale](../networking/tailscale.md), [NetBird](../networking/netbird.md) y [migración a mesh](../networking/vpn_to_mesh_migration.md).
- **Herramientas de gestión de secretos**: en [Gestión de Secretos](gestion_secretos.md) y [Secretos en GitOps](secrets_gitops.md).
- **PKI interna y CAs privadas**, firma de código, y criptografía post-cuántica: no están cubiertos en este repositorio a día de hoy.
- **Parámetros numéricos concretos** de Argon2 o de rotación: cambian con el hardware y con el año. Este documento te dice qué medir y dónde mirar, deliberadamente no te da un número que envejezca mal.

## Enlaces relacionados

- [Certificados TLS](../networking/certificados_tls.md) — TLS, cadenas de confianza, Let's Encrypt y configuración segura de servidores.
- [Tailscale](../networking/tailscale.md) y [NetBird](../networking/netbird.md) — VPN mesh sobre WireGuard.
- [Migración de VPN a mesh networking](../networking/vpn_to_mesh_migration.md) — de OpenVPN e IPsec a WireGuard.
- [Gestión de Secretos](gestion_secretos.md) — Vault, AWS Secrets Manager y Kubernetes Secrets.
- [Secretos en GitOps](secrets_gitops.md) — SOPS, Sealed Secrets y External Secrets Operator.
- [Hardening de Linux](hardening_linux.md) — endurecimiento del sistema base.
- [Backup Seguro](backup_seguro.md) — copias cifradas y verificación de restauración.

## Referencias

- [OWASP Cheat Sheet Series](https://cheatsheetseries.owasp.org/) — consulta las hojas de Password Storage y Cryptographic Storage para parámetros actualizados.
- [`cryptography` (Python)](https://cryptography.io/) — librería recomendada, con separación explícita de APIs peligrosas.
- [argon2-cffi](https://argon2-cffi.readthedocs.io/) — enlaces de Python a la implementación de referencia de Argon2.
- [libsodium](https://doc.libsodium.org/) — API de alto nivel difícil de usar mal, con XChaCha20-Poly1305.
- [cryptsetup / LUKS](https://gitlab.com/cryptsetup/cryptsetup) — documentación de referencia de dm-crypt y LUKS.
