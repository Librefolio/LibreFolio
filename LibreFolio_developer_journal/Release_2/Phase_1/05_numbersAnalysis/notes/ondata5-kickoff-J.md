# Kickoff J · Numeri e analisi — ondata 5 — bozza

Regole comuni: `kickoff-common.md` (leggilo per primo).

> **A cosa serve (per il developer).** (1) **#48, il backend**: il grafico delle posizioni sovrapposte e la torta per asset hanno bisogno di una **serie per (broker, asset, giorno)** con valore di mercato, costo e flussi, esposta **solo per le posizioni scelte**. Oggi il motore ha `DailyPositionState` (`financial_math/portfolio/models.py:141-170`) ma nessun endpoint lo espone; l'unica storia «per posizione» è per **lotto** e per un solo asset (`financial_math/lots/histories.py:499`). (2) **R1**: il rischio legge **solo le quotazioni vere**: lo strato del rischio scarta già i punti riempiti (`market_series.py:205`); la camminata sta nel prezzo (Q1 di Z). R1 passa `prepare_asset_series` (`risk/scope.py:338`, `:358`) e il replay (`risk/replay.py`) alla lettura nuova.

**Modello**: Sonnet (**MF rivede** J5-1). **Giorni**: 2-3 (J5-1 1,5-2; J5-2 0,5-1).
**Worktree**: `/home/alfy/Documenti/02_myRepo/LibreFolio_prj/LibreFolio-worktrees/e-alfy-crispy-goggles` · **Branch**: `e-alfy-j-numeri-e-analisi`
**HEAD di partenza (da verificare)**: `1fd80c481` (= `dev_release2`, treni 9 e 10 dentro; già fast-forward).
**Corsia**: porta `6190`, cartella dati `/tmp/librefolio-r13-j`.
**Piano**: `LibreFolio_developer_journal/Release_2/Phase_1/05_numbersAnalysis/plan-phase01NumbersAnalysis.prompt.md` (sezione nuova «Ondata 5»); #48: `PROSSIMI_LAVORI.md:390-444`; R1: piano 05 ~7444-7470 e ~9323-9335, backlog ~8487-8491.

## Cosa fare
Entrambi i lotti **aspettano il commit di un'altra sessione per il codice** (J5-1 dopo P4 di MF; J5-2 dopo Q1 di Z): il tuo primo turno è **solo analisi e contratto**, poi attendi.
1. **Analisi e contratto (11b, PARTI SUBITO)**:
   - **#48**: come la serie per posizione leggerà i **segmenti di P4** (non `daily_states` pieno). MF ti manda la forma dei segmenti (`models.py`) in un primo checkpoint piccolo di P4: aspetta quel messaggio per fissare i dettagli. Intanto scrivi il **contratto della serie** (schema: per (broker, asset, giorno): valore di mercato, costo, flussi; **solo per le posizioni scelte**; valori e valuta; come si dichiarano le chiuse) come proposta in `schemas/portfolio.py`-in-bozza **nel tuo piano**, non nel file (che è di MF per B5, in fila). Serve **presto a Y**, che disegna il componente su dati finti contro questo schema: appena stabile, mandalo al coordinatore come messaggio (non aspettare la fine del codice).
   - **R1**: il punto delicato è «**ultimo prezzo ≤ d al tasso di d**» nelle date comuni. È da concordare con **Z** (chi fa Q1/Q2): scrivi la tua versione e mandala al coordinatore perché la giri a Z **prima** che Z scriva Q1. Elenca i **7 scenari di parità** descritti nel piano 05 (0 scritti) e scrivi i test rossi **senza lanciarli finché Q1 non c'è** (puoi lanciare solo i puri).
2. **J5-1 · #48 backend** (**11b**, dopo il commit di P4). La matematica va in `financial_math/portfolio/` in **un modulo nuovo** (casa unica); il lettore in `portfolio_service.py` si **concorda con MF** (checkpoint separato, file di MF); l'endpoint in `api/v1/portfolio_api.py` e lo schema in `schemas/portfolio.py` (sezioni tue; **dopo B5 di MF**, che è piccolo e passa per primo). **Prima i rossi** (con `test-author`): serie di una posizione con acquisto, vendita parziale, trasferimento e split; solo le posizioni richieste; parità con `get_report` sui totali (somma delle posizioni = portafoglio); memoria bassa (non costruisce `daily_states` pieno). `services portfolio-*` sulla corsia, `api sync` (rigenera il client: Y ne ha bisogno). **MF rivede.**
3. **J5-2 · R1** (**11b**, **blocca il tag**, dopo il commit di Q1…S1 di Z). `prepare_asset_series` e il replay passano alla lettura per osservazioni; 7 scenari di parità (scritti con `test-author`, prima in rosso); `risk/scope.py`, `risk/replay.py`, `market_series.py`, `test_risk_*`. `services risk-*` + parità (~10 min, nello slot). **Dopo di te**, MF toglie il pavimento SEC8-1b (`risk/scope.py:71-85`): non toccare quelle righe nel tuo diff (lascia il commento «SEC8-1b dopo R1»).

## Dipendenze da altre sessioni
- **MF → te** (P4: segmenti), **Z → te** (Q1), **te → Y** (contratto e poi endpoint di #48), **te → MF** (SEC8-1b dopo R1).
- **B5 di MF prima di te** nei due file `portfolio_api.py`/`schemas/portfolio.py`.

## File condivisi
- **Tuoi**: `financial_math/portfolio/<modulo nuovo>.py` (file nuovo, dopo P4); `backend/app/api/v1/portfolio_api.py` e `schemas/portfolio.py` (sezione #48, **dopo B5**); `services/risk/{scope,replay,service}.py`, `market_series.py`; `test_risk_*`; il lettore in `portfolio_service.py` solo **con l'accordo di MF** (checkpoint separato).
- **Di altri**: `financial_math/portfolio/**` esistente, `returns.py`, `portfolio_service.py` (**MF**); `price_query.py` (**Z**: leggi); `features/dashboard/**` (**Y**); `features/risk/**` frontend e `riskPanelController.svelte.ts` (**Y**, per Z-14b).

## Non fare
- Non scrivere nel motore esistente (`daily_state.py`, `engine.py`…): è di MF. Nessun calcolo fuori da `financial_math/`. Non iniziare R1 senza Q1. Non togliere il pavimento SEC8-1b.
- Nessuna bonifica di dati.

## Domande
Nessuna aperta.

## Fatto quando
J5-1: rossi→verdi, somma delle posizioni = portafoglio (numero di casi), MF d'accordo, `api sync` senza differenze non spiegate, piano e doc per sviluppatori (docs-writer, inglese) aggiornati. J5-2: 7 scenari di parità verdi, `services risk-*` verde, nessuna riga dei limiti toccata. Righe CHANGELOG proposte: ✨ «serie giornaliera per posizione (base del grafico delle posizioni e della torta per asset)» — **o «nessuna»** finché Y non consegna il frontend (dillo); 🐛/🔄 «il rischio usa solo le quotazioni vere» (R1). Checkpoint: contratto (messaggio) · J5-1 · J5-2, con **CHECKPOINT READY** e **FROZEN**.
