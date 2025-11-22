Perfetto, Emanuele — per i tuoi vincoli (**tutto OSS**, **responsive**, **1 solo container**, **1 sola porta**, **niente networking/routing esterni**, **TLS selezionabile o generato all’avvio**) la **Soluzione B** è ideale.

Di seguito ti propongo un’architettura concreta, con snippet e un **Dockerfile multi‑stage** che produce **un unico container** che espone **una sola porta HTTPS**.  
Il frontend (statico) e il backend (ASGI) rispondono **dallo stesso host/porta**, così **eviti CORS** e mantieni gli endpoint invariati.

***

## Architettura in breve

*   **Frontend OSS e responsive**:
    *   **SvelteKit + Tailwind + Skeleton UI** (consigliato per velocità e resa estetica)  
        *oppure* **Vue 3 + Quasar** (material, responsive out‑of‑the‑box).  
        Entrambi sono open-source e nati per UI responsive.

*   **Backend**: FastAPI/Starlette + Uvicorn.

*   **Distribuzione**: **un solo container** che:
    1.  serve lo **static frontend** (cartella `/static`)
    2.  espone le **API** su `/api/*`
    3.  usa **HTTPS**:
        *   Se l’utente fornisce **CERT/KEY**: li carica.
        *   Altrimenti **genera self‑signed all’avvio** (validità breve, rigenerabile).

*   **Sicurezza senza toccare gli endpoint**:
    *   **Middleware globale** che blocca `/api/*` se non autenticato.
    *   **Login locale** (username/password) → set di un **cookie di sessione** firmato (`HttpOnly`, `Secure`, `SameSite=Lax`).
    *   Facoltativo: supporto **JWT** se preferisci stateless.

> Nota: il cookie è preferibile per single‑origin e per evitare di cambiare i payload esistenti.

***

## Struttura progetto (esempio)

    your-app/
    ├─ frontend/              # SvelteKit o Quasar (codice sorgente UI)
    ├─ app/
    │  ├─ main.py             # ASGI app (FastAPI/Starlette)
    │  ├─ security/
    │  │  ├─ middleware.py
    │  │  ├─ sessions.py
    │  ├─ utils/
    │  │  └─ tls.py
    │  └─ static/             # (verrà popolata dalla build del frontend)
    ├─ requirements.txt
    ├─ Dockerfile
    └─ .env.example

***

## Backend – TLS: generazione self‑signed se mancano i file

`app/utils/tls.py`

```python
from datetime import datetime, timedelta
from pathlib import Path
import ssl, os

from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa

def ensure_tls_context(
    cert_path: str, key_path: str, cn: str = "localhost", days: int = 7
) -> ssl.SSLContext:
    cert_p, key_p = Path(cert_path), Path(key_path)
    if not cert_p.exists() or not key_p.exists():
        cert_p.parent.mkdir(parents=True, exist_ok=True)
        key_p.parent.mkdir(parents=True, exist_ok=True)

        key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        subject = x509.Name([
            x509.NameAttribute(NameOID.COMMON_NAME, cn),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, u"Self-Hosted App"),
        ])
        cert = (
            x509.CertificateBuilder()
            .subject_name(subject)
            .issuer_name(subject)
            .public_key(key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(datetime.utcnow() - timedelta(minutes=1))
            .not_valid_after(datetime.utcnow() + timedelta(days=days))
            .add_extension(
                x509.SubjectAlternativeName([
                    x509.DNSName(cn),
                    x509.DNSName("localhost"),
                ]),
                critical=False,
            )
            .add_extension(x509.BasicConstraints(ca=True, path_length=None), critical=True)
            .sign(key, hashes.SHA256())
        )
        key_p.write_bytes(
            key.private_bytes(
                serialization.Encoding.PEM,
                serialization.PrivateFormat.TraditionalOpenSSL,
                serialization.NoEncryption(),
            )
        )
        cert_p.write_bytes(cert.public_bytes(serialization.Encoding.PEM))

    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ctx.minimum_version = ssl.TLSVersion.TLSv1_2
    ctx.set_ciphers("ECDHE+AESGCM:ECDHE+CHACHA20:!aNULL:!eNULL:!MD5:!DES")
    ctx.load_cert_chain(certfile=str(cert_p), keyfile=str(key_p))
    return ctx
```

***

## Backend – Middleware di autenticazione (senza toccare gli endpoint)

