# Plan: Round 12 Finale — Maturation Engine + Auto-Interest + Backend Cleanup + Frontend Fix

## Context

Round 12 della Phase 6 Step 3 di LibreFolio. I round precedenti (10, 11, 12.0, 12.1) hanno:
- Implementato AssetEvent infrastruttura + tabella DB
- Riscritto il provider `scheduled_investment` come motore puro deterministico (no DB access)
- Introdotto `InterestType` (SIMPLE/COMPOUND), `DayCountConvention` globale, cache theine 48h
- Aggiunto `initial_value` come oggetto Currency, `asset_events` nella config
- Frontend `ScheduledInvestmentEditor` con DataTable, CRUD periodi, late interest toggle

**Blocco 1.5 completato (2026-04-03):**
- Refactored `bulk_assign_providers` da DELETE+INSERT a UPSERT (preserva FK)
- `AssetEvent.source_plugin_key` → `provider_assignment_id` FK con ON DELETE CASCADE
- `AssetProviderAssignment.identifier` reso nullable per AUTO_GENERATED
- Tutti i test backend passano (DB 7/7, Schemas 4/4, Services 11/11, Utils 7/7, API Provider ✅)

**Problemi aperti identificati durante il testing manuale:**
1. `maturation_frequency` presente nello schema ma **non usata** nel motore — serve per emettere price points solo alle date di maturazione
2. Manca flag `generate_interest` per auto-generazione eventi di stacco interesse
3. `FALateInterestConfig` non ha `maturation_frequency` — il frontend lo deserializza ma non lo serializza
4. **Bug critico**: il save dalla modale non funziona per `scheduled_investment` (`hasProvider=false` perché `identifier` è vuoto per AUTO_GENERATED)
5. **Bug**: il pulsante "Test Configuration" è disabilitato per lo stesso motivo
6. `financial_math.py` contiene dead code (`find_active_period`) e va consolidato nel plugin
7. Vari polish frontend: componenti standard OS invece di custom, layout colonne, traduzioni mancanti
8. ~~`AssetEvent.source_plugin_key` è un VARCHAR — va sostituito con FK a `asset_provider_assignments` + refactor UPSERT~~ ✅ RISOLTO (Blocco 1.5)

---

## Decisioni di Design Confermate

### D1: Compound interest + cedola (generate_interest)
Quando `generate_interest=True` e `interest_type=COMPOUND`, dopo lo stacco la cedola riporta il valore a `initial_value`. Il `total_interest` si resetta a 0 e il compound riparte da `initial_value`. Questo è coerente con cedole reali (il bond paga la cedola e il NAV torna al nominale).

**Cedola = solo positiva**: `interest_amount = current_value - initial_value`. Se `interest_amount <= 0` (es. per price adjustment negativi che hanno portato il valore sotto `initial_value`), **non si genera** l'evento di stacco. In futuro si potrà raffinare con una colonna apposita per policy di generazione più fini (es. tasso cedola custom).

### D2: PRICE_ADJUSTMENT nel calcolo day-by-day
Gli eventi `PRICE_ADJUSTMENT` (positivi o negativi) vengono applicati nel calcolo giorno per giorno come già implementato (`event_adjustment += evt.value.amount`). Influenzano il valore corrente e quindi anche la base compound. Dopo uno stacco interesse (generate_interest), il valore torna a `initial_value` (non `initial_value + adjustments`), perché `event_adjustment` viene considerato nel calcolo della cedola: `interest_amount = principal + total_interest + event_adjustment - principal = total_interest + event_adjustment`. Dopo lo stacco, `total_interest` si resetta e `event_adjustment -= interest_amount`, riportando tutto a `principal`.

### D3: AssetEvent — FK a `asset_provider_assignments` con UPSERT
Sostituire `source_plugin_key: VARCHAR` con `provider_assignment_id: FK → asset_provider_assignments.id ON DELETE CASCADE`:
- `NULL` = evento creato manualmente dall'utente (sopravvive a tutto)
- `non-NULL` = evento auto-generato da quella configurazione provider

