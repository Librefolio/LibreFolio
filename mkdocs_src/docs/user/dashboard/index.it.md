# 📊 Dashboard

La Dashboard è il **centro di comando del tuo portafoglio** — una singola schermata che ti dice quanto vale il tuo portafoglio, come sta rendendo e dove sono allocati i tuoi soldi.

<div class="lf-screenshot-carousel" data-carousel="carousel-dashboard-main" data-carousel-interval="6000" data-show-titles="true" style="margin: 1rem 0 2rem 0;">
  <img class="gallery-img lf-screenshot-carousel-item is-active" data-category="dashboard" data-name="main" data-title="📈 Vista principale (assoluta)" alt="Dashboard — Modalità assoluta">
  <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="dashboard" data-name="main-pct" data-title="📈 Vista principale (percentuale)" alt="Dashboard — Modalità percentuale">
  <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="dashboard" data-name="allocation-type-now" data-title="📊 Allocation" alt="Dashboard — Allocazione">
</div>

## 🗂️ Layout a schede

L'interfaccia della Dashboard è organizzata in quattro schede principali, che ti permettono di passare tra diversi livelli di dettaglio:

1. **Panoramica** (predefinita): metriche chiave, saldi di cassa e grafici visivi del tuo portafoglio.
2. **[Posizioni e analisi](positions.md)**: posizioni aperte, pesi e analisi dettagliata dei lotti fiscali (FIFO).
3. **[Risk](#risk-tab)**: il pannello **Portfolio risk**, che risponde a quattro domande sul rischio del tuo portafoglio.
4. **Transazioni**: le operazioni nell'intervallo di date e nell'ambito broker selezionati, come elenco impaginato in sola lettura — fai doppio clic su una riga per aprirne il visualizzatore di dettaglio. Vedi [Transazioni](../transactions/index.md) per la guida completa.

---

## 📈 Scheda Panoramica

La scheda Panoramica è la pagina iniziale predefinita. È strutturata nelle seguenti sezioni:

| Sezione | Descrizione |
|---------|-------------|
| **[Schede KPI](kpi-cards.md)** | Riepilogo di patrimonio netto, P&L periodo e metriche di tasso di rendimento. |
| **Saldi di cassa** | Saldi liquidi raggruppati per valuta nell'ambito dei broker attivi. |
| **[Grafico di crescita](charts.md#portfolio-growth-chart)** | Valore del portafoglio nel tempo in tre viste: valori assoluti (Abs), tassi di rendimento (%) e denaro effettivamente guadagnato (P&L). |
| **[Pannello di allocazione](charts.md#allocation-panel)** | Grafici a ciambella e storici a barre impilate raggruppati per Tipo, Settore e Area geografica. |

### 🪙 Saldi di cassa

Direttamente sotto le schede KPI, il pannello **Saldi di cassa** mostra il totale della liquidità aggregato per valuta. Ad esempio, se detieni USD presso il broker A ed EUR presso il broker B, entrambi i saldi saranno visualizzati affiancati.

Quando applichi un filtro broker, i saldi di cassa si aggiornano automaticamente per riflettere solo la liquidità detenuta presso i broker selezionati.

---

## 🛡️ Scheda Risk {: #risk-tab }

La scheda Risk contiene il pannello **Portfolio risk**, che risponde a quattro domande sul rischio del tuo portafoglio: **Quanto può farti male?**, **Sono diversificato quanto penso?**, **Sono pagato per questo rischio?** e **E se…?** Copre sempre l'intero portafoglio — ogni broker che possiedi con una quota superiore allo 0% — e segue l'intervallo di date e la valuta target della dashboard, ma non il filtro broker: quando un filtro è attivo, un sottotitolo lo indica. Vedi [Scheda Risk](risk.md) per i blocchi e gli strumenti che mostrano.

---

## 🎛️ Intervallo di date, filtri e AI Export

In alto a destra nella dashboard hai diversi controlli per personalizzare la tua vista:

- **Intervallo temporale** — preset da 1 settimana a All-Time (MAX), oppure un intervallo personalizzato tramite il selettore di date.
- **Filtro broker** — filtra le metriche su uno o più broker specifici; la scheda Risk copre sempre ogni broker che possiedi, e un sottotitolo lo indica quando un filtro è attivo.
- **Valuta target** — converte dinamicamente tutte le attività e i saldi di cassa in un'unica valuta selezionata per una vista aggregata. L'elenco offre la tua valuta predefinita e le valute delle tue coppie FX configurate — entrambi gli estremi di ciascuna coppia. Una valuta che una [rotta a catena](../fx/add-pair.md) attraversa soltanto non viene offerta: sincronizzare una catena memorizza solo il tasso della sua coppia, quindi LibreFolio non ha tassi per convertire in quella valuta. Per rendere disponibile una valuta, assegnale una coppia propria: scegli **Create forex…** in fondo all'elenco, oppure spunta **Also create intermediate pairs** quando aggiungi una coppia tramite una rotta a catena.
- **AI Export** (:material-brain:) — apre un'esportazione negli appunti. Scegli **Data
  Snapshot** per soli dati fattuali, oppure un **analysis task** che include
  automaticamente le sue istruzioni e il contratto di risposta, poi seleziona il
  **livello di dettaglio** (Compact, Standard o Full). Lo snapshot del backend segue il filtro
  broker attivo, l'intervallo di date e la valuta target; LibreFolio non contatta un
  servizio AI. Vedi [Portfolio AI Export](../ai-export/portfolio.md) o la
  [panoramica di AI Export](../ai-export/index.md).

L'intervallo temporale, il filtro broker e la valuta target rimangono come li hai impostati per il resto della tua sessione in questa scheda del browser — anche ricaricando la pagina restano invariati — e si azzerano quando esci. L'intervallo temporale è condiviso con le altre pagine che ne hanno uno (le pagine Assets e FX, le loro pagine di dettaglio e la pagina di ogni broker), quindi una modifica fatta lì si riflette anche qui. Accanto a **AI Export**, il pulsante **Refresh** (:material-refresh:) ricalcola tutto su richiesta: vedi [Tornare indietro e aggiornare](#coming-back-and-refreshing).

!!! tip "L'ambito è importante"

    Quando filtri su un singolo broker, i giroconti *verso altri broker* diventano flussi esterni per quell'ambito. Questo influisce sui calcoli di [Capitale versato](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/deposited-capital.md) e [P&L](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/period-pnl.md).

!!! note "La condivisione influisce su questi numeri"

    La dashboard conta solo i broker che **possiedi** con una quota superiore allo 0%, e ogni importo da essi è **scalato in base alla tua quota di proprietà**: un proprietario con una quota del 50% vede metà del valore, del reddito e del P&L di quel broker conteggiati nei totali. I broker in cui sei un **Editor** o un **Visualizzatore** — che per regola hanno sempre una quota dello 0% — sono esclusi, come quelli che possiedi con una quota dello 0%: mancano dai totali, dal filtro broker, dalla scheda Posizioni (vista Performance e pannello lotti inclusi), dalla scheda Risk e dalla scheda Transazioni. Li vedi nella loro pagina broker dedicata, dove Editor e Visualizzatori ottengono gli importi **completi** del broker. Vedi [Condivisione broker](../brokers/sharing.md) per i dettagli.

---

## 🔄 Tornare indietro e aggiornare {: #coming-back-and-refreshing }

Torna alla Dashboard — dalla barra laterale, oppure con il pulsante **←** indietro di una pagina di un asset — e mostra subito ciò che mostrava quando l'hai lasciata: le schede KPI, i grafici, la scheda Posizioni con la sua vista Performance e il pannello [FIFO Lots Analysis](positions.md#fifo-lots-analysis), e la scheda Risk. Non ci sono segnaposto di caricamento, e le cifre dei KPI appaiono al loro valore invece di aumentare partendo da zero. Se nel frattempo hai cambiato l'intervallo temporale su un'altra pagina, la Dashboard si apre su quell'intervallo.

- **Se nel frattempo non è cambiato nulla**, è tutto: LibreFolio non ricalcola niente.
- **Se qualcosa è cambiato** — ad esempio una transazione; prezzi, tassi o eventi inseriti a mano o importati da una sincronizzazione; un asset modificato o unito; una modifica a uno dei tuoi broker o al tuo accesso ad esso; oppure il prezzo live che una pagina di un asset controlla mentre è aperta — le vecchie cifre restano a schermo mentre LibreFolio ricalcola in background, poi i numeri passano ai nuovi valori. Una sincronizzazione di prezzi o tassi che non ha portato nulla di nuovo non è un cambiamento.

Il pulsante **Refresh** ricalcola tutto, anche quando non è cambiato nulla: le cifre, la vista Performance, il pannello lotti e la scheda Risk. Nel frattempo ciò che vedi resta a schermo.

Se un ricalcolo fallisce, le cifre già a schermo restano e un messaggio te lo segnala. Nella scheda Risk, questo vale solo per le cifre del periodo e della valuta che stai visualizzando: se passi a un periodo o a una valuta per cui la scheda non ha ancora cifre e il calcolo fallisce, mostra *Risk data could not be loaded.* al posto dei suoi livelli, invece delle cifre della tua scelta precedente.

---

## 🌡️ Banner di qualità dei dati {: #data-quality-banner }

Se mancano prezzi o tassi FX alla data finale, in cima appare un banner che spiega quali asset non è stato possibile valutare.
<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="dashboard" data-name="data-quality-banner" alt="Banner della qualità dei dati nella dashboard, con i link per asset">
</div>
 Gli asset senza un provider di prezzi (inseriti manualmente, come i progetti di crowdfunding immobiliare) sono valutati al prezzo della loro ultima transazione, a meno che tu non inserisca tu stesso un prezzo più recente — questo è intenzionale e non genera un avviso. Un asset che ha un provider di prezzi ma non ha comunque un prezzo di mercato alla data finale, più di due settimane dopo che l'hai acquistato per la prima volta, è anch'esso valutato nel frattempo al prezzo della sua ultima transazione, e il banner lo elenca: un'obbligazione acquistata all'emissione, prima della sua prima quotazione, ad esempio.

Il banner ti avvisa anche quando un asset che detieni ha un provider di prezzi ma il suo prezzo più recente è **più vecchio di una settimana** alla data finale: fai clic su **Sync prices** per recuperare i prezzi mancanti, e l'avviso scompare una volta che sono aggiornati. Gli asset manuali non sono mai segnalati in questo modo, poiché non c'è nulla da sincronizzare.

Elenca inoltre gli asset con un **valore di acquisto mancante**: un trasferimento o una rettifica che ha portato unità senza un costo di carico. LibreFolio non può sapere quanto sono costate quelle unità, quindi le conta a zero nel tuo valore di acquisto e mostra il costo medio e il P&L latente di quella posizione come non disponibili (`—`). Per risolvere, trova quel trasferimento o quella rettifica tra le tue [transazioni](../transactions/index.md) e assegnagli il suo costo di carico.

I tassi di cambio vengono controllati per ogni transazione fino alla data finale — ogni acquisto, vendita e movimento di cassa è convertito al tasso della propria data — e, per valutare ciò che detieni, in ogni giorno del periodo a schermo. Quando una coppia FX configurata con un provider non ha **alcun tasso** per alcune di quelle date, il banner la elenca con l'intervallo delle date mancanti. LibreFolio converte un importo con il tasso più recente disponibile alla data o prima, per quanto vecchio, quindi queste date cadono *prima* del primo tasso memorizzato della coppia — spesso ben prima del periodo a schermo, perché ogni transazione passata contribuisce ai totali come il tuo P&L totale e il tuo valore di acquisto. Fai clic su **Sync rates** per riempirle:

- LibreFolio scarica quell'intervallo di date con **una settimana extra su ciascun lato** (mai oltre oggi), qualunque periodo stia mostrando la dashboard. La settimana extra copre i fine settimana e i giorni festivi, quando i provider non pubblicano nulla: un giorno del genere al limite dell'intervallo assume quindi il tasso del giorno lavorativo precedente.
- Una volta terminato il download, la dashboard si aggiorna e un messaggio riporta il risultato per ciascuna coppia.
- Se il download va a buon fine ma le stesse coppie sono ancora segnalate, il provider non ha tassi per le date ancora mancanti — tipicamente perché cadono prima dell'inizio della sua storia. Il messaggio diventa quindi un avviso che lo dice: inserisci quei tassi a mano nell'[editor dati](../fx/detail/data-editor.md) della coppia.

Le coppie con soli tassi manuali (nessun provider) ricevono un avviso proprio: il suo pulsante **View FX** apre la pagina della prima coppia che elenca, dove aggiungi tu stesso i tassi.

!!! tip "Riempire in una volta l'intera storia di una coppia"

    Apri la [pagina FX](../fx/index.md), scegli l'intervallo **All** (MAX) e fai clic su [Sync All](../fx/sync.md): LibreFolio scarica tutto ciò che i provider pubblicano per le tue coppie, fino a oggi. Una coppia che aggiungi con un provider lo fa da sola — vedi [Aggiungere una coppia di valute](../fx/add-pair.md).

---

## 🔗 In questa sezione

- 💰 **[Schede KPI](kpi-cards.md)** — Patrimonio netto, P&L periodo e rendimenti spiegati
- 📊 **[Grafici](charts.md)** — Grafico di crescita e Pannello di allocazione spiegati
- 🔍 **[Posizioni e analisi](positions.md)** — Posizioni aperte, viste tabella vs. mappa e analisi dettagliata dei lotti fiscali FIFO.

## 🔗 Teoria correlata

- **[NAV / Patrimonio netto](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/nav.md)**
- **[Valore contabile](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/book-value.md)**
- **[P&L periodo](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/period-pnl.md)**
- **[Capitale versato & P&L totale](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/deposited-capital.md)**
- **[Panoramica delle metriche di performance](../../financial-theory/technical-analysis/performance-metrics/index.md)**
