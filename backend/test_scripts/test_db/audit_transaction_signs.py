#!/usr/bin/env python3
"""
Transaction sign audit (read-only diagnostic) for LibreFolio.

Confirms that the persisted ``Transaction`` rows respect the per-type cash-sign
convention enforced by ``validate_transaction_business_rules`` (schemas Rule 11).
When the audit is clean, the FIFO economic stage can assume ``CostTotal = -Amount``
for FEE/TAX without a defensive ``abs()`` on trusted data.

Anomalies reported (mirrors the plan's Fase 0.2 thresholds):
- FEE / TAX with ``amount >= 0``    (should be a cash outflow, < 0)
- BUY with ``amount > 0``           (should be a cash outflow, < 0)
- SELL with ``amount < 0``          (should be a cash inflow,  > 0)
- DIVIDEND / INTEREST with ``amount <= 0`` (should be a cash inflow, > 0)

This script is a **read-only pre-deploy gate**, NOT a permanent automatic test:
it neither imports the test-DB harness nor mutates data. It targets whatever DB
``settings.DATABASE_URL`` points at (production by default; set
``LIBREFOLIO_TEST_MODE=1`` to audit the test DB).

Usage:
    python backend/test_scripts/test_db/audit_transaction_signs.py
    LIBREFOLIO_TEST_MODE=1 python backend/test_scripts/test_db/audit_transaction_signs.py

Exit code: 0 = clean, 1 = anomalies found.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from decimal import Decimal
from typing import Callable

from sqlmodel import Session, select

from backend.app.db.models import Transaction, TransactionType
from backend.app.db.session import get_sync_engine


@dataclass(frozen=True)
class SignRule:
    """One per-type sign expectation and the predicate that flags a violation."""

    label: str
    types: frozenset[TransactionType]
    # Returns True when *amount* is anomalous for this rule.
    is_anomalous: Callable[[Decimal], bool]
    expectation: str


_ZERO = Decimal("0")

SIGN_RULES: list[SignRule] = [
    SignRule(
        label="FEE/TAX amount >= 0",
        types=frozenset({TransactionType.FEE, TransactionType.TAX}),
        is_anomalous=lambda amt: amt >= _ZERO,
        expectation="cash outflow (amount < 0)",
    ),
    SignRule(
        label="BUY amount > 0",
        types=frozenset({TransactionType.BUY}),
        is_anomalous=lambda amt: amt > _ZERO,
        expectation="cash outflow (amount < 0)",
    ),
    SignRule(
        label="SELL amount < 0",
        types=frozenset({TransactionType.SELL}),
        is_anomalous=lambda amt: amt < _ZERO,
        expectation="cash inflow (amount > 0)",
    ),
    SignRule(
        label="DIVIDEND/INTEREST amount <= 0",
        types=frozenset({TransactionType.DIVIDEND, TransactionType.INTEREST}),
        is_anomalous=lambda amt: amt <= _ZERO,
        expectation="cash inflow (amount > 0)",
    ),
]


@dataclass
class RuleReport:
    rule: SignRule
    checked: int
    anomalous_ids: list[int]


def audit_transaction_signs(session: Session) -> list[RuleReport]:
    """Run every sign rule against the DB and return per-rule reports.

    Read-only: issues plain SELECTs, never writes.
    """
    reports: list[RuleReport] = []
    for rule in SIGN_RULES:
        rows = session.exec(select(Transaction.id, Transaction.amount).where(Transaction.type.in_(rule.types))).all()  # type: ignore[attr-defined]
        anomalous = sorted(tx_id for tx_id, amount in rows if rule.is_anomalous(amount))
        reports.append(RuleReport(rule=rule, checked=len(rows), anomalous_ids=anomalous))
    return reports


def _format_report(reports: list[RuleReport]) -> tuple[str, int]:
    """Render a human-readable report. Returns (text, total_anomalies)."""
    lines: list[str] = []
    lines.append("=" * 70)
    lines.append("Transaction sign audit (read-only)")
    lines.append("=" * 70)
    total_anomalies = 0
    for r in reports:
        n = len(r.anomalous_ids)
        total_anomalies += n
        status = "OK  " if n == 0 else "FAIL"
        lines.append(f"[{status}] {r.rule.label:<32} checked={r.checked:<6} anomalies={n}")
        if n:
            lines.append(f"        expected: {r.rule.expectation}")
            preview = ", ".join(str(i) for i in r.anomalous_ids[:50])
            more = "" if n <= 50 else f" … (+{n - 50} more)"
            lines.append(f"        ids: {preview}{more}")
    lines.append("-" * 70)
    verdict = "CLEAN — all transaction signs consistent" if total_anomalies == 0 else f"{total_anomalies} anomalous transaction(s) found"
    lines.append(f"Result: {verdict}")
    lines.append("=" * 70)
    return "\n".join(lines), total_anomalies


def main() -> int:
    engine = get_sync_engine()
    with Session(engine) as session:
        reports = audit_transaction_signs(session)
    text, total = _format_report(reports)
    print(text)
    return 0 if total == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
