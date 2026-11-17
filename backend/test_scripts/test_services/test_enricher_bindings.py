"""The enricher bindings of an asset (project 68, lot B3): ``services/enrichers/bindings.py``.

Under test, as its module docstring states the contract:

1. ``save_config(session, asset_id, config)`` replaces the asset's ``config`` — creating the row when there is none —
   keeping the key order **exactly as given** (the order is the priority): read back through ``load_enrichers`` and as
   the raw ``asset_enrichers.config`` text, whose keys appear in the same order. ``{}`` clears it. It never touches
   ``state``: removing an enricher from ``config`` leaves its ``state`` entry, and putting it back finds that entry
   unchanged.
2. ``update_state(session, asset_id, entries)`` sets the entries of those enricher codes in ``state``; the other codes'
   entries stay, and ``config`` is never touched. **The race** the two columns exist for: session A has loaded the row,
   session B saves a new config and commits, then A writes its state and commits: the stored config is B's (and the
   symmetric one: a state written while the user's session had the row loaded survives the user's save).
3. ``load_enrichers(session, asset_ids)`` → ``{asset_id: AssetEnricherRow}``; an asset without a row is left out.
4. ``installed_enrichers()`` → an instance of every enricher the registry serves, ordered by code (``mockenrich`` in
   test mode).
5. ``default_order(asset_type, *, price_provider_code, found_order)``: only the enrichers covering the type; by degree
   (lower first), then the one whose code is the price provider's, then the ``found_order``, then by code. Each
   tie-break is proven with synthetic enrichers registered on ``EnricherRegistry`` (``lab_bind_*`` codes, removed at
   teardown), built so that the alphabetical order would give the opposite answer. Only the relative order of the
   test's own codes is asserted: the real enrichers of later lots may sit anywhere among them.
6. ``enrichers_catalogue()`` → ``FAEnrichersCatalogue``: every installed enricher with its declarations (voices per
   type as sorted lists, a degree for every AssetType), and ``default_order`` with a key for every AssetType — the
   list of the enrichers covering it, empty when none does.

Not pinned: ``update_state`` on an asset with no row.

Every database is a private SQLite file under ``tmp_path`` built with ``SQLModel.metadata.create_all``, opened as
production opens its own (aiosqlite, NullPool, the PRAGMA listener of ``backend.app.db.session``). The functions never
commit: the tests do. Test mode is set with ``monkeypatch`` behind an ``is_test_mode()`` barrier.

Red until B3: every function of ``bindings.py`` raises ``NotImplementedError``; each test fails at its first call,
never at collection.
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator, Iterator
from pathlib import Path
from typing import Any

import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

from backend.app.config import is_test_mode
from backend.app.db.base import SQLModel  # imports every model, and backend.app.db.session with its PRAGMA listener
from backend.app.db.models import Asset, AssetEnrichers, AssetType
from backend.app.schemas.assets.enrichers import FAEnrichersCatalogue
from backend.app.services.enrichers import bindings
from backend.app.services.enrichers.base import EnricherBinding, EnricherPlugin, EnricherReadItem, EnricherRecognition, EnricherTerms
from backend.app.services.enrichers.registry import EnricherRegistry
from backend.app.services.plugin_settings.fields import release_env_variables
from backend.test_scripts.test_utils import print_section, print_success

TEST_MODE_VARIABLE = "LIBREFOLIO_TEST_MODE"
MOCK_CODE = "mockenrich"
SETTINGS_FAMILY = "enricher"
LAB_PREFIX = "lab_bind_"

#: A config in an order that is not alphabetical, with codes not installed and a plugin's own key (``mic``).
CONFIG_ORDER = ["zeta_lab", MOCK_CODE, "alpha_lab"]
CONFIG = {
    "zeta_lab": {"identifier_type": "ISIN", "identifier": "IE00B4L5Y983"},
    MOCK_CODE: {"identifier_type": "ISIN", "identifier": "IE00B4L5Y983"},
    "alpha_lab": {"identifier_type": "ISIN", "identifier": "IT0003128367", "mic": "MTA"},
}
#: Another order of other bindings: the save replaces, never merges.
CONFIG_AGAIN_ORDER = ["alpha_lab", "beta_lab", MOCK_CODE]
CONFIG_AGAIN = {
    "alpha_lab": {"identifier_type": "LEI", "identifier": "815600C1E8D1A8C6E417"},
    "beta_lab": {"identifier_type": "TICKER", "identifier": "SWDA"},
    MOCK_CODE: {"identifier_type": "ISIN", "identifier": "IE00B4L5Y983"},
}
STATE_MOCK = {"read_on": "2026-11-10", "outcome": "ok"}
STATE_MOCK_AGAIN = {"read_on": "2026-11-12", "outcome": "not_found"}
STATE_ZETA = {"read_on": "2026-11-11", "outcome": "error"}


# =============================================================================
# FIXTURES AND HELPERS
# =============================================================================


def _test_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(TEST_MODE_VARIABLE, "1")
    assert is_test_mode() is True, f"barrier: with {TEST_MODE_VARIABLE}=1 is_test_mode() is false"


@pytest_asyncio.fixture
async def engine(tmp_path: Path) -> AsyncIterator[AsyncEngine]:
    """A private SQLite file under tmp_path with the whole ORM schema, opened as production opens its own."""
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'enricher_bindings.db'}", poolclass=NullPool)
    try:
        async with engine.begin() as connection:
            await connection.run_sync(SQLModel.metadata.create_all)
            foreign_keys = (await connection.execute(text("PRAGMA foreign_keys"))).scalar()
        assert foreign_keys == 1, "barrier: the app's PRAGMA listener must hold on the private file (foreign keys on)"
        yield engine
    finally:
        await engine.dispose()


async def _asset(engine: AsyncEngine, name: str) -> int:
    async with AsyncSession(engine, expire_on_commit=False) as session:
        asset = Asset(display_name=name, currency="EUR", asset_type=AssetType.ETF)
        session.add(asset)
        await session.commit()
    return int(asset.id)


async def _save(engine: AsyncEngine, asset_id: int, config: dict[str, dict[str, Any]]) -> None:
    async with AsyncSession(engine) as session:
        await bindings.save_config(session, asset_id, config)
        await session.commit()


async def _state(engine: AsyncEngine, asset_id: int, entries: dict[str, dict[str, Any]]) -> None:
    async with AsyncSession(engine) as session:
        await bindings.update_state(session, asset_id, entries)
        await session.commit()


async def _load(engine: AsyncEngine, asset_ids: list[int]) -> dict[int, bindings.AssetEnricherRow]:
    async with AsyncSession(engine) as session:
        return await bindings.load_enrichers(session, asset_ids)


async def _raw(engine: AsyncEngine, asset_id: int) -> tuple[str, str] | None:
    """The row's ``config`` and ``state`` as stored text, or None when the asset has no row."""
    async with AsyncSession(engine) as session:
        row = (await session.execute(text("SELECT config, state FROM asset_enrichers WHERE asset_id = :asset"), {"asset": asset_id})).first()
    return None if row is None else (row.config, row.state)


