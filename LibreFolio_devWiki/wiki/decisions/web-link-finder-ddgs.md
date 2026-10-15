---
title: "The web link finder uses the ddgs metasearch library instead of a hand-written DuckDuckGo scraper; SearXNG was not needed"
category: decision
status: resolved
date: 2026-07-28
tags: [backend, search, web-link-finder, ddgs, duckduckgo, scraping, cache, assets]
related:
  - features/F-028
---

# Decision: replace the scraper, do not fix it

## Context

The web link finder looks for an asset's pages on the web from the asset modal. It scraped DuckDuckGo's HTML by hand.
In bursts of queries DuckDuckGo's bot detection answered HTTP 202 with an «anomaly» page and no results;
`raise_for_status()` does not fire on a 2xx, so the empty list was taken as a real answer and cached for 15 minutes —
while the same query worked in a browser, which hid the cause (folder `phases/04_webSearchEngine`, July 2026).

## Decision

`ae417b9ab` (2026-07-28, «feat(search): swap DuckDuckGo scraper for ddgs metasearch l…»): the `ddgs` library is the
default engine (`LIBREFOLIO_WEB_LINK_FINDER_ENGINE`, with `apikey` as the alternative), region `wt-wt` and backend
`auto` by default, both configurable; a total transport failure is never cached. A SearXNG instance was considered and
dropped by the developer (2026-09-02): `ddgs` is enough, and SearXNG would need its own infrastructure.

## Consequences

- Under `auto`, the search backend can change from one call to the next, so the same query may answer differently —
  noted as an open follow-up for bond (BTP) searches.
- An empty answer is only a result when the transport succeeded.

## Source files

| Role | Path |
|------|------|
| Link finder (engine, region, backend settings) | `backend/app/services/assets/web_link_finder.py` |
| Tests | `backend/test_scripts/test_services/test_web_link_finder.py` |
| Journal | `LibreFolio_developer_journal/Release_2/phases/04_webSearchEngine/README.md` |
