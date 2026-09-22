"""Tests for the three-verdict i18n usage classifier (``scripts/i18n_usage.py``).

The gate this module replaced answered *used* / *unused* with a rule that could
never say "unused" about a third of the catalogue: when a template interpolates
at its **first** segment, the extracted prefix collapses to the bare namespace
root, and ``"risk.anything".startswith("risk")`` absolves everything beneath it.

Every test here exercises **both halves** of a verdict. A gate proven only on the
case where it fires is not proven: half of its domain is the healthy case, and
that is the half on which it grants permission. So each shape below asserts what
must be condemned *and* what must survive.

PURE: synthetic sources under ``tmp_path``. No DB, no server, no network, and no
dependency on the real catalogue, whose contents legitimately move between
mandates.
"""

import pytest

from scripts.i18n_usage import (
    DEAD,
    UNVERIFIED,
    USED,
    classify,
    collect_from_source,
    harvest_vocabulary,
)


def _tree(root, files: dict[str, str]):
    """Materialise a fake frontend/backend tree and return its root."""
    for rel, body in files.items():
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(body, encoding="utf-8")
    return root


# The exact shape that started the mandate: the interpolation sits at the first
# segment, and the set of values it can take is written in the signature.
TYPED_UNION_SOURCE = """
<script lang="ts">
    function translatedCode(prefix: 'errors' | 'warnings', code: string | null | undefined): string {
        const key = `risk.${prefix}.${code}`;
        return translate(key);
    }
</script>
"""


@pytest.fixture
def union_usage(tmp_path):
    src = _tree(tmp_path / "src", {"Frame.svelte": TYPED_UNION_SOURCE})
    backend = _tree(tmp_path / "backend", {"svc.py": 'CODES = ["flat_series", "worker_busy"]\n'})
    usage = collect_from_source(src)
    usage.vocabulary = harvest_vocabulary(backend)
    return usage


class TestTypedUnionExpansion:
    """`risk.${prefix}.${code}` must become two families, not one bare root."""

    def test_expands_the_union_into_both_families(self, union_usage):
        assert "risk.errors." in union_usage.families
        assert "risk.warnings." in union_usage.families

    def test_supersedes_the_bare_root_that_absolved_everything(self, union_usage):
        # This is the whole point: without suppression the legacy prefix "risk"
        # keeps matching every key in the namespace.
        assert "risk" in union_usage.suppressed_roots
        assert classify("risk.anything.at.all", union_usage, {"risk"}) == DEAD

    def test_a_code_the_producer_emits_is_used(self, union_usage):
        # The evidence for a runtime segment lives in whatever produces it.
        assert classify("risk.warnings.flat_series", union_usage, set()) == USED

    def test_a_code_nobody_emits_is_not_condemned_but_flagged(self, union_usage):
        # A vocabulary can only ever prove presence, so absence downgrades to
        # "not verified" — it must not promote itself to a death sentence.
        assert classify("risk.warnings.regime_truncated", union_usage, set()) == UNVERIFIED

    def test_a_key_outside_every_family_with_no_reference_is_dead(self, union_usage):
        # `risk.simulation.regimeTruncated`: four languages, rendered zero times,
        # and under no resolved family. The gate used to call this one "used".
        assert classify("risk.simulation.regimeTruncated", union_usage, {"risk"}) == DEAD


class TestConstantNamespace:
    """`$t(`${NS}.leaf`)` — the interpolation is at position zero."""

    SOURCE = """
    <script>
        const NS = 'risk.levels.l4.provenance';
        const a = $t(`${NS}.includes`);
        const b = $t(`${NS}.labels.${entry.key}`);
    </script>
    """

    @pytest.fixture
    def usage(self, tmp_path):
        return collect_from_source(_tree(tmp_path / "src", {"P.svelte": self.SOURCE}))

    def test_a_fully_resolved_template_yields_a_whole_key(self, usage):
        assert "risk.levels.l4.provenance.includes" in usage.exact

    def test_a_trailing_interpolation_yields_a_family_not_a_key(self, usage):
        assert "risk.levels.l4.provenance.labels." in usage.families
        assert classify(
            "risk.levels.l4.provenance.labels.regime", usage, set()
        ) == UNVERIFIED

    def test_a_sibling_outside_the_family_stays_dead(self, usage):
        assert classify("risk.levels.l4.provenance.gone", usage, set()) == DEAD


