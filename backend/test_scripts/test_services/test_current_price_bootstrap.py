"""
Test Suite: F.2/F.3 OHLC bootstrap + intra-day extend (unit)

Covers Phase 7 Part 3 Blocco F.2 (new-row bootstrap) and F.3 (intra-day
extend) at the helper level: ``AssetSourceManager._extend_ohlc_bounds``.

The helper returns a *patch dict* — only fields that must change, so
callers (currently ``get_current_prices_bulk``) can ``setattr`` them on
the ORM row without clobbering stable columns.

Spec: ``backend/app/services/asset_source.py::_extend_ohlc_bounds`` (L2968+).

Rules under test:
- ``low``    = min(existing.low, new_close)  when existing.low is set; else new_close
- ``high``   = max(existing.high, new_close) when existing.high is set; else new_close
- ``open``   = new_close only when existing.open is None (first tick of the day)
- ``volume`` untouched (absent from patch)
- ``close``  NOT in patch (caller decides whether to overwrite)

Related plan: ``plan-phase07-transaction-Part3_1_Closure_2-BlockG.prompt.md``
              §G.6b (G-batch1).
"""

from dataclasses import dataclass
from decimal import Decimal
from typing import Optional

from backend.app.services.asset_source import AssetSourceManager
from backend.test_scripts.test_utils import print_section, print_success

# ---------------------------------------------------------------------------
# Minimal stand-in for a PriceHistory ORM row.
# The helper only reads ``existing.open / high / low``, so a dataclass is
# enough — no DB session, no real SQLModel instance required.
# ---------------------------------------------------------------------------


@dataclass
class _FakePriceRow:
    open: Optional[Decimal] = None
    high: Optional[Decimal] = None
    low: Optional[Decimal] = None
    volume: Optional[Decimal] = None


def _call(existing: _FakePriceRow, new_close: str) -> dict:
    """Thin wrapper to keep test bodies readable."""
    return AssetSourceManager._extend_ohlc_bounds(existing, Decimal(new_close))


# ===========================================================================
# G.6b.1 — F.2 bootstrap: fully empty row -> all 3 bounds pinned to new_close
# ===========================================================================


def test_extend_bootstrap_empty_row():
    """Existing row with open/high/low = None (e.g. freshly inserted bucket).

    F.2 wants bootstrap semantics: the first tick widens all three bounds
    to new_close. ``volume`` must NOT appear in the patch.
    """
    print_section("G.6b.1 - F.2 bootstrap on empty row")

    patch = _call(_FakePriceRow(), "50")

    assert patch == {"open": Decimal("50"), "high": Decimal("50"), "low": Decimal("50")}, f"empty row should produce open=high=low=new_close, got {patch}"
    assert "volume" not in patch, "volume must never be touched by _extend_ohlc_bounds"
    assert "close" not in patch, "close is NOT in the patch (caller decides)"
    print_success("bootstrap: open=high=low=50, no volume/close in patch")


# ===========================================================================
# G.6b.2 — F.3 low widens downward
# ===========================================================================


def test_extend_low_widens_when_tick_below():
    """existing.low=45, new_close=40 -> patch {'low': 40} only."""
    print_section("G.6b.2 - F.3 low widens downward")

    patch = _call(
        _FakePriceRow(open=Decimal("48"), high=Decimal("50"), low=Decimal("45")),
        "40",
    )
    assert patch == {"low": Decimal("40")}, f"expected only low update, got {patch}"
    print_success("low widened to 40; open/high/volume preserved")


# ===========================================================================
# G.6b.3 — F.3 high widens upward
# ===========================================================================


def test_extend_high_widens_when_tick_above():
    """existing.high=55, new_close=60 -> patch {'high': 60} only."""
    print_section("G.6b.3 - F.3 high widens upward")

    patch = _call(
        _FakePriceRow(open=Decimal("50"), high=Decimal("55"), low=Decimal("48")),
        "60",
    )
    assert patch == {"high": Decimal("60")}, f"expected only high update, got {patch}"
    print_success("high widened to 60; open/low/volume preserved")