*   Protegge **tutto** sotto `/api`.
*   Usa **cookie sessione** firmato.
*   Espone `/auth/login` e `/auth/logout` (endpoint nuovi, ma **i tuoi /api/* restano identici*\*).

`app/security/sessions.py`

```python
import secrets, time, hmac, hashlib, base64
from typing import Optional

class SessionManager:
    def __init__(self, secret: str, ttl_seconds: int = 3600):
        self.secret = secret.encode("utf-8")
        self.ttl = ttl_seconds

    def _sign(self, payload: bytes) -> str:
        sig = hmac.new(self.secret, payload, hashlib.sha256).digest()
        return base64.urlsafe_b64encode(sig).decode().rstrip("=")

    def create_cookie_value(self, user: str) -> str:
        # value: base64(user|exp|nonce).signature
        exp = int(time.time()) + self.ttl
        nonce = secrets.token_urlsafe(12)
        raw = f"{user}|{exp}|{nonce}".encode()
        b = base64.urlsafe_b64encode(raw).decode().rstrip("=")
        sig = self._sign(b.encode())
        return f"{b}.{sig}"

    def verify_cookie_value(self, cookie: str) -> Optional[str]:
        try:
            b64, sig = cookie.rsplit(".", 1)
            if not hmac.compare_digest(sig, self._sign(b64.encode())):
                return None
            raw = base64.urlsafe_b64decode(b64 + "===")
            user, exp, _ = raw.decode().split("|", 2)
            if int(exp) < int(time.time()):
                return None
            return user
        except Exception:
            return None
```

`app/security/middleware.py`

```python
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from starlette.requests import Request

PROTECTED_PREFIXES = ("/api",)

class RequireAuthMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, session_cookie_name: str = "session"):
        super().__init__(app)
        self.session_cookie_name = session_cookie_name

    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        if any(path.startswith(p) for p in PROTECTED_PREFIXES):
            cookie = request.cookies.get(self.session_cookie_name)
            user = request.state.session_verify(cookie) if cookie else None
            if not user:
                return JSONResponse({"detail": "Unauthorized"}, status_code=401)
            request.state.user = user
        return await call_next(request)
```

***

## Backend – App FastAPI (serve static + login/logout)

`app/main.py`

```python
import os, uvicorn
from fastapi import FastAPI, Depends, Response, Request, Form
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware import Middleware

from app.security.sessions import SessionManager
from app.security.middleware import RequireAuthMiddleware
from app.utils.tls import ensure_tls_context
from pathlib import Path

SESSION_COOKIE = os.getenv("SESSION_COOKIE", "session")
SESSION_SECRET = os.getenv("SESSION_SECRET", "change-me-please")  # in prod: segreto forte
SESSION_TTL = int(os.getenv("SESSION_TTL", "3600"))

# In-memory demo user store (sostituisci con DB/LDAP/OIDC)
USERS = {"admin": "admin"}  # usa hash in produzione (es. passlib/bcrypt)

app = FastAPI()
# Niente CORS se frontend e backend sono sulla stessa origin/porta
# Se servissero (domini diversi), abilita CORS con origins specifici.

session_mgr = SessionManager(SESSION_SECRET, ttl_seconds=SESSION_TTL)

def session_verify(cookie: str):
    return session_mgr.verify_cookie_value(cookie)

@app.middleware("http")
async def attach_session_verifier(request: Request, call_next):
    # Espone la funzione di verifica al middleware RequireAuth
    request.state.session_verify = session_verify
    return await call_next(request)

app.add_middleware(RequireAuthMiddleware, session_cookie_name=SESSION_COOKIE)

# --------- Static (frontend) ----------
static_dir = Path(__file__).parent / "static"
app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")

# (Opzionale) fallback SPA: serve index.html per route non /api
@app.get("/{full_path:path}")
async def spa_fallback(full_path: str):
    index = static_dir / "index.html"
    if index.exists():
        return FileResponse(index)
    return JSONResponse({"detail": "Not Found"}, status_code=404)

# --------- Auth ----------
@app.post("/auth/login")
async def login(response: Response, username: str = Form(...), password: str = Form(...)):
    # Sostituisci con verifica hash/DB
    if USERS.get(username) != password:
        return JSONResponse({"detail": "Invalid credentials"}, status_code=401)
    cookie_val = session_mgr.create_cookie_value(username)
    response = JSONResponse({"detail": "ok"})
    response.set_cookie(
        key=SESSION_COOKIE,
        value=cookie_val,
        httponly=True,
        secure=True,           # richiede HTTPS
        samesite="lax",
        path="/",
        max_age=SESSION_TTL,
    )
    return response

@app.post("/auth/logout")
async def logout(response: Response):
    response = JSONResponse({"detail": "bye"})
    response.delete_cookie(SESSION_COOKIE, path="/")
    return response

# --------- API protette (esempio) ----------
@app.get("/api/ping")
async def ping(request: Request):
    user = getattr(request.state, "user", None)
    return {"pong": True, "user": user}

def main():
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8443"))
    cert = os.getenv("TLS_CERT", "/run/tls/server.crt")
    key  = os.getenv("TLS_KEY",  "/run/tls/server.key")
    cn   = os.getenv("TLS_CN",   "localhost")

    # Se l’utente non monta cert/key → generiamo self-signed
    ctx = ensure_tls_context(cert, key, cn=cn, days=int(os.getenv("TLS_DAYS", "7")))

    uvicorn.run(
        "app.main:app",
        host=host,
        port=port,
        ssl_keyfile=key,
        ssl_certfile=cert,
        # in alternativa: ssl=ctx,
        forwarded_allow_ips="*",
        proxy_headers=True,
    )

if __name__ == "__main__":
    main()
```

> **Nota**: in produzione sostituisci l’archivio utenti con password **hashate** (es. `passlib[bcrypt]`) o integra un IdP (OIDC) se più avanti vorrai SSO — senza cambiare gli endpoint `/api/*`.

***

## Frontend OSS responsivo

### Opzione 1 – **SvelteKit + Tailwind + Skeleton UI** (consigliata)

*   UI moderna, theming rapido, bundle leggero.
*   Adapter **static** per build in HTML/CSS/JS (serviti da `StaticFiles`).

Passi principali:

```bash
# nel folder frontend/
npm create svelte@latest
# Seleziona Skeleton UI o aggiungilo:
npm i -D @skeletonlabs/skeleton tailwindcss postcss autoprefixer
npx tailwindcss init -p
# Configura tailwind + skeleton in postcss/tailwind.config.cjs
# Adatta svelte.config.js per adapter-static
npm i -D @sveltejs/adapter-static
```

Build:

```bash
npm run build      # output in build/ (configurabile come 'frontend_build')
```

Nel Dockerfile copieremo l’output in `app/static/`.

### Opzione 2 – **Vue 3 + Quasar**

```bash
npm create quasar@latest
quasar build       # output in dist/spa
```

Entrambe sono **100% open-source** e responsive by design.

***

## Dockerfile (un solo container, una sola porta)

Esempio con **SvelteKit (adapter‑static)**:

```Dockerfile
# ---------- STAGE 1: build frontend ----------
FROM node:20-alpine AS frontend
WORKDIR /frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ .
RUN npm run build

# ---------- STAGE 2: runtime python ----------
FROM python:3.12-slim AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# dipendenze per cryptography
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libssl-dev libffi-dev && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia backend
COPY app/ ./app/

# Copia build frontend in static
RUN mkdir -p app/static
# Se usi SvelteKit adapter-static: di solito out è "build"
COPY --from=frontend /frontend/build/ ./app/static/

# runtime dirs per cert
RUN mkdir -p /run/tls

# Porta unica (HTTPS)
EXPOSE 8443

ENV HOST=0.0.0.0 \
    PORT=8443 \
    TLS_CERT=/run/tls/server.crt \
    TLS_KEY=/run/tls/server.key \
    TLS_CN=localhost \
    TLS_DAYS=7 \
    SESSION_COOKIE=session \
    SESSION_TTL=3600

CMD ["python", "-m", "app.main"]
```

`requirements.txt`

    fastapi==0.115.0
    uvicorn[standard]==0.30.6
    starlette==0.38.5
    cryptography==43.0.1

> Se usi **Quasar/Vue**, cambia la directory di output nel `COPY --from=frontend` (es. `dist/spa`).

### Uso con certificato utente

*   Monta i tuoi file cert/key nel container in `/run/tls/`:

```bash
docker run -p 8443:8443 \
  -v $(pwd)/certs/server.crt:/run/tls/server.crt:ro \
  -v $(pwd)/certs/server.key:/run/tls/server.key:ro \
  -e TLS_CN="app.miodominio.tld" \
  -e SESSION_SECRET="$(openssl rand -hex 32)" \
  your-image:latest
```

*   Se **non** monti nulla, all’avvio il backend genera un **self‑signed** valido per `TLS_DAYS`.

***

## Perché questa soluzione è coerente con il tuo flow

*   **Unico container, unica porta**: sì, tutto gira dentro FastAPI/Uvicorn (static + API).
*   **Niente networking/routing esterno**: sì, nessun reverse proxy richiesto.
*   **TLS gestito dall’app**: sì, con selezione dinamica (user‑provided o self‑signed auto).
*   **Endpoint invariati**: sì, gli `/api/*` non cambiano. Aggiungi solo `/auth/login` & `/auth/logout`.
*   **Frontend OSS e responsivo**: SvelteKit/Skeleton o Quasar sono perfetti.
*   **Sicuro**: cookie `HttpOnly`/`Secure`, TLS obbligatorio, middleware che blocca tutto sotto `/api/*`.

***

## Hardening (checklist rapida)

*   Genera **SESSION\_SECRET** robusto (env segreto).
*   Imposta **Secure cookies** (già fatto) + **SameSite=Lax/Strict** secondo flussi.
*   Considera **rate‑limiting** su `/auth/login` (anche semplice in‑memory).
*   Hash password (es. `passlib[bcrypt]`) o integra un IdP quando vorrai (mantenendo invariati gli endpoint API).
*   Se esponi su Internet, valuta **CSP** per la UI e header di sicurezza (puoi servirli con una piccola middleware aggiuntiva).
*   Se usi `X-Forwarded-*` in futuro, limita `forwarded_allow_ips`.

***

## Prossimi passi (dimmi cosa preferisci)

1.  **Frontend**: vuoi che ti prepari il setup **SvelteKit + Tailwind + Skeleton** *oppure* **Vue + Quasar**?
2.  **Auth**: tieni login locale con hash password, o preferisci già un JWT?
3.  Vuoi che ti consegni un **repo starter** con Dockerfile già pronto e una pagina di login minimale?

Se mi confermi queste 3 preferenze, ti preparo i file pronti (inclusi config Tailwind/Quasar, pagine di login e chiamate fetch a `/auth/login` e `/api/ping`).
