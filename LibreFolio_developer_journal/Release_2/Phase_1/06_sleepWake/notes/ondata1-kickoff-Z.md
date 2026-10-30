# Brief — workstream Z · Sospensione e risveglio · Z-29s-a (backend del campionamento dei segnali)

**Worktree**: `/home/alfy/Documenti/02_myRepo/LibreFolio_prj/LibreFolio-worktrees/e-alfy-potential-sniffle`
**Branch**: `e-alfy-z-sospensione-e-risveglio`
**HEAD di partenza (da verificare)**: `208199bf6` (= `dev_release2`; il tuo ramo è stato portato avanti in fast-forward da `5bbadda95`: non hai commit tuoi fuori da dev).
**Corsia**: porta `6186`, cartella dati `/tmp/librefolio-r13-z`.
**Piano**: `LibreFolio_developer_journal/Release_2/Phase_1/06_sleepWake/plan-phase01SleepWake.prompt.md`. Leggi solo: «Z-29b e Z-29s — analisi breve aggiornata» (riga ~6913) e «Z-29s-a — i segnali ridotti dal backend, la metà backend: lavoro» (riga ~6974). Le bozze di codice sono nella cartella di sessione: `/home/alfy/Documenti/02_myRepo/LibreFolio_prj/copilot-enel/session-state/d401e062-12ee-4187-8b37-dcabd6841c89/files/z29s-draft/`.

## Dove eri rimasto
Z-29a (serie ridotte), Z-29a-f e Z-32 (d) sono già in `dev_release2`. Il 20/10 il coordinatore ti ha dato il via per **Z-29s-a**, la metà backend, durante Y-39 perché non tocca i file di Y. Nel worktree hai **6 file sporchi, solo rossi, nessun codice di prodotto**: `test_api/test_assets_prices.py`, `test_services/test_price_query_sampling.py`, `test_services/test_signal_aggregation.py`, `frontend/src/lib/components/charts/__tests__/timeSeriesAggregation.test.ts`, la nuova tabella `backend/test_scripts/fixtures/signals/signal_sampling_cases.v1.json`, e il piano. **Sono il tuo lavoro: non cancellarli né ripristinarli.**

## Cosa fare ora (un solo lotto)
Contratto (dal tuo piano, già approvato): le voci `signals` di una richiesta prezzi accettano `max_points` / `resolution` / `sample_like` (oggi rispondono 422; eventi e annotazioni restano 422). La voce si legge giornaliera e i segnali si calcolano lì, come oggi; poi la serie di prezzo e le serie dei segnali si **riducono in memoria sui secchi del prezzo**, con il profilo di ogni uscita (`services/signals/aggregation.py`), datate al punto del prezzo come fa `downsampleRenderedSignal`. Il budget conta i giorni, come oggi. Il rendimento mobile (`ASSET_CALENDAR_ROLLING_RETURN`, `LAST_WITH_RANGE`) entra senza casi speciali: il punto scelto è l'elemento stesso, con la sua provenienza. Le tre note di MF per chi consuma la serie (n1 tabella di densità, n2 rileggere al cambio di passo, n3 `sample_bounds.first`) valgono per Z-29b, non per questo lotto.

Passi:
1. Verifica la base e popola la corsia (regole comuni). Rilancia i rossi e **confermane la causa** (devono fallire per il motivo giusto, non per un errore di import o di configurazione).
2. Scrivi la cura (backend). La tabella comune `signal_sampling_cases.v1.json` deve essere letta **sia da pytest sia da Vitest** (`timeSeriesAggregation.test.ts`).
3. Verdi, uno alla volta, carico sotto 8: `services price-query-sampling`, `services signal-aggregation` (e quelle che hai già nel piano), `api assets-price`, il Vitest di `timeSeriesAggregation`, poi `api sync` (nessun cambio inatteso in `generated.ts`) e `front check`.
4. Doc per sviluppatori e piano aggiornati, proposta di CHANGELOG, **CHECKPOINT READY**. I revisori naturali sono MF (semantica) e Y (contratto): lo organizza il coordinatore, tu non scrivere a nessuno.

## Non fare
- **Non toccare i file di Y-39a** (in corso in un'altra sessione): `frontend/src/lib/charts/chartSignalRendering.ts` e i suoi test, `ChartSettingsModal.svelte`, `frontend/src/routes/(app)/assets/+page.svelte`, `frontend/src/routes/(app)/fx/+page.svelte`.
- **Non iniziare Z-29b** (la lista Assets): aspetta che Y-39a entri in `dev_release2`.
- Nessuna decisione di prodotto: il comportamento sull'FX (`/fx/currencies/convert`) resta fuori (Z-29fx, dopo Y-40).

## Fatto quando
I rossi sono verdi per la causa giusta, le suite vicine non regrediscono, `api sync` è pulito, il piano e la doc sono aggiornati e hai scritto **FROZEN**.
