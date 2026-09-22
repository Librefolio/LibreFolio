---
title: "Browser GHCR image probe could not complete the anonymous Bearer flow"
category: problem
status: resolved
date: 2026-09-09
mkdocs: null
tags: [backend, frontend, ghcr, docker, auth, cors, update-check, fail-closed]
related:
  - concepts/ci-release-pipeline
  - decisions/single-docker-image
---

# Problem: Browser GHCR image probe could not complete the anonymous Bearer flow

## Summary

The in-app update check originally treated an anonymous GHCR manifest `HEAD` as
a complete availability test. Public GHCR manifests instead use an anonymous
Bearer challenge: obtaining the public pull token is possible without
credentials, but the browser cannot reliably complete the challenge/token/
authenticated-manifest sequence because the required cross-origin requests are
not exposed through a usable CORS flow.

The fix moves only the image-availability probe behind an authenticated,
same-origin LibreFolio endpoint. Release metadata remains a separate browser
probe. An update is announced only when the stable release is newer **and** its
fixed LibreFolio image tag is pullable.

## Symptom

A valid newer GitHub release could never become `update-available`: the direct
browser request received the normal GHCR authentication challenge and the
client classified it as `image-request-failed`. Treating the first `401` as an
unavailable image would also confuse a registry protocol step with a terminal
failure.

## Root Cause

Two different questions had been collapsed into one browser-side check:

1. **Release metadata:** does GitHub report a newer stable release?
2. **Image availability:** is the corresponding GHCR image manifest actually
   pullable yet?

The first question is browser-compatible and may become true before the release
pipeline finishes publishing the image. The second requires GHCR's public
Bearer exchange. Although it is anonymous, it still needs a challenge-derived
token followed by an authorized manifest retry; browser CORS does not reliably
permit that protocol.

## Rejected Approach

Completing the public token exchange in the browser was rejected after checking
the actual CORS behavior. A client-side fallback that interpreted the challenge
as success was also rejected: it would announce updates whose image might not
exist.

## Solution

### Keep the two probes separate

- The frontend continues to query GitHub Releases for stable release metadata,
  validate and normalize the release tag, compare versions, and apply its
  cache/dismissal policy.
- Only when a newer release exists does it call the authenticated same-origin
  `/api/v1/system/container-image-status` endpoint with the normalized stable
  tag.
- The endpoint reports image pullability, not release existence. A release may
  therefore be newer while its image is still `pending`.

### Bound the backend registry exchange

The backend is deliberately not a generic registry proxy:

- repository is fixed to the public `librefolio/librefolio` image;
- the endpoint accepts only normalized stable `x.y.z` tags;
- the challenge must name the expected HTTPS realm host and token path, with no
  embedded identity, alternate port, query, fragment, or redirect;
- service and repository pull scope must exactly match the compiled-in GHCR
  constants;
- the public token request carries no LibreFolio, GitHub, proxy, cookie, or
  other credentials;
- the returned token is used only for the single manifest retry;
- manifest requests advertise the supported OCI and Docker manifest/index media
  types and use a bounded timeout with redirects disabled.

### Preserve explicit result semantics

| Registry outcome | API result |
|---|---|
| Manifest success | `published` |
| Manifest `404` | `pending` |
| Missing, malformed, or untrusted challenge; token transport/status/payload failure | `error` / `image-auth-request-failed` |
| Manifest transport failure or any non-success other than `404` | `error` / `image-request-failed` |

The response schema requires a reason exactly when the status is `error`, so
authentication and manifest failures cannot silently collapse into
`published`, `pending`, or `up-to-date`.

## Frontend Fail-Closed Rule

The frontend reports `update-available` only after both probes succeed and the
image result is `published`. `pending` remains a distinct expected state while
the release pipeline catches up. Any endpoint exception, malformed response,
authentication failure, or manifest failure remains an error. Automatic checks
stay silent on those failures; explicit checks can explain that verification
failed, but neither path presents the update as ready.

## Data-Handling Boundary

The wiki and the public API contract retain only the status/reason projection.
Registry token material, credentials, raw challenge/header material, and private
runtime environment details must not be persisted, logged, cached, or returned
to the frontend.

## Timeline and Stakeholders

| Date | Event |
|---|---|
| 2026-09-09 | Independent review identified the direct-browser GHCR challenge/CORS defect. |
| 2026-09-09 | Same-origin endpoint, strict challenge validation, explicit result mapping, frontend gate, and regression coverage were integrated. |

Primary stakeholders are self-hosted administrators receiving update prompts
and maintainers of the release/update-check path.

## Prevention

- Test registry protocols as multi-step exchanges rather than inferring
  browser viability from a successful server-side HTTP request.
- Keep release discovery and deployable-artifact readiness as separate state
  machines.
- Keep registry targets and authorization scope fixed; do not accept arbitrary
  realms, repositories, services, scopes, or tags from callers.
- Regression-test the complete anonymous manifest → public token → manifest
  retry sequence, all trust-boundary rejections, `404` pending behavior, API
  authentication, stable-tag validation, and frontend fail-closed mapping.

## Impact

The solved defect had prevented real updates from becoming available through
the prompt. The bounded backend exchange now handles GHCR's normal public
authentication protocol without exposing a credentialed proxy or leaking
sensitive transport data, while the image gate prevents the UI from advertising
a release before its container image is pullable.

## Links

- [[concepts/ci-release-pipeline]]
- [[decisions/single-docker-image]]

## Source files

| Role | Path |
|------|------|
| Fixed-target GHCR probe and trust validation | `backend/app/services/container_registry.py` |
| Authenticated same-origin endpoint | `backend/app/api/v1/system.py` |
| Typed status/reason contract | `backend/app/schemas/system.py` |
| Release metadata probe, image gate, and fail-closed mapping | `frontend/src/lib/features/update-check/updateCheck.ts` |
| Registry protocol and endpoint regressions | `backend/test_scripts/test_services/test_container_registry.py` |
| Integrated Round 5 plan and rationale | `LibreFolio_developer_journal/Release_2/Phase_0/14_feedbackImportUrgent/plan-phase00FeedbackImportUrgentRound5-GHCRAuth.prompt.md` |
