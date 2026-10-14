"""
Tests for scripts/update_js_cache.py — the fail-loud contract (I1), and the
companions of a js library (R2, M-19 follow-up).

Before I1, a resource that could not be downloaded degraded the build
*silently*: the Docker image shipped a 404 on the emoji font for months and
flag glyphs rendered as letters. Now an undownloadable resource with no usable
cached copy — or a partially downloaded font — is a hard failure that turns
into a non-zero exit code from ``run_from_args``.

A js library may also declare ``companions``: the files its script loads from
beside itself. MathJax's CHTML output loads its fonts from
``[mathjax]/output/chtml/fonts/woff-v2``; with the script vendored alone, every
formula was drawn in fallback fonts. The contract (``TestCompanions``):

- the names are the matches of ``companions.pattern`` in the *cached* script,
  each fetched once from the library's URL with ``companions.dir`` beside it,
  and written to the same ``dir`` beside the cached script — an empty or
  ``"."`` dir being the script's own folder, never the host's root;
- they are checked on every run, an up-to-date script included — the script's
  ETag early return must not skip them — and fetched again when there is no
  record, when the script's hash is not the one the record was made for, or
  on ``force``; otherwise a file already present costs no request;
- a download counts only if it is non-empty and, for ``.woff``/``.woff2``,
  starts with the font signature: an error page served with a 200 is a failed
  download;
- a named file with neither a usable download nor a cached copy is one hard
  failure of the library, attributed to its consumer as the script's own
  failure is; with a cached copy it is soft;
- the files the pattern matches but the script no longer names are removed
  only when no named file is missing — the script and any other file in the
  folder are never touched — and the record is written only once every file
  is current, so a soft failure is retried on the next run.

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


# ---------------------------------------------------------------------------
# R2, M-19 follow-up: a js library's companions — MathJax's CHTML fonts
# ---------------------------------------------------------------------------

#: A js library whose script loads its fonts from ``fonts/woff/`` beside itself.
COMPANION_CONFIG = {
    "type": "js",
    "url": "https://cdn.example/pkg/es5/lib.js",
    "target": "lib.js",
    "companions": {"pattern": r"F_[A-Za-z0-9-]+\.woff", "dir": "fonts/woff"},
}
#: Where the CDN serves them: the directory of the library's URL, then ``companions.dir``.
COMPANION_BASE = "https://cdn.example/pkg/es5/fonts/woff/"
#: The folder of the library's URL itself: where the companions live when ``dir`` is empty or ``"."``.
SCRIPT_FOLDER_URL = "https://cdn.example/pkg/es5/"
#: The same address for the real MathJax: what its bundle calls ``[mathjax]/output/chtml/fonts/woff-v2``.
MATHJAX_FONTS_BASE = "https://cdn.jsdelivr.net/npm/mathjax@3/es5/output/chtml/fonts/woff-v2/"
#: The ETag the fake CDN serves the script with, and the one a seeded manifest remembers.
SCRIPT_ETAG = '"v1"'
#: The hash of no script: a companions record made for it is a record made for another script.
OLD_HASH = "0ld0ld0ld0ld"
#: What a CDN may answer with a 200 instead of a font.
ERROR_PAGE = b"<!DOCTYPE html><html><head><title>404 Not Found</title></head></html>"


def script_naming(*files: str, version: str = "v1") -> bytes:
    """A script loading ``files`` from beside itself, in the words of MathJax's bundle; ``version`` tells two apart."""
    faces = "".join(f'src:url("%%URL%%/{name}") format("woff");' for name in files)
    return f"/* {version} */ {faces}\n".encode()


def woff(label: str) -> bytes:
    """A font file: the WOFF signature, then a label telling files and versions apart."""
    return b"wOFF" + label.encode()


