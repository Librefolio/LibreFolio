# ⚛️ UI Atoms

Small, standalone UI primitives, input helpers and display blocks, in `lib/components/ui/` and its
`input/`, `date/` and `display/` subfolders.

---

## 🌓 ThemeToggle

A **light/dark toggle** in the header (and on the login page).

- Shows 🌙 in light mode and ☀️ in dark mode; a click switches to the other theme
- Writes the device preference through `applyTheme()` (`lib/stores/app/themeStore.ts`,
  `localStorage` key `librefolio-theme`); while the stored preference is *auto*, the icon follows
  the operating system
- The three-way choice — light, dark, auto — saved in the user settings lives in the
  [Preferences tab](../features/settings.md); at login the saved theme is applied

**Used by**: `Header.svelte`, the login page.

---

## 🙈 PrivacyToggle {: #privacytoggle }

The header's **eye button** that hides or shows every monetary amount (`ui/PrivacyToggle.svelte`).

- Flips the device-local flag of `lib/stores/app/privacyStore.svelte.ts` (`isPrivacyEnabled()`,
  `togglePrivacy()`); `aria-pressed` reflects it, test id `privacy-toggle`
- It sits in the header, not in Settings, because the need is contextual: someone walks up to the
  screen

How the flag reaches the formatters is in [Privacy masking](../../state/app-state.md#privacy-masking).

**Used by**: `Header.svelte`.

---

## 📖 DocsLink

A **help icon that opens a documentation page** (`ui/DocsLink.svelte`).

- `path` (required) is relative to the docs root; the link opens `/mkdocs/{lang}/{path}` in a new
  tab, in the current UI language (no prefix for English)
- `localizedFallbackPath` replaces `path` in the other languages, for pages that exist only in
  English
- `icon`: `help` (default) or `book`; `label` is the tooltip and the accessible name, `math` renders
  LaTeX in it; `labelDisplay`: `hidden` (default), `responsive` or `visible`
- Literal `path` values are checked by `./dev.py mkdocs check-links` (`scripts/docs_links.py`)

**Used by**: metric cards (`RiskMetricCard`, `KpiSection`), the risk levels, the chart signals
section, the Tools hub, the asset detail page.

---

## 🌊 AnimatedBackground

**Animated chart-like background** for the login and error pages.

- Three wave layers and an SVG with three chart lines, animated with CSS
- Theme-aware colours (adapts to light/dark mode)
- Fixed behind the page (`z-index: -10`)

**Used by**: `routes/+page.svelte` (login, behind `LoginCard`/`RegisterCard`), `routes/+error.svelte`.

---

## 📋 OrderableList

A **drag-and-drop reorderable list** (`ui/OrderableList.svelte`).

- HTML5 drag and drop on desktop, with a grip handle and a green left border on the drop target
- Up/down arrow buttons below the `md` breakpoint
- Items rendered by a caller snippet; `keyFn` gives each a stable key
- Optional equal-width responsive grid and per-item warning tone
- Reports the new order through `onReorder(items)`

**Used by**: DataTable column reorder (in `ColumnVisibilityToggle`), `FxProviderSelect`,
`ChartSignalsSection`, `ImportWizardModal`, the PAC planner steps.

---

## 🔑 PasswordInput {: #passwordinput }

*Located in `lib/components/ui/input/`*

A **password field with visibility toggle** (eye icon).

- Toggle between `type="password"` and `type="text"`
- Eye / EyeOff icon from lucide-svelte
- `autocomplete` (`current-password` by default, or `new-password`, `off`, `on`), `id` and `name`
  are passed to the input: password managers rely on them — see the
  [password-manager contract](../features/auth.md#password-manager-contract)

**Used by**: [LoginCard, RegisterCard](../features/auth.md), `PasswordChangeModal`.

---

## 💪 PasswordStrength

*Located in `lib/components/ui/input/`*

A **password strength indicator** powered by `@zxcvbn-ts/core`.

- Color-coded strength bar (red → orange → yellow → lime → green) with a label, from score 0
  (very weak) to 4 (very strong)
- With `showRules` (default), a checklist of the five rules: 8 characters, uppercase, lowercase,
  number, special character
- Hidden while the password is empty

**Used by**: [RegisterCard](../features/auth.md) (below password field), `PasswordChangeModal`.

---

## 🔢 ExactDecimalInput {: #exactdecimalinput }

*Located in `lib/components/ui/input/`*

A **decimal text field that never goes through a JavaScript number**.

- `type="text"` with `inputmode="decimal"`: `,` and `.` both work as the decimal separator, and
  characters that can never belong to a number are filtered out while typing
- `value` (bindable string) is the field text; on blur or Enter a valid value is rewritten in
  canonical form (`.` separator, trailing zeros trimmed), then `oncommit` fires
- Validation is exact: digit budget (`maxIntegerDigits`, `maxFractionDigits`, default 12 each),
  `min`/`max` (strings, compared as exact decimals), `required`, `allowNegative`;
  `onvaliditychange` reports `{normalized, empty, syntaxValid, requiredValid, digitsValid,
  rangeValid, valid}`, and `externalInvalid` lets the parent mark it invalid
- ↑/↓ step by `step` in exact decimal arithmetic, clamped to the bounds (to 0 without
  `allowNegative`); `accelerateOnHold` (default `false`) climbs by powers of ten while the key is
  held

**Used by**: the PAC planner steps (targets, routing, fees, liquidity, prices).

---

## 📦 ExactQuantityInput {: #exactquantityinput }

*Located in `lib/components/ui/input/`*

`ExactDecimalInput` for **quantities**, with a controlled value.

- `value` is always the normalized draft (`.` separator), while the text the user types stays in a
  private buffer: a parent echoing the value back never rewrites `1,20` into `1.20` mid-typing;
  `resetKey` forces the buffer to reload
- `signRule`: `positive`, `negative`, `nonzero`, `zero` or `any` (default) — a sign that breaks the
  rule makes the value invalid and the border red, a matching one turns it green
- `accelerateOnHold` defaults to `true`

**Used by**: the quantity field of `TransactionFormModal`.

---

## ⏱️ CompactDurationBadge {: #compactdurationbadge }

*Located in `lib/components/ui/date/`*

A **"Custom" duration chip** that turns into an inline editor.

- Shows `customLabel` while inactive and `{amount}{unit}` when `active`; a click opens a small
  number field plus a unit `SimpleSelect` fed by `options` (units among days, weeks, months,
  years)
- Every valid draft — within `min`/`max` and accepted by `isAllowed(amount, unit)` — is applied at
  once (`amount`, `unit` are bindable, `onapply` fires); a click outside or Escape closes the editor

**Used by**: the custom window of `DateRangePicker`, the calendar-return window of the asset
detail page.

---

## 📊 Display blocks {: #display-blocks }

*Located in `lib/components/ui/display/`* — generic presentation blocks, kept out of `dashboard/`
and `risk/` so any panel can reuse them.

| Component | What it draws | Used by |
|---|---|---|
| `KpiMetricBar` | Label, value and a horizontal bar (`barPct`, clamped to 0–100, non-finite → 0), with an optional caret `marker`; `numericValue` + `formatValue` animate the value | `KpiSection` |
| `KpiDivergingFlowBar` | A bar growing left or right of a centre line: two magnitudes (`depositPct`, `withdrawPct`) or one signed value (`signedPct`); `layout` `stacked` or `inline` | `KpiSection`, risk L2 |
| `RiskMetricCard` | One risk metric: plain-language `label` with its `technicalName`, animated value, `caption`, `sentiment` accent, `docsPath` ⓘ link, optional `submetrics`/`sparkline`; the number scales with the card (container queries) and the value line keeps its place while `loading` | risk levels L1–L2 |
| `RiskCardGrid` | The layout of risk cards: `auto-fit` columns of at least `minWidth` (default `16rem`), no breakpoints, rows always full (the column count drops to a divisor of the card count) | risk levels L1–L2 |
| `CurrencyAmount` | One money amount through `formatCurrencyAmountHtml`, rendered in runes mode so a legacy parent follows the privacy toggle — see [legacy components](../../state/app-state.md#privacy-legacy-freeze) | `BrokerCard`, broker detail, import gap fix |
| `BrokerBadge` | Inline broker name with its icon fallback chain | Lots views, import wizard, transaction modals |
| `CompactCashCell` | Compact `{amount, currency}` editor for table cells, with a sign hint | `TransactionFormModal`, WAC preview |
