# Ingest Registry

> Records every source file ingested into the wiki, with its git hash at ingest time.
> Purpose: detect drift between the ingested snapshot and the current state of the source.
>
> **How to check drift for a source:**
> ```bash
> git diff {hash} HEAD -- {source-path}
> ```
> A non-empty diff means the source has changed since it was ingested.
> Significant changes → consider re-ingesting the source.
>
> For untracked files (external articles, PDFs in raw/): hash = `untracked`, no drift check possible.

| Source Path | Git Hash at Ingest | Date | Wiki Page |
|-------------|-------------------|------|-----------|
| `LibreFolio_developer_journal/knowledge_base/00_project_overview.md` | `f17d963` | 2026-04-24 | [[sources/knowledge-base-overview]] |
| `LibreFolio_developer_journal/RoadmapV4_UI/phases/00-index.md` | `f17d963` | 2026-04-24 | [[sources/roadmap-v4-index]] |
| `LibreFolio_developer_journal/RoadmapV4_UI/plan-phase07-transaction-Part1.md` | `f17d963` | 2026-04-24 | [[sources/phase07-transactions]] |
| `LibreFolio_developer_journal/knowledge_base/05_project_conventions.md` | `957a124` | 2026-04-24 | [[concepts/async-io-rule]], [[concepts/single-migration-strategy]], [[concepts/svelte5-runes]], [[problems/flag-emoji-windows]] |
| `LibreFolio_developer_journal/RoadmapV4_UI/phases/phase-06-subplan/Bugfix-Step4/changelog_2026-04-10_live-ticker-and-provider-lifecycle.md` | `2c448cd` | 2026-04-24 | [[decisions/provider-shutdown-generic]], [[problems/liveticker-header-crash]] |
| `LibreFolio_developer_journal/RoadmapV4_UI/phases/phase-05-subplan/plan-fxSyncApiRedesign.prompt.md` | `f123d4d` | 2026-04-24 | [[decisions/fx-sync-pair-based]] |
| `LibreFolio_developer_journal/RoadmapV4_UI/phases/phase-04-subplan/analysis-brim-multiuser.md` | `84516e3` | 2026-04-24 | [[decisions/brim-broker-scoped]] |
| `LibreFolio_developer_journal/RoadmapV4_UI/phases/phase-04-subplan/plan-data-separation.md` | `f17d963` | 2026-04-24 | [[decisions/prod-test-data-separation]] |
| `LibreFolio_developer_journal/RoadMapV1/01-Riassunto_generale.md` | `f17d963` | 2026-04-24 | [[sources/roadmap-v1-summary]] |
| `backend/app/db/models.py` | `f17d963` | 2026-04-24 | [[entities/db-models]] |
| `backend/app/api/v1/router.py` | `f1205b7` | 2026-04-24 | [[entities/api-router]] |
