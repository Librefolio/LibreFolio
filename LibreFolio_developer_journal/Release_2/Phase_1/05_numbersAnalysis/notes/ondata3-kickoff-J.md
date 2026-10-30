# Brief — workstream J · Numeri e analisi · TC-23 (aggiungere il cambio mancante senza uscire dall'analisi) poi L1b (lotti più veloci)

> **A cosa serve (per il developer).**
> - **TC-23**: nei pannelli di analisi del rischio, quando manca un tasso di cambio compare il pulsantino «Aggiungi coppia». Oggi ti porta alla pagina dei cambi e perdi l'analisi. Con TC-23 si apre la finestra di aggiunta **già compilata con la coppia giusta** (per esempio EUR/USD), e dopo il salvataggio il pannello si ricarica da solo.
> - **L1b**: l'analisi dei lotti legge i cambi «a gradini» invece che un tasso al giorno: stessi numeri identici, ma più veloce sulle storie lunghe (es. 1 900 giorni). L'utente non vede differenze, solo meno attesa.

**Worktree**: `/home/alfy/Documenti/02_myRepo/LibreFolio_prj/LibreFolio-worktrees/e-alfy-crispy-goggles` · **Branch**: `e-alfy-j-numeri-e-analisi`
**HEAD di partenza (da verificare)**: `2879ae3e4` (fast-forward fatto dal coordinatore; `npm ci` fatto per Linux).
**Corsia**: porta `6190`, cartella dati `/tmp/librefolio-r13-j`.
**Piano**: `LibreFolio_developer_journal/Release_2/Phase_1/05_numbersAnalysis/plan-phase01NumbersAnalysis.prompt.md`: TC-23 (riga ~8094, analisi ~8452-8523, risposte del coordinatore ~8525-8532, ordine ~8905-8922); L1b (~7426 progetto L1a/L1b, ~7517, ~7531, ~7703, memo e decisioni ~9068-9101). Backlog TC-23 ~3148, L1b ~7853.

## Novità che non hai mai ricevuto
**Q-TC23-1 è decisa: opzione (a)** (developer, 20/10 14:32). I pannelli aprono da soli `FxPairAddModal`, vuota se non c'è una coppia; dopo `oncreated`/`onsynced` il pannello si ricarica. Regola unica: `labQualityAction` dà `{kind: 'add_pair', pair}`; le due copie in linea spariscono. Il via a L1b è del 20/10 14:32 («L1b: via adesso»).

## Passo A — TC-23
- Rossi: `syncTargets.test.ts` (`add_fx_pair` con coppia → `add_pair` con coppia; senza → `add_pair` vuoto; `navigate_fx` per coppia invariato) e un test del componente (o un E2E, scegli con `test-author`) che il pulsantino apra la finestra con base e quote.
- File: `frontend/src/lib/features/risk/syncTargets.ts` (~:82), `levels/RiskPanelHeader.svelte` (~:70), `RiskAnalysisPanel.svelte` (~:536), `AssetSetRiskPanel.svelte` (~:635); una frase nella doc del rischio (`docs-writer`).
- Verdi: Vitest toccati, `front check` (in `flock`). Stima 2-3 ore.
- Consegna **CHECKPOINT READY (A)** e FROZEN.

## Passo B — L1b (dopo il via del coordinatore)
I lotti leggono i cambi con la funzione a gradini (P3 di MF e la funzione di X sono in dev) invece di un tasso al giorno. Restano giornalieri per progetto: la conversione del segno, il cambio chiesto giorno per giorno, la scansione. **Uscita identica**: test di parità contro la copia dei vecchi costruttori (come in L1a), prima i rossi.
- File: `backend/app/services/portfolio/lots_analysis_service.py`, `financial_math/lots/change_days.py`, la conversione in `financial_math/fx`, `test_lots_analysis_service.py` (~:73-86), `test_lots_analysis_pure.py`, il test di parità.
- Verdi: la famiglia `services lots-analysis`, `api portfolio`, `api sync` senza diff.
- **Dati reali**: il piano parla di due copie di un DB con libri in valuta estera. Prova prima con i dati di test della tua corsia. Se servono i dati reali del developer, **fermati e chiedi**: la copia la prepara il coordinatore (skill `real-data-copy`), mai sul DB di produzione.
- Dopo L1b c'è la «finestra tranquilla» per CP-8/CP-9 sullo stesso file: non iniziarla.

## Passo C — Q-G29-1 / J-68 (decisione del developer del 21/10: opzione (a), in 1.3, dopo L1b)
> **A cosa serve.** Nel Gantt di un lotto i segni ▲ ▼ + × │ ◆ (acquisto, vendita, trasferimento, chiusura…) oggi non dicono cosa sono. Con questo lotto, passando il mouse (o toccando) su un segno compare cosa è successo, quando, quanto e con quale broker.
- Piano: `05_numbersAnalysis/plan-phase01NumbersAnalysis.prompt.md` (righe ~8379-8400), J-68 nel backlog.
- Decisione: **(a) tooltip su tutti i segni**: titolo, data, quantità (**mascherata in modalità privacy**), broker («From A / To B» per un trasferimento interno); i segni fusi nello stesso punto elencano tutti gli eventi.
- File: `lotGanttChartHelpers.ts`, `LotGanttChart.svelte`, un Vitest; testi nuovi nelle 4 lingue se servono. Prima i rossi. Gate: Vitest toccati, `front check` (in `flock`), ratchet dei colori pulito (nessun colore scritto a mano).
- Consegna **CHECKPOINT READY (C)** e FROZEN.

## Non fare
- Non toccare `lib/features/transactions/**`, `lib/theme/**`, le pagine di Y-40.
- `OtherPeriodEffectsTable` è di Y (lo corregge Y in questa ondata): non toccarlo.

## Fatto quando
A: rossi→verdi, doc, checkpoint. B: parità provata, verdi, `api sync` pulito, piano aggiornato, **CHECKPOINT READY** e **FROZEN**. Righe CHANGELOG proposte (TC-23 sì; L1b solo se si nota, per esempio «Lots analysis is faster on long histories»).
