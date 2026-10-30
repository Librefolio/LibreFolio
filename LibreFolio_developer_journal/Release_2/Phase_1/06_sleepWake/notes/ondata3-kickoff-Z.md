# Brief — workstream Z · Sospensione e risveglio · Z-29fx (serie ridotte e rendimento mobile dei cambi) + Z-29d ridotto

> **A cosa serve (per il developer).** Oggi le schede dei **cambi** chiedono la storia giorno per giorno: con anni di dati sono pesanti, e non sanno mostrare il rendimento mobile. Z-29fx fa per i cambi quello che Z-29b ha fatto per gli asset: il backend manda solo i punti che la scheda disegna (per esempio ~200 invece di ~1 800) e calcola il rendimento mobile, così Y-40 può offrire le tre viste anche nella lista cambi. Z-29d ridotto: l'anteprima del dialogo di confronto si ricarica per scheda con le serie ridotte invece di quelle giornaliere.

**Worktree**: `/home/alfy/Documenti/02_myRepo/LibreFolio_prj/LibreFolio-worktrees/e-alfy-potential-sniffle` · **Branch**: `e-alfy-z-sospensione-e-risveglio`
**HEAD di partenza (da verificare)**: `2879ae3e4` (= `dev_release2`; fast-forward fatto dal coordinatore).
**Corsia**: porta `6186`, cartella dati `/tmp/librefolio-r13-z`.
**Piano**: `LibreFolio_developer_journal/Release_2/Phase_1/06_sleepWake/plan-phase01SleepWake.prompt.md`: Z-29fx (righe ~6964-6969), Z-29d «ridotto» (~6927), le note di MF n1-n3 (~6502). Backlog Z-29 (~8207-8225), Z-40 (~8367-8390).

## Passo A — Z-29fx, backend
`POST /fx/currencies/convert` accetta `max_points`, `resolution`, `sample_like` e restituisce `sample_bounds`, con la stessa regola di `/assets/prices/query` (riduzione in memoria sui secchi, budget in giorni, segnali ridotti con le serie allineate come in O1, rendimento mobile del dominio cambi con la sua provenienza). Riusa `services/signals/aggregation.py` e il campionamento esistente: niente seconda implementazione (regola «una sola casa per la matematica finanziaria», `backend.instructions.md`).
- Prima i rossi (servizio, API, la tabella comune se serve un caso cambi), poi la cura, poi `api sync` (il `generated.ts` cambierà: dillo nel checkpoint).
- **Solo backend**: la pagina dei cambi (`fx/+page.svelte`, `FxCard`) la fa **Y** in Y-40; tu non la tocchi.
- Verdi: le azioni `services`/`api` dei cambi e del campionamento (nomi esatti dal runner), `signal-aggregation`, `price-query-sampling`.
- Consegna **CHECKPOINT READY (A)** e FROZEN: Y aspetta questo commit.

## Passo B — Z-29d ridotto (dopo il via del coordinatore)
L'anteprima del dialogo dei confronti si ricarica per scheda con le serie ridotte (`_basePoint` di Z-29d-0 è già in dev). Stima 0,5-0,75 giorni. File e test: dal piano. Attenzione: `ChartSettingsModal.svelte` e `assets/+page.svelte` li tocca Y in Y-40; **se ti servono, fermati e chiedi**.

## Non fare
- Non toccare i file di Y-40 (vedi sopra), `lib/theme/**`, `lib/features/transactions/**`.
- Le osservazioni R1-R4 di Z-40 restano «nessuna cura» salvo richiesta di MF o Y.

## Fatto quando
A: rossi→verdi, `api sync` con il diff atteso descritto, doc per sviluppatori (`developer/backend/assets/architecture.md` o la pagina dei cambi) e piano aggiornati, checkpoint. B: idem, E2E solo se il coordinatore ti dà lo slot. Righe CHANGELOG proposte. **FROZEN**.
