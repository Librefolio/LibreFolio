# Issue #26 — Danske Bank: analisi degli export

> Workstream **L - Danske Bank** · 2026-09-28 · piano collegato:
> [plan-phase00BrimDanskeBank.prompt.md](plan-phase00BrimDanskeBank.prompt.md).
> Nessun valore dei file reali: solo struttura, forme mascherate, parole di servizio.
> §0–§7 scritti prima del fast-forward a `ea30d5ccf` (non dipendono dalla baseline);
> §8 scritto dopo, con le verifiche sul codice.

## 0. Metodo

- I file sono stati letti in sola lettura dalla copia locale degli allegati della issue, fuori dal repo.
- 4 script d'ispezione tenuti fuori dal repo, nella cartella di sessione dell'agente. Stampano solo
  nomi di colonna, tipi, formati mascherati (cifre→`9`, lettere→`A`), conteggi, booleani e
  parole di servizio. Script e log vanno cancellati a fine lavoro.
- Issue #26 letta con `gh`: corpo minimo, nessun commento, allegati = i due file.

## 1. Cosa sono i due file

Tutti e due vengono da **Danske Bank Finlandia** (interfaccia in finlandese). Sono **le due
facce della stessa osakesäästötili (OST)**, il conto finlandese di "risparmio azionario".
Per legge l'OST è formato da un **conto cassa** (*rahatili*) e da un **deposito titoli**
(*säilytystili*) [F1]:

| File | Cos'è | Contenuto |
|---|---|---|
| `ACCOUNTNUMBER.csv` | estratto del **conto cassa** OST (*tilitapahtumat*) | movimenti di cassa, saldo progressivo |
| `Transactions.xlsx` | lista **transazioni del deposito titoli** (sezione *Sijoitukset*) | operazioni su titoli |

Le prove:

