# 📉 Value at Risk

Il Value at Risk risponde a una domanda volutamente ristretta: su un dato orizzonte e a un livello di confidenza scelto, qual è la perdita che non dovrebbe essere superata?

La ristrettezza è il punto, ed è anche la trappola. Il VaR segna **dove inizia la coda** — è una soglia, non un massimo, e tace su tutto ciò che la supera.

---

## 🔢 Formula {: #formula }

Al livello di confidenza $c$, il Value at Risk è il quantile della distribuzione delle perdite:

$$
VaR_c = \inf\left\{\, \ell : P(L \le \ell) \ge c \,\right\}
$$

In pratica è un esercizio di ordinamento: le perdite osservate nella finestra analizzata vengono ordinate, e il valore viene letto alla posizione indicata dal livello di confidenza.

Il risultato è una **dichiarazione di frequenza**. Al 95%, dice che in 19 periodi su 20 la perdita non è peggiore del valore riportato — e che in quello rimanente è peggiore, di un ammontare che questa misura non specifica.

---

## 📜 Misurato, non Modellizzato {: #measured-not-modelled }

Il Value at Risk di LibreFolio è **storico**: è il quantile empirico delle perdite effettivamente subite dal portafoglio. Non c'è alcuna distribuzione ipotizzata al suo interno.

È una scelta deliberata contro l'alternativa più comune, in cui si assume che i rendimenti siano distribuiti normalmente e il quantile viene letto da quella curva.

!!! warning "L'assunzione gaussiana fallisce esattamente quando il numero conta"

    I rendimenti reali di mercato hanno **code più spesse** di una distribuzione normale: i movimenti estremi si verificano più spesso, e sono più ampi, di quanto la curva a campana consenta. Un VaR gaussiano parametrico promette quindi che i giorni peggiori siano più rari di quanto non siano — e mantiene questa promessa con maggiore sicurezza proprio ai livelli di confidenza elevati, che sono esattamente quelli usati per pensare alle crisi.

    È una misura di rischio tanto rassicurante quanto sbagliata. L'approccio empirico non può commettere quell'errore, perché non dichiara mai una forma: conta ciò che è accaduto.

Il vantaggio è guadagnato, non gratuito, e il prezzo si trova nella stessa pagina del beneficio:

!!! warning "Non può mostrarti una perdita che non hai mai vissuto"

    Un quantile empirico è limitato dal campione da cui è tratto. Una storia breve, o calma, produce un Value at Risk calmo — non perché il portafoglio sia sicuro, ma perché non è ancora stato osservato nulla di peggio. La misura descrive la finestra che le è stata data, e una finestra che non contiene alcuna crisi non contiene perdite di dimensioni da crisi.

---

## 💡 Interpretazione {: #interpretation }

Leggi la cifra come *quanto spesso*, mai come *quanto nel peggiore dei casi*:

- **È una soglia, non un limite.** Le perdite oltre di essa non sono escluse — per costruzione, ci si aspetta che si verifichino al tasso dichiarato.
- **Non dice nulla sulla profondità oltre la soglia.** Due portafogli possono riportare lo stesso VaR mentre uno lo supera in modo modesto e l'altro in modo catastrofico. Questa differenza è ciò a cui serve il [VaR condizionale](conditional-value-at-risk.md), ed è il motivo per cui questa sezione inizia con quel valore anziché con questo.
- **È un tasso, non un calendario.** "Un periodo su venti" non significa un periodo negativo ogni venti. I periodi negativi arrivano in gruppi, e un quantile non ha memoria dell'ordine.

Vale la pena enunciare con precisione quest'ultima proprietà, perché separa questa misura da metà della sezione: **rimescola l'ordine dei rendimenti osservati e il Value at Risk non si muove affatto.** Legge la distribuzione, non la sequenza. I valori che leggono la sequenza — [drawdown massimo](max-drawdown.md) e [drawdown attuale](current-drawdown.md) — possono cambiare completamente con lo stesso rimescolamento. Nessuna delle due viste è completa da sola, ed è per questo che entrambe vengono pubblicate.

L'osservazione singola meno favorevole nella finestra viene riportata come valore a sé stante, [peggior realizzazione](worst-realization.md): dove il Value at Risk dice *un periodo su venti va peggio di così*, quella dice *e il peggiore è stato questo, in questa data*.

---

## 🔄 Cosa cambia qui la correzione dello stimatore della coda {: #what-the-correction-changes }

La media della coda usata dal [VaR condizionale](conditional-value-at-risk.md) è stata corretta, e la domanda naturale è se la cifra del Value at Risk si muove con essa.

Lo fa per alcune configurazioni e non per altre, e il confine tra le due è esatto. Da quale lato cade una data cifra è deciso dall'aritmetica, non dall'ispezione, quindi può essere verificato anziché assunto.

