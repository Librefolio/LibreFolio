# CHANGELOG di D-P4 — testo unico e righe da riscrivere (MF, L5, 26/10/2026)

Base letta: `train11b` `d2dc09a9a` (`CHANGELOG.md`, capitolo `## [Unreleased]`). Inserisce il coordinatore.

## 1. La voce unica di «⚠️ Breaking changes»

Sostituisce la voce attuale «**Portfolio history series as steps, not one point per day.**» (oggi alla riga 503 circa).
Unisce tre lavori:
- MF: report a gradini, `mwrr_line`, la qualità dei dati a intervalli, via `TRANSACTIONS_BEFORE_FLOOR`, nessun
  pavimento nel motore;
- J: lotti e `positions-series` a gradini, via gli `incomplete_*_dates`, nessun pavimento nei lotti;
- W: la scrittura delle transazioni senza pavimento.

La prima voce della sezione, «A transaction dated after tomorrow … is refused», resta com'è: il tetto in avanti non
cambia.

```markdown
- **Portfolio histories come as steps and start at your first transaction, whatever its year.**
  - `POST /api/v1/portfolio/report` (`history`, `allocation_history`, `broker_pnl_history`, `pnl_candles`),
    `POST /api/v1/portfolio/lots/analysis` (the daily lot histories: value, return, price, market price, broker and
    cumulative average cost, performance) and `POST /api/v1/portfolio/positions-series` now give one point per stretch
    of days during which nothing changed, from its `date` to its `through` (both included), and every response
    carries its `range`. A day's value is the point whose `date ≤ day ≤ through`; a day no point covers has no value
    (a broker not yet open, a day without a P&L candle, a price that cannot be converted).
  - The history's MWRR moves to `mwrr_line`: true values at the start and end of each step, and at each month end
    inside a step longer than 62 days. `history[].mwrr_annualized` and `history[].mwrr_cumulative` are gone.
  - The data-quality report gives date ranges instead of one date per day: `incomplete_*_ranges`, and
    `missing_fx_pairs[].ranges` for the days valued without a rate (`missing_fx_pairs[].dates` now holds only the
    movements' dates). The four `incomplete_*_dates` lists are removed.
  - There is no 1 January 1900 floor any more. A transaction dated before 1900 is accepted (the form, the bulk editor
    and the import ask for a confirmation first, since such a date is usually a typo), and the portfolio, the lots and
    the positions start from it. The `TRANSACTIONS_BEFORE_FLOOR` warning is removed. A history that starts in the year
    1 costs as much as its changes, not as its 740 000 days. For a portfolio that already held rows dated before 1900,
    its «All» figures (MWRR, TWRR, ROI) now count from them.
```

## 2. Le righe del capitolo che contraddicono la voce

Sono state scritte quando il pavimento c'era. Proposta riga per riga (numeri di `d2dc09a9a`):

| Riga | Sezione | Testo di oggi (inizio) | Proposta |
|---|---|---|---|
| 132 | 🔄 Changed | «The Dashboard warns when transactions are dated before 1900: they still count, but the history starts on 1 January 1900.» | **togliere**: l'avviso non c'è più (lo dice la voce unica) |
| 353 | 🐛 Fixed | «Numbers with an absurd exponent and transaction dates outside 1 January 1900 – tomorrow (the server's date) are refused…» | «Numbers with an absurd exponent and transaction dates after tomorrow (the server's date) are refused with a clear message, instead of slowing the server; the merged fields of a pair promotion are checked like a new transaction's.» |
| 367 | 🐛 Fixed | «A transaction dated far in the past (e.g. year 1) no longer makes every portfolio report recompute hundreds of thousands of days, nor fail: histories start no earlier than 1 January 1900.» | «A transaction dated far in the past (e.g. year 1) no longer makes every portfolio report recompute hundreds of thousands of days, nor fail: the history is built from the days something changes.» |
| 371 | 🐛 Fixed | «The 1D … 5Y change endpoints of the Assets and FX lists now refuse an oversized request or a date before 1900 instead of overloading the server or failing.» | «The 1D … 5Y change endpoints of the Assets and FX lists now refuse an oversized request instead of overloading the server, and a period that would start before the year 1 has no change instead of failing.» (L4 di X; verificato in `returns.day_before()` / `fixed_period_dates()`: un riferimento prima dello 0001-01-01 dà null) |

Restano vere e non si toccano:
- 185–186: «on a history that starts in 1900» è solo l'esempio della misura;
- 349: i calendari dei titoli tra 1900 e 2200 (`SCHEDULE_MIN_DATE`, R5);
- 350: «starts no earlier than your first transaction»;
- 473: il drawdown a storia intera di un asset parte dal 1900 (Z-30, ora `FULL_HISTORY_LOAD_START`, R2).

## 3. Una riga da aggiungere in «✨ Added» (o «🔄 Changed»)

Il cambio vecchio entra nella qualità dei dati (MF, secondo checkpoint P4b). Non c'è ancora una voce:

```markdown
- The portfolio's data-quality report lists the exchange rates it values your holdings with that are more than
  7 days old (`stale_fx_pairs`: the pair, the date of the last stored rate and its age in days), like the stale prices.
  There is no banner for it yet.
```

Se il developer decide il banner del cambio vecchio, la frase finale cambia.
