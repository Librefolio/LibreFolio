# Audit Documentazione: Assets, Brokers & Import (BRIM)

**Data:** 18 Giugno 2026  
**Area di Analisi:** Documentazione LibreFolio V0.5.11 (lingua inglese `.en.md` e developer docs)

Di seguito l'esito dell'audit condotto sulle sezioni relative alla gestione degli asset, visibilità dei broker e importazione transazioni (BRIM).

---

## 1. Live-polling asset (Recupero prezzi in tempo reale) & Backend Scheduler

**File analizzati:**
- `docs/developer/backend/assets/architecture.md`
- `docs/developer/backend/assets/system_providers.md`
- `docs/developer/backend/scheduler.md`
- `docs/user/assets/index.en.md`
- `docs/user/settings/index.en.md`

**Valutazione:** 🟢 **Completa e allineata agli standard**

**Analisi:**
La documentazione tecnica e utente copre ora in modo integrato sia il polling in tempo reale del frontend (Live Ticker) sia l'infrastruttura di sincronizzazione periodica del backend (Scheduler).

**Risoluzione (19 Giugno 2026):**
- **Documentazione Tecnica Scheduler:** Creato il file [scheduler.md](file:///home/alfy/Documenti/02_myRepo/LibreFolio_prj/LibreFolio/mkdocs_src/docs/developer/backend/scheduler.md) descrivendo il ciclo del demone asincrono integrato nel lifespan di FastAPI, l'algoritmo di Leader Election (`leader.py` basato su file-lock), i job di sincronizzazione dei prezzi e delle cronologie storiche, e il sistema rotativo dei log JSONL (`scheduler_jobs.jsonl`). Aggiunto un diagramma del ciclo di vita con il layout ELK (`layout: elk`).
- **Guida Utente Live Ticker:** Aggiornato [index.en.md (Assets)](file:///home/alfy/Documenti/02_myRepo/LibreFolio_prj/LibreFolio/mkdocs_src/docs/user/assets/index.en.md) con la sezione *Real-time Pricing & Live Ticker*, spiegando le tempistiche di polling (30 secondi), il codice colore visivo dei badge (verde/rosso/grigio) e l'interazione con la cache del backend e lo scheduler.
- **Impostazioni di Amministrazione:** Aggiornato [index.en.md (Settings)](file:///home/alfy/Documenti/02_myRepo/LibreFolio_prj/LibreFolio/mkdocs_src/docs/user/settings/index.en.md) per includere le opzioni dello scheduler nella tabella dei Global Settings e documentare i dettagli dei modali di configurazione ed ispezione dei log.
- **Integrazione Galleria:** Inseriti i due screenshot ufficiali (`scheduler-config` e `scheduler-log` nella categoria `settings`) nel manuale utente delle impostazioni.
- **Navigazione:** Registrato il documento dello scheduler in [mkdocs.yml](file:///home/alfy/Documenti/02_myRepo/LibreFolio_prj/LibreFolio/mkdocs_src/mkdocs.yml).

---


## 2. Charts (Grafici interattivi, Segnali, Eventi)

**File analizzati:**
- `docs/user/assets/detail/chart.en.md`
- `docs/user/assets/detail/events.en.md`
- `docs/user/assets/detail/signals.en.md`

**Valutazione:** 🟢 **Completa e allineata agli standard estetici**

**Analisi:**
L'intera documentazione utente relativa alla *Detail Page* degli asset è eccellente. 
- Utilizza sistematicamente blocchi predisposti per gli screenshot (`<div class="screenshot-container">...</div>`).
- Strutturazione logica tramite markdown headers, emoji e liste.
- Ottimo l'utilizzo delle tabelle (es. Event Types con relative icone).
- **Punto di forza:** Collegamenti continui e ben strutturati alla documentazione di Teoria Finanziaria (es. per MACD, RSI, e dinamiche degli eventi come gli split). Non sono richiesti interventi correttivi.

---

## 3. Broker access visibility (RBAC e Condivisione)

**File analizzati:**
- `docs/user/brokers/sharing.en.md`
- `docs/developer/architecture/users_and_brokers.md`

**Valutazione:** 🟢 **Completa e allineata agli standard estetici**

**Analisi:**
La gestione dei permessi e la segregazione dei dati utente/broker sono documentati in modo impeccabile sia per gli sviluppatori che per l'utente finale.
- **Lato Developer:** L'architettura spiega bene la gerarchia di ownership e la condivisione tramite diagrammi Mermaid molto chiari e blocchi esplicativi sulle logiche globali vs specifiche per utente.
- **Lato User:** La pagina `sharing.en.md` usa efficacemente *admonitions* (avvisi grafici) e tabelle comparative per spiegare i ruoli (Viewer, Editor, Owner) e include esempi pratici sulla logica della *Share Percentage* (es. Joint Account vs Consulente Finanziario).

---

## 4. BRIM parser v2 (Broker Report Import Manager)

**File analizzati:**
- `docs/developer/backend/brim/architecture.md`
- `docs/user/transactions/import/index.en.md`
- `docs/user/transactions/import/ibkr.en.md` (e altri 9 broker: Degiro, Coinbase, Directa, eToro, Finpension, Freetrade, Revolut, Schwab, Trading212)

**Valutazione:** 🟢 **Completa e allineata agli standard**

**Analisi:**
La documentazione generale e le guide specifiche dei singoli broker sono state estese per offrire un percorso chiaro ed esauriente sia dal lato tecnico che utente.

**Risoluzione (19 Giugno 2026):**
- **Arricchimento Guide Broker:** Estesi e riscritti tutti i 10 manuali dei singoli broker (`ibkr.en.md`, `degiro.en.md`, `coinbase.en.md`, `directa.en.md`, `etoro.en.md`, `finpension.en.md`, `freetrade.en.md`, `revolut.en.md`, `schwab.en.md`, `trading212.en.md`).
- **Istruzioni Dettagliate di Export:** Aggiunti passaggi rigorosi e dettagliati per orientare l'utente nei portali originali dei broker (compresa la configurazione di Flex Query su Interactive Brokers).
- **Admonitions e Pitfalls:** Inserite avvertenze specifiche (`!!! warning`) riguardanti i formati dei file (es. obbligo di CSV rispetto a PDF), la lingua dei report (obbligo della lingua inglese per Interactive Brokers e altri provider) e il trattamento di split/dividendi o valute.
- **Placeholder Screenshot UI originali:** Inseriti elementi `<div class="screenshot-container">` con commenti e istruzioni esplicite per evidenziare dove posizionare le immagini dell'interfaccia dei portali originali.
