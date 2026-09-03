---
title: "Flutter in production — build, signing and distribution"
description: "What each Flutter build target produces and how it is operated: web build behind a reverse proxy, mobile artifact signing with credentials injected in CI, dependency caching, per-environment configuration, client-side error observability and artifact size."
keywords: "flutter, dart, web build, flutter build apk, appbundle, keystore, android signing, ci/cd, dart-define, obfuscate, split-debug-info, traefik, docker, internal distribution"
tags: ['programming', 'ci-cd', 'docker', 'secrets', 'performance']
updated: 2026-09-03
difficulty: intermediate
estimated_time: 20 min
category: Development
status: published
last_reviewed: 2026-09-03
prerequisites:
  - "Flutter SDK installed and a project that builds locally"
  - "[Docker — Basics](../docker/docker_base.md)"
  - "CI basics — [GitHub Actions](../cicd/github_actions.md)"
reviewers: ["@rasty94"]
contributors: ["@rasty94"]
---

# Flutter in production — build, signing and distribution

## The problem

Learning Flutter is not the problem: the official documentation and half the internet explain it better than anything written here. The problem shows up the day the application has to leave the emulator.

That is when the questions no widget tutorial answers appear: which artifact comes out of each platform and who is allowed to build it, who serves the web build and why reloading an internal route returns a 404, where the keystore that signs the APK lives and how it reaches the runner without ending up in the repository, how the app points at your API without the key being recoverable by unzipping the binary, and why a pipeline building three targets takes forty minutes.

This page does not teach Flutter. It covers **what to do with the result of compiling it** inside the infrastructure the rest of this site documents: a container, a reverse proxy, a pipeline and a secrets manager.