class FakeCdn:
    """The network boundary of one js library: its script, the script's ETag, the files served beside it.

    ``files`` maps a file name to what a GET at ``base + name`` answers (``None``: the request
    fails); any other URL fails too. Every GET is recorded.
    """

    def __init__(self, url: str, base: str, script: bytes | None, files: dict[str, bytes | None]):
        self.url = url
        self.base = base
        self.script = script
        self.files = files
        self.etag = SCRIPT_ETAG
        self.calls: list[str] = []

    def download_file(self, url, *args, **kwargs):
        self.calls.append(url)
        if url == self.url:
            return self.script
        return self.files.get(url.removeprefix(self.base)) if url.startswith(self.base) else None

    def get_remote_headers(self, url, *args, **kwargs):
        return {"ETag": self.etag} if url == self.url else None

    def publish(self, script: bytes, etag: str) -> None:
        """A new version of the script, under a new ETag."""
        self.script, self.etag = script, etag

    @property
    def companion_downloads(self) -> list[str]:
        """Every GET but the script's."""
        return [url for url in self.calls if url != self.url]


@pytest.fixture
def cdn(monkeypatch):
    """Install a fake CDN for one js library: ``cdn(script, {name: content})`` returns the recorder."""

    def install(script: bytes | None, files: dict[str, bytes | None], *, url: str = COMPANION_CONFIG["url"], base: str = COMPANION_BASE) -> FakeCdn:
        fake = FakeCdn(url, base, script, dict(files))
        monkeypatch.setattr(js_cache, "download_file", fake.download_file)
        monkeypatch.setattr(js_cache, "get_remote_headers", fake.get_remote_headers)
        return fake

    return install


def _record_of(files: dict[str, bytes]) -> dict:
    """``files`` as the companions record lists them."""
    return {name: {"hash": js_cache.get_file_hash(content), "size": len(content)} for name, content in files.items()}


def _companions_in(directory: str) -> dict:
    """``COMPANION_CONFIG`` with its companions in ``directory``, relative to the script's folder."""
    return {**COMPANION_CONFIG, "companions": {**COMPANION_CONFIG["companions"], "dir": directory}}


def _vendored(root: Path, script: bytes, fonts: dict[str, bytes] | None = None, *, name: str = "mylib", record_for: str | None = None, config: dict = COMPANION_CONFIG) -> dict:
    """Lay ``config`` out under ``root`` as an earlier run left it, and return its manifest.

    The script is cached and the manifest holds its hash and ``SCRIPT_ETAG``, so the fake CDN finds
    it up to date. ``fonts`` are already beside it; ``record_for`` is the script hash the companions
    record was made for (``None``: no record).
    """
    lib_dir = root / name
    lib_dir.mkdir(parents=True)
    (lib_dir / config["target"]).write_bytes(script)
    for file_name, content in (fonts or {}).items():
        path = lib_dir / config["companions"]["dir"] / file_name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
    lib = {"current_hash": js_cache.get_file_hash(script), "etag": SCRIPT_ETAG, "size": len(script), "versions": []}
    if record_for is not None:
        lib["companions"] = {"dir": config["companions"]["dir"], "for_hash": record_for, "files": _record_of(fonts or {})}
    return {"libraries": {name: lib}}


def _installed(root: Path, fake: FakeCdn) -> dict:
    """A first install of ``COMPANION_CONFIG`` from ``fake``; return the manifest as the next run loads it."""
    manifest: dict = {}
    assert js_cache.update_library(root, manifest, "mylib", COMPANION_CONFIG) is True
    assert js_cache._HARD_FAILURES == []
    js_cache.save_manifest(root, manifest)
    fake.calls.clear()
    return js_cache.load_manifest(root)


def _companions_on_disk(root: Path, name: str = "mylib") -> dict[str, bytes]:
    """The companions directory of ``name`` under ``root``, as {file name: bytes} (empty when absent)."""
    directory = root / name / COMPANION_CONFIG["companions"]["dir"]
    return _snapshot(directory) if directory.exists() else {}


