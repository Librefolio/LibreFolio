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

import re
from pathlib import Path

import pytest

import scripts.i18n_usage as U
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


class TestConditionalPrefix:
    """`${keyPrefix}.title` where the prefix is chosen between two literals.

    Unlike ``TestTernaryArgument``, the conditional is not the argument of the call
    but the *head* of a template: neither branch is a key on its own, each one has
    to be expanded through the template.
    """

    # RiskBetaBanner.svelte, reduced. The template opens on the interpolation, so it
    # has no literal head at all: the two branches are the only place its keys exist.
    SOURCE = """
    <script lang="ts">
        let {scope = 'subsystem'}: Props = $props();
        let keyPrefix = $derived(scope === 'simulation' ? 'ns.banner.simulation' : 'ns.banner');
    </script>
    <span>{$t(`${keyPrefix}.title`)}</span>
    """

    # The same shape with one branch unknown, beside a literal pair as the control.
    HALF_KNOWN_SOURCE = """
    <script>
        let p = $derived(flag ? 'ns.a' : someVariable);
        let q = $derived(flag ? 'ns.c' : 'ns.d');
    </script>
    <span>{$t(`${p}.x`)}</span>
    <span>{$t(`${q}.x`)}</span>
    """

    @pytest.fixture
    def usage(self, tmp_path):
        return collect_from_source(_tree(tmp_path / "src", {"Banner.svelte": self.SOURCE}))

    @pytest.mark.parametrize("key", ["ns.banner.title", "ns.banner.simulation.title"])
    def test_both_branches_are_evidence(self, usage, key):
        # Neither was, before: only a `const` or a typed union could resolve a name, and
        # with no literal head the template had nothing else to go on — both keys were
        # reported dead while being rendered.
        assert classify(key, usage, set()) == USED

    def test_a_key_under_neither_branch_stays_dead(self, usage):
        # Barrier first: the conditional did resolve, so the verdict below cannot be
        # the scan simply having seen nothing.
        assert classify("ns.banner.title", usage, set()) == USED
        # Two branches are two prefixes, not the namespace they share: a bare root
        # absolving everything beneath it is the very failure this gate exists to stop.
        assert classify("ns.other.title", usage, set()) == DEAD

    @pytest.mark.parametrize("key", ["ns.a.x", "ns.b.x"])
    def test_a_const_conditional_resolves_too(self, tmp_path, key):
        # Not only Svelte's `let x = $derived(...)`: a plain `const` in a .ts module.
        src = _tree(tmp_path / "src", {"keys.ts": "const p = flag ? 'ns.a' : 'ns.b';\nexport const label = t(`${p}.x`);\n"})
        assert classify(key, collect_from_source(src), set()) == USED

    def test_a_non_literal_branch_is_not_guessed(self, tmp_path):
        usage = collect_from_source(_tree(tmp_path / "src", {"Half.svelte": self.HALF_KNOWN_SOURCE}))
        # Control: the literal pair in the same file resolves, so the file was scanned
        # and the shape recognised — the verdict below is down to the unknown branch.
        assert classify("ns.c.x", usage, set()) == USED
        # One known branch of an unknown pair is not a finite set, so it is not
        # expanded: the contract is "not USED". DEAD is precisely where it lands, as
        # for a wholly unknown `${a}.${b}`: left unresolved, the template has no
        # literal head to hang even an unverified prefix on, so nothing is recorded.
        assert classify("ns.a.x", usage, set()) == DEAD

    def test_a_single_const_still_resolves(self, tmp_path):
        # The name table now maps each name to a *list* of values. A bare string
        # slipping back in would be expanded one character at a time by `list(...)`
        # — `n.leaf`, `s.leaf`, `..leaf` — and this key would quietly turn dead.
        src = _tree(tmp_path / "src", {"P.svelte": "<script>\n    const NS = 'ns.prov';\n    const a = $t(`${NS}.leaf`);\n</script>\n"})
        assert classify("ns.prov.leaf", collect_from_source(src), set()) == USED


# ---------------------------------------------------------------------------
# Second round: the defects the i18n audit measured on the real sources
# (Release_2/phases/29_i18nAudit, §5.1). One class per rule, each proven again in
# both halves. Names the module does not export yet are reached through `U.` inside
# the tests, so that a missing name fails the tests that need it and leaves every
# other test where it was.
# ---------------------------------------------------------------------------


def _line_of(text: str, needle: str) -> int:
    """1-based line of the first ``needle`` in ``text``: the origin a scan reports."""
    return text[: text.index(needle)].count("\n") + 1


# ai_export/analyses/catalog.py:77 builds the key from a reason that :92 spells,
# beside two f-strings that are no key at all.
CATALOG_PY = """
def _suggest(dataset_id: str, reason: str) -> AdditionalExportSuggestion:
    return AdditionalExportSuggestion(
        dataset_id=dataset_id,
        reason_i18n_key=f"aiExport.additionalData.reason.{reason}",
    )


SUGGESTIONS = (_suggest("portfolio.asset_history", "deeperTechnical"),)
GREETING = f"Hello {name}"
JOINED = f"{a}.{b}"
"""

# pac_allocator/evaluator.py:968, in single quotes: a family the catalogue no longer
# has a single key for (§2.4).
EVALUATOR_PY = """
def _constraint_ref(code: str) -> ConstraintRef:
    return ConstraintRef(explanation_key=f'tools.allocation.constraints.{code.lower()}')
"""

# utils/sector_fin_utils.py:24-33: display names, spaces included. The frontend strips
# them (`sectorI18nKey`, assetTypes.ts:427) before building `sectors.${…}`.
SECTORS_PY = """
class FinancialSector(str, Enum):
    HEALTH_CARE = "Health Care"
    CONSUMER_DISCRETIONARY = "Consumer Discretionary"
    TECHNOLOGY = "Technology"


UNAVAILABLE = "Price not available"
"""


class TestTestSourcesAreNotEvidence:
    """R1 — a test that names a key proves the key is tested, not that it is rendered.

    ``collect_from_source()`` walked ``*.test.ts``, ``__tests__/`` and ``__mocks__/``
    like any other source (323 files in ``src/``). Without them the exact keys drop
    from 4385 to 3611: 774 strings exist only in tests, 18 of them catalogue keys, and
    19 prefixes, among them the bare roots ``common`` and ``onboarding``, are propped
    up by fixtures such as ``src/__tests__/riskWarningCatalogue.ts``. A key that only a
    test mentions is dead to every user.
    """

    # One of each kind of evidence a scan records: a whole key, a family, an
    # unverified prefix, and a bare root superseded by a typed union.
    EVIDENCE = """
export function translatedCode(prefix: 'errors' | 'warnings', code: string): string {
    return $t(`risk.${prefix}.${code}`);
}
export const whole = $t('ns.inTests.whole');
export const family = (code: string) => $t(`ns.inTests.family.${code}`);
export const nested = (section: string) => $t(`ns.inTests.${section}.title`);
"""

    @pytest.mark.parametrize(
        "path",
        [
            "lib/Frame.test.ts",
            "lib/Frame.spec.ts",
            "lib/frame.test.js",
            "lib/frame.spec.js",
            "__tests__/riskWarningCatalogue.ts",
            "lib/stores/__mocks__/settings.ts",
        ],
    )
    def test_a_test_file_is_recognised(self, path):
        assert U.is_test_source(Path(path)) is True

    @pytest.mark.parametrize("path", ["lib/Foo.ts", "lib/Foo.svelte", "lib/testing.ts", "lib/latest.ts"])
    def test_a_production_file_is_not_mistaken_for_one(self, path):
        # A name that merely contains "test" is not a test.
        assert U.is_test_source(Path(path)) is False

    def test_the_walk_skips_tests_vendors_and_builds(self, tmp_path):
        src = _tree(
            tmp_path / "src",
            {
                "App.svelte": "",
                "lib/keys.ts": "",
                "lib/legacy.js": "",
                "lib/testing.ts": "",
                "lib/styles.css": "",
                "lib/Frame.test.ts": "",
                "lib/frame.spec.js": "",
                "__tests__/catalogue.ts": "",
                "lib/__mocks__/i18n.ts": "",
                "node_modules/pkg/index.js": "",
                "build/app.js": "",
                "lib/build/chunk.ts": "",
            },
        )
        walked = {Path(p).relative_to(src).as_posix() for p in U.iter_source_files(src)}
        # Equality: the tree is this test's own, so what is missing matters as much as what is there.
        assert walked == {"App.svelte", "lib/keys.ts", "lib/legacy.js", "lib/testing.ts"}

    @pytest.mark.parametrize("path", ["lib/Frame.test.ts", "lib/Frame.spec.ts", "__tests__/frame.ts", "lib/stores/__mocks__/frame.ts"])
    def test_a_test_source_contributes_nothing(self, tmp_path, path):
        # Control: the same text as a production file yields every kind of evidence...
        control = collect_from_source(_tree(tmp_path / "control", {"lib/Frame.ts": self.EVIDENCE}))
        assert "ns.inTests.whole" in control.exact
        assert "ns.inTests.family." in control.families
        assert "ns.inTests" in control.unverified_prefixes
        assert "risk" in control.suppressed_roots
        # ...and none of it once the file is a test.
        usage = collect_from_source(_tree(tmp_path / "subject", {path: self.EVIDENCE}))
        assert usage.exact == set()
        assert usage.families == {}
        assert usage.unverified_prefixes == {}
        assert usage.suppressed_roots == set()

    def test_a_key_only_tests_mention_is_dead(self, tmp_path):
        src = _tree(
            tmp_path / "src",
            {
                "lib/Real.svelte": "<span>{$t('ns.real.key')}</span>\n",
                "lib/Real.test.ts": "expect(render($t('ns.tested.only'))).toBeTruthy();\nconst k = $t(`ns.tested.family.${code}`);\n",
                "lib/__mocks__/catalogue.ts": "export const fixture = {label: 'ns.mocked.only'};\n",
            },
        )
        usage = collect_from_source(src)
        # Barrier: the production file was read.
        assert classify("ns.real.key", usage, set()) == USED
        assert classify("ns.tested.only", usage, set()) == DEAD
        assert classify("ns.tested.family.anything", usage, set()) == DEAD
        assert classify("ns.mocked.only", usage, set()) == DEAD


