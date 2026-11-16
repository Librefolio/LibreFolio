# 🛠️ Email: When It Does Not Work

Diagnosis page: emails do not go out.
For every error you find **what you see**, **why** and **what to do**, with the place where you act.

How to set email up and its test email: [Email](email.md).
The messages LibreFolio sends: [Email: Links and Messages](email_flows.md).

---

## 🛠️ When It Does Not Work {: #troubleshooting }

Two kinds of problem:

| What you see | Why | Where to look |
| --- | --- | --- |
| State **Not working** as soon as you open the **Email** tab | A variable LibreFolio cannot use | [Configuration Problems](#configuration-problems) |
| The error shows only when you send an email | The SMTP server refuses the email or does not answer | [Sending Errors](#sending-errors) |

A configuration that cannot be used turns only email off: the server starts as usual and everything else works.

Where you act, in the tables of this page:

| Where | What | Afterwards |
| --- | --- | --- |
| **`.env`** — LibreFolio's `.env` file ([where it lives](email.md#where-it-lives)) | The `LIBREFOLIO_SMTP_…` variables and `LIBREFOLIO_PUBLIC_URL` | Restart LibreFolio. With Docker Compose, run `docker compose up -d`. |
| **SMTP server** — the server or the provider | Login, allowed senders, certificate, relay | Try the test email again. |
| **Interface** — **Settings › Administration › Email**, [Profile](../user/settings/profile.md), [Users & Invitations](users.md#actions) | State, test email, your address, the accounts | No restart. |
| **Log** | The server's exact reply and the code | [What the Log Says](#logs): where to read it. |

### ⚙️ Configuration Problems {: #configuration-problems }

**Where: LibreFolio's `.env` file.** The **Email** tab names the variable; the code is in the log, right after `Starting LibreFolio`.
After every fix: restart LibreFolio. With Docker Compose, run `docker compose up -d`.

| What you see (tab) | Code | Why | What to do |
| --- | --- | --- | --- |
| `LIBREFOLIO_SMTP_HOST` is not a valid server name… | `SMTP_HOST_INVALID` | Not just a name or an IP address | `smtp.example.com`, not `smtp://smtp.example.com`, `smtp.example.com:587` or `user@smtp.example.com`. The port goes in `LIBREFOLIO_SMTP_PORT`; an IPv6 address without square brackets. |
| `LIBREFOLIO_SMTP_TLS` must be starttls, tls or none. | `SMTP_TLS_INVALID` | Word not allowed | One of the three. Encryption from the first byte, port 465: `tls`. |
| `LIBREFOLIO_SMTP_PORT` must be a whole number from 1 to 65535. | `SMTP_PORT_INVALID` | Out of range or not numeric | Digits only, or remove the line: the port of the mode applies. |
| The password file named by `LIBREFOLIO_SMTP_PASSWORD_FILE` cannot be read. | `SMTP_PASSWORD_UNREADABLE` | The file does not exist at that path (with Docker, the path inside the container), the user that runs LibreFolio cannot read it, it is empty or blank, not UTF-8, or larger than 64 KiB | The log says which: file system or path. |
| `LIBREFOLIO_SMTP_USER` is set alone… (or `LIBREFOLIO_SMTP_PASSWORD`) | `SMTP_CREDENTIALS_INCOMPLETE` | User without password or the other way round. A password from `LIBREFOLIO_SMTP_PASSWORD_FILE` counts as `LIBREFOLIO_SMTP_PASSWORD` | Both, or neither. |
| `LIBREFOLIO_SMTP_FROM` is missing… | `SMTP_FROM_MISSING` | Required as soon as you set a server | Add the sender. |
| `LIBREFOLIO_SMTP_FROM` must be one address… | `SMTP_FROM_INVALID` | List or line break | One address, with or without a name: `LibreFolio <noreply@example.com>`. |
| `LIBREFOLIO_SMTP_REPLY_TO` must be one address. | `SMTP_REPLY_TO_INVALID` | Same rule as the sender | One address, or remove the line. |
| `LIBREFOLIO_SMTP_MAX_PER_HOUR` must be a whole number of at least 1. | `SMTP_MAX_PER_HOUR_INVALID` | Not a whole number ≥ 1 | Digits only, at least `1`. To stop sending, remove `LIBREFOLIO_SMTP_HOST` instead. |
| `LIBREFOLIO_SIGNUP_EMAILS_PER_ADDRESS` must be a whole number of at least 1. | `SIGNUP_EMAILS_PER_ADDRESS_INVALID` | Not a whole number ≥ 1. Like the others, it turns email off until you fix it; the server starts anyway | Digits only, at least `1`, or remove the line: default `20`. |

### 📤 Sending Errors {: #sending-errors }

The test email, in **Settings › Administration › Email**, says why it did not go out.
The server's exact reply is in the log ([What the Log Says](#logs)).

| What you see (test email) | Code | Why | What to do — where |
| --- | --- | --- | --- |
| LibreFolio cannot reach the SMTP server… | `CONNECTION_FAILED` | Server name, port or firewall. The name counts from where LibreFolio runs: in a container, `localhost` is the container itself | **`.env`**: `LIBREFOLIO_SMTP_HOST`, `LIBREFOLIO_SMTP_PORT`. **Network**: a firewall that refuses the connection. |
| The secure connection failed… | `TLS_FAILED` | Mode and port do not go together; with `starttls` the server does not offer encryption; certificate not valid or not issued for the name in `LIBREFOLIO_SMTP_HOST` (self-signed, or an IP instead of the name, fails) | **`.env`**: `starttls` with 587, `tls` with 465; in `LIBREFOLIO_SMTP_HOST` the name of the certificate. **SMTP server**: a valid certificate. |
| The SMTP server refused the login… | `AUTH_FAILED` | Wrong user or password. A server without login refuses the login | **`.env`**: user and password; with a provider, an app password. Server without login: remove both. |
| The SMTP server refused the sender address… | `SENDER_REFUSED` | The server accepts only the addresses your account may send with. Without a user, it may still require a login | **`.env`**: in `LIBREFOLIO_SMTP_FROM` one of those addresses, or add the login. |
| The SMTP server refused your address. | `RECIPIENT_REFUSED` | The email of your account. Without a login, a server may refuse to relay to other domains: the reply in the log says so | **Interface**: your address in [Profile](../user/settings/profile.md). **SMTP server**: the relay. |
| The SMTP server did not answer in time. | `TIMEOUT` | Beyond the 20 seconds LibreFolio waits for each step: a firewall that drops the connection without refusing it, or `starttls` on port 465 | **`.env`**: the mode/port pair. **Network**: the firewall. |
| The SMTP server did not take the message. | `SEND_FAILED` | The server refused the message itself. Non-ASCII letters before the `@`, such as `zoë@example.com`, need SMTPUTF8: without it, the email never leaves LibreFolio and the log reports `SMTPNotSupportedError` | **Log**: the server's reply says why. **SMTP server**: SMTPUTF8, or an ASCII address. |
| The hourly limit of … emails is reached… (state), or The hourly email limit is reached: try again in … min. (test) | `EMAIL_RATE_LIMITED` | Maximum of the hour reached | Wait the minutes shown. For more, **`.env`**: raise `LIBREFOLIO_SMTP_MAX_PER_HOUR` and restart. |
| Email is off or not working on this instance. | `EMAIL_UNAVAILABLE` | Configuration changed since you loaded the tab, for example after a restart | **Interface**: the tab now shows the state and its problem. |
| The address of your account is not a valid email address. | `EMAIL_RECIPIENT_INVALID` | The email of your account | **Interface**: correct it in [Profile](../user/settings/profile.md). |
| The test email could not be sent. | — | No known answer, for example a network error | Reload the page and look at the **log**. |
| Test email sent to your address…, but nothing arrives | — | The server accepted: from there, delivery is its job. A sender on a domain that does not authorize that server may be rejected or end up in spam along the way | Spam folder, then the **logs of the server or of the provider**. |

**The state of email could not be read.**: the tab did not reach the server. Reload; if it persists, look at the log.

**Send by email**, in the invitation and reset dialogs, says why a link did not go out:

| What you see (dialog) | Code | Why | What to do — where |
| --- | --- | --- | --- |
| Email is off or not working on this instance. | `EMAIL_UNAVAILABLE` | Configuration changed since you opened the dialog, for example after a restart | **Interface**: [Settings › Administration › Email](email.md#email-tab). |
| Emails cannot carry links: LIBREFOLIO_PUBLIC_URL is not set, or cannot start a link. | `EMAIL_LINKS_UNAVAILABLE` | The start of the links is missing | **`.env`**: set `LIBREFOLIO_PUBLIC_URL`, then restart ([Emails with a Link](email_flows.md#public-url)). |
| This link no longer works: create a new one. | `EMAIL_LINK_INVALID` | Link expired, used or revoked | **Interface**: create a new link and send that one. |
| The account is not active: activate it before sending it a reset link. | `EMAIL_ACCOUNT_INACTIVE` | Deactivated account | **Interface**: **Reactivate** in [Users & Invitations](users.md#actions); or **command line**: `user activate` ([CLI](cli_tools.md)). Then send the link again. |
| Enter the address to send the invitation to. | `EMAIL_RECIPIENT_REQUIRED` | The invitation holds no address | **Interface**: type one in **Send to**. |
| This is not one valid email address. | `EMAIL_RECIPIENT_INVALID` | Invalid address. For a reset, it is the account's own | **Interface**: correct **Send to**. For the reset, copy the link instead. |
| The hourly email limit is reached: try again in … min. | `EMAIL_RATE_LIMITED` | Maximum of the hour reached | Wait the minutes shown. For more, **`.env`**: raise `LIBREFOLIO_SMTP_MAX_PER_HOUR` and restart. |
| The SMTP server refused the recipient's address. | `RECIPIENT_REFUSED` | The address of the link: **Send to** for an invitation, the account's email for a reset. Without a login, a server may refuse to relay to other domains | **Interface**: the address. **Log**: the server's reply. **SMTP server**: the relay. |
| The other messages of the test email | `CONNECTION_FAILED`, `TLS_FAILED`, `AUTH_FAILED`, … | As in the table above | As in the table above. |
| The email could not be sent. | — | No known answer, for example a network error | Reload the page and look at the **log**. |

`EMAIL_RECIPIENT_NOT_ALLOWED` (another address for a reset link) comes only from the API: the dialog never returns it.

### 📜 What the Log Says {: #logs }

**Where to read it:**

| Installation | Command or file |
| --- | --- |
| Docker | `docker compose logs librefolio` |
| On the host | `logs/librefolio.log` in the data folder ([Filesystem Structure](filesystem.md)); the server also prints it to the console |

At every start, right after `Starting LibreFolio`, the server checks the configuration, email included ([Startup Checks](configuration_security.md#startup-checks)): a configuration that cannot be used (the first two lines below), `none` towards a server outside your local network (one line), `LIBREFOLIO_PUBLIC_URL` missing or invalid (one line).
None of them stops the start.
The same three checks are in **Settings › Administration › Security**, read again when you ask; a finding links to the [Email tab](email.md#email-tab) (see «Security» in [Global Settings](settings.md)).

**Start and sending**

| The log says | Level | When |
| --- | --- | --- |
| `Email configuration cannot be used: email stays off` | `error` | A variable cannot be used. Once per server process, at startup, with `variable`, `problem` (the code) and `reason`: the rule it breaks, or why the password file cannot be read. |
| `LIBREFOLIO_SMTP_… cannot be used (SMTP_…): email stays off until it is fixed` | `error` | At startup, after the line above, with `check` set to `email.smtp`: the startup checks report the same problem. |
| `LIBREFOLIO_SMTP_TLS=none with …: emails, their links and the SMTP password travel unencrypted; use starttls or tls` | `warning` | At startup, with `check` set to `email.smtp_encryption`: `none` towards a server outside your local network, which the line names ([Security Notes](#security)). |
| `LIBREFOLIO_PUBLIC_URL is not set: emails work, but none with a link (forgotten password, invitation, reset) can go out` | `info` | At startup, with `check` set to `email.links`: email works, but `LIBREFOLIO_PUBLIC_URL` is not set ([Emails with a Link](email_flows.md#public-url)). |
| `LIBREFOLIO_PUBLIC_URL cannot start a link (it needs http:// or https:// and a host, with no user name, password, ? or #): no email with a link (forgotten password, invitation, reset) can go out` | `warning` | At startup, with `check` set to `email.links`: email works, but the variable cannot start a link ([Emails with a Link](email_flows.md#public-url)). |
| `Email sent` | `info` | The server accepted an email; `kind` says which: `test`, `invite`, `password_reset`, `email_verification`, `email_changed`, `email_change_confirmation` (the owner's new address) or `email_change_request` (a change asked from Profile: the confirmation and the notice). |
| `Email not sent` | `warning` | The server refused the email or did not answer: `code`, as in [Sending Errors](#sending-errors), and `detail`, the server's own reply, the most precise clue. |
| `Email not sent: the hourly limit of the instance is reached` | `warning` | The hourly limit stopped an email; `retry_after` is in seconds. |
| `Test email sent by an administrator` | `info` | A test email went out, with `admin_id` and `language`. |
| `Link emailed by an administrator` | `info` | An administrator sent a link by email: `admin_id`, `purpose` (`invite` or `password_reset`), `token_id`, the account's `user_id` for a reset link, and `language`. |

**Forgotten passwords**

| The log says | Level | When |
| --- | --- | --- |
| `Forgotten password: reset link emailed` | `info` | A reset link went out: `user_id`, `token_id` and `language`. |
| `Forgotten password: no active account matches, nothing sent` | `info` | No active account has that username or email address. What was typed is never logged. |
| `Forgotten password: the account had a reset link moments ago, nothing sent` | `info` | The account's limits: a reset link less than 5 minutes ago, or 3 in the last hour; with `user_id`. |
| `Forgotten password: an administrator's reset link is still live, nothing sent` | `info` | A request never cancels a link given by an administrator; with `user_id`. |
| `Forgotten password: the hourly limit of the instance is reached, nothing sent` | `warning` | The hourly limit was reached after the answer; with `user_id`. |
| `Forgotten password: the mailbox had reset emails moments ago, nothing sent` | `info` | That mailbox already had 3 reset emails in the last hour, those that did not go out included; with `user_id`. |
| `Forgotten password: another request won the race, nothing sent` | `info` | Two requests for the account at the same moment: the other one sends the email; with `user_id`. |
| `Forgotten password: no email sent` | `warning` | Email or `LIBREFOLIO_PUBLIC_URL` stopped working after the answer, or the email was refused: `reason` and `code` say which. The link created is revoked. |
| `Forgotten password: the request failed` | `error` | An unexpected error, with its type in `error` and nothing more: no detail of the request reaches the log. |

Every reset link also leaves a `Password reset link created` line, with `user_id`, `token_id` and, if an administrator created it, `created_by_user_id`.

**Email verification**

| The log says | Level | When |
| --- | --- | --- |
| `Registration waits for email verification` | `info` | A new account waits for its link; with `user_id`. The `User registered` line of the same registration has `waits_for_email` set to true. |
| `Verification email held: address limit or instance budget reached` | `info` | The address had already received its `LIBREFOLIO_SIGNUP_EMAILS_PER_ADDRESS` emails (20 by default) in the hour, or the hourly limit of the instance is spent: the account waits without its email, and the login page tells its owner so; with `user_id`. |
| `Verification link emailed` | `info` | A verification link went out: `user_id`, `token_id` and `language`. |
| `Verification email: not sent` | `warning` | The email of a registration did not go out: `reason` and `code` say why. The page had said that the email was on its way: only this line says that it did not go out. The account still waits; the owner can ask for the link again. |
| `Verification email: the account no longer waits, nothing sent` | `info` | An administrator activated, deactivated or deleted the account before the email went out; with `user_id`. |
| `Verification email: the request failed` | `error` | An unexpected error, with its type in `error` and the `user_id`, nothing more. |
| `Login refused: email not verified` | `info` | A waiting account logged in with the right password; with `user_id`. |
| `Verification resend refused: wrong credentials` | `warning` | Request for a new verification link with a wrong password, or for an account that does not exist. Neither what was typed nor the address is logged. |
| `Email verified` | `info` | The owner confirmed on the page of the link: the account is active; `user_id` and `token_id`. |
| `Email verification refused: the link's email did not go out` | `info` | Confirmation with a link whose email LibreFolio counted as not sent: the account still waits, and **Send the link again** works. |
| `Email verification refused: the link was sent to another address` | `info` | The account's address changed after the link was sent: that link stops working. |

**Email address change**

| The log says | Level | When |
| --- | --- | --- |
| `Email change notice sent to the previous address` | `info` | The notice went to the old address. The line has `user_id` and `language`, neither address. |
| `Email change notice sent to the new address` | `info` | The confirmation went to the new address. The line has `user_id` and `language`, neither address. |
| `Email change notice: email is off, nothing sent` | `info` | Email is off: nothing to send, nothing wrong. |
| `Email change notice: past its limits, nothing sent` | `info` | The account already had 3 changes with emails in the hour: the change went through, its two emails did not. With `user_id`. |
| `Email change notice: the previous mailbox is past its limit, not sent there` | `info` | The old mailbox already had 3 of these emails in the hour: the notice did not go, the confirmation to the new address still can. With `user_id`. |
| `Email change notice: the new mailbox is past its limit, not sent there` | `info` | The same, for the new mailbox and its confirmation. With `user_id`. |
| `Email change notice: the account no longer exists, nothing sent` | `info` | The account was deleted before the email went out. |
| `Email change notice: not sent` | `warning` | Email is configured but cannot be used now, the hourly limit is reached, an address is not one plain address, or sending failed: `reason` and `code` say which, and `recipient` (`previous` or `new`) which of the two emails, when it is one of them. |
| `Email change notice: the request failed` | `error` | An unexpected error, with its type in `error` and the `user_id`, nothing more. |

None of these lines holds the SMTP password, the content of an email, a link or its secret part, what someone typed to ask for a reset or verification link, or the recipient's full address: only its domain, in `recipient_domain`.
The server's reply is masked too, because it often quotes the refused address: `550 5.1.1 <***@example.com>: Recipient address rejected`.
The lines of an email change name neither the old address nor the new one.

---

## 🔒 Security Notes {: #security }

- **`starttls` never falls back to plain text.** A server that does not offer encryption gets neither the password nor the message: the test email fails with `TLS_FAILED`.
- **The certificate is always checked**, with `starttls` and with `tls`: no option skips it.
- **`none` sends everything in clear**: messages, links and the SMTP password. Use it only for a relay on your own machine or network. Towards any other server, Settings › Administration › Email shows a warning: *Emails, their links and the SMTP password travel unencrypted to a server outside the local network*; the start log has one too ([What the Log Says](#logs)).
- **Keep the password in a secret file** (`LIBREFOLIO_SMTP_PASSWORD_FILE`) that only the user running LibreFolio can read, out of `.env` and out of the data folder. Use an app password, or an account just for LibreFolio, that you can revoke on its own.
- **Links come only from `LIBREFOLIO_PUBLIC_URL`**, never from a request: nobody can make LibreFolio send one of your users a link to a third-party site ([Emails with a Link](email_flows.md#public-url)).
- **A verification link goes only to the account's own address**, and nobody sees it, administrator included. **Send the link again** asks for the account's password, like the login, and a new link disables the previous ones.
- **Names stay on one line.** Username, inviter's name and instance name go into an email on one line: control characters and line breaks become spaces, bidirectional controls are removed. A crafted username can neither add lines to an email nor disguise its text.
- **No stranger's words in an email.** Password reset, email verification and the two emails of an address change can be sent, by someone who is not an administrator, to an address of their choice. These emails open with a plain «Hello,», without the username, the notice shows no part of the new address and the confirmation to the new address none of the old one: LibreFolio does not resolve domains, so even the end of an address is chosen freely. A reset link you send by email is written the same way; the username appears once the link is opened. Only the test email and the setup link of the initial administrator greet by name: you, or whoever runs the server, send them.
- **Forgotten passwords tell nobody which accounts exist**: the same answer for everyone, the search after the answer, and limits per address, per username or email address, per mailbox and per account ([Forgotten Passwords](email_flows.md#forgot-password)).
- **Changing an account's email address requires its current password.** Without it, a moment inside someone's session (a stolen session cookie, a computer left unlocked) would be enough to put one's own address on the account and then reset its password: reset by email exists only together with this rule. When email works, the old address also gets a notice, and the new one a confirmation ([Email Address Changes](email_flows.md#email-change-notice)).
- **The hourly limit** caps what the instance can send, whatever happens: raise it only as far as you need.

??? info "🏠 What counts as your local network — when the warning appears"

    LibreFolio judges `LIBREFOLIO_SMTP_HOST` as written, without resolving the name. Local means:

    - `localhost`, or a name without a dot, such as a Docker Compose service (`smtp-relay`) or a
      machine of your LAN;
    - a name ending in `.local`, `.lan`, `.home.arpa`, `.internal` or `.localhost`;
    - a loopback, private or link-local address, such as `127.0.0.1`, `192.168.1.10` or
      `fd00::25`, or a Tailscale address (`100.64.0.0/10`, `fd7a:115c:a1e0::/48`).

    Any other server gets the warning, even one on your network known by a full name such as
    `relay.example.com`. A Tailscale name such as `relay.tailnet.ts.net` gets it too, while its
    `100.x` address does not.

---

## 🔗 Related

- 📄 **[Email](email.md)** — Where the Configuration Lives, The Variables, Examples, …
- 📄 **[Email: Links and Messages](email_flows.md)** — Emails with a Link, Links Sent by an Administrator, Forgotten Passwords, …
