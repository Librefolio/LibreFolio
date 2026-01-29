# Piano: Migrazione dev.sh → dev.py ✅ COMPLETATO

## Obiettivo

Trasformare `dev.sh` da script bash monolitico (~1100 linee) a sistema Python modulare con autocompletamento automatico via `argcomplete` e visualizzazione ad albero dei comandi.

---

## 📊 Stato: COMPLETATO (16 Gennaio 2026)

### Cosa è stato fatto:

1. ✅ Creato `dev.py` - Entry point Python con argparse, argcomplete e TreeParser
2. ✅ Semplificato `dev.sh` - Ora è un thin wrapper (~50 linee) che delega a dev.py
3. ✅ Spostati script in `scripts/`:
    - `test_runner.py` (da root)
    - `user_cli.py` (da root)
    - `list_api_endpoints.py` (da backend/test_scripts/)
4. ✅ Creato `scripts/cli_base.py` - Utilities condivise (Colors, paths, run_command)
5. ✅ Creato `scripts/cli_tree_parser.py` - TreeParser con visualizzazione albero comandi
6. ✅ Aggiunto `argcomplete` per autocompletamento automatico
7. ✅ Rimossi file legacy dalla root
8. ✅ Rinominato `fe` → `front` per chiarezza
9. ✅ Unificato `server` e `server:test` → `server [--test]`
10. ✅ Aggiunto `db create-clean` per ricreare DB da zero
11. ✅ Separato `mkdocs` come categoria dedicata con subparser visibili

---

## Architettura Finale

```
LibreFolio/
├── dev.py                      # Entry point principale (Python, TreeParser)
├── dev.sh                      # Thin wrapper bash per backward compatibility
└── scripts/
    ├── __init__.py
    ├── cli_base.py             # Utilities condivise (Colors, paths, etc.)
    ├── cli_tree_parser.py      # TreeParser, CustomFormatter, subparser_tree()
    ├── list_api_endpoints.py   # Lista/esporta API endpoints
    ├── test_runner.py          # Test orchestrator
    ├── update_js_cache.py      # Cache JS libraries
    └── user_cli.py             # User management CLI
```

---

## TreeParser Features

La libreria `cli_tree_parser.py` fornisce:

### TreeParser

Parser che mostra automaticamente l'albero dei comandi dopo l'help:

```
Command tree:
dev.py [-h]
├─┬╴db [-h]
│ ├──╴check [PATH] [-h]
│ ├──╴upgrade [PATH] [-h]
│ ├──╴migrate MESSAGE [-h]
│ ╰──╴create-clean [--test] [-h]
├─┬╴test [-v] [--coverage]
│ ├──╴api ACTION [-h]
│ ╰──╴all [-h]
╰──╴server [--test] [-h]
```

### CustomFormatter

Formatter migliorato che combina opzioni short/long:

- Prima: `-v VERBOSE, --verbose VERBOSE`
- Dopo: `-v, --verbose`

### subparser_tree()

Funzione standalone per generare l'albero ASCII.

---

## Autocompletamento

### Setup (una volta)

```bash
# Bash - aggiungi a ~/.bashrc
eval "$(register-python-argcomplete dev.py)"

# Zsh - aggiungi a ~/.zshrc  
autoload -U bashcompinit && bashcompinit
eval "$(register-python-argcomplete dev.py)"
```

---

## Comandi Disponibili

### 🖥️ Backend

```bash
./dev.py server              # Avvia server sviluppo (:8000)
./dev.py server --test       # Avvia server test (:8001, test DB)
./dev.py db upgrade          # Applica migrazioni
./dev.py db check            # Verifica constraints
./dev.py db migrate "msg"    # Crea migrazione
./dev.py db create-clean     # Cancella e ricrea DB da zero
./dev.py db create-clean -t  # Come sopra ma per test DB
```

### 🎨 Frontend

```bash
./dev.py front dev           # Dev server con HMR (:5173)
./dev.py front build         # Build produzione
./dev.py front check         # Type check
./dev.py front preview       # Preview build
```

### 🧪 Testing

```bash
./dev.py test api auth       # Test auth API
./dev.py test api all        # Tutti i test API
./dev.py test all            # TUTTI i test
./dev.py test --coverage all # Con coverage
```

### 👤 User Management

```bash
./dev.py user create <user> <email> <pass>
./dev.py user list
./dev.py user reset <user> <pass>
./dev.py user promote <user>
```

### 📚 Documentation

```bash
./dev.py mkdocs build        # Build sito documentazione
./dev.py mkdocs serve        # Serve localmente (:8002)
./dev.py mkdocs clean        # Rimuove cartella site/
./dev.py mkdocs deploy       # Deploy su GitHub Pages
```

### 📦 Tools

```bash
./dev.py api sync            # Rigenera client TypeScript
./dev.py i18n audit          # Audit traduzioni
./dev.py cache js            # Aggiorna cache JS
./dev.py info api            # Lista endpoints
./dev.py format              # Format con black
./dev.py lint                # Lint con ruff
```

### 🔧 Setup

```bash
./dev.py install             # Installa dipendenze
./dev.py shell               # Pipenv shell
```

---

## Compatibilità Backward

`dev.sh` rimane funzionante e converte automaticamente i vecchi comandi:

```bash
# Vecchio stile (ancora funziona per compatibilità)
./dev.sh fe:build            # → ./dev.py front build
./dev.sh server:test         # → ./dev.py server --test
./dev.sh db:upgrade          # → ./dev.py db upgrade

# Nuovo stile (consigliato)
./dev.py front build
./dev.py server --test
./dev.py db upgrade
```

---

## Note

- `dev.sh` è ora un wrapper minimale (~50 linee) che converte vecchi comandi e delega a dev.py
- `argcomplete` aggiunto a Pipfile per autocompletamento
- Tutti gli script in `scripts/` supportano esecuzione diretta e import
- TreeParser mostra albero comandi ricorsivamente per ogni subparser
- Format/lint usano black e ruff (configurati in pyproject.toml)
