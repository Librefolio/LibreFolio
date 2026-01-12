# Plan: Frontend Development - LibreFolio UI

**Data Creazione**: 8 Gennaio 2026
**Versione**: 3.0 (Riorganizzato con sotto-plan)
**Target**: Implementazione completa UI per LibreFolio
**Status**: 🟢 PHASE 3 COMPLETATA - Prossimo: Phase 3.5 (Settings System) o Phase 4 (Brokers)

---

## 📊 Overview

Questo documento è l'indice principale del piano frontend. Ogni fase ha il proprio file dettagliato nella cartella `phases/`.

**📁 Sotto-Plan Dettagliati**: [`phases/`](./phases/)

---

## 🔧 Stack Tecnologico

```json
{
  "framework": "SvelteKit 2.48+",
  "styling": "Tailwind CSS 4.1+ (via @theme in CSS)",
  "charts": "Apache ECharts 5.5+",
  "state": "SvelteKit load functions + Svelte Stores",
  "validation": "Zod (auto-generated da OpenAPI)",
  "dates": "date-fns 3.0+",
  "icons": "lucide-svelte 0.559+ + custom SVG",
  "i18n": "svelte-i18n 4.0+ (en/it/fr/es)"
}
```

---

## 📐 Design System

| Elemento       | Valore                      |
|----------------|-----------------------------|
| **Primary**    | Dark Forest Green (#1A4D3E) |
| **Accent**     | Mint Green (#A8D5BA)        |
| **Background** | Cream/Beige (#FDFBF7)       |
| **Text**       | Dark Grey (#2C2C2C)         |
| **Layout**     | Sidebar + Main Content      |
| **Responsive** | Mobile-first                |

---

## 📋 Fasi di Sviluppo

| Fase    | Nome                        | Status       | Link Dettagli                                                               | Giorni |
|---------|-----------------------------|--------------|-----------------------------------------------------------------------------|--------|
| **0**   | Setup & Build Integration   | ✅ COMPLETATA | [→ phase-00-setup.md](./phases/phase-00-setup.md)                           | 1      |
| **1**   | Foundation & Frontend Auth  | ✅ COMPLETATA | [→ phase-01-foundation.md](./phases/phase-01-foundation.md)                 | 3      |
| **2**   | Backend Authentication      | ✅ COMPLETATA | [→ phase-02-backend-auth.md](./phases/phase-02-backend-auth.md)             | 3      |
| **2.5** | Auth Integration (FE ↔ BE)  | ✅ COMPLETATA | [→ phase-02.5-auth-integration.md](./phases/phase-02.5-auth-integration.md) | 1      |
| **3**   | Layout & Settings           | ✅ COMPLETATA | [→ phase-03-layout-settings.md](./phases/phase-03-layout-settings.md)       | 1      |
| **3.5** | Settings System (Glob+Pers) | ⏳ TODO       | [→ phase-03.5-settings-system.md](./phases/phase-03.5-settings-system.md)   | 2.5    |
| **4**   | Brokers Management          | ⏳ TODO       | [→ phase-04-brokers.md](./phases/phase-04-brokers.md)                       | 3      |
| **5**   | FX Management               | ⏳ TODO       | [→ phase-05-fx.md](./phases/phase-05-fx.md)                                 | 3      |
| **6**   | Assets Management           | ⏳ TODO       | [→ phase-06-assets.md](./phases/phase-06-assets.md)                         | 4      |
| **7**   | Transactions Management     | ⏳ TODO       | [→ phase-07-transactions.md](./phases/phase-07-transactions.md)             | 5      |
| **8**   | Dashboard                   | ⏳ TODO       | [→ phase-08-dashboard.md](./phases/phase-08-dashboard.md)                   | 3      |
| **9**   | Polish & Responsive         | ⏳ ONGOING    | [→ phase-09-polish.md](./phases/phase-09-polish.md)                         | 2      |

**Totale stimato**: ~6 settimane (~31 giorni)

---

## 🎯 Priorità

- **P0 (MVP)**: Phase 0, 1, 2, 2.5, 3, 4, 6, 7
- **P1 (Important)**: Phase 5, 8
- **P2 (Ongoing)**: Phase 9 (fatto incrementalmente)

---

## 📅 Timeline

| Settimana | Fasi      | Obiettivo                           |
|-----------|-----------|-------------------------------------|
| 1         | 0, 1, 2 ✅ | Setup, Frontend Auth, Backend Auth  |
| 2         | 2.5, 3    | Auth Integration, Layout & Settings |
| 3         | 4, 5      | Brokers, FX Management              |
| 4         | 6         | Assets Management                   |
| 5         | 7         | Transactions + Import               |
| 6         | 8, 9      | Dashboard + Polish                  |

---

## 🔗 Dipendenze tra Fasi

```
Phase 0 (Setup)
    ↓
Phase 1 (Foundation)
    ↓
Phase 2 (Backend Auth)
    ↓
Phase 2.5 (Auth Integration) ✅
    ↓
Phase 3 (Layout & Settings) ✅
    ↓
    ├── Phase 3.5 (Settings System) ←── OPZIONALE (può essere fatto dopo Phase 4-7)
    │
    ├── Phase 4 (Brokers) ←── PROSSIMO STEP CONSIGLIATO
    │       ↓
    ├── Phase 5 (FX)
    │
    └── Phase 6 (Assets) ───────────────────┐
                                            ↓
                                    Phase 7 (Transactions)
                                            ↓
                                    Phase 8 (Dashboard)

Phase 9 (Polish) ← Fatto incrementalmente durante tutte le fasi
    │       ↓                               │
    ├── Phase 5 (FX)                        │
    │                                       │
    └── Phase 6 (Assets) ───────────────────┤
                                            ↓
                                    Phase 7 (Transactions)
                                            ↓
                                    Phase 8 (Dashboard)

Phase 9 (Polish) ← Fatto incrementalmente durante tutte le fasi
```

---

## ⚠️ Regole Importanti

### 1. Componenti Riutilizzabili

Ogni volta che si crea un componente che può essere riutilizzato:

- Seguire le linee guida in [Phase 9: Polish](./phases/phase-09-polish.md)
- Aggiornare quella fase con i dettagli del componente
- Creare in `src/lib/components/ui/`

### 2. Modali Auth (Phase 2.5)

- **NON creare pagine separate** per register e forgot-password
- Usare **modali intercambiabili** nella stessa pagina `/login`
- L'AnimatedBackground deve continuare senza reset

### 3. Tutto Frontend in `/frontend`

- Nessun file frontend nella root
- Nessun file misto con backend
- Struttura: `backend/` Python, `frontend/` SvelteKit

### 4. Calcoli nel Backend

- Il frontend è **solo presentazione**
- Tutti i calcoli avvengono lato server
- API-first approach

---

## ✅ Acceptance Criteria Globali

### Per ogni pagina:

- [ ] Responsive (desktop + mobile)
- [ ] Traduzioni en/it/fr/es complete
- [ ] Loading states visibili
- [ ] Error handling con toast
- [ ] Success feedback con toast
- [ ] Accessibility (keyboard, ARIA)
- [ ] Coerente con design system

### Per l'intero frontend:

- [ ] `npm run build` senza errori
- [ ] Static files serviti da FastAPI
- [ ] Session cookie funzionante
- [ ] Language setting sync con API
- [ ] Protezione route (redirect login)
- [ ] No errori console in production

---

## 📚 Riferimenti

| Risorsa         | Path                                        |
|-----------------|---------------------------------------------|
| Design Mockups  | `/site/POC_UX/`                             |
| Design Guide    | `/artwork/Prompt_gemini.md`                 |
| Architecture    | `/artwork/Struttura_sicurezza_programma.md` |
| Backend Roadmap | `/LibreFolio_developer_journal/RoadmapV3/`  |
| API Endpoints   | `./dev.sh info:api`                         |

---

## 📝 Note di Sviluppo

### Comandi Utili

```bash
# Frontend development
./dev.sh fe:dev          # Dev server con HMR
./dev.sh fe:build        # Build production
./dev.sh fe:check        # Type checking

# Backend con frontend
./dev.sh server          # Backend (auto-build frontend se necessario)

# API Schema
./dev.sh api:schema      # Genera openapi.json
./dev.sh api:sync        # Schema + client TypeScript

# User management
./dev.sh user:create <user> <email> <pass>
./dev.sh user:list
./dev.sh user:reset <user> <new_pass>
```

### Architettura Build

```
Development:
├── Backend:  ./dev.sh server    → http://localhost:8000
└── Frontend: ./dev.sh fe:dev    → http://localhost:5173 (HMR)

Production:
└── Backend:  ./dev.sh server    → http://localhost:8000
    ├── /api/v1/*  → FastAPI
    ├── /mkdocs/*  → Docs
    └── /*         → Frontend SPA
```

