"""A language is done only for the EN version it was translated from: the Aphra hash cache (M, R2 B11).

``mkdocs_src/aphra-pipeline/.translate-hashes.json`` holds one entry per EN page, keyed by its path under
``mkdocs_src/docs/``: ``md5`` is the EN version the entry's ``langs_done`` were translated (or stamped) from, and
``langs`` holds the per-language records. ``run_translate`` skips ``(page, lang)`` when the EN md5 equals ``md5`` and
``lang`` is in ``langs_done``.

The defect, in ``translate_docs.py`` up to 01c6f1ae4:

* once the analysis of a changed EN page succeeded, both execution paths (the parallel pipeline, ``--workers`` > 1,
  and the sequential loop) moved ``md5`` to the new EN and kept ``langs_done``. A language that then failed (a
  network error at Critique or Refine) or was never reached (a ``--lang`` subset, an interrupted run) stayed done for
  the new EN: its translation of the old EN was masked, and no later run offered it again;
* a failure replaced the language record with ``{"translated_at": now, "failed": True, ...}``: it read as a
  translation made at that moment;
* ``translate-stamp --lang it`` on a changed EN kept fr and es done for the new md5: masked as well;
* both paths read the source before the analysis but took ``md5`` from the file once the analysis came back, which
  takes minutes, or hours on a batch queue. An edit saved in between was recorded as the version translated, and was
  never offered for translation.

The fix sends every cache write through five pure transitions: ``_needs_translation``, ``_cache_mark_analyzed`` (a
changed source leaves no language done), ``_cache_mark_translated``, ``_cache_mark_failed`` (never done; keeps
``translated_at``; adds ``failed``, ``failed_at``, ``failure_reason`` and ``failed_models``) and ``_cache_stamp``
(keeps ``langs_done`` only for an unchanged source; clears the failure record of what it stamps). ``_read_source``
reads the source once and returns its text with the md5 of the same bytes, which ``_pipeline_analyze`` hands back
as ``source_md5``: the md5 recorded is the one of the text translated.

The behaviour tests run the real ``run_translate`` and ``run_stamp``, with arguments parsed by the real CLI parsers,
on a docs tree and a cache under ``tmp_path``. Only the LLM is faked, at the seams each path calls:
``_pipeline_analyze`` and ``_pipeline_worker`` (parallel), ``_analyze_source`` and ``_translate_one_lang``
(sequential). Like the real step, the fake writes the translation only on success and returns the same keys; a
failure returns no ``output_path`` and a ``failure_reason``; the fake analysis can save the EN while it runs.
``TestFakeSeams`` holds the fakes to the real signatures, result keys and source reading, and every run asserts that
it took the path under test. The plan of the next run is what ``translate --dry-run`` prints.

Red phase, in two steps. The new functions are reached only through fixtures and test bodies, never at module level,
so the module always collects.

* Against 01c6f1ae4, before the transitions:

  * red, the masking: the failed language (both paths), the languages left out by ``--lang`` or by an interruption,
    ``translate-stamp --lang it`` on a changed EN, the edit saved during the analysis (both paths, LF and CRLF);
  * red, the failure record survives a stamp: stamping every language;
  * red on ``source_md5``, the key the analysis task did not return yet: the fake-keys check;
  * green, and they must stay green: a failed ``--force`` retry of an unchanged page, plain success, stamping a new
    language of an unchanged page, the fake-parameters check;
  * error at setup: every ``TestCacheTransitions`` test.

* Against the transitions without ``_read_source``: red, the edit saved during the analysis (both paths, LF and
  CRLF), recorded as already translated; red, the fake-keys check, on ``source_md5``; everything else green.

Batch 25 translates ``CHANGELOG.md`` (the repository root) into ``CHANGELOG.<lang>.md`` beside it, through the same
seams and the same cache. ``changelog.py`` cuts it into units, the preamble and each chapter (``## [x.y.z] - date``),
and a unit longer than ``PIECE_THRESHOLD`` into pieces at its ``###`` and ``####`` lines: the intro is a piece of its
own, a part that is only its heading joins the next one, and a piece is keyed by its headings' words
(``CHANGELOG.md#<version>/<###>/<####>``), so an added section shifts no other key. The chapter line and the ``---``
that closes a unit are structure: copied, never sent to the model. Each piece's entry records, per language, its
position in the translated chapter (``langs.<lang>.index``), so a run finds the translated parts again after pieces
were inserted. Pinned here:

* ``changelog.py``, pure: where a chapter is cut, how a part is named, what is one piece and what is cut, the rule as
  a trailer, the English pieces assembled back into the English byte for byte, ``structure_change`` (what a translated
  piece must keep to take its place in its chapter) and ``locate`` (by recorded index, by position when nothing is
  recorded, a count mismatch named);
* ``run_translate``: the first run translates every piece into three files whose chapter lines are the English ones,
  in order (both ``--workers`` values); a second run does nothing; a changed piece is translated again alone and every
  other part, a reviewer's hand edits included, is kept byte for byte; an inserted section is translated alone; a
  language failing on a new piece leaves that chapter as it was (or absent) and the piece pending, the other languages
  written; a section removed or moved in the English is rebuilt in every translation with no model call; a new
  translation that no longer fits its piece (a heading added or dropped) or its chapter (a code fence left open) is
  refused, its chapter kept; ``--file CHANGELOG.md`` translates no page, no ``--file`` translates the pages and the
  CHANGELOG; ``--dry-run`` writes nothing and lists the pieces (or the files to rebuild);
* ``run_stamp``: ``--file CHANGELOG.md`` stamps each piece of a hand port with its position, and skips and names a
  chapter whose translated parts do not match its pieces (exit 1); with no ``--file`` it leaves the CHANGELOG alone.

Written against the new code, not red first; no test is red now. Three were red on it and named defects, fixed
since: ``part_ids`` read the headings inside fenced code, which ``cut_parts`` rightly skips
(``test_a_heading_inside_fenced_code_names_no_part``); with no piece left to translate, the run returned before it
rewrote the files, which kept a removed section (``test_a_section_removed_or_moved_…``); a new translation that lost
the heading its piece opens with was accepted, being one part alone, though in its chapter it joined the part before
it and made every later run translate the chapter again (``test_a_new_translation_that_drops_the_heading_…``). A new
translation that would not take its piece's place is now refused in two layers: piece by piece,
``changelog.structure_change`` (one part, opening with a heading exactly when the English piece does); chapter by
chapter, ``_changelog_misfits`` (the chapter its new texts would rebuild must still cut into its pieces: a fault at a
seam, such as a code fence left open, passes every piece and is caught there).

PURE: files under ``tmp_path`` only. ``DOCS_DIR``, ``HASH_FILE``, ``ENV_FILE`` and ``CONFIG_TOML`` point there, and so
do the CHANGELOG (``_changelog_source``; ``changelog.SOURCE``, its default, at a folder that does not exist, so a call
that forgets its source fails instead of reaching the repository's file) and the temporary folder its pieces are
written to while they are translated; the nav, the languages, the API key, the models and the model client are
stubbed. No network, no LLM, no DB, no server. The tracked cache, ``.env``, ``config.toml``, the docs and the
repository's ``CHANGELOG*.md`` are never opened or written: an autouse guard fails any test after which the tracked
cache or ``config.toml`` changed.
"""

import argparse
import ast
import dataclasses
import hashlib
import importlib
import inspect
import json
import re
import tempfile
import textwrap
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from types import ModuleType

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[3]
PIPELINE_DIR = PROJECT_ROOT / "mkdocs_src" / "aphra-pipeline"
TRACKED_CACHE = PIPELINE_DIR / ".translate-hashes.json"
TRACKED_CONFIG = PIPELINE_DIR / "config.toml"

PAGE = "user/cache-page.en.md"  # the page whose EN changes
OTHER = "user/other-page.en.md"  # an up-to-date neighbour that no run may plan or touch
LANGS = ("it", "fr", "es")  # the detected target languages, in CLI order
OLD_EN = "# Cache page\n\nFirst version of the page.\n"
NEW_EN = "# Cache page\n\nSecond version of the page, edited after its translations.\n"
EDITED_EN = "# Cache page\n\nThird version, saved by the author while the analysis was running.\n"
OTHER_EN = "# Other page\n\nNobody edits this page.\n"
EARLIER = "2020-01-01T00:00:00+00:00"  # when the seeded translations were written
FAILED_EARLIER = "2021-06-01T00:00:00+00:00"  # when a seeded failure happened
NOW = "2026-10-10T08:00:00+00:00"  # the clock the transition tests pass in
NETWORK_DOWN = "Critique connection error: [Errno 8] nodename nor servname provided, or not known"
FAILURE_KEYS = ("failed", "failed_at", "failure_reason", "failed_models")
TRANSITIONS = ("_needs_translation", "_cache_mark_analyzed", "_cache_mark_translated", "_cache_mark_failed", "_cache_stamp")
MODELS = {"analyzer": "fake/analyzer", "writer": "fake/writer", "searcher": "fake/searcher", "critiquer": "fake/critiquer"}

# `translate --dry-run`: "  • <cache key> → <lang>  (~N tok)" per planned pair, after "... = <N> translation(s)".
_PLAN_LINE = re.compile(r"^  • (?P<key>\S+) → (?P<lang>\S+)  \(", re.MULTILINE)
_PLAN_TOTAL = re.compile(r"= (?P<total>\d+) translation\(s\)")
# The CHANGELOG's half of it: the same "  • <piece key> → <lang>" lines, after "📋 CHANGELOG.md: <N> piece(s), <M> translation(s)";
# with nothing to translate but files left behind by the English structure, "📋 CHANGELOG.md: nothing to translate; <files> to rebuild".
_CHANGELOG_TOTAL = re.compile(r"📋 CHANGELOG\.md: (?P<pieces>\d+) piece\(s\), (?P<total>\d+) translation\(s\)")
_CHANGELOG_REBUILD = re.compile(r"📋 CHANGELOG\.md: nothing to translate; (?P<files>.+?) to rebuild")
CHANGELOG_UP_TO_DATE = "every piece is up to date, nothing to translate"
# `translate-stamp --file CHANGELOG.md`: "  📌 <piece key> → <lang>  (MD5 ...)" per stamped piece.
_STAMPED = re.compile(r"^  📌 (?P<key>\S+) → (?P<lang>\S+)  \(MD5 ", re.MULTILINE)
_NOT_STAMPED = re.compile(r"(?P<key>CHANGELOG\.md#\S+) → (?P<lang>\w+): (?P<parts>\d+) translated parts for (?P<pieces>\d+) pieces, not stamped")

# ---------------------------------------------------------------------------
# The CHANGELOG (R2 B25): a small one, shaped as the repository's
# ---------------------------------------------------------------------------
# Newest chapter first: [3.1.0] is open (being prepared), longer than THRESHOLD and so cut into five pieces; the
# preamble, [3.0.1] and [3.0.0] are one piece each. Blocks are separated by one blank line, a rule between two units.

