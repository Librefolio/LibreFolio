# 📊 Grafici

Sotto le schede KPI, il grafico **Crescita del portafoglio** e il pannello **Allocazione degli asset** mostrano da dove è passato il tuo portafoglio e di cosa è composto. Entrambi seguono l'intervallo temporale e il filtro broker della dashboard, e la pagina di un broker li mostra solo per quel broker.

---

## 📈 Grafico Crescita del portafoglio {: #portfolio-growth-chart }

Il grafico della crescita mostra come si è evoluto il tuo portafoglio nel periodo selezionato: l'interruttore **Assoluto / % / P&L** nell'angolo in alto a destra passa tra valori assoluti, tassi di rendimento e il denaro effettivamente guadagnato.

Su un periodo lungo il grafico raggruppa i giorni per restare leggibile: in settimane, poi mesi e, per uno storico di molti decenni, anni. Un badge **Settimanale**, **Mensile** o **Annuale** in alto a sinistra del grafico indica quale raggruppamento è attivo. Quando non è raggruppato nulla, non c'è alcun badge.

### 〰️ Come vengono disegnate le linee {: #line-shape }

Ogni grafico unisce i suoi punti secondo una di tre forme: **Segmenti** (l'impostazione predefinita, una linea retta tra due punti), **A gradini** (ogni valore resta fino al successivo) o **Curva morbida** (una linea dolce che non supera mai né scende mai sotto i due punti vicini, così non disegna valori che non sono mai esistiti). Scegli la forma nella prima pagina del tour di benvenuto e successivamente in **Impostazioni → Preferenze**; si applica a ogni grafico in questo browser. Nelle pagine di dettaglio di asset e FX, le impostazioni grafico hanno anche una riga **Forma della linea**, per dare a quel singolo grafico una forma propria. La forma cambia solo il modo in cui i punti vengono uniti: il valore di un giorno nel tooltip è sempre quello che il report conserva per quel giorno. Dove un grafico mostra settimane o mesi, i punti non sono gradini, quindi **A gradini** disegna segmenti.

Il grafico ricorda la tua ultima visualizzazione, inclusa la sotto-visualizzazione P&L, in questo browser e per ciascun utente, e la condivide con le pagine dei broker. Parte da **Assoluto**. Senza dati sui tassi di rendimento, **%** è in grigio e il grafico mostra **Assoluto**, ma conserva la tua scelta: **%** ricompare non appena ci sono dati da disegnare — dopo che cambi il periodo o il broker, o la prossima volta che apri il grafico — a meno che tu non scelga nel frattempo un'altra visualizzazione.

<div class="lf-screenshot-carousel" data-carousel="carousel-growth" data-carousel-interval="5000" data-show-titles="true" style="margin: 1.5rem 0 2.5rem 0;">
  <div class="lf-screenshot-carousel-item is-active chart-crop-container" data-title="📈 Modalità assoluta" alt="Grafico della crescita — Modalità assoluta">
     <img class="gallery-img" data-category="dashboard" data-name="main" alt="Grafico della crescita — Modalità assoluta">
  </div>
  <div class="lf-screenshot-carousel-item chart-crop-container" data-title="📈 Modalità percentuale" alt="Grafico della crescita — Modalità percentuale">
     <img class="gallery-img" data-category="dashboard" data-name="main-pct" alt="Grafico della crescita — Modalità percentuale">
  </div>
</div>

**Nascondi importi** (il pulsante a forma di occhio nella barra superiore) trasforma ogni importo sull'asse e nei tooltip in `•••`; segni, valute, linee e colori restano. Vedi [Modalità privacy](../settings/preferences.md#privacy-mode).

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="dashboard" data-name="privacy-masked" alt="La dashboard con Nascondi importi attivo: il pulsante a forma di occhio barrato nell'intestazione, gli importi delle schede KPI e dei saldi di cassa mostrati come ••• con il loro segno e la loro valuta, le percentuali ancora leggibili e l'asse di Crescita del portafoglio mascherato" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

### 💶 Assoluto — valori assoluti

| Elemento | Colore | Significato |
|---------|-------|---------|
| Area — **Valore di acquisto** | Blu | Quanto ti sono costate le posizioni che detieni (costo medio × quantità) |
| Area — **Rendimenti** | Smeraldo | Rendimenti detenuti come liquidità (dividendi, interessi, plusvalenze realizzate non ancora reinvestite, guadagni da cambio sulla liquidità detenuta in un'altra valuta) |
| Area — **Capitale** | Grigio-verde | Depositi non ancora investiti, detenuti come liquidità |
| Linea — **[Valore netto](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/nav.md)** | Verde scuro continuo | Valore totale del portafoglio ai prezzi di mercato correnti |
| Linea — **[Capitale versato](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/deposited-capital.md)** | Grigio tratteggiato | Capitale esterno netto conferito nel tempo |

**Il divario tra le due linee è il tuo P&L totale**: ogni guadagno mai prodotto (plusvalenze non realizzate e realizzate, interessi, dividendi e guadagni o perdite da cambio sulla liquidità detenuta in un'altra valuta) meno commissioni e imposte. Il tooltip mostra entrambe le linee, il P&L totale in verde o rosso e la ripartizione: **Asset al costo** (l'area blu, inclusi gli asset che si spostano tra i tuoi broker), **Rendimenti** e **Capitale**.

**Gli asset valutati al loro prezzo di acquisto**, come i prestiti P2P senza un prezzo live di mercato, mantengono il NAV vicino al Valore di acquisto, quindi il divario può essere sottile: leggi il **P&L totale** nel tooltip.

**Denaro da un broker fuori dalla visualizzazione.** Nella pagina di un broker, o con il filtro broker attivo, il denaro ricevuto da un broker fuori dalla visualizzazione è **Capitale**, come lo sarebbe un deposito — oppure di nuovo **Rendimenti**, se riporta rendimenti che avevi prelevato in precedenza. Il denaro inviato a un broker fuori dalla visualizzazione lascia prima il **Capitale**, poi i **Rendimenti**, come farebbe un prelievo. Lo stesso vale per la metà di un trasferimento la cui altra metà è stata eliminata o scollegata, in ogni visualizzazione.

🔗 **Teoria**: [Capitale versato e P&L totale](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/deposited-capital.md) · [Scomposizione della liquidità](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/deposited-capital.md#three-pool-cash-model)

### 📉 % — tasso di rendimento

Ogni linea è il rendimento accumulato dall'inizio del periodo selezionato:

| Serie | Cosa mostra |
|--------|--------------|
| **[MWRR cumulativo](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/mwrr.md)** | Il tuo rendimento personale ponderato per il denaro, inclusa la tempistica dei depositi |
| **[TWRR](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/twrr.md)** | Rendimento puro della strategia sugli asset, ignorando quando hai depositato |
| **[ROI](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/roi.md)** | Rendimento grezzo sul capitale netto investito |

Il divario tra MWRR e TWRR è l'[Effetto timing](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/timing-effect.md). La linea MWRR presenta un vuoto nei giorni senza MWRR — un valore pari a zero o inferiore, oppure prelievi netti che non lasciano capitale investito — secondo la stessa regola delle schede MWRR ([MWRR](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/mwrr.md)). La linea TWRR presenta un vuoto nei giorni in cui il tuo portafoglio vale zero o meno, ad esempio dopo che hai venduto tutto e prelevato la liquidità, secondo la stessa regola della scheda TWRR; dopo nuovi depositi riparte da dove si trovava ([Quando non viene mostrato il TWRR](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/twrr.md#when-no-twrr)). La linea ROI non ha vuoti. Quando l'ultimo giorno del periodo non ne presenta, il [banner di qualità dei dati](index.md#data-quality-banner) dice *Impossibile calcolare il MWRR per questo periodo*.

### 💰 P&L — il denaro che hai guadagnato {: #pnl-mode }

**P&L** traccia il tuo **P&L totale** (NAV meno capitale versato): quanto denaro ha effettivamente prodotto il portafoglio dall'inizio. Lo zoom non riavvia il conteggio da zero.

Un secondo interruttore, in alto a sinistra dell'area del grafico, seleziona come disegnarlo (solo icone su un grafico stretto):

| Visualizzazione | Cosa disegna | La domanda a cui risponde |
|------|---------------|------------------------|
| **Linea** | P&L accumulato come singola linea | Come si è mosso il mio risultato nel tempo? |
| **Candele** | Una candela per periodo, da un giorno a un anno | Quanto ampia è stata l'oscillazione all'interno di ciascun periodo? |
| **Entrate** | Barre della liquidità che si è effettivamente mossa | Da dove è arrivato il denaro e quanto mi è costato? |

#### Linea — P&L accumulato {: #pnl-line }

- La linea è **verde sopra zero e rossa sotto**.
- Una **linea grigia tratteggiata** segna il P&L del primo giorno nella visualizzazione: il divario rispetto a essa è ciò che hai guadagnato o perso dal bordo sinistro.

<div class="lf-screenshot-carousel" style="margin: 1.5rem 0 2.5rem 0;">
  <div class="lf-screenshot-carousel-item is-active chart-crop-container" alt="Il grafico Crescita del portafoglio in modalità P&L, visualizzazione Linea: la linea del P&L totale in verde, la linea grigia tratteggiata al P&L del primo giorno nella visualizzazione e una linea tratteggiata per broker">
     <img class="gallery-img" data-category="dashboard" data-name="growth-pnl-line" alt="Il grafico Crescita del portafoglio in modalità P&L, visualizzazione Linea: la linea del P&L totale in verde, la linea grigia tratteggiata al P&L del primo giorno nella visualizzazione e una linea tratteggiata per broker">
  </div>
</div>

**Linee dei broker.** Con due o più broker nell'ambito, ogni broker riceve una linea tratteggiata e una riga nel tooltip con la sua quota del totale; le quote si sommano al totale ogni giorno. La linea di un broker è il P&L prodotto mentre il valore si trovava presso quel broker: spostare denaro o titoli tra due tuoi broker non è né un guadagno né una perdita, quindi nessuna linea salta quando arriva un trasferimento.

- **In transito** — finché il trasferimento non arriva, il valore e le sue variazioni di prezzo o di cambio restano presso il broker da cui è partito.
- **Quote di proprietà diverse** — quando i due broker hanno [quote di proprietà](../brokers/sharing.md) diverse, la linea ricevente mantiene un gradino il giorno di arrivo: lo stesso gradino mostrato dal totale.
- **Nessun valore il giorno di arrivo** — se manca un tasso di cambio, o il titolo non ha ancora un prezzo e nessun costo è stato registrato al suo arrivo, il salto resta: non si ipotizza nulla. Un titolo senza alcun prezzo si sposta al costo che il broker ricevente registra per esso, il valore che LibreFolio gli attribuisce lì; se una parte di ciò che quel broker ha pagato per l'asset era già sconosciuta, la sua linea assorbe il divario.
- **Broker fuori dalla visualizzazione** — nella pagina di un broker, o con il filtro broker attivo, i titoli inviati a o ricevuti da un broker fuori dalla visualizzazione contano come capitale al loro valore di mercato in quel giorno — al loro costo se non hanno alcun prezzo — non come guadagno o perdita; il denaro conta come deposito o prelievo. Quando l'altro broker di un trasferimento viene eliminato, la metà rimasta non è più un trasferimento: i titoli diventano una rettifica, conteggiata come capitale al loro costo anziché al loro valore di mercato, e il denaro un deposito o un prelievo (vedi [Modifica o elimina un broker](../brokers/index.md)). Restano un trasferimento solo i titoli inviati per il cui costo medio manca un tasso di cambio, conteggiati al valore di mercato.

Con un solo broker, o nella pagina di un broker, viene disegnato solo il totale.

🔗 **Teoria**: [Trasferimenti interni nelle linee dei broker](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/deposited-capital.md#internal-transfers-broker-lines)

#### Candele — l'oscillazione all'interno del periodo {: #pnl-candles }

Ogni periodo della [larghezza che scegli](#pnl-width) diventa una **candela** composta da valori di P&L, non da prezzi. La sua **chiusura** è esattamente il P&L totale che **Linea** mostra per quel giorno.

<div class="lf-screenshot-carousel" style="margin: 1.5rem 0 2.5rem 0;">
  <div class="lf-screenshot-carousel-item is-active chart-crop-container" alt="Il grafico Crescita del portafoglio in modalità P&L, visualizzazione Candele a 3D: le candele sintetiche del P&L, i pulsanti di larghezza da 3D a 6M nell'angolo in alto a destra dell'area del grafico, le etichette dei periodi sull'asse e la didascalia Sintetico sotto il grafico">
     <img class="gallery-img" data-category="dashboard" data-name="growth-pnl-candles" alt="Il grafico Crescita del portafoglio in modalità P&L, visualizzazione Candele a 3D: le candele sintetiche del P&L, i pulsanti di larghezza da 3D a 6M nell'angolo in alto a destra dell'area del grafico, le etichette dei periodi sull'asse e la didascalia Sintetico sotto il grafico">
  </div>
</div>

!!! warning "I massimi e i minimi sono ipotetici"

    Il massimo e il minimo di una candela sommano il massimo e il minimo giornalieri di ciascun asset, che non sono stati raggiunti nello stesso momento: quello stato del portafoglio potrebbe non essere mai esistito, come dice la didascalia sotto il grafico (*Sintetico — i massimi/minimi tra asset sono ipotetici e non simultanei*). Leggili come l'ampiezza massima dell'oscillazione che il portafoglio *avrebbe potuto* avere.

Aspettati anche:

- **Nessun volume** — il P&L di un portafoglio non ha volume scambiato.
- **Corpi sottili, ombre lunghe** — apertura e chiusura sono di solito vicine mentre l'intervallo sommato è ampio.
- **Vuoti** — un giorno in cui un asset detenuto non ha potuto essere valutato non ha una candela anziché una candela ipotizzata.

Il tooltip mostra il periodo, **Apertura**, **Chiusura**, **Massimo** e **Minimo**, più una riga per broker quando ce ne sono due o più nell'ambito.

#### Entrate — la liquidità che si è effettivamente mossa {: #pnl-income }

**Entrate** mette da parte le valutazioni e traccia i tuoi flussi di cassa reali. Ogni barra è la **somma** dei flussi del suo periodo, in un massimo di tre colonne:

| Colonna | Barre | Cosa rappresenta |
|--------|------|--------------------|
| Entrate e costi | **Dividendi** · **Interessi** sopra zero, **Commissioni e imposte** sotto | Cosa ti ha pagato il portafoglio e quanto ti è costata l'attività |
| Depositi | **Deposito** | Denaro nuovo che hai versato (i prelievi non vengono disegnati) |
| Acquisti | **Valore di acquisto**, in due zone: **Nuovo capitale** in basso, **Reinvestito** in alto | Quanto hai speso per gli acquisti, suddiviso per provenienza del denaro |

<div class="lf-screenshot-carousel" style="margin: 1.5rem 0 2.5rem 0;">
  <div class="lf-screenshot-carousel-item is-active chart-crop-container" alt="Il grafico Crescita del portafoglio in modalità P&L, visualizzazione Entrate a 1M: gruppi mensili di barre per Interessi, Commissioni e imposte sotto zero, Deposito e Valore di acquisto">
     <img class="gallery-img" data-category="dashboard" data-name="growth-pnl-income" alt="Il grafico Crescita del portafoglio in modalità P&L, visualizzazione Entrate a 1M: gruppi mensili di barre per Interessi, Commissioni e imposte sotto zero, Deposito e Valore di acquisto">
  </div>
</div>

Come leggerlo:

- **Nuovo capitale o reinvestito.** Un acquisto spende prima i rendimenti già detenuti come liquidità presso quel broker (**Reinvestito**, verde come in **Assoluto**); il resto è **Nuovo capitale** (blu). Il denaro spostato da o verso un broker fuori dalla visualizzazione modifica quella liquidità come farebbe un deposito o un prelievo, come in **Assoluto** sopra. Le vendite non vengono mai disegnate.
- **I segni vengono mantenuti.** Una correzione negativa su un dividendo passato riduce la barra dei dividendi; commissioni e imposte restano sotto zero.
- **Coincide con i KPI.** Per le stesse date e gli stessi broker, la somma di **Dividendi** e **Interessi** corrisponde esattamente alla riga **Dividendi e interessi** della [scheda P&L periodo](kpi-cards.md#card-1-period-pl).
- **Una sola voce di legenda.** Entrambe le zone di acquisto si chiamano **Valore di acquisto**: un clic nasconde entrambe, e anche l'area omonima in **Assoluto**.
- **Tassi di cambio mancanti.** Un importo che non può essere convertito alla sua data viene escluso, non conteggiato come zero; il [banner di qualità dei dati](index.md#data-quality-banner) lo segnala.

!!! warning "Le barre degli acquisti non sono il KPI Valore di acquisto"

    Le barre sono un **flusso**: quanto hai speso per gli acquisti in ciascun periodo. La riga **Valore di acquisto** della [scheda Patrimonio netto](kpi-cards.md#card-3-net-worth) è un **livello**: quanto ti sono costate le posizioni che detieni ancora alla data finale. Le vendite e gli acquisti precedenti contano nel KPI ma non hanno una barra.

#### Larghezza delle candele — da 1D a 1Y {: #pnl-width }

In **Candele** e **Entrate**, i pulsanti nell'angolo in alto a destra dell'area del grafico, da **1D** a **1Y**, impostano quanto tempo copre una candela, o un gruppo di barre. Il grafico mostra comunque l'intero intervallo e lo zoom non cambia mai la larghezza.

- **Periodi di calendario.** **1W** va da lunedì a domenica, **1M** è un mese di calendario, **3M** un trimestre, **6M** un semestre, **1Y** un anno; **3D** e **2W** sono blocchi fissi di giorni.
- **Etichette dell'asse.** Ogni etichetta indica l'inizio del suo periodo, anche quando l'intervallo lo copre solo in parte; mesi e anni compaiono solo dove cambiano, e le etichette affollate si inclinano o si diradano.
- Vengono offerte **solo le larghezze che si adattano** al grafico e all'intervallo; **Entrate** parte da **1W**.
- **Da dove parte.** **Candele** adotta la larghezza più fine disponibile; **Entrate** si apre su **1M**, o sulla larghezza disponibile più vicina, ogni volta che vi entri. Ricaricare la pagina reimposta la larghezza.
- **I periodi parziali sono sbiaditi.** Un periodo in cui l'intervallo inizia a metà, o un ultimo periodo tagliato da un intervallo che termina nel passato, viene disegnato sbiadito, e il suo tooltip dice *Parziale: N di M giorni*. Altrimenti, il periodo in corso viene disegnato intero, con *In corso: N di M giorni*.

---

## 🥧 Pannello Allocazione {: #allocation-panel }

Il pannello **Allocazione degli asset** mostra come è suddiviso il tuo portafoglio, oggi e nel tempo. Scegli una dimensione con le schede **Per tipo**, **Per settore**, **Geografica** e **Per asset**, e una visualizzazione con i due pulsanti nell'angolo in alto a destra: il grafico a torta per **Ora**, il grafico ad area per **Storico**.

<div class="lf-screenshot-carousel" data-carousel="carousel-alloc" data-carousel-interval="5000" data-show-titles="true" style="margin: 1.5rem 0 2.5rem 0;">
  <div class="lf-screenshot-carousel-item is-active alloc-crop-container" data-title="Per tipo (attuale)" alt="Allocazione per tipo — attuale">
     <img class="gallery-img" data-category="dashboard" data-name="allocation-type-now" alt="Allocazione per tipo — attuale">
  </div>
  <div class="lf-screenshot-carousel-item alloc-crop-container" data-title="Per settore (attuale)" alt="Allocazione per settore — attuale">
     <img class="gallery-img" data-category="dashboard" data-name="allocation-sector-now" alt="Allocazione per settore — attuale">
  </div>
  <div class="lf-screenshot-carousel-item alloc-crop-container" data-title="Per geografia (attuale)" alt="Allocazione per geografia — attuale">
     <img class="gallery-img" data-category="dashboard" data-name="allocation-geo-now" alt="Allocazione per geografia — attuale">
  </div>
  <div class="lf-screenshot-carousel-item alloc-crop-container" data-title="Per tipo (storico)" alt="Storico dell'allocazione per tipo">
     <img class="gallery-img" data-category="dashboard" data-name="allocation-type-history" alt="Storico dell'allocazione per tipo">
  </div>
  <div class="lf-screenshot-carousel-item alloc-crop-container" data-title="Per settore (storico)" alt="Storico dell'allocazione per settore">
     <img class="gallery-img" data-category="dashboard" data-name="allocation-sector-history" alt="Storico dell'allocazione per settore">
  </div>
  <div class="lf-screenshot-carousel-item alloc-crop-container" data-title="Per geografia (storico)" alt="Storico dell'allocazione per geografia">
     <img class="gallery-img" data-category="dashboard" data-name="allocation-geo-history" alt="Storico dell'allocazione per geografia">
  </div>
</div>

### 🗂️ Tre dimensioni

| Scheda | Cosa mostra |
|-----|--------------|
| **Per tipo** | Cos'è ciascuna posizione — il suo [tipo di asset](../../financial-theory/instruments/asset-types/index.md), come Azione, ETF, Obbligazione, Fondo o Cripto — più **Liquidità** per la tua liquidità. I sottotipi contano con la loro [famiglia](../../financial-theory/instruments/asset-types/index.md#families-and-subtypes), come un **ETF azionario** insieme agli altri tuoi ETF. |
| **Per settore** | Settore industriale: 💻 Tecnologia, 🏦 Finanziario, 💊 Sanità, ecc. |
| **Geografica** | Dove sono investiti i tuoi asset, paese per paese, in base alla distribuzione geografica di ciascun asset |
| **Per asset** | Quanto pesa ogni singolo asset: una fetta per asset, con **Liquidità** per la tua liquidità. Vedi [Per asset](#allocation-by-asset). |

### 🕰️ Ora e Storico

- **Ora** — l'allocazione nell'ultimo giorno dell'intervallo selezionato: un grafico ad anello per **Per tipo** e **Per settore**, una mappa mondiale per **Geografica**. Passa sopra una fetta o un paese per vedere percentuale e importo. Per tipo, il grafico ad anello può avere [due anelli](#allocation-type-rings).
- **Storico** — un grafico ad area in pila al 100% di come l'allocazione è cambiata nel tempo, utile per vedere il ribilanciamento. Per tipo, ogni famiglia è un'area; passando sopra una data vengono elencati i suoi sottotipi, come *ETF generico* e *ETF azionario*.

Il pannello ricorda la visualizzazione e la scheda in questo browser, per ciascun utente, e le condivide con le pagine dei broker.

### 🧩 Per asset {: #allocation-by-asset }

Quali singoli asset pesano di più? **Per asset** suddivide il portafoglio asset per asset anziché per categoria.

- **Ora** — un grafico a torta con il peso di ogni asset nell'ultimo giorno dell'intervallo selezionato. Ogni spicchio mostra l'icona del suo asset — la sua, o quella del tipo se non ne ha una o non si carica; la liquidità mostra quella di Liquidità. Non c'è legenda: passa sopra uno spicchio per leggere nome, quota e importo.
- **Storico** — come è cambiata nel tempo la distribuzione per asset. **Le posizioni chiuse sono incluse**, quindi un asset che hai venduto compare ancora nei giorni in cui lo detenevi.
- **I colori** seguono il peso di oggi: l'asset più pesante riceve il primo colore, poi gli altri per peso, quindi gli asset chiusi, quelli chiusi più di recente per primi. Il grafico a torta, lo storico e le linee di [Rendimento delle posizioni](positions.md#return-of-the-positions) usano lo stesso colore per lo stesso asset.

### 🍩 Due anelli per tipo {: #allocation-type-rings }

Non appena detieni un asset con un sottotipo, come un **ETF azionario** o il **Crowdfunding immobiliare**, il grafico ad anello **Ora** di **Per tipo** disegna due anelli:

- **Anello interno** — una fetta per famiglia, con la sua icona dove c'è spazio: tutti i tuoi ETF (l'**ETF** generico e ogni sottotipo) insieme, **Crowdfunding** con **Crowdfunding immobiliare**, e ogni altro tipo, **Liquidità** inclusa, da solo. Queste sono le famiglie che il [menu Tipo](../assets/create-edit.md#choosing-the-asset-type) dell'asset raggruppa insieme.
- **Anello esterno** — più sottile e distanziato, suddivide ogni famiglia che contiene un sottotipo nei suoi membri, in tonalità del colore della famiglia, con didascalia dove c'è spazio. Il membro generico si chiama *ETF generico* o *Crowdfunding generico*.
- **Passa sopra** una fetta per vederne quota e importo; sull'anello esterno, un'ultima riga che inizia con **↳** indica la quota dell'intera famiglia.
- **La legenda** elenca solo le famiglie: facendo clic su una si nascondono le sue fette su entrambi gli anelli.

Senza alcun sottotipo, il grafico ad anello mantiene un solo anello.

### 💵 La liquidità come voce Liquidità

La tua liquidità è la fetta **Liquidità** di **Per tipo**, **Per settore** e **Per asset**; la mappa **Geografica** la esclude, poiché la liquidità non appartiene a nessun paese. Con il filtro broker attivo, il pannello mostra solo gli asset e la liquidità dei broker selezionati.

### ➖ Liquidità negativa {: #allocation-negative-cash }

La percentuale di ogni fetta è il suo importo diviso per la somma di tutte le fette, liquidità inclusa, quindi una liquidità negativa cambia le quote:

- **Liquidità sotto zero, asset sopra zero** — ad esempio 1.500 € di azioni con liquidità a −500 € su uno scoperto: le fette sommano 1.000 €, quindi **Liquidità** indica −50% e le azioni 150%. Le percentuali si sommano comunque a 100%.
- **Niente da ripartire** — quando le fette sommano zero o meno, nessuna fetta ha una percentuale: 500 € di azioni acquistate con uno scoperto di −500 €, oppure un portafoglio che hai svuotato, la cui unica fetta è **Liquidità** a zero. Ogni fetta mostra `—` anziché una percentuale e conserva il suo importo, e il grafico non ha nulla da disegnare e lo dichiara. Nello **Storico**, anche un giorno in cui le fette sommano zero o meno non ha percentuali.
- **Un residuo minuscolo** di 0,00001 unità o meno, che una vendita di quasi tutte le unità può lasciare, non è una posizione: non ha una fetta.

---

## 🔗 Correlati

- 💰 **[Schede KPI](kpi-cards.md)** — Patrimonio netto, P&L periodo, Rendimenti
- 💼 **[NAV / Patrimonio netto](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/nav.md)**
- 💸 **[Capitale versato e P&L totale](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/deposited-capital.md)**
- 📈 **[TWRR](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/twrr.md)** · **[MWRR](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/mwrr.md)** · **[Effetto timing](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/timing-effect.md)**
- 🛠️ **[Funzionamento interno dei grafici](../../developer/frontend/components/charts.md)** — per sviluppatori: come sono costruiti questi grafici

---

*[⬅️ Torna alla Panoramica della dashboard](index.md)*
