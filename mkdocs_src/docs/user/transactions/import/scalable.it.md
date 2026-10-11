# 📥 ![](../../../static/icons/brokers/scalable.png) Scalable Capital

!!! info "Alpha"

    Questi importatori sono in **Alpha**: alcune tipologie di righe non sono ancora state viste in esportazioni reali (vedi [Limiti](#limits)). Se un file viene rifiutato, o una riga viene importata in un modo che sembra sbagliato, segnalacelo nelle [issue](https://github.com/Librefolio/LibreFolio/issues) del progetto.

LibreFolio importa entrambi i conti di **Scalable Capital**: il **conto broker** e il **conto deposito** (*Tagesgeld*). LibreFolio non è affiliato a Scalable Capital.

---

## 🏦 Due conti, due broker {: #two-brokers }

Ogni conto diventa un broker a sé stante in LibreFolio, letto dal proprio importatore:

| Conto Scalable | Importatore | File che legge |
|:--|:--|:--|
| Conto broker | **Scalable Capital conto broker** | il file broker dell'esportatore LibreFolio, oppure il CSV di Scalable stesso |
| Conto deposito | **Scalable Capital conto deposito** | il file del conto deposito dell'esportatore LibreFolio |

Perché due broker? Ogni conto ha il proprio saldo di cassa e il proprio IBAN, e il denaro che sposti tra essi è un **Giroconto**, che collega due broker. Con due broker, ogni saldo può essere verificato rispetto all'app di Scalable, e ogni trasferimento diventa un'unica coppia collegata. Ogni importatore rifiuta il file dell'altro conto e indica l'importatore che lo legge.

---

## 📤 Cosa esportare

### 🧩 Consigliato: l'esportatore LibreFolio {: #exporter }

L'[esportatore LibreFolio](https://github.com/Librefolio/librefolio-exporter) è un'estensione per Chrome, Edge, Brave e gli altri browser Chromium, versione 120 o successiva. Legge le tue transazioni nelle pagine di Scalable, nel tuo browser, e le salva come file CSV:

- funziona su **ogni piano**, incluso FREE;
- è l'**unico modo** per esportare il **conto deposito**;
- aggiunge ciò che manca al CSV di Scalable stesso: l'**id della transazione** e il **tipo esatto** di ogni movimento.

Prima di installarlo, leggi il [README](https://github.com/Librefolio/librefolio-exporter#readme) dell'esportatore: copre in modo completo l'installazione e l'aggiornamento, la privacy, e i rischi di un'estensione che usa l'interfaccia interna dell'app web di Scalable.

**Installalo una volta:**

1. Scarica i due file dell'[ultima release](https://github.com/Librefolio/librefolio-exporter/releases/latest), `librefolio-exporter-<version>.zip` e `librefolio-exporter-<version>.zip.sha256`, nella stessa cartella — per esempio `Downloads/chromePlugin`.
2. Verifica lo ZIP da un terminale. Il `cd` va in quella cartella; il secondo comando confronta lo ZIP con l'impronta nel suo file `.sha256`:

    === "macOS"

        ```bash
        cd ~/Downloads/chromePlugin
        shasum -a 256 -c librefolio-exporter-*.zip.sha256
        ```

    === "Linux"

        ```bash
        cd ~/Downloads/chromePlugin
        sha256sum -c librefolio-exporter-*.zip.sha256
        ```

    === "Windows"

        Windows non ha un comando che legge i file `.sha256`: usa le righe PowerShell del [README](https://github.com/Librefolio/librefolio-exporter#readme) dell'esportatore.

    `OK` significa che lo ZIP è esattamente quello pubblicato. Con qualsiasi altra risposta, non installarlo: scarica di nuovo entrambi i file.

3. Estrailo in quella cartella: ottieni una cartella `librefolio-exporter`. Lasciala lì, dato che il browser carica l'estensione da essa.
4. Apri `chrome://extensions` (`edge://extensions` in Edge), attiva la **Modalità sviluppatore**, clicca **Carica estensione non pacchettizzata** e scegli la cartella `librefolio-exporter`.

**Esporta:**

1. Accedi a Scalable Capital: il pulsante **LibreFolio** appare nell'angolo in basso a destra di ogni pagina.
2. Cliccalo, scegli i conti e il periodo, poi clicca **Esporta CSV**.
3. Ottieni `scalable-broker_<date>_<time>.csv` e `scalable-deposit_<date>_<time>.csv` — insieme in un unico ZIP quando esporti entrambi i conti. Estrai lo ZIP: LibreFolio legge i file CSV.

La prima esportazione legge l'intera cronologia; le successive partono dall'ultima esportazione (**Dall'ultima**), quindi vengono lette solo le nuove transazioni. Le righe già presenti in LibreFolio tornano come [probabili duplicati](index.md#duplicate-detection) e arrivano deselezionate. Puoi rinominare i file: LibreFolio riconosce ciascuno dalle sue colonne.

!!! warning "File scritti dall'esportatore 1.0.0"

    L'esportatore 1.0.0 scriveva la commissione dentro l'importo di ogni operazione. LibreFolio importa quelle operazioni così come sono, senza una commissione separata, e te lo segnala. Aggiorna l'esportatore alla 1.0.1 o successiva ed esportale di nuovo. Se hai già importato un file del genere, elimina prima le operazioni elencate nell'avviso: i loro importi cambiano, quindi LibreFolio non le riconoscerebbe come duplicati.

### 📄 Alternativa: il CSV di Scalable stesso {: #scalable-csv }

Sui piani **PRIME** e **PRIME+**, Scalable ti permette di scaricare le transazioni del **conto broker** come file CSV: l'importatore **Scalable Capital conto broker** lo legge così come scaricato. Copre solo il conto broker — il conto deposito richiede sempre l'esportatore.

Attieniti a una sola fonte per conto. Le descrizioni che LibreFolio scrive differiscono tra le due fonti — solo quelle dell'esportatore contengono l'id della transazione — quindi le righe importate da una fonte tornano dall'altra come *possibili* duplicati, comunque selezionate: quando cambi fonte, esporta dal giorno successivo al tuo ultimo import.

---

## ⚙️ Configurare i due broker {: #set-up }

Crea due [broker](../../brokers/index.md), uno per conto — per esempio *Scalable broker* e *Scalable overnight account* — e scegli il **Plugin di Import Predefinito** di ciascuno:

| Broker per | Plugin di importazione predefinito | Icona |
|:--|:--|:--:|
| il conto broker | **Scalable Capital conto broker** | ![Il logo di Scalable con un badge blu a forma di grafico, l'icona dell'importatore Scalable Capital conto broker](../../../static/icons/brokers/scalable-broker.png){: width="48" } |
| il conto deposito | **Scalable Capital conto deposito** | ![Il logo di Scalable con un badge arancione a forma di salvadanaio, l'icona dell'importatore Scalable Capital conto deposito](../../../static/icons/brokers/scalable-deposit.png){: width="48" } |

Il broker mostra poi l'icona dell'importatore da solo: un broker senza un'icona propria mostra l'icona del suo plugin di importazione predefinito, prima dell'icona del sito web del suo **URL portale**, quindi lascia **URL icona personalizzata** vuoto.

---

## 📥 Importazione {: #import }

Importa ciascun file nel proprio broker, nella stessa importazione o in momenti diversi: nella [Procedura guidata di importazione](how-to.md), trascina i file CSV e assegna ciascuno al suo broker.

Se un file finisce nel broker sbagliato, la procedura guidata te lo dice subito dopo il caricamento. Mostra perché il plugin predefinito del broker non può leggere il file e quale broker può farlo, e offre di spostare il file, mantenerlo o rimuoverlo.

### 🔁 Trasferimenti tra i tuoi due conti {: #transfers }

Il denaro che sposti tra il conto broker e il conto deposito appare in entrambi i file: un **Prelievo** in un broker e un **Deposito** nell'altro, nello stesso giorno e per lo stesso importo. Unisci ogni coppia in un unico **Giroconto**: il workspace bulk della pagina [Transazioni](../index.md) suggerisce le coppie, e chiede prima di **Salva tutto** se non le hai esaminate.

- **File importati insieme**: le due metà si incontrano nel workspace, dove un banner verde, *Transazioni complementari rilevate*, offre di **Unisci** ogni coppia — o tutte insieme, con **Unisci tutti (N)**.
- **File importati in momenti diversi**: quando importi il secondo file, il workspace trova le metà già salvate e mostra il pulsante 💡: cliccalo per aggiungerle, poi **Unisci** ogni coppia dal banner. Per trasferimenti salvati molto tempo prima, puoi anche selezionare le righe di trasferimento di entrambi i broker nella pagina **Transazioni** e cliccare **Modifica**: il banner appare nel workspace.

Puoi anche collegare una coppia manualmente: seleziona le sue due righe nella pagina **Transazioni** e clicca **🔗 Promuovi coppia**.

Le due metà hanno descrizioni diverse, poiché ciascuna porta il proprio id della transazione: mantieni la descrizione unita che l'unione propone (in **Unisci tutto**, la scelta predefinita: **Combina**). Un'esportazione che si sovrappone a un trasferimento unito riporta poi le sue metà come probabili duplicati, deselezionate.

### 🤔 Un solo broker? {: #one-broker-only }

Puoi importare entrambi i file in un unico broker. L'importazione funziona, ma:

- ogni trasferimento tra i conti resta un **Deposito** più un **Prelievo**, poiché un giroconto richiede due broker: il denaro in entrata e in uscita sembra maggiore di quanto sia;
- i due conti condividono un unico saldo di cassa, quindi nessuno dei due può essere verificato da solo rispetto all'app di Scalable.

In ogni caso, non importare mai lo stesso file in due broker: le sue transazioni verrebbero contate due volte.

---

## 📝 Cosa viene importato {: #what-is-imported }

| Nel file (`type`) | Importato come |
|:--|:--|
| `Buy`, `Savings plan` | **Acquisto**, sull'importo del file — il valore delle quote — con la commissione dell'ordine come **Commissione** e l'imposta come **Imposta** dello stesso titolo. Un'imposta restituita diventa un **Deposito** |
| `Sell` | **Vendita**, allo stesso modo |
| `Distribution` | **Dividendo**, lordo — l'importo accreditato più l'imposta trattenuta — con quell'imposta come **Imposta**; netto quando il file non indica l'imposta |
| `Interest` | **Interesse**, lordo, con l'imposta trattenuta come **Imposta**; netto quando il file non indica l'imposta |
| `Deposit`, `Withdrawal` — bonifici bancari, e trasferimenti tra i tuoi due conti | **Deposito**, **Prelievo** |
| `Fee` | **Commissione** |
| `Taxes` | **Imposta**; un rimborso d'imposta diventa un **Deposito** |
| Qualsiasi altra riga di liquidità, come un bonus | **Deposito** o **Prelievo**, in base al segno del suo importo |
| `Security transfer`, `Corporate action` e altri tipi | Non importati: un [avviso](#notices) li elenca |

- **Vengono importate solo le righe eseguite**: un avviso conta le altre.
- **I titoli** arrivano con il loro ISIN e nome: abbina ciascuno ai tuoi asset nel passaggio **Revisione** della procedura guidata (vedi [Mappatura degli asset](index.md#asset-mapping)).
- **Ogni descrizione termina con l'id della transazione**: `· id …` dall'esportatore, seguito da `· ref …` quando la riga ha un riferimento; `· ref …` dal CSV di Scalable. La commissione e l'imposta di un'operazione iniziano con `Order fee ·` e `Tax ·`. L'id tiene distinti due movimenti identici, e permette a una nuova esportazione di riconoscere le righe già importate.
- **Tag**: `import` e `scalable`.
- **Gli importi vengono copiati** dal file, mai ricalcolati o convertiti — un dividendo o un interesse lordo è la somma di due delle sue colonne — e la valuta proviene da ogni riga.

---

## 🔔 Cosa ti dice LibreFolio {: #notices }

Nel passaggio **Analizza**, gli avvisi dell'importatore (⚠️) ti dicono cosa ha escluso o letto in un modo che vale la pena verificare, ciascuno con le sue righe:

- **Non eseguite** — le righe in sospeso, annullate, scadute o rifiutate non vengono importate; un ordine eseguito in seguito arriva con la prossima esportazione.
- **Eseguite in parte** — gli ordini eseguiti in parte e ancora aperti non vengono ancora importati: arrivano, eseguiti, con un'esportazione successiva.
- **Storni** — le righe che stornano una transazione già registrata non vengono importate: verifica quella transazione e correggila a mano.
- **Non importati** — trasferimenti di titoli, operazioni societarie e tipi che LibreFolio non legge ancora: aggiungili a mano se spostano quote o liquidità.
- **Registrate per segno** — righe di liquidità di tipo sconosciuto, o con un segno inatteso, diventano un deposito o un prelievo in base al segno del loro importo.
- **Rimborsi d'imposta** — importati come depositi: in LibreFolio un'imposta toglie sempre denaro.
- **Nessun dettaglio di commissione o imposta** — righe importate con l'importo mostrato da Scalable, senza commissione o imposta separate: esporta di nuovo con l'opzione per includere commissioni e imposte.
- **Dividendi netti** — il file non indica l'imposta trattenuta, quindi il dividendo viene importato come accreditato.
- **Trasferimenti tra i tuoi conti** — un promemoria a importare il file dell'altro conto nel suo broker e [unire ogni coppia](#transfers).
- **Più conti deposito** — il file ne contiene più di uno: tutte le loro righe finiscono in questo broker, il cui saldo è la loro somma.
- **Commissione dentro l'importo** — operazioni da un [file dell'esportatore 1.0.0](#exporter), importate così come sono.
- **Righe illeggibili** — manca una data, un importo, una valuta, le quote o il titolo: queste righe non vengono importate.

---

## ⚠️ Limiti {: #limits }

- **Alpha**: non sono ancora state viste esportazioni reali di vendite, dividendi, storni, cripto o ordini eseguiti in parte. Verifica con attenzione quelle righe dopo l'importazione.
- **Segnalaci**: se un file viene rifiutato o una riga sembra sbagliata, apri una [issue](https://github.com/Librefolio/LibreFolio/issues), con le righe interessate anonimizzate.

## 🔗 Riferimento per sviluppatori

→ [Elenco dei provider BRIM](../../../developer/backend/brim/providers_list.md) · [Dire il perché con un codice](../../../developer/architecture/patterns/brim_plugin_guide.md#cannot-parse-detail), i rifiuti dei due importatori
