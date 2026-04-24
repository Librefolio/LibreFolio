"""
Backup export service — shared helpers for streaming CSV / JSON snapshots.

Used by the ``/api/v1/backup/*`` endpoints to produce large, memory-safe
exports of historical market data (prices, events, FX rates) before
destructive operations (currency change, asset deletion, pair teardown).

Design goals
------------
* **Streaming**: never materialise the full row set in memory; yield chunks
  suitable for ``StreamingResponse``.
* **Uniform envelope**: JSON responses share a common wrapper
  ``{scope, entity, exported_at, row_count, rows: [...]}`` so tooling can
  ingest any backup regardless of the data family.
* **Stable schemas**: column order is fixed and documented per scope; callers
  (frontend download links, tests) rely on this.
* **Decimal/date safety**: numeric values are serialised as strings to
  preserve full precision; dates/datetimes use ISO-8601.

Not covered here
----------------
Authorisation, asset/FX lookup and 404 handling remain in the router layer
(they need request-scoped dependencies). This module only turns an
iterable of ORM rows into streamable bytes.
"""

from __future__ import annotations

import csv
import io
import json
from collections.abc import Iterable, Iterator
from datetime import UTC, datetime
from decimal import Decimal
from enum import StrEnum
from typing import Any, Optional


class BackupScope(StrEnum):
    """Logical family of the exported series (encoded in the JSON envelope)."""

    PRICES = "prices"
    EVENTS = "events"
    FX_RATES = "fx_rates"


def _to_str(value: Any) -> Optional[str]:
    """Render a scalar for CSV/JSON output, preserving precision."""
    if value is None:
        return None
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)


def slugify_for_filename(raw: str, fallback: str) -> str:
    """Lowercase, non-alnum → ``-``, max 60 chars. Empty → ``fallback``."""
    slug = "".join(c if c.isalnum() else "-" for c in raw.lower()).strip("-")[:60]
    return slug or fallback


# ---------------------------------------------------------------------------
# CSV streaming
# ---------------------------------------------------------------------------


def stream_rows_as_csv(fieldnames: list[str], rows: Iterable[dict[str, Any]]) -> Iterator[str]:
    """Yield CSV chunks (header first, then one line per row).

    ``rows`` is consumed lazily; pass a generator to avoid buffering.
    """
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=fieldnames)
    writer.writeheader()
    yield buf.getvalue()
    buf.seek(0)
    buf.truncate(0)
    for row in rows:
        # Normalise every value to its string form — csv.DictWriter cannot
        # serialise Decimal/datetime reliably across locales.
        writer.writerow({k: _to_str(row.get(k)) for k in fieldnames})
        yield buf.getvalue()
        buf.seek(0)
        buf.truncate(0)


# ---------------------------------------------------------------------------
# JSON streaming (uniform envelope)
# ---------------------------------------------------------------------------


def stream_rows_as_json(
    scope: BackupScope,
    entity: dict[str, Any],
    rows: list[dict[str, Any]],
) -> Iterator[str]:
    """Yield a JSON envelope with ``rows`` streamed as an array.

    Layout::

        {
          "scope": "<BackupScope>",
          "entity": {...},
          "exported_at": "2026-04-23T10:20:00Z",
          "row_count": N,
          "rows": [ {...}, {...}, ... ]
        }

    ``rows`` is a fully materialised list because its length is needed
    up-front for ``row_count`` and we want the envelope self-describing
    even for a single-shot download. For very large series (>1M rows)
    a future iteration can switch to chunked encoding with an unknown
    ``row_count`` trailer; not needed at current data volumes.
    """
    exported_at = datetime.now(tz=UTC).isoformat().replace("+00:00", "Z")
    header = {
        "scope": scope.value,
        "entity": entity,
        "exported_at": exported_at,
        "row_count": len(rows),
    }
    # Emit the envelope manually so the rows array can be streamed without
    # holding one huge string in memory.
    header_json = json.dumps(header, separators=(",", ":"), default=str)
    # Strip the closing brace — we'll append rows + close ourselves.
    assert header_json.endswith("}")
    yield header_json[:-1] + ',"rows":['
    for idx, row in enumerate(rows):
        if idx > 0:
            yield ","
        # Ensure Decimals/dates are serialisable.
        normalised = {k: _to_str(v) if isinstance(v, (Decimal, datetime)) or hasattr(v, "isoformat") else v for k, v in row.items()}
        yield json.dumps(normalised, separators=(",", ":"), default=str)
    yield "]}"


# ---------------------------------------------------------------------------
# Column schemas (kept here so tests can import them by name)
# ---------------------------------------------------------------------------

PRICE_COLUMNS = [
    "date",
    "open",
    "high",
    "low",
    "close",
    "volume",
    "currency",
    "source_plugin_key",
    "fetched_at",
]

EVENT_COLUMNS = [
    "date",
    "type",
    "value",
    "currency",
    "source",  # derived: "MANUAL" if provider_assignment_id IS NULL else "PROVIDER"
    "provider_assignment_id",
    "notes",
    "created_at",
    "updated_at",
]

FX_RATE_COLUMNS = [
    "date",
    "base",
    "quote",
    "rate",
    "source",
    "fetched_at",
]
