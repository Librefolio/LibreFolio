"""
Test Suite: the order of day and month in the generic CSV plugin, ``date_order`` (CP12, W5-8)

The first real field of a BRIM plugin (the contract: ``backend/brim/architecture.md``, «A field in a BRIM plugin», and
``test_services/test_brim_field_contract.py``). ``broker_generic_csv`` reads ``03/01/2025`` as 3 January by default; a user
whose bank writes the month first chooses ``month_first`` and reads it as 1 March.

What is pinned:

- A. PARITY, green before and after: the default is today's behaviour BIT FOR BIT. ``parse_date(value)`` and
  ``parse_date(value, "day_first")`` equal a frozen copy, kept in this file, of the format list as it was before the field; and
  parsing the generic sample reports with no settings delivered gives the very transactions parsed with ``day_first`` bound.
  Only the ``order`` argument (the second assertion of the first test) and the bound ``day_first`` are new: the rest is green
  today.
- B. ``month_first``: for the slash, the dash and the dot the month is tried first and the day order is the fallback; ISO, compact
  and text dates do not move; an unknown order reads as ``day_first``. And through the plugin: a file read with ``month_first``
  bound gives the month-first dates, with ``day_first`` the day-first ones, the same rows otherwise.
- C. The plugin declares the field: key, scope, default, type and options, and the declaration passes the rules of the ``brim``
  family.

The bound values are built the way the core builds them (``build_bound_settings``) with a field copied from the contract: the
declaration of the plugin itself is pinned by C alone, so a missing declaration does not hide in the other tests.

PURE: untouched samples and files of ``tmp_path``, no server, no database, no network, no clock.
"""

from __future__ import annotations

import json
from datetime import UTC, date, datetime
from pathlib import Path

import pytest

from backend.app.config import PROJECT_ROOT
from backend.app.services.brim.registry import BRIMProviderRegistry
from backend.app.services.brim_providers.broker_generic_csv.plugin import parse_date
from backend.app.services.plugin_settings.contract import BoundSettings
from backend.app.services.plugin_settings.fields import FAMILY_RULES, PluginSettingField, SettingOption, SettingScope, SettingType, validate_declaration
from backend.app.services.plugin_settings.resolver import StoredValue, build_bound_settings

CODE = "broker_generic_csv"
SAMPLE_DIR = PROJECT_ROOT / "backend" / "app" / "services" / "brim_providers" / "sample_reports"
BROKER_ID = 1

#: The field of the contract, as the plugin must declare it (C pins the plugin's own declaration).
DATE_ORDER = PluginSettingField(
    key="date_order",
    type=SettingType.SELECT,
    scope=SettingScope.USER,
    label="Order of day and month",
    default="day_first",
    options=(SettingOption("day_first", "Day first"), SettingOption("month_first", "Month first")),
)

#: The formats the plugin tried, in this order, BEFORE the field existed (frozen: it never follows the plugin).
FROZEN_DATE_FORMATS = [
    "%Y-%m-%d",
    "%d/%m/%Y",
    "%m/%d/%Y",
    "%d-%m-%Y",
    "%Y/%m/%d",
    "%d.%m.%Y",
    "%Y%m%d",
    "%d %b %Y",
    "%d %B %Y",
]

#: Every shape the corpus knows: ISO, the ambiguous and the unambiguous day/month, the three separators, compact, text, junk.
CORPUS = [
    "2025-01-03",
    "03/01/2025",
    "25/12/2025",
    "12/25/2025",
    "31/12/2025",
    "03-01-2025",
    "25-12-2025",
    "03.01.2025",
    "25.12.2025",
    "20250103",
    "03 Jan 2025",
    "03 January 2025",
    "",
    "   ",
    "  03/01/2025  ",
    "not a date",
    "2025-13-45",
    "2025/01/03",
]


def _reference_parse_date(value: str) -> date | None:
    """``parse_date`` as it was before the field: strip, empty is None, the first format that matches wins."""
    value = value.strip()
    if not value:
        return None
    for fmt in FROZEN_DATE_FORMATS:
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    return None


def _stored(value: str) -> StoredValue:
    return StoredValue(value_json=json.dumps(value), secret_ciphertext=None, key_id=None, updated_at=datetime.now(UTC))


def _bound(order: str | None) -> BoundSettings:
    """What the core binds for a user who saved ``order`` (None: saved nothing)."""
    rows = {"date_order": _stored(order)} if order is not None else {}
    return build_bound_settings("brim", CODE, (DATE_ORDER,), {}, rows, user_id=7)


def _plugin(order: str | None = None, *, bind: bool = True):
    """The registered generic CSV plugin; with ``bind=False`` the core delivers no settings (detection, report sets, gap fix)."""
    BRIMProviderRegistry.auto_discover()
    plugin = BRIMProviderRegistry.get_provider_instance(CODE)
    assert plugin is not None, f"no BRIM plugin is registered as {CODE}"
    if bind:
        plugin.bind_settings(_bound(order))
    return plugin


