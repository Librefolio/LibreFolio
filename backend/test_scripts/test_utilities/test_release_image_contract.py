"""Release images ship a production frontend: the contract between ``release.yml`` and the ``Dockerfile`` (M, R2 P0).

The images are built from the runner's working tree, and the docs gallery runs in the
same job before them. The gallery rebuilds ``frontend/build/`` in debug mode for its
test server (no minification, sourcemaps, ~2.7x the size) — today in its build step
``./dev.py server --test --build-only``, before Playwright starts the webServer — and
that build is what reached the published images. It also built the docs
site *before* the screenshots existed, so the "full" image had no gallery. Two halves
now hold the line, and this module pins both:

**The workflow** (job ``release-pipeline``), matched by the commands steps run, not by
their names:

* a production ``dev.py front build`` (no ``--debug``/``-d``, not instrumented) runs
  after the ``dev.py mkdocs gallery`` step and before every ``docker/build-push-action``
  step;
* a ``dev.py mkdocs build`` runs in the same window, so the full image ships the
  screenshots;
* the nightly report reads ``steps.rebuild-mkdocs.outcome`` — the docs rebuild is
  ``continue-on-error`` on ``dev``, and a soft failure nobody reads is a green lie —
  and, more generally, every ``continue-on-error`` step is read by the report, and the
  report reads no step id that does not exist (a typo'd id evaluates to ``''`` and
  silently hides the failure it was written for).

**The Dockerfile**:

* a ``FROM … AS frontend`` stage copies ``frontend/build/`` from the build context and
  then runs ``check_frontend_build.sh`` on that very directory;
* the final stage takes the build only through ``COPY --from=frontend <dir>
  ./frontend/build/``;
* no other stage copies ``frontend/build/`` (or a directory containing it) straight from
  the build context, which would bypass the guard.

**R12** pins more promises of the workflow:

* **cache keys carry the runner image**: a step exports ``RUNNER_IMAGE_OS`` from the
  runner's ``ImageOS`` before the first ``actions/cache``, and every ``key`` and
  ``restore-keys`` line reads ``env.RUNNER_IMAGE_OS``. ``runner.os`` is ``Linux`` on both
  ubuntu-latest images (24.04, then 26.04): keyed on it alone, a venv or a browser build
  made on one image would be restored on the other;
* **the gallery gates a release**: ``continue-on-error`` on ``dev`` only, and its command
  is the last of its step with nothing that can take over its exit status (no ``||``,
  pipe or ``::warning::`` fallback). The report reading its outcome is the generic check
  above;
* **a failed gallery leaves its evidence**: an ``actions/upload-artifact`` step after the
  gallery uploads ``frontend/playwright-report/`` and ``frontend/test-results/`` under
  ``!cancelled() && steps.<gallery>.outcome == 'failure'`` (a bare outcome check gets the
  implicit ``success()``, and is skipped on the failed release it is for);
* **the image tags are the user guide's** (``installation.en.md``, "Image Variants"),
  each variant found through the image build that pushes its metadata, whose inputs are
  read with their ``${{ }}`` evaluated for each run: on the stable release ``v1.2.0`` the
  full image is ``1.2.0`` and the light one ``1.2.0-light`` plus ``latest``, on a nightly
  ``nightly`` and ``nightly-light``; the full variant can never be ``latest`` (an
  explicit ``flavor: latest=false``, no raw ``latest``) and ``latest-light`` appears
  nowhere. A manual run from ``main``, which the guide does not cover, moves only
  ``latest``: the light image gets exactly that, the full one no tag;
* **a release's tag matches its kind**: a prerelease is tagged vX.Y.Z-rc.N, a stable
  release a plain vX.Y.Z (the developer's rules: a prerelease is never promoted, the stable
  release is published on a new tag, and the check is symmetric: an ``-rc.N`` tag published
  as stable would deploy the docs site and print a ``:latest`` line in its notes, while
  ``latest`` and the in-app update prompt both ignore it). The tag guard is found by what
  it does, the one step whose script reads ``github.event.release.tag_name`` and exits
  non-zero, and then held to what makes it the guard: it runs on every release and on no
  other run, reads the tag and the prerelease flag only through ``env`` (never a ``${{ }}``
  in its script) and is the job's first step. Its script, run in bash on fourteen tags per
  kind, passes exactly the ``vX.Y.Z-rc.N`` ones on a prerelease and the ``vX.Y.Z`` ones on
  a stable release (the ``v`` optional), each as a whole string, so a newline within or
  after the tag is part of it and ``$( )`` or quotes stay text, and fails every other with
  an ``::error`` titled for the kind (``Prerelease tag``, ``Release tag``). A prerelease on
  a plain ``v1.2.0`` tag and a stable release on ``v1.2.0-rc.1`` fail there, first, before
  anything else has run;
* **a prerelease publishes only its own tags** (the developer's rule): ``v1.2.0-rc.1``
  gives ``1.2.0-rc.1`` and ``1.2.0-rc.1-light``, a prerelease on a plain ``v1.2.0`` tag,
  were the tag guard ever weakened, ``1.2.0`` and ``1.2.0-light``. Neither moves
  ``latest`` nor deploys the docs site, which only a stable release and a manual run from
  ``main`` do;
* **an image build runs only when it has a tag**: every pushing build is guarded by
  ``if: steps.<id>.outputs.tags != ''`` on its own metadata step, read from its
  ``tags:``, since a push without a tag can only fail (the full build on a manual run
  from ``main``);
* **the prompted tag is pushed last**: on the stable release, the build that pushes
  ``1.2.0`` (the full variant, the tag the in-app update prompt probes) runs after those
  that push ``latest`` and ``1.2.0-light``, builds paired through their tags. That both
  come after the gallery and the production rebuild is the first check above;
* **the release notes pull those tags**: the step's script runs in bash, as written, with
  a stand-in ``gh`` that prints what it would append. A stable release pulls ``:latest``,
  ``:1.2.0`` and ``:1.2.0-light``, and the comment by ``:latest`` names the light
  variant; a prerelease pulls only its own two tags.

**Batch 34** pins the version the app shows and what dirties the checkout. The 1.1 release
screenshots read ``v1.1.0-dirty``: ``VERSION`` froze the backend's version only, and
``frontend/vite.config.ts`` ran ``git describe --dirty`` at each frontend build of the job,
after steps that rewrite tracked files.

* **the app version is frozen once**: one step, and only one, appends
  ``LF_APP_VERSION=$(cat VERSION)`` to ``$GITHUB_ENV``, right after the step that writes
  ``VERSION``, on every run that builds, and before every step that builds or serves the
  frontend (``dev.py front build``, the gallery, ``dev.py server``, ``npm run build``); no
  ``env:`` replaces it. The ``__APP_VERSION__`` define reads it, trimmed, before ``git
  describe``: checked in the source, and run in node (skipped without node) with a
  stand-in ``git`` that notes whether it was asked;
* **the checkout is checked, never gated**: a step runs ``sh
  scripts/ci/warn_if_tree_changed.sh "<label>"``, alone, right after ``dev.py install``, the
  first ``dev.py front build``, the first ``dev.py mkdocs build`` and the gallery. The
  script starts with ``#!/bin/sh`` and has no non-zero exit of its own; run in sh on git
  repositories under ``tmp_path``, it exits 0 on a clean checkout, an untracked file, a
  rewritten tracked file (the case that reads ``-dirty``) and outside any repository, each
  reported in its own words, and stops only without a label;
* **dev.py rewrites no tracked file for nothing**: ``cmd_install`` installs the root tools
  with ``npm ci`` and runs no npm command that may rewrite a lock (read with ``ast``); the
  icon generators, run in child interpreters on a tree under ``tmp_path``, regenerate a set
  only when an output is missing or ``frontend/generated-icons.json`` does not hold its
  source's sha256 and its recipe, never because an output's bytes differ (Pillow does not
  write the same PNG on every platform); and the committed record holds the committed
  logos, every icon is there and git ignores none of them, so a fresh checkout regenerates
  nothing.

Red phase of batch 34, against e501b9615 (HEAD): its 59 tests, run on ``git show HEAD:``
copies of the workflow, ``dev.py``, ``vite.config.ts`` and the script, went 46 red and 13
green. Red: every check of a real file (no ``LF_APP_VERSION`` export, no ``[CHECK]`` step,
no script, ``npm install`` at the root, ``getGitVersion()`` never reading
``LF_APP_VERSION``, no record), the two frozen node cases (git describe's answer baked in),
the five script runs, and the seven generator cases: a second call rewrote every icon (the
same bytes on macOS, a new mtime) and replaced the ones re-encoded as another platform
would. Green, as they should be: the four node cases without ``LF_APP_VERSION``, git
ignoring no icon, and the mutation cases that need no anchor HEAD lacks.

Each check is a function over the file's text that returns the list of violations, so
the same functions are run on mutated copies too: a check that cannot fail proves
nothing.

PURE: reads ``.github/workflows/release.yml``, ``Dockerfile``, ``dev.py``,
``frontend/vite.config.ts``, the tree check script and the committed icons, and mutates
copies in memory; the release-notes script runs in bash with the stand-in ``gh``, the tag
guard's in bash alone, the tree check in sh, the version's function in node, and dev.py's
icon generators in child interpreters (dev.py is never imported here: its import changes
directory and ``sys.path``, in a pytest process other units share). No DB, no server, no
network; writes only under ``tmp_path``.
"""

import ast
import copy
import fnmatch
import hashlib
import io
import json
import os
import posixpath
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
import textwrap
from dataclasses import dataclass, field
from pathlib import Path

import pytest
import yaml
from PIL import Image, ImageDraw

PROJECT_ROOT = Path(__file__).resolve().parents[3]
WORKFLOW = PROJECT_ROOT / ".github" / "workflows" / "release.yml"
DOCKERFILE = PROJECT_ROOT / "Dockerfile"
# Read with ast and run in child interpreters, never imported here: its import changes directory and ``sys.path``.
DEV_PY = PROJECT_ROOT / "dev.py"
VITE_CONFIG = PROJECT_ROOT / "frontend" / "vite.config.ts"

JOB = "release-pipeline"
DOCS_REBUILD_ID = "rebuild-mkdocs"
GUARD = "check_frontend_build.sh"
GUARD_STAGE = "frontend"
OUTCOME_REF = re.compile(r"steps\.([A-Za-z0-9_-]+)\.outcome")


# ---------------------------------------------------------------------------
# release.yml
# ---------------------------------------------------------------------------


def pipeline_steps(workflow_text: str) -> list[dict]:
    return yaml.safe_load(workflow_text)["jobs"][JOB]["steps"]


def _command_lines(step: dict) -> list[list[str]]:
    """The step's ``run`` script as tokenised command lines (comments and blanks dropped)."""
    lines = []
    for raw in (step.get("run") or "").splitlines():
        line = raw.strip()
        if line and not line.startswith("#"):
            lines.append(line.split())
    return lines


def _runs_dev_py(step: dict, *subcommand: str) -> list[list[str]]:
    """Every command line of the step that invokes ``dev.py <subcommand…>``; the tokens after it."""
    found = []
    for tokens in _command_lines(step):
        for i, token in enumerate(tokens):
            if token.endswith("dev.py") and tuple(tokens[i + 1 : i + 1 + len(subcommand)]) == subcommand:
                found.append(tokens[i + 1 + len(subcommand) :])
    return found


def is_gallery(step: dict) -> bool:
    return bool(_runs_dev_py(step, "mkdocs", "gallery"))


def is_production_front_build(step: dict) -> bool:
    if "COVERAGE_INSTRUMENT" in str(step):
        return False
    return any(not {"--debug", "-d"} & set(args) for args in _runs_dev_py(step, "front", "build"))


def is_docs_build(step: dict) -> bool:
    return bool(_runs_dev_py(step, "mkdocs", "build"))


def is_image_build(step: dict) -> bool:
    return (step.get("uses") or "").startswith("docker/build-push-action")


def _indexes(steps: list[dict], predicate) -> list[int]:
    return [i for i, step in enumerate(steps) if predicate(step)]


def _gallery_to_images_window(steps: list[dict]) -> tuple[tuple[int, int] | None, list[str]]:
    """(last gallery step, first image build), or the reasons the window does not exist."""
    galleries, images = _indexes(steps, is_gallery), _indexes(steps, is_image_build)
    problems = []
    if not galleries:
        problems.append("no step runs `dev.py mkdocs gallery`")
    if not images:
        problems.append("no step uses docker/build-push-action")
    if problems:
        return None, problems
    return (max(galleries), min(images)), []


def _rebuild_violations(workflow_text: str, predicate, what: str) -> list[str]:
    steps = pipeline_steps(workflow_text)
    window, problems = _gallery_to_images_window(steps)
    if window is None:
        return problems
    gallery, first_image = window
    if not any(gallery < i < first_image for i in _indexes(steps, predicate)):
        return [f"no {what} between the gallery (step {gallery}) and the first image build (step {first_image})"]
    return []


def frontend_rebuild_violations(workflow_text: str) -> list[str]:
    return _rebuild_violations(workflow_text, is_production_front_build, "production `dev.py front build`")


def docs_rebuild_violations(workflow_text: str) -> list[str]:
    return _rebuild_violations(workflow_text, is_docs_build, "`dev.py mkdocs build`")


def _docs_rebuild_report_violations(steps: list[dict], ids: dict[str, int], read: set[str]) -> list[str]:
    rebuild = ids.get(DOCS_REBUILD_ID)
    problems = []
    if rebuild is None:
        problems.append(f"no step has id {DOCS_REBUILD_ID!r}")
    elif not is_docs_build(steps[rebuild]):
        problems.append(f"step {DOCS_REBUILD_ID!r} does not run `dev.py mkdocs build`")
    if DOCS_REBUILD_ID not in read:
        problems.append(f"the nightly report does not read steps.{DOCS_REBUILD_ID}.outcome")
    return problems


def soft_failure_report_violations(workflow_text: str) -> list[str]:
    steps = pipeline_steps(workflow_text)
    ids = {step["id"]: i for i, step in enumerate(steps) if "id" in step}
    read = set(OUTCOME_REF.findall("\n".join(step.get("run") or "" for step in steps)))
    problems = [] if read else ["no step reads any steps.<id>.outcome: the nightly soft-failure report is gone"]
    problems += _docs_rebuild_report_violations(steps, ids, read)
    problems += [f"step {i} ({step.get('id') or 'no id'}) is continue-on-error but the nightly report never reads its outcome" for i, step in enumerate(steps) if "continue-on-error" in step and step.get("id") not in read]
    problems += [f"the report reads steps.{name}.outcome but no step has id {name!r}" for name in sorted(read - set(ids))]
    return problems


# ---------------------------------------------------------------------------
# release.yml, R12: the cache keys carry the runner image
# ---------------------------------------------------------------------------

IMAGE_OS = "RUNNER_IMAGE_OS"
EXPORTS_IMAGE_OS = re.compile(r"""\bRUNNER_IMAGE_OS=["']?\$\{?ImageOS\b.*>>\s*["']?\$\{?GITHUB_ENV\b""")
IMAGE_OS_IN_EXPRESSION = re.compile(r"\$\{\{[^}]*\benv\.RUNNER_IMAGE_OS\b[^}]*\}\}")


def _logical_lines(step: dict) -> list[str]:
    """The step's ``run`` script as shell lines: comments and blanks dropped, backslash continuations joined."""
    lines, pending = [], ""
    for raw in (step.get("run") or "").splitlines():
        line = pending + raw.strip()
        pending = line[:-1] + " " if line.endswith("\\") else ""
        if line and not pending and not line.startswith("#"):
            lines.append(line)
    return lines


def is_cache(step: dict) -> bool:
    return (step.get("uses") or "").startswith("actions/cache")


def exports_runner_image(step: dict) -> bool:
    """Whether the step appends ``RUNNER_IMAGE_OS=$ImageOS`` to ``$GITHUB_ENV``: ImageOS is a runner variable, absent from the expression ``env`` context."""
    return any(EXPORTS_IMAGE_OS.search(line) for line in _logical_lines(step))


def _cache_keys(step: dict) -> list[tuple[str, str]]:
    """``(input, key)`` for the cache's ``key`` and each ``restore-keys`` line."""
    inputs = step.get("with") or {}
    restore = [("restore-keys", line.strip()) for line in str(inputs.get("restore-keys") or "").splitlines() if line.strip()]
    return [("key", str(inputs.get("key") or "")), *restore]


def cache_key_violations(workflow_text: str) -> list[str]:
    steps = pipeline_steps(workflow_text)
    caches, exports = _indexes(steps, is_cache), _indexes(steps, exports_runner_image)
    if not caches:
        return ["no step uses actions/cache"]
    problems = []
    if not exports:
        problems.append(f"no step exports {IMAGE_OS}=$ImageOS to $GITHUB_ENV: env.{IMAGE_OS} is empty in every cache key")
    elif exports[0] > caches[0]:
        problems.append(f"{IMAGE_OS} is exported at step {exports[0]}, after the first actions/cache (step {caches[0]}): that cache keys on an empty image name")
    for i in caches:
        problems += [f"step {i} ({steps[i].get('name')}): {name} {key} lacks env.{IMAGE_OS}, so a cache saved on one runner image is restored on another" for name, key in _cache_keys(steps[i]) if not IMAGE_OS_IN_EXPRESSION.search(key)]
    return problems


# ---------------------------------------------------------------------------
# release.yml, R12: the gallery gates a release
# ---------------------------------------------------------------------------

GALLERY_ID = "gallery"
DEV_ONLY = "${{ github.ref_name == 'dev' }}"
ONLY_ON_REF = re.compile(r"\$\{\{\s*github\.ref_name\s*==\s*'([^']*)'\s*\}\}")
# What lets something other than a command decide its line's exit status: a list (|| && ;),
# a pipe, a background job, a subshell or a substitution, a negation, a condition.
SHELL_CONTROL = re.compile(r"\|\|?|&&|;|(?<![<>])&(?!>)|[()`]|(?:^|\s)(?:!|if|while|until)(?=\s|$)")
QUOTED = re.compile(r"""'[^']*'|"(?:[^"\\]|\\.)*"|\$\{\{.*?\}\}""")


def only_on_ref(condition) -> str | None:
    """The branch a ``${{ github.ref_name == '<branch>' }}`` condition holds on; None for any other value."""
    match = ONLY_ON_REF.fullmatch(condition.strip()) if isinstance(condition, str) else None
    return match.group(1) if match else None