class TestLiteralKeyReferences:
    """R2 — a quoted key is a reference, whoever carries it to the translator.

    ``_CALL`` knows four callee names (``t``, ``$t``, ``_``, ``$_``), and a key outside
    their parentheses did not exist: 93 live keys were reported dead. The shapes below
    are the real ones: wrappers (``translateOr($_, 'k', 'fb')`` at
    ``LotWacPriceChart.svelte:608-622``, ``label('k', 'fb')`` at
    ``YieldOnCostCell.svelte:49-71``, ``translate('k')`` inside a template at
    ``promptRenderer.ts:306-316``, ``tr('k', {…})`` at ``modeText.ts:21``), a key held
    in a property (``afterCopyKey`` at ``support/supportLinks.ts:37-53``), a multi-line
    ternary (``ChartSettingsModal.svelte:337-345``) and an array whose segments carry a
    digit (``OnboardingIntroScene.svelte:26``, ``onboarding.intro.line2``).

    The healthy half: a literal proves the key it spells, exactly. Not a key it is a
    prefix of, not a key named inside prose, and a template that interpolates is no
    literal at all.
    """

    WRAPPERS = """
import {translateOr} from '$lib/utils/core/translateOr';

export const openingValue = ($_: Translate) => translateOr($_, 'ns.markers.openingValue', 'Opening value');

export function yieldReason(reason: string | null, label: (key: string, fallback: string) => string): string {
    const labels: Record<string, [string, string]> = {
        non_positive_wac: ['ns.yield.reasons.nonPositiveWac', 'The average purchase price (WAC) is zero or negative.'],
    };
    const entry = reason ? labels[reason] : undefined;
    return entry ? label(entry[0], entry[1]) : label('ns.yield.unavailable', 'Yield on Cost is unavailable.');
}

export const promptLine = (translate: (key: string) => string) => `- **${translate('ns.export.what')}**: ${translate(dataset.description_i18n_key)}`;

export const unitsText = (tr: PlannerTranslate) => tr('ns.planner.units.shares', {default: 'units'});
"""

    COMPONENT = """
<script lang="ts">
    const SHARE = {
        facebook: {label: 'Facebook', afterCopyKey: 'ns.share.facebook.afterCopy'},
    };
    let previewKey = $derived(
        backendState === 'real-target-required'
            ? 'ns.preview.realTarget'
            : backendState === 'apply-required'
              ? 'ns.preview.apply'
              : null,
    );
    const phaseKeys = ['ns.intro.line1', 'ns.intro.line2', 'ns.intro.line3'] as const;
    const plain = `ns.backtick.plain`;
</script>

<GuideAnchor titleKey="ns.guide.title" />
"""

    @pytest.fixture
    def usage(self, tmp_path):
        return collect_from_source(_tree(tmp_path / "src", {"lib/wrappers.ts": self.WRAPPERS, "lib/Links.svelte": self.COMPONENT}))

    @pytest.mark.parametrize(
        "key",
        [
            "ns.markers.openingValue",
            "ns.yield.reasons.nonPositiveWac",
            "ns.yield.unavailable",
            "ns.export.what",
            "ns.planner.units.shares",
            "ns.share.facebook.afterCopy",
            "ns.preview.realTarget",
            "ns.preview.apply",
            "ns.intro.line2",
            "ns.guide.title",
            "ns.backtick.plain",
        ],
    )
    def test_a_quoted_key_is_a_reference_wherever_it_stands(self, usage, key):
        assert classify(key, usage, set()) == USED

    def test_a_literal_proves_only_the_key_it_spells(self, tmp_path):
        usage = collect_from_source(_tree(tmp_path / "src", {"keys.ts": "export const NS = 'ns.prefix.only';\n"}))
        assert classify("ns.prefix.only", usage, set()) == USED
        # Neither a key it is the prefix of, nor the prefix it extends.
        assert classify("ns.prefix.only.child", usage, set()) == DEAD
        assert classify("ns.prefix", usage, set()) == DEAD

    def test_a_template_with_an_interpolation_is_not_a_literal(self, tmp_path):
        source = "export const plain = `ns.tpl.plain`;\nexport const built = (kind: string) => $t(`ns.tpl.${kind}`);\n"
        usage = collect_from_source(_tree(tmp_path / "src", {"keys.ts": source}))
        # Barrier: without an interpolation, a backtick quotes like any other quote.
        assert classify("ns.tpl.plain", usage, set()) == USED
        # With one it is a family at best: neither its head nor the name it
        # interpolates is a key it spells.
        assert classify("ns.tpl", usage, set()) == DEAD
        assert classify("ns.tpl.kind", usage, set()) == UNVERIFIED

    def test_a_key_named_in_prose_or_a_comment_is_not_a_reference(self, tmp_path):
        source = """
// Rendered as ns.comment.mentioned by the parent.
export const hint = 'Falls back to ns.prose.mentioned when empty';
export const real = 'ns.prose.real';
"""
        usage = collect_from_source(_tree(tmp_path / "src", {"hint.ts": source}))
        # Barrier: the file was read and its one real literal counted.
        assert classify("ns.prose.real", usage, set()) == USED
        assert classify("ns.prose.mentioned", usage, set()) == DEAD
        assert classify("ns.comment.mentioned", usage, set()) == DEAD


class TestBackendKeyLiterals:
    """R2, backend — a key the backend keeps in a dictionary is still a key it emits.

    The old scan read the backend only in ``…_i18n_key="literal"`` assignments
    (``i18n-audit.py:208``). ``_message_key_for_issue()`` at
    ``lots_analysis_service.py:2027-2039`` keeps its nine ``dataQuality.*`` keys as
    dictionary values and reaches ``message_i18n_key=`` through a call (``:1892``), so
    ``DataQualityBanner.svelte:158`` rendered keys the audit called dead.
    """

    MAPPING = """
import logging

logger = logging.getLogger(__name__)


def _message_key_for_issue(code: IssueCode) -> str:
    # dataQuality.inCommentOnly is named here, not referenced.
    mapping = {
        IssueCode.REFERENCE_PRICE_FALLBACK: "dataQuality.referencePriceFallback",
        IssueCode.TRANSFER_PAIR_MISSING: 'dataQuality.transferPairMissing',
    }
    if code not in mapping:
        logger.warning("No message for dataQuality.inProseOnly yet")
    return mapping[code]


SEVERITY = "flat_series"
"""

    def test_a_dictionary_value_is_a_key_reference(self, tmp_path):
        backend = _tree(tmp_path / "backend", {"services/lots_analysis_service.py": self.MAPPING})
        assert {"dataQuality.referencePriceFallback", "dataQuality.transferPairMissing"} <= U.harvest_backend_keys(backend)

    def test_prose_comments_and_bare_codes_are_not_keys(self, tmp_path):
        keys = U.harvest_backend_keys(_tree(tmp_path / "backend", {"services/lots_analysis_service.py": self.MAPPING}))
        # Barrier: the file was read.
        assert "dataQuality.referencePriceFallback" in keys
        assert "dataQuality.inProseOnly" not in keys
        assert "dataQuality.inCommentOnly" not in keys
        assert "flat_series" not in keys
        # Whole literals only: a key-shaped fragment of a longer string is not one.
        assert all(re.fullmatch(r"[A-Za-z0-9_]+(?:\.[A-Za-z0-9_]+)+", key) for key in keys)

    def test_only_python_sources_outside_pycache_are_read(self, tmp_path):
        backend = _tree(
            tmp_path / "backend",
            {
                "app/svc.py": 'KEY = "ns.live.key"\n',
                "app/__pycache__/svc.py": 'KEY = "ns.cached.key"\n',
                "app/data/seed.json": '{"label": "ns.json.key"}\n',
            },
        )
        keys = U.harvest_backend_keys(backend)
        assert "ns.live.key" in keys
        assert "ns.cached.key" not in keys
        assert "ns.json.key" not in keys

    def test_a_missing_backend_directory_is_not_an_error(self, tmp_path):
        assert U.harvest_backend_keys(tmp_path / "nope") == set()


class TestSingleLiteralParameterType:
    """R3 — a parameter typed with one literal is a finite set too: a set of one.

    The regression behind defect 6. ``RiskResultFrame.svelte:27-29`` now reads
    ``function translatedCode(prefix: 'errors', code: string | null | undefined,
    fallbackKey: string)`` and builds ``risk.${prefix}.${code}``. ``_union_members``
    wants two members or more, returns ``None`` for one, and the template falls back to
    the bare root ``risk``, which absolves all 481 ``risk.*`` keys again, among them
    ``risk.simulation.regimeTruncated`` (§2.3), referenced nowhere.
    ``TestTypedUnionExpansion`` stayed green throughout: it only knows the synthetic
    ``'errors' | 'warnings'`` shape.

    The healthy half: only a *type* bounds a name. ``{prefix: 'warnings'}`` gives a
    property a value, says nothing about what ``${prefix}`` holds, and must not expand.
    """

    # RiskResultFrame.svelte:27-32 as it reads today. The signature line is swapped
    # for its arrow form in the second run, which must expand identically.
    FRAME = """
<script lang="ts">
    SIGNATURE
        if (!code) return $t(fallbackKey);
        const key = `risk.${prefix}.${code}`;
        const translated = $t(key);
        return translated === key ? $t(fallbackKey) : translated;
    }
</script>
"""
    SIGNATURES = {
        "function": "function translatedCode(prefix: 'errors', code: string | null | undefined, fallbackKey: string): string {",
        "arrow": "const translatedCode = (prefix: 'errors', code: string | null | undefined, fallbackKey: string): string => {",
    }

    # The same name and the same template, but `prefix` is the key of an object
    # literal: what follows its colon is a value, and nothing here bounds `${prefix}`.
    REQUEST = """
const request = OBJECT;
export const key = `risk.${prefix}.${code}`;
"""

    @pytest.fixture(params=["function", "arrow"])
    def usage(self, request, tmp_path):
        source = self.FRAME.replace("SIGNATURE", self.SIGNATURES[request.param])
        return collect_from_source(_tree(tmp_path / "src", {"RiskResultFrame.svelte": source}))

    def test_the_real_signature_expands_into_its_family(self, usage):
        assert "risk.errors." in usage.families
        assert "risk" in usage.suppressed_roots

    def test_the_bare_root_no_longer_absolves_the_namespace(self, usage):
        # Four languages, rendered zero times, and "used" for as long as `risk` absolved it.
        assert classify("risk.simulation.regimeTruncated", usage, {"risk"}) == DEAD

    def test_a_code_under_the_family_is_flagged_not_absolved(self, usage):
        assert classify("risk.errors.worker_busy", usage, {"risk"}) == UNVERIFIED

    @pytest.mark.parametrize("literal", ["{prefix: 'warnings', limit: 3}", "{limit: 3, prefix: 'warnings'}"])
    def test_an_object_property_is_a_value_not_a_type(self, tmp_path, literal):
        src = _tree(
            tmp_path / "src",
            {
                "RiskResultFrame.svelte": self.FRAME.replace("SIGNATURE", self.SIGNATURES["function"]),
                "request.ts": self.REQUEST.replace("OBJECT", literal),
            },
        )
        usage = collect_from_source(src)
        # Barrier: in the same tree, the parameter type does expand.
        assert "risk.errors." in usage.families
        assert "risk.warnings." not in usage.families


