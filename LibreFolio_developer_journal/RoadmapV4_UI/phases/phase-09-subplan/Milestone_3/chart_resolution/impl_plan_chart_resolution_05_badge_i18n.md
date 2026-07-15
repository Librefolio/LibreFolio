# Piano Implementativo: Chart Resolution 05 — Badge shared + i18n `chart.*` (Milestone_3)

> **Stato: ✅ implementato** — `frontend/src/lib/components/charts/ResolutionBadge.svelte` esiste ed è
> riusato dai 3 consumer (`[01]`/`[02]`/`[03]`), chiavi i18n `chart.*` presenti nelle 4 lingue.

> **Deriva da**: [`./study_chart_dynamic_resolution.md`](./study_chart_dynamic_resolution.md) — sez. [14. Tooltip bucket-aware](./study_chart_dynamic_resolution.md#14-tooltip-bucket-aware) (`:915-949`) e sez. [18. Badge di aggregazione](./study_chart_dynamic_resolution.md#18-badge-di-aggregazione) (`:1140-1175`).
> **Prerequisito minimo condiviso**: [`./impl_plan_chart_resolution_00_foundation.md`](./impl_plan_chart_resolution_00_foundation.md) (`[00]`, union canonica `ChartResolution = 'daily' | 'weekly' | 'monthly'`, fissata a `:45-63`).
> **Consumer che devono riusare questo contratto senza reinventarlo**: [`./impl_plan_chart_resolution_01_price_candlestick.md`](./impl_plan_chart_resolution_01_price_candlestick.md) · [`./impl_plan_chart_resolution_02_growth_chart.md`](./impl_plan_chart_resolution_02_growth_chart.md) · [`./impl_plan_chart_resolution_03_allocation_history.md`](./impl_plan_chart_resolution_03_allocation_history.md).
> **Ambito**: solo progettazione di (1) nuovo componente Svelte condiviso badge risoluzione e (2) nuove chiavi i18n sotto `chart.*`. Nessun file `.svelte` / `.json` sorgente viene toccato in questo task.

## Principio guida

> Tenere badge e lessico i18n **centralizzati e dumb**: un solo componente presentazionale shared, una sola famiglia di chiavi `chart.*`, nessuna logica di scelta soglia dentro il badge, nessuna duplicazione di stringhe nei 3 consumer. I consumer decidono **quando** mostrare `weekly/monthly`; il badge decide solo **come** renderizzare quella risoluzione.

Ogni step sotto dichiara esplicitamente cosa è **Riuso** vs cosa è **Nuovo**.

## Stato attuale

- **Riuso — contratto tipo già fissato da [00]**: `ChartResolution` è già canonico e va riusato senza alias (`daily | weekly | monthly`) (`impl_plan_chart_resolution_00_foundation.md:45-63`).
- **Riuso — requisito badge già esplicito nello studio**: niente badge per `daily`; badge sintetico solo `Settimanale` / `Mensile`; niente label lunghe tipo `Vista: Settimanale` (`study_chart_dynamic_resolution.md:1142-1166`).
- **Riuso — tooltip bucket-aware già richiesto nello studio**:
  - weekly: `Settimana {start} – {end}` + riga contestuale `Valore al {date}` (`study_chart_dynamic_resolution.md:926-931`);
  - monthly: header mese + anno + riga contestuale `Valore al {date}` (`study_chart_dynamic_resolution.md:933-949`).
- **Riuso — namespace i18n `chart.*` esiste già in tutti e 4 i file locale**, con nesting coerente:
  - `frontend/src/lib/i18n/en.json:537-546`
  - `frontend/src/lib/i18n/it.json:537-546`
  - `frontend/src/lib/i18n/fr.json:537-546`
  - `frontend/src/lib/i18n/es.json:537-546`
  Contiene oggi `chart.tooltip.stale`, `chart.tooltip.fxStale`, `chart.tooltip.percentNote`, `chart.tooltip.upper`, `chart.tooltip.lower`, `chart.showPercentage`, `chart.showAbsolute`.
- **Riuso — `PriceChartFull` ha già wrapper `.relative` corretto per overlay DOM**, ma possiede anche un overlay esistente da non sovrapporre: toggle tipo grafico in `absolute top-2 left-12` (`frontend/src/lib/components/charts/PriceChartFull.svelte:867-883`).
- **Riuso — `GrowthChart` ha già wrapper `.relative` libero in alto a sinistra**, oggi con solo skeleton / empty overlay + chart container (`frontend/src/lib/components/dashboard/GrowthChart.svelte:571-581`).
- **Riuso — `AllocationHistoryChart` ha già wrapper `.relative` libero in alto a sinistra**, oggi con solo skeleton / empty overlay + chart container (`frontend/src/lib/components/dashboard/AllocationHistoryChart.svelte:287-295`).
- **Nuovo al 100%**: nel tree attuale non esiste ancora un componente shared tipo `ResolutionBadge.svelte` e non esistono chiavi `chart.resolution.*` / `chart.tooltip.weekRange` verificate via grep in questo task.

## Gap

1. Manca un componente shared unico per badge non-daily; senza questo, i doc [01]/[02]/[03] rischiano 3 pill diverse per markup, classi e testi.
2. Manca un contratto di posizionamento riusabile che rispetti il conflitto reale di `PriceChartFull` con toggle `top-2 left-12`, ma resti minimale per `GrowthChart` e `AllocationHistoryChart`.
3. Manca un namespace i18n dedicato a:
   - label badge `weekly` / `monthly`;
   - header tooltip weekly;
   - header/seconda riga bucket-aware condivisa;
   - intestazione eventi aggregati nel periodo.
4. Manca scelta esplicita su **dove** vive l’anchor assoluto: nel badge shared o nel consumer.

## Decisioni prese (non più aperte)

| Decisione | Scelta |
|---|---|
| Nome file shared | **Nuovo** `frontend/src/lib/components/charts/ResolutionBadge.svelte` |
| Responsabilità componente | **Solo presentazionale**: riceve `resolution`, traduce testo badge, rende pill; nessuna logica ECharts, nessuna soglia, nessun listener |
| Props pubbliche | `resolution: ChartResolution` **obbligatoria e unica prop funzionale**; niente `label`, niente `variant`, niente `position` |
| Comportamento `daily` | Il componente ritorna `null` / non renderizza nulla quando `resolution === 'daily'` |
| Posizionamento shared | **Non dentro il componente**. L’anchor assoluto resta del consumer; il badge shared resta `inline-flex` puro. Motivo: serve un offset speciale solo in `PriceChartFull`, non negli altri 2 chart |
| Anchor standard consumer | `absolute top-2 left-2 z-10 pointer-events-none` per `GrowthChart` e `AllocationHistoryChart` |
| Anchor speciale consumer [01] | `absolute top-2 left-28 z-10 pointer-events-none` in `PriceChartFull`, per stare a destra del toggle già presente in `top-2 left-12` (`frontend/src/lib/components/charts/PriceChartFull.svelte:869-883`) |
| Owner badge nel doc [01] | **`PriceChartFull`, non `CandlestickChart`**. Un solo overlay owner evita divergenze tra vista linea e vista candela |
| Styling badge | Pill compatta, coerente col toggle esistente: `rounded-full`, `border`, `bg-white/90 dark:bg-slate-800/90`, `text-[11px] font-medium`, `shadow-sm`; testo sintetico solo `Weekly/Monthly` localizzato |
| Testo badge | `chart.resolution.weekly` / `chart.resolution.monthly`; **nessuna** chiave `daily` perché daily non mostra badge |
| Tooltip weekly | Nuova chiave `chart.tooltip.weekRange` con placeholder `{start}` / `{end}` |
| Tooltip monthly header | Nuova chiave `chart.tooltip.monthLabel` con placeholder `{month}` già preformattato locale (es. `January 2026`, `Gennaio 2026`) |
| Tooltip riga contestuale bucket | Nuova chiave condivisa `chart.tooltip.valueAt` con placeholder `{date}`; stessa frase per weekly e monthly |
| Tooltip marker aggregati | Nuova chiave `chart.tooltip.eventsInPeriod` per intestazione della lista eventi bucketizzati |

## Ordine di implementazione

```text
STEP 0A [00] Foundation
   └─ export type ChartResolution = 'daily' | 'weekly' | 'monthly'
            │
            ├──────────────┐
            ▼              ▼
STEP 0B [05] Badge+i18n    STEP 1 [01]/[02]/[03] Consumer wiring
   ├─ ResolutionBadge      ├─ PriceChartFull anchor special-case
   └─ chart.resolution.*   ├─ GrowthChart anchor standard
      + chart.tooltip.*    └─ AllocationHistoryChart anchor standard
```

`[05]` è quindi **parallelo concettualmente** a `[00]`, ma usa il nome tipo già fissato da `[00]`; non dipende da alcuna logica di aggregazione, cache, debounce o dataZoom.

---

## STEP 1 — Nuovo componente shared `ResolutionBadge.svelte`

### 1.1 Contratto pubblico

- **Nuovo**: file `frontend/src/lib/components/charts/ResolutionBadge.svelte`.
- **Riuso**: tipo importato da `[00]`, non ridefinito localmente (`impl_plan_chart_resolution_00_foundation.md:45-63`).
- **Nuovo**: contratto pubblico minimo:

```ts
import type {ChartResolution} from '$lib/components/charts/timeSeriesAggregation';

type Props = {
    resolution: ChartResolution;
};
```

- **Regola**:
  - `daily` → render nulla;
  - `weekly` → testo `chart.resolution.weekly`;
  - `monthly` → testo `chart.resolution.monthly`.

### 1.2 Sketch Svelte minimale

> Sketch concettuale. Non è codice scritto nei sorgenti in questo task.

```svelte
<script lang="ts">
    import { _ } from 'svelte-i18n';
    import type { ChartResolution } from '$lib/components/charts/timeSeriesAggregation';

    let { resolution }: { resolution: ChartResolution } = $props();

    const LABEL_KEY = {
        weekly: 'chart.resolution.weekly',
        monthly: 'chart.resolution.monthly',
    } as const;
</script>

{#if resolution !== 'daily'}
    <span
        class="inline-flex items-center rounded-full border border-gray-200/70 bg-white/90 px-2 py-1 text-[11px] font-medium text-gray-600 shadow-sm dark:border-slate-600/70 dark:bg-slate-800/90 dark:text-slate-200"
        data-testid="chart-resolution-badge"
    >
        {$_(LABEL_KEY[resolution])}
    </span>
{/if}
```

### 1.3 Contratto di posizionamento per i 3 consumer

- **Decisione chiave**: il componente shared **non** contiene classi `absolute top-* left-*`.
- **Motivo**: `PriceChartFull` ha collisione reale col toggle overlay in `top-2 left-12` (`frontend/src/lib/components/charts/PriceChartFull.svelte:869-883`), mentre `GrowthChart` e `AllocationHistoryChart` hanno top-left libero (`frontend/src/lib/components/dashboard/GrowthChart.svelte:571-581`, `frontend/src/lib/components/dashboard/AllocationHistoryChart.svelte:287-295`).
- **Contratto riusabile**:
  1. consumer deve montare `<ResolutionBadge>` come figlio diretto del wrapper plot `.relative`;
  2. consumer aggiunge un wrapper anchor assoluto esterno;
  3. il badge usa `pointer-events-none` sul wrapper anchor, così non disturba pan/zoom/click chart.

#### Anchor per consumer

| Consumer | Anchor raccomandato | Motivo |
|---|---|---|
| `PriceChartFull` ([01]) | `absolute top-2 left-28 z-10 pointer-events-none` | evita overlap col toggle `absolute top-2 left-12`; stesso baseline verticale, nessun salto tra vista line/candlestick |
| `GrowthChart` ([02]) | `absolute top-2 left-2 z-10 pointer-events-none` | top-left oggi libero; wrapper `.relative` già esiste |
| `AllocationHistoryChart` ([03]) | `absolute top-2 left-2 z-10 pointer-events-none` | top-left oggi libero; wrapper `.relative` già esiste |

#### Sketch consumer-side

```svelte
<div class="relative">
    <div class="absolute top-2 left-2 z-10 pointer-events-none">
        <ResolutionBadge resolution={currentResolution} />
    </div>

    <!-- chart container -->
</div>
```

Nel doc [01], solo l’anchor diventa `left-28`.

---

## STEP 2 — Nuove chiavi i18n `chart.*`

### 2.1 Posizione JSON

- **Riuso**: espandere il blocco `chart` già esistente, senza creare namespace fratelli (`frontend/src/lib/i18n/en.json:537-546`, `frontend/src/lib/i18n/it.json:537-546`, `frontend/src/lib/i18n/fr.json:537-546`, `frontend/src/lib/i18n/es.json:537-546`).
- **Nuovo**: due sottogruppi coerenti:
  - `chart.resolution.*`
  - nuove chiavi dentro `chart.tooltip.*`

### 2.2 Tabella completa chiavi × traduzioni

| Chiave | EN | IT | FR | ES |
|---|---|---|---|---|
| `chart.resolution.weekly` | `Weekly` | `Settimanale` | `Hebdomadaire` | `Semanal` |
| `chart.resolution.monthly` | `Monthly` | `Mensile` | `Mensuel` | `Mensual` |
| `chart.tooltip.weekRange` | `Week {start} – {end}` | `Settimana {start} – {end}` | `Semaine {start} – {end}` | `Semana {start} – {end}` |
| `chart.tooltip.monthLabel` | `{month}` | `{month}` | `{month}` | `{month}` |
| `chart.tooltip.valueAt` | `Value at {date}` | `Valore al {date}` | `Valeur au {date}` | `Valor al {date}` |
| `chart.tooltip.eventsInPeriod` | `Events in period:` | `Eventi nel periodo:` | `Événements sur la période :` | `Eventos en el período:` |

### 2.3 Note d’uso vincolanti per [01]/[02]/[03]

- **`chart.tooltip.monthLabel`**:
  - non localizza i mesi via JSON;
  - riceve invece `month` già formattato nel locale attivo (es. `January 2026`, `Gennaio 2026`, `Janvier 2026`, `Enero de 2026`);
  - serve solo a mantenere contratto stringa uniforme nel namespace `chart.tooltip.*`.
- **`chart.tooltip.valueAt`**:
  - è volutamente **generica**;
  - weekly e monthly la riusano identica;
  - evita doppioni inutili tipo `weekValueAt` / `monthValueAt`.
- **`chart.tooltip.eventsInPeriod`**:
  - usata solo quando un tooltip di bucket mostra marker aggregati;
  - la lista sotto resta composta da date/testi reali evento, come richiesto dallo studio (`study_chart_dynamic_resolution.md:940-949`).
- **Nessuna chiave `chart.resolution.daily`**:
  - scelta intenzionale;
  - daily non mostra badge, quindi chiave superflua.

### 2.4 Shape JSON raccomandata

> Sketch concettuale. Non è JSON scritto nei file locale in questo task.

```json
"chart": {
  "tooltip": {
    "stale": "...",
    "fxStale": "...",
    "percentNote": "...",
    "upper": "...",
    "lower": "...",
    "weekRange": "Week {start} – {end}",
    "monthLabel": "{month}",
    "valueAt": "Value at {date}",
    "eventsInPeriod": "Events in period:"
  },
  "resolution": {
    "weekly": "Weekly",
    "monthly": "Monthly"
  },
  "showPercentage": "...",
  "showAbsolute": "..."
}
```

Ordine suggerito: lasciare `tooltip` come primo blocco sotto `chart`, inserendo le nuove chiavi in continuità con quelle esistenti; aggiungere poi `resolution` prima di `showPercentage` / `showAbsolute`, così tutto il lessico chart-specific resta raccolto nello stesso namespace top-level.

---

## STEP 3 — Checklist di integrazione per i documenti fratelli

### 3.1 Doc [01] — `PriceChartFull` / `CandlestickChart`

- **Riuso**: wrapper `.relative` già esistente (`frontend/src/lib/components/charts/PriceChartFull.svelte:867-909`).
- **Nuovo**:
  - import `ResolutionBadge.svelte` nel parent `PriceChartFull`;
  - render un solo badge per entrambe le viste;
  - anchor `absolute top-2 left-28 z-10 pointer-events-none`;
  - usare chiavi `[05]` per header tooltip weekly/monthly e marker aggregati.

### 3.2 Doc [02] — `GrowthChart`

- **Riuso**: wrapper `.relative` già esistente (`frontend/src/lib/components/dashboard/GrowthChart.svelte:571-581`).
- **Nuovo**:
  - anchor standard `top-2 left-2`;
  - `chart.tooltip.weekRange`, `chart.tooltip.monthLabel`, `chart.tooltip.valueAt` per header bucket-aware.

### 3.3 Doc [03] — `AllocationHistoryChart`

- **Riuso**: wrapper `.relative` già esistente (`frontend/src/lib/components/dashboard/AllocationHistoryChart.svelte:287-295`).
- **Nuovo**:
  - anchor standard `top-2 left-2`;
  - stesse chiavi tooltip di [02], senza creare varianti dedicate per chart allocazione.

---

## Nota finale

Questo task produce **solo** documento di pianificazione. **Nessuna riga di codice Svelte o JSON i18n è stata scritta**.
