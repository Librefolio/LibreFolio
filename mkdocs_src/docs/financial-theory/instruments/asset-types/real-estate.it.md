# <img src="../../../static/icons/asset-types/crowdfunding.png" width="32" style="vertical-align: middle;" /> P2P / Crowdfunding

Le piattaforme di **P2P / Crowdfunding** consentono agli investitori di partecipare a progetti immobiliari o a prestiti per consumatori/imprese con importi relativamente piccoli. Questi strumenti offrono tipicamente pagamenti di interessi fissi o variabili e hanno una data di scadenza definita.

---

## 🔑 Caratteristiche Principali

| Proprietà | Dettaglio |
|----------|--------|
| **Codice in LibreFolio** | `CROWDFUNDING` |
| **Prezzo** | Non scambiato in borsa — il valore è tipicamente il capitale investito |
| **Valuta** | Denominata nella valuta operativa della piattaforma |
| **Reddito** | Pagamenti periodici di interessi (mensili, trimestrali o alla scadenza) |
| **Liquidità** | Molto bassa — i fondi sono bloccati fino alla scadenza o al riacquisto |
| **Provider tipici** | Scheduled Investment, Manual |

---

## 📊 Come Funziona

### 🏗️ Real Estate Crowdfunding

1. Una piattaforma pubblica un progetto immobiliare che necessita di finanziamenti
2. Diversi investitori contribuiscono con piccole somme (tipicamente tra €500 e €10.000)
3. Il progetto paga interessi sul capitale investito
4. Alla scadenza, il capitale viene restituito (se il progetto ha successo)

### 💸 P2P Lending

1. I debitori richiedono prestiti tramite una piattaforma
2. Gli investitori finanziano porzioni dei prestiti
3. I debitori rimborsano il capitale + gli interessi durante la durata del prestito
4. La piattaforma distribuisce i pagamenti agli investitori

---

## ⚠️ Fattori di Rischio

| Rischio | Descrizione |
|------|-------------|
| **Rischio di default** | Il debitore/progetto potrebbe non essere in grado di rimborsare |
| **Rischio di liquidità** | Impossibilità di vendere prima della scadenza (a differenza delle azioni) |
| **Rischio piattaforma** | La piattaforma stessa potrebbe fallire |
| **Rischio di concentrazione** | Ogni investimento è legato a un singolo progetto/debitore |

---

## 🔧 Modellazione in LibreFolio

Il provider **Scheduled Investment** è progettato per questi strumenti. Esso genera:

- **[Eventi di interesse](../asset-events/interest.md)** — Pagamenti periodici di cedole basati sul tasso e sulla programmazione configurati
- **[Eventi di regolamento alla scadenza](../asset-events/maturity-settlement.md)** — Restituzione finale del capitale alla scadenza
- **[Eventi di adeguamento del prezzo](../asset-events/price-adjustment.md)** — Svalutazioni in caso di performance negativa del progetto

---

## 🔗 Correlati

- 📈 **[Eventi di Interesse](../asset-events/interest.md)** — Come funziona l'accrual degli interessi
- 🏁 **[Regolamento alla Scadenza](../asset-events/maturity-settlement.md)** — Restituzione del capitale a scadenza dell'asset
- 📅 **[Convenzioni di Conteggio dei Giorni](../../fundamentals/day-count.md)** — Come vengono calcolati i periodi di interesse
