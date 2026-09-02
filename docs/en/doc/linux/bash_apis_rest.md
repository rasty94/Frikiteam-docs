---
title: "Bash and REST APIs — curl, jq and scripts that don't lie"
description: "Consuming REST APIs from Bash with curl and jq: real HTTP error handling, pagination, retries with backoff, secrets kept out of the script, and a service checker as a complete example."
keywords: "bash, curl, jq, rest api, scripting, http, retry, backoff, monitoring, shell"
tags: ['linux', 'bash', 'api']
updated: 2026-08-03
difficulty: intermediate
estimated_time: 18 min
category: Linux
status: published
last_reviewed: 2026-08-03
prerequisites:
  - "Basic Bash"
  - "HTTP basics (methods, status codes)"
reviewers: ["@rasty94"]
contributors: ["@rasty94"]
---

# Bash and REST APIs — curl, jq and scripts that don't lie

## The problem

You have twelve services spread across Proxmox, a couple of VPSs and Kubernetes, and checking on them means opening twelve tabs. You write a two-line `curl` script, put it in cron, and for three weeks it tells you everything is fine. Then you discover it had been failing for three weeks: `curl` got a 500, the script never checked the status code, `jq` didn't find the field, printed `null` and exited 0.

A script that queries APIs is easy to write and surprisingly hard to write **so that it fails when it should**. This page is about that second part.

## 📋 Table of Contents

