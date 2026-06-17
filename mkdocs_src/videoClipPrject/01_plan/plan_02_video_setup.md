# Piano di Setup e Implementazione — Video Promo Remotion

> Questo documento è la guida operativa per l'agente CLI.
> Ogni sezione è un **checkpoint**: completala prima di passare alla successiva.

---

## 📁 Struttura Target del Progetto

Una volta completato il setup, la struttura della cartella `video_promo/` dovrà essere:

```
videoClipPrject/
├── 01_plan/
│   ├── master_plan.md
│   ├── plan_02_video.md
│   └── plan_02_video_setup.md  ← questo file
├── external_src/
└── video_promo/                ← NEW: radice del progetto Remotion
    ├── package.json
    ├── tsconfig.json
    ├── remotion.config.ts
    ├── src/
    │   ├── Root.tsx             ← registra tutte le Composition
    │   ├── index.ts             ← entry-point Remotion
    │   ├── i18n/
    │   │   ├── index.ts         ← re-esporta tutto
    │   │   ├── en.ts
    │   │   ├── it.ts
    │   │   ├── es.ts
    │   │   └── fr.ts
    │   ├── types/
    │   │   └── i18n.ts          ← interfaccia T (dizionario tipizzato)
    │   ├── scenes/
    │   │   ├── Scene01Hook.tsx
    │   │   ├── Scene02Hero.tsx
    │   │   ├── Scene03MultiAsset.tsx
    │   │   ├── Scene04Mobile.tsx
    │   │   ├── Scene05OpenSource.tsx
    │   │   └── Scene06CTA.tsx
    │   └── components/
    │       ├── AnimatedTitle.tsx
    │       └── LogoLibreFolio.tsx
    └── public/
        └── assets/
            ├── en/
            ├── it/
            ├── es/
            └── fr/
```

---

## 🔧 FASE 0 — Pre-requisiti da verificare

Prima di procedere, accertarsi che sull'host siano presenti:

| Tool | Versione minima | Comando di verifica |
|------|----------------|---------------------|
| Node.js | ≥ 18 LTS | `node -v` |
| npm | ≥ 9 | `npm -v` |
| ffmpeg | qualsiasi | `ffmpeg -version` |

> [!IMPORTANT]
> Remotion **richiede** ffmpeg installato localmente per il render MP4.
> Su macOS: `brew install ffmpeg`

---

## 🚀 FASE 1 — Inizializzazione Progetto Remotion

### Step 1.1 — Creazione progetto

Dalla radice `videoClipPrject/`:

```bash
npx create-video@latest video_promo --template blank-typescript
cd video_promo
```

> [!NOTE]
> Il template `blank-typescript` genera un progetto minimale già con TypeScript configurato, senza scene demo da rimuovere.

### Step 1.2 — Installazione dipendenze aggiuntive

```bash
npm install @remotion/player framer-motion
npm install --save-dev @types/node
```

- **`@remotion/player`**: utile per una eventuale preview nel browser durante lo sviluppo.
- **`framer-motion`**: per le animazioni di Pan & Zoom nelle scene (Scena 3).

### Step 1.3 — Configurazione `remotion.config.ts`

Verificare/sovrascrivere il file con questa configurazione:

```ts
// video_promo/remotion.config.ts
import { Config } from "@remotion/cli/config";

Config.setVideoImageFormat("jpeg");
Config.setOverwriteOutput(true);
Config.setCodec("h264");
Config.setScale(2); // output 2x per qualità 2K/4K
```

### Step 1.4 — Aggiornamento `tsconfig.json`

Assicurarsi che `tsconfig.json` includa:

```json
{
  "compilerOptions": {
    "strict": true,
    "moduleResolution": "bundler",
    "jsx": "react-jsx",
    "allowImportingTsExtensions": true,
    "noEmit": true
  }
}
```

---

## 🌍 FASE 2 — Architettura Multi-lingua (i18n)

### Step 2.1 — Definizione del tipo dizionario

Creare `src/types/i18n.ts`:

```ts
export interface I18nDict {
  scene01: { headline: string; sub?: string };
  scene02: { headline: string };
  scene03: { headline: string; sub: string };
  scene04: { headline: string };
  scene05: { headline: string; sub: string };
  scene06: { headline: string; cta: string };
}

export type Locale = "en" | "it" | "es" | "fr";
```

### Step 2.2 — Dizionario Inglese (lingua pivot)

