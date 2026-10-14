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
  their central module once R has moved them there. If the export touches a file you do not own, report it.

## 1. Verify against the code as it is now

```bash
node frontend/scripts/designer-lab/verify-export.mjs <export.json>          # human summary, exit 1 if something is missing
node frontend/scripts/designer-lab/verify-export.mjs <export.json> --json   # machine report (lf-designer-lab-verify/1)
```

- `catalog_hash_match: false` means the code changed since the export: expect `moved` occurrences.
- `moved` gives the new line: use it. `missing` means the value is no longer there: find out why (already changed,
  refactored into a token) before doing anything, and list it in the final report.
- `definitions[].value_now` means a variable definition changed since the export: the designer's `from` is stale.

## 2. Group by layer

| `layer` | What it is | How it is applied |
|---|---|---|
| `css-var` | A CSS custom property: Tailwind's palette (`--color-emerald-600`), `--theme-*`, the brand `--color-libre-*`, future role tokens | Defined in the sources (`definitions[]`) → change the definition for the scope. A Tailwind palette primitive has no definition in the sources: changing it redefines it for **every** use (`impact.classes`). Prefer mapping the uses that matter to a role token, as the token plan says; redefine the primitive only if the designer explicitly wants the whole shade changed |
| `css-literal` | A colour written in a stylesheet: a component `<style>`, `app.css`, a Tailwind arbitrary class | Edit each occurrence (`file`, `line`, `selector`, `property`). `granularity: occurrence` means one rule only. `alpha_variants: true` means translucent writings of the colour change too, keeping their alpha. Many occurrences of one meaning → introduce a CSS variable, consistently with the token plan |
| `chart-color` | A colour of an ECharts option, built in TypeScript | Edit the occurrences, in the central chart-colour module when it exists. Hex helpers that only accept `#rrggbb` break on `oklch()`: canvas colours must stay sRGB (the Lab's preview clamped them) |
| `proposal` | No live preview: inline styles, generated colours (`getIndexColor`…), `static/offline.html`, `manifest.json`, the `theme-color` meta | Edit the occurrences; for generated colours change the generator's inputs, and say so |

Values may be any CSS colour. `oklch()` outside sRGB is legitimate in CSS (the Lab warned the designer); a
`var(--x)` target means "use this variable here" — an unification proposal.

## 3. Apply, then prove it

1. Apply in small groups, each one with its own commit message proposal (the agent never commits).
2. Run the checks of the files you touched (`./dev.py front check`, the unit tests that pin colours: `colors.test.ts`,
   `sourcePalettes.test.ts`, `chartCoreHelpers.test.ts`, `assetTypeTables.test.ts` — report 03 §6 of the analysis).
3. **Same-day gallery diff** (`scripts/visual_review/README.md`): a snapshot of the target branch and one of the
   candidate on two lanes, then `gallery_tool diff … --ignore-masks <noise masks> --stability <stability.json>`.
   Only the screens the change should touch may differ; every other difference is a regression.
4. Rebuild the designer package for the next round (`build_designer_package.py`).

Exports and snapshots live outside the repository, under `$LF_VISUAL_REVIEW_DIR` (`lab-exports/`, `snapshots/`, `diffs/`).

## 4. Final report

For each change: applied where (files and lines), applied how (definition, occurrences, new variable), or **not
applied and why** (missing, owner, ambiguous meaning, needs the designer). Add the gallery diff summary and the
screens that changed. A change silently skipped is the one failure this skill exists to prevent.