!!! info "La condizione, per intero"

    Il Value at Risk riportato cambia **esattamente quando $(1-c) \cdot T$ è un numero intero**, dove $c$ è il livello di confidenza e $T$ è il numero di osservazioni che entrano nel calcolo della coda.

    Quando quel prodotto non è un numero intero, entrambe le convenzioni selezionano la stessa osservazione e la cifra non è solo vicina ma identica.

### 🎚️ Perché il cambiamento è tutto o niente {: #why-the-change-is-all-or-nothing }

Uno studio di misurazione su 24 combinazioni di livello di confidenza e lunghezza della storia, 300 campioni ciascuna — 7.200 prove — ha rilevato che ogni combinazione era una in cui **o ogni campione si muoveva o nessuno lo faceva**. Nessuna combinazione ha prodotto una proporzione intermedia.

Ciò deriva da cosa è la cifra. Il Value at Risk qui è una **statistica d'ordine**: il calcolo ordina le perdite osservate e legge quella alla posizione indicata dal livello di confidenza, quindi il numero riportato è sempre una perdita che il portafoglio ha effettivamente subito. È una funzione a gradini di un indice, non una funzione continua dei dati.

Quando la condizione sopra è soddisfatta, l'indice si sposta di una posizione — e un indice che si sposta non si sposta di poco. Seleziona una **osservazione diversa**. La cifra quindi salta di una intera statistica d'ordine, e il salto più grande misurato è stato **+4,587%**. Tra numeri interi le due convenzioni arrotondano allo stesso indice e l'output è identico bit per bit.

!!! info "Dove la cifra si muove, si muove verso l'alto"

    Questa cifra e il [VaR condizionale](conditional-value-at-risk.md) si muovono entrambi nella stessa direzione: verso l'alto. Non è stata trovata alcuna configurazione in cui uno dei due numeri si muovesse verso una lettura più ottimistica. Dove un Value at Risk è cambiato, il rischio precedentemente riportato era **troppo basso**.

### 📅 Quali storie sono interessate {: #which-histories-are-affected }

$(1-c) \cdot T$ è un numero intero quando $T$ è divisibile per 10 al 90% di confidenza, per 20 al 95%, e per 100 al 99%:

| Osservazioni $T$ | 90% | 95% | 99% |
|---|---|---|---|
| 250 | si muove | — | — |
| 500 | si muove | si muove | si muove |
| 750 | si muove | — | — |
| 1000 | si muove | si muove | si muove |
| 1003 | — | — | — |
| 2000 | si muove | si muove | si muove |

Lo schema in quella tabella merita di essere nominato, perché è l'opposto di un raro caso limite: **le storie interessate sono quelle pulite**. Un anno, due anni, tre anni, mille giorni — i numeri tondi sono precisamente i numeri divisibili, e i numeri tondi sono quelli che un'interfaccia ti invita a digitare. Una storia di 1.003 osservazioni, al contrario, non è interessata a nessun livello di confidenza.

Questo è il fatto che risponde alla domanda che la correzione di solito provoca — **perché un'analisi è cambiata e quella di un collega no**. Due analisi dello stesso portafoglio allo stesso livello di confidenza possono non essere d'accordo sul fatto che sia cambiato qualcosa, perché una è stata eseguita su una finestra tonda e l'altra no. Nessuna delle due è sbagliata, e la differenza tra loro non è una questione di grado: è la divisibilità di un singolo numero intero.

### ⏳ Il numero di osservazioni non è la lunghezza della storia {: #the-observation-count-is-not-the-history-length }

$T$ non è il numero di giorni nella finestra. La coda è calcolata da rendimenti **composti per orizzonte** — ogni sequenza di $n$ rendimenti consecutivi composta in uno — quindi il numero di valori che entrano nel calcolo è

$$
T = N - n + 1
$$

dove $N$ è il numero di rendimenti nella finestra e $n$ è l'orizzonte contato in osservazioni. Il parametro **Orizzonte (giorni)** $h$ è in **giorni di calendario**, e viene convertito in osservazioni al tasso con cui la serie è stata effettivamente osservata — il suo [fattore di annualizzazione osservato](observed-annualization.md) $f$:

$$
n = \max\left(1,\ \operatorname{round}\left(\frac{h \cdot f}{365}\right)\right)
$$

Un orizzonte copre quindi lo stesso intervallo di calendario su ogni serie, all'osservazione più vicina. Trenta giorni — il mese negativo che l'app riporta accanto al giorno negativo — sono $n = 21$ osservazioni di una serie quotata nei giorni di negoziazione ($f \approx 252$) e $n = 30$ di una quotata ogni giorno di calendario ($f = 365$).

