# 🌊 Drawdown a rischio condizionale

Il drawdown a rischio condizionale calcola la media dei drawdown che hanno superato la soglia di drawdown a rischio, rispondendo a quanto profonda diventa la caduta una volta oltrepassato quel punto.

Il [Drawdown a rischio](drawdown-at-risk.md) dice **dove inizia la coda del drawdown**. Questo dice **quanto è profonda** — lo stesso passo che [VaR condizionale](conditional-value-at-risk.md) compie oltre [Value at Risk](value-at-risk.md), applicato alla serie dei drawdown invece che alla serie delle perdite.

La parola *media* in quella frase iniziale fa più lavoro di quanto sembri. È una media **ponderata**, e il peso è fissato dal livello di confidenza anziché da quante osservazioni capitano nella coda. Questa distinzione è l'argomento della maggior parte di questa pagina, perché la scorciatoia che essa esclude è plausibile.

---

## 🔢 Formula {: #formula }

Al livello di confidenza $c$, indicando con $\alpha = 1 - c$ la frazione di coda, la misura assume la forma **Rockafellar–Uryasev**:

$$
CDaR_c = DaR_c - \frac{1}{\alpha T} \sum_{t=1}^{T} \left( DaR_c - DD_t \right)^{+}
$$

dove $(x)^{+} = \max(x, 0)$, $DD_t$ è il drawdown all'osservazione $t$, e $T$ è il numero di punti osservati nella serie.

La somma raccoglie la **severità in eccesso**: per ogni osservazione più profonda della soglia, quanto più profonda. Ogni osservazione meno profonda della soglia non contribuisce. Tale totale viene poi distribuito su $\alpha T$ e sottratto dalla soglia, il che spinge il risultato più sotto zero del drawdown a rischio da cui parte.

Come la soglia che estende, il drawdown a rischio condizionale è **non positivo** — un drawdown è una caduta da un picco, e fare la media delle cadute non produce un rialzo. È sempre almeno altrettanto severo del drawdown a rischio allo stesso livello di confidenza, perché ogni quantità che aggiunge a quella soglia è una caduta oltre di essa.

---

## 🔬 Non è la media delle osservazioni peggiori {: #it-is-not-the-average-of-the-worst-observations }

La ricetta intuitiva — prendere i $k$ drawdown più profondi e farne la media — non è questa formula, e la differenza sta nel denominatore.

La normalizzazione sopra è $\alpha T$: una quantità **fissa** determinata dal livello di confidenza e dalla lunghezza della storia. Il conteggio della coda $k$ è una quantità diversa — il numero di osservazioni che sono effettivamente finite oltre la soglia, che può essere solo un numero intero. Quando $\alpha T$ non è intero, la coda contiene necessariamente **più** osservazioni di $\alpha T$, e dividere la stessa severità totale per quel conteggio maggiore produce una cifra meno profonda.

!!! warning "La scorciatoia sottostima la coda"

    Fare la media sul conteggio della coda invece che su $\alpha T$ riporta il caso medio negativo come **più mite** di quanto dicano i dati. Le due forme coincidono **esattamente** quando $\alpha T$ è un numero intero, e la scorciatoia è troppo ottimistica ogni volta che non lo è.

    | Osservazioni $T$ | $\alpha T$ al 95% | Numero intero? | Differenza relativa |
    |---|---|---|---|
    | 740 | 37.00 | sì | **0.00000%** |
    | 745 | 37.25 | no | $-0.03817\%$ |
    | 750 | 37.50 | no | $-0.02528\%$ |
    | 760 | 38.00 | sì | **0.00000%** |
    | 800 | 40.00 | sì | **0.00000%** |
    | 1000 | 50.00 | sì | **0.00000%** |

    Gli scarti sono frazioni di un punto percentuale. È proprio questo che rende la scorciatoia duratura: una cifra sbagliata di tre centesimi di punto percentuale sembra un arrotondamento, non una formula diversa.

---

## 🪤 La stessa trappola, nel senso opposto {: #the-same-trap-in-the-opposite-sense }