# ===========================================================================
# G.6b.4 — F.3 inside-bounds tick produces empty patch
# ===========================================================================


def test_extend_no_change_when_tick_inside_bounds():
    """existing bounds 45..55, new_close=50 inside -> patch = {} (no-op)."""
    print_section("G.6b.4 - inside-bounds tick produces empty patch")

    patch = _call(
        _FakePriceRow(open=Decimal("48"), high=Decimal("55"), low=Decimal("45")),
        "50",
    )
    assert patch == {}, f"tick inside bounds must produce empty patch, got {patch}"
    print_success("empty patch as expected — caller will still setattr nothing")


# ===========================================================================
# G.6b.5 — F.2/F.3 open preserved when set
# ===========================================================================


def test_extend_open_preserved_if_already_set():
    """existing.open=48, new_close=50 -> 'open' NOT in patch (only first tick sets open)."""
    print_section("G.6b.5 - open is preserved once set (F.2 first-tick only)")

    patch = _call(
        _FakePriceRow(open=Decimal("48"), high=Decimal("55"), low=Decimal("45")),
        "50",
    )
    assert "open" not in patch, f"open must not be in patch when already set, got {patch}"
    print_success("open=48 preserved; only the first tick-of-the-day sets open")


# ===========================================================================
# G.6b.6 — open written only when None (partial bootstrap)
# ===========================================================================


def test_extend_open_set_when_missing_even_if_bounds_exist():
    """existing.open=None + existing.high=55 + existing.low=45 -> patch contains open=new_close.

    This covers the partial-bootstrap edge case (the bucket had high/low
    from another pathway but open was never filled in, e.g. future F.5
    manual edits via sentinel).
    """
    print_section("G.6b.6 - open is filled when missing, even if bounds are set")

    patch = _call(
        _FakePriceRow(open=None, high=Decimal("55"), low=Decimal("45")),
        "50",
    )
    assert patch.get("open") == Decimal("50"), f"open should be set to 50 (first tick), got {patch.get('open')}"
    # low/high already set and 50 is inside them -> no change expected on those.
    assert "low" not in patch
    assert "high" not in patch
    print_success("open bootstrapped to 50; existing low/high left intact")


# ===========================================================================
# G.6b.7 — tick equal to existing boundary produces no widen
# ===========================================================================


def test_extend_tick_equal_boundary_is_noop():
    """Strict inequality: new_close == existing.low must NOT produce 'low' in patch.

    The helper uses ``new_close < existing.low`` / ``new_close > existing.high``,
    so an equal tick does not widen.
    """
    print_section("G.6b.7 - tick equal to existing bound is a no-op")

    patch = _call(
        _FakePriceRow(open=Decimal("48"), high=Decimal("55"), low=Decimal("45")),
        "45",
    )
    assert "low" not in patch, f"equal low should not widen, got {patch}"
    assert "high" not in patch
    print_success("equal-boundary tick produced empty patch")


# ===========================================================================
# G.6b.8 — both bounds widen on the same tick
# ===========================================================================


def test_extend_bounds_widen_both_sides_when_new_low():
    """open=None + high=50 + low=40, tick=35 -> patch has low and open (high stays)."""
    print_section("G.6b.8 - new low + open bootstrap in same call")

    patch = _call(
        _FakePriceRow(open=None, high=Decimal("50"), low=Decimal("40")),
        "35",
    )
    assert patch.get("low") == Decimal("35"), f"low should widen to 35, got {patch.get('low')}"
    assert patch.get("open") == Decimal("35"), f"open should bootstrap to 35, got {patch.get('open')}"
    assert "high" not in patch, "high should stay at 50"
    print_success("both low widened and open bootstrapped in a single call")
