# 🎯 Concentrazione

La concentrazione misura quanto il peso di un portafoglio si raccolga in poche posizioni, offrendo una lettura che un semplice conteggio delle posizioni non può fornire.

Qui viene trattata come **due** valori anziché uno, e la scelta è deliberata: il primo conta come il denaro è distribuito, il secondo verifica se distriburlo abbia prodotto qualcosa. Letto da solo, il primo dichiarerà diversificato un portafoglio che non lo è.

---

## 🔢 Il valore basato sul conteggio {: #the-count-based-figure }

Il punto di partenza è l'indice di Herfindahl — la somma dei pesi al quadrato:

$$
H = \sum_i w_i^{2}
$$

È l'elevamento al quadrato a renderlo una misura di concentrazione: un peso del 50% contribuisce venticinque volte tanto rispetto a un peso del 10%, quindi le posizioni grandi dominano il totale in un modo che un semplice conteggio non riflette mai.

Il reciproco lo trasforma in qualcosa di leggibile, il **numero di asset effettivi**:

$$
N_{eff} = \frac{1}{H}
$$

Risponde alla domanda: *quante posizioni di uguale dimensione produrrebbero la concentrazione che ho effettivamente?* Dieci posizioni del 10% ciascuna danno $H = 10 \times 0.1^2 = 0.1$ e quindi esattamente 10. Una posizione del 50% insieme a dieci del 5% dà molto meno di undici — il numero scende verso il conteggio delle posizioni che contano davvero.

