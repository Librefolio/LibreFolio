# Piano D — Round 5 · C0: delta ASCII della UI PAC 2.0.0 rispetto al target

> **Stato**: ✅ approvato dal developer il 24/09/2026 (Q-C0-F): «ho letto il piano e guardato le ascii
> mi paiono coerenti, quello che avevamo pianificato in origine, hai il mio via libera, ovviamente poi
> faremo la review». Le decisioni sulle domande di §8 sono in §8.1.1.
> **Data**: 2026-09-24 · **Baseline**: `f1047f766` · **Workstream**: D (allocatore PAC)
> **Piano padre**: [`plan-phase00PacRound5PostMerge.prompt.md`](plan-phase00PacRound5PostMerge.prompt.md), Passo C0
> **Target approvato**: [`../plan-phase00PacRebalancerUiTarget.prompt.md`](../plan-phase00PacRebalancerUiTarget.prompt.md)
> **Wire misurato**: `backend/app/schemas/pac_allocator.py`, `backend/app/schemas/portfolio.py`, `backend/app/schemas/tools.py`

Questo documento **non** ridisegna la UI. Prende il target approvato e segna, voce per voce, cosa il
backend 2.0.0 permette davvero di mostrare. Le voci senza supporto sul wire restano nel target:
qui sono marcate `−` e rimandate, mai simulate nel frontend.

### Registro delle modifiche dopo l'approvazione (24/09/2026)

Il developer ha approvato il delta e ha deciso le domande Q-C0-1…7 (§8.1.1). Le schermate sono state
riallineate a quelle decisioni; il resto non è cambiato.

| Decisione | Dove | Modifica |
|---|---|---|
| Q-C0-1 | §3.2 conto manuale; W2, W20, N18 | Il passo minimo della valuta non si chiede più: lo ricava il backend dalle cifre CLDR. |
| Q-C0-2 | §3.2 riepiloghi; §3.6; §5.3 | I riepiloghi della liquidità contano fonti, casse e contributi invece di sommare importi. Totale e restante del target sono etichettati come controllo. |
| Q-C0-3 | §3.4, §3.7, §3.9 | Spariscono i pulsanti «Conferma» e i `!` sui dati non del giorno; resta l'età in giorni. |
| Q-C0-4 | §3.8 | Niente annuncio della minima frammentazione: le strategie arrivano dal contratto. |
| Q-C0-5 | §3.5, §6 | Il tetto delle route parte da `1.000.000.000` quote, modificabile. |
| Q-C0-6 | §3.6 | Nuovo pulsante «Copia distribuzione corrente» e nuovo dialogo. |
| Q-C0-7 | §3.4 editor; W7, N22 | L'editor dichiara che una somma oltre il 100% viene rifiutata dal backend. |

---

## 0. Come leggere

| Segno | Significato |
|---|---|
| `=` | come nel target |
| `Δ` | c'è, ma diverso dal target (motivo nella colonna Nota) |
| `+` | nuovo in 2.0.0, il target non lo prevedeva |
| `−` | nel target, assente in 2.0.0: rimandato, non simulato |
| `?` | decisione aperta: domanda in §8 (dopo il 24/09 nessuna riga lo usa più) |

| Marcatore ASCII | Significato |
|---|---|
| `[C]` | fatto copiato da un'API di dominio (Portfolio, Asset, FX) |
| `[M]` | inserito a mano nel draft |
| `[B]` | calcolato dal backend |
| `•••` | valore mascherato dalla privacy (formatter di J, `maskable.ts`) |
| `≈` | valore esatto ma non decimale (`exact_ratio`): la UI mostra `display_decimal` arrotondato. Con la privacy ON resta fuori dalla maschera: `≈••• € EUR` |

- **Solo dati sintetici**: Broker Demo A/B/C; Asset MOND, OBBL, EMER, NUOV. Nessun dato del developer.
- **Larghezze**: desktop 110 colonne, mobile 34. Ogni blocco è generato e controllato per larghezza.
- **Importi**: la forma è quella di `formatCurrencyAmountPlain` (`utils/currency/currencyFormat.ts:33-80`),
  cioè `1.210,00 € EUR`. La bandiera è omessa nell'ASCII. Con la privacy ON diventa `••• € EUR`.

### 0.1 Lo scenario testimone

Un solo scenario attraversa quasi tutte le schermate. La sua aritmetica è verificata a mano con
frazioni esatte. **Non è un golden del solver**: serve a rendere credibili le schermate.

| Voce | Valore |
|---|---|
| Scenario | 23/09/2026 · valuta di riferimento EUR · quantum EUR e USD 0,01 (dal backend, cifre CLDR) |
| Liquidità | Demo A, cassa EUR 1.200,00 `[C]` (custodia = quota tua, 100%) + contributo «Risparmio settembre» 800,00 EUR `[M]` |
| Funding | route contributo → Demo A · EUR, priorità 0, tetto 800,00 |
| Modalità | Demo A · EUR e Demo A · USD, quote intere, passo 1, commissione 0 |
| Asset | MOND 110,00 EUR `[C]` del 22/09, 1 giorno prima · OBBL 5,00 EUR `[C]` · EMER 30,00 USD `[M]` · NUOV senza prezzo `[C]` |
| FX | EUR/USD 1,1000 `[C]` del 22/09, 1 giorno prima · spread globale 0,25% |
| Target | MOND 60% · OBBL 30% · EMER 10% (NUOV rimosso a mano prima del calcolo) |
| Piano | MOND 11 = 1.210,00 EUR · OBBL 119 = 595,00 EUR · EMER 7 = 210,00 USD |
| FX | addebito 191,39 EUR → accredito 210,00 USD · effettivo 1,09725 · perdita spread ≈0,48 EUR |
| Contabilità | riferimento 2.000,00 · investito ≈1.995,91 · U ≈4,09 = libera 3,61 + perdite ≈0,48 + arrotondamento 0 |
| Scarto L2 | 10² + 5² + (100/11)² ≈ 207,64 EUR² |
| Pesi finali | MOND ≈60,62% · OBBL ≈29,81% · EMER ≈9,57% |
| Prova | `not_proven` (SCIP): il dominio supera 200.000 candidati per le decisioni di funding al centesimo |

Un secondo scenario, minimo, mostra una prova esatta: 1.000,00 EUR, MOND con tetto 10 quote, OBBL con
tetto 200 quote, target 70/30. Sono 11 × 201 = 2.211 candidati, 1.020 ammissibili. L'ottimo è MOND 6 +
OBBL 60, con L2 1.600,00 EUR² e 40,00 EUR non investiti. Oracolo esaustivo, quindi `optimal_proven`.

---

## 1. Fatti del wire 2.0.0 usati da questo delta

| # | Fatto | Evidenza |
|---|---|---|
| W1 | L'input del plugin è solo `PacPlannerRequest` | `tool_plugins/pac_allocator.py:43,113,126` |
| W2 | Campi dello scenario: `snapshot`, `as_of`, `valuation_currency`, `currency_specs`, `provenance`, `fx_rates` (chiave `AAA/BBB`), `fx_spread_rate` **globale**, `assets`, `brokers`, `existing_cash`, `contributions`, `funding_routes`, `target_weights`, `order_routes`, `policy` | `schemas/pac_allocator.py:727-759`. Dopo C0b: senza `currency_specs` (Q-C0-1), `policy` solo `proportional` (Q-C0-4) |
| W3 | Cassa esistente: `source_kind local_broker_cash\|manual_cash`, `available`, `selected` | `:578-583` |
| W4 | Contributo: `contribution_id`, `label`, `amount` | `:585-589` |
| W5 | Route di funding: sorgente cassa o contributo → Broker × valuta, `priority`, `transfer_cap` | `:595-617` |
| W6 | Route d'ordine: `priority`, `minimum_if_active`, `required_minimum`, `cap` **obbligatorio**, `execution_margin_rate`, `fee_schedule_id` | `:658-672` |
| W7 | Esposizioni in input: `dimension ∈ asset_type\|sector\|geography`, peso in [0,1]; dopo C0b anche la somma per Asset e dimensione ≤ 1 (Q-C0-7) | `:484-490`; normalizer `normalize.py:258-274` |
| W8 | Numeri esatti: `finite_decimal` o `exact_ratio` con `display_decimal` non autoritativo | `:790-880` |
| W9 | Stati PAC: `needs_input`, `invalid`, `unsupported`, `ready_no_op`, `ready_incumbent`, `ready_infeasible`, `ready_no_incumbent` | `:2369-2395`, `:2433-2460` |
| W10 | Un piano con ordini è `ready_incumbent` + `incumbent_found`; la prova è a parte: `optimal_proven`, `gap_bounded` o `not_proven` | `:2441-2447`, `:1217-1297` |
| W11 | Righe del risultato: Asset, funding, FX, ordine BUY, ledger, esposizioni, contabilità, costi, obiettivi | `:1351`, `:1374`, `:1385`, `:1465`, `:1583`, `:1640`, `:1678`, `:1694`, `:1703` |
| W12 | Cascata `proportional`: `fixed_l2 → shortfall → route_priority → explicit_cost → active_order_rows`, spareggio `canonical_key` | `objectives.py:9,235-243` |
| W13 | Fino a 200.000 candidati decide l'oracolo esaustivo e il solver non gira (`allocation.solver_not_required`) | `oracle.py:61`, `planner.py:210,310` |
| W14 | Le tre dimensioni di esposizione escono sempre; la quota non dichiarata diventa la riga `allocation.uncategorised` | `planner_report.py:104,107,290,346-381` |
| W15 | Riga ordine: `fx_cost` sempre 0 nella valuta di riferimento, `buffer` sempre 0, `explanation_keys` sempre vuoto | `planner_report.py:564-570` |
| W16 | Deployment sempre `unavailable{allocation.deployment_omitted}` | `planner.py:108-112` |
| W17 | Sorgente di copia v2: `POST /portfolio/allocation-source`, `broker_ids` con almeno 1 elemento, solo Broker `OWNER`; dopo C0b anche la sezione `current_distribution` (Q-C0-6) | `schemas/portfolio.py:1263-1285,1367-1384` |
| W18 | Cassa copiata: `custody_amount`, `ownership_share`, `economic_amount` | `schemas/portfolio.py:1399-1408` |
| W19 | Classificazioni copiate: `category_id`, `label`, `weight` annullabili; la riga incompleta resta con il suo issue | `schemas/portfolio.py:1425-1433` |
| W20 | Alla baseline `minor_unit` arriva solo dalla sorgente di copia. **Superato da Q-C0-1**: lo ricava il backend da babel, e la copia non lo porta più | `schemas/portfolio.py:1322-1326` (alla baseline) |
| W21 | Errori di piattaforma: 16 codici `ToolError`, con `retryable` | `schemas/tools.py:28-45,231-235` |
| W22 | Tempi per fase: annullabili, «unobserved phases are null, never invented zeroes» | `schemas/tools.py:250-260` |
| W23 | `runTool` con `signal`: smette di attendere, non annulla il calcolo sul server | `frontend/src/lib/features/tools/client.ts:299-302` |

---

## 2. Delta per voce del target

Le righe citano la sezione del target (`UiTarget:riga`). Le decisioni `Q-C0-n` sono in §8.1.1, i reperti
`Nn` in §9.

### 2.1 Shell e navigazione (serie A)

| Voce | UiTarget | Segno | In 2.0.0 |
|---|---|---|---|
| A0 Tools Hub | `:209` | `Δ` | Card con la descrizione v2 (Passo B). Il banner «interfaccia non disponibile» resta solo per i casi veri. `ToolsHub.svelte` è di D per questo round. |
| A1 Step 1 Scenario | `:237` | `=` `+` | Data e valuta di riferimento. In più una riga: «quantità iniziali zero (PAC puro)», perché il backend rifiuta le holding (`pac_allocator.initial_holding_forbidden`). |
| A3 Densità desktop | `:323` | `=` | Tre colonne: passi, contenuto, riepilogo. |
| A4 Tablet | `:362` | `Δ` | Sotto la soglia desktop si usa il layout mobile. La rifinitura arriva dopo la review (Q1). |
| A5–A7 Mobile | `:397-471` | `Δ` | Vedi §6. Passi in un cassetto, un solo contenuto per schermata. |
| A8 Uscita con draft sporco | `:512` | `=` | Il draft vive in memoria; uscire chiede conferma. |
| A9 Modifica strutturale | `:537` | `=` | Togliere un Broker toglie le sue route, dopo una conferma che le elenca. |

### 2.2 Input (serie B)

