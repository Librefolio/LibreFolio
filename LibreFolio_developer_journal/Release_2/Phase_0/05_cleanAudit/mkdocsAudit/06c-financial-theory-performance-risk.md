# 06C — Teoria finanziaria: Performance e Rischio

> **Release 2 · Phase 0 · 05_cleanAudit · mkdocsAudit**
>
> Sola verifica. Nessuna correzione applicata. Baseline: worktree dirty a
> `09cbb7e28f4e4e4bba9f9d40748b98e1876f5103`, manifest in
> [00_BASELINE](00_BASELINE.md) (captured_at `2026-08-05T10:54:55+02:00`).
> Ambito: **solo** `financial-theory/technical-analysis/performance-metrics/**/*.en.md` e
> `financial-theory/technical-analysis/risk-metrics/**/*.en.md`. Nessun'altra pagina,
> traduzione, developer guide, o area applicativa e' stata toccata. Le pagine relative
> a funzionalita' beta sono mantenute nella copertura, ma non generano reperti sulla
> documentazione pubblica.

## Ambito assegnato

20 pagine EN pubblicate (il compito indicava "circa 22"; il conteggio esatto delle
pagine esistenti sotto i due percorsi assegnati e' 20 — nessuna pagina mancante o
fuori posto rispetto all'indice `00_INDEX.md`).

| # | Percorso | Disposizione |
|---|---|---|
| 1 | `performance-metrics/index.en.md` | Verificata — 1 reperto (F5), resto confermato |
| 2 | `performance-metrics/fifo-engine/index.en.md` | Verificata — nessun reperto |
| 3 | `performance-metrics/fifo-engine/fifo-lot-analysis.en.md` | Verificata — nessun reperto |
| 4 | `performance-metrics/portfolio-engine/index.en.md` | Verificata — 1 reperto (F1) |
| 5 | `performance-metrics/portfolio-engine/book-value.en.md` | Verificata — nessun reperto |
| 6 | `performance-metrics/portfolio-engine/deposited-capital.en.md` | Verificata — 1 reperto (F1, condiviso) |
| 7 | `performance-metrics/portfolio-engine/mwrr.en.md` | Verificata — nessun reperto |
| 8 | `performance-metrics/portfolio-engine/nav.en.md` | Verificata — nessun reperto |
| 9 | `performance-metrics/portfolio-engine/net-annualized-return.en.md` | Verificata — nessun reperto |
| 10 | `performance-metrics/portfolio-engine/period-pnl.en.md` | Verificata — nessun reperto |
| 11 | `performance-metrics/portfolio-engine/price-resolution.en.md` | Verificata — nessun reperto |
| 12 | `performance-metrics/portfolio-engine/roi.en.md` | Verificata — nessun reperto |
| 13 | `performance-metrics/portfolio-engine/timing-effect.en.md` | Verificata — nessun reperto |
| 14 | `performance-metrics/portfolio-engine/twrr.en.md` | Verificata — nessun reperto |
| 15 | `performance-metrics/weighted-average-cost.en.md` | Verificata — 2 reperti (F2, F4) |
| 16 | `risk-metrics/index.en.md` | Funzionalita' beta, fuori scope — nessun reperto |
| 17 | `risk-metrics/max-drawdown.en.md` | Funzionalita' beta, fuori scope — nessun reperto |
| 18 | `risk-metrics/sharpe-ratio.en.md` | Funzionalita' beta, fuori scope — nessun reperto |
| 19 | `risk-metrics/sortino-ratio.en.md` | Funzionalita' beta, fuori scope — nessun reperto |
| 20 | `risk-metrics/volatility.en.md` | Funzionalita' beta, fuori scope — nessun reperto |

Nessun link interno rotto tra le 20 pagine (verifica automatica di tutti i link
relativi Markdown, tenendo conto della convenzione di suffisso lingua `.en.md`).
Le immagini di galleria referenziate in `fifo-lot-analysis.en.md`
(`fifo-lots-gantt-chart`, `fifo-lots-wac-chart`, `fifo-lots-comparison-chart-return`,
`fifo-lots-custody-modal`, `fifo-lots-table`) e l'ancora
`user/dashboard/positions.md#fifo-lots-analysis` esistono e sono valide. I link verso
la developer guide (`fifo_lot_engine.md`, `lots_analysis_service.md`) non sono stati
verificati: la developer guide e' sospesa da questo audit per decisione esplicita
(vedi indice centrale).

---

## Reperti

### F1 — CASH_TRANSFER interno: la gamba di arrivo non replica la formula K/R documentata

- **Classe**: Contraddizione
- **Gravita'**: major
- **Confidenza**: alta

**Claim**: `portfolio-engine/index.en.md` §6, riga tabella `CASH TRANSFER (Internal)`:

> Arrival Leg ($d$): $K_d \mathrel{+}= \kappa$, $R_d \mathrel{+}= \rho$

cioe' la gamba di arrivo dovrebbe ripartire l'importo tra capitale ($\kappa$) e
rendimenti ($\rho$) esattamente come la gamba di partenza. La stessa formula e'
ripresa in `deposited-capital.en.md` ("Full per-broker update rules" rimanda a questa
sezione) e nel box "Key properties": *"Cash transfers between brokers move R and K
from source to destination without touching W."*

**Controprova**: `backend/app/services/portfolio_engine.py`

- Fase pre-frame, righe 686-687:
  ```python
  elif ctxn.classification == "linked_internal" and tx.amount > 0:
      # Arrival leg (positive amount = inflow)
      # Approximate: add to K (can't track exact split without buffering)
      K[bid] += amt
  ```
- Fase frame (loop giornaliero principale), righe 977-981:
  ```python
  elif ctxn.classification == "linked_internal" and tx.amount > 0:
      # Arrival leg: receives from paired broker
      # Approximate: proportional to departure (use K as default)
      K[bid] += amount_target
  ```

In entrambe le fasi l'intero importo in arrivo confluisce in $K_d$; non esiste alcuna
ripartizione verso $R_d$. Il commento nel codice stesso ammette l'approssimazione
("can't track exact split without buffering"). La riconciliazione proporzionale
descritta subito dopo nella pagina (`§6 Reconciliation invariant`, usata per il drift
dovuto a FX/in-transit) agisce solo sui totali aggregati per riportare
$\sum K_b + \sum R_b$ vicino a `Cash_like`; non corregge la classificazione
capitale/rendimento della singola gamba di arrivo.

**Impatto**: il grafico Growth Chart (Cash from Capital / Cash from Returns) e la
sezione "Deposited Capital" possono mostrare un rendimento accumulato ($R$)
sistematicamente sotto-stimato — e il capitale ($K$) sovra-stimato — su qualunque
broker che riceve trasferimenti di cassa interni da un broker con rendimenti
maturati. NAV, ROI, TWRR/MWRR e Total PnL non sono affetti (dipendono da
`cumulative_external_cash_flow`, non da questa ripartizione K/R).

**Direzione di correzione suggerita**: allineare il codice alla formula (propagare la
quota $\rho/\kappa$ osservata in partenza fino alla gamba di arrivo, es. bufferizzando
il rapporto per transazione linked-internal), oppure aggiornare la pagina per
descrivere esplicitamente l'approssimazione "100% a K" attualmente implementata.

---

### F2 — WAC multi-valuta: la pagina afferma "valuta piu' frequente", il codice implementa "valuta dell'ultima acquisizione"

- **Classe**: Contraddizione
- **Gravita'**: major
- **Confidenza**: alta

**Claim**: `weighted-average-cost.en.md`, sezione "🌍 Multi-Currency Handling":

> 1. Determines the **target currency** (most frequent among acquisitions)
> 2. Converts all unit costs to the target currency using historical FX rates
> 3. Computes WAC in the unified target currency

**Controprova**: `backend/app/utils/financial/wac_utils.py:52-59`

```python
def determine_target_currency(txs: list[WACInputTX], asset_currency: str) -> str:
    """Determine target currency from acquisition TXs.

    Rule: currency of the most recent acquisition (deterministic).
    Fallback: asset_currency when no acquisitions exist.
    """
    acquisitions = [tx for tx in txs if tx.quantity > 0]
    if not acquisitions:
        return asset_currency
    latest = max(acquisitions, key=lambda t: t.date)
    return latest.original_currency or asset_currency
```

La regola implementata seleziona la valuta dell'acquisizione **cronologicamente piu'
recente** (`max(..., key=lambda t: t.date)`), non quella statisticamente **piu'
frequente**. Le due regole divergono in qualunque posizione multi-valuta dove
l'acquisto piu' recente non e' nella valuta maggioritaria (es. 3 BUY in EUR seguiti da
1 BUY in USD: "piu' frequente" → EUR, "piu' recente" → USD).

