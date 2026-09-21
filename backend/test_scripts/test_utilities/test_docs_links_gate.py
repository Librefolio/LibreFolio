"""Tests for cross-boundary documentation link discovery (``scripts/docs_links.py``).

The gate this module serves used to declare its own blindness in a comment —
*"a dynamic `path={expr}` has no quotes and is skipped by construction"* — and
the declaration was not quite true: the expressions it skipped resolved to
static maps and constants sitting in the same file. It was skipped by choice.

Two properties are worth more than the rest, and both are asymmetries:

* **A known constant must be resolved, not deleted.** The naive repair — scan
  the map literals and strip ``${…}`` — turns ``${DOCS}/max-drawdown/`` into
  ``max-drawdown``, a plausible path that does not exist, and reports a healthy
  link as broken. A gate that stops being blind by starting to lie is worse than
  the blindness: people learn to ignore it.

* **A guess may confirm a link and never condemn one.** When an interpolation
  *cannot* be resolved, dropping it is a guess. If the guess lands on a real
  page, the link is fine; if it does not, that says something about the guess,
  not about the link — so the verdict is "unverifiable", never "broken".

PURE: every fixture is built under ``tmp_path``. No repo files are read.
"""

import pytest

from scripts.docs_links import (
    Link,
    collect_backend,
    collect_frontend,
    deduplicate,
    find_page,
    resolve,
)


@pytest.fixture
def docs_root(tmp_path):
    """A miniature mkdocs tree with one real page per shape."""
    root = tmp_path / "docs"
    for rel in (
        "financial-theory/metrics/max-drawdown/index.en.md",
        "financial-theory/metrics/value-at-risk.en.md",
        "user/tools/rebalancer/index.en.md",
    ):
        page = root / rel
        page.parent.mkdir(parents=True, exist_ok=True)
        page.write_text("# Title\n", encoding="utf-8")
    return root


class TestResolve:
    def test_a_known_constant_is_substituted_not_deleted(self):
        consts = {"DOCS": "financial-theory/metrics"}
        assert resolve("${DOCS}/max-drawdown/", consts) == (
            "financial-theory/metrics/max-drawdown",
            True,
        )

    def test_deleting_the_constant_would_have_produced_a_different_path(self, docs_root):
        # The measured trap, kept as an executable statement: the old resolver
        # returned "max-drawdown", which resolves to nothing.
        assert find_page(docs_root, "max-drawdown") is None
        resolved, _ = resolve("${DOCS}/max-drawdown/", {"DOCS": "financial-theory/metrics"})
        assert find_page(docs_root, resolved) is not None

    def test_an_unknown_interpolation_yields_a_speculative_path(self):
        # `/mkdocs/${prefix}user/...` — prefix is a language segment that is
        # empty for English, so dropping it is right *and* unproven.
        assert resolve("${prefix}user/tools/rebalancer/") == ("user/tools/rebalancer", False)

    def test_the_svelte_interpolation_dialect_is_understood_too(self):
        # Markup uses `{X}`, not `${X}`; a resolver that knows only one dialect
        # is blind on half the call sites.
        assert resolve("{DOCS}/max-drawdown/", {"DOCS": "financial-theory/metrics"}) == (
            "financial-theory/metrics/max-drawdown",
            True,
        )

    @pytest.mark.parametrize("raw", ["${lang", "", "/", "https://example.org/x", ":path"])
    def test_values_with_nothing_checkable_are_refused(self, raw):
        assert resolve(raw) is None


class TestFindPage:
    @pytest.mark.parametrize(
        "path",
        [
            "financial-theory/metrics/max-drawdown/",
            "financial-theory/metrics/max-drawdown",
            "financial-theory/metrics/value-at-risk",
            "financial-theory/metrics/max-drawdown/#an-anchor",
        ],
    )
    def test_directory_and_file_spellings_both_resolve(self, docs_root, path):
        assert find_page(docs_root, path) is not None

    def test_a_missing_page_is_reported_as_missing(self, docs_root):
        assert find_page(docs_root, "financial-theory/metrics/sortino") is None