class TestBackendFamiliesAndVocabulary:
    """R4 — the backend builds keys too, and its codes come in every case.

    Two blind spots, one effect. The backend was read only in ``…_i18n_key="literal"``
    assignments, so the f-string at ``ai_export/analyses/catalog.py:77``
    (``reason_i18n_key=f"aiExport.additionalData.reason.{reason}"``) built a family the
    audit never saw. And the producer vocabulary was lowercase snake_case only
    (``_CODE_LITERAL``): the reason ``"deeperTechnical"`` (``:92``), the provider codes
    behind ``providerErrors.${code}`` (``resolveProviderError.ts:48``, ``"NO_DATA"``) and
    the sector names behind ``sectors.${sectorI18nKey(entry.name)}``
    (``AllocationPieChart.svelte:177``; ``"Health Care"`` at ``sector_fin_utils.py:24-33``
    loses its space at ``assetTypes.ts:427``) could never prove a key.
    """

    # resolveProviderError.ts:48: the code arrives from the providers, in UPPER_SNAKE.
    PROVIDER_ERROR = """
export function resolveProviderError(op: Operation): string {
    const code = op.error_code;
    const key = `providerErrors.${code}`;
    const translated = t(key, {values});
    return translated !== key ? translated : op.error;
}
"""

    # AllocationPieChart.svelte:177
    PIE = """
<script lang="ts">
    const mapped = entries.map((entry) => {
        const i18nKey = `sectors.${sectorI18nKey(entry.name)}`;
        return tr(i18nKey) !== i18nKey ? tr(i18nKey) : entry.name;
    });
</script>
"""

    def test_an_f_string_with_a_dotted_head_is_a_family(self, tmp_path):
        backend = _tree(
            tmp_path / "backend",
            {
                "services/ai_export/analyses/catalog.py": CATALOG_PY,
                "services/pac_allocator/evaluator.py": EVALUATOR_PY,
            },
        )
        # Equality: `f"Hello {name}"` and `f"{a}.{b}"` sit in the same file without a
        # dotted head, so they must add nothing.
        assert U.harvest_backend_families(backend) == {
            "aiExport.additionalData.reason.": f"catalog.py:{_line_of(CATALOG_PY, 'reason_i18n_key=')}",
            "tools.allocation.constraints.": f"evaluator.py:{_line_of(EVALUATOR_PY, 'explanation_key=')}",
        }

    def test_a_missing_backend_directory_has_no_family(self, tmp_path):
        assert U.harvest_backend_families(tmp_path / "nope") == {}

    def test_every_identifier_case_is_vocabulary(self, tmp_path):
        backend = _tree(tmp_path / "backend", {"codes.py": 'SNAKE = "flat_series"\nCAMEL = "deeperTechnical"\nUPPER = "FETCH_ERROR"\n'})
        assert {"flat_series", "deeperTechnical", "FETCH_ERROR"} <= harvest_vocabulary(backend)

    def test_a_title_case_name_is_vocabulary_without_its_spaces(self, tmp_path):
        vocab = harvest_vocabulary(_tree(tmp_path / "backend", {"utils/sector_fin_utils.py": SECTORS_PY}))
        assert {"HealthCare", "ConsumerDiscretionary", "Technology"} <= vocab
        # Only the collapsed name: the phrase itself is no code, and a sentence is no name.
        assert "Health Care" not in vocab
        assert "Pricenotavailable" not in vocab

    def test_a_backend_family_is_used_through_a_reason_the_backend_spells(self, tmp_path):
        backend = _tree(tmp_path / "backend", {"services/ai_export/analyses/catalog.py": CATALOG_PY})
        usage = collect_from_source(_tree(tmp_path / "src", {"Empty.svelte": "<p>no keys here</p>\n"}))
        usage.families.update(U.harvest_backend_families(backend))
        usage.vocabulary = harvest_vocabulary(backend)
        assert classify("aiExport.additionalData.reason.deeperTechnical", usage, set()) == USED
        # A reason nobody suggests: the family is real, the leaf unproven. Flagged, not condemned.
        assert classify("aiExport.additionalData.reason.neverSuggested", usage, set()) == UNVERIFIED
        assert classify("aiExport.additionalData.title", usage, set()) == DEAD

    def test_an_upper_snake_code_reaches_its_provider_key(self, tmp_path):
        usage = collect_from_source(_tree(tmp_path / "src", {"resolveProviderError.ts": self.PROVIDER_ERROR}))
        usage.vocabulary = harvest_vocabulary(_tree(tmp_path / "backend", {"providers/base.py": 'raise ProviderError(code="NO_DATA", message="No data in range")\n'}))
        assert classify("providerErrors.NO_DATA", usage, set()) == USED
        assert classify("providerErrors.NEVER_RAISED", usage, set()) == UNVERIFIED

    def test_a_title_case_sector_reaches_its_key(self, tmp_path):
        usage = collect_from_source(_tree(tmp_path / "src", {"AllocationPieChart.svelte": self.PIE}))
        usage.vocabulary = harvest_vocabulary(_tree(tmp_path / "backend", {"utils/sector_fin_utils.py": SECTORS_PY}))
        assert classify("sectors.HealthCare", usage, set()) == USED
        assert classify("sectors.Cryptocurrency", usage, set()) == UNVERIFIED


class TestSameFileEvidence:
    """R5 — the file that completes a family often spells the rest of the key.

    A family only knows its prefix, so every key under it read "not verified": 50 keys
    whose rest is written a few lines from the template that completes them.
    ``KpiCards.svelte:45`` resolves ``text('compute.title')`` against
    ``const KEY = '…result.kpi'``, and ``tile()`` (``:96-110``) adds a second hop through
    ``text(`help.${key}`)``; ``ImportWizardModal.svelte:135-143`` lists the step titles
    that ``:4258`` reads as ``importWizard.${step.titleKey}``;
    ``ChartSignalsSection.svelte:435-441`` maps event types to the badge keys that
    ``:570`` reads as ``chartSettings.${EVENT_BADGE_KEY[evType] ?? 'badgePoints'}``.

    The healthy half is why the rule is narrow. Under a wide family such as ``ns.``,
    any word the file happens to quote would absolve the namespace again, the very
    failure this gate exists to stop. So a quoted rest counts only under a narrow
    family (two dots or more), while a property or a map that the interpolation itself
    names counts under any family. And only in the file that builds it.
    """

    # planner/result/KpiCards.svelte, reduced.
    KPI = """
<script lang="ts">
    const KEY = 'ns.tool.kpi';
    const HELP_FALLBACKS = {fixedReference: 'The amount the targets apply to.'};
    const text = (key: string, fallback: string) => $t(`${KEY}.${key}`, {default: fallback});
    const tile = (kpi: string, key: string, fallback: string, help: string) => ({kpi, label: text(key, fallback), help: text(`help.${key}`, help)});
    const reachable = text('parts.reachable', 'Reachable cash');
    const compute = text('compute.title', 'Calculation');
    const tiles = [tile('final_invested', 'finalInvested', 'Invested after', 'The value of the chosen Assets after the plan.')];
</script>
"""

    # One file, one quoted word, two families: the narrow one may read it, the wide one may not.
    PAIR = """
<script lang="ts">
    const SECTIONS = ['assets', 'orders'] as const;
    const section = (code: string) => $t(`ns.tool.result.${code}`);
    const anywhere = (code: string) => $t(`ns.${code}`);
</script>
"""

    # ImportWizardModal.svelte:133-143 and :4258: a property, read through a WIDE family.
    STEPS = """
<script lang="ts">
    type StepId = 'upload' | 'review' | 'gapFix';
    const STEP_DEFS: ReadonlyArray<{id: StepId; titleKey: string}> = [
        {id: 'upload', titleKey: 'step1Title'},
        {id: 'review', titleKey: 'step4Title'},
        {id: 'gapFix', titleKey: 'reportSet.gapFix.stepTitle'},
    ];
    let phase = $state('parsing');
</script>

{#each STEP_DEFS as step}
    <span>{$t(`ns.${step.titleKey}`)}</span>
{/each}
"""

    # ChartSignalsSection.svelte:435-441 and :570: a map, read through a WIDE family.
    BADGES = """
<script lang="ts">
    /** Map event type → i18n badge key suffix */
    const EVENT_BADGE_KEY: Record<string, string> = {
        DIVIDEND: 'badgeDividend',
        SPLIT: 'badgeSplit',
    };
    const density = 'badgeCompact';
</script>

<Tooltip text={$t(`ns.${EVENT_BADGE_KEY[evType] ?? 'badgePoints'}`, {values: {n: count}})} position="top" />
"""

    @pytest.fixture
    def kpi_usage(self, tmp_path):
        return collect_from_source(_tree(tmp_path / "src", {"KpiCards.svelte": self.KPI}))

    @pytest.fixture
    def steps_usage(self, tmp_path):
        return collect_from_source(_tree(tmp_path / "src", {"ImportWizardModal.svelte": self.STEPS}))

    @pytest.fixture
    def badge_usage(self, tmp_path):
        return collect_from_source(_tree(tmp_path / "src", {"ChartSignalsSection.svelte": self.BADGES}))

    @pytest.mark.parametrize(
        "key",
        [
            "ns.tool.kpi.compute.title",  # the rest quoted whole, dots and all
            "ns.tool.kpi.finalInvested",  # a one-segment rest
            "ns.tool.kpi.help.finalInvested",  # `help.${key}` plus a quoted leaf
            "ns.tool.kpi.help.fixedReference",  # `help.${key}` plus a leaf written as an object key
        ],
    )
    def test_a_rest_the_same_file_spells_is_used(self, kpi_usage, key):
        assert classify(key, kpi_usage, set()) == USED

    def test_a_rest_the_file_does_not_spell_is_not(self, kpi_usage):
        # Barrier: this family does read its file.
        assert classify("ns.tool.kpi.finalInvested", kpi_usage, set()) == USED
        # Under the family with nothing to read: flagged, never condemned.
        assert classify("ns.tool.kpi.shortfallParts", kpi_usage, set()) == UNVERIFIED
        # The second hop needs both of its halves: the leaf, and a template adding `mid.`.
        assert classify("ns.tool.kpi.help.shortfall", kpi_usage, set()) != USED
        assert classify("ns.tool.kpi.notes.finalInvested", kpi_usage, set()) != USED
        # Outside every family, dead as before.
        assert classify("ns.tool.other.title", kpi_usage, set()) == DEAD

    def test_only_a_narrow_family_reads_a_quoted_word(self, tmp_path):
        usage = collect_from_source(_tree(tmp_path / "src", {"ResultView.svelte": self.PAIR}))
        assert classify("ns.tool.result.assets", usage, set()) == USED
        # The same word under `ns.`: the shape of the false "used" on
        # `tools.pacAllocator.planner.result.sections.assets` (§2.3).
        assert classify("ns.assets", usage, set()) == UNVERIFIED
        assert classify("ns.tool.result.trades", usage, set()) == UNVERIFIED

    def test_the_evidence_must_sit_in_the_file_that_builds_the_family(self, tmp_path):
        src = _tree(
            tmp_path / "src",
            {
                "Kpi.svelte": "<script>\n    const KEY = 'ns.tool.kpi';\n    const text = (key: string) => $t(`${KEY}.${key}`);\n    const a = text('inFile');\n</script>\n",
                "Other.svelte": "<script>\n    const word = 'elsewhere';\n</script>\n",
            },
        )
        usage = collect_from_source(src)
        assert classify("ns.tool.kpi.inFile", usage, set()) == USED
        assert classify("ns.tool.kpi.elsewhere", usage, set()) == UNVERIFIED

    @pytest.mark.parametrize("key", ["ns.step1Title", "ns.reportSet.gapFix.stepTitle"])
    def test_a_value_of_the_interpolated_property_is_used(self, steps_usage, key):
        assert classify(key, steps_usage, set()) == USED

    def test_no_other_quoted_word_reaches_the_wide_family(self, steps_usage):
        assert classify("ns.step1Title", steps_usage, set()) == USED
        # Quoted in the file, but as an `id:`, not as a `titleKey:`...
        assert classify("ns.upload", steps_usage, set()) == UNVERIFIED
        # ...or as nothing in particular: `ns.` is wide, a quoted word is not enough.
        assert classify("ns.parsing", steps_usage, set()) == UNVERIFIED
        assert classify("other.step1Title", steps_usage, set()) == DEAD

    @pytest.mark.parametrize("key", ["ns.badgeDividend", "ns.badgePoints"])
    def test_a_value_of_the_indexed_map_or_its_fallback_is_used(self, badge_usage, key):
        assert classify(key, badge_usage, set()) == USED

    def test_the_map_keys_and_other_words_are_not(self, badge_usage):
        assert classify("ns.badgeDividend", badge_usage, set()) == USED
        # A map's keys are what it is indexed with, not what it yields...
        assert classify("ns.DIVIDEND", badge_usage, set()) == UNVERIFIED
        # ...and a word quoted beside it is not one of its values.
        assert classify("ns.badgeCompact", badge_usage, set()) == UNVERIFIED


