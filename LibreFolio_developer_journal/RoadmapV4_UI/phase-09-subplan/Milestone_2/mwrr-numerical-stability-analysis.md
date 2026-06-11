# MWRR / XIRR — Analisi di stabilità numerica

> File di appoggio per discussione ad alto livello sull'implementazione MWRR.
> Contesto: Phase 09 Step 2 — Dashboard backend patch.
> Data: 2026-06-11

---

## Contesto

LibreFolio calcola il MWRR (Money-Weighted Rate of Return / XIRR) storico
per ogni snapshot del portfolio.

**File rilevante:** `backend/app/utils/financial/roi_utils.py`

---

## Il problema osservato

Output dell'endpoint `GET /api/v1/portfolio/history`:

```json
{ "date": "2025-01-05", "mwrr": "11703813395738028.000000", ... }
```

Valore assurdo (~1.17 × 10^16 = 1.17 quadrilioni di %).
In un secondo caso precedente, il valore era `infinity` (già fixato con `math.isfinite`).

---

## Come funziona l'implementazione attuale

MWRR viene calcolato come XIRR (Extended Internal Rate of Return):

```
NPV(r) = Σ [ amount_i / (1 + r)^(days_i / 365) ] = 0
```

Flussi costruiti così per ogni snapshot a data T:
- `(day=0,   amount=-initial_NAV)` — investitore "compra" il portfolio all'inizio
- `(day=d_i, amount=cf_i)`        — cash flow intermedi (depositi negativi, prelievi positivi)
- `(day=T,   amount=+final_NAV)`  — investitore "vende" il portfolio a fine periodo

Si usa `scipy.optimize.newton` (Newton-Raphson) con `x0=0.1`, `tol=1e-8`, `maxiter=100`.

**Ottimizzazione warm-start:** `prev_guess = rate` dell'iterazione precedente,
in modo che ogni snapshot usi come punto di partenza il risultato del precedente.

---

## Il valore 1.17e16 è un bug numerico o matematica corretta?

Dati del punto incriminato (2025-01-01 → 2025-01-05, **4 giorni**):

| Campo | Valore |
|-------|--------|
| NAV iniziale | 4 000 |
| NAV finale | 6 000 (+50% in 4 giorni) |
| Cash flow intermedio | −400 al giorno 1 |

**Verifica analitica dell'annualizzazione:**

```
MWRR_annualizzato ≈ (1 + 0.50)^(365/4) − 1
                  = 1.5^91.25 − 1
                  ≈ e^(91.25 × ln 1.5)
                  ≈ e^(91.25 × 0.405)
                  ≈ e^36.96
                  ≈ 1.19 × 10^16
```

