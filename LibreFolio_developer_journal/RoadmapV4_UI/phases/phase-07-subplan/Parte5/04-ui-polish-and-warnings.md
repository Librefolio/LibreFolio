# Prompt per Agente: UI Polish & Migliorie Warning (Blocco 4)

## Contesto
Siamo nella fase di "polish" (rifinitura) dell'Import Wizard e della UI generale. I flussi core (Directa Bollo, Matematica BTP) sono confermati e funzionanti. Questo blocco si concentra sulla correzione di problemi di reattività Svelte, piccole anomalie nelle API e un restyling di precisione dei componenti UI e della Modale di Warning.

## Task 1: Bug & Backend
1. **Reattività Creazione Broker (`BrokerModal` / `ImportWizard`):**
   Quando si crea un nuovo broker dalla modale (all'interno dell'Import Wizard), il broker viene creato a DB ma non appare nel dropdown e non viene auto-selezionato. 
   - *💡 Hint:* In `ImportWizardModal.svelte`, il componente `<BrokerModal>` attualmente ascolta solo l'evento `onclose`. Manca un listener `oncreated` (come invece c'è in `TransactionFormModal.svelte`) per intercettare il nuovo broker creato, aggiornare l'elenco locale e assegnarlo a `selectedBrokerId`.
2. **Upload API (`/api/v1/brokers.py` endpoint `/upload`):**
   - Attualmente ignora un'eventuale rinomina del file fatta dall'utente nello Step 1, mantenendo il nome originale del CSV.
   - L'endpoint si aspetta `broker_id` come Query Parameter in una chiamata POST (`broker_id: int = Query(...)`).
   - *💡 Hint:* Sposta `broker_id` e l'eventuale `custom_filename` nel `Form(...)` (FormData) per maggiore coerenza REST e per permettere al server di usare il nuovo nome invece del `file.filename` originale.
3. **Traduzione Mancante:**
   Aggiungi la chiave `table.filter.empty` nei file di traduzione (`en.json`, `it.json`, ecc.).

## Task 2: Modale Asset (`AssetModal.svelte`)
1. **Toggle "Stato Asset" (Footer):**
   - Sposta l'icona del tooltip *sopra* (o prima) il testo della label.
   - Sostituisci l'emoji `ℹ️` con l'icona SVG di lucide (`lucide-info`).
   - Rendi la label dinamica ("Attivo" se true, "Inattivo" se false).
   - Nel file di lingua, modifica il tooltip cambiando "e non vuoi" in "o non vuoi".
2. **Campo "Prezzo riferito a N asset" (`quote_base_quantity`):**
   - Aggiungi l'asterisco `*` alla label.
   - Sostituisci l'emoji `ℹ️` con l'icona SVG `lucide-info`.
   - Riduci il tooltip a: *"Per le obbligazioni è tipicamente quotato su base 100."*

## Task 3: Wizard UX (Step 3 e 4)
1. **Quick Search Badges (Suggerimenti di Ricerca):**
   - Il titolo "Cerca online" deve stare *sopra* i suggerimenti.
   - Aggiungi un'icona lente di ingrandimento (SVG) prima del testo "Suggerimenti".
   - Formatta le label dei badge con prefisso (es. `Ticker: EXXY`, `ISIN: DE000...`). Quando cliccati, l'input deve popolarsi solo col valore.
   - Arrotonda i badge (`rounded-full`) e usa i colori generati dinamicamente da `color.ts` invece del grigio/blu di default.
2. **Dettagli Asset Card (Step 3 e 4):**
   - Aggiorna i badge (ISIN, Ticker) all'interno delle card dell'asset: falli `rounded-full` e usa `color.ts` per diversificare i colori.
3. **Mancanze Step 3:**
   - Inserisci il pulsantone globale "Preview File" in cima alla view dello Step 3.
   - Fixa l'icona del Broker nel riepilogo: se non ha favicon, usa il fallback generato (le iniziali) invece della valigetta generica fissa.

## Task 4: Modale di Conferma Warning (Miglioramento Workflow)
Attualmente la modale di conferma blocca correttamente l'avanzamento se ci sono warning, ma mostra solo un testo generico.
- **Azione:** Aggiungi un pannello collassabile (accordion/details) all'interno della modale.
- **Logica UI:** L'accordion deve raggruppare i warning per file. Per ogni file, mostra l'elenco puntato dei warning rilevati.
- **Preview Rapida:** Accanto al nome di ciascun file nell'accordion, aggiungi un pulsante "Preview" che permette di aprire la `FilePreviewModal` direttamente da lì, così l'utente può indagare il problema prima di decidere se premere "Continua lo stesso".
