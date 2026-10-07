# Piano — fase 00, 31: il plugin DEGIRO (issue #35)

> **Stato**: ✅ implementato (2026-10-07); checkpoint al coordinatore, FROZEN (§11.6). Via del developer portato dal coordinatore: D1–D10 come raccomandate (§0.1).
>
> - Mandato: coordinatore («Release 2 backlog analysis», `c8328a01-…`), con le decisioni del developer (§0). La sua analisi: `…/c8328a01-…/files/analisi-degiro-35.md` §1–§9.
> - Workstream L. Ramo `e-alfy-l-danske-bank`, base `d07412899` (fast-forward del developer alle 12:57). Corsia 6156/6166, `--data-dir /tmp/librefolio-r2-l`, un comando alla volta. La coverage completa gira nella 6150: un E2E in timeout si rilancia da solo prima di concludere.
> - Ricerca multilingue (fonti open source, citate): nella sessione di L, `files/degiro/research-degiro-strings.md`; sintesi in §1.8.

## 0. Il mandato (decisioni del developer, dal coordinatore)

1. Estratto conto letto **per posizione**, in qualunque lingua (12 colonne): importo dalla colonna senza nome dopo «Change/Mutatie», valuta da «Change/Mutatie», riga per riga; saldo ignorato. Il campione olandese resta supportato e diventa il test di non regressione (importi, valute, tipi).
2. Lingua dei messaggi dall'intestazione (guida `:420-428`), decisa su più colonne («Datum» è NL e DE); inglese di riserva.
3. Compravendite e commissioni riconosciute **dalla struttura**; dividendi, tasse, versamenti, prelievi, interessi con una tabella multilingue (confini di parola, tasse prima dei dividendi).
4. Cambi → coppie `FX_CONVERSION` con `link_uuid`; accoppiate per Order Id, o per data e ora; Order Id che va a capo su una riga vuota; AutoFX già compreso.
5. Accrediti promozionali e di cortesia → INTEREST, descrizione originale.
6. Righe interne saltate senza rumore (sweep, trasferimenti flatex, prenotazioni, informative senza importo, interessi a zero); **riga sconosciuta → avviso** con la riga d'origine, nella lingua del file. «Flatex Interest Income» non va perso.
7. Transactions.csv: DEGIRO lo riconosce (priorità sopra il generico), non importa nulla, avviso chiaro («elenco degli ordini: LibreFolio legge l'Account Statement»). La regola BRIM (~`:65`) si aggiorna come **estensione**.
8. Numeri: un tasso con una virgola e 4 decimali (esempio sintetico: `1,1734`) diventa 11734, va corretto; «il separatore decimale è lo stesso in tutto il file».
9. Doc: `degiro.en.md` via docs-writer (solo EN, niente stamp), regola BRIM nella guida.
10. Nessun avviso di reimport; la riga di CHANGELOG la scrive il coordinatore (io la propongo).

Test: test-author, rossi prima, file nuovo `test_brim_degiro.py`; di `test_brim_providers.py` solo le righe DEGIRO (P lavora intorno a `:1563`); campione inglese **sintetico**; registrazione nel runner mia, solo la mia voce.

### 0.1 L'approvazione (2026-10-07)

- **Coordinatore** (testuale, in sintesi fedele): «Piano approvato dal developer, in modalità interattiva. Valgono D1–D10 come le hai raccomandate.»
- **Developer**, note testuali:
  - D1: «riguardo al separatore, credo sia per colpa dell'utente che ha fatto il collage, ma se riusciamo a essere robusti a questo caso, tanto meglio». → Il collage è un **artefatto del campione**, non dei file DEGIRO reali (la ricerca lo conferma: il campione coincide col campione pubblico misto di `dickwolff/Export-To-Ghostfolio`); la regola valore per valore resta, per robustezza.
  - D3: «riguardo alle gambe doppie per i cambi valuta, ci sta, cerca di fare una ui simile a bulk transaction quando la transazione è doppia». → Prima del passo ④ si studia come `TransactionBulkModal.svelte` mostra e gestisce le coppie (TRANSFER, FX_CONVERSION), e si riusano linguaggio visivo e componenti.
- **Concessioni**: `broker_degiro.py`; `degiro-account-en.csv`; `test_brim_degiro.py`; la categoria in `test_brim_api.py`; la voce `brim-degiro` nel runner; `test_brim_providers.py` solo `:1062`; `ImportWizardModal.svelte` (D3; M ripara solo `gallery.spec.ts:2222`); lo spec E2E `tx-import-degiro` (D10, test-author); doc EN via docs-writer (`degiro.en.md`, guida BRIM solo aggiunte, `providers_list.md`, tolte a Q). Una riga in `import/how-to.en.md` passa dal coordinatore (pagina di Q).
- **CHANGELOG** del coordinatore: all'handoff la riga aggiornata (§10). Prima del commit: FROZEN e handoff.

## 1. Stato verificato (codice a `d07412899`)

### 1.1 Il plugin oggi (`broker_degiro.py`, 465 righe)

- `can_parse` vuole `datum`, `tijd`, `isin`, `omschrijving` nella prima riga (`:272-291`): solo olandese. Sonda: i due file dell'utente → `compatible_plugins = []`, nessun plugin li prende; con l'intestazione tradotta in NL → DEGIRO.
- `DictReader` (`:312`): le due colonne senza nome hanno la stessa chiave `""`, vince il saldo → importi sbagliati; la valuta è cercata nella colonna sbagliata → sempre EUR.
- `TYPE_PATTERNS` (`:72`): `koop \d+` prima di `verkoop`, `^dividend` prima delle tasse → vendite come acquisti, ritenute come dividendi.
- `SKIP_PATTERNS` (`:107`): `flatex` (perde «Flatex Interest Income»), `courtesy` (perde gli accrediti), i cambi.
- `_parse_degiro_number` (`:138`): una sola virgola con >2 cifre → migliaia.
- **Baseline misurata** (script del coordinatore, log in `files/degiro/baseline_stats.log`): campione NL → 42 transazioni, 29 importi, 19 valute, 6 tipi sbagliati.

### 1.2 I file dell'utente (solo la struttura)

- `Account.csv`: `;`, CRLF, ASCII, 12 colonne, virgola decimale, date `GG-MM-AAAA`. Header `Date;Time;Value date;Product;ISIN;Description;FX;Change;;Balance;;Order Id`. 4 righe: interessi a zero (CZK), riga informativa senza importo, cash sweep, promo in ceco.
- `Transactions.csv`: 17 colonne, ISIN in 4ª posizione, colonne 9 e 11 senza nome, «Order ID» in fondo.

### 1.3 ⚠️ Il campione olandese è un collage

- Mescola **due formati di numero**: righe 2–30 con virgola decimale tra virgolette (`"27,80"`), righe 31–74 con punto decimale (`-97.93`, `9999.99`, `-1.2108`). Mescola anche le lingue delle descrizioni (NL, PT, FR, ES, EN) e ha una descrizione già rovinata dall'encoding (`CrÃ©dito`).
- Conseguenza su **decisione 8**: con «un solo separatore per file» il campione di non regressione si rompe (`-97.93` diventerebbe `-9793`). Proposta in §4 D1.

### 1.4 Le coppie `link_uuid`, da capo a fondo

- `TXCreateItem` accetta `link_uuid`; `FX_CONVERSION` lo esige, con `quantity = 0`, cassa ≠ 0, **senza asset** (`schemas/transactions.py:313-334`). `_create_transaction(**kwargs)` lo passa.
- Il wizard copia `t.tx` com'è (`ImportWizardModal.svelte`, `buildFinalTxList`) → il `link_uuid` arriva all'editor; la BulkModal accoppia gli import con lo stesso `link_uuid` (`linkPairedImportOps`).
- Il batch (`transaction_batch_stages.py:730-786`, `transaction_service.py:168-225`) vuole **esattamente 2** create per `link_uuid`, **stesso tipo**, **descrizione e tag identici** (`pairDescriptionMismatch`, `pairTagsMismatch`). Le due gambe DEGIRO hanno descrizioni diverse («Valuta Creditering» / «Valuta Debitering») → serve una descrizione comune.
- Il passo ④ del wizard non conosce le coppie: il checkbox cambia solo la sua riga. Una gamba tolta da sola arriva all'editor e fallisce con `linkUuidPairCount` → §4 D3.
- Nessun plugin emette ancora coppie (Swissquote salta le gambe, il generico le rifiuta): DEGIRO è il primo.
- I test generici chiedono `parse` **idempotente** e identico sulla copia Windows-1252 → il `link_uuid` deve essere deterministico e non dipendere dai byte del file.

### 1.5 Avvisi e lingua

- `BRIMNotice` (severity, `code`, `message`, `evidence: BRIMEvidence[]`, `context`); evidenza = tabella con intestazioni, righe, numeri di riga, commento.
- Il frontend traduce `importWizard.brimNotice.<code>` nella lingua della UI e ripiega sul `message` del plugin (`resolveBrimNotice.ts`). Oggi esiste una sola chiave (`ca_succession_transfer_in`) → codici `degiro_*` **senza chiave i18n** = il messaggio arriva nella lingua del file. Nessuna chiave i18n serve (vincolo «dopo O» non toccato).
- Nessun plugin oggi sceglie la lingua per file: DEGIRO sarebbe il primo (CA e Fineco lo dicono solo nel docstring).
- Danske raggruppa le righe escluse per motivo, un avviso per motivo con la tabella delle righe: lo stesso schema qui.

### 1.6 Test che toccano DEGIRO

- Nessun test fissa i valori sbagliati di oggi. In `test_brim_providers.py`: `:59` (import di `_parse_degiro_date`, `_extract_quantity_from_description`), `:1062` (DEGIRO senza `cannot_parse_reason`), `:1106`, `:1126/:1144` (date), `:1187` (quantità). Tenendo i due helper, cambia solo `:1062`, e solo con D8.
- `test_parse_produces_transactions`: ogni campione di un plugin deve dare ≥ 1 transazione → un campione dell'**elenco ordini** in `sample_reports/` lo farebbe fallire, e quel test è fuori dalle mie righe → il caso Transactions.csv vive nel test nuovo, come byte scritti in `tmp_path`.
- Il campione inglese nuovo entra da solo nei contratti generici (parse, schema, idempotenza, Windows-1252, rilevazione).
- Usi indiretti invariati: Danske (`FOREIGN_SAMPLES`), report set (`EXISTING_PLUGIN_CODES`), gap-fix (plugin a file singolo), populate (carica `degiro-export.csv`), E2E (il broker «DEGIRO» del mock, nessun parse).

### 1.7 Altro

- Un parse con 0 transazioni e un avviso → il file va in `parsed` con l'avviso salvato (`brokers.py:950-985`): la decisione 7 non chiede modifiche al core.
- La guida (`:154-156`): il tasso di cambio del report va **ignorato** → le gambe si riconoscono senza usarne il valore (§2.5).
- `degiro.en.md:29` (lingue) e `:34` (cambi «automaticamente processati») sono falsi oggi; `providers_list.md:8` dice «multi-language».
- `plugin_version` è il default `1.0.0` → bump a `2.0.0`: i file DEGIRO già analizzati mostrano «nuova analisi disponibile».
- Con la voce 8, dopo l'aggiornamento i file DEGIRO già caricati vengono rilevati di nuovo: quelli dell'utente offriranno DEGIRO senza ricaricarli.
- `_brim_io.read_rows` (righe come liste, encoding con ripiego) e `to_decimal_it` / `to_decimal_plain` coprono lettura e conversione: niente parser nuovi.

### 1.8 La ricerca multilingue (fonti)

Agente di ricerca, 20+ importer open source (C#, Python, TS, Java, Go) più l'estrattore PDF di Portfolio Performance; testo completo nella sessione di L (`files/degiro/research-degiro-strings.md`), con un link per ogni stringa.

- **Intestazioni dell'estratto conto** (12 colonne): verificate EN, NL, PT (3 fonti), ES (2), FR (1, export reale dichiarato), DE quasi (Order-ID incerto: `Order-ID`/`Auftrags-ID`); IT a bassa confidenza («pieced together»); CS solo da un PDF; PL, nordiche, EL, HU: nessuna fonte.
- **Elenco ordini**: due layout noti (19 colonne con AutoFX; 16–19 più vecchio con una valuta dopo ogni importo), più il 17 colonne inglese dell'utente; ISIN sempre in 4ª, colonne 9 e 11 senza nome.
- **Righe in lingue miste nello stesso file** (estratto ceco con descrizioni inglesi; PT con `flatex Deposit`): la tabella di parole vale per tutte le lingue su ogni riga, indipendente dalla lingua dei messaggi.
- **Gambe di cambio**: in ceco le due gambe hanno lo stesso testo (`FX vyúčtování konverze měny`), la direzione è solo nel segno → conferma D2. Tutti gli importer seri accoppiano per Order Id, o per data e ora quando manca.
- **Compravendite**: `<verbo> <qtà> <nome>@<prezzo> <VAL> (<ISIN>)` in tutte le lingue (Koop, Buy, Kauf, Achat, Compra, Acquisto, Venda, Nákup…); il tedesco vecchio usa `zu je` al posto di `@`.
- **Azioni societarie**: una compravendita dopo un prefisso con i due punti (`PRODUCTWIJZIGING :`, `AANDELENSPLIT:`, `AKTIENSPLIT:`, `ISIN-WIJZIGING:`, `FUSIE:`, `STOCK DIVIDEND:`, `DELISTING:`, conversioni dei fondi monetari) **non** è una compravendita → D5.
- **Mojibake reale** (`CrÃ©dito de divisa`): le parole si confrontano su un testo normalizzato (minuscole, accenti tolti, riparazione latin-1 → UTF-8); la descrizione salvata resta quella del file.
- **Prelievi**: `Processed Flatex Withdrawal`, `flatex Withdrawal` (EN, anche in un file PT), `flatex terugstorting` (NL), `Prelievo flatex` (IT) sono la forma normale dell'era flatex → D7 resta un avviso finché un export reale (chiesto all'utente) non chiarisce quale riga è il prelievo vero.
- **Tasse sulle transazioni** (`Transactiebelasting <paese>`, `London/Dublin Stamp Duty`) hanno l'Order Id → riconosciute come TAX prima della regola strutturale delle commissioni.

## 2. Il disegno proposto

### 2.1 Lettura

- `read_rows(file_path, delimiter=self.detect_csv_delimiter(file_path))` → liste di celle; niente `DictReader`.
- 12 posizioni: data, ora, data valuta, prodotto, ISIN, descrizione, FX, valuta del movimento, importo, valuta del saldo, saldo, Order Id.
- **Riga di continuazione** (data e ora vuote, almeno una cella piena): le celle piene si accodano a quelle della riga prima (l'Order Id `5925d76b-eb36-46e3-` + `b017-a61a6d03c3e7`). La riga unita tiene il numero della prima.

### 2.2 Riconoscimento

- **Account Statement**: intestazione di 12 colonne, 9ª e 11ª vuote, «isin» nella 5ª; prima riga di dati con data `GG-MM-AAAA` e ora `HH:MM`.
- **Elenco ordini**: ≥ 16 colonne, «isin» nella 4ª, 9ª e 11ª vuote, stessa prima riga di dati.
- Priorità 100 (oggi), sopra il generico (0).
- `cannot_parse_reason` (D8): una frase inglese per un file che sembra DEGIRO ma non ha la struttura attesa.

### 2.3 Numeri (D1)

- Valore per valore quando è certo: entrambi i separatori → l'ultimo è il decimale; un separatore ripetuto → migliaia; un separatore con 1, 2 o ≥ 4 cifre dopo → decimale; spazi e NBSP → migliaia.
- **Il separatore del file** (voto sugli importi certi delle colonne 9 e 11) decide **solo** i valori ambigui: un solo separatore con esattamente 3 cifre dopo (`1.000`, `49,785`).
- Conversione con `to_decimal_it` / `to_decimal_plain`.

### 2.4 Classificazione, in quest'ordine

1. Senza importo → saltata, senza rumore.
2. **Gambe di cambio** (§2.5).
3. **Compravendita**: ISIN, Order Id e la forma `<parola> <qtà> …@<prezzo> <VAL>`; BUY se l'importo è negativo, SELL se positivo (quantità negativa); quantità dalla forma.
4. **Commissione**: Order Id, importo negativo, né gamba né compravendita → FEE (con l'asset dell'ISIN, se c'è).
5. **Tabella di parole** multilingue, con i confini di parola: tasse prima dei dividendi, poi dividendi, versamenti, prelievi, interessi, accrediti promozionali → INTEREST, commissioni senza ordine (connessione…), righe interne da saltare (sweep, trasferimenti flatex, prenotazioni). Le stringhe arrivano da fonti citate (ricerca in corso, §8).
6. **Importo zero**: senza ISIN (interessi a zero) → saltata; con ISIN (cambio prodotto, dividendo in azioni) → D5.
7. Il segno deve combaciare col tipo (es. WITHDRAWAL negativo); se no → avviso «segno inatteso», non importata.
8. Il resto → **avviso «righe sconosciute»**, con le righe.

Data della transazione: la colonna 1, come oggi.

### 2.5 Le coppie di cambio (D2)

- **Gamba**: la riga con la colonna FX piena. Il valore del tasso non si usa mai (regola BRIM): conta solo che ci sia.
- **Controparte**: nello stesso gruppo (stesso Order Id; senza Order Id stessa data e ora), in un'altra valuta, col segno opposto, né compravendita né commissione; fra più candidate, la riga **adiacente**. Nel campione tutte e 6 le coppie sono adiacenti, dopo l'unione della continuazione.
- Senza controparte, o ambigua → avviso con le righe, niente importato.
- Due `FX_CONVERSION`: stesso `link_uuid`, **stessa descrizione** (le due originali unite, «Valuta Debitering / Valuta Creditering»), stessi tag, senza asset.
- `link_uuid` = `uuid5` di un hash del **testo decodificato** e dei numeri di riga della coppia: stabile fra due parse e sulla copia Windows-1252, diverso fra due file diversi.

### 2.6 Asset

- Come oggi: un id finto per ISIN (ripiego: nome del prodotto), con ISIN e nome estratti. Le gambe di cambio non hanno asset.

### 2.7 Lingua dei messaggi (D4)

- Vocabolario delle intestazioni per lingua; punteggio sulle colonne nominate; vince la lingua col punteggio più alto se ≥ 3 corrispondenze ed è unica; altrimenti inglese.
- Catalogo dei messaggi per lingua (codici `degiro_unknown_rows`, `degiro_unpaired_fx`, `degiro_unexpected_sign`, `degiro_quantity_unreadable`, `degiro_orders_list`, più quelli di D5), titoli e commenti dell'evidenza compresi.

### 2.8 L'elenco ordini

- `parse` → 0 transazioni e **un** avviso `degiro_orders_list`, nella lingua dell'intestazione: «è l'elenco degli ordini; LibreFolio legge l'Account Statement (Inbox → Account Statement)». Il file va in `parsed`.

### 2.9 Risultato atteso sul campione olandese (con le raccomandazioni di §4)

- **57 transazioni** (D6 approvata): DEPOSIT 2, FX_CONVERSION 12 (6 coppie), DIVIDEND 9, TAX 6, FEE 13 (8 per ordine, 4 di connessione, 1 di azione societaria), BUY 10, SELL 3, INTEREST 2.
- Saltate senza rumore: 4 informative, 3 sweep, 2 prenotazioni. Avvisi: `degiro_not_imported` per le righe 34, 35, 65, 70, 71 (cambio prodotto, dividendo in azioni, fondo monetario: D5); `degiro_flatex_withdrawal` per le righe 24, 25 (D7). Nessuna riga sconosciuta.

## 3. Superfici

| File | Proprietà | Cosa |
|---|---|---|
| `backend/app/services/brim_providers/broker_degiro.py` | L | riscrittura |
| `backend/app/services/brim_providers/sample_reports/degiro-account-en.csv` (nuovo) | test-author, rivisto da L | campione inglese sintetico |
| `backend/test_scripts/test_external/test_brim_degiro.py` (nuovo) | test-author | i test |
| `backend/test_scripts/test_external/test_brim_providers.py` | test-author, **solo `:1062`** (D8) | file di P |
| `backend/test_scripts/test_api/test_brim_api.py` | test-author | una categoria: le coppie passano il batch |
| `scripts/test_runner/_backend_external.py` | L, **solo la voce** `brim-degiro` | file comune |
| `frontend/src/lib/components/transactions/modals/ImportWizardModal.svelte` + helper/test | L + test-author | **solo con D3** |
| `mkdocs_src/docs/user/transactions/import/degiro.en.md` | docs-writer | pagina utente |
| `mkdocs_src/docs/developer/architecture/patterns/brim_plugin_guide.md` | docs-writer | estensione della regola `:65`; contratto delle coppie; lingua per file |
| `mkdocs_src/docs/developer/backend/brim/providers_list.md` | docs-writer | la riga DEGIRO |
| `LibreFolio_developer_journal/Release_2/Phase_0/31_brimDegiro/` (nuovo) | L | il piano |

Nessuna API cambia (niente `api sync`), nessuna migrazione, nessuna chiave i18n. Il CHANGELOG lo scrive il coordinatore.

## 4. Decisioni (✅ tutte approvate come raccomandate, 2026-10-07)

- **D1 — numeri.** Valore per valore quando è certo, separatore del file solo per i casi ambigui. Il campione olandese mescola i formati: la regola «un separatore per file», da sola, lo rompe. **Consigliata.**
- **D2 — riconoscere le gambe senza usare il tasso.** Presenza della colonna FX, poi gruppo, valuta, segno, adiacenza. **Consigliata**, perché la guida dice di ignorare il tasso. Alternative: (b) il tasso come solo spareggio, che chiede un'eccezione esplicita alla regola; (c) parole multilingue.
- **D3 — wizard, passo ④: le due gambe insieme.** Il checkbox di una gamba cambia anche l'altra; `buildFinalTxList` passa solo coppie complete. Esce dal perimetro dato (frontend). **Consigliata**: senza, una gamba tolta da sola diventa un errore `linkUuidPairCount` nell'editor.
- **D4 — lingue dei messaggi.** EN + NL di sicuro; IT, FR, ES, DE se la ricerca trova le intestazioni verificate; le altre in inglese. Sbagliare lingua tocca solo i messaggi, mai la lettura.
  - ✅ **Risolta con la ricerca** (§1.8): catalogo EN, NL, DE, FR, ES. IT resta in inglese (intestazione non verificata), come PT, CS e le altre: si aggiungono con un export reale.
- **D5 — righe note ma non importabili** (cambio prodotto, dividendo in azioni, fondo monetario): oggi spariscono. **Consigliato: avviso raggruppato**, non importate. Alternativa: il dividendo in azioni come ADJUSTMENT senza cassa (chiede il costo all'utente).
- **D6 — «DEGIRO Corporate Action Kosten»** (oggi saltata): **FEE senza asset, consigliata**.
- **D7 — prelievi dell'era flatex** («Processed Flatex Withdrawal» +, «flatex terugstorting» −, stesso istante): oggi saltati entrambi. Se uno dei due è il vero prelievo, la cassa resta gonfiata. **Consigliato: avviso** finché un export reale (chiesto all'utente) non lo chiarisce. Alternativa: «trasferimenti flatex», silenziosi come da decisione 6.
- **D8 — `cannot_parse_reason`** di DEGIRO, in inglese: **sì, consigliato**; tocca `:1062`.
- **D9 — l'elenco ordini finisce in `parsed`** con 0 transazioni e l'avviso (decisione 7). Alternativa: `BRIMParseError` → `failed` col messaggio. **Consigliato l'avviso**, come chiesto.
- **D10 — la prova dal wizard.** Uno spec E2E nuovo, `tx-import-degiro` (upload del campione inglese, gambe nel passo ④, consegna all'editor, validazione senza errori di coppia), registrato da me. **Consigliato**; in alternativa solo il test API del batch.

## 5. Conflitti

- `test_brim_providers.py`: P lavora intorno a `:1563`; io tocco al massimo `:1062`, senza riformattare.
- `scripts/test_runner/_backend_external.py`: aggiungo solo la mia voce (e, con D10, `_frontend_transaction.py`).
- `brim_plugin_guide.md`: file comune della famiglia BRIM; sezioni nuove, additive.
- `ImportWizardModal.svelte`: solo con D3; da verificare che nessun altro ramo lo tocchi.
- i18n, API, migrazioni: nessuna modifica.

## 6. Rischi

1. **Stringhe reali** delle altre lingue: le righe non riconosciute non si perdono, diventano un avviso.
2. **Layout più vecchi** (senza FX o Order Id): non riconosciuti → il motivo di D8.
3. **Abbinamento delle gambe**: se un export reale ordina le righe in modo diverso, l'adiacenza sbaglia → l'ambiguità diventa un avviso, mai una coppia sbagliata in silenzio; i test fissano l'ordine visto nel campione.
4. **Prelievi flatex** (D7): semantica non provata.
5. **Numeri ambigui** con 3 cifre dopo un solo separatore: decide il file.
6. **Catalogo messaggi**: da mantenere per ogni lingua aggiunta.
7. **Il campione NL è un collage**: prova la lettura riga per riga, non un export reale; l'export reale dell'utente (chiesto) resta la prova vera.
8. **Cambio di comportamento**: gli import DEGIRO futuri cambiano molto (14 righe in più sul campione); il bump di versione lo segnala sui file già analizzati.

## 7. Passi, dopo il via

1. Copia del piano nel repo (`31_brimDegiro/`); SHA di partenza.
2. Rossi (test-author): campione inglese sintetico; `test_brim_degiro.py`; `:1062` (D8); categoria API delle coppie; registrazione `brim-degiro` (io). Verifica: rossi sul loro punto, guardie verdi.
3. Cura: `broker_degiro.py` riscritto (§2), `plugin_version` 2.0.0, descrizione aggiornata.
4. Con D3: helper delle coppie nel wizard, rosso Vitest prima; con D10, lo spec E2E.
5. Doc (docs-writer): `degiro.en.md`, guida (estensione della regola, contratto delle coppie, lingua per file), `providers_list.md`.
6. Gate (§9), privacy, checkpoint con la riga di CHANGELOG.

## 8. I test, rossi prima (test-author)

- **Riconoscimento**: campione NL, campione EN, intestazioni in altre lingue costruite nel test (la struttura basta); nessun campione di altri broker preso; varianti a 11/13 colonne rifiutate; elenco ordini preso; `auto_detect_plugin` → DEGIRO sopra il generico; con D8, `can_parse(p) is (cannot_parse_reason(p) is None)` sul corpus.
- **Lettura per posizione**: tabella attesa riga per riga del campione NL (tipo, quantità, importo, valuta, ISIN) presa dalle colonne del file; righe saltate e avvisi per codice; continuazione dell'Order Id.
- **Tipi**: vendite NL, tasse NL/EN/FR, compravendite e commissioni con parole sconosciute (struttura), promo e cortesia → INTEREST con la descrizione, «Flatex Interest Income» ≠ 0 → INTEREST, = 0 → saltata.
- **Coppie**: 2 `FX_CONVERSION` per cambio, stesso `link_uuid`, descrizione e tag identici, segni opposti, senza asset; per Order Id (anche spezzato) e per data e ora; la commissione mai presa come controparte; `link_uuid` stabile fra due parse e diverso fra due file; gamba senza controparte → avviso.
- **Numeri**: `1,1734`, `-1,2108`, `1.234,56`, `1 046,3825`, il campione misto.
- **Lingua**: NL → NL, EN → EN, «Datum» da sola non basta, intestazioni ignote → EN; codici `degiro_*` senza chiave `importWizard.brimNotice.*`; evidenza con le intestazioni del file e i numeri di riga.
- **Elenco ordini**: 0 transazioni, un avviso nella lingua del file, nessuna eccezione.
- **Campione inglese sintetico** (`degiro-account-en.csv`): `;`, CRLF, virgola decimale, intestazioni inglesi; versamento, compravendite con commissione e gambe di cambio (Order Id spezzato), dividendo e ritenuta in USD, interessi CZK ≠ 0 e = 0, promo ceca e cortesia, sweep, informativa, prenotazione. Valori, date, Order Id e ISIN **inventati**: nessun dato dell'utente.
- **API** (`test_brim_api.py`): upload del campione inglese, parse, commit delle coppie e delle righe senza asset → nessun errore di coppia, `related_transaction_id` reciproci.
- Con D3: Vitest sull'helper delle coppie. Con D10: lo spec E2E.

## 9. Gate e definizione di fatto

- `external brim-degiro` (nuovo), `brim-providers`, `brim-danske-bank`; `services brim-report-sets`, `brim-gap-fix`; `api brim`; `check-orphans`; `dev.py lint`, black e ruff.
- Con D3/D10: `front check`, `tx-unit`, `front build --debug`, `--clean`, `tx-import-degiro`, `tx-import-flow`, `tx-import-upload`.
- `mkdocs build`, `check-links`; privacy (verifica il coordinatore); `git diff --check`; porta 6156 libera.
- Fatto quando: i file dell'utente sono riconosciuti; il campione NL dà la tabella attesa; il campione inglese anche; le coppie passano il batch; nessun avviso perso.

## 10. CHANGELOG (proposta finale, per il coordinatore; ogni frase verificata sul codice)

- 🐛 `- **DEGIRO statements are read correctly, in any language.** The importer reads the Account Statement by column position, so English and other-language exports are recognised. Each movement keeps its own amount and currency (amounts came from the balance, and every currency was EUR), sales and dividend taxes get their own types, numbers with a decimal comma and more than two decimals are no longer read as thousands, promotional credits become interest, and rows it cannot classify are listed in a warning instead of being dropped. Currency conversions become linked FX conversions: the review step shows each one as a single row, From/To with the rate the two amounts imply, and ticks both legs together. The Transactions export is recognised and points you to the Account Statement.`

## 11. Avanzamento

### 11.0 ✅ Analisi (2026-10-07)

- Letti: plugin, campioni, file dell'utente (struttura), guida, schema BRIM, pipeline delle coppie (wizard, BulkModal, batch), test e runner. Baseline misurata.
- ✅ Ricerca multilingue conclusa (§1.8); mandata al coordinatore come addendum.

### 11.1 ✅ Il piano nel repo, la voce del runner, il campione, i rossi (2026-10-07)

> **Note implementazione**:
> - Il piano è in `31_brimDegiro/`: §0.1 (l'approvazione, testuale), §1.8 (le fonti della ricerca), D4 risolta.
> - Il runner: `external_brim_degiro` e la voce `brim-degiro` in `scripts/test_runner/_backend_external.py`; nient'altro nel file.
> - **Il campione inglese sintetico** `degiro-account-en.csv`: `;`, ASCII, 25 righe, 12 colonne ciascuna. Scritto CRLF, nel repo va LF (§11.6). Contiene:
>   - interessi CZK, uno a zero e uno diverso da zero;
>   - la promo ceca e la cortesia;
>   - una riga informativa, uno sweep e due prenotazioni;
>   - una coppia di cambio senza Order Id;
>   - un ordine in USD con le gambe di cambio, l'Order Id spezzato su una riga di continuazione, la commissione e l'acquisto;
>   - una vendita e un acquisto in EUR (`1.124,00`, col punto delle migliaia), una commissione di connessione, un `flatex Withdrawal`, un versamento.
>
>   Valori, date e Order Id sono inventati; gli ISIN sono pubblici. Controllato contro i token dei file dell'utente: coincidono solo `0,00`, `1,00`, `Bank:` e `and/or`, tutti generici.
> - **La bozza del plugin**, nella sessione (`files/degiro/broker_degiro.draft.py`), provata fuori dal repo (`files/degiro/dryrun_draft.py`, registro disattivato):
>   - campione NL: 57 transazioni, come §2.9; avvisi ai numeri di riga attesi;
>   - campione EN: 17 transazioni;
>   - file dell'utente: tutti e due riconosciuti. L'estratto dà un INTEREST (la promo); l'elenco ordini dà l'avviso;
>   - inoltre: parse idempotente; numeri e lingue come da contratto; nessun altro campione preso.
>   Entra nel repo solo dopo la verifica dei rossi.
> - **D3, il disegno** (bozze in `files/degiro/importPairs.draft.ts` e `pairCellHtml.draft.ts`):
>   - una riga per coppia: si vede la gamba che paga, come «From» nell'editor;
>   - le righe «From/To» copiano il markup di `renderDualHtml` della BulkModal (etichette `common.from`/`common.to`, già esistenti);
>   - il chip del cambio implicito, come il suggerimento di promozione;
>   - la spunta vale per le due gambe insieme; il risolutore dei doppioni propaga la scelta al partner;
>   - alla consegna passano solo coppie complete, ciascuna con un `link_uuid` nuovo.
>
>   Nessuna chiave i18n nuova.
>
> **⚠️ Fuori pista** (rivedendo la bozza):
> - una gamba rimasta senza controparte che ha un Order Id sarebbe finita fra le commissioni: ora la riconoscono prima le parole delle gambe di cambio;
> - `_certain_mark` superava la complessità 10 di ruff: riscritto.

### 11.2 ✅ I rossi del backend e la cura del plugin (2026-10-07)

> **Note implementazione** — i rossi (test-author, log nella sessione, `files/degiro-reds/`):
> - `test_brim_degiro.py`, 169 casi in 11 classi (identità, riconoscimento, fixture, campioni, classificazione, tabella di parole, coppie, numeri, lingue e messaggi, elenco ordini). Contro il plugin di prima: **125 rossi**, ciascuno su un'asserzione, e 44 guardie verdi.
> - `test_brim_api.py`, categoria 16 (RS-DG01): carica e analizza il campione inglese, valida e salva le 4 gambe di cambio e le 5 righe senza asset, poi rilegge i `related_transaction_id` reciproci. Rossa, perché il file non era riconosciuto.
> - `test_brim_providers.py`, solo `:1062`: `broker_degiro` sostituito da `broker_trading212` (non ridefinisce `cannot_parse_reason`; verificato).
> - `external brim-providers`: 4 rossi attesi (il campione inglese ancora non riconosciuto).
> - Il test-author ha provato i test anche contro un prototipo fuori dal repo: 168/169 verdi, e 4 rotture fatte apposta prese ciascuna dal suo test.
>
> **La cura**: `broker_degiro.py` riscritto dalla bozza (§11.1).
>
> | Comando (corsia 6156; log nella sessione, `files/degiro-cure/`) | Esito |
> |---|---|
> | `external brim-degiro` | **169 passed** |
> | `external brim-providers` | **626 passed**, 1 saltato |
> | `api brim` | **79 passed** (RS-DG01 compresa: le coppie passano il batch e si collegano) |
> | `external brim-danske-bank` / `services brim-report-sets` / `services brim-gap-fix` | **324** / **259** / **99 passed** |
> | `check-orphans`; ruff e black su `broker_degiro.py` | puliti |
>
> **⚠️ Fuori pista**:
> - Al primo giro 168/169: la mia bozza univa le righe di continuazione con uno spazio fra prodotto e descrizione. Il contratto, che avevo scritto io, dice «alla lettera», e DEGIRO va a capo per numero di caratteri (l'Order Id è spezzato a metà UUID). Corretto: si accoda alla lettera.
> - Ruff C416: `list(csv.reader(...))`.

### 11.3 ✅ D3/D10 e la doc, la preparazione (2026-10-07)

- Runner: `importPairs.test.ts` in `tx-unit`; la voce `tx-import-degiro` in `scripts/test_runner/_frontend_transaction.py`. Solo queste due aggiunte.
- Gli helper `importPairs.ts` e `pairCellHtml.ts` sono nel repo **come stub**, con le firme definitive, così i rossi falliscono sulle asserzioni.
- `front build --debug` del codice di adesso, prima dei rossi E2E.
- In corso:
  - i rossi di D3/D10 (test-author): lo spec `tx-import-degiro` prima, poi Vitest;
  - la doc EN (docs-writer): `degiro.en.md`, la guida (in aggiunta), `providers_list.md`.

### 11.4 ✅ La doc EN (2026-10-07)

> **Note implementazione** — docs-writer, solo EN, nessuno stamp:
> - `degiro.en.md`:
>   - cosa serve (Account Statement) e cosa no (Transactions);
>   - la lettura per posizione in qualunque lingua; la lingua degli avvisi;
>   - tre sezioni nuove: cosa si importa, i cambi, cosa non si importa e perché;
>   - via le due promesse false (`:29` lingue, `:34` cambi «processati»).
> - `brim_plugin_guide.md`, solo aggiunte (+73 righe, 0 tolte):
>   - l'**estensione** della regola di `can_parse` (`:65`);
>   - la lingua scelta dall'intestazione;
>   - perché i codici `degiro_*` non hanno chiave i18n;
>   - una sezione nuova `#linked-pairs`: il contratto del batch, il `link_uuid` deterministico, le gambe riconosciute senza tasso, le coppie nel wizard.
> - `providers_list.md`: solo la riga DEGIRO.
> - Prove (docs-writer): `mkdocs build` strict verde, senza warning. `check-links`: 89 link validi, 1 rotto, `user/assets/detail/chart/#rolling-return`. Non è nostro: è in una pagina che non tocco, e l'àncora esiste (`chart.en.md:22`).
> - Rilettura mia, sul codice: ogni simbolo citato esiste (`_layout`, `_detect_language`, `_HEADER_WORDS`, `_MIN_LANGUAGE_MATCHES`, `_MESSAGES`, `_pair_fx_legs`, `_fx_pair`, `resolve_create_links`, `_validate_linked_pair`, `_validate_pair_description_tags`, `resolveBrimNoticeMessage`, i 4 codici d'errore, i 3 test citati).
>   - Swissquote salta le gambe con un avviso (`broker_swissquote.py:199-200`); il generico rifiuta i tipi in coppia (`:615-616`).
>   - Il `link_uuid` non ha colonna nel DB.
>   - Le parole d'esempio vengono tutte dal campione sintetico; «FX Credit / FX Debit» è anche nel test `:1394`.
> - Da riverificare dopo D3: le frasi sul wizard (pagina utente e guida) e la frase su AutoFX («already included in the converted amount»), da rendere precisa.
> - ✅ Riverificato, a D3 fatto (secondo e terzo giro del docs-writer; la guida arriva a **+84 righe, 0 tolte**):
>   - pagina utente: la frase sul passo di revisione resta, ora è vera. Due frasi nuove: i contatori contano le transazioni, quindi una coppia vale due (un esempio con righe e transazioni); AutoFX «già parte dell'importo che il cambio addebita, nessuna commissione separata» (decisione §0.4, nient'altro);
>   - guida: il paragrafo sul wizard allineato al codice (gamba nascosta, cella From/To, chip, spunta, select visible, conteggi; cita `pairCellHtml.ts`) e una riga DEGIRO nella tabella dei plugin di riferimento;
>   - `mkdocs build` strict verde; `check-links` con il solo rotto preesistente (D28);
>   - le ancore che Q linka da `brim/architecture.md` (`#report-sets`, `#broker-metadata-lock`, `#cannot-parse-reason`, `#report-set-history`, `#compatible-plugins-lifecycle`) ci sono tutte e cinque, come a HEAD.
> - Il docs-writer ha trovato un errore mio: il docstring di `renderImpliedRateHtml` dava `USD → EUR @ 1.1690`, cioè il tasso inverso, quello della colonna FX del campione. Corretto in 0.8554.
>
> **⚠️ Fuori pista — privacy**: lo scanner (`/tmp/libreFolio_l_degiro_privacy.py`) confronta i file nuovi con i token dei file dell'utente e stampa solo classi e conteggi.
> - Le parole in comune sono il lessico di servizio di DEGIRO («Interest Income», «Cash Sweep Transfer», la promo ceca). Gli importi in comune sono generici (±1,00, ±2,00).
> - Un valore invece veniva dal file dell'utente: il tasso usato come esempio della decisione 8, finito in questo piano e nel test dei numeri. Nel piano ora c'è un valore sintetico della stessa forma (`1,1734`); nel test lo cambia il test-author.

### 11.5 ✅ D3/D10: le coppie nel passo ④ del wizard (2026-10-07)

> **Note implementazione** — i rossi (test-author; log nella sessione, `files/degiro-pairs-reds/`):
> - `importPairs.test.ts`, 43 casi Vitest sugli helper e sui due renderer. Contro gli stub: 30 rossi sulle asserzioni, 13 guardie verdi, il resto di `tx-unit` verde.
> - `tx-import-degiro.spec.ts`, P1–P3 sul campione inglese. Contro gli stub: 3 rossi sulle asserzioni della riga di coppia, mai sul percorso (upload → plugin → parse → revisione) né sulla pulizia.
> - **Conteggi in transazioni**: deciso dal test-author e adottato. Il bottone dice «Import {n} transactions», quindi `data-selected-count` e `data-total-count` contano le gambe (17), mentre la tabella mostra 15 righe; una coppia spuntata vale 2. Il mio abbozzo contava le righe.
>
> La cura:
> - `importPairs.ts` e `pairCellHtml.ts`: le bozze al posto degli stub, senza modifiche.
> - `ImportWizardModal.svelte`:
>   - `pairs = linkedPairs(mergedTransactions)`; `step4LegRows` (tutte le gambe) per i contatori; `step4Rows` (senza le gambe nascoste) per la tabella;
>   - `step4SelectedCount` conta solo coppie complete (`completePairsOnly`), come la consegna;
>   - la spunta mostra «entrambe le gambe» e le muove insieme (`setPairSelected`);
>   - la cella della cassa: From/To e il chip del tasso implicito (`import-tx-pair-cash`, `import-tx-pair-rate`);
>   - «seleziona visibili» prende anche la gamba nascosta;
>   - `buildFinalTxList`: solo coppie complete, con un `link_uuid` nuovo per coppia.
>   - Nessuna chiave i18n nuova (`common.from`/`common.to` esistono già in 4 lingue).
>
> | Comando (corsia 6156; log nella sessione, `files/degiro-d3/`) | Esito |
> |---|---|
> | `front-transaction tx-unit` | **676 passed** (15 file) |
> | `front check` | svelte-check: 0 errori, 0 avvisi |
> | prettier `--check` sui 5 file frontend | puliti. Il wizard a HEAD era già pulito; `--write` ha solo rimandato a capo la mia riga |
> | `front build --debug`, poi `front-transaction tx-import-degiro` | **3 passed** (P1 12,9 s · P2 5,6 s · P3 7,4 s) |
>
> **⚠️ Fuori pista**: `step4SelectVisible` seleziona le righe della pagina, e la gamba nascosta non c'è: senza correzione, «seleziona visibili» avrebbe lasciato coppie a metà. Adesso aggiunge il partner di ogni riga. Nessun test lo copre; la consegna resta comunque protetta da `completePairsOnly`.

### 11.6 ✅ P4, le regressioni, il triage, i gate finali (2026-10-07)

> **Note implementazione**:
> - **P4** (test-author): «seleziona visibili» muove le due gambe di ogni coppia della pagina. Prima legge che la pagina contenga tutte le righe. Il rosso l'ho provato io togliendo per un momento il ciclo dei partner da `step4SelectVisible`:
>   - conteggio 13 invece di 17. È 13 e non 15 perché il contatore, apposta, scarta le gambe orfane (`completePairsOnly`);
>   - le due spunte di coppia `false`;
>   - la guardia sul DEPOSIT e P1–P3 verdi.
>
>   Rimesso il ciclo: 4/4 verdi.
> - **Privacy**: nel test dei numeri ora c'è `1,1734`, sintetico, al posto del valore dell'utente (test-author). Lo scanner sui 16 file del lotto trova solo il lessico di servizio di DEGIRO e importi generici.
> - **Le regressioni dell'import** (prima giro sequenziale, corsia 6156):
>   - verdi: flow 10, bulk-import-handoff 2, duplicate-precedence 6, upload 9, report-set 28, report-set-guide 2, selection-after-bulk 10;
>   - `component-unit` 2829 (exit 0).
>
> **⚠️ Fuori pista — tre rossi, triage** (skill `test-triage`; `--clean` concesso dal coordinatore solo per rilanciarli):
> - **`tx-import-file-selection`** (1 su 2): il broker «control» trova 2 file invece di 1. Dal log del server, il secondo è un file di `tx-ca-contract` caricato su un broker con lo stesso id.
>   - Il meccanismo: ogni invocazione E2E lancia `populate --force`, che cancella i broker dal DB ma non i loro file su disco; `brokers` non ha AUTOINCREMENT, quindi gli id si riusano; CAC crea un broker e un file per ogni test e non li cancella mai.
>   - Dopo `--clean`, da solo: 2/2 verdi. **Verdetto: stato condiviso.**
> - **`tx-brim-import` T1, `tx-ca-contract` CAC-011/012**: timeout in attesa della revisione. Lo snapshot di CAC-011 mostra il wizard fermo sul passo delle correzioni.
>   - Gli helper cercano i passi intermedi con `isVisible({timeout})`, che non aspetta: sotto carico il passo appare dopo il controllo e viene saltato. T1, in più, sceglie il file con `.first()`.
>   - Restano rossi anche sulla corsia pulita, e **identici col wizard di HEAD** (D3 tolto per la prova, poi rimesso): non vengono da D3.
>   - **Verdetto: assunzione del test (orologio).** Il prodotto si comporta come previsto.
> - Tutto questo va al lotto successivo, approvato dal developer: l'infrastruttura dei test e la verifica in produzione.
>   - Dal codice: cancellare un broker dall'API cancella i suoi file (`brokers.py:103`, `_delete_brim_files_for_brokers`, chiamata da `:415` e `:564`). Restano due casi da verificare: la pulizia è best-effort, e tiene i file senza `target_broker_id`.
>
> **⚠️ Fuori pista — il campione e i fine riga**:
> - Il `~/.gitconfig` del developer ha `core.autocrlf=input`, e nel repo tutti i 51 campioni di testo sono LF. Quindi `git add` normalizza il campione in LF: il blob è identico (`cdf7f84…`) che il file sia CRLF o LF.
> - Ho portato la copia di lavoro in LF e rilanciato tutto ciò che legge il campione su quei byte: verde (tabella sotto).
> - Il CRLF, cioè il file come lo scarica l'utente, resta coperto dai byte che i test costruiscono (`_statement_bytes`). Il commento del test che diceva «CRLF» per il campione è corretto (test-author, `:616–617`).
> - Se il coordinatore vuole il campione CRLF byte per byte serve una riga in `.gitattributes`, che è un file condiviso: decide lui.
>
> | Gate finali (corsia 6156; log nella sessione, `files/degiro-d3/`) | Esito |
> |---|---|
> | `external brim-degiro` (campione LF) | **169 passed** |
> | `external brim-providers` (LF) | **626 passed**, 1 saltato |
> | `api brim` (LF) | **79 passed** |
> | `front-transaction tx-import-degiro` (LF) | **4 passed** (P1–P4) |
> | `front-transaction tx-unit` / `front-utility component-unit` | **676** / **2829 passed** |
> | `front check`; prettier sui file frontend | 0 errori, 0 avvisi; puliti |
> | `check-orphans` | pulito |
> | ruff e black sui file Python di DEGIRO | puliti. Nei file del runner, 4 PLC0415 e il formato black c'erano già a HEAD: non li tocco |
> | `mkdocs build` strict; `check-links` | verde; solo il rotto D28, preesistente |
> | `git diff --check`; porta 6156 | pulito; libera |