- il CSV contiene le etichette di banca `Nosto osakesäästötililtä` (prelievo dall'OST) e
  `Vero osakesäästötililtä` (ritenuta sul prelievo: in OST la tassa si paga solo quando si
  preleva, 30 % sulla quota di rendimento, trattenuta dalla banca [F1]) e `Palvelumaksut`
  (canoni di servizio, che la banca addebita sul conto cassa OST [F1]);
- l'XLSX ha la colonna `Säilytystili` (deposito titoli);
- **ogni riga dell'XLSX con un importo ha la sua riga gemella nel CSV**, con la data del CSV
  uguale alla data valuta dell'XLSX e l'importo del CSV uguale a `Summa`.

## 2. CSV `ACCOUNTNUMBER.csv`

**Formato**

- Codifica **ISO-8859-1** (compatibile con cp1252). Non è UTF-8 e non ha BOM. Gli unici
  caratteri non ASCII sono `ä` e `ö`.
- Separatore `;`, **nessun quoting**, sempre 6 campi, header alla riga 1, nessun preambolo,
  nessuna riga vuota, fine riga **LF**.
- Righe **dalla più recente alla più vecchia**.
- Nel file originale il nome è il numero di conto (l'autore l'ha sostituito con un
  segnaposto). Quindi `can_parse` non può basarsi sul nome del file.
- Nessuna colonna valuta: il conto è implicitamente in EUR (da confermare).

**Colonne**

| Colonna | Significato | Tipo e formato | Note |
|---|---|---|---|
| `Pvm` | data (registrazione e valuta) | `dd.mm.yyyy`, giorno prima del mese (verificato) | per i trade coincide con `Arvopäivä` dell'XLSX |
| `Saaja/Maksaja` | beneficiario/ordinante oppure descrizione | testo, al massimo circa 24 caratteri (sembra troncato a larghezza fissa) | vedi le famiglie qui sotto |
| `Määrä` | **importo** | virgola decimale, `-` davanti per gli addebiti, nessun `+`, nessun separatore delle migliaia nel campione; 0/1/2 decimali (gli zeri finali mancano) | ⚠️ nell'XLSX `Määrä` vuol dire **quantità** |
| `Saldo` | saldo progressivo dopo la riga | come `Määrä` | coerente al 100 % se letto dal più recente |
| `Tila` | stato della riga | **costante** `Toteutunut` («realizzato, contabilizzato») | colonna costante n. 1 |
| `Tarkastus` | spunta «controllato/riconciliato» | **costante** `Ei` («no») | colonna costante n. 2 |

**Famiglie di righe in `Saaja/Maksaja`** (etichette di banca, niente valori)

| Etichetta | Segno | Significato | Gemella nell'XLSX |
|---|---|---|---|
| `Osto <nome titolo>` | − | regolamento di un acquisto | sì (nome identico) |
| `Myynti <nome titolo>` | + | regolamento di una vendita | sì |
| `<nome titolo> <riferimento di 10 cifre>` | + | incasso di un provento (`Tuotto`) | sì |
| nome del titolare (l'autore l'ha sostituito con `ACCOUNT_HOLDER_NAME`) | + | versamento sul conto | no |
| `Nosto osakesäästötililtä` | − | prelievo dall'OST | no |
| `Vero osakesäästötililtä` | − | ritenuta fiscale sul prelievo OST | no |
| `Palvelumaksut …` | − | canone di servizio | no |

## 3. XLSX `Transactions.xlsx`

**Formato**

- **Ri-salvato da LibreOffice su Linux** (lo dicono i metadati `docProps/app.xml`). Non è il
  file originale di Danske: l'autore l'ha modificato per anonimizzarlo. Rispetto
  all'originale possono cambiare il generatore, gli stili e le righe d'intestazione.
- Un solo foglio (`Sheet1`), header alla riga 1, 11 colonne (A:K), nessun preambolo né piè di
  pagina, nessuna cella unita, niente filtri né tabelle.
- Le **date sono testo** `dd.mm.yyyy` (formato General). I numeri sono celle numeriche.
- Un header contiene **HTML letterale**: `Palkkio<br/>sis. Alv`. Quindi l'export nasce da una
  tabella HTML, con l'etichetta su due righe.
- La **colonna H non ha intestazione**.
- L'ordine delle righe non è monotono per data né per titolo: il parser non deve dipendere
  dall'ordine.
- Esistono righe con stessa data, stesso titolo e stesso tipo ma quantità o prezzo diversi
  (esecuzioni parziali o ordini separati): **non si fondono mai**.

**Colonne**

| Col. | Header | Significato | Tipo e formato | Note |
|---|---|---|---|---|
| A | `Kauppapäivä` | data dell'operazione | testo `dd.mm.yyyy` | |
| B | `Arvopäivä` | data valuta (regolamento) | testo `dd.mm.yyyy` | ≥ A: +1…4 giorni per i trade, uguale ad A per gli eventi |
| C | `Sijoituskohde` | nome del titolo | testo | **niente ISIN, ticker, mercato o valuta**; suffissi societari (`Oyj`, `Abp`, `AB`, `Inc`, `Ltd`, `SE`…) e a volte una classe tra parentesi |
| D | `Määrä` | **quantità con segno** | intero nel campione | + = entrata/acquisto, − = uscita/vendita |
| E | `Kurssi` | prezzo unitario | float, fino a 4 decimali | **nella valuta di quotazione del titolo, che il file non dichiara**; 0 per gli eventi |
| F | `Palkkio<br/>sis. Alv` | commissione IVA inclusa | numero | **sempre 0** (costante) |
| G | `Summa` | importo netto regolato | float, 2 decimali | − acquisti, + vendite e proventi; **vuoto** per gli eventi senza cassa |
| H | *(senza nome)* | **valuta di `Summa`** | ISO 4217 | costante `EUR`, vuota dove `Summa` è vuota |
| I | `Tila` | stato | **costante** `Toteutettu` («eseguito») | attenzione: non è la stessa forma del CSV (`Toteutunut`) |
| J | `Toimeksiantotyyppi` | tipo di ordine o di evento | 6 valori, vedi sotto | |
| K | `Säilytystili` | deposito titoli | **costante** | l'autore ha sostituito il valore con il segnaposto `Account_number` |

**`Toimeksiantotyyppi`: i 6 valori**

| Valore | Traduzione | Nel campione |
|---|---|---|
| `Rajakurssi` | ordine a prezzo limite | acquisti **e** vendite |
| `Päivän kurssi` | ordine al prezzo del giorno | solo vendite |
| `Pikakauppa` | trade rapido | acquisto |
| `Tuotto` | provento (dividendo o distribuzione) | quantità > 0, prezzo 0, `Summa` > 0 |
| `Jakautuminen, vanha` | scissione: linea **vecchia** | quantità < 0, niente prezzo né cassa |
| `Jakautuminen, uusi` | scissione: linea **nuova** | quantità > 0, niente prezzo né cassa |

**Cosa emerge**

1. **La direzione del trade viene dal segno di `Määrä`, non dal tipo.** Il tipo è l'ordine
   (limite o prezzo del giorno). Nell'OST di Danske gli acquisti sono sempre a limite, mentre
   le vendite possono essere a limite o al prezzo del giorno [F2]. Il campione è coerente: le
   `Päivän kurssi` sono tutte vendite. Per ogni trade `Määrä` e `Summa` hanno segno opposto.
2. **`Summa` ≠ `Määrä × Kurssi`.**
   - Per i titoli quotati in EUR la differenza è piccola e va sempre a sfavore del cliente
     (gli acquisti costano di più, le vendite incassano di meno). È compatibile con una
     **commissione già inclusa in `Summa`**, mentre la colonna commissione vale 0.
   - Per alcuni titoli il rapporto è lontano da 1 (≪ 1): il **prezzo è in valuta estera** e
     `Summa` è in EUR. Quindi la valuta del prezzo non è nel file.
3. **`Tuotto`**: la quantità è quella posseduta a quella data. L'ho verificato: coincide con
   la posizione netta ricostruita dal file. Non è un movimento di posizione, è un **provento
   in contanti**.
4. **`Jakautuminen`**: `vanha` toglie l'intera posizione del titolo (la quantità è uguale
   alla posizione netta). Due righe `uusi` aggiungono due titoli nuovi, con nomi diversi dal
   vecchio e fra loro, 1:1 ciascuno, alla stessa data. Dopo ci sono trade sui titoli nuovi.
   È una **scissione societaria (demerger)**. Fiscalmente è neutra e il costo
   d'acquisto si conserva, ripartito sulle azioni nuove [F3], ma **nel file il costo non c'è**.

