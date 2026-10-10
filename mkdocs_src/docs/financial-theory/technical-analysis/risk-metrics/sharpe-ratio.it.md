# 📐 Indice di Sharpe

L'indice di Sharpe è la metrica di **rendimento corretto per il rischio** più utilizzata. Misura quanto rendimento in eccesso si riceve per unità di volatilità totale.

---

## 🔢 Formula {: #formula }

$$
S = \frac{R_p - R_f}{\sigma_p}
$$

dove:

- $R_p$ = rendimento del portafoglio (annualizzato)
- $R_f$ = tasso privo di rischio (ad es., tasso dei buoni del Tesoro)
- $\sigma_p$ = deviazione standard del portafoglio (annualizzata)

!!! info "Come entra il tasso nel calcolo"

    Il tasso privo di rischio viene fornito come tasso **effettivo annuo** e convertito in un tasso **effettivo per periodo** prima dell'uso:

    $$
    r_{period} = (1 + r_{annual})^{1/f} - 1
    $$

    dove $f$ è lo stesso fattore di annualizzazione che scala la volatilità, misurato dai dati osservati — si veda [Annualizzazione](#annualization). Quel tasso per periodo viene sottratto da ogni rendimento di periodo, e i rendimenti in eccesso risultanti sono ciò su cui si basa l'indice. Il fatto che $f$ sia condiviso con la volatilità mantiene numeratore e denominatore sullo stesso periodo: applicare un tasso su base giorno di calendario a rendimenti su giorni di negoziazione sottostimerebbe l'addebito e, quando il tasso è positivo, renderebbe l'indice più favorevole. La conversione tiene conto della capitalizzazione: un semplice $r_{annual}/f$ tratterebbe il tasso come se non capitalizzasse nell'anno.

---

## 💡 Interpretazione {: #interpretation }

| Indice di Sharpe | Cosa significa il valore |
|---|---|
| $< 0$ | Il portafoglio ha reso meno del tasso privo di rischio nel periodo considerato: il rendimento in eccesso al numeratore è negativo, quindi nessun livello di volatilità può rendere positivo l'indice |
| $0 - 0.5$ | Meno di mezza unità di rendimento in eccesso per unità di volatilità: il portafoglio si è mosso molto rispetto a quanto quel movimento ha fruttato |
| $0.5 - 1.0$ | Tra mezza unità e una unità di rendimento in eccesso per unità di volatilità |
| $1.0 - 2.0$ | Da una a due unità di rendimento in eccesso per unità di volatilità: il rendimento in eccesso è stato maggiore della volatilità che lo ha prodotto |
| $> 2.0$ | Più di due unità di rendimento in eccesso per unità di volatilità — non comune su periodi lunghi, molto meno su periodi brevi e favorevoli |

!!! warning "Lo stesso numero non è la stessa affermazione"

    Un indice non significa nulla se separato dalla finestra temporale e dalla classe di asset su cui è stato misurato. Un periodo breve e favorevole produce valori che un ciclo di mercato completo non sostenrebbe, e classi di asset con ritmi di rendimento diversi occupano per costruzione parti diverse della scala. Due indici sono confrontabili solo quando coprono lo stesso periodo e sono stati annualizzati sullo stesso fattore osservato — si veda [Annualizzazione Osservata](observed-annualization.md). La tabella dice ciò che il numero *è*, non se il risultato sia stato buono: quel giudizio richiede l'obiettivo per cui il portafoglio è stato costruito.

!!! example "Esempio numerico"

    Rendimento del portafoglio: 12%, Tasso privo di rischio: 3%, Volatilità: 15%

    $$S = \frac{0.12 - 0.03}{0.15} = 0.60$$

    Per ogni 1% di volatilità, il portafoglio ha guadagnato 0,60% di rendimento in eccesso.

---

## ⚙️ Annualizzazione {: #annualization }

Un indice di Sharpe calcolato su rendimenti per periodo viene scalato a un valore annuale tramite la radice quadrata del numero di periodi contenuti in un anno:

$$
S_{annual} = S_{period} \times \sqrt{f}
$$

Il fattore $f$ è **misurato dai dati osservati** — il numero di rendimenti effettivamente utilizzati, riscalato a un anno solare completo sull'intervallo che coprono:

$$
f = \frac{N \times 365}{D}
$$

dove $N$ è il numero di rendimenti di periodo e $D$ i giorni di calendario che coprono. La radice quadrata deriva dal fatto che la varianza si somma tra periodi indipendenti, quindi il riscalamento assume che i rendimenti siano IID (indipendenti e identicamente distribuiti) — un'approssimazione che viene meno per rendimenti autocorrelati.

!!! info "√252 è un risultato, non una costante"

    Un titolo prezzato quotidianamente fornisce all'incirca 252 rendimenti in un anno solare completo, quindi $f \approx 252$ e il noto $\sqrt{252}$ viene ritrovato come esito della misurazione anziché esservi incorporato. Uno strumento prezzato ogni giorno di calendario dà invece $f \approx 365$, e un fondo prezzato settimanalmente $f \approx 52$.

    → Si veda **[Annualizzazione Osservata](observed-annualization.md)** per la derivazione ed esempi svolti.

---

## ⚠️ Limitazioni {: #limitations }

### 📊 Penalizzazione simmetrica {: #symmetric-penalty }

L'indice di Sharpe penalizza la **volatilità al rialzo** tanto quanto la volatilità al ribasso. Un asset che si impenna spesso verso l'alto (cosa altamente desiderabile!) avrà un indice di Sharpe inferiore rispetto a uno con lo stesso rendimento e minor movimento al rialzo.

→ Per distribuzioni dei rendimenti asimmetriche, preferire il **[Indice di Sortino](sortino-ratio.md)**.

### 📈 Sensibilità agli outlier {: #sensitivity-to-outliers }

Alcuni rendimenti estremi possono distorcere significativamente la deviazione standard, rendendo l'indice di Sharpe instabile per periodi di tempo brevi.

### 🔄 Dipendenza dal periodo temporale {: #time-period-dependency }

L'indice di Sharpe può variare drasticamente a seconda della finestra di osservazione. Una strategia con un eccellente indice di Sharpe a 5 anni può avere un indice di Sharpe a 1 anno scarso (o viceversa).

---

## 🔗 Correlati {: #related }

- 📊 **[Indice di Sortino](sortino-ratio.md)** — Variante solo al ribasso
- 📊 **[Volatilità](volatility.md)** — Il denominatore dell'indice di Sharpe
- 📈 **[Rendimenti](../../fundamentals/returns.md)** — Il numeratore dell'indice di Sharpe
