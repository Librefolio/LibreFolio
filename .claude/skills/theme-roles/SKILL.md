---
name: theme-roles
description: "Use this skill when migrating a frontend component to the colour roles (bg-lf-*, text-lf-*, border-lf-*…), choosing colours for new UI, or touching the colour ratchet baseline (frontend/src/themeRoles.baseline.tsv): converting palette classes, declaring a file split, resolving a merge conflict on the baseline, reading the colour gates' failures."
---

# Colour roles — migrating the interface

> **Building or changing UI?** Start from the skill [`design-system`](../design-system/SKILL.md): the two themes
> («Stone and Sage», «Slate and Sage»), every role and when to use it (its light and dark values in
> [`palette.md`](../design-system/palette.md)), the shared colour folder `lib/theme/`, the contrast pairs and all the
> rules. This skill is about migrating what still writes palette
> classes, and about the ratchet's baseline.

## The one idea

A colour in the interface says **what it is for**: a card, the muted text, the border of a field, an error. Each of
those meanings is one **role**, a CSS variable `--lf-<group>-<name>` in `frontend/src/lib/theme/tokens.css`. Each role
is exposed as a Tailwind utility through `@theme inline`: `bg-lf-card`, `text-lf-muted`, `border-lf-input`,
`text-lf-danger`.

- The role changes value with the theme. The designer tunes it in one place.
- A component that uses roles follows the palette everywhere, in light and in dark, with no `dark:` at all.

The rest of the frontend still writes palette classes (`bg-white dark:bg-slate-800`, `text-gray-500`) and keeps
today's look until it migrates. The gates make sure the old way only shrinks.

## Roles → utilities

The full table, with the light and dark values, is in `tokens.css`.

