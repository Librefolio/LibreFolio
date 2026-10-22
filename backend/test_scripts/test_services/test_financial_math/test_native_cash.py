"""
Unit tests for native cash (Lot 41, step F): cash held in the currency it was paid in.

Module under test: ``backend/app/services/financial_math/native_cash.py`` —
``effective_share``, ``cash_movement_from_transaction``, ``compute_native_cash`` and the
value objects they exchange (CashMovement, NativeCash, CashFlows, MissingCashConversion);
from step F-W also ``NativeCash.exchange_results`` and ``CONVERSION_DUST``.

What the module owes its callers, in one line: a broker's cash is the native balance of every
currency it holds, worth on any day that balance at that day's rate — every foreign amount
converted at its own date through the FX service, in one batched call — and every conversion it
could not make is reported with its pair and dates instead of becoming a silent zero.

Pure: no database, no server, no network. The module's only I/O is the FX service: ``convert_bulk``
for the movements' amounts and, since P3 («formule veloci»), ``unit_rate_steps`` for the unit rates,
asked as windows of days and answered as steps. Every test replaces both module attributes with
doubles on the same rates (``FakeFx``, ``FakeSteps``), so every figure is exact and every request is
observable. Where nothing needs converting both are one probe that records and fails, and the
session is ``None``: nothing may touch it. Values are compared through ``str()`` wherever the exponent is part of the contract:
an EUR-only history must come out byte-identical, so ``Decimal("950.00")`` is not
``Decimal("950")`` here.

The ``flows`` tests also carry the engine accumulator tests that step F-2 retired from the
builder (``test_portfolio_engine_vnext.py`` period accumulators, ``test_signed_income.py``):
the same histories and the same numbers, asked of the module instead.

Section 11 (``exchange_results`` and ``CONVERSION_DUST``) is red until step F-W. The constant
is read inside the tests as ``native_cash.CONVERSION_DUST`` and never imported at module level,
so before F-W those tests fail at run time with an AttributeError while every other test in
this file still collects and runs.

Section 12 (R13-SEC8-2) pins which days a currency's unit rate is asked on: every day from
``max(first movement, 1900-01-01)``, and before that floor only the foreign movements' own days, so a
balance counted before 1900 keeps a rate. The floor ``EARLIEST_RANGE_START`` is written as a literal
(the name is new). Since P3 those days are asked as windows — one ``(d, d)`` per movement day before
the floor, one window from ``max(first movement, floor)`` — and sections 3 and 12 assert the windows,
the very days asked one by one before.
"""

from __future__ import annotations

from bisect import bisect_right
from dataclasses import FrozenInstanceError, dataclass, field
from datetime import date
from decimal import Decimal
from types import SimpleNamespace

import pytest

from backend.app.db.models import Transaction, TransactionType, UserRole
from backend.app.schemas.common import Currency
from backend.app.services.financial_math import native_cash
from backend.app.services.financial_math.native_cash import (
    CashFlows,
    CashMovement,
    MissingCashConversion,
    NativeCash,
    cash_movement_from_transaction,
    compute_native_cash,
    effective_share,
)
from backend.app.services.fx.conversion import UnitRateSteps
from backend.test_scripts.test_utils import print_section, print_success

D0 = date(2025, 1, 1)
D1 = date(2025, 1, 2)
D2 = date(2025, 1, 3)
D3 = date(2025, 1, 4)
D4 = date(2025, 1, 5)
D5 = date(2025, 1, 6)
BEFORE_D0 = date(2024, 12, 31)

A = 10  # broker
B = 20  # broker
X = 100  # asset
Y = 200  # asset

_NOT_PASSED = object()


# =============================================================================
# convert_bulk doubles
# =============================================================================


@dataclass
class FakeFx:
    """``convert_bulk`` double: fixed directional rates, unlimited backward fill, every call recorded.

    ``rates[(from, to)][day]`` is the number of ``to`` units for one ``from`` unit from
    ``day`` on. Results are aligned with the input, as in the FX service:
    ``(Currency, rate_date, rate_date < requested_date)``, or ``None`` when no rate exists
    on or before the requested date.
    """

    rates: dict[tuple[str, str], dict[date, Decimal]] = field(default_factory=dict)
    calls: list[list[tuple[Currency, str, date]]] = field(default_factory=list)
    sessions: list[object] = field(default_factory=list)
    raise_on_error_args: list[object] = field(default_factory=list)
    #: The ``unit_rate_steps`` double installed with this one, on the same rates (``install_fx``).
    steps: FakeSteps | None = None

    async def __call__(self, session, conversions, raise_on_error=_NOT_PASSED):
        batch = list(conversions)
        self.sessions.append(session)
        self.raise_on_error_args.append(raise_on_error)
        self.calls.append(batch)
        results: list[tuple[Currency, date, bool] | None] = []
        errors: list[str] = []
        for index, (amount, to_currency, day) in enumerate(batch):
            series = self.rates.get((amount.code, to_currency), {})
            known = [rate_day for rate_day in series if rate_day <= day]
            if not known:
                results.append(None)
                errors.append(f"Conversion {index}: no {amount.code}/{to_currency} rate on or before {day}")
                continue
            rate_day = max(known)
            results.append((Currency(code=to_currency, amount=amount.amount * series[rate_day]), rate_day, rate_day < day))
        return results, errors

    @property
    def requests(self) -> set[tuple[str, Decimal, str, date]]:
        """Every ``(from, amount, to, date)`` requested, duplicates collapsed."""
        return {(amount.code, amount.amount, to_currency, day) for batch in self.calls for amount, to_currency, day in batch}

    @property
    def identity_requests(self) -> list[tuple[str, str, date]]:
        """Requests whose source and target currency coincide: the FX service is never asked for those."""
        return [(amount.code, to_currency, day) for batch in self.calls for amount, to_currency, day in batch if amount.code == to_currency]


@dataclass
class FakeSteps:
    """``unit_rate_steps`` double on the same rates as ``FakeFx`` (P3): one unit's steps on the windows asked, built as the
    FX service builds them — a step on each window's first day with the last rate on or before it (none before the
    first rate), and one on each rate day inside a window. So on every asked day ``at`` is what ``FakeFx`` answers for
    one unit, to the digit (``Decimal("1") * rate``). Every call recorded, the windows read once as lists; a pair of one
    currency, or a window that ends before it starts, raises ``ValueError`` as the FX service does.
    """

    rates: dict[tuple[str, str], dict[date, Decimal]] = field(default_factory=dict)
    calls: list[dict[tuple[str, str], list[tuple[date, date]]]] = field(default_factory=list)
    sessions: list[object] = field(default_factory=list)

    async def __call__(self, session, requests):
        asked = {pair: list(windows) for pair, windows in requests.items()}
        self.sessions.append(session)
        self.calls.append(asked)
        steps: dict[tuple[str, str], UnitRateSteps] = {}
        for (source, destination), windows in asked.items():
            if source == destination:
                raise ValueError(f"unit_rate_steps: {source}/{destination} is one currency, not a pair")
            series = self.rates.get((source, destination), {})
            rate_days = sorted(series)
            rows_by_day: dict[date, date] = {}
            for first, last in sorted(windows):
                if last < first:
                    raise ValueError(f"unit_rate_steps: the window {first} – {last} of {source}/{destination} ends before it starts")
                anchor = bisect_right(rate_days, first) - 1
                if anchor >= 0:
                    rows_by_day[first] = rate_days[anchor]
                for rate_day in rate_days[anchor + 1 : bisect_right(rate_days, last)]:
                    rows_by_day[rate_day] = rate_day
            days = tuple(sorted(rows_by_day))
            steps[(source, destination)] = UnitRateSteps(source=source, destination=destination, days=days, values=tuple(Decimal("1") * series[rows_by_day[day]] for day in days), rate_days=tuple(rows_by_day[day] for day in days))
        return steps


@dataclass
class ForbiddenFx:
    """Probe for histories where nothing needs converting: it records the call, then fails loudly.

    It stands for both doors of the FX service, ``convert_bulk`` and ``unit_rate_steps`` (P3). The record is what the
    tests assert on, so a caller that swallowed the exception would still be caught.
    """

    calls: list[tuple[tuple, dict]] = field(default_factory=list)

    async def __call__(self, *args, **kwargs):
        self.calls.append((args, kwargs))
        raise AssertionError("the FX service (convert_bulk, unit_rate_steps) must not be called: nothing in this history needs converting")


@pytest.fixture
def forbidden_fx(monkeypatch) -> ForbiddenFx:
    probe = ForbiddenFx()
    monkeypatch.setattr(native_cash, "convert_bulk", probe)
    monkeypatch.setattr(native_cash, "unit_rate_steps", probe)
    return probe


def install_fx(monkeypatch, rates: dict[tuple[str, str], dict[date, str]]) -> FakeFx:
    """``convert_bulk`` and ``unit_rate_steps`` replaced on the module by doubles on the same ``rates``; the steps double
    is ``fx.steps``."""
    fx = FakeFx(rates={pair: {day: Decimal(rate) for day, rate in series.items()} for pair, series in rates.items()})
    fx.steps = FakeSteps(rates=fx.rates)
    monkeypatch.setattr(native_cash, "convert_bulk", fx)
    monkeypatch.setattr(native_cash, "unit_rate_steps", fx.steps)
    return fx


# =============================================================================
# Builders and readers
# =============================================================================


def movement(
    day: date,
    currency: str,
    amount: str,
    *,
    broker_id: int = A,
    transaction_type: str = "DEPOSIT",
    asset_id: int | None = None,
    share: str = "1",
    movement_id: int | None = None,
) -> CashMovement:
    return CashMovement(
        movement_id=movement_id,
        transaction_type=transaction_type,
        date=day,
        broker_id=broker_id,
        asset_id=asset_id,
        currency=currency,
        amount=Decimal(amount),
        share=Decimal(share),
    )


