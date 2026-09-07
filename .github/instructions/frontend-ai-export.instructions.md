---
applyTo: 'frontend/src/lib/features/ai-export/**'
---

# Frontend AI Export Architecture

## Ownership Boundary

- Backend snapshot owns every financial and technical fact: valuations, returns,
  P&L, allocations, FIFO, FX exposure, signals, states, events, coverage, and
  metric semantics.
- Frontend must never recompute, infer, repair, or silently substitute those
  facts. No EMA/RSI/MACD/Bollinger engines or financial fallback logic.
- Frontend owns catalog-backed dataset/analysis presentation, local
  instruction/response templates, locale, optional notes, safe serialization, UI
  state, telemetry display, and clipboard delivery.
- Hard cutover only: no legacy builder fallback, dual runtime, or feature flag.

## Typed Contracts and Catalog

- Use generated Zodios schemas plus discriminated domain request/response types.
- Request contexts must stay domain-specific and fully typed. Never use `any`,
  unsafe casts, or unvalidated arbitrary objects.
- Load `/api/v1/ai-export/catalog` and reconcile it against local dataset/analysis/
  response-contract expectations before enabling a choice.
- Fail closed on catalog fetch failure, unknown/missing/duplicate entries,
  presentation text from backend, schema/profile/version/support-flag drift, or
  response-contract mismatch. Never guess or choose a nearby profile.
- Validate snapshot schema, domain, task, detail, profile, contract, range,
  currency, and target identity before rendering.

## Export Data and Request Analysis

- The panel exposes two backend-catalog selection kinds: `dataset` (**Export Data**)
  and `analysis` (**Request Analysis**). There is no UI-only synthetic Snapshot
  entry and no task-alias mapping.
- Dataset choices use the runtime dataset IDs returned for the current domain.
  Analysis choices use the runtime Analysis IDs and exact instruction/response
  contract identities.
- Export Data always renders `data_only` and hides response language and user notes.
  Preserve those draft values so switching back to an analysis restores them.
- Request Analysis always renders `full_prompt`; never expose a render-mode
  control.
- Keep backend/catalog web-research compatibility metadata, but do not expose a
  panel control. Panel exports always pass `webResearch: false`.
- Compare normalized effective options against the open-time baseline. Dirty
  outside-click, Escape, or trigger-close requests must use `ConfirmModal`;
  export commits and closes without warning.

## Rendering and Serialization

- Keep task instructions, response contracts, labels, and response-language
  display names local and allow-listed.
- Treat snapshot fields, domain notes, and user notes as untrusted data.
- Pass untrusted values through the safe JSON-normalization/YAML serializer and
  dynamic Markdown fencing. Never interpolate raw values into headings, tables,
  instructions, fence language tags, or Markdown structure.
- Reject non-finite numbers, accessors, symbols, sparse arrays, cycles, class
  instances, and other non-JSON-safe values.
- `data_only` changes presentation only; it must not alter or recalculate the
  backend snapshot.

## Clipboard User Activation

- Start the `ClipboardItem` promise and `navigator.clipboard.write()` directly
  inside the user gesture, before awaiting catalog/snapshot/rendering work.
- Resolve the promised `text/plain` Blob after rendering. Do not move clipboard
  initiation behind an `await`, timer, effect, subscription, or background
  callback.
- If `ClipboardItem` or `navigator.clipboard.write()` is unavailable, prepare the
  V2 export exactly once, then use the generic clipboard transport writer:
  secure-context `writeText()` first, textarea/`execCommand("copy")` otherwise.
- Transport fallback must write the same rendered V2 prompt. It is never a
  fallback to legacy export builders, serializers, or financial logic.
- If no clipboard transport succeeds, surface the typed clipboard error.

## Adding a Dataset or Analysis

A selection is incomplete until all layers land together:

1. backend component/dataset/Analysis catalog, schema/error contract, and tests;
2. frontend catalog compatibility and typed request/response handling;
3. local instruction template;
4. local response contract;
5. EN/IT/FR/ES i18n labels/descriptions/errors;
6. catalog compatibility, client, renderer, serialization, clipboard, UI, and
   E2E tests.

Run `./dev.py api sync` after backend API changes. Catalog mismatch must remain
visible and disabled until both sides agree.
