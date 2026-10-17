---
title: "Broker icon order: the custom icon, a dedicated plugin's icon, the portal's favicon, a fallback plugin's icon, the briefcase"
category: decision
status: resolved
date: 2026-10-10
tags: [frontend, brokers, icons, brim, plugins, workstream-s, release-1.2]
related:
  - problems/broker-icon-race-condition
  - decisions/scalable-two-accounts-two-plugins
  - decisions/import-wizard-default-plugin-check
  - features/F-009
  - sources/phase00-brim-scalable-2026-10
---

# Decision: a dedicated plugin's icon comes before the portal's favicon

## Context

Since 2026-06-26 (`ddffb5273`, «correct priority order restored (favicon before plugin icon)», without a written
reason) a broker's icon was the custom icon, else the portal's favicon, else the default plugin's icon, else a
briefcase. During the review of plan 37 the developer recalled another order and asked to restore it.

## Decision

The developer, 2026-10-10: «sicuro di questo ordine, anche nella guida e nelle prove che feci mi parse fosse
personalizzata>plugin>favicon portale>valigetta. Se non è più così o non lo è mai stato, ripristinalo per favore»
("I recall custom > plugin > portal favicon > briefcase; if that is no longer so, or never was, restore it"). He
approved one exception — the generic plugin's icon is the same for every broker — with «per ora ci sono solo 2 livelli
quindi facciamo così, ma in futuro potremmo pensare di aggiungere un parametro selettore» ("two levels for now; a
selector parameter later"):

1. the custom icon (`icon_url`);
2. the default plugin's icon, when the plugin is made for a broker;
3. the portal's favicon;
4. the default plugin's icon, when the plugin is a generic fallback;
5. the briefcase.

The fallback threshold is **one constant**, `FALLBACK_PLUGIN_PRIORITY_LIMIT = 50`, with `isFallbackPlugin`
(`utils/brim/pluginKind.ts`), on the bands of `BRIMProvider.detection_priority` (0–49 fallback). The icon cache
(`brokerHelpers.ts`), the reactive chain (`brokerIconChain.svelte.ts`) and the wrong-broker check of the import wizard
all use it — the wizard used to hold its own 50.

## Consequences

- Commit `d5c649e9f` (2026-10-10, train 30). The «Portal URL» row of the user guide on brokers, the Scalable page and
  the «Favicons» section of the BRIM guide say the same.
- A backend test pins the constant (`TestFallbackPluginPriorityLimit`: declared once, equal to 50, only the generic CSV
  below it); Vitest covers the orders (`brokerHelpers.test.ts`, `brokerIconChain.test.ts`, `pluginKind.test.ts`).
- A selector, on the plugin or on the broker, would replace the threshold: backlog C-40, after 1.2.
- The chain reads only the props it is given: a component that has only the broker's id does not see the icon fields
  loaded later into the store — [[problems/broker-icon-race-condition]], still open on 2026-10-12.

## Links

- [[decisions/scalable-two-accounts-two-plugins]] — the plugins whose icons triggered the review
- [[decisions/import-wizard-default-plugin-check]] — the other user of the threshold
- [[features/F-009]] — brokers

## Source files

| Role | Path |
|------|------|
| `FALLBACK_PLUGIN_PRIORITY_LIMIT`, `isFallbackPlugin` | `frontend/src/lib/utils/brim/pluginKind.ts` |
| Icon cache and candidates | `frontend/src/lib/utils/broker/brokerHelpers.ts` |
| The reactive chain | `frontend/src/lib/utils/broker/brokerIconChain.svelte.ts` |
| The component | `frontend/src/lib/components/ui/display/BrokerIcon.svelte` |
| `detection_priority` bands | `backend/app/services/brim/brim_provider.py` |
| Backend test of the constant | `backend/test_scripts/test_external/test_brim_providers.py` |
| User guide, «Portal URL» | `mkdocs_src/docs/user/brokers/index.en.md` |
