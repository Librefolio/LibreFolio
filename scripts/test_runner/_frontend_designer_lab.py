"""Frontend Designer Lab tests: the debug-only colour lab (Vitest units and E2E).

The Lab exists only in debug builds. The test server always runs one (``dev.py server --test``
forces debug mode), so every E2E run serves ``/designer-lab`` and loads the Lab client, idle,
on every app page. The E2E specs cover the live engines between two tabs, the element picker,
and the neutrality of the idle client: E2E and gallery runs must stay identical while the Lab
is unused.
"""

import subprocess

from . import _common
from ._common import PROJECT_ROOT, Colors, _get_category_tests_for_all, _run_test_suite, add_test, make_category, print_error, print_section, print_success
from ._frontend_common import _ensure_db_populated, _ensure_frontend_build, _ensure_test_users, _run_playwright, reset_setup_scope

DESIGNER_LAB_UNIT_TEST_PATHS = (
    "src/lib/dev/designer-lab/color.test.ts",
    "src/lib/dev/designer-lab/scanColors.test.ts",
    "src/lib/dev/designer-lab/vitePlugin.test.ts",
    "src/lib/dev/designer-lab/store.test.ts",
    "src/lib/dev/designer-lab/pick.test.ts",
    "src/lib/dev/designer-lab/exportFormat.test.ts",
    "src/lib/dev/designer-lab/catalogView.test.ts",
    "src/lib/dev/designer-lab/contrast.test.ts",
    "src/lib/dev/designer-lab/chartMapping.test.ts",
    "src/lib/dev/designer-lab/verifyExport.test.ts",
    "src/lib/dev/designer-lab/pickView.test.ts",
    "src/lib/dev/designer-lab/anchor.test.ts",
    "src/lib/dev/designer-lab/elementRules.test.ts",
    "src/lib/dev/designer-lab/designerLabImports.gate.test.ts",
    "src/routes/designer-lab/page.test.ts",
    "src/lib/dev/designer-lab/colorValue.test.ts",
    "src/lib/dev/designer-lab/targets.test.ts",
    "src/lib/dev/designer-lab/colorEditor.test.ts",
    "src/lib/dev/designer-lab/categories.test.ts",
    "src/lib/dev/designer-lab/chartColorsSignal.test.ts",
)

DESIGNER_LAB_E2E_SPECS = (
    "designer-lab/designer-lab-live.spec.ts",
    "designer-lab/designer-lab-picker.spec.ts",
    "designer-lab/designer-lab-neutral.spec.ts",
)


def front_designer_lab_unit(verbose: bool = False, ui: bool = False, headed: bool = False, debug: bool = False, test_names: list = None, coverage: bool = False) -> bool:
    """Run the Designer Lab Vitest files: colour maths, scanner, plugin, state, picker, export, gates."""
    print_section("Frontend Designer Lab Unit Tests (Vitest)")
    cmd = ["npx", "vitest", "run", *DESIGNER_LAB_UNIT_TEST_PATHS]
    print(f"\n{Colors.BLUE}Running: Designer Lab Vitest unit tests{Colors.NC}")
    print(f"Command:\n└─▶ $ cd frontend && {' '.join(cmd)}")
    try:
        result = subprocess.run(cmd, cwd=PROJECT_ROOT / "frontend", text=True)
        if result.returncode == 0:
            print_success("Designer Lab Vitest unit tests - PASSED")
            return True
        print_error(f"Designer Lab Vitest unit tests - FAILED (exit code: {result.returncode})")
        return False
    except Exception as exc:
        print_error(f"Vitest error: {exc}")
        return False


def _run_designer_lab_e2e(specs: str | list[str], section: str, ui: bool = False, headed: bool = False, debug: bool = False, test_names: list = None, coverage: bool = False) -> bool:
    """Run one or more Designer Lab Playwright specs."""
    print_section(section)
    if not _ensure_frontend_build():
        return False
    if not _ensure_db_populated():
        return False
    if not _ensure_test_users():
        return False
    # Desktop only: the Lab is a desktop tool for a designer, two tabs side by side; the specs
    # also skip themselves on any other project.
    return _run_playwright(specs, ui=ui, headed=headed, debug=debug, project="desktop", test_names=test_names, coverage=coverage)


def front_designer_lab_live(verbose: bool = False, ui: bool = False, headed: bool = False, debug: bool = False, test_names: list = None, coverage: bool = False) -> bool:
    """Run the live-engine E2E: L1 variables, L2 stylesheets, L3 charts, suspend, export/import, reset."""
    return _run_designer_lab_e2e(DESIGNER_LAB_E2E_SPECS[0], "Frontend Designer Lab Live Engine Tests", ui=ui, headed=headed, debug=debug, test_names=test_names, coverage=coverage)