THRESHOLD = 300  # changelog.PIECE_THRESHOLD in these tests, instead of writing 30,000 characters
RULE = "---"
OPEN = "3.1.0"
PREAMBLE_EN = "# Changelog\n\nAll notable changes to LibreFolio are documented in this file."
INTRO_LINE = "**Preparing v3.1.0.** These changes are in preparation and not released yet."
ADDED_LINE = "- A Tools catalogue with isolated computations and read-only diagnostics."
ADDED_SECTION = f"### ✨ Added\n\n- A support popup in the About page, with links to the project pages.\n{ADDED_LINE}"
SECURITY_LINE = "- Session cookies are rotated after every password change."
SECURITY_SECTION = f"#### 🔒 Security\n\n{SECURITY_LINE}"
DOC_HEADING = "#### 📚 Documentation"
DOC_LINE = "- The installation guide describes the Docker volumes again."
DOC_SECTION = f"{DOC_HEADING}\n\n{DOC_LINE}"
CHANGED_SECTION = "### 🔄 Changed\n\n- Charts load their history page by page instead of all at once."
OPEN_LINE = "## [3.1.0] - 2026-11-30"
OPEN_EN = "\n\n".join((OPEN_LINE, INTRO_LINE, ADDED_SECTION, "### 🐛 Fixed", SECURITY_SECTION, DOC_SECTION, CHANGED_SECTION))
PATCH_LINE = "- The import wizard keeps the broker selected after a page reload."
PATCH_BODY = f"### 🐛 Fixed\n\n{PATCH_LINE}"
PATCH_EN = f"## [3.0.1] - 2026-07-21\n\n{PATCH_BODY}"
FIRST_BODY = "First public release.\n\n### ✨ Added\n\n- Portfolio dashboard, broker report imports and exchange rates."
FIRST_EN = f"## [3.0.0] - 2026-07-20\n\n{FIRST_BODY}"
NEW_DOC_LINE = "- The upgrade notes list every step from 3.0 to 3.1."  # appended to Documentation by a later edit
NEW_SECURITY_LINE = "- Sign-in attempts are rate limited per address."  # appended to Security by a later edit
CHARTS_SECTION = "#### 📈 Charts\n\n- The value chart keeps its zoom after a refresh."  # inserted before Documentation

OPEN_PIECES = ("intro", "added", "fixed/security", "fixed/documentation", "changed")
CHANGELOG_KEYS = ("CHANGELOG.md#preamble", *(f"CHANGELOG.md#3.1.0/{piece}" for piece in OPEN_PIECES), "CHANGELOG.md#3.0.1", "CHANGELOG.md#3.0.0")
ALL_PIECE_PAIRS = sorted((key, lang) for key in CHANGELOG_KEYS for lang in LANGS)
DOC_KEY = "CHANGELOG.md#3.1.0/fixed/documentation"
SECURITY_KEY = "CHANGELOG.md#3.1.0/fixed/security"
CHARTS_KEY = "CHANGELOG.md#3.1.0/fixed/charts"
CHANGELOG_SEAMS = frozenset({"_analyze_source", "_translate_one_lang"})  # each piece, whatever --workers says: the threads are the run's own


def _changelog(*blocks: str) -> str:
    """A CHANGELOG as the repository writes it: the preamble, then the chapters newest first, a rule between two units."""
    return f"\n\n{RULE}\n\n".join(blocks) + "\n"


CHANGELOG_EN = _changelog(PREAMBLE_EN, OPEN_EN, PATCH_EN, FIRST_EN)


def _with_doc_line(text: str) -> str:
    """``text`` with one more line in the open chapter's Documentation section."""
    return text.replace(DOC_LINE, f"{DOC_LINE}\n{NEW_DOC_LINE}", 1)


def _with_security_line(text: str) -> str:
    """``text`` with one more line in the open chapter's Security section."""
    return text.replace(SECURITY_LINE, f"{SECURITY_LINE}\n{NEW_SECURITY_LINE}", 1)


def _with_charts(text: str) -> str:
    """``text`` with a new ``#### 📈 Charts`` section, before Documentation."""
    return text.replace(DOC_SECTION, f"{CHARTS_SECTION}\n\n{DOC_SECTION}", 1)


def _without_doc(text: str) -> str:
    """``text`` without the open chapter's Documentation section."""
    return text.replace(f"\n\n{DOC_SECTION}", "", 1)


def _with_changed_moved_up(text: str) -> str:
    """``text`` with the open chapter's Changed section moved before Fixed: the same pieces, the same keys, in another order."""
    return text.replace(OPEN_EN, "\n\n".join((OPEN_LINE, INTRO_LINE, ADDED_SECTION, CHANGED_SECTION, "### 🐛 Fixed", SECURITY_SECTION, DOC_SECTION)), 1)


def _md5(text: str) -> str:
    return hashlib.md5(text.encode("utf-8")).hexdigest()


def _translation(source_text: str, lang: str) -> str:
    """The fake writer's output: every prose line tagged with the language, the Markdown structure untouched."""
    return "\n".join(f"{line} ({lang})" if line and not line.startswith("#") else line for line in source_text.split("\n"))


def _translated_changelog(english: str, lang: str) -> str:
    """The ``CHANGELOG.<lang>.md`` the fake model gives for ``english``: every prose line tagged, every heading (the
    chapter lines with them), rule and blank line as in the English."""
    return "\n".join(line if line == RULE else _translation(line, lang) for line in english.split("\n"))


def _chapter_lines(text: str) -> list[str]:
    """The ``## [x.y.z] - date`` lines, in order: what the app finds the chapters of a CHANGELOG by."""
    return [line for line in text.split("\n") if line.startswith("## [")]


def _record(lang: str) -> dict:
    """A language record as a successful run wrote it, at ``EARLIER``."""
    return {
        "translated_at": EARLIER,
        "models": {"writer": "earlier/writer", "critiquer": "earlier/critiquer"},
        "critique": f"earlier critique ({lang})",
        "structural_diff": "",
        "structural_issues": 0,
        "elapsed_s": 12.5,
    }


def _failed(record: dict) -> dict:
    """``record`` after a failed attempt, as the fixed cache keeps it."""
    return {**record, "failed": True, "failed_at": FAILED_EARLIER, "failure_reason": NETWORK_DOWN, "failed_models": {"writer": "earlier/writer"}}


def _entry(source_text: str, langs_done: tuple[str, ...] = LANGS) -> dict:
    """A cache entry as a run that translated ``langs_done`` from ``source_text`` left it."""
    return {
        "md5": _md5(source_text),
        "langs_done": list(langs_done),
        "last_translated": EARLIER,
        "analysis": "earlier analysis",
        "analysis_model": "earlier/analyzer",
        "langs": {lang: _record(lang) for lang in langs_done},
    }


def _failure_keys(record: dict) -> list[str]:
    return [key for key in FAILURE_KEYS if key in record]


def _after_earlier(timestamp: str) -> bool:
    return datetime.fromisoformat(timestamp) > datetime.fromisoformat(EARLIER)


def _function_tree(function) -> ast.AST:
    return ast.parse(textwrap.dedent(inspect.getsource(function)))


def _is_name(node: ast.AST, name: str) -> bool:
    return isinstance(node, ast.Name) and node.id == name


def _result_keys(function) -> set[str]:
    """Keys of the ``result`` dict ``function`` builds: its ``result = {...}`` literal and every ``result["key"] = ...``."""
    keys: set[str] = set()
    for node in ast.walk(_function_tree(function)):
        if not isinstance(node, ast.Assign):
            continue
        for target in node.targets:
            if _is_name(target, "result") and isinstance(node.value, ast.Dict):
                keys.update(key.value for key in node.value.keys if isinstance(key, ast.Constant))
            elif isinstance(target, ast.Subscript) and _is_name(target.value, "result") and isinstance(target.slice, ast.Constant):
                keys.add(target.slice.value)
    return keys


def _returned_dict_keys(function) -> set[str]:
    """Keys of the dict literal ``function`` returns."""
    returns = [node.value for node in ast.walk(_function_tree(function)) if isinstance(node, ast.Return) and isinstance(node.value, ast.Dict)]
    return {key.value for value in returns for key in value.keys if isinstance(key, ast.Constant)}


# ---------------------------------------------------------------------------
# The fake LLM
# ---------------------------------------------------------------------------


class SimulatedInterrupt(BaseException):
    """Ctrl-C for the fakes: a BaseException, which ``run_translate``'s ``except Exception`` lets through exactly as it
    does KeyboardInterrupt, without pytest ever taking it for a real one."""


@dataclasses.dataclass(frozen=True)
class RunPath:
    workers: int
    seams: frozenset[str]


PARALLEL = RunPath(3, frozenset({"_pipeline_analyze", "_pipeline_worker"}))
SEQUENTIAL = RunPath(1, frozenset({"_analyze_source", "_translate_one_lang"}))
PATHS = [pytest.param(PARALLEL, id="parallel-workers3"), pytest.param(SEQUENTIAL, id="sequential-workers1")]


@dataclasses.dataclass
class FakeAphra:
    """The LLM at the four seams ``run_translate`` calls. A language in ``fail`` fails the way a network error at
    Critique does (when ``fail_only_on`` is set, only on the sources holding that line: one piece of the CHANGELOG); a
    language in ``interrupt`` raises ``SimulatedInterrupt``; any other language succeeds, its translation passed through
    ``restructure(text, lang)`` when set: a model that changes the Markdown structure. ``during_analysis`` runs while
    the analysis is in progress, after the source was read: the author saving the EN."""

    fail: dict[str, str] = dataclasses.field(default_factory=dict)
    interrupt: set[str] = dataclasses.field(default_factory=set)
    during_analysis: Callable[[], None] | None = None
    fail_only_on: str | None = None
    restructure: Callable[[str, str], str] | None = None
    seams: set[str] = dataclasses.field(default_factory=set)  # the seams the run called
    reached: list[str] = dataclasses.field(default_factory=list)  # the languages handed to the translate seam
    calls: list[tuple[str, str]] = dataclasses.field(default_factory=list)  # (source text, language) handed to it

    def reset(self, *, fail: dict[str, str] | None = None, interrupt=(), during_analysis: Callable[[], None] | None = None, fail_only_on: str | None = None, restructure: Callable[[str, str], str] | None = None) -> None:
        self.fail = dict(fail or {})
        self.interrupt = set(interrupt)
        self.during_analysis = during_analysis
        self.fail_only_on = fail_only_on
        self.restructure = restructure
        self.seams.clear()
        self.reached.clear()
        self.calls.clear()

    def _analyze(self, source_text: str) -> str:
        if self.during_analysis is not None:
            self.during_analysis()
        return f"analysis of {_md5(source_text)}"

    # Sequential path (workers == 1): run_translate reads the source, then calls the analysis

    def analyze_source(self, source_text, model_client, models):
        self.seams.add("_analyze_source")
        return "fake-workflow", {"writer": models["writer"]}, self._analyze(source_text)

    def translate_one_lang(self, source_text, source_path, target_lang, workflow, workflow_config, model_client, models, analysis, log_buf=None):
        self.seams.add("_translate_one_lang")
        return self._translate(source_text, source_path, target_lang, models)

    # Parallel path (workers > 1): the analysis task reads the source itself, once, as _read_source does

    def pipeline_analyze(self, source_path, cache_key, model_client, models, print_lock):
        self.seams.add("_pipeline_analyze")
        data = source_path.read_bytes()
        source_text = data.decode("utf-8").replace("\r\n", "\n").replace("\r", "\n")
        return {
            "workflow": "fake-workflow",
            "workflow_config": {"writer": models["writer"]},
            "analysis": self._analyze(source_text),
            "source_text": source_text,
            "source_md5": hashlib.md5(data).hexdigest(),  # of the bytes read, whatever the file holds by now
        }

    def pipeline_worker(self, cache_key, source_text, source_path, target_lang, workflow, workflow_config, model_client, models, analysis, log_buf, print_lock):
        self.seams.add("_pipeline_worker")
        result = self._translate(source_text, source_path, target_lang, models)
        result["elapsed_s"] = 0.1
        return result

    def _translate(self, source_text: str, source_path: Path, lang: str, models: dict) -> dict:
        """``_translate_one_lang``'s contract: the translation is written only on success; the same keys either way."""
        self.reached.append(lang)
        self.calls.append((source_text, lang))
        if lang in self.interrupt:
            raise SimulatedInterrupt(lang)
        result = {
            "output_path": None,
            "critique": "",
            "structural_diff": "",
            "structural_issues": 0,
            "models": {"writer": models["writer"], "critiquer": models["critiquer"]},
            "failure_reason": "",
        }
        if lang in self.fail and (self.fail_only_on is None or self.fail_only_on in source_text.split("\n")):
            result["failure_reason"] = self.fail[lang]
            return result
        output_path = source_path.parent / source_path.name.replace(".en.md", f".{lang}.md")
        translated = _translation(source_text, lang)
        output_path.write_text(self.restructure(translated, lang) if self.restructure else translated, encoding="utf-8")
        result.update(output_path=output_path, critique=f"fake critique ({lang})")
        return result


