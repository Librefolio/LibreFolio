# N78-1 · A che valore esce un'unità in una rettifica in uscita

Workstream W, 21-22/10/2026. Solo analisi: nessun codice cambiato. Base `2879ae3e4` (`dev_release2`, treno 7).
Fatti di partenza: la preparazione di MF (piano 11, «N78-1 con W — preparazione»); qui sono riletti sul codice e completati
con il lato utente (Form, Bulk, import).

---

## 1. La domanda, e che cosa fa oggi LibreFolio

**La domanda.** Quando delle unità escono con una **Rettifica** (ADJUSTMENT con quantità negativa: un regalo, un'uscita verso
un conto che LibreFolio non segue, una correzione), **a che valore escono**?

Il PMC (prezzo medio di carico) **non cambia già oggi**, in tutti i casi: esce una quantità, il PMC di ciò che resta è lo stesso.
È quello che chiedevi («modifica le quantità, non il PMC»). La scelta vera è il **valore d'uscita**, perché da lui dipendono il
realizzato, il capitale e il rendimento del giorno.

**Oggi**, il valore d'uscita è il campo `cost_basis_override` della riga (per unità), e ogni motore lo legge così:

| Dove | Con un valore per unità V | Senza valore |
|---|---|---|
| **PMC** (`financial_math/average_cost.py:302-303`) | una riduzione: il PMC resta | uguale |
| **Prezzi** (`price_marks`) | una rettifica non è mai un prezzo | uguale |
| **Dashboard** (`portfolio/daily_state.py:418-428`, J-24) | il capitale scende di q·V (al cambio del giorno); realizzato = q·V − q·PMC | nessun effetto sul capitale né sul realizzato: le unità «spariscono» |
| **TWRR / MWRR della Dashboard** (`portfolio/derived_views.py:192-220`) | il flusso del giorno è la variazione del capitale: q·V in uscita | nessun flusso |
| **Lotti FIFO** (`fifo/engine.py:241-245`, `:397-410`) | consuma i lotti come una vendita, al prezzo V: realizzato del lotto = V − costo del lotto | chiude a **0**: realizzato del lotto = −costo |
| **Performance dei lotti** (`lots/histories.py:146-152`) | un flusso in uscita di q·V | nessun flusso |

Due casi in cui il valore lo scrive LibreFolio da solo:
- **Decisione 47** (`services/transactions/auto_cost.py:248`, `_handover_cost`): la gamba che cede di un TRANSFER rimasto senza
  coppia diventa un ADJUSTMENT in uscita **al PMC** del suo broker (Auto). Il valore è salvato nel database.
- **Gambe al bordo di J-10** (`financial_math/lots/scope_boundary.py:95-104`): nell'analisi dei lotti di un sottoinsieme di
  broker, una gamba di TRANSFER che esce verso un broker fuori dall'ambito è letta come ADJUSTMENT in uscita **al valore di
  mercato del giorno**; senza un prezzo quel giorno, al costo FIFO di ogni pezzo (`hands_over_at_own_cost`). Non è salvato: è
  una lettura.

---

## 2. L'esempio, calcolato per (a), (b), (c)

Compri **10 azioni a 50** (PMC 50, capitale versato 500). Oggi valgono **80** (valore 800, guadagno non realizzato 300). Ne
**regali 2** a tuo fratello.

- **(a) al costo**: escono a 50 (il PMC, come la decisione 47).
- **(b) al valore di mercato**: escono a 80 (come le gambe al bordo di J-10).
- **(c) correzione di quantità**: escono senza valore (oggi, una rettifica senza costo).

Dopo il regalo restano 8 azioni a 80 = **640** in tutti e tre i casi.

| | (a) al costo | (b) al mercato | (c) correzione |
|---|---|---|---|
| Quantità | 8 | 8 | 8 |
| PMC | 50 | 50 | 50 |
| Valore che esce (q × V) | 100 | 160 | 0 |
| **Capitale** (versato netto) | 500 − 100 = **400** | 500 − 160 = **340** | **500** |
| **Realizzato** (Dashboard) | 100 − 2·50 = **0** | 160 − 100 = **+60** | **0** |
| Non realizzato (8 × (80 − 50)) | 240 | 240 | 240 |
| **P&L totale** (valore − capitale) | 640 − 400 = **240** | 640 − 340 = **300** | 640 − 500 = **140** |
| Variazione del P&L totale nel giorno | **−60** | **0** | **−160** |
| **TWRR del giorno** | (640 + 100) / 800 − 1 = **−7,5 %** | (640 + 160) / 800 − 1 = **0 %** | 640 / 800 − 1 = **−20 %** |
| Lotti: realizzato del lotto | 2 × (50 − 50) = **0** | 2 × (80 − 50) = **+60** | 2 × (0 − 50) = **−100** |
| Lotti: P&L totale (realizzato + aperto 240) | 240 | 300 | 140 |
| Dashboard e lotti dicono lo stesso? | sì | sì | il totale sì (140); ma la Dashboard mette 0 nel realizzato e i −100 finiscono in «Altro» |

