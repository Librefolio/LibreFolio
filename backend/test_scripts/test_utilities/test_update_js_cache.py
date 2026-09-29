"""
Tests for scripts/update_js_cache.py — the fail-loud contract (I1).

Before I1, a resource that could not be downloaded degraded the build
*silently*: the Docker image shipped a 404 on the emoji font for months and
flag glyphs rendered as letters. Now an undownloadable resource with no usable
cached copy — or a partially downloaded font — is a hard failure that turns
into a non-zero exit code from ``run_from_args``.

The module under test is import-time inert (all work happens inside
functions), so these tests monkeypatch the network boundary
(``download_file`` / ``get_remote_headers``) and point the filesystem side at
``tmp_path``. No DB, no server, no network, no writes outside tmp_path — PURE.
"""

import re
from pathlib import Path
from types import SimpleNamespace

import pytest

import scripts.update_js_cache as js_cache

JS_CONFIG = {"type": "js", "url": "https://cdn.example/lib.js", "target": "lib.js"}
FONT_CONFIG = {
    "type": "font",
    "css_url": "https://fonts.example/fake.css",
    "file_prefix": "fake-font",
    "css_file": "fake-font.css",
}

# Two subsets, the minimum that makes "partial" mean something.
FAKE_CSS = """
@font-face { font-family: 'Fake'; src: url(https://fonts.example/a.woff2); unicode-range: U+0000-00FF; }
@font-face { font-family: 'Fake'; src: url(https://fonts.example/b.woff2); unicode-range: U+1F300-1F5FF; }
"""


@pytest.fixture(autouse=True)
def _clean_failures():
    """_HARD_FAILURES is module-global — every test starts and ends empty."""
    js_cache._HARD_FAILURES.clear()
    yield
    js_cache._HARD_FAILURES.clear()


@pytest.fixture
def no_network(monkeypatch):
    """Every download fails; every HEAD probe finds nothing."""
    monkeypatch.setattr(js_cache, "download_file", lambda *a, **kw: None)
    monkeypatch.setattr(js_cache, "get_remote_headers", lambda *a, **kw: None)


class TestJsResource:
    def test_download_failure_without_cache_is_recorded_as_hard_failure(self, tmp_path, no_network):
        updated = js_cache.update_library(tmp_path, {}, "mylib", JS_CONFIG)

        assert updated is False
        assert len(js_cache._HARD_FAILURES) == 1
        assert "mylib" in js_cache._HARD_FAILURES[0]

    def test_download_failure_with_cached_copy_is_soft(self, tmp_path, no_network):
        # A usable cached copy: the file exists and the manifest names a hash.
        lib_dir = tmp_path / "mylib"
        lib_dir.mkdir(parents=True)
        (lib_dir / "lib.js").write_bytes(b"cached")
        manifest = {"libraries": {"mylib": {"current_hash": "abc123", "versions": []}}}

        updated = js_cache.update_library(tmp_path, manifest, "mylib", JS_CONFIG)

        assert updated is False
        assert js_cache._HARD_FAILURES == []


class TestFontResource:
    def test_css_failure_without_cache_is_a_hard_failure(self, tmp_path, no_network):
        updated = js_cache.update_library(tmp_path, {}, "fake-font", FONT_CONFIG)

        assert updated is False
        assert len(js_cache._HARD_FAILURES) == 1
        assert "fake-font" in js_cache._HARD_FAILURES[0]

    def test_css_failure_with_cached_copy_is_soft(self, tmp_path, no_network):
        (tmp_path / "fake-font.css").write_text("/* cached */")

        updated = js_cache.update_library(tmp_path, {}, "fake-font", FONT_CONFIG)

        assert updated is False
        assert js_cache._HARD_FAILURES == []

    def test_partial_subsets_are_a_hard_failure_and_no_partial_css_is_written(self, tmp_path, monkeypatch):
        # The CSS downloads fine; exactly one of the two woff2 subsets does not.
        # A partial font renders SOME glyph ranges as fallback letters — the
        # same silent degradation as a missing font, hence loud.
        def fake_download(url, *a, **kw):
            if url == FONT_CONFIG["css_url"]:
                return FAKE_CSS.encode()
            if url.endswith("a.woff2"):
                return b"woff2-a"
            return None  # b.woff2 fails

        monkeypatch.setattr(js_cache, "download_file", fake_download)

        updated = js_cache.update_library(tmp_path, {}, "fake-font", FONT_CONFIG)

        assert updated is False
        assert len(js_cache._HARD_FAILURES) == 1
        assert "1/2" in js_cache._HARD_FAILURES[0]
        # The previous cached version (if any) stays authoritative: no partial CSS.
        assert not (tmp_path / "fake-font.css").exists()


