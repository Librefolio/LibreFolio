# Panoramica del Piano Operativo: Integrazione Frontend (Login/Dashboard) con Backend FastAPI

Questo documento descrive i passi per sviluppare un'applicazione frontend moderna e responsiva (login e dashboard) e integrarla con il backend FastAPI/Uvicorn esistente. Il piano è stato aggiornato per includere requisiti specifici su UI/UX (mobile/desktop, tab, modali, sfondi animati) e sicurezza (hashing password, recovery via terminale).

## 1. Scelta delle Tecnologie Frontend

Per soddisfare i requisiti di **responsività**, gestione semplice di **tab/modali** e performance, confermiamo lo stack:

*   **SvelteKit**: Framework moderno, ideale per generare output statico e gestire lo stato dell'applicazione.
*   **Tailwind CSS**: Per uno styling rapido e adattabile a mobile/desktop.
*   **Skeleton UI**: Libreria basata su Tailwind che fornisce componenti pronti all'uso come **App Shell** (per layout responsivi), **Tabs** e **Modals**, riducendo drasticamente i tempi di sviluppo per l'interfaccia richiesta.

## 2. Architettura Integrata (Soluzione B)

*   **Unico Container**: Frontend statico e backend (ASGI) serviti dallo stesso processo Uvicorn.
*   **Unica Porta HTTPS**: Tutto su porta HTTPS (es. 8443), zero CORS issues.
*   **Backend FastAPI**: Serve static files su `/`, API su `/api/*` e Auth su `/auth/*`.

## 3. Sviluppo del Frontend (SvelteKit)

### 3.1. Setup e Componenti UI
1.  **Inizializzazione**: Setup progetto SvelteKit con `adapter-static`.
2.  **Skeleton UI**: Installazione e configurazione per gestire il layout.
    *   Utilizzo di `AppShell` di Skeleton per gestire header, sidebar e footer in modo responsivo (hamburger menu su mobile, sidebar fissa su desktop).
    *   Utilizzo dei componenti `TabGroup` e `Modal` di Skeleton per le funzionalità richieste.
3.  **Sfondo Animato**: Integrazione di un componente Svelte dedicato per il background.
    *   Supporto per immagini statiche classiche.
    *   Supporto per **SVG animati**: implementati come componenti Svelte inline o tramite CSS animations per garantire leggerezza e scalabilità senza pesare sul bundle.

### 3.2. Login e Dashboard
*   **Login Page**: Form minimalista centrato, con supporto visivo per lo sfondo animato. Chiamata POST a `/auth/login`.
*   **Dashboard**:
    *   Layout responsivo.
    *   Navigazione tramite Tabs (es. "Portafoglio", "Transazioni", "Analisi").
    *   Modali per operazioni di dettaglio (es. "Dettaglio Asset", "Nuova Transazione").

## 4. Configurazione Backend (FastAPI) & Sicurezza Avanzata

### 4.1. Gestione Credenziali (Hashing)
*   **Storage Sicuro**: Le password **NON** saranno mai salvate in chiaro.
*   **Libreria**: Utilizzo di `passlib[bcrypt]` o `argon2-cffi` per l'hashing.
*   **Verifica**: Al login, l'hash della password inviata viene confrontato con quello nel DB.

### 4.2. Recupero Account (Terminale Only)
Per proteggere da attacchi remoti ma permettere il recupero con accesso fisico:
*   **Nessun Endpoint di Reset**: Non esisteranno API pubbliche (`/api/reset-password`) per il reset.
*   **CLI Script**: Sviluppo di uno script Python (es. `manage.py` o integrato in `dev.sh`) eseguibile solo da terminale server.
    *   Comando: `python manage.py user reset-password <username>`
    *   Funzione: Genera un nuovo hash per una password fornita o generata casualmente e aggiorna direttamente il DB.
    *   Sicurezza: Richiede accesso alla shell del server/container, garantendo che solo l'amministratore fisico possa effettuare il reset.

### 4.3. Serving Statico & Middleware
*   Configurazione `app.mount("/", StaticFiles(...))` per servire la build SvelteKit.
*   Middleware per gestire cookie di sessione (`HttpOnly`, `Secure`, `SameSite=Lax`).

## 5. Build e Deployment

### 5.1 Dockerfile Multi-stage
1.  **Frontend Build**: Node.js compila SvelteKit → HTML/CSS/JS statici.
2.  **Backend Setup**: Python installa dipendenze e copia il backend.
3.  **Merge**: I file statici del frontend vengono copiati nella cartella `static` del backend.
4.  **Runtime**: Uvicorn avvia l'app completa.

## 6. Riepilogo Sicurezza

| Caratteristica | Implementazione | Beneficio |
| :--- | :--- | :--- |
| **Trasporto** | HTTPS (TLS) | Crittografia end-to-end. |
| **Sessione** | Cookie `HttpOnly`, `Secure` | Protezione da XSS e sniffing. |
| **Password** | Hashing (Bcrypt/Argon2) | Protezione in caso di data leak. |
| **Reset Pw** | **CLI Script (Solo Terminale)** | Impossibile resettare password da remoto senza accesso SSH/Fisico. |

## Prossimi Passi Operativi

1.  Confermare questa struttura aggiornata.
2.  Procedere con lo scaffolding del progetto Frontend (SvelteKit + Skeleton).
3.  Implementare la logica di hashing nel Backend e lo script di reset password CLI.