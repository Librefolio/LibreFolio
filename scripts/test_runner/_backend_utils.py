"""
Backend utility tests: decimal precision, datetime, day count, geo, version, etc.
"""

from . import _common
from ._common import (
    _build_pytest_cmd,
    _get_category_tests_for_all,
    _run_test_suite,
    add_test,
    make_category,
    print_info,
    print_section,
    run_command,
)


def utils_decimal_precision(verbose: bool = False, test_names: list = None) -> bool:
    """Test decimal precision utilities."""
    print_section("Utils: Decimal Precision")
    print_info("Testing: backend/app/db/precision.py, backend/app/utils/decimal_utils.py")
    print_info("Tests: Model precision extraction, Truncation, Edge cases")
    cmd = _build_pytest_cmd("backend/test_scripts/test_utilities/test_decimal_utils.py", test_names)
    return run_command(cmd, "Decimal precision tests", verbose=verbose)


def utils_real_decimal(verbose: bool = False, test_names: list = None) -> bool:
    """Test the RealDecimal column type and the digit limits of db/precision.py (C-97a)."""
    print_section("Utils: RealDecimal and Digit Limits")
    print_info("Testing: backend/app/db/real_decimal.py (through the model columns), backend/app/db/precision.py")
    print_info("Tests: quantities and prices read back on a private in-memory SQLite, column declarations, truncation, decimal_limit_issue")
    cmd = _build_pytest_cmd("backend/test_scripts/test_utilities/test_real_decimal.py", test_names)
    return run_command(cmd, "RealDecimal and digit limit tests", verbose=verbose)


def utils_origins(verbose: bool = False, test_names: list = None) -> bool:
    """Test canonical_origin: the one canonical form of an http(s) origin, and no origin for a host that could reach a header (H-55 v2)."""
    print_section("Utilities: Canonical Origin")
    print_info("Testing: backend/app/utils/runtime/origins.py")
    cmd = _build_pytest_cmd("backend/test_scripts/test_utilities/test_origins.py", test_names)
    return run_command(cmd, "Canonical origin tests", verbose=verbose)


def utils_datetime(verbose: bool = False, test_names: list = None) -> bool:
    """Test datetime utilities."""
    print_section("Utils: Datetime")
    print_info("Testing: backend/app/utils/datetime_utils.py")
    print_info("Tests: Timezone-aware datetime helpers")
    cmd = _build_pytest_cmd("backend/test_scripts/test_utilities/test_datetime_utils.py", test_names)
    return run_command(cmd, "Datetime utils tests", verbose=verbose)


def utils_pydantic_errors(verbose: bool = False, test_names: list = None) -> bool:
    """Test the shared pydantic-error helpers of the batch and BRIM parses (W-B77, W-B70)."""
    print_section("Utils: Pydantic Errors")
    print_info("Testing: backend/app/utils/pydantic_errors.py; its two call sites (transaction_batch_stages.py, brim_provider.py) read with ast")
    print_info("Tests: PLAIN_PARAM_TYPES, loc_to_field, error_params (field and packed sub-errors), no copy left at the call sites")
    cmd = _build_pytest_cmd("backend/test_scripts/test_utilities/test_pydantic_errors.py", test_names)
    return run_command(cmd, "Pydantic errors tests", verbose=verbose)


def utils_day_count(verbose: bool = False, test_names: list = None) -> bool:
    """Test day count conventions."""
    print_section("Utils: Day Count Conventions")
    print_info("Testing: backend/app/services/financial_math/interest.py (day count conventions and simple interest)")
    print_info("Tests: ACT/365, ACT/360, ACT/ACT, 30/360 conventions")
    cmd = _build_pytest_cmd("backend/test_scripts/test_utilities/test_day_count_conventions.py", test_names)
    return run_command(cmd, "Day count convention tests", verbose=verbose)


def utils_geo_utils(verbose: bool = False, test_names: list = None) -> bool:
    """Test geographic area normalization utilities."""
    print_section("Utils: Geographic Area Normalization")
    print_info("Testing: backend/app/utils/asset/geo.py")
    print_info("Tests: ISO-3166-A3 normalization, weight parsing, validation pipeline")
    cmd = _build_pytest_cmd("backend/test_scripts/test_utilities/test_geo_utils.py", test_names)
    return run_command(cmd, "Geographic area normalization tests", verbose=verbose)


def utils_version(verbose: bool = False, test_names: list = None) -> bool:
    """Test version utilities."""
    print_section("Utils: Version")
    print_info("Testing: backend/app/utils/runtime/version.py")
    cmd = _build_pytest_cmd("backend/test_scripts/test_utilities/test_version.py", test_names)
    return run_command(cmd, "Version utility tests", verbose=verbose)


def utils_container_registry(verbose: bool = False, test_names: list = None) -> bool:
    """Test the GHCR manifest/token flow without DB, server, or network."""
    print_section("Utils: Container Registry")
    print_info("Testing: trusted GHCR challenge parsing, token flow, status mapping, endpoint guards")
    cmd = _build_pytest_cmd(
        "backend/test_scripts/test_services/test_container_registry.py",
        test_names,
    )
    return run_command(cmd, "Container registry tests", verbose=verbose)


def utils_served_content_types(verbose: bool = False, test_names: list = None) -> bool:
    """Test that uploaded content reaches the browser only as types that cannot run."""
    print_section("Utils: Served Content Types")
    print_info("Testing: backend/app/api/v1/uploads.py (serve_file text preview), backend/app/api/v1/brokers.py (download_file)")
    print_info("Tests: text preview always text/plain with nosniff; broker reports inline only for safe types with download=false, attachment otherwise; nosniff on every report")
    cmd = _build_pytest_cmd("backend/test_scripts/test_utilities/test_served_content_types.py", test_names)
    return run_command(cmd, "Served content type tests", verbose=verbose)


def utils_nosniff_content_types(verbose: bool = False, test_names: list = None) -> bool:
    """Test that every file the app serves has its right type: nosniff refuses a script or a style sheet of another type."""
    print_section("Utils: nosniff Content Types")
    print_info("Testing: backend/app/services/platform/static_site.py (FileResponse through the /_app mount, the SPA catch-all, /mkdocs), every extension of frontend/build and mkdocs_src/site")
    print_info("Tests: JavaScript, CSS, WASM, font, JSON/manifest and SVG types; never application/octet-stream; on this machine and without any system mime.types file (python:3.13-slim)")
    cmd = _build_pytest_cmd("backend/test_scripts/test_utilities/test_nosniff_content_types.py", test_names)
    return run_command(cmd, "nosniff content type tests", verbose=verbose)


def utils_coverage_js_adapter(verbose: bool = False, test_names: list = None) -> bool:
    """Test the JS/Svelte coverage adapter that feeds coverage_analysis."""
    print_section("Utils: JS Coverage Adapter")
    print_info("Testing: scripts/coverage_js.py")
    print_info("Tests: line-based counting across the vitest/E2E double compilation, istanbul conversion")
    cmd = _build_pytest_cmd("backend/test_scripts/test_utilities/test_coverage_js_adapter.py", test_names)
    return run_command(cmd, "JS coverage adapter tests", verbose=verbose)


def utils_sector_normalization(verbose: bool = False, test_names: list = None) -> bool:
    """Test FinancialSector enum and sector normalization."""
    print_section("Utils: Sector Normalization")
    print_info("Testing: backend/app/utils/asset/sector.py")
    print_info("Tests: FinancialSector enum, aliases, normalization, validation")
    cmd = _build_pytest_cmd("backend/test_scripts/test_utilities/test_sector_normalization.py", test_names)
    return run_command(cmd, "Sector normalization tests", verbose=verbose)


def utils_currency_utils(verbose: bool = False, test_names: list = None) -> bool:
    """Test currency listing, flag mapping, and validation."""
    print_section("Utils: Currency Utils")
    print_info("Testing: backend/app/utils/fx/currency.py")
    print_info("Tests: list_currencies (pycountry), flag_emoji mapping, validation consistency")
    cmd = _build_pytest_cmd("backend/test_scripts/test_utilities/test_currency_utils.py", test_names)
    return run_command(cmd, "Currency utils tests", verbose=verbose)


def utils_cache_utils(verbose: bool = False, test_names: list = None) -> bool:
    """Test NamedCache wrapper, TTL expiration, and global cache registry."""
    print_section("Utils: Cache Utils")
    print_info("Testing: backend/app/utils/runtime/cache.py")
    print_info("Tests: NamedCache set/get/delete/clear, TTL, registry, stats")
    cmd = _build_pytest_cmd("backend/test_scripts/test_utilities/test_cache_utils.py", test_names)
    return run_command(cmd, "Cache utils tests", verbose=verbose)


def utils_rate_window(verbose: bool = False, test_names: list = None) -> bool:
    """Test the sliding-window limiter shared by the e-mail budget and the login limits."""
    print_section("Utils: Rate Window")
    print_info("Testing: backend/app/utils/runtime/rate_window.py")
    print_info("Tests: window edge, peek never counts, refused hits not recorded, retry_after, per-call limit, independent keys, LRU eviction, thread safety (fake clock, no sleeps)")
    cmd = _build_pytest_cmd("backend/test_scripts/test_utilities/test_rate_window.py", test_names)
    return run_command(cmd, "Rate window tests", verbose=verbose)


def utils_cooldown(verbose: bool = False, test_names: list = None) -> bool:
    """Test the per-key pauses after a remote refuses for too many calls (HTTP 429), shared by every provider boundary."""
    print_section("Utils: Cooldown")
    print_info("Testing: backend/app/utils/runtime/cooldown.py")
    print_info("Tests: RateLimitedError + domain error, Retry-After (seconds, HTTP-date), doubling to the max, Retry-After floor, jitter, per-call base/max, decay, answers during a running pause, one trial at a time, succeeded/released, backwards clock, snapshot, LRU, threads (fake clock)")
    cmd = _build_pytest_cmd("backend/test_scripts/test_utilities/test_cooldown.py", test_names)
    return run_command(cmd, "Cooldown tests", verbose=verbose)


def utils_provider_core_cache(verbose: bool = False, test_names: list = None) -> bool:
    """Test provider core cache & thread isolation infrastructure."""
    print_section("Utils: Provider Core Cache & Thread Isolation")
    print_info("Testing: backend/app/services/assets/core.py (core cache + _run_provider_in_thread)")
    print_info("Tests: Thread isolation, timeout, caches (history/current/metadata/search), probe bypass")
    cmd = _build_pytest_cmd("backend/test_scripts/test_utilities/test_provider_core_cache.py", test_names)
    return run_command(cmd, "Provider core cache tests", verbose=verbose)


def utils_roi_utils(verbose: bool = False, test_names: list = None) -> bool:
    """Test pure ROI helper functions (annualized_to_cumulative, calculate_mwrr*)."""
    print_section("Utils: ROI Helpers")
    print_info("Testing: backend/app/services/financial_math/returns.py")
    cmd = _build_pytest_cmd("backend/test_scripts/test_utilities/test_roi_utils.py", test_names)
    return run_command(cmd, "ROI helper tests", verbose=verbose)


