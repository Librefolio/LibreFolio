# 🧪 AI Export Probe Workflow

AI Export probes validate the exact prompt copied by the UI against real,
authenticated LibreFolio data. They are measurement and review tools, not
alternative renderers.

They are also separate from the functional test runner. The runner action
`./dev.py test utils ai-export-probe-helpers` executes only fast unit tests for
probe helper code; it never starts the copied database, diagnostic API, frontend
renderer bridge, prompt matrix, or qualitative review.

## 🎯 Source of Truth

The authoritative path is:

```text
runtime catalog
→ official frontend request builder
→ authenticated snapshot API
→ official frontend prompt renderer
→ saved prompt file
→ filesystem measurement and qualitative review
```

The prompt reread from disk is the decision artifact. Canonical backend JSON is
useful for diagnostics, but it is not what the user sends to an AI tool.

UI and probe rendering must match exactly:

- same string;
- same UTF-8 bytes;
- same SHA-256.

## 🧭 Current Entry Points

| Purpose                        | Current source                                                          |
| ------------------------------ | ----------------------------------------------------------------------- |
| Probe orchestration            | `backend/test_scripts/diagnostics/ai_export_real_prompt_probe.py`       |
| Local copied-DB API            | `backend/test_scripts/diagnostics/ai_export_probe_app.py`               |
| Official frontend bridge       | `frontend/scripts/run-ai-export-render-prompt-probe.mjs`                |
| Renderer bridge implementation | `frontend/scripts/ai-export-render-prompt-probe.ts`                     |
| Prompt renderer                | `frontend/src/lib/features/ai-export/templates/promptRenderer.ts`       |
| Snapshot Data renderer         | `frontend/src/lib/features/ai-export/templates/snapshotDataRenderer.ts` |

