# Piano di Remediation - LibreFolio

**Data creazione:** 13 Novembre 2025  
**Obiettivo:** Pulire, riorganizzare e allineare il codice sorgente rimuovendo refusi e migliorando la struttura

---

## CATEGORIA 1: DATABASE MODELS & SCHEMA OPTIMIZATION

### 1.1 ✅ DEPRECATO - Relazione bidirezionale (da correggere con 1.1b)

**Stato:** Implementato ma architettura da correggere  
**Problema architetturale identificato:** La relazione bidirezionale non è necessaria e complica la gestione.  
**Soluzione:** Task 1.1b corregge l'architettura rendendola unidirezionale.

---

### 1.1b 🔴 PRIORITÀ URGENTE - Correggere architettura: Transaction → CashMovement unidirezionale

**Razionale:**

- È la **Transaction** (BUY/SELL/DIVIDEND/INTEREST) che genera il **CashMovement**, non viceversa
- La relazione deve essere **unidirezionale**: Transaction → CashMovement
- Solo alcuni tipi di Transaction generano CashMovement (BUY, SELL, DIVIDEND, INTEREST, FEE, TAX)
- Altri tipi (ADD_HOLDING, REMOVE_HOLDING, TRANSFER_IN, TRANSFER_OUT) NON generano CashMovement

**Problema attuale:**

- Implementata relazione bidirezionale (Transaction.cash_movement_id + CashMovement.linked_transaction_id)
- CashMovement.linked_transaction_id è ridondante e va rimosso
- Transaction deve puntare a CashMovement con ON DELETE CASCADE
- Manca vincolo DB per garantire che certi tipi di Transaction abbiano CashMovement obbligatorio

**Azioni:**

#### 1. Modello Database (models.py)

- **Mantenere** `Transaction.cash_movement_id` (già presente)
- **Aggiungere** `ON DELETE CASCADE` al Foreign Key
- **Rimuovere** `CashMovement.linked_transaction_id` (ridondante)
- **Aggiungere** CHECK constraint per validare presenza CashMovement:
  ```sql
  CHECK (
    (type IN ('BUY', 'SELL', 'DIVIDEND', 'INTEREST', 'FEE', 'TAX') AND cash_movement_id IS NOT NULL)
    OR
    (type NOT IN ('BUY', 'SELL', 'DIVIDEND', 'INTEREST', 'FEE', 'TAX') AND cash_movement_id IS NULL)
  )
  ```
- **Verificare** che PRAGMA foreign_keys = ON sia attivo in session.py o configurazione DB, e aggiungerlo se necessario. Aggiungere se assente anche un test method per verificarlo
  in validation.

#### 2. Migrazione Alembic (modificare 001_initial.py)

- Modificare FK `Transaction.cash_movement_id` con `ON DELETE CASCADE`
- Rimuovere colonna `CashMovement.linked_transaction_id`
- Aggiungere CHECK constraint per validazione tipo-CashMovement
- Aggiornare indici (rimuovere indice su linked_transaction_id)

#### 3. Codice applicativo

- **populate_mock_data.py**: Rimuovere assegnazione `cash_mov.linked_transaction_id`
- **Schemas Pydantic**: Aggiornare eventuali schemi API che espongono linked_transaction_id
- **Services**: Verificare logica creazione Transaction+CashMovement sia corretta
- **API endpoints**: Verificare che nessun endpoint esponga/usi linked_transaction_id

#### 4. Test da aggiornare/creare

- `test_db/test_transaction_cash_bidirectional.py` → **RINOMINARE** in `test_transaction_cash_integrity.py`
- Modificare test per verificare:
    - Transaction → CashMovement unidirezionale (non viceversa)
    - ON DELETE CASCADE funziona (eliminare Transaction elimina CashMovement)
    - CHECK constraint respinto se BUY senza cash_movement_id
    - CHECK constraint accettato se ADD_HOLDING senza cash_movement_id
- `test_db/test_transaction_types.py` (nuovo) - verificare vincoli per tipo
- `test_api/test_transactions.py` - verificare creazione/cancellazione corretta
- `test_services/test_transaction_service.py` - verificare logica business

#### 5. Documentazione

- Aggiornare `docs/database-schema.md` con architettura corretta
- Documentare quali tipi Transaction generano CashMovement
- Aggiornare diagrammi ER se presenti

