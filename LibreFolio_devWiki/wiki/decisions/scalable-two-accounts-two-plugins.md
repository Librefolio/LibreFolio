---
title: "Scalable Capital: two accounts, two brokers, two plugins that refuse each other's file"
category: decision
status: resolved
date: 2026-10-10
updated: 2026-10-12
tags: [brim, import, scalable, plugins, broker, cash-transfer, duplicates, exporter, workstream-s, release-1.2]
related:
  - decisions/import-wizard-default-plugin-check
  - decisions/bulk-pairs-new-with-saved
  - problems/merged-transfer-not-seen-as-duplicate
  - concepts/brim-texts-translated-by-code
  - decisions/broker-icon-order-dedicated-plugin-first
  - decisions/brim-broker-scoped
  - features/F-013
  - sources/phase00-brim-scalable-2026-10
---

# Decision: Scalable Capital — two accounts, two brokers, two plugins

## Context

A Scalable Capital customer has two accounts: the **broker** (securities and their cash) and the **overnight
account** (*conto deposito*), with money moving between them. Scalable's own CSV export exists only on the PRIME
plans and covers only the broker; the overnight account cannot be exported at all. Workstream S first built an
exporter — the Chrome extension `Librefolio/librefolio-exporter`, a separate public repository (Manifest V3,
AGPL-3.0, v1.0.0 on 2026-10-09) that writes one file per account — and then, with plan 37, the importers
(2026-10-09/10, train 30).

## Options Considered

1. **One LibreFolio broker for both accounts** — rejected: a broker has one cash pool per currency, a `CASH_TRANSFER`
   links two *different* brokers, a BRIM import writes into one broker, and the two accounts and their balances could no
   longer be checked against the app.
2. **One plugin reading every layout**, as Revolut does — the plan's first draft. On the developer's idea it became
   two plugins that refuse each other's file.
3. **Linked pairs emitted by the import**, as DEGIRO does for `FX_CONVERSION` — impossible here: a transfer between
   the two accounts links two brokers, while an import writes one. The pairing comes after, in the bulk editor.

## Decision

The developer's decisions of 2026-10-09 (plan 37, §1):

- **Two brokers, two plugins, one shared module.** `broker_scalable` reads Scalable's PRIME CSV and the exporter's
  broker file; `broker_scalable_deposit` reads the exporter's overnight-account file; detection, mapping,
  descriptions, notices and refusals live in `_scalable.py`. The layout is recognised from the header, never from the
  file name, whose prefix is free. Each plugin refuses the other's file with a code and names the plugin to use:
  `scalable_deposit_file`, `scalable_broker_file`, `scalable_prime_file`, and `scalable_mixed_file` («the file mixes
  the broker and the overnight account: export the two accounts separately»). So **a broker's default plugin also
  says which account it is**, and the import wizard can catch a file dropped on the wrong broker —
  [[decisions/import-wizard-default-plugin-check]].
- **The transaction id goes into the description** — ` · id <lf_id>` for the exporter, ` · ref <reference>` for the
  PRIME CSV. LibreFolio finds duplicates by type, date, quantity, amount and description, not by an external id, and
  two identical transfers had once been taken for one: with the id, two equal rows stay distinct and the same movement
  exported again is recognised.
- **Amounts as the files state them.** In the PRIME CSV a trade's `amount` is the **gross** (shares × price), with
  `fee` and `tax` apart; on income it is the **net**, with the withholding in `tax`. BUY and SELL are booked on the
  gross with FEE and TAX legs; DIVIDEND and INTEREST are `amount` + `tax`, with a TAX leg. The exporter 1.0.0 wrote the
  web app's amount, fee included; **1.0.1** (commit `6672084`, tag `v1.0.1`, released by the developer) writes the
  market valuation, and the plugin warns on a 1.0.0 file (`scalable_fee_in_amount`). No amount is recomputed: only
  sums of values found in the file. *Update (2026-10-13, U-6, `a6d1754ed`)*: the developer dropped exporter 1.0.0 —
  the `scalable_fee_in_amount` notice, its branch and its catalogue keys are gone, every exporter trade books its FEE
  and TAX legs, and the CHANGELOG line names the exporter version the importers need, 1.0.1 or later (`3d3cf811a`).
