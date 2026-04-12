# 💰 Tassazione ed Efficienza Fiscale

Comprendere la tassazione è essenziale per massimizzare i rendimenti degli investimenti a lungo termine. Questa pagina copre le basi teoriche — **non le regole specifiche di una singola giurisdizione** — di come le tasse interagiscono con la crescita del portafoglio.

!!! warning "Non è un consiglio finanziario"

    LibreFolio non fornisce consulenza fiscale. Ogni giurisdizione ha regole diverse riguardo alle aliquote fiscali, ai periodi di detenzione, al riporto delle perdite e ai metodi di matching. Consulta un professionista fiscale qualificato per la tua situazione specifica.

---

## 📊 Plusvalenze e Minusvalenze

Quando vendi un asset, la differenza tra il prezzo di vendita e il prezzo di acquisto determina la tua **plusvalenza** (capital gain) o **minusvalenza** (capital loss):

$$
\text{Plusvalenza} = P_{sell} - P_{buy} - \text{Commissioni}
$$

- **Plusvalenza** ($> 0$): Hai venduto a un prezzo superiore a quello pagato $\rightarrow$ evento tassabile nella maggior parte delle giurisdizioni
- **Minusvalenza** ($< 0$): Hai venduto a un prezzo inferiore a quello pagato $\rightarrow$ può compensare plusvalenze future

### 🔄 Realizzate vs Non Realizzate

| Tipo | Definizione | Impatto Fiscale |
|------|-----------|------------|
| **Non Realizzate** (guadagno/perdita cartacea) | L'asset è ancora in portafoglio; il guadagno/perdita esiste solo sulla carta | Non tassate (nella maggior parte delle giurisdizioni) |
| **Realizzate** | L'asset è stato venduto; il guadagno/perdita è consolidato | In genere innesca un evento fiscale |

Questa distinzione è la base del **differimento fiscale** — non vendendo, differisci l'evento fiscale a tempo indeterminato.

### 📋 Metodi di Matching

Quando hai acquistato lo stesso asset più volte a prezzi diversi, a quale acquisto viene associata una vendita?

| Metodo | Regola | Effetto |
|--------|------|--------|
| **FIFO** (First In, First Out) | Le quote più vecchie vengono vendute per prime | L'impostazione predefinita più comune |
| **LIFO** (Last In, First Out) | Le quote più recenti vengono vendute per prime | Può minimizzare/massimizzare i guadagni |
| **Identificazione Specifica** | Scegli tu quale lotto vendere | Massima ottimizzazione fiscale |

!!! info "LibreFolio utilizza il FIFO"

    LibreFolio calcola le plusvalenze utilizzando il matching **FIFO** in fase di esecuzione. Il matching è calcolato on-demand e non viene memorizzato nel database.

---

## 🔄 Riporto delle Perdite (Loss Carry-Forward)

La maggior parte delle giurisdizioni consente di **riportare** le minusvalenze per compensare future plusvalenze:

$$
\text{Guadagno Tassabile}_t = \max(0, \text{Plusvalenze Realizzate}_t - \text{Perdite Riportate}_{t-1})
$$

Parametri chiave che variano a seconda della giurisdizione:

- ⏳ **Durata**: Per quanto tempo le perdite possono essere riportate (es. 4 anni in Italia, illimitato in Germania, 7 anni negli USA per certi tipi)
- 📊 **Ambito**: Se le perdite di una classe di asset possono compensare i guadagni di un'altra
- 🚫 **Regole sulle wash sale**: Restrizioni sull'acquisto di un asset appena venduto entro un breve intervallo di tempo per poter dedurre la perdita

---

## ⏳ Vantaggio del Differimento Fiscale { #tax-deferral-advantage }

Uno dei concetti più potenti nell'investimento efficiente dal punto di vista fiscale è quello di **differire** l'evento fiscale il più a lungo possibile. La matematica favorisce nettamente il differimento:

### 📐 La Formula

Confrontiamo due scenari su $n$ anni con rendimento annuale $r$ e aliquota fiscale $\tau$:

**Scenario A — Tassazione annuale** (es. fondo a distribuzione):

