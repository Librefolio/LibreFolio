# 🏗️ Hosting for Others: Your Instances

This page is part of the guide for whoever runs LibreFolio for other people. It covers what an instance does for each customer: the **initial administrator** the instance creates at its first start, and the **instance block** that closes the app but keeps the data.

The rest of the guide starts on [Hosting for Others](hosting_providers.md).

---

## 👑 The Initial Administrator {: #initial-admin }

Give each new instance its administrator from the environment. At its first start, the instance
creates the account for the address you name, not yet active, and a setup link that works once, for
72 hours. The link opens the instance's setup page, where your customer chooses the password and is
signed in ([What Your Customer Sees](#initial-admin-setup-page)). Nobody can register first and take
the administrator's place, even on an instance that is reachable from the internet from its first
minute.

### ⚙️ The Variables {: #initial-admin-variables }

| Variable | What it does |
| --- | --- |
| `LIBREFOLIO_ADMIN_EMAIL` | Your customer's email address, the administrator's. Setting it turns the initial administrator on |
| `LIBREFOLIO_ADMIN_USERNAME` | The administrator's username, `admin` when not set: 3 to 50 characters, without `@` |
| `LIBREFOLIO_ADMIN_BOOTSTRAP_TOKEN` | The token of the setup link, chosen by your panel: 32 to 200 characters, only letters, digits and `-` `.` `_` `~`. `LIBREFOLIO_ADMIN_BOOTSTRAP_TOKEN_FILE` reads it from a file instead, as Docker mounts its secrets |

- Set them in the container's environment, or in `.env`, like the other variables of this page.
- A value LibreFolio cannot use stops the server at startup, with an error that names the variable,
  never the token. They are checked at every start, after the setup too.
- Every detail, the case without a token included, is in «The Initial Administrator» in
  [Environment Variables](configuration.md).

### 🧾 Create the Administrator {: #initial-admin-create }

1. Generate the token:

    ```bash
    openssl rand -hex 32
    ```

2. Before you start the new instance, give it the three variables:

    ```bash
    LIBREFOLIO_ADMIN_EMAIL=anna@example.com
    LIBREFOLIO_ADMIN_USERNAME=anna
    LIBREFOLIO_ADMIN_BOOTSTRAP_TOKEN=<the 64 characters printed by openssl>
    ```

3. Start the instance. Its log says `Initial administrator created, waiting for its setup link`.
4. Send your customer the link: the instance's address, then `/setup#token=` and the token, such as
   `https://librefolio.example.com/setup#token=<the token>`. LibreFolio neither logs nor emails
   this link: delivering it is up to you, for example in your own «set your password» email.

- ⏱️ The link works once, for 72 hours from that first start. A restart changes nothing: the link
  you sent keeps working until it is used or expires, unless you give the administrator a new
  address or cancel the link ([A New Link](#initial-admin-new-link)), or the account is set up
  another way ([Once the Account Is Active](#initial-admin-active)).
- 🔒 The token travels after the `#` of the link, a part that browsers never send to the server, so
  it stays out of the access logs of the server and of every proxy on the way. Keep it as private as
  a password until your customer has used it.
- 🚪 The first start also sets **Registration** to **By invitation**: after the administrator,
  people join with an invitation link. `LIBREFOLIO_REGISTRATION`, if you set it, still decides.
- 📏 With `LIBREFOLIO_MAX_USERS`, the administrator takes a place from the first start, while it
  waits too.
- ⛔ While the instance is [blocked](#instance-block), the setup link does not work: the setup is
  refused until you unblock the instance, and the 72 hours keep running meanwhile. If the link
  expires in the meantime, give a new one ([A New Link](#initial-admin-new-link)). The setup page
  still opens its form, then refuses the setup and says why: see
  [What Your Customer Sees](#initial-admin-setup-page).
- 🔑 Without `LIBREFOLIO_ADMIN_BOOTSTRAP_TOKEN`, the instance generates the token: it writes the
  link once in its log, and emails it to `LIBREFOLIO_ADMIN_EMAIL` when its [email](email.md) works
  and `LIBREFOLIO_PUBLIC_URL` is set. A token of your own lets your panel know the link before the
  instance starts, without reading its log.
- 📊 Your panel can follow the setup without reading the log either: whether the link waits, was
  used or expired, in [The Setup Status](hosting_panel_api.md#panel-status).

### 🖥️ What Your Customer Sees {: #initial-admin-setup-page }

The setup page needs no account. When your customer opens the link:

1. The page takes the token out of the address bar at once, so that it stays out of the browser's
   history and bookmarks, then asks the instance whether the link still works.
2. A link that works opens the form: it names the account, by its username, and asks for the
   password twice. The password must meet the rules shown under the field, the instance's own: the
   form sends nothing until it does and the two passwords match. A password manager that saves the
   new password files it under that username.
3. Once the form is sent, the account is active and your customer is signed in. The app opens with
   the [Welcome setup](../user/getting-started.md#welcome-setup), as for any new account.

When the setup cannot go through, the page says why:

| The page shows | When | What to do |
| --- | --- | --- |
| *This link has expired.*, *This link has already been used.*, *This link has been withdrawn.*, *This link is not valid.* or *This link is incomplete: open it again from the message you received.*, then *Ask your hosting provider for a new link. On your own server, run `dev.py user setup-link`.* | The link is more than 72 hours old, was used, was replaced by a newer one, was cancelled, was withdrawn when the administrator's address changed or when the account was set up another way, is unknown to the instance, or lost its token when it was copied; also a link that stops working while the form is open, and a link left over on an account already set up, which the setup refuses once the form is sent | Give your customer a new link: [A New Link](#initial-admin-new-link). An account already set up, another way or through another of its links, gets none: see [Once the Account Is Active](#initial-admin-active) |
| *The link could not be checked. Try again in a moment.*, with **Retry** | The instance did not answer the check | **Retry** once the instance answers |
| *Password does not meet security requirements* | The password misses one of the instance's rules | Choose a password that meets the rules shown under the field |
| That the setup is refused while the instance is blocked, and no button to send the form any more | The instance is [blocked](#instance-block): the form opens, and the setup is refused once it is sent | Unblock the instance: your customer then opens the link again, within its 72 hours |
| That the setup failed | Any other problem | Send the form again |

### 🔁 A New Link {: #initial-admin-new-link }

If your customer has not used the link within 72 hours, each start of the instance logs a warning:
`The initial administrator's setup link has expired: run ./dev.py user setup-link, or set a new LIBREFOLIO_ADMIN_BOOTSTRAP_TOKEN`.
Either way gives a new link, which works for 72 hours, and ends the earlier ones:

- **A new token**: generate one, put it in `LIBREFOLIO_ADMIN_BOOTSTRAP_TOKEN` and restart the
  instance (with Docker Compose, `docker compose up -d`: `docker compose restart` keeps the old
  values), then send the new link. Generate a new token each time: a value the instance has already
  seen never gives a new link.
- **The command line**, from a shell on the server:
  `docker compose exec librefolio python dev.py user setup-link` prints a new link, with a token the
  instance generates. See «A New Setup Link for the Initial Administrator» in
  [CLI Admin Tools](cli_tools.md).

Both work before the link expires too, to replace a link that went astray.

To stop a link that went astray without sending a new one yet, cancel it from a shell on the
server, with the administrator's username (`admin` unless `LIBREFOLIO_ADMIN_USERNAME` names
another): `docker compose exec librefolio python dev.py user deactivate <username>`. Another
administrator of the instance can do the same with **Cancel setup link** in
[Users & Invitations](users.md#cancel-setup), but not for a protected account, whose button is off. The link you sent stops working at once, and every
other setup link of the account with it, while the account keeps waiting for its setup: when you
are ready, give a new link in one of the two ways above. Until then, each start logs the warning
`The initial administrator's setup link was withdrawn (cancelled, or its address changed): run ./dev.py user setup-link, or set a new LIBREFOLIO_ADMIN_BOOTSTRAP_TOKEN`.
Restarting with the same `LIBREFOLIO_ADMIN_BOOTSTRAP_TOKEN` gives no new link: the instance
has already seen that token.

To change the address or the username before your customer activates the account, change
`LIBREFOLIO_ADMIN_EMAIL` or `LIBREFOLIO_ADMIN_USERNAME` and restart: the waiting account takes the
new value. If another account already holds it, the log has an error, and the account keeps its
own; its link keeps working.

A new address always needs a new link: the link you sent went to the old address, so it stops
working at the start that gives the account its new one. Put a new token in
`LIBREFOLIO_ADMIN_BOOTSTRAP_TOKEN` together with the new `LIBREFOLIO_ADMIN_EMAIL`, restart, then
send the new link to the new address. Without a new token, that start logs
`The initial administrator's address changed: the setup link handed over before no longer works; run ./dev.py user setup-link, or set a new LIBREFOLIO_ADMIN_BOOTSTRAP_TOKEN`;
the starts after it log the same warning as after a cancellation, that the link was withdrawn,
until you give a new link in one of the two ways above. The same address with other capitals of
the letters A to Z, such as `Anna@example.com` for `anna@example.com`, is not a new address: the
account takes the new spelling and its link keeps working, as it does when only the username
changes.

### ✅ Once the Account Is Active {: #initial-admin-active }

Once your customer has chosen the password, the variables have done their work: every later start
creates nothing and logs `LIBREFOLIO_ADMIN_* ignored: this instance already has accounts`. You can
leave them set, or remove them. On an instance that already has accounts, they create nothing
either.

The setup link is not the only way to set the account up. On the server, `dev.py user activate`
and `dev.py user reset` work on the waiting account as on any other, and so does a password-reset
link made for it, by `dev.py user reset-link` or by another administrator in
[Users & Invitations](users.md#reset-links) (see «Reset a Password or Lock an Account» and «Send a
Password-Reset Link» in [CLI Admin Tools](cli_tools.md)). As soon as the account is activated, or
gets a password, this way, it no longer waits for its setup:

- every setup link it had stops working for good, the one you sent included: the setup page says
  *This link has been withdrawn.*;
- no new link replaces it: `dev.py user setup-link` stops with
  `No administrator account is waiting for its setup link`, and every later start ignores the
  variables, as above, a new token included;
- your customer signs in with the password set that way, once the account is active. Activated
  alone, the account has a password nobody knows until `dev.py user reset` or a reset link gives it
  one; given a password alone, it stays inactive until `dev.py user activate`, or **Reactivate** in
  [Users & Invitations](users.md#pending-setup).

### 📬 Changing the Administrator's Address {: #owner-email-change }

The account that owns a managed instance, the one with the address of `LIBREFOLIO_ADMIN_EMAIL`, cannot
change its own address from the app: it answers `409 ACCOUNT_PROTECTED`. When your customer's contact
changes, you change it from the host, and LibreFolio asks the **new** address to confirm it before
anything moves. The instance remembers which account is its owner (a mark on the account, not
visible in the app or in the API), so changing the variable never makes it lose track of who it is.

1. Update your registry, set `LIBREFOLIO_ADMIN_EMAIL=new.contact@customer.example` and restart the
   instance.
2. At that start LibreFolio emails a confirmation link, valid for **7 days**, to the *new* address
   (it needs [email and `LIBREFOLIO_PUBLIC_URL`](email_flows.md#public-url)). It is sent once: a restart
   while that link is still valid sends nothing more, and a link that expired is replaced at the next
   start.
3. Your customer opens it from the new address. The account moves to the new address, which counts as
   verified, every session of the account ends and the previous address gets a notice that it
   changed. The password does not change: from then on the account signs in with the new address.

Until the link is opened, **nothing changes**: the account keeps its old address, it stays protected
(nobody can delete, deactivate or demote it from the app), and your customer keeps working. If you
change the variable again before the click, the link already sent stops working and the next start
sends a new one for the latest address.

**An address that belongs to another account.** If another account of the instance already has the
new address, nothing is sent and nothing changes: the start logs an error saying that
`LIBREFOLIO_ADMIN_EMAIL` belongs to another account, the owner keeps its address and its
protection, and the other account is *not* protected (only the owner is). Free the address, for
example with `./dev.py user set-email`, or change the variable, and restart. The same applies if the
address is taken between the email and the click: the link is refused and revoked.

**Without email.** If email is off or cannot be used, or `LIBREFOLIO_PUBLIC_URL` is not set, or the
SMTP server refuses the message, LibreFolio writes the link in the startup log as a `warning`, as it
does for the `/setup` link: *Confirmation link for the instance owner's new email address*. Pass it on
to your customer, who must open it. It is written only when the email did not go; and without
`LIBREFOLIO_PUBLIC_URL` it is a path, to put after the address of your server.

**A customer who has not set the password yet.** While the first administrator still waits for its
`/setup` link, nothing of this applies: changing the variable follows
[the rules of the initial administrator](#initial-admin-variables), the waiting account takes the new
address and the links you sent to the old one stop working. The confirmation link is only for an
owner that is already active.

**A link that got lost.** There is no command to send the link again, and the instance never keeps it:
only its fingerprint is stored. If the customer never received it, or it expired, put `LIBREFOLIO_ADMIN_EMAIL`
back to the **old** address and restart (the instance sees no change and revokes the unused link), then set the
**new** address again and restart: a new link goes out. The previous link stays valid for 7 days, so a customer who
finds it can still use it; a restart with the new address in place never sends a second one while it is valid.

**The old address.** When the link is confirmed, the old address receives a short, generic notice that the
address of the account changed. It does not say the new address, so that nobody who still reads the old mailbox
learns it.

**Who counts as the owner.** At a start with no owner recorded, the instance records the account that has the address
of `LIBREFOLIO_ADMIN_EMAIL` as the owner only if it is an **active administrator**. An ordinary account, or a
deactivated administrator, that has that address is not recorded (the start logs an error that does not name the
address or the account) and is not protected as the owner. The first administrator the instance creates for
you is recorded from the start.

!!! note "State of a change"

    The instance knows whether a change is *pending* (waiting for the click, or for a new link at the next start)
    or *blocked* (another account holds the address), and never carries an address. You see it in three places:
    the `owner_email_change` key of the panel's [status](hosting_panel_api.md#panel-status) (`pending`, `blocked` or `null`), the
    security check `accounts.owner_email_change` that an administrator reads in Settings › Administration ›
    Security (`info` while pending, `warning` when blocked), and the startup log. A *blocked* change asks you to
    act: change the variable to an address no other account uses and restart.

### 🔁 Restoring a Backup on a Managed Instance: the Owner {: #restore-owner }

A backup can come from any instance, and whoever prepared it can write anything in it, so on a managed instance nothing in its
accounts, passwords or one-time links is trusted. When an administrator restores a backup from the app, the restore asks which
account of that backup is the owner, and then, in one step:

1. that account gets the address of `LIBREFOLIO_ADMIN_EMAIL`, becomes an active administrator and the **only** owner: the
   owner mark of every other account is removed, so the owner the backup had is no longer protected;
2. its password becomes unusable (nobody can sign in with the password the backup carried, whoever prepared it) and its
   open sessions end;
3. every one-time link of that account that the backup carried is cancelled: its password-reset links are deleted and its
   other links (email verification, setup, email change) are revoked, whatever they said;
4. one new password-reset link is emailed to the address of `LIBREFOLIO_ADMIN_EMAIL`, so the real owner chooses a password.

If the email cannot go (email off or unusable, no `LIBREFOLIO_PUBLIC_URL`, the hourly limit, a refusal by the SMTP server), the
link is written in the **log of the instance** as a `warning`, *Password-reset link for the instance owner*, and nowhere else:
the report of the restore says only that the link is in the log, and never contains it, because the report can be read by any
administrator. Pass the link to the owner. When the email went, the link is in no log.

If the first start after the restore is repeated, the step is repeated too: the previous link stops working and a new one is
sent. A restore made from the hosting panel does none of this. The whole restore is described in
[Backup & Restore](backup_restore.md).

---

## 🔒 Blocking an Instance {: #instance-block }

A hosting provider can block an instance, for example when its subscription is not paid. Users can
still sign in, follow a password-reset link already sent to them, read why the instance is blocked
and sign out, and administrators can still download a backup of the instance; the rest of the app is
closed.
LibreFolio deletes nothing: the data stays as it is. The block works in both profiles.

### ⚙️ The Variables {: #block-variables }

| Variable | Values | What it does |
| --- | --- | --- |
| `LIBREFOLIO_BLOCKED` | `1`, `true`, `yes` or `on` block; `0`, `false`, `no` or `off` do not, in any case. Not set or empty: not blocked | Blocks the instance |
| `LIBREFOLIO_DELETION_DATE` | An ISO date, such as `2026-11-14`. Not set or empty: no date | The day you will delete the instance and its data, shown to the users on the block page |

To block an instance and announce its deletion date:

```bash
LIBREFOLIO_BLOCKED=true
LIBREFOLIO_DELETION_DATE=2026-11-14
```

- LibreFolio reads both from its environment. Set them in the container's environment, or in
  `.env`: `./dev.py` and Docker Compose (`env_file: .env`) hand the values of `.env` to the server.
- A change applies when the server restarts. With Docker Compose, run `docker compose up -d`:
  `docker compose restart` keeps the old values.
- To lift the block, remove `LIBREFOLIO_BLOCKED` or set it to `false`, then restart.
- Any other value stops the server at startup, so a typo never leaves the instance blocked or open
  by chance. The error names the variable:

    ```text
    LIBREFOLIO_BLOCKED must be one of 1/0, true/false, yes/no, on/off, or unset
    LIBREFOLIO_DELETION_DATE must be an ISO date such as 2026-11-14, not '14/11/2026'
    ```

- While the instance is blocked, every start logs a warning,
  `Instance blocked by its hosting provider (LIBREFOLIO_BLOCKED): only a few API routes answer`,
  with the deletion date when there is one.
- While the instance is blocked, the [market data scheduler](settings.md#market-data-scheduler)
  runs no job: prices and exchange rates are not updated. Once you lift the block, its first run
  catches up the history sync missed in the meantime and fills the gap the block left, going back
  to each asset's and FX pair's last saved day, up to a year.
- A restore that an administrator confirmed before the block, and that still waits, is not applied
  while the instance is blocked: the first start after the unblock applies it. On the server,
  `backup pending` shows it waiting (`instance_blocked`), and `backup pending --cancel` drops it: see
  «Follow or Cancel a Restore» in [CLI Admin Tools](cli_tools.md). Two consequences:
  - its checked copy keeps its disk space in the data directory for the whole block: `backup pending
    --cancel` frees it;
  - if you update LibreFolio during the block, the first start after the unblock also migrates the
    restored database, checked at the version of then, as any update does; the data of before stays
    aside until that start completes, and if the start fails the next one puts it back.

### 👀 What Users See {: #what-users-see }

After signing in, users get a full page instead of the app, **This instance is blocked**:

- it says that the hosting provider has blocked the instance, for example because its subscription
  is not paid;
- administrators read that they should settle it with the provider to unblock the instance; the
  other users, that they should ask their administrator for a backup of their data;
- with `LIBREFOLIO_DELETION_DATE`, it adds the date, in the user's language: *The instance and its
  data will be deleted on …*;
- with `LIBREFOLIO_BILLING_URL` ([Environment Variables](configuration.md)),
  administrators also get a **Manage subscription** link to your subscription page, which opens in
  a new tab; the other users do not see it;
- administrators also get a second card under the message, **Keep a copy of the data**: the backup
  card of **Settings › Administration › Backup**, to back up the whole instance, follow the backup,
  download the archive before the instance is gone, and delete it from the server. The other users
  do not see it: their text tells them to ask their administrator for a backup;
- **Logout** signs out.

The card makes, by default, the same archive as your [hosting panel](hosting_panel_backups.md#panel-backups): it leaves out
the logs and the instance key, and the card says so. An administrator may choose a secure backup
instead, encrypted with a password of their own: it carries the instance key only when LibreFolio
generated it (`secrets/instance.key`), never a key you configured
([Secure Backups](backup_restore.md#secure)). Keep your copy of the instance's key, its
`secrets/instance.key` or the key you configured, with the data: without it, what LibreFolio
encrypted can no longer be read. See «The Instance Key» in [Environment Variables](configuration.md).

A user still signed in after the restart gets the page as soon as the app asks the server for data.
Once you lift the block and restart, users get the app back at their next page load.

### ✅ What Still Answers {: #what-still-answers }

On a blocked instance, only these API calls answer as usual:

| For | Endpoints |
| --- | --- |
| Signing in and out, and who is signed in | `POST /api/v1/auth/login`, `POST /api/v1/auth/logout`, `GET /api/v1/auth/me` |
| Following a link already sent: checking it, and setting a new password with a reset link | `POST /api/v1/auth/tokens/inspect`, `POST /api/v1/auth/password-reset` |
| Deleting one's own account, and seeing first what it would delete | `DELETE /api/v1/auth/users/me`, `GET /api/v1/auth/users/me/deletion-preview`: the block page has no button for it yet |
| Taking the data away: a backup of the whole instance, by an administrator or by your hosting panel | For an administrator, `POST /api/v1/backup/instance`, then `GET`, `GET …/file` and `DELETE` on `/api/v1/backup/instance/jobs/{job_id}`, and `GET /api/v1/backup/instance/options`, the rules of a secure backup's password, so that the card can offer a secure backup too: the backup card of the block page calls them ([What Users See](#what-users-see)). For your panel, its [four routes](hosting_panel_backups.md#panel-jobs), with its token |
| The outcome of a restore, for the page that asked the restart, with the one-time ticket of that request: when the block took effect at that restart, it says that the restore waits for the unblock, and starts nothing | `GET /api/v1/backup/restore/outcome` |
| The block page | `GET /api/v1/system/block` (signed-in users only), `GET /api/v1/system/instance` |
| Probes and version | `GET /api/v1/system/health`, `GET /api/v1/system/ready`, `GET /api/v1/system/info` |
| The [scheduled wake-up](wake_sync.md#wake-sync), with its own token: it answers `blocked` and runs no job | `POST /api/v1/system/wake-sync` |
| Your panel's [setup status](hosting_panel_api.md#panel-status), with its own token | `GET /api/v1/panel/status` |

- Your monitoring keeps working: `/system/health` and `/system/ready` answer as on any other
  instance.
- Your panel's [restore routes](hosting_panel_backups.md#panel-restore) pass the block too, so that a call without a valid
  ticket learns nothing about it; a call with a valid ticket gets `423` with the code
  `instance_blocked`, and no restore: the block lets the data leave, never come in.
- The web app itself is still served: the block covers the API, not the pages of the app.

The list is short on purpose, and it is fixed in the code: there is no setting to change it.

### 🚫 Every Other Call {: #refused-calls }

Every other API call is refused:

- a **signed-in user** gets `423 Locked`, and the web app shows the block page on the first one:

    ```json
    {"detail": {"code": "instance_blocked", "message": "This instance is blocked by its hosting provider"}}
    ```

- a caller **without a valid session** gets `401`.

For a caller without a session, most of the API answers as on any other instance:

- the calls that always need a sign-in answer the same `401` whether or not the instance is blocked;
- the calls of the list above answer as usual: `/system/instance`, `/system/info` and
  `/system/ready` do not reveal the block.

A few calls are normally open to anyone: registration (`POST /api/v1/auth/register`), the setup of
the [initial administrator](#initial-admin) (`POST /api/v1/auth/setup`), the address probe
(`GET /api/v1/auth/address-probe` and its image, `GET /api/v1/auth/address-probe.png`), the reference lists (`GET /api/v1/utilities/*`) and the AI
Export catalogue (`GET /api/v1/ai-export/catalog`). On a blocked instance they answer `401` too. The
setup page and the invitation page then say that the instance is blocked, instead of sending their
visitor to the sign-in page, which would lose the link. The address probe
then cannot confirm a public address, and the check of your instance's address reports it as not
verifiable. From them, a caller without a session can tell that the instance is blocked, and nothing
more: they return no data.

### 📅 The Deletion Date {: #deletion-date }

`LIBREFOLIO_DELETION_DATE` is information for your users: LibreFolio shows it on the block page and
does nothing on that day. Deleting the instance and its data is up to you. The date is checked at
every start, blocked or not, but users see it only on the block page.

---

## 🔗 Related

- 📄 **[Hosting for Others](hosting_providers.md)** — The Managed Profile, Your Legal Pages
- 📄 **[Hosting for Others: the Panel API](hosting_panel_api.md)** — Hosting Panel API
- 📄 **[Hosting for Others: Backups and Restores](hosting_panel_backups.md)** — Backups for Your Hosting Panel, Restoring an Instance from Your Panel, The Upload Limit of a Restore
