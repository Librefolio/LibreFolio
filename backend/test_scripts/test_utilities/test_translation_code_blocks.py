"""Translated code blocks keep the EN indentation: Aphra cleanup, restore and ``code-block-indent`` (M, R2 P0, step 8).

``translate_docs._clean_translation()`` post-processes every LLM translation, and its
step 7 (``re.sub(r'  +', ' ', text)``) ran on the whole document, fenced code
included. Every run of two or more spaces became one: the annotated compose of
``admin/docker_advanced`` lost its nesting (levels 2/4/6/8 collapsed to 0/1, a
broken compose), fences nested in list items and content tabs dropped from column 4
to 1 (lists split, tabs rendered empty), aligned ``# comments`` lost their column and
Markdown hard breaks died. ``validate_translations.check_code_blocks`` compared blocks
by position and filed every difference as LOCALIZED "comments translated or alignment
stripped", so nothing ever turned red.

The approved fix, pinned here before it exists:

* **B**: step 7 collapses runs of 2+ spaces only *between* non-space characters and
  only *outside* fenced code. Indentation and hard breaks survive, while the gap a
  removed ``[N]`` marker leaves still closes.
* **C**: ``_finalize_translation()`` is ``_clean_translation()`` followed by
  ``code_blocks.restore_code_indent()``, which gives every translated block paired
  with its EN block the EN leading whitespace back, line by line, keeping translated
  comments and labels. ``_translate_one_lang`` writes only what it returns.
* **check**: ``translate-validate`` raises ERROR ``code-block-indent``.
* **helper**: ``mkdocs_src/aphra-pipeline/code_blocks.py``, standard library only.
* **corpus guard**: every translation the next alignment will *not* regenerate (EN
  md5 equal to the cached one and the language in ``langs_done``: ``run_translate``'s
  own skip rule) already carries the EN code indentation.

The damaged translations are produced the way production produced them: the old
step 7 (``_flattened``) applied to an ideal translation, which has the EN layout and
translated prose, comments and labels. The expected repair is therefore the ideal
translation inside the blocks, and the damaged text, byte for byte, outside them.
The fixtures mirror real pages: the annotated compose, the "Starting the Test Server"
steps and the ``!!! warning`` volume snippet of ``admin/docker_advanced``, the Mermaid
content tabs of ``user/assets/create-edit``, the HuJSON ACL and the ASCII path of
``admin/service_exposure``.

Red phase: ``code_blocks`` and the new functions do not exist yet, so they are
reached inside fixtures and tests, never at module level. Each test fails on its
own, and the module always collects.

PURE: strings in memory and files under ``tmp_path``, plus a read-only pass over
``mkdocs_src/docs`` and ``.translate-hashes.json``, read with ``json.loads``.
``_load_hashes()`` is never called: it rewrites the tracked cache when it migrates
entries. No DB, no server, no network, no repo writes.
"""

import ast
import dataclasses
import importlib
import inspect
import itertools
import json
import re
import sys
import textwrap
from pathlib import Path

import pytest
import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[3]
PIPELINE_DIR = PROJECT_ROOT / "mkdocs_src" / "aphra-pipeline"
CODE_BLOCKS_PY = PIPELINE_DIR / "code_blocks.py"
CACHE_KEY = "admin/docker_advanced.en.md"

# The defect, verbatim: `_clean_translation()` step 7 before the fix, on the whole document.
_OLD_STEP_7 = re.compile(r"  +")


def _flattened(text: str) -> str:
    """What the pre-fix pipeline wrote: every run of 2+ spaces collapsed to one, code included."""
    return _OLD_STEP_7.sub(" ", text)


# ---------------------------------------------------------------------------
# Fixture pages. EN parts are verbatim Markdown; the Italian page is the EN page
# with IT_STRINGS applied, so every translated line keeps the EN layout exactly.
# A part is a code block when it starts with a fence.
# ---------------------------------------------------------------------------

# admin/docker_advanced, "Customizing docker-compose.yml": levels 0/2/4/6/8, aligned comments.
EN_COMPOSE = """\
```yaml
services:
  librefolio:
    image: librefolio:latest           # Built by ./dev.py docker build
    build:
      context: .
      args:
        UID: ${UID:-1000}              # (1) Match host user UID
        GID: ${GID:-1000}              # (1) Match host user GID
    # No 'user:' directive: the entrypoint starts as root,
    # then drops to the 'librefolio' user via gosu.
    restart: unless-stopped
    ports:
      - "${PORT:-6040}:6040"           # (2) Production port
      - "${TEST_PORT:-6041}:6041"      # (3) Test server port (optional)

    volumes:
      - ./LibreFolio-data:/app/backend/data/prod-docker  # (4) Persistent data
    env_file: .env                     # (5) All config from .env file
```"""
COMPOSE_PARTS = (
    "### 🎮 1. Customizing `docker-compose.yml`",
    "The repository ships a ready-to-use `docker-compose.yml` with annotations:",
    EN_COMPOSE,
    "**Common customizations:**",
)

# admin/docker_advanced, "Starting the Test Server": fences at column 4 inside list items.
EN_STEP_UP = """\
    ```bash
    docker compose up -d
    ```"""
EN_STEP_POPULATE = """\
    ```bash
    ./dev.py docker exec test db populate --force --with-static
    ```"""
EN_STEP_SERVER = """\
    ```bash
    ./dev.py docker exec server --test
    ```"""
STEPS_PARTS = (
    "### Starting the Test Server",
    "1. **Start the container** (the production server starts automatically on `:6040`):",
    EN_STEP_UP,
    "2. **Populate the test database** with mock data:",
    EN_STEP_POPULATE,
    "3. **Start the test server** on port 6041:",
    EN_STEP_SERVER,
    "4. **Access** at **`http://localhost:6041`**",
    "    Test credentials are in the table below.",
)