def _text_order(stored: str) -> list[str]:
    """The keys of a stored JSON object in the order they appear in its text."""
    return [key for key, _ in json.loads(stored, object_pairs_hook=list)]


# =============================================================================
# 1. save_config
# =============================================================================


@pytest.mark.asyncio
async def test_save_config_creates_the_row_and_keeps_the_order_as_given(engine: AsyncEngine) -> None:
    """No row first; a config in a non-alphabetical order, with codes not installed and a free key: the row is created,
    ``load_enrichers`` gives the config in that order with the free key, ``state`` empty; the stored text has its keys
    in that order too."""
    print_section("save_config: the order is the priority")
    asset = await _asset(engine, "Ordered ETF")
    assert await _load(engine, [asset]) == {}, "barrier: a new asset has no row"

    await _save(engine, asset, CONFIG)

    row = (await _load(engine, [asset]))[asset]
    assert row.asset_id == asset
    assert list(row.config) == CONFIG_ORDER, f"the config keeps the order given: {list(row.config)}"
    assert row.config == CONFIG, f"the bindings as given, free keys included: {row.config}"
    assert row.state == {}, f"a new row has no state: {row.state}"
    stored = await _raw(engine, asset)
    assert stored is not None and _text_order(stored[0]) == CONFIG_ORDER, f"the stored text keeps the order: {stored}"
    print_success("order kept in the row and in its text")