def native_cash_of(*rows: CashMovement | tuple[CashMovement, str | None], unit_rates: dict[tuple[str, date], str] | None = None, report_currency: str = "EUR") -> NativeCash:
    """A ``NativeCash`` built directly, as ``compute_native_cash`` would return it.

    A bare movement is converted to its own amount (a report-currency or zero row); a
    ``(movement, value)`` row is converted to ``value``, ``None`` being a missing conversion.
    """
    movements: list[CashMovement] = []
    converted: list[Decimal | None] = []
    for row in rows:
        row_movement, value = (row, row.amount) if isinstance(row, CashMovement) else (row[0], None if row[1] is None else Decimal(row[1]))
        movements.append(row_movement)
        converted.append(value)
    return NativeCash(
        report_currency=report_currency,
        movements=tuple(movements),
        converted=tuple(converted),
        unit_rates={key: Decimal(rate) for key, rate in (unit_rates or {}).items()},
    )


def transaction(*, tx_id: int | None = 7, tx_type: object = TransactionType.DEPOSIT, day: date = D2, broker_id: int = B, asset_id: int | None = None, currency: str | None = "USD", amount: str | None = "100") -> SimpleNamespace:
    """A transaction as the module reads it: the attributes ``cash_movement_from_transaction`` may touch, nothing else."""
    return SimpleNamespace(id=tx_id, type=tx_type, date=day, broker_id=broker_id, asset_id=asset_id, currency=currency, amount=None if amount is None else Decimal(amount))


def orm_transaction(*, tx_id: int, tx_type: TransactionType, day: date, amount: str, broker_id: int = 1, asset_id: int | None = None, quantity: str = "0", currency: str = "EUR") -> Transaction:
    """A real ``Transaction`` row, built as ``test_portfolio_engine_vnext._tx`` builds it."""
    tx = Transaction()
    tx.id = tx_id
    tx.broker_id = broker_id
    tx.asset_id = asset_id
    tx.type = tx_type
    tx.date = day
    tx.quantity = Decimal(quantity)
    tx.amount = Decimal(amount)
    tx.currency = currency
    tx.cost_basis_override = None
    tx.cost_basis_currency = None
    tx.related_transaction_id = None
    tx.updated_at = day
    return tx


def _strs(values) -> list[str | None]:
    """``str()`` of every value, ``None`` kept: the exponent is part of what is compared."""
    return [None if value is None else str(value) for value in values]


def _str_dict(mapping) -> dict:
    """The mapping with its values as ``str()``, keys untouched."""
    return {key: str(value) for key, value in mapping.items()}


def _batch(fx: FakeFx, index: int = 0) -> list[tuple[str, str, str, date]]:
    """Call ``index`` of the double as ``(code, str(amount), to, day)`` in request order."""
    return [(amount.code, str(amount.amount), to_currency, day) for amount, to_currency, day in fx.calls[index]]


def _unit_windows(fx: FakeFx) -> dict[tuple[str, str], list[tuple[date, date]]]:
    """The windows of the one ``unit_rate_steps`` call, by pair (P3); fails unless there was exactly one."""
    assert fx.steps is not None and len(fx.steps.calls) == 1, f"one unit_rate_steps call expected, got {0 if fx.steps is None else len(fx.steps.calls)}"
    return fx.steps.calls[0]


def _window_days(windows: list[tuple[date, date]]) -> list[date]:
    """Every day of ``windows``, in window order: the days a request a day asked before P3."""
    return [date.fromordinal(ordinal) for first, last in windows for ordinal in range(first.toordinal(), last.toordinal() + 1)]


_FLOW_FIELDS = ("signed_by_type", "absolute_by_type", "income_by_position", "costs_by_position", "unallocated_income", "unallocated_costs")


def flows_as_strings(flows: CashFlows) -> dict[str, dict]:
    """Every ``CashFlows`` accumulator, values as ``str()``, keyed by field name."""
    return {name: _str_dict(getattr(flows, name)) for name in _FLOW_FIELDS}


def expected_flows(**fields: dict) -> dict[str, dict]:
    """The six accumulators as ``flows_as_strings`` returns them: empty unless given."""
    unknown = set(fields) - set(_FLOW_FIELDS)
    assert not unknown, f"not CashFlows fields: {sorted(unknown)}"
    return {name: fields.get(name, {}) for name in _FLOW_FIELDS}


# =============================================================================
# 1 — effective_share
# =============================================================================


class TestEffectiveShare:
    @pytest.mark.parametrize("role", [UserRole.OWNER, "OWNER"], ids=["enum", "str"])
    def test_owner_keeps_the_recorded_share_object(self, role):
        """An OWNER holds exactly the share on its access row: the very object, exponent and all — 0 included."""
        print_section(f"1 — effective_share: OWNER ({type(role).__name__}) keeps its share")
        half = Decimal("0.500000")
        zero = Decimal("0")

        assert effective_share(role, half) is half
        assert effective_share(role, zero) is zero, "a 0 share is the owner's share, not a missing one"
        print_success("OWNER: 0.500000 and 0 come back as the same objects")

    @pytest.mark.parametrize("role", [UserRole.OWNER, "OWNER"], ids=["enum", "str"])
    def test_owner_without_a_recorded_share_holds_everything(self, role):
        print_section(f"1 — effective_share: OWNER ({type(role).__name__}) without share")
        share = effective_share(role, None)

        assert share == Decimal("1")
        assert str(share) == "1"
        print_success("OWNER with no share: 1")

    @pytest.mark.parametrize("role", [UserRole.EDITOR, UserRole.VIEWER, "EDITOR", "VIEWER"], ids=["editor-enum", "viewer-enum", "editor-str", "viewer-str"])
    @pytest.mark.parametrize("recorded", ["0", "0.500000", None], ids=["zero", "half", "none"])
    def test_other_roles_see_the_whole_broker(self, role, recorded):
        """EDITOR and VIEWER do not own a part of the broker: whatever the row says, they see all of it."""
        print_section(f"1 — effective_share: {role} with {recorded}")
        share = effective_share(role, None if recorded is None else Decimal(recorded))

        assert str(share) == "1"
        print_success(f"{role}: 1")


# =============================================================================
# 2 — cash_movement_from_transaction and CashMovement
# =============================================================================


class TestCashMovementFromTransaction:
    def test_fields_are_mapped_from_the_transaction(self):
        print_section("2 — cash_movement_from_transaction: field mapping")
        tx = transaction(tx_id=7, tx_type=TransactionType.FEE, day=D2, broker_id=B, asset_id=X, currency="USD", amount="-400.00")

        result = cash_movement_from_transaction(tx, share=Decimal("0.500000"))

        assert result == CashMovement(
            movement_id=7,
            transaction_type="FEE",
            date=D2,
            broker_id=B,
            asset_id=X,
            currency="USD",
            amount=Decimal("-400.00"),
            share=Decimal("0.500000"),
        )
        assert type(result.transaction_type) is str, "the type is a plain string, not the ORM enum"
        assert (str(result.amount), str(result.share)) == ("-400.00", "0.500000"), "raw, signed, as stored — not times share"
        assert not hasattr(result, "__dict__"), "CashMovement is a slots dataclass"
        print_success("id, type, date, broker, asset, currency, amount and share carried over")

    def test_native_is_amount_times_share_exponent_included(self):
        """``native = amount * share``, nothing quantized: -400.00 (exponent -2) x 0.500000 (exponent -6, the Numeric(7, 6) share column) is -200.00000000 (exponent -8)."""
        print_section("2 — CashMovement.native: -400.00 x 0.500000")
        result = cash_movement_from_transaction(transaction(amount="-400.00"), share=Decimal("0.500000"))

        assert str(result.native) == "-200.00000000"
        print_success("native = -200.00000000")

    def test_default_share_is_one_and_keeps_the_amount_exponent(self):
        print_section("2 — CashMovement: default share")
        result = cash_movement_from_transaction(transaction(currency="EUR", amount="12.50"))

        assert str(result.share) == "1"
        assert str(result.native) == "12.50"
        print_success("share 1, native 12.50")

    def test_movement_is_frozen(self):
        print_section("2 — CashMovement: frozen")
        result = cash_movement_from_transaction(transaction())

        with pytest.raises(FrozenInstanceError):
            result.amount = Decimal("1")
        print_success("assignment refused")

    @pytest.mark.parametrize(("amount", "currency"), [(None, "EUR"), ("100", None), ("100", "")], ids=["amount-none", "currency-none", "currency-empty"])
    def test_transaction_without_cash_yields_no_movement(self, amount, currency):
        print_section(f"2 — cash_movement_from_transaction: amount={amount!r}, currency={currency!r}")

        assert cash_movement_from_transaction(transaction(amount=amount, currency=currency)) is None
        print_success("no movement")

    def test_zero_amount_is_kept(self):
        """A zero row is still a movement: only the valuation ignores it."""
        print_section("2 — cash_movement_from_transaction: zero amount")
        result = cash_movement_from_transaction(transaction(currency="USD", amount="0.00"))

        assert result is not None
        assert str(result.amount) == "0.00"
        print_success("0.00 kept, exponent and all")

    @pytest.mark.parametrize("tx_type", [TransactionType.DIVIDEND, "DIVIDEND"], ids=["enum", "str"])
    def test_type_becomes_the_plain_type_string(self, tx_type):
        print_section(f"2 — cash_movement_from_transaction: type as {type(tx_type).__name__}")
        result = cash_movement_from_transaction(transaction(tx_type=tx_type))

        assert result.transaction_type == "DIVIDEND"
        assert type(result.transaction_type) is str
        print_success("DIVIDEND")

    def test_transaction_without_id_yields_a_movement_without_id(self):
        print_section("2 — cash_movement_from_transaction: no id")

        assert cash_movement_from_transaction(transaction(tx_id=None)).movement_id is None
        print_success("movement_id None")

    def test_orm_transaction_is_accepted(self):
        print_section("2 — cash_movement_from_transaction: ORM row")
        tx = orm_transaction(tx_id=3, tx_type=TransactionType.WITHDRAWAL, day=D4, amount="-75.5", broker_id=A, currency="GBP")

        assert cash_movement_from_transaction(tx) == CashMovement(
            movement_id=3,
            transaction_type="WITHDRAWAL",
            date=D4,
            broker_id=A,
            asset_id=None,
            currency="GBP",
            amount=Decimal("-75.5"),
        )
        print_success("a Transaction row maps like any other")


