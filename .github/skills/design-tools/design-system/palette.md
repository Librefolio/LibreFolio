# LibreFolio palette: every colour role, in both themes

The companion of [`SKILL.md`](SKILL.md), the design system (the themes, the shared colour folder, the rules). This file
holds every role of [`tokens.css`](../../../../frontend/src/lib/theme/tokens.css): its utility, its value in the light
and in the dark theme, and when to use it. Rule numbers and open questions refer to `SKILL.md`.

- **The values** are copied from `tokens.css` by a script and checked against it: every role has exactly one row, with
  its own utilities. If they ever differ, `tokens.css` wins, and whoever changes a role (T) updates this file in the
  same commit.
- Every utility takes an opacity: `bg-lf-card/90`, `border-lf-on-brand/20`.
- Paths are under `frontend/`.

## Surfaces

| Role | Utility | Light | Dark | When to use |
|---|---|---|---|---|
| `--lf-surface-app` | `bg-lf-app` | `#f3f5f3` | `#0d1110` | Behind the app shell: the background of every page inside the app. The same colour as `page` since round 2 |
| `--lf-surface-page` | `bg-lf-page` | `#f3f5f3` | `#0d1110` | A page outside the shell: login, sign-up, welcome, error, offline, splash, server unreachable |
| `--lf-surface-card` | `bg-lf-card` | `#fafbfa` | `#151b19` | Cards, modals, menus, dropdowns, popovers |
| `--lf-surface-panel` | `bg-lf-panel` | `#e8ece9` | `#1b2421` | The secondary surface: panels, table heads, boxes inside a card, the track of a segmented control, a secondary button, inline code |
| `--lf-surface-field` | `bg-lf-field` | `#ffffff` | `#0f1413` | The inside of an input, a select trigger, a textarea |
| `--lf-surface-hover` | `hover:bg-lf-hover` | `#e8ece9` | `#1b2421` | A row or an item under the pointer, on a card or a page. It equals `panel`: on a panel, hover with `hover:bg-lf-neutral` (open question 3) |
| `--lf-surface-neutral` | `bg-lf-neutral` | `#d8e0dc` | `#222c28` | Neutral fills: progress tracks, skeletons, neutral chips; the hover of a control that sits on a panel |
| `--lf-surface-logo` | `bg-lf-logo` | `#ffffff` | `#ffffff` | The tile behind the logo: white in both themes, on the green too (N1) |

## Text

| Role | Utility | Light | Dark | When to use |
|---|---|---|---|---|
| `--lf-text-primary` | `text-lf-primary` | `#1c2420` | `#edf2f0` | Body text, titles, values. Set it on the root of every component (rule 1) |
| `--lf-text-secondary` | `text-lf-secondary` | `#4a5550` | `#9ba8a2` | Labels, subtitles, the caption of a value, the text of a secondary button |
| `--lf-text-muted` | `text-lf-muted`; `bg-lf-muted` for the dot | `#616d67` | `#7f8c87` | Hints, timestamps, inactive icons, disabled text, the «inactive» status dot (Q5) |
| `--lf-text-placeholder` | `placeholder:text-lf-placeholder` | `#616d67` | `#7f8c87` | The placeholder of a field: the muted text |

## Borders

| Role | Utility | Light | Dark | When to use |
|---|---|---|---|---|
| `--lf-border-subtle` | `border-lf-subtle`, `divide-lf-subtle` | `#d8e0dc` | `#222c28` | Borders and dividers of cards, tables and sections; the edge of inline code |
| `--lf-border-raised` | `border-lf-raised` | `#d8e0dc` | `#2e3b36` | The border of a surface that floats: modal, dropdown, menu, popover, the login card (N3) |
| `--lf-border-input` | `border-lf-input` | `#7e8984` | `#606f6a` | The border of a field or a control at rest, 3:1 on every surface (D-T18); the edge of a switch knob turned off |
| `--lf-border-input-hover` | `hover:border-lf-input-hover` | `#616d67` | `#7f8c87` | The border of a field under the pointer: the muted text colour (D-T18). `focus:border-lf-focus` wins over it |

## Brand and action

