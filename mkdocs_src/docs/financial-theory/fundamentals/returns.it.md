# 📈 Rendimenti e tassi di crescita

Questa pagina copre le basi matematiche dei **rendimenti degli investimenti** — come misurare, confrontare e annualizzare i tassi di crescita. Questi concetti sono utilizzati in tutti gli strumenti di misurazione e nelle analisi di portafoglio di LibreFolio.

---

## 📊 Rendimento semplice (discreto)

Il **rendimento semplice** su un periodo è la variazione percentuale:

$$
R_{simple} = \frac{P_{end} - P_{start}}{P_{start}} = \frac{P_{end}}{P_{start}} - 1
$$

!!! example

    Se EUR/USD passa da 1.10 a 1.14:

    $$R = \frac{1.14 - 1.10}{1.10} = 0.0364 = 3.64\%$$

### 📊 Proprietà

- **Intuitivo**: rappresenta direttamente "quanto hai guadagnato/perso"
- **Non additivo**: non puoi semplicemente sommare i rendimenti semplici tra periodi per ottenere il rendimento totale
- **Capitalizzazione**: i rendimenti multi-periodo devono essere **moltiplicati**, non sommati

$$
R_{total} = (1 + R_1)(1 + R_2) \cdots (1 + R_n) - 1
$$

---

## 📐 Rendimento logaritmico (continuo)

Il **rendimento logaritmico** è il logaritmo naturale del rapporto tra i prezzi:

$$
r_{log} = \ln\left(\frac{P_{end}}{P_{start}}\right) = \ln(P_{end}) - \ln(P_{start})
$$

### 📊 Proprietà

- **Additivo nel tempo**: rendimento logaritmico totale = somma dei rendimenti logaritmici dei sotto-periodi

$$
r_{total} = r_1 + r_2 + \cdots + r_n
$$

- **Simmetrico**: un movimento del +5% seguito da un movimento del −5% ritorna esattamente al punto di partenza
- **Approssimativamente uguale** al rendimento semplice per valori piccoli: $r_{log} \approx R_{simple}$ quando $R_{simple}$ è piccolo

### 🔄 Conversione

$$
r_{log} = \ln(1 + R_{simple}) \qquad R_{simple} = e^{r_{log}} - 1
$$

---

## 📅 Rendimento annualizzato

Per confrontare i rendimenti su periodi di tempo diversi, li **annualizziamo** — proiettando il tasso di crescita osservato su un anno intero.

### 📈 Tasso di crescita annuo composto (CAGR)

Il metodo di annualizzazione più comune. Dato un rendimento totale su $d$ giorni di calendario:

$$
R_{annual} = \left(\frac{P_{end}}{P_{start}}\right)^{365/d} - 1
$$

Questo è ciò che visualizza lo [strumento Misure](../../user/fx/detail/measures.md) di LibreFolio.

!!! example

    EUR/USD passa da 1.10 a 1.14 in 90 giorni:

    $$R_{annual} = \left(\frac{1.14}{1.10}\right)^{365/90} - 1 = (1.0364)^{4.056} - 1 \approx 15.5\%$$

### 📐 Rendimento logaritmico annualizzato

Per i rendimenti logaritmici, l'annualizzazione è semplicemente una scalatura:

$$
r_{annual} = r_{log} \times \frac{365}{d}
$$

Questa linearità è uno dei principali vantaggi dei rendimenti logaritmici nella finanza quantitativa.

---

## 🔄 Relazione tra rendimenti semplici e logaritmici

| Proprietà | Rendimento semplice $R$ | Rendimento logaritmico $r$ |
|----------|:---:|:---:|
| **Capitalizzazione** | Moltiplicativa: $(1+R_1)(1+R_2)$ | Additiva: $r_1 + r_2$ |
| **Simmetria** | Asimmetrica: +10% poi −10% ≠ 0 | Simmetrica: +10% poi −10% = 0 |
| **Annualizzazione** | $(1+R)^{365/d} - 1$ | $r \times 365/d$ |
| **Rendimenti di portafoglio** | La somma ponderata funziona ✅ | La somma ponderata non funziona ❌ |
| **Serie temporali** | Non additivo ❌ | Additivo ✅ |
| **Interpretazione** | "Ho guadagnato il 5%" | "Il tasso di crescita logaritmico era 0.0488" |

!!! tip "Quando usare quale?"

    - **Rendimenti semplici** per la reportistica agli utenti e il calcolo dei rendimenti a livello di portafoglio
    - **Rendimenti logaritmici** per l'analisi statistica, la stima della volatilità e i modelli di serie temporali

---

## 🔁 Rendimento rolling {: #rolling-return }

Un **rendimento rolling** è il rendimento semplice delle sezioni precedenti, misurato su una finestra mobile lungo la serie: un valore per data, ciascuno dei quali guarda indietro sullo stesso intervallo. Due funzionalità della pagina di un asset lo calcolano, e differiscono nel modo in cui viene contato l'intervallo — in sedute o in giorni di calendario. Il pulsante guida 📖 sulla scheda del segnale **Rolling Return** apre questa pagina.

### 📊 Su una finestra di sedute {: #rolling-return-sessions }