class TestSuffixComposition:
    """R6 — ``${definition.displayNameKey}Full``: a key the sources spell, plus a suffix.

    ``ChartSignalsSection.svelte:142`` builds the long name of a signal by appending
    ``Full`` to its ``displayNameKey``, whose values are literals in
    ``charts/signals/registry.ts:91-107``. The template opens on an interpolation, so it
    has no literal head and the scan dropped it: every ``…Full`` key read as dead. Their
    ``…Abbr`` siblings have no such template, and are the doubtful keys of §2.2.
    """

    REGISTRY = """
export const SIGNALS = [
    {type: 'fx_pair', displayNameKey: 'ns.signals.fxPair'},
    {type: 'linear', displayNameKey: 'ns.signals.linear'},
];
"""

    SECTION = """
<script lang="ts">
    function getSignalSubtitle(definition: SignalDefinition): string {
        if (definition.source === 'backend') return translatedValue(definition.descriptionKey);
        const fullKey = definition.displayNameKey ? `${definition.displayNameKey}Full` : undefined;
        return translatedValue(fullKey) || translatedValue(definition.descriptionKey);
    }
    const childKey = (definition: SignalDefinition) => `${definition.displayNameKey}.title`;
</script>
"""

    @pytest.fixture
    def usage(self, tmp_path):
        src = _tree(tmp_path / "src", {"charts/signals/registry.ts": self.REGISTRY, "components/ChartSignalsSection.svelte": self.SECTION})
        return collect_from_source(src)

    @pytest.mark.parametrize("key", ["ns.signals.fxPairFull", "ns.signals.linearFull"])
    def test_a_spelled_key_plus_the_written_suffix_is_used(self, usage, key):
        assert classify(key, usage, set()) == USED

    def test_a_suffix_proves_nothing_without_its_template_or_its_base(self, usage):
        # Barrier: the base key is itself a literal reference (R2).
        assert classify("ns.signals.fxPair", usage, set()) == USED
        # `Abbr` has no template: the doubtful `*Abbr` keys stay dead.
        assert classify("ns.signals.fxPairAbbr", usage, set()) == DEAD
        # `Full` extends keys the sources spell, not any key at all.
        assert classify("ns.signals.sineFull", usage, set()) == DEAD
        # `.title` is a child path, not a suffix: nothing says which keys have one.
        assert classify("ns.signals.fxPair.title", usage, set()) == DEAD


class TestPhantomFamilies:
    """R7 — a family no catalogue key answers is reported, not silently kept.

    ``pac_allocator/evaluator.py:968`` still writes
    ``explanation_key=f"tools.allocation.constraints.{code.lower()}"``, while the
    catalogue has had no ``tools.allocation.*`` key since D's row 13 (§2.4). Nothing
    reads it today, which is exactly why nobody noticed: a family that can only ever
    render its raw key is a promise the audit has to surface, as a report section and
    not as a failure.
    """

    def test_a_family_with_no_key_beneath_it_is_reported(self):
        families = {
            "tools.allocation.constraints.": "evaluator.py:968",
            "aiExport.additionalData.reason.": "catalog.py:77",
        }
        keys = ["aiExport.additionalData.reason.deeperTechnical", "tools.pacAllocator.planner.title"]
        assert U.phantom_families(families, keys) == ["tools.allocation.constraints."]

    def test_phantoms_come_back_sorted(self):
        families = {"zeta.b.": "z.py:1", "alpha.b.": "a.py:1", "mid.b.": "m.py:1"}
        assert U.phantom_families(families, ["mid.b.leaf"]) == ["alpha.b.", "zeta.b."]

    def test_the_keys_may_be_a_one_shot_iterable(self):
        # Read once: a scan that walks the keys again for every family finds them
        # exhausted after the first, and reports a live family as a phantom.
        families = {"a.phantom.": "a.py:1", "b.live.": "b.py:1"}
        assert U.phantom_families(families, iter(["b.live.leaf"])) == ["a.phantom."]

    def test_the_harvested_backend_families_feed_the_report(self, tmp_path):
        backend = _tree(tmp_path / "backend", {"catalog.py": CATALOG_PY, "evaluator.py": EVALUATOR_PY})
        families = U.harvest_backend_families(backend)
        assert U.phantom_families(families, ["aiExport.additionalData.reason.deeperTechnical"]) == ["tools.allocation.constraints."]


class TestNestedTemplates:
    """§5.3 — a template nested in another template's interpolation is still a template.

    ``_TEMPLATE`` pairs backticks one after the other, so when an outer template calls
    ``$t`` on an inner one it matches the outer opening with the *inner* opening and
    never sees the key: ``CorrelationHeatmap.svelte:487-488`` builds
    ``risk.assetSet.band.${band}`` and ``risk.valueStatus.${item.status}`` this way, and
    those families survive today only through the legacy prefixes. Two shapes of the
    same blindness ride along: a camelCase continuation whose prefix does not end on a
    dot (``SchedulerConfigModal.svelte:163``, ``historyDays${…}``) and a concatenation
    that is no template at all (``ParseDetailModal.svelte:315``,
    ``$t('transactions.types.' + type)``).
    """

    # CorrelationHeatmap.svelte:485-488, reduced: a template inside an interpolation,
    # a third one inside a ternary inside the same template, a quoted key at the bottom.
    HEATMAP = """
<script lang="ts">
    const SHOWN = ['ok', 'stale'] as const;
    function reading(item: Item, value: number, band: string | null): string {
        return typeof value === 'number' && band
            ? `<div style="font-weight:600">ρ = ${value.toFixed(3)} · ${$t(`ns.band.${band}`)}${value >= NEAR_IDENTICAL ? ` · ${$t('ns.nearIdentical')}` : ''}</div>`
            : `<div style="font-weight:600">${$t(`ns.valueStatus.${item.status}`)}</div>`;
    }
</script>
"""

    @pytest.fixture
    def heatmap_usage(self, tmp_path):
        return collect_from_source(_tree(tmp_path / "src", {"CorrelationHeatmap.svelte": self.HEATMAP}))

    @pytest.mark.parametrize(
        ("source", "family"),
        [
            ('const html = `<div style="x">${$t(`ns.valueStatus.${item.status}`)}</div>`;\n', "ns.valueStatus."),
            ("const label = `ρ = ${v.toFixed(3)} · ${$t(`ns.band.${b}`)}`;\n", "ns.band."),
        ],
        ids=["markup", "prose"],
    )
    def test_an_inner_template_is_found_exactly(self, tmp_path, source, family):
        usage = collect_from_source(_tree(tmp_path / "src", {"Tooltip.ts": source}))
        assert family in usage.families
        # Exactly: no fragment of the outer markup passes for a family.
        assert all(re.fullmatch(r"[A-Za-z0-9_.]+", found) for found in usage.families)
        assert classify(f"{family}someLeaf", usage, set()) == UNVERIFIED

    def test_every_level_of_nesting_is_read(self, heatmap_usage):
        assert {"ns.band.", "ns.valueStatus."} <= set(heatmap_usage.families)
        assert all(re.fullmatch(r"[A-Za-z0-9_.]+", found) for found in heatmap_usage.families)
        assert classify("ns.nearIdentical", heatmap_usage, set()) == USED

    def test_an_inner_family_reads_its_file_like_any_other(self, heatmap_usage):
        # `ns.valueStatus.` is narrow (R5) and the file spells 'ok'.
        assert classify("ns.valueStatus.ok", heatmap_usage, set()) == USED
        assert classify("ns.valueStatus.missing", heatmap_usage, set()) == UNVERIFIED
        assert classify("ns.band.high", heatmap_usage, set()) == UNVERIFIED
        assert classify("ns.elsewhere.title", heatmap_usage, set()) == DEAD

    def test_a_markup_apostrophe_does_not_unbalance_the_scan(self, tmp_path):
        source = "<p>Don't stop</p>\n<span title={`<b>${$t(`ns.mode.${item.mode}`)}</b>`}>x</span>\n"
        usage = collect_from_source(_tree(tmp_path / "src", {"Hint.svelte": source}))
        assert "ns.mode." in usage.families
        assert classify("ns.mode.compact", usage, set()) == UNVERIFIED

    def test_a_camel_case_continuation_is_a_family(self, tmp_path):
        source = """
<script lang="ts">
    const DAYS = ['Mon', 'Tue'] as const;
    const dayLabel = (day: string) => $t(`ns.sched.historyDays${day}`);
</script>
"""
        usage = collect_from_source(_tree(tmp_path / "src", {"Scheduler.svelte": source}))
        assert classify("ns.sched.historyDaysMon", usage, set()) == USED
        assert classify("ns.sched.historyDaysSun", usage, set()) == UNVERIFIED
        # The family is the continuation, not the namespace it continues.
        assert classify("ns.sched.other", usage, set()) == DEAD

    def test_the_real_capitalising_continuation_is_not_condemned(self, tmp_path):
        # SchedulerConfigModal.svelte:56,163: spelled lowercase, capitalised at runtime.
        source = """
<script lang="ts">
    const DAY_KEYS = ['mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun'] as const;
    function historyLabel(day: string): string {
        const key = `ns.sched.historyDays${day.charAt(0).toUpperCase() + day.slice(1)}`;
        return $_(key);
    }
</script>
"""
        usage = collect_from_source(_tree(tmp_path / "src", {"SchedulerConfigModal.svelte": source}))
        assert classify("ns.sched.historyDaysMon", usage, set()) in {UNVERIFIED, USED}
        assert classify("ns.sched.other", usage, set()) == DEAD

    def test_a_concatenated_prefix_is_a_family(self, tmp_path):
        usage = collect_from_source(_tree(tmp_path / "src", {"ParseDetailModal.svelte": "<span>{$t('ns.cat.' + type)}</span>\n"}))
        assert "ns.cat." in usage.families
        assert classify("ns.cat.BUY", usage, set()) == UNVERIFIED
        assert classify("ns.other.BUY", usage, set()) == DEAD


# ---------------------------------------------------------------------------
# Third round (R8-R12). On the release tip (d07412899) 78 live keys still read "not
# verified": the evidence for their last segment sits in a module the family's file
# imports, in a backend code of another case or with a leading digit, or behind several
# runtime segments. And a key read only by a component nobody imports still reads
# "used". Same discipline as above: one class per rule, both halves, and the names the
# module does not export yet reached through `U.` inside the tests.
# ---------------------------------------------------------------------------


def _relative(src: Path, paths) -> set[str]:
    """``paths`` relative to ``src``, in POSIX form: what a test compares on any OS."""
    return {Path(p).relative_to(src).as_posix() for p in paths}


