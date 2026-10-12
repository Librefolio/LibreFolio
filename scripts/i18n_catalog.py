"""The frontend translation catalogue: its sources, who owns each key, and the generated files.

The catalogue the app loads, ``frontend/src/lib/i18n/<lang>.json``, is **generated**: never edit it. Its sources are

- ``frontend/src/lib/i18n/base/<lang>.json`` — the generic vocabulary; it owns every key nobody else claims;
- ``frontend/src/lib/i18n/<subsystem>/<lang>.json`` — one folder per subsystem; its ``prefixes.txt`` declares the
  key prefixes it owns, one per line (``#`` starts a comment);
- ``backend/app/services/<family>/<plugin>/i18n/<lang>.json`` — a plugin's own keys, in the ``*_providers`` and
  ``*_plugins`` families. A plugin owns exactly the keys its files hold.

Every source is nested JSON with absolute keys. A key belongs to the plugin that defines it, otherwise to the
subsystem with the longest declared prefix, otherwise to ``base``. A key defined twice, or a string in one source and a
branch in another, is an error. English is mandatory: a key missing in another language is filled from English with a
warning when building, and is an error under ``strict`` (``dev.py i18n check --strict``, the audit and its gate).

Python 3.9 compatible, stdlib only: the npm hooks run it with the system ``python3``.
"""

from __future__ import annotations

import argparse
import fnmatch
import hashlib
import json
import stat
import subprocess
import sys
import tempfile
from collections import OrderedDict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Set, Tuple

ROOT = Path(__file__).resolve().parents[1]
I18N_RELATIVE = Path("frontend") / "src" / "lib" / "i18n"
SERVICES_RELATIVE = Path("backend") / "app" / "services"
BASE_NAME = "base"
PREFIXES_FILE = "prefixes.txt"
STAMP_NAME = ".generated"
PLUGIN_I18N_DIR = "i18n"
PLUGIN_FAMILY_GLOBS = ("*_providers", "*_plugins")
SOURCE_LANGUAGE = "en"
LANGUAGE_ORDER = ("en", "it", "fr", "es")

Nested = Dict[str, object]
Flat = Dict[str, object]


class CatalogError(Exception):
    """The sources cannot give a catalogue; ``problems`` lists every reason found."""

    def __init__(self, problems: List[str]):
        self.problems = list(problems)
        super().__init__("\n".join(self.problems))


@dataclass
class Source:
    """One source of keys: ``base``, a subsystem folder or a plugin's ``i18n`` folder."""

    kind: str
    name: str
    folder: Path
    prefixes: Tuple[str, ...] = ()
    catalogs: Dict[str, Nested] = field(default_factory=dict)
    touched: bool = False

    def file(self, language: str) -> Path:
        return self.folder / f"{language}.json"


@dataclass
class Merged:
    """The merged catalogue of each language, the owner of every key, the warnings met."""

    catalogs: Dict[str, Nested]
    owners: Dict[str, Source]
    warnings: List[str]


# --------------------------------------------------------------------------------------------------------------
# Nested JSON


def flatten(nested: Nested, prefix: str = "") -> Flat:
    out: Flat = OrderedDict()
    for key, value in nested.items():
        full = f"{prefix}.{key}" if prefix else key
        if isinstance(value, dict):
            out.update(flatten(value, full))
        else:
            out[full] = value
    return out


def set_nested(nested: Nested, key: str, value: object) -> None:
    node = nested
    parts = key.split(".")
    for part in parts[:-1]:
        child = node.get(part)
        if child is None:
            child = OrderedDict()
            node[part] = child
        elif not isinstance(child, dict):
            raise CatalogError([f"{key}: '{part}' is a string and cannot hold children"])
        node = child
    if isinstance(node.get(parts[-1]), dict):
        raise CatalogError([f"{key}: is a branch and cannot become a string"])
    node[parts[-1]] = value


def delete_nested(nested: Nested, key: str) -> bool:
    """Remove ``key``, a string or a whole branch, and prune the parents it leaves empty."""
    parts = key.split(".")
    trail = []
    node: object = nested
    for part in parts[:-1]:
        if not isinstance(node, dict) or part not in node:
            return False
        trail.append((node, part))
        node = node[part]
    if not isinstance(node, dict) or parts[-1] not in node:
        return False
    del node[parts[-1]]
    for parent, part in reversed(trail):
        if isinstance(parent[part], dict) and not parent[part]:
            del parent[part]
        else:
            break
    return True


def under(key: str, prefix: str) -> bool:
    return key == prefix or key.startswith(prefix + ".")


def dumps(nested: Nested) -> str:
    return json.dumps(nested, ensure_ascii=False, indent=2) + "\n"


def loads(text: str) -> Nested:
    return json.loads(text, object_pairs_hook=OrderedDict)


# --------------------------------------------------------------------------------------------------------------
# Discovery


def i18n_dir(root: Path = ROOT) -> Path:
    return root / I18N_RELATIVE


