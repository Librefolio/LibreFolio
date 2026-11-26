"""«Recognize» in cascade (plan 68, B4; research §3): which enrichers know an asset, from the identifiers known.

The enrichers that cover the asset type are asked all at once; the answers come out as they arrive. Each enricher is
asked with one identifier it accepts at a time, the strongest first (ISIN and LEI before a ticker), and after a clean
«not found» with the next one, until one finds; the answer says which one found it. An error stops that enricher: a
site that refuses must not get one more call per identifier (plan B4, consultant 16/11). An answer «found» may name
other identifiers:

- a **strong** one (``STRONG_IDENTIFIER_TYPES``: ISIN, LEI) not known yet joins the known ones and starts a new round
  on the enrichers not found yet that accept it; one already searched never starts anything again (no cap: the list of
  searched identifiers is what stops the cascade);
- a strong one **different** from the one known of that type makes that answer a **conflict**: it is shown, adds
  nothing and starts nothing;
- a weak one (a ticker) is only reported, a candidate the user may pick.

An enricher found stops being asked. The plugin calls block: each runs in a worker thread (``asyncio.to_thread``). A
plugin that raises gives an ``error`` answer, logged; the others go on.

**Seeds** (ENR-2) are bindings to start from, today the asset's price assignment. A source's price provider and its
enricher share their code, so a seed of the code of a covering enricher that accepts its type is that enricher's first
binding, with the parameters its ``params_schema`` declares (the others are dropped); after a clean «not found» it goes
on with the identifiers known. A seed's identifier joins the known ones: a type not known yet is added; a weak one
(a ticker) different from the asset's goes first, the asset's kept as the last choice (R6: ``SWDA.MI`` before
``SWDA``); a strong one different from the asset's is a **conflict**: it joins nothing, and the enricher of the seed's
code answers ``conflict`` and is not asked.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Mapping, Sequence
from dataclasses import dataclass, field
from enum import StrEnum

from backend.app.db.models import AssetType
from backend.app.logging_config import get_logger
from backend.app.services.enrichers.admission import count_shared_call
from backend.app.services.enrichers.base import STRONG_IDENTIFIER_TYPES, EnricherBinding, EnricherPlugin, EnricherRecognition
from backend.app.services.enrichers.bindings import installed_enrichers

logger = get_logger(__name__)


class RecognizeStatus(StrEnum):
    FOUND = "found"
    NOT_FOUND = "not_found"
    CONFLICT = "conflict"
    ERROR = "error"


@dataclass(frozen=True, slots=True)
class Recognized:
    """One enricher's answer for one binding."""

    code: str
    binding: EnricherBinding
    status: RecognizeStatus
    name: str | None = None
    page_url: str | None = None
    identifiers: Mapping[str, str] = field(default_factory=dict)
    conflicts: Mapping[str, str] = field(default_factory=dict)
    error: str | None = None


@dataclass(frozen=True, slots=True)
class IdentifierLearned:
    """A strong identifier the cascade learned, and from which enricher; it starts a new round."""

    identifier_type: str
    identifier: str
    source: str


@dataclass(frozen=True, slots=True)
class Seed:
    """A binding to start from (ENR-2): the source's code and how it names the asset, with its parameters."""

    code: str
    binding: EnricherBinding


