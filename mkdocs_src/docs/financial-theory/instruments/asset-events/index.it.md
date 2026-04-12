# 📅 Eventi dell'Asset

Gli eventi dell'asset rappresentano **azioni societarie o occorrenze finanziarie programmate** che influenzano un asset a livello globale, indipendentemente dal portafoglio del singolo investitore. Sono distinti dalle [transazioni](../transaction-types/index.md), che tracciano ciò che accade a livello di portafoglio (ad esempio, un utente che acquista o vende azioni).

Comprendere gli eventi dell'asset è essenziale per un'analisi accurata dei prezzi, il calcolo del rendimento totale e l'interpretazione dei grafici storici.

---

## 📊 Panoramica dei Tipi di Evento

| Tipo | Emoji | Impatto sul Prezzo | Asset Tipici | Dettagli |
|------|-------|----------------|----------------|---------|
| **Dividendo** | 💰 | Il prezzo scende dell'importo del dividendo (ex-date) | Azioni, ETF | [📖](dividend.md) |
| **Interesse** | 📈 | L'accumulo riduce il rendimento rimanente | Obbligazioni, Prestiti, Reddito fisso | [📖](interest.md) |
| **Split** | ✂️ | Il prezzo si divide, la quantità si moltiplica | Azioni, ETF | [📖](split.md) |
| **Adeguamento del prezzo** | 📊 | Variazione algebrica (+/−) del fair value | Obbligazioni, Asset illiquidi | [📖](price-adjustment.md) |
| **Liquidazione alla scadenza** | 🏁 | Restituzione finale del capitale, nessun ulteriore prezzo | Obbligazioni, Depositi a termine | [📖](maturity-settlement.md) |

---

## 🔄 Eventi vs Transazioni

| Concetto | Eventi | Transazioni |
|---------|--------|-------------|
| **Ambito** | Globale — influenza l'asset stesso | Personale — influenza il portafoglio di un utente |
| **Esempio** | "Apple ha dichiarato un dividendo di $0,25 il 2024-05-10" | "Ho ricevuto $12,50 dalle mie 50 azioni AAPL" |
| **Effetto sul grafico** | Marcatore sul grafico dei prezzi | Non visibile sul grafico dei prezzi |
| **Chi li crea** | Provider (automatico) o utente (manuale) | Importazione da report del broker (BRIM) |

---

## ⚙️ Fonti degli Eventi

### 🤖 Generati dal Provider (automatici)

Alcuni provider producono eventi durante la sincronizzazione dei dati:

- **Scheduled Investment**: genera eventi `INTEREST` e `PRICE_ADJUSTMENT` sulla base del programma di interessi configurato
- **Yahoo Finance**: può produrre eventi `DIVIDEND` dai dati storici

Gli eventi generati dal provider hanno un `provider_assignment_id` e vengono aggiornati automaticamente durante la sincronizzazione (deduplicazione su `asset_id + date + type`).

### ✏️ Creati dall'Utente (manuali)

Gli eventi possono essere aggiunti manualmente tramite il **Data Editor** o l'**Importazione CSV**. Gli eventi manuali non hanno un `provider_assignment_id` e non vengono mai eliminati automaticamente durante la sincronizzazione.

---

## 📈 Marcatori di Evento sul Grafico

Gli eventi appaiono come **marcatori a diamante colorati** (◆) sul grafico interattivo dei prezzi. Ogni tipo di evento ha un colore distinto. Passa il mouse sopra un marcatore per vedere i dettagli completi (data, tipo, valore, valuta, note).

Fare doppio clic su un marcatore di evento mentre il Data Editor è aperto permetterà di **scorrere direttamente alla riga di quell'evento** nella scheda Eventi.

---

## 🔗 Correlati

- 📈 **[Grafico Interattivo](../../../user/assets/detail/chart.md)** — Marcatori di evento sul grafico
- ✏️ **[Data Editor](../../../user/assets/detail/data-editor.md)** — Gestione manuale degli eventi
- 💸 **[Tipi di Transazione](../transaction-types/index.md)** — Operazioni a livello di portafoglio
