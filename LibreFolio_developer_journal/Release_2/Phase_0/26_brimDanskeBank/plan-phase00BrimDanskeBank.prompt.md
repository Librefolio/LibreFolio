# Piano Phase 00 — BRIM Danske Bank: pilota multi-report + fix della codifica CSV

**Creato**: 2026-09-28
**Baseline/target**: `ea30d5ccf99e918a84ebd49bd5e65fb0f50a9628` (`dev_release2`), HEAD verificato
**Workstream**: L — ramo `e-alfy-l-danske-bank`, worktree `LibreFolio-worktrees/e-alfy-shiny-train`
**Coordinator**: sessione `c8328a01-f208-4ade-a352-0486d1f14de2`
**Runtime lane**: porta `6156`, data dir `/tmp/librefolio-r2-l` (la porta di review `6166` non si usa)
**Issue**: #26 (autore `jaska087`). Allegati letti in sola lettura; nessun valore reale qui dentro.
**Autorizzazione developer**: il 2026-09-28 il developer ha approvato il piano in questa sessione (uscita dal plan mode). Il messaggio successivo del coordinatore mi ha riportato in plan mode, quindi lo ripresento aggiornato per la conferma.
**Coordinatore, 2026-09-28**:
- nessun conflitto sui file dello Step 1 in nessun worktree;
- D11: il wizard dei set lo faccio io, dopo il merge di K in `dev_release2`;
- lo Step 1 va in due commit suoi (base, poi plugin), prima del resto.
**File collegati** (stessa cartella):
- [analysis-phase00BrimDanskeBank.md](analysis-phase00BrimDanskeBank.md): l'analisi degli export, senza valori;
- [issue26-reply.en.md](issue26-reply.en.md): la risposta pubblicata dal developer sulla issue il 2026-09-28;
- [design-phase00BrimReportSets.md](design-phase00BrimReportSets.md): lo Step 2, in bozza e in attesa della revisione del developer.

## 0. Decisioni del developer (verbatim)

| Tema | Decisione |
|---|---|
| Perimetro dei set | «L scrive prima solo il documento di design dei set; l'implementazione si decide dopo» |
| Pilota | «per ora facciamo il lavoro pilota su danske bank, poi lo estenderemo a CA e capiremo il da fare.» |
| Bug | «riguardo al bug, ben fatto, risolviamola in questa sessione, così quando faremo merge, tutti ne beneficieranno.» |
| Portata del fix | «Estesa: una funzione di lettura comune nella classe base, usata da tutti i plugin CSV, più il test sui campioni ri-salvati in Windows-1252» |
| Architettura | Va ripensata per più file: come raggrupparli fisicamente e come scegliere le righe. Una riga che si aspetta una controparte nell'altro file e non la trova va esclusa dalle transazioni estese. |
| Interfaccia e guida | Guidare l'utente: nella guida, come si esportano i file e il fatto che i periodi devono coincidere. Le righe senza controparte vengono ignorate. |
| `api sync` | È automatico: resta fuori dal piano. |
| Campione sintetico | «rispetto al file sintetico per i test, il permesso te lo do io non serve chiederlo» (2026-09-28). I campioni si possono creare subito, sempre costruiti a mano con valori inventati. |

## 1. Stato verificato

Il dettaglio è in [analysis-phase00BrimDanskeBank.md](analysis-phase00BrimDanskeBank.md).

**I due file**

- Tutti e due vengono da Danske Bank **Finlandia** (in finlandese) e sono le due facce della stessa OST
  (osakesäästötili), che ha un conto cassa e un deposito titoli [vero.fi].
- **XLSX, deposito titoli**:
  - 11 colonne. Le date sono testo `dd.mm.yyyy`. Un header contiene HTML letterale (`Palkkio<br/>sis. Alv`). La colonna H non ha nome ed è la valuta di `Summa`.
  - Il file è ri-salvato con LibreOffice.
  - `Toimeksiantotyyppi` è il tipo d'ordine (`Rajakurssi`, `Päivän kurssi`, `Pikakauppa`) oppure l'evento (`Tuotto`, `Jakautuminen, vanha/uusi`). La direzione viene dal segno di `Määrä`.
  - `Kurssi` è nella valuta di quotazione, che il file non dichiara. La commissione sembra inclusa in `Summa` (la colonna `Palkkio` vale sempre 0).
- **CSV, conto cassa**:
  - ISO-8859-1, `;`, senza quoting, LF, righe dalla più recente.
  - Colonne: `Pvm`, `Saaja/Maksaja`, `Määrä` (importo), `Saldo`, `Tila` (sempre `Toteutunut`), `Tarkastus` (sempre `Ei`).
- **Sovrapposizione**: ogni riga XLSX con `Summa` ha la sua gemella nel CSV (`Pvm` = `Arvopäivä`, importo = `Summa`). Solo il CSV ha versamenti, prelievi, la ritenuta sul prelievo e i canoni.

**Codice**

- `TXCreateItem` non ha un campo prezzo; `date` è la data di regolamento.
- ID finti positivi alti; `BRIMNotice` con `code`; `BRIMFieldTodo`.
- La suite BRIM è una sola (`test_brim_providers.py`) ed è l'unico file eseguito dal runner.
- **Bug**: `BRIMProvider.detect_csv_delimiter` apre il file solo come UTF-8.
  - Su un file ISO-8859-1 separato da `;` restituisce `,` (verificato su un file sintetico).
  - **27 plugin (31 punti) aprono il file con `open(..., encoding="utf-8-sig")`**: con Latin-1 o Windows-1252 falliscono comunque.
  - `_brim_io` (Intesa, CA, Directa) prova già più codifiche.
  - 17 campioni hanno caratteri non ASCII. Uno (`degiro-export.csv`) contiene U+202F, che non si può codificare in Windows-1252.
- **Prezzi**: Yahoo cerca per nome e trova le quotazioni nordiche (`.HE`, `.ST`, `.CO`) ma anche ADR e OTC. Il prezzo è coperto; l'ambiguità sta nella scelta della quotazione.
- **Favicon**: `https://danskebank.fi/favicon.ico` risponde 200 senza CORP, quindi si può incorporare.

## 2. Architettura proposta: il «report set» (pilota Danske, poi CA)