# =============================================================================
# 3 — compute_native_cash: what is asked of the FX service, and in which order
# =============================================================================

_CONTRACT_RATES = {("USD", "EUR"): {D1: "0.90", D2: "0.92", D3: "0.95"}, ("GBP", "EUR"): {D2: "1.20"}}
_CONTRACT_AMOUNT_REQUESTS = [("USD", "500.00", "EUR", D1), ("GBP", "200", "EUR", D2), ("USD", "-100.0", "EUR", D3)]
_CONTRACT_CONVERTED = ["1000", "0.00", "450.0000", "240.00", "-95.000", "0"]


def _contract_movements() -> list[CashMovement]:
    """Report, zero and foreign rows interleaved: two brokers, two foreign currencies, one shared row."""
    return [
        movement(D0, "EUR", "1000"),
        movement(D0, "USD", "0.00", transaction_type="FEE"),
        movement(D1, "USD", "500.00", share="0.5"),
        movement(D2, "GBP", "200", broker_id=B),
        movement(D3, "USD", "-100.0", transaction_type="WITHDRAWAL"),
        movement(D4, "USD", "0", broker_id=B, transaction_type="INTEREST"),
    ]


class TestRequestContract:
    @pytest.mark.asyncio
    @pytest.mark.parametrize("rates_until", [None, D5], ids=["rates-until-none", "rates-until-d5"])
    async def test_report_currency_only_never_reaches_the_fx_service(self, forbidden_fx, rates_until):
        print_section(f"3 — report currency only, rates_until={rates_until}: no call")
        movements = [
            movement(D0, "EUR", "1000.00"),
            movement(D0, "EUR", "200.0", broker_id=B, share="0.500000"),
            movement(D1, "EUR", "-0.250", transaction_type="FEE"),
        ]

        result = await compute_native_cash(None, movements, report_currency="EUR", rates_until=rates_until)

        assert forbidden_fx.calls == []
        assert result.report_currency == "EUR"
        assert result.movements == tuple(movements)
        assert _strs(result.converted) == ["1000.00", "200.0", "-0.250"], "a report row converts to its raw amount, not times share"
        assert dict(result.unit_rates) == {}
        print_success("nothing requested, every amount kept as it is")

    @pytest.mark.asyncio
    async def test_no_movements_no_call(self, forbidden_fx):
        print_section("3 — no movements: no call")

        result = await compute_native_cash(None, [], report_currency="EUR")

        assert forbidden_fx.calls == []
        assert (result.movements, tuple(result.converted), dict(result.unit_rates)) == ((), (), {})
        print_success("empty in, empty out")

    @pytest.mark.asyncio
    @pytest.mark.parametrize("rates_until", [None, D5], ids=["rates-until-none", "rates-until-d5"])
    async def test_zero_foreign_rows_are_never_requested(self, forbidden_fx, rates_until):
        """A zero foreign row needs no rate: neither its amount nor its currency's unit rate is asked."""
        print_section(f"3 — zero foreign rows only, rates_until={rates_until}: no call")
        movements = [
            movement(D0, "EUR", "100"),
            movement(D0, "USD", "0.00", transaction_type="FEE"),
            movement(D1, "GBP", "0", broker_id=B, transaction_type="INTEREST"),
        ]

        result = await compute_native_cash(None, movements, report_currency="EUR", rates_until=rates_until)

        assert forbidden_fx.calls == []
        assert _strs(result.converted) == ["100", "0.00", "0"]
        assert dict(result.unit_rates) == {}
        print_success("zero rows keep their own amount, no unit rate asked")

    @pytest.mark.asyncio
    async def test_one_call_for_the_amounts_then_one_for_the_unit_windows(self, monkeypatch):
        """Raw amounts in movement order to ``convert_bulk``; then one ``unit_rate_steps`` call with each currency's window
        from its first to its last non-zero day (P3: before it, the same days were unit requests of the same call)."""
        print_section("3 — one call for the amounts, one for the unit windows")
        fx = install_fx(monkeypatch, _CONTRACT_RATES)
        session = object()

        result = await compute_native_cash(session, _contract_movements(), report_currency="EUR")

        assert len(fx.calls) == 1, f"one batched convert_bulk call expected, got {len(fx.calls)}"
        assert fx.sessions[0] is session
        assert fx.raise_on_error_args[0] is False
        assert fx.identity_requests == []
        assert _batch(fx) == _CONTRACT_AMOUNT_REQUESTS, "convert_bulk converts the amounts only: the unit rates are asked as windows"
        windows = _unit_windows(fx)
        assert fx.steps.sessions[0] is session
        assert windows == {("GBP", "EUR"): [(D2, D2)], ("USD", "EUR"): [(D1, D3)]}
        assert {pair: _window_days(asked) for pair, asked in windows.items()} == {("GBP", "EUR"): [D2], ("USD", "EUR"): [D1, D2, D3]}, "the days the unit requests asked"
        assert _strs(result.converted) == _CONTRACT_CONVERTED, "aligned with the movements; 500.00 is converted whole, the share is not applied"
        assert _str_dict(result.unit_rates) == {("GBP", D2): "1.20", ("USD", D1): "0.90", ("USD", D2): "0.92", ("USD", D3): "0.95"}
        print_success("3 amount requests in one call, 2 unit windows in another, raise_on_error=False")

    @pytest.mark.asyncio
    async def test_rates_until_extends_every_unit_range(self, monkeypatch):
        print_section("3 — rates_until after the last movement")
        fx = install_fx(monkeypatch, _CONTRACT_RATES)

        result = await compute_native_cash(object(), _contract_movements(), report_currency="EUR", rates_until=D4)

        assert len(fx.calls) == 1
        assert _batch(fx) == _CONTRACT_AMOUNT_REQUESTS
        windows = _unit_windows(fx)
        assert windows == {("GBP", "EUR"): [(D2, D4)], ("USD", "EUR"): [(D1, D4)]}
        assert {pair: _window_days(asked) for pair, asked in windows.items()} == {("GBP", "EUR"): [D2, D3, D4], ("USD", "EUR"): [D1, D2, D3, D4]}
        assert _strs(result.converted) == _CONTRACT_CONVERTED
        assert _str_dict(result.unit_rates) == {
            ("GBP", D2): "1.20",
            ("GBP", D3): "1.20",
            ("GBP", D4): "1.20",
            ("USD", D1): "0.90",
            ("USD", D2): "0.92",
            ("USD", D3): "0.95",
            ("USD", D4): "0.95",
        }, "every answered day is a unit rate, as the service answered it"
        print_success("unit windows run through D4 for both currencies")

    @pytest.mark.asyncio
    async def test_rates_until_before_a_currency_starts_asks_no_unit_rate_for_it(self, monkeypatch):
        print_section("3 — rates_until inside the history")
        fx = install_fx(monkeypatch, _CONTRACT_RATES)

        result = await compute_native_cash(object(), _contract_movements(), report_currency="EUR", rates_until=D1)

        assert len(fx.calls) == 1
        assert _batch(fx) == _CONTRACT_AMOUNT_REQUESTS, "amounts are all asked"
        assert _unit_windows(fx) == {("USD", "EUR"): [(D1, D1)]}, "GBP starts on D2, after D1: no window for it (D2 – D1 would end before it starts)"
        assert _strs(result.converted) == _CONTRACT_CONVERTED
        assert _str_dict(result.unit_rates) == {("USD", D1): "0.90"}
        print_success("USD unit rate on D1 only, no GBP window")

    @pytest.mark.asyncio
    async def test_failed_conversion_is_none_and_reported_missing(self, monkeypatch):
        print_section("3 — a conversion the service cannot make")
        fx = install_fx(monkeypatch, {("USD", "EUR"): {D2: "0.90"}})
        movements = [movement(D0, "EUR", "1000"), movement(D1, "USD", "100"), movement(D2, "USD", "50")]

        result = await compute_native_cash(object(), movements, report_currency="EUR")

        assert len(fx.calls) == 1
        assert _batch(fx) == [("USD", "100", "EUR", D1), ("USD", "50", "EUR", D2)]
        assert _unit_windows(fx) == {("USD", "EUR"): [(D1, D2)]}, "the unit days D1 and D2"
        assert _strs(result.converted) == ["1000", None, "45.00"], "no rate is None, never a zero"
        assert _str_dict(result.unit_rates) == {("USD", D2): "0.90"}, "an unanswered day has no unit rate"
        assert result.missing_conversions() == [MissingCashConversion(pair="USD/EUR", dates=(D1,))]
        print_success("USD 100 on D1 unconverted and reported")


# =============================================================================
# 4 — NativeCash construction
# =============================================================================


class TestConstruction:
    @pytest.mark.parametrize("converted", [(), (Decimal("1"), Decimal("2"))], ids=["shorter", "longer"])
    def test_converted_must_align_with_movements(self, converted):
        print_section(f"4 — {len(converted)} converted values for 1 movement")

        with pytest.raises(ValueError):
            NativeCash(report_currency="EUR", movements=(movement(D0, "EUR", "1"),), converted=converted, unit_rates={})
        print_success("ValueError")


# =============================================================================
# 5 — value_at
# =============================================================================