## 4. Le colonne costanti: cosa sono e se servono

| File | Colonna | Valore | Cos'è | Serve? |
|---|---|---|---|---|
| CSV | `Tila` | `Toteutunut` | stato della riga: contabilizzata, non in attesa | **sì, come filtro**: si importano solo le righe contabilizzate; gli altri stati (per es. le prenotazioni `Varaus`, che un importer open source scarta [F4]) si saltano con un warning |
| CSV | `Tarkastus` | `Ei` | spunta di riconciliazione che l'utente può mettere nel netbank. Nel CSV danese la stessa coppia si chiama `Status` = `Udført` e `Afstemt` = `Nej` [F5][F6]; è una spunta di contabilità personale e non cambia i numeri della banca [F7] | **no**: si ignora e non si pretende |
| XLSX | `Tila` | `Toteutettu` | stato d'esecuzione | **sì, come filtro** (solo `Toteutettu`; gli altri valori vanno chiesti all'autore) |
| XLSX | `Säilytystili` | segnaposto | identificativo del deposito titoli | **sì, per un controllo**: un file con più depositi va segnalato. Non va mai salvato né loggato, perché è un numero di conto |
| XLSX | colonna H | `EUR` | valuta di `Summa` | **sì, è essenziale**: è la valuta di ogni riga |
| XLSX | `Palkkio<br/>sis. Alv` | `0` | commissione IVA inclusa | si trascrive così com'è (0 = nessuna commissione separata); nella doc si spiega che la commissione sembra inclusa in `Summa` |

