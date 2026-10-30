# Brief — workstream Z · Sospensione e risveglio · E2E di Z-29d (l'anteprima del dialogo dei confronti) — bozza

> **A cosa serve (per il developer).** Nell'ondata 3 hai avuto Z-29d ridotto: nel dialogo delle impostazioni di una scheda ridotta, un confronto appena scelto compare nell'anteprima prima di salvare. Oggi quel comportamento è provato solo a mano. Con questo lotto esiste la prova automatica, e gira nel gate di ogni treno: se qualcuno rompe l'anteprima, lo sappiamo prima del tag.

**Modello**: Sonnet.
**Worktree**: `/home/alfy/Documenti/02_myRepo/LibreFolio_prj/LibreFolio-worktrees/e-alfy-potential-sniffle` · **Branch**: `e-alfy-z-sospensione-e-risveglio`
**HEAD di partenza (da verificare)**: `c042f2481` (fast-forward dal coordinatore da `29deddba3`).
**Corsia**: porta `6186`, cartella dati `/tmp/librefolio-r13-z`.
**Piano**: `06_sleepWake/plan-phase01SleepWake.prompt.md`, «Z-29d ridotto — lavoro» (~7203) e il seguito «un `data-testid` sul pulsante delle impostazioni della scheda».

## Cosa fare
1. **Aspetta il checkpoint 0 di Y**: una riga in `AssetCard.svelte` con il `data-testid` sul pulsante delle impostazioni (il file è di Y). Il coordinatore ti avvisa quando è committato e la tua base aggiornata. Nel frattempo: leggi `frontend/e2e/assets/*.spec.ts` dove stanno i casi delle schede e scrivi il caso (lo spec, il seed, i passi) senza lanciarlo.
2. **L'E2E** (con `test-author`): apri la lista asset con una scheda ridotta, apri le impostazioni, scegli un confronto, verifica che l'anteprima lo disegni **prima** di salvare, annulla, verifica che la scheda non lo abbia. Localizzatori solo con `data-testid`; nessun testo tradotto; nessuna posizione fissa nella lista (ogni test condivide il DB con i vicini).
3. Registra lo spec nel runner (`scripts/test_runner/_frontend_asset.py`, una riga additiva, `check-orphans` verde). Verde due volte di fila nello slot.

## Non fare
- Non toccare `AssetCard.svelte` né nessun file di Y o X. Niente codice di prodotto: se l'E2E trova un difetto, è una **domanda** per il coordinatore (chi lo cura: Y o Z).

## Fatto quando
Spec nuovo verde due volte nello slot, registrato nel runner, `check-orphans` verde, piano aggiornato, nessuna riga CHANGELOG (è un test), **CHECKPOINT READY** e **FROZEN**.