class TestValueAt:
    def test_report_currency_rows_keep_every_exponent(self):
        print_section("5 — value_at: report-currency rows, exponents")
        cash = native_cash_of(
            movement(D0, "EUR", "1000.00"),
            movement(D0, "EUR", "200.0", broker_id=B, share="0.500000"),
            movement(D1, "EUR", "-0.250", transaction_type="FEE"),
            movement(D1, "EUR", "0.0000", transaction_type="INTEREST"),
        )

        assert _str_dict(cash.value_at(D0)) == {A: "1000.00", B: "100.0000000"}
        assert _str_dict(cash.value_at(D1)) == {A: "999.750", B: "100.0000000"}, "a zero row is never counted: its exponent stays out"
        print_success("A 1000.00 then 999.750, B 100.0000000")

    def test_broker_whose_counted_rows_net_to_zero_is_still_a_key(self):
        print_section("5 — value_at: net zero")
        cash = native_cash_of(movement(D0, "EUR", "100"), movement(D1, "EUR", "-100", transaction_type="WITHDRAWAL"))

        assert cash.value_at(D0) == {A: Decimal("100")}
        assert cash.value_at(D1) == {A: Decimal("0")}
        print_success("A present with 0")

    def test_latest_unit_rate_on_or_before_the_day_is_carried_forward(self):
        print_section("5 — value_at: carry-forward of the latest rate")
        cash = native_cash_of((movement(D0, "USD", "1000"), "900.00"), unit_rates={("USD", D0): "0.90", ("USD", D2): "0.95"})

        assert [str(cash.value_at(day)[A]) for day in (D0, D1, D2, D4)] == ["900.00", "900.00", "950.00", "950.00"]
        print_success("USD 1000 is worth 900.00 until D2, 950.00 from D2")

    def test_zero_foreign_balance_needs_no_rate(self):
        print_section("5 — value_at: a foreign balance back to zero")
        cash = native_cash_of(
            (movement(D1, "USD", "100", broker_id=B), "90"),
            (movement(D2, "USD", "-100.00", broker_id=B, transaction_type="WITHDRAWAL"), "-95.0000"),
        )

        assert cash.value_at(D2) == {B: Decimal("0")}
        print_success("B 0 without any unit rate")

    def test_non_zero_foreign_balance_without_any_rate_is_refused(self):
        print_section("5 — value_at: a foreign balance with no rate")
        cash = native_cash_of((movement(D1, "USD", "100", broker_id=B), "90"))

        with pytest.raises(ValueError):
            cash.value_at(D1)
        print_success("ValueError, not a zero")

    def test_missing_rows_are_not_valued(self):
        print_section("5 — value_at: missing rows excluded")
        cash = native_cash_of(
            (movement(D0, "USD", "1000"), "900.00"),
            (movement(D1, "USD", "500"), None),
            (movement(D1, "USD", "300", broker_id=B), None),
            unit_rates={("USD", D0): "0.90", ("USD", D2): "0.95"},
        )

        assert _str_dict(cash.value_at(D1)) == {A: "900.00"}, "B has nothing counted: no key"
        assert _str_dict(cash.value_at(D2)) == {A: "950.00"}
        print_success("only the converted USD 1000 is valued")

    def test_share_applies_to_every_currency(self):
        print_section("5 — value_at: share")
        cash = native_cash_of(
            movement(D0, "EUR", "100", share="0.5"),
            (movement(D0, "USD", "1000", share="0.5"), "1050.00"),
            unit_rates={("USD", D0): "1.05"},
        )

        assert _str_dict(cash.value_at(D0)) == {A: "575.000"}, "50.0 + 500.0 x 1.05"
        print_success("575.000")

    def test_before_the_first_movement_there_is_nothing(self):
        print_section("5 — value_at: before the first movement")
        cash = native_cash_of(movement(D0, "EUR", "100"), (movement(D0, "USD", "10", broker_id=B), "9.0"), unit_rates={("USD", D0): "0.90"})

        assert cash.value_at(BEFORE_D0) == {}
        print_success("{}")

    def test_mixed_currencies_at_one_broker(self):
        print_section("5 — value_at: EUR, USD and GBP at one broker")
        cash = native_cash_of(
            movement(D0, "EUR", "100"),
            (movement(D0, "USD", "1000"), "900.00"),
            (movement(D0, "GBP", "200"), "240.00"),
            movement(D0, "EUR", "5", broker_id=B),
            unit_rates={("USD", D0): "0.90", ("USD", D1): "0.95", ("GBP", D0): "1.20", ("GBP", D1): "1.10"},
        )

        assert _str_dict(cash.value_at(D0)) == {A: "1240.00", B: "5"}
        assert _str_dict(cash.value_at(D1)) == {A: "1270.00", B: "5"}, "100 + 1000 x 0.95 + 200 x 1.10"
        print_success("A 1240.00 then 1270.00, B 5")


# =============================================================================
# 6 — foreign_cash_broker_ids
# =============================================================================


class TestForeignCashBrokerIds:
    def test_only_brokers_with_a_counted_foreign_row(self):
        print_section("6 — foreign_cash_broker_ids")
        eur_only, usd, zero_usd, missing_usd, eur_and_gbp = 10, 20, 30, 40, 50
        cash = native_cash_of(
            movement(D0, "EUR", "100", broker_id=eur_only),
            (movement(D0, "USD", "100", broker_id=usd), "90"),
            movement(D0, "USD", "0.00", broker_id=zero_usd),
            (movement(D0, "USD", "100", broker_id=missing_usd), None),
            movement(D0, "EUR", "100", broker_id=eur_and_gbp),
            (movement(D1, "GBP", "10", broker_id=eur_and_gbp), "12.0"),
            unit_rates={("USD", D0): "0.90", ("GBP", D1): "1.20"},
        )

        assert cash.foreign_cash_broker_ids == frozenset({usd, eur_and_gbp})
        assert type(cash.foreign_cash_broker_ids) is frozenset
        print_success("the USD broker and the EUR+GBP broker; zero and missing rows do not count")

    def test_report_currency_only_has_none(self):
        print_section("6 — foreign_cash_broker_ids: report currency only")
        cash = native_cash_of(movement(D0, "EUR", "100"), movement(D1, "EUR", "50", broker_id=B))

        assert cash.foreign_cash_broker_ids == frozenset()
        print_success("frozenset()")


# =============================================================================
# 7 — rate_change_days
# =============================================================================

_DENSE_USD = {("USD", D0): "0.90", ("USD", D1): "0.90", ("USD", D2): "0.95", ("USD", D3): "0.95", ("USD", D4): "1.00", ("USD", D5): "1.00"}


class TestRateChangeDays:
    @pytest.mark.parametrize(
        ("date_from", "date_to", "expected"),
        [
            (None, D5, (D0, D2, D4)),
            (D0, D5, (D0, D2, D4)),
            (D1, D5, (D2, D4)),
            (D2, D5, (D2, D4)),
            (D3, D3, ()),
            (D4, D4, (D4,)),
            (None, D2, (D0, D2)),
            (None, D1, (D0,)),
        ],
        ids=["unbounded", "from-first-day", "from-unchanged-day", "from-change-day", "unchanged-day-alone", "change-day-alone", "to-change-day", "to-unchanged-day"],
    )
    def test_first_rate_day_and_every_change_inside_the_window(self, date_from, date_to, expected):
        """A change ON ``date_from`` counts, judged against the rate day before it."""
        print_section(f"7 — rate_change_days({date_from}, {date_to})")
        cash = native_cash_of((movement(D0, "USD", "1000"), "900.00"), unit_rates=_DENSE_USD)

        assert cash.rate_change_days(date_from, date_to) == expected
        print_success(f"{expected}")

    @pytest.mark.parametrize(("later_rate", "expected"), [("0.95", (D0, D3)), ("0.90", (D0,))], ids=["changed", "unchanged"])
    def test_a_gap_is_judged_against_the_previous_rate_day(self, later_rate, expected):
        print_section(f"7 — rate_change_days: 0.90 on D0, {later_rate} on D3")
        cash = native_cash_of((movement(D0, "USD", "1000"), "900.00"), unit_rates={("USD", D0): "0.90", ("USD", D3): later_rate})

        assert cash.rate_change_days(None, D5) == expected
        print_success(f"{expected}")

    def test_change_days_of_every_currency_are_merged(self):
        print_section("7 — rate_change_days: USD and GBP")
        cash = native_cash_of(
            (movement(D0, "USD", "1000"), "900.00"),
            (movement(D1, "GBP", "100", broker_id=B), "120.00"),
            unit_rates={
                ("USD", D0): "0.90",
                ("USD", D1): "0.90",
                ("USD", D2): "0.95",
                ("USD", D3): "0.95",
                ("GBP", D1): "1.20",
                ("GBP", D2): "1.25",
                ("GBP", D3): "1.25",
            },
        )

        assert cash.rate_change_days(None, D5) == (D0, D1, D2), "USD {D0, D2} and GBP {D1, D2}, sorted, unique"
        print_success("(D0, D1, D2)")

    def test_currency_without_a_counted_row_has_no_change_day(self):
        print_section("7 — rate_change_days: zero-only, missing-only, report-only")
        zero_only = native_cash_of(movement(D0, "EUR", "100"), movement(D1, "USD", "0.00"), unit_rates={("USD", D1): "0.90", ("USD", D2): "0.95"})
        missing_only = native_cash_of(movement(D0, "EUR", "100"), (movement(D1, "GBP", "10"), None), unit_rates={("GBP", D2): "1.20", ("GBP", D3): "1.25"})
        report_only = native_cash_of(movement(D0, "EUR", "100"))

        assert zero_only.rate_change_days(None, D5) == ()
        assert missing_only.rate_change_days(None, D5) == ()
        assert report_only.rate_change_days(None, D5) == ()
        print_success("no cash to revalue, no change day")

    def test_a_counted_row_after_the_window_still_brings_its_currency(self):
        """The currency qualifies by a counted row at any date, not only inside the window."""
        print_section("7 — rate_change_days: counted row after date_to")
        cash = native_cash_of(
            movement(D0, "EUR", "100"),
            (movement(D2, "USD", "50"), None),
            (movement(D4, "USD", "100"), "95.00"),
            unit_rates={("USD", D3): "0.95", ("USD", D4): "0.95"},
        )

        assert cash.rate_change_days(None, D3) == (D3,)
        print_success("(D3,)")


