# 🏦 Broker

Un **broker** è uno dei tuoi conti — presso un'agenzia di intermediazione, una banca o un exchange: il luogo in cui risiedono i tuoi investimenti e la tua liquidità. Ogni transazione e ogni report caricato appartiene a un broker, quindi ne serve almeno uno prima di iniziare.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="brokers" data-name="list" alt="Elenco broker" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

La pagina **Broker** mostra una scheda per broker, con il suo valore (**NAV**) nella valuta scelta in **Valuta** nella parte superiore della pagina. Fai clic su una scheda per aprire il broker.

!!! note "I broker condivisi mostrano la tua quota"

    Su un broker di cui sei comproprietario, i valori sulla sua scheda e nella sua scheda **Panoramica** sono **proporzionati alla tua quota di proprietà**: un Proprietario al 50% vede metà del conto. Editor e Visualizzatori vedono sempre gli importi completi. Vedi [Condivisione broker](sharing.md).

---

## ➕ Crea un broker

1. Apri **Broker** dalla barra laterale e fai clic su **Aggiungi broker**.
2. Digita un **Nome** — l'unico campo obbligatorio — e imposta le opzioni che ti servono.
    <div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
        <img class="gallery-img" data-category="brokers" data-name="edit-modal" alt="Modulo di modifica broker" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
    </div>

3. Fai clic su **Crea**: il broker compare nel tuo elenco, pronto per transazioni e report.
    <div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
        <img class="gallery-img" data-category="brokers" data-name="detail" alt="Modulo di modifica broker" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
    </div>

