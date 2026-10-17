"""
Test: FX Core Service — normalize_rate_for_storage, upsert_rates_bulk,
delete_rates_bulk, _count_actual_changes.

Covers the service-layer helper functions in services/fx/ (storage.py, sync.py) that are NOT covered
by test_fx_conversion.py (which focuses on convert_bulk / compute_chain_rate).

X-R38 (the FX side of W-B58, reported as W-B61): a manual rate ``fx_rates.rate`` cannot keep. Measured before the cure:
``upsert_rates_bulk`` checks ``base != quote`` and ``rate > 0`` only, then writes every rate of the call as a float: 1E+400
is stored as a REAL inf, its inverse as 0, 1E+15 as it is, 1E-11 as a value that reads back 0; a NaN makes the ``rate > 0``
check raise ``InvalidOperation``, and the inverse of 1E-1000000 ``decimal.Overflow``. ``_count_actual_changes`` truncates a
stored rate to compare it, which raises ``InvalidOperation`` on a legacy inf or 1e60. The contract: after its
normalization (the inverse when base > quote) a rate ``storable_fx_rate`` refuses is a ``ValueError`` naming the pair,
the date and the limits (14 digits before the decimal point, 10 decimal places), raised before anything of the call is
written; a rate at the limits is stored; the comparison with a legacy rate no column can keep never raises and counts a
change. Every X-R38 row is this file's (ISK quote), in a window of 1993 no other test writes, wiped before and after.
"""

import asyncio
import re
import sys
from datetime import date, timedelta
from decimal import Decimal

import pytest

from backend.app.config import PROJECT_ROOT

sys.path.insert(0, str(PROJECT_ROOT))

# Setup test database BEFORE importing app modules
from backend.test_scripts.test_db_config import setup_test_database

setup_test_database()

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import delete

import backend.app.services.financial_math.portfolio.engine as portfolio_engine_module
from backend.app.db.models import FxRate
from backend.app.db.precision import truncate_fx_rate
from backend.app.db.session import get_async_engine
from backend.app.services.fx.storage import delete_rates_bulk, normalize_rate_for_storage, upsert_rates_bulk
from backend.app.services.fx.sync import _count_actual_changes
from backend.app.services.portfolio_service import _portfolio_l2_cache
from backend.test_scripts.test_utils import print_section, print_success

# ============================================================================
# FIXTURE — clean FxRate table before each test
# ============================================================================


# The pair this file owns.
#
# It used to work on EUR/USD and start each test by emptying the entire `fx_rates`
# table — a DELETE with no WHERE, committed, from an autouse fixture. That took the
# mock's ECB series and any rate a concurrent test had just synced with it, and a
# committed DELETE is not something a neighbour's rollback can put back.
#
# The purge could not simply be narrowed, because it was load bearing: "no existing
# data -> all rates are new -> count = 2" is only true of EUR/USD if somebody has
# just demolished it. So the pair moved instead. BGN/ISK and CHF/ISK are used nowhere else
# in the codebase as FX pairs — not by populate_mock_data, not by any other test — which
# makes "no existing data" true by construction rather than by destruction.
FX_CORE_BASE = "BGN"
FX_CORE_BASE_ALT = "CHF"
# Everything this file writes uses ISK as the quote, so one WHERE covers all of it.
FX_CORE_QUOTE = "ISK"


@pytest.fixture(autouse=True)
def _clean_fx_rates():
    """Clear this file's own pair before each test, and nobody else's."""

    async def _purge():
        engine = get_async_engine()
        async with AsyncSession(engine) as session:
            await session.execute(delete(FxRate).where(FxRate.quote == FX_CORE_QUOTE))
            await session.commit()

    asyncio.run(_purge())
    yield


# X-R38: the window of this file's X-R38 rows, far from the dates its other tests write (today and the days before it).
XR38_DAYS = tuple(date(1993, 4, 5) + timedelta(days=offset) for offset in range(4))
XR38_SOURCE = "X-R38"