| Voce | UiTarget | Segno | In 2.0.0 |
|---|---|---|---|
| B1 Liquidità e fonti | `:703` | `Δ` `−` | Righe di cassa esistente (W3) e contributi (W4). «Importo da usare» parte vuoto, sempre. **`−` Equivalente indicativo**: richiederebbe FX nel frontend. **`−`** Totali nativi per valuta: la UI non somma importi, il riepilogo conta le fonti (Q-C0-2). |
| B2 «Prendi liquidità da…» | `:758` | `Δ` | Sorgente v2 (W17). Un Broker non `OWNER` compare disabilitato, mai tolto. Un 403/404 si vede in chiaro. Uno scenario manuale non ha più bisogno della copia: il quantum lo ricava il backend (Q-C0-1). |
| B3 Fonte manuale | `:789` | `Δ` | Un conto manuale è `manual_cash` su un Broker manuale «solo funding». Un contributo è una voce della lista W4. |
| B4 Conflitto dopo copia | `:826` | `=` | Solo dopo una copia o un refresh esplicito. Nessun legame live. |
| B4 Regola selettori | `:858` | `=` | |
| B4 Regola input numerici | `:871` | `=` | Unità sempre accanto al campo. Separatori della lingua UI. |
| B5 Broker operativi | `:886` | `Δ` `+` `−` | Modalità = Broker × valuta, con capability e tariffa BUY. **`+`** Broker «solo funding». **`−`** regime fiscale e minusvalenze: il PAC non vende. |
| B6 Editor Broker | `:916` | `Δ` `+` `−` | **`+`** `quantity_step` (lotto), che il target escludeva. Una tariffa ha una sola valuta, quella del prezzo (N10). **`−`** FX per Broker (`fx_mode`, N14). |
| B6 Normalizzazione campi | `:955` | `Δ` | `asset_class` in minuscolo prima dell'invio (N12). |
| B7 Asset PAC | `:980` | `Δ` | Prezzo con `quote_base_quantity`, data, fonte; se non è del giorno, l'età in giorni, senza conferma (Q-C0-3). Un prezzo mancante resta nel draft: il backend risponde `needs_input`. |
| B8 Editor Asset manuale | `:1008` | `=` | Funziona senza Asset nel DB. |
| B10 Routing | `:1072` | `Δ` `+` | Priorità: più bassa = preferita (N13). **`+`** `required_minimum` e `minimum_if_active`. **`+`** tetto obbligatorio (N16), precompilato a `1.000.000.000` e modificabile (Q-C0-5). Minimo e tetto seguono la modalità (N11, N21). **`−`** SELL. |
| B10 Editor vincoli tipizzato | `:1123` | `=` | Un tipo per campo, scelto da un selettore. |
| B11 Target PAC | `:1154` | `Δ` `+` | Percentuali in input, decimali sul wire. **`+`** «Copia distribuzione corrente» (Q-C0-6): il target PAC non l'aveva, il B12 del ribilanciatore sì (`:1180,1194`). Totale e restante come controllo informativo (Q-C0-2). |
| B13 FX | `:1199` | `Δ` `−` | Coppie proposte dalle valute in gioco; chiave solo da selettore (N20). Uno spread **globale** (W2). **`−`** margine di sicurezza per coppia, fee di conversione, buffer, multi-hop (❌ non più da fare, developer, 02/10/2026). **`−`** freschezza FX sul wire (N15): età solo in UI, senza conferma (Q-C0-3). |
| B14 Strategia PAC | `:1240` | `Δ` | Solo `proportional`, con la cascata W12. Le card nascono dalle opzioni del contratto; `min_fragmentation` esce dal wire (Q-C0-4). |
| B16 Review snapshot | `:1286` | `=` | Snapshot con id e revisione, conteggi, provenance. |
| B16 Submit | `:1312` | `=` | Un solo invio alla volta. Una risposta vecchia viene scartata. |

### 2.3 Risultato (serie C)

| Voce | UiTarget | Segno | In 2.0.0 |
|---|---|---|---|
| C1 Header | `:1365` | `Δ` `−` | Quattro badge: disponibilità, esito, prova, stop. **`−`** selettore Primario/Variante: 2.0.0 non produce varianti. |
| C2 Overview PAC | `:1425` | `Δ` `−` | Barre target/dopo sui pesi del backend. **`−`** colonna «Delta pp»: sarebbe una sottrazione nel frontend. Lo scarto monetario arriva dal backend (`residual`). |
| C3 Delta soluzione ottimizzata | `:1452` | `−` | Nessuna variante. |
| C4 Esposizioni | `:1474` | `Δ` `+` `−` | Tabelle con le stesse barre per dimensione. **`+`** riga «Non classificato» (W14). **`−`** ribbon ECharts custom e GeographyMap: dopo la review. |
| C5 Asset summary | `:1526` | `Δ` | Da `PacAssetPlanRow`. Nessun «Prima»: nel PAC puro è 0 per costruzione. I totali vengono dalla contabilità, non da somme. |
| C10–C12 Piano operativo | `:1656` | `Δ` `+` | Funding → FX → ordini, nell'ordine `sequence`. Ledger trasposto: una colonna per Broker × valuta. **`+`** funding raggiungibile e intrappolato. Righe SELL e tasse, sempre 0, ripiegate. |
| Sankey | `:1358` | `−` | Dopo la review (Q1). |
| C13 Dettaglio riga | `:1727` | `Δ` `−` | **`−`** spiegazioni del backend (`explanation_keys` vuoto, W15). Il costo FX si legge nell'azione FX, non nel campo della riga. |
| C14 Prova e diagnostica | `:1752` | `Δ` | I tipi di prova reali, gli stadi `reported_floating`, i tempi (null → `n/d`). **`−`** gap: PAC 2.0.0 non emette `gap_bounded` (N8). |
| C15 Confronto base/ottimizzata | `:1805` | `−` | Nessuna variante. |

### 2.4 Mobile e stati (serie D)

| Voce | UiTarget | Segno | In 2.0.0 |
|---|---|---|---|
| D1–D5 Mobile | `:1891-2042` | `Δ` | Vedi §6. |
| D6 Confronto mobile | `:2071` | `−` | Nessuna variante. |
| D7 Busy | `:2094` | `Δ` | «Interrompi attesa» smette di attendere (W23). Il server non viene fermato, e la sua risposta tardiva viene scartata. |
| D8 Invalid locale | `:2117` | `Δ` | Solo controlli di forma e di stessa unità, più le percentuali di controllo del target (Q-C0-2). |
| D9 `needs_input` | `:2133` | `=` | Ogni issue porta al suo passo. |
| D10 `unsupported` | `:2152` | `=` | |
| D11 `no_op` | `:2168` | `=` | |
| D12 `infeasible_proven` | `:2189` | `Δ` | Solo prove da oracolo (N8). La UI elenca i vincoli rigidi coinvolti e non sceglie quale rompere. |
| D13 Incumbent con limite | `:2212` | `Δ` | Nessun gap certificato (N8). |
| D14 Limite senza incumbent | `:2229` | `=` | Nessun «Riprova» con gli stessi input. |
| D15 Risultato stale | `:2242` | `=` | |
| D16 Cambio sessione | `:2260` | `=` | |
| Errore di piattaforma | — | `+` | Pannello per i 16 `ToolError`, con messaggi PAC-locali (N17). «Riprova» solo se `retryable`. |
| Matrice stati | `:2279` | `Δ` | Vedi §5.1: quali stati 2.0.0 produce davvero, quali solo da fixture. |

---

## 3. Desktop — wizard in nove passi

Il riepilogo a destra mostra solo conteggi e stati. Nessun valore futuro, nessuna conversione.

### 3.1 Passo 1 — Scenario (A1, `=` `+`)

```text
+--------------------+----------------------------------------------------------------+----------------------+
| PASSI              | SCENARIO                                                       | RIEPILOGO            |
| > 1  Scenario      | Allocatore PAC · quantità iniziali zero (PAC puro).            | Data    23/09/2026   |
| ○ 2  Liquidità     |                                                                | Valuta  EUR          |
| ○ 3  Broker        | Data di riferimento *    [ 23/09/2026 ]                        |                      |
| ○ 4  Asset         | Valuta di riferimento *  [ EUR - Euro                v ]       | Backend/API 2.0.0    |
| ○ 5  Routing       |                                                                | UI 2.0.0             |
| ○ 6  Target        | [i] Nessun valore finanziario in questo passo.                 |                      |
| ○ 7  FX            |                                                                |                      |
| ○ 8  Strategia     |                                                                |                      |
| ○ 9  Rivedi        |                                                                |                      |
+--------------------+----------------------------------------------------------------+----------------------+
|                                                                                            [ Continua -> ] |
+------------------------------------------------------------------------------------------------------------+
```

### 3.2 Passo 2 — Liquidità (B1, `Δ` `−`)

Privacy OFF: gli input sono in chiaro, perché l'utente li sta scrivendo.

```text
+--------------------+----------------------------------------------------------------+----------------------+
| PASSI              | LIQUIDITÀ                                      privacy: OFF    | RIEPILOGO            |
| v 1  Scenario      | Scegli quale liquidità entra nel piano. Il resto resta fuori.  | Fonti          2     |
| > 2  Liquidità     | [ Copia liquidità dai Broker ] [ + Contributo ] [ + Manuale ]  | Casse          1     |
| ○ 3  Broker        | +------------------------------------------------------------+ | Contributi     1     |
| ○ 4  Asset         | | Demo A · cassa EUR                         [C] 23/09 14:02 | | Valute       EUR     |
| ○ 5  Routing       | | Disponibile (custodia)   1.200,00 € EUR · 100% tua         | |                      |
| ○ 6  Target        | | Importo da usare *     [ 1.200,00 ] EUR                    | |                      |
| ○ 7  FX            | | Nessun precompilato: l'importo lo scrivi tu.               | |                      |
| ○ 8  Strategia     | +------------------------------------------------------------+ |                      |
| ○ 9  Rivedi        | +------------------------------------------------------------+ |                      |
|                    | | Risparmio settembre · contributo                       [M] | |                      |
|                    | | Importo *  [ 800,00 ] EUR   Etichetta [ Risparmio sett. ]  | |                      |
|                    | | Destinazione: route di funding nel passo Broker.           | |                      |
|                    | +------------------------------------------------------------+ |                      |
|                    | [i] Nessun equivalente convertito: FX solo nel backend.        |                      |
+--------------------+----------------------------------------------------------------+----------------------+
| [ <- Indietro ]                                                                            [ Continua -> ] |
+------------------------------------------------------------------------------------------------------------+
```

Privacy ON: i campi di input restano leggibili mentre li modifichi; le visualizzazioni in sola
lettura si mascherano. Il riepilogo conta fonti, casse e contributi: nessuna somma di importi (Q-C0-2).

```text
+--------------------+----------------------------------------------------------------+----------------------+
| PASSI              | LIQUIDITÀ                                       privacy: ON    | RIEPILOGO            |
| v 1  Scenario      | +------------------------------------------------------------+ | Fonti          2     |
| > 2  Liquidità     | | Demo A · cassa EUR                         [C] 23/09 14:02 | | Casse          1     |
| ○ 3  Broker        | | Disponibile (custodia)   ••• € EUR · 100% tua              | | Contributi     1     |
| ○ 4  Asset         | | Importo da usare *  [ 1.200,00 ] EUR  <- input in chiaro   | | Valute       EUR     |
| ○ 5  Routing       | +------------------------------------------------------------+ |                      |
| ○ 6  Target        | +------------------------------------------------------------+ |                      |
| ○ 7  FX            | | Risparmio settembre · contributo                       [M] | |                      |
| ○ 8  Strategia     | | Importo *  [ 800,00 ] EUR             <- input in chiaro   | |                      |
| ○ 9  Rivedi        | +------------------------------------------------------------+ |                      |
+--------------------+----------------------------------------------------------------+----------------------+
| [ <- Indietro ]                                                                            [ Continua -> ] |
+------------------------------------------------------------------------------------------------------------+
```

Copia dai Broker (B2). Ogni Broker × valuta diventa una riga; nessun importo viene precompilato.

```text
+--------------------------------------------------------------------------------------+
| Copia liquidità dai Broker                                                       [x] |
+--------------------------------------------------------------------------------------+
| Fonte: API Portfolio (allocation-source) · al 23/09/2026 · solo Broker OWNER.        |
|                                                                                      |
| [v] Demo A                     EUR  custodia ••• € EUR · 100% tua                    |
|                                USD  nessun saldo in USD                              |
| [ ] Demo B · quota 50%         EUR  custodia ••• € EUR · quota tua ••• € EUR         |
| [-] Demo C                          Non selezionabile: accesso VIEWER, non letto     |
|                                                                                      |
| Ogni Broker × valuta diventa una riga. 'Importo da usare' resta vuoto: lo scrivi tu. |
| Un 403/404 dell'API compare qui in chiaro; nessun Broker viene tolto in silenzio.    |
|                                                                                      |
| [ Annulla ]                                                         [ Copia 1 riga ] |
+--------------------------------------------------------------------------------------+
```