def _exit_status_violations(index: int, step: dict) -> list[str]:
    """Whatever lets the gallery step succeed when the gallery fails."""
    lines = _logical_lines(step)
    runs = [n for n, line in enumerate(lines) if is_gallery({"run": line})]
    problems = []
    for n in runs:
        operators = sorted({operator.strip() for operator in SHELL_CONTROL.findall(QUOTED.sub("_", lines[n]))})
        if operators:
            problems.append(f"the gallery (step {index}) is chained with {operators}: another command can decide its exit status")
    if runs and runs[-1] != len(lines) - 1:
        problems.append(f"the gallery (step {index}) is not its step's last command: {lines[runs[-1] + 1 :]} would decide the step's exit status")
    if any("::warning::" in line for line in lines):
        problems.append(f"the gallery (step {index}) downgrades a failure to a ::warning:: annotation")
    return problems


def gallery_gate_violations(workflow_text: str) -> list[str]:
    steps = pipeline_steps(workflow_text)
    galleries = _indexes(steps, is_gallery)
    if not galleries:
        return ["no step runs `dev.py mkdocs gallery`"]
    problems = []
    for i in galleries:
        soft = steps[i].get("continue-on-error")
        if only_on_ref(soft) != "dev":
            problems.append(f"the gallery (step {i}) is continue-on-error {soft!r}, not {DEV_ONLY}: a release must fail on a broken gallery, only a nightly carries on")
        problems += _exit_status_violations(i, steps[i])
    return problems


UPLOAD_ACTION = "actions/upload-artifact"
GALLERY_EVIDENCE = ("frontend/playwright-report", "frontend/test-results")


def _upload_paths(step: dict) -> set[str]:
    return {posixpath.normpath(line.strip()) for line in str((step.get("with") or {}).get("path") or "").splitlines() if line.strip()}


def uploads_gallery_evidence(step: dict) -> bool:
    return (step.get("uses") or "").startswith(UPLOAD_ACTION) and set(GALLERY_EVIDENCE) <= _upload_paths(step)


def _conjuncts(condition) -> set[str] | None:
    """An ``if:`` (bare or in ``${{ }}``) as its ``&&`` terms, whitespace dropped; None when it is not a plain conjunction."""
    text = str(condition or "").strip()
    wrapped = EXPRESSION_WRAPPER.fullmatch(text)
    text = wrapped.group(1) if wrapped else text
    return None if "||" in text else {re.sub(r"\s+", "", term) for term in text.split("&&")}


def gallery_evidence_violations(workflow_text: str) -> list[str]:
    """A failed gallery uploads its Playwright report and test-results, also after a failed release step.

    Without ``!cancelled()`` the implicit ``success()`` skips the upload once the gallery has failed a
    release: the one run it exists for.
    """
    steps = pipeline_steps(workflow_text)
    galleries = _indexes(steps, is_gallery)
    if not galleries:
        return ["no step runs `dev.py mkdocs gallery`"]
    gallery = galleries[-1]
    gallery_id = steps[gallery].get("id")
    if not gallery_id:
        return [f"the gallery (step {gallery}) has no id: no step can read its outcome"]
    uploads = _indexes(steps, uploads_gallery_evidence)
    if not uploads:
        return [f"no {UPLOAD_ACTION} step uploads {' and '.join(GALLERY_EVIDENCE)}: a failed gallery leaves no report to read"]
    problems = []
    for i in uploads:
        if _conjuncts(steps[i].get("if")) != {"!cancelled()", f"steps.{gallery_id}.outcome=='failure'"}:
            problems.append(f"the gallery evidence upload has if: {steps[i].get('if')!r}, not exactly !cancelled() && steps.{gallery_id}.outcome == 'failure' (step {i})")
        if i < gallery:
            problems.append(f"the gallery evidence upload runs before the gallery (step {i} < {gallery}): steps.{gallery_id}.outcome is still empty there")
    return problems


# ---------------------------------------------------------------------------
# release.yml, R12: the runs this module evaluates, and GitHub's expressions on them
# ---------------------------------------------------------------------------

EXPRESSION = re.compile(r"\$\{\{(.*?)\}\}", re.DOTALL)
EXPRESSION_WRAPPER = re.compile(r"\$\{\{(.*)\}\}", re.DOTALL)
EXPRESSION_TOKEN = re.compile(r"'(?:[^']|'')*'|&&|\|\||==|!=|!|\(|\)|[A-Za-z_][\w.-]*|\S")
EXPRESSION_NAME = re.compile(r"[A-Za-z_][\w.-]*")
LITERALS = {"true": True, "false": False, "null": None}


@dataclass(frozen=True)
class Run:
    """A workflow run as GitHub's expressions see it: its event, its ref, and whether its release is a prerelease."""

    name: str
    event_name: str
    ref_name: str  # a release runs on its git tag, any other run on its branch
    prerelease: bool = False

    def lookup(self, path: str):
        release = self.event_name == "release"
        context = {
            "github.event_name": self.event_name,
            "github.ref_name": self.ref_name,
            "github.event.release.prerelease": self.prerelease if release else None,
            "github.event.release.tag_name": self.ref_name if release else None,
        }
        if path.startswith("secrets."):
            return ""
        if path not in context:
            raise ValueError(f"this test does not model {path!r}")
        return context[path]


VERSION = "1.2.0"
STABLE = Run(f"stable release v{VERSION}", "release", f"v{VERSION}")
RC = Run(f"prerelease v{VERSION}-rc.1", "release", f"v{VERSION}-rc.1", prerelease=True)
PLAIN_PRERELEASE = Run(f"prerelease v{VERSION} (plain tag)", "release", f"v{VERSION}", prerelease=True)
RC_AS_STABLE = Run(f"stable release v{VERSION}-rc.1 (rc tag)", "release", f"v{VERSION}-rc.1")  # only the tag guard stops it: see TAG_GUARD
NIGHTLY = Run("nightly", "push", "dev")
MAIN = Run("manual run from main", "workflow_dispatch", "main")


def _equal(left, right) -> bool:
    """GitHub's ``==``: strings compare ignoring case; it coerces mixed types, which this test refuses to guess."""
    if isinstance(left, str) and isinstance(right, str):
        return left.casefold() == right.casefold()
    if type(left) is not type(right):
        raise ValueError(f"this test does not model GitHub's coercion in {left!r} == {right!r}")
    return left == right


class _Expression:
    """A GitHub expression evaluated on one run.

    Literals, context names, ``!``, ``==``/``!=``, parentheses, and ``&&``/``||``, which return an operand as
    GitHub's do (``cond && 'auto' || 'false'`` yields a string). Anything else is refused, not guessed.
    """

    def __init__(self, text: str, run: Run):
        self.tokens, self.at, self.run = EXPRESSION_TOKEN.findall(text), 0, run

    def value(self):
        value = self._either()
        if self.at != len(self.tokens):
            raise ValueError(f"cannot read {' '.join(self.tokens)!r} past {self.tokens[self.at]!r}")
        return value

    def _take(self, *expected: str) -> str | None:
        if self.at < len(self.tokens) and self.tokens[self.at] in expected:
            self.at += 1
            return self.tokens[self.at - 1]
        return None

    def _either(self):
        value = self._both()
        while self._take("||"):
            right = self._both()
            value = value or right
        return value

    def _both(self):
        value = self._compared()
        while self._take("&&"):
            right = self._compared()
            value = value and right
        return value

    def _compared(self):
        value = self._unary()
        while operator := self._take("==", "!="):
            value = _equal(value, self._unary()) == (operator == "==")
        return value

    def _unary(self):
        if self._take("!"):
            return not self._unary()
        if self._take("("):
            value = self._either()
            if not self._take(")"):
                raise ValueError("unbalanced parentheses")
            return value
        if self.at == len(self.tokens):
            raise ValueError("the expression ends too early")
        token, self.at = self.tokens[self.at], self.at + 1
        if len(token) > 1 and token[0] == token[-1] == "'":
            return token[1:-1].replace("''", "'")
        if token in LITERALS:
            return LITERALS[token]
        if EXPRESSION_NAME.fullmatch(token) and not self._take("("):
            return self.run.lookup(token)
        raise ValueError(f"this test does not model {token!r}")


def _text(value) -> str:
    """An expression's value as GitHub writes it into a workflow string."""
    if value is None:
        return ""
    return str(value).lower() if isinstance(value, bool) else str(value)


def substitute(text, run: Run) -> str:
    """``text`` with each ``${{ }}`` replaced by its value on ``run``, as GitHub does before a step or an action reads it."""
    source = text if isinstance(text, str) else _text(text)
    return EXPRESSION.sub(lambda match: _text(_Expression(match.group(1), run).value()), source)


def holds(condition, run: Run) -> bool:
    """Whether a step's ``if:`` (bare or in ``${{ }}``) holds on ``run``, everything before it having succeeded; no ``if:`` always does."""
    if condition is None or isinstance(condition, bool):
        return condition is not False
    wrapped = EXPRESSION_WRAPPER.fullmatch(condition.strip())
    return bool(_Expression(wrapped.group(1) if wrapped else condition, run).value())


def run_script(step: dict, run: Run, prelude: str = "") -> subprocess.CompletedProcess[str]:
    """The step's script on ``run``, as GitHub runs it: the ``${{ }}`` of its env and script evaluated, then ``bash -e``.

    Only PATH and the step's env, no profile or rc file, the temp directory as working directory; ``prelude`` goes ahead of
    the script (a stand-in for a command, say).
    """
    env = {"PATH": os.environ.get("PATH", os.defpath)} | {name: substitute(value, run) for name, value in (step.get("env") or {}).items()}
    command = ["bash", "--noprofile", "--norc", "-e", "-c", prelude + substitute(step.get("run"), run)]
    return subprocess.run(command, env=env, cwd=tempfile.gettempdir(), capture_output=True, encoding="utf-8", timeout=30, check=False)


# ---------------------------------------------------------------------------
# release.yml, R12: the image tags are the user guide's
# ---------------------------------------------------------------------------

METADATA_ACTION = "docker/metadata-action"
TAGS_OUTPUT = re.compile(r"\$\{\{\s*steps\.([A-Za-z0-9_-]+)\.outputs\.tags\s*\}\}")
FIELD_SEPARATOR = re.compile(r",(?![^{]*\}\})")  # a comma outside ${{ }}
DEFAULT_DOCS_VARIANT = "full"  # the Dockerfile's `ARG DOCS_VARIANT=full`, pinned by default_variant_violations
LATEST_VARIANT = "light"
VERSION_TYPES = ("semver", "pep440")
SEMVER = re.compile(r"v?(?P<version>(?P<major>0|[1-9]\d*)\.(?P<minor>0|[1-9]\d*)\.(?P<patch>0|[1-9]\d*)(?P<prerelease>-[0-9A-Za-z.-]+)?)(?:\+[0-9A-Za-z.-]+)?")
# mkdocs_src/docs/user/installation.en.md, "Image Variants": the tags each variant gets on a stable
# release and on a nightly. `latest` is the light variant, versions have no "v".
GUIDE_TAGS = {
    STABLE: {"full": {VERSION}, "light": {f"{VERSION}-light", "latest"}},
    NIGHTLY: {"full": {"nightly"}, "light": {"nightly-light"}},
}
# Not in the guide: a manual run from main moves only `latest`, which is the light variant. The full
# variant has no tag there, none is invented for it, and build_guard_violations' guard skips its build.
MAIN_RUN_TAGS = {MAIN: {"full": set(), "light": {"latest"}}}
# The developer's rule: a GitHub prerelease publishes only its own tags and never moves `latest`, also on
# a plain vX.Y.Z git tag, where metadata-action's own semver-prerelease skip does not apply. That run now
# fails first, at the tag guard (TAG_GUARD): this is the second line, should the guard ever be weakened.
PRERELEASE_TAGS = {
    RC: {"full": {f"{VERSION}-rc.1"}, "light": {f"{VERSION}-rc.1-light"}},
    PLAIN_PRERELEASE: {"full": {VERSION}, "light": {f"{VERSION}-light"}},
}
# The guard every pushing image build carries, on its own metadata step: a push without a tag can only fail.
TAGS_NOT_EMPTY = re.compile(r"steps\.([A-Za-z0-9_-]+)\.outputs\.tags\s*!=\s*''")


def is_metadata(step: dict) -> bool:
    return (step.get("uses") or "").startswith(METADATA_ACTION)


def _attribute(field: str) -> tuple[str, str]:
    key, separator, value = field.partition("=")
    return (key.strip().lower(), value.strip()) if separator else ("value", key.strip())


def _entries(text) -> list[list[tuple[str, str]]]:
    """A metadata-action list input (``tags``, ``flavor``): per line, its ``(attribute, value)`` pairs.

    Commas inside ``${{ }}`` do not split, and a bare field is the value: ``latest`` alone is a raw tag.
    """
    return [[_attribute(field) for field in FIELD_SEPARATOR.split(line)] for line in str(text or "").splitlines() if line.strip()]


def _tag_entries(step: dict) -> list[dict[str, str]]:
    return [dict(pairs) for pairs in _entries((step.get("with") or {}).get("tags"))]


def _flavor(text) -> dict:
    """A ``flavor`` input: ``latest`` (metadata-action's default: auto) and the global prefix/suffix, which reach ``latest`` only with ``onlatest=true``."""
    flavor = {"latest": "auto", "prefix": "", "suffix": "", "onlatest": set()}
    for pairs in _entries(text):
        last = None
        for key, value in pairs:
            if key in ("latest", "prefix", "suffix"):
                flavor[key], last = value, key
            elif key == "onlatest" and last in ("prefix", "suffix") and value.lower() == "true":
                flavor["onlatest"].add(last)
    return flavor


def _rendered(value: str, entry: dict, flavor: dict) -> str:
    """A tag as metadata-action writes it: the entry's own prefix/suffix, else the flavor's."""
    return f"{entry.get('prefix', flavor['prefix'])}{value}{entry.get('suffix', flavor['suffix'])}"


def _latest(flavor: dict) -> str:
    affix = {part: flavor[part] if part in flavor["onlatest"] else "" for part in ("prefix", "suffix")}
    return f"{affix['prefix']}latest{affix['suffix']}"


def _enabled(condition: str | None) -> bool:
    """Whether a tag's ``enable=`` holds, its expressions already evaluated; metadata-action's own templates count as enabled."""
    return condition is None or condition.strip().lower() != "false"


def git_tag_version(run: Run) -> re.Match | None:
    """The semver of the git tag a release runs on (``{{version}}`` drops its ``v``); None on any other run."""
    return SEMVER.fullmatch(run.ref_name) if run.event_name == "release" else None


def _version_tag(pattern: str, version: re.Match) -> str:
    """A semver ``pattern`` rendered for ``version``; a semver prerelease only ever gets ``{{version}}``, as in metadata-action."""
    fields = {"version": version["version"], "major": version["major"], "minor": version["minor"], "patch": version["patch"], "raw": version.group(0)}
    return re.sub(r"\{\{\s*(\w+)\s*\}\}", lambda match: fields.get(match.group(1), match.group(0)), "{{version}}" if version["prerelease"] else pattern)


def _entry_tag(entry: dict, flavor: dict, version: re.Match | None) -> tuple[str | None, bool]:
    """The tag an entry generates (None for none), and whether it lets ``latest=auto`` add ``latest``: a stable semver only."""
    kind = entry.get("type", "raw")
    if kind == "raw":
        return _rendered(entry.get("value", ""), entry, flavor), False
    if kind not in VERSION_TYPES:
        return f"<type={kind}>", False  # sha, ref, edge, schedule, match: in no table here
    if version is None:
        return None, False  # a version comes from a semver git tag: releases only
    return _rendered(_version_tag(entry.get("pattern", ""), version), entry, flavor), not version["prerelease"]


def published_tags(step: dict, run: Run) -> set[str]:
    """The tags a metadata-action step gives its image on ``run``: its inputs' ``${{ }}`` evaluated, then read as metadata-action reads them."""
    inputs = step.get("with") or {}
    flavor, version = _flavor(substitute(inputs.get("flavor"), run)), git_tag_version(run)
    entries = [entry for entry in map(dict, _entries(substitute(inputs.get("tags"), run))) if _enabled(entry.get("enable"))]
    generated = [_entry_tag(entry, flavor, version) for entry in entries]
    tags = {tag for tag, _ in generated if tag is not None}
    stable = any(lets_latest for _, lets_latest in generated)
    if tags and (flavor["latest"] not in ("auto", "false") or (flavor["latest"] == "auto" and stable)):
        tags.add(_latest(flavor))  # true: on every run with a tag, raw ones included (metadata-action's procRaw)
    return tags


def docs_variant(step: dict) -> str:
    """The DOCS_VARIANT an image build passes, else the Dockerfile's default."""
    for line in str((step.get("with") or {}).get("build-args") or "").splitlines():
        name, _, value = line.strip().partition("=")
        if name == "DOCS_VARIANT":
            return value.strip()
    return DEFAULT_DOCS_VARIANT


def pushes(step: dict) -> bool:
    """Whether an image build pushes: ``push: true``, or an expression this test cannot read."""
    value = (step.get("with") or {}).get("push", False)
    return value is True or (isinstance(value, str) and value.strip().lower() not in ("", "false"))


def is_image_push(step: dict) -> bool:
    return is_image_build(step) and pushes(step)


def _metadata_by_id(steps: list[dict]) -> dict[str, dict]:
    return {step["id"]: step for step in steps if is_metadata(step) and "id" in step}


def _pushed_metadata(build: dict, metadata: dict[str, dict]) -> list[str] | None:
    """The ids of the metadata-action steps whose tags an image build pushes, read from its ``tags:`` expression; None if it pushes anything else."""
    tags = str((build.get("with") or {}).get("tags") or "")
    ids = TAGS_OUTPUT.findall(tags)
    return ids if ids and set(ids) <= set(metadata) and not TAGS_OUTPUT.sub("", tags).strip(", \n") else None


def variant_metadata(steps: list[dict]) -> tuple[dict[str, list[dict]], list[str]]:
    """Each image variant's metadata-action steps, followed from the tags its docker/build-push-action pushes."""
    metadata = _metadata_by_id(steps)
    variants, problems = {}, []
    for i in _indexes(steps, is_image_push):
        variant, ids = docs_variant(steps[i]), _pushed_metadata(steps[i], metadata)
        if ids is None:
            problems.append(f"the {variant} image build (step {i}) pushes {str(steps[i]['with'].get('tags') or '').strip()!r}, not only docker/metadata-action tags: this test cannot vouch for them")
        else:
            variants.setdefault(variant, []).extend(metadata[name] for name in ids)
    return variants, problems


