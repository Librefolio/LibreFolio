"""Crédit Agricole: the combined file.

``combine`` writes the analysis of a set (``_report_set.py``) as one table, a line per fact; ``parse`` reads that table back and
books it (``_booking.py``). The table is the only thing the import sees: it carries every source figure as the bank wrote it
(``securities:<column>``, ``account:<column>``), and what the set decided about it (``lf_*``).

A line is one of:

- ``pair``: a securities row and the account row it is the same fact as (a coupon, a purchase, a fund redemption, a maturity);
- ``standalone``: a row that is imported on its own (an account row, a transfer from another dossier, a securities row inside a
  hole of the account);
- ``excluded``: a row that is not imported, with the reason;
- ``truth_cash``, ``truth_position``, ``verification``: what the bank states, which the gap-fix compares with LibreFolio.

Number and account identifiers (the dossier, the supporting account) are never copied into it.
"""

from __future__ import annotations

import csv
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

import structlog

from backend.app.schemas.brim import (
    BRIMAbsorbed,
    BRIMCheckpoint,
    BRIMCombinedTable,
    BRIMEvidence,
    BRIMNotice,
    BRIMParseOutput,
    BRIMTruthCash,
    BRIMTruthPosition,
    BRIMVerification,
)
from backend.app.services.brim import brim_report_set_core as core
from backend.app.services.brim.brim_provider import BRIMParseError, BRIMProvider
from backend.app.services.brim_providers.broker_credit_agricole._booking import ACCOUNT_SHEET_HEADER, SECURITIES_EVIDENCE_HEADERS, Booking, sheet_row
from backend.app.services.brim_providers.broker_credit_agricole._report_set import (
    PAIRED_ACCOUNT,
    PAIRED_SECURITIES,
    ZONE_BEFORE,
    ZONE_GAP,
    Analysis,
    account_isin,
    account_name,
    classify_account,
    classify_securities,
)
from backend.app.services.brim_providers.broker_credit_agricole._rows import (
    ACCOUNT_COLUMNS,
    SECURITIES_COLUMNS,
    AccountRow,
    SecuritiesRow,
    account_from_cells,
    securities_from_cells,
)

logger = structlog.get_logger(__name__)

LF_COLUMNS = ("lf_row_kind", "lf_zone", "lf_reason", "lf_checkpoint", "lf_source", "lf_match_key", "lf_value", "lf_currency", "lf_proof")
COMBINED_HEADERS = [*LF_COLUMNS, *(f"securities:{column}" for column in SECURITIES_COLUMNS), *(f"account:{column}" for column in ACCOUNT_COLUMNS)]
#: What tells a combined file of this plugin from an export: its own columns.
COMBINED_MARKERS = ("lf_row_kind", "lf_source", "securities:Causale", "account:Descrizione")
TRUTH_KINDS = ("truth_cash", "truth_position", "verification")

ZERO = Decimal("0")
DEFAULT_CURRENCY = "EUR"

#: The order the notices of the rows left out come in.
EXCLUDED_ORDER = ("no_counterpart", "ambiguous", "not_yet_settled", "outside_cash_coverage", "superseded")
EXCLUDED_MESSAGES = {
    "no_counterpart": "{n} righe senza la riga corrispondente nell'altro file: non vengono importate.",
    "ambiguous": "{n} righe che non si possono abbinare con certezza all'altro file: non vengono importate.",
    "not_yet_settled": "{n} operazioni si regolano dopo l'ultimo giorno del file del conto: arriveranno con la prossima importazione.",
    "outside_cash_coverage": "{n} operazioni si sono regolate in giorni che nessun file del conto copre: non vengono importate.",
    "superseded": "{n} righe sono state sostituite da un file più completo che copre gli stessi giorni.",
}
EXCLUDED_COMMENTS = {
    "no_counterpart": "Questa riga dovrebbe comparire anche nell'altro file e non c'è: importarla da sola conterebbe due volte il denaro o lo lascerebbe senza cassa. Se è un movimento vero, inseriscilo a mano.",
    "ambiguous": "Più righe dell'altro file potrebbero essere la stessa operazione e non c'è modo di scegliere senza indovinare. Se sono movimenti veri, inseriscili a mano.",
    "not_yet_settled": "Il denaro di queste operazioni passa dal conto dopo l'ultimo giorno che hai scaricato: le righe del conto arriveranno con il prossimo estratto.",
    "outside_cash_coverage": "Il conto non ha righe per il giorno in cui queste operazioni si sono regolate, quindi il denaro non si vede. Scarica il conto per quel periodo, o inseriscile a mano.",
    "superseded": "Un altro file scaricato per gli stessi giorni ha più righe di questo: si usa quello.",
}
EXCLUDED_SEVERITY = {"not_yet_settled": "info", "superseded": "info"}

