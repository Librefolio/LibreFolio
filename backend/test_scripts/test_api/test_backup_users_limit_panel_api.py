"""
The hosting panel and a backup that holds more active accounts than ``LIBREFOLIO_MAX_USERS`` (workstream B, lot B5-1k2;
contract ``B-5-1k2-contratto.md`` «Backend»). Selector: ``api backup-users-limit-panel``. Written RED, before B5-1k2.

The panel's routes are workstream H's (``panel_restore.py``, ``schemas/hosting_panel.py``): this lot does not touch them. The
panel's stage report (``PanelRestoreStageReport``) is a closed list of fields built from the administrators' report, and its
``warnings`` reuse the ``Literal`` of ``RestoreStageReport``. So, through the panel:

1. A real check of a sealed backup of the example (five active accounts, limit 3): the panel's report carries the warning
   code ``users_over_limit`` in ``warnings`` (before ``credentials_from_backup``), NO number (``users_active``, ``users_limit``
   and ``users_over_limit`` are not fields of the panel's view: its keys are still the twenty of before) and nothing that
   names an account.
2. The panel's confirmation of that backup is accepted (202, ``pending`` via the panel): there is nobody to ask, and nothing to
   refuse.

How. The fixtures of ``test_panel_restore_api.py`` (the app of ``main.py`` in process, the panel's tickets, fake check
threads) are imported as they are; the sealed archive is built here. Pure: data directories under ``tmp_path``, no lane
server, database or network.
"""

from __future__ import annotations

from dataclasses import dataclass

import pytest

from backend.app.services.platform.instance_backup import apply as apply_module
from backend.app.services.platform.instance_backup.staging import read_report
from backend.test_scripts.test_api import test_panel_restore_api as panel_cases
from backend.test_scripts.test_services import test_backup_staging as cases
from backend.test_scripts.test_utils import print_section, print_success

# The fixtures of the panel's tests, reused as they are (the app, the panel of a test, the real databases).
app = panel_cases.app
panel = panel_cases.panel
databases = panel_cases.databases

LIMIT_VARIABLE = "LIBREFOLIO_MAX_USERS"
CODE = "users_over_limit"
CREDENTIALS = "credentials_from_backup"
USERS_FIELDS = ("users_active", "users_limit", "users_over_limit")
ACCOUNTS = (
    ("anna_k", "anna.b51k2@example.com", 1, 1),
    ("bruno_k", "bruno.b51k2@example.com", 1, 1),
    ("carla_k", "carla.b51k2@example.com", 1, 0),
    ("dario_k", "dario.b51k2@example.com", 1, 0),
    ("elena_k", "elena.b51k2@example.com", 1, 0),
    ("olga_k", "olga.b51k2@example.com", 0, 1),
)


@dataclass(frozen=True)
class Sealed:
    lfbk: bytes


@pytest.fixture(scope="module")
def sealed(databases, tmp_path_factory) -> Sealed:
    root = tmp_path_factory.mktemp("b51k2-panel-archive")
    with pytest.MonkeyPatch.context() as patch:
        cases.configure(patch, root / "configured-data-dir")
        try:
            archive, _described = cases.backup_with_accounts(root / "backup", databases, ACCOUNTS)
        finally:
            cases.get_git_version.cache_clear()
    return Sealed(lfbk=panel_cases.seal(archive.path, root / "example.lfbk"))


@pytest.mark.asyncio
async def test_the_panel_s_report_carries_the_warning_code_and_no_number(panel, sealed):
    """B5-1k2: five active accounts for a limit of 3. Barrier: the administrators' report of that check says 5, 3, 2. The
    panel's ``GET .../stage/{id}``: ``report.warnings`` holds ``users_over_limit`` before ``credentials_from_backup``; the
    report has exactly the keys of before (no ``users_*`` field), and the answer holds no number about the users and no
    name of an account."""
    print_section("B5-1k2 panel: the warning, no number")
    panel.state("awaiting-restore")
    panel.monkeypatch.setenv(LIMIT_VARIABLE, "3")
    ended = await panel_cases.checked(panel, sealed.lfbk)
    stage_id = ended["stage_id"]
    admin_view = read_report(panel.root, stage_id)
    assert [getattr(admin_view, name, "<missing>") for name in USERS_FIELDS] == [5, 3, 2], "[new] B5-1k2: barrier: the administrators' report says 5, 3, 2"

    response = await panel_cases.poll(panel, stage_id)
    report = response.json().get("report") or {}
    warnings = report.get("warnings", [])
    assert CODE in warnings and warnings.index(CODE) < warnings.index(CREDENTIALS) and warnings[-1] == CREDENTIALS, f"[new] B5-1k2: the code, before credentials_from_backup, which stays last: {warnings}"
    assert set(report) == panel_cases.REPORT_FIELDS, f"the panel's report keeps its closed list of fields: missing {sorted(panel_cases.REPORT_FIELDS - set(report))}, extra {sorted(set(report) - panel_cases.REPORT_FIELDS)}"
    leaked = [word for word in ("users_active", "users_limit", '"users_over_limit":', "carla_k", "@example") if word in response.text]
    assert leaked == [], f"no number about the users and no name in the panel's answer: {leaked}"
    print_success("panel report: the code, nothing else")


@pytest.mark.asyncio
async def test_the_panel_confirms_a_backup_with_too_many_accounts(panel, sealed):
    """B5-1k2: the panel's confirmation of the same backup is 202, ``pending`` via ``panel``, and no new field in the state;
    the panel's status says the restore waits. (Barrier first: the check says the backup is over the limit.)"""
    panel.state("awaiting-restore")
    panel.monkeypatch.setenv(LIMIT_VARIABLE, "3")
    stage_id = (await panel_cases.checked(panel, sealed.lfbk))["stage_id"]
    assert getattr(read_report(panel.root, stage_id), "users_over_limit", "<missing>") == 2, "[new] B5-1k2: barrier: the backup is 2 accounts over the limit"
    response = await panel_cases.confirm(panel, stage_id)
    assert response.status_code == 202, f"accepted: {panel_cases.shown(response)}"
    state = apply_module.read_restore(panel.root)
    assert state is not None and (state.status, state.confirmed_via) == ("pending", "panel"), f"pending via the panel: {state}"
    assert (await panel_cases.restore_status(panel)).json().get("state") == "pending", "the panel's status says the restore waits"
    print_success("panel: 202, pending")


@pytest.mark.asyncio
async def test_a_limit_changed_since_the_panel_s_check_is_not_outdated(panel, sealed):
    """B5-1k2: checked under a limit of 3, confirmed under 10: 202, not 409 ``restore_stage_outdated``."""
    panel.state("awaiting-restore")
    panel.monkeypatch.setenv(LIMIT_VARIABLE, "3")
    stage_id = (await panel_cases.checked(panel, sealed.lfbk))["stage_id"]
    assert getattr(read_report(panel.root, stage_id), "users_over_limit", "<missing>") == 2, "[new] B5-1k2: barrier: the backup is 2 accounts over the limit"
    panel.monkeypatch.setenv(LIMIT_VARIABLE, "10")
    response = await panel_cases.confirm(panel, stage_id)
    assert response.status_code == 202, f"accepted all the same: {panel_cases.shown(response)}"
    print_success("panel: limit changed: 202")
