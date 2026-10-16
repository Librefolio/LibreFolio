# 💤 Sleep and Wake

LibreFolio does not have to run around the clock. The machine it runs on can be suspended when
nobody uses it, or switched off at night, and started again later: by a hosting panel, on its own
schedule, or by a script or a cron job of yours on a home server. While the machine sleeps, nothing
updates the prices and the exchange rates; the
[market data scheduler](settings.md#market-data-scheduler) catches up once it runs again.

Whoever wakes the machine can also bring the data up to date at once, and know when it is done,
with one call: the **scheduled wake-up**.

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
  due.
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
    such as a Docker secret (`/run/secrets/wake_token`): see «Secrets in Files» in
    [Environment Variables](configuration.md). When both are set, `LIBREFOLIO_WAKE_TOKEN` wins.

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

LibreFolio checks the token when the route is called, not at startup. A token it cannot use (too
short, with a space or a character outside ASCII, or a `LIBREFOLIO_WAKE_TOKEN_FILE` that is
missing, unreadable or empty) does not stop the server: the route answers `503` to every call, and
each call logs this error, with the variable and what is wrong, never the token:

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
| `not_leader` | This server process does not run the jobs, and no job ran: see [Several Workers](#wake-sync-workers) |
| `blocked` | The hosting provider blocked the instance, and no job ran: see [A Blocked Instance](#wake-sync-blocked) |

!!! tip "🧑‍💻 Writing the caller"

    - Read the whole body, then parse it as JSON: the spaces before the report are whitespace that
      every JSON parser skips. Check the report's `status`, not only the HTTP status.
    - Do not give up before the run ends. The spaces keep proxies from closing the connection, so an
      idle timeout of 30 seconds or more is safe, but a short total timeout may cut a long run.
    - If the connection drops, the run still goes on to its end, and until then every new call gets
      `409`.
    - After a `409`, try again later, not at once: the run in progress is already doing the updates.
    - Read the fields and the jobs you need, and ignore the ones you do not know.

### 👥 Several Workers {: #wake-sync-workers }

With several server processes (`./dev.py server --workers N`), only one of them runs the
scheduler's jobs: the leader. A call may reach any of them, and one that reaches another process
answers `200` with `status: "not_leader"`: nothing runs. When you use the scheduled wake-up, run the
server with one worker: the Docker image does, and so does `./dev.py server` without `--workers`
([Start the Server](cli_tools.md#start-the-server)).

### 🔒 A Blocked Instance {: #wake-sync-blocked }

On an instance that its hosting provider has [blocked](hosting_providers.md#instance-block), the
route still answers. The token is checked as usual, and the right one gets `200` with
`status: "blocked"`: no job runs, because a blocked instance does not update its prices and exchange
rates. Once the block is lifted, the next run catches up the history sync missed in the meantime.

---

## 🔗 Related

- 📝 **[Environment Variables](configuration.md)** — `LIBREFOLIO_WAKE_TOKEN`, and secrets in
  files such as Docker secrets
- 🏢 **[Hosting for Others](hosting_providers.md)** — The managed profile, and blocking an instance
- 🕐 **[Global Settings](settings.md#market-data-scheduler)** — The market data scheduler: its
  schedule and its log
- 🧑‍💻 For developers: **[Market Data Scheduler](../developer/backend/scheduler.md)** — How a run
  works: its checks, its lock and its report