class TestFrontendDiscovery:
    SOURCE = """
    <script lang="ts">
        const DOCS = 'financial-theory/metrics';
        const DOC_PATHS: Record<string, string> = {
            day: `${DOCS}/max-drawdown/`,
            worst: `${DOCS}/value-at-risk/`,
        };
    </script>
    <RiskMetricCard docsPath={DOC_PATHS[row.id]} />
    <DocsLink path="user/tools/rebalancer/" />
    <DocsLink path={runtimeOnly} />
    """

    @pytest.fixture
    def found(self, tmp_path):
        src = tmp_path / "src"
        src.mkdir()
        (src / "Panel.svelte").write_text(self.SOURCE, encoding="utf-8")
        return collect_frontend(src)

    def test_the_map_behind_a_dynamic_prop_is_read(self, found):
        paths = {link.path for link in found.links}
        assert "financial-theory/metrics/max-drawdown" in paths
        assert "financial-theory/metrics/value-at-risk" in paths

    def test_the_map_values_keep_their_constant_prefix(self, found):
        # The regression this guards: a stripped `${DOCS}` leaves a bare leaf.
        assert not any(link.path in {"max-drawdown", "value-at-risk"} for link in found.links)

    def test_plain_literals_still_work(self, found):
        assert "user/tools/rebalancer" in {link.path for link in found.links}

    def test_a_genuinely_dynamic_prop_is_declared_not_swallowed(self, found):
        # It used to vanish from the output, and an empty error list read as a pass.
        assert found.unverified, "an unresolvable reference must be reported"

    @pytest.mark.parametrize("name", ["Thing.test.ts", "Thing.spec.ts", "generated.ts"])
    def test_fixtures_and_generated_artefacts_are_ignored(self, tmp_path, name):
        # generated.ts is git-ignored, so reading it would make this gate's
        # output depend on whether a code generator happened to have run.
        src = tmp_path / "src"
        src.mkdir()
        (src / name).write_text("const p = 'user/ghost/page';\ndocsPath: 'user/ghost'\n")
        found = collect_frontend(src)
        assert found.links == []
        assert found.unverified == []

    def test_a_route_placeholder_is_not_reported_at_all(self, tmp_path):
        # `/mkdocs/:path` is a URL pattern, not a link. Listing it as
        # "unverifiable" would be noise in the one section meant to be read.
        src = tmp_path / "src"
        src.mkdir()
        (src / "Router.ts").write_text("const route = '/mkdocs/:path';\n")
        found = collect_frontend(src)
        assert found.links == []
        assert found.unverified == []


class TestBackendDiscovery:
    """Plugin families must be found by glob, not by a hand-written list."""

    @pytest.fixture
    def services(self, tmp_path):
        root = tmp_path / "services"
        for pkg, body in {
            "signal_plugins/adx.py": 'docs_path = "financial-theory/indicators/adx/"\n',
            "brim_providers/degiro.py": 'docs_path = "user/transactions/import/degiro/"\n',
            "tool_plugins/pac.py": 'ToolDocumentation(path="user/tools/pac-allocator/")\n',
            "fx_providers/ecb.py": 'DOCS = "/mkdocs/user/fx/providers/ecb/"\n',
            "not_a_plugin_dir/x.py": 'docs_path = "user/should/not/be/scanned/"\n',
        }.items():
            path = root / pkg
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(body, encoding="utf-8")
        return root

    @pytest.mark.parametrize(
        "expected",
        [
            "financial-theory/indicators/adx",
            "user/transactions/import/degiro",
            "user/tools/pac-allocator",
            "user/fx/providers/ecb",
        ],
    )
    def test_every_plugin_family_is_covered(self, services, expected):
        # The two directories the gate used to name by hand left signal_plugins,
        # tool_plugins and brim_providers unchecked — fifty pages between them.
        assert expected in {link.path for link in collect_backend(services).links}

    def test_unrelated_packages_are_not_scanned(self, services):
        paths = {link.path for link in collect_backend(services).links}
        assert "user/should/not/be/scanned" not in paths

    def test_a_missing_services_directory_is_not_an_error(self, tmp_path):
        assert collect_backend(tmp_path / "absent").links == []


class TestDeduplicate:
    def test_keeps_one_entry_per_path_with_its_first_origin(self):
        links = [Link("a/b", "one.py"), Link("a/b", "two.py"), Link("c/d", "three.py")]
        unique = deduplicate(links)
        assert [(link.path, link.origin) for link in unique] == [
            ("a/b", "one.py"),
            ("c/d", "three.py"),
        ]