Fonte manuale (B3). Senza Asset né Broker nel DB, il Tool funziona lo stesso. Il passo minimo della
valuta lo ricava il backend (Q-C0-1).

```text
+------------------------------------------------------------------------+
| Aggiungi conto manuale                                             [x] |
+------------------------------------------------------------------------+
| Nome conto *                  [ Banca non configurata        ]         |
| Valuta *                      [ EUR v ]                                |
| Liquidità dichiarata *        [ 5.000,00 ] EUR   limite, non grafico   |
| Importo da usare *            [ 2.000,00 ] EUR   <= dichiarata         |
| [i] Il passo minimo della valuta lo ricava il backend (CLDR).          |
|                                                                        |
| Nello scenario il conto diventa un Broker 'solo funding':              |
| nessun ordine parte da qui; serve una route verso un Broker.           |
|                                                                        |
| [ Annulla ]                                         [ Aggiungi fonte ] |
+------------------------------------------------------------------------+
```

Conflitto dopo una copia esplicita (B4). Mai un aggiornamento live.

```text
+----------------------------------------------------------------------------------+
| Demo A è cambiato dall'ultima copia                    privacy: ON           [x] |
+----------------------------------------------------------------------------------+
| Hai chiesto 'Copia di nuovo'. Il saldo EUR ora è diverso:                        |
|                                                                                  |
| Saldo copiato nel draft · 23/09 14:02                 ••• € EUR                  |
| Saldo dal sistema · 23/09 16:40                       ••• € EUR                  |
| Importo da usare (tuo)                             [ 1.200,00 ]  [non cambia]    |
|                                                                                  |
| Aggiornando cambia solo il fatto copiato e la sua data. I tuoi campi restano.    |
|                                                                                  |
| [ Mantieni copia precedente ]                         [ Aggiorna fatto copiato ] |
+----------------------------------------------------------------------------------+
```

### 3.3 Passo 3 — Broker (B5–B6, `Δ` `+` `−`)

```text
+--------------------+----------------------------------------------------------------+----------------------+
| PASSI              | BROKER SU CUI OPERARE                                          | RIEPILOGO            |
| v 1  Scenario      | Dove il backend può proporre acquisti. Nessun salvataggio.     | Broker         1     |
| v 2  Liquidità     | [ Scegli Broker esistente ] [ + Broker manuale ]               | Solo funding   1     |
| > 3  Broker        | +------------------------------------------------------------+ | Modalità       2     |
| ○ 4  Asset         | | Demo A                                     [C] 23/09 14:02 | | Route funding  1     |
| ○ 5  Routing       | | EUR: quote intere · passo 1 · commissione BUY 0            | |                      |
| ○ 6  Target        | | USD: quote intere · passo 1 · commissione BUY 0            | |                      |
| ○ 7  FX            | | Conversioni: tasso globale + spread (passo FX)             | |                      |
| ○ 8  Strategia     | | Funding: cassa locale EUR + Risparmio settembre            | |                      |
| ○ 9  Rivedi        | | [ Modifica ] [ Rimuovi ]                                   | |                      |
|                    | +------------------------------------------------------------+ |                      |
|                    | +------------------------------------------------------------+ |                      |
|                    | | Banca non configurata                     [M] solo funding | |                      |
|                    | | Nessun ordine: finanzia altri Broker via route.            | |                      |
|                    | +------------------------------------------------------------+ |                      |
+--------------------+----------------------------------------------------------------+----------------------+
| [ <- Indietro ]                                                                            [ Continua -> ] |
+------------------------------------------------------------------------------------------------------------+
```

L'editor mostra una modalità per valuta. La tariffa ha la stessa valuta del prezzo (N10).

```text
+------------------------------------------------------------------------------------------------------+
| Configura Demo A · dati dello scenario (il Broker non viene modificato)                          [x] |
+------------------------------------------------------------------------------------------------------+
| ORIGINE  [C] Broker esistente · copia 23/09/2026 14:02 · [ Ripristina valori copiati ]               |
|                                                                                                      |
| MODALITÀ D'ORDINE (una per valuta)                                                                   |
| Val.  Nel Broker inserisci     Passo            Commissione BUY (nella valuta della modalità)        |
| EUR   [ Numero di quote v ]    [ 1 ] quote      fissa [ 0,00 ] + [ 0 ]% · min [ 0,00 ] · max [ — ]   |
| USD   [ Numero di quote v ]    [ 1 ] quote      fissa [ 0,00 ] + [ 0 ]% · min [ 0,00 ] · max [ — ]   |
|       ( Importo )              [ 0,01 ] EUR     valuta del passo = valuta della modalità, bloccata   |
| [ + Aggiungi valuta ]                                                                                |
| [i] Commissione = 0 se l'importo è 0, altrimenti fissa + clamp(tasso × importo, min, max).           |
|                                                                                                      |
| FUNDING AMMESSO VERSO DEMO A                                                                         |
| [v] Cassa locale Demo A EUR · nessun trasferimento                                                   |
| [v] Risparmio settembre EUR -> Demo A EUR · priorità [ 0 ] · tetto [ 800,00 ] EUR                    |
|                                                                                                      |
| Non presenti in 2.0.0: gestione FX per valuta, regime fiscale, minus, commissioni SELL.              |
|                                                                                                      |
| [ Annulla ]                                                                     [ Applica al draft ] |
+------------------------------------------------------------------------------------------------------+
```

### 3.4 Passo 4 — Asset (B7–B8, `Δ`)

NUOV resta nel draft anche senza prezzo. Se l'utente non lo toglie, il backend risponde
`needs_input` (§5, D9). Nessun Asset sparisce in silenzio. Un prezzo non del giorno mostra la sua età;
la scelta di usarlo resta all'utente, senza conferma (Q-C0-3).

```text
+--------------------+----------------------------------------------------------------+----------------------+
| PASSI              | ASSET DA ACQUISTARE                                            | RIEPILOGO            |
| v 1  Scenario      | [ Cerca Asset ] [ + Asset manuale ] [ Copia prezzi ]           | Asset          4     |
| v 2  Liquidità     | [ Copia classificazioni ]                                      | Prezzi       3/4 !   |
| v 3  Broker        | +------------------------------------------------------------+ | Non del giorno 1     |
| > 4  Asset         | | MOND Azionario Mondo · etf                             [C] | | Esposizioni  3/4     |
| ○ 5  Routing       | | 110,00 € EUR / 1 quota · 22/09 · 1 giorno prima del 23/09  | |                      |
| ○ 6  Target        | +------------------------------------------------------------+ |                      |
| ○ 7  FX            | +------------------------------------------------------------+ |                      |
| ○ 8  Strategia     | | OBBL Obbligazionario · etf                             [C] | |                      |
| ○ 9  Rivedi        | | 5,00 € EUR / 1 quota · 23/09 · del giorno                  | |                      |
|                    | +------------------------------------------------------------+ |                      |
|                    | +------------------------------------------------------------+ |                      |
|                    | | EMER Emergenti · etf                                   [M] | |                      |
|                    | | 30,00 $ USD / 1 quota · 23/09 · inserito a mano            | |                      |
|                    | +------------------------------------------------------------+ |                      |
|                    | +------------------------------------------------------------+ |                      |
|                    | | NUOV Nuovo fondo · etf                             [C] [!] | |                      |
|                    | | Prezzo mancante: resta nel draft, il calcolo lo chiederà.  | |                      |
|                    | +------------------------------------------------------------+ |                      |
+--------------------+----------------------------------------------------------------+----------------------+
| [ <- Indietro ]                                                                            [ Continua -> ] |
+------------------------------------------------------------------------------------------------------------+
```

```text
+----------------------------------------------------------------------------------------------+
| Asset manuale                                                                            [x] |
+----------------------------------------------------------------------------------------------+
| IDENTITÀ                                                                                     |
| ID strumento *   [ ISIN o ID univoco dello scenario ]   Nome * [ Emergenti          ]        |
| Ticker           [ EMER ]        Classe * [ etf v ]  (codice minuscolo)                      |
| [i] Mai unire Asset per nome: lo stesso ID riusa la stessa identità nel draft.               |
|                                                                                              |
| PREZZO                                                                                       |
| Prezzo *  [ 30,00 ]  Valuta * [ USD v ]  Quote per prezzo * [ 1 ]  Data * [ 23/09/2026 ]     |
|                                                                                              |
| ESPOSIZIONI (facoltative)                                                                    |
| asset_type   [ equity  ] [ Azionario ]      [ 100 ]%                                         |
| geography    [ asia    ] [ Asia      ]      [ 100 ]%                                         |
| La quota non dichiarata va nella riga 'Non classificato' del backend.                        |
| Somma oltre il 100% in una dimensione: il backend la rifiuta come input non valido.          |
|                                                                                              |
| [ Annulla ]                                                             [ Applica al draft ] |
+----------------------------------------------------------------------------------------------+
```

### 3.5 Passo 5 — Routing (B10, `Δ` `+`)

Il tipo di minimo e di tetto dipende dalla modalità. Con quote intere si scrivono quote, con
«importo» si scrive un importo. Il tetto è obbligatorio in 2.0.0 (N16): parte da `1.000.000.000`
nell'unità della modalità, e l'utente lo abbassa se vuole (Q-C0-5). Il valore alto non allarga la
ricerca: il limite effettivo di ogni ordine è il minimo fra tetto e risorse.

```text
+--------------------+----------------------------------------------------------------+----------------------+
| PASSI              | ROUTING · MOND Azionario Mondo                                 | RIEPILOGO            |
| v 1  Scenario      | Dove può essere comprato ciascun Asset, con quali vincoli.     | Asset con route 3/3  |
| v 2  Liquidità     | [ < Asset precedente ]                  [ Asset successivo > ] | Route BUY      3     |
| v 3  Broker        | +------------------------------------------------------------+ |                      |
| v 4  Asset         | | [v] Demo A · EUR · quote intere · passo 1           pronta | |                      |
| > 5  Routing       | | Priorità            [ 0 ]   0 = preferita (N13)            | |                      |
| ○ 6  Target        | | Minimo se operi     [ Nessuno v ]                          | |                      |
| ○ 7  FX            | | Minimo obbligatorio [ Nessuno v ]                          | |                      |
| ○ 8  Strategia     | | Tetto *             [ Quantità ] [ 1.000.000.000 ] quote   | |                      |
| ○ 9  Rivedi        | |                     predefinito alto, modificabile         | |                      |
|                    | | Margine esecuzione  [ 0,00 ]%                              | |                      |
|                    | | Commissione         BUY EUR di Demo A · 0                  | |                      |
|                    | +------------------------------------------------------------+ |                      |
|                    | [i] Minimo e tetto seguono la modalità: quote per 'quote       |                      |
|                    |     intere', importo per 'importo'. Nessuna scelta libera.     |                      |
|                    | [ ] Banca non configurata · solo funding, non selezionabile    |                      |
+--------------------+----------------------------------------------------------------+----------------------+
| [ <- Indietro ]                                                                            [ Continua -> ] |
+------------------------------------------------------------------------------------------------------------+
```

### 3.6 Passo 6 — Target (B11, `Δ` `+`)

Le barre sono la forma del target, non un'anteprima del piano.

```text
+--------------------+----------------------------------------------------------------+----------------------+
| PASSI              | TARGET · NUOVA ALLOCAZIONE                                     | RIEPILOGO            |
| v 1  Scenario      | Come distribuire la liquidità. Non è un'anteprima del piano.   | Asset          3     |
| v 2  Liquidità     | [ Copia distribuzione corrente ]                               | Totale  100,00%      |
| v 3  Broker        |                                                                |      (controllo)     |
| v 4  Asset         | Asset                      Target % Distribuzione              |                      |
| v 5  Routing       | MOND Azionario Mondo         [ 60 ] ############               | Nessun valore        |
| > 6  Target        | OBBL Obbligazionario         [ 30 ] ######                     | futuro calcolato     |
| ○ 7  FX            | EMER Emergenti               [ 10 ] ##                         |                      |
| ○ 8  Strategia     |                                                                |                      |
| ○ 9  Rivedi        | Totale 100,00%   Restante 0,00%   (controllo informativo)      |                      |
|                    | [i] Pesi in percentuale; al backend vanno come decimali.       |                      |
+--------------------+----------------------------------------------------------------+----------------------+
| [ <- Indietro ]                                                                            [ Continua -> ] |
+------------------------------------------------------------------------------------------------------------+
```

