"""A translated page says what its source says: Mermaid, tabs, tables, identifiers, code, admonitions, anchors (E9E).

``translate-validate`` compared headings, links, fence counts and indentation, inline code, list items and the
admonitions at column 0. The admin guide was translated by hand from the Italian pages (E9E) and a reader of
another language could still lose something no check saw: an arrow reversed in a diagram, a proxy tab dropped,
a table row lost, a command changed inside a block (filed as "comments translated" and hidden by ``-L``), a
nested admonition left out. ``mkdocs_src/aphra-pipeline/page_equivalence.py`` holds those checks as pure
functions of two texts; ``validate_translations.ALL_CHECKS`` runs them as ERRORs.

Pinned here:

* **mermaid**: same count; per diagram the same skeleton (front matter, ids, arrows, shapes, ``style`` /
  ``classDef`` / ``class``), labels, participant aliases, messages and notes aside.
* **content tabs**: same count, order and marker; a proper name of the source title (Caddy, Fly.io…) stays;
  a body indented by less than 4 spaces is an error.
* **tables**: same count; per table the same rows and cells per row, a pipe inside a code span is no cell.
* **identifiers**: the same variables, ``dev.py`` commands and paths in inline code and in blocks.
* **code content**: a command, setting or log line that differs is an error; comments and ``<placeholders>`` are free.
* **admonitions**: marker, type and nesting depth, nested ones included.
* **explicit anchors**: every one of the source stays; none is added except the id of a source heading.
* **corpus guard**: every page of the docs tree passes the checks against the English page in every language.

PURE: strings in memory, plus a read-only pass over ``mkdocs_src/docs``. No DB, no server, no network, no repo writes.
"""

import importlib
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[3]
PIPELINE_DIR = PROJECT_ROOT / "mkdocs_src" / "aphra-pipeline"
DOCS_DIR = PROJECT_ROOT / "mkdocs_src" / "docs"


@pytest.fixture(scope="module")
def pe():
    with pytest.MonkeyPatch.context() as mp:
        mp.syspath_prepend(str(PIPELINE_DIR))
        yield importlib.import_module("page_equivalence")


@pytest.fixture(scope="module")
def validator():
    with pytest.MonkeyPatch.context() as mp:
        mp.syspath_prepend(str(PIPELINE_DIR))
        yield importlib.import_module("validate_translations")


def names(differences):
    return sorted({d.check for d in differences})


FLOW_EN = """
```mermaid
---
title: Backup
config:
  layout: elk
---
flowchart TD
    A["Create the backup"] --> B{"Is it sealed?"}
    B -->|Yes| C(["Keep the key"])
    B -- No --> D["Done"]
    subgraph S1["Where"]
        E["Server"]
    end
    style C fill:#d4edda,color:#1b1b1b
    classDef warn fill:#fff3cd,color:#1b1b1b
    class D warn
```
"""

FLOW_IT = """
```mermaid
---
title: Copia di sicurezza
config:
  layout: elk
---
flowchart TD
    A["Crea la copia"] --> B{"È sigillata?"}
    B -->|Sì| C(["Conserva la chiave"])
    B -- No --> D["Fatto"]
    subgraph S1["Dove"]
        E["Server"]
    end
    style C fill:#d4edda,color:#1b1b1b
    classDef warn fill:#fff3cd,color:#1b1b1b
    class D warn
```
"""

SEQUENCE_EN = """
```mermaid
sequenceDiagram
    participant U as User
    participant S as Server
    U->>S: Ask for the link
    S-->>U: Sends the email
    Note over U,S: Within one hour
    alt valid
        S->>U: Done
    else expired
        S->>U: Error
    end
```
"""

SEQUENCE_IT = """
```mermaid
sequenceDiagram
    participant U as Utente
    participant S as Server
    U->>S: Chiede il link
    S-->>U: Invia l'email
    Note over U,S: Entro un'ora
    alt valido
        S->>U: Fatto
    else scaduto
        S->>U: Errore
    end
```
"""


