"""The JS coverage adapter, and the double-compilation problem it exists to survive.

`coverage_analysis.py` reads `frontend/coverage-js/combined/coverage-final.json` to
answer "where should the next test go". That file is a *merge* of two measurements
of the same source: vitest compiles each `.svelte` for jsdom, the E2E suite measures
the production build, and the Svelte compiler emits different code each time.

So statement positions do not line up. Measured on `DataTableColumnFilter.svelte`:
532 statements under vitest, 484 under E2E, 791 in the merge — of which only 225
positions were shared. The merged denominator was the union of two maps of one file,
which inflated 2 163 statements across 89 files and made a file with a component
test look *worse* than one without.

Lines survive the double compilation (356 of ~450 shared on that same file), which
is why this adapter counts them instead. These tests pin that behaviour, because a
silent regression here does not break anything visibly — it just sends the next
person to write tests for code that is already covered.
"""

import pytest

from scripts.coverage_js import _branches_in_range, _statements_in_range, is_istanbul, istanbul_to_analysis


def _file(statements: dict[int, list[int]]) -> dict:
    """Build an istanbul file entry from {line: [hit counts on that line]}."""
    statement_map: dict[str, dict] = {}
    counters: dict[str, int] = {}
    sid = 0
    for line, hits in statements.items():
        for hit in hits:
            statement_map[str(sid)] = {"start": {"line": line, "column": 0}, "end": {"line": line, "column": 10}}
            counters[str(sid)] = hit
            sid += 1
    return {"statementMap": statement_map, "s": counters, "fnMap": {}, "f": {}}


class TestCountedByLine:
    def test_several_statements_on_one_line_count_once(self):
        """`a && b()` is one line, however many statements the compiler emits."""
        assert _statements_in_range(_file({5: [1, 1, 1]}), 1, 10) == (1, 1)

    def test_a_line_is_covered_when_any_statement_on_it_ran(self):
        """Line coverage has always meant this, and it is what makes the two
        compilations comparable: one may split a line the other keeps whole."""
        assert _statements_in_range(_file({5: [0, 3]}), 1, 10) == (1, 1)

    def test_a_line_is_uncovered_only_when_nothing_on_it_ran(self):
        assert _statements_in_range(_file({5: [0, 0]}), 1, 10) == (1, 0)

    def test_lines_are_counted_independently(self):
        total, covered = _statements_in_range(_file({5: [0, 3], 6: [0], 7: [2]}), 1, 10)
        assert (total, covered) == (3, 2)

    def test_the_range_still_bounds_what_is_counted(self):
        """Statements are attributed to a function by its line range, and that
        must keep working: the dedup happens inside the range, not around it."""
        assert _statements_in_range(_file({5: [1], 50: [1]}), 1, 10) == (1, 1)

    def test_an_empty_range_counts_nothing(self):
        assert _statements_in_range(_file({50: [1]}), 1, 10) == (0, 0)

    def test_a_statement_without_a_line_is_skipped_not_crashed(self):
        """Monocart has emitted entries with no `start.line` after a sourcemap
        failed to resolve. Dropping one statement is right; dying is not."""
        broken = {"statementMap": {"0": {"start": {}}, "1": {"start": {"line": 5}}}, "s": {"0": 1, "1": 1}}
        assert _statements_in_range(broken, 1, 10) == (1, 1)


class TestTheDoubleCompilation:
    def test_the_same_line_split_differently_is_not_counted_twice(self):
        """The defect, in miniature.

        One compilation emits three statements on line 5, the other emits one, and
        the merge holds all four. Counted by statement that line weighs 4; counted
        by line it weighs 1, which is how many lines of source there are.
        """
        merged = _file({5: [1, 1, 1, 1]})
        assert len(merged["statementMap"]) == 4
        assert _statements_in_range(merged, 1, 10) == (1, 1)

    def test_coverage_from_either_level_counts(self):
        """A line vitest reached and E2E did not is covered, and vice versa —
        otherwise merging two levels would report less than either alone, which is
        exactly what the broken denominator was doing."""
        assert _statements_in_range(_file({5: [3, 0], 6: [0, 7]}), 1, 10) == (2, 2)