**Files impattati:**

- `backend/app/db/models.py` (modificare FK, rimuovere linked_transaction_id, aggiungere CHECK)
- `backend/alembic/versions/001_initial.py` (modificare schema)
- `backend/test_scripts/test_db/populate_mock_data.py` (rimuovere linked_transaction_id)
- `backend/test_scripts/test_db/test_transaction_cash_integrity.py` (rinominare e aggiornare)
- `backend/test_scripts/test_db/test_transaction_types.py` (nuovo)
- `backend/app/schemas/transactions.py` (verificare e aggiornare se esiste)
- `backend/app/api/v1/transactions.py` (verificare e aggiornare se esiste)
- `docs/database-schema.md`

**Benefici:**

- ✅ Architettura più chiara e corretta
- ✅ Cancellazione sincronizzata via ON DELETE CASCADE
- ✅ Validazione automatica via CHECK constraint
- ✅ Meno complessità (una sola direzione FK)
- ✅ Impossibile creare dati inconsistenti

**Note:**

- Questo task corregge l'implementazione del task 1.1 precedente
- Va eseguito PRIMA di procedere con altre fasi
- Richiede ricreare database di test
- I dati esistenti (se presenti) devono essere migrati

---

### 1.2 ✅ PRIORITÀ ALTA - Eliminare colonne ridondanti `fees` e `taxes` da Transaction

**TODO Riferimento:** `models.py:415-416`

**Problema:**

- Le colonne `fees` e `taxes` in `Transaction` sono ridondanti
- Devono essere gestite come transazioni separate di tipo FEE e TAX
- Collegamento ai rispettivi `cash_movements` generati

**Azioni:**

1. Verificare se le colonne esistono nel modello attuale (da controllare)
2. Se esistono, creare migrazione Alembic per rimuoverle
3. Assicurarsi che il codice non le usi più
4. Aggiornare documentazione e esempi

**Test da eseguire/aggiornare:**

- `test_db/test_transaction_types.py` - verificare gestione FEE/TAX separate
- `test_api/test_transactions.py` - verificare API non accetti fees/taxes
- `test_services/test_transaction_service.py` - verificare creazione corretta

**Files impattati:**

- `backend/app/db/models.py`
- `backend/alembic/versions/XXXXXX_remove_fees_taxes_columns.py` (nuovo se esistono)
- `docs/database-schema.md`

---

### 1.3 ⚠️ PRIORITÀ MEDIA - Aggiungere `settlement_date` a CashMovement

**TODO Riferimento:** `models.py:636`

**Problema:**

- `CashMovement` ha solo `trade_date`
- Per uniformità con `Transaction` serve anche `settlement_date`
- I calcoli dovrebbero usare `settlement_date` come data effettiva

**Azioni:**

1. Aggiungere campo `settlement_date` opzionale a `CashMovement`
2. Creare migrazione Alembic
3. Aggiornare la logica per usare `settlement_date` quando disponibile
4. Aggiornare documentazione

**Test da eseguire/aggiornare:**

- `test_db/test_cash_movements.py` - verificare gestione settlement_date
- `test_services/test_cash_balance.py` - verificare calcoli con settlement_date
- `test_api/test_cash_accounts.py` - verificare API

**Files impattati:**

- `backend/app/db/models.py`
- `backend/alembic/versions/XXXXXX_add_settlement_date_to_cash_movement.py` (nuovo)
- `backend/app/services/cash_service.py` (verificare e aggiornare logica)
- `docs/database-schema.md`

---

### 1.4 ⚠️ PRIORITÀ MEDIA - Chiarire uso di trade_date vs settlement_date in Transaction

**TODO Riferimento:** `models.py:418-426`

**Problema:**

- Documentazione poco chiara su quale data usare nei calcoli
- `settlement_date` dovrebbe essere la data effettiva per i calcoli
- `trade_date` dovrebbe essere solo informativa e opzionale

**Azioni:**

1. Aggiornare documentazione del modello `Transaction`
2. Verificare che tutti i calcoli usino `settlement_date`
3. Rendere `trade_date` opzionale se non lo è già
4. Aggiungere esempi chiari nei commenti
5. Aggiornare logica di import CSV (Directa e altri)

