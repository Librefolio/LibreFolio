# 🛠️ Email: When It Does Not Work

This page is for when emails do not go out: the errors that the test email and the dialogs show,
what the log says, and the security notes of the SMTP setup.

How to set email up, with the **Email** tab of Settings and its test email, is in
[Email](email.md); the messages LibreFolio sends are in [Email: Links and Messages](email_flows.md).

---

## 🛠️ When It Does Not Work {: #troubleshooting }

Problems come in two kinds:

- a variable LibreFolio cannot use: the state is **Not working** as soon as you open the tab
  ([Configuration Problems](#configuration-problems));
- a server that refuses the email or does not answer: it shows only when an email is sent
  ([Sending Errors](#sending-errors)).

A configuration that cannot be used turns email off, nothing more: the server starts as usual and
everything else works. The start log already names the variable at fault, right after
`Starting LibreFolio`, and so does the tab ([What the Log Says](#logs)).

### ⚙️ Configuration Problems {: #configuration-problems }

The tab names the variable at fault; the code is in the log.

| The tab says | Code | What to check |
| --- | --- | --- |
| `LIBREFOLIO_SMTP_HOST` is not a valid server name… | `SMTP_HOST_INVALID` | Only the name or the IP address: `smtp.example.com`, not `smtp://smtp.example.com`, `smtp.example.com:587` or `user@smtp.example.com`. The port goes in `LIBREFOLIO_SMTP_PORT`; an IPv6 address goes without brackets. |
| `LIBREFOLIO_SMTP_TLS` must be starttls, tls or none. | `SMTP_TLS_INVALID` | One of the three words. For encryption from the first byte, on port 465, the word is `tls`. |
| `LIBREFOLIO_SMTP_PORT` must be a whole number from 1 to 65535. | `SMTP_PORT_INVALID` | Digits only, or no line at all to use the port of the mode. |
| The password file named by `LIBREFOLIO_SMTP_PASSWORD_FILE` cannot be read. | `SMTP_PASSWORD_UNREADABLE` | The log says why: the file does not exist at that path (with Docker, the path inside the container), the user that runs LibreFolio cannot read it, or it is empty or blank, not UTF-8 text or larger than 64 KiB. |
| `LIBREFOLIO_SMTP_USER` is set alone… (or `LIBREFOLIO_SMTP_PASSWORD`) | `SMTP_CREDENTIALS_INCOMPLETE` | Set both the user and the password, or neither. A password given by `LIBREFOLIO_SMTP_PASSWORD_FILE` is reported as `LIBREFOLIO_SMTP_PASSWORD`. |
| `LIBREFOLIO_SMTP_FROM` is missing… | `SMTP_FROM_MISSING` | Add the sender: it is required as soon as a server is set. |
| `LIBREFOLIO_SMTP_FROM` must be one address… | `SMTP_FROM_INVALID` | One address, with or without a name, such as `LibreFolio <noreply@example.com>`: no list, no line break. |
| `LIBREFOLIO_SMTP_REPLY_TO` must be one address. | `SMTP_REPLY_TO_INVALID` | The same rule as the sender, or remove the line. |
| `LIBREFOLIO_SMTP_MAX_PER_HOUR` must be a whole number of at least 1. | `SMTP_MAX_PER_HOUR_INVALID` | Digits only, at least `1`. To stop sending, remove `LIBREFOLIO_SMTP_HOST` instead. |
| `LIBREFOLIO_SIGNUP_EMAILS_PER_ADDRESS` must be a whole number of at least 1. | `SIGNUP_EMAILS_PER_ADDRESS_INVALID` | Digits only, at least `1`, or no line at all for the default of `20`. Like the others, it turns email off until it is fixed; the server starts anyway. |

### 📤 Sending Errors {: #sending-errors }

The test email says why it did not go out. For the server's own reply, look at the log.

| The tab says | Code | What to check |
| --- | --- | --- |
| LibreFolio cannot reach the SMTP server… | `CONNECTION_FAILED` | The server name, as seen from where LibreFolio runs (in a container, `localhost` is the container itself), the port, and a firewall that refuses the connection. |
| The secure connection failed… | `TLS_FAILED` | The mode and the port go together: `starttls` with 587, `tls` with 465. With `starttls`, the server must offer encryption. Its certificate must be valid and issued for the name in `LIBREFOLIO_SMTP_HOST`: a self-signed certificate, or an IP address instead of the name, fails the check. |
| The SMTP server refused the login… | `AUTH_FAILED` | The user and the password: with a provider, an app password. A server that takes mail without a login refuses one: remove the user and the password. |
| The SMTP server refused the sender address… | `SENDER_REFUSED` | The server accepts only the addresses your account may send as: use one of them in `LIBREFOLIO_SMTP_FROM`. Without a user, the server may also want a login. |
| The SMTP server refused your address. | `RECIPIENT_REFUSED` | The email of your account, in [Profile](../user/settings/profile.md). Without a login, a server may refuse to pass mail on to other domains: its reply in the log says so. |
| The SMTP server did not answer in time. | `TIMEOUT` | LibreFolio waits up to 20 seconds for each step. A firewall that drops the connection without refusing it ends here, and so can `starttls` on port 465. |
| The SMTP server did not take the message. | `SEND_FAILED` | The server refused the message itself: its reply in the log says why. An address with letters outside ASCII before the `@`, such as `zoë@example.com`, needs a server that supports SMTPUTF8: without it, the email never leaves LibreFolio, and the log names `SMTPNotSupportedError`. |
| The hourly limit of … emails is reached… (state), or The hourly email limit is reached: try again in … min. (test) | `EMAIL_RATE_LIMITED` | Wait the minutes shown. To allow more, raise `LIBREFOLIO_SMTP_MAX_PER_HOUR` and restart. |
| Email is off or not working on this instance. | `EMAIL_UNAVAILABLE` | The configuration changed since the tab was loaded, for example after a restart: the tab now shows the state and its problem. |
| The address of your account is not a valid email address. | `EMAIL_RECIPIENT_INVALID` | Correct the email of your account in [Profile](../user/settings/profile.md). |
| The test email could not be sent. | — | No known answer came back, such as after a network error: reload the page and look at the log. |
| Test email sent to your address…, but nothing arrives | — | The server accepted the message: from there, delivery is its job. Look in the spam folder, then in the logs of the server or of your provider. A sender on a domain that does not allow that server to send for it may be rejected, or filed as spam, on the way. |

**The state of email could not be read.** means that the tab could not reach the server: reload
the page and, if it lasts, look at the log.

**Send by email**, in the invitation and reset dialogs, says why a link did not go out:

| The dialog says | Code | What to do |
| --- | --- | --- |
| Email is off or not working on this instance. | `EMAIL_UNAVAILABLE` | The configuration changed since the dialog opened, for example after a restart: look at [Settings › Administration › Email](email.md#email-tab). |
| Emails cannot carry links: LIBREFOLIO_PUBLIC_URL is not set, or cannot start a link. | `EMAIL_LINKS_UNAVAILABLE` | Set it, then restart: see [Emails with a Link](email_flows.md#public-url). |
| This link no longer works: create a new one. | `EMAIL_LINK_INVALID` | The link has expired, was used or was revoked: create a new link, and send that one. |
| The account is not active: activate it before sending it a reset link. | `EMAIL_ACCOUNT_INACTIVE` | **Reactivate** the account in [Users & Invitations](users.md#actions), or run `user activate` on the [command line](cli_tools.md), then send the link again. |
| Enter the address to send the invitation to. | `EMAIL_RECIPIENT_REQUIRED` | The invitation has no address written in it: type one in **Send to**. |
| This is not one valid email address. | `EMAIL_RECIPIENT_INVALID` | Correct the address in **Send to**. For a reset link, the address of the account itself is not valid: copy the link instead. |
| The hourly email limit is reached: try again in … min. | `EMAIL_RATE_LIMITED` | Wait the minutes shown. To allow more, raise `LIBREFOLIO_SMTP_MAX_PER_HOUR` and restart. |
| The SMTP server refused the recipient's address. | `RECIPIENT_REFUSED` | The address the link went to: the one in **Send to** for an invitation, the email of the account for a reset link. Without a login, a server may refuse to pass mail on to other domains: its reply in the log says so. |
| The other messages of the test email | `CONNECTION_FAILED`, `TLS_FAILED`, `AUTH_FAILED`, … | As in the table above. |
| The email could not be sent. | — | No known answer came back, such as after a network error: reload the page and look at the log. |

`EMAIL_RECIPIENT_NOT_ALLOWED`, another address for a reset link, comes only from the API: the
dialog sends none.

### 📜 What the Log Says {: #logs }

The log is `logs/librefolio.log` in the data folder, and the server also prints it to its console:
`docker compose logs librefolio` with Docker ([Filesystem Structure](filesystem.md)).

At every start, right after `Starting LibreFolio`, the server checks its configuration, email
included ([Startup Checks](configuration_security.md#startup-checks)). A configuration that cannot be
used shows there in two lines, the first two below; `none` towards a server outside your local
network, and a missing or invalid `LIBREFOLIO_PUBLIC_URL`, in one line each. None of them stops
the start. The same three checks are in the **Security** tab of **Settings › Administration**,
read again when you ask, where a finding links to the [Email tab](email.md#email-tab) (see «Security» in
[Global Settings](settings.md)).

| The log says | Level | When |
| --- | --- | --- |
| `Email configuration cannot be used: email stays off` | `error` | A variable cannot be used. Each server process logs it once, at startup, with `variable`, `problem` (the code) and `reason`: the rule it breaks, or why the password file cannot be read. |
| `LIBREFOLIO_SMTP_… cannot be used (SMTP_…): email stays off until it is fixed` | `error` | At startup, after the line above, with `check` set to `email.smtp`: the startup checks report the same problem. |
| `LIBREFOLIO_SMTP_TLS=none with …: emails, their links and the SMTP password travel unencrypted; use starttls or tls` | `warning` | At startup, with `check` set to `email.smtp_encryption`: `none` towards a server outside your local network, which the line names ([Security Notes](#security)). |
| `LIBREFOLIO_PUBLIC_URL is not set: emails work, but none with a link (forgotten password, invitation, reset) can go out` | `info` | At startup, with `check` set to `email.links`: email works, but `LIBREFOLIO_PUBLIC_URL` is not set ([Emails with a Link](email_flows.md#public-url)). |
| `LIBREFOLIO_PUBLIC_URL cannot start a link (it needs http:// or https:// and a host, with no user name, password, ? or #): no email with a link (forgotten password, invitation, reset) can go out` | `warning` | At startup, with `check` set to `email.links`: email works, but the variable cannot start a link ([Emails with a Link](email_flows.md#public-url)). |
| `Email sent` | `info` | The server accepted an email; `kind` says which: `test`, `invite`, `password_reset`, `email_verification`, `email_changed` or `admin_setup`. |
| `Email not sent` | `warning` | The server refused the email or did not answer: `code`, as in [Sending Errors](#sending-errors), and `detail`, the server's own reply, the most precise clue. |
| `Email not sent: the hourly limit of the instance is reached` | `warning` | The hourly limit stopped an email; `retry_after` is in seconds. |
| `Test email sent by an administrator` | `info` | A test email went out, with the `admin_id` and the `language`. |
| `Link emailed by an administrator` | `info` | An administrator emailed a link: `admin_id`, `purpose` (`invite` or `password_reset`), `token_id`, the account's `user_id` for a reset link, and `language`. |
| `Forgotten password: reset link emailed` | `info` | A reset link went out for a forgotten password: `user_id`, `token_id` and `language`. |
| `Forgotten password: no active account matches, nothing sent` | `info` | No active account has that username or email address. What was typed is never logged. |
| `Forgotten password: the account had a reset link moments ago, nothing sent` | `info` | The account's own limits: a reset link less than 5 minutes ago, or 3 in the last hour; with `user_id`. |
| `Forgotten password: an administrator's reset link is still live, nothing sent` | `info` | A request never cancels a link an administrator gave the account; with `user_id`. |
| `Forgotten password: the hourly limit of the instance is reached, nothing sent` | `warning` | The hourly limit was reached after the answer; with `user_id`. |
| `Forgotten password: the mailbox had reset emails moments ago, nothing sent` | `info` | That mailbox already had 3 reset emails in the last hour, those that did not go out included; with `user_id`. |
| `Forgotten password: another request won the race, nothing sent` | `info` | Two requests for the account at the same moment: the other one sends the email; with `user_id`. |
| `Forgotten password: no email sent` | `warning` | Email or `LIBREFOLIO_PUBLIC_URL` stopped working after the answer, or the email was refused: `reason` and `code` say which. A link created for it is revoked. |
| `Forgotten password: the request failed` | `error` | An unexpected error, with its type in `error` and nothing more: no detail of the request reaches the log. |
| `Registration waits for email verification` | `info` | A new account waits for its link; with `user_id`. The `User registered` line of the same registration has `waits_for_email` set to true. |
| `Verification email held: address limit or instance budget reached` | `info` | The address of the registration already had its `LIBREFOLIO_SIGNUP_EMAILS_PER_ADDRESS` emails (20 by default) in the hour, or the hourly limit of the instance is spent: the account waits without its email, and the login page tells its owner so; with `user_id`. |
| `Verification link emailed` | `info` | A verification link went out: `user_id`, `token_id` and `language`. |
| `Verification email: not sent` | `warning` | The email of a registration did not go out: `reason` and `code` say why. The page had said that the email was on its way, so only this line says that it was not. The account still waits, and its owner can ask for the link again. |
| `Verification email: the account no longer waits, nothing sent` | `info` | An administrator activated, deactivated or deleted the account before its email left; with `user_id`. |
| `Verification email: the request failed` | `error` | An unexpected error, with its type in `error` and the `user_id`, nothing more. |
| `Login refused: email not verified` | `info` | A waiting account signed in with the right password; with `user_id`. |
| `Verification resend refused: wrong credentials` | `warning` | Someone asked for a new verification link with a wrong password, or for an account that does not exist. Neither what was typed nor the address is logged. |
| `Email verified` | `info` | The owner confirmed on the page of the link: the account is active; `user_id` and `token_id`. |
| `Email verification refused: the link's email did not go out` | `info` | Someone confirmed with a link whose email LibreFolio counted as not sent: the account still waits, and **Send the link again** works. |
| `Email verification refused: the link was sent to another address` | `info` | The account's address changed after the link was sent: that link stops working. |
| `Email change notice sent to the previous address` | `info` | The notice went to the old address. The line has `user_id` and `language`, and neither address. |
| `Email change notice: email is off, nothing sent` | `info` | Email is off: nothing to send, and nothing wrong. |
| `Email change notice: past its limits, nothing sent` | `info` | The account, or the old mailbox, already had 3 notices in the hour: the change went through, the notice did not. With `user_id`. |
| `Email change notice: the account no longer exists, nothing sent` | `info` | The account was deleted before the email left. |
| `Email change notice: not sent` | `warning` | Email is set but cannot be used now, a hosting provider blocks the instance, the hourly limit is reached, the old address is not one plain address, or sending failed: `reason` and `code` say which. |
| `Email change notice: the request failed` | `error` | An unexpected error, with its type in `error` and the `user_id`, nothing more. |

Every reset link also leaves a `Password reset link created` line, with `user_id`, `token_id` and,
when an administrator created it, `created_by_user_id`.

None of these lines holds the SMTP password, the content of an email, a link or its secret part,
what someone typed to ask for a reset link or for a new verification link, or the recipient's full
address: only its domain, in `recipient_domain`. Servers often quote the address they refuse, so
their reply is masked too, such as `550 5.1.1 <***@example.com>: Recipient address rejected`. The
notice of an email change names neither the old address nor the new one.

---

## 🔒 Security Notes {: #security }

- **`starttls` never falls back to plain text.** A server that does not offer encryption gets
  neither the password nor the message: the test email fails with `TLS_FAILED`.
- **The certificate is always checked**, with `starttls` and with `tls`: there is no option to skip
  the check.
- **`none` sends everything in clear**: the messages, their links and the SMTP password. Keep it for
  a relay on your own machine or network. Towards any other server,
  Settings › Administration › Email shows a warning: *Emails, their links and the SMTP password
  travel unencrypted to a server outside the local network*; the start log has one too
  ([What the Log Says](#logs)).
- **Keep the password in a secret file** (`LIBREFOLIO_SMTP_PASSWORD_FILE`) that only the user
  running LibreFolio can read, out of `.env` and out of the data folder. Use an app password, or an
  account just for LibreFolio, that you can revoke on its own.
- **Links come only from `LIBREFOLIO_PUBLIC_URL`**, never from a request: nobody can make
  LibreFolio email one of your users a link to a site of theirs ([Emails with a Link](email_flows.md#public-url)).
- **A verification link goes only to the account's own address**, and nobody sees it, an
  administrator included. **Send the link again** asks for the account's password, as the login
  does, and a new link stops the older ones.
- **Names stay on one line.** A username, the name of whoever invites or the name of the instance
  is written into an email on one line: control characters and line breaks become spaces, and the
  characters that reorder text (bidirectional controls) are removed. A crafted username can neither
  add lines of its own to an email nor disguise its text.
- **No stranger's words in an email.** A password reset, an email verification and the notice of an
  email change can be sent, by someone who is not an administrator, to an address of their choice.
  These emails open with a plain «Hello,», without the username, and the notice shows no part of the
  new address: LibreFolio does not look domains up, so even the end of one is chosen freely. A reset
  link you send by email is written the same way. The username still shows once the link is opened.
  Only the test email and the setup link of the initial administrator greet by name: you, or
  whoever runs the server, send those.
- **Forgotten passwords tell nobody which accounts exist**: the same answer for everyone, the
  search after the answer, and limits per address, per username or email address, per mailbox and
  per account ([Forgotten Passwords](email_flows.md#forgot-password)).
- **Changing an account's email address asks for its current password.** Without it, a moment
  inside someone's session (a stolen session cookie, a computer left unlocked) would be enough to
  put one's own address on the account, then reset its password from there: reset by email opened
  only together with this rule. When email works, the old address also gets a notice
  ([Email Address Changes](email_flows.md#email-change-notice)).
- **The hourly limit** caps what the instance can send, whatever happens: raise it only as far as
  you need.

??? info "🏠 What counts as your local network — when the warning appears"

    LibreFolio judges `LIBREFOLIO_SMTP_HOST` as written, without looking the name up. Local means:

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
