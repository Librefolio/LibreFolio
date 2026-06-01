---
title: "Port 60/40 Scheme (6040/6041/6042)"
category: decision
status: Resolved
date: 2026-05-27
tags: [infrastructure, ports, developer-ergonomics, mnemonic]
related:
  - features/F-062
  - features/F-064
  - decisions/single-docker-image
---

# Decision: Port 60/40 Scheme

## Context
LibreFolio previously used ports 8000 (prod), 8001 (test), 8002 (mkdocs). These are generic/commonly-used ports that easily conflict with other local services and are not memorable.

## Decision
Migrate all port defaults to **6040** (prod), **6041** (test), **6042** (docs).

## Rationale
The **"60/40 rule"** — 60% equities, 40% bonds — is the iconic asset allocation principle in finance. For a portfolio tracking application, these port numbers are:
1. **Instantly memorable** for anyone in the investment domain
2. **Unlikely to conflict** with other services (not a common default)
3. **Consistent**: sequential `+1` for test, `+2` for docs

## Alternatives considered
- **8000 series** (status quo): too generic, conflicts with Django/other FastAPI apps
- **5000 series**: commonly used by Flask, Node dev servers
- **3000 series**: React/Next.js default
- **Random high ports**: not memorable

## Impact
- All configuration files updated: `.env.example`, `config.py`, `dev.py`, `Dockerfile`, `docker-compose.yml`
- All E2E test files updated to use 6041
- Documentation and skills updated
- **Zero runtime behavior change** — purely a default port renaming

## Source files

| Role | Path |
|------|------|
| Config defaults | `backend/app/config.py` |
| Docker compose | `docker-compose.yml` |
| Dockerfile | `Dockerfile` |
| Dev CLI | `dev.py` |
| Env template | `.env.example` |
| E2E global setup | `frontend/e2e/global-setup.ts` |