async def _xr38_wipe() -> None:
    """Drop this file's rates (ISK quote) in the X-R38 window."""
    async with AsyncSession(get_async_engine()) as session:
        await session.execute(delete(FxRate).where(FxRate.quote == FX_CORE_QUOTE, FxRate.date >= XR38_DAYS[0], FxRate.date <= XR38_DAYS[-1]))
        await session.commit()


@pytest.fixture
def xr38_rows():
    """X-R38: no rate of this file in the window before and after the test (the autouse purge runs before it only)."""
    asyncio.run(_xr38_wipe())
    yield
    asyncio.run(_xr38_wipe())


async def _xr38_stored() -> dict[tuple[str, str, date], Decimal]:
    """This file's rates in the X-R38 window by (base, quote, date), read through the model, as the app reads them."""
    async with AsyncSession(get_async_engine()) as session:
        rows = (await session.execute(select(FxRate.base, FxRate.quote, FxRate.date, FxRate.rate).where(FxRate.quote == FX_CORE_QUOTE, FxRate.date >= XR38_DAYS[0], FxRate.date <= XR38_DAYS[-1]))).all()
    return {(row.base, row.quote, row.date): row.rate for row in rows}


def _xr38_numbers(message: str) -> set[str]:
    """The whole numbers ``message`` states, its ISO dates taken out first: a date cannot stand in for a limit."""
    return set(re.findall(r"\d+", re.sub(r"\d{4}-\d{2}-\d{2}", " ", message)))


async def _xr38_upsert_refused(rates: list[tuple], story: str) -> ValueError:
    """``upsert_rates_bulk`` for a call that must be refused: its ValueError, which ``POST /fx/currencies/rate`` turns
    into the item's error. Any other exception fails the test naming it, and so does a call that goes through."""
    async with AsyncSession(get_async_engine()) as session:
        try:
            results = await upsert_rates_bulk(session, rates)
        except ValueError as refusal:
            return refusal
        except Exception as exc:  # noqa: BLE001 — any other exception is the defect under test
            pytest.fail(f"{story} raised {exc!r} instead of a ValueError: POST /fx/currencies/rate reports a failure, not the limit (X-R38)")
    pytest.fail(f"{story} was accepted ({results}) and reads back as {await _xr38_stored()}, instead of being refused (X-R38: at most 14 digits before the decimal point, not 0 at 10 decimal places)")


# ============================================================================
# normalize_rate_for_storage — pure function tests
# ============================================================================


class TestNormalizeRateForStorage:
    """Tests for normalize_rate_for_storage()."""

    def test_base_lt_quote_no_change(self):
        """EUR < USD alphabetically → no inversion."""
        print_section("normalize_rate: base < quote (no-op)")
        b, q, r = normalize_rate_for_storage("EUR", "USD", Decimal("1.08"))
        assert b == "EUR"
        assert q == "USD"
        assert r == Decimal("1.08")
        print_success("No inversion when base < quote")

    def test_base_gt_quote_invert(self):
        """USD > CHF → swap to CHF/USD + invert rate."""
        print_section("normalize_rate: base > quote (invert)")
        b, q, r = normalize_rate_for_storage("USD", "CHF", Decimal("0.90"))
        assert b == "CHF"
        assert q == "USD"
        # Inverted: 1/0.90 ≈ 1.1111...
        expected = Decimal("1") / Decimal("0.90")
        assert r == expected
        print_success(f"Inverted correctly: CHF/USD = {r}")

    def test_base_eq_quote(self):
        """Same currency — normalize_rate_for_storage doesn't validate, returns as-is."""
        print_section("normalize_rate: base == quote (edge case)")
        b, q, r = normalize_rate_for_storage("EUR", "EUR", Decimal("1.00"))
        # base == quote alphabetically → no inversion path
        assert b == "EUR"
        assert q == "EUR"
        assert r == Decimal("1.00")
        print_success("Same currency returns as-is (no validation in this function)")


# ============================================================================
# upsert_rates_bulk — DB tests
# ============================================================================


