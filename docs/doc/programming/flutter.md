---
title: "Flutter en producción — build, firma y distribución"
description: "Qué produce cada objetivo de compilación de Flutter y cómo se opera: build web detrás de un proxy inverso, firma de artefactos móviles con credenciales inyectadas en CI, caché de dependencias, configuración por entorno, observabilidad de errores en cliente y tamaño del artefacto."
keywords: "flutter, dart, build web, flutter build apk, appbundle, keystore, firma android, ci/cd, dart-define, obfuscate, split-debug-info, traefik, docker, distribucion interna"
tags: ['programming', 'ci-cd', 'docker', 'secrets', 'performance']
updated: 2026-09-03
difficulty: intermediate
estimated_time: 30 min
category: Desarrollo
status: published
last_reviewed: 2026-09-03
prerequisites:
  - "SDK de Flutter instalado y un proyecto que compile en local"
  - "[Docker base](../docker/docker_base.md)"
  - "Nociones de CI — [GitHub Actions](../cicd/github_actions.md)"
reviewers: ["@rasty94"]
contributors: ["@rasty94"]
---

# Flutter en producción — build, firma y distribución

## El problema

Aprender Flutter no es el problema: la documentación oficial y media internet lo explican mejor que cualquier cosa que se escriba aquí. El problema aparece el día que la aplicación tiene que salir del emulador.

Ahí llegan las preguntas que ningún tutorial de widgets contesta: qué artefacto sale de cada plataforma y quién puede compilarlo, quién sirve el build web y por qué recargar una ruta interna devuelve 404, dónde vive el keystore que firma el APK y cómo llega al runner sin acabar en el repositorio, cómo apunta la app a tu API sin que la clave sea recuperable descomprimiendo el binario, y por qué un pipeline que compila tres objetivos tarda cuarenta minutos.

Esta página no enseña Flutter. Trata **qué hacer con el resultado de compilarlo** dentro de la infraestructura que documenta el resto del sitio: un contenedor, un proxy inverso, un pipeline y un gestor de secretos.