«Copia distribuzione corrente» (Q-C0-6) apre un dialogo. I pesi li calcola il backend, con il motore
del portafoglio che alimenta la pagina Allocazione; la UI li mostra soltanto. Il denominatore sono gli
Asset dello scenario, quindi i numeri coincidono con la pagina solo se lo scenario comprende tutti gli
Asset posseduti. Un Asset manuale non è nel portafoglio e riceve 0, con la nota. Come per le altre
copie serve almeno un Broker `OWNER`; nessun legame live, nessun calcolo avviato.

```text
+--------------------------------------------------------------------------------------+
| Copia distribuzione corrente                                                     [x] |
+--------------------------------------------------------------------------------------+
| Fonte: motore del portafoglio (valori della pagina Allocazione) · al 23/09/2026      |
| Broker (solo OWNER):  [v] Demo A   [ ] Demo B · quota 50%   [-] Demo C · VIEWER      |
| Denominatore: gli Asset dello scenario; la cassa non entra.                          |
| Se lo scenario non comprende tutti i tuoi Asset, i pesi differiscono dalla pagina.   |
|                                                                                      |
| Asset                            Peso Valorizzazione                                 |
| MOND Azionario Mondo           72,15% prezzo di mercato 22/09 · 1 giorno prima       |
| OBBL Obbligazionario           27,85% prezzo di mercato 23/09                        |
| EMER Emergenti                  0,00% manuale · non nel portafoglio                  |
| NUOV Nuovo fondo                0,00% non posseduto                                  |
| Totale                        100,00% a 0,01 punti; somma esatta dal backend         |
|                                                                                      |
| Solo pesi, nessun valore del portafoglio. Base da modificare, non un consiglio.      |
| Un Asset posseduto senza prezzo o cambio: nessun peso, pulsante disabilitato.        |
| Nessun Asset posseduto: nessun peso. In entrambi i casi nessun target cambia.        |
| Un target già modificato non viene sovrascritto senza conferma.                      |
|                                                                                      |
| [ Annulla ]                                                      [ Usa come target ] |
+--------------------------------------------------------------------------------------+
```

### 3.7 Passo 7 — FX (B13, `Δ` `−`)

Il tasso è un fatto copiato o scritto a mano. Il backend decide se e quanto convertire.

```text
+--------------------+----------------------------------------------------------------+----------------------+
| PASSI              | FX · TASSI USATI DAL CALCOLO                                   | RIEPILOGO            |
| v 1  Scenario      | Il backend decide se e quanto convertire. Tu fornisci i tassi. | Coppie         1     |
| v 2  Liquidità     | [ Copia tassi FX ]                                             | Non del giorno 1     |
| v 3  Broker        | +------------------------------------------------------------+ | Spread     0,25%     |
| v 4  Asset         | | EUR/USD                                                [C] | |                      |
| v 5  Routing       | | 1 EUR = [ 1,1000 ] USD   ECB · 22/09/2026 · 1 giorno prima | |                      |
| v 6  Target        | | [ Ripristina ] [ Modifica ]                                | |                      |
| > 7  FX            | +------------------------------------------------------------+ |                      |
| ○ 8  Strategia     | Spread di conversione *  [ 0,25 ]%                             |                      |
| ○ 9  Rivedi        | Uno per scenario, applicato una volta a ogni conversione;      |                      |
|                    | la valorizzazione usa il tasso ufficiale.                      |                      |
|                    |                                                                |                      |
|                    | Coppie proposte da valute di Asset, cassa e modalità;          |                      |
|                    | chiavi solo da selettore di coppia (N20).                      |                      |
|                    | Non in 2.0.0: FX per Broker, margine sicurezza, fee di         |                      |
|                    | conversione, multi-hop.                                        |                      |
+--------------------+----------------------------------------------------------------+----------------------+
| [ <- Indietro ]                                                                            [ Continua -> ] |
+------------------------------------------------------------------------------------------------------------+
```

> ❌ non più da fare (developer, 02/10/2026): le voci «Non in 2.0.0» di questo schema — margine di sicurezza, fee di conversione, multi-hop e un tasso o uno spread diverso per Broker. Il modo in cui un Broker converte è arrivato dopo, come `conversion_mode` (manuale o automatica). L'elenco è uscito dal passo FX con R13.9 del [piano post-merge](plan-phase00PacRound5PostMerge.prompt.md).

### 3.8 Passo 8 — Strategia (B14, `Δ`)

```text
+--------------------+----------------------------------------------------------------+----------------------+
| PASSI              | STRATEGIA                                                      | RIEPILOGO            |
| v 1  Scenario      | Tutti i vincoli dei passi precedenti restano rigidi.           | Strategia            |
| v 2  Liquidità     | +------------------------------------------------------------+ | Proporzionale        |
| v 3  Broker        | | (o) Proporzionale                                          | |                      |
| v 4  Asset         | |                                                            | |                      |
| v 5  Routing       | | Ordine degli obiettivi, dal più importante:                | |                      |
| v 6  Target        | | 1 scarto L2 dai target fissi                               | |                      |
| v 7  FX            | | 2 liquidità non investita (U)                              | |                      |
| > 8  Strategia     | | 3 priorità delle route                                     | |                      |
| ○ 9  Rivedi        | | 4 costi espliciti (commissioni, spread, margine)           | |                      |
|                    | | 5 numero di ordini                                         | |                      |
|                    | | Parametri aggiuntivi: nessuno.                             | |                      |
|                    | +------------------------------------------------------------+ |                      |
|                    | [i] Le strategie arrivano dal contratto del backend.           |                      |
+--------------------+----------------------------------------------------------------+----------------------+
| [ <- Indietro ]                                                                            [ Continua -> ] |
+------------------------------------------------------------------------------------------------------------+
```

### 3.9 Passo 9 — Rivedi (B16, `=`)

```text
+--------------------+----------------------------------------------------------------+----------------------+
| PASSI              | RIVEDI E CALCOLA                                               | SNAPSHOT             |
| v 1  Scenario      | Il backend riceverà questa copia completa, e solo questa.      | Draft rev. 18        |
| v 2  Liquidità     | +------------------------------------------------------------+ | Creato 23/09 14:35   |
| v 3  Broker        | | v Scenario     23/09/2026 · EUR                            | |                      |
| v 4  Asset         | | v Liquidità    2 fonti · EUR                               | | Fatti copiati   9    |
| v 5  Routing       | | v Broker       1 operativo · 1 solo funding                | | Manuali         6    |
| v 6  Target        | | v Asset        3 · prezzi 3/3 · 1 non del giorno           | | Non del giorno  2    |
| v 7  FX            | | v Routing      3 route BUY                                 | | Modificati      1    |
| v 8  Strategia     | | v Target       3 Asset                                     | |                      |
| > 9  Rivedi        | | v FX           1 coppia · 1 non del giorno                 | | Backend/API 2.0.0    |
|                    | | v Strategia    Proporzionale                               | |                      |
|                    | +------------------------------------------------------------+ |                      |
|                    | [ Snapshot completo ] [ Solo modificati/non del giorno ]       |                      |
|                    | [i] Nessun ordine verrà inviato al Broker.                     |                      |
|                    |                                                                |                      |
|                    |                     [ Calcola piano ]                          |                      |
+--------------------+----------------------------------------------------------------+----------------------+
```

---

## 4. Desktop — risultato

Il risultato sostituisce lo stepper (`UiTarget:1362`). «Modifica configurazione» riapre il passo 9
con il draft intatto.

### 4.1 Header, KPI e grafico per Asset (C1–C2)

Privacy OFF.

```text
+------------------------------------------------------------------------------------------------------------+
| <- Strumenti                                                                                     [ Guida ] |
| Allocatore PAC · Piano calcolato                                                              privacy: OFF |
| Scenario 23/09/2026 · Valuta EUR · draft rev. 18 · Backend/API 2.0.0                                       |
+------------------------------------------------------------------------------------------------------------+
| [v] Piano disponibile   [Verificato in Decimal]   [Ottimalità non provata]   [Completato]                  |
| Scarto L2 ≈207,64 EUR² · Non investito ≈4,09 € EUR · 0 vincoli violati · 0 issue bloccanti                 |
|                                                                                                            |
| [ Modifica configurazione ]                                                        [ Calcola nuovo piano ] |
+------------------------------------------------------------------------------------------------------------+
| Riferimento fisso    Investito dopo       Non investito (U)    Costi espliciti      Ordini                 |
| 2.000,00 € EUR       ≈1.995,91 € EUR      ≈4,09 € EUR          ≈0,48 € EUR          3                      |
| U = cassa libera 3,61 € EUR + perdite economiche ≈0,48 € EUR + arrotondamento 0,00 € EUR                   |
| Funding selezionato 2.000,00 € EUR · raggiungibile 2.000,00 € EUR · intrappolato 0,00 € EUR                |
+------------------------------------------------------------------------------------------------------------+
| ALLOCAZIONE PER ASSET · % dell'investito · T = target, D = dopo il piano                                   |
|                          Target     Dopo    0%          25%          50%          75%     100%             |
| MOND Azionario Mondo     60,00%  ≈60,62% T  ==============================                                 |
|                                          D  ##############################                                 |
| OBBL Obbligazionario     30,00%  ≈29,81% T  ===============                                                |
|                                          D  ###############                                                |
| EMER Emergenti           10,00%   ≈9,57% T  =====                                                          |
|                                          D  #####                                                          |
| Solo pesi del backend (target_weight, final_weight). Nessun 'Prima': in PAC puro è 0 per costruzione.      |
+------------------------------------------------------------------------------------------------------------+
```

Privacy ON. Pesi e conteggi restano visibili; ogni importo, L2 compreso, si maschera.

```text
+------------------------------------------------------------------------------------------------------------+
| <- Strumenti                                                                                     [ Guida ] |
| Allocatore PAC · Piano calcolato                                                               privacy: ON |
| Scenario 23/09/2026 · Valuta EUR · draft rev. 18 · Backend/API 2.0.0                                       |
+------------------------------------------------------------------------------------------------------------+
| [v] Piano disponibile   [Verificato in Decimal]   [Ottimalità non provata]   [Completato]                  |
| Scarto L2 ≈••• EUR² · Non investito ≈••• € EUR · 0 vincoli violati · 0 issue bloccanti                     |
|                                                                                                            |
| [ Modifica configurazione ]                                                        [ Calcola nuovo piano ] |
+------------------------------------------------------------------------------------------------------------+
| Riferimento fisso    Investito dopo       Non investito (U)    Costi espliciti      Ordini                 |
| ••• € EUR            ≈••• € EUR           ≈••• € EUR           ≈••• € EUR           3                      |
| U = cassa libera ••• € EUR + perdite economiche ≈••• € EUR + arrotondamento ••• € EUR                      |
| Funding selezionato ••• € EUR · raggiungibile ••• € EUR · intrappolato ••• € EUR                           |
+------------------------------------------------------------------------------------------------------------+
| ALLOCAZIONE PER ASSET · % dell'investito · T = target, D = dopo il piano                                   |
|                          Target     Dopo    0%          25%          50%          75%     100%             |
| MOND Azionario Mondo     60,00%  ≈60,62% T  ==============================                                 |
|                                          D  ##############################                                 |
| OBBL Obbligazionario     30,00%  ≈29,81% T  ===============                                                |
|                                          D  ###############                                                |
| EMER Emergenti           10,00%   ≈9,57% T  =====                                                          |
|                                          D  #####                                                          |
| Solo pesi del backend (target_weight, final_weight). Nessun 'Prima': in PAC puro è 0 per costruzione.      |
+------------------------------------------------------------------------------------------------------------+
```

- I quattro badge leggono quattro campi distinti: `availability`, `outcome`, `proof.kind`, `stop_reason`.
  «Completato» non è mai un segno di ottimo (`UiTarget:1391-1392`).
- `U` e la sua scomposizione vengono da `PlannerAccountingSummary` (`:1678`). La UI non somma.
- «Costi espliciti» è lo stadio `explicit_cost` di `objectives` (`:1703-1747`), non una somma di righe.

### 4.2 Esposizioni (C4, `Δ` `+` `−`)

