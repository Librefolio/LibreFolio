# 📧 Email

LibreFolio can send email through an SMTP server that you name in a few environment variables.
Email is **optional**: without it nothing changes, nothing is sent, and invitation and
password-reset links are copied by hand.

What LibreFolio sends:

- **A test email**, which an administrator sends to their own address from
  **Settings › Administration › Email**, to check that everything works.
- **The invitation and password-reset links an administrator creates**, with **Send by email** in
  their dialogs, instead of copied by hand: [Links Sent by an Administrator](email_flows.md#admin-links).
- **A reset link for a forgotten password**, to whoever asks for one for their account from the
  login page: [Forgotten Passwords](email_flows.md#forgot-password).
- **The setup link of the initial administrator**, once, when LibreFolio creates that administrator
  from `LIBREFOLIO_ADMIN_EMAIL` and generates the link itself: see
  [Hosting for Others](hosting_instances.md#initial-admin).
- **A link to confirm the email address of a new account**, when **Require Email Verification** is
  on: see [Email Verification](email_flows.md#verification).
- **A notice to the old address** when someone changes the email address of their account:
  [Email Address Changes](email_flows.md#email-change-notice).

The emails with a link also need `LIBREFOLIO_PUBLIC_URL`: see [Emails with a Link](email_flows.md#public-url).
While a hosting provider blocks the instance, LibreFolio sends no email at all
([Hosting for Others](hosting_instances.md#instance-block)).

To set it up:

1. Write the `LIBREFOLIO_SMTP_*` variables in `.env`: at least the server and the sender, and the
   login of your account when the server asks for one. The [examples](#examples) cover the usual
   cases.
2. For the emails with a link, set `LIBREFOLIO_PUBLIC_URL` too ([Emails with a Link](email_flows.md#public-url)).
3. Restart LibreFolio.
4. Open **Settings › Administration › Email**: the state reads **Ready**. Send yourself a test email.

!!! info "📚 This guide is in several pages"

    This page sets email up: the variables, examples for the usual servers, the **Email** tab of Settings and its test email. The rest of the guide:

    - [Email: Links and Messages](email_flows.md): the emails with a link, forgotten passwords, their limits, email verification and the notice of an address change.
    - [Email: When It Does Not Work](email_troubleshooting.md): the errors, what the log says and the security notes of the SMTP setup.

---

## 🔐 Where the Configuration Lives {: #where-it-lives }

The SMTP configuration comes **only** from environment variables, and the password also from a
secret file.

- **Never stored.** LibreFolio never writes it anywhere: it is not in the database, and a backup of
  LibreFolio's data does not contain it. Keep your own copy of `.env` and of the password file.
- **Never shown.** No page of the interface shows the server, the port, the user, the sender or the
  password: [Settings › Administration › Email](#email-tab) says whether email works and, when it
  does not, which variable to fix; of the `LIBREFOLIO_SMTP_*` values, it shows only the hourly limit.
- **Public: only whether email is ready.** `/api/v1/system/instance`, which anyone who can reach the
  server may read, says whether this instance can send email: `"available": true` when the state is
  **Ready** and no hosting provider blocks the instance, and `"links": true` when, on top of that,
  emails can carry a link ([Emails with a Link](email_flows.md#public-url)). Nothing else about email is there.
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
| `LIBREFOLIO_SIGNUP_EMAILS_PER_ADDRESS` | `20` | How many registration emails one client address may trigger in an hour, per server process: a whole number, at least 1. Past it, the next new accounts are created and wait, but their emails are held: see [Limits of the Verification Emails](email_flows.md#verification-limits). Not an SMTP variable, which is why its name does not start with `LIBREFOLIO_SMTP_`; it is checked with them, and read only while a server is set. |

- **Empty is the same as not set**: a value that is empty, or holds only spaces, counts as not set.
- **The login comes in pairs**: set `LIBREFOLIO_SMTP_USER` together with a password, or neither of
  them for a server that takes mail without a login.
- **The password in a file**: `LIBREFOLIO_SMTP_PASSWORD_FILE` follows the rules of
  [Secrets in Files](configuration_secrets.md#secret-files). The password is the text of the file as it is,
  whatever characters it holds, without the line breaks at its end. Set one of the two: when both
  are set, `LIBREFOLIO_SMTP_PASSWORD` wins, the file is ignored and the start log has a warning.
  Unlike `JWT_SECRET_FILE`, a password file that cannot be read never stops the server: email stays
  off until it is fixed.
- **The hourly limits count per server process**, over the last 60 minutes, in memory:
  `LIBREFOLIO_SMTP_MAX_PER_HOUR` and `LIBREFOLIO_SIGNUP_EMAILS_PER_ADDRESS` alike. A restart
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
       [Secrets](configuration_secrets.md#secrets), add the new lines to them:

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

=== "Gmail"

    Your Gmail account, or a Google Workspace one, through Gmail's SMTP server. LibreFolio signs in
    with a user and a password only, not with «Sign in with Google», so Gmail needs an
    **app password**, not the password of your Google Account.

    1. Turn on **2-Step Verification** for your Google Account, if it is not on yet: app passwords
       exist only with it.
    2. Open [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords) and
       create an app password, with a name such as `LibreFolio`. Google shows it as a code of 16
       characters, in four groups of four: copy it. If that page offers no way to create one,
       [Google's help page](https://support.google.com/accounts/answer/185833) says why. A work or
       school account may need its administrator.
    3. Add the variables to `.env`:

        ```env
        LIBREFOLIO_SMTP_HOST=smtp.gmail.com
        LIBREFOLIO_SMTP_USER=you@gmail.com
        LIBREFOLIO_SMTP_PASSWORD=abcdefghijklmnop
        LIBREFOLIO_SMTP_FROM=LibreFolio <you@gmail.com>
        ```

        - `you@gmail.com` stands for your full Gmail address, or your full work address with
          Google Workspace.
        - `abcdefghijklmnop` stands for your app password: its 16 characters, written
          **without the spaces**, since LibreFolio uses the password exactly as written, spaces
          included. Better still, keep it in a password file, as in the Docker Compose tab, also
          without the spaces.
        - The sender is the same address, with a name in front or without. Gmail sends only as your
          own address, or as one you added and confirmed under **Send mail as** in Gmail's settings.
        - No `LIBREFOLIO_SMTP_TLS` and no port: `starttls` on port 587 is the default, and one of
          the two ways Gmail offers. For the other, port 465, add `LIBREFOLIO_SMTP_TLS=tls`: the
          port follows.

    4. Restart LibreFolio. With Docker Compose, run `docker compose up -d`:
       `docker compose restart` keeps the old values.
    5. Open **Settings › Administration › Email**, where the state reads **Ready**, and click
       **Send a test email**. It goes to the address of your account: see
       [The Test Email](#test-email).

    To keep it working:

    - A personal Gmail account can send about 500 emails a day: past that, Gmail refuses to send
      for 1 to 24 hours. A Google Workspace account has 2,000 a day through `smtp.gmail.com`. These
      are [Google's limits](https://support.google.com/mail/answer/22839), and Google can change
      them. When Gmail refuses, the test email and the log report the refusal
      ([Sending Errors](email_troubleshooting.md#sending-errors)).
    - LibreFolio's own limit is 50 emails an hour by default, which could reach 1,200 in a day. To
      stay under the personal limit, add `LIBREFOLIO_SMTP_MAX_PER_HOUR=20` to `.env`, that is 480 a
      day, and restart. The count is per server process: see [The Variables](#variables).
    - Google revokes app passwords when the password of your Google Account changes: then create a
      new one, write it in place of the old one and restart. Removing the app password, on the page
      where you created it, also stops LibreFolio from sending.

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
      server, Settings › Administration › Email and the start log show a [warning](email_troubleshooting.md#security).

---

## 🖥️ Settings › Administration › Email {: #email-tab }

Open **Settings** (gear icon in the sidebar), then **Administration** and its **Email** tab, after
**Backup** (on a phone, the shield icon, then the envelope icon). Only administrators see it. The
book icon at its top opens this page.

### 🚦 The State {: #state }

| State | What it means | What the tab shows |
| --- | --- | --- |
| **Off** | `LIBREFOLIO_SMTP_HOST` is not set: nothing is sent. This is the default. | A short explanation, and a pointer to this guide. |
| **Ready** | Every variable can be used. | The emails left this hour, the notices that apply, the address emailed links start with and [its check](#links-check), and **Send a test email**. |
| **Not working** | A variable cannot be used: email stays off until it is fixed. | The problem, naming the variable at fault, and a reminder to restart after the fix. |

!!! note "✅ Ready is not yet a delivered email"

    **Ready** means that every variable can be used. LibreFolio does not contact the server until
    it sends an email: only a test email proves that the server takes your mail.

- **Not working** names one problem at a time, the first it finds: fix it, restart, then look
  again. [Configuration Problems](email_troubleshooting.md#configuration-problems) says what to check for each one.
- With **Ready**, the tab counts the emails left, such as **48 of 50 emails left this hour**: the
  last 60 minutes, not the clock hour. When none is left, it says in how many minutes the next one
  can go. With several server processes, each one counts its own, and the tab shows the count of
  the process that answered.
- The encryption warning appears when `LIBREFOLIO_SMTP_TLS=none` points to a server outside your
  local network: see [Security Notes](email_troubleshooting.md#security).
- A notice about `LIBREFOLIO_PUBLIC_URL` appears when it is not set (information: emails work, but
  none with a link can go out) or cannot start a link (warning): see [Emails with a Link](email_flows.md#public-url).

### 🧭 The Address in Emailed Links {: #links-check }

With the state **Ready** and a usable `LIBREFOLIO_PUBLIC_URL`, the tab shows *Links in emails start
with …*, followed by that address, and checks from this browser that **this** instance answers
there. It is the same signed check as the invitation and reset dialogs
([The Server Address of a Link](users.md#server-address)).

| Message | What it means |
| --- | --- |
| *Checking from this device that this instance answers there…* | The check is running. |
| *This instance answers there, from this device.* | Fine: the links reach this LibreFolio, at least from here. |
| *From this device, another server answers at that address, not this instance.* … | Something answers there, but not this LibreFolio. |
| *This device cannot reach this instance at that address.* … | Nothing answered that this browser could read: a wrong or closed address, a name this device cannot resolve, no answer within 8 seconds, a browser that blocks a public page from reaching a local address or asks your permission first, or an older LibreFolio that cannot answer the check. |
| *This page uses https:// while LIBREFOLIO_PUBLIC_URL starts with http://* … | This browser cannot check an `http://` address from an `https://` page, and the links in emails would travel unencrypted: set the variable to the `https://` address. |
| *This browser cannot read LIBREFOLIO_PUBLIC_URL as an address* … | The browser reads addresses a little more strictly than the server: the links may not open. Check the value. |

!!! warning "📱 This device only"

    The check runs from the browser you are using, so it tells what this device sees. A VPN, a
    direct IP address, its DNS or its network can differ from your users': after a warning, check
    from another device before you change the variable. **Check again** runs the check once more,
    for example after you changed network.

- The check runs once when the tab opens, not after each test email. **Check again** comes with a
  warning.
- Nothing is checked while email is **Off** or **Not working**, nor when `LIBREFOLIO_PUBLIC_URL` is
  not set or cannot be used, which the notice above reports.

### ✉️ The Test Email {: #test-email }

With the state **Ready**, **Send a test email** sends one email to yourself:

- **To your own address**: the email of your account, as in [Profile](../user/settings/profile.md).
  There is no field to type another one.
- **In your language**: the one in your [Preferences](../user/settings/preferences.md), otherwise
  the instance's **Default Language** ([Global Settings](settings.md)), otherwise English.
- **What it says**: its subject is **LibreFolio test email** in English. The message names your
  instance by the address your browser reached it at, not by `LIBREFOLIO_PUBLIC_URL`, and says that,
  if you can read it, LibreFolio can send emails. It comes as plain text with an HTML version.
- **It counts against the hourly limit**, even when the server refuses it.

The result appears below the button. **Test email sent to your address** means that the SMTP server
accepted the message: look in your inbox, and in the spam folder. Otherwise the tab says what went
wrong: see [Sending Errors](email_troubleshooting.md#sending-errors). While LibreFolio talks to the server, the button reads
**Sending…**: LibreFolio waits up to 20 seconds for each step, so a server that does not answer
takes a while to fail.

---

## 🔗 Related

- 📄 **[Email: Links and Messages](email_flows.md)** — Emails with a Link, Links Sent by an Administrator, Forgotten Passwords, …
- 📄 **[Email: When It Does Not Work](email_troubleshooting.md)** — When It Does Not Work, Security Notes
- 📝 **[Configuration](configuration.md)** — The `.env` file and its main options, and
  `LIBREFOLIO_PUBLIC_URL`
- 🔐 **[Configuration: Secrets and Plugin Settings](configuration_secrets.md)** — Secrets in files,
  such as the SMTP password
- 🩺 **[Configuration: Checks and Protections](configuration_security.md)** — The startup checks
- ⚙️ **[Global Settings](settings.md)** — The **Require Email Verification** switch
- 👥 **[Users & Invitations](users.md)** — Waiting accounts, and how to let one in
- 🛠️ **[Command-Line Tools](cli_tools.md)** — Invitation and password-reset links from the command
  line
- 🐳 **[Advanced Docker](docker_advanced.md)** — The Compose file, and the user that runs LibreFolio
  in the container
- 📂 **[Filesystem Structure](filesystem.md)** — Where the log is kept
- 👤 **[Profile](../user/settings/profile.md)** — The email address of your account
- 🧑‍💻 For developers: **[Email Service (SMTP)](../developer/backend/email.md)** — How the service
  works inside
