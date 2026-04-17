---
name: devpy-docker
description: "Use this skill when the user needs to build Docker images, deploy with docker-compose, check container status, or manage Docker-based deployments of LibreFolio."
---

# Docker Operations

## Commands

```bash
./dev.py docker build                  # Build image (git-versioned tag)
./dev.py docker build --tag myimg:v1   # Custom tag
./dev.py docker build --no-cache       # Force full rebuild
./dev.py docker rebuild                # Build + stop + restart (one command)
./dev.py docker up                     # Start containers (detached)
./dev.py docker up --no-detach         # Start in foreground
./dev.py docker down                   # Stop containers
./dev.py docker logs                   # View logs
./dev.py docker logs -f                # Follow logs
./dev.py docker logs -n 100            # Last N lines
./dev.py docker status                 # Container status
```

## Image Tagging

Tags are auto-generated from git:
- On a tag: `librefolio:v1.2.3`
- After commits: `librefolio:v1.2.3-5-gabcdef`
- No tags: `librefolio:v0.0.0-gabcdef`
- Dirty on exact tag is **suppressed** (build artifacts cause false dirty)

The `latest` tag is always applied alongside the versioned tag.

## Pre-Build Steps

`docker build` automatically ensures:
1. Frontend build is up-to-date
2. MkDocs build is up-to-date
3. JS library cache is refreshed
4. `requirements.txt` is generated from `Pipfile.lock`

## Docker Compose

`docker-compose.yml` uses the `librefolio:latest` image. Requires `.env` file (copy from `.env.example`).

## Dockerfile Architecture

Single-image runtime: Python 3.13-slim with pre-built frontend and docs copied in. No Node.js in the image — frontend is built on host.

```text
Dockerfile flow:
  python:3.13-slim → pip install requirements.txt
  → COPY backend/, scripts/, dev.py
  → COPY frontend/build/, mkdocs_src/site/
  → uvicorn backend.app.main:app
```