Creare `src/i18n/en.ts` con i testi definitivi della Sceneggiatura:

```ts
import { I18nDict } from "../types/i18n";

export const en: I18nDict = {
  scene01: {
    headline: "Fragmented investments?",
    sub: "Too many apps and spreadsheets?",
  },
  scene02: {
    headline: "Your wealth, in one private dashboard.",
  },
  scene03: {
    headline: "Stocks, Crypto, ETFs.",
    sub: "Technical analysis included.",
  },
  scene04: {
    headline: "Always with you, wherever you go.",
  },
  scene05: {
    headline: "Open Source and Expandable.",
    sub: "Self-Hosted or Cloud Subscription.",
  },
  scene06: {
    headline: "We are in Alpha.",
    cta: "Discover more: github.com/Librefolio/LibreFolio",
  },
};
```

### Step 2.3 — Stub per le altre lingue

Creare `src/i18n/it.ts`, `src/i18n/es.ts`, `src/i18n/fr.ts` come copie di `en.ts`
con i valori placeholder `"[TO TRANSLATE]"`. Verranno riempiti nella Phase 2 del progetto.

### Step 2.4 — Re-export centrale

Creare `src/i18n/index.ts`:

```ts
import { en } from "./en";
import { it } from "./it";
import { es } from "./es";
import { fr } from "./fr";
import { Locale, I18nDict } from "../types/i18n";

export const dictionaries: Record<Locale, I18nDict> = { en, it, es, fr };
```

---

## 🎬 FASE 3 — Root Composition e Scene Scaffold

### Step 3.1 — Definizione delle Composition in `Root.tsx`

La Composition principale definisce:
- **FPS**: 30
- **Durata totale**: 40 secondi (1200 frame)
- **Risoluzione**: 1920×1080

Il parametro `locale` è iniettato come **inputProps** per rendere tutto parametrizzato.

```tsx
// src/Root.tsx
import { Composition } from "remotion";
import { LibreFolioPromo } from "./MainVideo";
import { Locale } from "./types/i18n";

export const RemotionRoot: React.FC = () => (
  <Composition
    id="LibreFolioPromo"
    component={LibreFolioPromo}
    durationInFrames={1200}
    fps={30}
    width={1920}
    height={1080}
    defaultProps={{ locale: "en" as Locale }}
  />
);
```

### Step 3.2 — Sequenza delle Scene in `MainVideo.tsx`

Creare `src/MainVideo.tsx` che orchestra le scene con `<Series>`:

| Scena | Durata (frame @30fps) | Durata (s) |
|-------|----------------------|------------|
| Scene01 Hook | 150 | 5s |
| Scene02 Hero | 210 | 7s |
| Scene03 MultiAsset | 240 | 8s |
| Scene04 Mobile | 240 | 8s |
| Scene05 OpenSource | 210 | 7s |
| Scene06 CTA | 150 | 5s |
| **Totale** | **1200** | **40s** |

### Step 3.3 — Scaffold delle singole Scene

Creare ogni file in `src/scenes/` come componente React minimale (placeholder) che:
1. Riceve `{ locale: Locale }` come prop
2. Legge il dizionario corretto da `dictionaries[locale]`
3. Mostra il testo in un `<AbsoluteFill>` (da rifinire nella fase di sviluppo visivo)

---

## 🖼️ FASE 4 — Struttura Asset e Placeholder

### Step 4.1 — Creazione cartelle asset

```
public/assets/en/
public/assets/it/
public/assets/es/
public/assets/fr/
```

### Step 4.2 — Asset da produrre (checklist)

Gli asset seguenti vanno generati tramite **Gemini Imagen 3** o catturati dall'app,
e posizionati nella cartella `/en/` in primo luogo:

| File | Scena | Tipo | Stato |
|------|-------|------|-------|
| `chaos_bg.png` | Scena 1 | AI-generated (caos finanziario) | da generare |
| `dashboard_desktop.png` | Scena 2 | Screenshot app | da catturare |
| `echarts_view.png` | Scena 3 | Screenshot app | da catturare |
| `datatable_view.png` | Scena 3 | Screenshot app | da catturare |
| `mobile_mockup.png` | Scena 4 | Screenshot app in mockup | da generare/catturare |
| `opensource_infographic.png` | Scena 5 | AI-generated o icone | da generare |
| `logo_librefolio.svg` | Scena 6 | Logo ufficiale | da copiare dal progetto |

