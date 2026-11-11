"""Crédit Agricole broker report import plugin (BRIM), a report-set plugin.

Crédit Agricole offers two exports of one dossier, each as **CSV** (``;`` separated, UTF-8 BOM) or **XLSX**, each possibly
downloaded several times:

- the securities movements, "Lista Movimenti Deposito Titoli" (role ``securities``): coupons, purchases, fund redemptions,
  maturities and transfers from another dossier, dated by ``Data operazione``;
- the account movements, "Lista Movimenti Conto" (role ``account``): every cash movement, dated by ``Data Op.``. Only the
  XLSX carries, above the table, the opening and the closing balance (``Saldo Iniziale``, ``Saldo Finale``).

The two exports show the same facts twice: a coupon, a purchase, a redemption, a maturity is a row in each. Read apart (what up to
version 1.5.0 did) each is counted twice. From **2.0.0** the plugin imports the set: the files are uploaded together, the set pairs
the rows (same kind of fact, same amount to the cent, same *value date*), and what is imported is one transaction per fact, with
the cash the account states. Nothing is guessed: rows that cannot be paired with certainty are left out and said so. A file read
alone is no longer imported: it raises ``BRIMSetRequiredError`` naming the other export.

The pieces:

- ``_rows.py``: reading the exports and the XLSX header (the *testata*);
- ``_classify.py``: the causale registry and the pure functions that name a row (unchanged since 1.5.0);
- ``_report_set.py``: the analysis: rule M for several downloads of one export, pairing, balances (a hole in the account becomes a
  proposed cash correction), truth points;
- ``_combined.py``: the combined file (``combine``) and its parse;
- ``_booking.py``: from a line of the combined file to transactions, todos and notices.

**Warning language follows the input format.** The only export supported is the Italian one, so the warnings of a parse are
emitted in Italian; the notices of a set (``describe_set``) are in English, localised by the wizard.

**No ISIN** is in the securities export: its assets are identified by ``Nome``. A coupon row of the account names its ISIN, which
a pair links to the same asset.

A transaction takes its date from the *operation date* column, never from a value date. The plugin transcribes reported figures
verbatim and never calls the FX subsystem.
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional

from backend.app.schemas.brim import BRIMCombinedTable, BRIMMemberSummary, BRIMParseOutput, BRIMReportRole, BRIMSetShape
from backend.app.services.brim.brim_provider import BRIMParseError, BRIMProvider, BRIMSetRequiredError
from backend.app.services.brim.registry import BRIMProviderRegistry
from backend.app.services.brim_providers import _brim_io as io
from backend.app.services.brim_providers.broker_credit_agricole import _report_set
from backend.app.services.brim_providers.broker_credit_agricole._combined import COMBINED_MARKERS, CombinedParser, TableBuilder, read_combined
from backend.app.services.brim_providers.broker_credit_agricole._rows import ROLE_ACCOUNT, ROLE_SECURITIES, detect_role
from backend.app.services.platform.provider_registry import register_provider

_HEADER_SCAN_ROWS = 60


def _is_combined(path: Path) -> bool:
    """A file this plugin wrote: its header holds the columns of the combined file."""
    try:
        rows = io.read_rows(path)
    except Exception:  # noqa: BLE001 — a file that cannot be read is no combined file of ours: the answer is "no"
        return False
    head = {io.cell_str(cell).lstrip("\ufeff") for row in rows[:_HEADER_SCAN_ROWS] for cell in row}
    return all(marker in head for marker in COMBINED_MARKERS)


@register_provider(BRIMProviderRegistry)
class CreditAgricoleBrokerProvider(BRIMProvider):
    """Crédit Agricole: the securities export and the account export, combined into one import."""

    @property
    def provider_code(self) -> str:
        return "broker_credit_agricole"

    @property
    def provider_name(self) -> str:
        return "Crédit Agricole"

    @property
    def description(self) -> str:
        return (
            "Import from Crédit Agricole exports (CSV or XLSX), uploaded together as one set: the 'Lista Movimenti Deposito Titoli' securities movements "
            "and the 'Lista Movimenti Conto' account movements. Each coupon, purchase, redemption and maturity is imported once, with the cash the "
            "account states; the opening balance of the Excel export starts the cash, and a stretch with no account export becomes a proposed cash correction."
        )

    @property
    def supported_extensions(self) -> List[str]:
        return [".csv", ".xlsx"]

    @property
    def detection_priority(self) -> int:
        return 100

    @property
    def icon_url(self) -> str:
        return "https://www.credit-agricole.it/favicon.ico"

    @property
    def docs_url(self) -> Optional[str]:
        return "/mkdocs/user/transactions/import/credit_agricole/"

    @property
    def plugin_version(self) -> str:
        # 2.0.0 — a report-set plugin: the securities and the account exports are imported together, each fact once, with the cash
        #         of the account; a file read alone raises BRIMSetRequiredError (up to 1.5.0 each was imported on its own).
        return "2.0.0"

    @property
    def test_file_pattern(self) -> Optional[str]:
        return "credit_agricole"

    @property
    def test_sample_sets(self) -> List[Dict[str, List[str]]]:
        return [
            {ROLE_SECURITIES: ["credit_agricole-securities.csv"], ROLE_ACCOUNT: ["credit_agricole-account.xlsx"]},
            {ROLE_SECURITIES: ["credit_agricole-gap-securities.xlsx"], ROLE_ACCOUNT: ["credit_agricole-gap-account-1.xlsx", "credit_agricole-gap-account-2.xlsx"]},
        ]

    # ----------------------------------------------------------------- report set contract

    @property
    def report_roles(self) -> List[BRIMReportRole]:
        return [
            BRIMReportRole(
                code=ROLE_SECURITIES,
                required=True,
                multiple=True,
                extensions=[".csv", ".xlsx"],
                description="Securities movements (Lista Movimenti Deposito Titoli): coupons, purchases, redemptions, maturities and transfers, dated by operation date",
            ),
            BRIMReportRole(
                code=ROLE_ACCOUNT,
                required=True,
                multiple=True,
                extensions=[".csv", ".xlsx"],
                description="Account movements (Lista Movimenti Conto): every cash movement; the Excel export also states the opening and closing balance",
                max_history="P2Y",
                must_cover=ROLE_SECURITIES,
            ),
        ]

    @property
    def pre_checkpoint_policy(self) -> str:
        # The rows before the opening balance are positions (transfers from another dossier), not cash to summarise.
        return "import"

    def can_parse(self, file_path: Path) -> bool:
        """A member of the set (so that reading it alone says which export is missing) or a combined file."""
        if file_path.suffix.lower() not in (".csv", ".xlsx"):
            return False
        return detect_role(file_path) is not None or _is_combined(file_path)

    def detect_role(self, file_path: Path) -> Optional[str]:
        return detect_role(file_path)

    def describe_member(self, file_path: Path) -> BRIMMemberSummary:
        return _report_set.describe_member(file_path)

    def describe_set(self, members: Dict[str, List[Path]]) -> BRIMSetShape:
        return _report_set.describe_set(members)

    def combine(self, members: Dict[str, List[Path]]) -> BRIMCombinedTable:
        analysis = _report_set.Analysis(members)
        if not analysis.securities and not analysis.account:
            raise BRIMParseError("The exports have no dated rows: there is nothing to combine", details={"code": "credit_agricole_no_dated_rows"})
        return TableBuilder(analysis).build()

    def parse(self, file_path: Path, broker_id: int) -> BRIMParseOutput:
        role = detect_role(file_path)
        if role is not None:
            raise BRIMSetRequiredError(
                "This Crédit Agricole export is one file of a report set: upload the securities movements and the account movements together, and import the set",
                missing_roles=[item.code for item in self.report_roles if item.code != role],
            )
        if not _is_combined(file_path):
            raise BRIMParseError("Not a Crédit Agricole combined file", details={"code": "credit_agricole_not_combined_file"})
        parser = CombinedParser(self, broker_id)
        for number, row in read_combined(file_path):
            parser.add(number, row)
        return parser.output()
