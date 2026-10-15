---
name: theme-roles
description: "Use this skill when migrating a frontend component to the colour roles (bg-lf-*, text-lf-*, border-lf-*…), choosing colours for new UI, or touching the colour ratchet baseline (frontend/src/themeRoles.baseline.tsv): converting palette classes, declaring a file split, resolving a merge conflict on the baseline, reading the colour gates' failures."
---

# Colour roles — migrating the interface

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
| Background behind the app shell (sidebar, header, pages) | `bg-lf-app` |
| Background of a standalone page (login, error) | `bg-lf-page` |
| Card, modal, menu, dropdown | `bg-lf-card` |
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
| Border of an input | `border-lf-input` |
| Focus | `focus:ring-lf-focus`, `focus:border-lf-focus`, `focus-visible:outline-lf-focus` |
| Brand surface: card headers, sidebar | `bg-lf-brand` with `text-lf-on-brand` (`/70` for secondary text, `border-lf-on-brand/20`, `bg-lf-on-brand/10` for hovers) |
| Primary button | `bg-lf-action hover:bg-lf-action-hover text-lf-on-action` |
| Selected item | `bg-lf-selected` |
| State, with X = `success`, `warning`, `danger`, `info` | `text-lf-X` (text, icon); `bg-lf-X-soft` + `border-lf-X-line` + `text-lf-X-on-soft` (alert, badge); `bg-lf-X text-lf-on-status` (solid) |
| Signed figures | `text-lf-gain`, `text-lf-loss` |
| Donation link («Offrimi un caffè») | `text-lf-donate` |

Opacity works on every role: `bg-lf-card/90`, `border-lf-on-brand/20`.

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
| `bg-libre-green` on headers, banners, the sidebar | `bg-lf-brand text-lf-on-brand` |
| `text-libre-green` + `dark:text-green-400` (links, accents) | `text-lf-link` |
| `bg-libre-green/10` + `dark:bg-libre-green/20` | `bg-lf-selected` |
| `focus:ring-libre-green`, `focus:border-libre-green` | `focus:ring-lf-focus`, `focus:border-lf-focus` |
| `red`/`rose`, `amber`/`yellow`/`orange`, `emerald`/`green`, `blue`/`sky` used for a state | the state roles: text 500–700 → `text-lf-X`; bg 50–100 → `-soft`; border 200–400 → `-line`; text 800–900 on a tint → `-on-soft`; `bg-*-500/600 text-white` → `bg-lf-X text-lf-on-status` |
| `violet`, `purple`, `indigo`, `pink`, `teal`, `cyan`, `fuchsia`, `lime` (categories: asset types, broker roles) | **leave them**: categorical roles come later |

## Rules

1. **An element migrates whole.**
   - Never put a role utility and a palette class on the same element, or in the same class string.
   - `app.css` exempts every element carrying a `-lf-` class from its legacy dark remap: a half-migrated element would
     keep half of its old colours in dark.
   - If an element cannot migrate yet (a categorical colour), leave it entirely as it is.
2. **No `dark:` on a role.** The role already changes with the theme. Drop the `dark:` half of every converted pair.
3. **Set the text role on the component's root** (`text-lf-primary`): in dark, `body` still passes the legacy text
   colour down until the clean-up.
4. **Every `border` names its role** (`border border-lf-subtle`): Tailwind v4 draws an unnamed border in
   `currentColor`.
5. **No hand-written colours.**
   - No hex, `rgb()`, `hsl()` or colour names in markup, scripts or `<style>`.
   - No arbitrary values (`bg-[#…]`), except `bg-[var(--lf-…)]`.
   - A colour a library draws (ECharts, canvas) comes from the theme tables of `lib/theme/`, not from a literal.
6. **Class names stay whole literals.** Never build them from pieces (`'bg-lf-' + x`): Tailwind would not generate
   them, and the gate cannot see them.
7. **Shared files** (shell, header, files other workstreams also edit): change classes only, never reorder the markup.

## Gates and the baseline

- `src/themeRoles.gate.test.ts`:
  - **the ratchet:** per file, m1 legacy colour classes and m2 colour literals, compared as a multiset of values, so
    swapping one colour for another fails;
  - **the grammar:** G1 no `dark:` on a role, G2 no unknown role, G3 no mixed element, G4 no arbitrary colour.
- `src/themeTokens.gate.test.ts`: both themes declared, the utility table, the contrast pairs, no dead rule in the
  legacy remap.
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

**A merge conflict on the baseline:**
1. Keep the tighter side for each line: the lower m1, the m2 values both sides have.
2. A line one side removed stays removed; a line one side added (a split) stays.
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
