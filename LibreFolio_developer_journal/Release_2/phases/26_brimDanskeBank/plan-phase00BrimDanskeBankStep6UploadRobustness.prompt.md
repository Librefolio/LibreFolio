# Piano — fase 00, Danske Bank, passo 6: la robustezza dell'upload (F2; F3 e F4 al backlog)

> **Stato**: ✅ chiuso e integrato: `c3e6fa0a8` (fix(files): damaged workbook preview answers 400), con il journal in `2a90c1395` (verifica del 2026-10-09 su `3cceb4f90`). Rinviati: F3, F4 e F3-bis in `Phase_0/38_postReleaseBacklog/README.md`, voce L4.
> - Al checkpoint: ✅ pronta per il checkpoint (2026-10-06, §8.3). Il checkpoint è **solo F2** più il piano: F2 approvato con l'estensione di xlrd (§0), rossi verificati, cura, gate verdi. F3/F4 escono (D1 respinta dal developer: nessuna restrizione sui formati); il `.json` sovrascritto, l'estensione lunghissima e F3-bis vanno nel backlog del coordinatore.
>
> - Viene da: [plan-phase00BrimDanskeBankStep4Implementation.prompt.md](plan-phase00BrimDanskeBankStep4Implementation.prompt.md), §19.10 (i difetti F1–F4 trovati nel secondo giro di review) e §20 (la scelta del developer su F3/F4); [plan-phase00BrimDanskeBankStep5PluginRedetection.prompt.md](plan-phase00BrimDanskeBankStep5PluginRedetection.prompt.md), §8.5 (la voce 8 e F1, committate).
> - Workstream L, issue #26. Ramo `e-alfy-l-danske-bank`, base `b6ac553fc` (L8 sopra la punta di K `7dd5e47e7`); al checkpoint lo script porta L su `dev_release2` = `66506b67c` (`b6ac553fc` più il commit del CHANGELOG), poi committa.

## 0. Decisioni

- **Developer**, su F3/F4 (ask_user, testuale, §20 dello Step4): «422: rifiuta il file con un messaggio chiaro (Consigliato)».
- **Coordinatore**, l'assegnazione (dallo Step4): F3 e F4 nella 1.2, prima del taglio, con una concessione su `brokers.py` per la validazione dell'estensione nell'upload; prima i rossi (`.json`, `.JSON`, `custom_filename` con `.json`, un'estensione lunghissima). F2 è di L, in `file_preview.py`, e la mappatura deve valere anche per `uploads.py`, che importa lo stesso modulo. Un checkpoint di «robustezza dell'upload», con una riga 🐛 di CHANGELOG per ogni punto che l'utente vede.
- **Coordinatore**, 2026-10-06, dopo l'analisi di §1 (testuale):
  > «**F2 approvato come consigli**: le 4 famiglie, prese solo attorno alle due chiamate pandas, in `UnreadablePreviewError(ValueError)`. API invariate; un rosso anche via `uploads.py`. Parti coi rossi di F2 (test-author).»
  >
  > «L'elenco dei formati e gli upload generici li porto ora al developer e ti giro le risposte. Fino ad allora non toccare il codice di F3/F4, né `static_uploads.py`/`uploads.py`.»
- **Coordinatore**, 2026-10-06, le risposte (testuale, con la frase del developer):
  > «**Estensione di F2: sì.** `CompDocError`, `IndexError` e `struct.error` entrano nella famiglia di xlrd, sempre e solo attorno alle due chiamate pandas, più i 3 casi di test.»
  >
  > «**Il developer non vuole restrizioni sui formati.** Testuale: "non credo sia questa la strada, come è ora è corretto, segnamoci che dobbiamo risolvere il json per un futuro in cui generalizziamo generic csv, ma va bene uplodare e poi non parsare". Quindi F3/F4 escono dal checkpoint: nessuna validazione delle estensioni, il caricamento resta com'è. Il `.json` sovrascritto e l'estensione lunghissima vanno nel mio backlog.»
  >
  > «**Upload generici: backlog**, insieme al `.json` dell'import, perché la causa è la stessa: dati e metadati hanno lo stesso nome. `static_uploads.py` e `uploads.py` restano intoccati.»
  >
  > «Il checkpoint quindi è solo F2 più il piano, con la riga di CHANGELOG di F2; quella di F3+F4 cade.»
  >
  > «**Dopo F2:** il bottone e R6, prima l'analisi. La domanda su R6 per il developer la prepari tu.»

## 1. Stato verificato (2026-10-06, sul codice a `b6ac553fc`)

Sola lettura, più due sonde su file sintetici in cartelle temporanee, senza server (`files/upload-robustness/` nella sessione).