def languages(root: Path = ROOT) -> List[str]:
    """The languages of ``base``: English first, then the usual order, then any other by name."""
    found = {path.stem for path in (i18n_dir(root) / BASE_NAME).glob("*.json")}
    if SOURCE_LANGUAGE not in found:
        raise CatalogError([f"{(I18N_RELATIVE / BASE_NAME / (SOURCE_LANGUAGE + '.json')).as_posix()} is missing"])
    ordered = [language for language in LANGUAGE_ORDER if language in found]
    return ordered + sorted(found - set(ordered))


def generated_catalogs(root: Path = ROOT) -> List[Path]:
    """The files ``build`` writes, one per language of ``base``; none where there is no ``base`` to build them from."""
    if not (i18n_dir(root) / BASE_NAME / f"{SOURCE_LANGUAGE}.json").is_file():
        return []
    return [i18n_dir(root) / f"{language}.json" for language in languages(root)]


def read_prefixes(path: Path) -> Tuple[str, ...]:
    prefixes = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.split("#", 1)[0].strip()
        if line:
            prefixes.append(line)
    return tuple(prefixes)


def plugin_i18n_dirs(root: Path = ROOT) -> List[Path]:
    services = root / SERVICES_RELATIVE
    found = set()
    for pattern in PLUGIN_FAMILY_GLOBS:
        for family in services.glob(pattern):
            if family.is_dir():
                found.update(path for path in family.glob(f"*/{PLUGIN_I18N_DIR}") if path.is_dir())
    return sorted(found)


def plugin_name(i18n_folder: Path, root: Path = ROOT) -> str:
    return i18n_folder.parent.relative_to(root / SERVICES_RELATIVE).as_posix()


def discover(root: Path = ROOT) -> List[Source]:
    """Every source, not yet read: ``base``, then the subsystems by name, then the plugins by path."""
    folder = i18n_dir(root)
    sources = [Source("base", BASE_NAME, folder / BASE_NAME)]
    for sub in sorted(p for p in folder.iterdir() if p.is_dir() and p.name != BASE_NAME and not p.name.startswith((".", "_"))):
        prefix_file = sub / PREFIXES_FILE
        sources.append(Source("subsystem", sub.name, sub, read_prefixes(prefix_file) if prefix_file.is_file() else ()))
    for i18n_folder in plugin_i18n_dirs(root):
        sources.append(Source("plugin", plugin_name(i18n_folder, root), i18n_folder))
    return sources


def load(root: Path = ROOT) -> Tuple[List[str], List[Source]]:
    langs = languages(root)
    sources = discover(root)
    problems = []
    for source in sources:
        for path in sorted(source.folder.glob("*.json")):
            relative = path.relative_to(root).as_posix()
            if path.stem not in langs:
                problems.append(f"{relative}: '{path.stem}' is not one of base's languages {langs}")
                continue
            try:
                source.catalogs[path.stem] = loads(path.read_text(encoding="utf-8"))
            except (OSError, ValueError) as exc:
                problems.append(f"{relative}: unreadable JSON ({exc})")
    if problems:
        raise CatalogError(problems)
    return langs, sources


def save(sources: Iterable[Source]) -> List[Path]:
    """Write every touched source; a plugin source left empty loses its files."""
    written = []
    for source in sources:
        if not source.touched:
            continue
        empty = all(not catalog for catalog in source.catalogs.values())
        if empty and source.kind == "plugin":
            for path in source.folder.glob("*.json"):
                path.unlink()
            if source.folder.is_dir() and not any(source.folder.iterdir()):
                source.folder.rmdir()
            continue
        source.folder.mkdir(parents=True, exist_ok=True)
        for language, catalog in source.catalogs.items():
            path = source.file(language)
            text = dumps(catalog)
            if not path.exists() or path.read_text(encoding="utf-8") != text:
                path.write_text(text, encoding="utf-8")
                written.append(path)
    return written


# --------------------------------------------------------------------------------------------------------------
# Ownership and merge


def declared_owner(key: str, sources: Iterable[Source]) -> Optional[Source]:
    """The subsystem with the longest declared prefix of ``key``; None means ``base``."""
    best: Optional[Tuple[int, Source]] = None
    for source in sources:
        if source.kind != "subsystem":
            continue
        for prefix in source.prefixes:
            if under(key, prefix) and (best is None or len(prefix) > best[0]):
                best = (len(prefix), source)
    return best[1] if best else None


def display_path(path: Path, root: Path = ROOT) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()


def _prefix_problems(sources: List[Source], root: Path) -> List[str]:
    """Every subsystem declares at least one prefix, and no prefix is declared twice."""
    problems: List[str] = []
    declared: Dict[str, str] = {}
    for source in sources:
        if source.kind != "subsystem":
            continue
        if not source.prefixes:
            problems.append(f"{display_path(source.folder, root)}: declares no prefix ({PREFIXES_FILE} missing or empty)")
        for prefix in source.prefixes:
            if declared.get(prefix) == source.name:
                problems.append(f"prefix '{prefix}' is declared twice in '{source.name}'")
            elif prefix in declared:
                problems.append(f"prefix '{prefix}' is declared by both '{declared[prefix]}' and '{source.name}'")
            declared[prefix] = source.name
    return problems