Line = Tuple[int, Dict[str, str]]


def _line(
    kind: str,
    *,
    zone: str = "",
    reason: str = "",
    checkpoint: Optional[date] = None,
    source: str = "",
    match_key: str = "",
    value: str = "",
    currency: str = "",
    proof: str = "",
    securities: Optional[SecuritiesRow] = None,
    account: Optional[AccountRow] = None,
) -> List[str]:
    values = {
        "lf_row_kind": kind,
        "lf_zone": zone,
        "lf_reason": reason,
        "lf_checkpoint": checkpoint.isoformat() if checkpoint else "",
        "lf_source": source,
        "lf_match_key": match_key,
        "lf_value": value,
        "lf_currency": currency,
        "lf_proof": proof,
    }
    for column in SECURITIES_COLUMNS:
        values[f"securities:{column}"] = securities.cells.get(column, "") if securities else ""
    for column in ACCOUNT_COLUMNS:
        values[f"account:{column}"] = account.cells.get(column, "") if account else ""
    return [values[header] for header in COMBINED_HEADERS]


def _data_key(day: date, role_rank: int, file_index: int, row: int) -> Tuple[Any, ...]:
    return (day, 0, role_rank, file_index, row, "")


def _truth_key(day: date, rank: int, detail: str) -> Tuple[Any, ...]:
    return (day, 1, rank, 0, 0, detail)


# =============================================================================
# THE TABLE
# =============================================================================


