"""
Broker Report Import Manager (BRIM) - the plugin contract.

This module is the contract every broker report import plugin builds on:
- BRIMProvider: Abstract base class for broker report import plugins
- BRIMParseError, BRIMCannotParseError, BRIMSetRequiredError: what a plugin raises
- TEXT_ENCODINGS: the encodings tried when a broker export is read as text

The rest of the BRIM service lives beside it, one module per theme (W4/CP7): ``storage`` (uploaded files, sidecars,
the per-broker lock), ``combined_files`` (the merged CSV of a report set), ``parsing`` (plugin check and parse),
``candidates`` (asset search) and ``duplicates`` (duplicate detection). Plugins are auto-discovered from the
``brim_providers/`` folder by ``registry.BRIMProviderRegistry``.

**Flow:**
    UPLOADED → parse → PARSED (success) or FAILED (error)
    After parsing, the user reviews and imports via POST /transactions.
"""

from __future__ import annotations

import csv
import io
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import structlog
from pydantic import ValidationError

from backend.app.schemas.brim import (
    BRIMCombinedTable,
    BRIMMemberSummary,
    BRIMParseOutput,
    BRIMPluginInfo,
    BRIMRefusal,
    BRIMReportRole,
    BRIMSetShape,
    BRIMValidationIssue,
)
from backend.app.schemas.transactions.transactions import TXCreateItem
from backend.app.services.plugin_settings.contract import PluginSettingsMixin
from backend.app.utils.pydantic_errors import error_params, loc_to_field

logger = structlog.get_logger(__name__)

# Encodings tried, in order, whenever a broker export is read as text. UTF-8 (with or
# without BOM) first; then Windows-1252, which Excel on Windows and many banks write;
# Latin-1 last, because it decodes any byte sequence and so always succeeds.
TEXT_ENCODINGS: Tuple[str, ...] = ("utf-8-sig", "cp1252", "latin-1")

# =============================================================================
# EXCEPTIONS
# =============================================================================