class TestTernaryArgument:
    """`$t(cond ? 'a.b' : 'a.c')` — both branches are literal references."""

    SOURCE = """
    <script>
        const msg = $_(count ? 'brokers.deletedWithTransactions' : 'brokers.deleted');
    </script>
    """

    @pytest.fixture
    def usage(self, tmp_path):
        return collect_from_source(_tree(tmp_path / "src", {"B.svelte": self.SOURCE}))

    @pytest.mark.parametrize(
        "key", ["brokers.deleted", "brokers.deletedWithTransactions"]
    )
    def test_both_branches_count_as_evidence(self, usage, key):
        # The old regex required the quote immediately after `(`, so a ternary
        # produced *neither* branch and both keys were reported as dead.
        assert classify(key, usage, set()) == USED

    def test_a_third_key_that_appears_in_no_branch_is_still_dead(self, usage):
        assert classify("brokers.archived", usage, set()) == DEAD


class TestUnresolvableInterpolation:
    """What cannot be resolved must be declared, never silently absolved."""

    SOURCE = """
    <script>
        const label = $t(`${somethingUnknown}.${alsoUnknown}`);
        const other = $t(`settings.${section}.title`);
    </script>
    """

    @pytest.fixture
    def usage(self, tmp_path):
        return collect_from_source(_tree(tmp_path / "src", {"U.svelte": self.SOURCE}))

    def test_a_mid_template_unknown_yields_unverified_not_used(self, usage):
        # `settings.${section}.title`: the prefix is real but the set of sections
        # is not knowable, so nothing under it may be condemned.
        assert classify("settings.display.title", usage, set()) == UNVERIFIED

    def test_an_unrelated_namespace_is_unaffected(self, usage):
        assert classify("dashboard.title", usage, set()) == DEAD


class TestVocabularyHarvest:
    def test_collects_identifier_shaped_literals_only(self, tmp_path):
        backend = _tree(
            tmp_path / "backend",
            {"m.py": 'x = "flat_series"\ny = "Some Prose Here"\nz = "low_pair_coverage"\n'},
        )
        vocab = harvest_vocabulary(backend)
        assert {"flat_series", "low_pair_coverage"} <= vocab
        assert "Some Prose Here" not in vocab

    def test_camel_case_leaf_matches_a_snake_case_code(self, tmp_path):
        src = _tree(
            tmp_path / "src",
            {"S.svelte": "const k = `risk.warnings.${code}`;\n"},
        )
        usage = collect_from_source(src)
        usage.vocabulary = harvest_vocabulary(
            _tree(tmp_path / "be", {"m.py": 'c = "low_pair_coverage"\n'})
        )
        assert classify("risk.warnings.lowPairCoverage", usage, set()) == USED

    def test_missing_backend_directory_is_not_an_error(self, tmp_path):
        assert harvest_vocabulary(tmp_path / "nope") == set()


class TestNoiseRejection:
    """Templates that are not keys must not invent namespaces."""

    SOURCE = """
    <div class={`flex ${cls} gap-2`} data-testid={`tool-docs-${item.code}`}>
        <a href={`/mkdocs/${lang}/page`}>x</a>
    </div>
    """

    def test_css_urls_and_testids_contribute_nothing(self, tmp_path):
        usage = collect_from_source(_tree(tmp_path / "src", {"N.svelte": self.SOURCE}))
        assert usage.families == {}
        assert usage.suppressed_roots == set()
