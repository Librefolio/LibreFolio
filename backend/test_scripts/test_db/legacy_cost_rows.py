#!/usr/bin/env python3
"""
Legacy acquisitions without a cost basis, written straight into the lane's test database.

What it simulates. Before the cost basis became mandatory, LibreFolio stored a TRANSFER pair, or
an ADJUSTMENT adding quantity, like any other movement: no ``cost_basis_override``, no
``cost_basis_currency``, no cash. Today the app refuses to save either row without a cost basis
(``COST_BASIS_REQUIRED``: ``transaction_service.py`` and ``transaction_batch_stages.py``), so
such rows exist only in data an older version left behind — and that is exactly the data the
dashboard's yellow banner must flag (release checklist item 22, issue #32). The API cannot
create them any more, so this module writes them the way an old version stored them.

Who uses it. ``frontend/e2e/portfolio/data-quality-legacy.spec.ts`` and Y2 of
``frontend/e2e/portfolio/yield-on-cost-real.spec.ts``: each spec creates a disposable account, its
two brokers and its two assets through the API, calls this module to add the legacy rows, and
deletes everything in its teardown — the brokers with ``force``, which takes
these rows with them. The backend side of the same shapes is proven by
``test_portfolio_cost_currency.py`` (S7, L4).

What it writes, in ONE database transaction, exactly as an old version would have stored it
(amount 0, no currency, no cost basis, no asset event):

- TRANSFER ``-transfer_qty`` of the transfer asset at the source broker, and TRANSFER
  ``+transfer_qty`` at the destination broker, linked to each other both ways;
- ADJUSTMENT ``+adjustment_qty`` of the adjustment asset at the destination broker.

Every description carries ``--marker``. On success it prints ONE line of JSON to stdout,
``{"transfer_out": id, "transfer_in": id, "adjustment_in": id}``, and exits 0.

Safety: the lane's test database only. ``setup_test_database()`` runs before anything else of
the app is imported and reads the lane from ``TEST_PORT`` / ``LIBREFOLIO_TEST_DATA_DIR`` (both
exported by ``frontend/playwright.config.ts``), refusing a production data directory;
``verify_test_database()`` must then confirm the URL, and the database file must already exist.
Both brokers must be owned (role OWNER) by ``--user-id`` and both assets must exist. If anything
is refused, nothing is written.

Exit codes:
    0  the rows were written (their ids are on stdout);
    2  not this lane's test database, or a usage error (argparse);
    3  a guard refused the request.

Usage:
    python -m backend.test_scripts.test_db.legacy_cost_rows --user-id 7 --source-broker 11 --dest-broker 12 \\
        --transfer-asset 21 --adjustment-asset 22 --date 2026-09-12 --marker "E2E legacy-cost 123abc"
"""

import sys

# Before any other app import: point the app at this lane's test database (refusing production).
from backend.test_scripts.test_db_config import get_test_db_path, setup_test_database, verify_test_database

try:
    setup_test_database()
except ValueError as exc:
    print(f"legacy_cost_rows: refused, not a test lane: {exc}", file=sys.stderr)
    raise SystemExit(2) from exc

import argparse
import json
from datetime import date
from decimal import Decimal, InvalidOperation

from sqlalchemy import create_engine
from sqlalchemy.pool import NullPool
from sqlmodel import Session, select

from backend.app.config import get_settings
from backend.app.db.models import Asset, BrokerUserAccess, Transaction, TransactionType, UserRole

EXIT_NOT_TEST_DATABASE = 2
EXIT_REFUSED = 3


def _positive_decimal(text: str) -> Decimal:
    try:
        value = Decimal(text)
    except InvalidOperation as exc:
        raise argparse.ArgumentTypeError(f"not a decimal: {text!r}") from exc
    if not value.is_finite() or value <= 0:
        raise argparse.ArgumentTypeError(f"must be a positive quantity: {text!r}")
    return value


def _iso_date(text: str) -> date:
    try:
        return date.fromisoformat(text)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"not an ISO date (YYYY-MM-DD): {text!r}") from exc


def _marker(text: str) -> str:
    if not text.strip():
        raise argparse.ArgumentTypeError("the marker must not be blank")
    return text


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="python -m backend.test_scripts.test_db.legacy_cost_rows",
        description="Write a TRANSFER pair and an ADJUSTMENT-in without cost basis into the lane's test database, as a version before the cost basis became mandatory stored them.",
    )
    parser.add_argument("--user-id", type=int, required=True, help="the account that must own both brokers (role OWNER)")
    parser.add_argument("--source-broker", type=int, required=True, help="broker the transferred units leave")
    parser.add_argument("--dest-broker", type=int, required=True, help="broker the transferred units reach, and where the adjustment lands")
    parser.add_argument("--transfer-asset", type=int, required=True, help="asset moved by the TRANSFER pair")
    parser.add_argument("--adjustment-asset", type=int, required=True, help="asset added by the ADJUSTMENT")
    parser.add_argument("--date", type=_iso_date, required=True, help="settlement date of the three rows (YYYY-MM-DD)")
    parser.add_argument("--transfer-qty", type=_positive_decimal, default=Decimal("4"), help="units transferred (default 4)")
    parser.add_argument("--adjustment-qty", type=_positive_decimal, default=Decimal("5"), help="units added by the adjustment (default 5)")
    parser.add_argument("--marker", type=_marker, required=True, help="text carried by every row's description")
    return parser.parse_args(argv)


