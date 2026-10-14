# Riepilogo: export Scalable → plugin BRIM `broker_scalable`

> Stato al 2026-10-09, alla fine della fase «export Scalable via Chrome» (sessione S, coordinata da `c8328a01-f208-4ade-a352-0486d1f14de2`).
>
> È il punto di partenza per il plugin in LibreFolio. La fonte di verità del formato è `docs/formats/scalable.md` nel repo dell'esportatore; i dettagli di ogni giro stanno nel piano della fase dell'esportatore, rimasto nella sessione S (§12). Il piano del plugin è [`plan-phase00BrimScalable.prompt.md`](plan-phase00BrimScalable.prompt.md).
>
> Qui non ci sono valori, id o riferimenti reali del developer: il file si può archiviare nel journal così com'è.

## 1. Dove siamo

- **L'esportatore funziona ed è pubblicato**: `Librefolio/librefolio-exporter`, repo pubblico separato, AGPL-3.0. È un'estensione Manifest V3 per Chrome, Edge, Brave e altri Chromium dalla versione 120.
  - **v1.0.0** del 2026-10-09: tag `v1.0.0`, release con `librefolio-exporter-1.0.0.zip` e il suo `.sha256`, ultimo commit `699d023`.
  - Si installa a mano dalla release: ZIP verificato, estratto in `Downloads/chromePlugin`, «Carica estensione non pacchettizzata». Il pannello controlla gli aggiornamenti sulle release di GitHub.
  - Pipeline: `ci.yml` esegue i test a ogni push. `release.yml` parte da un tag `v*` uguale alla versione del manifest e fa test, ZIP, SHA-256 e release, con l'intero CHANGELOG come note.
- **Provato dal developer sul conto vero**:
  - broker e conto deposito si esportano da qualunque pagina dell'app;
  - per entrambi i conti la somma degli `amount` coincide con il saldo nell'app;
  - i trasferimenti interni si abbinano tra i due file.
- **In LibreFolio non c'è ancora nulla.** Il plugin BRIM è il passo successivo.

## 2. I file che il plugin leggerà

### 2.1 Nomi e forma

- **Un file per conto**: `<prefisso>-broker_<data>_<ora>.csv` e `<prefisso>-deposit_<data>_<ora>.csv`.
  - Con entrambi i conti l'utente riceve uno ZIP, `<prefisso>_<data>_<ora>.zip`, che li contiene.
  - Il prefisso è `scalable` di default, ma l'utente può cambiarlo: **i file non si riconoscono dal nome.**
- **Forma**:
  - UTF-8 senza BOM, righe LF, separatore `;`;
  - virgola decimale nelle colonne 1–14, punto nelle `lf_*`;
  - `reference` e `description` sempre tra virgolette;
  - data e ora in ora tedesca (Europe/Berlin).

### 2.2 Le colonne

Le colonne 1–14 sono quelle del CSV ufficiale Prime:

`date;time;status;reference;description;assetType;type;isin;shares;price;amount;fee;tax;currency`

Le colonne `lf_*` si leggono per nome. Una colonna non cambia mai significato; le colonne nuove arrivano in fondo, come `lf_<percorso>`.

| Colonna | Broker | Deposito | Contenuto |
|---|---|---|---|
| `lf_account` | ✓ | ✓ | `broker` o `deposit`: dice in quale dei due broker LibreFolio va il file |
| `lf_account_index` | — | ✓ | 1, 2… per ogni conto deposito |
| `lf_id` | ✓ | ✓ | id della transazione, stabile e unico, con gli id dei conti mascherati |
| `lf_subtype` | ✓ | ✓ | tipo esatto: `SINGLE`, `SAVINGS_PLAN`, `DEPOSIT`, `WITHDRAWAL`, `CASH_TRANSFER_IN`/`OUT`, `INTEREST`, `DISTRIBUTION`… |
| `lf_is_cancellation` | ✓ | ✓ | `true` solo per uno storno, altrimenti vuota |
| `lf_ordered_shares` | ✓ | — | pezzi ordinati, solo quando non sono stati eseguiti tutti |
| `lf_transaction_fee`, `lf_venue_fee`, `lf_crypto_spread_fee` | ✓ | — | le parti di `fee` |
| `lf_trading_venue` | ✓ | — | codice MIC della borsa, per esempio `SEIX` |

Il file del broker ha 23 colonne, quello del conto deposito 19.