# =============================================================================
# 8 — balances
# =============================================================================


def _balances_cash() -> NativeCash:
    """B appears first; A holds a missing USD row, a zero USD row with a longer exponent, and EUR."""
    return native_cash_of(
        (movement(D0, "GBP", "10", broker_id=B, share="0.5"), "12.00"),
        (movement(D0, "USD", "1000.000"), None),
        movement(D0, "EUR", "50"),
        movement(D1, "USD", "0.0000", transaction_type="FEE"),
        (movement(D1, "GBP", "5", broker_id=B, share="0.5", transaction_type="INTEREST"), "6.00"),
    )


def _str_balances(balances: dict[int, dict[str, Decimal]]) -> dict[int, dict[str, str]]:
    return {broker_id: _str_dict(by_currency) for broker_id, by_currency in balances.items()}


class TestBalances:
    def test_every_row_counts_in_first_appearance_order(self):
        """Native balances, not values: zero and missing rows are cash all the same."""
        print_section("8 — balances(): zero and missing rows included")
        result = _balances_cash().balances()

        assert _str_balances(result) == {B: {"GBP": "7.5"}, A: {"USD": "1000.0000", "EUR": "50"}}
        assert list(result) == [B, A], "brokers in first-appearance order"
        assert list(result[A]) == ["USD", "EUR"], "currencies in first-appearance order"
        print_success("B GBP 7.5; A USD 1000.0000 (missing and zero rows in), EUR 50")

    def test_as_of_keeps_the_rows_dated_up_to_it(self):
        print_section("8 — balances(as_of)")
        cash = _balances_cash()

        assert _str_balances(cash.balances(D0)) == {B: {"GBP": "5.0"}, A: {"USD": "1000.000", "EUR": "50"}}
        assert cash.balances(BEFORE_D0) == {}
        print_success("D0: B GBP 5.0, A USD 1000.000, EUR 50; before D0: {}")


# =============================================================================
# 9 — flows
# =============================================================================


def _flows_cash() -> NativeCash:
    """Income and costs on a position and on the broker, a shared row, a zero row, a missing row."""
    return native_cash_of(
        movement(D0, "EUR", "1000"),
        movement(D1, "EUR", "12.50", transaction_type="DIVIDEND", asset_id=X),
        (movement(D1, "USD", "-10", transaction_type="DIVIDEND", asset_id=X), "-9.00"),
        movement(D2, "EUR", "3", transaction_type="INTEREST"),
        movement(D2, "EUR", "-2.5", transaction_type="FEE", asset_id=X),
        movement(D2, "EUR", "-1.25", transaction_type="TAX"),
        (movement(D3, "USD", "-4", broker_id=B, transaction_type="FEE", asset_id=Y, share="0.5"), "-3.80"),
        movement(D3, "USD", "0.00", broker_id=B, transaction_type="INTEREST"),
        (movement(D3, "USD", "7", broker_id=B, transaction_type="DIVIDEND", asset_id=Y), None),
        movement(D4, "EUR", "-100", transaction_type="WITHDRAWAL"),
        unit_rates={("USD", D1): "0.90", ("USD", D2): "0.92", ("USD", D3): "0.95", ("USD", D4): "0.95"},
    )


class TestFlows:
    def test_whole_history_by_type_and_by_position(self):
        """Signed income nets a correction; costs are absolute; the missing dividend is nowhere; the zero interest is kept."""
        print_section("9 — flows(): whole history")
        result = _flows_cash().flows()

        assert isinstance(result, CashFlows)
        assert flows_as_strings(result) == expected_flows(
            signed_by_type={"DEPOSIT": "1000", "DIVIDEND": "3.50", "INTEREST": "3.00", "FEE": "-4.400", "TAX": "-1.25", "WITHDRAWAL": "-100"},
            absolute_by_type={"DEPOSIT": "1000", "DIVIDEND": "21.50", "INTEREST": "3.00", "FEE": "4.400", "TAX": "1.25", "WITHDRAWAL": "100"},
            income_by_position={(A, X): "3.50"},
            costs_by_position={(A, X): "2.5", (B, Y): "1.900"},
            unallocated_income={A: "3", B: "0.00"},
            unallocated_costs={A: "1.25"},
        )
        assert [type(getattr(result, name)) for name in _FLOW_FIELDS] == [dict] * len(_FLOW_FIELDS), "plain dicts"
        print_success("by type, by position and unallocated, exponents kept")

    @pytest.mark.parametrize(
        ("date_from", "date_to", "expected"),
        [
            (
                D1,
                D3,
                expected_flows(
                    signed_by_type={"INTEREST": "3.00", "FEE": "-4.400", "TAX": "-1.25"},
                    absolute_by_type={"INTEREST": "3.00", "FEE": "4.400", "TAX": "1.25"},
                    costs_by_position={(A, X): "2.5", (B, Y): "1.900"},
                    unallocated_income={A: "3", B: "0.00"},
                    unallocated_costs={A: "1.25"},
                ),
            ),
            (
                None,
                D1,
                expected_flows(
                    signed_by_type={"DEPOSIT": "1000", "DIVIDEND": "3.50"},
                    absolute_by_type={"DEPOSIT": "1000", "DIVIDEND": "21.50"},
                    income_by_position={(A, X): "3.50"},
                ),
            ),
            (D3, None, expected_flows(signed_by_type={"WITHDRAWAL": "-100"}, absolute_by_type={"WITHDRAWAL": "100"})),
            (D0, D0, expected_flows()),
        ],
        ids=["d1-to-d3", "up-to-d1", "after-d3", "empty-window"],
    )
    def test_window_excludes_its_first_day_and_includes_its_last(self, date_from, date_to, expected):
        print_section(f"9 — flows({date_from}, {date_to})")

        assert flows_as_strings(_flows_cash().flows(date_from, date_to)) == expected
        print_success("window (from, to]")


async def _eur_native_cash(transactions) -> NativeCash:
    """What the engine builds from an EUR-only history: every transaction a movement, nothing to convert."""
    return await compute_native_cash(None, [cash_movement_from_transaction(tx) for tx in transactions], report_currency="EUR")


def _signed_income_tx(tx_id: int, day: str, tx_type: str, amount: str, *, asset_id: int | None = None) -> SimpleNamespace:
    """A transaction as ``test_signed_income._tx`` builds it: broker 10, EUR."""
    return transaction(tx_id=tx_id, tx_type=TransactionType(tx_type), day=date.fromisoformat(day), broker_id=10, asset_id=asset_id, currency="EUR", amount=amount)


class TestFlowsPortedFromTheEngine:
    """The engine accumulator tests that F-2 retired from the builder, asked of the module: same histories, same numbers.

    A builder run ``[date_from, date_to]`` is the flows window ``(date_from - 1 day, date_to]``.
    """

    @pytest.mark.asyncio
    async def test_vnext_dividend_on_a_position_is_position_income(self, forbidden_fx):
        """Port of the former ``test_portfolio_engine_vnext.py`` ``test_income_attributed`` (frame 2025-01-01..10)."""
        print_section("9 — port: vnext DIVIDEND on asset 1 -> position income")
        cash = await _eur_native_cash(
            [
                orm_transaction(tx_id=1, tx_type=TransactionType.DEPOSIT, day=date(2025, 1, 2), amount="1000"),
                orm_transaction(tx_id=2, tx_type=TransactionType.DIVIDEND, day=date(2025, 1, 5), amount="50", asset_id=1),
            ]
        )

        assert cash.flows(date(2024, 12, 31), date(2025, 1, 10)).income_by_position[(1, 1)] == Decimal("50")
        assert forbidden_fx.calls == []
        print_success("income_by_position[(1, 1)] == 50")

    @pytest.mark.asyncio
    async def test_vnext_fee_without_asset_is_an_unallocated_cost(self, forbidden_fx):
        """Port of the former ``test_portfolio_engine_vnext.py`` ``test_unallocated_fees`` (frame 2025-01-01..10)."""
        print_section("9 — port: vnext FEE without asset -> unallocated cost")
        cash = await _eur_native_cash(
            [
                orm_transaction(tx_id=1, tx_type=TransactionType.DEPOSIT, day=date(2025, 1, 2), amount="1000"),
                orm_transaction(tx_id=2, tx_type=TransactionType.FEE, day=date(2025, 1, 5), amount="-10"),
            ]
        )

        assert cash.flows(date(2024, 12, 31), date(2025, 1, 10)).unallocated_costs[1] == Decimal("10")
        assert forbidden_fx.calls == []
        print_success("unallocated_costs[1] == 10")

    @pytest.mark.asyncio
    async def test_signed_income_negative_interest_stays_signed_and_unallocated(self, forbidden_fx):
        """Port of ``test_signed_income.py`` ``test_day2_negative_interest_correction`` (frame 2025-01-01..02)."""
        print_section("9 — port: negative INTEREST correction")
        cash = await _eur_native_cash([_signed_income_tx(1, "2025-01-01", "DEPOSIT", "1000"), _signed_income_tx(2, "2025-01-02", "INTEREST", "-50")])

        flows = cash.flows(date(2024, 12, 31), date(2025, 1, 2))

        assert flows.unallocated_income == {10: Decimal("-50")}
        assert flows.income_by_position == {}
        assert forbidden_fx.calls == []
        print_success("unallocated_income {10: -50}, no position income")

    @pytest.mark.asyncio
    async def test_signed_income_pure_positive_history(self, forbidden_fx):
        """Port of ``test_signed_income.py`` ``test_deposit_buy_dividend_interest_all_positive`` (frame 2025-01-01)."""
        print_section("9 — port: DEPOSIT, BUY, DIVIDEND, INTEREST all positive")
        cash = await _eur_native_cash(
            [
                _signed_income_tx(1, "2025-01-01", "DEPOSIT", "1000"),
                _signed_income_tx(2, "2025-01-01", "BUY", "-500", asset_id=100),
                _signed_income_tx(3, "2025-01-01", "DIVIDEND", "80", asset_id=100),
                _signed_income_tx(4, "2025-01-01", "INTEREST", "20"),
            ]
        )

        flows = cash.flows(date(2024, 12, 31), date(2025, 1, 1))

        assert flows.income_by_position == {(10, 100): Decimal("80")}, "keyed (broker_id, asset_id)"
        assert flows.unallocated_income == {10: Decimal("20")}
        assert forbidden_fx.calls == []
        print_success("income_by_position {(10, 100): 80}, unallocated_income {10: 20}")

    @pytest.mark.asyncio
    async def test_signed_income_correction_before_the_window_is_not_a_flow_of_it(self, forbidden_fx):
        """Port of ``test_signed_income.py`` ``test_negative_correction_before_date_from_carries_into_the_first_state`` (states 2025-01-05..06)."""
        print_section("9 — port: correction before the window")
        cash = await _eur_native_cash([_signed_income_tx(1, "2025-01-01", "DEPOSIT", "1000"), _signed_income_tx(2, "2025-01-02", "DIVIDEND", "-30")])

        assert flows_as_strings(cash.flows(date(2025, 1, 4), date(2025, 1, 6))) == expected_flows()
        assert forbidden_fx.calls == []
        print_success("every accumulator empty")


