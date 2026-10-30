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
- D. FB-18, the short-year and year-first orders: ``day_first_short`` (gg/mm/aa), ``month_first_short`` (mm/gg/aa),
  ``year_first_short`` (aa/mm/gg) and ``year_first`` (aaaa-mm-gg) are extra options. The exact, ordered, de-duplicated format list of
  each; ``parse_date`` on a table (the 03/04/26 examples, the 68/69 boundary of ``%y``, a four-digit year that still reads, junk and
  impossible dates are None); the PARITY guard of the two old orders on frozen lists (green before and after); the declaration with
  six options in order, each with its ``label_key`` in the four i18n files, carrying the example in digits; and a file with
  two-digit years read through the plugin (and, over the default, still an unreadable row as today).

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
from backend.app.services.brim_providers.broker_generic_csv import plugin as plugin_module
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
    options=(
        SettingOption("day_first", "Day first"),
        SettingOption("month_first", "Month first"),
        SettingOption("day_first_short", "Day first, two-digit year"),
        SettingOption("month_first_short", "Month first, two-digit year"),
        SettingOption("year_first_short", "Year first, two-digit year"),
        SettingOption("year_first", "Year first"),
    ),
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

#: The six values of the setting, in the order the select shows them (FB-18 added the last four).
ALL_ORDERS = ["day_first", "month_first", "day_first_short", "month_first_short", "year_first_short", "year_first"]