| Role | Utility | Light | Dark | When to use |
|---|---|---|---|---|
| `--lf-brand` | `bg-lf-brand` | `#1b4334` | `#1b4334` | The brand green as a surface: the header of the login card. The sidebar has a family of its own (`bar`), on the same green |
| `--lf-on-brand` | `text-lf-on-brand` | `#fafbfa` | `#edf2f0` | Text and icons on the brand green; `/70` for its secondary text, `/20` for its borders, `/10` for a hover |
| `--lf-action` | `bg-lf-action` | `#1b4334` | `#215240` | The primary button: the action the view is for |
| `--lf-action-hover` | `hover:bg-lf-action-hover` | `color-mix(in oklab, #1b4334 70%, #236b4d)` | `#28634e` | The primary button under the pointer (provisional in light: toward the focus green) |
| `--lf-on-action` | `text-lf-on-action` | `#fafbfa` | `#edf2f0` | Text and icons on the primary button |

## Focus, links and selection

| Role | Utility | Light | Dark | When to use |
|---|---|---|---|---|
| `--lf-focus` | `focus-visible:outline-lf-focus`, `focus:ring-lf-focus`, `focus:border-lf-focus` | `#236b4d` | `#429e79` | Keyboard focus, and the border of a focused field, on every neutral surface (3:1). On the sidebar, `--lf-bar-focus` |
| `--lf-link` | `text-lf-link` | `#236b4d` | `#429e79` | Links, the active item inside a page, accent icons. The focus green: the designer's «Focus, link attivi» |
| `--lf-selected` | `bg-lf-selected` | `color-mix(in oklab, #236b4d 12%, transparent)` | `color-mix(in oklab, #429e79 12%, transparent)` | A selected or highlighted row, option, item or date range: a quiet tint of the focus green. Its text: `text-lf-primary`, `text-lf-secondary`, or `text-lf-link` except over a `panel`; never muted, a status or a sign (SKILL.md, rule 5) |
| `--lf-checked` | `bg-lf-checked` | `#236b4d` | `#429e79` | A selected control: checkbox, radio, switch turned on, selected day or preset, active segment (D-T16) |
| `--lf-on-checked` | `text-lf-on-checked` | `#fafbfa` | `#151b19` | The mark on a checked fill: the tick, the dot, the number of the selected day |
| `--lf-tour-glow` | `ring-lf-tour-glow`, or `var(--lf-tour-glow)` in a shadow | `color-mix(in oklab, #236b4d 40%, transparent)` | `color-mix(in oklab, #429e79 40%, transparent)` | The glow of the guided tour around the element it shows (Q9) |

## States

Four families: `success`, `warning`, `danger`, `info`. **Each one comes as a set**, never split:
- `text-lf-X` for a state as text or icon;
- `bg-lf-X-soft border-lf-X-line text-lf-X-on-soft` for an alert, a banner, a badge, a row in that state;
- `bg-lf-X text-lf-on-status` for a solid fill (a toast, a solid badge), and `hover:bg-lf-X-hover` for a solid button
  hovered.

