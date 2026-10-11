# Piano — fase 00, 41: il P&L per broker senza salti ai trasferimenti

> **Stato**: 🚧 in esecuzione dal 2026-10-10. Avanzamento in §15.
>
> - **Dal 2026-10-11 il lotto ha tre consegne** (§0):
>   1. il checkpoint 1, col solo engine (T5a, treno 32);
>   2. poi H, cioè la card dal motore (T2f e T5b);
>   3. poi l'analisi di F (T7).
> - **Aperti**: T5b (READY, alla verifica del coordinatore), T7. T1d e T2g sono chiusi dal 2026-10-11 (§15): un reperto trovato preparando T5b, solo nella chiamata diretta di `get_summary`, senza effetto in produzione.
> - **Checkpoint 1 nel target** (2026-10-11): `883681766`, `3801cf93e`, `5c4c2c0e8`, fusi come `46272c3f0`; treno 32, `dev_release2` = `b20eac991`. H pronto il 2026-10-11 (T5b).
>
> - **Mandato**: coordinatore di Release 2 (`c8328a01-…`), con le decisioni del developer (§1) e l'autorizzazione testuale (§0).
> - **Workstream I**. Ramo `e-alfy-performance-charts-plan`, base `d59762e0a` (treno 30, fast-forward del developer a worktree pulita, verificata il 2026-10-10). L'analisi è stata fatta su `fbb57eb41` (treno 28) e riverificata su `e32f47133` (treno 29, la base del kickoff). I treni 29 e 30 non toccano le superfici del lotto (§8).
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
| T5b | Checkpoint 2, H: T2f, i rossi di T1b, T1c e T1d, T2g, T3b, il resto di T4 | ✅ READY 2026-10-11 (§15), alla verifica del coordinatore |
| T6 | Proposta per la devWiki (§13) | ✅ 2026-10-11, proposta completa in §13, card compresa; la archivia il coordinatore o lo storico |
| T7 | Analisi di F, prima del codice (§0): la cassa nativa rivalutata (B4) e i flussi del periodo nel motore, con la guardia sui portafogli con la sola valuta base | ⏳ dopo T5b |

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

## 12. CHANGELOG proposto (lo scrive il coordinatore)

- 🐛 **Fixed**: broker lines in the P&L chart no longer jump when money or securities move between two of your brokers; the total is unchanged.
- 🔄 **Changed**: in a view filtered to some brokers, securities sent to or received from a broker outside the filter count as capital at market value, not as a gain or a loss. The same applies to the leftover half of a transfer whose other broker was deleted.
- Treno 32 (checkpoint 1, T5a): la riga Fixed non nomina le card. «…and broker cards» entra con H (T5b).
- H (T5b), proposta per la riga Fixed: «Broker lines in the P&L chart and the broker cards no longer jump when money or securities move between two of your brokers; the total is unchanged. While a transfer is on its way, its value stays on the sending broker's card.»

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

- **B1**: rendere visibile l'avviso sulle quote diverse.
- **B2**: coppie invertite.
- **B3**: K/R delle gambe esterne e normali.
- **B4**: la cassa in valuta estera non viene mai rivalutata. Il registro dell'engine (`portfolio_engine.py:723-731`) somma ogni movimento al cambio della sua data, quindi il guadagno o la perdita di cambio sulla cassa non entra mai nel NAV né nel P&L: né a riposo, né quando la valuta si spende in un BUY o si riconverte con un FX_CONVERSION. La cassa in viaggio invece è al cambio del giorno (`book-value.en.md:23`). Ingrandito dall'inventario, §16.2. **Nella 1.2, dentro F (2026-10-11, §0); analisi in T7.**
- **B8**: `get_positions_contribution` (`portfolio_service.py:1711-2104`) ha un suo prezzo (`_get_price_at_date`, `:522`: ultima chiusura, senza ripiego sull'ultimo scambio né split) e, su un TRANSFER fra broker, sposta l'unrealized al costo: il mittente segna −ug_start, il destinatario tutto l'unrealized dall'acquisto. La somma delle righe è giusta. Da valutare in T7: dentro F o dopo (§0).
- **B9**: AI Export, reddito (`ai_export/components/portfolio_income.py:355`) e turnover (`broker_cost_efficiency.py:152-158`, `:341-359`) applicano la quota grezza senza ruolo. EDITOR e VIEWER hanno quota 0 per schema (`schemas/brokers.py:364`), mentre engine e servizio usano 1 (`portfolio_engine.py:2381`). Il reddito usa `abs` (`portfolio_income.py:379`) e la docstring (`:335-336`) dice di rispecchiare `period_income`, che invece ha il segno (`portfolio_service.py:813-814`). Da valutare in T7: dentro F o dopo (§0).
- **B10**: `GrowthChart.svelte:594-600`, `periodBasePnl` dichiarato e mai usato.
- **B5**: nel waterfall, una voce per i trasferimenti al valore di mercato.
- **B6**: coppie ADJUSTMENT coi flussi al valore di mercato (oggi, se di più giorni, un intervallo «cash» a valore 0).
- **B7**: uno split durante il viaggio.
- **B11**: il salto dei giorni ignora i cambi. `dirty_days` (`portfolio_engine.py:868-905`) raccoglie transazioni, flussi, bordi dei viaggi, prezzi e split, ma non le date dei cambi: in un giorno in cui si muove solo il cambio, le posizioni in valuta e la cassa in viaggio restano al valore del giorno prima. Trovato dal test-author sul caso 3 (d2). Preesistente, fuori dal lotto.
- **B12** (2026-10-11, righe del codice di H), latente: le righe con data futura in una chiamata diretta senza `date_to`. Lì il motore si ferma a oggi, ma due letture del servizio tengono tutte le righe del broker:
  - `_signed_transaction_sums_by_date` (`portfolio_service.py:1533`), per le storie di redditi, costi e depositi;
  - `get_positions_contribution` (`:1775`).
  - Nessun effetto in produzione: `get_report` passa sempre `effective_date_to` (`:2120`, `:2299-2372`). In `get_summary` lo stesso caso lo ripara T2g (§15 T1d/T2g). Da riguardare in T7, la seconda insieme a B8.
  - Nessuna validazione impedisce una data futura. Se debba esserci, è una scelta di prodotto fuori dal lotto.

## 15. Avanzamento

> **Righe citate**: ogni nota cita il codice del suo momento.
> - Da T0 a T1/T1b, e le sezioni scritte allora (§4, §5, §14, §16): `d59762e0a`. Lì `portfolio_service.py` è identico a `b20eac991`.
> - Da T2a–T2e a T1c: `b20eac991`, cioè il motore del checkpoint 1. Vale anche per i punti di §16 corretti in T1c.
> - Da T2f in poi, e i punti di §16.2 rivisti per T2f: il codice di H, quello del checkpoint 2 (T5b).

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

### T5b — Checkpoint 2, H ✅ READY (2026-10-11)

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
| 11 | Frontend | `BrokerCard.svelte:146-189` e `KpiSection.svelte` leggono soltanto | nessun calcolo |

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
- **Opzione F**: prima B4 intero nel motore (registro nativo per broker e valuta, rivalutato ogni giorno; preload dei cambi; pool K/R; una voce nuova nel waterfall, quindi schema, frontend e i18n; golden di TWRR/MWRR, candele e AI Export). Stima 2,5–4 giornate, rischio alto. Consiglio un lotto a parte dopo il 41: allora lo scambio di H vale zero.
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
