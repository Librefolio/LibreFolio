# 02 — Audit MkDocs EN: Transactions, Brokers, Import (BRIM)

> **Release 2 · Phase 0 · 05_cleanAudit · mkdocsAudit**
>
> Sola verifica. Nessuna correzione di codice, documentazione o traduzioni fa parte di
> questo audit. Vedi [00 — Indice](00_INDEX.md) per baseline, criterio di evidenza e
> tabella delle classificazioni.

## Baseline

| Campo | Valore |
|---|---|
| Manifest | [00_BASELINE](00_BASELINE.md) (persistito con l'audit) |
| Commit HEAD | `09cbb7e28f4e4e4bba9f9d40748b98e1876f5103` |
| Branch | `dev_release2` |
| Worktree | Dirty; confronto eseguito sul worktree, non solo su HEAD (vedi elenco `M`/`??` nel manifest) |
| Pagine assegnate | 38 (tutte `user/transactions/**/*.en.md` + tutte `user/brokers/**/*.en.md`) |

## Scope di questo report

Incluso: le 38 pagine elencate nella tabella di copertura sotto. Comportamento
verificato tramite: `backend/app/services/transaction_service.py`,
`backend/app/services/broker_service.py`, `backend/app/services/brim_provider.py`,
tutti i 29 plugin in `backend/app/services/brim_providers/`, `backend/app/schemas/brim.py`,
`backend/app/schemas/brokers.py`, `backend/app/schemas/transactions.py`,
`backend/app/schemas/uploads.py`, `backend/app/db/models.py`, `backend/app/api/v1/brokers.py`,
`backend/app/api/v1/transactions.py`, `backend/app/api/v1/uploads.py`, e il componente
frontend `frontend/src/lib/components/transactions/modals/ImportWizardModal.svelte` più
`BrokerSharingPanel.svelte` / `BrokerForm.svelte`.

Escluso da questo report (per istruzione): `docs/developer/**` (solo verificati i link
in uscita che puntano lì, non il loro contenuto), traduzioni IT/FR/ES, pagine AI Export,
FX, altre pagine utente, admin, teoria finanziaria, community, gallery.

Nota metodologica: molte pagine broker-specifiche condividono un template quasi
identico ("Beta — community feedback welcome" / "How to Export" / "Notes"). Le claim
generiche in quel template (CSV, beta, "built from sample exports") sono state
verificate una volta contro il registro provider e poi applicate a ciascuna pagina che
lo usa; le claim specifiche (formati, colonne, mapping) sono state tracciate nel
plugin backend corrispondente pagina per pagina.

## Copertura — 38 pagine

| # | Pagina | Disposizione | Note |
|---|---|---|---|
| 1 | `mkdocs_src/docs/user/brokers/import.en.md` | finding | F1, F2 |
| 2 | `mkdocs_src/docs/user/brokers/index.en.md` | verified | Nav/tab description coerente con `BrokerForm.svelte` e le tab del dettaglio broker |
| 3 | `mkdocs_src/docs/user/brokers/info.en.md` | verified | Overdraft/Shorting confermati in `transaction_service.py` |
| 4 | `mkdocs_src/docs/user/brokers/sharing.en.md` | finding | F4 |
| 5 | `mkdocs_src/docs/user/transactions/form.en.md` | verified | Tipi singoli/compositi, promote/split confermati |
| 6 | `mkdocs_src/docs/user/transactions/import/avanza.en.md` | verified | Template generico, CSV-only confermato |
| 7 | `mkdocs_src/docs/user/transactions/import/bitvavo.en.md` | verified | Template generico, CSV-only confermato |
| 8 | `mkdocs_src/docs/user/transactions/import/bux.en.md` | verified | Template generico, CSV-only confermato |
| 9 | `mkdocs_src/docs/user/transactions/import/coinbase.en.md` | verified | CSV-only, valuta letta per riga confermati |
| 10 | `mkdocs_src/docs/user/transactions/import/cointracking.en.md` | verified | Template generico, CSV-only confermato |
| 11 | `mkdocs_src/docs/user/transactions/import/credit_agricole.en.md` | verified | Tabella mapping causali verificata riga per riga nel plugin |
| 12 | `mkdocs_src/docs/user/transactions/import/cryptocom.en.md` | verified | Template generico, CSV-only confermato |
| 13 | `mkdocs_src/docs/user/transactions/import/degiro.en.md` | verified | CSV-only confermato |
| 14 | `mkdocs_src/docs/user/transactions/import/delta.en.md` | verified | Template generico, CSV-only confermato |
| 15 | `mkdocs_src/docs/user/transactions/import/directa.en.md` | verified | CSV **e** XLSX confermati nel plugin; il limite "3.000 righe" è un vincolo esterno di Directa, non verificabile nel repo |
| 16 | `mkdocs_src/docs/user/transactions/import/disnat.en.md` | verified | Template generico, CSV-only confermato |
| 17 | `mkdocs_src/docs/user/transactions/import/etoro.en.md` | finding | F6 |
| 18 | `mkdocs_src/docs/user/transactions/import/fineco.en.md` | verified | Varianti 11/15 colonne, Divisa/Cambio, bond sopra la pari, Aumento capitale — tutti confermati |
| 19 | `mkdocs_src/docs/user/transactions/import/finpension.en.md` | verified | Template generico, CSV-only confermato |
| 20 | `mkdocs_src/docs/user/transactions/import/freetrade.en.md` | verified | CSV-only confermato |
| 21 | `mkdocs_src/docs/user/transactions/import/generic-csv.en.md` | finding | F3 |
| 22 | `mkdocs_src/docs/user/transactions/import/how-to.en.md` | finding | F1, F2, F5 |
| 23 | `mkdocs_src/docs/user/transactions/import/ibkr.en.md` | verified | CSV-only confermato; Flex Query è UX esterna a IBKR, non verificabile nel repo |
| 24 | `mkdocs_src/docs/user/transactions/import/index.en.md` | finding | F5, F6, F7, F8 |
| 25 | `mkdocs_src/docs/user/transactions/import/intesa.en.md` | verified | `cost_basis_override` per-unit, keyword mapping, gate apertura (`txDate < info.openedAt`) — tutti confermati testualmente nel codice |
| 26 | `mkdocs_src/docs/user/transactions/import/investengine.en.md` | verified | Template generico, CSV-only confermato |
| 27 | `mkdocs_src/docs/user/transactions/import/investimental.en.md` | verified | Template generico, CSV-only confermato |
| 28 | `mkdocs_src/docs/user/transactions/import/parqet.en.md` | verified | Template generico, CSV-only confermato |
| 29 | `mkdocs_src/docs/user/transactions/import/rabobank.en.md` | verified | Template generico, CSV-only confermato |
| 30 | `mkdocs_src/docs/user/transactions/import/relai.en.md` | verified | Template generico, CSV-only confermato |
| 31 | `mkdocs_src/docs/user/transactions/import/revolut.en.md` | verified | La pagina dedicata dichiara solo CSV (non PDF) — coerente col codice; il claim PDF errato vive altrove (F5) |
| 32 | `mkdocs_src/docs/user/transactions/import/saxo.en.md` | verified | Template generico, CSV-only confermato |
| 33 | `mkdocs_src/docs/user/transactions/import/schwab.en.md` | finding | F9 |
| 34 | `mkdocs_src/docs/user/transactions/import/swissquote.en.md` | verified | Template generico, CSV-only confermato |
| 35 | `mkdocs_src/docs/user/transactions/import/traderepublic.en.md` | verified | Template generico, CSV-only confermato |
| 36 | `mkdocs_src/docs/user/transactions/import/trading212.en.md` | verified | Claim "Pie" è descrittivo/cautelativo, non contraddetto dal codice (righe Pie trattate come trade ordinari) |
| 37 | `mkdocs_src/docs/user/transactions/import/xtb.en.md` | verified | Template generico, CSV-only confermato |
| 38 | `mkdocs_src/docs/user/transactions/index.en.md` | verified | Rimanda correttamente a form.md e import/index.md |

**Totali**: 38 pagine · 31 `verified` · 7 `finding` · 0 `out-of-code-scope` · 0 link rotti
(controllo automatico dei link relativi `.md` interni alle 38 pagine, incluse le
destinazioni fuori scope in `developer/backend/brim/*` — tutte risolvono a un file
esistente).

---

## Reperti

### F1 — Numero di step del wizard BRIM non corrisponde alla UI reale

- **Pagine**: `brokers/import.en.md` (righe 43–54), `transactions/import/how-to.en.md`
  (riga 38: *"The guided wizard contains 5 operational steps"*; heading a riga 75
  `### Step 4: Asset Mapping & Duplicate Detection`; heading a riga 119
  `### Step 5: Bulk Staging Review`).
- **Claim**: `brokers/import.en.md` elenca 6 step nominati (Select File & Parser →
  Verify Headers & Mapping → Operation Analysis → Asset Resolution → Opening-Date Gate
  → Bulk Staging & Commit). `how-to.en.md` dichiara esplicitamente **5 step operativi**
  e li documenta come sezioni `###` distinte, ciascuna con proprio screenshot
  (`import-wizard-step4-resolution`, poi separatamente `import-bulk-staging` per lo
  "Step 5").
- **Controprova nel codice**: `frontend/src/lib/components/transactions/modals/ImportWizardModal.svelte:85`
  `const STEPS = ['step1Title', 'step2Title', 'step3Title', 'step4Title'] as const;` —
  la stepper bar (righe 2871–2911) e lo stato (`currentStep`, riga 91) mostrano
  **solo 4 step numerati**. Lo step 4 reale (`currentStep === 4`, righe 3334+, label
  i18n `importWizard.step4Title` = *"Review"*) contiene **in un'unica schermata**,
  come sezioni collassabili, sia la risoluzione asset sia il rilevamento duplicati
  sia (più sotto) la griglia di staging/commit — non sono step separati navigabili.
- **Classificazione**: Dettaglio obsoleto (struttura del workflow).
- **Gravità**: major — chi segue la numerazione documentata ("vai allo step 5") non
  trova quello step nella stepper bar reale (che si ferma a 4), e gli screenshot
  referenziati come step separati sono in realtà sotto-sezioni della stessa schermata.
- **Confidenza**: alta (citazione letterale di `STEPS` e dei blocchi `{:else if currentStep === N}`).
- **Impatto**: utente confuso da un disallineamento numerico tra guida e prodotto;
  nessun rischio dati.
- **Direzione di correzione**: allineare le pagine a 4 step reali (Upload → Select
  Files → Parse → Review), oppure rinominare le sotto-sezioni dello step "Review"
  senza usare numerazione "Step 4/Step 5" come se fossero pagine di wizard separate.

### F2 — Selezione del parser: descritta come azione nel wizard, in realtà configurata sul Broker

- **Pagine**: `brokers/import.en.md` (riga 45: *"Select File & Parser: Choose the
  statement file and select the appropriate parser configuration (e.g., Interactive
  Brokers, Degiro, Directa, Intesa Sanpaolo, Crédit Agricole, Charles Schwab, generic
  CSV, etc.)"*), `transactions/import/how-to.en.md` (sezione "⚙️ Step 2: Parser
  Configuration": *"The system automatically detects the broker format... you can use
  the Generic CSV parser to manually map your columns"*).
- **Claim**: implica che la scelta/configurazione del parser sia un passo dedicato e
  isolato del wizard di import (Step 1 o Step 2 a seconda della pagina).
- **Controprova nel codice**: il parser predefinito è un campo del **Broker**
  (`default_import_plugin`, `backend/app/db/models.py:405`, `backend/app/schemas/brokers.py:59,111,232`),
  impostato nel form di creazione/modifica broker tramite `ImportPluginSelect`
  (`frontend/src/lib/components/brokers/BrokerForm.svelte:229`). Nel wizard, lo step 1
  reale (`ImportWizardModal.svelte:2916`) chiede solo di caricare i file e assegnare un
  **broker** a ciascuno (non un parser); lo step 2 reale (righe 3018+) mostra i file già
  caricati raggruppati per broker con una colonna "plugin" per-file
  (`ImportWizardModal.svelte:2412-2444`, componente `ImportPluginSelect` con
  `compatiblePlugins` filtrati) che permette di **sovrascrivere** — non scegliere da
  zero — il parser altrimenti ereditato dal broker.
- **Classificazione**: Dettaglio obsoleto.
- **Gravità**: major — la narrativa "scegli il parser al passo 1" porta l'utente a
  cercare un selettore che in realtà non esiste in quello step; il meccanismo reale
  (default sul broker + override per-file al passo 2) non è documentato.
- **Confidenza**: alta.
- **Impatto**: nessun rischio dati; possibile confusione/tempo perso nella ricerca del
  controllo.
- **Direzione di correzione**: documentare che il parser è normalmente ereditato dal
  campo "Default Import Plugin" del broker (vedi guida Broker) e che può essere
  sovrascritto per singolo file allo step "Select Files" del wizard.

### F3 — Generic CSV: `TRANSFER`, `FX_CONVERSION`, `CASH_TRANSFER` documentati come valori `type` validi ma non importabili

- **Pagina**: `transactions/import/generic-csv.en.md`, tabella colonne (riga 42:
  *"`quantity` — Required for BUY/SELL/TRANSFER/ADJUSTMENT"*; riga 45: *"`asset` —
  Required for BUY/SELL/DIVIDEND/TRANSFER/ADJUSTMENT"*) e riga 48
  `### Valid \`type\` values` che elenca `... · TRANSFER · ADJUSTMENT · FX_CONVERSION ·
  CASH_TRANSFER`.
- **Claim**: implica che una riga CSV con `type=TRANSFER`, `type=FX_CONVERSION` o
  `type=CASH_TRANSFER` (con le colonne richieste popolate) venga importata come
  transazione composita.
- **Controprova nel codice**: `backend/app/services/brim_providers/broker_generic_csv.py`
  — `TYPE_MAPPINGS` (righe ~131-186) **non contiene affatto** le chiavi
  `"cash_transfer"` né `"fx_conversion"`; il lookup è un match esatto case-insensitive
  (`tx_type = TYPE_MAPPINGS.get(type_str.lower())`, riga 534) seguito da
  `raise ValueError(f"Unknown transaction type: '{type_str}'")` (riga 536) se non
  trovato — quindi `CASH_TRANSFER`/`FX_CONVERSION` come stringa letterale falliscono
  subito. `"transfer"` **è** mappato a `TransactionType.TRANSFER`, ma la riga viene
  comunque rifiutata più avanti: `if tx_type == TransactionType.TRANSFER: raise
  ValueError("TRANSFER type requires paired transactions with link_uuid. Please use
  manual entry or broker-specific plugin.")` (riga 597) e lo stesso per
  `FX_CONVERSION` (riga 601).
- **Classificazione**: Contraddizione.
- **Gravità**: critical — l'utente che segue la tabella per costruire un CSV con
  operazioni composite (trasferimenti asset, conversioni valuta, bonifici tra broker)
  vedrà **ogni riga di quel tipo fallire** l'import, senza che la pagina lo avverta.
- **Confidenza**: alta (citazione letterale di dizionario e `raise` con messaggio
  esplicito).
- **Impatto**: interruzione del workflow di import; nessuna perdita di dati già
  presenti (il parser rifiuta la riga, non la importa in modo silenzioso/errato), ma
  l'utente perde tempo e può interpretare l'errore come un bug.
- **Direzione di correzione**: rimuovere `TRANSFER`, `FX_CONVERSION`, `CASH_TRANSFER`
  dall'elenco "Valid type values" e dalle colonne richieste, oppure — se si intende
  implementarli — aggiungere il supporto nel plugin prima di documentarli.

### F4 — Broker Sharing: la percentuale di quota è documentata come assegnabile a Editor, ma il sistema la vincola a solo Owner

- **Pagina**: `brokers/sharing.en.md` — sezione "📊 Share Percentage" (riga 44:
  *"Each user with access to a broker has a share percentage (0% to 100%)"*), esempio
  "Joint Account" (righe 52–58: *"You (Owner): 50% / Spouse (Editor): 50%"*), tabella
  "Common Scenarios" (riga 76: *"Spouse / Partner | Editor or co-Owner, 50% share
  each"*).
- **Claim**: implica che un utente con ruolo **Editor** possa avere una quota
  percentuale diversa da zero (l'esempio "Joint Account" lo mostra esplicitamente).
- **Controprova nel codice**: `backend/app/schemas/brokers.py:397-403` —
  `BRAccessBulkItem.validate_share_for_role`: `if self.role != UserRole.OWNER and
  self.share_percentage > 0: raise ValueError(f"share_percentage must be 0 for role
  {self.role.value}. Only OWNERs can have ownership percentage.")`. Coerente con
  `backend/app/db/models.py:426-428` (commenti: *"EDITOR: defaults to 0.00"*, *"VIEWER:
  defaults to 0.00"*). Anche la UI lo impone lato client:
  `frontend/src/lib/components/brokers/BrokerSharingPanel.svelte:643`
  (`{#if newRole === 'OWNER'}`, mostra lo slider percentuale solo per il nuovo utente
  se il ruolo è Owner) e riga 763 (`{#if editRole === 'OWNER'}` per la modifica di un
  accesso esistente); altrove nello stesso file la quota è forzata a `0` quando il
  ruolo non è `OWNER` (righe 206, 245).
- **Classificazione**: Contraddizione.
- **Gravità**: major — l'esempio guida ("Joint Account") descrive una configurazione
  che il backend rifiuta con un errore di validazione esplicito; un utente che la
  replica manualmente (via API o aspettandosi lo stesso risultato in UI) non riuscirà
  ad assegnare quota a un Editor.
- **Confidenza**: alta (validator con messaggio d'errore esplicito + guardia UI su due
  punti distinti).
- **Impatto**: pianificazione errata della configurazione di condivisione da parte
  dell'utente; nessun rischio sui dati già salvati.
- **Direzione di correzione**: riscrivere l'esempio "Joint Account" e la riga
  "Spouse/Partner" della tabella "Common Scenarios" usando due **Owner** con quote
  parziali (es. 50%/50%) invece di un Owner + un Editor con quota, e chiarire nel testo
  che solo il ruolo Owner può avere `share_percentage > 0`.

### F5 — Formato PDF documentato come accettato dal wizard/da Revolut, ma nessun plugin lo supporta

- **Pagine**: `transactions/import/how-to.en.md` (riga 42: *"This step accepts CSV,
  XLSX or PDF reports exported from your broker"*), `transactions/import/index.en.md`
  (tabella "Importer Capabilities", riga 242: colonna Format per **Revolut** =
  `PDF/CSV`).
- **Claim**: il wizard accetterebbe file PDF in generale, e nello specifico il plugin
  Revolut saprebbe leggere sia PDF sia CSV.
- **Controprova nel codice**: nessuno dei 29 plugin BRIM dichiara `.pdf` in
  `supported_extensions()` — verificato su tutti i file
  `backend/app/services/brim_providers/broker_*.py` (ognuno restituisce solo `.csv`,
  o `.csv/.xlsx` per Directa/Intesa/Crédit Agricole).
  `backend/app/services/brim_providers/broker_revolut.py:284-285`:
  `def supported_extensions(self) -> List[str]: return [".csv"]`. Anche l'uploader
  frontend dello step 1 filtra i file a `accept=".csv,.xlsx,.xls"`
  (`ImportWizardModal.svelte:2929`) — nessun `.pdf`. Il generico riferimento a "PDF" in
  `backend/app/services/brim_provider.py:99,157` è solo un esempio nella docstring
  astratta dell'interfaccia (*"Examples: ['.csv'], ['.csv', '.xlsx'], ['.pdf']"*),
  non un'implementazione concreta.
- **Classificazione**: Contraddizione.
- **Gravità**: major — un utente Revolut che segue la pagina di import generale si
  aspetta di poter caricare l'estratto conto in PDF (coerentemente anche con la pagina
  dedicata Revolut, che però correttamente richiede solo CSV — vedi voce "verified" #31
  in tabella) e viene bloccato dal filtro `accept` del browser prima ancora di
  raggiungere il backend.
- **Confidenza**: alta (nessuna eccezione trovata su 29 provider + accept attr esplicito).
- **Impatto**: blocco del flusso di import per un formato dichiarato ma inesistente;
  nessun rischio dati.
- **Direzione di correzione**: rimuovere "PDF" dalla frase generica dello step 1 e
  dalla cella Format di Revolut nella tabella (o implementare un parser PDF dedicato
  prima di documentarlo).

### F6 — Formato XLSX documentato per eToro (pagina dedicata e tabella capacità), ma il plugin è CSV-only

- **Pagine**: `transactions/import/etoro.en.md` (riga 15: *"Select the Excel or CSV
  export option"*; riga 25, box "Common Pitfalls": *"select the spreadsheet format
  (XLSX or CSV)"*), `transactions/import/index.en.md` (tabella, riga 239: colonna
  Format per **eToro** = `XLSX/CSV`).
- **Claim**: il plugin eToro leggerebbe sia file XLSX sia CSV.
- **Controprova nel codice**: `backend/app/services/brim_providers/broker_etoro.py`
  — docstring di modulo (riga 4): *"This plugin parses **CSV** exports from eToro
  (social trading platform)"*; `supported_extensions()` (riga 182) restituisce solo
  `[".csv"]`; l'implementazione usa il modulo `csv` della standard library (import a
  riga 30), nessuna libreria per Excel (`openpyxl`/`pandas.read_excel`) è importata.
- **Classificazione**: Contraddizione.
- **Gravità**: major — la stessa falsa capacità è ripetuta su due pagine indipendenti
  (pagina broker dedicata + tabella riepilogativa), aumentando la probabilità che
  l'utente esporti un XLSX da eToro e lo carichi aspettandosi che venga letto,
  ottenendo invece un rifiuto per estensione non supportata.
- **Confidenza**: alta.
- **Impatto**: blocco del flusso di import per un formato dichiarato ma inesistente.
- **Direzione di correzione**: correggere entrambe le pagine a "CSV" per eToro, oppure
  aggiungere supporto XLSX al plugin.

### F7 — Directa SIM: la tabella capacità sottostima il formato realmente supportato (omette XLSX)

- **Pagina**: `transactions/import/index.en.md`, tabella riga 240: colonna Format per
  **Directa SIM** = `CSV` (non menziona XLSX).
- **Claim implicita**: Directa SIM supporterebbe solo CSV.
- **Controprova nel codice**: `backend/app/services/brim_providers/broker_directa.py:179-180`
  `def supported_extensions(self) -> List[str]: return [".csv", ".xlsx"]`. La pagina
  dedicata `transactions/import/directa.en.md` è corretta e coerente col codice
  (*"Both CSV and XLSX (Excel) formats are supported — not ods"*), il che rende
  l'incoerenza interna al solo file `index.en.md`, in contraddizione con la sua
  pagina "sorella".
- **Classificazione**: Dettaglio obsoleto (omissione di capacità già documentata
  altrove e presente nel codice).
- **Gravità**: minor — la capacità reale è più ampia di quanto dichiarato in tabella
  (nessun blocco per l'utente), ma la tabella riassuntiva risulta meno accurata della
  pagina di dettaglio a cui rimanda.
- **Confidenza**: alta.
- **Impatto**: incoerenza informativa a basso rischio.
- **Direzione di correzione**: aggiornare la cella Format di Directa SIM a `CSV/XLSX`
  per allinearla al codice e alla pagina dedicata.

### F8 — Descrizione dei campi usati per il rilevamento duplicati incoerente tra le due pagine e imprecisa rispetto al modello

- **Pagine**: `transactions/import/index.en.md` (riga 282: *"BRIM checks for duplicate
  transactions based on **date, type, asset, quantity, and amount**"*) vs.
  `transactions/import/how-to.en.md` (riga 100: *"...find potential duplicates based
  on **type, date, amount, quantity, and description**"*).
- **Claim**: le due pagine elencano insiemi di campi-base diversi per lo stesso
  meccanismo, e `index.en.md` include "asset" come criterio di base.
- **Controprova nel codice**: `backend/app/schemas/brim.py`, classe
  `BRIMDuplicateLevel` (righe 90-108): *"1. POSSIBLE: type + date + quantity + cash
  match, but asset not resolved. 2. POSSIBLE_WITH_ASSET: POSSIBLE + asset
  auto-resolved... 3. LIKELY: POSSIBLE + identical non-empty description... 4.
  LIKELY_WITH_ASSET: LIKELY + asset auto-resolved"*. Il match di base è quindi
  **type + date + quantity + cash (amount)**; la descrizione è un criterio aggiuntivo
  che eleva POSSIBLE→LIKELY; l'asset risolto è una dimensione ortogonale che qualifica
  la variante "_WITH_ASSET" (più affidabile), non un criterio di base allo stesso
  livello di type/date/quantity/amount. La formulazione di `how-to.en.md` è quindi più
  vicina al modello reale (aggiunge correttamente "description"); quella di
  `index.en.md` è imprecisa (aggiunge "asset" come se fosse un criterio-base e omette
  "description").
- **Classificazione**: Dettaglio obsoleto.
- **Gravità**: minor — non cambia il comportamento percepito dall'utente (i badge
  UNIQUE/POSSIBLE/LIKELY funzionano comunque), ma le due pagine si contraddicono a
  vicenda su un dettaglio verificabile.
- **Confidenza**: media-alta.
- **Impatto**: nessuno sul funzionamento; solo accuratezza documentale.
- **Direzione di correzione**: allineare `index.en.md` alla formulazione di
  `how-to.en.md` (o entrambe alla lista esatta type/date/quantity/amount/description,
  specificando separatamente il ruolo dell'asset risolto nelle varianti `_WITH_ASSET`).

### F9 — Schwab: lo "skip" delle righe di riepilogo è descritto come rilevamento dedicato, ma è uno scarto generico per data non valida (e produce un warning visibile, non un'operazione silenziosa)

- **Pagina**: `transactions/import/schwab.en.md`, box "Common Pitfalls" (riga 26):
  *"Schwab CSV files have a specific layout with metadata lines at the bottom (usually
  starting with 'Transactions Total'). The BRIM parser **automatically detects and
  skips** these metadata lines."*
- **Claim**: implica un meccanismo di rilevamento specifico per le righe di
  metadata/riepilogo (tipo "Transactions Total") in fondo al file.
- **Controprova nel codice**: `backend/app/services/brim_providers/broker_schwab.py`
  non contiene alcun riferimento a "Transactions Total" né ad alcuna logica dedicata
  al footer. Le righe vengono scartate da un controllo **generico**: se la data della
  riga non è parsabile, il parser esegue `warnings.append(f"Row {row_num}: invalid
  date, skipping")` (riga 264) e prosegue (`continue`, riga 265). L'effetto pratico
  (il file importa comunque) coincide con quanto promesso, ma il meccanismo non è
  "rilevamento" del footer, e soprattutto **non è silenzioso**: ogni riga di
  riepilogo scartata produce un warning visibile nel riepilogo dello Step 3 (colonna
  `⚠️ Warnings` descritta in `how-to.en.md`), diversamente da quanto un lettore
  potrebbe dedurre da "automatically detects and skips" (che suggerisce un'esclusione
  invisibile e mirata).
- **Classificazione**: Dettaglio obsoleto.
- **Gravità**: minor — imprecisione senza esito funzionale: il file importa comunque
  e l'esito pratico coincide con quanto promesso; cambia solo la descrizione del
  meccanismo (scarto generico per data non valida, non un rilevamento dedicato del
  footer) e il fatto che l'operazione produce un warning visibile anziché essere
  silenziosa.
- **Confidenza**: media.
- **Impatto**: nessuno; possibile lieve sorpresa nel vedere warning per righe che il
  testo lascia intendere gestite "automaticamente" e implicitamente senza segnalazione.
- **Direzione di correzione**: riformulare come "righe non conformi al formato data
  (incluse quelle di riepilogo in fondo al file) vengono saltate con un warning, senza
  bloccare l'import", evitando il riferimento a un rilevamento specifico di
  "Transactions Total".

---

## Campioni verificati (evidenza positiva)

- `intesa.en.md`: *"the shipped check is `txDate < info.openedAt`, not `<=`"* →
  riscontro letterale in `ImportWizardModal.svelte:613`
  (`return info !== null && txDate !== '' && txDate < info.openedAt;`).
- `how-to.en.md`: *"the wizard automatically unchecks 'Likely' duplicates"* →
  `duplicateStatusAllowsAutoSelect` (`ImportWizardModal.svelte:280-281`) esclude
  esplicitamente lo stato `'likely'` dall'auto-selezione.
- `fineco.en.md`: varianti a 11/15 colonne, colonna `Divisa` per la valuta riga per
  riga, `Cambio` ignorato, bond rimborsato sopra la pari diviso in SELL alla pari +
  INTEREST sul surplus, `Aumento capitale` → ADJUSTMENT senza cassa — tutti
  confermati testualmente in `broker_fineco.py` (commenti e costanti alle righe
  27-53, 92-104, 177-358).
- `credit_agricole.en.md`: tabella di mapping causali (CEDOLA, ACQ.CONT.SU MERC.,
  SICAV: SOTTOSCR, FONDI: RIMBORSO, TITOLI SCADUTI, GIRO ALTRO DOSSIER/VERS.TITOLI) e
  tag `auto_cash` — tutti confermati in `broker_credit_agricole.py` (righe 23-34, 89-92,
  153, 343-404).
- `intesa.en.md`: `cost_basis_override` come valore **per-unit** ottenuto dividendo
  `Controvalore di carico fiscale €` per la quantità → confermato in
  `broker_intesa.py:371-392`.
- `generic-csv.en.md`: tabella colonne/alias (`date`, `type`, `quantity`, `amount`,
  `currency`, `asset`, `description` con relativi sinonimi IT/EN/altre lingue) →
  corrispondenza pressoché 1:1 con `HEADER_MAPPINGS` in `broker_generic_csv.py:52-114`.
  (I valori `type` validi elencati sono invece parzialmente errati — vedi F3.)
  <br>*Nota incrociata*: la stessa evidenza di codice (`broker_generic_csv.py`) copre
  sia questo campione positivo sia il reperto F3; non duplicare.
- `transactions/form.en.md`: tipi singoli (BUY/SELL/DIVIDEND/INTEREST/DEPOSIT/
  WITHDRAWAL/FEE/TAX/ADJUSTMENT) e compositi (TRANSFER/CASH_TRANSFER/FX_CONVERSION),
  funzionalità "Promote"/"Split" → confermati in `backend/app/db/models.py:270-281,
  592-594` e `backend/app/services/transaction_service.py:631` (`promote_transfer`),
  `backend/app/schemas/transactions.py:902,917` (`TXSplitBatchItem`,
  `TXPromoteBatchItem`).
- Controllo automatico dei link relativi `.md` in tutte le 38 pagine (incluse le
  destinazioni verso `developer/backend/brim/{architecture,generic_csv,providers_list}.md`,
  fuori scope di contenuto ma dentro scope di navigazione): 0 link rotti.

## Claim non verificabili / ambigue

- **Vincoli quantitativi esterni al broker** (es. Directa: *"export covers up to 3,000
  rows per file"*; Crédit Agricole: *"limita quante righe/mesi puoi esportare"*): sono
  comportamenti dell'interfaccia esterna del broker, non della codebase LibreFolio —
  non verificabili nel repository. Non trattati come reperto.
- **UX di terze parti** (istruzioni passo-passo per ottenere l'export da IBKR, Degiro,
  eToro, Revolut, Coinbase, Trading212, ecc. — menu, pulsanti, percorsi nel portale del
  broker): per definizione esterne al repository, non verificabili localmente. Idem
  per lo screenshot placeholder "[Screenshot Placeholder: ...]" presenti in diverse
  pagine (avanza/coinbase/degiro/etoro/revolut/schwab/trading212 ecc.) — la loro
  presenza indica solo materiale incompleto, non un'affermazione falsificabile.
  Non trattati come reperto in questo report (non pertinenti a comportamento
  backend/frontend).
- **eToro — "CFD... cost basis and WAC logic might require manual validation"**:
  claim cautelativa/qualitativa che non specifica un comportamento verificabile in
  modo univoco nel codice (nessuna distinzione esplicita CFD/non-CFD nel plugin);
  non contraddetta né confermabile con sicurezza — lasciata come "non verificabile".
- **Trading212 — gestione "Pies"**: il plugin non ha logica dedicata alle "Pies" (nessun
  riferimento nel codice), ma la claim descrive un comportamento passivo ("le
  righe delle Pie sono riportate come trade separati sui singoli asset sottostanti, il
  parser le processa automaticamente" — cioè non serve logica speciale). Non
  contraddetta; lasciata come plausibile/non verificabile in modo stringente.
- **Coinbase — "Supports major fiat base currencies (USD, EUR, GBP)"**: il codice
  legge la valuta dalla colonna del CSV riga per riga con default `EUR` se assente
  (`broker_coinbase.py:240`); non c'è una lista bianca di valute che confermi o smentisca
  specificamente USD/GBP. Trattata come plausibile/non verificabile.

## Riepilogo per gravità e classificazione

| Gravità | Reperti |
|---|---|
| critical | F3 |
| major | F1, F2, F4, F5, F6 |
| minor | F7, F8, F9 |

| Classificazione | Reperti |
|---|---|
| Contraddizione | F3, F4, F5, F6 |
| Dettaglio obsoleto | F1, F2, F7, F8, F9 |
| Omissione | — |
| Limite non documentato | — |
| Navigazione/link | — (0 link rotti rilevati) |
| Non verificabile | Vedi sezione dedicata sopra (non conteggiate come reperti) |

**Pagine coinvolte in almeno un reperto**: 7 di 38 (`brokers/import.en.md`,
`brokers/sharing.en.md`, `transactions/import/generic-csv.en.md`,
`transactions/import/how-to.en.md`, `transactions/import/index.en.md`,
`transactions/import/etoro.en.md`, `transactions/import/schwab.en.md`).
**Pagine verificate senza reperti**: 31 di 38, incluse tutte le pagine broker
"stub" beta (template condiviso, verificato una volta contro il registro provider) e
le pagine broker con mapping dettagliato più a rischio (`fineco.en.md`,
`credit_agricole.en.md`, `intesa.en.md`, `directa.en.md`, `revolut.en.md`), risultate
accurate rispetto al codice attuale.

## Drift post-baseline

Nessuna modifica rilevata ai file toccati durante questa sessione (solo lettura); le
modifiche dirty già presenti nel worktree alla baseline (elencate nel manifest) non
intersecano i file di codice citati come controprova in questo report (transazioni,
BRIM, broker), ad eccezione di `backend/app/services/transaction_service.py` e
`backend/app/services/brim_providers/broker_generic_csv.py`, che risultano `M`
(modificati) nel worktree dirty rispetto a HEAD. Le citazioni di questo report sono
tratte dal contenuto **corrente del worktree** (coerente con la policy di baseline
dichiarata in [00 — Indice](00_INDEX.md)), non da HEAD puro; un futuro `git diff HEAD`
su questi due file potrebbe invalidare le righe citate per F3 e per gli overdraft/
shorting citati nella riga di copertura di `brokers/info.en.md` — da ri-verificare se
quelle modifiche vengono confermate/mergiate.

## Stato remediation — Block 3 (2026-08-05)

I conteggi sopra restano lo snapshot dell'audit. Il manuale inglese corrente e'
stato riallineato al codice per i seguenti reperti:

| Reperti | Stato | Esito |
|---|---|---|
| F1, F2 | ✅ Aggiornato | Documentato il flusso BRIM a quattro step, il parser compatibile di default e l'override per file. |
| F7 | ✅ Gia' allineato | La pagina Directa gia' documentava i formati CSV e XLSX; nessuna modifica forzata. |
| F8 | ✅ Aggiornato | Descritti i bucket di duplicati possibili/probabili senza esporre label interne. |
| F9 | ✅ Aggiornato | Chiarito che righe metadata, invalide o sconosciute vengono gestite genericamente con warning. |

Le traduzioni e la validazione MkDocs completa sono rinviate al batch multi-lingua.
