# LibreFolio - Roadmap to Public Release v3.0

**Data Creazione**: 18 Dicembre 2025  
**Versione**: 3.0 (Nomenclatura Pulita)  
**Target Release**: Fine Gennaio / Inizio Febbraio 2025

---

## 📊 Stato Attuale (Dicembre 2025)

### ✅ Completati (Phase 0-2)

| Phase       | Descrizione                                                            | Data     | Status |
|-------------|------------------------------------------------------------------------|----------|--------|
| **Phase 0** | Database Schema (9 tabelle, migrations, constraints)                   | Oct 2025 | ✅ 100% |
| **Phase 1** | FX Multi-Provider (ECB, FED, BOE, SNB, fallback, backward-fill)        | Nov 2025 | ✅ 100% |
| **Phase 2** | Asset Providers (yfinance, JustETF, CSS Scraper, Scheduled Investment) | Dec 2025 | ✅ 100% |

**Metriche Attuali**:

- Endpoints API: 35 operativi
- Test Coverage: 6/6 categorie passano (External, DB, Utils, Services, API, E2E)
- Schema Models: 54+ Pydantic con Currency class ISO 4217 + crypto
- Documentazione: mkdocs + developer guides

---

## 🚀 Fasi Rimanenti

### Phase 3, 4 e 5

Guarda brain storming e piano implementativo in [01_brainstorming_datamodel.md](01_brainstorming_datamodel.md)

---

### Phase 6: Runtime Analysis (5-7 giorni)

**Obiettivo**: FIFO matching completo e metriche performance.

#### 6.1 Deduzione Tipo Valutazione

Il tipo di valutazione si deduce da `asset_provider_assignments`:

- `provider_code = 'scheduled_investment'` → Calcolo synthetic yield (principal + accrued)
- `provider_code in ['yfinance', 'justetf', 'cssscraper']` → Usa price_history con forward-fill
- Nessun provider assegnato → Fallback a prezzo unitario acquisto

#### 6.2 FIFO Matching Engine

- Costruisce coda BUY lots con pro-rata fees/taxes in costo unitario
- Consuma FIFO su SELL/REMOVE_HOLDING/TRANSFER_OUT
- Calcola P/L realizzato con matching virtuale
- Output opzionale `matches` per trasparenza

#### 6.3 Series Computation

- **Invested**: cumulative BUY outflows (fees/taxes incluse)
- **Market Value**: valutazione giornaliera secondo provider type
- Conversione FX a base currency (riusa Phase 1)

#### 6.4 KPIs

- Simple ROI, Duration-Weighted ROI

#### 6.5 API

- `GET /analysis/asset/{asset_id}?broker_id=&start=&end=`

---

### Phase 7: Portfolio Aggregations (2-3 giorni)

**Obiettivo**: Aggregazioni portfolio-level per dashboard.

- `GET /portfolio/overview?start=&end=&broker_id=&asset_type=` - Series aggregate + KPIs + cash totals
- `GET /portfolio/allocation?date=&dimension=asset|broker|asset_type` - Breakdown

---

### Phase 8: Infrastructure (2-3 giorni)

**Obiettivo**: Automazione e sicurezza.

#### 8.1 Scheduler (APScheduler)

- Jobs: `refresh_recent_prices`, `daily_fx_sync`
- Future: `gc_broker_reports` per cleanup file vecchi
- `POST /tasks/run?name=<job>` trigger manuale

#### 8.2 Authentication

- `POST /auth/login` - Cookie session (HttpOnly, Secure, SameSite)
- `POST /auth/logout` - Clear cookie
- Middleware per proteggere `/api/*`
- Password hashing bcrypt

---

### Phase 9: Frontend (10-12 giorni)

**Obiettivo**: UI completa SvelteKit + Tailwind + Skeleton UI.

#### 9.1 Scaffold

- Layout sidebar + main content
- i18n: en/it/fr/es
- Login page con session

#### 9.2 Pages

- **Dashboard**: Overview + KPI cards + dual-line chart (Invested vs Market)
- **Brokers**: List + detail + cash modals
- **Assets**: List + detail + price chart + FIFO analysis
- **Transactions**: Forms + Import upload
- **Settings**: Configurazione utente

#### Principio: **Calcoli sempre dal backend**, frontend solo presentazione.

---

### Phase 10: Deploy (2-3 giorni)

**Obiettivo**: Single Docker image.

- Multi-stage Dockerfile (Node → Python)
- Frontend static served via FastAPI
- TLS auto/manual
- Volume `./data`
- README + docs in inglese

---

## 📅 Timeline

| Phase                        | Giorni | Cumulativo  |
|------------------------------|--------|-------------|
| 3 - Users, Settings, Brokers | 3-4    | ~0.5 sett   |
| 4 - Transactions & Cash      | 5-6    | ~1.5 sett   |
| 5 - Import Plugin System     | 4-5    | ~2.5 sett   |
| 6 - Runtime Analysis         | 5-7    | ~3.5 sett   |
| 7 - Portfolio Aggregations   | 2-3    | ~4 sett     |
| 8 - Infrastructure           | 2-3    | ~4.5 sett   |
| 9 - Frontend                 | 10-12  | ~6.5 sett   |
| 10 - Deploy & Docs           | 2-3    | **~7 sett** |

---

## 🔧 Note Architetturali Chiave

### Valutazione Asset = Provider Assignment

Non esiste attributo `valuation_model` sull'asset. Il comportamento si deduce dalla tabella `asset_provider_assignments`:

- Provider `scheduled_investment` → calcolo yield
- Provider `yfinance`/`justetf` → market price
- Nessun provider → manual/fallback

### Broker Multi-Utente

Tabella `broker_user_access` permette:

- Un broker visibile a più utenti (famiglia)
- Access levels differenziati (OWNER/VIEWER)
- Query filtrate automaticamente per utente

### Import Atomico

File di transazioni: **tutto o niente**

- Validazione completa prima di commit
- Oversell check su tutte le righe
- Rollback totale se anche una riga fallisce

---

## ✅ Principi

1. **Breaking changes OK** - Progetto embrionale
2. **Test-first** - Coverage completo
3. **Backend-first** - Calcoli server-side
4. **Plugin architecture** - Estensibilità
5. **Atomic operations** - No stato inconsistente

