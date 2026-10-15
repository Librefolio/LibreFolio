---
title: "The app compresses its own HTTP responses: Starlette's GZipMiddleware, level 6, above 1 KiB; no build-time precompression for 1.2"
category: decision
status: resolved
date: 2026-10-06
tags: [backend, http, gzip, compression, performance, self-hosting, docker, workstream-m, release-1.2]
related:
  - problems/release-images-shipped-debug-frontend
  - problems/stale-frontend-after-update-html-cached
  - features/F-062
  - sources/phase00-release-images-and-gallery-2026-10
---

# Decision: gzip in the app, not in front of it

## Context

LibreFolio is one container that serves the API, the SvelteKit build and the documentation site
([[features/F-062]]), and an install may reach it with no reverse proxy in between, or through one that does not
compress. The cloud sizing study of workstream M measured what a browser downloads (report, item 7): a first visit
of about 7.5 MB and an eight-page session of about 5.8 MB, nearly all of it text — API JSON, JavaScript, CSS and the
docs' HTML, about 200 KiB per docs page.

## Decision

The developer, on M's proposal (plan of the release images, §0, 2026-10-06): «direi proprio che va fatta».

`backend/app/main.py` adds `GZipMiddleware(minimum_size=1024, compresslevel=6)` outside the CORS middleware (since CP2b of 1.3.0 an entry of `MIDDLEWARE_STACK` in `services/platform/middleware.py`)
(`16238e220`, «feat(server): gzip HTTP responses»), with Starlette's default exclusions kept:

- images, fonts, archives, Server-Sent Events, 206 range replies and responses that are already encoded pass
  untouched — the provider search stream keeps arriving result by result;
- every compressed answer carries `Vary: Accept-Encoding`, so a shared cache keeps the two forms apart;
- bodies of 128 KiB and more are compressed off the event loop.

**Level 6**, measured on the real bodies of a session: 2.41 MB of API JSON became 0.22 MB in 19 ms at level 6 and
0.21 MB in 62 ms at level 9 — the same size for a third of the CPU.

## Options Considered

1. **Leave it to a reverse proxy.** Not every install has one: the repository's `docker-compose.yml` runs the one
   `librefolio` service.
2. **Precompress at build time** (SvelteKit's `precompress: true` plus `.br`/`.gz` negotiation in
   `ImmutableStaticFiles`). Not for 1.2: it saved only 0.37 MB more on a first visit, and it touched files outside
   the plan.
3. **Level 9.** The same bytes for three times the CPU.

## Consequences

Measured on two light images that differ only in `main.py` (plan, step 4):

| Window | Without gzip | With gzip |
|--------|--------------|-----------|
| First visit, cold | 7,456–7,489 KB | 2,780–2,785 KB (−63 %) |
| Eight-page session, warm | 5,374–5,935 KB | 888–889 KB (−84 %) |
| Dashboard reload | 387 KB | 55 KB |

The CPU cost stayed within the noise of the host (+0.2 s over the walk). `openapi.json` drops from 655 to 116 KB.
The HTML documents keep their `no-cache` revalidation ([[problems/stale-frontend-after-update-html-cached]]) and the
hashed chunks their year-long `immutable` header and ETag.

`backend/test_scripts/test_api/test_http_compression_api.py` pins the contract on the live backend: what is
compressed, what must be left alone (small bodies, PNG, SSE, `Range`) and the cache headers of each kind of response.

## Source files

| Role | Path |
|------|------|
| Middleware | `backend/app/services/platform/middleware.py` |
| Contract tests | `backend/test_scripts/test_api/test_http_compression_api.py` |
| Journal (§0, steps 2 and 4) | `LibreFolio_developer_journal/Release_2/Phase_0/27_releaseImages/plan-phase00ReleaseImages.prompt.md` |
