# 04 — BRIM & Import

Task sui plugin di import e sul wizard. Approvati dall'utente il 07/09/2026.
Skill di riferimento per chi esegue: `brim-plugin`.

---

## 🔍 eToro — "Withdraw Fee" / "Conversion Fee" scartate invece di importate come FEE

**Complessità**: S–M · **Tipo**: bug sospetto · **Origine**: verifica 18/07/2026 (bug BRIM FEE/TAX)

### Contesto
`backend/app/services/brim_providers/broker_etoro.py` — la docstring (riga ~20) dice
*"Withdraw Fee / Conversion Fee → FEE"* ma il codice (righe 72-78, `SKIP_TYPES`) le mette tra
i tipi **scartati a monte**: queste righe non diventano mai una transazione `FEE`, vengono
perse in import. Bug diverso dal FEE/TAX-non-collegato: qui la transazione non nasce proprio.
Ha senso anche estendere la ricerca a gli altri plugin per vedere se bug simili sono presenti.

### Da valutare (decisione prima del codice)
- Se vogliamo importarle (coerente con la docstring): spostarle da `SKIP_TYPES` a
  `TYPE_MAPPINGS` con `TransactionType.FEE`, **prima** verificando il formato reale di queste
  righe in un export eToro vero (il sample bundled `etoro-export.csv` non le contiene — serve
  un export reale o la conferma dell'utente sul formato).
- Se lo scarto è intenzionale (es. per evitare doppio conteggio): correggere la docstring per
  riflettere il comportamento reale.

---

## 💸 BRIM: FEE/TAX non collegati all'asset — verifica e consolidamento

**Complessità**: M · **Origine**: TODO_FUTURI (Fase 1 completata il 18/07)

### Stato (dalla nota)
- **Fase 1 (fatta)**: Directa e Schwab corrette (bug reale confermato sui sample bundled);
  Finpension/Revolut fix difensivo (FEE strutturalmente di conto); eToro spostata nella voce
  sopra; Freetrade/Trading212/generic_csv non affette.
- **Pattern di riferimento validi**: `broker_ibkr.py:229-247` (FEE riusa l'`asset_id` della
  riga madre), `broker_coinbase.py:283-303`, `broker_degiro.py:87-103` (mappa tipo→
  requires_asset caso per caso), `broker_generic_csv.py` (collega se il campo asset è pieno).

### Cosa resta (Fase 2, da pianificare)
- **Motore FIFO/lotti** ignora sempre FEE/TAX anche quando hanno `asset_id`: non entrano nel
  cost basis/WAC del lotto. Una ritenuta su cedola o una commissione d'acquisto oggi non
  altera mai il prezzo medio di carico.
- Il **Portfolio Engine** invece già distingue (period P&L per posizione: FEE/TAX con
  asset_id attribuiti, senza → bucket non allocato) — metà del lavoro esiste.
- Nota tecnica (18/07): esistono 3 motori separati (pool WAC, lotti event-sourced, allocazione
  pro-rata di `asset_income`) — la scelta del meccanismo (mutare il costo base del lotto vs
  metrica ausiliaria pro-rata) va decisa nel piano dedicato.
- File: `backend/app/services/fifo_lot_engine.py`, `backend/app/utils/financial/wac_utils.py`,
  `backend/app/services/portfolio_service.py` (`_HOLDING_TYPES`, `compute_wac_iterative`).
- Cross-link: tocca la stessa area del regime fiscale (in TODO_FUTURI, futuro) — coordinare
  se pianificati insieme.

---

## 🔗 Link transazioni nella Asset Delete Modal

**Complessità**: S · **Origine**: 26/03/2026, scope ridotto 17/07

### Richiesta
Quando un asset non si può eliminare perché ha transazioni (`error_code: HAS_TRANSACTIONS`),
il messaggio è generico. Ora che la pagina transazioni esiste:
1. Delete modal: conteggio + link diretto alla pagina transazioni filtrata
   (es. "This asset has 3 transactions: [View → /transactions?asset_id=123]").
2. Pagina dettaglio asset: sezione con link alle transazioni collegate.
3. Backend: `transaction_count: int` in `FAAssetDeleteResult` quando `error_code == "HAS_TRANSACTIONS"`.

### Nota
Il filtro `?asset_id=` nella pagina transazioni **esiste già** (`+page.svelte`, verificato
17/07) — scope residuo ridotto a campo backend + link nel frontend.
