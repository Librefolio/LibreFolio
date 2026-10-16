# ⚙️ Global Settings

Global settings apply to the whole instance and to every user. They are stored in the database:
every signed-in user can read them, only administrators can change them.

---

## ✏️ Change a Setting

### 🔓 1. Unlock the tab

Open **Settings** (gear icon in the sidebar), then the **Admin** tab: its **Global Settings**
panel groups the settings by category. Click the **lock icon** (🔒) in the header to unlock it.
Only administrators (superusers) have the lock; everyone else gets a read-only view.

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

Its link, **Change who can sign up**, opens **Settings › Admin**, where this setting is. When
`LIBREFOLIO_REGISTRATION` sets the mode on the server, the warning names that variable instead, and
has no link: only the server's configuration can change the mode
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

Everyone can see the panel. An administrator, with the tab unlocked, can empty one cache with
**Clear** or all of them with **Clear all**, to force fresh data without a restart. A restart
empties every cache too.

!!! warning "Clearing a cache slows down the next fetch"

    Both actions ask for confirmation first. After a clear, the next request for that data goes
    back to the providers, so expect a slowdown similar to a server restart while the caches fill
    up again.

??? note "🧵 Several workers — when the server runs with `--workers`"

    Each worker process has its own caches. The panel shows, and clears, those of the worker that
    answered; restart the server to empty them all.

---

## 🔗 Related

- 📝 **[Environment Variables](configuration.md)** — The settings that live in `.env` instead
- 👥 **[Users & Invitations](users.md)** — The accounts of the instance, invitations and password-reset links
- 👤 **[User Preferences](../user/settings/preferences.md)** — What each user can change for themselves
- 🧑‍💻 For developers: **[Settings System](../developer/architecture/settings.md)**,
  **[Cache Registry](../developer/architecture/settings_cache.md)** and
  **[Market Data Scheduler](../developer/backend/scheduler.md)**
