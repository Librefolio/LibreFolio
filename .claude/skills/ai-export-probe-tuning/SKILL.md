---
name: ai-export-probe-tuning
description: "Use this skill when changing AI Export components, datasets, analyses, contracts, renderer, sampling or event policy, or when running smoke, targeted, full, comparison, partial-history, or Task Adequacy probes."
---

# AI Export Probe Tuning

> Stable workflow for measuring and reviewing the prompt that LibreFolio actually copies.

## Authoritative References

Read these pages before choosing commands, files, or runtime identities:

- [AI Export runtime](../../../mkdocs_src/docs/developer/architecture/patterns/ai_export_snapshot.md)
- [Composition and prompt](../../../mkdocs_src/docs/developer/architecture/patterns/ai_export_composition.md)
- [Technical sampling](../../../mkdocs_src/docs/developer/architecture/patterns/ai_export_sampling.md)
- [Probe workflow](../../../mkdocs_src/docs/developer/architecture/patterns/ai_export_probe_workflow.md)

Then inspect the current implementation, tests, runtime catalog, and command help.
Historical reports are evidence, not the source of truth.

## When to Use

Use this skill for:

- component or dataset changes;
- Analysis composition, instruction, or response-contract changes;
- renderer or public-format changes;
- sampling or event-policy changes;
- dimensional tuning;
- Task Adequacy Review;
- validation on real Portfolio, Broker, Asset, or FX cases;
- partial-history or unavailable-data debugging;
- UI/probe equivalence checks;
- comparison between candidate and authoritative runs.

Do not use it for:

- unrelated unit tests;
- visual-only changes that cannot affect copied text;
- documentation-only edits with no runtime claim to validate;
- a full run when a targeted probe proves the requested behavior.

## Documentation and Code Divergence

If MkDocs documentation, current code, tests, the runtime catalog, or observed
probe behavior disagree:

1. do not silently rewrite the documentation;
2. do not assume the code is automatically correct;
3. identify the competing sources and affected behavior;
4. explain the impact and likely correction;
5. ask whether the MkDocs page should be updated unless the current task explicitly
   authorizes that update.

When the task authorizes the affected page, verify the discrepancy, determine the
correct source, update the page, and record the correction in the report. Do not
modify pages outside the authorized scope.

## Probe Types

| Probe | Use |
|---|---|
| Smoke | One inexpensive case proving request → snapshot → renderer works. |
| Targeted | Exact user, selection, period, detail, and scope cases for one change. |
| Full tuning | Current standard matrix across supported domains and selections. |
| Comparison | Stable-key comparison against an authoritative metrics file. |
| Task Adequacy | Semantic review of real Analysis prompts using the project rubric. |
| Partial history | Controlled copied-DB case with deliberately incomplete source history. |

Always choose the smallest probe that proves the behavior. Escalate only when the
targeted evidence is insufficient.

## Functional Test Boundary

- A real prompt probe is never part of the normal test runner.
- `./dev.py test utils ai-export-probe-helpers` runs fast unit tests for probe
  parsing, metrics, security, retention, and comparison helpers only.
- Functional backend/frontend tests verify contracts, composition, safety,
  rendering structure, and clipboard behavior. They must not freeze prompt
  wording or treat a changed cross-run prompt hash as a failure.
- UI and probe rendering of the same current input must remain byte-identical.
- Cross-run prompt SHA-256 changes are review signals for the separate
  qualitative/Task Adequacy workflow, not functional regressions by themselves.

## Renderer Source of Truth

- The final prompt copied by the UI is authoritative.
- The frontend probe must call the same request builder and prompt renderer.
- Python orchestrates authentication, HTTP, copied databases, files, hashes, and metrics.
- Python must not reimplement Markdown/YAML/table rendering.
- UI and diagnostic rendering must match exactly, including UTF-8 bytes and SHA-256.
- Canonical backend JSON is diagnostic input, not the user prompt.

Verify current paths and symbols in the MkDocs probe guide and source code before
using them.

## Database and Security

1. Use a copied database and a local diagnostic API.
2. Do not intentionally write to the production source.
3. Hash the source SQLite family before and after.
4. Record concurrent production writers separately from probe writes.
5. Normalize credentials only on the disposable copy when explicitly needed.
6. Supply credentials through approved local environment handling; never put real
   credentials in this skill, reports, commands committed to the repository, or artifacts.