```text
+------------------------------------------------------------------------------------------------------------+
| ESPOSIZIONI · pesi pubblici: identici con privacy ON                                                       |
| Tipo Asset                                                                                                 |
| Azionario                70,00%  ≈70,19% T  ===================================                            |
|                                          D  ###################################                            |
| Obbligazionario          30,00%  ≈29,81% T  ===============                                                |
|                                          D  ###############                                                |
| Geografia                                                                                                  |
| Europa                   42,00%  ≈41,94% T  =====================                                          |
|                                          D  #####################                                          |
| America                  36,00%  ≈36,37% T  ==================                                             |
|                                          D  ##################                                             |
| Non classificato         12,00%  ≈12,12% T  ======                                                         |
|                                          D  ######                                                         |
| Asia                     10,00%   ≈9,57% T  =====                                                          |
|                                          D  #####                                                          |
| Settore  nessuna classificazione dichiarata · 100% non classificato   [ Mostra ]                           |
| 'Non classificato' = quota non dichiarata (allocation.uncategorised), etichetta tradotta dalla UI.         |
+------------------------------------------------------------------------------------------------------------+
```

- Le tre dimensioni escono sempre (W14). Senza nessuna dichiarazione, una dimensione è una sola riga
  «Non classificato» al 100%: la UI la ripiega in una riga di testo.
- Etichetta di `allocation.uncategorised` tradotta dalla UI (il backend manda `Uncategorised`).

### 4.3 Asset (C5, `Δ`)

```text
+------------------------------------------------------------------------------------------------------------+
| ASSET · valori nella valuta di riferimento                                                                 |
| Asset                    Target     Dopo    Valore target      Valore dopo         Scarto   Acquisto (mid) |
| MOND Azionario Mondo     60,00%  ≈60,62%   1.200,00 € EUR   1.210,00 € EUR   +10,00 € EUR   1.210,00 € EUR |
| OBBL Obbligazionario     30,00%  ≈29,81%     600,00 € EUR     595,00 € EUR    -5,00 € EUR     595,00 € EUR |
| EMER Emergenti           10,00%   ≈9,57%     200,00 € EUR    ≈190,91 € EUR   ≈-9,09 € EUR    ≈190,91 € EUR |
| Totali (contabilità)                       2.000,00 € EUR  ≈1.995,91 € EUR                                 |
| Scarto = residual del backend (dopo - target). Nessuna sottrazione nel frontend.                           |
+------------------------------------------------------------------------------------------------------------+
```

```text
+------------------------------------------------------------------------------------------------------------+
| ASSET · valori nella valuta di riferimento                                                                 |
| Asset                    Target     Dopo    Valore target      Valore dopo         Scarto   Acquisto (mid) |
| MOND Azionario Mondo     60,00%  ≈60,62%        ••• € EUR        ••• € EUR     +••• € EUR        ••• € EUR |
| OBBL Obbligazionario     30,00%  ≈29,81%        ••• € EUR        ••• € EUR     -••• € EUR        ••• € EUR |
| EMER Emergenti           10,00%   ≈9,57%        ••• € EUR       ≈••• € EUR    ≈-••• € EUR       ≈••• € EUR |
| Totali (contabilità)                            ••• € EUR       ≈••• € EUR                                 |
| Scarto = residual del backend (dopo - target). Nessuna sottrazione nel frontend.                           |
+------------------------------------------------------------------------------------------------------------+
```

### 4.4 Piano operativo (C10–C12, `Δ` `+`)

```text
+------------------------------------------------------------------------------------------------------------+
| PIANO OPERATIVO · nell'ordine di sequenza del backend                                   [ Comprimi tutto ] |
+------------------------------------------------------------------------------------------------------------+
| 1  FUNDING  Risparmio settembre -> Demo A · EUR                                               796,39 € EUR |
|             route di funding · priorità 0 · allocation.fund_declared_orders (tradotto)                     |
+------------------------------------------------------------------------------------------------------------+
| 2  FX       Demo A · EUR -> USD · per la route di EMER                                                     |
|             addebito 191,39 € EUR -> accredito 210,00 $ USD                                                |
|             1 EUR = 1,1000 USD spot · 1,09725 effettivo · perdita spread ≈0,48 € EUR                       |
+------------------------------------------------------------------------------------------------------------+
| ORDINI · Demo A                                                                                            |
| Seq  Asset                  Istruzione                Prezzo mid     Addebito cassa    Commissione         |
| 3    MOND Azionario Mondo   compra 11 quote         110,00 € EUR     1.210,00 € EUR     0,00 € EUR         |
| 4    OBBL Obbligazionario   compra 119 quote          5,00 € EUR       595,00 € EUR     0,00 € EUR         |
| 5    EMER Emergenti         compra 7 quote           30,00 $ USD       210,00 $ USD     0,00 $ USD         |
| Prezzi di mercato pubblici; quantità, importi e commissioni addebitate sono patrimonio (privacy).          |
| Sequenze illustrative: la UI ordina per 'sequence' del backend, non ricalcola nulla.                       |
+------------------------------------------------------------------------------------------------------------+
```

```text
+------------------------------------------------------------------------------------------------------------+
| PIANO OPERATIVO · nell'ordine di sequenza del backend                                   [ Comprimi tutto ] |
+------------------------------------------------------------------------------------------------------------+
| 1  FUNDING  Risparmio settembre -> Demo A · EUR                                                  ••• € EUR |
|             route di funding · priorità 0 · allocation.fund_declared_orders (tradotto)                     |
+------------------------------------------------------------------------------------------------------------+
| 2  FX       Demo A · EUR -> USD · per la route di EMER                                                     |
|             addebito ••• € EUR -> accredito ••• $ USD                                                      |
|             1 EUR = 1,1000 USD spot · 1,09725 effettivo · perdita spread ≈••• € EUR                        |
+------------------------------------------------------------------------------------------------------------+
| ORDINI · Demo A                                                                                            |
| Seq  Asset                  Istruzione                Prezzo mid     Addebito cassa    Commissione         |
| 3    MOND Azionario Mondo   compra ••• quote        110,00 € EUR          ••• € EUR      ••• € EUR         |
| 4    OBBL Obbligazionario   compra ••• quote          5,00 € EUR          ••• € EUR      ••• € EUR         |
| 5    EMER Emergenti         compra ••• quote         30,00 $ USD          ••• $ USD      ••• $ USD         |
| Prezzi di mercato pubblici; quantità, importi e commissioni addebitate sono patrimonio (privacy).          |
| Sequenze illustrative: la UI ordina per 'sequence' del backend, non ricalcola nulla.                       |
+------------------------------------------------------------------------------------------------------------+
```

Ledger trasposto: una colonna per Broker × valuta scala meglio di sedici colonne per riga.

```text
+------------------------------------------------------------------------------------------------------------+
| SALDI PER BROKER E VALUTA · ledger del backend, una colonna per Broker × valuta                            |
| Voce                             Demo A · EUR       Demo A · USD                                           |
| Iniziale selezionato           1.200,00 € EUR         0,00 $ USD                                           |
| Funding in                       796,39 € EUR         0,00 $ USD                                           |
| Funding out                        0,00 € EUR         0,00 $ USD                                           |
| FX addebito                      191,39 € EUR         0,00 $ USD                                           |
| FX accredito                       0,00 € EUR       210,00 $ USD                                           |
| Acquisti                       1.805,00 € EUR       210,00 $ USD                                           |
| Commissioni BUY                    0,00 € EUR         0,00 $ USD                                           |
| Arrotondamento                     0,00 € EUR         0,00 $ USD                                           |
| Finale spendibile                  0,00 € EUR         0,00 $ USD                                           |
| Finale fisico                      0,00 € EUR         0,00 $ USD                                           |
| Vendite, commissioni SELL, tasse trattenute/riservate: sempre 0 in PAC 2.0.0  [ Mostra 5 righe a zero ]    |
| Cassa libera fuori dai Broker (contabilità): 3,61 € EUR                                                    |
+------------------------------------------------------------------------------------------------------------+
```

```text
+------------------------------------------------------------------------------------------------------------+
| SALDI PER BROKER E VALUTA · ledger del backend, una colonna per Broker × valuta                            |
| Voce                             Demo A · EUR       Demo A · USD                                           |
| Iniziale selezionato                ••• € EUR          ••• $ USD                                           |
| Funding in                          ••• € EUR          ••• $ USD                                           |
| Funding out                         ••• € EUR          ••• $ USD                                           |
| FX addebito                         ••• € EUR          ••• $ USD                                           |
| FX accredito                        ••• € EUR          ••• $ USD                                           |
| Acquisti                            ••• € EUR          ••• $ USD                                           |
| Commissioni BUY                     ••• € EUR          ••• $ USD                                           |
| Arrotondamento                      ••• € EUR          ••• $ USD                                           |
| Finale spendibile                   ••• € EUR          ••• $ USD                                           |
| Finale fisico                       ••• € EUR          ••• $ USD                                           |
| Vendite, commissioni SELL, tasse trattenute/riservate: sempre 0 in PAC 2.0.0  [ Mostra 5 righe a zero ]    |
| Cassa libera fuori dai Broker (contabilità): ••• € EUR                                                     |
+------------------------------------------------------------------------------------------------------------+
```

### 4.5 Dettaglio di una riga (C13, `Δ` `−`)

```text
+------------------------------------------------------------------------------------------------------------+
| DETTAGLIO ORDINE 5 · EMER Emergenti · Demo A · USD                                              [ Chiudi ] |
| Istruzione           compra 7 quote · passo 1       Quantità economica   7 quote (esatta)                  |
| Prezzo fonte         30,00 $ USD per 1 quota [M]    Data prezzo          23/09/2026 · manuale              |
| Prezzo mid           30,00 $ USD                    Prezzo di carico     30,00 $ USD · margine 0,00%       |
| Valore mid           ≈190,91 € EUR                  Costo margine        0,00 € EUR                        |
| Addebito cassa       210,00 $ USD                   Commissione          0,00 $ USD                        |
| Conversione          azione 2 · EUR -> USD          Perdita spread       ≈0,48 € EUR                       |
| Route                priorità 0 · tetto 20 quote    Minimi               nessuno                           |
| Provenance: [M] prezzo EMER · [M] route EMER · [C] EUR/USD ECB 22/09      [ Mostra provenance ]            |
| fx_cost e buffer della riga sono sempre 0, explanation_keys sempre vuoto (N23): la UI non li mostra.       |
+------------------------------------------------------------------------------------------------------------+
```

### 4.6 Prova e solver (C14, `Δ`)

Scenario testimone: il solver ha finito, la prova no.

```text
+------------------------------------------------------------------------------------------------------------+
| PROVA E SOLVER                                                                                [ Comprimi ] |
| Esito  incumbent_found · piano verificato in Decimal esatto dal backend (decimal_verified)                 |
| Prova  non provata · allocation.exact_proof_not_established                                                |
|        Il solver ha finito, ma riporta numeri floating: l'ottimalità non è certificata.                    |
| Stop   completed                                                                                           |
+------------------------------------------------------------------------------------------------------------+
| Stadi del solver · reported_floating · SCIP x.y.z · ambito globale                                         |
| Ord  Obiettivo              Stato             Primale          Duale   Gap ass.   Gap rel.                 |
| 1    fixed_l2 (EUR²)        finished       207,644628     207,644628          0          0                 |
| 2    shortfall (EUR)        finished         4,090909       4,090909          0          0                 |
| 3    route_priority         finished                0              0          0          0                 |
| 4    explicit_cost (EUR)    finished         0,480909       0,480909          0          0                 |
| 5    active_order_rows      finished                3              3          0          0                 |
| Spareggio finale: canonical_key.                                                                           |
+------------------------------------------------------------------------------------------------------------+
| Tempi  coda 3 ms · avvio n/d · validazione input 12 ms · calcolo 840 ms · validazione output 25 ms         |
|        serializzazione 4 ms · esecuzione 890 ms · pulizia n/d        (n/d = fase non osservata)            |
+------------------------------------------------------------------------------------------------------------+
```

Con la privacy ON si mascherano primale e duale degli stadi monetari (`fixed_l2`, `shortfall`,
`explicit_cost`). `route_priority` e `active_order_rows` restano visibili.