# admin/docker_advanced, `!!! warning` body: a YAML list at 6 under a fence at 4.
EN_VOLUMES = """\
    ```yaml
    volumes:
      - ./LibreFolio-data:/app/backend/data/prod-docker
      - ./LibreFolio-test-data:/app/backend/data/test    # ← add this
    ```"""
ADMONITION_PARTS = (
    '!!! warning "Test data is ephemeral"',
    "    The test database lives inside the container's writable layer.",
    EN_VOLUMES,
)

# user/assets/create-edit: Mermaid in `=== "Tab"` bodies, flowchart lines at 8, labels translated.
EN_FLOW_MANUAL = """\
    ```mermaid
    flowchart LR
        A[Start: Click '+ New Asset'] --> B[Type a name, ISIN or ticker]
        B --> C{Match found?}
        C -->|Yes| D[Auto-fill the details]
        C -->|No| E[Enter name, category and currency]
        D --> F[Click Save]
        E --> F
    ```"""
EN_FLOW_IMPORT = """\
    ```mermaid
    flowchart LR
        A[Upload a CSV report] --> B{Asset recognized?}
        B -->|Yes| C[Match the existing asset]
        B -->|No| D[Open the pre-filled modal]
    ```"""
TABS_PARTS = (
    "## 🚀 Asset Creation Flows",
    '=== "Manual Creation"',
    EN_FLOW_MANUAL,
    '=== "Broker Import"',
    EN_FLOW_IMPORT,
)

# admin/service_exposure: HuJSON with an aligned `//` comment, in a `???` body.
EN_ACL = """\
    ```json
    {
      "tagOwners": {
        "tag:server": ["autogroup:admin"],  // who may tag a server
      },
      "acls": [
        // Allow the admins to reach every node
        {"action": "accept", "src": ["autogroup:admin"], "dst": ["*:*"]},
      ],
    }
    ```"""
ACL_PARTS = (
    '??? example "Tailscale ACL policy"',
    "    Paste this policy in the Tailscale admin console.",
    EN_ACL,
)

# admin/service_exposure: ASCII art in a tilde fence, aligned by inner spaces.
EN_ASCII_PATH = """\
~~~text
Phone ──► Tailscale ──► LibreFolio
          100.x.y.z     :6040
~~~"""
ASCII_PARTS = ("The request path:", EN_ASCII_PATH)

# A top-level block with an aligned comment: no indentation to give back, one gap to restore.
EN_LOGS = """\
```bash
docker compose logs -f librefolio   # follow the logs
```"""
LOGS_PARTS = ("Follow the server output:", EN_LOGS)

# Blocks that exist on one side only, for the pairing robustness pages.
EN_SECRETS = """\
```yaml
secrets:
  db_password:
    file: ./secrets/db_password.txt
```"""
TR_ONLY_OUTPUT = """\
```text
Container librefolio Started
```"""

IT_STRINGS = {
    # compose
    "### 🎮 1. Customizing `docker-compose.yml`": "### 🎮 1. Personalizzare `docker-compose.yml`",
    "The repository ships a ready-to-use `docker-compose.yml` with annotations:": "Il repository include un `docker-compose.yml` pronto all'uso, con annotazioni:",
    "**Common customizations:**": "**Personalizzazioni comuni:**",
    "# Built by ./dev.py docker build": "# Creata da ./dev.py docker build",
    "# (1) Match host user UID": "# (1) Allinea la UID all'utente host",
    "# (1) Match host user GID": "# (1) Allinea la GID all'utente host",
    "# No 'user:' directive: the entrypoint starts as root,": "# Nessuna direttiva 'user:': l'entrypoint parte come root,",
    "# then drops to the 'librefolio' user via gosu.": "# poi passa all'utente 'librefolio' tramite gosu.",
    "# (2) Production port": "# (2) Porta di produzione",
    "# (3) Test server port (optional)": "# (3) Porta del server di test (opzionale)",
    "# (4) Persistent data": "# (4) Dati persistenti",
    "# (5) All config from .env file": "# (5) Tutta la configurazione dal file .env",
    # steps
    "### Starting the Test Server": "### Avvio del server di test",
    "**Start the container** (the production server starts automatically on `:6040`):": "**Avvia il container** (il server di produzione si avvia automaticamente su `:6040`):",
    "**Populate the test database** with mock data:": "**Popola il database di test** con dati fittizi:",
    "**Start the test server** on port 6041:": "**Avvia il server di test** sulla porta 6041:",
    "**Access** at **`http://localhost:6041`**": "**Accedi** a **`http://localhost:6041`**",
    "Test credentials are in the table below.": "Le credenziali di test sono nella tabella qui sotto.",
    # admonition
    '!!! warning "Test data is ephemeral"': '!!! warning "I dati di test sono effimeri"',
    "The test database lives inside the container's writable layer.": "Il database di test risiede nello strato scrivibile del container.",
    "# ← add this": "# ← aggiungi questa riga",
    # content tabs
    "## 🚀 Asset Creation Flows": "## 🚀 Flussi di creazione degli asset",
    '=== "Manual Creation"': '=== "Creazione manuale"',
    '=== "Broker Import"': '=== "Importazione da broker"',
    "Start: Click '+ New Asset'": "Inizio: clic su '+ Nuovo asset'",
    "Type a name, ISIN or ticker": "Digita un nome, ISIN o ticker",
    "Match found?": "Corrispondenza trovata?",
    "-->|Yes|": "-->|Sì|",
    "Auto-fill the details": "Compila i dettagli in automatico",
    "Enter name, category and currency": "Inserisci nome, categoria e valuta",
    "Click Save": "Fai clic su Salva",
    "Upload a CSV report": "Carica un report CSV",
    "Asset recognized?": "Asset riconosciuto?",
    "Match the existing asset": "Abbina l'asset esistente",
    "Open the pre-filled modal": "Apri la finestra precompilata",
    # HuJSON
    '??? example "Tailscale ACL policy"': '??? example "Policy ACL di Tailscale"',
    "Paste this policy in the Tailscale admin console.": "Incolla questa policy nella console di amministrazione di Tailscale.",
    "// who may tag a server": "// chi può assegnare il tag a un server",
    "// Allow the admins to reach every node": "// Consenti agli amministratori di raggiungere ogni nodo",
    # ASCII path, logs
    "The request path:": "Il percorso della richiesta:",
    "Follow the server output:": "Segui l'output del server:",
    "# follow the logs": "# segui i log",
}