class TestFormatDetection:
    def test_recognises_an_istanbul_report(self):
        assert is_istanbul({"src/a.ts": {"statementMap": {}, "fnMap": {}}}) is True

    def test_rejects_a_coverage_py_report(self):
        """coverage.py wraps everything in `files`; istanbul is a flat mapping."""
        assert is_istanbul({"files": {}, "totals": {}}) is False

    def test_rejects_anything_else(self):
        assert is_istanbul({}) is False
        assert is_istanbul({"src/a.ts": {"no": "maps"}}) is False


class TestConversion:
    def test_a_function_reports_its_own_lines(self):
        data = {
            "src/lib/thing.ts": {
                "fnMap": {"0": {"name": "doThing", "loc": {"start": {"line": 1}, "end": {"line": 3}}}},
                "f": {"0": 5},
                "statementMap": {
                    "0": {"start": {"line": 2, "column": 0}, "end": {"line": 2, "column": 5}},
                    "1": {"start": {"line": 2, "column": 6}, "end": {"line": 2, "column": 9}},
                    "2": {"start": {"line": 3, "column": 0}, "end": {"line": 3, "column": 5}},
                },
                "s": {"0": 5, "1": 5, "2": 0},
            }
        }
        out = istanbul_to_analysis(data)
        fn = out["files"]["src/lib/thing.ts"]["functions"]["doThing"]
        assert fn["summary"]["num_statements"] == 2, "two lines, not three statements"
        assert fn["summary"]["missing_lines"] == 1

    def test_an_anonymous_closure_is_named_after_its_line(self):
        """Svelte compiles markup into anonymous closures, so `(anonymous_3)` is
        every entry in a `.svelte` file. A position is what a developer can act on."""
        data = {
            "src/lib/X.svelte": {
                "fnMap": {"0": {"name": "(anonymous_3)", "loc": {"start": {"line": 142}, "end": {"line": 150}}}},
                "f": {"0": 0},
                "statementMap": {"0": {"start": {"line": 143, "column": 0}, "end": {"line": 143, "column": 5}}},
                "s": {"0": 0},
            }
        }
        out = istanbul_to_analysis(data)
        assert "block@142" in out["files"]["src/lib/X.svelte"]["functions"]

    def test_a_one_expression_arrow_owning_no_statement_is_still_reported(self):
        """Otherwise an untested one-liner would vanish from the gap list rather
        than appear in it."""
        data = {
            "src/lib/y.ts": {
                "fnMap": {"0": {"name": "tiny", "loc": {"start": {"line": 1}, "end": {"line": 1}}}},
                "f": {"0": 0},
                "statementMap": {},
                "s": {},
            }
        }
        out = istanbul_to_analysis(data)
        fn = out["files"]["src/lib/y.ts"]["functions"]["tiny"]
        assert fn["summary"]["num_statements"] == 1
        assert fn["summary"]["missing_lines"] == 1

    def test_an_entry_without_a_function_map_is_skipped(self):
        assert istanbul_to_analysis({"src/a.ts": {"statementMap": {}}, "meta": "x"})["files"] == {}


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))


