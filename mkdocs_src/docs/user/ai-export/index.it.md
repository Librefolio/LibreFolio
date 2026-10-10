# 🧠 AI Export

AI Export copia i tuoi dati LibreFolio come testo pronto da incollare, con una domanda mirata se ne vuoi
una, così puoi chiedere all'assistente AI che preferisci informazioni sul tuo portafoglio, su un broker, su un asset o su una
coppia di valute. LibreFolio stesso non contatta mai un servizio AI.

---

## 🎯 A cosa serve

- **Rivedere con dati reali**: un broker, una posizione, una coppia di valute e la tua esposizione ad essa.
- **Pianificare**: investimenti ricorrenti, un ribilanciamento, o come le minusvalenze in scadenza potrebbero compensare le plusvalenze.
- **Spiegare**: cosa ha determinato la tua performance, asset per asset, con fonti datate.
- **Conservare un'istantanea**: solo i fatti, pronti per la tua domanda.

Ciò che copi è contesto fattuale, non consulenza di investimento.

---

## 🚀 Aprilo

Seleziona **AI Export** (:material-brain:) nella barra degli strumenti di una di queste pagine:

| Pagina | Cosa copre l'esportazione | Guida |
| :--- | :--- | :--- |
| **Dashboard** | Il tuo portafoglio, come lo mostra la dashboard | [Portafoglio](portfolio.md) |
| Una pagina di dettaglio **Broker** | Solo quel broker | [Broker](broker.md) |
| Una pagina di dettaglio **Asset** | Quell'asset e, se lo detieni, la tua posizione | [Asset](asset.md) |
| Una pagina di dettaglio **FX** | Quella coppia di valute e la tua esposizione diretta ad essa | [FX](fx.md) |

L'esportazione è datata all'**ultimo giorno dell'intervallo di date della pagina**: sposta quella data per esportare un
momento precedente.

---

## 🧭 Scegli cosa esportare

Il pannello si apre su una scelta pronta all'uso: cambia solo ciò che ti serve.

### 📤 Passaggio 1: Scegli il tipo di esportazione

Sotto **Tipo di esportazione**:

- **Esporta dati** copia solo i fatti: conserva un'istantanea, oppure fai la tua domanda.
- **Richiedi analisi** aggiunge una domanda mirata, regole per verificare i dati e la
  struttura della risposta attesa.

### 🗂️ Passaggio 2: Scegli un dataset o un'analisi

Apri **Dataset o analisi**: ogni voce ha una descrizione di una riga. Ogni pagina offre un'esportazione dati generale,
una cronologia di mercato dettagliata e da due a quattro analisi, elencate nelle guide sopra.

### 🔍 Passaggio 3: Imposta il livello di dettaglio

Scegli **Compatto**, **Standard** (predefinito) o **Completo**. Tutti e tre coprono gli stessi asset,
indicatori e periodo; mantengono solo più o meno cronologia. **Completo** può essere molto lungo.

### 📅 Passaggio 4: Imposta il periodo AI

Scegli **3M** (predefinito), **6M**, **1Y** o **Personalizzato** (giorni, settimane, mesi o anni), con fine
alla data di esportazione. Se LibreFolio ha meno cronologia, l'esportazione viene contrassegnata come parziale: non
inventa mai prezzi né usa quelli futuri.

### 📝 Passaggio 5: Aggiungi note (solo analisi)

Con **Richiedi analisi**, aggiungi contesto o domande in **Note per l'AI**: un budget mensile, un'allocazione
obiettivo, ciò che ti preoccupa. L'AI le legge come informazioni, non come nuove regole.

### 📋 Passaggio 6: Copia

Seleziona **Copia AI Export**. Dopo **Preparazione dell'esportazione…**, un messaggio conferma la copia con la sua
dimensione stimata.

??? warning "📏 Prompt lungo — quando il testo è lungo"

    Il pannello mostra prima la **Dimensione finale del prompt** con un avvertimento. Scegli **Usa compatto** per un
    testo più breve (non mostrato su Compatto), oppure **Copia comunque**: le stesse impostazioni copiano poi senza
    chiedere per un po'.

LibreFolio ricorda le tue ultime scelte su ogni pagina per alcuni minuti; la disconnessione le azzera.

---

## 🤖 Incollalo nel tuo assistente AI

Copi testo semplice: una breve intestazione (cosa è stato esportato, la data, il periodo, la valuta e il livello
di dettaglio) e i tuoi dati in tabelle compatte. **Richiedi analisi** aggiunge la domanda e la struttura della
risposta attesa attorno ad essi.

1. Apri una nuova chat in un assistente AI di cui ti fidi per i dati finanziari.
2. Incolla il testo e invialo. Con **Richiedi analisi**, la domanda è già inclusa.
3. Rispondi alle domande dell'AI: all'AI viene detto di chiedere solo ciò che cambia il risultato (un budget, un
   obiettivo, la tua situazione fiscale) e di non indovinarlo mai.

Da sapere:

- Con **Richiedi analisi**, all'AI viene chiesto di rispondere nella lingua dell'interfaccia di LibreFolio e
  di tenere i tuoi dati separati dalla sua interpretazione.
- Le analisi **Performance e fattori di mercato** richiedono un assistente che possa cercare sul web;
  senza di esso, la risposta lo dice invece di inventare fonti.
- Asset, broker, coppie di valute e lotti appaiono come codici brevi (A1, B1, F1, L1) spiegati nel
  testo; all'AI viene chiesto di rispondere con i nomi reali.
- Un'analisi può suggerire un'ulteriore esportazione in **Dati aggiuntivi LibreFolio**, con l'indicazione di dove
  trovarla. Se l'AI la chiede, copia anche quell'esportazione e incollala nella stessa chat.

---

## 🔒 Privacy

- LibreFolio non invia l'esportazione da nessuna parte: la scrive solo negli appunti.
- Il testo contiene i tuoi **dati reali** e i nomi dei tuoi broker e asset, anche mentre
  la modalità privacy è attiva.
- Ogni pagina esporta solo il proprio ambito:
    - **Dashboard**: i broker che possiedi con una quota superiore allo 0%, ristretti dal filtro broker;
    - **Broker**: solo quel broker;
    - **Asset** e **FX**: ogni broker che puoi aprire, inclusi i broker condivisi con te.
- Controlla il testo prima di incollarlo ovunque; un promemoria appare dopo ogni copia.

---

## 🛠️ Quando qualcosa va storto

- **AI Export è inattivo**: la pagina è ancora in caricamento oppure, nella dashboard, non possiedi alcun broker
  con una quota superiore allo 0%.
- *Questa selezione non è applicabile ai dati correnti.*: scegli un'altra analisi.
  **Revisione posizione** richiede una posizione nell'asset; **Impatto esposizione FX** richiede liquidità o una
  posizione collegata alla coppia.
- Un messaggio che termina con *Aggiorna e riprova.*: ricarica la pagina.
- *L'accesso agli appunti non è disponibile. Controlla i permessi del browser.*: consenti l'accesso agli appunti per
  LibreFolio nel tuo browser.

---

## 🔗 Correlati

- 🛠️ **[Come funziona AI Export](../../developer/architecture/patterns/ai_export_snapshot.md)** — per sviluppatori
