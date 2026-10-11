# 🔍 Pagina di dettaglio dell'asset

Fai clic su un asset nella [pagina Asset](../index.md) per aprire la sua pagina: il suo storico dei prezzi, gli strumenti per analizzarlo e i dati che ne stanno alla base.

<div class="screenshot-container" style="max-width: 800px; margin: 1rem auto;">
    <img class="gallery-img" data-category="assets" data-name="detail-chart" alt="Pagina di dettaglio dell'asset" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

La pagina ha due schede: **Panoramica**, descritta di seguito, e **Rischio e scenari**.

!!! info "Beta"

    La scheda **Rischio e scenari** è ancora in beta: si apre con l'avviso *L'analisi del rischio è in beta.* e non è ancora coperta da questa documentazione.

---

## 🧭 Cosa mostra la Panoramica

Dall'alto verso il basso:

### 📊 [Segnali](signals.md)

Disegna uno qualsiasi dei **22 indicatori tecnici**, un altro asset o una coppia di valute, o una curva di riferimento sul grafico.

### 📈 [Grafico interattivo](chart.md)

Lo storico dei prezzi, oppure il **[Rendimento rolling](chart.md#rolling-return)** su una finestra a tua scelta (1W, 1M, 3M, 1Y o una lunghezza personalizzata). Fai zoom, pan e convertilo in un'altra valuta.

### ✏️ [Editor dati](data-editor.md)

Aggiungi, correggi o elimina prezzi ed eventi, uno alla volta o da un file CSV.

### 📐 [Misure](measures.md)

Fai clic su due punti del grafico per leggere la variazione tra di essi.

### 🗂️ [Classificazione](classification.md)

La distribuzione settoriale e geografica, nel pannello **Metadati e classificazione**.

### 📅 [Eventi](events.md)

Dividendi, split, interesse e altri eventi dell'asset, disegnati come marcatori sul grafico.

---

## 🔧 Intestazione e barra degli strumenti

- **←** torna all'elenco, o alla pagina da cui sei arrivato, in un solo passaggio, anche dopo aver navigato con le frecce.
- **L'asset** — un punto (verde attivo, rosso archiviato), il suo nome, tipo e valuta, un link **Transazioni (N)** quando ne ha, il suo provider (o **✏️ Manuale**), e un link alla sua pagina web: quella che hai impostato sull'asset, oppure quella del provider.
- **‹ n/N ›** — l'asset precedente o successivo, mantenendo le stesse date (vedi il pannello sotto).
- **Intervallo di date** e **Converti in** — il periodo e la valuta del [grafico](chart.md).
- **AI Export** — copia i dati dell'asset per un assistente AI ([AI Export asset](../../ai-export/asset.md)).
- **Modifica** (✏️) — apre il modulo dell'asset ([Crea e modifica](../create-edit.md)).
- **Sincronizza** (🔄) — scarica gli ultimi prezzi, insieme a quelli degli asset confrontati e ai tassi di cambio necessari al grafico; mostra **Ricalcola** per un Investimento programmato. Non disponibile per un asset senza provider o archiviato.
- **Ricarica** (↻) — ricarica i dati della pagina da ciò che LibreFolio ha memorizzato.

??? info "🧭 Quale ordine seguono le frecce ‹ ›"

    - **Aperto dalla pagina Asset**: l'elenco come l'hai lasciato — la sua ricerca, i filtri, la vista a griglia o tabella e, nella tabella, il suo ordinamento e i filtri di colonna.
    - **Aperto in qualsiasi altro modo** (un link o un segnalibro, una ricarica, la dashboard, Transazioni…), o per un asset che quell'elenco non mostra: tutti gli asset nell'ordine predefinito della pagina Asset, quelli archiviati solo quando l'asset che hai aperto è archiviato.
    - Il contatore (per esempio 3/12) mostra dove ti trovi. Le frecce si fermano a entrambe le estremità e scompaiono quando c'è un solo asset da sfogliare.

---

## 🔗 Correlati

- ➕ **[Crea e modifica](../create-edit.md)** — Creazione e configurazione degli asset
- 📋 **[Panoramica asset](../index.md)** — Torna alla pagina dell'elenco asset