@dataclass
class _Cascade:
    """The state of one cascade: what is known, searched, asked, found, and the calls in flight."""

    plugins: list[EnricherPlugin]
    known: dict[str, str]
    queue: asyncio.Queue
    #: Code → the binding a seed gives that enricher, asked before anything else.
    seeded: dict[str, EnricherBinding] = field(default_factory=dict)
    #: Identifiers tried only after the known ones (the asset's ticker a seed's put behind, R6).
    fallback: list[tuple[str, str]] = field(default_factory=list)
    asked: set[tuple[str, str, str]] = field(default_factory=set)
    found: set[str] = field(default_factory=set)
    stopped: set[str] = field(default_factory=set)
    busy: set[str] = field(default_factory=set)
    tasks: set[asyncio.Task] = field(default_factory=set)

    def _strongest_first(self) -> list[tuple[str, str]]:
        """The known identifiers, strong types first, each group in the order it became known."""
        return sorted(self.known.items(), key=lambda item: item[0] not in STRONG_IDENTIFIER_TYPES)

    def ask_next(self) -> None:
        """Ask every enricher not found, not stopped and not busy with the strongest known identifier it accepts and was
        not asked with: after a clean «not found» the next one is tried, until one finds."""
        ordered = self._strongest_first() + [item for item in self.fallback if self.known.get(item[0]) != item[1]]
        for plugin in self.plugins:
            if plugin.code in self.found or plugin.code in self.stopped or plugin.code in self.busy:
                continue
            seed = self.seeded.get(plugin.code)
            if seed is not None and (plugin.code, seed.identifier_type, seed.identifier) not in self.asked:
                self.asked.add((plugin.code, seed.identifier_type, seed.identifier))
                self.busy.add(plugin.code)
                task = asyncio.create_task(self._call(plugin, seed))
                self.tasks.add(task)
                task.add_done_callback(self.tasks.discard)
                continue
            for kind, value in ordered:
                if kind in plugin.accepted_identifier_types and (plugin.code, kind, value) not in self.asked:
                    self.asked.add((plugin.code, kind, value))
                    self.busy.add(plugin.code)
                    task = asyncio.create_task(self._call(plugin, EnricherBinding(identifier_type=kind, identifier=value)))
                    self.tasks.add(task)
                    task.add_done_callback(self.tasks.discard)
                    break

    async def _call(self, plugin: EnricherPlugin, binding: EnricherBinding) -> None:
        """One «recognize» in a worker thread; its answer, or its failure, goes to the queue in the order they end."""
        try:
            # Counted on the account the enricher shares (CoinGecko); a full limit is this enricher's «error» answer
            await count_shared_call(plugin)
            answer: EnricherRecognition | BaseException = await asyncio.to_thread(plugin.recognize, binding)
        except Exception as error:  # noqa: BLE001 — isolation boundary: a plugin that fails is one «error» answer
            logger.warning("Enricher recognize failed", enricher=plugin.code, identifier_type=binding.identifier_type, exc_info=error)
            answer = error
        await self.queue.put((plugin, binding, answer))

    def judge(self, plugin: EnricherPlugin, binding: EnricherBinding, answer: EnricherRecognition | BaseException) -> list[Recognized | IdentifierLearned]:
        """The events of one answer; a strong identifier learned joins the known ones."""
        self.busy.discard(plugin.code)
        if isinstance(answer, BaseException):
            # An error (a site down, a refusal for too many requests) stops this enricher: never one more call for it
            self.stopped.add(plugin.code)
            return [Recognized(code=plugin.code, binding=binding, status=RecognizeStatus.ERROR, error=f"{type(answer).__name__}: {answer}")]
        if not answer.found:
            return [Recognized(code=plugin.code, binding=binding, status=RecognizeStatus.NOT_FOUND)]
        named = {str(kind).upper(): str(value) for kind, value in (answer.identifiers or {}).items() if value}
        strong = {kind: value for kind, value in named.items() if kind in STRONG_IDENTIFIER_TYPES}
        conflicts = {kind: value for kind, value in strong.items() if kind in self.known and self.known[kind] != value}
        status = RecognizeStatus.CONFLICT if conflicts else RecognizeStatus.FOUND
        events: list[Recognized | IdentifierLearned] = [Recognized(code=plugin.code, binding=binding, status=status, name=answer.name, page_url=answer.page_url, identifiers=named, conflicts=conflicts)]
        if conflicts:
            return events
        self.found.add(plugin.code)
        for kind, value in strong.items():
            if kind not in self.known:
                self.known[kind] = value
                events.append(IdentifierLearned(identifier_type=kind, identifier=value, source=plugin.code))
        return events


def _seed_binding(plugin: EnricherPlugin, seed: Seed) -> EnricherBinding:
    """The seed as ``plugin``'s binding: its type and identifier, and only the parameters the plugin declares."""
    declared = {str(entry.get("key")) for entry in plugin.params_schema if isinstance(entry, Mapping)}
    params = {key: value for key, value in seed.binding.params.items() if key in declared}
    return EnricherBinding(identifier_type=seed.binding.identifier_type, identifier=seed.binding.identifier, params=params)


def _plant_seeds(cascade: _Cascade, seeds: Sequence[Seed]) -> list[Recognized]:
    """Put the seeds in the cascade (see the module docstring); the conflicts they make, as answers."""
    by_code = {plugin.code: plugin for plugin in cascade.plugins}
    conflicts: list[Recognized] = []
    for seed in seeds:
        kind = str(seed.binding.identifier_type).strip().upper()
        value = str(seed.binding.identifier).strip()
        if not kind or not value:
            continue
        binding = EnricherBinding(identifier_type=kind, identifier=value, params=dict(seed.binding.params))
        plugin = by_code.get(seed.code)
        current = cascade.known.get(kind)
        if kind in STRONG_IDENTIFIER_TYPES and current is not None and current != value:
            if plugin is not None and plugin.code not in cascade.stopped:
                cascade.stopped.add(plugin.code)
                conflicts.append(Recognized(code=plugin.code, binding=_seed_binding(plugin, Seed(seed.code, binding)), status=RecognizeStatus.CONFLICT, conflicts={kind: value}))
            continue
        if current is not None and current != value:
            cascade.fallback.append((kind, current))
        cascade.known[kind] = value
        if plugin is not None and kind in plugin.accepted_identifier_types and plugin.code not in cascade.seeded:
            cascade.seeded[plugin.code] = _seed_binding(plugin, Seed(seed.code, binding))
    return conflicts


async def recognize_cascade(asset_type: AssetType, identifiers: Mapping[str, str], *, plugins: Sequence[EnricherPlugin] | None = None, seeds: Sequence[Seed] = ()) -> AsyncIterator[Recognized | IdentifierLearned]:
    """The cascade from ``identifiers`` (type → value) and ``seeds`` (ENR-2) over ``plugins`` (the installed enrichers
    when None), its events as they happen."""
    covering = [plugin for plugin in (installed_enrichers() if plugins is None else plugins) if plugin.covers(asset_type)]
    known = {str(kind).strip().upper(): str(value).strip() for kind, value in identifiers.items() if str(value).strip()}
    cascade = _Cascade(plugins=covering, known=known, queue=asyncio.Queue())
    for conflict in _plant_seeds(cascade, seeds):
        yield conflict
    cascade.ask_next()
    try:
        while cascade.busy:
            plugin, binding, answer = await cascade.queue.get()
            for event in cascade.judge(plugin, binding, answer):
                yield event
            cascade.ask_next()
    finally:
        # A reader that stops early: drop the calls still in flight (their threads end on their own)
        for task in list(cascade.tasks):
            task.cancel()
