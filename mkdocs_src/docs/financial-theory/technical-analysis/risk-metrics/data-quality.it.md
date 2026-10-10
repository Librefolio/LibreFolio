# 🧪 Qualità dei dati

Una misura di rischio è affidabile solo quanto le osservazioni che ne stanno alla base, perciò la quantità e la freschezza dei dati sottostanti fanno parte della lettura del risultato. LibreFolio non tiene nascosto questo livello: ogni risultato di rischio viaggia con un report dei dati di origine, uno stato da esso derivato e — quando mancava qualcosa — l'elenco di ciò che mancava.

---

## 🚦 Stato dei dati di origine {: #source-data-status }

I dati di origine sono classificati su tre livelli:

| Stato | Cosa significa |
|---|---|
| `ok` | Nulla manca e nulla è stato mantenuto oltre la [soglia di obsolescenza](#staleness-threshold). La serie è ciò che dichiara di essere. |
| `carried_forward` | Nulla manca del tutto, ma alcuni prezzi o tassi di cambio sono stati mantenuti da una data precedente per un periodo superiore alla soglia di obsolescenza — quotazioni obsolete, punti prezzo mantenuti, punti FX mantenuti. |
| `partial` | Qualcosa manca del tutto: prezzi, coppie FX, date all'interno della finestra analizzata in cui non tutte le posizioni potevano essere valutate, coppie di valute irrisolte o asset che non potevano partecipare affatto. |

Due proprietà di questa scala contano più delle etichette.

**È derivato, non dichiarato.** Lo stato è una proprietà calcolata dei contenuti stessi del report: un produttore non può dichiarare `ok` mentre segnala prezzi mancanti, perché lo stato viene ricalcolato da ciò che il report contiene. Qualunque cosa manchi del tutto produce `partial`; se nulla manca ma qualcosa è stato mantenuto oltre la soglia di obsolescenza, `carried_forward`; altrimenti `ok`. `partial` ha la precedenza su `carried_forward`.

**È categorico, non numerico.** Lo stato risponde a *che tipo di imperfezione è presente*, mai a *quanto è tollerabile*. Non esiste un livello di completezza al di sotto del quale il sistema dichiari una misura inaffidabile — quel giudizio è lasciato al lettore, deliberatamente ed esplicitamente.

### ⏳ La soglia di obsolescenza {: #staleness-threshold }

Un prezzo o un tasso di cambio mantenuto da una data precedente è normale di per sé: weekend, festività e strumenti quotati sui propri calendari di mercato lasciano continuamente lacune — e un prezzo memorizzato in un weekend o in un giorno festivo di mercato che ripete solo la chiusura precedente è anch'esso mantenuto, non quotato (vedi [Carry memorizzati](#stored-carries)). Un valore mantenuto diventa **obsoleto** solo quando è più vecchio di **sette giorni di calendario** rispetto alla data che sostituisce, e solo uno obsoleto conta contro la serie per asset di un'analisi: viene registrato come punto prezzo o FX mantenuto, e uno solo è sufficiente per `carried_forward`. Uno più recente non degrada nulla, ma non è invisibile: un prezzo mantenuto dà comunque un rendimento di periodo pari a zero, e quel rendimento entra nel campione (vedi [Limitazioni](#limitations)). La soglia decide cosa conta come imperfezione, non quante imperfezioni sono tollerabili.

Questi sette giorni di calendario sono l'unica soglia di obsolescenza del progetto, non una convenzione di questa pagina: il [laboratorio di correlazione](../../../user/assets/correlation.md) della pagina Asset e il replay storico giudicano l'età di un prezzo con gli stessi sette giorni, e gli avvisi che segnalano prezzi o tassi di cambio obsoleti la citano.

### 🔁 Carry memorizzati {: #stored-carries }

Non ogni prezzo mantenuto arriva come una lacuna. Alcune fonti forniscono una riga per ogni giorno di calendario, ripetendo l'ultima chiusura nei giorni in cui il loro mercato è chiuso: justETF, per esempio, ripete la chiusura del venerdì il sabato e la domenica. Lette come quotazioni, quelle righe inserirebbero in ogni serie costruita da esse un rendimento pari a zero, nella valuta dell'asset, che nessun mercato ha prodotto. Quindi un prezzo memorizzato è un **carry**, non una quotazione, quando valgono entrambe queste condizioni:

- è datato di sabato o domenica, oppure in un giorno feriale che è festivo in almeno uno dei principali mercati — l'unione dei calendari forniti da QuantLib per TARGET, Borsa Italiana, Xetra, Euronext Paris, London Stock Exchange, Svizzera e NYSE;
- la sua chiusura, nella valuta dell'asset, è **esattamente** la chiusura della riga precedente, senza tolleranza.

Tre tipi di riga restano quotazioni: il primo prezzo di una serie, che non ha una riga precedente; un prezzo invariato in un normale giorno feriale, perché una giornata piatta di un'obbligazione o di un fondo monetario è reale; e un prezzo che si è mosso in un weekend o in un giorno festivo, come fa quello di un crypto-asset. L'unione dei mercati è sicura perché la regola richiede anche la ripetizione esatta: uno strumento che ha scambiato mentre un altro mercato era chiuso si è quasi sempre mosso, e un prezzo che si è mosso resta una quotazione — nel peggiore dei casi, una giornata genuinamente piatta in una data del genere viene letta come carry. La tabella dei giorni festivi viene costruita all'avvio del server; se non è stato possibile costruirla, si applicano solo i weekend fino a quando un tentativo successivo riesce.

Un carry è l'ultima quotazione genuina mantenuta, ed è datato da quella quotazione, quindi in un normale weekend ha uno o due giorni di età — ben dentro la soglia di obsolescenza. La sua data non è una data di quotazione dell'asset. Non aggiunge alcun candidato al [calendario condiviso](#alignment-what-missing-data-actually-costs), nessun giorno di osservazione a una serie di rendimenti di portafoglio (vedi [Copertura](#coverage)), e nulla alle quotazioni che decidono se un asset può partecipare a un'analisi di un insieme di asset — almeno 20 nel periodo, il minimo che le analitiche statistiche accettano — o a un [replay storico](historical-replay.md), che richiede che l'asset sia prezzato a entrambe le estremità della sua finestra. Dove la quotazione di un altro asset mette comunque la data su un calendario condiviso, l'asset viene valutato lì alla sua ultima quotazione genuina, e quel punto conta come mantenuto nella misura di freschezza sotto [Copertura](#coverage).

---

## 📋 Cosa registra il report {: #what-the-report-records }

Il report è un inventario, non un punteggio:

| Segnale | Cosa cattura |
|---|---|
| Asset con prezzi mancanti | Posizioni per cui non è stato possibile ottenere un prezzo utilizzabile |
| Coppie FX mancanti / irrisolte | Conversioni di valuta che non è stato possibile risolvere |
| Prezzi obsoleti | Posizioni il cui prezzo più recente è più vecchio della [soglia di obsolescenza](#staleness-threshold) |
| Punti prezzo mantenuti | Quanti punti prezzo sono stati mantenuti oltre la soglia di obsolescenza e per quali asset |
| Punti FX mantenuti | Quanti punti di conversione sono stati mantenuti oltre la soglia di obsolescenza e per quali coppie |
| Date incomplete | Date in cui valutazione, NAV, valore contabile o allocazione non è stato possibile completare per ogni posizione |
| Asset inutilizzabili | Asset esclusi prima che qualsiasi metrica fosse tentata, ciascuno con una motivazione |
| Avvisi | Note in forma libera aggiunte dalla fase di produzione |

Ogni voce nomina l'oggetto a cui si riferisce — l'asset, la coppia di valute, la data. Un lettore può chiedere *quale* asset, coppia di valute o data ha degradato la misura, non semplicemente *se* qualcosa lo ha fatto.

---

## 🧮 Allineamento: quanto costano davvero i dati mancanti {: #alignment-what-missing-data-actually-costs }

Quando un'analisi copre più posizioni — una matrice di correlazione, una scomposizione del contributo al rischio — viene calcolata su un **unico calendario condiviso**, e la costruzione di quel calendario è il punto in cui i dati mancanti si trasformano in un costo visibile.

1. Una data è candidata se almeno una posizione aveva una quotazione fresca in quella data, un [carry memorizzato](#stored-carries) non contando come tale: i candidati sono l'unione dei calendari di quotazione delle posizioni nella finestra richiesta.
2. Una data candidata entra nell'analisi solo se **ogni** posizione poteva essere valutata in essa. Qui *valutata* include un prezzo o un tasso di cambio mantenuto da una data precedente, senza limite di età, quindi in pratica il test fallisce solo prima del primo prezzo utilizzabile di una posizione, o dove non è stato possibile risolvere la sua conversione nella valuta obiettivo. Le date che falliscono questo test vengono scartate per tutte le posizioni, ma sono registrate come date di valutazione incomplete solo dopo che il calendario è iniziato — cioè dopo la baseline.
3. La baseline è l'ultima data prima dell'inizio richiesto in cui tutte le posizioni erano valutabili; se non ce n'è nessuna, l'analisi inizia invece all'interno della finestra richiesta, nella prima data in cui ogni posizione può essere valutata, e le posizioni responsabili dell'inizio tardivo vengono nominate.

La conseguenza va detta chiaramente: **una posizione che inizia tardi accorcia la finestra per tutti**. Una lacuna all'interno di uno storico non accorcia nulla, perché il prezzo o il tasso di cambio mancante viene mantenuto. Nulla viene interpolato: un prezzo o un tasso mantenuto è l'ultimo conosciuto. Una volta che è stato mantenuto oltre la [soglia di obsolescenza](#staleness-threshold), viene conteggiato come punto mantenuto — una questione per lo stato `carried_forward`, non per la lunghezza della finestra. Uno più recente non degrada lo stato, sebbene un prezzo mantenuto, qualunque sia la sua età, conti comunque contro la misura di freschezza descritta sotto [Copertura](#coverage). Una posizione non è mai parzialmente inclusa in un calcolo congiunto — o la data funziona per tutte o non è un'osservazione. Un inizio tardivo da solo non rende il risultato `partial`: le date che costa non sono elencate come incomplete, il report nomina le posizioni responsabili nelle sue voci `short_history`, e la perdita si vede nel conteggio delle osservazioni e nella copertura del calendario condiviso di seguito. Una data persa dopo che il calendario è iniziato è diversa: viene elencata come incompleta e rende il risultato `partial`.

---

## 📏 Copertura {: #coverage }

La copertura è normalmente il complemento di densità dello stato: risponde a *quanto di ciò che poteva essere osservato lo è stato effettivamente*. Rapporti diversi portano quel nome. Non condividono alcun denominatore e non misurano tutti lo stesso tipo di cosa: due contano osservazioni, un terzo conta posizioni e non contiene alcuna osservazione.

**Quanto è costato il calendario condiviso?** Delle date in cui almeno una posizione aveva una quotazione fresca, questa è la quota che ha superato il requisito che ogni posizione fosse valutabile. Una misura ben sotto 1 significa che in molte delle date in cui qualche posizione era quotata, un'altra non poteva essere valutata — e poiché le lacune vengono mantenute, questo di solito indica una posizione il cui storico inizia ben dopo l'inizio richiesto, o conversioni che non è stato possibile risolvere, piuttosto che lacune.

**Quanto dei dati è davvero fresco?** Sulla griglia posizioni × osservazioni, questa è la quota di punti il cui prezzo è stato quotato in quella data anziché mantenuto da una precedente. Misura lo stesso tipo di imperfezione dello stato `carried_forward`, ma solo sulle osservazioni e con una soglia più severa: ogni prezzo mantenuto conta contro di essa, per quanto recente, mentre lo stato conta solo quelli mantenuti oltre la soglia di obsolescenza. Inoltre conta solo i prezzi: una quotazione fresca ma che ha dovuto essere convertita con un tasso di cambio mantenuto conta comunque come fresca, perché le conversioni mantenute sono tracciate come segnale separato. Quindi una quota sotto il 100% non significa di per sé `carried_forward`, e una quota del 100% non lo esclude di per sé — né, quindi, un risultato `partial`.

**Quanta parte del portafoglio è potuta essere classificata?** Delle posizioni nell'ambito, questa è la quota per cui i metadati di settore o geografia erano disponibili, invece che mancanti e tali da mandare la posizione nel contenitore generico `Other` al 100%. Questa è un'affermazione sui metadati: nessun prezzo, nessuna data e nessuna osservazione vi entra. Uno [shock ipotetico](hypothetical-shock.md) riporta questo rapporto.

!!! warning "Un nome condiviso, due tipi di quantità"

    Quando la misura è una misura di densità, il suo denominatore dipende dal percorso. Per un'analisi costruita da quotazioni di strumenti sono le date di quotazione candidate. Per una serie di portafoglio sono i **giorni di osservazione** del portafoglio: l'analisi legge la serie di rendimenti propria del portafoglio, il suo [rendimento time-weighted](../performance-metrics/portfolio-engine/twrr.md), solo nei giorni in cui almeno una posizione dell'ambito aveva una quotazione propria, e concatena il rendimento di ogni altro giorno nel successivo; il denominatore conta quei giorni lungo l'intervallo — o ogni giorno di calendario coperto, se nessuna posizione aveva una quotazione propria nella finestra. Su una serie di portafoglio quella misura è alta per costruzione — lo storico del portafoglio ha un punto per ogni giorno di calendario, mantenendo l'ultimo valore noto dove nulla è stato quotato, quindi ogni giorno di osservazione ne ha uno — e quindi non certifica nulla sui prezzi che vi stanno dietro. Su una griglia di strumenti una misura più bassa indica date che il calendario condiviso ha effettivamente perso — un inizio tardivo, o una conversione che non è stato possibile risolvere — mai un mercato chiuso: una data in cui nulla è stato quotato, o in cui gli unici prezzi memorizzati erano carry, non è candidata, e in una data in cui solo alcune posizioni erano quotate le altre sono mantenute e comunque valutate, quindi la chiusura si vede invece nella misura di freschezza.

    La domanda *questi prezzi erano quotati o mantenuti?* ha una risposta nel sistema, ma è la misura di freschezza sopra, non quella che un risultato porta con il nome *copertura*. Quale misura raggiunga una determinata schermata è fuori da ciò che questa pagina descrive.

    Un discriminante lo risolve senza alcuna conoscenza degli interni. **Quando un risultato riporta `n_observations = 0` e `calendar_days = 0` accanto a una copertura non nulla, quella copertura non è un'affermazione sulla densità dei dati.** Non può esserlo: nulla è stato osservato. Sta riportando quanta parte del portafoglio è stata classificata.

    La distinzione cambia cosa si dovrebbe fare con il numero. Una copertura dell'80%, letta con i primi due significati in mente, dice *un quinto dei prezzi manca*. Su un rapporto di classificazione dice che un quinto delle etichette di settore o geografia manca. Uno è una lacuna nei dati di mercato, l'altro una lacuna nei metadati degli asset, e i due richiedono azioni completamente diverse. Vedi [Annualizzazione osservata](observed-annualization.md) per come l'intervallo e il conteggio delle osservazioni producono anche il fattore di annualizzazione.

---

## 🚫 Esclusioni {: #exclusions }

Un asset può uscire dall'analisi in due momenti diversi, e la distinzione viene registrata.

**Prima che qualsiasi metrica venga tentata**, quando i suoi dati di origine non possono supportarne una: nessun prezzo utilizzabile, nessuna conversione di valuta utilizzabile, una valuta non valida. Questi sono riportati come asset inutilizzabili, ciascuno con la propria motivazione.

**Quando l'ambito viene risolto**, se l'asset non ha alcuna serie di rendimenti preparata utilizzabile. L'ambito richiesto viene quindi ridotto agli asset che sopravvivono, ogni esclusione conserva la propria motivazione, e un avviso per ogni motivazione nomina esattamente quali asset sono stati eliminati.

In nessuno dei due casi l'analisi rifiuta di essere eseguita: viene eseguita su ciò che rimane e lo dichiara. Un asset escluso è un cambiamento in *ciò che è stato misurato*, ed è per questo che fa uscire dallo stato pulito ogni risultato la cui misurazione è cambiata — e solo quelli.

### 🎯 Quali risultati portano un'esclusione {: #which-results-carry-an-exclusion }

Un'esclusione è un buco nelle serie per asset dell'ambito: le serie di rendimenti di ogni posizione, allineate sul [calendario condiviso](#alignment-what-missing-data-actually-costs). Ogni risultato costruito da quelle serie la eredita — l'asset è elencato come escluso, l'avviso che lo nomina viaggia con il risultato, e il risultato è `partial`. Ciò copre correlazione, contributo al rischio, rischio/rendimento e la simulazione; i KPI, il Value at Risk e il confronto riprodotti sulla composizione corrente, cioè i pesi di oggi eseguiti su quelle serie; le analisi di un insieme di asset scelti direttamente; e le analisi di una *slice* di un portafoglio, una selezione delle sue posizioni. Una slice non può essere ritagliata dallo storico proprio del portafoglio, quindi anche in modalità storica viene riprodotta dalle serie delle posizioni selezionate.

L'eccezione è la modalità storica di un portafoglio nel suo complesso — tutti i suoi broker o una loro selezione, ma non una slice delle sue posizioni. Lì, quattro analitiche leggono lo storico di rendimenti proprio del portafoglio, il suo [rendimento time-weighted](../performance-metrics/portfolio-engine/twrr.md) (TWRR), nei suoi [giorni di osservazione](#coverage), invece delle serie per asset: i KPI (volatilità, Sharpe, Sortino, …), il [Value at Risk](value-at-risk.md) storico e il [VaR condizionale](conditional-value-at-risk.md), il drawdown e il confronto con un benchmark, che aggiunge solo la serie propria del benchmark. Quello storico valuta già ogni posizione — una senza quotazioni di mercato al prezzo della sua ultima transazione — quindi un asset mancante dalle serie per asset non costa nulla in valore a queste quattro: al massimo, i giorni in cui solo quell'asset era quotato smettono di essere giorni di osservazione, e i loro rendimenti vengono concatenati nel successivo. Non ereditano né l'esclusione né l'avviso che la nomina, né l'avviso che la parte della composizione odierna conteggiata a rendimento zero include valore in transito, un'affermazione su una composizione che non usano mai. La stessa richiesta riporta comunque l'esclusione su ogni risultato che legge le serie per asset. Ciò che può ancora rendere queste quattro `partial` sono i dati dietro lo storico del portafoglio stesso, e per il confronto la preparazione del suo benchmark — vedi [Interpretazione](#interpretation).

I test di stress applicano regole proprie. Un [replay storico](historical-replay.md) prepara le proprie serie sulla finestra del suo episodio e lascia fuori — per ragioni proprie, nominate nei suoi avvisi — gli asset che non può prezzare a entrambe le estremità di quella finestra. Uno [shock ipotetico](hypothetical-shock.md) non legge alcuna serie di rendimenti: applica i suoi shock a ogni posizione tramite la classificazione della posizione, quindi un'esclusione dalle serie per asset non gli costa nulla, e non eredita né l'esclusione né il suo avviso.

### 🏷️ Motivi di esclusione {: #exclusion-reasons }

Ogni asset escluso porta una motivazione, e ogni motivazione ha una frase propria nell'avviso:

| Motivo | Perché l'asset è stato lasciato fuori |
|---|---|
| `no_price_source` | Non gli è assegnata alcuna fonte di prezzo e non è mai stato registrato alcun prezzo per esso. Nulla è configurato per prezzarlo, quindi è uno stato permanente più che una lacuna nei dati — tipicamente un investimento privato, come un prestito di crowdfunding, che nessun mercato quota. |
| `missing_price` | Ha una fonte di prezzo, o prezzi registrati, ma nessun prezzo utilizzabile per il periodo: la fonte non ha restituito nulla per esso, o ogni prezzo registrato cade dopo il periodo. |
| `missing_fx` | Non è stato possibile convertire i suoi prezzi nella valuta obiettivo. |
| `invalid_currency` | I suoi prezzi non portano una valuta valida. |
| `insufficient_history` | Non c'è abbastanza storico nel periodo per dargli una serie di rendimenti utilizzabile. |

I prezzi registrati solo *prima* del periodo non causano mai un'esclusione: l'ultimo di essi viene mantenuto nel periodo, come descritto in [Allineamento](#alignment-what-missing-data-actually-costs). Solo il risultato distingue le prime due motivazioni: nel suo report dei dati di origine, un asset che nulla prezza è comunque elencato tra gli asset inutilizzabili come `missing_price`.

### ⚖️ Il peso escluso {: #excluded-weight }

Le analisi della composizione corrente che dichiarano pesi — contributo al rischio e rischio/rendimento — mantengono una posizione esclusa al suo peso e la contano a rendimento zero: le misure che calcolano sono esattamente quelle che darebbe lo stesso denaro tenuto in liquidità. Il risultato nomina quella parte separatamente. `excluded_weight` è la somma dei pesi delle posizioni dell'ambito rimaste senza serie, ed è indicata accanto a `cash_weight`, il residuo a rendimento zero: la quota del valore dell'ambito detenuta al di fuori delle posizioni che hanno una serie — liquidità, qualsiasi valore in transito e le posizioni escluse. In ogni risultato che queste due analisi producono, il peso escluso fa parte di quel residuo. I due potrebbero non annidarsi correttamente solo se le posizioni valessero più del patrimonio netto — un saldo di cassa negativo non compensato da valore in transito — e in quel caso nessuna delle due analisi produce un risultato: torna `unavailable`. Le selezioni senza pesi, come un insieme di asset scelti direttamente, non portano né l'uno né l'altro.

---

## 💡 Interpretazione {: #interpretation }

Ogni risultato analitico porta uno stato proprio, distinto da quello dei dati di origine:

| Stato del risultato | Significato |
|---|---|
| `ok` | Calcolato senza nulla mancante o obsoleto nei suoi dati di origine, nulla escluso da ciò che legge e nessun avviso degradante |
| `partial` | Calcolato, ma con dati di origine mancanti o obsoleti, qualcosa escluso da ciò che legge, o un avviso degradante |
| `unavailable` | Non calcolato; un codice di motivazione stabile spiega perché (storico insufficiente, dati non disponibili, parametri non validi, un calcolo troppo grande da eseguire, ambito o modalità incompatibili, …) |
| `failed` | Il calcolo si è interrotto su un errore che l'analitica non dichiara — un difetto del calcolo, mai un giudizio sui dati. Porta il codice `execution_failed` (*Il calcolo backend non è riuscito.*), il server lo registra, e la schermata legge **Calcolo non riuscito** |

Un fallimento non è un valore indefinito. Una metrica che genuinamente non ha valore per dati ben formati — la correlazione di una serie che non si è mai mossa, un indice di Sharpe su volatilità zero — non fallisce: quel valore torna vuoto, contrassegnato `undefined` in una cella di correlazione o spiegato da un avviso come `sharpe_undefined`, e il resto del risultato rimane utilizzabile. Al contrario, un errore che l'analitica non prevedeva non viene mai riportato come metrica indefinita: ciò trasformerebbe un difetto del calcolo in un'affermazione sui tuoi dati.

Un risultato è `partial` quando **una qualsiasi** di queste condizioni vale: è presente un avviso che degrada il risultato; un asset dell'ambito che il risultato legge è stato [escluso](#which-results-carry-an-exclusion); l'analitica stessa ha escluso qualcosa; oppure lo stato del report dei dati di origine su cui il risultato è giudicato è diverso da `ok`. Nell'ultimo caso viene allegato anche un avviso esplicito, così la degradazione non viene mai inferita dal solo stato.

Quel report è quello delle serie che il risultato ha consumato:

- un risultato costruito dalle serie per asset dell'ambito — inclusi i KPI, le misure di Value at Risk, il drawdown e il confronto quando vengono riprodotti da quelle serie, sulla composizione corrente o su una slice — è giudicato sul report della loro preparazione, unito, quando l'ambito è un portafoglio, al report proprio del portafoglio;
- sul TWRR di un portafoglio, i KPI, le misure di Value at Risk e il drawdown sono giudicati sul report dei dati di origine proprio del portafoglio: se lo storico del portafoglio stesso è incompleto — una posizione che non è stato possibile valutare, un tasso di cambio mancante, un giorno in cui non è stato possibile valutare per intero il patrimonio netto — sono comunque `partial`, con l'avviso. Quel report traccia ciò che non è stato possibile valutare, non quanto è vecchia una valutazione, quindi un prezzo mantenuto oltre la soglia di obsolescenza all'interno dello storico del portafoglio non li degrada;
- il confronto con un benchmark sul TWRR è giudicato sul report del portafoglio più la preparazione del suo benchmark, che è allineata sul calendario condiviso dell'ambito: un prezzo o un tasso di cambio su quel calendario mantenuto oltre la [soglia di obsolescenza](#staleness-threshold) — del benchmark o di una posizione — o una data persa da esso, lo rende comunque `partial`; le posizioni escluse dall'ambito non sono mai entrate in quel calendario, quindi la loro esclusione non lo fa.

!!! info "Come leggere un risultato partial"

    `partial` non significa *sbagliato*. Significa che la misura porta un'imperfezione nota: può basarsi su prezzi o tassi di cambio mantenuti oltre la soglia di obsolescenza — stessa finestra, stesse posizioni — oppure rispondere a una domanda leggermente diversa da quella posta, su un calendario con date incomplete o su meno posizioni. La misura e la motivazione viaggiano insieme nello stesso payload, e sono pensate per essere lette insieme: un contributo al rischio calcolato con due posizioni escluse descrive un portafoglio in cui quelle due sono rimaste ferme, come liquidità — non il portafoglio così com'è.

Le analitiche rifiutano anche di rispondere piuttosto che rispondere male. Ognuna dichiara il numero minimo di osservazioni di cui ha bisogno, e sotto quella soglia non viene calcolata affatto: il risultato torna `unavailable` con una motivazione `insufficient_history` che porta sia le osservazioni disponibili sia il numero richiesto. Il contributo al rischio e il confronto con un benchmark, per esempio, richiedono entrambi almeno 20. Le misure di Value at Risk contano le loro finestre composte per orizzonte anziché i loro rendimenti, quindi un orizzonte più lungo richiede una finestra più lunga — vedi [Value at Risk](value-at-risk.md#the-observation-count-is-not-the-history-length). La [Correlazione](correlation.md#how-each-cell-is-computed) è un'eccezione: non viene mai rifiutata per storico breve. La sua soglia — un parametro regolabile dell'analisi, 20 osservazioni per impostazione predefinita — si applica alla matrice nel suo complesso: ogni serie condivide un calendario, quindi ogni coppia ha lo stesso numero di osservazioni, e sotto la soglia ogni cella torna `insufficient` senza coefficiente, in un risultato contrassegnato `partial` anziché `unavailable`.

---

## ⚠️ Limitazioni {: #limitations }

!!! warning "Uno stato descrive gli input, non il modello"

    `ok` dice che la serie era completa, non che la metrica sia appropriata, che la finestra sia abbastanza lunga o che il passato assomigli al futuro. Ogni avvertenza nelle pagine delle metriche vale ancora per una misura costruita su dati impeccabili.

!!! warning "I dati mantenuti adulano una misura di rischio"

    Un prezzo mantenuto da una data precedente produce un rendimento di periodo esattamente pari a zero nella valuta dello strumento; dopo la conversione nella valuta obiettivo, solo il tasso di cambio lo muove. Ogni prezzo mantenuto fa questo, per quanto recente, e quei rendimenti entrano nel campione come qualsiasi altra osservazione. Entro la [soglia di obsolescenza](#staleness-threshold) è normale: in un weekend, in un giorno festivo o in un giorno in cui ha scambiato solo un altro mercato, lo strumento non ha avuto una nuova quotazione, e la sua quotazione successiva recupera. Un prezzo mantenuto più a lungo sostituisce giorni in cui lo strumento potrebbe benissimo essersi mosso, quindi una serie ricca di tali punti riporta **meno** movimento di quanto lo strumento abbia effettivamente avuto. Quelli sono i punti che lo stato `carried_forward` conta, e lo stato è l'avviso che una misura dall'aspetto calmo può essere calma per la ragione sbagliata.

!!! warning "Una posizione valutata dalle sue transazioni resta ferma"

    Sul TWRR di un portafoglio, una posizione che nessun mercato prezza è valutata al [prezzo della sua ultima transazione](../performance-metrics/portfolio-engine/price-resolution.md), quindi nella sua valuta resta ferma da una transazione alla successiva. Per un prestito detenuto al suo valore nominale — un tipico investimento di crowdfunding — questa è la verità. Per una posizione il cui valore si muove davvero, appiattisce ogni misura letta sul TWRR, proprio come fa un prezzo mantenuto. Nessuno stato lo segnala: il report del portafoglio non conta una valutazione da transazioni contro il suo stato, e per una posizione senza fonte di prezzo tratta quella valutazione come lo stato intenzionale e permanente.

!!! warning "Nessuna soglia di qualità scarta una misura"

    A parte i conteggi minimi di osservazioni descritti sopra, al di sotto dei quali un'analitica non viene calcolata affatto o ogni cella di correlazione torna `insufficient`, nulla nel sistema dichiara una copertura o una quota mantenuta oltre la quale una misura debba essere scartata. Quell'assenza è deliberata — il numero onesto è quello che arriva con la propria provenienza — ma significa che il giudizio finale è tuo, e non può essere delegato all'etichetta di stato.

---

## 🔗 Correlati {: #related }

- 📅 **[Annualizzazione osservata](observed-annualization.md)** — il fattore di annualizzazione conteggiato dalle stesse osservazioni, e perché una serie sparsa non è necessariamente una serie rotta
- 🔗 **[Correlazione](correlation.md)** — riporta il conteggio delle osservazioni dietro ogni singola cella
- 📊 **[Volatilità](volatility.md)** — la misura più direttamente appiattita dai prezzi mantenuti