# =============================================================================
# 10 — sums_by_date and missing_conversions
# =============================================================================


def _sums_cash() -> NativeCash:
    """Deliberately out of date order, so the ascending output is the module's doing, not the input's."""
    return native_cash_of(
        movement(D2, "EUR", "3", transaction_type="INTEREST"),
        movement(D1, "EUR", "100"),
        (movement(D1, "USD", "10", share="0.5"), "9.00"),
        movement(D3, "EUR", "-1.5", transaction_type="FEE"),
        movement(D1, "EUR", "0.0000"),
        (movement(D2, "USD", "7", broker_id=B, transaction_type="DIVIDEND", asset_id=Y), None),
        movement(D3, "USD", "0", broker_id=B, transaction_type="DIVIDEND"),
        movement(D4, "EUR", "-20", transaction_type="WITHDRAWAL"),
        movement(D0, "EUR", "1"),
        unit_rates={("USD", D1): "0.90", ("USD", D2): "0.92", ("USD", D3): "0.95"},
    )


def _str_sums(sums: dict[date, dict[str, Decimal]]) -> dict[date, dict[str, str]]:
    return {day: _str_dict(by_type) for day, by_type in sums.items()}


class TestSumsByDate:
    def test_window_sums_by_day_and_type_skipping_zero_and_missing_rows(self):
        """D1 is 100 + 9.00 x 0.5 without the 0.0000 row; the missing D2 dividend and the zero D3 dividend leave no key."""
        print_section("10 — sums_by_date(D0, D3)")
        result = _sums_cash().sums_by_date(D0, D3)

        assert _str_sums(result) == {D1: {"DEPOSIT": "104.500"}, D2: {"INTEREST": "3"}, D3: {"FEE": "-1.5"}}
        assert list(result) == [D1, D2, D3], "ascending dates"
        print_success("D1 DEPOSIT 104.500, D2 INTEREST 3, D3 FEE -1.5")

    @pytest.mark.parametrize(
        ("date_from", "date_to", "transaction_types", "expected"),
        [
            (None, D1, None, {D0: {"DEPOSIT": "1"}, D1: {"DEPOSIT": "104.500"}}),
            (D3, None, None, {D4: {"WITHDRAWAL": "-20"}}),
            (None, None, ("DEPOSIT", "WITHDRAWAL"), {D0: {"DEPOSIT": "1"}, D1: {"DEPOSIT": "104.500"}, D4: {"WITHDRAWAL": "-20"}}),
            (None, None, {"FEE"}, {D3: {"FEE": "-1.5"}}),
            (None, None, ["DIVIDEND"], {}),
        ],
        ids=["up-to-d1", "after-d3", "deposits-and-withdrawals", "fees", "dividends-none-counted"],
    )
    def test_bounds_and_type_filter(self, date_from, date_to, transaction_types, expected):
        print_section(f"10 — sums_by_date({date_from}, {date_to}, transaction_types={transaction_types})")
        result = _sums_cash().sums_by_date(date_from, date_to, transaction_types=transaction_types)

        assert _str_sums(result) == expected
        assert list(result) == sorted(expected), "ascending dates"
        print_success(f"{len(expected)} day(s)")


def _missing_cash() -> NativeCash:
    """Missing rows of two currencies at two brokers, out of date order, among counted, zero and report rows."""
    return native_cash_of(
        (movement(D3, "USD", "5", transaction_type="DIVIDEND", asset_id=X), None),
        (movement(D1, "USD", "100"), None),
        (movement(D1, "USD", "200"), None),
        (movement(D2, "GBP", "-3", broker_id=B, transaction_type="FEE", asset_id=Y), None),
        movement(D2, "USD", "0", transaction_type="INTEREST"),
        movement(D0, "EUR", "1000"),
        (movement(D2, "USD", "50"), "45.00"),
        (movement(D4, "GBP", "10", broker_id=B), None),
        unit_rates={("USD", D2): "0.90"},
    )


class TestMissingConversions:
    @pytest.mark.parametrize(
        ("kwargs", "expected"),
        [
            ({}, [("GBP/EUR", (D2, D4)), ("USD/EUR", (D1, D3))]),
            ({"date_from": D1, "date_to": D3}, [("GBP/EUR", (D2,)), ("USD/EUR", (D3,))]),
            ({"date_to": D1}, [("USD/EUR", (D1,))]),
            ({"transaction_types": ["DEPOSIT"]}, [("GBP/EUR", (D4,)), ("USD/EUR", (D1,))]),
            ({"transaction_types": {"FEE", "DIVIDEND"}}, [("GBP/EUR", (D2,)), ("USD/EUR", (D3,))]),
            ({"date_from": D4}, []),
        ],
        ids=["whole-history", "d1-to-d3", "up-to-d1", "deposits", "fees-and-dividends", "after-the-last-row"],
    )
    def test_grouped_by_pair_with_sorted_unique_dates(self, kwargs, expected):
        """Pairs sorted by name, dates ascending and unique; a pair with nothing in the window is omitted."""
        print_section(f"10 — missing_conversions({kwargs})")
        result = _missing_cash().missing_conversions(**kwargs)

        assert result == [MissingCashConversion(pair=pair, dates=dates) for pair, dates in expected]
        print_success(f"{[conversion.pair for conversion in result]}")

    def test_nothing_missing_is_an_empty_list(self):
        """Zero foreign rows are never requested, hence never missing."""
        print_section("10 — missing_conversions: nothing missing")
        cash = native_cash_of(movement(D0, "EUR", "1000"), (movement(D1, "USD", "100"), "90.00"), movement(D2, "USD", "0"), unit_rates={("USD", D1): "0.90"})

        assert cash.missing_conversions() == []
        print_success("[]")


# =============================================================================
# 11 — exchange_results and CONVERSION_DUST
# =============================================================================

C = 30  # broker
G = 40  # broker

_DAY_NAMES = {D0: "d0", D1: "d1", D2: "d2", D3: "d3", D4: "d4"}

_EXCHANGE_UNIT_RATES = {("USD", D1): "0.8", ("USD", D2): "0.7", ("USD", D3): "0.625"}

# (date_from, date_to, broker A's result with the base rows at share 1)
_EXCHANGE_WINDOWS = [
    (None, D3, "-212.5"),
    (D0, D3, "-212.5"),
    (D1, D3, "-212.5"),
    (D1, D2, "-100"),
    (D2, D3, "-112.5"),
    (None, D1, "0"),
]
_EXCHANGE_WINDOW_IDS = ["none-to-d3", "d0-to-d3", "d1-to-d3", "d1-to-d2", "d2-to-d3", "none-to-d1"]

_PROPERTY_WINDOWS = [(date_from, date_to) for date_from in [None, D0, D1, D2, D3, D4] for date_to in [D0, D1, D2, D3, D4] if date_from is None or date_from < date_to]
_PROPERTY_WINDOW_IDS = [f"{'none' if date_from is None else _DAY_NAMES[date_from]}-to-{_DAY_NAMES[date_to]}" for date_from, date_to in _PROPERTY_WINDOWS]


def _exchange_rows(share: str = "1") -> list[tuple[CashMovement, str]]:
    """Broker A's base rows: USD 1000 on D1 booked at 800, USD 500 on D2 booked at 350."""
    return [
        (movement(D1, "USD", "1000", share=share), "800"),
        (movement(D2, "USD", "500", share=share), "350"),
    ]


def _exchange_cash(*extra: CashMovement | tuple[CashMovement, str | None], share: str = "1", unit_rates: dict[tuple[str, date], str] | None = None) -> NativeCash:
    """The base rows (USD 0.8 on D1, 0.7 on D2, 0.625 on D3) followed by ``extra``."""
    return native_cash_of(*_exchange_rows(share), *extra, unit_rates=_EXCHANGE_UNIT_RATES if unit_rates is None else unit_rates)


