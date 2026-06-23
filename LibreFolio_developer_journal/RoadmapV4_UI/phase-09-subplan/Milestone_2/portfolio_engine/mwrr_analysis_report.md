# MWRR/TWRR/ROI Analysis Report
_Code-level audit — no code modified_

---

## 1. Causa del MWRR -36.71% nella card

**TL;DR: bug di double-counting dei depositi nell'XIRR.**

### Come viene calcolato `mwrr_percent` nella summary

In `portfolio_service.py` ~riga 782:

```python
mwrr_point = await asyncio.to_thread(
    calculate_mwrr, cash_flows_perf, total_invested,
    engine_nav, nav_snapshots[0].date, today,
)
```

In `roi_utils.py` → `calculate_mwrr()`:

```python
flows.append((0.0, -float(initial_nav)))            # t=0: -total_invested
flows.append((float(total_days), float(final_nav)))  # t=T: +engine_nav_today
for cf in cash_flows:
    days = (cf.date - start_date).days
    if 0 < days < total_days:
        flows.append((float(days), float(cf.amount)))  # flussi intermedi
```

### Il bug: `initial_nav = total_invested`

`total_invested` = somma di tutti i DEPOSIT meno i WITHDRAWAL nella valuta base.

`cash_flows_perf` proviene da `build_performance_inputs()`:

```python
cash_flows = [
    CashFlowInput(date=s.date, amount=-s.external_cash_flow)
    for s in self.daily_states if s.external_cash_flow != 0
]
```

`external_cash_flow` è il DEPOSIT/WITHDRAWAL di quel giorno (prospettiva portfolio → positivo per depositi).
Quindi `cash_flows_perf` contiene i depositi come flussi negativi (prospettiva investitore).

Risultato: l'equazione NPV ha:
- `t=0`: `−total_invested` (tutti i depositi sommati e messi al giorno 0)
- `t=d1..dn`: `−deposit_i` (gli stessi depositi anche alle loro date reali)
- `t=T`: `+final_nav`

**I depositi vengono contati due volte.** Il totale "investito" è `2 × Σdepositi − Σprelievi`.

### Esempio concreto

| Giorno | Flusso corretto | Flusso con bug |
|--------|----------------|----------------|
| 0 | 0 | `−1500` (synthetic total) |
| 0 | `−1000` (primo deposito) | `−1000` |
| 100 | `−500` (secondo deposito) | `−500` |
| 365 | `+1800` (NAV finale) | `+1800` |

Con il bug, NPV a `r=0`:
```
NPV = −1500 − 1000 − 500 + 1800 = −1200
```
Per fare `NPV = 0` il solver deve trovare un tasso molto negativo (il -36.71% visto in UI).

Con la correzione (`initial_nav = nav_snapshots[0].nav ≈ 0`):
```
NPV = 0 − 1000 − 500 + 1800 = +300
```
Il solver converge a un tasso positivo coerente con i valori attesi (~+26%).

---

## 2. Mappa completa dei campi attuali

### Backend fields

| Campo | Tipo | Dove calcolato | Semantica |
|-------|------|----------------|-----------|
| `simple_roi_percent` | `SafeDecimal` | `portfolio_service.get_summary()` | Cumulativo: `(NAV − invested) / invested` su tutta la storia |
| `twrr_percent` | `SafeDecimal \| None` | `portfolio_service.get_summary()` | **Cumulativo** TWRR su tutta la storia (non annualizzato) |
| `mwrr_percent` | `SafeDecimal \| None` | `portfolio_service.get_summary()` | **Annualizzato** XIRR — oggi **BUGGED** (double-counting) |
| `PortfolioHistoryPoint.twrr` | `SafeDecimal \| None` | `portfolio_service.get_history()` | Cumulativo TWRR per ogni giorno (rebased a `date_from`) |
| `PortfolioHistoryPoint.mwrr` | `SafeDecimal \| None` | `portfolio_service.get_history()` | **Annualizzato** MWRR per ogni giorno (rebased a `date_from`) — implementazione CORRETTA |
| `PortfolioHistoryPoint.roi` | `SafeDecimal \| None` | `portfolio_service.get_history()` | Cumulativo Simple ROI per ogni giorno |

### Mismatch critico tra summary e history

