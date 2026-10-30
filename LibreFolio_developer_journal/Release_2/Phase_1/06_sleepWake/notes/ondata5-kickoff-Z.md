# Kickoff Z · Sospensione e risveglio — ondata 5 — bozza

Regole comuni: `kickoff-common.md` (leggilo per primo).

> **A cosa serve (per il developer).** (1) **Le «formule veloci» dei prezzi (X-Q1…Q3 e S1)**: oggi i prezzi di un asset si generano **un punto per ogni giorno di calendario** dal primo prezzo e il cambio si converte una volta al giorno. Esempio: un ETF con 10 anni di storia e 2 500 quotazioni produce 3 650 punti e 3 650 conversioni; domani 2 500 punti più i giorni in cui cambia il tasso (P3 di MF, `unit_rate_steps`, è già in dev). **L'API pubblica resta «un punto al giorno»**, ma solo nella finestra visibile; i segnali tecnici si allargano solo sulla finestra più il riscaldamento (S1). È prerequisito del rischio sulle quotazioni vere (R1, di J) e dei «pavimenti» (limiti di data) che MF toglie. **Il developer ha deciso: nella 1.3.** (2) **Z5-F1**: l'avviso `UNDEFINED_METRIC_WINDOW` del calendar rolling return arriva **tradotto** nel frontend, con le date mancanti e il periodo da risincronizzare.

**Perché Z.** Q1 e Q2 riscrivono proprio i blocchi di `get_prices_bulk` che Z ha cambiato con Z-29a (`_fill_point`, `_sample_series`; piano 03 ~8219-8222), e X ha già 6-8 giorni. **X rivede** il tuo lavoro.

**Modello**: Sonnet. **Giorni**: 3,5-4,5 (Q1…Q3 + S1 3-4; Z5-F1 0,5).
**Worktree**: `/home/alfy/Documenti/02_myRepo/LibreFolio_prj/LibreFolio-worktrees/e-alfy-potential-sniffle` · **Branch**: `e-alfy-z-sospensione-e-risveglio`
**HEAD di partenza (da verificare)**: `1fd80c481` (= `dev_release2`, treni 9 e 10 dentro; il tuo ramo aveva 0 commit avanti: fast-forward).
**Corsia**: porta `6186`, cartella dati `/tmp/librefolio-r13-z`.
**Piano**: il tuo `LibreFolio_developer_journal/Release_2/Phase_1/06_sleepWake/plan-phase01SleepWake.prompt.md` (sezione nuova «Ondata 5»); il piano di MF (`11_financialMath/plan-phase01FinancialMath.prompt.md` ~3703-3737 per Q1…Q3/S1; ~3681-3689 per i pavimenti, che **non** sono tuoi) e `03_pluginsAssets/` (Q1…Q3 lato X). Backlog: grep «X-Q1», «X-Q2», «X-S1», «Z-29a». Z5-F1: `UNDEFINED_METRIC_WINDOW` (grep). Skill utili: `signal-plugin`, `testing-backend`.