L'analitica calcola esattamente queste quantità e pubblica entrambe con il risultato: $n$ come il suo orizzonte in osservazioni, $T$ come il suo conteggio di osservazioni. Quel conteggio pubblicato, non la lunghezza della finestra, è il $T$ a cui si applica la regola. È anche il conteggio rispetto al quale viene verificato il minimo di 20 osservazioni: con meno di 20 finestre composte la cifra non viene calcolata, e il risultato torna non disponibile per storia insufficiente. Un mese negativo richiede quindi $N \ge 40$ rendimenti con $f \approx 252$, dove $n = 21$, e $N \ge 49$ con $f = 365$.

L'orizzonte è un campo del modulo sull'analitica, con valore predefinito $h = 1$ e accetta valori da 1 a 365. Al valore predefinito $n = 1$ su ogni serie — nessuna è osservata più di una volta per giorno di calendario, quindi $f \le 365$ — e $T = N$, motivo per cui le storie tonde sono quelle interessate.

Alzalo e la tabella sopra si inverte. Con $h = 10$, una serie quotata nei giorni di negoziazione compone $n = 7$ osservazioni, quindi un $N$ tondo produce $T = N - 6$, un numero che termina con 4; una serie quotata ogni giorno di calendario compone $n = 10$, e $T = N - 9$ termina con 1. Nessuno dei due è mai divisibile per 10, 20 o 100, e lo stesso vale per qualsiasi serie osservata almeno 54,75 volte l'anno ($f \ge 54{,}75$): dieci giorni contengono allora tra 2 e 10 osservazioni, quindi un $N$ tondo ne perde tra 1 e 9. A parità di lunghezze di storia, con $h = 10$ **250, 500, 750, 1000, 1250 e 2000 osservazioni non sono interessate a nessuno dei tre livelli di confidenza**, su entrambi i tipi di serie. L'orizzonte predefinito di 1 è precisamente l'impostazione in cui le storie pulite si muovono; un orizzonte di 10 lascia quelle stesse storie intatte — tranne che su una serie osservata meno spesso, come un fondo settimanale ($f \approx 52$), dove dieci giorni arrotondano comunque a una singola osservazione e $T = N$. Questa è una conseguenza dell'aritmetica, non un suo difetto, ma significa che un confronto tra due analisi deve far corrispondere l'orizzonte oltre che la finestra e il livello — e, poiché lo stesso orizzonte contiene un $n$ diverso a un $f$ diverso, anche la frequenza osservata della serie.

!!! info "Come verificare un caso particolare"

    Prendi il conteggio delle osservazioni che il Value at Risk pubblica con le sue cifre — `observations`, già al netto dell'orizzonte e pubblicato accanto a `horizon_observations` — e moltiplicalo per $1 - c$. Un numero intero significa che la cifra si è spostata, di una osservazione; qualsiasi altro valore significa che è invariata. Il conteggio delle osservazioni nei metadati del risultato (`n_observations`, vedi [qualità dei dati](data-quality.md)) è $N$, contato prima della composizione: è uguale a $T$ solo quando $n = 1$.

---

## ⚠️ Limitazioni {: #limitations }

!!! warning "Silenzioso oltre la soglia"

    La misura si ferma al confine della coda. Se le perdite oltre di essa siano leggermente peggiori o molte volte peggiori è un'informazione che non porta con sé, e nessun livello di confidenza la recupera. Usa il [VaR condizionale](conditional-value-at-risk.md) per la profondità.

!!! warning "Il livello di confidenza cambia la domanda, non la precisione"

    Passare dal 95% al 99% non produce una risposta più accurata; chiede di un evento più raro. Chiede anche di uno stimato da meno osservazioni, quindi il livello più alto viene letto da una fetta più sottile della stessa storia.

!!! warning "Eredita la sua finestra"

    La cifra è calcolata dai rendimenti del periodo analizzato, sul calendario di osservazione che quelle serie condividono. La finestra, il conteggio delle osservazioni e la base utilizzata sono pubblicati con il risultato — vedi [qualità dei dati](data-quality.md).

---

## 🔗 Correlati {: #related }

- 🌊 **[VaR condizionale](conditional-value-at-risk.md)** — quanto è profonda la coda una volta superata la soglia
- 📉 **[drawdown massimo](max-drawdown.md)** — il calo peggiore lungo il percorso, che un quantile non può vedere
- 📊 **[volatilità](volatility.md)** — la dispersione nel suo complesso, anziché un punto della distribuzione
- ⏮️ **[replay storico](historical-replay.md)** — un episodio specifico invece di una statistica riassuntiva
- 🔻 **[peggior realizzazione](worst-realization.md)** — l'osservazione singola più profonda, come fatto datato anziché come tasso
- 🧪 **[qualità dei dati](data-quality.md)** — la finestra e le osservazioni da cui è stato letto il quantile