class TestOneImportHop:
    """R8 — a narrow family also reads the words of the modules its file imports directly.

    R5 lets the file that builds a family name its members, but the members often sit one
    import away. ``CorrelationHeatmap.svelte:487`` builds ``risk.assetSet.band.${band}``,
    and the bands are the union ``export type CorrelationBand = 'high' | 'moderate' |
    'low' | 'inverse'`` at ``correlationHelpers.ts:59``, imported at ``:53-71``:
    ``moderate`` is spelled nowhere else. ``SimulationProvenance.svelte:46`` builds
    ``${NS}.effects.${effect}`` under ``const NS = 'risk.levels.l4.provenance'`` (``:22``),
    and the effects are spelled in ``simulationProvenance.ts:40,60-65``, imported for its
    types only (``:6``). ``L4Simulation.svelte:163`` interpolates in the middle,
    ``risk.simulation.mode.${option.id}.label``, and the ids are the ``{id: 'calm', …}``
    rows of ``simulationModes.ts:50-54``. All of them read "not verified" while rendered.

    Resolving a specifier is a public helper, ``resolve_import(spec, importer, src_dir)``,
    because R9 walks the same graph: relative and ``$lib`` paths, an omitted ``.ts``,
    ``.js``, ``.svelte``, ``.svelte.ts`` or ``/index.ts``, and ``'./draft.svelte'`` naming
    the runes module ``draft.svelte.ts``. A package resolves to nothing.

    The healthy half is the hop and the width. A module the building file imports was
    chosen by that file; one it does not import, or one two hops away, was not, and
    proves nothing. A wide family (``ns.${x}``) reads no import at all, or every word of
    every dependency would absolve its namespace again. And an imported word is evidence
    only under a family: on its own it proves no key.
    """

    # The importer every specifier below is resolved from, and the files around it.
    IMPORTER = "lib/components/risk/CorrelationHeatmap.svelte"
    RESOLVE_TREE = {
        IMPORTER: "",
        "lib/components/risk/correlationHelpers.ts": "",
        "lib/components/risk/legacyBands.js": "",
        "lib/components/risk/CorrelationPairsList.svelte": "",
        "lib/components/risk/levels/draft.svelte.ts": "",
        "lib/components/risk/bands/index.ts": "",
        "lib/components/charts/echartsAnimationConfig.ts": "",
        "lib/components/ui/select/index.ts": "",
        "lib/utils/core/resizeWatcher.ts": "",
    }

    # correlationHelpers.ts:59 and :79, reduced. Its own import is the second hop below.
    HELPERS = """
import {bandThreshold} from './bandThresholds';

export type CorrelationBand = 'high' | 'moderate' | 'low' | 'inverse';

export function correlationBand(value: number | null | undefined): CorrelationBand | null {
    return value === null || value === undefined ? null : bandThreshold(value);
}
"""

    # Imported by the helpers, not by the heatmap: two hops from the family.
    THRESHOLDS = """
export function bandThreshold(value: number): string {
    return value >= 0.99 ? 'perfect' : 'high';
}
"""

    # Beside the heatmap, imported by nobody.
    PALETTE = """
export const BAND_COLORS = {extreme: '#7f1d1d', high: '#b91c1c'};
"""

    # CorrelationHeatmap.svelte:39-71 and :485-488, reduced.
    HEATMAP = """
<script lang="ts">
    import {onMount, tick} from 'svelte';
    import {_ as t} from '$lib/i18n';
    import {
        correlationBand,
        NEAR_IDENTICAL,
    } from './correlationHelpers';

    function reading(value: number): string {
        const band = correlationBand(value);
        return band
            ? `<div style="font-weight:600">ρ = ${value.toFixed(3)} · ${$t(`risk.assetSet.band.${band}`)}${value >= NEAR_IDENTICAL ? ` · ${$t('risk.assetSet.nearIdentical')}` : ''}</div>`
            : '';
    }
</script>
"""

    # simulationProvenance.ts:40 and :60-65, reduced.
    PROVENANCE = """
import type {RiskAnalyticResult} from '$lib/stores/risk/riskStore.svelte';

export type SimulationEffect = 'costs' | 'cashFlows' | 'inflation' | 'rebalancing';

const EFFECT_FIELDS: ReadonlyArray<readonly [SimulationEffect, string]> = [
    ['costs', 'costs_included'],
    ['cashFlows', 'cash_flows_included'],
    ['inflation', 'inflation_included'],
    ['rebalancing', 'rebalanced'],
];
"""

    # SimulationProvenance.svelte:6, :22 and :45-47: the module is imported for its types only.
    PROVENANCE_PANEL = """
<script lang="ts">
    import {_ as t} from '$lib/i18n';

    import type {ProvenanceEntry, SimulationProvenance} from './simulationProvenance';

    const NS = 'risk.levels.l4.provenance';

    function effectList(effects: readonly string[]): string {
        return effects.map((effect) => $t(`${NS}.effects.${effect}`)).join(', ');
    }
</script>
"""

    # simulationModes.ts:50-54
    MODES = """
import {schemas} from '$lib/api';

export const SIMULATION_MODES: readonly SimulationModeSpec[] = [
    {id: 'block_bootstrap', process: 'block_bootstrap', regime: 'none', badge: 'recommended'},
    {id: 'calm', process: 'block_bootstrap', regime: 'calm', badge: null},
    {id: 'prolonged_crisis', process: 'block_bootstrap', regime: 'prolonged_crisis', badge: null},
    {id: 'shock_recovery', process: 'block_bootstrap', regime: 'shock_recovery', badge: null},
    {id: 'gbm', process: 'gbm', regime: 'none', badge: 'advanced'},
];
"""

    # L4Simulation.svelte:14-17 and :151-170, reduced: one runtime segment, then a literal tail.
    L4 = """
<script lang="ts">
    import {_ as t} from '$lib/i18n';
    import SimulationProvenance from '../SimulationProvenance.svelte';
    import {DEFAULT_SIMULATION_MODE, SIMULATION_MODES, type SimulationMode} from './simulationModes';
</script>

<fieldset data-testid="risk-simulation-modes">
    <legend>{$t('risk.simulation.mode.label')}</legend>
    {#each SIMULATION_MODES as option (option.id)}
        <span>{$t(`risk.simulation.mode.${option.id}.label`)}</span>
        <span data-testid="risk-simulation-mode-hypothesis">{$t(`risk.simulation.mode.${option.id}.hypothesis`)}</span>
    {/each}
</fieldset>
"""

    RISK = {
        "lib/components/risk/correlationHelpers.ts": HELPERS,
        "lib/components/risk/bandThresholds.ts": THRESHOLDS,
        "lib/components/risk/correlationPalette.ts": PALETTE,
        "lib/components/risk/CorrelationHeatmap.svelte": HEATMAP,
        "lib/components/risk/levels/simulationProvenance.ts": PROVENANCE,
        "lib/components/risk/levels/SimulationProvenance.svelte": PROVENANCE_PANEL,
        "lib/components/risk/levels/l4/simulationModes.ts": MODES,
        "lib/components/risk/levels/l4/L4Simulation.svelte": L4,
    }

    # A narrow family in a module of its own, with the import under test on top.
    LABELS = """
STATEMENT

export const bandLabel = (band: string) => $t(`risk.legend.band.${band}`);
"""

    @pytest.fixture
    def risk_usage(self, tmp_path):
        return collect_from_source(_tree(tmp_path / "src", self.RISK))

    @pytest.mark.parametrize(
        ("spec", "expected"),
        [
            ("./correlationHelpers", "lib/components/risk/correlationHelpers.ts"),
            ("./legacyBands", "lib/components/risk/legacyBands.js"),
            ("./CorrelationPairsList.svelte", "lib/components/risk/CorrelationPairsList.svelte"),
            ("./CorrelationPairsList", "lib/components/risk/CorrelationPairsList.svelte"),
            ("./levels/draft.svelte", "lib/components/risk/levels/draft.svelte.ts"),
            ("./levels/draft", "lib/components/risk/levels/draft.svelte.ts"),
            ("./bands", "lib/components/risk/bands/index.ts"),
            ("../charts/echartsAnimationConfig", "lib/components/charts/echartsAnimationConfig.ts"),
            ("$lib/utils/core/resizeWatcher", "lib/utils/core/resizeWatcher.ts"),
            ("$lib/components/ui/select", "lib/components/ui/select/index.ts"),
        ],
    )
    def test_a_specifier_resolves_to_its_file(self, tmp_path, spec, expected):
        src = _tree(tmp_path / "src", self.RESOLVE_TREE)
        # The path as the walk yields it, `..` folded away, so R9 can compare the two.
        assert U.resolve_import(spec, src / self.IMPORTER, src) == src / expected

    @pytest.mark.parametrize("spec", ["svelte", "svelte/store", "lucide-svelte", "@sveltejs/kit", "$app/navigation", "./missing", "./levels", "$lib/nowhere/at/all"])
    def test_a_package_a_directory_or_a_missing_file_resolves_to_nothing(self, tmp_path, spec):
        # `./levels` is a directory with no `index.ts`: a folder is not a module.
        src = _tree(tmp_path / "src", self.RESOLVE_TREE)
        assert U.resolve_import(spec, src / self.IMPORTER, src) is None

    @pytest.mark.parametrize(
        "key",
        [
            "risk.assetSet.band.moderate",  # a union member, correlationHelpers.ts:59
            "risk.assetSet.band.inverse",
            "risk.levels.l4.provenance.effects.cashFlows",  # through a type-only import
            "risk.levels.l4.provenance.effects.rebalancing",
            "risk.simulation.mode.calm.label",  # a middle interpolation, then a literal tail
            "risk.simulation.mode.gbm.hypothesis",
        ],
    )
    def test_a_member_an_imported_module_spells_is_used(self, risk_usage, key):
        assert classify(key, risk_usage, set()) == USED

    def test_a_module_the_file_does_not_import_is_no_witness(self, risk_usage):
        # Barrier: the heatmap's own import does witness.
        assert classify("risk.assetSet.band.moderate", risk_usage, set()) == USED
        # `extreme` is written beside it, in a module nobody imports...
        assert classify("risk.assetSet.band.extreme", risk_usage, set()) == UNVERIFIED
        # ...and `perfect` two hops away, in a module only the helpers import.
        assert classify("risk.assetSet.band.perfect", risk_usage, set()) == UNVERIFIED

    def test_a_middle_slot_nobody_names_stays_unverified(self, risk_usage):
        assert classify("risk.simulation.mode.calm.label", risk_usage, set()) == USED
        assert classify("risk.simulation.mode.turbulent.label", risk_usage, set()) == UNVERIFIED
        # The literal tail is part of the evidence: no template writes `.tooltip`.
        assert classify("risk.simulation.mode.calm.tooltip", risk_usage, set()) == UNVERIFIED

    def test_an_imported_word_outside_every_family_proves_nothing(self, risk_usage):
        assert classify("risk.assetSet.band.moderate", risk_usage, set()) == USED
        assert classify("risk.assetSet.moderate", risk_usage, set()) == DEAD
        assert classify("risk.levels.l4.cashFlows", risk_usage, set()) == DEAD

    @pytest.mark.parametrize(
        ("statement", "module"),
        [
            ("import {BANDS} from './bands';", "lib/components/risk/bands.ts"),
            ("import type {Band} from './bands';", "lib/components/risk/bands.ts"),
            ("import {\n    BANDS,\n    bandOf,\n} from './bands';", "lib/components/risk/bands.ts"),
            ("import * as bands from './bands';", "lib/components/risk/bands.ts"),
            ("import BandList from './BandList.svelte';", "lib/components/risk/BandList.svelte"),
            ("export const loadBandList = () => import('./BandList.svelte');", "lib/components/risk/BandList.svelte"),
            ("export {BANDS} from './bands';", "lib/components/risk/bands.ts"),
            ("export * from './bands';", "lib/components/risk/bands.ts"),
            ("import {BANDS} from '$lib/risk/bands';", "lib/risk/bands.ts"),
            ("import {BANDS} from '../../risk/bands';", "lib/risk/bands.ts"),
        ],
        ids=["named", "type-only", "multi-line", "namespace", "default", "dynamic", "re-export", "re-export-all", "lib-alias", "parent"],
    )
    def test_every_import_form_is_one_hop(self, tmp_path, statement, module):
        words = "<script lang=\"ts\">\n    const BANDS = ['calm', 'storm'] as const;\n</script>\n" if module.endswith(".svelte") else "export const BANDS = ['calm', 'storm'] as const;\n"
        src = _tree(tmp_path / "src", {"lib/components/risk/bandLabels.ts": self.LABELS.replace("STATEMENT", statement), module: words})
        assert classify("risk.legend.band.storm", collect_from_source(src), set()) == USED

    def test_an_object_key_is_a_word_only_when_it_holds_a_literal(self, tmp_path):
        tones = "const GALE_TONE = 'text-orange-600';\nexport const BAND_TONES = {storm: 'text-red-600', gale: GALE_TONE};\n"
        src = _tree(tmp_path / "src", {"lib/components/risk/bandTones.ts": tones, "lib/components/risk/bandLabels.ts": self.LABELS.replace("STATEMENT", "import {BAND_TONES} from './bandTones';")})
        usage = collect_from_source(src)
        assert classify("risk.legend.band.storm", usage, set()) == USED
        # A key holding a name is not a word the module writes down.
        assert classify("risk.legend.band.gale", usage, set()) == UNVERIFIED

    def test_a_camel_case_continuation_reads_its_import(self, tmp_path):
        src = _tree(
            tmp_path / "src",
            {
                "lib/scheduler/days.ts": "export const DAY_KEYS = ['Mon', 'Tue', 'Wed'] as const;\n",
                "lib/scheduler/historyLabel.ts": "import {DAY_KEYS} from './days';\n\nexport const historyLabel = (day: string) => $t(`scheduler.historyDays${day}`);\n",
            },
        )
        usage = collect_from_source(src)
        # One dot only, and still narrow: `historyDays` continues a name, it opens no namespace.
        assert classify("scheduler.historyDaysTue", usage, set()) == USED
        assert classify("scheduler.historyDaysSun", usage, set()) == UNVERIFIED

    def test_a_wide_family_reads_no_import(self, tmp_path):
        labels = self.LABELS.replace("STATEMENT", "import {BANDS} from './bands';") + "export const legendLabel = (band: string) => $t(`legend.${band}`);\n"
        src = _tree(tmp_path / "src", {"lib/components/risk/bands.ts": "export const BANDS = ['calm', 'storm'] as const;\n", "lib/components/risk/bandLabels.ts": labels})
        usage = collect_from_source(src)
        # Barrier: the same import witnesses the narrow family built beside it.
        assert classify("risk.legend.band.storm", usage, set()) == USED
        # Under `legend.` it would be the false "used" of `ns.assets` (R5) again.
        assert classify("legend.storm", usage, set()) == UNVERIFIED