def utils_translation_utils(verbose: bool = False, test_names: list = None) -> bool:
    """Test translation/locale helper (get_babel_locale + English fallback)."""
    print_section("Utils: Translation Helpers")
    print_info("Testing: backend/app/utils/asset/translation.py")
    cmd = _build_pytest_cmd("backend/test_scripts/test_utilities/test_translation_utils.py", test_names)
    return run_command(cmd, "Translation helper tests", verbose=verbose)


def utils_ai_export_probe_helpers(verbose: bool = False, test_names: list = None) -> bool:
    """Test fast AI Export probe helper functions without running a real probe."""
    print_section("Utils: AI Export Probe Helpers")
    print_info("Testing helper logic only; no copied DB, API server, prompt corpus, or qualitative review")
    cmd = _build_pytest_cmd(
        "backend/test_scripts/test_utilities/test_ai_export_real_prompt_probe.py",
        test_names,
    )
    return run_command(cmd, "AI Export probe helper tests", verbose=verbose)


def utils_js_cache_fail_loud(verbose: bool = False, test_names: list = None) -> bool:
    """Test update_js_cache fail-loud contract (I1)."""
    print_section("Utils: JS Cache Fail-Loud")
    print_info("Testing: scripts/update_js_cache.py")
    print_info("Tests: hard failure (no cache) vs soft keep (cached), partial font subsets, exit codes")
    cmd = _build_pytest_cmd("backend/test_scripts/test_utilities/test_update_js_cache.py", test_names)
    return run_command(cmd, "JS cache fail-loud tests", verbose=verbose)


def utils_gate_docs_links(verbose: bool = False, test_names: list = None) -> bool:
    """Test the cross-boundary docs link gate (const resolution, plugin discovery, three verdicts, anchors from the render) and the built site's asset URLs."""
    print_section("Utils: Docs Link Gate")
    print_info("Testing: scripts/docs_links.py, dev.py mkdocs check-links (_mkdocs_check_anchor, _mkdocs_page_anchors), dev.py mkdocs build (_check_asset_paths_in_built_site)")
    print_info("Tests: const resolution vs deletion, plugin/provider glob, unverifiable bucket, anchors from the page's MkDocs render in every language, dev.py without MkDocs, relative asset URLs of the built site")
    cmd = _build_pytest_cmd("backend/test_scripts/test_utilities/test_docs_links_gate.py", test_names)
    return run_command(cmd, "Docs link discovery tests", verbose=verbose)


def utils_pwa_assets(verbose: bool = False, test_names: list = None) -> bool:
    """Test the committed PWA icons, manifest, apple-touch link and service-worker stamp."""
    print_section("Utils: PWA Assets")
    print_info("Testing: frontend/static/{icons/,manifest.json,sw.js,offline.html}, frontend/src/app.html")
    print_info("Tests: opaque RGB icons, maskable safe zone on splash beige, 180px apple-touch icon, sw.js stamp = md5(offline.html)[:8]; stamp_service_worker() and cmd_fe_build on copies under tmp_path (H-52)")
    cmd = _build_pytest_cmd("backend/test_scripts/test_utilities/test_pwa_assets.py", test_names)
    return run_command(cmd, "PWA asset tests", verbose=verbose)


def utils_check_frontend_build(verbose: bool = False, test_names: list = None) -> bool:
    """Test the Dockerfile's frontend guard: only a production build may reach an image."""
    print_section("Utils: Frontend Build Guard")
    print_info("Testing: scripts/docker/check_frontend_build.sh")
    print_info("Tests: production build passes; debug marker, sourcemaps, coverage marker, missing index.html/200.html fail")
    cmd = _build_pytest_cmd("backend/test_scripts/test_utilities/test_check_frontend_build.py", test_names)
    return run_command(cmd, "Frontend build guard tests", verbose=verbose)


def utils_release_image_contract(verbose: bool = False, test_names: list = None) -> bool:
    """Test the release.yml / Dockerfile contract that keeps the gallery's debug build out of the images."""
    print_section("Utils: Release Image Contract")
    print_info("Testing: .github/workflows/release.yml, Dockerfile")
    print_info("Tests: production front build + docs rebuild between gallery and image builds, nightly report, guarded frontend stage")
    cmd = _build_pytest_cmd("backend/test_scripts/test_utilities/test_release_image_contract.py", test_names)
    return run_command(cmd, "Release image contract tests", verbose=verbose)


def utils_dev_cli_image(verbose: bool = False, test_names: list = None) -> bool:
    """Test dev.py inside the image's file set (no backend/test_scripts) and the image's HEALTHCHECK port."""
    print_section("Utils: dev.py in the Docker image")
    print_info("Testing: dev.py on a copy of the image's /app tree (tmp_path), Dockerfile HEALTHCHECK vs CMD vs compose")
    print_info("Tests: help and user commands run, unavailable groups say so and exit 2, password reset on a temporary DB, the role user create and create-user give an account (L12), backup create/inspect on the image's DB (B1)")
    cmd = _build_pytest_cmd("backend/test_scripts/test_utilities/test_dev_cli_image.py", test_names)
    return run_command(cmd, "dev.py image tests", verbose=verbose)


def utils_dev_cli_docker(verbose: bool = False, test_names: list = None) -> bool:
    """Test the Docker lot (CP7a): the image's packages and port, the compose files, docker exec, and one version per image build."""
    print_section("Utils: dev.py docker commands and the image contract")
    print_info("Testing: Dockerfile, docker-compose*.yml, dev.py cmd_docker_exec, _docker_frontend_stale_reason, _docker_ensure_frontend_built, _docker_ensure_assets_built, _get_docker_tag, cmd_docker_build, _check_env_file")
    print_info('Tests: tzdata-legacy, EXPOSE and compose ports, compose environment, exec through gosu and "$@", the frozen version in the bundle, VERSION and the tag')
    cmd = _build_pytest_cmd("backend/test_scripts/test_utilities/test_dev_cli_docker.py", test_names)
    return run_command(cmd, "dev.py docker tests", verbose=verbose)


def utils_gate_i18n_usage(verbose: bool = False, test_names: list = None) -> bool:
    """Test the i18n three-verdict classifier (used / not verified / dead)."""
    print_section("Utils: i18n Usage Gate")
    print_info("Testing: scripts/i18n_usage.py")
    print_info("Tests: typed-union expansion, producer vocabulary, ternary arguments, bare-root suppression")
    cmd = _build_pytest_cmd("backend/test_scripts/test_utilities/test_i18n_usage_gate.py", test_names)
    return run_command(cmd, "i18n three-verdict classifier tests", verbose=verbose)


def utils_gate_i18n_catalog(verbose: bool = False, test_names: list = None) -> bool:
    """Test the translation catalogue built from its sources, and the repository's own sources."""
    print_section("Utils: i18n Catalogue Gate")
    print_info("Testing: scripts/i18n_catalog.py; frontend/src/lib/i18n/base/, the subsystem folders and the plugins' i18n/ sources")
    print_info("Tests: ownership, defects, English fallback, order and format, build stamp and hand-edit guard, route/set/move/split/remove, catalogs_at, check --against, three-way absorb, the repository's sources and ignore rules")
    cmd = _build_pytest_cmd("backend/test_scripts/test_utilities/test_i18n_catalog_gate.py", test_names)
    return run_command(cmd, "i18n catalogue gate tests", verbose=verbose)


def utils_gate_plugin_layout(verbose: bool = False, test_names: list = None) -> bool:
    """Test the plugin layout gate: every first-party plugin is a folder, reached through its plugin module."""
    print_section("Utils: Plugin Layout Gate")
    print_info("Testing: backend/app/services/{brim_providers,asset_source_providers,fx_providers,risk_plugins,signal_plugins,tool_plugins}/, imports and strings of backend/app, backend/test_scripts, scripts, dev.py")
    print_info("Tests: <name>/__init__.py (docstring only) + <name>/plugin.py, no single-module plugin, no import or string reaching a plugin package instead of its plugin module")
    cmd = _build_pytest_cmd("backend/test_scripts/test_utilities/test_plugin_layout_gate.py", test_names)
    return run_command(cmd, "Plugin layout gate tests", verbose=verbose)


def utils_gate_plugin_i18n_ownership(verbose: bool = False, test_names: list = None) -> bool:
    """Test the plugin i18n ownership gate: each plugin's keys live in its own i18n/ fragment."""
    print_section("Utils: Plugin i18n Ownership Gate")
    print_info("Testing: the spaces and keys the BRIM, asset, FX, signal, risk and tool registries publish, against the catalogue sources scripts/i18n_catalog.py reads")
    print_info("Tests: R1 fragment keys in their plugin's space, R2 declared keys of an exclusive space in its fragment, R3 no fragment key in another plugin's space or declared by another plugin, R4 every key under an exclusive space in its fragment (tools aside)")
    cmd = _build_pytest_cmd("backend/test_scripts/test_utilities/test_plugin_i18n_ownership_gate.py", test_names)
    return run_command(cmd, "Plugin i18n ownership gate tests", verbose=verbose)


def utils_gate_event_loop_io(verbose: bool = False, test_names: list = None) -> bool:
    """Test the event-loop gate: no API async handler calls a synchronous BRIM file-store function directly."""
    print_section("Utils: Event Loop BRIM I/O Gate")
    print_info("Testing: backend/app/api/v1/**/*.py against the synchronous functions of backend/app/services/brim/brim_provider.py")
    print_info("Tests: a direct call in an async def is flagged; asyncio.to_thread(fn, ...), nested def/lambda bodies, awaited coroutines and sync handlers are not; every import form is followed; the scan reaches the store's importers")
    cmd = _build_pytest_cmd("backend/test_scripts/test_utilities/test_event_loop_brim_io_gate.py", test_names)
    return run_command(cmd, "Event loop BRIM I/O gate tests", verbose=verbose)


def utils_gate_aiosqlite_leak(verbose: bool = False, test_names: list = None) -> bool:
    """Test the aiosqlite leak guard the shared conftest runs around every backend test (J-6)."""
    print_section("Utils: aiosqlite Leak Gate")
    print_info("Testing: backend/test_scripts/test_aiosqlite_guard.py, the autouse _aiosqlite_leak_guard of backend/test_scripts/conftest.py")
    print_info("Tests: C-93 shape reported until disposed, closed connections tracked but not reported, other threads untracked, no attribution before a window, exceptions at nodeid boundaries, loud failure without aiosqlite's _connection, a child pytest under the real conftest")
    cmd = _build_pytest_cmd("backend/test_scripts/test_utilities/test_aiosqlite_leak_gate.py", test_names)
    return run_command(cmd, "aiosqlite leak gate tests", verbose=verbose)


def utils_tools_wire(verbose: bool = False, test_names: list = None) -> bool:
    """Test bounded Tool JSON encoding and sanitized validation errors."""
    print_section("Utils: Tool Wire")
    print_info("Testing: Unicode scalars, JSON limits, raw values and error redaction")

    cmd = _build_pytest_cmd("backend/test_scripts/test_utilities/test_tools_wire.py", test_names)
    return run_command(cmd, "Tool wire tests", verbose=verbose)


