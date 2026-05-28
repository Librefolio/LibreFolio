# LibreFolio — Copilot Instructions

## What is LibreFolio

LibreFolio is a **self-hosted, open-source financial portfolio tracker** — alternative to Ghostfolio. It supports traditional assets (ETFs, stocks, bonds, crypto), multi-provider FX rates, technical analysis (EMA, MACD, RSI, Bollinger), and import from 11+ brokers.

## Tech Stack

| Layer | Technology | Details |
|-------|-----------|---------|
| **Backend** | Python 3.13 + FastAPI | SQLModel/SQLite, Alembic, Pipenv |
| **Frontend** | SvelteKit 2 + Svelte 5 | Tailwind CSS 4, ECharts 6, Zodios, Playwright |
| **Docs** | MkDocs Material | i18n (suffix strategy), Mermaid, LaTeX (KaTeX) |
| **Deploy** | Docker single-image | Backend serves frontend as static files |
| **CLI** | `dev.py` | Single entry point for everything |

## Project Structure

```text
LibreFolio/
├── backend/           # Python FastAPI (API, DB, services, providers)
├── frontend/          # SvelteKit SPA (routes, components, stores, i18n)
├── mkdocs_src/        # Documentation (MkDocs Material, i18n)
├── scripts/           # CLI tools (imported by dev.py)
├── dev.py             # Main CLI — ALWAYS use this, never manual commands
└── .github/           # Copilot instructions, skills
```

## Key Architectural Decisions

1. **All calculations in Backend** — the frontend is pure presentation
2. **FIFO at Runtime** — cost matching computed on-demand, not persisted
3. **Provider Registry Pattern** — auto-discovery for FX, Asset and BRIM providers with `params_schema` for dynamic forms
4. **Multi-Provider with Fallback** — FX rates from ECB→FED→BOE→SNB + MANUAL sentinel
5. **Svelte 5 Runes** — `$state`, `$derived`, `$effect` in new components
6. **Zodios API Client** — types from OpenAPI, Zod runtime validation
7. **Data Separation prod/test** — completely isolated folders
8. **Dual View** — card grid + DataTable for Assets and FX, toggle persisted in localStorage

## Fundamental Rules

- **Caveman mode ultra** — always active. Use `caveman` skill at `ultra` intensity. Max compression, abbrevs, arrows for causality (X → Y). Off only if user says "stop caveman" or "normal mode".
- **ALWAYS use `./dev.py`** for complex operations — never manual commands
- **No backward compatibility** — clean up instead of maintaining legacy
- **Code in English** — comments, docstrings, variables, README
- **Multilingual UI** — only the graphical interface in EN/IT/FR/ES
- **Edit > Rewrite** — prefer targeted edits to avoid regressions
- **No incremental Alembic migrations** — modify `001_initial.py` and recreate DB with `./dev.py db create-clean`
- **After modifying API** — run `./dev.py api sync` to regenerate TypeScript client
- **After modifying DB models** — run `./dev.py db create-clean`
- **NEVER run `git commit`** — the agent must only *propose* commit messages
  (e.g. write them to `/tmp/libreFolio_commit_*.txt` or print them inline).
  The user performs the actual commit manually. Staging (`git add`) and read-only
  git commands (`git status`, `git diff`, `git log --no-pager`) are allowed.
  Same rule for `git push`, `git reset --hard`, `git rebase`, `git checkout -- …`
  and any other history-mutating operation: **never** execute, only suggest.

## Terminal Command Rules

- **Long commands (>10 lines)** → do NOT paste them directly into the shell. Instead, write the command/script to a temporary file under `/tmp/` (e.g. `/tmp/libreFolio_<descr>.sh` or `.py`) and execute that file. This avoids quoting/escape issues and keeps the terminal log readable.
- **Truncated output (`tail`, `head`, `grep -m`, `| head -n`, etc.)** → always `tee` the full output to a file in `/tmp/` *before* truncating, so the complete log can be re-inspected without re-running the command. Pattern:
    ```bash
    <command> 2>&1 | tee /tmp/libreFolio_<descr>.log | tail -n 100
    ```
    Then, if more context is needed, read `/tmp/libreFolio_<descr>.log` instead of re-executing the command.
- **Rationale**: avoid re-running expensive commands (tests, builds, db operations) just to see output that was truncated earlier.

## Async I/O Rule (Event Loop Safety)

In `async def` handlers, **every sync library doing I/O** MUST be wrapped in `await asyncio.to_thread(...)`. Never call `requests.get()`, `yf.Ticker().info`, etc. directly — they block the entire event loop. If an endpoint only does light sync I/O (e.g. `Path.exists()`), define it as `def` (not `async def`).

## Frontend Conventions