@pytest.mark.asyncio
async def test_save_config_replaces_with_another_order(engine: AsyncEngine) -> None:
    """A second save in another order, without one code and with a new one: the config is exactly the new one."""
    asset = await _asset(engine, "Reordered ETF")
    await _save(engine, asset, CONFIG)
    assert list((await _load(engine, [asset]))[asset].config) == CONFIG_ORDER, "barrier: the first config is stored"

    await _save(engine, asset, CONFIG_AGAIN)

    row = (await _load(engine, [asset]))[asset]
    assert list(row.config) == CONFIG_AGAIN_ORDER and row.config == CONFIG_AGAIN, f"the save replaces: {row.config}"
    stored = await _raw(engine, asset)
    assert stored is not None and _text_order(stored[0]) == CONFIG_AGAIN_ORDER, f"the stored text keeps the new order: {stored}"


@pytest.mark.asyncio
async def test_save_config_of_an_empty_dict_clears_it_and_keeps_the_state(engine: AsyncEngine) -> None:
    """``{}`` clears the config; the state written before stays."""
    asset = await _asset(engine, "Cleared ETF")
    await _save(engine, asset, CONFIG)
    await _state(engine, asset, {MOCK_CODE: STATE_MOCK})
    before = (await _load(engine, [asset]))[asset]
    assert before.config == CONFIG and before.state == {MOCK_CODE: STATE_MOCK}, f"barrier: config and state stored: {before}"

    await _save(engine, asset, {})

    row = (await _load(engine, [asset]))[asset]
    assert row.config == {}, f"{{}} clears the config: {row.config}"
    assert row.state == {MOCK_CODE: STATE_MOCK}, f"save_config never touches the state: {row.state}"


@pytest.mark.asyncio
async def test_save_config_never_touches_the_state(engine: AsyncEngine) -> None:
    """A state for two codes, then a new config: the state is exactly as before."""
    asset = await _asset(engine, "State-kept ETF")
    await _save(engine, asset, CONFIG)
    await _state(engine, asset, {MOCK_CODE: STATE_MOCK, "zeta_lab": STATE_ZETA})
    assert (await _load(engine, [asset]))[asset].state == {MOCK_CODE: STATE_MOCK, "zeta_lab": STATE_ZETA}, "barrier: the state is stored"

    await _save(engine, asset, CONFIG_AGAIN)

    row = (await _load(engine, [asset]))[asset]
    assert row.config == CONFIG_AGAIN, f"barrier: the new config is stored: {row.config}"
    assert row.state == {MOCK_CODE: STATE_MOCK, "zeta_lab": STATE_ZETA}, f"save_config never touches the state: {row.state}"


@pytest.mark.asyncio
async def test_removing_an_enricher_from_the_config_keeps_its_state_entry_for_when_it_comes_back(engine: AsyncEngine) -> None:
    """``zeta_lab`` has a state entry; a config without it leaves the entry; a config with it again finds the entry
    unchanged (design consultant, B3)."""
    asset = await _asset(engine, "Removed-and-back ETF")
    await _save(engine, asset, CONFIG)
    await _state(engine, asset, {"zeta_lab": STATE_ZETA, MOCK_CODE: STATE_MOCK})

    without = {code: binding for code, binding in CONFIG.items() if code != "zeta_lab"}
    await _save(engine, asset, without)
    removed = (await _load(engine, [asset]))[asset]
    assert list(removed.config) == [MOCK_CODE, "alpha_lab"], f"barrier: zeta_lab is out of the config: {list(removed.config)}"
    assert removed.state.get("zeta_lab") == STATE_ZETA, f"the removed enricher's state entry stays: {removed.state}"

    await _save(engine, asset, CONFIG)
    back = (await _load(engine, [asset]))[asset]
    assert list(back.config) == CONFIG_ORDER, f"barrier: zeta_lab is back in the config: {list(back.config)}"
    assert back.state == {"zeta_lab": STATE_ZETA, MOCK_CODE: STATE_MOCK}, f"its old state entry is found unchanged: {back.state}"