@dataclasses.dataclass(frozen=True)
class Pair:
    """An EN page and its ideal Italian translation: EN layout, translated prose, comments and labels."""

    en: str
    it: str
    en_blocks: tuple[str, ...]
    it_blocks: tuple[str, ...]


def _page(*parts: str) -> str:
    return "\n\n".join(parts) + "\n"


def _is_block(part: str) -> bool:
    return part.lstrip(" ").startswith(("```", "~~~"))


def _translate(text: str) -> str:
    for source, target in IT_STRINGS.items():
        text = text.replace(source, target)
    return text


def _pair(en_parts: tuple[str, ...], it_parts: tuple[str, ...] | None = None) -> Pair:
    """``it_parts`` defaults to ``en_parts``; give it to drop or add blocks on the translated side."""
    translated = tuple(_translate(part) for part in (en_parts if it_parts is None else it_parts))
    return Pair(
        en=_page(*en_parts),
        it=_page(*translated),
        en_blocks=tuple(part for part in en_parts if _is_block(part)),
        it_blocks=tuple(part for part in translated if _is_block(part)),
    )


COMPOSE = _pair(COMPOSE_PARTS)
STEPS = _pair(STEPS_PARTS)
ADMONITION = _pair(ADMONITION_PARTS)
TABS = _pair(TABS_PARTS)
ACL = _pair(ACL_PARTS)
ASCII_PATH = _pair(ASCII_PARTS)
COMBINED = _pair(COMPOSE_PARTS + STEPS_PARTS + ADMONITION_PARTS + TABS_PARTS + ACL_PARTS + ASCII_PARTS + LOGS_PARTS)
# The translation lacks a block the EN page has (same language as the later block, different length):
# pairing by position would match the compose with the secrets snippet and leave it flattened.
EN_ONLY_BLOCK = _pair((*STEPS_PARTS, "Docker secrets are optional:", EN_SECRETS, *COMPOSE_PARTS), (*STEPS_PARTS, *COMPOSE_PARTS))
# The translation has a block the EN page lacks.
TR_ONLY_BLOCK = _pair((*STEPS_PARTS, *COMPOSE_PARTS), (*STEPS_PARTS, "Output atteso:", TR_ONLY_OUTPUT, *COMPOSE_PARTS))

CONSTRUCTS = {
    "compose": COMPOSE,
    "list-steps": STEPS,
    "admonition": ADMONITION,
    "content-tabs": TABS,
    "collapsible-hujson": ACL,
    "tilde-ascii-art": ASCII_PATH,
}
PAGES = {**CONSTRUCTS, "combined": COMBINED, "en-only-block": EN_ONLY_BLOCK, "tr-only-block": TR_ONLY_BLOCK}
CONSTRUCT_PARAMS = [pytest.param(page, id=name) for name, page in CONSTRUCTS.items()]
PAGE_PARAMS = [pytest.param(page, id=name) for name, page in PAGES.items()]


# ---------------------------------------------------------------------------
# Oracles: what the contract implies for the fixtures, computed without the code under test
# ---------------------------------------------------------------------------


def _lead(line: str) -> str:
    return line[: len(line) - len(line.lstrip())]


def _line_of(text: str, fragment: str) -> int:
    """0-based line where ``fragment`` starts; the fixture guarantees it starts a line and occurs once."""
    at = text.find(fragment)
    assert at >= 0 and text.count(fragment) == 1, f"fixture fragment not found exactly once: {fragment[:60]!r}"
    assert at == 0 or text[at - 1] == "\n", f"fixture fragment does not start a line: {fragment[:60]!r}"
    return text.count("\n", 0, at)


def _restored(page: Pair) -> str:
    """The flattened translation with every translated block back to its ideal form, and nothing else touched."""
    flat = _flattened(page.it)
    lines = flat.split("\n")
    for block in page.it_blocks:
        start = _line_of(flat, _flattened(block))
        ideal = block.split("\n")
        lines[start : start + len(ideal)] = ideal
    return "\n".join(lines)


def _changed_lines(before: str, after: str) -> int:
    return sum(old != new for old, new in zip(before.split("\n"), after.split("\n"), strict=True))


def _squeezed(text: str) -> str:
    return re.sub(r"\s+", "", text)


@dataclasses.dataclass(frozen=True)
class Drift:
    """One EN/TR block pair of a 1:1 page, as the flattened translation carries it."""

    en_start: int
    tr_start: int
    en_lines: tuple[str, ...]
    tr_lines: tuple[str, ...]
    lines: tuple[int, ...]  # 0-based TR lines whose leading whitespace differs from EN (non-blank lines)

    @property
    def tr_end(self) -> int:
        return self.tr_start + len(self.tr_lines) - 1


def _drift_table(page: Pair) -> list[Drift]:
    flat = _flattened(page.it)
    rows = []
    for en_block, it_block in zip(page.en_blocks, page.it_blocks, strict=True):
        tr_block = _flattened(it_block)
        tr_start = _line_of(flat, tr_block)
        en_lines, tr_lines = tuple(en_block.split("\n")), tuple(tr_block.split("\n"))
        drifted = tuple(tr_start + k for k, (en, tr) in enumerate(zip(en_lines, tr_lines, strict=True)) if en.strip() and tr.strip() and _lead(en) != _lead(tr))
        rows.append(Drift(_line_of(page.en, en_block), tr_start, en_lines, tr_lines, drifted))
    return rows


def _shape(blocks) -> list[tuple]:
    return [(block.start, block.end, block.indent, block.lang, block.lines, block.closed) for block in blocks]


