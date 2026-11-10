"""lf_theme_tokens: the docs site reads the app's colour roles, and the derived roles follow its dark scheme.

``mkdocs_src/hooks/lf_theme_tokens.py`` writes ``frontend/src/lib/theme/tokens.css`` into the docs, keyed on Material's
dark scheme (``[data-md-color-scheme="slate"]``, set on ``body``) instead of the app's ``html.dark``. A custom property
that names another (``--lf-link: var(--lf-focus)``) is resolved on the element that declares it: the derived block must
therefore also be declared under the dark scheme, or ``--lf-link`` keeps there the light green computed on ``:root``
(seen on the docs home, 07/11/2026). Pinned on the real token file, in memory: no build, no writes.
"""

import importlib.util
import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
HOOK = PROJECT_ROOT / "mkdocs_src" / "hooks" / "lf_theme_tokens.py"
SLATE = '[data-md-color-scheme="slate"]'


def _hook():
    spec = importlib.util.spec_from_file_location("lf_theme_tokens_under_test", HOOK)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _blocks(css: str) -> list[tuple[list[str], str]]:
    """Every top-level rule, in order: its selectors and its body (comments dropped first)."""
    css = re.sub(r"/\*.*?\*/", "", css, flags=re.DOTALL)
    return [([part.strip() for part in head.split(",")], body) for head, body in re.findall(r"([^{}]+)\{([^{}]*)\}", css)]


def test_the_derived_roles_are_declared_under_the_dark_scheme_too():
    hook = _hook()
    css = hook.transform(hook.TOKENS.read_text(encoding="utf-8"))
    derived = [body for selectors, body in _blocks(css) if "--lf-link:" in body]
    assert len(derived) == 1, "positive control: one block declares --lf-link"
    owner = [selectors for selectors, body in _blocks(css) if "--lf-link:" in body][0]
    assert SLATE in owner, f"the derived block must be declared under the dark scheme as well: {owner}"
    assert ":root" in owner, "and still on :root, for the light theme"


def test_the_dark_values_still_come_after_the_derived_block():
    hook = _hook()
    css = hook.transform(hook.TOKENS.read_text(encoding="utf-8"))
    blocks = _blocks(css)
    derived_at = next(i for i, (_, body) in enumerate(blocks) if "--lf-link:" in body)
    dark_at = next(i for i, (selectors, _) in enumerate(blocks) if selectors == [SLATE])
    assert dark_at > derived_at, "the dark block must follow the derived one, so it wins on the dark scheme"


def test_a_token_file_without_the_derived_block_is_refused():
    hook = _hook()
    source = hook.TOKENS.read_text(encoding="utf-8").replace(":root,\n.light,\n.dark {", ":root {", 1)
    try:
        hook.transform(source)
    except ValueError as exc:
        assert "derived" in str(exc)
    else:
        raise AssertionError("a token file whose derived block moved must stop the build, not publish wrong colours")