def _latest_violations(variants: dict[str, list[dict]]) -> list[str]:
    """Only the light variant may ever be `latest`: any other turns metadata-action's off and adds none of its own."""
    problems = []
    for variant, metadata in variants.items():
        if variant == LATEST_VARIANT:
            continue
        for step in metadata:
            latest = _flavor((step.get("with") or {}).get("flavor"))["latest"]
            if latest != "false":
                problems.append(f"the {variant} variant's metadata ({step.get('id')}) has flavor latest={latest}, not latest=false: metadata-action tags every semver release `latest` by itself")
            if any(entry.get("type", "raw") == "raw" and entry.get("value") == "latest" for entry in _tag_entries(step)):
                problems.append(f"the {variant} variant's metadata ({step.get('id')}) has a raw `latest` tag: `latest` is the {LATEST_VARIANT} variant")
    return problems


def _table_violations(variants: dict[str, list[dict]], table: dict[Run, dict[str, set[str]]]) -> list[str]:
    problems = []
    for run, documented in table.items():
        for variant in sorted(set(documented) | set(variants)):
            tagged = set().union(*(published_tags(step, run) for step in variants.get(variant, [])))
            expected = documented.get(variant, set())
            if tagged - expected:
                problems.append(f"on a {run.name}, the {variant} image gets {sorted(tagged - expected)} on top of its documented {sorted(expected)}")
            if expected - tagged:
                problems.append(f"on a {run.name}, the {variant} image lacks {sorted(expected - tagged)} of its documented {sorted(expected)}")
    return problems


def _strings(node):
    """Every string value of a parsed YAML node."""
    if isinstance(node, dict):
        node = list(node.values())
    if isinstance(node, list):
        for item in node:
            yield from _strings(item)
    elif isinstance(node, str):
        yield node


def docker_tag_violations(workflow_text: str) -> list[str]:
    document = yaml.safe_load(workflow_text)
    variants, problems = variant_metadata(document["jobs"][JOB]["steps"])
    problems += _latest_violations(variants) + _table_violations(variants, GUIDE_TAGS)
    if any("latest-light" in text for text in _strings(document)):
        problems.append("the workflow mentions `latest-light`: there is no such tag, `latest` itself is the light variant")
    return problems


def main_run_tag_violations(workflow_text: str) -> list[str]:
    variants, problems = variant_metadata(pipeline_steps(workflow_text))
    return problems + _table_violations(variants, MAIN_RUN_TAGS)


def prerelease_tag_violations(workflow_text: str) -> list[str]:
    variants, problems = variant_metadata(pipeline_steps(workflow_text))
    return problems + _table_violations(variants, PRERELEASE_TAGS)


def _guarding_metadata(step: dict) -> str | None:
    """The metadata step whose tags an ``if: steps.<id>.outputs.tags != ''`` (bare or in ``${{ }}``) requires; None for any other ``if:``."""
    condition = str(step.get("if") or "").strip()
    wrapped = EXPRESSION_WRAPPER.fullmatch(condition)
    match = TAGS_NOT_EMPTY.fullmatch((wrapped.group(1) if wrapped else condition).strip())
    return match.group(1) if match else None


def build_guard_violations(workflow_text: str) -> list[str]:
    """Every pushing image build runs only when its own metadata step, read from its ``tags:``, yields a tag."""
    steps = pipeline_steps(workflow_text)
    metadata, builds = _metadata_by_id(steps), _indexes(steps, is_image_push)
    if not builds:
        return ["no docker/build-push-action step pushes"]
    problems = []
    for i in builds:
        variant, own = docs_variant(steps[i]), _pushed_metadata(steps[i], metadata)
        if own is None or len(own) != 1:
            problems.append(f"the {variant} image build pushes {own or 'other'} tags, not those of one metadata step: which guard it needs is unknown (step {i})")
        elif "if" not in steps[i]:
            problems.append(f"the {variant} image build has no if: a run where {own[0]} yields no tag fails at its push (step {i})")
        elif _guarding_metadata(steps[i]) != own[0]:
            problems.append(f"the {variant} image build has if: {steps[i]['if']!r}, not exactly steps.{own[0]}.outputs.tags != '' (step {i})")
    return problems


# The tag the in-app update prompt probes before announcing a release (backend/app/services/
# container_registry.py, through frontend/src/lib/features/update-check/updateCheck.ts): the full
# variant's plain version, 1.2.0 on v1.2.0. What an admin is then told to pull must already exist.
PROMPTED_TAG = VERSION
PULLABLE_BEFORE_PROMPT = ("latest", f"{VERSION}-light")


def _release_tags(build: dict, metadata: dict[str, dict]) -> set[str]:
    """The tags an image build pushes on the stable release, through the metadata steps its ``tags:`` reads."""
    return set().union(*(published_tags(metadata[name], STABLE) for name in _pushed_metadata(build, metadata) or []))


def build_order_violations(workflow_text: str) -> list[str]:
    """The build that pushes the prompted tag runs after every build that pushes a tag the prompt leads to."""
    steps = pipeline_steps(workflow_text)
    metadata = _metadata_by_id(steps)
    pushed = {i: _release_tags(steps[i], metadata) for i in _indexes(steps, is_image_push)}
    prompted = [i for i, tags in pushed.items() if PROMPTED_TAG in tags]
    if not prompted:
        return [f"no image build pushes {PROMPTED_TAG} on a {STABLE.name}"]
    problems = []
    for tag in PULLABLE_BEFORE_PROMPT:
        before = [i for i, tags in pushed.items() if tag in tags]
        if not before:
            problems.append(f"no image build pushes {tag} on a {STABLE.name}")
        elif min(prompted) <= max(before):
            problems.append(f"{PROMPTED_TAG} is pushed at step {min(prompted)}, not after {tag} (step {max(before)}): the update prompt probes {PROMPTED_TAG} and would announce a release whose {tag} is not pullable yet")
    return problems


def default_variant_violations(dockerfile_text: str) -> list[str]:
    """``docs_variant`` reads an image build without DOCS_VARIANT as the full image: the Dockerfile must agree."""
    if ("ARG", f"DOCS_VARIANT={DEFAULT_DOCS_VARIANT}") in dockerfile_instructions(dockerfile_text):
        return []
    return [f"the Dockerfile does not default DOCS_VARIANT to {DEFAULT_DOCS_VARIANT}: the image built without it is not the one the version tag promises"]


# ---------------------------------------------------------------------------
# release.yml, R12: only a stable release or main deploys the docs site
# ---------------------------------------------------------------------------

# The public docs site follows stable releases and manual runs from main: never a prerelease, never a nightly.
DEPLOYS = {STABLE: True, RC: False, PLAIN_PRERELEASE: False, NIGHTLY: False, MAIN: True}


def is_docs_deploy(step: dict) -> bool:
    return bool(_runs_dev_py(step, "mkdocs", "deploy"))


def deploy_violations(workflow_text: str) -> list[str]:
    deploys = [step for step in pipeline_steps(workflow_text) if is_docs_deploy(step)]
    if not deploys:
        return ["no step runs `dev.py mkdocs deploy`"]
    problems = []
    for run, expected in DEPLOYS.items():
        deployed = any(holds(step.get("if"), run) for step in deploys)
        if deployed and not expected:
            problems.append(f"on a {run.name}, the docs site is deployed: only a stable release or a manual run from main publishes it")
        elif expected and not deployed:
            problems.append(f"on a {run.name}, the docs site is not deployed")
    return problems


# ---------------------------------------------------------------------------
# release.yml, R12: the release notes pull the published tags
# ---------------------------------------------------------------------------

PULL = re.compile(r"\bdocker pull \S+:(?P<tag>\S+)")
# What the notes tell a user to pull on each release: what that release publishes, `latest` only on a stable one.
NOTES_PULLS = {
    STABLE: {"latest", VERSION, f"{VERSION}-light"},
    RC: {f"{VERSION}-rc.1", f"{VERSION}-rc.1-light"},
    PLAIN_PRERELEASE: {VERSION, f"{VERSION}-light"},
}
# A stand-in for the gh CLI, defined ahead of the step's script so it shadows any real one: `release view`
# returns empty notes and `release edit` prints its --notes. The script itself runs as written, and what it
# prints is what it would append: no network, no token, no writes.
FAKE_GH = """gh() {
  if [ "$1 $2" = "release edit" ]; then
    while [ "$#" -gt 0 ]; do
      if [ "$1" = "--notes" ]; then printf '%s' "$2"; fi
      shift
    done
  fi
}
"""


def edits_release_notes(step: dict) -> bool:
    return any("gh release edit" in line for line in _logical_lines(step))


def release_notes(step: dict, run: Run) -> tuple[str, str | None]:
    """What the step appends to the release notes on ``run``, and why its script failed if it did: ``bash -e``, as GitHub runs it."""
    result = run_script(step, run, FAKE_GH)
    failure = (result.stderr.strip() or f"exit status {result.returncode}") if result.returncode else None
    return result.stdout, failure


def _comment_by(lines: list[str], n: int) -> str:
    """A snippet line's own ``#`` comment and the comment lines right above it."""
    comment = [lines[n].partition("#")[2]]
    while n > 0 and lines[n - 1].lstrip().startswith("#"):
        n -= 1
        comment.append(lines[n])
    return " ".join(comment)


def release_notes_violations(workflow_text: str) -> list[str]:
    """On each release, the notes pull exactly what it publishes, and the comment by ``:latest`` names the light variant."""
    notes = [step for step in pipeline_steps(workflow_text) if edits_release_notes(step)]
    if len(notes) != 1:
        return [f"{len(notes)} steps edit the release notes (`gh release edit`): this test reads exactly one"]
    problems = []
    for run, expected in NOTES_PULLS.items():
        text, failure = release_notes(notes[0], run)
        if failure:
            problems.append(f"on a {run.name}, the release-notes script fails: {failure}")
            continue
        lines = text.splitlines()
        pulls = {n: match["tag"] for n, line in enumerate(lines) if (match := PULL.search(line))}
        if sorted(pulls.values()) != sorted(expected):
            problems.append(f"on a {run.name}, the release notes pull {sorted(pulls.values())}, not {sorted(expected)}")
        problems += [f"on a {run.name}, the comment by `docker pull …:latest` does not name the light variant: {_comment_by(lines, n)!r}" for n, tag in pulls.items() if tag == "latest" and "light" not in _comment_by(lines, n).lower()]
    return problems


# ---------------------------------------------------------------------------
# release.yml, R12: a release's tag matches its kind
# ---------------------------------------------------------------------------

RELEASE_TAG = "github.event.release.tag_name"
RELEASE_PRERELEASE = "github.event.release.prerelease"
# What the guard reads of the release, each only through an env variable: its tag and GitHub's prerelease flag.
GUARD_INPUTS = {RELEASE_TAG: "tag", RELEASE_PRERELEASE: "prerelease flag"}
NON_ZERO_EXIT = re.compile(r"\bexit\s+[1-9]\d*\b")
# The tag guard on each run of the model: run on every release and on no other run, it passes a tag that matches
# the release's kind and fails one that does not, the plain-tag prerelease and the rc-tagged stable release. That
# is the run's first failure, nothing has run before it. PRERELEASE_TAGS, DEPLOYS and NOTES_PULLS still follow the
# plain-tag prerelease past it, the second line should the guard ever be weakened. The rc-tagged stable release
# has none: the docs deploy and the release notes read only the prerelease flag, so past the guard it would deploy
# the docs site and print a `:latest` line, while `latest` and the update prompt ignore its semver prerelease tag.
TAG_GUARD = {STABLE: "success", RC: "success", PLAIN_PRERELEASE: "failure", RC_AS_STABLE: "failure", NIGHTLY: "skipped", MAIN: "skipped"}
# Each kind of release: GitHub's prerelease flag, the tag the developer's rules give it, and the title of the
# guard's ::error on any other tag, which names on the run page the rule the tag broke.
RELEASE_KINDS = {"prerelease": (True, "vX.Y.Z-rc.N", "Prerelease tag"), "stable release": (False, "vX.Y.Z", "Release tag")}
# GitHub's error command, ::error title=…,file=…::message: its parameters end at the first "::".
ERROR_COMMAND = re.compile(r"::error(?: (?P<parameters>.*?))?::")
# The developer's rules as tags, the "v" optional and the whole string: a prerelease is tagged vX.Y.Z-rc.N, a
# stable release a plain vX.Y.Z. A newline within or after the tag is part of it, not a line of its own that
# happens to match (grep accepts both), and quotes or $( ) are text, never shell. By test id: the kind of
# release, its tag, and whether the guard passes it (True) or fails it (False).
TAG_VERDICTS = {
    "prerelease-rc": ("prerelease", "v1.2.0-rc.1", True),
    "prerelease-rc-without-v": ("prerelease", "1.2.0-rc.12", True),
    "prerelease-rc-zero-wide-fields": ("prerelease", "v10.20.30-rc.0", True),
    "prerelease-plain": ("prerelease", "v1.2.0", False),
    "prerelease-beta": ("prerelease", "v1.2.0-beta.1", False),
    "prerelease-rc-without-number": ("prerelease", "v1.2.0-rc", False),
    "prerelease-rc-extra-field": ("prerelease", "v1.2.0-rc.1.2", False),
    "prerelease-capital-v": ("prerelease", "V1.2.0-rc.1", False),
    "prerelease-leading-space": ("prerelease", " v1.2.0-rc.1", False),
    "prerelease-quote-injection": ("prerelease", "v1.2.0-rc.1'; echo pwned; '", False),
    "prerelease-embedded-newline": ("prerelease", "v1.2.0-rc.1\nv9", False),
    "prerelease-trailing-newline": ("prerelease", "v1.2.0-rc.1\n", False),
    "prerelease-command-substitution": ("prerelease", "$(id)", False),
    "prerelease-empty": ("prerelease", "", False),
    "stable-plain": ("stable release", "v1.2.0", True),
    "stable-plain-without-v": ("stable release", "1.2.0", True),
    "stable-plain-wide-fields": ("stable release", "v10.20.30", True),
    "stable-rc": ("stable release", "v1.2.0-rc.1", False),
    "stable-beta": ("stable release", "v1.2.0-beta.1", False),
    "stable-without-patch": ("stable release", "v1.2", False),
    "stable-extra-field": ("stable release", "v1.2.0.1", False),
    "stable-capital-v": ("stable release", "V1.2.0", False),
    "stable-leading-space": ("stable release", " v1.2.0", False),
    "stable-quote-injection": ("stable release", "v1.2.0'; echo pwned; '", False),
    "stable-embedded-newline": ("stable release", "v1.2.0\nv9", False),
    "stable-trailing-newline": ("stable release", "v1.2.0\n", False),
    "stable-command-substitution": ("stable release", "$(id)", False),
    "stable-empty": ("stable release", "", False),
}


def _reads_release_tag(step: dict) -> bool:
    """Whether the release's tag reaches the step's script: a ``${{ }}`` that reads it, in an env value or in the script itself."""
    texts = [*map(str, (step.get("env") or {}).values()), str(step.get("run") or "")]
    return any(RELEASE_TAG in expression for text in texts for expression in EXPRESSION.findall(text))


def is_tag_guard(step: dict) -> bool:
    """A step that can fail a release on its tag: its script reads the tag and exits non-zero (quoted text aside)."""
    return _reads_release_tag(step) and any(NON_ZERO_EXIT.search(QUOTED.sub("_", line)) for line in _logical_lines(step))


def _the_tag_guard(steps: list[dict]) -> tuple[int | None, list[str]]:
    """The index of the one tag guard, or why there is not exactly one."""
    found = _indexes(steps, is_tag_guard)
    if len(found) == 1:
        return found[0], []
    if not found:
        return None, [f"no step reads {RELEASE_TAG} and exits non-zero: a release goes on to build and publish whatever its tag"]
    return None, [f"{len(found)} steps read {RELEASE_TAG} and exit non-zero (steps {found}): this test reads exactly one tag guard"]


def _what(step: dict) -> str:
    """A step, for a message: the action it uses, else its name."""
    return (step.get("uses") or "").partition("@")[0] or repr(step.get("name") or "an unnamed step")


def _tag_guard_trigger_violations(guard: int, step: dict) -> list[str]:
    """The guard's ``if:`` holds on the model's releases, of either kind, and on no other run."""
    condition = f"if: {step['if']!r}" if "if" in step else "no if:"
    problems = []
    for run, outcome in TAG_GUARD.items():
        runs = holds(step.get("if"), run)
        if runs != (outcome != "skipped"):
            problems.append(f"the tag guard (step {guard}) {'runs' if runs else 'does not run'} on a {run.name} ({condition}): it must run on every release and on no other run")
    return problems


def _env_reading(step: dict, path: str) -> list[str]:
    """The step's env variables whose value is exactly ``${{ <path> }}``."""
    exactly = re.compile(r"\$\{\{\s*" + re.escape(path) + r"\s*\}\}")
    return [name for name, value in (step.get("env") or {}).items() if exactly.fullmatch(str(value).strip())]


def _tag_guard_input_violations(guard: int, step: dict) -> list[str]:
    """The tag and the prerelease flag reach the guard's script only through env variables: a ``${{ }}`` in the script pastes its value into the shell source."""
    problems = []
    pasted = list(dict.fromkeys(match.group(0) for match in EXPRESSION.finditer(str(step.get("run") or ""))))
    if pasted:
        problems.append(f"the tag guard (step {guard}) interpolates {pasted} into its script, where a value is shell source: it must read the release through env")
    for path, what in GUARD_INPUTS.items():
        names = _env_reading(step, path)
        if not names:
            problems.append(f"no env variable of the tag guard (step {guard}) is exactly ${{{{ {path} }}}}")
        elif not any(re.search(r"\$\{?" + re.escape(name) + r"\b", line) for name in names for line in _logical_lines(step)):
            problems.append(f"the tag guard's script (step {guard}) never reads {names}: it does not check the {what} it is given")
    return problems


def tag_guard_violations(workflow_text: str) -> list[str]:
    """The one step that reads the release's tag and exits non-zero runs on every release and on no other run, and reads the tag and the prerelease flag only through env."""
    steps = pipeline_steps(workflow_text)
    guard, problems = _the_tag_guard(steps)
    if guard is None:
        return problems
    return _tag_guard_trigger_violations(guard, steps[guard]) + _tag_guard_input_violations(guard, steps[guard])


def tag_guard_position_violations(workflow_text: str) -> list[str]:
    """The guard is the job's first step: a bad tag fails the job before it checks out, installs or caches anything."""
    steps = pipeline_steps(workflow_text)
    guard, problems = _the_tag_guard(steps)
    if guard is not None and guard > 0:
        problems.append(f"the tag guard is step {guard}, after {', '.join(_what(step) for step in steps[:guard])}: it must come before every other step")
    return problems


