---
name: signal-plugin
description: "Use this skill when creating, extending, or reviewing a LibreFolio technical signal plugin (backend/app/services/signal_plugins/) — a schema-driven indicator computed by the backend for the Asset and FX charts and for AI Export. Explains the high-level spirit of a signal plugin and points to the developer guide for up-to-date technical details."
---

# 📊 Signal Plugin Skill

> High-level, durable guide to what a **technical signal** plugin must do and the spirit it
> must follow. For exact, up-to-date signatures and behaviour, read the developer guide
> (see [Where to find the technical details](#-where-to-find-the-technical-details)).

## 🎯 What a signal plugin is

A signal plugin teaches LibreFolio **one technical indicator** (SMA, RSI, Bollinger Bands,
rolling drawdown, …). It lives in `backend/app/services/signal_plugins/<code>/` (one folder per
indicator: `plugin.py` holds the code, `i18n/` its `signals.<ns>.*` texts), extends `SignalPlugin`
(`signals/base.py`), and is auto-discovered via
`@register_plugin(SignalPluginRegistry)`.

It is a **pure, declarative calculator**: it declares its parameters, required data, outputs
and AI semantics, and computes the series it is given. The signal service plans the request,
loads and prepares prices, converts currencies, enforces the status matrix and serves the
results; the frontend renders the declaration without indicator-specific code.

## 🧭 The spirit — mandatory rules

1. **The declaration is the contract.** Code, version, i18n keys, `params_model`,
   `input_requirements`, `output_specs`, compatible domains and AI semantics are what the
   catalog, the selector UI, the chart and AI Export read. Declare everything; a plugin
   that needs special handling elsewhere is wrong.
2. **Pure computation only.** No database access, provider call, currency conversion or HTTP
   inside a plugin. Keep the formula and the third-party library choice inside it.
3. **Strict parameters.** A Pydantic model with `extra="forbid"`, with JSON Schema UI
   metadata for the dynamic controls. No free-form dictionaries.
4. **Never invent data.** Missing fields or date gaps are never compacted silently: the data
   policy decides, and the result says `partial` or `unavailable`. A plugin never sets the
   status itself; it raises `SignalUnavailableError` or returns a `SignalComputation`.
5. **Count periods the standard way.** Sessions by default (`computes_on_quote_days = True`);
   calendar days only for windows that are calendar spans by definition.
6. **Finite, canonical output.** Lines, areas, bars or bands only; `NaN` may mark warm-up,
   infinity never; every output key declared exactly once.
7. **Version the numbers.** Bump `implementation_version` whenever the values change.
8. **Common financial math comes from its one home.** Returns, annualization, FX conversion
   and valuation are never re-derived in a plugin: use `backend/app/services/financial_math/`
   and the map in `.github/instructions/backend.instructions.md`. The indicator's own formula
   stays in the plugin.

## 🛠️ Rough shape of the work

1. Create the folder `backend/app/services/signal_plugins/my_signal/`: `__init__.py` (docstring
   only, no re-export) and `plugin.py`, which extends `SignalPlugin` and is decorated with
   `@register_plugin(SignalPluginRegistry)`. Import and patch from `….my_signal.plugin`.
2. Declare the members (code, versions, keys, parameters, inputs, outputs, domains, AI
   temporal rules), then implement `warmup_requirement()` and `compute()`.
3. Add the EN/IT/FR/ES UI keys in the plugin's own `i18n/`
   (`./dev.py i18n add signals.<ns>.… --into signal_plugins/my_signal`; a key several indicators
   share stays in the `charts` subsystem) and the English financial-theory page named by `docs_path`.
4. Add numerical and parity tests, and update the registry pins in
   `backend/test_scripts/test_services/test_signal_plugin_matrix.py`.
5. Run the signal service, catalog and frontend gates, then `./dev.py api sync` when the
   catalog shape changed.

## 📚 Where to find the technical details

This skill is intentionally **high-level and durable**. For the precise, current contract,
**always read the developer guide**, the source of truth:

- **Signal Plugin Guide** —
  `mkdocs_src/docs/developer/architecture/patterns/signal_plugin_guide.md` (contract, status
  matrix, presentation, AI Export temporal rules, the full "Adding a Plugin" checklist)
- **Registry Pattern** — `mkdocs_src/docs/developer/architecture/patterns/registry_pattern.md`
- **Instructions** — `.github/instructions/backend-signals.instructions.md` (backend) and
  `.github/instructions/frontend-signals.instructions.md` (frontend renderer)
- **Reference code** — `backend/app/services/signals/base.py` and simple plugins such
  as `sma/plugin.py` and `rsi/plugin.py`; the runtime in `services/signals/` (`service.py` is the façade over
  `planning.py`, `execution.py` and `validation.py`).

Do not rely on this page for method signatures or exact conventions — they can change; the
developer guide is kept up to date.
