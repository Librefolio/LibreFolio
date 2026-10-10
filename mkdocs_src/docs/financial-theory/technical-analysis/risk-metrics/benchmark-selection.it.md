# 🎯 Selezione del benchmark

Ogni cifra relativa porta con sé un passeggero invisibile: la cosa rispetto a cui è stata misurata. "Il portafoglio ha battuto il mercato di tre punti" non è un'affermazione sul portafoglio — è un'affermazione sul portafoglio **e** su qualunque cosa sia stata chiamata "il mercato". Cambia il secondo termine e il verdetto cambia con esso, senza che una singola posizione si sia mossa.

Questa pagina riguarda quel secondo termine. La scelta del confronto non è una preferenza di visualizzazione applicata dopo l'analisi: fa parte del risultato.

---

## 🔢 Cosa significa "Relativo" {: #what-relative-means }

Data una serie di rendimenti primaria $r_p$ e una serie di confronto $r_b$ osservate nelle stesse date, LibreFolio deriva le cifre relative dalla coppia.

**Il rendimento attivo** è la differenza tra i due rendimenti del periodo di detenzione, ciascuno composto sull'intervallo condiviso:

$$\text{Active} = \left[ \prod_{t=1}^{N} (1 + r_{p,t}) - 1 \right] - \left[ \prod_{t=1}^{N} (1 + r_{b,t}) - 1 \right]$$

È una differenza di rendimenti composti sull'intervallo effettivamente condiviso dalle due serie — non una cifra annualizzata e non un rapporto.

**Il beta** misura quanto fortemente la serie primaria ha risposto a quella di confronto:

$$\beta = \frac{\mathrm{Cov}(r_p, r_b)}{\mathrm{Var}(r_b)}$$

Il denominatore è la chiave dell'intera pagina: il beta è la covarianza **divisa per la varianza del benchmark**. Tutto ciò che il benchmark fa — o non riesce a fare — si propaga nella cifra.

**La correlazione** viene calcolata con lo stesso stimatore della [matrice di correlazione](correlation.md), e risponde alla domanda se il confronto sia persino rilevante: un beta misurato rispetto a qualcosa che il portafoglio non traccia descrive una relazione che non esiste.

---

## 💡 Interpretazione {: #interpretation }

Le tre cifre rispondono a domande diverse e vanno lette insieme.

| Figura | Domanda a cui risponde |
|---|---|
| Rendimento attivo | Il portafoglio ha chiuso l'intervallo condiviso davanti o dietro il confronto? |
| Beta | Quanto è stata amplificata la risposta del portafoglio ai movimenti del confronto? |
| Correlazione | Il confronto era davvero un riferimento significativo? |

La correlazione viene prima in pratica. Il rendimento attivo e il beta restano aritmeticamente ben definiti rispetto a un confronto che il portafoglio ignora completamente, e lì sono privi di significato — una bassa correlazione è il segnale che il benchmark era la domanda sbagliata, non che il portafoglio fosse la risposta sbagliata.

### 🧭 Perché la scelta è già metà del verdetto {: #why-the-choice-is-already-half-the-verdict }

Un singolo portafoglio azionario globale confrontato con un ampio indice mondiale, con un indice domestico e con un fondo obbligazionario produrrà tre rendimenti attivi diversi, tre beta diversi e tre impressioni diverse — dalle stesse posizioni nelle stesse date. Nessuno dei tre è un errore di misurazione. Rispondono a tre domande diverse, e la domanda è stata scelta quando è stato scelto il benchmark.

La conseguenza pratica è una regola di comparabilità: **due cifre relative possono essere confrontate tra loro solo se sono state misurate rispetto allo stesso benchmark**. Un beta non è una proprietà di un portafoglio; è una proprietà di un portafoglio *e* di un riferimento. LibreFolio registra l'asset di confronto nei metadati del risultato stesso proprio perché una cifra non possa mai essere separata dal riferimento che l'ha prodotta.

---

## 🧮 Cosa può servire come benchmark {: #what-can-serve-as-a-benchmark }

Il confronto non è libero. L'analisi prende un **asset reale che esiste nei tuoi dati** come riferimento, identificato esplicitamente, e da ciò derivano tre cose.

**Deve esistere.** Un confronto con un asset sconosciuto non viene eliminato silenziosamente né sostituito con un valore predefinito: l'analisi non restituisce alcun valore, segnala parametri non validi e indica il nome dell'asset richiesto.

**Deve avere uno storico prezzi utilizzabile.** La serie del benchmark viene preparata esattamente come le posizioni in analisi, sullo stesso calendario condiviso e nella stessa valuta obiettivo. Se non è possibile costruire una serie utilizzabile per esso, il risultato è non disponibile anziché approssimato.

Il selettore del benchmark chiede al motore quali asset dispongono di un proprio storico prezzi utilizzabile nel periodo di analisi e nella valuta obiettivo, ed elenca gli altri a parte, in sola lettura, ciascuno con le motivazioni del motore. Un benchmark scelto in precedenza che non supera questo controllo resta scelto e mostrato nel selettore, ma non viene misurato nulla rispetto a esso. Se il controllo non può essere effettuato, nulla viene bloccato.

