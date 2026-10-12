# 📥 ![](../../../static/icons/brokers/scalable.png) Scalable Capital

LibreFolio importa entrambi i conti di **Scalable Capital**: il **conto broker** e il **conto deposito**. LibreFolio non è affiliato a Scalable Capital.

---

## 🏦 Due conti, due broker {: #two-brokers }

Ogni conto diventa un broker a sé stante in LibreFolio, letto dal proprio importatore. Crea due [broker](../../brokers/index.md), uno per conto, e scegli il **Plugin di Import Predefinito** di ciascuno:

| Conto Scalable | Plugin di Import Predefinito | Esempio di nome del broker | File che legge |
|:--|:--|:--|:--|
| Conto broker | ![](../../../static/icons/brokers/scalable-broker.png){: style="width:16px;vertical-align:middle;margin-right:6px" } **Scalable Capital conto broker** | *Scalable broker* | il file broker dell'esportatore LibreFolio, oppure il CSV di Scalable stesso |
| Conto deposito | ![](../../../static/icons/brokers/scalable-deposit.png){: style="width:16px;vertical-align:middle;margin-right:6px" } **Scalable Capital conto deposito** | *Scalable overnight account* | il file del conto deposito dell'esportatore LibreFolio |

Lascia vuoto **URL Icona Personalizzata**: un broker senza un'icona propria mostra l'icona del suo plugin di importazione predefinito — quella nella tabella — prima dell'icona del sito web del suo **URL Portale**.

Perché due broker? Ogni conto ha il proprio saldo di cassa e il proprio IBAN, e il denaro che sposti tra essi è un **Giroconto**, che collega due broker. Con due broker, ogni saldo può essere verificato rispetto all'app di Scalable, e ogni trasferimento diventa un'unica coppia collegata. Ogni importatore rifiuta il file dell'altro conto e indica l'importatore che lo legge.

---

## 📤 Come esportare {: #exporter }

A ottobre 2026, Scalable ti permette di scaricare le tue transazioni solo sui piani **PRIME** e **PRIME+**, e mai quelle del conto deposito. Per questo è stato realizzato l'[esportatore LibreFolio](https://github.com/Librefolio/librefolio-exporter).

L'esportatore è un'estensione per Chrome, Edge, Brave e gli altri browser Chromium, versione 120 o successiva. Legge le tue transazioni nelle pagine di Scalable, nel tuo browser, e le salva come file CSV:

- funziona su **ogni piano**, incluso FREE;
- è l'**unico modo** per esportare il **conto deposito**;
- aggiunge ciò che manca al CSV di Scalable stesso: l'**id della transazione** e il **tipo esatto** di ogni movimento.

??? note "🧩 Installa l'esportatore — una volta, prima della prima esportazione"

    I dettagli aggiornati sono nel [README](https://github.com/Librefolio/librefolio-exporter#readme) dell'esportatore, che copre anche l'aggiornamento, la privacy e i rischi di un'estensione che usa l'interfaccia interna dell'app web di Scalable: leggilo prima di installarlo. Ecco una sintesi dei passaggi.

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

---

## 📥 Importazione {: #import }

Importa ciascun file nel proprio broker, nella stessa importazione o in momenti diversi: nella [Procedura guidata di importazione](how-to.md), trascina i file CSV e assegna ciascuno al suo broker. Non importare mai lo stesso file in due broker: le sue transazioni verrebbero contate due volte.

Se un file finisce nel broker sbagliato, la procedura guidata te lo dice subito dopo il caricamento. Mostra perché il plugin predefinito del broker non può leggere il file e quale broker può farlo, e offre di spostare il file, mantenerlo o rimuoverlo.

### 🔁 Trasferimenti tra i tuoi due conti {: #transfers }

Il denaro che sposti tra il conto broker e il conto deposito appare in entrambi i file: un **Prelievo** in un broker e un **Deposito** nell'altro, nello stesso giorno e per lo stesso importo. Unisci ogni coppia in un unico **Giroconto**: il workspace bulk della pagina [Transazioni](../index.md) suggerisce le coppie, e chiede prima di **Salva tutto** se non le hai esaminate.

- **File importati insieme**: le due metà si incontrano nel workspace, dove un banner verde, *Transazioni complementari rilevate*, offre di **Unisci** ogni coppia — o tutte insieme, con **Unisci tutti (N)**.
- **File importati in momenti diversi**: quando importi il secondo file, il workspace trova le metà già salvate e mostra il pulsante 💡: cliccalo per aggiungerle, poi **Unisci** ogni coppia dal banner. Per trasferimenti salvati molto tempo prima, puoi anche selezionare le righe di trasferimento di entrambi i broker nella pagina **Transazioni** e cliccare **Modifica**: il banner appare nel workspace.

Puoi anche collegare una coppia manualmente: seleziona le sue due righe nella pagina **Transazioni** e clicca **🔗 Promuovi coppia**.

Le due metà hanno descrizioni diverse, poiché ciascuna porta il proprio id della transazione: mantieni la descrizione unita che l'unione propone (in **Unisci tutto**, la scelta predefinita: **Combina**). Un'esportazione che si sovrappone a un trasferimento unito riporta poi le sue metà come probabili duplicati, deselezionate.

## 🔗 Riferimento per sviluppatori

→ [Importatori Scalable Capital](../../../developer/backend/brim/scalable.md) · [Elenco dei provider BRIM](../../../developer/backend/brim/providers_list.md) · [Dire il perché con un codice](../../../developer/architecture/patterns/brim_plugin_guide.md#cannot-parse-detail), i rifiuti dei due importatori