def _property_cash() -> NativeCash:
    """Four brokers, three currencies, shares 1 / 0.5 / 0.25, a missing and a zero row; every product exact.

    A (share 1): USD +1000 D0 (900), EUR +500 D1, USD −200 D2 (−190), GBP +100 D3 (120).
    B (share 0.5): EUR +1000 D0, USD +400 D1 (380), USD +300 D2 missing, USD 0 D3, USD −100 D4 (−80).
    C (share 0.25): EUR +800 D1, EUR −100 D3 — report currency only.
    G (share 1): GBP +200 D2 (230), GBP −50 D4 (−62.5).
    """
    return native_cash_of(
        (movement(D0, "USD", "1000"), "900"),
        movement(D1, "EUR", "500"),
        (movement(D2, "USD", "-200", transaction_type="WITHDRAWAL"), "-190"),
        (movement(D3, "GBP", "100"), "120"),
        movement(D0, "EUR", "1000", broker_id=B, share="0.5"),
        (movement(D1, "USD", "400", broker_id=B, share="0.5"), "380"),
        (movement(D2, "USD", "300", broker_id=B, share="0.5"), None),
        movement(D3, "USD", "0", broker_id=B, share="0.5", transaction_type="INTEREST"),
        (movement(D4, "USD", "-100", broker_id=B, share="0.5", transaction_type="WITHDRAWAL"), "-80"),
        movement(D1, "EUR", "800", broker_id=C, share="0.25"),
        movement(D3, "EUR", "-100", broker_id=C, share="0.25", transaction_type="WITHDRAWAL"),
        (movement(D2, "GBP", "200", broker_id=G), "230"),
        (movement(D4, "GBP", "-50", broker_id=G, transaction_type="WITHDRAWAL"), "-62.5"),
        unit_rates={("USD", D0): "0.9", ("USD", D1): "0.95", ("USD", D2): "0.95", ("USD", D3): "0.85", ("USD", D4): "0.8", ("GBP", D2): "1.15", ("GBP", D3): "1.2", ("GBP", D4): "1.25"},
    )


def _booked(cash: NativeCash, broker_id: int, date_from: date | None, date_to: date) -> Decimal:
    """What ``broker_id``'s counted rows in ``(date_from, date_to]`` were worth when booked: Σ converted × share, every currency."""
    total = Decimal(0)
    for row, value in zip(cash.movements, cash.converted, strict=True):
        if row.broker_id == broker_id and row.amount != 0 and value is not None and (date_from is None or row.date > date_from) and row.date <= date_to:
            total += value * row.share
    return total


class TestExchangeResults:
    """``exchange_results(date_from, date_to)``: what each broker's foreign cash gained or lost to exchange over ``(date_from, date_to]``.

    Per broker with foreign cash: Σ over its foreign currencies of balance × rate on ``date_to``
    minus the same on ``date_from``, less what its foreign rows in the window were worth when
    booked (``converted × share``). Red until step F-W.
    """

    @pytest.mark.parametrize(("date_from", "date_to", "expected"), _EXCHANGE_WINDOWS, ids=_EXCHANGE_WINDOW_IDS)
    def test_windows(self, date_from, date_to, expected):
        """USD 1000 booked at 800 (0.8) on D1, USD 500 at 350 (0.7) on D2, rate 0.625 on D3: 1500 USD worth 937.5 against 1150 booked."""
        print_section(f"11 — exchange_results({date_from}, {date_to})")
        result = _exchange_cash().exchange_results(date_from, date_to)

        assert result == {A: Decimal(expected)}
        print_success(f"A {result[A]}")

    def test_adjacent_windows_add_up(self):
        """(D1, D2] + (D2, D3] == (D1, D3]: −100 + −112.5 = −212.5."""
        print_section("11 — exchange_results over adjacent windows")
        cash = _exchange_cash()

        first, second, whole = cash.exchange_results(D1, D2), cash.exchange_results(D2, D3), cash.exchange_results(D1, D3)

        assert first[A] + second[A] == whole[A] == Decimal("-212.5")
        print_success(f"{first[A]} + {second[A]} = {whole[A]}")

    @pytest.mark.parametrize(("date_from", "date_to", "expected"), _EXCHANGE_WINDOWS, ids=_EXCHANGE_WINDOW_IDS)
    def test_report_currency_rows_change_nothing(self, date_from, date_to, expected):
        """EUR +1000 on D1 and −200 on D2 at the same broker: booked at their own value, they owe nothing to exchange."""
        print_section(f"11 — exchange_results({date_from}, {date_to}) with EUR rows at A")
        cash = _exchange_cash(movement(D1, "EUR", "1000"), movement(D2, "EUR", "-200", transaction_type="WITHDRAWAL"))

        assert cash.exchange_results(date_from, date_to) == {A: Decimal(expected)}
        print_success(f"A {expected}")

    @pytest.mark.parametrize(("date_from", "date_to", "expected"), _EXCHANGE_WINDOWS, ids=_EXCHANGE_WINDOW_IDS)
    def test_the_share_scales_the_result(self, date_from, date_to, expected):
        """Share 0.5 on the USD rows: half the balance, half the booked value, half the result (−106.25 over (None, D3])."""
        print_section(f"11 — exchange_results({date_from}, {date_to}) at share 0.5")
        result = _exchange_cash(share="0.5").exchange_results(date_from, date_to)

        assert result == {A: Decimal(expected) * Decimal("0.5")}
        print_success(f"A {result[A]}")

    @pytest.mark.parametrize(("date_from", "date_to", "expected"), _EXCHANGE_WINDOWS, ids=_EXCHANGE_WINDOW_IDS)
    def test_a_missing_conversion_is_left_out(self, date_from, date_to, expected):
        """USD 300 on D2 with no conversion: out of the balance and out of the booked value, as ``value_at`` leaves it out."""
        print_section(f"11 — exchange_results({date_from}, {date_to}) with a missing USD row")
        cash = _exchange_cash((movement(D2, "USD", "300"), None))

        assert cash.exchange_results(date_from, date_to) == {A: Decimal(expected)}
        print_success(f"A {expected}")

    def test_keys_are_the_foreign_cash_brokers_ascending_a_zero_included(self):
        """C holds JPY 100 booked at 0.6 with one rate 0.006 (exactly 0), B only EUR: keys A and C, ascending, B absent."""
        print_section("11 — exchange_results keys")
        cash = native_cash_of(
            (movement(D1, "JPY", "100", broker_id=C), "0.6"),
            movement(D1, "EUR", "1000", broker_id=B),
            movement(D2, "EUR", "-50", broker_id=B, transaction_type="WITHDRAWAL"),
            *_exchange_rows(),
            unit_rates={**_EXCHANGE_UNIT_RATES, ("JPY", D1): "0.006"},
        )
        assert cash.foreign_cash_broker_ids == frozenset({A, C}), "precondition"

        result = cash.exchange_results(None, D3)

        assert result == {A: Decimal("-212.5"), C: Decimal("0")}
        assert list(result) == [A, C], "ascending broker ids, whatever the row order"
        assert all(isinstance(value, Decimal) for value in result.values())
        print_success(f"{_str_dict(result)}")

    @pytest.mark.parametrize(("date_from", "date_to"), [(D2, D2), (D3, D1)], ids=["same-day", "reversed"])
    def test_an_empty_window_is_an_empty_dict(self, date_from, date_to):
        """``date_from >= date_to`` is an empty window: ``{}``, not a dict of zeros."""
        print_section(f"11 — exchange_results({date_from}, {date_to}): empty window")

        assert _exchange_cash().exchange_results(date_from, date_to) == {}
        print_success("{}")

    def test_every_foreign_currency_counts_a_negative_balance_too(self):
        """GBP 100 booked at 115 (1.15) on D1, −300 at −348 (1.16) on D2, 1.2 on D3: −200 GBP worth −240 against −233 booked, −7; with the USD rows A is −219.5."""
        print_section("11 — exchange_results over two foreign currencies")
        gbp_rows = [(movement(D1, "GBP", "100"), "115"), (movement(D2, "GBP", "-300", transaction_type="WITHDRAWAL"), "-348")]
        gbp_rates = {("GBP", D1): "1.15", ("GBP", D2): "1.16", ("GBP", D3): "1.2"}

        gbp_only = native_cash_of(*gbp_rows, unit_rates=gbp_rates).exchange_results(None, D3)
        both = _exchange_cash(*gbp_rows, unit_rates={**_EXCHANGE_UNIT_RATES, **gbp_rates}).exchange_results(None, D3)

        assert gbp_only == {A: Decimal("-7")}
        assert both == {A: Decimal("-219.5")}
        print_success(f"GBP {gbp_only[A]}, USD and GBP {both[A]}")

    @pytest.mark.parametrize(("date_from", "date_to"), [(None, D1), (D1, D3)], ids=["to-side", "from-side"])
    def test_a_balance_with_no_rate_raises(self, date_from, date_to):
        """USD 100 booked on D1, USD rates only from D2: the D1 balance cannot be valued, on either side of the window."""
        print_section(f"11 — exchange_results({date_from}, {date_to}) with no USD rate on D1")
        cash = native_cash_of((movement(D1, "USD", "100"), "80"), unit_rates={("USD", D2): "0.8", ("USD", D3): "0.8"})
        with pytest.raises(ValueError, match="no USD/EUR rate"):
            cash.value_at(D1)  # precondition: the same balance value_at refuses

        with pytest.raises(ValueError, match="no USD/EUR rate"):
            cash.exchange_results(date_from, date_to)
        print_success("ValueError")

    def test_the_raw_difference_is_returned_dust_included(self):
        """USD 5000 booked at 5000 / 1.1 while its unit rate is 1 / 1.1: the two roundings differ by about 1E-24, returned as is (the caller filters)."""
        print_section("11 — exchange_results returns a sub-dust difference unfiltered")
        booked = Decimal(5000) / Decimal("1.1")
        unit_rate = Decimal(1) / Decimal("1.1")
        assert Decimal(5000) * unit_rate != booked, "precondition: the two conversions round differently"
        cash = native_cash_of((movement(D1, "USD", "5000"), str(booked)), unit_rates={("USD", D1): str(unit_rate)})

        result = cash.exchange_results(None, D3)

        assert result[A] != 0, "no dust filtering in the module"
        assert abs(result[A]) < native_cash.CONVERSION_DUST
        print_success(f"A {result[A]}")

    @pytest.mark.parametrize(("date_from", "date_to"), _PROPERTY_WINDOWS, ids=_PROPERTY_WINDOW_IDS)
    def test_value_change_less_booked_flows_for_every_window(self, date_from, date_to):
        """result[b] == value_at(to)[b] − value_at(from)[b] − Σ converted × share of b's counted rows in (from, to], every currency included.

        Report-currency rows are booked at their own value, so they cancel out of the identity:
        over the whole cash, the exchange result is what the cash is worth beyond what was paid in.
        """
        print_section(f"11 — exchange_results({date_from}, {date_to}) against value_at")
        cash = _property_cash()
        value_to = cash.value_at(date_to)
        value_from = {} if date_from is None else cash.value_at(date_from)
        expected = {broker_id: value_to.get(broker_id, Decimal(0)) - value_from.get(broker_id, Decimal(0)) - _booked(cash, broker_id, date_from, date_to) for broker_id in sorted(cash.foreign_cash_broker_ids)}

        result = cash.exchange_results(date_from, date_to)

        assert list(result) == sorted(cash.foreign_cash_broker_ids) == [A, B, G]
        assert result == expected
        print_success(f"{_str_dict(result)}")

    def test_conversion_dust_is_one_billionth(self):
        """``CONVERSION_DUST``: the threshold under which a caller treats a conversion difference as rounding."""
        print_section("11 — CONVERSION_DUST")

        assert isinstance(native_cash.CONVERSION_DUST, Decimal)
        assert native_cash.CONVERSION_DUST == Decimal("1e-9")
        print_success(f"{native_cash.CONVERSION_DUST}")


