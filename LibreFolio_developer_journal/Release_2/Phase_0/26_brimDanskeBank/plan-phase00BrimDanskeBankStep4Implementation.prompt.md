# Piano d'implementazione — report set BRIM e importer Danske (step 4–8)

**Stato**: ✅ **fasi A–E completate (2026-10-01)**, consegna finale al coordinatore. C3b annullata dal developer, A17 nel backlog (§11, E.0). Storia dello stato: via del coordinatore sulle superfici condivise; decisioni D-I1…D-I3 prese dal developer (2026-09-30), D-I1 rivisto il 2026-10-01; design approvato (v5.3).
**Riferimenti**:
- [design v5.3](design-phase00BrimReportSets.md), che è la fonte di verità delle regole;
- [piano principale](plan-phase00BrimDanskeBank.prompt.md), step 4–8;
- [analisi degli export](analysis-phase00BrimDanskeBank.md).

**Workstream**: L · **Corsia**: porta 6156, `--data-dir /tmp/librefolio-r2-l` · **Coordinatore**: `c8328a01-f208-4ade-a352-0486d1f14de2`.

## 0. Regole di lavoro

- **Test rossi prima**: li scrive il test-author per ogni fase, e il codice arriva dopo. Un test verde prima della cura va spiegato.
- **Comandi**: `PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py …`, nella corsia di L, un comando alla volta. Mai `./dev.py` da solo, mai `npx` (si usano i binari in `frontend/node_modules/.bin/`), mai installazioni.
- **Git**: solo comandi in lettura. Ogni fase si chiude con un `CHECKPOINT READY`: lo script lo prepara il coordinatore e lo lancia il developer. Dopo, FROZEN.
- **Dati**: nessun valore reale degli export. I campioni sono sintetici, e il controllo `/tmp/libreFolio_l_mockcheck.py` va esteso ai campioni.
- **Superfici condivise**: prima di toccarle, il via del coordinatore (§7).
- **Progressi**: dopo ogni passo si aggiorna questo file, con la data, `Note implementazione` e `Fuori pista`.

## 1. Fatti del codice che il piano usa (verificati il 2026-09-30)

| Area | Fatto | Dove |
|---|---|---|
| Storage | sidecar JSON accanto al file; `save_uploaded_file`, `_write_metadata_atomic`, `_build_file_info_from_metadata` (unico punto sidecar → `BRIMFileInfo`), `parse_is_stale` dalla versione del plugin | `backend/app/services/brim_provider.py:578`, `:523`, `:662`, `:680` |
| Nessun DB | i file BRIM non hanno tabelle né migrazioni: basta il sidecar | `models.py`, `alembic/versions` |
| Plugin | `BRIMProvider` e `to_plugin_info()`; registro con `get_compatible_plugins` ordinato per `detection_priority` (specifici ≥ 100, CSV generico 0–49) | `brim_provider.py:95`, `:394`; `provider_registry.py:374`, `:432` |
| Parse | `POST /files/{id}/parse`: auto-detect → `parse_file_offloaded` (process pool) → candidati asset → duplicati → `move_to_parsed` → risposta → `save_parse_result`. Con `BRIMParseError` o `ValueError` il file va in `failed` | `brokers.py:801–957`; `brim_parse_pool.py:85` |
| Upload | `broker_id: int = Form(...)`; i tre chiamanti usano `axiosInstance` con `FormData` | `brokers.py:570`; wizard `:2935`; `BrokerImportFilesModal.svelte:108`; `files/+page.svelte:495` |
| Salvataggio | l'editor salva con `POST /transactions/validate` e `/commit`, cioè `execute_batch`. `/brokers/{id}/transactions/bulk` non esiste (il design è corretto nella v5.3) | `backend/app/api/v1/transactions.py:62`, `:121`; `transaction_service.py:861` |
| Stato a una data | `_get_balances_before_date(broker_id, before_date)` restituisce cassa per valuta e quantità per asset, con somme SQL, **solo dal DB** | `transaction_service.py:439` |
| Tag | `Transaction.tags` è testo separato da virgole; il filtro esistente è `contains`, per sottostringa | `models.py:794`; `transaction_service.py:272` |
| Wizard | `StepId`/`STEP_DEFS` (`:126`), `stepIsActive` (`:2754`), `goNext`/`goBack` (`:2843`/`:2873`), `doParseAll` (`:3374`), `buildMergedTransactions` (`:716`), consegna `onImportBatch(buildFinalTxList(), …)` (`:1291`), tabella della revisione `step4Columns` (`:1780`) | `ImportWizardModal.svelte` |
| Righe prima dell'apertura | predicati puri già estratti (`isBeforeOpening`), da imitare per `H0` | `frontend/src/lib/utils/transactions/importRowState.ts` |
| Guida d'onboarding | l'import è una guida a step versionata: `IMPORT_GUIDE: 1`, con step da `import.upload` a `import.bulk`; catalogo e overlay nel frontend | `onboarding_service.py:33`, `:52–61`; `onboardingGuideCatalog.ts`; `OnboardingOverlayHost.svelte:498` |
| Test | `api brim` → `test_brim_api.py`; `external brim-providers` → `test_brim_providers.py`; `front tx-unit` è una **lista esplicita** di percorsi; gli E2E dell'import stanno in `frontend/e2e/transactions/tx-import-*.spec.ts`, registrati in `_frontend_transaction.py:530–555`. Un file di test nuovo va registrato: l'inventario segnala gli orfani | `scripts/test_runner/_backend_api.py:715`; `_backend_external.py:270`; `_frontend_transaction.py:10`, `:573`; `_inventory.py:361` |

## 2. Fasi e checkpoint

```mermaid
flowchart LR
  A[A · framework backend] --> B[B · plugin Danske]
  A --> C1[C1 · upload con batch_id]
  B --> C2[C2 · wizard: set, analisi, revisione]
  C2 --> C3[C3 · passo Allinea con la banca e guida]
  B --> D[D · documentazione]
  C3 --> E[E · gate finali e consegna]
  D --> E
```

| Fase | Contenuto | Checkpoint e commit proposti | Complessità |
|---|---|---|---|
| A | schemi, contratto, storage, `batch_id` all'upload, API dei set, `H0`, gap-fix | A1 `feat(brim): add report-set schemas and storage` · A2 `feat(brim): add report-set preview and combine API` · A3 `feat(brim): add gap-fix endpoint` | alta |
| B | campioni sintetici, `broker_danske_bank`, suite generica per i plugin a set | B `feat(brim): add Danske Bank report-set importer` | alta |
| C1 | `batch_id` nei tre chiamanti | può entrare con A2 | bassa |
| C2 | passi ①–④: set, combine e analisi, righe prima di `H0` | C2 `feat(import): report sets in the import wizard` | molto alta |
| C3 | passo «Allinea con la banca», guida d'onboarding, badge nella pagina file | C3 `feat(import): align imports with bank truth` | alta |
| D | pagina utente Danske, registrazioni, guida sviluppatore | D `docs(brim): Danske Bank and report sets` | media |
| E | gate finali, CHANGELOG proposto, consegna | — | — |

## 3. Fase A — framework backend

### A1. Schemi, contratto e storage

**Schemi** (`backend/app/schemas/brim.py`). Sono tutti aggiuntivi, con un default, quindi i plugin di oggi non cambiano:
- `BRIMReportRole` (`code`, `required`, `multiple`, `extensions`, `description`, `max_history`, `must_cover`) e `BRIMPluginInfo.report_roles` (lista vuota di default);
- `BRIMMemberSummary` (ruolo, righe, copertura per asse). Il controllo sul deposito titoli (`mixed_accounts`) si fa in memoria: il numero non esce mai;
- `BRIMCheckpoint`: data, cassa per valuta, posizioni con ID finto, quantità, `exact`/`at_least` e costo per unità facoltativo, più le righe assorbite (quante e somma per valuta) e le evidenze. `BRIMVerification`: data e cassa;
- `BRIMParseOutput` e `BRIMParseResponse` guadagnano `checkpoints` e `verifications`; `BRIMParseResponse` anche `history_start`;
- `BRIMFileInfo` guadagna `batch_id`, `kind`, `derived_from`, `combined_into`, `combine_is_stale`;
- richieste e risposte dei set e del gap-fix (§3.3–§3.6 del design).

**Contratto** (`BRIMProvider`, tutto facoltativo):
- `report_roles` (vuoto di default);
- `detect_role`, `describe_member` e `describe_set`. **Precisazione del design**: la preview chiede al plugin segmenti e buchi dimostrati, senza combinare;
- `combine(members)`, **puro**, che restituisce una tabella: intestazione, righe e riepilogo;
- `settlement_lag` (5 giorni lavorativi per Danske) e `pre_checkpoint_policy` (`summarize` o `import`);
- l'eccezione `BRIMSetRequiredError`.

**Storage** (`brim_provider.py`):
- `batch_id` nel sidecar all'upload;
- `save_combined_file` scrive il CSV (UTF-8 con BOM, `;`) e il sidecar in modo atomico; aggiorna `combined_into` dei membri; riusa il combinato se membri e versione coincidono (D-S6);
- `combine_is_stale` nel builder del `BRIMFileInfo`.

La scrittura del CSV la fa il core, non il plugin, così il formato D-S2 è uno solo.

**Test rossi** (test-author):
- un **plugin finto a due ruoli**, solo per i test, registrato nel registro durante il test;
- casi: storage, riuso, file stale, `batch_id`, file eliminato (A17), schemi retrocompatibili (i plugin di oggi producono lo stesso output).

### A2. API dei set, `H0` e parse

- `POST /upload`: `batch_id: Optional[str] = Form(None)`, validato come UUID.
- **Servizio nuovo** `backend/app/services/brim_report_sets.py`:
  - `collect_members(broker_id, plugin_code, batch_id)`: membri originali di quel caricamento, broker e plugin;
  - `preview_set`: ruoli, `missing` con il periodo (da `must_cover` e `lag`), segmenti e buchi (`describe_set`), avvisi con codici;
  - `history_start(session, broker_id, plugin_code)`: D-S25. Filtro SQL `contains`, poi confronto esatto dei tag separati da virgole; per una `gap_fix` si conta il giorno dopo;
  - `combine_set`: riuso, oppure `plugin.combine` fuori dall'event loop, poi `save_combined_file`.
- **Route**: `POST /sets/preview` e `POST /sets/combine` (EDITOR sul broker).
- **Parse**:
  - un membro di un plugin a set, da solo, risponde 422 senza passare a `failed` (D-S4);
  - sul combinato: `checkpoints` e `verifications` dal plugin; `H0` dal DB; i checkpoint prima di `H0` si scartano, tranne quello d'apertura del primo import; nella risposta va `history_start`.
- **Test rossi**:
  - `test_brim_api.py` (`api brim`): upload con `batch_id`, preview e combine (permessi, 404, set incompleto, `missing`, file di due broker), membro da solo → 422 e stato `uploaded`, combinato → checkpoint;
  - `test_services/test_brim_report_sets.py`, **file nuovo** da registrare: `H0` nei casi D-S25, il combine puro, la regola M con il plugin finto.

### A3. Gap-fix

- **Stato di LibreFolio a una data**: `_get_balances_before_date(broker_id, C + 1 giorno)`, esteso con `exclude_tx_ids` per le cancellazioni in attesa nell'editor, più le somme in memoria di selezione, righe in attesa e proposte dei checkpoint precedenti.
  - Tocca `transaction_service.py`: **superficie da confermare** (§7).
  - Alternativa: una query nel servizio gap-fix, con le stesse somme.
- **Servizio nuovo** `backend/app/services/brim_gap_fix.py`:
  - checkpoint in ordine di data;
  - cassa: DEPOSIT o WITHDRAWAL oltre 0,01;
  - posizioni: con prova esatta, un ADJUSTMENT della differenza; con prova minima, solo la parte mancante;
  - costo: dal checkpoint se noto, altrimenti un todo bloccante nella risposta;
  - spiegazione: le righe assorbite che LibreFolio non ha, e la parte non spiegata;
  - verifiche: solo il confronto;
  - tag `import`, il codice del plugin e `gap_fix`.
- **Route**: `POST /gap-fix` (EDITOR sul broker). Non scrive nulla.
- **Test rossi**: `test_services/test_brim_gap_fix.py`, **file nuovo** da registrare, più i casi API in `test_brim_api.py`:
  - primo import, import sovrapposto (nessuna proposta), buco, tre segmenti in un import solo e in tre import;
  - prova minima già coperta, correzione negativa;
  - proposta tolta (D-S24), cancellazioni e righe in attesa nell'editor, verifica che non torna;
  - lo scenario 8 del design.

**Chiusura della fase A**:
- verdi `services brim-*`, le azioni nuove, `api brim` ed `external brim-providers` (i plugin di oggi restano invariati);
- lint e format secondo la skill `lint-format`;
- `git diff --check`.

## 4. Fase B — plugin Danske

### B0. Specifica di dettaglio (2026-09-30)

Scritta prima dei test rossi: è l'interfaccia che il test-author usa. Le regole vengono dal design v5.3 (§3.4, §3.8, §7.1); qui ci sono le scelte d'implementazione.

**Identità** (`broker_danske_bank.py`):
- codice `broker_danske_bank`, nome `Danske Bank`, estensioni `.xlsx` e `.csv`, priorità 100, versione `1.0.0`;
- `icon_url` `https://danskebank.fi/favicon.ico` (verificato: 200, `image/x-icon`, nessun `cross-origin-resource-policy`); `docs_url` `/mkdocs/user/transactions/import/danske-bank/` (la pagina arriva nella fase D);
- ruoli: `custody` (`.xlsx`, obbligatorio, multiplo, `P1Y`) e `cash` (`.csv`, obbligatorio, multiplo, `P5Y`, `must_cover="custody"`);
- `settlement_lag_business_days` 5; `pre_checkpoint_policy` `summarize`; `history_tag` `danske_bank` (il default);
- `test_file_pattern` `danske_bank`; **nuova proprietà di test del contratto**, `test_sample_sets`: una lista di set, ognuno `{ruolo: [nomi dei campioni]}`. Default `[]`, come `test_file_patterns`.

**Riconoscimento**:
- `can_parse`: l'XLSX con le intestazioni dei titoli (fino alla riga 20); il CSV con `Pvm`, `Saaja/Maksaja`, `Määrä`, `Saldo`, `Tila`; il proprio combinato (`lf_row_kind`, `lf_source`, `custody:Toimeksiantotyyppi`, `cash:Saaja/Maksaja`). Un file illeggibile dà `False`, mai un'eccezione.
- `detect_role`: `custody`, `cash`, oppure `None` (anche per il combinato).
- `describe_member`: righe di dati; copertura sull'asse `trade` (titoli) o `value` (cassa), dalle date valide; per i titoli l'impronta del deposito (sha256 dei valori di `Säilytystili`, solo in memoria). La cassa non ha impronta: se l'avesse, il framework la confronterebbe con quella dei titoli e segnerebbe sempre `mixed_accounts`.
- `parse` di un membro da solo: `BRIMSetRequiredError` (il core lo rifiuta già prima; questo è un secondo livello).

**Lettura**:
- XLSX: colonne per nome; `Palkkio<br/>sis. Alv` riconosciuta anche con `<br>` o con uno spazio; la valuta è la prima colonna senza intestazione dopo `Summa` (in alternativa `Valuutta`), vuota = `EUR`, perché `Summa` è l'importo del conto cassa in euro. Date come testo `dd.mm.yyyy` **o** come celle data; numeri come celle **o** come testo finlandese (spazio o NBSP per le migliaia, virgola decimale, `−` Unicode).
- CSV: Latin-1 o cp1252 via `_open_text`; `;`; numeri finlandesi con gli spazi tolti (F4).
- Nel combinato le celle si copiano verbatim, tranne **`Säilytystili`, che non si copia**: serve solo al controllo dei depositi, fatto sui membri (minimizzazione del dato: è un numero di conto).

**Classi (S1)**:

