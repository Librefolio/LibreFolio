#!/usr/bin/env python3
"""
Static Resource Cache Manager for LibreFolio.

Downloads external JS libraries and font resources to local directories
for offline use.  Maintains versioned cache with automatic cleanup.

Supported resource types:
  - "js"   → single-file JS library (MathJax, etc.), plus the "companions" it
             loads from beside itself (MathJax's fonts), as its bundle names them
  - "font" → multi-file Google Fonts resource (CSS + woff2 subsets)

Usage:
    python scripts/update_js_cache.py [--force]

Called automatically by:
    - dev.py server (at startup)
    - Docker build (at build time)
"""

import hashlib
import json
import re
import shutil
import sys
import urllib.parse
import urllib.request
from contextlib import suppress
from datetime import UTC, datetime
from pathlib import Path
from typing import Optional

# Configuration
MAX_CACHED_VERSIONS = 4  # Keep last N versions of each library
CACHE_MANIFEST_FILE = ".cache_manifest.json"
CACHE_CHECK_INTERVAL_HOURS = 24  # Skip check if checked within this time

# I1 (02/09): a resource that cannot be downloaded AND has no usable cached copy
# must NOT degrade the build silently (the Docker image shipped with a 404 on
# the emoji font for months — flags rendered as letters on Windows). Hard
# failures are collected here and turn into a non-zero exit code so
# `dev.py front build` / `docker build` stop instead of shipping a broken build.
#
# 21/09: I1 was right about *silence* and wrong about *scope*. It made every
# resource fatal to every build, so an asset that only the documentation ships
# — MathJax lands in `mkdocs_src/`, and `grep -rn mathjax frontend/` finds
# nothing — aborted the build of the application. On a fresh worktree that is
# fatal before any test can run, while an older worktree with a warm cache goes
# green: the two lanes differ in age, not in health, and the green one means
# nothing.
#
# So a failure is now attributed to the build that actually consumes it. The
# missing verdict was never "present" or "fail" — it was **"absent, and not
# needed for what you are building"**. The attribution is derived from
# `vendor_dir_key`, never from a resource name: a hand-written exemption list
# would rot exactly the way a hand-written directory list does.
_HARD_FAILURES: list["_Failure"] = []


class _Failure(str):
    """A hard-failure message that remembers which build consumes the resource.

    Subclasses ``str`` on purpose: the collected messages are printed and
    substring-matched by callers and tests, and that contract predates the
    attribution. The consumer rides along as an attribute instead of changing
    the element type.
    """

    consumer: str | None
    """Which build ships this resource, or ``None`` when the attribution is unknown."""

    def __new__(cls, text: str, consumer: str | None) -> "_Failure":
        failure = super().__new__(cls, text)
        failure.consumer = consumer
        return failure


def _hard_fail(name: str, reason: str) -> None:
    vendor_key = LIBRARIES.get(name, {}).get("vendor_dir_key")
    consumer = CONSUMERS.get(vendor_key) if vendor_key else None
    _HARD_FAILURES.append(_Failure(f"{name}: {reason}", consumer))

# Libraries to cache
# type="js"   → single file download
# type="font" → fetch CSS from Google Fonts, parse woff2 URLs, download all
LIBRARIES = {
    "mathjax": {
        "type": "js",
        "url": "https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js",
        "target": "tex-mml-chtml.js",
        "vendor_dir_key": "mkdocs",
        # The CHTML output loads its fonts from beside the script ([mathjax]/output/chtml/fonts/woff-v2). The script
        # alone drew every formula in the page's font: letters upright, fractions clipped (R2 M-19).
        "companions": {
            "pattern": r"MathJax_[A-Za-z0-9-]+\.woff",
            "dir": "output/chtml/fonts/woff-v2",
        },
    },
    "noto-color-emoji": {
        "type": "font",
        "css_url": "https://fonts.googleapis.com/css2?family=Noto+Color+Emoji&display=swap",
        "file_prefix": "noto-color-emoji",
        "css_file": "noto-color-emoji.css",
        "vendor_dir_key": "fonts",
        # Only the flags are served from this font — through the 'LF Flags' face of
        # frontend/static/lf-flags.css, which points at subset 0. The other subsets would be dead
        # weight, and one of them holds digits, '#' and '*'.
        "keep_unicode_ranges": ["U+1f1e6-1f1ff"],
    },
}