def _error_titles(lines: list[str]) -> list[str | None]:
    """The ``title`` of each ``::error`` line, None for one without."""
    titles = []
    for line in lines:
        if command := ERROR_COMMAND.match(line):
            parameters = dict(field.split("=", 1) for field in (command["parameters"] or "").split(",") if "=" in field)
            titles.append(parameters.get("title"))
    return titles


def _verdict_problems(step: dict, kind: str, tag: str, accepted: bool) -> list[str]:
    """The guard's script on a ``kind`` of release tagged ``tag``: exit status 0 if ``accepted``, else non-zero with an ``::error`` line titled for the kind."""
    prerelease, rule, title = RELEASE_KINDS[kind]
    result = run_script(step, Run(f"{kind} tagged {tag!r}", "release", tag, prerelease=prerelease))
    lines = f"{result.stdout}\n{result.stderr}".splitlines()
    release = f"a {kind} tagged {tag!r}"
    if accepted:
        return [f"the tag guard rejects {release}: {' | '.join(line for line in lines if line.strip()) or f'exit status {result.returncode}'}"] if result.returncode else []
    if not result.returncode:
        return [f"the tag guard accepts {release}: a {kind} is tagged {rule}"]
    titles = _error_titles(lines)
    if not titles:
        return [f"the tag guard fails {release} without an ::error line, so the run page gives no reason: {lines}"]
    if set(titles) != {title}:
        return [f"the tag guard fails {release} under the ::error title {titles}, not {title!r}: the run page names the wrong rule"]
    return []


def tag_verdict_violations(workflow_text: str, verdicts=None) -> list[str]:
    """The guard's script, run in bash on a release for each of ``verdicts`` (``(kind, tag, accepted)``, all of TAG_VERDICTS by default)."""
    steps = pipeline_steps(workflow_text)
    guard, problems = _the_tag_guard(steps)
    if guard is None:
        return problems
    return [problem for kind, tag, accepted in verdicts or TAG_VERDICTS.values() for problem in _verdict_problems(steps[guard], kind, tag, accepted)]


def first_failure(steps: list[dict], run: Run) -> tuple[int | None, list[int]]:
    """Where ``run`` first fails, and the steps that run before it.

    A tag guard is the one step this model fails (every other is taken to pass), so the walk ends at the last one: past it, a
    ``!cancelled()`` or ``always()`` would need the job's status, which ``holds`` refuses to guess.
    """
    guards, ran = _indexes(steps, is_tag_guard), []
    for i in range(max(guards, default=-1) + 1):
        if not holds(steps[i].get("if"), run):
            continue
        if i in guards and run_script(steps[i], run).returncode:
            return i, ran
        ran.append(i)
    return None, ran


def first_failure_violations(workflow_text: str) -> list[str]:
    """On each run of the model, the job fails where TAG_GUARD says: only the plain-tag prerelease and the rc-tagged stable release, at the guard, with nothing run before it."""
    steps = pipeline_steps(workflow_text)
    problems = []
    for run, outcome in TAG_GUARD.items():
        failed_at, ran = first_failure(steps, run)
        if outcome != "failure":
            if failed_at is not None:
                problems.append(f"on a {run.name}, the job fails at the tag guard (step {failed_at})")
        elif failed_at is None:
            problems.append(f"on a {run.name}, no step fails the job: it goes on to build and publish")
        elif ran:
            problems.append(f"on a {run.name}, {', '.join(_what(steps[i]) for i in ran)} run before the tag guard (step {failed_at}) fails the job")
    return problems


TAG_GUARD_CHECKS = (tag_guard_violations, tag_guard_position_violations, tag_verdict_violations, first_failure_violations)


# ---------------------------------------------------------------------------
# Dockerfile
# ---------------------------------------------------------------------------


@dataclass
class Stage:
    name: str | None
    instructions: list[tuple[str, str]] = field(default_factory=list)


def dockerfile_instructions(text: str) -> list[tuple[str, str]]:
    """``(KEYWORD, arguments)`` per instruction: comments dropped, continuation lines joined."""
    instructions, pending = [], ""
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue  # also inside a continuation, where Docker ignores them too
        if line.endswith("\\"):
            pending += line[:-1] + " "
            continue
        keyword, _, args = (pending + line).partition(" ")
        instructions.append((keyword.upper(), args.strip()))
        pending = ""
    return instructions


def dockerfile_stages(text: str) -> list[Stage]:
    stages: list[Stage] = []
    for keyword, args in dockerfile_instructions(text):
        if keyword == "FROM":
            tokens = [t for t in args.split() if not t.startswith("--")]
            named = len(tokens) >= 3 and tokens[1].lower() == "as"
            stages.append(Stage(name=tokens[2].lower() if named else None))
        elif stages:
            stages[-1].instructions.append((keyword, args))
    return stages


def copy_parts(args: str) -> tuple[dict, list[str], str]:
    """``(flags, sources, destination)`` of a COPY/ADD, shell or JSON form."""
    flags, rest = {}, args.strip()
    while match := re.match(r"--([\w-]+)(?:=(\S*))?\s+", rest):
        flags[match.group(1).lower()] = match.group(2) or ""
        rest = rest[match.end() :]
    paths = json.loads(rest) if rest.startswith("[") else shlex.split(rest)
    return flags, paths[:-1], paths[-1]


def _copies(stage: Stage) -> list[tuple[int, dict, list[str], str]]:
    return [(i, *copy_parts(args)) for i, (keyword, args) in enumerate(stage.instructions) if keyword in ("COPY", "ADD")]


def brings_frontend_build_from_context(flags: dict, sources: list[str]) -> bool:
    """True when the copy takes ``frontend/build`` from the build context, directly or inside a parent."""
    if "from" in flags:
        return False
    for source in sources:
        path = posixpath.normpath(source)
        if path == "." or path.startswith("frontend/build/"):
            return True
        if any(fnmatch.fnmatchcase(target, path) for target in ("frontend", "frontend/build")):
            return True
    return False


def _tokens(args: str) -> list[str]:
    try:
        return shlex.split(args)
    except ValueError:  # an unbalanced quote in some unrelated RUN: plain split is enough here
        return args.split()


def _same_path(a: str, b: str) -> bool:
    return posixpath.normpath(a) == posixpath.normpath(b)


def _build_copy(stage: Stage) -> tuple[int, str] | None:
    """``(instruction index, destination)`` of the stage's last copy of frontend/build from the context."""
    found = [(i, dest) for i, flags, sources, dest in _copies(stage) if brings_frontend_build_from_context(flags, sources)]
    return found[-1] if found else None


def _runs_guard_on(stage: Stage, after: int, directory: str) -> bool:
    """Whether a RUN placed after instruction ``after`` passes ``directory`` to the guard script."""
    for i, (keyword, args) in enumerate(stage.instructions):
        if keyword != "RUN" or i <= after:
            continue
        tokens = _tokens(args)
        if any(token.endswith(GUARD) and _same_path(tokens[j + 1], directory) for j, token in enumerate(tokens[:-1])):
            return True
    return False


def _takes_verified_build(flags: dict, sources: list[str], dest: str, directory: str) -> bool:
    from_guard = flags.get("from", "").lower() == GUARD_STAGE
    return from_guard and posixpath.normpath(dest).endswith("frontend/build") and any(_same_path(source, directory) for source in sources)


def _guard_stage_violations(guard_stage: Stage) -> tuple[str | None, list[str]]:
    """The directory the guard stage copies the build to, and what is wrong with how it checks it."""
    copied = _build_copy(guard_stage)
    if copied is None:
        return None, [f"stage {GUARD_STAGE!r} does not copy frontend/build/ from the build context"]
    copied_at, directory = copied
    if not _runs_guard_on(guard_stage, copied_at, directory):
        return directory, [f"stage {GUARD_STAGE!r} never runs {GUARD} on {directory} after copying the build there"]
    return directory, []


def _bypass_violations(stages: list[Stage], guard_stage: Stage | None) -> list[str]:
    problems = []
    for index, stage in enumerate(stages):
        if stage is guard_stage:
            continue
        for _, flags, sources, dest in _copies(stage):
            if brings_frontend_build_from_context(flags, sources):
                problems.append(f"stage {stage.name or index} copies {sources} -> {dest} from the build context: frontend/build/ would bypass {GUARD}")
    return problems


def dockerfile_violations(text: str) -> list[str]:
    stages = dockerfile_stages(text)
    guard_stage = next((stage for stage in stages if stage.name == GUARD_STAGE), None)
    if guard_stage is None:
        return [f"no `FROM … AS {GUARD_STAGE}` stage", *_bypass_violations(stages, None)]
    directory, problems = _guard_stage_violations(guard_stage)
    final_copies = _copies(stages[-1])
    if directory is None or not any(_takes_verified_build(flags, sources, dest, directory) for _, flags, sources, dest in final_copies):
        problems.append(f"the final stage does not take the verified build: no COPY --from={GUARD_STAGE} <checked dir> ./frontend/build/")
    problems.extend(_bypass_violations(stages, guard_stage))
    return problems


# ---------------------------------------------------------------------------
# release.yml, batch 34: the app version is frozen before every frontend build
# ---------------------------------------------------------------------------

APP_VERSION = "LF_APP_VERSION"
# The step that writes VERSION: «Generate VERSION file for Docker»'s Path('VERSION').write_text(…), or a shell redirection.
WRITES_VERSION_FILE = re.compile(r"""\bPath\(\s*["']VERSION["']\s*\)\.write_text\(|>\s*["']?VERSION\b""")
# LF_APP_VERSION=$(cat VERSION) (or $(< VERSION)) appended to $GITHUB_ENV, where every later step of the job finds it.
EXPORTS_APP_VERSION = re.compile(r"""\bLF_APP_VERSION=["']?\$\((?:cat\s+|<\s*)["']?VERSION["']?\s*\)["']?\s*>>\s*["']?\$\{?GITHUB_ENV\b""")
# LF_APP_VERSION=<whatever> appended to $GITHUB_ENV.
WRITES_APP_VERSION = re.compile(r"""\bLF_APP_VERSION=.*>>\s*["']?\$\{?GITHUB_ENV\b""")
NPM_BUILD = re.compile(r"\bnpm\b.*\srun(?:-script)?\s+build\b")
# The runs that get past the tag guard, each building a frontend.
BUILDING_RUNS = (STABLE, RC, NIGHTLY, MAIN)


def writes_version_file(step: dict) -> bool:
    return any(WRITES_VERSION_FILE.search(line) for line in _logical_lines(step))


def exports_app_version(step: dict) -> bool:
    """Whether the step appends ``LF_APP_VERSION=$(cat VERSION)`` to ``$GITHUB_ENV``."""
    return any(EXPORTS_APP_VERSION.search(line) for line in _logical_lines(step))


def writes_app_version(step: dict) -> bool:
    return any(WRITES_APP_VERSION.search(line) for line in _logical_lines(step))


def builds_frontend(step: dict) -> bool:
    """Whether the step builds or serves the frontend, which bakes ``__APP_VERSION__`` in: ``dev.py front build``, the gallery (its build step rebuilds), ``dev.py server``, ``npm run build``."""
    runs = _runs_dev_py(step, "front", "build") or _runs_dev_py(step, "mkdocs", "gallery") or _runs_dev_py(step, "server")
    return bool(runs) or any(NPM_BUILD.search(line) for line in _logical_lines(step))


def _the_app_version_export(steps: list[dict]) -> tuple[int | None, list[str]]:
    """The index of the one step that exports LF_APP_VERSION from VERSION, and what else writes it to ``$GITHUB_ENV``."""
    exports = _indexes(steps, exports_app_version)
    problems = [f"step {i} ({steps[i].get('name')!r}) writes {APP_VERSION} to $GITHUB_ENV from something other than VERSION: the app would not show the version the image reports" for i in _indexes(steps, writes_app_version) if i not in exports]
    if len(exports) == 1:
        return exports[0], problems
    if exports:
        return None, [*problems, f"{len(exports)} steps export {APP_VERSION} from VERSION (steps {exports}): exactly one freezes it"]
    return None, [*problems, f"no step exports {APP_VERSION}=$(cat VERSION) to $GITHUB_ENV: every frontend build of the job stamps git describe, -dirty included"]


def _app_version_env_violations(document: dict) -> list[str]:
    """An ``env:`` of the workflow, the job or a step that sets LF_APP_VERSION replaces the frozen value."""
    job = document["jobs"][JOB]
    scopes = [("the workflow", document), (f"the job {JOB}", job), *((f"step {i} ({step.get('name')!r})", step) for i, step in enumerate(job["steps"]))]
    return [f"{where} sets {APP_VERSION} in its env: it replaces the version frozen from VERSION" for where, scope in scopes if APP_VERSION in (scope.get("env") or {})]


def _app_version_position_violations(steps: list[dict], export: int) -> list[str]:
    versions, builds = _indexes(steps, writes_version_file), _indexes(steps, builds_frontend)
    if not versions or not builds:
        return ["no step writes VERSION, or none builds the frontend: this test lost its anchors, update it"]
    problems = []
    if export < versions[-1]:
        problems.append(f"{APP_VERSION} is exported at step {export}, before VERSION is written (step {versions[-1]}): it would not hold the version the image reports")
    elif export != versions[-1] + 1:
        problems.append(f"{APP_VERSION} is exported at step {export}, not right after VERSION is written (step {versions[-1]}): the workflow says the frontend's version is frozen in the next step")
    problems += [f"step {i} ({steps[i].get('name')!r}) builds or serves the frontend before {APP_VERSION} is exported (step {export}): git describe decides the version it shows" for i in builds if i < export]
    condition = steps[export].get("if")
    problems += [f"the {APP_VERSION} export (step {export}) is skipped on a {run.name} (if: {condition!r}): that run's frontend builds stamp git describe" for run in BUILDING_RUNS if not holds(condition, run)]
    return problems


def app_version_violations(workflow_text: str) -> list[str]:
    """One step freezes LF_APP_VERSION from VERSION, right after VERSION is written, on every run that builds, before every step that builds or serves the frontend; nothing else sets it."""
    document = yaml.safe_load(workflow_text)
    steps = document["jobs"][JOB]["steps"]
    export, problems = _the_app_version_export(steps)
    problems += _app_version_env_violations(document)
    if export is not None:
        problems += _app_version_position_violations(steps, export)
    return problems


# ---------------------------------------------------------------------------
# frontend/vite.config.ts, batch 34: LF_APP_VERSION before git describe
# ---------------------------------------------------------------------------

# __APP_VERSION__: JSON.stringify(<function>()): the function whose value each build bakes into the sidebar.
APP_VERSION_DEFINE = re.compile(r"__APP_VERSION__\s*:\s*JSON\.stringify\(\s*([A-Za-z_$][\w$]*)\s*\(\s*\)\s*\)")
# What may hide a brace or a word from a scan of TypeScript (string and template literals, comments), and the braces.
JS_TOKEN = re.compile(r"""'(?:[^'\\\n]|\\.)*'|"(?:[^"\\\n]|\\.)*"|`(?:[^`\\]|\\.)*`|//[^\n]*|/\*.*?\*/|[{}]""", re.DOTALL)
READS_APP_VERSION = re.compile(r"""\bprocess\.env(?:\??\.LF_APP_VERSION\b|\[\s*['"]LF_APP_VERSION['"]\s*\])""")
TRIM_CALL = re.compile(r"\.trim\(\s*\)")
GIT_DESCRIBE = re.compile(r"\bgit\s+describe\b")
# The one TypeScript annotation the function has, its return type: `function name(): string {` runs in node as `function name() {`.
RETURN_TYPE = re.compile(r"^(function\s+[\w$]+\s*\([^)]*\))\s*:[^{]*\{")
NODE = shutil.which("node")
# What the stand-in git answers to `git describe`: no frozen value of the cases below equals it.
DESCRIBED = "v1.1.0-3-gabcdef0-dirty"
# By test id: LF_APP_VERSION (None: unset), whether `git describe` succeeds, what the define bakes in, whether git is asked.
APP_VERSION_CASES = {
    "frozen": ("v1.2.0", True, "v1.2.0", False),
    "frozen-with-whitespace": ("  v1.2.0\n", True, "v1.2.0", False),
    "unset": (None, True, DESCRIBED, True),
    "empty": ("", True, DESCRIBED, True),
    "blank": (" \t\n", True, DESCRIBED, True),
    "unset-outside-a-repository": (None, False, "unknown", True),
}
# A stand-in for git, first on PATH: it notes each command line it is given in {calls}, then answers.
FAKE_GIT = """#!/bin/sh
printf '%s\\n' "$*" >> {calls}
{answer}
"""
GIT_DESCRIBES = f"printf '%s\\n' {DESCRIBED}"
GIT_FAILS = "echo 'fatal: not a git repository' >&2\nexit 128"
# The define's function as node runs it: child_process, as vite.config.ts imports it; the function; what the define bakes in.
NODE_HARNESS = """const {{execSync}} = require('child_process');
{function}
process.stdout.write(JSON.stringify({name}()));
"""


def app_version_function(vite_text: str) -> tuple[str | None, str | None]:
    """The function the ``__APP_VERSION__`` define calls: its name, and its source from ``function`` to its closing brace (None when not found)."""
    define = APP_VERSION_DEFINE.search(vite_text)
    if define is None:
        return None, None
    name = define.group(1)
    start = re.search(r"\bfunction\s+" + re.escape(name) + r"\s*\(", vite_text)
    depth = 0
    for token in JS_TOKEN.finditer(vite_text, start.end()) if start else ():
        if token.group() in ("{", "}"):
            depth += 1 if token.group() == "{" else -1
            if depth == 0:
                return name, vite_text[start.start() : token.end()]
    return name, None


def _code(source: str) -> str:
    """``source`` with its comments blanked and its strings kept: ``git describe`` is a string, and a comment may say anything."""
    return JS_TOKEN.sub(lambda token: " " if token.group().startswith(("//", "/*")) else token.group(), source)


def app_version_source_violations(vite_text: str) -> list[str]:
    """The define's function reads LF_APP_VERSION and trims it before it runs ``git describe``. What it returns, and whether it asks git, the node cases run."""
    name, source = app_version_function(vite_text)
    if source is None:
        return [f"no `function {name}(…) {{…}}` behind the __APP_VERSION__ define: this test cannot find what computes the version" if name else "the __APP_VERSION__ define is not JSON.stringify(<function>()): this test cannot find what computes the version"]
    code = _code(source)
    read, describe = READS_APP_VERSION.search(code), GIT_DESCRIBE.search(code)
    if read is None:
        return [f"{name}() never reads process.env.{APP_VERSION}: every build of the release job stamps git describe, -dirty included"]
    if describe is None:
        return [f"{name}() never runs git describe: a build without {APP_VERSION} would show no version"]
    if describe.start() < read.start():
        return [f"{name}() runs git describe before it reads {APP_VERSION}: the frozen version does not come first"]
    if not TRIM_CALL.search(code, read.end(), describe.start()):
        return [f"{name}() does not trim {APP_VERSION} before it runs git describe: a blank value would reach the sidebar instead of git describe's"]
    return []


