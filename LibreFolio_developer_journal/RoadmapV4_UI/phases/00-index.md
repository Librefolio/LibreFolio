# Frontend Development Plan - Index

**Data Creazione**: 9 Gennaio 2026  
**Versione**: 3.0 (Riorganizzato in fasi separate)  
**Target**: Implementazione completa UI per LibreFolio  
**Status**: 🟢 PHASE 2.5 COMPLETATA - Prossimo: Phase 3 (Layout & Settings)

---

## 📊 Overview

Questo piano è suddiviso in fasi separate, ognuna in un file dedicato per facilitare la navigazione e il tracking del progresso.

**📌 Piano Principale**: [→ plan-frontendDevelopment.prompt.md](../plan-frontendDevelopment.prompt.md)

---

## 📁 Struttura Fasi

| Fase    | File                                                               | Descrizione                                | Status | Giorni |
|---------|--------------------------------------------------------------------|--------------------------------------------|--------|--------|
| **0**   | [phase-00-setup.md](./phase-00-setup.md)                           | Fix Login Page + Build Integration         | ✅      | 1      |
| **1**   | [phase-01-foundation.md](./phase-01-foundation.md)                 | i18n, OpenAPI, API Client, Auth Store      | ✅      | 3      |
| **2**   | [phase-02-backend-auth.md](./phase-02-backend-auth.md)             | Backend Auth: DB, Service, API, CLI, Tests | ✅      | 3      |
| **2.5** | [phase-02.5-auth-integration.md](./phase-02.5-auth-integration.md) | Integrazione Login + Register (Modali) | ✅ | 1 |
| **3**   | [phase-03-layout-settings.md](./phase-03-layout-settings.md)       | Layout Sidebar + Settings Page             | ⏳      | 3      |
| **4**   | [phase-04-brokers.md](./phase-04-brokers.md)                       | Brokers List, Add/Edit, Detail             | ⏳      | 3      |
| **5**   | [phase-05-fx.md](./phase-05-fx.md)                                 | FX Currencies, Pair Sources, Sync          | ⏳      | 3      |
| **6**   | [phase-06-assets.md](./phase-06-assets.md)                         | Assets List, Add/Edit, Detail              | ⏳      | 4      |
| **7**   | [phase-07-transactions.md](./phase-07-transactions.md)             | Transactions List, Add/Edit, Import        | ⏳      | 5      |
| **8**   | [phase-08-dashboard.md](./phase-08-dashboard.md)                   | Dashboard con KPI e Charts                 | ⏳      | 3      |
| **9**   | [phase-09-polish.md](./phase-09-polish.md)                         | UI Components, Responsive                  | ⏳      | 2      |

**Totale stimato**: ~6 settimane (~31 giorni)

---

## 🎯 Priorità

- **P0 (MVP)**: Phase 0, 1, 2, 2.5, 3, 4, 6, 7 (core funzionalità)
- **P1 (Important)**: Phase 5, 8 (FX, Dashboard)
- **P2 (Nice-to-have)**: Phase 9 (polish - fatto incrementalmente)

---

## 📐 Design System

- **Palette**:
    - Dark Forest Green (#1A4D3E) - Primary
    - Mint Green (#A8D5BA) - Accent/Success
    - Cream/Beige (#FDFBF7) - Background
    - Dark Grey (#2C2C2C) - Text
- **Layout**: Sidebar navigation + main content area
- **Style**: Modern, clean, Material UI inspired
- **Responsive**: Mobile-first approach

---

## 🔧 Stack Tecnologico

```json
{
  "framework": "SvelteKit 2.48+",
  "styling": "Tailwind CSS 4.1+ (via @theme in CSS)",
  "charts": "Apache ECharts 5.5+",
  "state": "SvelteKit load functions + Svelte Stores",
  "validation": "Zod (auto-generated from OpenAPI)",
  "dates": "date-fns 3.0+",
  "icons": "lucide-svelte 0.559+ + custom SVG",
  "i18n": "svelte-i18n 4.0+ (en/it/fr/es)"
}
```

---

## 📅 Timeline Complessiva

| Settimana | Fasi    | Obiettivi                           |
|-----------|---------|-------------------------------------|
| 1         | 0, 1, 2 | Setup, Frontend Auth, Backend Auth  |
| 2         | 2.5, 3  | Auth Integration, Layout & Settings |
| 3         | 4, 5    | Brokers, FX Management              |
| 4         | 6       | Assets Management                   |
| 5         | 7       | Transactions + Import               |
| 6         | 8, 9    | Dashboard + Polish                  |

**Totale stimato**: ~6 settimane

---

## ✅ Acceptance Criteria Globali

### Per ogni pagina:

- [ ] Responsive (desktop + mobile)
- [ ] Traduzioni en/it/fr/es complete
- [ ] Loading states visibili
- [ ] Error handling con toast
- [ ] Success feedback con toast
- [ ] Accessibility (keyboard navigation, ARIA)
- [ ] Coerente con design system

### Per l'intero frontend:

- [ ] `npm run build` senza errori
- [ ] Static files serviti da FastAPI
- [ ] Session cookie funzionante
- [ ] Language setting sincronizzato con API calls
- [ ] Protezione route (redirect a login)
- [ ] No errori console in production

---

## 📚 Riferimenti

- **Design Mockups**: `/site/POC_UX/`
- **Design Guide**: `/artwork/Prompt_gemini.md`
- **Architecture**: `/artwork/Struttura_sicurezza_programma.md`
- **Backend Roadmap**: `/LibreFolio_developer_journal/RoadmapV3/`
- **API Endpoints**: `./dev.sh info:api` (60+ endpoints)

