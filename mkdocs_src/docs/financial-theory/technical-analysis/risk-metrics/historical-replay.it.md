# ⏮️ Replay Storico

Il replay storico applica i movimenti di un reale episodio passato al portafoglio così come è composto oggi, chiedendo cosa farebbe quello stesso episodio adesso.

È la domanda *cosa mi farebbe il 2008?* a cui si risponde aritmeticamente anziché per ricordo — e il valore della risposta dipende interamente dalla comprensione di quale portafoglio viene sottoposto a quell'episodio.

---

## 🔢 Come Viene Calcolato il Replay {: #how-the-replay-is-computed }

Scegli un episodio — un intervallo di date — e l'analisi prende i rendimenti effettivi di ciascuna posizione su quell'intervallo. A ogni asset viene assegnata una unità di ricchezza all'inizio, che si compone da sola:

$$
W_i(t) = W_i(t-1) \cdot \left(1 + r_i(t)\right), \qquad W_i(0) = 1
$$

La ricchezza del portafoglio a ogni passo è la somma ponderata di quegli indici di ricchezza degli asset, più la quota di liquidità:

$$
W_p(t) = c + \sum_i w_i \, W_i(t)
$$

e il rendimento del portafoglio per il periodo è la variazione di quella ricchezza:

$$
r_p(t) = \frac{W_p(t)}{W_p(t-1)} - 1
$$

La quota di liquidità $c$ assume per impostazione predefinita quanto rimane dai pesi degli asset, $c = 1 - \sum_i w_i$, e i pesi più la liquidità devono sommare a $1$. Tutte le serie devono scorrere su un unico calendario comune; i rendimenti inferiori a $-100\%$ e i pesi negativi vengono rifiutati.

---

## 🧭 Nulla Viene Ribilanciato {: #nothing-is-rebalanced }

I pesi $w_i$ moltiplicano indici di ricchezza degli asset che crescono separatamente. Solo i pesi **iniziali** vengono imposti: dal secondo periodo in poi, la composizione effettiva è quella che la capitalizzazione ha determinato.

Ciò è deliberato, ed è il significato di *buy and hold*. Durante un crollo, gli asset che scendono di più si riducono come quota del portafoglio da soli — nessuna regola li vende, e nessuna regola li ricostituisce. Un replay ribilanciato sarebbe un esercizio diverso, perché il ribilanciamento acquista ciò che è caduto e riporterebbe un esito differente per lo stesso episodio.

!!! info "La liquidità rende esattamente zero"

    La quota di liquidità contribuisce con una costante alla ricchezza del portafoglio in ogni periodo. Non è una scelta neutrale, è una scelta specifica con conseguenze in entrambe le direzioni: durante un crollo, la liquidità è la parte del portafoglio che mantiene il suo valore, e renderà la perdita riprodotta più contenuta di quanto suggerirebbero le sole posizioni investite. Su un arco lungo o inflazionistico, un rendimento nominale nullo è una perdita reale che il replay non mostra, perché il replay è espresso in termini nominali.

---

## ❓ Quale Portafoglio Viene Riprodotto {: #whose-portfolio-is-being-replayed }

Questo è il punto su cui il risultato viene più spesso frainteso.

!!! warning "Questo non è come si è comportato il tuo portafoglio"

    Il replay proietta all'indietro le posizioni **odierne**. Risponde a *come se la sarebbe cavata il portafoglio che detengo ora in quell'episodio?* — non a *come me la sono cavata io?* Le due cose coincidono solo se la composizione non è mai cambiata, e divergono ogni volta che una posizione è stata acquistata, venduta o ridimensionata. La performance passata effettiva è materia di registro ed è riportata altrove; questa cifra è un'ipotesi su una composizione che, in molti casi, non esisteva a quelle date.

C'è una seconda conseguenza, più silenziosa. Il portafoglio detenuto oggi è quello che è **sopravvissuto** a ogni decisione presa da allora: le posizioni vendute, comprese quelle vendute perché andavano male, non ne fanno parte. Proiettarlo all'indietro porta con sé quella selezione, quindi un replay di un episodio negativo può apparire più confortevole di quanto l'episodio sia stato realmente — non perché l'aritmetica sia sbagliata, ma perché l'aritmetica viene applicata a un insieme di posizioni scelte con il beneficio di tutto ciò che è accaduto in seguito.

---

## 🧩 Posizioni Senza Storia Sufficiente {: #holdings-without-enough-history }

