# 🧪 Qualità dei dati

Una misura di rischio è affidabile solo quanto le osservazioni che la sostengono, perciò la quantità e la freschezza dei dati sottostanti fanno parte della lettura del risultato. LibreFolio non tiene nascosto questo livello: ogni risultato di rischio viaggia con un report sui dati di origine, uno stato da esso derivato e — quando mancava qualcosa — l'elenco di ciò che mancava.

---

## 🚦 Stato dei dati di origine {: #source-data-status }

I dati di origine sono classificati su tre livelli:

| Stato | Cosa significa |
|---|---|
| `ok` | Nulla mancante e nulla mantenuto per un periodo superiore alla [soglia di obsolescenza](#staleness-threshold). La serie è ciò che dichiara di essere. |
| `carried_forward` | Nulla manca del tutto, ma alcuni prezzi o tassi di cambio sono stati mantenuti da una data precedente per un periodo superiore alla soglia di obsolescenza — quotazioni obsolete, punti di prezzo mantenuti, punti FX mantenuti. |
| `partial` | Qualcosa manca del tutto: prezzi, coppie FX, date all'interno della finestra analizzata in cui non tutte le posizioni potevano essere valorizzate, coppie di valute non risolte o asset che non potevano partecipare affatto. |

Due proprietà di questa scala contano più delle etichette.

**È derivato, non dichiarato.** Lo stato è una proprietà calcolata dal contenuto stesso del report: un produttore non può dichiarare `ok` mentre segnala prezzi mancanti, perché lo stato viene ricalcolato da ciò che il report contiene. Qualsiasi cosa manchi del tutto produce `partial`; se nulla manca ma qualcosa è stato mantenuto oltre la soglia di obsolescenza, `carried_forward`; altrimenti `ok`. `partial` ha la precedenza su `carried_forward`.

**È categorico, non numerico.** Lo stato risponde a *che tipo di imperfezione è presente*, mai a *quanta sia tollerabile*. Non esiste un livello di completezza al di sotto del quale il sistema dichiari un valore inaffidabile: quel giudizio è lasciato a chi legge, deliberatamente ed esplicitamente.

### ⏳ La soglia di obsolescenza {: #staleness-threshold }

Un prezzo o un tasso di cambio mantenuto da una data precedente è di per sé ordinario: weekend, festivi e strumenti quotati sui propri calendari di mercato lasciano continuamente dei vuoti — e un prezzo memorizzato in un fine settimana o in un giorno festivo di mercato che ripete soltanto la chiusura precedente è anch'esso mantenuto, non quotato (vedi [Carry memorizzati](#stored-carries)). Un valore mantenuto diventa **obsoleto** solo quando è più vecchio di **sette giorni di calendario** rispetto alla data che sostituisce, e solo uno obsoleto pesa sulla serie per asset di un'analisi: viene registrato come punto di prezzo o FX mantenuto, e uno solo basta per `carried_forward`. Uno più giovane non degrada nulla, ma non è invisibile: un prezzo mantenuto produce comunque un rendimento di periodo pari a zero, e quel rendimento entra nel campione (vedi [Limitazioni](#limitations)). La soglia decide cosa conta come imperfezione, non quante imperfezioni siano tollerabili.

Sette giorni di calendario è l'unica soglia di obsolescenza del progetto, non una convenzione di questa pagina: il [laboratorio di correlazione](../../../user/assets/correlation.md) della pagina Asset e il replay storico giudicano l'età di un prezzo con gli stessi sette giorni, e gli avvisi che segnalano prezzi o tassi di cambio obsoleti la citano.

### 🔁 Carry memorizzati {: #stored-carries }

Non ogni prezzo mantenuto arriva come un vuoto. Alcune fonti forniscono una riga per ogni giorno di calendario, ripetendo l'ultima chiusura nei giorni in cui il loro mercato è chiuso: justETF, per esempio, ripete la chiusura del venerdì di sabato e domenica. Lette come quotazioni, quelle righe inserirebbero in ogni serie costruita da esse un rendimento pari a zero, nella valuta propria dell'asset, che nessun mercato ha prodotto. Quindi un prezzo memorizzato è un **carry**, non una quotazione, quando valgono entrambe queste condizioni:

- ha data di sabato o di domenica, oppure cade in un giorno feriale che è festivo in almeno uno dei principali mercati — l'unione dei calendari che QuantLib fornisce per TARGET, Borsa Italiana, Xetra, Euronext Paris, la London Stock Exchange, la Svizzera e il NYSE;
- la sua chiusura, nella valuta propria dell'asset, è **esattamente** la chiusura della riga precedente, senza tolleranza.

Tre tipi di riga restano quotazioni: il primo prezzo di una serie, che non ha una riga precedente; un prezzo invariato in un giorno feriale ordinario, perché un giorno piatto di un'obbligazione o di un fondo monetario è reale; e un prezzo che si è mosso in un weekend o in un festivo, come fa quello di un asset cripto. L'unione dei mercati è sicura perché la regola richiede anche la ripetizione esatta: uno strumento che ha scambiato mentre un altro mercato era chiuso si è quasi sempre mosso, e un prezzo che si è mosso resta una quotazione — nel peggiore dei casi, un giorno davvero piatto in una tale data viene letto come un carry. La tabella dei festivi è costruita all'avvio del server; se non è stato possibile costruirla, valgono solo i weekend finché un tentativo successivo non riesce.

Un carry è l'ultima quotazione autentica mantenuta, ed è datata da quella quotazione, perciò in un fine settimana ordinario è vecchio di uno o due giorni — ben dentro la soglia di obsolescenza. La sua data non è una data di quotazione dell'asset. Non aggiunge alcun candidato al [calendario condiviso](#alignment-what-missing-data-actually-costs), nessun giorno di osservazione alla serie di rendimenti di un portafoglio (vedi [Copertura](#coverage)), e nulla alle quotazioni che decidono se un asset può partecipare a un'analisi di un insieme di asset — almeno 20 nel periodo, il minimo che le analisi statistiche accettano — o a un [replay storico](historical-replay.md), che richiede che l'asset sia valorizzato a entrambi gli estremi della sua finestra. Quando la quotazione di un altro asset colloca comunque la data su un calendario condiviso, l'asset è valorizzato lì alla sua ultima quotazione autentica, e quel punto conta come mantenuto nella misura di freschezza descritta in [Copertura](#coverage).

---

## 📋 Cosa registra il report {: #what-the-report-records }

Il report è un inventario, non un punteggio:

| Segnale | Cosa cattura |
|---|---|
| Asset con prezzo mancante | Posizioni per cui non è stato possibile ottenere un prezzo utilizzabile |
| Coppie FX mancanti / non risolte | Conversioni di valuta che non è stato possibile risolvere |
| Prezzi obsoleti | Posizioni il cui prezzo più recente è più vecchio della [soglia di obsolescenza](#staleness-threshold) |
| Punti di prezzo mantenuti | Quanti punti di prezzo sono stati mantenuti oltre la soglia di obsolescenza, e per quali asset |
| Punti FX mantenuti | Quanti punti di conversione sono stati mantenuti oltre la soglia di obsolescenza, e per quali coppie |
| Date incomplete | Date in cui la valorizzazione, il NAV, il valore contabile o l'allocazione non hanno potuto essere completati per ogni posizione |
| Asset inutilizzabili | Asset esclusi prima che qualsiasi metrica fosse tentata, ciascuno con una motivazione |
| Avvisi | Note libere allegate dalla fase di produzione |

Ogni voce nomina l'oggetto a cui si riferisce — l'asset, la coppia di valute, la data. Chi legge può chiedere *quale* asset, coppia di valute o data ha degradato il valore, non solo *se* qualcosa lo ha fatto.

---

## 🧮 Allineamento: quanto costa davvero un dato mancante {: #alignment-what-missing-data-actually-costs }

Quando un'analisi abbraccia più posizioni — una matrice di correlazione, una scomposizione del contributo al rischio — viene calcolata su un **unico calendario condiviso**, ed è nella costruzione di quel calendario che i dati mancanti si traducono in un costo visibile.

1. Una data è candidata se almeno una posizione aveva una quotazione fresca in quella data, senza che un [carry memorizzato](#stored-carries) conti come tale: i candidati sono l'unione dei calendari di quotazione delle posizioni nella finestra richiesta.
2. Una data candidata entra nell'analisi solo se **ogni** posizione poteva essere valorizzata in essa. Qui *valorizzata* include un prezzo o un tasso di cambio mantenuto da una data precedente, senza limite di età, quindi in pratica il test fallisce solo prima del primo prezzo utilizzabile di una posizione, o dove non è stato possibile risolvere la sua conversione nella valuta di destinazione. Le date che non superano questo test vengono scartate per tutte le posizioni, ma sono registrate come date di valorizzazione incomplete solo una volta iniziato il calendario — cioè dopo la baseline.
3. La baseline è l'ultima data precedente l'inizio richiesto in cui tutte le posizioni erano valorizzabili; se non ce n'è nessuna, l'analisi parte invece all'interno della finestra richiesta, nella prima data in cui ogni posizione può essere valorizzata, e le posizioni responsabili dell'inizio tardivo vengono nominate.

La conseguenza merita di essere detta chiaramente: **una posizione che inizia tardi accorcia la finestra per tutti**. Un vuoto all'interno di una storia non accorcia nulla, perché il prezzo o il tasso di cambio mancante viene mantenuto. Nulla viene interpolato: un prezzo o un tasso mantenuto è l'ultimo conosciuto. Una volta mantenuto oltre la [soglia di obsolescenza](#staleness-threshold), è conteggiato come punto mantenuto — questione che riguarda lo stato `carried_forward`, non la lunghezza della finestra. Uno più giovane non degrada lo stato, sebbene un prezzo mantenuto, qualunque sia la sua età, pesi comunque sulla misura di freschezza descritta in [Copertura](#coverage). Una posizione non è mai inclusa parzialmente in un calcolo congiunto: o la data vale per tutte oppure non è un'osservazione. Un inizio tardivo da solo non rende il risultato `partial`: le date che fa perdere non sono elencate come incomplete, il report nomina le posizioni responsabili nelle sue voci `short_history`, e la perdita si vede nel conteggio delle osservazioni e nella copertura del calendario condiviso descritta più sotto. Una data persa dopo l'inizio del calendario è diversa: viene elencata come incompleta e rende il risultato `partial`.

---

## 📏 Copertura {: #coverage }

La copertura è normalmente il compagno di densità dello stato: risponde a *quanto di ciò che avrebbe potuto essere osservato è stato effettivamente osservato*. Rapporti diversi portano questo nome. Non condividono alcun denominatore e non misurano tutti lo stesso tipo di cosa: due di essi contano osservazioni, un terzo conta posizioni e non contiene alcuna osservazione.

**Quanto è costato il calendario condiviso?** Tra le date in cui almeno una posizione aveva una quotazione fresca, è la quota che ha superato il requisito che ogni posizione fosse valorizzabile. Un valore ben inferiore a 1 indica che in molte delle date in cui qualche posizione era quotata, un'altra non poteva essere valorizzata — e poiché i vuoti vengono mantenuti, questo di solito rimanda a una posizione la cui storia inizia ben dopo l'inizio richiesto, o a conversioni che non è stato possibile risolvere, piuttosto che a vuoti.

**Quanta parte dei dati è genuinamente fresca?** Sulla griglia posizioni × osservazioni, è la quota di punti il cui prezzo è stato quotato in quella data anziché mantenuto da una data precedente. Misura lo stesso tipo di imperfezione dello stato `carried_forward`, ma solo sulle osservazioni e con una soglia più severa: ogni prezzo mantenuto pesa su di essa, per quanto giovane, mentre lo stato conta solo quelli mantenuti oltre la soglia di obsolescenza. Inoltre conta solo i prezzi: una quotazione fresca che però è stata convertita con un tasso di cambio mantenuto conta comunque come fresca, perché le conversioni mantenute sono tracciate come segnale separato. Quindi una quota inferiore al 100% non significa di per sé `carried_forward`, e una quota del 100% non lo esclude di per sé — né, quindi, esclude un risultato `partial`.

**Quanta parte del portafoglio ha potuto essere classificata?** Tra le posizioni nel perimetro, è la quota per cui erano disponibili i metadati di settore o area geografica, anziché mancanti e tali da far finire la posizione nel bucket generico `Other` al 100%. Questa è un'affermazione sui metadati: nessun prezzo, nessuna data e nessuna osservazione vi entra. Un [shock ipotetico](hypothetical-shock.md) riporta questo rapporto.

!!! warning "Un unico nome, due tipi di grandezza"

    Quando il valore è una misura di densità, il suo denominatore dipende dal percorso. Per un'analisi costruita dalle quotazioni degli strumenti, sono le date di quotazione candidate. Per una serie di portafoglio, sono i **giorni di osservazione** del portafoglio: l'analisi legge la serie di rendimenti propria del portafoglio, il suo [rendimento ponderato per il tempo](../performance-metrics/portfolio-engine/twrr.md), solo nei giorni in cui almeno una posizione del perimetro aveva una quotazione propria, e concatena il rendimento di ogni altro giorno in quello successivo; il denominatore conta quei giorni lungo l'intero arco — o ogni giorno di calendario dell'arco, se nessuna posizione aveva una quotazione propria nella finestra. Su una serie di portafoglio quel valore è alto per costruzione — la storia del portafoglio ha un punto per ogni giorno di calendario, mantenendo l'ultimo valore noto dove nulla era quotato, così ogni giorno di osservazione ne ha uno — e quindi non certifica nulla sui prezzi che stanno dietro. Su una griglia di strumenti un valore più basso indica date che il calendario condiviso ha effettivamente perso — un inizio tardivo, o una conversione che non è stato possibile risolvere — mai un mercato chiuso: una data in cui nulla è stato quotato, o in cui gli unici prezzi memorizzati erano carry, non è candidata, e in una data in cui solo alcune posizioni erano quotate le altre vengono mantenute e comunque valorizzate, quindi la chiusura si vede nella misura di freschezza.

    La domanda *questi prezzi sono stati quotati o mantenuti?* ha una risposta nel sistema, ma è la misura di freschezza qui sopra, non quella che un risultato porta sotto il nome di *copertura*. Quale misura raggiunga una data schermata è fuori da ciò che questa pagina descrive.

    Un solo discriminante lo risolve senza alcuna conoscenza degli interni. **Quando un risultato riporta `n_observations = 0` e `calendar_days = 0` accanto a una copertura diversa da zero, quella copertura non è un'affermazione sulla densità dei dati.** Non può esserlo: nulla è stato osservato. Sta riportando quanta parte del portafoglio è stata classificata.

    La distinzione cambia ciò che si dovrebbe fare con il numero. Una copertura dell'80%, letta con i primi due significati in mente, dice *un quinto dei prezzi manca*. Su un rapporto di classificazione dice che un quinto delle etichette di settore o area geografica manca. Uno è un vuoto nei dati di mercato, l'altro un vuoto nei metadati degli asset, e i due richiedono azioni completamente diverse. Vedi [Annualizzazione osservata](observed-annualization.md) per come l'arco e il conteggio delle osservazioni producano anche il fattore di annualizzazione.

---

## 🚫 Esclusioni {: #exclusions }

Un asset può uscire dall'analisi in due momenti diversi, e la distinzione viene registrata.

**Prima che qualsiasi metrica sia tentata**, quando i suoi dati di origine non possono sostenerne una: nessun prezzo utilizzabile, nessuna conversione di valuta utilizzabile, una valuta non valida. Questi sono riportati come asset inutilizzabili, ciascuno con la propria motivazione.

**Quando il perimetro viene risolto**, se l'asset non ha alcuna serie di rendimenti preparata utilizzabile. Il perimetro richiesto viene allora ridotto agli asset che sopravvivono, ogni esclusione mantiene la propria motivazione, e un avviso per ogni motivazione nomina esattamente quali asset sono stati esclusi.

In nessuno dei due casi l'analisi rifiuta di essere eseguita: viene eseguita su ciò che resta e lo dichiara. Un asset escluso è un cambiamento in *ciò che è stato misurato*, ed è per questo che fa uscire dallo stato pulito ogni risultato la cui misurazione è cambiata — e solo quelli.

### 🎯 Quali risultati portano un'esclusione {: #which-results-carry-an-exclusion }

Un'esclusione è un buco nella serie per asset del perimetro: la serie di rendimenti di ogni posizione, allineata sul [calendario condiviso](#alignment-what-missing-data-actually-costs). Ogni risultato costruito da quelle serie la eredita — l'asset è elencato come escluso, l'avviso che lo nomina viaggia con il risultato, e il risultato è `partial`. Questo copre correlazione, contributo al rischio, rischio/rendimento e la simulazione; i KPI, il Value at Risk e il confronto riprodotti sulla composizione attuale, cioè i pesi di oggi eseguiti su quelle serie; le analisi di un insieme di asset scelti direttamente; e le analisi di una *porzione* di un portafoglio, una selezione delle sue posizioni. Una porzione non può essere ritagliata dalla storia propria del portafoglio, quindi anche in modalità storica viene riprodotta dalle serie delle posizioni selezionate.

L'eccezione è la modalità storica di un portafoglio nel suo complesso — tutti i suoi broker o una selezione di essi, ma non una porzione delle sue posizioni. Lì quattro analisi leggono la storia dei rendimenti propria del portafoglio, il suo [rendimento ponderato per il tempo](../performance-metrics/portfolio-engine/twrr.md) (TWRR), nei suoi [giorni di osservazione](#coverage), anziché le serie per asset: i KPI (volatilità, indice di Sharpe, indice di Sortino, …), il [Value at Risk](value-at-risk.md) storico e il [VaR condizionale](conditional-value-at-risk.md), il drawdown e il confronto con un benchmark, che aggiunge solo la serie propria del benchmark. Quella storia valorizza già ogni posizione — una senza quotazioni di mercato al prezzo del suo ultimo acquisto o vendita, o al suo costo quando non ha né l'uno né l'altro — quindi un asset assente dalla serie per asset non costa nulla, in valore, a queste quattro: al massimo, i giorni in cui era quotato solo quell'asset smettono di essere giorni di osservazione, e i loro rendimenti vengono concatenati in quello successivo. Non ereditano né l'esclusione né l'avviso che la nomina, né l'avviso secondo cui la parte della composizione odierna conteggiata a rendimento zero include valore in transito, affermazione su una composizione che non usano mai. La stessa richiesta riporta comunque l'esclusione su ogni risultato che legge la serie per asset. Ciò che può ancora rendere queste quattro `partial` sono i dati dietro la storia del portafoglio stesso e, per il confronto, la preparazione del suo benchmark — vedi [Interpretazione](#interpretation).

Gli stress test applicano regole proprie. Un [replay storico](historical-replay.md) prepara le proprie serie sulla finestra del suo episodio e tralascia — per ragioni proprie, nominate nei propri avvisi — gli asset che non riesce a prezzare a entrambi gli estremi di quella finestra. Un [shock ipotetico](hypothetical-shock.md) non legge alcuna serie di rendimenti: applica i suoi shock a ogni posizione tramite la classificazione della posizione, quindi un'esclusione dalla serie per asset non gli costa nulla, e non eredita né l'esclusione né il suo avviso.

### 🏷️ Motivi di esclusione {: #exclusion-reasons }

Ogni asset escluso porta un motivo, e ogni motivo ha una propria frase nell'avviso:

| Motivo | Perché l'asset è stato lasciato fuori |
|---|---|
| `no_price_source` | Non gli è assegnata alcuna fonte di prezzo e nessun prezzo è mai stato registrato per esso. Nulla è configurato per prezzarlo, quindi si tratta di uno stato permanente più che di un vuoto nei dati — tipicamente un investimento privato, come un prestito di crowdfunding, che nessun mercato quota. |
| `missing_price` | Ha una fonte di prezzo, o prezzi registrati, ma nessun prezzo utilizzabile per il periodo: la fonte non ha restituito nulla per esso, oppure ogni prezzo registrato cade dopo il periodo. |
| `missing_fx` | I suoi prezzi non hanno potuto essere convertiti nella valuta di destinazione. |
| `invalid_currency` | I suoi prezzi non portano una valuta valida. |
| `insufficient_history` | Non c'è storia sufficiente nel periodo per dargli una serie di rendimenti utilizzabile. |

I prezzi registrati solo *prima* del periodo non causano mai un'esclusione: l'ultimo di essi viene mantenuto nel periodo, come descritto in [Allineamento](#alignment-what-missing-data-actually-costs). Solo il risultato distingue i primi due motivi: nel suo report sui dati di origine, un asset che nulla prezza è comunque elencato tra gli asset inutilizzabili come `missing_price`.

### ⚖️ Il peso escluso {: #excluded-weight }

Le analisi della composizione attuale che dichiarano pesi — contributo al rischio e rischio/rendimento — mantengono una posizione esclusa al suo peso e la contano a rendimento zero: le cifre che calcolano sono esattamente quelle che darebbe lo stesso denaro tenuto in liquidità. Il risultato nomina separatamente quella parte. `excluded_weight` è la somma dei pesi delle posizioni del perimetro rimaste senza serie, ed è dichiarato accanto a `cash_weight`, il residuo a rendimento zero: la quota del valore del perimetro detenuta al di fuori delle posizioni che hanno una serie — liquidità, qualsiasi valore in transito e le posizioni escluse. In ogni risultato che queste due analisi producono, il peso escluso fa parte di quel residuo. I due potrebbero non annidarsi solo se le posizioni valessero più del patrimonio netto — un saldo di cassa negativo non compensato da valore in transito — e in quel caso nessuna delle due analisi produce un risultato: torna `unavailable`. Le selezioni senza pesi, come un insieme di asset scelti direttamente, non portano né l'uno né l'altro.

---

## 💡 Interpretazione {: #interpretation }

Ogni risultato analitico porta uno stato proprio, distinto da quello dei dati di origine:

| Stato del risultato | Significato |
|---|---|
| `ok` | Calcolato senza nulla di mancante o obsoleto nei suoi dati di origine, senza nulla di escluso da ciò che legge e senza avvisi degradanti |
| `partial` | Calcolato, ma con dati di origine mancanti o obsoleti, qualcosa escluso da ciò che legge, o un avviso degradante |
| `unavailable` | Non calcolato; un codice di motivazione stabile spiega perché (storia insufficiente, dati non disponibili, parametri non validi, un calcolo troppo grande da eseguire, perimetro o modalità incompatibili, …) |
| `failed` | Il calcolo si è interrotto su un errore che l'analisi non dichiara — un difetto del calcolo, mai un giudizio sui dati. Porta il codice `execution_failed` (*Il calcolo backend non è riuscito.*), il server lo registra nei log, e la schermata mostra **Calcolo fallito** |

Un fallimento non è un valore indefinito. Una metrica che genuinamente non ha valore per dati ben formati — la correlazione di una serie che non si è mai mossa, un indice di Sharpe su volatilità zero — non fallisce: quel valore torna vuoto, contrassegnato `undefined` in una cella di correlazione o spiegato da un avviso come `sharpe_undefined`, e il resto del risultato resta utilizzabile. Viceversa, un errore che l'analisi non ha previsto non viene mai riportato come una metrica indefinita: ciò trasformerebbe un difetto del calcolo in un'affermazione sui tuoi dati.

Un risultato è `partial` quando **una qualsiasi** di queste condizioni vale: è presente un avviso che degrada il risultato; un asset del perimetro che il risultato legge è stato [escluso](#which-results-carry-an-exclusion); l'analisi stessa ha escluso qualcosa; oppure lo stato del report sui dati di origine su cui il risultato è giudicato è qualcosa di diverso da `ok`. Nell'ultimo caso viene anche allegato un avviso esplicito, così il degrado non è mai dedotto dal solo stato.

Quel report è quello delle serie che il risultato ha consumato:

- un risultato costruito dalle serie per asset del perimetro — inclusi i KPI, le cifre del Value at Risk, il drawdown e il confronto quando sono riprodotti da quelle serie, sulla composizione attuale o su una porzione — è giudicato sul report della loro preparazione, unito, quando il perimetro è un portafoglio, al report proprio del portafoglio;
- sul TWRR di un portafoglio, i KPI, le cifre del Value at Risk e il drawdown sono giudicati sul report sui dati di origine proprio del portafoglio: se la storia del portafoglio stessa è incompleta — una posizione che non ha potuto essere valorizzata, un tasso di cambio mancante, un giorno in cui il patrimonio netto non ha potuto essere valorizzato per intero — sono comunque `partial`, con l'avviso. Quel report traccia ciò che non ha potuto essere valorizzato, non quanto sia vecchia una valorizzazione, quindi un prezzo mantenuto oltre la soglia di obsolescenza dentro la storia del portafoglio non li degrada;
- il confronto con un benchmark sul TWRR è giudicato sul report del portafoglio più la preparazione del suo benchmark, allineato sul calendario condiviso del perimetro: un prezzo o un tasso di cambio su quel calendario mantenuto oltre la [soglia di obsolescenza](#staleness-threshold) — del benchmark o di una posizione — o una data persa da esso, lo rende comunque `partial`; le posizioni escluse dal perimetro non sono mai entrate in quel calendario, quindi la loro esclusione non lo fa.

!!! info "Come leggere un risultato partial"

    `partial` non significa *sbagliato*. Significa che il valore porta un'imperfezione nota: può poggiare su prezzi o tassi di cambio mantenuti oltre la soglia di obsolescenza — stessa finestra, stesse posizioni — oppure rispondere a una domanda leggermente diversa da quella posta, su un calendario con date incomplete o su meno posizioni. Il valore e il motivo viaggiano insieme nello stesso payload, e vanno letti insieme: un contributo al rischio calcolato con due posizioni escluse descrive un portafoglio in cui quelle due sono rimaste ferme, come liquidità — non il portafoglio così com'è.

Le analisi preferiscono anche rifiutarsi di rispondere piuttosto che rispondere male. Ognuna dichiara il numero minimo di osservazioni di cui ha bisogno, e sotto quella soglia minima non viene calcolata affatto: il risultato torna `unavailable` con una motivazione `insufficient_history` che riporta sia le osservazioni disponibili sia il numero richiesto. Il contributo al rischio e il confronto con un benchmark, per esempio, ne richiedono entrambi almeno 20. Le cifre del Value at Risk contano le loro finestre composte sull'orizzonte anziché i loro rendimenti, quindi un orizzonte più lungo richiede una finestra più lunga — vedi [Value at Risk](value-at-risk.md#the-observation-count-is-not-the-history-length). La [correlazione](correlation.md#how-each-cell-is-computed) è un'eccezione: non viene mai rifiutata per storia breve. La sua soglia minima — un parametro regolabile dell'analisi, 20 osservazioni per impostazione predefinita — si applica alla matrice nel suo complesso: ogni serie condivide un unico calendario, quindi ogni coppia ha lo stesso numero di osservazioni, e sotto la soglia ogni cella torna `insufficient` senza coefficiente, in un risultato marcato `partial` anziché `unavailable`.

---

## ⚠️ Limitazioni {: #limitations }

!!! warning "Uno stato descrive gli input, non il modello"

    `ok` dice che la serie era completa, non che la metrica sia appropriata, che la finestra sia abbastanza lunga o che il passato somigli al futuro. Ogni avvertenza presente nelle pagine delle metriche vale ancora per un valore costruito su dati impeccabili.

!!! warning "I dati mantenuti abbelliscono una misura di rischio"

    Un prezzo mantenuto da una data precedente produce un rendimento di periodo esattamente pari a zero nella valuta propria dello strumento; dopo la conversione nella valuta di destinazione, solo il tasso di cambio lo muove. Ogni prezzo mantenuto fa questo, per quanto giovane, e quei rendimenti entrano nel campione come qualsiasi altra osservazione. Entro la [soglia di obsolescenza](#staleness-threshold) è ordinario: durante un fine settimana, un festivo o un giorno in cui solo un altro mercato ha scambiato, lo strumento non ha avuto una nuova quotazione, e la sua quotazione successiva si riallinea. Un prezzo mantenuto per più tempo sostituisce giorni in cui lo strumento potrebbe benissimo essersi mosso, quindi una serie ricca di tali punti riporta **meno** movimento di quello che lo strumento ha effettivamente avuto. Sono i punti che lo stato `carried_forward` conta, e lo stato è l'avviso che un valore dall'aria calma può essere calmo per la ragione sbagliata.

!!! warning "Una posizione valorizzata dalle sue operazioni resta ferma"

    Sul TWRR di un portafoglio, una posizione che nessun mercato prezza è valorizzata [al prezzo del suo ultimo acquisto o vendita](../performance-metrics/portfolio-engine/price-resolution.md) — o, ricevuta solo tramite trasferimento, al costo di quel trasferimento —, quindi nella sua valuta propria resta ferma da un'operazione alla successiva; senza né l'uno né l'altro, è valorizzata al suo costo, che resta fermo anche nella valuta di destinazione. Per un prestito tenuto al suo valore nominale — un tipico investimento di crowdfunding — questa è la verità. Per una posizione il cui valore si muove davvero, appiattisce ogni cifra letta sul TWRR, proprio come fa un prezzo mantenuto. Nessuno stato la segnala: il report del portafoglio non conta ai fini del proprio stato una valorizzazione da operazioni o al costo, e per una posizione senza fonte di prezzo tratta quella valorizzazione come lo stato inteso e permanente.

!!! warning "Nessuna soglia di qualità scarta un valore"

    A parte i conteggi minimi di osservazioni descritti sopra, al di sotto dei quali un'analisi non viene calcolata affatto o ogni cella di correlazione torna `insufficient`, nulla nel sistema dichiara una copertura o una quota di dati mantenuti oltre la quale un valore debba essere scartato. Quell'assenza è deliberata — il numero onesto è quello che arriva con la propria provenienza — ma significa che il giudizio finale è tuo, e non può essere delegato all'etichetta dello stato.

---

## 🔗 Correlati {: #related }

- 📅 **[Annualizzazione osservata](observed-annualization.md)** — il fattore di annualizzazione contato dalle stesse osservazioni, e perché una serie sparsa non è necessariamente una serie rotta
- 🔗 **[Correlazione](correlation.md)** — riporta il conteggio delle osservazioni dietro ogni singola cella
- 📊 **[Volatilità](volatility.md)** — la cifra più direttamente appiattita dai prezzi mantenuti
