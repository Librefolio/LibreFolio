# ⏰ Sleep and Wake: Scheduled Wake-up

This page covers the **scheduled wake-up**: the call that a hosting panel, or a script or a cron job
of yours, makes to run the updates that are due, with its token and its answer, and what users see
**while prices catch up**.

It works on any host. On Fly.io it pairs with the idle suspension, which lets an unused machine
sleep: that, and the provider pauses, are in [Sleep and Wake](sleep_wake.md).

---

## ⏰ Scheduled Wake-up {: #wake-sync }

`POST /api/v1/system/wake-sync` runs the updates that are due now, and answers when they are over,
with how each one went. Nobody signs in: the caller presents a token that you choose, and the route
stays off until you set it ([Turning It On](#wake-sync-token)).

```bash
curl -X POST -H "Authorization: Bearer $LIBREFOLIO_WAKE_TOKEN" \
  https://librefolio.example.com/api/v1/system/wake-sync
```

Who calls it, and when:

- **A hosting panel** that wakes the instance on its own schedule, for example every morning: it
  calls the route right after the wake-up, and the answer tells it when the updates are done.
- **A script or a cron job of yours**, for a home server that sleeps or is switched off part of the
  day: right after the server is back.

On a server that runs all the time you do not need it: the scheduler already checks every minute
what is due.

### ⚙️ What a Wake-up Runs {: #wake-sync-jobs }

A wake-up runs the jobs of the [market data scheduler](settings.md#market-data-scheduler), each
one only when it is due by the schedule of the **Update Job** settings:

- 💰 **Current price refresh** (`current_price`): the latest price of each active asset that has a
  price provider, when the last refresh is older than **Refresh every** (10 minutes by default).
- 📊 **History sync** (`history_sync`): the daily prices of those assets and the rates of the FX
  pairs with a provider, when a sync time has passed since the last history sync: one that passed
  while the machine slept counts too.

Good to know:

- A wake-up never forces a job: one that is not due does not run, and the answer says `not_due`.
- Nothing runs while the scheduler is off: when `LIBREFOLIO_NO_SCHEDULER` is set
  (`./dev.py server --no-scheduler` sets it), or when **Scheduler Enabled** is off in the
  **Update Job** settings.
- The run first waits 2 seconds, so that a machine that has just woken up has its clock right
  before the jobs are checked.
- A run of the scheduler already in progress ends first; the wake-up then runs only what is still
  due. The wake-up waits ten minutes at most for it: see `not_leader` in
  [The Answer](#wake-sync-answer).
- The jobs a wake-up runs show in the **Scheduler Execution Log** like any other run. The server
  log has `Wake-up run started`, then `Wake-up run finished` with how the run ended.

### 🔑 Turning It On {: #wake-sync-token }

The scheduled wake-up is off by default: without a token, the route answers `404`, as if it did not
exist.

1. Generate a token:

    ```bash
    openssl rand -hex 32
    ```

2. Put it in `.env`, or in the container's environment:

    ```bash
    LIBREFOLIO_WAKE_TOKEN=<the 64 characters printed above>
    ```

    To keep it out of `.env`, give `LIBREFOLIO_WAKE_TOKEN_FILE` the path of a file that holds it,
    such as a Docker secret (`/run/secrets/wake_token`): see
    [Secrets in Files](configuration_secrets.md#secret-files). When both are set, `LIBREFOLIO_WAKE_TOKEN` wins.

3. Restart LibreFolio. With Docker Compose, run `docker compose up -d`: `docker compose restart`
    keeps the old values.
4. Give the same token to whoever calls the route.

The rules of the token:

- **At least 32 visible ASCII characters**, without spaces: letters, digits and punctuation.
  `openssl rand -hex 32` prints 64.
- **A token of its own.** Do not reuse another secret, such as `JWT_SECRET` or the token that lets
  a hosting panel download backups (`LIBREFOLIO_BACKUP_DOWNLOAD_TOKEN`): whoever holds the wake-up
  token can start the updates, and nothing else.
- **Only in the `Authorization: Bearer` header**, never in the URL: addresses end up in the logs of
  servers and proxies, and a token in the URL is refused with `401`.
- **The rules of the hosting panel.** The wake-up is the `wake` scope of the
  [Hosting Panel API](hosting_panel_api.md#panel-api), whose shared rules hold for it too: after too
  many wrong tokens from one address, to any of its scopes, that address gets `429` for a while,
  and each call writes a `Hosting panel request` line in the log.

LibreFolio checks the token at startup, and reads it again at every call. A token it cannot use
(too short, with a space or a character outside ASCII, or a `LIBREFOLIO_WAKE_TOKEN_FILE` that is
missing, unreadable or empty) does not stop the server: the start log has an error that names the
variable (`check` is `platform.hosting_panel`: see
[The Startup Check](hosting_panel_api.md#panel-api-check)), the route answers `503` to every call,
and each call logs this error, with the variable and what is wrong, never the token:

```text
The wake-up token cannot be used: the scheduled wake-up refuses every request
```

Fix it, then restart LibreFolio.

### 📨 The Answer {: #wake-sync-answer }

| Status | When | Body |
| --- | --- | --- |
| `200` | The token is right, and no other wake-up is running | Spaces while the jobs run, then the report of the run in JSON |
| `401` | No token, or a wrong one | The code `wake_unauthorized` |
| `404` | The scheduled wake-up is off: no `LIBREFOLIO_WAKE_TOKEN` | `{"detail": "Not Found"}`, as for an address that does not exist |
| `409` | Another wake-up is still running | The code `wake_in_progress` |
| `503` | The token of the instance cannot be used: the server log says why | The code `wake_unavailable` |

The token is checked first: only a caller with the right token can get a `409`. A refusal carries
its code in `detail`:

```json
{"detail": {"code": "wake_in_progress", "message": "A wake-up is already running"}}
```

**The `200` is streamed.** A run can last more than a minute, and some proxies close a connection
that carries nothing for a minute. So LibreFolio sends a space at once, then one every 15 seconds
while the jobs run, and the report last, on one line. Once the first space has left, the status is
`200` whatever happens: the report's own `status` says how the run ended. A report, indented here
for reading:

```json
{
  "status": "ok",
  "started_at": "2026-10-16T05:00:02.004113Z",
  "finished_at": "2026-10-16T05:00:14.501876Z",
  "error": null,
  "jobs": [
    {
      "name": "current_price",
      "status": "ok",
      "started_at": "2026-10-16T05:00:02.010021Z",
      "duration_s": 12.48,
      "items_ok": 24,
      "items_err": 0,
      "error": null,
      "items_deferred": 0,
      "retry_at": null
    },
    {
      "name": "history_sync",
      "status": "not_due",
      "started_at": null,
      "duration_s": null,
      "items_ok": 0,
      "items_err": 0,
      "error": null,
      "items_deferred": 0,
      "retry_at": null
    }
  ]
}
```

| Field | What it holds |
| --- | --- |
| `status` | How the run ended: see the next table |
| `started_at`, `finished_at` | When the run started and ended, in UTC |
| `error` | When the run itself failed, the name of the error, never its message: the details are in the server log. `null` otherwise |
| `jobs` | Each job, in the order they run, `current_price` then `history_sync`. Empty when no job could run |
| `jobs[].name` | `current_price` or `history_sync` |
| `jobs[].status` | `ok`, `partial` or `error`, as in the **Scheduler Execution Log**; `not_due` when the job was not due |
| `jobs[].started_at`, `jobs[].duration_s` | When the job started, in UTC, and how long it ran, in seconds; `null` when it was not due |
| `jobs[].items_ok`, `jobs[].items_err` | How many assets, and for the history sync FX pairs too, were brought up to date, and how many failed |
| `jobs[].error` | When the job stopped on an error, the name of that error; `null` otherwise |
| `jobs[].items_deferred` | How many assets or FX pairs were put off because their provider is pausing after it answered «too many requests» (HTTP 429): they count neither as brought up to date nor as failed, and a job with deferred items is `partial` |
| `jobs[].retry_at` | When the job will run again, in UTC, if it has deferred items to retry (when the first of their providers' pauses ends) or is waiting after an error (when the wait ends; it doubles at each error in a row). `null` otherwise. A job that is not due reports it too, and deferred items are retried at the job's regular time if that comes first |

A job with deferred items, or one waiting after an error, thus says when it will run again: a hosting
panel can use `retry_at` to plan its next wake-up.

The report's `status`:

| `status` | What it means |
| --- | --- |
| `ok` | Every job that ran went well, or no job was due |
| `partial` | Part of the work failed or was deferred: a job is `partial`, or one job is `ok` and the other `error` |
| `error` | Every job that ran failed, or the run itself failed (see `error`) |
| `disabled` | The scheduler is off: no job ran |
| `not_leader` | No job ran for this call. Either the call waited ten minutes for another run of the scheduler, in the same server process or in another one, and gave up, with a warning in the server log; or, on Windows with several server processes, the process that received the call does not run the jobs. See [Several Workers](#wake-sync-workers) |
| `blocked` | The hosting provider blocked the instance, and no job ran: see [A Blocked Instance](#wake-sync-blocked) |
| `awaiting_restore` | The hosting panel is restoring the instance, and no job ran: see [The Awaiting Restore Mode](hosting_panel_backups.md#await-restore) |
| `restore_interrupted` | The state of a restore cannot be read, so the instance serves no data, and no job ran: see [When the State of a Restore Cannot Be Read](hosting_panel_backups.md#restore-interrupted) |
| `instance_key_mismatch` | The instance key is not the one its data was written with, and no job ran. The instance still serves: see [The Key Check](configuration_secrets.md#instance-key-check) |

!!! tip "🧑‍💻 Writing the caller"

    - Read the whole body, then parse it as JSON: the spaces before the report are whitespace that
      every JSON parser skips. Check the report's `status`, not only the HTTP status.
    - Do not give up before the run ends. The spaces keep proxies from closing the connection, so an
      idle timeout of 30 seconds or more is safe, but a short total timeout may cut a long run.
    - If the connection drops, the run still goes on to its end, and until then every new call gets
      `409`, or, when it reaches another server process, waits for that run, ten minutes at most
      ([Several Workers](#wake-sync-workers)).
    - After a `409`, try again later, not at once: the run in progress is already doing the updates.
    - A report with `status: "not_leader"` means that no job ran for this call: try again later.
    - Read the fields and the jobs you need, and ignore the ones you do not know.

### 👥 Several Workers {: #wake-sync-workers }

With several server processes (`./dev.py server --workers N`, see
[Start the Server](cli_tools.md#start-the-server)), a call may reach any of them, and any of them
can run the scheduler's jobs. The processes take turns on a lock file in the data directory,
`.scheduler.lock`: one run of the jobs at a time, never two at once.

- **The process that receives the call** runs the jobs that are due, as a single process would.
- **When another process is already running them**, for its check of every minute, say, or for a
  user who came back, the call waits for that run to end, ten minutes at most, then answers: the
  jobs that run has just brought up to date say `not_due`.
- **After ten minutes of waiting**, the call gives up, as it does behind a run of its own process:
  it answers `200` with `status: "not_leader"`, no job runs for it, and the server log has a
  warning, `Scheduler run gave up waiting for another run`. Ten minutes is well past a normal run:
  a run that holds the jobs that long is most likely stuck, so look at the server log.
- **A `409`** (`wake_in_progress`) comes only from a process that is running a wake-up itself: a
  call that reaches another process waits for that run instead, as above. A call that gave up has
  ended its wake-up, so the next call is accepted.
- **`.scheduler.lock`** is an empty file that LibreFolio creates and never deletes: leave it in
  place, and never delete it while LibreFolio runs.

On Windows, the server processes cannot share this lock, so only one of them runs the jobs: the
leader. A call that reaches another process answers `200` with `status: "not_leader"`, and nothing
runs. There, run the server with one process when you use the scheduled wake-up, as
`./dev.py server` does without `--workers`.

### 🔒 A Blocked Instance {: #wake-sync-blocked }

On an instance that its hosting provider has [blocked](hosting_instances.md#instance-block), the
route still answers. The token is checked as usual, and the right one gets `200` with
`status: "blocked"`: no job runs, because a blocked instance does not update its prices and exchange
rates. Once the block is lifted, the next run catches up the history sync missed in the meantime.

---

## 🔄 While Prices Catch Up {: #price-refresh }

Some runs of the [market data scheduler](settings.md#market-data-scheduler) are catch-ups, the runs
someone may be waiting for: they bring the prices and the exchange rates up to date after the server
was off, asleep or left without visitors. A catch-up comes:

- when the server starts;
- at the first request after a minute of silence, the first one after a
  [suspension](sleep_wake.md#idle-suspend-timing) included;
- at a [scheduled wake-up](#wake-sync).

It runs in the background, so the app can be used meanwhile. While one of its jobs runs, the current
price refresh or the history sync ([What a Wake-up Runs](#wake-sync-jobs)), the app shows
**Updating prices…** above its pages. The notice has no close button: it goes away by itself when the
catch-up is over.

- **Nothing due, nothing shown.** When no job is due, the catch-up is over within seconds and no
  notice shows. The scheduler's regular check, every minute, never shows it.
- **Afterwards.** When the catch-up has brought at least one price or rate up to date, a tab that
  showed the notice brings its portfolio pages up to date. A Dashboard or a broker's page on screen
  asks for its figures again by itself, in the background: its figures stay until the new ones
  arrive, with no need to press **Refresh** or to leave the page. The other portfolio pages, such as
  the broker list, and those two when they are not open, ask for their figures again the next time
  they load.
- **The machine can still sleep.** Without a catch-up, the app asks nothing more than usual. During
  one, it asks the server every 3 seconds whether it is over: these questions count as visits, like
  the [live prices](sleep_wake.md#idle-suspend-activity), and pause the same way, in a background tab and after
  two minutes without input. The catch-up itself keeps the machine awake until it ends.
- **Several server processes.** With several (`--workers N`), the jobs run in one of them at a time,
  and only that one's answers tell the app about the catch-up: the notice may not show.

The app learns of a catch-up from a header of the server's answers, `X-LibreFolio-Price-Refresh`: a
reverse proxy that strips the response headers it does not know only loses the notice, and the update
of the portfolio pages that follows it, never the catch-up.

---

## 🔗 Related

- 📄 **[Sleep and Wake](sleep_wake.md)** — Idle Suspension, Check That It Works, Provider Pauses
