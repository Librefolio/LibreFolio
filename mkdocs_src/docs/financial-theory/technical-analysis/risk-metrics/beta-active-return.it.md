# 📐 Beta e rendimento attivo

Beta misura quanto fortemente un portafoglio tende a seguire il suo benchmark, mentre il rendimento attivo isola la parte del risultato che il benchmark non spiega. Entrambi sono valori **relativi**: descrivono un portafoglio solo in compagnia della serie con cui è stato confrontato, e cambiano quando quella serie cambia.

---

## 🔢 Formula {: #formula }

Quattro quantità sono calcolate dalle due serie di rendimenti allineate — il portafoglio, $p$, e la serie di confronto, $b$.

**Beta** è la covarianza campionaria delle due serie divisa per la varianza della serie di confronto:

$$
\beta = \frac{\mathrm{Cov}(r_p, r_b)}{\mathrm{Var}(r_b)}
$$

Entrambi i momenti usano gli stimatori non distorti $(N-1)$, quindi sono richieste almeno due osservazioni comuni.

Il **rendimento attivo** è la differenza tra i due rendimenti composti sull'intera finestra:

$$
AR = \left[\prod_{t=1}^{N} (1 + r_{p,t}) - 1\right] - \left[\prod_{t=1}^{N} (1 + r_{b,t}) - 1\right]
$$

Il **tracking error** è la dispersione della differenza per periodo $a_t = r_{p,t} - r_{b,t}$, annualizzata con il fattore misurato:

$$
TE = \sigma_a \times \sqrt{f}
$$

L'**information ratio** mette in relazione la media di quella differenza con la sua dispersione, annualizzata sulla stessa base:

$$
IR = \frac{\bar{a}}{\sigma_a} \times \sqrt{f}
$$

Il fattore $f$ è lo stesso fattore di annualizzazione osservato usato ovunque altro nell'analisi — calcolato dai dati anziché ipotizzato. Vedi [Annualizzazione osservata](observed-annualization.md).

!!! info "Le due serie devono essere allineate"

    Entrambe le serie vengono confrontate punto per punto, quindi devono coprire le stesse osservazioni: un confronto viene calcolato solo quando le due serie hanno la stessa lunghezza e almeno due osservazioni. L'allineamento viene eseguito prima che si arrivi alle metriche, ed è per questo che un risultato che ha usato una finestra abbreviata lo segnala tramite il suo conteggio delle osservazioni anziché tramite un confronto spostato silenziosamente.

---

## 🚫 Quando il beta non ha valore {: #when-beta-has-no-value }

Il beta non è sempre definito, e quando non lo è, non viene pubblicato alcun numero.

**Una serie di confronto con varianza nulla non produce alcun beta.** Il beta esprime come il portafoglio risponde ai movimenti della serie di confronto; una serie che non si muove non offre nulla a cui rispondere. Matematicamente il denominatore si annulla, e qualsiasi valore restituito al suo posto sarebbe un artefatto dell'aritmetica anziché una misurazione. Il risultato segnala invece l'assenza.

La stessa disciplina si applica all'information ratio: se la differenza per periodo tra le due serie non varia mai, la sua dispersione è zero, e il rapporto non viene pubblicato anziché essere forzato.

!!! info "Un valore assente è un risultato"

    Un beta mancante non è un fallimento del calcolo — è ciò che i dati supportano. Leggerlo come "nessuna relazione" sarebbe la conclusione sbagliata: significa che la serie di confronto non ha fornito alcuna variazione rispetto alla quale una relazione potesse essere misurata in alcun modo.

---

## ➗ Il rendimento attivo è una differenza di rendimenti composti {: #active-return-is-a-difference-of-compounded-returns }

L'ordine delle operazioni conta, ed è la fonte della più comune errata interpretazione di questo numero. Il rendimento attivo applica la capitalizzazione composta a ogni serie sulla finestra **prima** e sottrae **dopo**. Non è la capitalizzazione composta delle differenze per periodo.

Ne derivano tre conseguenze.

**Non si somma nel tempo.** Il rendimento attivo di un anno non è la somma — né la capitalizzazione composta — dei rendimenti attivi dei suoi mesi. Ogni valore appartiene alla finestra su cui è stato calcolato, e le finestre non possono essere concatenate.