> **Aggiornamento 2026-09-28**: questa sezione è la prima bozza (manifest del set più `parse_set`, l'alternativa «A»). Il [documento di design](design-phase00BrimReportSets.md) la confronta con un'alternativa «C», il file combinato derivato, e consiglia la C. Fa fede il documento di design.

Il modello di oggi è **un file = un import autosufficiente**. Le banche che fanno anche da broker (CA, Danske, forse Intesa) spezzano però un conto in più export: ciascuno è parziale, e in parte si sovrappongono e in parte si completano.

Il set rende esplicita questa realtà. Lo schema qui sotto è il contenuto che il documento di design (step 2) deve sviluppare e far approvare.

### 2.1 Concetti

- **Ruolo**: un tipo di export che il plugin conosce. Per Danske: `custody` (XLSX transazioni titoli) e `cash` (CSV conto cassa). Ogni ruolo ha estensioni, un rilevatore e un flag di obbligatorietà.
- **Set**: i file di **un** broker e **un** plugin, ognuno con il suo ruolo. È *completo* quando ci sono tutti i ruoli obbligatori. Per Danske sono obbligatori entrambi.
- **Riga accoppiata**: una riga che, per sua natura, deve avere una controparte nell'altro file. Esempi: un trade XLSX e il suo `Osto`/`Myynti` nel CSV; un `Tuotto` e il relativo accredito.
- **Riga autonoma**: una riga che esiste in un solo file. Esempi: versamenti, prelievi, tasse e canoni nel CSV; la scissione nell'XLSX.
- **Periodo comune**: l'intersezione dei periodi coperti dai file, calcolata sulle date valuta.
- **Transazioni estese**: l'output del set. Sono le coppie fuse in una transazione sola più le righe autonome. Tutto quello che si esclude viene dichiarato.

### 2.2 Raggruppamento fisico

- **Proposta**: un **manifest del set** in `broker_reports/sets/{set_id}.json`, scritto in modo atomico come i metadati di oggi. Contiene broker, plugin, membri `{file_id, ruolo}`, stato (`incompleto`/`pronto`/`parsato`/`fallito`), versione del plugin e cache dell'output combinato.
- I file membri **restano dove sono**, con il loro ciclo di vita e le protezioni dalle race già esistenti. Ricevono solo un riferimento `set_id` nei metadati.
- La pagina dei file mostra il set come **una riga espandibile**, con gli originali scaricabili.
- Alternative scartate:
  - spostare i file in una cartella per set: rompe gli stati e le protezioni dalle race;
  - un «file virtuale» senza manifest: non salva il combinato.

### 2.3 Contratto del plugin (compatibile con oggi)

- Nuovo campo `report_roles`: `[]` per i plugin single-file, cioè tutti quelli di oggi, che restano invariati.
- `detect_role(path) → ruolo | None`, usato anche da `can_parse`.
- `describe_member(path) → {ruolo, date_min, date_max, righe}`. Serve all'interfaccia per mostrare i periodi **prima** del parse.
- `parse_set(parti: {ruolo: path}, broker_id) → BRIMParseOutput`, con la **stessa forma** dell'output di oggi. A valle (asset, correzioni, duplicati, bulk editor) il wizard non cambia.
- Un plugin a set chiamato su un file solo restituisce un output vuoto più una notice bloccante: «manca il file X».
- Regola del round G: la logica di abbinamento resta **dentro Danske** per il pilota. Si estrae in un helper comune solo quando CA diventa il secondo utilizzatore. Sono generici fin da subito i ruoli, il manifest, l'API e l'interfaccia.

### 2.4 Regole di selezione delle righe (il motore di abbinamento)

- **R1 — Classificazione per ruolo** (tabella Danske al §3).
- **R2 — Chiave di abbinamento**: data valuta + importo (a 0,01) + valuta del conto + direzione coerente (`Osto` ↔ quantità > 0 e cassa < 0) + nome compatibile. Il testo del CSV deve essere uguale al nome dell'XLSX o un suo prefisso, perché nel CSV il testo può essere troncato.
- **R3 — Abbinamento uno a uno**:
  - candidati identici (stesso nome, quantità e importo): si accoppiano in ordine di file;
  - candidati diversi e non distinguibili: si escludono entrambi, con un warning. Mai tirare a indovinare.
- **R4 — Riga accoppiata senza controparte**: esclusa dalle transazioni estese. Compare in una notice con un'evidenza per riga (file, riga, data, testo, importo).
- **R5 — Fuori dal periodo comune**: esclusa anche la riga autonoma (proposta, vedi D1). Motivo: un versamento tenuto e l'acquisto corrispondente escluso gonfierebbero la cassa. Una notice informativa mostra i due periodi e i conteggi degli esclusi.
- **R6 — Tipo o etichetta sconosciuta**: esclusa con un warning e le evidenze, mai in silenzio (lezione della beta CA).
- **R7 — Assemblaggio**:
  - una coppia diventa **una** transazione: quantità e asset dall'XLSX, cassa uguale sui due lati, data valuta;
  - descrizione deterministica, così i re-import vengono riconosciuti come duplicati;
  - provenienza da entrambe le righe.
- **R8 — Riconciliazione**: la cassa ricostruita deve seguire il `Saldo` del CSV. Una notice dice «riconciliata», oppure «differenza X dovuta a N righe escluse».
- **R9 — Saldo iniziale**: il `Saldo` prima della prima riga del periodo compare in una notice, con l'evidenza. Nessuna transazione automatica, come CA (vedi D9).

### 2.5 Provenienza

- `BRIMEvidence` e `BRIMValidationIssue` guadagnano una sorgente per riga, cioè ruolo o `file_id`. Il bottone «riga N nel file» apre così il file giusto.
- È una modifica di schema: il client si rigenera da solo.

### 2.6 API e storage

- Endpoint dei set:
  - crea, con validazione di ruoli, completezza, stesso broker e permesso EDITOR;
  - leggi;
  - sostituisci un membro;
  - elimina;
  - `POST …/sets/{id}/parse`, che restituisce `BRIMParseResponse` come oggi.
- Duplicati e asset si calcolano come oggi.
- Gli endpoint dei file restano tutti invariati.

### 2.7 Interfaccia (wizard)

- **Scelta dei file**: se un file è un ruolo di un plugin a set, il wizard mostra una **card del set**:
  - uno slot per ruolo, ✅ o ⛔;
  - il periodo di ogni file;
  - il periodo comune;
  - un avviso se i periodi non coincidono: «le righe senza controparte saranno ignorate»;
  - il link alla guida.
  - **Senza tutti i ruoli obbligatori non si prosegue.**
- **Parse**: il set entra come **un risultato unico** nell'elenco dei risultati (con i `fileId` dei membri). I passi successivi del wizard restano invariati.
- **Evidenze**: aprono l'anteprima del membro giusto.

### 2.8 Guida utente

- Come si esportano **entrambi** i file, con i percorsi di menu che fornirà l'autore.
- Bisogna usare **lo stesso periodo** per i due file, e per il primo import partire dall'apertura del conto.
- Cosa succede alle righe senza controparte.
- Re-import sovrapposti sono sicuri, perché i duplicati vengono rilevati.
- Il saldo iniziale.

### 2.9 CA (dopo il pilota, fuori da questo piano)

- Ruoli `conto` e `titoli`.
- Scompaiono il taglio temporale manuale e buona parte dei blocker sulle quantità.
- Il periodo del conto è limitato a 2 anni, quindi va capito come trattare la storia titoli più vecchia.
- Va gestito chi ha già dati importati con `auto_cash`.

## 3. Mappatura Danske nel set

| Ruolo | Riga | Classe | Tipo LibreFolio |
|---|---|---|---|
| custody | `Rajakurssi` / `Päivän kurssi` / `Pikakauppa`, `Määrä` > 0, `Summa` < 0 | accoppiata | **BUY** (quantità verbatim, cassa `Summa` + valuta colonna H) |
| custody | stessi tipi, `Määrä` < 0, `Summa` > 0 | accoppiata | **SELL** |
| custody | segni incoerenti | — | esclusa + warning |
| custody | `Tuotto` | accoppiata | **DIVIDEND**, quantità 0; la quantità di diritto va nella descrizione |
| custody | `Jakautuminen, vanha` / `uusi` | autonoma | **ADJUSTMENT** −/+ senza cassa, con il costo da decidere (D4) |
| custody | `Tila` ≠ `Toteutettu`, oppure tipo sconosciuto | — | esclusa + notice |
| cash | `Osto <nome>` / `Myynti <nome>` | accoppiata | si fonde con BUY/SELL |
| cash | accredito provento (`<nome> <rif.>`) | accoppiata (**riconosciuta per abbinamento**, niente euristiche) | si fonde con DIVIDEND |
| cash | `Nosto osakesäästötililtä` | autonoma | **WITHDRAWAL** |
| cash | `Vero osakesäästötililtä` | autonoma | **TAX** |
| cash | `Palvelumaksut …` | autonoma | **FEE** |
| cash | altre righe senza abbinamento | autonoma per segno | **DEPOSIT** / **WITHDRAWAL**, con notice informativa |
| cash | `Tila` ≠ `Toteutunut` | — | esclusa + notice |

- **Valuta**: dalla colonna H dell'XLSX; il CSV è nella valuta del conto. Nessuna conversione, e `Kurssi` non si salva: il campo prezzo non esiste.
- **Asset**: chiave = `Sijoituskohde` normalizzato, ID finto, solo il nome. La quotazione la sceglie l'utente.
- **Date**: la data valuta (D5); `Kauppapäivä` va nella descrizione.
- **Commissione**: `Palkkio` diverso da 0 porterebbe una notice e nessuna FEE separata finché l'autore non chiarisce (D14).
- **Lingua**: notice in finlandese, come chiede la guida; i messaggi dei todo in inglese più `reason_code` (D7).
- **Nessun dato sul titolare**: `Säilytystili` si usa solo per controllare che nel file ci sia un deposito solo; non si salva.

## 4. Fix della codifica CSV (versione estesa)

- **Nella classe base** (`brim_provider.py`):
  - una sola costante `TEXT_ENCODINGS = ("utf-8-sig", "cp1252", "latin-1")`;
  - `_read_text(path)` e `_open_text(path)`: uno `StringIO` con newline universali, come fa `open()`;
  - `detect_csv_delimiter` e `_read_file_head` riusano queste funzioni.
- **`_brim_io`**: `detect_delimiter` e `_read_csv_rows` delegano alla base, così l'implementazione è una.
- **27 plugin, 31 punti** (9 dei quali con `newline=""`, che resta: `_open_text(file_path, newline="")`): `open(file_path, encoding="utf-8-sig")` diventa `self._open_text(file_path)`, oppure `BRIMProvider._open_text(...)` nelle 4 funzioni annidate senza `self`. È una modifica meccanica e minima per ogni punto.
- **Con i file UTF-8 l'output non cambia**, perché UTF-8 si prova per primo. Lo provo con un dump prima/dopo dell'output di **tutti** i campioni: deve essere identico. Il dump sta nella cartella di sessione e non si committa.
- `plugin_version` non cambia (D10): per un input già leggibile l'output è lo stesso.
- **Test** (test-author, **rossi prima**, in `test_brim_providers.py`):
  - delimitatore su un CSV Windows-1252 o Latin-1 separato da `;`, con caratteri non ASCII nell'header;
  - ordine delle codifiche (BOM, Windows-1252 con `€`, byte non definito in Windows-1252 che ricade su Latin-1);
  - **invarianza parametrica**: ogni campione CSV ri-salvato in Windows-1252 in `tmp_path` dà lo stesso output (`model_dump`). I campioni non codificabili si saltano con un motivo;
  - guardia: nessun plugin usa più un `open(..., encoding=…)` fisso.
- **Documentazione collegata**:
  - `brim_plugin_guide.md`: la regola «mai una codifica fissa, usa `_open_text`»;
  - la skill `brim-plugin`: una riga.

## 5. Superfici e proprietà

- **Mie (Danske)**:
  - `brim_providers/broker_danske_bank.py`;
  - i campioni sintetici `sample_reports/danske_bank-custody.xlsx` e `danske_bank-cash.csv`;
  - la classe di test `TestDanskeBank*`;
  - `user/transactions/import/danske_bank.en.md`;
  - la cartella journal `26_brimDanskeBank/`.
- **Mie per decisione del developer**: `brim_provider.py` (fix codifica e contratto dei set), `_brim_io.py` (delega), i 27 plugin (solo il punto di apertura), `brim_plugin_guide.md`, `SKILL.md` di brim-plugin.
- **Del pilota, mie** (dopo il gate del design):
  - schemi `schemas/brim.py` (ruoli, set, provenienza);
  - storage ed endpoint dei set;
  - pagina dei file;
  - **wizard** (`ImportWizardModal.svelte` e dintorni): **mio solo dopo che K è entrato in `dev_release2`** e il coordinatore mi ha allineato (merge di `dev_release2` nel ramo, poi rilancio dei gate). Fino ad allora non lo tocco.
- **Condivisi, solo aggiungendo, da elencare nell'handoff**: nav MkDocs, `providers_list.md`, card e tabelle dell'indice ×4, `sample_reports/README.md`. Le eventuali unioni all'integrazione le fa il coordinatore.
- **i18n**: chiavi nuove solo in `importWizard.reportSet.*`, via `dev.py i18n`, in 4 lingue; nessuna chiave esistente toccata.
- **Non mie**: `CHANGELOG.md` lo scrive il coordinatore, io propongo le voci nell'handoff; restano fuori anche i file condivisi del runner.

## 6. Step

> Dopo ogni step: ✅ con data, «Note implementazione», «Fuori pista».

### 0. ✅ Journal e coordinamento — 2026-09-28

- Copiare nel journal questo piano, l'analisi (senza valori) e la bozza **v4** della risposta.
  - La v4 è in prima persona per il developer.
  - Contiene un'apertura che spiega che servono importer multi-file e che è improbabile un rilascio questa settimana, con il ringraziamento per lo spunto; poi le 14 domande concordate; poi il riepilogo.
- ✅ Risposta del coordinatore (2026-09-28):
  - nessun conflitto su `brim_provider.py`, `_brim_io.py`, i 27 plugin, `schemas/brim.py`, `providers_list.md`;
  - D11 risolta;
  - politica dei file condivisi e ordine dei commit ricevuti.

> **Note implementazione**:
> - Creata la cartella `26_brimDanskeBank/` con il piano, l'analisi e la bozza v4.
> - Nell'intestazione dell'analisi il riferimento alla cartella di sessione è sostituito da «fuori dal repo».
> - Controllo dei valori sui file copiati: presenti solo i segnaposto dell'autore (`ACCOUNT_HOLDER_NAME`, `Account_number`), nessuna data né importo reale.
>
> **⚠️ Fuori pista**:
> - La baseline iniziale non coincideva: il worktree era nato da `origin/dev_release2`, 35 commit indietro. Il coordinatore ha preparato il fast-forward a `ea30d5ccf`, poi verificato.
> - Il perimetro è cresciuto su decisione del developer: documento di design dei set, poi il pilota.
> - Un messaggio del coordinatore ha riportato la sessione in plan mode, e il piano è stato riapprovato dal developer.

### 1. ✅ Fix della codifica (§4), in due checkpoint e due commit — 2026-09-28

**1a. Base.** Riguarda `brim_provider.py`, `_brim_io.py` e i loro test.
1. Il test-author scrive i test rossi in `test_services/test_brim_provider_base.py` (azione del runner `services brim-provider-base`): delimitatore su CSV Windows-1252 o Latin-1, ordine delle codifiche, newline universali, delega di `_brim_io`. Nella mia lane, un comando per volta.
2. Poi `TEXT_ENCODINGS`, `_read_text`/`_open_text`, `detect_csv_delimiter` e `_read_file_head`; `_brim_io` delega alla base.
3. Dump prima/dopo identico per tutti i campioni UTF-8. Poi, come ha chiesto il coordinatore, la lista di test dei plugin che usano il metodo: tutte le azioni `services brim-*` (`brim-provider-base`, `brim-parse-error`, `brim-parse-pool`, `brim-parse-race`, `brim-create-transaction`, `brim-versioning`) e la suite `external brim-providers` completa. Infine lint e format, `git diff --check`, porta libera.
4. **CHECKPOINT 1a**, FROZEN. Il coordinatore prepara il commit del fix della base. Nell'handoff propongo la voce 🐛 del CHANGELOG.

> **✅ 1a completato — 2026-09-28** (manca solo il commit, che fa il coordinatore)
>
> **Note implementazione**:
> - **Test rossi** scritti dal test-author in `test_brim_provider_base.py`: classe `TestTextEncodingFallback`, 18 test e 24 casi.
>   - Prima del fix: `15 failed, 19 passed`.
>   - Motivi dei fallimenti: `AttributeError` per le API mancanti; `','` al posto di `';'` su Windows-1252 e Latin-1; `'\x80'` al posto di `'€'`.
> - **`brim_provider.py`**:
>   - costante `TEXT_ENCODINGS = ("utf-8-sig", "cp1252", "latin-1")`;
>   - `_read_text`, che decodifica l'intero file con fallback e lascia le newline intatte;
>   - `_open_text(path, *, newline=None)`, uno `StringIO` con le stesse newline di un `open()` in modalità testo, oppure `newline=""` per il modulo `csv`;
>   - `_read_file_head` segue lo stesso ordine di codifiche e continua a leggere solo le prime N righe, senza caricare tutto il file;
>   - `detect_csv_delimiter` legge la testa con `_read_file_head`.
> - **`_brim_io.py`**:
>   - rimosso `_TEXT_ENCODINGS`;
>   - `detect_delimiter` delega a `BRIMProvider.detect_csv_delimiter`;
>   - `_read_csv_rows` usa `_open_text(..., newline="")`;
>   - import di modulo di `BRIMProvider`: l'agente explore ha verificato che non crea cicli, perché il registry non importa i plugin quando viene caricato.
>
> **Evidenze** (lane `6156` + `/tmp/librefolio-r2-l`, un comando per volta):
>
> | Verifica | Esito |
> |---|---|
> | `services brim-provider-base` | `34 passed` |
> | Dump prima/dopo di tutti i campioni: 52 file, 30 plugin, 92 parse, più delimitatori, testa e `read_rows` | **byte-identico** |
> | `services brim-parse-error` | `4 passed` |
> | `services brim-parse-pool` | `8 passed` |
> | `services brim-parse-race` | `6 passed` |
> | `services brim-create-transaction` | `14 passed` |
> | `services brim-versioning` | `5 passed` |
> | `external brim-providers`, suite completa | `508 passed` |
> | `ruff` e `black --check` sui 3 file | verdi |
> | `dev.py lint` globale | verde |
> | `git diff --check` | pulito |
> | porta 6156 | libera |
>
> Il dump sta nella cartella di sessione e non si committa.
>
> **⚠️ Fuori pista**: il test-author segnala che la descrizione dell'azione `brim-provider-base` in `scripts/test_runner/_backend_services.py` («Abstract base default properties») non copre più il file. Il runner è condiviso: la modifica la propongo al coordinatore e non la faccio io.

**1b. Plugin.** Riguarda i 31 `open()` in 27 plugin, più la guida e la skill.

> **⚠️ Fuori pista (2026-09-28)**: invece di due checkpoint FROZEN separati, un solo handoff con **due gruppi di path distinti**, da committare nell'ordine 1a e poi 1b. I path di 1a sono `brim_provider.py`, `_brim_io.py` e `test_brim_provider_base.py`; quelli di 1b sono i 27 plugin, `test_brim_providers.py`, la guida e la skill. Non si sovrappongono: il coordinatore può fare i due commit separati. Così il lavoro non si ferma in attesa del primo commit. Il coordinatore è stato avvisato.

1. Il test-author scrive i test rossi: invarianza Windows-1252 su ogni campione CSV (quelli non codificabili si saltano con un motivo) e guardia contro gli `open()` con codifica fissa.
2. Poi la migrazione, il dump identico e la suite completa.
3. `brim_plugin_guide.md` e la skill `brim-plugin`.
4. **CHECKPOINT 1b**, FROZEN. Commit dei plugin.

> **✅ 1b completato — 2026-09-28**. Manca solo il commit, che fa il coordinatore. La guida l'ha aggiornata il docs-writer: `brim_plugin_guide.md`, +13 e −2, build strict verde.
>
> **Note implementazione**:
> - **Test rossi** scritti dal test-author in `test_brim_providers.py`, classe `TestWindows1252Invariance`:
>   - una guardia AST contro `open(..., encoding=...)` nei `broker_*.py`;
>   - l'invarianza su 29 coppie (campione, plugin) con testo non ASCII: la copia Windows-1252 deve dare lo stesso `model_dump` o lo stesso `BRIMParseError`;
>   - un controllo che la parametrizzazione non sia vuota.
> - Prima della migrazione: `25 failed, 4 passed, 2 skipped`. Le coppie che passavano già erano CA, Directa e Intesa, che leggono tramite `_brim_io`; le 2 saltate sono Degiro, che contiene U+202F e non si può salvare in Windows-1252.
> - **Migrazione**: uno script a sostituzione esatta ha cambiato 31 punti in 27 plugin.
>   - `open(file_path, encoding="utf-8-sig")` è diventato `self._open_text(file_path)`;
>   - la variante con `newline=""` è diventata `self._open_text(file_path, newline="")`;
>   - una verifica AST conferma che ogni nuovo `self._open_text` ha `self` disponibile: anche i 4 punti vicini a funzioni annidate stanno nel corpo di `parse`.
> - **Skill** `brim-plugin`, regola 4: «never assume the encoding», con `_open_text` o `_brim_io.read_rows`.
>
> **Evidenze** (lane `6156`):
>
> | Verifica | Esito |
> |---|---|
> | `external brim-providers TestWindows1252Invariance` | `29 passed, 2 skipped` |
> | Dump prima/dopo | **byte-identico** |
> | `external brim-providers`, suite completa | `537 passed, 2 skipped` |
> | `services brim-*` (6 azioni) | `71 passed` |
> | `ruff` e `black --check` sui 28 file | verdi |
> | `dev.py lint` | verde |
> | `git diff --check` | pulito |
> | porta 6156 | libera |
>
> **⚠️ Fuori pista**:
> - Il test-author ha trovato 16 casi in cui era già `can_parse` a rifiutare il file Windows-1252: Generic CSV su 14 campioni, InvestEngine e Rabobank, più Trade Republic, il cui campione è solo ASCII. Aprivano il file in `can_parse` con `utf-8-sig`. Dopo la migrazione sono verdi.
> - La skill, alla regola 8, parla ancora di ID finti «negativi»; il contratto reale usa ID positivi alti. È un errore preesistente e fuori tema: lo segnalo e non lo correggo.

> **Commit e allineamento (2026-09-28)**
>
> **Commit del developer** (13:51:21), con liste e digest controllati dal coordinatore:
>
> | Commit | Oggetto | File |
> |---|---|---|
> | `6ea71ea8d` | fix(brim): fall back to cp1252 for CSV exports | 3 |
> | `9d9c26d0d` | fix(brim): read CSV plugins via the base reader | 30 |
> | `28eca0dde` | docs(journal): plan the Danske Bank importer | 4 |
>
> **Merge di allineamento** `1110f2aa7` (developer, 14:00): genitori `28eca0dde` e `7c61dd924` (`dev_release2` con K), albero `53ba0fd4`. Da K arrivano `AssetType.CROWDFUND_REAL_ESTATE`, due scenari di stress, e nel frontend la select dei tipi, le icone e il wizard d'import. Nessuna superficie BRIM toccata.
>
> **Gate dopo il merge** (lane `6156`, un comando per volta):
>
> | Verifica | Esito |
> |---|---|
> | `services brim-provider-base` | `34 passed` |
> | `services brim-parse-error` | `4 passed` |
> | `services brim-parse-pool` | `8 passed` |
> | `services brim-parse-race` | `6 passed` |
> | `services brim-create-transaction` | `14 passed` |
> | `services brim-versioning` | `5 passed` |
> | `external brim-providers` | `537 passed, 2 skipped` |
> | `i18n audit` | rc 0: 3417 chiavi complete, 0 incomplete, 0 backend mancanti. Le 392 «unused» sono preesistenti: L non tocca l'i18n. |
>
> **Checkpoint piccolo** (dopo il merge, su richiesta del coordinatore):
> - **Runner**: in `_backend_services.py`, solo la riga `brim-provider-base`, con `desc="Abstract base defaults + text-encoding fallback"`.
> - **Skill `brim-plugin`, regola 8**: gli ID finti sono positivi alti. Partono da `FAKE_ASSET_ID_BASE = 2**31 - 1` e scendono di uno per ogni ISIN o ticker; `is_fake_asset_id` riconosce i valori da `BASE - 10000` in su. Il riferimento è `backend/app/schemas/brim.py`.
>
> **⚠️ Fuori pista**:
> - La richiesta sulla riga del runner è arrivata dopo i commit. L'avevo applicata subito, poi l'ho ripristinata per lasciare pulito il worktree in vista del merge (anche D tocca `_backend_services.py`). È rientrata in questo checkpoint.
> - La stessa affermazione sbagliata («negative integers») compare in `.github/instructions/backend-providers-brim.instructions.md:35`. Il coordinatore me l'ha assegnata e l'ho corretta nel checkpoint piccolo, gruppo 2.
>
> **Commit del checkpoint piccolo** (developer, 2026-09-29 10:02):
>
> | Commit | Oggetto | Contenuto |
> |---|---|---|
> | `e892e2e0e` | test(runner): describe brim-provider-base scope | 1 file |
> | `dafff60da` | docs(brim): fake asset IDs are high positive | skill e istruzione |
> | `c9ad3bb03` | docs(journal): record Danske step 1 commits | piano |

### 1c. ✅ Fix del 422 nell'upload dalla pagina file e dal dettaglio broker — 2026-09-30

Reperto di L, verificato dal coordinatore. Decisione del developer: «L lo corregge subito dopo la pausa del venv, in un commit a sé con prima il test rosso, senza aspettare il design».

- **Il bug.** `POST /brokers/import/upload` chiede `broker_id` nel form (`Form(...)`, dal commit `eb78aacdb` del 15/06). Due chiamanti lo mandano ancora nella query (`?broker_id=`):
  - `BrokerImportFilesModal.svelte:124`, la modale «storico import» del dettaglio broker;
  - `files/+page.svelte:511`, la scheda BRIM della pagina file.

  Risultato: 422 a ogni upload da lì, dalla v0.9.0 alla v1.1.0 rilasciata. Il wizard è corretto. Nessun test lo copriva: i test API e l'E2E caricano già con il form.
- **Perimetro.** La cura, e solo quella, più quattro `data-testid` per i test; `batch_id` e CHANGELOG restano fuori. Dopo i test rossi del test-author, nei due spec già registrati (`brokers/brokers-detail.spec.ts` → `front-broker detail`; `files.spec.ts` → `front-utility files`).
- **Base**: merge `183ce7b3d` (`dev_release2` in L, developer). `npm ci` autorizzato dal coordinatore.

**Passi**
1. ✅ `npm ci` (una volta, dal lock): exit 0. Avviso di npm 11 sugli script d'installazione non approvati (esbuild, fsevents, es5-ext): nessuna azione.
2. ✅ `data-testid`, solo attributi: `import-files-upload-toggle` (pulsante del footer della modale), `brim-assign-modal` (`testId` della `ModalBase`), `brim-assign-all` (il `div` «Assegna tutti a», come `import-wizard-step1-broker-select` nel wizard), `brim-upload-confirm`.
3. ✅ Test rossi (test-author, corsia 6156): un caso nuovo per spec, con broker proprio, il campione sintetico `generic_simple.csv` e la pulizia in `afterEach`.
   - `brokers-detail.spec.ts` → «uploads a report from the import history modal to its own broker»;
   - `files.spec.ts` → «uploads a BRIM report through the assign-brokers modal to its own broker». Aggiunge un parametro facoltativo `name` al `createBroker` locale; l'unico chiamante esistente resta invariato.

   Tutti e due rossi con `422 … "loc":["body","broker_id"],"msg":"Field required"`. Prima della cura, le azioni complete danno: `front-broker detail` 27 passati e 2 falliti, `front-utility files` 20 passati e 1 fallito.
4. ✅ La cura, solo nei due chiamanti: `formData.append('broker_id', String(brokerId))` e via `?broker_id=` dall'URL. Nessun `?broker_id=` rimasto in `frontend/src`.
5. ✅ Verde, corsia 6156, un comando alla volta, dopo `front build --debug` (exit 0):

   | Comando | Esito |
   |---|---|
   | `front-broker detail "import history modal to its own broker"` | 1 passato |
   | `front-utility files "assign-brokers modal to its own broker"` | 1 passato |
   | `front-broker detail` | 28 passati, 1 fallito (GrowthChart, preesistente) |
   | `front-utility files` | 21 passati |
   | Prettier sui 4 file toccati | pulito |
   | `git diff --check` | pulito |
   | porta 6156 | libera |

   Checkpoint consegnato al coordinatore per il commit `fix(brim): …`.

> **⚠️ Fuori pista**: i `data-testid` sono entrati prima dei test rossi, invertendo l'ordine del coordinatore. Così il test fallisce per il 422 e non per un selettore mancante; il commit resta lo stesso.
>
> **⚠️ Fuori pista**:
> - **Test rosso preesistente**, fuori perimetro: `brokers-detail.spec.ts` «Broker detail — GrowthChart P&L mode › line and income submodes render this broker own figures».
>   - Fallisce anche da solo, prima e dopo la cura.
>   - Il tooltip delle entrate cade su una settimana in cui dividendi e interessi valgono zero, e gli zeri si mostrano senza segno: il test si aspetta almeno 3 importi col segno e ne trova 1. Sembra dipendere dalla data.
>   - Segnalato al coordinatore.
> - Prettier lanciato dalla radice del repo non trova `prettier-plugin-svelte`: va lanciato da `frontend/` (`node_modules/.bin/prettier --check …`).
> - Il build (`svelte-check`) riporta 3 errori preesistenti in file estranei: `TransactionFormModal.test.ts` e `ToolExecutionMetrics.svelte`.
>
> **⚠️ Fuori pista**: il ramo di I (`e-alfy-performance-charts-plan`) aggiunge righe in `brokers-detail.spec.ts` negli stessi punti, e il merge a tre vie dava 2 conflitti. Su richiesta del coordinatore:
> - i 3 import nuovi vanno prima di `import {appears}`;
> - le costanti `__filename`/`__dirname` e il blocco «import history upload» vanno in fondo al file, dopo il `describe` GrowthChart.
>
> Il file risulta identico alla copia di prova del coordinatore (`diff` vuoto), e con quella il merge dà 0 conflitti. Dopo lo spostamento: Prettier pulito, il test nuovo da solo passa (1/1), `front-broker detail` dà 28 passati e 1 fallito (GrowthChart, preesistente, che il coordinatore passa a I), porta 6156 libera.
>
> **Commit** (developer, 2026-09-30). Il developer ha deciso che il fix entra in `dev_release2` da solo; il fix della codifica (step 1) resta nel ramo di L.
>
> | Commit | Dove | Oggetto |
> |---|---|---|
> | `f82eaa020` | ramo di L | fix(brim): send broker_id in upload form |
> | `7a6c772a4` | ramo di L | docs(brim): record the upload 422 fix |
> | `0743b9f44` | `dev_release2` | cherry-pick `-x` di `f82eaa020`, stesso diff |
> | `b1835949e` | `dev_release2` | voce 🐛 Fixed del CHANGELOG, scritta dal coordinatore |

### 2. ⏳ Documento di design dei set

- File `26_brimDanskeBank/design-phase00BrimReportSets.md`: §2 sviluppato con contratti, stati, errori, casi limite (bordi del periodo, troncamenti, righe identiche), compatibilità, test e fasi.
- **Gate: approvazione del developer.** Senza, niente codice sui set.

> **Note implementazione (2026-09-28)**: [bozza scritta](design-phase00BrimReportSets.md), in attesa della revisione.
> - **Fatti di partenza**: raccolti da due agenti explore in sola lettura, uno sul backend (storage, API, schemi, registry) e uno sul frontend (wizard, pagina file, anteprima, i18n).
> - **Contenuto**: confronto fra due architetture, A (manifest più `parse_set`) e C (file combinato derivato, consigliata); contratto del plugin; formato del combinato; regole S1–S9; periodi; API; interfaccia; guida; test; fasi; 12 decisioni D-S.
>
> **⚠️ Fuori pista**:
> - Rispetto al §2 del piano, il design consiglia l'alternativa C: corrisponde meglio a «salva sia gli originali che il combinato, ma lavora solo il combinato», e la provenienza delle righe arriva senza modificare gli schemi.
> - Il design rovescia anche D1: le righe autonome non si escludono in base al periodo ricavato dalle righe. Il primo versamento arriva prima del primo trade, quindi la cassa partirebbe negativa. Si esclude solo per mancanza di controparte.
>
> **Note implementazione (2026-09-29) — design v2**. Su richiesta del developer («ripensa il piano sapendo di questo limite sulle date… anche intesa san paolo e credit agricole hanno dei limiti… un'altra questione spinosa sono le commissioni»):
> - profondità degli export in §1 (Danske 1 anno/5 anni; CA 2 anni/molti anni; Intesa circa 1 anno più l'istantanea);
> - nuovi concetti (copertura, finestra completa `T0…T1`, zona precedente, stato iniziale);
> - regole S10–S16;
> - §10 riscritto (modello, tabella per banca, continuità, bordi, commissioni);
> - interfaccia, guida, test e fasi aggiornati, con CA e Intesa mappati;
> - decisioni D-S13…D-S18, D-S3 e D-S10 riviste.
>
> La semantica delle commissioni viene dalla #25: la banca esporta il regolato con la commissione dentro (acquisto 100 + 5 → −105; vendita 100 − 5 → +95).
>
> **Note implementazione (2026-09-29) — design v3**. Indicazioni del developer:
> - «l'utente, senza sapere nulla, nel tempo genera i vari export e li importa, e il sistema delle transazioni, DA SOLO, crea le transazioni ed evita di rimettere tutte le volte il salto T0»;
> - uno step facoltativo dopo la revisione, con le transazioni «sommarie» selezionate di default e un tag per riconoscerle;
> - lo split delle commissioni su tutti i trade con commissione non chiara;
> - saldo e posizioni di fix solo automatici;
> - confronto con CA e Intesa.
>
> Applicato nel design:
> - punti di verità (S12);
> - gap-fix calcolato dal core come differenza rispetto al database più la selezione (S13, §10.7, `POST /gap-fix`);
> - `T0` sulla data valuta, spostato solo quanto serve (S14, §10.5 con esempio);
> - tag `gap_fix`;
> - §17 con il confronto CA e Intesa: tutte e due migrabili;
> - decisioni D-S13…D-S21 aggiornate.
>
> Il principio della differenza l'ha approvato il developer (ask_user del 2026-09-29).
>
> **Note implementazione (2026-09-29) — design v4**. Domande del developer sul perimetro dei set e sui buchi:
> - **D-S22 ✅** (ask_user): il set sono i file scelti in un import, nuovi e già caricati, raggruppati da soli per broker, plugin e ruolo. Più file per ruolo sono ammessi: una riga identica compare tante volte quante nel file che ne ha di più. Fra un import e l'altro la memoria è il database. Il developer chiamava «A» proprio questo; il pool globale di tutti i file è scartato.
> - **D-S23 ✅** (ask_user): nei buchi dopo `H0` le righe autonome del CSV si importano con la loro data; la cassa di trade e dividendi del buco la riallinea il checkpoint successivo. Applicato nel nuovo §10.8, nella regola S16, in `combine(..., history_start=H0)` e in `POST /gap-fix`, che calcola i checkpoint in ordine.
> - **D-S24**, proposta: una correzione deselezionata non si compensa nei checkpoint successivi.
> - **D-S19 ✅** (solo verifica) e **D-S21 ⏸** (rimandata), su indicazione del developer.
> - **Offset delle date**, domanda del developer per l'autore. Sui file reali nessuna data cade nel weekend, e tutte le righe dell'XLSX con importo trovano la loro riga nel CSV con scarto zero; con scarto di uno o due giorni, nessuna. Le date dei due file sono quasi certamente coerenti. La bozza della domanda è nella cartella di sessione: se vuole, la pubblica il developer.
> - **D4**: la prima spiegazione non era chiara. L'ho riformulata con un esempio e con il meccanismo che esiste già: il todo bloccante su `cost_basis_override`, come nel CSV generico.
> - **D4 ✅** (developer, 2026-09-29): rettifiche semplici, marcate dal plugin per la revisione manuale. Scartati l'evento `DEMERGER` e la modalità PMC «auto» sulla rettifica negativa.
>
> **⚠️ Fuori pista**:
> - Verificando il motore (`portfolio_engine._is_capital_adjustment`): una rettifica negativa conta come uscita di capitale solo se porta un PMC, ma l'editor lo toglie sempre (`TransactionBulkModal`, `txPayloadHelpers.ts`, regola `required_qty_pos`). Quindi la linea vecchia di una scissione lascia capitale investito e guadagno sfalsati del suo costo. Il developer lo accetta come limite noto.
> - Per lo stesso motivo un blocco sul PMC di una rettifica negativa non si può risolvere nell'editor: nel plugin Danske la linea vecchia avrà un avviso, non un blocco. Il CSV generico emette il blocco su ogni rettifica senza PMC, di qualunque segno: va verificato se ha lo stesso problema, ma è fuori dal mio perimetro e l'ho segnalato al coordinatore.
> - Nell'[analisi](analysis-phase00BrimDanskeBank.md) ho corretto «ID finto negativo»: gli ID finti sono positivi alti (regola 8 della skill).
>
> **Commit del journal v4**: `e3244095e` (developer, 12:57), «docs(journal): design v4 of the Danske report sets».
>
> **Note implementazione (2026-09-29) — design v5, riscrittura completa**. Richiesta del developer: «rifai il piano di design partendo dalla nuova api e risalendo, spiegando i vari casi limite e come ci si dovrebbe comportare, ed evidenziando per ogni capitolo, a livello funzionale, la migrazione da ora al tendere, e alla fine un'analisi logica per trovare incongruenze».
> - **Struttura nuova**: la nuova API è il capitolo centrale (§3, endpoint per endpoint, con quello che ciascuno chiede al plugin e al core); poi si risale a wizard (§4), pagina file (§5), guide (§6) e banche (§7). Ogni capitolo ha una tabella dei casi limite e un riquadro «Migrazione» (oggi → pilota → a regime). In fondo, l'analisi logica (§11): invarianti, copertura dei casi, sette scenari Danske, incongruenze A1–A14, tensioni R1–R9.
> - **Da confermare** (§10): D-S13 (orfani di bordo al posto dello spostamento di `T0`), D-S25 (`H0`), D-S26 (`combine` puro), D-S27 (regola di sicurezza dei checkpoint), D-S28 (file sovrapposti), D-S29 (prove E1 ed E4), D-S30 (parte non spiegata ai checkpoint intermedi).
> - Fatti ricontrollati sul codice: le route del router `/brokers/import`; i campi di `BRIMParseOutput`; i criteri dei duplicati in `detect_tx_duplicates`; la soglia `opened_at` nel wizard (`importRowState.ts`); le righe in attesa che il wizard riceve dall'editor (`pendingCreateTransactions`, `pendingDeleteTxIds`); lo split generico `split_hint` in `FixFlaggedStep.svelte`; il seed del patrimonio Intesa; le gambe `auto_cash` e i blocchi sovrapposti di CA.
>
> **⚠️ Fuori pista**:
> - Rileggendo la v5 durante la scrittura ho trovato tre incongruenze mie (A12–A14): la spiegazione delle correzioni avrebbe contato righe già presenti; mancava il checkpoint quando il CSV inizia dopo l'XLSX; la prima formulazione di `H0` era sbagliata in tre casi. Sono corrette nel testo e registrate nel §11.4.
> - La guida utente CA dice che il saldo iniziale sta in testa all'XLSX dell'estratto: la v4 lo dava «da verificare» (A10).
>
> **Commit del journal v5**: `ed83ea279` (developer, 13:29).
>
> **Note implementazione (2026-09-30) — design v5.1**. Il developer approva l'impianto fino al wizard, ma chiede un dettaglio del §4 con i disegni dei passi. Il suo dubbio principale: «dopo l'upload, come capiscono l'utente o il sistema quali file caricati includere, e se serve includere altro già caricato?».
> - Il §4 è riscritto con una tabella «oggi → pilota» e i disegni di ② Seleziona file (casi A, B, C, D e la variante col buco), ③ Analizza (con il dettaglio del set), Correzioni, Revisione, «Allinea con la banca» (primo import, buco, verifica che non torna) ed editor.
> - Il nodo (§4.1, D-S31 da confermare): nessuno dichiara cosa va insieme. Il set sono i file scelti con lo stesso broker e lo stesso plugin, e il sistema lo completa da solo, per periodi, con i file già caricati che servono, spuntati, segnati e rimovibili. Se non trova nulla, dice quale export serve e per quale periodo, con un pulsante per caricarlo lì.
> - Adeguati di conseguenza: §3.3 (`additions`, `missing`, `excluded_file_ids`, cache nel sidecar), §3.8 (`must_cover`), §8 (test), §10 (D-S8 precisata, D-S31), §11 (A15, R10).
> - Rilevato sul codice di oggi: il passo ② elenca già tutti i file del broker e spunta quelli appena caricati (`loadBrokerFiles`, T7). Nel passo Correzioni finiscono solo i blocchi sui campi che servono al confronto dei duplicati, gli asset mancanti e gli split (`fixRowLifecycle.ts`); il costo mancante si scrive nell'editor. Per questo il costo della scissione è disegnato nell'editor, non in Correzioni.
>
> **⚠️ Fuori pista**: per non riportare nel design valori reali, ho confrontato date e importi inventati dei disegni con i due export, in sola lettura e senza stamparne il contenuto (`/tmp/libreFolio_l_mockcheck.py`). Su 24 valori coincide solo «0,00».
>
> **Note implementazione (2026-09-30) — design v5.2**. Il developer ha contestato il completamento automatico: «il plugin riceve ogni volta la lista di tutti gli upload precedenti e poi sceglie? Non mi pare il comportamento giusto. Forse è più lineare il set di upload». Abbiamo messo a confronto tre modelli (completamento automatico, selezione a mano, set di caricamento). Nel caso normale si comportano allo stesso modo; cambiano solo quando un file manca, quando un import si interrompe, e per la memoria fra un import e l'altro.
> - **D-S22 ✅** (ask_user): **il set nasce dal caricamento**. I file caricati insieme per lo stesso broker e riconosciuti dallo stesso plugin formano il set, che è un'unità. «Carica il file mancante» lo completa, e caricamenti diversi non si mescolano.
> - **D-S31 ❌ ritirata**: cercare fra i file già caricati trasformava l'archivio dei file in una memoria nascosta accanto al database (A16).
> - Applicato nel design:
>   - §2: «Caricamento», e la nuova definizione di «Set»;
>   - §3: `batch_id` all'upload, con i tre punti che caricano (wizard, pagina file, `BrokerImportFilesModal`); preview e combine per caricamento; la preview non guarda mai gli altri file del broker;
>   - §4.1–§4.4: disegni nuovi (casi A–F, set come riga unica, raggruppamento visibile già al passo ①);
>   - §5 e §6; §7.2, dove i file CA caricati prima dei set non hanno `batch_id`;
>   - §8, §10 (D-S8, D-S9, D-S22, D-S31), §11 (A15 risolta, A16, R10).
> - Il controllo dei valori inventati, rilanciato sul §4 nuovo, dà lo stesso esito: coincide solo «0,00».
>
> **Commit del journal v5.1 e v5.2**: `14122a76a` (developer).
>
> **Note implementazione (2026-09-30) — design v5.3**. Il developer chiede come si mostra un file obbligatorio che manca, cosa fa `POST /gap-fix`, e se c'è già un'analisi logica.
> - §4.2: il set incompleto si vede già al passo ①, dove basta trascinare il file mancante nello stesso caricamento; al passo ② resta il caso B.
> - Una nuova passata dell'analisi logica sulla v5.2 trova due punti:
>   - **A17**: il §3.2 e il §4 si contraddicevano su un originale eliminato. Ora, finché il combinato è aggiornato, il set resta importabile;
>   - **A18**: il set dipendeva dal plugin scelto in automatico. Ora un file di cui un plugin a set riconosce il ruolo entra nel suo set; il CSV generico, per esempio, accetta qualsiasi CSV con un'intestazione.
>
>   Aggiunto anche lo **scenario 8**: due set dello stesso broker importati insieme su un broker vuoto non contano niente due volte.
> - §3.2: i tre chiamanti restano su `axiosInstance` con `FormData`, e il `batch_id` è un campo in più del form; il 422 è già corretto (`f82eaa020`).
> - Il controllo dei valori inventati dà lo stesso esito.

### 3. ⏳ Risposte dell'autore

- ✅ 2026-09-28: il developer ha pubblicato la risposta sulla issue ([commento](https://github.com/Librefolio/LibreFolio/issues/26#issuecomment-5868387443)). È la v5 senza il paragrafo sul permesso; il testo pubblicato è in [issue26-reply.en.md](issue26-reply.en.md).
- ✅ 2026-09-28: il permesso per il campione sintetico l'ha dato il developer (§0). Campioni e test Danske non sono più bloccati.
- ⏳ Le risposte su menu, periodo e colonne servono:
  - alla guida (step 7), che le aspetta;
  - a rifinire R4/R5, D4, D6 e D14.
- Il plugin non le aspetta: i casi ignoti li gestisce in modo difensivo, con un'esclusione dichiarata.

> **Note implementazione**: la risposta è stata recuperata con `gh api` in sola lettura e registrata nel journal al posto della bozza.

> **✅ Risposte dell'autore — 2026-09-28 16:11 UTC** ([commento](https://github.com/Librefolio/LibreFolio/issues/26#issuecomment-5873953304)), lette il 2026-09-29.
>
> | Tema | Risposta | Effetto sul lavoro |
> |---|---|---|
> | Ruoli dei file | XLSX = titoli, CSV = cassa | conferma i due ruoli `custody` e `cash` |
> | **Profondità** | **XLSX al massimo 1 anno, CSV fino a 5 anni** | **i periodi non possono coincidere oltre un anno**: va ripensato §10 del design (S5, D-S3). Da discutere col developer. |
> | Filtro del periodo | per **data dell'operazione** | ai bordi si perdono controparti: i trade fatti a fine periodo si regolano dopo (la data valuta nel CSV cade oltre) |
> | Nomi dei file | `Transactions.xlsx`; `Osakesäästötili-<IBAN>-<data>.csv` | conferma che il conto è un'OST; il nome del CSV contiene l'IBAN, quindi non va propagato nel file combinato né nei campioni |
> | Lingua | l'interfaccia della banca è solo in finlandese | pilota solo con header finlandesi; nessuna variante EN/SV da supportare per ora |
> | `Tila` | nessun ordine annullato visto; valori alternativi sconosciuti | resta la difesa S7 |
> | `Tarkastus` | non sa | si ignora (come previsto) |
> | Commissione | **inclusa in `Summa`**; non viene esportata separatamente, si vede solo nel dettaglio web | **D14 chiusa**: nessuna FEE separata (e niente ricalcolo), notice informativa |
> | `Kurssi` | nella valuta del mercato; `Summa` in EUR | confermato; il prezzo resta solo descrittivo |
> | `Tuotto` | dividendo in contanti; `Määrä` = azioni possedute | **D6 chiusa**: DIVIDEND con quantità 0 |
> | `Jakautuminen` | la banca **non** indica la ripartizione del costo | **D4**: il costo delle nuove linee va chiesto all'utente (todo bloccante). Per le società quotate finlandesi, la ripartizione è pubblicata dall'Agenzia delle entrate (vero.fi) |
> | Altri `Toimeksiantotyyppi` | «probabilmente molti che non conosco» | resta la difesa S7, con esclusione dichiarata ed evidenze |
> | Numero di 10 cifre | riferimento del dividendo | indizio di classificazione, non chiave di abbinamento |
> | ISIN o ticker | **nessun export li contiene** | identificazione solo per nome (Yahoo, scelta manuale della quotazione) |
> | Mercati e prezzi | quasi tutti i mercati EU e USA; i dati della banca solo in app e web; usa **Yahoo Finance** | **nessun provider nuovo necessario** |
> | PS | «potrebbe essere sforzo sprecato… non mi dispiace aggiungere a mano» | segnale di bassa priorità per Danske; il framework dei set resta utile per CA |
>
> **⚠️ Fuori pista**: l'asimmetria 1 anno / 5 anni rende incompleta la regola «stessi periodi». Il design va rivisto prima dell'approvazione su questi punti:
> - periodo effettivo del set = copertura dell'XLSX;
> - CSV tagliato a quel periodo;
> - saldo iniziale della cassa ricavato dal `Saldo` del CSV;
> - posizioni aperte da oltre un anno da inserire come posizioni iniziali (vendite senza acquisto nel file).
>
> Proposta applicata nella **v2 del design** (2026-09-29, §10 «Finestre temporali, stato iniziale e commissioni»), in attesa della revisione del developer.

### 4. ⏸ Framework dei set (dopo il gate 2)

- Test rossi con un **plugin finto a due ruoli**, che non dipende dall'autore.
- Schemi, manifest, endpoint, provenienza.
- **Contratto API** (nota del coordinatore, 2026-09-30):
  - `api sync` solo nella corsia di L (6156, `/tmp/librefolio-r2-l`);
  - all'integrazione `openapi.json` e `generated.ts` si rigenerano, non si uniscono a mano, perché anche D cambia il contratto (R4.9);
  - `POST /upload` riceve `batch_id` come campo del form. I tre chiamanti (wizard, pagina file, `BrokerImportFilesModal`) restano su `axiosInstance` con `FormData`, come oggi: nel codice è scritto che Zodios non gestisce bene il `FormData`.

### 5. ⏸ Plugin Danske (dopo il gate 2)

- Test rossi sui campioni sintetici: abbinamento, esclusioni R4, R5 e R6, riconciliazione, segni, valuta, `Tuotto`, scissione, latin-1, header HTML, colonna senza nome.
- Poi il parser custody, il parser cash, il motore, l'assemblaggio.

### 6. ⏸ Wizard: card del set e blocchi (mio, D11)

- Si parte **dopo il merge di K** in `dev_release2` e l'allineamento del coordinatore: merge di `dev_release2` nel ramo, poi rilancio dei gate.
- Vitest per la logica pura; Playwright per il flusso completo; `front build --debug` se serve.
- Chiavi i18n solo in `importWizard.reportSet.*`.

### 7. ⏸ Documentazione

- docs-writer, solo EN: pagina utente Danske (export, stesso periodo, esclusioni) e sezione «plugin multi-report» nella guida sviluppatore.
- Registrazioni proposte (§9).

### 8. ⏸ Gate finali e handoff

- Suite BRIM, API dei set, E2E wizard, lint, `git diff --check`, porta libera, checkpoint.

## 7. Test: comandi

```bash
PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py test \
  --test-port 6156 --data-dir /tmp/librefolio-r2-l external brim-providers [<selettore -k>]
```

- Selettori previsti: `encoding`, `danske`, `TestPluginFrontendContract`, e la suite completa.
- Per le API dei set, `api all` con `-k brim_sets`.
- Gli E2E sulla stessa lane, uno alla volta.

## 8. Complessità e rischi

| Parte | Complessità | Rischi principali |
|---|---|---|
| Fix codifica | media, meccanica | diff largo (conflitti con altri workstream: controllo del coordinatore); modi di lettura particolari in qualche plugin |
| Design dei set | media | decisioni con molto impatto; righe ai bordi del periodo (regolamento T+2) |
| Framework dei set | medio-alta | schema e API nuovi; storage e race; provenienza |
| Wizard | alta | proprietà di K; interfaccia nuova; E2E |
| Plugin Danske | media | varianti di lingua, tipi sconosciuti, costo della scissione, semantica della commissione, identificazione solo per nome, file ri-salvati dall'autore diversi dall'originale |

## 9. Registrazioni (politica del coordinatore, 2026-09-28)

**Le scrivo io, solo aggiungendo, e le elenco nell'handoff**

- **Nav** `mkdocs.yml`: sotto «🏦 Banks & Neobrokers», `- Danske Bank: user/transactions/import/danske_bank.md`.
- **Indice** ×4: una card e una riga nella tabella delle capacità.
- **`providers_list.md`**: una riga `broker_danske_bank`, XLSX + CSV (set), 🧪 Beta.
- **`sample_reports/README.md`**: le due righe dei campioni.
- **i18n**: chiavi nuove solo in `importWizard.reportSet.*`, via `dev.py i18n`, in 4 lingue.

**Voci proposte per il CHANGELOG**, che scrive il coordinatore:

- `### 🐛 Fixed`: «Broker import: CSV exports saved as Windows-1252/Latin-1 (e.g. re-saved with Excel on Windows) are now read by every CSV importer instead of failing.»
- `### 🧪 Beta`, alla consegna del pilota: «Danske Bank (Finland) importer: combines the custody transactions (XLSX) and the cash-account statement (CSV) into one import; rows without a counterpart are left out and listed.» e «Import wizard: multi-report sets — banks that split an account across several exports are imported as one set.»

## 10. Decisioni aperte (developer)

| # | Decisione | Proposta |
|---|---|---|
| D1 | Fuori dal periodo comune: escludere **tutte** le righe (R5) o solo quelle accoppiate | ⚠️ **Superata dalla D-S3 del design**: solo le accoppiate senza controparte; i periodi servono solo a informare |
| D2 | Raggruppamento fisico | manifest + riferimento nei file (§2.2) |
| D3 | Obbligo dei ruoli: override possibile? | no, per il pilota Danske |
| D4 | Costo della scissione | ✅ **Deciso dal developer il 2026-09-29.** Una rettifica negativa per la linea vecchia e una positiva per ogni linea nuova, senza cassa. Il plugin le marca tutte per la revisione manuale (`field_todos`, reason `demerger`, con l'evidenza della riga): **blocco** sul PMC delle linee nuove (con rapporto 1:1, PMC nuovo = PMC vecchio × percentuale pubblicata da vero.fi) e **avviso** sulla linea vecchia. Sulla linea vecchia niente blocco: l'editor non permetterebbe di risolverlo. Niente evento `DEMERGER` e nessuna modifica al core. **Limite noto**: l'editor toglie il PMC dalle rettifiche negative (`required_qty_pos`), quindi il motore non registra l'uscita di capitale della linea vecchia; capitale investito e guadagno risultano sfalsati del costo della linea vecchia. La guida lo spiega. |
| D5 | Data della transazione estesa | ✅ data valuta (coerente con S14 del design) |
| D6 | `Tuotto` come DIVIDEND con quantità 0 | ✅ **confermato dall'autore** (2026-09-28): `Määrä` = azioni possedute |
| D7 | Lingua | ✅ notice in finlandese (l'interfaccia della banca è solo in finlandese); todo in inglese più `reason_code` |
| D8 | Pagina utente | solo EN; Aphra su richiesta |
| D9 | Saldo iniziale | ⚠️ **superata**: punto di verità più gap-fix proposto dal core (design, D-S14 e D-S15) |
| D10 | Bump di versione per il fix | nessuno |
| D11 | Chi fa il wizard dei set | ✅ **Deciso dal coordinatore**: L, dopo il merge di K in `dev_release2` |
| D12 | Provenienza nello schema | sorgente per riga di evidenza |
| D13 | Motore di abbinamento | dentro Danske finché CA non diventa il secondo utilizzatore |
| D14 | `Palkkio` diverso da 0 | ⚠️ **superata dalla D-S17 del design**: la commissione è dentro `Summa` e non viene esportata a parte (#26, #25) |

## 11. Definition of done

- **Adesso (step 0–2)**:
  - fix codifica verde, con output invariato per tutti i campioni UTF-8 e invarianza Windows-1252 provata;
  - documento di design approvato;
  - risposta all'autore pubblicata (✅ 2026-09-28);
  - journal aggiornato; porta libera; nessun dato reale nel repo.
- **Pilota (step 4–8)**:
  - un set Danske completo produce le transazioni estese;
  - ogni esclusione è dichiarata con le evidenze;
  - riconciliazione con il saldo del CSV;
  - il wizard blocca i set incompleti e mostra i periodi;
  - la guida spiega l'export e la regola dei periodi;
  - test rossi prima e poi verdi; checkpoint consegnato.