def _owners(sources: List[Source], root: Path) -> Tuple[Dict[str, Source], Dict[str, Flat], List[str]]:
    """The owner of every key (from the English files), each source's English keys, and the clashes found."""
    problems: List[str] = []
    owners: Dict[str, Source] = {}
    english: Dict[str, Flat] = {}
    for source in sources:
        if SOURCE_LANGUAGE not in source.catalogs:
            if source.catalogs or source.kind == "base":
                problems.append(f"{display_path(source.file(SOURCE_LANGUAGE), root)} is missing: English is mandatory")
            continue
        keys = flatten(source.catalogs[SOURCE_LANGUAGE])
        english[source.name] = keys
        for key in keys:
            if key in owners:
                problems.append(f"{key}: defined in both '{owners[key].name}' and '{source.name}'")
            else:
                owners[key] = source
    # A key that is also the ancestor of another: a string in one source and a branch in another (or the same one).
    for key, source in owners.items():
        parts = key.split(".")
        for depth in range(1, len(parts)):
            ancestor = ".".join(parts[:depth])
            if ancestor in owners:
                problems.append(f"{ancestor}: a string in '{owners[ancestor].name}' and a branch in '{source.name}' ({key})")
    return owners, english, problems


def _placement_problems(owners: Dict[str, Source], sources: List[Source]) -> List[str]:
    """A base or subsystem key sits where the longest declared prefix says; a plugin owns what it holds."""
    problems = []
    for key, source in owners.items():
        if source.kind == "plugin":
            continue
        expected = declared_owner(key, sources)
        expected_name = expected.name if expected else BASE_NAME
        if expected_name != source.name:
            problems.append(f"{key}: is in '{source.name}', but its prefix belongs to '{expected_name}'")
    return problems


def _merge_language(merged: Nested, source: Source, language: str, keys: Flat, strict: bool, fill: bool, root: Path) -> Tuple[List[str], List[str]]:
    """Add one source's keys in one language: its own order first, then (``fill``) English for what it lacks."""
    problems: List[str] = []
    warnings: List[str] = []
    catalog = source.catalogs.get(language)
    values = flatten(catalog) if catalog is not None else OrderedDict()
    path = display_path(source.file(language), root)
    extra = [key for key in values if key not in keys]
    if extra:
        problems.append(f"{path}: {len(extra)} key(s) English does not have, e.g. {extra[0]}")
    not_text = [key for key, value in values.items() if not isinstance(value, str)]
    if not_text:
        problems.append(f"{path}: {len(not_text)} value(s) not a string, e.g. {not_text[0]}")
    missing = [key for key in keys if key not in values]
    if missing:
        message = f"{path}: {len(missing)} key(s) missing, e.g. {missing[0]}"
        if strict:
            problems.append(message)
        elif fill:
            warnings.append(message + " (English used)")
    entries = [(key, value) for key, value in values.items() if key in keys]
    if fill:
        entries += [(key, keys[key]) for key in missing]
    for key, value in entries:
        # A string against a branch has already been reported by _owners, with both sources: skip it here.
        if _settable(merged, key):
            set_nested(merged, key, value)
    return problems, warnings


def _settable(nested: Nested, key: str) -> bool:
    """Whether ``set_nested`` can put a string at ``key`` without turning a string into a branch or the reverse."""
    node = nested
    parts = key.split(".")
    for part in parts[:-1]:
        child = node.get(part)
        if child is None:
            return True
        if not isinstance(child, dict):
            return False
        node = child
    return not isinstance(node.get(parts[-1]), dict)


def merge(langs: List[str], sources: List[Source], strict: bool = False, root: Path = ROOT, fill: bool = True) -> Merged:
    """Merge the sources; raise ``CatalogError`` with every problem, or return the catalogues and the warnings.

    ``fill``: a key a language lacks takes the English text (what the build ships); without it the catalogue of each
    language holds only the translations its sources really have.
    """
    problems = _prefix_problems(sources, root)
    owners, english, owner_problems = _owners(sources, root)
    problems += owner_problems + _placement_problems(owners, sources)
    warnings: List[str] = []
    merged: Dict[str, Nested] = {language: OrderedDict() for language in langs}
    for source in sources:
        keys = english.get(source.name)
        if keys is None:
            continue
        for language in langs:
            language_problems, language_warnings = _merge_language(merged[language], source, language, keys, strict, fill, root)
            problems += language_problems
            warnings += language_warnings
    if problems:
        raise CatalogError(problems)
    return Merged(merged, owners, warnings)


def load_catalog(language: str, root: Path = ROOT, fallback: bool = True) -> Nested:
    """The merged catalogue of one language, built in memory, writing nothing.

    With ``fallback`` it is what the build ships: a missing translation takes the English text. Without it, only the
    translations the sources really hold — what a test checking "translated in every language" must read.
    """
    langs, sources = load(root)
    return merge(langs, sources, root=root, fill=fallback).catalogs[language]


