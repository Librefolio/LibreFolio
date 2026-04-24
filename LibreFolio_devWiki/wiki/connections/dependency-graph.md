# Dependency Graph — Full Project

> Cross-domain view of feature dependencies. Shows which features must exist before others can be built.
> Read [[features/registry]] for feature descriptions.
> Last updated: 2026-05-13
> F-075–F-095 range (21 planned/idea features) is now tracked in the registry. Inverse `enables:` links from their dependencies have been populated.

---

## Top-Level Phase Dependencies

```mermaid
graph TD
  subgraph "Phase 0-3 ✅"
    F001[F-001 Auth]
    F003[F-003 Roles]
    F004[F-004 App Shell]
    F065[F-065 JWT Auth]
    F008[F-008 i18n]
  end

  subgraph "Phase 4 ✅"
    F009[F-009 Brokers]
    F010[F-010 Broker Sharing]
    F011[F-011 Files]
    F012[F-012 BRIM Framework]
    F013[F-013 BRIM Plugins]
  end

  subgraph "Phase 5 ✅"
    F015[F-015 FX Providers]
    F016[F-016 FX Pairs]
    F017[F-017 FX Sync]
    F020[F-020 FX Conversion]
    F037[F-037 Signal Library]
  end

  subgraph "Phase 6 ✅"
    F024[F-024 Assets]
    F025[F-025 Asset Providers]
    F031[F-031 Asset Events]
    F033[F-033 Asset Detail]
  end

  subgraph "Phase 7 🔄"
    F046[F-046 Transaction API]
    F047[F-047 TX List Page]
    F049[F-049 BRIM Import UI]
    F051[F-051 TX↔AssetEvent]
  end

  subgraph "Phase 8-9 📋"
    F052[F-052 Scheduler]
    F054[F-054 Dashboard]
    F056[F-056 FIFO]
  end

  subgraph "Phase 10+ — Planned/Ideas 📋"
    F075[F-075 TanStack Table v9]
    F081[F-081 Fiscal Sale Method]
    F083[F-083 Multi-File Import]
    F085[F-085 QuarkAI Assistant]
    F090[F-090 AssetEvent↔TX Link]
    FREST[F-076…F-095 — 21 planned/idea features]
  end

  F001 --> F003
  F065 --> F001
  F003 --> F009
  F003 --> F010
  F009 --> F011
  F009 --> F012
  F012 --> F013
  F001 --> F015
  F015 --> F016
  F016 --> F017
  F017 --> F020
  F020 --> F057[F-057 Currency Conversion]
  F001 --> F024
  F020 --> F024
  F024 --> F025
  F025 --> F027[F-027 Asset Sync]
  F031 --> F051
  F012 --> F049
  F024 --> F049
  F009 --> F046
  F024 --> F046
  F010 --> F046
  F046 --> F047
  F046 --> F051
  F025 --> F052
  F046 --> F056
  F047 --> F054
  F055[F-055 Portfolio Charts] --> F054
  F057 --> F054
  F056 --> F054
```

---

## Critical Dependency Chains

### Auth → Everything
`F-065 JWT` → `F-001 Auth` → `F-003 Roles` → all domain features

All API endpoints are auth-protected. Role (admin/user) gates admin features.
Broker sharing role (Owner/Editor/Viewer) gates transaction write access.

### FX → Assets → Transactions → Dashboard
```
F-015 FX Providers → F-016 FX Pairs → F-017 Sync → F-020 Conversion Graph
                                                         ↓
F-024 Asset CRUD → F-025 Providers → F-027 Sync → F-030 Price History
                                                         ↓
F-046 Transaction API → F-056 FIFO → F-058 ROI → F-054 Dashboard
```

### BRIM → Transactions
```
F-012 BRIM Framework → F-013 Plugins → F-049 BRIM Import UI
                                            ↓
                    F-046 TX API (commit) → F-047 TX List Page
```

### Asset Events cross-dependency
```
F-031 Asset Events ←─── Phase 6 (DIVIDEND, SPLIT recorded)
         ↓
F-051 TX↔AssetEvent Link ─── Phase 7 (link transactions to events)
         ↓
F-054 Dashboard (accurate income tracking)
```

---

## Cross-Layer Handoffs (Backend → Frontend)

| Backend Feature | Interface | Frontend Feature |
|----------------|-----------|-----------------|
| [[F-015]] FX Providers | `GET /api/v1/fx/providers` | [[F-016]] FX Pair Add Modal |
| [[F-017]] FX Rate Sync | `POST /api/v1/fx/sync` | [[F-021]] FX List → sync button |
| [[F-020]] FX Conversion | `GET /api/v1/fx/conversion-route` | [[F-057]] used in Asset prices |
| [[F-025]] Asset Providers | `GET /api/v1/assets/provider/list` | [[F-026]] Provider Assignment form |
| [[F-027]] Asset Sync | `POST /api/v1/assets/{id}/sync` | [[F-033]] Asset Detail → sync |
| [[F-031]] Asset Events | `GET /api/v1/assets/{id}/events` | [[F-033]] Event markers on chart |
| [[F-046]] TX Bulk API | `POST /api/v1/transactions/bulk` | [[F-048]] Staging Modal commit |
| [[F-013]] BRIM Plugins | `POST /api/v1/brokers/import/files/{id}/parse` | [[F-049]] BRIM Import UI |
| [[F-056]] FIFO | (embedded in portfolio endpoint) | [[F-054]] Dashboard KPI |
| [[F-052]] Scheduler | `GET/POST /api/v1/settings/global` | [[F-053]] Scheduler Settings UI |

## Key source files

| Role | Path |
|------|------|
| Feature registry | `LibreFolio_devWiki/wiki/features/registry.md` |
| All API endpoints | `backend/app/api/v1/` |
| All services | `backend/app/services/` |
| All frontend routes | `frontend/src/routes/(app)/` |
