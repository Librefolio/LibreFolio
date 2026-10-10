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
    print_info("Testing: backend/app/utils/decimal_utils.py")
    print_info("Tests: Model precision extraction, Truncation, Edge cases")
    cmd = _build_pytest_cmd("backend/test_scripts/test_utilities/test_decimal_utils.py", test_names)
    return run_command(cmd, "Decimal precision tests", verbose=verbose)


def utils_datetime(verbose: bool = False, test_names: list = None) -> bool:
    """Test datetime utilities."""
    print_section("Utils: Datetime")
    print_info("Testing: backend/app/utils/datetime_utils.py")
    print_info("Tests: Timezone-aware datetime helpers")
    cmd = _build_pytest_cmd("backend/test_scripts/test_utilities/test_datetime_utils.py", test_names)
    return run_command(cmd, "Datetime utils tests", verbose=verbose)


def utils_day_count(verbose: bool = False, test_names: list = None) -> bool:
    """Test day count conventions."""
    print_section("Utils: Day Count Conventions")
    print_info("Testing: backend/app/services/asset_source_providers/scheduled_investment.py (day count functions)")
    print_info("Tests: ACT/365, ACT/360, ACT/ACT, 30/360 conventions")
    cmd = _build_pytest_cmd("backend/test_scripts/test_utilities/test_day_count_conventions.py", test_names)
    return run_command(cmd, "Day count convention tests", verbose=verbose)


def utils_geo_utils(verbose: bool = False, test_names: list = None) -> bool:
    """Test geographic area normalization utilities."""
    print_section("Utils: Geographic Area Normalization")
    print_info("Testing: backend/app/utils/geo_utils.py")
    print_info("Tests: ISO-3166-A3 normalization, weight parsing, validation pipeline")
    cmd = _build_pytest_cmd("backend/test_scripts/test_utilities/test_geo_utils.py", test_names)
    return run_command(cmd, "Geographic area normalization tests", verbose=verbose)


def utils_version(verbose: bool = False, test_names: list = None) -> bool:
    """Test version utilities."""
    print_section("Utils: Version")
    print_info("Testing: backend/app/utils/version.py")
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
    print_info("Testing: backend/app/utils/sector_fin_utils.py")
    print_info("Tests: FinancialSector enum, aliases, normalization, validation")
    cmd = _build_pytest_cmd("backend/test_scripts/test_utilities/test_sector_normalization.py", test_names)
    return run_command(cmd, "Sector normalization tests", verbose=verbose)


def utils_currency_utils(verbose: bool = False, test_names: list = None) -> bool:
    """Test currency listing, flag mapping, and validation."""
    print_section("Utils: Currency Utils")
    print_info("Testing: backend/app/utils/currency_utils.py")
    print_info("Tests: list_currencies (pycountry), flag_emoji mapping, validation consistency")
    cmd = _build_pytest_cmd("backend/test_scripts/test_utilities/test_currency_utils.py", test_names)
    return run_command(cmd, "Currency utils tests", verbose=verbose)


def utils_cache_utils(verbose: bool = False, test_names: list = None) -> bool:
    """Test NamedCache wrapper, TTL expiration, and global cache registry."""
    print_section("Utils: Cache Utils")
    print_info("Testing: backend/app/utils/cache_utils.py")
    print_info("Tests: NamedCache set/get/delete/clear, TTL, registry, stats")
    cmd = _build_pytest_cmd("backend/test_scripts/test_utilities/test_cache_utils.py", test_names)
    return run_command(cmd, "Cache utils tests", verbose=verbose)


def utils_provider_core_cache(verbose: bool = False, test_names: list = None) -> bool:
    """Test provider core cache & thread isolation infrastructure."""
    print_section("Utils: Provider Core Cache & Thread Isolation")
    print_info("Testing: backend/app/services/asset_source.py (core cache + _run_provider_in_thread)")
    print_info("Tests: Thread isolation, timeout, caches (history/current/metadata/search), probe bypass")
    cmd = _build_pytest_cmd("backend/test_scripts/test_utilities/test_provider_core_cache.py", test_names)
    return run_command(cmd, "Provider core cache tests", verbose=verbose)


def utils_roi_utils(verbose: bool = False, test_names: list = None) -> bool:
    """Test pure ROI helper functions (annualized_to_cumulative, calculate_mwrr*)."""
    print_section("Utils: ROI Helpers")
    print_info("Testing: backend/app/utils/financial/roi_utils.py")
    cmd = _build_pytest_cmd("backend/test_scripts/test_utilities/test_roi_utils.py", test_names)
    return run_command(cmd, "ROI helper tests", verbose=verbose)


def utils_translation_utils(verbose: bool = False, test_names: list = None) -> bool:
    """Test translation/locale helper (get_babel_locale + English fallback)."""
    print_section("Utils: Translation Helpers")
    print_info("Testing: backend/app/utils/translation_utils.py")
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
    """Test the cross-boundary docs link gate (const resolution, plugin discovery, three verdicts)."""
    print_section("Utils: Docs Link Gate")
    print_info("Testing: scripts/docs_links.py")
    print_info("Tests: const resolution vs deletion, plugin/provider glob, unverifiable bucket")
    cmd = _build_pytest_cmd("backend/test_scripts/test_utilities/test_docs_links_gate.py", test_names)
    return run_command(cmd, "Docs link discovery tests", verbose=verbose)