def _numbers(text: str) -> set[int]:
    return {int(number) for number in re.findall(r"\d+", text)}


def _yaml_body(text: str) -> str:
    """Body of the first ```yaml block of ``text`` (the compose page holds one, at the top level)."""
    lines = text.split("\n")
    start = next(index for index, line in enumerate(lines) if line.strip() == "```yaml")
    end = next(index for index in range(start + 1, len(lines)) if lines[index].strip() == "```")
    return textwrap.dedent("\n".join(lines[start + 1 : end]))


def _yaml_or_error(body: str) -> object:
    try:
        return yaml.safe_load(body)
    except yaml.YAMLError as exc:
        return f"unparseable YAML ({type(exc).__name__})"


def _foreign_imports(source: str) -> list[str]:
    """Every imported top-level module that is not in the standard library (relative imports included)."""
    allowed = set(sys.stdlib_module_names) | {"__future__"}
    found = set()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            found.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            found.add("." * node.level + (node.module or "").split(".")[0])
    return sorted(found - allowed)


def _call_name(call: ast.Call) -> str:
    return call.func.id if isinstance(call.func, ast.Name) else getattr(call.func, "attr", "")


def _source_argument(call: ast.Call) -> str:
    """What a ``_finalize_translation`` call passes as ``source_text`` (first positional, or the keyword)."""
    node = call.args[0] if call.args else next((keyword.value for keyword in call.keywords if keyword.arg == "source_text"), None)
    return ast.unparse(node) if node is not None else ""


def _llm_output(page: Pair) -> str:
    """A raw LLM answer for ``page``: blocks flattened, a glossary marker in the prose, the glossary block at the end."""
    anchor = "`docker-compose.yml` pronto"
    assert page.it.count(anchor) == 1, "fixture: the glossary marker needs a unique anchor"
    raw = _flattened(page.it).replace(anchor, "`docker-compose.yml` [1] pronto")
    return raw + "\n[1] Docker Compose: lo strumento che avvia i container.\n"


def _ranges(numbers) -> str:
    spans: list[list[int]] = []
    for number in sorted(numbers):
        if spans and number == spans[-1][1] + 1:
            spans[-1][1] = number
        else:
            spans.append([number, number])
    return ", ".join(str(first) if first == last else f"{first}-{last}" for first, last in spans)


# ---------------------------------------------------------------------------
# Pipeline modules. The scripts import each other by bare name, as dev.py loads them;
# they are reached only through these fixtures, so a missing module fails each test
# that needs it instead of the whole collection.
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def pipeline_on_path():
    with pytest.MonkeyPatch.context() as mp:
        mp.syspath_prepend(str(PIPELINE_DIR))
        yield PIPELINE_DIR


def _load(name: str):
    module = importlib.import_module(name)
    origin = Path(module.__file__).resolve()
    assert origin.parent == PIPELINE_DIR, f"{name} resolved to {origin}, not to the pipeline script"
    return module


@pytest.fixture(scope="module")
def code_blocks(pipeline_on_path):
    return _load("code_blocks")


@pytest.fixture(scope="module")
def translate_docs(pipeline_on_path):
    return _load("translate_docs")


@pytest.fixture(scope="module")
def validate_translations(pipeline_on_path):
    return _load("validate_translations")


# ---------------------------------------------------------------------------
# Fixture self-check
# ---------------------------------------------------------------------------


class TestFixtures:
    def test_fixtures_exercise_the_defect(self):
        """Not a product contract: a key of IT_STRINGS that translates nothing, or a page the defect leaves intact, would let the other tests pass for the wrong reason."""
        en_text = "".join(page.en for page in PAGES.values())
        assert [key for key in IT_STRINGS if key not in en_text] == [], "IT_STRINGS keys that translate nothing"
        for name, page in PAGES.items():
            assert all(block in page.en for block in page.en_blocks), name
            assert all(block in page.it for block in page.it_blocks), name
            assert any(_flattened(block) != block for block in page.it_blocks), f"{name}: the defect damages no block"
            assert _restored(page).count("\n") == page.it.count("\n"), name


# ---------------------------------------------------------------------------
# code_blocks.py
# ---------------------------------------------------------------------------


class TestCodeBlocksModule:
    def test_imports_only_the_standard_library(self):
        """dev.py wraps the translate-command imports in `except ImportError: pass`: one third-party import and the commands vanish silently."""
        assert _foreign_imports("import os.path\nfrom re import sub\nimport yaml\nfrom . import sibling\n") == [".", "yaml"], "the detector itself"
        assert CODE_BLOCKS_PY.is_file(), f"{CODE_BLOCKS_PY.relative_to(PROJECT_ROOT)} does not exist yet"
        foreign = _foreign_imports(CODE_BLOCKS_PY.read_text(encoding="utf-8"))
        assert foreign == [], f"code_blocks.py imports {foreign}: dev.py would drop the translate commands without a word"

    def test_fenced_block_is_a_frozen_dataclass(self, code_blocks):
        (block,) = code_blocks.parse_fenced_blocks("```bash\necho hi\n```")
        assert isinstance(block, code_blocks.FencedBlock)
        assert {"start", "end", "indent", "lang", "lines", "closed"} <= {field.name for field in dataclasses.fields(block)}
        with pytest.raises(dataclasses.FrozenInstanceError):
            block.start = 1