def utils_runtime_isolation(verbose: bool = False, test_names: list = None) -> bool:
    """Test the runtime-isolation contract (test-mode data-dir override + CLI shapes)."""
    print_section("Utils: Runtime Isolation")
    print_info("Testing: runtime paths, CLI propagation, lane readiness and process ownership")
    print_info("Tests: prod guards, dotenv/Pipenv boundaries, port collisions, symlink escapes, server/test parser shapes")
    cmd = _build_pytest_cmd("backend/test_scripts/test_utilities/test_runtime_isolation.py", test_names)
    return run_command(cmd, "Runtime isolation tests", verbose=verbose)


def utils_confined_path(verbose: bool = False, test_names: list = None) -> bool:
    """Test that a request path joined to a folder never leaves that folder."""
    print_section("Utils: Confined Path")
    print_info("Testing: backend/app/utils/runtime/paths.py (confined_path)")
    print_info("Tests: paths inside returned resolved; parent segments leaving, absolute paths, a sibling folder sharing the name prefix, symlinks pointing outside and a NUL byte refused")
    cmd = _build_pytest_cmd("backend/test_scripts/test_utilities/test_confined_path.py", test_names)
    return run_command(cmd, "Confined path tests", verbose=verbose)


def utils_static_route_confinement(verbose: bool = False, test_names: list = None) -> bool:
    """Test that the routes serving files by request path never leave their folder."""
    print_section("Utils: Static Route Confinement")
    print_info("Testing: backend/app/services/platform/static_site.py (frontend_catchall, mkdocs_static), backend/app/api/v1/uploads.py (serve_plugin_static)")
    print_info("Tests: raw ASGI requests landing outside the served folder → SPA fallback / 404 / 403, never the outside content; the files of each folder still served")
    cmd = _build_pytest_cmd("backend/test_scripts/test_utilities/test_static_route_confinement.py", test_names)
    return run_command(cmd, "Static route confinement tests", verbose=verbose)


def utils_jwt_secret_blank(verbose: bool = False, test_names: list = None) -> bool:
    """Test that a blank JWT_SECRET never becomes the key that signs session cookies."""
    print_section("Utils: JWT Secret Blank")
    print_info("Testing: backend/app/services/accounts/auth_service.py (_JWT_SECRET, decode_jwt_token), backend/app/config/platform.py (configured_jwt_secret)")
    print_info("Tests: a whitespace-only JWT_SECRET replaced by a random key and tokens signed with it refused; a non-blank secret kept as written; unset or empty still random")
    cmd = _build_pytest_cmd("backend/test_scripts/test_utilities/test_jwt_secret_blank.py", test_names)
    return run_command(cmd, "JWT secret blank tests", verbose=verbose)


def utils_test_server_preparation(verbose: bool = False, test_names: list = None) -> bool:
    """Test that the test server's builds run before its startup timeout, that a tree without node_modules stops before npx (C-94), and that the shared backend's output reaches a log whose tail a failed start prints (H-12)."""
    print_section("Utils: Test Server Preparation")
    print_info("Testing: dev.py server --build-only, cmd_fe_build/cmd_api_client (frontend/node_modules/.bin check), cmd_mkdocs_gallery; scripts/test_runner/_server.py (build_server_prerequisites, SharedTestServer.start(), shared_backend_log_path, log_tail)")
    print_info(
        "Tests: pre-bind builds in order without binding, missing tools named with npm ci before any npm/npx, port check → build → spawn → STARTUP_TIMEOUT, build env without coverage wiring, gallery build with Playwright's env, the backend's output in shared-backend.log (emptied, appended to on a restart) and its tail on a failed start"
    )
    cmd = _build_pytest_cmd("backend/test_scripts/test_utilities/test_test_server_preparation.py", test_names)
    return run_command(cmd, "Test server preparation tests", verbose=verbose)


def utils_test_runner_cli(verbose: bool = False, test_names: list = None) -> bool:
    """Test the test-runner CLI's own command-building contract."""
    print_section("Utils: Test Runner CLI")
    print_info("Testing: scripts/test_runner/_backend_utils.py, _cli.py (registry dispatch)")
    print_info("Tests: test_names → pytest -k semantics, registry forwarding, coverage_js_adapter link")
    cmd = _build_pytest_cmd("backend/test_scripts/test_utilities/test_test_runner_cli.py", test_names)
    return run_command(cmd, "Test runner CLI contract tests", verbose=verbose)


def utils_dev_cli_db_path(verbose: bool = False, test_names: list = None) -> bool:
    """Test that dev.py db current/upgrade/downgrade/migrate/check act on the path they are given, never on the configured database."""
    print_section("Utils: dev.py db [path]")
    print_info("Testing: dev.py db current|upgrade|downgrade|migrate|check <path> on temporary databases (tmp_path), the configured one a sentinel")
    print_info("Tests: absolute and project-root-relative paths, missing file refused (upgrade creates it), %/?/# refused, db check runs the CHECK constraints hook, no path = configured database")
    cmd = _build_pytest_cmd("backend/test_scripts/test_utilities/test_dev_cli_db_path.py", test_names)
    return run_command(cmd, "dev.py db path tests", verbose=verbose)


def utils_dev_port_check(verbose: bool = False, test_names: list = None) -> bool:
    """Test that dev.py's check_port_in_use names the listener of a TCP port, and only it (H-12), on macOS and Linux."""
    print_section("Utils: dev.py port check")
    print_info("Testing: dev.py check_port_in_use, the port check of server and mkdocs gallery (the list --force kills)")
    print_info("Tests: Linux fuser fallback through the real subprocess.run argument check, host lsof/fuser on a 127.0.0.1 listener and on a released port, a socket holding the port without listening not reported (H-12), no capture_output with stdout=/stderr= in dev.py")
    cmd = _build_pytest_cmd("backend/test_scripts/test_utilities/test_dev_port_check.py", test_names)
    return run_command(cmd, "dev.py port check tests", verbose=verbose)


def utils_dev_server_interrupt(verbose: bool = False, test_names: list = None) -> bool:
    """Test that Ctrl+C on dev.py server waits for the server's own shutdown instead of killing it after 0.25 s, and that a SIGTERM to dev.py reaches the server (Z-10)."""
    print_section("Utils: dev.py server interrupt")
    print_info("Testing: scripts/cli_base.py run_server_live, dev.py _server_stop_grace and cmd_server's launch")
    print_info(
        "Tests: a real stand-in for dev.py and a fake server in a session of their own under tmp_path: Ctrl+C to the group waited for (130, not forwarded), the server SIGKILLed when the grace runs out or at a second Ctrl+C; SIGTERM to dev.py alone forwarded and waited for (143), to the group waited for, a second one forces; the server's own exit code, 1 when it cannot start, the SIGTERM handler given back; grace = shutdown budget + 2 s; cmd_server launches through run_server_live, --coverage still execs"
    )
    cmd = _build_pytest_cmd("backend/test_scripts/test_utilities/test_dev_server_interrupt.py", test_names)
    return run_command(cmd, "dev.py server interrupt tests", verbose=verbose)


def utils_dev_designer_lab_banner(verbose: bool = False, test_names: list = None) -> bool:
    """Test that dev.py lists the Designer Lab (/designer-lab) among the server's endpoints only when the frontend build carries it, and under front dev unless LF_DESIGNER_LAB=0."""
    print_section("Utils: dev.py Designer Lab banner")
    print_info("Testing: dev.py _frontend_build_has_designer_lab, DESIGNER_LAB_MARKER (= LAB_MARKER of frontend/scripts/designer-lab/vite-plugin.mjs), cmd_server's «Available endpoints», cmd_fe_dev")
    print_info(
        "Tests: fake builds (none, release, debug with and without the Lab, production with LF_DESIGNER_LAB=1, rebuilt by the auto-build), only _app/immutable/**/*.js counts, listing and read errors read as no Lab and never stop the start, --build-only never asks, front dev hides it only for LF_DESIGNER_LAB=0"
    )
    cmd = _build_pytest_cmd("backend/test_scripts/test_utilities/test_dev_designer_lab_banner.py", test_names)
    return run_command(cmd, "dev.py Designer Lab banner tests", verbose=verbose)


def utils_coverage_combine(verbose: bool = False, test_names: list = None) -> bool:
    """Test that coverage parts renamed or landing late are still combined, that run directories never pile up, that an empty finished part is dropped, and that a failed combine is a red pass."""
    print_section("Utils: Coverage Combine")
    print_info("Testing: scripts/test_runner/_coverage.py (combine_coverage_dir, _finalize_coverage), _executor.py (combine_coverage), _cli.py (parallel pass verdict), _suites.py (_clean_coverage_dirs)")
    print_info("Tests: part renamed while coverage starts, part landing after coverage's listing, shared-backend parts in the cwd, failed combine turns the pass red, run directories, --cov-clean-backend on parts/, empty finished parts")
    cmd = _build_pytest_cmd("backend/test_scripts/test_utilities/test_coverage_combine.py", test_names)
    return run_command(cmd, "Coverage combine tests", verbose=verbose)


def utils_translation_code_blocks(verbose: bool = False, test_names: list = None) -> bool:
    """Test that translated code blocks keep the source indentation (Aphra pipeline + validator)."""
    print_section("Utils: Translation Code Blocks")
    print_info("Testing: mkdocs_src/aphra-pipeline/code_blocks.py, translate_docs.py, validate_translations.py")
    print_info("Tests: fence-aware whitespace cleanup, EN indentation restore, code-block-indent check, corpus guard")
    cmd = _build_pytest_cmd("backend/test_scripts/test_utilities/test_translation_code_blocks.py", test_names)
    return run_command(cmd, "Translation code-block tests", verbose=verbose)


def utils_translation_cache(verbose: bool = False, test_names: list = None) -> bool:
    """Test that the translation hash cache counts a language as done only for the EN version it was translated from (Aphra pipeline)."""
    print_section("Utils: Translation Cache")
    print_info("Testing: mkdocs_src/aphra-pipeline/translate_docs.py (run_translate, run_stamp, the hash cache transitions)")
    print_info("Tests: failed, --lang-skipped and interrupted languages after an EN edit (parallel and sequential), an EN edit saved during the analysis (LF/CRLF), failed --force retry, stamp, plain success, the five transitions")
    cmd = _build_pytest_cmd("backend/test_scripts/test_utilities/test_translation_cache.py", test_names)
    return run_command(cmd, "Translation cache tests", verbose=verbose)


def utils_translation_validator(verbose: bool = False, test_names: list = None) -> bool:
    """Test the translate-validate checks of R2 batches 11-14 and the block-based LINE_COUNT of the structural diff (Aphra pipeline)."""
    print_section("Utils: Translation Validator")
    print_info("Testing: mkdocs_src/aphra-pipeline/validate_translations.py (_strip_code, HTML checks, text-untranslated, inline-code-missing, anchor-missing, html-asset-depth, check_latex, validate_file), page_anchors.py (render_anchors, file_anchors), translate_docs.py (_structural_diff)")
    print_info("Tests: fence-aware code stripping, inline code never read as HTML, untranslated alt/title/aria-label/data-title, inline code spans kept, link anchors from the page's MkDocs render, raw-HTML file paths one folder deeper, inline math read as arithmatex reads it, LINE_COUNT on blocks")
    cmd = _build_pytest_cmd("backend/test_scripts/test_utilities/test_translation_validator.py", test_names)
    return run_command(cmd, "Translation validator tests", verbose=verbose)