**Deve muoversi.** Il beta divide per la varianza della serie di confronto, quindi un riferimento che non si muove mai non ha varianza per cui dividere: il beta risulta indefinito, e anche la correlazione con esso, ed entrambi generano un avviso esplicito anziché un numero. Per questo un riferimento piatto — una costante, un ipotetico tasso di rendimento fisso — non può funzionare come benchmark qui. Il vincolo non è una politica che potrebbe essere derogata; è l'aritmetica del rapporto.

!!! info "Un benchmark non è una soglia"

    Il confronto risponde a "rispetto a cosa?", non a "è buono?". Un portafoglio che resta indietro rispetto a un benchmark in salita e uno che cade meno di un benchmark in crollo producono entrambi una cifra; nessuna delle due cifre sa se l'investitore dovrebbe essere soddisfatto. Quel giudizio richiede l'obiettivo, che vive al di fuori della metrica.

---

## 📏 L'intervallo condiviso {: #the-shared-window }

Due serie raramente coprono esattamente le stesse date, quindi il confronto viene calcolato sull'**intersezione** dei due calendari: in ciascuna data condivisa, ciascuna serie contribuisce con i propri rendimenti dalla data condivisa precedente — per la prima, dalla data precedente della serie primaria — composti in uno. Un benchmark quotato nei giorni che la serie primaria salta — un crypto-asset nel fine settimana, accanto a un portafoglio letto nei suoi [giorni di osservazione](data-quality.md#coverage) — mantiene quei movimenti.

Tre conseguenze vengono pubblicate con il risultato.

**Si applica un minimo.** Sotto le 20 osservazioni condivise il confronto non viene calcolato affatto: il risultato viene restituito come non disponibile con una motivazione di storico insufficiente che riporta sia il numero di osservazioni condivise trovate sia il numero richiesto. Un benchmark che si sovrappone appena al tuo storico non produce alcuna cifra anziché una fragile.

**La copertura viene riportata.** Il risultato registra quale frazione delle date proprie della serie primaria è sopravvissuta all'intersezione — vale a dire, in quante delle tue date il riferimento scelto aveva un rendimento proprio. Un benchmark lanciato a metà del tuo periodo di detenzione non confronta silenziosamente mezzo periodo; lo dichiara.

**Il fattore di annualizzazione viene rimisurato sull'intervallo condiviso.** Poiché l'intersezione è generalmente più breve e più rada della finestra di analisi completa, qualsiasi quantità annualizzata nel confronto viene scalata da un fattore misurato sul campione comune anziché ereditato dall'analisi più ampia — la stessa logica del fattore osservato descritta in [Annualizzazione osservata](observed-annualization.md), applicata alla sovrapposizione.

---

## 📈 La linea rischio/rendimento {: #the-risk-return-line }

Nella scheda **Rischio** della dashboard e della pagina di un broker, il livello **Sono pagato per questo rischio?** disegna un grafico del rischio rispetto al rendimento — volatilità annualizzata in orizzontale, rendimento medio annuo in verticale. Mostra un punto per ogni posizione, dimensionato in base al suo peso nel portafoglio; uno per il portafoglio stesso, come composto oggi e riprodotto sull'intervallo; uno per il benchmark, disegnato come un rombo; e una linea retta tratteggiata.

La linea parte sull'asse verticale al **tasso privo di rischio utilizzato dalla pagina** — lo stesso tasso dei suoi valori dell'indice di Sharpe e dell'indice di Sortino, che oggi è 0 nella dashboard e nella pagina di un broker — e passa **per il benchmark**. In teoria questa è la Capital Market Line, che passa per il *portafoglio di mercato*; qui il benchmark è ciò che sostituisce il mercato:

$$R = R_f + \frac{R_b - R_f}{\sigma_b}\,\sigma$$

dove:

- $\sigma$ è una volatilità annualizzata, e $R$ il rendimento medio annuo che la linea raggiunge a quella volatilità;
- $R_f$ è il tasso privo di rischio utilizzato dalla pagina;
- $R_b$ e $\sigma_b$ sono il rendimento medio annuo del benchmark — il suo rendimento medio per periodo, scalato a un anno — e la sua volatilità annualizzata.

**Come leggerla.** La pendenza, $(R_b - R_f)/\sigma_b$, è il [indice di Sharpe](sharpe-ratio.md) del benchmark: il suo rendimento medio al di sopra del tasso privo di rischio per unità di volatilità. Un punto sopra la linea è stato pagato meglio per il suo rischio rispetto al benchmark — più rendimento medio al di sopra del tasso privo di rischio per unità di volatilità, un indice di Sharpe più alto. Un punto sotto di essa è stato pagato meno. Come ogni cifra relativa su questa pagina, è un confronto con il riferimento, non un voto.