### 1.1 F2 — l'anteprima di una cartella Excel danneggiata risponde 500

- I due endpoint di anteprima chiamano `build_preview_response` di `file_preview.py` e mappano `UnsupportedPreviewError` e `ValueError` → 400, tutto il resto → 500 «Failed to build file preview»: `brokers.py` (`get_brim_file_preview`) e `uploads.py` (`get_upload_file_preview`).
- `_read_excel_preview` mappa solo `ImportError` (→ `UnsupportedPreviewError`). La sonda: 7 file danneggiati, **tutti 500 oggi**, e nessuno solleva un `ValueError`:

  | File sintetico | Eccezione |
  |---|---|
  | byte a caso con nome `.xlsx`; un `.xlsx` valido troncato a metà; un CSV con nome `.xlsx` | `zipfile.BadZipFile` |
  | uno zip vuoto; uno zip con solo un `readme.txt` (nome `.xlsx`) | `KeyError` («There is no item named '[Content_Types].xml'…») |
  | un `.xlsx` con l'XML del foglio rovinato | `xml.etree.ElementTree.ParseError` (un `SyntaxError`) |
  | byte a caso con nome `.xls` (motore `xlrd`) | `xlrd.biffh.XLRDError` |

- Il solo `BadZipFile` ne avrebbe sistemati 3 su 7: da qui le 4 famiglie.
- **Un residuo sui `.xls`** (seconda sonda, sul campione pubblico già nel repo, `backend/staticResources/FilePreviewSamples/file_example_XLS_10.xls`, rovinato in sei modi): con le 4 famiglie solo i byte invertiti diventano 400. Troncato al 5% → `struct.error`; al 25, 50 o 90% → `IndexError`; directory azzerata → `xlrd.compdoc.CompDocError`, che non è un `XLRDError`. Restano 500 → D3 in §5.
- `uploads.py` è raggiungibile: l'upload generico ha solo un elenco di estensioni *vietate* e accetta un `.xlsx` qualsiasi.

### 1.2 F3/F4 — l'estensione dell'upload BRIM

- `save_uploaded_file`: `ext = Path(original_filename).suffix.lower() or ".dat"`; scrive prima i dati in `{id}{ext}`, poi il sidecar in `{id}.json`. Con `.json` il sidecar sovrascrive i dati (perdita); con un'estensione di 300 caratteri `OSError` → 500.
- Il nome viene da `custom_filename` (la rinomina nel wizard) oppure da `file.filename`: conta anche la rinomina.
- L'unione delle `supported_extensions` dei plugin è oggi `.csv` e `.xlsx`. Nessun plugin legge `.xls`, `.txt`, `.json` o `.dat`.
- I tre selettori del frontend (wizard, `BrokerImportFilesModal`, il caricatore BRIM di /files) hanno `accept=".csv,.xlsx,.xls"`, statico.
- Il wizard mostra, per ogni file, il `detail` della risposta (`trySave` → `errorMessage`): un 422 col suo messaggio arriva all'utente, come oggi il 413 e il 400 «Empty file».
- `populate_mock_data.py`: i campioni BRIM sono tutti `.csv`; i campioni `.md`/`.txt` vanno negli upload generici. Nessun effetto.

### 1.3 F3-bis/F4-bis — lo stesso difetto negli upload generici (non di L)

- `static_uploads.save_upload` usa lo stesso schema: dati in `{id}{ext}` e metadati in `{id}.json`, nella stessa cartella; `.json` non è fra le estensioni vietate. La sonda: resta un solo file, quello dei metadati.
- Un'estensione di 300 caratteri: `OSError` → `uploads.py` → 500 «Failed to save file».
- Raggiungibile dalla UI: il caricatore «statico» di /files non ha `accept`.
- Fuori dalla concessione di L: proprietario e forma li decide il coordinatore con il developer (§5).

## 2. Il contratto di F2

- Nuova `UnreadablePreviewError(ValueError)` in `file_preview.py`: una sottoclasse diretta di `ValueError`, non di `UnsupportedPreviewError` (il formato è supportato, è il file a non leggersi).
- In `_read_excel_preview`, **solo attorno alle due chiamate pandas** (`pd.ExcelFile`, `pd.read_excel`), si prendono esattamente `zipfile.BadZipFile`, `KeyError`, `xml.etree.ElementTree.ParseError` e la famiglia di xlrd: `xlrd.XLRDError`, `xlrd.compdoc.CompDocError`, `IndexError`, `struct.error` (D3 accettata; import di `xlrd` protetto). Si solleva `UnreadablePreviewError(<una frase in inglese>) from <originale>`: il dettaglio resta nella catena, per i log.
- Restano come sono: `ImportError` → `UnsupportedPreviewError`; «Sheet 'X' not found» resta un `ValueError` semplice; ogni altra eccezione passa (→ 500).
- Le API non cambiano: i due endpoint rispondono 400 perché il nuovo errore è un `ValueError`.

