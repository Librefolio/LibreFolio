# 📥 ![](../../../static/icons/brokers/scalable.png) Scalable Capital

LibreFolio importa entrambi i conti di **Scalable Capital**: il **conto broker** e il **conto deposito**. LibreFolio non è affiliato a Scalable Capital.

---

## 🏦 Due conti, due broker {: #two-brokers }

Ogni conto diventa un broker a sé stante in LibreFolio, letto dal proprio importatore. Crea due [broker](../../brokers/index.md), uno per conto, e scegli il **Plugin di Import Predefinito** di ciascuno:

<div class="lf-accounts-table" markdown>

| Conto Scalable | Plugin di Import Predefinito | File che legge |
|:--|:--|:--|
| ![](../../../static/icons/brokers/scalable-broker.png){: style="width:36px;vertical-align:middle;margin-right:6px" } Conto broker | **Scalable Capital conto broker** | il file broker dell'esportatore LibreFolio, oppure il CSV di Scalable stesso |
| ![](../../../static/icons/brokers/scalable-deposit.png){: style="width:36px;vertical-align:middle;margin-right:6px" } Conto deposito | **Scalable Capital conto deposito** | il file del conto deposito dell'esportatore LibreFolio |

</div>

#### ❓ Perché due broker? {: #why-two-brokers }

- Ogni conto ha il proprio saldo di cassa e il proprio IBAN.
- Il denaro che sposti tra i due conti è un **Giroconto**, che collega due broker.
- Con due broker, ogni saldo può essere verificato rispetto all'app di Scalable, e ogni trasferimento diventa un'unica coppia collegata.
- Ogni importatore rifiuta il file dell'altro conto e indica l'importatore che lo legge.

---

## 📤 Come esportare {: #exporter }

A ottobre 2026, Scalable ti permette di scaricare le tue transazioni solo sui piani **PRIME** e **PRIME+**, e mai quelle del conto deposito.

Per questo è stato realizzato un plugin per browser che esporta i tuoi dati in file CSV: l'[esportatore LibreFolio](https://github.com/Librefolio/librefolio-exporter). Funziona in Chrome, Edge, Brave e negli altri browser Chromium, versione 120 o successiva, e legge le tue transazioni nelle pagine di Scalable, nel tuo browser.

Consigliamo il **nostro plugin** per i seguenti motivi:

- funziona su **ogni piano**, incluso FREE;
- è l'**unico modo** per esportare il **conto deposito**;
- aggiunge ciò che manca al CSV di Scalable stesso: l'**id della transazione** e il **tipo esatto** di ogni movimento.

Il plugin di import di LibreFolio per il conto broker legge anche il CSV di Scalable stesso (PRIME); quello del conto deposito legge solo il file dell'esportatore.

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

---

## 📥 Importazione {: #import }

Importa ciascun file nel proprio broker, nella stessa importazione o in momenti diversi: nella [Procedura guidata di importazione](how-to.md), trascina i file CSV e assegna ciascuno al suo broker. Non importare mai lo stesso file in due broker: le sue transazioni verrebbero contate due volte.

!!! note "💡 Un file nel broker sbagliato"

    Se un broker ha un **Plugin di Import Predefinito**, la procedura guidata controlla ogni file assegnato a quel broker subito dopo il caricamento. Quando quel plugin non può leggere un file, la procedura guidata ti dice perché, mostra quale broker può leggerlo e offre di spostare il file, mantenerlo o rimuoverlo.

### 🔁 Trasferimenti tra i tuoi due conti {: #transfers }

Il denaro che sposti tra il conto broker e il conto deposito compare in entrambi i file:

1. il conto da cui esce il denaro registra un **Prelievo**;
2. il conto in cui arriva registra un **Deposito**, nello stesso giorno e per lo stesso importo;
3. unisci i due in un unico **Giroconto**: dopo l'importazione, mentre le [nuove righe](../index.md#bulk-workspace) aspettano **Salva tutto**, LibreFolio ti suggerisce le coppie, e prima di salvare ti chiede conferma se non le hai esaminate.

??? info "🔍 Come vengono trovate le coppie, e come correggerle"

    - **File importati insieme**: le due metà arrivano con le altre nuove righe, e un banner verde, *Transazioni complementari rilevate*, propone di unire ogni coppia con **Unisci** — o tutte insieme, con **Unisci tutti (N)**.
    - **File importati in momenti diversi**: quando importi il secondo file, LibreFolio trova le metà già salvate e mostra il pulsante 💡: cliccalo per aggiungerle, poi **Unisci** ogni coppia dal banner. Per trasferimenti salvati molto tempo prima, puoi anche selezionare le righe di trasferimento di entrambi i broker nella pagina **Transazioni** e cliccare **Modifica**: compare lo stesso banner.
    - **A mano**: seleziona le due righe di una coppia nella pagina **Transazioni** e clicca **🔗 Promuovi coppia**.
    - **Descrizioni**: le due metà hanno descrizioni diverse, poiché ciascuna porta il proprio id della transazione. Mantieni la descrizione unita che l'unione propone (in **Unisci tutti**, la scelta predefinita: **Combina**): un'esportazione che si sovrappone a un trasferimento unito riporta poi le sue metà come probabili duplicati, deselezionate.

## 🔗 Riferimento per sviluppatori

- [Importatori Scalable Capital](../../../developer/backend/brim/scalable.md)
- [Elenco dei provider BRIM](../../../developer/backend/brim/providers_list.md)
- [Dire il perché con un codice](../../../developer/architecture/patterns/brim_plugin_guide.md#cannot-parse-detail): i rifiuti dei due importatori
