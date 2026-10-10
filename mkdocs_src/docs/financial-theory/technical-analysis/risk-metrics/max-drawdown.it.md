# 📉 Drawdown massimo

Il drawdown massimo (MDD) misura la **maggiore contrazione da picco a minimo** del valore di portafoglio prima che venga stabilito un nuovo picco. Risponde alla domanda: *"Qual è stata la perdita peggiore che un investitore avrebbe potuto subire?"*

---

## 🔢 Formula {: #formula }

$$
MDD = \frac{Trough - Peak}{Peak} = \min_{t} \left( \frac{V_t - \max_{\tau \leq t} V_\tau}{\max_{\tau \leq t} V_\tau} \right)
$$

dove $V_t$ è il valore del portafoglio al tempo $t$.

Il drawdown in qualsiasi punto $t$ è:

$$
DD_t = \frac{V_t - V_{peak}}{V_{peak}}
$$

Il drawdown massimo è il valore minimo (il più negativo) di $DD_t$ sull'intero periodo di osservazione.

---

## 💡 Interpretazione {: #interpretation }

| Drawdown massimo | Contesto tipico |
|---|---|
| $-5\%$ a $-10\%$ | Correzione normale, portafoglio ben diversificato |
| $-10\%$ a $-20\%$ | Correzione significativa |
| $-20\%$ a $-30\%$ | Territorio da mercato orso |
| $-30\%$ a $-50\%$ | Mercato orso severo (2008, COVID-2020) |
| $> -50\%$ | Catastrofico (posizioni concentrate, crypto) |

!!! example "Esempio numerico"

    Sequenza del valore del portafoglio: 100 → 120 → 90 → 110 → 130

    - Picco: 120
    - Minimo: 90
    - MDD: $(90 - 120) / 120 = -25\%$
    - Recupero: ha raggiunto di nuovo 120, poi nuovo massimo a 130

---

## ⏱️ Tempo di recupero {: #recovery-time }

Una metrica altrettanto importante è il **tempo di recupero** — per quanto tempo il portafoglio è rimasto al di sotto di un picco che aveva già raggiunto. Il conteggio inizia dal **picco**, non dal minimo: parte il giorno in cui il portafoglio lascia il suo picco e si ferma solo quando quel livello viene raggiunto di nuovo.

$$
T_{recovery} = t_{recovery} - t_{peak}
$$

Il calo fa quindi parte del conteggio, e la durata è espressa in **giorni di calendario** tra quelle due date. L'episodio peggiore viene sempre riportato insieme al suo stato, e lo stato determina cos'altro si può dire al riguardo:

| Stato di recupero | Cosa significa | Cosa comporta |
|---|---|---|
| *recovered* | Il picco precedente è stato raggiunto di nuovo | Date di picco, minimo e recupero; la durata è definitiva |
| *open* | Il picco non è stato raggiunto di nuovo entro il periodo osservato | Date di picco e minimo, e **nessuna data di recupero**; la durata è ancora in corso |
| *no drawdown* | Il portafoglio non è mai sceso sotto un picco precedente | Nessuna data e nessuna frazione recuperata; profondità e durata sono zero |

Queste non sono convenzioni di presentazione: le combinazioni sono imposte sul risultato stesso, quindi un episodio aperto non può avere una data di recupero, e un episodio che non si è mai verificato non può avere un recupero parziale.

!!! info "Quando il drawdown è ancora aperto"

    Se il picco non è stato raggiunto di nuovo entro la fine del periodo osservato non c'è una data di recupero, e la durata viene misurata invece fino all'ultima osservazione:

    $$
    T_{open} = t_{last} - t_{peak}
    $$

    Questa cifra **cresce ogni giorno che passa** mentre il portafoglio rimane sotto il picco: il numero non si sta muovendo a caso, l'episodio semplicemente non è ancora terminato.

    Un episodio aperto porta anche una **frazione recuperata** compresa tra $0$ e $1$: quanto della caduta, misurata dal minimo, è già stato risalito. È una lettura di avanzamento più che un verdetto — la parte della discesa che è stata annullata finora — ed è la cifra che risponde alla domanda che un investitore ancora sotto il picco si sta effettivamente ponendo.

!!! warning "Perché il conteggio inizia dal picco"

    Misurare solo la risalita — dal minimo a un nuovo picco — restituisce sempre un numero **più piccolo**, perché scarta il calo stesso. Ma l'investitore era già sotto il picco mentre il portafoglio scendeva: quel tratto non è un preludio alla perdita, è la perdita che si sta verificando. Iniziare il conteggio dal picco riporta l'intero periodo trascorso sotto il picco, che è il periodo che l'investitore ha effettivamente dovuto vivere.

Contesto storico, per classe di asset:

| Classe di asset | Tempo di recupero tipico (dopo un drawdown rilevante) |
|-------------|---------------------------------------------|
| Azioni USA (S&P 500) | 1-5 anni |
| Obbligazioni | Da mesi a 1-2 anni |
| Criptovalute | Altamente variabile (da mesi ad anni) |

Queste cifre sono storia generale di mercato, non una misurazione di LibreFolio, e non è indicato il criterio in base al quale sono stati conteggiati — i tempi di recupero pubblicati sono talvolta misurati dal minimo e talvolta dal picco. Non sono quindi **direttamente confrontabili** con la durata riportata sopra, che conta sempre dal picco e copre quindi un tratto più lungo rispetto a una cifra basata sul minimo per lo stesso episodio.

!!! warning "Asimmetria delle perdite"

    Una perdita del 50% richiede un **guadagno del 100%** per recuperare:

    $$
    \text{Guadagno richiesto} = \frac{1}{1 + MDD} - 1
    $$

    <div style="display: flex; justify-content: center;">

    | Perdita | Guadagno richiesto |
    |:----:|:-------------:|
    | -10% | +11.1% |
    | -25% | +33.3% |
    | -50% | +100% |
    | -75% | +300% |

    </div>

La tabella sopra è l'aritmetica generale dell'asimmetria, tabulata rispetto alla profondità del drawdown **massimo**. La cifra che il sistema calcola applica invece quella stessa formula al drawdown **attuale**: risponde a quanto guadagno serve per tornare al picco *dal punto in cui il portafoglio si trova oggi*, che è l'unica versione della domanda su cui si può agire. Le due letture coincidono solo quando il portafoglio si trova nel suo punto più profondo di sempre — vedi [Drawdown attuale](current-drawdown.md).

---

## 📊 Grafico del drawdown {: #drawdown-chart }

Un grafico del drawdown rappresenta $DD_t$ nel tempo. È sempre zero o negativo, e tocca zero a ogni nuovo picco. La valle più profonda è il drawdown massimo. Questa visualizzazione rende facile:

- Identificare la **tempistica** dei periodi peggiori
- Vedere quanto frequentemente si verificano i drawdown
- Confrontare i modelli di recupero tra strategie diverse

---

## 🔗 Correlati {: #related }

- 📊 **[Volatilità](volatility.md)** — La deviazione standard non cattura la gravità del drawdown
- 📐 **[Indice di Sharpe](sharpe-ratio.md)** — Rendimento corretto per il rischio (usa la volatilità, non il drawdown)
- 🔀 **[Diversificazione](../../portfolio-theory/diversification.md)** — Lo strumento principale per ridurre il drawdown massimo
