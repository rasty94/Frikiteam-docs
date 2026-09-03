---
title: "React in production — build, deployment and operations"
description: "What a React build produces and how it gets served: client-side route fallback, environment variables at build time and at runtime, multi-stage Docker image, cache and security headers, CI pipeline and keeping the bundle size under control."
keywords: "react, spa, production build, nginx try_files, traefik, docker multi-stage, cache-control, csp, bundle size, ci/cd, deployment"
tags: ['programming', 'docker', 'ci-cd', 'performance']
updated: 2026-09-02
difficulty: intermediate
estimated_time: 20 min
category: Development
status: published
last_reviewed: 2026-09-02
prerequisites:
  - "Node.js and npm installed"
  - "[Docker — Basics](../docker/docker_base.md)"
  - "Reverse proxy basics — [Traefik](../traefik/traefik_base.md) or [HAProxy](../haproxy/haproxy_base.md)"
reviewers: ["@rasty94"]
contributors: ["@rasty94"]
---

# React in production — build, deployment and operations

## The problem

Learning React is not the problem: there are a thousand tutorials better than anything written here. The problem shows up the day `npm run dev` stops being enough and *that thing* has to go on a server.

That is when the questions no component tutorial answers appear: what exactly gets deployed, who serves those files, why a reload on `/users/42` returns a 404 when navigating there works fine, where the API URL ends up written, and why the key you put in a `.env` is now public forever.

This page does not teach React. It covers **what to do with the result of compiling it** inside the infrastructure the rest of this site documents: a container, a reverse proxy, a pipeline and a handful of headers.