class TestMermaid:
    def test_labels_and_messages_may_be_translated(self, pe):
        assert pe.check_mermaid(FLOW_EN, FLOW_IT) == []
        assert pe.check_mermaid(SEQUENCE_EN, SEQUENCE_IT) == []

    def test_a_missing_diagram_is_counted(self, pe):
        assert names(pe.check_mermaid(FLOW_EN + SEQUENCE_EN, FLOW_IT)) == ["mermaid-count"]

    def test_a_reversed_arrow_is_found(self, pe):
        reversed_it = FLOW_IT.replace('A["Crea la copia"] --> B', 'B{"È sigillata?"} --> A')
        assert "mermaid-structure" in names(pe.check_mermaid(FLOW_EN, reversed_it))

    def test_a_changed_colour_is_found(self, pe):
        recoloured = FLOW_IT.replace("fill:#d4edda,color:#1b1b1b", "fill:#d4edda")
        found = pe.check_mermaid(FLOW_EN, recoloured)
        assert names(found) == ["mermaid-structure"]
        assert "style C" in found[0].message

    def test_a_dropped_node_is_found(self, pe):
        dropped = FLOW_IT.replace('    B -- No --> D["Fatto"]\n', "")
        assert "mermaid-structure" in names(pe.check_mermaid(FLOW_EN, dropped))

    def test_an_edge_label_changed_into_an_edge_is_found(self, pe):
        assert "mermaid-structure" in names(pe.check_mermaid(FLOW_EN, FLOW_IT.replace("B -->|Sì| C", "B --> C")))

    def test_a_changed_shape_is_found(self, pe):
        assert "mermaid-structure" in names(pe.check_mermaid(FLOW_EN, FLOW_IT.replace('D["Fatto"]', 'D("Fatto")')))

    def test_the_front_matter_must_match(self, pe):
        assert "mermaid-structure" in names(pe.check_mermaid(FLOW_EN, FLOW_IT.replace("layout: elk", "layout: dagre")))

    def test_a_changed_participant_or_message_target_is_found(self, pe):
        assert "mermaid-structure" in names(pe.check_mermaid(SEQUENCE_EN, SEQUENCE_IT.replace("U->>S: Chiede il link", "S->>U: Chiede il link")))
        assert "mermaid-structure" in names(pe.check_mermaid(SEQUENCE_EN, SEQUENCE_IT.replace("participant S as Server", "participant X as Server")))

    def test_a_dropped_branch_of_a_sequence_is_found(self, pe):
        assert "mermaid-structure" in names(pe.check_mermaid(SEQUENCE_EN, SEQUENCE_IT.replace("    else scaduto\n        S->>U: Errore\n", "")))

    def test_text_blocks_are_not_diagrams(self, pe):
        assert pe.check_mermaid("```text\na --> b\n```\n", "```text\nb --> a\n```\n") == []


TABS_EN = """
=== "Caddy"

    Body.

=== "Fly.io"

    Body.

=== "Other proxy"

    Body.
"""