# ---------------------------------------------------------------------------
# The sandbox: translate_docs pointed at tmp_path
# ---------------------------------------------------------------------------


@dataclasses.dataclass
class Sandbox:
    """A docs tree, a hash cache and the CHANGELOG's place under ``tmp_path``, which ``translate_docs`` reads and writes
    instead of the repo."""

    td: ModuleType
    docs: Path
    hash_file: Path
    llm: FakeAphra
    capsys: pytest.CaptureFixture
    root: Path  # CHANGELOG.md and its translations sit here, as at the repository's root
    scratch: Path  # the temporary folder: the CHANGELOG's pieces are written here while they are translated

    def path(self, key: str = PAGE, lang: str = "en") -> Path:
        return self.docs / key.replace(".en.md", f".{lang}.md")

    def write_en(self, text: str, key: str = PAGE) -> None:
        self.path(key).write_bytes(text.encode("utf-8"))

    def translation(self, lang: str, key: str = PAGE) -> str:
        return self.path(key, lang).read_text(encoding="utf-8")

    def cache(self) -> dict:
        return json.loads(self.hash_file.read_text(encoding="utf-8"))

    def entry(self, key: str = PAGE) -> dict:
        return self.cache()[key]

    def seed_entry(self, entry: dict, key: str = PAGE) -> None:
        cache = self.cache()
        cache[key] = entry
        self.hash_file.write_text(json.dumps(cache, indent=2), encoding="utf-8")

    def translate(self, *argv: str) -> int:
        """``translate_docs.py translate ARGV``, parsed by the real parser."""
        return self.td.run_translate(self._parse(self.td._add_arguments, argv))

    def stamp(self, *argv: str) -> int:
        """``translate_docs.py stamp ARGV``, parsed by the real parser."""
        return self.td.run_stamp(self._parse(self.td._add_stamp_arguments, argv))

    def next_plan(self) -> list[tuple[str, str]]:
        """The (page, lang) pairs the next full run would translate, as ``translate --dry-run`` lists them (the
        CHANGELOG's pieces it lists after them are ``changelog_plan``'s)."""
        before = self.hash_file.read_bytes()
        self.capsys.readouterr()
        assert self.translate("--dry-run") == 0
        out = self.capsys.readouterr().out
        assert self.hash_file.read_bytes() == before, "a dry run wrote the cache"
        pairs = sorted((match["key"], match["lang"]) for match in _PLAN_LINE.finditer(out) if not match["key"].startswith("CHANGELOG.md#"))
        total = _PLAN_TOTAL.search(out)
        unreadable = f"barrier: the dry-run output changed shape, its plan cannot be read:\n{out}"
        assert total is not None or "Nothing to translate" in out, unreadable
        assert len(pairs) == (int(total["total"]) if total else 0), unreadable
        return pairs

    # The CHANGELOG

    def changelog_path(self, lang: str = "en") -> Path:
        return self.root / ("CHANGELOG.md" if lang == "en" else f"CHANGELOG.{lang}.md")

    def write_changelog(self, text: str, lang: str = "en") -> None:
        self.changelog_path(lang).write_bytes(text.encode("utf-8"))

    def changelog_translation(self, lang: str) -> str:
        return self.changelog_path(lang).read_bytes().decode("utf-8")

    def changelog_files(self) -> dict[str, bytes]:
        """``CHANGELOG.md`` and each ``CHANGELOG.<lang>.md`` there is, by name."""
        return {path.name: path.read_bytes() for path in sorted(self.root.glob("CHANGELOG*.md"))}

    def changelog_units(self) -> list:
        """The units of the sandbox's English CHANGELOG, as the pipeline cuts it."""
        return self.td.cl.read_english(self.changelog_path())

    def changelog_entries(self) -> dict:
        return {key: entry for key, entry in self.cache().items() if key.startswith("CHANGELOG.md#")}

    def requested(self) -> list[tuple[str, str]]:
        """What the runs handed to the translate seam since the last reset, as sorted (key, lang) pairs: a page by its
        cache key, a piece of the CHANGELOG by its key in the current English."""
        keys = {self.path(key).read_text(encoding="utf-8"): key for key in (PAGE, OTHER)}
        if self.changelog_path().exists():
            keys.update((piece.text, piece.key) for unit in self.changelog_units() for piece in unit.pieces)
        return sorted((keys.get(text, f"<neither a page nor a piece: {text[:40]!r}>"), lang) for text, lang in self.llm.calls)

    def changelog_dry_run(self) -> tuple[list[tuple[str, str]], list[str]]:
        """What the next run would do, as ``translate --file CHANGELOG.md --dry-run`` lists it: the (piece, lang) pairs to
        translate, and the translations to rebuild with no model call (a section removed or moved in the English)."""
        before = (self.hash_file.read_bytes(), self.changelog_files())
        self.capsys.readouterr()
        assert self.translate("--file", "CHANGELOG.md", "--dry-run") == 0
        out = self.capsys.readouterr().out
        assert (self.hash_file.read_bytes(), self.changelog_files()) == before, "a dry run wrote the cache or a translation"
        pairs = sorted((match["key"], match["lang"]) for match in _PLAN_LINE.finditer(out))
        total, rebuild = _CHANGELOG_TOTAL.search(out), _CHANGELOG_REBUILD.search(out)
        unreadable = f"barrier: the dry-run output changed shape, its plan cannot be read:\n{out}"
        assert total is not None or rebuild is not None or CHANGELOG_UP_TO_DATE in out, unreadable
        assert len(pairs) == (int(total["total"]) if total else 0), unreadable
        assert all(key.startswith("CHANGELOG.md#") for key, _ in pairs), unreadable
        return pairs, sorted(rebuild["files"].split(", ")) if rebuild else []

    def changelog_plan(self) -> list[tuple[str, str]]:
        """The (piece, lang) pairs the next run would translate."""
        return self.changelog_dry_run()[0]

    @staticmethod
    def _parse(add_arguments, argv) -> argparse.Namespace:
        parser = argparse.ArgumentParser()
        add_arguments(parser)
        return parser.parse_args(list(argv))


@pytest.fixture(scope="module")
def translate_docs() -> ModuleType:
    """The pipeline script, imported by bare name as dev.py loads it (it imports its sibling ``code_blocks``)."""
    with pytest.MonkeyPatch.context() as mp:
        mp.syspath_prepend(str(PIPELINE_DIR))
        module = importlib.import_module("translate_docs")
    assert hasattr(module, "run_translate") and hasattr(module, "run_stamp"), f"not the pipeline script: {module.__file__}"
    return module


@pytest.fixture(scope="module")
def changelog(translate_docs) -> ModuleType:
    """``changelog.py``, the very module the pipeline imported: what a test patches on it, the pipeline sees."""
    module = translate_docs.cl
    assert Path(module.__file__).resolve().parent == PIPELINE_DIR and hasattr(module, "cut_parts"), f"not the pipeline module: {module.__file__}"
    return module


@pytest.fixture
def transitions(translate_docs) -> ModuleType:
    """``translate_docs``, once it has the five cache transitions. Before the fix it has none: each test using this errors at setup."""
    missing = [name for name in TRANSITIONS if not hasattr(translate_docs, name)]
    if missing:
        pytest.fail(f"translate_docs.py has no {', '.join(missing)}: the cache transitions are not implemented", pytrace=False)
    return translate_docs


def _tracked_state() -> tuple:
    cache = TRACKED_CACHE.stat() if TRACKED_CACHE.exists() else None
    return ((cache.st_size, cache.st_mtime_ns) if cache else None), TRACKED_CONFIG.exists()


@pytest.fixture(autouse=True)
def tracked_files_untouched():
    """Every write belongs in tmp_path: a test after which the tracked cache or config.toml changed fails at teardown."""
    before = _tracked_state()
    yield
    assert _tracked_state() == before, "the tracked .translate-hashes.json or config.toml changed during the test: a translate_docs write escaped tmp_path"


@pytest.fixture
def sandbox(translate_docs, tmp_path, monkeypatch, capsys) -> Sandbox:
    """Both pages translated into every language from their current EN, the cache in step with them. The CHANGELOG's
    place is ``tmp_path``, empty: a test that writes ``CHANGELOG.md`` there brings it in."""
    td = translate_docs
    root = tmp_path.resolve()
    docs = root / "docs"
    (docs / "user").mkdir(parents=True)
    aphra = root / "aphra-pipeline"
    aphra.mkdir()
    scratch = root / "tmp"
    scratch.mkdir()
    llm = FakeAphra()
    redirections = {
        "DOCS_DIR": docs,
        "HASH_FILE": aphra / ".translate-hashes.json",
        "ENV_FILE": aphra / ".env",  # absent: every .env lookup takes its default
        "CONFIG_TOML": aphra / "config.toml",
        "DEFAULT_RATE_LIMIT_RETRIES": td.DEFAULT_RATE_LIMIT_RETRIES,  # run_translate rebinds it from --rate-limit-retries
        "get_translatable_files": lambda: [PAGE, OTHER],
        "_detect_target_languages": lambda: list(LANGS),
        "_load_api_key": lambda: "sk-fake",
        "_load_models": lambda: dict(MODELS),
        "_create_model_client": lambda api_key, models: object(),
        "_generate_config_toml": lambda api_key, models: None,
        "_cleanup_config_toml": lambda: None,
        "_analyze_source": llm.analyze_source,
        "_translate_one_lang": llm.translate_one_lang,
        "_pipeline_analyze": llm.pipeline_analyze,
        "_pipeline_worker": llm.pipeline_worker,
        "_changelog_source": lambda: root / "CHANGELOG.md",  # absent unless a test writes it: then the pages alone run
    }
    for name, value in redirections.items():
        monkeypatch.setattr(td, name, value)  # raising: a renamed seam fails here, not silently in a real call
    monkeypatch.setattr(td.cl, "SOURCE", root / "not-the-repository" / "CHANGELOG.md")  # changelog.py's default, for a call that forgets its source
    monkeypatch.setattr(tempfile, "tempdir", str(scratch))
    box = Sandbox(td, docs, aphra / ".translate-hashes.json", llm, capsys, root, scratch)
    cache = {}
    for key, text in ((PAGE, OLD_EN), (OTHER, OTHER_EN)):
        box.write_en(text, key)
        for lang in LANGS:
            box.path(key, lang).write_text(_translation(text, lang), encoding="utf-8")
        cache[key] = _entry(text)
    box.hash_file.write_text(json.dumps(cache, indent=2), encoding="utf-8")
    return box


@pytest.fixture
def changelog_sandbox(sandbox, changelog, monkeypatch) -> Sandbox:
    """``sandbox`` with ``CHANGELOG_EN`` at its root, translated into no language yet, and ``PIECE_THRESHOLD`` at
    ``THRESHOLD``: the open chapter is cut into its pieces, every other unit is one piece."""
    monkeypatch.setattr(changelog, "PIECE_THRESHOLD", THRESHOLD)
    sandbox.write_changelog(CHANGELOG_EN)
    assert sandbox.td._changelog_source() == sandbox.changelog_path(), "barrier: the pipeline reads the sandbox's CHANGELOG"
    assert [unit.name for unit in sandbox.changelog_units() if unit.split] == [OPEN], "barrier: the threshold cuts the open chapter alone"
    return sandbox


