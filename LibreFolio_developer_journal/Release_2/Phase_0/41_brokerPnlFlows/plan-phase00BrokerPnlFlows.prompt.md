# Piano — fase 00, 41: il P&L per broker senza salti ai trasferimenti

> **Stato**: ✅ consegnato il 2026-10-12, in esecuzione dal 2026-10-10. Avanzamento in §15.
>
> - **Dal 2026-10-11 il lotto ha avuto tre consegne** (§0):
>   1. il checkpoint 1, col solo engine (T5a, treno 32);
>   2. poi H, cioè la card dal motore (T2f e T5b);
>   3. poi l'analisi di F (T7), e F stessa dopo la decisione del developer.
> - **Nel target**:
>   - checkpoint 1: `883681766`, `3801cf93e`, `5c4c2c0e8`, fusi come `46272c3f0` (treno 32, `dev_release2` = `b20eac991`);
>   - H: `801b4a168`, `144c9db27`, `fb954577f`, fusi come `8a546c046` (treno 35);
>   - F, checkpoint F-C1: `36b181836`, `aa6b6077a`, `384253663`, poi il merge `daee275fe` del treno 41 nel ramo;
>   - F, checkpoint F-C2: `a5f41f60c`, `c04e44ff5`, `9a0d9280c`, `a4332b25b`, `56fcf0aac`, fusi come `15cbff6fb` (treno 42), poi il CHANGELOG `5d62658bb`;
>   - F-C3: `f10fcd04a` (C9), poi J1 `deec22bf8` e il merge `d27a2f729` (treno 43).
> - **Chiuso**: F, approvato dal developer il 2026-10-11 (§0, esito in §17.11). F-0…F-5, F-W e i checkpoint F-C1 e F-C2 ✅ (§9, §15). T8 ✅ (2026-10-12): la sezione I di `BACKLOG_POST_1.2.md`, consegnata col checkpoint F-C3 insieme a questa nota. La seconda descrizione del runner (`:1070`) è passata a T, con T-1 (§15, «T8 / F-C3»).
> - **F-AI deciso dal developer** (2026-10-12): la (a) nella 1.2, cioè niente; la (b) dopo la 1.2, «con un codice tipizzato». La voce è nella sezione I del backlog, consegnata col checkpoint di M-16 (§15, «Treno 43 e F-AI»). Nel lotto non resta niente di aperto.
>
> - **Mandato**: coordinatore di Release 2 (`c8328a01-…`), con le decisioni del developer (§1) e l'autorizzazione testuale (§0).
> - **Workstream I**. Ramo `e-alfy-performance-charts-plan`. Dopo il treno 43 il ramo è avanzato in fast-forward a `d27a2f729`; l'ultima nota (§15, «Treno 43 e F-AI») è scritta su `378338fed`, la base di M-16 ([piano 44](../44_importWizardBrokerGate/plan-phase00ImportWizardBrokerGate.prompt.md)). F-C3 è partito da `5d62658bb` (treno 42, il CHANGELOG di I). F è partito da `251067435` (treno 36: solo journal e `.github`, codice identico a `43d92ed23`, verificata il 2026-10-11). Il lotto è partito da `d59762e0a` (treno 30); l'analisi era stata fatta su `fbb57eb41` (treno 28) e riverificata su `e32f47133` (treno 29). I treni 29 e 30 non toccano le superfici del lotto (§8).
> - **Corsia**: `--test-port 6157 --data-dir /tmp/librefolio-r2-i-charts`, con `PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py test …`; un comando alla volta. Mai le porte 6040 e 6041.
> - **Origine**: G1a, le linee additive del P&L per broker, nel piano archiviato [`plan-phase00PerformanceCharts.prompt.md`](../../phases/20_performanceCharts/plan-phase00PerformanceCharts.prompt.md) (§3.2).

## 0. Autorizzazione (2026-10-10)

- **Developer**, testuale, la segnalazione: «non mi torna che il tratteggiato mostri quelle cifre, dovrebbe mostrare i p&l di quei broker, e quelle cifre sono liquidità pura».
- **Developer**, testuale, dopo la trattazione del coordinatore: «che dire, mi hai convinto con riserva, implementiamolo e facciamo per bene tutti i casi normali e limite e vediamo cosa ne esce».
- **Developer**, testuale, sull'analisi di I (domanda del coordinatore con D1–D6 elencate una per una): «Via, con tutte le raccomandazioni (Consigliato)».
- **Coordinatore** (10:03): l'approvazione è valida. **D5 è nel lotto**: la cassa orfana va in ECF, il TRANSFER orfano segue la regola di D2. Per ultimo e isolato.
- **Coordinatore**, dal kickoff:
  - le pagine EN che cambio entrano nel secondo giro di traduzioni di M;
  - il CHANGELOG è suo: le righe proposte sono in §12;
  - un file del runner va annunciato prima di toccarlo: qui non serve (§6).
- **Developer**, testuale, sull'inventario di §16 e sulle opzioni H e F (2026-10-11, via il coordinatore): «voglio fare entrambi entro la 1.2 ma non capisco perchè dici che una ha rischio basso e una rischio altro. in oltre il fatto che ne ha trovate 11 di funzioni di calcolo mi fa molto strano, sicuro che non possiamo comunque fare un unica maxy funzione e tramite i parametri giusti ottenere quello che serve? quali sono questi altri 9 calcoli diversi?»
- **Coordinatore** (2026-10-11): H e F entrano entrambe nella 1.2. Le domande del developer le spiega lui, partendo da §16. L'ordine:
  1. **subito il checkpoint del solo engine** (T5a): T2a–T2e, i test dell'engine, la doc di T3 e questo piano, senza `test_portfolio_service.py`. Entra nel treno 32, e la riga del CHANGELOG per ora non nomina le card;
  2. **poi H**: il test della card col cambio via `test-author`, T2f, T3b e il resto di T4, in un secondo checkpoint (T5b). È la rete di sicurezza: se F slitta, le card restano giuste, a parte il cambio;
  3. **poi l'analisi di F, prima del codice** (T7). L'engine diventa l'unica funzione, con i parametri giusti, e una sola ricostruzione produce quello che oggi rifanno altri giri sulle transazioni:
     - il registro della cassa nativa per broker e valuta, rivalutato ogni giorno (B4), che assorbe i punti 3 e 4 di §16.1;
     - i flussi del periodo per tipo e l'«Other» (punti 5, 6 e 7);
     - da valutare se il punto 8 (B8), il 9 e B9 stanno dentro F o dopo.

     Per ogni punto: cosa misura e chi lo legge, dentro o fuori dalla 1.2, la stima e il rischio concreto (quali valori attesi cambiano, quanti test).
     - **Guardia obbligatoria**: per i portafogli con la cassa solo nella valuta base, tutti gli output identici byte per byte prima e dopo.
     - La voce del waterfall tocca schema, frontend e i18n. I cataloghi ora li scrive P, quindi passa dal coordinatore.
- **Coordinatore** (2026-10-11, 12:51): il checkpoint 1 è nel target (treno 32, `b20eac991`, albero `35d2afdc0533`); **via ad H** (T1c, T2f, T3b, T4), corsia 6157.
- **Developer**, testuale, per l'analisi di F: «Riguardo la funzione unica ne sono lieto, se serve un posto dove metterla mettiamola nello stesso modulo dei calcoli matematici, vicino al wac centralizzato.»
  - Il coordinatore: il codice nuovo di F va in `backend/app/services/financial_math/`, accanto a `average_cost.py`. L'analisi (T7) dice cosa ci va e come lo chiama l'engine.
  - I file esistenti non si spostano: ne parla il coordinatore col developer, dopo il lotto.
- **Coordinatore** (2026-10-11, checkpoint 2 verificato; H entra nel treno 35): **via a T7**. Il contratto per F, da T (analisi approvata dal developer):
  1. il codice nuovo va **piatto** in `financial_math/` (proposta: `native_cash.py`), accanto a `average_cost.py`; T-1 non lo sposta;
  2. nessun import di servizi d'orchestrazione: si importa dal modulo che definisce (regola del layer emendata, D-4);
  3. una riga per il modulo nella docstring di `financial_math/__init__.py`.

  Per i reperti di T fuori da §16 (P1, R1/R2, R3/R4, X5, O2, W1, V2/P2, C1): dentro F (stesso passaggio sulle transazioni) o in un lotto U dopo la 1.2, con una stima. Il mini-FIFO (L1/L2) resta a T (B4/U6). Da correggere il punto 11 di §16: KpiSection calcola (T, §1.4). La portata finale di F la porta il coordinatore al developer.
- **Coordinatore** (2026-10-11, treno 36): worktree a `251067435`, solo journal e `.github`. Regola nuova «Post-release backlog index» (`coordinated-workstream.agent.md:164-172`): ciò che un checkpoint lascia dopo la 1.2 diventa una riga della mia sezione I di `Phase_0/BACKLOG_POST_1.2.md`, nello stesso checkpoint. La sezione I la completo a fine lotto, con le voci di F rimaste dopo la 1.2 (§11).
- **Developer**, testuale, sull'analisi di F (2026-10-11, via il coordinatore): «ottima analisi». Sul waterfall: «dire i nella 1.2 solo, stiamo parlando di una riga nella tabella della pagina delle performance o di alterare le kpi in dashboard?», poi «si procediamo così, se riusciamo anche nell'ai export però, vediamo come si mette».
- **Coordinatore** (2026-10-11, 17:42): **F approvato, via all'implementazione.**
  1. **Portata**: le voci «F» di §17.6, con k2 e la politica (a) sul cambio mancante.
  2. **F-W è la (i) nella forma minima**, ultimo passo di F:
     - in `get_positions_contribution`, una riga di `other_effects` (`OtherPeriodEffect`, categoria `Other`) «FX on cash», una per ogni broker con cassa in valuta; il residuo scende della stessa cifra;
     - il modello accetta già righe generiche (`schemas/portfolio.py:433-440`): niente schema nuovo, niente `api sync`;
     - KpiSection non si tocca: le card KPI restano le 4 righe di oggi;
     - frontend: una riga di mappatura in `OtherPeriodEffectsTable.svelte:73-75` (`translateOr`) e una chiave nei 4 cataloghi, con `dev.py i18n`, solo col via del coordinatore (oggi i cataloghi li ha P);
     - doc EN: la lista «Other Period Effects» di `positions.en.md:87` e la frase di `kpi-cards.en.md:39`.
  3. **Il nome nell'AI Export è facoltativo.** La cifra resta dentro `period_other_result`, quindi la riconciliazione (`broker_financial.py:423-433`, `portfolio_financial.py`) torna anche senza. Solo dopo F-W e solo se c'è margine: prima il costo al coordinatore (contratto, versione, probe, secondo `ai-development.instructions.md` e la skill `ai-export-probe-tuning`); niente codice senza il suo via.
  4. **B9 dopo la 1.2**, con la descrizione corretta (§14): la prende T, in U3.
  5. **La mappa delle U** l'ha riconciliata il coordinatore col piano di T (§17.6).
  6. **Runner**: concesso il ritocco del solo testo descrittivo di `scripts/test_runner/_backend_services.py:571-574`, dentro F.
  - **Come**: base `251067435`; corsia 6157 con `/tmp/librefolio-r2-i-charts`. Il coordinatore ha corretto il suo primo messaggio: `/tmp/librefolio-r2-i` era un errore, quella cartella non si usa. F-0 per primo: i rossi e il golden della guardia, generato prima del codice, via `test-author`. Il piano si aggiorna dopo ogni passo. Checkpoint dopo F-2 (modulo e motore, con la guardia verde) e a fine F. A fine lotto, la sezione I di `BACKLOG_POST_1.2.md`: B9 corretto, le U che restano, il nome nell'AI Export se non entra.
  - **CHANGELOG**: lo propongo io, lo scrive il coordinatore. F-W è un ✨: «The Performance view lists exchange-rate results on cash as their own row».
  - **Data obiettivo del tag**: 22–23/10.
- **Coordinatore** (2026-10-12, F-C2 verificato e nel treno 42): **lotto F-C3** su `5d62658bb`: T8, la sezione I di `BACKLOG_POST_1.2.md` con tutte le voci tranne F-AI (b), che aspetta il developer, e la nota in questo piano; poi checkpoint e FROZEN. Della `/tmp` pulisco solo i miei file.
  - **Correzione successiva**: la riga del runner (`_backend_services.py:1070`) passa a T, perché T-1 riscrive tutta la voce `financial-math` e i file del runner ora sono suoi. F-C3 è quindi T8 più questa nota (§15, «T8 / F-C3»).

## 1. Obiettivo e decisioni del developer

La linea tratteggiata di un broker nel grafico del P&L (G1a) deve mostrare il P&L di quel broker. Oggi, quando denaro o titoli passano fra due broker della selezione, il mittente scende di X e il destinatario sale di X: è capitale che si sposta, non un guadagno. Il totale è già giusto e non deve cambiare.

Decisioni, tutte come consigliato nell'analisi:

| # | Decisione | Conseguenza |
|---|---|---|
| D1 | I titoli valgono il **valore di mercato all'arrivo**, non il costo | Al costo resterebbe un salto pari al guadagno non realizzato |
| D2 | **La stessa regola nella vista di un broker solo**: una metà TRANSFER col partner fuori dal filtro è capitale al valore di mercato della sua data | I titoli ricevuti non sono più un guadagno, quelli inviati non sono più una perdita; cambiano gli aggregati filtrati (§10) |
| D3 | Prezzo mancante all'arrivo: **X = 0**, cioè il valore che entra davvero nel NAV del destinatario | Il valore compare al primo prezzo, sul broker che lo detiene |
| D4 | Coppie ADJUSTMENT **escluse**: restano capitale al costo | Backlog B6 |
| D5 | **Orfani nel lotto**: CASH_TRANSFER e FX_CONVERSION orfani diventano ECF; un TRANSFER orfano segue D2 | Ultimo passo, isolato; cambia l'aggregato di chi ha cancellato un broker |
| D6 | L'avviso sulle quote resta com'è | Backlog B1; il residuo (s_B − s_A)·X va documentato |

## 2. Il difetto alla base (`backend/app/services/portfolio_engine.py` @ `d59762e0a`)

- **G1a** (:1175-1184): `P_b = V_b − C_b`.
  - `V_b` = valore di mercato delle posizioni del broker + cassa + valore in viaggio partito da lui.
  - `C_b = cumulative_ecf_by_broker[b]`, dall'indice ECF (:747-754): depositi e prelievi, metà di coppia col partner fuori dalla selezione, `ADJUSTMENT` in natura al costo.
- **Coppie interne** (`linked_internal`, :323-345): nessun ECF. All'arrivo P_A fa −X e P_B fa +X; il totale è giusto. La doc lo ammette (`mkdocs_src/docs/user/dashboard/charts.en.md:79`).
- **In viaggio** il valore resta al mittente (`_compute_in_transit` :1566-1625, `it_by_broker`), alla quota della partenza (:339).
- **Vista di un broker solo**: una metà TRANSFER `linked_external_*` non ha flusso (nessun importo; `_is_capital_adjustment` :1627 vale solo per ADJUSTMENT). I titoli ricevuti contano come guadagno, quelli inviati come perdita, contro la teoria (`deposited-capital.en.md:19` e la tabella :24-31).
- **Orfani** (`related_transaction_id = None` su un tipo collegato): il ramo unlinked (:296-304) dà ECF solo a DEPOSIT e WITHDRAWAL (:302). Un CASH_TRANSFER o un TRANSFER orfano conta come guadagno o perdita anche nell'aggregato.
- **Chi legge le contribuzioni**: solo `build_broker_pnl_history` (:1820) → `PortfolioService.get_broker_pnl_history` (`portfolio_service.py:1423`) → il grafico. `cumulative_ecf_by_broker` finisce anche in `EngineEndState` (:1313), che oggi nessuno rilegge.

## 3. Fatti verificati che decidono il disegno

1. **Gli orfani sono rari.**
   - Alla creazione TRANSFER, CASH_TRANSFER e FX_CONVERSION chiedono `link_uuid` (`backend/app/schemas/transactions.py:313-316`).
   - DEGIRO e Swissquote collegano le gambe FX; il CSV generico rifiuta FX_CONVERSION.
   - Lo split dell'editor in blocco cambia i tipi (WITHDRAWAL/DEPOSIT o ADJUSTMENT/ADJUSTMENT) prima di staccare i link (`transaction_batch_stages.py:286-299`, `SPLIT_TYPE_MAP` in `transaction_service.py:704-708`).
   - Restano `delete_by_broker` (`transaction_service.py:333`, che azzera il partner) e le modifiche manuali al DB.
   - **La strada vera degli orfani è cancellare un broker** (`broker_service.py:757` → `delete_by_broker`): la metà rimasta nell'altro broker diventa un tipo collegato con `related_transaction_id = None`. Cancellare una sola gamba invece è rifiutato (`apply_deletes`, `transaction_batch_stages.py:203-218`, codice `pairDeleteIncomplete`), quindi un id che punta a una riga assente (FK differita) nasce solo da modifiche manuali al DB.
2. **La valutazione non ha stato.** `AssetPriceSeries.resolve` (`backend/app/services/price_resolver.py:197`, bisezione a :201) non dipende dalle chiamate precedenti: `_market_value_for` si può chiamare fuori ordine, prima del ciclo dei giorni.
3. **Un TRANSFER non crea mai un mark** (`build_asset_price_series`, `price_resolver.py:278-296`); BUY, SELL e ADJUSTMENT con costo sì. Nella vista combinata un titolo entrato con un costo non è mai MISSING all'arrivo: il MISSING implica un ingresso senza prezzo, cioè a capitale 0.
4. **D4 viene da sé.** `_LINKED_TYPES` (:96-100) = TRANSFER, CASH_TRANSFER, FX_CONVERSION, senza ADJUSTMENT. Il classificatore invece collega qualsiasi coppia in scope, anche sullo stesso broker e le coppie ADJUSTMENT.
5. **Un TRANSFER non ha cassa** (`schemas/transactions.py:318-325`), un CASH_TRANSFER non ha quantità (:336-343): il segno di una gamba è la quantità per TRANSFER e l'importo per gli altri due tipi.
6. **Il pre-frame reale non esiste.** In produzione i chiamanti passano `date_from=None`: il pre-frame lo esercitano solo i test (`frame_start`).
7. **TWRR e MWRR** leggono i delta di `cumulative_external_cash_flow` (`build_performance_inputs` :1884-1911). D2 aggiunge capitale lì, come l'ADJUSTMENT in natura: restano coerenti.
8. **Il preload dei cambi** (`_preload_fx_rates` :2629) carica le valute di asset e prezzo solo per i giorni in [date_from, date_to]. Per una gamba TRANSFER prima di date_from il cambio della sua data manca.
9. **L'avviso sulle quote non arriva mai all'utente**: nessun chiamante passa `classifier_warnings` (parametro a :1974), e scatta solo sulle coppie di più giorni (:342-345).
10. **La doc è già fuori dal codice**: `deposited-capital.en.md:19` dice che un TRANSFER con `cost_basis_override` è capitale in natura, ma `_is_capital_adjustment` vale solo per ADJUSTMENT.

## 4. Disegno

### 4.1 Passo 3b — flussi interni a somma zero

- Nuovo metodo `DailyStateBuilder._internal_transfer_flows()` → lista di `(data, mittente, destinatario, X)`.
- **Selezione**: `classification == "linked_internal"`, `paired_tx` presente, `tx.type ∈ _LINKED_TYPES`, broker diversi.
- **Guidato dal destinatario**: per ogni coppia (dedupe su min/max id) il mittente è la gamba con segno < 0, il destinatario quella con segno > 0, quindi un solo flusso per coppia. Coppie degeneri (segni uguali o nulli): nessun flusso, log di debug.
- **Data** = max(date delle gambe) = l'arrivo, il t_arr della doc. **Quota** = quella del mittente `s_A`, come il valore in viaggio (:339).
- **X** (valutato alla data del flusso):
  - cassa e FX: `_convert(|recv.amount|, recv.currency, data) × s_A`, cioè il delta del registro di cassa (:724-733) a quote uguali;
  - titoli: `_market_value_for(asset, |recv.quantity|, data).market_value × s_A`, la stessa valutazione della 4c, con LOCF e staleness, nella forma di `_compute_in_transit` (valore × quota);
  - `None` (MISSING o cambio mancante) → nessun flusso (D3).
- **Applicazione**, subito dopo l'indice ECF (:754): `ecf_by_date_by_broker[(d, A)] −= X` e `ecf_by_date_by_broker[(d, B)] += X`, con lo stesso `Decimal`. **Mai** `ecf_by_date`, `cumulative_ecf` o `ecf_today`.
- **Date**: quelle < `frame_start` entrano in `preframe_tx_dates` (:790), le altre in `dirty_days` (:881). Sono già date di transazione; l'aggiunta esplicita rende il passo indipendente da questo.
- Metodo separato, così il test di regressione lo neutralizza e confronta gli aggregati (§6).

### 4.2 D2 — metà TRANSFER oltre il filtro

- Helper `_transfer_leg_capital(ctxn, tx_qty)` → `Decimal` con segno, oppure `None`.
- **Si applica** a un TRANSFER con asset e quantità ≠ 0, non `linked_internal` e non legato a uno split: `linked_external_inflow`, `linked_external_outflow`, `normal` col partner non trovato e, con D5, `normal` orfano.
- **Valore**: `sign(qty) × _market_value_for(asset, |tx_qty|, tx.date).market_value`, con `tx_qty` già alla quota del broker; MISSING → `None`, nessun capitale.
- **Dove**: in `cumulative_ecf` **e** in `cumulative_ecf_by_broker[bid]`, nel pre-frame (dopo il `continue` degli split, :865-866) e nel frame (dopo :1003-1004), prima dei rami ADJUSTMENT in natura. Non in `ecf_today`, come l'ADJUSTMENT in natura.
- **Proprietà**:
  - B da solo = B nella vista combinata (a quote uguali);
  - A da solo = A combinato − [MV(arrivo) − MV(partenza)]: le oscillazioni durante il viaggio restano ad A solo nella vista combinata. Va documentato (§7).

### 4.3 D5 — orfani

- Ramo unlinked (:302): ECF anche per `_CASH_LINKED_TYPES` (CASH_TRANSFER, FX_CONVERSION) con importo, come già il ramo «partner non trovato» (:309-317).
- TRANSFER orfano → D2: l'helper non guarda `related_transaction_id`.

### 4.4 Preload dei cambi