@pytest.mark.asyncio
class TestUpsertRatesBulk:
    """Tests for upsert_rates_bulk()."""

    async def test_insert_new_rates(self):
        """Insert brand-new rates → action = 'inserted'."""
        print_section("upsert_rates_bulk: insert new rates")
        engine = get_async_engine()
        async with AsyncSession(engine) as session:
            today = date.today()
            rates = [
                (today, FX_CORE_BASE, FX_CORE_QUOTE, Decimal("1.0800"), "TEST"),
                (today, FX_CORE_BASE_ALT, FX_CORE_QUOTE, Decimal("1.0600"), "TEST"),
            ]
            results = await upsert_rates_bulk(session, rates)
            assert len(results) == 2
            for success, action in results:
                assert success is True
                assert action == "inserted"
            print_success(f"Inserted {len(results)} rates")

    async def test_upsert_existing_rates(self):
        """Insert then re-insert same keys with different value → action = 'updated'."""
        print_section("upsert_rates_bulk: update existing rates")
        engine = get_async_engine()
        async with AsyncSession(engine) as session:
            today = date.today()
            rates_v1 = [(today, FX_CORE_BASE, FX_CORE_QUOTE, Decimal("1.0800"), "TEST")]
            await upsert_rates_bulk(session, rates_v1)

        async with AsyncSession(engine) as session:
            rates_v2 = [(today, FX_CORE_BASE, FX_CORE_QUOTE, Decimal("1.0900"), "TEST_v2")]
            results = await upsert_rates_bulk(session, rates_v2)
            assert len(results) == 1
            success, action = results[0]
            assert success is True
            assert action == "updated"
            print_success("Updated existing rate correctly")

    async def test_empty_list(self):
        """Empty input → empty results."""
        print_section("upsert_rates_bulk: empty list")
        engine = get_async_engine()
        async with AsyncSession(engine) as session:
            results = await upsert_rates_bulk(session, [])
            assert results == []
            print_success("Empty list → empty results")

    async def test_validation_same_currency(self):
        """base == quote → ValueError."""
        print_section("upsert_rates_bulk: validation base == quote")
        engine = get_async_engine()
        async with AsyncSession(engine) as session:
            with pytest.raises(ValueError, match="Base and quote must be different"):
                await upsert_rates_bulk(session, [(date.today(), "EUR", "EUR", Decimal("1"), "TEST")])
            print_success("ValueError raised for same currency")

    async def test_validation_negative_rate(self):
        """rate ≤ 0 → ValueError."""
        print_section("upsert_rates_bulk: validation rate ≤ 0")
        engine = get_async_engine()
        async with AsyncSession(engine) as session:
            with pytest.raises(ValueError, match="Rate must be positive"):
                await upsert_rates_bulk(session, [(date.today(), FX_CORE_BASE, FX_CORE_QUOTE, Decimal("-1"), "TEST")])
            print_success("ValueError raised for negative rate")

    async def test_auto_normalize_order(self):
        """base > quote → auto-normalized to alphabetical order."""
        print_section("upsert_rates_bulk: auto-normalize order")
        engine = get_async_engine()
        async with AsyncSession(engine) as session:
            today = date.today()
            # USD > CHF → should be stored as CHF/USD inverted
            rates = [(today, FX_CORE_BASE_ALT, FX_CORE_QUOTE, Decimal("1.1111"), "TEST")]
            results = await upsert_rates_bulk(session, rates)
            assert results[0] == (True, "inserted")
            print_success("Auto-normalized and inserted correctly")


# ============================================================================
# delete_rates_bulk — DB tests
# ============================================================================