```text
+------------------------------------------------------------------------------------------------------------+
| PROVA E SOLVER                                                                                [ Comprimi ] |
| Esito  incumbent_found · piano verificato in Decimal esatto dal backend (decimal_verified)                 |
| Prova  non provata · allocation.exact_proof_not_established                                                |
|        Il solver ha finito, ma riporta numeri floating: l'ottimalità non è certificata.                    |
| Stop   completed                                                                                           |
+------------------------------------------------------------------------------------------------------------+
| Stadi del solver · reported_floating · SCIP x.y.z · ambito globale                                         |
| Ord  Obiettivo              Stato             Primale          Duale   Gap ass.   Gap rel.                 |
| 1    fixed_l2 (EUR²)        finished              •••            •••          0          0                 |
| 2    shortfall (EUR)        finished              •••            •••          0          0                 |
| 3    route_priority         finished                0              0          0          0                 |
| 4    explicit_cost (EUR)    finished              •••            •••          0          0                 |
| 5    active_order_rows      finished                3              3          0          0                 |
| Spareggio finale: canonical_key.                                                                           |
+------------------------------------------------------------------------------------------------------------+
| Tempi  coda 3 ms · avvio n/d · validazione input 12 ms · calcolo 840 ms · validazione output 25 ms         |
|        serializzazione 4 ms · esecuzione 890 ms · pulizia n/d        (n/d = fase non osservata)            |
+------------------------------------------------------------------------------------------------------------+
```

Scenario minimo: prova esatta dall'oracolo.

```text
+------------------------------------------------------------------------------------------------------------+
| PROVA · esempio minimo: 1.000,00 EUR, MOND + OBBL, target 70/30                                            |
| Esito  incumbent_found · MOND 6 quote + OBBL 60 quote · L2 1.600,00 EUR² · U 40,00 € EUR                   |
| Prova  [Ottimo provato] · oracolo esaustivo · spareggio chiuso                                             |
|        2.211 candidati enumerati · 1.020 ammissibili · 5 obiettivi della cascata verificati                |
| Solver non eseguito · allocation.solver_not_required (dominio entro 200.000 candidati)                     |
+------------------------------------------------------------------------------------------------------------+
```

---

## 5. Stati

Ogni stato ha un pannello proprio. Nessuno stato si traveste da un altro: un limite di tempo non è
un'impossibilità, un piano valido non è un ottimo.

### 5.1 Matrice: stato del backend → schermata

| Stato | Come nasce in 2.0.0 | Runbook sulla copia | Solo fixture | Blocco |
|---|---|---|---|---|
| `needs_input` | prezzo o tasso mancante | sì | | D9 |
| `invalid` | es. `cash_selection_invalid`, `target_total_not_one`, `exposure_total_exceeds_one` (Q-C0-7) | sì | | D9b |
| `unsupported` | es. `broker_inactive` | da verificare | sì | D10 |
| `ready_no_op` | nessun acquisto possibile | sì | | D11 |
| `ready_incumbent` + `optimal_proven` | dominio ≤ 200.000 candidati: oracolo | sì | | C14 minimo |
| `ready_incumbent` + `not_proven`, `completed` | dominio grande: SCIP | sì | | C1–C14 |
| `ready_incumbent` + `time_limit`/`node_limit` | limite del solver | non affidabile | sì | D13 |
| `ready_incumbent` + `optimal_proven` da `score_lattice_closure` | **mai** in PAC 2.0.0 (N8) | no | sì | C14 |
| `ready_incumbent` + `gap_bounded` | **mai** in PAC 2.0.0 (N8) | no | sì | C14 |
| `ready_infeasible` + `exhaustive_oracle` | oracolo esaustivo | sì | | D12 |
| `ready_infeasible` + `deterministic_conflict` | **mai** in PAC 2.0.0 (N8) | no | sì | D12 |
| `ready_no_incumbent` | limite senza piano | non affidabile | sì | D14 |
| `ToolError` | piattaforma (timeout, output, memoria…) | no | sì | errore di piattaforma |
| risultato stale | modifica dopo il calcolo (solo UI) | sì | | D15 |
| cambio sessione | logout/login (solo UI) | sì | | D16 |

La UI deve rendere **tutti** gli stati del codec. Il runbook può raggiungere solo quelli prodotti.

### 5.2 Calcolo in corso (D7, `Δ`)

```text
+------------------------------------------------------------------------------------------------------------+
| CALCOLO IN CORSO                                                                               privacy: ON |
| [spinner] Validazione e ricerca del piano operativo...                                                     |
|                                                                                                            |
| Snapshot rev. 18 · 3 Asset · 1 Broker operativo · 3 route BUY · 1 coppia FX                                |
| La configurazione è bloccata finché questa richiesta è attiva.                                             |
|                                                                                                            |
| [ Interrompi attesa ]                                                                                      |
| Interrompere smette di attendere: il server può finire lo stesso, e quella risposta viene scartata.        |
+------------------------------------------------------------------------------------------------------------+
```

### 5.3 Problemi locali prima dell'invio (D8, `Δ`)

```text
+------------------------------------------------------------------------------------------------------------+
| RIVEDI E CALCOLA · 2 problemi da risolvere prima del calcolo                                               |
| [!] Target: il totale è 95,00%, deve essere 100,00%   (controllo)                         [ Vai a Target ] |
| [!] Liquidità: Demo A · EUR, 'Importo da usare' vuoto                                  [ Vai a Liquidità ] |
|                                                                                                            |
| [ Calcola piano ]  disabilitato finché la lista non è vuota                                                |
| Controlli locali solo di forma e di stessa unità; ogni regola economica resta al backend.                  |
+------------------------------------------------------------------------------------------------------------+
```

### 5.4 Servono altri dati (D9, `=`)

```text
+------------------------------------------------------------------------------------------------------------+
| [?] SERVONO ALTRI DATI · needs_input · il backend non ha calcolato nulla                                   |
| NUOV Nuovo fondo   prezzo mancante · allocation.price_missing                             [ Vai ad Asset ] |
| EUR/USD            tasso mancante · allocation.fx_rate_missing                                [ Vai a FX ] |
|                                                                                                            |
| Draft intatto. Nessun Asset tolto in silenzio: aggiungi il dato o rimuovi l'Asset tu.                      |
+------------------------------------------------------------------------------------------------------------+
```

Input rifiutato dal backend. Stesso pannello, altra intestazione.

```text
+------------------------------------------------------------------------------------------------------------+
| [x] INPUT NON VALIDO · invalid · il backend non ha calcolato nulla                                         |
| Liquidità   Demo A · EUR: importo oltre il disponibile · allocation.cash_selection_invalid         [ Vai ] |
| Target      il totale non è 100% · allocation.target_total_not_one                                 [ Vai ] |
|                                                                                                            |
| Messaggi tradotti dalla UI; parametri monetari mascherati con privacy ON. Codice visibile in [ Dettagli ]. |
+------------------------------------------------------------------------------------------------------------+
```

### 5.5 Non supportato (D10, `=`)

```text
+------------------------------------------------------------------------------------------------------------+
| [-] SCENARIO NON SUPPORTATO · unsupported                                                                  |
| Demo B   Broker non attivo · allocation.broker_inactive                                   [ Vai a Broker ] |
|                                                                                                            |
| Non è un errore dei tuoi dati: questa versione del Tool non gestisce il caso. Nessun calcolo avviato.      |
+------------------------------------------------------------------------------------------------------------+
```

### 5.6 Nessuna operazione (D11, `=`)

```text
+------------------------------------------------------------------------------------------------------------+
| [=] NESSUNA OPERAZIONE · ready_no_op · no_op                                                               |
| Con ••• € EUR non si compra nemmeno 1 quota di MOND (110,00 € EUR): il piano è non fare nulla.             |
| Prova pubblicata dal backend, qui [Ottimo provato] · oracolo esaustivo (illustrativo).                     |
| Nessun ordine, nessun FX, nessun funding.   [ Modifica configurazione ]                                    |
+------------------------------------------------------------------------------------------------------------+
```

### 5.7 Impossibile (D12, `Δ`)

```text
+------------------------------------------------------------------------------------------------------------+
| [x] IMPOSSIBILE CON QUESTI VINCOLI · ready_infeasible · infeasibility_proven                               |
| Provato: nessuna combinazione rispetta tutti i vincoli rigidi insieme.                                     |
| Fonte della prova: oracolo esaustivo · 21 candidati enumerati · 0 ammissibili (illustrativo)               |
|                                                                                                            |
| Vincoli rigidi coinvolti (dal draft; tetti e minimi mascherati fino a R7):                                 |
|   MOND · Demo A   minimo obbligatorio ••• quote         [ Vai a Routing ]                                  |
|   Liquidità       raggiungibile ••• € EUR               [ Vai a Liquidità ]                                |
|                                                                                                            |
| La UI non indica quale vincolo 'rompere': li elenca. Nessun piano parziale mostrato come valido.           |
+------------------------------------------------------------------------------------------------------------+
```

### 5.8 Piano al limite di tempo (D13, `Δ`)

```text
+------------------------------------------------------------------------------------------------------------+
| [v] Piano disponibile   [Verificato in Decimal]   [Ottimalità non provata]   [Limite di tempo]             |
| Il solver si è fermato al limite di tempo con un piano valido. Potrebbe esisterne uno migliore.            |
| Stadi (illustrativo): 1 finished · 4 unfinished · nessun gap certificato (PAC 2.0.0: no gap_bounded).      |
|                                                                                                            |
| [ Modifica configurazione ]          (il risultato sotto resta completo e consultabile)                    |
+------------------------------------------------------------------------------------------------------------+
```

### 5.9 Nessun piano entro i limiti (D14, `=`)

```text
+------------------------------------------------------------------------------------------------------------+
| [!] NESSUN PIANO ENTRO I LIMITI · ready_no_incumbent · allocation.solver_limit_no_incumbent                |
| Il solver non ha trovato un piano prima del limite. Non è una prova che il piano non esista.               |
|                                                                                                            |
| Per ridurre la ricerca: meno Asset o route, tetti più stretti, passi più grandi.                           |
| [ Modifica configurazione ]      nessun 'Riprova' con gli stessi input                                     |
+------------------------------------------------------------------------------------------------------------+
```

### 5.10 Risultato non aggiornato (D15, `=`)

```text
+------------------------------------------------------------------------------------------------------------+
| [!] RISULTATO NON AGGIORNATO                                                                               |
| Hai cambiato il target dopo questo calcolo. Valori e ordini sotto restano consultabili,                    |
| ma non descrivono più il draft corrente.                                                                   |
|                                                                                                            |
| Snapshot risultato rev. 18 · Draft corrente rev. 19                                                        |
| [ Torna a Rivedi ] [ Scarta risultato precedente ]                                                         |
+------------------------------------------------------------------------------------------------------------+
| RISULTATO PRECEDENTE · NON CORRENTE  (banner persistente, nessun ricalcolo automatico)                     |
+------------------------------------------------------------------------------------------------------------+
```

### 5.11 Sessione cambiata (D16, `=`)

```text
+------------------------------------------------------------+
| Sessione cambiata                                          |
| Il Tool è stato azzerato per proteggere i dati del conto.  |
|                                                            |
| [ Torna ai Tools ]                                         |
+------------------------------------------------------------+
```

### 5.12 Errore della piattaforma (`+`)

```text
+------------------------------------------------------------------------------------------------------------+
| [x] CALCOLO NON RIUSCITO · errore della piattaforma Tool                                                   |
| execution_timeout · il calcolo ha superato il limite di esecuzione.                                        |
| Esempio con retryable = sì:          [ Riprova ]   [ Modifica configurazione ]                             |
|                                                                                                            |
| Con retryable = no (es. invalid_output) il pulsante Riprova non compare.                                   |
| Messaggi PAC-locali per i 16 codici ToolError (N17); il draft resta intatto.                               |
+------------------------------------------------------------------------------------------------------------+
```

---

## 6. Mobile (34 colonne)

Un passo per schermata; i passi si aprono da «Passi». Il pulsante in basso resta fisso. La
rifinitura mobile arriva dopo la review di dettaglio della UI, al STOP: qui si fissa la struttura, non la densità.

Liquidità manuale con la privacy OFF; copia dai Broker e routing con la privacy ON.

```text
+--------------------------------+
| <- Strumenti       privacy OFF |
| Allocatore PAC                 |
| 2/9 Liquidità      [ Passi v ] |
| =======----------------------- |
+--------------------------------+
| [ + Contributo ] [ + Manuale ] |
| [ Copia dai Broker ]           |
|                                |
| Conto manuale             [M]  |
| Valuta     [ EUR v ]           |
| Importo *  [ 500,00 ] EUR      |
| Etichetta  [ Conto banca ]     |
| Solo funding: non compra.      |
|                                |
| Risparmio settembre       [M]  |
| Importo *  [ 800,00 ] EUR      |
+--------------------------------+
| [ <- ]         [ Continua -> ] |
+--------------------------------+
```