class TableBuilder:
    """Writes the analysis as the combined table: one line per source row (a pair is one line), plus the truth lines."""

    def __init__(self, analysis: Analysis):
        self.analysis = analysis
        self.lines: List[Tuple[Tuple[Any, ...], List[str]]] = []

    def build(self) -> BRIMCombinedTable:
        self._data_lines()
        self._truth_lines()
        rows = [line for _, line in sorted(self.lines, key=lambda item: item[0])]
        return BRIMCombinedTable(headers=list(COMBINED_HEADERS), rows=rows, summary=self._summary())

    def _add(self, key: Tuple[Any, ...], line: List[str]) -> None:
        self.lines.append((key, line))

    # ----------------------------------------------------------------- the rows

    def _data_lines(self) -> None:
        analysis = self.analysis
        for securities, account in analysis.pairs:
            # A pair is dated with the securities operation date, like the transaction it becomes.
            match = core.match_key_text(account.value, account.amount, account.currency)
            self._add(_data_key(securities.op, 0, securities.file_index, securities.row), _line("pair", zone=account.outcome.zone, source=f"{securities.source} + {account.source}", match_key=match, securities=securities, account=account))
        paired = {id(row) for pair in analysis.pairs for row in pair}
        for row in [*analysis.securities, *(item for item in analysis.superseded if isinstance(item, SecuritiesRow))]:
            if id(row) not in paired:
                self._add(_data_key(row.op, 0, row.file_index, row.row), self._securities_line(row))
        for row in [*analysis.account, *(item for item in analysis.superseded if isinstance(item, AccountRow))]:
            if id(row) not in paired:
                self._add(_data_key(row.op, 1, row.file_index, row.row), self._account_line(row))

    @staticmethod
    def _securities_line(row: SecuritiesRow) -> List[str]:
        outcome = row.outcome
        match = core.match_key_text(row.value, row.ctv, row.currency) if row.klass in PAIRED_SECURITIES else ""
        return _line(outcome.kind, zone=outcome.zone, reason=outcome.reason, source=row.source, match_key=match, securities=row)

    @staticmethod
    def _account_line(row: AccountRow) -> List[str]:
        outcome = row.outcome
        match = core.match_key_text(row.value, row.amount, row.currency) if row.klass in PAIRED_ACCOUNT else ""
        return _line(outcome.kind, zone=outcome.zone, reason=outcome.reason, source=row.source, match_key=match, account=row)

    # ----------------------------------------------------------------- what the bank states

    def _truth_lines(self) -> None:
        analysis = self.analysis
        for checkpoint in analysis.checkpoints:
            truth = checkpoint.cash
            zone = ZONE_BEFORE if checkpoint.kind == "opening" else ZONE_GAP
            self._add(_truth_key(truth.as_of, 0, ""), _line("truth_cash", zone=zone, checkpoint=truth.as_of, source=truth.source, value=core.money(truth.amount), currency=truth.currency))
            for position in checkpoint.positions:
                proof_row = position.rows[0]
                self._add(_truth_key(truth.as_of, 1, core.norm(position.name)), _line("truth_position", zone=zone, checkpoint=truth.as_of, source=proof_row.source, value=core.plain(position.quantity), proof=position.proof, securities=proof_row))
        for truth in analysis.verifications:
            self._add(_truth_key(truth.as_of, 2, truth.source), _line("verification", zone=analysis.zone(truth.as_of), checkpoint=truth.as_of, source=truth.source, value=core.money(truth.amount), currency=truth.currency))

    # ----------------------------------------------------------------- the summary

    def _summary(self) -> Dict[str, Any]:
        analysis = self.analysis
        kinds: Counter = Counter()
        zones: Counter = Counter()
        reasons: Counter = Counter()
        for _, line in self.lines:
            kind = line[0]
            if kind in TRUTH_KINDS:
                continue
            kinds[kind] += 1
            zones[line[1] or "none"] += 1
            if line[2]:
                reasons[line[2]] += 1
        if analysis.broken or analysis.conflicting_days:
            chain = "broken"
        else:
            chain = "ok" if analysis.statements else "none"
        return {
            "rows": {"securities": sum(len(file.rows) for file in analysis.securities_files), "account": sum(len(file.rows) for file in analysis.account_files)},
            "outcomes": dict(sorted(kinds.items())),
            "zones": dict(sorted(zones.items())),
            "reasons": dict(sorted(reasons.items())),
            "segments": [{"start": segment.start.isoformat(), "end": segment.end.isoformat()} for segment in analysis.segments()],
            "gaps": [{"start": gap.start.isoformat(), "end": gap.end.isoformat()} for gap in analysis.gaps()],
            "checkpoints": [{"as_of": item.cash.as_of.isoformat(), "kind": item.kind, "cash": core.money(item.cash.amount), "positions": len(item.positions)} for item in analysis.checkpoints],
            "verifications": [{"as_of": item.as_of.isoformat(), "cash": core.money(item.amount)} for item in analysis.verifications],
            "balance_chain": chain,
            "overlap_mismatch_days": sum(len(days) for days in analysis.mismatch.values()),
        }


# =============================================================================
# THE PARSE OF A COMBINED FILE
# =============================================================================


def read_combined(path: Path) -> List[Line]:
    """The lines of a combined file: ``(line number, {column: text})``, blank lines skipped."""
    with BRIMProvider._open_text(path, newline="") as handle:
        reader = csv.reader(handle, delimiter=";")
        header = [cell.strip().lstrip("﻿") for cell in next(reader, [])]
        missing = [name for name in COMBINED_HEADERS if name not in header]
        if missing:
            raise BRIMParseError(
                "Not a Crédit Agricole combined file: columns are missing",
                details={"missing": missing, "code": "credit_agricole_combined_columns_missing", "context": {"missing": ", ".join(str(c) for c in missing)}},
            )
        positions = {name: header.index(name) for name in COMBINED_HEADERS}
        lines: List[Line] = []
        for cells in reader:
            if not any(cell.strip() for cell in cells):
                continue
            lines.append((reader.line_num, {name: cells[position] if position < len(cells) else "" for name, position in positions.items()}))
        return lines


def _cells(row: Dict[str, str], prefix: str, columns: Sequence[str]) -> Dict[str, str]:
    return {column: row.get(f"{prefix}:{column}", "") for column in columns}