def plugin_namespace(source: Source) -> Optional[str]:
    """The branch a plugin's keys live under: the longest common prefix of their parent paths."""
    keys = flatten(source.catalogs.get(SOURCE_LANGUAGE, {}))
    parents = [key.rsplit(".", 1)[0].split(".") for key in keys if "." in key]
    if not parents:
        return None
    common: List[str] = []
    for index in range(min(len(parts) for parts in parents)):
        segments = {parts[index] for parts in parents}
        if len(segments) != 1:
            break
        common.append(segments.pop())
    return ".".join(common) or None


def route(key: str, sources: List[Source], owners: Dict[str, Source]) -> Source:
    """Where a new ``key`` goes.

    Look at the key's deepest existing ancestor. When every key under it belongs to one plugin and the ancestor lies
    within that plugin's own branch (``plugin_namespace``), the plugin: a new field of an existing plugin. When the
    keys under it belong only to plugins otherwise (``brimPlugins``: a new plugin; ``assets.providerParams``, whose one
    plugin is another provider), there is no safe guess, and the answer is ``--into``. Otherwise the subsystem with the
    longest declared prefix, then ``base``.
    """
    parts = key.split(".")
    for depth in range(len(parts) - 1, 0, -1):
        ancestor = ".".join(parts[:depth])
        found = {id(source): source for k, source in owners.items() if under(k, ancestor)}
        if not found:
            continue
        holders = list(found.values())
        if all(source.kind == "plugin" for source in holders):
            namespace = plugin_namespace(holders[0]) if len(holders) == 1 else None
            if namespace is not None and under(ancestor, namespace):
                return holders[0]
            names = ", ".join(sorted(source.name for source in holders)[:3]) + (", …" if len(holders) > 3 else "")
            raise CatalogError([f"{key}: the keys under '{ancestor}' belong to plugins ({names}); name the target with --into <family>/<plugin>"])
        break
    owner = declared_owner(key, sources)
    if owner is not None:
        return owner
    return next(source for source in sources if source.kind == "base")


def _is_plugin_family(name: str) -> bool:
    return any(fnmatch.fnmatchcase(name, pattern) for pattern in PLUGIN_FAMILY_GLOBS)


def resolve_target(into: str, sources: List[Source], root: Path = ROOT) -> Source:
    """A target folder from ``--into``: ``base``, a subsystem name, or a plugin (``<family>/<plugin>`` or its path).

    A plugin target is exactly ``<family>/<plugin>``, the family one discovery reads (``*_providers``, ``*_plugins``)
    and the folder a plugin (``plugin.py``): anything else would write keys no catalogue reads.
    """
    by_name = {source.name: source for source in sources}
    text = into.strip().rstrip("/")
    for marker in (SERVICES_RELATIVE.as_posix() + "/", "services/"):
        if marker in text:
            text = text.split(marker, 1)[1]
    if text.endswith("/" + PLUGIN_I18N_DIR):
        text = text[: -len(PLUGIN_I18N_DIR) - 1]
    if text in by_name:
        return by_name[text]
    if "/" in text:
        parts = text.split("/")
        plugin_folder = root / SERVICES_RELATIVE / text
        if len(parts) != 2 or not _is_plugin_family(parts[0]) or parts[1].startswith(("_", ".")):
            raise CatalogError([f"--into {into}: a plugin target is <family>/<plugin>, the family one of {', '.join(PLUGIN_FAMILY_GLOBS)}"])
        if not (plugin_folder / "plugin.py").is_file():
            raise CatalogError([f"--into {into}: {(SERVICES_RELATIVE / text).as_posix()} is not a plugin folder (no plugin.py)"])
        source = Source("plugin", text, plugin_folder / PLUGIN_I18N_DIR)
        sources.append(source)
        return source
    raise CatalogError([f"--into {into}: no subsystem '{text}' (create {(I18N_RELATIVE / text / PREFIXES_FILE).as_posix()} first)"])


# --------------------------------------------------------------------------------------------------------------
# Changes to the sources


def move(prefix: str, into: str, root: Path = ROOT) -> int:
    """Move every key under ``prefix`` (or the key itself), in every language, into the ``into`` folder."""
    langs, sources = load(root)
    target = resolve_target(into, sources, root)
    moved = 0
    for source in list(sources):
        if source is target:
            continue
        for language, catalog in source.catalogs.items():
            keys = [key for key in flatten(catalog) if under(key, prefix)]
            if not keys:
                continue
            values = flatten(catalog)
            for key in keys:
                set_nested(target.catalogs.setdefault(language, OrderedDict()), key, values[key])
                delete_nested(catalog, key)
            source.touched = target.touched = True
            if language == SOURCE_LANGUAGE:
                moved += len(keys)
    if not moved:
        raise CatalogError([f"no key under '{prefix}' outside {target.name}"])
    merge(langs, sources, root=root)
    save(sources)
    return moved


