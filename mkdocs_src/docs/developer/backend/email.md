# 📧 Email Service (SMTP)

The email service sends LibreFolio's transactional emails through an SMTP server that the administrator names in
environment variables. It can write five kinds — a password-reset link, an invitation, an address to confirm, the
activation link of the first administrator, a test message. The service lives in `backend/app/services/email/`, its
configuration in `backend/app/config/email.py`, and its hourly budget counts with the sliding-window limiter of
`backend/app/utils/runtime/rate_window.py`. For administrators, two endpoints (`backend/app/api/v1/email.py`) and
the Email tab of the settings (`frontend/src/lib/features/email/`) show the state of email and send a test email;
the administrator's guide is [Email](../../admin/email.md).

!!! note "Status: lots E1 and E2 of release 1.3 — the test email only"

    The only email with a caller is the test email an administrator sends to themselves
    ([`POST /api/v1/email/test`](#api-test)); the four builders that carry a link have no caller yet. Still open in
    E2: the Playwright test of the Email tab and its gallery screenshot. See [Coming Next](#coming-next).

---

## 🎯 Purpose and Rules {: #purpose-and-rules }

Email is optional (feature F04 of the release 1.3 plan). Three rules shape the whole package:

1. **Optional.** With `LIBREFOLIO_SMTP_HOST` unset or blank, email is off and nothing changes for a self-hosted
   install: nothing is sent, the other `LIBREFOLIO_SMTP_*` variables are not even validated, and the configuration
   check reports `ok`. "Email off" is the default state, so a caller handles `EmailUnavailableError` as a normal
   outcome, not as a fault.
2. **Environment only.** The configuration comes only from the `LIBREFOLIO_SMTP_*` variables, and the password also
   from a secret file (`LIBREFOLIO_SMTP_PASSWORD_FILE`). It is never written anywhere, so it is never in the
   database and never in a backup; it is never shown in the interface either.
   [`GET /api/v1/email/status`](#api-status) answers with the state, the problem and the variable at fault, the
   checks' i18n keys and `detail`, and the hourly budget: never the host, the port, the user, the sender, the
   Reply-To or the password. The `detail` of a check, the part meant for the interface, never holds the host, the
   user or the sender either. The public [`GET /api/v1/system/instance`](#instance-email) says only whether email
   is usable.
3. **Read at every call.** The accessors read the process environment each time, nothing is cached, and they are
   the only readers of these variables, as the [config package rule](../architecture/settings.md) requires. The
   variables are documented, commented, in the «Email» section of `.env.example`.

| Module | Role |
|--------|------|
| `backend/app/config/email.py` | The `LIBREFOLIO_SMTP_*` accessors and `EmailConfigError` |
| `services/email/smtp.py` | The transport: `deliver()`, `SmtpServer`, `SmtpErrorCode`, `SmtpDeliveryError` |
| `services/email/delivery.py` | `email_config_state()`, `email_available()`, the hourly budget (`INSTANCE_BUDGET`, `budget_status()`), `send_email()` and the `EmailError` family |
| `services/email/messages.py` and `templates/` | `EmailKind`, `email_language()`, the five builders and `compose_message()`; the texts in four languages and the HTML layout. Nothing here sends, reads the configuration or logs |
| `services/email/checks.py` | `check_smtp_configuration()`, `check_smtp_encryption()`, `EMAIL_CONFIG_CHECKS`, which closes the platform's `CONFIG_CHECKS` |
| `services/email/flows.py` | `account_language()` and `send_test_email()`: what an action of the application sends, to whom and in which language ([Flows](#flows)) |
| `backend/app/api/v1/email.py` and `backend/app/schemas/email.py` | `GET /email/status` and `POST /email/test`, for administrators only, and their response models ([The API](#api)); `EmailInstanceConfig`, the `email` field of `GET /system/instance` |
| `backend/app/utils/runtime/rate_window.py` | `SlidingWindowLimiter` and `RateDecision`, the [sliding-window limiter](#rate-window) |
| `frontend/src/lib/features/email/` and `frontend/src/lib/i18n/email/` | The Email tab of the settings, its seam over the API client and its texts ([The Email Tab](#email-tab)) |

`services/email/__init__.py` holds only the package docstring.

---

## ⚙️ Configuration {: #configuration }

### 📋 The Variables

| Variable | Unset or blank | Accepted | Code when unusable |
|----------|----------------|----------|--------------------|
| `LIBREFOLIO_SMTP_HOST` | Email off | A host name or an IP address, IPv6 without brackets: letters, digits, `.`, `-`, `_` and `:`; no scheme, user, port, path, bracket or space | `SMTP_HOST_INVALID` |
| `LIBREFOLIO_SMTP_TLS` | `starttls` | `starttls`, `tls` or `none`, in any case | `SMTP_TLS_INVALID` |
| `LIBREFOLIO_SMTP_PORT` | The port of the mode: 587 (`starttls`), 465 (`tls`), 25 (`none`) | ASCII digits, 1–65535 | `SMTP_PORT_INVALID` |
| `LIBREFOLIO_SMTP_USER` | No authentication | Any text, stripped | `SMTP_CREDENTIALS_INCOMPLETE` without a password |
| `LIBREFOLIO_SMTP_PASSWORD`, or `LIBREFOLIO_SMTP_PASSWORD_FILE` | No password | `env_secret("LIBREFOLIO_SMTP_PASSWORD")`: the value as written, otherwise the content of the file | `SMTP_PASSWORD_UNREADABLE` (a `_FILE` that cannot give it); `SMTP_CREDENTIALS_INCOMPLETE` without a user |
| `LIBREFOLIO_SMTP_FROM` | Required with a host | One mailbox: `Name <address>` or `address` | `SMTP_FROM_MISSING`, `SMTP_FROM_INVALID` |
| `LIBREFOLIO_SMTP_REPLY_TO` | Replies go to the sender | One mailbox | `SMTP_REPLY_TO_INVALID` |
| `LIBREFOLIO_SMTP_MAX_PER_HOUR` | 50 | ASCII digits, at least 1 | `SMTP_MAX_PER_HOUR_INVALID` |

- **Blank is unset**, and values are stripped — except the password, which `env_secret()` takes as written, spaces
  included ([Secrets from Files](../architecture/security.md#secrets-from-files)).
- **The modes**: `starttls` upgrades a plain connection before anything else is sent and refuses to go on without
  the upgrade; `tls` is TLS from the first byte (SMTPS); `none` sends in clear, meant for a relay on the same machine
  or the local network (the [encryption check](#configuration-checks) warns otherwise).
- **ASCII digits** is literal: a sign, a decimal, `2_525` or fullwidth digits, all of which `int()` would take, are
  refused.
- **A mailbox** is exactly one address, with a non-empty local part and domain and no whitespace inside; a comma
  inside a quoted display name belongs to the name. A CR or LF anywhere in the raw value is refused, even where
  stripping would remove it: no header injection reaches a message.
- **The `:` of the host** is there for IPv6 literals, written without brackets (`::1`, `fd00::25`); `[::1]` is
  refused. A value with exactly one colon, such as `smtp.example.com:587`, is a name with its port and is refused
  too, with a message saying that the port goes in `LIBREFOLIO_SMTP_PORT`: an IPv6 address always has at least two
  colons.

### 🧾 `EmailConfigError`

`EmailConfigError` is a `ValueError` with two attributes, `variable` and `code`. Its message is
`<VARIABLE>: <rule>`, for example `LIBREFOLIO_SMTP_PORT: expected a whole number from 1 to 65535`: it never holds
the value of a variable, so never a secret. The accessors raise it for the six `*_INVALID` codes. The other three
codes combine several variables, so `email_config_state()` decides them: `SMTP_PASSWORD_UNREADABLE`,
`SMTP_CREDENTIALS_INCOMPLETE` and `SMTP_FROM_MISSING`.

### 🔌 Email Off, Usable or Unusable {: #config-state }

`email_config_state()` (in `delivery.py`) reads every variable through its accessor and **never raises**. It
returns a frozen `EmailConfigState`:

| State | `configured` | `problem`, `variable` | `server`, `sender`, `reply_to`, `max_per_hour` | `usable` |
|-------|--------------|-----------------------|-----------------------------------------------|----------|
| Off: no host | `False` | `None` | Unset; `max_per_hour` 50 | `False` |
| Unusable | `True` | The code and the variable at fault | Unset; `max_per_hour` 50 | `False` |
| Usable | `True` | `None` | The `SmtpServer`, the two mailboxes as `(display name, address)`, the hourly limit | `True` |

The first fault wins, in this order: the host; then the TLS mode, the port, the user, the password, the sender, the
Reply-To and the hourly limit (an `EmailConfigError`, or a `SecretFileError` reported as `SMTP_PASSWORD_UNREADABLE`
on `LIBREFOLIO_SMTP_PASSWORD_FILE`); then the credentials, which come in pairs (`SMTP_CREDENTIALS_INCOMPLETE` on
whichever of `LIBREFOLIO_SMTP_USER` and `LIBREFOLIO_SMTP_PASSWORD` is set without the other); then the sender
(`SMTP_FROM_MISSING`).

An unusable value **turns email off**: `send_email()` raises `EmailUnavailableError` with the problem code, and
the check `email.smtp` reports an `error`. The fault is logged **once per process**: `_report_invalid()` is a
`functools.cache` keyed by `variable`, `problem` and `reason`, so the event
`Email configuration cannot be used: email stays off`, with those three fields, appears the first time a fault is
read, not at every send. A different reason is new information and is logged again, such as a password file that
was missing and is now empty. The `reason` is the accessor's message or the `SecretFileError` message, which names
the variable and the path of the file, never its content: no secret reaches the log.

The server starts either way. The startup audit reads the configuration at every start of every process, through
the two [configuration checks](#configuration-checks): an unusable value is logged there, first by
`_report_invalid()`, then as the `email.smtp` error of the audit. Later reads in the process log it again only for a
new reason. `log_configuration_audit()` never stops a start for email, only for the platform's own secrets and
settings ([Configuration Checks](../architecture/security.md#configuration-checks)).

---

## 📡 Transport (`smtp.py`) {: #transport }

`deliver(server, message)` sends one `EmailMessage` through one `SmtpServer` with the standard library's
`smtplib`: no third-party SMTP client. It **blocks**, so it runs in a worker thread: `send_email()` calls it
through `asyncio.to_thread()`, as the [Event Loop Blocking Rule](../architecture/patterns/async.md) requires, and a
test checks that the connection is opened on a thread without a running event loop.

`SmtpServer` is a frozen dataclass: `host`, `port`, `tls` (`starttls`, `tls` or `none`), `user`, `password` (kept
out of `repr`) and `timeout`. `email_config_state()` builds it with `SMTP_TIMEOUT_SECONDS`, **20 s**, read at call
time. It is the socket timeout to connect and for each exchange with the server, not a deadline for the whole
conversation.

The conversation:

1. **Connect**: `smtplib.SMTP_SSL` in `tls` mode, `smtplib.SMTP` otherwise; then `EHLO`.
2. **`starttls` mode**: `STARTTLS`, then `EHLO` again. A server that does not offer STARTTLS is refused with
   `TLS_FAILED` before the password or the message is sent: the mode never falls back to plain text.
3. **Authentication**, only with a user: `login()`.
4. **The message**: `send_message()`; the envelope sender is the From address, the recipient the To address.
5. **`QUIT`**. Once the server has accepted the message, a failure here — a `QUIT` answered badly, a dropped
   connection — is not a failure of the delivery: the email counts as sent.

Both TLS modes use `ssl.create_default_context()`, which **verifies** the certificate and the host name.
`smtplib`'s own default for `starttls()` and `SMTP_SSL` is an unverified context (`ssl._create_stdlib_context()`),
which is why `deliver()` always passes its own.

A failure raises `SmtpDeliveryError` with a code from `SmtpErrorCode`, a `StrEnum` whose values are the names:

| Code | When |
|------|------|
| `CONNECTION_FAILED` | The connection could not be opened or was lost: nothing listening, a name that does not resolve, a refused greeting, a network error outside the TLS step |
| `TLS_FAILED` | STARTTLS not offered or refused, a failed handshake, a certificate that does not verify (`ssl.SSLError` at any step) |
| `AUTH_FAILED` | The credentials were refused, or another SMTP error ended the login step (a server without `AUTH`, for one) |
| `SENDER_REFUSED` | `MAIL FROM` refused |
| `RECIPIENT_REFUSED` | `RCPT TO` refused |
| `TIMEOUT` | A `TimeoutError` anywhere in the exception chain: `smtplib` turns a read that timed out into `SMTPServerDisconnected` |
| `SEND_FAILED` | `DATA` refused, or another protocol error while sending |

`str()` of the error is the code alone, for the interface. `detail` holds what the server said (such as
`550 5.1.1 <alice@example.com>: Recipient address rejected`), or the exception's text, **raw**: the transport adds no
password and masks nothing. It leaves the process only through the `Email not sent` log, which masks it
([What Is Logged](#logs)). The original exception is dropped (`raise … from None`).

---

## 📤 Delivery (`delivery.py`) {: #delivery }

### ⏳ The Hourly Budget {: #hourly-budget }

`INSTANCE_BUDGET` is a `SlidingWindowLimiter` over 3600 s (`BUDGET_WINDOW_SECONDS`) with a single key, shared by
every send of the process. `send_email()` hits it with `limit=` the configured `LIBREFOLIO_SMTP_MAX_PER_HOUR`,
read at call time; `budget_status(max_per_hour=None)` peeks it with the limit it is given (the status passes the one
of the state it has just read) or else the configured one, and returns its `RateDecision` (`allowed`, `remaining`,
`retry_after`) without spending anything, for [`GET /api/v1/email/status`](#api-status).

- **One unit per attempt.** An attempt that passes the configuration and recipient checks spends one unit before
  any connection, whether the server then accepts the message or not.
- **Refusal before any connection.** With the budget spent, `send_email()` raises `EmailRateLimitedError` without
  opening a connection; its `retry_after` is the number of seconds until the oldest send of the hour leaves the
  window. A refused attempt is not recorded, so it never pushes that moment further.

!!! warning "Per process, not per instance"

    The budget lives in the memory of each process: with N worker processes the instance may send N times
    `LIBREFOLIO_SMTP_MAX_PER_HOUR` emails an hour, and a restart starts from zero. `.env.example` says so: the limit
    is per server process. `GET /api/v1/email/status` shows the budget of the process that answers it.

### 📨 `send_email()` {: #send-email }

`async def send_email(content, *, to, user_id=None)` sends one `EmailContent` to one address. It reads the
configuration with `asyncio.to_thread(email_config_state)`: with `LIBREFOLIO_SMTP_PASSWORD_FILE` that read opens a
file, and no file is read on the event loop.

```mermaid
flowchart TD
    Call["send_email(content, to, user_id)"] --> State{"email_config_state()<br/>in a worker thread: usable?"}
    State -->|"no host"| Off["EmailUnavailableError<br/>EMAIL_NOT_CONFIGURED"]
    State -->|"unusable value"| Bad["EmailUnavailableError<br/>the SMTP_* problem code"]
    State -->|yes| Compose["compose_message()"]
    Compose -->|"not exactly one address"| Value["EmailRecipientError<br/>a ValueError"]
    Compose --> Budget{"INSTANCE_BUDGET.hit()"}
    Budget -->|refused| Limited["EmailRateLimitedError<br/>retry_after"]
    Budget -->|"allowed: one unit spent"| Thread["asyncio.to_thread(smtp.deliver)"]
    Thread -->|"SmtpDeliveryError"| Failed["EmailDeliveryError<br/>the SmtpErrorCode"]
    Thread -->|accepted| Sent["Email sent"]
```

| Raised | `code` | When | Budget |
|--------|--------|------|--------|
| `EmailUnavailableError` | `EMAIL_NOT_CONFIGURED`, or the problem code of the configuration | No host, or an unusable value | Not spent |
| `EmailRecipientError` (a `ValueError`) | — | `to` is not exactly one address | Not spent |
| `EmailRateLimitedError` | `EMAIL_RATE_LIMITED`; `retry_after` in seconds | The hourly budget is spent | Not spent; no connection |
| `EmailDeliveryError` | A `SmtpErrorCode` value | The server did not take the message | Spent |

The three `Email*Error` classes derive from `EmailError`, which carries `code`: a caller needs a single
`except EmailError`. `EmailRecipientError`, from `messages.py`, is not part of the family: it subclasses
`ValueError`, and a caller that maps it to an answer catches it by name, never as any `ValueError`.

### 📝 What Is Logged {: #logs }

| Event | Level | Fields |
|-------|-------|--------|
| `Email sent` | `info` | `kind`, `language`, `user_id`, `recipient_domain` |
| `Email not sent` | `warning` | `kind`, `code`, `detail` (masked), `user_id`, `recipient_domain` |
| `Email not sent: the hourly limit of the instance is reached` | `warning` | `kind`, `user_id`, `recipient_domain`, `retry_after` (rounded) |
| `Email configuration cannot be used: email stays off` | `error` | `variable`, `problem`, `reason`; once per process for each combination of the three |
| `Test email sent by an administrator` | `info` | `admin_id`, `language`: logged by [`POST /email/test`](#api-test) after `Email sent` |

**Never logged**: the body (text and HTML), the link it carries and its token, the SMTP password, the recipient's
full address. The recipient appears as the domain of its address and as the `user_id` the caller passes.

That holds for the server's own words too. Servers quote the address they refuse, so before `detail` reaches the
`Email not sent` event, `_redacted()` replaces the SMTP password with `***` and the recipient's address with
`***@<domain>`, both matched case-insensitively: `550 5.1.1 <alice@example.com>: Recipient address rejected` is
logged as `550 5.1.1 <***@example.com>: Recipient address rejected`.

An unavailable email or a malformed recipient raises without an event of its own, beyond the one-time configuration
error.

---

## ✉️ Messages (`messages.py` and `templates/`) {: #messages }

### 🗂️ The Five Kinds

Each kind of email has a keyword-only builder that returns an `EmailContent`, a frozen dataclass with `kind`,
`language`, `subject`, `text` (the plain-text part) and `html`:

| `EmailKind` | Builder | Arguments | Link |
|-------------|---------|-----------|------|
| `password_reset` | `build_password_reset()` | `language`, `username`, `link`, `ttl`, `instance` | Yes |
| `invite` | `build_invite()` | `language`, `link`, `ttl`, `instance`, `inviter=None`, `grants_admin=False` | Yes |
| `email_verification` | `build_verification()` | `language`, `username`, `link`, `ttl`, `instance` | Yes |
| `admin_setup` | `build_admin_setup()` | `language`, `username`, `link`, `ttl`, `instance` | Yes |
| `test` | `build_test_message()` | `language`, `username`, `instance` | No |

- The four link kinds share their values with the purposes of the
  [single-use account tokens](../architecture/security.md#account-tokens), but the builders issue no token: the
  caller passes the finished link and its lifetime (`ttl`).
- A link must start with `http://` or `https://` and hold no whitespace; anything else (`javascript:`, `data:`,
  `mailto:`, a relative path) is a `ValueError`. Plain `http://` is accepted for an instance on a home network.
- An invitation opens without a name (the account does not exist yet), names the inviter only when `inviter` is
  given, and adds one sentence when `grants_admin` is true.
- `instance` names the instance in the body and in the footer; the test email passes the host the request was sent
  to ([`POST /email/test`](#api-test)).

Only `build_test_message()` has a caller today, [`send_test_email()`](#flows); the four link kinds have none yet
([Coming Next](#coming-next)).

### 🌍 Languages

`EMAIL_LANGUAGES` is `("en", "it", "fr", "es")`, exactly the choices of the `default_language` setting (a test
compares the two), so no account can pick a language its emails lack. `email_language(tag)` lowercases the tag,
keeps its primary subtag and falls back to English: `it-IT`, `it_IT` and `IT` give `it`; `de`, an empty tag or
`None` give `en`. Every builder passes its `language` through it.

### 🛡️ Rendering Rules

- **Placeholders**: the texts use `string.Template` placeholders — `$username`, `$instance`, `$inviter`,
  `$duration` — filled with `substitute()`.
- **Escaping**: every line of the HTML part is escaped (`html.escape`) after it is filled, so a value that comes
  from a person — a user name, the name of the instance, the inviter — stays text, never markup. The link is
  escaped in its `href` and in the visible fallback address.
- **Subjects**: the subject is the catalogue's text, never filled: no user value and no link reaches it, and it
  stays on one line. Every relay and every notification sees it.
- **Durations**: `$duration` is `babel.dates.format_timedelta(ttl, locale=language)`, Babel's default wording:
  30 minutes in Italian gives «30 minuti», 7 days in English "1 week", 72 hours in Italian «3 giorni».
- **The two parts**: the plain text holds the greeting, the body lines, for a link kind the action followed by the
  link verbatim on its own line, the closing lines, then a `-- ` signature line and the footer. The HTML part fills
  `templates/layout.html` (`$lang`, `$subject`, `$body`, `$footer`): a table-based layout with inline styles, a
  button for the link and, below it, the address to copy (`common.button_fallback`); `<html lang="…">` declares the
  language.
- The catalogues and the layout are read once, when `messages.py` is imported.

### 📚 The Catalogue {: #catalogue }

`templates/en.json`, `it.json`, `fr.json` and `es.json` share one structure: a `common` section (`greeting`,
`greeting_anonymous`, `button_fallback`, `footer`) and one section per `EmailKind` value, holding `subject`,
`intro` and, for the link kinds, `action`, `expiry` and `ignore`; `invite` adds `intro_anonymous` and
`admin_role`; `test` has `outro` instead.

`./dev.py test services email-messages` guards the catalogue:

- the four JSON files and `layout.html` exist in `templates/`, beside `messages.py`;
- each file parses as UTF-8 JSON, with an object at its root;
- every file has exactly the nested keys of `en.json`: a text missing in one language is a gap, an extra one is
  dead;
- every leaf is a non-empty string;
- for each key, the `$placeholders` are the same set as in English: a translation neither drops a value nor
  invents one;
- every text is valid `string.Template` syntax: no stray `$` (write `$$` for a literal dollar sign).

These texts are the backend's own catalogue: the frontend i18n sources and the `dev.py i18n` commands do not
include them.

### ➕ Adding a Text or a Kind {: #adding-a-text-or-a-kind }

**A text**: add the key to the same section of the four JSON files in one change, with the same `$placeholders`
in every language, then list it in the builder (the `before` or `after` keys that `_render()` assembles).

**A kind**:

1. a value in `EmailKind`, which is also the name of its catalogue section;
2. that section in the four JSON files, with a `subject` free of placeholders;
3. a keyword-only `build_*` builder that passes the language through `email_language()`, the link through
   `_checked_link()` and the lifetime through `_duration()`, and puts user values only into body placeholders;
4. the tests of `backend/test_scripts/test_services/test_email_messages.py`, which pin the five kinds and the
   signature of each builder.

### 📬 Composing the Message {: #composing }

`compose_message(content, *, to, sender, reply_to=None, now=None)` returns the `EmailMessage` to send:

| Header | Value |
|--------|-------|
| `Subject` | `content.subject` |
| `From` | `sender`, a `(display name, address)` tuple; a non-ASCII name is encoded as RFC 2047 words |
| `To` | `to`, exactly one bare address |
| `Reply-To` | Only when `reply_to` is given |
| `Date` | `now`, or the current time, in GMT |
| `Message-ID` | `make_msgid()` in the domain of the sender's address, never the name of the machine |
| `Auto-Submitted` | `auto-generated`: auto-responders do not answer (RFC 3834) |
| `X-Auto-Response-Suppress` | `All`: Exchange and Outlook send no automatic reply |
| `Content-Language` | `content.language` |

The body is `multipart/alternative`, the plain text first and the HTML last: a client shows the last alternative it
can display. `Content-Language` is set **after** the body, because `set_content()` clears every `Content-*` header
and turning the message into a multipart moves them into its first part.

`to` must be **exactly one** bare address: one `@` with something on both sides, and no whitespace (not even a
trailing line break: nothing is trimmed), comma, `<`, `>` or `"`. Anything else is an `EmailRecipientError` (a
`ValueError`), so no message is composed for a second, hidden recipient.

---

## 🩺 Configuration Checks (`checks.py`) {: #configuration-checks }

The email section has two checks in the shape of the platform's `ConfigCheck`
([Configuration Checks](../architecture/security.md#configuration-checks)). Like every configuration check, they
read the configuration through `email_config_state()`, change nothing, never raise and never put a secret in their
result:

| `check_id` | Severity | `i18n_key` | When |
|------------|----------|------------|------|
| `email.smtp` | `ok` | `email.checks.smtp.off` | No host: email is optional |
| `email.smtp` | `ok` | `email.checks.smtp.ok` | The configuration is usable |
| `email.smtp` | `error` | `email.checks.smtp.invalid` | A value cannot be used: `detail` is `{"problem": <code>, "variable": <name>}`; the summary names the variable and says that email stays off |
| `email.smtp_encryption` | `ok` | `email.checks.smtpEncryption.ok` | Email is not usable, or the mode is `starttls` or `tls` |
| `email.smtp_encryption` | `ok` | `email.checks.smtpEncryption.localPlain` | `none` towards a local host |
| `email.smtp_encryption` | `warning` | `email.checks.smtpEncryption.plain` | `none` towards any other host: emails, their links and the SMTP password travel unencrypted. Empty `detail` |

**What counts as local**: an IP address that `classify_ip()` (`backend/app/utils/runtime/network.py`) classes as
`loopback` (127.0.0.0/8, `::1`), `lan` (the private, link-local and unique-local ranges) or `vpn` (100.64.0.0/10
and Tailscale's `fd7a:115c:a1e0::/48`); or a name that is `localhost`, has a single label (a Docker service such as
`postfix`, a host of the LAN) or ends with `.localhost`, `.local`, `.lan`, `.home.arpa` or `.internal`. Names are
judged as written, nothing is resolved: a tailnet name such as `relay.tailnet.ts.net` gets the warning, while its
`100.x` address would not.

The `detail` travels to the admin interface as the parameters of a translated message, so it never names the host,
the user or the sender. The English `summary` is for the log only, and the plain-text warning's summary does name
the host. [`GET /api/v1/email/status`](#api-status) never returns a `summary`. The keys are written whole, like the
platform's; their messages are in the `email` i18n source of the frontend ([The Email Tab](#email-tab)).

`EMAIL_CONFIG_CHECKS = (check_smtp_configuration, check_smtp_encryption)` closes the platform's `CONFIG_CHECKS`
(`*EMAIL_CONFIG_CHECKS` at the end of the tuple in `backend/app/services/platform/config_audit.py`), so the two
checks run in two places:

- **At startup**, `log_configuration_audit()` logs every check that is not `ok`, with its `summary` as the message
  and `check` and `detail` as fields. For email that is the `email.smtp` error,
  `<variable> cannot be used (<problem>): email stays off until it is fixed`, and the plain-text warning,
  `LIBREFOLIO_SMTP_TLS=none with <host>: emails, their links and the SMTP password travel unencrypted; use starttls or tls`.
  Neither stops the start. An unusable configuration thus gives two lines:
  `Email configuration cannot be used: email stays off` from `_report_invalid()`, while the check reads the state,
  then the audit's summary.
- **On demand**, [`GET /api/v1/email/status`](#api-status) evaluates `EMAIL_CONFIG_CHECKS` at every call and
  returns each result without its `summary`.

`config_audit` imports `EMAIL_CONFIG_CHECKS` at module level to build its tuple, before it defines `ConfigCheck`.
A module-level `from backend.app.services.platform.config_audit import ConfigCheck` in `checks.py` would therefore
fail whenever `config_audit` is imported first, on a half-initialized module. So `checks.py` imports `ConfigCheck`
inside each check, when the check runs, and under `TYPE_CHECKING` for its annotations (the module has
`from __future__ import annotations`): either module can be imported first.

---

## 🔀 Flows (`flows.py`) {: #flows }

`services/email/flows.py` has one function per email that an action of the application sends. A flow decides the
content, the recipient and the language; `send_email()` checks the configuration and the budget, sends and logs.

| Function | What it does |
|----------|--------------|
| `async account_language(session, user_id)` | The language of every email of an account: its own `user_settings.language`, else the instance's `default_language` global setting, else English. It reads the `language` column alone and `get_setting_value()`: a settings row that no longer validates (a theme outside light/dark/auto, say) never stops an email, and an account without a `user_settings` row is left without one |
| `async send_test_email(session, user, *, instance)` | `build_test_message()` in the account's language, with `user.username` and `instance`, sent to `user.email` with `user_id`; returns the language. Raises what `send_email()` raises |

- `supported_email_language()` reduces `it-IT`, `it_IT` and `IT` to `it`, and gives `None` for a language the emails
  do not speak or an empty value; `email_language()` is the same with `en` instead of `None`.
- An account whose own language is one the emails do not speak counts as an account without one: it gets the
  instance's `default_language`, then English. A missing `default_language` setting reads as `en`.
- The language rule holds for every email of an account, as the module's docstring says: a new flow for an account
  takes its language from `account_language()`.

---

## 🌐 The API (`api/v1/email.py`) {: #api }

`backend/app/api/v1/email.py` is a router with `prefix="/email"` and the tag `Email`, which `api/v1/router.py`
mounts under `/api/v1`; its response models, all `StrictModel`, are in `backend/app/schemas/email.py`. Both routes
depend on `require_admin` (`backend/app/api/v1/settings.py`): 401 without a session, 403 for an account that is not
an administrator; then the email configuration is not read, and nothing is sent or spent. One more route, outside
this router, publishes whether email is usable: [`email` in `GET /api/v1/system/instance`](#instance-email).

### 📊 `GET /api/v1/email/status` {: #api-status }

A plain `def`: reading the configuration may read the password file, so FastAPI runs the route in its thread pool,
not on the event loop. Every call evaluates `EMAIL_CONFIG_CHECKS` and `email_config_state()` afresh; it opens no
connection and resolves no name. It answers an `EmailStatusResponse`:

| Field | Value |
|-------|-------|
| `state` | `off` (no host), `ready` (usable) or `invalid` (a value cannot be used: email stays off) |
| `problem`, `variable` | `invalid` only: the code and the variable at fault, as in [Email Off, Usable or Unusable](#config-state); `null` otherwise |
| `checks` | The two checks of `EMAIL_CONFIG_CHECKS`, in that order, each an `EmailCheckRead`: `check_id`, `severity`, `i18n_key`, `detail` |
| `budget` | `ready` only: an `EmailBudgetRead` from `budget_status()`, which spends nothing — `max_per_hour`, `remaining`, and `retry_after_seconds`, the limiter's `retry_after` rounded up, 0 while an email fits |

`EmailCheckRead` is a `ConfigCheck` without its `summary`, because the English log line of the plain-text warning
names the SMTP host. No state returns the host, the port, the user, the sender, the Reply-To, the password or the
path of a password file.

### 📮 `POST /api/v1/email/test` {: #api-test }

An `async def` without a body. It calls `flows.send_test_email(session, admin, instance=request.url.netloc)`: the
test email goes to the administrator's own address, in their language, and names the instance by the host the
request was sent to, port included (behind a reverse proxy, the `Host` header it forwards): a label in the text,
never a link. Like any [`send_email()`](#send-email), it spends one unit of the budget once the configuration and the
address pass.

| Status | Body | When | Budget |
|--------|------|------|--------|
| 200 | `EmailTestResponse`: `language` (`en`, `it`, `fr` or `es`) and `message`, `Test email sent` | The server accepted the message | Spent |
| 409 | `detail`: `error_code` `EMAIL_UNAVAILABLE`, `problem`, `message` | `EmailUnavailableError`: `problem` is `EMAIL_NOT_CONFIGURED` without a host, else the code of the configuration problem | Not spent; no connection |
| 422 | `detail`: `error_code` `EMAIL_RECIPIENT_INVALID`, `message` | The administrator's stored address is not exactly one address: the `EmailRecipientError` of `compose_message()`, caught by name (another `ValueError` is a 500) | Not spent; no connection |
| 429 | `detail`: `error_code` `EMAIL_RATE_LIMITED`, `retry_after`, `message`; the `Retry-After` header | `EmailRateLimitedError`: `retry_after` and `Retry-After` are the same whole number of seconds, at least 1 | Not spent; no connection |
| 502 | `detail`: `error_code` `EMAIL_DELIVERY_FAILED`, `smtp_code`, `message` | `EmailDeliveryError`: `smtp_code` is the [`SmtpErrorCode`](#transport) | Spent |

The rows follow the order of the checks in `send_email()`: an unusable configuration answers 409 even for an
address that is not one address. `message` is a fixed English sentence; the interface translates the codes. No
answer carries the server's own words, which reach only the log, masked ([What Is Logged](#logs)). After a 200 the
route logs `Test email sent by an administrator`, with `admin_id` and `language`.

### 🌍 `email` in `GET /api/v1/system/instance` {: #instance-email }

The public configuration of the instance, which answers without a session
([Public instance configuration](../architecture/settings.md#public-instance-configuration)), has an `email` field:
an `EmailInstanceConfig` (`backend/app/schemas/email.py`) with one boolean, `available`. `get_instance_config()`
(`backend/app/api/v1/system/instance.py`) fills it with `delivery.email_available()`, which returns
`email_config_state().usable`, through `asyncio.to_thread`: the read may open the password file.

- **Usable, not delivered**: `available` is true when a server is set and every variable can be used, the state
  `ready` of [`GET /api/v1/email/status`](#api-status). Nothing is sent and no server is contacted to tell, so a
  server that refuses the login still counts as available.
- **Nothing more**: the answer is the same for whoever asks and never holds the configuration or the budget. An
  unusable value read here is logged like any other read, at most once per process for the same reason.
- **Off by default**: `available` defaults to `False`, and `InstanceConfigResponse` declares the field with
  `default_factory=EmailInstanceConfig`, so it is optional in the schema: an answer built without it, or read from
  an older server, says that nothing can be sent.

Nothing in the frontend reads it yet.

---

## 🖥️ The Email Tab {: #email-tab }

The tab is in `frontend/src/lib/features/email/`, its texts in `frontend/src/lib/i18n/email/`.

| File | Role |
|------|------|
| `emailApi.ts` | The seam over the client that `./dev.py api sync` generates: `fetchEmailStatus()` and `sendTestEmail()` call `get_email_status_api_v1_email_status_get` and `send_test_api_v1_email_test_post`. `fetchEmailStatus()` narrows the answer into `EmailStatus`, all five keys present: the generated type of an optional field is wider than its runtime schema (`string \| null` also admits an array), so `problem` and `variable` become a string or `null`, `checks` a list, `budget` an object or `null`. `readTestFailure()` reads the `detail` of a refused test — from the `AxiosError` the generated client rejects with, or from an `ApiError` — into `{errorCode, problem, smtpCode, retryAfter}`; `errorCode` is `UNKNOWN` without a `detail` object, after a network error for one |
| `emailText.ts` | Every code to a whole i18n key and every state to whole classes of the theme roles (`*-lf-*`), as string literals that the i18n audit and the colour gates can see: `STATE_LABEL_KEYS`, `STATE_BADGE_CLASSES`, `NOTICE_CLASSES`, `OUTCOME_CLASSES`. `problemKey()` falls back to `email.problems.unknown` (only the maps' own entries count: a code such as `constructor` finds nothing); `minutesUntil()` gives whole minutes, at least 1; `testFailureMessage()` falls back to `email.smtpErrors.SEND_FAILED` for an unknown `smtp_code` and to `email.test.errors.generic` for any other failure |
| `EmailSettingsTab.svelte` | The tab body, in Svelte 5 runes |

What the tab does:

- **On mount** it reads `GET /email/status`; a failure shows `email.loadError`, above the last state read if there
  is one. Only the latest read writes: an older answer never replaces a newer one. `data-busy` (and `aria-busy`) is
  `true` while a request runs, the status or the test email.
- **The state**: a badge (`email.state.*`), then the explanation for `off`; for `invalid`, the message of the
  problem with its `{variable}` and the reminder to restart; for `ready`, the budget — `email.budget.remaining`, or
  `email.budget.spent` with the minutes to wait when none is left.
- **The checks**: one line for each check that is not `ok`, except `email.smtp`, whose problem the state already
  explains. Today that leaves the plain-text warning.
- **The test email**, in `ready` only. The button is disabled while any request runs, the status read again
  included, so one click sends one email. The outcome shows below it,
  `role="status"` or `role="alert"`, rendered from the stored outcome so that it follows a change of language; then
  the tab reads the status again, so the budget follows. Each outcome is also an app event, through `notify()`
  without a toast since the outcome is already on screen: `email.test.sent` with the `language`, or
  `email.test.failed` with the failure fields.
- **The guide**: the header's `DocsLink` opens `admin/email/`, the administrator's guide.
- **Test hooks**: a `data-testid` on each part (`email-tab`, `email-state`, `email-problem`, `email-budget`,
  `email-check`, `email-test-button`, `email-test-outcome`…) and the values a test checks as `data-*` attributes:
  `data-state`, `data-problem`, `data-variable`, `data-remaining`, `data-max`, `data-check-id`, `data-severity`,
  `data-outcome`.

The texts are a subsystem source of the frontend catalogue ([The Sources](../frontend/i18n.md#sources)): its
`prefixes.txt` owns `email`, and the four languages hold the same keys. They cover the tab, the states, the nine
problem codes and `unknown`, the messages of both checks (`email.checks.*`, the `i18n_key` values of `checks.py`),
the budget, the test email and its errors, and the seven `SmtpErrorCode` values (`email.smtpErrors.*`). The emails'
own texts stay in the backend catalogue ([The Catalogue](#catalogue)).

`SETTINGS_TABS`, the [tab registry](../frontend/components/features/settings.md#tab-registry) of the Settings page,
registers the tab:

```ts
{id: 'email', labelKey: 'email.tab.label', icon: Mail, order: 130, component: EmailSettingsTab, visible: (ctx) => ctx.isSuperuser},
```

Order 130 puts it after Admin (100), so in the right-hand group on a wide screen, and `visible` keeps it for
administrators: a regular user never sees it in the bar, and a `?tab=email` they open is ignored.

---

## 🪟 The Sliding-Window Limiter {: #rate-window }

`backend/app/utils/runtime/rate_window.py` is the one primitive for every limit that counts events in a moving
window: the hourly email budget uses it, and the login and «forgot password» limits of workstream A (lot A8) are
planned to reuse it. A new limit of this kind uses it too, instead of a counter of its own.

| Member | Contract |
|--------|----------|
| `SlidingWindowLimiter(limit, window_seconds, *, max_keys=10_000, clock=time.monotonic)` | `ValueError` when `limit < 1`, `window_seconds <= 0` or `max_keys < 1`; `limit` and `window_seconds` are properties |
| `peek(key=None, *, limit=None)` | The `RateDecision` a hit would get now; counts nothing and never creates a key |
| `hit(key=None, *, limit=None)` | The same decision; records the hit only when it is allowed |
| `count(key=None)` | How many hits of `key` are in the window now |
| `reset(key=None)`, `clear()` | Forget one key, or every key |
| `len(limiter)` | The number of keys tracked |
| `RateDecision(allowed, remaining, retry_after)` | Frozen |

- **The window**: a hit at `t` counts while `clock() - t < window_seconds`; exactly `window_seconds` later it no
  longer does.
- **Allowed** while the count is below the limit: `remaining` is `limit - count` for a peek and `limit - (count + 1)`
  after an allowed hit; `retry_after` is 0.
- **Refused**: `remaining` is 0 and `retry_after = ts[count - limit] + window_seconds - now`, where `ts` are the
  live hits, oldest first: the wait until enough of them leave. With a limit of 3 and a 60 s window, hits at 1000,
  1001 and 1002 make a fourth at 1003 wait 57 s.
- **A refused hit is not recorded**: a caller that keeps knocking does not push its own unlock further away.
- **Per-call limit**: `limit=` replaces the default for that call only (below 1, a `ValueError`); lowered below the
  count, the wait is for enough hits to expire.
- **Keys** are any hashable value, and `None`, the default, is a key like any other.
- **Bounded memory**: at most `max_keys` keys. A new key beyond them evicts the least recently used one — used meaning
  peeked, hit or counted — and its hits are forgotten with it, so an evicted full key is allowed again. Only an
  allowed hit creates a key, and a key whose hits have all expired is dropped when it is next read.
- **Injectable clock**: tests move a fake clock instead of waiting.
- **Thread-safe**: one lock; threads hitting a key with a limit of N get exactly N hits allowed.
- **Per process**, in memory: with N worker processes a limit is N times the configured one, and a restart forgets
  every count.

---

## 🧪 Testing {: #testing }

| Selector | File (IDs) | What it pins |
|----------|------------|--------------|
| `./dev.py test services email-config` | `test_services/test_email_config.py` (EMC-001…019) | The accessors: blank as unset, the three modes and their ports, the port and the hourly limit in ASCII digits, one mailbox for From and Reply-To (no CR or LF, no second address), the password exactly as `env_secret()` gives it, `EmailConfigError` naming the variable and never the password, nothing cached |
| `./dev.py test services email-messages` | `test_services/test_email_messages.py` (EMM-001…030) | Languages and kinds, keyword-only builders, `http(s)` links only, escaping, no user value in a subject, Babel durations, the administrator invitation's extra sentence, the catalogue guard, the headers and parts of `compose_message()`, exactly one recipient |
| `./dev.py test services email-delivery` | `test_services/test_email_delivery.py` (EMD-001…038) | The fake server itself and `closed_port()`; `deliver()` and its error codes (TLS never falls back to plain text, a bad `QUIT` is a success, the certificate is verified); `email_config_state()` and its one-time log; the budget; `send_email()` off the event loop; no secret and no full recipient address in the logs |
| `./dev.py test services email-checks` | `test_services/test_email_checks.py` (EMK-001…015) | Both checks in every state, local and public hosts, `EMAIL_CONFIG_CHECKS`, no password in any field and no host, user or sender in a `detail`; the two checks closing the platform's `CONFIG_CHECKS` and `run_config_checks()`; the three import orders, each in a fresh interpreter; the startup audit: one `email.smtp` error and no exception for an unusable configuration, one `email.smtp_encryption` warning for plain text to a public host, nothing when email is off, never the password |
| `./dev.py test utils rate-window` | `test_utilities/test_rate_window.py` (RWL-001…017) | The window edge, `peek` never counting, refused hits not recorded, `retry_after`, the per-call limit, independent keys, LRU eviction, exactly N allowed under concurrent threads |
| `./dev.py test services email-flows` | `test_services/test_email_flows.py` (EMF-001…010) | The two signatures; `supported_email_language()`; `account_language()`: the account's own language when the emails speak it, else `default_language`, else English, never creating a `user_settings` row, and a settings row that no longer validates still giving its language; `send_test_email()`: one message to the account's own address in its language, naming the instance and the user, one unit spent; nothing sent or spent when email is off or unusable; the configuration and its password file read off the event loop |
| `./dev.py test api email` | `test_api/test_email_api.py` (EMA-001…022) | Admin only: 401 without a session, 403 for a member, nothing sent or spent; the status in its three states with both checks and, when ready, the budget, never the SMTP configuration or a check's `summary`, without a connection or a name lookup; the test email in the administrator's language, naming the request's host with its port; 409, 422 (only for `EmailRecipientError`: another `ValueError` is a 500), 429 with `Retry-After` and 502 with the `SmtpErrorCode`, no secret and no server words in an answer; a settings row that no longer validates still sending; both routes reading the configuration off the event loop; `GET /system/instance`: no session needed, `email` exactly `{available}` in each state, never a value of the configuration, no connection and no name lookup, the password file read off the event loop, `available: false` when the answer is built without it |
| `./dev.py test front-utility core-unit` | `frontend/src/lib/features/email/emailText.test.ts`, `emailApi.test.ts` | The code-to-key maps (own entries only), the minutes, the failure messages and their keys in the four catalogues, the role classes (no palette class, no hex, no `dark:`); `fetchEmailStatus()` narrowing the answer; `readTestFailure()` on an `AxiosError` and on an `ApiError`, with the real client and a fake transport |
| `./dev.py test front-utility component-unit` | `frontend/src/lib/features/email/EmailSettingsTab.test.ts` | The tab in jsdom: each state, the notices, the budget, `data-busy` over every request, one email per click, the outcome after 200, 409, 422, 429, 502 and a network error, a failed read keeping the last state |
| `./dev.py test front-utility email-tab` | `frontend/e2e/settings/email-tab.spec.ts` | In the browser: an administrator's tab on the real backend in the `off` state, hidden from a member; the test email against a simulated API (200, 502, 429) |

The backend files are under `backend/test_scripts/`. All seven backend entries are `pure` in the runner catalogue:
no lane database, no server. The two E2 files build their database as a private SQLite file under `tmp_path`, and
`api email` mounts the real auth and email routers under the API prefix in an app of its own: its accounts sign in
through `POST /auth/login`, over `httpx.ASGITransport`. The Settings tab registry's own test
(`settingsTabs.test.ts`) pins the Email tab: administrators only, no props, after Admin. The gallery has a
`settings/email` shot, with the state answered `ready` by the test.

- **No inherited configuration.** Every module, the rate window's included, starts with an autouse fixture that
  removes every `LIBREFOLIO_SMTP_*` variable; each test then sets only what it needs with `monkeypatch`, and
  password files live in `tmp_path`. A test lane already drops them: `configure_test_runtime()`
  (`scripts/cli_base.py`) removes every variable `.env.example` documents and every `LIBREFOLIO_*` name, so the
  lane's server runs without email. The fixture keeps a run outside a lane honest too: a new email test follows the
  same rule and never reads the lane's environment.
- **Never a real network.** `FakeSmtpServer` (`backend/test_scripts/fixtures/email/fake_smtp.py`) is written with
  the standard library and listens on 127.0.0.1, on a port the OS picks. It speaks the part of SMTP that `smtplib`
  uses (`EHLO` with `AUTH PLAIN LOGIN`, `STARTTLS` only when given a `tls_context`, `MAIL`, `RCPT`, `DATA`, `QUIT`),
  can refuse at each step (`credentials`, `refuse_sender`, `refuse_recipients`, `refuse_data`, `quit_code`,
  `greet=False`), and records `messages`, `auth_attempts` and `connections`. A refused recipient is named in the
  `550` reply, as Postfix does, so the masking of the log meets a real server's habit. As a context manager it
  closes every socket, joins every thread and fails the test on a defect of its own. `closed_port()`, also a context
  manager, yields a port of 127.0.0.1 that refuses connections and holds it for the whole block, so no listener
  started meanwhile can take it. In `api email`, `socket.getaddrinfo` resolves the loopback only and records any
  other name, which proves that the status never looks up the configured host.
- **No waiting.** The delivery, flows and API tests replace `delivery.INSTANCE_BUDGET` with a limiter on a fake
  clock, clear the cache of `_report_invalid()` around each test, and lower `smtp.SMTP_TIMEOUT_SECONDS` to 5 s as a
  bound for a hang; both are module attributes read at call time for that purpose. The only real wait is the timeout
  test, 0.2 s.
- **TLS tests.** EMD-017 (STARTTLS against a certificate the client trusts) and EMD-018 (an untrusted
  certificate refused: the verification is real) build their certificates with `cryptography`, a dependency of the
  `Pipfile` since release 1.3; `pytest.importorskip` still skips them in an environment without it.

---

## 🔭 Coming Next {: #coming-next }

Still open in lot E2: the Playwright test of the Email tab and its gallery screenshot.

Planned in later lots of workstream E; none of it is in the code yet:

- **E3**: the links of an email (`links.py`), password-reset links sent by email, and the activation link of the
  first administrator;
- **E4**: the «forgot password» form and «Send by email» next to the copied invitation and reset links;
- **E5**: email verification, whose meaning is still a decision of the developer.

---

## 🔗 Related

* 📧 **[Email](../../admin/email.md)** — The administrator's guide: the variables, the Email tab, what to check
  when email does not work
* 🔐 **[Secrets from Files](../architecture/security.md#secrets-from-files)** — `env_secret()` and the `_FILE` form
  of a secret
* 🩺 **[Configuration Checks](../architecture/security.md#configuration-checks)** — `ConfigCheck`, `CONFIG_CHECKS`
  and the startup audit
* 🎟️ **[Single-use Account Tokens](../architecture/security.md#account-tokens)** — the tokens behind the links these
  emails carry
* ⚡ **[Asynchronous Architecture](../architecture/patterns/async.md)** — the Event Loop Blocking Rule
* ⚙️ **[Settings System](../architecture/settings.md)** — the `backend/app/config/` package and `.env.example`
* 🌍 **[Internationalization](../frontend/i18n.md#sources)** — the i18n sources, the `email` subsystem among them
* 🗂️ **[Tab registry](../frontend/components/features/settings.md#tab-registry)** — `SETTINGS_TABS`, the tabs of
  the Settings page
