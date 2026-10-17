"""MF-D4 (workstream MF), the pure half: a SPLIT asset event stored with a ratio the layer cannot use counts as missing.

Measured before the cure (HEAD 4c767685f): ``PortfolioCalculationEngine.calculate`` raises ``ValueError("SPLIT AssetEvent
… must have a positive finite ratio")`` for such an event linked to a transaction, so ``POST /portfolio/report`` answers
500; the FIFO lot engine applies the ratio (``_apply_split``: ``fragment.unit_price / ratio``) and raises: ``DivisionByZero``
for 0, ``AssertionError("Lot cost invariant violated")`` for -2, ``ValueError("Expected Decimal value")`` for a ratio that
reads as None, ``InvalidOperation`` for NaN or Infinity (measured, plain Python on 4c767685f). The write path (X-R47)
refuses new ones; this lot covers the rows already stored.

The contract (option a, the developer's decision through the coordinator, agreed with J): the event's linked ADJUSTMENT
rows stay the split's rescale, only the ratio is dropped. An invalid ratio is None, not finite, or ≤ 0
(``financial_math.splits.is_valid_split_ratio``). What this file pins, without a database:

* ``financial_math.portfolio.models.InvalidSplitEvent(event_id, asset_id, date)``, a frozen dataclass, and
  ``PortfolioCalculationResult.invalid_split_events``, a list defaulting to empty;
* ``data_quality.build_data_quality_report(..., invalid_split_assets=[(asset_id, name), …])`` gives one WARNING
  ``IssueCode.INVALID_SPLIT_RATIO``, built like MISSING_COST_BASIS: ``group_key`` "invalid_split_ratio",
  ``message_i18n_key`` "dataQuality.invalidSplitRatio", ``message_params`` {"count": n} and ``count`` n with n the
  number of assets given, their ids and names in order, ``cta_action`` "navigate_asset" on the first id; None or [] gives
  none;
* the FIFO lot engine skips a split-linked row whose ratio is invalid: no SPLIT event, no ADJUSTMENT_IN/OUT either (the row
  is still split-linked), the lots not rescaled, nothing raised;
* guards, green before and after: the default call gives no such issue, a valid ratio (2, 0.5) still rescales the lots,
  and the ratios used here are judged by the engine's rule as this file says.

The engine, the portfolio service (summary and report), the lots analysis service and the Yield on Cost parity need
stored rows (``load_split_links`` is a query): they live in ``test_financial/test_invalid_split_ratio_ledger.py``.

Every name read from the cure (``InvalidSplitEvent``, the new parameter, the new code) is looked up inside the test, so
before the cure each test fails on its own with what is missing, and the module still collects. Pure: no DB, no server.
"""

from __future__ import annotations

import dataclasses
from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock

import pytest

import backend.app.services.financial_math.portfolio.data_quality as data_quality
import backend.app.services.financial_math.portfolio.models as portfolio_models
from backend.app.schemas.portfolio import DataQualityReport, IssueDomain, IssueSeverity
from backend.app.services.financial_math.fifo.engine import run_fifo_lot_engine
from backend.app.services.financial_math.fifo.models import FifoInputTransaction
from backend.app.services.financial_math.portfolio.models import DailyPortfolioState
from backend.app.services.financial_math.splits import is_valid_split_ratio

INVALID_SPLIT_RATIO = "INVALID_SPLIT_RATIO"

#: The ratios that count as missing: what the database can hold (0, -2), what an unreadable stored value reads as (None:
#: a stored ±inf, ``RealDecimal`` W-B58), and the non-finite decimals ``is_valid_split_ratio`` names.
INVALID_RATIOS = [
    pytest.param(Decimal("0"), id="zero"),
    pytest.param(Decimal("-2"), id="negative"),
    pytest.param(None, id="none"),
    pytest.param(Decimal("NaN"), id="nan"),
    pytest.param(Decimal("Infinity"), id="infinity"),
]
VALID_RATIOS = [pytest.param(Decimal("2"), id="forward-2"), pytest.param(Decimal("0.5"), id="reverse-0.5")]