# =============================================================================
# 12 — the unit requests start at the floor (R13-SEC8-2)
# =============================================================================

#: ``EARLIEST_RANGE_START`` (utils/datetime_utils.py) as a literal: the name is new in R13-SEC8-2.
_FLOOR = date(1900, 1, 1)
_BEFORE_THE_FLOOR = date(1890, 1, 1)
_RATES_UNTIL = date(1900, 1, 10)


def _days_from(first: date, count: int) -> list[date]:
    return [date.fromordinal(first.toordinal() + offset) for offset in range(count)]


def _unit_days(fx: FakeFx, currency: str) -> list[date]:
    """The days ``currency``'s unit rate was asked on, in window order: its windows of the one ``unit_rate_steps`` call
    (P3), day by day — the unit requests of the ``convert_bulk`` call before."""
    return _window_days(_unit_windows(fx).get((currency, "EUR"), []))


class TestUnitRequestsStartAtTheFloor:
    """A currency's unit rate is asked on every day from ``max(its first movement, the floor)`` to ``rates_until``, and
    before the floor on each of its movements' own days only (R13-SEC8-2, MEDIUM, DoS): a foreign movement stored
    before 1900 no longer asks one rate for every day since its own date — what it asks is bounded by the movements, not
    by the days. The movement's own amount is still converted at its own date: it is replayed exactly. Since P3 the days
    are windows: ``(d, d)`` for each movement day before the floor, one window from ``max(first, floor)``."""

    @pytest.mark.asyncio
    async def test_a_movement_before_the_floor_asks_its_own_day_then_from_the_floor(self, monkeypatch):
        """USD 100 on 1890-01-01, rates until 1900-01-10: the amount at 1890-01-01, then eleven unit days — the
        movement's own day, 1890-01-01, then 1900-01-01 to 1900-01-10, as the windows (1890-01-01, 1890-01-01) and
        (1900-01-01, 1900-01-10). HEAD 94e170ae1: 3 662, every day from 1890-01-01."""
        print_section("12 — a USD movement of 1890: its own day, then unit windows from 1900-01-01")
        fx = install_fx(monkeypatch, {("USD", "EUR"): {_BEFORE_THE_FLOOR: "0.50", _FLOOR: "0.90"}})

        result = await compute_native_cash(object(), [movement(_BEFORE_THE_FLOOR, "USD", "100")], report_currency="EUR", rates_until=_RATES_UNTIL)

        assert len(fx.calls) == 1
        assert _batch(fx) == [("USD", "100", "EUR", _BEFORE_THE_FLOOR)], "the movement's own amount, at its own date, and nothing else"
        assert _unit_windows(fx) == {("USD", "EUR"): [(_BEFORE_THE_FLOOR, _BEFORE_THE_FLOOR), (_FLOOR, _RATES_UNTIL)]}
        expected = [_BEFORE_THE_FLOOR, *_days_from(_FLOOR, 10)]
        units = _unit_days(fx, "USD")
        assert units == expected, f"{len(units)} USD unit days, from {units[0] if units else None}"
        assert _strs(result.converted) == ["50.00"]
        assert sorted(result.unit_rates) == [("USD", day) for day in expected]
        print_success("the amount at 1890-01-01, unit rates on 1890-01-01 and from 1900-01-01")

    @pytest.mark.asyncio
    async def test_each_movement_before_the_floor_asks_its_own_day_and_nothing_else_before_it(self, monkeypatch):
        """USD 100 on 1890-01-01, USD -30 on 1895-03-01, rates until 1900-01-03: both movements' days, then 1900-01-01
        to 1900-01-03 — no other day before the floor. HEAD: every day from 1890-01-01. A request of the first movement's
        day alone would leave the 1895 balance read at the 1890 rate."""
        print_section("12 — two USD movements before the floor: both their days, nothing else before it")
        fx = install_fx(monkeypatch, {("USD", "EUR"): {_BEFORE_THE_FLOOR: "0.50", date(1895, 3, 1): "0.60", _FLOOR: "0.90"}})
        movements = [movement(_BEFORE_THE_FLOOR, "USD", "100"), movement(date(1895, 3, 1), "USD", "-30", transaction_type="WITHDRAWAL")]

        await compute_native_cash(object(), movements, report_currency="EUR", rates_until=date(1900, 1, 3))

        assert len(fx.calls) == 1
        assert _unit_windows(fx) == {("USD", "EUR"): [(_BEFORE_THE_FLOOR, _BEFORE_THE_FLOOR), (date(1895, 3, 1), date(1895, 3, 1)), (_FLOOR, date(1900, 1, 3))]}
        assert _unit_days(fx, "USD") == [_BEFORE_THE_FLOOR, date(1895, 3, 1), *_days_from(_FLOOR, 3)]
        print_success("1890-01-01, 1895-03-01, then 1900-01-01 to 1900-01-03")

    @pytest.mark.asyncio
    async def test_currencies_starting_on_or_after_the_floor_keep_their_first_movement(self, monkeypatch):
        """GUARD (green on HEAD too): USD 100 on 1900-01-01 itself and GBP 50 on 1900-01-05, rates until 1900-01-06 —
        each currency from its own first movement: GBP 1900-01-05 and 1900-01-06, USD 1900-01-01 to 1900-01-06. A
        floor applied to every currency would ask GBP from 1900-01-01."""
        print_section("12 — first movements on or after the floor: unchanged")
        fx = install_fx(monkeypatch, {("USD", "EUR"): {_FLOOR: "0.90"}, ("GBP", "EUR"): {_FLOOR: "1.20"}})
        movements = [movement(_FLOOR, "USD", "100"), movement(date(1900, 1, 5), "GBP", "50", broker_id=B)]

        await compute_native_cash(object(), movements, report_currency="EUR", rates_until=date(1900, 1, 6))

        assert len(fx.calls) == 1
        assert _unit_windows(fx) == {("GBP", "EUR"): [(date(1900, 1, 5), date(1900, 1, 6))], ("USD", "EUR"): [(_FLOOR, date(1900, 1, 6))]}
        assert (_unit_days(fx, "GBP"), _unit_days(fx, "USD")) == (_days_from(date(1900, 1, 5), 2), _days_from(_FLOOR, 6))
        print_success("GBP from 1900-01-05, USD from 1900-01-01")

    @pytest.mark.asyncio
    @pytest.mark.parametrize("day", [date(1890, 6, 1), date(1899, 12, 31)], ids=["mid-1890", "the-day-before-the-floor"])
    async def test_a_balance_counted_before_the_floor_is_valued_between_its_movement_and_the_floor(self, monkeypatch, day):
        """GUARD: a USD rate stored since 1880 (0.50; 0.90 from the floor) answers the 1890 movement of USD 100 and its
        own day's unit rate. On a day between the movement and the floor ``value_at`` is 50.00 (100 at 0.50, carried),
        and ``exchange_results(day, 1900-01-10)`` 40.00 (90.00 - 50.00) — numbers, no ValueError.

        HEAD: green (every day's unit rate is asked, so the day reads 0.50). Since P3 the movement's own day is a window
        ``(1890-01-01, 1890-01-01)``, whose step carries 0.50 forward. A floor-only clamp — unit rates from 1900-01-01
        alone, without the movements' own days — leaves a counted balance with no rate on or before the day:
        ``_foreign_value`` raises ``ValueError: no USD/EUR rate on or before …``, a 500 once the Dashboard passes such a
        period start to ``exchange_results``. This test guards against that clamp."""
        print_section(f"12 — a USD balance of 1890 valued on {day}")
        fx = install_fx(monkeypatch, {("USD", "EUR"): {date(1880, 1, 1): "0.50", _FLOOR: "0.90"}})

        cash = await compute_native_cash(object(), [movement(_BEFORE_THE_FLOOR, "USD", "100")], report_currency="EUR", rates_until=_RATES_UNTIL)

        assert _unit_windows(fx) == {("USD", "EUR"): [(_BEFORE_THE_FLOOR, _BEFORE_THE_FLOOR), (_FLOOR, _RATES_UNTIL)]}, "precondition: the 1890 day is asked"
        assert _strs(cash.converted) == ["50.00"], "precondition: the 1890 movement is converted, so its balance is counted"
        assert _str_dict(cash.value_at(day)) == {A: "50.00"}
        assert _str_dict(cash.exchange_results(day, _RATES_UNTIL)) == {A: "40.00"}
        print_success(f"value 50.00 on {day}, exchange result 40.00 to {_RATES_UNTIL}")