@dataclass
class Entry:
    """A line of the combined file with its rows read back."""

    number: int
    row: Dict[str, str]
    securities: Optional[SecuritiesRow] = None
    account: Optional[AccountRow] = None

    @property
    def kind(self) -> str:
        return self.row["lf_row_kind"]

    @property
    def reason(self) -> str:
        return self.row["lf_reason"]


@dataclass
class _TruthCash:
    zone: str
    amount: Decimal
    currency: str
    source: str
    number: int


def _incomplete(number: int, row: Dict[str, str]) -> BRIMParseError:
    return BRIMParseError(
        f"Line {number} of the combined file is incomplete",
        details={"line": number, "kind": row.get("lf_row_kind", ""), "code": "credit_agricole_combined_line_incomplete", "context": {"line": number}},
    )


class CombinedParser:
    """Rebuilds transactions, todos, notices and truth points from the combined file."""

    def __init__(self, provider: BRIMProvider, broker_id: int):
        self.provider = provider
        self.broker_id = broker_id
        self.entries: List[Entry] = []
        self.truth_cash: Dict[date, _TruthCash] = {}
        self.positions: Dict[date, List[Tuple[str, Decimal]]] = defaultdict(list)
        self.verifications: List[Tuple[int, date, Decimal, str, str]] = []

    # ----------------------------------------------------------------- reading

    def add(self, number: int, row: Dict[str, str]) -> None:
        kind = row["lf_row_kind"]
        if kind in TRUTH_KINDS:
            self._truth(number, row)
            return
        if kind not in ("pair", "standalone", "excluded"):
            raise BRIMParseError(
                f"Line {number} of the combined file has an unknown kind",
                details={"line": number, "kind": kind, "code": "credit_agricole_combined_line_unknown_kind", "context": {"line": number, "kind": kind}},
            )
        securities = securities_from_cells(_cells(row, "securities", SECURITIES_COLUMNS), number) if row.get("securities:Causale") else None
        account = account_from_cells(_cells(row, "account", ACCOUNT_COLUMNS), number) if row.get("account:Descrizione") or row.get("account:Causale") else None
        if (row.get("securities:Causale") and securities is None) or (row.get("account:Causale") and account is None):
            raise _incomplete(number, row)
        if kind == "pair" and (securities is None or account is None):
            raise _incomplete(number, row)
        if securities is not None:
            securities.klass = classify_securities(securities)
        if account is not None:
            account.klass, account.tier = classify_account(account)
        self.entries.append(Entry(number, row, securities, account))

    def _truth(self, number: int, row: Dict[str, str]) -> None:
        try:
            day = date.fromisoformat(row["lf_checkpoint"])
        except ValueError:
            raise _incomplete(number, row) from None
        kind = row["lf_row_kind"]
        value = io_decimal(row["lf_value"])
        if kind == "truth_position":
            if value is None:
                raise _incomplete(number, row)
            self.positions[day].append((row.get("securities:Nome", "").strip(), value))
            return
        if value is None:
            raise _incomplete(number, row)
        currency = row["lf_currency"] or DEFAULT_CURRENCY
        if kind == "truth_cash":
            self.truth_cash[day] = _TruthCash(row["lf_zone"], value, currency, row["lf_source"], number)
        else:
            self.verifications.append((number, day, value, currency, row["lf_source"]))

    # ----------------------------------------------------------------- booking

    def output(self) -> BRIMParseOutput:
        booking = Booking(self.provider, self.broker_id)
        imported = [entry for entry in self.entries if entry.kind in ("pair", "standalone")]
        booking.read_positions([entry.securities for entry in imported if entry.securities is not None])
        accounts = [entry for entry in imported if entry.account is not None]
        booking.read_sheet([entry.account for entry in accounts if entry.account is not None], [entry.number for entry in accounts])
        for entry in imported:
            if entry.kind == "pair" and entry.securities is not None and entry.account is not None:
                isin = account_isin(entry.account)
                if isin and entry.securities.name:
                    booking.link_isin(isin, entry.securities.name)
        excluded: Dict[str, List[Entry]] = defaultdict(list)
        mismatched: List[Entry] = []
        for entry in self.entries:
            if entry.kind == "pair":
                self._book_pair(booking, entry, mismatched)
            elif entry.kind == "standalone":
                self._book_standalone(booking, entry)
            else:
                excluded[entry.reason or "invalid"].append(entry)
        booking.attach_maturity_notices()
        notices = [*self._excluded_notices(excluded), *self._mismatch_notices(mismatched), *booking.warnings, *booking.notices()]
        if not booking.transactions and not notices:
            notices.append(BRIMNotice(severity="warning", code="ca_securities_empty", message="Nessuna transazione valida trovata nel file"))
        logger.info("Crédit Agricole combined file parsed", transaction_count=len(booking.transactions), warning_count=len(notices), asset_count=len(booking.extracted_assets), field_todo_count=len(booking.field_todos))
        return BRIMParseOutput(
            transactions=booking.transactions,
            warnings=notices,
            validation_issues=booking.validation_issues,
            field_todos=booking.field_todos,
            extracted_assets=booking.extracted_assets,
            checkpoints=self._checkpoints(booking),
            verifications=self._verifications(),
        )

    def _book_pair(self, booking: Booking, entry: Entry, mismatched: List[Entry]) -> None:
        securities, account = entry.securities, entry.account
        if securities is None or account is None or account.amount is None:
            raise _incomplete(entry.number, entry.row)
        booking.book_movement(securities, entry.number, account.amount, account)
        name = account_name(account)
        if name and not core.compatible(securities.name, name):
            mismatched.append(entry)

    def _book_standalone(self, booking: Booking, entry: Entry) -> None:
        if entry.account is not None:
            booking.book_account_row(sheet_row(entry.account), entry.number)
            return
        securities = entry.securities
        if securities is None:
            raise _incomplete(entry.number, entry.row)
        if securities.klass == "transfer_in":
            booking.book_transfer_in(securities, entry.number)
        elif securities.klass in PAIRED_SECURITIES and securities.ctv is not None:
            booking.book_movement(securities, entry.number, securities.ctv)
        else:
            raise _incomplete(entry.number, entry.row)

    # ----------------------------------------------------------------- notices

    @staticmethod
    def _securities_table(entries: Sequence[Entry], comment: str) -> BRIMEvidence:
        return BRIMEvidence(
            title="Titoli",
            headers=list(SECURITIES_EVIDENCE_HEADERS),
            rows=[[entry.securities.cells.get(label, "") if entry.securities else "" for label in SECURITIES_EVIDENCE_HEADERS] for entry in entries],
            row_numbers=[entry.number for entry in entries],
            comment=comment,
        )

    @staticmethod
    def _account_table(entries: Sequence[Entry], comment: str) -> BRIMEvidence:
        labels = {"Data Op.": "Data Op.", "Causale": "Causale", "Descrizione": "Descrizione", "Importo": "Importo", "Divisa": "Divisa"}
        return BRIMEvidence(
            title="Conto",
            headers=list(ACCOUNT_SHEET_HEADER),
            rows=[[entry.account.cells.get(labels[label], "") if entry.account else "" for label in ACCOUNT_SHEET_HEADER] for entry in entries],
            row_numbers=[entry.number for entry in entries],
            comment=comment,
        )

    def _row_evidence(self, entries: Sequence[Entry], comment: str) -> List[BRIMEvidence]:
        securities = [entry for entry in entries if entry.securities is not None]
        account = [entry for entry in entries if entry.account is not None]
        tables = []
        if securities:
            tables.append(self._securities_table(securities, comment))
        if account:
            tables.append(self._account_table(account, comment))
        return tables

    def _excluded_notices(self, excluded: Dict[str, List[Entry]]) -> List[BRIMNotice]:
        notices: List[BRIMNotice] = []
        for entry in excluded.pop("unknown_type", []):
            # A causale of the securities export that this plugin has never seen.
            causale = entry.securities.causale if entry.securities else ""
            notices.append(
                BRIMNotice(
                    severity="warning",
                    code="ca_securities_unknown_causale",
                    message=f"Riga {entry.number}: causale '{causale}' non riconosciuta, saltata",
                    context={"causale": causale, "row": entry.number, "report_issue": True},
                    evidence=self._row_evidence([entry], "Non so cosa farne di questa causale, quindi la riga non è stata importata: se contiene un movimento vero, va inserito a mano."),
                )
            )
        for entry in excluded.pop("invalid", []):
            causale = entry.account.causale if entry.account else ""
            notices.append(
                BRIMNotice(
                    severity="warning",
                    code="ca_account_invalid_amount",
                    message=f"Riga {entry.number}: importo non valido per '{causale}', saltata",
                    context={"causale": causale, "row": entry.number, "report_issue": True},
                    evidence=self._row_evidence([entry], "L'importo di questa riga non è leggibile come numero, quindi la riga è stata scartata."),
                )
            )
        for reason in sorted(excluded, key=lambda item: (EXCLUDED_ORDER.index(item) if item in EXCLUDED_ORDER else len(EXCLUDED_ORDER), item)):
            entries = excluded[reason]
            message = EXCLUDED_MESSAGES.get(reason, "{n} righe sono state lasciate fuori.").format(n=len(entries))
            comment = EXCLUDED_COMMENTS.get(reason, "Queste righe non vengono importate. Se una di loro è un movimento vero, inseriscilo a mano.")
            notices.append(BRIMNotice(severity=EXCLUDED_SEVERITY.get(reason, "warning"), code=f"excluded_{reason}", message=message, evidence=self._row_evidence(entries, comment), context={"count": len(entries), "reason": reason}))
        return notices

    def _mismatch_notices(self, mismatched: List[Entry]) -> List[BRIMNotice]:
        if not mismatched:
            return []
        message = f"{len(mismatched)} operazioni abbinate hanno un nome diverso nei due file: controllale."
        comment = "Data valuta, importo e tipo coincidono, quindi le righe sono state abbinate. Il nome però è diverso: verifica che sia la stessa operazione."
        return [BRIMNotice(severity="warning", code="name_mismatch", message=message, evidence=self._row_evidence(mismatched, comment), context={"count": len(mismatched)})]

    # ----------------------------------------------------------------- truth points

    @staticmethod
    def _statement_evidence(number: int, source: str, day: date, amount: Decimal, currency: str, comment: str) -> BRIMEvidence:
        return BRIMEvidence(title="Saldo della banca", headers=["Fonte", "Data", "Saldo"], rows=[[source, day.isoformat(), f"{core.money(amount)} {currency}"]], row_numbers=[number], comment=comment)

    def _checkpoints(self, booking: Booking) -> List[BRIMCheckpoint]:
        found = []
        for day in sorted(self.truth_cash):
            truth = self.truth_cash[day]
            kind = "opening" if truth.zone == ZONE_BEFORE else "gap"
            positions = [BRIMTruthPosition(asset_id=booking.name_asset_id(name), quantity=quantity, exactness="exact") for name, quantity in self.positions.get(day, []) if name]
            comment = "Saldo che la banca dichiara a fine giornata, nei termini del registro: il resto della cassa si confronta con questo."
            evidence = [self._statement_evidence(truth.number, truth.source, day, truth.amount, truth.currency, comment)]
            found.append(BRIMCheckpoint(as_of=day, kind=kind, cash=[BRIMTruthCash(currency=truth.currency, amount=truth.amount)], positions=positions, absorbed=BRIMAbsorbed(), evidence=evidence))
        return found

    def _verifications(self) -> List[BRIMVerification]:
        comment = "Saldo che la banca dichiara a fine giornata: si confronta con LibreFolio, ma non genera correzioni."
        found = [BRIMVerification(as_of=day, cash=[BRIMTruthCash(currency=currency, amount=amount)], evidence=[self._statement_evidence(number, source, day, amount, currency, comment)]) for number, day, amount, currency, source in self.verifications]
        return sorted(found, key=lambda item: item.as_of)


def io_decimal(text: str) -> Optional[Decimal]:
    """A figure the combined file writes: a plain number with a dot (``core.money``, ``core.plain``)."""
    try:
        return Decimal(text.strip()) if text.strip() else None
    except ArithmeticError:
        return None


__all__ = ["COMBINED_HEADERS", "COMBINED_MARKERS", "CombinedParser", "TableBuilder", "read_combined"]