**Come leggerlo, in parole.**
- (a) Il regalo **cancella il guadagno** di quelle 2 azioni (60) senza dirlo da nessuna parte, e il **TWRR del giorno segna
  −7,5 %** anche se il prezzo non è cambiato: un rendimento falso. Il motivo: il valore del portafoglio scende di 160, ma il
  flusso conta solo 100.
- (b) Il P&L totale resta **300**, il TWRR resta **0**: il regalo è un prelievo in natura al suo valore di oggi, e i 60 di
  guadagno si **realizzano** (come in una vendita). È anche il trattamento fiscale più vicino a una cessione.
- (c) Le unità **spariscono come una perdita**: il P&L scende di 160 (tutto il loro valore di mercato) e il **TWRR segna −20 %**.
  È giusto solo se quelle unità **non erano tue** (un errore di quantità) o se sono **perse davvero**.

**Come ho verificato i numeri.**
- **Lotti e TWRR: con il codice.** Uno script su dati sintetici (nessun database) ha fatto girare il vero motore FIFO
  (`run_fifo_lot_engine`) e il vero `calculate_twrr`: chiusure a 50 / 80 / 0 con realizzato 0 / +60 / −100; TWRR del giorno
  −0,075 / 0 / −0,20. Lo script è nello scratchpad della sessione, non nel repo.
- **Dashboard: a mano, seguendo `daily_state.py:418-428`.** Il caso con un valore dichiarato è già fissato da un test del
  backend (`test_scripts/test_services/test_financial/test_adjustment_out_with_cost_numbers.py`, J-24 / CP-16: capitale −q·V,
  realizzato q·V − costo). La ripartizione di (c) fra realizzato e «Altro» è letta nel codice, non fatta girare.

---

## 3. Che cosa vede l'utente oggi, e in ciascun caso

**Oggi** (letto nel codice, non visto a schermo):
- **Form**: per una Rettifica mostra **sempre** la sezione del costo, anche con quantità negativa
  (`TransactionFormModal.svelte:749`, `TxFormSingleSection.svelte:319`), con Auto e Manuale. Ma al salvataggio il valore
  **non parte**: `buildCreatePayload` e `buildUpdateDiff` lo tolgono quando la quantità è ≤ 0 (`txPayloadHelpers.ts:274-277`,
  `:301-302`). **Il valore digitato si perde in silenzio** (è il difetto già descritto in N78-bis, piano 04, sezione A).
  L'avviso «costo vuoto» appare solo con quantità positiva (`TxFormSingleSection.svelte:341`).
- **Bulk**: toglie modalità e costo a ogni riga con quantità ≤ 0 (`TransactionBulkModal.svelte:811-815`, `:835-838`).
- **Quindi dall'interfaccia oggi si arriva solo a (c).** (a) lo scrive solo la decisione 47; un valore qualsiasi passa solo
  dall'API.
- **Import**: nessun plugin mette un valore su una rettifica in uscita: tutte sono (c). Quali sono: prelievi di cripto
  (Bitvavo `:253`, Delta `:342`, CoinTracking `:355`), commissioni pagate in cripto (Bitvavo `:314`, Delta `:220`, CoinTracking
  `:195`), la gamba di vendita di uno scambio cripto-cripto (Delta `:300`), la vecchia gamba di una scissione (Danske Bank
  `:1457`), azioni societarie di Schwab (`:348`), le righe «adjustment» del CSV generico (`:640`). Un'incoerenza: il CSV
  generico chiede un costo bloccante su **ogni** rettifica (`plugin.py:455-470`), anche in uscita, e il Bulk non lascia
  riempirlo (`bulkTodos.ts:65-70`).
- **Messaggi**: `costBasisNotAllowed` e `costBasisModeIncompatible` dicono che solo le unità **in entrata** portano un costo:
  oggi non nominano l'uscita.

**Nei tre casi** (proposta, da decidere):

| | (a) al costo | (b) al mercato | (c) correzione |
|---|---|---|---|
| Campo nel Form | «Valore d'uscita», Auto = PMC | «Valore d'uscita», Auto = prezzo del giorno | nessun campo |
| Testo | «Le unità escono al loro costo: nessun guadagno realizzato» | «Le unità escono al loro valore di oggi: il guadagno si realizza, come in una vendita» | «Le unità spariscono: il loro valore conta come perdita. Usalo per correggere un errore di quantità» |
| Avviso | il rendimento del giorno cambia anche a prezzo fermo | senza un prezzo quel giorno, escono al costo (come J-10 e i giorni a costo di J-17) | l'unico caso che abbassa il P&L |

