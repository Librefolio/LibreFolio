# 💰 Tassazione & Efficienza Fiscale

Comprendere la tassazione è essenziale per massimizzare i rendimenti degli investimenti a lungo termine. Questa pagina tratta le basi teoriche — **non le regole specifiche per giurisdizione** — di come le tasse interagiscono con la crescita del portafoglio.

!!! warning "Non è consulenza finanziaria"

    LibreFolio non fornisce consulenza fiscale. Ogni giurisdizione ha regole diverse riguardo aliquote fiscali, periodi di detenzione, riporto delle perdite e metodi di abbinamento. Consulta un professionista fiscale qualificato per la tua situazione specifica.

---

## 📊 Plusvalenze e Minusvalenze

Quando vendi un asset, la differenza tra il prezzo di vendita e il prezzo di acquisto determina la tua **plusvalenza** o **minusvalenza**:

$$
\text{Plusvalenza} = P_{vendita} - P_{acquisto} - \text{Commissioni}
$$

- **Plusvalenza** ($> 0$): Hai venduto a un prezzo superiore a quello pagato → evento imponibile nella maggior parte delle giurisdizioni
- **Minusvalenza** ($< 0$): Hai venduto a un prezzo inferiore a quello pagato → può compensare plusvalenze future

### 🔄 Realizzate vs Non Realizzate

| Tipo | Definizione | Impatto Fiscale |
|------|------------|-----------------|
| **Non realizzate** (guadagno/perdita su carta) | Asset ancora detenuto; guadagno/perdita esiste solo sulla carta | Non tassato (nella maggior parte delle giurisdizioni) |
| **Realizzate** | Asset venduto; guadagno/perdita è consolidato | Tipicamente genera un evento imponibile |

Questa distinzione è la base del **differimento fiscale** — non vendendo, si differisce l'evento imponibile a tempo indeterminato.

### 📋 Metodi di Abbinamento

Quando hai acquistato lo stesso asset più volte a prezzi diversi, quale acquisto viene abbinato a una vendita?

| Metodo | Regola | Effetto |
|--------|--------|---------|
| **FIFO** (First In, First Out) | Le quote più vecchie vengono vendute per prime | Default più comune |
| **LIFO** (Last In, First Out) | Le quote più recenti vengono vendute per prime | Può minimizzare/massimizzare i guadagni |
| **Identificazione Specifica** | Scegli tu quale lotto vendere | Massima ottimizzazione fiscale |

!!! info "LibreFolio usa il FIFO"

    LibreFolio calcola le plusvalenze utilizzando l'abbinamento **FIFO** a runtime. L'abbinamento viene calcolato on-demand, non memorizzato nel database.

---

## 🔄 Riporto delle Perdite

La maggior parte delle giurisdizioni consente di **riportare** le minusvalenze per compensare plusvalenze future:

$$
\text{Guadagno Imponibile}_t = \max(0, \text{Plusvalenze Realizzate}_t - \text{Minusvalenze Riportate}_{t-1})
$$

Parametri chiave che variano per giurisdizione:

- ⏳ **Durata**: Per quanto tempo le perdite possono essere riportate (es. 4 anni in Italia, illimitato in Germania, 7 anni negli USA per alcuni tipi)
- 📊 **Ambito**: Se le perdite di una classe di asset possono compensare guadagni di un'altra
- 🚫 **Regole sulle vendite fittizie**: Restrizioni sul riacquisto di un asset venduto entro una finestra temporale breve per reclamare la perdita

---

## ⏳ Vantaggio del Differimento Fiscale { #tax-deferral-advantage }

Uno dei concetti più potenti nell'investimento fiscalmente efficiente è **differire** l'evento imponibile il più a lungo possibile. La matematica favorisce fortemente il differimento:

### 📐 La Formula

Confronta due scenari su $n$ anni con rendimento annuo $r$ e aliquota fiscale $\tau$:

**Scenario A — Tassazione annuale** (es. fondo a distribuzione):

$$
V_A = P \cdot (1 + r \cdot (1 - \tau))^n
$$

