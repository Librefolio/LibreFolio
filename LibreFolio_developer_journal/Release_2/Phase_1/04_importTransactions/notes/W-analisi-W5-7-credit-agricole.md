# W5-7 · Crédit Agricole sui report set — analisi (W, 24/10/2026, base `4a2ec35db`)

Solo analisi: nessun codice, nessun test scritto. Decide il developer.

## 0. In breve

**Sì, CA può passare al modello dei report set di Danske, e conviene.** Con i suoi export veri il modello di oggi (due import separati) **conta due volte** cedole, scadenze e acquisti, e nessun controllo se ne accorge: gli importi non coincidono (la cedola entra netta da un lato, lorda più ritenuta dall'altro).
Un set «titoli + conto» abbina le righe che sono lo stesso fatto visto da due parte, e dà alla cassa un punto di apertura dai saldi che il file XLSX porta nella testata.
Costo stimato: **7-10 giorni** (un lotto grosso come Danske). Tre decisioni al developer in fondo (§8), la prima è «si fa o no».

Non ho toccato nessun dato: ho letto gli export veri in sola lettura e qui ci sono solo conteggi e importi aggregati, senza nomi né numeri di conto.

## 1. Cosa ho guardato

La cartella dei materiali di un utente reale (la stessa che ha servito per scrivere il plugin): 3 sottocartelle, 8 file utili (CSV e XLSX), più uno snapshot dei titoli.

| Famiglia | File | Righe | Periodo delle righe | Testata |
|---|---|---|---|---|
| Conto «Lista Movimenti Conto» **A** | CSV + XLSX identici | 460 | 28/10/2024 → 30/07/2026 | XLSX: periodo dal 01/07/2024, saldo iniziale e finale |
| Conto **B** | CSV + XLSX identici | 94 | 01/08/2024 → 31/12/2024 | XLSX: dal 01/08/2024 al 01/01/2025, saldi |
| Conto **C** | solo XLSX | 71 | 07/05/2026 → 03/08/2026 | XLSX: dal 05/05/2026 al 05/08/2026, saldi |
| Deposito Titoli (grande) | CSV + XLSX identici | 94 | 05/06/2024 → 01/06/2026 | XLSX: dossier, c/c di appoggio, «Liquidità», data aggiornamento |
| Deposito Titoli (vecchio) | XLSX | 36 | 05/06/2024 → 13/06/2024 | sottoinsieme del grande (solo i trasferimenti di giugno 2024) |
| «Andamento Portafoglio» | XLSX | 1 foglio | stato al 05/08/2026 | quantità, prezzo medio, valore, liquidità per titolo |

**Verifica che ho fatto sul plugin attuale (1.5.0):** il CSV e l'XLSX dello stesso export danno la **stessa** lettura (A: 507 transazioni sia da CSV sia da XLSX). Quindi l'XLSX non è un estratto: ha tutte le righe **più la testata con i saldi**, che il CSV non ha. Il file «Andamento Portafoglio» oggi non è riconosciuto da nessun plugin CA (`can_parse` = falso).

## 2. Com'è oggi

Un solo plugin (`broker_credit_agricole`, 1663 righe) con **due formati**, scelti dalla riga d'intestazione: «Deposito Titoli» (posizioni e cedole) e «Lista Movimenti Conto» (cassa). Ognuno si importa da solo. Nessuno dei due ridefinisce `report_roles`/`detect_role`: non è un plugin a set.

- **Titoli da solo**: ogni acquisto/rimborso porta una gamba di cassa **inventata** (`auto_cash`: 60 righe nel campione, 56 prelievi e 4 versamenti), perché il file non ha il denaro (`plugin.py:980`). Le 36 righe di giugno 2024 sono trasferimenti da un altro dossier (successione): entrano come rettifiche con il prezzo di carico, senza versamento.
- **Conto da solo**: le righe di cassa sono vere. Gli acquisti/vendite di titoli le riconosce con un'euristica sui nomi e sui nominali (`try_account_trade`); quando non ci riesce mette un campo da correggere bloccante (`ca_account_trade_unresolved`).

### La doppia importazione (misurata sul campione)

Se l'utente importa tutti e due, gli stessi fatti entrano due volte:

| Fatto | Nell'export titoli | Nell'export conto | Conseguenza |
|---|---|---|---|
| 51 cedole (totale 13.553,60 EUR) | 51 `INTEREST` nette | 51 righe «CEDOLE, DIVIDENDI…» (stesso importo netto, 0-3 giorni dopo) | reddito contato **due volte** (in più, sul conto, la ritenuta diventa una `TAX` e la cedola lorda) |
| 2 scadenze di titoli (95.665,00 e 30.105,00 EUR) | `SELL` + incasso | 2 righe «TITOLI SCADUTI» | vendite doppie |
| 4 acquisti + 1 rimborso fondo | `BUY` con cassa inventata | 4 «COMPRAVENDITA» (e 1 «GIROCONTO» per il rimborso) | posizioni e cassa doppie |

Il controllo dei doppioni non se ne accorge: la cedola entra **netta** (es. `x`) dal lato titoli e **lorda + ritenuta** dal lato conto (`x + r` e `-r`), quindi gli importi non coincidono; solo 4 `INTEREST` su 53 hanno un gemello con lo stesso importo, 3 `BUY` su 4 e 2 `SELL` su 3. Lo stesso utente non lo vedrebbe dalla lista.

## 3. I fatti degli export veri

1. **Una cedola, un acquisto sono la stessa cosa in due file, e si abbinano per importo al centesimo.** Cedole: 51 su 51 con importo identico e data del conto 0-3 giorni dopo (30 lo stesso giorno, 13 a +1, 7 a +2, 1 a +3). Acquisti/rimborso: 5 su 5 con importo identico, ma la data del conto va da **-2 a +8 giorni** (es. acquisto del 17/02/2025 sul conto il 25/02/2025; sottoscrizione SICAV del 07/11 sul conto il 05/11). Il rimborso del fondo (10/11/2025) è un «GIROCONTO/BONIFICO» il giorno dopo, non una «COMPRAVENDITA».
2. **La catena dei saldi del conto chiude, tranne un file.** Saldo iniziale + somma delle righe = saldo finale:
   - B: 2.425,89 + 13.349,49 = 15.775,38 ✔
   - C: 27.115,09 + 36.566,66 = 63.681,75 ✔
   - **A: 2.984,99 + 50.087,17 = 53.072,16, ma il saldo finale dice 58.822,00: mancano 5.749,84.** La testata di A parte dal 01/07/2024, le righe dal 28/10/2024.
3. **Le righe che mancano ad A si ritrovano.** Luglio 2024: nessun file lo copre (saldo 01/07 = 2.984,99, saldo 01/08 = 2.425,89 → -559,10 di movimenti che non sono in nessun file). Da agosto a metà ottobre 2024 le ha B (5.595,51), più **3 righe del 28/10/2024 (713,43) che B ha e A no**: A si ferma a metà giornata. Somma: -559,10 + 5.595,51 + 713,43 = 5.749,84, esattamente il buco. La catena dei saldi **prova** dove manca denaro.
4. **Tre file di conto si sovrappongono**: B è dentro A per ottobre-dicembre 2024 (stesse righe, tranne le 3 del taglio), C coincide con A dal 07/05/2026 al 30/07/2026 (68 transazioni uguali, verificato sull'uscita del plugin) e aggiunge 31/07-03/08.
5. **Il CSV non ha saldi**: solo l'XLSX ha «Saldo Iniziale», «Saldo Finale», «Data dal/al». Il «Data dal» può essere più indietro della prima riga (A).
6. **Trabocchetti di formato**: «Data Aggiornamento» del Deposito Titoli è scritta `25/07/02026` (anno a cinque cifre: un `%Y` la rifiuta); `Data Val.` ≠ `Data Op.` in 263 righe su 460 (regola W5-1: si data con l'operazione, la valuta serve per i regolamenti); `Divisa` compare due volte nel file titoli e vale `000` nella riga delle scadenze.
7. **Il periodo coperto**: i titoli arrivano al 05/06/2024 (prima riga), il conto va indietro solo fino ad agosto 2024 (B): la banca dà al massimo ~2 anni di conto (B è stato scaricato il 01/08/2026 con inizio 01/08/2024). I trasferimenti di giugno 2024 cadono **prima** dell'inizio del conto.
8. **Lo snapshot «Andamento Portafoglio»** dà quantità, prezzo medio e liquidità al 05/08/2026; la sua «Liquidità» coincide con il saldo finale di C (63.681,75).

## 4. Il modello di Danske applicato a CA

Danske ha due ruoli (custodia, cassa) combinati in un file con una riga per fatto, zone e punti di verità. CA è la stessa forma.

**Ruoli** (`report_roles`):

| Ruolo | Cosa | Obbligatorio | Più file | Estensioni | `max_history` | `must_cover` |
|---|---|---|---|---|---|---|
| `securities` | Deposito Titoli | sì | sì | `.csv` `.xlsx` | senza limite visto (campione dal 05/06/2024) | — |
| `account` | Lista Movimenti Conto | sì | sì | `.csv` `.xlsx` | `P2Y` (osservato) | `securities` |
| `portfolio` (facoltativo) | Andamento Portafoglio | no | no | `.xlsx` | — | — |

Il terzo ruolo non è nella lista di partenza: vale come **verifica** a fine periodo (§4.4). Si può rimandare.

### 4.1 Abbinamento (1 a 1, come Danske)

Chiave: **importo al centesimo + verso + finestra di date**. Per le cedole: importo netto uguale, conto 0-3 giorni dopo (finestra 5 per sicurezza). Per acquisti/sottoscrizioni: importo uguale, conto da -3 a +10 giorni dopo la data del titolo (nel campione -2…+8). Il rimborso fondo si abbina a un «GIROCONTO» positivo il giorno dopo. Il nome serve solo da controllo di coerenza (il conto abbrevia: ha l'ISIN, non il nome). Candidati indistinguibili → `ambiguous`, nessuna scelta a caso (regola di Danske).

### 4.2 Esito per riga

| Riga | Esito |
|---|---|
| Cedola del titoli **con** riga di conto | `pair`: una `INTEREST` (lorda) più la `TAX` di ritenuta, con l'asset, **senza** la gamba inventata |
| Acquisto/vendita/scadenza del titoli con la riga di conto | `pair`: `BUY`/`SELL` con quantità e **cassa vera** (niente `auto_cash`) |
| Riga di conto senza titoli (POS, utenze, prelievi, commissioni, bollo, emolumenti, interessi) | `standalone`: com'è oggi |
| Riga del titoli senza riga di conto, fuori dalla copertura del conto | `excluded: outside_cash_coverage` per le righe con cassa; **trasferimenti da altro dossier**: `standalone` (rettifiche senza cassa, già così) |
| Riga di conto «COMPRAVENDITA» senza riga del titoli | oggi blocca con `ca_account_trade_unresolved`: nel set diventa `excluded: no_counterpart` con avviso (il titoli del periodo manca) |

Le 36 righe di giugno 2024 sono prima di ogni punto di verità del conto: serve `pre_checkpoint_policy = "import"` (non `summarize`), perché sono posizioni, non denaro da riassumere.

### 4.3 Più file dello stesso ruolo

La regola M di Danske dice «ogni giorno appartiene al file più recente che lo copre». Qui **non basta**: A e B si sovrappongono, ma A è tagliato a metà giornata (3 righe in meno il 28/10/2024) e B è stato scaricato **dopo** A. Proposta: righe identiche contano una volta (multiinsieme), e per ogni giorno vince il file che ha **più righe** quel giorno (la banca può solo tagliare, non aggiungere), con `overlap_mismatch` quando due file si contraddicono. Il campione è l'unico caso reale che ho: due coppie di file.

### 4.4 Punti di verità

- **Apertura di cassa**: il «Saldo Iniziale» del primo file di conto la cui catena **chiude** (B: 2.425,89 alla vigilia del 01/08/2024 → checkpoint `opening`). Un file la cui catena non chiude (A: scarto 5.749,84) **non** dà un checkpoint: dà un avviso `balance_chain_broken` e il suo saldo diventa una verifica (come Danske).
- **Buco di luglio 2024**: la catena prova -559,10 senza righe. Il gap-fix lo propone come correzione di cassa (-559,10) se l'utente ha scaricato luglio; altrimenti è l'apertura di B che lo assorbe. Da decidere con il developer quale delle due (§8).
- **Verifiche a fine periodo**: «Saldo Finale» di ogni file la cui catena chiude (B 15.775,38; C 63.681,75), «Liquidità» del Deposito Titoli, e, se c'è il ruolo `portfolio`, le quantità per titolo del 05/08/2026 (qui `exact`, perché lo snapshot elenca la posizione intera).
- **Regola di sicurezza**: un'apertura sul conto è un checkpoint solo se nessun import futuro porterà le righe che riassume: vera per la vigilia dell'inizio del conto. Il fondo del periodo (31/07/2026-05/08/2026) **non** lo è (il prossimo import porta le righe) → verifica.
- **Senza XLSX non c'è nessun saldo**: un set di soli CSV si importa e si abbina comunque, ma senza checkpoint e senza verifiche (avviso `no_balance`). L'XLSX porta gli stessi dati più i saldi: la guida utente deve dire di scaricare e caricare l'XLSX.

## 5. I tre problemi del kickoff

**Dati già importati alla vecchia maniera.** Il tag storico è `credit_agricole` (il predefinito del set è lo stesso: `history_tag` = `credit_agricole`), quindi `history_start` (H0) esiste già per chi ha importato, e il set tratta come già rappresentato ciò che è prima. Quello che **non** si può fare (e per la regola «nessuna bonifica» non si fa): togliere le cedole, vendite e acquisti doppi già salvati. Il gap-fix compara la cassa e le posizioni alla data del punto di verità e propone la differenza: assorbe il saldo sbagliato ma lascia le righe doppie, e una correzione di cassa che nasconde un reddito doppio è peggio di niente. Proposta: **avvisare**, non correggere: nella card del set, «hai già N transazioni importate con questo plugin dal …: se le hai caricate separate (titoli e conto), cedole e acquisti possono essere doppi; eliminali dal Bulk prima di importare il set». Il numero lo dà `history_count` (c'è già). Non c'è nient'altro da costruire.

**Export di soli 2 anni.** Il conto parte dal 01/08/2024 al più; il Deposito Titoli arriva al 05/06/2024. Tra le due date ci sono i trasferimenti di giugno 2024 (senza cassa) e luglio 2024 (il buco di -559,10). Con il modello a set: `max_history = P2Y` per il conto + `must_cover = securities` fanno dire «il conto deve coprire dal 05/06/2024: manca», con il periodo da scaricare quando la banca lo permette; l'apertura di cassa (§4.4) copre il resto. Per i titoli più vecchi del conto, nessun problema: sono rettifiche.

**Saldo d'apertura nel CSV.** Il CSV non lo ha (§3.5). Vedi §4.4: con l'XLSX sì, senza no. È la ragione per cui il set accetta entrambe le estensioni e il testo utente raccomanda l'XLSX.

## 6. Cosa cambia per chi usa CA

Prima: due caricamenti separati, nessun avviso, reddito e acquisti doppi se carica tutti e due.
Dopo: stesso caricamento (titoli + conto nello stesso invio), una sola lista di transazioni, ogni cedola e ogni acquisto una sola volta (con quantità **e** cassa vere), un'apertura di cassa dai saldi dell'XLSX, e avvisi con codice (`gap`, `balance_chain_broken`, `overlap_mismatch`, `no_balance`, `outside_cash_coverage`) che spiegano ciò che manca.
Esempio: una cedola netta di 218,75 EUR (la prima riga del file titoli, 01/06/2026) oggi entra come `INTEREST` da 218,75 dal file titoli **e** di nuovo dal file conto (lorda, con la ritenuta come `TAX` quando la descrizione la riporta); nel set è una sola `INTEREST` lorda con la sua `TAX`.

## 7. Lavoro e stima (non in questa ondata)

| Pezzo | Giorni |
|---|---|
| Ruoli, `detect_role`, `describe_member`/`describe_set` (copertura, catena dei saldi, sovrapposizioni), `max_history`/`must_cover` | 2 |
| `combine` puro (colonne `lf_*`, un file con una riga per fatto), abbinamento e zone | 2-3 |
| `parse` del file combinato: una riga = una transazione, riuso del classificatore di causali di oggi, punti di verità | 1,5-2 |
| Campioni sintetici anonimi (a partire dai veri: importi e nomi cambiati), test del plugin e `test_sample_sets`, nessun dato personale nel repo | 1,5-2 |
| Doc utente (inglese), guida dei plugin, i18n delle chiavi `reportSet`, avviso sui dati già importati | 1 |
Totale 7-10 giorni; il rischio maggiore è il punto 4.3 (un solo caso reale di file sovrapposti) e le finestre del punto 4.1 (cinque acquisti nel campione).

## 8. Decisioni per il developer

1. **Si fa?** Raccomandazione: sì, in un'ondata a sé (non in questa): oggi un utente che carica entrambi i file ha reddito e acquisti doppi senza accorgersene.
2. **Dati già importati**: avviso nella card del set (proposta) o nulla? Nessuna bonifica in ogni caso.
3. **Buco di luglio 2024** (e simili): correzione di cassa proposta dal gap-fix, o solo avviso `gap` senza correzione? (Danske: correzione a checkpoint; ma qui nessuna riga lo prova.)
4. **Ruolo `portfolio`** («Andamento Portafoglio» come verifica delle posizioni): dentro il lotto o rimandato?
5. **Versione e tag**: il plugin passa a 2.0.0 (cambia l'output dello stesso file) e tiene il tag `credit_agricole`.

## 9. Cosa non ho verificato

- Non ho scritto né provato nessun `combine`: tutto sopra viene dalla lettura degli export veri e del plugin attuale.
- Le finestre di data (§4.1) vengono da 5 acquisti e 51 cedole di un solo utente; un altro dossier (altra filiale, altra lingua) potrebbe avere altri ritardi.
- Il limite di due anni e il taglio a metà giornata di A sono **ipotesi** sul comportamento della banca (l'unica prova è la catena dei saldi); non so se il taglio dipenda dal numero di righe.
- Ho tenuto fuori il formato non italiano (altra entità del gruppo), come fa il plugin oggi.
