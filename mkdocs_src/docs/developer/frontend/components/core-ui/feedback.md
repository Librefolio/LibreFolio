# 💬 Feedback & Notifications

Components for user notifications, contextual information, loading states, and tooltips.

---

## 🔔 ToastContainer

Global container for **toast notifications** (success, error, info, warning). Components never
mount it: they call the store `toasts` (`lib/stores/app/toastStore.svelte.ts`).

```ts
import {toasts} from '$lib/stores/app/toastStore.svelte';

toasts.success('Saved');
toasts.error('Sync failed', 20000); // custom duration in ms
```

- **Position**: stacked at the **top centre** of the viewport (`fixed top-4 left-1/2
  -translate-x-1/2`, `z-[9999]`), newest last, each sliding in from above.
- **Auto-dismiss** after a per-variant default — success and info 8 s, warning 10 s, error 15 s —
  or the `duration` passed to the call; a thin bar counts the time down. A duration of `0` keeps
  the toast until it is dismissed.
- **Dismiss**: the ✕ button (`toast-dismiss`), which stays the keyboard- and screen-reader path,
  or a swipe of at least 60 px left, right or up (pointer events: finger, pen and mouse).
- **Color-coded** by variant, with a matching icon; test ids `toast-{variant}`.
- The store also offers `show(variant, message, duration?)`, `dismiss(id)` and `clear()`; toasts
  are cleared when the signed-in account changes (client-session reset, e.g. logout).

### 🧼 HTML messages {: #toast-html }

A message may contain markup — flags, coloured badges, icons, links — and is rendered with
`{@html sanitizeHtml(message)}` (`lib/utils/core/sanitizeHtml.ts`, DOMPurify): the markup is kept,
event-handler attributes, `<script>` and `javascript:` URLs are dropped. Sanitising is the safety
net, not a licence: escape any user or provider text you put into a message with `escapeHtml`.

**Links** inside a toast work like normal links. A press that starts on a link (or a button) never
starts a swipe, so tapping it navigates instead of dragging the toast away. Build links to detail
pages with `entityDetailLinkHtml({kind: 'asset', id} | {kind: 'fx', slug}, label)`
(`lib/utils/core/entityLink.ts`): it accepts only those two routes and escapes the label.
`ToastContainer.test.ts` covers both contracts.

**Used by**: mounted once in the authenticated layout, `routes/(app)/+layout.svelte`.

---

## ℹ️ InfoBanner { #infobanner }

An inline **banner** for contextual information or warnings (`ui/feedback/InfoBanner.svelte`).

- `variant`: `info` (default), `warning`, `error`, `success` — colours and default icon
  (`showIcon`, default `true`)
- Content from `message` or from the children; with `message`, the banner hides itself when the
  value is empty or `null`
- `dismissible` adds an ✕ that calls `ondismiss`
- `role="alert"` for `error`, `role="status"` otherwise; test id `info-banner-{variant}`
- Inline within page content (not a toast)

**Used by**: [BrokerModal](../features/brokers/modals.md) (validation errors), settings tabs, the
sync and import modals, `RegisterCard`.

---

## 🛡️ DataQualityBanner { #dataqualitybanner }

The **unified data quality banner component** for surfacing data warnings across the dashboard, asset detail, and forex detail pages. Replaces ad-hoc inline banners with a standardized `DataQualityIssue` model.

See [DataQualityBanner Developer Manual](../../data-quality-banner.md) for full documentation.

**Modes**:

- `grouped` — dashboard: single container with all issues sorted by severity
- `flat` — detail pages: one banner per issue

**CTA**: actions are emitted via `onaction(action, target, issue)` — the component does not navigate or open modals directly.

**Used by**: Dashboard (`/dashboard`), Asset detail (`/assets/:id`), FX detail (`/fx/:pair`), and the risk panels (`RiskAnalysisPanel`, `AssetSetRiskPanel`, `RiskPanelHeader`).

---

## ⏳ LoadingSpinner

A simple **animated spinner** for async loading states (`ui/feedback/LoadingSpinner.svelte`).

- `size`: `sm`, `md` (default), `lg` — the vertical padding around it
- `text` below the spinner, defaulting to the translated `common.loading`
- `role="status"`, `aria-live="polite"`

**Used by**: API calls, lazy-loaded content, search results.

---

## 💡 Tooltip

**Hover/tap tooltip** with automatic positioning (`ui/feedback/Tooltip.svelte`).

- Content: `text`, or `html` (rendered through `sanitizeHtml`); `math` renders inline `$…$` LaTeX
  with KaTeX
- Positions: `top` (default), `bottom`, `left`, `right` — flips when it would leave the viewport;
  the tooltip is moved to `document.body` and drawn with fixed positioning, so a modal's overflow
  or a parent's opacity never affects it
- Plain hover opens after `showDelayMs` (default 500 ms), so crossing the page does not flash
  tooltips; a click, a tap or Enter/Space on the focused trigger opens it at once and pins it
- A pinned tooltip stays while the pointer is on the trigger or on the tooltip itself; it closes on
  a second click on the trigger, on a click outside, or 30 s after contact ends
- `interactiveChild`: when the child is itself a button or a link, the wrapper does not add its own
  `role="button"` and tab stop

**Used by**: Toolbar buttons, icon-only buttons, info badges, `DocsLink`.
