# 📈 Rendimenti e Tassi di Crescita

Questa pagina copre le basi matematiche dei **rendimenti degli investimenti** — come misurare, confrontare e annualizzare i tassi di crescita. Questi concetti sono utilizzati in tutti gli strumenti di misurazione e nelle analisi di portafoglio di LibreFolio.

---

## 📊 Rendimento Semplice (Discreto)

Il **rendimento semplice** in un periodo è la variazione percentuale:

$$
R_{simple} = \frac{P_{end} - P_{start}}{P_{start}} = \frac{P_{end}}{P_{start}} - 1
$$

!!! example

    Se EUR/USD passa da 1,10 a 1,14:

    $$R = \frac{1,14 - 1,10}{1,10} = 0,0364 = 3,64\%$$

### 📊 Proprietà

- **Intuitivo**: rappresenta direttamente "quanto si è guadagnato/perso"
- **Non additivo**: non è possibile sommare semplicemente i rendimenti semplici tra i periodi per ottenere il rendimento totale
- **Capitalizzazione**: i rendimenti su più periodi devono essere **moltiplicati**, non sommati

$$
R_{total} = (1 + R_1)(1 + R_2) \cdots (1 + R_n) - 1
$$

---

## 📐 Rendimento Logaritmico (Continuo)

Il **rendimento logaritmico** è il logaritmo naturale del rapporto tra i prezzi:

$$
r_{log} = \ln\left(\frac{P_{end}}{P_{start}}\right) = \ln(P_{end}) - \ln(P_{start})
$$

### 📊 Proprietà

- **Additivo nel tempo**: rendimento log totale = somma dei rendimenti log dei sotto-periodi

$$
r_{total} = r_1 + r_2 + \cdots + r_n
$$

- **Simmetrico**: un movimento del +5% seguito da un movimento del −5% riporta esattamente al punto di partenza
- **Approssimativamente uguale** al rendimento semplice per valori piccoli: $r_{log} \approx R_{simple}$ quando $R_{simple}$ è piccolo

### 🔄 Conversione

$$
r_{log} = \ln(1 + R_{simple}) \qquad R_{simple} = e^{r_{log}} - 1
$$

---

## 📅 Rendimento Annualizzato

Per confrontare i rendimenti tra diversi periodi di tempo, li **annualizziamo** — proiettando il tasso di crescita osservato su un intero anno.

### 📈 Tasso di Crescita Annuale Composto (CAGR)

Il metodo di annualizzazione più comune. Dato un rendimento totale su $d$ giorni solari:

$$
R_{annual} = \left(\frac{P_{end}}{P_{start}}\right)^{365/d} - 1
$$

Questo è ciò che visualizza lo [strumento Misure](../../user/fx/detail/measures.md) di LibreFolio.

!!! example

    EUR/USD passa da 1,10 a 1,14 in 90 giorni:

    $$R_{annual} = \left(\frac{1,14}{1,10}\right)^{365/90} - 1 = (1,0364)^{4,056} - 1 \approx 15,5\%$$

### 📐 Rendimento Log Annualizzato

Per i rendimenti logaritmici, l'annualizzazione è un semplice ridimensionamento:

$$
r_{annual} = r_{log} \times \frac{365}{d}
$$

Questa linearità è uno dei vantaggi chiave dei rendimenti logaritmici nella finanza quantitativa.

---

## 🔄 Relazione tra Rendimenti Semplici e Logaritmici

| Proprietà | Rendimento Semplice $R$ | Rendimento Log $r$ |
|----------|:---:|:---:|
| **Capitalizzazione** | Moltiplicativa: $(1+R_1)(1+R_2)$ | Additiva: $r_1 + r_2$ |
| **Simmetria** | Asimmetrica: +10% poi −10% ≠ 0 | Simmetrica: +10% poi −10% = 0 |
| **Annualizzazione** | $(1+R)^{365/d} - 1$ | $r \times 365/d$ |
| **Rendimenti portafoglio** | La somma ponderata è applicabile ✅ | La somma ponderata non è applicabile ❌ |
| **Serie temporali** | Non additiva ❌ | Additiva ✅ |
| **Interpretazione** | "Ho guadagnato il 5%" | "Il tasso di crescita log era 0,0488" |

!!! tip "Quale usare?"

    - **Rendimenti semplici** per i report agli utenti e per il calcolo dei rendimenti a livello di portafoglio
    - **Rendimenti logaritmici** per l'analisi statistica, la stima della volatilità e i modelli di serie temporali

---

## 📏 Convenzioni di Conteggio dei Giorni

Il numero di giorni $d$ può essere calcolato diversamente a seconda della convenzione:

- **Actual/365**: Giorni solari (quello usato da LibreFolio)
- **Actual/360**: Giorni solari su un anno di 360 giorni (comune nei mercati monetari)
- **30/360**: Assume mesi di 30 giorni e un anno di 360 giorni

Per maggiori dettagli, vedi [Convenzioni di Conteggio dei Giorni](day-count.md).

---

## 💰 Metodi di Rendimento del Portafoglio

Quando un portafoglio ha **flussi di cassa** (depositi, prelievi), una singola formula di rendimento non è sufficiente, poiché gli apporti o i prelievi di capitale diluirebbero o gonfierebbero artificialmente il rendimento percentuale.

Per risolvere questo problema, vengono utilizzate metriche di performance avanzate:
- **TWRR (Time-Weighted Rate of Return):** Isola la performance degli asset, ignorando il tempismo dei flussi di cassa dell'investitore.
- **MWRR (Money-Weighted Rate of Return):** Misura la performance personale dell'investitore, tenendo conto del tempismo dei flussi di cassa.

Per un approfondimento su come funzionano queste metriche, perché differiscono e come LibreFolio le utilizza, consulta il capitolo dedicato [Metriche di Performance](../technical-analysis/performance-metrics/index.md).

---

## ⚠️ Insidie

1. **Periodi molto brevi**: L'annualizzazione di un rendimento di 3 giorni può produrre cifre fuorvianti (es. un movimento dello 0,1% in 3 giorni → 12,5% annualizzato)
2. **Prezzi negativi**: I rendimenti logaritmici non sono definiti per valori negativi — non è un problema per i tassi FX
3. **Frequenza di capitalizzazione**: Il CAGR assume una capitalizzazione continua; gli strumenti reali possono prevedere una capitalizzazione giornaliera, mensile o trimestrale