Questa è la stessa forma di errore che la pagina [VaR condizionale](conditional-value-at-risk.md) descrive per la coda delle perdite: una media uniforme plausibile, sbagliata di una frazione di punto percentuale, nella stessa direzione — sottostima la coda. Ed è governata dalla **stessa quantità aritmetica**, $(1 - c) \cdot T$, che la pagina [Value at Risk](value-at-risk.md#what-the-correction-changes) già espone.

!!! warning "La stessa quantità, il significato opposto — non trasferire una regola all'altra"

    Un $(1 - c) \cdot T$ intero significa cose opposte nelle due pagine, e le due affermazioni è facile confonderle in una sola.

    | Misura | Quando $(1 - c) \cdot T$ è un numero intero |
    |---|---|
    | [Value at Risk](value-at-risk.md#what-the-correction-changes) | le due convenzioni **divergono** — la cifra si sposta di un'osservazione intera |
    | **Drawdown a rischio condizionale** | la scorciatoia **è corretta per caso** — le due forme coincidono esattamente |

    La divisibilità è la condizione in entrambi i casi; semplicemente seleziona il disaccordo in uno e l'accordo nell'altro.

---

## 🔍 Verificare la cifra da soli {: #checking-the-figure-yourself }

Poiché un $\alpha T$ intero è esattamente il punto in cui la scorciatoia è indistinguibile dalla forma corretta, la scelta della lunghezza della storia decide se un controllo manuale può rilevare la differenza.

!!! warning "Una lunghezza della storia tonda non può distinguere le due forme"

    | Osservazioni $T$ | 90% | 95% | 99% |
    |---|---|---|---|
    | 250 | non distingue | distingue | distingue |
    | 500 | **non distingue** | **non distingue** | **non distingue** |
    | 750 | non distingue | distingue | distingue |
    | 1000 | **non distingue** | **non distingue** | **non distingue** |
    | 1003 | distingue | distingue | distingue |
    | 2000 | **non distingue** | **non distingue** | **non distingue** |

    **500, 1.000 e 2.000 osservazioni non distinguono a ogni livello di confidenza; 1.003 distingue a ogni livello.**

    Lo schema non è un caso limite raro — è l'opposto. $\alpha T$ è intero quando $T$ è divisibile per 10 al 90% di confidenza, per 20 al 95%, e per 100 al 99%, e i numeri tondi sono precisamente quelli divisibili. Due anni, mille giorni, cinquecento sedute: le lunghezze della finestra a cui chiunque ricorre per prime sono quelle in cui le due forme restituiscono lo stesso numero.

!!! tip "Quindi scegli una finestra non tonda"

    Se vuoi verificare la cifra ricalcolandola, scegli una lunghezza della storia che **non** sia un multiplo tondo di 10, 20 o 100 — 1.003 osservazioni invece di 1.000. A una lunghezza divisibile le due formule candidate concordano fino all'ultima cifra, quindi una corrispondenza non ti dice nulla su quale delle due l'abbia prodotta.

---

## 💡 Interpretazione {: #interpretation }

Leggilo come *quanto in basso sotto il picco si arriva una volta superata la soglia* — la severità della coda del drawdown, non il suo confine.

- **Lo scarto dalla soglia è informativo.** Un drawdown a rischio condizionale molto al di sotto del suo drawdown a rischio descrive un portafoglio le cui fasi negative, una volta iniziate, si spingono molto più in profondità di quanto suggerisca la soglia.
- **È una profondità, non una durata.** Dice quanto è profonda la coda della distribuzione dei drawdown, e nulla su quanto a lungo il portafoglio sia rimasto lì. [Indice di Ulcer](ulcer-index.md) è la cifra che incorpora la durata.
- **Legge una serie dipendente dal percorso.** A differenza della coppia basata sulle perdite, questa misura e la sua soglia sono calcolate dai drawdown, che dipendono dall'ordine in cui sono arrivati i rendimenti. Rimescolare la storia le ricostruisce entrambe.

---

## ⚠️ Limitazioni {: #limitations }

!!! warning "La coda è stimata da poche osservazioni"

    Solo una piccola frazione della finestra si trova oltre la soglia, e al 99% quella frazione è molto piccola. La cifra è corrispondentemente instabile: può spostarsi in modo evidente man mano che arrivano osservazioni, e due finestre adiacenti possono discordare più di quanto suggerisca la loro differenza di lunghezza.

!!! warning "Quelle poche osservazioni non sono indipendenti"

    I drawdown all'interno di un episodio sono quasi lo stesso numero giorno dopo giorno, quindi la coda è spesso un singolo declino prolungato contato molte volte anziché $\alpha T$ eventi separati. La misura fa la media delle osservazioni, non degli episodi, e una storia con un anno negativo può mettere quell'anno nella coda da solo.

!!! warning "È limitato dalla storia che gli è stata data"

    Fare la media della coda dei drawdown non crea ribassi che il portafoglio non ha mai vissuto. Una finestra che non contiene episodi severi produce una coda mite, riportata onestamente. Un [replay storico](historical-replay.md) o lo [shock ipotetico](hypothetical-shock.md) è il modo in cui uno scenario esterno alla finestra entra nell'analisi.

---

## 🔗 Correlati {: #related }

- 📉 **[Drawdown a rischio](drawdown-at-risk.md)** — la soglia oltre la quale questa cifra fa la media
- 🌊 **[VaR condizionale](conditional-value-at-risk.md)** — lo stesso passo di severità, applicato alla serie delle perdite
- 📉 **[Value at Risk](value-at-risk.md)** — dove la regola di divisibilità è esposta per intero
- 📉 **[Drawdown massimo](max-drawdown.md)** — la singola caduta più profonda, anziché una media sulla coda
- 🩹 **[Indice di Ulcer](ulcer-index.md)** — profondità e durata insieme, senza un livello di confidenza
- 🧪 **[Qualità dei dati](data-quality.md)** — la finestra e il numero di osservazioni da cui è stata tratta la coda