# ---------------------------------------------------------------------------
# The fakes stand where the real seams stand
# ---------------------------------------------------------------------------


class TestFakeSeams:
    @pytest.mark.parametrize(
        ("seam", "fake"),
        [
            pytest.param("_analyze_source", "analyze_source", id="analyze-source"),
            pytest.param("_translate_one_lang", "translate_one_lang", id="translate-one-lang"),
            pytest.param("_pipeline_analyze", "pipeline_analyze", id="pipeline-analyze"),
            pytest.param("_pipeline_worker", "pipeline_worker", id="pipeline-worker"),
        ],
    )
    def test_each_fake_takes_the_parameters_of_the_real_seam(self, translate_docs, seam, fake):
        """run_translate calls the seams by keyword: a renamed parameter would turn every fake call into a failure."""
        real = list(inspect.signature(getattr(translate_docs, seam)).parameters)
        assert list(inspect.signature(getattr(FakeAphra(), fake)).parameters) == real, f"{seam} changed its parameters: update FakeAphra.{fake}"

    def test_the_fakes_return_the_keys_of_the_real_seams(self, translate_docs, tmp_path):
        """A fake answer the run reads differently from a real one would let the cache tests pass for the wrong reason."""
        td = translate_docs
        translated, added_by_worker, analyzed = _result_keys(td._translate_one_lang), _result_keys(td._pipeline_worker), _returned_dict_keys(td._pipeline_analyze)
        assert translated and added_by_worker and analyzed, "barrier: the result dicts moved, update _result_keys/_returned_dict_keys"
        source = tmp_path / "page.en.md"
        source.write_bytes(OLD_EN.replace("\n", "\r\n").encode("utf-8"))  # CRLF: the analysis task normalises the text, not the md5
        fake = FakeAphra(fail={"fr": NETWORK_DOWN})
        call = {"source_text": OLD_EN, "source_path": source, "workflow": None, "workflow_config": {}, "model_client": None, "models": MODELS, "analysis": ""}
        ok = fake.translate_one_lang(target_lang="it", log_buf=None, **call)
        failed = fake.translate_one_lang(target_lang="fr", log_buf=None, **call)
        worker = fake.pipeline_worker(cache_key="page.en.md", target_lang="es", log_buf=[], print_lock=None, **call)
        analysis = fake.pipeline_analyze(source_path=source, cache_key="page.en.md", model_client=None, models=MODELS, print_lock=None)
        assert {"success": set(ok), "failure": set(failed), "pipeline worker": set(worker), "pipeline analyze": set(analysis)} == {
            "success": translated,
            "failure": translated,
            "pipeline worker": translated | added_by_worker,
            "pipeline analyze": analyzed,
        }
        assert ok["output_path"] == source.with_name("page.it.md")
        assert ok["output_path"].read_text(encoding="utf-8") == _translation(OLD_EN, "it")
        assert (failed["output_path"], failed["failure_reason"]) == (None, NETWORK_DOWN)
        assert not source.with_name("page.fr.md").exists(), "a failed translation writes no file"
        read_once = (OLD_EN, hashlib.md5(source.read_bytes()).hexdigest())  # the text with LF, the md5 of the CRLF bytes
        assert td._read_source(source) == read_once, "barrier: _read_source changed its contract, update FakeAphra.pipeline_analyze"
        assert (analysis["source_text"], analysis["source_md5"]) == read_once


# ---------------------------------------------------------------------------
# run_translate
# ---------------------------------------------------------------------------


class TestRunTranslate:
    @pytest.mark.parametrize("path", PATHS)
    def test_a_language_that_fails_after_the_en_changed_is_offered_again(self, sandbox, path):
        """The EN changed; it and es succeed, fr fails at Critique. The fr file still translates the old EN, so fr must
        not be done for the new one, its record must keep the old translated_at, and the retry heals it."""
        sandbox.write_en(NEW_EN)
        sandbox.llm.reset(fail={"fr": NETWORK_DOWN})
        assert sandbox.translate("--workers", str(path.workers)) == 1, "a failed language fails the run"
        assert sandbox.llm.seams == path.seams, "barrier: the run did not take the path under test"
        assert sorted(sandbox.llm.reached) == sorted(LANGS)
        assert [sandbox.translation(lang) for lang in LANGS] == [_translation(NEW_EN, "it"), _translation(OLD_EN, "fr"), _translation(NEW_EN, "es")]
        entry = sandbox.entry()
        fr = entry["langs"]["fr"]
        assert {
            "md5": entry["md5"],
            "langs_done": sorted(entry["langs_done"]),
            "fr.failed": fr.get("failed"),
            "fr.failure_reason": fr.get("failure_reason"),
            "fr.translated_at": fr.get("translated_at"),
            "next dry run": sandbox.next_plan(),
        } == {
            "md5": _md5(NEW_EN),
            "langs_done": ["es", "it"],
            "fr.failed": True,
            "fr.failure_reason": NETWORK_DOWN,
            "fr.translated_at": EARLIER,  # the fr file on disk is still the one written then
            "next dry run": [(PAGE, "fr")],
        }

        sandbox.llm.reset()
        assert sandbox.translate("--workers", str(path.workers)) == 0
        assert sandbox.llm.reached == ["fr"], "the retry translates fr alone"
        assert sandbox.translation("fr") == _translation(NEW_EN, "fr")
        entry = sandbox.entry()
        assert sorted(entry["langs_done"]) == sorted(LANGS)
        assert _failure_keys(entry["langs"]["fr"]) == [], "a success replaces the failure record"
        assert _after_earlier(entry["langs"]["fr"]["translated_at"])
        assert sandbox.next_plan() == []

    @pytest.mark.parametrize(
        ("path", "argv", "interrupt", "done", "pending"),
        [
            pytest.param(PARALLEL, ("--lang", "it"), (), ["it"], ["es", "fr"], id="lang-subset-parallel"),
            pytest.param(SEQUENTIAL, ("--lang", "it"), (), ["it"], ["es", "fr"], id="lang-subset-sequential"),
            pytest.param(SEQUENTIAL, (), ("fr",), ["it"], ["es", "fr"], id="interrupted-at-fr-sequential"),
            pytest.param(PARALLEL, (), LANGS, [], ["es", "fr", "it"], id="interrupted-in-flight-parallel"),
        ],
    )
    def test_languages_not_reached_after_the_en_changed_stay_pending(self, sandbox, path, argv, interrupt, done, pending):
        """The EN changed and the run translated only some languages: a ``--lang`` subset, or a run cut short (Ctrl-C
        at fr; in the pipeline, Ctrl-C while every translation was in flight). The others still translate the old EN."""
        sandbox.write_en(NEW_EN)
        sandbox.llm.reset(interrupt=interrupt)
        argv = ("--workers", str(path.workers), *argv)
        if interrupt:
            with pytest.raises(SimulatedInterrupt):
                sandbox.translate(*argv)
        else:
            assert sandbox.translate(*argv) == 0
        assert sandbox.llm.seams == path.seams, "barrier: the run did not take the path under test"
        assert {lang: sandbox.translation(lang) for lang in done + pending} == {
            **{lang: _translation(NEW_EN, lang) for lang in done},
            **{lang: _translation(OLD_EN, lang) for lang in pending},
        }
        entry = sandbox.entry()
        assert {"md5": entry["md5"], "langs_done": sorted(entry["langs_done"]), "next dry run": sandbox.next_plan()} == {
            "md5": _md5(NEW_EN),
            "langs_done": done,
            "next dry run": [(PAGE, lang) for lang in pending],
        }

    @pytest.mark.parametrize(
        ("path", "newline"),
        [
            pytest.param(PARALLEL, "\n", id="parallel-workers3-lf"),
            pytest.param(PARALLEL, "\r\n", id="parallel-workers3-crlf"),
            pytest.param(SEQUENTIAL, "\n", id="sequential-workers1-lf"),
            pytest.param(SEQUENTIAL, "\r\n", id="sequential-workers1-crlf"),
        ],
    )
    def test_an_edit_saved_while_the_analysis_runs_is_offered_by_the_next_run(self, sandbox, path, newline):
        """The author saves the EN again while the analysis runs (hours, on a batch queue). The run translates the text
        it read, so the cache must record the md5 of the file as it was read, and the next run must offer every language
        of the page again. With CRLF the text is normalised and the md5 is still the one of the bytes read."""
        analyzed, edited = NEW_EN.replace("\n", newline), EDITED_EN.replace("\n", newline)
        sandbox.write_en(analyzed)
        assert (b"\r\n" in sandbox.path().read_bytes()) is (newline == "\r\n"), "barrier: the EN does not carry the newlines under test"
        as_read = sandbox.td._file_md5(sandbox.path())
        version = {as_read: "the EN as read", _md5(edited): "the EN saved during the analysis"}
        sandbox.llm.reset(during_analysis=lambda: sandbox.write_en(edited))
        assert sandbox.translate("--workers", str(path.workers)) == 0
        assert sandbox.llm.seams == path.seams, "barrier: the run did not take the path under test"
        assert sandbox.path().read_bytes() == edited.encode("utf-8"), "barrier: the edit did not land during the run"
        assert [sandbox.translation(lang) for lang in LANGS] == [_translation(NEW_EN, lang) for lang in LANGS], "the run translates the text it read"
        entry = sandbox.entry()
        assert {"md5": version.get(entry["md5"], entry["md5"]), "langs_done": sorted(entry["langs_done"]), "next dry run": sandbox.next_plan()} == {
            "md5": "the EN as read",
            "langs_done": sorted(LANGS),
            "next dry run": [(PAGE, lang) for lang in sorted(LANGS)],
        }

    @pytest.mark.parametrize("path", PATHS)
    def test_a_failed_forced_retry_of_an_unchanged_en_keeps_the_language_done(self, sandbox, path):
        """The EN did not change and ``--file PAGE --lang fr --force`` fails. The fr file was not touched and still
        translates this EN: fr stays done. Green before the fix; it guards the fix against reopening too much."""
        sandbox.llm.reset(fail={"fr": NETWORK_DOWN})
        assert sandbox.translate("--workers", str(path.workers), "--file", str(sandbox.path()), "--lang", "fr", "--force") == 1
        assert sandbox.llm.seams == path.seams, "barrier: the run did not take the path under test"
        assert sandbox.llm.reached == ["fr"]
        assert sandbox.translation("fr") == _translation(OLD_EN, "fr")
        entry = sandbox.entry()
        assert {
            "md5": entry["md5"],
            "langs_done": sorted(entry["langs_done"]),
            "fr.failed": entry["langs"]["fr"].get("failed"),
            "next dry run": sandbox.next_plan(),
        } == {"md5": _md5(OLD_EN), "langs_done": sorted(LANGS), "fr.failed": True, "next dry run": []}

    @pytest.mark.parametrize("path", PATHS)
    def test_a_successful_run_marks_every_language_done_for_the_new_en(self, sandbox, path):
        """Plain success after an EN edit: every language done for the new md5, each with a fresh translated_at."""
        sandbox.write_en(NEW_EN)
        other = sandbox.entry(OTHER)
        assert sandbox.translate("--workers", str(path.workers)) == 0
        assert sandbox.llm.seams == path.seams, "barrier: the run did not take the path under test"
        assert sorted(sandbox.llm.reached) == sorted(LANGS)
        assert [sandbox.translation(lang) for lang in LANGS] == [_translation(NEW_EN, lang) for lang in LANGS]
        entry = sandbox.entry()
        assert {
            "md5": entry["md5"],
            "langs_done": sorted(entry["langs_done"]),
            "translated_at written": {lang: _after_earlier(entry["langs"][lang]["translated_at"]) for lang in LANGS},
            "failure keys": {lang: _failure_keys(entry["langs"][lang]) for lang in LANGS},
            "next dry run": sandbox.next_plan(),
        } == {
            "md5": _md5(NEW_EN),
            "langs_done": sorted(LANGS),
            "translated_at written": dict.fromkeys(LANGS, True),
            "failure keys": {lang: [] for lang in LANGS},
            "next dry run": [],
        }
        assert sandbox.entry(OTHER) == other, "the run touched a page it did not plan"