@pytest.mark.asyncio
class TestDeleteRatesBulk:
    """Tests for delete_rates_bulk()."""

    async def _seed(self, session, pairs_dates):
        """Helper: insert rates for given (base, quote, date) tuples."""
        for b, q, d in pairs_dates:
            rate = FxRate(date=d, base=b, quote=q, rate=Decimal("1.0000"), source="TEST")
            session.add(rate)
        await session.commit()

    async def test_delete_single_day(self):
        """Delete a single day for a pair."""
        print_section("delete_rates_bulk: single day")
        engine = get_async_engine()
        today = date.today()
        async with AsyncSession(engine) as session:
            await self._seed(session, [(FX_CORE_BASE, FX_CORE_QUOTE, today)])

        async with AsyncSession(engine) as session:
            results = await delete_rates_bulk(session, [(FX_CORE_BASE, FX_CORE_QUOTE, today, None)])
            assert len(results) == 1
            success, existing, deleted, msg = results[0]
            assert success is True
            assert deleted >= 1
            print_success(f"Deleted {deleted} rate(s)")

    async def test_delete_range(self):
        """Delete a date range for a pair."""
        print_section("delete_rates_bulk: date range")
        engine = get_async_engine()
        base_date = date.today() - timedelta(days=10)
        dates = [base_date + timedelta(days=i) for i in range(5)]
        async with AsyncSession(engine) as session:
            await self._seed(session, [(FX_CORE_BASE, FX_CORE_QUOTE, d) for d in dates])

        async with AsyncSession(engine) as session:
            results = await delete_rates_bulk(session, [(FX_CORE_BASE, FX_CORE_QUOTE, dates[0], dates[-1])])
            success, existing, deleted, msg = results[0]
            assert success is True
            assert deleted == 5
            print_success(f"Deleted {deleted} rate(s) in range")

    async def test_delete_not_found(self):
        """Delete non-existent pair → success=True, deleted=0."""
        print_section("delete_rates_bulk: pair not found")
        engine = get_async_engine()
        async with AsyncSession(engine) as session:
            results = await delete_rates_bulk(session, [("AAA", "ZZZ", date.today(), None)])
            success, existing, deleted, msg = results[0]
            assert success is True
            assert deleted == 0
            print_success("Not found returns (True, 0, 0, ...)")

    async def test_delete_empty_list(self):
        """Empty input → empty results."""
        print_section("delete_rates_bulk: empty list")
        engine = get_async_engine()
        async with AsyncSession(engine) as session:
            results = await delete_rates_bulk(session, [])
            assert results == []
            print_success("Empty list → empty results")


# ============================================================================
# _count_actual_changes — DB tests
# ============================================================================


