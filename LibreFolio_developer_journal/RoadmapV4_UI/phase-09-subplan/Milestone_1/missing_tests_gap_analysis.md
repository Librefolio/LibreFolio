# Gap Analysis — Test Mancanti per `PortfolioService`

> **Contesto**: Durante l'implementazione di Milestone 1 (2026-06-10) è emerso un `NameError`
> in `get_history()` (Bug 2) che i test di integrazione esistenti non avevano catturato.
> Questo documento identifica i test mancanti che avrebbero trovato il bug e quelli
> che proteggerebbero da regressioni future simili.

---

## Perché Bug 2 Non è Stato Catturato

```python
# get_history() — list comprehension finale (SBAGLIATO → CORRETTO)
return [
    PortfolioHistoryPoint(
        date=dt,
        cash_value=vals["cash"],      # NameError: 'vals' non definita
    )
    for dt in sorted(daily.keys())
]
```

Il test `test_empty_history` passava perché con portafoglio vuoto `daily` era vuoto,
quindi il list comprehension **non veniva mai eseguito** → il `NameError` dormiva silenzioso.

Il test `test_history_with_deposit` lo ha trovato perché creava una transazione reale
e quindi `daily` aveva almeno un entry.

**Categoria del bug**: *variable name mistake nel path of non-empty data* —
la classe più classica di bug non catturata da test che verificano solo il "caso vuoto".

---

## Test Mancanti per `get_history`

### Problema 1 — Nessun test verifica i valori numerici dell'output

I test attuali verificano solo:
- `isinstance(result, list)` ✅
- `"date" in point` ✅

Non verificano:
- `result[0].cash_value == Decimal("10000")` ❌
- `result[0].nav_value == result[0].cash_value + result[0].invested_value` ❌

**Test da aggiungere**:

```python
async def test_deposit_sets_cash_value(session, test_user, broker_with_access):
    """
    Deposito 10000 EUR → il punto di storia ha cash_value == 10000,
    invested_value == 0, nav_value == 10000.
    Questo test avrebbe catturato Bug 2 (NameError su vals["cash"]).
    """
    broker, _ = broker_with_access
    session.add(Transaction(
        broker_id=broker.id, type=TransactionType.DEPOSIT,
        date=date(2025, 1, 1), amount=Decimal("10000"), currency="EUR",
    ))
    await session.flush()

    service = PortfolioService(session)
    result = await service.get_history(user_id=test_user.id)

    assert len(result) >= 1
    point = next(p for p in result if p.date == date(2025, 1, 1))
    assert point.cash_value == Decimal("10000")
    assert point.invested_value == Decimal("0")
    assert point.nav_value == Decimal("10000")

async def test_buy_moves_cash_to_invested(session, test_user, broker_with_access):
    """
    Deposito 10000 → BUY 5000 → storia mostra:
      t0: cash=10000, invested=0
      t1: cash=5000, invested=5000, nav=10000
    Verifica la logica di redistribuzione cash→invested.
    """
    ...

async def test_nav_invariant(session, test_user, broker_with_access):
    """NAV = cash + invested per ogni punto della serie."""
    ...
    for point in result:
        assert point.nav_value == point.cash_value + point.invested_value
```

### Problema 2 — Nessun test verifica il sorting cronologico

```python
async def test_history_is_chronologically_sorted(session, test_user, broker_with_access):
    """I punti devono essere in ordine di data crescente."""
    # crea 3 transazioni in ordine sparso
    ...
    dates = [p.date for p in result]
    assert dates == sorted(dates)
```

### Problema 3 — Nessun test per `share_percentage != 1`

```python
async def test_share_percentage_halves_values(session, test_user):
    """Broker con share=0.5 → cash_value è la metà del deposito reale."""
    ...
    access.share_percentage = Decimal("0.5")
    ...
    # deposito 10000 → cash_value deve essere 5000
    assert result[0].cash_value == Decimal("5000")
```

---

## Test Mancanti per `get_summary`

### Problema — Test verificano solo struttura, non valori

