# 📦 BRIM Plugin Guide

How to create a new **Broker Report Import Manager** plugin to support a new broker's CSV/Excel export format.

**Base class**: `BRIMProvider` (in `backend/app/services/brim_provider.py`)
**Plugin folder**: `backend/app/services/brim_providers/`
**Registry**: `BRIMProviderRegistry`

---

## 🔄 Flow

The system calls plugin methods in two distinct phases:

```mermaid
graph TD
    subgraph "Phase 1 — Detection (file uploaded)"
        D1["File uploaded"] --> D2["can_parse(file_path)<br/><small>Quick header/extension check</small>"]
        D2 -->|true| D3["Plugin listed as<br/>compatible option"]
        D2 -->|false| D4["Skip"]
    end

    subgraph "Phase 2 — Parsing (user selects plugin)"
        P1["parse(file_path, broker_id)<br/><small>Full parsing</small>"] --> P2["Returns:<br/>• BRIMParseOutput"]
        P2 --> P3["User reviews<br/>in preview UI"]
        P3 --> P4["POST /transactions<br/><small>Core handles persist</small>"]
    end

    D3 ~~~ P1

    style D1 fill:#e3f2fd,stroke:#1565c0
    style D2 fill:#e3f2fd,stroke:#1565c0
    style D3 fill:#e3f2fd,stroke:#1565c0
    style P1 fill:#e8f5e9,stroke:#2e7d32
    style P2 fill:#fff3e0,stroke:#e65100
    style P3 fill:#fff3e0,stroke:#e65100
    style P4 fill:#f3e5f5,stroke:#7b1fa2
```

**Phase 1** runs automatically when a file is uploaded — every registered plugin is asked if it can parse the file. Compatible plugins are listed for the user.

**Phase 2** runs when the user selects a specific plugin — the plugin parses the file, the user reviews the results, and confirms the import.

**Plugin responsibility**: Read the broker-specific file format and convert to standard `TXCreateItem` DTOs.
**Core responsibility**: File storage, asset matching, duplicate detection, database persistence.

---

## 📋 ABC Methods

### ✅ Required (Abstract)

| Method | Signature | Description |
|--------|-----------|-------------|
| `provider_code` | `@property → str` | Unique identifier (e.g., `"directa_csv"`) |
| `provider_name` | `@property → str` | Display name (e.g., `"Directa CSV"`) |
| `description` | `@property → str` | Brief description for the UI |
| `can_parse(file_path)` | `→ bool` | Quick check if this plugin can parse the file (check extension, header row) |
| `parse(file_path, broker_id)` | `→ BRIMParseOutput` | Full parsing — returns structured BRIMParseOutput object containing transactions, warnings, and extracted asset info |

### 🔧 Optional (Override)

| Method | Default | Description |
|--------|---------|-------------|
| `supported_extensions` | `['.csv']` | Accepted file extensions |
| `detection_priority` | `100` | Auto-detection priority (higher = checked first). Use 0-49 for generic plugins. |
| `icon_url` | `None` | Plugin icon URL for the UI |
| `generate_static_url(path)` | — | Helper to build `/api/v1/uploads/plugin/brim/{path}` |

---

## 💻 Implementation Example

```python
# backend/app/services/brim_providers/my_broker.py

from pathlib import Path
from backend.app.services.brim_provider import BRIMProvider
from backend.app.services.provider_registry import register_provider, BRIMProviderRegistry
from backend.app.schemas.brim import BRIMExtractedAssetInfo, BRIMParseOutput
from backend.app.schemas.transactions import TXCreateItem

@register_provider(BRIMProviderRegistry)
class MyBrokerProvider(BRIMProvider):

    @property
    def provider_code(self) -> str:
        return "my_broker_csv"

    @property
    def provider_name(self) -> str:
        return "My Broker (CSV)"

    @property
    def description(self) -> str:
        return "Import transactions from My Broker CSV exports"

    def can_parse(self, file_path: Path) -> bool:
        """Quick check: read first lines and look for known header."""
        content = self._read_file_head(file_path, num_lines=5)
        return "Date;Operation;ISIN;Amount" in content

    def parse(self, file_path: Path, broker_id: int) -> BRIMParseOutput:
        """Parse the CSV and return transactions in a BRIMParseOutput envelope."""
        transactions = []
        warnings = []
        extracted_assets = {}

        # ... your parsing logic ...

        return BRIMParseOutput(
            transactions=transactions,
            warnings=warnings,
            extracted_assets={
                fake_id: BRIMExtractedAssetInfo(
                    extracted_symbol=info["extracted_symbol"],
                    extracted_isin=info["extracted_isin"],
                    extracted_name=info["extracted_name"],
                )
                for fake_id, info in extracted_assets.items()
            }
        )
```

### 🔍 Auto-Discovery

Place the file in `brim_providers/` and restart the app. The `BRIMProviderRegistry` will automatically discover and register it. The plugin will appear in the [ImportPluginSelect](../../frontend/components/select.md#importpluginselect) dropdown.

---

## 🔗 Related Documentation

- [BRIM Architecture](../../backend/brim/architecture.md) — Full pipeline design
- [Generic CSV Provider](../../backend/brim/generic_csv.md) — User-configurable CSV mapper (reference implementation)
- [Providers List](../../backend/brim/providers_list.md) — All supported brokers
- [Registry Pattern Overview](registry_pattern.md) — How the plugin system works