# Target directories (keyed by vendor_dir_key)
VENDOR_DIRS = {
    "mkdocs": Path(__file__).parent.parent / "mkdocs_src" / "docs" / "javascripts" / "vendor",
    "fonts": Path(__file__).parent.parent / "frontend" / "static" / "fonts" / "noto-color-emoji",
}

#: Which build ships each vendor directory. ``docker`` consumes both, because
#: the image copies ``mkdocs_src/site/`` alongside the frontend bundle.
CONSUMERS = {
    "mkdocs": "mkdocs",
    "fonts": "frontend",
}

# Backward compat alias
MKDOCS_VENDOR_DIR = VENDOR_DIRS["mkdocs"]


def get_file_hash(content: bytes) -> str:
    """Calculate SHA256 hash of content."""
    return hashlib.sha256(content).hexdigest()[:12]


def get_remote_headers(url: str, timeout: int = 10) -> Optional[dict]:
    """Get headers from URL using HEAD request (no download)."""
    try:
        req = urllib.request.Request(
            url,
            method="HEAD",
            headers={"User-Agent": "LibreFolio-CacheManager/1.0"}
            )
        with urllib.request.urlopen(req, timeout=timeout) as response:
            return dict(response.headers)
    except Exception:
        return None


def download_file(url: str, timeout: int = 30, ua: str = "LibreFolio-CacheManager/1.0") -> Optional[bytes]:
    """Download file from URL, return content or None on failure."""
    try:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": ua}
            )
        with urllib.request.urlopen(req, timeout=timeout) as response:
            return response.read()
    except Exception as e:
        print(f"  ⚠️  Failed to download {url}: {e}")
        return None


def load_manifest(vendor_dir: Path) -> dict:
    """Load cache manifest from vendor directory."""
    manifest_path = vendor_dir / CACHE_MANIFEST_FILE
    if manifest_path.exists():
        with suppress(Exception):  # corrupt manifest → treated as no cache
            with open(manifest_path) as f:
                return json.load(f)
    return {"libraries": {}, "versions": []}


def save_manifest(vendor_dir: Path, manifest: dict):
    """Save cache manifest to vendor directory."""
    manifest_path = vendor_dir / CACHE_MANIFEST_FILE
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)


def cleanup_old_versions(vendor_dir: Path, manifest: dict, library_name: str):
    """Remove old versions of a library, keeping MAX_CACHED_VERSIONS."""
    lib_versions = manifest.get("libraries", {}).get(library_name, {}).get("versions", [])

    while len(lib_versions) > MAX_CACHED_VERSIONS:
        old_version = lib_versions.pop(0)  # Remove oldest
        old_dir = vendor_dir / library_name / old_version["hash"]
        if old_dir.exists():
            shutil.rmtree(old_dir)
            print(f"  🗑️  Removed old version: {old_version['hash']}")


def should_skip_check(manifest: dict) -> bool:
    """Check if we should skip the update check based on last check time."""
    last_check = manifest.get("last_check")
    if not last_check:
        return False

    try:
        last_check_dt = datetime.fromisoformat(last_check.replace('Z', '+00:00'))
        if last_check_dt.tzinfo is None:
            last_check_dt = last_check_dt.replace(tzinfo=UTC)
        hours_since = (datetime.now(UTC) - last_check_dt).total_seconds() / 3600
        return hours_since < CACHE_CHECK_INTERVAL_HOURS
    except Exception:
        return False


def _parse_google_fonts_css(css_text: str):
    """
    Parse a Google Fonts CSS response into a list of subsets.

    Returns list of dicts:
      {src_url, unicode_range}
    """
    subsets = []
    # Find each @font-face block
    for match in re.finditer(r"@font-face\s*\{([^}]+)\}", css_text):
        block = match.group(1)
        url_match = re.search(r"src:\s*url\(([^)]+)\)", block)
        range_match = re.search(r"unicode-range:\s*([^;]+);", block)
        if url_match and range_match:
            subsets.append({
                "src_url": url_match.group(1).strip(),
                "unicode_range": range_match.group(1).strip(),
            })
    return subsets


def _normalise_unicode_range(unicode_range: str) -> str:
    """Compare unicode-ranges as Google writes them or as a config does: no spaces, lowercase."""
    return re.sub(r"\s+", "", unicode_range).lower()


