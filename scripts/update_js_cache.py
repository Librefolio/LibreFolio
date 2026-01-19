#!/usr/bin/env python3
"""
JS Library Cache Manager for LibreFolio.

Downloads external JS libraries to local vendor/ directories for offline use.
Maintains versioned cache with automatic cleanup of old versions.

Usage:
    python scripts/update_js_cache.py [--force]

Called automatically by:
    - dev.sh server (at startup)
    - Backend main.py (at startup, async)
"""

import hashlib
import json
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
LIBRARIES = {
    "mathjax": {
        "url": "https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js",
        "target": "tex-mml-chtml.js",
        }
    }

# Target directories
MKDOCS_VENDOR_DIR = Path(__file__).parent.parent / "mkdocs_src" / "docs" / "javascripts" / "vendor"


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


def download_file(url: str, timeout: int = 30) -> Optional[bytes]:
    """Download file from URL, return content or None on failure."""
    try:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "LibreFolio-CacheManager/1.0"}
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


def update_library(vendor_dir: Path, manifest: dict, name: str, config: dict, force: bool = False) -> bool:
    """
    Update a single library.

    Returns True if updated, False if already up-to-date.
    """
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
    print("LibreFolio JS Library Cache Manager")
    print("=" * 60)

    # Ensure vendor directory exists
    MKDOCS_VENDOR_DIR.mkdir(parents=True, exist_ok=True)

    # Load manifest
    manifest = load_manifest(MKDOCS_VENDOR_DIR)

    # Update each library
    updated_count = 0
    for name, config in LIBRARIES.items():
        if update_library(MKDOCS_VENDOR_DIR, manifest, name, config, force):
            updated_count += 1

    # Save manifest
    manifest["last_check"] = datetime.now(timezone.utc).isoformat()
    save_manifest(MKDOCS_VENDOR_DIR, manifest)

    print("-" * 60)
    if updated_count > 0:
        print(f"✅ Updated {updated_count} library(ies)")
    else:
        print("✓ All libraries up-to-date")
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
