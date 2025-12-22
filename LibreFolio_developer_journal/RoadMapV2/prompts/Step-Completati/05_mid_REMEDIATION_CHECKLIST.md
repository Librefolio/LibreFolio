# Checklist Remediation - LibreFolio

**Riferimento completo:** `REMEDIATION_PLAN.md`

---

## 🔴 PRIORITÀ ALTA

### Database Models & Schema
- [x] **1.1** ~~Relazione bidirezionale~~ (deprecato - vedi 1.1b)
  - [x] ~~Aggiunto campo cash_movement_id~~ 
  - [x] ~~Test bidirectional~~ (da aggiornare)
  - ⚠️ **DA CORREGGERE** - architettura sbagliata

- [x] **1.1b** Correggere architettura: Transaction → CashMovement unidirezionale
  - [x] Aggiungere ON DELETE CASCADE a Transaction.cash_movement_id FK
  - [x] Rimuovere CashMovement.linked_transaction_id (ridondante)
  - [x] Aggiungere CHECK constraint per validare tipo-CashMovement (se il tipo è uno di quelli che richiede la creazione di un CashMovement associato)
  - [x] Verificare attivazione PRAGMA foreign_keys = ON in session.py o configurazione DB (aggiungere se necessario, per garantire integrità referenziale). Aggiungere se assente anche un test method per verificarlo in validation.
  - [x] Modificare migrazione 001_initial.py
  - [x] Aggiornare populate_mock_data.py (rimuovere linked_transaction_id)
  - [x] Rinominare test: test_transaction_cash_bidirectional → test_transaction_cash_integrity
  - [x] Aggiornare test per unidirezionale + CASCADE + CHECK constraint
  - [x] Creare test_transaction_types.py (nuovo)
  - [x] Aggiornare docs/database-schema.md
  - [x] Ricreare database test - NORMALIZZAZIONE CHECK CONSTRAINTS COMPLETATA CON SQLGLOT
  - [x] get_db_check_constraints() aggiornato per ritornare tuple comparabili con get_model_check_constraints()

- [x] **1.2** Eliminare colonne ridondanti fees/taxes
  - [x] Verificare se esistono nel modello (esistevano)
  - [x] Rimosse da models.py, migrazione, populate_mock_data
  - [x] Test: validate schema (passato)
  - [x] Database ricreato con successo

### Scheduled Investment
- [x] **2.1** Refactoring schema interesse composto ✅ **COMPLETATO**
  - [x] Creare enum: compounding, compound_frequency, day_count
  - [x] Estendere InterestRatePeriod con nuovi campi (con validazione start_date/end_date)
  - [x] Aggiornare LateInterestConfig  
  - [x] Creare ScheduledInvestmentSchedule (classe completa con validazione)
  - [x] Implementare funzioni compound interest in financial_math.py
  - [x] Implementare day count conventions (ACT/360, 30/360, ACT/ACT) in financial_math.py
  - [x] Aggiungere find_active_period() per ottenere periodo completo
  - [x] Aggiornare ScheduledInvestmentProvider per usare nuove funzioni
    - [x] Provider recupera dati da DB (asset + transactions)
    - [x] Calcola face_value da transactions (BUY - SELL - principal repayments)
    - [x] Supporta "_transaction_override" per test
    - [x] Usa compound interest e day count conventions per periodo
  - [x] Eliminare face_value e maturity_date da Asset model
  - [x] Aggiornare migrazione 001 (rimossi face_value, maturity_date, late_interest)
  - [x] **Test: Day Count Conventions** (test_day_count_conventions.py) ✅ 20/20 passed
    - [x] ACT/365: 30 giorni, 1 anno, range multi-anno
    - [x] ACT/360: 30 giorni, 90 giorni, 360 giorni
    - [x] ACT/ACT: anno non bisestile, bisestile, range attraverso bisestile
    - [x] 30/360: stesso mese, mesi consecutivi, end-of-month cases
  - [x] **Test: Compound Interest** (test_compound_interest.py) ✅ 28/28 passed
    - [x] Simple interest: vari periodi e rate
    - [x] Compound annual, semiannual, quarterly, monthly, daily, continuous
    - [x] Edge cases: rate 0%, time 0, principal 0
  - [x] **Test: Financial Math Integration** (test_financial_math.py) ✅ 23/23 passed
    - [x] find_active_period(): vari scenari (within schedule, grace period, after grace, before schedule)
    - [x] find_active_rate(): backward compatibility
    - [x] Combinazioni day count + compounding (preserves all period attributes)
  - [x] **Test: ScheduledInvestmentProvider** (test_synthetic_yield.py) ✅ 9/9 passed
    - [x] Provider param validation (Pydantic)
    - [x] get_current_value() e get_history_value() con _transaction_override
    - [x] _calculate_value_for_date() metodo privato
    - [x] Integration: get_prices() via AssetSourceManager
    - [x] Verificato: no DB storage (calcolo on-demand)
    - [x] Utility functions: find_active_rate(), calculate_accrued_interest() con Pydantic
  - [x] **Test: Pydantic Schemas** (test_scheduled_investment_schemas.py) ✅ 23/25 passed (2 skipped)
    - [x] InterestRatePeriod validation (date ranges, rates, compounding logic)
    - [x] LateInterestConfig validation (rates, grace period)
    - [x] ScheduledInvestmentSchedule validation (overlaps, gaps, ordering, auto-sorting)
  - [x] **Test: Integration E2E** (test_synthetic_yield_integration.py) ✅ 3/3 passed
    - [x] Scenario prestito P2P completo (periodi + grace + late interest)
    - [x] Scenario bond con cedole (compound quarterly)
    - [x] Scenario cambio rate programmato (mixed SIMPLE/COMPOUND)
  - [x] **Documentazione**: financial-calculations/ e testing/ ✅ COMPLETATA E CONSOLIDATA
    - [x] Creata struttura docs/financial-calculations/ con README.md principale
    - [x] day-count-conventions.md - Tutte le convenzioni implementate
    - [x] interest-types.md - Simple vs Compound con esempi
    - [x] compounding-frequencies.md - Tutte le frequenze con comparazioni
    - [x] scheduled-investment-provider.md - Architettura provider, JSON format, algoritmo period-based
    - [x] Creata struttura docs/testing/ con README.md principale e guide complete
    - [x] utils-tests.md - Guida test utility (day count, compound, schemas)
    - [x] services-tests.md - Guida test servizi (FX, asset source, synthetic yield)
    - [x] database-tests.md - Guida test database (schema, constraints, integrity)
    - [x] api-tests.md - Guida test API (endpoints REST)
    - [x] synthetic-yield-e2e.md - Scenari integrazione completi
    - [x] Link incrociati tra tutti i documenti
    - [x] Esempi di codice e JSON in ogni documento
    - [x] ⚠️ **CONSOLIDAMENTO**: Eliminati file legacy obsoleti (financial-calculations.md, testing-guide.md, testing-environment.md)
    - [x] ⚠️ **AGGIORNAMENTO**: docs/README.md aggiornato con nuova struttura