# =============================================================================
# 2. update_state
# =============================================================================


@pytest.mark.asyncio
async def test_update_state_sets_its_codes_and_leaves_the_others(engine: AsyncEngine) -> None:
    """Two writes: the first sets ``mockenrich``, the second ``zeta_lab`` and ``mockenrich`` again: both entries are
    there, ``mockenrich`` the last one."""
    asset = await _asset(engine, "State ETF")
    await _save(engine, asset, CONFIG)

    await _state(engine, asset, {MOCK_CODE: STATE_MOCK})
    assert (await _load(engine, [asset]))[asset].state == {MOCK_CODE: STATE_MOCK}, "the first entry is set"
    await _state(engine, asset, {"zeta_lab": STATE_ZETA})
    assert (await _load(engine, [asset]))[asset].state == {MOCK_CODE: STATE_MOCK, "zeta_lab": STATE_ZETA}, "another code's entry stays"
    await _state(engine, asset, {MOCK_CODE: STATE_MOCK_AGAIN})

    row = (await _load(engine, [asset]))[asset]
    assert row.state == {MOCK_CODE: STATE_MOCK_AGAIN, "zeta_lab": STATE_ZETA}, f"mockenrich's entry is the last one, zeta_lab's stays: {row.state}"


@pytest.mark.asyncio
async def test_update_state_never_touches_the_config(engine: AsyncEngine) -> None:
    """The config, its order and its text are the same after a state write."""
    asset = await _asset(engine, "Config-kept ETF")
    await _save(engine, asset, CONFIG)
    before = await _raw(engine, asset)
    assert before is not None, "barrier: the row exists"

    await _state(engine, asset, {MOCK_CODE: STATE_MOCK})

    row = (await _load(engine, [asset]))[asset]
    assert row.state == {MOCK_CODE: STATE_MOCK}, f"barrier: the state is written: {row.state}"
    assert list(row.config) == CONFIG_ORDER and row.config == CONFIG, f"update_state never touches the config: {row.config}"
    after = await _raw(engine, asset)
    assert after is not None and _text_order(after[0]) == CONFIG_ORDER, f"nor its stored order: {after}"


@pytest.mark.asyncio
async def test_a_state_written_after_a_users_save_never_brings_back_the_old_config(engine: AsyncEngine) -> None:
    """The race the two columns exist for. Session A (a read) has loaded the row (and holds it in its identity map); session B (the user) saves another
    config and commits; then A writes its state and commits. The stored config is B's, in B's order, and A's state is
    there."""
    print_section("update_state: a read finishing while the user saves")
    asset = await _asset(engine, "Race ETF")
    await _save(engine, asset, CONFIG)

    async with AsyncSession(engine) as reader:
        loaded = await bindings.load_enrichers(reader, [asset])
        held = await reader.get(AssetEnrichers, asset)  # the row stays in A's identity map, as a read job holding it
        assert list(loaded[asset].config) == CONFIG_ORDER and held is not None and _text_order(held.config) == CONFIG_ORDER, "barrier: A loaded the old config"

        async with AsyncSession(engine) as user:
            await bindings.save_config(user, asset, CONFIG_AGAIN)
            await user.commit()

        await bindings.update_state(reader, asset, {MOCK_CODE: STATE_MOCK})
        await reader.commit()

    row = (await _load(engine, [asset]))[asset]
    assert list(row.config) == CONFIG_AGAIN_ORDER and row.config == CONFIG_AGAIN, f"the stored config is the user's: {row.config}"
    assert row.state == {MOCK_CODE: STATE_MOCK}, f"the read's state is there: {row.state}"
    print_success("the user's config survives the read")