def _kept_ranges_fingerprint(config: dict) -> Optional[list[str]]:
    """The subsets a font resource keeps, as the manifest stores them (None: every subset)."""
    keep = config.get("keep_unicode_ranges")
    if keep is None:
        return None
    return sorted({_normalise_unicode_range(r) for r in keep})


def _download_font_resource(  # noqa: C901 — flat download/manifest pipeline, no nested logic
    vendor_dir: Path, manifest: dict, name: str, config: dict, force: bool = False
) -> bool:
    """
    Download a Google Fonts resource (CSS + woff2 files).

    Fetches the CSS from Google Fonts, extracts woff2 URLs, downloads each
    subset file, and writes a local CSS with relative paths.

    With ``keep_unicode_ranges`` only the subsets whose unicode-range is in that list are kept,
    numbered from 0 in the order Google serves them. The stored fingerprint of that list is part of
    "already up-to-date", so a changed list rewrites the cache even when Google's CSS did not change.
    Files are written only once every kept subset has downloaded; then the resource's stale
    ``<prefix>.N.woff2`` files are removed.
    """
    print(f"🔤 Checking font {name}...")

    lib_data = manifest.get("libraries", {}).get(name, {})
    current_hash = lib_data.get("current_hash")
    kept_fingerprint = _kept_ranges_fingerprint(config)

    target_dir = vendor_dir
    css_path = target_dir / config["css_file"]
    file_exists = css_path.exists()

    # Fetch CSS from Google Fonts (need a modern User-Agent to get woff2)
    css_bytes = download_file(
        config["css_url"],
        ua="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
           "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    )
    if css_bytes is None:
        if file_exists:
            print("  ⚠️  CSS download failed, keeping cached version")
        else:
            print("  ❌ CSS download failed and no cached version exists")
            _hard_fail(name, "CSS download failed, no cached version")
        return False

    css_text = css_bytes.decode("utf-8")
    css_hash = get_file_hash(css_bytes)

    if current_hash == css_hash and not force and file_exists and lib_data.get("kept_unicode_ranges") == kept_fingerprint:
        print(f"  ✓ Already up-to-date (CSS hash: {css_hash})")
        return False

    # Parse subsets
    subsets = _parse_google_fonts_css(css_text)
    if not subsets:
        print("  ⚠️  No subsets found in Google Fonts CSS")
        if not file_exists:
            _hard_fail(name, "no subsets parsed, no cached version")
        return False

    if kept_fingerprint is not None:
        subsets = [subset for subset in subsets if _normalise_unicode_range(subset["unicode_range"]) in kept_fingerprint]
        if not subsets:
            print(f"  ⚠️  No subset matches keep_unicode_ranges {kept_fingerprint}")
            if not file_exists:
                _hard_fail(name, "no subset matches keep_unicode_ranges, no cached version")
            return False

    print(f"  📋 Found {len(subsets)} subsets")
    target_dir.mkdir(parents=True, exist_ok=True)

    # Download each woff2 file
    prefix = config["file_prefix"]
    local_css_lines = [
        "/*",
        f" * {name} — self-hosted subsets (Google Fonts)",
        " * Auto-downloaded by scripts/update_js_cache.py",
        f" * Source: {config['css_url']}",
        f" * Updated: {datetime.now(UTC).strftime('%Y-%m-%d')}",
        f" * Subsets: {len(subsets)}",
        " */",
        "",
    ]

    total_size = 0
    failed_subsets = 0
    downloaded: list[tuple[str, bytes]] = []
    font_family = " ".join(w.capitalize() for w in name.split("-"))
    for i, subset in enumerate(subsets):
        local_filename = f"{prefix}.{i}.woff2"
        woff2_content = download_file(subset["src_url"])
        if woff2_content is None:
            # I1: a partially cached font renders SOME glyph ranges as fallback
            # letters — the same silent degradation as a missing font. Loud.
            print(f"  ❌ Failed to download subset {i}")
            failed_subsets += 1
            continue

        downloaded.append((local_filename, woff2_content))
        total_size += len(woff2_content)

        # Build CSS block
        local_css_lines.extend([
            f"/* Subset {i} */",
            "@font-face {",
            f"\tfont-family: '{font_family}';",
            "\tfont-style: normal;",
            "\tfont-weight: 400;",
            "\tfont-display: swap;",
            f"\tsrc: url('./{local_filename}') format('woff2');",
            f"\tunicode-range: {subset['unicode_range']};",
            "}",
            "",
        ])

    if failed_subsets:
        # Do not write a partial CSS/manifest: the cached previous version (if
        # any) stays authoritative, and the build learns this is broken.
        _hard_fail(name, f"{failed_subsets}/{len(subsets)} font subsets failed to download")
        return False

    # Every subset is in hand: only now does the cache change.
    for local_filename, woff2_content in downloaded:
        with open(target_dir / local_filename, "wb") as f:
            f.write(woff2_content)
    kept_files = {local_filename for local_filename, _ in downloaded}
    for stale in target_dir.glob(f"{prefix}.*.woff2"):
        if stale.name not in kept_files:
            stale.unlink()
            print(f"  🗑️  Removed stale subset: {stale.name}")

    # Write local CSS
    css_content = "\n".join(local_css_lines) + "\n"
    with open(css_path, "w") as f:
        f.write(css_content)

    # Update manifest
    if "libraries" not in manifest:
        manifest["libraries"] = {}
    if name not in manifest["libraries"]:
        manifest["libraries"][name] = {"versions": []}

    manifest["libraries"][name]["current_hash"] = css_hash
    manifest["libraries"][name]["kept_unicode_ranges"] = kept_fingerprint
    manifest["libraries"][name]["url"] = config["css_url"]
    manifest["libraries"][name]["type"] = "font"
    manifest["libraries"][name]["subset_count"] = len(subsets)
    manifest["libraries"][name]["total_size"] = total_size
    manifest["libraries"][name]["updated_at"] = datetime.now(UTC).isoformat()
    manifest["libraries"][name]["versions"].append({
        "hash": css_hash,
        "downloaded_at": datetime.now(UTC).isoformat(),
        "subset_count": len(subsets),
        "total_size": total_size,
    })

    cleanup_old_versions(vendor_dir, manifest, name)
    print(f"  ✅ Updated {len(subsets)} subsets ({total_size / 1024:.0f} KB total)")
    return True


def update_library(vendor_dir: Path, manifest: dict, name: str, config: dict, force: bool = False) -> bool:
    """
    Update a single library.

    Returns True if updated, False if already up-to-date.
    Dispatches to type-specific handler (js or font). A js library's companions
    are checked on every run, whether the script itself changed or not.
    """
    resource_type = config.get("type", "js")
    if resource_type == "font":
        return _download_font_resource(vendor_dir, manifest, name, config, force)
    updated = _update_js_file(vendor_dir, manifest, name, config, force)
    if config.get("companions"):
        updated = _update_companions(vendor_dir, manifest, name, config, force) or updated
    return updated


def _update_js_file(vendor_dir: Path, manifest: dict, name: str, config: dict, force: bool = False) -> bool:  # noqa: C901 — flat update pipeline with guard returns, no nested logic
    """The single-file JS logic: True if the script was written, False if up to date or not downloadable."""
    print(f"📦 Checking {name}...")

    lib_data = manifest.get("libraries", {}).get(name, {})
    current_hash = lib_data.get("current_hash")
    current_etag = lib_data.get("etag")
    current_size = lib_data.get("size")

    # Check if file exists locally
    target_path = vendor_dir / name / config["target"]
    file_exists = target_path.exists()

    if not force and file_exists and current_hash:
        # Try HEAD request first to check if update needed
        headers = get_remote_headers(config["url"])
        if headers:
            remote_etag = headers.get("ETag") or headers.get("etag")
            remote_size = headers.get("Content-Length") or headers.get("content-length")

            # If ETag matches, no update needed
            if remote_etag and current_etag and remote_etag == current_etag:
                print("  ✓ Already up-to-date (ETag match)")
                return False

            # If size matches and no ETag, likely same file
            if remote_size and current_size and int(remote_size) == current_size and not remote_etag:
                print(f"  ✓ Already up-to-date (size match: {current_size} bytes)")
                return False

    # Download current version
    content = download_file(config["url"])
    if content is None:
        if file_exists:
            print("  ⚠️  Download failed, keeping cached version")
        else:
            print("  ❌ Download failed and no cached version exists")
            _hard_fail(name, "download failed, no cached version")
        return False

    # Calculate hash
    content_hash = get_file_hash(content)

    # Check if we already have this exact version
    if current_hash == content_hash and not force:
        print(f"  ✓ Already up-to-date (hash: {content_hash})")
        return False

    # Create directory structure
    lib_dir = vendor_dir / name
    lib_dir.mkdir(parents=True, exist_ok=True)

    # Save file
    target_path = lib_dir / config["target"]
    with open(target_path, "wb") as f:
        f.write(content)

    # Get headers for ETag storage
    headers = get_remote_headers(config["url"])
    etag = headers.get("ETag") or headers.get("etag") if headers else None

    # Update manifest
    if "libraries" not in manifest:
        manifest["libraries"] = {}

    if name not in manifest["libraries"]:
        manifest["libraries"][name] = {"versions": []}

    manifest["libraries"][name]["current_hash"] = content_hash
    manifest["libraries"][name]["url"] = config["url"]
    manifest["libraries"][name]["size"] = len(content)
    manifest["libraries"][name]["etag"] = etag
    manifest["libraries"][name]["updated_at"] = datetime.now(UTC).isoformat()
    manifest["libraries"][name]["versions"].append({
        "hash": content_hash,
        "downloaded_at": datetime.now(UTC).isoformat(),
        "size": len(content)
        })

    # Cleanup old versions
    cleanup_old_versions(vendor_dir, manifest, name)

    print(f"  ✅ Updated to version {content_hash}")
    return True


#: A font file's first bytes, by extension: an error page served with a 200 must not be cached as a font.
_FILE_SIGNATURES = {".woff": b"wOFF", ".woff2": b"wOF2"}


def _usable(file_name: str, content: Optional[bytes]) -> bool:
    if not content:
        return False
    signature = _FILE_SIGNATURES.get(Path(file_name).suffix.lower())
    return signature is None or content.startswith(signature)


def _update_companions(vendor_dir: Path, manifest: dict, name: str, config: dict, force: bool = False) -> bool:  # noqa: C901 — flat download/manifest pipeline, no nested logic
    """
    Download the files a JS library loads from beside itself, as its cached script names them.

    The names come from the script (``companions.pattern``) and the address from
    the library's own URL, so a new version brings its own list. Every file is
    downloaded again when the script changes. A file that cannot be downloaded
    keeps its cached copy; without one, it is a hard failure for the library's
    consumer, as the script is. Files the script no longer names are removed once
    every named one is in place.

    Returns True when a file was written or removed.
    """
    spec = config["companions"]
    script = vendor_dir / name / config["target"]
    if not script.exists():
        return False  # the script's own failure is already recorded
    names = sorted(set(re.findall(spec["pattern"], script.read_text(encoding="utf-8", errors="replace"))))
    if not names:
        _hard_fail(name, f"the cached script names no file like {spec['pattern']}: its companions cannot be listed")
        return False

    lib = manifest.setdefault("libraries", {}).setdefault(name, {"versions": []})
    record = lib.get("companions") or {}
    script_hash = lib.get("current_hash")
    # No record: nothing says which script the files on disk belong to.
    refresh = force or not record or record.get("for_hash") != script_hash
    # An empty dir (or ".") is the script's own folder, never the host's root.
    rel = spec["dir"].strip("/")
    target_dir = vendor_dir / name / rel
    base_url = urllib.parse.urljoin(config["url"], f"{rel}/" if rel else "./")

    files, kept, missing, written = {}, [], [], 0
    for file_name in names:
        path = target_dir / file_name
        if path.exists() and not refresh:
            files[file_name] = record.get("files", {}).get(file_name) or {
                "hash": get_file_hash(path.read_bytes()), "size": path.stat().st_size}
            continue
        content = download_file(base_url + file_name)
        if not _usable(file_name, content):
            (kept if path.exists() else missing).append(file_name)
            continue
        if not path.exists() or path.read_bytes() != content:
            target_dir.mkdir(parents=True, exist_ok=True)
            path.write_bytes(content)
            written += 1
        files[file_name] = {"hash": get_file_hash(content), "size": len(content)}

    if missing:
        print(f"  ❌ {len(missing)} of {len(names)} companion file(s) not downloaded and not cached")
        _hard_fail(name, f"{len(missing)} of {len(names)} companion file(s) not downloaded, no cached copy: "
                         f"{', '.join(missing)}")
        return written > 0
    removed = 0
    if target_dir.exists():
        # Only what the pattern names is a companion: the folder may hold the script itself, or other files.
        for stale in sorted(p for p in target_dir.iterdir()
                            if p.is_file() and re.fullmatch(spec["pattern"], p.name) and p.name not in names):
            stale.unlink()
            removed += 1
    if kept:
        # Retried on the next run: the record is written only once every file is current.
        print(f"  ⚠️  {len(kept)} companion file(s) not downloaded, keeping the cached copies")
    else:
        lib["companions"] = {"dir": spec["dir"], "for_hash": script_hash, "files": files}
    size_kb = sum(entry["size"] for entry in files.values()) / 1024
    if written or removed:
        print(f"  ✅ Companions: {written} written, {removed} removed ({len(names)} files, {size_kb:.0f} KB)")
    else:
        print(f"  ✓ Companions up-to-date ({len(names)} files, {size_kb:.0f} KB)")
    return bool(written or removed)


def update_all_libraries(force: bool = False):
    """Update all configured libraries."""
    print("=" * 60)
    print("LibreFolio Static Resource Cache Manager")
    print("=" * 60)

    # Ensure all vendor directories exist
    for vendor_dir in VENDOR_DIRS.values():
        vendor_dir.mkdir(parents=True, exist_ok=True)

    # Update each library (each may use a different vendor dir)
    updated_count = 0
    for name, config in LIBRARIES.items():
        vendor_dir = VENDOR_DIRS[config.get("vendor_dir_key", "mkdocs")]
        manifest = load_manifest(vendor_dir)
        if update_library(vendor_dir, manifest, name, config, force):
            updated_count += 1
        manifest["last_check"] = datetime.now(UTC).isoformat()
        save_manifest(vendor_dir, manifest)

    print("-" * 60)
    if updated_count > 0:
        print(f"✅ Updated {updated_count} resource(s)")
    else:
        print("✓ All resources up-to-date")
    print("=" * 60)

    return updated_count


def add_arguments(parser) -> None:
    """Add arguments to a parser (reusable for both standalone and subparser)."""
    parser.add_argument("--force", "-f", action="store_true",
                        help="Force re-download even if cached")
    parser.add_argument("--required-for", action="append", choices=sorted(set(CONSUMERS.values())),
                        metavar="CONSUMER",
                        help="Only fail for resources this build ships (repeatable). "
                             "Default: every consumer, so a standalone cache refresh "
                             "still reports everything.")


def run_from_args(args) -> int:
    """Execute the command from parsed args."""
    try:
        update_all_libraries(force=getattr(args, 'force', False))
        required = set(getattr(args, "required_for", None) or CONSUMERS.values())
        fatal, deferred = [], []
        for failure in _HARD_FAILURES:
            # An unattributed resource stays fatal everywhere: narrowing may
            # only ever excuse a consumer we positively know does not ship it.
            consumer = getattr(failure, "consumer", None)
            bucket = fatal if consumer is None or consumer in required else deferred
            bucket.append(failure)

        if deferred:
            # Not this build's problem, but never silent: the resource is still
            # missing, and the build that ships it will still stop.
            print("-" * 60)
            print("⚠️  Missing resources that this build does not ship:")
            for failure in deferred:
                print(f"   - {failure}  (needed by: {failure.consumer})")

        if fatal:
            # I1: a build missing a resource it cannot cache is a broken build.
            print("-" * 60)
            print("❌ Resource cache incomplete — the build would ship without these:")
            for failure in fatal:
                print(f"   - {failure}")
            return 1
        return 0
    except KeyboardInterrupt:
        print("\n⚠️  Interrupted")
        return 1
    except Exception as e:
        print(f"❌ Error: {e}")
        return 1


def main():
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="JS Library Cache Manager",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    add_arguments(parser)
    args = parser.parse_args()
    sys.exit(run_from_args(args))


def register_subparser(subparsers) -> None:
    """Register as subparser for dev.py integration."""
    p = subparsers.add_parser("cache", help="📦 Cache management")
    cache_sub = p.add_subparsers(dest="cache_cmd", metavar="action")

    js_p = cache_sub.add_parser("js", help="Update JS library cache")
    add_arguments(js_p)
    js_p.set_defaults(func=run_from_args)


if __name__ == "__main__":
    main()
