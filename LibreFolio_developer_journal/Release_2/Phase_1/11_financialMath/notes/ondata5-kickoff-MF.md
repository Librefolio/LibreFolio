# Kickoff MF · Matematica finanziaria — ondata 5 — bozza

Regole comuni: `kickoff-common.md` (leggilo per primo).

> **A cosa serve (per il developer).** (1) **MF-FV P4**: il motore dei numeri tiene in memoria **solo i giorni in cui cambia qualcosa** («segmenti validi fino al prossimo») e `daily_states` diventa una sequenza pigra che costruisce il giorno tranquillo solo se qualcuno lo legge. Esempio misurato: una data sbagliata al 1500 oggi costa 720 MB di stati (analisi MF `:4566`); al 1900, 176 MB; con P4 pochi MB. **Parità al bit** su `get_report` (come P3: 330 report, 0 differenze). (2) **Cadono i «pavimenti»** del 1900 e dei 100 anni (restano «non dopo domani», `MAX_BULK_ITEMS`, `MAX_BULK_ITEM_DAYS`): un BTP comprato dal nonno nel 1898 oggi è rifiutato. (3) **B5**: nel waterfall per broker il guadagno maturato di un titolo che entra o esce dalla selezione ha una riga sua («Trasferimenti al valore di mercato») invece di finire in «Other». (4) **MF-P1c**: su periodi che aprono a zero e durano più di ~77 anni la Dashboard mostra un **MWRR falso** (12,80) dove deve mostrare «—». (5) Rivedi i lavori di altri che toccano i numeri.

**Modello**: **Opus** (tutta la sessione). **Giorni**: 4,5-6,5 (P4 2-3; pavimenti 1,5-2; B5 0,5; P1c 0,5-1) + revisioni.
**Worktree**: `/home/alfy/Documenti/02_myRepo/LibreFolio_prj/LibreFolio-worktrees/e-alfy-turbo-waddle` · **Branch**: `e-alfy-mf-matematica-finanziaria`
**HEAD di partenza (da verificare)**: `1fd80c481` (= `dev_release2`, treni 9 e 10 dentro; già fast-forward).
**Corsia**: porta `6193`, cartella dati `/tmp/librefolio-r13-mf`.
**Piano**: `LibreFolio_developer_journal/Release_2/Phase_1/11_financialMath/plan-phase01FinancialMath.prompt.md` (sezione nuova «Ondata 5»): P4 ~3702-3737, analisi ~4502-4549, test-author `p4-tests` «in corso» ~4568; pavimenti ~3681-3689 (D2: uno per lotto, alla fine) e test dei pavimenti ~3738; P1c ~4074-4085 e `PROSSIMI_LAVORI.md:310-323`; B5 backlog ~680. Regole: «Financial Math — One Home» in `backend.instructions.md`.

## Decisioni del developer che ti riguardano
- **Le tre cose restano sempre**: «non dopo domani», `MAX_BULK_ITEMS`, `MAX_BULK_ITEM_DAYS`; tutti gli altri pavimenti cadono, **uno per lotto**, **dopo** chi cura la camminata.
- **P4b (Newton a mano) e D-P4 (storia campionata)**: fuori da questa ondata; da decidere dopo P4.
- **Z-35** (chiusure Yahoo non rettificate; nessuna bonifica): tu **rivedi** il lavoro di X su rendimenti ed eventi.
- **W-B87**: gli split moltiplicativi di Revolut e Trading 212 entrano come rettifica in entrata senza costo: tu fai una **revisione veloce** del checkpoint di W.

## Cosa fare (nell'ordine; treno 11b, salvo diverso avviso)
1. **MF5-1 · P4** (**11b**, **blocca il tag**, PARTI SUBITO; 2-3 giorni; **sul percorso critico**: J5-1, MF5-2 N74/SEC8, B5 e P1c ne dipendono). P1, P2, P3 sono in dev (`returns.py:826-856`, `derived_views.py:78`, merge `015094472`); P4 non ha codice (`portfolio/models.py:413` è ancora `list[DailyPortfolioState]`; `daily_state.py:310-339` copia ogni giorno). Sette moduli (`financial_math/portfolio/{daily_state,engine,models,derived_views,data_quality,period}.py`, `portfolio_service.py` ~:347 e il P&L per broker). **Prima i rossi** (con `test-author`: i `p4-tests` in corso): parità al bit di `get_report` sui 330 corpora, memoria (la copia del DB con la data al 1500: **durante la misura nessun altro slot pesante**; chiedi lo slot al coordinatore), e il comportamento pigro di `daily_states`. **Primo checkpoint piccolo, appena stabile**: la **forma dei segmenti** (`models.py`: come si leggono) in un messaggio al coordinatore, perché **J** progetta il contratto della serie per posizione su quella forma (J e Y non aspettano la fine di P4 per il contratto). Poi la cura completa, `services financial-math`, `portfolio-engine`, parità `get_report` (~20 min a checkpoint, **mai insieme a un `all-frontend`**).
2. **MF5-2 · i pavimenti**, un lotto per volta, nell'ordine in cui lo sblocca chi cura la camminata (**11b**, **blocca il tag**; 1,5-2 giorni in tutto):
   - **dopo P4** (tuo): **N74** e **R13-SEC8** (`engine.py:303`, `:562`, `:664`; `daily_state.py:899-901`; `native_cash.py:508-513`; `lots_analysis_service.py:148`, `:259`; `transaction_batch_stages.py:202-207`);
   - **dopo il commit di Q1…S1 di Z**: **N75/X-R55**, **Z-30**, il tetto dell'AI Export, e il 1900 su `POST /prices/current range_start` (`api/v1/assets/prices.py:48-51`; N83 è già tolto altrove) (`date_range_limits.py:21`, `currencies.py:494-525`, `assets/refresh.py:287`, `price_query.py:549-555`, `ai_export/runtime_service.py:104`, `schemas/common.py:746-752`): **solo le righe dei limiti**, non la logica di Z;
   - **dopo R1 di J**: **SEC8-1b** (`risk/scope.py:71-85`).
   I test che fissano i pavimenti (piano :3738) si riscrivono **prima** (rossi). Un checkpoint per ogni gruppo.
