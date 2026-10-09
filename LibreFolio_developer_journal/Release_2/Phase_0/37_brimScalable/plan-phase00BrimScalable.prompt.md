# Piano — fase 00, 37: i plugin BRIM di Scalable Capital (broker e conto deposito)

> **Stato**: 🚧 in esecuzione dal 2026-10-09. Avanzamento in §18.
>
> - **Mandato**: coordinatore di Release 2 (`c8328a01-…`), con le decisioni del developer (§1) e l'autorizzazione testuale (§0).
> - **Workstream S**. Ramo `e-alfy-s-export-scalable-via-chrome`, base `3cceb4f90` (treno 24b, fast-forward del developer, verificata pulita il 2026-10-09). L'analisi è stata fatta su `1ead733f2` (treno 23).
> - **Corsia**: `--test-port 6163 --data-dir /tmp/librefolio-r2-s`, con `PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py …`; un comando alla volta. Mai le porte 6040, 6041 e 6150.
> - **Riepilogo della fase dell'esportatore**: [`recap-phase00ScalableExporter.md`](recap-phase00ScalableExporter.md), controllato dal coordinatore.
> - **Repo esterno**: `Librefolio/librefolio-exporter`, estensione Chrome MV3; v1.0.0 rilasciata, 1.0.1 in questo piano (§5).
> - **Rilascio**: 1.2.0, se tutto è integrato entro martedì 13/10 (decisione del developer).

## 0. Autorizzazione (2026-10-09)

- **Developer**, testuale, tramite il coordinatore (15:29): «Confermo: S parte con il piano nuovo, superfici e npm ci come proponi (Consigliato)».
- **Coordinatore**:
  - baseline `3cceb4f90`, confermata dopo il fast-forward;
  - superfici in §13;
  - `npm ci` solo dal lock, niente update né `audit fix`;
  - il CHANGELOG è suo: propongo le righe a ogni checkpoint;
  - almeno un checkpoint per ogni gruppo di passi verdi (§14).
- **Storia del piano**: la prima stesura aveva un solo plugin. Su idea del developer è diventata due plugin che si rifiutano a vicenda, più una modale nell'assistente di import (§1, decisioni 1 e 5). Le versioni precedenti restano nella sessione S.

## 1. Obiettivo e decisioni del developer

Importare i movimenti di Scalable Capital in **due broker LibreFolio**, «Scalable broker» e «Scalable conto deposito». Decisioni del 2026-10-09:

1. **Due plugin, un modulo comune.**
   - `broker_scalable` legge il CSV ufficiale Prime e l'export del broker dell'esportatore.
   - `broker_scalable_deposit` legge l'export del conto deposito.
   - Ognuno rifiuta il file dell'altro e dice quale plugin usare.
   - Il plugin predefinito del broker indica quindi anche il conto.
2. **La guida consiglia l'esportatore**: dà più informazioni ed è l'unico modo di esportare il conto deposito. Rimanda al repo `Librefolio/librefolio-exporter` e spiega come scaricarlo e usarlo.
3. **L'id della transazione va nella frase della descrizione LibreFolio**: due movimenti identici restano distinti.
4. **Icone.**
   - Ogni plugin ha la sua icona composta: favicon di Scalable più un simbolo.
   - Le icone sono risorse statiche dei plugin di LibreFolio, generate con lo script delle icone composte.
   - Il broker la mostra da solo quando il plugin è il suo plugin predefinito, senza icona propria e senza percorsi da incollare.
5. **Modale nell'assistente di import.**
   - **Quando**: si assegna un file a un broker che ha un plugin predefinito, e quel plugin non sa leggere il file.
   - **Cosa dice**: il motivo del plugin, il plugin che legge il file e il broker che lo usa come predefinito.
   - **Cosa offre**: spostare il file, tenerlo dov'è o rimuoverlo.
   - Vale per tutti i broker.
6. **Traduzioni complete** in inglese, italiano, francese e spagnolo.
   - Interfaccia: la modale, il motivo del rifiuto (tradotto per codice) e gli avvisi dei plugin Scalable.
   - Documentazione: la pagina utente entra nel giro di traduzioni del 14/10.
7. **Unione dei trasferimenti interni.** Dopo l'import dei due file, insieme o in momenti diversi, l'editor in blocco suggerisce di unirli. Va verificato con un test umano e uno automatico.
8. **Campioni sintetici** per tutti i formati.
9. **Tutto nella 1.2.0.**
   - Tutto integrato entro martedì 13/10.
   - La pagina inglese entra prima che la documentazione si fermi, il 14/10.
   - CHANGELOG: `## [1.2.0] - 2026-10-19`.

## 2. Analisi: il codice BRIM alla baseline

**Contratto del plugin** (`backend/app/services/brim_provider.py`, guida `mkdocs_src/docs/developer/architecture/patterns/brim_plugin_guide.md`, skill `brim-plugin`):

- `provider_code`, `provider_name` e `description` restituiscono **letterali stringa**. Il test R13 (`optionFilter.test.ts`) e il runner li leggono come testo.
- `can_parse`, `parse`, e `cannot_parse_reason`, che restituisce una frase inglese, minuscola all'inizio e senza punto finale. Oggi il motivo serve solo al 400 del parse.
- Separatore rilevato e codifica mai fissata (`_open_text`, `_brim_io.read_rows`). La suite lo verifica con `TestWindows1252Invariance`.
- Regole dei segni verificate dai test. Gli id finti degli asset partono da `FAKE_ASSET_ID_BASE`.
- `plugin_version` va alzata quando l'output cambia.
- Una riga può produrre più transazioni. I tag `["import", "<plugin>"]` segnano le transazioni importate.

**Helper comuni**, estratti da Crédit Agricole e condivisi con Intesa, Fineco e DEGIRO:

- `_brim_io.py`: `read_rows`, `find_header_row`, `build_col_index`, `row_get`, `is_blank_row`, `to_decimal_it`, `to_decimal_plain`, `to_date`, `detect_delimiter`, e gli helper delle obbligazioni.
- `_brim_output.py`: `attach_maturity_notices`.
- Classe base: `_create_transaction`, `detect_csv_delimiter`, `_open_text`, `_read_file_head`, `generate_static_url`.

**Tre modelli esistenti, per confronto:**

| Modello | Esempio | Cos'è | Per Scalable |
|---|---|---|---|
| Plugin a più formati | Revolut (invest, crypto) | Una classe, più layout riconosciuti dall'intestazione; ogni file si legge da solo | Lo schema di partenza; qui diventa due plugin con un modulo comune |
| Report set | Danske Bank | Più export incompleti dello **stesso** conto, combinati prima della lettura, con checkpoint, gap-fix e H0, sempre su un solo broker | Non serve: i file sono completi e i conti sono due |
| Coppie collegate | DEGIRO (`FX_CONVERSION`) | Un plugin emette due transazioni collegate da un `link_uuid` deterministico, nello stesso broker | Non si può: un trasferimento di cassa collega due broker, mentre un import scrive in uno solo. L'unione arriva dopo, dall'editor in blocco |

Da DEGIRO prendiamo anche un'idea: riconoscere il file di un altro formato del proprio broker e dire cosa fare. Lo fa la nostra modale (§7).

**Wiki**: la devWiki dice poco su Danske e DEGIRO; la fonte resta la guida. Pagina utile: `wiki/decisions/pair-description-tags-validation.md`. I lati di una coppia hanno descrizione e tag identici; il frontend unisce i testi diversi.

## 3. Fatti verificati che decidono il disegno