def app_version_in_node(vite_text: str, workdir: Path, frozen: str | None, git_describes: bool) -> tuple[str, list[str]]:
    """What the ``__APP_VERSION__`` define bakes in, its function run in node as vite.config.ts writes it, with ``LF_APP_VERSION`` set to ``frozen`` (unset for None) and a stand-in git first on PATH; and the command lines git was given."""
    name, source = app_version_function(vite_text)
    assert source is not None, "no function behind the __APP_VERSION__ define: test_the_define_reads_lf_app_version_before_git_describe says why"
    calls, bin_dir, harness = workdir / "git-calls.txt", workdir / "bin", workdir / "app-version.cjs"
    bin_dir.mkdir()
    (bin_dir / "git").write_text(FAKE_GIT.format(calls=shlex.quote(str(calls)), answer=GIT_DESCRIBES if git_describes else GIT_FAILS), encoding="utf-8")
    (bin_dir / "git").chmod(0o755)
    harness.write_text(NODE_HARNESS.format(function=RETURN_TYPE.sub(r"\1 {", source, count=1), name=name), encoding="utf-8")
    env = {key: value for key, value in os.environ.items() if key != APP_VERSION} | {"PATH": f"{bin_dir}{os.pathsep}{os.environ.get('PATH', os.defpath)}"}
    if frozen is not None:
        env[APP_VERSION] = frozen
    result = subprocess.run([NODE, str(harness)], cwd=workdir, env=env, capture_output=True, encoding="utf-8", timeout=60, check=False)
    assert result.returncode == 0, f"node cannot run {name}() as vite.config.ts writes it (TypeScript beyond its return type? update this test): {result.stderr}"
    return json.loads(result.stdout), calls.read_text(encoding="utf-8").splitlines() if calls.exists() else []


# ---------------------------------------------------------------------------
# release.yml, batch 34: the checkout is checked, never gated, after each step that may write to it
# ---------------------------------------------------------------------------

TREE_CHECK = "scripts/ci/warn_if_tree_changed.sh"
TREE_CHECK_SCRIPT = PROJECT_ROOT / TREE_CHECK
# Each check's label, and the step it follows, found by what that step runs (the first that does): placed anywhere
# else, a check would blame the wrong step for a rewritten tracked file.
TREE_CHECK_ANCHORS = {
    "dev.py install": ("`dev.py install`", lambda step: bool(_runs_dev_py(step, "install"))),
    "the frontend build": ("the first `dev.py front build`", lambda step: bool(_runs_dev_py(step, "front", "build"))),
    "the docs build": ("the first `dev.py mkdocs build`", is_docs_build),
    "the gallery": ("the gallery", is_gallery),
}
# GitHub's warning command, ::warning title=…::message: its parameters end at the first "::".
WARNING_COMMAND = re.compile(r"::warning(?: (?P<parameters>.*?))?::(?P<message>.*)")
CHECK_LABEL = "the frontend build"


def runs_tree_check(step: dict) -> bool:
    return any(TREE_CHECK in line for line in _logical_lines(step))


def tree_check_label(step: dict) -> tuple[str | None, str]:
    """The label the step gives the tree check, or why its script is not ``sh <check> <label>`` alone: the one form whose exit status is the check's own, always 0."""
    lines = _logical_lines(step)
    if len(lines) != 1:
        return None, f"runs {lines}: another command beside the tree check could fail the job"
    operators = sorted({operator.strip() for operator in SHELL_CONTROL.findall(QUOTED.sub("_", lines[0]))})
    if operators:
        return None, f"chains the tree check with {operators}: another command could decide the step's exit status"
    tokens = _tokens(lines[0])
    if len(tokens) != 3 or tokens[:2] != ["sh", TREE_CHECK]:
        return None, f"runs {tokens}, not `sh {TREE_CHECK} <label>`"
    return tokens[2], ""


def _tree_check_place_violations(label: str, what: str, anchors: list[int], found: list[int]) -> list[str]:
    if not anchors:
        return [f"no step runs {what}: the check labelled {label!r} has no step to follow, update this test"]
    if not found:
        return [f"no step runs `sh {TREE_CHECK} {label!r}`: a tracked file rewritten by {what} would go unnamed"]
    if found != [anchors[0] + 1]:
        return [f"the check labelled {label!r} is step(s) {found}, not the one right after {what} (step {anchors[0]}): it would blame the wrong step"]
    return []


def tree_check_violations(workflow_text: str) -> list[str]:
    """Each label's check runs ``sh <check> "<label>"`` alone, in the step right after the one it names."""
    steps = pipeline_steps(workflow_text)
    problems, checks = [], {}
    for i in _indexes(steps, runs_tree_check):
        label, why = tree_check_label(steps[i])
        if label is None:
            problems.append(f"step {i} ({steps[i].get('name')!r}) {why}")
        else:
            checks.setdefault(label, []).append(i)
    for label, (what, anchor) in TREE_CHECK_ANCHORS.items():
        problems += _tree_check_place_violations(label, what, _indexes(steps, anchor), checks.get(label, []))
    return problems


def tree_check_script_violations(script_text: str | None) -> list[str]:
    """The script exists, runs in sh, and has no non-zero exit of its own: it warns, it never fails a step."""
    if script_text is None:
        return [f"{TREE_CHECK} does not exist: every [CHECK] step would fail the job"]
    lines = script_text.splitlines()
    problems = [] if lines[:1] == ["#!/bin/sh"] else [f"{TREE_CHECK} starts with {lines[:1]}, not #!/bin/sh"]
    code = [line.strip() for line in lines if line.strip() and not line.strip().startswith("#")]
    return problems + [f"{TREE_CHECK} exits non-zero on its own ({line!r}): the check must warn, never fail the job" for line in code if NON_ZERO_EXIT.search(QUOTED.sub("_", line))]


def hermetic_env(home: Path, **extra: str) -> dict[str, str]:
    """PATH alone, a temporary HOME and no system configuration: no git setting of the developer's reaches the command."""
    return {"PATH": os.environ.get("PATH", os.defpath), "HOME": str(home), "GIT_CONFIG_NOSYSTEM": "1", **extra}


def git(repo: Path, home: Path, *args: str) -> None:
    identity = ("-c", "user.name=Release Contract", "-c", "user.email=release-contract@example.invalid", "-c", "commit.gpgsign=false", "-c", "init.defaultBranch=main")
    result = subprocess.run(["git", *identity, *args], cwd=repo, env=hermetic_env(home), capture_output=True, encoding="utf-8", timeout=30, check=False)
    assert result.returncode == 0, f"git {' '.join(args)}: {result.stderr}"


def tree_check(cwd: Path, home: Path, *args: str, **extra_env: str) -> subprocess.CompletedProcess[str]:
    """The tree check in sh, as the workflow runs it, in ``cwd``."""
    return subprocess.run(["sh", str(TREE_CHECK_SCRIPT), *args], cwd=cwd, env=hermetic_env(home, **extra_env), capture_output=True, encoding="utf-8", timeout=30, check=False)


def warning_commands(output: str) -> list[tuple[str | None, str]]:
    """Each ``::warning`` line of ``output``: its title (None without) and its message."""
    found = []
    for line in output.splitlines():
        if command := WARNING_COMMAND.match(line):
            parameters = dict(item.split("=", 1) for item in (command["parameters"] or "").split(",") if "=" in item)
            found.append((parameters.get("title"), command["message"]))
    return found


# ---------------------------------------------------------------------------
# dev.py, batch 34: npm ci, and icons regenerated only when their source changes
# ---------------------------------------------------------------------------

# npm commands that may rewrite package-lock.json, a tracked file; `npm ci` installs the lock as committed and never writes it.
LOCK_WRITING_NPM = {"install", "i", "add", "update", "up", "upgrade"}
ICON_RECORD = "frontend/generated-icons.json"
# Seconds. A child loads dev.py and runs Pillow on two small logos; a loaded parallel run takes longer, a hang still ends.
CHILD_TIMEOUT = 120
ANSI = re.compile(r"\x1b\[[0-9;]*m")
# A child's script: dev.py (argv[1]) loaded as a module, its main() not run; PROJECT_ROOT pointed at the tree argv[2] and
# GENERATED_ICONS_RECORD at argv[3] in it, both of which dev.py derives from its own location; then the generators argv[4:].
GENERATE_ICONS = textwrap.dedent("""\
    import importlib.util, sys
    from pathlib import Path

    spec = importlib.util.spec_from_file_location("dev_under_test", sys.argv[1])
    dev = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(dev)
    dev.PROJECT_ROOT = Path(sys.argv[2])
    dev.GENERATED_ICONS_RECORD = dev.PROJECT_ROOT / sys.argv[3]
    for name in sys.argv[4:]:
        getattr(dev, name)()
    """)
# A timestamp no write leaves: every file is aged to it before a call, so a write shows whatever the filesystem's granularity.
AGED_NS = 946_684_800 * 10**9  # 2000-01-01T00:00:00Z
# The fill of a logo drawn again: other pixels, so other bytes and another sha256.
OTHER_FILL = (20, 150, 60, 255)


@dataclass(frozen=True)
class Command:
    """A command a function of dev.py runs: what it is passed to, its argv (string literals), its ``cwd=`` as written (None without), its line."""

    runner: str
    argv: tuple[str, ...]
    cwd: str | None
    line: int


@dataclass(frozen=True)
class IconSet:
    """An icon set dev.py generates: its key in the record, its generator, the constant of its recipe, its source and its outputs, from the project root."""

    key: str
    generator: str
    recipe: str
    source: str
    outputs: tuple[str, ...]


FAVICON = IconSet("favicon", "generate_favicon", "FAVICON_RECIPE", "frontend/static/logo.png", ("frontend/static/favicon.png",))
PWA_ICONS = IconSet("pwa-icons", "generate_pwa_icons", "PWA_ICONS_RECIPE", "frontend/static/logo_square.png", tuple(f"frontend/static/icons/{name}.png" for name in ("icon-192", "icon-512", "icon-maskable-192", "icon-maskable-512", "apple-touch-icon")))
ICON_SETS = (FAVICON, PWA_ICONS)
ICON_FILES = (ICON_RECORD, *(path for icon_set in ICON_SETS for path in (icon_set.source, *icon_set.outputs)))


def _argv(call: ast.Call) -> tuple[str, ...] | None:
    """The call's first argument when it is a list of string literals: an argv."""
    first = call.args[0] if call.args else None
    if isinstance(first, ast.List) and all(isinstance(item, ast.Constant) and isinstance(item.value, str) for item in first.elts):
        return tuple(item.value for item in first.elts)
    return None


def dev_commands(dev_text: str, function: str) -> list[Command] | None:
    """Every call in dev.py's ``function`` whose first argument is an argv of string literals, in line order; None when dev.py has no such function."""
    found = next((node for node in ast.parse(dev_text).body if isinstance(node, ast.FunctionDef) and node.name == function), None)
    if found is None:
        return None
    calls = [node for node in ast.walk(found) if isinstance(node, ast.Call) and _argv(node)]
    return sorted((Command(ast.unparse(call.func), _argv(call), next((ast.unparse(keyword.value) for keyword in call.keywords if keyword.arg == "cwd"), None), call.lineno) for call in calls), key=lambda command: command.line)


def _where(command: Command) -> str:
    return f"line {command.line}, cwd={command.cwd}" if command.cwd else f"line {command.line}, in the project root"


def install_violations(dev_text: str) -> list[str]:
    """``cmd_install`` installs the root project tools with ``run_command_live(["npm", "ci"])`` and runs no npm command that may rewrite a lock."""
    commands = dev_commands(dev_text, "cmd_install")
    if commands is None:
        return ["dev.py has no cmd_install"]
    problems = [f"cmd_install runs {' '.join(command.argv)} ({_where(command)}): it may rewrite package-lock.json, a tracked file; `npm ci` installs the lock as committed" for command in commands if command.argv[0] == "npm" and set(command.argv[1:2]) & LOCK_WRITING_NPM]
    if not any(command.runner == "run_command_live" and command.argv == ("npm", "ci") and command.cwd is None for command in commands):
        problems.append('cmd_install does not install the root project tools with run_command_live(["npm", "ci"]) in the project root')
    return problems


def dev_constants(dev_text: str) -> dict[str, object]:
    """dev.py's module-level names bound to a literal constant, read with ast."""
    return {node.targets[0].id: node.value.value for node in ast.parse(dev_text).body if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name) and isinstance(node.value, ast.Constant)}


def recipes_in(dev_text: str) -> dict[str, object]:
    """dev.py's recipe of each icon set, by the name of its constant (None when dev.py has none)."""
    constants = dev_constants(dev_text)
    return {icon_set.recipe: constants.get(icon_set.recipe) for icon_set in ICON_SETS}


def icon_entry(root: Path, icon_set: IconSet, recipes: dict) -> dict:
    """What the record must hold for ``icon_set`` under ``root``: dev.py's recipe, the sha256 of the source as it is there, its path."""
    return {"recipe": recipes.get(icon_set.recipe), "sha256": hashlib.sha256((root / icon_set.source).read_bytes()).hexdigest(), "source": icon_set.source}


def read_record(root: Path) -> dict:
    return json.loads((root / ICON_RECORD).read_text(encoding="utf-8"))


def icon_record_violations(root: Path, recipes: dict) -> list[str]:
    """Under ``root``, the record holds each icon set's recipe and its source's sha256 as they are there, and every output exists: dev.py would regenerate nothing."""
    path = root / ICON_RECORD
    record = json.loads(path.read_text(encoding="utf-8")) if path.is_file() else None
    if not isinstance(record, dict):
        return [f"{ICON_RECORD} is missing or not a JSON object: a fresh checkout regenerates every icon, in the bytes its own Pillow writes"]
    problems = []
    for icon_set in ICON_SETS:
        expected = icon_entry(root, icon_set, recipes)
        if record.get(icon_set.key) != expected:
            problems.append(f"the record's {icon_set.key!r} is {record.get(icon_set.key)!r}, not {expected!r}: a fresh checkout regenerates {', '.join(icon_set.outputs)}")
        problems += [f"{output} is missing: a fresh checkout regenerates the {icon_set.key} set" for output in icon_set.outputs if not (root / output).is_file()]
    return problems


def generate_icons(root: Path, *generators: str) -> str:
    """dev.py's icon generators (both by default, as ``copy_docs_assets`` calls them) on the tree ``root``, in a child interpreter; what they print."""
    env = {name: value for name, value in os.environ.items() if not name.startswith("LIBREFOLIO_")}
    names = generators or tuple(icon_set.generator for icon_set in ICON_SETS)
    child = subprocess.run([sys.executable, "-c", GENERATE_ICONS, str(DEV_PY), str(root), ICON_RECORD, *names], cwd=PROJECT_ROOT, env=env, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, encoding="utf-8", errors="replace", timeout=CHILD_TIMEOUT, check=False)
    output = ANSI.sub("", child.stdout)
    assert child.returncode == 0, output
    return output


def draw_logo(path: Path, fill: tuple[int, ...] = (200, 40, 40, 255)) -> None:
    """logo.png's stand-in: 30x40, not square like the real one, an opaque rectangle on transparency."""
    image = Image.new("RGBA", (30, 40), (0, 0, 0, 0))
    ImageDraw.Draw(image).rectangle((4, 6, 25, 33), fill=fill)
    image.save(path)


def draw_logo_square(path: Path, fill: tuple[int, ...] = (30, 90, 160, 255)) -> None:
    """logo_square.png's stand-in: 40x40, an opaque disc on transparency, so the maskable fit measures real pixels."""
    image = Image.new("RGBA", (40, 40), (0, 0, 0, 0))
    ImageDraw.Draw(image).ellipse((2, 2, 37, 37), fill=fill)
    image.save(path)


def reencode(path: Path) -> None:
    """The same picture in other PNG bytes, as another platform's Pillow may write it."""
    with Image.open(path) as image:
        encoded = io.BytesIO()
        image.save(encoded, format="PNG", compress_level=0)
    assert encoded.getvalue() != path.read_bytes(), f"{path.name}: re-encoding gave the same bytes, pick another encoding"
    path.write_bytes(encoded.getvalue())


def age(root: Path) -> None:
    for path in root.rglob("*"):
        if path.is_file():
            os.utime(path, ns=(AGED_NS, AGED_NS))


def snapshot(root: Path) -> dict[str, tuple[str, int]]:
    """Every file under ``root``: the sha256 of its bytes and its mtime in ns."""
    return {path.relative_to(root).as_posix(): (hashlib.sha256(path.read_bytes()).hexdigest(), path.stat().st_mtime_ns) for path in sorted(root.rglob("*")) if path.is_file()}


def not_rewritten(after: dict[str, tuple[str, int]], outputs: tuple[str, ...]) -> list[str]:
    """The outputs a call did not write: missing, or still at the aged mtime."""
    return [output for output in outputs if after.get(output, ("", AGED_NS))[1] == AGED_NS]


# ---------------------------------------------------------------------------
# Mutations: the same checks on copies that break one rule each
# ---------------------------------------------------------------------------


def mutate_steps(workflow_text: str, mutation) -> str:
    """Apply ``mutation(steps)`` to a parsed copy of the workflow and return it as text."""
    document = copy.deepcopy(yaml.safe_load(workflow_text))
    mutation(document["jobs"][JOB]["steps"])
    return yaml.safe_dump(document, sort_keys=False)


def _post_gallery_index(steps: list[dict], predicate) -> int:
    gallery = max(_indexes(steps, is_gallery))
    after = [i for i in _indexes(steps, predicate) if i > gallery]
    assert after, "mutation anchor missing: the workflow changed shape, update this test"
    return after[0]


def drop_frontend_rebuild(steps: list[dict]) -> None:
    del steps[_post_gallery_index(steps, is_production_front_build)]


def debug_frontend_rebuild(flag: str):
    def mutation(steps: list[dict]) -> None:
        step = steps[_post_gallery_index(steps, is_production_front_build)]
        step["run"] = step["run"].replace("front build", f"front build {flag}")

    return mutation


def instrument_frontend_rebuild(steps: list[dict]) -> None:
    steps[_post_gallery_index(steps, is_production_front_build)]["env"] = {"COVERAGE_INSTRUMENT": "1"}


def move_frontend_rebuild_after_images(steps: list[dict]) -> None:
    step = steps.pop(_post_gallery_index(steps, is_production_front_build))
    steps.insert(max(_indexes(steps, is_image_build)) + 1, step)