| Ruolo | Riga | Classe |
|---|---|---|
| titoli | `Tila` ≠ `Toteutettu` | `excluded` (`status`) |
| titoli | `Rajakurssi`, `Päivän kurssi`, `Pikakauppa` | trade: acquisto se `Määrä` > 0 e `Summa` < 0, vendita se `Määrä` < 0 e `Summa` > 0; altrimenti `invalid` |
| titoli | `Tuotto` | provento: `Määrä` > 0 (azioni possedute), `Summa` > 0 |
| titoli | `Jakautuminen, vanha` / `uusi` | scissione: `Määrä` < 0 / > 0, senza `Summa` (con una `Summa` è `invalid`) |
| titoli | altro tipo | `excluded` (`unknown_type`) |
| titoli | date, nome o quantità mancanti; `Arvopäivä` < `Kauppapäivä` | `excluded` (`invalid`) |
| cassa | `Tila` ≠ `Toteutunut`, oppure etichetta `Varaus` | `excluded` (`status`), fuori dalla catena dei saldi |
| cassa | `Osto <nome>` con importo < 0; `Myynti <nome>` con importo > 0; `<nome> <10 cifre>` con importo > 0 | accoppiabile: acquisto, vendita, provento |
| cassa | `Nosto osakesäästötililtä` < 0 → WITHDRAWAL; `Vero osakesäästötililtä` < 0 → TAX; `Palvelumaksu…` < 0 → FEE; `Korko…` > 0 → INTEREST | autonoma |
| cassa | altra etichetta con importo > 0 | autonoma DEPOSIT (nell'OST entra solo denaro del titolare), con una notice informativa |
| cassa | altra etichetta con importo < 0, o una famiglia col segno sbagliato | `excluded` (`unknown_type`) |
| cassa | data o importo non validi, importo zero | `excluded` (`invalid`) |

**Regola M** (D-S28), per ruolo: i file si ordinano per fine copertura, inizio, ordine d'ingresso; per ogni giorno vince l'ultimo file che lo copre. Righe uguali: una sola copia. Giorni diversi: le righe dei file perdenti diventano `excluded` con il motivo nuovo **`superseded`** (I4: nessuna perdita silenziosa), e `describe_set` dà `overlap_mismatch`.

**Abbinamento (S2–S4)**: la chiave è data valuta, importo al centesimo, valuta e direzione (acquisto, vendita, provento). Il nome è un controllo: compatibile se, normalizzato (casefold, spazi), uno è prefisso dell'altro, perché il CSV tronca a ~24 caratteri. Per ogni chiave:
- una riga per parte: coppia, con la notice `name_mismatch` se i nomi non sono compatibili (S3);
- più righe: fra gli abbinamenti di cardinalità massima si prendono quelli col maggior numero di nomi compatibili. Se danno tutti le stesse transazioni (stessi titoli, quantità e prezzi abbinati), si abbina nell'ordine dei file; altrimenti tutte le righe della chiave sono `excluded` (`ambiguous`). Oltre 8 candidati per parte: `ambiguous`.

**Segmenti, buchi e zone**:
- segmenti grezzi: le coperture dei file dei titoli, fuse se si toccano o si sovrappongono;
- un buco fra due segmenti è **dimostrato** se una riga di cassa accoppiabile, rimasta senza controparte, ha la data valuta fra la fine del primo e l'inizio del secondo più il ritardo; altrimenti i due segmenti si fondono;
- checkpoint del segmento *i*: `C_i` = vigilia del suo inizio. Per il primo, `C_1` = vigilia di max(inizio dei titoli, prima riga contabilizzata del CSV) (A13);
- finestra *i*: da `C_i`+1 a min(`E_i` + 5 giorni lavorativi, `C_{i+1}`); bordo: da `C_i`+1 a `C_i` + 5 giorni lavorativi. Giorni lavorativi: lunedì–venerdì, senza festività.

| Riga | Esito |
|---|---|
| coppia | `pair` |
| cassa accoppiabile senza controparte | ≤ `C_1`: `summarized` in `C_1`; nel bordo di *i*: `summarized` in `C_i` (orfano di bordo); oltre `E_i` nella finestra: la zona successiva (`summarized` in `C_{i+1}`, oppure `deferred` dopo l'ultimo); altrove nella finestra: `excluded` (`no_counterpart`); nel buco: `summarized` in `C_{i+1}`; dopo: `deferred` |
| titoli trade o provento senza controparte | data valuta oltre l'ultima riga di cassa: `not_yet_settled`; prima della prima riga di cassa o in un buco della cassa: `outside_cash_coverage`; altrimenti `no_counterpart` |
| scissione | `standalone` |
| cassa autonoma | `standalone` in ogni zona |

Tutte le righe di cassa contabilizzate con data ≤ `C_1` hanno `lf_checkpoint` = `C_1` (assorbite dall'apertura), qualunque sia l'esito.

**Punti di verità**:
- **catena dei saldi**: le righe contabilizzate, dalla più vecchia, per giorno: saldo di fine giorno = saldo precedente + somma del giorno, e deve comparire fra i `Saldo` di quel giorno. Una rottura dà la notice `balance_chain_broken`, e la cassa dei checkpoint diventa una verifica alla stessa data;
- **cassa di `C_i`**: il saldo di fine giorno a `C_i` (o il saldo prima della prima riga, se il CSV comincia dopo), più la cassa degli orfani di bordo del segmento;
- **posizioni**, una per titolo e checkpoint:
  - E1 `Tuotto`: esatta se nessuna riga di movimento di quel titolo (trade o scissione) ha la data d'operazione nei 30 giorni prima, e nessuna riga di cassa `Osto`/`Myynti` compatibile senza controparte ha la data valuta in quei giorni; se quei giorni cadono prima del CSV, la prova si scarta;
  - E2 `Jakautuminen, vanha`: esatta; un altro movimento dello stesso titolo nello stesso giorno la scarta;
  - E3: la somma progressiva dei movimenti importati del titolo nel segmento; se il minimo è negativo, `at_least` il suo opposto;
  - E4: una riga dei titoli esclusa dello stesso titolo, tranne `superseded`, fra `C_i` e la prova scarta la prova;
  - la posizione a `C_i` è la quantità della prova meno i movimenti importati fra `C_i` e la prova; prove esatte discordanti si scartano tutte (`conflict`); se c'è una prova esatta, E3 non si usa;
- **verifica finale**: a min(fine dell'ultimo segmento, ultima riga del CSV), la cassa di fine giorno.

**Combinato**: le colonne del design (`lf_row_kind`, `lf_zone`, `lf_reason`, `lf_checkpoint`, `lf_source`, `lf_match_key`) più tre per i punti di verità, che il design non specificava:

| Colonna | Contenuto |
|---|---|
| `lf_value` | la cassa (`truth_cash`, `verification`) o la quantità a `C_i` (`truth_position`), col punto decimale |
| `lf_currency` | la valuta della cassa |
| `lf_proof` | `exact:E1`, `exact:E2`, `at_least:E3`, oppure `discarded:<regola>:<motivo>` (`recent_trades`, `window_not_covered`, `excluded_rows`, `same_day_movement`, `conflict`) |

- le righe di verità copiano la riga d'origine (la riga di cassa del saldo, la riga dei titoli della prova), con `lf_checkpoint` = la data del punto e `lf_zone` = `before` per l'apertura, `gap` per i checkpoint successivi;
- `lf_source`: `custody:12`, oppure `custody#2:12` quando il ruolo ha più file (l'ordine è quello di `derived_from`); una coppia è `custody:12 + cash:40`;
- ordinamento per data valuta, poi ruolo e riga d'origine; `summary` con i conteggi per esito, zona e motivo, i segmenti, i checkpoint e la catena dei saldi.

**Parse del combinato**:
- `pair`: BUY o SELL (quantità da `custody:Määrä`, cassa e data da `cash:Pvm`/`cash:Määrä`), oppure DIVIDEND (quantità 0); `standalone` di cassa: il tipo della famiglia; `standalone` dei titoli: ADJUSTMENT senza cassa;
- tag `import`, `danske_bank` (+ `demerger` per la scissione); descrizioni deterministiche: `<etichetta di cassa> (<Toimeksiantotyyppi>)` per le coppie, l'etichetta per le righe autonome, `<Toimeksiantotyyppi>: <titolo>` per la scissione;
- asset: un ID finto per nome del titolo, anche per i titoli che compaiono solo nelle prove; `extracted_name` = il nome dei titoli;
- todo:
  - ogni BUY e SELL: `danske_trade_charges_included`, avviso su `cash`, con `split_hint: "trade_charges"`, `cash`, `currency`, `compare_nominal: false`, `row` e i suggerimenti. Per un titolo in euro (0 ≤ differenza ≤ max(15 €, 1 % del lordo)) il suggerimento dà la differenza fra `Summa` e `Määrä × Kurssi`; altrimenti dice che il prezzo può essere in un'altra valuta. L'autore ha confermato che la commissione è inclusa in `Summa` (#26, 2026-09-28);
  - linee nuove della scissione: `demerger`, bloccante su `cost_basis_override`; linea vecchia: `demerger_old_leg`, avviso su `quantity` (limite A6);
- notice in finlandese (D7), con i codici: `excluded_<motivo>` (una per motivo, con le evidenze), `deferred_rows`, `name_mismatch`, `proof_discarded`, `balance_chain_broken`, `deposit_assumed`;
- checkpoint: il più vecchio è `opening`, gli altri `gap`; le righe assorbite sono quelle col suo `lf_checkpoint`; `opening_cash` = cassa del checkpoint − somma delle righe assorbite, solo per l'apertura;
- evidenze: le righe del combinato (`row_numbers` = righe del combinato), senza `Säilytystili`.

**Due correzioni del framework** (A2/A3, trovate scrivendo questa specifica):
1. `apply_history`, in un import successivo (quando `H0` viene dal database): i checkpoint tenuti perdono `opening_cash` e le righe assorbite prima di `H0`, che sono già rappresentate. Altrimenti la spiegazione del gap-fix sottrarrebbe di nuovo il saldo iniziale;
2. `combine_set`: un errore del plugin (`BRIMParseError` o `ValueError`) diventa `BRIMSetCombineFailed`, 422, e i membri restano `uploaded`, come dice il design. Oggi è un 500.

### B1. Campioni sintetici

In `backend/app/services/brim_providers/sample_reports/`:
- **titoli**: un XLSX con date come testo, `<br/>` in un'intestazione e la colonna H senza nome;
- **cassa**: un CSV Latin-1 con `;`, LF, ordinato dal più recente;
- **varianti**: un secondo XLSX per il buco, e file che si sovrappongono.

Nomi e valori sono inventati, e il nome del CSV non contiene nessun IBAN. Il generatore resta fuori dal repository; nel README dei campioni vanno le righe che descrivono il contenuto. Il controllo dei valori va lanciato anche sui campioni.

Il campione copre ogni cella della tabella §3.4.2: coppie, righe autonome, orfani di bordo, `not_yet_settled`, `outside_cash_coverage`, `deferred`, `Tuotto`, scissione, eseguiti parziali identici, tipo sconosciuto, stato non contabilizzato, catena dei saldi.

### B2. Il plugin `broker_danske_bank.py`

- **Identità**: ruoli `custody` e `cash`, tutti e due obbligatori e `multiple`; priorità ≥ 100. `can_parse` riconosce i membri (intestazioni finlandesi) e i propri combinati.
- **`combine`**:
  - classificazione (S1);
  - segmenti e zone (§3.4.2);
  - abbinamento (S2–S4);
  - punti di verità (E1–E4, catena dei saldi, orfani di bordo);
  - regola M.

  Il motore di abbinamento resta dentro il plugin (D-S12).
- **`parse` del combinato**:
  - una coppia diventa BUY o SELL, con la cassa da `Summa`;
  - `Tuotto` diventa DIVIDEND con quantità 0;
  - le righe autonome diventano DEPOSIT, WITHDRAWAL, TAX o FEE, con una mappa esplicita delle etichette;
  - la scissione diventa rettifiche (D4);
  - lo split delle commissioni è un avviso con `split_hint: "trade_charges"` e il suggerimento per i titoli in euro;
  - notice in finlandese con i codici; evidenze da `lf_source`; ID finti da `FAKE_ASSET_ID_BASE`; tag `import` e `danske_bank`; descrizioni deterministiche (S8).

### B3. Test

- **Suite generica** `test_brim_providers.py` (del perimetro BRIM): supporto ai gruppi di campioni per i plugin con ruoli. Esegue combine e poi parse, e applica i controlli di sempre, compreso il contratto con il frontend.
- **Test di dettaglio**: `test_external/test_brim_danske_bank.py`, **file nuovo** da registrare, con le regole S1–S16 cella per cella, E1–E4, la catena dei saldi, il Latin-1 e l'intestazione HTML.
- **Registrazione del plugin**: auto-discovery, `docs_url` e icona, secondo la guida sviluppatore dei plugin BRIM.

## 5. Fase C — frontend

### C1. `batch_id` nei tre chiamanti

- **Wizard**: un UUID per sessione del passo ①, rigenerato al reset.
- **Pagina file**: un UUID per ogni conferma.
- **Modale del broker**: un UUID per ogni caricamento.

Tutti e tre con `crypto.randomUUID()`, come campo del `FormData`.

### C2. Passi ①–④

- **Modulo puro** `frontend/src/lib/utils/transactions/importReportSets.ts`, con i suoi `*.test.ts`:
  - raggruppa per caricamento, broker e plugin a set;
  - un file che un plugin a set riconosce entra nel suo set (A18);
  - dice se il set è completo e quali ruoli mancano.
- **① Carica**: finiti i caricamenti, per ogni set la preview; si vedono il raggruppamento e l'avviso del file mancante (§4.2).
- **② Seleziona file**:
  - componente `frontend/src/lib/components/transactions/import/ReportSetCard.svelte`: il set è una riga con la sua card;
  - «Carica il file mancante», con lo stesso `batch_id`, e «Escludi dall'import»;
  - Continua disattivato se un set spuntato è incompleto.
- **③ Analizza**: per un set, prima `sets/combine`, poi il parse del combinato. In `ParsedFileResult` c'è anche il set, per l'etichetta della riga; il dettaglio della riga ha la parte sull'abbinamento.
- **④ Revisione**: il predicato `isBeforeHistory` in `importRowState.ts`, accanto a `isBeforeOpening`. Le righe prima di `H0` restano nascoste dietro un contatore.

#### C2.0 Specifica di dettaglio (2026-10-01)

Scritta prima dei test rossi: è l'interfaccia per il test-author. Le regole vengono dal design v5.3 (§4.1–§4.5, §4.7); qui ci sono le scelte d'implementazione e i punti in cui il codice obbliga a precisare il design.

**Fatti del codice che cambiano il disegno**
- **Il wizard carica i file solo su «Continua» del passo ①** (`goNext` → `uploadAllPendingFiles`). Al passo ① il ruolo dei file non si conosce finché non sono caricati. Quindi l'avviso del file mancante (§4.2, v5.3) compare dopo il primo «Continua»: il wizard carica, chiede la preview dei set nati da quel caricamento e, se un set è incompleto, **resta al passo ①** con l'avviso. Il file trascinato dopo entra nello stesso set; un secondo «Continua» prosegue comunque (caso B).
- **Il `batch_id` del wizard diventa uno per sessione**, come diceva il piano C1, e si rigenera in `resetState`. Oggi è uno per chiamata di `uploadAllPendingFiles`, quindi il file aggiunto dopo l'avviso finirebbe in un altro set.
- **Il passo Correzioni chiede una decisione per ogni riga**, anche per gli avvisi con `split_hint`: «Continua» è disattivato finché ne resta una in sospeso, e «Accetta tutti» le chiude in un clic. Il design (§4.5) diceva «non blocca»: vale il comportamento di oggi, lo stesso di CA.
- **La preview e il combine del backend non conoscono il plugin scelto a mano**: raccolgono tutti i file del caricamento che il plugin sa leggere. Quindi la seconda frase di A18 («se l'utente cambia il plugin a mano, il file esce dal set») non si realizza nel pilota: nella card non c'è la scelta del plugin per i membri. Servirebbe un `exclude_file_ids` in `BRIMSetRequest`; resta nel backlog.

**Modulo puro** `frontend/src/lib/utils/transactions/importReportSets.ts`, test in `importReportSets.test.ts`, registrato nella lista di `front-transaction tx-unit`:

| Funzione | Contratto |
|---|---|
| `isReportSetPlugin(plugin)` | `true` se il plugin dichiara almeno un ruolo |
| `setPluginFor(file, plugins, override?)` | il plugin a set di un file, oppure `null`. `null` per un combinato (`kind: "combined"`) e per un file senza `batch_id`. Con `override`: l'override stesso se è un plugin a set, altrimenti `null`. Senza: il primo di `compatible_plugins` (già in ordine di priorità) che sia un plugin a set (A18) |
| `reportSetKey(brokerId, pluginCode, batchId)` | `set:<broker>:<plugin>:<batch>` |
| `groupBrokerFiles(brokerId, files, plugins, overrides?)` | `{sets, singles}`. I combinati non stanno in nessuna delle due liste. Un set per (broker, plugin a set, `batch_id`); i file del set in ordine di `uploaded_at`, poi di nome; `uploadedAt` del set = il più vecchio dei suoi; i set dal più recente. I singoli restano nell'ordine d'ingresso |
| `setSelectionState(set, selectedIds)` | `all`, `some` o `none` |
| `combinedFileForSet(set, files)` | il combinato dello stesso broker, `batch_id` e plugin (`compatible_plugins` lo contiene), il più recente; `null` se manca |
| `buildParseUnits(selected, sets)` | le unità d'analisi: i file selezionati di un set, col plugin del set, diventano **una** unità `set`, nella posizione del primo; ogni altro file è un'unità `file` |
| `setBlocksAnalysis(set, selectedIds, state?)` | `true` se il set ha almeno un file selezionato e la sua preview non è pronta, è in errore o dice `complete: false` |
| `parseIsoPeriod(value)` | `P1Y`, `P6M`, `P90D`, `P1Y6M` → `{years, months, days}`; altrimenti `null` |
| `dayBefore(isoDate)` | il giorno prima, in `YYYY-MM-DD` |
| `buildSetTimeline(preview, roleOrder)` | una riga per ruolo, nell'ordine del plugin; una barra per copertura di ogni file, in percentuale dell'intervallo fra la data più vecchia e la più recente, compresa `H0`; la barra della storia di LibreFolio da `H0` alla fine. `null` se nessun file ha una copertura |

**`importRowState.ts`**: `RowBrokerSource` guadagna `response?: {history_start?: string | null} | null`.
- `historyStartFor(mt, parseResults)` restituisce la `history_start` della risposta da cui viene la riga.
- `isBeforeHistory(mt, parseResults)` è vero se la data della riga è **strettamente** prima di `H0`: le righe del giorno `H0` sono nella storia, e il controllo dei duplicati le giudica.
- `shouldAutoSelectOnRecheck` non riseleziona mai una riga prima di `H0`.

**`importMerge.ts`**: in `buildMergedTransactions` una riga prima di `H0` nasce deselezionata, come una riga prima dell'apertura del broker.

**Wizard**
- **Catalogo dei plugin**: caricato all'apertura (`list_plugins`), e messo nella cache condivisa di `ImportPluginSelect`.
- **① Carica**:
  - dopo il caricamento, i file della sessione si raggruppano con `groupBrokerFiles`, partendo dalle risposte dell'upload, e per ogni set parte `POST /sets/preview`;
  - se un set è incompleto, il passo resta il ① e mostra `import-wizard-step1-set-warning`, uno per ruolo mancante (`data-plugin-code`, `data-role`): il plugin, il ruolo, le estensioni, il periodo di `missing` e il link «Come esportarlo» (`docs_url`);
  - il secondo «Continua», senza file nuovi, va al passo ②.
- **② Seleziona file**:
  - nel pannello di ogni broker, una `ReportSetCard` per set, sopra la tabella; la tabella mostra solo i singoli;
  - i set nati dal caricamento della sessione sono selezionati, gli altri no; un membro selezionato ha come plugin quello del set (A18, in `pickBestPlugin`);
  - `handleSelectionChange` della tabella non deve mai togliere i membri di un set;
  - il pulsante d'analisi conta le unità (un set conta 1); è disattivato se un set selezionato blocca (`setBlocksAnalysis`), con il messaggio `import-wizard-set-blocks`;
  - `data-busy` del passo è vero anche mentre una preview è in corso.
- **`ReportSetCard.svelte`** (`frontend/src/lib/components/transactions/import/`). È testo Svelte, senza `{@html}` (gate di K). Radice `report-set-card` con `data-set-key`, `data-batch-id`, `data-plugin-code`, `data-set-status` (`loading`, `complete`, `incomplete`, `error`), `data-selected` (`all`, `some`, `none`), `data-analysed`.
  - Intestazione: la casella `report-set-select`, l'apertura `report-set-toggle`, «Set caricato il ‹data› · ‹plugin›», il numero di file, lo stato.
  - Corpo:
    - per ruolo, il nome localizzato (`importWizard.reportSet.roleName.<ruolo>`, altrimenti la descrizione del plugin), le estensioni e la profondità («al massimo 1 anno»);
    - per file, `report-set-member` (`data-file-id`, `data-role`): nome, copertura, righe, anteprima ed eliminazione;
    - per ruolo mancante, `report-set-missing` (`data-role`), con il periodo, `report-set-upload-missing` (un `<input type=file>` nascosto, `report-set-upload-input`, che accetta le estensioni del ruolo) e «Come esportarlo»;
    - gli avvisi della preview, `report-set-warning` (`data-code`), localizzati con `importWizard.reportSet.warning.<codice>` e, se la chiave manca, il messaggio inglese;
    - la nota sulla storia, `report-set-history` (`data-kind` `first` o `later`);
    - la linea del tempo, `report-set-timeline`;
    - per un set che blocca, «Escludi dall'import» (`report-set-exclude`), che lo deseleziona.
  - «Carica il file mancante»: carica con lo stesso broker e lo stesso `batch_id`, rilegge i file del broker, rifà la preview del set e, se il set era selezionato, seleziona anche il file nuovo. Un errore di caricamento dà un toast (`notify`, `tx.import.set.upload_failed`).
- **③ Analizza**:
  - un set è una riga sola (`ParsedFileResult.set`), con l'etichetta «Set del ‹data› · combinato (N file)» e i nomi dei file sotto, escapati, in `parse-row-set`. All'inizio la riga ha come `fileId` la chiave del set; dopo il combine, quello del combinato;
  - `doParseAll` per un set fa prima `POST /sets/combine`, poi il parse del combinato col plugin del set. Un errore del combine va sulla riga, e le altre proseguono;
  - il dettaglio della riga ha la sezione `parse-detail-pairing`: i conteggi di `summary.outcomes` e `summary.reasons`, con `data-*` per E2E, più «Apri il combinato» e «Scarica».
- **④ Revisione**:
  - le righe prima di `H0` non si selezionano mai; un `$effect` le deseleziona come quelle prima dell'apertura;
  - restano fuori dalle Correzioni e dai gruppi di duplicati fra file (scenario 8: due set dello stesso broker importati insieme);
  - sono nascoste dietro il contatore `import-wizard-before-history-count` (`data-count`) e il pulsante `import-wizard-before-history-toggle`. Mostrate, sono grigie, col badge «Già in LibreFolio» e la casella disattivata. Non contano nel totale.
- **i18n**: le chiavi nuove stanno in `importWizard.reportSet.*`, nelle 4 lingue, via `dev.py i18n`.

**E2E**: `frontend/e2e/transactions/tx-import-report-set.spec.ts`, spec nuovo, azione `front-transaction tx-import-report-set`. Ogni test ha il suo broker e i campioni sintetici Danske; alla fine cancella file e broker.
- **R1**: XLSX e CSV insieme → passo ② con un set completo e selezionato, 2 file coi loro ruoli e la nota `first` → ③ una riga sola, con le coppie nel dettaglio → revisione con 7 righe prima di `H0` (2020-02-03) nascoste; mostrate, hanno la casella disattivata.
- **R2**: solo l'XLSX → l'avviso al passo ① per il ruolo `cash` → si trascina il CSV → «Continua» → passo ② con un set completo, e i due file hanno lo stesso `batch_id`.
- **R3**: solo l'XLSX, poi due volte «Continua» → set incompleto, selezionato, con l'analisi bloccata → «Carica il file mancante» col CSV → set completo, analisi possibile.
- **R4**: un set incompleto più un singolo CSV generico → «Escludi dall'import» deseleziona il set e sblocca l'analisi del singolo.

### C3. «Allinea con la banca», guida e pagina file

- **Il passo nuovo**:
  - `StepId` `gapFix`, dopo `review`. Sul pulsante finale della revisione il wizard chiama `POST /gap-fix`: se non c'è niente da mostrare consegna direttamente, altrimenti apre il passo;
  - il componente `GapFixStep.svelte` ha la stessa tabella della revisione, con le correzioni già selezionate;
  - il modulo puro `gapFixModel.ts` costruisce la richiesta (ID finti → asset risolti, righe in attesa, cancellazioni) e ricalcola quando l'utente torna indietro;
  - le correzioni selezionate, con i loro todo, si aggiungono a `onImportBatch`.
- **La guida d'onboarding** (skill `onboarding-guide`):
  - nuovo step `import.gapFix` fra `import.review` e `import.bulk`, nel backend e nel catalogo e overlay del frontend;
  - ~~IMPORT_GUIDE passa alla **versione 2**~~ → **resta alla versione 1** (D-I1 rivisto il 2026-10-01: le guide non sono mai state rilasciate). Si aggiorna anche il testo di `import.select`, per i set;
  - l'ancora solo su elementi davvero visibili; E2E della guida su desktop e mobile.
- **Pagina file e modale del broker**: badge del set, del combinato e di «incompleto» (D-S9, nel pilota il minimo).
- **i18n**: `importWizard.reportSet.*` via `dev.py i18n`, in 4 lingue; le chiavi della guida nel loro namespace (§7).
- **`api sync`**: solo nella corsia di L.
- **Test**:
  - Vitest per i due moduli puri e per `isBeforeHistory`, aggiunti alla lista di `front tx-unit`;
  - Playwright `tx-import-report-set.spec.ts`, **spec nuovo** da registrare: set completo, set incompleto con «Carica il file mancante», combinato come riga unica, righe prima di `H0`, passo «Allinea» selezionato di default, consegna con `gap_fix`;
  - aggiornamento di `onboarding-guides.spec.ts`.

#### C3.0 Specifica di dettaglio (2026-10-01)

Scritta prima dei test rossi: è l'interfaccia per il test-author. Le regole vengono dal design v5.3 (§3.6, §4.6, §4.7, §5) e dalla skill `onboarding-guide`; qui ci sono le scelte d'implementazione e i punti in cui il codice obbliga a precisare il piano.

**Fatti del codice che cambiano il disegno**
- **Lo step della guida segue il passo da solo.** L'id dello step è `import.${StepId}` (`importGuideStep`), quindi il passo `gapFix` porta lo step `import.gapFix`. Il `$effect` del wizard avvia lo step del passo corrente quando non c'è una guida attiva: il clic su «Importa» (ancora `import.action.review`) chiude lo step della revisione, e il passo nuovo avvia `import.gapFix`. Nessun codice di guida nuovo nel wizard, solo l'ancora `import.action.gapFix` sul «Continua» del passo.
- **D-I1, rivisto il 2026-10-01: la guida resta alla versione 1.** Le guide non sono mai state rilasciate (capitolo Unreleased; la v1.1.0 non le ha), e il Round 4 dell'onboarding ha deciso «tutti i flow restano unreleased/v1, nessun bump simulato», bloccato dal test «Every unreleased Round 5 flow must remain at version 1» (`test_settings_service.py:702`, `:741`). Lo step nuovo compare comunque a tutti: il frontend considera da fare uno step `pending` (`isOnboardingStepProgressDue`), e per gli utenti esistenti `ensure` crea la sua riga `pending`. Lo step nuovo nasce `pending` per tutti (`ensure`). Come Unifica, Correzioni e Duplicati, resta in sospeso finché un import non mostra il passo. Gli utenti E2E canonici restano in regola: il grandfathering segue `ONBOARDING_FLOW_VERSIONS`/`STEPS`, e ogni invocazione E2E ripopola il database.
- **Le posizioni dei punti di verità hanno gli ID finti del plugin, per file.** `buildMergedTransactions` li rimappa (`fakeRemap`) solo per gli ID che compaiono nelle righe, e solo dentro la funzione. Gli ID finti del plugin e quelli globali stanno nello stesso intervallo (≥ 2147473647, a scendere), quindi un ID del plugin che non compare nelle righe **non va mai cercato** fra i globali: resta finto, e il backend lo salta con la nota `unresolved_asset`.
- **La tabella delle correzioni è per punto, non quella della revisione.** Il piano diceva «la stessa tabella della revisione». Il mock del §4.6 però raggruppa per punto, ciascuno con il suo confronto e la sua spiegazione, e la DataTable della revisione è globale e paginata. Le colonne restano quelle della revisione: tipo, data, asset, quantità, cassa, tag.
- **Il messaggio del todo `gap_fix_cost` arriva in inglese**, e l'editor mostra `todo.message` così com'è. Il wizard lo localizza quando converte il todo: `importWizard.reportSet.gapFix.todo.<reason_code>`, e il messaggio del backend se la chiave manca.
- **`step4CanImport` comprende già `!importPreparing`**: il pulsante della revisione resta disattivato mentre il gap-fix gira.
- **`FilesTable` serve sia la pagina file sia il modale del broker**: i badge stanno solo lì, nel tipo `brim`. `files/+page.svelte` e `BrokerImportFilesModal.svelte` non cambiano.
- **Nessuna modifica all'API**, quindi niente `api sync`.

**Modulo puro** `frontend/src/lib/utils/transactions/gapFixModel.ts`, test in `gapFixModel.test.ts`, registrato nella lista di `front-transaction tx-unit`. I tipi sono strutturali: i campi che i tipi generati allargano si leggono come `unknown` e si restringono dentro (lezione di C2). I decimali arrivano come stringhe.

| Funzione | Contratto |
|---|---|
| `truthSourcesOf(parseResults)` | una fonte `{fileId, brokerId, pluginCode, checkpoints, verifications}` per ogni risultato `done` con una risposta che ha almeno un checkpoint o una verifica; `pluginCode` = `response.plugin_code`. Nell'ordine d'ingresso |
| `resolveTruthAssetId(fileId, assetId, ctx)` | `ctx = {fakeRemapByFile, survivorOf, resolutions}`. Un ID reale resta com'è. Un ID finto del plugin: il globale del suo file (`fakeRemapByFile.get(fileId)?.get(id)`); **se manca, l'ID del plugin com'è**. Poi il sopravvissuto dell'unificazione (`survivorOf.get(globale) ?? globale`), poi il suo `resolvedAssetId` se è un numero; altrimenti il sopravvissuto, che resta finto |
| `buildGapFixRequests(sources, selection, pendingCreates, pendingDeleteTxIds, resolveAsset)` | una richiesta per (broker, plugin), nell'ordine della prima fonte. `checkpoints` e `verifications` sono l'unione delle fonti (scenario 8: due set dello stesso broker). Ogni checkpoint è copiato con `positions[].asset_id = resolveAsset(fileId, asset_id)`, il resto invariato. `selection` e `pending_creates` sono filtrati su `broker_id` del gruppo; `pending_delete_tx_ids` passa intero. Nessuna fonte → `[]` |
| `buildGapFixView(outcomes, localizeTodo)` | `outcomes`: `{brokerId, pluginCode, response?, error?}` per richiesta. Un gruppo per esito, con chiave `<broker>:<plugin>`; checkpoint `<gruppo>:cp:<i>`, proposte `<checkpoint>:p:<j>`, verifiche `<gruppo>:v:<i>`. I todo della risposta (`tx_index` = indice nelle `proposals` del checkpoint) diventano `ImportTodo {field, severity, reasonCode, message: localizeTodo(reason_code, message), evidence: evidence ?? [], context: context ?? undefined}` della proposta giusta. `needsCost` = la proposta ha un todo bloccante su `cost_basis_override`. Un esito con `error` dà un gruppo senza righe, con l'errore |
| `gapFixHasSomethingToShow(view)` | `true` se c'è almeno una proposta, una verifica con `ok: false` o un gruppo in errore. Le sole note (`unresolved_asset`) non aprono il passo |
| `defaultGapFixSelection(view)` | tutte le chiavi delle proposte: le correzioni sono selezionate di default (D-S14) |
| `selectedGapFixCreates(view, selected)` | `Array<{tx, todos}>` delle proposte selezionate, per gruppo, punto e proposta |
| `gapFixSelectedCount(view, selected)` | quante proposte della vista sono selezionate |

**`importMerge.ts`**: `MergeResult` guadagna `fakeRemapByFile: Map<fileId, Map<idDelPlugin, idGlobale>>`, in aggiunta e con le stesse regole di oggi.

**Wizard** (`ImportWizardModal.svelte`)
- `StepId` `gapFix`, dopo `review` in `STEP_DEFS`, con `titleKey` `reportSet.gapFix.stepTitle`. `stepIsActive('gapFix')` è vero solo se c'è la vista del gap-fix, e `enterNextActiveStep` non lo raggiunge mai, perché la revisione è sempre attiva.
- **`handleImport`**, dopo i controlli di oggi:
  - le fonti (`truthSourcesOf`); se non ce ne sono, consegna come oggi, **senza chiamare** `POST /gap-fix`;
  - altrimenti una `POST /gap-fix` per richiesta, una dopo l'altra, con la lista finale (`buildFinalTxList`), `pendingCreateTransactions` e `pendingDeleteTxIds`;
  - se nel frattempo il wizard si è chiuso, i dati sono cambiati o la sessione non è più quella, si ferma;
  - se `gapFixHasSomethingToShow`, la vista, la selezione di default e `currentStepId = 'gapFix'`; altrimenti consegna.
- **Errore** di una richiesta: il suo gruppo mostra il messaggio, e «Continua» resta attivo; consegna le proposte degli altri gruppi.
- **«Continua»** del passo: `onImportBatch([...buildFinalTxList(), ...selectedGapFixCreates(...)], progresso)`, e `guideHandedOff` come oggi.
- **Ricalcolo**: la vista e la selezione si cancellano tornando indietro dal passo, andando a un passo precedente, in `resetDownstreamState`, in `resetState` e a ogni `mergeAllTransactions`. Il clic successivo su «Importa» ricalcola.
- **Piede del passo**: «Indietro» (`import-wizard-back`); il conteggio `import-wizard-gapfix-count` (`data-count`), «N correzioni selezionate»; «Continua» `import-wizard-gapfix-continue`, con l'ancora `import.action.gapFix`.

**`GapFixStep.svelte`** (`frontend/src/lib/components/transactions/import/`). È testo Svelte, senza `{@html}` (gate di K). La cassa passa per `CurrencyAmount`; le quantità **delle posizioni** passano per `maskableQuantity` (D5′: una posizione accanto ai prezzi); quelle delle proposte sono transazioni e restano visibili.
- Prop: `view`, `selected`, `onToggle(key)`, `assetName(assetId)`, `brokerName(brokerId)`.
- Radice `import-wizard-gapfix` (`data-proposal-count`, `data-selected-count`), con l'introduzione del §4.6.
- Per gruppo, `gapfix-group` (`data-broker-id`, `data-plugin-code`), col nome del broker; in errore, `gapfix-error`.
- Per checkpoint, `gapfix-checkpoint` (`data-as-of`, `data-kind`): «Punto di partenza · ‹data›» oppure «Dopo il buco · ‹data›».
  - `gapfix-cash-row` (`data-currency`, `data-difference`): LibreFolio, Banca, Differenza;
  - `gapfix-position-row` (`data-asset-id`, `data-exactness`), con «almeno» se `at_least`;
  - la spiegazione `gapfix-explanation`: i movimenti riassunti e quelli che mancano in LibreFolio, il saldo d'apertura, la parte non spiegata, le note `gapfix-note` (`data-code`), localizzate con `importWizard.reportSet.gapFix.note.<codice>` e, se la chiave manca, il messaggio del backend;
  - le proposte `gapfix-proposal` (`data-key`, `data-type`, `data-date`, `data-selected`), con la casella `gapfix-proposal-toggle`: tipo, data, asset, quantità, cassa, e «costo da inserire» se `needsCost`.
- Per verifica, `gapfix-verification` (`data-as-of`, `data-ok`): «TORNA» o «NON TORNA», con le righe di cassa se non torna.
- In fondo, la riga `gapfix-info-hidden-titles`: un titolo che nel file non si è mosso e non ha pagato dividendi non si vede.

**Guida d'onboarding** (skill `onboarding-guide`)
- Backend, `onboarding_service.py`: `import.gapFix` fra `import.review` e `import.bulk`; `import_guide` resta alla versione 1 (D-I1 rivisto).
- Frontend:
  - `IMPORT_GUIDE_STEP_IDS`, con la stessa aggiunta;
  - l'overlay, con `importPresentation`, l'ancora `import.action.gapFix`, le chiavi `onboarding.importGuide.steps.gapFix.{title,description}`, `/transactions` e profondità 2;
  - l'etichetta nella sezione di Impostazioni.
- Testi: lo step nuovo, e la descrizione di `import.select`, che spiega i set. Nessun testo annuncia un'altra guida.
- Test esistenti, con le concessioni del coordinatore (sotto): solo la versione e l'id dello step.

**Badge nella pagina file** (`FilesTable.svelte`, solo nel tipo `brim`)
- Nel modulo puro `importReportSets.ts` (test in `importReportSets.test.ts`):
  - `setsOfFiles(files, plugins)` → `Map<fileId, ReportSetGroup>`, con `groupBrokerFiles` per broker;
  - `fileSetBadges(file, ctx)` → i badge nell'ordine fisso `combined`, `stale`, `usedInCombined`, `set`, `incomplete`:
    - `combined`, per `kind: "combined"`, con i nomi di `derived_from` e quelli eliminati;
    - `stale`, per `combine_is_stale`;
    - `usedInCombined`, per un originale con `combined_into` non vuoto;
    - `set`, per un membro di un set, con la data del set;
    - `incomplete`, per un membro di un set la cui preview dice `complete: false`, con i ruoli mancanti; **non** se il set ha un combinato aggiornato (v5.3).
- Una colonna `reportSet` col componente `FileSetBadges.svelte` (`frontend/src/lib/components/files/`): `file-set-badge` con `data-kind`.
- Il catalogo dei plugin si carica una volta, in una cache del modulo. Una preview per set, in cache per chiave del set e file. Un errore non mostra il badge `incomplete`.

**i18n**: le chiavi nuove in `importWizard.reportSet.gapFix.*` e `importWizard.reportSet.badge.*`, più quelle della guida, nelle 4 lingue, via `dev.py i18n`.

**Test** (test-author; tutti rossi prima)
- **Vitest**, in `tx-unit`:
  - `gapFixModel.test.ts` (nuovo) e `GapFixStep.test.ts` (nuovo, jsdom), da registrare nella lista;
  - i badge, in `importReportSets.test.ts`;
  - `fakeRemapByFile`, in `importMerge.test.ts` (in `core-unit`).
- **Onboarding**: gli unit che leggono la costante del catalogo si adattano da soli. Una riga in `OnboardingCoachmark.test.ts` se la sua tabella deve essere completa.
- **E2E**, in `tx-import-report-set.spec.ts`:
  - **R5**: set principale su un broker nuovo → revisione → «Importa» → passo `gapFix`. Il punto `opening` del 2020-02-02 ha la proposta di versamento di 2.699,50 EUR, selezionata; c'è la verifica del 2020-06-26. «Indietro» e di nuovo «Importa» ricalcolano: due `POST /gap-fix`. «Continua» porta nell'editor tante righe col tag `gap_fix` quante proposte selezionate;
  - **R6**: tutte le proposte tolte → conteggio 0 → nell'editor nessuna riga `gap_fix`;
  - **R7**: un CSV generico da solo non chiama mai `POST /gap-fix` e va diritto all'editor;
  - **R8**: badge, con file caricati e combinati via API: `combined` sul combinato; `set` e `usedInCombined` sugli originali; `set` e `incomplete` su un XLSX da solo;
  - **R9**, in uno **spec separato**, `tx-import-report-set-guide.spec.ts`, con l'azione `tx-import-report-set-guide` (`project=""`): `tx-import-report-set` gira solo su desktop, la guida va provata anche su mobile. Un account usa e getta (`fixtures/onboarding-accounts.ts`); gli step d'import prima di `gapFix` si chiudono via API; al passo il coachmark è ancorato su `import-wizard-gapfix-continue`.
- **Liste a mano**, con le concessioni: `test_settings_service.py`, `test_settings_api.py`, `onboarding-tour.spec.ts:764` e `settings.spec.ts:735`.

#### C3b.0 Le bozze incomplete dell'editor (2026-10-01) — ❌ non eseguita: il developer l'ha annullata (vedi §11, C3b)

Decisione del developer, riportata dal coordinatore: «Correggerlo subito, prima della fase D». Una bozza incompleta dell'editor non deve più far fallire tutto il gap-fix.

**Il problema.** Il wizard manda al gap-fix le righe non salvate dell'editor dello stesso broker (`pending_creates`, D-I3). Oggi FastAPI valida tutta la richiesta come `List[TXCreateItem]`, quindi una sola bozza incompleta (per esempio un acquisto senza asset: «{type} requires asset_id») fa rispondere 422 a tutta la richiesta. Il gruppo mostra l'errore, e si perdono tutte le correzioni.

**Il comportamento** (quello predefinito del coordinatore):
- una bozza incompleta resta fuori da ogni calcolo del gap-fix: la cassa, le quantità e le righe «presenti» della spiegazione;
- il passo lo dice: quali righe (data, tipo, importo o quantità, asset) e perché, con gli stessi messaggi della validazione dell'editor;
- il resto prosegue: le bozze valide contano come prima;
- il passo si apre anche quando c'è solo questo da dire. Altrimenti l'utente non saprebbe che il confronto le ha ignorate.

**Backend**
- `BRIMGapFixRequest.pending_creates`: ogni elemento è `TXCreateItem | dict`, provato da sinistra a destra (`union_mode="left_to_right"`, esplicito sul tipo dell'elemento: il default di pydantic sarebbe «smart», e un `dict` preferirebbe il ramo `dict`). Una bozza valida diventa `TXCreateItem`, come oggi; una incompleta resta un `dict` e non fa più fallire la richiesta. Un elemento che non è un oggetto resta un 422. `extra="forbid"` resta: un campo sconosciuto diventa un'esclusione col suo motivo.
  - **Perché l'unione e non `List[dict]`** come il precedente di `/transactions/validate` e `/commit` (`transactions.py:708-717`). Scelta confermata col coordinatore il 2026-10-01:
    - i test di A3 fissano il contratto di oggi: `type(request.pending_creates[0]) is TXCreateItem` (`test_brim_gap_fix.py:723`), e il costruttore delle richieste dei test di servizio passa istanze di `TXCreateItem`, che un `dict` non accetta;
    - l'OpenAPI tiene lo schema dell'elemento, quindi il client generato resta tipizzato. Il precedente deve documentarlo a mano, con `openapi_extra` sulla rotta;
    - le bozze valide le legge FastAPI una volta sola; solo quelle incomplete passano da `_parse_lenient`. È lo stesso helper del precedente, quindi i motivi sono identici.

    Il costo è un secondo percorso di lettura, limitato alle bozze che FastAPI non ha potuto leggere.
- `compute_gap_fix`: le bozze `dict` si validano una per una con `_parse_lenient` (`transaction_batch_stages.py`), lo stesso helper di `/transactions/validate` e `/commit`. Le bozze valide vanno nei calcoli; i problemi delle altre vanno nella risposta, con l'indice originale.
- `BRIMGapFixResponse.excluded_pending: List[TXValidationIssue]`: un problema per voce, `operation="create"`, `index` nella lista `pending_creates` della richiesta, `code`, `params`, `field` ed `error` come li produce `_parse_lenient`.
- `selection` resta `List[TXCreateItem]`: le righe del wizard vengono dal parse e sono valide per costruzione. Una riga non valida sarebbe un difetto del wizard, e il 422 resta il segnale giusto.
- Contratto: cambia, quindi `api sync` nella corsia di L (i file generati sono ignorati).

**Frontend**
- `gapFixModel.ts`:
  - `GapFixOutcome` riceve `pendingCreates`, la lista mandata con la richiesta;
  - ogni gruppo ha `excluded: Array<{index, tx, issues}>`: un elemento per bozza, in ordine di indice, `tx` = la bozza mandata a quell'indice;
  - `gapFixHasSomethingToShow` è vero anche con sole bozze escluse.

  Gli elementi di `excluded` non hanno `key`, così le chiavi della vista non cambiano.
- `GapFixStep.svelte`: nel gruppo, il blocco `gapfix-excluded` (`data-count`), con una riga `gapfix-excluded-row` (`data-index`) per bozza: la data, il tipo, l'importo o la quantità, l'asset, poi i motivi. I motivi si risolvono con `resolveIssueMessage`, che produce HTML escapato, e passano da `{@html sanitizeHtml(…)}`, la forma ammessa dal gate di K. Una frase dice che le correzioni proposte non tengono conto di quelle righe.
- Wizard: a ogni esito passa la `pending_creates` della sua richiesta.
- i18n: `importWizard.reportSet.gapFix.excludedTitle` (plurale) ed `excludedHint`, nelle 4 lingue.

**Test** (test-author, rossi prima):
- `services brim-gap-fix`:
  - la lettura di un corpo JSON con una bozza valida e una incompleta dà i tipi (`TXCreateItem`, `dict`);
  - il calcolo conta solo la bozza valida, e `excluded_pending` dà indice e codice (`assetRequired`; data mancante → campo `date`);
  - le proposte sono le stesse della richiesta senza la bozza incompleta;
  - senza bozze incomplete, `excluded_pending == []`.
- `api brim`: `POST /gap-fix` con una bozza incompleta risponde 200, non 422, con `excluded_pending`, e non scrive nulla.
- `gapFixModel.test.ts`: `excluded` raggruppato per indice con la bozza giusta; il passo si apre con sole esclusioni; i gruppi in errore hanno `excluded: []`.
- `GapFixStep.test.ts`: il blocco e le sue righe.
- E2E, se l'editor permette di costruire una bozza incompleta dall'interfaccia: R10 apre l'editor con una bozza incompleta del broker, poi «Importa» dall'editor e il set. Il passo mostra la riga esclusa e propone ancora il versamento d'apertura. Se non è praticabile, il test-author lo dice e lo spiega.

## 6. Fase D — documentazione (docs-writer, solo in inglese)

- **Pagina utente** `mkdocs_src/docs/user/transactions/import/danske-bank.en.md`: gli export, il caricarli insieme, la profondità, l'import annuale, il passo «Allinea con la banca», le commissioni, le scissioni e i limiti (§6 del design). Il nome segue il `docs_url` del plugin (`/mkdocs/user/transactions/import/danske-bank/`), fissato dai test della fase B; nessun test controlla che la pagina esista.
- **Registrazioni**, solo in aggiunta:
  - nav di `mkdocs.yml`;
  - card e riga nell'indice ×4;
  - `providers_list.md`;
  - README dei campioni.
- **Documentazione sviluppatore**:
  - in `brim_plugin_guide.md`, la sezione «Plugin multi-report»;
  - in `brim_plugin_guide.md`, la regola che `provider_code` restituisce una **stringa letterale**, mai una costante o un'espressione, con il motivo: il test R13 (`optionFilter.test.ts`, in `front-utility core-unit`) e il runner (`_PROVIDER_CODE_RE` in `scripts/test_runner/_backend_external.py`) lo leggono dal sorgente, senza importare il modulo;
  - in `import-wizard.md`, i set e il passo nuovo;
  - la tabella dei flussi nella pagina utente delle preferenze, se lo step della guida cambia.
- **Verifica**: `mkdocs build` (strict) e `mkdocs check-links`.

## 7. Superfici condivise: da chiedere al coordinatore prima di toccarle

| Superficie | Perché | Esito del coordinatore (2026-09-30) |
|---|---|---|
| `scripts/test_runner/_backend_services.py` | azioni per `test_brim_report_sets.py` e `test_brim_gap_fix.py` | ✅ ma **solo subito dopo l'`add_test` di `brim-provider-base`** (`:1036` in `dev_release2`). D, Risk, A e F toccano altre righe (116–137, 927–975, 70, 82, 993) |
| `scripts/test_runner/_backend_external.py` | azione per `test_brim_danske_bank.py` | ✅ solo aggiunte |
| `scripts/test_runner/_frontend_transaction.py` | percorsi in più nella lista di `tx-unit` e nuova azione `tx-import-report-set` | ✅ solo aggiunte |
| `backend/app/services/transaction_service.py` | `exclude_tx_ids` nella somma a una data | ✅ nessun altro lo tocca; D-I3 deciso dal developer |
| `backend/app/services/onboarding_service.py`, `frontend/src/lib/features/onboarding/`, `components/onboarding/`, `onboarding-guides.spec.ts` | step `import.gapFix` e versione 2 | ✅ secondo la skill `onboarding-guide`; D-I1 deciso dal developer |
| i18n fuori da `importWizard.reportSet.*` | testi della guida | ✅ via `dev.py i18n`, 4 lingue |
| `FilesTable.svelte` | badge nella pagina file | ✅ solo nel tipo `brim` |
| documentazione: nav di `mkdocs.yml`, `user/transactions/import/index.{en,it,fr,es}.md`, `providers_list.md`, `brim_plugin_guide.md`, `import-wizard.md` | pagina e registrazioni | ✅ solo aggiunte. Il docs-writer scrive in inglese; le card negli indici it/fr/es sono una modifica minima, seguita da `translate-stamp`. **`mkdocs build` ritimbra `frontend/static/sw.js`, che non va committato** |
| **C3 (2026-10-01)**: `backend/test_scripts/test_services/test_settings_service.py` (`:610`, `:633-641`), `backend/test_scripts/test_api/test_settings_api.py` (`:423-431`), `frontend/e2e/onboarding-tour.spec.ts:764`, `frontend/e2e/settings.spec.ts:735` | liste a mano degli step della guida d'import, e la sua versione | ✅ **solo** la versione 1→2 e l'id `import.gapFix` fra `import.review` e `import.bulk`, nient'altro; le modifiche le fa il test-author |
| **C3 (2026-10-01)**: `frontend/e2e/transactions/tx-import-report-set-guide.spec.ts` e la nuova azione `tx-import-report-set-guide` in `_frontend_transaction.py` | E2E della guida (R9) su desktop e mobile: l'azione `tx-import-report-set` gira solo su desktop | ✅ solo R9, con un account usa e getta; azione con `project=""` come `onboarding-tour`, solo aggiunte; `check-orphans` e lo spec sui due progetti fra i controlli di C3 |
| **Fase D (2026-10-01)**: `mkdocs_src/docs/user/settings/preferences.en.md` | la frase sugli step facoltativi dell'import | ✅ via docs-writer. È un fatto nuovo nell'EN di una pagina tradotta: debito di traduzione vero, quindi **niente stamp**; va nella lista di traduzione di fine round |
| **`ImportWizardModal.svelte` e `TransactionBulkModal.svelte`** (mancavano nella prima stesura) | card del set, analisi, passo nuovo | ⚠️ K ha modifiche non committate (audit XSS, voce 0): nel wizard le righe ~12, 1396–1525, 2016–2068, 2169–2182, 3454–3482 e 5064; nel bulk, righe sparse fra 69 e 3117. **C1**: nel wizard solo la riga del `FormData` (~`:2951`), che il coordinatore simula al checkpoint. **C2 e C3**: solo dopo che la voce 0 di K è entrata in `dev_release2` e la base di L è aggiornata, su segnale del coordinatore |

## 8. Rischi

| Rischio | Mitigazione |
|---|---|
| Gap-fix incoerente col motore: trasferimenti, coppie collegate, split | somme grezze di quantità e cassa, come `_get_balances_before_date`; casi di test con trasferimenti e rettifiche |
| Il wizard ha già più di 5 100 righe | la logica nuova sta in moduli puri e componenti nuovi; nel modale solo il collegamento |
| Tempi degli E2E (limite di 120 s del runner) | `front build --debug` prima; spec nuovo separato; niente attese fisse |
| La versione 2 della guida la ripropone a chi l'aveva già finita | superato: D-I1 rivisto, la guida resta alla versione 1 finché non è rilasciata |
| Il combinato contiene i nomi delle controparti del CSV | stesso posto e stessi permessi degli originali; nessun log dei valori |
| Campioni troppo simili ai dati reali | valori inventati; controllo automatico prima del checkpoint B |

## 9. Decisioni del developer

| # | Decisione | Esito (2026-09-30, ask_user) |
|---|---|---|
| D-I1 | Guida dell'import: step `import.gapFix` e versione 2, che la ripropone a chi l'aveva già finita | ✅ «Sì: nuovo step e versione 2, la guida ricompare anche a chi l'aveva finita». **Rivisto il 2026-10-01** (ask_user): «Resta alla versione 1, aggiungo solo lo step». Le guide non sono mai state rilasciate, e un test blocca la regola «unreleased = versione 1»; lo step nuovo compare comunque a tutti, e nel CHANGELOG non c'è la riga sulla guida che ricompare |
| D-I2 | Commit per fase | ✅ «Sì: un commit per fase, con C1 insieme ad A2»: A1, A2 con C1, A3, B, C2, C3, D |
| D-I3 | Stato a una data | ✅ il parametro facoltativo `exclude_tx_ids` in `transaction_service.py`, che è libero. Il developer: «mi aspetto che sfrutti la lista che hai già quando si apre l'import wizard». Il wizard riceve già dall'editor `pendingDeleteTxIds` (oggi serve a scartare i duplicati di righe in cancellazione, `pendingDeleteSet` in `importMerge.ts`) e `pendingCreateTransactions`. Il gap-fix riceve le stesse due liste: gli ID vanno a `exclude_tx_ids`, le righe non salvate si sommano in memoria |

## 10. Definition of done

- Un set Danske sintetico si importa dal wizard: un set per caricamento, la card, il combinato come riga unica, le esclusioni dichiarate, il passo «Allinea con la banca» con le correzioni giuste, la consegna all'editor.
- I plugin di oggi non cambiano: la suite `external brim-providers` è verde.
- Test rossi prima, poi verdi, per ogni fase; nessun test nuovo senza registrazione.
- Documentazione EN e registrazioni fatte; `mkdocs build` in strict verde.
- Nessun dato reale nel repository; porta 6156 libera; `CHECKPOINT READY` per ogni fase.

## 11. Avanzamento

- ✅ **Piano scritto il 2026-09-30.** Il coordinatore ha dato il via sulle superfici del §7, aggiungendo i due modali condivisi con K; il developer ha deciso D-I1…D-I3.
- ⏳ Prossimo passo: `CHECKPOINT READY` del journal, cioè design, piano principale e questo piano. Dopo il commit si parte con **A1**.
- ⏸ C2 e C3 aspettano la voce 0 di K in `dev_release2` e l'aggiornamento della base di L.

### A1 — ⏳ in corso (2026-09-30)

- Journal della pianificazione committato: `f6f0d2637`. Il coordinatore dà il via ad A1 e conferma che la base va bene così: fuori dal journal, `dev_release2` ha in più solo le righe del CHANGELOG.
- Test rossi affidati al test-author, sull'interfaccia fissata qui:
  - file nuovo `test_services/test_brim_report_sets.py`;
  - registrazione `services brim-report-sets`, subito dopo `brim-provider-base`;
  - venti punti: schemi, contratto, plugin finto a due ruoli, storage.
- La cura è pronta come script e si applica solo dopo la prova del rosso.

> **Note implementazione (2026-09-30)**:
> - **Rosso** (test-author): 107 test raccolti, 106 falliscono, ciascuno con «not implemented yet (BRIM report sets, phase A1)» sul pezzo che manca (31 pezzi distinti). Passa solo il controllo del plugin finto, che non usa niente di A1. `brim-provider-base` resta 34/34; `check-orphans` è pulito (224 file registrati).
> - **Cura**, applicata dopo il rosso:
>   - `schemas/brim.py`:
>     - `BRIMReportRole`, `BRIMCoverage`, `BRIMMemberSummary` (con `account_fingerprint` escluso dalla serializzazione);
>     - `BRIMSetShape`, `BRIMCombinedTable` (con le colonne obbligatorie `lf_row_kind` e `lf_source`), `BRIMDerivedRef`;
>     - i punti di verità: `BRIMTruthCash`, `BRIMTruthPosition`, `BRIMAbsorbed`, `BRIMCheckpoint`, `BRIMVerification`;
>     - i campi nuovi di `BRIMFileInfo`, `BRIMPluginInfo`, `BRIMParseOutput` e `BRIMParseResponse`;
>     - corretto il commento sull'endpoint `…/bulk`.
>   - `brim_provider.py`:
>     - `BRIMSetRequiredError` e il contratto dei set, con tutti i default;
>     - `batch_id` all'upload; `write_combined_csv`, `save_combined_file`, `find_reusable_combined`;
>     - `combine_is_stale`; `delete_file` mantiene i collegamenti.
> - **Verde**: `services brim-report-sets` 107/107; `brim-provider-base` 34, `brim-parse-error` 4, `brim-parse-pool` 8, `brim-parse-race` 6, `brim-create-transaction` 14, `brim-versioning` 5.
> - **Lint**: `dev.py lint` pulito. Black su `brim_provider.py` ha unito su una riga una mia condizione su più righe; ora i 4 file sono puliti.
>
> **⚠️ Fuori pista**: `external brim-providers` dava 4 rossi in `TestCreditAgricoleCanonicalCharacterization`. Il test congela l'elenco dei campi di `BRIMParseOutput` e l'intero output in un letterale, e le due chiavi nuove, vuote, `checkpoints` e `verifications`, lo facevano fallire. È un cambio di contratto voluto e il contenuto di CA non cambia: la riparazione (chiavi aggiunte al letterale, non filtrate) è affidata al test-author.
>
> **Note implementazione (2026-09-30), chiusura di A1**:
> - Test-author: +7 righe in `test_brim_providers.py`. Le due chiavi entrano nell'elenco congelato dei campi e nei due letterali `EXPECTED_OUTPUTS`, con un commento, così un punto di verità inatteso da CA fa ancora fallire il test.
> - `external brim-providers`: 537 passati, 2 saltati (gli stessi di prima, `TestWindows1252Invariance` sul campione Degiro).
> - `api brim`: 30 passati; le risposte con i campi nuovi funzionano.
> - `git diff --check` pulito; black pulito sui 5 file Python; porta 6156 libera.
>
> ### A1 — ✅ pronta per il checkpoint (2026-09-30)

**Commit di A1**: `b271faaa2` feat(brim): add report-set schemas and storage (5 file) e `796db3f61` docs(journal): record report-set phase A1.

### A2 e C1 — ⏳ in corso (2026-09-30)

- Il coordinatore dà il via ad A2 insieme a C1. Nel wizard, per C1, solo le righe dell'upload: lì ci sono le modifiche non committate di K.
- Test rossi affidati al test-author:
  - servizio `brim_report_sets.py`: membri, `H0` (D-S25), preview, combine, `ensure_parseable`, `apply_history`, con il plugin finto;
  - API: `batch_id` all'upload, `sets/preview` e `sets/combine` (permessi ed errori), parse invariato per i plugin a file singolo;
  - E2E di C1: `batch_id` condiviso dai file caricati insieme, nei tre punti di upload.
- Cura pronta come script, da applicare dopo il rosso.
- **Scelte d'implementazione**:
  - la logica dei set sta nel servizio, e le route sono sottili. Il parse gira in un process pool, quindi il plugin finto è affidabile solo nei test di servizio;
  - il contratto guadagna `history_tag`: di default il codice del plugin senza `broker_`, cioè il tag che i plugin esistenti già scrivono (per esempio `credit_agricole`).

> **⚠️ Fuori pista**: il piano diceva `crypto.randomUUID()`. Funziona solo in un contesto sicuro (HTTPS o localhost), mentre LibreFolio self-hosted può girare in HTTP su rete locale. Si usa invece `generateUUID()` di `$lib/utils/core/uuid`, che il wizard già usa e che su HTTP ripiega su `crypto.getRandomValues`.

> **Note implementazione (2026-09-30), A2 e C1**:
> - **Rosso** (test-author):
>   - `services brim-report-sets`: 102 falliti e 112 passati (i 107 di A1 e 5 verifiche del setup);
>   - `api brim`: 16 falliti e 32 passati;
>   - E2E di C1: 3 falliti, perché `batch_id` è nullo.
>
>   Tutti falliscono per un pezzo di A2 o di C1 che manca.
> - **Cura**:
>   - servizio `brim_report_sets.py`: errori con `status_code`, `get_set_plugin`, `collect_members`, `history_start` e `gap_fix_dates` con confronto esatto dei tag, `build_preview`, `preview_set`, `combine_set` con riuso e nome generato, `ensure_parseable`, `apply_history`;
>   - route `POST /sets/preview` e `/sets/combine` (EDITOR sul broker, prima di tutto il resto); `batch_id` all'upload, validato come UUID;
>   - parse: un membro da solo risponde 422 senza passare a `failed`; il combinato porta checkpoint, verifiche e `history_start`;
>   - `history_tag` e `read_combine_summary` in `brim_provider.py`;
>   - C1: `generateUUID()` nei tre punti di upload.
> - **Verde**:
>   - `services brim-report-sets` 214/214; `api brim` 48/48;
>   - E2E di C1 1/1 per ciascuno dei tre spec. Azioni complete: `front-broker detail` 29 passati e 1 fallito (GrowthChart, preesistente, di I); `front-utility files` 22/22; `front-transaction tx-import-upload` 9/9;
>   - `external brim-providers` 537 passati e 2 saltati; le 6 azioni BRIM dei servizi verdi;
>   - `dev.py lint` pulito; black pulito sui 6 file Python; prettier pulito sui 6 file frontend; `git diff --check` pulito; porta 6156 libera.
>
> **⚠️ Fuori pista**:
> - ruff segnalava `parse_file` troppo complessa (12 > 10) dopo le mie aggiunte. Invece di un `noqa`, la guardia dei set e i punti di verità sono passati in due funzioni d'appoggio (`_refuse_report_set_member`, `_report_set_truth`), più un costruttore dell'errore 422. Test rilanciati: servizio 214, API 48.
> - Il test-author, per i test rossi, ha lanciato `dev.py format`, che passa black su tutto il backend: ha riformattato 6 file estranei. Li ha ripristinati byte per byte e ha verificato gli altri con gli hash; nel worktree non ne resta traccia. **Regola**: black solo sui file toccati (`python -m black <file>`), mai `dev.py format`.

**Commit di A2 e C1**: `b70e9ecce` feat(brim): add report-set preview and combine API (12 file) e `f480b5688` docs(journal): record report-set phase A2. **Regola del coordinatore**: niente `dev.py format`; black e prettier solo sui file toccati; un file estraneo toccato per errore va segnalato, non ripristinato.

### A3 — ⏳ in corso (2026-09-30)

- Test rossi affidati al test-author:
  - `transaction_service` con `exclude_tx_ids` e `get_balances_at_end_of`;
  - schemi del gap-fix;
  - servizio nuovo `brim_gap_fix.py`, con i casi del §3.6 del design;
  - `POST /gap-fix`;
  - file nuovo `test_brim_gap_fix.py`, con l'azione `services brim-gap-fix` subito dopo `brim-report-sets`.
- **Scelte d'implementazione**:
  - il gap-fix accetta **qualsiasi plugin registrato**, perché usa solo `history_tag` e `provider_name`. Così le API si provano per davvero già ora, con `broker_generic_csv`, e in futuro un plugin a file singolo con un saldo progressivo potrà dichiarare un checkpoint (§3.6 del design, migrazione);
  - per la spiegazione della differenza (A12 del design) `BRIMAbsorbed` guadagna `rows` (data valuta, valuta, importo) e `opening_cash`, tutti e due con default. Una riga riassunta conta come «già in LibreFolio» se c'è una transazione con la stessa data, valuta e importo, e ogni transazione vale per una sola riga.
- Cura pronta come script, da applicare dopo il rosso.

> **Note implementazione (2026-09-30), A3**:
> - **Rosso** (test-author):
>   - `services brim-gap-fix` (file nuovo, 99 test): 93 falliti, ciascuno sul pezzo mancante; passano 6 verifiche del setup;
>   - `api brim`: 14 falliti nuovi e 48 passati;
>   - `services brim-report-sets` resta 214.
>
>   Il test-author ha controllato che i test si possano far passare con un'implementazione di riferimento, rimossa dopo (file identico, stesso sha256), e che colgano 13 mutanti.
> - **Cura**:
>   - `transaction_service.py`: `exclude_tx_ids` in `_get_balances_before_date` e il metodo pubblico `get_balances_at_end_of`;
>   - `schemas/brim.py`: `BRIMAbsorbedRow`; `rows` e `opening_cash` in `BRIMAbsorbed`; le 7 classi del gap-fix;
>   - servizio nuovo `brim_gap_fix.py` (`compute_gap_fix`);
>   - route `POST /gap-fix`, con EDITOR verificato prima di tutto.
> - **Verde**:
>   - `services brim-gap-fix` 99/99; `api brim` 62/62;
>   - regressioni: `services transaction` 68; `api tx-balance-walk` 9; `api transactions` 22 passati e 1 saltato; `services brim-report-sets` 214; le 6 azioni BRIM dei servizi; `external brim-providers` 537 passati e 2 saltati.
>
>   Il test saltato è `test_delete_linked_without_pair`: lo salta la fixture `test_asset_id` («Could not create test asset»), che dipende dallo stato del database della corsia, non dalla modifica.
> - `dev.py lint` pulito; black pulito sui 7 file Python toccati; `git diff --check` pulito; porta 6156 libera.

**Commit di A3**: `75579a13b` feat(brim): add gap-fix endpoint e `bf589e339` docs(journal): record report-set phase A3.

### B — ⏳ in corso (2026-09-30)

- Via del coordinatore alle 17:25. Nella regressione di B: `api transactions` dopo un `db populate --force` nella corsia, perché `test_delete_linked_without_pair` era stato saltato dalla fixture.
- **B0 scritta**: specifica di dettaglio nel §4, prima dei test rossi.

> **⚠️ Fuori pista**:
> - Il builder dei casi `TestWindows1252Invariance` decodifica ogni campione CSV come UTF-8 già alla raccolta: un campione Latin-1, come il CSV vero di Danske, farebbe fallire la raccolta dell'intero modulo. Il campione resta Latin-1, e il test-author adatta le due letture a `BRIMProvider._read_text`.
> - Due buchi del framework (A2/A3), trovati scrivendo la specifica: `apply_history` negli import successivi e gli errori del plugin in `combine_set` (B0, ultime righe). Si chiudono in B, con i test rossi prima.
> - L'autore ha già confermato che la commissione è inclusa in `Summa` (commento del 2026-09-28): la condizione di D-S17 è soddisfatta.

> **Note implementazione (2026-09-30), B1 e rosso di B**:
> - **B1, campioni**: cinque file sintetici in `sample_reports/`, con valori inventati:
>   - set principale: `danske_bank-custody.xlsx` e `danske_bank-cash.csv`;
>   - set col buco: `danske_bank-gap-custody-1.xlsx`, `danske_bank-gap-custody-2.xlsx` e `danske_bank-gap-cash.csv`.
>
>   Il generatore sta fuori dal repository (`/tmp/libreFolio_l_danske_samples.py`). Il controllo `/tmp/libreFolio_l_samplecheck.py` confronta ogni cella con gli export reali, ammettendo solo le parole di servizio della banca: 554 celle, 0 collisioni, dopo aver cambiato un prezzo che coincideva. Righe aggiunte al README dei campioni.
> - **Rosso** (test-author), nella corsia, un comando alla volta:
>   - `external brim-danske-bank` (file nuovo, registrato): 324 raccolti, 311 falliti, 13 passati. Tutti i falliti dicono «no BRIM plugin is registered as broker_danske_bank»; i 13 passati sono verifiche dei generatori di file dei test;
>   - `external brim-providers`: 562 raccolti, 17 falliti, 535 passati, 10 saltati. I falliti: 12 contratti col frontend sui due set, 1 guardia (nessun plugin dichiara set di campioni), 4 perché i campioni Danske non hanno ancora un plugin. Gli 8 saltati nuovi sono la classe dei plugin a set, senza plugin su cui girare;
>   - `services brim-report-sets`: 222 raccolti, 6 falliti: `test_sample_sets` (2), la correzione di `apply_history` (2), `BRIMSetCombineFailed` (2);
>   - `api brim`: 63 raccolti, 1 fallito, il flusso completo Danske, perché il backend di test non ha il plugin;
>   - `check-orphans` pulito: 226 file raggiungibili.
>
>   Nessun test verde prima è diventato rosso. Un'implementazione di riferimento del test-author, fuori dal repository, passa 323 dei 324 test Danske; l'unico mancante è `test_sample_sets` nella classe base.
> - **Scelte fissate dai test**, tutte coerenti con la B0:
>   - le commissioni di una vendita valgono lordo − |`Summa`|;
>   - E3 vale anche dopo le prove esatte scartate;
>   - con la catena dei saldi rotta, ogni checkpoint diventa una verifica alla sua data;
>   - `custody#1`/`custody#2` solo con più file;
>   - una coppia si ordina come riga dei titoli;
>   - gli orfani di bordo stanno nella zona `window`;
>   - ogni riga di cassa contabilizzata fino a `C_1` è assorbita, anche se esclusa;
>   - `cash` nel todo dello split ha due decimali (`"718.00"`).
>
> **⚠️ Fuori pista**:
> - Nei fatti che avevo dato al test-author il checkpoint del buco aveva due posizioni: le posizioni sono tre, perché la vendita di Kaamos del 2021-01-05 dà anche una prova E3. L'ho corretto io prima della cura.
> - `_backend_external.py` non è pulito per black già a HEAD (113 righe cambierebbero): il test-author non ci ha lanciato black, e le aggiunte seguono lo stile del file.
> - Prima della modifica di questa fase, il campione CSV Latin-1 impediva la raccolta dell'intero `test_brim_providers.py`: le 4 righe rosse sui campioni Danske erano già vere, solo invisibili.

> **Note implementazione (2026-09-30), cura e verde di B**:
> - **Cura**, applicata dopo il rosso con lo script `/tmp/libreFolio_l_b_patch.py`:
>   - `broker_danske_bank.py` (nuovo): ruoli, riconoscimento, lettura robusta, classi S1, regola M, abbinamento S2–S4, segmenti e zone, catena dei saldi, prove E1–E4, combinato con le colonne `lf_*`, parse del combinato con todo, notice finlandesi e punti di verità;
>   - `brim_provider.py`: la proprietà di test `test_sample_sets`, default `[]`;
>   - `brim_report_sets.py`: `BRIMSetCombineFailed` (422, `combine_failed`) intorno a `plugin.combine`; `apply_history` negli import successivi toglie `opening_cash` e le righe assorbite prima di `H0`.
> - **Verde**, nella corsia, un comando alla volta:
>   - `external brim-danske-bank` 324/324; `external brim-providers` 574 passati e 2 saltati (i due Degiro di sempre);
>   - `services brim-report-sets` 222/222; `api brim` 63/63, compreso il flusso Danske completo (caricamento, preview, combine e riuso, 422 sul membro da solo, parse, gap-fix);
>   - regressioni: `services brim-gap-fix` 99, `brim-provider-base` 34, `brim-parse-error` 4, `brim-parse-pool` 8, `brim-parse-race` 6, `brim-create-transaction` 14, `brim-versioning` 5;
>   - `db populate --force` nella corsia, poi `api transactions`: 22 passati e 1 saltato (vedi sotto);
>   - `check-orphans` pulito (226 file); `dev.py lint` pulito; black e ruff puliti sui file Python toccati; `git diff --check` pulito; porta 6156 libera.
> - **Controllo dei dati**: nessuna cella dei campioni coincide con gli export reali; il combinato non contiene `Säilytystili`, e l'impronta del deposito non esce da `describe_member`.
>
> **⚠️ Fuori pista**:
> - Un solo rosso dopo la cura: con più di 8 esecuzioni identiche per parte la bozza le abbinava lo stesso, perché controllava le righe identiche prima del limite. La B0 dice «oltre 8 candidati per parte: `ambiguous`», e così dice il test: ho invertito i due controlli.
> - `test_delete_linked_without_pair` resta saltato anche dopo `db populate --force`, e non dipende dal database: la fixture `test_asset_id` di `test_transactions_api.py` chiama `GET /assets` senza gli `asset_ids` obbligatori (422) e si aspetta 200 da `POST /assets`, che risponde 201 dal 2025-11-21. È un difetto del test, fuori dal perimetro di L: lo segnalo al coordinatore.
> - I codici dei todo Danske non hanno una chiave `importWizard.brimNotice.*`, come quelli degli altri plugin (oggi ne esiste una sola): il wizard mostra il messaggio finlandese del plugin (D7). Le chiavi localizzate, se servono, vanno in C2.
>
> ### B — ✅ pronta per il checkpoint (2026-09-30)

**Commit di B**: `fda716b46` feat(brim): add Danske Bank report-set importer (14 file) e `2cb29faf1` docs(journal): record report-set phase B.

### Aggiornamento della base e correzione R13 (2026-09-30 → 2026-10-01)

- **Merge di `dev_release2` (`8f18416df`) in L**: aperto dallo script del coordinatore. I 7 conflitti sono stati risolti con la versione di L: i 6 previsti più `test_brim_providers.py`, perché dal lato di `dev_release2` quei file avevano solo i cherry-pick dei commit di L. L'albero è `4873e78e1`, come atteso.
  - Validato a merge aperto, nella corsia 6156, un comando alla volta:
    - `front build --debug` ok; `front check` 3 errori, il pavimento, in file non di L; `component-unit` 2182; `check-orphans` pulito;
    - E2E: `files` 22, `tx-import-upload` 9, `front-broker detail` 29 passati e 1 fallito (`:713` GrowthChart, di I);
    - backend: le 8 suite BRIM dei servizi, `services transaction` 68, `brim-providers` 574 passati e 2 saltati, `brim-danske-bank` 324, `api brim` 63.
  - Commit del merge: `5d48c668f`, genitori `2cb29faf1` e `8f18416df`.

> **⚠️ Fuori pista**: `core-unit` è rosso dal commit di B (`fda716b46`), non dal merge. Fallisce `optionFilter.test.ts › ranking › on the real import-plugin list (R13)`, con «broker_danske_bank.py, provider_code: the return is not a string literal».
> - Il test legge i sorgenti di tutti i plugin BRIM e vuole che `provider_code` restituisca una stringa letterale; il plugin restituiva la costante `PROVIDER_CODE`.
> - Per la stessa ragione `_PROVIDER_CODE_RE` del runner (`_backend_external.py`) non trovava Danske: l'aiuto di `--providers`/`--exclude-providers` elencava 30 plugin BRIM invece di 31. Il filtro funzionava lo stesso, perché non ha `choices`.
> - **Lezione**: una modifica a un plugin BRIM fa girare anche `front-utility core-unit`. Una fase «solo backend» non lo è, se un test del frontend legge i sorgenti.

> **Note implementazione (2026-10-01), correzione R13**:
> - **Decisione del coordinatore**: chiudere il merge così com'è e correggere in un commit a sé. Lo script è `/tmp/libreFolio_l_fix_literal_code.py`: `return "broker_danske_bank"` e via la costante, che aveva lo stesso valore e non serviva altrove. Il comportamento non cambia.
> - **Prove**, nella corsia 6156, un comando alla volta:
>   - `front-utility core-unit`: 102 file e 2684 test passati. Prima la suite di R13 falliva intera e i suoi test non si contavano: 2681 passati e 3 saltati;
>   - `vitest` sul solo `optionFilter.test.ts`: 34/34, comprese le 3 prove di R13;
>   - aiuto del runner: 31 plugin BRIM, `broker_danske_bank` compreso;
>   - `external brim-danske-bank` 324/324; `external brim-providers` 574 passati e 2 saltati;
>   - ruff e black puliti sul file; `git diff --check` pulito; porta 6156 libera.
> - **Fase D** (§6 aggiornato):
>   - la guida sviluppatore dirà che `provider_code` è una stringa letterale, e perché;
>   - la pagina utente si chiamerà `danske-bank.en.md`, perché il `docs_url` del plugin è `…/danske-bank/` e le pagine prendono il nome dal `docs_url` (`credit_agricole/`, `generic-csv/`). Il piano diceva `danske_bank.en.md`.

**Commit della correzione R13**: `791db7fee` fix(brim): return a literal Danske provider code e `fb90a8697` docs(journal): record the base merge and the R13 fix.

### C2 — ⏳ in corso (2026-10-01)

- Via del coordinatore, da `fb90a8697`: la voce 0 di K è nella base dal merge `5d48c668f`.
- **C2.0 scritta**, nel §5: la specifica di dettaglio prima dei test rossi.

> **⚠️ Fuori pista** (dalla lettura del wizard):
> - Il wizard carica i file solo su «Continua» del passo ①, quindi l'avviso del file mancante compare dopo il primo «Continua»: il passo resta il ①, e un secondo «Continua» prosegue.
> - Il `batch_id` del wizard passa a uno per sessione, come diceva il piano C1: con uno per chiamata, il file aggiunto dopo l'avviso finirebbe in un altro set.
> - Il passo Correzioni chiede una decisione anche per gli avvisi con `split_hint` («Accetta tutti» le chiude). Il §4.5 del design diceva «non blocca».
> - La preview e il combine del backend non conoscono il plugin scelto a mano: la seconda frase di A18 resta nel backlog (serve `exclude_file_ids` in `BRIMSetRequest`). Nella card non c'è la scelta del plugin per i membri.
> - I test dei componenti (`component-unit`) si registrano in `_frontend_utility.py`, che non è fra le superfici approvate: la logica sta nei moduli puri (`tx-unit`), e la card si prova con gli E2E.

> **Note implementazione (2026-10-01), rosso di C2** (test-author, corsia 6156, un comando alla volta):
> - **`front-transaction tx-unit`**: 9 file. `importReportSets.test.ts`, file nuovo, registrato: 65 test, 65 falliti, ognuno sul modulo che manca, perché il modulo si carica dentro ogni test. Gli altri 8 file: 375/375 verdi.
> - **`front-utility core-unit`**: 2700 test, 12 falliti, 2688 passati; tutti i 2684 di prima restano verdi.
>   - `importRowState.test.ts`: 10 falliti: `historyStartFor` (3), `isBeforeHistory` (6), `shouldAutoSelectOnRecheck`, che riseleziona una riga prima di `H0` (1);
>   - `importMerge.test.ts`: 2 falliti, le righe prima di `H0` nascono selezionate.
>
>   4 test nuovi passano già, ed è voluto: proteggono il comportamento che non deve cambiare.
> - **E2E `front-transaction tx-import-report-set`** (spec nuovo, registrato): 4/4 falliti in circa 10 s ciascuno, sul primo elemento che manca:
>   - R1 arriva al passo ② e si ferma su `report-set-card`;
>   - R2, R3 e R4 si fermano su `import-wizard-step1-set-warning`.
> - **Gate**: `check-orphans` pulito; `tx-import-upload` 9/9 (C1 invariato); `svelte-check` dà solo l'errore atteso del modulo mancante, più i 3 del pavimento.
> - **Precisazioni dei test**:
>   - R1 vuole un solo `POST /sets/combine` e un solo parse, quello del combinato col plugin Danske;
>   - il broker di R1 ha come predefinito il CSV generico, quindi R1 copre A18 in `pickBestPlugin`;
>   - nella revisione: 20 righe importabili, poi 27 col pulsante, 7 disattivate.
>
> **⚠️ Fuori pista** (test-author):
> - I file BRIM della corsia sopravvivono al ripopolamento del database, quindi un broker nuovo con un id già usato eredita i file di prove vecchie. Il primo giro di E2E, con la pulizia larga del C1, ha cancellato un file rimasto (`parse_test.csv`); poi la pulizia è stata limitata ai file caricati dal test.
> - Un aggiornamento senza filtro della tabella dei todo è stato corretto dal test-author stesso.

> **Note implementazione (2026-10-01), cura di C2** (gli script in `/tmp/libreFolio_l_c2_*`):
> - **Moduli puri**: `importReportSets.ts`, nuovo; `isBeforeHistory` e `historyStartFor` in `importRowState.ts`; in `importMerge.ts` le righe prima di `H0` nascono deselezionate.
> - **Card e tipi**: `ReportSetCard.svelte`, nuovo; i tipi `BrimSetPreview` e `BrimSetCombineResponse` in `types/files.ts`.
> - **`ParseDetailModal.svelte`**: la sezione dell'abbinamento, con lo scaricamento del combinato.
> - **`ImportWizardModal.svelte`**:
>   - un `batch_id` per sessione e l'avviso al passo ①;
>   - le card al passo ②, con A18 in `pickBestPlugin`, la selezione per set e «Carica il file mancante»;
>   - al passo ③ prima il combine, poi il parse in `parseResultInPlace`, una funzione sola anche per il parse di un solo file;
>   - alla revisione le righe prima di `H0`, escluse anche dalle Correzioni e dai duplicati fra file.
> - **i18n**: 63 chiavi `importWizard.reportSet.*` nelle 4 lingue, con `dev.py i18n add`; diff di +79/−1 per lingua.
>
> **⚠️ Fuori pista**:
> - Il primo `front check` ha dato 16 errori nuovi:
>   - i tipi generati allargano i campi nullabili (`T | null | Array<T | null>`), quindi i tipi dei moduli puri ora accettano `unknown` e restringono dentro;
>   - nella card, una prop chiamata `state` trasformava `$state` in una sottoscrizione a uno store: rinominata in `previewState`.
>
>   Dopo le correzioni, gli errori sono i 3 del pavimento.
> - **`component-unit` si bloccava** (un worker al 100 % di CPU per 6 minuti, fermato da me). `ensureImportPlugins()` leggeva `importPlugins` dentro l'effetto d'apertura, attraverso `loadBrokers()`, e poi la riscriveva dopo l'`await`. Col mock del test, che risponde con un catalogo vuoto, l'effetto ripartiva all'infinito; in produzione sarebbe ripartito una volta sola. Cura: la richiesta si memorizza in una variabile normale, non reattiva. Il file del wizard: 21/21.

> **Note implementazione (2026-10-01), verde di C2** (corsia 6156, un comando alla volta):
> - **Unit**: `front-transaction tx-unit` 440/440, di cui `importReportSets.test.ts` 65; `front-utility core-unit` 2700/2700, compresi i gate XSS di K; `front-utility component-unit` 2182/2182.
> - **Statici**: `front check` 3 errori e 41 avvisi, il pavimento; prettier pulito sui 15 file toccati; `dev.py lint` pulito; `check-orphans` pulito (93 E2E, 272 Vitest, 227 backend); `git diff --check` pulito; i18n con le stesse 3481 chiavi in tutte e 4 le lingue.
> - **E2E nuovi**: `tx-import-report-set` 4/4 al primo giro (R1–R4), dopo `front build --debug`.
> - **Regressione E2E del wizard**: verdi `tx-import-upload` 9, `tx-import-flow` 10, `tx-import-duplicate-precedence` 6, `tx-asset-identity` 9, `tx-import-resolution` 12, `tx-import-matching` 6, `front-utility onboarding-tour` 10.
>
> **⚠️ Fuori pista: quattro rossi che c'erano già** (triage con la skill `test-triage`). Per confrontare ho esportato `HEAD` (`fb90a8697`, senza C2) con `git archive` in `/tmp`, e ho fatto girare gli stessi spec nella stessa corsia e con lo stesso stato. Poi ho cancellato la copia.
>
> | Spec | Con C2 | Base senza C2 | Verdetto |
> |---|---|---|---|
> | `tx-brim-import` T1 | rosso | rosso | **orologio** (assunzione del test). L'helper usa `isVisible({timeout})`, che in Playwright non aspetta, e analizza «il primo file disponibile» della corsia |
> | `tx-ca-contract` CAC-011 e CAC-012 | rossi | rossi | **orologio**. Lo stesso `isVisible({timeout})` in `walkToReview`: se il passo Correzioni arriva dopo il controllo, il test non preme «Accetta tutti» e resta fermo lì (l'ho visto nell'istantanea) |
> | `tx-import-file-selection` «existing files» | rosso | rosso | **ambiente**. Il broker di controllo ha una riga in più: un file di una prova vecchia. La corsia ricrea il database (`db populate --force`, e le suite dei servizi che lo ricreano) senza `--clean`: i broker spariscono, ma i loro file BRIM restano su disco in `broker_<id>`. SQLite riusa gli id (max+1), quindi un broker nuovo eredita i file di uno sparito. La cancellazione via API invece li toglie (`_delete_brim_files_for_brokers`). Il raggruppamento di C2 può solo togliere righe (set e combinati), mai aggiungerne |
> | `tx-import-asset-inspector` E2-001 | 1 passato su 4 | 1 passato su 3 | **intermittente anche senza C2**. Il secondo clic sulla valuta, dopo l'annullamento del cambio di valuta, non apre la lista; non tocca codice di C2 |
>
> Non sono nel perimetro di L: vanno al coordinatore. I file orfani non sono un difetto di produzione, perché lì il database non si ricrea senza i file: sono un problema del setup dei test, che dovrebbe pulire `broker_reports` quando ricrea il database.
>
> ### C2 — ✅ pronta per il checkpoint (2026-10-01)

**Commit di C2**: `8c3271235` feat(import): report sets in the import wizard e `918693ed9` docs(journal): record report-set phase C2.

### C3 — ⏳ in corso (2026-10-01)

- Via del coordinatore, da `918693ed9`, nella corsia 6156.
- **Base dei controlli**: `front-utility onboarding-component-unit` su `918693ed9`, 408/408 verde (contiene `ImportWizardModal.test.ts`).
- **Concessioni del coordinatore**: nel §7 (le liste a mano della guida, `preferences.en.md` per la fase D).
- **C3.0 scritta**, nel §5: la specifica di dettaglio prima dei test rossi.

> **⚠️ Fuori pista**:
> - C2 non aveva lanciato `onboarding-component-unit`, che contiene `ImportWizardModal.test.ts`: l'ho lanciato ora, 408/408, e da C3 entra fra i controlli.
> - D-I1 regge col solo aumento della versione: la verifica è nella C3.0. Il coordinatore chiede una riga nel CHANGELOG, perché la guida d'import ricompare a tutti quelli che l'avevano finita. *(Superato: D-I1 rivisto più sotto, la guida resta alla versione 1 e la riga non serve.)*
> - Le liste a mano degli step della guida stanno in quattro test fuori dal §7: due backend e due E2E. Concessi con un vincolo: solo la versione e l'id dello step. Le liste simulate di altri quattro spec E2E non cambiano: rispondono «completed» e restano innocue.

> **Note implementazione (2026-10-01), rosso di C3** (test-author, corsia 6156, un comando alla volta):
> - **`front-transaction tx-unit`**: 440 verdi (la base di C2) e 55 rossi, tutti nuovi:
>   - `gapFixModel.test.ts` (nuovo, 32 test): «gapFixModel.ts cannot be loaded»;
>   - `GapFixStep.test.ts` (nuovo, 9 test, jsdom): componente assente;
>   - `importReportSets.test.ts`: `setsOfFiles` (4) e `fileSetBadges` (10), «not implemented yet».
> - **`front-utility core-unit`**: 2700 verdi e 4 rossi, `fakeRemapByFile` in `importMerge.test.ts`.
> - **`front-utility onboarding-component-unit`**: 408 verdi e 1 rosso, la riga `import.gapFix` aggiunta alla tabella delle presentazioni di `OnboardingCoachmark.test.ts`: l'ancora non riceve `aria-describedby`.
> - **Backend**: `services settings` 20/3 e `api settings` 37/2; rossi solo sulle liste concesse (versione 2 e `import.gapFix`).
> - **E2E `tx-import-report-set`**: R1–R4 verdi, R7 verde per costruzione (protegge il comportamento di oggi), R5, R6 e R8 rossi sul primo elemento nuovo: il passo resta `review`, e il badge `combined` manca.
> - **E2E `tx-import-report-set-guide`** (nuovo, desktop e mobile): 0/2, «the import guide has the step import.gapFix».
> - **E2E con le liste concesse**: `onboarding-tour` 0/2 e `settings` 0/1, sulla lista degli step.
> - `check-orphans`: pulito, dopo la registrazione dello spec della guida.
>
> **Scelte del test-author dove la C3.0 taceva**: le `resolutions` sono l'array `assetResolutions` del wizard; una selezione è un `ReadonlySet<string>`; il contesto dei badge è `{sets, files, previews}`. Negli E2E, «Importa» si abilita lasciando selezionate solo le 5 righe di cassa senza asset (deseleziona tutto, filtro «nessun asset», seleziona le visibili): così niente da risolvere e nessun asset creato. L'editor si chiude con «Chiudi» e «Scarta», mai «Salva tutto».

> **Note implementazione (2026-10-01), cura di C3** (script in `/tmp/libreFolio_l_c3_*`):
> - **Moduli puri**:
>   - `gapFixModel.ts`, nuovo: fonti, risoluzione degli asset, richieste, vista con chiavi, selezione;
>   - `importMerge.ts`: `MergeResult.fakeRemapByFile`;
>   - `importReportSets.ts`: `setsOfFiles`, `fileSetBadges` e `formatIsoDay`, il formattatore del giorno che stava nella card di C2 (la card ora lo importa).
> - **Componenti**:
>   - `GapFixStep.svelte`, nuovo, senza `{@html}`: la cassa con `CurrencyAmount`, le quantità delle posizioni con `maskableQuantity`; le righe ripetute hanno chiave per indice;
>   - `FileSetBadges.svelte`, nuovo;
>   - `FilesTable.svelte`: la colonna `reportSet` nel tipo `brim`, il catalogo dei plugin dalla cache condivisa di `ImportPluginSelect`, una preview per set (le richieste fallite tolgono solo il badge).
> - **Wizard**:
>   - il passo `gapFix` dopo `review`;
>   - in `handleImport`, con fonti di verità, una `POST /gap-fix` per broker e plugin, poi il passo o la consegna;
>   - «Continua» consegna la lista finale più le correzioni scelte;
>   - la vista si cancella tornando indietro, in `goToStep`, in `resetDownstreamState`, in `resetState` e a ogni merge.
> - **Guida**: lo step `import.gapFix` (la versione resta 1, D-I1 rivisto più sotto) nel backend, nel catalogo, nell'overlay (ancora `import.action.gapFix` sul «Continua» del passo) e nella sezione delle Impostazioni.
> - **i18n**: 38 chiavi nuove e il testo nuovo di `import.select`, nelle 4 lingue, con `dev.py i18n`. Parità: 3519 chiavi in ogni lingua.
>   - I badge usano chiavi letterali, così l'audit non le conta fra le inutilizzate;
>   - `reportSet.gapFix.stepTitle` resta segnalata come `importWizard.step4Title`: i titoli dei passi si leggono con `importWizard.${titleKey}`.
>
> **⚠️ Fuori pista**:
> - In `GapFixStep.test.ts` il caricamento pigro del componente (`import.meta.glob`, scelto per il rosso) ora avviene dentro il primo test. La trasformazione a freddo dura circa 7,7 s, oltre i 5 s del test: il primo test scade, e il suo montaggio tardivo rompe il secondo.
>   - Prova: il file da solo dà 3 rossi e 6 verdi; con `--testTimeout=30000` dà 9/9.
>   - Verdetto della skill `test-triage`: **assunzione sul tempo**, del test. La correzione (caricamento in un `beforeAll`) va al test-author; prodotto e configurazione restano invariati.

> **⚠️ Fuori pista: D-I1 rivisto (2026-10-01).** Con la versione 2, `services settings` restava rosso su due asserzioni che la concessione non copriva: «Every unreleased Round 5 flow must remain at version 1» (`test_settings_service.py:702`) e le righe degli step alla versione 1 (`:741`).
> - Le guide non sono mai state rilasciate: sono nel capitolo Unreleased, la v1.1.0 non le ha, e il dossier dell'onboarding lo dice («onboarding never shipped in 1.1.0»). Il Round 4 aveva deciso «tutti i flow restano unreleased/v1, nessun bump simulato».
> - Lo step nuovo compare comunque a tutti: per gli utenti esistenti `ensure` crea la riga `pending`, e uno step `pending` è da fare.
> - Domanda al developer (ask_user), risposta: «Resta alla versione 1, aggiungo solo lo step». Quindi:
>   - `onboarding_service.py` torna a `IMPORT_GUIDE: 1`;
>   - il test-author annulla il suo 1→2 a `test_settings_service.py:610`, l'unica modifica di versione che la concessione permetteva;
>   - le liste degli step restano con `import.gapFix`;
>   - nella proposta per il CHANGELOG non c'è la riga sulla guida che ricompare.

> **Note implementazione (2026-10-01), riparazioni dei test** (test-author; il prodotto non cambia):
> - `GapFixStep.test.ts`: il modello e il componente si caricano una volta in un `beforeAll` (timeout del hook 60 s). Un modulo assente fa ancora fallire ogni test da solo, col suo messaggio.
> - R6 (`tx-import-report-set.spec.ts`): l'editor mostra sempre la barra di paginazione (`alwaysShowPagination={true}`, `TransactionBulkModal.svelte:3395`). R6 ora mostra tutte le righe come R5, e prova che non c'è un'altra pagina con «precedente» e «successiva» disattivati. Verdetto: assunzione del test, e il prodotto era giusto (lo screenshot: 5 righe, nessuna `gap_fix`).
> - `test_settings_service.py:610`: annullato l'1→2 (D-I1 rivisto). Commento di R9 senza «version 2».

> **Note implementazione (2026-10-01), verde di C3** (corsia 6156, un comando alla volta):
> - **Unit**:
>   - `front-transaction tx-unit` 495/495, di cui `gapFixModel` 32, `GapFixStep` 9 e i badge 14;
>   - `front-utility core-unit` 2704/2704, compresi i gate XSS di K, la copia delle guide e R13;
>   - `front-utility onboarding-component-unit` 409/409;
>   - `front-utility component-unit` 2182/2182.
> - **Backend**: `services settings` 23/23, `api settings` 39/39, `db referential-integrity` 17/17.
> - **Statici**:
>   - `front check` al pavimento: 3 errori e 41 avvisi, negli stessi 3 file di prima;
>   - prettier pulito sui 24 file del frontend toccati; black e ruff puliti su `onboarding_service.py`; `dev.py lint` pulito;
>   - `check-orphans` pulito (94 E2E, 274 Vitest, 227 backend); `git diff --check` pulito;
>   - i18n: 3519 chiavi complete in ogni lingua.
> - **E2E nuovi**, dopo `front build --debug`:
>   - `tx-import-report-set` 8/8 (R1–R8, desktop);
>   - `tx-import-report-set-guide` 2/2 (R9, desktop e mobile).
> - **Regressione E2E**: verdi `onboarding-tour` 10, `onboarding-guides` 24, `settings` 45, `files` 22, `tx-import-flow` 10, `tx-import-upload` 9, `tx-import-duplicate-precedence` 6, `tx-asset-identity` 9, `tx-import-resolution` 12 e `tx-import-matching` 6. `front-broker detail` 29/30: l'unico rosso è `brokers-detail.spec.ts:713`, il rosso noto del workstream I (GrowthChart). I test del modale dei file importati, che usa `FilesTable`, sono verdi.
> - Porta 6156 libera alla fine.
>
> **Limite noto, da documentare in D**: le righe non salvate dell'editor dello stesso broker vanno al gap-fix così come sono. Una bozza incompleta (per esempio un acquisto senza asset) fa rispondere 422 a tutta la richiesta. Il gruppo mostra l'errore, e si prosegue senza correzioni.

### C3 — ✅ pronta per il checkpoint (2026-10-01)

**Commit di C3**: `9336c0e9b` feat(import): align imports with bank truth e `8ec9f46e0` docs(journal): record report-set phase C3.

### C3b — ⏳ in corso (2026-10-01)

- Decisione del developer, riportata dal coordinatore: correggere subito il limite delle bozze incomplete, prima della fase D.
- Base `8ec9f46e0`. Prima di ogni modifica, nella corsia 6156: `services brim-gap-fix` 99/99 e `api brim` 63/63.
- **C3b.0 scritta**, nel §5. Il comportamento è quello predefinito del coordinatore. Le scelte d'implementazione: la validazione riga per riga nel backend, con lo stesso helper dell'editor; l'unione `TXCreateItem | dict` sulle sole `pending_creates`; il passo che si apre anche con sole esclusioni.
- **Via del coordinatore** su C3b come descritta: la validazione nel backend con `_parse_lenient`, `excluded_pending: List[TXValidationIssue]`, il passo che si apre anche con sole esclusioni, `selection` rigida.
  - Scelta fra unione e `List[dict]`: resta l'unione con `union_mode="left_to_right"` esplicito; il motivo è nella C3b.0.
  - `api sync` solo nella corsia di L; il client va rigenerato all'integrazione in `dev_release2`, e il coordinatore lo annota.
- **Rosso di C3b** (test-author, corsia 6156): `services brim-gap-fix` 12 rossi e 106 verdi (99 vecchi e 7 guardie), `front-transaction tx-unit` 10 rossi e 495 verdi, `api brim` 1 rosso e 65 verdi (63 vecchi e 2 guardie). Tutti rossi sul pezzo mancante; `check-orphans` pulito.

> **⚠️ Fuori pista: il limite noto non si raggiunge dall'interfaccia.** Il test-author non è riuscito a scrivere l'E2E R10: l'editor non permette di creare una bozza incompleta. L'ho verificato nel codice:
> - nel form di aggiunta e di modifica, «Applica» (`tx-form-save`) resta disattivato finché la riga non è completa (`!commitOnSave && !isFormComplete`, `TransactionFormModal.svelte`), con le stesse regole del backend;
> - le celle della griglia sono in sola lettura;
> - `addRow()`, l'unica funzione che aggiunge una riga vuota, non è collegata all'interfaccia (`void addRow;`, `TransactionBulkModal.svelte`);
> - i cloni copiano righe già valide, e le righe del wizard vengono dal parse.
>
> Il 422 che avevo descritto nel verde di C3 («un acquisto senza asset») quindi si produce solo se le regole del form e quelle del backend divergono. La mia segnalazione esagerava la probabilità.
>
> Domanda al developer (ask_user), risposta: «Lascio perdere C3b: annullo i test rossi, tengo il comportamento di oggi (errore nel gruppo, si prosegue senza correzioni) e lo documento in D». Quindi:
> - il test-author riporta i quattro file di test a `HEAD` (`git show HEAD:…`, senza `checkout`);
> - nessuna modifica al prodotto;
> - la fase D documenta il comportamento: se il gap-fix fallisce, il gruppo mostra l'errore e l'import prosegue senza correzioni.

### C3b — ❌ annullata dal developer (2026-10-01)

### D — ⏳ in corso (2026-10-01)

- Via del coordinatore da `8ec9f46e0`. Nessun altro ramo tocca `mkdocs.yml`, le pagine dell'import, `user/files`, `preferences.en.md` e `patterns/brim_plugin_guide.md`. La nota di C3b entra nel commit del journal di D.
- **Traduzioni**: un fatto nuovo in una pagina tradotta è debito vero, **senza stamp**; la lista di `translate-validate` va nella consegna. La card e la riga degli indici it/fr/es le scrivo io, come il §7 e la guida dei plugin prevedono, poi lo stamp dell'indice.
- **Basi prima delle modifiche**:
  - `mkdocs build` verde;
  - `mkdocs check-links` con un solo errore: manca `user/transactions/import/danske-bank`, la pagina del `docs_url` che D crea;
  - `mkdocs translate-validate` con 498 errori già presenti (LaTeX e blocchi di codice), registro in `/tmp/libreFolio_l_d_base_tv.log`.
- Docs-writer al lavoro: la pagina utente, nav, l'indice EN, i badge in `user/files`, la frase di `preferences`, la sezione «report set» e la regola del `provider_code` letterale nella guida dei plugin, `providers_list`, `import-wizard.md` e il README dei campioni.

> **Note implementazione (2026-10-01), D** (docs-writer in inglese; io i tre indici tradotti):
> - **Utente**:
>   - `user/transactions/import/danske-bank.en.md`, nuova e solo in inglese. Contiene gli export (Sijoitukset → Tapahtumat, l'estratto dell'osakesäästötili), il periodo, il caricarli insieme, il file mancante, l'import annuale con sovrapposizioni, la tabella dei tipi, le commissioni nelle Correzioni, le scissioni (vero.fi), il primo import e «Align with the bank», l'errore del confronto, i buchi, la verifica di fine periodo, i limiti e i badge.
>   - `mkdocs.yml`: «Danske Bank» fra 🏦 Banks & Neobrokers, dopo Crédit Agricole.
>   - `import/index.en.md`: la card e la riga delle capacità. Io le ho riportate in it/fr/es (`set di report`, `lot de rapports`, `conjunto de informes`, come l'interfaccia) e ho stampato l'indice con `translate-stamp`; cambia solo la voce dell'indice in `.translate-hashes.json`.
>   - `user/files/index.en.md`: la sezione «🧩 Report sets» con i cinque badge.
>   - `preferences.en.md`: «Align with the bank» fra gli step facoltativi, senza cambio di versione.
> - **Sviluppatore**:
>   - `brim_plugin_guide.md`: l'avviso «`provider_code` must `return` a string literal», col motivo (R13 legge anche `provider_name` e `description`; `_PROVIDER_CODE_RE`), e la sezione «🧺 Multi-report plugins (report sets)»: ruoli, API del set, `combine` puro, zone ed esiti, punti di verità e regola di sicurezza, H0, tag, `/gap-fix`, test;
>   - `providers_list.md`: la riga di Danske;
>   - `import-wizard.md`: la sezione «🧺 Report sets» (moduli puri, passi, `gapFix`, la catena degli ID degli asset, i badge) e lo step `import.gapFix`, che resta alla versione 1.
>
>   Il README dei campioni era già a posto dalla fase B.
> - **Verificato da me sul codice**: `Korko` → interesse, la finestra di prova di 30 giorni (`PROOF_WINDOW_DAYS`), i messaggi del plugin in finlandese, gli avvisi della card `before_history_segment` e `covers_gap_fix`, le etichette delle Correzioni. Nessun dato reale: solo nomi di colonna e parole di servizio.
> - **Controlli**:
>   - `mkdocs build` verde, strict: l'unico avviso è il banner di Material;
>   - `mkdocs check-links` verde: 81 link validi, i 3 🟡 noti, e la pagina del `docs_url` ora esiste;
>   - `git diff --check` pulito; `frontend/static/sw.js` intatto.
> - **Debito di traduzione nuovo** (`translate-validate`: da 498 a 513 errori, file mancanti da 63 a 66; nessuno stamp):
>   - `user/files/index.{it,fr,es}.md`: la sezione «Report sets» e il link a `danske-bank`, cioè 5 errori e 5 avvisi per lingua;
>   - `user/settings/preferences.{it,fr,es}.md`: la frase sugli step facoltativi. `translate-validate` non la rileva, e quelle traduzioni erano già segnalate come troncate (21–22 %);
>   - `user/transactions/import/danske-bank.{it,fr,es}.md`: non esistono, la pagina è solo in inglese per scelta.
>
>   Gli indici dell'import non hanno debito nuovo: riportati a mano e stampati.
>
> **⚠️ Fuori pista: design e codice divergono, e la documentazione segue il codice** (rilevato dal docs-writer):
> 1. lo slug è `danske-bank`, non `danske_bank`;
> 2. gli avvisi di copertura si chiamano `coverage_starts_late` / `coverage_ends_early`, e la preview non conta le righe prima di H0 (le conta solo la Revisione);
> 3. le Correzioni chiedono una decisione per ogni trade;
> 4. l'avviso del file mancante compare dopo il primo «Next: Select Files»;
> 5. la seconda metà di A18 non c'è: nessuna scelta del plugin per membro;
> 6. A17 non c'è nel wizard: un set con un originale eliminato resta bloccato finché l'export non si ricarica, e solo il badge della pagina file segue la v5.3;
> 7. le verifiche non elencano le righe sospette, e nessuno elenca i titoli scambiati in un buco;
> 8. un file caricato senza `batch_id` non è in nessun set, e il suo parse risponde 422 `set_required`;
> 9. il dettaglio dell'analisi offre solo lo scaricamento del combinato;
> 10. `settlement_lag_business_days` è nel contratto ma il framework non lo legge.
>
> **Da segnalare al coordinatore** (fuori dallo scope di D):
> - **UX**: dopo un anno saltato, la correzione compare sotto «Starting point» e non «After the gap». Il plugin marca `opening` il primo segmento di ogni set (`broker_danske_bank.py:718`): i numeri sono giusti, l'etichetta no.
> - **Pagine che citano il flusso d'import e non sono state toccate**: `user/transactions/import/how-to.en.md` (la tabella dei passi e «Guided First Import» non nominano «Align with the bank») e `user/brokers/import.en.md` («Uploaded Reports» non nomina la colonna dei set). Aggiornarle aggiunge debito di traduzione.

### D — ✅ pronta per il checkpoint (2026-10-01)

**Commit di D**: `b643afb31` docs(import): document Danske Bank and report sets e `cf5cb2e35` docs(journal): record phase D and the dropped C3b.

### E — ⏳ in corso (2026-10-01)

- Decisione del developer, riportata dal coordinatore: «Etichetta e due pagine in fase E; A17 nel backlog». Via da `cf5cb2e35`, corsia 6156.

#### E.0 Specifica (2026-10-01)

**1. L'etichetta del gap-fix dopo un anno saltato**
- Oggi dopo un anno saltato la correzione compare sotto «Starting point». Il plugin marca `opening` il primo segmento di ogni set (`broker_danske_bank.py:718`), e il parse ne ricava il tipo (`:1474`).
- Il plugin non può sapere se LibreFolio ha già una storia: `combine` è puro, e `H0` lo calcola il framework. In un import successivo, `apply_history` (`brim_report_sets.py`) toglie già le righe prima di `H0` e `opening_cash` (`_without_represented_rows`), quindi i numeri della spiegazione sono giusti. Resta sbagliato solo il tipo.
- **Correzione, nel framework**: in `apply_history`, in un import successivo, un checkpoint datato **da `H0` in poi** diventa `gap`. Chiude un buco in una storia che esiste già, e il passo lo mostra come «After the gap».
- Il checkpoint della vigilia di `H0` (`H0 − 1`, cioè il reimport del primo set) resta `opening`, come fissano due test di oggi. Il primo import non cambia.
- Il plugin non cambia. La regola vale per ogni plugin a set.
- **Test** (test-author, rossi prima):
  - in `services brim-report-sets` (`TestApplyHistoryLaterImport`), un import successivo col primo checkpoint `opening` dopo `H0` torna `gap`;
  - in `api brim`, se praticabile: una storia Danske già salvata, poi il parse del set principale e il gap-fix danno `kind == "gap"`.
- **Controlli**: `services brim-report-sets`, `services brim-gap-fix`, `external brim-danske-bank`, `api brim`.

**2. Le due pagine utente** (docs-writer, solo EN, **senza stamp**, il debito nella consegna):
- `user/transactions/import/how-to.en.md`: «Align with the bank» nella tabella dei passi e in «Guided First Import»;
- `user/brokers/import.en.md`: la colonna dei set in «Uploaded Reports».

**3. Backlog — A17** (da design v5.3, §4.7, riga «Un file del set eliminato»):
- Se l'originale di un set viene eliminato dopo il combine, e il combinato c'è ed è aggiornato, il set dovrebbe restare importabile, con «originale eliminato» nella card.
- Oggi il wizard blocca il set finché l'export non si ricarica: la preview dice `complete: false`, e `setBlocksAnalysis` la segue.
- Solo il badge della pagina file segue la v5.3 (`fileSetBadges`).
- Serve anche il backend: la preview, o il combine riusato, devono considerare un combinato aggiornato come sostituto dei membri eliminati.
- Decisione del developer: non ora.

**4. I controlli finali**, come da piano (§10): le suite del backend e del frontend toccate dal workstream, gli E2E del wizard e dei set, la documentazione, `check-orphans`, il controllo dei dati reali, la porta libera. Poi la consegna e la voce 🧪 per il CHANGELOG.

> **Note implementazione (2026-10-01), E.1 l'etichetta**:
> - **Rosso** (test-author, corsia 6156):
>   - in `test_brim_report_sets.py`, `TestApplyHistoryLaterImport`: dopo un anno saltato il primo checkpoint è un `gap` (con le politiche `summarize` e `import`); un checkpoint datato `H0` è un `gap`; e una guardia, il primo import con politica `import` tiene `opening` anche dopo `H0`;
>   - in `test_brim_api.py`, RS-E01: una storia Danske salvata prima del set principale, poi parse e gap-fix danno `kind == "gap"` e un versamento di 2599.50;
>   - risultati: `services brim-report-sets` 3 rossi e 223 verdi, `api brim` 1 rosso e 63 verdi, tutti sul tipo (`'opening'` invece di `'gap'`); `services brim-gap-fix` 99/99 e `external brim-danske-bank` 324/324 invariati.
> - **Cura** (`brim_report_sets.apply_history`): in un import successivo, un checkpoint tenuto e datato da `H0` in poi diventa `gap`. Il docstring dice perché: il plugin non può conoscere `H0`. Black e ruff puliti.
> - **Verde**: `services brim-report-sets` 226/226, `services brim-gap-fix` 99/99, `external brim-danske-bank` 324/324, `api brim` 64/64.
>
> **⚠️ Fuori pista** (dal test-author): ogni avvio del backend condiviso chiama `auto_build_mkdocs()`. Se una pagina è più recente del sito costruito, ricostruisce la documentazione e scrive file tracciati (`mkdocs_src/docs/static`, `frontend/static/sw.js`). Dopo ogni corsa nella corsia controllo `git status`: finora nessun file generato è comparso.

> **Note implementazione (2026-10-01), E.2 le due pagine** (docs-writer, solo EN, senza stamp):
> - `how-to.en.md`:
>   - la riga «⚖️ Align with the bank» nella tabella dei passi, e «four» passi facoltativi invece di «three»;
>   - una frase sui set al passo 2, una sul passo nuovo al passo 4, e «Align with the bank» in «Guided First Import».
> - `user/brokers/import.en.md`: la colonna **Report set** in «Uploaded Reports».
> - `danske-bank.en.md`: l'ancora esplicita `{: #first-import-align-with-the-bank }`, lo stesso id di prima. I link di `how-to` resteranno validi quando la pagina avrà le traduzioni, che dovranno tenere l'ancora.
> - `mkdocs build` (strict) e `check-links` verdi (81 link validi).
> - **Debito di traduzione nuovo** (`translate-validate` da 513 a 525 errori, avvisi da 376 a 382):
>   - `how-to.{it,fr,es}.md`: i link a `danske-bank`, 9 errori;
>   - `brokers/import.{it,fr,es}.md`: il link a `files/index.md#report-sets`, 3 errori e 6 avvisi.
>
>   Da tradurre: la tabella dei passi, la fine del passo 2, il paragrafo del passo 4, il punto di «Guided First Import» e il punto di «Uploaded Reports».

> **Note implementazione (2026-10-01), E.4 i controlli finali** (corsia 6156, un comando alla volta, script `/tmp/libreFolio_l_efinal.sh`, log `/tmp/libreFolio_l_efinal_*.log`):
> - **Statici**: `dev.py lint` pulito; `front check` al pavimento (3 errori, 41 avvisi, negli stessi file di sempre).
> - **Unit del frontend**: `tx-unit` 495/495, `core-unit` 2704/2704, `component-unit` 2182/2182, `onboarding-component-unit` 409/409.
> - **Backend**: `services brim-provider-base` 34, `brim-report-sets` 226, `brim-gap-fix` 99, `transaction` 68, `settings` 23; `external brim-danske-bank` 324, `brim-providers` 574 più 2 saltati (i plugin di oggi non cambiano); `api brim` 64, `api settings` 39; `api transactions` 22 più 1 saltato; `db referential-integrity` 17.
> - **E2E**, dopo `front build --debug`:
>   - verdi: `tx-import-report-set` 8/8, `tx-import-report-set-guide` 2/2 (desktop e mobile), `tx-import-upload` 9, `tx-import-flow` 10, `tx-import-duplicate-precedence` 6, `tx-asset-identity` 9, `tx-import-resolution` 12, `tx-import-matching` 6, `files` 22, `onboarding-tour` 10, `onboarding-guides` 24, `settings` 45;
>   - rossi, solo quelli noti dal triage di C2: `tx-brim-import` T1 (spec seriale: ne restano 7 non eseguiti), `tx-ca-contract` CAC-011 e CAC-012 (10 verdi), `brokers-detail.spec.ts:713` di I (29 verdi).
> - **Registrazioni e albero**: `check-orphans` pulito; `git diff --check` pulito; nessun file generato fra le modifiche; 6156 libera.
> - **Privacy**:
>   - i 5 campioni Danske non hanno valori in comune con gli export reali (554 celle);
>   - le 22.558 righe aggiunte dai 29 commit del workstream (prima linea, senza merge), più le modifiche non committate, non contengono nessuno dei 163 token distintivi degli export reali.
>
>   Lo script stampa solo un hash del token, mai il valore. Quattro parole generiche che gli export condividono con qualunque testo sono escluse: «number», «account», «holder», «maksaja».
> - **Documentazione**: `mkdocs build` (strict) e `check-links` verdi, nel giro di E.2.
>
> **⚠️ Fuori pista: `api transactions` salta ancora `test_delete_linked_without_pair`**, anche dopo `test db populate --force` nella corsia, come chiesto nella fase B. Lo salta la fixture `test_asset_id` (`test_transactions_api.py:127-162`): `pytest.skip("Could not create test asset")` quando `GET /assets` non le dà un asset e `POST /assets` non risponde 200. È una condizione del setup del test, fuori da L e indipendente dai dati della corsia; il suo proprietario dovrebbe fare un triage.

### E — ✅ completata (2026-10-01)

**Commit di E**: `1a3ba20f2` fix(brim): mark later-import checkpoints as gaps, `37abcd203` docs(import): mention report sets in import pages e `2d0923a4c` docs(journal): record phase E.

---

## 12. Fase F — la review del developer (2026-10-02)

### Review manuale (2026-10-02)

- **Server di review**:
  - porta 6166, `--data-dir /tmp/librefolio-r2-l-review`, DB nuovo popolato senza `--force`;
  - `front build --debug` prima;
  - server staccato, broker «Danske Bank (review)» creato via API.
- **Prova a secco**, prima di chiamare il developer: via API nella corsia 6156, su un broker usa e getta (cancellato con i suoi file).
  - Primo import, set principale, solo righe di cassa: `opening` 2020-02-02, versamento 2699.50.
  - Secondo import, set con buco: due checkpoint `gap`, 2020-08-31 e 2021-01-04.
- **Il developer** ha provato sia gli export reali dell'autore della issue, caricati da lui solo sul server di review, sia i campioni sintetici.
  - **Privacy**: niente dei file reali entra in test, campioni, log, piano o messaggi di commit. I difetti si riproducono coi dati sintetici. Alla fine la `--data-dir` di review si cancella.
- Esito: il flusso è corretto, «Dopo il buco» compare, la pagina File «mi pare sufficiente». Chiede miglioramenti grafici e ha trovato difetti.
- Via del coordinatore alla fase F, da `2d0923a4c`, nella corsia 6156. Superfici:
  - wizard, `ParseDetailModal`, `ReportSetCard`, `GapFixStep`, i18n `importWizard.*`;
  - per U2-B, la preview del backend più `api sync`;
  - **anche D4–D7**: `TransactionBulkModal.svelte`, `TransactionFormModal.svelte` se serve, i loro test, i testi dell'editor.

  Due checkpoint: **F1** per i difetti (D1, D2, D4–D7) e **F2** per la grafica (U1–U4).

#### F.0 Specifica (2026-10-02)

**Decisioni del developer** (testuali):
- **D3 / D7, la lingua del plugin**: «riguardo D3 non è un problema, so che il design prevede che, basandosi sulle intestazioni, il plugin risponda nella lingua del report»; «va bene che il plugin risponda in filandese, essendo il report in quella riga, io ti ho fatto i copia e incolla solo perchè non lo so leggere, ma in fondo sono il dev, non l'utente fillandese».
  - **D7 resta com'è.** Il meccanismo `importWizard.brimNotice.<code>` resta come riserva, ma per Danske non si aggiungono chiavi.
- **D4**: «D4 diciamo che va in tandem con il fatto che non si era fatto il primo validaate now, ci fosse stato sarebbe stato più chiaro».
- **D5**: «dopo un processo di import, indipendentemente dalla dimensione dell'import, un validate now è bene che parta in automatico, solo il primo però, gli altri sono in carico all'utente».
- **D6**: «se apro e chiudo non è sufficiente, devo fare manual->auto affinchè auto gli vada bene, se già lo apre è sufficiente direi».
- **U1**: «credo che la B sia più adatta, ma nel set potrebbe essere interessante raccogliere, in caso di più file da agglomerare, titoli e cassa in 2 liste ordinate nei periodi (rispetto lo start period)».
- **U2**: «credo B, le barre mi piacciono, ma serve mostrare bene le cose, magari aggiungendo anche un infobox che se ci si passa sopra ti dice inizio e fine di quel periodo e quante transazioni sono registrate nel mezzo (se si riesce ad avere con poco sforzo)».
- **U3**: «oltre allo scarica, anche la semplice preview non sarebbe male».
- **U4**: «anche riguardo U4 il design di B sembra più accattivante».
- **Domanda del developer**: «cosa succede se 2 file si sovrappongono parzialmente o completamente come periodo?»
  - Risposta (regola M, D-S28, `_RoleMerge` in `broker_danske_bank.py`): per ogni giorno valgono le righe del file più recente che lo copre, cioè quello che finisce per ultimo.
  - Se i file coincidono su quel giorno, le righe contano una volta sola, senza avvisi.
  - Se non coincidono, vince il più recente, e la card mostra `overlap_mismatch` col numero dei giorni in disaccordo.

**F1 · i difetti**
- **D1, il passo 1 perde il secondo «Avanti»** (`ImportWizardModal.svelte`).
  - Causa: l'effetto che chiude l'area di upload a ogni `mousedown` esterno. Dopo l'avviso del set incompleto, che riapre l'area, il `mousedown` su «Avanti» la richiude, la modale cambia altezza, il pulsante si sposta prima del `mouseup` e il clic si perde.
  - Correzione: niente chiusura automatica finché `step1SetWarnings` non è vuoto.
  - Test: con l'avviso visibile, un `mousedown` fuori dall'area la lascia aperta, e **un solo** «Avanti» porta al passo 2.
- **D2, i campi da completare nel dettaglio dell'analisi** (`ParseDetailModal.svelte`). Vale per ogni plugin. Per ogni todo:
  - riga, campo e messaggio: `importWizard.brimNotice.<reason_code>`, e se manca il messaggio del plugin, come in `FixFlaggedStep.todoMessage`;
  - le chiavi di contesto che l'interfaccia conosce, come fatti con etichetta: `charges` con la valuta, `cash`, `split_suggestions` in elenco (vedi «🗝️ context keys the frontend understands» nella guida dei plugin);
  - le evidenze con `BrimEvidenceTable`, chiudibili;
  - il resto del contesto in «Dettagli tecnici», chiuso.

  Nessun `JSON.stringify` in linea. Testid: `parse-detail-todo` (`data-reason-code`, `data-severity`) e `parse-detail-todo-technical`.
- **D4**, insieme a D5: nell'editor, ogni voce dei banner dei todo (bloccanti e avvisi) è un pulsante `tx-bulk-todo-goto` (`data-row-id`). Porta alla riga e la evidenzia (`tableRef.navigateToRowId`, come `jumpToIssue`). Il banner degli avvisi riceve lo stesso elenco.
- **D5, una validazione automatica dopo ogni import.** Definizione di «una volta»:
  - ogni volta che il wizard consegna righe all'editor (`onImportBatch`), l'editor lancia **una** validazione, la stessa di «Validate now», appena le righe nuove sono al loro posto e qualunque sia il numero di righe;
  - non torna: dopo valgono le regole di oggi (validazione automatica solo fino a `AUTO_VALIDATE_THRESHOLD`, 50 righe; sopra, «Validate now» a mano);
  - un nuovo import ne lancia un'altra;
  - se un'altra validazione è già in corso o in coda, quella dell'import la sostituisce: niente doppioni.

  Va fissata da un test.
- **D6, Auto (WAC)**: nei due filtri che chiudono i todo (`TransactionBulkModal.svelte:803` e `:2460`), un todo su `cost_basis_override` è risolto anche quando la riga è applicata con `cost_basis_mode === 'auto'`, che sia il default o una scelta. Test: una riga col todo, applicata senza toccare la modalità, non ha più il todo.
- **D7, il testo dell'avviso** `importWizard.todoWarningConfirmMessage`: si toglie l'esempio delle obbligazioni scadute e diventa generico («un valore ricavato dall'importer, non ancora verificato»). 4 lingue, con `dev.py i18n update`. Con D4 l'utente trova la riga.

**F2 · la grafica**
- **U1-B**: il set resta una card.
  - I file del set vanno in **una DataTable per ruolo**, «Titoli» e «Cassa», ordinate per inizio del periodo. Colonne: file, periodo, righe, anteprima, eliminazione.
  - I file non riconosciuti vanno a parte.
  - Sotto le card, la tabella dei singoli prende il titolo «Altri file di questo broker» quando il broker ha anche set.
- **U2-B**:
  - **Backend**: `BRIMSetPreview` riceve `history_end` (l'ultimo giorno della storia salvata, cioè la transazione più recente col tag di storia del plugin) e `history_count` (le transazioni col tag fra `H0` e `history_end`). `api sync` nella corsia.
  - **Linea del tempo**:
    - date sulle barre;
    - i buchi fra due file dello stesso ruolo, tratteggiati;
    - la barra di LibreFolio da `H0` a `history_end`, non più fino alla fine della linea;
    - una legenda;
    - al passaggio del mouse, inizio, fine e numero di righe del file, oppure le transazioni salvate per la barra di LibreFolio.
- **U3**: nel dettaglio dell'analisi, l'abbinamento ha:
  - i chip degli esiti (coppie, solo cassa, riassunti, rimandati, esclusi);
  - una tabella dei motivi coi conteggi;
  - i comandi «Anteprima» (`FilePreviewModal` sul combinato) e «Scarica».
- **U4-B, «Allinea con la banca»**:
  - in alto, una card di riepilogo per punto (tipo, data, differenza di cassa, numero di posizioni) e una per verifica (torna o non torna, differenza);
  - un clic su una card filtra la tabella; un secondo clic toglie il filtro;
  - la card si apre col confronto completo: cassa, posizioni con le quantità mascherabili, spiegazione, note;
  - sotto, **una sola DataTable** delle correzioni: selezione, Punto, Data, Tipo con icona, Asset, Qtà, Cassa, Tag o «costo da inserire»;
  - i comandi della revisione: seleziona tutto, deseleziona tutto, seleziona in vista.

  Testid: `gapfix-summary` (`data-key`, `data-kind`, `data-as-of`), `gapfix-table`, righe `tr[data-row-id=<chiave della proposta>]`, `gapfix-proposal-toggle` (`aria-pressed`), `gapfix-select-all`, `gapfix-deselect-all` e `gapfix-select-visible`. Restano la radice `import-wizard-gapfix` coi conteggi, `gapfix-group`, `gapfix-error` e `gapfix-info-hidden-titles`.

**Test** (test-author, rossi prima, solo dati sintetici): un giro per F1 e uno per F2. Registrazioni solo in aggiunta, in `_frontend_transaction.py`. Gli E2E dell'editor vanno nelle specifiche `tx-bulk-*` o `tx-wac-bulk`, se servono.

### F1 — ⏳ in corso (2026-10-02)

- **Fine della review**, sul via del developer («Ho finito: spegni il server e cancella i dati della review»):
  - il server della 6166 è fermo, e `lsof` non mostra listener;
  - `/tmp/librefolio-r2-l-review` è cancellata, e `ls` dà «No such file or directory»;
  - è cancellato anche il log del server, perché poteva contenere i nomi dei file reali;
  - l'istantanea del DB nel `.testLog` è del `db populate`, presa prima dell'avvio del server: contiene solo dati finti.
- Il coordinatore conferma D3: «the developer has decided, twice … D7 holds».
- **Rosso di F1** affidato al test-author (D1, D2, D4, D5, D6), nella corsia 6156, con soli dati sintetici.

> **Note implementazione — il rosso (2026-10-02)**, test-author, corsia 6156, solo dati inventati:
> - **D1**: un test nuovo in `tx-import-report-set.spec.ts` (ora 9). Rosso: col set incompleto, il primo «Avanti» non porta al passo 2.
> - **D2**: `ParseDetailModal.test.ts`, nuovo, 11 test rossi. Il test registra da sé la chiave `importWizard.brimNotice.probe_localized_blocker`, così «la chiave esiste» non dipende dal catalogo.
> - **D6**: `bulkTodos.test.ts`, nuovo, 11 test rossi, sulla funzione pura `remainingTodos` (il modulo non esisteva).
> - **D4 e D5**: `tx-bulk-import-handoff.spec.ts`, nuovo, 2 test rossi, con l'azione nuova `tx-bulk-import-handoff`.
> - `tx-unit`: 517 test, 22 rossi. `check-orphans` pulito.
>
> **Note implementazione — la cura**:
> - **D1** (`ImportWizardModal.svelte`): l'effetto che chiude l'area di upload a ogni `mousedown` esterno esce subito se `step1SetWarnings` non è vuoto.
> - **D6**: modulo nuovo `frontend/src/lib/utils/transactions/bulkTodos.ts`, con `remainingTodos(todos, fields)`.
>   - Un todo resta finché il suo campo è vuoto (`null`, `undefined` o `''`). Un todo su `cost_basis_override` è risolto anche da `cost_basis_mode === 'auto'`.
>   - L'ordine resta quello di prima, e l'elenco in ingresso non cambia.
>   - I due filtri di `TransactionBulkModal.svelte` (`patchRowFromForm` e `patchDualRowFromForm`) chiamano la funzione. La modalità è già scritta da `applyFormPayload` prima del filtro.
> - **D5** (`onImportBatch`): `scheduler.trigger('change')` diventa `scheduler.trigger('manual')`.
>   - `manual` ignora la soglia di 50 righe e l'anti-rimbalzo, cancella il debounce in coda e parte subito: una validazione per import, senza doppioni.
>   - Dopo, valgono le regole di prima. `validateFn` non guarda il motivo, quindi «manual» non ha effetti in più sull'interfaccia.
> - **D4** (`TransactionBulkModal.svelte`):
>   - ogni voce dei due banner è un pulsante `tx-bulk-todo-goto` (`data-row-id`) che chiama `jumpToTodoRow`;
>   - `jumpToTodoRow` fa come `jumpToIssue`: se la riga è nascosta dai filtri, mostra il toast `transactions.bulk.issueRowsHidden`; altrimenti `navigateToRowId`, che sceglie la pagina ed evidenzia la riga;
>   - il banner degli avvisi diventa un contenitore `tx-bulk-todo-warnings` con l'interruttore `tx-bulk-todo-warnings-toggle`, chiuso come quello dei bloccanti, e l'elenco dei todo;
>   - l'id di destinazione è la riga visibile: `op.pairedWith ?? op.tempId`, così il todo di una gamba nascosta porta alla sua coppia.
> - **D2** (`ParseDetailModal.svelte`): ogni todo è un `parse-detail-todo` (`data-reason-code`, `data-severity`) con:
>   - riga, campo e messaggio, con la regola di `FixFlaggedStep.todoMessage`;
>   - i fatti in un `<dl>`: riga del file, importo (`cash`), commissioni (`charges`), nominale (solo con `compare_nominal`). Gli importi passano da `formatCurrencyAmountPlain`, quindi seguono la privacy;
>   - `split_suggestions` in un `<ul>`;
>   - le evidenze con `BrimEvidenceTable` chiudibile;
>   - il resto del contesto in `<details data-testid="parse-detail-todo-technical">`, chiuso, col JSON indentato in un `<pre>`.
>
>   Una chiave conosciuta che non si può mostrare (per esempio un importo senza valuta) non sparisce: finisce nei dettagli tecnici. `split_hint` e `compare_nominal` sono istruzioni per il passo di correzione e non si mostrano.
> - **D7**: `importWizard.todoWarningConfirmMessage` senza l'esempio delle obbligazioni, in 4 lingue, con `dev.py i18n update`.
> - **i18n nuove** (`dev.py i18n add`, 4 lingue): `importWizard.parseDetail.{sourceRow, charges, suggestions, technical}` e `importWizard.todoGoto`. Riusate: `importWizard.fixStep.splitRowAmountLabel` e `splitNominalLabel`.
>
> **Evidenze** (corsia 6156, un comando per volta):
>
> | Verifica | Esito |
> |---|---|
> | `front-transaction tx-unit` | `517 passed` (i 22 rossi sono verdi) |
> | `front check` | 3 errori e 41 avvisi, il pavimento: tutti in `BrokerSharingPanel`, `GlobalSettingsTab`, `TransactionFormModal.test.ts` e `ToolExecutionMetrics`; nessuno nei file toccati |
> | `front-utility core-unit` (con i gate della privacy e degli sink HTML) | `2704 passed` |
> | `front-utility component-unit` | `2182 passed` |
> | `front-utility onboarding-component-unit` | `409 passed` |
> | `front build --debug` | ok |
> | E2E `tx-bulk-import-handoff` (D4, D5) | `2 passed` |
> | E2E `tx-import-report-set` (D1 compreso) | `9 passed` |
> | E2E `tx-import-flow` / `tx-import-upload` / `tx-import-report-set-guide` | `10` / `9` / `2 passed` |
> | E2E `tx-wac-bulk` / `tx-bulk-diagnostics` / `tx-bulk-operations` | `10` / `2` / `10 passed` |
> | E2E `tx-paired-edit` / `tx-import-resolution` | `4` / `12 passed` |
> | E2E `tx-ca-contract` | `10 passed`, rossi CAC-011 e CAC-012, già noti |
> | E2E `tx-brim-import` | rosso T1, già noto |
> | E2E `tx-import-file-selection` | `1 passed`, 1 rosso: vedi «Fuori pista» |
> | prettier sui file toccati e sui test nuovi | pulito, nessuna riformattazione |
> | `check-orphans` | pulito |
> | `dev.py lint` | verde |
> | `git diff --check` | pulito |
> | porta 6156 | libera |
>
> **⚠️ Fuori pista**:
> - **`tx-import-file-selection.spec.ts:198`**, rosso: il broker di controllo, appena creato con id 10, mostra 3 file invece di 1. Non viene da F1:
>   - ogni invocazione del runner ripopola il DB con `--force --with-reports`, senza `--clean`, e gli id dei broker ripartono;
>   - i file BRIM restano su disco: nella corsia ci sono file `ca-contract-*` lasciati dai rossi CAC-011/012 (del 01/10 e di oggi) e file dei test API del 01/10, sotto i broker 9–46;
>   - un broker nuovo con un id riusato eredita quei file. La pulizia del test, che cancella il broker tramite l'API, li ha poi rimossi: ora in `broker_10` resta solo il file `ca-contract` di oggi, scritto dopo;
>   - l'asserzione riguarda il conteggio dei file al passo 2, che arriva dal backend; D1 cambia solo l'area di upload del passo 1, e solo con un avviso di set.
>
>   È il caso già nel backlog del coordinatore («`broker_<id>` files surviving a DB rebuild without `--clean`»). Per riavere la spec verde nella corsia serve un `test db populate --force --clean` sulla mia data dir, che il piano non prevede: lo chiedo al coordinatore.
> - **`scripts/test_runner/_frontend_transaction.py`**: black vorrebbe riformattarlo e ruff trova 4 errori, ma è identico su HEAD: il file ha uno stile suo, scritto a mano. Non lo tocco.

### F1 — ✅ pronta per il checkpoint (2026-10-02)

> **F1 committata** dal developer: `e57d08b84` (13 file) e `cf87bb2ff` (journal).
>
> **⚠️ Fuori pista — la verifica d'ambiente di `tx-import-file-selection`** (autorizzata dal coordinatore, 2026-10-02):
> - `test db populate --force --clean` sulla sola `/private/tmp/librefolio-r2-l`, exit 0. Dopo, `broker_reports/{uploaded,parsed,failed}` hanno 0 voci e 0 file.
> - La spec rilanciata da sola: `2 passed`. La causa era l'ambiente: file BRIM rimasti su disco, ereditati dagli id dei broker riusati. Resta nel backlog del coordinatore.
> - Una nota per il backlog: `clean_data_dirs` scrive «(0 files)» anche quando cancella le cartelle `broker_N`, perché conta solo i file al primo livello.

### F2 — ⏳ in corso (2026-10-02)

Base `cf87bb2ff`, corsia 6156.

#### F2.0 Contratto (2026-10-02)

Precisa le voci di F.0 su U1–U4; dove F.0 non decideva, la scelta è indicata.

**U2-B · backend** (`schemas/brim.py`, `services/brim_report_sets.py`)
- `BRIMSetPreview.history_end: Optional[date] = None`: la data della transazione più recente col tag di storia del plugin, come tag esatto.
- `BRIMSetPreview.history_count: int = 0`: quante transazioni hanno quel tag.
  - **Precisazione di F.0** («fra H0 e history_end»): si contano tutte, correzioni del gap-fix comprese. Ogni transazione col tag cade già fra la vigilia di H0 e `history_end`, e la correzione di partenza è una transazione salvata come le altre.
- Una sola query, quella di `_tagged_dates`, dà H0, la fine e il conteggio; `history_start` non cambia. Gli altri broker e i tag che contengono il tag solo come sottostringa non contano.
- Poi `api sync` nella corsia.

**U2-B · la linea del tempo** (`buildSetTimeline`, funzione pura)
- Ingresso in più: `members[].rows`, `history_end`, `history_count`.
- Barre: una per voce di copertura, come oggi, in ordine di inizio, poi di fine. Ogni barra porta `rows`, le righe del suo file (`null` se ignote).
- Buchi (`gaps`), per ruolo:
  - si scorrono le barre in ordine di inizio, tenendo la fine più lontana raggiunta, `e`;
  - una barra che parte dopo `e + 1` apre un buco da `e + 1` alla vigilia del suo inizio, con la stessa aritmetica delle barre;
  - mai un buco prima della prima barra o dopo l'ultima.
- Storia: da H0 a `history_end`, e non più fino alla fine della linea. Se `history_end` è prima di H0 (solo una correzione nella storia), la fine è H0. Porta `count` (`history_count`, oppure 0). È `null` senza H0.
- L'intervallo della linea comprende anche `history_end`. Resta `null` se nessun membro ha una copertura.

**U1-B e U2-B · `ReportSetCard.svelte`**
- Per ruolo:
  - il titolo resta: nome, estensioni, storia massima;
  - i file del ruolo vanno in una **DataTable** dentro `report-set-role-table` (`data-role`), con righe `tr[data-row-id=<file_id>]`;
  - ordine per inizio del periodo (il minimo degli inizi delle sue coperture), poi per nome; i file senza copertura vanno in fondo;
  - colonne: file, periodo (inizio → fine), righe;
  - azioni di riga: il menu `row-actions-<file_id>` con `context-menu-action-preview` e `context-menu-action-delete`; il doppio clic apre l'anteprima;
  - niente ordinamento, filtri, paginazione né selezione: il set si sceglie intero con `report-set-select`, e l'ordine resta quello chiesto dal developer.
- I file non riconosciuti stanno a parte: `report-set-unrecognised` (`data-file-id`). `report-set-member` sparisce.
- Linea del tempo (`report-set-timeline`):
  - `report-set-timeline-bar`: `data-role`, `data-file-id`, `data-start`, `data-end`, `data-rows`;
  - `report-set-timeline-gap`: `data-role`, `data-start`, `data-end`, tratteggiato;
  - `report-set-timeline-history`: `data-start`, `data-end`, `data-count`, nell'ultima riga;
  - accanto a ogni riga, le date delle sue barre;
  - legenda `report-set-timeline-legend` con `report-set-timeline-legend-item` (`data-kind` = `file` | `history` | `gap`). `history` e `gap` compaiono solo se ci sono.
  - Infobox: ogni barra, buco o storia apre un `Tooltip` al passaggio del mouse o al clic (`tooltip-content`). Dentro: inizio e fine (`formatIsoDay`) e il numero di righe del file, oppure delle transazioni in LibreFolio; per un buco, «non coperto».
- Tutto il resto della card non cambia.

**U1-B · il wizard**: sopra la tabella dei file singoli, il titolo `import-wizard-other-files-<brokerId>` («Altri file di questo broker»), solo se il broker ha anche set.

**U3 · `ParseDetailModal.svelte`**, sezione `parse-detail-pairing` (gli attributi restano)
- Gli esiti diventano chip `parse-detail-pairing-outcome` (`data-outcome`, `data-count`), tutti e cinque, nell'ordine di `SET_OUTCOMES`; quelli a zero sono attenuati.
- I motivi vanno in una tabella `parse-detail-pairing-reasons`, con righe `parse-detail-pairing-reason` (`data-reason`, `data-count`): motivo e righe.
- I comandi:
  - «Anteprima», `parse-detail-preview-combined`, chiama `onPreview`, che per un set apre già il combinato; c'è solo se `onPreview` c'è;
  - «Scarica», `parse-detail-download-combined`, resta.

**U4-B · `GapFixStep.svelte`**
- Restano:
  - la radice `import-wizard-gapfix`, coi conteggi;
  - `gapfix-group` e `gapfix-error`;
  - `gapfix-info-hidden-titles`;
  - la prop `onToggle(key)`.
- Prop nuova: `onSetSelected(keys, selected)`.
- Le card, per gruppo, in ordine di data (a parità di data, prima i punti), sono pulsanti `gapfix-summary`:
  - attributi: `data-key`, `data-kind` (`opening` | `gap` | `verification`), `data-as-of`, `aria-pressed`;
  - su un punto, anche `data-proposals` e `data-positions` (le posizioni con differenza diversa da zero); su una verifica, `data-ok`;
  - contenuto di un punto: titolo con la data, le differenze di cassa diverse da zero (`CurrencyAmount`, quindi mascherabili), quante posizioni e quante correzioni;
  - contenuto di una verifica: torna o non torna, e la differenza se non torna.
- **Il clic** (scelta mia: F.0 non distingueva punti e verifiche):
  - una card diventa il punto attivo (`aria-pressed="true"`, una sola per gruppo); un secondo clic la spegne;
  - il punto attivo apre `gapfix-point-details` (`data-key`) col confronto completo, coi testid di oggi: `gapfix-checkpoint` con `gapfix-cash-row`, `gapfix-position-row` (quantità mascherabili), `gapfix-explanation` e `gapfix-note`, oppure `gapfix-verification` con `gapfix-verification-cash-row`;
  - un punto attivo filtra la tabella alle sue correzioni. Una verifica non ne ha, quindi apre il confronto e lascia la tabella intera: una tabella vuota sembrerebbe aver perso le correzioni.
- **La tabella**: una sola DataTable `gapfix-table` per gruppo (solo se il gruppo propone qualcosa), con righe `tr[data-row-id=<chiave della correzione>]`, attenuate se non selezionate.
  - Colonne: selezione, Punto (Partenza o Dopo il buco), Data, Tipo con icona, Asset, Qtà (visibile: è una transazione), Cassa (`CurrencyAmount`), Tag (`gap_fix`, oppure «costo da inserire»).
  - Il selettore è un pulsante `gapfix-proposal-toggle` (`aria-pressed`, `data-key`, `data-type`, `data-date`, `data-point`) in una cella `custom` nuova, perché la cella `editable-checkbox` della DataTable condivisa non ha testid. La DataTable condivisa non si tocca.
  - Il tipo usa la cella `image` col testo (niente HTML nuovo).
  - `gapfix-proposal` sparisce.
- **I comandi della revisione**, per gruppo:
  - `gapfix-select-all` e `gapfix-deselect-all` agiscono su tutte le correzioni del gruppo;
  - `gapfix-select-visible` seleziona le righe della pagina mostrata, filtro compreso, e lascia le altre come sono.
- Il wizard passa `onSetSelected`, che aggiorna `gapFixSelected` in un colpo solo.

**i18n** (`dev.py i18n add`, 4 lingue, solo `importWizard.*`; i nomi definitivi nell'handoff): titolo «Altri file», colonne del set, legenda e infobox, «Punto», etichette brevi dei punti, conteggi di posizioni e correzioni, suggerimento sul filtro, «Anteprima del combinato» e colonna del motivo. Si riusano `common.*`, `importWizard.selectVisible`, `importWizard.reportSet.rows`, `gapFix.checkpointOpening`, `gapFix.checkpointGap`, `gapFix.verificationTitle`, `gapFix.costToEnter` e `gapFix.selectedCount`.

**Test** (test-author, rossi prima, solo dati inventati, corsia 6156):
- backend: `TestPreviewSet` in `test_brim_report_sets.py` (`services brim-report-sets`);
- Vitest:
  - `importReportSets.test.ts`: la linea del tempo, aggiornando il test della storia «fino alla fine»;
  - `ReportSetCard.test.ts`, nuovo, registrato in `tx-unit`;
  - `GapFixStep.test.ts`, riscritto sul contratto nuovo;
  - `ParseDetailModal.test.ts`, la parte U3;
- E2E: `tx-import-report-set.spec.ts`, coi selettori nuovi e i flussi di U1–U4.

> **Note implementazione — il rosso di F2 (2026-10-02)**, test-author, corsia 6156, solo dati inventati, nessun file di prodotto toccato:
>
> | Comando | Esito | Perché è rosso |
> |---|---|---|
> | `services brim-report-sets` | 6 rossi, 226 verdi | i 6 test nuovi: `history_end` e `history_count` non esistono |
> | `front-transaction tx-unit` | 55 rossi, 520 verdi | `importReportSets` 11, `ReportSetCard` 17 (file nuovo), `GapFixStep` 23 (riscritto), `ParseDetailModal` 4 (U3); i test di F1 restano verdi |
> | `front-transaction tx-import-report-set` | 7 rossi, 3 verdi | R1–R3 su `report-set-role-table`, R4 su `import-wizard-other-files-<id>`, F2-U2 (nuovo) su `report-set-timeline-history`, R5 e R6 su `gapfix-summary` |
> | `check-orphans` | pulito | — |
>
> Le scelte del test-author dove il contratto era aperto:
> - all'apertura nessun punto è attivo, e ogni gruppo ha il suo;
> - una card mostra solo le differenze diverse da zero;
> - card, selettori e «Anteprima» sono `<button>`; i motivi sono `<tr>`;
> - R5 e R6 assumono che le correzioni stiano in una pagina della tabella;
> - F2-U2 semina via API due transazioni col tag `danske_bank` e controlla inizio, fine e conteggio della storia.
>
> Da ricordare:
> - **`api sync`** serve perché `history_end` e `history_count` arrivino alla card: zod scarta le chiavi che non conosce.
> - **Documentazione sviluppatore**: `developer/frontend/components/features/import-wizard.md` descrive ancora `gapfix-proposal`.

> **Note implementazione — la cura di F2 (2026-10-02)**:
> - **Backend**:
>   - `BRIMSetPreview` riceve `history_end` e `history_count`;
>   - `preview_set` legge le transazioni col tag una volta sola (`_tagged_dates`) e ne ricava H0 (`_first_history_day`), le date del gap-fix (`_gap_fix_days`), la fine e il conteggio;
>   - `history_start` e `gap_fix_dates` restano, e delegano agli stessi helper;
>   - `api sync` nella corsia.
> - **`buildSetTimeline`**:
>   - barre in ordine di inizio, poi di fine, con `rows`;
>   - `gaps` per ruolo (`gapsBetween`, che tiene la fine più lontana raggiunta);
>   - storia da H0 a `max(H0, history_end)`, con `count`; l'intervallo comprende la fine della storia.
> - **`ReportSetCard.svelte`**:
>   - una DataTable per ruolo (`report-set-role-table`), con ordine fisso: inizio del periodo, poi nome in ordine naturale, e i file senza copertura in fondo;
>   - menu di riga anteprima/elimina e doppio clic; i non riconosciuti in `report-set-unrecognised`;
>   - linea del tempo: barre, buchi tratteggiati e storia, ognuno dentro un `Tooltip` (`showDelayMs` 200) col periodo e le righe o le transazioni; legenda; accanto a ogni riga il suo intervallo complessivo.
> - **Wizard**: il titolo `import-wizard-other-files-<id>` e `setGapFixProposals`, passata come `onSetSelected`.
> - **`ParseDetailModal.svelte`** (U3): chip degli esiti con emoji, tabella dei motivi, «Anteprima del combinato» (`onPreview`) e «Scarica».
> - **`GapFixStep.svelte`** (U4-B), riscritto:
>   - card per punto, ordinate per data;
>   - punto attivo per gruppo;
>   - confronto completo in `gapfix-point-details`: gli snippet `checkpointDetails` e `verificationDetails` riprendono il markup di C3;
>   - una DataTable per gruppo, coi comandi della revisione;
>   - il selettore è un componente nuovo, `GapFixToggle.svelte`, usato come cella `custom`.
> - **i18n**, 19 chiavi nuove in 4 lingue (`dev.py i18n add`):
>   - `importWizard.reportSet.{otherFiles, previewCombined}`;
>   - `importWizard.reportSet.column.{file, period, rows, reason}`;
>   - `importWizard.reportSet.timeline.{legendFile, legendHistory, legendGap, gapInfo, historyCount}`;
>   - `importWizard.reportSet.gapFix.{filterHint, pointOpening, pointGap, positions, corrections, notesCount, noProposals}` e `gapFix.column.point`.
>
>   Il francese usa «lot» e lo spagnolo «conjunto», come le chiavi esistenti.
> - **Primi verdi**:
>   - `services brim-report-sets`: `232 passed`;
>   - `front check`: il pavimento, 3 errori e 41 avvisi, nessuno nei file toccati;
>   - `front-transaction tx-unit`: `575 passed`, al primo giro.
>
> **Evidenze** (corsia 6156, un comando per volta):
>
> | Verifica | Esito |
> |---|---|
> | `services brim-report-sets` / `services brim-parse-pool` / `api brim` | `232` / `8` / `64 passed` |
> | `front-transaction tx-unit` | `575 passed` (i 55 rossi sono verdi) |
> | `front-utility core-unit` (coi gate della privacy e degli sink HTML) / `component-unit` / `onboarding-component-unit` | `2704` / `2182` / `409 passed` |
> | `front check` | il pavimento, 3 errori e 41 avvisi; nessuno nei file toccati |
> | `front build --debug` | ok |
> | E2E `tx-import-report-set` | `10 passed` (i 7 rossi sono verdi) |
> | E2E `tx-import-report-set-guide` / `tx-bulk-import-handoff` / `tx-import-file-selection` | `2` / `2` / `2 passed` |
> | E2E `tx-import-flow` / `tx-import-upload` / `tx-import-resolution` | `10` / `9` / `12 passed` |
> | E2E `tx-brim-import` / `tx-ca-contract` | rossi solo T1, CAC-011 e CAC-012, già noti (`tx-ca-contract`: 10 verdi) |
> | `dev.py lint`, `check-orphans`, `git diff --check` | verdi, pulito |
> | Privacy: righe aggiunte dal workstream contro i valori reali | 0 collisioni su 27 000 righe |
> | porta 6156 | libera |
>
> **⚠️ Fuori pista — la documentazione**: tre pagine descrivono ancora l'interfaccia di prima:
> - `developer/frontend/components/features/import-wizard.md`, le sezioni dei set scritte in D, coi testid di C2 e C3;
> - `developer/architecture/patterns/brim_plugin_guide.md`, i campi della preview;
> - `user/transactions/import/danske-bank.en.md`, i passi 2–3 e «Align with the bank».
>
> Il via di F non copriva la documentazione: ho chiesto al coordinatore se farla in questo checkpoint, col docs-writer, solo EN e senza stamp, o in un F2b.

> **Documentazione di F2 (2026-10-02)**, col permesso del coordinatore: «la doc va dentro questo checkpoint … solo in EN … niente stamp». L'ha fatta il docs-writer:
> - **`developer/frontend/components/features/import-wizard.md`**, solo le sezioni dei set scritte in D:
>   - la riga `select` del flusso;
>   - `buildSetTimeline` nella tabella degli helper;
>   - il passo `select`: titolo «Other files», tabelle per ruolo, `report-set-unrecognised`, linea del tempo, legenda e infobox;
>   - l'abbinamento: chip, tabella dei motivi, anteprima e scarica;
>   - `GapFixStep`: prop, card, punto attivo, `gapfix-point-details`, tabella con `GapFixToggle` e comandi; `gapfix-proposal` è sparito.
> - **`developer/architecture/patterns/brim_plugin_guide.md`**: la preview con `history_end` e `history_count`, letti insieme a H0 in una sola lettura, e una frase nel paragrafo su H0.
> - **`user/transactions/import/danske-bank.en.md`**: i passi 2–3, «Align with the bank» e la verifica di fine periodo. Le ancore restano tutte, compresa `{: #first-import-align-with-the-bank }`.
> - **Gate** del docs-writer:
>   - `mkdocs build` strict: exit 0, senza warning;
>   - `mkdocs check-links`: 81 link validi, coi soli 3 🟡 già noti; il rosso D28 non è uscito;
>   - `translate-validate`: nessun errore dalle modifiche, perché `danske-bank` non ha ancora traduzioni: tutta la pagina aspetta la sua prima traduzione;
>   - nessuno stamp.
> - Il docs-writer segnala piccole differenze fra il brief e il codice, e le ha documentate come sono nel codice: intestazioni «Quantity» e «Tags»; tabella del gap-fix ordinabile e paginata a 10; i conteggi di posizioni e note sulla card solo se diversi da zero.

### ⏸ Pausa (2026-10-02), chiesta dal developer tramite il coordinatore

- **Fatto**:
  - F1 committata (`e57d08b84` + `cf87bb2ff`);
  - la verifica d'ambiente di `tx-import-file-selection`: verde;
  - F2: rosso, cura, gate e documentazione, tutto verde (vedi le note sopra).
- **In corso**: niente. Nessun comando interrotto, nessun server acceso; le porte 6156 e 6166 sono libere (`lsof` vuoto).
- **Lo stato non committato**: HEAD `cf87bb2ff`, 23 path sporchi (21 M + 2 nuovi: `GapFixToggle.svelte` e `ReportSetCard.test.ts`), compreso questo piano. La `mkdocs build` non ha lasciato effetti collaterali tracciati.
- **Prossimo passo esatto**, alla ripresa («riprendi»):
  1. rileggere i diff delle tre pagine di documentazione (controllo mio), poi `git diff --check`;
  2. mandare al coordinatore `CHECKPOINT READY` F2, con:
     - i commit proposti: codice (`feat(import): report-set card, timeline and gap-fix review`), docs (`docs(import): report-set card and align-with-the-bank review`), journal;
     - la nota su `api sync`: i file generati sono ignorati, e all'integrazione il client va rigenerato;
     - le righe del CHANGELOG;
     - le esclusioni (log e `.testLog`);
  3. FROZEN fino agli SHA; poi il riallineamento della baseline col nuovo `dev_release2`, che fa il coordinatore. Lì `dev_release2` porta la correzione dei warning di svelte-check: quei file non li tocco.

### ▶️ Ripresa (2026-10-05), «Riprendi» del coordinatore

- **Stato alla ripresa**: lo stesso della pausa. HEAD `cf87bb2ff`, 23 path, `git diff --check` pulito, porta 6156 libera. La pulizia notturna di `/tmp` ha lasciato la corsia intatta (`app.db` c'è) e anche lo script del controllo privacy. Il client generato ha ancora `history_end`.
- **La mia revisione dei tre diff della documentazione**:
  - la guida dei plugin e la pagina sviluppatore del wizard corrispondono al codice. La frase «sets uploaded in this session are selected and open» era già in D, e il codice la conferma (`expandedSets` riceve i set della sessione);
  - nella pagina utente, l'esito `summarized` riguarda **movimenti** di ogni tipo, non solo trade: il plugin lo assegna anche alle righe di cassa. Ho corretto la parola a mano, «the trades summarised» → «the movements summarised». È l'unica modifica dopo il docs-writer.
- La guida dell'import (`onboarding.importGuide.steps.gapFix.description`) è generica e resta corretta: «keep or untick the corrections».
- **Gate della documentazione, rilanciati da me** dopo la correzione:
  - `mkdocs build` strict: exit 0, «Documentation built», senza warning;
  - `mkdocs check-links`: 81 link validi, 3 🟡 già noti, nessun D28;
  - nessun effetto collaterale sui file tracciati (sempre 23 path).
- **Privacy**, con la documentazione compresa: 0 collisioni su 27 172 righe aggiunte dal workstream.

### F2 — ✅ pronta per il checkpoint (2026-10-05)

> **F2 committata** dal developer (2026-10-05): `cdb8b3301` (codice), `5b35da6d4` (docs) e `5904ad20d` (journal). Blob uguali ai record, albero pulito.

## 13. Merge di baseline e validazione della revisione unita (2026-10-05)

- **Il merge**, fatto dal developer con lo script del coordinatore: `c59f9d7c2` «merge(l): dev_release2 into L before F2 integration».
  - Genitori `5904ad20d` (L) e `9b5291c25` (`dev_release2`); albero `c4d1cea6a`, come nella simulazione; merge-base `8f18416df`.
  - Porta K (Step 14 e 15), i giri di I, il pavimento di svelte-check a 0/0, il runner con l'attesa a 300 s, la PR #30 (`services/fx.py`) e la riparazione di `broker-sharing.spec.ts`: 54 file.

### 13.1 ✅ I file uniti da Git (2026-10-05)

- **i18n ×4**: controllo semantico a tre vie (base, mio, loro, risultato) di ogni chiave, con uno script fuori dal repo.
  - In tutte e quattro le lingue: **0 problemi**, nessuna chiave toccata da entrambe le parti.
  - Le mie 125 aggiunte e le 2 modifiche (`todoWarningConfirmMessage` e `select.description`) ci sono tutte; dall'altra parte una chiave aggiunta.
  - Dalla base manca una chiave, `dashboard.pnlCandlesHypothetical`: l'ha tolta l'altra parte, non io.
- **`frontend/e2e/brokers/brokers-detail.spec.ts`**: il mio unico blocco, 74 righe aggiunte in fondo a «Broker detail — import history upload» (il test C1 sul `batch_id`), è intatto e contiguo alla riga 1258 del risultato. I blocchi dell'altra parte (righe 9, 575 e 602–761 della base) non lo toccano.

### 13.2 ✅ Validazione, passi 1–4 (2026-10-05), corsia 6156, un comando per volta

| Passo | Comando | Esito |
|---|---|---|
| 1 | `api sync`; `front build --debug`; `mkdocs build` (strict) | ok; il client ha `history_end`; build ok; doc senza warning |
| 2 | `front check` | **0 errori, 0 avvisi**: il pavimento nuovo |
| 3 | `i18n audit` | 3543 chiavi in 4 lingue, nessuna traduzione mancante |
| 4 | `services brim-report-sets` / `brim-parse-pool` / `api brim` | `232` / `8` / `64 passed` |
| 4 | `front-transaction tx-unit` / `front-utility core-unit` (coi gate XSS di K) / `component-unit` / `onboarding-component-unit` | `575` / `2704` / `2203` / `409 passed` (`component-unit` cresce coi test arrivati dal merge) |

> **⚠️ Fuori pista — `i18n audit`**: fra i «❌ Likely Unused» c'è una mia chiave, `importWizard.reportSet.gapFix.stepTitle`. È un falso positivo, e non viene dal merge:
> - lo stepper la usa per costruzione: `STEP_DEFS` ha `{id: 'gapFix', titleKey: 'reportSet.gapFix.stepTitle'}` e rende `$t(\`importWizard.${step.titleKey}\`)`;
> - le chiavi sorelle (`importWizard.step1Title` … `stepDuplicatesTitle`) finiscono in «🔵 Not Verified» per lo stesso schema; la mia, più annidata, non la riconosce l'euristica;
> - lo strumento dell'audit non è cambiato nel merge (sono cambiati solo file del runner), e la riga 143 è la stessa da C3.

> **Decisione del developer** (2026-10-05), riportata dal coordinatore: il plugin Danske esce come **🔬 Alpha**, non 🧪 Beta. Testuale: «beta è quando è stato fatto dai report trovati online e anonimi, qui abbiamo il suo supporto».
> - Nello stesso checkpoint, dopo la validazione, va un commit `docs(import): Danske Bank is alpha` con:
>   - `providers_list.md:30`;
>   - la cella di `index.{en,it,fr,es}.md` (riga 276 in EN, 274 nelle altre), a mano in 4 lingue, poi `translate-stamp` di `index.en.md`;
>   - il riquadro e la frase di `danske-bank.en.md`.
> - Verifiche fatte prima: il plugin e la classe base non hanno un campo di maturità (lo stato vive solo nella documentazione), e nessun test legge queste celle. La card dell'indice non ha badge. La legenda di `providers_list.md` ha già 🔬 Alpha. Nessuna pagina d'import usa ancora un riquadro Alpha, quindi resta `!!! info`.
> - Il CHANGELOG lo sistema il coordinatore all'integrazione, fuori dalla sezione 🧪 Beta.

- **`check-orphans`** (passo 6): pulito. 96 spec E2E, 281 file Vitest e 227 file backend, tutti raggiungibili da `all`.

> **⚠️ Fuori pista — i file rimasti nella corsia prima degli E2E** (passo 5, in attesa):
> - `api brim` gira su un DB senza broker: crea 46 broker (id 1–46) e lascia 23 file BRIM su 16 di loro (id 9–46).
> - Ogni E2E ripopola senza `--clean` (8 broker finti) e crea i suoi broker dall'id 9: eredita quei file. R1 e R7 controllano che manchi il titolo «Other files», e falliscono sulla loro precondizione; `tx-import-file-selection` è lo stesso caso del 02/10.
> - Il 02/10 `file-selection` era passato solo perché le spec precedenti avevano cancellato i broker 9 e 10 con `force=true`, e i loro file con loro.
> - Ho chiesto al coordinatore il permesso per un `test db populate --force --clean` sulla mia data dir prima del giro E2E.
> - **Permesso del coordinatore**: «Sì: `test db populate --force --clean`, una volta, solo su `/private/tmp/librefolio-r2-l`, prima del giro E2E». La causa va nel suo backlog di fine round, accanto al conteggio di `clean_data_dirs` e al riuso degli id senza AUTOINCREMENT.
> - **Prima**:
>   - `broker_reports/uploaded`: 24 cartelle di broker, 26 file;
>   - `parsed`: 24 cartelle, 18 file;
>   - `failed`: 24 cartelle, 2 file;
>   - in tutto 46 file, cioè i 23 report di `api brim` e i loro metadati; più 61 file in `custom-uploads`.
> - **Il comando**: `test --test-port 6156 --data-dir /tmp/librefolio-r2-l db populate --force --clean`, exit 0, sulla corsia `/private/tmp/librefolio-r2-l`.
> - **Dopo**: `uploaded`, `parsed` e `failed` hanno 0 cartelle e 0 file. `custom-uploads` torna a 61 file: li svuota `--clean` e li ricrea il populate.
> - Ordine del giro E2E: prima le mie spec, poi la regressione, e in fondo i rossi accettati (T1, CAC-011/012), che lasciano file su disco.

### 13.3 ✅ Validazione, passo 5: gli E2E (2026-10-05), dopo il `--clean`, un comando per volta

| Spec (azione del runner) | Esito |
|---|---|
| `tx-import-report-set` / `-guide` / `tx-bulk-import-handoff` / `tx-import-file-selection` | `10` / `2` / `2` / `2 passed` |
| `tx-import-upload` / `tx-import-flow` / `tx-import-resolution` | `9` / `10` / `12 passed` |
| `tx-wac-bulk` / `tx-bulk-diagnostics` / `tx-bulk-operations` / `tx-paired-edit` | `10` / `2` / `10` / `4 passed` |
| `front-utility files` / `settings` / `onboarding-tour` | `22` / `45` / `10 passed` |
| `front-broker detail` (modificata da entrambe le parti) | `33 passed`: il rosso di I alla riga 713 è sparito col merge |
| `tx-brim-import` | rosso T1, già accettato; «7 did not run» come in F1 e F2, perché la suite è seriale |
| `tx-ca-contract` | `10 passed`; rossi CAC-011 e CAC-012, già accettati |

Nessun test saltato né instabile. Albero: solo il piano modificato. Porta 6156 libera.

### 13.4 ✅ Danske Bank in 🔬 Alpha (2026-10-05)

- **Modifiche**, 7 righe in 6 file:
  - `providers_list.md:30`, lo stato diventa `🔬 Alpha`; la legenda alla riga 41 lo ha già;
  - la cella della riga Danske in `index.{en,it,fr,es}.md`, `🧪 Beta` → `🔬 Alpha`, a mano nelle 4 lingue: la cella è uguale in tutte;
  - `danske-bank.en.md`: `!!! info "Alpha"` e «This importer is in **Alpha**»; il resto della frase resta.
- Non rimane nessun «Beta» riferito a Danske nella documentazione.
- `mkdocs translate-stamp --file user/transactions/import/index.en.md`, prima a secco: in `.translate-hashes.json` cambia solo la voce dell'indice d'import (l'md5 e tre `stamped_at`), come in D.
- **Gate della documentazione** (passo 6):
  - `mkdocs build` strict: exit 0, senza warning;
  - `mkdocs check-links`: 81 link validi, i 3 🟡 noti, e **1 rosso non mio**: `user/assets/detail/chart/#rolling-return`. L'ancora c'è in `chart.en.md:22` ma manca in it/fr/es; il link sta in `frontend/src/routes/(app)/assets/[id]/+page.svelte:3006`.
    - È identico su `dev_release2` (`9b5291c25`), non c'era nel mio ramo prima del merge, e il mio diff verso `dev_release2` non lo tocca.
    - Probabilmente è il rosso D28 che il coordinatore aveva dichiarato noto e accettato il 02/10. Lo segnalo, e non lo correggo: i file non sono miei.

### 13.5 ⏳ Prossimo passo: la scelta del plugin di un set

Richiesta del developer tramite il coordinatore: che il plugin di un set non lo scelga l'utente è «abbastanza grave».
- Dopo il checkpoint della validazione: un'analisi senza codice, da discutere col developer nella chat di L.
- Poi due righe di decisione al coordinatore, per l'ordine delle integrazioni e per il CHANGELOG.
- La bozza dell'analisi è nella cartella di sessione, fuori dal repo.

> **Commit della validazione** (developer, 2026-10-05): `adf3b8cd7` «docs(import): Danske Bank is alpha» e `8c6853281` journal.
> - **Danske è integrato**: `dev_release2` è avanzato a `8c6853281`, poi il commit `c8daff33f` del coordinatore con le righe del CHANGELOG. Il ramo di L resta un commit indietro, ed è normale.
> - Il D28 (`#rolling-return` in it/fr/es) è il rosso accettato, confermato dal coordinatore.

## 14. Passo G — la scelta del plugin di un set (2026-10-05)

**Base**: `8c6853281`, corsia 6156. **Via del coordinatore**: «Via al passo G sul tuo ramo… prima il piano nel journal… poi i test rossi col test-author; poi l'implementazione e il checkpoint. G deve entrare prima del taglio della release.»

> **⚠️ Fuori pista**: prima di cominciare ho lanciato per riflesso un `git fetch -q origin`. Aggiorna solo i riferimenti remoti, non il ramo né i file, ma non è un comando di sola lettura, quindi non va fatto: non lo ripeto.

### G.0 Decisioni del developer (testuali, nella chat di L, 2026-10-05)

- **La richiesta** (dal coordinatore): che nel caso del set il plugin non lo scelga l'utente sembra al developer «abbastanza grave».
- **Il perimetro**: «A + B + C: tutto, con D dietro (Consigliato)». Le opzioni erano disegnate nei bozzetti mostrati al developer, salvati nella cartella di sessione:
  - A = «Letto come» sulla card;
  - B = dal menu di un file, «Leggi da solo con…» oppure «Togli dal set»;
  - C = l'avviso;
  - D = `exclude_file_ids`.
- **I tempi**: «Dopo l'integrazione di Danske, ma prima del taglio della release (Consigliato)».
- **La memoria**: «la scelta se è un set o meno, è nella fase di import, quindi finchè siamo solo in "upload" ci sta non salvare nulla, quando poi si passa al "parsed" il gioco è fatto e mi aspetto che il set sia salvato e ricordato, posso accettare che venga modificato in seguito, ma la memoria dovrebbe rimanere».
  - Il bozzetto della memoria, «Sì, è questo il comportamento (Consigliato)»: dopo l'analisi il set ricorda i suoi file e il suo plugin, e un file analizzato da solo ricorda il suo plugin. Riaprendo, la memoria conta più del rilevamento; si cambia con gli stessi comandi, e la nuova scelta diventa la memoria alla prossima analisi.
  - Non serve un campo nuovo: la memoria si ricava da quello che il server salva già all'analisi.

### G.1 Stato verificato (2026-10-05)

- `setPluginFor(file, plugins, override?)` sa già usare un override:
  - verso un plugin a set, il file entra in quel set;
  - verso un altro plugin, diventa file singolo.

  I test lo coprono già. Però **nessun punto dell'interfaccia** imposta l'override di un membro: la colonna «Plugin» esiste solo nella tabella dei file singoli. Anche `pickBestPlugin` mette sui membri il plugin del set.
- Il backend non conosce la scelta: `BRIMSetRequest` contiene solo `{broker_id, plugin_code, batch_id}`, e `collect_members` prende tutti gli originali del caricamento che il plugin legge.
- Il rilevamento sui campioni sintetici dà questo: l'XLSX dei titoli lo legge solo `broker_danske_bank`; il CSV di cassa lo leggono `broker_danske_bank` e `broker_generic_csv`. Danske ha due ruoli, `custody` e `cash`, entrambi `required` e `multiple`.
- Quello che il server salva già:
  - per un file combinato: `kind`, `batch_id`, `derived_from` (`file_id`, `deleted`), `status`, `processed_at`, `parsed_plugin_code`, `uploaded_at`;
  - per un originale: `combined_into`, `status`, `processed_at`, `parsed_plugin_code`, `compatible_plugins`, `uploaded_at`.
- Anche FilesTable (la pagina File e i report del broker) chiede la preview dei set, per la badge «Incompleto», con la stessa richiesta del wizard.

### G.2 Contratto

**D · backend** (`schemas/brim.py`, `services/brim_report_sets.py`, `api/v1/brokers.py`):
- `BRIMSetRequest.exclude_file_ids: List[str] = []`: il default vuoto lo rende compatibile, e il modello resta strict.
- `collect_members(..., exclude_file_ids=())`: toglie gli esclusi dai membri. Preview e combine lo usano tutti e due.
- Un id escluso che non è un originale di quel broker e di quel caricamento dà **422** con `BRIMSetExcludeUnknown` (codice `exclude_unknown`).
- Se non resta nessun membro, vale il 404 di oggi (`members_not_found`).
- Le risposte non cambiano. Il riuso del combinato resta per insieme esatto di membri (`members_key`).
- Poi `api sync`; all'integrazione il client va rigenerato.

**Logica pura** (`importReportSets.ts`):
- `setPluginFor`: un override `''` vuol dire «file singolo senza plugin» e restituisce `null`. `null` o `undefined` restano «nessuna scelta».
- `rememberedChoices(files, plugins) → Map<file_id, override>`: la memoria dopo l'analisi. Per ogni originale con un caricamento si considerano tre eventi, contando solo i combinati con `status === 'parsed'`:
  - **E1, membro**: un combinato analizzato dello stesso broker e caricamento elenca il file fra i `derived_from` non cancellati. Il valore è il plugin del combinato, cioè il suo `parsed_plugin_code`; l'istante è il `processed_at` del combinato;
  - **E2, letto da solo**: il file ha `status === 'parsed'` con un `parsed_plugin_code` che non è un plugin a set. Il valore è quel plugin; l'istante è il `processed_at` del file;
  - **E3, lasciato fuori**: un combinato analizzato dello stesso caricamento non lo elenca, il file è compatibile col suo plugin ed esisteva già quando il combinato è nato (`uploaded_at` del file ≤ `uploaded_at` del combinato). Il valore è `''`; l'istante è il `processed_at` del combinato.

  Il risultato:
  - se l'E1 più recente è più recente di ogni E2 ed E3, il file sta nel set di quel plugin;
  - altrimenti, se c'è un E2 più recente dell'ultimo E1, il file resta singolo con quel plugin. Un E2 e un E3 della stessa analisi non si contraddicono: tutti e due dicono «fuori dal set»;
  - altrimenti, se c'è un E3, il valore è `''`;
  - altrimenti non c'è memoria, e vale il rilevamento.
- `setPluginChoices(set, plugins)`: i plugin a set compatibili con **tutti** i membri, primo quello del set.
- `readAlonePlugins(file, plugins, brokerDefault?)`: i plugin compatibili che non sono a set, con prima il predefinito del broker se c'è fra questi.
- `otherSetPlugins(file, setPluginCode, plugins)`: gli altri plugin a set compatibili col file (C2).
- `defaultPluginNote(set, brokerDefault, plugins)`: il predefinito del broker, se è diverso dal plugin del set e compatibile con almeno un membro; altrimenti `null` (C1).
- `setRequest(set, files)`: `{broker_id, plugin_code, batch_id, exclude_file_ids}`. Gli esclusi sono gli originali dello stesso broker e caricamento, compatibili col plugin, non `failed` e non membri del set. La usano il wizard e FilesTable.
- `combinedFileForSet(set, files)`: in più chiede che gli id non cancellati di `derived_from` coincidano coi membri del set. Così un set con un membro tolto non risulta «già analizzato» a causa di un combinato vecchio, e un originale cancellato dopo non cambia nulla, come in v5.3.
- `setsOfFiles(files, plugins)`: per ogni broker applica `rememberedChoices`, e le badge seguono la memoria.

**A, B, C · `ReportSetCard.svelte`**:
- Prop nuove:
  - `plugins: SetPluginInfo[]`, il catalogo;
  - `brokerDefaultPlugin: string | null`;
  - `onReadAs(code: string | null)`;
  - `onReadAlone(fileId, code)`;
  - `onRemoveFromSet(fileId)`.
- **A**: nell'intestazione, `<select data-testid="report-set-read-as">` col valore del plugin del set. Un'opzione per ogni plugin di `setPluginChoices`, quello del set marcato «rilevato», più `value=""` per «Leggi i file uno per uno». Il cambio chiama `onReadAs(code)`, oppure `onReadAs(null)` per `""`.
- **B**: nel menu di riga della tabella del ruolo:
  - un'azione `read-alone-<code>` per ogni plugin di `readAlonePlugins`, visibile solo sulle righe dei file che quel plugin legge; produce `context-menu-action-read-alone-<code>` e chiama `onReadAlone(fileId, code)`;
  - `remove-from-set`, che produce `context-menu-action-remove-from-set` e chiama `onRemoveFromSet(fileId)`.

  Anteprima ed Elimina restano.
- **C1**: `report-set-default-note` con `data-default-plugin`, quando `defaultPluginNote` non è `null`.
- **C2**: un `report-set-also-recognised` per file, con `data-file-id` e `data-plugins`, l'elenco dei codici separati da virgola.

**Wizard** (`ImportWizardModal.svelte`):
- **Override efficaci**: la memoria (`rememberedChoices` sui file del broker) più le scelte della sessione (`filePluginOverrides`); vincono quelle della sessione. Li usano `brokerSetGroups` e `pickBestPlugin`. Le scelte della sessione si azzerano ancora alla chiusura, come oggi.
- **`readSetAs(set, code)`**:
  - con un plugin a set, l'override va a ogni membro, e i membri selezionati prendono quel plugin;
  - con `null`, ogni membro prende il suo miglior plugin non a set, oppure `''`. I membri con `''` si deselezionano, gli altri restano selezionati col nuovo plugin.
- **`readFileAlone(fileId, code)`**: l'override va al file, che resta selezionato se lo era.
- **`removeFileFromSet(fileId)`**: override `''`, e il file si deseleziona.
- **Rientro nel set**: si sceglie il plugin del set nella colonna «Plugin» dei file singoli, con `updateFilePlugin` di oggi.
- **Preview**: si salvano per chiave del set e per insieme dei membri. Dopo ogni cambio si rileggono quelle cambiate, con `setRequest`.
- **Combine**: la richiesta porta gli `exclude_file_ids` dell'unità d'analisi.
- **FilesTable**: chiede le preview con `setRequest`.

**Memoria non mostrata con un testo nuovo** (proposta mia): «come all'ultima analisi» si capisce già dallo stato «Analizzato» del file e dal plugin preselezionato. Nella tabella dei singoli non aggiungo un'etichetta, per non toccare `ImportPluginSelect`, che è condiviso.

**i18n** (via `dev.py i18n add`, 4 lingue): `importWizard.reportSet.{readAs, readAsOneByOne, detected, readAloneWith, removeFromSet, defaultPluginNote, alsoRecognisedBy}`.

**Documentazione** (docs-writer, solo EN, senza stamp): la pagina utente Danske (come cambiare la lettura di un set, e la memoria); `import-wizard.md`; `brim_plugin_guide.md` (`exclude_file_ids` e la regola della memoria).

**Test** (test-author, rossi prima, solo dati inventati, corsia 6156):
- backend: `test_brim_report_sets.py` (`services brim-report-sets`) e `test_brim_api.py` (`api brim`);
- Vitest: `importReportSets.test.ts` e `ReportSetCard.test.ts` (`tx-unit`);
- E2E `tx-import-report-set.spec.ts`: G-A, G-B, G-C e la memoria. Per la memoria serve un terzo estratto conto sintetico, generato in una cartella temporanea.

**Gate**:
- backend BRIM, i Vitest e `front check` a 0/0;
- `front build --debug`, gli E2E d'import, `check-orphans`;
- `mkdocs build` strict e `check-links` (il D28 è accettato);
- privacy; porta libera.

**Definition of done**: tutti i test rossi diventano verdi, i gate sono verdi, e il checkpoint contiene le righe del CHANGELOG di G.

### G.3 ✅ Il rosso (test-author) — 2026-10-05

> **Note implementazione — il rosso di G (2026-10-05)**, test-author, corsia 6156, solo dati inventati, nessun file di prodotto toccato:
>
> | Comando | Esito | Rosso |
> |---|---|---|
> | `services brim-report-sets` | 23 rossi, 232 verdi | i 23 test nuovi di D |
> | `front-transaction tx-unit` | 42 rossi, 580 verdi | `importReportSets` 30, `ReportSetCard` 12 |
> | `front-transaction tx-import-report-set` | 7 rossi, 9 verdi | i 6 test nuovi di G, più R1 sulla sola asserzione del body del combine (`exclude_file_ids: []`) |
> | `api brim` (lanciato per ultimo) | 8 rossi, 64 verdi | gli 8 test nuovi (RS-G01…G04) |
> | `check-orphans` | pulito | — |
>
> **⚠️ Fuori pista — cosa ha trovato il test-author**:
> - **Il CSV generico** si dichiara compatibile con qualsiasi `.csv` che abbia un'intestazione (`can_parse`), ma in analisi pretende `date` e `type`. Quindi l'estratto di cassa Danske non lo può leggere, e «Leggi da solo con CSV generico» fallirebbe sempre. Per il test «memoria, da solo» il test-author ha scritto un estratto sintetico con in più le colonne `date;type;amount;currency`, che Danske ignora.
> - **Un originale con analisi fallita** (`failed`): `collect_members` lo scarta (regola A2), mentre il raggruppamento del frontend lo rimetterebbe nel set, e la card mostrerebbe un file che la preview non legge.
> - In più non sono coperti dagli E2E la scelta di un altro plugin a set in A (c'è solo Danske) e `setRequest` usata da FilesTable (coperta solo dai test unitari).
>
> **Decisioni del developer** (testuali, chat di L, 2026-10-05):
> - «credo che il problema sia di CSV generico che per ora guarda solo l'estenzione, dovrebbe guardare le colonne e vedere se tutte le obbligatorie, in almeno una delle lingue, ci sono»;
> - sulla proposta (`can_parse` vero solo se l'intestazione ha `date` e `type`, coi sinonimi multilingue di `HEADER_MAPPINGS`): «Sì, così, dentro G (Consigliato)».
>
> **Il contratto cambia così**:
> - `broker_generic_csv.can_parse` = estensione `.csv` **e** un'intestazione in cui `_detect_columns` trova `date` e `type`. Il resto del plugin non cambia.
> - Sul frontend un originale `failed` non entra mai in un set: `setPluginFor` restituisce `null` anche con un override, come `collect_members` sul server (regola A2).
> - Gli E2E che contavano sul generico «largo» vanno adattati:
>   - R1 (A18, il broker col generico come predefinito), G-A, G-B e G-C usano l'estratto sintetico a due formati;
>   - sul vero estratto Danske, «Leggi da solo» non offre più nulla e resta solo «Togli dal set».
> - **Superfici nuove**, segnalate al coordinatore con la richiesta di controllare i conflitti: `broker_generic_csv.py`, `test_brim_providers.py` e le pagine `generic-csv.*.md` (solo EN, debito di traduzione).

> **Coordinatore** (2026-10-05): nessun altro ramo tocca `broker_generic_csv.py`, `test_brim_providers.py` o `generic-csv.*.md`; sono superfici di G. Due avvertenze:
> - nei gate di G va anche `external brim-providers`;
> - nel checkpoint, una riga su cosa vede un utente con un CSV senza `date`/`type` che prima proponeva il generico.
>
> **Note implementazione — il rosso emendato (2026-10-05)**, test-author:
>
> | Comando | Esito | Rosso |
> |---|---|---|
> | `external brim-providers` | 10 rossi, 597 verdi, 2 saltati (già prima) | i 10 test nuovi di `TestGenericCSVDeclaresOnlyWhatItReads` |
> | `front-transaction tx-unit` | 45 rossi, 581 verdi | i 3 nuovi sul file `failed` più i 42 del primo giro |
> | `front-transaction tx-import-report-set` | 8 rossi, 10 verdi | R1 (solo il body del combine) e 7 test G; A18, ora su un estratto a due formati, è verde |
> | `check-orphans` | pulito | — |
>
> - **Spostamenti negli E2E**: A18, G-A, G-B, G-C e G-no-memory usano ora l'estratto sintetico «a due formati», che Danske e il CSV generico leggono tutti e due. Ogni caricamento ne verifica i `compatible_plugins`.
>   - G-real (nuovo) controlla l'estratto vero: sulla riga di cassa non c'è nessun «Leggi da solo», c'è «Togli dal set».
>   - R1 gira sui campioni veri, con un broker senza plugin predefinito.
> - **⚠️ Fuori pista**:
>   - `test_generic_can_parse_any_csv` chiedeva al generico di accettare **ogni** campione CSV, cioè il contrario della decisione del developer. Il test-author l'ha rinominato in `test_generic_can_parse_every_csv_sample_with_date_and_type` e ne ha tenuto la parte che resta vera; la parte rovesciata è il nuovo test rosso sul corpus dei campioni. È una conseguenza diretta della decisione.
>   - L'helper `_upload_main_set_and_third_cash` di `test_brim_api.py` (riga 1859) dà per scontato che il terzo estratto sintetico sia compatibile anche col generico, e dopo la correzione cadrà prima delle sue verifiche: va riparato dal test-author.
>   - Nella corsia restano file dei test API sui broker 11–54: per i gate E2E servirà ancora un `--clean`, autorizzato dal coordinatore.
>   - Dopo la correzione, un'analisi col generico di un CSV senza `date`/`type` risponde «Plugin 'broker_generic_csv' cannot parse file …» invece di «Required column 'date' not found». È ancora un 400, il file va ancora in `failed`, e nessun test controlla il testo.

### G.4 ✅ La cura — 2026-10-05

> **Note implementazione — la cura di G (2026-10-05)**:
> - **D** (backend):
>   - `BRIMSetRequest.exclude_file_ids` e `BRIMSetExcludeUnknown` (422, `exclude_unknown`);
>   - `collect_members` prima raccoglie gli originali del broker e del caricamento, poi rifiuta gli id estranei, poi toglie gli esclusi;
>   - `preview_set` e `combine_set` passano l'elenco; gli endpoint lo leggono dalla richiesta;
>   - `api sync`.
> - **Il CSV generico**: `can_parse` = estensione `.csv` **e** un'intestazione in cui `_detect_columns` trova `date` e `type`.
> - **Logica pura** (`importReportSets.ts`):
>   - `setPluginFor`: un originale `failed` non entra mai in un set; `''` = singolo senza plugin;
>   - `combinedFileForSet` confronta i membri vivi;
>   - `rememberedChoices` applica la regola E1/E2/E3, con gli istanti letti con `Date.parse`, e in parità vince «letto da solo»;
>   - poi `setPluginChoices`, `readAlonePlugins`, `otherSetPlugins`, `defaultPluginNote`, `setRequest`; `setsOfFiles` usa la memoria.
> - **`ReportSetCard.svelte`**:
>   - la select «Letto come» nell'intestazione, col plugin rilevato marcato;
>   - le azioni di riga `read-alone-<codice>`, visibili per file, e `remove-from-set`;
>   - le note C1 e C2 nel corpo.
> - **Wizard**:
>   - `rememberedByBroker` e `choicesFor`, dove la sessione conta più della memoria;
>   - `pickBestPlugin` parte dalla scelta in vigore;
>   - `readSetAs`, `readFileAlone` e `removeFileFromSet`;
>   - la cache delle preview tiene anche i membri (`memberSignature`), e `refreshChangedSetPreviews` rilegge quelle cambiate, anche dopo un'eliminazione;
>   - preview e combine mandano `setRequest` ed `excludeFileIds`.
> - **FilesTable**: la preview manda `setRequest`.
> - **i18n**: 7 chiavi nuove in 4 lingue (`importWizard.reportSet.{readAs, readAsOneByOne, detected, readAloneWith, removeFromSet, defaultPluginNote, alsoRecognisedBy}`). L'argomento di C1 si chiama `{defaultPlugin}`, perché `default` è un nome a rischio in ICU.
>
> **Primi verdi**:
>
> | Verifica | Esito |
> |---|---|
> | `services brim-report-sets` | `255 passed` (i 23 rossi di D sono verdi) |
> | `external brim-providers` | `595 passed`, 1 saltato. I casi sono 13 in meno perché il generico rivendica meno campioni: per esempio la matrice Windows-1252 scende a 22 casi, di cui 4 col generico, e il salto Degiro×generico non c'è più. Nessun test perso |
> | `front check` | **0/0**. Un errore di tipo, il predicato `code is string` negato in un `filter`, corretto con un helper booleano |
> | `front-transaction tx-unit` | `626 passed` (i 45 rossi sono verdi) |
> | `front-utility core-unit` / `component-unit` / `onboarding-component-unit` | `2704` / `2203` / `409 passed` |
> | `front build --debug` | ok |
>
> **`--clean` prima degli E2E di G**, autorizzato dal coordinatore («una volta, solo su `/private/tmp/librefolio-r2-l`»):
> - **prima**: la cartella `broker_reports` non c'era proprio, quindi 0 file. La causa non è chiara: non sono i fixture delle suite di servizio, che lavorano in `tmp_path`;
> - `test … db populate --force --clean`: exit 0;
> - **dopo**: `uploaded`, `parsed` e `failed` esistono, vuote, con 0 file.
>
> **E2E di G, primo giro** (in corso): `tx-import-report-set`, 4 rossi e 14 verdi.
> - **R3, difetto mio**: «Carica il file mancante» rilegge la preview passando l'oggetto del set di **prima** del caricamento. Con `setRequest`, il file appena caricato risulta un originale del caricamento che non è membro, quindi finisce fra gli esclusi, e il set resta incompleto.
>   - Correzione: dopo il caricamento si rilegge la preview del set **attuale**, cioè quello con la stessa chiave in `allReportSets`.
>   - Non la applico finché il giro E2E è in corso: un sorgente cambiato farebbe ricostruire il frontend al prossimo avvio del server.
> - **G-memory (set), G-memory (alone) e G-no-memory**, difetto di test: `reopenOnStep2` clicca il pulsante Import della barra mentre l'editor (`tx-bulk-modal`), rimasto aperto dopo la chiusura del wizard, intercetta il clic. Il pulsante della pagina apre l'editor col wizard dentro, e chiudere il wizard lascia l'editor vuoto aperto.
>   - Riparazione per il test-author: riaprire il wizard dall'editor (`tx-bulk-import`), oppure chiudere prima l'editor (`closeEditorWithoutSaving`).
>   - In più, la premessa di `test_brim_api.py:1859` va adattata al generico più stretto: il terzo estratto è compatibile con `[DANSKE_CODE]`, cioè come il campione di cassa.
>
> **E2E di G, primo giro concluso** (corsia 6156, un comando per volta):
> - **verdi**:
>   - `-guide` 2, `tx-bulk-import-handoff` 2, `tx-import-file-selection` 2, `tx-import-upload` 9, `tx-import-flow` 10, `tx-import-resolution` 12;
>   - `tx-import-matching` 6, `tx-import-asset-inspector` 5, `tx-import-duplicate-precedence` 6;
>   - `tx-wac-bulk` 10, `tx-bulk-diagnostics` 2, `tx-bulk-operations` 10, `tx-paired-edit` 4;
>   - `front-utility files` 22, `select` 17, `image-crop` 42, `onboarding-tour` 10;
>   - `front-broker detail` 33;
> - rossi accettati: T1 e CAC-011/012;
> - `tx-import-report-set`: i 4 rossi analizzati sopra. **R3 è corretto** (si rilegge la preview del set attuale); `front check` resta a 0/0.
>
> **⚠️ Fuori pista — `front-utility files-uploader`, 6/6 rossi.** Verdetto della test-triage: **assumption** del test, che non viene da G.
> - La spec ha un elenco chiuso di GET permessi e riceve `GET /api/v1/settings/onboarding`, l'avvio dell'onboarding (`onboardingApi.ts:81`); la pagina File non si apre mai.
> - La spec è cambiata l'ultima volta in `ef722b552`; le modifiche di G non toccano onboarding, layout né la spec.
> - L'ho segnalato al coordinatore: non è un mio file.
>
> **⚠️ Fuori pista — la corsia dopo il giro**:
> - CAC ha lasciato file `ca-*` sui broker 9–21, gli id che `tx-import-report-set` riusa;
> - ogni populate senza `--clean` aggiunge un'altra copia dei campioni ai broker finti 1–7 (25 copie ciascuno).
>
> Ho chiesto al coordinatore un `--clean` prima di ogni giro E2E di G.

> **Decisioni del coordinatore (2026-10-05)**:
> - **`--clean` prima di ogni giro E2E di G**: permesso fino alla fine di G, solo sulla corsia, con il comando esatto `… test --test-port 6156 --data-dir /private/tmp/librefolio-r2-l db populate --force --clean`, un comando alla volta e senza backend sulla 6156.
> - **`files-uploader` assegnata a L**, solo test, in un commit separato `test(e2e): …`. La spec resta severa sulle chiamate della pagina File; la GET dell'onboarding si dichiara come contratto dell'app, con una risposta sintetica in cui le guide risultano completate. Non si toccano `onboardingApi.ts` né il layout.
> - I file `ca-*` di CAC e le copie dei campioni: backlog di fine round del coordinatore.

> **Note implementazione — la riparazione dei test (2026-10-05)**:
> - **La corsia**: `--clean` autorizzato, da 426 file a 0.
> - **Il test-author**:
>   - `tx-import-report-set`: `reopenOnStep2` riapre il wizard dall'editor (`tx-bulk-import`); i tre G-memory sono verdi;
>   - `test_brim_api.py:1859`: la premessa segue il generico più stretto;
>   - `files-uploader.spec.ts`: `GET /api/v1/settings/onboarding` è nell'elenco come contratto dell'app, con una risposta sintetica (tutte le guide completate) validata sullo schema.
> - **Esiti**:
>
> | Verifica | Esito |
> |---|---|
> | `tx-import-report-set` | `18 passed` a 1 worker e a 4 worker |
> | `front-utility files-uploader` | `6 passed` |
> | `api brim` | `72 passed` |
> | `check-orphans` | pulito |
>
> - **⚠️ Fuori pista — un possibile difetto fuori da G**, visto dal test-author: `TransactionBulkModal.svelte` (~483) mette `initialOpsKey = ''` quando i tipi di transazione non sono ancora in cache, e allora un editor vuoto chiede «Scartare le modifiche?». Non riprodotto dalla pagina Transazioni. Va al backlog del coordinatore.

> **Note implementazione — la documentazione di G (2026-10-05)**, dal docs-writer, solo EN, senza stamp:
> - `user/transactions/import/danske-bank.en.md`: la sezione nuova «🔀 How the set is read» (`#how-the-set-is-read`): «Read as», il menu di riga (Read alone with / Remove from the set), le due note, la memoria dopo l'analisi; più una frase sui badge.
> - `developer/frontend/components/features/import-wizard.md`: la tabella degli helper, le sezioni nuove `#set-read-as` e `#set-memory` (E1/E2/E3 e la precedenza), il combine con `excludeFileIds`, i badge con la memoria.
> - `developer/architecture/patterns/brim_plugin_guide.md`: un plugin non rivendica un file che non sa leggere (la regola del generico); `exclude_file_ids`, 404 `members_not_found`, 422 `exclude_unknown`.
> - `user/transactions/import/generic-csv.en.md`: due frasi su quando il CSV generico si propone. La pagina ha traduzioni: è **debito di traduzione**.
> - `providers_list.md`: non toccato. «Accepts any CSV matching the Generic CSV spec» è già condizionale.
> - **Gate**: `mkdocs build` strict ok; `check-links` 81 validi e il solo rosso D28 accettato; `translate-validate` senza problemi strutturali su generic-csv (un'ancora interna tolta perché i titoli tradotti cambiano slug).
> - **Dal codice, cose che la doc ora dice giuste**:
>   - un file tolto dal set si rimette nel set spuntandolo e scegliendo il plugin del set;
>   - le due note si vedono solo a scheda aperta;
>   - in parità di istante, nella memoria vince «letto da solo».
> - **⚠️ Fuori pista — deriva fuori da G, per il backlog**:
>   - il ripiego `auto` → CSV generico (`brokers.py:894`) fallisce sempre, sia prima sia dopo G;
>   - la mappatura manuale delle colonne è descritta in `generic-csv.en.md:3,15-17`, `how-to.en.md:84` e `index.en.md:288`, ma non esiste: le colonne si riconoscono dal nome;
>   - un file che nessun plugin riconosce può ricevere a mano un plugin di set: il wizard lo mette nel set, il server no. Viene da C2, non da G.
> - **⚠️ Fuori pista — il messaggio d'errore del CSV generico**, che viene da G. Forzare il generico su un CSV senza `date` o `type` prima dava «Parse error: Required column 'date' not found in CSV header»; ora la guardia di `parse_file` (`brim_provider.py:1431`) risponde «Plugin 'broker_generic_csv' cannot parse file '…'». L'esito è lo stesso, il file finisce in `failed`, ma il messaggio non dice più quale colonna manca. Domanda al developer.

### G.5 ✅ Il motivo del rifiuto (2026-10-05)

**Decisione del developer** (ask_user, testuale): «Correggi dentro G con il metodo opzionale (Consigliato)».

**Contratto**:
1. **Il metodo del plugin**. `BRIMProvider.cannot_parse_reason(file_path) -> Optional[str]` è un metodo concreto della classe base, non astratto, che di default restituisce `None`.
   - Dà, in una frase inglese breve, senza maiuscola iniziale né punto finale, il motivo per cui `can_parse` rifiuta il file: qualcosa che l'utente può correggere. `None` vuol dire «niente da aggiungere».
   - Lo chiama solo la guardia del parse, dopo un `can_parse` falso. Deve costare quanto `can_parse` e non sollevare mai eccezioni.
2. **La guardia di `parse_file`** (`brim_provider.py` ~1431). Quando rifiuta, il messaggio è `Plugin '{code}' cannot parse file '{name}'`, più `: {motivo}` se c'è un motivo.
   - Il motivo si chiede sul percorso controllato per ultimo, cioè quello spostato se il file si è mosso.
   - Il metodo si legge con `getattr`: i plugin duck-typed dei test e i plugin scritti sulla base vecchia restano validi.
   - Un'eccezione del metodo si registra nel log e si ignora: resta il messaggio semplice, mai un 500.
   - Per il resto non cambia nulla: `ValueError`, quindi 400 dall'API, e il file va in `failed` con quel messaggio.
3. **Il CSV generico** implementa il metodo:

   | Caso | Motivo |
   |---|---|
   | estensione diversa da `.csv` | «the Generic CSV reads only .csv files» |
   | file illeggibile | «the file could not be read» |
   | nessuna riga d'intestazione | «the file has no header row» |
   | intestazione senza `date` e/o `type` | «required column 'date' not found in the CSV header», la stessa frase con 'type', oppure «required columns 'date' and 'type' not found in the CSV header» |
   | file leggibile dal plugin | `None` |

   - Invariante: `can_parse(p) is (cannot_parse_reason(p) is None)`, per costruzione, perché `can_parse` si appoggia al motivo.
4. **Cosa vede l'utente** nel riquadro degli errori del wizard: «x.csv — Plugin 'broker_generic_csv' cannot parse file '‹id›.csv': required column 'date' not found in the CSV header».
   - Il nome tra apici è quello salvato, `{file_id}{ext}`, e non viene da G: la guardia ha sempre usato `file_path.name`. Va al backlog, ed è fuori da G.

**Test** (test-author, prima rossi):
- `external brim-providers`: il motivo per ogni intestazione rifiutata, `None` per quelle accettate, i casi di estensione, file vuoto e file mancante, l'invariante su tutti i campioni, e il default della base.
- `services brim-parse-race`: il messaggio della guardia con e senza motivo, il plugin senza metodo, il metodo che solleva un'eccezione, il percorso spostato, e il generico vero.
- `api brim`: il parse forzato col generico su un CSV senza `date` risponde 400 col motivo, e il file finisce in `failed`.

**Doc** (docs-writer, solo EN): `brim_plugin_guide.md` (il metodo opzionale) e `generic-csv.en.md` (la frase dell'errore).

> **Note implementazione — G.5 (2026-10-05)**:
> - **Il rosso** (test-author):
>   - `external brim-providers`: la classe nuova `TestGenericCSVSaysWhyItRefuses`, 31 rossi per `AttributeError`; la parametrizzazione dei rifiuti ora dichiara a mano le colonne mancanti (`_HEADERS_MISSING_DATE_OR_TYPE`), e i 33 test esistenti restano verdi con gli stessi id;
>   - `services brim-parse-race`: 7 rossi e una guardia nuova già verde (il plugin senza metodo tiene il messaggio semplice, verificato per uguaglianza);
>   - `api brim`: RS-G05, rosso solo sulla fine di `detail`.
> - **La cura**:
>   - `BRIMProvider.cannot_parse_reason` (default `None`);
>   - `_refusal_message` in `brim_provider.py`, chiamata dalla guardia di `parse_file` col percorso controllato per ultimo, metodo letto con `getattr`, eccezioni registrate e ignorate;
>   - il CSV generico implementa il motivo, e `can_parse` è `cannot_parse_reason(p) is None`.
> - **Verdi**:
>
> | Verifica | Esito |
> |---|---|
> | `external brim-providers` | `626 passed`, 1 saltato (595 + 31) |
> | `services brim-parse-race` | `14 passed` |
> | `services brim-parse-pool` / `brim-parse-error` / `brim-report-sets` | `8` / `4` / `255 passed` |
> | `api brim` (per ultimo) | `73 passed` (72 + RS-G05) |
> | `dev.py lint`, `black --check` | puliti |
>
> - **Doc di G.5** (docs-writer, solo EN, senza stamp):
>   - `brim_plugin_guide.md`: la riga del metodo nella tabella dei metodi opzionali, la sottosezione «🗣️ Saying why a file is refused» (`#cannot-parse-reason`) e il messaggio nel flusso;
>   - `generic-csv.en.md`: il messaggio ora dice cosa manca, più una frase su come correggere il file.
>   - `mkdocs build` strict ok; `check-links` col solo D28; `translate-validate` senza problemi su generic-csv.
> - **⚠️ Fuori pista — `compatible_plugins` è calcolato al caricamento** e non si ricalcola più (`brim_provider.py:711`, `:723`, `:800`). Per un CSV caricato prima di G il CSV generico resta quindi proposto; sceglierlo ora fallisce col motivo. È un limite noto, per il backlog.

### G.6 ✅ Gate finali (2026-10-05), corsia 6156, un comando per volta

- `front build --debug` ok (dopo R3).
- `--clean` autorizzato prima del giro: da 46 file a 0.
- Il giro: script `/tmp/libreFolio_l_g_final_e2e.sh`, log in `/tmp/libreFolio_l_g_final_*.log`.

| Verifica | Esito |
|---|---|
| `tx-import-report-set` / `-guide` / `tx-bulk-import-handoff` / `tx-import-file-selection` | `18` / `2` / `2` / `2 passed` |
| `tx-import-upload` / `-flow` / `-resolution` / `-matching` / `-duplicate-precedence` | `9` / `10` / `12` / `6` / `6 passed` |
| `tx-wac-bulk` / `tx-bulk-diagnostics` / `tx-bulk-operations` / `tx-paired-edit` | `10` / `2` / `10` / `4 passed` |
| `front-utility files` / `files-uploader` / `select` / `image-crop` / `onboarding-tour` / `settings` | `22` / `6` / `17` / `42` / `10` / `45 passed` |
| `front-broker detail` | `33 passed` |
| Vitest `tx-unit` / `component-unit` / `core-unit` / `onboarding-component-unit` | `626` / `2203` / `2704` / `409 passed` |
| `tx-import-asset-inspector` | `4 passed`, **E2-001 rosso** (vedi sotto) |
| `tx-brim-import` / `tx-ca-contract` | T1 e CAC-011/012, rossi già accettati; `10 passed` in CAC |
| `front check` | **0/0** |
| `check-orphans` | pulito: 96 E2E, 281 Vitest e 227 backend raggiungibili |
| privacy (`/tmp/libreFolio_l_e_privacy.py 8c6853281`) | 0 collisioni su 3399 righe aggiunte |
| `git diff --check` | pulito; 26 file tracciati modificati, 0 nuovi; porte 6156 e 6166 libere |

> **⚠️ Fuori pista — E2-001 (`tx-import-asset-inspector`)**:
> - Rosso alla riga 476. Dopo «Annulla» sulla modale di cambio valuta, il clic sul combobox della valuta non apre la listbox: nello snapshot la modale «Edit Asset» è aperta, la valuta è «USD» e il combobox è chiuso.
> - Non viene da G. Risk lo riproduce 4 volte su 5 senza G (snapshot del coordinatore in `/tmp/lf-triage-k3/`), e G non tocca AssetModal, SearchSelect né la modale della valuta. Nel primo giro di G era verde.

> **Decisione di L sulla proposta del coordinatore (CAC-011/012 ed E2-001 nel giro di G): non costano poco, quindi backlog, oppure un mini-giro dopo il commit di G.**
> - **CAC**: la spec usa `isVisible({timeout})` 14 volte come condizione di ramo (`walkToReview`, `confirmNotices` e altri). Playwright ignora quel timeout e risponde subito, quindi renderla deterministica significa riscrivere quegli helper di una spec che non è di L.
> - **E2-001**: serve una test-triage vera, con trace. Potrebbe essere una corsa sul focus fra modali annidate, cioè un difetto del prodotto.
> - Lo stesso schema `isVisible({timeout})` è usato in circa 30 punti di altre spec (`tx-wac-fx`, `broker-sharing`, `brokers-detail`, `image-crop`, `tx-wac-formmodal`, `tx-bulk-suggest-ux`).

### G — ✅ pronta per il checkpoint (2026-10-05)

## 15. Integrazione di G (2026-10-05)

### 15.1 ✅ I commit e il merge di baseline (2026-10-05)

- I commit del developer, fatti con l'ORDER del coordinatore (`/tmp/libreFolio_ORDER_0510_lg.sh`) e verificati da lui; albero `5a4ed0eee`:
  - `15c91d42a` feat(import): choose how a report set is read
  - `a33eb243b` test(e2e): declare the onboarding GET in files-uploader
  - `96b7a4903` docs(import): how a report set is read and when the generic CSV applies
  - `a2dcf786f` docs(journal): Danske workstream step G
- Il merge `361c1acbd` (`merge(l): dev_release2 into L before step G integration`): genitori `a2dcf786f` e `d9aad0ec9` (il PAC planner di D e il suo changelog); albero `e88472305`, uguale alla simulazione; worktree pulito.
- Le correzioni ai messaggi, chieste da L prima del run e applicate dal coordinatore:
  - C1, il punto «Memory»: la memoria non legge `combined_into` ma `derived_from`, `parsed_plugin_code` e `processed_at`. L'errore era nel mio checkpoint;
  - C1, il punto «Wizard»;
  - C2, la data in formato ISO;
  - C3, il punto «Developer pages».
- **Decisione del developer sui rossi** (testuale, tramite il coordinatore): «E2-001 da capire subito dopo G, CAC nel backlog (Consigliato)».

### 15.2 ✅ Validazione della revisione unita `361c1acbd` (2026-10-05 → 2026-10-06), corsia 6156, un comando per volta — interrotta il 05/10 perché il developer stacca, ripresa il 06/10

- G e D si sovrappongono solo nei cataloghi i18n ×4, che Git ha unito da solo.

| Verifica | Esito |
|---|---|
| i18n a tre vie (`git show`, base `8c6853281`) | in ogni lingua 4505 chiavi = 3543 + 7 (G) + 955 (D); nessuna chiave mancante, in più o con valore diverso; le 7 chiavi di G ci sono tutte |
| `api sync` / `front build --debug` / `mkdocs build` (strict) | ok / ok / ok, 0 WARNING e 0 ERROR |
| `services brim-report-sets` / `brim-parse-race` / `brim-parse-pool` / `brim-parse-error` | `255` / `14` / `8` / `4 passed` |
| `external brim-providers` | `626 passed`, 1 saltato |
| `front check` | **0/0** |
| `i18n audit` | completo (4505 chiavi). «Likely Unused» passa da 393 a 522: sono 129 chiavi `tools.*` in più, tutte di D, nessuna di G. `importWizard.reportSet.gapFix.stepTitle` resta il falso positivo già noto (§13.2) |
| Vitest `tx-unit` / `component-unit` / `core-unit` / `onboarding-component-unit` | `626` / `2223` / `2898` / `409 passed` (crescono coi test di D) |
| `--clean` autorizzato | ok, 0 file |
| E2E di import | `report-set` 18, `-guide` 2, `handoff` 2, `file-selection` 2, `upload` 9, `flow` 10, `resolution` 12, `matching` 6, `duplicate-precedence` 6, `wac-bulk` 10, `bulk-diagnostics` 2, `bulk-operations` 10, `paired-edit` 4 |
| E2E utility e broker | `files` 22, `files-uploader` 6, `select` 17, `image-crop` 42, `onboarding-tour` 10, `settings` 45; `front-broker detail` 33 |
| Rossi | T1 e CAC-011/012, già accettati (CAC va nel backlog); **E2-001**, allo stesso punto del giro finale di G |

- **Ripresa del 2026-10-06** («Riprendi» del coordinatore). Lo stato era come allo stop: HEAD `361c1acbd`, solo il piano modificato, la data-dir presente, le porte libere, `dev_release2` = `d9aad0ec9`, antenato di HEAD. La macchina è carica per i servizi di sistema; il carico (load average) è annotato prima e dopo ogni comando.

| Verifica (06/10) | Esito | Carico |
|---|---|---|
| `api pac-planner-tool` | `7 passed` | da 17,9 a 18,2 |
| `api brim` (per ultimo) | `73 passed` | da 17,6 a 30,1 |
| `check-orphans` | pulito: 96 E2E, 286 Vitest, 228 backend | — |
| `mkdocs check-links` | 81 link validi, i 3 gialli noti e il solo rosso D28 (`#rolling-return` in it/fr/es), già accettato | — |
| `git diff --check` | pulito; l'unico file modificato è il piano | — |

- La revisione unita è **pronta per l'integrazione**: l'avanzamento in fast-forward di `dev_release2`, da `d9aad0ec9` a `361c1acbd`, più il commit del journal con questo §15.
- All'integrazione il client API va rigenerato (`api sync`), perché il client generato è ignorato.
- I rossi restano T1 e CAC-011/012, già accettati (CAC va nel backlog), ed E2-001 (§15.3).
- Alla fine del giro le porte 6156 e 6166 sono libere (`lsof` senza ascolto) e nessun processo del runner è attivo.
- La pulizia di macOS può cancellare la data-dir della corsia: al rientro si ripopola con `db populate --force`, solo in `/tmp/librefolio-r2-l`.
- Il materiale per riprendere è copiato fuori dal repo, nei file della sessione di L (`resume-g-merge/`): i log dei gate, gli script dei giri, lo scanner di privacy e gli snapshot di E2-001 presi da Risk (`/tmp/lf-triage-k3/`).

### 15.3 ⏳ Dopo l'integrazione: la triage di E2-001

- **Il rosso**: `tx-import-asset-inspector.spec.ts:653`, riga 476 (`chooseCurrency`), dentro la seconda `blockedSave` (riga 704), dopo «Annulla» sulla `currency-change-modal`. Il clic sul combobox della valuta non apre la listbox. Nello snapshot la modale «Edit Asset» è aperta, la valuta è «USD» e il combobox è chiuso.
- **Frequenza**:
  - da Risk, 4 corse su 5 senza G, con carico 8–23;
  - nella corsia di L, verde nel primo giro di G, poi rosso nel giro finale di G e nella revisione unita.
- **Metodo**: la skill test-triage, con la traccia di Playwright.
  - Se la causa è nel prodotto (AssetModal, la modale della valuta o SearchSelect, tutti fuori dal perimetro di L), la diagnosi va al coordinatore **prima** di correggere.
  - Se la causa è nel test, lo ripara il test-author, in un commit `test(e2e)` separato.

## 16. Triage di E2-001 (2026-10-06)

**Avvio**:
- G è integrato: `dev_release2` = `385238e85`, cioè `bff6dea45` più il CHANGELOG (`v1.1.0-464`). Il client API è rigenerato dal coordinatore.
- Il ramo di L è a `bff6dea45`, pulito. Corsia 6156 e `/tmp/librefolio-r2-l`.

### 16.1 ✅ Le prove già raccolte, prima di rilanciare (skill §0)

- Lo snapshot ARIA e lo screenshot di Risk, più il log del giro finale di G e quello della revisione unita.
- Al fallimento la modale «Edit Asset» è aperta, la valuta è «USD $» e il trigger è chiuso (senza `[expanded]` né `[disabled]`), con lo stile di hover. Il clic dunque è arrivato al trigger, ma per 10 s `isOpen` è rimasto falso: la listbox esiste solo dentro `{#if isOpen}`, nel contenitore.
- **Il codice**:
  - `CurrencySearchSelect` usa `SearchSelect` con `inlineSearch={true}`;
  - il clic sul trigger chiama `toggleDropdown()`;
  - `openDropdown()` esce senza fare nulla se `disabled`, oppure se `Date.now() - lastClosedAt < 200`. È la guardia contro la riapertura immediata («touch event race»), ed è un orologio nel prodotto;
  - `closeDropdown()` rimette il focus sul trigger;
  - il clic fuori chiude la tendina con un listener di `mousedown`, attivo solo mentre è aperta;
  - nel 409 `AssetModal` apre `AssetCurrencyChangeModal` (`ModalBase`); «Annulla» la chiude e azzera blocker e payload.
- **Ipotesi da verificare con la traccia**, in ordine:
  1. il clic trova la tendina già aperta, per esempio ancora in `loading`, quindi senza opzioni: `optionsClosed` passa, e il clic la chiude (`toggle`);
  2. il clic cade entro 200 ms da una chiusura;
  3. il trigger viene rimontato fra il clic e l'attesa;
  4. il clic arriva mentre il componente è `disabled`.
- **Come avere la traccia**:
  - il runner non passa argomenti a Playwright, e in locale `retries: 0` con `trace: 'on-first-retry'` non registra nulla;
  - `CI=1` cambia in `playwright.config.ts` soltanto `retries` (2), `forbidOnly` e il timeout del `webServer`, e nient'altro nel runner o nel backend;
  - quindi il comando canonico con `CI=1` registra traccia e video al primo retry, senza toccare file. Il carico si annota prima e dopo.

### 16.2 ✅ Le misure (2026-10-06), corsia 6156, un comando per volta

| Corsa | Come | Carico | E2-001 |
|---|---|---|---|
| T1 | runner con `CI=1` | 8,8 | ✘ al primo tentativo (non tracciato), ✓ al retry tracciato |
| T2 | Playwright diretto con `--trace retain-on-failure` (vedi il Fuori pista) | 6,2 | ✓, 5/5 verdi |
| P1–P4 | runner con `DEBUG=pw:protocol`, senza traccia | 5,2 / 6,4 / 8,5 / 10,4 | ✘ / ✘ / ✓ / ✘ |

- **Nessuna eccezione JS** (`Runtime.exceptionThrown` = 0) e nessun errore di console nuovo: cade l'ipotesi dell'errore di rendering.
- **La traccia verde** (T1, retry):
  - la modale della valuta sparisce subito dopo «Annulla», perché sta dentro `{#if open && blocker}` e non fa la transizione d'uscita;
  - il secondo clic arriva circa 127 ms dopo «Annulla» e apre la tendina.
- **La cronologia del protocollo** (P1–P4) va dal clic sull'opzione USD (`selectOption` → `closeDropdown` → `lastClosedAt`) al secondo clic sul trigger. La differenza di tempo coincide fra l'invio e la conferma di Chrome, con uno scarto di circa 3 ms:

| Corsa | Opzione → secondo clic | «Annulla» → secondo clic | Esito |
|---|---|---|---|
| P1 | 191 ms | 50 ms | ✘ |
| P2 | 189 ms | 48 ms | ✘ |
| P3 | 316 ms | 78 ms | ✓ |
| P4 | 191 ms | 50 ms | ✘ |
| tracciate | oltre 600 ms | — | ✓ |

- A decidere l'intervallo è la latenza del PATCH 409: dalla richiesta a «Annulla» passano 104 ms in P1 e 182 ms in P3. Il carico non decide: P1 è rosso con carico 5,2. Anche la traccia «risolve» il rosso solo perché rallenta ogni azione.
- **⚠️ Fuori pista — gli strumenti**:
  - il runner non passa argomenti a Playwright, quindi in T2 ho chiamato Playwright direttamente (`node_modules/.bin/playwright` via `pipenv run`), con lo stesso ambiente della corsia che imposta il runner (`TEST_PORT=6156`, `LIBREFOLIO_TEST_DATA_DIR=/tmp/librefolio-r2-l`, `LIBREFOLIO_TEST_MODE=1`, `PIPENV_DONT_LOAD_ENV=1`, `LF_SETUP_DONE=1`) e con `--trace retain-on-failure`;
  - T1 e P1–P4 usano il comando canonico, con `CI=1` (retry e traccia) oppure `DEBUG=pw:protocol`, che il backend non legge;
  - nessun file tracciato è cambiato.
- Un mio errore di analisi, corretto: il primo conteggio di P3 dava 171 ms, perché il parser riconosceva il trigger dalle coordinate più frequenti e in P3 c'era un pareggio. Ora riconosce la sequenza del test (trigger, opzione, Save, «Annulla», trigger).

### 16.3 ✅ Il verdetto (2026-10-06): **defect** nel prodotto (`SearchSelect`), fuori dal perimetro di L

- **La causa**: `openDropdown()` ignora ogni apertura che arriva meno di 200 ms dopo l'ultima chiusura (`Date.now() - lastClosedAt < 200`). La guardia viene da `f9e79d580` (17/04, «dropdown not reopening after selection on mobile») e serve contro il clic fantasma del tocco sul trigger sotto l'opzione. Però si applica a **qualunque** chiusura: mouse, tastiera, selezione.
  - Il test seleziona USD, salva, riceve il 409, annulla e riapre la tendina in circa 190 ms. Il clic vero viene scartato in silenzio, `isOpen` resta falso e l'attesa della listbox scade dopo 10 s.
  - Lo stato «riapertura bloccata» non si vede da nessuna parte, né per il test né per l'utente (skill §6). Un test non può aspettarlo senza un orologio.
- **Perché non è il test**: nessuna posizione, nessun conteggio, nessuna attesa sbagliata. Il test fa ciò che può fare un utente veloce o un programma. E la guardia non ha un test unitario (`SearchSelect.test.ts` non la copre).
- **Correzione proposta** (da approvare; `SearchSelect` è condiviso da 38 componenti):
  - la guardia si applica solo se la chiusura è venuta da un tocco o da una penna, cioè dal `pointerType` del `pointerdown` che ha portato alla selezione o alla chiusura. Le aperture con mouse e tastiera dopo una chiusura con mouse o tastiera restano immediate;
  - prima i test unitari rossi (test-author, Vitest): la riapertura immediata col mouse dopo una selezione col mouse; quella con la tastiera dopo una selezione con la tastiera; il clic fantasma dopo una selezione col tocco, che resta ignorato;
  - poi la correzione. E2-001 dovrebbe diventare verde senza toccare la spec; da verificare con P1–P4 ripetuti;
  - un'alternativa solo nel test (un ciclo `toPass` sul clic) è possibile, ma nasconderebbe il difetto.
- Altre spec che riaprono una `SearchSelect` entro 200 ms da una selezione possono avere lo stesso rosso intermittente. È un'ipotesi, non l'ho verificata.

### 16.4 ✅ La correzione di `SearchSelect` (2026-10-06)

**Decisione del developer** (testuale, tramite il coordinatore): «L corregge sul suo ramo, con i test prima (Consigliato)».

**Vincoli del coordinatore**:
- i test rossi li scrive il test-author, in un **file separato**, `frontend/src/lib/components/ui/select/SearchSelect.reopen.test.ts`. La famiglia Risk ha aggiunto 127 righe a `SearchSelect.test.ts` sul suo ramo;
- la registrazione in `component-unit` (`scripts/test_runner/_frontend_utility.py`) è **una riga**, subito dopo `SearchSelect.test.ts`, non in fondo, e la `desc=` non si tocca.
  - Su `cda8cba1c` F inserisce `AssetPickerPanel.test.ts` dopo `AssetTypeSelect.test.ts`, cioè quattro righe più giù, e cambia le `desc=` di `core-unit` e `component-unit`;
  - prima del checkpoint, `git merge-file -p` contro la versione di `cda8cba1c` (base `9b5291c25`), salvando subito il codice d'uscita;
- la spec di E2-001 non si tocca;
- i gate: `component-unit`; E2-001 ripetuto con la misura dell'intervallo; `select` e qualche `tx-import-*` con molte `SearchSelect`; `front check`.

**Contratto**, cioè il comportamento che i test fissano:
1. **Mouse**: si apre col clic sul trigger e si sceglie un'opzione col mouse (`pointerdown` con `pointerType: 'mouse'`, poi `click`). Un clic sul trigger **subito dopo, allo stesso istante**, apre la tendina.
2. **Tastiera**: si apre con `ArrowDown` sul trigger e si sceglie con `Enter` nel campo di ricerca. Un `ArrowDown` sul trigger subito dopo apre la tendina.
   - `Enter` subito dopo che il trigger prende il focus resta bloccato da un'altra guardia (`triggerFocusedAt`), che non cambia; il test riapre con `ArrowDown`.
3. **Tocco** (e penna): si apre e si sceglie un'opzione col tocco (`pointerdown` con `pointerType: 'touch'`, poi `click`). Un clic sul trigger entro 200 ms, cioè il clic fantasma, viene ignorato e la tendina resta chiusa. Passati 200 ms, un nuovo tocco la apre.
4. Senza nessun `pointerdown`, per esempio con un `click` sintetico, la chiusura non conta come tocco: l'apertura subito dopo funziona.

**Progetto della correzione** (in `SearchSelect.svelte`; nessun altro file del prodotto):
- il componente ricorda il `pointerType` dell'ultima pressione al suo interno, con un listener `pointerdown` in cattura sul contenitore, registrato in un `$effect`. Un `keydown` al suo interno lo azzera;
- `closeDropdown()` registra se la chiusura è venuta dal tocco o dalla penna;
- `openDropdown()` applica la guardia dei 200 ms solo in quel caso.

> **Note implementazione — 16.4 (2026-10-06)**:
> - **Il rosso** (test-author): `SearchSelect.reopen.test.ts`, 5 test × 2 layout (ricerca nella tendina e nel trigger, cioè `inlineSearch`):
>   - mouse, tastiera, nessun puntatore: **6 rossi**, sull'ultima asserzione (il trigger resta `aria-expanded="false"`), con tutte le premesse verdi;
>   - tocco e penna: **4 verdi**, perché proteggono la correzione mobile originale;
>   - `component-unit`: 2223 test esistenti verdi; `check-orphans` pulito (287 file).
> - **La registrazione**: una sola riga in `_frontend_utility.py`, subito dopo `SearchSelect.test.ts`.
> - **La cura**: in `SearchSelect.svelte`, `lastPointerType` (listener `pointerdown` e `keydown` in cattura sul contenitore, in un `$effect`), `closedByTouch` in `closeDropdown()`, la guardia in `openDropdown()` solo se `closedByTouch`.
> - **I gate** (corsia 6156, un comando per volta):
>
> | Verifica | Esito |
> |---|---|
> | `front-utility component-unit` | 98 file, **2233 passed** (2223 + 10) |
> | `front check` | **0/0** |
> | `front build --debug` | ok |
> | Prettier `--check` sui due file del frontend, `black --check` sul runner | puliti |
> | E2-001 con `DEBUG=pw:protocol`, spec intera (P5–P8) | 4/4 ✓, intervalli 211–347 ms, carico 9,6–18,7: non discriminano |
> | E2-001 da solo (P9–P12) | 4/4 ✓, intervalli **194**, 219, **203**, 312 ms dalla conferma (182, 206, 191, 298 dall'invio). P9 (182 ms) e P11 (191 ms) hanno gli stessi intervalli che prima erano sempre rossi (189–191 ms, 3 su 3) |
> | `front-utility select` | `17 passed` |
> | `tx-import-asset-inspector` / `-resolution` / `-matching` / `-flow` / `-upload` | `5` / `12` / `6` / `10` / `9 passed` |
> | `tx-bulk-operations` / `tx-wac-bulk` | `10` / `10 passed` |
>
> - **Una firma indipendente**: Chrome conferma il secondo clic in circa 3 ms quando lo scarta (P1, P2, P4) e in 14–18 ms quando apre la lista, perché deve disegnarla (P3 e tutte le corse dopo la correzione).
> - **`git merge-file -p`** sul runner contro `cda8cba1c` (base `9b5291c25`): **rc=0**, nessun marcatore di conflitto. Il file unito contiene sia `SearchSelect.reopen.test.ts` sia `AssetPickerPanel.test.ts` di F, e si legge senza errori.
> - **Spec candidate allo stesso rosso** (scansione statica, una guardia per istanza):
>   - `tx-fx-completeness.spec.ts:370→375` sceglie EUR e poi USD **nella stessa** `SearchSelect` (`tx-form-cash-to`), con solo due asserzioni rapide in mezzo. Oggi è mascherata da `openSearchSelect` (riga 82), che riclicca finché `aria-expanded="true"` (`toPass`, 3 s; introdotta in `ef722b552`). Con la correzione il ciclo non serve più: da semplificare (backlog);
>   - `tx-commit-all-types`, `tx-fx-implied-rate` e `fx-add-pair` sono falsi positivi: scelgono in istanze diverse;
>   - nessun'altra spec riapre la stessa istanza in fretta.
> - Non eseguiti: `tx-import-report-set` e `tx-import-file-selection`, sensibili ai file BRIM rimasti dopo `api brim` di stamattina. Il permesso di `--clean` è scaduto con G.

> **Note implementazione — la documentazione (2026-10-06)**: il docs-writer ha aggiunto un punto in `developer/frontend/components/core-ui/select.md`, sezione «🔎 SearchSelect». Dice che solo una chiusura col tocco o con la penna blocca la riapertura per 200 ms (`closedByTouch`), mentre mouse e tastiera non la bloccano mai. Ricorda anche la guardia separata e invariata su `Enter` subito dopo che il trigger prende il focus (`triggerFocusedAt`, solo con un valore impostato). `mkdocs build` strict ok; `check-links` col solo D28. Pagina senza traduzioni.

### 16 — ✅ pronta per il checkpoint (2026-10-06)

> **Note implementazione — il gate in più, chiesto dal coordinatore prima dello script (2026-10-06)**:
> - un solo `db populate --force --clean`, autorizzato, sulla corsia 6156 (`/private/tmp/librefolio-r2-l`): i file della corsia passano da 854 a 0;
> - poi, sull'albero di allora e senza toccare file: `tx-import-report-set` **18 passed** (carico 36,8) e `tx-import-file-selection` **2 passed**.
>
> **Integrazione**: `5df39167a` (fix), `e09ec9b47` (docs), `eade0c135` (journal), poi il merge `af5591991` (albero `b2e5e16d4`). `dev_release2` = `aa74797ff` (`v1.1.0-471`), con la riga 🐛 nel CHANGELOG. Nel backlog di fine round del coordinatore: CAC-011/012, il ciclo `toPass` di `openSearchSelect` (`tx-fx-completeness.spec.ts:82`), l'opzione `--trace` del runner e la nota su Invio e `triggerFocusedAt`.

## 17. Review del passo G (2026-10-06)

**Richiesta del developer** (testuale, tramite il coordinatore): «Sì, L prepari ora la review sulla 6166».

### 17.1 ✅ La corsia di review (2026-10-06)

- **Codice**: il worktree a `af5591991`, cioè `dev_release2` meno il CHANGELOG. `front build --debug`; il server dice `v1.1.0-470-gaf5591991`.
- **Data-dir**: `/tmp/librefolio-r2-l-review`, nuova e separata da quella dei test. Un solo `test --test-port 6166 --data-dir /tmp/librefolio-r2-l-review db populate --force --clean`, autorizzato solo lì.
  - Utenti di test creati con `dev.py user --test-db create` (più `promote` dell'admin) e impostazioni globali con `init-settings`, tutti con `LIBREFOLIO_TEST_DATA_DIR` sulla stessa data-dir.
  - Verifica: cambia solo l'`app.db` della review; in questo worktree non esiste un DB di test predefinito.
- **Server**: `dev.py server --test --host 127.0.0.1 --port 6166 --data-dir /tmp/librefolio-r2-l-review --no-reload --no-scheduler`, senza `--force`. Ascolta solo su `127.0.0.1:6166`; il login di `e2e_test_user` risponde 200.
- **File sintetici**, fuori dal repo, in `/tmp/librefolio-r2-l-review-files/`. Vengono solo dai campioni sintetici di `sample_reports/`, nessun dato reale. Chi li legge, controllato col registro dei plugin:

| File | Plugin che lo leggono | Motivo del CSV generico |
|---|---|---|
| `danske_bank-custody.xlsx` | Danske | «the Generic CSV reads only .csv files» |
| `danske_bank-cash.csv` (come la spedisce la banca) | Danske | colonne `date` e `type` assenti |
| `danske_bank-cash-both.csv` (la cassa «doppia», come `writeDualCash` della spec) | Danske e CSV generico | — |
| `generic_simple.csv` | CSV generico | — |
| `generico-senza-date-type.csv` | nessuno | colonne `date` e `type` assenti |
| `generico-solo-date.csv` | nessuno | colonna `type` assente |

- **Un limite della review**: la nota «riconosciuto anche da…», cioè un altro plugin a set, non si può mostrare, perché oggi Danske è l'unico plugin a set.

### 17.2 ⏳ Le osservazioni del developer, primo giro (2026-10-06)

**Testuali**, nella chat di L:

> «il selettore read as è fatto con un select os e non uno custom fatto da noi. in oltre se faccio ce lo voglio leggere 1 ad 1 on ho modo poi di tornare indietro nella scelta, devo fare step back e poi avanti, e sono ancora in quello singolo, poi se nel primo scelgo il plugin di danske bak solo il primo passa al set, se faccio anche il secondo pure e almeno si mettono nello stesso set.
> Poi nella riga con le barre, securities transactions è troppo corto  come spazio e la parte finale viene troncata con i ... sono su desktop, mi aspettavo di vederlo tutto.
>
> il cash-both non ho capito che dovrei farci nel test, nel plugin dice giustamente che manca l'xlsx, se poi scelgo il generico rileva 9 depositi e 23 prelievi, ti torna?
>
> l'escludi dal set funziona, ma come prima non compare la possibilità di scegliere un plugin fino a che non faccio indietro e poi avanti
>
> quando scrivi "apri la scheda: c'è la nota «Letto come set Danske Bank, non col plugin predefinito del broker (Generic CSV)…»;" non ho capito dove guardare, ma ho notato che solo nei csv, nel kebab menù c'è l'opzione di rimuoverlo e leggerlo con il generic csv, intendevi lui? se lo clicco però all'inizio in tabella il plugin è -
>
> ho poi notato nele prove, uscendo e rientrando, che la memoria resta, quindi direi che funziona.
>
> intanto risolvi queste cose, poi rifacciamo da capo»

- Server di review spento a fine giro: porta 6166 libera (`lsof` rc=1).
- Il prossimo passo è l'analisi di ogni punto, da mandare al coordinatore prima di correggere, come al solito.

### 17.3 ✅ Analisi delle osservazioni (2026-10-06)

| # | Osservazione | Causa verificata nel codice | Proposta |
|---|---|---|---|
| R1 | «Letto come» è una select nativa del sistema operativo | `ReportSetCard.svelte:338`, un `<select>` HTML | `SimpleSelect`, la nostra select senza ricerca (tastiera, `compact`, `testId`; già usata da 15 componenti). Vanno aggiornati i test che usano `selectOption` / `change` (test-author) |
| R2 | Dopo «Leggi i file uno per uno» non si torna indietro | `readSetAs(set, null)` dà a ogni membro un override fuori dal set, quindi il set e la sua scheda spariscono, e con loro il menu. Si torna al set solo scegliendo Danske nella colonna Plugin di ogni file | da decidere col developer (17.4) |
| R3 | Nella timeline «Securities transactions» è troncato con «…» su desktop | `ReportSetCard.svelte:475`: l'etichetta del ruolo ha larghezza fissa `w-26` (104 px) e `truncate`; la riga delle date si allinea con `pl-28`/`pr-44` | colonna dell'etichetta larga quanto l'etichetta più lunga (griglia `max-content` / `1fr` / `max-content`, con le date allineate alla colonna delle barre); a capo solo se lo schermo è stretto |
| R4 | Dopo «Togli dal set» la scelta del plugin compare solo dopo Indietro/Avanti; dopo «Leggi da solo con…» il plugin in tabella è «—» | La colonna Plugin mostra la select **solo sui file spuntati** (`ImportWizardModal.svelte`, colonna `plugin`: `if (!sel) return '—'`). «Togli dal set» toglie la spunta di proposito; «Leggi da solo» e «uno per uno» tengono la spunta solo se c'era già, e con un set incompleto non c'era. Indietro/Avanti rispunta da solo i file caricati in questa sessione (`pickBestPlugin`), ed è per questo che la select «compariva» | da decidere col developer (17.4) |
| R5 | La nota del plugin predefinito non si trova | Il broker creato, «danske bank» (id 9), ha `default_import_plugin = NULL` (verificato sul DB della review, in sola lettura). La nota esiste solo se il predefinito del broker è un altro plugin che legge un file del set (per esempio Generic CSV con `cash-both`): la sua assenza è corretta, non è un difetto. Le voci del menu ⋮ sono un'altra cosa (B) | nel prossimo giro, guida più chiara: impostare Generic CSV come predefinito; la nota è la riga blu con (i) in cima alla scheda aperta |
| R6 | `cash-both` col generico: 9 depositi e 23 prelievi, torna? | Sì: 32 righe; la colonna `type` del file di prova viene dal segno di ogni importo (9 positivi, 23 negativi) | spiegarlo al developer: `cash-both` serve solo perché è l'unico file che leggono sia Danske sia il generico |
| R7 | La memoria resta uscendo e rientrando | — | ✅ confermata dal developer |

### 17.4 ⏳ Decisioni del developer

- **R2, come si torna indietro da «uno per uno»** (testuale): «direi che per tornare indietro devo rimettere il plugin della banca in ogniuno dei file, e per farlo ovviamente deve essere possibile raggiungere il menù, levare dal set i file poi trovo corretto li faccia anche deselezionare, singolarmente sono ancora selezionati, ad essere cambiato è stato il modo di parsarli».
  - Quindi: niente scheda ridotta né riga «Leggili come set». Si torna al set rimettendo il plugin della banca file per file, nella colonna Plugin, che dev'essere raggiungibile;
  - «Togli dal set» toglie anche la spunta: va bene così;
  - «Leggi i file uno per uno» **lascia spuntati tutti i file**: cambia solo come vengono letti. Un file che nessun plugin singolo legge resta spuntato, senza plugin, con la select su «Seleziona plugin…», da cui si può rimettere la banca.
- **R4, la select del plugin sui file non spuntati** (testuale): «il select dovrebbe stare al posto del - , è un bug che non ci sia, dalla tua risposta immagino sia perchè togliendoli dal set si despuntano, se non è quella la causa trovala tu».
  - La causa è proprio quella: la colonna Plugin mostra `—` quando il file non è in `selectedFiles`;
  - più un difetto latente trovato nell'analisi: la tabella dei file singoli prende la selezione solo quando si monta (`initialSelectedIds`, in `untrack`). Un file che arriva dal set in una tabella già montata, per esempio con «Leggi da solo», risulta in `selectedFiles` ma senza spunta, e il primo clic su un'altra casella della tabella lo deseleziona senza dirlo.
- **R1** (a voce nella domanda, senza obiezioni): `SimpleSelect` al posto della select nativa. **R3**: l'etichetta prende tutta la larghezza che le serve.

### 17.5 ⏳ Il piano delle correzioni (H), approvato

**Via del coordinatore** (2026-10-06): R1, R2 come ha deciso il developer, R3, R4 più il difetto latente, con `DataTable` intatto. `--clean` sulla 6156 prima di ogni giro E2E fino alla fine di H; per il secondo giro di review, `populate --force --clean` solo sulla data-dir di review. Nessun ramo tocca i 6 file.

**La spunta alla scelta del plugin**, confermata dal developer (ask_user, testuale): «Sì: scegliere un plugin su un file non spuntato lo spunta (Consigliato)». Vale anche per «Leggi da solo con…», che è una scelta di plugin.

**⚠️ Fuori pista — R4 ridefinito dal developer, dopo i rossi del primo giro** (testuale, nella chat di L): «riguardo al file non spuntato, ripeto che l'errore non è mostrare - per quelli non spuntati, è despuntare i file tolti dal set quando si chiede di trattare tutto il set come file singoli, per l'excel capisco che venga mostrato "nessun plugin disponibile" ma sui csv ni, dipende».
- Riepilogo proposto da L e confermato (ask_user, testuale: «Sì, è così (Consigliato)»), che **sostituisce** la conferma precedente:
  1. «Leggi i file uno per uno» non despunta più nessun file e cambia solo come vengono letti. Il file che un plugin singolo legge lo prende (`cash-both` → Generic CSV). Il file che nessun plugin singolo legge (l'Excel, la cassa come la esporta la banca) resta spuntato senza plugin, con la select su «Seleziona plugin…» che offre comunque Danske per tornare al set; finché non si sceglie, «Analizza» resta bloccato;
  2. i file non spuntati, per esempio dopo «Togli dal set», **tengono il «—» come oggi**: per scegliere il plugin si spuntano prima;
  3. le scelte di plugin **non cambiano la spunta**: «Leggi da solo con…» lascia il file spuntato o no com'era. Resta la correzione del difetto latente: la casella della tabella dei singoli coincide sempre con la selezione del wizard.
- Quindi cadono la select sui file non spuntati e la spunta alla scelta. I rossi H-E3, H-E4, H-E5 e i due G-memory adattati vanno riscritti sul nuovo contratto (test-author).

1. **I test rossi** (test-author):
   - Vitest `ReportSetCard.test.ts`: «Letto come» è una `SimpleSelect` (`report-set-read-as-button`, le opzioni via `optionTestId`), e la scelta chiama `onReadAs`;
   - E2E `tx-import-report-set.spec.ts`:
     - «uno per uno» lascia spuntati tutti i file; l'XLSX ha la select su «Seleziona plugin…»; «Analizza» resta bloccato finché si sceglie; rimettere Danske su ogni file riforma il set;
     - «Togli dal set» toglie la spunta e mostra la select al posto di «—»; scegliere Danske rispunta il file e lo rimette nel set;
     - «Leggi da solo con Generic CSV» da un set incompleto mostra Generic CSV, col file spuntato;
     - la casella della tabella coincide sempre con la selezione;
     - l'etichetta della timeline non è troncata su desktop (`scrollWidth ≤ clientWidth`);
   - adattare i test G che usano la select nativa.
2. **La correzione**:
   - `ReportSetCard.svelte`: R1 con `SimpleSelect` `compact`; R3 con la timeline a griglia;
   - `ImportWizardModal.svelte`:
     - `readSetAs(set, null)` conserva la selezione di ogni membro;
     - la colonna Plugin mostra la select anche sui file non spuntati, col valore della scelta in vigore, e scegliere un plugin spunta il file (proposta di L: il developer non ha obiettato, ma va confermato nel secondo giro);
     - la tabella dei singoli si rimonta quando cambiano i suoi file, e spunta con `toggleRowSelectionById` quando la scelta lo richiede.
3. **I gate**: `tx-unit`, `component-unit`, `front check`, `front build --debug`; E2E `report-set` (con `--clean` prima), `-guide`, `handoff`, `file-selection`, `upload`, `flow`; `select`.
4. **La doc** (docs-writer, solo EN): `import-wizard.md` (testid e comportamento) e `danske-bank.en.md` (come si torna al set; i file tolti hanno la select).
5. Checkpoint, poi il **secondo giro di review** sulla 6166, da capo, con una guida più chiara per la nota (Generic CSV come predefinito).

### 17.6 ✅ H: il rosso, la cura, i gate (2026-10-06)

> **Note implementazione**:
> - **Il rosso** (test-author, due giri; il secondo dopo la ridefinizione di R4):
>   - Vitest `ReportSetCard.test.ts`: 6 rossi, cioè 5 test R1 adattati a `SimpleSelect` e il nuovo R3 sulle etichette;
>   - E2E `tx-import-report-set.spec.ts`: 5 rossi su 24, ciascuno sul suo punto: H-E1 e H-E2 ×2 (R1, il trigger manca; poi R2), H-E6 (difetto latente: la casella «unchecked» mentre il wizard tiene il file selezionato), H-E7 (R3). Più due guardie verdi: H-E3, la via del ritorno da «Togli dal set», e H-E5, «Leggi da solo» che non cambia la spunta. H-E4 è cancellato e i G-memory sono tornati a HEAD.
> - **La cura**:
>   - `ReportSetCard.svelte`:
>     - R1: `SimpleSelect` `compact`, testid `report-set-read-as`, opzioni `report-set-read-as-option-<code>` e `-one-by-one` (valore sentinella `__one_by_one__`, perché un valore vuoto vorrebbe dire «nessuna scelta»);
>     - R3: la timeline è una griglia `fit-content(40%)` / `minmax(0,1fr)` / `max-content`; le date e la legenda stanno nella colonna delle barre; le etichette hanno `report-set-timeline-label` e `data-role`, `history` per LibreFolio;
>   - `ImportWizardModal.svelte`:
>     - R2: `readSetAs` cambia solo il plugin dei membri e ne conserva la spunta;
>     - difetto latente: la tabella dei singoli è dentro un `{#key}` sugli id dei suoi file, quindi si rimonta quando un file entra o esce e rilegge `initialSelectedIds`. `DataTable` emette `onSelectionChange` solo su azioni dell'utente, quindi il rimontaggio non tocca la selezione;
>   - Prettier sui due file, con le modifiche confinate alle zone toccate.
> - **I gate** (corsia 6156, un comando per volta, `--clean` prima del giro):
>
> | Verifica | Esito |
> |---|---|
> | `front-transaction tx-unit` | `627 passed` (i 6 rossi sono verdi) |
> | `front check` | **0/0** |
> | `front build --debug` | ok |
> | `tx-import-report-set` | **24 passed** a 1 worker (carico 15) e **24 passed** a 4 worker |
> | `-guide` / `tx-bulk-import-handoff` / `tx-import-file-selection` / `tx-import-upload` / `tx-import-flow` / `tx-import-resolution` | `2` / `2` / `2` / `9` / `10` / `12 passed` |
> | `front-utility select` / `files` / `component-unit` | `17` / `22` / `2233 passed` |
>
> - Porta 6156 libera alla fine.

> **Note implementazione — la doc di H (2026-10-06)**, dal docs-writer, solo EN:
> - `user/transactions/import/danske-bank.en.md`, «🔀 How the set is read»: «uno per uno» cambia solo come vengono letti i file e non la spunta; un file spuntato senza plugin mostra *Select plugin…* e «Analizza» aspetta. «Leggi da solo» non cambia la spunta; solo «Togli dal set» toglie la spunta. Il file non spuntato mostra «—»: si spunta per scegliere il plugin, e Danske lo rimette nel set (dopo «uno per uno», file per file). La nota è «in cima alla scheda aperta», che risponde a R5. La pagina non ha traduzioni.
> - `developer/frontend/components/features/import-wizard.md`: un punto nuovo sui file singoli (`handleSelectionChange`, colonna Plugin, `step2CanParse` e i due avvisi, il `{#key}` e perché); la griglia della timeline e `report-set-timeline-label`; «Read as» con `SimpleSelect` e i testid; `readSetAs`, `readFileAlone` e `removeFileFromSet` col nuovo contratto; il ritorno al set file per file.
> - **⚠️ Fuori pista — crash dell'app verso le 14:18**, durante il lavoro del docs-writer, che non ha consegnato il rapporto:
>   - stato ritrovato: HEAD `af5591991`, 7 file modificati, niente in stage, nessuna porta occupata e nessun processo rimasto;
>   - i file di codice hanno l'ultima modifica alle 13:53, prima dei gate verdi, quindi i gate restano validi;
>   - le due pagine (14:16 e 14:18) le ho rilette: sono complete, coerenti col codice e senza frasi vecchie rimaste (verificato con grep), e `importWizard.pluginRequired` e l'ordine degli avvisi esistono come la doc li descrive;
>   - ho rifatto il passo interrotto, cioè i gate della doc: `mkdocs build` strict exit 0 con 0 WARNING/ERROR; `check-links` 81 validi, i 3 gialli noti e il solo rosso D28.
> - **Controlli finali**: `git diff --check` pulito; Prettier `--check` sui 4 file del frontend pulito; privacy 0 collisioni su 745 righe aggiunte; porte 6156 e 6166 libere.

### 17.7 ✅ H — pronta per il checkpoint (2026-10-06)

- Poi il secondo giro di review sulla 6166, da capo, dopo il checkpoint.

> **Commit di H** (developer, verificati dal coordinatore): `aa9c62291` fix, `c58e72368` docs, `97259ce7f` journal; `~3` = `af5591991`, albero `ddfb5a782`.
> - Le correzioni ai messaggi, chieste da L: «every file keeps its tick» in C1, l'oggetto di C2 `docs(import): one by one keeps each file's tick`, e in C3 il gate in più del fix di `SearchSelect`.

## 18. La voce 8: «scrivendo CSV il primo risultato è Generic CSV» (2026-10-06), analisi senza codice

**La nota del developer** (testuale, dalle verifiche sul server nightly `049d36c8d`, senza G, tramite il coordinatore): «sui file uplodati si, quelli già analizzati mostrano solo il plugin già usato!».

### 18.1 ✅ Dove e perché

- **Dove**:
  - nel wizard, «Seleziona file», la colonna Plugin è un `ImportPluginSelect` filtrato sui `compatible_plugins` del file (T5: «only show these plugins»);
  - la select del broker, cioè il plugin predefinito di `BrokerForm`, mostra invece tutto il catalogo, e lì «CSV» → Generic CSV primo funziona (R13, ordinamento di K).
- **La causa verificata**:
  - `compatible_plugins` si calcola **una volta, al caricamento** (`save_uploaded_file`, `brim_provider.py:711`), col `can_parse` che ogni plugin ha in quel momento, e si salva nei metadati;
  - **non si ricalcola mai**: né all'analisi (`_move_file` cambia `status`, `processed_at` e `parsed_plugin_code`) né alla lettura (`:800` lo restituisce com'è salvato). L'unica eccezione sono i file combinati (`:1143`), già esclusa dal coordinatore;
  - nessuna logica del frontend riduce i file analizzati al plugin usato: la colonna Plugin del nightly (`git show 049d36c8d`) è identica a quella attuale.
  - Quindi «un file analizzato mostra solo il plugin già usato» vuol dire che, quando è stato caricato, solo quel plugin lo accettava.
- **Il perché più probabile, da confermare**: i file analizzati sono stati caricati con una versione più vecchia.
  - Fino al 28/09 (`9d9c26d0d`, il lettore di base col ripiego cp1252), il `can_parse` del Generic CSV apriva il file in UTF-8 stretto e dava `False` a ogni errore. Un export Windows-1252 o Latin-1, tipico di broker e banche europee e motivo della correzione `6ea71ea8d`, non riceveva il Generic CSV;
  - lo stesso vale per XLSX e XLS, perché il generico legge solo `.csv` (voluto);
  - i file caricati sul nightly invece ricevono il generico: prima di G, qualunque CSV con una prima riga leggibile;
  - i campioni sintetici sono UTF-8 e non lo mostrano: il vecchio generico rifiutava solo i 2 CSV Latin-1 di Danske.
  - **Per confermarlo**: i `compatible_plugins` di un file analizzato (DevTools → Network → `GET /api/v1/brokers/import/files`), la sua data di caricamento e la codifica o il formato.

### 18.2 ✅ Col codice attuale, con G

- Il Generic CSV si propone solo se l'intestazione nomina `date` e `type` (alias multilingue).
- Sui campioni, `/tmp/libreFolio_l_item8_samples.py` dà **49 elenchi su 56 con un solo plugin**: un export di broker appena caricato offre solo il suo plugin. Generic CSV compare per i 7 campioni generici e per 7 dei broker (bitvavo, cointracking, etoro, parqet, revolut ×2, schwab).
- Quindi con G «un solo plugin» diventa **il caso normale** per gli export di broker, per scelta (decisione 1 di G: il generico non si propone dove non sa leggere, e se forzato dice quale colonna manca).
- La voce 8 resta verificabile nella select del broker e, nel wizard, sui file che il generico legge.

### 18.3 ✅ Voluto o difetto?

- **Il filtro sui `compatible_plugins` è voluto** (T5).
- **L'elenco congelato al caricamento è un difetto**: è la voce 7 del backlog di G, la stessa radice. Le conseguenze, con G:
  1. i file caricati **prima di G** tengono il Generic CSV anche dove non sa leggere, e sceglierlo fallisce col motivo (G.5): chiaro, ma evitabile;
  2. i file cp1252 caricati **prima del 28/09** non elencano il generico, anche quando con G potrebbe leggerli (cioè hanno `date` e `type`);
  3. **il più serio per l'alpha**: un plugin arrivato **dopo** il caricamento non viene mai offerto per quel file. E siccome `setPluginFor` (frontend) e `collect_members` (server) leggono proprio `compatible_plugins`, un export Danske caricato prima del plugin Danske **non entra mai in un set**: bisogna ricaricarlo.

### 18.4 ⏳ Opzioni per la correzione, da decidere col developer (niente codice adesso)

| Opzione | Cosa | Superfici e costo |
|---|---|---|
| **A (consigliata)** | Rilevare di nuovo quando i plugin cambiano: insieme all'elenco si salva una firma del catalogo (codici più `plugin_version`); quando si elencano i file, gli originali con la firma vecchia vengono ricalcolati fuori dall'event loop e riscritti in modo atomico | `brim_provider.py` (salvataggio e lettura), forse l'endpoint della lista; test di servizio (firma vecchia → ricalcolo; firma uguale → niente) e API. Un `can_parse` per file vecchio dopo ogni cambio di plugin, trasparente per l'utente |
| B | Un'azione manuale «Rileva di nuovo i plugin» (pagina File o wizard) | Più economica, ma l'utente deve saperlo |
| C | Lasciare com'è e documentarlo | Nessun costo; i file vecchi restano coi loro elenchi |

- **Quando** lo decide il developer: prima o dopo il taglio della release. Con A, i file caricati prima dell'aggiornamento si allineano da soli, compresi gli export Danske degli utenti alpha.
- **Nel secondo giro sulla 6166** (DB nuovo, tutto caricato con G) il developer può vedere il comportamento attuale: Generic CSV primo nella select del broker; nel wizard, il generico solo sui CSV con `date` e `type`, e solo il loro plugin sugli export di broker. Il congelamento non si riproduce in una corsia nuova; per mostrarlo bisognerebbe ritoccare a mano i metadati sintetici della corsia di review, cosa che propongo ma non faccio senza permesso.

## 19. Review del passo G, secondo giro (2026-10-06)

### 19.1 ✅ La corsia di review, da capo

- Codice: HEAD `97259ce7f` (H committato; c'è anche il piano, modificato). `front build --debug`; il server dice `v1.1.0-473-g97259ce7f-dirty`, dove `-dirty` è solo il piano.
- Data-dir `/tmp/librefolio-r2-l-review`: un `test --test-port 6166 --data-dir /tmp/librefolio-r2-l-review db populate --force --clean` (autorizzato solo lì; i file passano da 14 a 0), poi gli utenti e `init-settings` come nel primo giro.
- Server: `dev.py server --test --host 127.0.0.1 --port 6166 --data-dir /tmp/librefolio-r2-l-review --no-reload --no-scheduler`; ascolta solo su `127.0.0.1:6166`, login 200.
- File sintetici: gli stessi del primo giro (§17.1), in `/tmp/librefolio-r2-l-review-files/`.

### 19.2 ⏳ Le osservazioni del developer

**Testuali** (secondo giro, prima risposta):

> «piccola nota, appena connesso ho visto in period p&L:
> +91,31 € 🇪🇺 EUR (+-16.36%)
>
> il +- credevo lo avevamo risolto, dobbiamo forse aggiornare la baseline di questa immagine?
>
> cmq appena arrivato all'upload ho caricato danske_bank-cash.csv e danske_bank-custody.xlsx ma facendo avanti mi è comparso
>
> Danske Bank also needs: Securities transactions (XLSX).
>
> Drop it here: it joins the same set. You can also continue: the set will show as incomplete. How to export it
>
> e mi si sono deselezionati entrambi, e xlsx ha anche perso il selettore del broker con il suo stato che è diventato: danske_bank-custody.xlsx: HTTP 500 — Internal Server Error»

### 19.3 ✅ Analisi (2026-10-06)

**V1 — l'upload dell'XLSX con HTTP 500: un difetto vero, non di G, nell'infrastruttura comune.**
- Log del server di review: `POST /api/v1/brokers/import/upload` → 500, `RuntimeError: dictionary changed size during iteration` in `BRIMProviderRegistry.get_compatible_plugins` (`provider_registry.py:447`), chiamato da `save_uploaded_file` (`brim_provider.py:711`, in `asyncio.to_thread`).
- **Il meccanismo** (lettura del codice):
  - il wizard carica i due file in parallelo, su due thread;
  - il catalogo era freddo: prima dell'upload non c'era stata nessuna chiamata a `/brokers/import/plugins`, e all'avvio non c'è riscaldamento;
  - `auto_discover` (`:112`) non ha lock e imposta `_discovery_done` solo alla fine. Il secondo thread salta i moduli che il primo ha già messo in `sys.modules` (prima di `exec_module`), dichiara finita la scoperta e scorre `_providers` mentre il primo sta ancora registrando i plugin.
- **Le conseguenze**: dopo ogni riavvio del server, il primo caricamento di più file può dare 500 su un file. Peggio, un thread può vedere un catalogo **parziale** e salvare un `compatible_plugins` incompleto, che non si ricalcola più (§18).
- **Perché i test non l'hanno visto**: nei test il catalogo è già caldo prima di ogni concorrenza.
- `provider_registry.py` è comune (FX, asset, BRIM; ultima modifica `d54d74189`, 10/09); `dev_release2` è identico.
- **Proposta**:
  - un `threading.RLock` di classe attorno alla scoperta, con doppio controllo di `_discovery_done`;
  - scorrere una copia (`list(cls._providers.items())`) in `get_compatible_plugins`, `auto_detect_plugin` e `list_plugin_info`;
  - facoltativo: scaldare i cataloghi all'avvio;
  - prima il rosso (test-author): due thread su un catalogo freddo, con un modulo plugin lento in una cartella temporanea.
  - Da decidere: il permesso, perché il file è fuori dal perimetro di L.
- **Il «deselezionati entrambi»**: l'XLSX non è stato caricato, quindi la cassa da sola forma un set incompleto e l'avviso «Danske Bank also needs…» è corretto. Da chiarire col developer cosa ha visto deselezionarsi; il file in errore non ha un id sul server, quindi perde la select del broker.

**V2 — «+-16.36%» nel «Period P&L»: un difetto vero, fuori dal perimetro di L, anche su `dev_release2`.**
- `KpiSection.svelte`: `({pnlDeltaDay >= 0 ? '+' : ''}{pnlDeltaDayVsPrevTotalPct}%)`. Il segno segue il delta in denaro (+91,31 €), ma la percentuale è relativa al totale precedente: quando quel totale è negativo la percentuale è negativa, e il risultato è «+» seguito da «-16.36».
- Il file è identico su `dev_release2` (ultima modifica `53219bc00`, 30/09), quindi aggiornare la baseline non lo risolve. Va al coordinatore, che sa se un ramo non ancora integrato lo corregge.
- C'è anche una domanda di senso: una percentuale su una base negativa o zero ha significato?

### 19.4 ⏸ Il secondo giro si ferma qui

- **Decisione del developer** (ask_user, testuale): «Fermiamoci qui: prima si corregge il 500».
- Server di review spento, porta 6166 libera (`lsof` rc=1), nessun processo rimasto.
- **Decisione del coordinatore**: nessun ramo tocca `provider_registry.py` né `KpiSection.svelte`.
  - **V1** lo corregge L, dentro H, in un commit a sé, dopo la chiusura del giro: prima il rosso (test-author: due thread su un catalogo freddo, con un modulo plugin lento), poi `RLock` di classe con doppio controllo e copie di `_providers` nei tre metodi che lo scorrono. **Niente riscaldamento all'avvio**: `main.py` lo toccano la famiglia Risk (lifespan) e M (middleware), e il lock basta per la correttezza. Gate: le suite `services` ed `external` dei provider (BRIM, FX, asset) e gli E2E di import. Va proposta una riga 🐛 di CHANGELOG.
  - **V2**: passato a N (Dashboard), che porta al developer anche la domanda di senso sulla base negativa.
- La **voce 8** (opzioni A/B/C di §18.4) aspetta la scelta del developer.
- Dopo la correzione di V1 si ricomincia il secondo giro, da capo.

### 19.5 ✅ Voce 8: la scelta del developer

- Testuale (ask_user): «A — rilevare di nuovo quando i plugin cambiano (Consigliata)». Il developer non ha indicato il quando, quindi lo chiedo al coordinatore. Serve un piano proprio (analisi → via), dopo V1.

### 19.6 ⏳ V1 — la scoperta dei plugin al riparo dalla concorrenza (dentro H, commit a sé)

**Contratto**:
- `AbstractPluginRegistry.auto_discover` diventa sicura fra thread. Ogni registro ha un suo `threading.RLock`, creato in `__init_subclass__`. Il doppio controllo è: `_discovery_done` letto fuori dal lock, poi di nuovo dentro; la scoperta intera avviene sotto il lock, e `_discovery_done` diventa vero solo alla fine.
  - Un thread che arriva durante la scoperta di un altro aspetta e poi trova il catalogo completo.
  - Il lock è rientrante, quindi un modulo che durante l'import richiama lo stesso registro non si blocca.
  - Il lock per registro non ha rischio di ordine fra lock: nessun modulo plugin interroga un altro registro mentre viene importato (verificato con grep su `brim_providers`, `fx_providers`, `asset_source_providers`, `signal_plugins` e `tool_plugins`).
- In `provider_registry.py` si scorre una copia di `_providers` in **tutti e cinque** i punti: `list_providers` (`:251`), `shutdown_all_providers` (`:263`), `auto_detect_plugin` (`:403`), `get_compatible_plugins` (`:447`) e `list_plugin_info` (`:467`). Il coordinatore ne aveva contati tre.
- Niente riscaldamento all'avvio (decisione del coordinatore: `main.py` è di Risk e M).

**Rosso** (test-author), in `backend/test_scripts/test_services/test_provider_registry_misc.py` (azione `services provider-registry-misc`):
- un registro di prova con la sua cartella di plugin temporanea e un modulo lento;
- due thread, il secondo che entra mentre il primo sta ancora importando: senza la correzione il secondo vede `RuntimeError` o un catalogo parziale; con la correzione tutti e due vedono il catalogo intero;
- una guardia verde: la rientranza nello stesso thread non si blocca.

**Gate**: `services` dei registri e dei provider (BRIM, FX, asset), `external` dei provider (BRIM, FX, asset), gli E2E di import (col `--clean` prima), `lint`.

> **Via del coordinatore** (2026-10-06): d'accordo sui cinque punti a copia e sull'`RLock` per registro. I gate coprono tutti i registri: signal, risk, tool, FX, asset e BRIM, più i test del registro e gli E2E di import. Le suite `external` che vanno in rete non si eseguono e si segnalano come non eseguite. Serve una riga 🐛 di CHANGELOG, poi il checkpoint in un commit a sé.
> - **Voce 8 (A) va nella 1.2, prima del taglio.** Il motivo del coordinatore: con la 1.2 arriva Danske, e chi aggiorna dalla 1.1.0 ha file caricati senza quel plugin, che altrimenti non entrerebbero mai in un set. Dopo V1 si scrive il piano, solo analisi; il via al codice lo porta il coordinatore al developer.

> **Note implementazione — V1 (2026-10-06)**:
> - **Il rosso** (test-author, in `test_provider_registry_misc.py`, 7 casi nuovi): la corsa, deterministica con Event e attese limitate, su un registro di prova che eredita da `BRIMProviderRegistry`, con una cartella temporanea, uno spazio dei nomi unico e moduli registrati con `@register_provider`. Il secondo chiamante dava `RuntimeError: dictionary changed size during iteration` a `provider_registry.py:447`, la stessa riga del 500 vero. Più 5 casi sulle copie, uno per punto che scorre il catalogo (rossi), e una guardia sulla rientranza (verde). Il test-author ha anche provato il contratto su sottoclassi temporanee: ogni metà della correzione è fissata da un suo test.
> - **La cura** (`provider_registry.py`):
>   - `import threading`; `_discovery_lock = threading.RLock()` in `__init_subclass__`;
>   - `auto_discover` col doppio controllo, e la scoperta spostata in `_discover_modules()` sotto il lock. Gli errori si registrano prima di `_discovery_done = True`; il `raise` degli errori avviene fuori dal lock;
>   - `list(cls._providers.items())` nei cinque punti (`:272`, `:284`, `:424`, `:468`, `:488`).
> - **I gate** (corsia 6156, un comando per volta):
>
> | Verifica | Esito |
> |---|---|
> | `services provider-registry-misc` / `provider-registry` / `provider-contracts` | `13` (i 6 rossi sono verdi) / `7` / `405 passed` |
> | `services signal-registry` / `signal-contracts` / `signal-runtime` / `tools-registry` | `65` / `10` / `6` / `93 passed` |
> | `services risk-all test_risk_registry` | `4 passed` (450 non selezionati) |
> | `services brim-provider-base` / `brim-versioning` / `brim-parse-pool` / `brim-parse-race` / `brim-report-sets` / `asset-source` | `34` / `5` / `8` / `14` / `255` / `61 passed` |
> | `external brim-providers` / `brim-danske-bank` (offline, sui campioni) | `626 passed`, 1 saltato / `324 passed` |
> | `external fx-providers` / `asset-providers` / `justetf-multicurrency` | **non eseguiti**: vanno in rete (decisione del coordinatore) |
> | `--clean` autorizzato, poi gli E2E di import | `report-set` 24, `-guide` 2, `handoff` 2, `file-selection` 2, `upload` 9, `flow` 10, `resolution` 12, tutti verdi, con carico 35–50 |
> | **Avvio a freddo, da capo a fondo** (`/tmp/libreFolio_l_v1_coldstart_uploads.sh`): server di test sulla 6156 appena avviato, nessuna chiamata BRIM prima, poi 6 upload in parallelo come fa il wizard | 3 avvii su 3: **6 × 200**, ogni `compatible_plugins` completo e giusto, 0 righe `dictionary changed size` nel log |
> | `api brim` (per ultimo) / `check-orphans` | `73 passed` / pulito |
> | `black --check` e `ruff check` sui due file | puliti |
> | `dev.py lint` | 1 errore **non di L**: C901 in `pac_allocator/normalize.py:461` (`ac18ce097`, 05/10, arrivato con D). I miei file sono puliti |
>
> - I server degli avvii a freddo li ho avviati in shell async collegate e fermati con `stop_bash`, senza `kill`. Dopo ogni avvio, la porta 6156 era libera.
> - **La doc** (docs-writer, solo EN): `developer/architecture/patterns/registry_pattern.md`, un passo 5 «Thread-safe» nel processo di scoperta. `mkdocs build` strict ok; `check-links` col solo D28.
> - **⚠️ Fuori pista — deriva della doc, trovata dal docs-writer e non toccata (per il backlog)**: `registry_pattern.md` cita un `get_provider()` che non esiste (esistono `get_plugin` e `get_provider_instance`), chiama `AbstractProviderRegistry` la base di tutti i registri (la base vera è `AbstractPluginRegistry`), e non elenca `RiskAnalyticRegistry` né `ToolPluginRegistry`. `ToolPluginRegistry` ha anche un suo lock e rifiuta con `RuntimeError` la rientranza durante l'import; `tools-registry` resta verde (93).
> - **CHANGELOG proposto** (🐛 Fixed): `- **Uploading several reports right after LibreFolio starts no longer fails.** The first uploads after a restart could end in an *Internal Server Error* on one file, or record an incomplete list of the plugins able to read it, while the import plugins were still being loaded; loading them is now safe when uploads arrive together.`

### 19.7 ✅ V1 — pronta per il checkpoint (2026-10-06)

- Poi: il piano della voce 8 (A), solo analisi, e il secondo giro di review da capo.
