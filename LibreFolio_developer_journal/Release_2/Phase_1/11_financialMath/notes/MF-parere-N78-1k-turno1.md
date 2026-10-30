# MF · parere sull'analisi di W per Q-N78-1k (turno 1, 22/10/2026)

Sola lettura, worktree MF a `c1b4ba49c` (= `dev_release2` `c042f2481`). Fonte: `W-analisi-turno1.md` §1, contro il codice di
`backend/app/services/financial_math/`.

**In breve**: l'analisi tiene in larga parte. I numeri della tabella sono giusti, ma **solo nell'esempio di W** (un lotto solo,
le due gambe nello stesso giorno, la gamba di B con un costo di 50 = PMC di A). Fuori da queste tre condizioni **P non dà
più 0 sul totale**. Ci sono tre casi che W non vede e due correzioni sulla «casa unica».

---

## 1. La matematica ha una sola casa? Quasi: due correzioni

**1a. Il modulo nuovo deve contenere solo il predicato, non un «calcolatore del valore d'uscita».**
Il valore d'uscita al PMC esiste già, due volte e per scelta:
- Dashboard: il passo del costo medio, `sell_cb_target` (`portfolio/daily_state.py:414`, dal passo di `average_cost.py`);
- lotti: `_own_fifo_cost` con `hands_over_at_own_cost` (`fifo/engine.py:409`, `:1318`).
Un terzo calcolatore in `linked_adjustments.py` sarebbe una copia. → Il modulo dà solo *quali righe* sono l'uscita di una
coppia: `is_internal_adjustment_exit(tx, partner)` e una funzione sull'insieme (vedi 1c). Il valore lo leggono dai motori.

**1b. Performance dei lotti (punto 3 di W): non scrivere un flusso nuovo «pari al costo» in `lots/histories.py:146`.**
Sarebbe un secondo calcolo del costo FIFO. Il numero c'è già: è il `proceeds` della chiusura `ADJUSTMENT_OUT` del motore.
→ Allargare il ciclo delle chiusure `SELL` (`lots/histories.py:158-169`, `convert_closure(...).proceeds`) alle chiusure
`ADJUSTMENT_OUT` con `hands_over_at_own_cost` (o riusare `_boundary_leg_cost`, che fa già «il costo dei pezzi che chiude»).

**1c. Il segno della coppia nel FIFO va messo in un punto solo, non nel motore.**
W propone `FifoLotEngine.__init__` (punto 2) **e** `partner_ids_to_load` (punto 4). Sono due rilevamenti: il motore vede solo
il partner dentro l'ambito, il bordo solo quello fuori. Con P la regola **non dipende dall'ambito** (A esce al PMC con o
senza B), quindi basta un rilevamento solo, con i partner di entrambe le provenienze.
→ `linked_adjustments.mark_internal_adjustment_exits(transactions, partners)` restituisce le copie con
`hands_over_at_own_cost=True`; la chiama `lots_analysis_service._read_at_scope_boundary` (così la ricevono tutte e due le
corse, `:232` e `:284`). Il motore resta com'è.
→ Non allargare `partner_ids_to_load` (`lots/scope_boundary.py:71`, oggi solo TRANSFER, usato anche da J-47
`_load_late_transfer_legs`): una funzione propria nel modulo nuovo, così J-10 e J-47 non cambiano contratto.
- Dashboard: il classificatore carica già **ogni** partner, di qualsiasi tipo (`portfolio/classifier.py:63`,
  `get_needed_paired_ids`), quindi `ctxn.paired_tx` c'è sia dentro sia fuori dall'ambito: nessun caricamento nuovo.
- Yield on cost (punto 5): legge solo i lotti aperti (`yield_on_cost.py:716`, `replay.lots`): il prezzo d'uscita non cambia
  nulla. → Nessun codice, solo un test di guardia.
- Il predicato deve escludere le righe legate a uno SPLIT (`asset_event_id`, `splits.py`), come fa `_is_capital_adjustment`.

**Copie fuori casa**: nessuna trovata (grep di `ADJUSTMENT` + `related_transaction_id` su `backend/app`: le letture stanno
tutte in `financial_math/`). Lo ricontrollo sul diff di W.

---

## 2. I numeri della tabella P/M sono giusti? Sì, con le ipotesi dell'esempio

Ricalcolati sul codice (10 azioni a 50, valgono 80 già il giorno prima, gamba di B con costo 50, stesso giorno):

| | Oggi | P | M |
|---|---|---|---|
| Tutti: capitale / realizzato / P&L / TWRR | 1000 / −500 / −200 / −62,5 % | 500 / 0 / 300 / 0 % | 500 / 0 / 300 / 0 % |
| Solo A: capitale / P&L / TWRR | 500 / −500 / −100 % | 0 / 0 / −37,5 % | −300 / 300 / 0 % |
| Solo B: capitale / P&L | 500 / 300 | 500 / 300 | 800 / 0 |