Il segnale **Rolling Return** del pannello Segnali, nella famiglia di rischio, legge la serie preparata dei rendimenti dell'asset, nella valuta del grafico: un rendimento semplice per **seduta**, un giorno in cui l'asset ha una quotazione propria. Un prezzo memorizzato in un fine settimana o in un giorno festivo di mercato che ripete solo la chiusura precedente non è una seduta. Con $V_t$ il valore alla seduta $t$ e $r_t = V_t / V_{t-1} - 1$, il rendimento rolling su una finestra di $w$ sedute è

$$
R_t^{(w)} = \prod_{k=0}^{w-1} \left(1 + r_{t-k}\right) - 1 = \frac{V_t}{V_{t-w}} - 1
$$

calcolato tramite logaritmi, $R_t^{(w)} = \exp\left(\sum_{k=0}^{w-1} \ln(1 + r_{t-k})\right) - 1$, in modo che la finestra possa scorrere un passo alla volta. La finestra $w$ — 30 per impostazione predefinita, da 1 a 500 — conta le osservazioni di rendimento, non i giorni di calendario: 30 sedute di uno strumento quotato nei giorni feriali coprono circa sei settimane, 30 sedute di uno quotato ogni giorno coprono 30 giorni. Il primo valore appare quando sono disponibili $w + 1$ valutazioni.

### 🗓️ Su una finestra di giorni di calendario {: #rolling-return-calendar }

La modalità **Rolling Return** del grafico misura ogni data rispetto alla chiusura esattamente $N$ giorni di calendario prima. Con $\hat{P}(d)$ la chiusura determinata del giorno di calendario $d$ — l'ultima chiusura disponibile a o prima di $d$, convertita nella valuta del grafico, in modo che un fine settimana o un giorno festivo legga la seduta precedente — il rendimento nel giorno $d$ è

$$
R^{[N]}(d) = \frac{\hat{P}(d)}{\hat{P}(d - N)} - 1
$$

Le preimpostazioni **1W**, **1M**, **3M** e **1Y** impostano $N$ a 7, 30, 90 e 365 giorni; una finestra personalizzata conta 7 giorni a settimana, 30 al mese e 365 all'anno. Un punto viene lasciato vuoto, mai stimato, quando una delle estremità non ha una chiusura determinata o una chiusura non positiva; quando nessun punto dell'intervallo può essere calcolato, il risultato non è disponibile. Ogni punto riporta la data di riferimento richiesta e le date del prezzo e del tasso di cambio effettivamente utilizzati — vedi il [Grafico interattivo](../../user/assets/detail/chart.md#rolling-return).

### ⚖️ Sedute o giorni di calendario {: #sessions-or-calendar-days }

Entrambe le misure sono rendimenti semplici solo sul prezzo: nessuna aggiunge dividendi, cedole o flussi di cassa, e nessuna è annualizzata. Rispondono a domande leggermente diverse:

| | Finestra di sedute | Finestra di giorni di calendario |
|---|---|---|
| Intervallo | $w$ quotazioni, qualunque tempo coprano | esattamente $N$ giorni, qualunque sia il ritmo di quotazione |
| Definito su | le sedute dell'asset | ogni data del grafico |
| Confronto tra due asset | uguale $w$ può significare intervalli diversi | uguale $N$ significa sempre lo stesso intervallo |
| Un giorno di mercato chiuso a una delle estremità | non può verificarsi: si usano solo le sedute | ricondotto all'ultima chiusura precedente |

Per confrontare un rendimento rolling con uno su un intervallo diverso, annualizzalo con la formula CAGR sopra, dove $d$ è l'intervallo in giorni di calendario — tenendo presente la trappola sui periodi molto brevi di seguito.

---

## 📏 Convenzioni di conteggio dei giorni

Il numero di giorni $d$ può essere calcolato in modo diverso a seconda della convenzione:

- **Actual/365**: giorni di calendario (la convenzione usata da LibreFolio)
- **Actual/360**: giorni di calendario su un anno di 360 giorni (comune nei mercati monetari)
- **30/360**: presuppone mesi di 30 giorni e un anno di 360 giorni

Per maggiori dettagli, vedi [Convenzioni di conteggio dei giorni](day-count.md).

---

## 💰 Metodi di rendimento di portafoglio

Quando un portafoglio ha **flussi di cassa** (depositi, prelievi), una singola formula di rendimento non è sufficiente, perché iniezioni o prelievi di capitale diluirebbero o gonfierebbero artificialmente il rendimento percentuale.

Per risolvere questo problema, vengono utilizzate metriche di performance avanzate:
- **TWRR (Time-Weighted Rate of Return):** Isola la performance degli asset, ignorando la tempistica dei flussi di cassa dell'investitore.
- **MWRR (Money-Weighted Rate of Return):** Misura la performance personale dell'investitore, tenendo conto della tempistica dei flussi di cassa.

Per un approfondimento su come funzionano queste metriche, perché differiscono e come LibreFolio le utilizza, vedi il capitolo dedicato [Metriche di performance](../technical-analysis/performance-metrics/index.md).

---

## ⚠️ Insidie

1. **Periodi molto brevi**: annualizzare un rendimento di 3 giorni può produrre cifre fuorvianti (ad es., un movimento dello 0.1% in 3 giorni → 12.5% annualizzato)
2. **Prezzi negativi**: i rendimenti logaritmici non sono definiti per valori negativi — non è un problema per i tassi di cambio
3. **Frequenza di capitalizzazione**: il CAGR presuppone la capitalizzazione continua; gli strumenti del mondo reale possono capitalizzare giornalmente, mensilmente o trimestralmente