## 3. Superfici

| Superficie | Proprietà | Per |
|---|---|---|
| `backend/app/services/file_preview.py` | L (assegnato) | F2 |
| `backend/test_scripts/test_services/test_file_preview.py` (`services file-preview`) | test-author | F2 |
| `backend/test_scripts/test_api/test_brim_api.py` (`api brim`) | test-author | F2 |
| `backend/test_scripts/test_api/test_uploads_api.py` (`api uploads`) | test-author, in aggiunta (file comune) | F2 |
| ~~`brim_provider.py`, l'upload in `brokers.py`~~ | — | F3/F4: **usciti** (D1 respinta) |
| ~~`static_uploads.py`, `uploads.py`~~ | — | F3-bis: **backlog**, intoccati |

Nessuna registrazione nuova nel runner: i tre selettori esistono già. Il frontend non cambia.

## 4. I test, rossi prima (test-author)

- `test_file_preview.py`:
  - la classe esiste, è un `ValueError` e non un `UnsupportedPreviewError`;
  - **10 casi** parametrizzati: i 7 di §1.1 più i 3 `.xls` di D3, ricavati dal campione pubblico già nel repo (troncato al 5% → `struct.error`, al 50% → `IndexError`, directory azzerata → `CompDocError`). `build_preview_response` solleva la nuova classe, con l'eccezione originale come causa;
  - guardie: il foglio mancante resta un `ValueError` semplice; `ImportError` → `UnsupportedPreviewError`; un `RuntimeError` passa invariato (la presa è stretta).
- `test_brim_api.py`: una categoria nuova; un `.xlsx` danneggiato e uno col foglio rovinato, caricati su un broker del test → l'anteprima risponde 400 (oggi 500).
- `test_uploads_api.py`: un `.xlsx` danneggiato negli upload generici → l'anteprima risponde 400 (oggi 500).
- ~~F3/F4~~: nessun test (D1 respinta).

## 5. Decisioni