def utils_docs_fr_typography(verbose: bool = False, test_names: list = None) -> bool:
    """Test the MkDocs hook that applies French typography to the French pages at build time."""
    print_section("Utils: Docs French Typography")
    print_info("Testing: mkdocs_src/hooks/fr_typography.py (typeset, typeset_html, on_page_content, on_nav), its registration in mkdocs_src/mkdocs.yml")
    print_info("Tests: U+00A0/U+202F before : ; ? ! %, a currency, inside « », thousand groups, never inserted; text only (attributes, comments, code, formulas, raw text untouched); French pages and TOC, French nav labels; a page rendered in memory")
    cmd = _build_pytest_cmd("backend/test_scripts/test_utilities/test_docs_fr_typography.py", test_names)
    return run_command(cmd, "Docs French typography tests", verbose=verbose)


def utils_docs_search_split(verbose: bool = False, test_names: list = None) -> bool:
    """Test the MkDocs hook that splits the search index by language after the build (DOC-2)."""
    print_section("Utils: Docs Search Language Split")
    print_info("Testing: mkdocs_src/hooks/search_language_split.py (language_of, split_index, on_post_build), its registration in mkdocs_src/mkdocs.yml and overrides/main.html, the built site's search_index.<lang>.json")
    print_info("Tests: first path segment decides the language (it/ fr/ es/, anything else en), every doc in exactly one file, same config, input untouched, four UTF-8 files written beside the full index, a missing index warns and does nothing, the built site's files and script order")
    cmd = _build_pytest_cmd("backend/test_scripts/test_utilities/test_docs_search_split.py", test_names)
    return run_command(cmd, "Docs search language split tests", verbose=verbose)


def utils_normalize_dashboard_fixture(verbose: bool = False, test_names: list = None) -> bool:
    """Test the gallery dashboard fixture normalizer: money scaled, shares and fractions left alone, invariants loud and value-free."""
    print_section("Utils: Dashboard Fixture Normalizer")
    print_info("Testing: scripts/normalize_dashboard_fixture.py (_walk, _verify, normalize_file), dev.py mkdocs normalize-dashboard-fixture")
    print_info("Tests: money and per-unit prices scaled, allocation shares, Yield on Cost and one-day price change untouched, shares summing to 100, YoC = gross/WAC and price change vs P&L change enforced, messages without values, the committed fixture")
    cmd = _build_pytest_cmd("backend/test_scripts/test_utilities/test_normalize_dashboard_fixture.py", test_names)
    return run_command(cmd, "Dashboard fixture normalizer tests", verbose=verbose)


def utils_backup_cli(verbose: bool = False, test_names: list = None) -> bool:
    """Test the instance backup command line: output path, switch to the data directory's owner, create, inspect."""
    print_section("Utils: Backup CLI")
    print_info("Testing: scripts/backup_cli.py (_output_path, _drop_root_privileges, _dispatch, cmd_create, cmd_inspect), python scripts/backup_cli.py")
    print_info("Tests: --output folder/file/relative/~, root → setgroups/setgid/setuid of the owner or a message, exit codes of create and inspect, the script end to end")
    cmd = _build_pytest_cmd("backend/test_scripts/test_utilities/test_backup_cli.py", test_names)
    return run_command(cmd, "Backup CLI tests", verbose=verbose)


def utils_backup_cli_restore(verbose: bool = False, test_names: list = None) -> bool:
    """Test the restore from the command line: restore ARCHIVE with its confirmation, pending, pending --cancel."""
    print_section("Utils: Backup CLI restore")
    print_info("Testing: scripts/backup_cli.py (cmd_restore without --dry-run, cmd_pending), python scripts/backup_cli.py pending")
    print_info("Tests: --yes, the word typed on a pty, a pipe refused, declined, blocked, already pending, confirm errors; pending and --cancel")
    cmd = _build_pytest_cmd("backend/test_scripts/test_utilities/test_backup_cli_restore.py", test_names)
    return run_command(cmd, "Backup CLI restore tests", verbose=verbose)


def utils_backup_cli_secure(verbose: bool = False, test_names: list = None) -> bool:
    """Test the secure backup from the command line: create with a password, inspect and restore an envelope, decrypt."""
    print_section("Utils: Backup CLI secure backup")
    print_info("Testing: scripts/backup_cli.py (create --encrypt / --password-file / --password-stdin, inspect, restore --dry-run and decrypt of an .lfbk)")
    cmd = _build_pytest_cmd("backend/test_scripts/test_utilities/test_backup_cli_secure.py", test_names)
    return run_command(cmd, "Backup CLI secure backup tests", verbose=verbose)


def utils_backup_cli_sealed(verbose: bool = False, test_names: list = None) -> bool:
    """Test the sealed backup from the command line: keygen, create --recipient / --sealed, a sealed tar read with an identity."""
    print_section("Utils: Backup CLI sealed backup")
    print_info("Testing: scripts/backup_cli.py (keygen, create --recipient / --sealed, inspect, decrypt and restore --dry-run of a sealed .tar with --identity-file)")
    cmd = _build_pytest_cmd("backend/test_scripts/test_utilities/test_backup_cli_sealed.py", test_names)
    return run_command(cmd, "Backup CLI sealed backup tests", verbose=verbose)


def utils_backup_cli_recover(verbose: bool = False, test_names: list = None) -> bool:
    """Test the restore recovery from the command line: pending --json and pending --recover <choice>."""
    print_section("Utils: Backup CLI recover and --json")
    print_info("Testing: scripts/backup_cli.py (pending --json: one line, the six states, privacy; pending --recover previous|cancel: exit codes 0/3/4/5, idempotency)")
    cmd = _build_pytest_cmd("backend/test_scripts/test_utilities/test_backup_cli_recover.py", test_names)
    return run_command(cmd, "Backup CLI recover tests", verbose=verbose)


def utils_all(verbose: bool = False) -> bool:
    """Run all utility tests."""
    if _common.nothing_left_to_run("utils"):
        return _common.consolidated_verdict("utils")
    return _run_test_suite(
        suite_name="Utility Tests",
        tests=_get_category_tests_for_all("utils", verbose),
        verbose=verbose,
        info_msgs=["Testing utility modules and helper functions"],
        resume=_common._RESUME_MODE,
    )