| # | Fatto | Fonte | Conseguenza |
|---|---|---|---|
| F1 | Nel CSV Prime ufficiale `amount` di un'operazione è il **lordo**, pezzi × prezzo; `fee` e `tax` sono a parte | Due export reali pubblici (`athimannil/scalable-to-tradingview`, `popokatapepel/popos-taco-trade`), letti in memoria | BUY e SELL sul lordo, più gambe FEE e TAX |
| F2 | L'esportatore 1.0.0 scrive in `amount` l'importo della web app, **commissione compresa** | Dati del developer: importo della web app = valore di mercato + commissione | Esportatore 1.0.1 (§5) |
| F3 | Sui proventi `amount` è il **netto**, `tax` la ritenuta | Parser pubblici (`EGZX/Tax-Calculator-Austria`, `GeiserX/DeclaRenta`); dati del developer | DIVIDEND e INTEREST = `amount` + `tax`, più una gamba TAX |
| F4 | L'unione in `CASH_TRANSFER` richiede WITHDRAWAL e DEPOSIT con stessa valuta, broker diversi, importi opposti, entro `tolerance_days` (3 di default) | `schemas/transactions.py:1269-1300`, `transaction_service.py:781` | I trasferimenti interni soddisfano la regola |
| F5 | L'editor in blocco suggerisce nuova + nuova e salvata + salvata, ma **non nuova + salvata**. Backend e `executePromote` (ramo misto) supportano già quel caso | `TransactionBulkModal.svelte:2697-2737, 2826, 2853, 2890, 2611`; `schemas/transactions.py:925` | Modifica solo del frontend (§8) |
| F6 | I lati di una coppia hanno descrizione e tag identici. La finestra di unione propone i due testi uniti | `transaction_service.py:202`; `PromoteMergeModal.svelte:62` | Un id diverso per lato non blocca |
| F7 | I duplicati si cercano per broker, **stesso tipo**, data, quantità e importo. Un trasferimento già unito, esportato di nuovo, non risulta duplicato | `brim_provider.py:2025` | Correzione del core (§9) |
| F8 | Le icone composte dei tipi di asset sono PNG statici creati da `scripts/compose_asset_type_icons.py` (Pillow, 192 px, simbolo in basso a destra) | lo script | Stessa geometria per le icone dei plugin |
| F9 | Ordine delle icone del broker: `icon_url`, poi favicon del portale, poi icona del plugin predefinito, poi la valigetta | `brokerIconChain.svelte.ts:73-91` | L'icona del plugin arriva da sola |
| F10 | `https://de.scalable.capital/favicon.ico` risponde 404. Il sito dichiara `https://assets.scalable.capital/favicon/favicon.ico` e un PNG 192×192 (`…/touch-icons/android-chrome-192x192.png`) | `curl -I`, intestazione della pagina | Anche con il portale impostato si arriva all'icona del plugin; il PNG è la base delle composte |
| F11 | Nel worktree manca `frontend/node_modules` | `ls` | Vitest, Playwright, R13 e `svelte-check` richiedono `npm ci`: concesso il 2026-10-09, solo dal lock |
| F12 | Se il plugin predefinito del broker non legge il file, l'assistente sceglie **in silenzio** il primo plugin compatibile | `ImportWizardModal.svelte:3415-3440` (`pickBestPlugin`) | È il caso del file nel broker sbagliato (§7) |
| F13 | Il caricamento manda il file con `broker_id` e risponde con `compatible_plugins`. Non c'è un'API per spostare un file tra broker; l'assistente tiene il `File` in `pendingFiles` | `ImportWizardModal.svelte:3212-3243`; rotte di `brokers.py` | «Sposta» ricarica il file nell'altro broker e poi cancella l'originale |
| F14 | `cannot_parse_reason` serve solo al 400 del parse: nessuna API lo espone prima | `brim_provider.py`, guida | Endpoint nuovo (§7) |
| F15 | Il frontend traduce avvisi e todo per codice (`importWizard.brimNotice.<code>`, `resolveBrimNotice.ts`) e, senza chiave, mostra il testo del plugin | guida, righe 452-458 | Stesso meccanismo per gli avvisi Scalable e per i rifiuti (§10) |
| F16 | `GET /api/v1/uploads/plugin/brim/{path}` serve `backend/app/services/brim_providers/static/`, con la sessione e la protezione dal path traversal. La cartella non esiste ancora: saremo i primi a usarla. Il Dockerfile copia `backend/` | `uploads.py:149, 495`; `Dockerfile:102` | Icone dei plugin come risorse del backend |

## 4. I due plugin

### 4.1 Struttura

| File | Ruolo |
|---|---|
| `backend/app/services/brim_providers/_scalable.py` | Modulo comune: riconoscimento dell'intestazione, lettura delle righe, mappatura, descrizioni, avvisi, motivi di rifiuto |
| `backend/app/services/brim_providers/broker_scalable.py` | Plugin del broker: CSV Prime ed export del broker |
| `backend/app/services/brim_providers/broker_scalable_deposit.py` | Plugin del conto deposito: export del conto deposito |

Il test R13 legge solo i file `broker_*.py`: il modulo comune, con il trattino basso, non è un plugin.

| Proprietà | `broker_scalable` | `broker_scalable_deposit` |
|---|---|---|
| `provider_name` | `Scalable Capital broker` | `Scalable Capital overnight account` |
| `description` | broker: export ufficiale (PRIME) o dell'esportatore LibreFolio | conto deposito (Tagesgeld): export dell'esportatore LibreFolio |
| `icon_url` | `generate_static_url("scalable/broker.png")` | `generate_static_url("scalable/deposit.png")` |
| `docs_url` | `/mkdocs/user/transactions/import/scalable/` | lo stesso |
| `test_file_patterns` | `["scalable-prime", "scalable-broker"]` | `["scalable-deposit"]` |
| `plugin_version` | `1.0.0` | `1.0.0` |

### 4.2 Riconoscimento e rifiuti

- **Il layout si riconosce dall'intestazione**, mai dal nome del file, perché il prefisso è libero.
  - `prime`: le 14 colonne ufficiali, senza `lf_account`.
  - `exporter`: le 14 colonne più `lf_account`; il conto viene dai valori (`broker` o `deposit`).
- **`can_parse`**:
  - del broker: `prime`, oppure `exporter` con tutte le righe `broker`;
  - del conto deposito: `exporter` con tutte le righe `deposit`.
- **Collisioni**: Parqet richiede `identifier` e `holdingname`; il CSV generico ha priorità 0, i nostri 100.
- **`cannot_parse_detail`** (§7.1), con codice, messaggio inglese e contesto. `cannot_parse_reason` ne restituisce il messaggio.

| Codice | Chi lo dà | Messaggio inglese |
|---|---|---|
| `scalable_deposit_file` | broker, su un export del conto deposito | this is the export of the Scalable overnight account: read it with the Scalable Capital overnight account plugin |
| `scalable_broker_file` | conto deposito, su un export del broker | this is the export of the Scalable broker account: read it with the Scalable Capital broker plugin |
| `scalable_prime_file` | conto deposito, su un CSV Prime | this is Scalable's own export of the broker account: read it with the Scalable Capital broker plugin |
| `scalable_mixed_file` | entrambi | the file mixes the broker and the overnight account: export them separately |

Un file che non è di Scalable non ha motivo: `None`.

### 4.3 Mappatura

**Regole generali:**
- si importano solo le righe eseguite: `status` = `Executed` (o `Settled`, se mai compare);
- il tipo esatto viene da `lf_subtype` quando c'è, altrimenti da `type`;
- i segni seguono il tipo LibreFolio, i valori assoluti vengono dal file;
- le colonne Prime si leggono con `to_decimal_it`, le `lf_*` con `to_decimal_plain`;
- la data è `date`, cioè la data di Berlino.

