# Plan: Round 7.1 — Fix feedback utente post Round 7

**Dipendenze**: [`plan-fxDetailBugRound7.prompt.md`](plan-fxDetailBugRound7.prompt.md)

Refinements basati su feedback utente dopo Round 7.

**Stato**: ✅ Completato (18 Marzo 2026) → Seguito da [`plan-fxDetailBugRound7-2.prompt.md`](plan-fxDetailBugRound7-2.prompt.md)

---

## Steps

### 1. DataTable row colors — Solo `deleted` in trasparenza

I colori di sfondo per edited/appended restano come background tenue. Solo le righe `deleted` hanno i componenti in lieve trasparenza (opacity 0.5 sul contenuto).

### 2. Dark mode — Colori più accesi + bottone cancel leggibile

- Aumentare saturazione colori dark per row-edited, row-appended, row-deleted
- Fix bottone revert/cancel: in dark mode il testo grigio su sfondo grigio è illeggibile → testo più scuro o nero

### 3. SimpleSelect — Dropdown width auto (fit content)

Il dropdown per mese/anno nel CalendarMonth e per granularity nel DateRangePicker è troppo stretto. Aggiungere `w-max min-w-full` al dropdown per adattarsi al contenuto.

### 4. DateRangePicker — Smart direction popover (come SingleDatePicker)

Misurare spazio sopra/sotto e aprire nella direzione con più spazio.

### 5. DataEditor — navigateToRowId migliorato

Funzione pubblica: input = date → calcola pagina → scroll alla riga. Riusabile anche per click su grafico.

### 6. ColumnVisibilityToggle — Eye icon invece di checkbox

Sostituire checkbox con Eye/EyeOff icon. Larghezza dropdown adattata al contenuto. Apertura smart direction.

### 7. MeasurePanel header — Layout responsive a 2 righe

- Riga 1: chevron + DateRangePicker + Δ% + days
- Riga 2: color + line style (min-w-[50px] max-w-[200px] flex-1) + column visibility + trash
- Il DateRangePicker in layout stacked non deve allargarsi oltre il suo max

### 8. headerTooltip — LaTeX rendering

Passare `math={true}` al Tooltip per le formule (es. `(1 + Δ\%)^{365/d} - 1`).

### 9. Misure — Auto-delete su date range invalido

Quando si cambia il date range di una misura e i nuovi estremi non coprono entrambi i punti, cancellare la misura.

### 10. DateRangePicker stacked — max-width constraint

In layout stacked (mobile) il DateRangePicker si allarga troppo. Aggiungere `max-w-full` constraint.

