# 🏦 Broker

Un **broker** è uno dei tuoi conti — presso una società di intermediazione, una banca o un exchange: il luogo in cui vivono i tuoi investimenti e la tua liquidità. Ogni transazione e ogni report caricato appartiene a un broker, quindi ne serve almeno uno prima di iniziare.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="brokers" data-name="list" alt="Elenco broker" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

La pagina **Broker** mostra una scheda per ogni broker, con il suo valore (**NAV**) nella valuta scelta in **Valuta** in cima alla pagina. Clicca una scheda per aprire il broker.

Il **Guadagno/Perdita** è il NAV meno il capitale versato nel broker: i tuoi depositi meno i prelievi, più il costo dei titoli conferiti in natura, senza contanti, più quanto è affluito dagli altri tuoi broker meno quanto hai trasferito fuori, con ogni movimento valorizzato al giorno in cui è arrivato. Quindi spostare denaro o titoli tra due tuoi broker non è un guadagno su una scheda e una perdita sull'altra, e mentre un trasferimento è in transito, il suo valore resta sulla scheda del broker mittente. La liquidità detenuta in un'altra valuta è valorizzata al tasso di cambio più recente, quindi l'effetto del cambio su di essa conta nel Guadagno/Perdita, non nel capitale. La percentuale tra parentesi è il guadagno su quel capitale: mostra 0,00% quando quel capitale è zero o inferiore, per esempio quando il broker ha inviato più di quanto ha ricevuto. → [Trasferimenti interni](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/deposited-capital.md#internal-transfers-broker-lines)

!!! note "I broker condivisi mostrano la tua quota sulla scheda"

    Su un broker che possiedi in comproprietà, i valori della sua scheda sono **proporzionati alla tua quota di proprietà**: un Proprietario al 50% vede metà del conto. Editor e Visualizzatori vedono gli importi completi. La pagina del broker mostra a tutti l'intero conto — vedi [La pagina del broker è la Dashboard su un singolo broker](#broker-page-is-dashboard). Vedi [Condivisione del broker](sharing.md).

---

## ➕ Creare un broker

1. Apri **Broker** dalla barra laterale e clicca **Aggiungi broker**.
2. Digita un **Nome** — l'unico campo obbligatorio — e imposta le opzioni che ti servono.
    <div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
        <img class="gallery-img" data-category="brokers" data-name="edit-modal" alt="Modulo di modifica del broker" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
    </div>

3. Clicca **Crea**: il broker compare nel tuo elenco, pronto per transazioni e report.