# ---------------------------------------------------------------------------
# run_stamp
# ---------------------------------------------------------------------------


class TestRunStamp:
    def test_stamping_one_language_of_a_changed_en_leaves_the_others_pending(self, sandbox):
        """``translate-stamp --lang it`` after the EN changed: it is done for the new EN; fr and es still translate the old one."""
        sandbox.write_en(NEW_EN)
        assert sandbox.stamp("--lang", "it") == 0
        entry = sandbox.entry()
        assert {"md5": entry["md5"], "langs_done": entry["langs_done"], "next dry run": sandbox.next_plan()} == {
            "md5": _md5(NEW_EN),
            "langs_done": ["it"],
            "next dry run": [(PAGE, "es"), (PAGE, "fr")],
        }

    def test_stamping_every_language_marks_all_done_and_clears_the_failure_records(self, sandbox):
        """The EN changed and fr carries a failure record: stamping every language makes all of them done and leaves
        no failure record on any stamped language."""
        failed = _entry(OLD_EN)
        failed["langs"]["fr"] = _failed(_record("fr"))
        sandbox.seed_entry(failed)
        sandbox.write_en(NEW_EN)
        assert sandbox.stamp() == 0
        entry = sandbox.entry()
        assert {
            "md5": entry["md5"],
            "langs_done": sorted(entry["langs_done"]),
            "failure keys": {lang: _failure_keys(entry["langs"][lang]) for lang in LANGS},
            "stamped by": {lang: entry["langs"][lang].get("stamped_by") for lang in LANGS},
            "next dry run": sandbox.next_plan(),
        } == {
            "md5": _md5(NEW_EN),
            "langs_done": sorted(LANGS),
            "failure keys": {lang: [] for lang in LANGS},
            "stamped by": dict.fromkeys(LANGS, "translate-stamp"),
            "next dry run": [],
        }

    def test_stamping_a_new_language_of_an_unchanged_en_keeps_the_languages_done(self, sandbox):
        """The EN did not change and es was never recorded (its file is hand-made): stamping es keeps it and fr done."""
        sandbox.seed_entry(_entry(OLD_EN, langs_done=("it", "fr")))
        assert sandbox.stamp("--lang", "es") == 0
        entry = sandbox.entry()
        assert {"md5": entry["md5"], "langs_done": sorted(entry["langs_done"]), "next dry run": sandbox.next_plan()} == {
            "md5": _md5(OLD_EN),
            "langs_done": sorted(LANGS),
            "next dry run": [],
        }


# ---------------------------------------------------------------------------
# The five transitions, directly
# ---------------------------------------------------------------------------


class TestCacheTransitions:
    @pytest.mark.parametrize(
        ("entry", "source", "lang", "force", "needed"),
        [
            pytest.param(None, OLD_EN, "it", False, True, id="no-entry"),
            pytest.param({}, OLD_EN, "it", False, True, id="empty-entry"),
            pytest.param(_entry(OLD_EN), OLD_EN, "it", False, False, id="done-from-this-source"),
            pytest.param(_entry(OLD_EN), NEW_EN, "it", False, True, id="done-from-another-source"),
            pytest.param(_entry(OLD_EN, langs_done=("it",)), OLD_EN, "fr", False, True, id="not-done"),
            pytest.param(_entry(OLD_EN), OLD_EN, "it", True, True, id="forced"),
        ],
    )
    def test_needs_translation_skips_only_a_language_done_from_this_source(self, transitions, entry, source, lang, force, needed):
        assert transitions._needs_translation(entry, _md5(source), lang, force) is needed

    @pytest.mark.parametrize(
        ("analyzed_before", "done_after"),
        [
            pytest.param(OLD_EN, [], id="source-changed"),
            pytest.param(NEW_EN, sorted(LANGS), id="same-source"),
            pytest.param(None, [], id="first-analysis"),
        ],
    )
    def test_mark_analyzed_keeps_languages_done_only_for_the_same_source(self, transitions, analyzed_before, done_after):
        hashes = {} if analyzed_before is None else {PAGE: _entry(analyzed_before)}
        records = {} if analyzed_before is None else {lang: _record(lang) for lang in LANGS}
        transitions._cache_mark_analyzed(hashes, PAGE, _md5(NEW_EN), "new analysis", "fake/analyzer")
        entry = hashes[PAGE]
        assert {
            "md5": entry["md5"],
            "langs_done": sorted(entry["langs_done"]),
            "analysis": (entry["analysis"], entry["analysis_model"]),
            "langs": entry["langs"],
        } == {
            "md5": _md5(NEW_EN),
            "langs_done": done_after,
            "analysis": ("new analysis", "fake/analyzer"),
            "langs": records,  # the records stay: they describe the translations on disk
        }

    def test_mark_translated_records_the_language_once_and_replaces_its_failure_record(self, transitions):
        hashes = {PAGE: _entry(NEW_EN, langs_done=("it",))}
        hashes[PAGE]["langs"]["fr"] = _failed(_record("fr"))
        info = {"models": {"writer": "fake/writer", "critiquer": "fake/critiquer"}, "critique": "fine", "structural_diff": "", "structural_issues": 0, "elapsed_s": 3.0}
        for _ in range(2):
            transitions._cache_mark_translated(hashes, PAGE, "fr", info, NOW)
        entry = hashes[PAGE]
        assert {"langs_done": sorted(entry["langs_done"]), "last_translated": entry["last_translated"], "fr": entry["langs"]["fr"]} == {
            "langs_done": ["fr", "it"],
            "last_translated": NOW,
            "fr": {"translated_at": NOW, **info},
        }

    @pytest.mark.parametrize(
        ("langs_done", "translated_before"),
        [
            pytest.param(("it", "es"), True, id="pending-after-a-source-change"),
            pytest.param(LANGS, True, id="done-from-this-source"),
            pytest.param(("it", "es"), False, id="never-translated"),
        ],
    )
    def test_mark_failed_never_makes_a_language_done_and_keeps_its_last_translation(self, transitions, langs_done, translated_before):
        hashes = {PAGE: _entry(NEW_EN, langs_done=langs_done)}
        hashes[PAGE]["langs"].pop("fr", None)
        if translated_before:
            hashes[PAGE]["langs"]["fr"] = _record("fr")
        models = {"writer": "fake/writer", "critiquer": "fake/critiquer"}
        transitions._cache_mark_failed(hashes, PAGE, "fr", NETWORK_DOWN, models, NOW)
        before = _record("fr") if translated_before else {}
        assert {"langs_done": sorted(hashes[PAGE]["langs_done"]), "fr": hashes[PAGE]["langs"]["fr"]} == {
            "langs_done": sorted(langs_done),
            "fr": {**before, "failed": True, "failed_at": NOW, "failure_reason": NETWORK_DOWN, "failed_models": models},
        }

    @pytest.mark.parametrize(
        ("stamped_source", "done_after"),
        [
            pytest.param(OLD_EN, sorted(LANGS), id="same-source-keeps-the-others"),
            pytest.param(NEW_EN, ["it"], id="changed-source-reopens-the-others"),
        ],
    )
    def test_stamp_keeps_the_other_languages_only_for_the_same_source(self, transitions, stamped_source, done_after):
        stamped = transitions._cache_stamp(_entry(OLD_EN), _md5(stamped_source), ["it"], NOW)
        it = stamped["langs"]["it"]
        assert {"md5": stamped["md5"], "langs_done": sorted(stamped["langs_done"]), "it stamped": (it.get("stamped_at"), it.get("stamped_by"))} == {
            "md5": _md5(stamped_source),
            "langs_done": done_after,
            "it stamped": (NOW, "translate-stamp"),
        }

    def test_stamp_clears_the_failure_record_of_the_stamped_languages_only(self, transitions):
        entry = _entry(OLD_EN, langs_done=("it",))
        entry["langs"].update(fr=_failed(_record("fr")), es=_failed(_record("es")))
        stamped = transitions._cache_stamp(entry, _md5(OLD_EN), ["fr"], NOW)
        assert {
            "langs_done": sorted(stamped["langs_done"]),
            "fr failure keys": _failure_keys(stamped["langs"]["fr"]),
            "es failure keys": _failure_keys(stamped["langs"]["es"]),
            "fr translated_at": stamped["langs"]["fr"].get("translated_at"),
        } == {
            "langs_done": ["fr", "it"],
            "fr failure keys": [],
            "es failure keys": list(FAILURE_KEYS),  # es was not stamped: still pending, its failure still on record
            "fr translated_at": EARLIER,
        }


# ---------------------------------------------------------------------------
# The CHANGELOG (R2 B25): changelog.py, pure
# ---------------------------------------------------------------------------

# Code that shows a heading: the fenced `### Example` is no heading, the `####` after the fence is one.
FENCED_BODY = "### ✨ Added\n\n- Write a release note as:\n\n```markdown\n### Example\n```\n\n#### 🧩 Providers\n\n- A new provider."


def _open_unit(changelog: ModuleType, english: str):
    """The open chapter's unit in ``english``, cut as the pipeline cuts it."""
    return next(unit for unit in changelog.english(english) if unit.name == OPEN)


def _indexed(changelog: ModuleType, english: str, lang: str, *, reverse: bool = False) -> dict:
    """The entries of the open chapter's pieces as a run that translated ``english`` into ``lang`` left them: done, each
    at its position in the translated chapter (counted from the end with ``reverse``: a record that matches nothing)."""
    pieces = _open_unit(changelog, english).pieces
    return {piece.key: {"md5": _md5(piece.text), "langs_done": [lang], "langs": {lang: {"translated_at": EARLIER, "index": len(pieces) - 1 - index if reverse else index}}} for index, piece in enumerate(pieces)}