**Conclusione: il valore NON è un errore numerico di Newton-Raphson.**
È matematicamente corretto: annualizzare un +50% in 4 giorni produce
effettivamente ~10^16. Il calcolo è converso, il risultato è solo
informativamente inutile (artefatto dell'annualizzazione su periodo brevissimo).

---

## Fix applicato (da valutare)

Aggiunto un cap di magnitudine in `roi_utils.py`:

```python
_MAX_REASONABLE_RATE: float = 100.0  # ±10 000 %

# in calculate_mwrr e calculate_mwrr_series:
if not math.isfinite(rate) or abs(rate) > _MAX_REASONABLE_RATE:
    return MWRRPoint(date=end_date, mwrr=None)
```

---

## Domande aperte per la discussione

### 1. Il cap è l'approccio giusto?

Il cap di `100×` (±10 000%) è una soglia arbitraria:

| | |
|---|---|
| ✅ PRO | Semplice, zero false positives per portfolio normali |
| ❌ CON | Maschera un risultato matematicamente corretto, non risolve la causa radice |
| ❌ CON | Asset crypto potrebbero legittimamente avere >10 000% annualizzato su brevi periodi |

**Alternative più principiate:**

**(a) Minimum period check** — skip MWRR quando `total_days < N` (es. 30 giorni):
- Più corretto concettualmente: MWRR annualizzato su periodi <30 giorni è sempre un artefatto
- Semplice da implementare: un `if total_days < 30: return MWRRPoint(mwrr=None)`
- Svantaggio: MWRR nullo per il primo mese di ogni portfolio

**(b) Cap relativo al periodo** — reject se `abs(rate) > f(total_days)`, es.:
- `max_daily_gain = 0.50` → `max_annual = (1 + max_daily_gain)^(365/total_days)`
- Adattivo, ma complesso e ancora arbitrario

**(c) Non annualizzare** — restituire il rendimento del periodo grezzo (non annualizzato):
- Evita completamente gli artefatti
- Richiede cambio semantico dell'API e gestione nel frontend per confrontare periodi diversi

### 2. Bug potenziale nel warm-start

Quando il valore viene rifiutato (`abs(rate) > 100`), il codice fa `continue`
**senza aggiornare `prev_guess`**. `prev_guess` rimane al suo ultimo valore accettato
(o al seed iniziale 0.1).

Scenario problematico:
- Portfolio con molti snapshot nei primi giorni (es. aggiornamento quotidiano)
- Tutti i primi N snapshot hanno `total_days < X` e vengono rifiutati
- `prev_guess` rimane a 0.1 per tutti → nessun beneficio del warm-start
- Quando finalmente si ha un periodo sufficientemente lungo, x0=0.1 potrebbe
  convergere su un risultato scorretto se il "vero" MWRR è lontano da 0.1

**Domanda:** è più corretto resettare `prev_guess = 0.1` quando un valore viene rifiutato,
o tenerlo al suo ultimo valore accettato?

### 3. Semantica corretta dei cash flow

L'implementazione distingue tra:
- **Cash flow esterno**: denaro che entra/esce dal portafoglio dall'esterno (deposito/prelievo)
- **Rebalancing interno**: da liquidità → asset o viceversa (non cambia il NAV)

Dai dati osservati:
- 2025-01-02: `invested_value` 0→400, NAV rimane 4000 → **rebalancing interno** (buy)
- 2025-01-05: NAV 4000→6000 → price appreciation (nessun CF)

**Domanda critica:** nella `get_history()` di `portfolio_service.py`, come vengono
classificati i movimenti come CF esterni? Se un BUY viene erroneamente trattato come
deposito, la lista `cash_flows` sarà sbagliata e il MWRR sarà matematicamente corretto
ma finanziariamente sbagliato.

**Dove guardare:** `backend/app/services/portfolio_service.py`, funzione `get_history()` (~L746+)

### 4. Cambio algoritmo: Newton vs Brent

`scipy.optimize.brentq` (metodo di Brent) è più robusto di Newton per NPV malcondizionati:

| | Newton | Brent |
|---|---|---|
| Velocità | O(iter) con convergenza quadratica | O(iter) con convergenza superlineare |
| Robustezza | Può divergere (richiede derivata) | Garantisce convergenza (bracket richiesto) |
| Requisito | Solo x0 | Richiede [a, b] con sign change |
| Complessità | Semplice | Richiede bracket search preliminare |

Per trovare il bracket `[a, b]` con sign change si può fare una ricerca logaritmica:
`r ∈ {-0.999, -0.9, -0.5, 0, 0.5, 1, 5, 10, 100}` e trovare il primo cambio di segno.

---

## Dove guardare nel codice

```
backend/app/utils/financial/roi_utils.py
  L73-78   _PREC_PCT, _MAX_REASONABLE_RATE (nuova costante)
  L229-275 calculate_mwrr() — caso singolo, x0=0.1
  L278-336 calculate_mwrr_series() — serie cumulativa, warm-start
  L265-266 def npv(r): ...  ← funzione malcondizionata per d piccolo

backend/app/services/portfolio_service.py
  ~L746+   get_history() — costruisce nav_snapshots e cash_flows
           ← capire come vengono classificati i CF esterni
```

**Nota sulla malcondizionatura della NPV per d piccolo:**

```python
def npv(r: float) -> float:
    return sum(amount / (1.0 + r) ** (d / 365.0) for d, amount in flows)
```

Per `d = 1..4` giorni: `(1+r)^(d/365)` è quasi 1 per qualsiasi `r` ragionevole.
Es. per `r=1e16`: `(1+1e16)^(4/365) ≈ e^(0.011 × log(1e16)) ≈ e^(0.40) ≈ 1.49`

La funzione NPV diventa quasi costante per `r` grandi → gradiente quasi zero →
Newton non converge o converge su valori estremi arbitrari.

---

## Domanda finale

Qual è la strategia corretta per un portfolio tracker self-hosted?

1. **Minimum period** (skip MWRR per `total_days < 30`)?
2. **Cap di magnitudine** (fix attuale, `abs(rate) > 100`)?
3. **Cambio algoritmo** (Brent + bracket search)?
4. **Combinazione** (minimum period + Brent per i periodi validi)?

Considerando che gli utenti tipici hanno dati su settimane/mesi/anni,
e i casi problematici sono quasi sempre i primissimi giorni dopo il primo deposito.
