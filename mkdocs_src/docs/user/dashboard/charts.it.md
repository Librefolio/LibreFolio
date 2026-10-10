# 📊 Grafici

Sotto le schede KPI, il grafico **Crescita del portafoglio** e il pannello **Allocazione asset** mostrano dove è stato il tuo portafoglio e di cosa è composto. Entrambi seguono l'intervallo temporale e il filtro broker della Dashboard, e la pagina di un broker li mostra per quel solo broker.

---

## 📈 Grafico della crescita del portafoglio {: #portfolio-growth-chart }

Il grafico di crescita mostra come è evoluto il tuo portafoglio nel periodo selezionato: l'interruttore **Abs / % / P&L** nell'angolo in alto a destra permette di passare tra valori assoluti, tassi di rendimento e il denaro effettivamente guadagnato.

Il grafico ricorda la tua ultima vista, inclusa la sotto-vista P&L, in questo browser e per ciascun utente, e la condivide con le pagine dei broker. Parte su **Abs**. Senza dati sui tassi di rendimento, **%** è in grigio e disattivata e il grafico mostra **Abs**; la tua scelta viene ripristinata la prossima volta che apri il grafico con dati da disegnare.

<div class="lf-screenshot-carousel" data-carousel="carousel-growth" data-carousel-interval="5000" data-show-titles="true" style="margin: 1.5rem 0 2.5rem 0;">
  <div class="lf-screenshot-carousel-item is-active chart-crop-container" data-title="📈 Modalità assoluta" alt="Grafico della crescita — Modalità assoluta">
     <img class="gallery-img" data-category="dashboard" data-name="main" alt="Grafico della crescita — Modalità assoluta">
  </div>
  <div class="lf-screenshot-carousel-item chart-crop-container" data-title="📈 Modalità percentuale" alt="Grafico della crescita — Modalità percentuale">
     <img class="gallery-img" data-category="dashboard" data-name="main-pct" alt="Grafico della crescita — Modalità percentuale">
  </div>
</div>

**Nascondi importi** (il pulsante a forma di occhio nella barra superiore) trasforma ogni importo sull'asse e nei tooltip in `•••`; segni, valute, linee e colori rimangono. Vedi [Modalità privacy](../settings/preferences.md#privacy-mode).

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="dashboard" data-name="privacy-masked" alt="La Dashboard con Nascondi importi attivo: il pulsante a forma di occhio barrato nell'intestazione, gli importi delle schede KPI e dei Saldi di cassa mostrati come ••• con il loro segno e la loro valuta, le percentuali ancora leggibili e l'asse della Crescita del portafoglio mascherato" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

### 💶 Abs — valori assoluti

| Elemento | Colore | Significato |
|---------|-------|---------|
| Area — **Valore di acquisto** | Blu | Quanto ti sono costate le posizioni che detieni (costo medio × quantità) |
| Area — **Returns** | Smeraldo | Rendimenti detenuti come liquidità (dividendi, interessi, plusvalenze realizzate non ancora reinvestite) |
| Area — **Capital** | Grigio-verde | Depositi non ancora investiti, detenuti come liquidità |
| Linea — **[Valore netto](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/nav.md)** | Verde scuro pieno | Valore totale del portafoglio ai prezzi di mercato correnti |
| Linea — **[Capitale versato](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/deposited-capital.md)** | Grigio tratteggiato | Capitale esterno netto conferito nel tempo |