@pytest.mark.asyncio
class TestCountActualChanges:
    """Tests for _count_actual_changes()."""

    async def test_all_new_inserts(self):
        """No existing data → all rates are new → count = len."""
        print_section("_count_actual_changes: all new")
        engine = get_async_engine()
        today = date.today()
        async with AsyncSession(engine) as session:
            computed = [
                (today, FX_CORE_BASE, FX_CORE_QUOTE, truncate_fx_rate(Decimal("1.0800"))),
                (today - timedelta(days=1), FX_CORE_BASE, FX_CORE_QUOTE, truncate_fx_rate(Decimal("1.0790"))),
            ]
            count = await _count_actual_changes(session, computed)
            assert count == 2
            print_success(f"All new → count = {count}")

    async def test_no_changes(self):
        """Existing data matches exactly → count = 0."""
        print_section("_count_actual_changes: no changes")
        engine = get_async_engine()
        today = date.today()
        rate_val = truncate_fx_rate(Decimal("1.0800"))

        async with AsyncSession(engine) as session:
            session.add(FxRate(date=today, base=FX_CORE_BASE, quote=FX_CORE_QUOTE, rate=rate_val, source="TEST"))
            await session.commit()

        async with AsyncSession(engine) as session:
            computed = [(today, FX_CORE_BASE, FX_CORE_QUOTE, rate_val)]
            count = await _count_actual_changes(session, computed)
            assert count == 0
            print_success(f"Same values → count = {count}")

    async def test_mixed_changes(self):
        """Mix of new, same, and changed values."""
        print_section("_count_actual_changes: mixed")
        engine = get_async_engine()
        d1 = date.today()
        d2 = date.today() - timedelta(days=1)
        d3 = date.today() - timedelta(days=2)
        rate_same = truncate_fx_rate(Decimal("1.0800"))
        rate_changed_old = truncate_fx_rate(Decimal("1.0700"))
        rate_changed_new = truncate_fx_rate(Decimal("1.0900"))

        async with AsyncSession(engine) as session:
            # d1: existing with same value (no change)
            session.add(FxRate(date=d1, base=FX_CORE_BASE, quote=FX_CORE_QUOTE, rate=rate_same, source="TEST"))
            # d2: existing with different value (change)
            session.add(FxRate(date=d2, base=FX_CORE_BASE, quote=FX_CORE_QUOTE, rate=rate_changed_old, source="TEST"))
            await session.commit()

        async with AsyncSession(engine) as session:
            computed = [
                (d1, FX_CORE_BASE, FX_CORE_QUOTE, rate_same),  # same → no change
                (d2, FX_CORE_BASE, FX_CORE_QUOTE, rate_changed_new),  # changed → +1
                (d3, FX_CORE_BASE, FX_CORE_QUOTE, truncate_fx_rate(Decimal("1.0750"))),  # new → +1
            ]
            count = await _count_actual_changes(session, computed)
            assert count == 2  # 1 changed + 1 new
            print_success(f"Mixed → count = {count} (1 changed + 1 new)")

    async def test_empty_list(self):
        """Empty computed list → 0."""
        print_section("_count_actual_changes: empty list")
        engine = get_async_engine()
        async with AsyncSession(engine) as session:
            count = await _count_actual_changes(session, [])
            assert count == 0
            print_success("Empty list → 0")

    @pytest.mark.parametrize(
        "planted",
        [
            pytest.param(float("inf"), id="inf"),
            pytest.param(0.0, id="0"),
            pytest.param(1e19, id="1e19-20-integer-digits"),
            pytest.param(1e60, id="1e60"),
        ],
    )
    async def test_xr38_a_legacy_rate_no_column_can_keep_counts_as_a_change_never_raising(self, planted):
        """Red today for inf and 1e60: the stored rate reads back ``Decimal('Infinity')`` or a Decimal of 70 digits, and
        ``truncate_fx_rate`` raises ``InvalidOperation`` on it, so the sync of the pair fails. Green today for 0 and 1e19.

        Contract (X-R38): reads never raise. A stored rate no column can keep, as an older release could leave it (planted
        with raw SQL, past the model), compares as different from the new rate: one change, and the sync overwrites it.
        The plant is never committed: the session rolls it back.
        """
        print_section(f"_count_actual_changes: legacy stored rate {planted!r}")
        day = XR38_DAYS[0]
        key = {"day": day.isoformat(), "base": FX_CORE_BASE, "quote": FX_CORE_QUOTE}
        async with AsyncSession(get_async_engine()) as session:
            try:
                await session.execute(text("INSERT INTO fx_rates (date, base, quote, rate, source, fetched_at) VALUES (:day, :base, :quote, :rate, :source, CURRENT_TIMESTAMP)"), {**key, "rate": planted, "source": XR38_SOURCE})
                found = (await session.execute(text("SELECT rate FROM fx_rates WHERE base = :base AND quote = :quote AND date = :day"), key)).scalar_one()
                assert found == planted, f"barrier: the legacy rate reads back {found!r} with raw SQL, not {planted!r}"
                try:
                    count = await _count_actual_changes(session, [(day, FX_CORE_BASE, FX_CORE_QUOTE, truncate_fx_rate(Decimal("1.5")))])
                except Exception as exc:  # noqa: BLE001 — any exception is the defect under test
                    pytest.fail(f"comparing a new rate of 1.5 with a stored {planted!r} raised {exc!r}: the sync of {FX_CORE_BASE}/{FX_CORE_QUOTE} fails (X-R38: reads never raise)")
                assert count == 1, f"a new rate of 1.5 against a stored {planted!r} counts {count} change(s): expected 1, the new rate overwrites it"
            finally:
                await session.rollback()
        print_success(f"legacy {planted!r} counted as a change")


# ============================================================================
# normalize_rate_for_storage — additional edge cases
# ============================================================================


class TestNormalizeRateEdgeCases:
    """Additional edge cases for normalize_rate_for_storage."""

    def test_very_small_rate(self):
        """Very small rate (like JPY per 100) normalizes correctly."""
        print_section("normalize_rate: very small rate")
        b, q, r = normalize_rate_for_storage("JPY", "USD", Decimal("0.0067"))
        assert b == "JPY"
        assert q == "USD"
        assert r == Decimal("0.0067")
        print_success(f"Small rate preserved: {r}")

    def test_large_rate(self):
        """Large rate (e.g., 1 BTC = 60000 USD) normalizes correctly."""
        print_section("normalize_rate: large rate")
        b, q, r = normalize_rate_for_storage("BTC", "USD", Decimal("60000.50"))
        # BTC > USD alphabetically → inverted to (BTC, USD)
        assert b == "BTC"
        assert q == "USD"
        assert r == Decimal("60000.50")
        print_success(f"Large rate preserved: {r}")


