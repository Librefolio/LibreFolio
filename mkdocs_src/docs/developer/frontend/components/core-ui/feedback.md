# 💬 Feedback & Notifications

Components for user notifications, contextual information, loading states, and tooltips.

---

## 🔔 ToastContainer

Global container for **toast notifications** (success, error, info, warning).

- Stacked notifications in bottom-right corner
- Auto-dismiss with configurable timeout
- Manual dismiss via close button
- Color-coded by severity

**Used by**: Global layout — mounted once in the root layout.

---

## ℹ️ InfoBanner { #infobanner }

A **dismissible banner** for contextual information or warnings.

- Variants: `info`, `warning`, `error`, `success`
- Optional icon and dismiss button
- Inline within page content (not a toast)

**Used by**: [BrokerModal](../features/brokers/modals.md) (validation errors), settings pages, import previews.

---

## 🛡️ DataQualityBanner { #dataqualitybanner }

The **unified data quality banner component** for surfacing data warnings across the dashboard, asset detail, and forex detail pages. Replaces ad-hoc inline banners with a standardized `DataQualityIssue` model.

See [DataQualityBanner Developer Manual](../../data-quality-banner.md) for full documentation.

**Modes**:

- `grouped` — dashboard: single container with all issues sorted by severity
- `flat` — detail pages: one banner per issue

**CTA**: actions are emitted via `onaction(action, target, issue)` — the component does not navigate or open modals directly.

**Used by**: Dashboard (`/dashboard`), Asset detail (`/assets/:id`), FX detail (`/fx/:pair`).

A simple **animated spinner** for async loading states.

- Configurable size: `sm`, `md`, `lg`
- Optional label text below spinner

**Used by**: API calls, lazy-loaded content, search results.

---

## 💡 Tooltip

**Hover/focus tooltip** with automatic positioning.

- Positions: `top`, `bottom`, `left`, `right` (auto-adjusts to viewport)
- Delay before showing (prevents flicker on quick mouse movements)
- Accessible: shows on focus for keyboard users

**Used by**: Toolbar buttons, icon-only buttons, info badges.