PARSE_DOC = "\n".join(
    [
        "# Title",  # 0
        "",  # 1
        '```yaml title="docker-compose.yml"',  # 2  lang is the first word of the info string
        "services:",  # 3
        "  app: {}",  # 4
        "```",  # 5
        "",  # 6
        "1. Start the container:",  # 7
        "",  # 8
        "    ```bash",  # 9  list item, column 4
        "    docker compose up -d",  # 10
        "    ```",  # 11
        "",  # 12
        '=== "Manual"',  # 13
        "",  # 14
        "    ~~~Mermaid",  # 15  content tab, tilde fence, lang lower-cased
        "    flowchart LR",  # 16
        "        A --> B",  # 17
        "    ~~~",  # 18
        "",  # 19
        '!!! note "Heads up"',  # 20
        "",  # 21
        "    ```",  # 22  admonition, no info string
        "    plain text",  # 23
        "    ```",  # 24
        "",  # 25
        '??? tip "Nested fences"',  # 26
        "",  # 27
        "    ````markdown",  # 28  collapsible admonition, 4-backtick fence
        "    ```python",  # 29  shorter fence with an info string: content
        '    print("inner fence")',  # 30
        "    ```",  # 31  shorter bare fence: content, does not close
        "    ````",  # 32  closes
        "",  # 33
        "Done.",  # 34
    ]
)

CLOSING_DOC = "\n".join(
    [
        "```text",  # 0  opens with 3 backticks
        "~~~",  # 1  the other fence character: content
        "```python",  # 2  something after the fence: content, not a closer
        "`````",  # 3  a longer fence of the same character closes
        "",  # 4
        "~~~~",  # 5  opens with 4 tildes, no info string
        "~~~",  # 6  shorter: content
        "~~~~~   ",  # 7  longer, followed by whitespace only: closes
        "after",  # 8
    ]
)


class TestParseFencedBlocks:
    def test_finds_fences_at_any_indentation(self, code_blocks):
        lines = PARSE_DOC.split("\n")
        assert _shape(code_blocks.parse_fenced_blocks(PARSE_DOC)) == [
            (2, 5, "", "yaml", tuple(lines[2:6]), True),
            (9, 11, "    ", "bash", tuple(lines[9:12]), True),
            (15, 18, "    ", "mermaid", tuple(lines[15:19]), True),
            (22, 24, "    ", "", tuple(lines[22:25]), True),
            (28, 32, "    ", "markdown", tuple(lines[28:33]), True),
        ]

    def test_closes_only_on_a_long_enough_bare_fence_of_the_same_character(self, code_blocks):
        lines = CLOSING_DOC.split("\n")
        assert _shape(code_blocks.parse_fenced_blocks(CLOSING_DOC)) == [
            (0, 3, "", "text", tuple(lines[0:4]), True),
            (5, 7, "", "", tuple(lines[5:8]), True),
        ]

    def test_an_unclosed_fence_runs_to_the_last_line(self, code_blocks):
        text = "\n".join(["Intro", "", "```bash", "echo one", "echo two"])
        assert _shape(code_blocks.parse_fenced_blocks(text)) == [(2, 4, "", "bash", ("```bash", "echo one", "echo two"), False)]


class TestCodeLineMask:
    @pytest.mark.parametrize(
        ("text", "mask"),
        [
            pytest.param(
                "\n".join(["Intro", "```bash", "echo hi", "```", "Middle", "    ```yaml", "    a: 1", "    b: 2"]),
                [False, True, True, True, False, True, True, True],
                id="unclosed-block-masks-to-the-end",
            ),
            pytest.param("a\n```\nx\n```\n", [False, True, True, True, False], id="one-entry-per-split-line"),
        ],
    )
    def test_marks_every_line_of_every_block_fences_included(self, code_blocks, text, mask):
        assert code_blocks.code_line_mask(text) == mask


# Pairing fixtures. "Twin" = a block of the same language and length placed before the true
# counterpart and missing from the translation: pairing in order would pick the twin.
M1_EN = """\
```mermaid
flowchart LR
    A[Prices] --> B[Indicator]
    B --> C[Signal]
```"""
M1_IT = """\
```mermaid
flowchart LR
 A[Prezzi] --> B[Indicatore]
 B --> C[Segnale]
```"""
M2_EN = """\
```mermaid
flowchart TD
    D[Report] --> E[Export]
    E --> F[Archive]
    F --> G[Done]
```"""
M2_IT = """\
```mermaid
flowchart TD
 D[Report] --> E[Esportazione]
 E --> F[Archivio]
 F --> G[Fatto]
```"""
UP_EN = """\
```bash
docker compose up -d   # start in the background
```"""
UP_IT = """\
```bash
docker compose up -d # avvia in background
```"""
PULL_EN = """\
```bash
docker compose pull
```"""
MAKE_EN = """\
```bash
make docs
```"""
NOTE_IT = """\
```text
Output atteso
```"""
PORTS_EN = """\
```yaml
ports:
  - 6040:6040
  - 6041:6041
```"""
VOLUMES_EN = """\
```yaml
# Persistent data lives here
volumes:
  - ./data:/app/data
```"""
VOLUMES_IT = """\
```yaml
# I dati persistenti stanno qui
volumes:
 - ./data:/app/data
```"""
SSH_ADMIN_EN = """\
```bash
ssh admin@librefolio.example
```"""
SSH_EN = """\
```bash
ssh <user>@<tailscale_ip>
```"""
SSH_IT = """\
```bash
ssh <utente>@<ip_tailscale>
```"""

PAIR_CASES = [
    pytest.param(_page(PULL_EN, UP_EN), _page(UP_IT), [(1, 0)], id="inline-comment-translated-after-en-only-twin"),
    pytest.param(_page(PORTS_EN, VOLUMES_EN), _page(VOLUMES_IT), [(1, 0)], id="comment-line-translated-after-en-only-twin"),
    pytest.param(_page(SSH_ADMIN_EN, SSH_EN), _page(SSH_IT), [(1, 0)], id="placeholders-differ-after-en-only-twin"),
    pytest.param(_page(M1_EN, M2_EN), _page(M1_IT, M2_IT), [(0, 0), (1, 1)], id="translated-labels-pair-in-order"),
    pytest.param(_page(M1_EN, MAKE_EN, M2_EN), _page(M1_IT, M2_IT), [(0, 0), (2, 1)], id="en-only-block-between-translated-labels"),
    pytest.param(_page(UP_EN, M2_EN), _page(UP_IT, NOTE_IT, M2_IT), [(0, 0), (1, 2)], id="tr-only-block-before-translated-labels"),
    pytest.param(COMBINED.en, _flattened(COMBINED.it), [(k, k) for k in range(len(COMBINED.en_blocks))], id="combined-page-flattened"),
    pytest.param(EN_ONLY_BLOCK.en, _flattened(EN_ONLY_BLOCK.it), [(0, 0), (1, 1), (2, 2), (4, 3)], id="en-only-block-before-the-compose"),
    pytest.param(TR_ONLY_BLOCK.en, _flattened(TR_ONLY_BLOCK.it), [(0, 0), (1, 1), (2, 2), (3, 4)], id="tr-only-block-before-the-compose"),
]


