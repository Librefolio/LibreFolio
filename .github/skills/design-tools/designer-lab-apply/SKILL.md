---
name: designer-lab-apply
description: "Use this skill when an export of the Designer Lab (designer-lab-changes.json / .md, schema lf-designer-lab/1) has to be checked, discussed or applied to the frontend code: verify it against the current code, group the changes by layer, apply them occurrence by occurrence (never a blind global replace), then prove the effect with a same-day gallery diff."
---

# Applying a Designer Lab export

The **Designer Lab** (`/designer-lab`, debug builds only) lets a designer change the app's colours live and export
the list of changes. The export is the hand-off to an agent: what changes, from which value to which, and **where it
lives in the code** (file, line, and for stylesheets the selector and property), from the colour catalogue the Lab was
built with.

Read the design first when the context is new: `LibreFolio_developer_journal/Release_2/Phase_0/55_colorSystem/design-designerLab.md`
(§5 layers, §7 export, §8 limits) and the developer page `mkdocs_src/docs/developer/frontend/designer-lab.md`.

## Rules that do not bend

- **Changing how the app looks is a decision, not a refactor.** Apply an export only when the developer asks for it,
  in a workstream allowed to change the appearance. A colour refactor that must keep every pixel (workstream R) does
  not apply exports.
- **Never replace a value everywhere at once.** The same hex often means different things (`#dc2626` is a loss, a
  cost, a sale *and* slot 4 of a palette — P5 of the colour analysis). Work from the occurrence list, and read the
  change's `note` and `shots` (gallery screen codes) to understand which meaning the designer changed.
- **Respect the theme.** `scope` is `light`, `dark` or `both`. Each occurrence carries `theme_context`: a rule written
  for both themes changed in one theme only must be split (a dark override, or a token with two values), not edited.
- **Owners stay owners.** `frontend/src/app.css` and the token files belong to their workstream; chart colours live in
  their central module once R has moved them there. Changes to the role tokens `--lf-<group>-<name>` apply to
  `frontend/src/lib/theme/tokens.css`, which only workstream T writes. If the export touches a file you do not own,
  report it.

## 1. Verify against the code as it is now

```bash
node frontend/scripts/designer-lab/verify-export.mjs <export.json>          # human summary, exit 1 if something is missing
node frontend/scripts/designer-lab/verify-export.mjs <export.json> --json   # machine report (lf-designer-lab-verify/1)
```

- `catalog_hash_match: false` means the code changed since the export: expect `moved` occurrences.
- `moved` gives the new line: use it. `missing` means the value is no longer there: find out why (already changed,
  refactored into a token) before doing anything, and list it in the final report.
- `definitions[].value_now` means a variable definition changed since the export: the designer's `from` is stale.
- Specialisations count their candidates apart (`candidates_*`): a moved or gone candidate is a hint. `anchor.status`
  per change: `ok`; `testid-missing` (a test id of the anchor is no longer written: the component moved or was
  renamed, find it by route and `css_path`); `no-candidates` (the Lab found no place: bind by test id); `lost` (exit
  1: none of the candidates is still there — do not guess, ask).

## 2. Group by layer

