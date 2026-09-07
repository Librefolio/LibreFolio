# 🔐 Broker Access Control (RBAC)

LibreFolio implements a granular **Role-Based Access Control (RBAC)** system for Brokers. This allows users to share access to their brokerage accounts with other users (e.g.,
family members, accountants) while maintaining control over permissions.

## 📖 Overview

Access is managed via the `BrokerUserAccess` table, which links a `User` to a `Broker` with a specific `UserRole`.

```mermaid
erDiagram
    USER ||--o{ BROKER_USER_ACCESS : "has access"
    BROKER ||--o{ BROKER_USER_ACCESS : "granted to"
    
    BROKER_USER_ACCESS {
        int user_id FK
        int broker_id FK
        enum role "OWNER, EDITOR, VIEWER"
        decimal share_percentage "0..1, OWNER-only, scales aggregation"
    }
```

## 🛡️ Roles and Permissions

There are three roles with increasing levels of privilege:

| Feature                              | VIEWER | EDITOR | OWNER |
|:-------------------------------------|:------:|:------:|:-----:|
| **View Broker Details**              |   ✅    |   ✅    |   ✅   |
| **View Transactions**                |   ✅    |   ✅    |   ✅   |
| **View Reports/Charts**              |   ✅    |   ✅    |   ✅   |
| **Add/Edit Transactions**            |   ❌    |   ✅    |   ✅   |
| **Import Files (BRIM)**              |   ❌    |   ✅    |   ✅   |
| **Edit Broker Settings**             |   ❌    |   ✅    |   ✅   |
| **Manage Access (Add/Remove Users)** |   ❌    |   ❌    |   ✅   |
| **Delete Broker**                    |   ❌    |   ❌    |   ✅   |

### 📋 Role Definitions

1. 👁️ **VIEWER**: Read-only access. Ideal for sharing portfolio visibility without risk of data modification.
2. ✏️ **EDITOR**: Operational access. Can manage the day-to-day data (transactions, imports) and broker settings (name, icon), but cannot perform destructive administrative actions (deleting the broker) or change who has access.
3. 👑 **OWNER**: Administrative access. Full control over the broker.

## 📏 Key Rules & Constraints

### 📊 Ownership share (`share_percentage`)

Each access row carries a `share_percentage` (0.000000–1.000000) used **only for portfolio
aggregation**, never for permissions:

- **OWNER** defaults to 1.00 and may be reduced for co-ownership (e.g. joint accounts);
  **EDITOR** and **VIEWER** default to 0.00 (delegated operator, read-only accountant).
- The sum of shares across a broker's users **must not exceed 1.00** (validated on add/update);
  it **can be less** (a co-owner may simply not be in the system).
- **0 % is a valid share**: a 0 % OWNER keeps full admin rights but contributes nothing to the
  owner's aggregated numbers.
- Aggregation scales by share **only for OWNERs** — EDITOR/VIEWER rows always carry share 0 by
  schema rule yet see full data, so the engine uses scale 1 for them
  (`portfolio_service.py`, `portfolio_engine.py`). Role/share edits change every scaled number
  but not the underlying data, so they also join the cache fingerprint for instant invalidation.

### 🔒 The "Last Owner" Rule

To prevent brokers from becoming "orphaned" (inaccessible by anyone with admin rights), the system enforces a strict rule:

> **The last OWNER of a broker cannot be removed or downgraded.**

If a broker has only one user with the `OWNER` role:

- ❌ That user **cannot** remove themselves.
- ❌ That user **cannot** change their role to `EDITOR` or `VIEWER`.
- ✅ To leave the broker, they must first promote another user to `OWNER` or delete the broker entirely.

### 🔧 Self-Management

- 🚪 **Leaving**: any user can remove *themselves* from a broker at any time (`leave_broker`).
  EDITOR/VIEWER always succeed. An OWNER may leave when at least one other OWNER remains —
  otherwise leaving as the **last OWNER deletes the broker entirely** (cascade over
  transactions; BRIM report files are cleaned up by the API layer).
- ⬇️ **Self-demotion** (`update_own_role`): EDITOR → VIEWER is always allowed; OWNER →
  EDITOR/VIEWER is allowed only when another OWNER remains, and demoting from OWNER **zeroes
  the share** (only OWNERs may hold share > 0). Promotions stay on the OWNER-only path.

## 🔧 Implementation Details

The logic is centralized in `backend/app/services/broker_service.py`.

- 🔍 **`_check_user_access(broker_id, user_id, min_role)`**: Core internal method to verify permissions.
- ➕ **`add_access()`**: Grants access to a new user (OWNER only).
- 🔄 **`update_access()`**: Changes an existing user's role (OWNER only).
- ❌ **`remove_access()`**: Revokes access (OWNER can remove anyone; others can only remove themselves).
- 🚪 **`leave_broker()`** / **`update_own_role()`**: The self-service paths described above.

### 🌐 API Endpoints

Access management is exposed via the following endpoints:

- `GET /api/v1/brokers/{id}/access`: List all users with access.
- `POST /api/v1/brokers/{id}/access`: Grant access.
- `PATCH /api/v1/brokers/{id}/access/{user_id}`: Change role.
- `DELETE /api/v1/brokers/{id}/access/{user_id}`: Revoke access.