**Il divario tra le due linee è il tuo Total P&L**: ogni guadagno mai ottenuto (non realizzato, realizzato, interessi e dividendi) meno commissioni e imposte. Il tooltip mostra entrambe le linee, il Total P&L in verde o rosso e la ripartizione: **Assets at Cost** (l'area blu, inclusi gli asset che si spostano tra i tuoi broker), **Returns** e **Capital**.

**Gli asset valutati al loro prezzo di acquisto**, come i prestiti P2P senza un prezzo live, mantengono il NAV vicino al Valore di acquisto, quindi il divario può essere sottile: leggi il **Total P&L** nel tooltip.

🔗 **Teoria**: [Capitale versato & Total P&L](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/deposited-capital.md) · [Cash Decomposition](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/deposited-capital.md#three-pool-cash-model)

### 📉 % — tasso di rendimento

Ogni linea è il rendimento accumulato dall'inizio del periodo selezionato:

| Serie | Cosa mostra |
|--------|--------------|
| **[MWRR cumulative](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/mwrr.md)** | Il tuo rendimento personale ponderato per il denaro, inclusa la tempistica dei depositi |
| **[TWRR](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/twrr.md)** | Rendimento puro della strategia degli asset, ignorando quando hai depositato |
| **[ROI](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/roi.md)** | Rendimento grezzo sul capitale netto investito |

Il divario tra MWRR e TWRR è l'[effetto timing](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/timing-effect.md). Se il [banner di qualità dei dati](index.md#data-quality-banner) indica **MWRR chart unavailable**, la linea MWRR è nascosta; TWRR e ROI rimangono.

### 💰 P&L — il denaro che hai guadagnato {: #pnl-mode }

**P&L** traccia il tuo **Total P&L** (NAV meno capitale versato): quanto denaro ha effettivamente guadagnato il portafoglio dall'inizio. Lo zoom non fa ripartire il conteggio da zero.

Un secondo interruttore, in alto a sinistra nel grafico, sceglie come disegnarlo (solo icone su un grafico stretto):

| Vista | Cosa disegna | La domanda a cui risponde |
|------|---------------|------------------------|
| **Linea** | P&L accumulato come singola linea | Come si è mosso il mio risultato nel tempo? |
| **Candele** | Una candela per periodo, da un giorno a un anno | Quanto è stata ampia l'oscillazione all'interno di ogni periodo? |
| **Entrate** | Barre della liquidità che si è effettivamente mossa | Da dove è arrivato il denaro e quanto mi è costato? |

#### Linea — P&L accumulato {: #pnl-line }

- La linea è **verde sopra lo zero e rossa sotto**.
- Una **linea grigia tratteggiata** segna il P&L del primo giorno in vista: il divario rispetto ad essa è ciò che hai guadagnato o perso dal bordo sinistro.

<div class="lf-screenshot-carousel" style="margin: 1.5rem 0 2.5rem 0;">
  <div class="lf-screenshot-carousel-item is-active chart-crop-container" alt="Il grafico della crescita del portafoglio in modalità P&L, vista Linea: la linea Total P&L in verde, la linea grigia tratteggiata al P&L del primo giorno in vista e una linea tratteggiata per ciascun broker">
     <img class="gallery-img" data-category="dashboard" data-name="growth-pnl-line" alt="Il grafico della crescita del portafoglio in modalità P&L, vista Linea: la linea Total P&L in verde, la linea grigia tratteggiata al P&L del primo giorno in vista e una linea tratteggiata per ciascun broker">
  </div>
</div>

**Linee per broker.** Con due o più broker nell'ambito, ciascun broker ottiene una linea tratteggiata e una riga nel tooltip con la sua quota del totale; le quote sommano al totale ogni giorno. Una quota non è la performance del broker stesso: il denaro in transito conta per il broker da cui è partito, quindi la linea di un broker può saltare in una data di trasferimento. Con un solo broker, o sulla pagina di un broker, viene disegnato solo il totale.

#### Candele — l'oscillazione all'interno del periodo {: #pnl-candles }

Ogni periodo della [larghezza che scegli](#pnl-width) diventa una **candela** fatta di valori di P&L, non di prezzi. La sua **chiusura** è esattamente il Total P&L che la vista **Linea** mostra per quel giorno.

<div class="lf-screenshot-carousel" style="margin: 1.5rem 0 2.5rem 0;">
  <div class="lf-screenshot-carousel-item is-active chart-crop-container" alt="Il grafico della crescita del portafoglio in modalità P&L, vista Candele a 3D: le candele sintetiche di P&L, i pulsanti di larghezza da 3D a 6M nell'angolo in alto a destra del grafico, le etichette dei periodi sull'asse e la dicitura Synthetic sotto il grafico">
     <img class="gallery-img" data-category="dashboard" data-name="growth-pnl-candles" alt="Il grafico della crescita del portafoglio in modalità P&L, vista Candele a 3D: le candele sintetiche di P&L, i pulsanti di larghezza da 3D a 6M nell'angolo in alto a destra del grafico, le etichette dei periodi sull'asse e la dicitura Synthetic sotto il grafico">
  </div>
</div>

!!! warning "I massimi e i minimi sono ipotetici"

    Il massimo e il minimo di una candela sommano il massimo e il minimo giornaliero di ciascun asset, che non sono stati raggiunti nello stesso momento: quello stato del portafoglio potrebbe non essere mai esistito, come dice la dicitura sotto il grafico (*Synthetic — cross-asset high/low are hypothetical and non-simultaneous*). Leggili come quanto il portafoglio *avrebbe potuto* oscillare.

Aspettati anche:

- **Nessun volume** — il P&L di un portafoglio non ha volume scambiato.
- **Corpi sottili, ombre lunghe** — apertura e chiusura sono di solito vicine mentre l'intervallo sommato è ampio.
- **Lacune** — un giorno in cui un asset detenuto non poteva essere valutato non ha candela, invece di una stimata.

Il tooltip fornisce il periodo, **Open**, **Close**, **High** e **Low**, più una riga per broker quando due o più sono nell'ambito.

#### Entrate — la liquidità che si è effettivamente mossa {: #pnl-income }

**Entrate** mette da parte le valutazioni e traccia i tuoi flussi di cassa reali. Ogni barra è la **somma** dei flussi del suo periodo, in massimo tre colonne:

| Colonna | Barre | Cosa rappresenta |
|--------|------|--------------------|
| Entrate e costi | **Dividendo** · **Interesse** sopra lo zero, **Commissioni e imposte** sotto lo zero | Ciò che il portafoglio ti ha pagato e ciò che l'attività ti è costata |
| Depositi | **Deposito** | Denaro fresco che hai versato (i prelievi non vengono disegnati) |
| Acquisti | **Valore di acquisto**, in due zone: **Nuovo capitale** in basso, **Reinvestito** sopra | Ciò che hai speso per gli acquisti, suddiviso per provenienza del denaro |

<div class="lf-screenshot-carousel" style="margin: 1.5rem 0 2.5rem 0;">
  <div class="lf-screenshot-carousel-item is-active chart-crop-container" alt="Il grafico della crescita del portafoglio in modalità P&L, vista Entrate a 1M: gruppi mensili di barre per Interesse, Commissioni e imposte sotto lo zero, Deposito e Valore di acquisto">
     <img class="gallery-img" data-category="dashboard" data-name="growth-pnl-income" alt="Il grafico della crescita del portafoglio in modalità P&L, vista Entrate a 1M: gruppi mensili di barre per Interesse, Commissioni e imposte sotto lo zero, Deposito e Valore di acquisto">
  </div>
</div>

Come leggerlo:

- **Nuovo capitale o reinvestito.** Un acquisto utilizza prima i rendimenti già detenuti come liquidità presso quel broker (**Reinvestito**, verde come in **Abs**); il resto è **Nuovo capitale** (blu). Le vendite non vengono mai disegnate.
- **I segni sono mantenuti.** Una correzione negativa su un dividendo passato riduce la barra dei dividendi; commissioni e imposte rimangono sotto lo zero.
- **Corrisponde ai KPI.** Per le stesse date e gli stessi broker, **Dividendo** e **Interesse** corrispondono esattamente alla riga **Dividendi e interessi** della [scheda P&L periodo](kpi-cards.md#card-1-period-pl).
- **Una sola voce in legenda.** Entrambe le zone di acquisto si chiamano **Valore di acquisto**: un clic nasconde entrambe, e anche l'area **Abs** con lo stesso nome.
- **Tassi di cambio mancanti.** Un importo che non può essere convertito alla sua data viene escluso, non contato come zero; il [banner di qualità dei dati](index.md#data-quality-banner) lo segnala.

!!! warning "Le barre degli acquisti non sono il KPI Valore di acquisto"

    Le barre sono un **flusso**: ciò che hai speso per gli acquisti in ciascun periodo. La riga **Valore di acquisto** della [scheda Patrimonio netto](kpi-cards.md#card-3-net-worth) è un **livello**: quanto ti sono costate le posizioni che detieni ancora alla data finale. Le vendite e gli acquisti precedenti contano nel KPI ma non hanno una barra.

#### Larghezza delle candele — da 1D a 1Y {: #pnl-width }

In **Candele** e **Entrate**, i pulsanti nell'angolo in alto a destra del grafico, da **1D** a **1Y**, impostano quanto tempo copre una candela, o un gruppo di barre. Il grafico mostra comunque l'intero intervallo, e lo zoom non cambia mai la larghezza.

- **Periodi di calendario.** **1W** va da lunedì a domenica, **1M** è un mese di calendario, **3M** un trimestre, **6M** un semestre, **1Y** un anno; **3D** e **2W** sono blocchi fissi di giorni.
- **Etichette dell'asse.** Ogni etichetta indica l'inizio del suo periodo, anche se l'intervallo lo copre solo in parte; mesi e anni compaiono solo dove cambiano, e le etichette affollate si inclinano o si diradano.
- **Vengono offerte solo le larghezze** che si adattano al grafico e all'intervallo; **Entrate** parte da **1W**.
- **Da dove inizia.** **Candele** prende la larghezza più fine disponibile; **Entrate** si apre su **1M**, o sulla larghezza più vicina disponibile, ogni volta che vi entri. Ricaricare la pagina reimposta la larghezza.
- **I periodi parziali sono attenuati.** Un periodo in cui l'intervallo inizia a metà, o un ultimo periodo tagliato corto da un intervallo che termina nel passato, viene disegnato attenuato, e il suo tooltip dice *Partial: N of M days*. Altrimenti, il periodo in corso viene disegnato per intero, con *In progress: N of M days*.

---

## 🥧 Pannello Allocazione {: #allocation-panel }

Il pannello **Allocazione asset** mostra come è suddiviso il tuo portafoglio, oggi e nel tempo. Scegli una dimensione con le schede **By Type**, **By Sector** e **Geographic**, e una vista con i due pulsanti nell'angolo in alto a destra: il grafico a torta per **Now**, il grafico ad area per **History**.

<div class="lf-screenshot-carousel" data-carousel="carousel-alloc" data-carousel-interval="5000" data-show-titles="true" style="margin: 1.5rem 0 2.5rem 0;">
  <div class="lf-screenshot-carousel-item is-active alloc-crop-container" data-title="Per tipo (attuale)" alt="Allocazione per tipo — Attuale">
     <img class="gallery-img" data-category="dashboard" data-name="allocation-type-now" alt="Allocazione per tipo — Attuale">
  </div>
  <div class="lf-screenshot-carousel-item alloc-crop-container" data-title="Per settore (attuale)" alt="Allocazione per settore — Attuale">
     <img class="gallery-img" data-category="dashboard" data-name="allocation-sector-now" alt="Allocazione per settore — Attuale">
  </div>
  <div class="lf-screenshot-carousel-item alloc-crop-container" data-title="Per area geografica (attuale)" alt="Allocazione per area geografica — Attuale">
     <img class="gallery-img" data-category="dashboard" data-name="allocation-geo-now" alt="Allocazione per area geografica — Attuale">
  </div>
  <div class="lf-screenshot-carousel-item alloc-crop-container" data-title="Per tipo (storico)" alt="Storico dell'allocazione per tipo">
     <img class="gallery-img" data-category="dashboard" data-name="allocation-type-history" alt="Storico dell'allocazione per tipo">
  </div>
  <div class="lf-screenshot-carousel-item alloc-crop-container" data-title="Per settore (storico)" alt="Storico dell'allocazione per settore">
     <img class="gallery-img" data-category="dashboard" data-name="allocation-sector-history" alt="Storico dell'allocazione per settore">
  </div>
  <div class="lf-screenshot-carousel-item alloc-crop-container" data-title="Per area geografica (storico)" alt="Storico dell'allocazione per area geografica">
     <img class="gallery-img" data-category="dashboard" data-name="allocation-geo-history" alt="Storico dell'allocazione per area geografica">
  </div>
</div>

### 🗂️ Tre dimensioni

| Scheda | Cosa mostra |
|-----|--------------|
| **By Type** | Cos'è ciascuna posizione — il suo [asset type](../../financial-theory/instruments/asset-types/index.md), come Stock, ETF, Bond, Fund o Crypto — più **Liquidity** per la tua liquidità. I sottotipi contano con la loro [famiglia](../../financial-theory/instruments/asset-types/index.md#families-and-subtypes), ad esempio un **Equity ETF** con gli altri tuoi ETF. |
| **By Sector** | Settore industriale: 💻 Technology, 🏦 Financials, 💊 Health Care, ecc. |
| **Geographic** | Dove sono investiti i tuoi asset, paese per paese, secondo la distribuzione geografica di ciascun asset |

### 🕰️ Now e History

- **Now** — l'allocazione nell'ultimo giorno dell'intervallo selezionato: un grafico ad anello per **By Type** e **By Sector**, una mappa del mondo per **Geographic**. Passa il mouse su una fetta o un paese per la sua percentuale e il suo importo. Per tipo, il grafico ad anello può avere [due anelli](#allocation-type-rings).
- **History** — un grafico ad area impilata al 100% di come è cambiata l'allocazione nel tempo, utile per vedere il ribilanciamento. Per tipo, ogni famiglia è un'area; passando il mouse su una data si elencano i suoi sottotipi, come *Generic ETF* e *Equity ETF*.

Il pannello ricorda la vista e la scheda in questo browser, per ciascun utente, e le condivide con le pagine dei broker.

### 🍩 Due anelli per tipo {: #allocation-type-rings }

Non appena detieni un asset con un sottotipo, come un **Equity ETF** o **Real estate crowdfunding**, il grafico ad anello della vista **Now** di **By Type** disegna due anelli:

- **Anello interno** — una fetta per famiglia, con la sua icona dove c'è spazio: tutti i tuoi ETF (l'**ETF** generico e ogni sottotipo) insieme, **Crowdfund** con **Real estate crowdfunding**, e ogni altro tipo, **Liquidity** inclusa, per conto proprio. Queste sono le famiglie che il [menu Type](../assets/create-edit.md#choosing-the-asset-type) dell'asset raggruppa.
- **Anello esterno** — più sottile e distanziato, divide ciascuna famiglia che contiene un sottotipo nei suoi membri, in sfumature del colore della famiglia, con didascalia dove c'è spazio. Il membro generico si legge *Generic ETF* o *Generic Crowdfund*.
- **Passa il mouse** su una fetta per la sua quota e il suo importo; sull'anello esterno, un'ultima riga che inizia con **↳** indica la quota dell'intera famiglia.
- **La legenda** elenca solo le famiglie: cliccandone una si nascondono le sue fette su entrambi gli anelli.

Senza alcun sottotipo, il grafico ad anello resta a un solo anello.

### 💵 La liquidità come Liquidity

La tua liquidità è la fetta **Liquidity** di **By Type** e **By Sector**; la mappa **Geographic** la esclude, poiché la liquidità non appartiene a nessun paese. Con il filtro broker attivo, il pannello mostra solo gli asset e la liquidità dei broker selezionati.

---

## 🔗 Correlati

- 💰 **[Schede KPI](kpi-cards.md)** — Patrimonio netto, P&L periodo, Rendimenti
- 💼 **[NAV / Patrimonio netto](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/nav.md)**
- 💸 **[Capitale versato & Total P&L](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/deposited-capital.md)**
- 📈 **[TWRR](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/twrr.md)** · **[MWRR](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/mwrr.md)** · **[Effetto timing](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/timing-effect.md)**
- 🛠️ **[Chart internals](../../developer/frontend/components/charts.md)** — per gli sviluppatori: come sono costruiti questi grafici

---

*[⬅️ Torna alla Panoramica della Dashboard](index.md)*