# =============================================================================
# GUARD — the ratios of this file are judged by the engine's own rule
# =============================================================================


@pytest.mark.parametrize("ratio", INVALID_RATIOS)
def test_guard_the_invalid_ratios_here_are_invalid_for_the_layer(ratio):
    """Green before and after: every ratio this file calls invalid is refused by ``splits.is_valid_split_ratio``."""
    assert is_valid_split_ratio(ratio) is False, f"is_valid_split_ratio({ratio!r}) is not False: this file's invalid ratios must be the layer's"


@pytest.mark.parametrize("ratio", VALID_RATIOS)
def test_guard_the_valid_ratios_here_are_valid_for_the_layer(ratio):
    """Green before and after: every ratio this file calls valid is accepted by ``splits.is_valid_split_ratio``."""
    assert is_valid_split_ratio(ratio) is True


# =============================================================================
# THE ENGINE'S RECORD — InvalidSplitEvent and PortfolioCalculationResult.invalid_split_events
# =============================================================================


def _invalid_split_event_class() -> type:
    cls = getattr(portfolio_models, "InvalidSplitEvent", None)
    if cls is None:
        pytest.fail("financial_math.portfolio.models has no InvalidSplitEvent (MF-D4): the engine has nowhere to record a SPLIT counted as missing")
    return cls


class TestInvalidSplitEventRecord:
    def test_it_is_a_frozen_dataclass_of_event_asset_and_date(self):
        """Red today: ``InvalidSplitEvent(event_id, asset_id, date)``, frozen, compared by value (the engine deduplicates by
        event, the tests compare lists of them)."""
        cls = _invalid_split_event_class()
        assert dataclasses.is_dataclass(cls), f"InvalidSplitEvent is {cls!r}, not a dataclass"
        assert [field.name for field in dataclasses.fields(cls)] == ["event_id", "asset_id", "date"]
        record = cls(event_id=11, asset_id=7, date=date(2025, 1, 8))
        assert record == cls(event_id=11, asset_id=7, date=date(2025, 1, 8))
        assert record != cls(event_id=12, asset_id=7, date=date(2025, 1, 8))
        with pytest.raises(dataclasses.FrozenInstanceError):
            record.event_id = 12  # type: ignore[misc]

    def test_the_result_lists_none_by_default(self):
        """Red today: ``PortfolioCalculationResult.invalid_split_events`` exists and is empty when nothing is invalid,
        a fresh list each time (a shared default would leak one scope's events into another's result)."""
        first = portfolio_models.PortfolioCalculationResult(daily_states=[])
        second = portfolio_models.PortfolioCalculationResult(daily_states=[])
        assert hasattr(first, "invalid_split_events"), "PortfolioCalculationResult has no invalid_split_events (MF-D4)"
        assert first.invalid_split_events == []
        assert first.invalid_split_events is not second.invalid_split_events


# =============================================================================
# DATA QUALITY — IssueCode.INVALID_SPLIT_RATIO
# =============================================================================


def _complete_state(day: str) -> DailyPortfolioState:
    state = MagicMock(spec=DailyPortfolioState)
    state.date = date.fromisoformat(day)
    state.nav_complete = True
    state.missing_fx_pairs = set()
    return state


STATES = [_complete_state("2025-01-09"), _complete_state("2025-01-10")]


def _report_with(invalid_split_assets):
    try:
        return data_quality.build_data_quality_report(STATES, invalid_split_assets=invalid_split_assets)
    except TypeError as exc:
        pytest.fail(f"build_data_quality_report(…, invalid_split_assets=…) raised {exc!r}: it takes the assets with a SPLIT counted as missing (MF-D4)")


def _invalid_split_issues(report) -> list:
    return [issue for issue in report.issues if str(issue.code) == INVALID_SPLIT_RATIO]