**Scenario B — Tassazione alla fine** (es. fondo ad accumulazione):

$$
V_B = P \cdot (1 + r)^n - \tau \cdot [P \cdot (1 + r)^n - P] = P \cdot [(1 + r)^n \cdot (1 - \tau) + \tau]
$$

### 📊 Esempio Numerico

Con $P = 10.000$, $r = 7\%$, $\tau = 26\%$, $n = 20$ anni:

| Scenario | Valore Finale | Rendimento Effettivo |
|----------|--------------|---------------------|
| Tassazione annuale | €28.398 | 5,18% p.a. |
| Tassazione alla fine | €31.616 | 5,93% p.a. |
| **Vantaggio del differimento** | **+€3.218** | **+0,75% p.a.** |

Il vantaggio cresce esponenzialmente nel tempo — su 30 anni, il divario supera gli €8.000 sullo stesso investimento di €10.000.

---

## 📦 Strumenti ad Accumulazione vs a Distribuzione

Questo vantaggio del differimento si manifesta direttamente nella scelta tra veicoli di investimento ad accumulazione e a distribuzione:

### 📈 Accumulazione (es. ETF Acc)

- I dividendi vengono **reinvestiti internamente** dal fondo
- **Nessun evento imponibile** finché non vendi le quote del fondo
- Pieno beneficio della [crescita composta](synthetic-benchmarks.md#compound-growth) sull'importo al lordo delle tasse
- Ideale per investitori a lungo termine che cercano la massima crescita

### 💵 Distribuzione (es. ETF Dist)

- I dividendi vengono **pagati** periodicamente
- Ogni distribuzione è un **evento imponibile** (tassato immediatamente)
- Ricevi liquidità ma perdi il beneficio della capitalizzazione sulla parte tassata
- Utile se hai bisogno di reddito dai tuoi investimenti

### 🔗 Collegamento ai Modelli di Crescita

- **[Crescita Lineare](synthetic-benchmarks.md#linear-growth)** approssima il comportamento quando i dividendi vengono ricevuti ma **non reinvestiti** — la crescita è additiva
- **[Crescita Composta](synthetic-benchmarks.md#compound-growth)** rappresenta il caso ideale con reinvestimento completo — la crescita è moltiplicativa e beneficia maggiormente del differimento fiscale

---

## ⚠️ Considerazioni Specifiche per Giurisdizione

Ogni paese ha il proprio quadro fiscale. Parametri chiave che variano:

| Parametro | Esempi |
|-----------|--------|
| **Aliquota sulle plusvalenze** | 26% (Italia), 25% (Germania), 0-20% (USA, in base al periodo di detenzione) |
| **Benefici per periodo di detenzione** | Alcuni paesi riducono le aliquote per detenzioni a lungo termine |
| **Durata riporto perdite** | 4 anni (Italia), illimitato (Germania), 7 anni (USA per alcuni tipi) |
| **Trattati contro la doppia imposizione** | Influenzano i dividendi da azioni estere |
| **Esenzioni fiscali** | Soglie annuali sotto le quali i guadagni non sono tassati |
| **Regole specifiche per le crypto** | In rapida evoluzione; spesso trattate diversamente dagli asset tradizionali |

!!! abstract "Il ruolo di LibreFolio"

    LibreFolio traccia le tue transazioni e calcola le plusvalenze/minusvalenze realizzate usando l'abbinamento FIFO. Fornisce le **basi dati** per la dichiarazione fiscale, ma non genera dichiarazioni fiscali né applica regole specifiche per giurisdizione. Esporta i dati delle tue transazioni e consulta un professionista fiscale.

---

## 🔗 Correlati

- 📈 **[Rendimenti e Tassi di Crescita](returns.md)** — Come misurare e annualizzare i rendimenti
- 🎯 **[Benchmark Sintetici](synthetic-benchmarks.md)** — Visualizzazione crescita lineare vs composta
- 📅 **[Convenzioni di Conteggio dei Giorni](day-count.md)** — Come i periodi temporali influenzano i calcoli

