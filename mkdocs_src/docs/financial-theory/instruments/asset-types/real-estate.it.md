# ![](../../../static/icons/asset-types/crowdfunding.png){: width="32" style="vertical-align: middle;" } P2P / Crowdfunding

Le piattaforme **P2P / Crowdfunding** consentono agli investitori di partecipare a progetti immobiliari o prestiti al consumo/alle imprese con importi relativamente piccoli. Questi strumenti offrono tipicamente pagamenti di interessi fissi o variabili e hanno una data di scadenza definita.

---

## 🔑 Caratteristiche Principali

| Proprietà | Dettaglio |
|-----------|-----------|
| **Codice in LibreFolio** | `CROWDFUND` |
| **Prezzatura** | Non scambiato in borsa — il valore è tipicamente il capitale investito |
| **Valuta** | Denominato nella valuta operativa della piattaforma |
| **Reddito** | Pagamenti periodici di interessi (mensili, trimestrali o alla scadenza) |
| **Liquidità** | Molto bassa — i fondi sono bloccati fino alla scadenza o al riacquisto |
| **Provider tipici** | Investimento programmato, Manuale |

---

## 📊 Come Funziona

### 🏗️ Crowdfunding Immobiliare

1. Una piattaforma elenca un progetto immobiliare che necessita di finanziamenti
2. Molteplici investitori contribuiscono con piccole somme (tipicamente €500–€10.000)
3. Il progetto paga interessi sul capitale investito
4. Alla scadenza, il capitale viene restituito (se il progetto ha successo)

### 💸 Prestiti P2P

1. I mutuatari richiedono prestiti tramite una piattaforma
2. Gli investitori finanziano porzioni di prestiti
3. I mutuatari rimborsano capitale + interessi durante la durata del prestito
4. La piattaforma distribuisce i pagamenti agli investitori

---

## ⚠️ Fattori di Rischio

| Rischio | Descrizione |
|---------|-------------|
| **Rischio di default** | Il mutuatario/progetto potrebbe non rimborsare |
| **Rischio di liquidità** | Non è possibile vendere prima della scadenza (a differenza delle azioni) |
| **Rischio piattaforma** | La piattaforma stessa potrebbe fallire |
| **Rischio di concentrazione** | Ogni investimento è un singolo progetto/mutuatario |

---

## 🔧 Modellazione in LibreFolio

Il provider **Investimento programmato** è progettato per questi strumenti. Genera:

- **[Eventi di Interesse](../asset-events/interest.md)** — Pagamenti cedolari periodici basati sul tasso e sulla frequenza configurati
- **[Eventi di Liquidazione a Scadenza](../asset-events/maturity-settlement.md)** — Restituzione finale del capitale alla fine del termine
- **[Eventi di Adeguamento Prezzo](../asset-events/price-adjustment.md)** — Svalutazioni se il progetto sottoperforma

---

## 🔗 Correlati

- 📈 **[Eventi di Interesse](../asset-events/interest.md)** — Come funziona la maturazione degli interessi
- 🏁 **[Liquidazione a Scadenza](../asset-events/maturity-settlement.md)** — Restituzione del capitale a fine vita
- 📅 **[Convenzioni di Conteggio Giorni](../../fundamentals/day-count.md)** — Come vengono calcolati i periodi di interesse
