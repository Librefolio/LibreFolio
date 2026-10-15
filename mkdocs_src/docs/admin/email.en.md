# 📧 Email

LibreFolio can send email through an SMTP server that you name in a few environment variables.
Email is **optional**: without it nothing changes, nothing is sent, and invitation and
password-reset links are copied by hand.

What LibreFolio sends:

- **A test email**, which an administrator sends to their own address from **Settings › Email**,
  to check that everything works.
- **The invitation and password-reset links an administrator creates**, by email instead of copied
  by hand: [Links Sent by an Administrator](#admin-links). The **Send by email** button is coming
  with the invitation and reset dialogs.
- **A reset link for a forgotten password**, to whoever asks for one for their account. This one is
  held for now, for a security reason: see [Forgotten Passwords](#forgot-password).

The emails with a link also need `LIBREFOLIO_PUBLIC_URL`: see [Emails with a Link](#public-url).
While a hosting provider blocks the instance, LibreFolio sends no email at all
([Hosting for Others](hosting_providers.md)).

To set it up:

1. Write the `LIBREFOLIO_SMTP_*` variables in `.env`: at least the server and the sender, and the
   login of your account when the server asks for one. The [examples](#examples) cover the usual
   cases.
2. For the emails with a link, set `LIBREFOLIO_PUBLIC_URL` too ([Emails with a Link](#public-url)).
3. Restart LibreFolio.
4. Open **Settings › Email**: the state reads **Ready**. Send yourself a test email.

---

## 🔐 Where the Configuration Lives {: #where-it-lives }

The SMTP configuration comes **only** from environment variables, and the password also from a
secret file.

- **Never stored.** LibreFolio never writes it anywhere: it is not in the database, and a backup of
  LibreFolio's data does not contain it. Keep your own copy of `.env` and of the password file.
- **Never shown.** No page of the interface shows the server, the port, the user, the sender or the
  password: [Settings › Email](#email-tab) only says whether email works and, when it does not,
  which variable to fix.
- **Public: only whether email is ready.** `/api/v1/system/instance`, which anyone who can reach the
  server may read, says whether this instance can send email: `"available": true` when the state is
  **Ready**, and `"links": true` when, on top of that, emails can carry a link
  ([Emails with a Link](#public-url)). Nothing else about email is there.
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

## 🌐 Emails with a Link {: #public-url }

An invitation or a password-reset link sent by email is built from `LIBREFOLIO_PUBLIC_URL` alone:
that address, then the page that takes the link, such as
`https://librefolio.example.com/reset-password#token=…`. Never from the address your browser
used, nor from anything else in a request.

- **Why.** Anyone can send LibreFolio a request that names another address. If a link were built
  from the request, a stranger could have LibreFolio email one of your users a real link to a site
  of theirs, and catch its secret part when the user opens it.
- **What to set.** The address your users open LibreFolio at, with `http://` or `https://` and a
  host name, such as `https://librefolio.example.com`: no user name or password, no `?` or `#`, no
  spaces. It is the same variable the command line puts in front of the links it prints: see
  *Accounts and Sign-ups* in [Configuration](configuration.md).
- **Without it**, or with an address that breaks these rules, no email with a link goes out: such
  an email is refused with `EMAIL_LINKS_UNAVAILABLE`, while the test email still works. The links
  you copy, from the [command line](cli_tools.md) for one, stay as they are.
- **What the email says**: it names your instance by the host of `LIBREFOLIO_PUBLIC_URL`, and says
  how long the link still works, 7 days for a new invitation and 30 minutes for a reset link. A
  link works once.
- **The secret part** of the link comes after `#`: browsers never send it to the server, so it
  stays out of server and proxy logs.
- **To check it**: with email **Ready**, Settings › Email shows a notice when
  `LIBREFOLIO_PUBLIC_URL` is not set or cannot be used, and the start log has a line
  ([What the Log Says](#logs)). From anywhere, `/api/v1/system/instance` shows `"links": true` once
  both are fine. LibreFolio does not check that this address leads to it: open it in a browser
  yourself.

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
      server, Settings › Email and the start log show a [warning](#security).

---

## 🖥️ Settings › Email {: #email-tab }

Open **Settings** (gear icon in the sidebar), then the **Email** tab, after **Admin** (on a phone,
the tab with the envelope icon). Only administrators see it. The book icon at its top opens this
page.

### 🚦 The State {: #state }

| State | What it means | What the tab shows |
| --- | --- | --- |
| **Off** | `LIBREFOLIO_SMTP_HOST` is not set: nothing is sent. This is the default. | A short explanation, and a pointer to this guide. |
| **Ready** | Every variable can be used. | The emails left this hour, the notices that apply, and **Send a test email**. |
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
- A notice about `LIBREFOLIO_PUBLIC_URL` appears when it is not set (information: emails work, but
  none with a link can go out) or is not an `http://` or `https://` address (warning): see
  [Emails with a Link](#public-url).

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

## 📨 Links Sent by an Administrator {: #admin-links }

An invitation or a password-reset link that an administrator creates can go out by email, instead
of being copied by hand. The **Send by email** button is coming with the invitation and reset
dialogs; LibreFolio already follows these rules:

- **An invitation** goes to the address you choose, or else to the one written in the invitation,
  in the language you choose, or else the instance's **Default Language**. It names you as the
  person who invites, and says so when the new account will be an administrator.
- **A password-reset link** goes only to the address of its account, in the account's language,
  and only while the account is active: no other address is accepted.
- **Only a live link** goes out: one that has expired, was used or was revoked is refused, and a
  new one must be created.
- Each email counts against the hourly limit, and needs `LIBREFOLIO_PUBLIC_URL`
  ([Emails with a Link](#public-url)).

---

## 🗝️ Forgotten Passwords {: #forgot-password }

Someone who forgot their password will be able to ask for a reset link by email, with their
username or their email address, without signing in.

!!! warning "⏸️ Held for now"

    LibreFolio refuses every such request for now, with `FORGOT_PASSWORD_DISABLED`, and the login
    page's **Forgot Password?** still shows the command-line reset. The reason: today, the email
    address of an account can be changed with its session alone. With reset by email open, a moment
    inside someone's session (a stolen session cookie, a computer left unlocked) would be enough to
    put one's own address on the account, then reset its password from there: a lasting takeover.
    The hold is lifted together with the login page's form, once changing an account's email
    address asks for its current password. The links an administrator emails are not affected.

Once open, it works this way:

- **The same answer for everyone**: *If an active account matches, its owner gets an email with a
  link to choose a new password*, whether an account matches or not. The search for the account
  and the email come after the answer, so nobody can use it to find out which accounts exist.
- **The account** is found as the login finds it, by username or email address. Only an active
  account gets the email, at its own address and in its language.
- **The link** works once, for 30 minutes, and replaces the reset links that earlier requests sent
  the account. While a reset link an administrator created is still live, nothing is sent: a
  request never cancels it.
- **When email or `LIBREFOLIO_PUBLIC_URL` is not ready**, the request is refused with a short
  message, the same for everyone.

The limits:

| Limit | Past it |
| --- | --- |
| 10 requests every 15 minutes from the same address; an IPv6 address counts by its /64, the block one subscriber usually holds | The request is refused until the oldest of them is 15 minutes old. |
| 3 requests an hour for the same username or email address, whether an account matches or not | The request is refused until the oldest of them is an hour old. |
| The hourly limit of the instance, `LIBREFOLIO_SMTP_MAX_PER_HOUR` | The request is refused until an email fits again. |
| 3 emails an hour to the same mailbox, in capitals or not, whatever account they are for | Nothing is sent, and the answer stays the same. |
| 1 email every 5 minutes, and 3 an hour, for the same account, the reset links an administrator created included | Nothing is sent, and the answer stays the same. Two requests at the same moment cannot both send. |

The limit per account counts the account's reset links in the database. The others are kept in the
memory of each server process: with several processes, each keeps its own count, and a restart
forgets them.

**Behind a reverse proxy**, the address that counts is the one the server (uvicorn) sees:

- It takes the visitor's address from the proxy's `X-Forwarded-For` header only when the proxy's
  address is listed in `FORWARDED_ALLOW_IPS` (`127.0.0.1` when not set). List your proxy's exact
  addresses there, never `*`: with `*`, uvicorn takes the first address of the header, which the
  visitor can write.
- Behind a proxy it does not trust, every visitor shares the proxy's address, and one count of 10
  requests every 15 minutes. The other limits still hold.

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

Emails with a link have reasons of their own. No page shows them yet; the server answers with these
codes:

| Code | Why | What to do |
| --- | --- | --- |
| `EMAIL_LINKS_UNAVAILABLE` | `LIBREFOLIO_PUBLIC_URL` is not set, or does not start with `http://` or `https://`. | Set it, then restart: see [Emails with a Link](#public-url). |
| `EMAIL_LINK_INVALID` | The link has expired, was used or revoked, or does not exist: the answer says which. | Create a new link, and send that one. |
| `EMAIL_RECIPIENT_REQUIRED` | An invitation without an address: none given, and none written in the invitation. | Give the address to send it to. |
| `EMAIL_RECIPIENT_NOT_ALLOWED` | Another address for a password-reset link. | A reset link goes only to the address of its account: to reach the person elsewhere, copy the link instead. |
| `EMAIL_ACCOUNT_INACTIVE` | A password-reset link for an account that is deactivated. | Activate the account first, with `user activate` on the [command line](cli_tools.md) for one, then send it a reset link. |

The other codes mean what they mean for the test email: `EMAIL_UNAVAILABLE`, `EMAIL_RATE_LIMITED`,
the SMTP codes above, and `EMAIL_RECIPIENT_INVALID`, here for the address the link would go to.

### 📜 What the Log Says {: #logs }

The log is `logs/librefolio.log` in the data folder, and the server also prints it to its console:
`docker compose logs librefolio` with Docker ([Filesystem Structure](filesystem.md)).

At every start, right after `Starting LibreFolio`, the server checks its configuration, email
included (*Startup Checks* in [Configuration](configuration.md)). A configuration that cannot be
used shows there in two lines, the first two below; `none` towards a server outside your local
network, and a missing or invalid `LIBREFOLIO_PUBLIC_URL`, in one line each. None of them stops
the start.

| The log says | Level | When |
| --- | --- | --- |
| `Email configuration cannot be used: email stays off` | `error` | A variable cannot be used. Each server process logs it once, at startup, with `variable`, `problem` (the code) and `reason`: the rule it breaks, or why the password file cannot be read. |
| `LIBREFOLIO_SMTP_… cannot be used (SMTP_…): email stays off until it is fixed` | `error` | At startup, after the line above, with `check` set to `email.smtp`: the startup checks report the same problem. |
| `LIBREFOLIO_SMTP_TLS=none with …: emails, their links and the SMTP password travel unencrypted; use starttls or tls` | `warning` | At startup, with `check` set to `email.smtp_encryption`: `none` towards a server outside your local network, which the line names ([Security Notes](#security)). |
| `LIBREFOLIO_PUBLIC_URL is not set: emails work, but none with a link (forgotten password, invitation, reset) can go out` | `info` | At startup, with `check` set to `email.links`: email works, but `LIBREFOLIO_PUBLIC_URL` is not set ([Emails with a Link](#public-url)). |
| `LIBREFOLIO_PUBLIC_URL is not an http(s) address: no email with a link (forgotten password, invitation, reset) can go out` | `warning` | At startup, with `check` set to `email.links`: email works, but the variable does not start with `http://` or `https://`. |
| `Email sent` | `info` | The server accepted an email; `kind` says which: `test`, `invite` or `password_reset`. |
| `Email not sent` | `warning` | The server refused the email or did not answer: `code`, as in [Sending Errors](#sending-errors), and `detail`, the server's own reply, the most precise clue. |
| `Email not sent: the hourly limit of the instance is reached` | `warning` | The hourly limit stopped an email; `retry_after` is in seconds. |
| `Test email sent by an administrator` | `info` | A test email went out, with the `admin_id` and the `language`. |
| `Link emailed by an administrator` | `info` | An administrator emailed a link: `admin_id`, `purpose` (`invite` or `password_reset`), `token_id`, the account's `user_id` for a reset link, and `language`. |
| `Forgotten password: reset link emailed` | `info` | A reset link went out for a forgotten password: `user_id`, `token_id` and `language`. |
| `Forgotten password: no active account matches, nothing sent` | `info` | No active account has that username or email address. What was typed is never logged. |
| `Forgotten password: the account had a reset link moments ago, nothing sent` | `info` | The account's own limits: a reset link less than 5 minutes ago, or 3 in the last hour; with `user_id`. |
| `Forgotten password: an administrator's reset link is still live, nothing sent` | `info` | A request never cancels a link an administrator gave the account; with `user_id`. |
| `Forgotten password: the hourly limit of the instance is reached, nothing sent` | `warning` | The hourly limit was reached after the answer; with `user_id`. |
| `Forgotten password: the mailbox had reset emails moments ago, nothing sent` | `info` | 3 reset emails went to that mailbox in the last hour; with `user_id`. |
| `Forgotten password: another request won the race, nothing sent` | `info` | Two requests for the account at the same moment: the other one sends the email; with `user_id`. |
| `Forgotten password: no email sent` | `warning` | Email or `LIBREFOLIO_PUBLIC_URL` stopped working after the answer, or the email was refused: `reason` and `code` say which. A link created for it is revoked. |
| `Forgotten password: the request failed` | `error` | An unexpected error, with its type in `error` and nothing more: no detail of the request reaches the log. |

The `Forgotten password: …` lines appear only once [forgotten passwords](#forgot-password) are
open. Every reset link also leaves a `Password reset link created` line, with `user_id`, `token_id`
and, when an administrator created it, `created_by_user_id`.

The log never holds the SMTP password, the content of an email, a link or its secret part, what
someone typed to ask for a reset link, or the recipient's full address: only its domain, in
`recipient_domain`. Servers often quote the address they refuse, so their reply is masked too, such
as `550 5.1.1 <***@example.com>: Recipient address rejected`.

---

## 🔒 Security Notes {: #security }

- **`starttls` never falls back to plain text.** A server that does not offer encryption gets
  neither the password nor the message: the test email fails with `TLS_FAILED`.
- **The certificate is always checked**, with `starttls` and with `tls`: there is no option to skip
  the check.
- **`none` sends everything in clear**: the messages, their links and the SMTP password. Keep it for
  a relay on your own machine or network. Towards any other server, Settings › Email shows a
  warning: *Emails, their links and the SMTP password travel unencrypted to a server outside the
  local network*; the start log has one too ([What the Log Says](#logs)).
- **Keep the password in a secret file** (`LIBREFOLIO_SMTP_PASSWORD_FILE`) that only the user
  running LibreFolio can read, out of `.env` and out of the data folder. Use an app password, or an
  account just for LibreFolio, that you can revoke on its own.
- **Links come only from `LIBREFOLIO_PUBLIC_URL`**, never from a request: nobody can make
  LibreFolio email one of your users a link to a site of theirs ([Emails with a Link](#public-url)).
- **Names stay on one line.** A username, the name of whoever invites or the name of the instance
  is written into an email on one line: control characters and line breaks become spaces, and the
  characters that reorder text (bidirectional controls) are removed. A crafted username can neither
  add lines of its own to an email nor disguise its text.
- **Forgotten passwords are held** until changing an account's email address asks for its current
  password. Once open, they tell nobody which accounts exist: the same answer for everyone, the
  search after the answer, and limits per address, per username or email address, per mailbox and
  per account ([Forgotten Passwords](#forgot-password)).
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

- 📝 **[Configuration](configuration.md)** — The `.env` file, secrets in files, the startup checks
  and `LIBREFOLIO_PUBLIC_URL`
- 🛠️ **[Command-Line Tools](cli_tools.md)** — Invitation and password-reset links from the command
  line
- 🐳 **[Advanced Docker](docker_advanced.md)** — The Compose file, and the user that runs LibreFolio
  in the container
- 📂 **[Filesystem Structure](filesystem.md)** — Where the log is kept
- 👤 **[Profile](../user/settings/profile.md)** — The email address of your account
- 🧑‍💻 For developers: **[Email Service (SMTP)](../developer/backend/email.md)** — How the service
  works inside