def drop_docs_rebuild(steps: list[dict]) -> None:
    del steps[_post_gallery_index(steps, is_docs_build)]


def _edit_report(steps: list[dict], edit, step_id: str = DOCS_REBUILD_ID) -> None:
    reports = [step for step in steps if f"steps.{step_id}.outcome" in (step.get("run") or "")]
    assert reports, f"mutation anchor missing: the report no longer reads steps.{step_id}.outcome"
    for step in reports:
        step["run"] = edit(step["run"])


def _unreport(steps: list[dict], step_id: str) -> None:
    _edit_report(steps, lambda run: "\n".join(line for line in run.splitlines() if f"steps.{step_id}.outcome" not in line), step_id)


def unreport_docs_rebuild(steps: list[dict]) -> None:
    _unreport(steps, DOCS_REBUILD_ID)


def unreport_gallery(steps: list[dict]) -> None:
    _unreport(steps, GALLERY_ID)


def typo_docs_rebuild_in_report(steps: list[dict]) -> None:
    _edit_report(steps, lambda run: run.replace(f"steps.{DOCS_REBUILD_ID}.outcome", "steps.rebuild-mkdoc.outcome"))


# R12 mutations. Anchors are found by what a step does, or by the metadata step ids; an anchor
# that matches nothing, or more than one thing, fails the test instead of mutating nothing.
GALLERY_COMMAND = r"(mkdocs gallery[^\n]*)"  # the gallery's command line, to chain onto
LATEST_COMMENT = r"#[^\\]*(?=\\ndocker pull \S+:latest\\n)"  # the snippet's comment above `docker pull …:latest`
LIGHT_FLAVOR_LATEST = r"latest=[^\n]*"  # the light metadata's flavor line, whatever its value
LATEST_PRINTF_IN_IF = r'[ \t]*if \[ "\$PRERELEASE" != "true" \]; then\n([^\n]*\n)[ \t]*fi\n'  # the `latest` printf, in its if
RC_SUFFIX = re.escape(r"-rc\.[0-9]+$")  # the prerelease regex past the patch number, to its end anchor
STABLE_TAIL = re.escape(r"\.[0-9]+\.[0-9]+") + r"(?=\$)"  # the stable regex's .minor.patch, right before its end anchor (the prerelease one has -rc.N there)
WHOLE_STRING_TEST = r'\[\[ ("\$\w+") =~ (\S+) \]\]'  # each of the tag guard's [[ "$VAR" =~ regex ]]: the variable, the regex
TESTED_VARIABLE = r'"\$\w+"(?= =~)'  # the variable each of the tag guard's [[ =~ ]] tests
FLAG_VARIABLE = r'"\$\w+"(?= = "true" \])'  # the variable the tag guard compares to "true": the prerelease flag
ELSE_BRANCH = r"(?m)^([ \t]*)else\n(?:\1[ \t]+.*\n)+"  # the tag guard's else branch: its line and the lines indented below it
PRERELEASE_ONLY = "github.event_name == 'release' && github.event.release.prerelease"  # the tag guard's if: before the stable branch


def _the_index(steps: list[dict], predicate) -> int:
    found = _indexes(steps, predicate)
    assert len(found) == 1, f"mutation anchor matched {len(found)} steps: the workflow changed shape, update this test"
    return found[0]


def _has_id(step_id: str):
    return lambda step: step.get("id") == step_id


def _cache_keyed(name: str):
    return lambda step: is_cache(step) and f"-{name}-" in str((step.get("with") or {}).get("key"))


def rewrite(predicate, pattern: str, replacement: str, field: str = "run", times: int = 1):
    """A mutation: ``pattern`` → ``replacement``, exactly ``times`` times, in the ``run`` / ``if`` (or the ``with`` input ``field``) of the one step ``predicate`` picks."""

    def mutation(steps: list[dict]) -> None:
        step = steps[_the_index(steps, predicate)]
        holder = step if field in ("run", "if") else step["with"]
        mutated, count = re.subn(pattern, replacement, str(holder[field]))
        assert count == times, f"mutation anchor {pattern!r} matched {count} times, not {times}: the workflow changed shape, update this test"
        holder[field] = mutated

    return mutation


def set_key(predicate, key: str, value):
    def mutation(steps: list[dict]) -> None:
        steps[_the_index(steps, predicate)][key] = value

    return mutation


def drop_key(predicate, key: str):
    def mutation(steps: list[dict]) -> None:
        del steps[_the_index(steps, predicate)][key]

    return mutation


def drop_image_export(steps: list[dict]) -> None:
    del steps[_the_index(steps, exports_runner_image)]


def move_image_export_after_first_cache(steps: list[dict]) -> None:
    step = steps.pop(_the_index(steps, exports_runner_image))
    steps.insert(_indexes(steps, is_cache)[0] + 1, step)


def add_tag(step_id: str, line: str):
    def mutation(steps: list[dict]) -> None:
        inputs = steps[_the_index(steps, _has_id(step_id))]["with"]
        inputs["tags"] = f"{inputs['tags'].rstrip()}\n{line}\n"

    return mutation


def drop_full_latest_flavor(steps: list[dict]) -> None:
    del steps[_the_index(steps, _has_id("meta"))]["with"]["flavor"]


def move_nightly_to_light(steps: list[dict]) -> None:
    full, light = (steps[_the_index(steps, _has_id(step_id))]["with"] for step_id in ("meta", "meta-light"))
    nightly = [line for line in full["tags"].splitlines() if "value=nightly," in line]
    assert len(nightly) == 1, "mutation anchor missing: the full metadata has no raw nightly tag, update this test"
    full["tags"] = full["tags"].replace(nightly[0] + "\n", "")
    light["tags"] += nightly[0] + "\n"


def swap_image_tags(steps: list[dict]) -> None:
    first, second = (steps[i]["with"] for i in _indexes(steps, is_image_build))
    first["tags"], second["tags"] = second["tags"], first["tags"]


def _image_build(variant: str):
    return lambda step: is_image_build(step) and docs_variant(step) == variant


def drop_build_guard(variant: str):
    def mutation(steps: list[dict]) -> None:
        del steps[_the_index(steps, _image_build(variant))]["if"]

    return mutation


def swap_image_builds(steps: list[dict]) -> None:
    first, second = _indexes(steps, is_image_build)
    steps[first], steps[second] = steps[second], steps[first]


def move_full_build_after_frontend_rebuild(steps: list[dict]) -> None:
    """The full build moved up, ahead of the light one: still after the gallery and the production rebuild."""
    build = steps.pop(_the_index(steps, _image_build("full")))
    steps.insert(_post_gallery_index(steps, is_production_front_build) + 1, build)


def move_light_build_before_frontend_rebuild(steps: list[dict]) -> None:
    """The first image build now is the light one: moved between the gallery and the production rebuild."""
    build = steps.pop(_the_index(steps, _image_build("light")))
    steps.insert(_post_gallery_index(steps, is_production_front_build), build)


def drop_gallery_evidence(steps: list[dict]) -> None:
    del steps[_the_index(steps, uploads_gallery_evidence)]


def move_gallery_evidence_before_gallery(steps: list[dict]) -> None:
    step = steps.pop(_the_index(steps, uploads_gallery_evidence))
    steps.insert(_the_index(steps, is_gallery), step)


def drop_tag_guard(steps: list[dict]) -> None:
    del steps[_the_index(steps, is_tag_guard)]


def move_tag_guard_after_the_caches(steps: list[dict]) -> None:
    """The guard moved after checkout, the setup steps and the caches: still there, still failing a bad tag, too late."""
    guard = steps.pop(_the_index(steps, is_tag_guard))
    steps.insert(max(_indexes(steps, is_cache)) + 1, guard)


def assert_rejected(problems: list[str], *fragments: str) -> None:
    """Each fragment names some problem: the copy is rejected, and for the reason the mutation broke."""
    for fragment in fragments:
        assert any(fragment in problem for problem in problems), (fragment, problems)


def mutate_dockerfile(text: str, pattern: str, replacement: str) -> str:
    mutated, count = re.subn(pattern, replacement, text, flags=re.MULTILINE)
    assert count == 1, f"mutation anchor {pattern!r} matched {count} times: the Dockerfile changed shape, update this test"
    return mutated


# Batch 34 mutations: of the workflow's steps, of a file's text, of an icon tree under tmp_path.
APP_VERSION_FROM_GIT = 'echo "LF_APP_VERSION=$(git describe --tags --always --dirty)" >> "$GITHUB_ENV"'


def mutate_text(text: str, pattern: str, replacement: str, what: str) -> str:
    """``pattern`` → ``replacement`` in the text of ``what``, exactly once."""
    mutated, count = re.subn(pattern, replacement, text, flags=re.MULTILINE)
    assert count == 1, f"mutation anchor {pattern!r} matched {count} times: {what} changed shape, update this test"
    return mutated


def insert_before(predicate, step: dict):
    def mutation(steps: list[dict]) -> None:
        steps.insert(_the_index(steps, predicate), dict(step))

    return mutation


def insert_after(predicate, step: dict):
    def mutation(steps: list[dict]) -> None:
        steps.insert(_the_index(steps, predicate) + 1, dict(step))

    return mutation


def move_step(predicate, by: int):
    """A mutation: the one step ``predicate`` picks, moved ``by`` places down."""

    def mutation(steps: list[dict]) -> None:
        i = _the_index(steps, predicate)
        steps.insert(i + by, steps.pop(i))

    return mutation


def drop_app_version_export(steps: list[dict]) -> None:
    del steps[_the_index(steps, exports_app_version)]


def move_app_version_export_after_first_frontend_build(steps: list[dict]) -> None:
    step = steps.pop(_the_index(steps, exports_app_version))
    steps.insert(_indexes(steps, builds_frontend)[0] + 1, step)


def move_app_version_export_before_version_file(steps: list[dict]) -> None:
    step = steps.pop(_the_index(steps, exports_app_version))
    steps.insert(_the_index(steps, writes_version_file), step)


def set_app_version_env_on_the_rebuild(steps: list[dict]) -> None:
    """The production rebuild for the images given an LF_APP_VERSION of its own."""
    steps[_post_gallery_index(steps, is_production_front_build)]["env"] = {APP_VERSION: "${{ github.sha }}"}


def _tree_check(label: str):
    return lambda step: tree_check_label(step)[0] == label


def drop_tree_check(label: str):
    def mutation(steps: list[dict]) -> None:
        del steps[_the_index(steps, _tree_check(label))]

    return mutation


def change_logo(root: Path) -> None:
    draw_logo(root / FAVICON.source, fill=OTHER_FILL)


def bump_recorded_recipe(key: str):
    """A mutation of a tree: the record's recipe for ``key`` one below dev.py's, as right after dev.py bumps it."""

    def mutation(root: Path) -> None:
        record = read_record(root)
        record[key]["recipe"] -= 1
        (root / ICON_RECORD).write_text(json.dumps(record), encoding="utf-8")

    return mutation


def delete_file(relative: str):
    def mutation(root: Path) -> None:
        (root / relative).unlink()

    return mutation


def copy_committed_icons(destination: Path) -> Path:
    """The committed record, logos and icons, copied under ``destination`` at their paths."""
    for relative in ICON_FILES:
        (destination / relative).parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(PROJECT_ROOT / relative, destination / relative)
    return destination


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def workflow_text() -> str:
    return WORKFLOW.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def dockerfile_text() -> str:
    return DOCKERFILE.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def dev_text() -> str:
    return DEV_PY.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def vite_text() -> str:
    return VITE_CONFIG.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def tree_check_text() -> str | None:
    return TREE_CHECK_SCRIPT.read_text(encoding="utf-8") if TREE_CHECK_SCRIPT.is_file() else None


@pytest.fixture(scope="module")
def icon_recipes(dev_text) -> dict:
    """dev.py's FAVICON_RECIPE and PWA_ICONS_RECIPE, read with ast."""
    return recipes_in(dev_text)


@pytest.fixture
def checkout(tmp_path) -> Path:
    """A git repository under tmp_path, one commit holding tracked.txt: a checkout as actions/checkout leaves it."""
    repo = tmp_path / "checkout"
    repo.mkdir()
    (repo / "tracked.txt").write_text("committed\n", encoding="utf-8")
    git(repo, tmp_path, "init", "-q")
    git(repo, tmp_path, "add", "tracked.txt")
    git(repo, tmp_path, "commit", "-q", "-m", "the commit the workflow checks out")
    return repo


@pytest.fixture
def icon_tree(tmp_path) -> Path:
    """A project tree under tmp_path holding only the two logos, synthetic: no icon, no record yet."""
    root = tmp_path / "project"
    (root / "frontend" / "static").mkdir(parents=True)
    draw_logo(root / FAVICON.source)
    draw_logo_square(root / PWA_ICONS.source)
    return root


@pytest.fixture
def generated_icons(icon_tree) -> Path:
    """``icon_tree`` after a first generation, every file aged: a checkout of committed icons and of their record."""
    generate_icons(icon_tree)
    age(icon_tree)
    return icon_tree


class TestReleaseWorkflow:
    def test_frontend_is_rebuilt_for_production_after_the_gallery(self, workflow_text):
        assert frontend_rebuild_violations(workflow_text) == []

    def test_docs_are_rebuilt_after_the_gallery(self, workflow_text):
        assert docs_rebuild_violations(workflow_text) == []

    def test_nightly_report_reads_every_soft_gated_step(self, workflow_text):
        assert soft_failure_report_violations(workflow_text) == []

    @pytest.mark.parametrize(
        "mutation",
        [drop_frontend_rebuild, debug_frontend_rebuild("--debug"), debug_frontend_rebuild("-d"), instrument_frontend_rebuild, move_frontend_rebuild_after_images, move_light_build_before_frontend_rebuild],
        ids=["dropped", "debug-long-flag", "debug-short-flag", "coverage-instrumented", "after-images", "light-build-before-rebuild"],
    )
    def test_frontend_check_fails_on_a_broken_copy(self, workflow_text, mutation):
        problems = frontend_rebuild_violations(mutate_steps(workflow_text, mutation))

        assert any("no production `dev.py front build` between the gallery" in problem for problem in problems), problems

    def test_docs_check_fails_on_a_broken_copy(self, workflow_text):
        problems = docs_rebuild_violations(mutate_steps(workflow_text, drop_docs_rebuild))

        assert any("no `dev.py mkdocs build` between the gallery" in problem for problem in problems), problems

    @pytest.mark.parametrize(
        ("mutation", "expected"),
        [
            (unreport_docs_rebuild, f"the nightly report does not read steps.{DOCS_REBUILD_ID}.outcome"),
            (typo_docs_rebuild_in_report, "the report reads steps.rebuild-mkdoc.outcome but no step has id"),
            # R12: the gallery is soft on dev now, and this generic rule is what makes the report read it.
            (unreport_gallery, f"({GALLERY_ID}) is continue-on-error but the nightly report never reads its outcome"),
        ],
        ids=["unreported", "typo", "gallery-unreported"],
    )
    def test_report_check_fails_on_a_broken_copy(self, workflow_text, mutation, expected):
        problems = soft_failure_report_violations(mutate_steps(workflow_text, mutation))

        assert any(expected in problem for problem in problems), problems

    @pytest.mark.parametrize(
        "check",
        [
            frontend_rebuild_violations,
            docs_rebuild_violations,
            soft_failure_report_violations,
            cache_key_violations,
            gallery_gate_violations,
            gallery_evidence_violations,
            docker_tag_violations,
            main_run_tag_violations,
            prerelease_tag_violations,
            deploy_violations,
            build_guard_violations,
            build_order_violations,
            release_notes_violations,
            tag_guard_violations,
            tag_guard_position_violations,
            tag_verdict_violations,
            first_failure_violations,
            app_version_violations,
            tree_check_violations,
        ],
        ids=lambda check: check.__name__,
    )
    def test_an_unmutated_copy_passes(self, workflow_text, check):
        """A broken copy is rejected for what its mutation broke, not for being a copy."""
        assert check(mutate_steps(workflow_text, lambda steps: None)) == []


class TestCacheKeys:
    def test_every_cache_key_carries_the_runner_image(self, workflow_text):
        assert cache_key_violations(workflow_text) == []

    @pytest.mark.parametrize(
        ("mutation", "expected"),
        [
            (drop_image_export, (f"no step exports {IMAGE_OS}=$ImageOS",)),
            (move_image_export_after_first_cache, ("after the first actions/cache",)),
            (rewrite(exports_runner_image, re.escape("${ImageOS:-unknown}"), "linux"), (f"no step exports {IMAGE_OS}=$ImageOS",)),
            (rewrite(_cache_keyed("pipenv"), re.escape("-${{ env.RUNNER_IMAGE_OS }}-pipenv-"), "-pipenv-", field="key"), ("(Cache Pipenv): key ${{ runner.os }}-pipenv-${{",)),
            (rewrite(_cache_keyed("node"), re.escape("-${{ env.RUNNER_IMAGE_OS }}-node-"), "-node-", field="restore-keys"), ("(Cache NPM): restore-keys ${{ runner.os }}-node- lacks",)),
        ],
        ids=["export-dropped", "export-after-first-cache", "export-a-constant", "pipenv-key-without-image", "npm-restore-key-without-image"],
    )
    def test_cache_key_check_fails_on_a_broken_copy(self, workflow_text, mutation, expected):
        assert_rejected(cache_key_violations(mutate_steps(workflow_text, mutation)), *expected)