class TestInvalidSplitRatioIssue:
    def test_the_code_exists(self):
        """Red today: ``IssueCode.INVALID_SPLIT_RATIO`` == "INVALID_SPLIT_RATIO" (the frontend keys on the string)."""
        from backend.app.schemas.portfolio import IssueCode  # noqa: PLC0415 — read when the test runs, so the module collects without it

        assert getattr(IssueCode, INVALID_SPLIT_RATIO, None) == INVALID_SPLIT_RATIO, "schemas.portfolio.IssueCode has no INVALID_SPLIT_RATIO (MF-D4)"

    def test_one_asset_gives_one_warning_that_names_it(self):
        """Red today: [(7, "ACME")] gives one WARNING built like MISSING_COST_BASIS, naming that asset."""
        issues = _invalid_split_issues(_report_with([(7, "ACME")]))
        assert len(issues) == 1, f"expected one {INVALID_SPLIT_RATIO} issue, got {[str(issue.code) for issue in issues]}"
        issue = issues[0]
        assert issue.domain == IssueDomain.PORTFOLIO
        assert issue.severity == IssueSeverity.WARNING
        assert issue.group_key == "invalid_split_ratio"
        assert issue.message_i18n_key == "dataQuality.invalidSplitRatio"
        assert issue.message_params == {"count": 1}
        assert issue.count == 1
        assert issue.affected_asset_ids == [7]
        assert issue.affected_asset_names == ["ACME"]
        assert issue.cta_action == "navigate_asset"
        assert issue.cta_target == "7"

    def test_the_count_is_the_number_of_assets_and_the_cta_targets_the_first(self):
        """Red today: two assets → still one issue, count 2, both named in the order given, the CTA on the first."""
        issues = _invalid_split_issues(_report_with([(7, "ACME"), (9, "BETA")]))
        assert len(issues) == 1, f"expected one {INVALID_SPLIT_RATIO} issue for two assets, got {len(issues)}"
        issue = issues[0]
        assert issue.message_params == {"count": 2}
        assert issue.count == 2
        assert issue.affected_asset_ids == [7, 9]
        assert issue.affected_asset_names == ["ACME", "BETA"]
        assert issue.cta_target == "7"

    def test_a_warning_alone_does_not_degrade_the_status(self):
        """Red today (the parameter): like MISSING_COST_BASIS, the warning is an issue, not a gap in the data — the
        derived status reads only the legacy gap fields, none of which an invalid split fills."""
        report = _report_with([(7, "ACME")])
        assert report.data_quality_status == DataQualityReport(issues=[]).data_quality_status

    @pytest.mark.parametrize("invalid_split_assets", [pytest.param(None, id="none"), pytest.param([], id="empty")])
    def test_no_asset_gives_no_issue(self, invalid_split_assets):
        """Red today only for the new parameter: None or [] gives no INVALID_SPLIT_RATIO issue."""
        assert _invalid_split_issues(_report_with(invalid_split_assets)) == []

    def test_guard_the_default_call_gives_no_issue(self):
        """Green before and after: a caller that does not pass the parameter gets no such issue."""
        report = data_quality.build_data_quality_report(STATES)
        assert [str(issue.code) for issue in report.issues if str(issue.code) == INVALID_SPLIT_RATIO] == []


# =============================================================================
# FIFO LOTS — a split-linked row with an invalid ratio is skipped
# =============================================================================

ASSET_ID = 701
BROKER_ID = 1
BUY_ID = 1
SPLIT_ROW_ID = 2


def _tx(tx_id: int, tx_type: str, day: str, quantity: str, amount: str = "0", cost_basis_override: str | None = None) -> FifoInputTransaction:
    return FifoInputTransaction(
        id=tx_id,
        broker_id=BROKER_ID,
        asset_id=ASSET_ID,
        date=date.fromisoformat(day),
        type=tx_type,
        quantity=Decimal(quantity),
        amount=Decimal(amount),
        currency="EUR",
        cost_basis_override=Decimal(cost_basis_override) if cost_basis_override is not None else None,
        cost_basis_currency="EUR" if cost_basis_override is not None else None,
    )


#: The two ledgers a split row meets: a forward split (BUY 10 @ 100, then a row of +10) and a reverse one (BUY 30 @ 50,
#: then a row of -15). Each: (quantity bought, unit price, the split row's quantity).
LEDGERS = {
    "forward": ("10", "100", "10"),
    "reverse": ("30", "50", "-15"),
}


