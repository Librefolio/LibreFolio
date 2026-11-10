"""
MkDocs hook: the site's colours are the app's colours, read from the one place that defines them.

``frontend/src/lib/theme/tokens.css`` holds every colour role (``--lf-*``) of the design system, in the light theme
«Stone and Sage» and the dark theme «Slate and Sage». Before each build this hook writes that file to ``docs/stylesheets/lf-tokens.css`` (git-ignored),
changed in two ways only, so the docs never keep a second copy of the palette:

* the dark block is keyed on Material's scheme, ``[data-md-color-scheme="slate"]``, instead of the app's ``html.dark``,
  and the derived block (``:root, .light, .dark``) gets that selector too: a custom property that names another is
  resolved where it is declared, so without it ``--lf-link`` and the other derived roles would keep, under the dark
  scheme (set on ``body``), the values computed on ``:root`` from the light ones;
* everything from ``@theme inline`` on is dropped: it is Tailwind's utility table, which the docs do not use.

``static/extra.css`` then maps Material's ``--md-*`` variables onto the roles, and the pages read roles only.
"""

from __future__ import annotations

import re
from pathlib import Path

TOKENS = Path(__file__).resolve().parents[2] / "frontend" / "src" / "lib" / "theme" / "tokens.css"
PUBLISHED = Path(__file__).resolve().parents[1] / "docs" / "stylesheets" / "lf-tokens.css"  # git-ignored

_DARK_SELECTOR = re.compile(r"^html\.dark,\s*\n\.dark\s*\{", re.MULTILINE)
_DERIVED_SELECTOR = re.compile(r"^:root,\s*\n\.light,\s*\n\.dark\s*\{", re.MULTILINE)
_UTILITY_TABLE = re.compile(r"^/\* =+ Utilities:.*", re.MULTILINE | re.DOTALL)

BANNER = "/* Generated at build time from frontend/src/lib/theme/tokens.css by mkdocs_src/hooks/lf_theme_tokens.py.\n" "   Do not edit: change the role there. */\n"


def transform(source: str) -> str:
    """The app's token file, ready for the docs site (see the module docstring)."""
    css, dark_blocks = _DARK_SELECTOR.subn('[data-md-color-scheme="slate"] {', source)
    if dark_blocks != 1:
        raise ValueError(f"tokens.css: expected one `html.dark, .dark` block, found {dark_blocks}")
    css, derived_blocks = _DERIVED_SELECTOR.subn(':root,\n.light,\n.dark,\n[data-md-color-scheme="slate"] {', css)
    if derived_blocks != 1:
        raise ValueError(f"tokens.css: expected one `:root, .light, .dark` block of derived roles, found {derived_blocks}")
    css, tables = _UTILITY_TABLE.subn("", css)
    if tables != 1:
        raise ValueError("tokens.css: the `Utilities` section marker was not found")
    return BANNER + css.rstrip() + "\n"


def on_pre_build(config) -> None:
    """Write the published file into the docs tree before MkDocs collects it (the i18n plugin wants real files on
    disk). The file is rewritten only when its content changes, so ``mkdocs serve`` does not rebuild in a loop."""
    if not TOKENS.is_file():
        raise FileNotFoundError(f"lf_theme_tokens hook: {TOKENS} not found (the docs read the app's palette from it)")
    css = transform(TOKENS.read_text(encoding="utf-8"))
    if not PUBLISHED.is_file() or PUBLISHED.read_text(encoding="utf-8") != css:
        PUBLISHED.write_text(css, encoding="utf-8")
