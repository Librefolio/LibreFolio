---
title: "Tailwind 4 sorts same-property utilities by name: an always-on colour beat the open state"
category: problem
status: resolved
date: 2026-10-16
tags: [frontend, css, tailwind, colour, theme, svelte, cascade]
related: [decisions/colour-factorisation-at-pixel-parity, problems/esbuild-colour-minify-skips-custom-properties, problems/colour-ratchet-resolve-drops-an-accept]
---

# Problem: Tailwind 4 sorts same-property utilities by name: an always-on colour beat the open state

## Symptom
Workstream T's lot I1 (W1-a and W1-b, the `ui/select` components, night of 15–16/10/2026) moved the selects onto the
colour roles. The first version of `SimpleSelect`'s trigger kept the structure of the legacy markup: the idle border was
always present, and the open state added its colour conditionally.

```svelte
<!-- legacy: worked -->
class="… border-gray-300 dark:border-slate-600 hover:border-gray-400 … {isOpen ? 'ring-2 ring-libre-green border-libre-green' : ''}"
<!-- first role version: the open border never showed -->
class="… border-lf-input hover:border-lf-input-hover … {isOpen ? 'ring-2 ring-lf-focus border-lf-focus' : ''}"
```

Open, the select drew the focus ring but kept the idle border colour. The class strings were right; only the rendering
showed the problem.

## Root Cause
Tailwind 4 emits one rule per utility and sorts the rules: first by their variants, then by the CSS properties they set
(its internal property order), then by the utility's name. Two **base** utilities that set the same property on one
element (here `border-color`) have the same specificity and the same layer, so the one emitted later wins, and that is
the one whose **name sorts later**. The order of the classes in the `class` attribute plays no part.

- Legacy: `border-gray-300` sorts before `border-libre-green`, so the open colour came later and won: it had worked by
  luck of the names.
- Roles: `border-lf-focus` sorts before `border-lf-input`, so the idle colour came later and won.

Renaming colours to roles reorders every pair like this one, whatever the property: `bg-lf-card` against
`bg-lf-selected`, `text-lf-muted` against `text-lf-primary`, and so on.

Variants are emitted after every base utility, in the order Tailwind registers them. In 4.1.18 (`frontend/package.json`
asks `^4.1.17`) the order includes `invalid`, `hover`, `focus`, `focus-visible`, `active`, `disabled`, then `aria-*`,
`data-*`, `supports-*`, and `dark` near the end. Specificity counts too:
- a pseudo-class or attribute variant (`hover:`, `focus:`, `aria-invalid:`) adds one class of specificity, so it beats
  a base utility of the same property both by specificity and by order;
- two such variants that apply together (hovered and focused) have the same specificity, and the one registered later
  wins;
- the project's `dark` is `@custom-variant dark (&:where(.dark, .dark *))` in `app.css`, which adds no specificity: a
  `dark:` utility beats a base utility by order alone, and loses to `hover:` or `focus:` (hence the legacy
  `dark:hover:` pairs). Roles need none of this, since they change with the theme.

## Solution
**One property, one ternary.** The idle and the state colour of the same property are the branches of one expression,
and the idle `hover:` sits in the idle branch, so the two never meet on the element:

```svelte
{isOpen ? 'ring-2 ring-lf-focus border-lf-focus' : disabled || loading ? 'border-lf-subtle' : 'border-lf-input hover:border-lf-input-hover'}
```

The rule was sent to the sub-agent while it was writing the lot, and it went into the body of I1's commit (`1c16151a1`).

Where a state must win over a colour that a **caller** adds, the state can be a variant: a base `border-*` passed in by
the caller can never beat it. The input lot, still a draft when this page was written, puts the error border of
`ExactDecimalInput` on `aria-invalid:border-lf-danger` for this reason.

### The same rule across a class prop
A class prop (`className`, `contentClass`, `triggerClass`, `fieldClass`, `tab.className`) puts the caller's colours on
the component's element, and they meet the component's own colours under the same name order.

`ModalBase` (lot W1-e) keeps its border and text colour as classes in the markup (`border border-lf-raised
text-lf-primary {contentClass}`), not in its `<style>`:
- a Svelte component's `<style>` is not in a cascade layer, so it beats every Tailwind utility, which lives in
  `@layer utilities`;
- a border declared there would erase the `border-2 border-red-300 dark:border-red-700` that `AssetCurrencyChangeModal`
  passes through `contentClass`;
- as classes, `border-red-300` sorts after `border-lf-raised`, and the caller's red border wins, as it did before.

The balance is fragile. When that caller moves to a role whose name sorts first (`border-lf-danger-line` comes before
`border-lf-raised`), the modal's default border will win instead. The caller then needs a modal variant prop, or the
modal must stop setting a default border colour on that path. This is recorded in T's backlog (TC-10, «da rivedere»).

## Prevention
- Rule 8 of the `theme-roles` skill: one property, one ternary; a state that must beat a caller is a variant; check
  every class prop before migrating either side.
- Before converting a component, look for a property set twice on one element (always-on plus conditional) and for
  class props that callers fill with colours.
- Check the open, selected, disabled and invalid states in the rendering, not only in the class strings: a class string
  reads the same in either order.
- During the night lots, a throw-away scan of the work copies flagged same-property pairs before each patch. It was not
  committed.

## Impact
No wrong colour shipped: the problem was caught on the first lot that met it, before that lot's commit. Every later lot
(W1-c, W1-d, W1-e, W2-a, the input lot) was written with the rule.

## Source files
| Role | Path |
|------|------|
| The fix: open, disabled and idle borders in one ternary | `frontend/src/lib/components/ui/select/SimpleSelect.svelte` |
| Border and text as classes, so a caller's `contentClass` can win | `frontend/src/lib/components/ui/modals/ModalBase.svelte` |
| A caller passing a border through `contentClass` | `frontend/src/lib/components/assets/AssetCurrencyChangeModal.svelte` |
| The `dark` custom variant | `frontend/src/app.css` |
| The rule for every migration (rule 8) | `.github/skills/design-tools/theme-roles/SKILL.md` |
| Tailwind version | `frontend/package.json` |