class TestContentTabs:
    def test_titles_and_bodies_may_be_translated(self, pe):
        translated = TABS_EN.replace("Other proxy", "Autre proxy").replace("Body.", "Corps.")
        assert pe.check_tabs(TABS_EN, translated) == []

    def test_a_dropped_tab_is_counted(self, pe):
        assert "tab-count" in names(pe.check_tabs(TABS_EN, TABS_EN.replace('=== "Fly.io"\n\n    Body.\n\n', "")))

    def test_a_proper_name_must_stay_in_the_title(self, pe):
        found = pe.check_tabs(TABS_EN, TABS_EN.replace('"Fly.io"', '"Fly point io"'))
        assert names(found) == ["tab-title"]
        assert "Fly.io" in found[0].message

    def test_a_translated_proper_name_is_found(self, pe):
        assert names(pe.check_tabs(TABS_EN, TABS_EN.replace('"Caddy"', '"Caddie"'))) == ["tab-title"]

    def test_a_body_indented_by_one_space_is_found(self, pe):
        broken = TABS_EN.replace('=== "Caddy"\n\n    Body.', '=== "Caddy"\n\n Body.')
        assert names(pe.check_tabs(TABS_EN, broken)) == ["tab-indent"]

    def test_the_marker_must_match(self, pe):
        assert names(pe.check_tabs(TABS_EN, TABS_EN.replace('=== "Caddy"', '===+ "Caddy"'))) == ["tab-marker"]

    def test_a_tab_inside_a_code_block_is_no_tab(self, pe):
        assert pe.check_tabs('```markdown\n=== "A"\n```\n', "```markdown\ntext\n```\n") == []

    def test_a_tab_nested_in_an_admonition_is_read(self, pe):
        nested = '!!! note "N"\n\n    === "Caddy"\n\n        Body.\n'
        assert names(pe.check_tabs(nested, nested.replace("    === ", "=== "))) == ["tab-nesting"]


TABLE_EN = """
| Variable | Default | Meaning |
|----------|---------|---------|
| `A_B` | `1` | One |
| `C_D` | `a\\|b` | Two |
| `E_F` | `3` | Three |

Text.

| X | Y |
|---|---|
| 1 | 2 |
"""


class TestTables:
    def test_translated_cells_are_fine(self, pe):
        assert pe.check_tables(TABLE_EN, TABLE_EN.replace("Meaning", "Signification").replace("Two", "Deux")) == []

    def test_a_pipe_in_a_code_span_is_no_cell(self, pe):
        assert pe.tables("| a | `x|y` | b |\n")[0][1] == [3]

    def test_a_lost_row_is_found(self, pe):
        found = pe.check_tables(TABLE_EN, TABLE_EN.replace("| `E_F` | `3` | Three |\n", ""))
        assert names(found) == ["table-shape"]
        assert "5 rows" in found[0].message

    def test_a_lost_column_is_found(self, pe):
        found = pe.check_tables(TABLE_EN, TABLE_EN.replace("| `E_F` | `3` | Three |", "| `E_F` | Three |"))
        assert names(found) == ["table-shape"]
        assert "row 5" in found[0].message

    def test_a_lost_table_is_counted(self, pe):
        assert "table-count" in names(pe.check_tables(TABLE_EN, TABLE_EN.split("Text.")[0]))

    def test_a_table_inside_a_code_block_is_not_one(self, pe):
        assert pe.tables("```text\n| a | b |\n```\n") == []

    def test_a_table_in_a_tab_is_read(self, pe):
        assert pe.tables('=== "T"\n\n    | a | b |\n    |---|---|\n')[0][1] == [2, 2]


class TestIdentifiers:
    EN = "Set `LIBREFOLIO_PUBLIC_URL` and run `./dev.py backup create --sealed`.\n" "```bash\n# Create the backup\n./dev.py db migrate\ncp .env /srv/librefolio/.env\n```\n" "The path `LibreFolio-data/backups/` holds them.\n"

    def test_comments_and_prose_may_change(self, pe):
        translated = self.EN.replace("# Create the backup", "# Crea la copia").replace("Set", "Imposta").replace("holds them", "le contiene")
        assert pe.check_identifiers(self.EN, translated) == []

    def test_a_renamed_variable_is_found(self, pe):
        found = pe.check_identifiers(self.EN, self.EN.replace("LIBREFOLIO_PUBLIC_URL", "LIBREFOLIO_URL_PUBBLICO"))
        assert names(found) == ["variable-extra", "variable-missing"]

    def test_a_changed_command_is_found(self, pe):
        found = pe.check_identifiers(self.EN, self.EN.replace("db migrate", "db migra"))
        assert "command-missing" in names(found) and "command-extra" in names(found)

    def test_command_options_are_not_part_of_the_command(self, pe):
        assert pe.identifiers(self.EN)["command"] == {"dev.py backup create", "dev.py db migrate"}

    def test_a_changed_path_is_found(self, pe):
        assert names(pe.check_identifiers(self.EN, self.EN.replace("LibreFolio-data/backups/", "LibreFolio-data/copie/"))) == ["path-extra", "path-missing"]

    def test_urls_are_not_paths(self, pe):
        assert pe.identifiers("`https://example.com/a/b`\n")["path"] == set()

    def test_bare_prose_is_not_read(self, pe):
        assert pe.identifiers("The state PARTIALLY_CLOSED.\n")["variable"] == set()

    def test_mermaid_labels_are_not_read(self, pe):
        assert pe.identifiers('```mermaid\nA["LIBREFOLIO_X"] --> B\n```\n')["variable"] == set()