| `layer` | What it is | How it is applied |
|---|---|---|
| `css-var` | A CSS custom property: Tailwind's palette (`--color-emerald-600`), `--theme-*`, the brand `--color-libre-*`, the role tokens `--lf-<group>-<name>` | Defined in the sources (`definitions[]`) → change the definition for the scope. A Tailwind palette primitive has no definition in the sources: changing it redefines it for **every** use (`impact.classes`). Prefer mapping the uses that matter to a role token, as the token plan says; redefine the primitive only if the designer explicitly wants the whole shade changed. A role token is defined in `tokens.css` (workstream T): its utilities (`bg-lf-card`…, the `raw` of its `occurrences[]`) read it through `@theme inline` and follow the definition, with no edit at their lines |
| `css-literal` | A colour written in a stylesheet: a component `<style>`, `app.css`, a Tailwind arbitrary class | Edit each occurrence (`file`, `line`, `selector`, `property`). `granularity: occurrence` means one rule only. `alpha_variants: true` means translucent writings of the colour change too, keeping their alpha. Many occurrences of one meaning → introduce a CSS variable, consistently with the token plan |
| `chart-color` | A colour of an ECharts option, built in TypeScript | Edit the occurrences, in the central chart-colour module when it exists. Hex helpers that only accept `#rrggbb` break on `oklch()`: canvas colours must stay sRGB (the Lab's preview clamped them) |
| `proposal` | No live preview: inline styles, generated colours (`getIndexColor`…), `static/offline.html`, `manifest.json`, the `theme-color` meta | Edit the occurrences; for generated colours change the generator's inputs, and say so |
| `element` | A **specialisation**: one colour property of one component, decided on an element the designer pointed at in the app. The shared source (`anchor.source`) stays as it is: only this component changes | Create a component-scoped variable (or role token) and bind it at the places `occurrences[]` lists — see «Specialisations» below. `target` is the selector the preview wrote: context, not code to paste |
| `category` | The fixed colour of a **chart category** — an asset type, a sector, or the `Liquidity` / `Unknown` bucket (`category.kind`, `category.key`): every chart reads it through `categoryColor` of `frontend/src/lib/theme/chartCategories.ts` (workstream DV) | Edit the line `occurrences[]` lists for each theme of the change, in `chartCategories.ts`, **never by value**: types and sectors share values (`ETF` and `Technology`) and the change is for one category. The subtype shades follow the new colour. A `bucket` change is the one entry the two tables share |

Values may be any CSS colour. `oklch()` outside sRGB is legitimate in CSS (the Lab warned the designer); a
`var(--x)` target means "use this variable here" — an unification proposal. `color-mix(in <space>, <base> p%,
transparent)` is the base at opacity p, the form the role tokens use for shadows and the backdrop: apply it as written,
which keeps a `var()` base referenced — usually only the percentage changed.

### Specialisations (`element`)

The designer pointed at an element in the app tab and asked for a different colour **there**, not wherever the shared
source is used. The export says where she was and what sets the colour today:

- `anchor.route` (SvelteKit route, dynamic segments kept as `[param]`: `/assets/[id]`), `anchor.testids` (nearest
  first; `prefix*` is a templated id, `row-${id}` in the code, or an id cut before a record value such as a number or
  a currency code), `anchor.css_path`, `anchor.element` (tag, classes): how to find the component. **No element text
  is exported**: never search by content.
- `anchor.source.kind` says what to un-share: `tailwind-class` (`source.class` in the component's markup → a class or
  style bound to the new variable), `rule-literal` (the component's rule writes the colour → make it read the variable),
  `var` (the component reads a shared variable → give it its own, or override the shared one on the component's root),
  `inline` / `attribute` (the markup), `current-color` (it follows `color`: specialise `color`).
- `occurrences[]` are the candidate places, `raw` the text expected there and `why` the reason: `matched-rule` the rule
  that sets the colour, `class-use` the colour class on that line, `var-use` the rule reading the variable, `literal` an
  inline style or attribute, `testid` where the component's test id is written (the instance, or the component).
- `anchor.breadth: component` means every instance of the component (decision of 14/10/2026): bind the variable in the
  component, not at one call site. `element` means no test id surrounds it: ask before binding to one place.
- `anchor.matches` is how many elements the preview selector took on the open page. If it looks wider or narrower than
  the `note` suggests, ask the designer.
- `property: chart` with `color_key`: one colour of the charts inside that component — a per-chart override in the
  chart's option builder, never a change of the shared palette slot.
- Other layers may carry an `anchor` too: the element the designer was looking at when she edited the shared source,
  context for the `note`.

## 3. Apply, then prove it

1. Apply in small groups, each one with its own commit message proposal (the agent never commits).
2. Run the checks of the files you touched (`./dev.py front check`, the unit tests that pin colours: `colors.test.ts`,
   `sourcePalettes.test.ts`, `chartCoreHelpers.test.ts`, `assetTypeTables.test.ts` — report 03 §6 of the analysis).
3. **Same-day gallery diff** (`scripts/visual_review/README.md`): a snapshot of the target branch and one of the
   candidate on two lanes, then `gallery_tool diff … --ignore-masks <noise masks> --stability <stability.json>`.
   Only the screens the change should touch may differ; every other difference is a regression.
4. Rebuild the designer package for the next round (`build_designer_package.py`).

Exports and snapshots live outside the repository, in the visual-review work dir (`lab-exports/`, `snapshots/`,
`diffs/`): `--work-dir`, else `$LF_VISUAL_REVIEW_DIR`, else `LibreFolio_subRepo/LibreFolio_visual_review` next to the
main checkout (`scripts/visual_review/README.md`).

## 4. Final report

For each change: applied where (files and lines), applied how (definition, occurrences, new variable), or **not
applied and why** (missing, owner, ambiguous meaning, needs the designer). Add the gallery diff summary and the
screens that changed. A change silently skipped is the one failure this skill exists to prevent.
