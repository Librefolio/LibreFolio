"""
Backend schema validation tests: computed fields, common, assets, transactions, brokers.
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


def schemas_computed_fields(verbose: bool = False, test_names: list = None) -> bool:
    """Test computed properties across all schemas."""
    print_section("Schemas: Computed Fields")
    print_info("Testing: computed properties at 0% across brokers, common, fx, prices, transactions schemas")

    cmd = _build_pytest_cmd("backend/test_scripts/test_schemas/test_schema_computed_fields.py", test_names)
    return run_command(cmd, "Schema computed fields tests", verbose=verbose)


def schemas_common(verbose: bool = False, test_names: list = None) -> bool:
    """Test common Pydantic schemas."""
    print_section("Schemas: Common (Currency, DateRangeModel, OldNew)")
    print_info("Testing: backend/app/schemas/common.py")

    cmd = _build_pytest_cmd("backend/test_scripts/test_schemas/test_common_schemas.py", test_names)
    return run_command(cmd, "Common schemas tests", verbose=verbose)


def schemas_assets(verbose: bool = False, test_names: list = None) -> bool:
    """Test asset-related Pydantic schemas."""
    print_section("Schemas: Assets (FAGeographicArea, FAInterestRatePeriod, etc.)")
    print_info("Testing: backend/app/schemas/assets.py")

    cmd = _build_pytest_cmd("backend/test_scripts/test_schemas/test_asset_schemas.py", test_names)
    return run_command(cmd, "Asset schemas tests", verbose=verbose)


def schemas_transactions(verbose: bool = False, test_names: list = None) -> bool:
    """Test transaction Pydantic schemas."""
    print_section("Schemas: Transactions (TXCreateItem, TXReadItem, etc.)")
    print_info("Testing: backend/app/schemas/transactions.py")

    cmd = _build_pytest_cmd("backend/test_scripts/test_schemas/test_transaction_schemas.py", test_names)

    return run_command(cmd, "Transaction schemas tests", verbose=verbose)


def schemas_brokers(verbose: bool = False, test_names: list = None) -> bool:
    """Test broker Pydantic schemas."""
    print_section("Schemas: Brokers (BRCreateItem, BRReadItem, etc.)")
    print_info("Testing: backend/app/schemas/brokers.py")

    cmd = _build_pytest_cmd("backend/test_scripts/test_schemas/test_broker_schemas.py", test_names)

    return run_command(cmd, "Broker schemas tests", verbose=verbose)


def schemas_all(verbose: bool = False) -> bool:
    """Run all schema validation tests."""
    return _run_test_suite(
        suite_name="Schema Validation Tests",
        tests=_get_category_tests_for_all("schemas", verbose),
        verbose=verbose,
        info_msgs=["Testing Pydantic schema validation rules"],
        summary_title="Schema Tests Summary",
        success_msg="All schema tests passed! 🎉",
            resume=_common._RESUME_MODE,
        )


def populate_registry(registry: dict) -> None:
    """Register all schema test entries."""
    cat = make_category(
        help_text="Pydantic schema validation tests (computed fields, assets, transactions, brokers)",
        description="""
Schema Validation Tests

Tests for Pydantic/SQLModel schema validation:
  • Computed fields, Common schemas, Asset schemas
  • Transaction schemas, Broker schemas
""")
    add_test(cat, "computed-fields", schemas_computed_fields, name="Computed Fields", desc="Computed properties across all schemas")
    add_test(cat, "common", schemas_common, name="Common Schemas", desc="Currency, DateRangeModel, OldNew")
    add_test(cat, "assets", schemas_assets, name="Asset Schemas", desc="FAGeographicArea, FAInterestRatePeriod")
    add_test(cat, "transactions", schemas_transactions, name="Transaction Schemas", desc="TXCreateItem, TXReadItem")
    add_test(cat, "brokers", schemas_brokers, name="Broker Schemas", desc="BRCreateItem, BRReadItem")
    add_test(cat, "all", schemas_all, test_names=False, name="All Schema Tests", desc="Run all schema tests")
    registry["schemas"] = cat