### Code Organization
- [x] **3.1** Spostare utcnow() in utils
  - [x] Creare utils/datetime_utils.py
  - [x] Spostare funzione con docs
  - [x] Aggiornare import in models.py
  - [x] Test: datetime_utils (nuovo)
  - [x] Verificare nessuna regressione

- [x] **3.2** Fattorizzare funzioni precisione Decimal
  - [x] Verificato non esistono funzioni nel modulo FX
  - [x] Creato utils/decimal_utils.py con funzioni complete
  - [x] Implementato get_model_column_precision()
  - [x] Implementato truncate_to_db_precision()
  - [x] Aggiornato asset_source.py (rimosso MOCK)
  - [x] Test: test_decimal_utils.py (nuovo, 14 test passati)
  - [x] Aggiunto a test_runner.py

---

## ⚠️ PRIORITÀ MEDIA

### Database Models
- [x] **1.3** Aggiungere settlement_date a CashMovement
  - [x] Aggiungere campo opzionale
  - [x] Modificare la Migrazione 001 di Alembic
  - [x] Aggiornare logica calcoli (da verificare nei servizi)
  - [x] Test: db_schema_validate passato
  - [x] Aggiornare docs

- [x] **1.4** Chiarire trade_date vs settlement_date
  - [x] Aggiornare documentazione Transaction
  - [x] Verificare calcoli usano settlement_date (documentato)
  - [x] trade_date rimane required ma informativo
  - [ ] Aggiornare import CSV (quando implementato)
  - [ ] Test: transaction_dates, portfolio_calculations (quando implementati)
  - [x] Aggiornare docs

### Code Cleanup
- [x] **3.3** Rimuovere default USD hardcoded
  - [x] Query asset.currency in upsert_manual_prices
  - [x] Usare asset.currency come default
  - [x] Test: asset_source, prices API

- [x] **4.1** Chiarire docs engine/session
  - [x] Aggiornare docstring get_async_engine()
  - [x] Aggiungere commenti strategia singleton
  - [x] Rimuovere TODO misleading
  - [x] Test: session_management (nuovo)

---

## ⚠️ PRIORITÀ BASSA

- [x] **2.2** Day count conventions enum (completato come parte di 2.1)
  - [x] Enum DayCountConvention creato (ACT_365, ACT_360, ACT_ACT, THIRTY_360)
  - [x] Integrato in InterestRatePeriod e LateInterestConfig
  - [x] Test coverage completo
- [ ] **3.4** Garbage collector cache provider (futuro)

---

## 📋 ORDINE ESECUZIONE CONSIGLIATO

### Fase 1: Quick Wins ✅ COMPLETATA
1. ✅ **3.1** Spostare utcnow()
2. ✅ **4.1** Chiarire docs engine/session
3. ✅ **3.3** Rimuovere default USD

### Fase 2: Database Cleanup ✅ COMPLETATA (ma da correggere)
4. ✅ **1.2** Eliminare colonne fees/taxes ridondanti
5. ⚠️ **1.1** ~~Relazione bidirezionale~~ (deprecato - vedi 1.1b)
6. ✅ **3.2** Fattorizzare precisione Decimal

### Fase 2b: Correzione Architettura DB 🔴 URGENTE
7. ✅ **1.1b** Correggere Transaction → CashMovement unidirezionale + CASCADE

### Fase 3: Date Management ✅ COMPLETATA
7. ✅ **1.4** Chiarire trade_date/settlement_date
8. ✅ **1.3** Settlement date CashMovement

### Fase 4: Major Refactoring ✅ COMPLETATA
9. ✅ **2.1** Schema interesse composto (COMPLETATO: provider, test, documentazione)
10. ✅ **2.2** Day count conventions enum

---

**Ultima revisione:** 17 Novembre 2025
