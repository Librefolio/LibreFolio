# 📊 Tipi di asset

Gli strumenti differiscono nel mondo reale — come sono prezzati, se generano reddito, come sono
tassati — e le pagine di dettaglio di seguito coprono queste differenze. All'interno di LibreFolio ogni asset porta
esattamente un **tipo di asset**, e il tipo è una **classificazione** letta in tre punti: sceglie
l'icona e l'etichetta che vedi, decide dove l'asset viene conteggiato nei
grafici di [allocazione](../../portfolio-theory/asset-allocation.md), e assegna il nome al bucket in cui l'asset
ricade quando uno [scenario di stress](../../technical-analysis/risk-metrics/hypothetical-shock.md)
sottopone il portafoglio a shock per classe di asset. `INDEX` è, inoltre, l'unico tipo che non accetta
transazioni.

La tassonomia ha **due livelli**. La maggior parte dei tipi è autonoma; due di essi — **ETF** e
**Crowdfunding** — sono **famiglie**, i cui membri indicano anche cosa lo strumento *contiene*.

---

## 📋 Tipi di base {: #base-types }

| | Tipo | Codice | Descrizione | |
|:---:|:---|:---|---|:---:|
| ![](../../../static/icons/asset-types/stock.png){: width="32" } | **Azione** | `STOCK` | Azioni di una singola società. I prezzi sono generalmente recuperati da borse pubbliche. | [📖](stocks.md) |
| ![](../../../static/icons/asset-types/etf.png){: width="32" } | **ETF** | `ETF` | ETF di contenuto misto o non specificato (bilanciato, multi-asset) — il membro generico della [famiglia ETF](#etf-family). | [📖](etfs.md) |
| ![](../../../static/icons/asset-types/bond.png){: width="32" } | **Obbligazione** | `BOND` | Titoli a reddito fisso che rappresentano un prestito a un mutuatario (governativo o societario). | [📖](bonds.md) |
| ![](../../../static/icons/asset-types/crypto.png){: width="32" } | **Cripto** | `CRYPTO` | Valute digitali e token (Bitcoin, Ethereum, ecc.). | [📖](crypto.md) |
| ![](../../../static/icons/asset-types/fund.png){: width="32" } | **Fondo** | `FUND` | Fondi comuni di investimento e altri fondi di investimento gestiti professionalmente. | [📖](mutual-fund.md) |
| ![](../../../static/icons/asset-types/crowdfunding.png){: width="32" } | **Crowdfund** | `CROWDFUND` | Prestiti di crowdfunding peer-to-peer e business, spesso valutati tramite pagamenti programmati di interessi — il membro generico della [famiglia Crowdfunding](#crowdfunding-family). | [📖](real-estate.md) |
| ![](../../../static/icons/asset-types/hold.png){: width="32" } | **Asset detenuto** | `HOLD` | Asset senza prezzatura automatica di mercato: arte, oggetti da collezione, quote di società non quotate. | — |
| ![](../../../static/icons/asset-types/commodity.png){: width="32" } | **Materie prime** | `COMMODITY` | Beni fisici e le loro esposizioni dirette: oro, petrolio, prodotti agricoli. | [📖](commodities.md) |
| ![](../../../static/icons/asset-types/real-estate.png){: width="32" } | **Immobiliare** | `REAL_ESTATE` | Esposizione immobiliare: REIT e altri veicoli immobiliari quotati. | [📖](real-estate.md#three-ways-to-hold-property) |
| ![](../../../static/icons/asset-types/index.png){: width="32" } | **Indice** | `INDEX` | Indici di mercato (S&amp;P 500, MSCI World) usati come benchmark di riferimento — non negoziabili direttamente, quindi non sono consentite transazioni. | [📖](index-benchmark.md) |
| ![](../../../static/icons/asset-types/other.png){: width="32" } | **Altro** | `OTHER` | Qualsiasi asset che i tipi precedenti non descrivono. | [📖](other.md) |

Un tipo è **un'etichetta per asset**: un ETF bilanciato viene conteggiato per intero sotto `ETF`, mai suddiviso nelle sue
parti azionarie e obbligazionarie. Guardare *attraverso* uno strumento è compito delle sue distribuzioni settoriali e geografiche,
non del suo tipo.

---

## 🧬 Famiglie e sottotipi {: #families-and-subtypes }

Un sottotipo risponde a una sola domanda: **quale tipo di base contiene questo strumento?** Il secondo
livello non è quindi una tassonomia parallela — *è* l'insieme dei tipi di base, visti attraverso un wrapper.
Il membro generico di ciascuna famiglia (`ETF`, `CROWDFUND`) resta una scelta valida a sé stante: è
il residuo per contenuto misto o non specificato, e il menu dei tipi lo elenca per primo nella sua famiglia, con
un suggerimento che lo dice.

L'icona di un sottotipo è l'icona della sua famiglia con un piccolo disco nell'angolo — una **pastiglia** — che mostra il suo
contenuto: il contenitore dice cosa lo strumento *è*, la pastiglia cosa *contiene*. La pastiglia è
l'icona del tipo di base contenuto dal sottotipo; l'ETF monetario, che non contiene alcun tipo di base,
prende in prestito l'icona della liquidità. Ovunque LibreFolio disegni l'icona del tipo, un sottotipo mostra il suo composito —
un asset con un'icona personalizzata mantiene la propria.

### 📦 Famiglia ETF {: #etf-family }

| | Tipo | Codice | Contiene | Confluisce in |
|:---:|:---|:---|:---|:---|
| ![](../../../static/icons/asset-types/etf.png){: width="32" } | **ETF** | `ETF` | Contenuto misto o non specificato — il membro generico | `ETF` (sé stesso) |
| ![](../../../static/icons/asset-types/etf-stock.png){: width="32" } | **ETF azionario** | `ETF_STOCK` | Azioni | `STOCK` |
| ![](../../../static/icons/asset-types/etf-bond.png){: width="32" } | **ETF obbligazionario** | `ETF_BOND` | Obbligazioni | `BOND` |
| ![](../../../static/icons/asset-types/etf-commodity.png){: width="32" } | **ETF materie prime** | `ETF_COMMODITY` | Materie prime | `COMMODITY` |
| ![](../../../static/icons/asset-types/etf-real-estate.png){: width="32" } | **ETF immobiliare** | `ETF_REAL_ESTATE` | Immobiliare | `REAL_ESTATE` |
| ![](../../../static/icons/asset-types/etf-crypto.png){: width="32" } | **ETF cripto** | `ETF_CRYPTO` | Asset cripto | `CRYPTO` |
| ![](../../../static/icons/asset-types/etf-liquidity.png){: width="32" } | **ETF monetario** | `ETF_MONETARY` | Strumenti del mercato monetario | `ETF_MONETARY` (sé stesso — vedi [sotto](#two-views-of-one-instrument)) |

Lo strumento stesso è descritto nella pagina [ETF](etfs.md).

### 🤝 Famiglia Crowdfunding {: #crowdfunding-family }

| | Tipo | Codice | Contiene | Confluisce in |
|:---:|:---|:---|:---|:---|
| ![](../../../static/icons/asset-types/crowdfunding.png){: width="32" } | **Crowdfund** | `CROWDFUND` | Prestiti P2P e business — il membro generico | `CROWDFUND` (sé stesso) |
| ![](../../../static/icons/asset-types/crowdfunding-real-estate.png){: width="32" } | **Crowdfunding immobiliare** | `CROWDFUND_REAL_ESTATE` | Prestiti garantiti da progetti immobiliari | `REAL_ESTATE` |

Entrambi sono descritti nella pagina [P2P / Crowdfunding](real-estate.md).

---

## ⚖️ Due viste di un unico strumento {: #two-views-of-one-instrument }

I due livelli rispondono a due domande diverse, e LibreFolio li tiene separati.

- **La vista contenitore** — *che tipo di strumento è?* — è la famiglia. Il menu dei tipi raggruppa per
  famiglia, l'icona mantiene la forma della famiglia, e l'etichetta dice *ETF azionario*: quello è lo strumento
  che possiedi effettivamente.
- **La vista contenuto** — *a cosa sono esposto?* — è la confluenza: un sottotipo appartiene al tipo di base
  che contiene. Un ETF azionario e un'azione sono entrambi esposizione azionaria, e alla domanda *sono
  diversificato quanto penso?* il wrapper non dice nulla.

Formalmente, sia $c$ la mappa che manda ogni sottotipo al tipo di base che contiene, e ogni altro tipo — inclusi i
membri generici e `ETF_MONETARY` — a sé stesso. Il peso di una classe di contenuto $k$ è quindi

$$
W_k = \sum_{i \,:\, c(\tau_i) = k} w_i
$$

dove $\tau_i$ è il tipo della posizione $i$ e $w_i$ il suo peso nel portafoglio. La stessa somma presa
sulla mappa delle famiglie invece che su $c$ — ogni sottotipo ETF a `ETF`, `CROWDFUND_REAL_ESTATE` a
`CROWDFUND`, ogni altro tipo a sé stesso — dà il peso di ciascuna famiglia, la controparte della vista contenitore.
Il badge del tipo segue il contenuto: un badge *ETF azionario* è blu, come un badge *Azione*. Come la
dashboard presenta l'allocazione per tipo è descritto nel
[Pannello di allocazione](../../../user/dashboard/charts.md#allocation-panel).

Due eccezioni meritano una frase ciascuna:

- **`ETF_MONETARY` confluisce in sé stesso.** Un fondo del mercato monetario non ha un tipo di base in cui confluire: la liquidità è
  un saldo di conto, non un asset che viene acquistato, quindi non è un tipo di asset. `ETF` seppellirebbe il
  fondo tra i fondi misti, e *Liquidità* non è affatto un tipo di asset — è il bucket di allocazione
  in cui LibreFolio conteggia separatamente il tuo saldo di cassa. Nella vista contenuto l'ETF monetario
  è quindi una classe a sé stante, e il suo badge ha un colore proprio.
- **`CROWDFUND_REAL_ESTATE` ha due risposte.** Nella vista contenuto contiene immobili e
  appartiene alla classe Immobiliare; negli scenari di stress viene sottoposto a shock come il prestito che è.

---

## 🌪️ Tipi negli scenari di stress {: #types-in-stress-scenarios }

Uno scenario di stress che sottopone il portafoglio a shock per classe di asset tratta ogni codice come un **bucket a sé** —
lì, un sottotipo non viene mai aggregato nella sua classe di contenuto. Nei valori predefiniti dei due scenari integrati
per classe di asset, *Crash azionario* e *Risk-off globale*, ogni sottotipo ETF porta esattamente lo
shock del tipo di base che detiene, mentre il generico `ETF` mantiene uno shock misto proprio, perché
il suo contenuto non è specificato; `ETF_MONETARY` non viene sottoposto a shock.

L'unica deviazione deliberata è `CROWDFUND_REAL_ESTATE`, che si muove come `CROWDFUND` anziché
come `REAL_ESTATE`: un prestito di crowdfunding è illiquido e non è mark-to-market, e il suo rischio è un
default che arriva in ritardo. Il ragionamento, e il suo limite noto, sono nella pagina
[P2P / Crowdfunding](real-estate.md#in-stress-scenarios).

Ogni shock di bucket di quegli scenari è modificabile, e un bucket lasciato non configurato viene sottoposto a
shock pari a zero — vedi [Shock ipotetico](../../technical-analysis/risk-metrics/hypothetical-shock.md#what-you-did-not-configure).

---

## 🔗 Correlati

- 💸 **[Tipi di transazione](../transaction-types/index.md)** — Operazioni che influiscono sul tuo portafoglio
- 📅 **[Eventi sugli asset](../asset-events/index.md)** — Azioni societarie che influiscono sui prezzi degli asset
- 💰 **[Tassazione](../../fundamentals/taxation.md)** — Implicazioni fiscali per classe di asset
- 🧭 **[Asset Allocation](../../portfolio-theory/asset-allocation.md)** — Distribuire capitale tra classi di asset
- ⚡ **[Shock ipotetico](../../technical-analysis/risk-metrics/hypothetical-shock.md)** — Come vengono sottoposti a shock i bucket per classe di asset
