# Plan: UI Fixes Post Data-Separation

**Creato**: 2026-02-06
**Stato**: 🔲 TODO
**Priorità**: Media
**Dipende da**: Data Separation completata ✅

## Contesto

Durante i test di verifica della migrazione prod/test data separation, sono stati identificati alcuni bug UI pre-esistenti che necessitano correzione.

---

## 🐛 Lista Bug

### Bug 1: Preferenze Utente Non Applicate al Login

**Posizione**: Flusso di login / Gestione lingua
**Severità**: Media
**Descrizione**:

- Le preferenze utente (lingua, tema) salvate in `user_settings` non vengono applicate automaticamente al login
- Il pulsante lingua nella dashboard è correttamente temporaneo (session-only)
- Ma al login, la lingua dovrebbe essere letta da `user_settings` e applicata

**Comportamento Atteso**:

1. L'utente effettua il login
2. Il sistema legge `user_settings.language` e `user_settings.theme` dal DB
3. Il sistema applica queste impostazioni alla sessione
4. La dashboard mostra la lingua/tema corretti

**Comportamento Attuale**:

- Il login usa l'ultima lingua della sessione browser
- L'utente deve andare manualmente in Settings per vedere le proprie preferenze salvate

**Approccio di Fix**:

- Nella risposta di login (`/api/v1/auth/login`), includere le user settings
- Il frontend, al login riuscito, applica le settings allo store (lingua, tema, valuta base)
- File coinvolti:
    - `backend/app/api/v1/auth.py` - endpoint login
    - `frontend/src/routes/(public)/login/+page.svelte` - handler login success
    - `frontend/src/lib/stores/` - stores per lingua/tema

---

### Bug 2: Valuta Base Non Usata nella Modale Creazione Broker

**Posizione**: `BrokerCreateModal.svelte` - Campo Initial Balance
**Severità**: Bassa
**Descrizione**:

- Quando si crea un broker, il selettore valuta per il bilancio iniziale non usa come default la `base_currency` dell'utente
- Lo stesso problema potrebbe esistere nei form di deposito/prelievo transazioni (POC, non ancora implementati)

**Comportamento Atteso**:

- Il selettore valuta dovrebbe avere come default `userSettings.base_currency`

**Approccio di Fix**:

- Leggere `userSettings.base_currency` dallo store
- Impostarlo come valore di default per gli input valuta
- File coinvolti:
    - `frontend/src/lib/components/brokers/BrokerCreateModal.svelte`
    - Eventualmente altri form con selezione valuta

---

### Bug 3: Modale Upload BRIM - Nessuno Scroll con Molti File

**Posizione**: `BrimUploadModal.svelte`
**Severità**: Media
**Descrizione**:

- Quando si caricano molti file contemporaneamente, il contenuto della modale va in overflow
- Il pulsante "Carica" nel footer diventa irraggiungibile
- Non appare nessuna scrollbar per scorrere verso il basso

**Comportamento Atteso**:

- Il contenuto della modale dovrebbe essere scrollabile quando la lista file è lunga
- Il footer con i pulsanti di azione dovrebbe rimanere visibile (sticky)

**Approccio di Fix**:

- Aggiungere `max-height` e `overflow-y: auto` al container della lista file
- Assicurarsi che il footer rimanga fisso in fondo alla modale
- File coinvolti:
    - `frontend/src/lib/components/brokers/BrimUploadModal.svelte`
    - Verificare che `Modal.svelte` supporti contenuto scrollabile

---

### Bug 4: Pagina Files - Colonna Broker Non Auto-Aggiunta

**Posizione**: `FilesPage.svelte` o `BrimFilesTable.svelte`
**Severità**: Bassa
**Descrizione**:

- Se l'utente ha solo 1 broker, la colonna "Broker" è correttamente nascosta
- Quando l'utente carica un file su un 2° broker, la colonna dovrebbe apparire automaticamente
- Attualmente, l'utente deve cliccare "Reset" nel menu filtri per vedere la nuova colonna

**Comportamento Atteso**:

- La tabella dovrebbe rilevare quando i file appartengono a più broker e mostrare automaticamente la colonna
- Oppure: mostrare sempre la colonna broker se l'utente ha più di 1 broker

**Approccio di Fix**:

- Opzione A: Controllare `brokers.length > 1` per mostrare la colonna (più semplice)
- Opzione B: Controllare se i file visualizzati hanno diversi `broker_id` (reattivo)
- File coinvolti:
    - `frontend/src/lib/components/files/BrimFilesTable.svelte`
    - `frontend/src/routes/(app)/files/+page.svelte`

---

## 📋 Ordine di Implementazione Bug

1. **Bug 1** - Più impattante per UX (ogni login)
2. **Bug 3** - Blocca il workflow utente
3. **Bug 4** - Fastidio minore
4. **Bug 2** - Nice to have, transazioni non ancora implementate

---

## 🏷️ Feature: Sistema di Versioning con Git Tags

**Priorità**: Media
**Stima**: 2-3 ore

### Obiettivo

