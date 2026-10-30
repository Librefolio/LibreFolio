# Brief — workstream J · Numeri e analisi · J-68 (il trasferimento nello stesso giorno dice da dove viene), J-71 (una sola `buildSyncTargets`), verifica di R1 — bozza

> **A cosa serve (per il developer).** Un trasferimento che parte e arriva lo stesso giorno oggi ha nei lotti solo la riga d'arrivo, senza origine: lo Storico dice «In transit → Fineco» senza dire da dove, e il tooltip del Gantt scrive «To Fineco» (Q-G29-1 non inventa l'origine). Con J-68 il backend scrive origine e destinazione anche per quel caso, e lo Storico dice «Da Directa a Fineco». J-71 è un riordino senza effetti visibili: i due pannelli del rischio ricalcolano da soli cosa sincronizzare invece di chiamare la funzione fatta apposta; dopo, una regola sola. R1 (il rischio sulle osservazioni) aspettava Q1 di X: tu verifichi lo stato e lo chiudi o lo rimandi per iscritto.

**Modello**: Sonnet.
**Worktree**: `/home/alfy/Documenti/02_myRepo/LibreFolio_prj/LibreFolio-worktrees/e-alfy-crispy-goggles` · **Branch**: `e-alfy-j-numeri-e-analisi`
**HEAD di partenza (da verificare)**: `c042f2481` (fast-forward dal coordinatore da `0c9a07d9a`).
**Corsia**: porta `6190`, cartella dati `/tmp/librefolio-r13-j`.
**Piano e backlog**: J-68 nel backlog `Phase_0/BACKLOG_POST_1.2.md:7956-7969` e nel tuo piano `05_numbersAnalysis/plan-phase01NumbersAnalysis.prompt.md` §10 «Gantt §29, punto 2»; J-71 backlog `:7985-7990` e piano §10 «Ondata 3 — TC-23 poi L1b», passo A2; R1 piano ~7384, ~7437-7456, ~9075-9096.

## Cosa fare
1. **R1, verifica (un'ora)**: R1 aspetta Q1 di X (`price_query._build_backward_filled_series`, i prezzi per osservazioni). Nel piano di X Q1 è ancora in coda e il piano dell'ondata lo consiglia **fuori dalla 1.3** (domanda 12). Scrivi nel tuo piano lo stato di R1 e la proposta (rimandare con Q1), con il numero dei casi di test già pronti. Nessun codice.
2. **J-68** (backend): `_build_transfer_rows` in `backend/app/services/portfolio/lots_analysis_service.py`: per un trasferimento partito e arrivato lo stesso giorno scrive anche la riga TRANSFER_DEPART (dal frammento di partenza) e mette `source_broker_id`/`destination_broker_id` su entrambe, come fa per i trasferimenti di più giorni. Prima i rossi: un caso nel test puro dei lotti (`services lots-analysis-pure`) e, se il frontend legge le righe, un Vitest dello Storico e del tooltip del Gantt («Da A a B» anche in un giorno). Poi la cura. **Attenzione**: se la cura ti porta dentro `financial_math/` (per esempio `lots/scope_boundary.py` o il motore FIFO), **fermati e dillo**: lì scrive W in questa ondata (Q-N78-1k).
3. **J-71** (frontend): `features/risk/levels/RiskPanelHeader.svelte` e `RiskAnalysisPanel.svelte` usano `features/risk/syncTargets.ts::buildSyncTargets` invece dei loro `syncAssets`/`syncFxPairs`; un test che fissa l'uso (il componente chiama la funzione) e nessun cambio di risultato. Vitest `risk-levels-component`.
4. Verdi: `services lots-analysis-pure` + parità (sulla corsia), Vitest del rischio (in `flock`), `front check` dopo `api sync`, E2E `front-portfolio` dei lotti/Gantt nello slot se la riga nuova cambia ciò che la pagina mostra.
5. Doc: la pagina utente dei lotti se descrive lo Storico (una frase); `mkdocs build` e `check-links`.

## File condivisi
- Tuoi: `portfolio/lots_analysis_service.py`, `features/risk/**`, gli spec dei lotti e del rischio.
- Di W: `financial_math/**`. Di X: `price_query.py` (Q1): non toccarlo.

## Non fare
- Non iniziare R1 senza Q1 di X. Non toccare `financial_math/**` né `features/transactions/**`.

## Fatto quando
R1 verificato e scritto; J-68 rossi→verdi con parità invariata sui casi esistenti; J-71 con il test che fissa l'uso; E2E nello slot se servono; doc e piano aggiornati; righe CHANGELOG proposte (🐛 «un trasferimento nello stesso giorno mostra origine e destinazione nei lotti»; J-71 nessuna riga), **CHECKPOINT READY** e **FROZEN**.
