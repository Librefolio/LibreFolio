# Audit Documentazione: Assets, Brokers & Import (BRIM)

**Data:** 18 Giugno 2026  
**Area di Analisi:** Documentazione LibreFolio V0.5.11 (lingua inglese `.en.md` e developer docs)

Di seguito l'esito dell'audit condotto sulle sezioni relative alla gestione degli asset, visibilità dei broker e importazione transazioni (BRIM).

---

## 1. Live-polling asset (Recupero prezzi in tempo reale)

**File analizzati:**
- `docs/developer/backend/assets/architecture.md`
- `docs/developer/backend/assets/system_providers.md`
- `docs/user/assets/index.en.md`

**Valutazione:** 🟡 **Completa ma da migliorare esteticamente / Gap da colmare**

**Analisi:**
La documentazione tecnica (Developer) è di altissimo livello ("Completa e allineata agli standard estetici"). Descrive in modo esauriente la pipeline di sincronizzazione, i meccanismi di caching (`_asset_current_cache`) e l'endpoint dedicato `POST /assets/prices/current` utilizzato per il componente *LiveTicker*.
Lato utente (User Manual), tuttavia, manca un focus specifico sul concetto di "live-polling". Le meccaniche sono accennate nelle sezioni dei singoli provider (es. CSS Scraper o Yahoo Finance) e si parla di "Refresh" o "Sync" nella pagina indice degli assets, ma non c'è una rappresentazione visiva chiara dell'indicatore Live Ticker in azione.

**Proposta:**
- **Dove scrivere:** Integrare in `docs/user/assets/index.en.md` (o creare una sotto-pagina dedicata) una sezione "Real-time Pricing & Live Ticker".
- **Cosa scrivere:** Spiegare in termini utente come e quando l'applicazione effettua il polling (vs. il sync batch), aggiungendo uno screenshot o una GIF del componente Live Ticker nell'interfaccia.
- **NOTA OPERATIVA (Cross-reference con lo Scheduler):** La feature di aggiornamento del *Live Ticker* lato frontend, seppur indipendente a livello di componente UI, concettualmente ricade nella stessa categoria architetturale dello **Scheduler di backend**. Quando si affronterà questo task, le due tematiche verranno trattate congiuntamente per garantire coerenza tra il polling frontend e i cron job di sistema.

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
- `docs/user/transactions/import/ibkr.en.md` (e omologhi per altri broker)

**Valutazione mista:**
- Core Architecture e Index: 🟢 **Completa e allineata agli standard estetici**
- Pagine specifiche dei Broker: 🟠 **Gap da colmare**

**Analisi:**
La documentazione generale di BRIM è ottima. Il workflow di parsing a fasi (Upload -> Preview -> Mapping -> Import) è documentato tecnicamente con un diagramma Mermaid e spiegato in modo semplice all'utente finale nel file `index.en.md`.

Il problema sorge nelle **sotto-pagine dedicate ai singoli broker** (es. `coinbase.en.md`, `degiro.en.md`, `ibkr.en.md`). Attualmente sono estremamente brevi, composte da un elenco testuale di 3 passaggi su come effettuare l'esportazione dal broker e segnate come "Beta".

**Proposta (Analisi del gap):**
- **Dove scrivere:** All'interno di ogni file `.en.md` dei singoli broker (es. `ibkr.en.md`, `degiro.en.md`).
- **Cosa scrivere:** È necessario arricchire la guida di esportazione inserendo screenshot catturati dai portali originali dei broker (evidenziando i menu "Report", "Esporta in CSV", etc.). Un blocco di testo non è sufficiente, in quanto l'interfaccia dei broker cambia spesso e una guida visiva riduce la frustrazione dell'utente durante il setup dell'importazione.