def split(root: Path = ROOT) -> Dict[str, int]:
    """Put every base and subsystem key in the folder its declared prefixes name; returns the keys moved per target."""
    langs, sources = load(root)
    by_name = {source.name: source for source in sources}
    plan: Dict[Tuple[str, str], List[str]] = OrderedDict()
    for source in sources:
        if source.kind == "plugin" or SOURCE_LANGUAGE not in source.catalogs:
            continue
        for key in flatten(source.catalogs[SOURCE_LANGUAGE]):
            owner = declared_owner(key, sources)
            target = owner.name if owner else BASE_NAME
            if target != source.name:
                plan.setdefault((source.name, target), []).append(key)
    counts: Dict[str, int] = OrderedDict()
    for (from_name, to_name), keys in plan.items():
        origin, target = by_name[from_name], by_name[to_name]
        for language, catalog in origin.catalogs.items():
            values = flatten(catalog)
            for key in keys:
                if key in values:
                    set_nested(target.catalogs.setdefault(language, OrderedDict()), key, values[key])
                    delete_nested(catalog, key)
        origin.touched = target.touched = True
        counts[to_name] = counts.get(to_name, 0) + len(keys)
    merge(langs, sources, root=root)
    save(sources)
    return counts


def set_key(key: str, values: Dict[str, str], into: Optional[str] = None, root: Path = ROOT, create: bool = True) -> Source:
    """Add (``create``) or update ``key`` with ``values`` per language, in its owner; returns that owner."""
    langs, sources = load(root)
    merged = merge(langs, sources, root=root)
    if key in merged.owners:
        if create:
            raise CatalogError([f"{key}: already exists in '{merged.owners[key].name}'"])
        target = merged.owners[key]
    else:
        if not create:
            raise CatalogError([f"{key}: does not exist"])
        target = resolve_target(into, sources, root) if into else route(key, sources, merged.owners)
    for language, value in values.items():
        if language not in langs:
            raise CatalogError([f"{key}: unknown language '{language}'"])
        set_nested(target.catalogs.setdefault(language, OrderedDict()), key, value)
    target.touched = True
    merge(langs, sources, root=root)
    save(sources)
    return target


def remove_key(key: str, root: Path = ROOT) -> List[str]:
    """Remove ``key`` (or the branch under it) from every source and language; returns the sources touched."""
    langs, sources = load(root)
    names = []
    for source in sources:
        for catalog in source.catalogs.values():
            if delete_nested(catalog, key):
                source.touched = True
        if source.touched:
            names.append(source.name)
    if not names:
        raise CatalogError([f"{key}: not found"])
    merge(langs, sources, root=root)
    save(sources)
    return names


def where(key: str, root: Path = ROOT) -> str:
    """The file that holds ``key``, or the one ``add`` would write it to."""
    langs, sources = load(root)
    merged = merge(langs, sources, root=root)
    if key in merged.owners:
        return f"{display_path(merged.owners[key].file(SOURCE_LANGUAGE), root)} (exists)"
    branch = [k for k in merged.owners if k.startswith(key + ".")]
    if branch:
        holders = sorted({merged.owners[k].name for k in branch})
        return f"branch of {len(branch)} key(s) in: {', '.join(holders)}"
    target = route(key, sources, merged.owners)
    notice = base_namespace_notice(key, target, merged.owners)
    return f"{display_path(target.file(SOURCE_LANGUAGE), root)} (new key" + (f"; {notice})" if notice else ")")


def base_namespace_notice(key: str, target: Source, owners: Dict[str, Source]) -> Optional[str]:
    """What ``add`` says when ``key`` opens a top-level namespace in ``base``, which holds only the generic vocabulary.

    ``owners`` are the keys before the addition. ``None`` when the key goes elsewhere or its namespace already exists.
    """
    namespace = key.split(".")[0]
    if target.kind != "base" or any(under(other, namespace) for other in owners):
        return None
    return f"'{namespace}' is a new namespace in base, the generic vocabulary: if it belongs to a subsystem or a plugin, use --into, or move it (dev.py i18n move {namespace} --into <subsystem|family/plugin>)"


# --------------------------------------------------------------------------------------------------------------
# Revisions: comparison and absorption of changes made on the legacy layout


def _git_show(root: Path, rev: str, path: str) -> Optional[str]:
    result = subprocess.run(["git", "-C", str(root), "show", f"{rev}:{path}"], capture_output=True, text=True, encoding="utf-8")
    return result.stdout if result.returncode == 0 else None


def _verify_revision(root: Path, rev: str) -> None:
    result = subprocess.run(["git", "-C", str(root), "rev-parse", "--verify", "--quiet", f"{rev}^{{commit}}"], capture_output=True, text=True, encoding="utf-8")
    if result.returncode != 0:
        raise CatalogError([f"{rev}: not a commit of this repository"])


