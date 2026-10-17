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
- Eye / EyeOff icon from lucide-svelte, on a `type="button"` that never submits the form and is
  disabled with the field
- The eye button is named after what a press does: `aria-label` and `title` are
  `$_('auth.showPassword')` while the field is masked, `$_('auth.hidePassword')` while it shows the
  text. It is in the tab order, and has no `aria-pressed` on purpose: a toggle whose name changes
  must not also report a pressed state (WAI-ARIA APG, Button pattern)
- `autocomplete` (`current-password` by default, or `new-password`, `off`, `on`), `id` and `name`
  are passed to the input: password managers rely on them — see the
  [password-manager contract](../features/auth.md#password-manager-contract)

**Used by**: [LoginCard, RegisterCard](../features/auth.md), `PasswordChangeModal`.

---

## 💪 PasswordStrength {: #passwordstrength }

*Located in `lib/components/ui/input/`*

A **password strength indicator** powered by `@zxcvbn-ts/core`.

- Strength bar with a label, from score 0 (very weak) to 4 (very strong), in three colours: danger,
  warning, success
- With `showRules` (default), a checklist of the
  [password rules](../../../architecture/security.md#password-rules) the server publishes
  (`GET /system/instance`), the five of release 1.3 until it answers, or of the rules a caller passes
  in `rules`, such as a secure backup's; its bindable `valid` tells a form whether they all hold
- Hidden while the password is empty

Details: [PasswordStrength](../features/auth.md#passwordstrength).

**Used by**: [RegisterCard](../features/auth.md) (below password field), `ResetPasswordCard`, `PasswordChangeModal`, `BackupDownloadCard` (a secure backup's password, with `rules`).

---

## 🔢 ExactDecimalInput {: #exactdecimalinput }

*Located in `lib/components/ui/input/`*

A **decimal text field that never goes through a JavaScript number**.

- `type="text"` with `inputmode="decimal"`: `,` and `.` both work as the decimal separator, and
  characters that can never belong to a number are filtered out while typing
- A number pasted in scientific notation is read exactly, never stripped of its `e` (W-B66;
  `filterDecimalInput`, and `normalizeDecimalInput` for every field that reads through it, in
  `lib/utils/core/parseDecimalInput.ts`): a text that is wholly such a number, with `.` or `,` as
  its decimal mark, is expanded to a plain decimal when its exponent is within ±100
  (`MAX_DECIMAL_EXPONENT`, the backend's bound): `1e-8` → `0.00000001`, `1,5E+3` → `1500`. The
  usual checks then apply to the result. Any other text holding an exponent — past ±100
  (`3E+150`), or not wholly a number (`1e5x`, `1.234,5e2`) — stays as typed, invalid, with a
  `<p>` after the field: `data-testid="<testid>-exponent-error"`, `data-max` 100, and
  `common.decimalExponentOutOfRange` (*Write the number out in full…*). A text without an
  exponent filters as before: a lone typed `e` is dropped, `EUR 12,34` gives `12,34`. Before, the
  filter dropped the `e`, so a pasted `1e-8` became `18`, silently
- `value` (bindable string) is the field text; on blur or Enter a valid value is rewritten in
  canonical form (`.` separator, trailing zeros trimmed), then `oncommit` fires. An invalid value
  stays as typed: never cut, never coerced on blur
- Validation is exact: digit budget (`maxIntegerDigits`, `maxFractionDigits`, default 12 each),
  `min`/`max` (strings, compared as exact decimals with the value stripped of the zeros the budget
  does not count, once the digits fit the budget: a longer value is invalid anyway, and comparing
  the text would build a BigInt of every pasted digit, zeros included), `required`,
  `allowNegative`;
  `onvaliditychange` reports `{normalized, empty, syntaxValid, requiredValid, digitsValid,
  rangeValid, valid}`, and `externalInvalid` lets the parent mark it invalid. The digits are
  counted as the backend counts them (`_digit_counts` in `backend/app/db/precision.py`; W-B64):
  leading integer zeros and trailing fraction zeros are not digits of the value, so
  `0.10000000000` has one decimal, `5.0` none and `007` one integer digit.
  `decimalDigitCounts(value)` (`lib/utils/core/parseDecimalInput.ts`) gives these counts for a
  canonical decimal, with the value without those zeros (`stripped`). So `0.10000000000` is valid
  at `maxFractionDigits={10}`, `5.0` at `maxFractionDigits={0}` (the PAC priority fields; a blur
  commits it as `5`) and `0000000000001.5` at the default 12 integer digits
- A fraction longer than `maxFractionDigits`, its trailing zeros not counted, is flagged
  (`digitsValid: false`, `aria-invalid`, red border) and also said under the field: a `<p>`
  rendered right after the `<input>`, as its sibling, with
  `data-testid="<testid>-digits-error"` (when `testid` is set), `data-max` set to the
  budget, and a text that follows the budget (`common.decimalPlacesExceeded`, an ICU plural):
  *Whole numbers only* for `maxFractionDigits={0}`, as in the PAC priority fields,
  *At most 1 decimal place* for 1, *At most N decimal places* above. It is withdrawn as soon as
  the value is back within the budget. Too many integer digits and the other limits are flagged
  without a message. The field has no `maxlength`: the browser silently cut a longer paste down to
  a number that looked valid
- ↑/↓ step by `step` in exact decimal arithmetic, clamped to the bounds (to 0 without
  `allowNegative`); `accelerateOnHold` (default `false`) climbs by powers of ten while the key is
  held. A value whose text fits the budget steps from that text, its typed places kept (`1.50` →
  `2.50` at step 1); one whose text is longer, within the budget only because the zeros it starts
  or ends with are not counted, steps from the value without them, so no BigInt is as long as the
  text (`5.` followed by 40 000 zeros, ↑ at step 1 → `6`; W-B64). A value past the digit budget,
  or a text kept for its exponent, is not stepped
- The checks stay linear on a long paste: the regular expressions of `normalizeDecimalInput` and
  `formatDecimalForDisplay` (`lib/utils/core/formatDecimal.ts`) and its trailing-zero strip used
  to backtrack quadratically, about 3 s on a 40 000-character text, in the paster's own tab (W-B66);
  `decimalDigitCounts` drops its zeros with two loops, never a `/0+$/`, for the same reason

**Used by**: the PAC planner steps (targets, routing, fees, liquidity, prices).

---

## 📦 ExactQuantityInput {: #exactquantityinput }

*Located in `lib/components/ui/input/`*

`ExactDecimalInput` for **quantities**, with a controlled value.

- `value` is always the normalized draft (`.` separator), while the text the user types stays in a
  private buffer: a parent echoing the value back never rewrites `1,20` into `1.20` mid-typing;
  `resetKey` forces the buffer to reload
- A new value from the parent is shown in canonical form (`formatDecimalForDisplay`: `.`
  separator, trailing zeros trimmed) when its digits fit the budget, counted as `ExactDecimalInput`
  counts them: `0.10000000000` at `maxFractionDigits={10}` is shown `0.1` (W-B64). A value past
  the budget is shown as given, and refused: formatting would cut it to fit
- `signRule`: `positive`, `negative`, `nonzero`, `zero` or `any` (default) — a sign that breaks the
  rule makes the value invalid and the border red, a matching one turns it green
- `accelerateOnHold` defaults to `true`
- `testid` is passed to the inner field, so the message under it is `<testid>-digits-error`

**Used by**: the quantity field of `TransactionFormModal` (`tx-form-quantity`), with at most 15
integer digits (the backend's limit for a quantity, decision N63) and 10 fraction digits (the 10
decimals the backend keeps for a quantity), so a longer fraction shows
`tx-form-quantity-digits-error`.

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