def front_designer_lab_picker(verbose: bool = False, ui: bool = False, headed: bool = False, debug: bool = False, test_names: list = None, coverage: bool = False) -> bool:
    """Run the element-picker E2E: veil, Element tab, specialise, anchor export, Esc, Alt+Shift+D, dark override."""
    return _run_designer_lab_e2e(DESIGNER_LAB_E2E_SPECS[1], "Frontend Designer Lab Element Picker Tests", ui=ui, headed=headed, debug=debug, test_names=test_names, coverage=coverage)


def front_designer_lab_neutral(verbose: bool = False, ui: bool = False, headed: bool = False, debug: bool = False, test_names: list = None, coverage: bool = False) -> bool:
    """Run the neutrality E2E: a context that never opened the Lab is left untouched."""
    return _run_designer_lab_e2e(DESIGNER_LAB_E2E_SPECS[2], "Frontend Designer Lab Neutrality Tests", ui=ui, headed=headed, debug=debug, test_names=test_names, coverage=coverage)


def front_designer_lab_e2e(verbose: bool = False, ui: bool = False, headed: bool = False, debug: bool = False, test_names: list = None, coverage: bool = False) -> bool:
    """Run the three Designer Lab E2E specs in one Playwright invocation."""
    return _run_designer_lab_e2e(list(DESIGNER_LAB_E2E_SPECS), "Frontend Designer Lab E2E Tests", ui=ui, headed=headed, debug=debug, test_names=test_names, coverage=coverage)


def front_designer_lab_all(verbose: bool = False, ui: bool = False, headed: bool = False, debug: bool = False, test_names: list = None, coverage: bool = False) -> bool:
    """Run all Designer Lab frontend tests."""
    if _common.nothing_left_to_run("front-designer-lab"):
        return _common.consolidated_verdict("front-designer-lab")
    reset_setup_scope()
    return _run_test_suite(
        suite_name="All Designer Lab Tests (Unit + E2E)",
        tests=_get_category_tests_for_all("front-designer-lab", verbose, ui=ui, headed=headed, debug=debug, test_names=test_names, coverage=coverage),
        verbose=verbose,
        summary_title="Designer Lab Test Summary",
        success_msg="All Designer Lab tests passed! 🎉",
        resume=_common._RESUME_MODE,
    )


def populate_registry(registry: dict) -> None:
    """Register frontend Designer Lab test entries."""
    cat = make_category(
        help_text="Frontend Designer Lab (debug-only colour lab) unit and E2E tests",
        description="""Frontend Designer Lab Tests\n\nThe Lab exists only in debug builds; the test server always serves one.\n\nOptions: --ui, --headed, --debug""",
    )
    add_test(
        cat,
        "unit",
        front_designer_lab_unit,
        test_names=False,
        name="Designer Lab Unit Tests",
        desc="Colour maths, scanner, Vite plugin, state, picker, anchor, export, verify-export and import gates (Vitest)",
        tests="explicit Vitest files",
    )
    add_test(
        cat,
        "live",
        front_designer_lab_live,
        name="Designer Lab Live Engine Tests",
        desc="Catalogue, L1 variables, L2 stylesheets, L3 charts and CVD in another tab; suspend, export/import, reset",
        tests=DESIGNER_LAB_E2E_SPECS[0],
        in_all=False,  # run by "e2e" in a single Playwright invocation
    )
    add_test(
        cat,
        "picker",
        front_designer_lab_picker,
        name="Designer Lab Element Picker Tests",
        desc="Veil, Element tab sources, specialise one component element, anchored export without text, Esc, Alt+Shift+D, dark override",
        tests=DESIGNER_LAB_E2E_SPECS[1],
        in_all=False,  # run by "e2e" in a single Playwright invocation
    )
    add_test(
        cat,
        "neutral",
        front_designer_lab_neutral,
        name="Designer Lab Neutrality Tests",
        desc="A context that never opened the Lab: no shortcut, no veil, no Lab style, idle engines",
        tests=DESIGNER_LAB_E2E_SPECS[2],
        in_all=False,  # run by "e2e" in a single Playwright invocation
    )
    add_test(
        cat,
        "e2e",
        front_designer_lab_e2e,
        name="Designer Lab E2E Tests",
        desc="The live, picker and neutral specs in one Playwright invocation",
        tests=DESIGNER_LAB_E2E_SPECS,
    )
    add_test(cat, "all", front_designer_lab_all, test_names=False, name="All Designer Lab Tests", desc="Run the unit tests, then the three E2E specs")
    registry["front-designer-lab"] = cat