class TestUnreferencedSources:
    """R9 — a source no route reaches renders nothing, so it proves nothing either.

    The audit read every file the walk found, so a key read only by a component nobody
    imports counted as used. ``planner/shared/AgeLabel.svelte`` reads five
    ``tools.pacAllocator.planner.age.*`` keys on the release tip and no file imports it,
    as none imported ``planner/result/WeightBars.svelte`` before it was removed with its
    keys (``08b885d43``). Reachability starts from SvelteKit's own entries (``+page``,
    ``+layout``, ``+error``, ``+server``, the hooks, the service worker) and follows static
    and dynamic imports: the planner itself is loaded only by
    ``import('./pac-allocator/planner/PacPlannerTool.svelte')`` at
    ``features/tools/registry.ts:244``.

    The report is informational; ``collect_from_source(…, skip=…)`` is what lets the audit
    leave those files out, and without ``skip`` the scan reads everything, as before.

    The healthy half: whatever an entry reaches, through any import form, is reachable;
    a declaration file is never reported, and neither is a test, which is no entry and
    reaches nothing.
    """

    # features/tools/registry.ts:240-246
    REGISTRY = """
const compiledRendererRegistrations: readonly CompiledToolRendererRegistration[] = [
    defineToolRenderer('pac_allocator', '1.0.0', {
        componentKey: 'pac-allocator',
        uiVersion: '1.0.0',
        load: () => import('./pac-allocator/planner/PacPlannerTool.svelte'),
    }),
];
"""

    PLANNER_TOOL = """
<script lang="ts">
    import {SimpleSelect} from '$lib/components/ui/select';
    import {daysBetween} from './draft.svelte';
    import CopyNotice from './shared/CopyNotice.svelte';
</script>

<CopyNotice />
"""

    # planner/shared/AgeLabel.svelte at d07412899, reduced.
    AGE_LABEL = """
<script lang="ts">
    import {t, locale} from '$lib/i18n';
    import {daysBetween} from '../draft.svelte';
    import {formatPlannerDate} from '../format';

    let {date, asOf, manual = false}: Props = $props();
    const days = $derived(date ? daysBetween(date, asOf) : null);
</script>

{#if manual}
    {$t('tools.pacAllocator.planner.age.manual', {default: 'Entered by hand'})}
{:else}
    {$t('tools.pacAllocator.planner.age.daysBefore', {values: {count: days ?? 0, date: formatPlannerDate(asOf, $locale)}})}
{/if}
"""

    # The planner, reduced to what reaches it: a route renders the tool host, whose registry
    # loads the planner lazily; the planner pulls in a barrel, its runes module and a shared
    # component. AgeLabel.svelte sits in the same folder and nobody imports it; format.ts is
    # imported by AgeLabel alone; the test beside AgeLabel is no entry.
    PLANNER = {
        "app.d.ts": "declare global {\n    namespace App {}\n}\n\nexport {};\n",
        "hooks.server.ts": "import type {Handle} from '@sveltejs/kit';\nimport {SESSION_COOKIE} from '$lib/server/session';\n\nexport const handle: Handle = async ({event, resolve}) => resolve(event);\n",
        "lib/server/session.ts": "export const SESSION_COOKIE = 'session';\n",
        "routes/+layout.svelte": "<script lang=\"ts\">\n    import '../app.css';\n    import {locale} from '$lib/i18n';\n    let {children} = $props();\n</script>\n\n{@render children()}\n",
        "lib/i18n/index.ts": "export {_, t, locale} from 'svelte-i18n';\n",
        "routes/(app)/tools/[tool_code]/+page.svelte": "<script lang=\"ts\">\n    import ToolHost from '$lib/features/tools/ToolHost.svelte';\n</script>\n\n<ToolHost />\n",
        "routes/(app)/tools/[tool_code]/+page.ts": "import {loadToolCatalog} from '$lib/features/tools/client';\n\nexport const load = () => loadToolCatalog();\n",
        "lib/features/tools/client.ts": "export const loadToolCatalog = () => fetch('/api/v1/tools');\n",
        "lib/features/tools/ToolHost.svelte": "<script lang=\"ts\">\n    import {resolveToolRenderer} from './registry';\n</script>\n",
        "lib/features/tools/registry.ts": REGISTRY,
        "lib/features/tools/pac-allocator/planner/PacPlannerTool.svelte": PLANNER_TOOL,
        "lib/features/tools/pac-allocator/planner/draft.svelte.ts": "export function daysBetween(from: string, to: string): number {\n    return 0;\n}\n",
        "lib/features/tools/pac-allocator/planner/shared/CopyNotice.svelte": "<script lang=\"ts\">\n    import {t} from '$lib/i18n';\n</script>\n\n<p>{$t('tools.pacAllocator.planner.copy.notice')}</p>\n",
        "lib/components/ui/select/index.ts": "export {default as SimpleSelect} from './SimpleSelect.svelte';\n",
        "lib/components/ui/select/SimpleSelect.svelte": "<select></select>\n",
        "lib/features/tools/pac-allocator/planner/shared/AgeLabel.svelte": AGE_LABEL,
        "lib/features/tools/pac-allocator/planner/format.ts": "export function formatPlannerDate(date: string, locale: string): string {\n    return date;\n}\n",
        "lib/features/tools/pac-allocator/planner/shared/AgeLabel.test.ts": "import AgeLabel from './AgeLabel.svelte';\n\nrender(AgeLabel, {props: {date: null, asOf: '2026-10-07'}});\n",
    }

    # Two components, one read and one skipped; both spell the shared key.
    LIVE = """
<script lang="ts">
    const shared = $t('ns.shared.key');
    const live = (code: string) => $t(`ns.live.${code}`);
</script>
"""

    DEAD = """
<script lang="ts">
    const shared = $t('ns.shared.key');
    const only = $t('ns.dead.only');
    const family = (code: string) => $t(`ns.dead.family.${code}`);
    const nested = (section: string) => $t(`ns.dead.${section}.title`);
</script>
"""

    def test_a_component_nobody_imports_is_reported(self, tmp_path):
        src = _tree(tmp_path / "src", self.PLANNER)
        found = set(U.unreferenced_sources(src))
        # The paths the walk yields, so that they can be handed back to it as `skip=`.
        assert found <= set(U.iter_source_files(src))
        # Equality: the tree is this test's own. Everything else is reached, the planner
        # included, through a dynamic import, a barrel and a runes module.
        assert _relative(src, found) == {
            "lib/features/tools/pac-allocator/planner/shared/AgeLabel.svelte",
            "lib/features/tools/pac-allocator/planner/format.ts",
        }

    @pytest.mark.parametrize(
        "entry",
        [
            "routes/+page.svelte",
            "routes/(app)/assets/[id]/+page.ts",
            "routes/(app)/files/+page.server.ts",
            "routes/(app)/+layout.svelte",
            "routes/+layout.ts",
            "routes/(app)/+layout.server.ts",
            "routes/+error.svelte",
            "routes/api/health/+server.ts",
            "hooks.server.ts",
            "hooks.client.ts",
            "hooks.ts",
            "service-worker.ts",
        ],
    )
    def test_every_sveltekit_entry_is_a_root(self, tmp_path, entry):
        statement = "import {reached} from '$lib/reached';"
        body = f'<script lang="ts">\n    {statement}\n</script>\n\n<p>{{reached}}</p>\n' if entry.endswith(".svelte") else f"{statement}\n\nexport const value = reached;\n"
        src = _tree(tmp_path / "src", {entry: body, "lib/reached.ts": "export const reached = 1;\n", "lib/orphan.ts": "export const orphan = 1;\n"})
        # The entry is a root and what it imports is reached; the barrier is the one file nobody imports.
        assert _relative(src, U.unreferenced_sources(src)) == {"lib/orphan.ts"}

    def test_a_name_that_resembles_an_entry_is_no_root(self, tmp_path):
        src = _tree(
            tmp_path / "src",
            {
                "routes/(app)/assets/+page.svelte": "<h1>Assets</h1>\n",
                "routes/(app)/assets/page.svelte": "<h1>Assets, before the route moved</h1>\n",
                "routes/(app)/assets/columns.ts": "export const COLUMNS = [];\n",
                "lib/server/layout.ts": "export const LAYOUT = 'wide';\n",
                "lib/stores/hooks.svelte.ts": "export const hooks = $state([]);\n",
            },
        )
        # A helper beside a route is not a route: nobody imports it, so nothing renders it.
        assert _relative(src, U.unreferenced_sources(src)) == {
            "routes/(app)/assets/page.svelte",
            "routes/(app)/assets/columns.ts",
            "lib/server/layout.ts",
            "lib/stores/hooks.svelte.ts",
        }

    @pytest.mark.parametrize(
        ("statement", "target"),
        [
            ("export const loadPlanner = () => import('./tools/PacPlannerTool.svelte');", "lib/tools/PacPlannerTool.svelte"),
            ("export {default as SimpleSelect} from './select/SimpleSelect.svelte';", "lib/select/SimpleSelect.svelte"),
            ("export * from './format';", "lib/format.ts"),
            ("import {daysBetween} from './draft.svelte';", "lib/draft.svelte.ts"),
            ("import {SimpleSelect} from '$lib/select';", "lib/select/index.ts"),
            ("import {legacy} from './legacy';", "lib/legacy.js"),
        ],
        ids=["dynamic", "re-export", "re-export-all", "runes-module", "index", "javascript"],
    )
    def test_every_import_form_reaches(self, tmp_path, statement, target):
        src = _tree(
            tmp_path / "src",
            {
                "routes/+page.svelte": "<script lang=\"ts\">\n    import {hub} from '$lib/hub';\n</script>\n",
                "lib/hub.ts": f"{statement}\n\nexport const hub = 1;\n",
                target: "\n",
                "lib/orphan.ts": "export const orphan = 1;\n",
            },
        )
        assert _relative(src, U.unreferenced_sources(src)) == {"lib/orphan.ts"}

    def test_what_only_unreferenced_files_import_is_unreferenced(self, tmp_path):
        src = _tree(
            tmp_path / "src",
            {
                "routes/+page.svelte": "<script lang=\"ts\">\n    import {ring} from '$lib/ring/a';\n</script>\n",
                # A cycle an entry reaches: both files reached, and the walk ends.
                "lib/ring/a.ts": "import {b} from './b';\n\nexport const ring = () => b;\n",
                "lib/ring/b.ts": "import {ring} from './a';\n\nexport const b = 1;\n",
                # A chain nobody reaches: imported, but only by the unreferenced.
                "lib/orphan/Panel.svelte": "<script lang=\"ts\">\n    import {chart} from './chart';\n</script>\n",
                "lib/orphan/chart.ts": "import {palette} from './palette';\n\nexport const chart = palette;\n",
                "lib/orphan/palette.ts": "export const palette = ['#000000'];\n",
                # A cycle nobody reaches: each file has an importer, and neither is reached.
                "lib/orphan/left.ts": "import {right} from './right';\n\nexport const left = right;\n",
                "lib/orphan/right.ts": "import {left} from './left';\n\nexport const right = left;\n",
            },
        )
        assert _relative(src, U.unreferenced_sources(src)) == {
            "lib/orphan/Panel.svelte",
            "lib/orphan/chart.ts",
            "lib/orphan/palette.ts",
            "lib/orphan/left.ts",
            "lib/orphan/right.ts",
        }

    def test_declarations_and_tests_are_never_reported_and_reach_nothing(self, tmp_path):
        src = _tree(
            tmp_path / "src",
            {
                "routes/+page.svelte": "<h1>Home</h1>\n",
                "app.d.ts": "declare global {\n    namespace App {}\n}\n\nexport {};\n",
                "lib/types/svg.d.ts": "declare module '*.svg?raw' {\n    const content: string;\n    export default content;\n}\n",
                "lib/components/charts/SparkBars.svelte": '<div data-testid="spark-bars"></div>\n',
                "lib/components/charts/SparkBars.test.ts": "import SparkBars from './SparkBars.svelte';\n",
                "__tests__/component.ts": "import SparkBars from '$lib/components/charts/SparkBars.svelte';\n",
                "lib/stores/__mocks__/settings.ts": "export const settings = {};\n",
            },
        )
        # Equality: no declaration and no test is reported, and the component that only
        # tests import is, because a test is no entry and reaches nothing.
        assert _relative(src, U.unreferenced_sources(src)) == {"lib/components/charts/SparkBars.svelte"}

    def test_a_skipped_file_proves_nothing(self, tmp_path):
        src = _tree(tmp_path / "src", {"lib/Live.svelte": self.LIVE, "lib/Dead.svelte": self.DEAD})
        full = U.collect_from_source(src)
        usage = U.collect_from_source(src, skip=frozenset({src / "lib/Dead.svelte"}))
        # Control: without `skip` the scan reads every file, as it always did.
        assert classify("ns.dead.only", full, set()) == USED
        assert classify("ns.dead.family.anything", full, set()) == UNVERIFIED
        assert classify("ns.dead.section.title", full, set()) == UNVERIFIED
        # Skipped: no whole key, no family, no unverified prefix.
        assert classify("ns.dead.only", usage, set()) == DEAD
        assert classify("ns.dead.family.anything", usage, set()) == DEAD
        assert classify("ns.dead.section.title", usage, set()) == DEAD
        # The same literal in a file that is read still counts, and so does its family.
        assert classify("ns.shared.key", usage, set()) == USED
        assert classify("ns.live.anything", usage, set()) == UNVERIFIED

    def test_the_audit_can_leave_unreferenced_sources_out(self, tmp_path):
        src = _tree(tmp_path / "src", self.PLANNER)
        usage = U.collect_from_source(src, skip=frozenset(U.unreferenced_sources(src)))
        # Barrier: the planner's live component is read.
        assert classify("tools.pacAllocator.planner.copy.notice", usage, set()) == USED
        # AgeLabel was the only reader of its keys: left out, they are dead.
        assert classify("tools.pacAllocator.planner.age.manual", usage, set()) == DEAD
        assert classify("tools.pacAllocator.planner.age.daysBefore", usage, set()) == DEAD
        # Read in full they pass for used: the blindness this rule removes.
        assert classify("tools.pacAllocator.planner.age.manual", U.collect_from_source(src), set()) == USED


