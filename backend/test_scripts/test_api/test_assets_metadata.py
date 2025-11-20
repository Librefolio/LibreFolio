import json

import httpx

from backend.test_scripts.test_utils import (
    print_header,
    print_section,
    print_info,
    print_success,
    print_error,
    )

# TODO: rendere dinamico sfruttando Settings
API_BASE = "http://localhost:8001/api/v1/assets"


def run_patch_metadata_tests():
    print_section("Test 1: PATCH /assets/metadata bulk")

    payload = {
        "assets": [
            {
                "asset_id": 1,
                "patch": {
                    "short_description": "Updated via API",
                    "geographic_area": {"USA": "0.7", "FRA": "0.3"},
                    },
                }
            ]
        }
    resp = httpx.patch(f"{API_BASE}/metadata", json=payload, timeout=30.0)
    if resp.status_code != 200:
        print_error(f"PATCH metadata failed: {resp.status_code} {resp.text}")
        return False
    data = resp.json()
    print_info(f"PATCH response: {json.dumps(data, indent=2)}")
    print_success("Bulk PATCH metadata succeeded")
    return True


def run_bulk_read_tests():
    print_section("Test 2: POST /assets bulk read")
    resp = httpx.post(
        API_BASE,
        json={"asset_ids": [1]},
        timeout=30.0,
        )
    if resp.status_code != 200:
        print_error(f"Bulk read failed: {resp.status_code} {resp.text}")
        return False
    data = resp.json()
    print_info(f"Bulk read response: {json.dumps(data, indent=2)}")
    print_success("Bulk read returned metadata")
    return True


def run_refresh_tests():
    print_section("Test 3: POST /{asset_id}/metadata/refresh")
    resp = httpx.post(f"{API_BASE}/1/metadata/refresh", timeout=30.0)
    if resp.status_code != 200:
        print_error(f"Single refresh failed: {resp.status_code} {resp.text}")
        return False
    print_info(f"Single refresh: {resp.json()}")
    print_success("Single refresh ok")

    print_section("Test 4: POST /metadata/refresh/bulk")
    resp = httpx.post(
        f"{API_BASE}/metadata/refresh/bulk",
        json={"asset_ids": [1]},
        timeout=30.0,
        )
    if resp.status_code != 200:
        print_error(f"Bulk refresh failed: {resp.status_code} {resp.text}")
        return False
    print_info(f"Bulk refresh: {resp.json()}")
    print_success("Bulk refresh ok")
    return True


def run_provider_assignments_read():
    print_section("Test 5: POST /assets/scraper")
    resp = httpx.post(
        f"{API_BASE}/scraper",
        json={"asset_ids": [1]},
        timeout=30.0,
        )
    if resp.status_code != 200:
        print_error(f"Provider read failed: {resp.status_code} {resp.text}")
        return False
    print_info(f"Provider assignments: {resp.json()}")
    print_success("Provider assignments read ok")
    return True


def main():
    print_header("API: Assets Metadata Tests")
    ok = True
    ok &= run_patch_metadata_tests()
    ok &= run_bulk_read_tests()
    ok &= run_refresh_tests()
    ok &= run_provider_assignments_read()
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
