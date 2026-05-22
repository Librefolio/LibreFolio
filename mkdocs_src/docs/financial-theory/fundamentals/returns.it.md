# 📈 Rendimenti e Tassi di Crescita

Questa pagina tratta le basi matematiche dei **rendimenti degli investimenti** — come misurare, confrontare e annualizzare i tassi di crescita. Questi concetti sono utilizzati in tutti gli strumenti di misurazione e nelle analisi del portafoglio di LibreFolio.

---

## 📊 Rendimento Semplice (Discreto)

Il **rendimento semplice** in un determinato periodo è la variazione percentuale:

$$
R_{simple} = \frac{P_{end} - P_{start}}{P_{start}} = \frac{P_{end}}{P_{start}} - 1
$$

!!! example

    Se EUR/USD passa da 1,10 a 1,14:

    $$R = \frac{1,14 - 1,10}{1,10} = 0,0364 = 3,64\%$$

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

- **Additivo nel tempo**: il rendimento logaritmico totale = somma dei rendimenti logaritmici dei singoli sotto-periodi

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

Per confrontare i rendimenti di periodi temporali diversi, li **annualizziamo** — proiettando il tasso di crescita osservato su un intero anno.

### 📈 Tasso di Crescita Annuale Composto (CAGR)

Il metodo di annualizzazione più comune. Dato un rendimento totale su $d$ giorni solari:

$$
R_{annual} = \left(\frac{P_{end}}{P_{start}}\right)^{365/d} - 1
$$

Questo è ciò che visualizza lo [strumento di misura](../../user/fx/detail/measures.md) di LibreFolio.

!!! example

    EUR/USD passa da 1,10 a 1,14 in 90 giorni:

    $$R_{annual} = \left(\frac{1,14}{1,10}\right)^{365/90} - 1 = (1,0364)^{4,056} - 1 \approx 15,5\%$$

### 📐 Rendimento Log Annualizzato

Per i rendimenti logaritmici, l'annualizzazione è semplicemente un riscalamento:

$$
r_{annual} = r_{log} \times \frac{365}{d}
$$

Questa linearità è uno dei vantaggi chiave dei rendimenti logaritmici nella finanza quantitativa.

---

## 🔄 Relazione tra Rendimenti Semplici e Log

| Proprietà | Rendimento Semplice $R$ | Rendimento Log $r$ |
|----------|:---:|:---:|
| **Capitalizzazione** | Moltiplicativa: $(1+R_1)(1+R_2)$ | Additiva: $r_1 + r_2$ |
| **Simmetria** | Asimmetrica: +10% e poi −10% ≠ 0 | Simmetrica: +10% e poi −10% = 0 |
| **Annualizzazione** | $(1+R)^{365/d} - 1$ | $r \times 365/d$ |
| **Rendimenti portafoglio** | La somma ponderata funziona ✅ | La somma ponderata non funziona ❌ |
| **Serie temporali** | Non additiva ❌ | Additiva ✅ |
| **Interpretazione** | "Il rendimento è stato del 5%" | "Il tasso di crescita log è stato 0,0488" |

!!! tip "Quale usare?"

    - **Rendimenti semplici** per i report agli utenti e per il calcolo dei rendimenti a livello di portafoglio
    - **Rendimenti log** per l'analisi statistica, la stima della volatilità e i modelli di serie temporali

---

## 📏 Convenzioni di Conteggio dei Giorni

Il numero di giorni $d$ può essere calcolato diversamente a seconda della convenzione:

- **Actual/365**: Giorni solari (quello utilizzato da LibreFolio)
- **Actual/360**: Giorni solari su un anno di 360 giorni (comune nei mercati monetari)
- **30/360**: Assume mesi di 30 giorni e un anno di 360 giorni

Per maggiori dettagli, consulta [Convenzioni di Conteggio dei Giorni](day-count.md).

---

## 💰 Metodi di Rendimento del Portafoglio

Quando un portafoglio presenta **flussi di cassa** (depositi, prelievi), una singola formula di rendimento non è sufficiente. Esistono due metodi per isolare la performance dagli effetti dei flussi di cassa:

### ⏱️ Rendimento Ponderato nel Tempo (TWR)

Elimina l'effetto dei flussi di cassa calcolando i rendimenti dei sotto-periodi tra ogni evento di flusso e concatenandoli:

$$
R_{TWR} = \prod_{i=1}^{n} (1 + r_i) - 1
$$

- Misura la **pura performance del portafoglio** indipendentemente dal momento dei depositi/prelievi
- Utilizzato dai gestori di fondi per il benchmarking (conforme GIPS)
- Non influenzato dal comportamento dell'investitore (aggiungere denaro ai picchi, prelevare ai minimi)

### 💵 Rendimento Ponderato per il Capitale (MWR / IRR)

Tiene conto del **momento e dell'entità** dei flussi di cassa — è il tasso interno di rendimento che porta il VAN di tutti i flussi a zero:

$$
0 = \sum_{i=0}^{n} \frac{CF_i}{(1 + r)^{t_i}}
$$

dove $CF_i$ è ogni singolo flusso di cassa (depositi positivi, prelievi negativi, valore finale del portafoglio positivo).

- Misura l'**esperienza specifica dell'investitore** (il tuo rendimento reale dato il momento in cui hai aggiunto/rimosso capitale)
- Penalizza un timing errato (depositare ai massimi, prelevare ai minimi)
- Utilizzato per la performance del portafoglio personale

!!! info "Quale usa LibreFolio?"

    LibreFolio calcolerà sia il TWR che il MWR nella dashboard di analisi del portafoglio. TWR per il confronto con i benchmark, MWR per la valutazione della performance personale.

---

## ⚠️ Insidie

1. **Periodi molto brevi**: Annualizzare un rendimento di 3 giorni può produrre cifre fuorvianti (es. un movimento dello 0,1% in 3 giorni → 12,5% annualizzato)
2. **Prezzi negativi**: I rendimenti log non sono definiti per valori negativi — non è un problema per i tassi FX
3. **Frequenza di capitalizzazione**: Il CAGR assume una capitalizzazione continua; gli strumenti finanziari di mercato possono capitalizzare giornalmente, mensilmente o trimestralmente
