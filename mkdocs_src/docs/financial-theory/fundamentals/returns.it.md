# 📈 Rendimenti e tassi di crescita

Questa pagina illustra i fondamenti matematici dei **rendimenti degli investimenti** — come misurare, confrontare e annualizzare i tassi di crescita. Questi concetti sono utilizzati in tutti gli strumenti di misurazione e nelle analisi di portafoglio di LibreFolio.

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

- **Intuitivo**: rappresenta direttamente «quanto hai guadagnato/perso»
- **Non additivo**: non è possibile sommare semplicemente i rendimenti semplici di più periodi per ottenere il rendimento totale
- **Capitalizzazione composta**: i rendimenti multiperiodali devono essere **moltiplicati**, non sommati

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

- **Additivo nel tempo**: rendimento logaritmico totale = somma dei rendimenti logaritmici dei sottoperiodi

$$
r_{total} = r_1 + r_2 + \cdots + r_n
$$

- **Simmetrico**: un movimento del +5% seguito da uno del −5% riporta esattamente al punto di partenza
- **Approssimativamente uguale** al rendimento semplice per valori piccoli: $r_{log} \approx R_{simple}$ quando $R_{simple}$ è piccolo

### 🔄 Conversione

$$
r_{log} = \ln(1 + R_{simple}) \qquad R_{simple} = e^{r_{log}} - 1
$$

---

## 📅 Rendimento annualizzato

Per confrontare rendimenti su periodi di tempo diversi, li **annualizziamo** — proiettando il tasso di crescita osservato su un anno intero.

### 📈 Tasso annuo di crescita composto (CAGR)

È il metodo di annualizzazione più comune. Dato un rendimento totale su $d$ giorni di calendario:

$$
R_{annual} = \left(\frac{P_{end}}{P_{start}}\right)^{365/d} - 1
$$

È quanto mostra lo [strumento Misure](../../user/fx/detail/measures.md) di LibreFolio.

!!! example

    EUR/USD passa da 1.10 a 1.14 in 90 giorni:

    $$R_{annual} = \left(\frac{1.14}{1.10}\right)^{365/90} - 1 = (1.0364)^{4.056} - 1 \approx 15.5\%$$

### 📐 Rendimento logaritmico annualizzato

Per i rendimenti logaritmici, l'annualizzazione è una semplice scalatura:

$$
r_{annual} = r_{log} \times \frac{365}{d}
$$

Questa linearità è uno dei principali vantaggi dei rendimenti logaritmici nella finanza quantitativa.

---

## 🔄 Relazione tra rendimento semplice e logaritmico

| Proprietà | Rendimento semplice $R$ | Rendimento logaritmico $r$ |
|----------|:---:|:---:|
| **Capitalizzazione composta** | Moltiplicativa: $(1+R_1)(1+R_2)$ | Additiva: $r_1 + r_2$ |
| **Simmetria** | Asimmetrica: +10% poi −10% ≠ 0 | Simmetrica: +10% poi −10% = 0 |
| **Annualizzazione** | $(1+R)^{365/d} - 1$ | $r \times 365/d$ |
| **Rendimenti di portafoglio** | La somma ponderata funziona ✅ | La somma ponderata non funziona ❌ |
| **Serie temporali** | Non additiva ❌ | Additiva ✅ |
| **Interpretazione** | «Ho guadagnato il 5%» | «Il tasso di crescita logaritmico era 0,0488» |

!!! tip "Quando usare quale?"

    - **Rendimenti semplici** per la reportistica verso gli utenti e per il calcolo dei rendimenti a livello di portafoglio
    - **Rendimenti logaritmici** per l'analisi statistica, la stima della volatilità e i modelli di serie temporali

---

## 🔁 Rendimento rolling {: #rolling-return }

Un **rendimento rolling** è il rendimento semplice delle sezioni precedenti, misurato su una finestra che scorre lungo la serie: un valore per ogni data, ciascuno calcolato a ritroso sullo stesso intervallo. LibreFolio misura tale intervallo in **giorni di calendario**, e un unico calcolo serve due funzioni della pagina di un asset: la modalità **Rolling Return** del grafico e il segnale **Rolling Return** del pannello Segnali, nella famiglia di rischio, che traccia la stessa serie sopra i prezzi. Il pulsante guida 📖 sulla scheda del segnale **Rolling Return** apre questa pagina.

### 🗓️ Su una finestra di giorni di calendario {: #rolling-return-calendar }

