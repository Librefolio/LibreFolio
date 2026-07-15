# 📥 Transazioni del broker

La scheda **Transazioni** è il centro di controllo per modificare il registro del broker. Elenca tutte le operazioni finanziarie registrate (acquisti, vendite, dividendi, depositi, prelievi, trasferimenti e conversioni FX) relative a questo broker.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
 <img class="gallery-img" data-category="brokers" data-name="transactions-tab" alt="Broker Transactions Tab">
</div>

Da questa scheda è possibile eseguire transazioni manuali o avviare importazioni massive di estratti conto.

---

## ➕ Transazioni Manuali

Fai clic sul pulsante **Aggiungi Transazione** (icona `Plus`) per aprire la procedura guidata della finestra modale per singola transazione. Questo ti consente di registrare manualmente:

- **Acquisto / Vendita**: Negoziazione di asset, specificando data, prezzo, quantità e valuta.
- **Dividendo / Reddito**: Reddito ricevuto dalle partecipazioni.
- **Deposito / Prelievo**: Flussi di cassa esterni in entrata o in uscita dal saldo di cassa del broker.
- **Trasferimento**: Trasferimento di denaro o asset tra broker (ad es., finanziamento del conto da un broker bancario).
- **Conversione FX**: Cambi di valuta all'interno del conto del broker.

Per una spiegazione dettagliata dei campi della transazione e delle regole di validazione, consulta la guida **[Modulo Transazione](../transactions/form.md)**.

---

## 🧙 BRIM: Modulo di Importazione Estratti Conto Broker

Il pulsante **Importa** (icona `Upload`) avvia la procedura guidata **BRIM**. Questo modulo ti consente di importare in massa gli estratti conto esportati dal tuo broker (formati CSV o Excel), eseguire validazioni automatiche di integrità e mappare i ticker agli asset locali prima del commit finale.

### Il Flusso di Importazione

<div class="lf-screenshot-carousel" data-carousel="carousel-broker-import" data-carousel-interval="6000" data-show-titles="true" style="margin: 1.5rem 0 2.5rem 0;">
 <img class="gallery-img lf-screenshot-carousel-item is-active" data-category="brokers" data-name="import-modal" data-title="📥 Quick Import Modal" alt="Import Modal">
 <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="brokers" data-name="import-wizard-step1" data-title="🧙 Wizard — Step 1: Upload" alt="Import Wizard Step 1">
 <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="brokers" data-name="import-wizard-step2" data-title="⚙️ Wizard — Step 2: Parser Config" alt="Import Wizard Step 2">
 <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="brokers" data-name="import-wizard-step3" data-title="🧠 Wizard — Step 3: Analysis" alt="Import Wizard Step 3">
 <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="brokers" data-name="import-wizard-step4-resolution" data-title="🔍 Wizard — Step 4: Asset Resolution" alt="Import Wizard Asset Resolution">
 <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="brokers" data-name="import-wizard-duplicate" data-title="⚠️ Duplicate Detection" alt="Import Wizard Duplicate Detection">
 <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="brokers" data-name="import-bulk-staging" data-title="📦 Bulk Staging" alt="Import Bulk Staging">
</div>

La procedura guidata procede attraverso i seguenti passaggi:

1. **Seleziona File & Parser**: Scegli il file dell'estratto conto e seleziona la configurazione di parser appropriata (ad es., Interactive Brokers, Degiro, Directa, Charles Schwab, CSV generico, ecc.).
2. **Verifica Intestazioni & Mappatura**: Mostra le intestazioni CSV per confermare che il parser sia allineato correttamente con le colonne.
3. **Analisi Operazioni**: Elabora il file e visualizza una griglia di anteprima delle azioni analizzate (Acquisti, Vendite, Dividendi, ecc.).
 * **Badge**: Le operazioni sono etichettate come `UNIQUE` (nuova operazione), `DUPLICATE` (già esistente nel database), o `UNRESOLVED` (richiede mappatura ticker/ISIN).
 * **Note TODO**: Evidenziano campi che richiedono attenzione o elementi che non possono essere analizzati automaticamente.
4. **Risoluzione Asset**: Se l'estratto conto contiene ticker o ISIN che non esistono nel tuo registro asset locale, BRIM mostra un passaggio di mappatura. Puoi:
 * Mappare il ticker a un asset esistente.
 * Creare un nuovo asset direttamente da questa schermata, precompilato con i dettagli estratti dall'estratto conto.
5. **Staging Massivo & Commit**: Rivedi l'elenco di staging delle transazioni pulite e uniche. Deseleziona le operazioni che desideri escludere, quindi fai clic su **Commit** per scrivere i record nel registro del tuo portafoglio.

---

## 📑 Cronologia Importazioni

Fai clic sul pulsante **Mostra Cronologia Importazioni** (icona `FileText`) per visualizzare un registro completo delle attività di importazione precedenti. Mostra:

- Nome e dimensione del file caricato.
- Righe elaborate e numero totale di transazioni sottoposte a commit.
- Timestamp del caricamento.
- Utente che ha eseguito l'importazione.