def _ledger(kind: str, *, cost_basis_override: str | None = None) -> list[FifoInputTransaction]:
    bought, unit_price, split_quantity = LEDGERS[kind]
    return [
        _tx(BUY_ID, "BUY", "2025-01-03", bought, amount=str(-Decimal(bought) * Decimal(unit_price))),
        _tx(SPLIT_ROW_ID, "ADJUSTMENT", "2025-01-08", split_quantity, cost_basis_override=cost_basis_override),
    ]


def _run(transactions: list[FifoInputTransaction], ratio):
    try:
        return run_fifo_lot_engine(
            transactions,
            {BROKER_ID: False},
            split_ratios_by_tx_id={SPLIT_ROW_ID: ratio},
            split_event_ids_by_tx_id={SPLIT_ROW_ID: 501},
            target_currency="EUR",
        )
    except Exception as exc:  # noqa: BLE001 — the contract is «never raises»: any exception is the finding
        pytest.fail(f"run_fifo_lot_engine with a split ratio of {ratio!r} raised {exc!r}: the lots analysis answers 500 (MF-D4: skip that SPLIT)")


class TestFifoSkipsAnInvalidSplit:
    @pytest.mark.parametrize("kind", list(LEDGERS))
    @pytest.mark.parametrize("cost_basis_override", [pytest.param(None, id="costless-row"), pytest.param("50", id="priced-row")])
    @pytest.mark.parametrize("ratio", INVALID_RATIOS)
    def test_the_split_row_is_skipped_and_the_lot_is_not_rescaled(self, ratio, cost_basis_override, kind):
        """Red today: nothing raises; the row gives no SPLIT and, still split-linked, no ADJUSTMENT_IN/OUT either — no
        event at all — and the BUY's lot keeps its quantity, unit price and cost: it is not rescaled."""
        bought, unit_price, _split_quantity = LEDGERS[kind]
        result = _run(_ledger(kind, cost_basis_override=cost_basis_override), ratio)

        row_events = [(event.kind, event.transaction_id) for event in result.classified_events if event.transaction_id == SPLIT_ROW_ID or SPLIT_ROW_ID in event.raw_transaction_ids]
        assert row_events == [], f"the split row with ratio {ratio!r} became {row_events}: it is skipped, neither a SPLIT nor an ADJUSTMENT"
        assert SPLIT_ROW_ID not in result.split_quantities_by_transaction_id
        assert [lot.lot_id for lot in result.lots] == [BUY_ID], "the only lot is the BUY's: the split row opens none"
        lot = result.get_lot(BUY_ID)
        assert lot.original_quantity == Decimal(bought)
        assert lot.open_quantity == Decimal(bought)
        assert lot.opening_unit_price == Decimal(unit_price)
        assert lot.original_cost == Decimal(bought) * Decimal(unit_price)
        active = result.active_fragments(lot_id=BUY_ID)
        assert [(fragment.quantity, fragment.unit_price) for fragment in active] == [(Decimal(bought), Decimal(unit_price))]

    @pytest.mark.parametrize("kind", list(LEDGERS))
    @pytest.mark.parametrize("ratio", VALID_RATIOS)
    def test_guard_a_valid_ratio_still_rescales_the_lot(self, ratio, kind):
        """Green before and after: with a valid ratio the row is a SPLIT of that ratio, and the lot keeps its cost over
        quantity × ratio. (The ledger's own quantity is irrelevant to the FIFO: it applies the ratio.)"""
        bought, unit_price, _split_quantity = LEDGERS[kind]
        result = _run(_ledger(kind), ratio)

        split_events = [event for event in result.classified_events if event.kind == "SPLIT"]
        assert [(event.transaction_id, event.ratio) for event in split_events] == [(SPLIT_ROW_ID, ratio)]
        lot = result.get_lot(BUY_ID)
        assert lot.open_quantity == Decimal(bought) * ratio
        assert lot.original_cost == Decimal(bought) * Decimal(unit_price)
        assert lot.open_quantity * lot.opening_unit_price == lot.original_cost
