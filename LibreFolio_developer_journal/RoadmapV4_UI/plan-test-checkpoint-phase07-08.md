# Test Checkpoint: Phase 07 Part 5 & Phase 08

**Obiettivo**: Completare la copertura dei test (Backend e Frontend E2E) per le funzionalità introdotte nella Fase 07 Parte 5 (BRIM Import Wizard) e nella Fase 08 (Market Data Scheduler) prima di procedere all'archiviazione della documentazione e alla prosecuzione della Dashboard.

---

## 🧪 1. Test E2E Frontend — Phase 07 Part 5 (Import Wizard)

Il backend per la Fase 07.5 è già ben testato (~90%). Il frontend ha una copertura dell'happy path (~60%), ma manca la copertura per la parte di risoluzione avanzata e UX degli asset non riconosciuti (file `generic_simple.csv`).

### Feature da testare (Nuovo E2E Spec)
Aggiungere o estendere uno spec (es. `frontend/e2e/transactions/import-wizard-resolution.spec.ts`) che carichi il file `generic_simple.csv` e verifichi i seguenti scenari:

- **Compare Modal**: click sul badge ⚠️ apre la vista comparativa (TransactionFormModal read-only) per vedere la riga originale.
- **Risoluzione UI Details**:
  - Verifica della presenza di `titleOverride` nel compare.
  - Verifica che l'animazione gialla `hl-match` venga triggerata quando si torna dalla compare view.
  - Verifica che `initialSearchQuery` sia pre-compilato nel campo di ricerca dell'AssetSelect in base al nome estratto.
  - Tooltip confidenza visibile sulle option dei candidati.
  - Candidati mostrati in cima con i badge corretti in AssetSelect.
- **Flusso "Add Identifier" (Manual Matching)**:
  - Selezione manuale di un asset dalla lista.
  - Verifica del prompt (ConfirmModal) per mappare definitivamente il fake_id all'asset scelto e aggiungere l'identificatore (es. simbolo estrato) al database.
- **Flusso "Create New Asset"**:
  - Click su "+ Create new" → apre l'AssetModal con i campi pre-compilati (nome, tipo dedotto) e la sezione "Ulteriori Info" espansa.
- **End-to-End Resolution**: completare la risoluzione del file `generic_simple.csv` e verificare che il tasto "Import" si abiliti correttamente dopo aver risolto tutti i `fake_id`.
- **Duplicate Detection (Doppio Import)**: Eseguire due volte l'importazione dello stesso file per verificare che al secondo passaggio le transazioni vengano rilevate correttamente come duplicati (segnalazione `likely duplicate` o `possible duplicate` e conseguente deselezione automatica).
- **UI Final Polish & Edge Cases**:
  - Creazione di un nuovo broker dallo Step 1 e verifica della reattività: il nuovo broker deve apparire subito nel dropdown senza refresh.
  - Apertura della `FilePreviewModal` (Step 1/2) per confermare il corretto posizionamento dello z-index rispetto alle modali sottostanti.
  - Verifica della presenza delle nuove tooltip i18n (es. specifica quote in italiano/inglese).

---

## 🧪 2. Test Backend & Frontend — Phase 08 (Scheduler)

Lo scheduler del mercato dati è stato completato lato implementazione, ma la suite di test è interamente da scrivere.

### 2.1 Backend Unit & Integration Tests

Aggiungere i seguenti file di test (es. in `backend/tests/services/scheduler/` e `backend/tests/api/`):

1. **`test_scheduler_state.py` (Unit)**: 
   - Load/save dello stato in JSON.
   - Scrittura atomica (`os.replace`).
   - Resilienza: recupero da file corrotto o assente (tutto a null).
2. **`test_scheduler_due.py` (Unit)**: 
   - Test di `due_current_price` e `due_history_sync`.
   - Edge case: calcolo slot multipli (es. "06:00, 23:00"), controlli su giorni della settimana (es. domenica se escluso), slot già eseguito, slot mai eseguito.
   - Gestione downtime a cavallo della mezzanotte.
3. **`test_scheduler_leader.py` (Unit)**: 
   - Mock di `psutil` per simulare l'elezione del leader.
   - Scenari: single-worker, multi-worker (chi ha il PID minore vince), zombie processes, Docker PID 1.
4. **`test_scheduler_loop.py` (Integration)**: 
   - Mock time e mock service layer (`AssetSourceManager`, `sync_pairs_bulk`).
   - Verifica che un ciclo completo scriva lo state correttamente.
   - Verifica che la sessione del db venga creata fresca per ogni job e chiusa correttamente.
5. **`test_scheduler_state_api.py` (API)**: 
   - Endpoint `GET /api/v1/settings/scheduler/state` (read-only, restituisce lo stato).
   - Endpoint `GET /api/v1/settings/scheduler/log` (JSONL parser, paginazione corretta `offset/limit`).
   - Verifica auth: accesso ristretto ai soli admin.
6. **`test_settings_api.py` (API Settings)**:
   - Verifica salvataggio e validazione delle 5 nuove chiavi dello scheduler (`scheduler_enabled`, `scheduler_current_price_frequency_minutes`, `scheduler_history_sync_times`, `scheduler_history_sync_days`, `scheduler_history_sync_horizon_days`).
   - Parsing range e formato (es. controllo formato "HH:MM", csv string).

### 2.2 Frontend E2E Tests

Creare/aggiornare gli spec (es. `frontend/e2e/settings/scheduler-settings.spec.ts`):

1. **Gestione Impostazioni Scheduler**:
   - Accesso alla GlobalSettingsTab come amministratore.
   - Modifica delle 5 nuove settings tramite la modale (`SchedulerConfigModal`).
   - Verifica del salvataggio nel database e persistenza a livello di UI.
   - Visibilità e accuratezza del campo "Last execution" dalla modale di hint.
2. **Scheduler Log Modal**:
   - Apertura della modale dello storico log.
   - Paginazione, filtri e apertura delle card con errori.
3. **Rimozione Fetch Interval**:
   - Accedere alla pagina di modifica asset (`AssetModal`) e alla configurazione del provider.
   - Verificare che il campo `Fetch Interval` non esista più (post-cleanup).

---

## 📈 Modalità di esecuzione

1. **Fase 1**: Esecuzione dei test Backend per lo Scheduler (Ph08) per garantire la solidità del demone.
2. **Fase 2**: Implementazione dei test E2E Frontend (Ph07.5 e Ph08).
3. **Fase 3**: Successo della CI locale (esecuzione completa con playwright e pytest).
4. **Archiviazione**: A testing completato, utilizzeremo la skill di archiving per pulire la cartella di pianificazione e prepararsi esclusivamente alla Dashboard M2.
