# Plan: FX Detail Page — Componenti Avanzati e Edit Mode Bidirezionale

**Data creazione**: 12 Marzo 2026
**Status**: 📋 ACCENNATO — da dettagliare quando ci arriviamo
**Priorità**: Media (dopo plan-fxConversionChain)
**Stima**: ~3 giorni
**Dipendenze**: `plan-fxConversionChain.prompt.md` completato (le catene influenzano provider config)
**Riferimenti**:
- `phases/phase-05-subplan/05FX_outofdate_plan/plan-phase05Fx.prompt.md` Steps 4, 6 — task pendenti originali
- `phases/phase-05-subplan/05FX_outofdate_plan/phase05-pending-audit.md` §A (Feature/Code pendenti)
- `phases/phase-05-subplan/plan-fxCardRedesignChartSettings.prompt.md` — architettura chart/signal library

---

## Contesto

La pagina FX detail (`/fx/[pair]`) è funzionante con LineChart, DataZoomBar, MeasureOverlay, DateRangePicker, edit mode CSV, e provider config. Restano da completare i componenti avanzati e il wiring bidirezionale tra chart e CSV editor.

## Task pendenti (da vecchio master plan)

### A1. CandlestickChart.svelte — Completamento
- Stub creato in `src/lib/components/charts/CandlestickChart.svelte`
- Implementare OHLC sintetizzato client-side (FX: O=close giorno precedente, C=rate, H=max, L=min)
- Nota "Simulated OHLC from daily close rates" nella UI
- Toggle Line/Candlestick nel ChartToolbar già presente

### A2. VolumeBar.svelte — Completamento
- Stub creato in `src/lib/components/charts/VolumeBar.svelte`
- Barre Δ% giornaliera (verde positivo, rosso negativo)
- Sub-chart sotto il chart principale, sincronizzato con DataZoomBar

### A3. EditPopup.svelte — Completamento
- Stub creato in `src/lib/components/charts/EditPopup.svelte`
- Click su data point (solo in edit mode) → popup con input numerico
- Integrazione con EditBuffer: modifica → aggiorna buffer + riga CSV
- Punto modificato diventa arancione nel chart

### A4. Bidirezionalità Edit Mode
- Click chart → scroll CSV alla riga corrispondente + open popup
- Modifica CSV → aggiorna chart preview (punto arancione)
- Modifica popup → aggiorna riga CSV corrispondente
- `CsvEditor.svelte` già esiste con validazione live e numeri riga

### A5. Signal Library 7A (bassa priorità)
- Preview pair mode nel ChartSettingsModal: titolo coppia con bandiere + pulsante inversione
- Solo UX polish, funzionalità core ok
- Da `phases/phase-05-subplan/plan-signalLibraryExpansion.prompt.md` Step 7A

---

## Note

Questo plan sarà dettagliato con step implementativi precisi, file da modificare, e test specifici quando verrà preso in carico. I task sopra servono come promemoria dei punti aperti.