- **Notices, not guesses** — twelve coded notices, each with the file's rows: orders not executed, open partial
  orders, unknown fees and taxes, reversals, rows not imported (security transfers, corporate actions), cash booked by
  its sign, tax refunds, internal transfers to pair, several overnight accounts, the 1.0.0 fee, net dividends,
  unreadable rows.
- Both plugins tag `["import", "scalable"]`, so a merged pair has no tags to reconcile
  ([[decisions/pair-description-tags-validation]]).
- **Icons**: Scalable's logo with a glyph — a chart for the broker, a piggy bank for the overnight account — generated
  by `scripts/compose_broker_icons.py` and served as the plugins' static files; a broker whose default plugin is one of
  them shows it without any setting ([[decisions/broker-icon-order-dedicated-plugin-first]]).

## Consequences

- The developer's test with his real exports, kept outside the repository: 7 of 7 (2026-10-09/10).
- The internal transfers are paired after the import, together or months apart —
  [[decisions/bulk-pairs-new-with-saved]]; a transfer already merged is recognised when exported again —
  [[problems/merged-transfer-not-seen-as-duplicate]].
- **Out of alpha on 2026-10-12**, the developer's word after reading the page: «Siccome abbiamo l'export reale del
  plugin nostro, toglierei l'alpha». The user page was rewritten around «How to export» (opened by the PRIME-only
  lead, the installation in a fold-out panel), «What is imported» moved to a developer page, and both rows of the
  providers list read «✅ Stable» (M, batch 21, `ff2cf5b3d`, train 55).
- Open: no real samples yet of sales, dividends, reversals, crypto or security transfers (the exporter's recap, §6).
  The word *Tagesgeld* left the overnight plugin's description, its English fallback and its docstrings on 2026-10-13
  (D4, `a6d1754ed`).

## Links

- [[sources/phase00-brim-scalable-2026-10]] — the plan, the exporter's recap and M's batch 21
- [[decisions/brim-broker-scoped]] — a BRIM import belongs to one broker
- [[concepts/brim-texts-translated-by-code]] — the refusals and notices in four languages
- [[features/F-013]] — the parser plugins

## Source files

| Role | Path |
|------|------|
| Shared module (detection, mapping, notices, refusals) | `backend/app/services/brim_providers/_scalable.py` |
| Broker plugin | `backend/app/services/brim_providers/broker_scalable/plugin.py` |
| Overnight-account plugin | `backend/app/services/brim_providers/broker_scalable_deposit/plugin.py` |
| Synthetic samples (PRIME, broker, overnight) | `backend/app/services/brim_providers/sample_reports/scalable-prime-export.csv`, `backend/app/services/brim_providers/sample_reports/scalable-broker-export.csv`, `backend/app/services/brim_providers/sample_reports/scalable-deposit-export.csv` |
| The plugins' icons and their generator | `backend/app/services/brim_providers/static/scalable/`, `scripts/compose_broker_icons.py` |
| Plugin tests; the two-broker API flow | `backend/test_scripts/test_external/test_brim_scalable.py`, `backend/test_scripts/test_api/test_brim_scalable_api.py` |
| User guide | `mkdocs_src/docs/user/transactions/import/scalable.en.md` |
| Developer page (what is imported) | `mkdocs_src/docs/developer/backend/brim/scalable.md` |
| Providers list | `mkdocs_src/docs/developer/backend/brim/providers_list.md` |
| Plan 37 | `LibreFolio_developer_journal/Release_2/Phase_0/37_brimScalable/plan-phase00BrimScalable.prompt.md` |
| The exporter's recap | `LibreFolio_developer_journal/Release_2/Phase_0/37_brimScalable/recap-phase00ScalableExporter.md` |