class TestGalleryGate:
    def test_a_broken_gallery_fails_a_release(self, workflow_text):
        assert gallery_gate_violations(workflow_text) == []

    @pytest.mark.parametrize(
        ("mutation", "expected"),
        [
            # The fallback this round removed, restored word for word.
            (rewrite(is_gallery, GALLERY_COMMAND, r'\1 || echo "::warning::Gallery had failures — releasing with the screenshots that succeeded"'), ("is chained with ['||']", "downgrades a failure to a ::warning:: annotation")),
            (rewrite(is_gallery, GALLERY_COMMAND, r"\1 || true"), ("is chained with ['||']",)),
            # The default `bash -e` has no pipefail: the pipeline's status is tee's.
            (rewrite(is_gallery, GALLERY_COMMAND, r"\1 | tee gallery.log"), ("is chained with ['|']",)),
            (rewrite(is_gallery, GALLERY_COMMAND, r'\1\necho "gallery done"'), ("is not its step's last command",)),
            (set_key(is_gallery, "continue-on-error", True), ("is continue-on-error True",)),
            # A release runs on its tag, not on main: soft "everywhere but main" is soft on releases.
            (set_key(is_gallery, "continue-on-error", "${{ github.ref_name != 'main' }}"), ("is continue-on-error", "!= 'main'")),
        ],
        ids=["warning-fallback", "or-true", "piped", "not-last", "soft-everywhere", "soft-off-main"],
    )
    def test_gallery_check_fails_on_a_broken_copy(self, workflow_text, mutation, expected):
        assert_rejected(gallery_gate_violations(mutate_steps(workflow_text, mutation)), *expected)

    def test_a_failed_gallery_uploads_its_playwright_report(self, workflow_text):
        assert gallery_evidence_violations(workflow_text) == []

    @pytest.mark.parametrize(
        ("mutation", "expected"),
        [
            # A bare outcome check gets the implicit success(): skipped after the failed release gallery.
            (rewrite(uploads_gallery_evidence, r"!cancelled\(\)\s*&&\s*", "", field="if"), ("the gallery evidence upload has if: \"${{ steps.gallery.outcome == 'failure' }}\"",)),
            (drop_gallery_evidence, ("no actions/upload-artifact step uploads frontend/playwright-report and frontend/test-results",)),
            (move_gallery_evidence_before_gallery, ("the gallery evidence upload runs before the gallery",)),
        ],
        ids=["not-cancelled-dropped", "evidence-step-dropped", "evidence-before-gallery"],
    )
    def test_evidence_check_fails_on_a_broken_copy(self, workflow_text, mutation, expected):
        assert_rejected(gallery_evidence_violations(mutate_steps(workflow_text, mutation)), *expected)


class TestImageTags:
    def test_tags_follow_the_user_guide(self, workflow_text):
        assert docker_tag_violations(workflow_text) == []

    def test_an_image_build_without_docs_variant_is_the_full_image(self, dockerfile_text):
        assert default_variant_violations(dockerfile_text) == []

    def test_default_variant_check_fails_on_a_broken_copy(self, dockerfile_text):
        problems = default_variant_violations(mutate_dockerfile(dockerfile_text, r"^ARG[ \t]+DOCS_VARIANT=full[ \t]*$", "ARG DOCS_VARIANT=light"))

        assert_rejected(problems, f"does not default DOCS_VARIANT to {DEFAULT_DOCS_VARIANT}")

    @pytest.mark.parametrize(
        ("mutation", "expected"),
        [
            (drop_full_latest_flavor, ("(meta) has flavor latest=auto, not latest=false", "on a stable release v1.2.0, the full image gets ['latest']")),
            (add_tag("meta", "type=raw,value=latest,enable=${{ github.ref_name == 'main' }}"), ("(meta) has a raw `latest` tag",)),
            (add_tag("meta-light", "type=raw,value=latest-light,enable=${{ github.ref_name == 'main' }}"), ("mentions `latest-light`",)),
            # The same tag through the flavor: a global suffix that also reaches `latest`.
            (rewrite(_has_id("meta-light"), f"({LIGHT_FLAVOR_LATEST})", r"\1\nsuffix=-light,onlatest=true", field="flavor"), ("on a stable release v1.2.0, the light image gets ['latest-light']",)),
            (rewrite(_has_id("meta"), re.escape("pattern={{version}}"), "pattern=v{{version}}", field="tags"), ("on a stable release v1.2.0, the full image gets ['v1.2.0']", "on a stable release v1.2.0, the full image lacks ['1.2.0']")),
            (rewrite(_has_id("meta-light"), re.escape("pattern={{version}}"), "pattern=v{{version}}", field="tags"), ("on a stable release v1.2.0, the light image gets ['v1.2.0-light']",)),
            (move_nightly_to_light, ("on a nightly, the light image gets ['nightly']", "on a nightly, the full image lacks ['nightly']")),
            # Each metadata step is right, the wiring is not: the full image gets the light tags.
            (swap_image_tags, ("the full variant's metadata (meta-light) has flavor latest=", "on a stable release v1.2.0, the full image gets ['1.2.0-light', 'latest']")),
            (rewrite(_has_id("meta-light"), LIGHT_FLAVOR_LATEST, "latest=false", field="flavor"), ("on a stable release v1.2.0, the light image lacks ['latest']",)),
        ],
        ids=["full-latest-flavor-dropped", "full-raw-latest", "light-raw-latest-light", "light-latest-light-by-flavor", "full-v-version", "light-v-version", "nightly-on-light", "images-swapped", "light-never-latest"],
    )
    def test_tag_check_fails_on_a_broken_copy(self, workflow_text, mutation, expected):
        assert_rejected(docker_tag_violations(mutate_steps(workflow_text, mutation)), *expected)

    def test_a_manual_run_from_main_tags_only_the_light_latest(self, workflow_text):
        assert main_run_tag_violations(workflow_text) == []

    @pytest.mark.parametrize(
        ("mutation", "expected"),
        [
            (rewrite(_has_id("meta-light"), r"type=raw,value=latest,[^\n]*\n", "", field="tags"), ("on a manual run from main, the light image lacks ['latest']",)),
            # The full variant's raw `latest` on main, as it was before this round.
            (add_tag("meta", "type=raw,value=latest,enable=${{ github.ref_name == 'main' }}"), ("on a manual run from main, the full image gets ['latest']",)),
            # A tag invented so the full build has something to push.
            (add_tag("meta", "type=raw,value=main,enable=${{ github.ref_name == 'main' }}"), ("on a manual run from main, the full image gets ['main']",)),
        ],
        ids=["light-latest-dropped", "full-latest-on-main", "full-tag-invented"],
    )
    def test_main_run_check_fails_on_a_broken_copy(self, workflow_text, mutation, expected):
        assert_rejected(main_run_tag_violations(mutate_steps(workflow_text, mutation)), *expected)

    def test_each_image_build_runs_only_when_its_metadata_has_tags(self, workflow_text):
        assert build_guard_violations(workflow_text) == []

    def test_build_guard_check_accepts_the_expression_wrapper(self, workflow_text):
        """``if: ${{ … }}`` and the bare ``if: …`` are the same condition to GitHub, and to this check."""
        wrapped = mutate_steps(workflow_text, rewrite(_image_build("full"), r"^(.*)$", r"${{ \1 }}", field="if"))

        assert build_guard_violations(wrapped) == []

    @pytest.mark.parametrize(
        ("mutation", "expected"),
        [
            (drop_build_guard("full"), ("the full image build has no if: a run where meta yields no tag",)),
            (drop_build_guard("light"), ("the light image build has no if: a run where meta-light yields no tag",)),
            (rewrite(_image_build("full"), re.escape("steps.meta."), "steps.meta-light.", field="if"), ("the full image build has if:", "steps.meta-light.outputs.tags != ''", "not exactly steps.meta.outputs.tags != ''")),
            (rewrite(_image_build("full"), "!=", "==", field="if"), ("the full image build has if:", "steps.meta.outputs.tags == ''")),
        ],
        ids=["full-guard-dropped", "light-guard-dropped", "full-guarded-by-light", "full-guard-inverted"],
    )
    def test_build_guard_check_fails_on_a_broken_copy(self, workflow_text, mutation, expected):
        assert_rejected(build_guard_violations(mutate_steps(workflow_text, mutation)), *expected)

    def test_the_prompted_version_tag_is_pushed_last(self, workflow_text):
        """That both builds come after the gallery and the production rebuild is test_frontend_is_rebuilt_for_production_after_the_gallery."""
        assert build_order_violations(workflow_text) == []

    @pytest.mark.parametrize(
        ("mutation", "expected"),
        [
            (swap_image_builds, ("1.2.0 is pushed at step", "not after latest (step", "not after 1.2.0-light (step")),
            (move_full_build_after_frontend_rebuild, ("not after latest (step", "not after 1.2.0-light (step")),
            # Steps in the right order, tags crossed: the pairing comes from the tags, not the step.
            (swap_image_tags, ("not after latest (step", "not after 1.2.0-light (step")),
        ],
        ids=["builds-swapped-back", "full-build-moved-up", "tags-swapped"],
    )
    def test_push_order_check_fails_on_a_broken_copy(self, workflow_text, mutation, expected):
        assert_rejected(build_order_violations(mutate_steps(workflow_text, mutation)), *expected)


class TestReleaseNotes:
    def test_release_notes_pull_the_documented_tags(self, workflow_text):
        """The step's script runs in bash for a stable release and both prereleases, with a stand-in gh."""
        assert release_notes_violations(workflow_text) == []

    @pytest.mark.parametrize(
        ("mutation", "expected"),
        [
            # The comment before this round, then one that names the wrong variant.
            (rewrite(edits_release_notes, LATEST_COMMENT, "# Install the latest version"), ("on a stable release v1.2.0, the comment by `docker pull …:latest` does not name the light variant",)),
            (rewrite(edits_release_notes, LATEST_COMMENT, "# Latest release, full variant"), ("on a stable release v1.2.0, the comment by `docker pull …:latest` does not name the light variant",)),
            (rewrite(edits_release_notes, re.escape("${TAG_NAME#v}"), "${TAG_NAME}"), ("on a stable release v1.2.0, the release notes pull ['latest', 'v1.2.0', 'v1.2.0-light']",)),
            (rewrite(edits_release_notes, re.escape('"$IMAGE_TAG"'), '"$TAG_NAME"', times=2), ("on a stable release v1.2.0, the release notes pull ['latest', 'v1.2.0', 'v1.2.0-light']",)),
        ],
        ids=["latest-comment-generic", "latest-comment-full", "image-tag-keeps-the-v", "pulls-the-git-tag"],
    )
    def test_release_notes_check_fails_on_a_broken_copy(self, workflow_text, mutation, expected):
        assert_rejected(release_notes_violations(mutate_steps(workflow_text, mutation)), *expected)


class TestPrereleases:
    """The developer's rule: a GitHub prerelease publishes only its own tags, moves no `latest`, deploys no docs site, and its notes pull no `latest`."""

    def test_a_prerelease_publishes_only_its_own_tags(self, workflow_text):
        assert prerelease_tag_violations(workflow_text) == []

    def test_only_a_stable_release_or_main_deploys_the_docs_site(self, workflow_text):
        assert deploy_violations(workflow_text) == []

    @pytest.mark.parametrize(
        ("mutation", "check", "expected"),
        [
            # metadata-action skips 1.2.0-rc.1 by itself, not a prerelease on a plain tag.
            (rewrite(_has_id("meta-light"), LIGHT_FLAVOR_LATEST, "latest=auto", field="flavor"), prerelease_tag_violations, ("on a prerelease v1.2.0 (plain tag), the light image gets ['latest']",)),
            # latest=true reaches the raw tags too.
            (rewrite(_has_id("meta-light"), LIGHT_FLAVOR_LATEST, "latest=true", field="flavor"), docker_tag_violations, ("on a nightly, the light image gets ['latest']",)),
            (
                rewrite(is_docs_deploy, re.escape("(github.event_name == 'release' && !github.event.release.prerelease)"), "github.event_name == 'release'", field="if"),
                deploy_violations,
                ("on a prerelease v1.2.0-rc.1, the docs site is deployed", "on a prerelease v1.2.0 (plain tag), the docs site is deployed"),
            ),
            (rewrite(edits_release_notes, LATEST_PRINTF_IN_IF, r"\1"), release_notes_violations, ("on a prerelease v1.2.0-rc.1, the release notes pull ['1.2.0-rc.1', '1.2.0-rc.1-light', 'latest']", "on a prerelease v1.2.0 (plain tag), the release notes pull ['1.2.0', '1.2.0-light', 'latest']")),
            (
                rewrite(edits_release_notes, re.escape('[ "$PRERELEASE" != "true" ]'), '[ "$PRERELEASE" = "true" ]'),
                release_notes_violations,
                ("on a stable release v1.2.0, the release notes pull ['1.2.0', '1.2.0-light'],", "on a prerelease v1.2.0-rc.1, the release notes pull ['1.2.0-rc.1', '1.2.0-rc.1-light', 'latest']"),
            ),
        ],
        ids=["flavor-literal-auto", "flavor-latest-true", "deploy-on-any-release", "latest-printf-outside-if", "if-inverted"],
    )
    def test_prerelease_rule_fails_on_a_broken_copy(self, workflow_text, mutation, check, expected):
        assert_rejected(check(mutate_steps(workflow_text, mutation)), *expected)


class TestPrereleaseTagGuard:
    """The developer's rules: a prerelease is tagged vX.Y.Z-rc.N and never promoted, the stable release is published on a new, plain vX.Y.Z tag; a release whose tag does not match its kind fails the job at once."""

    def test_the_tag_guard_runs_on_every_release_and_reads_tag_and_flag_through_env(self, workflow_text):
        """Found by what it does: the one step whose script reads the release's tag and exits non-zero. It runs on every release, of either kind, and on no other run."""
        assert tag_guard_violations(workflow_text) == []

    def test_the_tag_guard_is_the_first_step(self, workflow_text):
        assert tag_guard_position_violations(workflow_text) == []

    @pytest.mark.parametrize(("kind", "tag", "accepted"), list(TAG_VERDICTS.values()), ids=list(TAG_VERDICTS))
    def test_the_tag_guard_verdict(self, workflow_text, kind, tag, accepted):
        """The guard's script in bash, the tag and the prerelease flag in its env: exit status 0 for a tag that matches the release's kind, else non-zero with an ::error line titled for that kind."""
        assert tag_verdict_violations(workflow_text, [(kind, tag, accepted)]) == []

    def test_a_tag_of_the_wrong_kind_fails_first_at_the_tag_guard(self, workflow_text):
        """The model's runs: the rc prerelease and the stable release pass the guard, the plain-tag prerelease and the rc-tagged stable release fail there before anything else has run, the others skip it."""
        assert first_failure_violations(workflow_text) == []

    @pytest.mark.parametrize(
        ("mutation", "expected"),
        [
            (drop_tag_guard, (f"no step reads {RELEASE_TAG} and exits non-zero", "on a prerelease v1.2.0 (plain tag), no step fails the job", "on a stable release v1.2.0-rc.1 (rc tag), no step fails the job")),
            # The if: before this round: a stable release skips the guard, whatever its tag.
            (set_key(is_tag_guard, "if", PRERELEASE_ONLY), (f"does not run on a stable release v1.2.0 (if: {PRERELEASE_ONLY!r})", "on a stable release v1.2.0-rc.1 (rc tag), no step fails the job")),
            (drop_key(is_tag_guard, "if"), ("runs on a nightly (no if:)", "runs on a manual run from main (no if:)", "on a nightly, the job fails at the tag guard", "on a manual run from main, the job fails at the tag guard")),
            # The prerelease regex loosened: any suffix passes as a release candidate.
            (rewrite(is_tag_guard, RC_SUFFIX, "-.+$"), ("the tag guard accepts a prerelease tagged 'v1.2.0-beta.1'", "the tag guard accepts a prerelease tagged 'v1.2.0-rc'")),
            # The grep version, back in both branches: it matches any one line of the tag, so a newline smuggles a bad tag through.
            (
                rewrite(is_tag_guard, WHOLE_STRING_TEST, r"printf '%s\\n' \1 | grep -Eq '\2'", times=2),
                ("the tag guard accepts a prerelease tagged 'v1.2.0-rc.1\\nv9'", "the tag guard accepts a prerelease tagged 'v1.2.0-rc.1\\n'", "the tag guard accepts a stable release tagged 'v1.2.0\\nv9'", "the tag guard accepts a stable release tagged 'v1.2.0\\n'"),
            ),
            (rewrite(is_tag_guard, TESTED_VARIABLE, '"${{ github.event.release.tag_name }}"', times=2), ("the tag guard (step 0) interpolates ['${{ github.event.release.tag_name }}'] into its script",)),
            (rewrite(is_tag_guard, FLAG_VARIABLE, '"${{ github.event.release.prerelease }}"'), ("the tag guard (step 0) interpolates ['${{ github.event.release.prerelease }}'] into its script",)),
            # The prerelease check alone, as before this round: a stable release passes, whatever its tag.
            (rewrite(is_tag_guard, ELSE_BRANCH, ""), ("on a stable release v1.2.0-rc.1 (rc tag), no step fails the job", "the tag guard accepts a stable release tagged 'v1.2.0-rc.1'")),
            # A suffix allowed on a stable tag: the release candidate's tag, published as stable, passes.
            (rewrite(is_tag_guard, STABLE_TAIL, r"\g<0>(-.+)?"), ("the tag guard accepts a stable release tagged 'v1.2.0-rc.1'", "the tag guard accepts a stable release tagged 'v1.2.0-beta.1'", "on a stable release v1.2.0-rc.1 (rc tag), no step fails the job")),
            # The stable branch's error copied from the prerelease one, title included: the run page names the wrong rule.
            (rewrite(is_tag_guard, re.escape("title=Release tag::"), "title=Prerelease tag::"), ("the tag guard fails a stable release tagged 'v1.2.0-rc.1' under the ::error title ['Prerelease tag'], not 'Release tag'",)),
            (
                move_tag_guard_after_the_caches,
                ("after actions/checkout, actions/setup-python", "actions/cache: it must come before every other step", "on a prerelease v1.2.0 (plain tag), actions/checkout", "on a stable release v1.2.0-rc.1 (rc tag), actions/checkout", "run before the tag guard"),
            ),
        ],
        ids=["removed", "if-prerelease-only", "if-dropped", "any-suffix", "grep-restored", "tag-in-script", "prerelease-in-script", "stable-branch-dropped", "stable-regex-loosened", "stable-error-titled-as-prerelease", "after-checkout-and-caches"],
    )
    def test_tag_guard_check_fails_on_a_broken_copy(self, workflow_text, mutation, expected):
        mutated = mutate_steps(workflow_text, mutation)

        assert_rejected([problem for check in TAG_GUARD_CHECKS for problem in check(mutated)], *expected)