7. Run the secret scan.
8. Use anonymized artifact aliases and public A#/B#/F#/L# references.
9. Keep failed/intermediate runs when cleanup is outside scope.

## Scope Selection

Avoid a Cartesian product. Select cases that answer the current question:

- full Portfolio or a deliberate Broker subset;
- a Broker with costs and one without costs;
- a data-rich Asset;
- an Asset held across multiple Brokers;
- a representative FX pair;
- complete and insufficient histories;
- a FIFO-relevant scope;
- current-position, inactive-scoped, and historical-contributor Broker cases.

For current CLI syntax:

1. read the MkDocs probe guide;
2. inspect the diagnostic entry point;
3. run its `--help`;
4. use only supported options;
5. record the actual command and cases in the report.

Do not copy old flags or commands from historical reports without verification.

## Metrics

Measure per prompt:

- rendered characters, UTF-8 bytes, lines, words, chars/4 estimate, and SHA-256;
- technical share;
- section, dataset, and component breakdown;
- history rows;
- detailed, context, latest-category, and digest event counts;
- requested/available period and coverage;
- eligible and covered entities/weights;
- omission and partial reasons;
- empty temporal rows detected, omitted, and remaining;
- Broker scope and explicit Broker-universe counters;
- failure/status codes;
- UI/probe equivalence.

`chars / 4` is only a stable estimate, not a tokenizer. One copied prompt is the
decision unit. Corpus totals are diagnostic. Review minimum, median, P75, P90, P95,
and maximum where the cohort is large enough.

A smaller prompt is not automatically better.

## Qualitative Review

Read real prompts, not only metrics. For broad runs inspect at least:

- minimum;
- median;
- P90;
- maximum;
- pure financial;
- financial with focused context;
- explicit technical;
- missing/unavailable data;
- partial history;
- Additional Data guidance;
- FIFO;
- FX.

For targeted runs, read every generated prompt.

## Task Adequacy

Classify each Analysis as:

- `INSUFFICIENT`;
- `SUFFICIENT`;
- `OPTIMAL`.

Score:

| Axis | Points |
|---|---:|
| Deterministic completeness | 25 |
| Task relevance | 25 |
| Semantic clarity | 15 |
| Coverage and limits | 15 |
| Density/information | 10 |
| Additional Data usability | 10 |

Missing information that only the user can provide does not automatically reduce
deterministic completeness. Evaluate whether the prompt asks only material
questions, separates indispensable inputs from optional refinements, supports
conditional scenarios, and never invents preferences.

Likewise, genuinely unavailable source data is not a prompt defect when the prompt
distinguishes unavailable from zero and disables dependent conclusions.

## Iterative Workflow

```text
read MkDocs
→ verify current code, tests, catalog, and --help
→ choose the smallest probe
→ generate
→ measure
→ read real prompts
→ identify a factual or contract problem
→ correct the owning layer
→ rerun only necessary cases
→ compare stable keys
→ rerate
→ select the authoritative run
→ report and stop for review
```

Use the backend for deterministic calculations, semantic selection, coverage, and
status. Use the frontend for official rendering, presentation, localization, and
Additional Data guidance.

## Errors to Avoid

- measuring canonical JSON as the final prompt;
- implementing a second renderer;
- running the full matrix after every small correction;
- treating the whole corpus as one AI request;
- relying only on averages;
- adding financial calculations or semantic selection to the frontend;
- hiding partial history;
- converting unavailable to zero;
- silently omitting observed zero values;
- adding silent token caps;
- freezing commands, flags, classes, or counts in this skill;
- copying historical implementation details without verification;
- updating out-of-scope documentation automatically;
- committing, cleaning, or releasing before review;
- including secrets.

## Completion Checklist

1. Correct probe type and cases selected.
2. Source DB integrity and concurrent-writer status recorded.
3. Secret scan passed.
4. UI/probe bytes and hashes match.
5. Prompt files saved with anonymized artifact names.
6. Required metrics persisted.
7. Real prompts read qualitatively.
8. Comparison includes only the intended cohort.
9. Rating reflects information adequacy, not size.
10. Authoritative run and report identified.
