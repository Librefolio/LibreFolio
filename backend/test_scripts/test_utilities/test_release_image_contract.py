"""Release images ship a production frontend: the contract between ``release.yml`` and the ``Dockerfile`` (M, R2 P0).

The images are built from the runner's working tree, and the docs gallery runs in the
same job before them. Its Playwright webServer is ``./dev.py server --test``, which
rebuilds ``frontend/build/`` in debug mode (no minification, sourcemaps, ~2.7x the
size), and that build is what reached the published images. It also built the docs
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

Each check is a function over the file's text that returns the list of violations, so
the same functions are run on mutated copies too: a check that cannot fail proves
nothing.

PURE: reads ``.github/workflows/release.yml`` and ``Dockerfile`` and mutates copies in
memory. No DB, no server, no network, no writes.
"""

import copy
import fnmatch
import json
import posixpath
import re
import shlex
from dataclasses import dataclass, field
from pathlib import Path

import pytest
import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[3]
WORKFLOW = PROJECT_ROOT / ".github" / "workflows" / "release.yml"
DOCKERFILE = PROJECT_ROOT / "Dockerfile"

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


def _edit_report(steps: list[dict], edit) -> None:
    reports = [step for step in steps if f"steps.{DOCS_REBUILD_ID}.outcome" in (step.get("run") or "")]
    assert reports, "mutation anchor missing: the report no longer reads the docs rebuild"
    for step in reports:
        step["run"] = edit(step["run"])


def unreport_docs_rebuild(steps: list[dict]) -> None:
    _edit_report(steps, lambda run: "\n".join(line for line in run.splitlines() if f"steps.{DOCS_REBUILD_ID}.outcome" not in line))


def typo_docs_rebuild_in_report(steps: list[dict]) -> None:
    _edit_report(steps, lambda run: run.replace(f"steps.{DOCS_REBUILD_ID}.outcome", "steps.rebuild-mkdoc.outcome"))


def mutate_dockerfile(text: str, pattern: str, replacement: str) -> str:
    mutated, count = re.subn(pattern, replacement, text, flags=re.MULTILINE)
    assert count == 1, f"mutation anchor {pattern!r} matched {count} times: the Dockerfile changed shape, update this test"
    return mutated


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def workflow_text() -> str:
    return WORKFLOW.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def dockerfile_text() -> str:
    return DOCKERFILE.read_text(encoding="utf-8")


class TestReleaseWorkflow:
    def test_frontend_is_rebuilt_for_production_after_the_gallery(self, workflow_text):
        assert frontend_rebuild_violations(workflow_text) == []

    def test_docs_are_rebuilt_after_the_gallery(self, workflow_text):
        assert docs_rebuild_violations(workflow_text) == []

    def test_nightly_report_reads_every_soft_gated_step(self, workflow_text):
        assert soft_failure_report_violations(workflow_text) == []

    @pytest.mark.parametrize(
        "mutation",
        [drop_frontend_rebuild, debug_frontend_rebuild("--debug"), debug_frontend_rebuild("-d"), instrument_frontend_rebuild, move_frontend_rebuild_after_images],
        ids=["dropped", "debug-long-flag", "debug-short-flag", "coverage-instrumented", "after-images"],
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
        ],
        ids=["unreported", "typo"],
    )
    def test_report_check_fails_on_a_broken_copy(self, workflow_text, mutation, expected):
        problems = soft_failure_report_violations(mutate_steps(workflow_text, mutation))

        assert any(expected in problem for problem in problems), problems


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
