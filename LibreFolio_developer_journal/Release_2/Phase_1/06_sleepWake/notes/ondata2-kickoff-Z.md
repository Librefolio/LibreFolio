# Brief — workstream Z · Sospensione e risveglio · O1 + Z-29b (la lista Assets chiede serie ridotte)

**Worktree**: `/home/alfy/Documenti/02_myRepo/LibreFolio_prj/LibreFolio-worktrees/e-alfy-potential-sniffle`
**Branch**: `e-alfy-z-sospensione-e-risveglio`
**HEAD di partenza (da verificare)**: `89e8b2e61` (= `dev_release2`; Z-29s-a e Y-39a sono già in dev dal treno 6; fast-forward fatto dal coordinatore).
**Corsia**: porta `6186`, cartella dati `/tmp/librefolio-r13-z`.
**Piano**: `LibreFolio_developer_journal/Release_2/Phase_1/06_sleepWake/plan-phase01SleepWake.prompt.md`. Leggi solo: le note di MF n1–n3 (riga ~6502), «Z-29b e Z-29s — analisi breve aggiornata» (~6913), «Z-29b, il contratto della pagina» (~6931). Nel backlog `Phase_0/BACKLOG_POST_1.2.md` la voce Z-40 con le osservazioni O1–O4 della revisione di Y su Z-29s-a.

## Due passi, in quest'ordine

### Passo A — O1 (prima di Z-29b)
Dopo la riduzione le serie dello stesso segnale possono avere date diverse (`services/signals/aggregation.py:129`, `_scalar_points`: ogni serie si riduce da sola e scarta i nulli iniziali), mentre `_validate_series_alignment` (`backend/app/schemas/signals.py:1127`) le vuole allineate. Casi: MACD, ADX, Aroon, PPO con riscaldamento diverso dentro l'intervallo.
1. Scrivi il **rosso**: un caso a due serie con riscaldamento diverso (nella tabella comune `signal_sampling_cases.v1.json`, letta da pytest e Vitest) che mostra il disallineamento.
2. **Decisione del developer (21/10): ALLINEARE.** Tutte le serie di un segnale escono con le **stesse date dei secchi**; dove una serie non ha valore (riscaldamento) il punto c'è ma è vuoto (`null`), invece di sparire. `_validate_series_alignment` resta com'è. Se allineare rompe qualcosa che il contratto di Z-29s-a prometteva (per esempio il Vitest della tabella comune o il disegno serie per serie), fermati e chiedi.
3. Verdi: `services signal-aggregation`, `services price-query-sampling`, `api assets-price`, il Vitest di `timeSeriesAggregation`; `test_schemas` per `test_signal_schemas.py`.
4. **O3**: nella doc per sviluppatori scrivi che con la riduzione del backend restano solo la data del secchio e la provenienza. **O4**: Z-29b non deve dedurre il passo dalla densità delle serie dei segnali.
Consegna un **CHECKPOINT READY intermedio** (A) e scrivi FROZEN: il coordinatore lo committa prima di farti partire con B.

### Passo B — Z-29b (solo dopo il via del coordinatore sul passo A)
Il contratto del piano (~6931): ogni scheda manda la sua voce con `key` e `max_points` dalla larghezza misurata (`compactMaxPoints(w)`, la soglia 1,3 spostata da `LineChart.svelte` in `timeSeriesAggregation.ts`); i bersagli dei confronti con `sample_like`; `bulkBatches.ts` taglia per gruppi (scheda + bersagli), anche dopo `bulk_too_many_days`; una cache ridotta accanto alla giornaliera (stesso bus `{kind: 'prices'}`); al cambio di passo si rilegge (MF n2); base della percentuale e colore della linea da `sample_bounds.first` (MF n3), passata a `LineChart` con la prop **`baselineValue`** che Y aggiunge in Y-39b; ricarica per scheda; le schede con segnali del backend mandano `max_points` come le altre (Z-29s-a è in dev).
- Rossi: Vitest (n1: `compactDensityCases.json` con la regola del browser e i `max_points` della pagina; piano a gruppi; cache ridotta; base da `first`; bersagli). Poi la cura. Poi `front check` (dopo `api sync`) in `flock`.
- **E2E `front-asset asset-list` solo con lo slot**, e **dopo** quello di Y (stesso spec).

## Non fare
- **`LineChart.svelte` lo tocca anche Y-39b** (riga `:450` e la prop `baselineValue`). Tu tocchi solo la soglia della densità (`:193`, `:296-301`). Se la prop di Y non è ancora in dev quando ti serve, **non scriverla tu**: chiedi al coordinatore.
- Non toccare i file di Y-39b: l'anteprima del grafico del dettaglio (`ChartSettingsModal.svelte` e `PriceChartFull`), `chartSignalRendering.ts`.
- Le coppie FX restano fuori (Z-29fx, dopo Y-40). Niente Z-29s (rendimento mobile): è il lotto dopo.

## Fatto quando
A: rosso di O1 scritto, cura secondo la decisione, verdi, doc O3/O4, checkpoint intermedio. B: rossi verdi per la causa giusta, `front check` 0/0, doc e piano aggiornati, righe CHANGELOG proposte, **CHECKPOINT READY** e **FROZEN**; E2E nello slot.