$$
V_A = P \cdot (1 + r \cdot (1 - \tau))^n
$$

**Scenario B — Tassazione finale** (es. fondo ad accumulazione):

$$
V_B = P \cdot (1 + r)^n - \tau \cdot [P \cdot (1 + r)^n - P] = P \cdot [(1 + r)^n \cdot (1 - \tau) + \tau]
$$

### 📊 Esempio Numerico

Con $P = 10{,}000$, $r = 7\%$, $\tau = 26\%$, $n = 20$ anni:

| Scenario | Valore Finale | Rendimento Effettivo |
|----------|------------|-----------------|
| Tassazione annuale | €28,398 | 5.18% p.a. |
| Tassazione finale | €31,616 | 5.93% p.a. |
| **Vantaggio del differimento** | **+€3,218** | **+0.75% p.a.** |

Il vantaggio cresce esponenzialmente con il tempo — su 30 anni, il divario si allarga a oltre €8,000 sullo stesso investimento di €10,000.

---

## 📦 Strumenti ad Accumulazione vs Distribuzione

Questo vantaggio del differimento si manifesta direttamente nella scelta tra veicoli d'investimento ad accumulazione o a distribuzione:

### 📈 Accumulazione (es. ETF Acc)

- I dividendi sono **reinvestiti internamente** dal fondo
- **Nessun evento tassabile** fino alla vendita delle quote del fondo
- Pieno beneficio della [crescita composta](../technical-analysis/synthetic-benchmarks/compound.md) sull'importo pre-tasse
- Ideale per investitori a lungo termine che cercano la massima crescita

### 💵 Distribuzione (es. ETF Dist)

- I dividendi ti vengono **pagati** periodicamente
- Ogni distribuzione è un **evento tassabile** (tassato immediatamente)
- Ricevi liquidità ma perdi il beneficio della capitalizzazione composta sulla quota tassata
- Utile se hai bisogno di un reddito dai tuoi investimenti

### 🔗 Collegamento ai Modelli di Crescita

- **[Crescita Lineare](../technical-analysis/synthetic-benchmarks/linear.md)** approssima il comportamento quando i dividendi vengono ricevuti ma **non reinvestiti** — la crescita è additiva
- **[Crescita Composta](../technical-analysis/synthetic-benchmarks/compound.md)** rappresenta il caso ideale con reinvestimento totale — la crescita è moltiplicativa e beneficia maggiormente del differimento fiscale

---

## ⚠️ Considerazioni Specifiche per Giurisdizione

Ogni paese ha il proprio quadro fiscale. Parametri chiave che variano:

| Parametro | Esempi |
|-----------|---------|
| **Aliquota sulle plusvalenze** | 26% (Italia), 25% (Germania), 0-20% (USA, a seconda del periodo di detenzione) |
| **Benefici per periodo di detenzione** | Alcuni paesi riducono le aliquote per le posizioni a lungo termine |
| **Durata riporto minusvalenze** | 4 anni (Italia), illimitato (Germania), 7 anni (USA per alcuni tipi) |
| **Trattati contro la doppia imposizione** | Influenzano i dividendi da azioni estere |
| **Soglie di esenzione** | Limiti annuali sotto i quali i guadagni non sono tassati |
| **Regole specifiche per Crypto** | In rapida evoluzione; spesso trattate diversamente dagli asset tradizionali |

!!! abstract "Il ruolo di LibreFolio"

    LibreFolio traccia le tue transazioni e calcola le plusvalenze/minusvalenze realizzate utilizzando il matching FIFO. Fornisce la **base dati** per la rendicontazione fiscale, ma non genera dichiarazioni dei redditi né applica regole specifiche di una giurisdizione. Esporta i dati delle tue transazioni e consulta un professionista fiscale.

---

## 🔗 Correlati

- 📈 **[Rendimenti e Tassi di Crescita](returns.md)** — Come misurare e annualizzare i rendimenti
- 🎯 **[Benchmark Sintetici](../technical-analysis/synthetic-benchmarks/index.md)** — Visualizzazione crescita lineare vs composta
- 📅 **[Convenzioni di Conteggio dei Giorni](day-count.md)** — Come i periodi temporali influenzano i calcoli