```text
+--------------------------------+
| Copia dai Broker           [x] |
+--------------------------------+
| API Portfolio · 23/09/2026     |
| Solo Broker OWNER.             |
|                                |
| [v] Demo A                     |
|     EUR custodia ••• € EUR     |
|     100% tua                   |
| [ ] Demo B · quota 50%         |
|     EUR tua ••• € EUR          |
| [-] Demo C · VIEWER            |
|     non selezionabile          |
|                                |
| 'Importo da usare' resta       |
| vuoto: lo scrivi tu.           |
+--------------------------------+
| [ Annulla ]        [ Copia 1 ] |
+--------------------------------+
```

```text
+--------------------------------+
| <- Strumenti        privacy ON |
| Allocatore PAC                 |
| 5/9 Routing        [ Passi v ] |
| =================------------- |
+--------------------------------+
| MOND · Demo A · EUR            |
| quote intere · passo 1         |
|                                |
| Priorità   [ 0 ]  0 = prima    |
| Minimo se operi                |
|            [ Nessuno v ]       |
| Minimo obbligatorio            |
|            [ Nessuno v ]       |
| Tetto *    [ Quantità v ]      |
|            [ 1.000.000.000 ]   |
|            quote · predefinito |
| Margine    [ 0,00 ]%           |
|                                |
| [ < prec. ]      [ OBBL > ]    |
+--------------------------------+
| [ <- ]         [ Continua -> ] |
+--------------------------------+
```

Risultato, con privacy ON. Le sezioni si aprono una alla volta.

```text
+--------------------------------+
| <- Strumenti        privacy ON |
| Piano calcolato                |
| [v] Disponibile                |
| [Verificato in Decimal]        |
| [Ottimalità non provata]       |
+--------------------------------+
| Investito dopo  ≈••• € EUR     |
| Non investito   ≈••• € EUR     |
| Scarto L2       ≈••• EUR²      |
| Ordini          3              |
+--------------------------------+
| MOND  T 60,00%  D ≈60,62%      |
| T ===============              |
| D ###############              |
| OBBL  T 30,00%  D ≈29,81%      |
| EMER  T 10,00%  D ≈9,57%       |
+--------------------------------+
| [+] Esposizioni                |
| [+] Asset                      |
| [+] Piano operativo (3)        |
| [+] Saldi per Broker           |
| [+] Prova e solver             |
+--------------------------------+
| [ Modifica configurazione ]    |
+--------------------------------+
```

Stati: invalid, impossibile, calcolo in corso, non aggiornato.

```text
+--------------------------------+
| [x] Input non valido           |
| Nessun calcolo eseguito.       |
+--------------------------------+
| Liquidità · Demo A · EUR       |
| importo oltre il disponibile   |
|                   [ Vai ]      |
| Target                         |
| totale diverso da 100%         |
|                   [ Vai ]      |
+--------------------------------+
| [ Dettagli codici ]            |
+--------------------------------+
```

```text
+--------------------------------+
| [x] Impossibile con            |
|     questi vincoli             |
| Provato · oracolo esaustivo    |
+--------------------------------+
| Vincoli coinvolti:             |
| MOND · minimo obbl. ••• quote  |
|                   [ Vai ]      |
| Raggiungibile ••• € EUR        |
|                   [ Vai ]      |
+--------------------------------+
| [ Modifica configurazione ]    |
+--------------------------------+
```

```text
+--------------------------------+
| Calcolo in corso               |
| [spinner] Ricerca del piano    |
|                                |
| Snapshot rev. 18               |
| Configurazione bloccata.       |
|                                |
| [ Interrompi attesa ]          |
| Il server può finire lo        |
| stesso: la risposta viene      |
| scartata.                      |
+--------------------------------+
```

```text
+--------------------------------+
| [!] Risultato non              |
|     aggiornato                 |
| Risultato rev. 18              |
| Draft corrente rev. 19         |
|                                |
| [ Torna a Rivedi ]             |
| [ Scarta risultato ]           |
+--------------------------------+
| PRECEDENTE · NON CORRENTE      |
| ...                            |
+--------------------------------+
```

---

## 7. Privacy

Criterio del developer (decisione c, `09_reperti_analisi_statica_20260922.md` §4): *patrimonio è ciò
da cui si risale a quanto possiede l'utente*. La maschera è quella di J, a livello di formatter
(`maskable.ts`, default `personal`). Il PAC non scrive maschere proprie.

| Classe | Campi | Formatter |
|---|---|---|
| **Patrimonio** (mascherato) | cassa disponibile e quota tua, importo da usare (in sola lettura), contributi, tetti di funding, addebiti degli ordini, commissioni addebitate, FX addebitato/accreditato, perdita spread, costo margine, ledger, contabilità, valori target/dopo/scarto, L2, primale e duale degli stadi monetari, parametri monetari degli issue | `formatCurrencyAmountPlain`/`Html`, sensibilità `personal` |
| **Patrimonio** (mascherato) | quantità: istruzione e quantità economica (N6) | `maskable(…, 'personal')` |
| **Pubblico** | pesi e percentuali, esposizioni, prezzi di mercato per unità (fonte, mid, carico), tassi FX, spread %, passi, parametri di tariffa, conteggi, tempi | prezzi e tariffe: formatter valuta con `sensitivity: 'public'`; tassi e percentuali: `maskable(…, 'public')` |
| **Da confermare in R7** | tetti e minimi delle route, in quote o importo | **patrimonio per default**: mascherati nelle viste in sola lettura |

Regole di forma:

- Il segno resta fuori dalla maschera: `+••• € EUR`, `-••• € EUR` (decisione D8 della privacy di J, `currencyFormat.ts:40-41`; non è lo stato D8 del target).
- Il codice valuta resta visibile: `••• € EUR`.
- `≈` resta fuori dalla maschera, come il segno: `≈••• € EUR` (J, 24/09). Per un valore personale
  anche il ramo `exact_ratio` passa dalla maschera: sulla riga non resta nessuna cifra in chiaro, perché
  il gate di J (`SAFE_CALL`) giudica la riga intera.
- `maskable(…, 'public')` si usa solo per tassi e percentuali. Il gate salta le righe che la contengono,
  quindi non si usa mai per un valore che deriva da ciò che l'utente possiede.
- Un campo di input mostra ciò che l'utente sta scrivendo. Una volta confermato, si maschera come
  ogni altro valore in sola lettura. Da confermare in R7.

Adapter `planner/format.ts` (C7), unico punto di passaggio:

| Funzione | Classe | Note |
|---|---|---|
| `formatPlannerMoneyPlain` / `Html` | patrimonio | `ExactMoney` → formatter di J |
| `formatPlannerPricePlain` / `Html` | pubblico | `ExactPrice`, con `quote_base_quantity` |
| `formatPlannerQuantity` | patrimonio | via `maskable` |
| `formatPlannerFxRate` | pubblico | `ExactFxRate`, verso canonico |
| `formatPlannerPercent` | pubblico | `60,62%` |
| `formatPlannerL2` | patrimonio | `≈••• EUR²`: unità fuori dalla maschera |

Guardie comuni: vuoto o non finito → `—`, non mascherato; `exact_ratio` → `≈` + `display_decimal`,
con le cifre mascherate se il valore è personale; oltre 15 cifre significative si chiede a J. Nessun
`Intl.NumberFormat` o `toFixed` fuori dall'adapter. L2 mostra l'unità `EUR²` fuori dalla maschera.

Cifre decimali degli importi (Q-C0-1):

- nel risultato vengono da `catalogs.currencies[].minor_unit`, cioè dal backend;
- nel draft, prima di ogni calcolo, sono le cifre CLDR della valuta, lette dentro l'adapter con
  `new Intl.NumberFormat('en', {style: 'currency', currency}).resolvedOptions().maximumFractionDigits`.
  È lo schema di `features/ai-export/templates/snapshotDataRenderer.ts:226`, che il gate di J registra
  come falso positivo noto (`utils/privacy/moneyRenderSites.test.ts:174-176`). Il PAC aggiunge la voce
  gemella, passando dal coordinator. Formatta cifre e non calcola, quindi resta dentro Q-C0-2.

---

## 8. Domande e decisioni

### 8.1 Domande al developer (poste il 24/09; decise in 8.1.1)

Una alla volta, con l'opzione raccomandata per prima. Le risposte si registrano qui e in Round5 §2.
La tabella resta com'era quando le domande sono state poste: Q-C0-1 e Q-C0-2 sono state decise con una
strada che non era fra le opzioni.

| # | Domanda | Opzioni (1 = raccomandata) | Perché |
|---|---|---|---|
| Q-C0-1 | Quantum di valuta e copie senza Broker | 1. `minor_unit` in `/utilities/currencies`, e allocation-source che accetta `broker_ids` vuoto · 2. solo `minor_unit` · 3. quantum scritto a mano | N18: serve almeno un Broker `OWNER`, e `minor_unit` arriva solo dalla copia. Uno scenario tutto manuale non ha fonte per il quantum. |
| Q-C0-2 | Aritmetica locale | 1. solo esatta e nella stessa unità: totale e restante del target, totali nativi per valuta (mascherati), selezionato ≤ disponibile · 2. solo totale del target · 3. nessuna | Il target ammette «somma esatta e restante» e «totali nativi» (`UiTarget:183,187`). L'«equivalente indicativo» che ammette anche (`:183`) è una conversione, e l'opzione 1 lo esclude. Il Passo C3 di Round5 dice «nessuna aritmetica»: va riallineato. |
| Q-C0-3 | Dato stale | 1. stale ⇔ data < `as_of`; età visibile; conferma per riga e «Conferma tutti»; prezzi sul wire come `stale{age_days, accepted}`, FX solo in UI · 2. soglia di N giorni · 3. solo conferma per riga | N15: il wire non porta la freschezza FX. |
| Q-C0-4 | Passo 8 | 1. solo la card proporzionale, preselezionata, con la cascata; `min_fragmentation` più avanti · 2. card `min_fragmentation` disabilitata · 3. nascondere il passo | N1: `min_fragmentation` riesce sui domini piccoli e fallisce sui grandi. Decisione in R2. |
| Q-C0-5 | Tetto delle route | 1. obbligatorio in UI ora; tornare a `none` si decide in R1 · 2. `{kind:"none"}` sul wire subito · 3. obbligatorio per sempre | N16. |
| Q-C0-6 | «Copia distribuzione corrente» | 1. nuova sezione backend con pesi esatti per Asset canonico · 2. rimandare | Il target la vuole come base modificabile (`UiTarget:187,1180,1194`). Nessuna API la pubblica oggi. |
| Q-C0-7 | Somma delle esposizioni > 100% (N22) | 1. correzione nel normalizer in questa fetta: nuovo issue `invalid`, i18n, fingerprint, test · 2. blocco solo in UI · 3. rimandare | Oggi il normalizer non la rifiuta, e il report fallisce più avanti. |
| Q-C0-F | Approvazione del delta | 1. approvato · 2. approvato solo desktop · 3. non approvato | Gate C0. |

### 8.1.1 Decisioni del developer (24/09)

La mattina il developer non era disponibile (alla Q-C0-1: «non disponibile, lavora in autonomia») e
avevo scritto dei default provvisori. Il pomeriggio ha risposto in tre giri: `ask_user`, chat e
`ask_user` sul dettaglio di Q-C0-6. Le sue decisioni sostituiscono tutti quei default. Le citazioni
sono testuali.

| # | Decisione | Parole del developer | Effetto |
|---|---|---|---|
| Q-C0-1 | Il quantum lo ricava il backend da babel; `currency_specs` esce dal wire | «cambiamo la api semplicemente, tanto le valute sono standard e vincolate ad essere quelle di babel» | Niente campo manuale e niente `/utilities/currencies`: `minor_unit` = `10^-cifre` CLDR (`get_currency_precision`). Esce dalla request dei tre planner e dalla risposta della copia. Uno scenario tutto manuale non ha più bisogno della copia (N18). Round5 C0b.1. |
| Q-C0-2 | Nella UI solo percentuali di controllo | «se si tratta di fare percentuali, ovviamente li può fare anche la ui, ma devono essere di controllo/informativi, quelli dei risultati stanno nel backend» | Totale e restante del target; «selezionato ≤ disponibile» nella stessa unità. Nessuna somma di importi: il riepilogo della liquidità conta le fonti. Lettura prudente, da confermare in R1. |
| Q-C0-3 | Si mostra l'età, nessuna conferma | «vale giusto la pena mostrare se è del giorno precedente di quanti giorni è, ma in ogni caso la scelta finale è dell'utente» | Età in giorni per prezzi e tassi non del giorno. Prezzi sul wire come `stale{age_days, accepted: true}`; l'età FX resta solo in UI (N15). |
| Q-C0-4 | `min_fragmentation` esce dal wire | «semplicemente non mettiamola, la ui in questo deve essere dinamica» | `policy` = `Literal["proportional"]` per il PAC. Il Passo 8 legge le opzioni dal contratto generato. Round5 C0b.2. |
| Q-C0-5 | Tetto obbligatorio, default alto con TODO | «per ora se ti devi predisporre metti un numero alto e un todo che dice che andrà ridotto quando si saranno fatte le simulazioni sui tempi di esecuzione» | Default UI `1000000000` nell'unità della modalità, in `planner/defaults.ts` con il TODO. Il wire non cambia. |
| Q-C0-6 | «Copia distribuzione corrente» si fa, dal motore del portafoglio | «è un ottima idea facciamola»; fonte scelta: «Motore del portafoglio (numeri della pagina Allocazione)» | Nuova sezione `current_distribution` della copia; dialogo in §3.6. Round5 C0b.4. |
| Q-C0-7 | Nuovo issue `invalid` | «il codice invalid è la scelta giusta» | `allocation.exposure_total_exceeds_one` nel normalizer. Round5 C0b.3. |
| Q-C0-F | Delta approvato | «ho letto il piano e guardato le ascii mi paiono coerenti, quello che avevamo pianificato in origine, hai il mio via libera, ovviamente poi faremo la review» | Le viste nascono da questo documento; la review di dettaglio resta allo STOP. |