**Test da eseguire/aggiornare:**

- `test_db/test_transaction_dates.py` - verificare calcoli con settlement_date
- `test_services/test_portfolio_calculations.py` - verificare date corrette
- `test_external/test_import_directa.py` - verificare mappatura corretta

**Files impattati:**

- `backend/app/db/models.py`
- `backend/app/services/portfolio_service.py`
- `backend/app/services/import_service.py`
- `docs/database-schema.md`

---

## CATEGORIA 2: SCHEDULED INVESTMENT REFACTORING

### 2.1 🔴 PRIORITÀ ALTA - Completare refactoring schema interesse composto

**TODO Riferimento:** `models.py:323-343`, `schemas/assets.py:73-74,118-119,160-161`, `financial_math.py:56,129-130`

**Problema:**

- Schema attuale troppo semplice: solo SIMPLE interest con ACT/365
- Serve supporto per interesse composto, diverse convenzioni day count, diverse frequenze
- Schema JSON proposto ma non implementato
- Le classi Pydantic `InterestRatePeriod`, `LateInterestConfig`, `ScheduledInvestmentParams` sono incomplete

**Schema proposto (da implementare):**

```json
{
  "schedule": [
    {
      "start_date": "YYYY-MM-DD",
      "end_date": "YYYY-MM-DD",
      "annual_rate": 0.085,
      "compounding": "SIMPLE" | "COMPOUND",
      "compound_frequency": "DAILY" | "MONTHLY" | "ANNUAL",
      "day_count": "ACT/365" | "ACT/360" | "30/360"
    }
  ],
  "late_interest": {
    "annual_rate": 0.12,
    "grace_days": 0
  }
}
```

**Azioni:**

1. Creare enum per `compounding`, `compound_frequency`, `day_count` in `schemas/assets.py`
2. Estendere classe `InterestRatePeriod` con nuovi campi
3. Aggiornare `LateInterestConfig` con schema completo
4. Creare nuova classe Pydantic per tutto lo schedule completo
5. Implementare funzioni in `financial_math.py` per:
    - Diverse day count conventions (ACT/360, 30/360)
    - Calcolo interesse composto con varie frequenze
6. Aggiornare plugin `ScheduledInvestmentProvider`
7. Eliminare `face_value` e `maturity_date` da `Asset` (ridondanti)
8. Aggiornare migrazione Alembic per schema JSON

**Test da eseguire/aggiornare:**

- `test_services/test_synthetic_yield.py` - estendere con compound interest
- `test_utils/test_financial_math.py` - testare tutte le convenzioni
- `test_services/test_asset_source.py` - testare plugin aggiornato
- Creare `test_utils/test_day_count_conventions.py` (nuovo)
- Creare `test_utils/test_compound_interest.py` (nuovo)

**Files impattati:**

- `backend/app/schemas/assets.py`
- `backend/app/utils/financial_math.py`
- `backend/app/db/models.py`
- `backend/app/services/asset_source_providers/scheduled_investment.py`
- `backend/alembic/versions/XXXXXX_scheduled_investment_schema_v2.py` (nuovo)
- `docs/financial-calculations.md`
- `docs/assets/scheduled-investment-provider.md`

**NOTA:** Questo è un refactoring importante e va fatto DOPO aver verificato che il sistema attuale funzioni correttamente.

---

### 2.2 ⚠️ PRIORITÀ BASSA - Aggiungere enum per day count conventions

**TODO Riferimento:** `financial_math.py:30`

**Problema:**

- Solo ACT/365 implementato
- Manca enum per scegliere diverse convenzioni

**Azioni:**

1. Creare enum `DayCountConvention` in `schemas/assets.py`
2. Implementare funzioni per ACT/360, 30/360
3. Parametrizzare `calculate_daily_factor_between_act365` → `calculate_daily_factor`

**Test da eseguire/aggiornare:**

- `test_utils/test_day_count_conventions.py` (nuovo)
- `test_utils/test_financial_math.py` - verificare tutte le convenzioni

**Files impattati:**

- `backend/app/schemas/assets.py`
- `backend/app/utils/financial_math.py`

**NOTA:** Parte di 2.1, può essere fatto insieme.

---

## CATEGORIA 3: CODE ORGANIZATION & CLEANUP