class TestExitCode:
    def test_run_from_args_returns_1_when_any_hard_failure_was_collected(self, monkeypatch):
        def fake_update_all(force=False):
            js_cache._hard_fail("mylib", "download failed, no cached version")

        monkeypatch.setattr(js_cache, "update_all_libraries", fake_update_all)

        assert js_cache.run_from_args(SimpleNamespace(force=False)) == 1

    def test_run_from_args_returns_0_when_everything_is_cached_or_downloaded(self, monkeypatch):
        monkeypatch.setattr(js_cache, "update_all_libraries", lambda force=False: 0)

        assert js_cache.run_from_args(SimpleNamespace(force=False)) == 0


class TestConsumerScopedFailure:
    """Which build a missing resource actually breaks.

    I1 made every resource fatal to every build. That was right about silence
    and wrong about scope: MathJax lands in ``mkdocs_src/`` and is referenced
    nowhere under ``frontend/``, yet a failure to fetch it aborted the frontend
    build — on a fresh worktree, before any test could run. Meanwhile an older
    worktree with a warm cache went green, so the two lanes differed in *age*,
    not in health.

    Both halves are exercised below, because a gate proven only where it fires
    is not proven: the half that grants permission is the one that matters.
    """

    @pytest.fixture
    def only_docs_asset_missing(self, monkeypatch):
        def fake_update_all(force=False):
            js_cache._hard_fail("mathjax", "download failed, no cached version")

        monkeypatch.setattr(js_cache, "update_all_libraries", fake_update_all)

    @pytest.fixture
    def only_frontend_asset_missing(self, monkeypatch):
        def fake_update_all(force=False):
            js_cache._hard_fail("noto-color-emoji", "CSS download failed, no cached version")

        monkeypatch.setattr(js_cache, "update_all_libraries", fake_update_all)

    def test_a_docs_only_asset_no_longer_aborts_the_frontend_build(self, only_docs_asset_missing):
        args = SimpleNamespace(force=False, required_for=["frontend"])
        assert js_cache.run_from_args(args) == 0

    def test_but_it_is_still_reported_rather_than_swallowed(self, only_docs_asset_missing, capsys):
        js_cache.run_from_args(SimpleNamespace(force=False, required_for=["frontend"]))
        out = capsys.readouterr().out
        assert "mathjax" in out
        assert "mkdocs" in out, "the consumer that still needs it must be named"

    def test_a_frontend_asset_still_aborts_the_frontend_build(self, only_frontend_asset_missing):
        # The acceptance control: without this, the fix is a gate turned off
        # rather than a gate corrected.
        args = SimpleNamespace(force=False, required_for=["frontend"])
        assert js_cache.run_from_args(args) == 1

    def test_a_docs_only_asset_still_aborts_the_docs_build(self, only_docs_asset_missing):
        args = SimpleNamespace(force=False, required_for=["mkdocs"])
        assert js_cache.run_from_args(args) == 1

    def test_an_unnarrowed_call_keeps_every_resource_fatal(self, only_docs_asset_missing):
        # Docker ships mkdocs_src/site/ next to the bundle, so it must not narrow.
        assert js_cache.run_from_args(SimpleNamespace(force=False, required_for=None)) == 1

    def test_attribution_comes_from_vendor_dir_key_not_from_a_name_list(self):
        # A hand-written exemption list rots exactly the way a hand-written
        # directory list does; the mapping must be derived from configuration.
        for name, config in js_cache.LIBRARIES.items():
            js_cache._HARD_FAILURES.clear()
            js_cache._hard_fail(name, "x")
            expected = js_cache.CONSUMERS[config["vendor_dir_key"]]
            assert js_cache._HARD_FAILURES[0].consumer == expected

    @pytest.mark.parametrize("required_for", [["frontend"], ["mkdocs"], None])
    def test_an_unattributed_resource_stays_fatal_for_every_consumer(self, required_for):
        # Narrowing may only excuse a consumer we positively know does not ship
        # the resource. An unregistered name is not such a case, and letting it
        # fall through would turn "I don't know" into "it doesn't matter".
        js_cache._hard_fail("mystery", "download failed")
        assert js_cache.run_from_args(SimpleNamespace(force=False, required_for=required_for)) == 1