Un fatto utile per Q-C0-5: il tetto alto non allarga il dominio. Il limite di ogni ordine è il minimo
fra tetto e risorse (`evaluator.py:784-845`), e `compiler.py:146` lo passa a SCIP come `ub`: un tetto
sopra le risorse non cambia né l'oracolo né il solver. Il numero va comunque rimisurato con le soglie
crescenti (Step 3, punto 13).

### 8.2 Default applicati senza domanda

| Default | Motivo |
|---|---|
| Funding: priorità 0, tetto = importo della fonte | nessuna preferenza implicita |
| Route: priorità 0, minimi «nessuno», margine 0, tetto `1.000.000.000` (Q-C0-5) | idem; il tetto alto non allarga il dominio |
| Snapshot: UUID + revisione monotona | protezione da risposte vecchie (T2) |
| Provenance: un record per riga manuale | ogni fatto porta un `provenance_id`; un id assente dà `allocation.provenance_not_found` (`normalize.py:140-142`) |
| Deployment: «non calcolato» | W16 |
| `asset_class` in minuscolo prima dell'invio | N12 |
| Messaggi PAC-locali per i `ToolError` | N17 |
| Ledger trasposto (Broker × valuta in colonna) | leggibilità; nessun dato perso |
| Sequenze solo dal backend | nessun riordino nel frontend |
| `fx_cost`, `buffer`, `explanation_keys` non mostrati sulla riga | N23: costanti in 2.0.0 |
| Chiave FX in ordine canonico, solo da selettore | N20 |

---

## 9. Reperti nuovi (N10–N23)

N1–N9 sono in Round5 §1.2. Qui ci sono quelli emersi dal confronto col wire. Ognuno ha
l'evidenza nel codice e l'effetto sulla UI.

| # | Reperto | Evidenza | Effetto sulla UI |
|---|---|---|---|
| N10 | Una tariffa ha **una sola valuta**, e deve essere quella del prezzo dell'Asset | `normalize.py:369-373` (fisso, minimo e tetto nella stessa valuta, altrimenti `allocation.currency_mismatch`); `:539-540` (valuta della tariffa ≠ valuta del prezzo della route → `currency_mismatch`) | Una valuta per tariffa, preimpostata sulla valuta del prezzo. Un Broker che addebita la commissione in un'altra valuta non si rappresenta in 2.0.0. |
| N11 | Un tetto o un minimo del tipo sbagliato dà `reference_not_found`, non un codice di tipo | `normalize.py:556-557` (tetto), `:567` (minimi) | Il tipo di tetto e minimo segue la modalità d'ordine scelta, e l'utente non lo sceglie. Il messaggio per `reference_not_found` su `cap`/`minimum_*` si specializza in base al path. |
| N12 | `asset_class` deve essere minuscolo; la copia lo dà maiuscolo | pattern `PlannerCode` `schemas/pac_allocator.py:166,245`, campo `:458`; la copia usa `asset.asset_type.value` (`portfolio_allocation_source.py:615`), valori `STOCK`/`ETF`/`BOND` (`db/models.py:183-185`), tipo `str` (`schemas/portfolio.py:1361`) | Inviato così com'è, dà l'errore di piattaforma `invalid_parameters` (`worker.py:110-112,175`), non un issue. Il mapper lo porta in minuscolo (T3). |
| N13 | Priorità: **più bassa = preferita**; negativa rifiutata | `objectives.py:150-151` (si minimizza la somma priorità × attiva); `normalize.py:521-522` (`allocation.route_priority_negative`) | Etichetta «priorità (0 = preferita)». Nessun ordinamento invertito in UI. |
| N14 | Nessuna modalità «solo nativa» | lo scenario ha solo `fx_rates` e uno `fx_spread_rate` globale (`schemas/pac_allocator.py:734-735`); lo stesso tasso serve a valutare e a convertire | Non si può dire «valuta questa cassa ma non convertirla». In UI nessun interruttore «converti sì/no». Il tema torna in R3. |
| N15 | Il wire non porta la freschezza del tasso FX | `fx_rates: dict[str, PlannerFixedDecimal]` (`:734`); i prezzi invece hanno `freshness` con `AcceptedStaleObservation{age_days, accepted}` (`normalize.py:152-158`) | L'età del tasso FX vive solo in UI, senza conferma (Q-C0-3). |
| N16 | Il tetto della route è **obbligatorio**; non esiste «nessun tetto» | `OrderCap = Union[QuantityOrderCap, NotionalOrderCap]` (`schemas/pac_allocator.py:642-656`); campo `cap` (`:668`) | Obbligatorio anche in UI, precompilato a `1.000.000.000` e modificabile (Q-C0-5). |
| N17 | I 16 `ToolErrorCode` hanno messaggi solo sotto `risk.errors.*` | codici `schemas/tools.py:28-45`; i18n `en.json:3208-3223` (`risk.errors.*`); nessuna chiave sotto `tools.*` | Messaggi PAC-locali per i 16 codici (64 voci). Un namespace comune `tools.errors.*` tocca il perimetro Risk: lo propongo al coordinator. |
| N18 | La copia richiede **almeno un Broker `OWNER`**; `minor_unit` arriva solo dalla copia | W17 `schemas/portfolio.py:1263-1285,1367-1384`; W20 `:1322-1326` | **Parte quantum superata da Q-C0-1**: il backend ricava il `minor_unit` da babel, e uno scenario tutto manuale non ha più bisogno della copia. Resta vero che ogni copia, compresa la distribuzione corrente (Q-C0-6), richiede almeno un Broker `OWNER`. |
| N19 | Liquidità selezionata = raggiungibile + intrappolata | `evaluator.py:584-586`; `schemas/pac_allocator.py:1681-1682,2000-2001` | La contabilità mostra la quota intrappolata (mascherata), con la spiegazione: selezionata ma non raggiungibile per i tetti di funding. |
| N20 | Una chiave `fx_rates` malformata dà un errore di piattaforma, non un issue | `_validate_fx_rate_pair_keys` (`schemas/pac_allocator.py:744-752`) → `invalid_parameters` | La chiave nasce solo dal selettore, in ordine canonico. |
| N21 | La valuta del passo monetario è **ignorata** | `normalize.py:349-352` controlla solo il codice e il segno; `:870` tiene solo `.amount`. Un passo «1 USD» su un Asset in EUR vale 1 EUR. | Il passo si mostra nella valuta del prezzo e non si sceglie. Correzione backend candidata (`currency_mismatch`): la porto in R1. |
| N22 | Una somma di esposizioni > 100% per Asset e dimensione non è rifiutata | `normalize.py:258-274` controlla solo il singolo peso e i duplicati; `planner_report.py:330` fa `undeclared = 1 − dichiarato` senza limite, quindi la riga non classificata diventa negativa | **Provato il 24/09** con una sonda fuori dal repo: `planner.py:171 > 250 > 333` → `planner_report.py:291 > 370 > 404` → `ValidationError` in `PacExposurePlanRow` → `execution_failed`. Si corregge nel normalizer con l'issue `invalid` nuovo (Q-C0-7, Round5 C0b.3); TB4 fissa prima l'esito attuale. |
| N23 | Sulla riga d'ordine `fx_cost`, `buffer` e `explanation_keys` sono costanti | `planner_report.py:568-570` | Non si mostrano per riga. Il costo FX sta sull'azione FX (`spread_loss`). |

---

## 10. Delta della test list

Si aggiunge alla lista di Round5 Passo D. I test UI vanno al developer come lista; i test backend
passano da test-author.

### 10.1 Frontend

| Test | Aggiunta |
|---|---|
| T3 request builder | `asset_class` in minuscolo (N12). Chiave FX solo canonica (N20). Tipo di tetto e minimo dalla modalità d'ordine (N11). Passo monetario nella valuta del prezzo (N21). Liquidità selezionata ≤ disponibile, senza conversioni (Q-C0-2). Nessun `currency_specs` (Q-C0-1). `policy` dal contratto (Q-C0-4). Prezzo non del giorno → `stale{age_days, accepted: true}` (Q-C0-3). Tetto precompilato `1000000000` (Q-C0-5). |
| T5 stati da fixture | Tutti gli stati della matrice §5.1, compresi quelli che 2.0.0 non produce (N8): `gap_bounded`, `score_lattice_closure`, `deterministic_conflict`, `time_limit`, `node_limit`, `ready_no_incumbent`. Solo fixture, dichiarato nel nome del test. |
| T6 issue | Messaggi PAC-locali per i 16 `ToolErrorCode` (N17). `reference_not_found` su `cap`/`minimum_*` con il messaggio di tipo (N11). «Riprova» solo con `retryable`. |
| T7 privacy | Segno e `≈` fuori dalla maschera (D8 di J). Codice valuta visibile. Liquidità intrappolata mascherata (N19). Tetti e minimi delle route mascherati in sola lettura (default fino a R7). Prezzi con `sensitivity: 'public'`, tassi e percentuali in chiaro. |
| **T7b** quantità | Richiesto da J. Con la privacy ON, istruzione e quantità economica sono `•••` via `maskable(…, 'personal')`; con la privacy OFF sono in chiaro. Nessuna cella espone insieme quantità in chiaro e prezzo pubblico. Caso `≈` (J, 24/09): un valore personale `exact_ratio` con la privacy ON rende `≈•••`, senza cifre. |
| T8 registro | Invariato. |
| **T10** copia distribuzione corrente | Q-C0-6. Il dialogo mostra fonte, data, Broker `OWNER` ed età dei prezzi. «Usa come target» applica i pesi solo alla conferma; un target già modificato apre il conflitto B4. Asset manuale → 0 con nota. `incomplete` → pulsante disabilitato; `no_holdings` → nessun target cambiato. Solo pesi, nessun importo. |

### 10.2 Backend (via test-author, lane 6151)

| Test | Scopo |
|---|---|
| TB1–TB3 | Round5 Passo D: API del tool (con `min_fragmentation` rifiutata dal codec, Q-C0-4), API di `allocation-source`, `tools-registry`. |
| **TB4** | N22 e Q-C0-7: prima fissa l'esito attuale (`execution_failed`), poi attende `allocation.exposure_total_exceeds_one` (`invalid`), 79 codici e il fingerprint aggiornato. |
| **TB5** | Q-C0-1: una request con `currency_specs` è wire-invalid; `minor_unit` CLDR nei cataloghi (JPY `1`, EUR `0.01`, KWD `0.001`); uno scenario tutto manuale arriva a `ready_*` senza copia. |
| **TB6** | Q-C0-6: sezione `current_distribution`. Pesi del motore, denominatore = scenario, resti maggiori con parità per `asset_id`, `incomplete`, `no_holdings`, 403 per un Broker non `OWNER`, nessun importo nella risposta. |

### 10.3 Runbook

| Scenario | Aggiunta |
|---|---|
| S2 | Il caso piccolo di §0.1 (2.211 candidati, 1.020 ammissibili): l'oracolo decide e la prova è `optimal_proven` con `exhaustive_oracle`. Tutto manuale: con Q-C0-1 non serve nessuna copia. |
| S9 | Lo scenario testimone di §0.1: le decisioni di funding al centesimo superano 200.000 candidati → `not_proven`. |
| S14 | Privacy ON/OFF come T7 e T7b. |
| S16 | «Copia distribuzione corrente» sui dati del developer: pesi uguali a quelli della pagina Allocazione quando lo scenario comprende tutti gli holding (Q-C0-6). |
