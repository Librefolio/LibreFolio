# 📖 API Reference

LibreFolio provides a comprehensive RESTful API built with **FastAPI**.

## 🔗 Quick Links

- [API Overview](overview.md) - Architecture and design patterns
- [cURL Testing Guide](curl-testing.md) - How to test APIs from terminal

## 🖥️ Interactive Documentation

When the server runs in debug mode (`./dev.py server --debug`), you can access the interactive documentation generated from the code. These pages allow you to explore the API endpoints, see the expected
request/response schemas, and even execute requests directly from your browser.

- 🚀 [**Swagger UI**](http://localhost:6040/api/v1/docs){:target="_blank"} : Best for exploring and testing endpoints.
- 💻 [**ReDoc**](http://localhost:6040/api/v1/redoc){:target="_blank"}: Best for reading the documentation in a structured format.

!!! warning "Off on every other instance"

    `/api/v1/docs`, `/api/v1/redoc` and `/api/v1/openapi.json` exist only where the documentation is switched on: with `./dev.py server --debug`, which sets `LIBREFOLIO_API_DOCS=1`, with that variable set by hand, or in test mode (the test lanes). Anywhere else, Docker and managed instances included, they answer `404`: an instance in use publishes no map of its API. The links above therefore work on a debug server only.

    The schema does not need the pages: `./dev.py api schema` (and `./dev.py api sync`, which adds the TypeScript client) builds it in process from the application, so it works whatever the instance serves ([API & Frontend Communication](overview.md)). The pages are LibreFolio's own (`backend/app/api/api_docs.py`), with their libraries pinned and checked: see [The Content-Security-Policy and Frame Protection](../architecture/security.md#managed-headers).

## 🔀 Dynamic Route Generation

FastAPI generates the API routes dynamically at startup based on the Python function definitions. This ensures that the documentation is always perfectly in sync with the code.

The API is structured into routers, each handling a specific domain (all mounted under `/api/v1` by `backend/app/api/v1/router.py`):

- `/auth`: Authentication and the account's own actions. Sign-in and sign-out (`/auth/login`, `/auth/logout`): the session is a cookie that lasts `session_ttl_hours`, with no refresh token ([Token Expiration](../architecture/security.md#token-expiration)). The current account (`/auth/me`), registration (`/auth/register`, with an invitation where the registration mode asks for one), the profile and the password (`/auth/profile`, `/auth/change-password`), and the deletion of one's own account (`DELETE /auth/users/me`, with its preview). The account's user carries `whats_new`, the changelog chapters left to show after an update, and `POST /auth/whats-new/seen` records that the user closed them ([What's new](../frontend/onboarding.md#whats-new)). The links an account receives: inspect a token (`/auth/tokens/inspect`), the password reset (`/auth/password-reset`) and the initial administrator's setup (`/auth/setup`). The [Address Probe](../architecture/security.md#address-probe) (`/auth/address-probe`).
- `/users`: User management.
- `/email`: The instance's email: its state, a test email and the links an administrator sends (`GET /email/status`, `POST /email/test`, `POST /email/links`, administrators only), and, without a session, the «forgot password» email and the verification link (`POST /email/password-reset`, `POST /email/verification/confirm`, `POST /email/verification/resend`); see [The API](../backend/email.md#api) of the Email Service.
- `/security`: The security checks of the instance, evaluated on demand (`GET /security/checks`, administrators only); see [The Checks on Demand](../architecture/security.md#security-checks-endpoint).
- `/settings`: User settings, admin-managed global settings, scheduler state/logs, the cache admin routes (`/settings/cache/status`, `/settings/cache/clear/{name}`, `/settings/cache/clear-all` — see [Cache Registry & Admin](../architecture/settings_cache.md)), and the plugin settings (`/settings/plugins` — see [Plugin Settings](../architecture/patterns/plugin_settings.md#api)).
- `/system`: Server info (`/system/info`: the app version only without a session, everything with one), health check (`/system/health`), readiness (`/system/ready`, no session: `200` when the database answers and its schema is at the head revision, `503` otherwise), plugin diagnostics (`/system/plugin-diagnostics`), the connection and container-image checks, the public instance configuration (`/system/instance`, no session: see [Public instance configuration](../architecture/settings.md#public-instance-configuration)), the block page (`/system/block`, signed-in users only: whether the hosting provider blocked the instance, its deletion date and, for an administrator, where the subscription is managed and whether a backup can still be downloaded; see [Instance Block](../architecture/security.md#instance-block)), the catch-up of the prices (`GET /system/price-refresh`, signed-in users only: whether the scheduler is catching up on prices now, for the web app's notice **Updating prices…**; see [Catch-up Progress](../backend/scheduler.md#price-refresh)), and the scheduled wake-up (`POST /system/wake-sync`, with the `LIBREFOLIO_WAKE_TOKEN` token instead of a session: it runs the scheduler's due jobs and streams their report; see [Scheduled Wake-up](../../admin/sleep_wake.md#wake-sync)). [System Information and Readiness](../architecture/security.md#system-info-and-readiness) details `/system/info` and `/system/ready`. One module per resource in the `backend/app/api/v1/system/` package, whose `__init__.py` only composes the `/system` router.
- `/uploads`: File uploads and media serving.
- `/assets`: Asset management (CRUD, price history) — includes `/prices`, `/provider` (search, live quotes), `/events`.
- `/transactions`: Transaction management.
- `/brokers`: Broker management and sharing — includes `/import` (BRIM broker report import).
- `/backup`: Backup & export.
- `/panel`: The hosting panel's status route, `GET /panel/status` (`get_panel_status`), with the `LIBREFOLIO_PANEL_STATUS_TOKEN` token instead of a session: where the setup of the [initial administrator](../architecture/access_control.md#initial-admin) stands, as [`admin_setup_status()`](../architecture/access_control.md#setup-status) reads it. Its answer, `PanelStatusResponse`, holds exactly four keys: `admin_setup`, one of `none`, `pending`, `done` and `expired`; `setup_expires_at`, when the setup link stops working, in UTC, only while `pending` (`null` otherwise); `mode`, `normal` or `awaiting_restore`; and `restore`, `PanelRestoreSummary` (`state`, `reason`, `waiting`, `backup_created_at`, `stage_id`), `null` when no restore was ever recorded (lot H-62). Responses `200`, `401`, `404` (no token set: the route is off), `429`, `500` (`restore_state_unreadable`) and `503`; it answers on a blocked instance too. Its OpenAPI tag is «Hosting panel», the only tag of the thirteen routes a hosting panel calls: this one, the four `/backup/panel/jobs…` routes, the seven `/backup/panel/restore…` routes (scope `backup:restore`, a signed ticket only: see [Awaiting Restore](../architecture/security.md#await-restore)) and `POST /system/wake-sync`. See [The Hosting Panel's Access](../architecture/security.md#panel-access) and, for administrators, [The Setup Status](../../admin/hosting_providers.md#panel-status).
- `/portfolio`: Portfolio analysis and metrics.
- `/fx`: Foreign exchange operations — includes `/fx/providers` and `/fx/currencies`.
- `/signals`: Domain-agnostic signal preview (`POST /signals/preview`).
- `/risk`: Risk analysis — analytics catalog, queries, scenario catalog, and per-asset eligibility for a period (`POST /risk/eligibility`). The Asset Detail risk view and the *What if…?* simulation still carry a beta notice.
- `/ai-export`: Versioned AI Export datasets and analyses.
- `/tools`: Atomic Tool calculations — catalog, batch compute (`POST /tools/compute`), and per-process diagnostics; see [Tool plugins](../architecture/patterns/tool_plugins.md).
- `/utilities`: Reference data (ISO currencies, etc.).

On an instance blocked by its hosting provider (`LIBREFOLIO_BLOCKED`), every route but a short list answers `423 Locked` with `detail.code` `instance_blocked` to a signed-in user, and `401` to a caller without a valid session, the public routes outside the list included: see [Instance Block](../architecture/security.md#instance-block).

While the hosting panel restores an instance (`LIBREFOLIO_AWAIT_RESTORE`), every route but the probes, `/system/instance`, the scheduled wake-up and the panel's routes answers `423 Locked` with `detail.code` `instance_awaiting_restore`, to anyone, signed in or not: see [Awaiting Restore](../architecture/security.md#await-restore).

## 📋 Pydantic Schemas

The API uses **Pydantic** models for data validation and serialization. These schemas define the structure of the data exchanged between the frontend and backend. You can find the
schema definitions in the `backend/app/schemas/` directory.