class TestCodeContent:
    def test_comments_and_placeholders_are_free(self, pe):
        en = "```bash\n# Create\nopenssl rand -hex 32 # secret\ncp <file> /srv/x\n```\n"
        it = "```bash\n# Crea\nopenssl rand -hex 32 # segreto\ncp <file-nome> /srv/x\n```\n"
        assert pe.check_code_content(en, it) == []

    def test_a_changed_command_is_an_error(self, pe):
        en = "```bash\nopenssl rand -hex 32\n```\n"
        found = pe.check_code_content(en, en.replace("-hex 32", "-hex 16"))
        assert names(found) == ["code-block-content"]
        assert "-hex 32" in found[0].message

    def test_a_translated_log_line_is_an_error(self, pe):
        en = "```text\nLibreFolio blocked a script\n```\n"
        assert names(pe.check_code_content(en, "```text\nLibreFolio a bloqué un script\n```\n")) == ["code-block-content"]

    def test_a_dropped_line_is_an_error(self, pe):
        assert names(pe.check_code_content("```bash\na\nb\n```\n", "```bash\na\n```\n")) == ["code-block-content"]

    def test_a_block_present_on_one_side_only_does_not_shift_the_others(self, pe):
        en = "```bash\na\n```\n\n```bash\nb\n```\n"
        found = pe.check_code_content(en, "```bash\nb\n```\n")
        assert len(found) == 1 and "#1" in found[0].message

    def test_hash_comment_lines_in_yaml_and_json_comments(self, pe):
        assert pe.check_code_content('```yaml\n# a\nx: 1 # one\n```\n```json\n{\n  // c\n  "k": 1\n}\n```\n', '```yaml\n# b\nx: 1 # uno\n```\n```json\n{\n  // d\n  "k": 1\n}\n```\n') == []

    def test_mermaid_is_left_to_its_own_check(self, pe):
        assert pe.check_code_content(FLOW_EN, FLOW_IT) == []