```python
# ATTUALE (solo struttura):
assert "net_worth" in data  ← non cattura calcoli sbagliati

# DA AGGIUNGERE (valori):
async def test_summary_cash_only_portfolio(session, ...):
    """
    Solo depositi (nessun asset) → net_worth == cash_total == deposito.
    Se la formula di net_worth fosse sbagliata (es. net_worth = 0 per default),
    questo test fallirebbe.
    """
    # deposito 10000 EUR
    summary = await service.get_summary(user_id=test_user.id)
    assert summary.cash_total == Decimal("10000")
    assert summary.net_worth == Decimal("10000")
    assert summary.total_invested == Decimal("0")
    assert summary.total_gain_loss == Decimal("0")
    assert summary.simple_roi_percent == Decimal("0")

async def test_summary_allocations_sum_to_100(session, ...):
    """
    La somma delle percentuali in allocation_by_type deve essere ~100%.
    Cattura bug nel calcolo delle percentuali (es. divisione per zero,
    arrotondamenti sistematici).
    """
    ...
    total = sum(item.value for item in summary.allocation_by_type)
    assert abs(total - Decimal("100")) < Decimal("1")  # tolleranza 1%
```

---

## Test Mancanti per `get_lots`

### Problema — Nessun test verifica il P&L non realizzato

```python
async def test_open_lot_unrealized_pnl(session, ...):
    """
    open_lot.unrealized_pnl = (current_price - buy_price) * remaining_qty.
    Questo test verifica l'arricchimento con il prezzo corrente.
    Se il prezzo corrente fosse None o se la formula fosse sbagliata,
    il test fallirebbe.
    """
    # crea PriceHistory con prezzo noto
    # crea BUY transaction
    # verifica unrealized_pnl = (market_price - buy_price) * qty
    ...
```

---

## Strategia Generale: "Golden Path con Valori"

Il pattern mancante è il **"golden path con verifica dei valori"**:

| Tipo di test | Cosa verifica | Cattura Bug 2? |
|-------------|---------------|---------------|
| `assert isinstance(result, list)` | struttura | ❌ (lista vuota passa) |
| `assert len(result) > 0` | non-vuoto | ❌ (si ferma prima della lettura) |
| `assert result[0].cash_value == Decimal("10000")` | **valore** | ✅ → `NameError` esplode subito |

**Regola pratica per orchestratori async con DB**:
> Per ogni metodo che restituisce una lista o un oggetto con campi computati,
> aggiungere almeno un test che verifica il **valore esatto** di almeno un campo
> in uno scenario con dati reali (non vuoto). Questo è sufficiente per catturare
> bug nella fase di serializzazione/mapping (come Bug 2).

---

## Estrarre Logica Pura da `get_history` (Refactor Consigliato)

La strategia più robusta è **estrarre la logica di accumulo** in una funzione pura,
testabile senza DB:

```python
# Funzione pura estraibile da get_history():
def _build_history_series(
    transactions: list[tuple[date, TransactionType, Decimal, Decimal]],  # (date, type, amount, share)
) -> list[PortfolioHistoryPoint]:
    """
    Accumula i punti storici da una lista di transazioni già fetchata dal DB.
    Pura, sincrona, testabile.
    """
    daily: dict[date, dict[str, Decimal]] = defaultdict(...)
    cumulative_cash = Decimal("0")
    cumulative_invested = Decimal("0")

    for tx_date, tx_type, amount, share in sorted(transactions):
        if tx_type == TransactionType.DEPOSIT:
            cumulative_cash += amount * share
        ...
        daily[tx_date]["cash"] = cumulative_cash
        daily[tx_date]["invested"] = cumulative_invested
        daily[tx_date]["nav"] = cumulative_cash + cumulative_invested

    return [
        PortfolioHistoryPoint(date=dt, cash_value=daily[dt]["cash"], ...)
        for dt in sorted(daily.keys())
    ]
```

Con questa funzione pura:
- Il test è sincrono, senza DB, senza fixture async
- Bug 2 sarebbe stato catturato da un test di 5 righe
- Il refactor separa la logica computazionale dall'I/O (principio Single Responsibility)

---

## Riepilogo Priorità Test da Aggiungere

| Priorità | Test | Metodo | Motivo |
|----------|------|--------|--------|
| 🔴 Alta | `test_deposit_sets_cash_value` | `get_history` | Avrebbe trovato Bug 2 |
| 🔴 Alta | `test_buy_moves_cash_to_invested` | `get_history` | Verifica logica core |
| 🔴 Alta | `test_nav_invariant` | `get_history` | Invariante fondamentale |
| 🟡 Media | `test_summary_cash_only_portfolio` | `get_summary` | Valori aggregati |
| 🟡 Media | `test_allocations_sum_to_100` | `get_summary` | Invariante percentuali |
| 🟡 Media | `test_share_percentage_halves_values` | `get_history` | Logica share |
| 🟢 Bassa | `test_open_lot_unrealized_pnl` | `get_lots` | Arricchimento prezzo |
| 🟢 Bassa | `test_history_is_chronologically_sorted` | `get_history` | Ordinamento |