- In `_preload_fx_rates`: per ogni TRANSFER classificato con asset, quantità ≠ 0 e data < `date_from`, aggiungere (valuta dell'asset, data) e le valute dei suoi prezzi diverse dalla valuta di riferimento, alla data della gamba.
- Mai dagli intervalli; un BUY prima del range non aggiunge niente. Il test delle chiavi esatte (`test_portfolio_engine_vnext.py:788-960`) resta verde: le sue transazioni classificate sono BUY, i TRANSFER stanno solo negli intervalli.

### 4.5 Invarianti

- Σ_b C_b = `cumulative_ecf` e Σ_b P_b = `total_pnl`, ogni giorno.
- Nessun flusso durante il viaggio.
- Vista combinata: ogni campo di `DailyPortfolioState` tranne `broker_contributions` identico byte per byte, con e senza i flussi (NAV, capitale, `total_pnl`, ROI/TWRR/MWRR che ne derivano, candele, cassa, K/R, valori in viaggio, qualità dei dati). Cambia anche `EngineEndState.cumulative_ecf_by_broker`.

## 5. Casi con i numeri attesi

In EUR; broker A = 10, B = 20, C = 30; d0 = 2025-01-01 … d5 = 2025-01-06.

- **Setup T** (titoli): asset in EUR, prezzi 10/11/12/13/14/15 su d0–d5; A deposita 100 e compra 10 pezzi a 10 a d0.
- **Setup C** (cassa): A deposita 5000 a d0.
- **Oggi** = le due linee nel giorno d'arrivo, prima della cura.

| # | Caso | Atteso dopo la cura | Oggi (A/B) |
|---|---|---|---|
| 1 | Cassa in giornata, 1000 da A a B a d1 (C) | P_A = P_B = 0; C_A 4000, C_B 1000 | −1000/+1000 |
| 2 | Golden Scenario B: CASH_TRANSFER 1000 dal 10 (02-01) al 20 (02-05) | P_10 = P_20 = 0 ogni giorno; C_10 5000 → 4000 e C_20 0 → 1000 dal 02-05 | −1000/+1000 |
| 3 | A deposita 1000 USD a d0; cambi .90/.90/.91/.92/.93 su d0–d4; CASH_TRANSFER d1 → d4 | P_A 0, 0, +10, +20, +30 (C_A −30 a d4); P_B 0; aggregato +30 | −900/+930 |
| 4a | Titoli in giornata a d2 (T) | P_A +20; P_B 0 a d2, poi +10/+20/+30 su d3–d5 | −100/+120 |
| 4b | Titoli d1 → d3 (T) | P_A +10, +20, +30 su d1–d3; P_B 0 a d3, +10 a d4, +20 a d5 | −100/+130 |
| 5 | U (id 200) entra in A a d0 con un ADJUSTMENT senza costo; coppia TRANSFER con costo 10 per pezzo, d1 → d3; primo prezzo 15 a d4 | P_A 0, poi +100 su d1–d2 (ripiego al costo, preesistente), 0 da d3; P_B 0, +150 da d4. **Guardia**: uguale prima e dopo | uguale |
| 6 | Parziale, 4 pezzi su 10 a d2 (T) | C_A 52, P_A +20, P_B 0; a d3 +26/+4 | −28/+48 |
| 7 | A ha 1000 USD (cambio .92); FX_CONVERSION −1000 USD (A) → +900 EUR (B) | P_A −20, P_B 0 | −920/+900 |
| 8 | A deposita 2000 e passa 1000 a B a d1; quote .5/.5, .5/1, 1/.5 | 0/0; P_B +500; P_B −500. Aggregati invariati | |
| 9 | Pre-frame: prezzi 10/11/12/13 su d0–d3 e 14 a d10; trasferimento come 4b; `frame_start` d10 | P_A +30, P_B +10, uguali al calcolo completo | |
| 10 | Viaggio a cavallo: partenza d1, arrivo d5, `frame_start` d3 | P_A +30 a d3, +40 a d4, +50 a d5; P_B 0 | −100/+150 |
| 11 | Catena: A → B in giornata a d2, B → C d3 → d4 | a d5: 20/20/10, Σ 50 | |
| 12 | Andata e ritorno: A → B a d2, B → A a d4 | a d5: P_A +30, P_B +20 | |
| 13 | Viste di un broker solo, come 4b | B da solo: C_B 130 a d3, P_B 0/+10/+20 = B combinato. A da solo: C_A −10, P_A +10 costante da d1 | −100 (A) / +130 (B) |
| 14 | Commissioni: FEE −5 a parte in A a d1; oppure coppia −1000/+995 | P_A −5 in entrambi; P_B 0 | |
| 15 | Coppia TRANSFER promossa (lotto 40, costo su entrambe) contro coppia ADJUSTMENT col costo 10, a d2 | TRANSFER +20/0; ADJUSTMENT 0/+20 prima e dopo (**guardia**) | |
| 16 | Orfani (D5): TRANSFER +10 in B a d2; CASH_TRANSFER +1000 in B; e gli speculari in uscita da A | P_B 0 a d2, +10 a d3; P_B 0; TRANSFER −10 da A: P_A +20; CASH_TRANSFER −1000: P_A 0 | +120; +1000; −100; −1000 |
| 17 | Identità | Σ P_b = P ogni giorno, in ogni scenario | |
| 18 | Golden | Scenario A invariato; Scenario B: aggregati invariati, capitale per broker cambiato dal 02-05 | |

## 6. Test (T1, via `test-author`)

Tutti in `backend/test_scripts/test_services/test_financial/test_portfolio_engine/`, raccolti da `services roi-fifo-utils` (`scripts/test_runner/_backend_services.py:581-589`): **nessuna modifica al runner**.

- **Nuovo** `test_broker_internal_flows.py`, al livello di `DailyStateBuilder`, coi helper del golden:
  - i casi 1 e 3–17 di §5, coi numeri attesi;
  - la regressione degli aggregati: gli stessi scenari due volte, una coi flussi neutralizzati (`monkeypatch.setattr(DailyStateBuilder, "_internal_transfer_flows", lambda self: [], raising=False)`), confrontando con `dataclasses.fields` ogni campo di `DailyPortfolioState` tranne `broker_contributions`;
  - il preload dei cambi: una gamba TRANSFER prima di `date_from` aggiunge le valute alla sua data, un BUY no (`convert_bulk` sostituito, come in `test_portfolio_engine_vnext.py:788-960`).
- `test_broker_pnl_contributions.py`: lo Scenario B (:252-338) riceve le asserzioni su capitale e P&L per broker (caso 2); lo Scenario A resta il golden invariato.
- `test_scope_classifier.py`: gli orfani di D5 (CASH_TRANSFER e FX_CONVERSION → ECF; TRANSFER → nessun ECF, è D2 nel builder).
- **Guardie**, verdi prima e dopo: i casi 5 e 15-ADJUSTMENT, lo Scenario A, la regressione degli aggregati. **Rossi attesi** prima della cura: tutti i casi con un flusso.

## 7. Documentazione (T3, via `docs-writer`, solo EN)

- `mkdocs_src/docs/user/dashboard/charts.en.md:79`: le linee non saltano più ai trasferimenti; il valore in viaggio resta al mittente; con quote diverse resta un residuo.
- `mkdocs_src/docs/financial-theory/technical-analysis/performance-metrics/portfolio-engine/deposited-capital.en.md`:
  - :19, il capitale in natura: ADJUSTMENT col costo; le metà TRANSFER oltre il filtro al valore di mercato;
  - la tabella :24-31: TRANSFER col partner fuori dal filtro, metà orfane, coppie interne a somma zero per broker;
  - una sezione nuova sui flussi interni nelle linee dei broker: data e valore di X, viaggio, quote, prezzo mancante, vista di un broker solo contro la vista combinata.
- `portfolio-engine/index.en.md`: da valutare, solo se nomina le linee dei broker.
- Niente `translate-stamp`: è debito vero per il secondo giro di M. `translate-validate` lo misura.

## 8. Superfici

- **Mie**: `backend/app/services/portfolio_engine.py`; i tre file di test di §6; le pagine EN di §7; questo piano.
- **Mie dal 2026-10-10 (opzione A)**: `backend/app/services/portfolio_service.py` (nessun altro lo tocca) e `backend/test_scripts/test_services/test_financial/test_portfolio_service.py` (T1b).
- **Vietate**: frontend, cataloghi i18n (S), traduzioni (M), `transaction_service.py`.
- **Runner** e **API**: nessuna modifica; `api sync` non serve.
- **Treni 29 e 30** (`fbb57eb41..d59762e0a`): non toccano engine, test dell'engine, le due pagine di §7, devWiki, `_backend_services.py`, `portfolio_service.py`.

## 9. Passi

| Passo | Cosa | Stato |
|---|---|---|
| T0 | Piano nel journal | ✅ 2026-10-10 |
| T1 | Rossi via `test-author` (§6), con la prova del rosso sulla 6157 | ✅ 2026-10-10 |
| T1b | Rosso della card via `test-author` in `test_portfolio_service.py` (§16.3) | ✅ 2026-10-10 |
| T2-inv | Inventario classificato dei calcoli fuori dal motore (§16), al coordinatore prima di togliere copie | ✅ 2026-10-10, in verifica |
| T2a | Passo 3b, nel pre-frame e nel frame | ✅ 2026-10-10 |
| T2b | D2, nel pre-frame e nel frame | ✅ 2026-10-10 |
| T2c | Preload dei cambi | ✅ 2026-10-10 |
| T2d | D5 nel classificatore, ultimo e isolato | ✅ 2026-10-10 (stesso passaggio di T2b, separabile: §15) |
| T2e | Lint e format del backend | ✅ 2026-10-10 |
| T1c | Rosso della card col cambio, via `test-author` in `test_portfolio_service.py` (§16.3) | ✅ 2026-10-11 (§15) |
| T2f | La card prende il broker dal motore, lo specchio del capitale sparisce (§16.2); solo dopo la verifica dell'inventario | ✅ 2026-10-11 (§15), opzione H con il disegno rivisto di §16.2 |
| T1d | Rosso dell'orizzonte: righe con data futura in una chiamata diretta di `get_summary` senza `date_to`, sulla card e nel riepilogo, via `test-author` in `test_portfolio_service.py` | ✅ 2026-10-11 (§15) |
| T2g | Il riepilogo legge le transazioni fino a `valuation_date`, l'orizzonte del motore | ✅ 2026-10-11 (§15) |
| T3 | Doc EN via `docs-writer` (§7) | ✅ 2026-10-10, rivista; entra solo insieme all'engine |
| T3b | Una riga sulle card in `user/brokers/index.en.md:9` (guadagno senza salti, valore in viaggio sulla card del mittente), via `docs-writer`; solo se T2f passa | ✅ 2026-10-11 (§15) |
| T4 | Gate (§11) | ✅ 2026-10-11 (§15): backend senza T2f il 2026-10-10, poi tutto con T2f |
| T5a | Checkpoint 1, solo engine: T2a–T2e, i test dell'engine, la doc di T3, questo piano; senza `test_portfolio_service.py` (§0) | ✅ 2026-10-11 (§15), nel treno 32 (`46272c3f0`) |
| T5b | Checkpoint 2, H: T2f, i rossi di T1b, T1c e T1d, T2g, T3b, il resto di T4 | ✅ 2026-10-11 (§15), nel treno 35 (`8a546c046`) |
| T6 | Proposta per la devWiki (§13) | ✅ 2026-10-11, proposta completa in §13, card compresa; la archivia il coordinatore o lo storico |
| T7 | Analisi di F, prima del codice (§0): la cassa nativa rivalutata (B4) e i flussi del periodo nel motore, con la guardia sui portafogli con la sola valuta base | ✅ 2026-10-11 (§15, §17); approvata il 2026-10-11 (§0, §17.11) |
| F-0 | Rossi e golden della guardia, generato prima del codice, via `test-author` (§17.8) | ✅ 2026-10-11 (§15) |
| F-1 | `financial_math/native_cash.py`, `effective_share`, la riga nella docstring | ✅ 2026-10-11 (§15) |
| F-2 | Il motore: registro nativo, cassa rivalutata, giorni «dirty» della cassa, K/R k2, via gli accumulatori di B13 | ✅ 2026-10-11 (§15) |
| F-C1 | Checkpoint 3: modulo e motore, con la guardia verde | ✅ 2026-10-11: `36b181836`, `aa6b6077a`, `384253663`; base riallineata col merge `daee275fe` (treno 41), revisione combinata verde (§15) |
| F-3 | Il servizio: card, riepilogo, storie, flussi dei contributi | ✅ 2026-10-12 (§15) |
| F-4 | Gate, confronto col golden, rapporto sul DB mock, tempi | ✅ 2026-10-12 (§15): 58 report cambiati su 76, tutti con cassa estera; identità tenute; E2E 27 + 37 + 9 |
| F-5 | Doc EN via `docs-writer` (§17.8) | ✅ 2026-10-12 (§15): 13 pagine EN e il testo del runner; build e check-links verdi; translate-validate misura il debito per M (75 errori, 75 avvisi) |
| F-W | «FX on cash» negli `other_effects` dei contributi, forma minima (§0); la chiave i18n solo col via del coordinatore | ✅ 2026-10-12 (§15), con la chiave `dashboard.fxOnCash` (via del coordinatore, treno 41) |
| F-AI | Facoltativo: il costo del nome nell'AI Export, al coordinatore; il codice solo col suo via (§0) | ✅ 2026-10-12 (§15): nessun bump (decisione del coordinatore); il developer ha scelto la (a) per la 1.2 e la (b) dopo, «con un codice tipizzato», nella sezione I del backlog |
| F-C2 | Checkpoint 4, fine F | ✅ 2026-10-12 (§15): C4–C8, nel treno 42 (`15cbff6fb`) |
| T8 | Indice post-1.2: la sezione I di `BACKLOG_POST_1.2.md` (§11) | ✅ 2026-10-12 (§15, «T8 / F-C3»); F-AI (b) aggiunta col checkpoint di M-16 (§15, «Treno 43 e F-AI») |
| F-C3 | Checkpoint 5: T8 e questa nota; la riga del runner a `:1070` passa a T | ✅ 2026-10-12 (§15): C9 `f10fcd04a`, nel treno 43 (`d27a2f729`) |

## 10. Rischi

- **Pre-frame**: esiste solo nei test (§3.6); i casi 9 e 10 lo coprono.
- **Quote diverse**: sulla linea del destinatario resta (s_B − s_A)·X; l'aggregato non cambia, è già così oggi.
- **Prezzo mancante**: X = 0. Il gradino del mittente durante il viaggio (ripiego al costo di `_compute_in_transit`) resta preesistente.
- **D2 e D5 cambiano aggregati**, nelle viste filtrate e per gli orfani:
  - ROI, TWRR e MWRR filtrati, il riepilogo del periodo;
  - il residuo «Other» (`portfolio_service.py:2073-2081`), perché i titoli ricevuti o inviati escono dal P&L;
  - l'AI Export per bucket (`ai_export/components/payloads/portfolio_broker.py:350-354`).
- **Vista singola**: i mark sono filtrati per scope, quindi un titolo senza quotazioni può essere MISSING in B da solo e prezzato nel combinato (preesistente).
- **Somma zero in `Decimal`**: lo stesso oggetto X per il più e per il meno.
- **Cache del blob** in memoria (TTL 24 h, :61): la chiave non cambia; il riavvio la svuota.
- **Coppie invertite** (arrivo prima della partenza): il flusso cade alla data più tarda, resta il residuo transitorio preesistente (B2).
- **Coppie sullo stesso broker**: saltate; un FX_CONVERSION interno a un broker resta com'è.
- **Semantica**: la linea di un broker è il P&L maturato mentre il valore stava lì; l'unrealized di un lotto si misura sempre dal costo originale.
- **Lo specchio del riepilogo per broker** (trovato prima di T1; decisione chiesta al coordinatore il 2026-10-10):
  - `PortfolioService.get_summary(include_breakdown=True)` non legge l'engine: ha un suo capitale per broker, `broker_total_invested` (`portfolio_service.py:736`, `:767-776`, `:802-803`). Il guadagno è NAV − capitale (`:1004-1019`).
  - Lo specchio somma DEPOSIT, WITHDRAWAL e gli ADJUSTMENT in natura.
  - Lo leggono la card di /brokers (`BrokerCard.svelte:154-157`) e l'AI Export (`portfolio_broker.py:792`, `fx_core.py:310`).
  - Dopo la cura, il grafico darà 0/0 a un trasferimento di cassa, mentre la card darà ancora −X/+X. Con D2, in una vista di un broker solo, il totale in testa (dall'engine) e la riga del broker (dallo specchio) divergono.
  - **Opzioni**:
    - A: un passo T2f, in cui la card prende la `capital_contribution` dell'ultimo stato dell'engine; prima un rosso in `test_portfolio_service.py`;
    - B: backlog B8.
  - Il §2 («chi legge le contribuzioni») resta vero: lo specchio non le legge, le rifà.
  - **Decisione (2026-10-10): opzione A**, e il compito si allarga. Il developer, testuale: «si sono sempre daccordo nel fattorizzare, specie in matematica, verifica che non ci siano altre zone che rifanno questo calcolo con regole loro e in caso migra anche loro, ma stai attendo a verificare che il risultato finale sia migliore delle parti, se ci sono cose a cui non avevi pensato, prima di buttarle integrale». Il coordinatore: prima T1b, poi l'inventario (§16), poi T2f; nessuna copia tolta prima della sua verifica.
  - **Esito (2026-10-11)**: T2f toglie lo specchio; le card prendono capitale e valore in viaggio dal motore (§15 T2f). T2g porta allo stesso orizzonte del motore anche la chiamata diretta senza `date_to` (§15 T1d/T2g).

## 11. Definition of done e gate

- Casi 1–18 verdi coi numeri attesi; le guardie verdi prima e dopo.
- Aggregati della vista combinata identici byte per byte; Σ P_b = P ogni giorno.
- Gate sulla 6157, un comando alla volta:
  - `services roi-fifo-utils`, `services portfolio-engine`, `services ai-export`, `api portfolio`;
  - `front build --debug`, poi gli E2E `front-portfolio dashboard` e `front-broker detail`; con T2f anche `front-broker list`, la pagina delle card;
  - `mkdocs build`, `mkdocs check-links`, `mkdocs translate-validate`.
- Lint e format del backend puliti.
- Nessun file vietato toccato; porta 6157 libera (`lsof -nP -iTCP:6157 -sTCP:LISTEN` vuoto).
- Questo piano aggiornato a ogni passo.
- A fine lotto (T8), la sezione I di `Phase_0/BACKLOG_POST_1.2.md` completa, secondo la regola «Post-release backlog index» (`coordinated-workstream.agent.md:164-172`): le voci di §14 e di §17.6 che restano dopo la 1.2, secondo la decisione su F.

## 12. CHANGELOG proposto (lo scrive il coordinatore)

- 🐛 **Fixed**: broker lines in the P&L chart no longer jump when money or securities move between two of your brokers; the total is unchanged.
- 🔄 **Changed**: in a view filtered to some brokers, securities sent to or received from a broker outside the filter count as capital at market value, not as a gain or a loss. The same applies to the leftover half of a transfer whose other broker was deleted.
- Treno 32 (checkpoint 1, T5a): la riga Fixed non nomina le card. «…and broker cards» entra con H (T5b).
- H (T5b), proposta per la riga Fixed: «Broker lines in the P&L chart and the broker cards no longer jump when money or securities move between two of your brokers; the total is unchanged. While a transfer is on its way, its value stays on the sending broker's card.»
- F: proposta in §17.10.

## 13. devWiki (T6, solo proposta)

`LibreFolio_devWiki/wiki/decisions/portfolio-pnl-series-contracts.md`, sezione G1a: i trasferimenti interni sono flussi di capitale per broker a somma zero, nel giorno d'arrivo, pari al valore che entra nel NAV del destinatario; il valore in viaggio resta al mittente; la regola di D2 nelle viste filtrate; D3, D4 e D5; gli invarianti di §4.5.

Testo proposto (bozza del 2026-10-10, in inglese come la wiki; la parte della card aggiunta il 2026-10-11, dopo T2f, ai punti 6–8). Lo archivia il coordinatore o lo storico, non io.

1. In «G1a», al posto del punto «Cash in transit stays with the departure broker until it arrives.»:

   ```markdown
   - **Internal transfers are zero-sum capital flows between broker lines** (lot 41, 2026-10). On the arrival day
     (the later leg date), a `linked_internal` TRANSFER / CASH_TRANSFER / FX_CONVERSION pair between two brokers
     adds X to the receiver's capital and removes the same Decimal X from the sender's
     (`_internal_transfer_flows()`). X is what enters the receiver's NAV that day: cash at the arrival FX rate,
     securities at arrival market value with the NAV's own valuation, both at the sender's ownership share.
     The portfolio capital never moves, so total P&L, ROI/TWRR/MWRR, candles and cash stay byte-identical.
   - **Rejected**: no flow (each line jumped by −X/+X at arrival while the total stayed right); securities at
     cost (a jump equal to the lot's unrealized gain would remain).
   - Value in transit, and its price move, stay with the sender until arrival; no flow during the trip.
   - A missing price at arrival gives X = 0, which is what enters the receiver's NAV; the value appears with the
     first price, on the broker that holds it.
   - Different ownership shares leave (s_B − s_A)·X on the receiver's line; the total is unaffected.
   - Filtered views: a securities TRANSFER leg whose partner is outside the view, or whose partner was deleted,
     is capital at market value on its own date (`_transfer_leg_capital()`); a cash leg in the same position is
     capital at its amount. B alone equals B in the combined view; A alone loses the in-transit move at departure.
   - ADJUSTMENT pairs keep their capital at cost and get no internal flow.
   ```

2. In «Consequences», un punto: «A byte-equality guard (`test_broker_internal_flows.py`) reruns the replay with the
   internal flows neutralised and checks that every combined-view aggregate is unchanged: the flows only move capital
   between broker lines.»
3. In «Source files», tre righe:
   - `backend/test_scripts/test_services/test_financial/test_portfolio_engine/test_broker_internal_flows.py` (internal flows, filtered views, orphans, aggregate guard);
   - `mkdocs_src/docs/financial-theory/technical-analysis/performance-metrics/portfolio-engine/deposited-capital.en.md` (theory, `#internal-transfers-broker-lines`);
   - il piano di questo lotto, col percorso che avrà dopo l'archiviazione.
4. Due pagine `problems/` nuove, dai reperti preesistenti fuori dal lotto: B4 (la cassa estera nell'engine non si rivaluta mai) e B11 (`dirty_days` ignora i giorni in cui si muove solo il cambio).
5. Prima di archiviare: `python3 LibreFolio_devWiki/check_source_paths.py`.
6. In «G1a», dopo i punti del punto 1, la card (H, 2026-10-11):

   ```markdown
   - **Broker cards read the same capital** (lot 41, step H). `PortfolioService.get_summary(include_breakdown=True)`
     no longer keeps its own per-broker capital (`broker_total_invested`: DEPOSIT/WITHDRAWAL plus in-kind
     ADJUSTMENT as override × quantity, transfers ignored). Each card takes `capital_contribution` and
     `in_transit_contribution` from the engine's `BrokerDailyContribution` at the valuation date. Market value
     (holdings rows at the valuation date, dust excluded) and cash (native balances × FX at that date) stay the
     service's own. NAV = MV + cash + in transit; gain = NAV − capital; percent only when capital > 0.
   - **Rejected**: card NAV = `nav_contribution` − engine cash + cash at T. The engine re-values a day only when
     it is dirty, so on a last day where only FX moved its market value would lag the holdings rows.
   - A card and the last point of its broker line can still differ by foreign-cash drift (B4), dust, and an
     FX-only move on a non-dirty last day (B11). The value in transit comes from the engine, so on such a day
     it lags on both.
   ```

7. In `wiki/decisions/broker-card-aggregation-no-n-plus-one.md`, «Consequences», un punto: «Since lot 41 (2026-10), the card's Gain/Loss reads capital and value in transit from the engine's per-broker slice; the service's own capital mirror is gone (see [[decisions/portfolio-pnl-series-contracts]], G1a).»
8. In «Source files» di `portfolio-pnl-series-contracts.md`, altre due righe:
   - `backend/app/services/portfolio_service.py` (`get_summary`, the per-broker breakdown);
   - `backend/test_scripts/test_services/test_financial/test_portfolio_service.py` (the card tests: same-day and multi-day transfer, foreign currency at the arrival rate).

## 14. Backlog

> Le voci aperte dopo la 1.2 sono nella sezione I di [`BACKLOG_POST_1.2.md`](../BACKLOG_POST_1.2.md) (T8, 2026-10-12), con le righe di `5d62658bb`. Qui sotto ogni voce tiene le righe del suo momento (§15, «Righe citate»).

- **B1**: rendere visibile l'avviso sulle quote diverse.
- **B2**: coppie invertite.
- **B3**: K/R delle gambe esterne e normali.
- ✅ **B4**: la cassa in valuta estera non viene mai rivalutata. Il registro dell'engine (`portfolio_engine.py:730-740`) somma ogni movimento al cambio della sua data, quindi il guadagno o la perdita di cambio sulla cassa non entra mai nel NAV né nel P&L: né a riposo, né quando la valuta si spende in un BUY o si riconverte con un FX_CONVERSION. La cassa in viaggio invece è al cambio del giorno (`book-value.en.md:23`). Ingrandito dall'inventario, §16.2. **Nella 1.2, dentro F (§0); analisi in §17.** **Chiuso il 2026-10-12** da F: il modulo `36b181836`, il motore `aa6b6077a`, il servizio `c04e44ff5` (treno 42).
- **B8**: `get_positions_contribution` (`portfolio_service.py:1703-2096`) ha un suo prezzo (`_get_price_at_date`, `:522`: ultima chiusura, senza ripiego sull'ultimo scambio né split) e, su un TRANSFER fra broker, sposta l'unrealized al costo: il mittente segna −ug_start, il destinatario tutto l'unrealized dall'acquisto. La somma delle righe è giusta. **T7**: dopo la 1.2, in U5 con V2/P2 e R4 (§17.6); i suoi flussi per posizione entrano invece in F (B14).
- **B9**: AI Export, reddito (`ai_export/components/portfolio_income.py:350-379`) e turnover (`broker_cost_efficiency.py:154`) applicano la quota grezza senza ruolo. EDITOR e VIEWER hanno quota 0 per schema (`schemas/brokers.py:364`), mentre engine e servizio usano 1 (`portfolio_engine.py:2494`). Il reddito usa `abs` (`portfolio_income.py:379`) e la docstring (`:335`) dice di rispecchiare `period_income`, che invece ha il segno (`portfolio_service.py:799`).
  - **Corretto il 2026-10-11** (decisione su F, §0). Nell'export del patrimonio lo 0 di Viewer ed Editor è giusto: la Dashboard passa all'export solo i broker di cui l'utente è Owner con quota > 0 (`getOwnedBrokers` e la guardia F2, `dashboard/+page.svelte:719-721`), come dice la doc (`user/brokers/sharing.en.md:53`).
  - Il difetto vero è più stretto: l'export dalla pagina di un broker dove l'utente è Viewer o Editor. Lì le cifre del report sono piene (scala 1, come la pagina), ma il turnover è moltiplicato per la quota grezza 0 (`broker_cost_efficiency.py:150-157`). In più c'è l'`abs` sul reddito.
  - La cura è una regola sola per export, quella della pagina da cui parte. **Dopo la 1.2, a T in U3** (il piano di T mette B9 in U3, non in U9).
- **B10**: `GrowthChart.svelte:594-600`, `periodBasePnl` dichiarato e mai usato.
- **B5**: nel waterfall, una voce per i trasferimenti al valore di mercato.
- **B6**: coppie ADJUSTMENT coi flussi al valore di mercato (oggi, se di più giorni, un intervallo «cash» a valore 0).
- **B7**: uno split durante il viaggio.
- **B11**: il salto dei giorni ignora i cambi. `dirty_days` (`portfolio_engine.py:902-936`) raccoglie transazioni, flussi, bordi dei viaggi, prezzi e split, ma non le date dei cambi: in un giorno in cui si muove solo il cambio, le posizioni in valuta e la cassa in viaggio restano al valore del giorno prima. Trovato dal test-author sul caso 3 (d2). Preesistente. **T7**: la parte della cassa entra in F; quella dei titoli va in U (U1 o U5), perché romperebbe la guardia (§17.6). **La parte della cassa è chiusa** (`aa6b6077a`, treno 42); quella dei titoli resta, nella sezione I del backlog.
- **B12** (2026-10-11, righe del codice di H), latente: le righe con data futura in una chiamata diretta senza `date_to`. Lì il motore si ferma a oggi, ma due letture del servizio tengono tutte le righe del broker:
  - `_signed_transaction_sums_by_date` (`portfolio_service.py:1533`), per le storie di redditi, costi e depositi;
  - `get_positions_contribution` (`:1775`).
  - Nessun effetto in produzione: `get_report` passa sempre `effective_date_to` (`:2120`, `:2299-2372`). In `get_summary` lo stesso caso lo ripara T2g (§15 T1d/T2g). Da riguardare in T7, la seconda insieme a B8.
  - Nessuna validazione impedisce una data futura. Se debba esserci, è una scelta di prodotto fuori dal lotto.
  - **T7**: le storie e i flussi dei contributi in F (§17.4); le quantità dei contributi in U5, con B8.
  - **Storie e flussi dei contributi chiusi** da F-3 (`c04e44ff5`, treno 42). Le quantità dei contributi restano, nella sezione I del backlog.
- ✅ **B13** (T7): gli accumulatori del motore (`per_realized`, `per_income`, `per_fees_taxes`, `unalloc_income`, `unalloc_fees`: `portfolio_engine.py:792-796`, `:1069`, `:1100-1113`, campi `:1834-1838` di `PortfolioCalculationResult`) non hanno un lettore in produzione: in `get_positions_contribution` (`portfolio_service.py:1755-1760`) sono dict locali con lo stesso nome. Li leggono solo i test (`test_portfolio_engine_vnext.py:664-692`; `test_portfolio_engine/test_signed_income.py:211-213`, `:250-257`, `:402-403`). `per_realized` doppia `realized_sales`. **In F**: li sostituisce la vista dei flussi; i test passano a quella, con gli stessi numeri. **Chiuso** (`aa6b6077a`, treno 42).
- ✅ **B14** (T7): nei contributi una coppia di cambio mancante si perde in silenzio (`portfolio_service.py:1789`), mentre il riepilogo la segnala (`:780`). **In F.** **Chiuso** (`c04e44ff5`, treno 42): i flussi dei contributi e quelli del riepilogo vengono dalle stesse righe, con le stesse coppie mancanti. Lo schema dei contributi non ha un campo per le coppie, quindi il segnale resta nel riepilogo.
- **B15** (T7): il PAC rifà la custodia per conto suo, quantità e cassa nativa per broker e valuta (`portfolio_allocation_source.py:46-68`, `:107-133`). Lo stesso vale per la cassa della pagina del broker (§16, punto 9: `transaction_service.get_cash_balances`, `broker_service.py:392`; file fuori dal lotto). **Dopo la 1.2**, in U.
- **B16** (T7), latente: depositi e costi in valore assoluto in un consumatore, con segno in un altro. Il validatore impone il segno negativo a BUY, WITHDRAWAL, FEE e TAX (`schemas/transactions.py:189-190`), quindi oggi non cambia nulla. Nessuna azione: F tiene i segni di ogni consumatore.
- **B17** (F-W, 2026-10-12): il risultato di cambio sulla cassa in viaggio resta nel residuo «Other» (test S6: residuo −175, nessuna riga FX). §15 «F-W», «Fuori pista».
- **B18** (F-W, 2026-10-12): lo spread di un FX_CONVERSION sullo stesso broker resta nel residuo (test S5: −10). Idem.
- **B19** (F-W, 2026-10-12), preesistente: nei contributi le righe degli unallocati seguono l'ordine del set (`set(unalloc_income) | set(unalloc_fees)`), non quello d'accesso. La cura cambia l'ordine delle righe, non le cifre. Idem.

## 15. Avanzamento

> **Righe citate**: ogni nota cita il codice del suo momento.
> - Da T0 a T1/T1b, e le sezioni scritte allora (§4, §5, §14, §16): `d59762e0a`. Lì `portfolio_service.py` è identico a `b20eac991`.
> - Da T2a–T2e a T1c: `b20eac991`, cioè il motore del checkpoint 1. Vale anche per i punti di §16 corretti in T1c.
> - Da T2f in poi, e i punti di §16.2 rivisti per T2f: il codice di H, quello del checkpoint 2 (T5b).
> - Da T7 (§17), e le ancore di §14 riallineate allora: `251067435`, dove il codice è identico a `43d92ed23`.
> - Da F-C3, la sezione I del backlog e B17–B19 di §14: `5d62658bb`.

### T0 — Piano nel journal ✅ (2026-10-10)

> **Note implementazione**: piano scritto dal piano di sessione approvato, con la base portata a `d59762e0a` (treno 30) e le decisioni D1–D6 risolte come consigliato, D5 compresa. Ancore del codice riverificate a `d59762e0a`: il motore è identico a `e32f47133`. I numeri di §5 ricalcolati a mano sul codice.
>
> **⚠️ Fuori pista**: `deposited-capital.en.md:19` è già fuori dal codice (§3.10). Lo sistema T3.

### T2-inv — Inventario dei calcoli fuori dal motore ✅ (2026-10-10, in verifica dal coordinatore)

> **Note implementazione**: inventario in §16, dal codice a `d59762e0a`. Letti direttamente `portfolio_service.py`, `broker_service.py`, l'engine e le pagine `book-value`/`index` del motore; due sottoagenti `explore` in sola lettura per l'AI Export e per il frontend. Nessuna copia tolta.
>
> **⚠️ Fuori pista**: lo specchio della card non copia solo il capitale, rifà anche il NAV, e lo fa in modo diverso dal motore: esclude il valore in viaggio (durante un viaggio il valore sparisce da tutte le card) e rivaluta la cassa in valuta al cambio di oggi, cosa che il motore non fa. Quindi B4 è più grande del previsto (§14) e su quel punto la copia è migliore del motore. Per questo la card va presa dal motore con lo scambio della cassa (opzione H, §16.2), non integrale.

### T3 — Doc EN via `docs-writer` ✅ (2026-10-10)

> **Note implementazione**: `docs-writer` `1ab6cb5d` ha cambiato solo le due pagine di §7.
> - `user/dashboard/charts.en.md:79-88`: il paragrafo «Broker lines» (nessun salto all'arrivo), 4 punti (in viaggio, quote diverse, valore mancante, broker fuori dalla vista) e il link alla teoria.
> - `deposited-capital.en.md`: `:19` corretta (ADJUSTMENT al costo, TRANSFER fuori dalla vista al valore di mercato), la tabella «What Counts» a 7 righe, e la sezione nuova `#internal-transfers-broker-lines` con le formule per broker, il flusso interno, il valore in viaggio, i casi speciali, le viste filtrate e due esempi.
> - Riletta contro D1–D6 e §4. Rifatti a mano gli esempi: titoli in viaggio, combinato e viste singole, compresa la formula A da solo = A combinato − s_A·[V(min(t, t_arr)) − V(t_dep)]; USD in viaggio (C_A = −30); cassa 5000/1000 con commissione e quota 50 %; coppia ADJUSTMENT contro TRANSFER (A = 0, B = +20 contro A = +20, B = 0, confermato su `_is_capital_adjustment` e `portfolio_engine.py:1003-1023`). Tutto torna.
> - Evidenze del docs-writer: `mkdocs build` stretto verde (`/tmp/libreFolio_l41_t3_build.log`); `check-links` 95 validi, 0 rotti (`/tmp/libreFolio_l41_t3_check_links.log`); `translate-validate` da 90 a 126 errori e da 159 a 195 avvisi, tutti delle due pagine, cioè il debito di traduzione per M (`/tmp/libreFolio_l41_t3_translate_validate.log`). Nessuno stamp.
> - Nessuna pagina developer di G1a esiste in `mkdocs_src/docs/developer/`: niente da aggiornare.
>
> **⚠️ Fuori pista**: `period-pnl.en.md:15`, `roi.en.md:21`, `twrr.en.md:6` e `mwrr.en.md:88` dicono ancora «priced in-kind ADJUSTMENT/TRANSFER capital». Dopo il lotto è impreciso, non sbagliato. Sono fuori dalle mie superfici: propongo al coordinatore una riga per pagina che rimandi a «What Counts».

### T1 / T1b — Rossi via `test-author` ✅ (2026-10-10)

> **Note implementazione**: `test-author` `c84d2910`, solo file di test.
> - `test_portfolio_engine/test_broker_internal_flows.py` (nuovo, 47 test): casi 1–17 di §5 coi numeri attesi, le viste singole e gli orfani (D2, D5), la guardia degli aggregati e il preload dei cambi (T2c).
> - `test_broker_pnl_contributions.py`: `TestScenarioBInTransitShareFix::test_internal_transfer_moves_capital_on_arrival` (caso 2 e 18).
> - `test_scope_classifier.py`: `TestOrphanLinkedTypes`, 2 rossi (D5 cassa e FX) e 2 guardie; commento di `TestLinkedExternal` allineato a D2.
> - `test_portfolio_service.py`: i 2 rossi della card (T1b, §16.3), su cassa in giornata e in viaggio.
> - Contratto dell'aggancio, fissato dai test: `DailyStateBuilder._internal_transfer_flows(self) -> list`, dove `[]` vuol dire nessun flusso. La guardia lo sostituisce con `[]` e confronta byte per byte i due calcoli, esclusi solo `DailyPortfolioState.broker_contributions` e `EngineEndState.cumulative_ecf_by_broker`; il NAV per broker si confronta a parte. `test_neutral_hook_restores_todays_lines` impedisce che la guardia passi a vuoto.
> - Prova del rosso sulla 6157: `services roi-fifo-utils` → **30 failed, 555 passed**; i 30 sono tutti voluti (28 di T1, 2 di T1b). Log `/tmp/libreFolio_l41_t1_verify.log`.
>
> **⚠️ Fuori pista**:
> - Caso 3: P a d2 non è fissato. d2 non è un giorno «sporco» (solo il cambio si muove), quindi l'engine copia d1. È B11 (§14), preesistente.
> - T1b: durante un viaggio il test non fissa `cash_total` della card, perché il NAV del mittente (5000) include il valore in viaggio e la sua cassa (4000) no. Dove mostrare quei 1000 sulla card lo decide T2f.

### T2a–T2e — Engine ✅ (2026-10-10)

> **Note implementazione**: solo `backend/app/services/portfolio_engine.py` (+127/−4), in un passaggio.
> - **T2a** `_internal_transfer_flows` (:1673): coppie `linked_internal` di `_LINKED_TYPES` su broker diversi, dedupe su (min id, max id), mittente e destinatario dai segni. Il passo 3b (:760-769) le applica a `ecf_by_date_by_broker` col solo Decimal `flow_value`, mai a `ecf_by_date`. Le date di flusso entrano esplicitamente in `preframe_tx_dates` (:805) e in `dirty_days` (:910). Commento 4f2 aggiornato (:1200).
> - **T2b** `_transfer_leg_capital` (:1731), chiamato nel pre-frame (:882) e nel frame (:1030), dopo il `continue` degli split e prima dei rami in natura: `cumulative_ecf` e `cumulative_ecf_by_broker`, mai `ecf_today`.
> - **T2c** in `_preload_fx_rates` (:2797): per ogni TRANSFER con asset e quantità, con data < `date_from`, le valute dei prezzi e dell'asset alla data della gamba. Docstring aggiornata.
> - **T2d** ramo unlinked del classificatore (:301): ECF anche per `_CASH_LINKED_TYPES`.
> - **T2e** `ruff check` e `black --check` puliti sull'engine e sui 4 file di test del lotto.
> - Evidenze sulla 6157:
>   - `services roi-fifo-utils` → **2 failed, 583 passed**: i 28 rossi dell'engine sono verdi, restano solo i 2 della card (T1b, aspettano T2f). Nessun altro test di `test_financial/` cambia. Log `/tmp/libreFolio_l41_t2_roi.log`.
>   - `services portfolio-engine` → **42 passed** (vnext, col test delle chiavi esatte del preload). Log `/tmp/libreFolio_l41_t2_pe.log`.
>
> **⚠️ Fuori pista**:
> - **Data del flusso**: X si valuta alla data del flusso, max(date delle gambe), come dice la doc (t_arr = la gamba più tarda), non alla data del destinatario. Coincidono sempre, tranne nelle coppie invertite (B2): lì il lato del mittente resta pulito anche per i TRANSFER. §4.1 allineato.
> - **Forma della valutazione dei titoli**: `MV(|q|) × s_A`, come `_compute_in_transit`, invece di `MV(|q| × s_A)` di §4.1. `compute_holding_value` è lineare (`(qty / base) × prezzo`, nessuna quantizzazione), quindi le due forme coincidono; questa è il valore che A portava in viaggio. §4.1 allineato.
> - **Nome dell'helper D2**: `_transfer_leg_capital`, non `_external_transfer_capital`, perché copre anche gli orfani. §4.2 allineato.
> - **D5 nello stesso passaggio di D2**: l'helper non guarda `related_transaction_id`, quindi gli orfani TRANSFER passano da lì. Resta separabile: per toglierlo bastano due righe, cioè `tx.related_transaction_id is not None` nell'helper e il ritorno del ramo unlinked (:301) a `_EXTERNAL_CASH_TYPES`. I test D5 sono a parte (`TestOrphanLinkedTypes`, la classe `Orphan`).
> - Una coppia interna con tipi diversi fra le gambe (dato degenere) non dà flusso né capitale D2: come oggi.
> - Il `noqa: C901` sul metodo nuovo non serve (complessità ≤ 10, provato con ruff senza): tolto.

### T4 (parziale) — Gate backend che non dipendono da T2f ✅ (2026-10-10)

> **Note implementazione**: sulla 6157, un comando alla volta, con l'engine di T2a–T2e e senza T2f.
> - `services ai-export` → **929 passed** (i componenti broker e portafoglio dell'AI Export leggono l'engine). Log `/tmp/libreFolio_l41_t4_aiexport.log`.
> - `api portfolio` → **51 passed**; dopo, `lsof -nP -iTCP:6157 -sTCP:LISTEN` vuoto. Log `/tmp/libreFolio_l41_t4_apiportfolio.log`.
> - `services lots-analysis-pure` → **106 passed** (`DerivedViewsBuilder` legge l'engine). Log `/tmp/libreFolio_l41_t4_lotspure.log`.
> - Raggio di D2/D5 fuori da `test_financial/`: i test API che usano TRANSFER (cancellazione account, broker, transazioni, promozione di split e trasferimenti, WAC inline) non hanno asserzioni che dipendono dall'engine; `BrokerService.get_summary` non usa l'engine. Nessun test esistente cambia.
> - Restano, dopo T2f: `services roi-fifo-utils` (i 2 rossi della card), `front build --debug`, gli E2E `front-portfolio dashboard` e `front-broker detail`, e i tre comandi `mkdocs`.

### T5a — Checkpoint 1, solo engine ✅ READY (2026-10-11)

> **Note implementazione**: su richiesta del coordinatore (§0), il checkpoint prende il lavoro fatto fino al T4 parziale, senza la card.
> - **Dentro, 7 percorsi**:
>   - `portfolio_engine.py`;
>   - i test dell'engine: `test_broker_internal_flows.py` (nuovo), `test_broker_pnl_contributions.py`, `test_scope_classifier.py`;
>   - le due pagine di T3;
>   - questo piano.
> - **Fuori**: `test_portfolio_service.py`, cioè i 2 rossi della card (T1b).
>   - Il suo diff è solo aggiunte (+86/−0: 3 helper e i 2 test), quindi senza di lui gli altri test del file sono quelli della base.
>   - Resta nella worktree, fuori dallo stage, ed entra con T2f nel checkpoint 2.
> - **Evidenze sulla 6157**, sull'engine finale (dopo la rimozione del `noqa`, che è venuta dopo le prove di T2):
>   - `services roi-fifo-utils` → **583 passed, 2 failed**. I 2 sono i rossi della card, fuori dal checkpoint, quindi sull'albero del checkpoint: 583 passed, 0 failed. Log `/tmp/libreFolio_l41_t5a_roi.log`.
>   - `services portfolio-engine` → **42 passed**. Log `/tmp/libreFolio_l41_t5a_pe.log`.
>   - `services ai-export` 929, `api portfolio` 51 e `services lots-analysis-pure` 106 (T4 parziale, qui sopra), già sull'engine finale.
>   - `ruff check` e `black --check` puliti sui 4 file Python; `git diff --check` pulito; nessuno spazio in coda nei 2 file nuovi; porta 6157 libera.
>   - Doc: le prove di T3 (`mkdocs build` stretto, `check-links`, `translate-validate`) valgono ancora, perché le due pagine non sono più cambiate.
> - **Non eseguiti**: `front build` (non cambiano né il frontend né lo schema dell'API) e gli E2E `front-portfolio dashboard` e `front-broker detail`.
>   - Restano nel T4 dopo H.
>   - Gli spec controllano la struttura (le righe dei broker, le righe OHLC), non i valori: `dashboard.spec.ts:575-584`, `:656-658`; `brokers-detail.spec.ts:944-1017`.
> - **Conflitti**: `dev_release2` è a `f4a42bf4a` (treno 31). Fra la base `d59762e0a` e quella punta nessun cambio:
>   - né sui 7 percorsi;
>   - né su `test_portfolio_service.py` e `portfolio_service.py`;
>   - né in `backend/`, nel runner, o nelle pagine di teoria e della dashboard.
>
> **⚠️ Fuori pista**: il lotto si divide in due checkpoint.
> - Fra il primo e il secondo, a un trasferimento interno la card dei broker mostra ancora −X/+X, il grafico no.
> - La riga del CHANGELOG del treno 32 non nomina le card (§12).
>
> **Integrato** (2026-10-11): `883681766` (engine e test), `3801cf93e` (doc EN), `5c4c2c0e8` (piano), fusi come `46272c3f0`; treno 32, `dev_release2` = `b20eac991`, albero `35d2afdc0533`. La worktree è avanzata lì, con `test_portfolio_service.py` intatto (+86, blob `b6d6642023ec`). Il treno 32 non tocca `portfolio_service.py` né gli schemi.

### T1c — Rosso della card col cambio ✅ (2026-10-11)

> **Note implementazione**: scenario in §16.3, scritto dal `test-author` (`test_portfolio_service.py:448-491` nel codice di H; `:431-474` quando è stato scritto, prima degli helper di T1d), accanto ai rossi di T1b; ruff e black puliti.
> - Prova del rosso sulla 6157: `services roi-fifo-utils` → **583 passed, 3 failed**, cioè i 2 di T1b e T1c. Log `/tmp/libreFolio_l41_t1c_red.log`.
> - T1c dà le 7 discrepanze previste: il 14 A 475 / −325 / −0,40625 (manca il valore in viaggio); il 20 A −200 / −0,25 e B +600 / 0 (il trasferimento non sposta il capitale).
>
> **Verifiche prima del codice di T2f** (sola lettura):
> - Cache del blob solo in memoria (`theine`, `portfolio_engine.py:61`); `BrokerDailyContribution` ha un solo costruttore (`portfolio_engine.py:1209`), nessuno la serializza, e i test la controllano con `isinstance`. Un campo nuovo è sicuro.
> - Le card scorrono `broker_names`, cioè ogni broker accessibile: B compare anche vuoto (`portfolio_service.py:1004-1019`).
> - Un arrivo oltre `date_to` è caricato da `get_needed_paired_ids` (`portfolio_engine.py:255-265`) e resta `linked_internal`, con l'intervallo in viaggio: la vista a metà viaggio non diventa orfana.
>
> **⚠️ Fuori pista**:
> - **Il ripiego per il cambio mancante (§16.2) non serve**: engine e servizio usano lo stesso `convert_bulk`, che riempie all'indietro senza limite. Se il cambio manca a T, manca anche a ogni movimento ≤ T. §16.2 è corretto.
> - **La MV della card resta senza la polvere**: il servizio esclude le posizioni sotto 0,00001 unità (`portfolio_service.py:850`), il motore no. T2f tiene la MV della card com'è (le righe della tabella, §16.2), quindi la card continua a escluderla.
> - **Il cambio mancante sulle rettifiche in natura** è già coperto: `average_cost.missing` → `_missing_fx` → `_engine_missing_fx_pairs` (`portfolio_service.py:298`). Togliere `inkind_missing` dallo specchio non perde coppie.
> - **Reperto per F**: un giorno con un solo cambio di cambio non è «dirty» (`portfolio_engine.py:899-933`: transazioni, flussi, prezzi, bordi dei viaggi, split). Il giorno si copia dal precedente (`:939-976`), quindi la cassa in viaggio e la MV in valuta senza un prezzo nuovo restano al cambio dell'ultimo giorno «dirty».
>   - Per questo T1c verifica il viaggio il 14, ultimo giorno del viaggio (sempre «dirty»), con la sua riga di cambio. Nello scenario iniziale la riga 0,95 era il 12: lì la card avrebbe dato 925 (cassa 475 + viaggio 450, copiato dal 10), non 950. Lo scarto è del motore, non di H.
>   - Entra nell'analisi di F (T7): rivalutare la cassa ogni giorno (B4) chiede di rendere «dirty» i giorni di cambio, con il costo relativo.

### T2f — La card dei broker dal motore ✅ (2026-10-11)

> **Note implementazione**:
> - `portfolio_engine.py`:
>   - `BrokerDailyContribution` ha un campo nuovo, `in_transit_contribution` (`:530-532`). È la parte in viaggio di `nav_contribution`: interna, mai esportata, la legge solo la card.
>   - Nel ciclo 4f2 (`:1210-1218`) lo stesso valore entra nella somma del NAV, nello stesso ordine di prima, e nel campo nuovo. Gli altri campi restano identici byte per byte.
> - `portfolio_service.py`:
>   - **Tolto lo specchio**: `broker_total_invested`, il blocco degli ADJUSTMENT in natura, e le due somme di DEPOSIT/WITHDRAWAL in `total_invested` e `broker_total_invested`.
>   - **Restano**: gli accumuli del periodo (`_total_deposited`, `_total_withdrawn`, `:788-793`), la cassa, i redditi, le commissioni e `all_missing_pairs`.
>   - **Card** (`:989-1001`):
>     - capitale e valore in viaggio vengono dall'ultimo stato del motore (`last_state.broker_contributions`); senza stato valgono 0;
>     - NAV = MV della tabella + cassa a T + valore in viaggio;
>     - guadagno = NAV − capitale; la percentuale si calcola solo con capitale > 0.
>   - **`total_invested`** vale 0 quando manca uno stato del motore. Il motore parte dalla prima transazione: `date_from=None`, anche nel report (`:2196-2203`). Lo stato manca quindi solo se non c'è nessuna transazione ≤ T, e anche la vecchia somma dava 0. Nessun cambio, salvo una chiamata diretta senza `date_to` con sole righe future, dove la vecchia somma le contava (§15 T1d/T2g).
> - Nessun cambio di schema né di API. Le cache sono solo in memoria (`portfolio_service.py:112`, `portfolio_engine.py:61`).
> - Ruff e black sono puliti sui due file.
>
> **Gate sulla 6157**, un comando alla volta (log in `/tmp/libreFolio_l41_t2f_*.log`):
> - `services roi-fifo-utils` → **586 passed**. I 3 rossi di T1b e T1c ora sono verdi. Nessun altro test cambia, nemmeno `test_summary_with_breakdown_uses_per_broker_invested`.
> - Verdi anche `services portfolio-engine` (42), `services ai-export` (929), `api portfolio` (51) e `services lots-analysis-pure` (106).
> - Dopo i gate la porta 6157 è libera.
>
> **⚠️ Fuori pista**:
> - **Il disegno approvato è cambiato prima del codice.** Era: NAV della card = `nav_contribution` − cassa del motore + cassa a T, con un campo `cash_contribution`.
>   - Il motore rivaluta solo i giorni «dirty», e T non sempre lo è (§15 T1c). In un ultimo giorno in cui si muove solo il cambio, la MV del motore resta al cambio precedente, mentre le righe della tabella sono a T.
>   - Ora la card prende dal motore solo il capitale e il valore in viaggio, e tiene la sua MV e la sua cassa a T. Il NAV ha la forma approvata in §16.2: MV + IT + cassa a T.
> - **Cosa cambia di proposito rispetto allo specchio**:
>   - il capitale conta le metà `linked_external` al valore di mercato (D2) e i trasferimenti interni all'arrivo;
>   - il costo degli ADJUSTMENT in natura viene dal pool del costo medio (D4), non da override × quantità;
>   - la percentuale è 0 con capitale ≤ 0; prima si divideva per qualunque capitale non nullo.

### T3b — Doc EN della card ✅ (2026-10-11)

> **Note implementazione**: `docs-writer` (`9879aae8`) ha aggiunto un solo paragrafo, `user/brokers/index.en.md:11`, e nient'altro.
> - **Contenuto**:
>   - Gain/Loss = NAV − capitale;
>   - capitale = depositi − prelievi + costo dei titoli portati senza cassa + trasferimenti dagli altri broker − quelli verso gli altri, al valore del giorno d'arrivo;
>   - un trasferimento fra due broker propri non dà guadagno a uno e perdita all'altro, e durante il viaggio il valore resta sulla card del mittente;
>   - la percentuale è 0,00 % con capitale ≤ 0;
>   - link a `deposited-capital.md#internal-transfers-broker-lines`.
> - **Riletto contro il codice**: `BrokerCard.svelte:143-157`; `portfolio_service.py:989-1001`; la pagina Brokers chiede il report di tutti i broker accessibili, senza date (`brokers/+page.svelte:175`). Nessuna affermazione su Σ card = Total P&L.
> - **Due scelte del docs-writer**, entrambe nei fatti: il costo dei titoli portati senza cassa (ADJUSTMENT in natura); «zero o meno» per lo 0,00 %.
> - **Evidenze**:
>   - `mkdocs build` stretto verde (`/tmp/libreFolio_l41_t3b_build.log`);
>   - `check-links`: 95 validi, 0 rotti (`/tmp/libreFolio_l41_t3b_check_links.log`);
>   - `translate-validate`: da 126/195 a 129/198 errori/avvisi (`/tmp/libreFolio_l41_t3b_tv_before.log`, `_after.log`). Il link nuovo manca in IT, FR ed ES: un link-missing e un link-count per lingua.
> - Nessuno stamp: è debito vero per il secondo giro di M. La pagina non ha un timbro «last updated».

### T4 — Gate completi ✅ (2026-10-11)

> **Note implementazione**: sulla 6157, un comando alla volta, con T2f.
> - Backend: in §15 T2f (586, 42, 929, 51, 106).
> - `front build --debug` verde (`/tmp/libreFolio_l41_t4_front_build.log`).
>   - Prima del build, `node_modules` coincide col lock: 0 differenze sui pacchetti non opzionali.
>   - Il build risincronizza i tipi API; nessun file tracciato cambia.
> - E2E:
>   - `front-portfolio dashboard` → **27 passed** (`/tmp/libreFolio_l41_t4_e2e_dashboard.log`);
>   - `front-broker detail` → **35 passed** (`/tmp/libreFolio_l41_t4_e2e_broker_detail.log`);
>   - `front-broker list` → **9 passed** (`/tmp/libreFolio_l41_t4_e2e_broker_list.log`).
> - I tre comandi `mkdocs` sono in T3b.
> - Dopo i gate `lsof -nP -iTCP:6157 -sTCP:LISTEN` è vuoto.
>
> **⚠️ Fuori pista**: ho aggiunto `front-broker list` ai gate di §11. È la pagina delle card (`brokers.spec.ts`). Come gli altri E2E controlla la struttura e non i numeri: i valori della card li fissano T1b e T1c.

### T1d / T2g — L'orizzonte della card ✅ (2026-10-11)

> **⚠️ Fuori pista**: reperto trovato rileggendo il diff per T5b, prima del checkpoint 2.
> - **Due orizzonti diversi**, in una chiamata diretta di `get_summary` con `date_to=None`:
>   - il motore si ferma a oggi (`portfolio_engine.py:2544`, `actual_to = date_to or today`), quindi anche capitale, valore in viaggio, MV della card (`position_states_end`) e la testata (`net_worth`, `cash_total`, `:1218-1222`);
>   - la cassa della card legge invece tutte le righe del broker, anche quelle con data futura (`_get_transactions(broker_id, date_to=date_to)`, `portfolio_service.py:759` prima di T2g). Nessuna validazione impedisce una data futura.
> - **Cosa rompe H**, nella chiamata diretta:
>   - un trasferimento di cassa partito ieri con l'arrivo registrato fra tre giorni (coppia interna, il motore carica tutte le righe, `:2497-2499`): A ha −X di cassa e +X in viaggio, e va bene. B ha già +X di cassa ma nessun capitale, perché l'arrivo è futuro: guadagno +X, e Σ card = NAV + X;
>   - un deposito con data futura: cassa +X, capitale invariato, guadagno +X.
>   - Prima di H lo specchio leggeva le stesse righe future della cassa, e il guadagno restava 0 per caso. Lo specchio aveva quindi una regola che il motore non ha: lo stesso orizzonte della cassa. È il caso della decisione del developer (§10): «stai attendo a verificare che il risultato finale sia migliore delle parti».
> - **Già sbagliato prima di H**, nella chiamata diretta con righe future: una BUY (cassa −X, nessuna MV), un dividendo (+X), il periodo (`total_deposited`, redditi e commissioni del periodo, il residuo «Other»), la lista delle casse.
> - **Portata, rivista dopo la cura e prima del checkpoint: nessun effetto in produzione.**
>   - L'unico chiamante, `get_report`, passa sempre `date_to = date_to or today` (`portfolio_service.py:2120`, `:2214-2222`).
>   - La pagina Brokers chiede il report senza date (`brokers/+page.svelte:175`), ma il report risolve oggi prima di chiamare il riepilogo. Lo stesso vale per l'API (`portfolio_api.py:239-240`), per l'AI Export (`fx_core.py:313`, `portfolio_broker.py:795`, `asset_resources.py:259`) e per il rischio (`risk/service.py:496`).
>   - Il ramo con `date_to=None` lo usano solo le chiamate dirette: i test del servizio e un chiamante futuro.
>   - In un primo momento avevo scritto che il difetto si vedeva nella pagina Brokers: era sbagliato.
>   - T2g resta: H peggiora la chiamata diretta (guadagno +X), e una riga la rende coerente con la testata.
> - **Cura proposta (T2g)**, una riga: `_get_transactions(broker_id, date_to=valuation_date)`.
>   - Con `date_to` dato, `valuation_date == date_to`: nessun cambio.
>   - Senza righe future: nessun cambio.
>   - Con righe future e `date_to=None`: card, lista delle casse, totali del periodo e lotti leggono lo stesso orizzonte del motore e della testata.
> - **T1d**: il rosso via `test-author`, prima della cura.
>
> **T1d ✅ (2026-10-11) — Note implementazione**: `test-author` (`t1d-horizon-red`) ha aggiunto due test in `TestPortfolioServiceGetSummary` (`test_portfolio_service.py:493-562`), con date relative a oggi, ognuna ad almeno due giorni, così una mezzanotte non sposta nessuna riga.
> - `…_internal_cash_transfer_arriving_after_today_stays_in_transit`: 5000 depositati ad A dieci giorni fa; 1000 partono due giorni fa e arrivano a B fra tre. Attesi oggi A 5000 (cassa 4000 + 1000 in viaggio) / 0 / 0 e B 0 / 0 / 0; Σ card = testata = 5000.
> - `…_future_dated_deposit_is_outside_today_valuation`: 5000 dieci giorni fa, 700 fra cinque. Attesi la card 5000 / 0 / 0 con cassa 5000, la testata 5000 e `total_deposited` 5000.
> - Helper: `_deposit_and_transfer` ha la chiave opzionale `deposited_on` (predefinita 2025-01-01, i chiamanti di prima non cambiano); nuovo `_card_cash_problems`.
> - **Prova del rosso sulla 6157**: `services roi-fifo-utils` → **586 passed, 2 failed**, i due nuovi, coi numeri previsti (`/tmp/libreFolio_l41_t1d_red.log`):
>   - B: NAV 1000, guadagno 1000, cassa 1000; Σ card 6000 contro una testata di 5000;
>   - A: NAV 5700, guadagno 700 (0,14), cassa 5700; `total_deposited` 5700.
>
> **T2g ✅ (2026-10-11) — Note implementazione**:
> - `portfolio_service.py:759-761`: `_get_transactions(broker_id, date_to=valuation_date)`, con due righe di commento: lo stesso orizzonte del motore, quindi nessuna riga successiva raggiunge cassa, totali del periodo e lotti.
> - In `get_summary` è l'unica lettura delle transazioni. Le altre due tengono `date_to=date_to` e restano fuori da H:
>   - `_signed_transaction_sums_by_date` (`:1533`), per le storie di redditi, costi e depositi;
>   - `get_positions_contribution` (`:1775`).
>   - Anche loro ricevono sempre `effective_date_to` da `get_report` (`:2299-2372`): nessun effetto in produzione. Le annoto come B12 (§14), latenti.
> - Ruff e black puliti su servizio, motore e test.
> - **Gate sulla 6157**, un comando alla volta (log in `/tmp/libreFolio_l41_t2g_*.log`):
>   - `services roi-fifo-utils` → **588 passed**: i 2 rossi di T1d ora sono verdi, nessun altro test cambia;
>   - `api portfolio` → **51 passed**; `services ai-export` → **929 passed**;
>   - E2E sul build di T4 (il frontend non è cambiato): `front-portfolio dashboard` **27**, `front-broker detail` **35**, `front-broker list` **9**.
>   - Non ripetuti: `services portfolio-engine` (42) prova solo il motore, che T2g non tocca; `services lots-analysis-pure` (106) prova builder puri con `db=None` (`_backend_services.py:1084-1096`).
>   - Dopo i gate la porta 6157 è libera.
> - **Cosa cambia per l'utente: nulla.** In produzione `valuation_date == date_to` sempre (vedi «Portata»), quindi la lettura resta identica. Cambia solo la chiamata diretta senza `date_to`: lì card, lista delle casse, totali del periodo, «Other» e lotti stanno a oggi, come la testata. Nessuna riga di CHANGELOG.

### T5b — Checkpoint 2, H ✅ (2026-10-11), nel treno 35

> **Note implementazione**:
> - **Base**: HEAD `b20eac991` (treno 32).
>   - Il target è andato avanti a `c0d933abf` (treno 33, poi tre commit di documenti). Nessuno tocca i 5 percorsi di H: `git diff --stat b20eac991 c0d933abf -- <percorsi>` è vuoto.
>   - In `user/brokers/` il treno 33 cambia solo le traduzioni, alla riga dell'ordine delle icone: nessuna sovrapposizione col paragrafo di T3b.
> - **Delta**: 5 file tracciati modificati, nessun file nuovo, stage vuoto.
>   - Motore: il campo `in_transit_contribution` e il ciclo 4f2.
>   - Servizio: specchio tolto, card dal motore, T2g.
>   - Test: T1b, T1c, T1d e due helper (+219).
>   - Doc EN: il paragrafo di T3b.
>   - Questo piano.
> - **Prima del checkpoint**:
>   - Il commento sopra i test di T1d diceva «as the Brokers page asks», ed era sbagliato (§15 T1d/T2g, «Portata»).
>   - L'ha corretto il `test-author` (`t1d-comment-fix`), toccando solo il commento (`:493-499`). Poi py_compile, ruff e black puliti.
>   - `services roi-fifo-utils` → **588 passed** sui byte del checkpoint (`/tmp/libreFolio_l41_t5b_roi.log`).
>   - Gli altri gate di T2g restano validi, perché dopo non è cambiato codice.
>   - `git diff --check` pulito.
>   - Scansione privacy pulita, salvo due falsi positivi: `@pytest.mark` e il nome di questo piano.
> - **⚠️ Fuori pista: regola nuova sul target.** È il commit `789c18582` (decisione 10, «One home for financial math», 2026-10-11), arrivato durante H. Il punto 4 chiede, prima di chiudere, di cercare le copie di ciò che si è cambiato. Letto dall'oggetto del commit, perché la worktree è a `b20eac991`. Esito:
>   - **Capitale del broker**: l'inventario di §16 resta completo. Da `d59762e0a` a `c0d933abf`, in `backend/app` cambia solo il motore del checkpoint 1, e il frontend solo il PAC e `formatPercent`.
>   - **Valore in viaggio**: nessuna copia. Fuori dal motore lo si legge soltanto:
>     - riepilogo e storia (`portfolio_service.py:997-999`, `:1226-1228`, `:1382-1388`);
>     - l'avviso del rischio (`risk/service.py:563`);
>     - la custodia `IN_TRANSIT` dei lotti FIFO, che è un'altra cosa.
>   - **Guadagno della card**: si calcola solo in `get_summary` (`:989-1001`), dal capitale del motore. Il frontend lo legge e basta.
>   - **MV della card**: legge le posizioni del motore (`position_states_end`, `:835`, `:879-881`), oltre la soglia di polvere. Non è una copia.
>   - **Copie che restano per la decisione 10**: la cassa della card e i totali del periodo sono un giro sulle transazioni fuori dal motore (`:759-813`). Sono i punti di §16 per F (T7), e le tiene il disegno rivisto di T2f (§16.2, B4).
> - **Debito di traduzione per M**: il paragrafo di T3b manca in IT, FR ed ES. Con il validatore di `b20eac991`, errori e avvisi salgono da 126/195 a 129/198. Il validatore cambia nel treno 33, quindi la misura va rifatta sulla revisione combinata.
> - **CHANGELOG di H**: la riga Fixed proposta in §12. T2g non ne ha.
> - Porta 6157 libera.
> - Messaggi proposti: `/tmp/libreFolio_commit_i_l41h_C1.txt`, `_C2.txt`, `_C3.txt`.
> - **Nel target** (2026-10-11): `801b4a168`, `144c9db27`, `fb954577f`, fusi come `8a546c046` (treno 35). La worktree è poi avanzata a `251067435` (treno 36).

### T7 — Analisi di F ✅ (2026-10-11)

> **Note implementazione**:
> - Solo lettura: nessun file di codice né test toccato, nessun comando nella corsia. Base `251067435`, codice identico a `43d92ed23`, dove ogni ancora è stata riverificata.
> - Il risultato è in §17: il modulo, le chiamate, la guardia, la collocazione F/U dei reperti di T, i passi, la stima (4–5 giornate; 4½–6 con la voce del waterfall) e le decisioni chieste.
> - Corretti in §16 il punto 11 (KpiSection calcola) e la stima dell'opzione F (→ §17.8). Ancore di §14 riallineate, nuove B13–B16.
>
> **⚠️ Fuori pista**:
> - Le ancore di §14 erano di `d59762e0a`: B4, B8, B9 e B11 si erano spostate di decine di righe. Riallineate.
> - Il piano di T (`43_financialMathHome/`) non è nella base. Le U-n le leggo dall'indice (`BACKLOG_POST_1.2.md:98-108`) e dal messaggio del coordinatore: la corrispondenza va riconciliata con T (§17.11, punto 6).
> - B13: gli accumulatori del motore sono morti in produzione, ma non per i test (§14). Vanno portati, non cancellati.
> - Le tre storie sono pubbliche, con circa 30 chiamate dirette nei test (`test_portfolio_service.py:743-3660`, `test_acquisition_funding.py:1147-1149`) senza un run del motore. Per questo il modulo si chiama anche da solo (§17.4).
> - Per una coppia inversa, il motore moltiplica per il cambio unitario e `convert_bulk` divide l'importo: differiscono all'ultima cifra. Ogni vista tiene quindi l'aritmetica di oggi del suo consumatore (§17.7).
> - Treno 36: la regola nuova sull'indice post-1.2 (§0); il passo T8 e la riga di §11.

### F-0 — Rossi e golden della guardia, prima del codice ✅ (2026-10-11)

> **Note implementazione** (fase 1):
> - Base `251067435`, worktree pulita salvo il piano, porta 6157 libera. Contratto dei test in un file di sessione (API del modulo, regola FXR, scenari, guardia): il `test-author` l'ha seguito in due fasi.
> - Fase 1 via `test-author`, senza importare il modulo che non esiste ancora:
>   - **(c) la guardia EUR**: `test_services/test_financial/test_native_cash_guard.py`, golden `backend/test_scripts/fixtures/native_cash_guard/eur_only_golden.json` (14 397 righe). Scenario 2091 con tre broker (A 100%, B 50%, C solo visto), un titolo EUR con prezzi, uno senza fornitore, un ETF in IDR comprato in EUR, cambi EUR/IDR anche in giorni senza movimenti (le trappole: una valuta tenuta solo come titolo non deve dare giorni di rivalutazione), una riga a zero, le due coppie collegate, un deposito dopo le finestre. Due finestre; per ognuna il report completo, `get_summary` con le card, gli 8 getter e `calculate()` (lista chiusa dei campi, più `end_state` coi 10 campi di oggi). Lo scenario si costruisce due volte, per due utenti: le due copie etichettate devono coincidere fra loro e col golden;
>   - **(d) T1c**: un metodo nuovo in `test_portfolio_service.py` (`:493-551`): la testata = Σ card, con la cassa CNY in viaggio;
>   - **(e) gli esponenti EUR**: `test_portfolio_engine/test_eur_cash_exponents.py`, 4 test che fissano con `str()` le cifre del builder di oggi (valori da un oracolo sul codice di oggi).
> - Corsia 6157, un comando alla volta (log in `/tmp/libreFolio_l41_f0_*.log`):
>   - `LIBREFOLIO_REGEN_NATIVE_CASH_GUARD=1 … services roi-fifo-utils native_cash_guard` → 1 skipped, «golden regenerated» (l'autoverifica delle due copie passa prima della scrittura);
>   - lo stesso senza la variabile, due volte (con e senza `--fresh-run`) → 1 passed, 1 passed;
>   - `… services roi-fifo-utils eur_cash_exponents` → 4 passed;
>   - `… services roi-fifo-utils test_summary_with_breakdown_foreign_cash_in_transit_headline_equals_sum_of_cards` → **rosso atteso**: 12 righe di testata, nessuna di card. Al 14/01 la testata dice 825 / 25 / 350 contro 950 / 150 / 475; al 20/01 850 / 50 / 850 contro 1200 / 400 / 1200. Le card sono già giuste (H).
> - Controllo del golden: nessun id grezzo, il deposito del 31/01 non entra; il capitale della card B, 1660.40 = 1000 + 400 + 2 × 130.20, prende il prezzo implicito della vendita del 07/01 all'arrivo dei titoli.
> - Prefisso dei comandi: `PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py test --test-port 6157 --data-dir /tmp/librefolio-r2-i-charts`.
>
> **⚠️ Fuori pista** (fase 1 e disegno fissato in F-0):
> - **FXR solo nei giorni di cambio nuovo.** `fxr = value_at(giorno)[b] − cassa_cumulata[b]` per ogni broker con cassa estera, dopo i delta del giorno e prima delle regole dei pool; nel frame sui giorni `rate_change_days(frame_start, date_to)`, aggiunti ai giorni sporchi; nel pre-frame su `rate_change_days(None, frame_start − 1)`. Motivo: il builder somma `|importo|×u×quota`, `value_at` calcola `(importo×quota)×u`; con i cambi inversi a 28 cifre differiscono di un'unità all'ultima cifra. Nei giorni piatti lo zero è esatto, nei giorni di cambio la deriva si corregge da sola. I giorni sporchi in più (cambio nuovo senza movimenti) sono innocui: ricalcolano un giorno identico.
> - **La regola di copertura**: `R[b] += fxr; se R[b] < 0: K[b] += R[b]; R[b] = 0`, la stessa di FEE/TAX nel frame e della perdita alla vendita. K + R resta uguale alla cassa: niente scala del 4g.
> - **Righe a zero e righe mancanti**: le righe estere a zero non si chiedono a `convert_bulk`, quindi non risultano mai mancanti (oggi il motore le salta già). Una riga senza cambio esce da valore e flussi e va nelle coppie mancanti (politica (a)): vale anche per la cassa della card in F-3.
> - **I cambi unitari per valuta**: dal primo movimento non nullo della valuta fino a `rates_until` (il motore passa `actual_to`, il servizio la data di valutazione). Il motore carica anche le transazioni dopo l'orizzonte: i movimenti si filtrano a `≤ actual_to`.
> - **D-β**: `native_cash` è un argomento obbligatorio del builder; 19 punti nei test lo devono passare in F-2 (un helper `_engine_native_cash.py` sul modello di `_engine_average_costs.py`).
> - **La guardia ha la sua coppia, EUR/IDR**, con i giorni trappola; i test di (b) usano USD con cambi esatti per giorno.
> - **Due fasi di dispatch** più (e): prima ciò che non importa il modulo (guardia, T1c, esponenti), poi i test del modulo e degli scenari, rossi in raccolta fino a F-1.
> - **Scenari aggiunti in F-0**: B11 (FX_CONVERSION nello stesso broker), B12 (perdita di cambio che svuota R e scende in K), B3w (finestra che parte durante il viaggio).
> - **`model_dump(mode="json")` perde l'esponente** (SafeDecimal scrive `format(v, "f")`): la guardia scarica in modo python e scrive ogni Decimal con `str()`.
> - **Cache svuotate prima di ogni chiamata**, non solo all'inizio: altrimenti il `calculate()` diretto di W2 si servirebbe dal blob dei getter.
> - **Righe tenute vive fino alla fine**: la mappa d'identità di SQLAlchemy le tiene deboli, e una riga ricaricata torna alla scala della colonna (`10000.000000` invece di `10000.00`).
> - **MWRR**: viene da un risolutore float; un aggiornamento di scipy potrebbe muoverne l'ultima cifra. Il diff resterebbe nei campi `mwrr_*`, da rivedere prima di rigenerare.
> - **Il treno 37** ha portato `dev_release2` a `41ddc61cb`; tocca solo `test_lots_analysis_service.py`, fuori da F.
> - **Osservazioni fuori portata, non corrette**: il commento di `portfolio_engine.py:592-593` sulla scomposizione della cassa è vecchio (la regola vera è a `:1219-1239`); il testo del runner a `_backend_services.py:625` cita ancora vnext (fuori dalla concessione `:571-574`, lo propongo al coordinatore); la fixture `test_asset` di `test_portfolio_service.py:83-87` passa `ticker=` e `type=`, che non sono colonne di `Asset` (`identifier_ticker`, `asset_type`).
> - **T1c resta fuori dal checkpoint F-C1**: diventa verde solo in F-3, quindi `test_portfolio_service.py` entra in F-C2. *(Superato in F-2: T1c è verde già col motore, vedi «F-2» qui sotto.)*
>
> **⚠️ Fuori pista** (ripresa dopo il guasto di rete, 2026-10-11):
> - Controllo alla ripresa: HEAD `251067435`; le modifiche della worktree coincidono con la fase 1 (piano, T1c in `test_portfolio_service.py`, guardia + golden, esponenti); niente in ascolto su 6157/6167, nessun pytest o uvicorn rimasto; il DB della corsia è fermo alla fine del run di T1c; i 5 log della fase 1 sono completi. **Nessun comando era a metà, nessuna riesecuzione.**
> - La fase 2 non era partita. Il `test-author` della fase 1 era sincrono, quindi non riceve messaggi: la fase 2 va a un `test-author` nuovo, in background, con lo stesso contratto.
> - Il target è a `b578f4fec` (treni 37–38, nessun file di F): il riallineamento della base si fa al checkpoint dopo F-2.
>
> **Note implementazione** (fase 2):
> - Via un `test-author` in background, che importa il modulo che ancora non esiste:
>   - **l'helper** `test_services/_engine_native_cash.py` (88 righe), sul modello di `_engine_average_costs.py`: i movimenti di `calculate()` (≤ `date_to`, alla quota del classificatore), le conversioni dalla mappa dei cambi del builder, solo il giorno esatto;
>   - **(a) il modulo**: `test_services/test_financial_math/test_native_cash.py`, 49 funzioni, 88 casi. La quota effettiva; il movimento da una transazione; il contratto con `convert_bulk` (una chiamata sola, `raise_on_error=False`, prima gli importi poi i cambi unitari, nessuna richiesta per le righe a zero o in valuta di report); `value_at`; i giorni di cambio nuovo; saldi, flussi, somme per data e coppie mancanti. In più i 5 port degli accumulatori di B13 che F-2 toglie (vnext e `test_signed_income.py`). Gli esponenti si fissano con `str()`;
>   - **(b) gli scenari del motore**: `test_portfolio_engine/test_foreign_cash_revaluation.py`, 14 test (B1–B12, B3w, B4v); l'invariante G1a ogni giorno di ogni run; B3w e B10 confrontano la finestra col run intero.
> - Lint: `py_compile`, `ruff check` e `black --check` puliti sui 3 file.
> - Rossi provati sulla 6157, un comando alla volta:
>   - `… services financial-math` → `ModuleNotFoundError` in raccolta (`/tmp/libreFolio_l41_f0p2_red_fm.log`);
>   - `… services roi-fifo-utils foreign_cash_revaluation` → `ModuleNotFoundError` in raccolta, attraverso l'helper; 594 deselezionati (`/tmp/libreFolio_l41_f0p2_red_fcr.log`).
> - Dopo F-1 (b) resta rosso con `TypeError` (l'argomento `native_cash` del builder) fino a F-2.
>
> **⚠️ Fuori pista** (fase 2):
> - **Un errore nella spec, corretto prima del commit dei test**: −400.00 × 0.500000 = `-200.00000000` (esponente −2 −6 = −8), non `-200.0000000`. Ho chiesto al `test-author` di ricalcolare ogni cifra fissata con `str()` invece di copiarla: nessun'altra cambiava.
> - **Il registro dei broker di B non ha la chiave prima dell'arrivo** (B2, B3, B3w): `value_at(giorno)` elenca solo i broker con un movimento contato fino a quel giorno. Nel motore un broker senza chiave si salta (fxr 0): prima dell'arrivo la sua cassa è zero anche nel registro del builder.
> - **Le due cartelle intere ferme fino a F-1**: un errore di raccolta ferma tutto `services financial-math` e tutto `services roi-fifo-utils`, anche con `-k` (guardia, esponenti e T1c compresi). Si sbloccano con F-1.
> - **Ordine degli import**: senza il modulo, ruff mette il suo import fra i pacchetti esterni. Dopo F-1, `ruff check --fix` lo riporta al suo posto in `_engine_native_cash.py` e `test_native_cash.py` (I001, solo l'ordine).

### F-1 — Il modulo `financial_math/native_cash.py` ✅ (2026-10-11)

> **Note implementazione**:
> - `backend/app/services/financial_math/native_cash.py` (≈470 righe), piatto accanto a `average_cost.py` (D-4). Importa solo `Currency` e `convert_bulk`, dai moduli che li definiscono:
>   - `effective_share(role, share_percentage)`: OWNER → la quota (1 se None), altrimenti 1. È la regola che F-3 toglie dai 3 giri del servizio (O2);
>   - `CashMovement` e `cash_movement_from_transaction(tx, share=…)`: una riga per transazione con importo, None senza importo;
>   - `NativeCash`: i saldi per broker e valuta; `value_at(giorno)` al cambio unitario del giorno, con l'ultimo cambio noto prima; `foreign_cash_broker_ids`; `rate_change_days(da, a)`; `balances`, `flows`, `sums_by_date`, `missing_conversions`;
>   - `compute_native_cash(sessione, movimenti, report_currency=…, rates_until=…)`: **una sola** chiamata a `convert_bulk` (gli importi, poi un'unità di ogni valuta per giorno), nessuna se la cassa è tutta nella valuta di report.
> - `financial_math/__init__.py`: la riga del modulo nella docstring (contratto §0, punto 3).
> - Lint: `ruff check`, `black --check` e `py_compile` puliti.
> - Corsia 6157, un comando alla volta:
>   - `… services financial-math` → **127 passed** (88 di `native_cash` più `average_cost`) (`/tmp/libreFolio_l41_f1_fm.log`);
>   - `… services roi-fifo-utils foreign_cash_revaluation` → **14 failed, 594 deselected**, tutti `TypeError: DailyStateBuilder.__init__() got an unexpected keyword argument 'native_cash'` (`/tmp/libreFolio_l41_f1_fcr_red.log`). È il rosso atteso fino a F-2.
>
> **⚠️ Fuori pista**:
> - **C901 su `__post_init__`** (complessità 14 > 10): la bozza lo faceva tutto in un metodo solo. L'ho diviso in 4 funzioni del modulo, con la stessa logica: `_running_balances` (ordinamento stabile per data), `_first_dates`, `_rate_series`, `_change_days` (il primo giorno di ogni serie conta; solo le valute contate in valuta estera). Il verde dei 127 lo conferma.
> - **L'ordine degli import serviva, ma la cache di ruff lo nascondeva**: subito dopo F-1 `ruff check` era pulito sui file di test, perché la cache di ruff non vede che il modulo è nato. Con `--no-cache` l'I001 compare in `_engine_native_cash.py` e `test_native_cash.py`. L'ho corretto con `ruff check --no-cache --fix --select I001` (solo l'ordine), poi `black`. Regola: dopo aver creato un modulo, i controlli sull'ordine degli import si fanno con `--no-cache`.

### F-2 — Il motore ✅ (2026-10-11)

> **Note implementazione**:
> - `backend/app/services/portfolio_engine.py` (+68 / −38):
>   - `DailyStateBuilder` riceve `native_cash: NativeCash`, argomento obbligatorio (D-β), e lo rimette nel risultato (`native_cash: NativeCash | None`, None sui ritorni anticipati);
>   - `_revalue_foreign_cash(giorno, cassa, K, R)`: per ogni broker con cassa estera, `fxr = value_at(giorno)[b] − cassa[b]`, alla cassa e a R; se R < 0, K += R e R = 0 (k2). Il capitale (ECF) non si muove;
>   - pre-frame: i giorni `rate_change_days(None, frame_start − 1)` entrano nel replay, con la rivalutazione dopo i delta di cassa ed ECF del giorno e prima delle regole dei pool;
>   - frame: i giorni `rate_change_days(frame_start, date_to)` diventano sporchi, con la rivalutazione subito dopo il 4a;
>   - `calculate()`: il passo 10c chiama `compute_native_cash` sui movimenti classificati fino a `actual_to`, alla quota del classificatore. Sta dopo 10a e 10b, prima dell'11;
>   - via gli accumulatori di B13 (`per_realized`, `per_income`, `per_fees_taxes`, `unalloc_income`, `unalloc_fees`): nessun lettore in `backend/app` né in `scripts` (nel servizio restano solo variabili locali con lo stesso nome). `realized_sales` resta;
>   - `broker_shares` passa da `effective_share`, la regola del modulo (O2); via l'import di `UserRole`.
> - **Allineamento dei test**, via `test-author`, in 15 file. Nessun valore atteso cambiato, salvo i port:
>   - l'argomento `native_cash=` a ogni costruttore del builder, con l'helper `_engine_native_cash.py`: vnext (`_build` e i 2 punti in linea, con `classified_txs=[]`), `test_brim_providers.py` (import locale), `test_signed_income.py`, `test_resolver_valuation_tier.py`, `test_acquisition_funding.py`, `test_performance_inputs_inkind.py`, `test_broker_internal_flows.py`, `test_daily_state_builder.py`, `test_pnl_candles.py`, `test_broker_pnl_contributions.py`, `test_cash_decomposition.py`, `test_eur_cash_exponents.py`;
>   - vnext: `TestRealizedSales.test_sell_realized` legge `realized_sales` (750 / 500 / 250); `test_income_attributed` e `test_unallocated_fees` tolti, perché portati in `test_native_cash.py::TestFlowsPortedFromTheEngine`. Quindi 42 → 40;
>   - `test_signed_income.py`: le asserzioni di B13 diventano commenti che citano i port;
>   - via i paragrafi «Red-first» ormai superati, dalle docstring di `_engine_native_cash.py` e `test_native_cash.py`;
>   - case 3 di `test_broker_internal_flows.py`: D2 ora fissato (A 900 / 10, B 0 / 0; aggregato 900 / 10);
>   - T1c: la docstring passa al passato («Before F, the headline kept…»), nessuna asserzione toccata.
> - Lint: `ruff check --no-cache`, `black --check` e `py_compile` puliti su motore e test.
> - Corsia 6157, un comando alla volta (prefisso di F-0), tutti con exit 0:
>   - `services roi-fifo-utils native_cash_guard` → 1 passed: la guardia EUR, byte per byte (`/tmp/libreFolio_l41_f2_guard.log`);
>   - `… eur_cash_exponents` → 4 passed (`_exp.log`);
>   - `… foreign_cash_revaluation` → **14 passed**, dal rosso di F-1 (`_fcr.log`);
>   - `services portfolio-engine` → 40 passed (`_pe.log`);
>   - `services financial-math` → 127 passed (`_fm.log`);
>   - `services roi-fifo-utils` → **608 passed**, prima e dopo il ritocco del case 3 (`_rfu.log`, `_rfu2.log`); `… test_case_03` → 1 passed;
>   - i consumatori del motore fuori da `test_financial/`: `external brim-providers` 705 passed e 1 skipped (lo stesso di prima, Windows-1252 su DEGIRO); `services risk-asset-set` 51; `services portfolio-allocation-source` 89; `services settings` 23.
>
> **⚠️ Fuori pista**:
> - **T1c è verde già a F-2, non a F-3.** La testata di `get_summary` legge lo stato del motore: NAV e cassa a `portfolio_service.py:717-719`, capitale e P&L a `:1097-1099`. Il motore ora rivaluta la cassa, e le card erano già giuste (H).
>   - Quindi la nota di F-0 «T1c resta fuori da F-C1» è superata: propongo `test_portfolio_service.py` già in F-C1.
>   - F-3 resta la migrazione dei giri del servizio (G2–G4, la card, le quote) sul modulo. I suoi rossi si ricavano lì, dove il comportamento cambia: la politica (a) sui giri G3 e G4.
> - **Il valore in viaggio segue il cambio.** Un giorno di cambio nuovo è sporco, quindi quel giorno si rivaluta anche la cassa estera in viaggio. Nel case 3, P_A(d2) = +10, come nella tabella del lotto; prima era 0, la copia di d1 (nota di T1, «P a d2 non è fissato»). F-2 chiude così la metà «cassa» di B11 (§14); la metà «titoli» resta in U. D2 ora è fissato.
> - **Il passo 10c dopo 10b.** La prima stesura lo metteva subito dopo 10a (`average_costs`), prima di 10b. L'ho spostato dopo 10b, per avere l'ordine 10a, 10b, 10c, 11. Nessun effetto: 10c non legge né 10a né 10b.
> - **`test_eur_cash_exponents.py` era rimasto senza l'argomento**: il `test-author` l'ha aggiunto in `_builder_kwargs`, nella seconda passata.
> - **Un FXR non asserito**: `test_daily_state_builder.py:663` (`test_buy_paid_in_another_currency…`) registra ora +40 il 2025-01-03 (USD −100, cambio da .9 a .5: la cassa passa da −90 a −50). Il test fissa altro e resta verde. Tutti gli altri test del builder hanno FXR 0.
> - **`value_at` e la politica (a): l'eccezione non si raggiunge, a una condizione.** Il registro conta solo i movimenti convertiti alla loro data. Una riga senza cambio non entra né nel valore né nel replay del motore (`portfolio_engine.py:736-745`, stessi movimenti e stessa quota), e va nelle coppie mancanti.
>   - `value_at` solleva `ValueError` su un saldo estero non nullo senza un cambio unitario alla data o prima. È una guardia d'invariante.
>   - Da `compute_native_cash` non si arriva lì: `convert_bulk` (`fx.py:1240`) cerca il cambio per coppia e data, con backward-fill illimitato e senza guardare l'importo. Un movimento contato alla data d implica quindi il cambio unitario a d, e la richiesta (valuta, d) c'è sempre, perché copre ogni giorno dal primo movimento a `rates_until`.
>   - **La condizione**: `rates_until` ≥ la data di ogni movimento passato. Nel motore vale (`rates_until = actual_to`, movimenti ≤ `actual_to`). **Vincolo per F-3**: se il servizio chiama il modulo invece di leggere `native_cash` dal risultato del motore, deve rispettarla.
>   - Una nota di precisione: il motore converte `importo × cambio unitario`, mentre il modulo, per i flussi, converte l'importo direttamente (`importo / cambio` sulle coppie inverse), come facevano i giri del servizio. Le due strade possono differire alla 28ª cifra significativa. La FXR usa solo i cambi unitari, quindi l'eventuale resto finisce nel giorno di cambio e non si vede.
> - **Il target è avanzato a `c7f7b1807`** (treni 39–41: T e M), non più `b578f4fec`. HEAD ne è antenato, e nessuno dei 22 percorsi di F è toccato. Vicini a F:
>   - `schemas/portfolio.py`, solo i lotti FIFO;
>   - i componenti FIFO dell'AI Export, da rileggere per F-AI;
>   - `test_portfolio_api.py`, solo i lotti;
>   - `BACKLOG_POST_1.2.md`, per T8;
>   - le traduzioni di `deposited-capital` e `kpi-cards` (M): F-5 ne cambierà le pagine EN.
>   - Sovrapposizione semantica riverificata sull'albero del target: nessun lettore dei 5 campi tolti dal risultato (`git grep` su `dev_release2`). `lots_analysis_service.py` (T) importa dal motore solo `DerivedViewsBuilder` e `load_configured_fx_pair_sets`, che F-2 non tocca. I test nuovi del target (lotti, FIFO dell'AI Export) non passano dalla cassa estera del motore.

### F-C1 — Checkpoint 3: modulo e motore ✅ (2026-10-11)

> **Note implementazione**:
> - 22 percorsi: 15 modificati e 7 nuovi (il golden conta come un file). `git diff --check` pulito; lint fresco sui 20 file Python (ruff, black, py_compile); tutti i gate di F-2 girati sui blob di oggi.
> - Commit proposti, uno per livello:
>   - C1 `feat(math): add native cash reconstruction`: `financial_math/__init__.py`, `native_cash.py`, `test_native_cash.py`;
>   - C2 `fix(portfolio): revalue foreign cash every day`: il motore, il golden e la guardia, l'helper `_engine_native_cash.py`, i 12 file di test del motore (gli 11 di `test_portfolio_engine/` e vnext), `test_brim_providers.py`, T1c in `test_portfolio_service.py`;
>   - C3 `docs(journal): record lot 41 steps F-0 to F-2`: questo piano.
> - Porte 6157 e 6167 libere; nessun sotto-agente al lavoro.
> - **Verificato e committato dal coordinatore** (autorizzato dal developer a commit e merge locali; il push resta suo): `36b181836` (C1), `aa6b6077a` (C2), `384253663` (C3), albero `fb092cac7074`, uguale alla prova.
> - **Base riallineata**: il coordinatore ha fuso `dev_release2` (`c7f7b1807`, treno 41: T B3b, PL3, FE1, etichette, C-50; M lotti 14–17; P) nel ramo. Il merge `daee275fe` ha albero `02f1370dcd1e` e non ha avuto conflitti. I 22 blob di F sono intatti: verificati contro il manifesto, 22 su 22.
> - **La revisione combinata è verde** sulla 6157, un comando alla volta, tutti con exit 0:
>   - `services financial-math` 127 (`/tmp/libreFolio_l41_f3pre_fm.log`);
>   - `services portfolio-engine` 40 (`_pe.log`);
>   - `services roi-fifo-utils` **631**, cioè 608 più i test nuovi di T in `test_financial/` (`_rfu.log`);
>   - `services ai-export` 1002 (`_aie.log`);
>   - `services lots-analysis-pure` 121 (`_lap.log`);
>   - `api portfolio` 51 (`_apip.log`).
>   Nessun attrito con T. La porta 6157 è libera dopo l'ultimo comando.

### F-3 — Il servizio ✅ (2026-10-12)

> **Progetto**, verificato riga per riga su `daee275fe`:
> - **Una sola sorgente**: `nc = engine_result.native_cash`, oppure un `NativeCash` vuoto sui ritorni anticipati del motore (`portfolio_engine.py:2502`, `:2522`).
> - **Gli stessi movimenti dei giri di oggi.**
>   - Il motore prende gli accessi dell'utente filtrati per `broker_ids`, come `_get_user_broker_access` (`portfolio_service.py:482-492`).
>   - Il classificatore (`portfolio_engine.py:268-360`) mette in `classified` ogni transazione dello scope una volta sola, alla quota del suo broker (`effective_share`).
>   - Il passo 10c (`:2708-2714`) tiene `tx.date <= actual_to`, con `actual_to = date_to or today` (`:2566`): è la `valuation_date` del riepilogo.
>   - La cache a blob rende il risultato intero, `native_cash` compreso (`:2612`).
>   - `convert_bulk` (`fx.py:1240-1425`) dà a ogni voce l'ultimo cambio ≤ la sua data, qualunque sia il resto della richiesta: una chiamata sola rende gli stessi valori delle chiamate una per una.
> - **`get_summary`**:
>   - del giro per accesso (G2, `portfolio_service.py:750-813`) restano i nomi, `broker_txns` e il giro dei lotti;
>   - periodo `nc.flows(date_from, valuation_date)`, vita intera `nc.flows(None, valuation_date)`. Depositi e prelievi da `absolute_by_type`; il reddito è `DIVIDEND + INTEREST` col segno; commissioni e tasse in assoluto. `income_by_pos` e `fees_taxes_by_pos` vengono dai flussi della vita intera;
>   - coppie mancanti da `nc.missing_conversions(None, valuation_date)`;
>   - card (`:977-1012`): `cash_total = nc.value_at(valuation_date)[b]`, oppure il saldo in valuta base se il broker ha solo righe a zero; `cash_balances` da `nc.balances(valuation_date)`; NAV = valore di mercato + cassa + in viaggio;
>   - testata: `cash_balances` è la somma delle liste delle card, nell'ordine degli accessi.
> - **Le tre storie**, con `_signed_transaction_sums_by_date(..., native_cash=None)`:
>   - da `get_report` ricevono il registro del run (`_precomputed_native_cash`);
>   - chiamate da sole lo costruiscono con `compute_native_cash` all'orizzonte del motore, `date_to or today`. Così vale il vincolo di `value_at` (`rates_until` ≥ ogni data);
>   - poi `sums_by_date` e `missing_conversions` sui tipi richiesti.
> - **I contributi**: `nc.flows(date_from, effective_end)` al posto di G4 (`:1774-1808`). Le quantità restano col loro `date_to` (U5). Gli unallocati vanno riordinati come gli accessi, perché l'iterazione del set di oggi (`:2023`) resti la stessa.
> - **La quota** passa da `effective_share` anche nei contributi (O2 chiuso), e l'import di `UserRole` sparisce. `convert_bulk` resta, per `_convert_to_base`.
> - **Byte per byte con la sola valuta base.** Le somme Decimal sono esatte in qualunque ordine. L'esponente di una somma è il minimo dei suoi addendi, e le righe del DB hanno tutte esponente −6: togliere le righe a zero da `value_at` non lo cambia. Un broker con sole righe a zero passa dal ripiego; uno senza righe dà `Decimal("0")`. L'ordine delle valute per broker è quello dei movimenti, `(data, id)`, come oggi.
>
> **Cambiamenti attesi**, fuori dalla guardia EUR e approvati con la politica (a) (§17):
> - una riga estera senza cambio alla sua data conta 0 nella cassa della card e nel suo NAV, ed è ancora elencata in nativo. Quindi card = motore, e testata = Σ card;
> - la testata `cash_balances` elenca anche le valute senza cambio, come le card;
> - una riga estera a zero non chiede più un cambio, quindi non risulta mancante. Per una posizione senza prezzo con una sola riga così, `period_pnl` dei contributi passa da None a 0;
> - la card non aggiunge più la coppia mancante datata `valuation_date`: la coppia resta con le date dei movimenti;
> - **B12** chiuso per le storie e per i flussi dei contributi: chiamati senza `date_to`, si fermano a oggi. In produzione nessun effetto, perché `get_report` passa sempre `effective_date_to` (`:2120`, `:2338-2372`);
> - **B14** chiuso: i flussi dei contributi e del riepilogo vengono dalle stesse righe, con le stesse coppie mancanti. Lo schema dei contributi non ha un campo per le coppie: la segnalazione resta nel riepilogo;
> - sulle coppie inverse la cassa della card passa da `saldo / cambio` a `saldo × (1 / cambio)`: al più la 28ª cifra.
>
> **Rossi e fermi**, via `test-author`, in un file nuovo di `test_financial/`, raccolto da `roi-fifo-utils` senza registrazione:
> 1. rosso, politica (a) sulla card: SBD senza cambio alla data del deposito → `cash_total`, NAV e guadagno della card uguali al motore;
> 2. rosso: una valuta senza nessun cambio → la testata `cash_balances` la elenca come la card, e la coppia mancante ha solo la data del movimento;
> 3. rosso, B12: le tre storie e i contributi chiamati senza `date_to` ignorano le righe dopo oggi;
> 4. fermo, B14: il reddito dei contributi con una coppia mancante è uguale a `period_income` del riepilogo;
> 5. fermo: le storie di `get_report` sono uguali alle chiamate da sole;
> 6. fermo: un broker EUR con sole righe a zero ha la cassa 0 e la lista `EUR 0`.
>
> **Note implementazione** (2026-10-12):
> - `portfolio_service.py`, +96 −184. La bozza l'ho scritta fuori dalla worktree e l'ho copiata solo dopo aver girato i rossi sul codice di prima. Prima della copia lo sha256 del file era uguale a quello della copia intatta.
>   - Helper `_engine_native_cash(engine_result, report_currency)`: il registro del run, oppure uno vuoto sui ritorni anticipati.
>   - `get_summary`:
>     - G2 → `flows` del periodo e della vita intera;
>     - le coppie mancanti → `missing_conversions`;
>     - la card → `value_at` / `balances`;
>     - la testata `cash_balances` = Σ delle liste delle card, nell'ordine degli accessi.
>   - `_signed_transaction_sums_by_date(..., native_cash=None)`: usa il registro ricevuto, oppure lo costruisce con `compute_native_cash(rates_until=date_to or today)`; poi `sums_by_date` e `missing_conversions`. Le tre storie hanno `_precomputed_native_cash`, e `get_report` passa `engine_result.native_cash`.
>   - I contributi:
>     - `flows(date_from, effective_end)`, al posto delle 4 mappe e del giro per riga;
>     - gli unallocati riordinati come gli accessi;
>     - la quota da `effective_share` (O2).
>   - Tolti i 4 import, le costanti morte e `UserRole`.
> - **Test** (`test-author`): `test_portfolio_service_native_cash.py`, 9 test, raccolti da `roi-fifo-utils` senza registrazione. Sono 6 rossi (1, 2, 3a–d) e 3 fermi (4, 5, 6). Valute SBD, VUV, TOP e WST, anno 2039, righe B12 a ±5 giorni da oggi.
> - **Comandi ed evidenza** (corsia 6157, uno alla volta, tutti con exit 0 a parte il rosso voluto):
>   - **Rossi sul codice di prima**: `… services roi-fifo-utils portfolio_service_native_cash` → **6 failed, 3 passed** (`/tmp/libreFolio_l41_f3_red.log`). Ognuno è rosso per la ragione scritta:
>     - test 1: card 1090 / 1090 / 90 / 0,09, e Σ card ≠ testata;
>     - test 2: testata `[EUR 1000]` senza VUV, e VUV/EUR datata `[02-02, 02-05]`;
>     - 3a–c: un punto in più a t+5;
>     - 3d: 50 / 10.
>   - **Dopo la copia**: 9 passed (`_green.log`).
>   - **La guardia** `native_cash_guard`: 1 passed, byte per byte (`_guard.log`). Copre `get_report`, `get_summary` con le card e gli 8 getter delle serie.
>   - **Gate**:
>     - `services roi-fifo-utils` **640** (631 + 9) (`_roi.log`);
>     - `portfolio-engine` 40 (`_engine.log`);
>     - `financial-math` 127 (`_fmath.log`);
>     - `ai-export` 1002 (`_aiexport.log`);
>     - `lots-analysis-pure` 121 (`_lots.log`);
>     - `api portfolio` 51 (`_api.log`).
>   - Porta 6157 libera dopo l'ultimo comando.
>   - **Lint**: ruff `--no-cache --config pyproject.toml`, black `--check` e py_compile puliti su servizio e test.
> - **Non girati, col perché**:
>   - `services risk-all`: il rischio legge da `get_report` solo le posizioni, `net_worth` / `cash_total` / `in_transit` del motore e la storia TWRR, e F-3 non tocca nessuno dei tre;
>   - `services broker`: usa `BrokerService`, non questo servizio.
>
> **⚠️ Fuori pista**:
> - **I rossi 1 e 2 sono rossi solo in parte**, come previsto in F-2 (T1c già verde col motore).
>   - Nel test 1 la testata e la data mancante `[01-01]` erano già giuste: il rosso viene dalla card.
>   - Nel test 2 i valori della card erano già giusti: il rosso viene dalla testata e dalla data in più.
> - **Due scostamenti del `test-author` dalla specifica**, accettati.
>   - Test 5: le storie dei depositi hanno almeno 1 punto, non 2. Il deposito di B cade sull'inizio, e l'inizio è escluso: `(start, end]` è la convenzione dei flussi di periodo da G1c (le righe del primo giorno stanno nel NAV d'apertura), già scritta nella docstring di prima. F-3 non la cambia: è un'osservazione, non un buco.
>   - Test 4: TOP/EUR è controllata per contenimento, perché prima di F-3 la card aggiungeva la data di valutazione. La data esatta la fissa il test 2.

### F-W — «FX on cash» nei contributi ✅ (2026-10-12)

> **Progetto** (forma minima, §0 e §17.8):
> - **Nel modulo**, `NativeCash.exchange_results(date_from, date_to)` calcola, per ogni broker di `foreign_cash_broker_ids` in ordine crescente:
>   - il valore delle sue valute estere alla chiusura, meno quello all'apertura, ognuno al cambio del suo giorno;
>   - meno i movimenti esteri contati in `(date_from, date_to]`, convertiti alla loro data e moltiplicati per la quota.
>
>   La valuta del report non ha risultato. Una finestra vuota non elenca nessuno; un risultato zero resta in lista.
> - **Nel servizio**, in `get_positions_contribution`, quando `period_other_result` esiste:
>   - una riga `OtherPeriodEffect("FX on cash", "Other", risultato, broker)` per ogni broker, nell'ordine degli accessi;
>   - il residuo scende della stessa cifra.
> - **Restano come sono**: il riepilogo, lo schema, l'API (niente `api sync`) e KpiSection.
>
> **Note implementazione** (2026-10-12):
> - **`financial_math/native_cash.py`**, +53 −8:
>   - `CONVERSION_DUST = Decimal("1e-9")` (:53), con il suo perché;
>   - `_foreign_value(balance, currency, day)` (:222): il saldo estero al cambio del giorno. Vale None se il saldo è assente o zero; se manca il cambio per un saldo diverso da zero, ValueError.
>     - `value_at` lo usa con le stesse operazioni e lo stesso messaggio, quindi l'uscita è identica.
>     - Il saldo conta solo i movimenti convertiti, quindi `exchange_results` solleva soltanto dove già solleverebbe `value_at` (il contratto `rates_until` di F-1 e F-2): nessun nuovo modo di fallire per la vista Performance;
>   - `exchange_results` (:237-268), citato anche nella docstring del modulo.
> - **`portfolio_service.py`**:
>   - l'import di `CONVERSION_DUST` (:86) e il registro del run in una variabile locale (:1700);
>   - il blocco del residuo (:1986-2019):
>     - prima le righe FX, nell'ordine degli accessi, saltando quelle con |r| < polvere;
>     - poi il residuo. Con cassa estera nello scope compare solo se |residuo| ≥ polvere, altrimenti vale la regola di prima, `!= 0`;
>   - la docstring del metodo.
> - **Frontend**: una riga di mappatura con `translateOr` in `OtherPeriodEffectsTable.svelte` (`descriptionLabel`, :75) e una in `PerformanceChart.svelte` (`otherEffectDescriptionLabel`, :291).
> - **i18n**: `dashboard.fxOnCash` nei 4 cataloghi via `dev.py i18n add`, una riga per file (:1712), in coda al namespace `dashboard`:
>   - EN «FX on cash»;
>   - IT «Effetto cambio sulla liquidità»;
>   - FR «Effet de change sur les liquidités»;
>   - ES «Efecto del tipo de cambio sobre el efectivo».
> - **Test** (`test-author`, rossi prima del codice):
>   - `TestExchangeResults`, 48 casi, in `test_native_cash.py` (sezione 11);
>   - `TestFxOnCashContributionRows`, 12 casi, in `test_portfolio_service_native_cash.py`: 10 rossi e 2 fermi, S6 (il viaggio) e S4 col solo broker E. Valute FJD e KMF, anno 2040, un mese per scenario.
> - **Comandi ed evidenza** (corsia 6157, uno alla volta, tutti con exit 0 a parte i rossi voluti):
>   - **Rossi**:
>     - modulo **48 failed, 127 passed** (`/tmp/libreFolio_l41_fw_red_module.log`), tutti AttributeError su `exchange_results` o `CONVERSION_DUST`;
>     - servizio **10 failed, 11 passed** (`_red_service.log`). In ogni rosso del servizio il residuo di oggi è esattamente la cifra FX attesa:
>       - S1 −262,5;
>       - S2 −362,5, −187,5 e −175;
>       - S3 −131,25;
>       - S4 −393,75 = −262,5 − 131,25;
>       - S5 −113,25 = FX −103,25 più lo spread −10.
>   - **Verdi**: modulo 175 (`_green_module.log`), servizio 21 (`_green_service.log`).
>   - **La guardia** `native_cash_guard`: 1 passed, byte per byte (`_gate_guard.log`).
>   - **Gate**:
>     - `roi-fifo-utils` **652** (640 + 12) (`_gate_roi.log`);
>     - `portfolio-engine` 40 (`_gate_engine.log`);
>     - `financial-math` **175** (127 + 48) (`_gate_fm.log`);
>     - `ai-export` 1002 (`_gate_aiexport.log`);
>     - `lots-analysis-pure` 121 (`_gate_lots.log`);
>     - `api portfolio` 51 (`_gate_api.log`).
>   - **Frontend**:
>     - `dev.py front check`: 0 errori, 0 avvisi (`_front_check.log`);
>     - prettier `--check` pulito sui 2 Svelte e sui 4 cataloghi;
>     - `dev.py i18n audit`: 4349 chiavi, tutte complete, 0 inutilizzate (`_i18n_audit.log`).
>   - **Lint** del backend: ruff, black `--check` e py_compile puliti.
>   - La porta 6157 è libera dopo l'ultimo comando.
> - **I consumatori di `other_effects`**, verificati:
>   - `PositionsPanel` e `PerformanceChart.svelte:351-358` mostrano le righe in modo generico;
>   - per l'AI Export, vedi il Fuori pista.
>
> **⚠️ Fuori pista**:
> - **La polvere di conversione.**
>   - Il motore converte col cambio unitario, `importo × r`; per le coppie inverse `convert_bulk` divide, `importo / r`. Le due strade differiscono alla 28ª cifra: 5000 a 1/1,1 dà 4545,454545454545454545454546 contro …545.
>   - Con 1234,56 a 1,1 la polvere non c'è: per questo i test usano 5000.
>   - Da qui `CONVERSION_DUST` e la regola del residuo: con cassa estera nello scope, né la riga FX né il residuo mostrano una cifra sotto 1e-9.
>   - Senza cassa estera resta `!= 0` e non c'è aritmetica nuova: la guardia EUR resta byte per byte.
> - **L'AI Export vede la riga senza codice nuovo.**
>   - `broker.flows_income_costs` (`ai_export/components/broker_financial.py:376`) mappa ogni riga di `other_effects`. Nell'export di un broker la riga «FX on cash» compare da sola, e il residuo scende.
>   - Correggo quindi l'ipotesi di §0, «la cifra resta dentro `period_other_result`». Il campo del riepilogo non cambia, quindi restano come sono:
>     - la riconciliazione (`:405-433`);
>     - l'export del portafoglio (`portfolio_financial.py:401,438`), che tiene solo Income e Cost.
>
>     La lista degli effetti del broker invece mostra la riga. `ai-export`: 1002, verde.
>   - Il nome nell'export (F-AI) diventa una questione di versione e di probe, non di dati. Lo porto al coordinatore.
> - **Due limiti documentati**, che restano nel residuo:
>   1. il risultato di cambio sulla cassa in viaggio (S6: residuo −175, nessuna riga FX);
>   2. lo spread di un FX_CONVERSION sullo stesso broker (S5: −10 resta nel residuo).
>
>   Vanno nel backlog (T8).
> - **L'ordine delle righe degli unallocati è quello del set**, `set(unalloc_income) | set(unalloc_fees)`, ed è preesistente: già prima di F-3 il giro era un'unione di set.
>   - F-3 ha tenuto solo l'ordine delle somme, che le lascia identiche byte per byte.
>   - Il commento di F-3 diceva di più: l'ho corretto in «The unallocated sums keep the access order».
>   - Va nel backlog (T8).
> - **Anche `PerformanceChart.svelte`**, oltre alla tabella di §0. Il waterfall (`otherEffectDescriptionLabel`) mappa le stesse descrizioni: senza la riga, nel grafico comparirebbe l'inglese grezzo.
> - **Scostamenti del `test-author`**, accettati:
>   - S4 diviso in due: lo scope misto è rosso, il solo E è un fermo;
>   - S3, col Viewer, fissa la quota 1;
>   - S7 riconcilia col riepilogo entro `CONVERSION_DUST`;
>   - nessun test unitario della mappatura Svelte, come per le righe sorelle: la coprono gli E2E di F-4.

### F-AI — Il nome nell'AI Export: il costo ✅ (inviato il 2026-10-12; deciso dal developer)

Solo il costo, come chiede §0: niente codice senza il via del coordinatore. Fonti: `.github/instructions/ai-development.instructions.md`, la skill `ai-export-probe-tuning`, `ai_export_composition.md:387-392` e `ai_export_probe_workflow.md`.

> **Note implementazione** (2026-10-12):
> - **Lo stato di oggi.** L'export di un broker mostra già la riga, per nome:
>   - `broker.flows_income_costs` mappa ogni riga di `other_effects` (`broker_financial.py:376` → `map_effect_row`, `payloads/portfolio_broker.py:730`; ordine di `sort_effects`, `:740`).
>   - Il componente passa dal renderer generico (`snapshotDataRenderer.ts`, `renderGenericPayload`): la descrizione esce così com'è, in inglese, come quella delle righe sorelle.
>   - `broker.reconciliation` e l'export del portafoglio leggono il riepilogo, il cui `period_other_result` non cambia con F-W. L'export del portafoglio tiene solo Income e Cost (`portfolio_financial.py:401,438`).
> - **La domanda di contratto: un bump di `broker.flows_income_costs`?** (`catalog.py:134`, v1)
>   - La forma del payload resta la stessa; cambia il contenuto: una riga in più, il residuo più piccolo.
>   - Nessuna regola scritta chiede un bump per i soli valori, e F-2/F-3 hanno cambiato cifre senza.
>   - Un bump chiede, nello stesso cambio: il catalogo, `COMPACT_COMPONENT_VERSIONS` (`snapshotDataRenderer.ts:1443`, altrimenti il fallback YAML) e i test che fissano le versioni.
>   - Consiglio: nessun bump.
> - **Le opzioni per il portafoglio:**
>   - **(a) niente**, costo 0. Per nome la riga si vede nell'export del broker; in quello del portafoglio resta dentro `period_other_result`.
>   - **(b) un campo nuovo** in `portfolio.flows_income` (`catalog.py:109`, da v1 a v2): le righe «FX on cash» per broker, filtrate per descrizione come fa il frontend, perché `OtherPeriodEffect` non ha un codice.
>     - Serve: payload e builder, catalogo v2, mappa compatta `{1,2}`, i test via `test-author`, i gate `ai-export`, vitest ai-export e `front check`, una riga di doc developer.
>     - Serve anche un **probe mirato**: `all`, un broker con cassa estera e uno solo EUR, in Compact e Standard. Il probe copia il DB di produzione e usa le credenziali, quindi lo lancia il developer, fuori dalla mia corsia.
>     - Stima ½ g più il probe. Rischio basso sulle cifre, che non cambiano; medio sul contratto.
>   - **Facoltativo con (b)**: una frase in `valuation_semantics` (`broker_financial.py:271`, `portfolio_financial.py:301`) sulla cassa estera rivalutata ogni giorno. Costa il bump a v3 delle due provenance e la mappa `{1,2,3}`, circa 2 h.
> - **Consigliato**: la (a) adesso; la (b) nella sezione I del backlog (T8), salvo il via del coordinatore per la 1.2.
>
> **Decisioni del coordinatore** (2026-10-12):
> 1. **Nessun bump di `broker.flows_income_costs`.** Il `version` di un componente è la versione dell'implementazione (`ai_export_composition.md`, «ComponentSpec»). Qui non cambiano né il builder né la forma del payload: cambiano solo i valori che arrivano dal motore. È lo stesso caso di C-50, dove il payload era invariato e la versione è rimasta la stessa.
> 2. **La (a) è lo stato attuale. Sulla (b) decide il developer**: il coordinatore la porta nel suo recap.
>    - La voce di T8 non va nel backlog finché il developer non decide: il testo pronto è qui sotto.
>    - Se arriva il via, il coordinatore dice quando farla: dopo F-4, o in un lotto a parte dopo l'integrazione di F.
> 3. **Correzione al costo della (b): la sonda non chiede né il developer né i dati di produzione.** T l'ha già fatta sulla sua corsia, con i dati sintetici, per B3b e per C-50. Il metodo è nel piano 43, al passo 5 di B3b:
>    - `test db populate --force --clean` nella corsia 6157;
>    - la sonda ufficiale `ai_export_real_prompt_probe.py`, lanciata da un involucro temporaneo fuori dal repo, sul DB copiato della corsia;
>    - la scansione dei segreti, e il controllo che UI e sonda diano gli stessi byte.
>
>    Per filtrare la riga serve una costante condivisa con chi la produce (oggi il letterale è a `portfolio_service.py:2001`), non una seconda copia del letterale.
>
>    La stima della (b) resta ½ g, più la sonda, che ora gira sulla 6157.
>
> **Testo pronto per T8** (sezione I di `BACKLOG_POST_1.2.md`), da scrivere solo se il developer non mette la (b) nella 1.2:
> - **«FX on cash» per nome nell'export del portafoglio.** Oggi la riga compare per nome negli `effects` di `broker.flows_income_costs`. Nell'export del portafoglio resta invece dentro `period_other_result`, perché `portfolio.flows_income` tiene solo Income e Cost (`portfolio_financial.py:401,438`).
>   - Cura: un campo con le righe «FX on cash» per broker, filtrate con una costante condivisa col servizio. Poi `portfolio.flows_income` passa a v2, con `COMPACT_COMPONENT_VERSIONS` `{1,2}`, e i test.
>   - Sonda mirata sulla corsia, sui dati sintetici (metodo del piano 43, B3b passo 5).
>   - Facoltativo: una frase sulla cassa rivalutata nella `valuation_semantics` delle due provenance, con il loro bump a v3.
>   - Stima ½ g più la sonda. Rischio basso sulle cifre, medio sul contratto.
>
> **⚠️ Fuori pista**:
> - **L'ipotesi di §0 era sbagliata a metà.** «La cifra resta dentro `period_other_result`» vale per il riepilogo e per l'export del portafoglio. Non vale per gli effetti dell'export del broker, dove la riga compare da sola, già con F-W. Il nome nell'AI Export è quindi in parte già fatto.
> - **Il mio costo della sonda era sbagliato.** Leggendo `ai_export_probe_workflow.md` («Copied Database and Credentials») avevo concluso che la sonda copiasse per forza il DB di produzione, e quindi toccasse al developer. Il coordinatore mi ha corretto (punto 3): la sonda gira sulla corsia, sui dati sintetici, col metodo che T ha usato per B3b e C-50.
>
> **Decisione del developer** (2026-10-12, riportata dal coordinatore): la (a) nella 1.2, cioè niente; la (b) dopo la 1.2, «con un codice tipizzato». Il testo pronto qui sopra è andato nella sezione I del backlog con quel cambio: un campo tipizzato su `OtherPeriodEffect` al posto della costante condivisa, e la stima a ¾ g più la sonda (§15, «Treno 43 e F-AI»).

### F-4 — Gate, golden, rapporto sul DB mock, tempi ✅ (2026-10-12)

Tutto sulla 6157, un comando alla volta. Prove in `/tmp/libreFolio_l41_f4_*.log`, fuori dal repo.

> **Note implementazione** (2026-10-12):
> - **I gate di F-W valgono anche per F-4**, perché dopo di loro nessun sorgente è cambiato.
>   - L'mtime più recente dei sorgenti è 02:36:59, il primo log dei gate è delle 02:37:19.
>   - I blob (12 caratteri):
>     - `native_cash.py` `9884e226c88d`;
>     - `portfolio_service.py` `39cb41d6ad8e`;
>     - `portfolio_engine.py` `00e6c07415f1`;
>     - `test_native_cash.py` `bef072035fb0`;
>     - `test_portfolio_service_native_cash.py` `6f5c12030269`;
>     - `OtherPeriodEffectsTable.svelte` `0475cad3415e`;
>     - `PerformanceChart.svelte` `3decff70146e`.
>   - I conti: guardia 1, `roi-fifo-utils` 652, `portfolio-engine` 40, `financial-math` 175, `ai-export` 1002, `lots-analysis-pure` 121, `api portfolio` 51. `front check` 0 errori e 0 avvisi; `i18n audit` 4349 chiavi, 0 mancanti.
> - **Il golden della guardia non è mai stato rigenerato.** `fixtures/native_cash_guard/eur_only_golden.json` ha il blob `611964be9fee`, lo stesso di F-0 (un solo commit, `aa6b6077a`), e la guardia passa.
> - **Build ed E2E**, con la porta verificata libera prima di ogni comando:
>   - `dev.py front build --debug`: exit 0 in 81 s; svelte-check 0 errori e 0 avvisi (`_f4_front_build.log`). L'`api sync` interno alla build non ha toccato file tracciati;
>   - `front-portfolio dashboard` 27/27 (`_f4_e2e_dashboard.log`). Copre `OtherPeriodEffectsTable` (via `PositionsPanel.svelte:208`) e il waterfall di `PerformanceChart`;
>   - `front-broker detail` 37/37 (`_f4_e2e_broker_detail.log`);
>   - `front-broker list` 9/9 (`_f4_e2e_broker_list.log`).
> - **Il rapporto sul DB mock** (`_f4_diff.log`, 963 righe).
>   - **Il metodo.** «Prima» è il codice di `c7f7b1807`, cioè il target senza F, estratto con `git archive`. «Dopo» è la worktree, da F-1 a F-W. Il DB è quello della corsia (76 transazioni), in due copie. Così la differenza isola F.
>   - 76 report: 38 coppie utente|scope per i periodi `1y` e `all`. I broker con cassa estera sono 1, 3, 4, 5 e 8; solo EUR il 2 e il 6; il 7 non ha cassa.
>   - **18 identici**, cioè tutti gli scope B2, B6 e B7. **58 cambiati**, solo sui broker con cassa estera.
>   - Due controlli, entrambi vuoti: «scope solo EUR cambiati» e «cambi di solo rumore».
>   - **Cosa cambia**:
>     - la storia: NAV, cassa, book, `broker_nav`, `total_pnl`, ROI/TWRR/MWRR, K/R;
>     - le candele, `allocation_history` e `broker_pnl_history`;
>     - `acquisition_funding`, per k2;
>     - i campi del riepilogo e le righe di `other_effects`.
>   - **Le identità dopo F** (prima di F fra parentesi):
>     - |cassa − Σ card| ≤ 2,9e-22 e |patrimonio − Σ card| ≤ 2,8e-22 (prima: fino a **866,5**);
>     - waterfall ≤ 9,5e-24 (9,4e-24);
>     - righe FX contro il Δ del P&L di periodo, e lo spostamento del residuo: ≤ 2,8e-22;
>     - nessun report rompe un'identità a 0,01 o più.
>   - **Esempio: admin, tutti i broker, `1y`.** Il P&L di periodo scende di 472,16, esattamente la somma delle 5 righe FX:
>     - B1 −127,14;
>     - B3 −54,34;
>     - B4 −94,60;
>     - B5 −196,08;
>     - B8 −0,003.
>
>     Il residuo resta 937,3212.
>   - **Esempio: B4, solo USD.** Prima nessun effetto; dopo, l'unica riga «FX on cash», −94,598.
> - **L'AI Export** (`_f4_ai_detail.log`): 33 snapshot, 31 cambiati; B7 è identico.
>   - In 21 snapshot di broker la riga «FX on cash» compare negli effetti.
>   - B2 e B6 cambiano solo nei campi «portafoglio» e «delta» di `concentration_comparison`, cioè nel confronto col portafoglio intero.
>   - Il resto segue il NAV: i bucket della performance, il drawdown, la concentrazione, i rapporti di `cost_efficiency`.
> - **Determinismo**: un secondo giro indipendente dà 0/76 report e 0/33 snapshot diversi, da entrambi i lati.
> - **I tempi**: a freddo, con le cache svuotate, mediane su n=7, admin, periodo `all`. Prima → dopo:
>   - ALL 0,2039 → 0,1589 s (0,78);
>   - B1 0,1104 → 0,0928 (0,84);
>   - B2 0,0691 → 0,0617 (0,89);
>   - B3 0,0720 → 0,0771 (1,07);
>   - B4 0,0617 → 0,0677 (1,10);
>   - B5 0,0854 → 0,0840 (0,98);
>   - B6 0,0536 → 0,0490 (0,91);
>   - B7 0,0059 → 0,0058 (0,98);
>   - B8 0,0308 → 0,0291 (0,94).
>
>   La somma dei 76 report a freddo passa da 10,30 a 9,55 s (0,927). La cassa nativa costa 4,4 ms di mediana (massimo 5,7), il 2,7% del totale; sugli scope solo EUR, 0.
> - **Il DB è stato solo letto**: il `.dump` delle due copie coincide con quello del DB della corsia (7582 righe).
>
> **⚠️ Fuori pista**:
> - **`reconciled` scatta sul rumore.** È preesistente, nell'AI Export, e non è mio.
>   - `portfolio_financial.py:490` e `broker_financial.py:435` fanno `reconciled = residual_amount == Decimal("0")`. Il residuo è ricalcolato dai campi del riepilogo e non è quantizzato.
>   - Il conteggio (`_f4_reconciled.log`): da ogni lato 33 flag, 26 veri, 5 falsi e 2 None (B7, senza dati).
>     - Prima i falsi sono user2|B1, test_user|OWNED (−2e-25), bob|B1, carol|B1 ed eve|B1.
>     - Dopo sono admin|OWNED (−1e-24), user2|B1, bob|B1, carol|B1 ed eve|B1.
>     - Due scambi; il |residuo| massimo è 1e-24.
>   - F quindi non cambia il numero dei falsi: sposta solo quali sono, e sempre su residui di rumore.
>   - Il danno: un lettore AI vede un residuo che si stampa 0,00 accanto a `reconciled: false`.
>   - **Proposta**: una tolleranza o la quantizzazione, per esempio |residuo| < 1e-9 come `CONVERSION_DUST` (`native_cash.py:53`).
>     - Probabilmente chiede il bump di `portfolio.reconciliation` e `broker.reconciliation`, più la mappa `COMPACT_COMPONENT_VERSIONS`.
>     - Il proprietario è T (AI Export). Lo porto al coordinatore nel checkpoint F-C2; se non entra, va in T8.
> - **Lo sha dei DB copiati cambia**, uguale per le due copie: è l'intestazione journal_mode/WAL che l'app imposta alla connessione. Il `.dump` identico prova che nessuna riga è cambiata.
> - **Il rumore dei tempi con n=3.**
>   - Al primo giro la mediana di ALL sembrava peggiorare (0,207 → 0,333 s), mentre il minimo migliorava (0,193 → 0,169).
>   - Con n=7 la mediana è 0,204 → 0,159.
>   - B3 e B4 restano a 1,07 e 1,10: è il costo della cassa nativa, 4–5 ms su report da 60–70 ms.
> - **Il messaggio del runner** «Shared backend ignored SIGTERM for 5s — killing its process group» è preesistente.
>   - Compare in circa 20 log precedenti, compresi i gate g12–g40 del coordinatore e i miei di T4 e T2g.
>   - Non cambia gli esiti.
> - **L'istantanea del DB** che il runner scrive in `.testLog/00_archive/` è ignorata da `.gitignore:119`. È un artefatto normale, fuori dal checkpoint.

### F-5 — Doc EN via `docs-writer`, e il testo del runner ✅ (2026-10-12)

Solo pagine EN, senza translate-stamp: le traduzioni vanno nel secondo giro di M. Nessuna pagina nuova; `mkdocs.yml` e la nav non cambiano. Prove in `/tmp/libreFolio_l41_f5_*.log`, fuori dal repo.

> **Note implementazione** (2026-10-12):
> - **Il runner** (`scripts/test_runner/_backend_services.py:571-574`, il solo testo concesso in §0).
>   - La docstring, il titolo e le due righe `print_info` di `services financial-math` nominano ora anche `native_cash.py` e le sue funzioni pubbliche: `compute_native_cash`, `cash_movement_from_transaction`, `effective_share`, `exchange_results`.
>   - Il comando e la cartella raccolta non cambiano; `ast.parse` ok.
>   - La prova a runtime, prima del checkpoint F-C2: `services financial-math` → **175 passed**, con le righe nuove stampate (`/tmp/libreFolio_l41_fc2_fm.log`). Il codice non è cambiato dai gate di F-W (02:37–02:43): dopo, solo il runner e la doc.
> - **Il brief**: ogni affermazione è stata verificata sul codice prima del lancio, pagina per pagina. Il `docs-writer` ha toccato solo le 13 pagine del brief:
>   - **teoria**, in `financial-theory/technical-analysis/performance-metrics/portfolio-engine/`:
>     - `index.en.md`:
>       - le regole di valutazione (:41);
>       - Cash(t) come cassa nativa rivalutata (§5);
>       - il risultato di cambio sulla cassa, con k2 e l'ancora `#exchange-result-on-foreign-cash` (§6);
>       - la riconciliazione;
>       - $\mathrm{FXonCash}_b$ fra gli effetti del periodo (§7);
>       - il pre-frame, che rigioca anche i giorni di cambio;
>     - `deposited-capital.en.md`:
>       - la riga della tabella: il cambio sulla cassa è un risultato, non capitale;
>       - il risultato va in $R_b$, e la perdita oltre $R_b$ esce da $K_b$;
>       - il transito in valuta e l'esempio D.
>
>       Le sezioni di T3 sui flussi interni restano;
>     - `period-pnl.en.md`: l'«Other» diviso in «FX on cash» (`#fx-on-cash`, con la formula e gli esempi +20 e +25) e residuo, con i limiti che restano nel residuo;
>     - `nav.en.md` e `book-value.en.md`: il termine Cash(t), lo stesso in NAV e in Book. Il cambio sulla cassa si annulla nell'Unrealized e sta nel Total P&L;
>   - **developer**:
>     - `backend/transactions/wac.md`: la regola del layer (D-4), la tabella dei moduli e la sezione su `native_cash`, cioè la firma, i membri di `NativeCash`, `CONVERSION_DUST`, il vincolo di `rates_until` e i chiamanti;
>     - `architecture/overview.md:76`: il layer contiene anche la cassa nativa;
>     - `frontend/data-quality-banner.md:141`: le conversioni del riepilogo vengono da `NativeCash.missing_conversions()`;
>   - **utente**:
>     - `dashboard/positions.en.md:87` e `kpi-cards.en.md:39`: la riga «FX on cash» di F-W;
>     - `dashboard/charts.en.md`: l'area Returns e il Total P&L comprendono il cambio sulla cassa;
>     - `dashboard/index.en.md:99`: la cassa in valuta è valutata ogni giorno;
>     - `brokers/index.en.md:11`: il cambio sulla cassa conta nel Gain/Loss, non nel capitale. Il paragrafo di T3b resta.
> - **La revisione sul codice**, prima di accettare:
>   - **`native_cash.py`**:
>     - la firma: `report_currency` solo per nome, `rates_until=None`;
>     - i membri di `NativeCash` e `CONVERSION_DUST` (:53);
>     - `financial_math/__init__.py` ha solo la docstring, quindi «non riesporta nulla» è vero;
>   - **il motore**:
>     - il passo 10c (`portfolio_engine.py:2708-2715`, `rates_until=actual_to`);
>     - `_revalue_foreign_cash` (:1490-1517);
>     - l'ordine: dopo la cassa del giorno e prima dei pool (:808-818 nel pre-frame, :993-996 nel frame);
>     - la riconciliazione (:1220-1239);
>   - **il servizio**:
>     - in `get_summary` la cassa della card è `value_at(valuation_date)`, e la testata è `last_state.cash_value` (:721, :1175);
>     - il riepilogo non converte rettifiche in natura, quindi la riga del banner è giusta;
>     - F-W (:1986-2019) salta la riga sotto `CONVERSION_DUST`;
>   - **l'aritmetica**: l'esempio D, il transito (+10 a 0,94), «FX on cash» (+20 e +25), e il residuo (il FX_CONVERSION da −€20 resta lì).
> - **Le prove**, un comando alla volta, sul giro finale (r3):
>   - `mkdocs build` (strict): ok, 0 avvisi (`_f5_build_r3.log`);
>   - `mkdocs check-links`: 95 validi, 0 rotti, 8 risolti a runtime (`_f5_check_links_r3.log`);
>   - `mkdocs translate-validate` (`_f5_tv_after_r3.log`). Il giro r2 aveva dato 75 errori e 74 avvisi; r3 aggiunge un `size-ratio` (vedi sotto).
> - **Il debito delle traduzioni**, per M:
>   - prima: 0 errori, 0 avvisi e 478 file ok (`_f5_tv_before.log`);
>   - dopo: 75 errori e 75 avvisi, 469 file ok su 624, 0 mancanti. Riguarda 6 pagine EN × 3 lingue: `book-value`, `deposited-capital`, `index`, `nav`, `period-pnl` e `positions`;
>   - gli errori: 42 `link-missing`, 12 `latex-display-count`, 9 `heading-count`, 9 `heading-level`, 3 `admonition-count`;
>   - gli avvisi: 30 `heading-emoji`, 18 `link-count`, 15 `latex-inline-count`, 9 `list-bullet-count`, 3 `size-ratio`;
>   - le pagine IT, FR ed ES non sono toccate.
>
> **⚠️ Fuori pista**:
> - **Due testi vecchi corretti nelle sezioni riscritte**, perché il codice diceva altro:
>   - la riconciliazione scala i pool **sommati** (:1220-1239), non broker per broker come diceva `index.en.md:164`;
>   - il pre-frame «senza consumare prezzi o cambi» (`index.en.md:220`) non è più vero: ora rigioca i giorni di cambio.
> - **Dove il `docs-writer` ha seguito il codice e non il brief** (tutto verificato):
>   1. la riga del banner perde anche «priced in-kind adjustments», perché il riepilogo non le converte. Le «cash balances» le toglieva già il brief;
>   2. ε_b è definito sul replay: il valore del giorno meno la cassa rigiocata;
>   3. `rates_until` è un obbligo del chiamante, che il codice non controlla: dopo quella data vale l'ultimo cambio, e `value_at` alza un errore se il cambio manca;
>   4. la cassa in testata «coincide» con la somma delle card;
>   5. il link di `wac.md` punta all'ancora del §6, comune a tutte le lingue: `#exchange-result-on-foreign-cash` esiste solo in EN e rompeva le build IT, FR ed ES;
>   6. «byte per byte» non compare: è una garanzia dei test (la guardia), non una promessa per l'utente;
>   7. il cambio della cassa in viaggio resta nel residuo.
> - **Due miei giri di correzione** (r2 e r3):
>   - **r2**, quattro frasi che dicevano troppo:
>     - «ogni movimento entra nella base del capitale» (`deposited-capital.en.md`, riga della tabella);
>     - «una riga per ogni broker con cassa in valuta» (`positions.en.md:87`, `kpi-cards.en.md:39`, `index.en.md:231`). La riga c'è solo se i cambi hanno mosso quella cassa, perché F-W la salta sotto `CONVERSION_DUST`;
>   - **r3**: la frase sulla base del capitale tornava in `book-value.en.md:29` e `index.en.md:41`.
>     - Veniva dal mio brief: «every movement stays at its own date's rate», detto del capitale.
>     - In realtà ogni movimento si registra al cambio della sua data, ma nella base entrano solo i flussi di capitale (in `index.en.md`, «external cash flow»).
>   - Il messaggio di commit C5 aveva la stessa svista di r2: corretto prima del checkpoint.
> - **Il `size-ratio` in più** (r3): la frase più lunga porta `book-value.en.md` da 4.419 a 4.477 caratteri, e la copia FR (3.347) scende dal 75,7% al 74,8%, sotto la soglia del 75%. IT ed ES lo avevano già. L'avviso è vero, perché la pagina FR non ha il contenuto di F-5. Non accorcio il testo solo per passare il controllo.
> - **La seconda descrizione del runner** è fuori dal ritocco concesso: `_backend_services.py:1070`, `desc="Average cost: movements, conversions through the FX service, diagnostics"`. La propongo al coordinatore in F-C2.

### F-C2 — Checkpoint 4, fine F ✅ (2026-10-12), nel treno 42

> **Note implementazione**:
> - Consegnato FROZEN al coordinatore il 2026-10-12: 25 percorsi, cinque commit proposti (C4–C8), col manifest e i messaggi.
> - **Verificato dal coordinatore**:
>   - i 25 blob coincidono col manifest, la partizione C4–C8 è esatta, la scansione privacy è pulita (1.988 righe);
>   - ha letto `exchange_results`, la riga «FX on cash» col residuo e i conti degli esempi della doc (+25 EUR, tabella D): tutto torna.
> - **Nel target**:
>   - C4 `a5f41f60c` (i risultati di cambio nel modulo e il testo del runner), C5 `c04e44ff5` (il servizio), C6 `9a0d9280c` (il frontend e la chiave i18n), C7 `a4332b25b` (la doc EN), C8 `56fcf0aac` (questo piano). L'albero è `dce102dc320c`, quello del manifest;
>   - treno 42: il merge `15cbff6fb`, poi il CHANGELOG `5d62658bb` con le due righe di I;
>   - il ramo è avanzato a `5d62658bb` in fast-forward.
> - **Le decisioni del coordinatore** sui tre punti del checkpoint:
>   1. il debito di traduzione di F-5 passa a M, nel giro finale;
>   2. `reconciled` sul rumore (F-4, «Fuori pista») diventa C-53, del coordinatore, che consiglia al developer di farlo nella 1.2, a T dopo T-1. I non lo tocca;
>   3. il testo del runner a `:1070` è approvato con la formulazione di F-5. Poi è passato a T (qui sotto).

### T8 / F-C3 — La sezione I del backlog ✅ (2026-10-12)

> **Note implementazione**:
> - **Base**: HEAD `5d62658bb` (treno 42), worktree pulita prima dei due file.
> - **La sezione I di `BACKLOG_POST_1.2.md`**, riscritta da capo, solo nelle sue righe:
>   - l'introduzione: il lotto è chiuso e resta solo F-AI (b); i rimandi alle voci che stanno altrove (la sezione T, il gruppo I del backlog 38) e a quelle lasciate fuori di proposito: F-AI (b), che aspetta il developer, B16 (latente), C-53 (del coordinatore), il debito di traduzione di F-5 (di M);
>   - ✅ F (B4, B13, B14), coi commit;
>   - aperte: B1, B2, B3, B5, B6, B7, B8, B10, B11 (i titoli), B12 (le quantità), B15, e le nuove B17, B18, B19;
>   - ogni ancora riverificata su `5d62658bb`.
> - **Questo piano**: stato e base in testa, §9 (F-C2, T8, F-C3), §14 (il rimando al backlog, B4, B13 e B14 chiusi, B11 e B12 chiusi a metà, B17–B19), «Righe citate», §17.9.
> - Solo documenti: nessun test e nessun server; `git diff --check` pulito. Consegnato al coordinatore col checkpoint F-C3: 2 percorsi, un commit proposto.
>
> **⚠️ Fuori pista**:
> - **La riga del runner è passata a T.** Il coordinatore l'aveva messa in F-C3, poi l'ha tolta: T-1 riscrive tutta la voce `financial-math` del runner (le righe descrittive `:569-573` e la `desc` di `:1070`), e un file condiviso ha un solo autore. Non l'avevo ancora toccata: niente da annullare.
> - **P1, R4, W1 e X5 sui prezzi restano fra due piani.** Il piano di T li segna «F» (P1 `:240`, R4 `:136`, W1 `:226`), ma F non li ha fatti: §17.6 li mette in U4, in U5 con B8, in U7 e in U1. Nella sezione I sono un rimando; la correzione del piano di T la propongo al coordinatore.
> - **P-3 del backlog è chiudibile** con F (`c04e44ff5`): i flussi dei contributi vengono dalle stesse righe del riepilogo, che segnala le coppie mancanti (B14). È nella sezione P: lo propongo al coordinatore.
> - **La riga 41 dell'indice** (`BACKLOG_POST_1.2.md:47`) dice ancora «§14 Backlog (B1–B12) | lotto in corso (F)». È del coordinatore: propongo «§14 Backlog (B1–B19) | chiuso: F nel treno 42; voci aperte nella sezione I».
> - **T-U1** («Esclude i giri del portafoglio, che chiude F (O2, X5)») va stretta a «X5 sui movimenti»: le quattro conversioni dei prezzi (`portfolio_service.py:822`, `:851`, `:1795`, `:1813`) restano in U1 e U5. Proposta al coordinatore.
> - **Il commento PURE del runner** (`:1071-1072`) parla di «the module». Con due moduli può diventare «each module's only I/O is convert_bulk, which every test replaces on its module with a double»: solo un suggerimento per T-1.
> - **Il significato di B5** l'ho ripreso dall'analisi del 2026-10-10 (D2, D5): nella vista del mittente il residuo del waterfall è MV(t) − costo, in quella del destinatario costo − MV(t).
> - **Le righe di §14 sono scivolate** da quando sono state scritte (per esempio `get_positions_contribution` da `:1703` a `:1642`, `_get_price_at_date` da `:522` a `:525`). Nel backlog uso quelle di `5d62658bb`; qui restano quelle del loro momento.

### Treno 43 e F-AI ✅ (2026-10-12)

> **Note implementazione**:
> - **F-C3 nel target**, verificato dal coordinatore:
>   - C9 è `f10fcd04a`; l'albero `f8c1eb29aced` corrisponde al manifest, e la privacy è pulita;
>   - treno 43: J1 `deec22bf8`, poi il merge `d27a2f729`. Il ramo è avanzato in fast-forward.
> - **In J1 il coordinatore ha chiuso le proposte 1 e 2** di «T8 / F-C3»:
>   - la riga 41 dell'indice, con le mie parole;
>   - P-3, chiusa con `c04e44ff5` nell'indice e nel backlog 38.
>
>   Nella sezione C ha aggiunto anche C-53.
> - **Le proposte 3, 4 e 5** (T-U1, P1/R4/W1 nel piano 43, il commento PURE del runner) toccano file di T: le ha girate lui a T.
> - **La decisione del developer su F-AI**, riportata dal coordinatore: la (a) nella 1.2, cioè niente; la (b) dopo la 1.2, «con un codice tipizzato».
> - **La voce F-AI (b)** è nella sezione I di `BACKLOG_POST_1.2.md`. È il testo pronto di «F-AI», con un cambio: chi legge la riga confronta un codice tipizzato su `OtherPeriodEffect` invece della descrizione inglese. Righe riverificate su `378338fed`.
> - Consegnato col checkpoint di M-16 ([piano 44](../44_importWizardBrokerGate/plan-phase00ImportWizardBrokerGate.prompt.md), S6): solo documenti, nessun test di questo lotto.
>
> **⚠️ Fuori pista**:
> - **Il codice tipizzato tocca l'API.** Al posto della costante condivisa, che proponevo nel costo, ora c'è un campo dello schema (`schemas/portfolio.py:433-440`). Quindi serve `api sync`, che F-W aveva evitato apposta. In cambio, i due confronti del frontend sulla descrizione (`OtherPeriodEffectsTable.svelte:75`, `PerformanceChart.svelte:291`, entrambi di `9a0d9280c`) possono passare al codice. La stima sale da ½ g a ¾ g, più la sonda.
> - **Il letterale è scivolato** da `portfolio_service.py:2001` (`5d62658bb`) a `:1978` (`378338fed`), con i riordini di T (`1cc9cd8f5`, `a57a43fbd`). Le righe di `portfolio_financial.py:401,438`, `components/catalog.py:109` e `snapshotDataRenderer.ts:1443` non sono cambiate.

## 16. Inventario: capitale, investito e guadagno fuori dal motore (T2-inv)

Classi: **(a)** misura la stessa cosa del motore → migra; **(b)** ha regole che il motore non ha → prima nel motore, con un test, poi migra; **(c)** misura di proposito altro → resta, documentata.

### 16.1 I punti

| # | Punto | Cosa calcola | Classe |
|---|---|---|---|
| 1 | `portfolio_service.py:724`, `:802`: `total_invested` | Σ DEPOSIT/WITHDRAWAL convertiti | (a), già morto: `:1106` lo sovrascrive col motore quando c'è uno stato |
| 2 | `:736`, `:767-776`, `:803`: `broker_total_invested` | il capitale della card | (a), §16.2 |
| 3 | `:992-1001`, `:1005-1006`: il NAV della card | MV del motore + cassa nativa × cambio di oggi, **senza** il valore in viaggio | (b) per la cassa, §16.2 |
| 4 | `broker_cash_native`, `all_cash_balances` | cassa nativa per valuta, × quota | (c): la card (`cash_balances`), la testata, AI Export `fx_core.py:322-325` |
| 5 | `_total_deposited`, `_total_withdrawn`, `net_deposited_capital` (`:382-384`, `:806-808`) | depositi e prelievi espliciti del periodo, lordi | (c): nelle viste filtrate differiscono di proposito da `period_net_flows` del motore |
| 6 | `_income_accum`, `_fees_*`, `income_by_pos`, `fees_taxes_by_pos` (`:813-828`) | scansioni per tipo | (c) |
| 7 | «Other» (`:1131-1137`) | `period_pnl` del motore − le parti del motore − le scansioni | (c); dopo D2 un TRANSFER filtrato non vi finisce più |
| 8 | `get_positions_contribution` (`:1711-2104`) | P&L per (broker, asset) | (c) per questo lotto; B8 |
| 9 | `broker_service.get_summary` (`broker_service.py:363-497`) | vista di custodia: broker intero, cassa senza quota, unrealized per titolo | (c): nessun capitale né guadagno del broker |
| 10 | AI Export | tutto passa da `get_report`, quindi dal motore (`portfolio_broker.py:343-358`, `broker_cost_efficiency.py:606`) | nessuna copia; scansioni (c) di turnover e reddito, B9 |
| 11 | Frontend | `BrokerCard.svelte:146-189` legge soltanto. `KpiSection.svelte` invece calcola `pnlDeltaDay` (`:77`) con le sue percentuali (`:96-99`, `:128-131`) e `timingEffectVal` (`:236-240`) | BrokerCard: nessun calcolo. KpiSection: di T (§1.4, U8). Corretto in T7 (2026-10-11) |

Regole dello specchio confrontate col motore (punto 2):

| Regola | Motore | Specchio | Esito |
|---|---|---|---|
| DEPOSIT/WITHDRAWAL × quota | sì | sì | uguale |
| quota (OWNER: `share_percentage`, None → 1; EDITOR/VIEWER: 1) | `portfolio_engine.py:2381` | `portfolio_service.py:755` | uguale |
| metà `linked_external` | contate (D2 per i titoli) | ignorate | motore |
| coppie `linked_internal` | flussi all'arrivo (questo lotto) | ignorate, salto | motore |
| ADJUSTMENT in natura | costo dal pool (`step.cost_report_change`), la gamba d'uscita toglie il costo medio, cambio mancante segnalato | `override × qty`, anche sulle uscite; `cost_basis_currency or base_currency` | motore (D4, un'unica funzione del costo medio) |
| esclusione delle rettifiche legate a un evento | solo `split_linked_tx_ids` | `asset_event_id is None` | motore più preciso; differiscono solo su un ADJUSTMENT manuale con override legato a un evento non SPLIT (`transaction_service.py:958-975` azzera l'override sugli SPLIT automatici) |
| coppie FX mancanti | `_missing_fx` del motore, unito da `_engine_missing_fx_pairs` (`:298-315`, `:1210`) | `all_missing_pairs` | nulla si perde |
| limite `date_to` | stato alla data di valutazione | `_get_transactions(…, date_to)` | uguale in produzione, dove `get_report` passa sempre una data. Solo in una chiamata diretta senza `date_to` lo specchio leggeva anche le righe con data futura, il motore no: correzione del 2026-10-11, §15 T1d/T2g |

### 16.2 La card

- **Capitale**: `capital_contribution` del motore alla data di valutazione. Guadagno = NAV − C; percentuale = guadagno / C solo se C > 0, altrimenti 0, come la testata (`:1110`). Un broker che ha spedito più di quanto ha ricevuto ha C ≤ 0: mostrerà 0,00 %; un «—» chiederebbe lo schema e il frontend (backlog).
- **NAV, opzione H (consigliata)**: NAV_b = MV_b + IT_b + cassa_b a T.
  - **Come si calcola (T2f, rivisto il 2026-10-11, §15 T2f)**:
    - MV_b: invariata, cioè le righe della tabella (`position_states_end`, valutate a T, senza la polvere; `portfolio_service.py:835`, `:879-881`);
    - cassa_b: invariata, Σ_valute nativa_b × cambio(T);
    - IT_b: un campo interno nuovo, `in_transit_contribution` di `BrokerDailyContribution`, letto dall'ultimo stato del motore. Nessuno fuori dall'engine e dalla card lo legge (l'API esporta solo `pnl_contribution`). Nessun cambio di schema né di API.
  - La prima idea era `nav_contribution_b` − cassa del motore_b + cassa_b a T. **L'ho abbandonata**: il motore valuta per intero solo i giorni «dirty». In un ultimo giorno con un solo cambio di cambio, la sua MV resterebbe al cambio dell'ultimo giorno «dirty», mentre le righe della tabella sono a T. La card avrebbe perso la valutazione esatta alla data, che oggi ha.
  - Cambio mancante a T: **nessun ripiego serve** (correzione del 2026-10-11, §15 T1c). Engine e servizio cercano il cambio con lo stesso `convert_bulk`, che riempie all'indietro senza limite (`fx.py:1240-1420`; preload dell'engine `portfolio_engine.py:2820-2837`). Se a T manca, manca anche a ogni data di movimento ≤ T: la cassa del motore non ha quella valuta nemmeno lei, e la coppia è già segnalata. Oggi quella cassa sparisce dalla card, e così resta.
  - Card e ultimo punto della linea del broker differiscono per tre motivi:
    - la deriva di B4 sulla cassa;
    - la polvere (`QUANTITY_DUST_THRESHOLD` = 0,00001 unità), che la card esclude e il motore conta;
    - un cambio mosso in un giorno non «dirty», che il motore non rivaluta (F).
  - Il valore in viaggio della card viene invece dal motore: in un giorno non «dirty» in cui si muove solo il cambio, resta al cambio dell'ultimo giorno «dirty», sulla card come sulla linea (§15 T1c, B11).
  - Σ card = NAV della testata quando cassa e titoli sono in valuta base, a meno della polvere.
  - Ripara i salti e il valore in viaggio, e tiene la rivalutazione. Attribuzione del cambio verificata a mano: A guadagna (Y−X)·fx(T) − Y·fx(t0) + X·fx(t_arr), B guadagna X·(fx(T) − fx(t_arr)).
  - Resta la differenza fra card e linea del grafico, pari alla deriva di B4 sulla cassa; esiste già oggi, insieme al valore in viaggio.
  - `cash_total` e `cash_balances` invariati.
  - Stima: T1b ¼ di giornata, T2f ½ giornata. Rischio basso.
- **Opzione F**: prima B4 intero nel motore (registro nativo per broker e valuta, rivalutato ogni giorno; preload dei cambi; pool K/R; una voce nuova nel waterfall, quindi schema, frontend e i18n; golden di TWRR/MWRR, candele e AI Export). Stima 2,5–4 giornate, rischio alto. Consiglio un lotto a parte dopo il 41: allora lo scambio di H vale zero. **Rivista in T7** (§17.8): 4–5 giornate, 4½–6 con la voce del waterfall; F è nella 1.2 (§0).
- `total_invested` (punto 1): col motore, oppure 0 senza stato.

### 16.3 T1b, il rosso della card

- `test_portfolio_service.py`, accanto a `test_summary_with_breakdown_uses_per_broker_invested` (`:310-343`).
- A deposita 5000; CASH_TRANSFER A→B di 1000, collegato, in giornata; nessun prezzo. `get_summary(include_breakdown=True)`: oggi le card danno −1000 / +1000, atteso 0 / 0; NAV 4000 / 1000.
- Variante con un viaggio di più giorni, valutata durante il viaggio: oggi A ha NAV 4000 e B 0, atteso NAV A 5000 (il valore in viaggio resta di A), guadagni 0 / 0.
- Variante in valuta (T1c, opzione H, 2026-10-11): `test_summary_with_breakdown_internal_cash_transfer_foreign_currency_moves_capital_at_arrival_rate`.
  - Base EUR, CNY (nessun altro test usa CNY né il 2038). Cambi CNY→EUR: 01-01 0,8; 01-10 0,9; 01-14 0,95; 01-15 1,0; 01-20 1,2.
  - A deposita 1000 CNY (capitale 800); 500 CNY partono da A il 10 e arrivano a B il 15.
  - Il 14, in viaggio: A 950 / 150 / 0,1875 (500 di cassa e 500 in viaggio, entrambi a 0,95); B 0 / 0 / 0.
  - Il 20: A 600 / 300 / 1; B 600 / 100 / 0,2. Il flusso interno vale 500 (al cambio dell'arrivo); Σ guadagni = 400 = 1000 × 1,2 − 800.
  - La testata non si verifica: il motore valuta la cassa al cambio di ogni movimento (B4, F), quindi differisce da Σ card.

## 17. Analisi di F (T7, 2026-10-11)

> Base `251067435`, codice identico a `43d92ed23`, dove ogni riga citata è stata verificata. Solo analisi: niente codice, niente test.

### 17.1 F in una riga

Una sola ricostruzione della cassa nativa per broker e valuta, in `financial_math/native_cash.py`. Il motore ne prende il valore della cassa, rivalutata ogni giorno (B4); il servizio ne prende la cassa delle card e i flussi del periodo. Sostituisce quattro giri sulle transazioni che oggi rifanno lo stesso conto con regole proprie.

### 17.2 I giri che F sostituisce

| # | Dove | Cosa misura | Chi lo legge | Regole sue |
|---|---|---|---|---|
| G1 | motore, passo 1 (`portfolio_engine.py:730-740`) | la cassa, ogni movimento al cambio della sua data | NAV, P&L, linee per broker, «Liquidity», K/R | solo importo ≠ 0 con valuta; × quota; cambio mancante → riga esclusa e segnalata |
| G2 | `get_summary` (`portfolio_service.py:750-813`) | cassa nativa delle card; depositi e prelievi (abs), reddito (con segno), costi (abs); reddito e costi per posizione | card (`:977-987`, un `_convert_to_base` per broker × valuta a `:983`), «Other» (`:1118-1128`), `net_deposited_capital` (`:1233`), il rendimento netto della posizione (`:929-943`) | tiene le righe a importo 0 (`:763-766`); un `convert_bulk` per riga (`:771`); coppia mancante → `all_missing_pairs` (`:780`) |
| G3 | `_signed_transaction_sums_by_date` (`:1509-1560`) | somme per data e tipo, con segno | `get_income_history` (`:1562`), `get_cost_history` (`:1599`), `get_deposit_history` (`:1625`); in produzione solo da `get_report` (`:2338`, `:2350`, `:2362`) | finestra `(from, to]`; salta importi nulli o 0; un `convert_bulk` per riga (`:1548`); coppia mancante → riga saltata e segnalata |
| G4 | `get_positions_contribution` (`:1777-1808`) | reddito e costi per (broker, titolo), e non allocati | i contributi per posizione e il loro «Other» (`:2068-2080`) | un `convert_bulk` per riga (`:1789`); coppia mancante persa in silenzio (B14) |

Inoltre la regola della quota è scritta quattro volte (O2: `portfolio_engine.py:2494`, `portfolio_service.py:754`, `:1532`, `:1771`), e gli accumulatori del motore rifanno G4 senza un lettore in produzione (B13).

### 17.3 B4 in numeri

- **Trasferimento**: 1000 USD depositati a 0,90 (capitale 900), poi A→B in giornata a 0,95.
  - Oggi: la cassa di A resta −50 per sempre, P_A = 0; B 950, P_B = 0; P = 0.
  - Con F: A 0, P_A = +50; B 950, P_B = 0; P = +50, il guadagno di cambio vero.
- **Spesa**: 1000 USD depositati a 0,90, poi un BUY da 1000 USD a 0,95.
  - Oggi: una cassa fantasma di −50 per sempre, col saldo nativo a 0; P = MV − 950.
  - Con F: cassa 0, P = MV − 900.

### 17.4 Il modulo e chi lo chiama

**`backend/app/services/financial_math/native_cash.py`**, piatto, sullo schema di `average_cost.py`:
- `effective_share(role, share_percentage)`: OWNER → `share_percentage`, None → 1; EDITOR e VIEWER → 1. Chiude O2 sui quattro siti.
- `CashMovement`, record immutabile: id, data, broker, titolo o None, tipo, valuta, importo nativo × quota. L'adattatore `cash_movement_from_transaction(tx, *, share)`, come `cost_movement_from_transaction`.
- Fold puri, senza I/O, testati da soli:
  - il registro nativo per (broker, valuta), giorno per giorno;
  - i flussi in una finestra: per tipo, per posizione, non allocati per broker.
- `compute_native_cash(...)`, asincrona: una sola chiamata `convert_bulk` per tutti i movimenti, con l'importo vero al cambio della sua data, cioè l'aritmetica di oggi. Chiude X5 sui giri G2–G4. Le coppie mancanti tornano in un elenco (chiude B14).
- Il valore del registro a una data: la valuta del report sommata come oggi; ogni valuta estera = saldo nativo × cambio del giorno. Un termine vuoto non si somma: un `Decimal("0E-10")` cambierebbe l'esponente, quindi i byte del JSON.
- Importa `Currency` da `schemas.common` e `convert_bulk` da `services.fx`, come `average_cost.py`; nessun servizio d'orchestrazione (D-4). Una riga nella docstring di `financial_math/__init__.py`.

**Il motore** (`portfolio_engine.py`):
- il passo 1 costruisce il registro col modulo, e ogni giorno la cassa vale il registro a quella data. La cassa in viaggio e i flussi interni del lotto 41 restano come sono. L'ECF non cambia: ogni movimento al cambio della sua data;
- un giorno diventa «dirty» quando si muove il cambio di una valuta tenuta in cassa: la metà di B11 che riguarda la cassa. Quella dei titoli rompe la guardia e va in U (§17.6);
- pre-frame: i saldi nativi valutati all'inizio della finestra. In produzione il pre-frame è vuoto (`date_from=None`);
- K/R, opzione **k2** (consigliata): il risultato di cambio della cassa di un broker, valore(d) − valore(d−1) − Σ movimenti convertiti(d), va in R[b]. Un risultato negativo prende la strada già esistente del clamp, come il reddito con segno. Il valore in viaggio tiene il riscalamento di oggi (B3). L'opzione k1, il solo riscalamento, darebbe una parte del guadagno di cambio a K;
- il risultato espone il registro. Gli accumulatori di B13 spariscono e i loro test passano alla vista dei flussi, con gli stessi numeri, via `test-author`;
- la chiave della cache del blob non cambia; `EngineEndState` non viene mai ripreso (`:2596-2600`, «for now recompute»);
- i cambi li chiede il modulo, così il test del preload (`test_portfolio_engine_vnext.py:792`) non cambia. Se i tempi (F-4) non reggono, il motore gli passa la sua mappa, e quel test cresce delle nuove richieste.

**Il servizio** (`portfolio_service.py`):
- `get_summary`: cassa delle card e `cash_total` di ogni broker dal registro del motore a T; i totali del periodo dai flussi. Spariscono G2 e il `_convert_to_base` per broker × valuta (`:983`). Testata = Σ card anche con la cassa in valuta;
- le tre storie tengono la firma: le circa 30 chiamate dirette nei test restano uguali. Chiamate da sole, usano il modulo senza il motore, all'orizzonte del motore (`date_to or today`), e lì B12 sparisce. `get_report` passa loro il registro del suo run: nessun secondo giro;
- `get_positions_contribution`: i flussi per posizione dal modulo (G4 sparisce, B14 chiuso). Prezzi e quantità restano (B8, U5).

**Le viste**, ciascuna coi segni di oggi del suo consumatore:
- custodia: tiene le righe a importo 0 (la valuta resta in `cash_balances` come oggi), raggruppa per riga come la card, si ferma a `actual_to`;
- valore del motore: per giorno, come sopra;
- flussi: finestra `(from, to]`, per tipo. Nel riepilogo depositi, prelievi e costi in valore assoluto, il reddito con segno; nelle storie tutto con segno, senza le righe a 0. Per posizione senza filtri, non allocati per broker, coppie mancanti segnalate.

**Cambio mancante**, politica (a), consigliata: un movimento datato prima del primo cambio disponibile resta fuori dal valore e dall'ECF, ed è segnalato, come oggi nel motore. La card smette di contarlo (oggi lo conta al cambio di T), quindi testata = Σ card; `cash_balances` lo elenca ancora in nativo. L'alternativa (b), contarlo dal primo cambio con l'ECF a quel cambio, cambia la semantica dell'ECF.

### 17.5 La guardia

- **Portafoglio guardia**: ogni riga con un importo è nella valuta del report. Lì F non vede valute estere in cassa, e tutti gli output restano identici byte per byte: NAV, P&L, linee per broker, ROI, TWRR, MWRR, candele, allocazione, card, riepilogo, storie, contributi, AI Export.
- **Prova**: un golden JSON su fixture dedicate (cassa EUR; una variante con titoli USD comprati in EUR), generato **prima** del codice (F-0) e confrontato in F-4.
- **Limite**: con una valuta del report diversa dalla cassa (override), la cassa EUR diventa estera e quei valori cambiano, giustamente.
- **Il DB mock non è un portafoglio guardia**: ha cassa USD (IB, Directa, eToro, Coinbase) e un FX_CONVERSION (`populate_mock_data.py:1180-1469`, `:1660-1690`). Un rapporto prima/dopo ne elenca i cambiamenti attesi. Nessuna spec E2E fissa NAV o cassa.

### 17.6 Dove va ogni voce: F o U

U = le unificazioni di T dopo la 1.2 (U1–U10, `BACKLOG_POST_1.2.md:98-108`). La corrispondenza U-n era mia, perché il piano di T non è nella base. **Il 2026-10-11 il coordinatore l'ha riconciliata col piano di T** (§0, §17.11): B9 va in U3, non in U9; il piano di T dice già «U3 … O2 con F» e «U6 (L1, L2) … con B4», dove B4 è quello di T; X5 e O2 sui giri G1–G4 e sulla card li chiude F; R1 resta in U4; C1 lo smista T.

| Voce | Cosa | Dove | Perché | Stima, rischio |
|---|---|---|---|---|
| B4 | cassa estera mai rivalutata | **F** | è F | in F |
| §16, punti 3–7 | cassa della card, `cash_balances`, flussi del periodo, «Other» | **F** | giro G2 | in F |
| X5 | cambi convertiti uno a uno | **F** per G2–G4 e la card (`:771`, `:1548`, `:1789`, `:983`); **U1** per i prezzi (`:867`, `:896`, `:1884`, `:1902`) | stesso giro | in F |
| O2 | quota copiata | **F** | serve al modulo | ¼ g, basso |
| B12 | date future in chiamata diretta | **F** per storie e flussi dei contributi; **U5** per le quantità | stesso giro | in F |
| B13 | accumulatori del motore | **F** | doppiano la vista dei flussi | in F; port dei test |
| B14 | coppia persa nei contributi | **F** | giro G4 | in F |
| B11 | giorni «dirty» senza cambi | **F** per la cassa; **U1** o **U5** per i titoli | i titoli rompono la guardia | U: ½ g, medio (cambiano NAV e linee con titoli in valuta) |
| P1 | P&L di periodo nel servizio (`_compute_period_summary_metrics`, `:595`) | **U4** | aritmetica sugli stati del motore, non un giro; con F cambia da sé | ¼–½ g, basso |
| R1/R2 | ribasamento TWRR/MWRR due volte (circa `:1303-1345` e `:2237-2290`), riprova MWRR | **U4** | puro riordino | ½–1 g, basso: nessun valore atteso cambia |
| R3 | rendimento netto della posizione (`:929-943`) | **U4** la formula; gli ingressi da F | | ¼ g, basso |
| R4, B8, V2/P2, quantità di B12 | prezzi propri dei contributi e variazione a 1 giorno (`:886-912`; `_get_price_at_date` `:522`, senza ripiego né split) | **U5** | valorizzazione, non flussi | 1½–2 g, medio: cambiano i contributi e le variazioni a 1 giorno |
| W1 | allocazione senza i titoli in viaggio (`portfolio_engine.py:1281-1283`) | **U7** | rompe la guardia | ½ g, basso |
| B15 | custodia rifatta dal PAC e dalla pagina del broker | **U** (U5 o U7) | altri consumatori; `transaction_service.py` è vietato | ½ g |
| C1 | costo unitario dell'anteprima (`_wac_qualifying_txs`, `:239`) | **T** (casa del costo medio) o U6 | | 1–2 h |
| B9 | AI Export dalla pagina di un broker dove l'utente è Viewer o Editor: turnover per la quota grezza 0, e `abs` sul reddito (descrizione corretta in §14) | **U3, a T** | regola unica per export: quella della pagina da cui parte | dopo la 1.2 |
| §16, punto 9 | pagina del broker, custodia | resta (c) | misura altro | — |
| L1/L2 | mini-FIFO | **T** (B4/U6) | deciso dal coordinatore | — |
| KpiSection | `pnlDeltaDay`, `timingEffectVal` | **T** (U8) | frontend | — |

Somma U, senza C1 e B9: circa 4–5½ giornate.

### 17.7 Rischi

- **Portata**: F tocca motore, servizio, tre storie e i contributi. La guardia la contiene: tutto ciò che cambia deve stare nei portafogli con cassa estera.
- **Valori attesi che cambiano**, solo con cassa estera:
  - i test del servizio in valuta: le coppie PGK mancanti (`test_portfolio_service.py:3186+`); T1c guadagna l'asserzione testata = Σ card;
  - i test di B13, portati con gli stessi numeri;
  - golden e probe dell'AI Export, se un fixture ha cassa estera: da misurare in F-4.
- **Tempi**: rivalutare ogni giorno chiede il cambio di ogni giorno per ogni valuta in cassa. Misura in F-4; ripiego: la mappa del motore.
- **Precisione**: per una coppia inversa, `importo × (1/r)` del motore e `importo / r` di `convert_bulk` differiscono all'ultima cifra. Ogni vista tiene l'aritmetica di oggi, quindi nessun valore cambia per questo.
- **K/R**: un risultato di cambio negativo passa dal clamp; con k1 andrebbe in parte a K.
- **Card e linea**: dopo F differiscono solo per la polvere, come oggi.
- **Waterfall**: senza F-W il risultato di cambio sulla cassa finisce nell'«Other».

### 17.8 Passi e stima

| Passo | Cosa | Stima |
|---|---|---|
| F-0 | Rossi via `test-author`: i fold puri; P_A = +50 (§17.3); Σ P_b = P con cassa estera; K/R; il golden della guardia, generato prima del codice; T1c con testata = Σ card; i port di B13 | ~1 g |
| F-1 | `native_cash.py`, `effective_share`, la riga nella docstring | ½ g |
| F-2 | Il motore | 1–1½ g |
| F-3 | Il servizio: card, riepilogo, storie, contributi | 1 g |
| F-4 | Gate, confronto col golden, rapporto sul DB mock, tempi | ½ g |
| F-5 | Doc EN via `docs-writer`: `deposited-capital`, `book-value.en.md:23`, la pagina developer di `financial_math` | ¼–½ g |
| F-W | **Forma minima** (§0): in `get_positions_contribution`, una riga «FX on cash» negli `other_effects` per ogni broker con cassa in valuta, e il residuo scende della stessa cifra. Nessuno schema nuovo, niente `api sync`, KpiSection intatta. Una riga di mappatura in `OtherPeriodEffectsTable.svelte`, una chiave nei 4 cataloghi col via del coordinatore, la doc di `positions.en.md:87` e `kpi-cards.en.md:39`. (Prima della decisione: voce nel waterfall, con schema, `api sync`, KpiSection e `snapshotDataRenderer.ts:1162`) | ½ g |

- **Totale**: il nucleo 4–5 giornate; 4½–6 con F-W. Rischio alto, contenuto dalla guardia.
- Sostituisce le 2,5–4 giornate di §16.2, che non contavano storie, contributi, B13 e i port dei test.

### 17.9 Test e gate

- Nuovo `test_financial_math/test_native_cash.py`. Il runner `services financial-math` raccoglie già la cartella (`scripts/test_runner/_backend_services.py:570-578`): nessuna registrazione. Le righe descrittive (`:571-574`) nominano solo il costo medio: il ritocco del solo testo è concesso dentro F (§0). *(Fatto in F-5, §15. La seconda descrizione, `:1070`, approvata dal coordinatore il 2026-10-12, è poi passata a T con T-1, che riscrive la voce `financial-math` del runner: §15, «T8 / F-C3».)*
- Casi nuovi del motore in `test_portfolio_engine/`.
- `test_daily_state_builder.py:549-578` non cambia: un giorno solo, o il cambio mancante.
- Gate sulla 6157, un comando alla volta:
  - `services financial-math`, `services roi-fifo-utils`, `services portfolio-engine`, `services ai-export`, `api portfolio`;
  - `front build --debug`, poi `front-portfolio dashboard`, `front-broker detail`, `front-broker list`;
  - `mkdocs build`, `mkdocs check-links`, `mkdocs translate-validate`.

### 17.10 CHANGELOG e devWiki proposti

- 🐛 «Cash held in a foreign currency is now revalued every day: exchange-rate gains and losses on cash count in value and P&L, and the headline cash equals the sum of the broker cards.»
- F-W, un ✨, nella forma decisa dal coordinatore: «The Performance view lists exchange-rate results on cash as their own row». (Proposta superata: «The P&L waterfall shows exchange-rate results on cash as their own item.»)
- devWiki: la decisione «One home for financial math» guadagna `native_cash` accanto ad `average_cost`; la pagina di G1a nota che la deriva di B4 è chiusa.

### 17.11 Decisioni chieste al developer

1. **Portata di F**: le voci «F» di §17.6, con la stima di §17.8.
2. **F-W**: (i) la voce nuova nel waterfall, consigliata; (ii) il risultato resta nell'«Other», con una nota nella doc.
3. **K/R**: k2, consigliata.
4. **B9**: U9 o un lotto a parte; oppure la sola quota (il bug di EDITOR e VIEWER) dentro F, ¼ g in più.
5. **Cambio mancante**: la politica (a), consigliata.
6. **Le U di T**: X5 ~ U1, O2 ~ U3, P1 e R1–R3 ~ U4, R4/B8/V2/P2 ~ U5, L1/L2 ~ U6, W1 ~ U7, KpiSection ~ U8, B9 ~ U9. O2 e X5 sui giri del portafoglio li chiude F, quindi escono dalle U di T. Da riconciliare con T.

**Esito (2026-10-11, §0)**, dal developer via il coordinatore:
1. Portata: le voci «F» di §17.6. ✅
2. F-W: la (i), nella **forma minima**: una riga «FX on cash» negli `other_effects` dei contributi, senza schema nuovo né KpiSection (§17.8). Il nome nell'AI Export è facoltativo: prima il costo (F-AI).
3. K/R: k2. ✅
4. B9: dopo la 1.2, a T in U3. La descrizione è corretta in §14.
5. Cambio mancante: la politica (a). ✅
6. Mappa delle U: riconciliata dal coordinatore col piano di T (§17.6).