Tutti giusti. Il TWRR usa `(V_fine − flusso − V_inizio) / V_inizio` (`returns.py:546`), con i flussi dal delta del capitale
(`derived_views.py:211-219`): −62,5 % = (800 − 500 − 800)/800; −37,5 % = (0 + 500 − 800)/800. Nota: la tabella vale se il
prezzo è 80 già il giorno prima; altrimenti il TWRR del giorno mescola il movimento del prezzo.

---

## 3. Casi che W non vede (tutti contro P; M li regge per costruzione)

**3a. La gamba di B senza costo, o con un costo diverso dal PMC di A** — il caso più importante.
Con P il totale è neutro solo se `costo gamba B = PMC di A`. Nessun codice lo garantisce: l'Auto cost di una gamba in entrata
fa la media del **broker del partner** solo per i TRANSFER (`services/transactions/auto_cost.py:256-268`, riga 265); per una rettifica
collegata fa la media del **proprio** broker B (spesso vuoto → `autoCostEmptyPool`, la riga è rifiutata o salvata senza costo).
Esempio, tutti i broker, con P:
- gamba B **senza costo**: capitale 500 − 500 + 0 = **0**, NAV 800, P&L **800** (+500 inventati). Oggi: P&L 300.
- gamba B **a 60**: capitale 500 − 500 + 600 = 600, P&L **200** (−100 inventati).
Con M il capitale totale non si muove (coppia interna): P&L 300 in tutti e due i casi.

**3b. Più lotti a prezzi diversi, spostamento parziale (vista lotti).**
A ha 5 a 40 e 5 a 60 (PMC 50), sposta 5; la gamba B costa 50.
- Dashboard: A cede 250 al PMC, B porta 250 → neutro.
- Lotti FIFO: A chiude il lotto a 40 al suo costo (200, realizzato 0), B apre a 250 → il costo dei lotti aperti passa da 500 a
  550, il non realizzato cala di 50 dal nulla, TWRR dei lotti del giorno −6,25 % (flusso +50 su 800).
Con P le due viste non danno lo stesso «neutro». Con M (i frammenti viaggiano col loro costo) sì.

**3c. Le due gambe in giorni diversi.**
Il classificatore costruisce un intervallo «in viaggio» anche per una coppia di rettifiche, ma la tratta come **contanti** con
importo 0 (`portfolio/classifier.py:223-233`: solo i TRANSFER sono «asset»). Uscita il 1°, entrata il 5, con P, tutti i broker:
dal 1° al 4 il NAV perde 800 e il capitale 500 → P&L 300 → 0 per quattro giorni, TWRR del 1° −37,5 %, e il 5° il giorno ha base
0 (saltato). Il totale non è neutro durante il viaggio. Con M serve l'intervallo «asset» (è uno degli otto siti di W).

**3d. (minore) La lista dei realizzati.** Con P il ramo `daily_state.py:421` continuerebbe ad aggiungere una «vendita» con
ricavo = costo (guadagno 0) alla lista dei realizzati della Dashboard. Un TRANSFER non ci compare. Va deciso: la togliamo
(consiglio) o resta una riga a 0.

---

## 4. Conseguenza per la scelta P/M (da girare al developer)

P è più piccola, ma **la sua promessa («entrambi i broker → totale 0») dipende da un dato che nessuno controlla**, il costo
della gamba B, e non regge 3b e 3c. M è neutra sempre, perché non usa il costo per il capitale.

Se il developer resta su P, servono in aggiunta (domande):
- **Q-N78-1k-3 · il costo della gamba B.** (a) l'Auto cost di una rettifica collegata in entrata fa la media del partner, come
  per il TRANSFER (`auto_cost.py`, fuori da `financial_math/`, piccolo) **e** un avviso di qualità dei dati quando il costo
  salvato è diverso da quello ceduto (dati vecchi); oppure (b) si accetta lo scarto. *Consiglio MF: (a).*
- **Q-N78-1k-4 · gambe in giorni diversi.** (a) una coppia di rettifiche in giorni diversi non è «coppia» (resta N78-1); (b) si
  accetta il buco; (c) l'intervallo diventa «asset» come per i TRANSFER (si avvicina a M). *Consiglio MF: (a), con un test.*
- **3b** resta una differenza nota fra Dashboard (PMC) e lotti (FIFO): da scrivere nella pagina di teoria.

*Consiglio MF*: **M**, oppure — più semplice di tutto — la risposta (b) di W a Q-N78-1k-2: l'API rifiuta le nuove coppie di
rettifiche e propone di promuoverle a TRANSFER (che esiste già: `promote_from`), e i dati vecchi si leggono con P. Decide il
developer.

---

## 5. Test che chiedo in più (oltre a quelli di W)

1. Coppia con la gamba B **senza costo** (3a), tre viste.
2. Coppia con la gamba B a un costo **diverso** dal PMC (3a).
3. Due lotti a prezzi diversi, spostamento parziale, vista lotti (3b).
4. Gambe in **giorni diversi** (3c).
5. Riga legata a uno **SPLIT** con `related_transaction_id`: non è una coppia.
6. Yield on cost invariato con la coppia (guardia, punto 5 di W).
7. Le tre guardie di W (non collegate; stesso broker; quantità non opposte) e la coppia promossa a TRANSFER.
