# 📥 Transazioni del Broker

La scheda **Transazioni** è il centro di controllo per modificare il libro mastro del broker. Elenca tutte le operazioni finanziarie registrate (acquisti, vendite, dividendi, depositi, prelievi, trasferimenti e conversioni FX) relative a questo broker.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
 <img class="gallery-img" data-category="brokers" data-name="transactions-tab" alt="Scheda Transazioni del Broker">
</div>

Da questa scheda puoi registrare transazioni manualmente o avviare importazioni in blocco di estratti conto.

---

## ➕ Transazioni Manuali

Fai clic sul pulsante **Aggiungi Transazione** (icona `Plus`) per aprire la procedura guidata modale per la singola transazione. Questa ti consente di registrare manualmente:

- **Acquisto / Vendita**: scambia asset, specificando data, prezzo, quantità e valuta.
- **Dividendo / Reddito**: reddito ricevuto dagli asset in portafoglio.
- **Deposito / Prelievo**: flussi di cassa esterni in entrata o in uscita dal saldo di cassa del broker.
- **Trasferimento**: trasferimento di liquidità o asset tra broker (ad esempio, finanziando il conto tramite un broker bancario).
- **Conversione FX**: cambi di valuta all'interno del conto del broker.

Per una spiegazione dettagliata dei campi delle transazioni e delle regole di validazione, consulta la guida **[Modulo di Transazione](../transactions/form.md)**.

---

## 🧙 Importazione in Blocco (BRIM)

Il pulsante **Importa** (icona `Upload`) avvia la procedura guidata **BRIM** (Broker Report Import Module), che importa in blocco gli estratti conto esportati dal tuo broker: analizza i file, valida ogni riga, uniforma i titoli trovati, verifica la presenza di duplicati e ti consente di rivedere tutto prima che qualsiasi dato venga scritto. Le righe approvate finiscono nell'**editor in blocco**, dove un **Salva tutto** finale le registra nel libro mastro.

La stessa procedura guidata è disponibile anche dalla pagina globale **[Transazioni](../transactions/index.md)**. Per la procedura completa, consulta le guide dedicate:

- 📥 **[Importazione dal Broker (BRIM)](../transactions/import/index.md)** — broker supportati, formati e note specifiche per plugin.
- 🧙 **[Come Importare le Transazioni](../transactions/import/how-to.md)** — la procedura guidata, passo dopo passo.

---

## 🧩 Il tuo broker non è supportato?

Se il tuo broker non ha ancora un plugin di importazione, puoi aiutare:

- **Richiedi un plugin** — apri una [richiesta di plugin](https://github.com/Librefolio/LibreFolio/issues/new?template=plugin_request.yml) su GitHub, allegando un campione anonimizzato del file esportato dal broker in modo che il formato possa essere compreso. (Il passaggio Corrections della procedura guidata include anche un banner "apri una segnalazione" per segnalare le righe che sembrano errate.)
- **Scrivi un plugin** — la [Guida ai plugin BRIM](../../developer/architecture/patterns/brim_plugin_guide.md) guida gli sviluppatori attraverso il contratto del provider; consulta [Contribuire](../../community/contribute.md) per il flusso di lavoro generale.

---

## 🗂️ Report Caricati

Fai clic sul pulsante **Report Caricati** (icona `FileText`) per gestire i file di report BRIM archiviati per questo broker. La finestra modale ti consente di:

- Rivedere i report caricati (nome, data di caricamento, dimensione, stato), con un'**anteprima** rapida del contenuto di ciascun file.
- **Caricare** nuovi report direttamente — vengono assegnati automaticamente a questo broker e diventano disponibili nel passaggio Select Files della procedura guidata.
- **Eliminare** i report che non ti servono più.
- Passare alla pagina completa **[File e Caricamenti](../files/index.md#broker-reports)**, pre-filtrata su questo broker.
