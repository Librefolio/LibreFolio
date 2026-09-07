"""The two int predicates the AI Export spec validators share.

They exist because five modules each carried the same `isinstance(value, bool) or
not isinstance(value, int)` check, and that check is subtler than it looks: in
Python `bool` is a subclass of `int`, so `isinstance(True, int)` is `True`. A
version field annotated `int` therefore accepts `True` and stores `1` unless
somebody remembers to say otherwise — and five authors remembered, which is
exactly the kind of thing that holds until the sixth one.

The rest of `_require_positive_int` — the exception type, the wording — stayed
with each caller on purpose: those messages belong to versioned contracts.
"""

from __future__ import annotations

import pytest

from backend.app.services.ai_export._int_validation import is_int_not_bool, is_positive_int, require_positive_int


class TestIsIntNotBool:
    """The whole point: a bool must never pass for an int."""

    @pytest.mark.parametrize("value", [True, False])
    def test_rejects_a_bool(self, value: bool):
        # `isinstance(True, int)` is True, so a plain isinstance check would accept
        # this and quietly store 1 — a caller's typo turned into a real version
        # number, attached to real data.
        assert is_int_not_bool(value) is False

    @pytest.mark.parametrize("value", [0, 1, -1, 42, 10**18])
    def test_accepts_a_real_int(self, value: int):
        assert is_int_not_bool(value) is True

    @pytest.mark.parametrize("value", [1.0, 1.5, "1", None, [], {}, (1,), b"1"])
    def test_rejects_anything_that_is_not_an_int(self, value: object):
        # 1.0 matters on its own: it equals 1 and would survive a `== int(value)`
        # style check, but a float version is a caller mistake all the same.
        assert is_int_not_bool(value) is False


class TestIsPositiveInt:
    @pytest.mark.parametrize("value", [1, 2, 10**9])
    def test_accepts_one_and_above(self, value: int):
        assert is_positive_int(value) is True

    @pytest.mark.parametrize("value", [0, -1, -(10**9)])
    def test_rejects_zero_and_below(self, value: int):
        # Zero is the interesting one: it is the sentinel a caller reaches for when
        # it has no version to give, and it must not be mistaken for one.
        assert is_positive_int(value) is False

    def test_rejects_true_even_though_it_is_positive_as_a_number(self):
        # `True >= 1` is True, so a predicate that only compared magnitude would let
        # it through. This is the composition the five validators depend on.
        assert is_positive_int(True) is False

    @pytest.mark.parametrize("value", [1.0, "1", None, [1]])
    def test_rejects_non_ints_regardless_of_value(self, value: object):
        assert is_positive_int(value) is False


class TestRequirePositiveInt:
    """The five copies this replaced differed on exception, wording and signature.

    None of that was load bearing: every one of those exceptions is a `ValueError`
    subclass meaning "a *declaration* is internally inconsistent", raised when a
    plugin author writes a bad spec. They never reach the API and no test pinned
    their wording — so the five became one, keeping only the part a caller can
    reasonably want back: its own error type.
    """

    def test_returns_the_value_so_it_can_be_used_inline(self):
        # Three of the five returned the int and two returned None, which meant a
        # caller had to know which one it was looking at. It always returns it now.
        assert require_positive_int(7, "version") == 7

    def test_a_wrong_type_raises_TypeError_by_default(self):
        # Without a typed error of its own, a caller should get what Python means:
        # TypeError for the wrong kind of thing...
        with pytest.raises(TypeError, match="version must be an int, got str"):
            require_positive_int("7", "version")

    def test_a_wrong_value_raises_ValueError_by_default(self):
        # ...and ValueError for the right kind of thing with an unusable value.
        with pytest.raises(ValueError, match="version must be >= 1"):
            require_positive_int(0, "version")

    def test_a_bool_is_a_wrong_type_not_a_wrong_value(self):
        # True is 1, so a check that only looked at magnitude would accept it and a
        # check that reported it as "must be >= 1" would send the author looking in
        # the wrong place. It is the *type* that is wrong.
        with pytest.raises(TypeError, match="must be an int, got bool"):
            require_positive_int(True, "version")

    def test_error_cls_replaces_both_defaults(self):
        # A subsystem with its own typed error keeps raising it, which is the only
        # difference between the five originals that was worth preserving.
        class SpecError(ValueError):
            pass

        with pytest.raises(SpecError):
            require_positive_int("7", "version", error_cls=SpecError)
        with pytest.raises(SpecError):
            require_positive_int(0, "version", error_cls=SpecError)

    def test_owner_id_names_the_declaration_the_error_came_from(self):
        # With dozens of plugins loaded, "version must be >= 1" alone does not say
        # which one to go and fix.
        with pytest.raises(ValueError, match="fx.exposure: version must be >= 1"):
            require_positive_int(0, "version", owner_id="fx.exposure")

    def test_without_an_owner_the_message_has_no_stray_prefix(self):
        with pytest.raises(ValueError) as excinfo:
            require_positive_int(0, "version")
        assert str(excinfo.value).startswith("version must be"), str(excinfo.value)