def _urls(*names: str, base: str = COMPANION_BASE) -> list[str]:
    return sorted(base + name for name in names)


class TestCompanions:
    """R2, M-19 follow-up: the files a js library loads from beside itself (contract: module docstring).

    MathJax vendored alone drew every formula in fallback fonts: its CHTML output fetches them from
    beside the script. Fetching them along with the script is not enough either — the script's path
    returns on an ETag match before anything else runs, so an install whose script is already
    current, which is every install but the first, would never get them. That regression is
    ``test_an_up_to_date_script_still_brings_its_missing_companions``.

    ``FakeCdn`` answers only at the address the library's URL implies: a wrongly derived URL is a
    failed download here, never a lucky one.
    """

    def test_the_names_come_from_the_cached_script_and_the_address_from_the_library_url(self, tmp_path, cdn):
        script = script_naming("F_A.woff", "F_B.woff", "F_B.woff")
        fonts = {"F_A.woff": woff("A"), "F_B.woff": woff("B")}
        fake = cdn(script, fonts)
        manifest: dict = {}

        updated = js_cache.update_library(tmp_path, manifest, "mylib", COMPANION_CONFIG)

        assert updated is True
        assert js_cache._HARD_FAILURES == []
        assert sorted(fake.companion_downloads) == ["https://cdn.example/pkg/es5/fonts/woff/F_A.woff", "https://cdn.example/pkg/es5/fonts/woff/F_B.woff"], "one GET per file the script names (F_B.woff twice), beside the library's URL"
        assert _snapshot(tmp_path / "mylib" / "fonts" / "woff") == fonts
        lib = manifest["libraries"]["mylib"]
        assert lib["current_hash"] == js_cache.get_file_hash(script), "control: the hash of the script this run cached"
        assert lib["companions"] == {"dir": "fonts/woff", "for_hash": lib["current_hash"], "files": _record_of(fonts)}

    def test_an_up_to_date_script_still_brings_its_missing_companions(self, tmp_path, cdn):
        # An install from before companions: the script cached and current, nothing beside it.
        script = script_naming("F_A.woff", "F_B.woff")
        manifest = _vendored(tmp_path, script)
        fonts = {"F_A.woff": woff("A"), "F_B.woff": woff("B")}
        fake = cdn(script, fonts)

        updated = js_cache.update_library(tmp_path, manifest, "mylib", COMPANION_CONFIG)

        assert COMPANION_CONFIG["url"] not in fake.calls, "control: the ETag matched, the script was not downloaded"
        assert sorted(fake.companion_downloads) == _urls(*fonts)
        assert _companions_on_disk(tmp_path) == fonts
        assert updated is True, "the fonts were written: the library was updated"
        assert js_cache._HARD_FAILURES == []
        assert manifest["libraries"]["mylib"]["companions"]["for_hash"] == js_cache.get_file_hash(script)

    def test_once_every_companion_is_current_a_run_downloads_nothing(self, tmp_path, cdn):
        fonts = {"F_A.woff": woff("A"), "F_B.woff": woff("B")}
        fake = cdn(script_naming(*fonts), fonts)
        manifest = _installed(tmp_path, fake)
        record = manifest["libraries"]["mylib"]["companions"]

        updated = js_cache.update_library(tmp_path, manifest, "mylib", COMPANION_CONFIG)

        assert updated is False
        assert fake.calls == [], "the script is current (ETag) and so is every companion (for_hash): not one GET"
        assert js_cache._HARD_FAILURES == []
        assert _companions_on_disk(tmp_path) == fonts
        assert manifest["libraries"]["mylib"]["companions"] == record

    @pytest.mark.parametrize("trigger", ["new-script-version", "record-for-another-script", "force"])
    def test_every_companion_is_downloaded_again_when(self, tmp_path, cdn, trigger):
        names = ("F_A.woff", "F_B.woff")
        fake = cdn(script_naming(*names), {"F_A.woff": woff("A"), "F_B.woff": woff("B")})
        manifest = _installed(tmp_path, fake)  # without a trigger, the next run downloads nothing (test above)
        fake.files = {"F_A.woff": woff("A2"), "F_B.woff": woff("B2")}
        if trigger == "new-script-version":
            fake.publish(script_naming(*names, version="v2"), '"v2"')
        elif trigger == "record-for-another-script":
            manifest["libraries"]["mylib"]["companions"]["for_hash"] = OLD_HASH

        updated = js_cache.update_library(tmp_path, manifest, "mylib", COMPANION_CONFIG, force=trigger == "force")

        assert updated is True
        assert sorted(fake.companion_downloads) == _urls(*names), "every file, once each"
        assert _companions_on_disk(tmp_path) == {"F_A.woff": woff("A2"), "F_B.woff": woff("B2")}
        lib = manifest["libraries"]["mylib"]
        assert lib["current_hash"] == js_cache.get_file_hash(fake.script)
        assert lib["companions"]["for_hash"] == lib["current_hash"]

    def test_files_on_disk_without_a_record_are_downloaded_once_and_then_recorded(self, tmp_path, cdn):
        # The script and its hash are known and the fonts are on disk, but nothing says which script they were fetched for.
        script = script_naming("F_A.woff", "F_B.woff")
        manifest = _vendored(tmp_path, script, {"F_A.woff": woff("A-unknown"), "F_B.woff": woff("B-unknown")})
        fonts = {"F_A.woff": woff("A"), "F_B.woff": woff("B")}
        fake = cdn(script, fonts)

        assert js_cache.update_library(tmp_path, manifest, "mylib", COMPANION_CONFIG) is True

        assert COMPANION_CONFIG["url"] not in fake.calls, "control: the script is up to date"
        assert sorted(fake.companion_downloads) == _urls(*fonts), "every file, once each"
        assert _companions_on_disk(tmp_path) == fonts
        assert manifest["libraries"]["mylib"]["companions"] == {"dir": "fonts/woff", "for_hash": js_cache.get_file_hash(script), "files": _record_of(fonts)}

        fake.calls.clear()
        assert js_cache.update_library(tmp_path, manifest, "mylib", COMPANION_CONFIG) is False
        assert fake.calls == [], "recorded: the next run downloads nothing"

    def test_a_refresh_that_brings_the_same_bytes_writes_nothing_and_still_moves_the_record(self, tmp_path, cdn):
        fonts = {"F_A.woff": woff("A"), "F_B.woff": woff("B")}
        fake = cdn(script_naming(*fonts), fonts)
        manifest = _installed(tmp_path, fake)
        manifest["libraries"]["mylib"]["companions"]["for_hash"] = OLD_HASH

        updated = js_cache.update_library(tmp_path, manifest, "mylib", COMPANION_CONFIG)

        assert sorted(fake.companion_downloads) == _urls(*fonts), "control: the record was for another script, so every file was fetched"
        assert updated is False, "the same bytes: nothing written, nothing to report"
        lib = manifest["libraries"]["mylib"]
        assert lib["companions"]["for_hash"] == lib["current_hash"], "...and the record is current again, so the next run fetches nothing"

    @pytest.mark.parametrize("name, consumer", [("mathjax", "mkdocs"), ("mylib", None)], ids=["mathjax-is-mkdocs", "unknown-is-unattributed"])
    def test_a_file_with_neither_a_download_nor_a_cached_copy_is_one_hard_failure(self, tmp_path, cdn, name, consumer):
        script = script_naming("F_A.woff", "F_B.woff")
        manifest = _vendored(tmp_path, script, {"F_OLD.woff": woff("old")}, name=name)  # F_OLD.woff: named by no script
        cdn(script, {"F_A.woff": woff("A"), "F_B.woff": None})

        updated = js_cache.update_library(tmp_path, manifest, name, COMPANION_CONFIG)

        assert len(js_cache._HARD_FAILURES) == 1, "one failure for the library, not one per file"
        failure = js_cache._HARD_FAILURES[0]
        assert name in failure
        assert "F_B.woff" in failure
        assert "F_A.woff" not in failure, "only the missing file is named"
        assert failure.consumer == consumer
        assert updated is True, "F_A.woff was written all the same"
        assert _companions_on_disk(tmp_path, name) == {"F_A.woff": woff("A"), "F_OLD.woff": woff("old")}, "nothing is removed"
        assert "companions" not in manifest["libraries"][name], "no record: the next run tries again"

    def test_a_file_that_fails_with_a_cached_copy_is_kept_and_retried_on_the_next_run(self, tmp_path, cdn):
        fonts = {"F_A.woff": woff("A"), "F_B.woff": woff("B")}
        fake = cdn(script_naming(*fonts), fonts)
        manifest = _installed(tmp_path, fake)
        record_v1 = {"dir": "fonts/woff", "for_hash": js_cache.get_file_hash(fake.script), "files": _record_of(fonts)}
        # A new script version makes every companion due again, and F_B.woff cannot be downloaded.
        fake.publish(script_naming(*fonts, version="v2"), '"v2"')
        fake.files = {"F_A.woff": woff("A2"), "F_B.woff": None}

        js_cache.update_library(tmp_path, manifest, "mylib", COMPANION_CONFIG)

        assert COMPANION_BASE + "F_B.woff" in fake.companion_downloads, "control: F_B.woff was due and was asked for"
        assert js_cache._HARD_FAILURES == [], "a cached copy makes the failure soft"
        assert _companions_on_disk(tmp_path) == {"F_A.woff": woff("A2"), "F_B.woff": woff("B")}, "the cached bytes are untouched, the other file is refreshed"
        assert manifest["libraries"]["mylib"]["companions"] == record_v1, "the record still names the old script..."

        fake.files["F_B.woff"] = woff("B2")
        fake.calls.clear()
        js_cache.update_library(tmp_path, manifest, "mylib", COMPANION_CONFIG)

        assert COMPANION_BASE + "F_B.woff" in fake.companion_downloads, "...so the next run tries again"
        assert _companions_on_disk(tmp_path)["F_B.woff"] == woff("B2")
        lib = manifest["libraries"]["mylib"]
        assert lib["companions"]["for_hash"] == lib["current_hash"] == js_cache.get_file_hash(fake.script)

    def test_after_a_lost_manifest_cached_companions_are_retried_softly_and_left_unrecorded(self, tmp_path, cdn):
        # Every file is on disk, the manifest is gone and the script cannot be downloaded: no known hash to tie them to.
        script = script_naming("F_A.woff", "F_B.woff")
        fonts = {"F_A.woff": woff("A"), "F_B.woff": woff("B")}
        _vendored(tmp_path, script, fonts)
        manifest = js_cache.load_manifest(tmp_path)
        fake = cdn(None, {"F_A.woff": None, "F_B.woff": None})

        updated = js_cache.update_library(tmp_path, manifest, "mylib", COMPANION_CONFIG)

        assert COMPANION_CONFIG["url"] in fake.calls, "control: the script was asked for and failed..."
        assert "current_hash" not in manifest["libraries"].get("mylib", {}), "...so no script hash is known"
        assert sorted(fake.companion_downloads) == _urls(*fonts), "no record: every file is due"
        assert js_cache._HARD_FAILURES == [], "every file is cached: a failed download loses nothing"
        assert _companions_on_disk(tmp_path) == fonts
        assert "companions" not in manifest["libraries"].get("mylib", {}), "no record for files no known script was checked against"
        assert updated is False

        # Once the CDN answers again, the script comes back with its hash, and the companions get their record.
        fake.script = script
        fake.files = dict(fonts)
        fake.calls.clear()
        js_cache.update_library(tmp_path, manifest, "mylib", COMPANION_CONFIG)

        assert sorted(fake.companion_downloads) == _urls(*fonts)
        assert manifest["libraries"]["mylib"]["companions"]["for_hash"] == js_cache.get_file_hash(script)

    def test_a_200_that_is_not_a_font_is_refused_like_a_failed_download(self, tmp_path, cdn):
        # F_A.woff is cached and F_B.woff is not; the CDN answers both with an error page and a 200.
        script = script_naming("F_A.woff", "F_B.woff")
        manifest = _vendored(tmp_path, script, {"F_A.woff": woff("A")}, record_for=OLD_HASH)
        fake = cdn(script, {"F_A.woff": ERROR_PAGE, "F_B.woff": ERROR_PAGE})

        updated = js_cache.update_library(tmp_path, manifest, "mylib", COMPANION_CONFIG)

        assert sorted(fake.companion_downloads) == _urls("F_A.woff", "F_B.woff"), "control: both were due and both were answered"
        assert updated is False, "nothing was written"
        assert _companions_on_disk(tmp_path) == {"F_A.woff": woff("A")}, "no error page cached as a font, no cached font overwritten by one"
        assert len(js_cache._HARD_FAILURES) == 1
        failure = js_cache._HARD_FAILURES[0]
        assert "F_B.woff" in failure, "refused without a cached copy: missing"
        assert "F_A.woff" not in failure, "refused with a cached copy: kept"
        assert manifest["libraries"]["mylib"]["companions"]["for_hash"] == OLD_HASH

    @pytest.mark.parametrize(
        "file_name, content, usable",
        [
            ("F.woff", b"wOFF\x00\x01\x00\x00", True),
            ("F.woff2", b"wOF2\x00\x01\x00\x00", True),
            ("F.woff2", b"wOFF\x00\x01\x00\x00", False),
            ("F.woff", ERROR_PAGE, False),
            ("F.woff", b"", False),
            ("F.woff", None, False),
            ("F.js", b"console.log(1)", True),
            ("F.js", b"", False),
        ],
        ids=["woff", "woff2", "woff-bytes-named-woff2", "error-page", "empty-200", "failed", "no-known-signature", "no-known-signature-empty"],
    )
    def test_a_download_is_usable_when_it_has_content_and_its_font_signature(self, file_name, content, usable):
        assert js_cache._usable(file_name, content) is usable

    def test_a_script_that_names_no_companion_is_a_hard_failure_and_removes_nothing(self, tmp_path, cdn):
        # A version that no longer spells its fonts' names out the way the pattern expects.
        script = b'/* v2 */ src:url("%%URL%%/" + face + ".woff");\n'
        manifest = _vendored(tmp_path, script, {"F_A.woff": woff("A")}, record_for=OLD_HASH)
        fake = cdn(script, {"F_A.woff": woff("A2")})

        updated = js_cache.update_library(tmp_path, manifest, "mylib", COMPANION_CONFIG)

        assert updated is False
        assert len(js_cache._HARD_FAILURES) == 1
        failure = js_cache._HARD_FAILURES[0]
        assert "mylib" in failure
        assert COMPANION_CONFIG["companions"]["pattern"] in failure, "the pattern that matched nothing is named"
        assert fake.companion_downloads == []
        assert _companions_on_disk(tmp_path) == {"F_A.woff": woff("A")}, "naming nothing does not make every cached file stale"

    def test_a_file_the_script_no_longer_names_is_removed_after_a_complete_run(self, tmp_path, cdn):
        fake = cdn(script_naming("F_A.woff", "F_B.woff"), {"F_A.woff": woff("A"), "F_B.woff": woff("B")})
        manifest = _installed(tmp_path, fake)
        fake.publish(script_naming("F_A.woff", "F_C.woff", version="v2"), '"v2"')  # v2 names F_C.woff instead of F_B.woff
        fake.files = {"F_A.woff": woff("A"), "F_C.woff": woff("C")}

        js_cache.update_library(tmp_path, manifest, "mylib", COMPANION_CONFIG)

        assert js_cache._HARD_FAILURES == []
        current = {"F_A.woff": woff("A"), "F_C.woff": woff("C")}
        assert _companions_on_disk(tmp_path) == current, "F_B.woff is no longer named: removed"
        assert manifest["libraries"]["mylib"]["companions"]["files"] == _record_of(current)

    def test_a_file_the_script_no_longer_names_is_kept_while_a_named_one_is_missing(self, tmp_path, cdn):
        fake = cdn(script_naming("F_A.woff", "F_B.woff"), {"F_A.woff": woff("A"), "F_B.woff": woff("B")})
        manifest = _installed(tmp_path, fake)
        record_v1 = manifest["libraries"]["mylib"]["companions"]
        fake.publish(script_naming("F_A.woff", "F_C.woff", version="v2"), '"v2"')
        fake.files = {"F_A.woff": woff("A"), "F_C.woff": None}

        js_cache.update_library(tmp_path, manifest, "mylib", COMPANION_CONFIG)

        assert len(js_cache._HARD_FAILURES) == 1
        assert "F_C.woff" in js_cache._HARD_FAILURES[0]
        assert _companions_on_disk(tmp_path) == {"F_A.woff": woff("A"), "F_B.woff": woff("B")}, "nothing is removed while a named file is missing"
        assert manifest["libraries"]["mylib"]["companions"] == record_v1, "and the record still names the old script"

    def test_a_stray_file_beside_current_companions_is_removed_and_reported(self, tmp_path, cdn):
        fonts = {"F_A.woff": woff("A"), "F_B.woff": woff("B")}
        fake = cdn(script_naming(*fonts), fonts)
        manifest = _installed(tmp_path, fake)
        (tmp_path / "mylib" / "fonts" / "woff" / "F_OLD.woff").write_bytes(woff("old"))

        updated = js_cache.update_library(tmp_path, manifest, "mylib", COMPANION_CONFIG)

        assert fake.calls == [], "control: nothing was due, so the removal is all this run did"
        assert updated is True, "a removal is an update"
        assert _companions_on_disk(tmp_path) == fonts

    @pytest.mark.parametrize("directory", ["", "."], ids=["empty-dir", "dot-dir"])
    def test_an_empty_or_dot_dir_is_the_script_s_own_folder(self, tmp_path, cdn, directory):
        script = script_naming("F_A.woff")
        fake = cdn(script, {"F_A.woff": woff("A")}, base=SCRIPT_FOLDER_URL)

        assert js_cache.update_library(tmp_path, {}, "mylib", _companions_in(directory)) is True

        assert js_cache._HARD_FAILURES == []
        assert fake.companion_downloads == ["https://cdn.example/pkg/es5/F_A.woff"], "from the script's folder, never from the host's root"
        assert _snapshot(tmp_path / "mylib") == {"lib.js": script, "F_A.woff": woff("A")}, "written beside the cached script"

    def test_companions_in_the_script_s_own_folder_sweep_only_what_the_pattern_names(self, tmp_path, cdn):
        config = _companions_in(".")
        script = script_naming("F_A.woff")
        manifest = _vendored(tmp_path, script, {"F_OLD.woff": woff("old")}, config=config)  # F_OLD.woff: a companion no longer named
        (tmp_path / "mylib" / "notes.txt").write_bytes(b"not a companion")
        cdn(script, {"F_A.woff": woff("A")}, base=SCRIPT_FOLDER_URL)

        assert js_cache.update_library(tmp_path, manifest, "mylib", config) is True

        assert js_cache._HARD_FAILURES == []
        assert _snapshot(tmp_path / "mylib") == {"lib.js": script, "F_A.woff": woff("A"), "notes.txt": b"not a companion"}, "F_OLD.woff is swept; the script and notes.txt match no pattern and stay"

    def test_without_a_cached_script_only_the_script_failure_is_recorded(self, tmp_path, cdn):
        fake = cdn(None, {"F_A.woff": woff("A"), "F_B.woff": woff("B")})  # the script fails to download, none is cached

        updated = js_cache.update_library(tmp_path, {}, "mylib", COMPANION_CONFIG)

        assert updated is False
        assert fake.companion_downloads == [], "no script, no names: nothing else is asked for"
        assert len(js_cache._HARD_FAILURES) == 1, "the script's failure, once: its companions do not report it again"
        assert "companion" not in js_cache._HARD_FAILURES[0]

    def test_a_js_library_without_companions_downloads_its_script_and_nothing_else(self, tmp_path, cdn):
        # The script even names a font: without ``companions`` in the config, nothing is read from it.
        fake = cdn(script_naming("F_A.woff"), {"F_A.woff": woff("A")}, url=JS_CONFIG["url"])
        manifest: dict = {}

        assert js_cache.update_library(tmp_path, manifest, "mylib", JS_CONFIG) is True
        assert fake.calls == [JS_CONFIG["url"]], "one GET: the script"
        assert sorted(path.relative_to(tmp_path).as_posix() for path in tmp_path.rglob("*")) == ["mylib", "mylib/lib.js"]
        assert "companions" not in manifest["libraries"]["mylib"]

        fake.calls.clear()
        assert js_cache.update_library(tmp_path, manifest, "mylib", JS_CONFIG) is False, "and an up-to-date script is still a no-op"
        assert fake.calls == []

    def test_mathjax_fetches_its_fonts_from_beside_its_cdn_script_into_the_same_place_beside_its_copy(self, tmp_path, cdn):
        config = js_cache.LIBRARIES["mathjax"]
        fonts = {name: woff(name) for name in ("MathJax_Zero.woff", "MathJax_Main-Regular.woff", "MathJax_Math-BoldItalic.woff", "MathJax_Size1-Regular.woff")}
        fake = cdn(script_naming(*fonts, "MathJax_Zero.woff"), fonts, url=config["url"], base=MATHJAX_FONTS_BASE)

        assert js_cache.update_library(tmp_path, {}, "mathjax", config) is True

        assert js_cache._HARD_FAILURES == []
        assert sorted(fake.companion_downloads) == _urls(*fonts, base=MATHJAX_FONTS_BASE)
        # MathJax reads them from [mathjax]/output/chtml/fonts/woff-v2, [mathjax] being the script's own directory:
        # the copy must mirror the CDN relative to the script, so that offline it finds what it finds online.
        cdn_dir = config["url"].rsplit("/", 1)[0] + "/"
        local_dir = (tmp_path / "mathjax" / config["target"]).parent
        for url in fake.companion_downloads:
            assert url.startswith(cdn_dir)
            assert (local_dir / url.removeprefix(cdn_dir)).read_bytes() == fonts[url.rsplit("/", 1)[1]]

    def test_a_missing_mathjax_font_is_a_failure_of_the_docs_build(self, tmp_path, cdn):
        config = js_cache.LIBRARIES["mathjax"]
        cdn(script_naming("MathJax_Zero.woff", "MathJax_Main-Regular.woff"), {"MathJax_Zero.woff": woff("zero")}, url=config["url"], base=MATHJAX_FONTS_BASE)

        js_cache.update_library(tmp_path, {}, "mathjax", config)

        assert len(js_cache._HARD_FAILURES) == 1
        failure = js_cache._HARD_FAILURES[0]
        assert "MathJax_Main-Regular.woff" in failure
        assert failure.consumer == "mkdocs", "from vendor_dir_key: the docs ship MathJax, the frontend does not"
