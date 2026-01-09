# Phase 2: Backend Authentication System

**Status**: ✅ COMPLETATA (8-9 Gennaio 2026)  
**Durata**: 3 giorni  
**Priorità**: P0 (Critica)

---

## Obiettivo

Implementare l'intero sistema di autenticazione lato server: modello database, servizi, API endpoints, CLI management, e tests.

---

## ⚠️ Riferimento Phase 9

Questa fase è backend-only. Per componenti frontend riutilizzabili, vedere [Phase 9: Polish](./phase-09-polish.md).

---

## 2.1 Database Schema & Models (0.5 giorni) ✅

### Modifiche al Database

**Tabella `users`** in `001_initial.py`:

```python
op.create_table(
    'users',
    sa.Column('id', sa.Integer(), primary_key=True),
    sa.Column('username', sa.String(50), nullable=False, unique=True),
    sa.Column('email', sa.String(255), nullable=False, unique=True),
    sa.Column('hashed_password', sa.String(255), nullable=False),
    sa.Column('is_active', sa.Boolean(), default=True),
    sa.Column('is_superuser', sa.Boolean(), default=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=utcnow),
    sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=utcnow),
    )
```

### Modello SQLModel

**File**: `backend/app/db/models.py`

```python
class User(SQLModel, table=True):
    __tablename__ = "users"

    id: int | None = Field(default=None, primary_key=True)
    username: str = Field(max_length=50, unique=True)
    email: str = Field(max_length=255, unique=True)
    hashed_password: str = Field(max_length=255)
    is_active: bool = Field(default=True)
    is_superuser: bool = Field(default=False)
    created_at: datetime | None = Field(default=None)
    updated_at: datetime | None = Field(default=None)
```

### File Modificati

- `backend/alembic/versions/001_initial.py`
- `backend/app/db/models.py`

---

## 2.2 Auth Service (Password Hashing) (0.5 giorni) ✅

### Dipendenze Installate

```bash
pipenv install bcrypt email-validator
```

### Auth Service

**File**: `backend/app/services/auth_service.py`

```python
# Password Hashing (bcrypt, cost factor 12)
def hash_password(password: str) -> str


    def verify_password(plain_password: str, hashed_password: str) -> bool


# Session Management (In-Memory)
_sessions: dict[str, dict] = {}  # session_id → {user_id, created_at, expires_at}


def create_session(user_id: int) -> str  # 24h expire, 256-bit entropy


    def get_session(session_id: str) -> dict | None


    def get_user_id_from_session(session_id: str) -> int | None


    def delete_session(session_id: str) -> bool


    def delete_user_sessions(user_id: int) -> int


    def cleanup_expired_sessions() -> int
```

### User Service

**File**: `backend/app/services/user_service.py`

```python
# Logica condivisa tra API e CLI (DRY)
async def get_user_by_username(session, username) -> User | None
async def get_user_by_email(session, email) -> User | None
async def get_user_by_username_or_email(session, identifier) -> User | None
async def get_user_by_id(session, user_id) -> User | None
async def list_users(session) -> list[User]
async def create_user(session, username, email, password, ...) -> tuple[User | None, str | None]
async def reset_password(session, username, new_password) -> tuple[bool, str | None]
async def set_user_active(session, username, active) -> tuple[bool, str | None]
```

### File Creati

- `backend/app/services/auth_service.py`
- `backend/app/services/user_service.py`

---

## 2.3 Auth Endpoints (1 giorno) ✅

### API Router

**File**: `backend/app/api/v1/auth.py`

| Endpoint         | Metodo | Descrizione                               |
|------------------|--------|-------------------------------------------|
| `/auth/login`    | POST   | Login con username/email → session cookie |
| `/auth/logout`   | POST   | Destroy session + clear cookie            |
| `/auth/me`       | GET    | Get current user info                     |
| `/auth/register` | POST   | Registrazione nuovo utente                |

### Session Cookie Configuration

```python
SESSION_COOKIE_NAME = "session"
SESSION_COOKIE_MAX_AGE = 60 * 60 * 24  # 24 hours
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "lax"
SESSION_COOKIE_SECURE = False  # True in production with HTTPS
```

### Request/Response Schemas

**File**: `backend/app/schemas/auth.py`

```python
class AuthLoginRequest(BaseModel):
    username: str  # Accetta username O email
    password: str


class AuthRegisterRequest(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(min_length=8)


class AuthUserResponse(BaseModel):
    id: int
    username: str
    email: str
    is_active: bool
    is_superuser: bool
    created_at: datetime


class AuthLoginResponse(BaseModel):
    user: AuthUserResponse
    message: str = "Login successful"
```

### Route Protection Dependency

