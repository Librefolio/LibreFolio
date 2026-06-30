"""
Test: Scheduler leader election — am_i_leader() with mocked psutil.

Tests single-worker, multi-worker, zombie siblings, Docker PID 1,
dev mode --reload detection, and exception safety.

Test IDs: SL-001..SL-007
"""

import sys
from unittest.mock import MagicMock, patch

from backend.app.config import PROJECT_ROOT

sys.path.insert(0, str(PROJECT_ROOT))

from backend.test_scripts.test_utils import print_section, print_success

# ============================================================================
# Helpers — build mock Process objects
# ============================================================================


def _mock_process(pid: int, status: str = "sleeping", cmdline: list[str] | None = None):
    """Create a mock psutil.Process with given PID and status."""
    p = MagicMock()
    p.pid = pid
    p.is_running.return_value = status != "zombie"
    p.status.return_value = status
    p.cmdline.return_value = cmdline or ["python", "-m", "uvicorn", "app:app"]
    return p


def _patch_leader(me_pid: int, siblings: list, parent_cmdline: list[str] | None = None, no_parent: bool = False):
    """Context manager factory: patches psutil.Process to simulate a given scenario."""
    me = _mock_process(me_pid)

    if no_parent:
        me.parent.return_value = None
    else:
        parent = MagicMock()
        parent.cmdline.return_value = parent_cmdline or ["uvicorn", "--workers", "2"]
        parent.children.return_value = siblings
        me.parent.return_value = parent

    return patch("backend.app.services.scheduler.leader.psutil.Process", return_value=me), patch("backend.app.services.scheduler.leader.os.getpid", return_value=me_pid)


# ============================================================================
# SL-001: Single worker → always leader
# ============================================================================


class TestSingleWorker:
    def test_single_sibling_is_leader(self):
        """SL-001: Only 1 sibling (self) → True."""
        print_section("SL-001: am_i_leader — single worker")
        from backend.app.services.scheduler.leader import am_i_leader

        me_pid = 1001
        me = _mock_process(me_pid)

        parent = MagicMock()
        parent.cmdline.return_value = ["uvicorn", "app:app", "--workers", "1"]
        parent.children.return_value = [me]
        me.parent.return_value = parent

        with patch("backend.app.services.scheduler.leader.psutil.Process", return_value=me), patch("backend.app.services.scheduler.leader.os.getpid", return_value=me_pid):
            result = am_i_leader()

        assert result is True
        print_success("Single worker → True")


# ============================================================================
# SL-002: Lowest PID is leader
# ============================================================================


class TestLowestPidIsLeader:
    def test_lowest_pid_leader(self):
        """SL-002: siblings=[100,200,300], me=100 → True (lowest)."""
        print_section("SL-002: am_i_leader — lowest PID is leader")
        from backend.app.services.scheduler.leader import am_i_leader

        me_pid = 100
        siblings = [_mock_process(100), _mock_process(200), _mock_process(300)]
        me = siblings[0]

        parent = MagicMock()
        parent.cmdline.return_value = ["uvicorn", "--workers", "3"]
        parent.children.return_value = siblings
        me.parent.return_value = parent

        with patch("backend.app.services.scheduler.leader.psutil.Process", return_value=me), patch("backend.app.services.scheduler.leader.os.getpid", return_value=me_pid):
            result = am_i_leader()

        assert result is True
        print_success("Lowest PID (100) among [100,200,300] → True")


# ============================================================================
# SL-003: Not lowest PID → not leader
# ============================================================================


class TestNotLowestPid:
    def test_not_lowest_pid_not_leader(self):
        """SL-003: siblings=[100,200,300], me=200 → False."""
        print_section("SL-003: am_i_leader — not lowest PID")
        from backend.app.services.scheduler.leader import am_i_leader

        me_pid = 200
        siblings = [_mock_process(100), _mock_process(200), _mock_process(300)]
        me = siblings[1]

        parent = MagicMock()
        parent.cmdline.return_value = ["uvicorn", "--workers", "3"]
        parent.children.return_value = siblings
        me.parent.return_value = parent

        with patch("backend.app.services.scheduler.leader.psutil.Process", return_value=me), patch("backend.app.services.scheduler.leader.os.getpid", return_value=me_pid):
            result = am_i_leader()

        assert result is False
        print_success("Not lowest PID (200) among [100,200,300] → False")


