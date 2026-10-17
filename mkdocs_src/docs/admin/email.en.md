# 📧 Email

LibreFolio can send email through an SMTP server that you name in a few environment variables.
Email is **optional**: without it nothing changes, nothing is sent, and invitation and
password-reset links are copied by hand.

What LibreFolio sends:

- **A test email**, which an administrator sends to their own address from
  **Settings › Administration › Email**, to check that everything works.
- **The invitation and password-reset links an administrator creates**, with **Send by email** in
  their dialogs, instead of copied by hand: [Links Sent by an Administrator](#admin-links).
- **A reset link for a forgotten password**, to whoever asks for one for their account from the
  login page: [Forgotten Passwords](#forgot-password).
- **The setup link of the initial administrator**, once, when LibreFolio creates that administrator
  from `LIBREFOLIO_ADMIN_EMAIL` and generates the link itself: see
  [Hosting for Others](hosting_providers.md#initial-admin).
- **A link to confirm the email address of a new account**, when **Require Email Verification** is
  on: see [Email Verification](#verification).
- **A notice to the old address** when someone changes the email address of their account:
  [Email Address Changes](#email-change-notice).

The emails with a link also need `LIBREFOLIO_PUBLIC_URL`: see [Emails with a Link](#public-url).
While a hosting provider blocks the instance, LibreFolio sends no email at all
([Hosting for Others](hosting_providers.md#instance-block)).

To set it up:

1. Write the `LIBREFOLIO_SMTP_*` variables in `.env`: at least the server and the sender, and the
   login of your account when the server asks for one. The [examples](#examples) cover the usual
   cases.
2. For the emails with a link, set `LIBREFOLIO_PUBLIC_URL` too ([Emails with a Link](#public-url)).
3. Restart LibreFolio.
4. Open **Settings › Administration › Email**: the state reads **Ready**. Send yourself a test email.

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
  emails can carry a link ([Emails with a Link](#public-url)). Nothing else about email is there.
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
      server, Settings › Administration › Email and the start log show a [warning](#security).

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
  an email is refused with `EMAIL_LINKS_UNAVAILABLE`, while the test email still works, and
  **Require Email Verification** cannot be turned on ([Email Verification](#verification)). The
  links you copy, from the [command line](cli_tools.md) for one, stay as they are.
- **What the email says**: it names your instance by the host of `LIBREFOLIO_PUBLIC_URL`, and says
  how long the link still works: 7 days for a new invitation, 30 minutes for a reset link, 24 hours
  for a verification link, 72 hours for the setup link of the initial administrator. A link works
  once.
- **The secret part** of the link comes after `#`: browsers never send it to the server, so it
  stays out of server and proxy logs.
- **To check it**: with email **Ready**, Settings › Administration › Email shows a notice when
  `LIBREFOLIO_PUBLIC_URL` is not set or cannot be used, and the start log has a line
  ([What the Log Says](#logs)). Once it can be used, the tab shows the address and checks, from
  your browser, that this instance answers there: see [The Address in Emailed Links](#links-check).
  From anywhere, `/api/v1/system/instance` shows `"links": true` once email and the address are
  both fine.

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
  again. [Configuration Problems](#configuration-problems) says what to check for each one.
- With **Ready**, the tab counts the emails left, such as **48 of 50 emails left this hour**: the
  last 60 minutes, not the clock hour. When none is left, it says in how many minutes the next one
  can go. With several server processes, each one counts its own, and the tab shows the count of
  the process that answered.
- The encryption warning appears when `LIBREFOLIO_SMTP_TLS=none` points to a server outside your
  local network: see [Security Notes](#security).
- A notice about `LIBREFOLIO_PUBLIC_URL` appears when it is not set (information: emails work, but
  none with a link can go out) or cannot start a link (warning): see [Emails with a Link](#public-url).

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
wrong: see [Sending Errors](#sending-errors). While LibreFolio talks to the server, the button reads
**Sending…**: LibreFolio waits up to 20 seconds for each step, so a server that does not answer
takes a while to fail.

---

## 📨 Links Sent by an Administrator {: #admin-links }

An invitation or a password-reset link that an administrator creates can go out by email, instead
of being copied by hand. While email is **Ready** and `LIBREFOLIO_PUBLIC_URL` can be used
([Emails with a Link](#public-url)), the invitation and reset dialogs of
[Users & Invitations](users.md#send-by-email) show **Send by email** under the link:

1. Create the link as usual: **Invite**, or **Password-reset link** on the person's row.
2. For an invitation, check the address in **Send to**: it starts with the one written in the
   invitation, and you can change it. A reset link has no field: it goes to the address of its
   account.
3. For an invitation, choose the **Language of the email**: **The instance's language** writes it
   in the instance's **Default Language** ([Global Settings](settings.md)); pick English,
   Italiano, Français or Español for someone who reads another one. A reset link goes in its
   account's language.
4. Click **Send by email**. The dialog says *Sent to …* with the address and the language the email
   was written in, or why the email did not go out ([Sending Errors](#sending-errors)).

The rules:

- **The link in the email starts with `LIBREFOLIO_PUBLIC_URL`**, whatever **Server address** the
  dialog shows: only the secret part of the link travels from the dialog. The dialog says so above
  the button.
- **An invitation** goes to the address in **Send to**, or else to the one written in the
  invitation, in the language chosen in **Language of the email**, the instance's **Default
  Language** unless you picked another. It is the email's language only: it does not become the
  language of the account the invitation creates. It names you as the person who invites, and says so when the new account will be an administrator.
- **A password-reset link** goes only to the address of its account, in the account's language,
  and only while the account is active.
- **Only a live link** goes out: one that has expired, was used or was revoked is refused, and a
  new one must be created.
- Each email counts against the hourly limit.

---

## 🗝️ Forgotten Passwords {: #forgot-password }

Someone who forgot their password can ask for a reset link by email, with their username or their
email address, without signing in. On the login page, **Forgot Password?** opens a form for it
while emails with a link can go out: email **Ready** and a usable `LIBREFOLIO_PUBLIC_URL`. Below the
form, a panel closed until clicked keeps the command an administrator can run on the server.
Otherwise the page shows that command, open, under the warning *Email recovery is not available on
this instance. Reset your password from the server terminal, or ask your administrator for a
password-reset link.* An administrator creates that link in **Settings › Administration › Users**,
even without email ([Password-Reset Links](users.md#reset-links)).

It is safe because changing an account's email address asks for its current password
([Profile](../user/settings/profile.md)): see [Security Notes](#security).

It works this way:

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
| 3 emails an hour to the same mailbox, whatever account they are for and however its address is written | Nothing is sent, and the answer stays the same. |
| 1 email every 5 minutes, and 3 an hour, for the same account, the reset links an administrator created included | Nothing is sent, and the answer stays the same. Two requests at the same moment cannot both send. |

The limit per account counts the account's reset links in the database. The others are kept in the
memory of each server process: with several processes, each keeps its own count, and a restart
forgets them. A reset email that did not go out still counts, for the account and for the mailbox.

**One mailbox, however its address is written.** The limit per mailbox counts the aliases of an
address as one mailbox: capitals do not count, nor a `+tag` on any domain (`name+news@example.com`
is `name@example.com`), nor the dots of a Gmail address, where `googlemail.com` is `gmail.com`
(`first.last@googlemail.com` is `firstlast@gmail.com`). The limits of the
[verification emails](#verification-limits) and of the
[notices of an email change](#email-change-notice) count the same way. Each email still goes to the
address exactly as the account has it. A mailbox that takes mail under any name, such as a catch-all
domain or Fastmail's `anything@user.fastmail.com`, counts each name apart: only the hourly limit of
the instance holds those back.

**Behind a reverse proxy**, the address that counts is the visitor's, as LibreFolio reads it (see
*The Visitor's Address* in [Checking Connection Security](connection_checks.md)):

- When `LIBREFOLIO_CLIENT_IP_HEADER` names the header your proxy sets with the visitor's address
  (`Fly-Client-IP` on Fly.io, `X-Real-IP` from Nginx), LibreFolio reads it there. Set it only if
  every request crosses that proxy: a visitor who reaches LibreFolio directly could write the header.
- Otherwise it is the address the server (uvicorn) sees, which takes the visitor's address from the
  proxy's `X-Forwarded-For` header only when the proxy's address is listed in `FORWARDED_ALLOW_IPS`
  (`127.0.0.1` when not set). List your proxy's addresses or networks there, such as
  `172.18.0.0/16`, never `*`: with `*`, uvicorn takes the first address of the header, which the
  visitor can write.
- **A proxy LibreFolio does not trust, on a local address** (a Docker network, your own network or
  your VPN), such as a proxy container in front of the Docker image, the usual setup: these limits
  per address leave the requests through it out, so that 10 requests from anyone cannot block
  **Forgot password?**, **Send the link again** or the registration emails for everyone. The limits
  per username or email address, per account and per mailbox, and the hourly limit of the instance,
  still count them. The log warns once per server process, and the security checks report it as a
  warning of `platform.client_address` (see *The Visitor's Address* above).
- **A proxy LibreFolio does not trust, on a public address**, such as a CDN: every visitor shares
  the proxy's address and its count, so 10 requests from anyone block those requests through the
  proxy for everyone, for up to 15 minutes (an hour for the registration emails). Tell LibreFolio
  about the proxy.

---

## ✅ Email Verification {: #verification }

With **Require Email Verification** on, a new account cannot sign in until its owner opens a link
that LibreFolio emails to the address of the account. The switch is in
**Settings › Administration › Global Settings**, in the **Security** category
([Global Settings](settings.md)), and it is off by default.

- **Who waits**: every account created from the registration page while the switch is on, the
  ones opened with an invitation included. The first account of a new instance, its administrator,
  never waits, nor does the administrator LibreFolio creates from `LIBREFOLIO_ADMIN_EMAIL`, which
  its setup link activates; neither do the accounts created with `user create` on the
  [command line](cli_tools.md), nor the accounts that already exist.
- **Right after the registration**, the login page says: *Account created. We sent you an email
  with a link to activate it: open it within 24 hours, then sign in.*
- **The email**, *Confirm your email address*, leaves at once, unless a limit holds it back
  ([Limits of the Verification Emails](#verification-limits)), in the instance's
  **Default Language**: a new account has no language of its own yet. Its button,
  **Confirm my email address**, opens a link that starts with `LIBREFOLIO_PUBLIC_URL`
  ([Emails with a Link](#public-url)) and works once, for 24 hours.
- **Until the link is opened**, the account cannot sign in. Signing in with the right password says
  that the address is not verified yet, and offers **Send the link again**: a new link, which stops
  the older ones. With a wrong password, the login gives its usual refusal, so nobody learns more
  than from any other attempt.
- **Once the link is opened**, the account is active, and its owner is back on the login page with a
  confirmation. What the person sees, step by step: *If LibreFolio Asks You to Confirm Your Email*
  in [Getting Started](../user/getting-started.md).
- **While a hosting provider blocks the instance**, the page of the link says so and offers no
  retry: the link is not used up, and works again once the instance is unblocked, as long as it has
  not expired; otherwise signing in offers a new one
  ([Hosting for Others](hosting_providers.md#instance-block)). Signing in still offers
  **Send the link again**, which then says *This instance is blocked by its hosting provider: try
  again once it is unblocked.*, never that the password is wrong, and works once the instance is
  unblocked. Nobody can sign up meanwhile: the registration page says the same.

### 🔀 Turning It On and Off {: #verification-switch }

- **It turns on only while emails with a link can go out**: email **Ready**
  ([Settings › Administration › Email](#email-tab)), a usable `LIBREFOLIO_PUBLIC_URL`
  ([Emails with a Link](#public-url)), and an instance that no hosting provider blocks. Until then,
  while it is off, the switch is greyed
  out, with the hint *Needs an email with a link to go out: set up SMTP and LIBREFOLIO_PUBLIC_URL
  first (Settings › Administration › Email).* Should that change between the moment you open the tab and your save,
  the save is refused — *Email verification needs an email with a link to go out, and none can go
  now: check Settings › Administration › Email.* — and nothing of it is stored.
- **Turning it off always works.** The accounts already waiting keep waiting: their links still
  work, and so does **Send the link again**. To let one in at once, activate it
  ([Waiting Accounts](#verification-waiting)).
- **While it is on, saving the other settings always works**, even when email has stopped working
  since.
- **If email stops working while it is on** — the server or a variable breaks — nobody can sign up
  any more, not even with an invitation, which stays valid: the registration page says *Sign-up is
  not possible right now: this instance cannot send the verification email. Try again later, or ask
  its administrator.*, and no account is created. Only the first account of a new instance is let
  through. **Send the link again** fails the same way.
  Fix email ([When It Does Not Work](#troubleshooting)), or turn the switch off.

### ⏳ Waiting Accounts {: #verification-waiting }

In **Settings › Administration › Users**, a waiting account shows as **Deactivated**: this version
does not tell it apart from an account an administrator deactivated.

- **It takes a place** of the user limit (`LIBREFOLIO_MAX_USERS`) while its link is live, like an
  open invitation. When the last link sent expires, 24 hours later, the place is free again, and
  **Send the link again** then needs a free place: on a full instance, its owner is told to ask you.
- **To let it in without the email**, click **Reactivate** on its row
  ([Accounts Waiting for Their Email](users.md#waiting)), or run `user activate` on the
  [command line](cli_tools.md): it can sign in at once, and the links already sent stop working.
  While its link is live, this takes no extra place, since its place is already counted:
  **Reactivate** works even on a full instance, and `user activate` prints no limit warning. Once
  the link has expired, reactivating it needs a free place, as for any deactivated account.
- **To turn it away**, delete it ([Delete an Account](users.md#delete)), or deactivate it: with
  `user deactivate` on the command line, or with the administrator API
  (`PATCH /api/v1/users/{id}` with `is_active: false`). Deactivated, it stops waiting: its links stop
  working, its place is free, and signing in tells its owner that the account is disabled. The
  Users tab itself offers no **Deactivate** for an account that is not active: there, **Delete** is
  the way.

### 📏 Limits of the Verification Emails {: #verification-limits }

| Limit | Past it |
| --- | --- |
| The emails of 10 registrations an hour from the same address; an IPv6 address counts by its /64 | The next new accounts are still created and wait, but their emails do not leave: their owners ask for the link again from the login page, under the limits below. |
| 10 requests of **Send the link again** every 15 minutes from the same address, counted before the password is checked; an IPv6 address counts by its /64 | The request is refused until the oldest of them is 15 minutes old. |
| The sign-in's own limit on wrong passwords, shared with the login page: 10 every 15 minutes for the same username or email address, 50 from the same address (see *Failed Sign-ins* in [Configuration](configuration.md)) | The request is refused before the password is checked: the page says in how many minutes to try again. The right password clears the failures of what was typed. |
| 1 email every 5 minutes, and 3 an hour, for the same account, the email of the registration included | The request is refused: the page says in how many minutes to try again. |
| 3 emails an hour to the same mailbox, whatever account they are for and however its address is written ([Forgotten Passwords](#forgot-password)): the email of a registration and the links sent again alike, and only the emails that went out | **Send the link again** is refused: the page says in how many minutes to try again. After a registration, the account is created and waits, but no email leaves: its owner asks for the link again later. |
| The hourly limit of the instance, `LIBREFOLIO_SMTP_MAX_PER_HOUR` | The request is refused until an email fits again. |
| A free place, once the account's link has expired | The request is refused: its owner is told to ask you. |

A link whose email did not go out counts neither for the account nor for the mailbox. If the
account stops waiting in the meantime — its link opened, or an administrator activated or
deactivated it — no new link is sent. The limits per address and per mailbox are kept in the memory
of each server process: with several processes, each keeps its own count, and a restart forgets
them. Behind a reverse proxy, the address that counts follows the rules given in
[Forgotten Passwords](#forgot-password).

---

## 🔔 Email Address Changes {: #email-change-notice }

When someone changes the email address of their account, in [Profile](../user/settings/profile.md),
LibreFolio writes to the address the account had **before**:

- **Only to the old address**: the new one gets nothing.
- **Nothing of the new address, and no username**: the email says only that the address changed,
  without any part of the new one, not even its domain, and it opens with a plain «Hello,»
  ([Security Notes](#security)).
- **No link.** It tells the owner that, if they did not make the change, someone may be using their
  account: change the password at once if they still can, and tell you.
- **In the account's language.** It names your instance by the host of `LIBREFOLIO_PUBLIC_URL`, with
  its port if it has one, or «LibreFolio» when the variable is not set or cannot be used: with no
  link inside, the notice does not need it.
- **After the change**: the email leaves after the answer, and the change never waits for it. With
  email off, nothing is sent, and the log says so in an information line, not a warning. The notice
  counts against the hourly limit like any email.
- **At most 3 an hour for an account, and 3 an hour to the same mailbox**, however its address is
  written ([Forgotten Passwords](#forgot-password)). Past either, the change still goes through and
  the notice is skipped. Without these limits, an account could point its email at any address and
  change it again, to make your instance write there.
- **Not for capitals alone.** Changing only the capitals of the letters A to Z, such as
  `Anna@example.com` for `anna@example.com`, is no change of address, so no notice goes. Accented
  letters count as different: `Émile@example.com` for `émile@example.com` is a change, with its
  notice.

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
| Email is off or not working on this instance. | `EMAIL_UNAVAILABLE` | The configuration changed since the dialog opened, for example after a restart: look at [Settings › Administration › Email](#email-tab). |
| Emails cannot carry links: LIBREFOLIO_PUBLIC_URL is not set, or cannot start a link. | `EMAIL_LINKS_UNAVAILABLE` | Set it, then restart: see [Emails with a Link](#public-url). |
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
included (*Startup Checks* in [Configuration](configuration.md)). A configuration that cannot be
used shows there in two lines, the first two below; `none` towards a server outside your local
network, and a missing or invalid `LIBREFOLIO_PUBLIC_URL`, in one line each. None of them stops
the start. The same three checks are in the **Security** tab of **Settings › Administration**,
read again when you ask, where a finding links to the [Email tab](#email-tab) (see «Security» in
[Global Settings](settings.md)).

| The log says | Level | When |
| --- | --- | --- |
| `Email configuration cannot be used: email stays off` | `error` | A variable cannot be used. Each server process logs it once, at startup, with `variable`, `problem` (the code) and `reason`: the rule it breaks, or why the password file cannot be read. |
| `LIBREFOLIO_SMTP_… cannot be used (SMTP_…): email stays off until it is fixed` | `error` | At startup, after the line above, with `check` set to `email.smtp`: the startup checks report the same problem. |
| `LIBREFOLIO_SMTP_TLS=none with …: emails, their links and the SMTP password travel unencrypted; use starttls or tls` | `warning` | At startup, with `check` set to `email.smtp_encryption`: `none` towards a server outside your local network, which the line names ([Security Notes](#security)). |
| `LIBREFOLIO_PUBLIC_URL is not set: emails work, but none with a link (forgotten password, invitation, reset) can go out` | `info` | At startup, with `check` set to `email.links`: email works, but `LIBREFOLIO_PUBLIC_URL` is not set ([Emails with a Link](#public-url)). |
| `LIBREFOLIO_PUBLIC_URL cannot start a link (it needs http:// or https:// and a host, with no user name, password, ? or #): no email with a link (forgotten password, invitation, reset) can go out` | `warning` | At startup, with `check` set to `email.links`: email works, but the variable cannot start a link ([Emails with a Link](#public-url)). |
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
| `Verification email held: too many registrations from this address` | `info` | The address of the registration already had the emails of 10 registrations in the hour: the account waits without its email; with `user_id`. |
| `Verification link emailed` | `info` | A verification link went out: `user_id`, `token_id` and `language`. |
| `Verification email: not sent` | `warning` | The email of a registration did not go out: `reason` and `code` say why. The account still waits, and its owner can ask for the link again. |
| `Verification email: the account no longer waits, nothing sent` | `info` | An administrator activated, deactivated or deleted the account before its email left; with `user_id`. |
| `Verification email: the request failed` | `error` | An unexpected error, with its type in `error` and the `user_id`, nothing more. |
| `Login refused: email not verified` | `info` | A waiting account signed in with the right password; with `user_id`. |
| `Verification resend refused: wrong credentials` | `warning` | Someone asked for a new verification link with a wrong password, or for an account that does not exist. Neither what was typed nor the address is logged. |
| `Email verified` | `info` | A link was opened: the account is active; `user_id` and `token_id`. |
| `Email verification refused: the link's email did not go out` | `info` | Someone opened a link whose email LibreFolio counted as not sent: the account still waits, and **Send the link again** works. |
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
  LibreFolio email one of your users a link to a site of theirs ([Emails with a Link](#public-url)).
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
  per account ([Forgotten Passwords](#forgot-password)).
- **Changing an account's email address asks for its current password.** Without it, a moment
  inside someone's session (a stolen session cookie, a computer left unlocked) would be enough to
  put one's own address on the account, then reset its password from there: reset by email opened
  only together with this rule. When email works, the old address also gets a notice
  ([Email Address Changes](#email-change-notice)).
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
