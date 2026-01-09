# Phase 0: Setup & Build Integration

**Status**: ✅ COMPLETATA (8 Gennaio 2026)  
**Durata**: 1 giorno  
**Priorità**: P0 (Critica)

---

## Obiettivo

Far funzionare la login page esistente con sfondo dinamico e integrare il build del frontend in dev.sh.

---

## ⚠️ Riferimento Phase 9

Se vengono creati componenti riutilizzabili, seguire le linee guida in [Phase 9: Polish](./phase-09-polish.md) e aggiornare quella fase con i dettagli del componente.

**Componenti creati in questa fase**:

- `AnimatedBackground.svelte` - Sfondo animato con onde e grafici

---

## 0.1 Fix Login Page (0.5 giorni) ✅

### Problema Risolto

- `npm run dev` mostrava componenti senza sfondo dinamico
- Grafica rotta / styling non applicato

### Soluzioni Implementate

1. **Tailwind CSS v4 Config**:
    - Eliminato `tailwind.config.ts` (non necessario in v4)
    - Usato `@theme {}` in `app.css` per colori custom:
   ```css
   @import "tailwindcss";
   @theme {
     --color-libre-green: #1a4031;
     --color-libre-beige: #f5f4ef;
     --color-libre-sage: #9caf9c;
     --color-libre-dark: #111111;
   }
   ```

2. **AnimatedBackground.svelte**:
    - Riscritto con 3 onde animate (clip-path + scaleY)
    - 3 linee grafici che si disegnano e sfumano a loop
    - Bordi sempre attaccati ai margini finestra
    - Rimossi frecce e griglia su richiesta

3. **Dipendenze Pulite**:
    - Rimosso Skeleton UI (non compatibile con Tailwind v4)
    - Mantenuto solo lucide-svelte per icone

### File Modificati

- `frontend/src/app.css`
- `frontend/src/lib/components/AnimatedBackground.svelte`
- `frontend/src/routes/+layout.svelte`
- `frontend/src/routes/+page.svelte` (login)
- `frontend/package.json`

---

## 0.2 Build Integration in dev.sh (0.5 giorni) ✅

### Funzionalità Implementate

1. **Nuovi Comandi dev.sh**:
    - `fe:dev` - Development server frontend (HMR)
    - `fe:build` - Build production frontend
    - `fe:check` - Type checking (svelte-check)
    - `fe:preview` - Preview del build

2. **Auto-Build in `start_server()`**:
    - `frontend_needs_rebuild()` - Controlla modifiche
    - `auto_build_frontend()` - Rebuilda se necessario
    - Console output migliorato con URL endpoints

3. **FastAPI Serve Frontend**:
    - Mount `/` per static files da `frontend/build/`
    - Mount `/_app` per asset SvelteKit
    - Catch-all per SPA routing (fallback a index.html)

4. **SvelteKit Adapter Static**:
    - Cambiato da `adapter-auto` a `adapter-static`
    - Configurato fallback per SPA
    - `prerender = true`, `ssr = false`

### Architettura Risultante

```
Development:
├── Backend:  ./dev.sh server    → http://localhost:8000
│   └── Auto-builds frontend se modifiche rilevate
└── Frontend: ./dev.sh fe:dev    → http://localhost:5173 (con HMR)

Production (Docker):
└── Backend:  ./dev.sh server    → http://localhost:8000
    ├── /api/v1/*  → FastAPI routes
    ├── /mkdocs/*  → User documentation
    └── /*         → Frontend SPA (da frontend/build/)
```

### File Modificati

- `dev.sh` (nuove funzioni e comandi)
- `backend/app/main.py` (StaticFiles mount)
- `frontend/svelte.config.js` (adapter-static)
- `frontend/src/routes/+layout.ts` (prerender config)

---

## Package.json Structure ✅

### Root `/package.json`

```json
{
  "scripts": {
    "install:all": "npm install && cd frontend && npm install",
    "test:e2e": "playwright test"
  },
  "devDependencies": {
    "@playwright/test": "^1.48.2"
  }
}
```

### Frontend `/frontend/package.json`

```json
{
  "devDependencies": {
    "@sveltejs/adapter-static": "^3.0.0",
    "@sveltejs/kit": "^2.48.5",
    "@tailwindcss/postcss": "^4.1.17",
    "svelte": "^5.43.8",
    "tailwindcss": "^4.1.17",
    "typescript": "^5.9.3",
    "vite": "^7.2.2"
  },
  "dependencies": {
    "lucide-svelte": "^0.559.0"
  }
}
```

**Motivazione Separazione**:

- Compartimentazione pulita
- Deploy indipendente possibile
- Aggiornamenti separati
- Root solo per tool di progetto (E2E tests)

---

## Verifica Completamento

### Test Manuali ✅

- [x] `npm run dev` in frontend mostra login con sfondo animato
- [x] Onde animate funzionano e toccano i bordi
- [x] Linee grafici si disegnano e sfumano a loop
- [x] Colori brand applicati correttamente
- [x] Language selector funziona
- [x] `./dev.sh fe:build` genera `frontend/build/`
- [x] `./dev.sh server` serve frontend su `/`

---

## Note per Fasi Future

- Il frontend ora è **puramente statico** (no SSR)
- Per aggiungere SSR in futuro, serve `adapter-node`
- I cookies `HttpOnly` funzionano solo con backend sullo stesso dominio

