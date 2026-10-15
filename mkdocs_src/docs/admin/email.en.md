# 📧 Email

LibreFolio can send email through an SMTP server that you name in a few environment variables.
Email is **optional**: without it nothing changes, nothing is sent, and invitation and
password-reset links are copied by hand.

Today, the only email LibreFolio sends is the **test email**: an administrator sends it to their
own address from **Settings › Email**, to check that everything works.

To set it up:

1. Write the `LIBREFOLIO_SMTP_*` variables in `.env`: at least the server and the sender, and the
   login of your account when the server asks for one. The [examples](#examples) cover the usual
   cases.
2. Restart LibreFolio.
3. Open **Settings › Email**: the state reads **Ready**. Send yourself a test email.

---

## 🔐 Where the Configuration Lives {: #where-it-lives }

The SMTP configuration comes **only** from environment variables, and the password also from a
secret file.

- **Never stored.** LibreFolio never writes it anywhere: it is not in the database, and a backup of
  LibreFolio's data does not contain it. Keep your own copy of `.env` and of the password file.
- **Never shown.** No page of the interface shows the server, the port, the user, the sender or the
  password: [Settings › Email](#email-tab) only says whether email works and, when it does not,
  which variable to fix.
- **Read from the environment.** `./dev.py` and Docker Compose (`env_file: .env`) put the values of
  `.env` there, so these variables go in `.env` like the other [options](configuration.md).
- **Restart after a change.** With Docker Compose, run `docker compose up -d`:
  `docker compose restart` keeps the old values.

To turn email off, remove `LIBREFOLIO_SMTP_HOST` or leave it empty, then restart. The other
variables can stay: without a server, LibreFolio ignores them.

---

## 📋 The Variables {: #variables }

The «Email» section of `.env.example` lists them, commented: copy the lines you need into your
`.env`.

| Variable | Default | Accepted values |
| --- | --- | --- |
| `LIBREFOLIO_SMTP_HOST` | _not set_: email off | The SMTP server: a host name, such as `smtp.example.com`, or an IP address, and nothing else: no `smtp://`, no `user@`, no `:587`, no path. An IPv6 address goes without brackets, such as `fd00::25`. |
| `LIBREFOLIO_SMTP_TLS` | `starttls` | `starttls`, `tls` or `none`, in capitals or not: see [Encryption Modes](#encryption-modes). |
| `LIBREFOLIO_SMTP_PORT` | `587` with `starttls`, `465` with `tls`, `25` with `none` | A whole number from 1 to 65535. Set it only when your server uses another port than the one of its mode. |
| `LIBREFOLIO_SMTP_USER` | _not set_: no login | The login of your account on the SMTP server. |
| `LIBREFOLIO_SMTP_PASSWORD` | _not set_ | The password of that login, used exactly as written, spaces included. Or `LIBREFOLIO_SMTP_PASSWORD_FILE`: the path of a file that holds it. |
| `LIBREFOLIO_SMTP_FROM` | _required_ with a server | The sender: one address, with a name or without, such as `LibreFolio <noreply@example.com>` or `noreply@example.com`. |
| `LIBREFOLIO_SMTP_REPLY_TO` | _not set_: replies go to the sender | One address, where replies go. |
| `LIBREFOLIO_SMTP_MAX_PER_HOUR` | `50` | How many emails LibreFolio may send in an hour, per server process: a whole number, at least 1. |

- **Empty is the same as not set**: a value that is empty, or holds only spaces, counts as not set.
- **The login comes in pairs**: set `LIBREFOLIO_SMTP_USER` together with a password, or neither of
  them for a server that takes mail without a login.
- **The password in a file**: `LIBREFOLIO_SMTP_PASSWORD_FILE` follows the rules of *Secrets in
  Files* in [Configuration](configuration.md). The password is the text of the file as it is,
  whatever characters it holds, without the line breaks at its end. Set one of the two: when both
  are set, `LIBREFOLIO_SMTP_PASSWORD` wins, the file is ignored and the start log has a warning.
  Unlike `JWT_SECRET_FILE`, a password file that cannot be read never stops the server: email stays
  off until it is fixed.
- **The hourly limit counts per server process**, over the last 60 minutes, in memory: a restart
  starts the count again from zero. `./dev.py server --workers 4` runs four processes, each with its
  own count, so the instance may send up to four times the limit
  ([Start the Server](cli_tools.md#start-the-server)). The Docker image runs a single process.

### 🔑 Encryption Modes {: #encryption-modes }

| `LIBREFOLIO_SMTP_TLS` | What it does | Usual port |
| --- | --- | --- |
| `starttls` (default) | Connects, then switches to encryption before sending anything. A server that does not offer it is refused: nothing goes out in clear. | 587 |
| `tls` | Encrypted from the first byte, also called SSL/TLS or SMTPS. | 465 |
| `none` | No encryption: the messages, their links and the password travel in clear. Only for a relay on the same machine or on your local network. | 25 |

- With `starttls` and `tls`, LibreFolio checks the server's certificate: it must be valid and
  issued for the name in `LIBREFOLIO_SMTP_HOST`. Write the name the certificate is issued for,
  usually not the server's IP address.
- The port follows the mode, not the other way around: `LIBREFOLIO_SMTP_PORT=465` alone keeps
  `starttls`, which a server on port 465 does not expect. For port 465, set
  `LIBREFOLIO_SMTP_TLS=tls`.

---

## 💡 Examples {: #examples }

Replace `smtp.example.com`, the addresses and the password with your own, then restart LibreFolio.

=== "Docker Compose + secret file"

    The password stays out of `.env` and out of the container's environment, in a Docker secret.

    1. Save the password in a file next to `docker-compose.yml`, such as `smtp_password.txt`. A line
       break at its end does not count; spaces do.
    2. The container sees the file with the owner and permissions it has on the host, so let the user
       that runs LibreFolio there read it, `1000:1000` with the official image:

        ```bash
        sudo chown 1000:1000 smtp_password.txt
        sudo chmod 600 smtp_password.txt
        ```

        An image you built yourself may use other ids: put those in the `chown` command instead
        (see [Advanced Docker](docker_advanced.md)).

    3. Add the marked lines to `docker-compose.yml`, and keep the rest of the service as it is. If
       the file already has `secrets:` lists, such as the `JWT_SECRET_FILE` example of
       [Configuration](configuration.md), add the new lines to them:

        ```yaml
        services:
          librefolio:
            secrets:                         # added
              - smtp_password                # added
        secrets:                             # added
          smtp_password:                     # added
            file: ./smtp_password.txt        # added
        ```

    4. Add the variables to `.env`. If it gives `LIBREFOLIO_SMTP_PASSWORD` a value, remove that
       line: it would win over the file.

        ```env
        LIBREFOLIO_SMTP_HOST=smtp.example.com
        LIBREFOLIO_SMTP_USER=noreply@example.com
        LIBREFOLIO_SMTP_PASSWORD_FILE=/run/secrets/smtp_password
        LIBREFOLIO_SMTP_FROM=LibreFolio <noreply@example.com>
        ```

        No `LIBREFOLIO_SMTP_TLS` and no port: `starttls` on port 587 is the default.

    5. Run `docker compose up -d`.

=== "Mail provider"

    Your own account on the SMTP server of a mail provider:

    ```env
    LIBREFOLIO_SMTP_HOST=smtp.example.com
    LIBREFOLIO_SMTP_USER=you@example.com
    LIBREFOLIO_SMTP_PASSWORD=your-app-password
    LIBREFOLIO_SMTP_FROM=LibreFolio <you@example.com>
    ```

    - That is `starttls` on port 587, the defaults. If your provider gives port 465 instead, add
      `LIBREFOLIO_SMTP_TLS=tls`: the port follows.
    - Use an **app password**, not the password you sign in with: a separate password that your
      provider creates for one application, and that you can revoke without touching your account.
    - Your provider's help pages give the server name, the port and the encryption, and say which
      sender addresses your account may use.
    - Better still, keep the password in a file, as in the Docker Compose tab.

=== "Local relay"

    A relay such as Postfix, on the same machine or on your network, takes mail without a login and
    delivers it for LibreFolio.

    LibreFolio on the host, the relay on the same machine:

    ```env
    LIBREFOLIO_SMTP_HOST=localhost
    LIBREFOLIO_SMTP_TLS=none
    LIBREFOLIO_SMTP_FROM=LibreFolio <noreply@example.com>
    ```

    LibreFolio in Docker, the relay in another container on the same Docker network, here a Compose
    service called `smtp-relay`:

    ```env
    LIBREFOLIO_SMTP_HOST=smtp-relay
    LIBREFOLIO_SMTP_TLS=none
    LIBREFOLIO_SMTP_FROM=LibreFolio <noreply@example.com>
    ```

    LibreFolio in Docker, the relay on the host itself: inside a container, `localhost` is the
    container, not the host. Add the marked lines to `docker-compose.yml`, set
    `LIBREFOLIO_SMTP_HOST=host.docker.internal`, and let the relay accept mail from the Docker
    network (in Postfix: `inet_interfaces` and `mynetworks`):

    ```yaml
    services:
      librefolio:
        extra_hosts:                                # added
          - "host.docker.internal:host-gateway"     # added
    ```

    - Port 25 is the default with `none`: set `LIBREFOLIO_SMTP_PORT` only if the relay listens on
      another one.
    - No user and no password: a relay without login takes neither.
    - The relay delivers the mail: it must be allowed to send for the domain of
      `LIBREFOLIO_SMTP_FROM`.
    - `none` sends in clear: use it only towards your own machine or network. Towards any other
      server, Settings › Email shows a [warning](#security).

---

## 🖥️ Settings › Email {: #email-tab }

Open **Settings** (gear icon in the sidebar), then the **Email** tab. It is for administrators
only. The book icon at its top opens this page.

### 🚦 The State {: #state }

| State | What it means | What the tab shows |
| --- | --- | --- |
| **Off** | `LIBREFOLIO_SMTP_HOST` is not set: nothing is sent. This is the default. | A short explanation, and a pointer to this guide. |
| **Ready** | Every variable can be used. | The emails left this hour, the encryption warning when it applies, and **Send a test email**. |
| **Not working** | A variable cannot be used: email stays off until it is fixed. | The problem, naming the variable at fault, and a reminder to restart after the fix. |

!!! note "✅ Ready is not yet a delivered email"

    **Ready** means that every variable can be used. LibreFolio does not contact the server until
    it sends an email: only a test email proves that the server takes your mail.

- **Not working** names one problem at a time, the first it finds: fix it, restart, then look
  again. [Configuration Problems](#configuration-problems) says what to check for each one.
- With **Ready**, the tab counts the emails left, such as **48 of 50 emails left this hour**: the
  last 60 minutes, not the clock hour. When none is left, it says in how many minutes the next one
  can go. With several server processes, each one counts its own, and the tab shows the count of
  the process that answered.
- The encryption warning appears when `LIBREFOLIO_SMTP_TLS=none` points to a server outside your
  local network: see [Security Notes](#security).

### ✉️ The Test Email {: #test-email }

With the state **Ready**, **Send a test email** sends one email to yourself:

- **To your own address**: the email of your account, as in [Profile](../user/settings/profile.md).
  There is no field to type another one.
- **In your language**: the one in your [Preferences](../user/settings/preferences.md), otherwise
  the instance's **Default Language** ([Global Settings](settings.md)), otherwise English.
- **What it says**: its subject is **LibreFolio test email** in English. The message names your
  instance by its address and says that, if you can read it, LibreFolio can send emails. It comes as
  plain text with an HTML version.
- **It counts against the hourly limit**, even when the server refuses it.

The result appears below the button. **Test email sent to your address** means that the SMTP server
accepted the message: look in your inbox, and in the spam folder. Otherwise the tab says what went
wrong: see [Sending Errors](#sending-errors). While LibreFolio talks to the server, the button reads
**Sending…**: LibreFolio waits up to 20 seconds for each step, so a server that does not answer
takes a while to fail.

---

## 🛠️ When It Does Not Work {: #troubleshooting }

Problems come in two kinds:

- a variable LibreFolio cannot use: the state is **Not working** as soon as you open the tab
  ([Configuration Problems](#configuration-problems));
- a server that refuses the email or does not answer: it shows only when an email is sent
  ([Sending Errors](#sending-errors)).

A configuration that cannot be used turns email off, nothing more: the server starts as usual and
everything else works. LibreFolio logs it once per server process, the first time it reads the
email configuration: opening Settings › Email is enough ([What the Log Says](#logs)).

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
| The SMTP server did not take the message. | `SEND_FAILED` | The server refused the message itself: its reply in the log says why. |
| The hourly limit of … emails is reached… (state), or The hourly email limit is reached: try again in … min. (test) | `EMAIL_RATE_LIMITED` | Wait the minutes shown. To allow more, raise `LIBREFOLIO_SMTP_MAX_PER_HOUR` and restart. |
| Email is off or not working on this instance. | `EMAIL_UNAVAILABLE` | The configuration changed since the tab was loaded, for example after a restart: the tab now shows the state and its problem. |
| The address of your account is not a valid email address. | `EMAIL_RECIPIENT_INVALID` | Correct the email of your account in [Profile](../user/settings/profile.md). |
| The test email could not be sent. | — | No known answer came back, such as after a network error: reload the page and look at the log. |
| Test email sent to your address…, but nothing arrives | — | The server accepted the message: from there, delivery is its job. Look in the spam folder, then in the logs of the server or of your provider. A sender on a domain that does not allow that server to send for it may be rejected, or filed as spam, on the way. |

**The state of email could not be read.** means that the tab could not reach the server: reload
the page and, if it lasts, look at the log.

### 📜 What the Log Says {: #logs }

The log is `logs/librefolio.log` in the data folder, and the server also prints it to its console:
`docker compose logs librefolio` with Docker ([Filesystem Structure](filesystem.md)).

| The log says | Level | When |
| --- | --- | --- |
| `Email configuration cannot be used: email stays off` | `error` | A variable cannot be used. Once per server process and problem, with `variable`, `problem` (the code) and `reason`: the rule it breaks, or why the password file cannot be read. |
| `Email sent` | `info` | The server accepted an email; `kind` is `test` for the test email. |
| `Email not sent` | `warning` | The server refused the email or did not answer: `code`, as in [Sending Errors](#sending-errors), and `detail`, the server's own reply, the most precise clue. |
| `Email not sent: the hourly limit of the instance is reached` | `warning` | The hourly limit stopped an email; `retry_after` is in seconds. |
| `Test email sent by an administrator` | `info` | A test email went out, with the `admin_id` and the `language`. |

The log never holds the SMTP password, the content of an email or the recipient's full address:
only its domain, in `recipient_domain`. Servers often quote the address they refuse, so their reply
is masked too, such as `550 5.1.1 <***@example.com>: Recipient address rejected`.

---

## 🔒 Security Notes {: #security }

- **`starttls` never falls back to plain text.** A server that does not offer encryption gets
  neither the password nor the message: the test email fails with `TLS_FAILED`.
- **The certificate is always checked**, with `starttls` and with `tls`: there is no option to skip
  the check.
- **`none` sends everything in clear**: the messages, their links and the SMTP password. Keep it for
  a relay on your own machine or network. Towards any other server, Settings › Email shows a
  warning: *Emails, their links and the SMTP password travel unencrypted to a server outside the
  local network*.
- **Keep the password in a secret file** (`LIBREFOLIO_SMTP_PASSWORD_FILE`) that only the user
  running LibreFolio can read, out of `.env` and out of the data folder. Use an app password, or an
  account just for LibreFolio, that you can revoke on its own.
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

- 📝 **[Configuration](configuration.md)** — The `.env` file, secrets in files and the startup
  checks
- 🐳 **[Advanced Docker](docker_advanced.md)** — The Compose file, and the user that runs LibreFolio
  in the container
- 📂 **[Filesystem Structure](filesystem.md)** — Where the log is kept
- 👤 **[Profile](../user/settings/profile.md)** — The email address of your account
- 🧑‍💻 For developers: **[Email Service (SMTP)](../developer/backend/email.md)** — How the service
  works inside