class TestDockerfile:
    def test_frontend_reaches_the_image_only_through_the_guard(self, dockerfile_text):
        assert dockerfile_violations(dockerfile_text) == []

    @pytest.mark.parametrize(
        ("pattern", "replacement", "expected"),
        [
            # The final stage copies the build from the context again, as before the guard existed.
            (r"--from=frontend[ \t]+/build/[ \t]+\./frontend/build/", "frontend/build/ ./frontend/build/", ("the final stage does not take the verified build", "would bypass")),
            # The guard stage copies the build but never checks it.
            (r"^RUN[ \t]+sh[ \t]+/check_frontend_build\.sh[ \t]+/build[ \t]*\n", "", (f"never runs {GUARD}",)),
            # A parent directory brings frontend/build along: the manifest copy, "simplified".
            (r"^(COPY[ \t].*[ \t])frontend/package\.json[ \t]+\./frontend/package\.json[ \t]*$", r"\1frontend/ ./frontend/", ("would bypass",)),
            # No guard stage at all.
            (r"^(FROM[ \t]+\S+[ \t]+AS[ \t]+)frontend[ \t]*$", r"\1frontend-unchecked", (f"no `FROM … AS {GUARD_STAGE}` stage",)),
        ],
        ids=["final-stage-from-context", "guard-never-runs", "parent-directory-copy", "no-guard-stage"],
    )
    def test_dockerfile_check_fails_on_a_broken_copy(self, dockerfile_text, pattern, replacement, expected):
        problems = dockerfile_violations(mutate_dockerfile(dockerfile_text, pattern, replacement))

        for fragment in expected:
            assert any(fragment in problem for problem in problems), (fragment, problems)

    def test_guard_must_run_after_the_copy(self, dockerfile_text):
        """Checking /build before the build is copied there verifies an empty directory."""
        without_guard = mutate_dockerfile(dockerfile_text, r"^RUN[ \t]+sh[ \t]+/check_frontend_build\.sh[ \t]+/build[ \t]*\n", "")
        guard_first = mutate_dockerfile(without_guard, r"^(FROM[ \t]+\S+[ \t]+AS[ \t]+frontend)[ \t]*$", r"\1\nRUN sh /check_frontend_build.sh /build")

        problems = dockerfile_violations(guard_first)

        assert any(f"never runs {GUARD}" in problem for problem in problems), problems


class TestAppVersion:
    """Batch 34: the version the sidebar shows is frozen from VERSION before every frontend build, and vite.config.ts takes it before git describe."""

    def test_lf_app_version_is_frozen_before_every_frontend_build(self, workflow_text):
        assert app_version_violations(workflow_text) == []

    @pytest.mark.parametrize(
        ("mutation", "expected"),
        [
            (drop_app_version_export, (f"no step exports {APP_VERSION}=$(cat VERSION) to $GITHUB_ENV",)),
            # Frozen from git describe: the -dirty of the 1.1 screenshots, frozen.
            (rewrite(exports_app_version, re.escape("$(cat VERSION)"), "$(git describe --tags --always --dirty)"), (f"writes {APP_VERSION} to $GITHUB_ENV from something other than VERSION", f"no step exports {APP_VERSION}")),
            (insert_after(is_gallery, {"name": "Refresh the app version", "run": APP_VERSION_FROM_GIT}), (f"('Refresh the app version') writes {APP_VERSION} to $GITHUB_ENV from something other than VERSION",)),
            (move_app_version_export_after_first_frontend_build, (f"('Build SvelteKit Frontend') builds or serves the frontend before {APP_VERSION} is exported",)),
            (move_app_version_export_before_version_file, ("before VERSION is written",)),
            (move_step(exports_app_version, 1), ("not right after VERSION is written",)),
            (insert_before(exports_app_version, {"name": "Early bundle", "run": "npm --prefix frontend run build"}), (f"('Early bundle') builds or serves the frontend before {APP_VERSION} is exported",)),
            (insert_before(exports_app_version, {"name": "Smoke server", "run": "pipenv run ./dev.py server --test"}), (f"('Smoke server') builds or serves the frontend before {APP_VERSION} is exported",)),
            (set_key(exports_app_version, "if", "github.event_name == 'release'"), ("is skipped on a nightly", "is skipped on a manual run from main")),
            (set_app_version_env_on_the_rebuild, (f"sets {APP_VERSION} in its env",)),
        ],
        ids=["export-dropped", "export-from-git-describe", "re-exported-from-git-describe", "export-after-first-build", "export-before-version-file", "export-one-step-late", "npm-build-before-export", "server-before-export", "export-on-releases-only", "env-override-on-rebuild"],
    )
    def test_app_version_check_fails_on_a_broken_copy(self, workflow_text, mutation, expected):
        assert_rejected(app_version_violations(mutate_steps(workflow_text, mutation)), *expected)

    def test_the_define_reads_lf_app_version_before_git_describe(self, vite_text):
        assert app_version_source_violations(vite_text) == []

    @pytest.mark.parametrize(
        ("pattern", "replacement", "expected"),
        [
            # The function before batch 34: git describe alone.
            (r"^[ \t]*const frozen = .*\n[ \t]*if \(frozen\) return frozen;\n", "", ("getAppVersion() never reads process.env.LF_APP_VERSION",)),
            # Read in a comment only: a comment is not code.
            (re.escape("const frozen = process.env.LF_APP_VERSION?.trim();"), "// process.env.LF_APP_VERSION?.trim()\n    const frozen = '';", ("getAppVersion() never reads process.env.LF_APP_VERSION",)),
            (re.escape("process.env.LF_APP_VERSION?.trim()"), "process.env.LF_APP_VERSION", ("getAppVersion() does not trim LF_APP_VERSION",)),
            (r"^([ \t]*)(const frozen = )", r"\1const described = execSync('git describe --tags --always --dirty').toString().trim();\n\1\2", ("getAppVersion() runs git describe before it reads LF_APP_VERSION",)),
            (re.escape("JSON.stringify(getAppVersion())"), "JSON.stringify(getGitVersion())", ("no `function getGitVersion(…) {…}` behind the __APP_VERSION__ define",)),
        ],
        ids=["never-read", "read-in-a-comment", "untrimmed", "git-describe-first", "define-calls-another-function"],
    )
    def test_define_check_fails_on_a_broken_copy(self, vite_text, pattern, replacement, expected):
        assert_rejected(app_version_source_violations(mutate_text(vite_text, pattern, replacement, "vite.config.ts")), *expected)

    @pytest.mark.skipif(NODE is None, reason="node is not on PATH: test_the_define_reads_lf_app_version_before_git_describe still reads the source")
    @pytest.mark.parametrize(("frozen", "git_describes", "expected", "git_asked"), list(APP_VERSION_CASES.values()), ids=list(APP_VERSION_CASES))
    def test_the_define_bakes_in_lf_app_version_else_git_describe(self, vite_text, tmp_path, frozen, git_describes, expected, git_asked):
        """The define's function run in node: LF_APP_VERSION trimmed when it is not blank, git never asked then; else git describe, and 'unknown' when git fails."""
        version, asked = app_version_in_node(vite_text, tmp_path, frozen, git_describes)

        assert version == expected
        assert [call.split()[:1] for call in asked] == ([["describe"]] if git_asked else []), asked


class TestCheckoutChecks:
    """Batch 34: what dirties the checkout is named right after the step that did it, by a check that cannot fail the job."""

    def test_each_writing_step_is_followed_by_its_check(self, workflow_text):
        assert tree_check_violations(workflow_text) == []

    @pytest.mark.parametrize(
        ("mutation", "expected"),
        [
            (drop_tree_check("the gallery"), (f"no step runs `sh {TREE_CHECK} 'the gallery'`",)),
            (move_step(_tree_check("the frontend build"), 3), ("the check labelled 'the frontend build' is step(s) [", "not the one right after the first `dev.py front build`")),
            (rewrite(_tree_check("the docs build"), '"the docs build"', '"the gallery"'), (f"no step runs `sh {TREE_CHECK} 'the docs build'`", "the check labelled 'the gallery' is step(s) [")),
            (rewrite(_tree_check("dev.py install"), r'"dev\.py install"', '"dev.py install" || exit 1'), ("chains the tree check with ['||']",)),
            (rewrite(_tree_check("the gallery"), '"the gallery"', '"the gallery"\ngit diff --exit-code'), ("another command beside the tree check could fail the job",)),
            (rewrite(_tree_check("the docs build"), r"^sh ", ""), (f"not `sh {TREE_CHECK} <label>`",)),
        ],
        ids=["gallery-check-dropped", "check-moved-away", "check-mislabelled", "or-exit", "second-command", "not-run-by-sh"],
    )
    def test_check_placement_fails_on_a_broken_copy(self, workflow_text, mutation, expected):
        assert_rejected(tree_check_violations(mutate_steps(workflow_text, mutation)), *expected)

    def test_the_check_script_runs_in_sh_and_only_warns(self, tree_check_text):
        assert tree_check_script_violations(tree_check_text) == []

    @pytest.mark.parametrize(
        ("mutate", "expected"),
        [
            (lambda text: None, (f"{TREE_CHECK} does not exist",)),
            (lambda text: mutate_text(text, r"\A#!/bin/sh$", "#!/bin/bash", TREE_CHECK), ("starts with ['#!/bin/bash'], not #!/bin/sh",)),
            (lambda text: mutate_text(text, r"^exit 0$", "exit 1", TREE_CHECK), ("exits non-zero on its own ('exit 1')",)),
        ],
        ids=["missing", "bash", "exits-1"],
    )
    def test_script_check_fails_on_a_broken_copy(self, tree_check_text, mutate, expected):
        assert_rejected(tree_check_script_violations(mutate(tree_check_text)), *expected)


class TestCheckoutCheckScript:
    """Batch 34: the tree check in sh, on git repositories under tmp_path, with PATH alone and a temporary HOME: whatever it finds, it says so and exits 0."""

    def test_a_clean_checkout_is_reported_unchanged(self, checkout, tmp_path):
        result = tree_check(checkout, tmp_path, CHECK_LABEL)

        assert result.returncode == 0, result
        assert f"Checkout unchanged after {CHECK_LABEL}." in result.stdout.splitlines(), result.stdout
        assert warning_commands(result.stdout + result.stderr) == []

    def test_an_untracked_file_warns_without_dirty(self, checkout, tmp_path):
        (checkout / "new.txt").write_text("not committed\n", encoding="utf-8")

        result = tree_check(checkout, tmp_path, CHECK_LABEL)

        warnings = warning_commands(result.stdout)
        assert result.returncode == 0, result
        assert "?? new.txt" in result.stdout.splitlines(), result.stdout
        assert [title for title, _ in warnings] == [f"Checkout changed after {CHECK_LABEL}"], result.stdout
        assert "1 untracked" in warnings[0][1] and "-dirty" not in warnings[0][1], warnings

    def test_a_rewritten_tracked_file_warns_that_git_describe_reads_dirty(self, checkout, tmp_path):
        (checkout / "tracked.txt").write_text("rewritten by a step\n", encoding="utf-8")
        (checkout / "new.txt").write_text("not committed\n", encoding="utf-8")

        result = tree_check(checkout, tmp_path, CHECK_LABEL)

        warnings = warning_commands(result.stdout)
        assert result.returncode == 0, result
        assert {" M tracked.txt", "?? new.txt"} <= set(result.stdout.splitlines()), result.stdout
        assert [title for title, _ in warnings] == [f"Checkout changed after {CHECK_LABEL}"], result.stdout
        assert "1 tracked path(s) changed and 1 untracked" in warnings[0][1] and "-dirty" in warnings[0][1], warnings

    def test_outside_a_repository_it_warns_and_exits_0(self, tmp_path):
        plain = tmp_path / "not-a-checkout"
        plain.mkdir()

        # git looks no higher than tmp_path: whatever holds the temporary directory, no parent of it is a repository.
        result = tree_check(plain, tmp_path, CHECK_LABEL, GIT_CEILING_DIRECTORIES=str(plain.resolve().parent))

        warnings = warning_commands(result.stdout)
        assert result.returncode == 0, result
        assert [title for title, _ in warnings] == [f"Checkout check failed after {CHECK_LABEL}"], result.stdout
        assert "git status failed" in warnings[0][1], warnings

    def test_without_a_label_it_stops_with_its_usage(self, checkout, tmp_path):
        result = tree_check(checkout, tmp_path)

        assert result.returncode != 0, result
        assert "usage: warn_if_tree_changed.sh <what-just-ran>" in result.stderr, result.stderr


class TestInstall:
    """Batch 34: dev.py install writes no lock file. Read with ast: dev.py is never imported here."""

    def test_install_runs_npm_ci_and_nothing_that_rewrites_a_lock(self, dev_text):
        assert install_violations(dev_text) == []

    @pytest.mark.parametrize(
        ("pattern", "replacement", "expected"),
        [
            # The root install before batch 34.
            (re.escape('run_command_live(["npm", "ci"])'), 'run_command_live(["npm", "install"])', ("cmd_install runs npm install (line", "in the project root)", 'does not install the root project tools with run_command_live(["npm", "ci"])')),
            (re.escape('["npm", "ci"], cwd='), '["npm", "install"], cwd=', ("cmd_install runs npm install (line", "cwd=PROJECT_ROOT / 'frontend')")),
            (re.escape('run_command_live(["npm", "ci"])'), 'run_command_live(["npm", "i"])', ("cmd_install runs npm i (line",)),
        ],
        ids=["root-npm-install", "frontend-npm-install", "root-npm-i"],
    )
    def test_install_check_fails_on_a_broken_copy(self, dev_text, pattern, replacement, expected):
        assert_rejected(install_violations(mutate_text(dev_text, pattern, replacement, "dev.py")), *expected)


class TestIconRegeneration:
    """Batch 34: dev.py's icon generators, in child interpreters on a tree under tmp_path (two synthetic logos), regenerate a set only when one of its outputs is missing or the record does not hold its source's sha256 and its recipe."""

    def test_a_first_generation_writes_every_icon_and_records_each_source(self, icon_tree, icon_recipes):
        generate_icons(icon_tree)

        assert [output for icon_set in ICON_SETS for output in icon_set.outputs if not (icon_tree / output).is_file()] == []
        text = (icon_tree / ICON_RECORD).read_text(encoding="utf-8")
        record = json.loads(text)
        assert {icon_set.key: record.get(icon_set.key) for icon_set in ICON_SETS} == {icon_set.key: icon_entry(icon_tree, icon_set, icon_recipes) for icon_set in ICON_SETS}
        assert isinstance(record.get("_about"), str), record
        assert text == json.dumps(record, indent=2, sort_keys=True, ensure_ascii=False) + "\n", "the record is not written in one canonical form: the same content would not always be the same bytes"

    def test_a_second_call_writes_nothing(self, generated_icons):
        before = snapshot(generated_icons)

        output = generate_icons(generated_icons)

        assert snapshot(generated_icons) == before
        assert "favicon.png is up to date" in output and "PWA icons are up to date" in output, output

    def test_icons_in_another_platforms_bytes_are_left_as_they_are(self, generated_icons):
        """Why the record exists: Pillow does not write the same PNG on every platform. The same pictures in other bytes, sources and record unchanged, stay as they are: the decision is on the source's sha256, never on an output's bytes."""
        for output in (FAVICON.outputs[0], PWA_ICONS.outputs[1]):
            reencode(generated_icons / output)
        age(generated_icons)
        before = snapshot(generated_icons)

        generate_icons(generated_icons)

        assert snapshot(generated_icons) == before

    def test_a_changed_logo_regenerates_the_favicon_alone(self, generated_icons, icon_recipes):
        favicon = generated_icons / FAVICON.outputs[0]
        drawn = favicon.read_bytes()
        change_logo(generated_icons)
        before = snapshot(generated_icons)

        generate_icons(generated_icons)

        after, record = snapshot(generated_icons), read_record(generated_icons)
        assert favicon.read_bytes() != drawn
        assert record.get(FAVICON.key) == icon_entry(generated_icons, FAVICON, icon_recipes)
        assert record.get(PWA_ICONS.key) == icon_entry(generated_icons, PWA_ICONS, icon_recipes)
        assert {output: after[output] for output in PWA_ICONS.outputs} == {output: before[output] for output in PWA_ICONS.outputs}

    def test_a_missing_pwa_icon_regenerates_the_pwa_set_alone(self, generated_icons, icon_recipes):
        delete_file(PWA_ICONS.outputs[2])(generated_icons)
        before = snapshot(generated_icons)

        generate_icons(generated_icons)

        after, record = snapshot(generated_icons), read_record(generated_icons)
        assert not_rewritten(after, PWA_ICONS.outputs) == [], "the PWA set is regenerated as a whole"
        assert after[FAVICON.outputs[0]] == before[FAVICON.outputs[0]]
        assert {icon_set.key: record.get(icon_set.key) for icon_set in ICON_SETS} == {icon_set.key: icon_entry(generated_icons, icon_set, icon_recipes) for icon_set in ICON_SETS}

    @pytest.mark.parametrize("icon_set", ICON_SETS, ids=lambda icon_set: icon_set.key)
    def test_a_recorded_recipe_that_differs_regenerates_that_set_alone(self, generated_icons, icon_recipes, icon_set):
        other = next(candidate for candidate in ICON_SETS if candidate != icon_set)
        bump_recorded_recipe(icon_set.key)(generated_icons)
        age(generated_icons)
        before = snapshot(generated_icons)

        generate_icons(generated_icons)

        after = snapshot(generated_icons)
        assert not_rewritten(after, icon_set.outputs) == []
        assert {output: after[output] for output in other.outputs} == {output: before[output] for output in other.outputs}
        assert read_record(generated_icons).get(icon_set.key) == icon_entry(generated_icons, icon_set, icon_recipes)


class TestCommittedIcons:
    """Batch 34: a fresh checkout holds the record of the committed logos and every icon, so the release runner's Pillow redraws nothing."""

    def test_the_committed_record_holds_the_committed_logos(self, icon_recipes):
        assert icon_record_violations(PROJECT_ROOT, icon_recipes) == []

    def test_git_ignores_neither_the_record_nor_a_logo_nor_an_icon(self, tmp_path):
        result = subprocess.run(["git", "check-ignore", *ICON_FILES], cwd=PROJECT_ROOT, env=hermetic_env(tmp_path), capture_output=True, encoding="utf-8", timeout=30, check=False)
        if result.returncode not in (0, 1):
            pytest.skip(f"git cannot read this tree's ignore rules: {result.stderr.strip()}")

        assert result.stdout.splitlines() == [], "ignored, so missing from a fresh checkout, which regenerates the icons"

    def test_an_unbroken_copy_passes(self, tmp_path, icon_recipes):
        assert icon_record_violations(copy_committed_icons(tmp_path), icon_recipes) == []

    @pytest.mark.parametrize(
        ("mutation", "expected"),
        [
            (change_logo, ("the record's 'favicon' is",)),
            (bump_recorded_recipe(PWA_ICONS.key), ("the record's 'pwa-icons' is",)),
            (delete_file(PWA_ICONS.outputs[4]), (f"{PWA_ICONS.outputs[4]} is missing",)),
            (delete_file(ICON_RECORD), (f"{ICON_RECORD} is missing or not a JSON object",)),
        ],
        ids=["logo-changed", "recipe-differs", "icon-missing", "record-missing"],
    )
    def test_record_check_fails_on_a_broken_copy(self, tmp_path, icon_recipes, mutation, expected):
        root = copy_committed_icons(tmp_path)
        mutation(root)

        assert_rejected(icon_record_violations(root, icon_recipes), *expected)
