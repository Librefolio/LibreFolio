# Brief — workstream MF · Matematica finanziaria · revisione di Q-N78-1k (una sola casa) — bozza

> **A cosa serve (per il developer).** Ogni calcolo finanziario ha una sola implementazione, in `backend/app/services/financial_math/`. W sta cambiando come si legge una coppia di rettifiche collegate fra due broker propri (uscita al PMC, totale 0 con entrambi i broker). Tu controlli che la regola stia **in un posto solo** e che Dashboard, lotti, TWRR e yield on cost la leggano da lì, senza una seconda copia. Esempio di cosa cerchi: un `if tx.type == ADJUSTMENT and related_transaction_id` ripetuto in due moduli.

**Worktree**: `/home/alfy/Documenti/02_myRepo/LibreFolio_prj/LibreFolio-worktrees/e-alfy-turbo-waddle` · **Branch**: `e-alfy-mf-matematica-finanziaria`
**HEAD di partenza (da verificare)**: `c1b4ba49c` (merge di `dev_release2` `c042f2481` sul tuo ramo, dopo il commit del piano sporco `40a38289f`) (il coordinatore prima committa il tuo piano rimasto sporco, `11_financialMath/plan-phase01FinancialMath.prompt.md`, poi fa il fast-forward da `d1f75a3df`, 132 commit dietro, e `npm ci` per Linux).
**Corsia**: porta `6193`, cartella dati `/tmp/librefolio-r13-mf` (ti serve solo per rilanciare un'azione dei servizi, se vuoi).
**Piano**: il tuo, `11_financialMath/plan-phase01FinancialMath.prompt.md` (apri una sezione «Revisione N78-1k (ondata 4)»); le regole: `.github/instructions/financial-math.instructions.md` (o dove sta «Financial Math — One Home» in `backend.instructions.md`: verifica).
**Modello**: Opus.

## Cosa fare
1. **Prima**: leggi l'analisi di W quando il coordinatore te la gira (dove mette la regola, chi la legge, l'esempio numerico). Rispondi in mezza giornata: va bene / va spostata in X perché… / manca il lettore Y.
2. **Poi**: quando W consegna il checkpoint, rivedi il diff **in sola lettura** (`git -C <worktree di W> diff`), cercando: una seconda copia della regola; un motore che non la legge (Dashboard `portfolio/daily_state.py`, lotti `lots/`, TWRR `returns.py`, yield on cost `yield_on_cost.py`, bordo dell'ambito `lots/scope_boundary.py`); un caso di test mancante (coppia collegata con un solo broker in ambito; coppia non collegata; coppia promossa a TRANSFER). Manda le osservazioni al coordinatore come lista `file:riga → problema → correzione`. W le applica.
3. **P4/D-P4**: scrivi due righe nel tuo piano che confermano «fuori dalla 1.3» (motore a segmenti, `daily_states` pigri), con il perché, se il developer lo conferma (domanda 12 del piano).

## Non fare
- Non scrivere codice in `financial_math/` mentre W è aperto: una sola persona scrive. Se trovi un difetto fuori dal perimetro di W, è una voce di backlog con il tuo prefisso, non una patch.
- Niente corse pesanti: al massimo un'azione dei servizi sulla tua corsia, con carico sotto 8.

## Fatto quando
Il parere sull'analisi e la revisione del diff consegnati; W ha applicato le correzioni e tu confermi; piano aggiornato; **CHECKPOINT READY** (nessun file di prodotto tuo, solo il piano) e **FROZEN**.