def _write_csv(tmp_path: Path, lines: list[str], name: str = "dates.csv") -> Path:
    path = tmp_path / name
    path.write_text("date,type,quantity,amount,currency,asset,description\n" + "\n".join(lines) + "\n", encoding="utf-8")
    return path


def _by_description(output) -> dict[str, object]:
    """The transactions of a parse by the description this test wrote (unique per row): never by position."""
    return {tx.description: tx for tx in output.transactions}


# =============================================================================
# A. PARITY: THE DEFAULT IS TODAY'S BEHAVIOUR, BIT FOR BIT
# =============================================================================


@pytest.mark.parametrize("value", CORPUS, ids=[repr(v) for v in CORPUS])
def test_parse_date_without_an_order_is_what_it_always_was(value: str):
    """Green today and after: no ``order`` given, the answer is the frozen reference's."""
    assert parse_date(value) == _reference_parse_date(value)


@pytest.mark.parametrize("value", CORPUS, ids=[repr(v) for v in CORPUS])
def test_parse_date_day_first_is_what_it_always_was(value: str):
    """Red until ``parse_date`` takes the ``order``: ``day_first`` is exactly the frozen reference."""
    assert parse_date(value, "day_first") == _reference_parse_date(value)


def test_the_frozen_reference_reads_the_ambiguous_dates_day_first():
    """Guard of the guard: the reference is what the contract says (3 January, 25 December), so a parity that holds means it."""
    assert _reference_parse_date("03/01/2025") == date(2025, 1, 3)
    assert _reference_parse_date("12/25/2025") == date(2025, 12, 25)
    assert _reference_parse_date("not a date") is None


GENERIC_SAMPLES = sorted(path.name for path in SAMPLE_DIR.glob("generic_*.csv"))


def test_the_generic_samples_are_found():
    """Barrier: the parity below runs over real samples, and the one with the ambiguous dates is among them."""
    assert "generic_dates.csv" in GENERIC_SAMPLES and len(GENERIC_SAMPLES) >= 2, GENERIC_SAMPLES


@pytest.mark.parametrize("sample", GENERIC_SAMPLES)
def test_a_sample_parsed_with_no_settings_equals_the_same_sample_with_day_first_bound(sample: str):
    """The core delivers no settings for a user who chose nothing (and the plugin sees the declared default): the transactions
    (type, date, quantity, cash, asset ids...) are those of ``day_first`` bound explicitly. Green today: the plugin ignores
    the value, and the day-first reading is the only one it has."""
    path = SAMPLE_DIR / sample
    unbound = _plugin(bind=False).parse(path, BROKER_ID)
    bound = _plugin("day_first").parse(path, BROKER_ID)

    assert [tx.model_dump(mode="json") for tx in unbound.transactions] == [tx.model_dump(mode="json") for tx in bound.transactions]
    assert unbound.warnings == bound.warnings
    assert len(unbound.transactions) > 0, "barrier: the sample gave rows, so the equality above compares something"


def test_the_dates_sample_is_read_day_first_by_default():
    """Golden, green today: ``generic_dates.csv`` read with no settings. ``03/01/2025`` is 3 January, ``01/04/2025`` is 1 April
    (the sample's «US» label notwithstanding: the day-first format matches first), the dotted date is 5 January."""
    output = _plugin(bind=False).parse(SAMPLE_DIR / "generic_dates.csv", BROKER_ID)
    dates = _by_description(output)

    assert dates["European DD/MM/YYYY format"].date == date(2025, 1, 3)
    assert dates["US MM/DD/YYYY format"].date == date(2025, 4, 1)
    assert dates["German DD.MM.YYYY format"].date == date(2025, 1, 5)
    assert dates["ISO date format"].date == date(2025, 1, 2)


# =============================================================================
# B. month_first
# =============================================================================

#: (value, day_first, month_first): the separators that mirror, and the dates that cannot move. ``None`` under ``day_first`` is
#: today's behaviour (a dash or dot date with the month first was never read), kept bit for bit.
ORDER_CASES = [
    ("03/01/2025", date(2025, 1, 3), date(2025, 3, 1)),
    ("25/12/2025", date(2025, 12, 25), date(2025, 12, 25)),
    ("12/25/2025", date(2025, 12, 25), date(2025, 12, 25)),
    ("03-01-2025", date(2025, 1, 3), date(2025, 3, 1)),
    ("25-12-2025", date(2025, 12, 25), date(2025, 12, 25)),
    ("12-25-2025", None, date(2025, 12, 25)),
    ("03.01.2025", date(2025, 1, 3), date(2025, 3, 1)),
    ("25.12.2025", date(2025, 12, 25), date(2025, 12, 25)),
    ("12.25.2025", None, date(2025, 12, 25)),
    ("2025-01-03", date(2025, 1, 3), date(2025, 1, 3)),
    ("2025/01/03", date(2025, 1, 3), date(2025, 1, 3)),
    ("20250103", date(2025, 1, 3), date(2025, 1, 3)),
    ("03 Jan 2025", date(2025, 1, 3), date(2025, 1, 3)),
    ("03 January 2025", date(2025, 1, 3), date(2025, 1, 3)),
]


