---
title: "React en producción — build, despliegue y operación"
description: "Qué produce un build de React y cómo se sirve: fallback de rutas de cliente, variables de entorno en build y en runtime, imagen Docker multi-stage, cabeceras de caché y seguridad, pipeline de CI y control del tamaño del bundle."
keywords: "react, spa, build produccion, nginx try_files, traefik, docker multi-stage, cache-control, csp, bundle size, ci/cd, despliegue"
tags: ['programming', 'docker', 'ci-cd', 'performance']
updated: 2026-09-02
difficulty: intermediate
estimated_time: 20 min
category: Desarrollo
status: published
last_reviewed: 2026-09-02
prerequisites:
  - "Node.js y npm instalados"
  - "[Docker base](../docker/docker_base.md)"
  - "Nociones de proxy inverso — [Traefik](../traefik/traefik_base.md) o [HAProxy](../haproxy/haproxy_base.md)"
reviewers: ["@rasty94"]
contributors: ["@rasty94"]
---

# React en producción — build, despliegue y operación

## El problema

Aprender React no es el problema: hay mil tutoriales mejores que cualquier cosa que se escriba aquí. El problema aparece el día que `npm run dev` deja de bastar y hay que poner *eso* en un servidor.

Entonces salen las preguntas que ningún tutorial de componentes contesta: qué se despliega exactamente, quién sirve esos ficheros, por qué recargar en `/usuarios/42` devuelve un 404 cuando navegar hasta ahí funciona, dónde acaba escrita la URL de la API, y por qué la clave que metiste en un `.env` es ahora pública para siempre.

Esta página no enseña React. Trata **qué hacer con el resultado de compilarlo** dentro de la infraestructura que documenta el resto del sitio: un contenedor, un proxy inverso, un pipeline y unas cabeceras.