class TestGeneratedClients:
    """R10 — a generated client is no product source: the verdict must not depend on it.

    ``lib/api/generated.ts`` is git-ignored and exists only after ``./dev.py api sync``;
    ``generated-tools.ts`` and ``tool-contract-map.generated.ts`` sit beside it. The walk
    read them like hand-written code, so a key quoted by a generated schema counted as a
    reference on a synced tree and as nothing on a fresh clone: one commit, two verdicts.
    The backend the client is generated from is read directly anyway (R2, R4), so the
    client adds nothing true and something unstable. Product files also import it
    directly (``charts/signals/backendTypes.ts:3``, ``providerProbeState.svelte.ts:2``), so
    it must not come back one import away as a witness for R8 either.

    The healthy half: only generated clients. A generator, a helper whose name begins with
    ``generated``, a ``regenerate`` script and a component called ``Generated`` are
    hand-written, and stay sources.
    """

    # What `api sync` writes, reduced: schema defaults that happen to be keys.
    GENERATED = """
const AdditionalExportSuggestion = z.object({
    dataset_id: z.string(),
    reason_i18n_key: z.string().default('ns.export.reason.generatedOnly'),
    fallback_i18n_key: z.string().default('ns.export.reason.deeperTechnical'),
});
"""

    CONTRACT_MAP = """
export const toolContractMap = {
    pac_allocator: {'1.0.0': {toolCode: 'pac_allocator', titleKey: 'ns.tools.contractTitle'}},
};
"""

    @pytest.mark.parametrize(
        "path",
        ["lib/api/generated.ts", "lib/api/generated-tools.ts", "lib/api/tool-contract-map.generated.ts", "lib/api/schemas.generated.js"],
    )
    def test_a_generated_client_is_recognised(self, path):
        assert U.is_generated_source(Path(path)) is True

    @pytest.mark.parametrize(
        "path",
        ["lib/api/generator.ts", "lib/utils/generatedHelpers.ts", "scripts/regenerate.ts", "lib/components/Generated.svelte"],
    )
    def test_a_name_that_merely_contains_generated_is_not_one(self, path):
        assert U.is_generated_source(Path(path)) is False

    def test_the_walk_skips_generated_clients(self, tmp_path):
        src = _tree(
            tmp_path / "src",
            {
                "lib/api/index.ts": "",
                "lib/api/zodios-client.ts": "",
                "lib/api/generated.ts": "",
                "lib/api/generated-tools.ts": "",
                "lib/api/tool-contract-map.generated.ts": "",
                "lib/api/schemas.generated.js": "",
                "lib/api/generator.ts": "",
                "lib/utils/generatedHelpers.ts": "",
                "lib/tools/regenerate.ts": "",
                "lib/components/Generated.svelte": "",
            },
        )
        # Equality: what is left out matters as much as what is kept.
        assert _relative(src, U.iter_source_files(src)) == {
            "lib/api/index.ts",
            "lib/api/zodios-client.ts",
            "lib/api/generator.ts",
            "lib/utils/generatedHelpers.ts",
            "lib/tools/regenerate.ts",
            "lib/components/Generated.svelte",
        }

    def test_a_key_only_a_generated_client_spells_is_dead(self, tmp_path):
        src = _tree(
            tmp_path / "src",
            {
                "lib/api/generated.ts": self.GENERATED,
                "lib/api/tool-contract-map.generated.ts": self.CONTRACT_MAP,
                "lib/api/index.ts": "export {schemas} from './generated';\n",
                "lib/components/SuggestionRow.svelte": "<span>{$t('ns.export.reason.deeperTechnical')}</span>\n",
            },
        )
        usage = collect_from_source(src)
        # Barrier: the hand-written component is read, and its key is proven whoever else spells it.
        assert classify("ns.export.reason.deeperTechnical", usage, set()) == USED
        assert classify("ns.export.reason.generatedOnly", usage, set()) == DEAD
        assert classify("ns.tools.contractTitle", usage, set()) == DEAD

    def test_a_generated_client_is_no_witness_one_import_away(self, tmp_path):
        label = "import {schemas} from '$lib/api/generated';\nimport {SHOWN_REGIMES} from './regimes';\n\nexport const regimeLabel = (regime: string) => $t(`risk.simulation.regime.${regime}`);\n"
        src = _tree(
            tmp_path / "src",
            {
                "lib/api/generated.ts": "export const schemas = {RiskSimulationRegime: z.enum(['none', 'calm', 'prolonged_crisis'])};\n",
                "lib/risk/regimes.ts": "export const SHOWN_REGIMES = ['calm'] as const;\n",
                "lib/risk/regimeLabel.ts": label,
            },
        )
        usage = collect_from_source(src)
        # Barrier: the hand-written module one hop away does witness (R8).
        assert classify("risk.simulation.regime.calm", usage, set()) == USED
        # The client one hop away does not: on a fresh clone there is nothing to read.
        assert classify("risk.simulation.regime.prolonged_crisis", usage, set()) == UNVERIFIED


