# Plan: i18n CLI Improvements

**Data creazione**: 30 Gennaio 2026  
**Status**: ✅ COMPLETATO  
**Priorità**: P1  
**Stima**: 30-45 min
**Completato**: 30 Gennaio 2026

---

## 🎯 Obiettivo

Estendere lo script `./dev.py i18n` con funzioni per gestire le traduzioni da CLI:

- Aggiungere nuove chiavi di traduzione
- Rimuovere chiavi obsolete
- Modificare traduzioni esistenti
- Cercare nelle traduzioni

Questo riduce errori manuali e velocizza il workflow di sviluppo.

---

## 📋 Problema Attuale

- Le traduzioni si modificano manualmente editando 4 file JSON
- Facile dimenticare una lingua
- Facile introdurre errori di sintassi JSON
- Nessun modo veloce per cercare dove una traduzione è usata

---

## 🔧 Implementazione

### File: `scripts/i18n_cli.py`

```python
"""
i18n CLI - Translation management commands for LibreFolio.

Commands:
- audit: Check translation coverage (existing)
- add: Add a new translation key to all languages
- remove: Remove a translation key from all languages
- update: Update a specific translation in one or more languages
- search: Search for keys/values in translations
"""

import json
import re
import sys
from pathlib import Path
from typing import Optional

# Paths
FRONTEND_DIR = Path(__file__).parent.parent / "frontend"
LOCALES_DIR = FRONTEND_DIR / "src" / "lib" / "i18n"
SUPPORTED_LANGUAGES = ["en", "it", "fr", "es"]


def load_translations(lang: str) -> dict:
    """Load translation file for a language."""
    filepath = LOCALES_DIR / f"{lang}.json"
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


def save_translations(lang: str, data: dict) -> None:
    """Save translation file for a language."""
    filepath = LOCALES_DIR / f"{lang}.json"
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")  # Trailing newline


def get_nested_key(data: dict, key: str) -> Optional[str]:
    """Get value from nested dict using dot notation key."""
    parts = key.split(".")
    current = data
    for part in parts:
        if isinstance(current, dict) and part in current:
            current = current[part]
        else:
            return None
    return current if isinstance(current, str) else None


def set_nested_key(data: dict, key: str, value: str) -> bool:
    """Set value in nested dict using dot notation key. Creates parents if needed."""
    parts = key.split(".")
    current = data
    for part in parts[:-1]:
        if part not in current:
            current[part] = {}
        elif not isinstance(current[part], dict):
            return False  # Cannot create nested key, parent is not a dict
        current = current[part]
    current[parts[-1]] = value
    return True


def delete_nested_key(data: dict, key: str) -> bool:
    """Delete key from nested dict using dot notation."""
    parts = key.split(".")
    current = data
    for part in parts[:-1]:
        if isinstance(current, dict) and part in current:
            current = current[part]
        else:
            return False
    if parts[-1] in current:
        del current[parts[-1]]
        return True
    return False


# =============================================================================
# CLI Commands
# =============================================================================

def cmd_add(args) -> int:
    """Add a new translation key to all languages."""
    key = args.key
    translations = {
        "en": args.en,
        "it": args.it,
        "fr": args.fr,
        "es": args.es,
    }
    
    # Check if key already exists
    for lang in SUPPORTED_LANGUAGES:
        data = load_translations(lang)
        if get_nested_key(data, key) is not None:
            print(f"❌ Key '{key}' already exists in {lang}.json")
            return 1
    
    # Add to all languages
    for lang in SUPPORTED_LANGUAGES:
        data = load_translations(lang)
        if set_nested_key(data, key, translations[lang]):
            save_translations(lang, data)
            print(f"✅ Added '{key}' to {lang}.json: \"{translations[lang]}\"")
        else:
            print(f"❌ Failed to add '{key}' to {lang}.json (parent path conflict)")
            return 1
    
    print(f"\n✅ Successfully added key '{key}' to all languages")
    return 0


def cmd_remove(args) -> int:
    """Remove a translation key from all languages."""
    key = args.key
    
    if not args.force:
        confirm = input(f"Remove '{key}' from all languages? [y/N]: ")
        if confirm.lower() != 'y':
            print("Aborted.")
            return 0
    
    removed_count = 0
    for lang in SUPPORTED_LANGUAGES:
        data = load_translations(lang)
        if delete_nested_key(data, key):
            save_translations(lang, data)
            print(f"✅ Removed '{key}' from {lang}.json")
            removed_count += 1
        else:
            print(f"⚠️  Key '{key}' not found in {lang}.json")
    
    if removed_count > 0:
        print(f"\n✅ Removed key from {removed_count} language(s)")
    else:
        print(f"\n⚠️  Key '{key}' was not found in any language")
    return 0


def cmd_update(args) -> int:
    """Update a specific translation in one or more languages."""
    key = args.key
    updates = {}
    
    if args.en: updates["en"] = args.en
    if args.it: updates["it"] = args.it
    if args.fr: updates["fr"] = args.fr
    if args.es: updates["es"] = args.es
    
    if not updates:
        print("❌ At least one language must be specified (--en, --it, --fr, --es)")
        return 1
    
    # Check key exists in at least one language
    key_exists = False
    for lang in SUPPORTED_LANGUAGES:
        data = load_translations(lang)
        if get_nested_key(data, key) is not None:
            key_exists = True
            break
    
    if not key_exists:
        print(f"❌ Key '{key}' does not exist. Use 'i18n add' to create it first.")
        return 1
    
    # Update specified languages
    for lang, value in updates.items():
        data = load_translations(lang)
        old_value = get_nested_key(data, key)
        if set_nested_key(data, key, value):
            save_translations(lang, data)
            if old_value:
                print(f"✅ Updated {lang}.json: \"{old_value}\" → \"{value}\"")
            else:
                print(f"✅ Added to {lang}.json: \"{value}\"")
        else:
            print(f"❌ Failed to update {lang}.json")
            return 1
    
    return 0


def cmd_search(args) -> int:
    """Search for keys/values in translations."""
    query = args.query.lower()
    results = []
    
    for lang in SUPPORTED_LANGUAGES:
        data = load_translations(lang)
        _search_recursive(data, "", query, lang, results)
    
    if not results:
        print(f"No results found for '{args.query}'")
        return 0
    
    # Group by key
    by_key = {}
    for key, lang, value in results:
        if key not in by_key:
            by_key[key] = {}
        by_key[key][lang] = value
    
    print(f"\n🔍 Found {len(by_key)} key(s) matching '{args.query}':\n")
    for key, langs in sorted(by_key.items()):
        print(f"  {key}:")
        for lang in SUPPORTED_LANGUAGES:
            if lang in langs:
                print(f"    [{lang}] {langs[lang]}")
        print()
    
    return 0


def _search_recursive(data: dict, prefix: str, query: str, lang: str, results: list):
    """Recursively search through translation dict."""
    for key, value in data.items():
        full_key = f"{prefix}.{key}" if prefix else key
        if isinstance(value, dict):
            _search_recursive(value, full_key, query, lang, results)
        elif isinstance(value, str):
            if query in full_key.lower() or query in value.lower():
                results.append((full_key, lang, value))


# =============================================================================
# Argument Parser Setup
# =============================================================================

def setup_parser(subparsers):
    """Setup i18n subcommands in the main dev.py parser."""
    
    # i18n add
    add_parser = subparsers.add_parser("add", help="Add a new translation key")
    add_parser.add_argument("key", help="Translation key (e.g., 'common.save')")
    add_parser.add_argument("--en", required=True, help="English translation")
    add_parser.add_argument("--it", required=True, help="Italian translation")
    add_parser.add_argument("--fr", required=True, help="French translation")
    add_parser.add_argument("--es", required=True, help="Spanish translation")
    add_parser.set_defaults(func=cmd_add)
    
    # i18n remove
    remove_parser = subparsers.add_parser("remove", help="Remove a translation key")
    remove_parser.add_argument("key", help="Translation key to remove")
    remove_parser.add_argument("-f", "--force", action="store_true", help="Skip confirmation")
    remove_parser.set_defaults(func=cmd_remove)
    
    # i18n update
    update_parser = subparsers.add_parser("update", help="Update a translation")
    update_parser.add_argument("key", help="Translation key to update")
    update_parser.add_argument("--en", help="English translation")
    update_parser.add_argument("--it", help="Italian translation")
    update_parser.add_argument("--fr", help="French translation")
    update_parser.add_argument("--es", help="Spanish translation")
    update_parser.set_defaults(func=cmd_update)
    
    # i18n search
    search_parser = subparsers.add_parser("search", help="Search translations")
    search_parser.add_argument("query", help="Search query (searches keys and values)")
    search_parser.set_defaults(func=cmd_search)
```

