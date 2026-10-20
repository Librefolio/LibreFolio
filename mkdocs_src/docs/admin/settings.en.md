# ⚙️ Global Settings

Global settings apply to the whole instance and to every user. They are stored in the database, and
only administrators have their tab, to see and change them. They are not secret, though: the app
reads them for every signed-in user, to apply them (the upload limit, the defaults of the
[Preferences](../user/settings/preferences.md)…), and any signed-in user can read them through the
API.

---

## 🗂️ Settings › Administration {: #administration }

**Global Settings** is the first tab of **Administration**, the group of tabs that look after the
instance, at the right end of the **Settings** tab bar on a wide screen. Only administrators have
the group. Click **Administration**: it opens **Global Settings** and a second row of tabs under the
first one, with the tabs of the group.

| Tab | Who has it | What it is for |
|---|---|---|
| ⚙️ **Global Settings** | Administrators | The settings of this page |
| 👥 **Users** | Administrators | The accounts, invitations and password-reset links: [Users & Invitations](users.md) |
| 💾 **Backup** | Administrators | The whole instance in one archive, and its restore: [Backup, Restore & Moving](backup_restore.md) |
| ✉️ **Email** | Administrators | Whether LibreFolio can send emails, and a test email: [Email](email.md) |
| 🛡️ **Security** | Administrators | How the instance is configured, and what needs your attention: [Security](#security-tab), below |

- 👤 A user who is not an administrator has no **Administration** group, nor any of its tabs: their
  **Settings** end with **About**, and a link to one of the group's tabs opens their **Profile**
  instead.
- 🔁 Clicking **Administration** while one of its tabs is open keeps that tab open.
- 🔢 A number on **Security**, repeated on **Administration**, counts the errors and warnings of the
  [security checks](#security-tab).
- 📱 On a phone, the tabs show their icons only, and the title of the page names the open tab.

---

## ✏️ Change a Setting

### 🔓 1. Unlock the tab

Open **Settings** (gear icon in the sidebar), then **Administration**, which opens on
**Global Settings**: its panel groups the settings by category. Click the **lock icon** (🔒) in the
header to unlock it. Only administrators (superusers) have this tab.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="settings" data-name="global-settings" alt="Global Settings" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

### 💾 2. Edit and save

- Nothing is written until you click **Save** next to a setting, or **Save All** in the header.
  **Undo** and **Undo All** bring back the saved values.
- **Reset to Default** and **Reset All to Defaults** fill in the default values, ready to save.
- Saved values apply right away, without a restart.

??? note "🔒 Locking with unsaved changes — when a dialog asks first"

    Clicking the lock with unsaved changes asks whether to discard them. **Cancel** keeps your
    edits; **Discard** puts back the saved values and locks the tab.

??? tip "💻 Missing settings — recreate them from the command line"

    Every server start recreates any missing setting with its default value. To do it without a
    restart, run the [command-line tool](cli_tools.md):

    ```bash
    pipenv run ./dev.py user init-settings
    ```

    The values you changed are kept.

---

## 📋 What Each Setting Does

| Category | Setting | Default | What it does — when to change it |
|---|---|---|---|
| ⏳ Session | **Session Duration** | 24 hours | How long users stay signed in. Shorten it on shared devices; a new value applies from each user's next login. |
| 🛡️ Security | **Registration** | By invitation | Who can create an account: **Open**, **By invitation** or **Closed** (see [Who Can Sign Up](#registration)). An instance upgraded from an earlier version keeps the mode it had. **Open** lets in anyone who reaches the login page: avoid it if the instance is reachable from the internet. Administrators who open the app at an address outside the local network are [warned](#open-registration-warning) while it is **Open**. |
| 🛡️ Security | **Require Email Verification** | Off | New accounts must open a link emailed to their address before they can sign in; the first account never waits, and existing accounts are not affected. It turns on only while email works and `LIBREFOLIO_PUBLIC_URL` can be used: until then the switch is greyed out. See *Email Verification* in [Email](email.md). |
| 🔄 Update Job | **Scheduler Enabled** | On | Turns the automatic price and exchange-rate updates on or off: see [Market Data Scheduler](#market-data-scheduler). |
| 🧠 Memory | **Max File Upload Size** | 10 MB | The largest file users can upload, broker reports included. Raise it if a large export is refused. |
| 🌍 Defaults | **Default Currency** | `EUR` | The currency new users report in. |
| 🌍 Defaults | **Default Language** | `en` | 🇬🇧 `en`, 🇮🇹 `it`, 🇫🇷 `fr` or 🇪🇸 `es`. |
| 🌍 Defaults | **Default Theme** | `auto` | ☀️ `light`, 🌙 `dark`, or 🖥️ `auto`, which follows the device. |

New users start from the three defaults: the [Welcome setup](../user/getting-started.md#welcome-setup)
shows their language and currency pre-filled. Changing a default later leaves the
[Preferences](../user/settings/preferences.md) of existing users untouched.

---

## 🚪 Who Can Sign Up {: #registration }

The **Registration** setting decides who can create an account:

| Mode | Who can create an account |
|---|---|
| 🌐 **Open** | Anyone who reaches the login page, with **Register here**. |
| ✉️ **By invitation** (default) | Only people with an invitation link. You create one link per person from the [Users](users.md#invitations) tab, or from the [command line](cli_tools.md#invite), and send it to them. The login page shows no **Register here**. |
| 🔒 **Closed** | Nobody, not even with an invitation link. The login page shows no **Register here**. |

- 👑 The first account of a new instance can always be created, whatever the mode: until it
  exists, the login page shows **Register here**, and the account it creates becomes the
  administrator. With `LIBREFOLIO_ADMIN_EMAIL`, LibreFolio creates that administrator itself at its
  first start, and nobody can register in its place: see
  [The Initial Administrator](configuration.md#initial-admin).
- 🆕 A new instance starts **By invitation**. An instance upgraded from an earlier version keeps
  the mode it had: one that was **Open**, the earlier default, stays **Open** until you change it
  (**Reset to Default** proposes **By invitation**). Once everyone has an account, choose
  **By invitation** or **Closed**.
- ✉️ An invitation link works once, for 7 days, and can make the new account an administrator. With
  **Open**, nobody needs one, but a link still gives its role.
- 💻 Whatever the mode, the [command line](cli_tools.md) can still create accounts with
  `user create`.
- 📏 With a user limit, nobody can sign up without an invitation once the instance is full: see
  [When the Instance Is Full](configuration.md#user-limit).
- 🔒 If the server's configuration sets `LIBREFOLIO_REGISTRATION`, that value decides: the field
  shows it, cannot be changed, and says *Set on the server by LIBREFOLIO_REGISTRATION: change it
  there*. **Reset All to Defaults** leaves it alone. See [Accounts and Sign-ups](configuration.md#accounts).
- ⬆️ This setting replaces the **Enable Registration** switch of earlier versions, and the upgrade
  keeps your choice: a switch that was on becomes **Open**, a switch that was off becomes **Closed**.

!!! warning "🆕 A new instance: create your account first"

    Until the first account exists, anyone who reaches the login page can create it with
    **Register here**, whatever the mode, `LIBREFOLIO_REGISTRATION` included, and that account
    becomes the administrator. Register as soon as the server is up, before you make it reachable
    from the internet. From the second account on, the mode applies: with **By invitation**, the
    default, the login page no longer shows **Register here**.

    You can also create the first administrator from the [command line](cli_tools.md), without the
    browser:

    ```bash
    pipenv run ./dev.py user create <username> <email> <password>
    ```

    With Docker: `docker compose exec librefolio python dev.py user create <username> <email> <password>`.

    Or give LibreFolio `LIBREFOLIO_ADMIN_EMAIL` before its first start: it then creates the
    administrator itself, with a setup link for you, and nobody can register in its place
    ([The Initial Administrator](configuration.md#initial-admin)).

### 📢 The Open-Registration Warning {: #open-registration-warning }

While **Registration** is **Open**, an administrator who opens LibreFolio at an address outside the
local network gets a warning above the pages of the app:

*Registration is open and this instance is reachable from outside your local network: anyone who
finds it can create an account.*

Its link, **Change who can sign up**, opens **Settings › Administration › Global Settings**, where
this setting is. When `LIBREFOLIO_REGISTRATION` sets the mode on the server, the warning names that
variable instead, and has no link: only the server's configuration can change the mode
([Accounts and Sign-ups](configuration.md#accounts)).

- 👑 Only administrators see it.
- 🌐 Your browser decides, from the name or IP address in its address bar (the port does not
  matter). Nothing is sent to the server, and nothing tests whether the instance can really be
  reached from the internet. These addresses count as local, and get no warning:
    - `localhost`, and every name ending in `.localhost`;
    - a name without a dot, such as `nas`, and every name ending in `.local`, `.lan`, `.home.arpa`
      or `.internal`;
    - the IPv4 addresses of `127.0.0.0/8`, `10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16` and
      `100.64.0.0/10` (carrier-grade NAT, the range where Tailscale numbers its devices);
    - the IPv6 address `::1`, and those of `fc00::/7` and `fe80::/10`; an IPv4 address written as
      IPv6, such as `::ffff:192.168.1.10`, counts as the IPv4 address it carries.

    Capitals and a final dot change nothing. Every other address counts as outside, the Tailscale
    names ending in `.ts.net` included: Tailscale Funnel can publish them on the internet.
- ✖️ Its close button hides it until the page is loaded again.
- 🔄 It goes away as soon as the mode is no longer **Open**: saving **Registration** here updates it
  at once.
- 🛡️ The [Security](#security-tab) tab lists the same warning among its findings, as long as it
  holds, even after you close it above the pages.

How it decides, for developers:
[The Open-Registration Warning](../developer/architecture/security.md#open-registration-warning).

---

## 🕐 Market Data Scheduler {: #market-data-scheduler }

The scheduler keeps prices and exchange rates up to date on its own, even when nobody is signed in:

- 💰 **Current price refresh** — every few minutes, the latest price of each active asset that has
  a price provider.
- 📊 **History sync** — on the days and times you choose, the daily prices of those assets and the
  rates of every FX pair with a provider, over at least the **Lookback horizon**, to fill any gap.
  For an asset or a pair whose last saved price or rate is older, it goes back to that day, up to a
  year; an asset with no saved price yet gets the horizon only, as the scheduler never downloads a
  whole history. Pairs with manual rates only are skipped.

If the server is off or asleep at a sync time, the history sync it missed runs as soon as the server
is back, instead of waiting for the next sync time: a server off for weeks fills its whole gap.

### ⚙️ Configure the schedule

Unlock the tab, open **Update Job** and click **Configure…** in the **Schedule Configuration** row.
The dialog has its own **Save** button.

<div class="screenshot-container" style="max-width: 600px; margin: 1rem auto;">
 <img class="gallery-img" data-category="settings" data-name="scheduler-config" alt="Scheduler Configuration Modal" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

| Field | Default | What it sets |
|---|---|---|
| **Timezone** | `UTC` | The timezone of the times and days below; the server's UTC clock is shown next to it. |
| **Refresh every** | 10 minutes | How often current prices are refreshed, from 1 to 1440 minutes. |
| **Sync times** | `06:00`, `23:00` | When the history sync runs; **Add time** adds a slot. |
| **Sync days** | Mon to Sat | The days of the history sync. |
| **Lookback horizon** | 14 days | How many past days each history sync checks at least, from 1 to 365. It goes further back, up to a year, when the last saved price or rate of an asset or a pair is older. |

Keep at least one time and one day. Tip: a history sync after the markets close (for example
`22:00`) gets the most complete data.

??? warning "🌍 Changing the timezone — the jobs move in time"

    Times and days keep their values but count in the new timezone, so the jobs run at another
    moment. They also follow its daylight saving time: `06:00` in `Europe/Rome` runs at 05:00 UTC
    in winter and at 04:00 UTC in summer.

### 📜 Read the scheduler log

The **Scheduler Status** row shows the last current price refresh, with a dot for its result.
While a retry is pending, an extra line gives its time: **Failed: next attempt at …** after a
refresh that could not finish, otherwise **Paused items retried at …** for the prices deferred
because their provider paused.
Click the row (or **Details…**) to open the **Scheduler Execution Log**. Only administrators can
read the status and the log.

<div class="screenshot-container" style="max-width: 600px; margin: 1rem auto;">
 <img class="gallery-img" data-category="settings" data-name="scheduler-log" alt="Scheduler Log Modal" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

- Each entry is one run: job, time, duration and how many items succeeded. 🟢 **OK**: all of
  them, or nothing to do; 🟡 **Partial**: some failed, or were deferred because their provider paused after too
  many requests; 🔴 **Error**: none succeeded and none was deferred.
- Click an entry to see each asset or FX pair, its provider and the prices changed (**Delta**).
  Hover an error to read it in full; double-click it (long-press on a phone) to copy it.
- A deferred item shows a pause icon and **Deferred: provider paused**: hover the label to read the
  provider's message. The entry counts deferred items with ⏸, next to ✓ and ✗ (for example
  `3/5 ✓ · 1 ⏸ · 1 ✗`), and **Retry at** in its header gives the time set for retrying them.
- Filter by job, status or period, from the last hour to the last 30 days. Only the most recent
  runs are kept.

---

## 🗄️ Server Caches {: #server-caches }

To stay fast, LibreFolio keeps recent provider answers and computed results in memory. The
**Cache Status** panel, at the end of the **Memory** category, lists each cache with its
**Size / Max** and its **TTL** (how long an entry is kept). Click a column header to sort;
**Refresh** updates the numbers.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="settings" data-name="cache-panel" alt="Server caches panel in Global Settings (Memory category)">
</div>

The panel shows its numbers whether the tab is locked or not. With the tab unlocked, you can empty
one cache with **Clear** or all of them with **Clear all**, to force fresh data without a restart.
A restart empties every cache too.

!!! warning "Clearing a cache slows down the next fetch"

    Both actions ask for confirmation first. After a clear, the next request for that data goes
    back to the providers, so expect a slowdown similar to a server restart while the caches fill
    up again.

??? note "🧵 Several workers — when the server runs with `--workers`"

    Each worker process has its own caches. The panel shows, and clears, those of the worker that
    answered; restart the server to empty them all.

---

## 🛡️ Security {: #security-tab }

**Settings › Administration › Security** checks how this instance is configured, and lists first
what needs your attention. Only administrators have this tab. It is not the 🛡️ **Security** category
of Global Settings, which holds **Registration** and **Require Email Verification**.

### 🚦 What It Lists {: #security-findings }

Each finding says what is wrong, with its icon and its colour: ❌ an **error**, ⚠️ a **warning** or
ℹ️ an **information**. Errors come first, then warnings, then information; within each severity, the
findings keep the order of this table.

| Check | A finding when | Its link |
|---|---|---|
| Session signing key | ℹ️ No key is set: every restart signs every user out. ⚠️ The key is shorter than 32 characters. ❌ Its `JWT_SECRET_FILE` cannot be read | — |
| Secrets set twice | ⚠️ A secret is set both directly and through its `_FILE` variable: the direct value wins | — |
| Instance key | ❌ It cannot be used. ⚠️ Its folder or its file is open to other users | — |
| Session cookie | ⚠️ `SESSION_COOKIE_SECURE=never`: the cookie also travels over plain HTTP | — |
| Visitor's address | ⚠️ Since the start, requests came through a reverse proxy that LibreFolio does not trust: the limits per visitor's address do not apply to them. ℹ️ Since the start, forwarding headers from a public address were ignored. What to do: [The Visitor's Address](connection_checks.md#client-address) | — |
| Frame protection | ⚠️ `LIBREFOLIO_FRAME_PROTECTION` is off in the `managed` profile: any site can show LibreFolio in a frame | — |
| Report-only policy | ℹ️ `LIBREFOLIO_CSP_REPORT_ONLY` is off in the `managed` profile: browsers list nothing it would block | — |
| Log level | ℹ️ `DEBUG` or `TRACE` | — |
| Test mode | ❌ `LIBREFOLIO_TEST_MODE` is on outside LibreFolio's own test runs: data providers that exist only for the tests are served, and the data are kept in the test data folder | — |
| Hosting panel's backup token | ❌ `LIBREFOLIO_BACKUP_DOWNLOAD_TOKEN` is too short (at least 32 random characters), holds characters a request header cannot carry as written (spaces, tabs or characters outside visible ASCII), or cannot be read from its file: the panel's backup routes answer `503` until it is fixed. Passed when no token is set, the panel's backup routes off, or when the token can be used | — |
| Upload limit of a restore | ❌ `LIBREFOLIO_BACKUP_MAX_UPLOAD_MB` cannot be used (a whole number of megabytes, `0` for no limit), or LibreFolio's own profile defaults give the upload limit no value, or one of the wrong type: restore uploads are refused until it is fixed. Passed with a limit, such as *A restore accepts archives of up to 500 MB.*, or with none | — |
| Unpacked size of a restore | ❌ `LIBREFOLIO_BACKUP_MAX_RESTORE_MB` cannot be used (a whole number of megabytes, `0` for no limit), or, while it is unset in the managed profile, the `LIBREFOLIO_BACKUP_MAX_UPLOAD_MB` it follows, which the finding then names; or LibreFolio's own profile defaults give the upload limit no value, or one of the wrong type: restore checks are refused until it is fixed. Passed with a limit, such as *A restore check accepts archives that unpack to up to 4000 MB.*, or with none | — |
| Failed sign-ins | ⚠️ The limit is off: `LIBREFOLIO_LOGIN_LIMIT=off` | — |
| Email server | ❌ A `LIBREFOLIO_SMTP_*` value cannot be used: email stays off until it is fixed | **Open the Email tab** |
| Email encryption | ⚠️ Emails, their links and the SMTP password travel unencrypted to a server outside your local network | **Open the Email tab** |
| Links in emails | ℹ️ Email works, but `LIBREFOLIO_PUBLIC_URL` is not set. ⚠️ `LIBREFOLIO_PUBLIC_URL` cannot start a link | **Open the Email tab** |
| Plugin secrets | ❌ Instance-wide plugin secrets cannot be read with the instance key | **Open the plugin settings**, to **Settings › Plugins** |
| Open registration, checked by your browser | ⚠️ **Registration** is **Open**, and you reached LibreFolio at an address outside your local network, as for [the warning above the pages](#open-registration-warning) | **Change who can sign up**, to **Global Settings**. None when `LIBREFOLIO_REGISTRATION` sets the mode: the finding names that variable instead |

The findings without a link are fixed on the server, in its configuration, and need a restart: what
to do for each one is in the table of «Startup Checks» in [Configuration](configuration.md), where
the server's log words the same checks.

### 🔢 The Number on the Tab {: #security-badge }

**Security** shows how many errors and warnings it lists, and **Administration** shows the same
number, so you see it from every tab of Settings. Information is listed but never counted: with
information only, there is no number, and the tab does not say *Nothing needs your attention.*
either.

Outside Settings, the same count follows you on every page, as a dot on the connection line at the
bottom of the sidebar: red with at least one error, amber with warnings only, none with information
only. Click the line: after its reason, its details link to this tab with the count, such as
**2 security warnings**, errors included. On a phone, the menu button carries the dot too. What it
looks like: [Security Warnings for Administrators](../user/connection-security.md#security-warnings).

### 🔄 When It Checks {: #security-refresh }

LibreFolio reads the checks once, as soon as it opens in your browser, whatever the page: the
sidebar's connection line asks for them, so its dot, and the number on the tab, are already there
when you open **Settings**. If that read fails, opening **Settings** tries again. LibreFolio keeps
the checks while you use the app: after you change the server's configuration and restart it, click
**Check again**, at the top of the tab, or reload the page. The open-registration finding follows
**Registration** at once: saving it in Global Settings updates the list, the number and the dot.

- ⏳ Until the first answer, the tab shows placeholder rows.
- ⚠️ When the checks cannot be read, the tab says *The security checks could not be loaded.*, with
  **Try again**. After a **Check again** that fails, the last results stay listed under it.

### ✅ Passed Checks {: #security-passed }

With no finding, the tab says *Nothing needs your attention.* Below the findings, a folded section,
**N checks passed**, lists the checks that passed, each with its own sentence (such as *Sessions are
signed with a key set by the administrator.*): click it to unfold it. Email that is off, or sent
unencrypted to a server of your own network, counts as passed, and says so there.

---

## 🔗 Related

- 📝 **[Environment Variables](configuration.md)** — The settings that live in `.env` instead
- 👥 **[Users & Invitations](users.md)** — The accounts of the instance, invitations and password-reset links
- 👤 **[User Preferences](../user/settings/preferences.md)** — What each user can change for themselves
- 🧑‍💻 For developers: **[Settings System](../developer/architecture/settings.md)**,
  **[Cache Registry](../developer/architecture/settings_cache.md)**,
  **[Market Data Scheduler](../developer/backend/scheduler.md)** and
  **[Configuration Checks](../developer/architecture/security.md#configuration-checks)**
