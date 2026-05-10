#!/usr/bin/env python3
"""
Static Resource Cache Manager for LibreFolio.

Downloads external JS libraries and font resources to local directories
for offline use.  Maintains versioned cache with automatic cleanup.

Supported resource types:
  - "js"   → single-file JS library (MathJax, etc.)
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
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

# Configuration
MAX_CACHED_VERSIONS = 4  # Keep last N versions of each library
CACHE_MANIFEST_FILE = ".cache_manifest.json"
CACHE_CHECK_INTERVAL_HOURS = 24  # Skip check if checked within this time

# Libraries to cache
# type="js"   → single file download
# type="font" → fetch CSS from Google Fonts, parse woff2 URLs, download all
LIBRARIES = {
    "mathjax": {
        "type": "js",
        "url": "https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js",
        "target": "tex-mml-chtml.js",
        "vendor_dir_key": "mkdocs",
    },
    "noto-color-emoji": {
        "type": "font",
        "css_url": "https://fonts.googleapis.com/css2?family=Noto+Color+Emoji&display=swap",
        "file_prefix": "noto-color-emoji",
        "css_file": "noto-color-emoji.css",
        "vendor_dir_key": "fonts",
    },
}

# Target directories (keyed by vendor_dir_key)
VENDOR_DIRS = {
    "mkdocs": Path(__file__).parent.parent / "mkdocs_src" / "docs" / "javascripts" / "vendor",
    "fonts": Path(__file__).parent.parent / "frontend" / "static" / "fonts" / "noto-color-emoji",
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
        try:
            with open(manifest_path, "r") as f:
                return json.load(f)
        except Exception:
            pass
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
            last_check_dt = last_check_dt.replace(tzinfo=timezone.utc)
        hours_since = (datetime.now(timezone.utc) - last_check_dt).total_seconds() / 3600
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


def _download_font_resource(
    vendor_dir: Path, manifest: dict, name: str, config: dict, force: bool = False
) -> bool:
    """
    Download a Google Fonts resource (CSS + woff2 files).

    Fetches the CSS from Google Fonts, extracts woff2 URLs, downloads each
    subset file, and writes a local CSS with relative paths.
    """
    print(f"🔤 Checking font {name}...")

    lib_data = manifest.get("libraries", {}).get(name, {})
    current_hash = lib_data.get("current_hash")

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
            print(f"  ⚠️  CSS download failed, keeping cached version")
        else:
            print(f"  ❌ CSS download failed and no cached version exists")
        return False

    css_text = css_bytes.decode("utf-8")
    css_hash = get_file_hash(css_bytes)

    if current_hash == css_hash and not force and file_exists:
        print(f"  ✓ Already up-to-date (CSS hash: {css_hash})")
        return False

    # Parse subsets
    subsets = _parse_google_fonts_css(css_text)
    if not subsets:
        print(f"  ⚠️  No subsets found in Google Fonts CSS")
        return False

    print(f"  📋 Found {len(subsets)} subsets")
    target_dir.mkdir(parents=True, exist_ok=True)

    # Download each woff2 file
    prefix = config["file_prefix"]
    local_css_lines = [
        "/*",
        f" * {name} — self-hosted subsets (Google Fonts)",
        f" * Auto-downloaded by scripts/update_js_cache.py",
        f" * Source: {config['css_url']}",
        f" * Updated: {datetime.now(timezone.utc).strftime('%Y-%m-%d')}",
        f" * Subsets: {len(subsets)}",
        " */",
        "",
    ]

    total_size = 0
    font_family = " ".join(w.capitalize() for w in name.split("-"))
    for i, subset in enumerate(subsets):
        local_filename = f"{prefix}.{i}.woff2"
        woff2_content = download_file(subset["src_url"])
        if woff2_content is None:
            print(f"  ⚠️  Failed to download subset {i}, skipping")
            continue

        woff2_path = target_dir / local_filename
        with open(woff2_path, "wb") as f:
            f.write(woff2_content)
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
    manifest["libraries"][name]["url"] = config["css_url"]
    manifest["libraries"][name]["type"] = "font"
    manifest["libraries"][name]["subset_count"] = len(subsets)
    manifest["libraries"][name]["total_size"] = total_size
    manifest["libraries"][name]["updated_at"] = datetime.now(timezone.utc).isoformat()
    manifest["libraries"][name]["versions"].append({
        "hash": css_hash,
        "downloaded_at": datetime.now(timezone.utc).isoformat(),
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
    Dispatches to type-specific handler (js or font).
    """
    resource_type = config.get("type", "js")
    if resource_type == "font":
        return _download_font_resource(vendor_dir, manifest, name, config, force)

    # Original single-file JS logic
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
                print(f"  ✓ Already up-to-date (ETag match)")
                return False

            # If size matches and no ETag, likely same file
            if remote_size and current_size and int(remote_size) == current_size and not remote_etag:
                print(f"  ✓ Already up-to-date (size match: {current_size} bytes)")
                return False

    # Download current version
    content = download_file(config["url"])
    if content is None:
        if file_exists:
            print(f"  ⚠️  Download failed, keeping cached version")
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
    manifest["libraries"][name]["updated_at"] = datetime.now(timezone.utc).isoformat()
    manifest["libraries"][name]["versions"].append({
        "hash": content_hash,
        "downloaded_at": datetime.now(timezone.utc).isoformat(),
        "size": len(content)
        })

    # Cleanup old versions
    cleanup_old_versions(vendor_dir, manifest, name)

    print(f"  ✅ Updated to version {content_hash}")
    return True


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
        manifest["last_check"] = datetime.now(timezone.utc).isoformat()
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


def run_from_args(args) -> int:
    """Execute the command from parsed args."""
    try:
        update_all_libraries(force=getattr(args, 'force', False))
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