!!! note "Qué cubre y qué no"
    Aquí no hay hooks, componentes ni gestión de estado: eso está mejor explicado en [react.dev](https://react.dev/). Lo que hay es el camino desde `npm run build` hasta una URL que responde con TLS, caché correcta y rollback posible.

## 📋 Tabla de Contenidos

- [Qué produce un build de producción](#que-produce-un-build-de-produccion)
- [Servir la SPA y el 404 al recargar](#servir-la-spa-y-el-404-al-recargar)
- [Variables de entorno en build y en runtime](#variables-de-entorno-en-build-y-en-runtime)
- [Imagen Docker multi-stage](#imagen-docker-multi-stage)
- [Cabeceras de caché y de seguridad](#cabeceras-de-cache-y-de-seguridad)
- [Pipeline de CI y despliegue](#pipeline-de-ci-y-despliegue)
- [Tamaño del bundle](#tamano-del-bundle)
- [SPA o renderizado en servidor](#spa-o-renderizado-en-servidor)
- [Troubleshooting](#troubleshooting)
- [Buenas prácticas](#buenas-practicas)
- [Referencias](#referencias)

## Qué produce un build de producción

`npm run build` compila, minifica y escribe un directorio de ficheros estáticos:

```
dist/
├── index.html
├── assets/
│   ├── index-a1b2c3d4.js
│   ├── vendor-e5f6a7b8.js
│   └── index-9c0d1e2f.css
└── favicon.svg
```

Los nombres llevan un hash derivado del contenido: si el fichero cambia, cambia el nombre. Esa propiedad es la que hace posible toda la estrategia de caché de más abajo.

Tres consecuencias operativas:

1. **El resultado es estático.** No hay proceso Node en producción, salvo que uses renderizado en servidor. Cualquier servidor de ficheros vale.
2. **No hay entorno en tiempo de ejecución.** Lo que no estaba en el build no existe después; volveremos a esto.
3. **`index.html` es el único fichero que no puede cachearse.** Es el que apunta a los assets con hash.

!!! note "El directorio de salida depende de la herramienta"
    Vite escribe en `dist/`, Create React App en `build/`, y los frameworks con SSR producen algo bastante distinto (servidor + cliente). El nombre del directorio, el formato del hash y la estructura interna son configurables y cambian entre versiones: mira tu configuración antes de asumir rutas en un `Dockerfile` o en un pipeline.

## Servir la SPA y el 404 al recargar

Una SPA tiene un router **de cliente**. El navegador conoce `/usuarios/42`; el servidor no: ahí no hay ningún fichero. Navegar hasta esa ruta desde la home funciona, porque nunca se pide al servidor. Recargar la página, o entrar por un enlace compartido, devuelve 404.

El arreglo es un *fallback*: cualquier ruta que no corresponda a un fichero real sirve `index.html`, y el router de cliente se encarga desde ahí.

```nginx
server {
    listen 80;
    root /usr/share/nginx/html;
    index index.html;

    # La API, antes del fallback: si no, se la traga index.html
    location /api/ {
        proxy_pass http://backend:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location / {
        try_files $uri $uri/ /index.html;
    }
}
```

`try_files` prueba el fichero, luego el directorio, y si nada existe entrega `index.html`.

!!! warning "El fallback convierte todos tus 404 en 200"
    Con esta configuración, `/rota-que-no-existe` responde 200 con el HTML de la aplicación. Es aceptable para rutas de la SPA, pero significa que una llamada a la API mal escrita ya no devuelve 404 sino HTML — y el error que ves en consola es un `SyntaxError` al parsear JSON, que despista mucho. Por eso el `location /api/` va **antes**, y por eso conviene que la SPA muestre su propia página de "no encontrado" para rutas desconocidas.

Con [Traefik](../traefik/traefik_base.md) delante, el reparto de responsabilidades es claro: **Traefik enruta y termina TLS, no sirve ficheros estáticos**. El contenedor de nginx sigue siendo quien resuelve el fallback.

```yaml
labels:
  - "traefik.enable=true"
  - "traefik.http.routers.web.rule=Host(`app.example.com`)"
  - "traefik.http.routers.web.entrypoints=websecure"
  - "traefik.http.routers.web.tls.certresolver=le"
  - "traefik.http.services.web.loadbalancer.server.port=80"
```

Con [HAProxy](../haproxy/haproxy_base.md) el planteamiento es el mismo: balancea hacia el backend que sirve los estáticos y deja el `try_files` donde está.

## Variables de entorno en build y en runtime

El bundler **sustituye** las variables por su valor durante la compilación. En Vite se leen como `import.meta.env.VITE_API_URL`, en Create React App como `process.env.REACT_APP_API_URL`. El prefijo obligatorio (`VITE_`, `REACT_APP_`) es un filtro deliberado: sin él, cualquier variable del entorno del build acabaría en el navegador.

Dos consecuencias que se pagan caras:

**El artefacto queda atado a un entorno.** Si la URL de la API se hornea en el bundle, el mismo `dist/` no se puede promocionar de *staging* a producción: hay que reconstruir. Eso rompe el principio de "construir una vez, desplegar muchas".

**Todo lo que pongas ahí es público.** No está ofuscado ni protegido: está en un fichero de texto que cualquiera descarga.

```bash
grep -r "MI_VALOR_SECRETO" dist/assets/
```

!!! danger "Un secreto en el bundle es un secreto quemado"
    Rehacer el build no lo arregla. Ese fichero ya está en el navegador de los usuarios, en cachés intermedias y probablemente en un CDN. La única respuesta correcta es **rotar la credencial** y mover la llamada al backend, que sí puede guardarla. Ver [gestión de secretos](../cybersecurity/gestion_secretos.md).

    Regla práctica: el navegador solo puede sostener valores públicos (URLs, *client IDs* de OAuth, *feature flags*). Todo lo demás vive detrás de una API — por ejemplo, una [FastAPI](fastapi.md) que autentica al usuario y habla con el tercero en su nombre.

Si necesitas un artefacto único para todos los entornos, la configuración se inyecta **en tiempo de ejecución**: un fichero pequeño generado al arrancar el contenedor, cargado antes del bundle.

```html
<!-- index.html, antes del script principal -->
<script src="/config.js"></script>
```

```sh
# docker-entrypoint.d/10-config.sh — la imagen oficial de nginx
# ejecuta los scripts de ese directorio antes de arrancar
set -eu
cat > /usr/share/nginx/html/config.js <<EOF
window.APP_CONFIG = { apiUrl: "${API_URL}", env: "${APP_ENV}" };
EOF
```

`config.js` debe servirse con `Cache-Control: no-store`: es lo único que cambia entre despliegues sin cambiar de nombre. Y sigue siendo público — la regla del secreto no cambia, solo cambia el momento de la inyección.

## Imagen Docker multi-stage

```dockerfile
# --- build ---
FROM node:lts-alpine AS build
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

# --- runtime ---
FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
```

Por qué está escrito así:

- **`COPY package*.json` antes que el código.** Si no tocas las dependencias, Docker reutiliza la capa de `npm ci` y el build tarda segundos en lugar de minutos. Más en [optimización de imágenes](../docker/docker_optimizations.md).
- **`npm ci`, no `npm install`.** Instala exactamente lo del *lockfile* y falla si `package.json` y `package-lock.json` no concuerdan. Reproducible por definición.
- **La imagen final no lleva Node.** Ni npm, ni `node_modules`, ni el código fuente: solo ficheros estáticos y un nginx. Menos tamaño y muchísima menos superficie de ataque ([seguridad en Docker](../docker/docker_security.md)).

Un `.dockerignore` no es opcional aquí:

```
node_modules
dist
.git
.env*
```

Sin él, `COPY . .` arrastra los `node_modules` de tu máquina dentro de la imagen — lo que rompe cualquier dependencia con binarios compilados, invalida la caché de capas en cada build y, con `.env`, mete secretos en una capa que queda en el registro para siempre.

## Cabeceras de caché y de seguridad

Los nombres con hash permiten la política más agresiva posible sin riesgo de servir algo viejo:

| Recurso | Cabecera | Motivo |
|---|---|---|
| `index.html` | `Cache-Control: no-cache` | Es el índice: debe revalidarse siempre |
| `/assets/*-hash.js` y `.css` | `Cache-Control: public, max-age=31536000, immutable` | Si cambia, cambia el nombre |
| `config.js` (si lo usas) | `Cache-Control: no-store` | Cambia sin cambiar de nombre |

```nginx
location = /index.html {
    add_header Cache-Control "no-cache" always;
}

location /assets/ {
    add_header Cache-Control "public, max-age=31536000, immutable" always;
}
```

!!! warning "`add_header` no se hereda cuando lo redefines"
    En nginx, un `add_header` dentro de un `location` **anula todos** los heredados de niveles superiores, no los suma. Es la causa habitual de "puse las cabeceras de seguridad en el `server` y en `/assets/` no aparecen". Compruébalo siempre contra el servidor real, no contra el fichero.

Cabeceras de seguridad mínimas para una SPA:

```nginx
add_header X-Content-Type-Options "nosniff" always;
add_header Referrer-Policy "strict-origin-when-cross-origin" always;
add_header Content-Security-Policy "default-src 'self'; img-src 'self' data:; object-src 'none'; frame-ancestors 'none'" always;
```

!!! note "La CSP hay que ajustarla, no copiarla"
    Las directivas exactas dependen de lo que cargue tu aplicación: `connect-src` para el dominio de la API si es distinto, `font-src` si usas fuentes externas, y a menudo excepciones para los estilos o scripts inline que inyecta el propio bundler. Despliega primero con `Content-Security-Policy-Report-Only`, mira lo que se rompería, y solo entonces pasa a modo bloqueo.

HSTS y la terminación TLS van en el proxy, no aquí — ver [certificados TLS](../networking/certificados_tls.md). La compresión, igual: `gzip` en nginx es directo, mientras que Brotli necesita un módulo que no viene en todas las builds; alternativamente, comprime en el build y sirve los ficheros precomprimidos.

## Pipeline de CI y despliegue

El principio que ordena todo lo demás: **construir una vez, desplegar muchas**. El artefacto — una imagen etiquetada con el SHA del commit, o un tarball del directorio de salida — es el mismo en todos los entornos. Si tienes que reconstruir para promocionar, no estás desplegando lo que probaste.

{% raw %}

```yaml
name: build-deploy
on:
  push:
    branches: [main]

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-node@v4
        with:
          node-version-file: .nvmrc
          cache: npm

      - run: npm ci
      - run: npm run lint
      - run: npm test
      - run: npm run build

      - name: Construir y publicar la imagen
        run: |
          IMAGE="registry.example.com/app:${GITHUB_SHA::7}"
          docker build -t "$IMAGE" .
          echo "$REGISTRY_TOKEN" | docker login registry.example.com -u ci --password-stdin
          docker push "$IMAGE"
        env:
          REGISTRY_TOKEN: ${{ secrets.REGISTRY_TOKEN }}
```

{% endraw %}

Detalles que ahorran incidentes:

- **`.nvmrc` compartido** entre CI y `Dockerfile`. La causa número uno de "en local funciona" es una versión de Node distinta en cada sitio.
- **Etiqueta con el SHA, nunca solo `latest`.** El rollback pasa a ser "desplegar la etiqueta anterior" en vez de una arqueología de digests.
- **`npm audit` o un escáner de imagen** en el mismo pipeline: ver [escaneo de seguridad en CI](../cybersecurity/ci_security_scanning.md).
- Si el destino es Kubernetes, el despliegue es cambiar la etiqueta en el manifiesto; con [Argo CD](../cicd/argocd.md) eso es un commit, no un `kubectl apply` desde el runner.

Más sobre el motor de pipelines en [GitHub Actions](../cicd/github_actions.md).

!!! note "Las versiones de las actions envejecen"
    Los `@v4` de arriba son ilustrativos. Fija tú la versión mayor que uses y revísala periódicamente; los cambios de mayor rompen los parámetros.

## Tamaño del bundle

Es la única métrica de rendimiento de una SPA que controlas por completo desde el pipeline. Medirla es trivial:

```bash
du -sh dist/assets
cat dist/assets/*.js | gzip -c | wc -c    # bytes transferidos, aproximado
```

Para saber *qué* ocupa hace falta un analizador. El nombre cambia según el bundler — `rollup-plugin-visualizer` en el ecosistema de Vite, `webpack-bundle-analyzer` en el de webpack, `source-map-explorer` sobre los sourcemaps de cualquiera — pero el uso es siempre el mismo: generas un treemap y buscas el bloque grande que no esperabas.

Cuando crece, en orden de rentabilidad:

1. **División por rutas.** `React.lazy` con `Suspense` saca del bundle inicial las pantallas que no se ven al entrar.
2. **Revisar las dependencias gordas.** Librerías de fechas o de utilidades importadas enteras, paquetes de iconos completos por usar tres, dos librerías que hacen lo mismo porque las metieron personas distintas.
3. **Decidir qué pasa con los sourcemaps.** Publicarlos facilita depurar en producción y expone tu código; no publicarlos convierte cualquier traza en ruido. Decisión consciente, no descuido.

Y un tope en CI, para que el crecimiento sea visible el día que ocurre y no seis meses después:

```bash
LIMIT_KB=600
SIZE_KB=$(du -sk dist | cut -f1)
if [ "$SIZE_KB" -gt "$LIMIT_KB" ]; then
  echo "bundle: ${SIZE_KB} KB supera el límite de ${LIMIT_KB} KB"
  exit 1
fi
```

## SPA o renderizado en servidor

La decisión suele plantearse como técnica de frontend. Operativamente es otra cosa: **el SSR convierte un problema de ficheros en un problema de servicio.**

| | SPA estática | Renderizado en servidor |
|---|---|---|
| Qué despliegas | Ficheros | Un proceso Node |
| Escalado | CDN o nginx, trivial | Réplicas, memoria, límites |
| Fallo típico | 404 al recargar | Proceso caído, fuga de memoria |
| Necesita | Proxy + estáticos | Runtime, [probes](../kubernetes/probes.md), logs |
| Rollback | Cambiar de imagen | Cambiar de imagen y drenar conexiones |
| Coste de guardia | Casi nulo | El de cualquier servicio |

El SSR resuelve problemas reales — SEO, primer pintado en conexiones lentas, contenido que debe existir antes del JavaScript. Pero deja de ser gratis en cuanto se despliega: pasa a necesitar healthchecks, límites de memoria, [observabilidad](../monitoring/observability_stack.md) y, si va a [Kubernetes](../kubernetes/kubernetes_base.md), todo lo que implica un pod que sirve tráfico.

Si nadie ha pedido SEO ni tienes usuarios en redes lentas, la SPA estática es la opción barata, y "barata" aquí significa que no te despierta de madrugada.

## Troubleshooting

| Síntoma | Causa | Arreglo |
|---|---|---|
| 404 al recargar en una ruta interna | No hay fallback a `index.html` | `try_files $uri $uri/ /index.html` |
| Los cambios no se ven tras desplegar | `index.html` cacheado | `Cache-Control: no-cache` en `index.html` |
| Página en blanco y 404 de assets | Ruta base incorrecta al servir en subdirectorio | Ajustar la base pública del bundler y reconstruir |
| `SyntaxError` al parsear JSON de la API | El fallback devuelve HTML en una ruta de API | Declarar el `location /api/` antes del `location /` |
| CORS al llamar a la API | La API está en otro origen | Servirla bajo el mismo dominio vía proxy, o configurar CORS en el backend |
| La CSP bloquea estilos o scripts | Inline generado por el bundler | Probar en `Report-Only` y añadir hash o nonce |
| Build correcto en local, roto en CI | Versión de Node distinta o `node_modules` copiados | `.nvmrc`, `npm ci` y `.dockerignore` |
| Imagen de cientos de MB | Falta el multi-stage o el `.dockerignore` | Copiar solo el directorio de salida al runtime |
| Aparece un secreto en el bundle | Variable con prefijo público | Rotar la credencial y mover la llamada al backend |
| *Mixed content* tras activar TLS | URLs absolutas con `http://` en el código | Rutas relativas, o `https` explícito |

Comprobar lo que realmente sirve el servidor, que casi nunca es lo que dice el fichero de configuración:

```bash
curl -sI https://app.example.com/ | grep -iE 'cache-control|content-security|x-content-type'
curl -sI https://app.example.com/assets/index-a1b2c3d4.js | grep -i cache-control
curl -s -o /dev/null -w '%{http_code}\n' https://app.example.com/ruta/inexistente
```

## Buenas prácticas

- **Un artefacto por commit, etiquetado con el SHA**, promocionado entre entornos sin reconstruir. Si reconstruyes para promocionar, despliegas otra cosa.
- **Nada secreto en el bundle.** Ni claves de API, ni credenciales, ni endpoints internos que preferirías no publicar. El navegador solo guarda valores públicos.
- **Fallback a `index.html`, pero con la API declarada antes.** Y una pantalla de "no encontrado" en la propia SPA.
- **`index.html` sin caché, assets con hash cacheados un año.** Cualquier otra combinación acaba en "borra la caché del navegador" como procedimiento de soporte.
- **Cabeceras verificadas con `curl` contra el entorno real**, no leídas del fichero de configuración.
- **Multi-stage y `.dockerignore` siempre.** Node no pinta nada en la imagen final.
- **Un tope de tamaño en CI.** El bundle no engorda de golpe: engorda 20 KB por pull request durante un año.
- **Antes de meter SSR, cuenta el coste de operarlo.** Es un servicio más, con guardia incluida.

## Referencias

- [Documentación de React](https://react.dev/)
- [Vite — build de producción](https://vite.dev/guide/build.html)
- [nginx — `try_files`](https://nginx.org/en/docs/http/ngx_http_core_module.html#try_files)
- [MDN — `Cache-Control`](https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Cache-Control)
- [MDN — Content Security Policy](https://developer.mozilla.org/en-US/docs/Web/HTTP/CSP)
- [Traefik](../traefik/traefik_base.md) · [HAProxy](../haproxy/haproxy_base.md) · [Docker base](../docker/docker_base.md)
- [GitHub Actions](../cicd/github_actions.md) · [Gestión de secretos](../cybersecurity/gestion_secretos.md) · [FastAPI](fastapi.md)