class TestChangelogPieces:
    @pytest.mark.parametrize(
        ("body", "parts"),
        [
            pytest.param("Intro of the chapter.\n\n### ✨ Added\n\n- One thing.", ["Intro of the chapter.", "### ✨ Added\n\n- One thing."], id="the-intro-is-a-part-of-its-own"),
            pytest.param(
                "### 🐛 Fixed\n\n#### 🔒 Security\n\n- A fix.\n\n#### 📚 Documentation\n\n- A page.",
                ["### 🐛 Fixed\n\n#### 🔒 Security\n\n- A fix.", "#### 📚 Documentation\n\n- A page."],
                id="a-heading-alone-joins-the-next-part",
            ),
            pytest.param("### 🐛 Fixed\n\n#### 🔒 Security\n\n#### 🧩 Providers\n\n- A fix.", ["### 🐛 Fixed\n\n#### 🔒 Security\n\n#### 🧩 Providers\n\n- A fix."], id="headings-alone-in-a-row-join-the-next-part"),
            pytest.param("### ✨ Added\n\n- One thing.\n\n### ⚠️ Breaking changes", ["### ✨ Added\n\n- One thing.\n\n### ⚠️ Breaking changes"], id="a-last-heading-alone-stays-with-the-part-before-it"),
            pytest.param(
                "### ✨ Added\n\n- Write a note as:\n\n```markdown\n### Example\n#### Nested\n```\n\n~~~text\n### Also code\n~~~\n\n- Another thing.",
                ["### ✨ Added\n\n- Write a note as:\n\n```markdown\n### Example\n#### Nested\n```\n\n~~~text\n### Also code\n~~~\n\n- Another thing."],
                id="headings-in-fenced-code-are-not-cuts",
            ),
            pytest.param("### ✨ Added\n\n- One thing.\n\n##### A fifth level\n\n- A detail.", ["### ✨ Added\n\n- One thing.\n\n##### A fifth level\n\n- A detail."], id="a-fifth-level-heading-is-not-a-cut"),
            pytest.param("A paragraph.\n\n- A list.", ["A paragraph.\n\n- A list."], id="no-heading-one-part"),
        ],
    )
    def test_a_long_chapter_is_cut_at_its_third_and_fourth_level_headings_outside_code(self, changelog, body, parts):
        assert "\n\n".join(parts) == body, "barrier: the expected parts hold every line of the body"
        assert changelog.cut_parts(body) == parts

    @pytest.mark.parametrize(
        ("parts", "ids"),
        [
            pytest.param(
                ["Intro.", "### ✨ Added\n\n- a", "### 🐛 Fixed\n\n#### 🔒 Security\n\n- s", "#### 📚 Documentation\n\n- d", "### 🔄 Changed\n\n- c", "#### 💰 Purchase cost and P&L\n\n- p"],
                ["intro", "added", "fixed/security", "fixed/documentation", "changed", "changed/purchase-cost-and-p-l"],
                id="the-third-level-is-carried-into-the-fourth",
            ),
            pytest.param(
                ["### 🐛 Fixed\n\n#### 📈 Borsa Italiana — non-XMIL markets (EuroTLX) + OHLC integrity (2026-09-04)\n\n- a", "#### 📱 Sign-in, language & small_screens\n\n- b", "### ⚠️ Breaking changes\n\n- c"],
                ["fixed/borsa-italiana-non-xmil-markets-eurotlx-ohlc-integrity-2026-09-04", "fixed/sign-in-language-small-screens", "breaking-changes"],
                id="emoji-and-punctuation-are-dropped",
            ),
            pytest.param(
                ["### 🐛 Fixed\n\n#### Earlier in this cycle\n\n- a", "#### Earlier in this cycle\n\n- b", "#### Earlier in this cycle\n\n- c", "### 🔄 Changed\n\n#### Earlier in this cycle\n\n- d"],
                ["fixed/earlier-in-this-cycle", "fixed/earlier-in-this-cycle-2", "fixed/earlier-in-this-cycle-3", "changed/earlier-in-this-cycle"],
                id="a-repeated-id-is-numbered-from-2",
            ),
            pytest.param(["#### 🔒 Security\n\n- s"], ["security"], id="a-fourth-level-before-any-third"),
        ],
    )
    def test_a_part_is_named_by_the_words_of_its_headings(self, changelog, parts, ids):
        assert changelog.part_ids(parts) == ids

    def test_a_heading_inside_fenced_code_names_no_part(self, changelog):
        """``cut_parts`` reads only the headings outside fenced code; a part's name must come from the same headings, or
        a fenced ``### Example`` renames its part and every ``####`` after it."""
        parts = changelog.cut_parts(FENCED_BODY)
        assert parts == [FENCED_BODY.split("\n\n#### ")[0], "#### " + FENCED_BODY.split("\n\n#### ")[1]], "barrier: the fenced line is not a cut"
        assert changelog.part_ids(parts) == ["added", "added/providers"]

    @pytest.mark.parametrize(
        ("english", "translated", "why"),
        [
            pytest.param(DOC_SECTION, _translation(DOC_SECTION, "fr"), None, id="a-section-that-fits"),
            pytest.param(INTRO_LINE, _translation(INTRO_LINE, "fr"), None, id="an-intro-that-fits"),
            pytest.param(f"### 🐛 Fixed\n\n{SECURITY_SECTION}", _translation(f"### 🐛 Fixed\n\n{SECURITY_SECTION}", "fr"), None, id="a-heading-alone-joined-to-its-section-fits"),
            pytest.param(DOC_SECTION, f"{_translation(DOC_SECTION, 'fr')}\n\n#### 📌 Notes\n\n- A section the English does not have. (fr)", "the translation cuts into 2 parts instead of 1", id="a-heading-added"),
            pytest.param(DOC_SECTION, _translation(DOC_LINE, "fr"), "the translation drops the heading its English piece opens with", id="the-opening-heading-dropped"),
            pytest.param(INTRO_LINE, f"### 🧭 Introduzione\n\n{_translation(INTRO_LINE, 'it')}", "the translation opens with a heading its English piece does not have", id="a-heading-added-to-an-intro"),
        ],
    )
    def test_a_translated_piece_keeps_the_structure_that_places_it_in_its_chapter(self, changelog, english, translated, why):
        """One part, opening with a heading exactly when the English piece does: an added heading would cut it in two, a
        lost one would join it to the part before it, and the chapter would no longer cut into its pieces."""
        assert changelog.structure_change(english, translated) == why

    def test_the_units_are_the_preamble_and_the_chapters_and_a_long_one_is_cut_into_keyed_pieces(self, changelog, monkeypatch):
        """Up to the threshold a unit is one piece, keyed by its name; the open chapter is cut, its intro a piece of its
        own and the heading-only ``### 🐛 Fixed`` joined to Security. The chapter line and the closing rule are no text."""
        monkeypatch.setattr(changelog, "PIECE_THRESHOLD", THRESHOLD)
        units = changelog.english(CHANGELOG_EN)
        assert [(unit.name, unit.heading, unit.trailer) for unit in units] == [
            ("preamble", "", RULE),
            (OPEN, "## [3.1.0] - 2026-11-30", RULE),
            ("3.0.1", "## [3.0.1] - 2026-07-21", RULE),
            ("3.0.0", "## [3.0.0] - 2026-07-20", ""),  # the last chapter closes the file, not a rule
        ]
        assert [(piece.key, piece.text) for unit in units for piece in unit.pieces] == [
            ("CHANGELOG.md#preamble", PREAMBLE_EN),
            ("CHANGELOG.md#3.1.0/intro", INTRO_LINE),
            ("CHANGELOG.md#3.1.0/added", ADDED_SECTION),
            ("CHANGELOG.md#3.1.0/fixed/security", f"### 🐛 Fixed\n\n{SECURITY_SECTION}"),
            (DOC_KEY, DOC_SECTION),
            ("CHANGELOG.md#3.1.0/changed", CHANGED_SECTION),
            ("CHANGELOG.md#3.0.1", PATCH_BODY),
            ("CHANGELOG.md#3.0.0", FIRST_BODY),
        ]

    @pytest.mark.parametrize(
        ("over", "keys"),
        [
            pytest.param(0, ["CHANGELOG.md#3.1.0"], id="as-long-as-the-threshold-one-piece"),
            pytest.param(1, [f"CHANGELOG.md#3.1.0/{piece}" for piece in OPEN_PIECES], id="one-character-longer-cut"),
        ],
    )
    def test_a_chapter_as_long_as_the_threshold_is_one_piece(self, changelog, monkeypatch, over, keys):
        body = OPEN_EN.split("\n\n", 1)[1]
        monkeypatch.setattr(changelog, "PIECE_THRESHOLD", len(body) - over)
        unit = _open_unit(changelog, CHANGELOG_EN)
        assert unit.body == body, "barrier: the chapter's body is what lies between its line and its rule"
        assert [piece.key for piece in unit.pieces] == keys

    @pytest.mark.parametrize("threshold", [pytest.param(THRESHOLD, id="open-chapter-cut"), pytest.param(None, id="default-threshold-one-piece-each")])
    def test_the_english_pieces_assemble_back_into_the_english_byte_for_byte(self, changelog, monkeypatch, threshold):
        if threshold is not None:
            monkeypatch.setattr(changelog, "PIECE_THRESHOLD", threshold)
        units = changelog.english(CHANGELOG_EN)
        assert any(unit.split for unit in units) is (threshold is not None), "barrier: the threshold under test decides the cut"
        bodies = {unit.name: "\n\n".join(piece.text for piece in unit.pieces) for unit in units if unit.pieces}
        assert changelog.assemble(units, bodies) == CHANGELOG_EN


class TestChangelogLocate:
    """Where each piece of a chapter is in its translation: what lets a run keep the parts it does not translate again."""

    def test_after_a_section_was_inserted_each_part_is_found_by_its_recorded_index(self, changelog, monkeypatch):
        monkeypatch.setattr(changelog, "PIECE_THRESHOLD", THRESHOLD)
        translation = changelog.parse_translation(_translated_changelog(CHANGELOG_EN, "it"))
        before = _open_unit(changelog, CHANGELOG_EN)
        unit = _open_unit(changelog, _with_charts(CHANGELOG_EN))
        keys = [piece.key for piece in before.pieces]
        assert [piece.key for piece in unit.pieces] == [*keys[:3], CHARTS_KEY, *keys[3:]], "barrier: Charts is a new piece, between Security and Documentation"
        assert changelog.locate(unit, translation, {}, "it") == ({}, "5 parts for 6 pieces"), "barrier: by position, five parts cannot be matched to six pieces"
        found = changelog.locate(unit, translation, _indexed(changelog, CHANGELOG_EN, "it"), "it")
        assert found == ({piece.key: _translation(piece.text, "it") for piece in before.pieces}, "")

    def test_with_a_section_inserted_and_another_removed_the_indexes_still_pair_each_part_with_its_piece(self, changelog, monkeypatch):
        """As many parts as pieces, all shifted: by position, Charts would take the Documentation part and Documentation the
        part of the removed Changed."""
        monkeypatch.setattr(changelog, "PIECE_THRESHOLD", THRESHOLD)
        translation = changelog.parse_translation(_translated_changelog(CHANGELOG_EN, "it"))
        old = {piece.key: _translation(piece.text, "it") for piece in _open_unit(changelog, CHANGELOG_EN).pieces}
        unit = _open_unit(changelog, _with_charts(CHANGELOG_EN).replace(f"\n\n{CHANGED_SECTION}", "", 1))
        by_position = changelog.locate(unit, translation, {}, "it")[0]
        assert (by_position[CHARTS_KEY], by_position[DOC_KEY]) == (old[DOC_KEY], old["CHANGELOG.md#3.1.0/changed"]), "barrier: position pairs the wrong parts"
        found, why = changelog.locate(unit, translation, _indexed(changelog, CHANGELOG_EN, "it"), "it")
        assert ({piece.key: found.get(piece.key) for piece in unit.pieces}, why) == ({piece.key: old.get(piece.key) for piece in unit.pieces}, "")

    def test_with_no_index_yet_the_parts_are_matched_by_position(self, changelog, monkeypatch):
        """Nothing recorded for this language (a translation made before the cache knew it, or by hand): the parts go to
        the pieces in order, when there are as many. Another language's indexes are not this one's."""
        monkeypatch.setattr(changelog, "PIECE_THRESHOLD", THRESHOLD)
        translation = changelog.parse_translation(_translated_changelog(CHANGELOG_EN, "it"))
        unit = _open_unit(changelog, CHANGELOG_EN)
        expected = ({piece.key: _translation(piece.text, "it") for piece in unit.pieces}, "")
        assert changelog.locate(unit, translation, {}, "it") == expected
        assert changelog.locate(unit, translation, _indexed(changelog, CHANGELOG_EN, "fr", reverse=True), "it") == expected

    @pytest.mark.parametrize(("recorded", "why"), [pytest.param(True, "4 parts for 5 recorded pieces", id="indexes-recorded"), pytest.param(False, "4 parts for 5 pieces", id="no-index")])
    def test_a_translated_chapter_cut_into_another_number_of_parts_is_named_and_nothing_is_found(self, changelog, monkeypatch, recorded, why):
        monkeypatch.setattr(changelog, "PIECE_THRESHOLD", THRESHOLD)
        merged = _translated_changelog(CHANGELOG_EN, "it").replace(f"{DOC_HEADING}\n\n", "", 1)  # Documentation merged into Security by hand
        hashes = _indexed(changelog, CHANGELOG_EN, "it") if recorded else {}
        assert changelog.locate(_open_unit(changelog, CHANGELOG_EN), changelog.parse_translation(merged), hashes, "it") == ({}, why)

    def test_an_absent_chapter_is_named_and_a_one_piece_unit_is_its_whole_translated_body(self, changelog, monkeypatch):
        monkeypatch.setattr(changelog, "PIECE_THRESHOLD", THRESHOLD)
        units = {unit.name: unit for unit in changelog.english(CHANGELOG_EN)}
        translation = changelog.parse_translation(_translated_changelog(_changelog(PREAMBLE_EN, OPEN_EN, FIRST_EN), "it"))
        assert {
            "3.0.1 absent": changelog.locate(units["3.0.1"], translation, {}, "it"),
            "no file": changelog.locate(units["3.0.1"], None, {}, "it"),
            "3.0.0": changelog.locate(units["3.0.0"], translation, {}, "it"),
            "preamble": changelog.locate(units["preamble"], translation, {}, "it"),
        } == {
            "3.0.1 absent": ({}, "absent"),
            "no file": ({}, "absent"),
            "3.0.0": ({"CHANGELOG.md#3.0.0": _translation(FIRST_BODY, "it")}, ""),
            "preamble": ({"CHANGELOG.md#preamble": _translation(PREAMBLE_EN, "it")}, ""),
        }