Un episodio del 2008 non può essere riprodotto su un fondo lanciato nel 2019: non ci sono rendimenti da applicare. L'analisi non colma il vuoto con un'assunzione né si ferma: **esclude la posizione** e riproduce le altre.

Ogni posizione viene giudicata sulle proprie quotazioni, non sul calendario condiviso. Partecipa solo se è quotata a entrambe le estremità della finestra, con una tolleranza di sette giorni di calendario della [soglia di obsolescenza](data-quality.md#staleness-threshold): all'inizio, una quotazione nei sette giorni precedenti l'inizio della finestra — oppure, per una storia che inizia dentro la finestra, una prima quotazione non più di sette giorni dopo l'inizio della finestra; alla fine, un'ultima quotazione non più di sette giorni prima della fine della finestra. Il test viene eseguito prima che le serie di rendimenti siano preparate, e l'ordine conta. Le serie riprodotte condividono un unico calendario (vedi [Limitazioni](#limitations)): una posizione che inizia tardi, se mantenuta, sposterebbe l'inizio di quel calendario e accorcerebbe il replay di ogni altra posizione per adattarsi alla propria.

### 🏷️ Perché una Posizione Viene Esclusa {: #why-a-holding-is-left-out }

Ogni posizione esclusa porta esattamente una motivazione:

| Motivazione | Cosa mostrano le quotazioni della posizione |
|---|---|
| Nessun prezzo nel periodo | Nessuna quotazione dentro la finestra, e nessuna nei sette giorni precedenti il suo inizio. |
| Prima quotazione dopo l'inizio del periodo | La sua storia inizia dentro la finestra, più di sette giorni dopo l'inizio. |
| Nessun prezzo recente all'inizio del periodo | Era quotata prima della finestra, ma non nei sette giorni precedenti il suo inizio — un vuoto in una storia più vecchia, o un ritmo rado come un NAV mensile. |
| Nessun prezzo recente alla fine del periodo | Nessun prezzo negli ultimi sette giorni della finestra. Le quotazioni vengono lette solo fino alla fine della finestra, quindi un vuoto e una cancellazione dalla quotazione appaiono uguali lì e condividono questa motivazione. |
| Nessun tasso di cambio verso la tua valuta | Nessun tasso di cambio dalla sua valuta verso la valuta in cui è espressa l'analisi. |
| Esclusa da te | Il lettore l'ha esclusa a mano, dove ciò è possibile — vedi [Proxy](#proxies). |

### ⚖️ Cosa Prende il Suo Posto {: #what-takes-its-place }

Ciò che diventa una posizione esclusa dipende dal fatto che il replay abbia dei pesi.

**Su un portafoglio** — la scheda Risk della dashboard o della pagina di un broker — la posizione esce dal replay, ma il suo peso no. Il peso escluso viene aggiunto alla quota di liquidità $c$, il che significa che viene riprodotto come **rendimento esattamente zero** per l'intero episodio. Quello zero appartiene al totale, non alla posizione: la posizione non ottiene un rendimento proprio, e l'elenco dei rendimenti per posizione riporta solo le posizioni che sono state riprodotte — uno zero tra esse dichiarerebbe un rendimento che nessuno ha misurato.

Questo trattamento merita un momento di riflessione, perché non è neutrale. Escludere una posizione non rende il portafoglio più piccolo; rende piatta quella frazione del portafoglio. In un episodio in cui tutto è caduto, una posizione del 10% mantenuta piatta è un'affermazione implicita che sarebbe stata la cosa migliore che possedevi. Nessuno fa quell'affermazione di proposito — il motore la applica da solo — ed è per questo che il risultato nomina ogni posizione esclusa, con la sua motivazione e la sua quota del valore.

**Su una selezione di asset senza pesi** — la [scheda Correlation](../../../user/assets/correlation.md) della pagina Assets — non c'è una quota di liquidità che tenga qualcosa. L'asset viene semplicemente omesso: non ottiene alcun rendimento, non un rendimento pari a zero, e le cifre parlano per gli asset che sono stati riprodotti. Una selezione non ha una composizione da sommare, quindi quei rendimenti per asset sono la risposta completa.

### 🔎 Cosa Mostra il Risultato {: #what-the-result-shows }

Su quelle tre schede, il replay dichiara ciò che ha escluso prima delle cifre che riporta:

- un avviso **sopra tutto il resto** quando più della metà del valore del portafoglio viene esclusa, che dichiara la quota ancora coperta dal risultato: oltre quel punto il totale parla per una minoranza del portafoglio, con il resto mantenuto piatto accanto;
- non appena una posizione viene esclusa, un riquadro **sopra il totale, dove presente, e la tabella** elenca le posizioni escluse, **raggruppate per motivazione**, ciascuna come badge con la sua icona e il suo nome — su un portafoglio anche con la sua quota del valore, sotto una riga che dichiara quanto del valore conta come liquidità a rendimento zero. Il [periodo comune](#the-common-period), quando esiste, è offerto nello stesso riquadro;
- la tabella elenca solo le posizioni che sono state **riprodotte**, dalla peggiore in poi — un clic sul titolo di una colonna ordina per quella colonna — ciascuna in una riga: il suo **Weight**; il suo **Return**, il proprio sul periodo; il suo **Contribution**, il peso per quel rendimento, così che i contributi sommino al totale; il suo **Impact**, l'importo guadagnato o perso; e il suo **Effect**, una barra in una colonna che puoi allargare trascinando il bordo del suo titolo. La barra mostra il contributo su un portafoglio e il rendimento su una selezione. Cresce da una linea dello zero al centro della colonna — le perdite a sinistra in rosso, i guadagni a destra in verde — su un'unica scala condivisa da ogni riga, con l'ampiezza maggiore che raggiunge il bordo. Una posizione esclusa non ha [un rendimento proprio](#what-takes-its-place), quindi non riceve una riga, non una riga a zero;
- una colonna che non ha nulla da mostrare viene omessa, non riempita con trattini: una selezione di asset non ha pesi, né contributi, né denaro, quindi la sua tabella mostra solo **Return** ed **Effect**;
- quando ogni posizione è esclusa, nessuna cifra: il risultato dichiara che non c'è **nulla da riprodurre**, ed elenca le motivazioni.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="risk" data-name="lab-replay" alt="Cosa succede se…? nella scheda Correlazione dopo Esegui replay: il riquadro degli asset esclusi, come badge raggruppati per motivo, con il pulsante del periodo comune, sopra la tabella degli asset ripercorsi, con Rendimento ed Effetto" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

### 📆 Il Periodo Comune {: #the-common-period }

Quando sono i bordi della finestra a escludere delle posizioni — un inizio tardivo, un vuoto prima della finestra, nessun prezzo recente alla sua fine — l'analisi propone la parte della finestra in cui anch'esse sono quotate. Quella parte inizia il giorno dopo la più recente delle prime quotazioni, dentro la finestra, di una posizione senza prezzo all'inizio, così che questa quotazione diventi il suo prezzo di partenza; termina alla più antica delle ultime quotazioni di una posizione senza prezzo recente alla fine. Prima che venga proposta, una seconda lettura delle quotazioni su quella finestra più breve la conferma: ogni posizione che riporta indietro, e ogni posizione già coperta dalla finestra, deve essere quotata a entrambe le sue estremità, altrimenti nulla viene proposto. Una posizione esclusa per non avere prezzi nella finestra, o per non avere tasso di cambio, non ne fa mai parte: nessuna finestra più breve la riporterebbe indietro.

Su quelle schede, la proposta è un pulsante dentro il riquadro che elenca ciò che è stato escluso: mostra le sue date e quante posizioni riporta indietro, e un clic la riproduce — anche quando nulla è potuto essere riprodotto sulla finestra originale. Quando il replay è stato eseguito su una delle crisi predefinite — ancora scelta nel menu, alle date proprie della crisi — e la proposta è più breve, questa viene contrassegnata come se coprisse solo una parte della crisi. Questo è il compromesso: recuperi le posizioni, ma riproduci un tratto più breve dell'episodio, e qualunque cosa il mercato abbia fatto fuori da quel tratto non è più nella risposta. Scegliere **No preset**, un intervallo rapido o una data propria mette da parte la crisi: il replay successivo è di un periodo, non più della crisi, e non porta tale contrassegno.

### 🎭 Proxy {: #proxies }

Un proxy consente alla serie di rendimenti di un altro asset di sostituire una posizione priva di storia. Esiste in un solo posto: la scheda **Risk & Scenarios** della pagina di dettaglio di un asset, per quel solo asset, dove il lettore può scegliere per esso un proxy o escluderlo invece. Una posizione con proxy viene riprodotta sui rendimenti del suo proxy invece di essere esclusa, e un proxy senza rendimenti utilizzabili sulla finestra viene rifiutato come scelta non valida, mai eliminato silenziosamente. Il replay sulle tre schede di cui sopra non offre né un proxy né un'esclusione manuale.

!!! warning "Un proxy è una scelta, non un fatto"

    Sostituire una posizione con un proxy cambia il significato del risultato. Non dice più cosa sarebbe accaduto a quella posizione; dice cosa sarebbe accaduto **se quella posizione si fosse comportata come il suo sostituto** in quell'episodio. Quella condizione fa parte della risposta, non è una nota a piè di pagina — un indice ampio che fa da proxy a una posizione concentrata sottostimerà come quella posizione si sarebbe mossa, e nessuna parte dell'aritmetica può rilevare la discrepanza. Il risultato registra quali posizioni sono state sostituite con proxy.

---

## 💡 Interpretazione {: #interpretation }

Il replay produce un rendimento composto per l'episodio, e sotto di esso un rendimento per ogni posizione che ha riprodotto. Leggili come un'**affermazione condizionale**: *questa composizione, attraverso quelle date specifiche, senza ribilanciamento, liquidità piatta — e piatta con essa ogni posizione che il motore ha escluso — e un proxy solo dove ne è stato scelto uno*. Su una selezione di asset non c'è una composizione da capitalizzare e nulla è mantenuto piatto: i rendimenti per asset stanno da soli, per gli asset che hanno potuto essere riprodotti.

La sua forza è che ogni numero in esso è accaduto. La sequenza dei rendimenti è quella che il mercato ha consegnato — il percorso di drawdown, il raggruppamento dei giorni negativi, la velocità della ripresa sono tutti reali, che è esattamente ciò che un riepilogo distribuzionale non può riprodurre. La sua debolezza è l'immagine speculare: è **un** episodio. È accaduto una volta, e il prossimo stress non ne sarà una copia.

Un replay quindi non è una previsione né una probabilità. È una misurazione dell'esposizione rispetto a un evento noto — utile perché l'evento è noto, e limitata per la stessa ragione.

---

## ⚠️ Limitazioni {: #limitations }

!!! warning "Un episodio è un campione singolo"

    Riprodurre un singolo tratto storico dice cosa farebbe quel tratto. Non delimita ciò che potrebbe fare un tratto futuro, e scegliere l'episodio peggiore del registro non rende il risultato un caso peggiore — lo rende il caso peggiore *nel registro*.

!!! warning "La composizione è fissa a quella odierna"

    Le posizioni aperte dopo l'episodio, le posizioni nel frattempo chiuse, e ogni variazione di dimensione nel mezzo sono assenti per costruzione. Più l'intervallo del replay è lontano da oggi, più il portafoglio riprodotto è un costrutto anziché una storia.

!!! warning "I rendimenti vengono presi come sono misurati"

    Il replay prepara le sue serie di rendimenti come fa il resto dell'analisi, ma sulla finestra del suo episodio e per gli asset che riproduce, con ciascun proxy al posto della posizione che rappresenta. Quelle serie condividono un unico calendario, costruito come descritto in [Qualità dei dati](data-quality.md#alignment-what-missing-data-actually-costs): ogni data della finestra in cui almeno uno di quegli asset ha una quotazione propria, mantenuta ovunque ognuno di essi possa essere valutato, se necessario a un prezzo mantenuto da una data precedente. Vuoti, prezzi mantenuti e conversione di valuta raggiungono tutti il replay attraverso quelle serie. Vedi [Qualità dei dati](data-quality.md) per ciò che l'analisi riporta sulle serie che ha utilizzato.

---

## 🔗 Correlati {: #related }

- ⚡ **[Shock ipotetico](hypothetical-shock.md)** — la stessa domanda con uno scenario scelto invece che storico
- 📉 **[Drawdown massimo](max-drawdown.md)** — la caduta peggiore lungo un percorso, e [quanto è durata la ripresa](max-drawdown.md#recovery-time)
- 📍 **[Drawdown attuale](current-drawdown.md)** — dove si trova oggi il portafoglio, prima che venga applicato qualsiasi scenario
- 🧩 **[Contributo al rischio](risk-contribution.md)** — quali posizioni portano il rischio su cui agirebbe un episodio
- 🧪 **[Qualità dei dati](data-quality.md)** — le serie su cui è stato eseguito il replay