class TestAdmonitionsAndAnchors:
    EN = '!!! warning "W"\n\n    Body.\n\n??? note "N"\n\n    ??? tip "Inner"\n\n        Body.\n\n- item\n\n    !!! info "I"\n\n        Body.\n'

    def test_titles_may_change(self, pe):
        assert pe.check_admonition_sequence(self.EN, self.EN.replace('"Inner"', '"Intérieur"')) == []

    def test_a_nested_admonition_dropped_is_counted(self, pe):
        broken = self.EN.replace('    ??? tip "Inner"\n\n        Body.\n\n', "")
        assert "admonition-nested-count" in names(pe.check_admonition_sequence(self.EN, broken))

    def test_a_changed_marker_is_found(self, pe):
        assert names(pe.check_admonition_sequence(self.EN, self.EN.replace("??? note", "!!! note"))) == ["admonition-sequence"]

    def test_a_changed_depth_is_found(self, pe):
        assert names(pe.check_admonition_sequence(self.EN, self.EN.replace('    ??? tip "Inner"', '??? tip "Inner"'))) == ["admonition-sequence"]

    def test_an_admonition_in_a_code_block_is_not_one(self, pe):
        assert pe.check_admonition_sequence('```markdown\n!!! note "N"\n```\n', "```markdown\nx\n```\n") == []

    SRC = "## 🔐 Security {: #sec }\n\n### 📋 Data quality banner\n"

    def test_the_anchors_of_the_source_stay(self, pe):
        assert pe.check_heading_anchors(self.SRC, self.SRC) == []
        assert names(pe.check_heading_anchors(self.SRC, "## 🔐 Sicurezza\n")) == ["anchor-id"]

    def test_a_translation_may_keep_the_id_of_a_source_heading(self, pe):
        assert pe.check_heading_anchors(self.SRC, "## 🔐 Sicurezza {: #sec }\n\n### 📋 Banner {: #data-quality-banner }\n") == []

    def test_a_new_anchor_is_found(self, pe):
        found = pe.check_heading_anchors(self.SRC, "## 🔐 Sicurezza {: #sec }\n\n### 📋 Banner {: #banner-qualita }\n")
        assert names(found) == ["anchor-id"]
        assert "banner-qualita" in found[0].message

    def test_the_order_matters(self, pe):
        assert names(pe.check_heading_anchors("# A {: #a }\n# B {: #b }\n", "# B {: #b }\n# A {: #a }\n")) == ["anchor-order"]


class TestValidatorRunsThem:
    def test_the_checks_are_registered(self, validator):
        registered = {name for name, _, _ in validator.ALL_CHECKS}
        assert {"mermaid", "content-tabs", "tables", "identifiers", "code-content", "admonition-sequence", "heading-anchors"} <= registered

    def test_a_difference_is_an_error_issue_with_the_check_name(self, validator):
        issues = validator.validate_text(FLOW_EN, FLOW_IT.replace("fill:#d4edda,color:#1b1b1b", "fill:#d4edda"), "x.en.md", "it")
        found = [i for i in issues if i.check == "mermaid-structure"]
        assert len(found) == 1
        assert found[0].severity == validator.Severity.ERROR and found[0].lang == "it" and found[0].line

    def test_equal_pages_have_no_new_issue(self, validator):
        issues = validator.validate_text(FLOW_EN + TABS_EN + TABLE_EN, FLOW_IT + TABS_EN + TABLE_EN, "x.en.md", "it")
        assert [i.check for i in issues if i.severity == validator.Severity.ERROR] == []


def _pairs():
    for english in sorted(DOCS_DIR.rglob("*.en.md")):
        for lang in ("it", "fr", "es"):
            other = english.with_name(english.name.replace(".en.md", f".{lang}.md"))
            if other.exists():
                yield english, other, lang


class TestCorpus:
    """Every translated page of the docs tree passes the checks against its English page."""

    CHECKS = ("check_mermaid", "check_tabs", "check_tables", "check_identifiers", "check_code_content", "check_admonition_sequence", "check_heading_anchors")

    def test_every_page_in_every_language_is_equivalent(self, pe):
        failures = []
        for english, other, _lang in _pairs():
            source, translated = english.read_text(encoding="utf-8"), other.read_text(encoding="utf-8")
            for name in self.CHECKS:
                failures += [f"{other.relative_to(DOCS_DIR)} [{d.check}] {d.message[:140]}" for d in getattr(pe, name)(source, translated)]
        assert failures == [], "\n".join(failures[:40]) + f"\n({len(failures)} differences)"

    def test_the_corpus_is_not_empty(self):
        assert len(list(_pairs())) > 100

    def test_the_checks_do_not_need_a_third_party_package(self):
        text = (PIPELINE_DIR / "page_equivalence.py").read_text(encoding="utf-8")
        imports = {line.split()[1].split(".")[0] for line in text.splitlines() if line.startswith(("import ", "from "))}
        assert imports <= set(sys.stdlib_module_names) | {"code_blocks"}