| Metrica | Summary | History point finale |
|---------|---------|---------------------|
| TWRR | Cumulativo (sull'intera storia) | Cumulativo (rebased a date_from) |
| MWRR | BUGGED + annualizzato + full history | Annualizzato (rebased a date_from) — corretto |
| ROI | Cumulativo (intera storia) | Cumulativo (rebased a date_from) |

La summary ignora il `date_from` selezionato dall'utente.
L'engine in `get_summary()` gira sempre con `date_from=None, date_to=None`.

### Frontend → quale campo viene mostrato dove

| UI elemento | Campo usato | Note |
|-------------|-------------|------|
| Card "ROI Ponderato" (valore principale) | `summary.simple_roi_percent * 100` | Cumulativo ✓ |
| Card sub-label "TWRR: X%" | `summary.twrr_percent * 100` | Cumulativo ✓ |
| Card sub-label "MWRR: X%" | `summary.mwrr_percent * 100` | **BUGGED** ✗ |
| GrowthChart % mode — linea MWRR | `history[].mwrr * 100` | Annualizzato (ma corretto) |
| GrowthChart % mode — linea TWRR | `history[].twrr * 100` | Cumulativo |
| GrowthChart % mode — linea ROI | `history[].roi * 100` | Cumulativo |

### Problema di incoerenza nel grafico

Il grafico mostra MWRR (annualizzato) accanto a TWRR e ROI (cumulativi). Per periodi
pluriennali sono misure incomparabili:

- Portfolio di 3 anni, crescita totale +80%
  - TWRR chart finale: **+80%**
  - MWRR chart finale: **~+21%** (annualizzato ≈ (1.80)^(1/3)−1)
  - Appaiono sullo stesso grafico a scale molto diverse → confonde l'utente

---

## 3. Incoerenza card vs grafico — spiegazione dettagliata

```
card MWRR = −36.71%    ← XIRR con double-counting → converge a tasso fortemente negativo
chart MWRR ≈ +26%      ← XIRR corretto (initial_nav = nav[0] ≈ 0) → annualizzato ~correct
```

Il grafico usa `calculate_mwrr_series()` che prende `initial_nav = sorted_navs[0].nav`.
Per un portfolio che parte da zero, `sorted_navs[0].nav = 0`, e il t=0 flow è nullo.
I depositi entrano come flussi intermedi alle loro date reali. ✓

La card usa `calculate_mwrr()` con `initial_nav = total_invested` (SBAGLIATO).

---

## 4. Rebasing temporale

### Cosa cambia con `date_from`

| Metrica | Risponde a date_from? |
|---------|----------------------|
| Card ROI | ✗ sempre full history |
| Card TWRR | ✗ sempre full history |
| Card MWRR | ✗ sempre full history |
| Chart TWRR | ✓ rebased con synthetic CF |
| Chart MWRR | ✓ rebased con synthetic CF |
| Chart ROI | ✓ rebased |

La summary è quindi **sempre full-history** indipendentemente dal `DateRangePicker`.
Solo il grafico risponde al filtro data.

---

## 5. Proposta DTO — `mwrr_annualized` e `mwrr_cumulative`

### Definizione

```
mwrr_annualized  = tasso XIRR come lo restituisce il solver (d/365 exponent)
mwrr_cumulative  = (1 + mwrr_annualized)^(period_days / 365) − 1
```

Dove `period_days = (end_date − start_date).days`.

Oppure, più direttamente:

```
mwrr_cumulative = (1 + daily_rate)^period_days − 1
  dove daily_rate = (1 + mwrr_annualized)^(1/365) − 1
```

### PortfolioSummary (modifiche proposte)

```python
# rimuovere:
mwrr_percent: Optional[SafeDecimal]

# aggiungere:
mwrr_annualized: Optional[SafeDecimal]  # XIRR annualizzato
mwrr_cumulative: Optional[SafeDecimal]  # (1+r_ann)^(days/365) − 1 sul periodo
mwrr_period_days: Optional[int]         # giorni del periodo MWRR (per debug/UI)
```

### PortfolioHistoryPoint (modifiche proposte)

```python
# rimuovere (o tenere ma documentare):
mwrr: Optional[SafeDecimal]   # oggi annualizzato, rename consigliato

# aggiungere:
mwrr_annualized: Optional[SafeDecimal]
mwrr_cumulative: Optional[SafeDecimal]
```

### PortfolioReportResponse

Transitivo: la summary e history già contengono le metriche. Nessun campo
aggiuntivo nel wrapper.

---

## 6. Regole UI proposte

### Grafico % mode
- Mostrare **`mwrr_cumulative`** (non annualizzato)
- Così MWRR, TWRR e ROI sono tutti cumulativi → comparabili sullo stesso grafico

### Card KPI

**Valore principale**: mantenere `simple_roi_percent` (ROI cumulativo)

**Sub-label**:
```
TWRR: +26.51% | MWRR: +24.3% (ann.)
```
o con tooltip:
```
MWRR cumulativo: +X% | MWRR annualizzato: +Y%
```

**Priorità display**:
1. Mostrare `mwrr_cumulative` come valore principale MWRR nella sub-label
2. Mostrare `mwrr_annualized` come secondario (tooltip o sub-sub)
3. Se periodo < 30 giorni → nascondere annualizzato o aggiungere `(ann. *)`
4. Se `|mwrr_annualized| > 200%` → mostrare solo cumulativo con asterisco

### Policy "non significativo"

| Condizione | Azione |
|------------|--------|
| `period_days < 30` | Nascondere `mwrr_annualized`, mostrare solo cumulativo |
| `period_days < 7` | Nascondere entrambi, mostrare "—" |
| `mwrr_annualized > 5.0` (500%) | Mostrare solo cumulativo, aggiungere nota |
| `mwrr == None` | Banner `MWRR_NOT_CALCULABLE` già esistente |

---

## 7. Modifiche richieste — lista file

### Backend

| File | Modifica |
|------|---------|
| `backend/app/services/portfolio_service.py` | **Fix bug principale**: `initial_nav = nav_snapshots[0].nav` (non `total_invested`) in `get_summary()` |
| `backend/app/services/portfolio_service.py` | Calcolare e restituire `mwrr_cumulative` in `get_summary()` |
| `backend/app/services/portfolio_service.py` | Calcolare e restituire `mwrr_cumulative` in `get_history()` per ogni history point |
| `backend/app/utils/financial/roi_utils.py` | Aggiungere helper `annualized_to_cumulative(r, days)` |
| `backend/app/schemas/portfolio.py` | Aggiungere `mwrr_annualized`, `mwrr_cumulative`, `mwrr_period_days` in `PortfolioSummary` e `PortfolioHistoryPoint` |

### Frontend

| File | Modifica |
|------|---------|
| `frontend/src/lib/components/dashboard/GrowthChart.svelte` | % mode usa `mwrr_cumulative` invece di `mwrr` |
| `frontend/src/routes/(app)/dashboard/+page.svelte` | Card mostra `mwrr_cumulative` + tooltip `mwrr_annualized` |
| `frontend/src/lib/i18n/{en,it,fr,es}.json` | Aggiungere `dashboard.mwrrAnnualized`, `dashboard.mwrrCumulative` |
| API client (`./dev.py api sync`) | Rigenerare dopo modifiche DTO |

### Docs

| File | Modifica |
|------|---------|
| `mkdocs_src/docs/financial-theory/technical-analysis/performance-metrics/mwrr.en.md` | Sezione su annualizzato vs cumulativo, formula di conversione, esempio numerico |
| Tutte le traduzioni (`mwrr.it.md`, `.fr.md`, `.es.md`) | Allineamento |

---

## 8. Formula matematica corretta

### XIRR / MWRR annualizzato

Il solver risolve:

$$
0 = \sum_{i=0}^{n} \frac{CF_i}{(1 + r)^{t_i / 365}}
$$

dove:
- $CF_0 = -\text{NAV}_{t_0}$ (valore portfolio all'inizio del periodo)
- $CF_i = -\text{deposito}_i$ o $+\text{prelievo}_i$ per flussi intermedi
- $CF_n = +\text{NAV}_{t_n}$ (valore portfolio alla fine)
- $r$ = tasso annualizzato (annualized)

**NOTA CRITICA**: il flusso $CF_0$ deve essere il **NAV reale a $t_0$**, non il totale investito cumulativo. Per un portfolio che parte da zero, $CF_0 = 0$.

### Da annualizzato a cumulativo

$$
r_{\text{cum}} = (1 + r_{\text{ann}})^{d/365} - 1
$$

dove $d = t_n - t_0$ in giorni.

### Esempio di conversione

| Periodo | r_ann | r_cumulative |
|---------|-------|-------------|
| 6 mesi | +26% | +12.4% |
| 1 anno | +26% | +26.0% |
| 2 anni | +26% | +58.8% |
| 3 anni | +26% | +100.2% |

Per periodi brevi l'annualizzato sopravvaluta fortemente; per periodi lunghi
sottovaluta il guadagno totale.

---

## 9. Bug probabilities e test necessari

### Bug confermati

| # | Descrizione | Gravità | File | Riga ~|
|---|-------------|---------|------|--------|
| 1 | `initial_nav = total_invested` in `calculate_mwrr()` call da `get_summary()` | **CRITICO** | `portfolio_service.py` | 782 |
| 2 | Card MWRR non risponde al `date_from` selezionato | MEDIO | `portfolio_service.py` | 559+ |
| 3 | Grafico mostra MWRR annualizzato accanto a TWRR/ROI cumulativi | MEDIO | `GrowthChart.svelte` | 82 |

### Test da aggiungere

```
test_mwrr_summary_no_double_counting
  - portfolio: deposito 1000 giorno 0, deposito 500 giorno 180, NAV oggi 1800
  - mwrr_percent (dopo fix) deve essere > 0
  - mwrr deve essere simile al TWRR (stessa storia, no timing distortion)

test_mwrr_cumulative_matches_annualized
  - dati sintetici: r_ann noto
  - verifica r_cum = (1 + r_ann)^(days/365) − 1

test_mwrr_series_is_annualized
  - verifica che calculate_mwrr_series restituisce il tasso annualizzato
  - per periodo 1 anno esatto: annualizzato == cumulativo

test_mwrr_summary_respects_date_range
  - verifica che con date_from diverso, mwrr_percent nella summary cambia
  - (questo test fallisce attualmente — conferma bug 2)

test_mwrr_not_calculable_short_period
  - periodo < 2 giorni → mwrr = None e banner MWRR_NOT_CALCULABLE presente
```

---

## 10. Domande aperte residue

1. **Breaking change o retrocompatibile?** Rinominare `mwrr_percent` → `mwrr_annualized`
   è un breaking change per API client e test. Valutare se fare entrambi per un periodo
   di transizione o fare clean break.

2. **Summary risponde a date_from?** Attualmente la summary è sempre full-history.
   Sarebbe corretto che ROI/TWRR/MWRR nella card rispecchiassero il `date_from` selezionato?
   Se sì, richiede passare `date_from` a `get_summary()` e all'engine (ora ignorato).

3. **Chart MWRR series all'inizio** — il primo punto del grafico ha `mwrr = 0.0` (hardcoded
   per continuità grafico). Dopo switch a `mwrr_cumulative` verificare che il padding iniziale
   sia ancora sensato.

4. **MWRR_NOT_CALCULABLE** — attualmente emesso quando `mwrr_result is None`. Dopo il fix
   del bug, il solver dovrebbe convergere più spesso. Verificare se il banner scompare o
   rimane per casi legittimi.

5. **Portfolio senza depositi/prelievi** — se l'utente ha solo BUY/SELL/DIV senza DEPOSIT/WITHDRAWAL
   espliciti, `external_cash_flow = 0` su tutti i giorni. Sia il bug che la correzione
   restituiscono risultati degeneri. Documentare questa limitazione.

---

## 11. Sintesi esecutiva

| Aspetto | Stato attuale | Dopo fix |
|---------|--------------|---------|
| Card MWRR | ERRATO (double-counting) | Corretto, annualizzato |
| Chart MWRR | Corretto ma annualizzato | Mostrare cumulativo |
| Card TWRR | Corretto, cumulativo full-history | — |
| Chart TWRR | Corretto, cumulativo rebased | — |
| Confronto grafico | MWRR ≠ TWRR/ROI (diverse scale per periodi lunghi) | Tutti cumulativi |
| `mwrr_cumulative` | Assente | Da aggiungere |
| Date range rispettato in card | ✗ | Decisione da prendere |

**Il fix minimale per eliminare il -36.71%** è una sola riga in `portfolio_service.py`:
sostituire `total_invested` con `nav_snapshots[0].nav` nella chiamata a `calculate_mwrr`.

**Il fix completo** richiede aggiungere `mwrr_cumulative` ovunque, aggiornare il grafico
per usarlo, e allineare la semantica della card con quella del grafico.