**Non è il rendimento di una strategia.** Non è ciò che un investitore avrebbe guadagnato detenendo il portafoglio e vendendo allo scoperto il benchmark: quella posizione capitalizzerebbe la differenza, e comporterebbe anche effetti di finanziamento e ribilanciamento che nessuna sottrazione di due rendimenti composti può rappresentare.

**Non si scompone in abilità.** Il rendimento attivo afferma che il portafoglio ha chiuso la finestra avanti o indietro rispetto al suo confronto, di quell'importo. Non attribuisce nulla: il divario può derivare da esposizioni diverse, da timing diverso, o da un confronto che non è mai stato un metro di paragone appropriato fin dall'inizio.

---

## 💡 Interpretazione {: #interpretation }

**Beta** descrive la sensibilità, non la qualità. Un beta di $1$ significa che il portafoglio ha teso a muoversi in rapporto uno-a-uno con la serie di confronto; sotto $1$ si è mosso meno della serie, sopra $1$ di più. Il segno conta più di qualsiasi soglia: un beta negativo significa che il portafoglio ha teso a muoversi nella direzione opposta.

Vale la pena separare il beta dalla correlazione, perché vengono facilmente confusi. Dalle definizioni di cui sopra, $\beta = \rho_{p,b} \times \dfrac{\sigma_p}{\sigma_b}$: la correlazione cattura solo la *direzione* della relazione, mentre il beta porta con sé anche il rapporto tra le due volatilità. Un portafoglio può seguire da vicino il proprio confronto e avere comunque un beta lontano da $1$ semplicemente perché fluttua più, o meno, della serie che segue. Vedi [Correlazione](correlation.md).

Il **rendimento attivo** è la distanza tra i due traguardi, misurata sulla finestra.

Il **tracking error** è quanto costantemente è stata percorsa quella distanza. È la volatilità della differenza, quindi un valore elevato indica che il portafoglio si è discostato dal proprio confronto frequentemente o bruscamente — in entrambe le direzioni, poiché è una dispersione e non porta segno.

L'**information ratio** mette insieme le due cose: esprime la differenza media per periodo in unità della propria dispersione, annualizzata. Un rapporto più alto significa che la differenza era più regolare rispetto a quanto variava; un rapporto vicino a zero significa che la differenza, qualunque sia il suo segno, è piccola rispetto alla variazione che la circonda. Nessun valore è buono o cattivo di per sé — il valore dipende dalla lunghezza della finestra e dal confronto scelto, e lo stesso numero misurato su una finestra diversa non è la stessa affermazione.

---

## ⚠️ Limitazioni {: #limitations }

!!! warning "Ogni valore qui eredita il proprio benchmark"

    Beta, rendimento attivo, tracking error e information ratio sono tutti misurati *rispetto a* una serie di confronto. Cambia la serie e ognuno di essi cambia, senza che nulla del portafoglio sia cambiato. Un valore relativo citato senza indicare rispetto a cosa è stato misurato è incompleto. Vedi [Selezione del benchmark](benchmark-selection.md).

!!! warning "Beta vede una linea retta, su una finestra"

    Il beta è la pendenza di una relazione lineare stimata sul periodo osservato. Un portafoglio il cui comportamento differisce tra condizioni calme e condizioni di stress viene riassunto da una singola pendenza che non descrive né le une né le altre. E poiché è stimato, una finestra breve produce un valore che riflette la particolare sequenza che la finestra si è trovata a contenere.

!!! warning "La sensibilità non è una spiegazione"

    Un beta vicino a $1$ dice che il portafoglio si è mosso con la serie di confronto; non dice che la serie guida il portafoglio, né che il resto è abilità. Due serie possono muoversi insieme per una causa comune senza alcuna relazione tra loro — la stessa cautela che si applica alla correlazione vale qui, con in più il rapporto tra le volatilità.

---

## 🔗 Correlati {: #related }

- 🎯 **[Selezione del benchmark](benchmark-selection.md)** — la scelta che ogni valore in questa pagina eredita
- 🔗 **[Correlazione](correlation.md)** — direzione della relazione, con il rapporto tra le volatilità rimosso
- 📊 **[Volatilità](volatility.md)** — la dispersione che trasforma una correlazione in un beta
- 📏 **[Annualizzazione osservata](observed-annualization.md)** — il fattore misurato usato per annualizzare tracking error e information ratio
