---
name: enricher-plugin
description: "Use this skill when creating, extending, or reviewing a LibreFolio enricher (backend/app/services/enricher_providers/) — a plugin that reads an asset's descriptive profile (costs, countries, sectors, coupons, legal form, issuer…) from one outside source, for the weekly read, «Aggiorna» and «Chiedi alla fonte». Explains the high-level spirit of an enricher and its mandatory rules, and points to the developer guide for up-to-date technical details."
---

# 🪪 Enricher Plugin Skill

> High-level, durable guide to what an **enricher** must do and the spirit it must follow. For exact, up-to-date
> signatures and behaviour, read the developer guide (see [Where to find the technical details](#-where-to-find-the-technical-details)).

## 🎯 What an enricher is

An enricher teaches LibreFolio to **read an asset's profile from one source**: the voices of the profile catalogue it
knows (a fund's TER and replication, a bond's coupons and maturity, a share's sector, an issuer's legal form…). It lives
in `backend/app/services/enricher_providers/<name>/` (`plugin.py`, and `i18n/` for its own texts), extends
`EnricherPlugin`, and is auto-discovered via `@register_provider(EnricherRegistry)`.

It is a **family of its own**, beside the price providers: a source may be both (justETF, Yahoo, Borsa Italiana), but the
enricher is a separate plugin with its own contract. An asset binds **several** enrichers in an order the user chooses;
for each voice the first enricher in the list that gives it wins.

Think of it as a **faithful adapter** to the source's descriptive data. It is **not** the store of the profile, **not**
the merge of several sources, **not** the scheduler and **not** the cache: those live in the core
(`services/enrichers/`, `services/assets/profile/`).

## 🧭 The spirit — mandatory rules

1. **The site is the plugin's own.** It is read through the plugin's library or HTTP client, inside the plugin. The core
   is told nothing about the site: no host, no pause declared.
2. **No imports between plugins.** An enricher never imports another enricher, nor the price provider of the same
   source. A helper two plugins need goes to a shared generic module.
3. **Only generic helpers are shared.** A shared module parses a number, a percentage, a country, a sector, or reads a
   «too many requests» refusal (`rate_limited_from_exception`): never a source. A helper only this plugin uses sits
   beside `plugin.py` as `_*.py`.
4. **The queue and the pause live inside `read`.** The plugin spaces its own calls and handles its own refusals (too
   many requests → the item carries `RATE_LIMITED` and its `retry_after`). The queue also covers two requests arriving
   together, for example an «Aggiorna» while the weekly read runs: the registry builds a new instance per call, so the
   pace lives at module level, never on `self`. Use the core's `Pacer` (`backend/app/utils/runtime/pacing.py`): one
   instance per plugin with its own interval, `_PACER.wait()` right before each call to the site, in `recognize`,
   `read` and `search` alike.
5. **Plain blocking calls.** `recognize`, `read`, `search` and `page_url` are ordinary blocking functions: the core runs
   them away from the event loop. Do not make them `async`, do not wrap them in `asyncio.to_thread`.
   A `search` the source refuses for too many requests raises `EnricherRateLimited` (`services/enrichers/base.py`),
   never an empty list: the route answers 429 `RATE_LIMITED` with `Retry-After`.
6. **`read` yields, one binding at a time.** It receives a list of bindings (and, optionally, the voices wanted) and
   yields one item per binding as it goes, each with its own outcome: `ok` with the values, `not_found`, or `error`.
   «Not found» is an outcome, never an exception. A plugin that reads everything from one page may ignore the voices
   asked; one that pays a call per voice uses them to skip calls.
7. **Values in the catalogue's stored form.** Every value is a voice of the profile catalogue, in its shape: decimals as
   **text**, never floats; a percentage as a fraction («0.0022»); maps renormalised; dates ISO. The core checks them
   (`normalize_value`) and drops what it refuses. Never write a voice under another's key: a fund's management fee is
   `management_fee`, never `ter`.
8. **Declare truthfully, per asset type.** `voices` names, for each asset type, the voices it can fill; `default_priority`
   gives a degree to **every** `AssetType`, `None` written out for a type it does not cover. The enrichers window, the
   default order and «Riconosci» read these.
9. **The binding is the identity.** A binding is `identifier_type` + `identifier` + the plugin's own parameters
   (`params_schema` draws their form; labels via `x-i18n-key` in the plugin's `i18n/`). Everything needed to read the
   asset later lives there: reading never re-searches.
10. **Settings are the instance's.** Keys go in `settings_fields`; a required one left empty makes the enricher «not
    configured»: the weekly read and «Aggiorna» skip it and its voices pass to the next enricher, «Riconosci» leaves it
    out, «Chiedi» reports it as an error outcome, `test` and `search` answer the coded 422 `NOT_CONFIGURED`.
    `LIBREFOLIO_ENRICHERS_ENABLED` can turn it off on an instance: its bindings stay, the reads skip it, its routes
    answer 404.

## 🛠️ Rough shape of the work

1. Create `backend/app/services/enricher_providers/my_source/` with `__init__.py` (docstring only) and `plugin.py`,
   extending `EnricherPlugin`, decorated with `@register_provider(EnricherRegistry)`.
2. Declare `code`, `name`, `icon`, `help_url`, `terms` (the class of the source's terms of use), `accepted_identifier_types`,
   `voices`, `default_priority`, and, when needed, `params_schema` and `settings_fields`.
3. Implement `recognize`, `read` and `page_url`; `search` only when the source has its own search engine. A `search`
   feeds «Search online» at the top of the enrichers' window: each result must be a binding `recognize` and `read`
   take as it is (set `market` when the source names the listing). An enricher without `search` is still reached
   there, by `recognize`, when the user types an identifier of a type it accepts.
4. Add `test_cases` (real bindings per asset type) for the external suite, and offline tests with recorded answers under
   `backend/test_scripts/`.
5. A voice the catalogue does not have is a change to the catalogue (`services/assets/profile/catalogue.py`, with its
   `topic` and its labels in four languages), never an extra key in the plugin.
6. After any change to the plugin's declarations, run `./dev.py api sync`.

## 📚 Where to find the technical details

This skill is intentionally **high-level and durable**. For the precise, current contract — signatures, return types,
the 30-minute cache, the «Riconosci» cascade, the weekly read, the routes and their refusals, worked examples — **always
read the developer guide**, which is the source of truth:

- **Enricher Plugin Guide** — `mkdocs_src/docs/developer/architecture/patterns/enricher_plugin_guide.md`
- **Plugin Settings** — `mkdocs_src/docs/developer/architecture/patterns/plugin_settings.md` (settings, readiness,
  `NOT_CONFIGURED`)
- **Reference code** — `backend/app/services/enrichers/` (`base.py` the contract, `registry.py`, `usable.py`,
  `bindings.py`, `recognize.py`, `refresh.py`), and the plugins `mockenrich/`, `justetf/`, `yahoo_finance/`,
  `borsa_italiana/` (with its `params_schema` and `i18n/`) in `backend/app/services/enricher_providers/`.

Do not rely on this page for method signatures or exact conventions — they can change; the developer guide is kept up to
date.