@pytest.mark.parametrize(("value", "day_first", "month_first"), ORDER_CASES, ids=[case[0] for case in ORDER_CASES])
def test_the_order_decides_an_ambiguous_date_and_nothing_else(value: str, day_first: date | None, month_first: date):
    """The mirror: slash, dash and dot try the month first under ``month_first``; whatever has one reading has it in both."""
    assert parse_date(value, "day_first") == day_first
    assert parse_date(value, "month_first") == month_first


@pytest.mark.parametrize("value", ["", "   ", "not a date", "2025-13-45", "32/13/2025", "13/13/2025"])
def test_what_is_not_a_date_is_none_in_both_orders(value: str):
    assert parse_date(value, "day_first") is None
    assert parse_date(value, "month_first") is None


@pytest.mark.parametrize("unknown", ["", "auto", "MONTH_FIRST", "month-first", "whatever"])
def test_an_unknown_order_reads_as_day_first(unknown: str):
    """No ``auto`` value exists: a string the plugin does not know is the default, never an error."""
    assert parse_date("03/01/2025", unknown) == date(2025, 1, 3)
    assert parse_date("12/25/2025", unknown) == date(2025, 12, 25)


def test_a_file_is_read_with_the_order_bound(tmp_path: Path):
    """03/01/2025 and 25/12/2025 through the plugin: month first gives 1 March and 25 December, day first 3 January and 25 December;
    the rows are the same otherwise (type, quantity, cash, asset)."""
    path = _write_csv(
        tmp_path,
        ["03/01/2025,BUY,5,-500.00,EUR,MSFT,ambiguous", "25/12/2025,BUY,2,-200.00,EUR,AAPL,unambiguous", "2025-02-03,DEPOSIT,0,1000.00,EUR,,iso"],
    )

    day = _by_description(_plugin("day_first").parse(path, BROKER_ID))
    month = _by_description(_plugin("month_first").parse(path, BROKER_ID))
    default = _by_description(_plugin(bind=False).parse(path, BROKER_ID))

    assert set(day) == set(month) == set(default) == {"ambiguous", "unambiguous", "iso"}
    assert (day["ambiguous"].date, month["ambiguous"].date, default["ambiguous"].date) == (date(2025, 1, 3), date(2025, 3, 1), date(2025, 1, 3))
    assert (day["unambiguous"].date, month["unambiguous"].date) == (date(2025, 12, 25), date(2025, 12, 25))
    assert (day["iso"].date, month["iso"].date) == (date(2025, 2, 3), date(2025, 2, 3))
    for description in day:
        without_date = lambda tx: {key: value for key, value in tx.model_dump(mode="json").items() if key != "date"}  # noqa: E731
        assert without_date(day[description]) == without_date(month[description]), f"only the date of '{description}' may depend on the order"


def test_the_dates_sample_follows_the_order(tmp_path: Path):
    """``generic_dates.csv`` with ``month_first``: 03/01 is 1 March, 01/04 is 4 January, 05.01 is 1 May; ISO rows stay."""
    dates = _by_description(_plugin("month_first").parse(SAMPLE_DIR / "generic_dates.csv", BROKER_ID))

    assert dates["European DD/MM/YYYY format"].date == date(2025, 3, 1)
    assert dates["US MM/DD/YYYY format"].date == date(2025, 1, 4)
    assert dates["German DD.MM.YYYY format"].date == date(2025, 5, 1)
    assert dates["ISO date format"].date == date(2025, 1, 2)


# =============================================================================
# C. THE PLUGIN DECLARES THE FIELD
# =============================================================================


def test_the_plugin_declares_date_order_as_the_contract_says():
    """Registered ``settings_fields``: key ``date_order``, personal scope, a select, default ``day_first``, the two options."""
    BRIMProviderRegistry.auto_discover()
    plugin_class = BRIMProviderRegistry.get_plugin(CODE)
    assert plugin_class is not None, f"no BRIM plugin is registered as {CODE}"
    declared = {field.key: field for field in plugin_class.settings_fields}

    assert "date_order" in declared, f"{CODE} declares {sorted(declared) or 'no field'}"
    field = declared["date_order"]
    assert field.type is SettingType.SELECT
    assert field.scope is SettingScope.USER
    assert field.default == "day_first"
    assert field.secret is False
    assert [option.value for option in field.options] == ["day_first", "month_first"]


def test_the_declaration_passes_the_rules_of_the_brim_family():
    """The very check the registry applies when a plugin registers (``validate_declaration`` with the ``brim`` rules)."""
    BRIMProviderRegistry.auto_discover()
    plugin_class = BRIMProviderRegistry.get_plugin(CODE)
    assert plugin_class is not None
    assert BRIMProviderRegistry.settings_family() == "brim" and "brim" in FAMILY_RULES
    assert plugin_class.settings_fields, f"{CODE} declares no field"

    validate_declaration(plugin_class.settings_fields, family="brim")


def test_the_default_of_the_declaration_is_what_a_user_who_chose_nothing_gets():
    """A plugin the core did not configure (detection, report sets, gap fix) reads the declared default: ``day_first``."""
    plugin = _plugin(bind=False)

    assert plugin.settings.get("date_order") == "day_first"
