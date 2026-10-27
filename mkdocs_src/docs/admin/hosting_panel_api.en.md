# 🔌 Hosting for Others: the Panel API

This page is part of the guide for whoever runs LibreFolio for other people. It covers the **panel API**: the tokens and signed tickets your hosting panel uses to call an instance, what an instance answers, and the setup status.

The rest of the guide starts on [Hosting for Others](hosting_providers.md).

---

## 🔌 Hosting Panel API {: #panel-api }

Your hosting panel calls the instance without a user's session. Each of its calls belongs to a
**scope**, and each scope but the restore has a token of its own, which opens that scope and nothing
else:

| Scope | For | Routes | Token |
| --- | --- | --- | --- |
| `backup` | Back up the whole instance and download the archive: [Backups for Your Hosting Panel](hosting_panel_backups.md#panel-backups) | `POST /api/v1/backup/panel/jobs`, then `GET`, `GET …/file` and `DELETE` on `/api/v1/backup/panel/jobs/{job_id}` | `LIBREFOLIO_BACKUP_DOWNLOAD_TOKEN` |
| `wake` | Run the price and exchange rate updates that are due, for example right after your panel wakes the instance: [Scheduled Wake-up](wake_sync.md#wake-sync) | `POST /api/v1/system/wake-sync` | `LIBREFOLIO_WAKE_TOKEN` |
| `status` | Follow the setup of the [initial administrator](hosting_instances.md#initial-admin), the instance's mode and its restore: [The Setup Status](#panel-status) | `GET /api/v1/panel/status` | `LIBREFOLIO_PANEL_STATUS_TOKEN` |
| `backup:restore` | Put a backup back on an instance that awaits it: [Restoring an Instance from Your Panel](hosting_panel_backups.md#panel-restore) | The seven routes under `/api/v1/backup/panel/restore` | None: a [signed ticket](#panel-api-tickets) only |

Beside the tokens, a panel that runs many instances can sign a short-lived **ticket** for each call:
see [Signed Tickets](#panel-api-tickets). A scope accepts its token, its tickets, or both; the
`backup:restore` scope accepts tickets only, so it is off while the panel's public keys are not set.

The rules of this section hold for the four scopes alike. None of your panel's calls counts as a
visit for the [idle suspension](sleep_wake.md#idle-suspend-activity): each keeps the machine awake
only while it runs.

### 🗝️ A Token per Scope {: #panel-api-tokens }

- **No token and no keys, no scope.** A scope is off when its token is not set and the panel's
  [public keys](#panel-api-tickets) are not set either: its routes answer `404`, as a path that
  does not exist, and LibreFolio writes no line of its own about them. Set only what your panel
  uses.
- **Each token opens its own scope only.** Each scope compares a call with its own token alone: sent
  to another scope, a token is a wrong one. Generate a different token for each scope and for each
  instance, so that a token that leaks opens one scope of one instance.
- **At least 32 visible ASCII characters**: letters, digits and punctuation; no space, no tab, no
  accented letter. `openssl rand -hex 32` prints 64:

    ```bash
    openssl rand -hex 32
    ```

- **In a file, if you prefer.** Each variable has its `_FILE` twin, such as
  `LIBREFOLIO_PANEL_STATUS_TOKEN_FILE`: the path of a file that holds the token, as Docker mounts
  its secrets (see «Secrets in Files» in [Environment Variables](configuration.md)).
  When both are set, the variable itself wins.
- **Set them in the container's environment or in `.env`**, then restart LibreFolio. With Docker
  Compose, run `docker compose up -d`: `docker compose restart` keeps the old values.
- **A token LibreFolio cannot use does not stop the server**: the
  [startup check](#panel-api-check) names it, and its routes answer `503` until you fix it.

### 📨 How a Call Proves Itself {: #panel-api-auth }

A call proves itself with its scope's token, or with a [signed ticket](#panel-api-tickets), in one
header:

```text
Authorization: Bearer <the scope's token, or a signed ticket>
```

- **Only in that header**, never in the URL, where the access logs of servers and proxies would
  keep it: a token in the query string is not read, and the call gets a `401`.
- **Compared in constant time** with the scope's token, so that how long LibreFolio takes to answer
  tells nothing about the token. What is not the token is read as a ticket, when the panel's keys
  are set.
- **Over HTTPS only**: whoever reads a token on the way can use it.

### 🎫 Signed Tickets {: #panel-api-tickets }

A panel that runs many instances does not need a token per instance and scope. It signs a short
**ticket** for each call, with one Ed25519 private key that stays in its vault. Each instance holds
only the matching **public keys**: a leaked instance gives nothing that opens another.

Tokens and tickets work together, scope by scope. A scope with a token and the panel's keys accepts
either, so a panel can migrate step by step: set the keys, make the panel sign, then remove the
tokens. A self-hosted cron job keeps its token.

| Variable | What it holds | Default |
| --- | --- | --- |
| `LIBREFOLIO_PANEL_PUBLIC_KEYS` | `kid:key`, or `kid:key,kid:key…`: 1 to 4 entries, spaces around an entry ignored. `kid` is the label of a key, 1 to 64 characters among `A-Z a-z 0-9 . _ -`, each once. `key` is the raw 32-byte Ed25519 public key in base64url without padding, 43 characters. A public key is not a secret, so there is no `_FILE` twin | Unset or blank: tickets are off |
| `LIBREFOLIO_PANEL_CLOCK_SKEW_SECONDS` | How far a ticket's times may be off the instance's clock: a whole number from 0 to 300 | `60` |
| `LIBREFOLIO_PUBLIC_URL` | The instance's address, **required with the keys**: its origin is the audience of its tickets | — |

The **audience** is the origin of `LIBREFOLIO_PUBLIC_URL`, `scheme://host[:port]`: lower case, without
the default port (80 or 443), without a path and without a trailing slash. `https://Folio.Example.com:443/app/`
gives `https://folio.example.com`. Set them in the container's environment or in `.env`, then restart
LibreFolio, as for the tokens.

**One origin per instance.** A ticket names an origin, never a path: two instances served from the same
origin under different paths (`https://host/a` and `https://host/b`) would accept each other's tickets.
Give each instance an origin of its own, for example its own host name. With the keys set, a
`LIBREFOLIO_PUBLIC_URL` that holds a path is a warning of the [startup check](#panel-api-check).

**What a ticket is.** A compact JWS, which is a JWT, of at most 2048 bytes:

| Part | Field | Value |
| --- | --- | --- |
| Header | `alg` | exactly `EdDSA` |
| Header | `typ` | exactly `lf-panel+jwt` |
| Header | `kid` | one of the configured labels |
| Claims | `aud` | the instance's audience, above |
| Claims | `scope` | `backup`, `wake`, `status` or `backup:restore`: it must be the scope of the route |
| Claims | `iat`, `exp` | Unix seconds, whole numbers; `exp − iat` is positive and at most 300 |
| Claims | `jti` | a unique id of 16 to 64 characters among `A-Z a-z 0-9 _ -`, used once |

All the claims are required; any other claim is ignored. It travels in the header of a token,
`Authorization: Bearer <ticket>`, and in no other place.

- **One ticket per call.** Following a backup job means a new ticket for each `GET`, and a retry
  gets a new `jti`. A ticket is not bound to a method or a path, only to an instance and a scope.
- **Recommended signer**: `iat` is now, `exp` is `iat + 300`, and `jti` is 16 random bytes in
  base64url.
- **Times**, with the tolerance `skew`: a ticket is expired when `exp ≤ now − skew`, and not yet
  valid when `iat > now + skew`.

```bash
curl -H "Authorization: Bearer $TICKET" https://folio.example.com/api/v1/panel/status
```

#### 🚫 Why a Ticket Is Refused {: #panel-api-ticket-refusals }

A ticket that cannot be verified (more than 2048 bytes, not a JWS, another `alg` or `typ`, a bad
signature) gets the scope's usual `401` code, with no reason: only the holder of a genuinely signed
ticket learns why a ticket is refused. A signed ticket that is refused gets `401`, the header
`WWW-Authenticate: Bearer` and its own `code`, checked in this order:

| Order | `code` | When |
| --- | --- | --- |
| 1 | the scope's `…_unauthorized` | The ticket cannot be verified, as above |
| 2 | `panel_ticket_unknown_key` | The `kid` is not in the instance's keys. It shows at once a rotation half done |
| 3 | `panel_ticket_expired` | `exp ≤ now − skew`: sign a new ticket |
| 3 | `panel_ticket_not_yet_valid` | `iat > now + skew`: the instance's clock is behind, for example right after the machine resumed. The answer carries `Retry-After: 5`: retry with a **new** ticket |
| 4 | `panel_ticket_wrong_audience` | Another instance's ticket, or no `aud` |
| 5 | `panel_ticket_wrong_scope` | The ticket is for another scope than the route's |
| 6 | `panel_ticket_invalid` | Signed but badly built: a bad `jti`, a lifetime that is not positive or over 300 seconds, a required claim missing or of the wrong type. It is a bug of the signer |
| 7 | `panel_ticket_replayed` | The `jti` was used before |

Only the first two refusals count for [the limit](#panel-api-limit), since they prove nothing.

#### 📒 The Registry of Used Tickets {: #panel-api-registry }

LibreFolio remembers each accepted `jti` in a small SQLite file, `panel_tickets.sqlite3` in the data
directory (permissions 600, created at the first ticket). A ticket is checked and recorded in one
transaction, so several worker processes, and a restart, never accept it twice. Each record removes
the entries whose ticket expired more than 10 minutes ago (the widest tolerance plus the longest life
of a ticket), so a clock that steps back, or a tolerance raised later, never makes a ticket valid twice.

- Only a regular file is used: a symbolic link in its place is refused, never followed.

- The file is not part of a backup, and a restore leaves it alone.
- If LibreFolio cannot use it, the call gets `503` with the scope's `…_unavailable` code. A call with
  the scope's token, which is checked first, still works.

#### 🔄 Rotating the Key {: #panel-api-rotation }

1. Add the new key as a second entry: `LIBREFOLIO_PANEL_PUBLIC_KEYS=old:…,new:…`, then restart the
   instance, since the environment of a process changes only at its start.
2. Make the panel sign with the new `kid`. A ticket of the new key that reaches an instance
   before step 1 is refused with `panel_ticket_unknown_key`.
3. After 5 minutes, the longest life of a ticket, remove the old entry and restart.

!!! warning "Settings that cannot be used"

    A malformed key list, a tolerance out of range, or keys without a usable `LIBREFOLIO_PUBLIC_URL`
    make **every** route of the panel answer `503` with the scope's `…_unavailable` code, tokens
    included, until you fix them. This is on purpose: a panel that fails closed is never left half
    open by a typo. The [startup check](#panel-api-check) names the variable.

### 🧪 Test Vectors {: #panel-api-test-vectors }

To test a signer, here is a published key pair and a ticket made with it. The values are for tests
only: the private key is public, so **never use it for a real instance**.

- `private_key_seed_hex` is the 32-byte Ed25519 private key seed, in hexadecimal.
- `public_key` is the matching public key, in base64url without padding, and `environment` holds
  the settings of an instance that trusts it: `LIBREFOLIO_PANEL_PUBLIC_KEYS` with the label
  `test-vector-1`, `LIBREFOLIO_PUBLIC_URL` and the tolerance, 60 seconds.
- `header` and `payload` are what the ticket signs. `ticket` is the result: the base64url of the
  header, a dot, the base64url of the payload, a dot, and the base64url of the signature.
- `verdicts` lists what an instance with that environment answers to the ticket, one row per
  try, each against an empty registry. A row has `now` (the instance's clock, in Unix seconds),
  `scope` (the scope of the route that receives the ticket) and, when given, `public_url`, which
  replaces `LIBREFOLIO_PUBLIC_URL`. `accepted` is the only success; the others are the `code` of a
  `401`.

```json
{
  "warning": "Test values only: this key is published, never use it to sign for a real instance",
  "private_key_seed_hex": "934e14faf1000ba247789b80c5ee42e56e9bcea95704f27789dbf79feb1f0d87",
  "public_key": "ZaKIp6hE1dqXQkB19O2g4x_047q1cEYL_u_S5ToghwE",
  "environment": {
    "LIBREFOLIO_PANEL_PUBLIC_KEYS": "test-vector-1:ZaKIp6hE1dqXQkB19O2g4x_047q1cEYL_u_S5ToghwE",
    "LIBREFOLIO_PUBLIC_URL": "https://folio.example.com",
    "LIBREFOLIO_PANEL_CLOCK_SKEW_SECONDS": "60"
  },
  "header": {"alg": "EdDSA", "kid": "test-vector-1", "typ": "lf-panel+jwt"},
  "payload": {"aud": "https://folio.example.com", "scope": "status", "iat": 2000000000, "exp": 2000000300, "jti": "dGVzdC12ZWN0b3ItMDAx"},
  "ticket": "eyJhbGciOiJFZERTQSIsImtpZCI6InRlc3QtdmVjdG9yLTEiLCJ0eXAiOiJsZi1wYW5lbCtqd3QifQ.eyJhdWQiOiJodHRwczovL2ZvbGlvLmV4YW1wbGUuY29tIiwic2NvcGUiOiJzdGF0dXMiLCJpYXQiOjIwMDAwMDAwMDAsImV4cCI6MjAwMDAwMDMwMCwianRpIjoiZEdWemRDMTJaV04wYjNJdE1EQXgifQ.mZTtw7BdXHfJfrI2cSf_CPsZ6piPpTmXEWtb_ZoMVtrW4uKFH3JSqOiXQ6D7dbhro0PHbNNEOlPNkdGrPYOnCA",
  "verdicts": [
    {"now": 2000000000, "scope": "status", "verdict": "accepted"},
    {"now": 1999999940, "scope": "status", "verdict": "accepted"},
    {"now": 1999999939, "scope": "status", "verdict": "panel_ticket_not_yet_valid"},
    {"now": 2000000359, "scope": "status", "verdict": "accepted"},
    {"now": 2000000360, "scope": "status", "verdict": "panel_ticket_expired"},
    {"now": 2000000000, "scope": "backup", "verdict": "panel_ticket_wrong_scope"},
    {"now": 2000000000, "scope": "status", "public_url": "https://other.example.com", "verdict": "panel_ticket_wrong_audience"}
  ]
}
```

| `now` | `scope` | Verdict | Why |
| --- | --- | --- | --- |
| 2000000000 | `status` | `accepted` | The ticket's own `iat` |
| 1999999940 | `status` | `accepted` | `iat` is exactly `now + 60`: the tolerance allows it |
| 1999999939 | `status` | `panel_ticket_not_yet_valid` | One second more than the tolerance |
| 2000000359 | `status` | `accepted` | `exp` is 59 seconds behind |
| 2000000360 | `status` | `panel_ticket_expired` | `exp ≤ now − 60` |
| 2000000000 | `backup` | `panel_ticket_wrong_scope` | The ticket is for `status` |
| 2000000000 | `status`, `public_url` `https://other.example.com` | `panel_ticket_wrong_audience` | The ticket names `https://folio.example.com` |

- Presenting the same ticket a second time after it was accepted gives `panel_ticket_replayed`.
- A signer must produce a ticket the instance accepts, but its bytes need not equal the vector's:
  Ed25519 signatures are deterministic, so the same header and payload bytes always give the same
  signature, and a signer whose JSON bytes differ (key order, spaces) gets another one.

### 🚫 Refused Calls {: #panel-api-refusals }

| Answer | When | `code` |
| --- | --- | --- |
| `404` | The scope is off: neither its token nor the panel's public keys are set (for `backup:restore`, the keys are not set). The body is `{"detail": "Not Found"}`, as for a path that does not exist | — |
| `401` | No credential, or one that is not the scope's token and not a ticket LibreFolio can verify, another scope's token included (any token, for `backup:restore`). The answer carries `WWW-Authenticate: Bearer` | `backup_panel_unauthorized`, `wake_unauthorized`, `panel_status_unauthorized` or `backup_restore_unauthorized`, by scope |
| `401` | A ticket signed by your panel, but refused: see [Why a Ticket Is Refused](#panel-api-ticket-refusals). The answer carries `WWW-Authenticate: Bearer` | `panel_ticket_…`, in every scope |
| `429` | Too many refused credentials from your panel's address: see [The Limit on Refused Credentials](#panel-api-limit). The answer carries `Retry-After`, the seconds to wait | `panel_too_many_attempts`, in every scope |
| `503` | The scope's token is set but cannot be used: shorter than 32 characters, a character that is not visible ASCII, or a `_FILE` that cannot give it. Or the [ticket settings](#panel-api-tickets) cannot be used, or the registry of used tickets. Each call logs an error that names the variable, never the token | `backup_panel_unavailable`, `wake_unavailable`, `panel_status_unavailable` or `backup_restore_unavailable`, by scope |

A scope that is off, or whose token or ticket settings cannot be used, answers before anything else:
the credential of the call is not read, and nothing is counted. The `code` comes in the `detail` of the answer, with a
`message` in English:

```json
{"detail": {"code": "panel_too_many_attempts", "message": "Too many refused panel credentials from this address"}}
```

### 🚦 The Limit on Refused Credentials {: #panel-api-limit }

LibreFolio counts the credentials it refuses, per address:

- **20 refused credentials in 10 minutes**, and every call from that address gets `429`, to every
  scope, until fewer than 20 of its refusals are less than 10 minutes old: `Retry-After` gives the
  seconds to wait. LibreFolio does not read the credential of a call it answers `429`, so the right
  token waits too.
- **A refusal counts when it proves nothing**: no credential, a wrong token, another scope's token,
  a ticket that cannot be verified, or a ticket signed with a key the instance does not hold. The
  four scopes share one count: a panel that keeps sending a wrong backup token also waits for its
  wake-up and its status calls.
- **A ticket with a valid signature is never counted**, whatever is wrong with it (expired, not
  yet valid, another instance, already used…): only the panel can sign one, so a panel whose clock
  is behind never locks itself out.
- **Nothing else counts**: not a call with the right token or an accepted ticket, not a `429`, not
  the `404` of a scope that is off, nor the `503` of a setting that cannot be used.
- **One address, one count**: an IPv6 address counts by its `/64`. Behind a reverse proxy that
  LibreFolio does not trust, every caller has the proxy's address: LibreFolio then counts nothing,
  rather than let one caller's refusals make every caller wait. See «When LibreFolio Does Not Trust
  Your Proxy» in [Checking Connection Security](connection_proxy.md#reverse-proxy).
- **In memory**: each server process keeps its own count, and a restart forgets it.

### 📋 In the Log {: #panel-api-log }

Every call to a scope that is on writes one line, `Hosting panel request`:

| Level | `outcome` | When | With |
| --- | --- | --- | --- |
| ℹ️ `info` | `accepted` | The right token or an accepted ticket: the route then answers as usual | For a ticket: `kid` and `jti` |
| ⚠️ `warning` | `refused` | The `401` | `reason`: `missing`, no credential in the header; `mismatch`, a token that is not the scope's and not a ticket that can be verified. For a signed ticket, the `panel_ticket_…` code, with its `kid` |
| ⚠️ `warning` | `limited` | The `429` | `retry_after`, the seconds of `Retry-After` |
| ⚠️ `warning` | `unavailable` | The `503` | `reason`: `unusable`, or `registry` when the registry of used tickets cannot be used. Just before it, an error line names the variable and what is wrong |

- Every line also carries `scope` (`backup`, `wake`, `status` or `backup:restore`), `method`, `path` (without the
  query string), `credential`, the kind of credential the call presented (`token` or `ticket`), and
  the `request_id` of the request.
- It never carries the token, the ticket, the value sent, a header, the query string or your panel's
  address:
  uvicorn's access line, which the web server writes for every request, has the address.
- The error line before an `unavailable` one is the scope's own:
  `The hosting panel's backup token cannot be used: its routes refuse every request`
  ([The Token](hosting_panel_backups.md#panel-token)),
  `The wake-up token cannot be used: the scheduled wake-up refuses every request`
  ([Turning It On](wake_sync.md#wake-sync-token)), or
  `The panel status token cannot be used: the status route refuses every request`.
  For the ticket settings it is
  `The hosting panel's ticket settings cannot be used: its routes refuse every request`, with the
  variable and its code.
- A call to a scope that is off writes no such line.

### 🩺 The Startup Check {: #panel-api-check }

At every start, LibreFolio checks the tokens of the three scopes that have one and the ticket settings, in two
checks, and logs an error for each one that fails. The **Security** tab of Settings › Administration shows the same checks
(«Security» in [Global Settings](settings.md)).

| `check` | Tokens | Passed | An error |
| --- | --- | --- | --- |
| `platform.hosting_panel` | `LIBREFOLIO_WAKE_TOKEN`, `LIBREFOLIO_PANEL_STATUS_TOKEN` and, for the [tickets](#panel-api-tickets), `LIBREFOLIO_PANEL_PUBLIC_KEYS`, `LIBREFOLIO_PANEL_CLOCK_SKEW_SECONDS` and `LIBREFOLIO_PUBLIC_URL` | None is set: the scopes are off. Or each one that is set can be used | A token cannot be used: its route answers `503` to every call until you fix it. The line names the variables and why, never a token: `A hosting panel token cannot be used, and its route answers 503 to every call: LIBREFOLIO_PANEL_STATUS_TOKEN (PANEL_STATUS_TOKEN_TOO_SHORT)`. Or the ticket settings cannot be used: **every** route of the panel answers `503`, the backup's included |
| `backup.panel_token` | `LIBREFOLIO_BACKUP_DOWNLOAD_TOKEN` | Not set: the backup scope is off. Or it can be used | It cannot be used: see [The Token](hosting_panel_backups.md#panel-token) |

- The reasons of `platform.hosting_panel` are `…_TOO_SHORT`, fewer than 32 characters;
  `…_NOT_VISIBLE_ASCII`, a space, a tab or another character outside visible ASCII; and
  `FILE_UNREADABLE`, a `_FILE` that cannot give the token.
- The reasons for the ticket settings are `PANEL_KEYS_INVALID`, `PANEL_CLOCK_SKEW_INVALID` and
  `PANEL_AUDIENCE_UNAVAILABLE`, a missing or unusable `LIBREFOLIO_PUBLIC_URL`. The line never
  carries a key.
- With usable keys, a `LIBREFOLIO_PUBLIC_URL` that holds a path, such as `https://host/app`, is a
  `warning` in every profile: serve [one instance per origin](#panel-api-tickets).
- In the [managed profile](hosting_providers.md#managed-profile), a token still set beside usable keys, the backup's
  included, is a warning: `A hosting panel token is set beside the panel's public keys: remove it
  once the panel signs tickets`.
- A check that passes writes nothing in the log.

### 📊 The Setup Status {: #panel-status }

`GET /api/v1/panel/status` tells your panel where the setup of the
[initial administrator](hosting_instances.md#initial-admin) stands: whether your customer has used the setup link, and
until when the link works. It also gives the instance's `mode` and its `restore`
([Restoring an Instance from Your Panel](hosting_panel_backups.md#panel-restore)), how many places its users take, with the
limit, and whether the owner's [new address](hosting_instances.md#owner-email-change) waits for its confirmation. Turn it on with a token of its own in
`LIBREFOLIO_PANEL_STATUS_TOKEN`, as in [A Token per Scope](#panel-api-tokens), then:

```bash
curl -sS -H "Authorization: Bearer $LIBREFOLIO_PANEL_STATUS_TOKEN" \
  https://librefolio.example.com/api/v1/panel/status
```

```json
{"admin_setup": "pending", "setup_expires_at": "2026-10-23T09:12:44.512312Z", "mode": "normal", "restore": null, "users_used": 3, "users_limit": 10, "owner_email_change": null, "instance_key": "ok", "users_over_limit": false}
```

| `admin_setup` | What it means | `setup_expires_at` |
| --- | --- | --- |
| `none` | No setup link was ever issued, as on an instance started without `LIBREFOLIO_ADMIN_EMAIL`; or the account it was for has been deleted since | `null` |
| `pending` | The latest setup link is still valid: not used, not withdrawn and not expired | When the link stops working |
| `done` | The setup is complete: your customer chose the password through the link, or the account was set up another way ([Once the Account Is Active](hosting_instances.md#initial-admin-active)) | `null` |
| `expired` | The latest link is more than 72 hours old, or was withdrawn: cancelled, or the administrator's address changed. A new link makes it `pending` again: [A New Link](hosting_instances.md#initial-admin-new-link) | `null` |

| Key | What it holds |
| --- | --- |
| `mode` | `normal`, or `awaiting_restore` while [`LIBREFOLIO_AWAIT_RESTORE`](hosting_panel_backups.md#await-restore) is on |
| `restore` | `null` when no restore was ever recorded on this instance; otherwise `state` (`pending`, `in_progress`, `committed`, `rolled_back`, or `unreadable` when the state of the restore cannot be read), `reason` (why a restore was rolled back: `first_start_failed`, `swap_interrupted`, `swap_failed` or `stage_missing`; for `unreadable`, why the state cannot be read: `io`, `not_a_file` or `invalid`), `waiting` (why a confirmed restore still waits: `backup_running`, `other_data_directory`, `server_running` or `instance_blocked`), `backup_created_at` and `stage_id`. Each is `null` when it does not apply. It never says who confirmed the restore |
| `users_used` | The places the users take, a whole number from `0`: the active accounts, the invitations not yet used, revoked or expired, and the deactivated accounts that wait for their email verification while its link is live or, for the [initial administrator](hosting_instances.md#initial-admin), for the setup. Each account or invitation counts once. It is what `LIBREFOLIO_MAX_USERS` limits |
| `users_limit` | The value of `LIBREFOLIO_MAX_USERS`, a whole number from `1`; `null` when it is not set, which means no limit |
| `owner_email_change` | Where a [change of the owner's address](hosting_instances.md#owner-email-change) stands: `pending` (the new address was sent a confirmation link and the account keeps the old one until it is clicked), `blocked` (another account already holds the new address, so nothing changes: change the variable again to a free address) or `null` (no change is waiting, the instance is not managed, or its initial administrator has not set up yet). Never the address |
| `instance_key` | `ok`, or `mismatch` when the instance key it has is not the one its data was written with ([The Key Check](configuration_secrets.md#instance-key-check)). With `mismatch`, your backup starts answer `409` `backup_instance_key_mismatch` and the wake-up runs no job; the instance keeps serving. Never the fingerprint |
| `users_over_limit` | `true` while the active accounts outnumber `users_limit`, for example after your customer moved to a smaller plan: ordinary users are then refused until an administrator chooses who keeps access, and the others are deactivated, never deleted. `false` otherwise, and always `false` when `users_limit` is `null`. Invitations and accounts waiting for their email verification take places, so they count in `users_used`, but they never make this `true`. One yes or no, never who |

- The answer holds these nine keys and nothing else: `admin_setup`, `setup_expires_at`, `mode`,
  `restore`, `users_used`, `users_limit`, `owner_email_change`, `instance_key` and `users_over_limit`. The two counts are numbers only,
  never a username, an email address or an id; `owner_email_change` never carries the address either, `instance_key` never the fingerprint, and `users_over_limit` never says who. Ignore the keys you do not know: a later version may add some.
- 📏 Compare `users_used` with `users_limit` to know when an instance is full. At the limit, nobody
  can sign up without an invitation and administrators cannot create invitations: see
  «When the Instance Is Full» in [Environment Variables](configuration.md), and
  «Places and Subscription» in [Users & Invitations](users.md) for what the administrator
  sees. With `users_limit` `null` there is nothing to compare.
- `setup_expires_at` is an ISO 8601 date and time in UTC, given only while the state is `pending`.
- When the state of the restore cannot be read, the answer is still `200`, never `restore: null`:
  a restore may be waiting behind it. `restore` then reads
  `{"state": "unreadable", "reason": "io", "waiting": null, "backup_created_at": null, "stage_id": null}`,
  with `reason` `io` (its owner, its permissions or a disk error), `not_a_file` (a link or a folder in
  its place) or `invalid` (content no LibreFolio wrote): see
  [When the State of a Restore Cannot Be Read](hosting_panel_backups.md#restore-interrupted).
- It answers on a [blocked instance](hosting_instances.md#instance-block) too, as on any other. A `pending` link there
  still waits for the unblock: the setup is refused until then, and its 72 hours keep running.
- Without `LIBREFOLIO_PANEL_STATUS_TOKEN` and without the panel's keys it answers `404`. Its other
  refusals are those of every scope ([Refused Calls](#panel-api-refusals)), with the codes
  `panel_status_unauthorized` and `panel_status_unavailable`. A [signed ticket](#panel-api-tickets)
  of scope `status` opens it too.

---

## 🔗 Related

- 📄 **[Hosting for Others](hosting_providers.md)** — The Managed Profile, Your Legal Pages
- 📄 **[Hosting for Others: Your Instances](hosting_instances.md)** — The Initial Administrator, Blocking an Instance
- 📄 **[Hosting for Others: Backups and Restores](hosting_panel_backups.md)** — Backups for Your Hosting Panel, Restoring an Instance from Your Panel, The Upload Limit of a Restore