## Cosa fare
1. **Analisi (mezza giornata, PARTI SUBITO)**: leggi `assets/price_query.py:189-211` (`_build_backward_filled_series`, un punto per giorno di calendario), `:780-797` (`convert_bulk` una volta al giorno), `api/v1/fx/currencies.py:540-558` (due volte), `signals/planning.py:68-82`, `utils/date_range_limits.py` (**solo lettura**: i pavimenti li toglie MF dopo), e come `_fill_point`/`_sample_series` (Z-29a) si incastrano. **Il flag `observed_only` esistente è un'altra cosa** (filtro delle annotazioni, `schemas/signals.py:326`): non riusare il nome. Scrivi: il modello nuovo («per osservazione» + i giorni in cui il tasso cambia), cosa resta identico per l'utente, e i **7 scenari di parità** che servono (data uguale per ogni punto a parità di finestra; weekend/festivi; cambio che cambia a metà; asset in valuta diversa dalla base; finestra più corta della storia; riempimenti; segnali con riscaldamento). **Il punto delicato per J (R1)**: nelle date comuni serve «ultimo prezzo ≤ d **al tasso di d**»: concordalo per iscritto con **J** (tramite il coordinatore) *prima* di scrivere Q1.
2. **Q1…Q3 + S1** (**11b**, **blocca il tag**; ~3-4 giorni). **Prima i rossi** (con `test-author`): test di **parità** (le serie pubbliche identiche a oggi, punto per punto, sui corpora di test e su più finestre) e un test che conta le conversioni (3 650 punti → ~2 500 osservazioni + i cambi di tasso). Poi: Q1 `price_query` per osservazione, un punto al giorno solo nella finestra visibile; Q2 le conversioni (`convert_bulk` per osservazioni e giorni di cambio di tasso); Q3 `currencies.py`; S1 `signals/planning.py` (finestra + warm-up). `api sync` se cambia lo schema (non deve cambiare l'API pubblica). Test dalla corsia: `services price-query`, `api prices`, `api fx`, `services signals`, parità delle serie (~15 min, nello slot).
3. **Dopo il checkpoint**: **J** parte con R1 (legge `price_query`) e **MF** toglie i pavimenti N75/X-R55, Z-30 e AI Export; non toccare le righe dei limiti. **X rivede** il tuo diff prima del commit: rispondi alle sue osservazioni nello stesso worktree.
4. **Z5-F1** (**11a**, mezza giornata, indipendente da 2): oggi il frontend non traduce l'avviso `UNDEFINED_METRIC_WINDOW` del calendar rolling return; il **backend aggiunge l'intervallo nei `details`** (date mancanti, periodo da risincronizzare) e il frontend lo rende dal codice nella lingua dell'app. Rossi: test backend (i `details` ci sono) e Vitest del rendering (4 lingue, via cataloghi); nessun testo inglese hard-coded. Fai questo mentre aspetti la risposta di J sul punto delicato o la revisione di X.

## Dipendenze da altre sessioni
- **Tu → J** (R1 dopo Q1), **tu → MF** (pavimenti dopo Q1…S1): il tuo checkpoint di Q1…S1 è sul percorso critico di tre sessioni: consegna **appena è verde**.
- **X** rivede. **J** concorda con te «ultimo prezzo ≤ d al tasso di d» prima di Q1.

## File condivisi
- **Tuoi in questa ondata**: `backend/app/services/assets/price_query.py`, `api/v1/fx/currencies.py`, `services/signals/planning.py`, `market_series.py`; per Z5-F1 il file backend dove nasce `UNDEFINED_METRIC_WINDOW` e il punto del frontend che lo mostra (verifica con grep: se è di un altro, chiedi).
- **Di altri**: `utils/date_range_limits.py`, `assets/refresh.py:287`, `ai_export/runtime_service.py:104`, `schemas/common.py:746-752` (**MF**, solo limiti); `risk/{scope,replay}.py` (**J**); liste e dettagli dei prezzi (**Y** / **X**).

## Non fare
- Non togliere nessun pavimento (1900, 100 anni, ecc.): è di MF e viene dopo. Non cambiare l'API pubblica (un punto al giorno nella finestra visibile). Nessuna bonifica di serie salvate.

## Domande
Nessuna aperta.

## Fatto quando
Q1…S1: analisi consegnata (con i 7 scenari e l'accordo con J), rossi→verdi con i comandi e i conteggi esatti, parità dimostrata (0 differenze sui corpora), X d'accordo, doc per sviluppatori se cambia il modello (docs-writer, inglese), piano aggiornato. Z5-F1: rossi→verdi, `i18n check`, `front check` 0/0. Righe CHANGELOG proposte: 🔄 «i grafici dei prezzi caricano più in fretta: si leggono solo le quotazioni e i giorni in cui cambia il tasso» (Q1…S1; «nessuna» se non c'è un effetto visibile misurabile: dillo con i numeri); 🐛 «l'avviso del rolling return con dati mancanti dice quali date mancano e cosa risincronizzare» (Z5-F1). Checkpoint: **Z5-F1** · **Q1…S1** (ciascuno **CHECKPOINT READY** + **FROZEN**).
