# TODO Prossime Attività

Backlog azionabile e ordinato per complessità (facile → complesso), con impatto utente finale stimato.

- **Relazione con gli altri file**: `TODO_FUTURI.md` resta l'archivio raw delle idee (contesto estenso, cronologico). `TODO_Completati.md` resta lo storico di ciò che è fatto/scartato. Questo file è il **backlog curato**: per le voci con spec completa qui sotto, il contenuto è stato rimosso da `TODO_FUTURI.md` per evitare doppioni (di norma solo il titolo/idea resta lì se serve contesto storico). Per le voci "solo indice", il dettaglio estenso resta in `TODO_FUTURI.md` — qui c'è solo la sintesi + priorità.
- **Cx** = complessità stimata (XS/S/M/L/XL). **Imp** = impatto per l'utente finale (Nullo/Basso/Medio/Alto).
- Quando una voce è completata, va spostata in `TODO_Completati.md`.

---

## 🔴 PRIORITÀ ALTA — fuori dall'ordinamento per complessità

### 0. 💸 BRIM: FEE/TAX non collegati all'asset — verifica e consolidamento — Cx: M/L — Imp: **Alto** (correttezza dati fiscali/cost basis)

**Bug confermato** (non solo idea) — dettaglio completo in `TODO_FUTURI.md`. Riassunto:

- **Directa**: confermato con export reale dell'utente — righe `Rit.cedola obb.` (TAX) hanno ISIN/ticker identici alla riga di acquisto originale, ma `broker_directa.py:306-312` esclude esplicitamente FEE/TAX dalla risoluzione asset → `asset_id` resta sempre `NULL` anche quando risolvibile
- Stesso pattern (bug) confermato anche in `broker_etoro.py`, `broker_finpension.py`, `broker_freetrade.py`, `broker_revolut.py`, `broker_schwab.py`, `broker_trading212.py` (7 plugin su 11)
- 4 plugin già corretti, da usare come riferimento per il fix: `broker_ibkr.py`, `broker_coinbase.py` (riusano l'`asset_id` della riga trade genitrice), `broker_degiro.py` (mappa tipo→`requires_asset` già case-by-case — il pattern più maturo), `broker_generic_csv.py` (collega se il CSV sorgente fornisce l'asset — gap qui potrebbe essere dati utente, non bug, da verificare a parte)
- **Gap di calcolo separato dal gap di dati**: anche quando `asset_id` è già corretto, il Portfolio Engine (`portfolio_service.py:1698-1700`) già lo attribuisce correttamente alla posizione — ma il **motore FIFO/Lotti** (`fifo_utils.py`, `_HOLDING_TYPES = {BUY, SELL}`) lo ignora sempre, non impatta mai il cost basis/WAC del lotto

**Target definito dall'utente**: 2 fasi — (1) fix import per collegare l'asset quando risolvibile dal broker, (2) se l'asset è dichiarato → il costo entra nella FIFO/analisi lotti (cost basis del lotto); se non è dichiarato → resta costo generico di broker nel Portfolio Engine (comportamento già corretto oggi per quel ramo).

⚠️ **Nessun codice da toccare finché non c'è un piano dedicato** — richiesta esplicita dell'utente, questa voce è solo tracciamento.

---

## 🎯 Task con spec completa (discussi 17 Luglio 2026)

### 1. 🧹 Rimuovere endpoint `/countries/normalize` — Cx: XS — Imp: Nullo

Scartato come feature user-facing (vedi `TODO_Completati.md`), ma l'endpoint HTTP resta morto nel codice. Cleanup:

- Rimuovere la route `GET /countries/normalize` da `backend/app/api/v1/utilities.py` (righe ~42-91)
- Rimuovere `CountryNormalizationResponse` da `backend/app/schemas/utilities.py` se non usato altrove
- Rimuovere il test dedicato in `backend/test_scripts/test_api/test_utilities.py` (**non** toccare `test_geo_utils.py::test_normalize_country_to_iso3` — quella testa la funzione sottostante, ancora usata da `justetf.py`)
- **Non rimuovere** `normalize_country_to_iso3()` in `geo_utils.py` — resta in uso interno
- Rigenerare client FE: `./dev.py api sync`

---

### 2. ⚙️ Default lang/currency: priorità ai global settings, hardcode solo come fallback — Cx: S — Imp: Basso

