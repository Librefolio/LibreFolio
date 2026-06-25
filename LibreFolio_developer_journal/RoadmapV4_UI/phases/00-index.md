# Frontend Development Plan - Index

**Data Creazione**: 9 Gennaio 2026  
**Versione**: 4.0 (Aggiornato con stato completamento fasi)  
**Target**: Implementazione completa UI per LibreFolio  
**Status**: 🟢 PHASE 4 COMPLETATA - Prossimo: Phase 5 (FX Management)

---

## 📊 Overview

Questo piano è suddiviso in fasi separate, ognuna in un file dedicato per facilitare la navigazione e il tracking del progresso.

**📌 Piano Principale**: [→ plan-frontendDevelopment.prompt.md](../plan-frontendDevelopment.prompt.md)  
**📌 Phase 4 Summary**: [→ plan-phase04-summary.md](phase-04-subplan/plan-phase04-summary.md)  
**📌 Master Plan Phase 5–8**: [→ plan-phase05-to-08-upgrade.md](../plan-phase05-to-08-upgrade.md)

### Piani di Dettaglio per Fase

| Fase | Piano dettagliato | Status |
|------|-------------------|--------|
| **Phase 6** | [→ phase-06-assets.md](./phase-06-assets.md) | ✅ Completato |
| **Phase 7** | [→ phase-07-transactions.md](./phase-07-transactions.md) | ✅ Completato |
| **Phase 8** | [→ phase-08-scheduler.md](./phase-08-scheduler.md) | ✅ Completato |
| **Phase 9** | [→ phase-09-dashboard.md](./phase-09-dashboard.md) | ✅ Completato |

I sotto-piani di implementazione per ogni fase vanno in `phases/phase-XX-subplan/`.

---

## 📁 Struttura Fasi

| Fase    | File                                                               | Descrizione                                | Status | Giorni |
|---------|--------------------------------------------------------------------|--------------------------------------------|--------|--------|
| **0**   | [phase-00-setup.md](./phase-00-setup.md)                           | Fix Login Page + Build Integration         | ✅      | 1      |
| **1**   | [phase-01-foundation.md](./phase-01-foundation.md)                 | i18n, OpenAPI, API Client, Auth Store      | ✅      | 3      |
| **2**   | [phase-02-backend-auth.md](./phase-02-backend-auth.md)             | Backend Auth: DB, Service, API, CLI, Tests | ✅      | 3      |
| **2.5** | [phase-02.5-auth-integration.md](./phase-02.5-auth-integration.md) | Integrazione Login + Register (Modali)     | ✅      | 1      |
| **3**   | [phase-03-layout-settings.md](./phase-03-layout-settings.md)       | Layout Sidebar + Settings Page             | ✅      | 3      |
| **4**   | [phase-04-brokers.md](./phase-04-brokers.md)                       | Brokers, Files, Image Crop, ModalBase      | ✅      | 15+    |
| **5**   | [phase-05-fx.md](./phase-05-fx.md)                                 | FX Currencies, Pair Sources, Sync          | ⏳      | 3      |
| **6**   | [phase-06-assets.md](./phase-06-assets.md)                         | Assets: Dual View, Chart, Signals, Wizard  | ✅      | 7      |
| **7**   | [phase-07-transactions.md](./phase-07-transactions.md)             | Transactions: DB+BRIM+API (Part 1/2/3/4/5) | ✅      | 5+     |
| **8**   | [phase-08-scheduler.md](./phase-08-scheduler.md)                   | Market Data Scheduler (daemon + settings)  | ✅      | 2      |
| **9**   | [phase-09-dashboard.md](./phase-09-dashboard.md)                   | Dashboard con KPI e Charts                 | ✅      | 3      |
| **10**  | [phase-10-polish.md](./phase-10-polish.md)                         | UI Components, Responsive                  | ⏳      | 2      |
| **QA**  | [phase-final-subplan/README.md](./phase-final-subplan/README.md)   | QA trasversale 2026-06-25: 27 fix (A–L)    | ✅      | 1      |

**Totale stimato**: ~6,5 settimane (~33 giorni)

---

## 🎯 Priorità

- **P0 (MVP)**: Phase 0, 1, 2, 2.5, 3, 4, 6, 7 (core funzionalità)
- **P1 (Important)**: Phase 5, 8, 9 (FX, Scheduler, Dashboard)
- **P2 (Nice-to-have)**: Phase 10 (polish - fatto incrementalmente)

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

| Settimana | Fasi     | Obiettivi                                    |
|-----------|----------|----------------------------------------------|
| 1         | 0, 1, 2  | Setup, Frontend Auth, Backend Auth           |
| 2         | 2.5, 3   | Auth Integration, Layout & Settings          |
| 3-4       | 4        | Brokers, Files, Image Crop, ModalBase        |
| 4         | Pre-work | Schema Changes (share%, cost_basis_override) |
| 5         | 5        | FX Management + PriceChartShared             |
| 6         | 6        | Assets: Dual View, Chart, Signals, Wizard    |
| 7-8       | 7        | Transactions + Fiscal + Multi-Import         |
| 8         | 7.5      | File Preview                                 |
| 9         | 8        | Market Data Scheduler (daemon + settings)    |
| 10        | 9        | Dashboard + KPI + Dual Axis Charts           |
| 11        | 10       | Polish & Responsive                          |

**Totale stimato**: ~11 settimane (incluse fasi completate)

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
- **API Endpoints**: `./dev.py info api` (84+ endpoints)

