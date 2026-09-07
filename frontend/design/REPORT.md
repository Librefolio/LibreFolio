# Report — Estrazione Design System LibreFolio

Data: 2026-07-24
File collegato: [`design-system.html`](./design-system.html) (artifact autocontenuto, apribile da browser)

## Contesto

Richiesta originale: usare `/design-sync` per portare il design system di LibreFolio su
claude.ai/design.

**Bloccante tecnico**: `/design-sync` e il tool `DesignSync` compilano i componenti
assumendo **React** (shim su `window.React`/`window.ReactDOM`, runtime JSX, output
`.jsx`/`.d.ts`). Il frontend di LibreFolio è **SvelteKit + Svelte 5**
(`frontend/package.json`), quindi i componenti reali non possono essere renderizzati da
quel runtime. Ricrearli come cloni React per "ingannare" il tool avrebbe violato il
principio guida dello skill stesso ("mai una reimplementazione") e prodotto codice non
corrispondente a quello effettivamente spedito in produzione.

**Scelta concordata con l'utente**: niente progetto claude.ai/design. Produrre invece un
documento di riferimento statico (`design-system.html`), estratto dal codice sorgente e
verificato a runtime.

## Metodologia

1. **Estrazione statica** — lettura diretta di:
   - `frontend/src/app.css` (token colore `@theme`, sistema tema chiaro/scuro,
     variabili `--theme-*`)
   - `frontend/tailwind.config.js`
   - `frontend/src/lib/components/ui/**` (~30 componenti letti per intero: modali,
     select/dropdown, feedback, tab/toolbar, date picker, data editor, media)
   - `frontend/src/lib/i18n/**` (lingue supportate, locale di default, meccanismo di
     rilevamento)
2. **Verifica a runtime** — avvio di `dev.py server` (porta 6040, DB di produzione),
   login come utente `alfy` via Chrome automation, navigazione e screenshot di:
   dashboard (chiaro/scuro), selettore lingua, tabella transazioni, griglia asset,
   modale "Add Asset", dettaglio asset con grafico, pannello Impostazioni → Preferences
   (controllo ufficiale tema/lingua).
3. **Composizione** — un unico file HTML autocontenuto (`design-system.html`, ~860 KB,
   9 screenshot incorporati come data URI) organizzato come pagina di riferimento con
   navigazione laterale, pensato per essere letto da un designer o da un altro sviluppatore
   senza bisogno di clonare il repo o avviare il server.

## Principali risultati

- **Brand**: verde `#1a4031` (`libre-green`) come accento primario, beige `#f5f4ef`
  (`libre-beige`) come sfondo di base. In tema scuro `libre-green` **non viene
  semplicemente schiarito**: è ridefinito a `#00d681`, una scelta deliberata per il
  contrasto su `#0f172a`.
- **Tema chiaro/scuro**: doppio strato sopra Tailwind — oltre alle utility `dark:`,
  un set di custom property semantiche (`--theme-bg-*`, `--theme-text-*`,
  `--theme-border-*`, `--theme-accent`) ridefinite su `html.dark` e applicate anche
  sopra classi Tailwind comuni (es. `html.dark .bg-white`). Uno script anti-FOUC in
  `app.html` evita il flash al primo paint.
- **Nessun componente `Button.svelte` atomico**: i pulsanti sono classi scoped
  per-componente (`.btn-primary`, `.btn-danger`, `.btn-warning`, `.btn-secondary`) che
  riusano gli stessi hex in punti diversi del codice — è una convenzione, non un
  componente condiviso.
- **Pattern più distintivo**: `PageToolbar` implementa 4 livelli responsivi
  (`oneRow` / `denseRow` / `stackFilters` / `oneColumn`) guidati da un
  `ResizeObserver` sul proprio contenitore, non dai breakpoint del viewport — resta
  corretto anche annidato in pannelli stretti. Le etichette troppo lunghe (es. francese
  "Vue d'ensemble") vengono rimpicciolite in blocco con una scala lineare misurata a
  runtime (`labelShrink.ts`), mai nascoste silenziosamente.
- **i18n**: 4 lingue (EN default, IT, FR, ES) via `svelte-i18n`, selettore con bandiera
  sempre visibile in header, persistenza su `localStorage`.
- **Icone**: `lucide-svelte` in tutto il prodotto; le bandiere lingua usano uno stack
  font emoji dedicato (`.emoji-flag`: Apple Color Emoji poi Noto Color Emoji) per resa
  coerente cross-piattaforma.
- **Grafici**: ECharts, con un sistema di overlay "signal" configurabile
  (`SignalTreeSelect`, `SignalStyleEditor`, `MeasurePanel`) sopra i grafici prezzo.

## Limiti noti

- Documento statico: non è collegato a claude.ai/design e non si aggiorna da solo se il
  codice cambia — va rigenerato manualmente (rilettura sorgenti + nuovi screenshot).
- Copertura component-level qualitativa, non esaustiva: sono stati letti i componenti
  condivisi in `components/ui/**`; componenti specifici di dominio (es. in
  `components/charts`, `components/brokers`, `components/transactions`) sono citati ma
  non tutti aperti singolarmente.
- Gli screenshot riflettono lo stato dei dati dell'utente `alfy` sul DB di produzione al
  momento della cattura (24 luglio 2026).