# ---------------------------------------------------------------------------
# The CHANGELOG (R2 B25): run_translate
# ---------------------------------------------------------------------------


def _reviewed(text: str, lang: str) -> str:
    """``text`` after a reviewer's hand edits: a line of the open chapter's Added, the line of the released [3.0.1]."""
    for line in (ADDED_LINE, PATCH_LINE):
        assert text.count(f"{line} ({lang})") == 1, f"barrier: the translation holds {line!r} once"
        text = text.replace(f"{line} ({lang})", f"{line} ({lang}, reviewed)")
    return text


class TestChangelogTranslate:
    @pytest.mark.parametrize("workers", [pytest.param(1, id="workers1"), pytest.param(3, id="workers3")])
    def test_a_first_run_translates_every_piece_into_three_files_with_the_english_chapter_lines(self, changelog_sandbox, workers):
        """Each piece into each language, once. Each CHANGELOG.<lang>.md opens every chapter with its English line, in
        the English order (the app finds the chapters by them), and the cache records each piece done at its position."""
        box = changelog_sandbox
        pages = box.cache()
        assert box.translate("--workers", str(workers)) == 0
        assert box.llm.seams == CHANGELOG_SEAMS, "barrier: the run took the CHANGELOG's path, and no page's"
        assert box.requested() == ALL_PIECE_PAIRS
        assert sorted(box.changelog_files()) == ["CHANGELOG.es.md", "CHANGELOG.fr.md", "CHANGELOG.it.md", "CHANGELOG.md"]
        written = {lang: box.changelog_translation(lang) for lang in LANGS}
        assert {lang: _chapter_lines(text) for lang, text in written.items()} == dict.fromkeys(LANGS, _chapter_lines(CHANGELOG_EN))
        assert written == {lang: _translated_changelog(CHANGELOG_EN, lang) for lang in LANGS}
        entries = box.changelog_entries()
        assert {key: (entry["md5"], sorted(entry["langs_done"]), {lang: entry["langs"][lang].get("index") for lang in LANGS}) for key, entry in entries.items()} == {
            piece.key: (_md5(piece.text), sorted(LANGS), dict.fromkeys(LANGS, index)) for unit in box.changelog_units() for index, piece in enumerate(unit.pieces)
        }
        assert {key: entry for key, entry in box.cache().items() if key not in entries} == pages, "the run touched a page"
        assert list(box.scratch.iterdir()) == [], "the pieces' temporary files were left behind"
        assert box.changelog_plan() == []

    def test_a_second_run_translates_nothing_and_writes_nothing(self, changelog_sandbox):
        box = changelog_sandbox
        assert box.translate() == 0
        files, cache = box.changelog_files(), box.hash_file.read_bytes()
        box.llm.reset()
        box.capsys.readouterr()
        assert box.translate() == 0
        out = box.capsys.readouterr().out
        assert (box.llm.seams, box.llm.calls) == (set(), [])
        assert CHANGELOG_UP_TO_DATE in out
        assert (box.changelog_files(), box.hash_file.read_bytes()) == (files, cache)

    def test_a_changed_piece_is_translated_again_alone_and_every_other_part_is_kept_byte_for_byte(self, changelog_sandbox):
        """One line added to Documentation: that piece is translated again into each language, and nothing else. The
        other parts are kept from the files as they are, a reviewer's hand edits included."""
        box = changelog_sandbox
        assert box.translate() == 0
        reviewed = {lang: _reviewed(box.changelog_translation(lang), lang) for lang in LANGS}
        for lang, text in reviewed.items():
            box.write_changelog(text, lang)
        box.write_changelog(_with_doc_line(CHANGELOG_EN))
        box.llm.reset()
        assert box.translate() == 0
        assert box.requested() == [(DOC_KEY, lang) for lang in sorted(LANGS)]
        assert {lang: box.changelog_translation(lang) for lang in LANGS} == {lang: text.replace(f"{DOC_LINE} ({lang})", f"{DOC_LINE} ({lang})\n{NEW_DOC_LINE} ({lang})") for lang, text in reviewed.items()}
        entry = box.changelog_entries()[DOC_KEY]
        assert (entry["md5"], sorted(entry["langs_done"])) == (_md5(f"{DOC_SECTION}\n{NEW_DOC_LINE}"), sorted(LANGS))
        assert box.changelog_plan() == []

    def test_an_inserted_section_is_translated_alone_and_the_pieces_after_it_move_down(self, changelog_sandbox):
        box = changelog_sandbox
        assert box.translate() == 0
        english = _with_charts(CHANGELOG_EN)
        box.write_changelog(english)
        box.llm.reset()
        assert box.translate() == 0
        assert box.requested() == [(CHARTS_KEY, lang) for lang in sorted(LANGS)]
        assert {lang: box.changelog_translation(lang) for lang in LANGS} == {lang: _translated_changelog(english, lang) for lang in LANGS}
        open_keys = [f"CHANGELOG.md#3.1.0/{piece}" for piece in ("intro", "added", "fixed/security", "fixed/charts", "fixed/documentation", "changed")]
        entries = box.changelog_entries()
        assert {key: {lang: entries[key]["langs"][lang].get("index") for lang in LANGS} for key in open_keys} == {key: dict.fromkeys(LANGS, index) for index, key in enumerate(open_keys)}
        assert box.changelog_plan() == []

    def test_a_language_failing_on_an_inserted_piece_keeps_its_chapter_as_it_was(self, changelog_sandbox):
        """fr fails on the new Charts piece: CHANGELOG.fr.md is left byte for byte as it was, Charts pending in fr with its
        failure on record; it and es get the new section."""
        box = changelog_sandbox
        assert box.translate() == 0
        before = box.changelog_translation("fr")
        english = _with_charts(CHANGELOG_EN)
        box.write_changelog(english)
        box.llm.reset(fail={"fr": NETWORK_DOWN}, fail_only_on=CHARTS_SECTION.split("\n")[0])
        assert box.translate() == 1, "a failed translation fails the run"
        assert box.requested() == [(CHARTS_KEY, lang) for lang in sorted(LANGS)]
        assert box.changelog_translation("fr") == before
        assert {lang: box.changelog_translation(lang) for lang in ("it", "es")} == {lang: _translated_changelog(english, lang) for lang in ("it", "es")}
        entry = box.changelog_entries()[CHARTS_KEY]
        assert {
            "langs_done": sorted(entry["langs_done"]),
            "fr": {key: entry["langs"]["fr"].get(key) for key in ("failed", "failure_reason", "index")},
            "next run": box.changelog_plan(),
        } == {
            "langs_done": ["es", "it"],
            "fr": {"failed": True, "failure_reason": NETWORK_DOWN, "index": None},
            "next run": [(CHARTS_KEY, "fr")],
        }

    def test_a_language_failing_on_a_piece_of_an_untranslated_chapter_leaves_that_chapter_absent(self, changelog_sandbox):
        """First run, fr fails on Documentation alone: CHANGELOG.fr.md holds every other chapter and not the open one (the
        app shows it in English), every piece of which stays pending in fr; it and es are complete."""
        box = changelog_sandbox
        box.llm.reset(fail={"fr": NETWORK_DOWN}, fail_only_on=DOC_HEADING)
        assert box.translate() == 1
        assert box.requested() == ALL_PIECE_PAIRS
        assert box.changelog_translation("fr") == _translated_changelog(_changelog(PREAMBLE_EN, PATCH_EN, FIRST_EN), "fr")
        assert {lang: box.changelog_translation(lang) for lang in ("it", "es")} == {lang: _translated_changelog(CHANGELOG_EN, lang) for lang in ("it", "es")}
        doc = box.changelog_entries()[DOC_KEY]["langs"]["fr"]
        assert (doc.get("failed"), doc.get("failure_reason")) == (True, NETWORK_DOWN)
        assert box.changelog_plan() == sorted((f"CHANGELOG.md#3.1.0/{piece}", "fr") for piece in OPEN_PIECES)

    def test_file_changelog_alone_translates_no_page(self, changelog_sandbox):
        box = changelog_sandbox
        box.write_en(NEW_EN)
        page = box.entry()
        assert box.translate("--file", "CHANGELOG.md") == 0
        assert box.requested() == ALL_PIECE_PAIRS, "a page was translated"
        assert [box.translation(lang) for lang in LANGS] == [_translation(OLD_EN, lang) for lang in LANGS]
        assert box.entry() == page
        assert box.next_plan() == [(PAGE, lang) for lang in sorted(LANGS)], "the page is still to be translated"

    @pytest.mark.parametrize("path", PATHS)
    def test_no_file_translates_the_pages_and_the_changelog(self, changelog_sandbox, path):
        box = changelog_sandbox
        box.write_en(NEW_EN)
        assert box.translate("--workers", str(path.workers)) == 0
        assert box.llm.seams == path.seams | CHANGELOG_SEAMS, "barrier: the page took the path under test"
        assert box.requested() == sorted([(PAGE, lang) for lang in LANGS] + ALL_PIECE_PAIRS)
        assert [box.translation(lang) for lang in LANGS] == [_translation(NEW_EN, lang) for lang in LANGS]
        assert {lang: box.changelog_translation(lang) for lang in LANGS} == {lang: _translated_changelog(CHANGELOG_EN, lang) for lang in LANGS}
        assert (box.next_plan(), box.changelog_plan()) == ([], [])

    @pytest.mark.parametrize("argv", [pytest.param((), id="no-file"), pytest.param(("--file", "CHANGELOG.md"), id="file-changelog")])
    def test_a_dry_run_lists_every_piece_and_writes_nothing(self, changelog_sandbox, argv):
        box = changelog_sandbox
        cache = box.hash_file.read_bytes()
        box.capsys.readouterr()
        assert box.translate(*argv, "--dry-run") == 0
        out = box.capsys.readouterr().out
        listed = sorted((match["key"], match["lang"]) for match in _PLAN_LINE.finditer(out) if match["key"].startswith("CHANGELOG.md#"))
        total = _CHANGELOG_TOTAL.search(out)
        assert (listed, total and total.groupdict()) == (ALL_PIECE_PAIRS, {"pieces": str(len(CHANGELOG_KEYS)), "total": str(len(ALL_PIECE_PAIRS))})
        assert (box.llm.seams, box.llm.calls) == (set(), [])
        assert box.changelog_files() == {"CHANGELOG.md": CHANGELOG_EN.encode("utf-8")}
        assert box.hash_file.read_bytes() == cache

    @pytest.mark.parametrize(
        ("edit", "pieces"),
        [
            pytest.param(_without_doc, ("intro", "added", "fixed/security", "changed"), id="a-section-removed"),
            pytest.param(_with_changed_moved_up, ("intro", "added", "changed", "fixed/security", "fixed/documentation"), id="a-section-moved"),
        ],
    )
    def test_a_section_removed_or_moved_in_the_english_is_rebuilt_in_every_translation_without_the_model(self, changelog_sandbox, edit, pieces):
        """No piece needs translating, yet every CHANGELOG.<lang>.md keeps the old structure: the run rebuilds the files
        from the parts it finds, in the English order and with no model call, records the new positions and drops the
        entry that no translation places any more."""
        box = changelog_sandbox
        assert box.translate() == 0
        english = edit(CHANGELOG_EN)
        assert english != CHANGELOG_EN, "barrier: the edit applies"
        box.write_changelog(english)
        assert box.changelog_dry_run() == ([], sorted(f"CHANGELOG.{lang}.md" for lang in LANGS)), "the dry run names the files to rebuild and translates nothing"
        box.llm.reset()
        assert box.translate() == 0
        assert box.requested() == [], "every piece that remains is translated already"
        assert {lang: box.changelog_translation(lang) for lang in LANGS} == {lang: _translated_changelog(english, lang) for lang in LANGS}
        entries = box.changelog_entries()
        assert {key: {lang: entry["langs"][lang].get("index") for lang in LANGS} for key, entry in entries.items() if key.startswith("CHANGELOG.md#3.1.0/")} == {f"CHANGELOG.md#3.1.0/{piece}": dict.fromkeys(LANGS, index) for index, piece in enumerate(pieces)}
        assert box.changelog_dry_run() == ([], [])

    def test_a_new_translation_that_adds_a_section_is_refused_and_its_chapter_kept(self, changelog_sandbox):
        """fr's new translation of Documentation brings a ``####`` of its own: it cuts into two parts where the chapter
        has one piece, so every later run would translate the whole chapter again. Refused as failed: CHANGELOG.fr.md
        keeps its chapter as it was and the piece stays pending in fr; it and es are written."""
        box = changelog_sandbox
        assert box.translate() == 0
        before = box.changelog_translation("fr")
        english = _with_doc_line(CHANGELOG_EN)
        box.write_changelog(english)
        box.llm.reset(restructure=lambda text, lang: f"{text}\n\n#### 📌 Notes\n\n- A section the English does not have. ({lang})" if lang == "fr" else text)
        assert box.translate() == 1, "a refused translation fails the run"
        assert box.requested() == [(DOC_KEY, lang) for lang in sorted(LANGS)]
        assert box.changelog_translation("fr") == before
        assert {lang: box.changelog_translation(lang) for lang in ("it", "es")} == {lang: _translated_changelog(english, lang) for lang in ("it", "es")}
        entry = box.changelog_entries()[DOC_KEY]
        assert {"langs_done": sorted(entry["langs_done"]), "fr failure": entry["langs"]["fr"].get("failure_reason"), "next run": box.changelog_plan()} == {
            "langs_done": ["es", "it"],
            "fr failure": "structure changed: the translation cuts into 2 parts instead of 1",
            "next run": [(DOC_KEY, "fr")],
        }

    def test_a_new_translation_that_drops_the_heading_its_piece_opens_with_is_refused_too(self, changelog_sandbox):
        """The same harm through the other door: fr's new translation of Documentation loses its ``####`` line. Alone it
        is one part, but in the chapter it would join the part before it, so the chapter would no longer cut into its
        pieces and the next run would translate it all again in fr. Refused the same way, piece by piece."""
        box = changelog_sandbox
        assert box.translate() == 0
        before = box.changelog_translation("fr")
        box.write_changelog(_with_doc_line(CHANGELOG_EN))
        box.llm.reset(restructure=lambda text, lang: text.removeprefix(f"{DOC_HEADING}\n\n") if lang == "fr" else text)
        rc = box.translate()
        assert box.requested() == [(DOC_KEY, lang) for lang in sorted(LANGS)]
        entry = box.changelog_entries()[DOC_KEY]
        assert {"exit": rc, "fr kept as it was": box.changelog_translation("fr") == before, "fr failure": entry["langs"]["fr"].get("failure_reason"), "next run": box.changelog_plan()} == {
            "exit": 1,
            "fr kept as it was": True,
            "fr failure": "structure changed: the translation drops the heading its English piece opens with",
            "next run": [(DOC_KEY, "fr")],
        }

    def test_a_new_translation_that_breaks_its_chapter_at_a_seam_is_refused_and_the_chapter_kept(self, changelog_sandbox):
        """fr's new translation of Security fits as a piece, but ends on a code fence it leaves open: in the chapter the
        fence hides every heading after it, and the chapter would cut into three parts for five pieces. Refused chapter
        by chapter: CHANGELOG.fr.md is left byte for byte, Security stays pending in fr with the reason; it and es are
        written."""
        box = changelog_sandbox
        assert box.translate() == 0
        before = box.changelog_translation("fr")
        english = _with_security_line(CHANGELOG_EN)
        box.write_changelog(english)
        security = next(piece for unit in box.changelog_units() for piece in unit.pieces if piece.key == SECURITY_KEY)
        assert box.td.cl.structure_change(security.text, f"{_translation(security.text, 'fr')}\n\n```") is None, "barrier: the piece passes the check per piece, the chapter is what refuses it"
        box.llm.reset(restructure=lambda text, lang: f"{text}\n\n```" if lang == "fr" else text)
        assert box.translate() == 1, "a refused translation fails the run"
        assert box.requested() == [(SECURITY_KEY, lang) for lang in sorted(LANGS)]
        assert box.changelog_translation("fr") == before
        assert {lang: box.changelog_translation(lang) for lang in ("it", "es")} == {lang: _translated_changelog(english, lang) for lang in ("it", "es")}
        entry = box.changelog_entries()[SECURITY_KEY]
        assert {"langs_done": sorted(entry["langs_done"]), "fr failure": entry["langs"]["fr"].get("failure_reason"), "next run": box.changelog_plan()} == {
            "langs_done": ["es", "it"],
            "fr failure": "structure changed: the chapter would cut into 3 parts instead of 5",
            "next run": [(SECURITY_KEY, "fr")],
        }


