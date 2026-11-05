# 📥 <img src="https://danskebank.fi/favicon.ico" alt=""> Danske Bank

!!! info "Alpha"

    Questo importatore è in **Alpha**: è stato realizzato a partire dagli export di un singolo conto, condivisi nella [issue #26](https://github.com/Librefolio/LibreFolio/issues/26). Se i tuoi file hanno un aspetto diverso, o una riga viene importata in un modo che sembra sbagliato, apri una nuova issue e menziona la #26.

LibreFolio importa il **conto di risparmio azionario** (*osakesäästötili*) di **Danske Bank Finland**. La banca lo suddivide in **due export**, e nessuno dei due è sufficiente da solo:

- i **movimenti titoli** (XLSX): operazioni, dividendi e scissioni, con quantità e prezzi — ma nessun deposito, prelievo o saldo;
- l'**estratto del conto** (CSV): ogni movimento di cassa e il saldo — ma nessuna quantità.

Quindi li carichi **insieme**: LibreFolio li legge come un unico **set di report**, abbina ogni operazione al suo pagamento e verifica i relativi saldi con quelli della banca.

---

## 📤 Cosa esportare {: #what-to-export }

| Export (nome in LibreFolio) | Dove in eBanking | Formato | Quanto indietro |
|:--|:--|:--|:--|
| **Movimenti titoli** (`Transactions.xlsx`) | **Sijoitukset → Tapahtumat** | XLSX | al massimo **un anno** per export |
| **Estratto del conto** | le transazioni del conto di cassa del tuo conto di risparmio azionario | CSV | fino a **cinque anni** |

- Movimenti titoli: l'**intero anno** che la banca consente.
- Estratto del conto: lo stesso periodo, a partire dal giorno precedente, e idealmente **qualche giorno oltre** la sua fine — le operazioni vengono pagate alcuni giorni lavorativi dopo essere state effettuate.
- Importa i file **così come scaricati**, senza salvarli di nuovo in Excel.

---

## 🧺 Carica entrambi i file insieme

1. Apri la **[Procedura guidata di importazione](how-to.md)**, trascina **entrambi** i file in **Carica**, assegnali al tuo broker Danske Bank e fai clic su **Avanti: Seleziona file**.
2. In **Seleziona file**, i due file formano **una sola scheda**, già spuntata: verifica che indichi **Completo**. Una nota sulla scheda ti dice cosa farà questa importazione.
3. Fai clic su **Analizza**: LibreFolio unisce i due file in un unico **file combinato** e lo analizza come un'unica riga. Il suo dettaglio, **Abbinamento titoli ↔ cassa**, mostra come le operazioni sono state abbinate ai loro pagamenti e perché qualche riga è stata esclusa.
4. Prosegui come al solito fino a **Importa N transazioni**.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="brokers" data-name="import-report-set-card" alt="Scheda del set di report Danske Bank in Seleziona file: una tabella per tipo di export, la cronologia dei file e Letto come nella sua intestazione" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="brokers" data-name="import-report-set-pairing" alt="Dettaglio del set in Analizza: Abbinamento titoli ↔ cassa, con i chip di esito e i motivi con il loro numero di righe" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

Anche i file caricati insieme dalla pagina [File](../../files/index.md#broker-reports) o dai **Report caricati** di un broker formano un set.

Gli export caricati con una versione di LibreFolio precedente alla 1.2 non appartengono ad alcun set e non possono essere letti da soli: la procedura guidata mantiene **Analizza** disabilitato finché uno di essi è selezionato. Carica di nuovo tutti gli export del set insieme, in un'unica volta, poi seleziona quel set; le copie vecchie possono essere eliminate.

### 🧩 Se manca un file

- Hai trascinato un solo file? **Avanti: Seleziona file** ti mantiene su **Carica**, indicando l'export mancante e il suo periodo: trascinalo lì — si unisce allo **stesso set** — e fai di nuovo clic su **Avanti: Seleziona file**.
- Vuoi proseguire senza? La scheda mostra **Manca un file** e offre **Carica il file mancante**. Nel frattempo il set spuntato blocca **Analizza**: togli la spunta al set per importare prima gli altri file.
- I file caricati in momenti diversi **non si uniscono mai**: carica di nuovo quello mancante con **Carica il file mancante** sulla scheda giusta, poi elimina la copia solitaria precedente.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="brokers" data-name="import-report-set-missing" alt="Scheda del set in Seleziona file con Manca un file: l'estratto del conto mancante, il periodo che deve coprire e Carica il file mancante" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

### 🔀 Come viene letto il set {: #how-the-set-is-read }

Normalmente non c'è nulla da cambiare: **Letto come**, nell'intestazione della scheda, mostra **Danske Bank (rilevato)**. Se un file non appartiene al set — ad esempio un estratto di un altro conto caricato per errore — scegli **Rimuovi dal set** nel suo menu **⋮**: il file si sposta, senza plugin, sotto **Altri file di questo broker**, dove togli la spunta al file. Per rimetterlo a posto, scegli *Danske Bank* nella sua colonna **Plugin** (la scelta compare una volta spuntato il file).

**Leggi i file uno per uno** non serve qui, dato che nessun altro importatore legge questi export: se l'hai scelto, rimetti a posto ogni file allo stesso modo. Un set spuntato solo in parte — la sua casella mostra un trattino — blocca **Analizza**: fai clic una volta sulla casella per togliere la spunta al set, due volte per spuntarlo per intero.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="brokers" data-name="import-report-set-read-as" alt="Scheda del set con la lista Letto come aperta: Danske Bank (rilevato), selezionato, e Leggi i file uno per uno" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="brokers" data-name="import-report-set-file-menu" alt="Scheda del set Danske Bank in Seleziona file con il menu ⋮ dell'estratto del conto aperto: Anteprima, Rimuovi dal set ed Elimina" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

---

## 🗓️ Importa almeno una volta all'anno

L'export dei movimenti titoli risale solo a un anno indietro, quindi importa **almeno una volta all'anno**, con ogni nuovo export dei movimenti titoli che arriva fino a dove terminava il precedente. Le sovrapposizioni non sono un problema: ciò che LibreFolio già possiede è nascosto nella **Revisione** (*N già in LibreFolio (nascosti)*) o arriva deselezionato come [duplicato](index.md#duplicate-detection). Hai saltato più di un anno? Vedi [Buchi](#gaps).

!!! warning "Set importati con LibreFolio 1.2"

    LibreFolio 1.2 registrava ogni operazione nel giorno in cui si muoveva il denaro; ora la registra nel giorno in cui l'hai effettuata, qualche giorno prima. Reimportate, quelle operazioni non sarebbero riconosciute come duplicate e verrebbero contate due volte. Quindi, una volta sola: elimina tutte le transazioni Danske Bank create da quelle importazioni — anche le correzioni contrassegnate con `gap_fix` — e importa di nuovo l'intero set, oppure importa solo dal giorno successivo all'ultimo giorno già importato: inizia da lì l'export dei movimenti titoli, e l'estratto del conto dal giorno prima, come dice [Cosa esportare](#what-to-export). Da quel momento in poi, le sovrapposizioni sono di nuovo accettabili.

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
| Qualsiasi altro accredito (solo il tuo denaro può essere depositato) | **Deposito** — un avviso li elenca |
| `Jakautuminen, vanha` / `uusi` (una scissione) | **Rettifiche** senza cassa — vedi [Scissioni](#demergers) |

- Ogni operazione è registrata nel **giorno in cui l'hai effettuata** (`Kauppapäivä`, la data di negoziazione): un acquisto fatto il 27 è un acquisto del 27, anche se la banca muove il denaro qualche giorno lavorativo dopo. Anche i dividendi e le scissioni prendono la loro data dall'export dei movimenti titoli; depositi, prelievi, imposte, commissioni e interessi mantengono la loro data nell'estratto del conto. Gli importi sono in **euro**, come li ha scritti la banca.
- I file non forniscono ISIN né ticker: conferma ogni titolo nella [mappatura degli asset](index.md#asset-mapping) della procedura guidata.
- **Ogni riga è rendicontata**: una riga esclusa — un pagamento mancante, un'operazione pagata dopo la fine dell'estratto del conto… — è comunque conteggiata nel dettaglio del set, con il suo motivo, ed elencata negli avvisi dell'importatore, in **finlandese** come i file. Due casi sono gestiti diversamente:
    - Le **prenotazioni** (`Varaus` nell'estratto del conto) sono blocchi che la banca sostituisce con il movimento contabilizzato, ed è quel movimento a essere importato. Sono conteggiate nel dettaglio del set come *prenotate, non contabilizzate*, ma non elencate negli avvisi: non c'è nulla da verificare.
    - **Uno stato che LibreFolio non conosce**: una riga il cui `Tila` è diverso da eseguito (`Toteutettu`) o contabilizzato (`Toteutunut`) — un ordine non eseguito, per esempio — viene esclusa con un **avviso** e un link per **aprire una issue su GitHub**. Aprine una, indicando il `Tila` che vedi, così l'importatore imparerà a gestirlo. Nel frattempo, se una di quelle righe è un movimento reale, aggiungila a mano.
- Controlla le operazioni abbinate che un avviso segnala perché i loro nomi differiscono.

### 💶 Le commissioni sono incluse negli importi delle operazioni

I file forniscono **un totale per operazione**, commissione inclusa, quindi il passo **Correzioni** chiede, per ogni acquisto e vendita:

- **Separare il prezzo dalle spese?**, poi **Applica correzione** — per un titolo quotato in euro, LibreFolio suggerisce la commissione probabile; la cifra esatta è nella conferma dell'operazione in eBanking;
- oppure **Mantieni come registrato**: l'operazione mantiene il suo intero importo (in entrambi i casi la tua cassa è corretta).

Ogni operazione richiede una scelta; **Mantieni le restanti N righe come lette** sistema le restanti con un clic.

### ✂️ Scissioni {: #demergers }

Una scissione (`Jakautuminen`) arriva come **rettifiche senza cassa**: la riga vecchia (`vanha`) rimuove le tue vecchie azioni, ogni riga nuova (`uusi`) ne aggiunge di nuove. Nell'editor, ogni riga nuova richiede il suo **costo per azione** (**Salva tutto** attende): il costo delle tue vecchie azioni × la percentuale della riga pubblicata dall'Amministrazione fiscale finlandese ([vero.fi](https://www.vero.fi/)), diviso per il suo numero di azioni.

---

## 🏁 Prima importazione: allinearsi con la banca {: #first-import-align-with-the-bank }

Alla prima importazione, tutto ciò che precede il primo giorno del tuo export dei movimenti titoli è riassunto in un **punto di partenza** alla fine del giorno precedente; da lì in poi, ogni movimento viene importato uno per uno. La scheda del set ti indica la data.

Dopo la **Revisione**, **Importa N transazioni** può aprire **Allinea con la banca**: confronta ciò che LibreFolio conterrà con ciò che dichiara la banca e propone ciò che chiude la differenza — un **Deposito** o un **Prelievo** che porta la cassa al saldo dell'estratto del conto, e una **Rettifica** per ogni posizione che i tuoi file provano.

LibreFolio registra un'operazione nel giorno in cui l'hai effettuata, mentre il saldo della banca cambia solo quando l'operazione viene pagata, qualche giorno lavorativo dopo. Perciò ogni confronto conta le operazioni importate già effettuate ma non ancora pagate in quel giorno, e entrambe le parti parlano della stessa cosa.

1. Le schede in alto mostrano ogni punto — il **Punto di partenza**, un punto **Dopo il buco** per ogni [buco](#gaps), la [Verifica di fine periodo](#end-of-period-check). Fai clic su una per vedere il suo confronto e solo le sue correzioni; fai di nuovo clic per vederle tutte.
2. Le correzioni, contrassegnate con `gap_fix`, sono **selezionate per impostazione predefinita**: togli la spunta a quelle che non vuoi (oppure usa **Seleziona tutto**, **Seleziona visibili**, **Deseleziona tutto**), poi fai clic su **Continua**.
3. Nell'editor, inserisci il **costo per azione** di ogni posizione contrassegnata come *costo da inserire* — il sito della banca mostra il prezzo medio di acquisto di ogni posizione. **Salva tutto** attende.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="brokers" data-name="import-wizard-gapfix-step" alt="Allinea con la banca: le schede Punto di partenza, Dopo il buco e Verifica di fine periodo sopra le correzioni proposte contrassegnate con gap_fix" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

Il passo si apre **solo quando c'è qualcosa da mostrare** — di solito non dopo un'importazione annuale che si sovrappone alla precedente. Anche la cronologia inserita a mano conta: viene proposta solo la differenza. Se il confronto con la banca fallisce, puoi **Continuare** senza correzioni.

### 📅 Se il tuo estratto del conto inizia più tardi {: #cash-statement-starts-later }

Se il tuo estratto del conto inizia **dopo** il primo giorno del tuo export dei movimenti titoli, il punto di partenza cade comunque il giorno precedente a quello dell'export dei movimenti titoli e prende il saldo da cui inizia il tuo estratto del conto.

- Un'operazione effettuata prima dell'inizio dell'estratto del conto e pagata al suo interno viene importata come di consueto, nel giorno in cui l'hai effettuata.
- Un'operazione già pagata prima dell'inizio dell'estratto del conto non è nell'estratto, quindi non può essere importata una per una: un avviso la elenca, e il dettaglio del set la conta come *regolata prima dell'inizio dell'estratto del conto*. Il suo denaro è già nel saldo da cui inizia l'estratto, quindi finisce nel punto di partenza, qualche giorno prima del giorno in cui l'hai effettuata. Anche le sue azioni, quando i tuoi file provano la posizione — un dividendo, per esempio; altrimenti verifica quel titolo sul sito della banca (vedi [Limiti](#limits)).

Per avere ogni operazione importata nel suo giorno, esporta l'estratto del conto dal giorno precedente all'export dei movimenti titoli, come dice [Cosa esportare](#what-to-export).

### ✅ Verifica di fine periodo {: #end-of-period-check }

L'ultima scheda confronta la tua cassa con il saldo dell'estratto del conto alla fine dell'ultimo periodo dei movimenti titoli — contando, come gli altri punti, le operazioni importate effettuate ma non ancora pagate in quel giorno: **Corrisponde** o **Non corrisponde**. Non viene **mai corretta**: la tua prossima importazione porta le operazioni degli ultimi giorni, mancanti dalla tua cassa fino ad allora. Se non corrisponde, aggiungi a mano il movimento che l'importazione ha escluso (vedi il dettaglio del set in **Analizza**).

---

## 🕳️ Buchi tra gli export dei movimenti titoli {: #gaps }

Un **buco** è un periodo che nessun export dei movimenti titoli copre mentre l'estratto del conto vi mostra delle operazioni — hai saltato più di un anno, o hai lasciato un vuoto tra due export dei movimenti titoli. Senza le quantità, quelle operazioni non possono essere ricostruite:

- i depositi, i prelievi, le imposte, le commissioni e gli interessi del buco sono importati con la loro data;
- le sue operazioni sono riassunte nelle correzioni **Dopo il buco**;
- i titoli comprati o venduti nel buco vanno verificati sul sito della banca e corretti a mano.

La scheda del set ti avverte di un buco del genere: se la banca ha ancora quel periodo, esportalo e caricalo insieme agli altri.

---

## ⚠️ Limiti {: #limits }

- **Titoli che non compaiono mai**: le posizioni sono provate solo da un dividendo, dalla riga vecchia di una scissione o da una vendita di più azioni di quante ne hai comprate (*almeno N*). Un titolo che non si è mosso e non ha pagato dividendi non può essere visto: verifica le tue posizioni sul sito della banca e aggiungi a mano quelle mancanti.
- **Capitale investito**: una correzione negativa di posizione, o la riga vecchia di una scissione, rimuove azioni senza abbassare il tuo capitale investito.
- **Niente passi indietro nel tempo**: un export dei movimenti titoli più vecchio della cronologia che LibreFolio possiede per il broker non viene importato; la scheda del set lo dice.
- **Correzioni precedenti**: se un nuovo set copre la data di una correzione `gap_fix` importata in precedenza, elimina quella correzione dopo l'importazione, come chiede la scheda — altrimenti la cassa conta due volte.

## 🔗 Riferimento per sviluppatori

→ [Importatore Danske Bank (riferimento per sviluppatori)](../../../developer/backend/brim/danske_bank.md)