@pytest.mark.asyncio
async def test_a_users_save_after_a_state_write_never_erases_the_state(engine: AsyncEngine) -> None:
    """The symmetric race. The user's session has loaded the row; a read writes its state and commits; then the user
    saves a config and commits. The read's state is there."""
    asset = await _asset(engine, "Race-back ETF")
    await _save(engine, asset, CONFIG)

    async with AsyncSession(engine) as user:
        loaded = await bindings.load_enrichers(user, [asset])
        held = await user.get(AssetEnrichers, asset)  # the row stays in the user's identity map
        assert loaded[asset].state == {} and held is not None and json.loads(held.state) == {}, "barrier: the user loaded an empty state"

        async with AsyncSession(engine) as reader:
            await bindings.update_state(reader, asset, {MOCK_CODE: STATE_MOCK})
            await reader.commit()

        await bindings.save_config(user, asset, CONFIG_AGAIN)
        await user.commit()

    row = (await _load(engine, [asset]))[asset]
    assert row.config == CONFIG_AGAIN, f"barrier: the user's config is saved: {row.config}"
    assert row.state == {MOCK_CODE: STATE_MOCK}, f"the read's state survives the user's save: {row.state}"


# =============================================================================
# 3. load_enrichers
# =============================================================================


@pytest.mark.asyncio
async def test_load_enrichers_answers_the_rows_and_leaves_out_the_assets_without_one(engine: AsyncEngine) -> None:
    first = await _asset(engine, "Bound ETF")
    second = await _asset(engine, "Also bound ETF")
    unbound = await _asset(engine, "Unbound ETF")
    await _save(engine, first, CONFIG)
    await _save(engine, second, CONFIG_AGAIN)

    rows = await _load(engine, [first, unbound, second])

    assert set(rows) == {first, second}, f"an asset without a row is left out: {sorted(rows)}"
    assert rows[first].asset_id == first and list(rows[first].config) == CONFIG_ORDER
    assert rows[second].asset_id == second and list(rows[second].config) == CONFIG_AGAIN_ORDER
    assert rows[first].updated_at is not None and rows[second].updated_at is not None, "a stored row has its updated_at"


# =============================================================================
# 4–6. installed_enrichers, default_order, enrichers_catalogue
# =============================================================================


class _LabMethods(EnricherPlugin):
    """The abstract methods once: a synthetic enricher differs by its declarations only."""

    def recognize(self, binding: EnricherBinding) -> EnricherRecognition:
        return EnricherRecognition(found=False)

    def read(self, bindings, keys=None) -> Iterator[EnricherReadItem]:  # noqa: ARG002 — the contract's signature
        yield from ()

    def page_url(self, binding: EnricherBinding) -> str | None:
        return None

    @property
    def test_cases(self) -> list[dict]:
        return []


@pytest.fixture
def lab() -> Iterator[Any]:
    """Registers synthetic enrichers: ``lab(name, degree)`` → its code; a degree for ETF (None: not covered), the others
    not covered. Removed from the registry, with their claims, at teardown."""
    codes: list[str] = []

    def register(name: str, etf_degree: int | None, *, voices: frozenset[str] = frozenset({"ter"})) -> str:
        code = f"{LAB_PREFIX}{name}"
        attributes = {
            "code": code,
            "name": f"Lab {name} (testing)",
            "terms": EnricherTerms.OPEN,
            "accepted_identifier_types": ("ISIN",),
            "default_priority": {asset_type: (etf_degree if asset_type == AssetType.ETF else None) for asset_type in AssetType},
            "voices": {AssetType.ETF: voices} if etf_degree is not None else {},
        }
        codes.append(code)
        EnricherRegistry.register(type(f"LabBindEnricher_{name}", (_LabMethods,), attributes))
        return code

    yield register
    storage = EnricherRegistry._get_storage()
    for code in codes:
        stored = storage.get(code)
        if stored is not None and getattr(stored, "__name__", "").startswith("LabBindEnricher_"):
            storage.pop(code, None)
        release_env_variables(SETTINGS_FAMILY, code)