class TestCodesInOtherSpellings:
    """R11 — a code is a code in any case, and it may begin with a digit.

    Two spellings fell through the producer vocabulary. ``AiExportAdditionalExportPeriod``
    (``schemas/ai_export_runtime.py:98-100``) emits ``"3m"``, ``"6m"`` and ``"1y"``, which
    ``promptRenderer.ts:299`` reads as ``aiExport.additionalData.period.${…}``; an
    identifier literal had to begin with a letter, so no period key could ever be proven.
    And ``LotCustodyModal.svelte:116`` lowercases what the backend spells in capitals:
    ``brokers.lots.modal.state.${state.toLowerCase()}`` renders ``in_transit`` and
    ``degraded`` for ``"IN_TRANSIT"`` and ``"DEGRADED"`` (``schemas/portfolio.py:716,721``),
    while the match was case-sensitive.

    The healthy half: a quoted sentence does not become a code because it begins with a
    digit, and a rest whose letters spell no code, in any case, stays unverified.
    """

    # schemas/ai_export_runtime.py:97-101, and prose that a code must not be confused with.
    RUNTIME_PY = """
class AiExportAdditionalExportPeriod(StrEnum):
    THREE_MONTHS = "3m"
    SIX_MONTHS = "6m"
    ONE_YEAR = "1y"
    MAXIMUM_AVAILABLE = "maximum_available"


PERIOD_HINT = "3 months of daily closes"
"""

    # schemas/portfolio.py:716 and :721
    PORTFOLIO_PY = """
LotCustodyType = Literal["BROKER", "IN_TRANSIT"]
LotAnalysisStatus = Literal["COMPLETE", "DEGRADED", "FAILED"]
"""

    # promptRenderer.ts:299-301, reduced.
    RENDERER = """
export function suggestionLines(suggestion: AdditionalExportSuggestion, translate: (key: string) => string): string[] {
    const period = translate(`aiExport.additionalData.period.${suggestion.recommended_period}`);
    const necessity = translate(`aiExport.additionalData.necessity.${suggestion.necessity}`);
    return [period, necessity];
}
"""

    # LotCustodyModal.svelte:115-119
    CUSTODY = """
<script lang="ts">
    function stateLabel(state: string): string {
        const key = `brokers.lots.modal.state.${state.toLowerCase()}`;
        const translated = $_(key);
        return translated === key ? state.replaceAll('_', ' ') : translated;
    }
</script>
"""

    @pytest.fixture
    def period_usage(self, tmp_path):
        usage = collect_from_source(_tree(tmp_path / "src", {"lib/features/ai-export/templates/promptRenderer.ts": self.RENDERER}))
        usage.vocabulary = harvest_vocabulary(_tree(tmp_path / "backend", {"schemas/ai_export_runtime.py": self.RUNTIME_PY}))
        return usage

    @pytest.fixture
    def custody_usage(self, tmp_path):
        usage = collect_from_source(_tree(tmp_path / "src", {"lib/components/brokers/lots/LotCustodyModal.svelte": self.CUSTODY}))
        usage.vocabulary = harvest_vocabulary(_tree(tmp_path / "backend", {"schemas/portfolio.py": self.PORTFOLIO_PY}))
        return usage

    def test_a_code_may_begin_with_a_digit(self, tmp_path):
        vocab = harvest_vocabulary(_tree(tmp_path / "backend", {"schemas/ai_export_runtime.py": self.RUNTIME_PY}))
        assert {"3m", "6m", "1y", "maximum_available"} <= vocab

    def test_a_sentence_is_still_no_code(self, tmp_path):
        vocab = harvest_vocabulary(_tree(tmp_path / "backend", {"schemas/ai_export_runtime.py": self.RUNTIME_PY}))
        # Barrier: the codes beside it are harvested.
        assert "1y" in vocab
        assert "3 months of daily closes" not in vocab
        assert "3" not in vocab

    @pytest.mark.parametrize("key", ["aiExport.additionalData.period.3m", "aiExport.additionalData.period.6m", "aiExport.additionalData.period.1y"])
    def test_a_period_the_backend_emits_proves_its_key(self, period_usage, key):
        assert classify(key, period_usage, set()) == USED

    def test_a_period_nobody_emits_stays_unverified(self, period_usage):
        assert classify("aiExport.additionalData.period.3m", period_usage, set()) == USED
        assert classify("aiExport.additionalData.period.5y", period_usage, set()) == UNVERIFIED
        assert classify("aiExport.additionalData.title", period_usage, set()) == DEAD

    @pytest.mark.parametrize("key", ["brokers.lots.modal.state.in_transit", "brokers.lots.modal.state.degraded"])
    def test_a_lowercased_member_matches_its_capitals(self, custody_usage, key):
        assert classify(key, custody_usage, set()) == USED

    def test_a_rest_no_code_spells_in_any_case_stays_unverified(self, custody_usage):
        assert classify("brokers.lots.modal.state.in_transit", custody_usage, set()) == USED
        assert classify("brokers.lots.modal.state.lost", custody_usage, set()) == UNVERIFIED
        assert classify("brokers.lots.modal.title", custody_usage, set()) == DEAD


class TestSeveralRuntimeSegments:
    """R12 — a template with several runtime segments still has a shape, and each slot a witness.

    A template that interpolated more than once, or before a literal tail, left only its
    literal head behind as an unverified prefix: everything under it flagged, nothing
    proven. ``ProviderAssignmentSection.svelte:130`` builds
    ``assets.providerParams.${code}.${kind}.${field.key}``, where ``kind`` is the parameter
    union ``'label' | 'description'`` and the backend spells both the provider code and
    the param key (``"borsa_italiana"`` at ``borsa_italiana.py:346``, ``"codice_fondo"`` at
    ``:438``). ``routes/(app)/assets/+page.svelte:1668`` builds
    ``assets.panels.${panel.id}Hint`` and spells ``'analysis'`` at ``:349-364``. Every slot
    was named, and every key read "not verified".

    The shape keeps what resolves (a union keeps its members) and turns each runtime
    segment into a slot of one segment; a key is used when every slot is a word of the
    building file or of its direct imports (R8), or a backend code (R11).

    The healthy half: the shape is matched whole. One slot named nowhere leaves the key
    unverified, through the unverified prefix that stays; a resolved position takes only
    its values; an extra segment is no match; and a template without a dotted literal head
    (``${a}.${b}``) has no shape at all, or any two quoted words would make a key.
    """

    # ProviderAssignmentSection.svelte:126-131 and :476, reduced.
    PARAMS = """
<script lang="ts">
    import {_ as t} from '$lib/i18n';

    function paramText(field: ParamField, kind: 'label' | 'description'): string {
        const backend = (kind === 'label' ? field.label : field.description) ?? '';
        const code = selectedProvider?.code;
        if (!code) return backend;
        const translated = $t(`assets.providerParams.${code}.${kind}.${field.key}`);
        return translated !== `assets.providerParams.${code}.${kind}.${field.key}` ? translated : backend;
    }
</script>

<span>{paramText(field, 'label') || field.key}</span>
"""

    # borsa_italiana.py:345-346 and :437-442, reduced.
    PROVIDER_PY = """
class BorsaItalianaProvider(AssetSourceProvider):
    @property
    def provider_code(self) -> str:
        return "borsa_italiana"

    def get_params_schema(self) -> list[dict]:
        return [
            {
                "key": "codice_fondo",
                "type": "string",
                "required": False,
                "label": "Fund internal code",
            },
        ]
"""

    # routes/(app)/assets/+page.svelte:349-364 and :1668, reduced. The bare
    # `assets.panels.${panel.id}` at :1666 is left out: it is R5's, not this rule's.
    PANELS = """
<script lang="ts">
    type AssetScope = 'own' | 'others' | 'analysis';

    function assetScope(a: {held_by_me?: boolean; held_by_others?: boolean}): AssetScope {
        if (a.held_by_me) return 'own';
        if (a.held_by_others) return 'others';
        return 'analysis';
    }

    let assetPanels = $derived([
        {id: 'own' as const, items: ownAssets},
        {id: 'others' as const, items: otherAssets},
        {id: 'analysis' as const, items: analysisAssets},
    ]);
</script>

{#each assetPanels as panel (panel.id)}
    <p class="text-[11px] text-gray-400 dark:text-gray-500">{$t(`assets.panels.${panel.id}Hint`)}</p>
{/each}
"""

    @pytest.fixture
    def params_usage(self, tmp_path):
        usage = collect_from_source(_tree(tmp_path / "src", {"lib/components/assets/ProviderAssignmentSection.svelte": self.PARAMS}))
        usage.vocabulary = harvest_vocabulary(_tree(tmp_path / "backend", {"services/asset_source_providers/borsa_italiana.py": self.PROVIDER_PY}))
        return usage

    @pytest.fixture
    def panels_usage(self, tmp_path):
        return collect_from_source(_tree(tmp_path / "src", {"routes/(app)/assets/+page.svelte": self.PANELS}))

    @pytest.mark.parametrize("key", ["assets.providerParams.borsa_italiana.label.codice_fondo", "assets.providerParams.borsa_italiana.description.codice_fondo"])
    def test_a_key_whose_every_slot_is_named_is_used(self, params_usage, key):
        assert classify(key, params_usage, set()) == USED

    def test_one_slot_named_nowhere_leaves_the_key_unverified(self, params_usage):
        assert classify("assets.providerParams.borsa_italiana.label.codice_fondo", params_usage, set()) == USED
        assert classify("assets.providerParams.borsa_italiana.label.isin_override", params_usage, set()) == UNVERIFIED
        assert classify("assets.providerParams.justetf.label.codice_fondo", params_usage, set()) == UNVERIFIED

    def test_a_resolved_position_takes_only_its_values(self, params_usage):
        assert classify("assets.providerParams.borsa_italiana.label.codice_fondo", params_usage, set()) == USED
        # The backend spells `required`, but `${kind}` is 'label' | 'description': no slot here.
        assert classify("assets.providerParams.borsa_italiana.required.codice_fondo", params_usage, set()) == UNVERIFIED

    def test_a_key_with_an_extra_segment_does_not_match(self, params_usage):
        assert classify("assets.providerParams.borsa_italiana.label.codice_fondo", params_usage, set()) == USED
        # Every word below is named, and neither key has the shape: one slot, one segment.
        assert classify("assets.providerParams.borsa_italiana.label.codice_fondo.label", params_usage, set()) == UNVERIFIED
        assert classify("assets.providerParams.borsa_italiana.codice_fondo.label.codice_fondo", params_usage, set()) == UNVERIFIED

    @pytest.mark.parametrize("key", ["assets.panels.analysisHint", "assets.panels.ownHint"])
    def test_a_slot_inside_a_segment_is_matched_with_its_tail(self, panels_usage, key):
        assert classify(key, panels_usage, set()) == USED

    def test_the_tail_of_the_segment_is_part_of_the_shape(self, panels_usage):
        assert classify("assets.panels.analysisHint", panels_usage, set()) == USED
        assert classify("assets.panels.archivedHint", panels_usage, set()) == UNVERIFIED
        # `analysis` is named, but `${panel.id}Hint` never renders it bare.
        assert classify("assets.panels.analysis", panels_usage, set()) == UNVERIFIED

    def test_each_slot_may_have_its_own_witness(self, tmp_path):
        source = """
<script lang="ts">
    const SECTIONS = ['assets', 'orders'] as const;
    const reasonText = (section: string, code: string) => $t(`ns.tool.${section}.reasons.${code}`);
</script>
"""
        usage = collect_from_source(_tree(tmp_path / "src", {"ReasonList.svelte": source}))
        usage.vocabulary = harvest_vocabulary(_tree(tmp_path / "backend", {"svc.py": 'CODES = ["flat_series"]\n'}))
        # One slot spelled by the file, the other by the producer.
        assert classify("ns.tool.assets.reasons.flat_series", usage, set()) == USED
        assert classify("ns.tool.assets.reasons.worker_busy", usage, set()) == UNVERIFIED
        assert classify("ns.tool.trades.reasons.flat_series", usage, set()) == UNVERIFIED

    def test_a_template_without_a_dotted_head_has_no_shape(self, tmp_path):
        source = """
<script lang="ts">
    const SCOPES = ['own', 'analysis'] as const;
    const PARTS = ['title', 'hint'] as const;
    const scoped = (scope: string, part: string) => $t(`ns.panels.${scope}.${part}`);
    const anyKey = (scope: string, part: string) => $t(`${scope}.${part}`);
</script>
"""
        usage = collect_from_source(_tree(tmp_path / "src", {"Panels.svelte": source}))
        # Barrier: under a dotted head the same two words do make a key.
        assert classify("ns.panels.analysis.title", usage, set()) == USED
        # Bare slots would turn any pair of quoted words into a key.
        assert classify("analysis.title", usage, set()) == DEAD
        assert classify("own.hint", usage, set()) == DEAD