!!! note "Qué cubre y qué no"
    Aquí no hay widgets, ni Dart, ni gestión de estado: eso está mejor explicado en [docs.flutter.dev](https://docs.flutter.dev/). Lo que hay es el camino desde `flutter build` hasta un artefacto firmado, distribuible y con trazas legibles cuando falle.

!!! warning "Las herramientas de build se mueven rápido"
    Los nombres de flags, los renderizadores web, los plugins de Gradle y los requisitos de firma cambian entre versiones y canales de Flutter. Esta página se queda en conceptos estables a propósito; antes de copiar un comando, contrástalo con `flutter build <objetivo> --help` de **tu** versión.

## 📋 Tabla de Contenidos

- [Qué produce cada objetivo de compilación](#que-produce-cada-objetivo-de-compilacion)
- [El build web y el proxy inverso](#el-build-web-y-el-proxy-inverso)
- [Firma de artefactos móviles y credenciales en CI](#firma-de-artefactos-moviles-y-credenciales-en-ci)
- [Caché de dependencias y builds lentos](#cache-de-dependencias-y-builds-lentos)
- [Configuración por entorno y secretos en el binario](#configuracion-por-entorno-y-secretos-en-el-binario)
- [Observabilidad de errores en cliente](#observabilidad-de-errores-en-cliente)
- [Distribución interna para pruebas](#distribucion-interna-para-pruebas)
- [Tamaño del artefacto](#tamano-del-artefacto)
- [Troubleshooting](#troubleshooting)
- [Buenas prácticas](#buenas-practicas)
- [Referencias](#referencias)

## Qué produce cada objetivo de compilación

"Una sola base de código" es cierto para el código y falso para el pipeline. Cada objetivo produce un artefacto distinto, con requisitos distintos:

| Objetivo | Comando | Qué sale | Qué necesita el runner |
|---|---|---|---|
| Web | `flutter build web` | Ficheros estáticos | Cualquier runner Linux |
| Android (tienda) | `flutter build appbundle` | Un `.aab` firmado | JDK + SDK de Android + keystore |
| Android (directo) | `flutter build apk` | Uno o varios `.apk` firmados | Lo mismo |
| iOS | `flutter build ipa` | Un `.ipa` firmado | macOS + Xcode + certificados |
| Escritorio | `flutter build linux \| macos \| windows` | Binario y bibliotecas | Un runner del mismo sistema operativo |

De esa tabla salen las dos consecuencias que ordenan todo el pipeline:

**No hay compilación cruzada.** iOS y macOS exigen macOS; Windows exige Windows. Un pipeline multiplataforma no es un job, son varios jobs en varios runners — y el de macOS suele ser el caro. Merece la pena que solo se ejecute cuando toca, no en cada push a una rama de trabajo.

**Cada objetivo tiene su propio ciclo de firma y su propio canal.** El web se despliega como cualquier estático y se corrige en minutos; el móvil pasa por firma, y a menudo por una revisión de tienda que tarda horas o días. Esa asimetría condiciona decisiones que parecen de código —como si la URL de la API se compila o se lee al arrancar— y que en realidad son operativas.

!!! note "Las rutas de salida no son un contrato"
    `build/web/` para web y `build/app/outputs/…` para Android son las rutas habituales, pero han cambiado con el tiempo y dependen de la configuración del proyecto. En un `Dockerfile` o en un paso de CI, verifica la ruta real con un `ls` la primera vez en lugar de asumirla.

## El build web y el proxy inverso

El build web es un directorio de ficheros estáticos: HTML, JavaScript, los recursos del renderizador y tus assets. Se sirve exactamente igual que cualquier otra aplicación de página única — el planteamiento completo está en [React en producción](react.md), y aquí solo van las diferencias.

**El enrutado de cliente.** Flutter web puede usar dos estrategias de URL. Con la estrategia de *hash*, las rutas viven detrás de un `#` y el servidor nunca las ve: no hace falta ninguna configuración especial. Con la estrategia de ruta —URLs limpias, que es lo que casi todo el mundo quiere— el servidor sí recibe `/pedidos/42`, donde no hay ningún fichero, y responde 404 al recargar. El arreglo es el *fallback* de siempre:

```nginx
server {
    listen 80;
    root /usr/share/nginx/html;
    index index.html;

    location = /index.html {
        add_header Cache-Control "no-cache" always;
    }
    location / {
        try_files $uri $uri/ /index.html;
    }
}
```

La función que activa esa estrategia de ruta ha cambiado de paquete y de nombre entre versiones de Flutter: búscala en la documentación de la tuya antes de copiar una línea de un blog. Si el arranque falla con un error de importación, casi siempre es eso.

**El service worker y la caché.** El build web incluye un service worker que cachea la aplicación en el navegador. Es una ventaja de arranque y la causa número uno de "he desplegado y los usuarios siguen viendo lo de ayer": si `index.html` y el propio service worker se sirven cacheados, el navegador no llega a enterarse de que hay algo nuevo. La regla es la misma que en cualquier SPA — el índice y el service worker con `no-cache`, los ficheros con nombre versionado con caché larga — y conviene comprobarla con `curl -I` contra el entorno real, no leerla del fichero de configuración.

!!! warning "El renderizador puede traerse recursos de un origen externo"
    Según la versión y el renderizador, el build web descarga parte de su runtime desde un CDN de terceros la primera vez. Eso rompe dos cosas: una **CSP** estricta (el origen no está permitido) y cualquier despliegue sin salida a Internet. Se puede servir desde tu propio dominio, pero el mecanismo exacto —una variable de entorno de build cuyo nombre ha cambiado— depende de la versión: **compruébalo en la documentación de la tuya**. Detecta el caso abriendo la aplicación con la pestaña de red del navegador y mirando si sale tráfico a un dominio que no es el tuyo.

Empaquetado en una imagen, con el mismo multi-stage que cualquier estático:

```dockerfile
# No hay imagen oficial de Flutter: usa una comunitaria fijada por digest
# o instala el SDK en esta etapa. Revisa qué estás ejecutando.
FROM tu-registro/flutter-sdk:pinned AS build
WORKDIR /app
COPY pubspec.* ./
RUN flutter pub get
COPY . .
RUN flutter build web --release

FROM nginx:alpine
COPY --from=build /app/build/web /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
```

Con [Traefik](../traefik/traefik_base.md) delante, el reparto es el habitual: Traefik enruta y termina TLS, el contenedor sirve ficheros y resuelve el fallback.

```yaml
labels:
  - "traefik.enable=true"
  - "traefik.http.routers.app.rule=Host(`app.example.com`)"
  - "traefik.http.routers.app.entrypoints=websecure"
  - "traefik.http.routers.app.tls.certresolver=le"
  - "traefik.http.services.app.loadbalancer.server.port=80"
```

Si sirves la aplicación en una subruta (`https://example.com/app/`), el build necesita saberlo: `flutter build web --base-href /app/`. Sin eso, la página carga en blanco y la consola se llena de 404 de assets, porque el HTML busca los ficheros en la raíz.

## Firma de artefactos móviles y credenciales en CI

Aquí es donde más se sufre, y no por dificultad conceptual: por lo caro que sale equivocarse. Un artefacto móvil sin firmar no se instala. La firma se hace con material privado —un *keystore* en Android, un certificado y un perfil de aprovisionamiento en iOS— que tiene dos propiedades incómodas: **si lo pierdes** puedes quedarte sin poder publicar actualizaciones de esa aplicación, y **si se filtra** cualquiera puede firmar software en tu nombre.

De ahí las tres reglas, en orden de importancia:

1. **El keystore nunca entra en el repositorio.** Ni en una rama vieja, ni "temporalmente", ni cifrado con una contraseña que también está en el repositorio. Un fichero que entra en Git se queda en el historial.
2. **Las contraseñas tampoco.** El fichero de propiedades que las contiene se genera en el runner y se destruye con él.
3. **Existe una copia de seguridad del keystore fuera de CI.** Un secreto de CI no es un almacén: si alguien lo borra, el material desaparece. Guárdalo también en el gestor de secretos de verdad — ver [gestión de secretos](../cybersecurity/gestion_secretos.md).

Lo primero, el `.gitignore`, antes de que sea tarde:

```
android/key.properties
*.jks
*.keystore
ios/**/*.mobileprovision
ios/**/*.p12
```

En Android, la firma se configura mediante un fichero de propiedades que apunta al keystore:

```properties
# android/key.properties — generado en el runner, jamás versionado
storeFile=/ruta/absoluta/al/upload.jks
storePassword=…
keyPassword=…
keyAlias=upload
```

Y en CI, el material se restaura desde secretos justo antes de compilar:

{% raw %}

```yaml
- name: Restaurar el material de firma
  run: |
    echo "$KEYSTORE_B64" | base64 -d > "$RUNNER_TEMP/upload.jks"
    cat > android/key.properties <<EOF
    storeFile=$RUNNER_TEMP/upload.jks
    storePassword=$STORE_PASSWORD
    keyPassword=$KEY_PASSWORD
    keyAlias=upload
    EOF
  env:
    KEYSTORE_B64: ${{ secrets.ANDROID_KEYSTORE_B64 }}
    STORE_PASSWORD: ${{ secrets.ANDROID_STORE_PASSWORD }}
    KEY_PASSWORD: ${{ secrets.ANDROID_KEY_PASSWORD }}
```

{% endraw %}

Detalles que no son cosméticos:

- **El keystore se escribe fuera del workspace.** Si cae dentro, cualquier paso que empaquete el directorio —subir artefactos, construir una imagen con `COPY . .`— se lo lleva puesto.
- **En un runner efímero, el material muere con la máquina.** En uno autoalojado no: hay que borrarlo explícitamente en un paso que se ejecute también cuando el build falla.
- **Base64 no es cifrado.** Se usa porque un secreto de CI transporta texto, no binario. El valor sigue siendo tan sensible como el fichero original.

!!! danger "El log de CI es el sitio donde se filtran las contraseñas"
    Un `set -x` en el script, un `echo` de depuración o una herramienta demasiado habladora imprimen el valor y ahí se queda, visible para quien tenga acceso a las ejecuciones. El enmascarado automático del proveedor ayuda, pero deja de funcionar en cuanto el valor se transforma —se parte, se recodifica, se mete en un JSON—. Si sospechas que un secreto se ha impreso, el procedimiento no es borrar el log: es **rotar la credencial**.

En iOS el material es distinto —certificado de firma más perfil de aprovisionamiento, instalados en un llavero temporal del runner— pero el patrón operativo es idéntico: se inyecta, se usa, se destruye. La diferencia práctica es la **caducidad**: certificados y perfiles expiran, y buena parte de los fallos de firma en iOS son eso, no un error del pipeline. Un aviso en el calendario antes del vencimiento ahorra una mañana entera de depuración equivocada.

## Caché de dependencias y builds lentos

Un build de release compila a código nativo para cada arquitectura y, por debajo, arrastra la cadena de herramientas de la plataforma: Gradle en Android, Xcode en iOS. Es intrínsecamente lento. Lo que **no** tiene por qué ser lento es volver a descargar lo mismo en cada ejecución.

Qué merece la pena cachear:

- **El caché de paquetes de Dart** (`~/.pub-cache`), poblado por `flutter pub get`.
- **El caché de Gradle** (`~/.gradle`) en los objetivos de Android, que suele ser el más grande y el que más tiempo ahorra.
- **El propio SDK de Flutter**, si el pipeline lo instala en vez de partir de una imagen que ya lo trae.

La clave del caché se deriva de los ficheros de bloqueo, no del contenido del repositorio: si no incluye el lockfile, sirves dependencias viejas; si incluye todo, nunca aciertas.

{% raw %}

```yaml
- uses: actions/cache@v4
  with:
    path: |
      ~/.pub-cache
      ~/.gradle/caches
    key: deps-${{ runner.os }}-${{ hashFiles('pubspec.lock') }}
    restore-keys: deps-${{ runner.os }}-
```

{% endraw %}

!!! warning "Cachea descargas, no resultados de compilación"
    Meter `build/`, `.dart_tool/` o los intermedios de Gradle en el caché entre ejecuciones produce fallos raros e irreproducibles: un artefacto compilado con una configuración anterior que sobrevive a un cambio que debería haberlo invalidado. Cuando aparezca un error absurdo que no se reproduce en local, la primera prueba es lanzar el job con el caché limpio.

Y una cosa más que ahorra tardes enteras: **fija la versión del SDK en el pipeline**. Un runner que instala "la última" convierte cualquier lunes en una lotería. El `pubspec.lock` fija las dependencias; la versión de Flutter hay que fijarla aparte, en el propio workflow.

## Configuración por entorno y secretos en el binario

Para que el mismo código apunte a tu API de *staging* o a la de producción, los valores se pasan en la compilación y se leen como constantes de entorno:

```bash
flutter build appbundle --release \
  --dart-define=API_URL=https://api.example.com \
  --dart-define=APP_ENV=prod
```

```dart
const apiUrl = String.fromEnvironment('API_URL', defaultValue: 'http://localhost:8000');
```

Esto tiene la misma consecuencia que en el navegador, y conviene decirla sin rodeos: **lo que se compila dentro del binario es recuperable**. Un `.apk` es un fichero comprimido y el build web es texto. No hace falta nada sofisticado para comprobarlo:

```bash
unzip -o app-release.apk -d apk/
strings apk/lib/*/libapp.so | grep -i 'example.com'
grep -r 'example.com' build/web/
```

!!! danger "Un secreto compilado en la app es un secreto quemado"
    La ofuscación (`--obfuscate`) sube el coste de encontrarlo; no lo elimina. Y aquí es peor que en web: una app instalada no se "vuelve a desplegar" — sigue en los dispositivos de los usuarios hasta que actualicen, y algunos no lo harán nunca.

    Regla práctica idéntica a la del navegador: el cliente solo puede llevar valores públicos (la URL de la API, un *client ID* de OAuth, *feature flags*). Todo lo demás vive detrás de una API propia —por ejemplo una [FastAPI](fastapi.md)— que autentica al usuario y guarda las credenciales del lado del servidor. Si sospechas que se ha publicado un secreto, **rótalo**: rehacer el build no arregla nada.

Hay una alternativa a compilar la configuración: servirla desde un endpoint propio al arrancar. Permite cambiar la URL de la API sin volver a pasar por la tienda, lo cual en móvil no es un detalle menor. A cambio, la aplicación depende de esa llamada para arrancar y necesita un comportamiento definido cuando falla. Es una decisión de arquitectura, no una preferencia de estilo.

## Observabilidad de errores en cliente

Los errores del servidor los ves en tus logs; los del cliente ocurren en un dispositivo que no controlas y sobre el que no vas a hacer `journalctl`. Si no los recoges, no existen: simplemente hay gente que deja de usar la aplicación. Hay dos puntos donde engancharse, y los dos hacen falta: los errores del framework y los errores no capturados fuera de él.

```dart
void main() {
  FlutterError.onError = (details) {
    // enviar al colector, además del comportamiento por defecto
  };
  PlatformDispatcher.instance.onError = (error, stack) {
    // enviar al colector
    return true;
  };
  runApp(const MyApp());
}
```

Adónde se envía es indiferente para lo que aquí importa: un colector autoalojado o gestionado, integrado con el resto de tu [stack de observabilidad](../monitoring/observability_stack.md). Lo que no es indiferente:

**Cada evento tiene que llevar la versión y el número de build.** En móvil conviven versiones antiguas durante semanas. Sin ese dato no distingues un fallo nuevo de uno que corregiste hace un mes y que sigue llegando desde dispositivos sin actualizar.

**Si ofuscas, guarda los símbolos.** Un build ofuscado produce trazas ilegibles; para volver a leerlas hacen falta los ficheros de símbolos de **ese** build exacto:

```bash
flutter build appbundle --release \
  --obfuscate --split-debug-info=build/symbols/"$APP_VERSION"
```

Esos ficheros deben subirse como artefacto del pipeline —o al colector, si lo admite— indexados por versión. Perderlos equivale a perder todas las trazas de esa versión, y no hay forma de recuperarlas después.

**Filtra antes de enviar.** Una traza de cliente arrastra con facilidad rutas, identificadores de usuario o contenido de formularios. Eso es tratamiento de datos personales y también material que no querrías en un tercero.

## Distribución interna para pruebas

En web, "distribuir a testers" es desplegar en otra URL. En móvil no: el sistema operativo decide qué se instala, y ahí las plataformas divergen mucho.

**Android** permite instalar un `.apk` fuera de la tienda. Sirviéndolo por HTTPS detrás de autenticación —un [proxy inverso](../traefik/traefik_base.md) con [Authentik](../identity/authentik.md) delante, por ejemplo— tienes un canal interno propio en una tarde. Dos detalles que se atragantan: el fichero debe servirse con el tipo MIME correcto (`application/vnd.android.package-archive`), y el dispositivo tiene que permitir instalar desde ese origen. Y un aviso importante: si firmas las builds internas con una clave distinta a la de producción, el dispositivo **no** actualizará de una a otra; hay que desinstalar primero.

**iOS** no permite ese flujo. La instalación pasa por perfiles con dispositivos registrados, por el canal de pruebas de Apple o por un programa empresarial, según el caso. Los límites y las reglas cambian con cierta frecuencia: consúltalos antes de prometer un procedimiento a nadie. Las pistas de prueba de las tiendas evitan casi toda esa fricción y añaden la suya propia: cuenta de desarrollador, tiempos de propagación y una subida por cada cambio.

!!! warning "El número de build se genera en el pipeline, no a mano"
    El identificador interno de la subida (`versionCode` en Android, el *build number* en iOS) debe ser único y estrictamente creciente. Si se repite, la tienda rechaza la subida o el dispositivo no ve la actualización. El sitio natural para generarlo es el contador de ejecuciones del pipeline; hacerlo a mano garantiza que algún día se repita justo el día del despliegue importante.

## Tamaño del artefacto

En móvil el tamaño influye en cuánta gente termina la instalación —y hay límites duros por tienda—; en web, en cuánto tarda la aplicación en pintar algo la primera vez. En ambos casos crece solo si nadie mira. Las palancas, en orden de rentabilidad:

1. **Entrega por arquitectura.** Un App Bundle deja que la tienda sirva a cada dispositivo solo su arquitectura y sus recursos. Si distribuyes APK por tu cuenta, `--split-per-abi` genera uno por arquitectura en vez de uno con todas dentro.
2. **Revisar los assets.** Suele ser la causa real: imágenes sin comprimir, fuentes completas por usar dos pesos, ficheros de prueba olvidados en el directorio de recursos. Se auditan en cinco minutos y el ahorro es inmediato.
3. **Compresión en el servidor, en web.** El runtime del renderizador domina la primera carga; servir comprimido es la mejora más barata que existe.

Flutter incluye un análisis de tamaño en el propio build (una opción del estilo `--analyze-size`) que genera un desglose por componentes; el formato del informe y su visor han cambiado entre versiones, así que no automatices su salida sin comprobar antes qué produce la tuya. Y un tope en CI, para que el crecimiento se vea el día que ocurre:

```bash
LIMIT_KB=40000
SIZE_KB=$(du -sk build/app/outputs/bundle/release | cut -f1)
if [ "$SIZE_KB" -gt "$LIMIT_KB" ]; then
  echo "artefacto: $SIZE_KB KB supera el limite de $LIMIT_KB KB"
  exit 1
fi
```

## Troubleshooting

| Síntoma | Causa | Arreglo |
|---|---|---|
| 404 al recargar una ruta del build web | Estrategia de ruta sin fallback en el servidor | `try_files $uri $uri/ /index.html` |
| Página en blanco y 404 de assets en web | Se sirve en una subruta sin base correcta | Reconstruir con `--base-href /sub/` |
| Se despliega y los usuarios ven la versión anterior | `index.html` o el service worker cacheados | `Cache-Control: no-cache` en ambos |
| El build web no arranca con CSP estricta | El renderizador carga recursos de un origen externo | Servirlos desde tu dominio o permitir el origen |
| El build de CI falla al firmar | Falta el keystore o el fichero de propiedades en el runner | Inyectarlos desde secretos antes de compilar |
| La tienda rechaza la subida por la firma | Se subió un artefacto de depuración o firmado con otra clave | Verificar que el build de release usa la firma correcta |
| El dispositivo no actualiza la app instalada | Firma distinta o número de build no mayor | Desinstalar, o incrementar el número de build |
| Trazas de fallo ilegibles | Build ofuscado sin símbolos conservados | Guardar `--split-debug-info` como artefacto por versión |
| Builds de cuarenta minutos | Sin caché de dependencias o SDK descargado cada vez | Cachear `~/.pub-cache` y `~/.gradle` por lockfile |
| Compila en local y falla en CI | Versión de Flutter distinta en cada sitio | Fijar la versión del SDK en el workflow |
| Un valor sensible aparece al descomprimir el APK | Compilado con `--dart-define` | Rotarlo y mover la llamada detrás de la API |
| iOS falla al firmar tras semanas funcionando | Certificado o perfil caducado | Renovarlo y volver a inyectarlo en CI |
| El APK descargado del navegador no se instala | Tipo MIME incorrecto en el servidor | Servirlo como `application/vnd.android.package-archive` |

Antes de depurar nada, comprobar qué está ejecutando realmente el runner y qué está sirviendo realmente el servidor:

```bash
flutter --version                       # version y canal exactos del SDK
flutter doctor -v                       # que cadenas de herramientas ve el runner
unzip -l app-release.apk | tail -5      # que hay dentro del artefacto
curl -sI https://app.example.com/ | grep -i cache-control
```

## Buenas prácticas

- **El material de firma nunca en el repositorio**, siempre inyectado desde secretos, escrito fuera del workspace y con una copia de seguridad fuera de CI. Perder un keystore es un incidente sin arreglo técnico.
- **Nada sensible compilado en el binario.** Un artefacto instalado es público y permanente: si un secreto entra ahí, rótalo.
- **Versión del SDK fijada** en el pipeline y compartida con el entorno local. La mayoría de los "en mi máquina funciona" de Flutter son eso.
- **Cachear descargas, nunca resultados de compilación.** Y saber lanzar el job sin caché cuando algo huele raro.
- **Número de build generado por el pipeline**, único y creciente. A mano se repite, y siempre en el peor momento.
- **Símbolos de depuración archivados por versión** si ofuscas. Sin ellos, las trazas de producción no sirven para nada.
- **Un solo runner de macOS y solo cuando toca.** Es el recurso caro del pipeline; no lo gastes en cada push.
- **Un tope de tamaño en CI.** El artefacto no engorda de golpe, engorda un megabyte por pull request durante un año.

## Referencias

- [Documentación de Flutter](https://docs.flutter.dev/)
- [Flutter — desplegar la app web](https://docs.flutter.dev/deployment/web)
- [Flutter — firma y publicación en Android](https://docs.flutter.dev/deployment/android)
- [Flutter — ofuscación de código Dart](https://docs.flutter.dev/deployment/obfuscate)
- [React en producción](react.md) · [Traefik](../traefik/traefik_base.md) · [Docker base](../docker/docker_base.md)
- [GitHub Actions](../cicd/github_actions.md) · [Gestión de secretos](../cybersecurity/gestion_secretos.md) · [Stack de observabilidad](../monitoring/observability_stack.md)