| CSV: `type` (`lf_subtype`) | LibreFolio | Importi |
|---|---|---|
| `Buy`, `Savings plan` | BUY, poi FEE se `fee` > 0, TAX se `tax` > 0 | BUY: quantità +shares, cassa −\|amount\|; FEE −fee; TAX −tax |
| `Sell` | SELL, FEE, TAX | SELL: quantità −shares, cassa +\|amount\|. Un `tax` negativo (credito d'imposta) è un DEPOSIT di rimborso |
| `Distribution` (`DISTRIBUTION`, `REINVESTMENT_DISTRIBUTION`) | DIVIDEND, TAX | DIVIDEND = `amount` + `tax`; TAX = −`tax`; asset da `isin` |
| `Interest` (`INTEREST`, `INTEREST_PAYMENT`) | INTEREST, TAX | INTEREST = `amount` + `tax`; TAX = −`tax`. Senza dettagli resta l'INTEREST netto, con un avviso |
| `Deposit` (`DEPOSIT`, `POCKET_MONEY`, `CASH_TRANSFER_IN`) | DEPOSIT | +\|amount\| |
| `Withdrawal` (`WITHDRAWAL`, `CASH_TRANSFER_OUT`) | WITHDRAWAL | −\|amount\| |
| `Fee` | FEE | −\|amount\| |
| `Taxes` (`TAX`, `TAX_RETURN`) | TAX se `amount` < 0, DEPOSIT di rimborso se > 0 | Un TAX positivo non è ammesso. Avviso informativo |
| Sottotipo di cassa sconosciuto | DEPOSIT o WITHDRAWAL secondo il segno | Avviso informativo |
| `Security transfer`, `Corporate action`, altro | Non importati | Avviso con le righe |

**Senza dettagli** (`fee`/`tax` vuoti, cioè non noti) non si crea nessuna gamba FEE o TAX. L'avviso dice di riesportare con «Includi commissioni e tasse».

### 4.4 Descrizione, tag e asset

- **Descrizione.**
  - Il testo del file (oppure l'etichetta del tipo, se vuoto), poi l'id: ` · id <lf_id>` per l'esportatore, ` · ref <reference>` per Prime.
  - Per l'esportatore si aggiunge anche ` · ref <SCAL…>` quando c'è.
  - Le gambe FEE e TAX hanno lo stesso testo, preceduto da `Order fee` o `Tax`.
- **Tag**: `["import", "scalable"]` per entrambi i plugin. Tag uguali non chiedono di essere risolti quando si unisce una coppia.
- **Asset**: chiave ISIN; `extracted_isin` dall'ISIN, `extracted_name` da `description`. Le gambe FEE e TAX puntano allo stesso asset.
- **Valuta**: dalla riga; una riga senza valuta viene saltata con un avviso.

### 4.5 Avvisi

Ogni avviso ha codice, messaggio inglese (il ripiego), contesto ed evidenze con i numeri di riga. Il frontend li traduce nelle quattro lingue (§10). Nessun `field_todo`.

| Codice | Gravità | Caso |
|---|---|---|
| `scalable_not_executed` | info | Righe `Pending`, `Cancelled`, `Expired`, `Rejected` non importate, con il conteggio |
| `scalable_open_partial` | warning | Ordine eseguito in parte e ancora aperto: non importato, arriverà eseguito con il prossimo export |
| `scalable_fees_unknown` | warning | Operazioni o interessi senza dettagli: commissioni e tasse non note |
| `scalable_reversal` | warning | `lf_is_cancellation` = `true`: non importato, da correggere a mano |
| `scalable_not_imported` | warning | Trasferimenti di titoli, operazioni societarie, tipi sconosciuti |
| `scalable_cash_by_sign` | info | Sottotipo di cassa sconosciuto, registrato secondo il segno |
| `scalable_tax_refund` | info | Rimborsi d'imposta registrati come DEPOSIT |
| `scalable_internal_transfers` | info | N trasferimenti tra broker e conto deposito, da unire dopo l'import dell'altro file |
| `scalable_several_overnight_accounts` | warning | Più conti deposito nello stesso file: tutte le righe vanno nel broker scelto |
| `scalable_fee_in_amount` | warning | File dell'esportatore 1.0.0 con la commissione nell'importo: nessuna gamba FEE, con la richiesta di riesportare |

### 4.6 Campioni sintetici

Vanno in `backend/app/services/brim_providers/sample_reports/`, descritti nel `README.md`. I valori sono inventati, la struttura è reale; ISIN di ETF pubblici, riferimenti e id finti.

1. **`scalable-prime-export.csv`** (14 colonne): piano di accumulo, acquisto con 0,99 € (amount lordo), acquisto PRIME gratuito, vendita con commissione e tasse, dividendo con ritenuta, deposito, prelievo, ordine annullato, ordine in attesa, commissione di cassa, tassa, rimborso d'imposta, `Security transfer`.
2. **`scalable-broker-export.csv`** (23 colonne, esportatore 1.0.1): le stesse famiglie, più:
   - i trasferimenti verso e dal conto deposito;
   - un ordine parziale aperto, uno storno, un sottotipo sconosciuto, una commissione di borsa;
   - una descrizione non ASCII, per il test Windows-1252.
3. **`scalable-deposit-export.csv`** (19 colonne): interessi con ritenuta e senza dettagli, versamento e prelievo verso la banca, e i trasferimenti speculari a quelli del broker, **stessi giorni e importi**.

## 5. Esportatore 1.0.1 (repo `librefolio-exporter`)

- `TRANSACTION_DETAILS` chiede di nuovo `tradeTransactionAmounts.marketValuation`.
- Nelle operazioni con i dettagli letti, `amount` diventa `marketValuation` con il segno dell'operazione, come nel CSV ufficiale.
- Senza dettagli resta l'importo della web app; `fee` e `tax` vuoti dicono che è il netto.
- Da aggiornare: test, `docs/formats/scalable.md`, CHANGELOG `1.0.1`, link alla pagina LibreFolio nel README.
- Il developer prova un export sul conto vero (un acquisto con commissione deve dare il valore di mercato, azioni × prezzo, senza la commissione) e crea il tag `v1.0.1`.
- I file 1.0.0 li ha solo lui: li riesporta. L'avviso `scalable_fee_in_amount` fa da rete.

## 6. Icone

**Generazione**: `scripts/compose_broker_icons.py`, nuovo, con la stessa geometria di `compose_asset_type_icons.py` e la sua funzione `compose()` riusata.

- **Base**: il PNG 192×192 di Scalable, salvato in `scripts/assets/brokers/scalable.png`, così la generazione non dipende dalla rete.
- **Simboli**: quelli dei tipi di asset, `stock.png` per il broker e `liquidity.png` per il conto deposito.
- **Uscite**:
  - `backend/app/services/brim_providers/static/scalable/broker.png` e `deposit.png`, cioè gli `icon_url` dei plugin;
  - `mkdocs_src/docs/static/icons/brokers/scalable.png`, `scalable-broker.png` e `scalable-deposit.png`, per la guida.
- `--check` verifica che i file siano aggiornati.

**Uso**:
- La guida dice di impostare il plugin predefinito di ogni broker: l'icona compare da sola (F9, F10).
- Chi vuole fissarla può incollare l'`icon_url` del plugin nella scheda URL del selettore.

**Marchio**: il logo resta intatto, con il simbolo nell'angolo, e la guida dice «not affiliated». È un uso nominativo per riconoscere il broker; rischio basso, accettato dal developer.

## 7. Assistente di import: il file fuori dal formato del broker

### 7.1 Backend

- **Schemi** in `backend/app/schemas/brim.py`:
  - `BRIMRefusal`: `code` opzionale, `message` (la frase inglese), `context`;
  - `BRIMPluginCheck`: `plugin_code`, `can_parse`, `refusal`.
- **Contratto** in `brim_provider.py`: nuovo metodo facoltativo `cannot_parse_detail(file_path) -> Optional[BRIMRefusal]`.
  - Di default avvolge `cannot_parse_reason`, con `code` vuoto. I plugin esistenti non cambiano.
  - Non deve mai sollevare eccezioni: in caso di errore vale `None`.
- **Endpoint**: `GET /api/v1/brokers/import/files/{file_id}/plugin-check?plugin_code=…`.
  - Accesso come agli altri file del broker.
  - Esegue `can_parse` e, se falso, `cannot_parse_detail`, in `asyncio.to_thread`.
  - Plugin sconosciuto: 404.
  - Dopo l'aggiunta: `./dev.py api sync`.
- **Test**:
  - del contratto, per ogni plugin e campione: `None`, oppure un codice valido più una frase;
  - dell'API.
- **Guida**: una sezione nuova accanto a «Saying why a file is refused».

### 7.2 Frontend

- **Funzione pura** in `frontend/src/lib/utils/brim/defaultPluginCheck.ts`, testata con Vitest.
  - Input: il file caricato, il suo broker, tutti i broker.
  - Output:
    - se il plugin predefinito manca dai `compatible_plugins`;
    - i plugin che leggono il file;
    - i broker che hanno uno di quei plugin come predefinito.
- **Modale nuova**: `frontend/src/lib/components/transactions/modals/ImportBrokerMismatchModal.svelte`.
  - Si apre dopo il caricamento, una per file, in sequenza.
  - Mostra il nome del file, il broker, il suo plugin predefinito, il motivo del plugin tradotto (§10) e la proposta: «lo legge ‹plugin›, predefinito di ‹broker›».
  - **Sposta in ‹broker›**: carica il file nel broker proposto con lo stesso `batch_id`, poi cancella l'originale. Con più broker possibili, si sceglie da un elenco.
  - **Tienilo qui**: comportamento di oggi (F12).
  - **Rimuovi**: cancella il file caricato.
- **Aggancio** in `ImportWizardModal.svelte`, dopo `uploadAllPendingFiles`.
  - Senza plugin predefinito, nessuna modale.
  - Se nessun plugin legge il file, la modale mostra il motivo del plugin predefinito (per esempio la colonna mancante) e offre «Tienilo qui» e «Rimuovi».
- **Generale**: protegge ogni broker, non solo Scalable.

## 8. Editor in blocco: suggerimento anche per gli import separati

Riguarda `TransactionBulkModal.svelte`, solo il frontend; il backend lo supporta già (F5).

1. La ricerca nel database (`promote-suggest`) include anche le righe nuove non collegate, con id negativi.
2. I suggerimenti importabili (💡) valgono anche per le righe nuove.
3. Il banner propone anche le coppie nuova + salvata. `executePromote` ha già il ramo misto.
4. L'abbinamento si estrae in `frontend/src/lib/utils/transactions/promoteSuggest.ts`, testabile con Vitest.

Effetto: chi importa il conto deposito un mese dopo il broker si vede proporre l'unione con le righe salvate già durante la revisione dell'import.

## 9. Duplicati dopo l'unione (core)

In `detect_tx_duplicates` (`brim_provider.py:2025`), un DEPOSIT o WITHDRAWAL in arrivo cerca anche i lati `CASH_TRANSFER` e `FX_CONVERSION` già salvati con stesso segno, data e importo.

- **Perché**: «Dall'ultima» riparte dal giorno dell'ultimo export, incluso. Senza questa correzione, un trasferimento già unito torna come nuovo e la cassa raddoppia.
- **Ambito**: vale per tutti i plugin.
- **Test**: un test nuovo dei servizi BRIM.

## 10. Traduzioni

Tutte e quattro le lingue, con lo strumento della skill `devpy-i18n` (`./dev.py i18n …`) e l'audit di parità tra i cataloghi.

| Testi | Chiavi |
|---|---|
| Avvisi dei plugin Scalable (§4.5) | `importWizard.brimNotice.scalable_*`, con i valori del contesto (conteggi, righe) |
| Motivi di rifiuto (§4.2) | `importWizard.parseRefusal.<code>`, namespace nuovo, con il nome del plugin dal contesto |
| Modale (§7.2) | titolo, testi, pulsanti, elenco dei broker |
| Editor in blocco (§8) | solo se servono testi nuovi; meglio riusare quelli del banner |

- **Lingua del file.** La regola di DEGIRO (avvisi nella lingua del file) qui non dà nulla: i file di Scalable sono sempre in inglese, quindi vince la lingua dell'interfaccia. Il testo inglese del plugin resta il ripiego, come oggi.
- **Documentazione.** La pagina utente va scritta in inglese prima del 14/10 ed entra nel giro di traduzioni (italiano, francese, spagnolo) con il resto della documentazione. Lo stesso vale per la card dell'indice: io scrivo solo `index.en.md`, come assegnato dal coordinatore.

## 11. Documentazione

Pagina utente `mkdocs_src/docs/user/transactions/import/scalable.en.md`, una per i due plugin, scritta da `docs-writer`. Sezioni:

- avviso «Alpha»;
- cosa esportare: l'esportatore, consigliato, con link al repo e i passi «scarica, verifica, installa, esporta»; il CSV Prime, solo PRIME e PRIME+ e solo broker;
- due broker:
  - creazione, con un plugin predefinito diverso per ciascuno;
  - l'icona, che compare da sola;
- import:
  - ogni file nel suo broker, insieme o in momenti diversi;
  - la modale, se un file finisce nel broker sbagliato;
  - l'unione dei trasferimenti;
- «Un broker solo?»: effetti, e perché lo stesso file non va importato in due broker;
- cosa viene importato (§4.3) e i limiti (§4.5).

Altre superfici:
- **Indice**: card «Scalable Capital» in `index.en.md`, «🔬 Alpha · …», accanto a Trade Republic. Italiano, francese e spagnolo con il giro del 14/10.
- **Navigazione**: `mkdocs.yml`, sotto «📈 Stocks & ETFs», con i `nav_translations`.
- **Elenco dei provider**: `providers_list.md`, due righe, una per plugin.
- **Guida BRIM**: `cannot_parse_detail`, l'endpoint, i rifiuti tradotti.
- **Assistente di import**: la pagina dev `developer/frontend/components/features/import-wizard.md` e la pagina utente su come si importa, per la modale.
- **Da non toccare** (sono di M): `user/connection-security.en.md`, `user/files/index.en.md`, `admin/cli_tools.en.md` e le pagine della gallery.
- **CHANGELOG** 1.2.0: il file è del coordinatore, io propongo le righe a ogni checkpoint. Bozza:
  - **✨ Added**: «Scalable Capital importers, alpha: broker and overnight account as two brokers», con l'esportatore e le icone; «Import wizard: a file outside the broker's format is flagged, with the plugin's reason and where it belongs»; «Bulk editor: merge suggestions for transfers imported separately».
  - **🐛 Fixed**: duplicati dei trasferimenti uniti.
- **Verifica**: `mkdocs build` in modalità strict e `check-links`, mai `serve`; `translate-validate`.

## 12. Test

**Automatici:**

| Test | Dove | Esecuzione |
|---|---|---|
| Suite generica sui due plugin (riconoscimento, contratto, segni, asset, idempotenza, Windows-1252) | `test_external/test_brim_providers.py`, automatica con i campioni | `test external brim-providers` |
| Contratto di `cannot_parse_detail` | stesso file, test nuovo | idem |
| Regole Scalable (layout, rifiuti e codici, mappatura e gambe, lordo e netto, stati, storni, id nella descrizione, tag, numeri, file misti, più conti deposito, rete 1.0.0) | `test_external/test_brim_scalable.py`, registrato come `brim-scalable` in `scripts/test_runner/_backend_external.py` | `test external brim-scalable` |
| Endpoint `plugin-check` | test API, registrato nel runner | corsia 6163 |
| Duplicati di un `CASH_TRANSFER` (§9) | suite dei servizi BRIM | `services` |
| Unione tra due broker: import dei campioni, `promote-suggest` trova le coppie, promozione, nuovo import riconosciuto come duplicato | test API | corsia 6163 |
| Tutto in un broker: nessun errore, cassa = somma, nessuna coppia, rendimenti invariati | stesso modulo API | corsia 6163 |
| Funzioni pure: plugin predefinito e abbinamento nuova + salvata | Vitest | `front-utility` |
| E2E: (a) file del conto deposito nel broker dei titoli, con modale, motivo tradotto, «Sposta»; (b) import insieme, con il banner; (c) broker salvato, poi conto deposito, con il suggerimento durante l'import | Playwright in `frontend/e2e/transactions/`, registrato nel runner | corsia 6163, dopo `npm ci` |
| Icone | `--check` dello script | |
| R13 e parità i18n | `optionFilter.test.ts`, audit di `./dev.py i18n` | `front-utility core-unit` |

**Umano** (developer, con i CSV veri, mai nel repo):

1. Esportatore 1.0.1: export di tutto lo storico.
2. Due broker, ciascuno con il suo plugin predefinito: le icone compaiono da sole.
3. Il file del conto deposito assegnato per errore al broker: compare la modale, «Sposta» funziona.
4. Import dei due file **insieme**: il banner propone le coppie; unirle; i saldi coincidono con l'app.
5. Su broker nuovi, import **separato**: il suggerimento compare durante il secondo import.
6. «Dall'ultima» e nuovo import: i trasferimenti già uniti risultano duplicati.
7. Interfaccia in italiano: modale, motivi e avvisi tradotti.

`test-author` scrive i test nuovi, in file distinti, con le regole della corsia.

**Rossi previsti**:
- `test_all_plugins_used_at_least_once` finché mancano i campioni;
- `TestGenericCSVPlugin` sui nuovi CSV (eventuale esclusione, come per Danske);
- `mkdocs build` in modalità strict.

## 13. Superfici (assegnate dal coordinatore il 2026-10-09)

**Mie:**
- **Contratto BRIM**:
  - `brim_provider.py`: il metodo facoltativo (§7.1); nello stesso file anche i duplicati (§9), come proposto e approvato dal developer. Da ricordare al coordinatore al primo checkpoint;
  - `schemas/brim.py`;
  - l'endpoint in `api/v1/brokers.py`, con il client generato da `api sync`;
  - `test_external/test_brim_providers.py` e i test API.
- **Assistente di import**: `ImportWizardModal.svelte`, la modale nuova e la util.
- **i18n**: i cataloghi delle quattro lingue, **solo con `dev.py i18n`**. Se a D servono chiavi, coordina il coordinatore.
- **Documentazione**:
  - le pagine nuove, la guida BRIM, le pagine dell'assistente, `providers_list.md`;
  - in `mkdocs.yml`: la nav e i `nav_translations`;
  - la card in `index.en.md`. Le card in italiano, francese e spagnolo arrivano con il giro di traduzioni del 14/10.
- **Runner**: solo righe aggiunte.
- **Cartelle e file nuovi**: `brim_providers/static/scalable/`, `mkdocs_src/docs/static/icons/brokers/`, `scripts/compose_broker_icons.py` (con `scripts/assets/brokers/`), i due plugin, il modulo comune, i campioni e il loro README, `test_brim_scalable.py`.
- **`TransactionBulkModal.svelte`** (passo 11): **solo dopo** il treno con lo step 23 di K e un mio aggiornamento di baseline, perché lì lo stesso file è cambiato.

**Non mie:**
- `CHANGELOG.md` è del coordinatore: propongo le righe a ogni checkpoint.
- File di M, da non toccare: `user/connection-security.en.md`, `user/files/index.en.md`, `admin/cli_tools.en.md` e le pagine della gallery.

**Fuori dal monorepo**: il repo `librefolio-exporter` (§5).

**Journal e devWiki**:
- la cartella `37_brimScalable/`, con il piano e il riepilogo;
- `wiki-file` alla fine: due plugin per due conti, id nella descrizione, lordo in Prime, il controllo del plugin predefinito, i suggerimenti nuova + salvata, i duplicati dei trasferimenti uniti.

**Regole della corsia**:
- `npm ci` concesso, solo dal lock: niente update né `audit fix`;
- porta 6163 e `/tmp/librefolio-r2-s`;
- un checkpoint almeno per ogni gruppo di passi verdi, con le righe del CHANGELOG proposte.

## 14. Passi e linea di taglio

1. ✅ (2026-10-09) **Piano nel journal**, dopo la conferma della baseline `3cceb4f90`; il riepilogo va nella stessa cartella.
2. 🚧 **Esportatore 1.0.1** (§5) e prova del developer. Codice e test fatti, in stage nel repo dell'esportatore; mancano commit, prova sul conto vero e tag del developer.
3. ✅ (2026-10-09) **Campioni sintetici** (§4.6).
4. ✅ (2026-10-09) **Contratto `cannot_parse_detail`**, schemi, endpoint, `api sync` e test (§7.1).
5. ✅ (2026-10-09) **I due plugin e il modulo comune** (§4), con `test_brim_scalable.py` e la registrazione nel runner.
6. ✅ (2026-10-09) **Duplicati dei trasferimenti uniti** (§9).
7. ✅ (2026-10-09) **Test API**: unione tra due broker e caso «tutto in un broker».
8. ✅ (2026-10-09) **Icone** (§6).
9. ✅ (2026-10-09, inglese) **Documentazione** (§11): pagina inglese prima del 14/10, card in `index.en.md`, navigazione, elenco dei provider, guida BRIM, pagine dell'assistente; righe di CHANGELOG proposte al coordinatore. Pagina, card, nav, elenco, guida BRIM, pagine dell'assistente e deduplica in `architecture.md` fatti.
10. ✅ (2026-10-09) **Modale dell'assistente** (§7.2) e traduzioni (§10): `npm ci` dal lock, util, Vitest, E2E (a).
11. ✅ (2026-10-09) **Editor in blocco per gli import separati** (§8): util, Vitest, E2E (b, c). Partito dopo il treno 25 (step 23 di K) e il merge `5eb01e2ea`.
12. **Prova umana** del developer e correzioni.
13. **Controlli finali**: lint e format, tutte le suite, mkdocs, porte libere; handoff. Le note per la devWiki vanno nell'handoff: il coordinatore ha chiesto di non scrivere in `LibreFolio_devWiki/` (niente `wiki-file`) finché non lo dice lui.

**Ritmo.** I passi 2, 3, 4 e 8 sono indipendenti. `test-author` e `docs-writer` lavorano in parallelo su file distinti.

**Checkpoint**, ciascuno con le righe di CHANGELOG proposte:
- **CP1**: passi 1, 3 e 4 (piano, campioni, contratto ed endpoint). L'esportatore 1.0.1 va nel suo repo, con un commit a parte del developer;
- **CP2**: passi 5, 6 e 7 (plugin, duplicati, test API);
- **CP3**: passi 8 e 9 (icone e documentazione), comunque prima del 14/10;
- **CP4**: passo 10 (modale e traduzioni);
- **CP5**: passo 11 (editor in blocco), dopo il treno di K;
- **finale**: passi 12 e 13.

**Linea di taglio.** I passi 1-10 non si tagliano. Se all'ultimo checkpoint prima del 13/10 qualcosa non è verde, l'ordine è:
1. il passo 11 passa a una 1.2.x; la guida dice di importare i due file nella stessa sessione;
2. se serve ancora tempo, la modale perde il motivo del plugin, ma resta con la proposta del plugin e del broker.

## 15. Rischi

- **Scadenza.** Sono quattro giorni, weekend compreso, con tre modifiche al core: contratto ed endpoint, assistente di import, editor in blocco. Il developer deve esserci per autorizzazione, esportatore 1.0.1, commit dei checkpoint e prova umana.
- **File grandi e contesi**: `ImportWizardModal.svelte` e `TransactionBulkModal.svelte`. Le util pure riducono le modifiche al componente; i conflitti li coordina il coordinatore.
- **Infrastruttura frontend**: senza `npm ci` non partono Vitest, E2E, R13 e `svelte-check`.
- **Semantica Prime.** È ricavata da due export pubblici, e mancano campioni reali di vendite, dividendi, storni e crypto. Per questo: «Alpha», avvisi invece di supposizioni, mai importi ricalcolati (solo somme di valori del file).
- **Contratto BRIM.** Il metodo nuovo è facoltativo e ha un default: i 34 plugin esistenti non cambiano. Il test di contratto li copre tutti.
- **Duplicati (§9)**: aggiunge solo candidati; da provare contro la suite BRIM completa.
- **Icone servite con la sessione**: l'endpoint richiede l'accesso; nell'app va bene, nella guida si usano le copie di mkdocs.

## 16. Definition of done

- **Esportatore 1.0.1** rilasciato e documentato; export reale del developer verificato.
- **Plugin.**
  - I due plugin leggono i tre formati e si rifiutano a vicenda con un codice.
  - La suite generica, `brim-scalable` e R13 sono verdi.
  - Tre campioni sintetici sono nel README.
- **Core.**
  - `cannot_parse_detail` ed endpoint, con test, `api sync` e guida.
  - Duplicati dei trasferimenti uniti corretti, senza regressioni nella suite BRIM.
- **Test di integrazione.**
  - I due test API (unione e un broker) sono verdi.
  - Modale con Vitest ed E2E (a) verdi.
  - Editor in blocco con Vitest ed E2E (b, c) verdi, oppure taglio documentato.
- **Traduzioni** complete nelle quattro lingue, con audit pulito.
- **Icone** generate (`--check` pulito), visibili nell'app tramite il plugin predefinito e nella guida.
- **Documentazione.**
  - Pagina inglese, card in `index.en.md`, navigazione con i `nav_translations`, elenco dei provider, guida BRIM, pagine dell'assistente; righe di CHANGELOG proposte al coordinatore.
  - `mkdocs build` in modalità strict e `check-links` puliti.
  - `translate-validate` eseguito; pagina nel giro del 14/10.
- **Lint e format**: ruff e black; prettier e `svelte-check` sui file toccati.
- **Prova umana** superata (§12).
- **Chiusura**: piano del journal aggiornato a ogni passo; `wiki-file`; handoff; porta 6163 libera.

## 17. Cosa serve dal developer

1. ~~Autorizzazione del piano, tramite il coordinatore~~: data il 2026-10-09 alle 15:29.
2. Prova dell'esportatore 1.0.1 e tag `v1.0.1`.
3. Commit dei checkpoint, quando il coordinatore li chiede.
4. Disponibilità nel weekend per le prove (§12).
5. ~~Permesso per `npm ci` nel worktree~~: concesso, solo dal lock.
6. Fast-forward della worktree a `3cceb4f90` (treno 24b), poi al treno con lo step 23 di K prima del passo 11.

## 18. Avanzamento

### Passo 1 — Piano nel journal ✅ (2026-10-09)

> **Note implementazione**: piano copiato dalla sessione S con l'intestazione del journal (§0). Tolti i riferimenti ai file della sessione e i valori reali del conto del developer (F2 in §3, prova in §5). Il riepilogo della fase dell'esportatore è in [`recap-phase00ScalableExporter.md`](recap-phase00ScalableExporter.md), con i riferimenti alla sessione riscritti.

### Passo 3 — Campioni sintetici ✅ (2026-10-09)

> **Note implementazione**: tre file in `sample_reports/`, con valori inventati sulla struttura reale: `scalable-prime-export.csv` (14 colonne, 15 righe), `scalable-broker-export.csv` (23 colonne, 19 righe, semantica dell'esportatore 1.0.1) e `scalable-deposit-export.csv` (19 colonne, 8 righe). ISIN di titoli pubblici, l'IBAN d'esempio della documentazione, id e riferimenti finti (`synthB…`, `SYNTHC…`, `synthD…`, `SCALPRIME…`, `SCALEXPORT…`). I trasferimenti interni sono speculari tra broker e conto deposito (2026-04-02 −1000/+1000, 2026-06-01 +300/−300). Caratteri non ASCII («Ü», «ä») per il test Windows-1252. Sezione nel `README.md` dei campioni. Controllo: larghezza di ogni riga, LF, newline finale.
>
> **⚠️ Fuori pista**: nell'esportatore un ordine eseguito in parte (`PARTIAL_FILLED`, scritto `Pending`) ha i dettagli: riferimento, prezzo, `fee` e `tax`. Gli interessi del conto deposito hanno `tax` ma `fee` vuota (`mapping.js`). Il campione segue il codice, non l'ipotesi del piano.

### Passi 4, 5 e 6 — Contratto, plugin, duplicati: codice 🚧 (2026-10-09)

> **Note implementazione**:
> - **Contratto**: `BRIMRefusal` e `BRIMPluginCheck` in `schemas/brim.py`; `BRIMProvider.cannot_parse_detail`, concreto, che di default avvolge `cannot_parse_reason`; `check_file_with_plugin(file_id, plugin)` in `brim_provider.py`, che non solleva mai e riprova sul percorso nuovo se un parse concorrente ha spostato il file; `GET /brokers/import/files/{file_id}/plugin-check?plugin_code=` in `brokers.py`. `api sync` verde; il client generato (ignorato da git) contiene l'endpoint.
> - **Conferma del developer** (2026-10-09, domanda «riusi quello di DEGIRO/Danske?»): «Avanti così: base `cannot_parse_reason`, più codice per le traduzioni ed endpoint al caricamento». L'elenco ordini di DEGIRO (accetta il file e avvisa) non va: la modale non scatterebbe mai; il 422 `set_required` di Danske riguarda solo i report set.
> - **Plugin**: `_scalable.py` (lettura, riconoscimento, rifiuti, mappatura, avvisi) e due file piccoli, `broker_scalable.py` e `broker_scalable_deposit.py`, con i letterali che R13 legge. Prova a mano sui tre campioni: 17, 19 e 9 transazioni, nessun errore di validazione, avvisi e rifiuti come da §4.
> - **Duplicati**: in `detect_tx_duplicates` un DEPOSIT o WITHDRAWAL cerca anche i lati `CASH_TRANSFER` e `FX_CONVERSION` (`_MERGED_LEG_TYPES`), con lo stesso segno. Su un lato unito la descrizione combacia se contiene quella in arrivo: l'unione delle descrizioni (`mergeStrings`) le unisce con un a capo.
> - **Test**: due `test-author` in parallelo, su file distinti: (a) `test_brim_scalable.py`, contratto in `test_brim_providers.py`, endpoint in `test_brim_api.py`, runner `brim-scalable` esterno; (b) duplicati in `test_db/test_brim_db.py`, flusso API in `test_api/test_brim_scalable_api.py`, runner `brim-scalable` API.
>
> **⚠️ Fuori pista**:
> - **Due avvisi in più** rispetto a §4.5: `scalable_dividends_net` (info: dividendo senza `tax`, importato netto; l'esportatore non legge i dettagli dei dividendi, quindi riesportare non serve) e `scalable_unreadable_rows` (warning: data, importo, valuta, quantità o titolo mancanti).
> - **Segno delle righe di cassa**: decide il segno di `amount`; un segno contrario all'etichetta (per esempio un `Fee` positivo) diventa deposito o prelievo, con `scalable_cash_by_sign`.
> - **`test_file_pattern`** del broker è `scalable-broker`, non `scalable`: il test di rilevamento per nome lo cerca anche nel campione del conto deposito.
> - **Duplicati, livello**: una riga «possibile» viene selezionata di default (`duplicateStatusAllowsAutoSelect`); per non raddoppiare la cassa, il lato unito che contiene la descrizione in arrivo vale «probabile».
> - **`npm ci`** (dal lock, verde): npm 11 non ha eseguito gli script di installazione di `esbuild` e `fsevents` (avviso `install-scripts`). Non li ho approvati: se Vitest o la build ne risentono, lo segnalo al coordinatore.

### Passo 8 — Icone ✅ (2026-10-09)

> **Note implementazione**: `scripts/compose_broker_icons.py` riusa costanti e helper di `compose_asset_type_icons.py` (`fit`, `differs`, la geometria della pastiglia) senza modificarlo: la sua `compose()` legge solo dalla cartella dei tipi di asset, quindi ne ho una copia di dieci righe che parte dal logo del broker. Base `scripts/assets/brokers/scalable.png`, il PNG 192×192 di Scalable (`assets.scalable.capital/touch-icons/android-chrome-192x192.png`, scaricato una volta). Uscite: `brim_providers/static/scalable/{broker,deposit}.png` e `mkdocs_src/docs/static/icons/brokers/scalable{,-broker,-deposit}.png`. Pastiglia `stock` per il broker, `liquidity` per il conto deposito. `--check` verde; anteprima controllata su fondo chiaro e scuro.
>
> **⚠️ Fuori pista**: il riepilogo della fase export proponeva SVG Phosphor (grafico, salvadanaio); il piano approvato usa le icone dei tipi di asset, come le composte esistenti. Se il developer preferisce altri simboli basta cambiare `ACCOUNTS` nello script.

### Passo 10 — Modale e traduzioni: codice 🚧 (2026-10-09)

> **Note implementazione**:
> - `frontend/src/lib/utils/brim/defaultPluginCheck.ts`: `findDefaultPluginMismatch` (pura) e `resolveParseRefusalMessage` (chiave `importWizard.parseRefusal.<code>`, ripiego sulla frase del plugin resa frase).
> - `ImportBrokerMismatchModal.svelte`: motivo del plugin, uno o più broker di destinazione, **Sposta**, **Tienilo qui**, **Rimuovi**; chiudere vale «tieni».
> - `ImportWizardModal.svelte`: dopo il caricamento del passo 1, `reviewDefaultPluginMismatches` apre una modale per file; «Sposta» ricarica lo stesso file nel broker scelto con lo stesso `batch_id` e poi cancella la copia vecchia; «Rimuovi» la cancella; se non resta nessun file l'assistente rimane al passo 1. Alla chiusura dell'assistente un prompt aperto vale «tieni».
> - **Traduzioni** con `dev.py i18n add`: 29 chiavi × 4 lingue (13 della modale, 4 rifiuti, 12 avvisi Scalable, plurali ICU su `{count}`). Termini allineati al catalogo: «editor bulk» / «éditeur groupé» / «editor masivo»; il tipo CASH_TRANSFER come «Bonifico» / « Virement » / «Transferencia bancaria». Audit: 4244 chiavi complete, nessuna inutilizzata.
> - Controlli: `npm run check` 0 errori e 0 avvisi; Prettier pulito sui file toccati.
>
> **⚠️ Fuori pista**: il tipo TypeScript generato da `openapi-zod-client` aggiunge un ramo `Array` impossibile ai campi oggetto opzionali (`anyOf` + `null`). Lo schema Zod di runtime è corretto; nell'assistente c'è un cast locale e commentato verso `ParseRefusal`.

### Passo 2 — Esportatore 1.0.1: codice ✅, prova del developer ⏳ (2026-10-09)

> **Note implementazione** (sub-agente nel repo `librefolio-exporter`, rivisto da me):
> - `queries.js`: la query dei dettagli chiede di nuovo `tradeTransactionAmounts.marketValuation`.
> - `mapping.js`: con i dettagli letti, `amount` è `marketValuation` con il segno dell'operazione (BUY negativo, SELL positivo, altrimenti il segno dell'importo della lista); senza dettagli, o senza il valore, resta l'importo della web app. In `FIELDS` il campo va nella colonna Prime `amount`: il file del broker resta a 23 colonne.
> - Test 113 → 117, tutti verdi; `npm run check` verde (manifest 1.0.1); `docs/formats/scalable.md`, CHANGELOG 1.0.1, README con il link alla guida LibreFolio e senza «0.x».
> - In stage (`git add -A`); messaggio proposto in `/tmp/libreFolio_commit_exporter_101.txt`.
>
> **⚠️ Fuori pista**:
> - Il link del README alla pagina `…/import/scalable/` dà 404 finché la documentazione della 1.2.0 non è pubblicata.
> - Il nome del campo si conferma solo sul conto vero. Se fosse sbagliato, GraphQL rifiuterebbe la query dei dettagli: il pannello avviserebbe e nessun dato sbagliato verrebbe scritto.
> - Se un'operazione con i dettagli arrivasse senza `marketValuation`, l'importo resterebbe con la commissione: lo segnala l'avviso `scalable_fee_in_amount` del plugin.

### Passo 9 — Documentazione: prima parte ✅ (2026-10-09)

> **Note implementazione** (`docs-writer`, rivisto da me):
> - Pagina nuova `user/transactions/import/scalable.en.md`: avviso Alpha, due conti e due broker, l'esportatore (installazione con verifica dello ZIP, export, «Since last», avviso sui file della 1.0.0), il CSV di Scalable, broker e plugin predefiniti con le icone, import e modale, trasferimenti, «One broker only?», cosa si importa, avvisi, limiti.
> - Card in `index.en.md` (tra Danske Bank e Trade Republic), voce di nav sotto «📈 Stocks & ETFs» (nome proprio: niente `nav_translations`), due righe Alpha in `providers_list.md`, sezione «Saying why with a code» (`#cannot-parse-detail`) nella guida BRIM, con la nota sui moduli con il trattino basso.
> - `dev.py mkdocs build` strict verde. `check-links`: la pagina nuova è a posto; l'uscita 1 viene da `#rolling-return`, rosso già sulla baseline. `translate-validate`: debito atteso (pagina e card in IT/FR/ES, nel giro del 14/10).
>
> **⚠️ Fuori pista**:
> - **Icone della guida**: `dev.py mkdocs build` cancella `mkdocs_src/docs/static/icons/` e la ricopia da `frontend/static/icons/` (`copy_docs_assets`). Lo script ora le scrive in entrambe, come le composte dei tipi di asset. Cartella nuova `frontend/static/icons/brokers/`, da segnalare al coordinatore.
> - **Ancore tolte** dalla pagina (`#bulk-workspace`, `#link-pairs`, `#review`): esistono solo in inglese e la pagina, finché non è tradotta, si costruisce anche nelle altre lingue. Si possono rimettere dopo il giro del 14/10.
> - **Per il giro del 14/10**: nelle card IT/FR/ES il percorso dell'icona vuole un `../` in più (`../../../../static/icons/brokers/scalable.png`).
> - **Avvisi in più nella pagina**: chi aveva importato un file della 1.0.0 deve prima cancellare le operazioni segnalate (gli importi cambiano, quindi non tornano come duplicati); chi cambia fonte (CSV di Scalable ↔ esportatore) ritrova le righe come duplicati «possibili», ancora selezionati.
> - **Classificazione**: decide `type`; `lf_subtype` serve per i trasferimenti interni. Il piano (§4.3) diceva «`lf_subtype` quando c'è», ma per le operazioni dice solo SINGLE o SAVINGS_PLAN, non la direzione.

### Passi 6 e 7 — Duplicati e test API ✅ (2026-10-09)

> **Note implementazione** (test di `test-author`, eseguiti da me nella corsia 6163):
> - `test_db/test_brim_db.py`, classe `TestMergedPairDuplicates` (DD-011…DD-017, 11 casi): ogni lato è «probabile» contro il proprio lato unito; descrizione riscritta → «possibile»; segno opposto → unico; coppia FX; FEE, TAX e INTEREST non guardano i lati uniti; stesso tipo con testo solo contenuto → resta «possibile»; testo vuoto → mai «probabile».
> - `test_api/test_brim_scalable_api.py` (runner `api brim-scalable`): SC-A01, i due campioni in due broker, `promote-suggest` trova esattamente le coppie, unione con descrizione unita, reimport con i trasferimenti «probabili» contro i lati uniti; SC-B01, tutto in un broker: nessuna coppia proposta, saldo EUR uguale alla somma delle righe di cassa dei due file.
> - Comandi: `db create` (prima volta nella corsia), poi `db brim` **28 passed** e `api brim-scalable` **2 passed**; porta 6163 libera dopo.
>
> **⚠️ Fuori pista**:
> - La cartella della corsia `/tmp/librefolio-r2-s` non esisteva: il primo `db brim` è fallito con «unable to open database file», prima dei test. Risolto con `test db create` sulla cartella assegnata, nuova, quindi senza dati da perdere.
> - `promote-suggest` esclude dai candidati tutti gli id della richiesta: il test chiede una riga per volta.

### Passi 4 e 5 — Contratto e plugin: test ✅ (2026-10-09)

> **Note implementazione** (test di `test-author`, eseguiti da me nella corsia 6163):
> - `test_external/test_brim_scalable.py` (runner `external brim-scalable`): identità, riconoscimento su 23 file per i due plugin (BOM, colonne riordinate, intestazione sola, file misti, conto sconosciuto…), i tre campioni riga per riga, avvisi con righe e conteggi, casi limite di stati, operazioni, proventi, cassa, righe non lette. **133 passed**.
> - `test_brim_providers.py`: classe `TestPluginSaysWhyWithACode` (contratto di `cannot_parse_detail` per ogni plugin e campione) e i tre campioni Scalable in `CONTRACT_SAMPLES`. `external brim-providers` **694 passed, 1 skipped** (DEGIRO, già sulla baseline).
> - `test_brim_api.py`, categoria 17, `TestPluginCheckEndpoint` (RS-PC01…07): rifiuto con codice e contesto, accettazione, file non Scalable, rifiuto senza codice del CSV generico, 404 per plugin e file sconosciuti, 422 senza `plugin_code`, VIEWER sì e utente senza accesso 403, stato del file invariato. `api brim` **87 passed**.
> - `check-orphans` verde; `front-utility core-unit` (R13) **3654 passed**; lint e format puliti sui file nuovi. Porta 6163 libera dopo ogni giro.
>
> **⚠️ Fuori pista**:
> - Il primo `test-author` ha chiuso il primo giro senza file né rapporto; al secondo giro, sullo stesso agente, ha consegnato tutto.
> - Al primo giro di `external brim-scalable`, 5 rossi erano difetti dei test (un `Counter` confrontato con le tuple delle righe, un `isin` passato due volte): corretti dal `test-author`, prodotto invariato.
> - `history_tag` del plugin del conto deposito ora vale `scalable`, come il tag delle sue transazioni.
> - `scripts/test_runner/_backend_external.py` non era formattato con black già sulla baseline: le righe aggiunte seguono lo stile del file e non l'ho riformattato.

### Passo 10 — Correzioni dopo la lettura del `test-author` frontend (2026-10-09)

> **⚠️ Fuori pista**: leggendo il codice per scrivere i test, il `test-author` ha trovato tre problemi veri, corretti nel prodotto:
> 1. **Report set (decisione A18)**: un membro Danske caricato in un broker col CSV generico come predefinito avrebbe aperto la modale e rotto `tx-import-report-set` (A18, G-C, G-real). Ora un file letto da un plugin di report set non viene mai messo in discussione (`options.reportSetPlugins`). Verifica: `front-transaction tx-import-report-set` **32 passed** (32 saltati, i casi mobile come sulla baseline).
> 2. **Destinazioni**: il CSV generico legge anche i file Scalable, quindi un broker col generico come predefinito poteva comparire primo. Ora le destinazioni seguono l'ordine di `compatible_plugins` (miglior plugin prima) e i broker con un plugin di ripiego (`detection_priority` < 50) restano solo se non ce n'è uno specifico (`options.fallbackPlugins`).
> 3. **Doppio «Continua»**: mentre l'assistente chiede il motivo al plugin, un secondo clic saltava il controllo. Ora `mismatchReviewing` tiene il pulsante disabilitato, con lo spinner, fino alla fine del controllo.
>
> Altri due punti del `test-author`, lasciati come sono: se lo spostamento fallisce resta un messaggio d'errore e il file nel broker di partenza; il seed `populate_mock_data` imposta un campo `brim_plugin_key` che il modello del broker non ha (fuori dal mio perimetro, da segnalare al coordinatore).

### Passo 10 — Modale e traduzioni: test ✅ (2026-10-09)

> **Note implementazione** (test di `test-author`, eseguiti da me nella corsia 6163):
> - `frontend/src/lib/utils/brim/defaultPluginCheck.test.ts`: **37 passed** (ordine per priorità, esenzione dei report set, filtro dei ripieghi, traduzione dei rifiuti), registrato in `tx-unit` (**722 passed**).
> - `frontend/e2e/transactions/tx-import-broker-mismatch.spec.ts` (runner `front-transaction tx-import-broker-mismatch`): M1 sposta il file del conto deposito dal broker al conto deposito (account usa e getta, con un terzo broker sul CSV generico che non deve comparire tra le destinazioni; «Continua» disabilitato con la modale aperta); M2 nessuna domanda sul broker giusto; M3 «Rimuovi» e l'assistente resta al passo 1. **3 passed** con `--fresh-run` e **3 passed** con `--workers 4`.
> - Regressioni del passo 1: `tx-import-report-set` 32 passed (32 mobile saltati), `tx-import-upload` 9, `tx-import-flow` 10, `tx-import-degiro` 4, `tx-brim-import` 8; tutte verdi.
> - `npm run check` 0 errori e 0 avvisi; Prettier pulito.
>
> **⚠️ Fuori pista**: dagli ultimi dubbi del `test-author`, il flag è diventato `step1Continuing` e copre tutta la prosecuzione del passo 1 (caricamento, controllo del plugin predefinito, controllo dei report set). Si azzera in un `finally` sull'intera catena, così un errore non lascia «Continua» bloccato.

### Checkpoint 1 — passi 1, 3–10 (2026-10-09)

> Mandato al coordinatore dopo il treno 25 (`dev_release2` = `586a4f0ea`, con lo step 23 di K): il passo 11 (`TransactionBulkModal.svelte`) parte dopo il merge di `dev_release2` nel mio ramo. Stato: FROZEN fino alla risposta.

### Passo 11 — Editor in blocco per gli import separati: codice 🚧 (2026-10-09)

> **Baseline**: `5eb01e2ea` (`merge: train 25 into S for step 11`, parent `305b80202`, il checkpoint 1, e `586a4f0ea`); `TransactionBulkModal.svelte` assegnato dal coordinatore dopo lo step 23 di K.
>
> **Note implementazione**:
> - `frontend/src/lib/utils/transactions/promoteSuggest.ts`: `newRowSuggestId` (id negativo `-(createdSeq + 1)`), `mixedPromotePairs` (coppie nuova × salvata nella finestra di date, con la regola di abbinamento passata dal componente) e `importableSuggestions` (i candidati del database non ancora nell'editor, per riga, per `tempId`).
> - `TransactionBulkModal.svelte`:
>   - `promote-suggest` riceve anche le righe nuove non collegate (`isSuggestable`: tipo, broker, data e un importo o una quantità non nulli). Senza importo il backend salta il controllo «importi opposti» e restituirebbe ogni deposito o prelievo della finestra;
>   - il 💡, nella barra e sulla riga, vale anche per le righe nuove;
>   - il banner propone anche le coppie nuova + salvata; «Unisci» passa dal ramo misto già esistente di `executePromote`.
> - Pagina Scalable: il caso «file importati in momenti diversi» ora passa dal 💡 durante il secondo import.
> - Controlli: `npm run check` 0 errori e 0 avvisi; Prettier pulito.
>
> **⚠️ Fuori pista** (richieste del coordinatore, da mettere nel prossimo checkpoint):
> - `transactions.costBasisOverride.warningAdjustment` nelle 4 lingue con `dev.py i18n update`: in modalità manuale un costo vuoto non si salva (`COST_BASIS_REQUIRED`); per quote che non sono costate nulla si scrive 0. Decisione del developer, 09/10, testuale: «se i dati mancano lo 0 come fallback per auto è corretto. se bisogna cambiare sarà l'utente ad andare su quella transazione e correggere.» Il testo di ripiego inglese dentro `TransactionFormModal.svelte:1949` è ancora quello vecchio: il file non è mio.
> - Guida BRIM: Fineco tolto dall'elenco dei plugin con gli avvisi nella lingua dell'export (scrive in inglese), con una nota che lo dice; docstring di `broker_fineco.py` corretta. La riga eToro di `providers_list.md` ora descrive cosa legge davvero il plugin (CSV dell'attività del conto; i CFD come le altre posizioni; commissioni overnight e SDRT saltate). La `description` del plugin eToro dice ancora «Supports stocks, CFDs»: da segnalare.

### Passo 11 — Test e una correzione del ramo nuova + nuova ✅ (2026-10-09)

> **Note implementazione** (test di `test-author`, eseguiti da me nella corsia 6163):
> - `frontend/src/lib/utils/transactions/promoteSuggest.test.ts`: 20 test, registrato in `tx-unit` (**759 passed**).
> - `frontend/e2e/transactions/tx-import-scalable-transfers.spec.ts` (runner `front-transaction tx-import-scalable-transfers`, account usa e getta per test):
>   - **S1**, (b) stessa sessione: i due file in un solo giro dell'assistente; il banner propone esattamente i due trasferimenti; uno viene unito e salvato come `CASH_TRANSFER` collegato su A e B;
>   - **S2**, (c) sessioni separate: le righe di cassa del broker salvate via API, poi l'import del conto deposito; il 💡 compare sulle gambe nuove dei trasferimenti, aggiunge la gamba salvata e il banner propone la coppia nuova + salvata, che viene unita.
>   - **2 passed** a un worker e a quattro.
> - Regressioni dell'editor in blocco: `tx-bulk-promote-exec` 9, `tx-bulk-suggest-ux` 8, `tx-split-promote` 6, `tx-fx-implied-rate` 3, `tx-commit-all-types` 19, `tx-paired-edit` 4, `tx-bulk-import-handoff` 3; `check-orphans` verde; `npm run check` 0/0.
>
> **⚠️ Fuori pista**: S1 ha trovato un difetto **preesistente** del ramo nuova + nuova di `executePromote`. L'editor mostra gli importi in valore assoluto e lascia il segno al tipo (`txCreateItemToPendingOp`, il form). Quando il tipo diventa CASH_TRANSFER o FX_CONVERSION, a segno libero, il prelievo partiva come +300 e `collapseIntoPaired` sceglieva il lato «da» a caso. Ora il segno passa nell'importo (`applySignRules` col tipo d'origine) prima del cambio di tipo. Il ramo misto non era colpito: la riga nuova parte col tipo d'origine (`promoteFromType`).
>
> **Dubbi del `test-author`, lasciati come sono**:
> - le voci del banner non espongono le due righe né il tipo di destinazione (si potrebbero aggiungere attributi `data-*`);
> - il select del broker per file al passo 1 non ha un `data-testid`;
> - in `PromoteMergeModal`, che non è mio, un Annulla subito dopo la seconda apertura può chiedere «scartare le modifiche?» senza modifiche, perché `initialSnapshot` si aggiorna in un `setTimeout(0)`.

### Passo 13 — Tre voci assegnate dal coordinatore ✅ (2026-10-09)

> **Baseline**: `94271713b` (checkpoint 2, batch 21).
>
> **Note implementazione**:
> - `TransactionFormModal.svelte:1949`: il ripiego inglese inline di `warningAdjustment` ora coincide col testo nuovo del catalogo.
> - `broker_etoro.py`, `description` (da owner BRIM): ora dice cosa legge davvero, cioè il CSV dell'attività del conto, con posizioni aperte e chiuse (un CFD letto come le altre), dividendi, interessi, depositi, prelievi, commissioni di prelievo e di cambio. Prima diceva «Supports stocks, CFDs». R13 (`front-utility core-unit`) **3654 passed**; `external brim-providers` **694 passed, 1 skipped**.
> - `user/transactions/index.en.md`, «The bulk workspace»: il banner unisce due righe nuove, due salvate o una di ciascun tipo; il 💡, nella barra e nel menu della riga, aggiunge la metà già salvata. È l'unica pagina utente generale che parla del banner.
> - `dev.py mkdocs build` strict verde; ruff, black e Prettier puliti; `git diff --check` pulito.