| Meaning | Utility |
|---|---|
| Background behind the app shell (pages) | `bg-lf-app` (today the same colour as `page`) |
| The app header (D-T23): a step darker than the page in light, lighter in dark | `bg-lf-header text-lf-primary border-b border-lf-subtle`; its controls in their page look (`text-lf-secondary hover:bg-lf-hover`, focus `focus-visible:outline-lf-focus`) |
| Background of a standalone page (login, error) | `bg-lf-page` |
| The green sidebar (D-T17): one family in both themes | `bg-lf-bar text-lf-bar-text`, no edge (D-T23), dividers `border-lf-bar-line`, quiet text `text-lf-bar-muted`, `hover:bg-lf-bar-hover`; active item `bg-lf-bar-active text-lf-on-bar-active border-l-4 border-lf-bar-indicator`; logout `bg-lf-bar-logout hover:bg-lf-bar-logout-hover`; focus `focus-visible:outline-lf-bar-focus`; states on the bar `text-lf-bar-success`, `-warning`, `-danger` |
| Card, modal, menu, dropdown | `bg-lf-card`; one that floats (modal, menu, dropdown, the login card) adds `border-lf-raised` and `shadow-lf-shadow` (N3, Q8); a card of a page `shadow-lf-shadow-card` |
| Secondary surface: panels, table heads, boxes inside a card | `bg-lf-panel` |
| Inside of an input | `bg-lf-field` |
| Hovered row or item | `hover:bg-lf-hover` |
| Neutral fill: tracks, skeletons, neutral chips | `bg-lf-neutral` |
| Tooltip | `bg-lf-inverse` with `text-lf-on-inverse` |
| Modal backdrop | `bg-lf-overlay` |
| Tile behind the logo | `bg-lf-logo` |
| Primary text | `text-lf-primary` |
| Secondary text: labels, subtitles | `text-lf-secondary` |
| Muted text, also disabled | `text-lf-muted` |
| Placeholder | `placeholder:text-lf-placeholder` |
| Link, active item | `text-lf-link` |
| Border, divider | `border-lf-subtle`, `divide-lf-subtle` |
| Border of an input | `border-lf-input`, under the mouse `hover:border-lf-input-hover` (D-T18; focus wins over it) |
| Focus | `focus:ring-lf-focus`, `focus:border-lf-focus`, `focus-visible:outline-lf-focus`; on the green sidebar `focus-visible:outline-lf-bar-focus` |
| Brand surface: the login card header | `bg-lf-brand` with `text-lf-on-brand` (`/70` for secondary text, `border-lf-on-brand/20`, `bg-lf-on-brand/10` for hovers) |
| Primary button | `bg-lf-action hover:bg-lf-action-hover text-lf-on-action` |
| Selected item | `bg-lf-selected`; its text primary, secondary or link (not over a panel), never muted (design-system rule 5) |
| Selected control: checkbox, radio, switch on, selected day or preset, active segment (D-T16) | `bg-lf-checked` with `text-lf-on-checked` for its mark |
| Switch (Q2) | track `bg-lf-switch-off`, on `bg-lf-checked`; knob `bg-lf-switch-knob-off border border-lf-input`, on `bg-lf-switch-knob-on` |
| State, with X = `success`, `warning`, `danger`, `info` | `text-lf-X` (text, icon); `bg-lf-X-soft` + `border-lf-X-line` + `text-lf-X-on-soft` (alert, badge); `bg-lf-X text-lf-on-status` (solid) |
| Solid red button, e.g. «Delete account» (Q3) | `bg-lf-danger-solid hover:bg-lf-danger-hover text-lf-on-danger-solid`; a solid warning hovers with `hover:bg-lf-warning-hover` |
| Warning inside a tooltip (Q10) | `text-lf-warning-on-inverse`: the other theme's warning, on the inverted tooltip |
| AI functions (Q11) | `text-lf-ai`, `bg-lf-ai-soft`, `border-lf-ai-line`; solid `bg-lf-ai text-lf-on-ai` |
| Terminal block, dark in both themes (Q6) | `bg-lf-terminal border-lf-terminal-line text-lf-on-terminal`; prompt and commands `text-lf-terminal-prompt`; comments `text-lf-terminal-comment`. Inline code: `bg-lf-panel border-lf-subtle text-lf-primary` |
| Highlighted result, `<mark>` (Q7) | `bg-lf-mark text-lf-on-mark border-lf-mark-line` |
| Guided tour glow (Q9) | `var(--lf-tour-glow)`, backdrop `bg-lf-overlay` |
| Signed figures | `text-lf-gain`, `text-lf-loss` |
| Donation link («Offrimi un caffè») | `text-lf-donate hover:text-lf-donate-hover` |

Opacity works on every role: `bg-lf-card/90`, `border-lf-on-brand/20`.

**Roles without a utility.** The login illustration (`ui/AnimatedBackground.svelte`) reads `--lf-art-hill-1…3` and
`--lf-art-line` with `var()` in its `<style>`: the alpha of each colour is the strength of its layer. A `<style>` block
reads any role that way, `var(--lf-…)`, never a literal.

## Converting a component

Convert by **meaning and step**, not by colour family: `gray` and `slate` go to the same roles.