# ============================================================================
# SL-004: Zombie siblings excluded from election
# ============================================================================


class TestZombieSiblingsExcluded:
    def test_zombie_excluded(self):
        """SL-004: siblings=[zombie(100), running(200)], me=200 → True (zombie excluded)."""
        print_section("SL-004: am_i_leader — zombie siblings excluded")

        from backend.app.services.scheduler.leader import am_i_leader

        me_pid = 200
        zombie = _mock_process(100, status="zombie")
        me = _mock_process(200, status="sleeping")
        siblings = [zombie, me]

        parent = MagicMock()
        parent.cmdline.return_value = ["uvicorn", "--workers", "2"]
        parent.children.return_value = siblings
        me.parent.return_value = parent

        with patch("backend.app.services.scheduler.leader.psutil.Process", return_value=me), patch("backend.app.services.scheduler.leader.os.getpid", return_value=me_pid), patch("backend.app.services.scheduler.leader.psutil.STATUS_ZOMBIE", "zombie"):
            result = am_i_leader()

        assert result is True
        print_success("Zombie PID 100 excluded → PID 200 becomes leader → True")


# ============================================================================
# SL-005: Docker PID 1 (no parent) → always leader
# ============================================================================


class TestDockerPid1:
    def test_no_parent_is_leader(self):
        """SL-005: parent() returns None (Docker PID 1) → True."""
        print_section("SL-005: am_i_leader — Docker PID 1 (no parent)")
        from backend.app.services.scheduler.leader import am_i_leader

        me_pid = 1
        me = MagicMock()
        me.pid = me_pid
        me.parent.return_value = None

        with patch("backend.app.services.scheduler.leader.psutil.Process", return_value=me), patch("backend.app.services.scheduler.leader.os.getpid", return_value=me_pid):
            result = am_i_leader()

        assert result is True
        print_success("No parent (Docker PID 1) → True")


# ============================================================================
# SL-006: Dev mode (--reload in parent cmdline) → always leader
# ============================================================================


class TestDevModeReload:
    def test_reload_flag_always_leader(self):
        """SL-006: parent cmdline contains '--reload' → True (dev mode fast-path)."""
        print_section("SL-006: am_i_leader — dev mode --reload fast-path")
        from backend.app.services.scheduler.leader import am_i_leader

        me_pid = 5000
        me = _mock_process(me_pid)
        parent = MagicMock()
        parent.cmdline.return_value = ["uvicorn", "app:app", "--reload", "--host", "0.0.0.0"]
        parent.children.return_value = [me]
        me.parent.return_value = parent

        with patch("backend.app.services.scheduler.leader.psutil.Process", return_value=me), patch("backend.app.services.scheduler.leader.os.getpid", return_value=me_pid):
            result = am_i_leader()

        assert result is True
        print_success("--reload in parent cmdline → True (dev mode fast-path)")


# ============================================================================
# SL-007: psutil exception → fail-safe True
# ============================================================================


class TestPsutilException:
    def test_no_such_process_returns_true(self):
        """SL-007: psutil.Process() raises NoSuchProcess → True (fail-safe)."""
        print_section("SL-007: am_i_leader — psutil.NoSuchProcess → fail-safe True")
        import psutil as psutil_module

        from backend.app.services.scheduler.leader import am_i_leader

        with (
            patch(
                "backend.app.services.scheduler.leader.psutil.Process",
                side_effect=psutil_module.NoSuchProcess(pid=999),
            ),
            patch("backend.app.services.scheduler.leader.os.getpid", return_value=999),
        ):
            result = am_i_leader()

        assert result is True
        print_success("NoSuchProcess exception → True (fail-safe)")

    def test_access_denied_returns_true(self):
        """SL-007b: psutil.AccessDenied → True (fail-safe)."""
        print_section("SL-007b: am_i_leader — psutil.AccessDenied → fail-safe True")
        import psutil as psutil_module

        from backend.app.services.scheduler.leader import am_i_leader

        with (
            patch(
                "backend.app.services.scheduler.leader.psutil.Process",
                side_effect=psutil_module.AccessDenied(pid=999),
            ),
            patch("backend.app.services.scheduler.leader.os.getpid", return_value=999),
        ):
            result = am_i_leader()

        assert result is True
        print_success("AccessDenied exception → True (fail-safe)")
