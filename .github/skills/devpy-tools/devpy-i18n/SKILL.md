---
name: devpy-i18n
description: "Use this skill when the user needs to manage frontend translations (i18n): audit keys, add/remove/update translations, search for keys or values, check for duplicates, or understand the i18n namespace structure."
---

# i18n Management (Frontend Translations)

## Commands

```bash
./dev.py i18n audit                          # Full audit report
./dev.py i18n audit --duplicates             # Show duplicate values
./dev.py i18n audit --format xlsx            # Export as Excel
./dev.py i18n audit --format md              # Export as Markdown

./dev.py i18n add "ns.key" --en "English" --it "Italiano" --fr "Français" --es "Español"
./dev.py i18n remove "ns.key"                # Remove key from all languages
./dev.py i18n remove "ns.key" -f             # Force (no confirmation)
./dev.py i18n update "ns.key" --it "Nuovo"   # Update single language

./dev.py i18n search "query"                 # Search in values (all languages)
./dev.py i18n search "query" -k              # Search in key names only
./dev.py i18n search "query" -v              # Verbose (show all languages)
./dev.py i18n search "query" -l it           # Search only in Italian

./dev.py i18n tree                           # Full key tree
./dev.py i18n tree common                    # Tree under "common" namespace
./dev.py i18n tree --counts                  # Show key counts per namespace
./dev.py i18n tree -d                        # Show duplicates in tree
```

## Translation Files

- Location: `frontend/src/lib/i18n/{en,it,fr,es}.json`
- Library: svelte-i18n
- Languages: EN (primary), IT, FR, ES
- ~4 150 keys per language after the Release 2 audit (2026-10: 4 356 → 4 152; 192 dead keys removed,
  five condensations C1-C5). Read the live number from `./dev.py i18n audit`, never from here.

## Locale File Format — canonical form is `indent=2`

The canonical serialization is the one `./dev.py i18n` produces:
**`indent=2`, `ensure_ascii=False`** (accented characters stay literal), trailing newline.
Prettier is configured to agree with it byte-for-byte:

- `frontend/.prettierrc` has a `*.json` override setting `tabWidth: 2` (the global
  `tabWidth` is 4, which is correct for `.ts`/`.svelte` but wrong for these files).
- `frontend/package.json` includes `json` in the `format`/`format:check` globs, so
  `./dev.py front format` and `./dev.py front check` actually cover the locale files.
  (`src/lib/api/openapi.json` is excluded via `.prettierignore`.)

**Why this matters**: before this alignment, `.json` was not in the format glob at all,
so the locale files were never checked by Prettier. Anyone editing them by hand — rather
than through `./dev.py i18n` — introduced a different indentation, and the next tool run
reformatted the whole file, producing a ~5 700-line diff *per language* for a change of a
few keys. Aligning Prettier to the tool means both paths converge on one form.

**Never hand-reindent these files.** Use `./dev.py i18n add/remove`, or
`./dev.py front format`; both now produce identical bytes. After any change, sanity-check
the diff size and key parity:

```bash
git --no-pager diff --stat -- 'frontend/src/lib/i18n/*.json'   # should be small
```

A key removed from some languages but not others is worse than an unused key — always
verify all four locales end up with the same key set.

## Key Naming Conventions

| Pattern | When to use |
|---------|-------------|
| `common.*` | Generic values shared across features (Cancel, Save, Delete...) |
| `feature.*` | Feature-specific keys (e.g. `assets.sync.modalTitle`) |
| `feature.types.*` | Dynamic prefix for `$t(\`feature.types.${var}\`)` lookup |

## Protected Dynamic-Prefix Namespaces (NEVER merge away, even if the value duplicates `common.*`)

These are looked up via a template-literal pattern like `` $t(`namespace.${variable}`) `` or
`` $t('namespace.' + variable) ``, so every key must exist under its own namespace regardless of
whether its text happens to match another key elsewhere:

`transactions.fields.*`, `transactions.types.*`, `transactions.errors.*`, `transactions.fieldErrors.*`,
`assets.types.*`, `assets.events.types.*`, `assetDetail.eventType.*`, `assetDetail.eventTypeTooltip.*`,
`chartSettings.params.*`, `sectors.*`, `settings.globalSettingCategories.*`,
`settings.globalSettingDescriptions.*`, `settings.globalSettingNames.*`, `settings.globalSettingUnits.*`,
`settings.global.scheduler.historyDays*` (day-of-week lookup), `importWizard.confidence.*`,
`importWizard.confidenceTip.*`, `importWizard.fileStatus.*`, `fileStatus.*`, `dataQuality.cta.*`,
`auth.passwordStrength.*` (incl. `.rules.*`), `providerErrors.*` (backend error codes),
`aiExport.additionalData.reason.*` (backend f-string, `ai_export/analyses/catalog.py:77`).