def catalogs_at(rev: str, root: Path = ROOT) -> Dict[str, Flat]:
    """The flat catalogue of every language at ``rev``, as its sources hold it (no English fallback): the tracked
    monolith of the legacy layout, or the merge of the sources tracked at ``rev``."""
    _verify_revision(root, rev)
    legacy = {}
    for language in LANGUAGE_ORDER:
        text = _git_show(root, rev, (I18N_RELATIVE / f"{language}.json").as_posix())
        if text is not None:
            legacy[language] = flatten(loads(text))
    if legacy:
        return legacy
    listing = subprocess.run(
        ["git", "-C", str(root), "ls-tree", "-r", "--name-only", rev, "--", I18N_RELATIVE.as_posix(), SERVICES_RELATIVE.as_posix()],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    ).stdout.split()
    wanted = []
    for path in listing:
        parts = Path(path).parts
        in_i18n = path.startswith(I18N_RELATIVE.as_posix() + "/") and len(parts) == len(I18N_RELATIVE.parts) + 2 and (path.endswith(".json") or path.endswith("/" + PREFIXES_FILE))
        in_plugin = path.startswith(SERVICES_RELATIVE.as_posix() + "/") and f"/{PLUGIN_I18N_DIR}/" in path and path.endswith(".json")
        if in_i18n or in_plugin:
            wanted.append(path)
    with tempfile.TemporaryDirectory() as tmp:
        tmp_root = Path(tmp)
        for path in wanted:
            target = tmp_root / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(_git_show(root, rev, path) or "", encoding="utf-8")
        for path in wanted:  # a plugin source needs its plugin.py to be one
            if f"/{PLUGIN_I18N_DIR}/" in path:
                (tmp_root / path).parent.parent.joinpath("plugin.py").touch()
        langs, sources = load(tmp_root)
        merged = merge(langs, sources, root=tmp_root, fill=False)
        return {language: flatten(merged.catalogs[language]) for language in langs}


def compare(expected: Dict[str, Flat], actual: Dict[str, Flat]) -> List[str]:
    differences = []
    for language in sorted(set(expected) | set(actual), key=lambda lang: (LANGUAGE_ORDER + (lang,)).index(lang)):
        before, after = expected.get(language, {}), actual.get(language, {})
        missing = [key for key in before if key not in after]
        extra = [key for key in after if key not in before]
        changed = [key for key in before if key in after and before[key] != after[key]]
        if missing or extra or changed:
            differences.append(f"{language}: {len(missing)} missing, {len(extra)} extra, {len(changed)} changed" + "".join(f"; e.g. {kind} {keys[0]}" for kind, keys in (("missing", missing), ("extra", extra), ("changed", changed)) if keys))
    return differences


ABSENT = object()  # a key a catalogue does not have (distinct from any JSON value, ``null`` included)
Values = Dict[str, Flat]


def _shown(value: object) -> str:
    if value is ABSENT:
        return "(absent)"
    text = json.dumps(value, ensure_ascii=False)
    return text if len(text) <= 60 else text[:57] + "..."


def _apply_theirs(key: str, language: str, value: object, sources: List[Source], owners: Dict[str, Source]) -> Optional[str]:
    """Set (or, ``value`` absent, delete) ``key`` in one language, in its owner; a new key goes where ``add`` puts it.
    Returns a problem, or ``None``."""
    owner = owners.get(key)
    if value is ABSENT:
        if owner is not None and delete_nested(owner.catalogs.get(language, OrderedDict()), key):
            owner.touched = True
        return None
    if owner is None:
        try:
            owner = owners[key] = route(key, sources, owners)
        except CatalogError as exc:
            return "; ".join(exc.problems) + f" (absorb cannot choose: add it first with `dev.py i18n add {key} --into ...` and its values, then absorb again)"
    try:
        set_nested(owner.catalogs.setdefault(language, OrderedDict()), key, value)
    except CatalogError as exc:
        return f"{language} " + "; ".join(exc.problems)
    owner.touched = True
    return None


def _removal_conflicts(before: Values, after: Values, mine: Values, langs: List[str]) -> Dict[str, str]:
    """The keys one side removed while the other gave one of their translations a new text: for each, the conflict.

    Whether a key exists is decided by its English, so such a conflict is about the whole key: ``--prefer`` settles it
    in every language at once, as the preferred side has it. A side that only dropped translations of the key does not
    conflict with its removal.
    """
    found: Dict[str, str] = OrderedDict()
    for key in before.get(SOURCE_LANGUAGE, {}):
        gone_theirs = key not in after.get(SOURCE_LANGUAGE, {})
        gone_ours = key not in mine.get(SOURCE_LANGUAGE, {})
        if gone_theirs == gone_ours:
            continue
        keeper, remover = ("ours", "theirs") if gone_theirs else ("theirs", "ours")
        kept = mine if gone_theirs else after
        texts = []
        for language in langs:
            old, new = before.get(language, {}).get(key, ABSENT), kept.get(language, {}).get(key, ABSENT)
            if new is not ABSENT and new != old:
                texts.append(f"{language} {_shown(old)} → {_shown(new)}")
        if texts:
            found[key] = f"{key}: removed by {remover}, while {keeper} changed it: " + ", ".join(texts)
    return found


