---
name: asset-plugin
description: "Use this skill when creating, extending, or reviewing a LibreFolio asset source provider (backend/app/services/asset_source_providers/) — a plugin that prices one data source (current value, history) and optionally searches, enriches metadata, or resolves URLs. Explains the high-level spirit of an asset provider plugin and points to the developer guide for up-to-date technical details."
---

# 🧩 Asset Provider Plugin Skill

> High-level, durable guide to what an **asset source provider** plugin must do and the
> spirit it must follow. For exact, up-to-date signatures and behaviour, read the developer
> guide (see [Where to find the technical details](#-where-to-find-the-technical-details)).

## 🎯 What an asset provider plugin is

An asset provider plugin teaches LibreFolio to **price one data source**: fetch an asset's
**current value** and its **historical values**, and — optionally — **search** for it,
**enrich its metadata**, and **resolve it from a URL**. It lives in
`backend/app/services/asset_source_providers/` (one file per source), extends
`AssetSourceProvider`, and is auto-discovered via `@register_provider(AssetProviderRegistry)`.

Think of it as a **faithful adapter** to an external quote source (Yahoo, justETF, Borsa
Italiana, a scraped page, …): it maps that source's data into LibreFolio's standard value and
search shapes. It is **not** the cache, **not** the FX layer, and **not** the FIFO/analytics
engine — those live in the core.

## 🧭 The spirit — mandatory rules

1. **Pricing is the core contract.** Implement `get_current_value` and `get_history_value`,
   returning the standard value shape (price + currency + date, plus optional volume).
   Everything else is optional capability layered on top.
2. **Sync I/O is allowed — do NOT wrap it in `asyncio.to_thread`.** Every provider call runs
   through `_run_provider_in_thread()`, in its own dedicated thread with its own event loop.
   This is the **one place the app-wide "wrap sync I/O" rule is inverted**: call `requests`,
   `yf.Ticker().info`, an HTML scraper, etc. **directly**. The methods are `async def`, but
   their bodies may block — they are isolated.
3. **Never manage your own price cache.** The manager owns the caches (history, current,
   metadata, search-queries, search-results) plus a `probe_provider_config` dry-run that
   bypasses them. A provider must be **pure per call** — fetch and return, no memoisation.
4. **Expected-empty is data, not an error.** Return structured outcomes
   (`NO_DATA` / `NOT_SUPPORTED` / `NOT_IMPLEMENTED`) instead of raising for "no quote dated
   today" or "history unsupported". Reserve exceptions for **real** failures. Best-effort,
   never fatal.
5. **Declare capabilities truthfully.** `supports_history`, `supports_search` (derived from
   `test_search_query`), and `supports_meaningful_volume` + `volume_kind` drive the UI and the
   engine. Set them to match reality so downstream adapts (hides the history UI, picks the
   right volume semantics, etc.).
6. **`provider_params` carries pricing identity across the boundary.** Everything needed to
   price an asset **later** must live in its stored identifier + `provider_params` (e.g. a
   Borsa Italiana fund's internal `codice_fondo`). `params_schema` describes those params so
   the frontend renders a **dynamic form**. Pricing must never depend on re-searching.
7. **Search is optional and on-site only; pricing never re-searches.** If you implement
   `search(query)`, return the standard search-item dicts from the source's **own** engine.
   The external link-finder and `resolve_url` are an interactive **last resort** for discovery
   only (see the search guide). Load-bearing invariant: once an asset exists it is priced by
   its identifier/params, **never** by searching.
8. **`resolve_url` is the inverse of `get_asset_url`.** Opt in via `resolvable_url_domains`;
   open the URL, extract it, and return the **same shape `search` returns** (a single item, or
   the full canonical set) — or `None`. Never raise; off-domain / unrecognised → `None`.

## 🛠️ Rough shape of the work

1. Create `backend/app/services/asset_source_providers/my_provider.py`, extend
   `AssetSourceProvider`, decorate with `@register_provider(AssetProviderRegistry)`.
2. Implement the **required** members: `provider_code`, `display_name`, `get_current_value`,
   `get_history_value`, and `test_search_query` (return `None` if the source has no search).
3. Add **optional** capability as needed: `search`, `fetch_asset_metadata`, `params_schema`
   (+ the dynamic form it drives), `resolvable_url_domains` + `resolve_url`, and the
   `supports_history` / volume properties.
4. Drop a provider **icon** in `backend/app/services/asset_source_providers/static/`.
5. Verify with the **probe** dry-run (it bypasses the caches), add a provider test under
   `backend/test_scripts/`, and add a docs page. After any change to `params_schema` or other
   API-visible provider info, run `./dev.py api sync`.

## 📚 Where to find the technical details

This skill is intentionally **high-level and durable**. For the precise, current contract —
abstract methods, exact signatures, return types, the cache TTL table, thread isolation, and
worked examples — **always read the developer guide**, which is the source of truth:

- **Asset Plugin Guide** —
  `mkdocs_src/docs/developer/architecture/patterns/asset_plugin_guide.md` (the central how-to)
- **Asset Search & Link-Finder** —
  `mkdocs_src/docs/developer/backend/assets/search_link_finder.md`
  (for `search` / `resolve_url` / `hints`, the three-layer discovery stack)
- **Borsa Italiana Provider** —
  `mkdocs_src/docs/developer/backend/assets/provider_borsa_italiana.md`
  (reference implementer of `provider_params` + `resolve_url` — funds by internal code)
- **Instructions** — `.github/instructions/backend-providers-asset.instructions.md`
  (base class, thread isolation, the 5-cache table, provider inventory)
- **Reference code** — `backend/app/services/asset_source.py`
  (base class `AssetSourceProvider` + the manager/orchestration), and the providers
  `yahoo_finance.py`, `justetf.py`, `borsa_italiana.py`, `css_scraper.py`.

Do not rely on this page for method signatures or exact conventions — they can change; the
developer guide is kept up to date.