### 2.3 Regole di lettura per il plugin

- **`status`.**
  - Si importano solo le righe `Executed`.
  - `Cancelled`, `Expired` e `Rejected` hanno `shares` a 0, come nel file Prime.
  - `Pending` vuol dire non eseguito: nel file Prime compare comunque con pezzi e importo pieni.
- **`fee` e `tax`.**
  - Vuoti vuol dire non noti (dettagli non letti o non riusciti); `0` vuol dire nessuno.
  - Se mancano, il plugin deve avvisare e suggerire di riesportare con «Includi commissioni e tasse».
  - `fee` è la somma esatta delle tre parti.
  - Nell'esportatore 1.0.0 l'`amount` degli acquisti comprende la commissione, `-(pezzi × prezzo + fee)`. Nel CSV Prime ufficiale, invece, `amount` è il lordo (pezzi × prezzo), con commissioni e tasse a parte: lo dicono due export reali pubblici. L'esportatore 1.0.1 lo allinea (piano del plugin, §5).
- **`amount`.**
  - Non è arrotondato al centesimo: è il prodotto pezzi × prezzo, anche con 3 o più decimali, come nel file Prime. In LibreFolio va verificata la precisione.
  - Nel conto deposito è negativo per `WITHDRAWAL` e `*_OUT`. La web app li dà tutti positivi: è l'esportatore a cambiare il segno.
- **Interessi.** `amount` è il netto e `tax` la ritenuta (26% in Italia); il lordo è `amount + tax`.
- **Data.** I movimenti di cassa hanno solo la data. `02:00:00` (ora legale) o `01:00:00` (ora solare) corrispondono alla mezzanotte UTC: va usata solo la data.
- **`reference`.**
  - `SCAL…` (15 caratteri) per le operazioni, `INTEREST-PAY-<conto>-<numero>` per gli interessi, vuota sulle altre righe.
  - L'id della transazione è sempre in `lf_id`.
- **`description`.** È così come arriva, nella lingua del conto («Trasferimento interno», «… piano di accumulo»), con IBAN e nomi. Non va interpretata: il tipo esatto è in `lf_subtype`.
- **Riconoscimento del layout dall'intestazione.** Le sole 14 colonne indicano il file Prime. Se c'è `lf_account` è il nostro esportatore, e `lf_account` dice anche il conto.

### 2.4 Il CSV Prime ufficiale (solo broker)

