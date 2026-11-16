"""Format checks of BCB's feed C (D10): the PTAX closing CSV of one currency over a period.

A row is ``ddmmyyyy;<BCB code>;<A|B>;<symbol>;<cotação compra>;<cotação venda>;<paridade compra>;<paridade venda>``:
no header, ``;``-separated, decimal comma, the BCB code without leading zeros. Anything else in the shape of a row (a
field count, a date, a code, a symbol, a type) means the feed changed: one ``FXServiceError`` for the whole answer, no
rate. A value that is no number loses its day only (X-R50). See ``studio-BCB.md`` §5.
"""

from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import NamedTuple

from backend.app.logging_config import get_logger
from backend.app.services.fx.base import FXServiceError

logger = get_logger(__name__)

#: The text of BCB's «no data» page (HTTP 200, HTML): an empty range or an unknown ChkMoeda id.
NO_DATA_TEXT = "Não existe informação"
#: A range this long with no bulletin is no holiday: the ChkMoeda id has probably changed.
NO_DATA_IS_AN_ERROR_FROM_DAYS = 7


class BcbRow(NamedTuple):
    """One bulletin row: the day, the type (A: paridade = units per 1 USD, B: USD per 1 unit) and the four values."""

    day: date
    kind: str
    cotacao_compra: Decimal | None
    cotacao_venda: Decimal | None
    paridade_compra: Decimal | None
    paridade_venda: Decimal | None


def is_html(body: str, content_type: str) -> bool:
    return "html" in content_type.lower() or body.lstrip()[:1] == "<"


def check_html(body: str, symbol: str, start: date, end: date) -> None:
    """An HTML answer: BCB's «no data» page on a short range is no rate (returns); on a range of
    ``NO_DATA_IS_AN_ERROR_FROM_DAYS`` days or more, or any other page, an ``FXServiceError``."""
    if NO_DATA_TEXT in body and "msgErro" in body:
        days = (end - start).days + 1
        if days < NO_DATA_IS_AN_ERROR_FROM_DAYS:
            return
        raise FXServiceError(f"BCB has no bulletin for {symbol} in {days} days ({start} to {end}): its ChkMoeda id has probably changed")
    raise FXServiceError(f"BCB answer for {symbol} is an HTML page, not the CSV (endpoint changed or request refused)")


def _number(text: str) -> Decimal | None:
    try:
        value = Decimal(text.strip().replace(",", "."))
    except InvalidOperation:
        return None
    return value if value.is_finite() and value > 0 else None


def read_rows(body: str, bcb_code: int, symbol: str, start: date, end: date) -> list[BcbRow]:
    """The rows of ``body`` dated within ``[start, end]``, one per day: a day seen twice is dropped (never seen after
    1999), a row outside the range ignored. Raises ``FXServiceError`` when a row is not the shape of this currency's CSV."""
    rows: dict[date, BcbRow] = {}
    doubled: set[date] = set()
    for line in body.splitlines():
        if not line.strip():
            continue
        fields = line.strip().split(";")
        if len(fields) != 8:
            raise FXServiceError(f"BCB answer for {symbol} is not the expected CSV: {len(fields)} fields in {line[:60]!r}")
        try:
            day = datetime.strptime(fields[0], "%d%m%Y").date()
            code = int(fields[1])
        except ValueError:
            raise FXServiceError(f"BCB answer for {symbol} is not the expected CSV: unreadable date or code in {line[:60]!r}") from None
        if code != bcb_code or fields[3].strip() != symbol:
            raise FXServiceError(f"BCB answer for {symbol} carries another currency ({fields[1]} {fields[3]!r}, expected {bcb_code} {symbol!r})")
        if fields[2] not in ("A", "B"):
            raise FXServiceError(f"BCB answer for {symbol} has an unknown type {fields[2]!r}")
        if not start <= day <= end:
            continue
        if day in rows:
            doubled.add(day)
            continue
        rows[day] = BcbRow(day, fields[2], *(_number(f) for f in fields[4:8]))
    for day in doubled:
        logger.warning(f"BCB: {symbol} has two bulletins on {day}: the day is dropped")
        rows.pop(day)
    return [rows[day] for day in sorted(rows)]


def mean(first: Decimal | None, second: Decimal | None) -> Decimal | None:
    """The mean of compra and venda (the convention of the other providers), or None when either is unreadable."""
    if first is None or second is None:
        return None
    return (first + second) / 2
