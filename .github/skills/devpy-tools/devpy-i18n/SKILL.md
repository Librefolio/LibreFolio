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
- ~1476 keys per language (post 2026-07 cleanup campaign, 2 rounds — removed 194 dead/duplicate keys)

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
`chartSettings.params.*`, `chartSettings.signals.*`, `sectors.*`, `settings.globalSettingCategories.*`,
`settings.globalSettingDescriptions.*`, `settings.globalSettingNames.*`, `settings.globalSettingUnits.*`,
`settings.global.scheduler.historyDays*` (day-of-week lookup), `importWizard.confidence.*`,
`importWizard.confidenceTip.*`, `importWizard.fileStatus.*`, `fileStatus.*`, `dataQuality.cta.*`,
`auth.passwordStrength.*` (incl. `.rules.*`).

**Partially-protected namespaces — do NOT blanket-protect the whole prefix, only these specific keys**
(discovered during round 2 of the 2026-07 campaign; the audit tool's dynamic-prefix detector flags the
*whole* bare namespace as "potentially used" if even ONE key under it is referenced dynamically, which
is overly conservative for merge purposes — verify per-key with grep, don't assume):
- `importWizard.*` bare namespace: only `importWizard.step1Title/.step2Title/.step3Title/.step4Title`
  are truly dynamic (`` $t(`importWizard.${stepKey}`) `` over a fixed `STEPS` array in
  `ImportWizardModal.svelte`). Every other bare `importWizard.*` key (`.back`, `.cancel`, `.continue`,
  `.import`, `.sourceFile`, etc.) is a literal call site and safe to merge.
- `chartSettings.*` bare namespace: only `chartSettings.badgeDividend/.badgeInterest/.badgePriceAdjustment/
  .badgeMaturitySettlement/.badgeSplit/.badgePoints` are truly dynamic (`` $t(`chartSettings.${EVENT_BADGE_KEY[evType] ?? 'badgePoints'}`) ``
  in `ChartSignalsSection.svelte`). Other bare `chartSettings.*` keys (`.apply`, `.discard`, `.preview`,
  `.overlaySignals`) are literal and safe to merge (though `chartSettings.discard` is still kept
  separate from `common.discard` for a *semantic* FR-divergence reason, not a dynamic one).
- `datePicker.granularity.*`: values are referenced via a small fixed local array of `labelKey`/`shortKey`
  string literals in `DateRangePicker.svelte` (not a runtime-arbitrary template variable) — safe to merge
  if you also update that array's literal entries, but low value (short generic words), generally left
  alone.

## Backend-Driven Dynamic Keys (auto-detected since 2026-07 tool fix)

The backend can emit an i18n key as **data**, not just the frontend calling it statically. Confirmed
pattern: `backend/app/services/portfolio_engine.py` / `portfolio_service.py` set a
`message_i18n_key="dataQuality.xxx"` field on API response objects (data-quality issues), consumed
dynamically via `$_(issue.message_i18n_key, {values: ...})` in
`frontend/src/lib/components/ui/feedback/DataQualityBanner.svelte`.

`./dev.py i18n audit` now automatically scans `backend/**/*.py` for any `..._i18n_key="ns.key"` /
`'ns.key'` literal assignment (see `find_used_keys_in_backend()` in `frontend/scripts/i18n-audit.py`)
and treats those keys as used — no manual cross-checking needed anymore. If you introduce a NEW
backend-driven key mechanism with a different field-name suffix than `..._i18n_key`, update that
function's regex accordingly.

Similarly, `` $t(`prefix.wordSuffix${var}` `` `` `` -style camelCase-continuation dynamic templates
(no dot before the interpolation — e.g. `settings.global.scheduler.historyDays${day}` in
`SchedulerConfigModal.svelte`) are now detected too (see the second `patterns_dynamic` regex in
`find_used_keys_in_sources()`), in addition to the classic dot-anchored `` `prefix.${var}` `` form.

## Rules for New Keys

1. **Search first**: check if the value already exists under `common.*`
2. **Generic values** → use `common.*`
3. **Feature-specific** → use the feature namespace
4. **Never duplicate** a `common.*` value unless the meaning is genuinely different

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

**Signal abbreviations (intentional):**
- `chartSettings.signals.ema` / `.emaAbbr` — Name may become "Exponential Moving Average" while abbreviation stays "EMA". Consistent pattern for all signals.

**Discovered during 2026-07 cleanup campaign (do NOT re-consolidate):**
- `dashboard.holdings` vs `dashboard.positions` — "Holdings" and "Positions" are distinct portfolio concepts, not interchangeable despite similar translations.
- `transactions.promote.fieldTags` vs `transactions.fields.tags` / `transactions.form.tags` — promote-merge UI field label vs generic field/form label; `transactions.fields.*` is dynamic-prefix protected anyway.
- `transactions.linkTooltip.generic` vs `transactions.types.CASH_TRANSFER` — generic tooltip copy vs the actual transaction-type label (dynamic-prefix protected).
- `assets.confirm.confirmChange` vs `assets.confirm.identifierChanged` — generic confirm-change prompt vs a specific "identifier changed" warning; same FR text today but distinct triggers.
- `transactions.form.costBasis` vs `transactions.fields.cost_basis_override` — display label vs the dynamic-prefix-protected editable field label.
- `assetDetail.eventType.SPLIT` vs `assets.schedule.split` — corporate-action event type (dynamic-prefix protected) vs a scheduler action verb.
- `transactions.form.transferCashTitle` ("Wire Transfer") vs `transactions.types.CASH_TRANSFER` ("Cash Transfer") — modal title vs transaction-type label; kept separate pending a possible future copy-consistency pass (not a merge candidate as-is).

**New canonical `common.*` keys created by the 2026-07 merge pass** (prefer these over creating new feature-namespaced duplicates): `common.broker`, `common.provider`, `common.providers`, `common.active`, `common.seeAll`, `common.from`, `common.to`, `common.tags`, `common.preview`, `common.import`, `common.rowN`, `common.saveCancelled`, `common.assets`, `common.recentTransactions`, `common.addRow`, `common.clearSelection`, `common.syncFxRates`, `common.linkedEvent`, `common.currentPrice`, `common.resetAllChanges`, `common.apply`, `common.deselectAll`, `common.discardImport` (in addition to the pre-existing `common.description`, `common.type`, `common.date`, `common.status`, `common.error`, `common.cancel`, `common.resetAll` — note `common.resetAll` means "Reset All **to Defaults**" (settings-specific) and is NOT the same as `common.resetAllChanges` = plain "Reset All" button, don't conflate them).

**Round 2 additional accepted-duplicates (kept separate on purpose):**
- `dashboard.capitalBaseline` / `.capitalBaselineTooltip` / `dashboard.netDepositedCapital` — legend label vs tooltip-line label vs a distinct net-deposited metric; same text today but different UI roles, may diverge later (same pattern as signal name/abbr).
- `assets.distribution.total` vs `assets.probe.totalTime` — distribution sum vs a diagnostics execution-time display; coincidentally both render "Total" today.
- `assets.schedule.currency` vs `settings.categoryCurrency` — investment-schedule form field label vs a settings-tab category name; both happen to use the ES "Moneda" wording today but serve different UI roles.
- `assets.sync.assetsCount` (lowercase "assets", used inline like "12 assets") vs `common.assets` (Title-case "Assets", section/page heading) — casing carries grammatical meaning (mid-sentence count vs heading), not a mergeable pair despite case-insensitive match.
- `importWizard.sourceFile` ("File") vs `uploads.file` ("file") — same case-sensitivity distinction as above.