def _settle_removals(removals: Dict[str, str], prefer: Optional[str], after: Values, langs: List[str], sources: List[Source], owners: Dict[str, Source], tally: Dict[str, Set[str]]) -> List[str]:
    """Apply ``prefer="theirs"`` to the removal conflicts (``ours`` is already what the sources hold); returns problems."""
    problems: List[str] = []
    if prefer != "theirs":
        return problems
    for key in removals:
        for language in langs:
            problem = _apply_theirs(key, language, after.get(language, {}).get(key, ABSENT), sources, owners)
            if problem:
                problems.append(problem)
        tally["added" if key in after.get(SOURCE_LANGUAGE, {}) else "removed"].add(key)
    return problems


def _absorb_language(language: str, old: Flat, new: Flat, mine: Flat, prefer: Optional[str], sources: List[Source], owners: Dict[str, Source], tally: Dict[str, Set[str]], skip: Dict[str, str]) -> Tuple[List[str], List[str]]:
    """The three-way merge of one language, ``skip`` (the removal conflicts) aside; returns the problems and conflicts."""
    problems: List[str] = []
    conflicts: List[str] = []
    removed_first = [key for key in old if key not in new]  # a removed string may make room for a new branch
    for key in removed_first + list(new):
        if key in skip:
            continue
        base, theirs, ours = old.get(key, ABSENT), new.get(key, ABSENT), mine.get(key, ABSENT)
        if theirs == base:
            continue
        if ours == theirs:
            tally["already"].add(key)
            continue
        if ours != base:
            conflicts.append(f"{language} {key}: base {_shown(base)}, ours {_shown(ours)}, theirs {_shown(theirs)}")
            if prefer != "theirs":
                continue
        problem = _apply_theirs(key, language, theirs, sources, owners)
        if problem:
            problems.append(problem)
        elif language == SOURCE_LANGUAGE and base is ABSENT and ours is ABSENT:
            tally["added"].add(key)
        elif language == SOURCE_LANGUAGE and theirs is ABSENT:
            tally["removed"].add(key)
        else:
            tally["changed"].add(key)
    return problems, conflicts


def absorb(base_rev: str, theirs_rev: str, root: Path = ROOT, prefer: Optional[str] = None) -> Dict[str, int]:
    """Replay on the sources the changes ``theirs_rev`` made to the catalogue since ``base_rev``, language by language.

    A three-way merge per key and language: ``base`` (at ``base_rev``), ``ours`` (the sources here) and ``theirs``.
    What ``theirs`` did not change is left alone; what only ``theirs`` changed is applied, a new key going where ``add``
    would put it; what both changed to the same value is already there. What both changed differently is a conflict,
    and so is a key one side removed while the other changed one of its translations (settled whole, in every
    language). Without ``prefer`` every conflict is reported and nothing is written; ``prefer`` (``ours`` or
    ``theirs``) settles them all one way. All or nothing: any problem writes nothing.
    """
    if prefer not in (None, "ours", "theirs"):
        raise CatalogError([f"--prefer {prefer}: expected 'ours' or 'theirs'"])
    before, after = catalogs_at(base_rev, root), catalogs_at(theirs_rev, root)
    langs, sources = load(root)
    current = merge(langs, sources, root=root, fill=False)
    owners = dict(current.owners)
    ordered = [SOURCE_LANGUAGE] + [lang for lang in langs if lang != SOURCE_LANGUAGE]
    mine = {language: flatten(current.catalogs.get(language, OrderedDict())) for language in ordered}
    tally: Dict[str, Set[str]] = {"added": set(), "changed": set(), "removed": set(), "already": set()}
    removals = _removal_conflicts(before, after, mine, ordered)
    conflicts = list(removals.values())
    problems = _settle_removals(removals, prefer, after, ordered, sources, owners, tally)
    for language in ordered:
        language_problems, language_conflicts = _absorb_language(language, before.get(language, {}), after.get(language, {}), mine[language], prefer, sources, owners, tally, removals)
        problems += language_problems
        conflicts += language_conflicts
    if conflicts and prefer is None:
        problems += [f"conflict (base/ours/theirs differ; settle with --prefer ours|theirs): {line}" for line in conflicts]
    if problems:
        raise CatalogError(list(OrderedDict.fromkeys(problems)))
    merge(langs, sources, root=root)
    save(sources)
    settled = tally["added"] | tally["removed"]
    changed = tally["changed"] - settled
    return {
        "added": len(tally["added"]),
        "changed": len(changed),
        "removed": len(tally["removed"]),
        "already": len(tally["already"] - settled - changed),
        "conflicts": len(conflicts),
    }


# --------------------------------------------------------------------------------------------------------------
# Generated files


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _read_stamp(path: Path) -> Dict[str, str]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def _write_generated(path: Path, text: str) -> None:
    if path.exists():
        path.chmod(path.stat().st_mode | stat.S_IWUSR)
    path.write_text(text, encoding="utf-8")
    path.chmod(stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH)