- [The foundation almost nobody lays](#the-foundation-almost-nobody-lays)
- [curl: separating body, status and network errors](#curl-separating-body-status-and-network-errors)
- [jq: what you use 90% of the time](#jq-what-you-use-90-of-the-time)
- [Authentication and secrets](#authentication-and-secrets)
- [Retries and backoff](#retries-and-backoff)
- [Pagination](#pagination)
- [Complete example: a service checker](#complete-example-a-service-checker)
- [When to leave Bash](#when-to-leave-bash)
- [Best practices](#best-practices)
- [References](#references)

## The foundation almost nobody lays

```bash
#!/usr/bin/env bash
set -Eeuo pipefail
```

| Option | What it prevents |
|---|---|
| `-e` | The script carrying on after a failed command |
| `-u` | A typo'd variable expanding to an empty string |
| `-o pipefail` | `failing_cmd \| jq .` returning `jq`'s status (0) and hiding the failure |
| `-E` | Functions not inheriting the `ERR` trap |

`pipefail` is the important one here: **every** API call ends in a pipe into `jq`. Without it, the exit status you see is the last command's in the pipeline, not the one that broke.

!!! warning "`set -e` is not a complete safety net"
    It does not trigger inside conditionals (`if`, `&&`, `||`) or in command substitutions in certain contexts. Check the statuses that matter explicitly; `set -e` is the floor, not the ceiling.

## curl: separating body, status and network errors

The fundamental mistake is treating the response body as if it were the result. There are three distinct things: whether the request arrived, what code it returned, and what it contained.

```bash
api_get() {
    local url=$1
    local body status

    # -s silences the progress bar, -S keeps errors visible
    # --max-time avoids hanging forever
    # -w appends the HTTP code after the body, on its own line
    if ! body=$(curl -sS --max-time 10 -w $'\n%{http_code}' "$url"); then
        echo "network error querying $url" >&2
        return 1
    fi

    status=${body##*$'\n'}   # last line
    body=${body%$'\n'*}      # everything before it

    if [[ $status -lt 200 || $status -ge 300 ]]; then
        echo "HTTP $status on $url: $body" >&2
        return 1
    fi

    printf '%s' "$body"
}
```

Three distinct failures, three treatments:

- **No response** (DNS, timeout, connection refused): `curl` exits non-zero. Without `--max-time`, a server that accepts the connection and never answers hangs your cron job forever.
- **A response, but an error** (4xx/5xx): `curl` still exits 0. That's why you need `-w '%{http_code}'`. The `--fail` alternative is shorter but discards the body, which is exactly where the API explains what you did wrong.
- **A good response**: now you can hand it to `jq`.

## jq: what you use 90% of the time

```bash
# One field
jq -r '.status' <<<"$body"

# Nested field with a default if missing
jq -r '.data.uptime // "unknown"' <<<"$body"

# Filter and project a list
jq -r '.services[] | select(.state != "running") | .name' <<<"$body"

# Several fields as columns (TSV, safe with spaces)
jq -r '.items[] | [.name, .status, .updated] | @tsv' <<<"$body"

# Count
jq '[.items[] | select(.healthy == false)] | length' <<<"$body"
```

`-r` (raw) strips the quotes from the output. Without it you end up with `"running"` including quotes and comparisons that never match — the most common and most annoying bug when driving `jq` from Bash.

The `//` operator supplies a default only when the result is `null` or `false`. It's the difference between a report saying "unknown" and one saying "null".

To know whether a field really exists:

```bash
if jq -e '.data.token' >/dev/null <<<"$body"; then
    echo "token present"
fi
```

`-e` sets the exit status from the result: 1 if `null` or `false`, 4 if there's no output. That is what makes `jq` usable inside an `if`.

## Authentication and secrets

```bash
# BAD: the token lands in your history and in `ps` for every user
curl -H "Authorization: Bearer sk-abc123" https://api.example.com/v1/status
```

A process's arguments are public in `/proc/<pid>/cmdline`. Any user on the system can read that token while the command runs.

```bash
# GOOD: the token never appears on the command line
: "${API_TOKEN:?API_TOKEN missing from the environment}"

curl -sS --max-time 10 \
     -H "@/dev/stdin" \
     https://api.example.com/v1/status <<<"Authorization: Bearer $API_TOKEN"
```

A cleaner alternative when the API accepts basic auth: a `.netrc` file with 600 permissions.

```bash
# ~/.netrc (chmod 600)
machine api.example.com login user password secret
```

```bash
curl -sS --netrc https://api.example.com/v1/status
```

The `${API_TOKEN:?message}` syntax aborts the script with a clear message when the variable is unset. Better than finding out via a 401 three steps later.

For the service's environment file, see [secrets management](../cybersecurity/gestion_secretos.md).

## Retries and backoff

A one-off 503 or timeout shouldn't wake anyone. A 401 is not fixed by retrying.

```bash
api_get_retry() {
    local url=$1 max=${2:-4} attempt=1 wait=2

    while :; do
        if api_get "$url"; then
            return 0
        fi
        if (( attempt >= max )); then
            echo "exhausted $max attempts for $url" >&2
            return 1
        fi
        echo "attempt $attempt failed, retrying in ${wait}s" >&2
        sleep "$wait"
        (( wait *= 2, attempt++ ))
    done
}
```

2s, 4s, 8s: exponential backoff keeps a struggling service from becoming a downed service. Retrying every second is joining the incident.

!!! tip "curl retries on its own"
    For simple cases you don't need the loop:
    ```bash
    curl -sS --retry 4 --retry-delay 2 --retry-all-errors --max-time 10 "$url"
    ```
    `--retry-all-errors` is required because by default `--retry` only covers transient errors, not 5xx. Write the loop only when you need your own logic between attempts.

## Pagination

Almost no API returns everything at once. Two patterns cover nearly all of them:

```bash
# By cursor (GitHub, Stripe): follow until there is no next
cursor=""
while :; do
    body=$(api_get "https://api.example.com/items?limit=100${cursor:+&after=$cursor}")
    jq -r '.items[] | .name' <<<"$body"

    cursor=$(jq -r '.next_cursor // empty' <<<"$body")
    [[ -z $cursor ]] && break
done
```

`// empty` yields an empty string instead of the word `null`, which is what makes the exit condition work.

```bash
# By page: stop when a page comes back empty, not when you think you're done
page=1
while :; do
    body=$(api_get "https://api.example.com/items?page=$page&per_page=100")
    n=$(jq '.items | length' <<<"$body")
    (( n == 0 )) && break
    jq -r '.items[].name' <<<"$body"
    (( page++ ))
done
```

Always add a cap (`(( page > 100 )) && break`): an API that keeps returning the same page turns your script into an infinite loop against someone else's server.

## Complete example: a service checker

It pulls the pieces together: read endpoints from a file, query them in parallel, and exit non-zero when something fails — so cron actually tells you.

{% raw %}

```bash
#!/usr/bin/env bash
# check-services.sh — status of several HTTP endpoints as a table
set -Eeuo pipefail

ENDPOINTS_FILE=${1:-/etc/check-services.list}   # one URL per line, # for comments
TIMEOUT=${TIMEOUT:-5}

check() {
    local url=$1 start end ms code
    start=$(date +%s%3N)
    code=$(curl -so /dev/null -w '%{http_code}' --max-time "$TIMEOUT" "$url" 2>/dev/null) || code="000"
    end=$(date +%s%3N)
    ms=$(( end - start ))

    case $code in
        2*|3*) printf '%s\tOK\t%s\t%sms\n'   "$url" "$code" "$ms" ;;
        000)   printf '%s\tDOWN\tno-response\t%sms\n' "$url" "$ms" ;;
        *)     printf '%s\tFAIL\t%s\t%sms\n' "$url" "$code" "$ms" ;;
    esac
}
export -f check
export TIMEOUT

mapfile -t urls < <(grep -vE '^\s*(#|$)' "$ENDPOINTS_FILE")
(( ${#urls[@]} )) || { echo "no endpoints in $ENDPOINTS_FILE" >&2; exit 2; }

results=$(printf '%s\n' "${urls[@]}" | xargs -P 8 -I{} bash -c 'check "$@"' _ {})
printf '%s\n' "$results" | sort | column -t -s $'\t'   # sort: xargs -P gives no ordering

# Exit status: 1 if anything is not OK — cron only warns when it matters
# Note: $'\t' (Bash ANSI-C quoting) produces a real tab.
# With '\t' in single quotes, grep -E looks for the letter "t" and never matches.
! grep -qE $'\t(FAIL|DOWN)\t' <<<"$results"
```

{% endraw %}

```bash
# Minimal self-check: the script must fail when an endpoint fails
printf 'https://httpbin.org/status/200\nhttps://httpbin.org/status/503\n' > /tmp/ep.list
./check-services.sh /tmp/ep.list && echo "BAD: should have exited 1" || echo "OK: failure detected"
```

`xargs -P 8` gives real parallelism: twelve endpoints with a 5 s timeout take as long as the slowest, not the sum. The last line is the crux — without it the script prints a beautiful table and always exits 0, which is precisely the problem we started with.

## When to leave Bash

Bash is unbeatable for gluing commands and chaining pipes. It stops being so as soon as you hit:

| Signal | Alternative |
|---|---|
| Building complex JSON to send | `jq -n` goes a fair way; beyond that, Python |
| Nested data structures in memory | Python with `requests` |
| Error handling with per-type retries, shared state | Python |
| More than ~150 lines | Python |
| Concurrency beyond `xargs -P` | Python (`asyncio`) or Go |

It isn't dogma: past that point you write more code to work around Bash's limits than to solve the problem. If you already have [FastAPI](../programming/fastapi.md) in the stack, the jump is short.

For genuinely simple cases, write nothing at all: [Uptime Kuma](../monitoring/uptime_kuma.md) does what the example above does, with a UI and notifications.

## Best practices

- **`set -Eeuo pipefail` on the first line.** Always.
- **Check the HTTP status code**, not just that `curl` didn't blow up.
- **`--max-time` on every call.** A hung cron job warns you about nothing.
- **`jq -r` for output into variables**, and `//` for defaults.
- **Secrets via the environment or `.netrc`**, never on the command line.
- **Exponential backoff and a maximum attempt count.**
- **Exit non-zero when something fails.** It is the only thing that makes cron and your monitoring notice.
- **Run `shellcheck`.** It finds 90% of what this page explains, in a second.

```bash
shellcheck check-services.sh
```

## References

- [curl manual](https://curl.se/docs/manpage.html) · [jq manual](https://jqlang.github.io/jq/manual/)
- [ShellCheck](https://www.shellcheck.net/)
- [Quick recipes](../recipes.md) · [Systemd](systemd.md)
- [Uptime Kuma](../monitoring/uptime_kuma.md) · [Secrets management](../cybersecurity/gestion_secretos.md)