---

## 4. Coerenza con la decisione 47 e con le gambe al bordo di J-10

Oggi le due regole **si contraddicono** sullo stesso fatto: unità che lasciano ciò che LibreFolio segue.
- **Decisione 47** (gamba sola di un TRANSFER, salvata): **(a), al PMC**. Il guadagno di quelle unità sparisce senza essere
  realizzato e il TWRR del giorno segna un rendimento falso (−7,5 % nell'esempio).
- **J-10** (gamba al bordo di un ambito, letta dai lotti): **(b), al mercato del giorno**, e al costo senza un prezzo. Il guadagno
  si realizza, il TWRR resta neutro.

Esempio: sposti le 2 azioni a un broker che non hai in LibreFolio. Se la coppia esiste ma guardi un solo broker, i lotti di quel
broker realizzano +60 (J-10). Se cancelli il broker di destinazione e la gamba resta sola, la decisione 47 la fa uscire a 50: il
realizzato diventa 0 e la Dashboard segna −7,5 % quel giorno.

Con **(b)** le due regole diventano la stessa; con **(a)** bisognerebbe cambiare J-10; con **(c)** entrambe.

---

## 5. Pro, contro e costo

| | (a) al costo | (b) al mercato | (c) correzione |
|---|---|---|---|
| **Pro** | semplice; il valore c'è sempre (il PMC); è la decisione 47 di oggi | P&L continuo e TWRR neutro; realizza il guadagno come una vendita, come chiedevi; coerente con J-10; Dashboard e lotti dicono lo stesso | è il comportamento di oggi di ogni import; giusto per un errore di quantità |
| **Contro** | **TWRR del giorno falso** a prezzo fermo; il guadagno sparisce senza essere realizzato; contro J-10 | serve un prezzo quel giorno (senza: al costo); il valore è fissato al salvataggio (un prezzo corretto dopo non lo cambia, come oggi l'Auto in entrata); il campo si chiama ancora `cost_basis_override` | una perdita pari a tutto il valore di mercato; TWRR −20 % nell'esempio; Dashboard e lotti non concordano sul realizzato |
| **Backend** | regola 12 con Auto in uscita (= `_handover_cost`, già esiste); la risposta pubblicata di N78-bis. ~½ giorno | come (a), più un «Auto al mercato»: il prezzo del giorno per unità con la funzione che J-10 usa già (`compute_holding_value` su `price_series.resolve`, in `financial_math`), con lo stesso ripiego al costo. I motori non cambiano (J-24 e CP-16 leggono già un valore dichiarato). ~1 giorno | nulla nei motori; a parte allineare il realizzato della Dashboard ai lotti (Q-N78-1e) |
| **Frontend** | N78-bis (i 9 punti che oggi buttano il valore) + testi. ~1 giorno | uguale ad (a) | solo i testi, ma N78-bis serve comunque: oggi il Form mostra un campo che non salva |
| **Dati già salvati** | nessuna migrazione | facoltativa: le righe della decisione 47 (oggi al PMC) potrebbero passare al mercato con un passo d'avvio come `lone-transfer-legs` (Q-N78-1c); le rettifiche senza valore restano (c) | nessuna |
| **Doc** | pagina utente delle transazioni, `brokers_transactions.md` | uguale | uguale |

In tutti e tre i casi **N78-bis** (il backend pubblica la regola, il frontend la legge) è il primo passo: senza, il Form continua a
perdere il valore in silenzio.

---

## 6. Raccomandazione di W

**(b) come valore d'uscita di default, (c) come scelta esplicita, (a) solo come ripiego senza prezzo.**
1. Una Rettifica in uscita ha un **«Valore d'uscita»** con due modi: **Auto** = prezzo di mercato del giorno (calcolato dal
   backend, al costo se quel giorno non c'è un prezzo) e **Manuale**. È il default nel Form e nel Bulk.
2. **Senza valore** resta possibile, con un nome chiaro: «correzione di quantità», e il testo che dice che conta come perdita.
3. La **decisione 47** passa al mercato del giorno, come J-10 (la migrazione delle righe già salvate è una tua scelta,
   Q-N78-1c).
4. **Gli import non cambiano** per ora (restano (c)); quali passare a (b) lo decidi plugin per plugin (Q-N78-1d).

Perché: è l'unica delle tre che non inventa un rendimento (TWRR 0 a prezzo fermo), tiene il P&L continuo, realizza il guadagno come
una vendita («se esce, è come fosse una vendita») e mette d'accordo la decisione 47 con J-10. I motori la sanno già leggere: il
lavoro è dare il valore giusto e farlo arrivare dal Form.

**La lettura di MF.** MF ha preparato i fatti (piano 11, «N78-1 con W — preparazione») e ha già segnato il TWRR falso di (a) e la
neutralità di (b); non ha scritto una raccomandazione. Su ciò che ha scritto non ci sono differenze con questa analisi; aggiungo
solo il lato utente (§ 3), la contraddizione 47 / J-10 con l'esempio (§ 4) e il disaccordo sul realizzato di (c) fra Dashboard e
lotti.

---

## 7. Domande al developer

- **Q-N78-1a · Il default.** Il valore d'uscita di una Rettifica nuova nel Form: (b) mercato del giorno *(consiglio)*, (a) PMC, o
  (c) nessun valore?
- **Q-N78-1b · La correzione resta?** Lasciare la scelta «nessun valore» (c), con il testo «conta come perdita»? *(consiglio: sì,
  serve per gli errori di quantità.)*
- **Q-N78-1c · La decisione 47.** La gamba sola di un TRANSFER esce al mercato del giorno come J-10 *(consiglio)*, o resta al PMC?
  E le righe già salvate: si ricalcolano con un passo d'avvio, o restano come sono?
- **Q-N78-1d · Gli import.** I prelievi di cripto verso un proprio wallet sono uscite di capitale: (b)? Le commissioni pagate in
  cripto sono un costo vero: (c) va bene (abbassano il rendimento)? La vecchia gamba di una scissione (Danske) e le azioni
  societarie di Schwab: restano come oggi? *(consiglio: tutto come oggi in 1.3, da rivedere plugin per plugin dopo.)*
- **Q-N78-1e · Il realizzato di (c).** Oggi in (c) i lotti realizzano −100 e la Dashboard 0 (i −100 vanno in «Altro»). Allineare
  la Dashboard ai lotti, o lasciarlo? *(consiglio: allineare, in un lotto di MF.)*
- **Q-N78-1f · Senza prezzo quel giorno.** In (b), senza prezzo: al PMC (come J-10 e i giorni a costo di J-17) *(consiglio)*, o
  rifiutare il salvataggio finché il prezzo non c'è?
- **Q-N78-1g · Il nome del campo.** «Valore d'uscita» nel Form per l'uscita e «Costo per unità» per l'entrata? Il campo del
  database resta `cost_basis_override` (nessuna migrazione dello schema).
- **Q-N78-1h · Quando.** In 1.3 (N78-bis + Auto al mercato: circa 2 giorni fra backend e frontend, più la doc) o dopo?

---

## 8. Decisioni del developer (21/10 sera, riportate dal coordinatore)

Diverse dalla raccomandazione di W: vale **(c)**, con il realizzato allineato ai lotti.
1. **Una rettifica in uscita non ha valore**: abbassa solo la quantità. Nessun prezzo di carico in uscita, **anche per il TWRR**
   (sapendo l'effetto: nell'esempio P&L −160 e TWRR −20 % quel giorno).
2. **Decisione 47 cambiata**: la gamba sola di un TRANSFER che cede esce **senza valore** (non più al PMC).
3. **Realizzato allineato ai lotti**: la Dashboard mostra realizzato = 0 − costo (−100 nell'esempio) invece di «Altro». Il calcolo
   resta in `financial_math`.
4. **Form e Bulk**: il campo del costo solo con quantità positiva (fine del difetto N78-bis).
5. **Righe già salvate**: la 1.2.1 non aveva la decisione 47; il passo d'avvio `lone-transfer-legs` d'ora in poi converte senza
   valore, e toglie il valore alle righe che aveva convertito al PMC se si riconoscono.
6. **Quando**: in 1.3.
7. **Backlog dopo la 1.3**: la metà che entra di un trasferimento può servire a stimare il prezzo dell'asset quel giorno.

L'esempio con le decisioni: capitale 500, realizzato **−100** (Dashboard e lotti), non realizzato 240, «Altro» 0, P&L totale
**140**, TWRR del giorno **−20 %**.

**Due fatti trovati preparando la cura** (dettagli nel piano 04, «N78-1 · cura»):
- **Le righe convertite al PMC non si riconoscono una per una**: la conversione (`make_standalone`) non lascia un segno; resta un
  ADJUSTMENT in uscita con un valore, come una riga salvata con un valore dall'API. Nella **1.2.1** un valore su una rettifica in
  uscita **era già salvabile** (la regola 12 rifiutava solo la modalità, non il valore), quindi anche installazioni rilasciate
  possono averne. La cura fa sì che **i motori ignorino sempre** il valore di un'uscita: i numeri sono giusti comunque. Togliere il
  valore salvato a tutte le rettifiche in uscita è una domanda (Q-N78-1i).
- **Le gambe al bordo di J-10** (lettura dei lotti di un TRANSFER ancora in coppia, guardando un solo broker) restano al mercato del
  giorno: la decisione non le nomina. Domanda Q-N78-1j.