Implementare un sistema di versioning automatico basato su git tags che permetta di identificare esattamente la versione del codice in esecuzione, sia in sviluppo che in
produzione.

### Comportamento Desiderato

- Se siamo esattamente su un tag `v1.2.3` → versione mostrata: `v1.2.3`
- Se siamo N commit dopo il tag → versione mostrata: `v1.2.3-N-gabcdef` (N = numero commit, abcdef = hash corto)
- Se non ci sono tag → versione mostrata: `v0.0.0-gabcdef` o simile

### Comando Git da Usare

```bash
git describe --tags --always --dirty
```

- `--tags`: usa tutti i tag, non solo annotated
- `--always`: ritorna hash se non ci sono tag
- `--dirty`: aggiunge `-dirty` se ci sono modifiche non committate

### Dove Usare la Versione

#### 1. Backend (Python) - Dinamico a Runtime

La versione viene letta dinamicamente all'avvio, **NON** hardcodata:

- **Log di avvio server**: Mostra versione quando parte uvicorn
- **Endpoint `/api/v1/info`**: Ritorna versione nell'oggetto info
- **`pyproject.toml`**: Mantiene una versione statica di riferimento (es. `0.1.0`), ma la versione reale viene da git

```python
# backend/app/utils/version.py
import subprocess
from functools import lru_cache
from pathlib import Path


@lru_cache(maxsize=1)
def get_git_version() -> str:
    """Ottiene la versione da git describe."""
    try:
        project_root = Path(__file__).parent.parent.parent.parent
        result = subprocess.run(
            ["git", "describe", "--tags", "--always", "--dirty"],
            capture_output=True,
            text=True,
            cwd=project_root,
            timeout=5
            )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass
    return "unknown"
```

#### 2. Frontend (SvelteKit) - Dinamico a Build-Time

La versione viene iniettata al momento del build tramite Vite:

**`vite.config.ts`**:

```typescript
import {execSync} from 'child_process';

function getGitVersion(): string {
    try {
        return execSync('git describe --tags --always --dirty')
            .toString()
            .trim();
    } catch {
        return 'unknown';
    }
}

export default defineConfig({
    define: {
        __APP_VERSION__: JSON.stringify(getGitVersion()),
    },
    // ...
});
```

**`src/lib/version.ts`**:

```typescript
declare const __APP_VERSION__: string;
export const APP_VERSION: string = __APP_VERSION__ ?? 'unknown';
```

**`package.json`**: La versione nel package.json rimane statica (es. `0.0.1`) perché npm non supporta versioni dinamiche. La versione reale mostrata nell'app viene da git via Vite.

#### 3. CLI (`dev.py`)

Aggiungere comando per mostrare versione:

```bash
./dev.py info version
# Output: v1.2.3-5-gabcdef
```

#### 4. Dove Mostrare la Versione nell'UI

- **Footer frontend**: Piccolo, discreto (es. `LibreFolio v1.2.3-5-gabcdef`)
- **Pagina About/Settings**: Se esiste una sezione "About"
- **Console log** (solo dev mode): All'avvio dell'app

### File da Modificare/Creare

| File                                               | Azione    | Descrizione                       |
|----------------------------------------------------|-----------|-----------------------------------|
| `backend/app/utils/version.py`                     | **Nuovo** | Funzione `get_git_version()`      |
| `backend/app/api/v1/info.py`                       | Modifica  | Aggiungere versione alla response |
| `backend/app/main.py`                              | Modifica  | Log versione all'avvio            |
| `frontend/vite.config.ts`                          | Modifica  | Inject `__APP_VERSION__`          |
| `frontend/src/lib/version.ts`                      | **Nuovo** | Export `APP_VERSION`              |
| `frontend/src/lib/components/layout/Footer.svelte` | Modifica  | Mostrare versione                 |
| `scripts/cli_base.py` o `dev.py`                   | Modifica  | Comando `info version`            |

### Note Importanti

1. **`pyproject.toml` e `package.json`**: Mantengono versioni statiche per compatibilità con tool esterni (pip, npm), ma l'app usa sempre la versione git
2. **Docker**: Quando si builderà l'immagine, la versione verrà letta da git al momento del build e baked nell'immagine
3. **MkDocs**: Potrebbe mostrare la versione nel footer della documentazione

### Workflow per Release

1. Sviluppo normale → versione tipo `v1.2.3-5-gabcdef`
2. Quando pronto per release:
   ```bash
   git tag v1.3.0
   git push origin v1.3.0
   ```
3. Build immediatamente dopo il tag mostra `v1.3.0`
4. Commit successivi mostrano `v1.3.0-1-g...`

### Test di Verifica

```bash
# Verificare versione backend
./dev.py info version

# Verificare endpoint
curl http://localhost:8000/api/v1/info | jq .version

# Verificare frontend (dopo build)
# Guardare footer o console
```

---

## 📝 Note

- Questi bug esistevano prima della migrazione data separation
- Sono stati scoperti durante i test manuali della nuova struttura prod/test
- Nessuno è bloccante per la feature data separation
- Il sistema di versioning è indipendente dai bug e può essere implementato in parallelo

