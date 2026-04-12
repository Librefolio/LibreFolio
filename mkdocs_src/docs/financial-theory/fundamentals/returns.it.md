# 📈 Rendimenti e Tassi di Crescita

Questa pagina tratta le basi matematiche dei **rendimenti degli investimenti**: come misurare, confrontare e annualizzare i tassi di crescita. Questi concetti sono utilizzati in tutti gli strumenti di misurazione e nelle analisi di portafoglio di LibreFolio.

---

## 📊 Rendimento Semplice (Discreto)

Il **rendimento semplice** in un periodo è la variazione percentuale:

$$
R_{simple} = \frac{P_{end} - P_{start}}{P_{start}} = \frac{P_{end}}{P_{start}} - 1
$$

!!! example

    Se EUR/USD passa da 1.10 a 1.14:

    $$R = \frac{1.14 - 1.10}{1.10} = 0.0364 = 3.64\%$$

### 📊 Proprietà

- **Intuitivo**: rappresenta direttamente "quanto si è guadagnato/perso"
- **Non additivo**: non è possibile sommare semplicemente i rendimenti semplici tra diversi periodi per ottenere il rendimento totale
- **Capitalizzazione**: i rendimenti multi-periodo devono essere **moltiplicati**, non sommati

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

- **Additivo nel tempo**: il rendimento logaritmico totale = somma dei rendimenti logaritmici dei sotto-periodi

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

Per confrontare i rendimenti in periodi di tempo differenti, li **annualizziamo**, proiettando il tasso di crescita osservato su un anno intero.

### 📈 Tasso di Crescita Annuale Composto (CAGR)

Il metodo di annualizzazione più comune. Dato un rendimento totale su $d$ giorni solari:

$$
R_{annual} = \left(\frac{P_{end}}{P_{start}}\right)^{365/d} - 1
$$

Questo è ciò che visualizza lo strumento [Measures](../../user/fx/detail/measures.md) di LibreFolio.

!!! example

    EUR/USD passa da 1.10 a 1.14 in 90 giorni:

    $$R_{annual} = \left(\frac{1.14}{1.10}\right)^{365/90} - 1 = (1.0364)^{4.056} - 1 \approx 15.5\%$$

### 📐 Rendimento Logaritmico Annualizzato

Per i rendimenti logaritmici, l'annualizzazione è una semplice scalatura:

$$
r_{annual} = r_{log} \times \frac{365}{d}
$$

Questa linearità è uno dei vantaggi chiave dei rendimenti logaritmici nella finanza quantitativa.

---

## 🔄 Relazione tra Rendimenti Semplici e Logaritmici

| Proprietà | Rendimento Semplice $R$ | Rendimento Logaritmico $r$ |
|----------|:---:|:---:|
| **Capitalizzazione** | Moltiplicativa: $(1+R_1)(1+R_2)$ | Additiva: $r_1 + r_2$ |
| **Simmetria** | Asimmetrica: +10% seguito da −10% ≠ 0 | Simmetrica: +10% seguito da −10% = 0 |
| **Annualizzazione** | $(1+R)^{365/d} - 1$ | $r \times 365/d$ |
| **Rendimenti di portafoglio** | La somma ponderata funziona ✅ | La somma ponderata non funziona ❌ |
| **Serie temporali** | Non additiva ❌ | Additiva ✅ |
| **Interpretazione** | "Ho guadagnato il 5%" | "Il tasso di crescita logaritmico era 0.0488" |

!!! tip "Quale usare?"

    - **Rendimenti semplici** per il reporting agli utenti e per il calcolo dei rendimenti a livello di portafoglio
    - **Rendimenti logaritmici** per l'analisi statistica, la stima della volatilità e i modelli di serie temporali

---

## 📏 Convenzioni di calcolo dei giorni (Day Count Conventions)

Il numero di giorni $d$ può essere calcolato diversamente a seconda della convenzione:

- **Actual/365**: Giorni solari (utilizzato da LibreFolio)
- **Actual/360**: Giorni solari su un anno di 360 giorni (comune nei mercati monetari)
- **30/360**: Ipotizza mesi di 30 giorni e un anno di 360 giorni

Per ulteriori dettagli, consultare [Day Count Conventions](day-count.md).

---

## ⚠️ Insidie

1. **Periodi molto brevi**: Annualizzare un rendimento di 3 giorni può produrre cifre fuorvianti (es. un movimento dello 0,1% in 3 giorni $\rightarrow$ 12,5% annualizzato)
2. **Prezzi negativi**: I rendimenti logaritmici non sono definiti per valori negativi — non è un problema per i tassi di cambio
3. **Frequenza di capitalizzazione**: Il CAGR presuppone una capitalizzazione continua; gli strumenti del mondo reale possono prevedere una capitalizzazione giornaliera, mensile o trimestrale