Ogni data è misurata rispetto alla chiusura esattamente $N$ giorni di calendario prima. Detta $\hat{P}(d)$ la chiusura risolta del giorno di calendario $d$ — l'ultima chiusura disponibile alla data $d$ o prima, convertita nella valuta del grafico, così che un fine settimana o un giorno festivo faccia riferimento alla seduta precedente — il rendimento al giorno $d$ è

$$
R^{[N]}(d) = \frac{\hat{P}(d)}{\hat{P}(d - N)} - 1
$$

Nella modalità del grafico, i preset **1W**, **1M**, **3M** e **1Y** impostano $N$ a 7, 30, 90 e 365 giorni, e una finestra personalizzata conta 7 giorni a settimana, 30 al mese e 365 all'anno; sulla scheda del segnale, $N$ è la **Finestra**, un numero intero di giorni — 30 per impostazione predefinita, minimo 1. Un punto viene lasciato vuoto, mai stimato, quando una delle due estremità non ha una chiusura risolta o ha una chiusura non positiva; se nessun punto dell'intervallo può essere calcolato, il risultato non è disponibile. La modalità del grafico mostra inoltre, per ogni punto, la data di riferimento richiesta e le date del prezzo e del tasso di cambio effettivamente utilizzati — vedi il [Grafico interattivo](../../user/assets/detail/chart.md#rolling-return).

### ⚖️ Giorni di calendario, non sedute {: #sessions-or-calendar-days }

La finestra è un intervallo di tempo, non un numero di quotazioni. Gli altri indicatori del pannello Segnali contano invece le quotazioni: gli [indicatori tecnici](../technical-analysis/indicators/index.md) contano le sedute, ovvero i giorni con una quotazione propria, mentre la volatilità rolling, l'indice di Sharpe e il beta contano le osservazioni di rendimento. Un numero uguale può quindi corrispondere a intervalli diversi — 30 sedute di uno strumento quotato nei giorni feriali coprono circa sei settimane, 30 sedute di uno strumento quotato ogni giorno coprono 30 giorni — mentre una finestra di $N$ giorni di calendario copre esattamente $N$ giorni su ogni asset, qualunque sia il suo ritmo di quotazione: due rendimenti rolling con lo stesso $N$ si riferiscono sempre allo stesso intervallo. Il rendimento è definito su ogni data del grafico, e un giorno di chiusura a una delle due estremità viene risolto con l'ultima chiusura precedente.

Il rendimento rolling è un rendimento semplice basato solo sul prezzo: non aggiunge dividendi, cedole o flussi di cassa e non è annualizzato. Per confrontarlo con un rendimento su un intervallo diverso, annualizzalo con la formula del CAGR sopra riportata, con $d$ uguale a $N$ — tenendo presente la trappola dei periodi molto brevi descritta più avanti.

---

## 📏 Convenzioni di conteggio dei giorni

Il numero di giorni $d$ può essere calcolato in modi diversi a seconda della convenzione:

- **Actual/365**: giorni di calendario (la convenzione usata da LibreFolio)
- **Actual/360**: giorni di calendario su un anno di 360 giorni (comune nei mercati monetari)
- **30/360**: assume mesi di 30 giorni e un anno di 360 giorni

Per maggiori dettagli, vedi [Convenzioni di conteggio dei giorni](day-count.md).

---

## 💰 Metodi di calcolo del rendimento di portafoglio

Quando un portafoglio presenta **flussi di cassa** (depositi, prelievi), una singola formula di rendimento non è sufficiente, perché apporti o prelievi di capitale diluirebbero o gonfierebbero artificialmente il rendimento percentuale.

Per risolvere questo problema si utilizzano metriche di performance avanzate:
- **TWRR (Time-Weighted Rate of Return, rendimento ponderato nel tempo):** isola la performance degli asset, ignorando la tempistica dei flussi di cassa dell'investitore.
- **MWRR (Money-Weighted Rate of Return, rendimento ponderato per il capitale):** misura la performance personale dell'investitore, tenendo conto della tempistica dei flussi di cassa.

Per un approfondimento su come funzionano queste metriche, perché differiscono e come LibreFolio le utilizza, vedi il capitolo dedicato [Metriche di performance](../technical-analysis/performance-metrics/index.md).

---

## ⚠️ Trappole

1. **Periodi molto brevi**: annualizzare un rendimento di 3 giorni può produrre cifre fuorvianti (ad es. un movimento dello 0,1% in 3 giorni → 12,5% annualizzato)
2. **Prezzi negativi**: i rendimenti logaritmici non sono definiti per valori negativi — non è un problema per i tassi di cambio
3. **Frequenza di capitalizzazione**: il CAGR presuppone una capitalizzazione continua; gli strumenti reali possono capitalizzare giornalmente, mensilmente o trimestralmente