| Today (light + dark) | Role |
|---|---|
| `bg-white` + `dark:bg-slate-800/900` on cards, modals, menus | `bg-lf-card` |
| `bg-white` on inputs | `bg-lf-field` |
| `bg-gray-50/100`, `bg-slate-50` + `dark:bg-slate-700/800/900` | `bg-lf-panel` |
| `bg-gray-200` (tracks, skeletons) | `bg-lf-neutral` |
| `hover:bg-gray-50/100` + `dark:hover:bg-slate-600/700` | `hover:bg-lf-hover` |
| `bg-libre-beige` | by context: `bg-lf-app` (in the shell), `bg-lf-page` (standalone page), `bg-lf-card` (card, modal body) |
| `bg-black/40–50`, `bg-slate-900/30–70`, `bg-gray-900/40–50` (backdrops) | `bg-lf-overlay` |
| `text-gray-900/800`, `text-libre-dark` + `dark:text-gray-100/200`, `white` | `text-lf-primary` |
| `text-gray-700/600` + `dark:text-gray-300/200` | `text-lf-secondary` |
| `text-gray-500/400/300` + `dark:text-gray-400/500` | `text-lf-muted` |
| `border-gray-100/200` + `dark:border-slate-600/700` | `border-lf-subtle` |
| `border-gray-300/400` on inputs + `dark:border-slate-600` | `border-lf-input` |
| `bg-libre-green text-white hover:bg-libre-green/90` (button) | `bg-lf-action text-lf-on-action hover:bg-lf-action-hover` |
| `bg-libre-green` on headers and banners | `bg-lf-brand text-lf-on-brand` |
| `text-libre-green` + `dark:text-green-400` (links, accents) | `text-lf-link` |
| `bg-libre-green/10` + `dark:bg-libre-green/20` | `bg-lf-selected` |
| `focus:ring-libre-green`, `focus:border-libre-green` | `focus:ring-lf-focus`, `focus:border-lf-focus` |
| `red`/`rose`, `amber`/`yellow`/`orange`, `emerald`/`green`, `blue`/`sky` used for a state | the state roles: text 500–700 → `text-lf-X`; bg 50–100 → `-soft`; border 200–400 → `-line`; text 800–900 on a tint → `-on-soft`; `bg-*-500/600 text-white` → `bg-lf-X text-lf-on-status` |
| `violet`, `purple`, `indigo`, `pink`, `teal`, `cyan`, `fuchsia`, `lime` (categories: broker roles, file kinds, identifiers) | **leave them**: categorical roles come later. The AI violet is not a category: the `ai` roles (Q11); the asset types have their roles since round 3: their badges come from `assetTypeBadgeClass()` (design-system, rule 11) |

## Rules

1. **An element migrates whole.**
   - Never put a role utility and a palette class on the same element, or in the same class string.
   - `app.css` exempts every element carrying a `-lf-` class from its legacy dark remap: a half-migrated element would
     keep half of its old colours in dark.
   - If an element cannot migrate yet (a categorical colour), leave it entirely as it is.
2. **No `dark:` on a role.** The role already changes with the theme. Drop the `dark:` half of every converted pair.
3. **Set the text role on the component's root** (`text-lf-primary`): in dark, `body` still passes the legacy text
   colour down until the clean-up.
   - **And on every native field**, with its placeholder role: `<input class="… text-lf-primary
     placeholder:text-lf-placeholder">`, the same on `<textarea>` and `<select>`, even inside a parent that already
     gives the colour. `app.css` colours native fields in dark only while they carry no `-lf-` class, so a migrated
     field falls back to the preflight: the inherited colour, the placeholder at 50 % of it.
4. **Every `border` names its role** (`border border-lf-subtle`): Tailwind v4 draws an unnamed border in
   `currentColor`.
5. **No hand-written colours.**
   - No hex, `rgb()`, `hsl()` or colour names in markup, scripts or `<style>`.
   - No arbitrary values (`bg-[#…]`), except `bg-[var(--lf-…)]`.
   - A colour a library draws (ECharts, canvas) comes from the theme tables of `lib/theme/`, not from a literal.
6. **Class names stay whole literals.** Never build them from pieces (`'bg-lf-' + x`): Tailwind would not generate
   them, and the gate cannot see them.
7. **Shared files** (shell, header, files other workstreams also edit): change classes only, never reorder the markup.
8. **One property, one ternary** (Tailwind 4 order).
   - Two base utilities that set the same property on one element come out **sorted by name**, and the later one wins;
     their order in the `class` string does not count. `border-lf-input` (always on) beat `border-lf-focus` (only when
     open), and an open select lost its focus border. The legacy pair had worked by luck: `border-gray-300` sorts
     before `border-libre-green`.
   - So the idle and the state colour of one property are the branches of one ternary, and the idle `hover:` sits in
     the idle branch: `{open ? 'border-lf-focus' : 'border-lf-input hover:border-lf-input-hover'}`.
   - Variants (`hover:`, `focus:`, `aria-*:`) come after base utilities and add specificity. A state that must beat a
     colour the caller passes in can be a variant (`aria-invalid:border-lf-danger`).
   - A class prop (`className`, `contentClass`, `triggerClass`, `fieldClass`, `tab.className`) meets the component's
     own classes under the same name order: check the caller's colours before migrating either side.
   - A colour in a component's `<style>` beats every utility, a caller's class included: keep colours a caller may
     override in the markup.
   - The gate checks it (G5), through the classes, the `{…}`, the `class:` directives and the UPPER_CASE string
     constants of the element, imported ones included. A class prop stays out of its sight: check its callers.
   - Details: devWiki `problems/tailwind4-same-property-utilities-sorted-by-name`.