## 5. CSV contro XLSX

- **Stesso periodo.** Il CSV va avanti qualche giorno in più per il regolamento.
- **Il lato cassa dell'XLSX è contenuto nel CSV.** Ogni riga XLSX con `Summa` ha la gemella
  nel CSV (`Pvm` = `Arvopäivä`, `Määrä` = `Summa`).
- **Solo nell'XLSX**: quantità, prezzo, data dell'operazione, tipo d'ordine, eventi senza cassa
  (la scissione), stato, deposito, valuta esplicita.
- **Solo nel CSV**: versamenti, prelievi, ritenuta sul prelievo OST, canoni di servizio, saldo
  progressivo.
- **In nessuno dei due**: ISIN, ticker, valuta di quotazione, cambio, commissione valorizzata,
  ritenute sui dividendi.
- **Conclusione.**
  - Per i titoli l'XLSX è il più informativo: su questo sono d'accordo l'autore e il developer.
  - Da solo però non basta per la cassa. Un portafoglio completo richiede tutti e due i file,
    **con de-duplicazione**: se si importa l'XLSX, le righe `Osto`, `Myynti` e dei proventi del
    CSV non vanno importate di nuovo.

## 6. Ricerca online: fonti

| # | Fonte | Cosa conferma |
|---|---|---|
| F1 | Verohallinto (Agenzia delle entrate finlandese), *Osakesäästötili* — <https://www.vero.fi/henkiloasiakkaat/omaisuus/sijoitukset/osakes%C3%A4%C3%A4st%C3%B6tili/> | OST = conto cassa + deposito titoli; si versa solo denaro e si preleva solo denaro; tasse solo al prelievo (ritenuta del 30 % sulla quota di rendimento, calcolata dalla banca); canoni addebitati sul conto cassa OST |
| F2 | Danske Bank FI, *Usein kysyttyä Osakesäästötilistä* — <https://danskebank.fi/sinulle/asiakaspalvelu/saastaminen-ja-sijoittaminen/osakesaastotili> | tipi d'ordine *päivän kurssi* e *rajakurssi*; in OST acquisti sempre a limite, vendite in tutti e due i modi; nell'ordine si scelgono deposito titoli e conto cassa |
| F3 | Verohallinto, *Yritysjärjestelyt ja verotus – jakautuminen* — <https://www.vero.fi/syventavat-vero-ohjeet/ohje-hakusivu/49340/yritysjarjestelyt-ja-verotus-jakautuminen4/> | scissione fiscalmente neutra, continuità, costo d'acquisto conservato |
| F4 | `trahkoi/ynab-danske-csv` (convertitore open source, formato FI) — <https://github.com/trahkoi/ynab-danske-csv/blob/master/src/main/resources/application.properties>, <https://github.com/trahkoi/ynab-danske-csv/blob/master/src/main/java/fi/rahkoi/ynab/mapper/DanskeRecordFieldSetMapper.java>, <https://github.com/trahkoi/ynab-danske-csv/blob/master/src/main/java/fi/rahkoi/ynab/processor/DanskeRecordFilterProcessor.java> | stesse 6 colonne, `iso-8859-1`, `dd.MM.yyyy`, virgola decimale, **spazi rimossi dagli importi** (quindi l'originale può avere separatori delle migliaia con spazio), righe `Varaus` scartate |
| F5 | `Jothom2912/Finance-Tracker`, parser Danske DK — <https://github.com/Jothom2912/Finance-Tracker/blob/master/services/transaction-service/app/application/csv_parsers/danske_bank.py> | variante danese: Windows-1252, `;`, **tutti i campi tra virgolette**, `Dato;Kategori;Underkategori;Tekst;Beløb;Saldo;Status;Afstemt` |
| F6 | `bank2ynab`, sezione `[DK Danske Bank]` — <https://github.com/bank2ynab/bank2ynab/blob/develop/bank2ynab/data/bank2ynab.conf> | stesso header danese; nome file DK `Accountname-<conto>-<data>.csv` |
| F7 | homepage.dk, *Afstemt i netbank betydning* — <https://homepage.dk/afstemt-i-netbank-betydning/> (fonte secondaria) | «afstemt» è una spunta di riconciliazione interna |