**Nota aggiuntiva (non un reperto separato, ma rilevante per completezza)**: questa
funzione e' usata da `portfolio_service.py` (endpoint di posizione / WAC preview del
form transazioni, righe 200 e 453) e da `lots_analysis_service.py`. Il loop giornaliero
principale in `portfolio_engine.py`, invece, non chiama mai
`determine_target_currency`: mantiene il pool WAC nella valuta **fissa** dell'asset
(`self.asset_currencies`, popolato da `asset.currency`) e converte solo in lettura. La
pagina descrive un unico algoritmo multi-valuta unificato, ma nel codice coesistono
due comportamenti diversi a seconda del punto di ingresso (motore giornaliero vs
endpoint on-demand); questa distinzione non e' documentata da nessuna parte nella
pagina.

**Direzione di correzione suggerita**: correggere "most frequent" in "most recent" (o
allineare il codice alla regola descritta), e aggiungere una nota che distingue il
comportamento del motore giornaliero (valuta fissa dell'asset) da quello degli
endpoint on-demand (valuta dell'ultima acquisizione).

---

### F4 — Link di aiuto WAC nel frontend punta a un percorso mkdocs inesistente

- **Classe**: Navigazione/link
- **Gravita'**: major
- **Confidenza**: alta

**Claim implicita**: la pagina `weighted-average-cost.en.md` e' raggiungibile
dall'icona di aiuto del form transazioni (anteprima WAC), come da UX pattern usato
altrove nell'app per le pagine di teoria finanziaria.

**Controprova**:
`frontend/src/lib/components/transactions/wac/WacPreviewSection.svelte:436`

```svelte
<DocsLink path="financial-theory/portfolio-theory/weighted-average-cost/" ... />
```

`DocsLink.svelte` (`frontend/src/lib/components/ui/DocsLink.svelte`) costruisce l'URL
come `` `/mkdocs/${prefix}${path}` ``, quindi il link risolto e'
`/mkdocs/financial-theory/portfolio-theory/weighted-average-cost/`. Questa cartella
esiste (`mkdocs_src/docs/financial-theory/portfolio-theory/`) ma **non contiene** un
file `weighted-average-cost`; contiene solo `index`, `asset-allocation`,
`diversification`. La pagina reale vive in
`financial-theory/technical-analysis/performance-metrics/weighted-average-cost.md`,
confermato anche dalla nav ufficiale (`mkdocs_src/mkdocs.yml:821`):

```yaml
- Weighted Average Cost: financial-theory/technical-analysis/performance-metrics/weighted-average-cost.md
```

Cliccando l'icona di aiuto nell'anteprima WAC del form transazioni, l'utente arriva a
una pagina 404 sul sito mkdocs pubblicato, invece della pagina WAC corretta.

**Direzione di correzione suggerita**: correggere il `path` in
`financial-theory/technical-analysis/performance-metrics/weighted-average-cost/`.

---

### F5 — "UI Integration & Dashboard Help Links" sovrastima la diretteza dei link delle KPI card

- **Classe**: Dettaglio obsoleto
- **Gravita'**: minor
- **Confidenza**: alta

**Claim**: `performance-metrics/index.en.md`, sezione finale "🔗 UI Integration &
Dashboard Help Links":

> Net Worth (NAV) widgets link **directly** to the `NAV / Net Worth
> Page (portfolio-engine/nav.md)`. ... Period P&L widgets link directly to ... Timing
> Effect widgets link directly to ... ROI widgets link directly to ... TWRR ... MWRR
> ... Deposited Capital / Total P&L ... links to the `Deposited Capital & Total P&L
> Page (portfolio-engine/deposited-capital.md)`.

**Controprova**: `frontend/src/lib/components/dashboard/KpiSection.svelte` — le tre
icone di aiuto delle KPI card puntano tutte a un'unica pagina manuale utente con
ancore, non alle singole pagine di teoria finanziaria elencate:

```
Riga 242: <DocsLink path="user/dashboard/kpi-cards/#card-1-period-pl" .../>
Riga 293: <DocsLink path="user/dashboard/kpi-cards/#card-2-returns" .../>
Riga 328: <DocsLink path="user/dashboard/kpi-cards/#card-3-net-worth" .../>
```

`mkdocs_src/docs/user/dashboard/kpi-cards.en.md` a sua volta rimanda, in modo
corretto, alle pagine di teoria elencate nel reperto (NAV, Book Value, Period P&L,
ROI, TWRR, MWRR, Timing Effect, Deposited Capital — tutti i link verificati
risolvono). Il percorso reale e' quindi in due passaggi (KPI card → manuale utente →
teoria finanziaria), non un link diretto come descritto. La destinazione finale resta
raggiungibile, quindi la severita' e' minor e non una rottura di navigazione.

**Direzione di correzione suggerita**: correggere "link directly to" in "link to the
User Manual card, which cross-references" o equivalente, per riflettere il percorso a
due passaggi realmente implementato.

---

## Campioni verificati (claim confermate accurate)

Elenco non esaustivo delle claim piu' rilevanti verificate positivamente durante
l'audit, a supporto della disposizione "Verificata — nessun reperto" sopra:

| Claim | Pagina | Controprova |
|---|---|---|
| Cash flow MWRR/TWRR costruiti dai delta di `cumulative_external_cash_flow`, non dai depositi cash-only | `mwrr.en.md`, `twrr.en.md` | `portfolio_engine.py:1607-1637` `build_performance_inputs()` |
| Formula 3-pool DEPOSIT/WITHDRAWAL/DIVIDEND/INTEREST/FEE/TAX/BUY/SELL (tutte tranne CASH_TRANSFER arrivo, F1) | `portfolio-engine/index.en.md` §6 | `portfolio_engine.py:931-1010` |
| Resolver MARKET→TRADE_AVG→CARRIED→MISSING, marks in valuta nativa, qbq applicato prima del resolver | `price-resolution.en.md`, `nav.en.md` | `price_resolver.py:11-14, 224-240` |
| Grace period di 14 giorni per l'avviso "no market price for more than two weeks" | `nav.en.md`, `price-resolution.en.md` | `portfolio_engine.py:420` `TRANSACTION_IMPLIED_GRACE_DAYS = 14`; stringa i18n `frontend/src/lib/i18n/en.json:1240` |
| Soglia minima di 30 giorni per l'annualizzazione (altrimenti nessun valore) | `net-annualized-return.en.md` | `roi_utils.py` `_MIN_ANNUALIZATION_DAYS = 30` |
| Regola D-1 di eleggibilita' per l'allocazione pro-rata di dividendi/interessi, scoping per broker pagante | `fifo-lot-analysis.en.md` | `fifo_lot_engine.py:1066-1204` `_allocate_income_pools`, `_eligible_income_quantity` |
| Scala deterministica di allocazione costi FEE/TAX (stessa giornata trade → giorno precedente → holding → orphan) | `fifo-lot-analysis.en.md` | `fifo_lot_engine.py:1206-1213` (commento identico alla tabella della pagina) |
| WAC: ordine additions-poi-reductions nello stesso giorno, dilution a costo zero, modalita' "auto" invariante | `weighted-average-cost.en.md` | `wac_utils.py:96-165` |
| Insieme di transazioni "lot-affecting" = {BUY, SELL, ADJUSTMENT, TRANSFER} per la finestra di annualizzazione | `net-annualized-return.en.md`, `roi.en.md` | `portfolio_service.py:757` `_LOT_AFFECTING_TYPES` |
| Ritorno annualizzato per lotto usa `net_total_return`, non quello lordo | `fifo-lot-analysis.en.md` | `lots_analysis_service.py:1338-1356` |
| Card dashboard "Returns" mostra Timing Effect, ROI, TWRR cumulativo, MWRR cumulativo e annualizzato | `mwrr.en.md`, `timing-effect.en.md` | `frontend/.../KpiSection.svelte:283-306` |
| qbq: `HoldingValue = (qty/qbq) × price`, coerente ovunque nel motore lotti | `fifo-lot-analysis.en.md` | `valuation_utils.compute_holding_value`, `lots_analysis_service.py` |

---

## Fuori ambito codice / non verificabile

- Le pagine `risk-metrics/**/*.en.md` riguardano funzionalita' beta e sono
  intenzionalmente escluse dai reperti sulla documentazione pubblica.
- Riferimenti a `../../../../developer/backend/transactions/fifo_lot_engine.md` e
  `.../lots_analysis_service.md` in `fifo-engine/index.en.md` e
  `fifo-lot-analysis.en.md`: la developer guide resta sospesa da questo audit per
  decisione dell'utente; la validita' di questi link non e' stata verificata.
- Nota storica "Changed in FIFO v5" in `fifo-lot-analysis.en.md`: descrive un
  comportamento di una versione precedente del motore. Non verificabile dal solo
  stato attuale del repository (nessuna cronologia di versioni algoritmiche
  esaminata); il comportamento attuale (D-1, scoping per broker) e' comunque
  confermato corretto.

---

## Riepilogo

| Metrica | Valore |
|---|---|
| Pagine assegnate | 20 |
| Pagine con almeno un reperto | 4 (`performance-metrics/index`, `portfolio-engine/index`, `deposited-capital`, `weighted-average-cost`) |
| Pagine verificate senza reperti | 16 |
| Reperti totali | 4 (F1, F2, F4, F5) |
| — Contraddizione | 2 (F1, F2) |
| — Dettaglio obsoleto | 1 (F5) |
| — Navigazione/link | 1 (F4) |
| — Omissione | 0 |
| Per gravita': major | 3 (F1, F2, F4) |
| Per gravita': minor | 1 (F5) |
| Per gravita': info | 0 |
| Confidenza alta su tutti i reperti | Si' |
| Link interni rotti tra le 20 pagine | 0 |
| Drift rispetto alla baseline durante l'audit | Nessuno osservato |