def utils_pwa_assets(verbose: bool = False, test_names: list = None) -> bool:
    """Test the committed PWA icons, manifest, apple-touch link and service-worker stamp."""
    print_section("Utils: PWA Assets")
    print_info("Testing: frontend/static/{icons/,manifest.json,sw.js,offline.html}, frontend/src/app.html")
    print_info("Tests: opaque RGB icons, maskable safe zone on splash beige, 180px apple-touch icon, sw.js stamp = md5(offline.html)[:8]")
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
    print_info("Tests: help and user commands run, unavailable groups say so and exit 2, password reset on a temporary DB")
    cmd = _build_pytest_cmd("backend/test_scripts/test_utilities/test_dev_cli_image.py", test_names)
    return run_command(cmd, "dev.py image tests", verbose=verbose)


def utils_gate_i18n_usage(verbose: bool = False, test_names: list = None) -> bool:
    """Test the i18n three-verdict classifier (used / not verified / dead)."""
    print_section("Utils: i18n Usage Gate")
    print_info("Testing: scripts/i18n_usage.py")
    print_info("Tests: typed-union expansion, producer vocabulary, ternary arguments, bare-root suppression")
    cmd = _build_pytest_cmd("backend/test_scripts/test_utilities/test_i18n_usage_gate.py", test_names)
    return run_command(cmd, "i18n three-verdict classifier tests", verbose=verbose)


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
    """Test that dev.py's check_port_in_use names who holds a TCP port on Linux (fuser) as it does on macOS (lsof)."""
    print_section("Utils: dev.py port check")
    print_info("Testing: dev.py check_port_in_use, the port check of server and mkdocs gallery (the list --force kills)")
    print_info("Tests: Linux fuser branch through the real subprocess.run argument check, host lsof/fuser on a 127.0.0.1 listener and on a released port, no capture_output with stdout=/stderr= in dev.py")
    cmd = _build_pytest_cmd("backend/test_scripts/test_utilities/test_dev_port_check.py", test_names)
    return run_command(cmd, "dev.py port check tests", verbose=verbose)


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
    add_test(cat, "datetime", utils_datetime, name="Datetime Utils", desc="Timezone-aware datetime helpers")
    add_test(cat, "day-count", utils_day_count, name="Day Count Conventions", desc="ACT/365, ACT/360, ACT/ACT, 30/360")
    add_test(cat, "geo-utils", utils_geo_utils, name="Geographic Utils", desc="ISO-3166-A3 normalization, weights")
    add_test(cat, "version", utils_version, name="Version Utils", desc="get_git_version, get_version_info")
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
        "container-registry",
        utils_container_registry,
        name="Container Registry",
        desc="Trusted GHCR challenge/token flow, result mapping, endpoint guards, secret redaction",
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
        desc="dev.py on a copy of the image's /app file set (no backend/test_scripts): help, user and db run; test, i18n and mkdocs translate answer «not available in this installation» and exit 2; user create/reset/list on a temporary DB; the Dockerfile HEALTHCHECK probes the port the CMD binds, like compose",
        # A copy of the image tree and a temporary DB under tmp_path, dev.py in
        # subprocesses: no lane DB, no server, no network, no repo writes.
        isolation="pure",
    )
    add_test(
        cat,
        "js-cache-fail-loud",
        utils_js_cache_fail_loud,
        name="JS Cache Fail-Loud (I1)",
        desc="update_js_cache: undownloadable+uncached resource or partial font subsets → hard failure → exit 1; cached copy → exit 0; consumer-scoped narrowing (a docs-only asset does not fail a frontend build, an unknown attribution still does)",
        # tmp_path + monkeypatched network only: no DB, no server, no repo writes.
        isolation="pure",
    )
    add_test(
        cat,
        "gate-docs-links",
        utils_gate_docs_links,
        name="Docs Link Gate",
        desc="Cross-boundary link discovery: a resolved const confirms a link but an unresolved interpolation may never condemn one, plugin/provider folders are found by glob rather than by a hand-written list, and what cannot be decided is reported as unverifiable instead of dropped",
        isolation="pure",
    )
    add_test(
        cat,
        "pwa-assets",
        utils_pwa_assets,
        name="PWA Assets",
        desc="Opaque RGB icons at exact sizes (any, maskable, apple-touch 180), maskable logo inside the 0.40 safe zone on the splash beige, one manifest entry per purpose and size with no file serving both, app.html apple-touch link at 180x180, sw.js build stamp = md5(offline.html)[:8]",
        # Reads committed files under frontend/static/ and frontend/src/app.html only:
        # no DB, no server, no network, no writes.
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
        desc="dev.py db current/upgrade/downgrade/migrate/check act on the [path] they are given (absolute, or relative to the project root), never on the configured database: a missing file is refused (upgrade creates it), a path with %, ? or # is refused, db check runs the CHECK constraints hook; without a path the configured database is used",
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
        desc="dev.py check_port_in_use names who holds a TCP port on Linux as on macOS: the fuser call passes Python's own subprocess.run argument check and its PIDs come back with their process names; on the host, lsof (macOS) or fuser (Linux) report this process while it listens on 127.0.0.1 and no longer once it has closed the socket; no call in dev.py passes capture_output together with stdout= or stderr=",
        # platform.system and subprocess.run monkeypatched for the Linux case, a 127.0.0.1
        # socket on a port the OS picks, read-only lsof/fuser/ps children, dev.py parsed:
        # no DB, no server, no network beyond loopback, no writes.
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
    add_test(cat, "all", utils_all, test_names=False, name="All Utils Tests", desc="Run all utility tests")
    registry["utils"] = cat