# ============================================================================
# upsert_rates_bulk — additional edge cases
# ============================================================================


@pytest.mark.asyncio
class TestUpsertRatesBulkEdgeCases:
    """Additional edge case tests for upsert_rates_bulk."""

    async def test_upsert_same_rate_unchanged(self):
        """Insert then re-insert same key with same value → action = 'unchanged'."""
        print_section("upsert_rates_bulk: same rate unchanged")
        engine = get_async_engine()
        today = date.today()
        rate_val = Decimal("1.0800")

        async with AsyncSession(engine) as session:
            await upsert_rates_bulk(session, [(today, FX_CORE_BASE, FX_CORE_QUOTE, rate_val, "TEST")])

        async with AsyncSession(engine) as session:
            results = await upsert_rates_bulk(session, [(today, FX_CORE_BASE, FX_CORE_QUOTE, rate_val, "TEST")])
            assert len(results) == 1
            success, action = results[0]
            assert success is True
            # Action should be 'updated' or 'unchanged' — depending on implementation
            assert action in ("updated", "unchanged")
            print_success(f"Same rate → action={action}")

    async def test_upsert_multiple_pairs(self):
        """Multiple different pairs in one bulk call."""
        print_section("upsert_rates_bulk: multiple pairs")
        engine = get_async_engine()
        today = date.today()
        rates = [
            (today, "CHF", "USD", Decimal("1.1200"), "TEST"),
            (today, "EUR", "GBP", Decimal("0.8400"), "TEST"),
            (today, "AUD", "USD", Decimal("0.6500"), "TEST"),
        ]
        async with AsyncSession(engine) as session:
            results = await upsert_rates_bulk(session, rates)
            assert len(results) == 3
            assert all(r[0] for r in results), "All should succeed"
            print_success(f"Inserted {len(results)} different pairs")


# ============================================================================
# upsert_rates_bulk — X-R38: a rate no column can keep
# ============================================================================


