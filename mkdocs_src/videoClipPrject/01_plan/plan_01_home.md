# Plan 1: Restyling della Homepage (MkDocs)

Questo piano dettaglia i passi tecnici per rinnovare la landing page di LibreFolio, procedendo in modo incrementale e sicuro.

## Obiettivi e Vincoli
- Lavorare **esclusivamente** sulla versione inglese (`index.en.md`) per la prima fase.
- Non cancellare la vecchia home: spostarla su un tab temporaneo per facilitare il confronto (A/B testing visivo).
- Creare un CSS isolato per mantenere la base del progetto pulita.

---

## Dettaglio delle Azioni

### Fase 1: Preservare la Vecchia Home
1. **Rinominare e Spostare**: 
   - Copiare il contenuto attuale di `mkdocs_src/docs/index.en.md` in un nuovo file `mkdocs_src/docs/oldHome.en.md`.
2. **Aggiornare la Navigazione**:
   - Modificare `mkdocs_src/mkdocs.yml` per aggiungere temporaneamente la voce "Old Home" nel menu di navigazione, puntando al nuovo file creato, permettendo un rapido confronto.

### Fase 2: Impostare la Nuova Struttura (Solo EN)
1. **Creare il CSS Isolato**:
   - Creare il file `mkdocs_src/docs/stylesheets/home-custom.css`.
   - Definire all'interno le classi per il *glassmorphism*, le animazioni di entrata, il grid system per le card, e il posizionamento dei layer video (sfondo astratto `z-index: -1` e player embed in primo piano).
2. **Aggiornare `mkdocs.yml`**:
   - Assicurarsi che `home-custom.css` sia caricato in `extra_css`.

### Fase 3: Ricostruire `index.en.md`
1. **Hero Section (Doppio Video)**:
   - Sostituire l'SVG attuale con un video background in autoplay e loop.
   - Inserire la call to action principale e il player video centrale per il promo ufficiale.
   - Tradurre i testi in inglese (es. "Free to understand, free to act").
2. **Feature Cards**:
   - Convertire la griglia esistente per adottare il nuovo design premium (glassmorphism, bordi luminescenti).
   - Inserire mockup grafici estratti dalla galleria tra le sezioni descrittive.

### Fase 4: Verifica
- Avviare `mkdocs serve` e navigare tra la root (nuova home) e la scheda "Old Home" per confrontare il colpo d'occhio, l'impatto visivo e le performance.
- Solo dopo l'approvazione finale di questa versione inglese, estenderemo le modifiche ai file `.it.md`, `.fr.md`, `.es.md`.
