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

PURE: files under ``tmp_path`` only. ``DOCS_DIR``, ``HASH_FILE``, ``ENV_FILE`` and ``CONFIG_TOML`` point there; the
nav, the languages, the API key, the models and the model client are stubbed. No network, no LLM, no DB, no server.
The tracked cache, ``.env``, ``config.toml`` and the docs are never opened or written: an autouse guard fails any test
after which the tracked cache or ``config.toml`` changed.
"""

import argparse
import ast
import dataclasses
import hashlib
import importlib
import inspect
import json
import re
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


def _md5(text: str) -> str:
    return hashlib.md5(text.encode("utf-8")).hexdigest()


def _translation(source_text: str, lang: str) -> str:
    """The fake writer's output: every prose line tagged with the language, the Markdown structure untouched."""
    return "\n".join(f"{line} ({lang})" if line and not line.startswith("#") else line for line in source_text.split("\n"))


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
    Critique does; a language in ``interrupt`` raises ``SimulatedInterrupt``; any other language succeeds.
    ``during_analysis`` runs while the analysis is in progress, after the source was read: the author saving the EN."""

    fail: dict[str, str] = dataclasses.field(default_factory=dict)
    interrupt: set[str] = dataclasses.field(default_factory=set)
    during_analysis: Callable[[], None] | None = None
    seams: set[str] = dataclasses.field(default_factory=set)  # the seams the run called
    reached: list[str] = dataclasses.field(default_factory=list)  # the languages handed to the translate seam

    def reset(self, *, fail: dict[str, str] | None = None, interrupt=(), during_analysis: Callable[[], None] | None = None) -> None:
        self.fail = dict(fail or {})
        self.interrupt = set(interrupt)
        self.during_analysis = during_analysis
        self.seams.clear()
        self.reached.clear()

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
        if lang in self.fail:
            result["failure_reason"] = self.fail[lang]
            return result
        output_path = source_path.parent / source_path.name.replace(".en.md", f".{lang}.md")
        output_path.write_text(_translation(source_text, lang), encoding="utf-8")
        result.update(output_path=output_path, critique=f"fake critique ({lang})")
        return result


# ---------------------------------------------------------------------------
# The sandbox: translate_docs pointed at tmp_path
# ---------------------------------------------------------------------------


@dataclasses.dataclass
class Sandbox:
    """A docs tree and a hash cache under ``tmp_path``, which ``translate_docs`` reads and writes instead of the repo."""

    td: ModuleType
    docs: Path
    hash_file: Path
    llm: FakeAphra
    capsys: pytest.CaptureFixture

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
        """The (page, lang) pairs the next full run would translate, as ``translate --dry-run`` lists them."""
        before = self.hash_file.read_bytes()
        self.capsys.readouterr()
        assert self.translate("--dry-run") == 0
        out = self.capsys.readouterr().out
        assert self.hash_file.read_bytes() == before, "a dry run wrote the cache"
        pairs = sorted((match["key"], match["lang"]) for match in _PLAN_LINE.finditer(out))
        total = _PLAN_TOTAL.search(out)
        unreadable = f"barrier: the dry-run output changed shape, its plan cannot be read:\n{out}"
        assert total is not None or "Nothing to translate" in out, unreadable
        assert len(pairs) == (int(total["total"]) if total else 0), unreadable
        return pairs

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
    """Both pages translated into every language from their current EN, the cache in step with them."""
    td = translate_docs
    docs = (tmp_path / "docs").resolve()
    (docs / "user").mkdir(parents=True)
    aphra = tmp_path / "aphra-pipeline"
    aphra.mkdir()
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
    }
    for name, value in redirections.items():
        monkeypatch.setattr(td, name, value)  # raising: a renamed seam fails here, not silently in a real call
    box = Sandbox(td, docs, aphra / ".translate-hashes.json", llm, capsys)
    cache = {}
    for key, text in ((PAGE, OLD_EN), (OTHER, OTHER_EN)):
        box.write_en(text, key)
        for lang in LANGS:
            box.path(key, lang).write_text(_translation(text, lang), encoding="utf-8")
        cache[key] = _entry(text)
    box.hash_file.write_text(json.dumps(cache, indent=2), encoding="utf-8")
    return box


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
