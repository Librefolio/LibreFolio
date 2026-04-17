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
- 840+ keys per language

## Key Naming Conventions

| Pattern | When to use |
|---------|-------------|
| `common.*` | Generic values shared across features (Cancel, Save, Delete...) |
| `feature.*` | Feature-specific keys (e.g. `assets.sync.modalTitle`) |
| `feature.types.*` | Dynamic prefix for `$t(\`feature.types.${var}\`)` lookup |

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
