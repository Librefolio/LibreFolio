---
title: "Allocation tab: filter by content, pie by family, its own endpoint on the page's engine run"
category: decision
status: resolved
date: 2026-11-24
tags: [dashboard, broker, allocation, asset-types, financial-math, api, honesty, issue-89]
related: [decisions/asset-type-two-level-taxonomy, decisions/one-colour-rank-per-asset, entities/asset-profile-enrichers]
---

# Decision: the «Allocazione» tab filters by content, draws by family, and has its own endpoint

## Context

Issue #89 (22/11/2026) asked for two things on the allocation charts:

- **filters**, for example the geography of the equity part only;
- **exclusions** with the percentages recomputed, for example without an asset whose sectors are unknown, or without
  «Altro».

The Dashboard's allocation card could not answer either one. The replay kept three independent totals per day
(`by_type`, `by_sector`, `by_geography`), with no cross between them. The card also stood beside whole-portfolio KPIs,
so a filtered pie there would read as the whole portfolio.

The developer chose a fifth tab, «Allocazione», between Positions and Risk. It sits on the Dashboard and on every
broker page (proposal C2 of project 80, 23/11/2026). It is also a home for future analyses.

## Options considered

1. **The class filter, by family or by content.**
   - By **family** (`assetTypeFamily`: `ETF_STOCK` → ETF), as the pie and the history have grouped since D15. Then
     «equity only» would leave out an equity ETF, and the issue's own example would fail: equity is mostly held
     through ETFs.
   - By **content** (`primaryAssetType` / `asset_type_content`: `ETF_STOCK` → STOCK). This is the question «what am
     I exposed to?».
2. **Where the numbers come from.**
   - A field added to `POST /portfolio/report`.
   - A dedicated `POST /portfolio/allocation`, as the Risk tab has its own calls.
3. **How a re-based percentage is shown.** Quietly re-normalised slices, as an ECharts legend click does today, or a
   base that is always declared.

## Decision

- **The filter goes by content; the charts keep the family.**
  - An asset's class is `asset_type_content` (`services/assets/type_rules.py`, beside `asset_type_family`). A test
    reads the frontend's `PRIMARY_TYPE_MAP` and checks that the two maps agree.
  - The pie and the type dimension still group by family (D15, [[decisions/asset-type-two-level-taxonomy]]). So under
    «Azioni» the Type tab shows how the equity is held: shares against equity ETFs.
  - Liquidity is a class only, never an excludable bucket: one control per meaning.
- **The tab has its own endpoint, but not its own replay.**
  - `POST /portfolio/allocation` (`services/portfolio/allocation.py`) reads the page's engine run through `_engine_run`
    (FB-14). That run has the same blob-cache key as the report of that period and scope.
  - A change of filter or dimension therefore builds only the derived view; nothing is replayed
    (`test_the_allocation_views_after_the_report_build_nothing`).
  - `PortfolioCalculationResult` now carries `asset_types` and `asset_classifications`, the maps the replay read.
- **The calculation lives in `financial_math/portfolio/allocation_view.py`, with one split of value.**
  - `daily_state.allocation_parts` is the split the replay uses for its own `by_type`, `by_sector` and
    `by_geography`, and the view reuses it.
  - With no filter, the view's slices are the state's slices.
  - Shares are computed only by `weights.slice_percents` and `percent_of`. The frontend computes nothing
    (`features/allocation/allocationView.ts` only reads the backend's strings for drawing).
- **The base is always declared.** The identity `base + outside + excluded = NAV` holds, with NAV equal to the KPI
  «Patrimonio netto».
  - **Outside:** what the class filter leaves out.
  - **Excluded, the user's choice:** an asset excluded whole, or an asset's part in `Unknown` or `Other`. An excluded
    bucket applies only in a dimension where it exists.
  - **Excluded, fixed rows with a reason:** securities in transit (the state holds no asset for them) and the cash in
    the geography (no country).
  - Three tiles and a two-column table show it all: the % of the selection and the % of the portfolio.
- **The matrix (class × the chosen dimension) shows the whole portfolio.** It has a Liquidity row where cash has a
  bucket, and the unattributed amounts bring its sum back to the NAV. The asset dimension has no matrix.
- **Filters are remembered per page**: the Dashboard keeps its own, and each broker its own. On the Dashboard card,
  the old panel stays as it was, plus a link to the tab.

## Consequences

- The frontend now has two views of a type, and each one answers its own question. The filter asks «what does it
  contain?»; the chart grouping asks «what instrument is it?». A future chart that groups by content must say so in
  its own decision.
- The report stays unchanged, and so do AI Export and the other readers of `summary.allocation_*`.
- The engine cache is shared by the report and the tab. A change to `_engine_run`'s key touches both, and
  `test_engine_shared_run.py` guards it.
- Profile voices with a pie in the catalogue (fund currency, replication, domicile…) come next. Each one becomes a new
  dimension of the same view; the engine does not load them yet.
- Still open after the merge: FR and ES translations at the end of the release, and the lane backlog ALF-1…ALF-8.

## Source files

| Role | Path |
|------|------|
| The view (filters, identity, matrix, history) | `backend/app/services/financial_math/portfolio/allocation_view.py` |
| The one split of value per asset and day | `backend/app/services/financial_math/portfolio/daily_state.py` |
| The class of an asset (content map) | `backend/app/services/assets/type_rules.py` |
| The service on the page's engine run | `backend/app/services/portfolio/allocation.py` |
| The shared engine run | `backend/app/services/portfolio/data_access.py` |
| The endpoint | `backend/app/api/v1/portfolio_api.py` |
| Request and answer | `backend/app/schemas/portfolio/allocation.py` |
| The tab | `frontend/src/lib/features/portfolio-view/PortfolioAllocationTab.svelte` |
| The tab's features (controller, filters, table, matrix) | `frontend/src/lib/features/allocation/` |
| The tab in both page profiles | `frontend/src/lib/features/portfolio-view/portfolioScopeProfile.ts` |
| Unit tests of the view | `backend/test_scripts/test_services/test_financial_math/test_allocation_view.py` |
| Content map parity with the frontend | `backend/test_scripts/test_services/test_asset_type_rules.py` |
| No replay after the report | `backend/test_scripts/test_services/test_financial/test_engine_shared_run.py` |
| API tests | `backend/test_scripts/test_api/test_portfolio_allocation_api.py` |
| E2E | `frontend/e2e/portfolio/allocation-tab.spec.ts` |

## Links

- [[decisions/asset-type-two-level-taxonomy]] — the family and content views this decision uses side by side.
- [[decisions/one-colour-rank-per-asset]] — the asset colours the tab's pie reuses.
- [[entities/asset-profile-enrichers]] — the dated sector and country weights the split reads.
- Source: `developer_journal/Release_2/Phase_2/80_allocationFilters/` (`analisi-ALF.md` §10–§12, `lotti-ALF.md`,
  `mockup-ALF-C2.html`).
