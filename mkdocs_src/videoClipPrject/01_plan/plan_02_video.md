# Plan 2: Produzione Video Promo (Remotion)

Questo piano dettaglia la creazione del video di presentazione tramite codice (React) usando Remotion, con un'architettura progettata fin dall'inizio per supportare il multi-lingua.

## Obiettivi e Vincoli
- Creare il progetto in **Remotion** per avere il massimo controllo sulle animazioni e i timing.
- Impostare lo sviluppo inizialmente in **Inglese**.
- Strutturare il codice in modo che testi e screenshot dipendano da una variabile `locale`. In questo modo potremo compilare (build) 4 video diversi semplicemente passando la lingua desiderata.

---

## Dettaglio delle Azioni

### Fase 1: Setup Architettura Multi-lingua
1. **Inizializzazione Remotion**:
   - Creare un nuovo progetto Remotion in una cartella dedicata (es. `video_promo/`).
2. **Dizionari e Asset Dinamici**:
   - Creare un file di configurazione delle lingue (`i18n.ts`) che esporti i testi (es. `en`, `it`, `es`, `fr`).
   - Organizzare le cartelle degli asset statici (gli screen dalla galleria) dividendole per lingua: `public/assets/en/`, `public/assets/it/`, ecc.
   - Definire un parametro di composizione `locale` in Remotion per iniettare i testi e caricare le immagini corrette in base al target di compilazione.

### Fase 2: Montaggio delle Scene (Sviluppo in EN)
Inizieremo assemblando le scene in Inglese seguendo questa scaletta (testi provvisori):

1. **Scena 1 (Hook - 5s)**: *Investimenti caotici* -> Generazione asset caos via Gemini Imagen 3.
   - Testo EN: "Fragmented investments? Too many apps and spreadsheets?"
2. **Scena 2 (Hero - 7s)**: *Svelamento Dashboard* -> Transizione elegante sulla dashboard Desktop.
   - Testo EN: "Your wealth, in one private dashboard."
3. **Scena 3 (Multi-Asset - 8s)**: *ECharts e DataTable* -> Pan & Zoom via CSS/Framer Motion all'interno di Remotion.
   - Testo EN: "Stocks, Crypto, ETFs. Technical analysis included."
4. **Scena 4 (Mobile - 8s)**: *Mockup Smartphone*.
   - Testo EN: "Always with you, wherever you go."
5. **Scena 5 (Flessibilità - 7s)**: *Open Source e Abbonamento* -> Icone o infografica (generata via Gemini).
   - Testo EN: "Open Source and Expandable. Self-Hosted or Cloud Subscription."
6. **Scena 6 (Call to Action - 5s)**: *Fase Alpha & GitHub* -> Logo LibreFolio.
   - Testo EN: "We are in Alpha. Discover more and contribute at: github.com/Librefolio/LibreFolio"

### Fase 3: Generazione Asset (Iterativa)
- Qualsiasi grafica mancante (es. background animato iniziale o icone complesse) verrà creata durante lo sviluppo tramite prompt a **Gemini Pro (Imagen 3)**.

### Fase 4: Build e Render
- Implementare script in `package.json` per esportare i video. 
  - `npm run build:en`
  - `npm run build:it` (che faremo in un secondo momento)
- Il risultato finale saranno N video MP4, uno per ogni lingua supportata.