class TestPairBlocks:
    @pytest.mark.parametrize(("en", "tr", "expected"), PAIR_CASES)
    def test_pairs_each_block_with_its_true_counterpart(self, code_blocks, en, tr, expected):
        pairs = code_blocks.pair_blocks(code_blocks.parse_fenced_blocks(en), code_blocks.parse_fenced_blocks(tr))
        assert all(a[0] < b[0] and a[1] < b[1] for a, b in itertools.pairwise(pairs)), f"not monotonic: {pairs}"
        assert pairs == expected


SMALL_YAML_EN = "```yaml\nfoo:\n  bar: 1\n```"
UNCLOSED_TR_TAIL = "\n```yaml\nfoo:\n bar: 1\n baz: 2"  # a truncated answer: same length as the EN block, no closing fence
LONGER_COMPOSE_TR = _flattened(_translate(EN_COMPOSE)).replace("\n restart:", "\n # riavvio automatico\n restart:")
MISALIGNED = [
    pytest.param(_page(EN_STEP_UP, EN_COMPOSE), _page(_flattened(EN_STEP_UP), LONGER_COMPOSE_TR), _page(EN_STEP_UP, LONGER_COMPOSE_TR), id="translated-block-has-an-extra-line"),
    pytest.param(_page(EN_STEP_UP, SMALL_YAML_EN), _page(_flattened(EN_STEP_UP)) + UNCLOSED_TR_TAIL, _page(EN_STEP_UP) + UNCLOSED_TR_TAIL, id="translated-block-is-unclosed"),
]


class TestRestoreCodeIndent:
    @pytest.mark.parametrize("page", PAGE_PARAMS)
    def test_gives_back_the_en_layout_and_keeps_the_translation(self, code_blocks, page):
        """Inside paired blocks: EN leading whitespace (and EN gap before a same-code comment); outside them: nothing moves, not even flattened prose."""
        flat = _flattened(page.it)
        expected = _restored(page)
        out, changed = code_blocks.restore_code_indent(page.en, flat)
        assert _squeezed(out) == _squeezed(flat), "only whitespace may change"
        assert out == expected
        assert changed == _changed_lines(flat, expected)

    @pytest.mark.parametrize("page", PAGE_PARAMS)
    def test_is_idempotent(self, code_blocks, page):
        once, _ = code_blocks.restore_code_indent(page.en, _flattened(page.it))
        assert code_blocks.restore_code_indent(page.en, once) == (once, 0)

    @pytest.mark.parametrize("page", PAGE_PARAMS)
    def test_leaves_a_correct_translation_alone(self, code_blocks, page):
        assert code_blocks.restore_code_indent(page.en, page.it) == (page.it, 0)

    @pytest.mark.parametrize(("en", "tr", "restored"), MISALIGNED)
    def test_leaves_blocks_it_cannot_align_line_by_line_untouched(self, code_blocks, en, tr, restored):
        """Only closed pairs with the same line count are rewritten; the aligned list block beside them still is."""
        assert code_blocks.restore_code_indent(en, tr) == (restored, _changed_lines(tr, restored))

    def test_never_introduces_trailing_whitespace(self, code_blocks):
        en = "\n".join(["```yaml", "services:  ", "  app:", "    image: x   ", "  db:", "```", ""])
        tr = "\n".join(["```yaml", "services:", "app:", " image: x", "  db:  ", "```", ""])
        # "services:" differs from EN only by EN's trailing spaces: not rewritten.
        # "image: x" takes the EN indentation, not the EN trailing spaces.
        # "  db:  " differs only by its own trailing spaces: not rewritten, not counted.
        expected = "\n".join(["```yaml", "services:", "  app:", "    image: x", "  db:  ", "```", ""])
        assert code_blocks.restore_code_indent(en, tr) == (expected, 2)

    def test_leaves_blank_lines_alone_on_either_side(self, code_blocks):
        en = "\n".join(["```yaml", "a:", "  b: 1", "", "  c: 2", "```", "", "```text", "first", "", "second", "```", ""])
        tr = "\n".join(["```yaml", "a:", " b: 1", "   ", " c: 2", "```", "", "```text", "primo", "  nota", "secondo", "```", ""])
        # The whitespace-only TR line stays as it is; so does "  nota", whose EN line is blank.
        expected = "\n".join(["```yaml", "a:", "  b: 1", "   ", "  c: 2", "```", "", "```text", "primo", "  nota", "secondo", "```", ""])
        assert code_blocks.restore_code_indent(en, tr) == (expected, 2)