### 3.1 ✅ PRIORITÀ ALTA - Spostare `utcnow()` in utils

**TODO Riferimento:** `models.py:31`

**Problema:**

- Funzione helper `utcnow()` definita in `models.py`
- Dovrebbe essere in un modulo utils per riutilizzabilità
- Nessuno la importa da models attualmente (grep conferma)

**Azioni:**

1. Creare file `backend/app/utils/datetime_utils.py` (se non esiste)
2. Spostare funzione `utcnow()` con la sua documentazione
3. Aggiungere altre utility date/time se necessario
4. Aggiornare import in `models.py`
5. Verificare non ci siano altri posti che la usano

**Test da eseguire/aggiornare:**

- `test_utils/test_datetime_utils.py` (nuovo) - testare utcnow()
- Tutti i test DB esistenti - verificare nessuna regressione

**Files impattati:**

- `backend/app/utils/datetime_utils.py` (nuovo)
- `backend/app/db/models.py`

---

### 3.2 ✅ PRIORITÀ ALTA - Fattorizzare funzioni di precisione Decimal

**TODO Riferimento:** `asset_source.py:198-212,215-235`

**Problema:**

- Funzioni `get_price_column_precision()` e `truncate_price_to_db_precision()` sono MOCK
- Dovrebbero leggere precisione dal modello DB
- Duplicazione logica con modulo FX che ha funzioni simili

**Azioni:**

1. Cercare nel modulo FX le funzioni `get_column_decimal_precision()` e `truncate_decimal_to_db_precision()`
2. Creare modulo unificato `backend/app/utils/decimal_utils.py`
3. Implementare funzione generica che legge precisione dal SQLModel:
   ```python
   def get_model_column_precision(model: Type[SQLModel], column_name: str) -> tuple[int, int]
   ```
4. Implementare funzione generica di troncamento
5. Aggiornare sia `asset_source.py` che il modulo FX
6. Rimuovere hardcoded (18, 6)

**Test da eseguire/aggiornare:**

- `test_utils/test_decimal_utils.py` (nuovo) - testare lettura precisione
- `test_services/test_asset_source.py` - verificare troncamento corretto
- `test_services/test_fx_service.py` - verificare nessuna regressione

**Files impattati:**

- `backend/app/utils/decimal_utils.py` (nuovo)
- `backend/app/services/asset_source.py`
- `backend/app/services/fx_service.py` (verificare e aggiornare)

---

### 3.3 ⚠️ PRIORITÀ MEDIA - Rimuovere default "USD" hardcoded

**TODO Riferimento:** `asset_source.py:485`

**Problema:**

- Default currency "USD" hardcoded nella funzione `upsert_manual_prices`
- Dovrebbe leggere currency dall'asset

**Azioni:**

1. Aggiungere query per ottenere asset.currency prima del loop
2. Usare asset.currency come default invece di "USD"
3. Verificare che tutti i test forniscano currency esplicita

**Test da eseguire/aggiornare:**

- `test_services/test_asset_source.py` - verificare currency corretta
- `test_api/test_prices.py` - verificare API usa currency asset

**Files impattati:**

- `backend/app/services/asset_source.py`

---

### 3.4 ⚠️ PRIORITÀ BASSA - Definire metodo garbage collector per cache provider

**TODO Riferimento:** `asset_source.py:191`

**Problema:**

- TODO placeholder per future cache cleanup
- Non implementato, non urgente

**Azioni:**

1. Definire interfaccia astratta `cleanup_cache()` in `AssetSourceProvider`
2. Implementare nei provider che usano cache
3. Creare job schedulato per chiamarlo periodicamente

**Test da eseguire/aggiornare:**

- `test_services/test_provider_cache.py` (nuovo) - quando implementato

**Files impattati:**

- `backend/app/services/asset_source.py`
- Provider specifici con cache

**NOTA:** Rimandare a quando si implementa caching nei provider.

---

## CATEGORIA 4: DATABASE ENGINE & SESSION MANAGEMENT

### 4.1 ⚠️ PRIORITÀ MEDIA - Verificare singleton pattern per engine e session

**TODO Riferimento:** `session.py:58,90`

**Problema:**