#: ``month_first``'s formats as they were before FB-18 (frozen: it never follows the plugin).
FROZEN_MONTH_FIRST_DATE_FORMATS = [
    "%Y-%m-%d",
    "%m/%d/%Y",
    "%d/%m/%Y",
    "%m-%d-%Y",
    "%d-%m-%Y",
    "%Y/%m/%d",
    "%m.%d.%Y",
    "%d.%m.%Y",
    "%Y%m%d",
    "%d %b %Y",
    "%d %B %Y",
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
    """Registered ``settings_fields``: key ``date_order``, personal scope, a select, default ``day_first``, the six options in order."""
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
    assert [option.value for option in field.options] == ALL_ORDERS


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


# =============================================================================
# D. FB-18: SHORT YEARS AND YEAR FIRST
# =============================================================================


def _dedup(*lists: list[str]) -> list[str]:
    """The lists joined in order, a format kept at its first place only."""
    seen: list[str] = []
    for formats in lists:
        for fmt in formats:
            if fmt not in seen:
                seen.append(fmt)
    return seen


#: The format list of each new order, written out from the contract: its own formats, then the whole fallback list.
EXPECTED_FORMATS = {
    "day_first_short": _dedup(["%Y-%m-%d", "%d/%m/%y", "%d-%m-%y", "%d.%m.%y"], FROZEN_DATE_FORMATS),
    "month_first_short": _dedup(["%Y-%m-%d", "%m/%d/%y", "%m-%d-%y", "%m.%d.%y"], FROZEN_MONTH_FIRST_DATE_FORMATS),
    "year_first_short": _dedup(["%Y-%m-%d", "%y/%m/%d", "%y-%m-%d", "%y.%m.%d"], FROZEN_DATE_FORMATS),
    "year_first": _dedup(["%Y-%m-%d", "%Y/%m/%d", "%Y.%m.%d", "%Y%m%d"], FROZEN_DATE_FORMATS),
}


def test_the_new_orders_are_named_by_constants_with_the_values_of_the_setting():
    """The plugin module names the four new values (``DAY_FIRST_SHORT`` ... ``YEAR_FIRST``); the old two keep theirs."""
    assert (plugin_module.DAY_FIRST, plugin_module.MONTH_FIRST) == ("day_first", "month_first")
    assert (plugin_module.DAY_FIRST_SHORT, plugin_module.MONTH_FIRST_SHORT, plugin_module.YEAR_FIRST_SHORT, plugin_module.YEAR_FIRST) == tuple(ALL_ORDERS[2:])


def test_the_formats_of_the_two_old_orders_are_untouched():
    """PARITY guard, green before and after: ``day_first`` is the frozen list, ``month_first`` the frozen month-first list."""
    assert list(plugin_module._date_formats("day_first")) == FROZEN_DATE_FORMATS
    assert list(plugin_module._date_formats("month_first")) == FROZEN_MONTH_FIRST_DATE_FORMATS


@pytest.mark.parametrize("order", sorted(EXPECTED_FORMATS))
def test_each_new_order_has_its_exact_ordered_deduplicated_format_list(order: str):
    formats = list(plugin_module._date_formats(order))

    assert formats == EXPECTED_FORMATS[order]
    assert len(formats) == len(set(formats)), "a format is listed once"


@pytest.mark.parametrize("unknown", ["", "auto", "DAY_FIRST_SHORT", "day_first_long", "year-first"])
def test_an_unknown_order_still_has_the_day_first_formats(unknown: str):
    """Guard, green before and after: the new values did not change what an unknown one means."""
    assert list(plugin_module._date_formats(unknown)) == FROZEN_DATE_FORMATS


#: (order, value, expected). ``%y`` is Python's: 00-68 are 2000-2068, 69-99 are 1969-1999.
SHORT_CASES = [
    # day_first_short: 03/04/26 is 3 April 2026
    ("day_first_short", "03/04/26", date(2026, 4, 3)),
    ("day_first_short", "03-04-26", date(2026, 4, 3)),
    ("day_first_short", "03.04.26", date(2026, 4, 3)),
    ("day_first_short", "25/12/26", date(2026, 12, 25)),
    ("day_first_short", "2026-04-03", date(2026, 4, 3)),
    ("day_first_short", "03/04/2026", date(2026, 4, 3)),  # a four-digit year still reads, day first
    ("day_first_short", "03-04-2026", date(2026, 4, 3)),
    ("day_first_short", "03.04.2026", date(2026, 4, 3)),
    ("day_first_short", "12/25/2026", date(2026, 12, 25)),  # the whole DATE_FORMATS list is the fallback
    ("day_first_short", "20260403", date(2026, 4, 3)),
    ("day_first_short", "03 Apr 2026", date(2026, 4, 3)),
    ("day_first_short", "  03/04/26  ", date(2026, 4, 3)),
    ("day_first_short", "01/01/68", date(2068, 1, 1)),  # the boundary of %y
    ("day_first_short", "01/01/69", date(1969, 1, 1)),
    ("day_first_short", "01/01/00", date(2000, 1, 1)),
    ("day_first_short", "01/01/99", date(1999, 1, 1)),
    # month_first_short: 03/04/26 is 4 March 2026
    ("month_first_short", "03/04/26", date(2026, 3, 4)),
    ("month_first_short", "03-04-26", date(2026, 3, 4)),
    ("month_first_short", "03.04.26", date(2026, 3, 4)),
    ("month_first_short", "12/25/26", date(2026, 12, 25)),
    ("month_first_short", "2026-04-03", date(2026, 4, 3)),
    ("month_first_short", "03/04/2026", date(2026, 3, 4)),  # four digits: the month-first list
    ("month_first_short", "25/12/2026", date(2026, 12, 25)),  # ... with its day-first fallback
    ("month_first_short", "20260403", date(2026, 4, 3)),
    ("month_first_short", "01/01/68", date(2068, 1, 1)),
    ("month_first_short", "01/01/69", date(1969, 1, 1)),
    # year_first_short: 26/04/03 is 3 April 2026
    ("year_first_short", "26/04/03", date(2026, 4, 3)),
    ("year_first_short", "26-04-03", date(2026, 4, 3)),
    ("year_first_short", "26.04.03", date(2026, 4, 3)),
    ("year_first_short", "2026-04-03", date(2026, 4, 3)),
    ("year_first_short", "03/04/2026", date(2026, 4, 3)),  # four digits fall back to day first
    ("year_first_short", "68/01/01", date(2068, 1, 1)),
    ("year_first_short", "69/01/01", date(1969, 1, 1)),
    ("year_first_short", "00/01/01", date(2000, 1, 1)),
    # year_first: 2026-04-03 is 3 April 2026
    ("year_first", "2026-04-03", date(2026, 4, 3)),
    ("year_first", "2026/04/03", date(2026, 4, 3)),
    ("year_first", "2026.04.03", date(2026, 4, 3)),
    ("year_first", "20260403", date(2026, 4, 3)),
    ("year_first", "03/04/2026", date(2026, 4, 3)),  # the rest of DATE_FORMATS: day first
    ("year_first", "25/12/2026", date(2026, 12, 25)),
    ("year_first", "03 January 2026", date(2026, 1, 3)),
]


@pytest.mark.parametrize(("order", "value", "expected"), SHORT_CASES, ids=[f"{case[0]}:{case[1]}" for case in SHORT_CASES])
def test_the_new_orders_read_the_values_of_their_format(order: str, value: str, expected: date):
    assert parse_date(value, order) == expected


#: Unreadable in EVERY new order: junk, a month or a day out of range everywhere.
UNREADABLE_IN_NEW_ORDERS = ["", "   ", "not a date", "2026-13-45", "00/00/00", "32/13/26"]

#: An impossible date, written in the shape of the order (the same text can be a real date in another order: 31/02/26 is
#: 26 February 2031 year first, so each order has its own).
IMPOSSIBLE_DATES = [
    ("day_first_short", "31/02/26"),
    ("day_first_short", "31/04/26"),
    ("day_first_short", "30-02-26"),
    ("month_first_short", "02/31/26"),
    ("month_first_short", "04/31/26"),
    ("month_first_short", "02.30.26"),
    ("year_first_short", "26/02/31"),
    ("year_first_short", "26-04-31"),
    ("year_first_short", "26.13.01"),
    ("year_first", "2026-02-31"),
    ("year_first", "2026/04/31"),
    ("year_first", "2026.02.30"),
]


@pytest.mark.parametrize("order", ["day_first_short", "month_first_short", "year_first_short", "year_first"])
@pytest.mark.parametrize("value", UNREADABLE_IN_NEW_ORDERS)
def test_what_is_not_a_date_is_none_in_the_new_orders(order: str, value: str):
    assert parse_date(value, order) is None


@pytest.mark.parametrize(("order", "value"), IMPOSSIBLE_DATES, ids=[f"{order}:{value}" for order, value in IMPOSSIBLE_DATES])
def test_an_impossible_date_is_none_never_rolled_over(order: str, value: str):
    """31 February and 31 April are None, never a clamped or rolled-over date."""
    assert parse_date(value, order) is None


def test_a_two_digit_year_is_not_read_by_the_orders_that_have_no_short_format():
    """A two-digit-year value stays unreadable under ``year_first`` (no ``%y`` there) and under the old orders (guard, green before)."""
    for order in ("day_first", "month_first", "year_first"):
        assert parse_date("03/04/26", order) is None, order
    assert parse_date("26/04/03", "day_first") is None


def test_the_short_orders_do_not_swap_each_other():
    """The same text is three different dates: that is what the three orders are for."""
    assert parse_date("03/04/26", "day_first_short") == date(2026, 4, 3)
    assert parse_date("03/04/26", "month_first_short") == date(2026, 3, 4)
    assert parse_date("03/04/26", "year_first_short") == date(2003, 4, 26)


def test_the_old_orders_still_read_a_four_digit_value_as_before():
    """PARITY guard, green before and after, on the values the new ones also read: the old orders answer exactly as frozen."""
    for value in ("03/04/2026", "25/12/2026", "2026-04-03", "20260403", "03-04-2026", "03.04.2026"):
        assert parse_date(value, "day_first") == _reference_parse_date(value)
        assert parse_date(value) == _reference_parse_date(value)


# --- the declaration: six options, each with its label in the four languages -------------------------------------


I18N_DIR = PROJECT_ROOT / "backend" / "app" / "services" / "brim_providers" / "broker_generic_csv" / "i18n"
LANGUAGES = ["en", "it", "fr", "es"]
LABEL_KEY_BASE = "pluginSettings.brim.broker_generic_csv.option.date_order"

#: The example date of each new option, as digits (the words and the letters of the format are the translators').
EXAMPLE_DIGITS = {"day_first_short": "03/04/26", "month_first_short": "03/04/26", "year_first_short": "26/04/03", "year_first": "2026-04-03"}


def _declared_options():
    BRIMProviderRegistry.auto_discover()
    plugin_class = BRIMProviderRegistry.get_plugin(CODE)
    assert plugin_class is not None, f"no BRIM plugin is registered as {CODE}"
    field = next((f for f in plugin_class.settings_fields if f.key == "date_order"), None)
    assert field is not None, f"{CODE} does not declare date_order"
    return field


def _i18n(language: str) -> dict:
    return json.loads((I18N_DIR / f"{language}.json").read_text(encoding="utf-8"))


def _labels(language: str) -> dict[str, str]:
    return _i18n(language)["pluginSettings"]["brim"]["broker_generic_csv"]["option"]["date_order"]


def test_the_field_offers_six_options_in_order_with_the_default_unchanged():
    field = _declared_options()

    assert [option.value for option in field.options] == ALL_ORDERS
    assert len({option.value for option in field.options}) == len(ALL_ORDERS), "an option is declared once"
    assert field.default == "day_first"
    assert field.type is SettingType.SELECT


def test_every_option_has_its_label_key_and_the_key_is_in_the_four_languages():
    field = _declared_options()

    assert {option.value: option.label_key for option in field.options} == {value: f"{LABEL_KEY_BASE}.{value}" for value in ALL_ORDERS}
    for language in LANGUAGES:
        labels = _labels(language)
        for value in ALL_ORDERS:
            assert isinstance(labels.get(value), str) and labels[value].strip(), f"{language}.json has no label for date_order.{value}"
        assert not set(labels) - set(ALL_ORDERS), f"{language}.json labels an option the plugin does not declare: {sorted(set(labels) - set(ALL_ORDERS))}"


@pytest.mark.parametrize("language", LANGUAGES)
@pytest.mark.parametrize("value", sorted(EXAMPLE_DIGITS))
def test_the_label_of_a_new_option_carries_its_example_in_digits(language: str, value: str):
    """The user reads the format and the example in his own language: the digits of the example are in each label, whatever the words."""
    assert EXAMPLE_DIGITS[value] in _labels(language)[value]


@pytest.mark.parametrize("language", LANGUAGES)
def test_the_labels_of_the_six_options_are_all_different(language: str):
    labels = list(_labels(language).values())

    assert len(set(labels)) == len(labels)


# --- through the plugin ------------------------------------------------------------------------------------------


def test_a_file_with_two_digit_years_is_read_under_the_short_orders(tmp_path: Path):
    """03/04/26 through the plugin: 3 April under ``day_first_short``, 4 March under ``month_first_short``, 25/12/26 is 25 December
    under the first; the rows are the same otherwise."""
    path = _write_csv(tmp_path, ["03/04/26,BUY,5,-500.00,EUR,MSFT,ambiguous", "25/12/26,BUY,2,-200.00,EUR,AAPL,christmas", "2026-02-03,DEPOSIT,0,1000.00,EUR,,iso"])

    day = _by_description(_plugin("day_first_short").parse(path, BROKER_ID))
    month = _by_description(_plugin("month_first_short").parse(path, BROKER_ID))

    assert (day["ambiguous"].date, month["ambiguous"].date) == (date(2026, 4, 3), date(2026, 3, 4))
    assert day["christmas"].date == date(2026, 12, 25)
    assert "christmas" not in month, "25 is not a month: the month-first short order does not read it"
    assert (day["iso"].date, month["iso"].date) == (date(2026, 2, 3), date(2026, 2, 3))


def test_a_file_with_year_first_dates_is_read_under_the_year_first_orders(tmp_path: Path):
    path = _write_csv(tmp_path, ["26/04/03,BUY,5,-500.00,EUR,MSFT,short", "2026.04.03,BUY,2,-200.00,EUR,AAPL,dotted"])

    short = _by_description(_plugin("year_first_short").parse(path, BROKER_ID))
    full = _by_description(_plugin("year_first").parse(path, BROKER_ID))

    assert short["short"].date == date(2026, 4, 3)
    assert full["dotted"].date == date(2026, 4, 3)
    assert "short" not in full, "year_first has no two-digit-year format"


def test_the_same_two_digit_file_over_the_default_is_unparsed_as_today(tmp_path: Path):
    """A user who chose nothing (or the old orders) gets no transaction for a two-digit-year date, exactly as before FB-18. The
    warning is the structured ``date_unreadable`` notice since FB-18b (red until then: the plugin sent a plain string)."""
    path = _write_csv(tmp_path, ["03/04/26,BUY,5,-500.00,EUR,MSFT,short"])

    for plugin in (_plugin(bind=False), _plugin("day_first"), _plugin("month_first")):
        output = plugin.parse(path, BROKER_ID)
        assert [tx.description for tx in output.transactions] == []
        notices = _date_notices(output)
        assert [(n.context or {}).get("value") for n in notices] == ["03/04/26"], output.warnings


# =============================================================================
# E. FB-18b: AN UNREADABLE DATE IS REPORTED AS A STRUCTURED NOTICE (``date_unreadable``)
# =============================================================================
#
# The row is still NOT read (no transaction), but the plugin appends a ``BRIMNotice`` (severity warning, code ``date_unreadable``,
# context ``{row, value, order}``): ``row`` counts as the parse loop does (header = 1, first data row = 2), ``value`` is the date text
# as written in the file, stripped, ``order`` the ``date_order`` in force. Only the first 20 such rows get their own notice; the rest
# are summed in ONE ``date_unreadable_more`` notice (``n`` = rows not covered), after them. An EMPTY date cell and every other row
# error keep their plain warning. Red before FB-18b: the plugin appends the plain string ``"Row N: Invalid date format: '...'"``.

NOTICE_CODE = "date_unreadable"
MORE_CODE = "date_unreadable_more"
NOTICE_CAP = 20

#: Dates no format of the order reads, in every order (impossible day or month, junk).
UNREADABLE_EVERYWHERE = ["31/02/2026", "13/13/2013", "hello"]
#: ``25/12/26`` is read by ``day_first_short`` (25 Dec) and ``year_first_short`` (2025-12-26); under these four it is unreadable.
ORDERS_WHERE_SHORT_25_IS_UNREADABLE = {"day_first", "month_first", "month_first_short", "year_first"}

UNREADABLE_CASES = [(order, value) for order in ALL_ORDERS for value in UNREADABLE_EVERYWHERE + (["25/12/26"] if order in ORDERS_WHERE_SHORT_25_IS_UNREADABLE else [])]


def _codes(output) -> list[str]:
    return [notice.code for notice in output.warnings]


def _date_notices(output) -> list:
    """The ``date_unreadable`` notices of a parse, in the order the plugin gave them."""
    return [notice for notice in output.warnings if notice.code == NOTICE_CODE]


def _more_notices(output) -> list:
    return [notice for notice in output.warnings if notice.code == MORE_CODE]


@pytest.mark.parametrize(("order", "value"), UNREADABLE_CASES, ids=[f"{o}-{v}" for o, v in UNREADABLE_CASES])
def test_an_unreadable_date_is_one_structured_notice_and_its_row_is_not_read(tmp_path: Path, order: str, value: str):
    """Row 4 holds the unreadable date between readable rows: one notice with row/value/order, no transaction for it, the
    readable rows are read."""
    path = _write_csv(tmp_path, ["2026-02-03,DEPOSIT,0,1000.00,EUR,,before", "2026-02-04,DEPOSIT,0,200.00,EUR,,between", f"{value},DEPOSIT,0,500.00,EUR,,broken", "2026-02-05,DEPOSIT,0,100.00,EUR,,after"])

    output = _plugin(order).parse(path, BROKER_ID)

    notices = _date_notices(output)
    assert len(notices) == 1, output.warnings
    notice = notices[0]
    assert notice.severity == "warning"
    assert notice.context == {"row": 4, "value": value, "order": order}
    assert "4" in notice.message and value in notice.message, notice.message
    assert set(_by_description(output)) == {"before", "between", "after"}, "the unreadable row is not a transaction, the readable ones are"
    assert not _more_notices(output)


def test_the_value_of_the_notice_is_the_date_as_written_and_stripped(tmp_path: Path):
    path = _write_csv(tmp_path, ["2026-02-03,DEPOSIT,0,1000.00,EUR,,ok", "   hello   ,DEPOSIT,0,500.00,EUR,,broken"])

    output = _plugin("day_first").parse(path, BROKER_ID)

    assert [n.context for n in _date_notices(output)] == [{"row": 3, "value": "hello", "order": "day_first"}]


def test_the_order_in_the_notice_is_the_one_in_force(tmp_path: Path):
    """Same file, two orders in force: the notice names the one the parse ran with; with no settings bound it is the default."""
    path = _write_csv(tmp_path, ["25/12/26,DEPOSIT,0,500.00,EUR,,broken"])

    assert [n.context["order"] for n in _date_notices(_plugin("month_first_short").parse(path, BROKER_ID))] == ["month_first_short"]
    assert [n.context["order"] for n in _date_notices(_plugin("month_first").parse(path, BROKER_ID))] == ["month_first"]
    assert [n.context["order"] for n in _date_notices(_plugin(bind=False).parse(path, BROKER_ID))] == ["day_first"]


def test_the_notices_follow_the_rows(tmp_path: Path):
    path = _write_csv(
        tmp_path,
        ["hello,DEPOSIT,0,1.00,EUR,,a", "2026-02-03,DEPOSIT,0,1000.00,EUR,,ok", "13/13/2013,DEPOSIT,0,2.00,EUR,,b", "31/02/2026,DEPOSIT,0,3.00,EUR,,c"],
    )

    output = _plugin("day_first").parse(path, BROKER_ID)

    assert [(n.context["row"], n.context["value"]) for n in _date_notices(output)] == [(2, "hello"), (4, "13/13/2013"), (5, "31/02/2026")]


@pytest.mark.parametrize(("bad", "own", "more"), [(20, 20, 0), (21, 20, 1), (25, 20, 5)], ids=["exactly-20", "21", "25"])
def test_only_the_first_twenty_unreadable_rows_get_their_own_notice(tmp_path: Path, bad: int, own: int, more: int):
    """Row 2 is readable; the unreadable rows are 3...(bad + 2). 25 bad rows: 20 own notices, then ONE ``_more`` with n = 5;
    exactly 20: no ``_more``."""
    lines = ["2026-02-03,DEPOSIT,0,1000.00,EUR,,ok"] + [f"hello{i},DEPOSIT,0,1.00,EUR,,bad{i}" for i in range(bad)]
    path = _write_csv(tmp_path, lines)

    output = _plugin("day_first").parse(path, BROKER_ID)

    notices = _date_notices(output)
    assert len(notices) == own, _codes(output)
    assert [n.context["row"] for n in notices] == list(range(3, 3 + own)), "the FIRST rows, in order"
    assert [n.context["value"] for n in notices] == [f"hello{i}" for i in range(own)]
    extra = _more_notices(output)
    assert len(extra) == (1 if more else 0), _codes(output)
    if more:
        assert extra[0].severity == "warning"
        assert extra[0].context == {"n": bad - own} == {"n": more}
        codes = _codes(output)
        assert codes.index(MORE_CODE) > max(i for i, c in enumerate(codes) if c == NOTICE_CODE), "the summary comes after the notices it summarises"
        assert codes[-1] == MORE_CODE, "and it closes the notices"
    assert set(_by_description(output)) == {"ok"}, "none of the unreadable rows is a transaction"


def test_an_empty_date_and_other_row_errors_keep_their_plain_warning(tmp_path: Path):
    """Not part of FB-18b: the empty cell, an unknown type, stay plain ``Row N: ...`` strings (coerced by the schema), not the structured notice."""
    path = _write_csv(tmp_path, ["2026-02-03,DEPOSIT,0,1000.00,EUR,,ok", ",DEPOSIT,0,5.00,EUR,,nodate", "2026-02-05,NOSUCHTYPE,0,5.00,EUR,,badtype", "hello,DEPOSIT,0,5.00,EUR,,unreadable"])

    output = _plugin("day_first").parse(path, BROKER_ID)

    by_row = {notice.message.split(":")[0]: notice for notice in output.warnings if notice.message.startswith("Row ")}
    assert "Empty date value" in by_row["Row 3"].message and by_row["Row 3"].code not in {NOTICE_CODE, MORE_CODE}
    assert "Unknown transaction type" in by_row["Row 4"].message and by_row["Row 4"].code not in {NOTICE_CODE, MORE_CODE}
    assert [n.context["row"] for n in _date_notices(output)] == [5], "only the unreadable date is the structured notice"
    assert set(_by_description(output)) == {"ok"}


def test_a_clean_file_has_none_of_the_unreadable_date_notices(tmp_path: Path):
    path = _write_csv(tmp_path, ["2026-02-03,DEPOSIT,0,1000.00,EUR,,one", "2026-02-04,DEPOSIT,0,200.00,EUR,,two"])

    for order in ALL_ORDERS:
        output = _plugin(order).parse(path, BROKER_ID)
        assert set(_by_description(output)) == {"one", "two"}, order
        assert NOTICE_CODE not in _codes(output) and MORE_CODE not in _codes(output), order