## Gates and the baseline

- `src/themeRoles.gate.test.ts`:
  - **the ratchet:** per file, m1 legacy colour classes and m2 colour literals, compared as a multiset of values, so
    swapping one colour for another fails;
  - **the grammar:** G1 no `dark:` on a role, G2 no unknown role, G3 no mixed element, G4 no arbitrary colour, G5 one
    property, one ternary (rule 8), G6 a native field names its text and placeholder roles (rule 3).
- `src/themeTokens.gate.test.ts`: both themes declared, the utility table, the contrast pairs, no dead rule in the
  legacy remap.
- `src/themeColorMeta.gate.test.ts`: the PWA title bar, `#1b4334` in both themes (N2, D-T17), the same in its three
  copies (`app.html`, `themeStore.ts`, `offline.html`) and equal to `--lf-surface-bar`; and the static copies of the
  roles in the splash of `app.html` and in `static/offline.html`, which paint without the app's stylesheet. **Change a
  role they copy, and change the copy in the same commit.**
- **Run them:** with the runner (`front-utility core-unit`), or alone with
  `node frontend/scripts/theme/theme-roles.mjs --check`. `--report` shows what is left, area by area.

The baseline `frontend/src/themeRoles.baseline.tsv` has one line per file, sorted, with no totals.

**Who writes it:**
- `--update`, which only tightens, at the colour checkpoints (workstream T);
- `--split`, in the commit of a split;
- `--resolve`, on a merge.

`--accept` takes a file as it is: only with the colour coordinator's OK.

**A file split** (one file becomes several, the old one possibly staying as one of the parts). Run, in the same
commit as the split, with paths under `frontend/src`:

```bash
node frontend/scripts/theme/theme-roles.mjs --split lib/components/assets/AssetModal.svelte:lib/components/assets/AssetModalPrices.svelte,lib/components/assets/AssetModalProvider.svelte
```

- Each part's line starts from what it measures.
- Together the parts may hold no more legacy classes and no other colour literals than the old file had.
- A `~split` line records the declaration in the diff.
- A pure move or rename needs nothing: the gate pairs a file that left the tree with a new one of the same name.

**A merge conflict on the baseline** is a three-way merge, line by line (TC-7):
1. A line one side left as the base had it takes the other side's line: its change, its removal, its addition.
2. A line both sides changed: the side that accepted the file (a new `~accept` line) keeps it; if both sides accepted
   it, the merge stops — merge the sources, then `--accept` the file again on the merged tree. Otherwise the tighter
   side wins: the lower m1, the m2 values both sides have; a line removed on one side stays removed.
3. `node frontend/scripts/theme/theme-roles.mjs --resolve` does it from the three index stages. Then `git add` the
   file.
4. The gate must pass on the merged tree. If it does not, there is a real regression or a missing split declaration:
   fix that. **Never widen the baseline to make it pass.**

## Checklist for a migration batch

1. Only the files assigned to you. If one of them is also being split or moved by another session, stop and ask.
2. Convert every colour class of each element with the tables above; drop the `dark:` halves.
3. Remove hand-written colours, or report them if a role is missing.
4. Leave categorical colours as they are, and report them.
5. Do not run tests, builds or servers: the workstream runs the gates in its lane.
6. Report:
   - the files;
   - the elements you could not convert, and why;
   - roles that seemed missing;
   - any tests that assert the old classes. Tests should read `data-*` or `aria-*` state, not colours.