class TestBranchCounting:
    """Branches are the measurement that says whether a decision was *exercised*.

    A statement is covered the moment it is reached; a branch only when the
    decision has gone both ways. On this codebase the two disagree by 16 points on
    the frontend against 10 on the backend, which is the whole reason the analyser
    now reports them: the frontend's coverage is not merely smaller, it is
    shallower, and steering by statements hides exactly that.
    """

    @staticmethod
    def _file(branches: dict[int, list[int]]) -> dict:
        """Build an istanbul entry from {line: [hit counts per arm]}."""
        branch_map: dict[str, dict] = {}
        counters: dict[str, list[int]] = {}
        for i, (line, arms) in enumerate(branches.items()):
            branch_map[str(i)] = {"loc": {"start": {"line": line}, "end": {"line": line}}, "type": "if"}
            counters[str(i)] = arms
        return {"branchMap": branch_map, "b": counters, "statementMap": {}, "s": {}, "fnMap": {}, "f": {}}

    def test_counts_every_arm_not_every_branch(self):
        """An if/else is two arms, and taking one of them is half the story."""
        assert _branches_in_range(self._file({5: [3, 0]}), 1, 10) == (2, 1)

    def test_a_decision_taken_both_ways_is_fully_covered(self):
        assert _branches_in_range(self._file({5: [3, 7]}), 1, 10) == (2, 2)

    def test_a_decision_never_reached_counts_as_two_misses(self):
        assert _branches_in_range(self._file({5: [0, 0]}), 1, 10) == (2, 0)

    def test_sums_across_lines(self):
        total, covered = _branches_in_range(self._file({5: [1, 0], 6: [1, 1], 7: [0, 0]}), 1, 10)
        assert (total, covered) == (6, 3)

    def test_the_range_bounds_what_is_counted(self):
        """Branches belong to the function whose line range contains them, the
        same way statements do."""
        assert _branches_in_range(self._file({5: [1, 1], 50: [0, 0]}), 1, 10) == (2, 2)

    def test_a_file_without_branches_reports_nothing(self):
        assert _branches_in_range({"branchMap": {}, "b": {}}, 1, 10) == (0, 0)

    def test_falls_back_to_a_bare_line_field(self):
        """Older istanbul emitters put the position in `line` instead of `loc`."""
        data = {"branchMap": {"0": {"line": 5, "type": "if"}}, "b": {"0": [1, 0]}}
        assert _branches_in_range(data, 1, 10) == (2, 1)

    def test_a_branch_with_no_position_is_skipped_not_crashed(self):
        data = {"branchMap": {"0": {"type": "if"}, "1": {"loc": {"start": {"line": 5}}}}, "b": {"0": [1], "1": [1]}}
        assert _branches_in_range(data, 1, 10) == (1, 1)


class TestBranchesReachTheSummary:
    def test_a_function_reports_its_own_branch_totals(self):
        data = {
            "src/lib/x.ts": {
                "fnMap": {"0": {"name": "decide", "loc": {"start": {"line": 1}, "end": {"line": 5}}}},
                "f": {"0": 4},
                "statementMap": {"0": {"start": {"line": 2}, "end": {"line": 2}}},
                "s": {"0": 4},
                "branchMap": {"0": {"loc": {"start": {"line": 3}, "end": {"line": 3}}, "type": "if"}},
                "b": {"0": [4, 0]},
            }
        }
        summary = istanbul_to_analysis(data)["files"]["src/lib/x.ts"]["functions"]["decide"]["summary"]
        assert summary["num_branches"] == 2
        assert summary["covered_branches"] == 1
        assert summary["missing_branches"] == 1
        # …and the statement side is untouched by the addition.
        assert summary["num_statements"] == 1
        assert summary["missing_lines"] == 0

    def test_a_function_without_branches_reports_zero_not_absent(self):
        """The analyser reads `missing_branches` with a default, but a Python
        report has no branches at all — so the JS side must always supply the key
        rather than leave callers guessing."""
        data = {
            "src/lib/y.ts": {
                "fnMap": {"0": {"name": "plain", "loc": {"start": {"line": 1}, "end": {"line": 2}}}},
                "f": {"0": 1},
                "statementMap": {"0": {"start": {"line": 2}, "end": {"line": 2}}},
                "s": {"0": 1},
            }
        }
        summary = istanbul_to_analysis(data)["files"]["src/lib/y.ts"]["functions"]["plain"]["summary"]
        assert summary["num_branches"] == 0
        assert summary["missing_branches"] == 0