`chartSettings.signals.*` is **not** a dynamic prefix any more: its keys are literals in
`lib/charts/signals/registry.ts` (`displayNameKey`), plus the `Full` suffix appended at
`ChartSignalsSection.svelte:142` (`` `${definition.displayNameKey}Full` ``). Merge one only by updating
the registry. The `*Abbr` keys had no reader and were removed in the Release 2 audit.

**Partially-protected namespaces — do NOT blanket-protect the whole prefix, only these specific keys**
(discovered during round 2 of the 2026-07 campaign; the audit tool's dynamic-prefix detector flags the
*whole* bare namespace as "potentially used" if even ONE key under it is referenced dynamically, which
is overly conservative for merge purposes — verify per-key with grep, don't assume):
- `importWizard.*` bare namespace: only the step titles are truly dynamic —
  `step1Title`, `step2Title`, `step3Title`, `step4Title`, `stepAssetsTitle`, `stepDuplicatesTitle`,
  `stepFixTitle` and `reportSet.gapFix.stepTitle`, read as `` $t(`importWizard.${step.titleKey}`) `` over the
  fixed `STEP_DEFS` list in `ImportWizardModal.svelte` (`titleKey:` values). Every other bare
  `importWizard.*` key (`.back`, `.cancel`, `.continue`, `.import`, `.sourceFile`, etc.) is a literal
  call site and safe to merge.
- `chartSettings.*` bare namespace: only `chartSettings.badgeDividend/.badgeInterest/.badgePriceAdjustment/
  .badgeMaturitySettlement/.badgeSplit/.badgePoints` are truly dynamic (`` $t(`chartSettings.${EVENT_BADGE_KEY[evType] ?? 'badgePoints'}`) ``
  in `ChartSignalsSection.svelte`). Other bare `chartSettings.*` keys (`.apply`, `.discard`, `.preview`,
  `.overlaySignals`) are literal and safe to merge (though `chartSettings.discard` is still kept
  separate from `common.discard` for a *semantic* FR-divergence reason, not a dynamic one).
- `datePicker.granularity.*`: values are referenced via a small fixed local array of `labelKey`/`shortKey`
  string literals in `DateRangePicker.svelte` (not a runtime-arbitrary template variable) — safe to merge
  if you also update that array's literal entries, but low value (short generic words), generally left
  alone.

## How the Audit Decides "Used" (since the Release 2 audit, 2026-10)

`./dev.py i18n audit` gives each key one of three verdicts (`scripts/i18n_usage.py`, gate
`./dev.py test … utils gate-i18n-usage`):

- **used** — proven: a literal, a resolved template, or a member the producer or the building file names;
- **not verified** — under a real family (or only under a legacy truncated prefix), final segment built
  at runtime and named nowhere. **Not evidence of death** — never remove one without a per-key grep;
- **dead** — no evidence anywhere. The only actionable list.

What counts as evidence:

- **Product sources only.** `*.test.ts`, `*.spec.ts`, `__tests__/` and `__mocks__/` prove nothing: a key
  only a test names is dead to every user (774 strings and 19 prefixes came only from tests before).
  Generated API clients (`lib/api/generated.ts`, `generated-tools.ts`, `*.generated.ts`) prove nothing
  either: they exist only after `api sync`, so a verdict resting on them would flip on a fresh clone.
- **Any whole-key literal**, quoted or in a backtick without interpolation, whoever receives it:
  `translateOr($_, 'k', …)`, `label('k', …)`, `translate('k')`, `tr('k', …)`, `afterCopyKey: 'k'`,
  ternaries across lines, arrays, and **backend** literals (dictionaries such as
  `_message_key_for_issue` in `lots_analysis_service.py`, `..._i18n_key=` fields, `x-i18n-key` schemas).
- **Templates**, nested ones included (`` `…${$t(`ns.band.${b}`)}…` ``): constants, literal
  conditionals, typed unions and single-literal parameter types (`prefix: 'errors'`) are expanded;
  camelCase continuations (`historyDays${day}`) and `'ns.cat.' + code` concatenations are families.
- **Family members**: the producer's vocabulary (any identifier case, Title Case names without spaces —
  `"Health Care"` → `HealthCare` — dotted codes, codes beginning with a digit such as `"3m"`, matched in
  any case: `IN_TRANSIT` proves `in_transit`); the `titleKey:` values or map values the interpolation
  itself names; and, for narrow families only (two dots or a camelCase continuation), any word the
  **building file** quotes (`text('compute.title')` over `` `${KEY}.${key}` ``) **or a module it imports
  directly** (the bands of `correlationHelpers.ts` for the heatmap). One hop only: a word two imports
  away, or in a neighbour nobody imports, proves nothing, and a wide family (`ns.${x}`) reads no import.