| Role | Utility | Light | Dark | When to use |
|---|---|---|---|---|
| `--lf-success` | `text-lf-success`, `bg-lf-success` | `#18794e` | `#5ed69a` | A success as text or icon (✓, «Strong»), or its solid fill |
| `--lf-success-soft` | `bg-lf-success-soft` | `#e6f4ed` | `#13261e` | The tint of a success alert, badge or row |
| `--lf-success-line` | `border-lf-success-line` | `#b8dfca` | `#1f4435` | Its border |
| `--lf-success-on-soft` | `text-lf-success-on-soft` | `#145937` | `#86efac` | Text on the success tint |
| `--lf-success-hover` | `hover:bg-lf-success-hover` | `color-mix(in oklab, #18794e 80%, #1c2420)` | `color-mix(in oklab, #5ed69a 80%, #edf2f0)` | A solid success button under the pointer, with `text-lf-on-status`. **Provisional** (open question 5): 20 % toward the primary text (≈ `#1f6744` in light, `#81dcab` in dark), so it moves away from its text in both themes; 6.58:1 in light, 10.63:1 in dark |
| `--lf-warning` | `text-lf-warning`, `bg-lf-warning` | `#ae4e00` | `#f59e0b` | A warning as text or icon, or its solid fill; the «modified» state of a setting (Q4) |
| `--lf-warning-soft` | `bg-lf-warning-soft` | `#fef3c7` | `#291e0c` | The tint of a warning alert, badge or row |
| `--lf-warning-line` | `border-lf-warning-line` | `#fde68a` | `#54380e` | Its border |
| `--lf-warning-on-soft` | `text-lf-warning-on-soft` | `#92400e` | `#fcd34d` | Text on the warning tint |
| `--lf-warning-hover` | `hover:bg-lf-warning-hover` | `#92400e` | `#d97706` | A solid warning button under the pointer (Q3) |
| `--lf-danger` | `text-lf-danger`, `bg-lf-danger` | `#c82838` | `#ff7a86` | An error as text, icon or border (an invalid field), or its solid fill. A softer red in dark (D-T25) |
| `--lf-danger-soft` | `bg-lf-danger-soft` | `#ffe5e5` | `#2a1417` | The tint of an error alert, badge or row |
| `--lf-danger-line` | `border-lf-danger-line` | `#fecaca` | `#581c24` | Its border |
| `--lf-danger-on-soft` | `text-lf-danger-on-soft` | `#991b1b` | `#fca5a5` | Text on the error tint |
| `--lf-danger-solid` | `bg-lf-danger-solid` | `#c82838` | `#e1284f` | A solid destructive button, «Delete account» (Q3): it carries white text, which `danger` cannot in dark |
| `--lf-danger-hover` | `hover:bg-lf-danger-hover` | `#a81f2d` | `#d51c42` | That button under the pointer |
| `--lf-on-danger-solid` | `text-lf-on-danger-solid` | `#ffffff` | `#ffffff` | Its white text, at rest and hovered |
| `--lf-info` | `text-lf-info`, `bg-lf-info` | `#155eef` | `#3f86fa` | Information as text or icon, or its solid fill |
| `--lf-info-soft` | `bg-lf-info-soft` | `#deedff` | `#131f33` | The tint of an info alert, badge or row |
| `--lf-info-line` | `border-lf-info-line` | `#bfdbfe` | `#1e3a5f` | Its border |
| `--lf-info-on-soft` | `text-lf-info-on-soft` | `#1e40af` | `#93c5fd` | Text on the info tint |
| `--lf-info-hover` | `hover:bg-lf-info-hover` | `color-mix(in oklab, #155eef 80%, #1c2420)` | `color-mix(in oklab, #3f86fa 80%, #edf2f0)` | A solid info button under the pointer, with `text-lf-on-status`. **Provisional**, as `success-hover` (≈ `#1854c2` in light, `#639efa` in dark): 6.54:1 in light, 6.47:1 in dark (a darker hover would fall under 4.5:1 in dark) |
| `--lf-on-status` | `text-lf-on-status` | `#fafbfa` | `#151b19` | Text on a solid state fill (toasts, solid badges) and on a solid warning or donation button hovered |

## Gain, loss and donation

A sign, never a state (rule 7): as text `text-lf-gain`, `text-lf-loss`; on a tint, `SIGN_BADGE` of `toneClasses.ts`.

| Role | Utility | Light | Dark | When to use |
|---|---|---|---|---|
| `--lf-gain` | `text-lf-gain` | `#18794e` | `#5ed69a` | A positive signed figure: P&L, return, a price that went up (rule 7). Today the value of `success` |
| `--lf-loss` | `text-lf-loss` | `#c82838` | `#ff7a86` | A negative signed figure. Today the value of `danger` |
| `--lf-gain-soft` | `bg-lf-gain-soft` | `#e6f4ed` | `#13261e` | A gain on a tint: a badge or a chip that says gain or loss, not a state (`SIGN_BADGE` of `toneClasses.ts`). Today the success tint, kept a role of its own |
| `--lf-gain-on-soft` | `text-lf-gain-on-soft` | `#145937` | `#86efac` | Text on the gain tint |
| `--lf-loss-soft` | `bg-lf-loss-soft` | `#ffe5e5` | `#2a1417` | A loss on a tint. Today the danger tint, kept a role of its own |
| `--lf-loss-on-soft` | `text-lf-loss-on-soft` | `#991b1b` | `#fca5a5` | Text on the loss tint |
| `--lf-donate` | `text-lf-donate` | `#ae4e00` | `#f59e0b` | The donation link «Offrimi un caffè»: the warm amber of `warning` |
| `--lf-donate-hover` | `hover:text-lf-donate-hover` | `#92400e` | `#d97706` | The donation link under the pointer (Q3) |

## The tooltip, an inverted surface