def _print_problems(title: str, problems: List[str]) -> None:
    print(title, file=sys.stderr)
    for problem in problems:
        print(f"  ✗ {problem}", file=sys.stderr)


def _hand_edited(out_dir: Path, texts: Dict[str, str], stamp: Dict[str, str], root: Path) -> List[str]:
    """The generated files whose content is neither what this build writes nor what the last build wrote."""
    edited = []
    for language, text in texts.items():
        path = out_dir / f"{language}.json"
        if path.exists() and language in stamp:
            current = path.read_text(encoding="utf-8")
            if current != text and _sha(current) != stamp[language]:
                edited.append(display_path(path, root))
    return edited


def build(root: Path = ROOT, strict: bool = False, force: bool = False, quiet: bool = False) -> int:
    """Write the generated catalogues when they change; refuse to overwrite a hand edit unless ``force``."""
    try:
        langs, sources = load(root)
        merged = merge(langs, sources, strict=strict, root=root)
    except CatalogError as exc:
        _print_problems("i18n catalogue: cannot build", exc.problems)
        return 1
    for warning in merged.warnings:
        print(f"  ⚠ i18n: {warning}", file=sys.stderr)
    out_dir = i18n_dir(root)
    stamp_path = out_dir / STAMP_NAME
    stamp = _read_stamp(stamp_path)
    texts = {language: dumps(merged.catalogs[language]) for language in langs}
    edited = [] if force else _hand_edited(out_dir, texts, stamp, root)
    if edited:
        _print_problems(
            "i18n catalogue: generated file(s) edited by hand; move the change to its source (`dev.py i18n where <key>`), then build again:",
            edited,
        )
        return 1
    changed = []
    for language, text in texts.items():
        path = out_dir / f"{language}.json"
        if not path.exists() or path.read_text(encoding="utf-8") != text:
            _write_generated(path, text)
            changed.append(language)
    new_stamp = {language: _sha(text) for language, text in texts.items()}
    if new_stamp != stamp:
        stamp_path.write_text(json.dumps(new_stamp, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if not quiet:
        total = len(flatten(merged.catalogs[SOURCE_LANGUAGE]))
        used = sum(1 for source in sources if SOURCE_LANGUAGE in source.catalogs)
        state = f"rewrote {', '.join(changed)}" if changed else "up to date"
        print(f"i18n catalogue: {total} keys × {len(langs)} languages from {used} source(s); {state}")
    return 0


def check(root: Path = ROOT, strict: bool = True, against: Optional[str] = None) -> int:
    """Validate the sources (``strict``: every language complete); with ``against``, also require their content, per
    language and without English fallback, to equal the catalogue at that revision."""
    try:
        langs, sources = load(root)
        merged = merge(langs, sources, strict=strict, root=root)
        reference = catalogs_at(against, root) if against else None
    except CatalogError as exc:
        _print_problems("i18n catalogue: check failed", exc.problems)
        return 1
    for warning in merged.warnings:
        print(f"  ⚠ i18n: {warning}", file=sys.stderr)
    if reference is not None:
        current = {language: flatten(catalog) for language, catalog in merge(langs, sources, root=root, fill=False).catalogs.items()}
        differences = compare(reference, current)
        if differences:
            _print_problems(f"i18n catalogue: differs from {against}", differences)
            return 1
        print(f"i18n catalogue: identical to {against} in {len(langs)} languages")
    by_kind: Dict[str, int] = {}
    for source in sources:
        if SOURCE_LANGUAGE in source.catalogs:
            by_kind[source.kind] = by_kind.get(source.kind, 0) + 1
    print(f"i18n catalogue: {len(merged.owners)} keys, sources " + ", ".join(f"{kind} {count}" for kind, count in sorted(by_kind.items())) + (", strict" if strict else ""))
    return 0


# --------------------------------------------------------------------------------------------------------------
# Command line (``dev.py i18n`` wraps the same functions)


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="The frontend translation catalogue (see the module docstring).")
    sub = parser.add_subparsers(dest="command")
    p_build = sub.add_parser("build", help="write the generated catalogues")
    p_build.add_argument("--strict", action="store_true", help="a missing language is an error")
    p_build.add_argument("--force", action="store_true", help="overwrite generated files edited by hand")
    p_build.add_argument("--quiet", action="store_true")
    p_check = sub.add_parser("check", help="validate the sources (strict by default)")
    p_check.add_argument("--lenient", action="store_true", help="fill missing languages from English, as the build does")
    p_check.add_argument("--against", metavar="REV", help="also require the merged catalogue to equal the one at REV")
    p_where = sub.add_parser("where", help="the file that holds, or would hold, a key")
    p_where.add_argument("key")
    args = parser.parse_args(argv)
    try:
        if args.command == "build":
            return build(strict=args.strict, force=args.force, quiet=args.quiet)
        if args.command == "check":
            return check(strict=not args.lenient, against=args.against)
        if args.command == "where":
            print(where(args.key))
            return 0
    except CatalogError as exc:
        _print_problems("i18n catalogue:", exc.problems)
        return 1
    parser.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