- **Shapes**: a template with several runtime segments, or one before a literal tail
  (`` `assets.providerParams.${code}.${kind}.${field.key}` ``, `` `assets.panels.${panel.id}Hint` ``),
  keeps its shape. A key with exactly that shape is used when every slot is a word of the building file,
  of its direct imports or of the producer; a typed-union slot takes only its members. One slot named
  nowhere leaves the key not verified, and a template without a dotted literal head has no shape.
- **Backend f-string families** (`f"aiExport.additionalData.reason.{reason}"`) and suffixes
  (`` `${displayNameKey}Full` ``).
- A backend family whose namespace exists but holds no key is listed under 👻 (today:
  `tools.allocation.constraints.` ← `pac_allocator/evaluator.py:968`, a field nobody reads).
- A key that only **unreferenced sources** keep alive is listed under 📦, with the verdict it would get
  without them. A source is unreferenced when no SvelteKit entry (route files, hooks, service worker)
  reaches it through static or dynamic imports. Informational: decide whether the source is dead, then
  remove it with its keys (`AgeLabel.svelte` and its five `planner.age.*` keys went this way). Today
  `onboardingTourSurfaces.svelte.ts` and `stores/core/EditBuffer.ts` are unreferenced but read no key.

Known limit: the backend vocabulary is shared by every family, so a common word ("assets") can still
make a dead key look used under a family (`…planner.result.sections.assets` was removed by hand). And
a member two imports away stays not verified (`chartSettings.params.amplitude`, `histogramScale`).

If you introduce a NEW backend-driven key mechanism, make sure the key is a literal somewhere, or a
dotted f-string head: then the audit sees it with no tool change.

## Rules for New Keys

1. **Search first**: check if the value already exists under `common.*`
2. **Generic values** → use `common.*`
3. **Feature-specific** → use the feature namespace
4. **Never duplicate** a `common.*` value unless the meaning is genuinely different
5. **A locale-sensitive ICU message must differ across locales.** svelte-i18n 4.0.1 caches each
   formatter by message text only (`getMessageFormatter`, `runtime.js:383-392`, `:496`), so a
   `plural`/`selectordinal`/`number`/`date`/`time` text byte-identical in two catalogues keeps the rules
   of whichever locale compiled it first after an in-place language switch (`0 position` vs
   `0 positions`). Make the texts differ — e.g. FR adds a `many` branch identical to `other`, which
   changes no rendering. Gate: `frontend/src/lib/i18n/catalogIcuLocale.test.ts`.
6. **Count from the digits shown**: an ICU `count` next to a formatted decimal comes from
   `plannerPlainDecimalCount` / `plannerQuantityCount` (`planner/format.ts`), never from `Number(…)`
   (`"1.00000000000000000001"` is plural; a masked value is plural). Gate:
   `planner/pluralCountSites.test.ts`.

## Duplicate Strategy

Consolidate under `common.*` only when **meaning, context AND value match in all 4 languages**. Same value but different meaning → keep separate.

### Accepted Duplicates (do NOT consolidate)

**Semantic difference:**
- `common.close` vs `dataEditor.col.close` — Button "Close" vs OHLC price "Close". IT/FR/ES diverge.
- `common.reset` vs `common.undo` — Reset to defaults vs undo last action. Opposite meanings.
- `assets.modal.saveChanges` vs `common.save` — "Save Changes" (explicit) vs "Save" (short).

**Dynamic prefix / Singular-Plural:**
- `assets.types.OTHER` vs `common.other` — `assets.types` is a dynamic prefix (`$t(\`assets.types.${var}\`)`), all keys must stay.
- `uploads.file` / `uploads.files` / `uploads.title` — Singular, plural, page title. All three needed.

**Different UI context:**
- `assets.schedule.currency` vs `common.currency` — ES diverges: "Moneda" vs "Divisa".
- `nav.settings` vs `sharedResource.settings` — ES diverges: "Configuración" vs "Ajustes".
- `chartSettings.discard` vs `common.discard` — FR diverges: "Rejeter" vs "Abandonner".

**Signal name and long name:**
- `chartSettings.signals.<signal>` / `<signal>Full` — short name vs long name of a local signal; the
  `Full` key is read by suffix (`ChartSignalsSection.svelte:142`). Backend plugins carry their own
  `signals.<plugin>.{name,output}`, often identical ("EMA"/"EMA"): metadata emitted by the backend, keep.