| Role | Utility | Light | Dark | When to use |
|---|---|---|---|---|
| `--lf-surface-inverse` | `bg-lf-inverse` | `#1c2420` | `#edf2f0` | The tooltip: dark in the light theme, light in the dark theme (the primary text colour) |
| `--lf-text-on-inverse` | `text-lf-on-inverse` | `#fafbfa` | `#151b19` | The text of a tooltip (the card colour) |
| `--lf-warning-on-inverse` | `text-lf-warning-on-inverse` | `#f59e0b` | `#ae4e00` | A warning inside a tooltip: the other theme's warning (Q10, rule 6) |
| `--lf-danger-on-inverse` | `text-lf-danger-on-inverse` | `#ff7a86` | `#c82838` | An error inside a tooltip: the other theme's danger |
| `--lf-info-on-inverse` | `text-lf-info-on-inverse` | `#3f86fa` | `#155eef` | Information, links and formulas inside a tooltip: the other theme's info |
| `--lf-text-muted-on-inverse` | `text-lf-muted-on-inverse` | `#7f8c87` | `#616d67` | Muted text inside a tooltip: the other theme's muted text |

## Backdrops and shadows

| Role | Utility | Light | Dark | When to use |
|---|---|---|---|---|
| `--lf-surface-overlay` | `bg-lf-overlay` | `color-mix(in oklab, #0d1110 60%, transparent)` | `color-mix(in oklab, #0d1110 60%, transparent)` | The backdrop of a modal and of the guided tour: the dark page at 60 %, in both themes (Q13) |
| `--lf-on-overlay` | `text-lf-on-overlay` | `#ffffff` | `#ffffff` | Text and icons on the backdrop: a camera on an avatar, an icon on a scrim. **Provisional** (open question 5): white in both themes, 4.98:1 at worst, the backdrop over a white field |
| `--lf-shadow-raised` | `shadow-lf-shadow` | `color-mix(in oklab, #0d1110 25%, transparent)` | `color-mix(in oklab, #0d1110 50%, transparent)` | The shadow colour of a floating surface, beside a size: `shadow-xl shadow-lf-shadow` (Q8) |
| `--lf-shadow-card` | `shadow-lf-shadow-card` | `color-mix(in oklab, #0d1110 7%, transparent)` | `color-mix(in oklab, #0d1110 40%, transparent)` | The shadow colour of a card on a page: `shadow-sm shadow-lf-shadow-card` (provisional in dark) |

## The shell: sidebar and header

| Role | Utility | Light | Dark | When to use |
|---|---|---|---|---|
| `--lf-surface-header` | `bg-lf-header` | `#edf0ee` | `#111615` | The app header, desktop and mobile: a step darker than the page in light, lighter in dark (D-T23). Bottom border `border-lf-subtle`; its controls keep their page look |
| `--lf-surface-bar` | `bg-lf-bar` | `#1b4334` | `#1b4334` | The sidebar, green in both themes, desktop and mobile (D-T17), with no right edge (D-T23) |
| `--lf-bar-border` | `border-lf-bar-line` | `#265946` | `#265946` | Dividers inside the sidebar |
| `--lf-bar-text` | `text-lf-bar-text` | `#cfe0d8` | `#cfe0d8` | Inactive items, their icons, secondary information |
| `--lf-bar-text-muted` | `text-lf-bar-muted` | `#a0bcaf` | `#a0bcaf` | The version, the e-mail under the name |
| `--lf-bar-hover` | `hover:bg-lf-bar-hover` | `#21503e` | `#21503e` | An inactive item under the pointer |
| `--lf-bar-active-bg` | `bg-lf-bar-active` | `#285e49` | `#285e49` | The active item |
| `--lf-bar-active-text` | `text-lf-on-bar-active` | `#ffffff` | `#ffffff` | The text and icon of the active item; the username |
| `--lf-bar-indicator` | `border-lf-bar-indicator` | `#52c493` | `#52c493` | The mark on the left of the active item (`border-l-4`) |
| `--lf-bar-logout-bg` | `bg-lf-bar-logout` | `#153529` | `#153529` | The logout button |
| `--lf-bar-logout-hover` | `hover:bg-lf-bar-logout-hover` | `#21503e` | `#21503e` | The logout button under the pointer |
| `--lf-bar-focus` | `focus-visible:outline-lf-bar-focus` | `#52c493` | `#52c493` | Keyboard focus on the green, where the page's `--lf-focus` would reach 1.73:1 |
| `--lf-bar-success` | `text-lf-bar-success` | `#5ed69a` | `#5ed69a` | A success on the green (the connection security): the dark theme's bright state, in both themes (D-T26) |
| `--lf-bar-warning` | `text-lf-bar-warning` | `#fbbf24` | `#fbbf24` | A warning on the green |
| `--lf-bar-danger` | `text-lf-bar-danger` | `#ff7a86` | `#ff7a86` | A danger on the green (D-T25) |

