# 💤 Sleep and Wake

LibreFolio does not have to run around the clock. The machine it runs on can be suspended when
nobody uses it, or switched off at night, and started again later: by a hosting panel, on its own
schedule, or by a script or a cron job of yours on a home server. While the machine sleeps, nothing
updates the prices and the exchange rates; the
[market data scheduler](settings.md#market-data-scheduler) catches up once it runs again, in the
background, while the app shows **Updating prices…** ([While Prices Catch Up](wake_sync.md#price-refresh)).

Two features help, both off until you turn them on. With the [idle suspension](#idle-suspend), the
instance asks Fly.io to suspend its machine after a few minutes without visitors (on any other
host, leave it off); with the [scheduled wake-up](wake_sync.md#wake-sync), whoever wakes the machine brings the
data up to date at once, and knows when it is done, with one call. To check both on a real Fly.io
machine, see [Check That It Works](#check-it-works).

The page also covers the [provider pauses](#provider-pauses), on by default on every install: a
price provider that answers «too many requests» is left alone until its pause is over.

!!! info "📚 This guide is in several pages"

    This page covers the idle suspension, how to check it on Fly.io and the provider pauses. The [scheduled wake-up](wake_sync.md#wake-sync) has a page of its own: [Sleep and Wake: Scheduled Wake-up](wake_sync.md) explains the token, the call and its answer, and what users see while prices catch up.

---

## 😴 Idle Suspension {: #idle-suspend }

When nobody has used LibreFolio for a few minutes, and no work is in progress, it can ask Fly.io to
suspend the machine it runs on. Fly saves the machine's memory and CPU state, and its proxy resumes
the machine at the next request, where it stopped: the server does not restart, and the user who
comes back only waits for the resume.

It is off by default: a self-hosted install that does not set it is unchanged. Fly.io is the only
host LibreFolio can ask today; on any other host, leave it off.

| Variable | Default | What it does |
| --- | --- | --- |
| `LIBREFOLIO_IDLE_SUSPEND_MODE` | `none` | `fly` turns the idle suspension on; `none` never suspends. Case and spaces around the value do not matter. |
| `LIBREFOLIO_IDLE_SUSPEND_MINUTES` | `5` | How many minutes without a user's request before the machine is suspended: a whole number from `1` to `1440` (one day). Read only with `fly`. |

LibreFolio reads both at startup: change them, then restart it ([Setting Up Fly.io](#idle-suspend-fly)
shows where they go). A value it cannot use does not stop the server: the log has an error
([In the Log](#idle-suspend-log)), an unknown mode counts as `none`, so that a typo never suspends
the machine, and unusable minutes count as 5.

### 👀 What Keeps the Machine Awake {: #idle-suspend-activity }

LibreFolio asks for the suspension only when nobody is around **and** no work is in progress.

**Nobody is around** when no request from a user has reached the server for
`LIBREFOLIO_IDLE_SUSPEND_MINUTES` minutes. Every request counts (a page, an image, an API call),
except:

- the health checks, `/api/v1/system/health` and `/api/v1/system/ready`, which a host or an uptime
  monitor may call every few seconds;
- the [scheduled wake-up](wake_sync.md#wake-sync): it is not a visit, although it keeps the machine awake while
  its jobs run;
- the calls of a hosting panel to its backup routes, `/api/v1/backup/panel/…`, and to its status
  route, `/api/v1/panel/status` ([Hosting Panel API](hosting_providers.md#panel-api)): they are not
  visits either, so a panel that polls a backup or the setup status never keeps the machine awake
  as a visit would. Each call keeps it awake only while it runs, a download until its last byte,
  and a running backup keeps it awake by itself (below). Like any request through Fly's proxy, a
  call still resumes a suspended machine, as the tip below says of uptime monitors. The backup and
  restore routes of Settings › Administration › Backup, `/api/v1/backup/instance…` and
  `/api/v1/backup/restore/…`, are the user's: they count as visits.

The live prices of the Assets list and of an asset's page are requests too, so they count while
someone uses the page. They pause while the tab is in the background and after two minutes without
mouse, keyboard or touch: a tab left open with nobody in front of it does not keep the machine
awake.

**Work in progress** keeps the machine awake, however long nobody has been around:

- a request still being answered, such as a long download;
- a run of the [market data scheduler](settings.md#market-data-scheduler), which updates the prices
  and the exchange rates;
- a [Tool](../user/tools/index.md) calculation, waiting or running;
- a backup, whoever started it, and the check of an archive uploaded for a restore. While a backup
  runs, the **Backup** tab of the settings reads its progress every second, in the background too,
  and those reads are visits: with that page open, the minutes start again when the backup ends.
  Leave it or close it, and the machine sleeps within 30 seconds of the end, once the minutes have
  run out since you left.

!!! tip "📡 Uptime monitors"

    Point an uptime monitor at `/api/v1/system/health`: its calls never count as a visit. Each call
    still resumes a suspended machine, as any request through Fly's proxy does, and the machine
    sleeps again within about a minute: a monitor that calls every minute or so keeps it awake most
    of the time.

### ⏱️ When It Sleeps and Wakes {: #idle-suspend-timing }

- **Going to sleep.** LibreFolio checks every 30 seconds, so the machine is suspended at most
  30 seconds after the minutes have run out: with the default, between 5 minutes and 5 minutes
  30 seconds after the user's last request. When work is still in progress then, it is suspended
  within 30 seconds of the end of that work. Work that is itself a user's request, such as a long
  download or a Tool calculation, counts as a visit when it ends, so the minutes start again from
  its end. With an Assets page left open, add the two minutes its live prices keep refreshing after
  the last input.
- **After a [scheduled wake-up](wake_sync.md#wake-sync).** The wake-up is not a visit, so it does not start the
  minutes again. A check comes 2 seconds after its jobs end: when nobody has been around for the
  minutes, the machine goes back to sleep at once, without waiting for the next regular check. A
  hosting panel can thus wake it, bring the prices up to date, and leave it asleep again.
- **Waking up.** The request that reaches a suspended machine resumes it, and LibreFolio answers it
  as usual. The first request from a user after a suspension, like any that comes after at least a
  minute of silence, also makes the [market data scheduler](settings.md#market-data-scheduler) run
  at once: it catches up the price and exchange-rate updates that fell due while the machine slept,
  in the background ([While Prices Catch Up](wake_sync.md#price-refresh)). After asking for a suspension,
  LibreFolio waits a minute before its next check, so that the request that woke the machine counts
  first.
- **After a cold start.** A deploy discards the state Fly saved, and Fly may start a machine from
  scratch in other cases too: the minutes then count from the start of the server.
- **One server process.** Run a single server process, as the Docker image does: each process
  counts only the requests it serves itself, so with several (`--workers N`) one of them could
  suspend the machine while another serves a user.

### 🪂 Setting Up Fly.io {: #idle-suspend-fly }

LibreFolio decides when the machine sleeps, because it knows what work is in progress: Fly's proxy
only wakes it. LibreFolio asks through Fly's Machines API, on the `/.fly/api` socket that Fly
provides inside each machine: there is no token to create.

The lines that matter in `fly.toml`; keep the rest of yours as it is:

```toml
kill_signal = "SIGTERM"
kill_timeout = 10

[env]
  LIBREFOLIO_IDLE_SUSPEND_MODE = "fly"
  LIBREFOLIO_IDLE_SUSPEND_MINUTES = "5"  # optional: 5 is the default

[http_service]
  internal_port = 6040
  auto_stop_machines = "off"
  auto_start_machines = true
  min_machines_running = 0
```

Deploy with `fly deploy`, then look for `Idle monitor started` in `fly logs`.

- **`auto_stop_machines = "off"`**: Fly's proxy never stops or suspends the machine on its own.
  With `"stop"` or `"suspend"`, it would when it sees no traffic for a few minutes, even in the
  middle of a backup or a price update.
- **`auto_start_machines = true`**: a request resumes the suspended machine. Fly's documentation
  advises turning both on or both off; here LibreFolio does the suspending, so only the start is
  left to Fly.
- **`min_machines_running = 0`**: no machine has to stay running.
- **`internal_port = 6040`**: the port the LibreFolio image listens on.
- **`kill_signal` and `kill_timeout`**: a suspension sends no signal, since the server is frozen,
  not stopped; these two matter when Fly stops the machine, at a deploy or a restart. By default
  Fly sends SIGINT and kills the machine 5 seconds later, before LibreFolio's 8-second shutdown
  budget runs out. SIGTERM is the signal `docker stop` sends too, and 10 seconds leave LibreFolio
  its 8 and a margin. If you raise `LIBREFOLIO_SHUTDOWN_TIMEOUT_SECONDS`, keep `kill_timeout` at
  least 2 seconds above it (Fly allows up to 300): see
  [Stopping the Server](configuration_security.md#shutdown).

Fly documents what a machine needs to be suspended: 2 GB of memory or less, no swap
(`swap_size_mb`), no schedule, and an update since 20 June 2024:
`fly machine update <machine-id> --yes` brings an older machine up to date. See
[Machine Suspend and Resume](https://fly.io/docs/reference/suspend-resume/) in Fly's documentation.

### 📋 In the Log {: #idle-suspend-log }

| Level | The log says | When |
| --- | --- | --- |
| ℹ️ `info` | `Idle monitor started`, with `mode` and `minutes` | At startup, with `fly`. No such line: the idle suspension is off |
| ℹ️ `info` | `Idle suspend requested`, with `idle_s`, the seconds without a user's request, and `minutes` | Fly accepted the suspension. Fly may suspend the machine before the line is written, which then appears after the resume |
| ⚠️ `warning` | `Idle suspend failed`, with `reason` and `retry_in_s` | The first failure in a row: see below |
| ❌ `error` | `Idle suspend mode cannot be used: the machine is never suspended` | At startup: `LIBREFOLIO_IDLE_SUSPEND_MODE` is neither `none` nor `fly` |
| ❌ `error` | `Idle suspend minutes cannot be used: the default applies` | At startup, with `fly`: `LIBREFOLIO_IDLE_SUSPEND_MINUTES` is not a whole number from 1 to 1440, and 5 minutes apply |

**When a suspension fails**, LibreFolio tries again later, as long as nobody comes back. It waits
at least `retry_in_s` seconds: 30 after the first failure, twice as long after each failure in a
row, up to 10 minutes. Only the first failure is a warning: the next ones are logged at `DEBUG`
level, as `Idle suspend failed again`, until a suspension succeeds. `reason` says what went wrong:

| `reason` | What it means |
| --- | --- |
| `not_on_fly` | `FLY_APP_NAME` or `FLY_MACHINE_ID` is not set, so this is not a Fly.io machine: Fly sets both on each of its machines. On any other host, set `LIBREFOLIO_IDLE_SUSPEND_MODE` back to `none` |
| `http_<status>` | Fly's Machines API answered with that HTTP status instead of accepting the suspension: check what a machine needs in [Setting Up Fly.io](#idle-suspend-fly) |
| `connection` | Fly's Machines API did not answer |
| `error` | Another error: its name is in an `Idle suspend raised` line, at `DEBUG` level |

---

## ✅ Check That It Works {: #check-it-works }

These checks try the idle suspension and the scheduled wake-up on a real Fly.io machine. You need
a Fly app set up as in [Setting Up Fly.io](#idle-suspend-fly) and, for the wake-up, a token in
`LIBREFOLIO_WAKE_TOKEN` ([Turning It On](wake_sync.md#wake-sync-token)). Any request through Fly's proxy
resumes a suspended machine, health checks included: pause any uptime monitor while you check.

1. **It is on.** After `fly deploy`, `fly logs` shows `Idle monitor started`, with `mode` (`fly`)
    and `minutes`. No such line: the idle suspension is off, and [In the Log](#idle-suspend-log)
    lists the errors to look for at startup.
2. **It goes to sleep.** Sign in, open a page, then close the tab or leave it in the background.
    LibreFolio checks every 30 seconds: with the default, the machine is suspended between 5 minutes
    and 5 minutes 30 seconds after your last request. An Assets page or an asset's page left in the
    foreground adds two minutes: its live prices pause two minutes after your last mouse, keyboard
    or touch input. `fly logs` then shows `Idle suspend requested`, with `idle_s` and `minutes` (or
    after the next resume, when Fly suspended the machine first), and `fly machine list`, or
    `fly machine status <machine-id>`, shows the state `suspended`.
3. **A visit wakes it.** Open the app again: the first request resumes the machine, and LibreFolio
    answers it as usual. It then runs at once the price and exchange-rate updates that fell due
    while the machine slept: while one runs, the app shows **Updating prices…**, which goes away by
    itself ([While Prices Catch Up](wake_sync.md#price-refresh)). The machine does not go back to sleep while
    you use it: your visit started the minutes again, and LibreFolio waits a minute after asking
    for a suspension before it checks again.
4. **Work keeps it awake.** Start a backup from the **Backup** tab of the settings, then close the
    browser tab: that page reads the backup's progress every second, in the background too, and
    each read is a visit ([What Keeps the Machine Awake](#idle-suspend-activity)). If the minutes
    run out before the backup ends, the machine stays awake until the end, and is suspended within
    30 seconds after.
5. **A wake-up brings the data up to date.** While the machine sleeps, call the route from your
    computer, with the token in the shell variable `LIBREFOLIO_WAKE_TOKEN` (`-N` shows the answer
    as it comes):

    ```bash
    curl -N -X POST -H "Authorization: Bearer $LIBREFOLIO_WAKE_TOKEN" \
      https://<your-app>.fly.dev/api/v1/system/wake-sync
    ```

    The call resumes the machine. The answer, a `200`, is blank spaces, one at once and one every
    15 seconds while the jobs run, then the report in JSON on one line: check its `status`, `ok`
    when all went well ([The Answer](wake_sync.md#wake-sync-answer)). `fly logs` shows `Wake-up run started`,
    then `Wake-up run finished` with `status` and `jobs`, the jobs that ran. A wake-up is not a
    visit: it does not start the minutes again, so with nobody around for the minutes, 2 seconds
    after the jobs end the machine is suspended again (`Idle suspend requested`, state `suspended`).
6. **A wrong call is refused.** Without the `Authorization` header, or with a wrong token, the
    answer is `401` (`wake_unauthorized`). A second call while a run is in progress, from another
    terminal, gets `409` (`wake_in_progress`). A `404` means the server has no token.

**If the machine does not sleep**, or sleeps at the wrong time:

- An `Idle suspend failed` line gives a `reason`: see [In the Log](#idle-suspend-log).
- Neither that line nor `Idle suspend requested`: something keeps the machine awake, such as a tab
  left open and used, the **Backup** tab open during a backup, or an uptime monitor that calls
  every minute or so ([What Keeps the Machine Awake](#idle-suspend-activity)).
- Check against [Setting Up Fly.io](#idle-suspend-fly): `auto_stop_machines = "off"`, and a machine
  with 2 GB of memory or less, no swap, no schedule, updated since 20 June 2024.
- Run a single server process: with several (`--workers N`), one may suspend the machine while
  another serves a user ([When It Sleeps and Wakes](#idle-suspend-timing)).

---

## ⏸️ Provider Pauses {: #provider-pauses }

LibreFolio asks outside services for prices and exchange rates: its price providers, such as Yahoo
Finance or the European Central Bank. When one of them answers «too many requests» (HTTP 429),
LibreFolio pauses it: until the pause ends, no request reaches that provider, whether the
[market data scheduler](settings.md#market-data-scheduler) or a user asks. A pause holds for every
user and every job of the server.

The pauses are on by default: an exception to the rule that a new option leaves an install as it
was, by developer decision 34 (15 October 2026). `LIBREFOLIO_PROVIDER_COOLDOWN_BASE_SECONDS=0`
turns them off, as before release 1.3.

| Variable | Default | What it does |
| --- | --- | --- |
| `LIBREFOLIO_PROVIDER_COOLDOWN_BASE_SECONDS` | `60` | The first pause, in seconds, doubled at each refusal in a row: a whole number from `0` to `86400` (one day). `0` turns the pauses off. |
| `LIBREFOLIO_PROVIDER_COOLDOWN_MAX_SECONDS` | `3600` | The longest pause the doubling reaches, in seconds: a whole number from `1` to `86400`, and not below the first pause while the pauses are on. A provider's `Retry-After` may still ask for more, up to one day. |

Set them in `.env` or in the container's environment, then restart LibreFolio: with Docker Compose,
`docker compose up -d`. A value LibreFolio cannot use does not stop the server: the log has an
error ([In the Log](#provider-pauses-log)), and both defaults apply, 60 and 3600, so the pauses stay
on. With the pauses off, every request goes to the provider again; the scheduler still counts a
refused one as deferred ([below](#provider-pauses-effects)).

### ⏱️ How Long a Pause Lasts {: #provider-pauses-length }

- **The first refusal** pauses the provider for `LIBREFOLIO_PROVIDER_COOLDOWN_BASE_SECONDS`, 60
  seconds by default.
- **Each refusal in a row** doubles the pause, up to `LIBREFOLIO_PROVIDER_COOLDOWN_MAX_SECONDS`.
  With the defaults: 2 minutes, then 4, 8, 16 and 32, then an hour at each further refusal.
  Requests refused together count as one refusal.
- **A `Retry-After`**, when the provider sends one, is the shortest pause LibreFolio takes: it is
  honoured beyond the longest pause, up to one day.
- **A random extra** of up to 10 % is added to each pause, never past one day.
- **When a pause ends**, one request goes through to try the provider, and the others still count
  as paused until it has an outcome, a minute at most. An answer ends the series: the next refusal
  starts again from the first pause, and so does a refusal that comes more than the longest pause
  after the previous pause ended.
- **A pause holds for the whole provider**, except with the CSS Scraper: a site that refuses pauses
  only the pages of that site, and the other sites are still read.

### 👀 Who Waits, and What You See {: #provider-pauses-effects }

| Where | During a pause |
| --- | --- |
| 🕐 [Market data scheduler](settings.md#market-data-scheduler) | The assets and FX pairs of a paused provider are **deferred**: counted neither as updated nor as failed, and their job is **Partial**. The job runs again when the first of those pauses ends, or at its regular time if that comes first. In **Global Settings**, the **Scheduler Status** row reads **Paused items retried at …** for the current price refresh; the **Scheduler Execution Log** counts the deferred items with ⏸, marks each one with a pause icon and **Deferred: provider paused**, and shows **Retry at …** in the entry's header: see «Read the scheduler log» on that page. |
| ⏰ [Scheduled wake-up](wake_sync.md#wake-sync-answer) | Each job of the answer counts its deferred items in `items_deferred`, and says in `retry_at` when it runs again. |
| 💰 Live prices, on the Assets list and on an asset's page | The last stored price stays, with no new message. When every asset the page asks about has its provider paused, the page asks again by itself only once the first of those pauses is over; while one provider still answers, the refresh goes on, and LibreFolio does not call the paused ones. After a refresh that fails, the next one waits twice as long, and so on up to ten minutes, until one works again. |
| 🔌 **Test Configuration**, in the asset dialog | ⚠️ *Paused for too many requests until …*, with the time the pause ends; the test still passes. See [Connect a price provider](../user/assets/create-edit.md). |
| 🔎 Asset search | A paused provider brings no result until its pause ends; the other providers answer as usual. |
| 💱 Exchange rates | A paused provider counts as a route that failed: a pair with another route gets its rate there, as when a central bank does not answer ([Provider Configuration](../user/fx/detail/provider.md)). Otherwise the scheduler defers the pair, as it does an asset. |

### 💤 In Memory, and During a Suspension {: #provider-pauses-memory }

- **Each server process keeps its pauses in memory.** A restart forgets them, a deploy included.
  With several server processes (`--workers N`), each one learns a pause from a refusal of its own;
  the Docker image runs one.
- **With the [idle suspension](#idle-suspend)**, a pause is not work in progress: the machine may be
  suspended during one. A pause runs on the wall clock, so one begun before a suspension is over at
  the wake-up if its time has passed meanwhile. The retry of the deferred items does not wake the
  machine: the scheduler runs it once the machine is awake again, and the answer of the
  [scheduled wake-up](wake_sync.md#wake-sync-answer) gives its `retry_at`, to plan the next wake-up.

### 📋 In the Log {: #provider-pauses-log }

| Level | The log says | When |
| --- | --- | --- |
| ⚠️ `warning` | `Provider refused for too many requests: paused`, with `domain` (`asset` or `fx`), `provider`, `scope` (the site, with the CSS Scraper), `wait_s`, the seconds of pause ahead, and `retry_after`, the wait the provider asked for, if any | A provider refused a request |
| ℹ️ `info` | `Provider answering again after a pause`, with `refusals`, the refusals in a row before it | The first answer after a pause |
| ❌ `error` | `Provider pause settings cannot be used: the defaults apply`, with `variable`, `code` (`PROVIDER_COOLDOWN_BASE_INVALID` or `PROVIDER_COOLDOWN_MAX_INVALID`) and `reason` | One of the two variables has a value that cannot be used: once per server process, the first time LibreFolio is about to call a provider |

At `DEBUG` level, `Provider call skipped: paused after too many requests`, with `wait_s`, marks each
request a pause kept from the provider. The scheduler's own lines, `Scheduler: current-price refresh`
and `Scheduler: history sync`, give the deferred items in `deferred`, with `retry_at`.

---

## 🔗 Related

- 📄 **[Sleep and Wake: Scheduled Wake-up](wake_sync.md)** — Scheduled Wake-up, While Prices Catch Up
- 📝 **[Environment Variables](configuration.md)** — `LIBREFOLIO_WAKE_TOKEN`, the idle suspension
  variables, the provider pause variables, the shutdown budget, and secrets in files such as Docker
  secrets
- 🏢 **[Hosting for Others](hosting_providers.md)** — The managed profile, and blocking an instance
- 🕐 **[Global Settings](settings.md#market-data-scheduler)** — The market data scheduler: its
  schedule and its log
- 🪂 **[Machine Suspend and Resume](https://fly.io/docs/reference/suspend-resume/)** — Fly.io's
  documentation: how a suspension works, and what a machine needs for it
- 🧑‍💻 For developers: **[Market Data Scheduler](../developer/backend/scheduler.md)** — How a run
  works: its checks, its lock and its report; [Catch-up Progress](../developer/backend/scheduler.md#price-refresh)
  for how the app learns of a catch-up, and [Updating prices…](../developer/frontend/components/features/live-ticker.md#price-refresh)
  for the notice
- 🧑‍💻 For developers: **[Provider Pauses](../developer/backend/assets/architecture.md#provider-pauses)** —
  The boundary every call to an asset provider goes through, and what each caller gets during a
  pause; [Paused Providers](../developer/backend/fx/configuration.md#paused-providers) for the
  exchange rates, and [Live Prices](../developer/frontend/components/features/live-ticker.md#backoff)
  for the live refresh of the Assets pages