### Integrazione in `dev.py`

Aggiungere nel parser `i18n`:

```python
# In dev.py, sezione i18n
i18n_subparsers = i18n_parser.add_subparsers(dest="i18n_action")

# Existing audit command
audit_parser = i18n_subparsers.add_parser("audit", help="Audit translation coverage")

# New commands from i18n_cli
from scripts.i18n_cli import setup_parser as setup_i18n_parser
setup_i18n_parser(i18n_subparsers)
```

---

## 📖 Esempi d'Uso

### Aggiungere una nuova chiave

```bash
./dev.py i18n add "uploads.deleteConfirm" \
    --en "Are you sure you want to delete this file?" \
    --it "Sei sicuro di voler eliminare questo file?" \
    --fr "Êtes-vous sûr de vouloir supprimer ce fichier ?" \
    --es "¿Estás seguro de que deseas eliminar este archivo?"
```

### Rimuovere una chiave

```bash
./dev.py i18n remove "old.unused.key"
# Chiede conferma
./dev.py i18n remove "old.unused.key" -f  # Skip conferma
```

### Modificare una traduzione

```bash
# Aggiorna solo italiano
./dev.py i18n update "common.save" --it "Salva modifiche"

# Aggiorna più lingue
./dev.py i18n update "common.save" --en "Save Changes" --it "Salva modifiche"
```