Oggi `get_or_create_user_settings()` e il ramo di creazione in `update_user_settings()` (`backend/app/services/settings_service.py:57-59, 86-88`) creano `UserSettings` con `"en"/"EUR"/"light"` **hardcoded**, ignorando `GLOBAL_SETTINGS_DEFAULTS` già importato nello stesso file.

**Direzione decisa**: non più hardcode come valore primario — leggere prima da `GlobalSetting` (via `get_setting_value()`, già esistente in `global_settings_service.py`), usare `"en"/"EUR"/"light"` solo come fallback se il global setting stesso non è configurato.

- Modificare `get_or_create_user_settings()`: prima di inserire, leggere `default_language`/`default_currency` da global settings
- Stesso fix nel ramo "crea se non esiste" di `update_user_settings()`
- Il tema (`theme`) non ha un default globale equivalente oggi — restare hardcoded `"light"` o valutare se aggiungere anche quello ai global settings (fuori scope minimo)
- Nessuna migrazione DB necessaria (stesso schema, cambia solo la logica di inizializzazione)

---

### 3. 🤖 AI Export — FX Pair Detail (snapshot + spiegazione trend) — Cx: M — Imp: Basso-Medio

**Decisione 17/07**: niente AI export su `/transactions` (non ha senso, confermato). Solo su `/fx/[pair]`, mirror ridotto del pattern asset (2 varianti, non 6).

**Design** (mirror di `frontend/src/lib/features/ai-export/asset/`):
- `fx_snapshot` (dati puri, no istruzioni — come `asset_snapshot`)
- `fx_trend` (aggiunge ruolo/task: "spiega perché il tasso si muove in questa direzione", richiesta di web research su differenziali di tasso/politica monetaria/eventi macro — come `asset_classify` ma tarato su FX)

**Dati nella fotografia — punto chiave richiesto**: includere **entrambe le direzioni del tasso già calcolate** (`rate_base_to_quote` e `rate_quote_to_base` = `1/rate`), così l'LLM non deve invertire nulla da solo. La logica di inversione esiste già in `fx/[pair]/+page.svelte` (`inverted ? 1/rate : rate`, riga ~222) — riusarla per calcolare entrambi i valori invece di uno solo.

**Segnali tecnici — proposta** (nessuno di questi esiste oggi per FX, serve nuova infra):
- ✅ **EMA** (20/50/200) e ✅ **MACD** (hist): inclusi — standard anche in analisi FX, utili per la narrativa di trend/momentum richiesta da `fx_trend`
- ❌ **RSI**: escluso come richiesto — dominio senza vero "overbought/oversold" strutturale (i tassi sono guidati da differenziali macro, non da momentum)
- **Bollinger Bands**: non incluse — non fanno parte nemmeno dell'export tecnico asset attuale (`technicalExportBuilder.ts` non le calcola, solo EMA/RSI/MACD) → nessuno scope-creep, consistenza con l'asset export esistente

**File da creare** (mirror 1:1 di `ai-export/asset/`):
- `frontend/src/lib/features/ai-export/fx/fxPromptCatalog.ts` (2 entry)
- `frontend/src/lib/features/ai-export/fx/fxTypes.ts`
- `frontend/src/lib/features/ai-export/fx/fxExportBuilder.ts` — legge da `fxStoreRegistry.ts` (non `assetPriceStoreRegistry.ts`)
- `frontend/src/lib/features/ai-export/fx/fxPromptRenderer.ts`
- `frontend/src/lib/features/ai-export/fx/fxExportClipboard.ts`
- Nuovo `buildFxTechnicalContext()` in `ai-export/technical/` — **valutare se generalizzare** `buildTechnicalContext()` esistente (accetta un price-loader come parametro) invece di duplicare ~250 righe; se troppo invasivo, duplicare e adattare da `technicalExportBuilder.ts`
- Wiring in `frontend/src/routes/(app)/fx/[pair]/+page.svelte` (stesso pattern di `assets/[id]/+page.svelte`)

---

### 4. 📸 Gallery: 4 tipi transazione mancanti + carousel mkdocs — Cx: S — Imp: Nullo

**gallery.spec.ts** (`frontend/e2e/gallery.spec.ts:1006-1014`): aggiungere a `TX_FORM_VARIANT_TYPES`:
```ts
{type: 'WITHDRAWAL', name: 'form-modal-withdrawal'},
{type: 'INTEREST', name: 'form-modal-interest'},
{type: 'FEE', name: 'form-modal-fee'},
{type: 'TAX', name: 'form-modal-tax'},
```
Loop e screenshot sono già generici — zero altra logica da scrivere.

