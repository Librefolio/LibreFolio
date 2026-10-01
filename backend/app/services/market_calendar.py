"""Market holidays, and the rule that tells a stored carry from a quote (developer's decision of 30/09/2026).

Some price sources store a row for every calendar day: a Saturday or Sunday row that repeats Friday's close,
and the same on exchange holidays. Read as quotes, those rows put zero-return observations into every calendar
built from them — the portfolio's own TWRR has one point per calendar day by construction — so a «day» became a
calendar day and a «month» of 21 observations about three weeks. The rule: **a row dated on a weekend or on a
market holiday whose close equals exactly the close of the row before it is a carry, not a quote.** Only
weekends and holidays, and only exact repeats: a crypto that moves on Saturday stays a quote, and so does a
genuinely flat weekday (a bond, a money-market fund).

Market holidays are the **union** of the weekday holidays of the main exchanges, read from QuantLib's
calendars. The union is safe because the rule also requires the exact repeat: an exchange that traded that day
moved its price, and the day stays. The web process never imports QuantLib (decision
`risk-quant-engine-process-boundary`), so the table is built in a separate ``spawn`` process — started in the
background at application startup and awaited by the first computation that needs it — and then kept in memory
as a plain set of dates.

One module for risk and signals alike: the rule has one definition.
"""

from __future__ import annotations

import asyncio
import multiprocessing
import time
from collections.abc import Set as AbstractSet
from datetime import date
from multiprocessing.connection import Connection
from multiprocessing.process import BaseProcess
from typing import Any, Optional

from backend.app.logging_config import get_logger

logger = get_logger(__name__)

MARKET_HOLIDAY_YEARS: tuple[int, int] = (1970, 2100)
"""Inclusive range of the holiday table. QuantLib's calendars cover it; beyond it only weekends apply."""

BUILD_TIMEOUT_SECONDS = 120.0
RETRY_AFTER_SECONDS = 600.0
"""After a failed build, how long weekends alone apply before the next computation tries again."""


def is_market_closed_repeat(day: date, close: Any, previous_close: Any, holidays: AbstractSet[date]) -> bool:
    """Whether a stored row is a carry: dated on a weekend or a market holiday, and repeating the close before it."""
    if previous_close is None:
        return False
    if day.weekday() < 5 and day not in holidays:
        return False
    return close == previous_close


def build_market_holidays(first_year: int, last_year: int) -> list[str]:
    """The union of the weekday holidays of the main exchanges, as sorted ISO dates.

    Runs QuantLib, so it is only ever called in the build process (or in a test process), never in the web
    process. Weekends are left out: the rule treats every weekend as a potential closed day anyway.
    """
    import QuantLib as ql  # noqa: PLC0415 — only in the build process: the web process never imports QuantLib

    calendars = (
        ql.TARGET(),
        ql.Italy(ql.Italy.Exchange),
        ql.Germany(ql.Germany.Xetra),
        ql.France(ql.France.Exchange),
        ql.UnitedKingdom(ql.UnitedKingdom.Exchange),
        ql.Switzerland(),
        ql.UnitedStates(ql.UnitedStates.NYSE),
    )
    start, end = ql.Date(1, 1, first_year), ql.Date(31, 12, last_year)
    days: set[str] = set()
    for calendar in calendars:
        for day in calendar.holidayList(start, end, False):
            days.add(date(day.year(), day.month(), day.dayOfMonth()).isoformat())
    return sorted(days)


def _child_main(connection: Connection, first_year: int, last_year: int) -> None:
    """Entry point of the build process: send the table, or the reason there is none, and exit."""
    try:
        connection.send(("ok", build_market_holidays(first_year, last_year)))
    except BaseException as exc:  # noqa: BLE001 — report every failure to the parent instead of leaving it waiting
        connection.send(("error", f"{type(exc).__name__}: {exc}"))
    finally:
        connection.close()


_holidays: Optional[frozenset[date]] = None
_failed_at: Optional[float] = None
_build_task: Optional[asyncio.Task[frozenset[date]]] = None
_build_loop: Optional[asyncio.AbstractEventLoop] = None
_process: Optional[BaseProcess] = None


def _stop(process: BaseProcess) -> None:
    """End the build process now, without waiting for it to finish its work."""
    if process.is_alive():
        process.terminate()
        process.join(0.5)
        if process.is_alive():
            process.kill()
    process.join(0.5)


async def _build_in_subprocess(first_year: int, last_year: int) -> list[str]:
    """Build the table in a separate ``spawn`` process and return it; the process is gone when this returns."""
    global _process
    context = multiprocessing.get_context("spawn")
    receiver, sender = context.Pipe(duplex=False)
    process = context.Process(target=_child_main, args=(sender, first_year, last_year), name="librefolio-market-holidays", daemon=True)
    process.start()
    sender.close()
    _process = process
    try:
        if not await asyncio.to_thread(receiver.poll, BUILD_TIMEOUT_SECONDS):
            raise TimeoutError(f"market holiday build took longer than {BUILD_TIMEOUT_SECONDS:.0f} s")
        status, payload = await asyncio.to_thread(receiver.recv)
    finally:
        receiver.close()
        await asyncio.to_thread(_stop, process)
        if _process is process:
            _process = None
    if status != "ok":
        raise RuntimeError(f"market holiday build failed: {payload}")
    return list(payload)


async def _build_and_store() -> frozenset[date]:
    global _holidays, _failed_at
    try:
        days = await _build_in_subprocess(*MARKET_HOLIDAY_YEARS)
    except asyncio.CancelledError:
        raise
    except Exception:
        _failed_at = time.monotonic()
        logger.exception("Market holiday table could not be built; weekends alone apply until the next attempt")
        return frozenset()
    _holidays = frozenset(date.fromisoformat(day) for day in days)
    _failed_at = None
    logger.info("Market holiday table built", holidays=len(_holidays), years=MARKET_HOLIDAY_YEARS)
    return _holidays


async def ensure_market_holidays() -> frozenset[date]:
    """The market holiday table: built once per process, shared by every caller that needs it meanwhile.

    Returns an empty set — weekends alone — after a failed build, until ``RETRY_AFTER_SECONDS`` have passed.
    """
    global _build_task, _build_loop
    if _holidays is not None:
        return _holidays
    if _failed_at is not None and time.monotonic() - _failed_at < RETRY_AFTER_SECONDS:
        return frozenset()
    loop = asyncio.get_running_loop()
    if _build_task is None or _build_task.done() or _build_loop is not loop:
        _build_task = loop.create_task(_build_and_store())
        _build_loop = loop
    return await asyncio.shield(_build_task)


def start_market_holiday_prewarm() -> asyncio.Task[frozenset[date]]:
    """Start the build in the background, off the request path; the first computation that needs it awaits it."""
    return asyncio.get_running_loop().create_task(ensure_market_holidays())


async def shutdown_market_holidays() -> None:
    """Stop a build in progress at once: shutdown never waits for it, and leaves no build process behind."""
    process = _process
    if process is not None:
        await asyncio.to_thread(_stop, process)
    task = _build_task
    if task is not None and not task.done():
        task.cancel()


__all__ = [
    "MARKET_HOLIDAY_YEARS",
    "build_market_holidays",
    "ensure_market_holidays",
    "is_market_closed_repeat",
    "shutdown_market_holidays",
    "start_market_holiday_prewarm",
]
