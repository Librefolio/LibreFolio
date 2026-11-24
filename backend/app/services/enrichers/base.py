"""The contract of an enricher (plan 68, §3.3): a plugin that reads the profile of an asset from one outside source.

An enricher is a family of its own, beside the price providers (``services/assets/base.py``). A plugin lives in
``services/enricher_providers/<name>/plugin.py`` and registers with ``@register_provider(EnricherRegistry)``.

What it declares, on the class:

- ``code`` and ``name``; ``icon`` and ``help_url`` (optional); ``terms``, the class of the source's terms of use, shown
  to the user (plan §12: never a legal opinion);
- ``settings_fields``, when it needs keys (``PluginSettingsMixin``); the first four enrichers need none;
- ``accepted_identifier_types``, and ``params_schema`` for the extra parameters of a binding (the frontend draws the
  form from it, as for the price providers);
- ``voices``: per asset type, the profile voices it can fill (catalogue keys);
- ``default_priority``: a degree for **every** ``AssetType``, ``None`` written out for a type it does not cover. The
  default order of the enrichers of an asset follows it, lower first.

No site and no pause between calls: the queue of its calls and the wait between them are the plugin's own, inside
``read`` (plan, round 30).

What it does: ``recognize`` one binding (does the source know it, how does it name it, which other identifiers does it
know); ``read`` a list of bindings, yielding one item per binding as it goes; ``page_url`` of a binding; ``search``
(optional) by a word. They are plain blocking calls: the core runs them away from the event loop.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterable, Iterator, Mapping
from dataclasses import dataclass, field
from datetime import date
from enum import StrEnum
from typing import Any, ClassVar

from backend.app.db.models import AssetType
from backend.app.services.plugin_settings.contract import PluginSettingsMixin
from backend.app.utils.runtime.cooldown import RateLimitedError

#: The identifier types strong enough to start another search in the cascade (plan §3.2, round 18).
STRONG_IDENTIFIER_TYPES: frozenset[str] = frozenset({"ISIN", "LEI"})

#: The error code of a read refused for too many requests: the one the scheduler knows (``scheduler/jobs.py``).
RATE_LIMITED = "RATE_LIMITED"


class EnricherRateLimited(RateLimitedError):
    """The source refused a call of the enricher for too many requests (a ``search``; ENR-3b).

    ``retry_after`` is the wait the source asked for, in seconds, None when it did not say. The enrichers' routes answer
    it with a 429 ``RATE_LIMITED`` and ``Retry-After``: a refusal is never an empty result. A plugin raises it from the
    library's error (``raise EnricherRateLimited(...) from error``) and never retries in its thread.
    """


class EnricherTerms(StrEnum):
    """The class of a source's terms of use, as the research classed them (``arricchitori-PROF.md`` §10).

    - ``open``: open or official data (a register, a free dataset): fine on any instance, the source cited;
    - ``price_source``: a source already read for prices, under restrictive terms the project already accepts;
    - ``self_hosted``: restrictive terms that allow personal use only: never on a hosted service;
    - ``personal_file``: a public file for personal use: off until the user turns it on, self-hosted only.
    """

    OPEN = "open"
    PRICE_SOURCE = "price_source"
    SELF_HOSTED = "self_hosted"
    PERSONAL_FILE = "personal_file"


@dataclass(frozen=True, slots=True)
class EnricherBinding:
    """How one enricher names one asset: the object stored under its code in ``asset_enrichers.config``.

    ``identifier_type`` and ``identifier`` are what every binding holds; ``params`` the rest of the object, which only
    that plugin reads (Borsa Italiana's ``mic`` and ``platform``, for instance).
    """

    identifier_type: str
    identifier: str
    params: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class EnricherSearchResult:
    """One result of ``search``: what the user picks from to fill a binding."""

    name: str
    binding: EnricherBinding
    asset_type: AssetType | None = None
    page_url: str | None = None


@dataclass(frozen=True, slots=True)
class EnricherRecognition:
    """The answer of ``recognize``: whether the source knows the binding, its name there, its page, and the other
    identifiers it knows (type → value: ``{"LEI": "…"}``), which may start the cascade (plan B4)."""

    found: bool
    name: str | None = None
    page_url: str | None = None
    identifiers: Mapping[str, str] = field(default_factory=dict)


class EnricherReadStatus(StrEnum):
    """The outcome of reading one binding."""

    OK = "ok"
    NOT_FOUND = "not_found"
    ERROR = "error"


@dataclass(frozen=True, slots=True)
class EnricherReadItem:
    """What ``read`` yields for one binding, in any order: ``index`` is its place in the list it was given.

    ``values`` maps catalogue keys to raw values (the catalogue turns them into stored forms); a voice the source does
    not give is absent, never ``None``. ``source_date`` is the day the source says its data are of, when it says one;
    ``source_dates`` the day of a voice that has one of its own (a fund's countries and sectors are «as of» their
    holdings date): a voice not in it takes ``source_date``.
    A refusal for too many requests is ``ERROR`` with ``error_code`` ``RATE_LIMITED`` and, when known, ``retry_after``
    in seconds: the reads not done yet come back that way, and the core reads them later.
    """

    index: int
    status: EnricherReadStatus
    values: Mapping[str, Any] = field(default_factory=dict)
    source_date: date | None = None
    source_dates: Mapping[str, date] = field(default_factory=dict)
    error_code: str | None = None
    error_message: str | None = None
    retry_after: float | None = None


class EnricherPlugin(PluginSettingsMixin, ABC):
    """The base of every enricher. A subclass sets the class attributes below and implements the abstract methods."""

    code: ClassVar[str]
    name: ClassVar[str]
    icon: ClassVar[str | None] = None
    help_url: ClassVar[str | None] = None
    terms: ClassVar[EnricherTerms]
    accepted_identifier_types: ClassVar[tuple[str, ...]]
    #: The voices it can fill, per asset type: a type it does not cover may be absent.
    voices: ClassVar[Mapping[AssetType, frozenset[str]]]
    #: A degree for every ``AssetType``, lower first; ``None`` for a type it does not cover.
    default_priority: ClassVar[Mapping[AssetType, int | None]]
    #: Whether the enricher reaches an external service (project 76, K1), as the asset and FX bases declare it: each
    #: binding it reads is then counted at the enrichers' boundary, and refused when an instance limit is full. False for
    #: an enricher that computes its answers itself, with no network (the test doubles): never counted.
    calls_external_service: ClassVar[bool] = True

    @property
    def params_schema(self) -> list[dict]:
        """The extra parameters of a binding, as the price providers describe theirs; none by default."""
        return []

    @property
    def supports_search(self) -> bool:
        """Whether ``search`` is implemented: true when the subclass overrides it."""
        return type(self).search is not EnricherPlugin.search

    def search(self, query: str) -> list[EnricherSearchResult]:
        """The assets the source finds for ``query``; optional. A refusal for too many requests raises
        ``EnricherRateLimited``, never an empty list (ENR-3b)."""
        raise NotImplementedError(f"{self.code} does not search")

    @abstractmethod
    def recognize(self, binding: EnricherBinding) -> EnricherRecognition:
        """Whether the source knows ``binding``; light, writes nothing."""

    @abstractmethod
    def read(self, bindings: list[EnricherBinding], keys: Iterable[str] | None = None) -> Iterator[EnricherReadItem]:
        """Read each binding, yielding one item per binding as it goes, each with its own outcome.

        ``keys`` are the voices asked (all when None): a plugin that reads everything with one page may ignore them; one
        for which a voice costs one more call uses them to skip it. The plugin paces its own calls.
        """

    @abstractmethod
    def page_url(self, binding: EnricherBinding) -> str | None:
        """The address of the page the user opens to check the source by eye."""

    @property
    @abstractmethod
    def test_cases(self) -> list[dict]:
        """The cases of the external suite: bindings the real source must recognize and read."""

    def covers(self, asset_type: AssetType) -> bool:
        """Whether it covers ``asset_type`` (a degree, not ``None``)."""
        return self.default_priority.get(asset_type) is not None

    def shutdown(self) -> None:  # noqa: B027 — intentional no-op default: a plugin with resources overrides it
        """Release what the plugin holds, at the server's shutdown."""