??? info "⚙️ I campi facoltativi — cosa fa ciascuno"

    - **Descrizione** — le tue note personali.
    - **Plugin di importazione predefinito** — l'importatore che la [Procedura guidata di importazione](../transactions/import/index.md) propone per i file di questo broker.
    - **URL del portale** — il sito web del broker, aperto dalla pagina del broker. L'icona del broker è, in quest'ordine: il tuo **URL icona personalizzata**; l'icona del **Plugin di importazione predefinito**, quando quell'importatore è realizzato per questo broker; l'icona del sito web; l'icona di un importatore generico come il CSV generico; altrimenti una valigetta.
    - **Conto aperto** e **Conto attivo** — quando il conto è stato aperto e se è ancora aperto. Un broker chiuso appare attenuato nell'elenco.
    - **Opzioni di trading** — **Consenti acquisti con leva** e **Consenti vendite allo scoperto**, spiegate in [Opzioni di trading](info.md#trading-options).
    - **Saldi iniziali** (solo in fase di creazione) — la tua liquidità di partenza. LibreFolio registra un **Deposito** per valuta, **datato oggi**: se il denaro era già presente prima, cambia la data di quei depositi nella pagina [Transazioni](../transactions/index.md).

??? warning "🏷️ «Un broker chiamato … esiste già» — quando compare"

    I nomi dei broker sono univoci sull'intero server, tra tutti i suoi utenti. Scegli un nome diverso, oppure rinomina il broker esistente se è tuo.

    I broker di altri utenti che non puoi aprire sono elencati sotto **Altri broker esistenti**. Il relativo pulsante di condivisione mostra chi ha accesso, così sai a chi chiedere: ogni utente autenticato di questo LibreFolio può vederlo, per qualsiasi broker.

---

## ✏️ Modificare o eliminare un broker

- **Modifica** — la matita sulla scheda del broker, oppure **Modifica** nella barra degli strumenti del broker. Proprietari ed Editor possono modificare un broker.
- **Elimina** — il cestino sulla scheda del broker. Solo un Proprietario può eliminare un broker. Se contiene ancora transazioni, LibreFolio indica quante sono e offre **Vai alle transazioni** oppure **Elimina broker e transazioni**, che le elimina anch'esse. Gli asset che ha trasferito a un altro broker, incluso uno condiviso, restano lì come posizione di apertura al loro costo di trasferimento, a partire dalla data del trasferimento: il guadagno di quel broker include quindi anche quanto hanno guadagnato prima del trasferimento. Gli asset che un altro broker gli ha trasferito vengono rimossi da quel broker come una rettifica che toglie le unità: la rettifica non ha valore, quindi le unità diminuiscono solo nella quantità e il loro costo conta come perdita realizzata lì ([Rettifiche in uscita](../../financial-theory/instruments/transaction-types/adjustment.md#outgoing-adjustments)). I giroconti con un altro broker diventano, presso quel broker, un deposito o un prelievo.

---

## 🗂️ All'interno di un broker

La scheda di un broker apre la sua pagina sulla scheda **Panoramica**:

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="brokers" data-name="detail" alt="Dettaglio del broker" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

In alto, l'intestazione mostra il nome del broker, la sua icona e, come badge, il tuo ruolo e la tua quota di proprietà. La barra degli strumenti sottostante si applica a ogni scheda:

- l'**intervallo di date** e la **Valuta** delle cifre, con lo stesso elenco della Dashboard, **Crea forex** incluso;
- **Modifica** (Proprietari ed Editor) e **Condividi broker**, che apre la scheda **Info**;
- **AI Export**, che copia negli appunti un prompt già pronto relativo a questo broker — vedi [AI Export del broker](../ai-export/broker.md);
- **Aggiorna**, che ricalcola la pagina su richiesta.

Sotto, cinque schede:

1. **Panoramica** — come sta andando il conto (sotto).
2. **Posizioni** — cosa detieni presso questo broker (sotto).
3. **Rischio** — l'analisi del rischio della Dashboard, limitata a questo broker (vedi [Scheda Rischio della Dashboard](../dashboard/index.md#risk-tab)).
4. **Transazioni** — il registro del broker, gli inserimenti manuali, le importazioni e i report caricati (vedi [Transazioni del broker](import.md)).
5. **Info** — dettagli del conto, opzioni di trading e condivisione (vedi [Configurazione e info](info.md)).

---

## 🧭 La pagina del broker è la Dashboard su un singolo broker {: #broker-page-is-dashboard }

La pagina di un broker è la [Dashboard](../dashboard/index.md) con quel broker già selezionato, più la scheda **Info** del broker stesso. I controlli, le schede e i relativi pannelli funzionano come descritto nelle pagine della Dashboard; non c'è alcun filtro per broker, perché la pagina riguarda un singolo broker.

Cosa resta uguale rispetto alla Dashboard:

- **Periodo, valuta e pulsanti.** L'intervallo di date, il menu **Valuta**, **AI Export** e **Aggiorna** sono quelli della Dashboard. Quando non usi la pagina da due minuti, il pulsante **Aggiorna** mostra l'icona della pausa e un colore più spento, e il suo suggerimento dice che gli aggiornamenti sono in pausa: cliccalo per aggiornare di nuovo i prezzi (vedi **Prezzi live** nella pagina [Asset](../assets/index.md)).
- **I saldi di cassa seguono il periodo.** Mostrano la liquidità alla fine del periodo scelto.
- **Lotti.** **Analizza lotti** apre il dettaglio dei lotti sotto l'elenco; il pulsante **Indietro** del browser lo chiude. **Vedi tutto →** apre la pagina Asset sullo stesso periodo.
- **Banner di qualità dei dati.** Anche qui vengono segnalati prezzi obsoleti e tassi di cambio mancanti o obsoleti, con gli stessi pulsanti **Sincronizza prezzi** e **Sincronizza tassi** ([Banner di qualità dei dati](../dashboard/index.md#data-quality-banner)). Tutti i ruoli li vedono, Visualizzatore incluso: aggiornano prezzi e tassi di cambio condivisi, non il broker.

Cosa cambia:

- **L'intero broker.** Ogni importo nella pagina, Rischio incluso, è l'importo **intero** del broker (100%), anche quando ne possiedi meno del 100%. Il badge nell'intestazione mostra il tuo ruolo e la tua quota. La Dashboard filtrata sullo stesso broker mostra la tua quota.
- **Le transazioni seguono il periodo.** La scheda Transazioni elenca le transazioni dell'intervallo di date scelto nella barra degli strumenti, e **Visualizza nelle transazioni** apre la pagina [Transazioni](../transactions/index.md) con lo stesso periodo. **Importa**, **Aggiungi transazione**, **Modifica**, **Clona**, **Elimina** e la barra di selezione sono per Proprietari ed Editor; un Visualizzatore vede la tabella, la cronologia delle importazioni e **Visualizza nelle transazioni**.

---

## 📈 Scheda Panoramica

La **Panoramica** risponde a «come sta andando questo conto?» con gli stessi blocchi della [Panoramica della Dashboard](../dashboard/index.md), limitati a questo broker:

- **Schede KPI** — **P&L periodo**, **Rendimenti** e **Patrimonio netto** ([Schede KPI](../dashboard/kpi-cards.md)).
- **Saldi di cassa** — la liquidità detenuta qui alla fine del periodo, per valuta.
- **Grafico di crescita** — le viste **Abs**, **%** e **P&L**, con il P&L come **Linea**, **Candele** o **Reddito** ([Grafico di crescita del portafoglio](../dashboard/charts.md#portfolio-growth-chart), [Modalità P&L](../dashboard/charts.md#pnl-mode)). La vista scelta è condivisa con la Dashboard.
- **Allocazione** — per tipo, settore e area geografica ([Pannello Allocazione](../dashboard/charts.md#allocation-panel)).

Tornando a un broker già aperto, le sue ultime cifre compaiono subito, aggiornate in background se qualcosa è cambiato ([Tornare indietro e aggiornare](../dashboard/index.md#coming-back-and-refreshing)). **Aggiorna** ricalcola su richiesta anche la scheda **Rischio** e il pannello dei lotti.

---

## 🔍 Scheda Posizioni

La scheda **Posizioni** elenca ciò che detieni presso questo broker, nello stesso pannello delle [Posizioni della Dashboard](../dashboard/positions.md):

<div class="lf-screenshot-carousel" data-carousel="carousel-broker-positions" data-carousel-interval="6000" data-show-titles="true" style="margin: 1.5rem 0 2.5rem 0;">
  <img class="gallery-img lf-screenshot-carousel-item is-active" data-category="brokers" data-name="positions-holdings-table" data-title="📋 Portafoglio (Tabella)" alt="Vista tabella del portafoglio del broker">
  <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="brokers" data-name="positions-holdings-map" data-title="🗺️ Portafoglio (Mappa / Treemap)" alt="Vista mappa del portafoglio del broker">
  <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="brokers" data-name="positions-performance-table" data-title="📈 Periodo (Tabella)" alt="Vista tabella del periodo del broker">
  <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="brokers" data-name="positions-performance-map" data-title="📊 Periodo (Mappa / Grafico)" alt="Vista mappa del periodo del broker">
</div>

- **Portafoglio** mostra le tue posizioni (quantità, valore, peso); **Periodo** mostra i guadagni e le perdite di ogni posizione sulle date selezionate. Entrambi sono disponibili come **Tabella** o **Mappa**.
- La colonna **YOC** è il [Rendimento sul costo](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/yield-on-cost.md) di ogni posizione presso questo broker.
- **Analizza lotti** apre il pannello [Analisi lotti FIFO](../dashboard/positions.md#fifo-lots-analysis) sotto l'elenco: lo trovi nel menu **⋮** di una riga, oppure facendo clic con il tasto destro sull'asset nella tabella o nella mappa.

---

## 📑 In questa sezione

- 📥 **[Transazioni del broker](import.md)** — aggiungi transazioni a questo broker, importa estratti conto e gestisci i report caricati.
- ⚙️ **[Configurazione e info](info.md)** — dettagli del conto, opzioni di trading e pannello di condivisione.
- 🧠 **[AI Export del broker](../ai-export/broker.md)** — cosa contiene un AI Export del broker e quali analisi puoi chiedere a un'AI.
- 🤝 **[Condivisione del broker](sharing.md)** — ruoli (Proprietario, Editor, Visualizzatore) e quote di proprietà.

La pagina Broker, il modulo **Aggiungi broker** e la pagina del broker hanno ciascuno una breve guida contestuale: puoi ripeterle da [Impostazioni → Preferenze → Primo utilizzo e guide](../settings/preferences.md#onboarding-and-guides).
