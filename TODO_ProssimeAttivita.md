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

## 📋 Backlog ordinato — solo indice (dettaglio esteso in `TODO_FUTURI.md`)

> I 4 "task con spec completa" (cleanup `/countries/normalize`, default lang/currency, AI Export FX Pair Detail, gallery 4 tipi mancanti) e il cleanup `preview_columns` BRIM sono stati implementati e verificati il 17 Luglio 2026 — vedi `TODO_Completati.md`.

### Facili (S/XS)

5. **Link Transazioni in Asset Delete Modal** — Cx: XS — Imp: Basso. Il filtro `?asset_id=` esiste già in `/transactions` → resta solo `transaction_count` su `FAAssetDeleteResult` + link cliccabile nel modal di cancellazione bloccata. *Doppia verifica 17/07 su richiesta utente: nessun conteggio/link esistente trovato in nessun punto del flusso (backend `asset_source.py:3597` cattura solo un FK error generico; FE `assets/+page.svelte:674,727` mostra un toast statico senza numero né link); confermato ancora da fare.*
6. **Filtro Utente nella Files Page** — Cx: S/M — Imp: Basso. Serve endpoint che risolva `uploaded_by_user_id` → username (riusa `search_users`, resta GDPR-safe senza email) + colonna/filtro FE. Utile solo su istanze multi-utente.

### Medie (M)

7. **BRIM auto-detect broker via account_code** — Cx: M — Imp: Medio. Nuovo campo `Broker.account_code` + estensione `can_parse()`/`detect()` + 1 plugin pilota (Directa) + prefill FE nel wizard import.
8. **Transaction Form — badge conteggio asset/cash per broker** — Cx: M — Imp: Medio. Riduce errori in inserimento transazioni (specialmente SELL/oversell).
9. **Price provider oltre CSS selector (JSON API generico / HTML table / CSV remoto)** — Cx: M — Imp: Medio-Alto. Pattern provider registry già pronto (vedi `css_scraper.py` come base) — "solo" nuovi plugin.
10. **Grafico asset — rendimento a N giorni (rolling return)** — Cx: M — Imp: Medio-Alto. Nuovo calcolo + toggle sul chart asset detail, nessuna infra esistente da riusare.
11. **coupon_policy + frequenze scheduled investment disaccoppiate** — Cx: M/L — Imp: Medio (nicchia bond/BTP). Design già scritto in `TODO_FUTURI.md`; c'è un bug noto (#R6-3, `current_price` incoerente) da risolvere come prerequisito.

### Medio-complesse (M/L)

12. **Asset Detail: lista transazioni con P&L storico + grafico guadagni cumulativo per transazione** — Cx: M/L — Imp: **Alto**, molto richiesta. Riusa parecchia infra già costruita per il broker "Posizioni" (`UnifiedLotsTable`, `LotsAnalysisPanel`, `LotWacPriceChart`) — serve una vista cross-broker per singolo asset invece che per singolo broker.
13. **Migrazione a ORJSONResponse** — Cx: M/L — Imp: Nullo/impercettibile. Attenzione a `SafeDecimal`/`PlainSerializer` — serve subclass dedicata, non sostituzione diretta.
14. **Cache server centralizzato multi-worker** — Cx: M/L — Imp: Nullo oggi. Gated da migrazione a Postgres + scala reale (>50 utenti concorrenti) — non è un problema con 1 worker/SQLite attuale.
15. **Pagine di dettaglio trade/fee** — Cx: M/L — Imp: Medio. *Verificato 17/07 su richiesta utente*: Dashboard/Broker detail (Holdings panel + KPI) mostrano oggi solo **aggregati**, non dettaglio. `HoldingsPanel.svelte` ha solo colonne Asset/Prezzo/Valore/Gain% (nessuna fee, nessun trade). Il KPI "Fees & Taxes" (`KpiSection.svelte:156-173`) è **un singolo numero per periodo** (con tooltip che separa commissioni da tasse), non una pagina/breakdown. Il backend ha già i campi (`period_fees`, `period_fees_taxes`, `unallocated_fees_taxes` in `portfolio.py`) — utile "solo" costruire la UI di dettaglio (breakdown per broker/tempo/tipo), il dato è pronto. La parte "trade" si sovrappone al punto 12 (lista transazioni asset) — da coordinare insieme, non due feature indipendenti.

### Complesse (L)

16. **Calcolatore FIRE (teorico vs reale)** — Cx: L — Imp: Alto, feature "wow" per community FIRE.
17. **Target Allocation persistente (per broker/generale)** — Cx: L — Imp: Alto, feature standard nei competitor.
18. **AI provider diretti oltre ollama/openrouter** — Cx: L — Imp: Medio. Diverso concettualmente dall'AI export a clipboard attuale — richiede gestione API key/costi, non solo aggiungere provider.

### Molto complesse (XL) — toccano architettura core

19. **Stock Split nel motore FIFO** — Cx: L/XL — Imp: **ALTO e urgente**. Il motore FIFO (`fifo_utils.py`) filtra solo BUY/SELL, `ADJUSTMENT` non basta (verificato: il messaggio di errore oversell già lo dice — *"Possible unrecognized stock split..."*). Crasha oggi su split reali (AAPL, GOOG, NVDA...). ⚠️ Il motore FIFO è già "sotto osservazione" per un redesign più ampio (mismatch WAC/transfer, vedi `LibreFolio_developer_journal/RoadmapV4_UI/fifo-engine/fifo-engine-current-state.md`, + item 0 di questo file sui FEE/TAX) — **non affrontare isolato**, coordinare con quel redesign.
20. **Regime Fiscale — Metodo di Vendita (FIFO/LIFO/PMC/Select ID)** — Cx: XL — Imp: **Alto**, per utenti IT è quasi requisito di conformità fiscale (PMC). Stesso motore dei punti 0 e 19 → stessa raccomandazione di coordinamento.
21. **Portafogli (gruppi arbitrari di broker/asset)** — Cx: XL — Imp: Alto (multi-conto/famiglia) ma tocca quasi tutte le aggregazioni esistenti.
22. **GDPR — accesso broker Utente-SuperUtente** — Cx: XL — Imp: Medio-Alto se multi-utente/EU, basso per self-host singolo utente. Architettura di massima già in `plan-phase05-to-08-upgrade.md` §10.
23. **QuarkAI — assistente AI (MCP server, notifiche)** — Cx: XL — Imp: Basso-Medio. Nuovo sottosistema completo (scheduler, notifiche Telegram, scraping notizie).
24. **Addon/Marketplace per tab frontend** — Cx: XL+ — Imp: Alto potenziale a lungo termine, priorità bassissima realistica ora. Il più ambizioso di tutti.

### Bloccato (esterno, non azionabile ora)

25. **TanStack Table v9 migration** — Imp: Nullo. v9 ancora in alpha, adapter custom Svelte 5 resta necessario finché non c'è supporto ufficiale stabile.