Il plugin deve leggere anche questo, per decisione del developer. Cosa sappiamo (il piano della fase dell'esportatore, §2.4, e due export reali pubblici):

- nelle operazioni `amount` è il lordo (pezzi × prezzo), con `fee` e `tax` a parte; nei proventi è il netto, con la ritenuta in `tax`;

- intestazione e valori sono sempre in inglese, ma il file può avere un BOM;
- `type` comprende anche `Fee` (esclusa la commissione d'ordine), `Taxes`, `Security transfer` e `Corporate action`; forse `Reinvestment_Distribution`;
- il segno di `fee` e `tax` non è coerente tra le fonti;
- `reference` c'è su ogni riga;
- nei campioni le righe di cassa hanno `fee` a `0` e `tax` vuoto;
- i `Security transfer` delle coppie interne della migrazione a Baader (dicembre 2025) vanno trattati come neutri.

## 3. Decisioni prese con il developer

1. **Due broker in LibreFolio**: «Scalable broker» e «Scalable conto deposito».
   - **Motivi:**
     - un broker LibreFolio ha un solo pool di cassa per valuta;
     - `CASH_TRANSFER` collega solo broker diversi;
     - un import BRIM va in un solo broker;
     - così i due IBAN e i due saldi restano verificabili.
   - **Uso:**
     - ogni CSV si importa nel proprio broker;
     - i trasferimenti interni (`CASH_TRANSFER_OUT` ↔ `CASH_TRANSFER_IN`, stesso giorno e importo) si collegano con promote / promote-suggest;
     - in futuro si potranno collegare in automatico all'import.
2. **`lf_id` nella frase della descrizione LibreFolio**, per ogni riga importata.
   - **Perché:** LibreFolio riconosce i duplicati da tipo, data, quantità, importo e descrizione o asset, non da un id esterno. In passato due bonifici identici (stesso giorno, importo e causale) sono stati scambiati per un doppione.
   - **Effetto:** con l'id nella descrizione, due righe uguali restano distinte, e lo stesso movimento esportato di nuovo viene riconosciuto.
   - **Vincolo per l'esportatore:** la maschera degli id non deve cambiare mai (tag FNV-1a di 8 cifre esadecimali, formato `<tipo>-<tag>`). Se cambia, cambiano gli `lf_id` e i movimenti già importati tornano come nuovi.
3. **Descrizioni intere, IBAN compresi**: servono in LibreFolio. Si mascherano solo gli id interni di persona, portafoglio e conti.
4. **Il CSV Prime ufficiale** si legge con lo stesso plugin.
5. **Ogni campo compare una sola volta**: niente colonne doppie. Le `lf_*` portano solo ciò che le 14 colonne non dicono.
6. **Il numero negli id e nei riferimenti degli interessi** (`INTEREST-PAY-<conto>-<numero>`) resta in chiaro: il developer ha verificato che non è il numero cliente né una parte dell'IBAN.
7. **Documentazione e loghi**, dopo il plugin:
   - una pagina utente con i due broker e l'import di ciascun CSV nel suo broker;
   - due SVG del logo Scalable con un piccolo simbolo (grafico per il broker, salvadanaio per il deposito; icone Phosphor, MIT);
   - le istruzioni per usarli come icona del broker (`Broker.icon_url`);
   - una verifica preventiva dell'uso del marchio Scalable.

## 4. Mappatura proposta verso LibreFolio

> Superata dal [piano del plugin](plan-phase00BrimScalable.prompt.md) (§4.3), che usa il lordo delle operazioni e le gambe FEE e TAX. La tabella qui sotto resta come traccia della proposta iniziale.

Va verificata sul codice dopo l'aggiornamento della baseline.

| CSV: `type` (`lf_subtype`) | LibreFolio | Note |
|---|---|---|
| `Buy`, `Savings plan` | `BUY` | quantità da `shares`, prezzo da `price`, poi `fee` e `tax`; asset da `isin` + `description` |
| `Sell` | `SELL` | da verificare su una vendita reale (0,99 € di commissione, tasse sulle plusvalenze) |
| `Distribution` (`DISTRIBUTION`, `REINVESTMENT_DISTRIBUTION`) | `DIVIDEND` | `isin` viene da `relatedIsin`; importo lordo o netto ❓ |
| `Interest` (`INTEREST`, `INTEREST_PAYMENT`) | `INTEREST` | netto in `amount`, ritenuta in `tax`: come si rappresenta la ritenuta ❓ |
| `Deposit` (`DEPOSIT`, `POCKET_MONEY`) | `DEPOSIT` | |
| `Withdrawal` (`WITHDRAWAL`) | `WITHDRAWAL` | |
| `Deposit` o `Withdrawal` con `CASH_TRANSFER_IN`/`OUT` | `DEPOSIT` o `WITHDRAWAL`, poi `CASH_TRANSFER` | coppie tra i due broker collegate con promote; descrizione «Trasferimento interno» |
| `Fee` (`FEE`) | `FEE` | |
| `Taxes` (`TAX`, `TAX_RETURN`) | `TAX` | un `TAX_RETURN` positivo è ammesso dalle regole dei segni ❓ |
| `Security transfer`, `Corporate action` | movimento senza cassa, o notice | ❓ |
| `lf_is_cancellation` = `true` | ❓ | mai visto: importare lo storno come correzione, o saltarlo insieme all'originale |

- Regole BRIM: valuta presa dalla riga (`currency`), nessun forex, importi verbatim, asset per ISIN (id fittizi), `plugin_version`.
- Ordini eseguiti in parte (`Pending` con `shares` > 0 e `lf_ordered_shares` valorizzata): decidere se importare la parte già eseguita.

## 5. Fatti verificati sui dati reali

Nessun valore del developer, solo le regole che ne sono emerse.

- **Acquisti.** |`amount`| = `shares` × `price` + `fee` (+ `tax`), salvo l'arrotondamento del prezzo nei piani di accumulo.
- **Commissioni del piano FREE.** Fonti ufficiali: centro assistenza «Cosa sono i PRIME partner e quali vantaggi offrono?» e `de.scalable.capital/en/trading-costs`.
  - Gli acquisti di ETF dei partner PRIME (Amundi, iShares, Vanguard, Xtrackers; vale anche per un ETC iShares) sono gratuiti da 250 € in su, altrimenti costano 0,99 €.
  - Le vendite costano 0,99 €; i piani di accumulo sono gratuiti.
  - La commissione è esplicita nei dettagli (`transactionFee`): non serve leggerla dai PDF.
- **Piano di accumulo.** Genera anche un `DEPOSIT` lo stesso giorno: l'addebito diretto («… piano di accumulo»).
- **Apertura del conto.** Ci sono micro-movimenti di verifica (centesimi e qualche euro, in entrata e in uscita): vanno trattati come normali depositi e prelievi.
- **Trasferimenti interni.** Compaiono su entrambi i lati con lo stesso giorno e lo stesso importo.
- **Saldi.** La somma degli `amount` eseguiti dà il saldo del conto nell'app, salvo mezzi centesimi degli importi non arrotondati.
- **Interessi del conto deposito.** Sono mensili, con data a mezzanotte UTC. I dettagli danno lordo e ritenuta; `transactionHistory` ripete solo stato e data.

## 6. Lacune note e verifiche da fare

- **Mancano campioni reali** di:
  - vendita, dividendo, tasse sul broker;
  - storno (`isCancellation` vero), ordine eseguito in parte, crypto, ELTIF;
  - trasferimento titoli, corporate action;
  - più conti deposito (`lf_account_index` maggiore di 1).
- **Ordine eseguito in parte e poi annullato o scaduto**: `shares` risulterebbe 0, perché i dettagli di quegli ordini non vengono letti ❓.
- **Crypto**: `cryptoSpreadFee` potrebbe essere già compreso nel prezzo; in quel caso sommarlo in `fee` lo conterebbe due volte ❓.
- **`lastEventDateTime`**: non sappiamo se è l'ora dell'operazione o quella del regolamento ❓.
- **Righe di cassa**: nel file Prime hanno `fee` a `0` e `tax` vuoto, nelle nostre sono vuoti entrambi.
- **Non esportati** (todo `broker-details-fields`): prezzo limite, storico dell'ordine (creato, esecuzioni parziali), nome completo della borsa, documenti (contratto, informativa sui costi). Per aggiungerli bisogna catturare la query della pagina di dettaglio del broker.
- **Sviluppo senza conto** (todo `ext-fixture-capture`): uno strumento nel pannello che scarichi risposte anonimizzate.
- **CSV veri del developer**: restano nella sua cartella dei download. Servono per provare l'import a mano; non vanno mai copiati nel repo o nel journal.

## 7. Riferimenti nel codice LibreFolio

I numeri di riga sono quelli del baseline `9eb01c756` e vanno ricontrollati.

- **Guida e modelli BRIM**: `mkdocs_src/docs/developer/architecture/patterns/brim_plugin_guide.md`, la doc dev di Danske (report set titoli + cassa), la skill `brim-plugin`, `backend/app/services/brim_providers/`.
- **Broker e cassa**: `models.py`, un pool di cassa per valuta (circa righe 522-553 e 757-775).
- **`CASH_TRANSFER`**: rifiutato nello stesso broker in `transaction_service.py` (circa 193-197). La promozione di WITHDRAWAL + DEPOSIT a `CASH_TRANSFER` e `promote-suggest` stanno circa alle righe 705-712.
- **Motore**: `portfolio_engine.py`, circa 300-356.
  - una coppia con entrambi i lati nel perimetro non è un flusso;
  - un `DEPOSIT` o un `WITHDRAWAL` non collegato è un flusso esterno;
  - gli interessi sono un provento.
- **Lettura dei file**:
  - `file_preview.py` legge `.csv .xlsx .xls`, `_brim_io` legge `.csv .txt`; con `detect_csv_delimiter` e `_open_text` (gestisce il BOM).
  - Lo ZIP non viene letto: l'utente estrae i due CSV, oppure si fa accettare lo ZIP al plugin o al core ❓.
- **Coppie già emesse**: oggi solo DEGIRO ne produce (`FX_CONVERSION`, nello stesso broker). Nessun plugin emette coppie tra broker diversi.
- **Superfici previste**:
  - codice: `backend/app/services/brim_providers/broker_scalable.py`;
  - campioni: `sample_reports/scalable-*.csv`, solo sintetici;
  - favicon;
  - documentazione: `mkdocs_src/docs/user/transactions/import/scalable.en.md` e l'elenco dei provider nella doc dev;
  - eventuali chiavi i18n per le notice;
  - test BRIM esterni, da scrivere con `test-author`.

## 8. L'esportatore: cose da ricordare per la manutenzione

- **Conto deposito.** L'app degli interessi accetta solo le query GraphQL delle sue pagine, identiche carattere per carattere.
  - La lista si legge con la «ricetta» Apollo che la pagina contiene.
  - Per i dettagli si usa la query della pagina, fissata da un test sha256. Se Scalable la cambia, quel test diventa rosso.
- **Broker.** Il backend accetta le nostre query: la query dei dettagli chiede solo i campi che scriviamo.
- **Carico sul server.** Una richiesta alla volta, con pause e attesa progressiva sui 429. Le richieste dei due conti, letti in parallelo, passano dalla stessa coda.
- **Rilascio di una nuova versione.**
  1. Stessa versione in `manifest.json` e `package.json`.
  2. Data sul capitolo del CHANGELOG.
  3. Commit.
  4. `git tag -a v<versione>`, poi push del branch e del tag.
- **Schermate.** Quelle del pannello vengono dall'e2e in Edge con `SHOTS_DIR`. La scheda di `chrome://extensions` è stata rifatta con uno script usa e getta (Chrome headless, `Extensions.loadUnpacked`), che non è nel repo.

## 9. Regole per la prossima fase

- **Avvio.**
  - Il primo turno è solo analisi: worktree, baseline e verifica dei riferimenti della §7.
  - Poi il piano, e l'autorizzazione del developer passa dal coordinatore.
- **Corsia.**
  - Parametri: `--test-port 6163 --data-dir /tmp/librefolio-r2-s`.
  - Comando: `PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py …`.
  - Porte da non toccare: 6040, 6041, 6150.
- **Git.** Mai commit, merge, push, rebase o reset; i messaggi di commit si propongono in `/tmp/libreFolio_commit_*.txt`.
- **Dati.** Fixture solo sintetiche. Mai CSV veri, id, riferimenti o importi reali nel repo o nel journal.
- **Specialisti.**
  - i test con `test-author`;
  - la documentazione con `docs-writer`, solo in inglese;
  - la skill `brim-plugin`.
- **Baseline.**
  - Il worktree è a `108a2adf5` (train 17), pulito.
  - I file di terzi scaricati durante la ricerca sono stati spostati fuori dal worktree, nella cartella della sessione S.
  - Ho chiesto al coordinatore di portarlo all'ultimo `dev_release2`, che all'ultimo controllo era `3af9aac63`.

## 10. Todo aperti

| Todo | Stato | Dipende da |
|---|---|---|
| `brim-broker-scalable`: plugin BRIM | da fare | — |
| `doc-two-brokers`: guida utente con i due broker | da fare | plugin |
| `broker-logos`: SVG dei due broker | da fare | guida |
| `broker-details-fields`: prezzo limite, storico, documenti | da fare | cattura della query di dettaglio |
| `ext-fixture-capture`: risposte anonimizzate per sviluppare senza conto | da fare | — |
| `store-distribution`: Chrome Web Store | solo se il progetto cresce | — |
| `exporter-cli` | non previsto | — |

## 11. Fonti

- **Repo dell'esportatore**: `README.md`, `docs/formats/scalable.md`, `docs/HOW-IT-WORKS.md`, `docs/RISKS.md`, `docs/DEVELOPMENT.md`, `PRIVACY.md`, `CHANGELOG.md`.
- **Piano della fase dell'esportatore** (nella sessione S): §2.4 (CSV Prime), §4 (integrazione), §12 (esecuzione), fonti F1–F38.
- **Campioni Prime**: `VibeNL/GhostfolioSidekick`, cartella `Parsers.UnitTests/TestFiles/ScalableCapital/Prime/` (licenza MIT).
- **Export Prime reali pubblici**, letti in memoria e mai copiati: `athimannil/scalable-to-tradingview` (`app/data/original.csv`), `popokatapepel/popos-taco-trade` (`2026_05_11_12_24_59_ScalableCapital-Broker-Transactions.csv`).
- **Strumento ufficiale**: `ScalableCapital/scalable-cli`, che riporta `isCancellation` senza documentarlo.
- **Commissioni**: centro assistenza IT, «Cosa sono i PRIME partner e quali vantaggi offrono?»; `de.scalable.capital/en/trading-costs`.
