# 📈 Rendimenti e Tassi di Crescita

Questa pagina tratta le basi matematiche dei **rendimenti di investimento** — come misurare, confrontare e annualizzare i tassi di crescita. Questi concetti sono utilizzati in tutti gli strumenti di misurazione FX e nell'analisi del portafoglio di LibreFolio.

---

## 📊 Rendimento Semplice (Discreto)

Il **rendimento semplice** in un periodo è la variazione percentuale:

$$
R_{semplice} = \frac{P_{fine} - P_{inizio}}{P_{inizio}} = \frac{P_{fine}}{P_{inizio}} - 1
$$

!!! esempio
    Se EUR/USD si muove da 1.10 a 1.14:

    $$R = \frac{1.14 - 1.10}{1.10} = 0.0364 = 3.64\%$$

### 📊 Proprietà

- **Intuitivo**: rappresenta direttamente "l'ammontare del guadagno/perdita"
- **Non additivo**: non puoi semplicemente sommare i rendimenti semplici tra i periodi per ottenere il rendimento totale
- **Composizione**: i rendimenti multi-periodo devono essere **moltiplicati**, non sommati

$$
R_{totale} = (1 + R_1)(1 + R_2) \cdots (1 + R_n) - 1
$$

---

## 📐 Rendimento Logaritmico (Continuo)

Il **rendimento logaritmico** è il logaritmo naturale del rapporto tra prezzi:

$$
r_{log} = \ln\left(\frac{P_{fine}}{P_{inizio}}\right) = \ln(P_{fine}) - \ln(P_{inizio})
$$

### 📊 Proprietà

- **Additivo nel tempo**: il rendimento logaritmico totale = somma dei rendimenti logaritmici dei sotto-periodi

$$
r_{totale} = r_1 + r_2 + \cdots + r_n
$$

- **Simmetrico**: un movimento +5% seguito da −5% riporta esattamente al punto di partenza
- **Approssimativamente uguale** al rendimento semplice per valori piccoli: $r_{log} \approx R_{semplice}$ quando $R_{semplice}$ è piccolo

### 🔄 Conversione

$$
r_{log} = \ln(1 + R_{semplice}) \qquad R_{semplice} = e^{r_{log}} - 1
$$

---

## 📅 Rendimento Annualizzato

Per confrontare rendimenti su periodi diversi, li **annualizziamo** — proiettando il tasso di crescita osservato su un anno intero.

### 📈 Compound Annual Growth Rate (CAGR)

Il metodo di annualizzazione più comune. Dato un rendimento totale su $d$ giorni di calendario:

$$
R_{annuale} = \left(\frac{P_{fine}}{P_{inizio}}\right)^{365/d} - 1
$$

Questo è ciò che lo strumento [Misurazioni](../user/fx/detail/measures.md) di LibreFolio visualizza.

!!! esempio
    EUR/USD si muove da 1.10 a 1.14 in 90 giorni:

    $$R_{annuale} = \left(\frac{1.14}{1.10}\right)^{365/90} - 1 = (1.0364)^{4.056} - 1 \approx 15.5\%$$

### 📐 Rendimento Logaritmico Annualizzato

Per i rendimenti logaritmici, l'annualizzazione è semplicemente una scala:

$$
r_{annuale} = r_{log} \times \frac{365}{d}
$$

Questa linearità è uno dei principali vantaggi dei rendimenti logaritmici nella finanza quantitativa.

---

## 🔄 Relazione tra Rendimento Semplice e Logaritmico

| Proprietà | Rendimento Semplice $R$ | Rendimento Logaritmico $r$ |
|----------|:---:|:---:|
| **Composizione** | Moltiplicativo: $(1+R_1)(1+R_2)$ | Additivo: $r_1 + r_2$ |
| **Simmetria** | Asimmetrico: +10% poi −10% ≠ 0 | Simmetrico: +10% poi −10% = 0 |
| **Annualizzazione** | $(1+R)^{365/d} - 1$ | $r \times 365/d$ |
| **Rendimenti di portafoglio** | La somma pesata funziona ✅ | La somma pesata non funziona ❌ |
| **Serie temporali** | Non additivo ❌ | Additivo ✅ |
| **Interpretazione** | "Ho guadagnato il 5%" | "Il tasso di crescita logaritmica era 0.0488" |

!!! tip "Quando usare l'uno o l'altro?"
    - **Rendimenti semplici** per la reportistica agli utenti e il calcolo dei rendimenti a livello di portafoglio
    - **Rendimenti logaritmici** per l'analisi statistica, la stima della volatilità e i modelli di serie temporali

---

## 📏 Convenzioni di Conteggio dei Giorni

Il numero di giorni $d$ può essere calcolato in modo diverso a seconda della convenzione:

- **Actual/365**: giorni di calendario (quello che usa LibreFolio)
- **Actual/360**: giorni di calendario su un anno di 360 giorni (comune nei mercati monetari)
- **30/360**: presume mesi di 30 giorni e anno di 360 giorni

Per maggiori dettagli, vedere [Convenzioni di Conteggio dei Giorni](day-count.md).

---

## ⚠️ Insidie

1. **Periodi molto brevi**: annualizzare un rendimento di 3 giorni può produrre figure ingannevoli (es. un movimento dello 0.1% in 3 giorni → 12.5% annualizzato)
2. **Prezzi negativi**: i rendimenti logaritmici sono indefiniti per valori negativi — non un problema per i tassi di cambio
3. **Frequenza di composizione**: il CAGR presume composizione continua; gli strumenti reali possono comporsi giornalmente, mensilmente o trimestralmente