Senza esito:

- **Il layout XLSX degli investimenti non ha documentazione pubblica** e nessun importer open
  source. Ho cercato su GitHub `Toimeksiantotyyppi`, `Sijoituskohde`, `Säilytystili`,
  `Kauppapäivä`: nessun parser.
- Il listino OST di Danske (PDF) non era leggibile qui: la struttura delle commissioni non è
  verificata.
- Le risposte «AI» dei motori di ricerca erano generiche e le ho scartate.

**Altri export Danske da chiedere**

- l'export delle **posizioni** (*Omistukset*), per avere ISIN e valuta;
- le **conferme d'eseguito** (*kauppavahvistus*, PDF), con ISIN, mercato, cambio e commissione;
- l'export di un **deposito ordinario** (*arvo-osuustili*, non OST), con dividendi e ritenute;
- i **fondi** (Danske Invest), con quote frazionarie;
- gli stessi file con l'interfaccia in **inglese o svedese**.

Le varianti DK, SE e NO sono piattaforme diverse, con un altro header (vedi F5): fuori scope
finché non arrivano campioni.

## 7. Implicazioni preliminari per il plugin (da verificare sulla guida dopo il FF)

- **Primo formato: l'XLSX del deposito.** Il CSV del conto cassa viene dopo e importa solo
  gli eventi di cassa, saltando i regolamenti già coperti dall'XLSX.
- **`can_parse` sull'insieme degli header finlandesi**, per entrambi i formati.
  - Deve reggere al `<br/>` negli header, all'header vuoto, alle date sia testo sia data, ai
    numeri sia numerici sia testo.
  - Per il CSV: encoding e delimitatore rilevati (con i metodi della base), quoting opzionale,
    CRLF/LF, spazio o NBSP come separatore delle migliaia.
- **Mappatura provvisoria per l'XLSX**:

  | Riga | Tipo |
  |---|---|
  | `Määrä` > 0 e `Summa` < 0 | BUY |
  | `Määrä` < 0 e `Summa` > 0 | SELL |
  | `Tuotto` | DIVIDEND, con quantità 0 |
  | `Jakautuminen vanha/uusi` | ADJUSTMENT ∓ senza cassa (costo da decidere) |
  | `Tila` ≠ `Toteutettu` | skip con warning |
  | segni incoerenti | errore di validazione |

- **Valuta**: dalla colonna H, riga per riga. Il **prezzo** è in una valuta non dichiarata;
  come trattarlo dipende dallo schema BRIM (da verificare). Non si ricalcola mai
  `Summa`/`Määrä` e non si converte.
- **Asset**: chiave = `Sijoituskohde` normalizzato, ID finto negativo, info asset solo con il
  nome. Il matching lo fa l'interfaccia utente.
- **Decisioni che vedo già** (le dettaglio nel piano):
  - la scissione senza costo;
  - il prezzo in valuta ignota;
  - le righe ambigue del CSV (un versamento e un provento hanno testi simili);
  - aspettare o no le risposte dell'autore;
  - il permesso per il campione sintetico, che blocca `sample_reports/` e i test.

## 8. Dopo il fast-forward (HEAD `ea30d5ccf`): verifiche su codice e precedenti

**Schema delle transazioni**

- `TXCreateItem` **non ha un campo prezzo**: ci sono solo `quantity` e `cash`. Quindi il
  dubbio sulla valuta di `Kurssi` si scioglie da solo: il prezzo non si salva. Al massimo
  si mette nella `description`, come testo.
