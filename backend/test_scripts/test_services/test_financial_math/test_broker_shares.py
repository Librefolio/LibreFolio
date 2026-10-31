"""MF6-3 (decision D4) — ``native_cash.broker_shares``: the share each broker of a scope counts, from the user's accesses.

Module under test: ``backend/app/services/financial_math/native_cash.py`` — ``broker_shares(accesses, *,
apply_ownership_share=True) -> dict[int, Decimal]``, the one rule that replaces the four comprehensions over
``effective_share`` (the portfolio engine, the summary's and the contribution's lot shares, the income/cost/deposit
histories).

- By default each broker counts ``effective_share(role, share_percentage)``: an OWNER its own share (0 included, None =
  the whole broker), an EDITOR or a VIEWER the whole broker.
- With ``apply_ownership_share=False`` every broker counts whole (``Decimal("1")``), whatever the role and the share: the
  figures an Editor sees, which the broker page shows.

The accesses are plain objects with ``broker_id``, ``role`` and ``share_percentage`` (the ORM column is not nullable, so
the None share is only reachable this way). ``broker_shares`` is read as ``native_cash.broker_shares`` inside each test:
before MF6-3 every test fails on its own with an AttributeError, and the rest of the directory still collects.

Pure: no database, no server, no network. Runs in ``./dev.py test services financial-math`` (the runner collects the whole
``test_financial_math/`` directory).
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any

import pytest

from backend.app.db.models import UserRole
from backend.app.services.financial_math import native_cash
from backend.test_scripts.test_utils import print_section, print_success

ONE = Decimal("1")


@dataclass(frozen=True)
class _Access:
    broker_id: int
    role: Any
    share_percentage: Decimal | None


#: One access per case; the broker ids are distinct, so the result names each case by its broker.
_ACCESSES = (
    _Access(broker_id=1, role=UserRole.OWNER, share_percentage=Decimal("0.3")),
    _Access(broker_id=2, role=UserRole.OWNER, share_percentage=Decimal("0")),
    _Access(broker_id=3, role=UserRole.OWNER, share_percentage=None),
    _Access(broker_id=4, role=UserRole.OWNER, share_percentage=Decimal("1")),
    _Access(broker_id=5, role=UserRole.EDITOR, share_percentage=Decimal("0")),
    _Access(broker_id=6, role=UserRole.VIEWER, share_percentage=Decimal("0")),
    # A role given as its text, as a raw row may carry it: effective_share reads both.
    _Access(broker_id=7, role="OWNER", share_percentage=Decimal("0.6")),
    _Access(broker_id=8, role="VIEWER", share_percentage=Decimal("0.25")),
)


class TestBrokerSharesDefault:
    def test_the_default_is_effective_share_of_each_access(self):
        print_section("MF6-3: broker_shares by default — effective_share of every access")
        shares = native_cash.broker_shares(_ACCESSES)
        expected = {access.broker_id: native_cash.effective_share(access.role, access.share_percentage) for access in _ACCESSES}
        assert shares == expected
        # The values themselves, so that the parity above cannot hide a change of effective_share.
        assert shares == {1: Decimal("0.3"), 2: Decimal("0"), 3: ONE, 4: ONE, 5: ONE, 6: ONE, 7: Decimal("0.6"), 8: ONE}
        print_success("owner 30 % → 0.3, 0 % → 0, no share → 1; editor and viewer → 1")

    def test_apply_ownership_share_true_is_the_default(self):
        print_section("MF6-3: broker_shares(apply_ownership_share=True) equals the default")
        assert native_cash.broker_shares(_ACCESSES, apply_ownership_share=True) == native_cash.broker_shares(_ACCESSES)
        print_success("True is the default")

    def test_the_shares_are_decimals(self):
        shares = native_cash.broker_shares(_ACCESSES)
        assert all(isinstance(value, Decimal) for value in shares.values()), shares

    def test_no_access_no_broker(self):
        assert native_cash.broker_shares([]) == {}
        assert native_cash.broker_shares([], apply_ownership_share=False) == {}


class TestBrokerSharesWhole:
    def test_without_the_ownership_share_every_broker_counts_whole(self):
        print_section("MF6-3: broker_shares(apply_ownership_share=False) — every broker whole")
        shares = native_cash.broker_shares(_ACCESSES, apply_ownership_share=False)
        assert shares == {access.broker_id: ONE for access in _ACCESSES}
        assert all(isinstance(value, Decimal) for value in shares.values()), shares
        print_success("owner 30 %, 0 %, no share, editor, viewer → 1")

    @pytest.mark.parametrize("role", [UserRole.OWNER, UserRole.EDITOR, UserRole.VIEWER], ids=lambda role: role.value)
    @pytest.mark.parametrize("share", [Decimal("0"), Decimal("0.3"), Decimal("1"), None], ids=["0", "0.3", "1", "none"])
    def test_whole_for_every_role_and_share(self, role, share):
        assert native_cash.broker_shares([_Access(broker_id=9, role=role, share_percentage=share)], apply_ownership_share=False) == {9: ONE}

    def test_the_option_is_keyword_only(self):
        with pytest.raises(TypeError):
            native_cash.broker_shares(_ACCESSES, False)  # noqa: FBT003 — the positional call is what is refused