def _refusals(session: Session, args: argparse.Namespace) -> list[str]:
    """Why the request must not be written: an empty list means every guard passed."""
    problems: list[str] = []
    if args.source_broker == args.dest_broker:
        problems.append(f"the source and destination brokers must differ (both {args.source_broker})")
    for broker_id in dict.fromkeys((args.source_broker, args.dest_broker)):
        owner = session.exec(select(BrokerUserAccess).where(BrokerUserAccess.broker_id == broker_id, BrokerUserAccess.user_id == args.user_id, BrokerUserAccess.role == UserRole.OWNER)).first()
        if owner is None:
            problems.append(f"broker {broker_id} is not owned (role OWNER) by user {args.user_id}")
    for asset_id in dict.fromkeys((args.transfer_asset, args.adjustment_asset)):
        if session.get(Asset, asset_id) is None:
            problems.append(f"asset {asset_id} does not exist")
    return problems


def _legacy_row(*, broker_id: int, asset_id: int, tx_type: TransactionType, day: date, quantity: Decimal, description: str) -> Transaction:
    """A movement of units the way a version before the mandatory cost basis stored it."""
    return Transaction(
        broker_id=broker_id,
        asset_id=asset_id,
        type=tx_type,
        date=day,
        quantity=quantity,
        amount=Decimal("0"),
        currency=None,
        cost_basis_override=None,
        cost_basis_currency=None,
        asset_event_id=None,
        description=description,
    )


def _write_legacy_rows(session: Session, args: argparse.Namespace) -> dict[str, int]:
    """The three rows, in the session's single transaction: the pair, linked both ways, then the adjustment."""
    transfer_out = _legacy_row(broker_id=args.source_broker, asset_id=args.transfer_asset, tx_type=TransactionType.TRANSFER, day=args.date, quantity=-args.transfer_qty, description=f"{args.marker} legacy transfer out")
    transfer_in = _legacy_row(broker_id=args.dest_broker, asset_id=args.transfer_asset, tx_type=TransactionType.TRANSFER, day=args.date, quantity=args.transfer_qty, description=f"{args.marker} legacy transfer in")
    session.add(transfer_out)
    session.add(transfer_in)
    session.flush()
    # A linked pair references itself both ways: the ids exist only after the first flush.
    transfer_out.related_transaction_id = transfer_in.id
    transfer_in.related_transaction_id = transfer_out.id
    session.flush()
    adjustment_in = _legacy_row(broker_id=args.dest_broker, asset_id=args.adjustment_asset, tx_type=TransactionType.ADJUSTMENT, day=args.date, quantity=args.adjustment_qty, description=f"{args.marker} legacy adjustment in")
    session.add(adjustment_in)
    session.flush()
    return {"transfer_out": transfer_out.id, "transfer_in": transfer_in.id, "adjustment_in": adjustment_in.id}


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)

    ok, url = verify_test_database()
    if not ok:
        print(f"legacy_cost_rows: refused, {url} is not this lane's test database (LIBREFOLIO_TEST_MODE / LIBREFOLIO_TEST_DATA_DIR); nothing written", file=sys.stderr)
        return EXIT_NOT_TEST_DATABASE
    db_path = get_test_db_path()
    if not db_path.is_file():
        # SQLite would create an empty file on connect: a lane without a database is refused, not initialised.
        print(f"legacy_cost_rows: refused, no test database at {db_path}; nothing written", file=sys.stderr)
        return EXIT_NOT_TEST_DATABASE

    # The backend runs on the same file (WAL, busy_timeout 30 s): a short write beside it waits its turn.
    engine = create_engine(get_settings().DATABASE_URL, poolclass=NullPool, connect_args={"timeout": 30})
    try:
        with Session(engine) as session:
            problems = _refusals(session, args)
            if problems:
                print("legacy_cost_rows: refused, nothing written: " + "; ".join(problems), file=sys.stderr)
                return EXIT_REFUSED
            ids = _write_legacy_rows(session, args)
            session.commit()
    finally:
        engine.dispose()

    print(json.dumps(ids))
    return 0


if __name__ == "__main__":
    sys.exit(main())