### Step 4.3 — Strategia prompt per Gemini Imagen 3

Per ogni asset AI-generated, i prompt di riferimento sono:

**`chaos_bg.png`** (Scena 1):
```
Abstract digital chaos: overlapping financial charts, spreadsheets, and app icons
scattered on a dark background. Overwhelming, fragmented, dystopian tech aesthetic.
4K, cinematic.
```

**`mobile_mockup.png`** (Scena 4):
```
Modern smartphone mockup (frameless, dark mode) showing a sleek portfolio dashboard
with green/purple gradients. Floating on a subtle gradient background. 4K, minimal design.
```

**`opensource_infographic.png`** (Scena 5):
```
Clean flat infographic icons: open-source symbol (GitHub Octocat), a server/cloud split,
and a puzzle piece for extensibility. Dark background, teal and purple accent colors. 4K.
```

---

## 📦 FASE 5 — Script di Build Multi-lingua

### Step 5.1 — Aggiornamento `package.json`

Aggiungere i seguenti script nella sezione `"scripts"`:

```json
{
  "scripts": {
    "start": "remotion studio",
    "build:en": "remotion render LibreFolioPromo out/librefolio_promo_en.mp4 --props='{\"locale\":\"en\"}'",
    "build:it": "remotion render LibreFolioPromo out/librefolio_promo_it.mp4 --props='{\"locale\":\"it\"}'",
    "build:es": "remotion render LibreFolioPromo out/librefolio_promo_es.mp4 --props='{\"locale\":\"es\"}'",
    "build:fr": "remotion render LibreFolioPromo out/librefolio_promo_fr.mp4 --props='{\"locale\":\"fr\"}'",
    "build:all": "npm run build:en && npm run build:it && npm run build:es && npm run build:fr"
  }
}
```

> [!NOTE]
> Per ora eseguiremo solo `npm run build:en`. Gli altri script sono pronti ma
> vengono attivati solo quando le traduzioni saranno complete.

---

## Checklist di Completamento Fase Setup

- [x] F0 - Node >= 18, npm >= 9, ffmpeg verificati ✅ 2026-06-16 (Node v26.3, npm 11.16, ffmpeg 8.1.1)
- [x] F1.1 - Progetto Remotion inizializzato in `video_promo/` ✅ 2026-06-16 (npm init + install manuale remotion@4.0.478)
- [x] F1.2 - Dipendenze installate (`framer-motion`, `@remotion/player`) ✅ 2026-06-16
- [x] F1.3 - `remotion.config.ts` configurato ✅ 2026-06-16
- [x] F1.4 - `tsconfig.json` verificato ✅ 2026-06-16
- [x] F2.1 - `src/types/i18n.ts` creato (interfaccia `I18nDict` e tipo `Locale`) ✅ 2026-06-16
- [x] F2.2 - `src/i18n/en.ts` creato con testi EN definitivi ✅ 2026-06-16
- [x] F2.3 - Stub `it.ts`, `es.ts`, `fr.ts` creati con placeholder ✅ 2026-06-16
- [x] F2.4 - `src/i18n/index.ts` re-export creato ✅ 2026-06-16
- [x] F3.1 - `src/Root.tsx` con Composition configurata (1920x1080, 30fps, 40s) ✅ 2026-06-16
- [x] F3.2 - `src/MainVideo.tsx` con sequenza `<Series>` delle 6 scene ✅ 2026-06-16
- [x] F3.3 - 6 file in `src/scenes/` scaffoldati come placeholder ✅ 2026-06-16
- [x] F4.1 - Cartelle `public/assets/{en,it,es,fr}/` create ✅ 2026-06-16
- [ ] F4.2 - Asset generati e posizionati (iterativo) ⏳ da fare (Phase 2)
- [x] F5.1 - Script `build:*` in `package.json` ✅ 2026-06-16
- [ ] Studio avviabile - `npm run start` mostra il progetto nel browser ⏳ da verificare live (richiede UI)

---

## Roadmap Post-Setup

```
SETUP (questo piano)
    ↓
Sviluppo visivo Scene EN (colori, font, animazioni Framer Motion)
    ↓
Generazione / inserimento asset (Gemini Imagen 3 + screenshot app)
    ↓
Review video EN → aggiustamenti
    ↓
Traduzione testi IT / ES / FR
    ↓
npm run build:all → 4 video MP4
```