- `date` è descritto come «Settlement date», e il docstring di `TransactionType` dice che
  tutti i calcoli usano la data di regolamento.
- I plugin non fanno tutti la stessa scelta: Fineco usa la data valuta; Saxo, Disnat,
  InvestEngine e IBKR la data dell'operazione.
- Proposta: `Arvopäivä` come data, `Kauppapäivä` nella descrizione. Si allinea anche con
  le date del CSV.

**Helper di lettura**

- **Bug nella base, verificato su un file sintetico ISO-8859-1 separato da `;`**:
  `BRIMProvider.detect_csv_delimiter` restituisce `,`.
  - Il motivo: apre il file solo in utf-8-sig; al primo errore di decodifica il campione
    resta vuoto e il fallback sceglie `,`.
  - `_brim_io.detect_delimiter` e `_brim_io.read_rows` provano più encoding e funzionano.
  - Il plugin userà `_brim_io`, come fanno Intesa e CA. La correzione della base la
    propongo soltanto: il file non è mio.
- `_brim_io` fornisce quello che serve:
  - `read_rows` (CSV e XLSX);
  - `find_header_row` (confronto per sottostringa);
  - `build_col_index` (label esatte, quindi va messa anche `palkkio<br/>sis. alv`);
  - `to_decimal_it` (regge spazio e NBSP come separatore delle migliaia);
  - `to_date` (`%d.%m.%Y`).

**Regole della guida da applicare**

- ID finti positivi alti e decrescenti.
- `BRIMNotice` sempre con un `code`.
- **Warning nella lingua del report**, cioè in finlandese.
- `field_todos`.
- Un solo plugin con più formati e `test_file_patterns`.
- Registrazioni: pagina, card e riga della tabella nell'indice ×4, nav, `providers_list`.

**Scissione nel motore**

- Un `ADJUSTMENT` con `cost_basis_override` è un conferimento o un prelievo *in kind* di
  capitale.
- Un `ADJUSTMENT` negativo toglie il costo WAC.
- Per una scissione neutra entrambe le gambe devono avere il cbo.
- La regola 12 vieta `cost_basis_mode` quando qty < 0.
- Il precedente è `broker_generic_csv`: todo `blocker` su `cost_basis_override` con reason
  `corporate_action`, e `TransactionBulkModal` blocca il commit finché l'utente non lo
  risolve.

**Precedente Crédit Agricole (dalla pagina utente)**

- L'import principale è l'estratto conto, con la cassa reale.
- L'export titoli è facoltativo e serve per la storia più vecchia. È cash-neutral: ogni
  acquisto ha un versamento automatico e ogni vendita, cedola o scadenza un prelievo
  automatico, tutti con tag `auto_cash`.
- I due file si combinano **tagliandoli nel tempo**, senza sovrapposizione.
- Il saldo iniziale si inserisce a mano come versamento.

**Danske è diversa**

- Il CSV non ha le quantità, quindi non può essere il file principale per i titoli.
- I due file si sovrappongono del tutto: vanno divisi **per contenuto**, non per tempo.

**Prezzi e identificazione**

- `yahoo_finance.search()` usa `yf.Search` per nome. L'ho provato con nomi nordici
  generici, non presi dai file: restituisce le quotazioni di Helsinki (`.HE`), Stoccolma
  (`.ST`) e Copenaghen (`.CO`), più ADR, OTC e piazze tedesche.
- Quindi il prezzo è coperto; l'ambiguità sta nella scelta della quotazione giusta.
- Gli altri provider sono JustETF (ETF per ISIN), Borsa Italiana, CSS scraper e
  Scheduled Investment.

**Favicon**: `https://danskebank.fi/favicon.ico` risponde 200, `image/x-icon`, senza CORP:
si può incorporare.

**Test**: la suite parametrica copre il plugin da sola appena c'è il campione. I test
specifici vanno in `test_brim_providers.py`, che è l'unico file eseguito dal runner:
quindi si aggiunge una classe a un file condiviso.
