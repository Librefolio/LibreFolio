# ⚙️ Global Settings

Global settings apply to the whole instance and to every user. They live in the database.
Only administrators have the tab to see and change them. They are not secret: the app reads them for every signed-in user (the upload limit, the defaults of the [Preferences](../user/settings/preferences.md)…) and any signed-in user can read them through the API.

Some have a variable in the `.env` file that fixes them or comes first: the **Where** column of each table says so.

---

## 🗂️ Settings › Administration {: #administration }

**Where:** **Settings** (gear icon in the sidebar) › **Administration**, at the right end of the tab bar on a wide screen. Only administrators have the group.
Click **Administration**: it opens **Global Settings** and a second row of tabs under the first one.

| Tab | What it is for |
|---|---|
| ⚙️ **Global Settings** | The settings of this page |
| 👥 **Users** | The accounts, the invitations and the password-reset links: [Users & Invitations](users.md) |
| 💾 **Backup** | The whole instance in one archive, and its restore: [Backup, Restore & Moving](backup_restore.md); to make one from the app, start from the [quick start](backup_restore.md#quick-start) |
| ✉️ **Email** | Whether LibreFolio can send emails, and a test email: [Email](email.md) |
| 🛡️ **Security** | How the instance is configured and what needs your attention: [Security](#security-tab), below |

- 👤 A user who is not an administrator has neither the group nor its tabs: their **Settings** end with **About**, and a link to a tab of the group opens their **Profile**.
- 🔁 Click **Administration** while one of its tabs is open: that tab stays open.
- 🔗 Each tab has its own address, for a bookmark or a link: `/settings/admin/global`, `/settings/admin/users`, `/settings/admin/backup`, `/settings/admin/email`, `/settings/admin/security`; `/settings/admin` opens the group's first tab. The address follows the open tab, and **Back** returns to the previous one.
- 🔢 A number on **Security**, repeated on **Administration**, counts the errors and warnings of the [security checks](#security-tab).
- 📱 On a phone, the tabs show their icons only; the title of the page names the open tab.

---

## ✏️ Change a Setting

### 🔓 1. Unlock the tab

**Where:** **Settings › Administration › Global Settings**. The panel groups the settings by category.
Click the **lock icon** (🔒) in the header.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="settings" data-name="global-settings" alt="Global Settings" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

### 💾 2. Edit and save

- Nothing is written until you click **Save** next to a setting or **Save All** in the header. **Undo** and **Undo All** bring back the saved values.
- **Reset to Default** and **Reset All to Defaults** fill in the defaults, ready to save.
- Saved values apply right away, without a restart.

??? note "🔒 Locking with unsaved changes — when a dialog asks first"

    Click the lock with unsaved changes: it asks whether to discard them. **Cancel** keeps your edits; **Discard** brings back the saved values and locks the tab.

??? tip "💻 Missing settings — recreate them from the command line"

    Every server start recreates the missing settings with their default value. To do it without a restart, **in the server's terminal**, with the [command-line tool](cli_tools.md):

    ```bash
    pipenv run ./dev.py user init-settings
    ```

    The values you changed are kept.

---

## 📋 What Each Setting Does

**Where:** the named category of the **Global Settings** tab.

| Where | Setting | Default | What it does — when to change it |
|---|---|---|---|
| ⏳ Session | **Session Duration** | 24 hours | How long users stay signed in. Shorten it on shared devices. A new value applies from each user's next login. |
| 🛡️ Security | **Registration** | By invitation | Who can create an account: **Open**, **By invitation** or **Closed**. **Open** lets in anyone who reaches the login page: avoid it if the instance is reachable from the internet. Modes, warning and `LIBREFOLIO_REGISTRATION`: [Who Can Sign Up](#registration). |
| 🛡️ Security | **Require Email Verification** | Off | New accounts must open a link sent to their address before they can sign in; the first account never waits and existing accounts are not affected. It turns on only while email works and `LIBREFOLIO_PUBLIC_URL` can be used: until then the switch is disabled. See *Email Verification* in [Email](email.md). |
| 🔄 Update Job | **Scheduler Enabled** | On | Turns the automatic price and exchange-rate updates on or off: [Market Data Scheduler](#market-data-scheduler). |
| 🧠 Memory | **Max File Upload Size** | 10 MB | The largest file users can upload, broker reports included. Raise it if a large export is refused. |
| 🧠 Memory | **LibreFolio total space (MB)** | `0`, no limit | The most megabytes the instance may take: it is the line the space bar of **Files** is drawn against. `0` means no limit: the bar then shows the disk. The same field is under that bar, in **Advanced**. `LIBREFOLIO_STORAGE_LIMIT_MB`, when set, wins and locks it: the field is read-only and says that whoever hosts the instance sets it ([Environment Variables](configuration.md)). **Open the settings**, on a refusal of the limit, opens this tab with the row highlighted; the tab stays locked. See [The Space Bar](backup_restore.md#space-used). |
| 🌍 Defaults | **Default Currency** | `EUR` | The currency new users report in. Before the first save, `LIBREFOLIO_DEFAULT_CURRENCY` decides (below). |
| 🌍 Defaults | **Default Language** | `en` | 🇬🇧 `en`, 🇮🇹 `it`, 🇫🇷 `fr` or 🇪🇸 `es`. It is also the language of the emails sent to people who have no account yet. Before the first save, `LIBREFOLIO_DEFAULT_LANGUAGE` decides (below). |
| 🌍 Defaults | **Default Theme** | `auto` | ☀️ `light`, 🌙 `dark` or 🖥️ `auto`, which follows the device. Applies to every user who has not chosen a theme of their own, not only to new users; a change reaches them at their next sign-in. |
| 🌍 Defaults | **Default Chart Line Shape** | `segments` | `segments`, `steps` or `spline` (smooth curve). Applies to every user who has not chosen a line shape of their own; a change reaches them at their next page load. |

**In the `.env` file**, two variables decide, if set, only until you save the setting for the first time: from the first save, your value wins, even when it is the default again (`EUR`, `en`). See [Environment Variables](configuration_accounts.md#accounts).

```env
LIBREFOLIO_DEFAULT_CURRENCY=EUR
LIBREFOLIO_DEFAULT_LANGUAGE=en
```

New users start from the three defaults: the [Welcome setup](../user/getting-started.md#welcome-setup) shows language and currency already pre-filled. Changing a default later does not touch the [Preferences](../user/settings/preferences.md) of existing users.

---

## 🚪 Who Can Sign Up {: #registration }

**Where:** **Global Settings › Security › Registration**, or the [Users](users.md#registration) tab, next to **Invite**: there the mode is saved at once, asking first only for **Open**.

| Mode | Who can create an account |
|---|---|
| 🌐 **Open** | Anyone who reaches the login page, with **Register here**. |
| ✉️ **By invitation** (default) | Only people with an invitation link. Create one link per person from the [Users](users.md#invitations) tab or from the [command line](cli_tools.md#invite), and send it. The login page shows no **Register here**. |
| 🔒 **Closed** | Nobody, not even with an invitation link. The login page shows no **Register here**. |

- 👑 The first account of a new instance can always be created, whatever the mode: see the warning below.
- 🆕 A new instance starts **By invitation**. An instance upgraded from an earlier version keeps the mode it had: one that was **Open**, the earlier default, stays **Open** until you change it (**Reset to Default** proposes **By invitation**). Once everyone has an account, choose **By invitation** or **Closed**.
- ✉️ An invitation link works once, for 7 days, and can make the new account an administrator. With **Open**, nobody needs one, but a link still gives its role.
- 💻 Whatever the mode, the [command line](cli_tools.md) can create accounts with `user create`.
- 📏 With a user limit, nobody can sign up without an invitation once the instance is full: [When the Instance Is Full](configuration_accounts.md#user-limit).
- 🔒 **In the `.env` file**, `LIBREFOLIO_REGISTRATION` fixes the mode: the field shows it in both places, cannot be changed and says *Set on the server by LIBREFOLIO_REGISTRATION: change it there*. **Reset All to Defaults** leaves it alone. See [Accounts and Sign-ups](configuration_accounts.md#accounts).
- ⬆️ This setting replaces the **Enable Registration** switch of earlier versions; the upgrade keeps your choice: a switch that was on becomes **Open**, one that was off **Closed**.

!!! warning "🆕 A new instance: create your account first"

    Until the first account exists, anyone who reaches the login page can create it with **Register here**, whatever the mode, `LIBREFOLIO_REGISTRATION` included, and that account becomes the administrator. Register as soon as the server is up, before you make it reachable from the internet. From the second account on, the mode applies: with **By invitation**, the default, the login page no longer shows **Register here**.

    Or create the first administrator **in the server's terminal**, without a browser ([command line](cli_tools.md)):

    ```bash
    pipenv run ./dev.py user create <username> <email> <password>
    ```

    With Docker: `docker compose exec librefolio python dev.py user create <username> <email> <password>`.

    Or set `LIBREFOLIO_ADMIN_EMAIL` **in the `.env` file** before the first start: LibreFolio creates the administrator itself, with a setup link for you, and nobody can register in its place ([The Initial Administrator](configuration_accounts.md#initial-admin)).

### 📢 The Open-Registration Warning {: #open-registration-warning }

While **Registration** is **Open**, an administrator who opens LibreFolio at an address outside the local network reads, above the pages of the app:

*Registration is open and this instance is reachable from outside your local network: anyone who finds it can create an account.*

Its link, **Change who can sign up**, opens **Settings › Administration › Global Settings**. When `LIBREFOLIO_REGISTRATION` fixes the mode, the warning names that variable instead and has no link: only the server's configuration (`.env` file) can change it ([Accounts and Sign-ups](configuration_accounts.md#accounts)).

- 👑 Only administrators see it.
- 🌐 Your browser decides, from the name or IP address in the address bar (the port does not matter). Nothing is sent to the server and nothing tests whether the instance is really reachable from the internet. These count as local, with no warning:
    - `localhost` and every name ending in `.localhost`;
    - a name without a dot, such as `nas`, and every name ending in `.local`, `.lan`, `.home.arpa` or `.internal`;
    - the IPv4 addresses of `127.0.0.0/8`, `10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16` and `100.64.0.0/10` (carrier-grade NAT, the range where Tailscale numbers its devices);
    - the IPv6 address `::1` and those of `fc00::/7` and `fe80::/10`; an IPv4 address written as IPv6, such as `::ffff:192.168.1.10`, counts as the IPv4 address it carries.

    Capitals and a final dot change nothing. Every other address counts as outside, the Tailscale names ending in `.ts.net` included: Tailscale Funnel can publish them on the internet.
- ✖️ The close button hides it until the page is loaded again.
- 🔄 It goes away as soon as the mode is no longer **Open**: saving **Registration** updates it at once.
- 🛡️ The [Security](#security-tab) tab lists the same warning among its findings as long as it holds, even after you have closed it.

How it decides, for developers: [The Open-Registration Warning](../developer/architecture/security.md#open-registration-warning).

---

## 🕐 Market Data Scheduler {: #market-data-scheduler }

The scheduler updates prices and exchange rates on its own, even when nobody is signed in:

- 💰 **Current price refresh** — every few minutes, the latest price of each active asset with a price provider.
- 📊 **History sync** — on the days and at the times you choose, the daily prices of those assets and the rates of every FX pair with a provider, over at least the **Lookback horizon**, to fill the gaps. If the last saved price or rate is older, it goes back to that day, up to a year at most; an asset with no saved price at all gets the horizon only: the scheduler never downloads a whole history. Pairs with manual rates only are skipped.

Server off or asleep at the sync time: the missed sync runs as soon as the server is back, without waiting for the next time. A server off for weeks fills its whole gap.

### ⚙️ Configure the schedule

**Where:** **Global Settings › Update Job › Schedule Configuration › Configure…**, with the tab unlocked. The dialog has its own **Save** button.

<div class="screenshot-container" style="max-width: 600px; margin: 1rem auto;">
 <img class="gallery-img" data-category="settings" data-name="scheduler-config" alt="Scheduler Configuration Modal" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

| Field | Default | What it sets |
|---|---|---|
| **Timezone** | `UTC` | The timezone of the times and days below; next to it, the server's UTC clock. Before the first save of the schedule, `LIBREFOLIO_DEFAULT_TIMEZONE` **in the `.env` file** decides, if set; from the first save, your value wins, even when it is `UTC` again ([Environment Variables](configuration_accounts.md#accounts)). |
| **Refresh every** | 10 minutes | How often current prices are refreshed, from 1 to 1440 minutes. |
| **Sync times** | `06:00`, `23:00` | When the history sync runs; **Add time** adds a slot. |
| **Sync days** | Mon to Sat | The days of the history sync. |
| **Lookback horizon** | 14 days | How many past days each sync checks at least, from 1 to 365. It goes further back, up to a year, when the last saved price or rate is older. |

Keep at least one time and one day. A sync after the markets close (for example `22:00`) gets the most complete data.

??? warning "🌍 Changing the timezone — the jobs move in time"

    Times and days keep their values but count in the new timezone: the jobs run at another moment. They also follow the timezone's daylight saving time: `06:00` in `Europe/Rome` runs at 05:00 UTC in winter and at 04:00 UTC in summer.

### 📜 Read the scheduler log

**Where:** **Global Settings › Update Job › Scheduler Status**. Only administrators read the status and the log.

The row shows the last current price refresh, with a dot for its result. While a retry is pending, an extra line gives its time: **Failed: next attempt at …** after a refresh that could not finish, otherwise **Paused items retried at …** for the prices deferred because their provider was paused.
Click the row (or **Details…**): the **Scheduler Execution Log** opens.

<div class="screenshot-container" style="max-width: 600px; margin: 1rem auto;">
 <img class="gallery-img" data-category="settings" data-name="scheduler-log" alt="Scheduler Log Modal" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

- Each entry is one run: job, time, duration and how many items succeeded. 🟢 **OK**: all of them, or nothing to do; 🟡 **Partial**: some failed, or were deferred because their provider paused after too many requests; 🔴 **Error**: none succeeded and none was deferred.
- Click an entry: each asset or FX pair, its provider and the prices changed (**Delta**). Hover an error to read it in full; double-click (long-press on a phone) to copy it.
- A deferred item shows a pause icon and **Deferred: provider paused**: hover the label to read the provider's message. The entry counts the deferred items with ⏸, next to ✓ and ✗ (for example `3/5 ✓ · 1 ⏸ · 1 ✗`), and **Retry at** in the header gives the time of the retry.
- Filter by job, status or period, from the last hour to the last 30 days. Only the most recent runs are kept.

---

## ⏸️ Provider Pauses {: #provider-pauses }

When a price or rate provider (Yahoo Finance, the European Central Bank…) answers «too many requests» (HTTP 429), LibreFolio pauses it: until the pause ends, no request reaches it, neither from the [market data scheduler](settings.md#market-data-scheduler) nor from a user. A pause holds for every user and every job of the server.

The pauses are on by default. `LIBREFOLIO_PROVIDER_COOLDOWN_BASE_SECONDS=0` turns them off, as before release 1.3.

**Where:** **in the `.env` file** (or in the container's environment). These are the defaults:

```env
LIBREFOLIO_PROVIDER_COOLDOWN_BASE_SECONDS=60
LIBREFOLIO_PROVIDER_COOLDOWN_MAX_SECONDS=3600
```

| Variable | Default | What it does |
| --- | --- | --- |
| `LIBREFOLIO_PROVIDER_COOLDOWN_BASE_SECONDS` | `60` | The first pause, in seconds, doubled at each refusal in a row: a whole number from `0` to `86400` (one day). `0` turns the pauses off. |
| `LIBREFOLIO_PROVIDER_COOLDOWN_MAX_SECONDS` | `3600` | The longest pause the doubling reaches, in seconds: a whole number from `1` to `86400`, not below the first pause while the pauses are on. A provider's `Retry-After` may still ask for more, up to one day. |

Restart LibreFolio. With Docker Compose, run `docker compose up -d`.

- A value LibreFolio cannot use does not stop the server: the log has an error ([In the Log](#provider-pauses-log)) and both defaults apply, 60 and 3600: the pauses stay on.
- With the pauses off, every request goes to the provider again; the scheduler still counts a refused request as deferred ([below](#provider-pauses-effects)).

### ⏱️ How Long a Pause Lasts {: #provider-pauses-length }

- **The first refusal** pauses the provider for `LIBREFOLIO_PROVIDER_COOLDOWN_BASE_SECONDS`, 60 seconds by default.
- **Each refusal in a row** doubles the pause, up to `LIBREFOLIO_PROVIDER_COOLDOWN_MAX_SECONDS`. With the defaults: 2 minutes, then 4, 8, 16 and 32, then an hour at each further refusal. Requests refused together count as one refusal.
- **A `Retry-After`**, when the provider sends one, is the shortest pause LibreFolio takes: honoured even beyond the longest pause, up to one day.
- **A random extra** of up to 10 % is added to each pause, never past one day.
- **When a pause ends**, one request goes through to try the provider; the others still count as paused until it has an outcome, a minute at most. An answer ends the series: the next refusal starts again from the first pause. The same goes for a refusal that comes, from the end of the previous pause, after a gap longer than the longest pause.
- **A pause holds for the whole provider**, except with the CSS Scraper: a site that refuses pauses only the pages of that site; the other sites are still read.

### 👀 Who Waits, and What You See {: #provider-pauses-effects }

| Where | During a pause |
| --- | --- |
| 🕐 [Market data scheduler](settings.md#market-data-scheduler) | The assets and FX pairs of a paused provider are **deferred**: neither updated nor failed, and their job is **Partial**. The job runs again when the first of those pauses ends, or at its regular time if that comes first. How **Scheduler Status** and the **Scheduler Execution Log** show it: «Read the scheduler log», above. |
| 💰 Live prices, in the Assets list and on an asset's page | The last stored price stays, with no new message. When every asset the page asks about has its provider paused, the page asks again by itself only once the first of those pauses is over; while one provider still answers, the refresh goes on and LibreFolio does not call the paused ones. After a refresh that fails, the next one waits twice as long, and so on up to ten minutes, until one works again. |
| 🔌 **Test Configuration**, in the asset dialog | ⚠️ *Paused for too many requests until …*, with the time the pause ends; the test still passes. See [Connect a price provider](../user/assets/create-edit.md). |
| 🔎 Asset search | A paused provider returns no result until its pause ends; the others answer as usual. |
| 💱 Exchange rates | A paused provider counts as a route that failed: a pair with another route gets its rate there, as when a central bank does not answer ([Provider Configuration](../user/fx/detail/provider.md)). Otherwise the scheduler defers the pair, as it does an asset. |

### 💤 In Memory {: #provider-pauses-memory }

- **Each server process keeps its own pauses in memory.** A restart forgets them, a deploy included. With several server processes (`--workers N`), each one learns a pause from a refusal of its own; the Docker image runs one.

### 📋 In the Log {: #provider-pauses-log }

| Level | The log says | When |
| --- | --- | --- |
| ⚠️ `warning` | `Provider refused for too many requests: paused`, with `domain` (`asset` or `fx`), `provider`, `scope` (the site, with the CSS Scraper), `wait_s`, the seconds of pause ahead, and `retry_after`, the wait the provider asked for, if any | A provider refused a request |
| ℹ️ `info` | `Provider answering again after a pause`, with `refusals`, the refusals in a row before it | The first answer after a pause |
| ❌ `error` | `Provider pause settings cannot be used: the defaults apply`, with `variable`, `code` (`PROVIDER_COOLDOWN_BASE_INVALID` or `PROVIDER_COOLDOWN_MAX_INVALID`) and `reason` | One of the two variables has a value that cannot be used: once per server process, the first time LibreFolio is about to call a provider |

At `DEBUG` level, `Provider call skipped: paused after too many requests`, with `wait_s`, marks each request a pause kept from being sent. The scheduler's lines, `Scheduler: current-price refresh` and `Scheduler: history sync`, give the deferred items in `deferred`, with `retry_at`.

---

## 🗄️ Server Caches {: #server-caches }

LibreFolio keeps recent provider answers and computed results in memory.

**Where:** **Global Settings › Memory › Cache Status**, at the end of the category. The panel lists each cache with **Size / Max** and **TTL** (how long an entry is kept). Click a column header to sort; **Refresh** updates the numbers.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="settings" data-name="cache-panel" alt="Server caches panel in Global Settings (Memory category)">
</div>

The panel shows its numbers even with the tab locked. With the tab unlocked, **Clear** empties one cache and **Clear all** all of them, to force fresh data without a restart. A restart empties every cache too.

!!! warning "Clearing a cache slows down the next fetch"

    Both actions ask for confirmation first. After a clear, the next request for that data goes back to the providers: expect a slowdown similar to a server restart until the caches fill up again.

??? note "🧵 Several workers — when the server runs with `--workers`"

    Each worker process has its own caches. The panel shows and clears those of the worker that answered; restart the server to empty them all.

---

## 🛡️ Security {: #security-tab }

**Where:** **Settings › Administration › Security**. Only administrators have the tab. It checks how the instance is configured and lists first what needs your attention.
It is not the 🛡️ **Security** category of Global Settings, which holds **Registration** and **Require Email Verification**.

### 🚦 What It Lists {: #security-findings }

Each finding says what is wrong, with an icon and a colour: ❌ an **error**, ⚠️ a **warning** or ℹ️ an **information**. Errors first, then warnings, then information; at equal severity, the order of this table.

| Check | A finding when | Its link |
|---|---|---|
| Session signing key | ℹ️ The key is random: every restart signs everyone out; set `JWT_SECRET` to stay signed in. ⚠️ The key is shorter than 32 characters. ❌ Its `JWT_SECRET_FILE` cannot be read | — |
| Secrets set twice | ⚠️ A secret is set both directly and through its `_FILE` variable: the direct value wins | — |
| Instance key | ❌ It cannot be used. ⚠️ Its folder or its file is open to other users | — |
| Session cookie | ⚠️ `SESSION_COOKIE_SECURE=never`: the cookie also travels over plain HTTP | — |
| Visitor's address | ⚠️ Since the start, requests came through a reverse proxy that LibreFolio does not trust: the limits per visitor's address do not apply to them. ℹ️ Since the start, forwarding headers from a public address were ignored. What to do: [The Visitor's Address](connection_proxy.md#client-address) | — |
| Log level | ℹ️ `DEBUG` or `TRACE` | — |
| Test mode | ❌ `LIBREFOLIO_TEST_MODE` is on outside LibreFolio's test runs: data providers that exist only for the tests are served and the data are kept in the test data folder | — |
| Upload limit of a restore | ❌ `LIBREFOLIO_BACKUP_MAX_UPLOAD_MB` cannot be used (a whole number of megabytes, `0` for no limit): restore uploads are refused until it is fixed. Passed with a limit, such as *A restore accepts archives of up to 500 MB.*, or with none | — |
| Unpacked size of a restore | ❌ `LIBREFOLIO_BACKUP_MAX_RESTORE_MB` cannot be used (a whole number of megabytes, `0` for no limit): restore checks are refused until it is fixed. Passed with a limit, such as *A restore check accepts archives that unpack to up to 4000 MB.*, or with none | — |
| Failed sign-ins | ⚠️ The limit is off: `LIBREFOLIO_LOGIN_LIMIT=off` | — |
| Email server | ❌ A `LIBREFOLIO_SMTP_*` value cannot be used: email stays off until it is fixed | **Open the Email tab** |
| Email encryption | ⚠️ Emails, their links and the SMTP password travel unencrypted to a server outside your local network | **Open the Email tab** |
| Links in emails | ℹ️ Email works, but `LIBREFOLIO_PUBLIC_URL` is not set. ⚠️ `LIBREFOLIO_PUBLIC_URL` cannot be used at the start of a link | **Open the Email tab** |
| Plugin secrets | ❌ Instance-wide plugin secrets cannot be read with the instance key | **Open the plugin settings**, in **Settings › Plugins** |
| Open registration, checked by your browser | ⚠️ **Registration** is **Open** and you reached LibreFolio at an address outside your local network, as for [the warning above the pages](#open-registration-warning) | **Change who can sign up**, in **Global Settings**. None when `LIBREFOLIO_REGISTRATION` sets the mode: the finding names that variable instead |
| A blocked script, checked by your browser | ⚠️ A script that LibreFolio did not send, added by a proxy, a CDN or a browser extension, was blocked in this browser tab: the finding names its sources. It goes when you close the tab. Not fixed on the server, but in the proxy, the CDN or the extension: [A Script You Did Not Send](configuration_security.md#csp-blocked-script) | — |

Every row has a help button, chosen by who can solve the check:

- 📖 **Guide**: you can solve it alone, on the server. The button, shown on passed checks too, opens the page of this guide that explains that check, in a new tab and in your language when it is translated.

A check without a page of its own and without support has no button.

The findings without a link are fixed in the server's configuration (**`.env` file**) and need a restart: what to do for each one is in the table of «Startup Checks» in [Configuration](configuration.md), where the server's log reports the same checks.

### 🔢 The Number on the Tab {: #security-badge }

**Security** shows how many errors and warnings it lists; **Administration** shows the same number, visible from every tab of Settings. Information is listed but never counted: with information only there is no number, and the tab does not say *Nothing needs your attention.* either.

Outside Settings, the same count follows you on every page, as a dot on the connection line at the bottom of the sidebar: red with at least one error, amber with warnings only, none with information only. Click the line: after its reason, the details link to this tab with the count, for example **2 security warnings**, errors included. On a phone, the menu button carries the dot too. What it looks like: [Security Warnings for Administrators](../user/connection-security.md#security-warnings).

### 🔄 When It Checks {: #security-refresh }

LibreFolio reads the checks once, as soon as it opens in your browser, whatever the page: the sidebar's connection line asks for them, so the dot and the number on the tab are already there when you open **Settings**. If that read fails, opening **Settings** tries again. The checks stay the same while you use the app: after changing the server's configuration (`.env` file) and restarting, click **Check again**, at the top of the tab, or reload the page. The open-registration finding follows **Registration** at once: saving it in Global Settings updates the list, the number and the dot.

- ⏳ Until the first answer, the tab shows placeholder rows.
- ⚠️ When the checks cannot be read, the tab says *The security checks could not be loaded.*, with **Try again**. After a **Check again** that fails, the last results stay listed below.

### ✅ Passed Checks {: #security-passed }

With no finding, the tab says *Nothing needs your attention.* Below the findings, a folded section, **N checks passed**, lists the passed checks, each with its own sentence (for example *Sessions are signed with a key set by the administrator.*): click it to unfold it. Email that is off, or sent unencrypted to a server of your own network, counts as passed and says so there.

---

## 🔗 Related

- 📝 **[Environment Variables](configuration.md)** — The settings that live in the `.env` file instead
- 👥 **[Users & Invitations](users.md)** — The accounts of the instance, the invitations and the password-reset links
- 👤 **[User Preferences](../user/settings/preferences.md)** — What each user can change for themselves
- 🧑‍💻 For developers: **[Settings System](../developer/architecture/settings.md)**,
  **[Cache Registry](../developer/architecture/settings_cache.md)**,
  **[Market Data Scheduler](../developer/backend/scheduler.md)** and
  **[Configuration Checks](../developer/architecture/security.md#configuration-checks)**