- **Svelte 5 Runes**: use `$state()`, `$derived()`, `$effect()` — never old `$:` reactive
- **Tailwind CSS 4**: config via `@theme {}` in `app.css` — no `tailwind.config.ts`
- **Dark mode**: `html.dark` with Tailwind `dark:*` classes
- **Icons**: lucide-svelte
- **Selectors**: always use `data-testid` — never CSS classes or text (fragile with i18n)
- **Flag emoji**: use `Noto Color Emoji` web font for Windows compatibility

## Developer Journal & Plan Methodology

Development history is tracked in `LibreFolio_developer_journal/`. We follow a structured plan-driven workflow:

1. **Plan** → create a detailed implementation plan (`.prompt.md`)
2. **Execute** → implement the plan
3. **Repeat: BugfixPlan + Execute** → for each issue, create a bugfix plan and execute it
4. **Debug** → final verification pass

### File Naming Convention

Plans are saved with an ordered naming scheme that encodes phase, step, iteration, and bugfix round:

```
plan-phase{NN}{Description}.prompt.md              # Main plan
plan-phase{NN}Step{N}{Description}.prompt.md        # Step-level plan
plan-phase{NN}BugfixMigration.prompt.md             # Bugfix iteration
plan-phase{NN}Step{N}Round{N}-{Description}.prompt.md  # Bugfix round N
plan-phase{NN}Step{N}Round{N}{Suffix}.prompt.md     # Sub-iteration (e.g. part2, part3b)
```

When a plan spawns a follow-up, both files cross-link each other (the original links forward, the new one links back).

### Plan Execution — Progress Tracking Rule

When executing a plan, after completing **EVERY step**, immediately return to the plan `.prompt.md` file and:
1. Mark the step as ✅ completed with date
2. Add a line `> **Note implementazione**: ...` describing what was done
3. If there were **detours** (unexpected fixes, discoveries, errors), note them with `> **⚠️ Fuori pista**: ...`

**Do not wait until the end** — update after each step. If context resets mid-execution, nothing is lost.

### Archive Structure

Completed plan chains are moved into `LibreFolio_developer_journal/RoadmapV4_UI/phases/`:

```
phases/
├── phase-{NN}-{name}.md          # Summary plan for the phase
├── phase-{NN}-subplan/           # All sub-plans, bugfix rounds, checklists
│   ├── README.md                 # Index of all sub-plans with status
│   ├── Bugfix-Step{N}/           # Grouped by step
│   │   ├── plan-phase{NN}...md
│   │   └── checklist-...md
│   └── ...
└── 00-index.md                   # Master index of all phases
```

Each `phase-{NN}-subplan/README.md` contains a table of all sub-plans with step, description, and status (✅/⏳).

### Skills

Use the `plan-archive` skill for plan verification and archiving operations (see `.github/skills/planning/plan-archive/SKILL.md`).

Use the `find-skills` skill when looking for new capabilities to install (see `~/.github/skills/find-skills/SKILL.md`).

## Persistent Knowledge Layer (devWiki)

`LibreFolio_devWiki/` is the accumulated knowledge base for this project — decisions, patterns, problems solved, entity documentation. It is NOT the source of truth (code is) and NOT user docs (mkdocs is). It is the living memory that compounds across sessions.

**For the main dev agent**, two wiki skills are available:

| Skill | When to Use |
|-------|------------|
| `wiki-search` | At the **start** of a task — enrich context with accumulated knowledge before coding |
| `wiki-file` | At the **end** of a session — preserve discoveries, solved problems, decisions made |

**Rule**: before touching code in a domain with prior history (providers, FIFO, async I/O, EditBuffer, FX, etc.), run `wiki-search` first to avoid re-deriving what's already been learned.

**Historian agent**: for full wiki operations (ingest sources, query the wiki, health-check), invoke the `project-historian` agent — the workflows are embedded directly in that agent's instructions.

### Graphify Knowledge Graph

The devWiki is backed by a **graphify knowledge graph** (`LibreFolio_devWiki/graphify-out/graph.json`) — 9259 nodes, 14151 edges, 748 communities covering backend, frontend, wiki, roadmap and docs.

- `wiki-search` uses graphify BFS/DFS as primary lookup (much faster than reading raw files)
- `./dev.py graph update` — incremental code-only rebuild after code changes (no LLM, ~5s)
- `./dev.py graph viz` — regenerate `graph.html` for browser visualization
- `./dev.py graph query "TOPIC"` — quick BFS query from the CLI
- Full semantic rebuild (new .md files): invoke the `graphify` skill through the AI assistant

## Test Users

| Username | Password | Role |
|----------|----------|------|
| `e2e_test_user` | `E2eTestPass123!` | Normal user |
| `e2e_test_admin` | `E2eAdminPass123!` | Admin |

## Ports

| Port | Service |
|------|---------|
| 6040 | Backend production |
| 6041 | Backend test mode |
| 6042 | MkDocs serve |
| 5173 | Frontend dev (Vite HMR) |