??? info "⚙️ I campi opzionali — cosa fa ciascuno"

    - **Descrizione** — le tue note.
    - **Plugin di importazione predefinito** — l'importatore che la [Procedura guidata di importazione](../transactions/import/index.md) propone per i file di questo broker.
    - **URL del portale** — il sito web del broker, aperto dalla pagina del broker. La sua icona viene usata quando non imposti un **URL icona personalizzata**.
    - **Conto aperto** e **Conto attivo** — quando è stato aperto il conto e se è ancora aperto. Un broker chiuso viene mostrato in grigio nell'elenco.
    - **Opzioni di trading** — **Consenti acquisto con leva** e **Consenti vendita allo scoperto**, spiegate in [Opzioni di trading](info.md#trading-options).
    - **Saldi iniziali** (solo durante la creazione) — la tua liquidità iniziale. LibreFolio registra un **Deposito** per valuta, **datato oggi**: se il denaro era presente prima, cambia la data di quei depositi nella pagina [Transazioni](../transactions/index.md).

??? warning "🏷️ “Esiste già un broker chiamato …” — quando compare"

    I nomi dei broker sono univoci sull'intero server, per tutti i suoi utenti. Scegli un nome diverso oppure rinomina il broker esistente se è tuo.

    I broker di altri utenti che non puoi aprire sono elencati in **Altri broker esistenti**. Il loro pulsante di condivisione mostra chi ha accesso, così sai a chi chiedere: ogni utente autenticato di questo LibreFolio può vederlo, per qualsiasi broker.

---

## ✏️ Modifica o elimina un broker

- **Modifica** — la matita sulla scheda del broker, oppure **Modifica** nella barra degli strumenti del broker. Proprietari ed Editor possono modificare un broker.
- **Elimina** — il cestino sulla scheda del broker. Solo un Proprietario può eliminare un broker. Se contiene ancora transazioni, LibreFolio indica quante e offre **Vai alle transazioni** o **Elimina broker e transazioni**, che le elimina anch'esse.

---

## 🗂️ Dentro un broker

La barra degli strumenti in alto si applica a ogni scheda:

- l'**intervallo di date** e la **Valuta** delle cifre;
- **Modifica**, **Condividi broker** (apre la scheda **Info**) e **Aggiorna**;
- **AI Export**, che copia negli appunti un prompt già pronto su questo broker — vedi [Broker AI Export](../ai-export/broker.md).

Sotto, cinque schede:

1. **Panoramica** — come sta andando il conto (sotto).
2. **Posizioni** — ciò che detieni presso questo broker (sotto).
3. **Rischio** — l'analisi del rischio della Dashboard, limitata a questo broker (vedi [Scheda Rischio della Dashboard](../dashboard/index.md#risk-tab)).
4. **Transazioni** — il registro del broker, le voci manuali, le importazioni e i report caricati (vedi [Transazioni broker](import.md)).
5. **Info** — dettagli del conto, opzioni di trading e condivisione (vedi [Configurazione e Info](info.md)).

---

## 📈 Scheda Panoramica

La **Panoramica** risponde a "come sta andando questo conto?" con gli stessi blocchi della [Panoramica della Dashboard](../dashboard/index.md), limitati a questo broker:

- **Schede KPI** — **P&L periodo**, **Rendimenti** e **Patrimonio netto** ([Schede KPI](../dashboard/kpi-cards.md)).
- **Saldi di cassa** — la liquidità detenuta qui, per valuta.
- **Grafico di crescita** — le viste **Abs**, **%** e **P&L**, con P&L come **Linea**, **Candele** o **Reddito** ([Grafico di crescita del portafoglio](../dashboard/charts.md#portfolio-growth-chart), [Modalità P&L](../dashboard/charts.md#pnl-mode)). La vista scelta è condivisa con la Dashboard.
- **Allocazione** — per tipo, settore e area geografica ([Pannello di allocazione](../dashboard/charts.md#allocation-panel)).

Tornando a un broker che hai già aperto, vengono mostrate subito le sue ultime cifre, aggiornate in background se qualcosa è cambiato ([Tornare e aggiornare](../dashboard/index.md#coming-back-and-refreshing)). **Aggiorna** ricalcola su richiesta, inclusi la scheda **Rischio** e il pannello dei lotti.

---

## 🔍 Scheda Posizioni

La scheda **Posizioni** elenca ciò che detieni presso questo broker, nello stesso pannello delle [Posizioni della Dashboard](../dashboard/positions.md):

<div class="lf-screenshot-carousel" data-carousel="carousel-broker-positions" data-carousel-interval="6000" data-show-titles="true" style="margin: 1.5rem 0 2.5rem 0;">
  <img class="gallery-img lf-screenshot-carousel-item is-active" data-category="brokers" data-name="positions-holdings-table" data-title="📋 Posizioni (Tabella)" alt="Vista tabella posizioni broker">
  <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="brokers" data-name="positions-holdings-map" data-title="🗺️ Posizioni (Mappa / Treemap)" alt="Vista mappa posizioni broker">
  <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="brokers" data-name="positions-performance-table" data-title="📈 Performance (Tabella)" alt="Vista tabella performance broker">
  <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="brokers" data-name="positions-performance-map" data-title="📊 Performance (Mappa / Grafico)" alt="Vista mappa performance broker">
</div>

- **Portafoglio** mostra le tue posizioni (quantità, valore, peso); **Periodo** mostra i guadagni e le perdite di ogni posizione sulle date selezionate. Entrambi sono disponibili come **Tabella** o **Mappa**.
- La colonna **YOC** è il [Rendimento sul costo](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/yield-on-cost.md) di ogni posizione presso questo broker.
- **Analizza lotti** apre il pannello [Analisi lotti FIFO](../dashboard/positions.md#fifo-lots-analysis) sotto l'elenco: trovalo nel menu **⋮** di una riga oppure fai clic con il pulsante destro del mouse sull'asset nella tabella o nella mappa.

---

## 📑 In questa sezione

- 📥 **[Transazioni broker](import.md)** — aggiungi transazioni a questo broker, importa estratti conto e gestisci i report caricati.
- ⚙️ **[Configurazione e Info](info.md)** — dettagli del conto, opzioni di trading e pannello di condivisione.
- 🧠 **[Broker AI Export](../ai-export/broker.md)** — cosa contiene un'esportazione broker e le analisi che puoi chiedere a un'AI.
- 🤝 **[Condivisione broker](sharing.md)** — ruoli (Proprietario, Editor, Visualizzatore) e quote di proprietà.

La pagina Broker, il modulo **Aggiungi broker** e la pagina del broker hanno ciascuno una breve guida contestuale: ripetile da [Impostazioni → Preferenze → Primo utilizzo e guide](../settings/preferences.md#onboarding-and-guides).