class TestCodeIndentIssues:
    def test_names_every_drifted_line_of_every_drifted_block(self, code_blocks):
        rows = [row for row in _drift_table(COMBINED) if row.lines]
        issues = code_blocks.code_indent_issues(COMBINED.en, _flattened(COMBINED.it))
        assert len(issues) == len(rows), [(issue.translated_block.start, issue.lines) for issue in issues]
        by_start = {issue.translated_block.start: issue for issue in issues}
        assert sorted(by_start) == sorted(row.tr_start for row in rows)
        for row in rows:
            issue = by_start[row.tr_start]
            assert issue.lines == row.lines
            assert (issue.source_block.start, issue.source_block.lines) == (row.en_start, row.en_lines)
            assert issue.translated_block.lines == row.tr_lines

    @pytest.mark.parametrize("page", PAGE_PARAMS)
    def test_is_empty_for_a_correct_translation_and_after_restore(self, code_blocks, page):
        flat = _flattened(page.it)
        assert code_blocks.code_indent_issues(page.en, flat) != [], "barrier: the flattened translation must be flagged"
        assert code_blocks.code_indent_issues(page.en, page.it) == []
        restored, _ = code_blocks.restore_code_indent(page.en, flat)
        assert code_blocks.code_indent_issues(page.en, restored) == []

    @pytest.mark.parametrize(("en", "tr", "restored"), MISALIGNED)
    def test_ignores_blocks_it_cannot_align_line_by_line(self, code_blocks, en, tr, restored):
        issues = code_blocks.code_indent_issues(en, tr)
        assert [(issue.translated_block.start, issue.lines) for issue in issues] == [(0, (0, 1, 2))]


# ---------------------------------------------------------------------------
# translate_docs.py
# ---------------------------------------------------------------------------

PROSE_CASES = [
    pytest.param(
        _page("- Docker Compose avvia il container.\n    - Il volume conserva i dati.\n    - La porta 6040 serve l'app.\n- Il server di test è facoltativo."),
        ("    - Il volume conserva i dati.", "    - La porta 6040 serve l'app."),
        id="nested-list-items",
    ),
    pytest.param(
        _page('=== "Docker"', "    Avvia il container con le impostazioni predefinite.", '=== "Manuale"', "    Installa prima le dipendenze."),
        ("    Avvia il container con le impostazioni predefinite.", "    Installa prima le dipendenze."),
        id="content-tab-bodies",
    ),
    pytest.param(
        _page(
            '!!! warning "I dati di test sono effimeri"',
            "    I dati sopravvivono a un riavvio del container:",
            "    - `docker compose stop` li conserva;\n        - anche dopo un `docker compose start`.\n    - `docker compose down` li cancella.",
        ),
        ("    I dati sopravvivono a un riavvio del container:", "    - `docker compose stop` li conserva;", "        - anche dopo un `docker compose start`.", "    - `docker compose down` li cancella."),
        id="admonition-body-with-a-nested-list",
    ),
    pytest.param(
        _page('??? info "Dettagli"', "    Nascosto per impostazione predefinita."),
        ("    Nascosto per impostazione predefinita.",),
        id="collapsible-admonition-body",
    ),
    pytest.param(
        _page("- Docker Compose avvia il container.\n    - Il volume [2] conserva i dati."),
        ("    - Il volume conserva i dati.",),
        id="nested-item-loses-a-marker-keeps-its-indent",
    ),
]


class TestCleanTranslation:
    @pytest.mark.parametrize("page", CONSTRUCT_PARAMS)
    def test_keeps_fenced_code_byte_identical(self, translate_docs, page):
        """Nested YAML, double spaces inside code, aligned comments; fences at the top level, in list items, tabs, `!!!` and `???` bodies."""
        cleaned = translate_docs._clean_translation(page.it)
        assert [block for block in page.it_blocks if block not in cleaned] == [], f"cleaned page:\n{cleaned}"

    @pytest.mark.parametrize(("text", "kept"), PROSE_CASES)
    def test_keeps_the_leading_indentation_of_prose(self, translate_docs, text, kept):
        lines = translate_docs._clean_translation(text).split("\n")
        assert [line for line in kept if line not in lines] == [], "\n".join(lines)

    def test_keeps_markdown_hard_breaks(self, translate_docs):
        text = _page("Introduzione.", "La prima riga va a capo qui  \nla seconda riga continua il paragrafo.")
        assert translate_docs._clean_translation(text) == text

    def test_still_collapses_the_gap_a_removed_marker_leaves(self, translate_docs):
        """Regression pin, green before and after the fix: step 7 exists for this."""
        raw = _page("Il valore [1] del portafoglio [^2] cresce ogni giorno.", "word [1] word")
        assert translate_docs._clean_translation(raw) == _page("Il valore del portafoglio cresce ogni giorno.", "word word")


class TestFinalizeTranslation:
    def test_cleans_then_gives_back_the_en_indentation(self, translate_docs):
        """`_finalize_translation(source, raw)` = clean + restore: the compose parses as EN's again, translated comments stay."""
        raw = _llm_output(COMPOSE)
        en_data = yaml.safe_load(_yaml_body(COMPOSE.en))
        assert _yaml_or_error(_yaml_body(raw)) != en_data, "barrier: the flattened compose must not already mean the same"
        out, restored = translate_docs._finalize_translation(COMPOSE.en, raw)
        code_blocks = _load("code_blocks")
        assert _yaml_or_error(_yaml_body(out)) == en_data
        assert code_blocks.code_indent_issues(COMPOSE.en, out) == []
        assert "# (2) Porta di produzione" in out and "# (2) Production port" not in out
        assert restored > 0
        assert restored == _changed_lines(_flattened(COMPOSE.it), COMPOSE.it)
        assert out == COMPOSE.it

    def test_translate_one_lang_finalizes_the_translation_before_writing_it(self, translate_docs):
        """The only write of a translation goes through `_finalize_translation(source_text, ...)`, never the bare clean."""
        tree = ast.parse(textwrap.dedent(inspect.getsource(translate_docs._translate_one_lang)))
        calls = [node for node in ast.walk(tree) if isinstance(node, ast.Call)]
        writes = [call.lineno for call in calls if _call_name(call) == "write_text"]
        finalizes = [call for call in calls if _call_name(call) == "_finalize_translation"]
        bare_cleans = [node.lineno for node in ast.walk(tree) if isinstance(node, ast.Assign) and isinstance(node.value, ast.Call) and _call_name(node.value) == "_clean_translation"]
        assert writes, "barrier: _translate_one_lang no longer writes the translation; the wiring moved, update this test"
        assert finalizes, "_translate_one_lang must pass the LLM output through _finalize_translation(source_text, translated) before write_text"
        assert min(call.lineno for call in finalizes) < min(writes)
        assert [_source_argument(call) for call in finalizes] == ["source_text"] * len(finalizes)
        assert bare_cleans == [], f"`translated = _clean_translation(translated)` is still there (function lines {bare_cleans})"