@pytest.mark.asyncio
@pytest.mark.usefixtures("xr38_rows")
class TestUpsertRatesBulkDigitLimits:
    """X-R38 (the FX side of W-B58): a manual rate ``fx_rates.rate`` cannot keep is refused before anything is written."""

    @pytest.mark.parametrize(
        ("base", "quote", "typed", "normalized"),
        [
            pytest.param(FX_CORE_BASE, FX_CORE_QUOTE, "1E+15", "1E+15", id="1E+15"),
            pytest.param(FX_CORE_BASE, FX_CORE_QUOTE, "100000000000000", "100000000000000", id="derived-15-integer-digits"),
            pytest.param(FX_CORE_BASE, FX_CORE_QUOTE, "1E+400", "1E+400", id="1E+400"),
            pytest.param(FX_CORE_BASE, FX_CORE_QUOTE, "1E-11", "1E-11", id="1E-11"),
            pytest.param(FX_CORE_BASE, FX_CORE_QUOTE, "NaN", "NaN", id="derived-NaN"),
            pytest.param(FX_CORE_QUOTE, FX_CORE_BASE, "1E-15", "1E+15", id="inverted-1E-15"),
            pytest.param(FX_CORE_QUOTE, FX_CORE_BASE, "1E+11", "1E-11", id="inverted-1E+11"),
            pytest.param(FX_CORE_QUOTE, FX_CORE_BASE, "1E+400", "1E-400", id="derived-inverted-1E+400"),
            pytest.param(FX_CORE_QUOTE, FX_CORE_BASE, "1E-1000000", "1E+1000000", id="derived-inverted-1E-1000000-the-inverse-overflows"),
        ],
    )
    async def test_xr38_a_rate_no_column_can_keep_is_refused_and_nothing_of_the_call_is_written(self, base, quote, typed, normalized):
        """Red today: accepted, and written with the valid rate of the call — 1E+15 and 15 integer digits as they are,
        1E+400 as a REAL inf, 1E-11 and the inverse of 1E+11 or 1E+400 as values that read back 0, the inverse of 1E-15 as
        1E+15; a NaN makes the ``rate > 0`` check raise ``InvalidOperation``, the inverse of 1E-1000000 ``decimal.Overflow``.

        Contract (X-R38): after the normalization (the inverse when base > quote) a rate ``storable_fx_rate`` refuses is a
        ``ValueError`` naming the pair, the date and the limits (14 digits before the decimal point, 10 decimal places),
        raised before anything of the call is written: the valid CHF/ISK rate saved first in the same call is not written
        either. The ``derived-`` cases read the same rule.
        """
        print_section(f"upsert_rates_bulk: {base}/{quote} {typed} refused")
        story = f"a manual {base}/{quote} rate of {typed} on {XR38_DAYS[1]} ({FX_CORE_BASE}/{FX_CORE_QUOTE} {normalized} once normalized), saved after a valid {FX_CORE_BASE_ALT}/{FX_CORE_QUOTE} rate"
        rates = [
            (XR38_DAYS[0], FX_CORE_BASE_ALT, FX_CORE_QUOTE, Decimal("1.5"), XR38_SOURCE),
            (XR38_DAYS[1], base, quote, Decimal(typed), XR38_SOURCE),
        ]

        refusal = await _xr38_upsert_refused(rates, story)

        message = str(refusal)
        assert FX_CORE_BASE in message and FX_CORE_QUOTE in message and XR38_DAYS[1].isoformat() in message, f"the refusal does not name the pair {FX_CORE_BASE}/{FX_CORE_QUOTE} and the date {XR38_DAYS[1]}: {message!r}"
        assert {"14", "10"} <= _xr38_numbers(message), f"the refusal does not name the limits, 14 digits before the decimal point and 10 decimal places: {message!r}"
        stored = await _xr38_stored()
        assert not stored, f"the call was refused, yet rows were written: {stored}"
        print_success("refused, nothing written")

    async def test_xr38_guard_rates_at_the_limits_are_stored(self):
        """Guard: green today and after. 14 digits before the decimal point and 1E-10 are the limits, not past them, typed
        or reached by the inverse (ISK → BGN 1E-13 is stored BGN/ISK 1E+13, ISK → BGN 1E+10 is 1E-10). Each value is one a
        double holds exactly, so it reads back as typed."""
        print_section("upsert_rates_bulk: rates at the limits stored")
        rates = [
            (XR38_DAYS[0], FX_CORE_BASE, FX_CORE_QUOTE, Decimal("99999999999999"), XR38_SOURCE),
            (XR38_DAYS[1], FX_CORE_BASE, FX_CORE_QUOTE, Decimal("1E-10"), XR38_SOURCE),
            (XR38_DAYS[2], FX_CORE_QUOTE, FX_CORE_BASE, Decimal("1E-13"), XR38_SOURCE),
            (XR38_DAYS[3], FX_CORE_QUOTE, FX_CORE_BASE, Decimal("1E+10"), XR38_SOURCE),
        ]
        async with AsyncSession(get_async_engine()) as session:
            try:
                await upsert_rates_bulk(session, rates)
            except ValueError as refusal:
                pytest.fail(f"rates at the limits were refused: {refusal}")

        stored = await _xr38_stored()
        expected = {
            (FX_CORE_BASE, FX_CORE_QUOTE, XR38_DAYS[0]): Decimal("99999999999999"),
            (FX_CORE_BASE, FX_CORE_QUOTE, XR38_DAYS[1]): Decimal("1E-10"),
            (FX_CORE_BASE, FX_CORE_QUOTE, XR38_DAYS[2]): Decimal("1E+13"),
            (FX_CORE_BASE, FX_CORE_QUOTE, XR38_DAYS[3]): Decimal("1E-10"),
        }
        assert stored == expected, f"rates at the limits read back as {stored}: expected {expected}"
        print_success("stored at the limits")


