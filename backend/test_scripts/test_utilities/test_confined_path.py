"""A path taken from a request never leaves the folder it is joined to (``backend/app/utils/runtime/paths.py``).

``confined_path(root, relative)`` resolves ``root / relative``, symlinks included, and returns the
result only while it stays inside the resolved root; anything else is ``None``. The result may name
a file that does not exist: the callers still check ``is_file()`` or ``is_dir()``.

Every case builds its own tree under ``tmp_path``: the served folder (``static``), a sibling folder
whose name starts with the served folder's name (``static-other``) and a file outside both. Each
case that expects a refusal first proves that its path, joined without the helper, really names an
existing file outside the folder, so a ``None`` is never satisfied by a path that names nothing.
No DB, no server, no network.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import pytest

from backend.app.utils.runtime.paths import confined_path

FAVICON = b"\x89PNG\r\n\x1a\nfavicon"


@dataclass(frozen=True)
class Tree:
    """The folders of one case, all resolved: ``tmp_path`` itself may sit behind a symlink."""

    base: Path  # the case's tmp folder, parent of everything below
    root: Path  # the served folder
    sibling_file: Path  # a file in a folder next to root, whose name starts with root's name
    outside: Path  # a file outside both


@pytest.fixture
def tree(tmp_path: Path) -> Tree:
    base = tmp_path.resolve()
    root = base / "static"
    (root / "assets").mkdir(parents=True)
    (root / "favicon.png").write_bytes(FAVICON)
    (root / "assets" / "app.css").write_text("body {}\n")
    sibling_file = base / "static-other" / "note.txt"
    sibling_file.parent.mkdir()
    sibling_file.write_text("next to the served folder\n")
    outside = base / "outside" / "marker.txt"
    outside.parent.mkdir()
    outside.write_text("outside the served folder\n")
    return Tree(base=base, root=root, sibling_file=sibling_file, outside=outside)


def _symlink_or_skip(link: Path, target: Path) -> None:
    try:
        link.symlink_to(target, target_is_directory=target.is_dir())
    except (OSError, NotImplementedError) as exc:
        pytest.skip(f"symlinks are not available here: {exc}")


def _assert_names_a_file_outside(root: Path, relative: str) -> None:
    """The case is not vacuous: joined without the helper, ``relative`` names an existing file outside ``root``."""
    joined = root / relative
    assert joined.is_file(), f"{relative!r} names no file when joined to {root}"
    assert not joined.resolve().is_relative_to(root), f"{relative!r} stays inside {root}"


def _climb_to_filesystem_root(start: Path, target: Path) -> str:
    """A relative path from ``start`` up to the filesystem root, then down to ``target``."""
    return "../" * (len(start.parts) - 1) + target.relative_to(target.anchor).as_posix()


#: Relative paths that climb out of the served folder at several depths; each lands on the outside file.
LEAVING_PATHS: dict[str, Callable[[Tree], str]] = {
    "one-level-up": lambda t: "../outside/marker.txt",
    "through-a-subfolder": lambda t: "assets/../../outside/marker.txt",
    "past-the-tmp-folder": lambda t: f"../../{t.base.name}/outside/marker.txt",
    "to-the-filesystem-root": lambda t: _climb_to_filesystem_root(t.root, t.outside),
}


# ---------------------------------------------------------------------------
# Paths that stay inside are returned
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("relative", ["favicon.png", "assets/app.css"])
def test_a_file_inside_the_root_is_returned_resolved(tree: Tree, relative: str) -> None:
    assert confined_path(tree.root, relative) == tree.root / relative


@pytest.mark.parametrize("relative", ["a/../favicon.png", "assets/../favicon.png", "./favicon.png", "assets/./../favicon.png"])
def test_parent_segments_that_come_back_inside_stay_inside(tree: Tree, relative: str) -> None:
    assert confined_path(tree.root, relative) == tree.root / "favicon.png"


def test_an_empty_relative_path_names_the_resolved_root(tree: Tree) -> None:
    assert confined_path(tree.root, "") == tree.root


def test_a_missing_path_inside_the_root_is_still_returned(tree: Tree) -> None:
    result = confined_path(tree.root, "missing/page.html")

    assert result == tree.root / "missing" / "page.html"
    assert not result.exists()


def test_a_symlink_inside_the_root_pointing_inside_is_followed(tree: Tree) -> None:
    _symlink_or_skip(tree.root / "alias.png", tree.root / "favicon.png")

    assert confined_path(tree.root, "alias.png") == tree.root / "favicon.png"


def test_a_root_reached_through_a_symlink_keeps_its_files_and_its_bounds(tree: Tree) -> None:
    link = tree.base / "served-through-a-link"
    _symlink_or_skip(link, tree.root)

    assert confined_path(link, "favicon.png") == tree.root / "favicon.png"
    assert confined_path(link, "") == tree.root
    assert confined_path(link, "../outside/marker.txt") is None


# ---------------------------------------------------------------------------
# Paths that would leave the root are refused
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("leaving", LEAVING_PATHS.values(), ids=list(LEAVING_PATHS))
def test_parent_segments_that_leave_the_root_are_refused(tree: Tree, leaving: Callable[[Tree], str]) -> None:
    relative = leaving(tree)
    _assert_names_a_file_outside(tree.root, relative)

    assert confined_path(tree.root, relative) is None


@pytest.mark.parametrize("target", ["outside-file", "filesystem-root"])
def test_an_absolute_path_outside_the_root_is_refused(tree: Tree, target: str) -> None:
    absolute = str(tree.outside) if target == "outside-file" else tree.outside.anchor
    # Joining an absolute path drops the root altogether.
    assert tree.root / absolute == Path(absolute)

    assert confined_path(tree.root, absolute) is None


@pytest.mark.parametrize("relative", ["../static-other/note.txt", "../static-other"])
def test_a_sibling_folder_sharing_the_root_name_prefix_is_refused(tree: Tree, relative: str) -> None:
    resolved = (tree.root / relative).resolve()
    assert resolved.exists()
    # A comparison of the two paths as strings would take this folder for the root itself.
    assert str(resolved).startswith(str(tree.root))

    assert confined_path(tree.root, relative) is None


@pytest.mark.parametrize("link_name", ["linked-folder/marker.txt", "linked-file.txt"])
def test_a_symlink_inside_the_root_pointing_outside_is_refused(tree: Tree, link_name: str) -> None:
    _symlink_or_skip(tree.root / "linked-folder", tree.outside.parent)
    _symlink_or_skip(tree.root / "linked-file.txt", tree.outside)
    # Through the link, the file outside is reachable from inside the root.
    assert (tree.root / link_name).read_text() == tree.outside.read_text()

    assert confined_path(tree.root, link_name) is None


@pytest.mark.parametrize("relative", ["favicon\x00.png", "\x00", "assets/\x00/../favicon.png"], ids=["inside-a-name", "alone", "inside-a-segment"])
def test_a_path_the_os_cannot_represent_is_refused(tree: Tree, relative: str) -> None:
    assert confined_path(tree.root, relative) is None