def _mine(order: list[str], codes: list[str]) -> list[str]:
    """``order`` restricted to the test's own codes: real enrichers may sit anywhere among them."""
    return [code for code in order if code in codes]


def test_installed_enrichers_are_instances_by_code_with_mockenrich_in_test_mode(monkeypatch: pytest.MonkeyPatch, lab) -> None:
    _test_mode(monkeypatch)
    own = lab("installed", 10)

    installed = bindings.installed_enrichers()

    codes = [plugin.code for plugin in installed]
    assert all(isinstance(plugin, EnricherPlugin) for plugin in installed), f"instances of enrichers: {installed}"
    assert MOCK_CODE in codes and own in codes, f"mockenrich (test mode) and the registered lab enricher are installed: {codes}"
    assert codes == sorted(codes), f"ordered by code: {codes}"
    assert len(codes) == len(set(codes)), f"one instance per code: {codes}"


def test_default_order_puts_the_lower_degree_first(monkeypatch: pytest.MonkeyPatch, lab) -> None:
    """``a`` would come first by code; its degree is higher: ``b`` comes first."""
    _test_mode(monkeypatch)
    late, early = lab("a_degree", 20), lab("b_degree", 5)

    order = bindings.default_order(AssetType.ETF)

    assert _mine(order, [late, early]) == [early, late], f"lower degree first: {order}"


def test_default_order_leaves_out_an_enricher_that_does_not_cover_the_type(monkeypatch: pytest.MonkeyPatch, lab) -> None:
    _test_mode(monkeypatch)
    covering, not_covering = lab("covers", 10), lab("no_cover", None)

    etf, index = bindings.default_order(AssetType.ETF), bindings.default_order(AssetType.INDEX)

    assert covering in etf and not_covering not in etf, f"only the enrichers covering ETF: {etf}"
    assert covering not in index and MOCK_CODE not in index, f"neither covers INDEX: {index}"
    assert MOCK_CODE in etf, f"mockenrich covers ETF: {etf}"


def test_default_order_with_equal_degrees_and_nothing_else_is_by_code(monkeypatch: pytest.MonkeyPatch, lab) -> None:
    """Registered c, a, b with the same degree and no other information: a, b, c (plan rounds 38/40)."""
    _test_mode(monkeypatch)
    third, first, second = lab("c_alpha", 10), lab("a_alpha", 10), lab("b_alpha", 10)

    order = bindings.default_order(AssetType.ETF)

    assert _mine(order, [first, second, third]) == [first, second, third], f"equal degrees: by code: {order}"


def test_default_order_puts_the_price_provider_first_among_equal_degrees_but_never_before_a_lower_degree(monkeypatch: pytest.MonkeyPatch, lab) -> None:
    """Same degree for a, b, c; the price provider is c: c, a, b. A lower degree (d) still comes before c."""
    _test_mode(monkeypatch)
    a, b, c = lab("a_price", 10), lab("b_price", 10), lab("c_price", 10)
    d = lab("d_price", 3)

    order = bindings.default_order(AssetType.ETF, price_provider_code=c)

    assert _mine(order, [a, b, c, d]) == [d, c, a, b], f"degree, then the price provider, then by code: {order}"


def test_default_order_follows_found_order_among_equal_degrees(monkeypatch: pytest.MonkeyPatch, lab) -> None:
    """Same degree for a, b, c; «recognize» found c then b: c, b, then a (not found)."""
    _test_mode(monkeypatch)
    a, b, c = lab("a_found", 10), lab("b_found", 10), lab("c_found", 10)

    order = bindings.default_order(AssetType.ETF, found_order=(c, b))

    assert _mine(order, [a, b, c]) == [c, b, a], f"the found order, then by code: {order}"


def test_default_order_puts_the_price_provider_before_the_found_order(monkeypatch: pytest.MonkeyPatch, lab) -> None:
    """Same degree for a, b, c; found c then a; the price provider is b: b, c, a."""
    _test_mode(monkeypatch)
    a, b, c = lab("a_both", 10), lab("b_both", 10), lab("c_both", 10)

    order = bindings.default_order(AssetType.ETF, price_provider_code=b, found_order=(c, a))

    assert _mine(order, [a, b, c]) == [b, c, a], f"the price provider, then the found order: {order}"