**mkdocs — stesso carosello delle altre transazioni**, 8 file da aggiornare (carousel `carousel-desktop-1` / `carousel-mobile-1`, subito dopo l'ultima riga `form-modal-cash-transfer` in ciascun file):
- `mkdocs_src/docs/gallery/desktop.{en,it,fr,es}.md`
- `mkdocs_src/docs/gallery/mobile.{en,it,fr,es}.md`

Pattern (esempio EN, replicare per le altre 3 lingue con stesso `data-name`, titoli/alt tradotti):
```html
<img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="transactions" data-name="form-modal-withdrawal" data-title="💸 Withdrawal" alt="Transaction Form — WITHDRAWAL">
<img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="transactions" data-name="form-modal-interest" data-title="🪙 Interest" alt="Transaction Form — INTEREST">
<img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="transactions" data-name="form-modal-fee" data-title="💳 Fee" alt="Transaction Form — FEE">
<img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="transactions" data-name="form-modal-tax" data-title="🧾 Tax" alt="Transaction Form — TAX">
```
Traduzioni titolo proposte (stesse emoji, cambia solo il testo — pattern esistente: EN "Transaction Form — X", IT "Modulo Transazione — X", FR "Formulaire de Transaction — X", ES "Formulario de Transacción — X"):

| Tipo | EN | IT | FR | ES |
|---|---|---|---|---|
| WITHDRAWAL | Withdrawal | Prelievo | Retrait | Retiro |
| INTEREST | Interest | Interesse | Intérêt | Interés |
| FEE | Fee | Commissione | Frais | Comisión |
| TAX | Tax | Tassa | Taxe | Impuesto |

Emoji proposte (💸/🪙/💳/🧾) scelte per non duplicare quelle già usate nello stesso carosello (📈📉💰🏦🔧🔀💱🏧) — modificabili.

---

## 📋 Backlog ordinato — solo indice (dettaglio esteso in `TODO_FUTURI.md`)

### Facili (S/XS)

5. **Rimuovere `preview_columns` dai plugin BRIM** — Cx: XS — Imp: Nullo. Cleanup meccanico su 11 plugin + schema + test + `./dev.py api sync`.
6. **Link Transazioni in Asset Delete Modal** — Cx: XS — Imp: Basso. Il filtro `?asset_id=` esiste già in `/transactions` → resta solo `transaction_count` su `FAAssetDeleteResult` + link cliccabile nel modal di cancellazione bloccata. *Doppia verifica 17/07 su richiesta utente: nessun conteggio/link esistente trovato in nessun punto del flusso (backend `asset_source.py:3597` cattura solo un FK error generico; FE `assets/+page.svelte:674,727` mostra un toast statico senza numero né link); confermato ancora da fare.*
7. **Filtro Utente nella Files Page** — Cx: S/M — Imp: Basso. Serve endpoint che risolva `uploaded_by_user_id` → username (riusa `search_users`, resta GDPR-safe senza email) + colonna/filtro FE. Utile solo su istanze multi-utente.

### Medie (M)

8. **BRIM auto-detect broker via account_code** — Cx: M — Imp: Medio. Nuovo campo `Broker.account_code` + estensione `can_parse()`/`detect()` + 1 plugin pilota (Directa) + prefill FE nel wizard import.
9. **Transaction Form — badge conteggio asset/cash per broker** — Cx: M — Imp: Medio. Riduce errori in inserimento transazioni (specialmente SELL/oversell).
10. **Price provider oltre CSS selector (JSON API generico / HTML table / CSV remoto)** — Cx: M — Imp: Medio-Alto. Pattern provider registry già pronto (vedi `css_scraper.py` come base) — "solo" nuovi plugin.
11. **Grafico asset — rendimento a N giorni (rolling return)** — Cx: M — Imp: Medio-Alto. Nuovo calcolo + toggle sul chart asset detail, nessuna infra esistente da riusare.
12. **coupon_policy + frequenze scheduled investment disaccoppiate** — Cx: M/L — Imp: Medio (nicchia bond/BTP). Design già scritto in `TODO_FUTURI.md`; c'è un bug noto (#R6-3, `current_price` incoerente) da risolvere come prerequisito.

### Medio-complesse (M/L)

13. **Asset Detail: lista transazioni con P&L storico + grafico guadagni cumulativo per transazione** — Cx: M/L — Imp: **Alto**, molto richiesta. Riusa parecchia infra già costruita per il broker "Posizioni" (`UnifiedLotsTable`, `LotsAnalysisPanel`, `LotWacPriceChart`) — serve una vista cross-broker per singolo asset invece che per singolo broker.
14. **Migrazione a ORJSONResponse** — Cx: M/L — Imp: Nullo/impercettibile. Attenzione a `SafeDecimal`/`PlainSerializer` — serve subclass dedicata, non sostituzione diretta.
15. **Cache server centralizzato multi-worker** — Cx: M/L — Imp: Nullo oggi. Gated da migrazione a Postgres + scala reale (>50 utenti concorrenti) — non è un problema con 1 worker/SQLite attuale.
16. **Pagine di dettaglio trade/fee** — Cx: M/L — Imp: Medio. *Verificato 17/07 su richiesta utente*: Dashboard/Broker detail (Holdings panel + KPI) mostrano oggi solo **aggregati**, non dettaglio. `HoldingsPanel.svelte` ha solo colonne Asset/Prezzo/Valore/Gain% (nessuna fee, nessun trade). Il KPI "Fees & Taxes" (`KpiSection.svelte:156-173`) è **un singolo numero per periodo** (con tooltip che separa commissioni da tasse), non una pagina/breakdown. Il backend ha già i campi (`period_fees`, `period_fees_taxes`, `unallocated_fees_taxes` in `portfolio.py`) — utile "solo" costruire la UI di dettaglio (breakdown per broker/tempo/tipo), il dato è pronto. La parte "trade" si sovrappone al punto 13 (lista transazioni asset) — da coordinare insieme, non due feature indipendenti.

### Complesse (L)

17. **Calcolatore FIRE (teorico vs reale)** — Cx: L — Imp: Alto, feature "wow" per community FIRE.
18. **Target Allocation persistente (per broker/generale)** — Cx: L — Imp: Alto, feature standard nei competitor.
19. **AI provider diretti oltre ollama/openrouter** — Cx: L — Imp: Medio. Diverso concettualmente dall'AI export a clipboard attuale — richiede gestione API key/costi, non solo aggiungere provider.

### Molto complesse (XL) — toccano architettura core

20. **Stock Split nel motore FIFO** — Cx: L/XL — Imp: **ALTO e urgente**. Il motore FIFO (`fifo_utils.py`) filtra solo BUY/SELL, `ADJUSTMENT` non basta (verificato: il messaggio di errore oversell già lo dice — *"Possible unrecognized stock split..."*). Crasha oggi su split reali (AAPL, GOOG, NVDA...). ⚠️ Il motore FIFO è già "sotto osservazione" per un redesign più ampio (mismatch WAC/transfer, vedi `LibreFolio_developer_journal/RoadmapV4_UI/fifo-engine/fifo-engine-current-state.md`, + item 0 di questo file sui FEE/TAX) — **non affrontare isolato**, coordinare con quel redesign.
21. **Regime Fiscale — Metodo di Vendita (FIFO/LIFO/PMC/Select ID)** — Cx: XL — Imp: **Alto**, per utenti IT è quasi requisito di conformità fiscale (PMC). Stesso motore dei punti 0 e 20 → stessa raccomandazione di coordinamento.
22. **Portafogli (gruppi arbitrari di broker/asset)** — Cx: XL — Imp: Alto (multi-conto/famiglia) ma tocca quasi tutte le aggregazioni esistenti.
23. **GDPR — accesso broker Utente-SuperUtente** — Cx: XL — Imp: Medio-Alto se multi-utente/EU, basso per self-host singolo utente. Architettura di massima già in `plan-phase05-to-08-upgrade.md` §10.
24. **QuarkAI — assistente AI (MCP server, notifiche)** — Cx: XL — Imp: Basso-Medio. Nuovo sottosistema completo (scheduler, notifiche Telegram, scraping notizie).
25. **Addon/Marketplace per tab frontend** — Cx: XL+ — Imp: Alto potenziale a lungo termine, priorità bassissima realistica ora. Il più ambizioso di tutti.

### Bloccato (esterno, non azionabile ora)

26. **TanStack Table v9 migration** — Imp: Nullo. v9 ancora in alpha, adapter custom Svelte 5 resta necessario finché non c'è supporto ufficiale stabile.