- **D1 — l'elenco dei formati BRIM: ❌ respinta dal developer** (testuale, portato dal coordinatore): «non credo sia questa la strada, come è ora è corretto, segnamoci che dobbiamo risolvere il json per un futuro in cui generalizziamo generic csv, ma va bene uplodare e poi non parsare». Il caricamento resta com'è: nessuna validazione delle estensioni. F3 (il `.json` sovrascritto dal sidecar) e F4 (l'estensione lunghissima → 500) passano al backlog del coordinatore.
- **D2 — F3-bis/F4-bis (upload generici): backlog**, insieme al `.json` dell'import, perché la causa è la stessa: dati e metadati hanno lo stesso nome. `static_uploads.py` e `uploads.py` restano intoccati.
- **D3 — il residuo `.xls` di F2: ✅ sì.** `CompDocError`, `IndexError` e `struct.error` entrano nella famiglia di xlrd, solo attorno alle due chiamate pandas, più 3 casi di test.
- Restano note per il backlog: l'`accept` statico dei tre selettori del frontend (`.xls` compreso) e i `.json` già caricati, che restano rotti (i dati sono andati persi al caricamento).

## 6. CHANGELOG proposto (lo scrive il coordinatore all'integrazione)

- 🐛 F2: `- Previewing a damaged Excel file now says the file cannot be read, instead of failing with a server error.`
- ~~🐛 F3+F4~~: cade con D1.

## 7. Gate e definizione di fatto

- I rossi rossi sul loro punto, poi verdi; le guardie verdi prima e dopo.
- `services file-preview`, `api brim`, `api uploads`. Niente E2E: cambia solo la risposta a un file danneggiato (500 → 400), nessun file del frontend.
- `dev.py lint`; black e ruff sui file toccati; scanner di privacy; `git diff --check`; porta 6156 libera.
- Il checkpoint: F2 più i piani (Step5 §8.5, questo Step6).

## 8. Avanzamento

### 8.0 ✅ L'analisi (2026-10-06)

- §1, mandata al coordinatore insieme alla validazione di L8 (Step5 §8.5). F2 approvato come consigliato; D1 e D2 portati al developer; D3 chiesta dopo la seconda sonda.
- Risposte: D1 respinta, D2 al backlog, D3 sì (§0, §5). Il checkpoint si restringe a F2.

### 8.1 ✅ F2 — i rossi (test-author, 2026-10-06)

> **Note implementazione** (log nella sessione, `files/f2-reds/`):
> - `test_file_preview.py`:
>   - `test_unreadable_preview_error_is_a_value_error_and_not_an_unsupported_one`;
>   - `test_damaged_workbook_preview_raises_unreadable_preview_error`, con 10 casi: 7 sintetici e 3 dal campione `.xls` pubblico. Ogni caso nomina il motore e chiama `pytest.importorskip`;
>   - 3 guardie: `test_missing_sheet_stays_a_value_error_of_its_own`, `test_missing_excel_engine_stays_an_unsupported_preview_error`, `test_unexpected_reader_error_escapes_unchanged`.
> - `test_brim_api.py`: categoria 15, `TestDamagedWorkbookPreview`, **RS-F201**, con 2 casi (`not-a-zip`, `unparseable-sheet-xml`). Un utente e un broker per caso, cancellati nel `finally`.
> - `test_uploads_api.py`: **UPLOAD-005H** (`test_damaged_xlsx_preview_returns_400`), che cancella il suo file nel `finally`.
>
> | Comando (corsia 6156) | Esito, prima della cura |
> |---|---|
> | `services file-preview` | 11 rossi, ciascuno sul suo tipo (BadZipFile ×3, KeyError ×2, ParseError, XLRDError, struct.error, IndexError, CompDocError al posto di `UnreadablePreviewError`; la classe mancante); 15 verdi (12 esistenti + 3 guardie) |
> | `api brim` | 2 rossi (RS-F201: 500 invece di 400), 76 verdi |
> | `api uploads` | 1 rosso (UPLOAD-005H: 500 invece di 400), 23 verdi, 1 saltato (UPLOAD-013, già prima) |
>
> Nessun errore di raccolta: la classe nuova si legge con `getattr`. Black e ruff puliti.
>
> **⚠️ Fuori pista**: i 3 casi `.xls` di D3 sono arrivati con un seguito al test-author, a metà lavoro; il primo giro aveva i 7 casi.

### 8.2 ✅ F2 — la cura (2026-10-06)

> **Note implementazione**:
> - `file_preview.py`, 26 righe:
>   - `UnreadablePreviewError(ValueError)`;
>   - l'import protetto di `xlrd` (`XLRDError`, `CompDocError`), in cima, come `magic` in `static_uploads.py`;
>   - `_UNREADABLE_WORKBOOK_ERRORS`, con 7 classi;
>   - un messaggio solo;
>   - un `except` dopo quello di `ImportError`, in ciascuna delle due prove attorno a pandas.
>
>   API e frontend invariati; nessuna pagina di doc descrive gli errori di anteprima. `xlrd` è già una dipendenza (`Pipfile:51`).
> - **⚠️ Fuori pista**: la prima versione importava `xlrd` dentro una funzione, e ruff (PLC0415) l'ha rifiutata; ora l'import sta in cima. Su quella prima versione: `api brim` **78 passed**, `api uploads` **24 passed**, 1 saltato. Il giro finale li ripete sul codice definitivo.
> - Una guardia in più, chiesta al test-author: `test_caught_type_raised_outside_the_pandas_calls_escapes_unchanged` (`[key-error]`, `[index-error]`). Un `KeyError` o un `IndexError` sollevato **fuori** dalle due chiamate (da `_dataframe_to_rows`) esce invariato, quindi la presa resta stretta.
>
> | Gate finale, sul codice definitivo (corsia 6156, un comando per volta; log nella sessione, `files/f2-cure/`) | Esito |
> |---|---|
> | `services file-preview` | **28 passed**: 12 esistenti, la classe, i 10 casi, 5 guardie |
> | **Controprova della guardia di ambito**: la presa allargata per un momento attorno a `_dataframe_to_rows` | rossi **esattamente** i 2 casi della guardia (26 verdi); file ripristinato, hash verificato (`6b87acbc7`) |
> | `api uploads` / `api brim` | **24 passed**, 1 saltato (UPLOAD-013, già prima) / **78 passed** |
> | `dev.py lint`; black e ruff sui 4 file Python | puliti |
> | `check-orphans` | pulito |
> | scanner di privacy contro `b6ac553fc` (file non tracciati compresi) | 546 righe aggiunte, 0 collisioni |
> | `git diff --check`; porta 6156 | pulito; libera |

### 8.3 ✅ F2 — pronta per il checkpoint (2026-10-06)

- Delta: 4 file Python (`file_preview.py` e i 3 file di test), il piano Step5 (§8.5) e questo piano, nuovo.
- Il `CHANGELOG.md` lo scrive il coordinatore, con la riga di §6.
- Dopo F2 viene il bottone «Escludi dall'import», da togliere, insieme a R6: prima l'analisi, con la domanda su R6 per il developer (Step4 §22).