### Cercare nelle traduzioni

```bash
./dev.py i18n search "broker"
# Mostra tutte le chiavi/valori contenenti "broker"

./dev.py i18n search "elimina"
# Trova traduzioni italiane con "elimina"
```

---

## 📋 Command Tree Aggiornato

```
dev.py i18n [-h]
├──╴audit [--format]     # Audit traduzioni (esistente)
├──╴add <key> --en --it --fr --es   # Aggiungi chiave
├──╴remove <key> [-f]    # Rimuovi chiave
├──╴update <key> [--en] [--it] [--fr] [--es]  # Modifica
╰──╴search <query>       # Cerca
```

---

## ✅ Checklist Implementazione

- [x] Creare `scripts/i18n_cli.py` con funzioni base → Integrato in `frontend/scripts/i18n-audit.py`
- [x] Integrare in `dev.py` i18n subcommands
- [x] Test: `./dev.py i18n add` con chiave nuova
- [x] Test: `./dev.py i18n add` con chiave esistente (deve fallire)
- [x] Test: `./dev.py i18n remove` con conferma
- [x] Test: `./dev.py i18n update` singola lingua
- [x] Test: `./dev.py i18n search` trova risultati
- [x] Aggiornare `--help` con nuovi comandi
- [x] Output formattato come tabelle (miglioramento extra)

---

## 🔗 Dipendenze

- Nessuna dipendenza esterna
- Solo libreria standard Python (json, pathlib, argparse)

---

## 📚 Aggiornamento Welcome Prompt

Aggiungere nella sezione comandi utili:

```markdown
| **Gestire traduzioni** | `./dev.py i18n add "key" --en "..." --it "..." --fr "..." --es "..."` |
| **Cercare traduzioni** | `./dev.py i18n search "query"` |
```