# ---------------------------------------------------------------------------
# K step 12b (e): the Noto resource keeps only the flags subset
# ---------------------------------------------------------------------------

FLAGS_RANGE = "U+1f1e6-1f1ff"
DIGITS_RANGE = "U+23, U+2a, U+30-39, U+a9"

#: The fake Google subsets: (woff2 url, unicode-range, content). ``decoy`` starts
#: with the flags range but is not it — a subset is kept only when its whole
#: normalised range is listed, never because it overlaps the flags.
SUBSETS = {
    "digits": ("https://fonts.example/digits.woff2", DIGITS_RANGE, b"woff2-digits"),
    "flags": ("https://fonts.example/flags.woff2", FLAGS_RANGE, b"woff2-flags"),
    "decoy": ("https://fonts.example/decoy.woff2", "U+1f1e6-1f1ff, U+1f308", b"woff2-decoy"),
    "misc": ("https://fonts.example/misc.woff2", "U+1f300-1f5ff", b"woff2-misc"),
}
FLAGS_URL = SUBSETS["flags"][0]
KEEP_FLAGS_CONFIG = {**FONT_CONFIG, "keep_unicode_ranges": [FLAGS_RANGE]}
PROJECT_ROOT = Path(__file__).resolve().parents[3]


def google_css(*names: str, flags_range: str | None = None) -> str:
    """A Google Fonts CSS response serving the named subsets, in the order given."""
    blocks = []
    for name in names:
        url, unicode_range, _content = SUBSETS[name]
        if name == "flags" and flags_range:
            unicode_range = flags_range
        blocks.append(f"/* {name} */\n@font-face {{\n  font-family: 'Fake';\n  font-weight: 400;\n  src: url({url}) format('woff2');\n  unicode-range: {unicode_range};\n}}\n")
    return "".join(blocks)


class FakeGoogle:
    """The network boundary: serves the CSS and the subsets, records every download asked for."""

    def __init__(self, css: str, failing: frozenset[str] = frozenset()):
        self.css = css.encode()
        self.failing = failing
        self.calls: list[str] = []

    def __call__(self, url, *args, **kwargs):
        self.calls.append(url)
        if url == FONT_CONFIG["css_url"]:
            return self.css
        for name, (subset_url, _range, content) in SUBSETS.items():
            if url == subset_url:
                return None if name in self.failing else content
        return None

    @property
    def woff2_downloads(self) -> list[str]:
        return [url for url in self.calls if url.endswith(".woff2")]


@pytest.fixture
def google(monkeypatch):
    """Install a fake Google Fonts: ``google(css, failing={...})`` returns the recorder."""

    def install(css: str, failing: frozenset[str] = frozenset()) -> FakeGoogle:
        fake = FakeGoogle(css, frozenset(failing))
        monkeypatch.setattr(js_cache, "download_file", fake)
        return fake

    return install


def _snapshot(root: Path) -> dict[str, bytes]:
    return {path.name: path.read_bytes() for path in root.iterdir() if path.is_file()}


class _SeededCache:
    """The cache the 11-subset generation left behind, and a way to prove it was not touched."""

    def __init__(self, root: Path, extra: dict[str, bytes] | None = None):
        files = {f"fake-font.{i}.woff2": f"old-subset-{i}".encode() for i in range(11)}
        files["fake-font.css"] = b"/* cached: 11 subsets */\n"
        files.update(extra or {})
        for name, content in files.items():
            (root / name).write_bytes(content)
        self.root = root
        self.files = files
        # Today's manifest shape: a CSS hash and no kept-ranges fingerprint.
        self.manifest = {"libraries": {"fake-font": {"current_hash": "0ld0ld0ld0ld", "versions": []}}}

    def unchanged(self) -> bool:
        return _snapshot(self.root) == self.files


def _woff2_files(root: Path) -> list[str]:
    return sorted(path.name for path in root.glob("fake-font.*.woff2"))


def _normalised(unicode_range: str) -> str:
    return re.sub(r"\s+", "", unicode_range).lower()