# ---------------------------------------------------------------------------
# validate_translations.py
# ---------------------------------------------------------------------------


class TestValidator:
    def test_check_code_block_indent_flags_each_drifted_block_once(self, validate_translations):
        vt = validate_translations
        rows = {min(row.lines) + 1: row for row in _drift_table(COMBINED) if row.lines}
        issues = vt.check_code_block_indent(COMBINED.en, _flattened(COMBINED.it), CACHE_KEY, "it")
        assert sorted(issue.line for issue in issues) == sorted(rows), [str(issue) for issue in issues]
        for issue in issues:
            assert (issue.severity, issue.check, issue.file, issue.lang) == (vt.Severity.ERROR, "code-block-indent", CACHE_KEY, "it")
            row = rows[issue.line]
            numbers = _numbers(issue.message)
            spans = ((row.tr_start + 1, row.tr_end + 1), (row.tr_start + 2, row.tr_end), (min(row.lines) + 1, max(row.lines) + 1))
            assert any(first in numbers and last in numbers for first, last in spans), f"the message names no TR line range of the block: {issue.message}"
            assert len(row.lines) in numbers, f"the message does not say how many lines are off ({len(row.lines)}): {issue.message}"

    def test_check_code_block_indent_accepts_translated_comments_and_labels(self, validate_translations):
        vt = validate_translations
        assert vt.check_code_block_indent(COMBINED.en, _flattened(COMBINED.it), CACHE_KEY, "it") != [], "barrier: the flattened page must be flagged"
        assert vt.check_code_block_indent(COMBINED.en, COMBINED.it, CACHE_KEY, "it") == []

    def test_code_block_indent_is_registered_and_reported_by_validate_file(self, validate_translations, tmp_path):
        vt = validate_translations
        registered = {name: (check, needs_source) for name, check, needs_source in vt.ALL_CHECKS}
        assert "code-block-indent" in registered, sorted(registered)
        assert registered["code-block-indent"] == (vt.check_code_block_indent, True)
        source = tmp_path / "docker_advanced.en.md"
        source.write_text(COMBINED.en, encoding="utf-8")
        flat = tmp_path / "flat.it.md"
        flat.write_text(_flattened(COMBINED.it), encoding="utf-8")
        ideal = tmp_path / "ideal.it.md"
        ideal.write_text(COMBINED.it, encoding="utf-8")
        reported = [issue for issue in vt.validate_file(source, flat, CACHE_KEY, "it") if issue.check == "code-block-indent"]
        assert sorted(issue.line for issue in reported) == sorted(min(row.lines) + 1 for row in _drift_table(COMBINED) if row.lines)
        assert {issue.severity for issue in reported} == {vt.Severity.ERROR}
        assert [issue for issue in vt.validate_file(source, ideal, CACHE_KEY, "it") if issue.check == "code-block-indent"] == []

    def test_check_code_blocks_no_longer_blames_alignment_on_localization(self, validate_translations):
        vt = validate_translations
        localized = [issue for issue in vt.check_code_blocks(_page(EN_LOGS), _page(_translate(EN_LOGS)), CACHE_KEY, "it") if issue.check == "code-block-modified" and issue.severity == vt.Severity.LOCALIZED]
        assert localized, "barrier: a translated comment is still a LOCALIZED code-block-modified"
        assert [issue.message for issue in localized if "alignment stripped" in issue.message] == []


# ---------------------------------------------------------------------------
# Corpus guard (read-only over the repository)
# ---------------------------------------------------------------------------


def _up_to_date_pairs(td) -> list[tuple[str, str, Path, Path]]:
    """(page, lang, EN path, TR path) for every pair the next `run_translate` skips (translate_docs.py ~:1963-1979)."""
    cache = json.loads(td.HASH_FILE.read_text(encoding="utf-8"))
    langs = td._detect_target_languages()
    pairs = []
    for rel in dict.fromkeys(td.get_translatable_files()):
        source = td.DOCS_DIR / rel
        entry = cache.get(rel, {})
        if not source.is_file() or td._file_md5(source) != entry.get("md5", ""):
            continue  # missing, or the EN changed since the last run: the next alignment regenerates it
        for lang in langs:
            target = source.with_name(source.name.replace(".en.md", f".{lang}.md"))
            if lang in entry.get("langs_done", []) and target.is_file():
                pairs.append((rel, lang, source, target))
    return pairs


def _describe(rel: str, lang: str, issue) -> str:
    block = issue.translated_block
    return f"  {rel.replace('.en.md', f'.{lang}.md')} ({lang}): {block.lang or 'plain'} block at line {block.start + 1}, indentation off on lines {_ranges(n + 1 for n in issue.lines)}"


class TestCorpusGuard:
    def test_up_to_date_translations_keep_the_en_code_indentation(self, translate_docs, code_blocks):
        """Stale pairs are skipped: the next alignment re-translates them through the fixed pipeline. After it, every pair is covered."""
        pairs = _up_to_date_pairs(translate_docs)
        assert pairs, "barrier: no up-to-date (page, lang) pair, so the guard would pass without looking at anything"
        drifted: list[str] = []
        blocks = 0
        for rel, lang, source, target in pairs:
            en_text, tr_text = source.read_text(encoding="utf-8"), target.read_text(encoding="utf-8")
            blocks += len(code_blocks.parse_fenced_blocks(tr_text))
            drifted += [_describe(rel, lang, issue) for issue in code_blocks.code_indent_issues(en_text, tr_text)]
        assert blocks, "barrier: the up-to-date translations hold no fenced block at all"
        assert drifted == [], f"{len(drifted)} code block(s) lost the EN indentation in {len(pairs)} up-to-date pairs (1-based lines):\n" + "\n".join(drifted)