!!! note "What this covers and what it doesn't"
    No widgets, no Dart, no state management here: [docs.flutter.dev](https://docs.flutter.dev/) explains that far better. What you get is the path from `flutter build` to an artifact that is signed, distributable and produces readable stack traces when it fails.

!!! warning "Build tooling moves fast"
    Flag names, web renderers, Gradle plugins and signing requirements change between Flutter versions and channels. This page deliberately sticks to stable concepts; before copying a command, check it against `flutter build <target> --help` on **your** version.

## 📋 Table of Contents

- [What each build target produces](#what-each-build-target-produces)
- [The web build and the reverse proxy](#the-web-build-and-the-reverse-proxy)
- [Mobile artifact signing and credentials in CI](#mobile-artifact-signing-and-credentials-in-ci)
- [Dependency caching and slow builds](#dependency-caching-and-slow-builds)
- [Per-environment configuration and secrets in the binary](#per-environment-configuration-and-secrets-in-the-binary)
- [Client-side error observability](#client-side-error-observability)
- [Internal distribution for testing](#internal-distribution-for-testing)
- [Artifact size](#artifact-size)
- [Troubleshooting](#troubleshooting)
- [Best practices](#best-practices)
- [References](#references)

## What each build target produces

"A single codebase" is true for the code and false for the pipeline. Each target produces a different artifact, with different requirements:

| Target | Command | What comes out | What the runner needs |
|---|---|---|---|
| Web | `flutter build web` | Static files | Any Linux runner |
| Android (store) | `flutter build appbundle` | A signed `.aab` | JDK + Android SDK + keystore |
| Android (direct) | `flutter build apk` | One or several signed `.apk` | The same |
| iOS | `flutter build ipa` | A signed `.ipa` | macOS + Xcode + certificates |
| Desktop | `flutter build linux \| macos \| windows` | Binary and libraries | A runner on the same operating system |

Two consequences come out of that table, and they govern the whole pipeline:

**There is no cross-compilation.** iOS and macOS demand macOS; Windows demands Windows. A multi-platform pipeline is not one job, it is several jobs on several runners — and the macOS one is usually the expensive one. It is worth making sure it only runs when it has to, not on every push to a working branch.

**Each target has its own signing cycle and its own channel.** The web build deploys like any other static site and gets fixed in minutes; mobile goes through signing, and often a store review that takes hours or days. That asymmetry drives decisions that look like code decisions — such as whether the API URL is compiled in or read at startup — and are really operational ones.

!!! note "Output paths are not a contract"
    `build/web/` for web and `build/app/outputs/…` for Android are the usual paths, but they have changed over time and depend on the project configuration. In a `Dockerfile` or a CI step, verify the real path with an `ls` the first time instead of assuming it.

## The web build and the reverse proxy

The web build is a directory of static files: HTML, JavaScript, the renderer's resources and your assets. It is served exactly like any other single-page application — the full approach is in [React in production](react.md), and only the differences go here.

**Client-side routing.** Flutter web can use two URL strategies. With the *hash* strategy, routes live behind a `#` and the server never sees them: no special configuration is needed. With the path strategy — clean URLs, which is what almost everyone wants — the server does receive `/orders/42`, where no file exists, and answers 404 on reload. The fix is the usual *fallback*:

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

The function that enables that path strategy has changed package and name between Flutter versions: look it up in the documentation for yours before copying a line from a blog. If startup fails with an import error, that is almost always it.

**The service worker and caching.** The web build includes a service worker that caches the application in the browser. It is a startup advantage and the number one cause of "I deployed and users still see yesterday's version": if `index.html` and the service worker itself are served cached, the browser never finds out there is something new. The rule is the same as for any SPA — the index and the service worker with `no-cache`, versioned filenames with long caching — and it is worth checking with `curl -I` against the real environment rather than reading it off the configuration file.

!!! warning "The renderer may pull resources from an external origin"
    Depending on the version and the renderer, the web build downloads part of its runtime from a third-party CDN the first time. That breaks two things: a strict **CSP** (the origin is not allowed) and any deployment without Internet access. It can be served from your own domain, but the exact mechanism — a build environment variable whose name has changed — depends on the version: **check it in the documentation for yours**. Spot the case by opening the application with the browser's network tab and looking for traffic to a domain that is not yours.

Packaged into an image, with the same multi-stage as any static site:

```dockerfile
# There is no official Flutter image: use a community one pinned by digest
# or install the SDK in this stage. Know what you are running.
FROM your-registry/flutter-sdk:pinned AS build
WORKDIR /app
COPY pubspec.* ./
RUN flutter pub get
COPY . .
RUN flutter build web --release

FROM nginx:alpine
COPY --from=build /app/build/web /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
```

With [Traefik](../traefik/traefik_base.md) in front, the split is the usual one: Traefik routes and terminates TLS, the container serves files and resolves the fallback.

```yaml
labels:
  - "traefik.enable=true"
  - "traefik.http.routers.app.rule=Host(`app.example.com`)"
  - "traefik.http.routers.app.entrypoints=websecure"
  - "traefik.http.routers.app.tls.certresolver=le"
  - "traefik.http.services.app.loadbalancer.server.port=80"
```

If you serve the application under a subpath (`https://example.com/app/`), the build needs to know: `flutter build web --base-href /app/`. Without it the page loads blank and the console fills with 404s on assets, because the HTML looks for the files at the root.

## Mobile artifact signing and credentials in CI

This is where it hurts most, and not because it is conceptually hard: because getting it wrong is expensive. An unsigned mobile artifact will not install. Signing uses private material — a *keystore* on Android, a certificate and a provisioning profile on iOS — with two uncomfortable properties: **if you lose it** you can end up unable to publish updates for that application, and **if it leaks** anyone can sign software in your name.

Hence the three rules, in order of importance:

1. **The keystore never enters the repository.** Not on an old branch, not "temporarily", not encrypted with a password that is also in the repository. A file that enters Git stays in the history.
2. **Neither do the passwords.** The properties file holding them is generated on the runner and destroyed with it.
3. **A backup of the keystore exists outside CI.** A CI secret is not a vault: if someone deletes it, the material is gone. Keep it in a real secrets manager too — see [secrets management](../cybersecurity/gestion_secretos.md).

First things first, the `.gitignore`, before it is too late:

```
android/key.properties
*.jks
*.keystore
ios/**/*.mobileprovision
ios/**/*.p12
```

On Android, signing is configured through a properties file pointing at the keystore:

```properties
# android/key.properties — generated on the runner, never versioned
storeFile=/absolute/path/to/upload.jks
storePassword=…
keyPassword=…
keyAlias=upload
```

And in CI, the material is restored from secrets right before building:

{% raw %}

```yaml
- name: Restore the signing material
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

Details that are not cosmetic:

- **The keystore is written outside the workspace.** If it lands inside, any step that packages the directory — uploading artifacts, building an image with `COPY . .` — takes it along.
- **On an ephemeral runner the material dies with the machine.** On a self-hosted one it does not: it has to be deleted explicitly, in a step that also runs when the build fails.
- **Base64 is not encryption.** It is used because a CI secret carries text, not binary. The value is still exactly as sensitive as the original file.

!!! danger "The CI log is where passwords leak"
    A `set -x` in the script, a debug `echo` or an overly talkative tool prints the value and there it stays, visible to anyone with access to the runs. The provider's automatic masking helps, but it stops working the moment the value is transformed — split, re-encoded, wrapped in JSON. If you suspect a secret has been printed, the procedure is not to delete the log: it is to **rotate the credential**.

On iOS the material is different — a signing certificate plus a provisioning profile, installed into a temporary keychain on the runner — but the operational pattern is identical: inject, use, destroy. The practical difference is **expiry**: certificates and profiles expire, and a good share of iOS signing failures are exactly that, not a pipeline bug. A calendar reminder ahead of the expiry date saves a whole morning of debugging the wrong thing.

## Dependency caching and slow builds

A release build compiles to native code for each architecture and, underneath, drags in the platform toolchain: Gradle on Android, Xcode on iOS. It is inherently slow. What does **not** have to be slow is downloading the same things again on every run.

What is worth caching:

- **The Dart package cache** (`~/.pub-cache`), populated by `flutter pub get`.
- **The Gradle cache** (`~/.gradle`) on Android targets, usually the biggest one and the one that saves the most time.
- **The Flutter SDK itself**, if the pipeline installs it instead of starting from an image that already ships it.

The cache key derives from the lock files, not from the repository content: if it does not include the lockfile you serve stale dependencies; if it includes everything you never get a hit.

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

!!! warning "Cache downloads, not compilation output"
    Putting `build/`, `.dart_tool/` or Gradle intermediates into the cache between runs produces weird, irreproducible failures: an artifact compiled with an earlier configuration surviving a change that should have invalidated it. When an absurd error appears that does not reproduce locally, the first test is to run the job with a clean cache.

And one more thing that saves entire afternoons: **pin the SDK version in the pipeline**. A runner installing "the latest" turns any Monday into a lottery. `pubspec.lock` pins the dependencies; the Flutter version has to be pinned separately, in the workflow itself.

## Per-environment configuration and secrets in the binary

To make the same code point at your staging API or your production one, values are passed at build time and read as environment constants:

```bash
flutter build appbundle --release \
  --dart-define=API_URL=https://api.example.com \
  --dart-define=APP_ENV=prod
```

```dart
const apiUrl = String.fromEnvironment('API_URL', defaultValue: 'http://localhost:8000');
```

This has the same consequence as in the browser, and it is worth saying plainly: **whatever is compiled into the binary is recoverable**. An `.apk` is a compressed file and the web build is text. Nothing sophisticated is needed to check it:

```bash
unzip -o app-release.apk -d apk/
strings apk/lib/*/libapp.so | grep -i 'example.com'
grep -r 'example.com' build/web/
```

!!! danger "A secret compiled into the app is a burned secret"
    Obfuscation (`--obfuscate`) raises the cost of finding it; it does not remove it. And here it is worse than on the web: an installed app does not get "redeployed" — it stays on your users' devices until they update, and some never will.

    The rule of thumb is identical to the browser one: the client can only carry public values (the API URL, an OAuth *client ID*, *feature flags*). Everything else lives behind an API of your own — a [FastAPI](fastapi.md), for instance — that authenticates the user and keeps the credentials server-side. If you suspect a secret has shipped, **rotate it**: rebuilding fixes nothing.

There is an alternative to compiling the configuration in: serving it from an endpoint of your own at startup. It lets you change the API URL without going through the store again, which on mobile is not a minor detail. In exchange, the application depends on that call to start and needs defined behaviour when it fails. That is an architecture decision, not a style preference.

## Client-side error observability

Server errors show up in your logs; client errors happen on a device you do not control and will not be running `journalctl` on. If you do not collect them, they do not exist: there are simply people who stop using the application. There are two places to hook in, and both are needed: framework errors and uncaught errors outside it.

```dart
void main() {
  FlutterError.onError = (details) {
    // send to the collector, on top of the default behaviour
  };
  PlatformDispatcher.instance.onError = (error, stack) {
    // send to the collector
    return true;
  };
  runApp(const MyApp());
}
```

Where it is sent does not matter for what concerns us here: a self-hosted or managed collector, wired into the rest of your [observability stack](../monitoring/observability_stack.md). What does matter:

**Every event has to carry the version and the build number.** On mobile, old versions coexist for weeks. Without that field you cannot tell a new failure from one you fixed a month ago that keeps arriving from devices that never updated.

**If you obfuscate, keep the symbols.** An obfuscated build produces unreadable stack traces; reading them back requires the symbol files from **that** exact build:

```bash
flutter build appbundle --release \
  --obfuscate --split-debug-info=build/symbols/"$APP_VERSION"
```

Those files should be uploaded as a pipeline artifact — or to the collector, if it accepts them — indexed by version. Losing them means losing every stack trace for that version, and there is no way to recover them afterwards.

**Filter before sending.** A client stack trace easily drags along paths, user identifiers or form contents. That is personal data processing, and also material you would rather not hand to a third party.

## Internal distribution for testing

On the web, "distributing to testers" means deploying to another URL. On mobile it does not: the operating system decides what gets installed, and the platforms diverge sharply there.

**Android** allows installing an `.apk` outside the store. Serving it over HTTPS behind authentication — a [reverse proxy](../traefik/traefik_base.md) with [Authentik](../identity/authentik.md) in front, for example — gives you your own internal channel in an afternoon. Two details that trip people up: the file must be served with the right MIME type (`application/vnd.android.package-archive`), and the device has to allow installing from that source. And an important warning: if you sign internal builds with a different key than production, the device will **not** update from one to the other; it has to be uninstalled first.

**iOS** does not allow that flow. Installation goes through profiles with registered devices, Apple's testing channel or an enterprise programme, depending on the case. The limits and rules change fairly often: check them before promising anyone a procedure. Store testing tracks avoid almost all of that friction and add their own: a developer account, propagation times and one upload per change.

!!! warning "The build number is generated by the pipeline, not by hand"
    The internal upload identifier (`versionCode` on Android, the *build number* on iOS) must be unique and strictly increasing. If it repeats, the store rejects the upload or the device does not see the update. The natural place to generate it is the pipeline's run counter; doing it by hand guarantees that one day it repeats, exactly on the day of the important release.

## Artifact size

On mobile, size affects how many people finish the install — and there are hard store limits; on the web, how long the application takes to paint something the first time. In both cases it grows on its own if nobody looks. The levers, in order of payoff:

1. **Per-architecture delivery.** An App Bundle lets the store serve each device only its architecture and its resources. If you distribute APKs yourself, `--split-per-abi` produces one per architecture instead of one with all of them inside.
2. **Review the assets.** That is usually the real cause: uncompressed images, full font families for two weights, test files forgotten in the resources directory. They take five minutes to audit and the saving is immediate.
3. **Server-side compression, on the web.** The renderer runtime dominates the first load; serving it compressed is the cheapest improvement there is.

Flutter ships a size analysis in the build itself (an option along the lines of `--analyze-size`) that produces a per-component breakdown; the report format and its viewer have changed between versions, so do not automate its output without first checking what yours produces. And a cap in CI, so growth becomes visible the day it happens:

```bash
LIMIT_KB=40000
SIZE_KB=$(du -sk build/app/outputs/bundle/release | cut -f1)
if [ "$SIZE_KB" -gt "$LIMIT_KB" ]; then
  echo "artifact: $SIZE_KB KB exceeds the $LIMIT_KB KB limit"
  exit 1
fi
```

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| 404 on reload of a web build route | Path strategy with no fallback on the server | `try_files $uri $uri/ /index.html` |
| Blank page and 404s on assets on the web | Served under a subpath without the right base | Rebuild with `--base-href /sub/` |
| You deploy and users see the previous version | `index.html` or the service worker cached | `Cache-Control: no-cache` on both |
| The web build does not start under a strict CSP | The renderer loads resources from an external origin | Serve them from your domain or allow the origin |
| The CI build fails while signing | Keystore or properties file missing on the runner | Inject them from secrets before building |
| The store rejects the upload over signing | A debug artifact was uploaded, or one signed with another key | Verify the release build uses the right signing config |
| The device will not update the installed app | Different signature or a build number that is not higher | Uninstall, or increment the build number |
| Unreadable crash stack traces | Obfuscated build with no symbols kept | Keep `--split-debug-info` as an artifact per version |
| Forty-minute builds | No dependency cache, or the SDK downloaded every time | Cache `~/.pub-cache` and `~/.gradle` by lockfile |
| Builds locally, fails in CI | Different Flutter version in each place | Pin the SDK version in the workflow |
| A sensitive value shows up when unzipping the APK | Compiled in with `--dart-define` | Rotate it and move the call behind the API |
| iOS fails to sign after weeks of working | Expired certificate or profile | Renew it and inject it into CI again |
| The APK downloaded from the browser will not install | Wrong MIME type on the server | Serve it as `application/vnd.android.package-archive` |

Before debugging anything, check what the runner is actually running and what the server is actually serving:

```bash
flutter --version                       # exact SDK version and channel
flutter doctor -v                       # which toolchains the runner sees
unzip -l app-release.apk | tail -5      # what is inside the artifact
curl -sI https://app.example.com/ | grep -i cache-control
```

## Best practices

- **Signing material never in the repository**, always injected from secrets, written outside the workspace and backed up outside CI. Losing a keystore is an incident with no technical fix.
- **Nothing sensitive compiled into the binary.** An installed artifact is public and permanent: if a secret gets in there, rotate it.
- **SDK version pinned** in the pipeline and shared with the local environment. Most Flutter "works on my machine" cases are exactly that.
- **Cache downloads, never compilation output.** And know how to run the job without the cache when something smells off.
- **Build number generated by the pipeline**, unique and increasing. By hand it repeats, always at the worst possible moment.
- **Debug symbols archived per version** if you obfuscate. Without them, production stack traces are worthless.
- **One macOS runner, and only when needed.** It is the expensive resource in the pipeline; do not spend it on every push.
- **A size cap in CI.** The artifact does not blow up all at once, it puts on a megabyte per pull request for a year.

## References

- [Flutter documentation](https://docs.flutter.dev/)
- [Flutter — deploying the web app](https://docs.flutter.dev/deployment/web)
- [Flutter — Android signing and publishing](https://docs.flutter.dev/deployment/android)
- [Flutter — obfuscating Dart code](https://docs.flutter.dev/deployment/obfuscate)
- [React in production](react.md) · [Traefik](../traefik/traefik_base.md) · [Docker — Basics](../docker/docker_base.md)
- [GitHub Actions](../cicd/github_actions.md) · [Secrets management](../cybersecurity/gestion_secretos.md) · [Observability stack](../monitoring/observability_stack.md)