The official frontend bridge loads the renderer bridge implementation with Vite's
`ssrLoadModule` on a bare server — `$lib` aliased, `$app/environment` and
`$app/navigation` stubbed, no Svelte plugin — so nothing compiles runes: a
module-level `$state` throws `rune_outside_svelte` as soon as its module is evaluated,
and the probe fails. The static import graph of `ai-export-render-prompt-probe.ts`,
the API client (`$lib/api`) included, must therefore reach no `.svelte.ts` module and
no `.svelte` component. The gate `frontend/src/lib/api/apiClientRuneFree.gate.test.ts`
(`./dev.py test front-utility core-unit`) keeps it true: it walks the static imports
of `frontend/src/lib/api/index.ts` and of that entry, and checks that
`zodios-client.ts` imports no such module directly.
{: #frontend-bridge }

The gate follows static runtime imports only: `import type` is erased (an
`import {type X}` is not: `verbatimModuleSyntax` keeps it), and a dynamic `import()`,
which loads its module only when it runs, is not followed. A module that needs runes
on that path is therefore loaded with `import()` where it is used, as the
[price-refresh notice](../../frontend/components/features/live-ticker.md#price-refresh-notice)
is, or keeps its state in a plain module behind a reactive face, as the
[instance block](../../frontend/state/app-state.md#instance-block) does.

Paths and flags may evolve. Inspect the current files and command help before every
new tuning session:

```bash
pipenv run python backend/test_scripts/diagnostics/ai_export_real_prompt_probe.py --help
```

## 🧰 Probe Types

| Type            | Typical scope                                                         |
| --------------- | --------------------------------------------------------------------- |
| Smoke           | One cheap selection proving the pipeline works.                       |
| Targeted        | Exact cases affected by one correction.                               |
| Full tuning     | Current standard matrix for catalog-wide validation.                  |
| Comparison      | Current stable keys against a prior `metrics.json`.                   |
| Task Adequacy   | Semantic scoring of real Analysis prompts.                            |
| Partial history | Controlled copy with incomplete source history and explicit coverage. |

Prefer targeted probes during iteration. Use a full tuning run only when the
catalog-wide result is materially affected or when selecting a new authoritative
corpus.

## 🧩 Standard and Public-Catalog Matrices

The current standard profile is `tuning-v2`. It discovers the runtime catalog and
applies the current dataset/Analysis matrices. Do not copy a historical expected
count: inspect the catalog recorded in `run_manifest.json`.

The release-validation profile is `public-catalog-v1`:

```text
19 public selections × {3M, 1Y} × {Compact, Standard, Full} = 114 prompts
```

It measures every prompt but permanently retains only approved named cases plus
nearest minimum, maximum, median, P10, P25, P75, P90, P95, and P99 stable keys.
`metrics.json` retains all rows; unretained rows have `prompt_file = null`.

Targeted cases use the current repeatable target-case syntax:

```text
USER|SELECTION_ID|PERIOD|DETAIL|SCOPE
```

Current scope selectors include:

- `all` for the whole Portfolio scope;
- `broker=<display name>` for one exact accessible Broker;
- `representative` for the probe's deterministic representative scope in the
  selected domain.

Targeted comparison considers only the requested stable keys. Unselected cases in
the previous run are not reported as removals.

Use only syntax shown by the current `--help`.

## 🔐 Copied Database and Credentials

The probe:

1. hashes the local production SQLite family;
2. creates an immutable source snapshot;
3. creates a disposable runtime copy;
4. starts a local API on the copy;
5. authenticates and renders prompts;
6. verifies source and production hashes after the run.

Credential normalization, when requested, affects only the disposable copy.
Passwords come from approved local environment handling and are included in the
secret scan. Never put real credentials in documentation, skills, reports, or
committed scripts.

A production writer may be active while the probe runs. The manifest records
detected processes and distinguishes external production drift from copied-DB
writes.

## 🗂️ Scope Selection

Choose the smallest representative set that tests the changed behavior:

- full Portfolio or a deliberate Broker subset;
- Broker with recorded costs and Broker without costs;
- current-position, inactive-scoped, and historical-contributor Broker cases;
- data-rich Asset and multi-Broker Asset;
- representative FX pair;
- complete and partial source histories;
- FIFO-relevant scope.

Artifact user and scope names are anonymized. Public prompt joins use A#, B#, F#,
and L# references. The Entity Directory resolves A#, B#, and F# references to
readable names: Asset display names and identifiers, Broker display names, and the
FX pair label. L# references have no directory entry: each is the backend-assigned
`lot_ref` of one FIFO lot row, read in place, and the row links to its opening
Broker by B# and, in Portfolio and Broker exports, to its Asset by A#.

## 📏 Metrics

Per prompt, `metrics.json` records:

- rendered characters, bytes, lines, words, chars/4 estimate, and hash;
- size category and technical share;
- section, dataset, and component breakdown;
- history and event-family counts;
- coverage, eligible/covered entities, weights, omission and partial reasons;
- empty temporal rows detected, omitted, and remaining;
- Broker scope refs plus scoped/current-position/period-contributor counts;
- renderer equivalence;
- HTTP/failure status.

`chars / 4` is a stable estimate, not a model tokenizer. One prompt is one user
request. Corpus totals are diagnostic only.

For larger cohorts review minimum, median, P75, P90, P95, and maximum. A reduction
in size is not automatically an improvement.

## 🧹 Public Empty-Row Policy

Backend bucket boundaries and calculations remain unchanged. The public renderer
omits a temporal row only when:

- it has only nominal bucket boundaries/index metadata;
- `has_data` is false or the row otherwise contains no observed state;
- every economic, performance, flow, reconciliation, extrema, and observed-date
  value is absent.

Observed zero is meaningful and remains public. A flow, P&L, extrema, variation,
reconciliation, observed date, or explicit non-absence status keeps the row.

The renderer reports:

- `empty_temporal_rows_detected`;
- `empty_temporal_rows_omitted`;
- `temporal_rows_rendered`.

Requested/effective/available periods, coverage, and insufficient-history warnings
remain outside the omitted rows and must stay visible.

Columns have their own rule: a compact table removes a column that is empty or `null`
in every row, and names the removed columns that held a `null` on an
`omitted_null_columns=` line right after the table (see
[Snapshot Data Tables](ai_export_composition.md#snapshot-data-tables)). The renderer
reports:

- `empty_columns_removed`, every removed column;
- `empty_parent_columns_removed`, the removed columns that were the parent of nested
  columns (counted in both);
- `null_columns_declared`, the names written on `omitted_null_columns` lines.

A column `null` in every row is therefore named even though no row shows it; a fact to
be counted belongs in a SUMMARY field, as `unavailable_amount_lot_count` does for lot
amounts without an FX rate. The counters are part of each prompt's
`format_diagnostics`, and the public table audit, which reads only `|…|` rows, still
rejects a prompt that contains an all-empty column. When reading a prompt, check that
each `omitted_null_columns` line names fields the payload really leaves unavailable,
and that no column the scope does not apply to is named — neither an `undefined` one nor
one whose `null` means "none" (`NULL_MEANS_NONE_COLUMNS`, such as an open lot's
`closing_date`).

## 🏦 Broker Universe Diagnostics

Portfolio prompts distinguish:

| Field                             | Meaning                                                       |
| --------------------------------- | ------------------------------------------------------------- |
| `scoped_broker_count`             | Brokers selected for the calculation after access validation. |
| `broker_scope`                    | The same scope rendered as B# references.                     |
| `position_broker_count`           | Brokers with current open positions at `snapshot_as_of`.      |
| `period_contributor_broker_count` | Brokers represented by period performance contributors.       |

A scoped Broker may have no current position. A historical contributor may differ
from the current-position universe. The Entity Directory must contain every scoped
Broker, including all-accessible requests without an explicit Broker filter.

## 🧠 Qualitative Review and Task Adequacy

Metrics locate candidates; they do not replace reading prompts.

For broad runs inspect minimum, median, P90, maximum, financial, focused-context,
technical, partial-history, unavailable-data, Additional Data, FIFO, and FX cases.
For targeted runs, read every prompt.

Task Adequacy uses:

| Axis                       | Points |
| -------------------------- | -----: |
| Deterministic completeness |     25 |
| Task relevance             |     25 |
| Semantic clarity           |     15 |
| Coverage and limits        |     15 |
| Density/information        |     10 |
| Additional Data usability  |     10 |

Ratings are `INSUFFICIENT`, `SUFFICIENT`, and `OPTIMAL`.

User-only inputs do not reduce completeness when the prompt asks only material
questions, distinguishes indispensable from optional answers, supports conditional
scenarios, and never invents preferences. Unavailable source data is not zero and
must disable dependent conclusions.

## 📦 Run Artifacts

Each timestamped run contains the current subset of:

```text
real_prompt_probe/<run_id>/
├── prompts/
├── canonical/
├── metrics.json
├── failures.json
├── run_manifest.json
└── summary.md
```

Additional review artifacts may be added for a specific task. Do not mix a targeted
run into a previously authoritative full corpus.

Public V1 runs additionally contain `retained_prompt_manifest.json`, deterministic
SVG charts, structured review artifacts, and comparison manifests. Artifact user
labels and prompt filenames are anonymized.

## 🚨 Troubleshooting

| Symptom                       | Check                                                                                   |
| ----------------------------- | --------------------------------------------------------------------------------------- |
| UI/probe mismatch             | Confirm both paths call the official renderer and use the same locale/catalog/snapshot. |
| False removed comparisons     | Confirm the run is targeted and current-only comparison mode is active.                 |
| Production hash changed       | Inspect concurrent-writer records before attributing drift to the probe.                |
| Partial history shown as full | Compare requested/available dates, coverage, warning, and omission reasons.             |
| Raw IDs in prompt             | Check Entity Directory seeding and generic reference mapping.                           |
| Size fell unexpectedly        | Check omitted rows/components/datasets and read the actual prompt before accepting.     |
| Cost shown as zero            | Verify typed source rows and recorded/unavailable/not-applicable status.                |

## 🔗 Related Documentation

- [AI Export Runtime](ai_export_snapshot.md)
- [Composition and Prompt](ai_export_composition.md)
- [Technical Sampling](ai_export_sampling.md)
- Project skill: `.github/skills/ai-export-probe-tuning/SKILL.md`