# ============================================================================
# delete_rates_bulk — portfolio cache invalidation (R2-Fx)
# ============================================================================
#
# delete_rates_bulk() feeds compute_portfolio_fx_cache_identity()'s dependency
# set (backend/app/services/financial_math/portfolio/engine.py): deleting a rate that a
# portfolio depended on must not leave a stale L1 blob / L2 report entry
# alive for the rest of its TTL. A no-op delete (nothing matched) must, by the
# same logic, leave both caches untouched — clearing them on every call,
# including pure misses, would erase every other user's warm cache for no
# reason each time an already-absent rate is "deleted".
#
# The cache sentinel key intentionally does NOT collide with any real
# portfolio blob/report key shape (those are tuples keyed on user_id etc.) —
# it exists only to observe whether clear_cache("portfolio_blob" /
# "portfolio_layer2") ran, not to imitate a real cache entry.
_CACHE_SENTINEL_KEY = ("test_fx_core_cache_invalidation_sentinel",)


@pytest.mark.asyncio
class TestDeleteRatesBulkCacheInvalidation:
    """delete_rates_bulk() must clear the portfolio_layer2 + portfolio_blob TTL
    caches when it actually deletes rows, and must not touch them on a no-op
    delete (existing/deleted count of 0)."""

    def _seed_portfolio_caches(self) -> None:
        portfolio_engine_module._portfolio_blob_cache.set(_CACHE_SENTINEL_KEY, object())
        _portfolio_l2_cache.set(_CACHE_SENTINEL_KEY, object())

    def _portfolio_caches_populated(self) -> bool:
        _, blob_hit = portfolio_engine_module._portfolio_blob_cache.get(_CACHE_SENTINEL_KEY)
        _, l2_hit = _portfolio_l2_cache.get(_CACHE_SENTINEL_KEY)
        return blob_hit and l2_hit

    async def test_successful_deletion_clears_portfolio_caches(self):
        """A delete that actually removes rows (deleted_count_total > 0) must
        clear both portfolio_layer2 and portfolio_blob."""
        print_section("delete_rates_bulk: successful deletion clears portfolio caches")
        engine = get_async_engine()
        today = date.today()
        async with AsyncSession(engine) as session:
            session.add(FxRate(date=today, base=FX_CORE_BASE, quote=FX_CORE_QUOTE, rate=Decimal("1.0"), source="TEST"))
            await session.commit()

        self._seed_portfolio_caches()
        assert self._portfolio_caches_populated(), "test setup: sentinel did not land in both portfolio caches"

        async with AsyncSession(engine) as session:
            results = await delete_rates_bulk(session, [(FX_CORE_BASE, FX_CORE_QUOTE, today, None)])
        success, existing, deleted, _msg = results[0]
        assert success is True
        assert deleted >= 1, "seeded rate was not actually deleted — cache-clear precondition not met"

        assert not self._portfolio_caches_populated(), "a successful rate deletion did not clear the portfolio_layer2/portfolio_blob caches"
        print_success("Successful deletion cleared both portfolio cache layers")

    async def test_noop_deletion_does_not_clear_portfolio_caches(self):
        """A delete request that matches nothing (deleted_count_total == 0) must
        leave both portfolio caches untouched."""
        print_section("delete_rates_bulk: no-op deletion must not clear portfolio caches")
        engine = get_async_engine()

        self._seed_portfolio_caches()
        assert self._portfolio_caches_populated(), "test setup: sentinel did not land in both portfolio caches"

        async with AsyncSession(engine) as session:
            # AAA/ZZZ: not this file's pair, and nothing was seeded for it — a
            # genuine miss, not merely "this file's own rows happen to be absent".
            results = await delete_rates_bulk(session, [("AAA", "ZZZ", date.today(), None)])
        success, existing, deleted, _msg = results[0]
        assert success is True
        assert deleted == 0, "test setup: expected nothing to match so the delete is a genuine no-op"

        assert self._portfolio_caches_populated(), "a no-op deletion (nothing existed to delete) falsely cleared the portfolio caches"
        print_success("No-op deletion left both portfolio cache layers untouched")
