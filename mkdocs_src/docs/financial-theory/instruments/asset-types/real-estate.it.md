# ![](../../../static/icons/asset-types/crowdfunding.png){: width="32" style="vertical-align: middle;" } P2P / Crowdfunding

Le piattaforme **P2P / Crowdfunding** permettono agli investitori di prestare importi relativamente piccoli a consumatori,
imprese o progetti immobiliari. L'investitore non acquista una quota di nulla: detiene un
**prestito**, che in genere paga interessi fissi o variabili e ha una data di scadenza definita.

LibreFolio modella questi strumenti come la **famiglia Crowdfunding** dei
[tipi di asset](index.md#crowdfunding-family): il generico `CROWDFUND` e la sua specializzazione
immobiliare, `CROWDFUND_REAL_ESTATE`.

---

## 🔑 Caratteristiche principali

| Proprietà | Dettaglio |
|----------|--------|
| **Codici in LibreFolio** | `CROWDFUND` — prestiti P2P e alle imprese, e il membro generico della famiglia · `CROWDFUND_REAL_ESTATE` — prestiti garantiti da progetti immobiliari |
| **Prezzo** | Non negoziati in borsa — il valore è tipicamente il capitale investito |
| **Valuta** | Denominati nella valuta operativa della piattaforma |
| **Reddito** | Pagamenti periodici di interessi (mensili, trimestrali o alla scadenza) |
| **Liquidità** | Molto bassa — i fondi sono bloccati fino alla scadenza o al riacquisto |
| **Provider tipici** | Investimento programmato, o prezzi inseriti manualmente nell'[editor dati](../../../user/assets/detail/data-editor.md) |

---

## 🏷️ Quale codice scegliere {: #which-code-to-choose }

| | Codice | Sceglilo quando il prestito… |
|:---:|:---|:---|
| ![](../../../static/icons/asset-types/crowdfunding-real-estate.png){: width="32" } | `CROWDFUND_REAL_ESTATE` | finanzia un progetto immobiliare |
| ![](../../../static/icons/asset-types/crowdfunding.png){: width="32" } | `CROWDFUND` | va a consumatori o imprese — oppure il suo scopo non è dichiarato |

La regola riguarda ciò che il prestito finanzia, non la piattaforma. In caso di dubbio, `CROWDFUND` — il
residuo della famiglia — è la scelta sicura; il prezzo da pagare è che, nella
[vista contenuto](index.md#two-views-of-one-instrument), il prestito non conta più come immobiliare.

---

## 📊 Come funziona

### 🏗️ Crowdfunding immobiliare — `CROWDFUND_REAL_ESTATE`

1. Una piattaforma elenca un progetto immobiliare che necessita di finanziamento
2. Più investitori contribuiscono con piccoli importi (tipicamente 500–10.000 €)
3. Il progetto paga interessi sul capitale investito
4. Alla scadenza, il capitale viene restituito (se il progetto ha successo)

### 💸 Prestiti P2P — `CROWDFUND`

1. I mutuatari — consumatori o imprese — richiedono prestiti tramite una piattaforma
2. Gli investitori finanziano porzioni di prestiti
3. I mutuatari rimborsano capitale + interessi durante la durata del prestito
4. La piattaforma distribuisce i pagamenti agli investitori

---

## ⚠️ Fattori di rischio

| Rischio | Descrizione |
|------|-------------|
| **Rischio di default** | Il mutuatario/progetto potrebbe non rimborsare |
| **Rischio di liquidità** | Non è possibile vendere prima della scadenza (a differenza delle azioni) |
| **Rischio piattaforma** | La piattaforma stessa potrebbe fallire |
| **Rischio di concentrazione** | Ogni investimento è un singolo progetto/mutuatario |

---

## 🏠 Tre modi di detenere immobili {: #three-ways-to-hold-property }

"Immobiliare" designa tre strumenti diversi in LibreFolio, e ciò che li separa è la
differenza tra **possedere** e **prestare**:

| | Codice | Cosa detieni | Natura del diritto |
|:---:|:---|:---|:---|
| ![](../../../static/icons/asset-types/real-estate.png){: width="32" } | `REAL_ESTATE` | Una quota di un REIT o di un altro veicolo immobiliare quotato | Equity: possiedi parte del reddito e del valore dell'immobile |
| ![](../../../static/icons/asset-types/etf-real-estate.png){: width="32" } | `ETF_REAL_ESTATE` | Una quota di un ETF che detiene tali veicoli | Equity, attraverso un paniere |
| ![](../../../static/icons/asset-types/crowdfunding-real-estate.png){: width="32" } | `CROWDFUND_REAL_ESTATE` | Un prestito a un progetto immobiliare, tramite una piattaforma | Debito: ti sono dovuti interessi e capitale, rimborsati dal progetto |

Tutti e tre contengono immobili, quindi la [vista contenuto](index.md#two-views-of-one-instrument) li
colloca nella stessa classe, e il loro badge è verde acqua. I diritti, tuttavia, si comportano in
modo molto diverso quando i mercati calano — ed è qui che gli scenari di stress prendono strade diverse.

---

## 🌪️ Negli scenari di stress {: #in-stress-scenarios }

Uno scenario di stress che sottopone il portafoglio a shock per classe di asset assegna a ogni codice il proprio
bucket. Nelle impostazioni predefinite dei due scenari integrati per classe di asset:

| Codice | Crollo azionario | Risk-off globale |
|:---|---:|---:|
| `REAL_ESTATE` | −20 % | −15 % |
| `ETF_REAL_ESTATE` | −20 % | −15 % |
| `CROWDFUND_REAL_ESTATE` | −10 % | −10 % |
| `CROWDFUND` | −10 % | −10 % |

`CROWDFUND_REAL_ESTATE` subisce uno shock in quanto **prestito**, non in quanto immobile che vi sta dietro.
Gli immobili quotati vengono riprezzati ogni giorno di negoziazione, quindi un sell-off li raggiunge
subito. Un prestito di crowdfunding è illiquido e non soggetto a mark-to-market — nulla lo
riprezza la mattina successiva — e il suo rischio è un **default che arriva in ritardo**; in uno
shock istantaneo si muove quindi come il resto di `CROWDFUND`.

!!! warning "Limite noto: una crisi immobiliare prolungata"

    Uno shock ipotetico è un'affermazione a periodo singolo: non contiene il tempo. Il rischio di
    credito dei prestiti garantiti da immobili è proprio il tipo che si accumula nel tempo, mentre
    una crisi immobiliare si protrae — quindi il −10 % **sottostima** tale rischio in una crisi
    prolungata. Ogni shock di bucket è modificabile: se è quello lo scenario che vuoi testare,
    aumenta tu stesso il bucket `CROWDFUND_REAL_ESTATE`.

Come vengono applicati i bucket, e cosa succede a quelli che non configuri, è spiegato in
[Shock ipotetico](../../technical-analysis/risk-metrics/hypothetical-shock.md).

---

## 🔧 Modellazione in LibreFolio

Il provider **Investimento programmato** è progettato per questi strumenti. Dalla programmazione che
configuri, genera:

- **[Eventi di interesse](../asset-events/interest.md)** — pagamenti periodici di interessi, quando la
  programmazione è impostata per generarli
- **[Eventi di regolamento alla scadenza](../asset-events/maturity-settlement.md)** — la restituzione finale del capitale
  alla fine della durata

Gli **[eventi di rettifica prezzo](../asset-events/price-adjustment.md)** che registri tu stesso — una
svalutazione quando un progetto va male — vengono applicati al valore che calcola.

---

## 🔗 Correlati

- 📊 **[Tipi di asset](index.md)** — La tassonomia a due livelli e come si aggregano i sottotipi
- 📈 **[Eventi di interesse](../asset-events/interest.md)** — Come funziona la maturazione degli interessi
- 🏁 **[Regolamento alla scadenza](../asset-events/maturity-settlement.md)** — Restituzione del capitale a fine vita
- 📅 **[Convenzioni di calcolo dei giorni](../../fundamentals/day-count.md)** — Come vengono calcolati i periodi di interesse
- ⚡ **[Shock ipotetico](../../technical-analysis/risk-metrics/hypothetical-shock.md)** — Come gli scenari di stress sottopongono a shock i bucket per classe di asset