**Discovered during 2026-07 cleanup campaign (do NOT re-consolidate):**
- `transactions.promote.fieldTags` vs `transactions.fields.tags` / `transactions.form.tags` — promote-merge UI field label vs generic field/form label; `transactions.fields.*` is dynamic-prefix protected anyway.
- `transactions.linkTooltip.generic` vs `transactions.types.CASH_TRANSFER` — generic tooltip copy vs the actual transaction-type label (dynamic-prefix protected).
- `assets.confirm.confirmChange` vs `assets.confirm.identifierChanged` — generic confirm-change prompt vs a specific "identifier changed" warning; same FR text today but distinct triggers.
- `transactions.form.costBasis` vs `transactions.fields.cost_basis_override` — display label vs the dynamic-prefix-protected editable field label.
- `assetDetail.eventType.SPLIT` vs `assets.schedule.split` — corporate-action event type (dynamic-prefix protected) vs a scheduler action verb.
- `transactions.form.transferCashTitle` ("Wire Transfer") vs `transactions.types.CASH_TRANSFER` ("Cash Transfer") — modal title vs transaction-type label; kept separate pending a possible future copy-consistency pass (not a merge candidate as-is).

**New canonical `common.*` keys created by the 2026-07 merge pass** (prefer these over creating new feature-namespaced duplicates): `common.broker`, `common.provider`, `common.providers`, `common.active`, `common.from`, `common.to`, `common.tags`, `common.preview`, `common.import`, `common.rowN`, `common.saveCancelled`, `common.assets`, `common.addRow`, `common.clearSelection`, `common.syncFxRates`, `common.linkedEvent`, `common.currentPrice`, `common.resetAllChanges`, `common.apply`, `common.deselectAll`, `common.discardImport` (in addition to the pre-existing `common.description`, `common.type`, `common.date`, `common.status`, `common.error`, `common.cancel`, `common.resetAll` — note `common.resetAll` means "Reset All **to Defaults**" (settings-specific) and is NOT the same as `common.resetAllChanges` = plain "Reset All" button, don't conflate them). `common.seeAll` and `common.recentTransactions` lost their last reader and were removed in the Release 2 audit: re-add them only with a caller.

**Round 2 additional accepted-duplicates (kept separate on purpose):**
- `dashboard.capitalBaseline` / `.capitalBaselineTooltip` / `dashboard.netDepositedCapital` — legend label vs tooltip-line label vs a distinct net-deposited metric; same text today but different UI roles, may diverge later (same pattern as signal name/abbr).
- `assets.distribution.total` vs `assets.probe.totalTime` — distribution sum vs a diagnostics execution-time display; coincidentally both render "Total" today.
- `assets.schedule.currency` vs `settings.categoryCurrency` — investment-schedule form field label vs a settings-tab category name; both happen to use the ES "Moneda" wording today but serve different UI roles.
- `assets.sync.assetsCount` (lowercase "assets", used inline like "12 assets") vs `common.assets` (Title-case "Assets", section/page heading) — casing carries grammatical meaning (mid-sentence count vs heading), not a mergeable pair despite case-insensitive match.
- `importWizard.sourceFile` ("File") vs `uploads.file` ("file") — same case-sensitivity distinction as above.

**Release 2 audit (2026-10) — condensed, prefer the surviving keys:**
- `uploads.previewZoomIn` / `.previewZoomOut` → `uploads.zoomIn` / `.zoomOut` (file preview and image cropper);
- `uploads.size` → `uploads.fileSize` (asset picker, file table, file edit modal);
- `assetDetail.editorTip{Desktop,Mobile}` and `fxDetail.editorTip{Desktop,Mobile}` → `dataEditor.editorTip{Desktop,Mobile}`
  (the same data-editor tip on the asset and FX pages);
- `brokers.lots.modal.{currentValue,fifoPnl,openQuantity,openReturn,originalQuantity,totalPnl}` and
  `brokers.lots.tooltip.totalPnl` → `brokers.lots.{…}` (one lot field, one label, in the custody modal,
  the lots table and the chart tooltips).

Of the 112 groups identical in all four languages, the rest were kept on purpose: backend signal-plugin
metadata (`signals.<plugin>.{name,output}`, «Overbought»/«Oversold»/«Neutral» per plugin), the PAC
planner's per-module namespaces, generic words in different roles («Period», «Type», «Status», «Price»),
and the `risk.*` and `dashboard.*` groups, kept separate while those areas were under active work.
(`dashboard.holdings` vs `dashboard.positions` no longer applies: `dashboard.holdings` had no reader
and was removed.)