# ---------------------------------------------------------------------------
# The CHANGELOG (R2 B25): run_stamp
# ---------------------------------------------------------------------------


class TestChangelogStamp:
    def test_stamping_a_hand_made_translation_records_each_piece_at_its_position(self, changelog_sandbox):
        """Three translations made by hand, the cache knowing no piece: ``--file CHANGELOG.md`` stamps every piece of every
        language done for the current English, with its position; the next run has nothing to translate."""
        box = changelog_sandbox
        for lang in LANGS:
            box.write_changelog(_translated_changelog(CHANGELOG_EN, lang), lang)
        pages = box.cache()
        assert box.changelog_entries() == {}, "barrier: the cache knows no piece"
        assert box.stamp("--file", "CHANGELOG.md") == 0
        entries = box.changelog_entries()
        assert {key: (entry["md5"], sorted(entry["langs_done"]), {lang: (entry["langs"][lang].get("stamped_by"), entry["langs"][lang].get("index")) for lang in LANGS}) for key, entry in entries.items()} == {
            piece.key: (_md5(piece.text), sorted(LANGS), dict.fromkeys(LANGS, ("translate-stamp", index))) for unit in box.changelog_units() for index, piece in enumerate(unit.pieces)
        }
        assert {key: entry for key, entry in box.cache().items() if key not in entries} == pages, "the stamp touched a page"
        assert box.changelog_plan() == []
        box.llm.reset()
        assert box.translate("--file", "CHANGELOG.md") == 0
        assert box.llm.calls == []

    def test_stamping_a_hand_port_stamps_the_changed_piece_alone(self, changelog_sandbox):
        """One line added to Documentation in the English and, by hand, in the three translations: the stamp records that
        piece alone, at its position, and leaves every other entry as it was."""
        box = changelog_sandbox
        assert box.translate() == 0
        others = {key: entry for key, entry in box.changelog_entries().items() if key != DOC_KEY}
        english = _with_doc_line(CHANGELOG_EN)
        box.write_changelog(english)
        for lang in LANGS:
            box.write_changelog(_translated_changelog(english, lang), lang)
        assert box.changelog_plan() == [(DOC_KEY, lang) for lang in sorted(LANGS)], "barrier: the cache does not know the hand port yet"
        box.capsys.readouterr()
        assert box.stamp("--file", "CHANGELOG.md") == 0
        out = box.capsys.readouterr().out
        assert sorted((match["key"], match["lang"]) for match in _STAMPED.finditer(out)) == [(DOC_KEY, lang) for lang in sorted(LANGS)]
        entries = box.changelog_entries()
        doc = entries.pop(DOC_KEY)
        assert entries == others, "a piece the hand port did not change was stamped"
        assert (doc["md5"], sorted(doc["langs_done"]), {lang: doc["langs"][lang].get("index") for lang in LANGS}) == (
            _md5(f"{DOC_SECTION}\n{NEW_DOC_LINE}"),
            sorted(LANGS),
            dict.fromkeys(LANGS, OPEN_PIECES.index("fixed/documentation")),
        )
        assert box.changelog_plan() == []

    def test_a_chapter_whose_parts_do_not_match_its_pieces_is_skipped_and_named(self, changelog_sandbox):
        """The fr translator merged Documentation into Security: four parts for five pieces. Stamping them would pair parts
        with the wrong pieces, so that chapter is named and left pending in fr (exit 1); the rest is stamped."""
        box = changelog_sandbox
        for lang in LANGS:
            text = _translated_changelog(CHANGELOG_EN, lang)
            box.write_changelog(text.replace(f"{DOC_HEADING}\n\n", "", 1) if lang == "fr" else text, lang)
        box.capsys.readouterr()
        assert box.stamp("--file", "CHANGELOG.md") == 1
        out = box.capsys.readouterr().out
        assert [match.groups() for match in _NOT_STAMPED.finditer(out)] == [("CHANGELOG.md#3.1.0", "fr", "4", "5")]
        open_fr = {(f"CHANGELOG.md#3.1.0/{piece}", "fr") for piece in OPEN_PIECES}
        assert {(key, lang) for key, entry in box.changelog_entries().items() for lang in entry["langs_done"]} == set(ALL_PIECE_PAIRS) - open_fr
        assert box.changelog_plan() == sorted(open_fr)

    def test_stamp_without_file_leaves_the_changelog_alone(self, changelog_sandbox):
        """``translate-stamp`` with no ``--file`` stamps the nav pages: a hand port of the CHANGELOG stays pending."""
        box = changelog_sandbox
        assert box.translate() == 0
        english = _with_doc_line(CHANGELOG_EN)
        box.write_changelog(english)
        for lang in LANGS:
            box.write_changelog(_translated_changelog(english, lang), lang)
        entries = box.changelog_entries()
        assert box.stamp() == 0
        assert box.changelog_entries() == entries
        assert box.changelog_plan() == [(DOC_KEY, lang) for lang in sorted(LANGS)]