```python
async def get_current_user(request, session) -> User:
    """Raises 401 if not authenticated."""


async def get_optional_user(request, session) -> User | None:
    """Returns None if not authenticated (no exception)."""
```

### File Creati/Modificati

- `backend/app/api/v1/auth.py`
- `backend/app/schemas/auth.py`
- `backend/app/api/v1/router.py` (registrato nuovo router)

---

## 2.4 Route Protection Approach ✅

### Decisione: FastAPI Dependencies (non Middleware)

Invece di middleware globale, usiamo **Dependencies esplicite**:

```python
# Endpoint protetto
@router.get("/protected")
async def protected_endpoint(
        current_user: User = Depends(get_current_user)
        ):
    return {"user": current_user.username}


# Endpoint con auth opzionale
@router.get("/optional")
async def optional_endpoint(
        user: User | None = Depends(get_optional_user)
        ):
    if user:
        return {"authenticated": True}
    return {"authenticated": False}
```

**Vantaggi**:

- Più idiomatico per FastAPI
- Controllo granulare per endpoint
- Nessun overhead su route pubbliche

---

## 2.5 CLI Commands (0.5 giorni) ✅

### Script CLI

**File**: `user_cli.py` (nella root, accanto a test_runner.py)

```python
Commands:
- create - superuser < username > < email > < password >
- reset - password < username > < new_password >
- list - users
- activate < username >
- deactivate < username >
```

### Integrazione dev.sh

```bash
./dev.sh user:create <username> <email> <password>
./dev.sh user:reset <username> <new_password>
./dev.sh user:list
./dev.sh user:activate <username>
./dev.sh user:deactivate <username>
```

### Uso Tipico

```bash
# Creare primo admin
./dev.sh user:create admin admin@example.com password123

# Reset password dimenticata (da terminale server)
./dev.sh user:reset admin newpassword

# Verificare utenti
./dev.sh user:list
```

### File Creati/Modificati

- `user_cli.py`
- `dev.sh` (nuovi comandi)

---

## 2.6 Tests (0.5 giorni) ✅

### Test Suite

**File**: `backend/test_scripts/test_api/test_auth_api.py`

| Test Class             | Test        | Descrizione                      |
|------------------------|-------------|----------------------------------|
| TestRegister           | REG-001     | Register success                 |
|                        | REG-002     | Duplicate username rejected      |
|                        | REG-003     | Duplicate email rejected         |
|                        | REG-004     | Short password rejected          |
| TestLogin              | LOGIN-001   | Login with username              |
|                        | LOGIN-002   | Login with email                 |
|                        | LOGIN-003   | Wrong password rejected          |
|                        | LOGIN-004   | Non-existent user rejected       |
| TestLogout             | LOGOUT-001  | Logout clears session cookie     |
| TestMe                 | ME-001      | Get user when authenticated      |
|                        | ME-002      | 401 when not authenticated       |
|                        | ME-003      | 401 with invalid session         |
| TestSessionPersistence | SESSION-001 | Cookie is HttpOnly               |
|                        | SESSION-002 | Session persists across requests |

### Esecuzione

```bash
./dev.sh test api auth
# Output: 14 passed, 0 warnings
```

### File Creati/Modificati

- `backend/test_scripts/test_api/test_auth_api.py`
- `test_runner.py` (aggiunto comando `auth`)

---

## Riepilogo File Creati/Modificati

| File                                             | Azione                           |
|--------------------------------------------------|----------------------------------|
| `Pipfile`                                        | Aggiunto bcrypt, email-validator |
| `backend/alembic/versions/001_initial.py`        | Aggiornato users table           |
| `backend/app/db/models.py`                       | Aggiornato User model            |
| `backend/app/services/auth_service.py`           | Creato                           |
| `backend/app/services/user_service.py`           | Creato                           |
| `backend/app/api/v1/auth.py`                     | Creato                           |
| `backend/app/schemas/auth.py`                    | Creato                           |
| `backend/app/api/v1/router.py`                   | Registrato auth router           |
| `user_cli.py`                                    | Creato                           |
| `dev.sh`                                         | Aggiunti comandi user:*          |
| `backend/test_scripts/test_api/test_auth_api.py` | Creato                           |
| `test_runner.py`                                 | Aggiunto test auth               |

---

## Verifica Completamento

### Test Automatici ✅

```bash
./dev.sh test api auth
# 14 passed, 0 warnings
```

### Test Manuali ✅

- [x] `./dev.sh user:create admin admin@test.com pass123` funziona
- [x] `./dev.sh user:list` mostra utente creato
- [x] Login via curl con session cookie funziona
- [x] `/auth/me` ritorna user info con cookie valido
- [x] Logout invalida sessione

---

## Prossimi Passi

→ **Phase 2.5**: Integrare frontend login con backend auth