- `get_async_engine()` viene chiamata ma ritorna ogni volta un nuovo engine
- Tuttavia `async_engine` è creato come singleton globale (riga 87)
- Conflitto concettuale: la funzione suggerisce istanze multiple, ma il singleton è corretto
- Commento confuso sul sessionmaker

**Analisi:**

- ✅ `async_engine = get_async_engine()` crea UN singleton globale (CORRETTO)
- ✅ `get_session()` usa `async_engine` globale (CORRETTO)
- ❌ Nessuno chiama `get_async_engine()` dopo l'inizializzazione (grep conferma)
- ❌ TODO fuorviante: la gestione è già corretta

**Azioni:**

1. Rimuovere TODO misleading (la struttura attuale è corretta)
2. Aggiornare docstring di `get_async_engine()` per chiarire:
    - Non va chiamata direttamente
    - Usata solo per inizializzazione singleton
3. Aggiungere commento chiaro sulla strategia singleton
4. Verificare con test che una sola istanza di engine esiste

**Test da eseguire/aggiornare:**

- `test_db/test_session_management.py` (nuovo) - verificare singleton
- Verificare tutti i test esistenti passino

**Files impattati:**

- `backend/app/db/session.py`

---

## RIEPILOGO PRIORITÀ

### 🔴 PRIORITÀ URGENTE (correzione architettura):

1. **1.1b** - Correggere architettura Transaction → CashMovement (unidirezionale + CASCADE + CHECK)

### 🔴 PRIORITÀ ALTA (da fare dopo 1.1b):

2. **1.2** - Eliminare colonne fees/taxes ridondanti ✅ FATTO
3. **2.1** - Refactoring schema interesse composto (COMPLESSO - pianificare bene)
4. **3.1** - Spostare `utcnow()` in utils ✅ FATTO
5. **3.2** - Fattorizzare funzioni precisione Decimal ✅ FATTO

### ⚠️ PRIORITÀ MEDIA (quando possibile):

6. **1.3** - Aggiungere settlement_date a CashMovement
7. **1.4** - Chiarire trade_date vs settlement_date
8. **3.3** - Rimuovere default USD hardcoded
9. **4.1** - Chiarire documentazione engine/session

### ⚠️ PRIORITÀ BASSA (opzionale/futuro):

10. **2.2** - Day count conventions (parte di 2.1)
11. **3.4** - Garbage collector cache (quando serve)

---

## ORDINE DI ESECUZIONE CONSIGLIATO

### Fase 1: Quick Wins (1-2 giorni)

1. **3.1** - Spostare `utcnow()` ✅ Semplice, no breaking changes
2. **4.1** - Chiarire docs engine/session ✅ Solo documentazione
3. **3.3** - Rimuovere default USD ✅ Semplice, migliora qualità

### Fase 2: Database Cleanup (2-3 giorni) ✅ COMPLETATA

4. **1.2** - Verificare e rimuovere fees/taxes ✅ FATTO
5. **1.1** - Relazione bidirezionale (deprecato - sostituito da 1.1b)
6. **3.2** - Fattorizzare precisione Decimal ✅ FATTO

### Fase 2b: Correzione Architettura DB (1 giorno) 🔴 URGENTE

7. **1.1b** - Correggere Transaction → CashMovement unidirezionale + CASCADE + CHECK
    - Questo corregge l'architettura del task 1.1 precedente
    - Da fare PRIMA di procedere con Fase 3

### Fase 3: Date Management (2-3 giorni)

7. **1.4** - Chiarire trade_date vs settlement_date
8. **1.3** - Aggiungere settlement_date a CashMovement

### Fase 4: Major Refactoring (1-2 settimane)

9. **2.1** - Schema interesse composto completo
    - Questo è il più complesso, richiede:
        - Design schema definitivo
        - Implementazione enum e classi Pydantic
        - Implementazione funzioni matematiche
        - Aggiornamento plugin
        - Test estensivi
        - Migrazione dati esistenti

---

## NOTE FINALI

- **Backup database** prima di ogni migrazione
- **Eseguire test completi** dopo ogni modifica
- **Aggiornare documentazione** contestualmente al codice
- **Committare atomicamente** ogni punto completato
- Per **2.1 (Scheduled Investment)**: considerare di implementare in branch separato

**Stato:** ⬜ Da iniziare  
**Ultima revisione:** 13 Novembre 2025