class BRIMParseError(Exception):
    """Raised when a file cannot be parsed by a plugin."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}


class BRIMCannotParseError(ValueError):
    """The parse guard refused the file: the plugin's ``can_parse`` said no (C-70b).

    A ``ValueError``, as before, with the same English sentence as its message. It also carries what the API needs to
    answer in a form the wizard translates: the plugin's code and name, and its refusal (``cannot_parse_detail``) as a plain
    dict, never ``None`` fields apart. The attributes travel in ``__dict__``, so it survives the trip from a parse worker.
    """

    def __init__(self, message: str, *, plugin_code: str = "", plugin_name: str = "", refusal: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.plugin_code = plugin_code
        self.plugin_name = plugin_name
        self.refusal = refusal


class BRIMSetRequiredError(BRIMParseError):
    """Raised when a report-set member is parsed on its own instead of through its combined file."""

    def __init__(self, message: str, missing_roles: Optional[List[str]] = None, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, details)
        self.missing_roles: List[str] = list(missing_roles or [])


# =============================================================================
# ABSTRACT BASE CLASS
# =============================================================================


class BRIMProvider(PluginSettingsMixin, ABC):
    """
    Abstract base class for broker report import plugins.

    Each plugin is responsible for parsing a specific broker's file format
    and converting it to a list of TXCreateItem DTOs.

    Plugins are auto-discovered from `brim_providers/` folder when the
    registry is first accessed.

    **Plugin Responsibilities:**
    - Parse broker-specific file formats (CSV, XLSX, PDF, etc.)
    - Convert parsed data to standard TXCreateItem DTOs
    - Return warnings for skipped/ambiguous rows
    - Handle date format variations
    - Map broker-specific transaction types to TransactionType enum

    **Core Responsibilities (not in plugin):**
    - File storage and management
    - Final import via TransactionService.create_bulk()
    - Database persistence

    Example:
        @register_provider(BRIMProviderRegistry)
        class DirectaCSVProvider(BRIMProvider):
            @property
            def provider_code(self) -> str:
                return "directa_csv"
            # ... implement other methods
    """

    @property
    @abstractmethod
    def provider_code(self) -> str:
        """
        Unique plugin identifier.

        Used in database, API, and for plugin selection.
        Must be lowercase alphanumeric with underscores.

        Examples: 'broker_generic_csv', 'directa_csv', 'degiro_xlsx'
        """

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """
        Human-readable plugin name for UI display.

        Examples: 'Generic CSV', 'Directa CSV Export', 'Degiro XLSX'
        """

    @property
    @abstractmethod
    def description(self) -> str:
        """
        Plugin description for UI display.

        Should explain what file formats are supported and any limitations.
        """

    @property
    def supported_extensions(self) -> List[str]:  # pragma: no cover
        """
        List of supported file extensions (lowercase, with dot).

        Default: ['.csv']
        Override if plugin supports other formats.

        Examples: ['.csv'], ['.csv', '.xlsx'], ['.pdf']
        """
        return [".csv"]

    @property
    def detection_priority(self) -> int:  # pragma: no cover
        """
        Priority for auto-detection (higher = checked first).

        Used when iterating plugins to find one that can parse a file.
        Higher priority plugins are checked before lower priority ones.

        Suggested ranges:
        - 100+: Broker-specific plugins with unique headers
        - 50-99: Semi-generic plugins
        - 0-49: Generic fallback plugins (e.g., broker_generic_csv)

        Default: 100 (broker-specific plugins)
        """
        return 100

    @staticmethod
    def _read_file_head(file_path: Path, num_lines: int = 15) -> str:
        """
        Read the first N lines of a file with encoding fallback.

        Tries ``TEXT_ENCODINGS`` in order: UTF-8 (with or without BOM), then
        Windows-1252, then Latin-1. Line endings are normalised to LF, as in any
        text-mode read.

        Args:
            file_path: Path to the file
            num_lines: Number of lines to read (default 15)

        Returns:
            String containing the first N lines, empty string on error
        """
        for encoding in TEXT_ENCODINGS:
            try:
                with open(file_path, encoding=encoding) as f:
                    lines = []
                    for _ in range(num_lines):
                        line = f.readline()
                        if not line:
                            break
                        lines.append(line)
                    return "".join(lines)
            except (UnicodeDecodeError, UnicodeError):
                continue
            except Exception:
                return ""

        return ""

    @staticmethod
    def _read_text(file_path: Path) -> str:
        """Read a whole text export, trying ``TEXT_ENCODINGS`` in order.

        Broker exports are not always UTF-8: a file produced by a European bank, or
        re-saved with Excel on Windows, is often Windows-1252 or Latin-1, and a UTF-8
        read fails on its first accented byte. The BOM, if any, is dropped; line
        endings are returned untouched.
        """
        raw = Path(file_path).read_bytes()
        for encoding in TEXT_ENCODINGS[:-1]:
            try:
                return raw.decode(encoding)
            except UnicodeDecodeError:
                continue
        return raw.decode(TEXT_ENCODINGS[-1])

    @staticmethod
    def _open_text(file_path: Path, *, newline: Optional[str] = None) -> io.StringIO:
        """Open a text export like ``open(file_path, encoding=...)``, with encoding fallback.

        Plugins use this instead of ``open()`` with a fixed encoding. The result is an
        in-memory stream that also works in a ``with`` block. The default
        ``newline=None`` normalises CRLF and CR to LF exactly like a text-mode
        ``open``; pass ``newline=""`` to keep line endings for the ``csv`` module.
        """
        return io.StringIO(BRIMProvider._read_text(file_path), newline=newline)

    @property
    def icon_url(self) -> Optional[str]:
        """
        URL to the broker's icon/logo.

        Override in subclass to provide broker-specific icon.
        Can be:
        - Absolute URL (https://...)
        - Relative path served by backend (e.g., /static/icons/broker_xxx.png)
        - Local static path via generate_static_url()
        - None if no icon available

        Default: None
        """
        return None

    @classmethod
    def generate_static_url(cls, relative_path: str) -> str:
        """
        Generate URL for a static asset in the plugin's static folder.

        Use this to reference icons, images, or other static files
        bundled with your plugin.

        Structure:
            brim_providers/{plugin folder}/static/{file}   (relative_path: "{plugin folder}/{file}")

        Args:
            relative_path: The plugin's folder and the file in its ``static/`` folder (e.g., "broker_directa/logo.png")

        Returns:
            Full URL path (e.g., "/api/v1/uploads/plugin/brim/broker_directa/logo.png")

        Example:
            class DirectaCSVProvider(BRIMProvider):
                @property
                def icon_url(self) -> str:
                    return self.generate_static_url("broker_directa/logo.png")
        """
        return f"/api/v1/uploads/plugin/brim/{relative_path}"

    @abstractmethod
    def can_parse(self, file_path: Path) -> bool:
        """
        Check if this plugin can parse the given file.

        Should perform a quick check (e.g., extension, header row)
        without full parsing. Used to determine compatible plugins
        for a file.

        Args:
            file_path: Path to the file to check

        Returns:
            True if this plugin can likely parse the file
        """

    def cannot_parse_reason(self, file_path: Path) -> Optional[str]:
        """
        Why ``can_parse`` refuses this file, in one short sentence the user can act on.

        Called only by the parse guard, after ``can_parse`` answered False for a file the
        user chose this plugin for: the sentence completes the "cannot parse file" error
        (lowercase start, no final period, e.g. "required column 'date' not found in the
        CSV header"). Override it when the refusal has a cause the user can fix in the
        file. Keep it as cheap as ``can_parse`` and never raise.

        Returns:
            The reason, or None when there is nothing to add (the default)
        """
        return None

    def cannot_parse_detail(self, file_path: Path) -> Optional[BRIMRefusal]:
        """Why ``can_parse`` refuses this file, with a code the frontend can translate.

        The import wizard asks it right after an upload, through ``GET
        /import/files/{file_id}/plugin-check``: when the broker's default plugin refuses the
        file, the wizard shows this reason next to the plugin and the broker that read it.

        The default wraps ``cannot_parse_reason`` with no code, so every plugin answers
        without changes. Override it to give a stable snake_case ``code``, translated as
        ``importWizard.parseRefusal.<code>``, and its ``context``; ``message`` stays the
        English fallback and must be what ``cannot_parse_reason`` returns. Same rules as
        ``cannot_parse_reason``: as cheap as ``can_parse``, and never raise.

        Returns:
            The refusal, or None when there is nothing to add
        """
        reason = self.cannot_parse_reason(file_path)
        return BRIMRefusal(message=reason) if reason else None

    @abstractmethod
    def parse(self, file_path: Path, broker_id: int) -> BRIMParseOutput:
        """
        Parse file and return a ``BRIMParseOutput`` with transactions, warnings,
        extracted assets and optional asset-level events.

        **Plugin Responsibility:**
        - Read the broker-specific file format
        - Create TXCreateItem DTOs with fake_asset_ids for asset-linked transactions
        - Extract asset identifiers (symbol, ISIN, name) from the file
        - Group same-asset transactions under the same fake_asset_id
        - Collect warnings for skipped/problematic rows
        - Optionally populate ``asset_events`` for plugins that extract
          asset-level events (e.g. dividends in IBKR / Schwab reports)

        **Core Responsibility (NOT plugin):**
        - Search DB for asset candidates using extracted info
        - Map fake_asset_ids to real asset_ids
        - Detect duplicate transactions

        Args:
            file_path: Path to the file to parse
            broker_id: Target broker ID for all transactions

        Returns:
            BRIMParseOutput with:
              - transactions: List[TXCreateItem] (with fake asset IDs)
              - warnings: List[str]
              - extracted_assets: Dict[int, BRIMExtractedAssetInfo]

        Raises:
            BRIMParseError: If file cannot be parsed
        """

    @property
    def docs_url(self) -> Optional[str]:
        """URL to the plugin's documentation page. Default: None.

        Override in subclasses to provide a user-facing doc link, e.g.
        to the MkDocs page describing the expected file format.
        """
        return None

    @property
    def plugin_version(self) -> str:
        """Semver of the parsing logic. Default: "1.0.0".

        **Contract:** bump this string whenever the plugin's output for
        the same input would change (new columns, different row
        filtering, fixed bug in type detection, etc.). The frontend
        compares this value with ``BRIMFileInfo.parsed_plugin_version``
        to surface a "re-parse available" hint for files whose cached
        parse was produced by an older version.
        """
        return "1.0.0"

    @property
    def test_file_pattern(self) -> Optional[str]:
        """
        Filename contain pattern for auto-detection tests.
        Using for test with backend/app/services/brim_providers/<plugin>/sample_reports/* files

        Override this to specify what filename substring should auto-detect
        to this plugin. Used only for testing purposes.

        Example: "directa" for broker_directa plugin
        Returns None if no test pattern (e.g., generic fallback plugin).

        For plugins that own several export formats (e.g. Revolut invest + crypto),
        prefer overriding :attr:`test_file_patterns` with the full list.
        """
        return None

    @property
    def test_file_patterns(self) -> List[str]:
        """Filename substrings for **every** sample this plugin owns.

        A single plugin can handle several export layouts of the same broker
        (variant detected by header inside :meth:`can_parse` / :meth:`parse`).
        Register one sample per variant in ``sample_reports/`` and list each
        filename substring here so the test suite exercises them all.

        Default: derives from the single-value :attr:`test_file_pattern` shim,
        so existing plugins keep working without changes. Returns ``[]`` when
        neither is set (e.g. the generic fallback plugin).

        Example: ``["revolut-invest", "revolut-crypto"]``.
        """
        single = self.test_file_pattern
        return [single] if single else []

    @property
    def test_sample_sets(self) -> List[Dict[str, List[str]]]:
        """Sample report sets for the test suite, one ``{role: [sample file names]}`` per set.

        Only a report-set plugin declares them: its members are never parsed alone, so the
        generic suite combines each set and parses the combined file. The names refer to
        ``sample_reports/``. Default: ``[]``.
        """
        return []

    # -------------------------------------------------------------------------
    # Report sets (multi-file imports). Every default keeps a plugin single-file.
    # -------------------------------------------------------------------------

    @property
    def report_roles(self) -> List[BRIMReportRole]:
        """Export roles this plugin combines. Default: ``[]`` (single-file plugin)."""
        return []

    @property
    def is_report_set_plugin(self) -> bool:
        """True when the plugin combines several exports into one import."""
        return bool(self.report_roles)

    def detect_role(self, file_path: Path) -> Optional[str]:
        """Role of ``file_path`` in a report set, or None. Default: None."""
        return None

    def describe_member(self, file_path: Path) -> BRIMMemberSummary:
        """Role, rows and coverage of one member, read without combining."""
        raise NotImplementedError(f"{self.provider_code} is not a report-set plugin")

    def describe_set(self, members: Dict[str, List[Path]]) -> BRIMSetShape:
        """Segments, proven gaps and notices of a set, read without combining."""
        raise NotImplementedError(f"{self.provider_code} is not a report-set plugin")

    def combine(self, members: Dict[str, List[Path]]) -> BRIMCombinedTable:
        """Build the combined table from the members, grouped by role.

        Must be a pure function of the members and of the plugin version: it never
        reads the database, so the same set always yields the same combined file.
        """
        raise NotImplementedError(f"{self.provider_code} is not a report-set plugin")

    @property
    def settlement_lag_business_days(self) -> int:
        """Longest settlement delay between an operation and its cash movement. Default: 0."""
        return 0

    @property
    def pre_checkpoint_policy(self) -> str:
        """What happens to rows before the first checkpoint: ``summarize`` (default) or ``import``."""
        return "summarize"

    @property
    def history_tag(self) -> str:
        """Tag this plugin puts on its transactions; the report sets use it to find the broker history.

        Default: the provider code without its ``broker_`` prefix (``broker_credit_agricole`` becomes
        ``credit_agricole``), which is the tag the existing plugins already write.
        """
        return self.provider_code.removeprefix("broker_")

    def to_plugin_info(self) -> BRIMPluginInfo:
        """Convert provider to BRIMPluginInfo DTO."""
        return BRIMPluginInfo(
            code=self.provider_code,
            name=self.provider_name,
            description=self.description,
            supported_extensions=self.supported_extensions,
            icon_url=self.icon_url,
            docs_url=self.docs_url,
            plugin_version=self.plugin_version,
            detection_priority=self.detection_priority,
            report_roles=self.report_roles,
        )

    # -------------------------------------------------------------------------
    # Transaction construction helpers (parent responsibility)
    # -------------------------------------------------------------------------

    def _create_transaction(
        self,
        row_num: int,
        transactions: List[TXCreateItem],
        validation_issues: List[BRIMValidationIssue],
        context: Optional[str] = None,
        **kwargs,
    ) -> Optional[TXCreateItem]:
        """Create a TXCreateItem, catching ValidationErrors as structured issues.

        On success: appends to ``transactions`` and returns the item.
        On ValidationError: extracts structured issues from Pydantic, appends to
        ``validation_issues``, and returns None. Each issue carries the error's code,
        message and field, and its plain context as ``params`` (``error_params``,
        the transaction batch's rule: W-B72, W-B75, W-B70).

        Plugins should call this instead of ``TXCreateItem(...)`` directly so that
        the parent class owns the error-handling contract and the frontend receives
        structured, localizable validation messages.
        """
        try:
            tx = TXCreateItem(**kwargs)
            transactions.append(tx)
            return tx
        except ValidationError as e:
            for err in e.errors():
                err_type = err.get("type", "unknown")
                err_ctx = err.get("ctx") or {}
                # Unpack multipleBusinessRuleErrors into individual issues
                if err_type == "multipleBusinessRuleErrors" and "errors" in err_ctx:
                    for sub_err in err_ctx["errors"]:
                        validation_issues.append(
                            BRIMValidationIssue(
                                row=row_num,
                                code=sub_err.get("code", "unknown"),
                                message=sub_err.get("msg", ""),
                                params=error_params(sub_err),
                                context=context,
                            )
                        )
                else:
                    validation_issues.append(
                        BRIMValidationIssue(
                            row=row_num,
                            code=err_type,
                            message=err.get("msg", str(e)),
                            field=loc_to_field(err.get("loc", ())),
                            params=error_params(err),
                            context=context,
                        )
                    )
            return None
        except Exception as exc:
            # Non-validation errors (shouldn't happen, but safety net)
            validation_issues.append(
                BRIMValidationIssue(
                    row=row_num,
                    code="unexpected_error",
                    message=str(exc),
                    context=context,
                )
            )
            return None

    def shutdown(self) -> None:  # pragma: no cover  # noqa: B027 — intentional no-op default
        """
        Cleanup resources on application shutdown.

        Override to release persistent connections, stop background threads,
        flush caches, etc.  Called once per provider during app lifespan teardown
        via ``BRIMProviderRegistry.shutdown_all_providers()``.

        Default: no-op.
        """

    @staticmethod
    def detect_csv_delimiter(file_path: Path, lines_to_read: int = 15) -> str:
        """Sniff the delimiter used in a CSV file.

        The head is read with the same encoding fallback as ``_open_text``. A plain
        UTF-8 read used to fail on a Windows-1252 or Latin-1 export, leave the
        sample empty and answer ``,`` for a ``;``-separated file.

        Uses ``csv.Sniffer`` which handles quoted fields correctly.
        Falls back to counting raw characters when sniffing fails.
        """
        sample = BRIMProvider._read_file_head(file_path, num_lines=lines_to_read)
        try:
            dialect = csv.Sniffer().sniff(sample, delimiters=[",", ";", "\t"])
            return dialect.delimiter
        except Exception:
            comma_count = sample.count(",")
            semi_count = sample.count(";")
            return ";" if semi_count > comma_count else ","