Il valore è intuitivo proprio perché è espresso sulla scala di un conteggio pur non comportandosi affatto come tale. Questa lettura dipende dal fatto che i pesi sommino a uno: non appena si detiene della liquidità ciò non accade, e il risultato può superare addirittura il numero di posizioni detenute — [Dove si colloca la liquidità](#where-cash-sits) illustra cosa succede in quel caso.

---

## 🙈 Ciò che un conteggio non può vedere {: #what-a-count-cannot-see }

Il numero di asset effettivi legge **solo i pesi**. Non guarda mai a come si comportano le posizioni, e questo è il suo punto cieco — totale.

Si considerino tre portafogli, ciascuno con dieci asset a peso uguale, che differiscono solo per quanto correlate siano tali asset. Accanto al valore basato sul conteggio, la tabella mostra il **rapporto di diversificazione**, che confronta la volatilità che le posizioni avrebbero avuto separatamente con la volatilità del portafoglio che esse formano:

$$
DR = \frac{\sum_i w_i \sigma_i}{\sigma_p}
$$

| Correlazione tra le posizioni | Numero di asset effettivi | Rapporto di diversificazione |
|---|---|---|
| 0 | **10,00** | 3,15 |
| 0,5 | **10,00** | 1,35 |
| 0,95 | **10,00** | **1,02** |

Il valore basato sul conteggio non si muove di un centesimo. Il rapporto di diversificazione crolla.

!!! warning "Dieci posizioni che si muovono insieme non sono dieci scommesse"

    Con una correlazione di 0,95 il portafoglio si comporta quasi esattamente come una singola posizione: il rapporto di 1,02 dice che distribuire il denaro su dieci asset ha comportato una riduzione del 2% della volatilità rispetto a detenerne una sola. Il valore basato sul conteggio riporta 10,00 in tutti e tre i casi, e un lettore che guardasse solo quel numero concluderebbe che tutti e tre i portafogli sono ugualmente ben diversificati.

    Ecco perché i due valori appartengono alla stessa pagina e allo stesso colpo d'occhio. Uno misura come il denaro è **distribuito**, l'altro se la distribuzione ha **funzionato**.

I valori misurati sopra sono coerenti con il caso idealizzato: per $n$ posizioni a peso uguale, con volatilità uguale e correlazione costante a coppie $\rho$, il rapporto è $\sqrt{n / (1 + (n-1)\rho)}$, che dà approssimativamente 3,16, 1,35 e 1,02 per le tre righe.

---

## 🏦 La stessa parola a due granularità {: #two-granularities }

Un portafoglio può riportare due diversi valori di concentrazione nello stesso momento, e nessuno dei due è sbagliato. Ciò che cambia è **cosa conta come una posizione**.

Si supponga che lo stesso strumento sia detenuto presso due broker, al 6% e al 4% del portafoglio.

- Contato **per posizione**, contribuisce per $0.06^2 + 0.04^2 = 0.0052$.
- Contato **per strumento**, le posizioni vengono prima accorpate al 10%, contribuendo per $0.10^2 = 0.0100$.

La differenza è esattamente $2 w_1 w_2$, che è sempre positivo. Quindi la vista per strumento riporta **sempre** la concentrazione più alta — e, poiché il numero di asset effettivi è il reciproco, la vista per posizione riporta **sempre** il numero più rassicurante.

!!! info "Due domande, non due risposte"

    *Quanto sono concentrato per posizione?* e *quanto sono concentrato per strumento?* sono domande diverse, e un portafoglio distribuito su più broker vi risponde diversamente per costruzione. La vista per strumento è quella che corrisponde all'esposizione di mercato: lo stesso fondo detenuto su due conti è una sola scommessa, per quante righe occupi.

    Quando due valori non concordano, ciò che va stabilito è quale granularità abbia contato ciascuno di essi — non quale dei due sia corretto.

Un valore calcolato sulle posizioni è verificabile su questo punto: il report di portafoglio e del broker di LibreFolio costruisce il proprio indice di Herfindahl dai pesi delle singole posizioni, e una posizione è identificata **sia** dal suo strumento sia dal suo broker.

---

## 🪙 Dove si colloca la liquidità {: #where-cash-sits }

La liquidità deve essere gestita in qualche modo, e la scelta cambia il risultato. Nel report di portafoglio e del broker, la regola è dichiarata nel codice stesso: i pesi sono il valore della posizione rapportato al **NAV totale**, e la liquidità è *inclusa nel denominatore ma non è essa stessa un termine dell'indice*.

Vale la pena esplicitare la conseguenza, perché va in una direzione che la maggior parte dei lettori non immaginerebbe. La liquidità diluisce ogni peso senza contribuire con un quadrato proprio, quindi detenere più liquidità **abbassa** l'indice e dunque **innalza** il numero di asset effettivi. Un portafoglio che detiene metà del proprio valore in liquidità sembra meglio diversificato rispetto alle stesse posizioni senza di essa.

Con questa regola l'effetto va oltre un semplice *sembrare migliore*. Si indichi con $s$ la quota investita del portafoglio, così che $s = 1 - \text{quota di liquidità}$ e i pesi sommino a $s$ anziché a uno. Aggiungere liquidità a un insieme fisso di posizioni scala l'indice di $s^{2}$ e il numero di asset effettivi di $1/s^{2}$; per $n$ posizioni a peso uniforme è esattamente

$$
N_{eff} = \frac{n}{s^{2}}
$$

Due posizioni e nessuna liquidità danno 2,00. Le stesse due posizioni danno 8,00 con metà del valore in liquidità, circa **11,4** con poco più della metà in liquidità, e 200 con il novanta per cento in liquidità. Un portafoglio di due posizioni può quindi riportare un valore molte volte superiore a due, e non esiste alcun limite superiore: quando la liquidità si avvicina all'intero portafoglio, il conteggio diverge.

Pesi disomogenei tirano nella direzione opposta, quindi un portafoglio sbilanciato che detiene poca liquidità può comunque riportare meno asset effettivi di quante posizioni detenga. L'inflazione in sé, però, è sempre presente — e la lettura familiare, un valore compreso tra uno e il numero di posizioni detenute, descrive solo il caso senza liquidità.

Ciò è difendibile — la liquidità è davvero una posizione non concentrata, e riduce davvero l'esposizione a qualsiasi singolo strumento — ma è un'assunzione, non un fatto neutrale, e leggere un valore di concentrazione senza conoscerla porta a conclusioni sbagliate. Due portafogli con posizioni identiche e saldi di cassa diversi non sono ugualmente diversificati nel loro capitale investito.

---

## 💡 Interpretazione {: #interpretation }

Leggere i due valori come una coppia, in questo ordine:

1. **Asset effettivi rispetto al numero effettivo di posizioni.** La direzione dello scarto ne seleziona il significato: **al di sotto** del conteggio, i pesi sono sbilanciati e poche posizioni reggono il portafoglio a prescindere da quante righe abbia; **al di sopra**, l'eccesso è liquidità, e non dice nulla su come sono distribuiti i pesi.
2. **Rapporto di diversificazione.** Un valore vicino a 1 significa che le posizioni si muovono come un'unica posizione, e che la distribuzione ha fruttato poco. Quanto più è sopra 1, tanto più le posizioni si compensano a vicenda.

Il secondo valore è quello che può contraddire il primo, ed è la contraddizione a portare l'informazione. Un portafoglio può essere perfettamente bilanciato nei pesi e non diversificato nella sostanza — è il risultato ordinario del detenere diversi fondi che replicano mercati sovrapposti.

Nessuno dei due valori dice nulla su **quali** posizioni determinino il rischio. Quell'attribuzione è il [Contributo al rischio](risk-contribution.md), e il comportamento a coppie sottostante entrambi è la [Correlazione](correlation.md).

---

## ⚠️ Limitazioni {: #limitations }

!!! warning "I soli pesi possono rassicurare"

    Il valore basato sul conteggio è una funzione dei pesi e nulla più. Non può distinguere un portafoglio realmente variegato da un insieme di posizioni quasi identiche, e non è di per sé una prova di diversificazione.

!!! warning "Essere consapevoli delle correlazioni non significa essere previsionali"

    Il rapporto di diversificazione dipende da volatilità e correlazioni stimate su una finestra, e queste cambiano — tipicamente nella direzione meno conveniente, poiché le correlazioni tendono a salire nei mercati sotto stress. Un rapporto rassicurante misurato su un periodo calmo è una misura di quel periodo. Vedi [Qualità dei dati](data-quality.md) per la finestra su cui è stato calcolato ciascun risultato.

!!! warning "La concentrazione non è automaticamente un difetto"

    Nessuno dei due valori è un punteggio. Un portafoglio deliberatamente concentrato è una scelta, e un elevato numero di asset effettivi non è di per sé un risultato — come mostra la tabella sopra, può essere riportato da un portafoglio che detiene dieci versioni della stessa scommessa.

---

## 🔗 Correlati {: #related }

- 🔗 **[Correlazione](correlation.md)** — il comportamento a coppie che il rapporto di diversificazione riassume
- 🧩 **[Contributo al rischio](risk-contribution.md)** — quali posizioni portano il rischio, una volta combinati pesi e co-movimenti
- 📊 **[Volatilità](volatility.md)** — la grandezza rispetto alla quale il rapporto di diversificazione confronta
- 🧪 **[Qualità dei dati](data-quality.md)** — la finestra su cui sono state stimate volatilità e correlazioni
