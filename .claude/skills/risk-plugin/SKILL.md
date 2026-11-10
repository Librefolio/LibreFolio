---
name: risk-plugin
description: "Use this skill when creating, extending, or reviewing a LibreFolio risk analytic plugin (backend/app/services/risk_plugins/) — a calculation over prepared return series for an asset, an asset set, or a portfolio (KPIs, VaR, drawdown, correlation, stress, simulation, optimization). Explains the high-level spirit of a risk analytic and points to the developer guide for up-to-date technical details."
---

# 📉 Risk Analytic Plugin Skill

> High-level, durable guide to what a **risk analytic** plugin must do and the spirit it must
> follow. For exact, up-to-date signatures and behaviour, read the developer guide (see
> [Where to find the technical details](#-where-to-find-the-technical-details)).

## 🎯 What a risk analytic is

A risk analytic answers **one risk question** — how much can it hurt, how diversified is it,
is it paid for its risk, what if… — over an asset, an asset set or a portfolio. It lives in
`backend/app/services/risk_plugins/<analytic_code>/` (one folder per analytic: `plugin.py` holds the
code, `i18n/` its `risk.analytics.<id>.*` texts), extends `RiskAnalytic`
(`backend/app/services/risk/base.py`), and is auto-discovered via
`@register_plugin(RiskAnalyticRegistry)`.

It is a **calculator over a prepared, DB-free context**: the risk service resolves the scope,
loads and aligns the series, checks eligibility and observations, and calls the analytic. The
analytic never opens a session or fetches prices.

## 🧭 The spirit — mandatory rules

1. **The declaration is the contract.** `analytic_code`, `algorithm_version`, i18n keys,
   output kind, supported scopes and modes, `params_model` (`extra="forbid"`),
   `min_observations` and `series_inputs` are validated at import; an incomplete declaration
   fails loudly.
2. **Read only the context.** Use the risk helpers to read the primary series, one series per
   asset, or a benchmark; never query the database or a provider.
3. **Refuse, don't crash.** A property of the data or of the user's choice raises
   `RiskUnavailableError` with a `RiskErrorCode`; an undefined value is `None` plus a warning,
   never a zero standing in for an unknown.
4. **Heavy work leaves the web process.** QuantLib, Riskfolio-Lib or long CPU work go through
   an overridden `execute()` and the spawn worker pools; never import those libraries in the
   web process.
5. **Statistical floors are shared.** A statistical analytic takes
   `min_observations = RISK_MIN_OBSERVATIONS`, never a literal.
6. **Words are keys.** Names, descriptions and warnings are i18n keys in the four frontend
   catalogues, with an English `message` for logs; asset ids go in `details`.
7. **Version the numbers.** Bump `algorithm_version` whenever the values change: results and
   worker caches key on it.
8. **Common financial math comes from its one home.** Series statistics belong to
   `risk/metrics.py`; returns, annualization, FX conversion, average cost and valuation come
   from `backend/app/services/financial_math/` and the map in
   `.github/instructions/backend.instructions.md`, never from a local copy.

## 🛠️ Rough shape of the work

1. Create the folder `backend/app/services/risk_plugins/<analytic_code>/`: `__init__.py`
   (docstring only, no re-export) and `plugin.py` with the parameters model and the decorated
   `RiskAnalytic` subclass. Import and patch from `….<analytic_code>.plugin`.
2. Implement `compute()` (light work) or override `execute()` (worker pools).
3. Reuse an output model, or add a new output kind end to end (schema union, OpenAPI
   discriminator, `./dev.py api sync`).
4. Add the i18n keys — the analytic's own `risk.analytics.<id>.*` in its `i18n/`
   (`./dev.py i18n add … --into risk_plugins/<analytic_code>`); a new `risk.warnings.*` sentence in
   the shared `risk` subsystem — the pure plugin tests and the pinned catalogue lists; review the
   code-keyed decisions of the risk service (`available_observations()` and
   `requires_valid_composition()` in `risk/results.py`, the `stress` predicates in `risk/plan.py`).
5. Surface it in a panel if needed, and document it (theory page, user page, analytics table).

## 📚 Where to find the technical details

This skill is intentionally **high-level and durable**. For the precise, current contract,
**always read the developer guide**, the source of truth:

- **Risk Engine** — `mkdocs_src/docs/developer/backend/risk/architecture.md`, sections
  "The Plugin Contract" (`#plugin-contract`) and "Adding a Risk Analytic"
  (`#adding-an-analytic`), with the test map (`#tests`)
- **Registry Pattern** — `mkdocs_src/docs/developer/architecture/patterns/registry_pattern.md`
- **Instructions** — `.github/instructions/backend-risk.instructions.md`
- **Reference code** — `backend/app/services/risk/base.py`, `risk/analytic_helpers.py`, and
  analytics such as `risk_plugins/historical_kpi/plugin.py` and `risk_plugins/correlation/plugin.py`.

Do not rely on this page for method signatures or exact conventions — they can change; the
developer guide is kept up to date.