!!! note "What this covers and what it doesn't"
    No hooks, components or state management here: [react.dev](https://react.dev/) explains that far better. What you get is the path from `npm run build` to a URL that answers with TLS, correct caching and a rollback you can actually perform.

## 📋 Table of Contents

- [What a production build produces](#what-a-production-build-produces)
- [Serving the SPA and the 404 on reload](#serving-the-spa-and-the-404-on-reload)
- [Environment variables at build time and at runtime](#environment-variables-at-build-time-and-at-runtime)
- [Multi-stage Docker image](#multi-stage-docker-image)
- [Cache and security headers](#cache-and-security-headers)
- [CI pipeline and deployment](#ci-pipeline-and-deployment)
- [Bundle size](#bundle-size)
- [SPA or server-side rendering](#spa-or-server-side-rendering)
- [Troubleshooting](#troubleshooting)
- [Best practices](#best-practices)
- [References](#references)

## What a production build produces

`npm run build` compiles, minifies and writes a directory of static files:

```
dist/
├── index.html
├── assets/
│   ├── index-a1b2c3d4.js
│   ├── vendor-e5f6a7b8.js
│   └── index-9c0d1e2f.css
└── favicon.svg
```

The names carry a hash derived from the content: if the file changes, the name changes. That property is what makes the whole caching strategy below possible.

Three operational consequences:

1. **The result is static.** There is no Node process in production unless you use server-side rendering. Any file server will do.
2. **There is no runtime environment.** Whatever was not in the build does not exist afterwards; we will come back to this.
3. **`index.html` is the only file that cannot be cached.** It is the one pointing at the hashed assets.

!!! note "The output directory depends on the tool"
    Vite writes to `dist/`, Create React App to `build/`, and SSR frameworks produce something quite different (server + client). The directory name, the hash format and the internal structure are configurable and change between versions: check your configuration before assuming paths in a `Dockerfile` or a pipeline.

## Serving the SPA and the 404 on reload

A SPA has a **client-side** router. The browser knows about `/users/42`; the server does not: there is no file there. Navigating to that route from the home page works, because the server is never asked. Reloading the page, or coming in through a shared link, returns a 404.

The fix is a *fallback*: any route that does not map to a real file serves `index.html`, and the client router takes it from there.

```nginx
server {
    listen 80;
    root /usr/share/nginx/html;
    index index.html;

    # The API, before the fallback: otherwise index.html swallows it
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

`try_files` tries the file, then the directory, and if nothing exists it serves `index.html`.

!!! warning "The fallback turns every 404 of yours into a 200"
    With this configuration, `/broken-route-that-does-not-exist` answers 200 with the application's HTML. That is acceptable for SPA routes, but it means a mistyped API call no longer returns a 404 but HTML — and the error you see in the console is a `SyntaxError` while parsing JSON, which is deeply misleading. That is why `location /api/` goes **first**, and why the SPA should show its own "not found" page for unknown routes.

With [Traefik](../traefik/traefik_base.md) in front, the split of responsibilities is clear: **Traefik routes and terminates TLS, it does not serve static files**. The nginx container is still the one resolving the fallback.

```yaml
labels:
  - "traefik.enable=true"
  - "traefik.http.routers.web.rule=Host(`app.example.com`)"
  - "traefik.http.routers.web.entrypoints=websecure"
  - "traefik.http.routers.web.tls.certresolver=le"
  - "traefik.http.services.web.loadbalancer.server.port=80"
```

With [HAProxy](../haproxy/haproxy_base.md) the approach is the same: balance towards the backend serving the static files and leave `try_files` where it is.

## Environment variables at build time and at runtime

The bundler **substitutes** variables for their value during compilation. In Vite they are read as `import.meta.env.VITE_API_URL`, in Create React App as `process.env.REACT_APP_API_URL`. The mandatory prefix (`VITE_`, `REACT_APP_`) is a deliberate filter: without it, any variable in the build environment would end up in the browser.

Two consequences that cost dearly:

**The artifact gets tied to one environment.** If the API URL is baked into the bundle, the same `dist/` cannot be promoted from *staging* to production: you have to rebuild. That breaks the "build once, deploy many times" principle.

**Everything you put there is public.** It is neither obfuscated nor protected: it sits in a text file anyone can download.

```bash
grep -r "MY_SECRET_VALUE" dist/assets/
```

!!! danger "A secret in the bundle is a burned secret"
    Rebuilding does not fix it. That file is already in your users' browsers, in intermediate caches and most likely in a CDN. The only correct answer is to **rotate the credential** and move the call to the backend, which can actually keep it. See [secrets management](../cybersecurity/gestion_secretos.md).

    Rule of thumb: the browser can only hold public values (URLs, OAuth *client IDs*, *feature flags*). Everything else lives behind an API — for example, a [FastAPI](fastapi.md) that authenticates the user and talks to the third party on their behalf.

If you need a single artifact for every environment, the configuration is injected **at runtime**: a small file generated when the container starts, loaded before the bundle.

```html
<!-- index.html, before the main script -->
<script src="/config.js"></script>
```

```sh
# docker-entrypoint.d/10-config.sh — the official nginx image
# runs the scripts in that directory before starting
set -eu
cat > /usr/share/nginx/html/config.js <<EOF
window.APP_CONFIG = { apiUrl: "${API_URL}", env: "${APP_ENV}" };
EOF
```

`config.js` must be served with `Cache-Control: no-store`: it is the only thing that changes between deployments without changing its name. And it is still public — the secret rule does not change, only the moment of injection does.

## Multi-stage Docker image

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

Why it is written this way:

- **`COPY package*.json` before the code.** If you do not touch the dependencies, Docker reuses the `npm ci` layer and the build takes seconds instead of minutes. More in [image optimisation](../docker/docker_optimizations.md).
- **`npm ci`, not `npm install`.** It installs exactly what the *lockfile* says and fails if `package.json` and `package-lock.json` disagree. Reproducible by definition.
- **The final image carries no Node.** No npm, no `node_modules`, no source code: only static files and an nginx. Smaller size and a vastly smaller attack surface ([Docker security](../docker/docker_security.md)).

A `.dockerignore` is not optional here:

```
node_modules
dist
.git
.env*
```

Without it, `COPY . .` drags your machine's `node_modules` into the image — which breaks any dependency with compiled binaries, invalidates the layer cache on every build and, with `.env`, puts secrets into a layer that stays in the registry forever.

## Cache and security headers

Hashed names allow the most aggressive policy possible with no risk of serving something stale:

| Resource | Header | Reason |
|---|---|---|
| `index.html` | `Cache-Control: no-cache` | It is the index: it must always be revalidated |
| `/assets/*-hash.js` and `.css` | `Cache-Control: public, max-age=31536000, immutable` | If it changes, the name changes |
| `config.js` (if you use it) | `Cache-Control: no-store` | It changes without changing its name |

```nginx
location = /index.html {
    add_header Cache-Control "no-cache" always;
}

location /assets/ {
    add_header Cache-Control "public, max-age=31536000, immutable" always;
}
```

!!! warning "`add_header` is not inherited once you redefine it"
    In nginx, an `add_header` inside a `location` **cancels every** header inherited from upper levels, it does not add to them. It is the usual cause of "I set the security headers in `server` and they do not show up under `/assets/`". Always check it against the real server, not against the file.

Minimum security headers for a SPA:

```nginx
add_header X-Content-Type-Options "nosniff" always;
add_header Referrer-Policy "strict-origin-when-cross-origin" always;
add_header Content-Security-Policy "default-src 'self'; img-src 'self' data:; object-src 'none'; frame-ancestors 'none'" always;
```

!!! note "The CSP has to be tuned, not copied"
    The exact directives depend on what your application loads: `connect-src` for the API domain if it differs, `font-src` if you use external fonts, and often exceptions for the inline styles or scripts the bundler itself injects. Deploy first with `Content-Security-Policy-Report-Only`, look at what would break, and only then switch to blocking mode.

HSTS and TLS termination belong in the proxy, not here — see [TLS certificates](../networking/certificados_tls.md). Compression likewise: `gzip` in nginx is straightforward, whereas Brotli needs a module that is not in every build; alternatively, compress at build time and serve the pre-compressed files.

## CI pipeline and deployment

The principle that governs everything else: **build once, deploy many times**. The artifact — an image tagged with the commit SHA, or a tarball of the output directory — is the same in every environment. If you have to rebuild in order to promote, you are not deploying what you tested.

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

      - name: Build and push the image
        run: |
          IMAGE="registry.example.com/app:${GITHUB_SHA::7}"
          docker build -t "$IMAGE" .
          echo "$REGISTRY_TOKEN" | docker login registry.example.com -u ci --password-stdin
          docker push "$IMAGE"
        env:
          REGISTRY_TOKEN: ${{ secrets.REGISTRY_TOKEN }}
```

{% endraw %}

Details that save you incidents:

- **A shared `.nvmrc`** between CI and the `Dockerfile`. The number one cause of "it works on my machine" is a different Node version in each place.
- **Tag with the SHA, never just `latest`.** Rollback becomes "deploy the previous tag" instead of digest archaeology.
- **`npm audit` or an image scanner** in the same pipeline: see [security scanning in CI](../cybersecurity/ci_security_scanning.md).
- If the target is Kubernetes, deploying means changing the tag in the manifest; with [Argo CD](../cicd/argocd.md) that is a commit, not a `kubectl apply` from the runner.

More on the pipeline engine in [GitHub Actions](../cicd/github_actions.md).

!!! note "Action versions age"
    The `@v4` above are illustrative. Pin the major version you use and review it periodically; major changes break the parameters.

## Bundle size

It is the only performance metric of a SPA that you fully control from the pipeline. Measuring it is trivial:

```bash
du -sh dist/assets
cat dist/assets/*.js | gzip -c | wc -c    # transferred bytes, approximate
```

To find out *what* is taking up the space you need an analyser. The name changes with the bundler — `rollup-plugin-visualizer` in the Vite ecosystem, `webpack-bundle-analyzer` in webpack's, `source-map-explorer` on anyone's sourcemaps — but the usage is always the same: you generate a treemap and look for the big block you were not expecting.

When it grows, in order of payoff:

1. **Route-based splitting.** `React.lazy` with `Suspense` pulls the screens you do not see on entry out of the initial bundle.
2. **Review the heavy dependencies.** Date or utility libraries imported whole, full icon packs because three icons are used, two libraries doing the same thing because different people added them.
3. **Decide what happens with sourcemaps.** Publishing them makes debugging in production easier and exposes your code; not publishing them turns any stack trace into noise. A conscious decision, not an oversight.

And a cap in CI, so that growth becomes visible the day it happens and not six months later:

```bash
LIMIT_KB=600
SIZE_KB=$(du -sk dist | cut -f1)
if [ "$SIZE_KB" -gt "$LIMIT_KB" ]; then
  echo "bundle: ${SIZE_KB} KB exceeds the ${LIMIT_KB} KB limit"
  exit 1
fi
```

## SPA or server-side rendering

The decision is usually framed as a frontend technicality. Operationally it is something else: **SSR turns a file problem into a service problem.**

| | Static SPA | Server-side rendering |
|---|---|---|
| What you deploy | Files | A Node process |
| Scaling | CDN or nginx, trivial | Replicas, memory, limits |
| Typical failure | 404 on reload | Crashed process, memory leak |
| Needs | Proxy + static files | Runtime, [probes](../kubernetes/probes.md), logs |
| Rollback | Change the image | Change the image and drain connections |
| On-call cost | Almost none | That of any service |

SSR solves real problems — SEO, first paint on slow connections, content that must exist before the JavaScript. But it stops being free the moment it is deployed: it now needs healthchecks, memory limits, [observability](../monitoring/observability_stack.md) and, if it goes to [Kubernetes](../kubernetes/kubernetes_base.md), everything a traffic-serving pod implies.

If nobody has asked for SEO and you do not have users on slow networks, the static SPA is the cheap option, and "cheap" here means it does not wake you up at night.

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| 404 on reload of an internal route | No fallback to `index.html` | `try_files $uri $uri/ /index.html` |
| Changes not visible after deploying | `index.html` cached | `Cache-Control: no-cache` on `index.html` |
| Blank page and 404s on assets | Wrong base path when serving from a subdirectory | Adjust the bundler's public base and rebuild |
| `SyntaxError` parsing JSON from the API | The fallback returns HTML on an API route | Declare `location /api/` before `location /` |
| CORS when calling the API | The API is on another origin | Serve it under the same domain via proxy, or configure CORS on the backend |
| The CSP blocks styles or scripts | Inline content generated by the bundler | Test in `Report-Only` and add a hash or nonce |
| Build fine locally, broken in CI | Different Node version or copied `node_modules` | `.nvmrc`, `npm ci` and `.dockerignore` |
| Image of hundreds of MB | Missing multi-stage or `.dockerignore` | Copy only the output directory into the runtime |
| A secret shows up in the bundle | Variable with a public prefix | Rotate the credential and move the call to the backend |
| *Mixed content* after enabling TLS | Absolute `http://` URLs in the code | Relative paths, or explicit `https` |

Check what the server actually serves, which is almost never what the configuration file says:

```bash
curl -sI https://app.example.com/ | grep -iE 'cache-control|content-security|x-content-type'
curl -sI https://app.example.com/assets/index-a1b2c3d4.js | grep -i cache-control
curl -s -o /dev/null -w '%{http_code}\n' https://app.example.com/nonexistent/route
```

## Best practices

- **One artifact per commit, tagged with the SHA**, promoted across environments without rebuilding. If you rebuild to promote, you are deploying something else.
- **Nothing secret in the bundle.** No API keys, no credentials, no internal endpoints you would rather not publish. The browser only holds public values.
- **Fallback to `index.html`, but with the API declared first.** And a "not found" screen inside the SPA itself.
- **`index.html` uncached, hashed assets cached for a year.** Any other combination ends with "clear your browser cache" as a support procedure.
- **Headers verified with `curl` against the real environment**, not read off the configuration file.
- **Multi-stage and `.dockerignore`, always.** Node has no business being in the final image.
- **A size cap in CI.** A bundle does not blow up all at once: it puts on 20 KB per pull request for a year.
- **Before adding SSR, count the cost of operating it.** It is one more service, on-call included.

## References

- [React documentation](https://react.dev/)
- [Vite — production build](https://vite.dev/guide/build.html)
- [nginx — `try_files`](https://nginx.org/en/docs/http/ngx_http_core_module.html#try_files)
- [MDN — `Cache-Control`](https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Cache-Control)
- [MDN — Content Security Policy](https://developer.mozilla.org/en-US/docs/Web/HTTP/CSP)
- [Traefik](../traefik/traefik_base.md) · [HAProxy](../haproxy/haproxy_base.md) · [Docker — Basics](../docker/docker_base.md)
- [GitHub Actions](../cicd/github_actions.md) · [Secrets management](../cybersecurity/gestion_secretos.md) · [FastAPI](fastapi.md)