def populate_registry(registry: dict) -> None:
    """Register all utility test entries."""
    cat = make_category(
        help_text="Utility module tests (decimal, datetime, geo, currency, cache)",
        description="""
Utility Module Tests

Tests for utility modules and helper functions:
  • Decimal precision, Datetime, Day count conventions
  • Geographic area normalization, Sector normalization
  • Currency utilities, Cache utilities
  • Provider core cache & thread isolation
  • Test-runner CLI contract (coverage-js-adapter command building, registry dispatch)
""",
        # These are functions over values. The three the static classifier could
        # not prove pure only touch a database because they import a helper that
        # mentions one.
        default_isolation="write-scoped",
    )
    add_test(cat, "decimal-precision", utils_decimal_precision, name="Decimal Precision", desc="Model precision, truncation, edge cases")
    add_test(
        cat,
        "real-decimal",
        utils_real_decimal,
        name="RealDecimal and Digit Limits",
        desc="C-97a: Transaction.quantity RealDecimal(22, 10), Transaction.cost_basis_override (per-unit, D5) and the five price columns RealDecimal(24, 12), a TypeDecorator over Numeric; what fits reads back exactly (a REAL as its shortest decimal, at most 15 significant digits, rounded to the scale, padded to 6 decimals as today), written as today (REAL, INTEGER when whole), no double noise; amount, AssetEvent.value, volume and FxRate.rate unchanged; truncation to the scale then 15 significant digits on a RealDecimal column (ROUND_DOWN), FX untouched; decimal_limit_issue (decimalPlacesExceeded before significantDigitsExceeded, trailing zeros not counted); round_computed_value (D6: scale then 15 significant digits, ROUND_HALF_EVEN, always within decimal_limit_issue)",
        # PURE: each round trip opens a private in-memory SQLite engine of its own test and disposes it; the lane
        # database is never opened. Everything else is a function over values. No server, no network.
        isolation="pure",
    )
    add_test(cat, "datetime", utils_datetime, name="Datetime Utils", desc="Timezone-aware datetime helpers")
    add_test(
        cat,
        "origins",
        utils_origins,
        name="Canonical Origin",
        desc="H-55 v2: canonical_origin, scheme://host[:port] lower-cased, default ports dropped, IPv6 in brackets, international names in punycode, path/query/fragment/user info dropped; None for a wrong shape, a bad port, and a host that could reach a header (a ';', a quote, a comma, a space, an IPv6-looking host that is no address, a zone id)",
        # PURE: a function over strings. No DB, no server, no network.
        isolation="pure",
    )
    add_test(
        cat,
        "pydantic-errors",
        utils_pydantic_errors,
        name="Pydantic Errors",
        desc="W-B77/W-B70: backend/app/utils/pydantic_errors.py, one copy for the batch and BRIM parses: PLAIN_PARAM_TYPES exactly str/int/float/bool/None; loc_to_field (indices skipped, a leading resolved_fields dropped, None when empty); error_params (a copy of a plain ctx, loc never read so a field error keeps it, None for a ctx missing, empty or not plain, a packed sub-error alike); the two call sites keep no copy and import it",
        # PURE: functions over values, pydantic models of the test's own, two app sources read with ast. No DB, no
        # server, no network, no writes.
        isolation="pure",
    )
    add_test(cat, "day-count", utils_day_count, name="Day Count Conventions", desc="ACT/365, ACT/360, ACT/ACT, 30/360")
    add_test(cat, "geo-utils", utils_geo_utils, name="Geographic Utils", desc="ISO-3166-A3 normalization, weights")
    add_test(cat, "version", utils_version, name="Version Utils", desc="get_git_version: LF_APP_VERSION when set, else git describe in a checkout, else VERSION, else unknown; get_version_info")
    add_test(
        cat,
        "coverage-js-adapter",
        utils_coverage_js_adapter,
        name="JS Coverage Adapter",
        desc="Line-based counting across the vitest/E2E double compilation, istanbul conversion",
        # Overrides the category default: these are functions over plain dicts
        # built inside the test. No session, no server, no file read — the module
        # imports nothing but stdlib.
        isolation="pure",
    )
    add_test(cat, "sector-normalization", utils_sector_normalization, name="Sector Normalization", desc="FinancialSector enum, aliases")
    add_test(cat, "currency-utils", utils_currency_utils, name="Currency Utils", desc="Currency listing, flag mapping")
    add_test(cat, "cache-utils", utils_cache_utils, name="Cache Utils", desc="NamedCache, TTL, registry, stats")
    add_test(
        cat,
        "rate-window",
        utils_rate_window,
        name="Rate Window",
        desc="SlidingWindowLimiter: a hit counts until exactly window_seconds later, peek never counts, a refused hit records nothing, retry_after waits for enough hits to leave (per-call limit too), independent keys with None among them, reset/clear, len = the keys with a hit still in the window, eviction at max_keys of the key with the fewest hits still in the window, the one used or regrouped longest ago among them (E-14: exact expiry, so expired hits protect nothing even on a key read since; no limit enters the choice; no search, no eviction_scan; a spray of fresh keys never frees a heavier key, locked or a hit short of its limit; never refused, never unbounded, the private expiry heap at most 2·len+64 entries), exactly N allowed under concurrent threads",
        # PURE: no lane DB, no server, no environment read; an injected fake clock, threads of its own, no sleeps.
        isolation="pure",
    )
    add_test(
        cat,
        "cooldown",
        utils_cooldown,
        name="Cooldown",
        desc="Cooldowns: an unknown key may call and is not tracked; once a pause is over (its trial taken or not) the n-th refusal in a row waits min(base·2^(n−1), max), a positive finite Retry-After a floor honoured above the max up to the hard max, a jitter of up to 10 % on top and never below the floor, base/max given to a call for that call only, a refusal more than max after the end of the pause starts over, no overflow on any streak; while a pause runs, a refusal or a success of a call already in flight counts nothing and never shortens it, only a Retry-After ending later extends it (to now + floor, no jitter), so a burst of 429s counts one; check counts the pause down, then lets one trial through at a time for trial_seconds; succeeded after the pause forgets and returns the count, released frees the trial and keeps it; a backwards clock never lengthens a wait; snapshot, reset/len, independent keys with None among them, LRU eviction at max_keys, one trial and one counted refusal under concurrent threads; retry_after_seconds reads delta-seconds and HTTP-dates, None otherwise; RateLimitedError combines with a domain exception",
        # PURE: no lane DB, no server, no environment read; an injected fake clock and random source, threads of its own, no sleeps.
        isolation="pure",
    )
    add_test(
        cat,
        "container-registry",
        utils_container_registry,
        name="Container Registry",
        desc="Trusted GHCR challenge/token flow, result mapping, endpoint guards, secret redaction",
        isolation="pure",
    )
    add_test(
        cat,
        "served-content-types",
        utils_served_content_types,
        name="Served Content Types",
        desc="Uploaded content reaches the browser only as types that cannot run: the text preview of an upload is text/plain; charset=utf-8 with X-Content-Type-Options: nosniff whatever type was stored (a CSV still readable, whole or windowed); a broker report opens inline only with download=false and a type that cannot carry active content (PDF, PNG, CSV, JSON, plain text), while HTML, SVG, XML, XHTML and unknown types are attachments, download=true (the default) is always an attachment, and every answer carries nosniff",
        # Fresh apps holding the uploads and broker import routers, called through httpx's in-process
        # ASGI transport; sign-in and session dependencies overridden, broker report lookups monkeypatched,
        # each upload a real file and sidecar, all under tmp_path. No DB, no server, no network.
        isolation="pure",
    )
    add_test(
        cat,
        "nosniff-content-types",
        utils_nosniff_content_types,
        name="nosniff Content Types",
        desc="Every file the app serves has its right type (nosniff refuses a script or a style sheet of another type; nothing goes out as application/octet-stream): .js/.mjs a JavaScript MIME type, .css text/css, .wasm application/wasm, .woff/.woff2 font/…, .json/.webmanifest a JSON MIME type, .svg image/svg+xml, any other extension never application/octet-stream; for the extensions the rules name (fake files at the SPA catch-all, the /_app mount and /mkdocs) and for every extension of frontend/build and mkdocs_src/site (skipped, with the reason, when a tree is not built; its table printed), on this machine and in an interpreter that read no system mime.types file, as on python:3.13-slim",
        # Fresh FastAPI() apps over fake trees under tmp_path and over the real trees (read only), raw ASGI calls; one
        # child interpreter importing backend.app.main with mimetypes.knownfiles emptied, its data directory under
        # tmp_path. No DB, no server, no network.
        isolation="pure",
    )
    add_test(cat, "provider-core-cache", utils_provider_core_cache, name="Provider Core Cache", desc="Thread isolation, timeout, caches")
    add_test(cat, "roi-utils", utils_roi_utils, name="ROI Utils", desc="annualized_to_cumulative, calculate_mwrr/_series")
    add_test(cat, "translation-utils", utils_translation_utils, name="Translation Utils", desc="get_babel_locale + English fallback")
    add_test(cat, "ai-export-probe-helpers", utils_ai_export_probe_helpers, name="AI Export Probe Helpers", desc="Fast unit tests for probe orchestration, metrics, security, and audit helpers; never runs a real prompt probe")
    add_test(
        cat,
        "check-frontend-build",
        utils_check_frontend_build,
        name="Frontend Build Guard",
        desc="scripts/docker/check_frontend_build.sh: a production build passes (a missing .build-debug only warns); a debug marker, any sourcemap (named), the coverage marker or a missing index.html/200.html exits 1",
        # Throwaway build trees in tmp_path, the script run with sh: no DB, no
        # server, no network, no repo writes.
        isolation="pure",
    )
    add_test(
        cat,
        "release-image-contract",
        utils_release_image_contract,
        name="Release Image Contract",
        desc="release.yml rebuilds the frontend (production) and the docs between the gallery and both image builds, the nightly report reads every soft-gated step, the gallery fails a release (soft on dev only), cache keys carry the runner image, tags follow the user guide (latest = light, X.Y.Z full, X.Y.Z-light, no v; a variant without tags is not pushed) and the release notes say so; the Dockerfile takes frontend/build only through the guarded frontend stage",
        # Reads .github/workflows/release.yml and Dockerfile, mutates copies in
        # memory: no DB, no server, no network, no writes.
        isolation="pure",
    )
    add_test(
        cat,
        "dev-cli-image",
        utils_dev_cli_image,
        name="dev.py in the Docker image",
        desc="dev.py on a copy of the image's /app file set (no backend/test_scripts): help, user, db and backup run; test, i18n and mkdocs translate answer «not available in this installation» and exit 2; user create/reset/list on a temporary DB; the role of a created account (L12): user create is an administrator by default and with --role admin, an ordinary account with --role user even alone in an empty DB, an unknown role an argparse error that creates nobody, and user_cli.py create-user an ordinary account (❌ and exit 1 on a weak password or a taken username) while create-superuser stays an administrator; dev.py backup (B1): listed in --help, group help exits 0, backup create on the image's DB writes exactly one librefolio-backup-*.zip into <data dir>/backups/ with no job folder left and that DB inside, inspect exits 0 on it and 1 on a missing file; the Dockerfile HEALTHCHECK probes the port the CMD binds, like compose",
        # A copy of the image tree and a temporary DB under tmp_path, dev.py in
        # subprocesses: no lane DB, no server, no network, no repo writes.
        isolation="pure",
    )
    add_test(
        cat,
        "dev-cli-docker",
        utils_dev_cli_docker,
        name="dev.py docker commands and the image contract",
        desc="The Docker lot (CP7a): the final image installs tzdata and tzdata-legacy (P-4); EXPOSE and service librefolio of every compose file publish only the CMD's port, 6040 (C-37); both compose files pin PORT, HOST and LIBREFOLIO_DATA_DIR in environment to what the image binds and mounts (N-8); docker exec runs sh -c 'exec gosu \"${LIBREFOLIO_UID:-1000}:${LIBREFOLIO_GID:-1000}\" python dev.py \"$@\"' sh <args>, each argument one element and verbatim through a real sh, as the ids of the image's ENV or, with neither set, entrypoint.sh's 1000:1000, exit 1 without a command (32-3); docker build freezes the version once, rebuilds the frontend when its sources changed, it is not production, has no recorded version or another one, sets LF_APP_VERSION around that build only and gives it back, records .build-version only on success, writes the same version to VERSION, and tags the image from VERSION, not from a later -dirty git answer (M-25); _check_env_file compares PORT only; each static check with synthetic negative controls",
        # Reads the Dockerfile, compose files and entrypoint.sh; dev.py loaded in-process with its
        # commands stood in for, a fake project and build markers under tmp_path,
        # a local sh with stand-ins for gosu and python: no DB, no server, no
        # network, no Docker, no repo writes.
        isolation="pure",
    )
    add_test(
        cat,
        "js-cache-fail-loud",
        utils_js_cache_fail_loud,
        name="JS Cache Fail-Loud (I1)",
        desc="update_js_cache: undownloadable+uncached resource or partial font subsets → hard failure → exit 1; cached copy → exit 0; consumer-scoped narrowing (a docs-only asset does not fail a frontend build, an unknown attribution still does); js companions (MathJax fonts): names from the cached script, fetched beside the CDN URL even when the script is up to date, refreshed on script change, --force or a missing record; a missing file with no cached copy → hard failure; only pattern-matching stale files removed",
        # tmp_path + monkeypatched network only: no DB, no server, no repo writes.
        isolation="pure",
    )
    add_test(
        cat,
        "gate-docs-links",
        utils_gate_docs_links,
        name="Docs Link Gate",
        desc="Cross-boundary link discovery: a resolved const confirms a link but an unresolved interpolation may never condemn one, plugin/provider folders are found by glob rather than by a hand-written list, and what cannot be decided is reported as unverifiable instead of dropped; a link's anchor must be an id of the page's own MkDocs render in English and in every translation, and dev.py builds its CLI without MkDocs while check-links says it needs it; after mkdocs build every relative file URL of the site (img/source/video/audio, links to files) must resolve, a translation being built one folder deeper, or the build exits 1",
        # Discovery on files under tmp_path; dev.py runs in child processes, on a docs tree
        # under tmp_path for the anchor verdict, on a built site under tmp_path for the asset
        # check, and on the code alone for the runs without MkDocs. Reads mkdocs_src/mkdocs.yml
        # (the site configuration the anchors are rendered with).
        isolation="pure",
    )
    add_test(
        cat,
        "pwa-assets",
        utils_pwa_assets,
        name="PWA Assets",
        desc="Opaque RGB icons at exact sizes (any, maskable, apple-touch 180), maskable logo inside the 0.40 safe zone on the splash beige, one manifest entry per purpose and size with no file serving both, app.html apple-touch link at 180x180, sw.js build stamp = md5(offline.html)[:8]; H-52: stamp_service_worker() writes sw.js only when its stamp changes (the same page leaves its bytes and mtime alone, an edited page gets the new stamp on line 2), and cmd_fe_build stamps it before the build command, both on copies under tmp_path",
        # Reads committed files under frontend/static/ and frontend/src/app.html; the stamping cases (H-52) write
        # copies under tmp_path only: no DB, no server, no network, no write to the checkout.
        isolation="pure",
    )
    add_test(
        cat,
        "gate-i18n-usage",
        utils_gate_i18n_usage,
        name="i18n Usage Gate",
        desc="Three verdicts where the audit had two: typed unions are expanded from the code that declares them, a bare namespace root no longer absolves everything beneath it, ternary arguments are seen, a key prefix chosen between two literals is expanded over both branches, and 'not verified' stays apart from 'dead' so neither absolution nor condemnation is a default",
        isolation="pure",
    )
    add_test(
        cat,
        "gate-i18n-catalog",
        utils_gate_i18n_catalog,
        name="i18n Catalogue Gate",
        desc="The catalogue the app loads is generated from its sources (frontend/src/lib/i18n/base/, a folder per subsystem with its prefixes.txt, each plugin's i18n/), every rule proven both ways on synthetic trees: a key belongs to the plugin holding it, else to the subsystem with the longest declared prefix, else to base; a key in two sources, a string against a branch, a key outside its prefix's folder, a prefix declared twice, a subsystem without prefixes, a source without English, a key English lacks, a value that is not a string, unreadable JSON and an unknown language are errors for merge, build and check, all reported at once; a missing translation is filled from English with a warning when building, an error when strict, and stays missing without fallback; each source keeps its key order (base, subsystems by name, plugins by path) and one source comes back byte for byte; build writes only what changed, read-only, with a sha256 stamp, and refuses a hand-edited file unless forced; route refuses a key only a plugin could own, a plugin target being exactly <*_providers|*_plugins>/<plugin> with its plugin.py; move, split, remove and set keep the catalogue and rewrite only their files; catalogs_at reads the legacy and the sources layouts, check --against compares without fallback, absorb merges three ways per key and language (every conflict reported and nothing written unless --prefer settles them, a removal conflict settled for the whole key, all or nothing); in the repository the sources merge strictly, base holds the four languages with the same keys in the generator's format, load_catalog reads the checkout without a build, git ignores the generated files and none of the sources, and the index never tracks them beside base/",
        # Synthetic trees and throwaway git repositories under tmp_path; the repository's own
        # sources are only read, and asked about with git check-ignore and git ls-files.
        # No DB, no server, no network, no writes outside tmp_path.
        isolation="pure",
    )
    add_test(
        cat,
        "gate-plugin-layout",
        utils_gate_plugin_layout,
        name="Plugin Layout Gate",
        desc="Every first-party plugin is a folder <family>/<name>/ holding __init__.py (its docstring and nothing else) and plugin.py, in the six families the app's registries declare (brim, asset, FX, risk, signal, tool), plugin being the module discovery loads; no family keeps a plugin as a single module and none is empty; no import in backend/app, backend/test_scripts, scripts or dev.py reaches a plugin's package instead of its plugin module or a _helper beside it, relative and lazy imports included, and no string names one (patch targets, logger names, __module__)",
        # ast and filesystem reads of the repository's sources, never imported; the control
        # cases build their trees under tmp_path. No DB, no server, no network, no writes
        # outside tmp_path.
        isolation="pure",
    )
    add_test(
        cat,
        "gate-plugin-i18n-ownership",
        utils_gate_plugin_i18n_ownership,
        name="Plugin i18n Ownership Gate",
        desc="Each plugin's translations live in its own i18n/ fragment, judged by the metadata its registry publishes: a plugin's space is brimPlugins.<code> (the code being its folder), assets.providerParams.<provider code> and pluginSettings.asset.<provider code> for an asset plugin, pluginSettings.fx.<provider code> for an FX plugin (the code as the registry has it: ECB, MOCKFX), the parent of a signal's display_name_key or of a risk analytic's name_i18n_key, or exactly a tool's name_i18n_key and description_i18n_key, and it is exclusive when no other plugin has it; R1 every fragment key lies in its plugin's space; R2 every key a plugin declares in its exclusive space (display_name_key, description_key, name_i18n_key, description_i18n_key, label_key, x-i18n-key, x-tooltip-key, the BRIM name and description, and an asset or FX plugin's settings_fields: each field's label_key and description_key and each option's label_key, the frozen declarations dumped to plain data) lives in its fragment; R3 no fragment key lies in another plugin's space or is declared by another plugin; R4 every catalogue key under an exclusive space lives in that plugin's fragment, tools aside; every rule proven both ways on synthetic trees, and a sentinel fails on a published key field the gate does not read, in the signal and risk definitions, in the plugins' settings and in the attributes of PluginSettingField and SettingOption",
        # Imports the registries (discovery instantiates the plugins) and reads what they publish; synthetic trees under tmp_path. No DB, no server, no network.
        isolation="pure",
    )
    add_test(
        cat,
        "gate-event-loop-io",
        utils_gate_event_loop_io,
        name="Event Loop BRIM I/O Gate",
        desc="No async def under backend/app/api/v1 calls a synchronous function of backend/app/services/brim/brim_provider.py (its top-level defs and their aliases) directly: such I/O runs on the event loop and must go through await asyncio.to_thread(fn, ...); a reference handed to to_thread, the body of a nested def or lambda, an awaited coroutine of the module and a sync handler are allowed; every import form is followed (from-import, import as, plain, relative, lazy, a function imported by name); the detector is proven both ways on in-memory sources, and the scan must reach an API module that imports the store",
        # ast and filesystem reads of the repository's sources, never imported; the control
        # cases are in-memory strings. No DB, no server, no network, no writes.
        isolation="pure",
    )
    add_test(
        cat,
        "gate-aiosqlite-leak",
        utils_gate_aiosqlite_leak,
        name="aiosqlite Leak Gate",
        desc="No backend test leaves open an aiosqlite connection it created: the shared conftest's autouse guard tracks every connection born in the main thread during a test (weak references, creation stack followed across SQLAlchemy's greenlet) and fails that test at its own teardown if one is still open and not excused by the explicit, reasoned AIOSQLITE_LEAK_EXCEPTIONS (empty); proven as presences: the C-93 shape (in-memory engine queried, session closed, engine not disposed) is reported with a stack reaching the test and cleared by dispose; connections closed by async with, dispose or a NullPool session are tracked but not reported; a connection born in another thread is not tracked, one born before a window is not attributed to it; an exception excuses its own nodeid at a boundary only, and an entry without a prefix or a reason is refused; a tracked object without aiosqlite's private _connection fails loudly; install wraps once and the conftest's window surrounds every test; a child pytest loading the real conftest errors the leaking test, and only it, at its teardown",
        # Private in-memory aiosqlite databases, a worker thread of its own, and a child pytest that loads
        # the real conftest on a synthetic file under tmp_path: no lane DB beyond the conftest's own session
        # read (as in every pytest process), no server, no network, no writes outside tmp_path.
        isolation="pure",
    )
    add_test(
        cat,
        "tools-wire",
        utils_tools_wire,
        name="Tool Wire",
        desc="Strict UTF-8 JSON, byte/depth boundaries and sanitized validation issues",
        isolation="pure",
    )
    add_test(
        cat,
        "runtime-isolation",
        utils_runtime_isolation,
        name="Runtime Isolation",
        desc="Per-lane port/data propagation, production guards, readiness identity and process ownership",
        # Only monkeypatches os.environ/sys.argv and builds argparse parsers;
        # no DB, no server, no filesystem writes.
        isolation="pure",
    )
    add_test(
        cat,
        "confined-path",
        utils_confined_path,
        name="Confined Path",
        desc="confined_path keeps a request path inside the folder it is joined to: a file inside, parent segments coming back inside, an empty path (the resolved root), a missing file inside and a symlink pointing inside are returned resolved, also when the root itself sits behind a symlink; parent segments leaving at any depth, an absolute path outside, a sibling folder sharing the root's name prefix, a symlink pointing outside and a NUL byte are refused (None)",
        # A function over folders built under tmp_path: no DB, no server, no network.
        isolation="pure",
    )
    add_test(
        cat,
        "static-route-confinement",
        utils_static_route_confinement,
        name="Static Route Confinement",
        desc="The frontend catch-all, the documentation and the plugin icon routes serve the files of their own folder only: a path landing outside it (parent segments at several depths, an absolute path, a sibling folder sharing the plugin folder's name prefix) gets the SPA fallback (200.html, else index.html), the documentation's 404 and a 403, never the outside content, and a path the OS rejects gets a 403 from the plugin route; build files, client-side routes, documentation folders, the site index and plugin icons are still served",
        # Raw ASGI calls on the global app (the lifespan never runs) and on a fresh app holding the
        # uploads router with sign-in overridden; folders under tmp_path swapped in for the module
        # globals by monkeypatch. No DB, no server, no network.
        isolation="pure",
    )
    add_test(
        cat,
        "jwt-secret-blank",
        utils_jwt_secret_blank,
        name="JWT Secret Blank",
        desc="The JWT_SECRET read at import signs session cookies only when it holds something besides whitespace: a value made only of whitespace (three spaces, tab-space-newline, one space) is replaced by a random URL-safe key of at least 64 characters, new in every process, and a token signed with the blank value is refused by decode_jwt_token; a non-blank value is the key exactly as written, surrounding spaces included, and a token signed with it decodes to its user id; an unset or empty JWT_SECRET gives a random key, new in every process",
        # Each case imports auth_service in a fresh interpreter run in tmp_path, with a copy of the
        # environment carrying the case's JWT_SECRET. No DB, no server, no network.
        isolation="pure",
    )
    add_test(
        cat,
        "test-server-preparation",
        utils_test_server_preparation,
        name="Test Server Preparation",
        desc="dev.py server --build-only runs exactly the server's pre-bind steps in today's order and mode (the frontend in debug under --test, through cmd_fe_build with --rebuild, then MkDocs, then the non-strict JS cache) and returns their exit code without checking the port, running a command or exec'ing uvicorn, and the runner's prerequisites command is such a run; front build and api client check frontend/node_modules/.bin first (openapi-zod-client, svelte-check, vite; the API client only its generator, symlinks or shim files) and exit 1 naming the missing tools and npm ci before any npm or npx call; SharedTestServer.start() checks the port, then runs python -u dev.py server --test --build-only in the foreground with its output visible and in order on a pipe (its own stdout and stderr flushed right after its info line) and the runner's environment, never the coverage wiring the server gets, and only then spawns the backend and starts STARTUP_TIMEOUT: a build longer than the timeout still starts, a failed build (False, or an exit code it names) spawns nothing, an occupied port builds nothing; mkdocs gallery runs the same step after its database step and port check and before Playwright, with Playwright's environment (LF_APP_VERSION and --test-port included), exits 1 when it fails, and --list builds nothing; without --workers the gallery runs 60% of the CPUs (rounded, the count read at each call) as browser workers, at least one (an explicit --workers wins), and sizes its server from them; the shared backend's stdout and stderr go to one file, shared-backend.log in the run's --log-dir (DEVNULL as before without one, the terminal under verbose), stderr merged, PYTHONUNBUFFERED=1, the runner's handle closed after the spawn, emptied by the instance's first start and appended to by a restart; a start that fails (an exit during startup, or STARTUP_TIMEOUT) prints the path and the last 30 lines that start wrote, read from at most the last 64 KiB, or (no output); log_tail() returns whole lines after an offset; a real one-line child started through exec_unmasked.py proves its stderr lands in the file",
        # Fakes only, but for one case: the seams of dev.py and _server.py monkeypatched, every real process and
        # signal forbidden, node_modules/.bin layouts under tmp_path; --list reads frontend/e2e/gallery.spec.ts.
        # The case (H-12) starts one one-line Python child through the real exec_unmasked.py: only that argv may
        # start, only its group may be signalled. No DB, no server, no network, no port, no writes outside tmp_path.
        isolation="pure",
    )
    add_test(
        cat,
        "test-runner-cli",
        utils_test_runner_cli,
        name="Test Runner CLI Contract",
        desc="test_names → pytest -k semantics on the real coverage-js-adapter action, registry dispatch forwarding, coverage_js.py compile check",
        # Monkeypatches run_command/subprocess.run and reads source text only;
        # no DB, no server, no network, no repo writes.
        isolation="pure",
    )
    add_test(
        cat,
        "dev-cli-db-path",
        utils_dev_cli_db_path,
        name="Dev CLI db path",
        desc="dev.py db current/upgrade/downgrade/migrate/check act on the [path] they are given (absolute, or relative to the project root), never on the configured database: a missing file is refused (upgrade creates it), a path with %, ? or # is refused, db check runs the CHECK constraints hook; without a path the configured database is used; B-37 (DBP-j, static): env.py's run_migrations_online registers a connect listener on its engine, for every URL, before it connects, executing PRAGMA trusted_schema=OFF",
        # Temporary databases and data dirs under tmp_path, free ports, dev.py and alembic
        # in subprocesses: no lane DB, no server, no network, no repo writes (db migrate
        # only ever runs its refusal, with no database at head within its reach).
        isolation="pure",
    )
    add_test(
        cat,
        "dev-port-check",
        utils_dev_port_check,
        name="Dev port check",
        desc="dev.py check_port_in_use names who holds a TCP port on Linux as on macOS: the fuser call passes Python's own subprocess.run argument check and its PIDs come back with their process names; on the host, lsof (macOS) or fuser (Linux) report this process while it listens on 127.0.0.1 and no longer once it has closed the socket; no call in dev.py passes capture_output together with stdout= or stderr=; only a listener counts (H-12): a socket that holds the port through an accepted connection, its listener closed, is not reported where lsof exists, as in the runner's port_holders",
        # platform.system and subprocess.run monkeypatched for the Linux case, a 127.0.0.1
        # socket on a port the OS picks, read-only lsof/fuser/ps children, dev.py parsed:
        # no DB, no server, no network beyond loopback, no writes.
        isolation="pure",
    )
    add_test(
        cat,
        "dev-server-interrupt",
        utils_dev_server_interrupt,
        name="Dev server interrupt",
        desc="Ctrl+C on dev.py server lets the server finish its own shutdown (Z-10): scripts/cli_base.py run_server_live does not forward the first Ctrl+C (the terminal gave it to the whole group), waits for the server up to the grace (none = no limit) and returns 130; when the grace runs out, or at a second Ctrl+C, it SIGKILLs the server and waits for it; a SIGTERM to dev.py alone is forwarded once and waited for the same way (143), a SIGTERM to the whole group too, a second SIGTERM forces; dev.py never returns before its server is gone; a server that stops by itself gives its own exit code, one that cannot start gives 1 and an error; the server runs in the project root with os.environ plus env; the SIGTERM handler in force before the call is back after it, on every path; dev.py _server_stop_grace(env) is shutdown_timeout_seconds(env) + 2 s (unset or blank 10.0, 5 → 7.0, 2 → 4.0, 600 → 602.0, 0 → None, unusable → 10.0), read from the env it is given; cmd_server launches uvicorn through run_server_live with that grace and never through run_command_live, and --coverage still execs coverage run",
        # Real child processes: a stand-in for dev.py and a fake server, two Python scripts written under tmp_path,
        # started in a session of their own (start_new_session) without the runner's coverage wiring; signals go only
        # to that process group or to the stand-in's pid, and whatever survives a case is SIGKILLed through that group.
        # In-process cases start a child that exits at once, or a program that does not exist; cmd_server runs in-process
        # with its builds, port check and launchers stood in for, every real process, exec and signal forbidden.
        # No DB, no server, no network, no port, no writes outside tmp_path.
        isolation="pure",
    )
    add_test(
        cat,
        "dev-designer-lab-banner",
        utils_dev_designer_lab_banner,
        name="Dev Designer Lab banner",
        desc="dev.py server lists 🎨 Designer Lab: http://localhost:<port>/designer-lab right after the Frontend line of «Available endpoints» only when a script under frontend/build/_app/immutable/ (any depth) holds DESIGNER_LAB_MARKER, the LAB_MARKER the Vite plugin exports, inside a longer string too: not without a build, not for a release build nor a debug build made with LF_DESIGNER_LAB=0 (whatever .build-debug says), yes for a debug build with the Lab and a production build made with LF_DESIGNER_LAB=1, as the auto-build left it; source maps, CSS, HTML, _app/env.js and the static files never count; a listing that fails or a script that cannot be read reads as no Lab (the script skipped, the scan going on) and the server still reaches its launch; --build-only prints no endpoint list and never asks; front dev lists http://localhost:5173/designer-lab after its URL unless LF_DESIGNER_LAB is exactly 0",
        # The real helper on fake builds under tmp_path; cmd_server and cmd_fe_dev run in-process with their runtime
        # configuration, builds, port check and launcher stood in for, every real process, exec and signal forbidden,
        # os.environ compared before and after; reads frontend/scripts/designer-lab/vite-plugin.mjs. No DB, no server,
        # no network, no writes outside tmp_path.
        isolation="pure",
    )
    add_test(
        cat,
        "coverage-combine",
        utils_coverage_combine,
        name="Coverage Combine",
        desc="Coverage parts are combined as a directory: a part coverage renames while the combine starts and one landing after coverage's own listing are both folded in with nothing left behind, the shared backend's parts in the cwd too (.coveragerc is never a part), and a failed combine turns the parallel pass red; a run's parts/run-* directory goes once combined and stays, named with the unreadable part, when not; --cov-clean-backend empties parts/ of coverage data and keeps the junit reports; a finished part holding coverage's schema and no rows is removed and named without failing the combine (worker parts and the shared backend's alike), one with a transient name is never judged empty",
        # Temporary files and coverage subprocesses on them, cwd moved into tmp_path: no DB, no server, no network, no repo writes.
        isolation="pure",
    )
    add_test(
        cat,
        "translation-code-blocks",
        utils_translation_code_blocks,
        name="Translation Code Blocks",
        desc="Aphra cleanup never collapses whitespace inside fenced code; translated blocks get the EN indentation back before the write; translate-validate raises code-block-indent; every up-to-date translation keeps the EN indentation",
        # Pure functions over strings, plus a read-only pass over mkdocs_src/docs and
        # the translation hash cache: no DB, no server, no network, no repo writes.
        isolation="pure",
    )
    add_test(
        cat,
        "translation-cache",
        utils_translation_cache,
        name="Translation Cache",
        desc="A language counts as done only for the EN version it was translated or stamped from: after an EN edit, a language that fails (parallel and sequential paths), is left out by --lang or is cut short by an interruption is offered again by the next run, and its failure keeps the last translated_at; a failed --force retry of an unchanged page stays done; translate-stamp of a changed EN reopens the languages it does not stamp and clears the failure records of those it does; an EN edit saved while the analysis runs is offered again too, the md5 recorded being the one of the bytes translated (LF and CRLF); the CHANGELOG translates by pieces: the preamble and each chapter are units, a chapter over the threshold is cut at its ###/#### headings outside fenced code into pieces keyed by their heading words, and the English pieces assemble back byte for byte; a second run translates nothing, a changed or inserted section is translated alone and every other part kept byte for byte, a removed or moved one is rebuilt without the model, the parts being found again by their recorded index; a language that fails keeps its chapter as it was, or absent; a new translation that adds a section, drops its opening heading or breaks the chapter at a seam is refused and the chapter kept; --file CHANGELOG.md translates no page, no --file does the pages then the CHANGELOG; translate-stamp --file CHANGELOG.md records a hand port piece by piece, and without --file leaves the CHANGELOG alone",
        # run_translate and run_stamp on a docs tree and a cache under tmp_path, the
        # LLM seams faked: no DB, no server, no network, no repo writes.
        isolation="pure",
    )
    add_test(
        cat,
        "translation-validator",
        utils_translation_validator,
        name="Translation Validator",
        desc="translate-validate reads what a page renders: fenced blocks of any kind and inline code are stripped before the HTML checks, so inline code such as EUR<USD is never a tag while a real tag's class/src/data-* changes are still reported; alt, title, aria-label, data-title and Markdown image alts of three words or more copied from the source warn (text-untranslated); every inline code span of the source stays in the translation, digit grouping aside, named as the source writes it (inline-code-missing); a page.md#anchor link must land on an anchor of the translated target or its EN fallback, the anchors being the ids of the page's own MkDocs render with the site configuration (anchor-missing, page_anchors.py); a raw-HTML relative file path copied unchanged from the source is an error, since a translated page is built one folder deeper (html-asset-depth); inline math is counted as pymdownx.arithmatex reads it (smart dollar), so a price such as 500 $ is never a formula and a formula after a number is never dropped (latex-inline-count); the structural diff counts blocks, not lines, for LINE_COUNT; the CHANGELOG is validated chapter by chapter through the page checks, its newest chapter open until its tag exists (vX.Y.Z or X.Y.Z, in the CHANGELOG's repository, or the CI run's ref): a missing translation or a chapter line unlike the English one is an error once released and information while open, an unknown, misplaced or repeated chapter is an error, a chapter changed since its translation is stale; translate-validate and translate-diff take the CHANGELOG with no --file or with --file CHANGELOG.md, their exit code counting the released chapters alone; an empty newest chapter leaves the one below it released",
        # Check functions on strings in memory and on a docs tree under tmp_path (DOCS_DIR
        # redirected in every test): no DB, no server, no network, never opens the repo's
        # docs or translation cache, no writes outside tmp_path. Reads mkdocs_src/mkdocs.yml
        # (the site configuration the anchors are rendered with).
        isolation="pure",
    )
    add_test(
        cat,
        "docs-fr-typography",
        utils_docs_fr_typography,
        name="Docs French Typography",
        desc="The fr_typography MkDocs hook turns the plain whitespace already standing before : (U+00A0), before ; ? ! and % and before a currency symbol after a digit (U+202F), inside « » (U+00A0) and between thousand groups (U+202F) into non-breaking spaces and never inserts one; a : ; ? or ! counts only before whitespace, the end of the text, closing punctuation or an entity, and a year is not joined to the next number; it reads text only: tags and attributes (a quoted > included) and comments pass through byte for byte, code, pre, kbd, samp, var, svg, math and arithmatex formulas are skipped with nesting counted, script, style, textarea and the other raw-text elements up to their end tag (a <!-- inside them opens no comment); it acts on the pages whose source is French (file.locale fr as mkdocs-static-i18n sets it, never the English fallback) and their table of contents at every level, and in the French build on the French navigation labels once mkdocs-static-i18n has put them in; mkdocs.yml registers it, and a French page rendered with the site's Markdown extensions keeps its code, formulas, diagram and attributes",
        # Strings in memory, the hook loaded by path. Reads mkdocs_src/mkdocs.yml: the hook's
        # registration, and the site configuration MkDocs loads (plugins and hooks) to render one
        # page in memory (Page.render, no build) and to dispatch on_nav on navigations built in
        # the test. No DB, no server, no network, no writes.
        isolation="pure",
    )
    add_test(
        cat,
        "docs-search-split",
        utils_docs_search_split,
        name="Docs Search Language Split",
        desc="The search_language_split MkDocs hook writes, after the build, one search index per language beside the full one (search_index.en/it/fr/es.json, same config): the language of a doc is its location's first path segment, exactly it, fr or es alone or before / or #, anything else (a name that only starts like one, a language that is not first, an English-only page) is en; every doc of the full index is in exactly one file, unchanged, none lost or duplicated, the input untouched; on_post_build writes four UTF-8 JSON files equal to the split and nothing else, leaves the full index byte for byte, and a missing index warns without raising; the real built index splits with counts adding up and the Italian pages not in en; mkdocs.yml lists the hook and not the script as extra_javascript, main.html loads search-language.js in extrahead; the built site has the four files, every page's html lang among the four languages, and each home page loads the script in the head before Material's bundle",
        # Dictionaries and files under tmp_path, the hook loaded by path. Reads mkdocs_src/mkdocs.yml, overrides/main.html
        # and (read only) the built mkdocs_src/site/. No DB, no server, no network, no writes outside tmp_path.
        isolation="pure",
    )
    add_test(
        cat,
        "normalize-dashboard-fixture",
        utils_normalize_dashboard_fixture,
        name="Dashboard Fixture Normalizer",
        desc="The gallery dashboard fixture normalizer scales money (currency objects and money-named plain numbers, per-unit prices included) to the target net worth and leaves quantities, percents, the allocation shares (summary and history, every dimension), the Yield on Cost fraction and the one-day price change fraction alone, whatever their money-like key name; after the transform every non-empty allocation list sums to 100 within the rounding of its shares, every available Yield on Cost equals gross income per unit over WAC, and every market-priced holding's one-day price change matches its one-day P&L change percent, or the script exits 1 without writing; its failure messages name the path family, never a sum, a share, a ratio, a Yield on Cost or a price change; the committed fixture passes the script's own invariants",
        # Synthetic reports under tmp_path, plus a read-only copy of frontend/e2e/dashboard-report.json:
        # no DB, no server, no network, no writes outside tmp_path.
        isolation="pure",
    )
    add_test(
        cat,
        "backup-cli",
        utils_backup_cli,
        name="Backup CLI",
        desc="scripts/backup_cli.py: the archive goes to <data dir>/backups/, into an existing --output folder, or to the --output file (relative to the working directory, which dev.py sets to the project root; ~ expanded), never replacing a file (-2, -3 … in a folder); --output is checked before the run and nothing is created for it until the archive moves there; an archive that cannot get there goes to backups/ (exit 1) or stays in its job folder, never lost, with no folder left behind; run as root on a data directory owned by another user it drops its groups, takes the owner's group then user, and stops with a message if it cannot; backups/ that is a link or a file, and OS errors before the run, are messages with exit 1; no subcommand exits 1; inspect exits 0 on an intact archive (--no-verify compares the entry names without reading them) and 1 on a missing file, a file that is not a zip, a zip without manifest, an altered, added or damaged entry; create exits 1 without data directory or database, writing nothing; python scripts/backup_cli.py create then inspect exit 0; restore of a missing file, with or without --dry-run, exits 1 creating nothing, restore --dry-run exits 0 on a restorable archive (report printed, administrators named, the copy removed) and 1 with the StagingError code on a refused one, without an active administrator, while another check runs, or when .restore is a link; the script runs restore --dry-run end to end",
        # Data directories under tmp_path seen through monkeypatched LIBREFOLIO_* variables (production mode, checked
        # before each command), children with the same data directory and without LIBREFOLIO_*/COVERAGE_*, identity
        # calls replaced: no lane DB, no server, no network, no writes outside tmp_path.
        isolation="pure",
    )
    add_test(
        cat,
        "backup-cli-secure",
        utils_backup_cli_secure,
        name="Backup CLI Secure Backup",
        desc="scripts/backup_cli.py and a secure backup (lot B4): create with --password-file, --password-stdin or --encrypt (password_required without a terminal; the two sources exclusive; no --password option; password_too_weak with the failed rules, nothing written), an .lfbk the password opens; inspect and restore --dry-run of an envelope (wrong_password, password_required, a zip ignoring the source); decrypt to a new 0600 zip (an existing output refused untouched, not_an_envelope); the password never printed; no decrypted zip left in the data directory; B-38: a --password-file or --instance-key-file that is not a regular file (a FIFO, a folder) refused at once, as root and not (not a regular file, password_unreadable / instance_key_unreadable; a FIFO never waited on); as root, one that goes through a link inside the data directory (the file, or backups/ itself) refused with its target never opened; read as today: a plain file, a Kubernetes secret link outside the data directory, a link inside it when not root",
        # Data directories under tmp_path seen through monkeypatched LIBREFOLIO_* variables, as test_backup_cli.py
        # sets them: no lane DB, no server, no network, no writes outside tmp_path.
        isolation="pure",
    )
    add_test(
        cat,
        "backup-cli-sealed",
        utils_backup_cli_sealed,
        name="Backup CLI Sealed Backup",
        desc="scripts/backup_cli.py and the sealed nightly backup (lot L3-2): keygen (an age identity 0600, an existing file refused, the recipient printed, never the private key); create --recipient (one or two, three refused) and --sealed (LIBREFOLIO_BACKUP_RECIPIENTS, unset refused), exclusive with a password; inspect, decrypt and restore --dry-run of a sealed .tar with --identity-file (the L3 vectors: the good zip, the rotation; sealed_no_identity, wrong_password, sealed_tar_invalid, sealed_manifest_invalid, envelope_damaged; sealed_backup_needs_key without the identity; --identity-file on a zip refused); no temporary .lfbk left",
        # Data directories under tmp_path seen through monkeypatched LIBREFOLIO_* variables, as test_backup_cli.py
        # sets them; the L3 vectors copied into tmp_path: no lane DB, no server, no network, no writes outside tmp_path.
        isolation="pure",
    )
    add_test(
        cat,
        "backup-cli-recover",
        utils_backup_cli_recover,
        name="Backup CLI Recover",
        desc="scripts/backup_cli.py (lot B5-2): pending --json (exactly one line on stdout for none, pending, in_progress, committed, rolled_back and unreadable io/not_a_file/invalid; keys, choices, waiting, backup_created_at in UTC with Z, safety_copy from .restore/previous/; no username, path or stage id; no log line on stdout; exit 5 for a missing data directory; usage errors exit 2); pending --recover previous|cancel (exit 0 done, 3 nothing to recover, 4 choice not valid, 5 failed; idempotent; with and without --json; --json adds recover and error)",
        # Data directories under tmp_path seen through monkeypatched LIBREFOLIO_* variables, as test_backup_cli_restore.py
        # sets them; a few cases run the script in a process of its own: no lane DB, no server, no network.
        isolation="pure",
    )
    add_test(
        cat,
        "backup-cli-restore",
        utils_backup_cli_restore,
        name="Backup CLI Restore",
        desc="scripts/backup_cli.py restore ARCHIVE without --dry-run: the check and its report, then the confirmation (--yes; the word restore typed on a terminal, spaces ignored, case kept; a pipe refused naming --yes; anything else declined, Nothing restored) → exit 0, the restore pending for the next start (.restore/restore.json 0600, confirmed_by cli), the copy kept, the live data untouched; exit 1 with the copy removed when declined, blocked (no administrator) or refused by the confirmation (its code in parentheses); an active restore stops the command before its check (restore_already_pending), --dry-run unchanged meanwhile; pending (none, each phase, waiting and reason codes in parentheses) and pending --cancel (the restore and its copy dropped; restore_not_pending with exit 1, nothing created); the script end to end; B-32: a state the file system cannot read (an open refused here, EACCES or EIO; for the script a state of mode 000, or a .restore it cannot search) → ❌ The state of the restore cannot be read: <reason> (restore_state_unreadable), exit 1, never «no restore», from pending, pending --cancel (the restore and its copy kept) and restore --yes (nothing checked; --dry-run unchanged); a cancel refused before the drop (the state's removal refused, a read-only .restore) → (restore_cancel_failed), exit 1, the restore kept; a drop whose copy stays (its removal raising, or leaving it) → ✅ … dropped without «with its copy», then ⚠️ its copy stays, exit 0; the usual drop keeps «with its copy»; B-18: restore --instance-key-file FILE gives the old instance key (a clear archive whose saved provider keys K1 encrypted, the instance on K2): --dry-run exit 0 with «Instance key: not included; given with --instance-key-file» and the re-encrypted count, nothing unreadable, the copy removed; --yes confirmed with the copy under K2, pending shows it; a file missing, blank or unreadable → (instance_key_unreadable), exit 1, no copy, the password never asked; a key under 32 characters → (instance_key_invalid), no copy; D1 an archive carrying its own key uses it (ℹ️ the file not used); D2 a wrong key → ⚠️ it reads none, before the unreadable line, or ⚠️ this instance's own key cannot be used (its problem) instead; as root (fake identity) the file read before the switch; no key text on stdout or stderr; B-35: restore honours LIBREFOLIO_BACKUP_MAX_RESTORE_MB (the total a check unpacks, MB of 1024², 0 no limit): over it → exactly one ❌ (unpacked_too_large), exit 1, after the 🔎 line, no copy; unreadable (abc; managed with the upload limit's profile entry of the wrong type) → one ❌ naming the variable (backup_restore_unavailable), exit 1, before the 🔎 line, no copy; 0 lifts the profile's limit for one command (after the barrier that unset refuses); managed, unset, upload 1 MB → a limit of 8 MB, over refused, under checked; B-34: with no instance key yet and none creatable (secrets/ 0500, skipped as root), K1 given → ⚠️ this instance's own key cannot be used: <secrets/instance.key>: there is no instance key yet, and it could not be created, right before the unreadable line, never the line that blames the key given; B-43: restore --dry-run of an archive whose index calls a function this LibreFolio lacks → exactly one ❌ (database_damaged) after the 🔎 line, exit 1, no traceback, no copy left, the function's name on neither output",
        # Data directories under tmp_path seen through monkeypatched LIBREFOLIO_* variables (production mode, checked),
        # a database at the head made once by alembic in its own process, a pty or a pipe for stdin; restart.send_signal
        # and os.kill as restart sees them record and must stay unused: no lane DB, no server, no network, no writes
        # outside tmp_path.
        isolation="pure",
    )
    add_test(cat, "all", utils_all, test_names=False, name="All Utils Tests", desc="Run all utility tests")
    registry["utils"] = cat
