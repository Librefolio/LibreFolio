"""The bindings of the enrichers to the assets (plan 68, §3.1, B3): ``asset_enrichers``, one row per asset.

- ``config`` is a JSON object, enricher code → binding, and **the order of its keys is the priority**: it is stored as
  given and never re-sorted (a sorted dump would invert the priority without any error). Only the user writes it.
- ``state`` is a JSON object, enricher code → its last read and outcome. Only the reads that save write it. The two are
  separate columns, each written alone, so that a read finishing while the user saves never brings back a binding the
  user removed.

The installed enrichers come from ``EnricherRegistry``; their default order for an asset type is by degree
(``default_priority``), then the enricher with the same code as the asset's price provider, then — when there is one —
the order in which «recognize» answered «found», and last by code (plan I6).
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from sqlalchemy import insert, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models import AssetEnrichers, AssetType
from backend.app.db.session import begin_writes
from backend.app.schemas.assets.enrichers import FAEnricherInfo, FAEnrichersCatalogue
from backend.app.services.enrichers.base import EnricherPlugin
from backend.app.services.enrichers.registry import EnricherRegistry
from backend.app.utils.datetime_utils import utcnow


@dataclass(frozen=True, slots=True)
class AssetEnricherRow:
    """An asset's row: ``config`` in its order, ``state``, when it last changed."""

    asset_id: int
    config: dict[str, dict[str, Any]]
    state: dict[str, dict[str, Any]]
    updated_at: datetime | None


def _loads(text: str | None) -> dict[str, Any]:
    """A JSON object column; ``{}`` for an empty or unreadable one (never written by the app)."""
    if not text:
        return {}
    try:
        value = json.loads(text)
    except ValueError:
        return {}
    return value if isinstance(value, dict) else {}


def _dumps(value: Mapping[str, Any]) -> str:
    # Never sort_keys: the order of the keys of config is the priority
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), default=str)


async def load_enrichers(session: AsyncSession, asset_ids: Sequence[int]) -> dict[int, AssetEnricherRow]:
    """The rows of those assets; an asset without a row is left out."""
    if not asset_ids:
        return {}
    statement = select(AssetEnrichers.asset_id, AssetEnrichers.config, AssetEnrichers.state, AssetEnrichers.updated_at).where(AssetEnrichers.asset_id.in_(list(asset_ids)))
    rows = (await session.execute(statement)).all()
    return {asset_id: AssetEnricherRow(asset_id=asset_id, config=_loads(config), state=_loads(state), updated_at=updated_at) for asset_id, config, state, updated_at in rows}


async def _ensure_row(session: AsyncSession, asset_id: int) -> None:
    """Create the asset's row, empty, when it has none (under the write lock the caller holds)."""
    exists = (await session.execute(select(AssetEnrichers.asset_id).where(AssetEnrichers.asset_id == asset_id))).first()
    if exists is None:
        await session.execute(insert(AssetEnrichers).values(asset_id=asset_id, config="{}", state="{}", updated_at=utcnow()))


async def save_config(session: AsyncSession, asset_id: int, config: Mapping[str, Mapping[str, Any]]) -> None:
    """Replace the asset's ``config`` with ``config``, in its order; ``state`` is not touched. Not committed."""
    await begin_writes(session, AssetEnrichers)
    await _ensure_row(session, asset_id)
    text = _dumps({code: dict(binding) for code, binding in config.items()})
    statement = update(AssetEnrichers).where(AssetEnrichers.asset_id == asset_id).values(config=text, updated_at=utcnow())
    await session.execute(statement.execution_options(synchronize_session=False))


async def update_state(session: AsyncSession, asset_id: int, entries: Mapping[str, Mapping[str, Any]]) -> None:
    """Set the ``state`` of those enrichers of the asset (the others stay); ``config`` is not touched. Not committed.

    The state is read again under the write lock and only its column is written: a ``config`` the user saved meanwhile
    stays as the user saved it.
    """
    await begin_writes(session, AssetEnrichers)
    await _ensure_row(session, asset_id)
    current = (await session.execute(select(AssetEnrichers.state).where(AssetEnrichers.asset_id == asset_id))).scalar_one()
    state = {**_loads(current), **{code: dict(entry) for code, entry in entries.items()}}
    statement = update(AssetEnrichers).where(AssetEnrichers.asset_id == asset_id).values(state=_dumps(state), updated_at=utcnow())
    await session.execute(statement.execution_options(synchronize_session=False))


def installed_enrichers() -> list[EnricherPlugin]:
    """An instance of every enricher the registry serves, by code."""
    return [EnricherRegistry.get_plugin_instance(code) for code in sorted(EnricherRegistry.list_plugin_codes())]


def default_order(asset_type: AssetType, *, price_provider_code: str | None = None, found_order: Sequence[str] = ()) -> list[str]:
    """The codes of the enrichers that cover ``asset_type``, in their default order (see the module docstring)."""
    arrival = {code: index for index, code in enumerate(found_order)}
    covering = [plugin for plugin in installed_enrichers() if plugin.covers(asset_type)]
    covering.sort(key=lambda plugin: (plugin.default_priority[asset_type], plugin.code != price_provider_code, arrival.get(plugin.code, len(arrival)), plugin.code))
    return [plugin.code for plugin in covering]


def _info(plugin: EnricherPlugin) -> FAEnricherInfo:
    return FAEnricherInfo(
        code=plugin.code,
        name=plugin.name,
        icon=plugin.icon,
        help_url=plugin.help_url,
        terms=plugin.terms.value,
        accepted_identifier_types=list(plugin.accepted_identifier_types),
        params_schema=plugin.params_schema,
        supports_search=plugin.supports_search,
        voices={asset_type: sorted(keys) for asset_type, keys in plugin.voices.items()},
        default_priority=dict(plugin.default_priority),
    )


def enrichers_catalogue() -> FAEnrichersCatalogue:
    """What ``GET /assets/enrichers`` answers: every installed enricher with its declarations, and the default order of
    each asset type."""
    return FAEnrichersCatalogue(enrichers=[_info(plugin) for plugin in installed_enrichers()], default_order={asset_type: default_order(asset_type) for asset_type in AssetType})