def test_default_order_puts_the_degree_before_the_found_order(monkeypatch: pytest.MonkeyPatch, lab) -> None:
    """a has the lower degree; «recognize» found b first: a still comes first."""
    _test_mode(monkeypatch)
    a, b = lab("a_degree_found", 5), lab("b_degree_found", 10)

    order = bindings.default_order(AssetType.ETF, found_order=(b, a))

    assert _mine(order, [a, b]) == [a, b], f"the degree before the found order: {order}"


def test_the_catalogue_lists_every_installed_enricher_with_its_declarations(monkeypatch: pytest.MonkeyPatch, lab) -> None:
    print_section("enrichers_catalogue: what GET /assets/enrichers answers")
    _test_mode(monkeypatch)
    own = lab("catalogue", 7, voices=frozenset({"ter", "geography", "description"}))

    catalogue = bindings.enrichers_catalogue()

    assert isinstance(catalogue, FAEnrichersCatalogue)
    by_code = {info.code: info for info in catalogue.enrichers}
    installed = bindings.installed_enrichers()
    assert set(by_code) == {plugin.code for plugin in installed}, f"every installed enricher, nothing else: {sorted(by_code)}"
    info = by_code[own]
    assert info.name == "Lab catalogue (testing)" and info.terms == "open" and info.accepted_identifier_types == ["ISIN"], f"the lab enricher's declarations: {info}"
    assert info.voices.get(AssetType.ETF) == ["description", "geography", "ter"], f"voices per type as a sorted list: {info.voices}"
    assert set(info.default_priority) == set(AssetType), f"a degree for every AssetType: {info.default_priority}"
    assert info.default_priority[AssetType.ETF] == 7 and info.default_priority[AssetType.INDEX] is None, f"its degrees: {info.default_priority}"
    assert info.supports_search is False and info.params_schema == []

    from backend.app.services.enricher_providers.mockenrich.plugin import MockEnricher  # noqa: PLC0415 — the plugin's own declarations, read in the test body

    mock = by_code[MOCK_CODE]
    assert mock.terms == "open" and mock.accepted_identifier_types == list(MockEnricher.accepted_identifier_types)
    assert {asset_type: sorted(keys) for asset_type, keys in MockEnricher.voices.items()} == {asset_type: keys for asset_type, keys in mock.voices.items() if keys}, f"mockenrich's voices as sorted lists: {mock.voices}"
    assert mock.default_priority == dict(MockEnricher.default_priority), f"mockenrich's degrees: {mock.default_priority}"
    print_success(f"{len(by_code)} enrichers with their declarations")


def test_the_catalogue_has_a_default_order_for_every_asset_type(monkeypatch: pytest.MonkeyPatch, lab) -> None:
    """A key for every AssetType, its value the default order of that type — empty when no installed enricher covers it."""
    _test_mode(monkeypatch)
    own = lab("catalogue_order", 10)

    catalogue = bindings.enrichers_catalogue()

    assert set(catalogue.default_order) == set(AssetType), f"a key for every AssetType: {sorted(catalogue.default_order)}"
    installed = bindings.installed_enrichers()
    for asset_type in AssetType:
        covering = {plugin.code for plugin in installed if plugin.covers(asset_type)}
        listed = catalogue.default_order[asset_type]
        assert set(listed) == covering and len(listed) == len(covering), f"{asset_type}: the enrichers covering it, each once: {listed} vs {sorted(covering)}"
        assert listed == bindings.default_order(asset_type), f"{asset_type}: the default order: {listed}"
    assert own in catalogue.default_order[AssetType.ETF] and own not in catalogue.default_order[AssetType.INDEX]
    assert MOCK_CODE in catalogue.default_order[AssetType.ETF] and MOCK_CODE not in catalogue.default_order[AssetType.INDEX]
