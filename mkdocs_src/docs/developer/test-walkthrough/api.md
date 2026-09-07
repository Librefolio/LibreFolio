# 📡 API Endpoint Tests (`api`)

These are integration tests that run against a live backend server. They verify the full request-response cycle.

## 🎯 Purpose

To ensure that the API endpoints are reachable, return the correct status codes, and produce the expected JSON responses.

## ✅ Prerequisites

**Do not start a server.** The runner starts one, once, and every module talks to it over
`API_BASE`. A module that starts its own uvicorn takes port 6041 from everyone else and makes the
whole category serial by construction. The only thing to check before a run is that the port is
free: `lsof -ti:6041` must come back empty.

That single shared backend is what lets the category run concurrently — and what makes the run test
something the old design could not: **whether the application actually holds up under concurrent
requests**. It has already answered twice, both times with a product defect rather than a test one
(a cache that silently stopped caching, and a SQLite `busy_timeout` left at zero so a second writer
failed instead of waiting).

## ⛔ The semantics: verify, never assume

Modules share one database, and now share it *at the same time*. Three consequences, normative in
`.github/instructions/backend-testing.instructions.md`:

- **Never identify data by position.** `response.json()[0]` is a claim about everybody else's rows.
  Search the response for the id you created.
- **Never assert a count you did not create.** `len(items) == 4` breaks the moment a neighbour adds
  one; `len([i for i in items if i["id"] == mine]) == 1` says what you mean.
- **Never reach a third party over the network.** A test that calls the real ECB is testing today's
  weather. `MOCKFX` and `MOCKFX_FAIL` exist for this, and return fixed values — which lets the
  assertion be exact instead of "some number arrived".

A unit that genuinely cannot share the database declares `exclusive_because=` with the surface it
mutates. There is currently **one** in the whole backend; see `runner_architecture.md` for what
justifies a second.

## 🔑 Key Tests

- **Auth**: Login, token refresh, protected routes.
- **Assets CRUD**: Create, read, update, delete assets via API (19 tests).
- **Assets Metadata**: Classification params, sector/geo distributions (4 tests).
- **Assets Patch**: Partial field updates including identifiers (8 tests).
- **Assets Provider**: Provider assignment, probe with valid/invalid params, Scheduled Investment via API (16 tests).
- **Assets Prices**: Bulk upsert, query with backward-fill, sync idempotency, events in response, bulk multi-asset sync (9 tests).
- **FX**: Currency pair CRUD, conversion, sync, delete (25+ tests).
- **Brokers**: CRUD, sharing, multi-user access control.
- **Transactions**: Import and manage transactions.
- **Uploads**: File upload and media management.
- **Settings**: Global and user settings.
- **Utilities**: Country codes, currency utils.
- **AI Export API**: Runtime catalog, versioned snapshots, authorization,
  applicability, typed problems, and cross-domain request contracts.

## 🧠 AI Export Test Stack

AI Export spans API, service, probe, frontend unit, and live Playwright layers:

```bash
# Catalog, snapshots, authorization, typed API problems
./dev.py test api ai-export

# Backend components, datasets, analyses, sampling, runtime, and composition
./dev.py test services ai-export

# Strict request/response/catalog schemas
./dev.py test schemas ai-export

# Fast unit tests for probe helpers; does not run a real prompt probe
./dev.py test utils ai-export-probe-helpers

# Frontend runtime, renderer, clipboard, memory, and Signal unit tests
./dev.py test front-ai-export unit

# Focused live UI concerns
./dev.py test front-ai-export panel
./dev.py test front-ai-export catalog
./dev.py test front-ai-export memory
./dev.py test front-ai-export contract

# Compatibility alias for all four Playwright concerns
./dev.py test front-ai-export cutover

# Canonical frontend AI Export gate: unit + Playwright
./dev.py test front-ai-export all

# Ensure every remaining test file is registered
./dev.py test check-orphans

# Accumulate backend AI Export coverage
./dev.py test --cov-clean-backend --coverage services ai-export
./dev.py test --coverage schemas ai-export
./dev.py test --coverage api ai-export
./dev.py test --coverage utils ai-export-probe-helpers
```

## 🚀 Running

```bash
# All API tests
./dev.py test api all

# AI Export API only
./dev.py test api ai-export
```