class TestKeepOnlyTheFlagsSubset:
    """K step 12b (e): Noto Color Emoji is cached for its flags, and for nothing else.

    The flags come from one global face, ``'LF Flags'`` (``frontend/static/lf-flags.css``), whose
    last source is ``/fonts/noto-color-emoji/noto-color-emoji.0.woff2``. So the cache must hold the
    regional indicators, U+1F1E6-1F1FF, **as subset 0** whatever position Google serves them in
    (D-b3), and nothing else: the other ten subsets are dead weight, and subset 2 — digits, ``#``,
    ``*`` — is the one that must never be served under the Noto family name again.

    The contract: ``keep_unicode_ranges`` on the resource; a subset is kept when its unicode-range,
    lowercased and without spaces, is in that list; no match is fail-loud exactly like "no subsets
    parsed" (hard without a cached copy, soft with one); "already up-to-date" also needs the stored
    kept-ranges fingerprint to equal the configuration, so the first run after the change rewrites
    the cache; a successful write removes the stale ``<prefix>.N.woff2`` files, a failed one
    removes and rewrites nothing.
    """

    def test_the_noto_resource_keeps_exactly_the_flags_range(self):
        assert js_cache.LIBRARIES["noto-color-emoji"].get("keep_unicode_ranges") == [FLAGS_RANGE]

    def test_subset_0_is_the_file_lf_flags_css_points_at(self):
        # Control: static/lf-flags.css reaches the flags through this exact path.
        config = js_cache.LIBRARIES["noto-color-emoji"]
        flags_file = js_cache.VENDOR_DIRS[config["vendor_dir_key"]] / f"{config['file_prefix']}.0.woff2"
        assert flags_file.resolve() == (PROJECT_ROOT / "frontend/static/fonts/noto-color-emoji/noto-color-emoji.0.woff2").resolve()

    @pytest.mark.parametrize(
        "order",
        [("flags", "digits", "misc", "decoy"), ("digits", "flags", "decoy", "misc"), ("digits", "misc", "decoy", "flags")],
        ids=["flags-first", "flags-middle", "flags-last"],
    )
    def test_only_the_flags_subset_is_downloaded_and_it_is_written_as_subset_0(self, tmp_path, google, order):
        fake = google(google_css(*order))

        updated = js_cache.update_library(tmp_path, {}, "fake-font", KEEP_FLAGS_CONFIG)

        assert updated is True
        assert js_cache._HARD_FAILURES == []
        assert fake.woff2_downloads == [FLAGS_URL], "only the flags subset is downloaded"
        assert _woff2_files(tmp_path) == ["fake-font.0.woff2"]
        assert (tmp_path / "fake-font.0.woff2").read_bytes() == b"woff2-flags", "subset 0 is the flags, wherever Google put them"

    def test_the_range_is_matched_after_normalisation(self, tmp_path, google):
        fake = google(google_css("digits", "flags", flags_range="U+1F1E6-1F1FF"))

        assert js_cache.update_library(tmp_path, {}, "fake-font", KEEP_FLAGS_CONFIG) is True
        assert fake.woff2_downloads == [FLAGS_URL]
        assert (tmp_path / "fake-font.0.woff2").read_bytes() == b"woff2-flags"

    def test_the_generated_css_declares_only_the_kept_subset(self, tmp_path, google):
        google(google_css("digits", "flags", "misc"))

        js_cache.update_library(tmp_path, {}, "fake-font", KEEP_FLAGS_CONFIG)

        faces = re.findall(r"@font-face\s*\{([^}]*)\}", (tmp_path / "fake-font.css").read_text())
        assert len(faces) == 1, "the generated CSS declares the kept subset and nothing else"
        sources = re.findall(r"url\(\s*['\"]?([^'\")]+)", faces[0])
        assert [Path(source).name for source in sources] == ["fake-font.0.woff2"]
        assert [_normalised(r) for r in re.findall(r"unicode-range:\s*([^;]+);", faces[0])] == [FLAGS_RANGE.lower()]

    def test_no_matching_subset_without_a_cached_copy_is_a_hard_failure(self, tmp_path, google):
        fake = google(google_css("digits", "decoy", "misc"))

        updated = js_cache.update_library(tmp_path, {}, "fake-font", KEEP_FLAGS_CONFIG)

        assert updated is False
        assert len(js_cache._HARD_FAILURES) == 1
        assert "fake-font" in js_cache._HARD_FAILURES[0]
        assert fake.woff2_downloads == [], "no subset matches: nothing is downloaded"
        assert not (tmp_path / "fake-font.css").exists()
        assert _woff2_files(tmp_path) == []

    def test_no_matching_subset_with_a_cached_copy_is_soft_and_leaves_the_cache_alone(self, tmp_path, google):
        cache = _SeededCache(tmp_path)
        fake = google(google_css("digits", "decoy", "misc"))

        updated = js_cache.update_library(tmp_path, cache.manifest, "fake-font", KEEP_FLAGS_CONFIG)

        assert updated is False
        assert js_cache._HARD_FAILURES == []
        assert fake.woff2_downloads == []
        assert cache.unchanged(), "the cached copy stays authoritative: nothing rewritten, nothing removed"

    def test_same_google_css_without_a_stored_fingerprint_is_not_up_to_date(self, tmp_path, google):
        # The cache the 11-subset generation wrote: same Google CSS, no kept-ranges fingerprint.
        css = google_css("flags", "digits", "misc")
        cache = _SeededCache(tmp_path)
        cache.manifest["libraries"]["fake-font"]["current_hash"] = js_cache.get_file_hash(css.encode())
        fake = google(css)

        updated = js_cache.update_library(tmp_path, cache.manifest, "fake-font", KEEP_FLAGS_CONFIG)

        assert updated is True, "same CSS hash, but the cache predates keep_unicode_ranges: the first run must rewrite it"
        assert fake.woff2_downloads == [FLAGS_URL]

    def test_same_google_css_with_a_different_kept_set_is_not_up_to_date(self, tmp_path, google):
        fake = google(google_css("flags", "digits"))
        manifest: dict = {}
        assert js_cache.update_library(tmp_path, manifest, "fake-font", {**FONT_CONFIG, "keep_unicode_ranges": [DIGITS_RANGE]}) is True
        js_cache.save_manifest(tmp_path, manifest)
        fake.calls.clear()

        updated = js_cache.update_library(tmp_path, js_cache.load_manifest(tmp_path), "fake-font", KEEP_FLAGS_CONFIG)

        assert updated is True, "same CSS hash, but the kept ranges changed: not up-to-date"
        assert fake.woff2_downloads == [FLAGS_URL]
        assert _woff2_files(tmp_path) == ["fake-font.0.woff2"]
        assert (tmp_path / "fake-font.0.woff2").read_bytes() == b"woff2-flags"

    def test_same_google_css_and_same_kept_set_is_up_to_date(self, tmp_path, google):
        # Control: the fingerprint survives the manifest's JSON round-trip, so a second run is a no-op.
        fake = google(google_css("digits", "flags"))
        manifest: dict = {}
        assert js_cache.update_library(tmp_path, manifest, "fake-font", KEEP_FLAGS_CONFIG) is True
        js_cache.save_manifest(tmp_path, manifest)
        fake.calls.clear()

        updated = js_cache.update_library(tmp_path, js_cache.load_manifest(tmp_path), "fake-font", KEEP_FLAGS_CONFIG)

        assert updated is False
        assert fake.woff2_downloads == []

    def test_stale_subsets_are_removed_after_a_successful_write(self, tmp_path, google):
        cache = _SeededCache(tmp_path, extra={"other-font.1.woff2": b"not ours", "notes.txt": b"not a subset"})
        google(google_css("digits", "misc", "flags"))

        updated = js_cache.update_library(tmp_path, cache.manifest, "fake-font", KEEP_FLAGS_CONFIG)

        assert updated is True
        assert _woff2_files(tmp_path) == ["fake-font.0.woff2"], "fake-font.1..10.woff2 are stale once only the flags are kept"
        assert (tmp_path / "fake-font.0.woff2").read_bytes() == b"woff2-flags"
        # The sweep is scoped to this resource's own subsets.
        assert (tmp_path / "other-font.1.woff2").read_bytes() == b"not ours"
        assert (tmp_path / "notes.txt").read_bytes() == b"not a subset"

    def test_a_failed_flags_download_removes_and_rewrites_nothing(self, tmp_path, google):
        cache = _SeededCache(tmp_path)
        google(google_css("digits", "flags", "misc"), failing={"flags"})

        updated = js_cache.update_library(tmp_path, cache.manifest, "fake-font", KEEP_FLAGS_CONFIG)

        assert updated is False
        assert len(js_cache._HARD_FAILURES) == 1, "I1: a subset that fails to download is loud"
        assert cache.unchanged(), "the previous cache stays exactly as it was: every stale file kept, none rewritten"

    def test_a_font_without_keep_unicode_ranges_keeps_every_subset(self, tmp_path, google):
        # Control, pinned by test_partial_subsets_are_a_hard_failure_and_no_partial_css_is_written:
        # the filter applies only where a resource declares it.
        google(google_css("flags", "digits"))

        assert js_cache.update_library(tmp_path, {}, "fake-font", FONT_CONFIG) is True
        assert _woff2_files(tmp_path) == ["fake-font.0.woff2", "fake-font.1.woff2"]
