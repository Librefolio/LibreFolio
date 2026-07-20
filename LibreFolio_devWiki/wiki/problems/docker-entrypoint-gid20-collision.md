---
title: "Docker entrypoint chown fails on macOS: GID 20 collides with Debian's dialout"
category: problem
status: open
date: 2026-07-20
tags: [docker, deployment, macos, entrypoint, gid, permissions]
related: [decisions/single-docker-image]
---

# Problem: Docker entrypoint chown fails on macOS (GID 20 collides with `dialout`)

## Symptom
`docker run`/`docker compose up` on the built `librefolio` image fails at
startup:
```
chown: invalid group: 'librefolio:librefolio'
```
from `entrypoint.sh`. Does **not** reproduce on typical Linux hosts.

## Root Cause
`dev.py` passes the *host's* UID/GID as Docker build args
(`--build-arg UID=$(os.getuid()) --build-arg GID=$(os.getgid())`, both in
the direct `docker build` call and via `docker-compose.yml`'s
`build.args`), intended to align bind-mount file permissions with the
host user.

`Dockerfile` (`python:3.13-slim`, Debian-based) then runs:
```dockerfile
groupadd -g ${GID} librefolio 2>/dev/null || true
```
On **macOS**, the default first-user GID is **20** ("staff"). Debian's
base image already defines GID 20 as `dialout` (`getent group 20` →
`dialout:x:20:`). `groupadd -g 20 librefolio` therefore fails silently
(masked by `|| true`) — a group literally named `librefolio` never gets
created; GID 20 only exists under the name `dialout`.

`useradd` still succeeds (a numeric GID doesn't need a matching literal
name), so the image builds fine and looks correct. The failure only
surfaces at **container runtime**, in `entrypoint.sh`:
```bash
chown -R "$TARGET_USER:$TARGET_USER" "$DATA_DIR"   # TARGET_USER defaults to "librefolio"
```
`chown` needs the literal group *name* `librefolio` to resolve — it
doesn't exist, so this fails and the container never starts.

**This affects most macOS Docker Desktop users** following the
documented `./dev.py docker build` / `docker compose up` workflow, since
GID 20 is the default primary group for the first user account on macOS.
It would not reproduce on typical Linux hosts (default GID 1000, unused
in the Debian base image).

## Suggested Fix (NOT yet applied — needs approval, unrelated to the task that discovered it)
`Dockerfile`, change:
```dockerfile
groupadd -g ${GID} librefolio 2>/dev/null || true
```
to:
```dockerfile
groupadd -o -g ${GID} librefolio 2>/dev/null || true
```
The `-o`/`--non-unique` flag allows creating a **new** group literally
named `librefolio` that shares GID 20 with `dialout` — `chown
librefolio:librefolio` then resolves the name correctly. Single-line
change.

## Workaround used for verification only (not shipped)
```bash
docker run -d -p 6043:6040 --entrypoint sh librefolio:latest \
  -c "mkdir -p /app/backend/data/prod-docker && exec uvicorn backend.app.main:app --host 0.0.0.0 --port 6040"
```
Bypasses `entrypoint.sh` entirely and runs as root (no chown needed) —
useful for ad-hoc verification of unrelated features inside the
container, but not a real fix.

## How it was found
Discovered while verifying the fix in
[[problems/docker-system-info-missing-deps]] on a Mac host — unrelated to
that task, flagged separately per the "report, don't silently fix
unrelated bugs" workflow rule rather than folding an unrelated Dockerfile
change into that PR.

## Source files

| Role | Path |
|------|------|
| Group/user creation (bug) | `Dockerfile` (`groupadd -g ${GID} librefolio`, ~line 65) |
| Runtime chown (failure site) | `entrypoint.sh` (`chown -R "$TARGET_USER:$TARGET_USER" "$DATA_DIR"`) |
| UID/GID build args source | `dev.py` (`docker build`/`docker rebuild` commands), `docker-compose.yml` (`build.args`) |