**Scegliere il benchmark per essa.** Poiché il benchmark rappresenta "il mercato", un **ampio indice globale** — ad esempio un tracker di un indice azionario mondiale — è il sostituto più significativo. Un indice domestico, un indice settoriale o un fondo obbligazionario disegnano comunque una linea, ma la trasformano in un confronto con quel riferimento più ristretto: vedi [Perché la scelta è già metà del verdetto](#why-the-choice-is-already-half-the-verdict).

**Se non è stato scelto alcun benchmark** — o se quello scelto non ha potuto essere misurato sull'intervallo — la linea passa invece per **il tuo portafoglio**. Trovarsi sopra di essa significa quindi essere pagati meglio rispetto al portafoglio nel suo complesso, e la pendenza è l'indice di Sharpe del portafoglio.

**Un benchmark che detieni** viene disegnato una volta sola, non come due punti: è il punto della tua posizione, al suo peso, nello stile del benchmark, e la linea passa per esso.

**Nella pagina Asset.** La sua [scheda Correlazione](../../../user/assets/correlation.md#what-did-each-pay), che confronta una selezione di asset che hai messo insieme, disegna la stessa linea quando viene scelto un benchmark e misurato sull'intervallo: parte dal tasso privo di rischio utilizzato dalla pagina — 0 oggi, come nella dashboard — e passa per il rombo del benchmark, quindi la sua pendenza è l'indice di Sharpe del benchmark e un punto sopra di essa è stato pagato meglio per il suo rischio rispetto al benchmark. Un benchmark che è uno degli asset selezionati viene disegnato una volta, come punto proprio di quell'asset nello stile del benchmark, e la linea passa per esso. Senza benchmark, o con uno che non ha potuto essere misurato sull'intervallo, non viene disegnata alcuna linea, perché nessun portafoglio può prendere il posto del benchmark — una selezione non ha pesi e quindi nessun insieme proprio attraverso cui far passare una linea — e il grafico mostra il trade-off e lascia il giudizio a te.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="risk" data-name="lab-risk-return" alt="Cosa ha pagato ciascuno di questi per il proprio rischio? nella scheda Correlazione, con S&P 500 come benchmark: la tabella aperta dalla sua riga colorata, e il grafico con i cerchi degli asset, il rombo del benchmark e la linea tratteggiata dal tasso privo di rischio che passa per esso" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

!!! warning "Solo prezzi, per ora"

    I rendimenti su questo grafico provengono esclusivamente da serie di prezzi: cedole e dividendi non sono ancora inclusi. Una posizione che distribuisce una grande quota del proprio rendimento come reddito si colloca quindi più in basso di dove la collocherebbe il suo rendimento totale — e quando lo fa il benchmark, la linea si inclina verso il basso con esso.

---

## ⚠️ Limitazioni {: #limitations }

!!! warning "Il benchmark è una scelta, e la scelta non è neutrale"

    Poiché sia il beta sia il segno del rendimento attivo dipendono dal riferimento, un confronto scelto dopo aver visto i risultati non è una misurazione — è una narrazione. La sequenza onesta è decidere cosa il portafoglio sta cercando di replicare *prima* di chiedere come si è comportato rispetto a esso.

!!! warning "Le cifre relative non si sommano"

    Beta e rendimenti attivi misurati rispetto a riferimenti diversi appartengono a scale diverse. Confrontare il beta di un asset rispetto a un indice domestico con il beta di un altro asset rispetto a un indice mondiale produce il confronto tra due numeri non correlati che per caso condividono un nome.

!!! warning "I due lati non sono sempre lo stesso tipo di rendimento"

    L'asset di confronto contribuisce sempre con il rendimento della propria serie di prezzi, mentre il lato primario mantiene la base di rendimento di ciò che viene analizzato — un asset o un intero portafoglio. Il risultato registra quale base è stata usata sul lato primario, e vale la pena verificarlo prima di leggere un piccolo rendimento attivo come significativo.

!!! warning "Un calendario condiviso nasconde ciò che scarta"

    Vengono confrontate solo le date presenti in entrambe le serie. Se il riferimento manca proprio durante il tratto turbolento che conta di più, il confronto vede quel tratto come un singolo passo composto — o non lo vede affatto, prima della prima data condivisa del riferimento — anziché come si è svolto. La cifra di copertura è ciò che rende visibile quella perdita — leggila prima di leggere il beta.

---

## 🔗 Voci correlate {: #related }

- 📈 **[Beta e rendimento attivo](beta-active-return.md)** — le due cifre che questa scelta determina
- 🔗 **[Correlazione](correlation.md)** — se il riferimento scelto sia davvero rilevante
- 📅 **[Annualizzazione osservata](observed-annualization.md)** — perché il fattore viene rimisurato sulla sovrapposizione
- 🧪 **[Qualità dei dati](data-quality.md)** — cosa scarta il calendario condiviso, e come viene riportato
- 📐 **[Indice di Sharpe](sharpe-ratio.md)** — la pendenza della linea rischio/rendimento