Prerequisito: cambiare `bulk_assign_providers` da DELETE+INSERT a **UPSERT** (UPDATE se esiste già un'assegnazione per lo stesso `asset_id`, INSERT solo se nuova). Questo preserva l'`id` della riga di assegnazione → il FK resta valido attraverso le riconfigurazioni.

**Flusso cambio provider** (utente cambia da provider A a provider B):
1. Frontend mostra modale di conferma: "Ci sono N eventi generati dalla configurazione precedente"
2. Opzioni: (a) elimina tutto (il DELETE dell'assegnazione fa CASCADE sugli eventi), (b) mantieni come manuali (UPDATE SET NULL sugli eventi prima del DELETE), (c) annulla
3. In Phase 7, se ci sono transazioni collegate a eventi → il CASCADE viene bloccato dal FK, forzando la "bonifica" utente

### D4: Somma eventi auto-generati + manuali
Gli eventi auto-generati (da `generate_interest=True`) e quelli manuali (tabella "Asset Events") si **sommano** se cadono sulla stessa data. L'utente può disabilitare `generate_interest` e usare solo eventi manuali per casi anomali.

### D5: Cache — valori + auto_events insieme
`_generate_schedule_values` restituisce `(dict[date, Decimal], list[FAAssetEventPoint])`. La cache theine salva la **tupla intera** (valori + auto_events). Gli auto_events sono deterministici e leggeri — cachearli insieme evita di ricalcolarli ad ogni richiesta e mantiene il pattern "una funzione, un risultato completo".

### D6: MATURITY_SETTLEMENT — evento di chiusura asset
Aggiungere `MATURITY_SETTLEMENT` a `AssetEventType`. Questo evento viene generato automaticamente quando `generate_interest=True` su `FALateInterestConfig` e rappresenta il rimborso finale del capitale. Dopo questo evento **il motore si ferma** — nessun ulteriore calcolo di prezzo.

Semantica:
- L'evento `MATURITY_SETTLEMENT` ha `value = valore residuo dell'asset` (= `principal + total_interest + event_adjustment` al momento del settlement). Di default è il valore completo; l'utente può modificarlo manualmente verso il basso (ma non oltre il residuo), e l'eventuale differenza rappresenta una perdita non rimborsata che non matura ulteriore late interest.
- Si genera in corrispondenza dell'ultima maturation date configurata nel late interest, oppure alla fine dell'ultimo periodo se non c'è late interest
- Nella valutazione del portafoglio, rappresenta il valore finale dell'asset
- Si attende che coincida con una transazione SELL 100% (o del residuo) in Phase 7
- Se l'utente non ha late interest e ha `generate_interest=True`, il settlement avviene all'`end_date` dell'ultimo periodo

### D7: Rimozione UniqueConstraint su `asset_events`
Rimuovere `UNIQUE(asset_id, date, type)` dalla tabella `asset_events`. Motivo: con `generate_interest=True`, il motore può generare un evento INTEREST automatico su una data in cui l'utente ha anche un evento INTEREST manuale. Questi devono **coesistere** nel DB (e sommarsi), non sovrascriversi.

Si mantengono gli **indici** (`idx_asset_event_asset_date`, `idx_asset_event_asset_type_date`) per performance delle query. Il dedup logico è gestito dal `provider_assignment_id`: `NULL` = manuale, non-`NULL` = auto-generato.

### D8: Ordine operazioni nel loop giornaliero del motore
L'ordine esplicito nel loop day-by-day di `_generate_schedule_values`:
1. **Calcolo interesse giornaliero** — accumula `total_interest`
2. **Auto-stacco cedola** — se maturation date + `generate_interest=True` + `interest_amount > 0`: genera evento, resetta (concettualmente: avviene a "mezzanotte e 1 min", riferito al giorno in corso)
3. **Applicazione eventi manuali** — INTEREST e PRICE_ADJUSTMENT dal config (avvengono "durante la giornata")
4. **Scrittura valore** — salva nel dict `values` solo se `current_date in all_maturation_dates`

### D9: Late interest — ottimizzazione calcolo con formula di salto
Per il late interest, il calcolo non itera giorno per giorno dall'inizio della maturity fino al target. Si usa una **formula di salto**:
- **SIMPLE**: `V = V_maturity + P * r * Δt` (closed-form, nessun loop)
- **COMPOUND**: `V = V_base * (1 + r * day_fraction)^N` dove `N` = numero di giorni tra il punto base e il target, oppure più precisamente `V_base * ∏(1 + r * frac_day_i)` che per day-by-day identico diventa una potenza

In pratica: per il range richiesto (`request_start_date` → `request_end_date`), si calcola il valore al punto di partenza con la formula closed-form, poi si itera day-by-day **solo nel sotto-periodo richiesto** (non dall'inizio della maturity).

---

## Sei blocchi di lavoro

### Blocco 1 — Eliminare `financial_math.py`, consolidare nel plugin

**Status: ✅ COMPLETATO** (2026-04-03)

**File da modificare:**
- `backend/app/services/asset_source_providers/scheduled_investment.py` — riceve le funzioni
- `backend/app/utils/financial_math.py` — **da eliminare**
- `backend/test_scripts/test_utilities/test_financial_math.py` — **da eliminare** (13 test orfani di `find_active_period`)
- `backend/test_scripts/test_services/test_asset_source.py` — aggiornare import (riga 41)
- `backend/test_scripts/test_utilities/test_day_count_conventions.py` — aggiornare import (riga 19)
- `scripts/test_runner.py` — rimuovere `utils_financial_math` (riga 732) e entry `"financial-math"` (riga 2107)

**Dettaglio:**
- [x] Spostare `calculate_day_count_fraction`, `calculate_simple_interest`, `_calculate_act_365`, `_calculate_act_360`, `_calculate_act_act`, `_calculate_30_360` come funzioni private in `scheduled_investment.py` (sezione `# Financial Math` sopra la classe)
- [x] **Fattorizzare** `_calculate_act_365` + `_calculate_act_360` in unica `_calculate_act_fixed(start, end, denominator: int)` — entrambe fanno `days / N`
- [x] Eliminare `find_active_period` (dead code: mai importata in produzione, usata solo nei test orfani)
- [x] Eliminare file `backend/app/utils/financial_math.py`
- [x] Eliminare file `backend/test_scripts/test_utilities/test_financial_math.py`
- [x] Aggiornare import in `test_asset_source.py` riga 41: `from backend.app.services.asset_source_providers.scheduled_investment import calculate_day_count_fraction`
- [x] Aggiornare import in `test_day_count_conventions.py` riga 19: stessa nuova location
- [x] In `test_runner.py`: rimuovere funzione `utils_financial_math` (righe 732-738) e entry dict `"financial-math"` (righe 2107-2113)
- [x] Verificare: `./dev.py test utils all` passa

---

### Blocco 1.5 — UPSERT + FK per AssetEvent (Design Decision D3)

**Status: ✅ COMPLETATO** (2026-04-03)

**File modificati:**
- `backend/app/db/models.py` — `AssetEvent.source_plugin_key` → `provider_assignment_id` FK
- `backend/alembic/versions/001_initial.py` — schema tabella `asset_events` aggiornato
- `backend/app/services/asset_source.py` — `bulk_assign_providers` refactored a UPSERT
- Test verificati: `test_asset_source.py`, `test_assets_provider.py`

#### §1.5.1 Refactor `bulk_assign_providers` → UPSERT
- [x] In `asset_source.py`, cambiata logica in `bulk_assign_providers`:
  - SELECT existing per `asset_id` → mappa `existing_map: Dict[int, AssetProviderAssignment]`
  - Se esiste → UPDATE (provider_code, identifier, identifier_type, provider_params, fetch_interval, user_url)
  - Se non esiste → INSERT
- [x] Preserva `asset_provider_assignments.id` attraverso le riconfigurazioni
- [x] Se il `provider_code` cambia, il backend fa UPDATE senza chiedere (modale di conferma per eventi orfani rimandata a Phase 7)

#### §1.5.2 Schema DB: `AssetEvent` FK
- [x] In `backend/app/db/models.py`, su `AssetEvent`:
  - Rimosso `source_plugin_key: Optional[str]`
  - Aggiunto `provider_assignment_id: Optional[int]` con FK a `asset_provider_assignments.id ON DELETE CASCADE`
  - Aggiunto indice `idx_asset_event_provider_assignment`
- [x] In `001_initial.py`: colonna `provider_assignment_id INTEGER` con `FOREIGN KEY ... ON DELETE CASCADE`

#### §1.5.3 Allineamento codice che usava `source_plugin_key`
- [x] `_upsert_asset_events` in `asset_source.py`: parametro `source_plugin_key: str` → `provider_assignment_id: Optional[int]`
- [x] Caller in `bulk_refresh_prices`: passa `prep["assignment"].id` invece della stringa `provider_code`
- [x] **Nota**: `source_plugin_key` su `PriceHistory` è un campo DIVERSO e resta invariato (traccia quale provider ha scaricato il prezzo)

#### §1.5.4 Verifiche
- [x] `./dev.py db create-clean --test` — OK
- [x] `./dev.py test db all` — 7/7 passed
- [x] `./dev.py test schemas all` — 4/4 passed
- [x] `./dev.py test services all` — 11/11 passed
- [x] `./dev.py test utils all` — 7/7 passed
- [x] `./dev.py test api assets-provider` — ✅ PASSED

#### Dettaglio cambiamenti §1.5 (per identifier nullable, incluso qui perché prerequisito)
- [x] `AssetProviderAssignment.identifier`: da `str = Field(nullable=False)` → `Optional[str] = Field(default=None, nullable=True)` — per AUTO_GENERATED che non ha bisogno di un identifier
- [x] `001_initial.py`: `asset_provider_assignments.identifier` rimosso `NOT NULL`
- [x] `bulk_assign_providers`: se `identifier_type == AUTO_GENERATED` e identifier è vuoto/None → lascia `None`

---

### Blocco 2 — Maturation Frequency nel motore + Late Interest frequency

**File da modificare:**
- `backend/app/schemas/assets.py` — aggiungere `maturation_frequency` a `FALateInterestConfig`
- `backend/app/services/asset_source_providers/scheduled_investment.py` — modificare `_generate_schedule_values` e `_compute_late_interest_value`
- `frontend/src/lib/components/assets/ScheduledInvestmentEditor.svelte` — serialize late `maturation_frequency`, filtro opzioni per durata periodo

**Concetto chiave:**
Il motore calcola giorno per giorno internamente (per correttezza, edge case dove maturation < periodo). Ma i **price points emessi** nel dict `values` seguono la `maturation_frequency`:
- `DAILY` → ogni giorno (comportamento attuale)
- `WEEKLY` → ogni 7 giorni dalla `period.start_date`
- `MONTHLY` → +1 mese (usa `dateutil.relativedelta`)
- `QUARTERLY` → +3 mesi
- `SEMIANNUAL` → +6 mesi
- `ANNUAL` → +12 mesi
- Sempre inclusi come ancoraggi: `period.start_date` e `period.end_date`

Il backward-fill del sistema prezzi DB copre i giorni senza price point.

Al confine tra periodi: il primo giorno del nuovo periodo si basa sull'ultimo valore maturato del precedente (la continuità è naturale perché `principal + total_interest + event_adjustment` è continuo).

**Dettaglio:**

#### §2.1 Schema: `maturation_frequency` su FALateInterestConfig
- [x] In `backend/app/schemas/assets.py`, aggiungere a `FALateInterestConfig`:
  ```python
  maturation_frequency: MaturationFrequency = Field(
      default=MaturationFrequency.DAILY,
      description="Maturation frequency for late interest period"
  )
  ```
- [x] Aggiornare docstring di `FALateInterestConfig`

#### §2.2 Motore: maturation dates in `_generate_schedule_values`
- [x] Importare `from dateutil.relativedelta import relativedelta` (`python-dateutil` già nel Pipfile)
- [x] Aggiungere helper `_compute_maturation_dates(start: date, end: date, frequency: MaturationFrequency) -> set[date]`:
  ```python
  def _compute_maturation_dates(start, end, frequency):
      """Compute all maturation dates within [start, end] for given frequency.
      Always includes start and end as anchors."""
      dates = {start, end}
      if frequency == MaturationFrequency.DAILY:
          # All days
          d = start
          while d <= end:
              dates.add(d)
              d += timedelta(days=1)
          return dates
      # Map frequency to relativedelta
      delta_map = {
          MaturationFrequency.WEEKLY: relativedelta(weeks=1),
          MaturationFrequency.MONTHLY: relativedelta(months=1),
          MaturationFrequency.QUARTERLY: relativedelta(months=3),
          MaturationFrequency.SEMIANNUAL: relativedelta(months=6),
          MaturationFrequency.ANNUAL: relativedelta(years=1),
      }
      delta = delta_map[frequency]
      d = start
      while d <= end:
          dates.add(d)
          d += delta
      return dates
  ```
- [x] In `_generate_schedule_values`, pre-calcolare maturation dates per tutti i periodi:
  ```python
  all_maturation_dates: set[date_type] = set()
  for p in schedule.schedule:
      all_maturation_dates |= _compute_maturation_dates(p.start_date, p.end_date, p.maturation_frequency)
  ```
- [x] Nel loop giornaliero, cambiare `values[current_date] = ...` a: salvare nel dict `values` **solo** se `current_date in all_maturation_dates`
- [x] Tutto il resto (calcolo interesse, event adjustment) rimane invariato — il calcolo è giorno per giorno, ma l'emissione è selettiva

#### §2.3 Motore: late interest con maturation frequency + ottimizzazione (D9)
- [x] Riscrivere `_compute_late_interest_value` per usare la **formula di salto** invece di iterare dall'inizio:
  - **Input**: `schedule`, `target_date`, `last_scheduled_value`, `maturity_date`
  - **SIMPLE grace**: `V = last_scheduled_value + principal * grace_rate * frac(maturity→min(target, grace_end))`
  - **SIMPLE late**: `V_grace + principal * late_rate * frac(grace_end→target)`
  - **COMPOUND grace**: `V = last_scheduled_value`; poi day-by-day **solo** dal `max(maturity+1, request_start)` al `min(grace_end, target)` (non dall'inizio se non serve)
  - **COMPOUND late**: stessa ottimizzazione — calcolare il valore base al punto di partenza del sotto-periodo con formula closed-form (`V_base * (1+r*Δt)^N`), poi day-by-day solo per il range residuo
- [x] Il caller in `get_history_value` per il range post-maturity:
  - Calcola le maturation dates del late interest con `_compute_maturation_dates(maturity_date + 1 day, request_end_date, schedule.late_interest.maturation_frequency)`
  - Per ogni maturation date nel range, chiama `_compute_late_interest_value` e emette un `FAPricePoint`
  - NON emette per tutti i giorni — solo le maturation dates

#### §2.4 `get_history_value`: emissione selettiva
- [x] Modificare `get_history_value` per emettere solo i price points presenti nel dict `values` filtrati per `[start_date, end_date]`:
  ```python
  for d in sorted(cached.keys()):
      if start_date <= d <= end_date:
          prices.append(FAPricePoint(date=d, close=cached[d], currency=currency))
  ```
- [x] Per il range post-maturity: stessa logica con maturation dates del late interest

#### §2.5 Frontend: serialize late `maturation_frequency`
- [x] In `ScheduledInvestmentEditor.svelte` funzione `serialize()` (riga 320), aggiungere al `late_interest` JSON:
  ```javascript
  maturation_frequency: lr.maturation_frequency,
  ```

#### §2.6 Frontend: filtro opzioni maturation frequency per durata periodo
- [x] Per ogni riga della DataTable, filtrare `MATURATION_FREQ_OPTIONS` in base a `daysBetween(row.start_date, row.end_date)`:
  - `DAILY` → sempre
  - `WEEKLY` → ≥ 7 giorni
  - `MONTHLY` → ≥ 28 giorni
  - `QUARTERLY` → ≥ 90 giorni
  - `SEMIANNUAL` → ≥ 180 giorni
  - `ANNUAL` → ≥ 365 giorni
- [x] Se resize del periodo invalida la scelta corrente → fallback a `DAILY`
- [x] Per la riga late interest: tutte le opzioni sono sempre disponibili (range infinito)

#### §2.7 Verifiche
- [x] `./dev.py test services synthetic-yield` passa
- [x] `./dev.py test services synthetic-yield-integration` passa
- [x] `./dev.py front check && ./dev.py front build --debug` passa

---

### Blocco 3 — Flag `generate_interest` + auto-generazione eventi + MATURITY_SETTLEMENT

**Prerequisito**: Blocco 3.0 — Rimozione UniqueConstraint (D7)

**File da modificare:**
- `backend/app/db/models.py` — rimuovere UniqueConstraint, aggiungere `MATURITY_SETTLEMENT` a enum
- `backend/alembic/versions/001_initial.py` — rimuovere UNIQUE constraint
- `backend/app/schemas/assets.py` — aggiungere `generate_interest` a `FAInterestRatePeriod` e `FALateInterestConfig`
- `backend/app/services/asset_source_providers/scheduled_investment.py` — logica auto-generazione + cache tupla + settlement
- `frontend/src/lib/components/assets/ScheduledInvestmentEditor.svelte` — toggle UI + serialize/deserialize

**Concetto chiave (da Design Decisions D1, D2, D4, D5, D6, D8):**

Quando `generate_interest=True` su un periodo, ad ogni maturation date il motore:
1. Calcola `interest_amount = current_value - initial_value` (dove `current_value = principal + total_interest + event_adjustment`)
2. Se `interest_amount > 0` (cedola solo positiva — se negativa per price adjustment, non si genera):
   - Genera un `FAAssetEventPoint(type="INTEREST", value=Currency(code=currency, amount=interest_amount))`
   - Applica: `event_adjustment -= interest_amount` (stacca l'interesse)
   - Resetta: `total_interest = Decimal("0")` (compound riparte da `initial_value`)
3. Il prezzo post-stacco torna a `initial_value` (il reset è totale: interest + adjustments entrano nella cedola). Dopo il reset, il loop giornaliero successivo calcola l'interesse compound sulla base `principal + total_interest` dove `total_interest = 0` → base = `principal` = `initial_value`. Questo è matematicamente corretto: il compound riparte dal nominale.

**Ordine operazioni nel loop (D8):**
1. Calcolo interesse giornaliero
2. Se maturation date + `generate_interest` → stacco cedola (evento a "mezzanotte e 1 min" del giorno)
3. Applicazione eventi manuali del giorno (INTEREST, PRICE_ADJUSTMENT dal config)
4. Scrittura valore nel dict (solo se maturation date)

**Cache tupla (D5):** `_generate_schedule_values` restituisce `(dict[date, Decimal], list[FAAssetEventPoint])`. La cache salva la tupla intera. Auto_events sono deterministici — cachearli insieme è più efficiente.

**MATURITY_SETTLEMENT (D6):** Quando `generate_interest=True` sull'ultimo periodo (o su late interest), al termine del calcolo il motore genera un evento `MATURITY_SETTLEMENT` con `value = initial_value`. Dopo questo evento il motore non produce più price points — l'asset è "chiuso". In Phase 7, questo dovrebbe coincidere con un SELL 100%.

Gli eventi auto-generati si **sommano** a quelli manuali se cadono sulla stessa data (D4 + D7: no UniqueConstraint).

In futuro: colonna apposita per policy di generazione più fini (tasso cedola custom, cedola parziale, etc.).

**Dettaglio:**

#### §3.0 Prerequisito: rimozione UniqueConstraint (D7)
- [x] In `backend/app/db/models.py`, rimuovere `UniqueConstraint("asset_id", "date", "type", name="uq_asset_event_asset_date_type")` da `AssetEvent.__table_args__`
- [x] In `backend/alembic/versions/001_initial.py`, rimuovere `CONSTRAINT uq_asset_event_asset_date_type UNIQUE (asset_id, date, type)` dalla CREATE TABLE `asset_events`
- [x] Mantenere gli indici `idx_asset_event_asset_date` e `idx_asset_event_asset_type_date` per performance
- [x] `./dev.py db create-clean --test`

#### §3.0a Fix `_upsert_asset_events` per coesistenza auto/manuali (conseguenza D7)
- [x] In `backend/app/services/asset_source.py`, nella funzione `_upsert_asset_events` (~riga 1197), il DELETE deve filtrare anche per `provider_assignment_id`:
  ```python
  # PRIMA (cancella TUTTI gli eventi su quella date/type — anche manuali!):
  del_stmt = delete(AssetEvent).where(and_(
      AssetEvent.asset_id == asset_id,
      AssetEvent.date == evt_date,
      AssetEvent.type == evt_type,
  ))
  # DOPO (cancella solo gli eventi dello STESSO provider — manuali sopravvivono):
  del_stmt = delete(AssetEvent).where(and_(
      AssetEvent.asset_id == asset_id,
      AssetEvent.date == evt_date,
      AssetEvent.type == evt_type,
      AssetEvent.provider_assignment_id == provider_assignment_id,
  ))
  ```
  **Nota**: quando `provider_assignment_id=None` (evento manuale), `== None` in SQLAlchemy genera `IS NULL` — il comportamento è corretto per entrambi i casi.

#### §3.0b Aggiungere `MATURITY_SETTLEMENT` a `AssetEventType` (D6)
- [x] In `backend/app/db/models.py`, aggiungere all'enum `AssetEventType`:
  ```python
  MATURITY_SETTLEMENT = "MATURITY_SETTLEMENT"
  ```
- [x] Aggiornare docstring dell'enum con la descrizione: "Asset reaches maturity — final capital return, no further calculations"
- [x] `./dev.py api sync` per aggiornare i tipi TypeScript generati

#### §3.1 Schema
- [x] In `backend/app/schemas/assets.py`, aggiungere a `FAInterestRatePeriod`:
  ```python
  generate_interest: bool = Field(
      default=False,
      description="Auto-generate INTEREST events at each maturation date. "
                  "Event value = asset_value - initial_value (resets price to initial_value). "
                  "Only generated if positive (no negative coupons)."
  )
  ```
- [x] In `backend/app/schemas/assets.py`, aggiungere a `FALateInterestConfig`:
  ```python
  generate_interest: bool = Field(
      default=False,
      description="Auto-generate INTEREST events at each late maturation date, "
                  "plus a MATURITY_SETTLEMENT event at the end. "
                  "After settlement, the asset produces no further price points."
  )
  ```
- [x] Aggiornare docstring ed esempio JSON di entrambi

#### §3.2 Motore: cache tupla + auto-generazione in `_generate_schedule_values` (D5, D8)
- [x] Cambiare return type: `def _generate_schedule_values(schedule) -> tuple[dict[date, Decimal], list[FAAssetEventPoint]]`
- [x] Aggiornare la cache per salvare la tupla `(values, auto_events)`
- [x] Aggiungere lista `auto_events: list[FAAssetEventPoint] = []` nel motore
- [x] Nel loop giornaliero, seguire l'ordine D8:
  ```python
  # 1. Calcolo interesse giornaliero (già esistente)

  # 2. Auto-stacco cedola (se maturation date + generate_interest)
  if current_date in all_maturation_dates and period and period.generate_interest:
      current_value = principal + total_interest + event_adjustment
      interest_amount = current_value - principal
      if interest_amount > 0:  # cedola solo positiva
          auto_evt = FAAssetEventPoint(
              date=current_date,
              type="INTEREST",
              value=Currency(code=schedule.initial_value.code, amount=interest_amount),
              notes="Auto-generated interest payout"
          )
          auto_events.append(auto_evt)
          event_adjustment -= interest_amount
          total_interest = Decimal("0")

  # 3. Applicazione eventi manuali del giorno (già esistente)

  # 4. Scrittura valore (solo se maturation date)
  if current_date in all_maturation_dates:
      values[current_date] = principal + total_interest + event_adjustment
  ```
- [x] Aggiornare tutti i caller di `_generate_schedule_values` per destrutturare la tupla:
  ```python
  cached_values, cached_events = _generate_schedule_values(schedule)
  ```
- [x] **Attenzione compound**: dopo il reset, il loop successivo usa `base = principal + total_interest` dove `total_interest = 0` → base = `principal` = `initial_value`. Matematicamente corretto.

#### §3.2b MATURITY_SETTLEMENT alla fine dello schedule (D6)
- [x] Dopo il loop principale, se l'ultimo periodo ha `generate_interest=True` E non c'è late interest:
  ```python
  # Settlement: asset closes at end of last period
  # Value = residual asset value (principal + remaining interest + adjustments)
  settlement_value = values.get(last_end, principal)
  auto_events.append(FAAssetEventPoint(
      date=last_end,
      type="MATURITY_SETTLEMENT",
      value=Currency(code=schedule.initial_value.code, amount=settlement_value),
      notes="Maturity settlement — asset closed"
  ))
  ```
- [x] Se c'è late interest con `generate_interest=True`, il settlement avviene nell'ultimo price point del late interest (gestito in `get_history_value`)
- [x] Dopo MATURITY_SETTLEMENT, il motore NON produce ulteriori price points. In `get_history_value` e `get_current_value`: se `target_date > settlement_date`, restituire il settlement value senza ulteriori calcoli.
- [x] **Nota**: il valore del settlement è il residuo dell'asset. Se `generate_interest=True` ha già staccato tutte le cedole, il residuo sarà ≈ `initial_value`. Se ci sono PRICE_ADJUSTMENT non staccati, il residuo li include. L'utente può eventualmente modificare manualmente l'evento di settlement verso il basso — la differenza è una perdita non rimborsata.

#### §3.3 Motore: emettere auto_events in `get_history_value`
- [x] In `get_history_value`, destrutturare la cache: `cached_values, cached_events = _generate_schedule_values(schedule)`
- [x] Dopo aver costruito i `prices`, mergiare cached_events con i manuali:
  ```python
  # Merge cached auto-events + manual events, filtered to range
  all_events = [e for e in cached_events if start_date <= e.date <= end_date]
  all_events += [e for e in schedule.asset_events if start_date <= e.date <= end_date]
  all_events.sort(key=lambda e: e.date)
  ```
- [x] Per il late interest con `generate_interest=True`: generare auto_events anche nel range post-maturity (non cachati — calcolati on-demand in `get_history_value`)
- [x] Se late interest ha `generate_interest=True`, aggiungere MATURITY_SETTLEMENT all'ultima maturation date del late interest

#### §3.4 Frontend: toggle `generate_interest` in ScheduledInvestmentEditor
- [x] Aggiungere `generate_interest: boolean` all'interfaccia `ScheduleRow` (riga 55)
- [x] Nella colonna maturation_frequency della DataTable, aggiungere un toggle/icona inline (es: 📤) per `generate_interest`. Quando attivo, indica che alla maturation il sistema genera automaticamente l'evento di stacco interesse.
  - Implementazione: nella definizione `columns`, o aggiungere una 4ª colonna dedicata (piccola, solo toggle), o come icon-button inline accanto al select di frequenza
- [x] `serialize()`: aggiungere `generate_interest: r.generate_interest` nel mapping periodi
- [x] `serialize()`: aggiungere `generate_interest: lr.generate_interest ?? false` nel late_interest JSON
- [x] `deserializeRows()`: leggere `p.generate_interest ?? false`
- [x] `handleAddPeriod()`: default `generate_interest: false`
- [x] Traduzione: `./dev.py i18n add "assets.schedule.generateInterest" --en "Auto-payout" --it "Stacco auto" --fr "Paiement auto" --es "Pago auto"`

#### §3.5 Verifiche
- [x] Test sintetico: schedule con `generate_interest=True`, MONTHLY, 1 anno → 12 eventi auto-generati, prezzo che torna a initial_value ogni mese
- [x] Test sintetico: schedule con `generate_interest=True` + COMPOUND → dopo stacco, compound riparte da initial_value (non da valore accumulato)
- [x] Test sintetico: schedule con `generate_interest=True` + PRICE_ADJUSTMENT negativo che porta valore sotto initial_value → nessun evento generato (cedola solo positiva)
- [x] Test sintetico: schedule con `generate_interest=True` sull'ultimo periodo senza late → genera MATURITY_SETTLEMENT all'end_date con value = valore residuo
- [x] Test sintetico: late interest con `generate_interest=True` → genera MATURITY_SETTLEMENT + INTEREST periodici
- [x] Test sintetico: auto INTEREST + manuale INTEREST sulla stessa data → entrambi coesistono nel DB (UniqueConstraint rimosso)
- [x] Test sintetico: `get_current_value` chiamato **dopo** la data di MATURITY_SETTLEMENT → restituisce il settlement value, senza calcoli ulteriori (motore "spento")
- [x] Test sintetico: `_upsert_asset_events` con auto-eventi non cancella eventi manuali sulla stessa (date, type)
- [x] `./dev.py test services synthetic-yield` passa
- [x] `./dev.py front check && ./dev.py front build --debug` passa

---

### Blocco 4 — Fix critici frontend: save + test button + identifier + UX polish

**Status: ✅ COMPLETATO**

**File da modificare:**
- `frontend/src/lib/components/assets/AssetModal.svelte` — fix `hasProvider`
- `frontend/src/lib/components/assets/ProviderAssignmentSection.svelte` — fix test button + computedParams
- `frontend/src/lib/components/assets/ScheduledInvestmentEditor.svelte` — UX polish (componenti custom, layout, icone, tooltip, bulk events)

#### §4.1 Fix `hasProvider` in AssetModal.svelte
- [x] Riga 172, cambiare:
  ```javascript
  // PRIMA:
  let hasProvider = $derived(!providerNoProvider && providerCode !== '' && providerIdentifier !== '');
  // DOPO:
  let hasProvider = $derived(!providerNoProvider && providerCode !== '' && (providerIdentifier !== '' || providerIdentifierType === 'AUTO_GENERATED'));
  ```

#### §4.2 Fix `identifier` nullable nel backend
- [x] **COMPLETATO in Blocco 1.5** — `models.py`, `001_initial.py`, `bulk_assign_providers` tutti aggiornati
- [x] `./dev.py db create-clean --test` — verificato

#### §4.3 Fix test button in ProviderAssignmentSection.svelte
- [x] Riga 620: cambiare disabled condition:
  ```javascript
  // PRIMA:
  disabled={!providerCode || !identifier || testStatus === 'testing' || disabled}
  // DOPO:
  disabled={!providerCode || (!identifier && !isAutoGenerated) || testStatus === 'testing' || disabled}
  ```
- [x] Riga 291: cambiare computedParams per scheduled_investment:
  ```javascript
  // PRIMA:
  const computedParams = paramsSchema.length > 0 ? {...paramsValues} : null;
  // DOPO:
  const computedParams = uiComponent === 'scheduled_investment' ? providerParams : (paramsSchema.length > 0 ? {...paramsValues} : null);
  ```

#### §4.4 Asset Events: componenti custom + bulk delete + responsive
- [x] **Date**: sostituire `<input type="date">` con `SingleDatePicker` (importarlo, prop `allowFuture={true}` per date future, `compact={true}`)
- [x] **Type**: sostituire `<select>` nativo con `SimpleSelect` (già importato, usare `EVENT_TYPE_OPTIONS` con label da i18n)
- [x] **Currency evento**: aggiungere `CurrencySearchSelect` accanto al campo value (come nel blocco initial_value)
- [x] **Bulk delete eventi**: aggiungere stato `selectedEventIds: string[]`, checkbox per selezione evento, toolbar bulk (come per i periodi) con pulsante delete + conferma. La toolbar compare accanto a "Add Event" quando ci sono eventi selezionati.
- [x] **Responsive "Add Event"**: la label deve avere `class="hidden sm:inline"` per nasconderla in mobile (come per "Add Period")

#### §4.5 Layout colonne DataTable
- [x] Equilibrare le 3 colonne (Period, Rate, Maturation Frequency): rimuovere `width` fissi e usare distribuzione uguale. Actions e Selection restano di dimensione fissa.
  ```javascript
  // Per tutte e 3 le colonne:
  width: undefined,  // rimuovere o commentare
  minWidth: 100,
  // Il DataTable gestirà la distribuzione equa
  ```

#### §4.6 Icone maturation frequency
- [x] Aggiungere emoji a `MATURATION_FREQ_OPTIONS`:
  ```javascript
  {value: 'DAILY', label: `🕐 ${$t('assets.schedule.matFreqDaily')}`},
  {value: 'WEEKLY', label: `📅 ${$t('assets.schedule.matFreqWeekly')}`},
  {value: 'MONTHLY', label: `📆 ${$t('assets.schedule.matFreqMonthly')}`},
  {value: 'QUARTERLY', label: `📊 ${$t('assets.schedule.matFreqQuarterly')}`},
  {value: 'SEMIANNUAL', label: `📈 ${$t('assets.schedule.matFreqSemiannual')}`},
  {value: 'ANNUAL', label: `🗓️ ${$t('assets.schedule.matFreqAnnual')}`},
  ```

#### §4.7 CurrencySearchSelect altezza
- [x] Nel blocco initial_value (riga 960-969): allineare l'altezza del `CurrencySearchSelect` a quella dell'input numerico adiacente. Il wrapper div può avere una classe che forza l'altezza uguale.

#### §4.8 Day Count & Interest Type tooltip
- [x] Aggiungere icona ℹ️ cliccabile accanto al label "📆 Day Count" con tooltip che spiega "Applies to all schedule periods" + link a `/mkdocs/financial-theory/day-count/` (stesso pattern del `headerTooltipUrl` nelle colonne DataTable)
- [x] Stesso pattern per "📐 Interest Type" con link a docs

#### §4.9 Step valore iniziale
- [x] Verificare che `step="100"` sull'input numerico funzioni correttamente (non mostri incrementi di 0.01 col browser)

#### §4.10 Traduzioni
- [x] `./dev.py i18n search "assets.schedule"` — verificare chiavi esistenti
- [x] `./dev.py i18n audit` — identificare chiavi orfane
- [x] Rimuovere chiavi obsolete: `./dev.py i18n remove "assets.schedule.compounding"`, `"assets.schedule.compFreq"`, `"assets.schedule.freqHint"`, `"assets.schedule.compoundingHint"`, `"assets.schedule.dayCountHint"` (se sostituita da tooltip)
- [x] Aggiungere nuove chiavi mancanti (se non già presenti):
  - `assets.schedule.generateInterest` — "Auto-payout" / "Stacco auto" / "Paiement auto" / "Pago auto"
  - `assets.schedule.generateInterestHint` — tooltip per il toggle
  - `assets.schedule.dayCountTooltip` — tooltip per day count globale
  - `assets.schedule.interestTypeTooltip` — tooltip per interest type globale

#### §4.11 Verifiche
- [x] `./dev.py front check` → 0 errori
- [x] `./dev.py front build --debug` → OK
- [x] `./dev.py test all` → tutti verdi

---

### Blocco 5 — Note architetturali Phase 7 + documentazione

**File da modificare:**
- `LibreFolio_developer_journal/RoadmapV4_UI/plan-phase06Assets.prompt.md` — annotazioni
- `TODO_FUTURI.md` — decisioni architetturali

#### §5.1 Annotare nel piano principale (plan-phase06Assets.prompt.md)
- [x] Nello step di documentazione, aggiungere:
  - `scheduled-investment.en.md` da aggiornare con: `interest_type`/`day_count` globali, formato `initial_value` Currency, `generate_interest` flag, `maturation_frequency` su late interest, sezione eventi auto-generati, maturation frequency nei price points
  - Nota su **auto-sync alla creazione**: alla creazione dell'asset con `scheduled_investment`, il frontend richiede sync su tutto il range schedule (dall'inizio alla fine o almeno fino a oggi), non solo today
  - Nota su **riconfigurazione**: alla modifica del provider `scheduled_investment`, il frontend deve prima eliminare tutti i prezzi/eventi precedenti e poi ri-sincronizzare
  - Verificare docs `day-count` aggiornati con le 4 convenzioni

#### §5.2 Annotare in TODO_FUTURI.md
- [x] **Phase 7 — Collegamento evento→transazione**:
  - Aggiungere campo `asset_event_id: Optional[int] = Field(default=None, foreign_key="asset_events.id")` su `Transaction`
  - Tipo DIVIDEND/INTEREST nella transaction collega all'evento asset auto-generato
  - Il FK `Transaction.asset_event_id` blocca il CASCADE delete su `AssetEvent` quando ci sono transazioni collegate → il backend ritorna errore 409 Conflict
  - Frontend mostra modale "Alcuni eventi hanno transazioni collegate" con opzioni: migrazione date, scollegamento (SET NULL su transaction.asset_event_id), o annullamento
  - Gli eventi manuali (tabella "Asset Events" nel frontend, `provider_assignment_id=NULL`) servono per eventi un-planned
  - Gli eventi auto-generati (`provider_assignment_id` non-NULL, da `generate_interest=True`) sono planned e ricreabili deterministicamente
  - **MATURITY_SETTLEMENT** → al momento del settlement, il frontend suggerisce la creazione di una transazione SELL 100% (o del residuo). Se l'utente ha transazioni INTEREST auto-generate, il settlement chiude il ciclo.
- [x] **Phase 7 — Modale cambio provider**:
  - Quando l'utente cambia provider su un asset che ha eventi auto-generati (provider_assignment_id non-NULL):
    1. Frontend mostra modale: "Ci sono N eventi generati dalla configurazione attuale"
    2. Opzione A: "Elimina tutto" → procedi con DELETE assignment (CASCADE elimina eventi)
    3. Opzione B: "Mantieni come manuali" → UPDATE asset_events SET provider_assignment_id=NULL, poi DELETE assignment
    4. Opzione C: "Annulla"
  - Se ci sono transazioni collegate (Phase 7+), l'opzione A è bloccata → mostrare dettaglio transazioni da scollegare prima
- [x] **Futura policy cedola**:
  - Colonna `coupon_policy` su `FAInterestRatePeriod` con opzioni: FULL_RESET (attuale, torna a initial_value), CUSTOM_RATE (tasso cedola diverso dal tasso di accumulo), PARTIAL (percentuale del valore accumulato)
  - Per ora solo FULL_RESET è implementato
- [x] **Late interest generate_interest**:
  - Il late interest ora supporta `generate_interest=True`. Genera INTEREST periodici + MATURITY_SETTLEMENT finale.
  - Il late interest NON è una "opportunità" ma una penale — tuttavia il flag unifica il pattern: l'utente decide se auto-generare eventi o meno, indipendentemente dalla natura del tasso.
  - Documentare che se l'utente non vuole auto-generare eventi di penale, lascia `generate_interest=False` sul late interest e usa eventi manuali.

---

## Ordine di esecuzione raccomandato

1. ~~**Blocco 1.5** — UPSERT + FK AssetEvent~~ ✅ COMPLETATO (2026-04-03)
   - Include: UPSERT `bulk_assign_providers`, FK `provider_assignment_id`, `identifier` nullable, indici
   - Verificato: DB create-clean, DB all 7/7, Schemas 4/4, Services 11/11, Utils 7/7, API Provider ✅
2. **Blocco 1** — Backend cleanup (`financial_math.py` → `scheduled_investment.py`)
3. **Blocco 4 §4.1, §4.3** — Fix critici frontend save/test (sbloccano il testing manuale)
4. **Blocco 3 §3.0** — Rimozione UniqueConstraint + MATURITY_SETTLEMENT enum (prerequisito feature)
5. **Blocco 2** — Maturation frequency engine (cuore del round)
6. **Blocco 3 §3.1-§3.5** — generate_interest flag + cache tupla + auto-eventi + settlement (dipende da Blocco 2)
7. **Blocco 4 §4.4-§4.10** — UX polish (può essere parallelizzato)
8. **Blocco 5** — Documentazione (ultimo)

## Validation Checklist

### Backend
- [ ] `./dev.py test utils all` — day count tests passano con nuovo import (dopo Blocco 1)
- [x] `./dev.py test services all` — 11/11 passed (verificato Blocco 1.5)
- [x] `./dev.py test schemas all` — 4/4 passed (verificato Blocco 1.5)
- [x] `./dev.py test api assets-provider` — ✅ PASSED (verificato Blocco 1.5)
- [ ] `./dev.py test api all` — provider probe funziona per scheduled_investment (dopo fix frontend §4.1/§4.3)
- [ ] `./dev.py test db all` — dopo rimozione UniqueConstraint (§3.0)

### Frontend
- [ ] `./dev.py front check` → 0 errori, 0 warning
- [ ] `./dev.py front build --debug` → OK
- [ ] Manuale: creare asset con scheduled_investment → save funziona, provider assegnato
- [ ] Manuale: Test Configuration → probe ritorna current_price + history
- [ ] Manuale: chart preview mostra valori con step alle maturation dates
- [ ] Manuale: `generate_interest=true` → chart mostra denti di sega (interesse accumulato → stacco → torna a initial_value)
- [ ] Manuale: late interest con maturation frequency diversa da DAILY → funziona
- [ ] Manuale: COMPOUND + generate_interest → dopo stacco il compound riparte da initial_value
- [ ] Manuale: MATURITY_SETTLEMENT visibile come ultimo evento su asset chiuso

### Full suite
- [ ] `./dev.py test all` → 🎉 ALL TESTS PASSED