The installed app's title bar (`<meta name="theme-color">`) continues the sidebar: `#1b4334` in both themes (N2,
D-T24). Three static copies write it (`src/app.html`, `src/lib/stores/app/themeStore.ts`, `static/offline.html`), and
the splash and the offline page copy a few roles too: `src/themeColorMeta.gate.test.ts` keeps them equal to
`tokens.css`. Change a role they copy, and change the copy in the same commit.

## Controls and special surfaces

| Role | Utility | Light | Dark | When to use |
|---|---|---|---|---|
| `--lf-switch-off` | `bg-lf-switch-off` | `#cbd4d0` | `#2c3834` | The track of a switch turned off: never green (Q2). Turned on, the track is `bg-lf-checked` |
| `--lf-switch-knob-off` | `bg-lf-switch-knob-off` | `#ffffff` | `#9ba8a2` | The knob of a switch turned off, with `border border-lf-input`: in light the edge is what makes the switch readable |
| `--lf-switch-knob-on` | `bg-lf-switch-knob-on` | `#ffffff` | `#ffffff` | The knob of a switch turned on, over `bg-lf-checked` |
| `--lf-terminal-bg` | `bg-lf-terminal` | `#0d1110` | `#0d1110` | A terminal block, dark in both themes (Q6). Inline code is not a terminal: `bg-lf-panel border-lf-subtle text-lf-primary` |
| `--lf-terminal-border` | `border-lf-terminal-line` | `#222c28` | `#222c28` | The terminal's border |
| `--lf-terminal-text` | `text-lf-on-terminal` | `#edf2f0` | `#edf2f0` | The terminal's text |
| `--lf-terminal-prompt` | `text-lf-terminal-prompt` | `#36d399` | `#36d399` | The prompt and the commands |
| `--lf-terminal-comment` | `text-lf-terminal-comment` | `color-mix(in oklab, #edf2f0 60%, #0d1110)` | `color-mix(in oklab, #edf2f0 60%, #0d1110)` | Comments (`# Docker`); provisional |
| `--lf-mark-bg` | `bg-lf-mark` | `#fde68a` | `#78350f` | A highlighted search result, `<mark>` (Q7) |
| `--lf-mark-text` | `text-lf-on-mark` | `#1c2420` | `#fef3c7` | The text of a highlighted result |
| `--lf-mark-line` | `border-lf-mark-line`, `inset-ring-lf-mark-line` | `transparent` | `#b45309` | Its edge: none in light, amber in dark. An inset ring does not move the text around it |
| `--lf-ai` | `text-lf-ai`, `bg-lf-ai` | `#6d28d9` | `#a78bfa` | The AI accent (Q11): the AI Export's icons and choices; `bg-lf-ai` is a solid AI button, with `text-lf-on-ai` |
| `--lf-ai-soft` | `bg-lf-ai-soft` | `#f3e8ff` | `#1e1b2e` | The AI tint |
| `--lf-ai-line` | `border-lf-ai-line` | `#ddd6fe` | `#3b3054` | The border of the AI tint |
| `--lf-on-ai` | `text-lf-on-ai` | `#ffffff` | `#151b19` | Text on a solid AI fill; provisional |
| `--lf-art-hill-1` | — | `color-mix(in oklab, #9caf9c 25%, transparent)` | `#16221d` | The login illustration (`src/lib/components/ui/AnimatedBackground.svelte`), first hill. No utility: its `<style>` reads it with `var()`, and the alpha is the strength of the layer (N6) |
| `--lf-art-hill-2` | — | `color-mix(in oklab, #9caf9c 18%, transparent)` | `#121c18` | The login illustration, second hill |
| `--lf-art-hill-3` | — | `color-mix(in oklab, #9caf9c 12%, transparent)` | `#0f1714` | The login illustration, third hill |
| `--lf-art-line` | — | `color-mix(in oklab, #1b4334 30%, transparent)` | `#3b5249` | The lines of the login illustration (no dots on them, N6) |
