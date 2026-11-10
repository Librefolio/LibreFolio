# 📊 Dashboard

La Dashboard è il **centro di controllo del tuo portafoglio** — un'unica schermata che ti dice quanto vale il tuo portafoglio, come sta rendendo e dove sono allocati i tuoi soldi.

<div class="lf-screenshot-carousel" data-carousel="carousel-dashboard-main" data-carousel-interval="6000" data-show-titles="true" style="margin: 1rem 0 2rem 0;">
  <img class="gallery-img lf-screenshot-carousel-item is-active" data-category="dashboard" data-name="main" data-title="📈 Vista principale (Assoluta)" alt="Dashboard — Modalità assoluta">
  <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="dashboard" data-name="main-pct" data-title="📈 Vista principale (Percentuale)" alt="Dashboard — Modalità percentuale">
  <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="dashboard" data-name="allocation-type-now" data-title="📊 Allocazione" alt="Dashboard — Allocazione">
</div>

## 🗂️ Layout a schede

L'interfaccia della Dashboard è organizzata in quattro schede principali, che ti permettono di passare tra diversi livelli di dettaglio:

1. **Panoramica** (predefinita): metriche chiave, saldi di cassa e grafici visivi del tuo portafoglio.
2. **[Posizioni e analisi](positions.md)**: posizioni aperte, pesi e analisi dettagliata dei lotti fiscali (FIFO).
3. **[Rischio](#risk-tab)**: il pannello **Rischio di portafoglio**, che risponde a quattro domande sul rischio del tuo portafoglio.
4. **Transazioni**: le operazioni nell'intervallo di date e nell'ambito broker selezionati, come elenco paginato in sola lettura — fai doppio clic su una riga per aprire il visualizzatore di dettaglio. Vedi [Transazioni](../transactions/index.md) per la guida completa.

---

## 📈 Scheda Panoramica

La scheda Panoramica è la pagina iniziale predefinita. È strutturata nelle seguenti sezioni:

| Sezione | Descrizione |
|---------|-------------|
| **[Schede KPI](kpi-cards.md)** | Riepilogo di Patrimonio netto, P&L periodo e metriche di tasso di rendimento. |
| **Saldi di cassa** | Saldi di cassa raggruppati per valuta nell'ambito broker attivo. |
| **[Grafico di crescita](charts.md#portfolio-growth-chart)** | Valore del portafoglio nel tempo in tre viste: valori assoluti (Abs), tassi di rendimento (%) e il denaro effettivamente guadagnato (P&L). |
| **[Pannello di allocazione](charts.md#allocation-panel)** | Grafici a ciambella e grafici storici a barre impilate raggruppati per Tipo, Settore e Area geografica. |

### 🪙 Saldi di cassa

Subito sotto le schede KPI, il pannello **Saldi di cassa** mostra la tua liquidità totale aggregata per valuta. Per esempio, se detieni USD presso il broker A ed EUR presso il broker B, entrambi i saldi vengono mostrati affiancati.

Quando applichi un filtro broker, i saldi di cassa si aggiornano automaticamente per riflettere solo la liquidità detenuta presso i broker selezionati.

---

## 🛡️ Scheda Rischio {: #risk-tab }

La scheda Rischio ospita il pannello **Rischio di portafoglio**, che risponde a quattro domande sul rischio del tuo portafoglio: **Quanto può farmi male?**, **Sono diversificato quanto penso?**, **Vengo pagato per questo rischio?** e **E se…?** Copre sempre l'intero portafoglio — ogni broker che possiedi con una quota superiore allo 0% — e segue l'intervallo di date e la valuta obiettivo della dashboard, ma non il filtro broker: quando un filtro è attivo, un sottotitolo lo segnala. Vedi [Scheda Rischio](risk.md) per i blocchi e gli strumenti che mostrano.

---

## 🎛️ Intervallo di date, filtri e AI Export

In alto a destra nella dashboard hai diversi controlli per personalizzare la visualizzazione:

- **Intervallo temporale** — preimpostazioni da **1W** a **All**, oppure un intervallo personalizzato tramite il selettore di date.
- **Filtro broker** — limita le metriche a uno o più broker specifici; la scheda Rischio copre sempre ogni broker che possiedi, e un sottotitolo lo segnala quando un filtro è attivo.
- **Valuta obiettivo** — converte dinamicamente tutti gli asset e i saldi di cassa in un'unica valuta selezionata per una visualizzazione aggregata. L'elenco propone la tua valuta predefinita e le valute delle tue coppie FX configurate — entrambi gli estremi di ciascuna coppia. Una valuta che una [rotta a catena](../fx/add-pair.md) attraversa soltanto non viene proposta: sincronizzare una catena memorizza solo il tasso della propria coppia, quindi LibreFolio non ha tassi per convertire in quella valuta. Per rendere disponibile una valuta, assegnale una coppia propria: scegli **Crea forex…** in fondo all'elenco, oppure seleziona **Crea anche coppie intermedie** quando aggiungi una coppia tramite una rotta a catena.
- **AI Export** (:material-brain:) — apre un'esportazione negli appunti. Scegli **Istantanea dati** per soli dati fattuali, oppure un'**attività di analisi** che include automaticamente le sue istruzioni e il contratto di risposta, poi seleziona il **livello di dettaglio** (Compatto, Standard o Completo). L'istantanea lato backend segue il filtro broker attivo, l'intervallo di date e la valuta obiettivo; LibreFolio non contatta alcun servizio AI. Vedi [AI Export del portafoglio](../ai-export/portfolio.md) o la [panoramica di AI Export](../ai-export/index.md).

L'intervallo temporale, il filtro broker e la valuta obiettivo restano come li hai impostati per il resto della sessione in questa scheda del browser — anche ricaricando la pagina restano — e si azzerano quando esci. L'intervallo temporale è condiviso con le altre pagine che ne hanno uno (le pagine Asset e FX, le loro pagine di dettaglio e la pagina di ciascun broker), quindi una modifica fatta lì compare anche qui. Accanto a **AI Export**, il pulsante **Aggiorna** (:material-refresh:) ricalcola tutto su richiesta: vedi [Tornare e aggiornare](#coming-back-and-refreshing).

!!! tip "L'ambito conta"

    Quando filtri su un singolo broker, i giroconti *verso altri broker* diventano flussi esterni per quell'ambito. Questo influisce sui calcoli del [Capitale versato](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/deposited-capital.md) e del [P&L](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/period-pnl.md).

!!! note "La condivisione influisce su questi numeri"

    La dashboard conta solo i broker che **possiedi** con una quota superiore allo 0%, e ogni importo che ne proviene è **calcolato in proporzione alla tua quota di proprietà**: un proprietario con una quota del 50% vede metà del valore, del reddito e del P&L di quel broker conteggiati nei totali. I broker in cui sei **Editor** o **Visualizzatore** — che per regola hanno sempre una quota dello 0% — sono esclusi, come quelli che possiedi con una quota dello 0%: mancano dai totali, dal filtro broker, dalla scheda Posizioni (compresi la vista Periodo e il pannello dei lotti), dalla scheda Rischio e dalla scheda Transazioni. Li vedi nella loro pagina del broker, che conta il broker **per intero** per ogni ruolo. Vedi [Condivisione dei broker](../brokers/sharing.md) per i dettagli.

La pagina di un broker è questa stessa Dashboard su un singolo broker, con la scheda **Info** propria di quel broker: vedi [La pagina del broker è la Dashboard su un singolo broker](../brokers/index.md#broker-page-is-dashboard).

---

## 🔄 Tornare e aggiornare {: #coming-back-and-refreshing }

Torna alla Dashboard — dalla barra laterale o con il pulsante indietro **←** di una pagina asset — e mostra subito ciò che mostrava quando l'hai lasciata: le schede KPI, i grafici, la scheda Posizioni con la sua vista Periodo e il pannello [Analisi dei lotti FIFO](positions.md#fifo-lots-analysis), e la scheda Rischio. Non ci sono segnaposto di caricamento e le cifre KPI compaiono direttamente al loro valore invece di contare da zero. Se nel frattempo hai cambiato l'intervallo temporale in un'altra pagina, la Dashboard si apre su quell'intervallo.

- **Se nel frattempo non è cambiato nulla**, è tutto: LibreFolio non ricalcola niente.
- **Se qualcosa è cambiato** — per esempio una transazione; prezzi, tassi o eventi inseriti a mano o importati da una sincronizzazione; un asset modificato o unito; una modifica a uno dei tuoi broker o al tuo accesso a esso; oppure il prezzo live che una pagina asset verifica mentre è aperta — le vecchie cifre restano sullo schermo mentre LibreFolio ricalcola in background, poi i numeri passano ai nuovi valori. Una sincronizzazione di prezzi o tassi che non ha portato nulla di nuovo non è un cambiamento.

Il pulsante **Aggiorna** ricalcola tutto, anche quando non è cambiato nulla: le cifre, la vista Periodo, il pannello dei lotti e la scheda Rischio. Nel frattempo ciò che vedi resta sullo schermo.

Se un ricalcolo fallisce, le cifre già sullo schermo restano e un messaggio te lo segnala. Nella scheda Rischio questo vale solo per le cifre del periodo e della valuta che stai visualizzando: se passi a un periodo o a una valuta per cui la scheda non ha ancora cifre e il calcolo fallisce, mostra *Impossibile caricare i dati di rischio.* al posto dei suoi livelli, invece delle cifre della tua scelta precedente.

---

## 🌡️ Banner di qualità dei dati {: #data-quality-banner }

Se alla data finale mancano prezzi o tassi FX, in alto compare un banner che spiega quali asset non è stato possibile valutare.
<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="dashboard" data-name="data-quality-banner" alt="Banner di qualità dei dati della Dashboard con link per ogni asset">
</div>
 Gli asset senza un provider di prezzi (inseriti manualmente, come i progetti di crowdfunding immobiliare) sono valutati al prezzo del loro ultimo acquisto o della loro ultima vendita, a meno che tu non inserisca un prezzo più recente — questo è intenzionale e non genera alcun avviso. Un asset che ha un provider di prezzi ma alla data finale non ha ancora un prezzo di mercato, più di due settimane dopo il tuo primo acquisto, viene nel frattempo valutato anch'esso al prezzo del suo ultimo acquisto o della sua ultima vendita, e il banner lo elenca: per esempio un'obbligazione acquistata all'emissione, prima della sua prima quotazione.

Una rettifica registra quanto sono costate le unità, mai un prezzo. Lo stesso fa un trasferimento, con un'eccezione: per un asset che non ha ancora nient'altro — nessun prezzo di mercato, nessun acquisto o vendita, nessuna rettifica, nessuna uscita precedente — il costo che hai indicato per un trasferimento in entrata vale come suo prezzo, una stima, finché un prezzo reale o uno scambio non lo sostituisce. Tale asset è valutato a quel costo convertito al tasso di cambio di ogni giorno, quindi il suo valore si muove con il tasso, e il banner lo tratta come un asset valutato al suo ultimo acquisto o vendita: per un asset con un provider di prezzi, viene elencato più di due settimane dopo l'arrivo del trasferimento, se non ha ancora un prezzo di mercato. Un asset quotato spostato tra i tuoi broker mantiene il suo prezzo di mercato. Un asset che detieni senza alcun prezzo — nessun prezzo di mercato, nessun acquisto o vendita e nessun trasferimento del genere, come un asset ricevuto tramite una rettifica — è valutato a quanto ti è costato, quando tale costo è noto, senza plusvalenze o minusvalenze non realizzate. Per un asset manuale questo è intenzionale e non genera alcun avviso; per un asset con un provider di prezzi, da più di due settimane dopo il tuo primo acquisto, il banner lo elenca come *valutato al costo* finché non ottiene un prezzo.

Il banner ti avvisa anche quando un asset che detieni ha un provider di prezzi ma il suo prezzo più recente è **più vecchio di una settimana** alla data finale: fai clic su **Sincronizza prezzi** per scaricare i prezzi mancanti, e l'avviso scompare una volta che sono aggiornati. Gli asset manuali non vengono mai segnalati così, poiché non c'è nulla da sincronizzare.

Lo stesso vale per i **tassi di cambio obsoleti**. Quando il portafoglio è valutato alla data finale con un tasso di cambio il cui tasso memorizzato più recente è **più vecchio di una settimana**, una riga di avviso elenca le coppie FX interessate, con un unico pulsante **Sincronizza tassi** per tutte. Se la sincronizzazione riesce ma il provider non ha ancora un tasso più recente, un avviso lo dice — *Il provider non ha ancora tassi più recenti per USD → EUR: riprova più tardi* — invece di un semplice messaggio di successo; riprova più tardi e la riga scompare una volta memorizzato un tasso più recente.

Elenca anche gli asset con un **valore di acquisto mancante**: un trasferimento o una rettifica che ha portato unità senza un costo di carico. LibreFolio non può sapere quanto sono costate quelle unità, quindi le conta a zero nel tuo valore di acquisto e mostra il costo medio e il P&L latente di quella posizione come non disponibili (`—`). Per risolvere, trova quel trasferimento o quella rettifica tra le tue [transazioni](../transactions/index.md) e assegnagli il suo costo di carico.

Ti avvisa inoltre dei **codici valuta che non sono codici ISO**: un numero o un nome, come `978` o `EURO`, che una versione precedente di LibreFolio ha salvato così come l'hai digitato. Ora LibreFolio salva solo codici come `EUR`, quindi gli importi in un simile valore non possono essere convertiti, e una riga che lo contiene non può essere salvata di nuovo dopo una modifica finché il suo codice non viene corretto. L'avviso indica il valore e il codice che rappresenta (`978` è `EUR`) e non elenca alcun tasso di cambio da aggiungere, poiché nessuno servirebbe. Quando il valore è la tua valuta predefinita, ti dice di sceglierla di nuovo in **Impostazioni › Preferenze**. Il tuo amministratore può elencare ogni valore di questo tipo con `./dev.py db currencies` ([Strumenti di amministrazione CLI](../../admin/cli_tools.md), «Codici valuta che non sono codici ISO»).

Segnala inoltre, senza chiederti di correggere nulla, i **trasferimenti tra broker che possiedi con quote diverse**: ciascun lato è conteggiato secondo la quota del proprio broker, quindi ciò che esce da un broker e ciò che arriva all'altro differiscono, e LibreFolio conta quella differenza come guadagno o perdita.

I tassi di cambio vengono verificati per ogni transazione fino alla data finale — ogni acquisto, vendita e movimento di cassa è convertito al tasso della propria data — e, per valutare ciò che detieni, in ogni giorno del periodo visualizzato: i tuoi titoli e anche la liquidità che tieni in un'altra valuta, valutata ogni giorno al tasso di quel giorno. Quando una coppia FX configurata con un provider non ha **alcun tasso** per alcune di quelle date, il banner la elenca con l'intervallo delle date mancanti. LibreFolio converte un importo con il tasso più recente disponibile alla sua data o prima, per quanto vecchio, quindi queste date sono *precedenti* al primo tasso memorizzato della coppia — spesso ben prima del periodo visualizzato, perché ogni transazione passata contribuisce a totali come il tuo P&L totale e il tuo valore di acquisto. Fai clic su **Sincronizza tassi** per riempirle:

- LibreFolio scarica quell'intervallo di date con **una settimana in più su ciascun lato** (mai oltre oggi), qualunque periodo stia mostrando la dashboard. La settimana in più copre i fine settimana e i giorni festivi, quando i provider non pubblicano nulla: un giorno di questo tipo ai bordi dell'intervallo prende quindi il tasso del giorno lavorativo precedente.
- Al termine del download, la dashboard si aggiorna e un messaggio riporta il risultato per ciascuna coppia.
- Se il download va a buon fine ma le stesse coppie sono ancora segnalate, il provider non ha tassi per le date ancora mancanti — di solito perché sono precedenti all'inizio della sua cronologia. Il messaggio diventa allora un avviso che lo dice: inserisci quei tassi a mano nell'[editor dati](../fx/detail/data-editor.md) della coppia.

Le coppie con soli tassi manuali (senza provider) ricevono un avviso a parte: il suo pulsante **Visualizza FX** apre la pagina della prima coppia elencata, dove aggiungi tu stesso i tassi.

!!! tip "Riempi in una volta tutta la cronologia di una coppia"

    Apri la [pagina FX](../fx/index.md), scegli l'intervallo **All** e fai clic su [Sincronizza tutto](../fx/sync.md): LibreFolio scarica tutto ciò che i provider pubblicano per le tue coppie, fino a oggi. Una coppia che aggiungi con un provider lo fa da sola — vedi [Aggiungere una coppia FX](../fx/add-pair.md).

---

## 🔗 In questa sezione

- 💰 **[Schede KPI](kpi-cards.md)** — Patrimonio netto, P&L periodo e rendimenti spiegati
- 📊 **[Grafici](charts.md)** — il grafico di crescita e il pannello di allocazione spiegati
- 🔍 **[Posizioni e analisi](positions.md)** — posizioni aperte, viste a tabella e a mappa e analisi dettagliata dei lotti fiscali FIFO.

## 🔗 Teoria correlata

- **[NAV / Patrimonio netto](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/nav.md)**
- **[Valore contabile](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/book-value.md)**
- **[P&L periodo](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/period-pnl.md)**
- **[Capitale versato e P&L totale](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/deposited-capital.md)**
- **[Panoramica delle metriche di performance](../../financial-theory/technical-analysis/performance-metrics/index.md)**
