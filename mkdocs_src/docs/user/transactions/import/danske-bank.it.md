# 📥 <img src="https://danskebank.fi/favicon.ico" alt=""> Danske Bank

!!! info "Alpha"

    Questo importatore è in **Alpha**: è stato creato dalle esportazioni di un singolo conto, condivise nella [segnalazione #26](https://github.com/Librefolio/LibreFolio/issues/26). Se i tuoi file sembrano diversi, o una riga viene importata in un modo che sembra sbagliato, segnalacelo lì.

LibreFolio importa il **conto di risparmio azionario** (*osakesäästötili*) di **Danske Bank Finland**. La banca lo divide in **due esportazioni**, e nessuna delle due è sufficiente da sola:

- i **movimenti titoli** (XLSX): operazioni, dividendi e scissioni, con quantità e prezzi — ma nessun deposito, prelievo o saldo;
- l'**estratto del conto** (CSV): ogni movimento di cassa e il saldo — ma nessuna quantità.

Quindi li carichi **insieme**: LibreFolio li legge come un unico **set di report**, abbina ogni operazione al suo pagamento e verifica i saldi rispetto a quelli della banca.

---

## 📤 Cosa esportare

| Esportazione (nome in LibreFolio) | Dove in eBanking | Formato | Quanto indietro |
|:--|:--|:--|:--|
| **Movimenti titoli** (`Transactions.xlsx`) | **Sijoitukset → Tapahtumat** | XLSX | al massimo **un anno** per esportazione |
| **Estratto del conto** | i movimenti del conto di cassa del tuo conto di risparmio azionario | CSV | fino a **cinque anni** |

- Movimenti titoli: l'**intero anno** che la banca consente.
- Estratto del conto: lo stesso periodo, dal giorno precedente, e idealmente **qualche giorno oltre** la sua fine — le operazioni vengono pagate alcuni giorni lavorativi dopo essere state effettuate.
- Importa i file **così come scaricati**, senza salvarli di nuovo in Excel.

---

## 🧺 Carica entrambi i file insieme

1. Apri la **[Procedura guidata di importazione](how-to.md)**, trascina **entrambi** i file in **Caricamento**, assegnali al tuo broker Danske Bank e fai clic su **Avanti: Seleziona file**.
2. In **Seleziona file**, i due file formano **una scheda**, già selezionata: controlla che indichi **Completo**. Una nota sulla scheda ti dice cosa farà questo import.
3. Fai clic su **Analizza**: LibreFolio unisce i due file in un unico **file combinato** e lo analizza come una riga. Il suo dettaglio, **Abbinamento titoli ↔ liquidità**, mostra come le operazioni sono state abbinate ai loro pagamenti e perché qualche riga è stata esclusa.
4. Procedi come al solito fino a **Importa N transazioni**.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="brokers" data-name="import-report-set-card" alt="Scheda del set di report Danske Bank in Seleziona file: una tabella per tipo di esportazione, la cronologia dei file e Leggi come nella sua intestazione" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="brokers" data-name="import-report-set-pairing" alt="Dettaglio Analizza del set: Abbinamento titoli ↔ liquidità, con i chip di esito e le motivazioni con il loro numero di righe" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

Anche i file caricati insieme dalla pagina [File](../../files/index.md#broker-reports) o dal modulo **Report caricati** di un broker formano un set.

Le esportazioni caricate con una versione di LibreFolio precedente alla 1.2 non appartengono ad alcun set e non possono essere lette da sole: la procedura guidata mantiene **Analizza** disabilitato finché una di esse è selezionata. Carica di nuovo tutte le esportazioni del set insieme, in un'unica soluzione, poi seleziona quel set; le vecchie copie possono essere eliminate.

### 🧩 Se manca un file

- Hai trascinato solo un file? **Avanti: Seleziona file** ti mantiene su **Caricamento**, indicando l'esportazione mancante e il suo periodo: trascinalo lì — si unisce al **medesimo set** — e fai di nuovo clic su **Avanti: Seleziona file**.
- Vuoi procedere senza? La scheda mostra **Manca un file** e offre **Carica il file mancante**. Nel frattempo il set selezionato blocca **Analizza**: deselezionalo per importare prima gli altri tuoi file.
- I file caricati in momenti diversi **non si uniscono mai**: carica di nuovo quello mancante con **Carica il file mancante** sulla scheda giusta, poi elimina la copia precedente e isolata.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="brokers" data-name="import-report-set-missing" alt="Scheda del set in Seleziona file che mostra Manca un file: l'estratto del conto mancante, il periodo che deve coprire e Carica il file mancante" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

### 🔀 Come viene letto il set {: #how-the-set-is-read }

Normalmente non c'è nulla da cambiare: **Leggi come**, nell'intestazione della scheda, mostra **Danske Bank (rilevato)**. Se un file non appartiene al set — ad esempio, l'estratto del conto di un altro conto caricato per errore — scegli **Rimuovi dal set** dal suo menu **⋮**: il file si sposta, senza un plugin, sotto **Altri file di questo broker**, dove lo deselezioni. Per rimetterlo, scegli *Danske Bank* nella sua colonna **Plugin** lì (la scelta appare una volta che il file è selezionato).

**Leggi i file uno per uno** qui non serve, dato che nessun altro importatore legge queste esportazioni: se lo hai scelto, rimetti ogni file allo stesso modo. Un set selezionato solo in parte — la sua casella mostra un trattino — blocca **Analizza**: fai clic una volta sulla casella per deselezionare il set, due volte per selezionarlo interamente.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="brokers" data-name="import-report-set-read-as" alt="Scheda del set con l'elenco Leggi come aperto: Danske Bank (rilevato), selezionato, e Leggi i file uno per uno" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="brokers" data-name="import-report-set-file-menu" alt="Scheda del set Danske Bank in Seleziona file con il menu ⋮ dell'estratto del conto aperto: Anteprima, Rimuovi dal set ed Elimina" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

---

## 🗓️ Importa almeno una volta all'anno

L'esportazione dei movimenti titoli va indietro solo di un anno, quindi importa **almeno una volta all'anno**, con ogni nuova esportazione dei movimenti titoli che arriva fino a dove terminava la precedente. Le sovrapposizioni vanno bene: ciò che LibreFolio già possiede è nascosto nella **Revisione** (*N già in LibreFolio (nascosto)*) o arriva deselezionato come [duplicato](index.md#duplicate-detection). Hai saltato più di un anno? Vedi [Lacune](#gaps).

---

## 📝 Cosa viene importato

| Nei tuoi file | Importato come |
|:--|:--|
| Un acquisto (`Määrä` positivo) e il suo pagamento `Osto …` | **Acquisto** |
| Una vendita (`Määrä` negativo) e il suo pagamento `Myynti …` | **Vendita** |
| `Tuotto` e il suo accredito | **Dividendo** |
| `Nosto osakesäästötililtä` | **Prelievo** |
| `Vero osakesäästötililtä` | **Imposta** |
| `Palvelumaksu…` (commissioni di servizio) | **Commissione** |
| `Korko…` (interessi) | **Interesse** |
| Qualsiasi altro accredito (solo il tuo denaro può essere versato) | **Deposito** — un avviso li elenca |
| `Jakautuminen, vanha` / `uusi` (una scissione) | **Rettifiche** senza cassa — vedi [Scissioni](#demergers) |

- Ogni transazione riceve la sua **data valuta** (il giorno in cui il denaro o le azioni si sono mossi) e il suo importo in **euro**, come l'ha scritto la banca.
- I file non forniscono ISIN o ticker: conferma ogni titolo nella [mappatura degli asset](index.md#asset-mapping) della procedura guidata.
- **Niente viene eliminato in silenzio**: le righe escluse — un pagamento mancante, un ordine non eseguito, un'operazione pagata dopo la fine dell'estratto del conto… — sono conteggiate nel dettaglio del set ed elencate negli avvisi dell'importatore, in **finlandese** come i file. Controlla le operazioni abbinate che un avviso segnala perché i loro nomi differiscono.

### 💶 Le commissioni sono incluse negli importi delle operazioni

I file forniscono **un totale per operazione**, commissione inclusa, quindi il passaggio **Correzioni** chiede, per ogni acquisto e vendita:

- **Separare il prezzo dalle spese?**, poi **Applica correzione** — per un titolo quotato in euro, LibreFolio suggerisce la commissione probabile; la cifra esatta è nella conferma dell'operazione in eBanking;
- oppure **Mantieni come registrato**: l'operazione mantiene il suo importo totale (in entrambi i casi la tua liquidità è corretta).

Ogni operazione richiede una scelta; **Mantieni le restanti N righe come lette** risolve il resto con un clic.

### ✂️ Scissioni {: #demergers }

Una scissione (`Jakautuminen`) arriva come **rettifiche senza cassa**: la riga vecchia (`vanha`) rimuove le tue vecchie azioni, ogni nuova riga (`uusi`) ne aggiunge di nuove. Nell'editor, ogni nuova riga necessita del suo **costo per azione** (**Salva tutto** lo attende): il costo delle tue vecchie azioni × la percentuale della riga pubblicata dall'Amministrazione fiscale finlandese ([vero.fi](https://www.vero.fi/)), diviso per il suo numero di azioni.

---

## 🏁 Primo import: allinea con la banca {: #first-import-align-with-the-bank }

Al primo import, tutto ciò che precede il primo giorno della tua esportazione dei movimenti titoli è riassunto in un **punto di partenza** alla fine del giorno precedente; da quel momento in poi, ogni movimento viene importato uno per uno. La scheda del set ti indica la data.

Dopo la **Revisione**, **Importa N transazioni** può aprire **Allinea con la banca**: confronta ciò che LibreFolio deterrà con ciò che dichiara la banca e propone ciò che chiude la differenza — un **Deposito** o un **Prelievo** che porta la liquidità al saldo dell'estratto del conto, e una **Rettifica** per ogni posizione che i tuoi file provano.

1. Le schede in alto mostrano ogni punto — il **Punto di partenza**, un punto **Dopo la lacuna** per ogni [lacuna](#gaps), il [Controllo di fine periodo](#end-of-period-check). Fai clic su uno per vedere il suo confronto e solo le sue correzioni; fai di nuovo clic per vederle tutte.
2. Le correzioni, contrassegnate con `gap_fix`, sono **selezionate per impostazione predefinita**: deseleziona quelle che non vuoi (oppure usa **Seleziona tutto**, **Seleziona visibili**, **Deseleziona tutto**), poi fai clic su **Continua**.
3. Nell'editor, inserisci il **costo per azione** di ogni posizione contrassegnata con *costo da inserire* — il sito web della banca mostra il prezzo medio di acquisto di ogni posizione. **Salva tutto** lo attende.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="brokers" data-name="import-wizard-gapfix-step" alt="Allinea con la banca: le schede Punto di partenza, Dopo la lacuna e Controllo di fine periodo sopra le correzioni proposte contrassegnate con gap_fix" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

Questo passaggio si apre **solo quando c'è qualcosa da mostrare** — di solito non dopo un import annuale che si sovrappone al precedente. La cronologia inserita manualmente conta: viene proposta solo la differenza. Se il confronto con la banca fallisce, puoi **Continuare** senza correzioni.

### ✅ Controllo di fine periodo {: #end-of-period-check }

L'ultima scheda confronta la tua liquidità con il saldo dell'estratto del conto alla fine dell'ultimo periodo dei movimenti titoli: **Corrisponde** o **Non corrisponde**. Non viene **mai corretto**: il tuo prossimo import porterà le operazioni degli ultimi giorni, mancanti dalla tua liquidità fino ad allora. Se non corrisponde, aggiungi manualmente il movimento che l'import ha tralasciato (vedi il dettaglio del set in **Analizza**).

---

## 🕳️ Lacune tra esportazioni dei movimenti titoli {: #gaps }

Una **lacuna** è un periodo che nessuna esportazione dei movimenti titoli copre mentre l'estratto del conto mostra operazioni al suo interno — hai saltato più di un anno o lasciato un buco tra due esportazioni dei movimenti titoli. Senza quantità, quelle operazioni non possono essere ricostruite:

- i depositi, i prelievi, le imposte, le commissioni e gli interessi della lacuna vengono importati con la loro data;
- le sue operazioni sono riassunte nelle correzioni **Dopo la lacuna**;
- i titoli acquistati o venduti nella lacuna devono essere controllati sul sito web della banca e corretti manualmente.

La scheda del set ti avvisa di un tale buco: se la banca ha ancora quel periodo, esportalo e caricalo con gli altri.

---

## ⚠️ Limiti {: #limits }

- **Titoli che non compaiono mai**: le posizioni sono provate solo da un dividendo, dalla riga vecchia di una scissione, o da una vendita di più azioni di quelle acquistate (*almeno N*). Un titolo che non si è mosso e non ha pagato dividendi non può essere visto: controlla le tue posizioni sul sito web della banca e aggiungi manualmente quelle mancanti.
- **Capitale investito**: una correzione di posizione negativa, o la riga vecchia di una scissione, rimuove azioni senza ridurre il tuo capitale investito.
- **Niente viaggi indietro nel tempo**: un'esportazione dei movimenti titoli più vecchia della cronologia che LibreFolio detiene per il broker non viene importata; la scheda del set lo dice.
- **Correzioni precedenti**: se un nuovo set copre la data di una correzione `gap_fix` importata prima, elimina quella correzione dopo l'import, come chiede la scheda — altrimenti la liquidità viene conteggiata due volte.

## 🔗 Riferimenti per sviluppatori

→ [Importatore Danske Bank (riferimenti per sviluppatori)](../../../developer/backend/brim/danske_bank.md)