3. **MF5-3 · B5** (**11b**, 0,5 giorni, «rosso prima»; dopo P4; **prima** di J nel file `portfolio_api.py`/`schemas/portfolio.py`: B5 è piccolo e passa per primo). Il guadagno maturato che entra o esce dalla selezione ha una riga («Trasferimenti al valore di mercato»); `portfolio_service.py:1879-1922` (le righe «FX on cash» sono il precedente), formula `period.py:140-145`; B8 è chiusa ma il suo taglio copre solo le coppie con entrambi i broker in vista (`contributions.py:24-46`). Schema (`schemas/portfolio.py`) + la riga nel frontend: **la scrive Y** (`PerformanceChart.svelte`, `OtherPeriodEffectsTable.svelte`, i18n `dashboard`) su tua richiesta: mandala al coordinatore come `file:riga → cosa → testo i18n`.
4. **MF5-4 · MF-P1c** (**11b**, 0,5-1 giorno, dopo P4). **Prima conta i casi** (lo ha chiesto il developer): sui corpora di test e sui **dati reali** (con la skill `real-data-copy`, mai `backend/data/prod/`, copia di lavoro in `/tmp`, da cancellare dopo). Il senso, attenzione: su periodi che aprono a zero e durano più di ~77 anni ogni termine del NPV va a 0.0 e la griglia prende quel punto come «radice esatta» (`returns.py:755-756`, `:786-789`): la Dashboard mostra un **MWRR falso** e deve mostrare «—». La cura accetta uno zero esatto solo se il NPV cambia davvero segno attorno, sopra il rumore di P1b. Test con un caso lungo. Se i conteggi dicono che non capita mai nei dati reali, scrivilo e proponi comunque la cura (è piccola).
5. **Revisioni** (sola lettura, lista `file:riga → problema → correzione` al coordinatore, mezza giornata ciascuna): **(a) W-B87** (rettifica in entrata senza costo per lo split, effetto su costo medio e lotti: veloce); **(b) X5-2** (Z-35: rendimenti ed eventi con prezzi non rettificati; gli split coperti dagli eventi); **(c) J5-1** (#48, serie per posizione: la matematica va in `financial_math/`, legge i segmenti di P4, nessuna copia); **(d) prima del gate del treno 11b**: la **revisione dei numeri** (parità, pavimenti, B5, P1c) con una tua nota firmata. Rispondi anche a J sul contratto della serie.

## Dipendenze da altre sessioni
- **Tu → J → Y** (#48): la forma dei segmenti dopo P4; J scrive il modulo nuovo; Y il frontend.
- **Z → tu** (pavimenti N75/Z-30/AI Export), **J → tu** (SEC8-1b).
- **Tu → Y** (B5): una riga nel waterfall.
- Revisioni: W, X, J.

## File condivisi
- **Tuoi**: `backend/app/services/financial_math/portfolio/**`, `financial_math/returns.py`, `financial_math/portfolio/period.py`, `backend/app/services/portfolio_service.py`; `utils/date_range_limits.py`, `assets/refresh.py:287`, `ai_export/runtime_service.py:104`, `transactions/transaction_batch_stages.py:202-207`, `schemas/common.py:746-752` (solo i limiti); `api/v1/portfolio_api.py` e `schemas/portfolio.py` (B5, **prima** di J).
- **Di altri**: `price_query.py`, `currencies.py`, `signals/planning.py` (**Z**: tu togli solo le righe dei limiti **dopo** il suo commit); `risk/{scope,replay}.py` (**J**: SEC8-1b dopo R1); il modulo nuovo della serie per posizione (**J**, dopo P4); dashboard (**Y**).

## Non fare
- Nessun calcolo finanziario fuori da `financial_math/`; nessuna copia. Nessuna bonifica di dati. Non togliere un pavimento prima del suo prerequisito (e mai i tre che restano). Niente `all-frontend` insieme alle tue misure di memoria.
- P4b e D-P4: non iniziarli.

## Domande
Nessuna aperta.

## Fatto quando
P4: rossi→verdi, **0 differenze di parità** (numero dei report confrontati), memoria misurata prima/dopo (numeri), `services financial-math` + `portfolio-engine` verdi; poi i lotti uno per uno con il loro checkpoint. Righe CHANGELOG proposte: 🔄 «il motore dei numeri usa molta meno memoria sulle storie lunghe e sulle date vecchie» (P4); ✨ «puoi registrare operazioni più vecchie del 1900 e oltre i 100 anni» (pavimenti, **quando cade l'ultimo**); ✨ «il waterfall per broker mostra i trasferimenti al valore di mercato» (B5); 🐛 «su periodi molto lunghi il rendimento in denaro (MWRR) mostra «—» invece di un valore falso» (P1c, **se i conteggi lo giustificano**). Checkpoint: P4 (forma dei segmenti) · P4 · pavimenti (un messaggio per gruppo) · B5 · P1c; ognuno con **CHECKPOINT READY** e **FROZEN**.
