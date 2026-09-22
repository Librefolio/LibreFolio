# Round 5 — PAC/Rebalancer operational planner

> **ARCHIVIO:** piano superato, non specifica corrente. L'entrypoint della suite
> target è
> [`../plan-phase00PacRebalancerTargetDesign.prompt.md`](../plan-phase00PacRebalancerTargetDesign.prompt.md).
> Ogni riferimento sotto a design o piano “corrente” conserva soltanto il
> contesto storico del round in cui fu scritto.

**Stato:** SUPERSEDED / STORICO — contratto raffinato dalla UI Round 6 approvata;
esecuzione sostituita dal piano Round 7. Nessun codice production/test è stato
autorizzato o consegnato da questo documento.

← Previous: [Round 4 — PAC + Ribilanciamento P1 multi-servizio](plan-phase00Step2Round4-PacAndRebalancerUiAcceptance.prompt.md)

→ Follow-up:
[Round 6 — PAC/Rebalancer UI Blueprint](plan-phase00Step2Round6-PacRebalancerUiBlueprint.prompt.md)

→ Piano implementativo successivo nel percorso storico:
[Round 7 — PAC/Rebalancer operational migration](plan-phase00Step2Round7-PacRebalancerOperationalMigration.prompt.md)

↔ Supersedes and re-scopes:
[Solver operativo PAC + Ribilanciamento](plan-phase00Step3-PacRebalancingSolver.prompt.md)

**Design prodotto normativo del round storico:**
[PAC/Rebalancer end-to-end design](pac-rebalancer-end-to-end-design.md).

> Il corpo seguente conserva il gate operativo precedente alla review UI. Dove
> differisce da Round 6, dal design end-to-end corrente o da Round 7, prevalgono
> questi ultimi; Round 5 non è più un piano eseguibile.
>
> **Correzione successiva — 2026-09-16:** tutte le formulazioni PAC/Rebalancer
> nel corpo sono storiche. L'autorità corrente usa target monetari fissi e
> primario globale `L2_fixed → U`, con tier operativi distinti; la variante
> congela tutte le azioni e aggiunge BUY secondo `U → L2_fixed`. Percentuali,
> D∞ e D1 sono diagnostici. PySCIPOpt/SCIP è candidato additivo approvato, ma
> dependency/probe/capacità e payload restano gate Round 7.

**Cronologia storica:**
[PAC/Rebalancer decision chronicle](pac-rebalancer-decision-chronicle.md).

Copie di handoff byte-identiche:

- `/tmp/libreFolio_pac_rebalancer_end_to_end_design.md`;
- `/tmp/libreFolio_pac_rebalancer_decision_chronicle.md`.

## 0. Mandato, baseline e vincoli

| Campo | Valore |
|---|---|
| Worktree | `/Users/ea_enel/Documents/00_My/LibreFolio-worktrees/e-alfy-friendly-dollop` |
| Branch | `e-alfy-allocatore-pac` |
| Baseline combinata | `e38a521f068c2d1b8d743775e90711fec1326fb3` |
| Lane futura | porta `6153`, dati `/tmp/librefolio-r2-d` |
| Venv condiviso | `PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc` |
| Coordinatore nel kickoff | `12a0954d-0fbe-42da-b687-979e798a50c6` |
| Contatto coordinatore attivo | `c8328a01-f208-4ade-a352-0486d1f14de2` |
| Stato repository all'avvio | solo `TODO_FUTURI.md` modificato, modifica autorizzata |
| Versione pubblica finale | `contract_version="1.0.0"`, feature mai rilasciata |

Questo round è soltanto pianificazione. Non autorizza:

- implementazione production/test;
- avvio server, build, lint, suite, DB o probe;
- installazione solver o dipendenze;
- API sync, i18n, traduzioni o graph update;
- staging, commit, merge, rebase, push o altre mutazioni Git;
- lettura di portafogli, export o valori personali.

Il nome richiesto segue la convenzione esistente
`plan-phase00Step2RoundN-Descrizione.prompt.md`; nessuna deviazione.

### 0.1 Fonti e autorità

Ordine di prevalenza:

1. decisioni developer più recenti;
2. [design operativo corrente](pac-rebalancer-operational-design.md);
3. questo piano;
4. codice alla baseline;
5. [cronologia](pac-rebalancer-decision-chronicle.md);
6. prototipi/piani storici.

Fonti obbligatorie:

- [backlog PAC/Tool](../../09_feedbackJobs/05_pac_allocation_tool.md);
- [piano sprint completo](../../09_feedbackJobs/06_piano_sprint.md);
- [indice feedback](../../09_feedbackJobs/README.md);
- [studio PAC multi-ETF](../../../guida_allocazione_pac_multi_etf.md);
- [Round 4 respinto](plan-phase00Step2Round4-PacAndRebalancerUiAcceptance.prompt.md);
- [solver storico superato](plan-phase00Step3-PacRebalancingSolver.prompt.md);
- [contratto P1 storico](pac-allocator-contract.md);
- [UX P1 storica](pac-allocator-ux.md);
- [evidenze P1](pac-allocator-evidence.md);
- [deferred backlog](../../../../../TODO_FUTURI.md).

## 1. Obiettivo

Sostituire integralmente il prototipo P1 analysis-only con due Tool operativi ma
non esecutivi:

1. **PAC allocator**: distribuisce la liquidità selezionata tra Asset target e
   produce funding, FX e ordini BUY per Broker.
2. **Portfolio Rebalancer**: avvicina l'intero portafoglio ai pesi finali con
   `invest_only` oppure, solo se scelto, `invest_and_sell`.

I due servizi mantengono:

- card, route, copy e semantica prodotto distinte;
- stesso plugin multi-servizio;
- stesso core puro per Decimal, ledger, fee, FX, quantizzazione, evaluator e
  solver;
- stesso confine Tool atomico: payload completo in ingresso, risultato completo
  in uscita, nessun lookup runtime.

### 1.1 Risultato utente atteso

Ogni run valido produce:

- soluzione policy-base;
- soluzione con recupero del residuo, se computabile;
- grafico acquisti/vendite;
- confronto `Ora / Target / Dopo`;
- card Tipo, Settore e Geografia, inclusa `Unknown`;
- istruzioni di funding/trasferimento;
- conversioni FX;
- tabelle ordini per Broker;
- fee, riserva fiscale, costo FX, buffer, residui e riconciliazione cassa;
- esito, prova, motivo di stop, limiti e spiegazioni backend.

Nessun ordine viene inviato al Broker.

**Complessità:** XL. Nuovo dominio combinatorio, schema pubblico, copie dominio,
UI multi-step e integrazione trasversale. L'ampiezza non autorizza una Fleet
prima del contract freeze.

## 2. Non-obiettivi

- Nessun cambio a FIFO, WAC, motori lotti o regime fiscale applicativo.
- Nessuna strategia consigliata automaticamente.
- Nessun riuso dell'optimizer storico Riskfolio.
- Nessun routing verso Broker non selezionati.
- Nessun supporto short, leva, marginazione o ordini impliciti.
- Nessun `/tools/prefill`.
- Nessun calcolo economico autorevole nel frontend.
- Nessuna persistenza automatica di fonti o Broker manuali scenario-only.
- Nessuna persistenza dei parametri operativi Broker nella v1: restano input
  per-run; la futura configurazione DB è tracciata in `TODO_FUTURI.md`.
- Nessuna fee dipendente da mercato o sequenza intraday nella v1.
- Nessuna ottimizzazione fiscale nella v1.
- Nessun trasferimento modellato con fee, settlement o limite nella v1.
- Nessuna compatibilità con il contratto P1 scartato.

## 3. Verità corrente e clean break

### 3.1 Piattaforma da riusare, non duplicare

| Superficie corrente | Simboli/ruolo | Decisione Round 5 |
|---|---|---|
| `backend/app/services/tools/base.py` | `ToolService`, `ToolPlugin`, `ToolExecutionContext` | Riusare senza creare una seconda piattaforma. |
| `backend/app/services/tools/registry.py` | discovery, descriptor, fingerprint | Cambi soltanto se il contratto reale dimostra un gap generale; lease coordinatore. |
| `backend/app/services/tools/catalog.py` | catalogo effettivo | Nessun endpoint schema separato. |
| `backend/app/services/tools/executor.py` | admission, code, limiti, processi | Non incorporare logica PAC. |
| `backend/app/services/tools/worker.py` | validazione/compute/output isolati | Worker senza DB/principal/provider. |
| `backend/app/api/v1/tools.py` | catalog/compute/diagnostics autenticati | Nessuna route PAC dedicata. |
| `backend/app/schemas/tools.py` | envelope Tool | Non aggiungere campi finanziari al generico envelope. |
| `frontend/src/lib/features/tools/ToolsHub.svelte` | hub e stato catalogo | Conservare host generico. |
| `frontend/src/lib/features/tools/ToolHost.svelte` | compatibilità e mount renderer | Conservare fail-closed. |
| `frontend/src/lib/features/tools/registry.ts` | import compilati | Un solo writer durante integrazione. |
| `frontend/src/lib/features/tools/contracts.ts` | account generation e compatibilità | Riusare guardie, non indebolirle. |
| `frontend/src/lib/features/tools/client.ts` | catalogo, compute, abort/stale | Riusare snapshot e cleanup. |

### 3.2 Prototipo P1 respinto

| Superficie corrente | Verità corrente | Azione futura |
|---|---|---|
| `backend/app/schemas/pac_allocator.py` | `PacAnalyzeInput`, `RebalanceAnalyzeInput`, output/issues P1 | Sostituire con input/output `operation="plan"` e union operative. |
| `backend/app/services/pac_allocator/__init__.py` | `analyze_pac_budget`, `analyze_rebalancing` | Rimuovere facade analysis-only; esporre normalizzazione/solve/evaluate finali. |
| `backend/app/services/pac_allocator/normalize.py` | normalizza draft P1 | Riutilizzare solo primitive dimostrate; riscrivere dominio finale. |
| `backend/app/services/pac_allocator/evaluator.py` | analisi Decimal senza ordini | Conservare disciplina Decimal, non contratto P1. |
| `backend/app/services/pac_allocator/report.py` | report teorico | Sostituire con report operativo e riconciliazione. |
| `backend/app/services/pac_allocator/models.py` | dataclass numeriche P1 | Riutilizzo simbolo-per-simbolo solo dopo verifica; nessun adapter P1. |
| `backend/app/services/pac_allocator/numeric.py` | helper Decimal puri | Candidati al riuso: `decimal_context`, `decimal_text`, `exact_holding_value`, `ratio_approximation`. |
| `backend/app/services/tool_plugins/pac_allocator.py` | due servizi, operation `analyze` | Conservare i due `tool_code`; sostituire input/output/operation/compute. |
| `frontend/src/lib/features/tools/pac-allocator/PacAllocatorTool.svelte` | UI PAC P1 | Riscrivere come wrapper PAC del planner. |
| `frontend/src/lib/features/tools/pac-allocator/PortfolioRebalancerTool.svelte` | UI Rebalancer P1 | Riscrivere come wrapper Rebalancer del planner. |
| `frontend/src/lib/features/tools/pac-allocator/*ResultPanel.svelte` | report analysis-only | Eliminare o sostituire con risultati operativi. |
| `frontend/src/lib/features/tools/pac-allocator/allocationSource.ts` | copie P1 | Rifare contro snapshot dominio finale; preservare stale/account guard. |
| `backend/test_scripts/test_services/test_pac_analyze.py` | test P1 | Eliminare/sostituire tramite `test-author`. |
| `backend/test_scripts/test_api/test_pac_tool_api.py` | API P1 | Riscrivere sul servizio `plan`. |
| `backend/test_scripts/test_schemas/test_pac_analyze_schemas.py` | schema P1 | Riscrivere sui discriminanti finali. |
| guide MkDocs PAC/Rebalancer | dichiarano no-solver/no-order | Riscrivere tramite `docs-writer`. |

Il clean break è obbligatorio:

- `operation="analyze"` eliminata;
- `report_currency` eliminato;
- vecchi schema, renderer, fixture, test e chiavi i18n eliminati quando privi di
  consumer finali;
- nessun adapter, alias, fallback, dual version, feature flag o path legacy;
- `tool_code` pubblici restano `pac_allocator` e `portfolio_rebalancer`;
- `contract_version`, `implementation_version` e UI SemVer finali restano
  `1.0.0`, perché nessuna versione è stata rilasciata.

## 4. Decisioni pre-implementazione

| ID | Decisione | Stato | Gate |
|---|---|---|---|
| D01 | PAC e Rebalancer restano due servizi/UI distinti; core condiviso. | CONGELATA | Nessuno. |
| D02 | Un solo submit: snapshot completo → compute → risultati. | CONGELATA | Nessuna preview solver negli step. |
| D03 | Worker atomico, puro, senza DB/provider/service lookup. | CONGELATA | Test worker con lookup vietati. |
| D04 | Asset aggregato per identità canonica; custodia Asset×Broker preservata. | CONGELATA | Mai matching per nome. |
| D05 | Cash per sorgente/Broker/valuta; solo importo selezionato. | CONGELATA | Riconciliazione ledger nativa. |
| D06 | Fonti manuali e Broker manuali sono scenario-only. | CONGELATA | Nessuna scrittura automatica. |
| D07 | Parametri operativi Broker sono input per-run; Broker esistente precompila solo fatti già disponibili. | CONGELATA | Nessuna migration v1; persistenza differita. |
| D08 | Utente dichiara solo se il Broker accetta ordini frazionati per valuta; `share_quantity`/`cash_amount` sono output backend. | CONGELATA | Nessun `order_entry_mode` o `quantity_step` input. |
| D09 | `fee_buy` e `fee_sell` indipendenti: fisso + rate + min/max. | CONGELATA | Nessuna fee implicita. |
| D10 | FX solo single-hop dichiarato, debit/credit accoppiati, niente cicli. | CONGELATA | Invarianti cash/oracle. |
| D11 | Buffer FX opzionale, default 0, resta cassa e non è fee. | CONGELATA | Non sottrarre due volte. |
| D12 | PAC: base deterministica; `proportional`/`min_fragmentation` governano il solo residuo. | CORRETTA 2026-09-15 | Nessun solve minimax/D² per la base. |
| D13 | Rebalancer: `invest_only`, `invest_and_sell`; default invest-only. | CONGELATA | Nuova liquidità prima delle vendite. |
| D14 | Base + residual-optimized nello stesso output, senza booleano utente. | CORRETTA 2026-09-15 | Ordini base monotoni; score può peggiorare con delta visibile. |
| D15 | Valuta di riferimento è un campo Step 1, prefilled dalla valuta default utente e modificabile. | CONGELATA | Solo metro per pesi/grafici; worker non legge preferenze. |
| D16 | Trasferimenti v1 dichiarati, gratuiti e immediati. | CONGELATA | Limiti/fee/settlement differiti. |
| D17 | PMC, aliquota plusvalenze Asset, regime e minus pregresse entrano nello snapshot; v1 riserva imposta senza compensazioni nascoste. | CONGELATA | Fee SELL → gain positivo → tax reserve → cash netto. |
| D18 | Minor unit valutaria è regola backend, `ROUND_HALF_UP`; non campo UI. | CONGELATA | Test per valuta. |
| D19 | Nessuna tolleranza target nascosta; il residuo può peggiorare D∞/D1 per aumentare l’investito e mostra il delta. | CORRETTA 2026-09-15 | Decimal canonicalizza entro una minor unit senza rilassare fattibilità fisica. |
| D20 | Fiscalità SELL v1: aliquota Asset esplicita, prefill `26%`, applicata al gain positivo dopo fee SELL. | **RISOLTA 2026-09-15** | Formula e rounding testati; nessun input fiscale alternativo. |
| D21 | `withholding_kind` è output derivato dal regime, non un altro input: `broker_withheld` per amministrato, `self_reserved` per dichiarativo/libero. | CONGELATA | Entrambi escludono la riserva dai BUY; solo il secondo resta cash fisico. |

### 4.1 Fiscalità SELL v1 — decisione chiusa

Ogni Asset porta `capital_gains_tax_rate`, rapporto Decimal `[0,1]`. La UI lo
pre-popola a `0.26` e l'utente può modificarlo. Per ogni SELL:

1. calcolare il provento lordo;
2. sottrarre `fee_sell`;
3. sottrarre il costo PMC della quantità venduta;
4. applicare l'aliquota soltanto alla plusvalenza positiva;
5. arrotondare la riserva fiscale nella valuta ledger;
6. rendere disponibile al solver solo provento meno fee meno riserva.

`tax_regime` e minusvalenze pregresse restano fatti espliciti, ma v1 non applica
compensazioni né strategie fiscali implicite. Non resta un blocker prodotto.
Il backend deriva `withholding_kind`: `broker_withheld` con regime
`administered`, `self_reserved` con `declarative_free`. In entrambi i casi il
tax reserve non finanzia BUY; nel secondo resta fisicamente sul conto e viene
mostrato come riserva dell'utente.
La schedule v1 è per riga SELL Asset×Broker: fee → gain positivo → rounding
tax reserve → disponibilità BUY nello stesso candidato. Nessun netting
giornaliero, compensazione tra righe o rinvio implicito della riserva.
Il PMC usato nel calcolo deve essere già nella valuta fiscale/ledger del SELL,
oppure accompagnato da conversione esplicita, fonte e data. Un PMC non
riconciliabile produce `needs_input`, mai una conversione implicita.

## 5. Flusso finale

1. **Scope/Tool**
   - PAC oppure Rebalancer;
   - data snapshot;
   - valuta di riferimento scelta dall'utente, pre-popolata dalla valuta
     predefinita dell'account.
2. **Liquidità e fonti**
   - nuova liquidità;
   - importo selezionato da conto/Broker esistente;
   - fonte manuale.
3. **Broker operativi**
   - Broker esistente con profilo precompilato;
   - Broker manuale scenario-only;
   - override locali espliciti.
4. **Asset, posizioni e route**
   - copia/manuale;
   - custodie Asset×Broker;
   - PMC;
   - Broker eleggibili, priorità, hard minimum opzionale e cap per Asset.
5. **Target**
   - PAC: distribuzione nuova liquidità;
   - Rebalancer: distribuzione finale intero portafoglio;
   - nessuna preview economica frontend.
6. **FX potenzialmente necessari**
   - coppie derivate dalle route ammesse;
   - spot, fonte, timestamp/age, spread, buffer, fee.
7. **Strategia**
   - PAC: proportional/min_fragmentation;
   - Rebalancer: invest_only/invest_and_sell.
8. **Review snapshot**
   - payload completo, unità, override, stale facts, limiti;
   - conferma esplicita; nessun binding live.
9. **Compute**
   - un item Tool, `operation="plan"`.
10. **Risultati**
    - grafici reali;
    - base/optimized;
    - funding/FX;
    - ordini Broker;
    - esito/prova/limiti/issues.

## 6. Contratto dominio finale

Tutti i modelli Pydantic hanno `extra="forbid"`. Ogni alternativa esclusiva è una
union discriminata. Gli input Decimal sono stringhe finite, fixed-point,
locale-independent; la UI può mostrare la virgola ma serializza con punto. Nessun
`float` attraversa il core.

### 6.1 Unità canoniche

| Concetto | Unità wire |
|---|---|
| denaro | stringa Decimal + currency |
| quantità Asset | stringa Decimal in unità titolo |
| prezzo | denaro per `quote_base_quantity` |
| target/peso | rapporto Decimal `[0,1]`, somma esatta `1` |
| fee rate/spread/buffer | rapporto Decimal `[0,1)`, non percentuale 0–100 |
| priorità Broker | intero `>=0`, minore = preferito |
| timestamp | ISO 8601 timezone-aware |
| data fiscale/as-of | ISO date |
| età spot | derivata da timestamp/as-of; riportata, non autorità separata |

#### 6.1.1 Confine campi utente / risultati

Un valore copiato dal sistema diventa input solo dopo essere stato mostrato e
confermato nello snapshot. Il piano non presenta variabili solver come campi.

| Step | Input utente (manuale o prefilled/editabile) |
|---|---|
| Scope | Tool, data, valuta di riferimento |
| Liquidità | fonte, valuta, saldo dichiarato/conosciuto, importo da usare, route consentite |
| Broker | Broker esistente/manuale, valute, FX mode, valuta addebito, frazioni ammesse, step importo, fee BUY/SELL, regime, minus |
| Asset | identità, prezzo/valuta/base quote, quantità correnti, PMC, aliquota plusvalenze, classificazioni |
| Route | Broker eleggibili per Asset, priorità, vincoli BUY/SELL con minimi condizionali/hard e cap tipizzati |
| Target | pesi PAC oppure pesi finali Rebalancer |
| FX | coppia, spot, fonte/data, spread, buffer, fee |
| Strategia | `pac_policy` oppure `trade_mode` |

| Solo output backend | Motivo |
|---|---|
| numero di titoli da comprare/vendere | variabile decisionale quantizzata |
| importo cash da inserire nel Broker | variabile decisionale quantizzata |
| quantità stimata per ordine cash | derivata dal prezzo |
| funding e trasferimenti | allocazione di cassa |
| conversioni FX | decisione di funding |
| fee, tax reserve, addebiti/accrediti | calcolo economico |
| before/target/after, deviazioni, residui | valutazione candidato |
| outcome/proof/stop | stato solver |

### 6.2 Radice comune

```text
PlanningScenario
├── scenario_id
├── as_of
├── valuation_currency       # input visibile, prefilled ma modificabile
├── funding_sources[]
├── trading_brokers[]
├── assets[]
├── fx_facts[]
└── target[]
```

`scenario_id` correla UI/result ma non autorizza lookup. Limiti solver, timeout e
cancellation non sono campi finanziari né controlli del draft: appartengono alla
policy versionata del servizio/worker, sono visibili nel catalogo e riepilogati
nell'output `limits`, senza coefficienti nascosti o override utente.

### 6.3 Fonti di liquidità

```text
FundingSource =
  NewExternalFunding       {source_kind="new_external", source_id, label, selected_money}
| ExistingAccountFunding  {source_kind="existing_account", source_id, broker_id?,
                           available_money, selected_money, provenance}
| ManualAccountFunding    {source_kind="manual_account", source_id, label,
                           declared_available_money, selected_money}
```

Invarianti:

- stessa valuta in saldo e importo selezionato;
- `0 <= selected <= available`;
- nuova liquidità non ha saldo preesistente;
- identità riusata se la fonte coincide con un Broker operativo;
- cash non selezionato non entra nel solver;
- nessuna fonte viene duplicata come contributo separato.

### 6.4 Broker operativi

```text
TradingBroker =
  ExistingTradingBroker {broker_kind="existing_broker", broker_id,
                         domain_snapshot, run_configuration}
| ManualTradingBroker   {broker_kind="manual_broker", scenario_broker_id,
                         label, run_configuration}

BrokerRunConfiguration
├── account_currencies[]
├── default_debit_currency
├── fx_mode
├── currency_capabilities[]
├── fee_buy[]
├── fee_sell[]
├── tax_regime
└── carried_losses
```

Enum:

- `fx_mode`: `native_currency_required | auto_convert_on_buy`;
- `tax_regime`: `administered | declarative_free`.

`carried_losses` conserva importo Decimal, valuta e `as_of`, con default zero.
È un fatto schematico mostrato nel review snapshot ma non riduce la tax reserve
e non entra in obiettivi fiscali v1: mancano ancora categoria, compensabilità e
scadenza.

Per valuta:

- `fractional_orders_allowed`: unico sì/no utente, valido per BUY e SELL;
- `order_amount_step` richiesto solo se `fractional_orders_allowed=true`;
- valuta di addebito/accredito;
- fee BUY/SELL.

Questi sono input di capacità. “Numero di titoli” e “Importo da investire” non
configurano il Broker: sono risultati. Il backend deriva:

```text
OrderInstruction =
  ShareQuantityInstruction {kind="share_quantity", quantity intera}
| CashAmountInstruction    {kind="cash_amount", amount quantizzato,
                            estimated_quantity informativa}
```

Se `fractional_orders_allowed=false`, il backend emette quantità intere
`0,1,2,…`. Se è `true`, emette l'importo cash allineato a
`order_amount_step`. Non esiste `quantity_step`. Inventario frazionario
pregresso resta Decimal esatto; nessun flag separato per SELL.

Separazione UI obbligatoria:

| L'utente configura | Il backend calcola e restituisce |
|---|---|
| valuta conto/addebito | quantità titoli oppure importo cash da inserire |
| FX nativo/auto-conversione | quantità stimata per ordini cash |
| ordini frazionati ammessi sì/no | BUY/SELL scelti |
| step importo se frazionato | notional investito/disinvestito |
| minimo e limiti | fee, FX, tax reserve, addebito/accredito |
| fee BUY/SELL | funding e trasferimenti |
| regime e minus pregresse | residui, deviazioni, proof/status |

### 6.5 Fee

```text
FeeProfile
├── currency
├── fixed_amount
├── rate
├── rate_minimum_amount?
└── rate_maximum_amount?
```

Per notional `N` e lato `h`:

```math
\operatorname{fee}_h(N)=
\begin{cases}
0, & N=0\\
f_h+\min(\max(r_hN,l_h),u_h), & N>0
\end{cases}
```

`u_h=+∞` quando assente; `0<=l_h<=u_h`. Min/max si applicano alla componente
percentuale; rate zero con minimo positivo applica il minimo. Fee per riga
ordine, mai capitale investito.

### 6.6 Asset, custodie e route

```text
PlanningAsset
├── asset_key
├── asset_id?
├── display_name
├── quote
├── classifications
├── capital_gains_tax_rate
├── holdings_by_broker[]
└── broker_routes[]
```

Ogni `HoldingSnapshot` contiene:

- Broker;
- quantità esatta;
- valore corrente e valuta;
- PMC unitario, valuta, as-of e provenance;
- nessun ulteriore campo fiscale alternativo.

`capital_gains_tax_rate` è un rapporto Decimal `[0,1]`, pre-popolato dalla UI
con `0.26`, sempre modificabile e accompagnato da provenance
`system_default | user_override`. Nella v1 vive nello snapshot; la futura
persistenza sull'Asset è tracciata in `TODO_FUTURI.md`.

Ogni `AssetBrokerRoute` contiene:

- Asset/Broker;
- eligibility BUY;
- eligibility SELL;
- priorità;
- lato/valuta;
- `buy_constraints` e `sell_constraints`;
- nessuna capacità inferita da nome o Broker non selezionato.

```text
SideOrderConstraints
├── minimum_order_notional       # condizionale: vale solo se la riga esiste
├── required_min_notional?       # hard: se presente, la riga è obbligatoria
└── maximum =
      NoOrderCap {cap_kind="none"}
    | QuantityOrderCap {cap_kind="quantity", quantity}
    | NotionalOrderCap {cap_kind="notional", money}
```

Ogni lato ha unità e limiti propri. `required_min_notional` nullo non obbliga
un ordine; se positivo può provare infeasibility. Un massimo quantità viene
confrontato con quantità esatta/stimata; un massimo notional con il notional
operativo nella valuta dichiarata.
Required BUY e required SELL sullo stesso Asset canonico sono input
contraddittori e producono `needs_input`, non un problema solver artificiale.

Prezzo:

- originale e valuta di quotazione;
- `quote_base_quantity`;
- fonte, timestamp, staleness;
- prezzo `mid`, prezzo BUY charge e prezzo SELL credit derivati dagli FX fact.

### 6.7 FX

```text
FxFact
├── broker_id
├── from_currency
├── to_currency
├── mid_rate
├── source
├── observed_at
├── spread_rate
├── fx_buffer_rate
└── fixed_fee?
```

Il rate indica unità `to_currency` ricevute per una unità `from_currency`.
Nome wire input: `fx_buffer_rate`; nome output monetario:
`fx_buffer_amount`; label UI: **Margine di sicurezza FX**.
Conversioni:

- solo coppie dichiarate;
- un solo hop;
- niente cicli attivi;
- debit/credit leg accoppiati;
- spot age mostrata;
- spread costo;
- buffer FX cash riservato, default zero;
- fee FX separata.

### 6.8 Input pubblici

```text
PacPlanInput
├── operation = "plan"
├── scenario
└── pac_policy = "proportional" | "min_fragmentation"

RebalancePlanInput
├── operation = "plan"
├── scenario
└── trade_mode = "invest_only" | "invest_and_sell"
```

Nessun campo `report_currency`, `analyze`, `buy_grid`, `quantity_step`,
`monetary_step`, `preview_target` o `optimize_residual`.

### 6.9 Output pubblico

```text
PlanOutput
├── availability
├── outcome
├── proof
├── stop_reason
├── limits
├── objective_values
├── target_deviation
├── cash_deficit
├── base_solution?
├── residual_optimized_solution?
├── issues[]
└── normalized_snapshot_digest
```

Dimensioni ortogonali:

- `availability`: `ready | needs_input | unsupported`;
- `outcome`: `no_op | infeasible_proven | incumbent_found | no_incumbent`;
- `proof`: `optimal_proven | gap_bounded | not_proven`;
- `stop_reason`: `completed | time_limit | node_limit | memory_limit | cancelled`.

Regole:

- `optimal_proven` solo con prova;
- timeout con incumbent =
  `incumbent_found/not_proven/time_limit`;
- timeout senza incumbent =
  `no_incumbent/not_proven/time_limit`;
- input/fatto mancante non diventa `infeasible_proven`;
- `no_op` quando il piano vuoto è fattibile e nessuna operazione ammessa
  migliora l'obiettivo;
- `infeasible_proven` soltanto quando vincoli hard espliciti rendono vuoto
  l'intero dominio;
- cash sotto il minimo condizionale o nessuna route utile produce `no_op`
  con issue, non `infeasible_proven`;
- crash, invalid output, timeout piattaforma e cleanup failure restano errori Tool;
- `target_deviation`, `cash_deficit` e gap sono numeri, non status.

`base_solution` e `residual_optimized_solution` sono entrambe richieste per
`no_op` e `incumbent_found`; senza delta utile la seconda coincide con la prima
e dichiara delta zero. Sono assenti per `needs_input`, `unsupported`,
`infeasible_proven` e `no_incumbent`.

Ogni soluzione contiene:

- `funding_actions`;
- `transfer_actions`;
- `fx_actions`;
- `broker_plans.orders`;
- `cash_ledgers`;
- `residuals`;
- `current_target_planned_exposure`;
- `fees`, `tax_reserve`, `fx_cost`, `fx_buffer_amount`;
- motivazioni e vincoli attivi.

Ogni `cash_ledger` espone saldo iniziale selezionato, trasferimenti, FX,
proventi lordi SELL, BUY, fee, tax reserve, buffer, saldo spendibile finale e
saldo fisico finale.

Ogni `BrokerOrder` contiene almeno:

- Asset, Broker, lato e currency;
- `OrderInstruction` output-only;
- prezzo originale, mid, charge/sell e provenance;
- `asset_target_notional` come riferimento aggregato non sommabile;
- notional mid e notional operativo;
- quantità esatta o stimata;
- fee lato, costo FX, tax reserve SELL e `withholding_kind`;
- `order_cash_amount` rounded;
- `total_cash_debit` BUY oppure `gross_cash_credit` e `net_cash_credit` SELL;
- issue e vincoli attivi.

`AssetPlanSummary` contiene `target_notional`, notional aggregato su tutti i
Broker, residual e residual ratio. Il target/residuo non viene inventato per
una singola route; la UI può combinare summary Asset e child order, ma non
somma più volte un target Asset splittato. Se `target_notional=0`,
`residual_ratio` è `null` con semantica tipizzata; non si emette un rapporto
infinito/non finito.

## 7. Modello matematico e invarianti

### 7.1 Ledger nativo

Per ogni Broker `b` e valuta `c`:

```math
\begin{aligned}
\operatorname{cashDisponibileFinale}_{b,c}
=\;&u_{b,c}
+\sum_{s\ne b}t_{s,b,c}
-\sum_{b'\ne b}t_{b,b',c}\\
&+\sum_{j:\,\cdot\to c}\operatorname{credito}^{(c)}_j
-\sum_{j:\,c\to\cdot}f_j\\
&+\sum_a\operatorname{proventoSell}^{(c)}_{a,b}
-\sum_a\operatorname{addebitoBuy}^{(c)}_{a,b}\\
&-\sum_a\operatorname{feeBuy}^{(c)}_{a,b}
-\sum_a\operatorname{feeSell}^{(c)}_{a,b}\\
&-\sum_a\operatorname{taxReserve}^{(c)}_{a,b}
-\operatorname{feeFX}^{(c)}_b
-\operatorname{fxBuffer}^{(c)}_b
\ge 0
\end{aligned}
```

Ogni termine mantiene valuta nativa. La valuta di riferimento scelta serve solo a confrontare
valori, target e grafici.

Il ledger contabilizza provento SELL lordo, fee SELL e tax reserve come termini
separati. `cashNetSell` è solo un totale derivato e non viene accreditato una
seconda volta.

Il buffer non è spesa:

```math
\operatorname{cashFisicoFinale}_{b,c}
=
\operatorname{cashDisponibileFinale}_{b,c}
+\operatorname{fxBuffer}^{(c)}_b
+\operatorname{selfReservedTax}^{(c)}_b
```

Il primo saldo è ancora spendibile dal piano; il secondo è il saldo fisico
atteso nel conto. `selfReservedTax` include solo SELL
`withholding_kind="self_reserved"`; una ritenuta `broker_withheld` è già uscita
dal conto.

### 7.2 FX accoppiato

Per conversione `j=(b,c→d)`:

```math
\operatorname{credito}^{(d)}_j=f_jR^{eff}_{c\to d}
```

```math
R^{eff}_{c\to d}=R_{c\to d}(1-s)
```

```math
\operatorname{fxBuffer}_c=mD_c
```

Nessun credito senza debito. `0<=s<1`; `m>=0`. `fx_buffer_rate=m`; il relativo
output monetario è `fx_buffer_amount`. Il buffer resta nel ledger
sorgente, non viene convertito.

### 7.3 Prezzi distinti

Per Asset quotato in `q`, con prezzo sorgente `P_source` riferito a
`quote_base_quantity=Q_a`, il prezzo unitario è:

```math
p_a^{(q)}=\frac{P_{source,a}^{(q)}}{Q_a}
```

`Q_a` resta nello snapshot/output; la divisione avviene una sola volta.
Se il Broker addebita/accredita in `c`:

```math
P_{a,b}^{(mid,c)}=\frac{p_a^{(q)}}{R_{c\to q}}
```

```math
P_{a,b}^{(chg,c)}=\frac{p_a^{(q)}}{R^{eff}_{c\to q}}
```

```math
P_{a,b}^{(sell,c)}=p_a^{(q)}R^{eff}_{q\to c}
```

Grafici/investimento usano mid; cash BUY usa charge; cash SELL usa sell.

#### 7.3.1 Semantica delle istruzioni ordine

Broker senza frazioni:

```math
q_{a,b}\in\mathbb{Z}_{\ge0}
```

```math
\operatorname{orderDebit}_{a,b}^{(c)}
=
\operatorname{round}_{\mu_c}
\left(q_{a,b}P_{a,b}^{(chg,c)}\right)
```

`cashDebit=orderDebit+feeBuy`; il ledger sottrae i due termini una volta.

Broker con frazioni, BUY:

- `M_buy[a,b]` è l'importo cash fee-escluse da inserire nel Broker;
- `M_buy` è multiplo di `order_amount_step[b,c]`;
- `estimated_quantity=M_buy/P^(chg,c)`;
- `orderDebit=round_mu(M_buy)` e
  `cashDebit=orderDebit+feeBuy(M_buy)`;
- valore investimento mid =
  `estimated_quantity * P^(mid,c)`, quindi con spread positivo è minore di
  `M_buy`.

Broker con frazioni, SELL:

- `M_sell[a,b]` è il provento lordo richiesto, multiplo dello stesso step;
- `estimated_quantity=M_sell/P^(sell,c) <= holding_quantity`;
- `grossSell=round_mu(M_sell)`;
- la v1 può lasciare un residuo di posizione se il valore totale non è
  allineato allo step; nessuna eccezione “sell all” nascosta.

La fee percentuale usa il notional operativo della riga. Spread è differenza
fra notional operativo e valore mid, non un secondo addebito.

Witness obbligatorio: prezzo `99 USD`, mid `1 USD/EUR`, spread `1%`, fee zero
→ prezzo charge `100 EUR`; `M_buy=100 EUR` produce quantità `1`,
investimento mid `99 EUR`, costo spread `1 EUR` e addebito `100 EUR`.

### 7.4 PAC base

Pesi `w_a>=0`, somma esatta `1`. `K_reachable` è il budget lordo che può
raggiungere almeno un BUY eleggibile, entro route/cap dichiarati e valorizzato
al mid; esclude cash intrappolato. Fee fisse/min/max, righe ordine e FX
dipendono invece dal candidato. Il solver opera direttamente sui ledger e
l'evaluator può derivare, solo ex post:

```math
B_{ref}(x)
=
K_{reachable}^{(v)}
-C_{buy}^{(v)}(x)
-C_{FX}^{(v)}(x)
-H_{FX}^{(v)}(x)
```

Cash selezionato ma non instradabile resta residuo con issue. `B_ref(x)` è
diagnostico candidato-dipendente, non bound usato per costruire `x`.

Per `A_a(x)` valore mid acquistato e
`B_actual(x)=sum_a A_a(x)`, quando `K_reachable>0`:

```math
T_a=w_aK_{reachable}^{(v)}
```

```math
d_a(x)=
\left|
\frac{A_a(x)-T_a}{K_{reachable}^{(v)}}
\right|
```

Il PAC base non ottimizza `d_a`. Calcola `T_a=w_aK_reachable`, assegna a ogni
Asset il relativo envelope lordo, visita le route per priorità e sceglie per
difetto la massima quantità intera o il massimo step monetario compatibile con
envelope, cash nativo, fee, FX, buffer, minimi e cap. Target non disponibile
resta residuo esplicito; D∞/D1 sono diagnostici.

Se `K_reachable=0`, l'outcome è `no_op` e le deviazioni PAC restano `null`.
Se `K_reachable>0` ma `B_actual=0`, per esempio sotto minimo condizionale,
`d_a=|w_a|` e l'outcome resta `no_op`. Fee, tax, spread e buffer non sono
investimento né denominatore.

`proportional` e `min_fragmentation` non cambiano la base. Governano soltanto il
post-step. Entrambe massimizzano prima l’investimento aggiuntivo; `proportional`
ordina quindi D∞/D1 prima di priorità/costi/righe, mentre
`min_fragmentation` ordina Asset splittati/righe prima di D∞/D1 e
priorità/costi. Il piano nullo non può vincere contro un incremento con
investimento mid maggiore.

### 7.5 Residual optimization

Parte dalla soluzione base immutabile:

```math
z_{a,b}=z^0_{a,b}+\Delta z_{a,b},\qquad \Delta z_{a,b}\ge0
```

Può solo aggiungere BUY ammessi. Non può:

- diminuire/spostare azioni base;
- introdurre SELL;
- superare cash/FX/fee/buffer;
- conteggiare fee o buffer come investimento.

Fra i candidati ammessi massimizza prima l'investimento mid aggiuntivo, poi
applica l’ordine `proportional` o `min_fragmentation` congelato nel design
normativo.
Può peggiorare lo score base per ridurre cash inattivo; output separa investimento,
fee, residuo e delta score. Può coincidere con la base.

### 7.6 Rebalancer invest-only

Con valori correnti `V_a`, target `w_a`, totale investito `V_0`:

```math
F^*=\max_{a:w_a>0}\frac{V_a}{w_a}
```

```math
K^*=F^*-V_0
```

```math
B_a^*=w_aF^*-V_a
```

`K*` è solo lower bound continuo, gratuito e senza vincoli. Non è sufficienza
operativa. Fee, FX, minimi, routing e quantum possono richiedere più cash o
rendere irraggiungibile il target esatto.

Per ogni candidato discreto Rebalancer, `AssetPlanSummary.target_notional` è
`w_a * sum_a V_a_final`; la deviazione confronta valore finale e questo target.
Non usa il budget PAC `K_reachable`.

### 7.7 Rebalancer invest-and-sell

Sequenza lessicografica:

1. calcola/congela miglior `invest_only`;
2. usa SELL solo se riduce gap residuo;
3. vende solo overweight;
4. minimizza turnover;
5. minimizza costi;
6. minimizza righe;
7. applica tie-break stabile.

Questa è una semantica sequenziale deliberata: `invest_and_sell` non cerca un
ottimo BUY/SELL globale che possa scartare la migliore soluzione invest-only.
L'oracle esaustivo implementa la stessa sequenza e confronta ogni fase, non un
obiettivo congiunto diverso.

Hard constraints:

- SELL `<=` inventario Asset×Broker;
- nessun short;
- nessun BUY+SELL dello stesso Asset globale;
- proventi SELL nel ledger prima dei BUY;
- fee SELL e riserva fiscale sottratte;
- nessuna vendita implicita.

Per quantità venduta `n[a,b]`, PMC unitario `k[a,b]`, provento lordo
`grossSell[a,b]`, fee `feeSell[a,b]` e aliquota Asset `rho[a]`:

```math
\operatorname{costBasisSold}_{a,b}=n_{a,b}k_{a,b}
```

```math
\operatorname{taxableGain}_{a,b}
=
\max\left(
\operatorname{grossSell}_{a,b}
-\operatorname{feeSell}_{a,b}
-\operatorname{costBasisSold}_{a,b},
0
\right)
```

```math
\operatorname{taxReserve}_{a,b}
=
\operatorname{round}_{\mu_c,\mathrm{HALF\_UP}}
\left(
\rho_a\operatorname{taxableGain}_{a,b}
\right)
```

```math
\operatorname{cashNetSell}_{a,b}
=
\operatorname{grossSell}_{a,b}
-\operatorname{feeSell}_{a,b}
-\operatorname{taxReserve}_{a,b}
```

Solo l'equivalente netto può finanziare BUY. Nel ledger si accredita
`grossSell` e si sottraggono `feeSell` e `taxReserve` separatamente; l'evaluator
verifica che il saldo spendibile coincida con `cashNetSell` e vieta il double
posting. `withholding_kind` determina soltanto se la riserva è uscita dal conto
o resta nel saldo fisico non spendibile.
Minus pregresse non riducono la riserva in v1: servono policy fiscali e regole
di compensabilità future.

### 7.8 Classificazioni

Tipo, Settore e Geografia usano esposizioni `alpha[a,k]`. Quota mancante va in
`Unknown`; non si rinormalizza il solo sottoinsieme noto. `Ora`, `Target` e
`Dopo` usano stessa valuta/data/FX e lo stesso denominatore: valore investito
negli Asset, cash escluso. Cash selezionato, trasferito, convertito, investito,
riservato e residuo usa un grafico/KPI funding separato; non si aggiunge una
slice Cash a una sola serie di confronto.

```math
E_k^{target}=\sum_a w_a\alpha_{a,k}
```

### 7.9 Risultato e riserva fiscale

```math
G_{a,b}=n_{a,b}(p_{a,b}-k_{a,b})
```

`G` resta indicazione lorda, non una policy fiscale. La v1 usa la formula
conservativa sopra soltanto per riservare cash; non ottimizza plus/minus.

### 7.10 Bound finiti del solver

Ogni upper bound è derivato dai dati normalizzati:

- BUY integero: cash nativo raggiungibile diviso per prezzo charge più minimo
  costo lato, arrotondato verso il basso;
- BUY frazionario: cash nativo raggiungibile diviso per `order_amount_step`;
- SELL integero: quantità intera effettivamente posseduta;
- SELL frazionario: minimo fra step monetari rappresentabili e quantità
  ricavabile dall'inventario al prezzo SELL;
- indicatori Asset/ordine: somma o OR dei soli bound route derivati.

Nessun `U_a`, `Qmax_ab` o Big-M arbitrario. Un bound non derivabile rende lo
snapshot `needs_input`/`unsupported`; non viene sostituito con una costante
silenziosa.

## 8. Persistenza e API dominio

### 8.1 Decisione DB

La v1 **non modifica il DB** per parametri operativi Broker o aliquota Asset.

- Un Broker esistente fornisce identità, accesso, conti/cash e altri fatti già
  presenti nel dominio.
- L'utente completa nello scenario i parametri mancanti: FX mode, valuta di
  addebito, frazionamento per valuta, step monetario, min/max, fee, regime e
  minus pregresse.
- Il valore `capital_gains_tax_rate` è pre-popolato a `0.26` nello scenario e
  resta modificabile.
- Broker e fonti manuali restano scenario-only.
- Nessun endpoint GET/PUT planner profile, nuova tabella o migration v1.

Persistenza futura:

- profilo operativo personale user×Broker;
- aliquota plusvalenze configurabile sull'Asset.

Entrambe sono registrate in `TODO_FUTURI.md`; non vanno anticipate come codice
legacy o schema parziale.

### 8.2 Domain-copy API

Riutilizzare/estendere:

- `backend/app/schemas/portfolio.py`:
  `PortfolioAllocationSourceRequest`, `PortfolioAllocationSource` e nested;
- `backend/app/services/portfolio_service.py` +
  `build_portfolio_allocation_source`;
- Broker API/service per identità, accesso, conti e cash già disponibili;
- Asset API per identità, prezzo originale, `quote_base_quantity`,
  classificazioni e provenance;
- FX API/service per spot read-only, fonte e timestamp.

Se manca un fatto read-only riusabile, estendere il DTO/endpoint del relativo
dominio. Non aggiungere endpoint dedicati a un profilo planner persistito.

Lo snapshot Portfolio deve restituire:

- custodia intera OWNER, anche OWNER 0%;
- quota economica personale separata e solo informativa;
- cash per Broker/valuta contato una volta;
- holding per Asset×Broker;
- quantità, valore, PMC, valuta e provenance;
- asset senza prezzo/FX espliciti come missing, mai omessi;
- nessuna restrizione silenziosa dello scope richiesto.

Non usare `/assets/prices/current` come innocuo prefill: può scrivere OHLC.
Se manca una lettura prezzo read-only, aggiungerla nel dominio Asset.

### 8.3 Async boundary

- API/domain assembly async può interrogare DB.
- Ogni libreria sync con I/O dentro `async def` usa
  `await asyncio.to_thread(...)`.
- Plugin/core/solver sono sync e puri nel worker.
- `compute()` riceve solo snapshot + `context.checkpoint`.
- Nessun principal, sessione DB, request, provider o service globale nel core.

## 9. Tool, schema export e renderer

Il plugin esistente resta multi-servizio:

| `tool_code` | Input | Output | Component key |
|---|---|---|---|
| `pac_allocator` | `PacPlanInput` | `PacPlanOutput` | `pac-allocator` |
| `portfolio_rebalancer` | `RebalancePlanInput` | `RebalancePlanOutput` | `portfolio-rebalancer` |

Entrambi dichiarano soltanto `operation="plan"`. Non introdurre una modalità
interna che nasconda due servizi pubblici.

Acceptance:

- conservare il catalogo Tool v2 esistente; nessun endpoint/versione parallela;
- schema catalogo derivato da TypeAdapter;
- root reali esportate nella pipeline API sync;
- schema fingerprint cambia rispetto a P1 e coincide fra backend/client;
- client generato conserva literal, union discriminator, required/nullable ed
  `extra=forbid`;
- compatibilità esatta su tool code, contract `1.0.0`, fingerprint,
  component key e UI SemVer `1.0.0`;
- implementation version live pin valida;
- renderer sconosciuto/incompatibile = unavailable, nessun fallback generico;
- catalogo, diagnostics, worker e compute vedono gli stessi due servizi;
- batch con più item uguali/differenti mantiene correlazione, ordine e
  cardinalità; nessuna deduplica fisica.

Un solo writer gestisce:

- export roots;
- API sync;
- mapping codec version→schema;
- `frontend/src/lib/features/tools/registry.ts`;
- eventuali registrazioni catalogo condivise.

## 10. Frontend Svelte 5

### 10.1 Componenti

Wrapper distinti:

- `PacAllocatorTool.svelte`;
- `PortfolioRebalancerTool.svelte`.

Shared planner proposto sotto
`frontend/src/lib/features/tools/pac-allocator/planner/`:

- `OperationalPlannerShell.svelte`;
- `FundingSourcesStep.svelte`;
- `TradingBrokersStep.svelte`;
- `PlanningAssetsStep.svelte`;
- `AssetBrokerRoutesStep.svelte`;
- `PlanningTargetsStep.svelte`;
- `PlanningFxStep.svelte`;
- `PlanningStrategyStep.svelte`;
- `PlanningReviewStep.svelte`;
- `PlanningResultShell.svelte`;
- `PlanningAllocationChart.svelte`;
- `PlanningExposureCards.svelte`;
- `PlanningAssetAllocationTable.svelte`;
- `PlanningFundingTable.svelte`;
- `PlanningBrokerOrdersTable.svelte`;
- `planningDraft.svelte.ts`;
- `planningSourceCopies.ts`;
- `planningResultSelectors.ts`;
- `planningContracts.ts`.

Ownership:

- shell: account generation, request sequence, draft revision, busy/error,
  result stale, abort;
- source-copy layer: fetch, provenance, preview diff, apply atomico;
- step editors: solo draft locale;
- result components: read-only;
- wrapper PAC/Rebalancer: copy/strategy specifiche;
- nessun componente calcola allocazioni, fee, FX o quantità.

Usare rune Svelte 5. Non modificare i boundary legacy del layout/onboarding per
comodità del planner.

### 10.2 Copy e stale safety

Pulsanti indipendenti:

- copia situazione iniziale;
- copia prezzi;
- copia distribuzione corrente come base target;
- copia identità/casse Broker disponibili;
- copia FX.

Ogni fetch:

1. cattura account generation, component identity, request sequence e draft
   revision;
2. mostra provenance/data/staleness;
3. produce preview dei campi sostituiti;
4. richiede apply esplicito;
5. viene ignorato se una guardia cambia;
6. non mantiene binding live;
7. non sovrascrive input successivi.

### 10.3 Grafici e tabelle

- ECharts riceve solo coordinate/formattazione derivate da output backend.
- `DataTable` per ordini, funding e FX.
- `ExactDecimalInput` preserva stringhe; nessun `Number` per economia.
- `CurrencySearchSelect`, icone Asset/Broker e `DocsLink` riusati.
- Desktop e mobile mostrano gli stessi fatti; mobile usa card/stack senza
  eliminare colonne core.
- `data-testid`, tastiera, label, focus, `aria-busy`, `role=status/alert`.
- Privacy copre importi, quantità, PMC, funding e ordini; prezzi pubblici e
  percentuali restano secondo policy globale.

Tabella allocazione Asset core:

| Colonna | Semantica |
|---|---|
| Asset | identità/display |
| Target Asset | notional della policy sull'Asset, aggregato su tutti i Broker |
| Investimento/disinvestimento | valore mid aggregato |
| Residuo target | target meno valore aggregato, non fee |
| Residuo % | rapporto sul target Asset |
| Stato | eseguibile/issue |

Tabelle operative per Broker:

| Colonna | Semantica |
|---|---|
| Asset | identità/display |
| Lato | BUY/SELL |
| Prezzo corrente | originale + fonte/data |
| Input Broker | numero titoli oppure cash amount |
| Quantità stimata | esatta per integer, informativa per cash |
| Investimento/disinvestimento | valore mid |
| Fee | BUY o SELL |
| Costo FX | separato |
| Ritenuta/riserva | importo + `withholding_kind` |
| Addebito/accredito Broker | cash operativo rounded |
| Stato | eseguibile/issue |

Con un solo Broker la UI può presentare le due viste nello stesso gruppo
visivo, ma target/residuo resta semanticamente Asset-level e viene totalizzato
una sola volta.

### 10.4 Onboarding

Conservare:

- anchor `tools.hub`;
- route/card stabili;
- replay e focus;
- ownership settlement di `frontend/src/routes/(app)/+layout.svelte`.

Nuovi anchor interni possono essere aggiunti solo con owner J/coordinatore,
test-author e prova che non riaprono la race bootstrap/route. Nessun cambio
onboarding è necessario per il primo checkpoint backend.

## 11. Storyboard prima del codice UI

Questi storyboard sono baseline di review, non UI implementata. Ogni modifica
sostanziale richiede nuova approvazione developer prima del codice viste.

### 11.1 Desktop — manuale/copie/vincoli

```text
+----------------------------------------------------------------------------+
| Tool > PAC allocator                                  Draft r12 · non inviato |
| [1 Scope] [2 Liquidità] [3 Broker] [4 Asset/route] [5 Target] [6 FX] [7 Policy] |
|----------------------------------------------------------------------------|
| LIQUIDITÀ                                                                  |
| [ + Nuova ] [ Copia da conto/Broker ] [ + Fonte manuale ]                 |
| Banca X · EUR · disponibile 8.400 · usa [2.500] · copiato 2h fa [Aggiorna] |
| Directa · EUR · disponibile 1.159 · usa [  800] · override utente          |
|----------------------------------------------------------------------------|
| BROKER OPERATIVI                                                           |
| [ Scegli esistente ] [ + Broker manuale ]                                  |
| Directa · Frazioni: no · fee BUY 0 · fee SELL 5+0,19% · amministrato      |
| Demo USD · Frazioni: sì · step 1 USD · auto-FX · scenario-only             |
|----------------------------------------------------------------------------|
| ASSET × BROKER                                                             |
| XMAW: [x] Directa priorità 1  [x] Demo priorità 2  [ ] Banca funding-only |
| XDWF: [x] Directa priorità 1                                            |
|----------------------------------------------------------------------------|
| [Continua]  Dati mancanti: FX EUR→USD                                    |
+----------------------------------------------------------------------------+
```

### 11.2 Desktop — target/strategy/review

```text
+----------------------------------------------------------------------------+
| TARGET                                                                     |
| Asset               Target        Totale 100%                              |
| XMAW World          [70,00] %                                               |
| XDWF Financials     [30,00] %                                               |
| Nessuna anteprima teorica: il risultato dipende da fee, FX e quantum.       |
|----------------------------------------------------------------------------|
| FX POTENZIALI                                                              |
| EUR→USD · 1,1732 · ECB · 2 giorni fa · spread [0,50]%                    |
| Margine di sicurezza FX [1,00]%                                          |
|----------------------------------------------------------------------------|
| STRATEGIA                                                                  |
| (●) Residuo proporzionale   ( ) Residuo minima frammentazione              |
|----------------------------------------------------------------------------|
| REVIEW SNAPSHOT                                                            |
| 3 fonti · 2 Broker · 2 Asset · 1 FX · 2 override · facts stale: 1         |
| [Apri dettaglio JSON tipizzato] [Conferma e calcola]                       |
+----------------------------------------------------------------------------+
```

### 11.3 Desktop — risultati

```text
+----------------------------------------------------------------------------+
| RISULTATO · incumbent · ottimo provato · completed                         |
| [Base policy] [Base + residuo]  Valori in EUR · snapshot 2026-09-15       |
|----------------------------------------------------------------------------|
| [EChart: acquisti/vendite]       [Ora | Target | Dopo]                     |
| [Tipo: before/after] [Settore: before/after] [Geografia: before/after]     |
| Unknown esplicito · [KPI cash: selezionato/usato/riservato/residuo]        |
|----------------------------------------------------------------------------|
| FUNDING / FX                                                               |
| Bonifico Banca X → Directa · 2.500 EUR                                    |
| Auto-FX Directa EUR→USD · debito 358,12 EUR · credito 418,00 USD          |
|----------------------------------------------------------------------------|
| ALLOCAZIONE ASSET                                                          |
| ETF | target Asset | valore aggregato | residuo | residuo %               |
| XMAW| 2.563        | 2.561,730        | 1,270   | 0,050%                  |
|----------------------------------------------------------------------------|
| ORDINI DIRECTA                                                             |
| ETF | lato | prezzo | input Broker | quantità | valore mid | fee | cash   |
| XMAW| BUY  | 50,230 | 51 titoli    | 51       | 2.561,730 | 0   | 2.561,73 |
| Totale Broker: addebito 2.561,73 · residuo cassa 1,27 EUR                 |
|----------------------------------------------------------------------------|
| Vincoli attivi · deviazione · proof · limiti · issues [Dettagli]           |
+----------------------------------------------------------------------------+
```

### 11.4 Invalid / infeasible / busy / stale

```text
INVALID / NEEDS INPUT               NO-OP
+-------------------------------+   +--------------------------------+
| Aliquota Asset non valida     |   | Nessuna route finanzia USD    |
| Correggere 26% / 0,26         |   | Oracle/evaluator confermano   |
| Draft e valori preservati     |   | Nessun ordine inventato       |
+-------------------------------+   +--------------------------------+

BUSY / LIMIT                        STALE RESULT
+-------------------------------+   +--------------------------------+
| Calcolo r12 in corso          |   | Risultato r12 non applicato   |
| [Annulla attesa]              |   | Draft attuale r13             |
| Nessun risultato precedente  |   | [Ricalcola]                    |
| mostrato come nuovo           |   | Nessuna sovrascrittura        |
+-------------------------------+   +--------------------------------+

NO INCUMBENT / TIME LIMIT            INCUMBENT / TIME LIMIT
+-------------------------------+   +--------------------------------+
| Nessun piano trovato entro    |   | Piano fattibile, non ottimo   |
| limite; non “infeasible”      |   | Gap e limite mostrati         |
+-------------------------------+   +--------------------------------+
```

### 11.5 Mobile

```text
+----------------------------------+
| PAC · Step 4/8                   |
| Draft r12 · stale FX             |
|----------------------------------|
| XMAW World                       |
| Broker: Directa · priorità 1     |
| Broker: Demo USD · priorità 2    |
| [Modifica route]                 |
|----------------------------------|
| Target 70,00%                    |
| Prezzo 50,230 EUR · 2h fa        |
|----------------------------------|
| [Indietro] [Continua]            |
+----------------------------------+

+----------------------------------+
| RISULTATO · BASE                 |
| Incumbent · optimal proven       |
| [Grafico acquisti]               |
| [Ora/Target/Dopo]                |
|----------------------------------|
| Directa                          |
| BUY XMAW · 51 titoli             |
| Investimento 2.561,730 EUR       |
| Fee 0 · addebito 2.561,73        |
| Margine 1,270 EUR                |
|----------------------------------|
| [Funding/FX] [Vincoli/Proof]     |
+----------------------------------+
```

## 12. Workstream futuri e ownership

Nessuna Fleet parte con questo piano. Dopo autorizzazione:

| WS | Scope esclusivo | Dipendenze | Modello/agente |
|---|---|---|---|
| W0 | contratto/schema finale corretto | nessuna | Astra/high-reasoning |
| W1 | normalizer/evaluator/ledger Decimal | W0 | Astra; review matematica indipendente |
| W2 | solver/oracle/benchmark/limits | W0, W1 contract | Astra; `test-author` per test |
| W3 | Portfolio/Broker/Asset/FX copies, senza DB migration | W0 | backend specialist; `test-author` |
| W4 | shell/editor PAC | W0 fixtures; W3 per integrazione | frontend agent delimitato |
| W5 | shell/editor Rebalancer + result views | W0 fixtures; W2/W3 per integrazione | frontend agent delimitato |
| W6 | Tool plugin/catalog/codec/client integration | W0–W5 | un solo integratore shared |
| W7 | test matrix E2E/runner registrations | W1–W6 | `test-author`, un writer runner |
| W8 | EN docs + changelog | contratto/UI stabili | `docs-writer`; changelog integratore |
| W9 | review auth/privacy/invarianti/math | combined revision | Astra/rubber-duck/read-only |

Agenti più piccoli ammessi solo su file esclusivi e task delimitati. Astra/high
reasoning obbligatoria per:

- matematica;
- oracle;
- autorizzazioni;
- invarianti;
- review finale.

Lock condivisi:

- `backend/app/db/models.py` + Alembic;
- API router;
- Portfolio service/schema;
- Tool registry/schema export;
- client generato;
- `frontend/src/lib/features/tools/registry.ts`;
- quattro cataloghi i18n;
- runner catalog;
- MkDocs nav;
- `CHANGELOG.md`;
- onboarding/layout.

## 13. Sequenza dettagliata di implementazione

Ogni step usa il template di avanzamento della sezione 14 immediatamente dopo
la sua chiusura.

### Step 0 — Congelare il contratto corretto e rifare il math review

**Owned surfaces**

- questo piano;
- nuovo ADR/appendice nello stesso folder, se richiesto;
- nessun production file.

**Dipendenza:** nessuna decisione prodotto aperta; applicare le correzioni
developer del 2026-09-15.

**Azioni**

1. Congelare input Broker per-run e output order instruction separati.
2. Congelare valuta di riferimento visibile/prefilled.
3. Congelare aliquota Asset e formula fee→gain→tax reserve→cash netto.
4. Congelare BUY/SELL cash instruction, gross/net posting e nomi FX buffer.
5. Congelare denominatori, budget raggiungibile e no-op/infeasible.
6. Preparare esempi numerici minimi per zero, plus, minus, spread e rounding.
7. Rilanciare review matematica del contratto.

**Specialista:** Astra/high-reasoning; rubber-duck read-only.

**Validazione pianificata:** review documentale; nessun comando runtime.

**Artifact:** contratto firmato, schema pseudocodice e audit aggiornato.

**DoD:** nessun `order_entry_mode` input; aliquota e tax reserve senza
ambiguità; valuta di riferimento esplicita; nessun epsilon/Big-M arbitrario;
review senza blocker.

**Nota piano:** compilare subito il template §14 per Step 0.

**Stop:** qualunque cambio successivo a input, fee, FX, fiscalità od obiettivi
riapre questo gate.

### Step 1 — Sostituire schema P1 e definire modelli interni

**Owned surfaces**

- `backend/app/schemas/pac_allocator.py`;
- `backend/app/services/pac_allocator/models.py`;
- nuovi moduli schema interni sotto `backend/app/services/pac_allocator/`;
- test schema esclusivi assegnati a `test-author`.

**Dipendenza:** Step 0.

**Azioni**

1. Implementare union/discriminanti sezioni 6.3–6.8.
2. Imporre `extra="forbid"`, limiti cardinalità/stringa e Decimal finite.
3. Separare PAC/Rebalancer input/output mantenendo root bundled reali.
4. Eliminare operation `analyze`, `report_currency`, `buy_grid`,
   `quantity_step`, `monetary_step` e output P1.
5. Definire output status/proof/stop ortogonali.
6. Definire `BrokerOrder` e `AssetPlanSummary` completi, senza target
   route-level inventati.
7. Far scrivere a `test-author` witness valid/invalid, discriminanti,
   required/nullable, nonfinite, Unicode e round-trip.

**Specialista:** backend schema owner; `test-author`.

**Validazione futura**

```text
PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py test \
  --test-port 6153 --data-dir /tmp/librefolio-r2-d \
  schemas pac-planner
```

Registrare `schemas pac-planner` una volta sola se assente.

**Artifact:** schema export diff + tabella unità.

**DoD:** nessun modello P1 importabile; tutti i nuovi root validano; fingerprint
deterministico; nessun compatibility union.

**Nota piano:** compilare subito il template §14 per Step 1.

### Step 2 — Copie dominio senza nuova persistenza planner

**Owned surfaces**

- schema/service/API Broker;
- `backend/app/schemas/portfolio.py`;
- builder `build_portfolio_allocation_source`;
- route dominio necessarie;
- test API/service tramite `test-author`.

**Dipendenza:** Step 1.

**Azioni**

1. Estendere snapshot Portfolio con holding/cash/PMC/provenance completi.
2. Esporre Asset/FX read-only mancanti nel dominio corretto.
3. Copiare dal Broker soltanto fatti già persistiti nel dominio.
4. Lasciare capability/fee/regime/minus/aliquota come input scenario.
5. Rifiutare scope Broker parzialmente non autorizzato; nessuna intersezione
   silenziosa.
6. Non persistere parametri planner, manual account o manual Broker.
7. Provare che `/assets/prices/current` non viene usato dal copy automatico.

**Specialista:** backend; `test-author`; API/domain writer unico.

**Validazione futura**

```text
PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py test \
  --test-port 6153 --data-dir /tmp/librefolio-r2-d \
  services portfolio-allocation-source
```

**Artifact:** API examples sanitizzati + prova assenza migration/schema DB.

**DoD:** OWNER-only; OWNER 0% custodial facts complete; no leaks; no silent
omission; existing Broker prefilla solo fatti noti; tutti i parametri
operativi sono editabili per-run; manual scenario funziona senza DB.

**Nota piano:** compilare subito il template §14 per Step 2.

### Step 3 — Normalizer e evaluator Decimal indipendenti

**Owned surfaces**

- `backend/app/services/pac_allocator/normalize.py`;
- `backend/app/services/pac_allocator/evaluator.py`;
- `backend/app/services/pac_allocator/numeric.py`;
- moduli ledger/fees/fx nuovi nello stesso package;
- test pure-service tramite `test-author`.

**Dipendenza:** Step 1; fixture W3 sufficienti, non route HTTP.

**Azioni**

1. Normalizzare snapshot in dataclass immutabili.
2. Validare unità, target, route, min/max, fee, FX, inventory, aliquota e PMC.
3. Implementare ledger per Broker/valuta.
4. Implementare fee piecewise, rounding minor unit, mid/charge/sell.
5. Implementare BUY/SELL cash instruction, `withholding_kind`, saldi
   spendibile/fisico e gross SELL posting senza doppio accredito.
6. Calcolare budget PAC raggiungibile e denominatori solo dal candidato.
7. Implementare evaluator di un candidato senza chiamare solver.
8. Produrre issue typed per missing/invalid/unsupported.
9. Inserire `context.checkpoint` solo come callback passata dall'esterno.

**Specialista:** Astra; `test-author`.

**Validazione futura**

```text
PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py test \
  --test-port 6153 --data-dir /tmp/librefolio-r2-d \
  services pac-planner-core
```

**Artifact:** truth tables cash/fee/FX/rounding.

**DoD:** evaluator non importa solver; riconcilia ogni ledger; nessun float;
cash/contributi/costi contati una volta; witness cross-currency prova
notional operativo, investimento mid e spread; invarianti verdi.

**Nota piano:** compilare subito il template §14 per Step 3.

### Step 4 — Oracle esaustivo, solver e limiti

**Owned surfaces**

- nuovi `solver.py`, `oracle.py`, `objectives.py`, `limits.py`;
- benchmark diagnostico sotto `backend/test_scripts/diagnostics/`;
- test tramite `test-author`;
- manifest dipendenza solo se una libreria viene scelta e approvata.

**Dipendenza:** Step 0, Step 1, Step 3.

**Azioni**

1. Definire dominio massimo supportato e failure mode.
2. Implementare vettori indipendenti per la base PAC deterministica.
3. Implementare oracle esaustivo completo per il residuo e il Rebalancer, non
   algoritmo equivalente al solver.
4. Implementare post-step PAC proportional/min_fragmentation.
5. Implementare Rebalancer invest_only.
6. Implementare invest_and_sell sequenziale con tax reserve per Asset.
7. Implementare residual optimization monotona sugli ordini, non sullo score.
8. Derivare tutti gli upper bound da cash/inventario; vietare Big-M
   arbitrari.
9. Separare outcome/proof/stop.
10. Validare ogni incumbent con evaluator Decimal indipendente.
11. Misurare cold start, solve, memoria e cancellazione senza installare
    dipendenze non approvate.

**Specialista:** Astra; `test-author`; rubber-duck matematica.

**Validazione futura**

```text
PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py test \
  --test-port 6153 --data-dir /tmp/librefolio-r2-d \
  services pac-planner-solver

PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py test \
  --test-port 6153 --data-dir /tmp/librefolio-r2-d \
  diagnostics pac-planner-benchmark
```

**Artifact:** oracle comparison matrix + supported-domain benchmark.

**DoD:** solver=oracle nei casi completi, inclusa la stessa sequenza
invest-only→sell; nessuna falsa ottimalità; no-op, infeasible,
incumbent/no-incumbent e limiti distinti; cancellazione osservata.

**Nota piano:** compilare subito il template §14 per Step 4.

### Step 5 — Report operativo e plugin Tool

**Owned surfaces**

- `backend/app/services/pac_allocator/report.py`;
- `backend/app/services/pac_allocator/__init__.py`;
- `backend/app/services/tool_plugins/pac_allocator.py`;
- PAC-specific registry/worker/API tests via `test-author`.

**Dipendenza:** Step 1, Step 3, Step 4.

**Azioni**

1. Costruire output operativo completo.
2. Mantenere plugin sottile: validate → normalize → solve → evaluate → report.
3. Dichiarare due `ToolService`, operation `plan`, root reali.
4. Passare `context.checkpoint`.
5. Rimuovere P1 `analyze`.
6. Provare batch eterogeneo, item ripetuti, output invalid, timeout/cancel.
7. Verificare nessun import DB/provider/domain service nel compute.

**Specialista:** backend Tool; `test-author`; review auth/invarianti Astra.

**Validazione futura**

```text
PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py test \
  --test-port 6153 --data-dir /tmp/librefolio-r2-d \
  services pac-tool

PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py test \
  --test-port 6153 --data-dir /tmp/librefolio-r2-d \
  api pac-tool-api
```

**Artifact:** catalog/compute/diagnostic payload sanitizzati.

**DoD:** due servizi reali; atomicità; no lookup; correlation/order/cardinality;
errori piattaforma non mascherati da risultato finanziario.

**Nota piano:** compilare subito il template §14 per Step 5.

### Step 6 — API sync, codec, fingerprint e renderer mapping

**Owned/shared surfaces**

- export schema Tool;
- client TypeScript generato;
- codec/version map;
- `frontend/src/lib/features/tools/registry.ts`;
- test codec/compatibilità.

**Dipendenza:** Step 2 e Step 5 stabili.

**Azioni**

1. Prenotare lease unico.
2. Eseguire API sync ufficiale.
3. Verificare root bundled e literal `plan`.
4. Rigenerare codec senza hand-written financial types.
5. Allineare fingerprint/component key/UI SemVer.
6. Provare renderer unknown/mismatch fail-closed.
7. Rieseguire sync e verificare diff vuoto.

**Specialista:** integratore shared; `test-author`.

**Validazione futura**

```text
PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py api sync

PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py test \
  --test-port 6153 --data-dir /tmp/librefolio-r2-d \
  front-utility tool-client-unit
```

**Artifact:** fingerprint table + deterministic second sync.

**DoD:** nessun P1 codec/type; client e catalogo concordi; generated diff
deterministico; renderer incompatibile non monta.

**Nota piano:** compilare subito il template §14 per Step 6.

### Step 7 — Shell, draft e source-copy frontend

**Owned surfaces**

- `planner/OperationalPlannerShell.svelte`;
- `planningDraft.svelte.ts`;
- `planningSourceCopies.ts`;
- funding/Broker/Asset/route/target/FX/review step components;
- wrapper PAC/Rebalancer solo per wiring;
- unit test via `test-author`.

**Dipendenza:** Step 1 fixture; Step 2/6 per integrazione reale.

**Azioni**

1. Implementare wizard progressivo Svelte 5.
2. Separare funding source da Broker operativo.
3. Supportare existing/manual in entrambi i ruoli.
4. Implementare enum, non flag mutuamente esclusivi.
5. Applicare copy preview e stale/account/request/revision guards.
6. Mostrare provenance/date/age/override.
7. Costruire snapshot review immutabile.
8. Non calcolare economia nel browser.

**Specialista:** frontend delimitato; `test-author`.

**Validazione futura**

```text
PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py test \
  --test-port 6153 --data-dir /tmp/librefolio-r2-d \
  front-utility pac-planner-component-unit
```

**Artifact:** component matrix + fixture snapshot.

**DoD:** manuale senza Asset DB; copie non distruttive; draft protetto;
nessun impossible-state boolean; responsive/accessibile.

**Nota piano:** compilare subito il template §14 per Step 7.

### Step 8 — PAC UI e policy

**Owned surfaces**

- `PacAllocatorTool.svelte`;
- PAC-specific editor/presentation;
- PAC component/E2E test via `test-author`.

**Dipendenza:** Step 4/5/6/7; ASCII developer-approved.

**Azioni**

1. Collegare `proportional` e `min_fragmentation`.
2. Mostrare base + optimized senza toggle input.
3. Renderizzare grafico acquisti, exposure cards, summary Asset e tabelle
   funding/FX/ordini Broker.
4. Mostrare min-fragmentation rationale e fee tie-break.
5. Coprire zero budget, low budget/no-op, hard-min infeasible, limits, stale.

**Specialista:** frontend; `test-author`.

**Validazione futura**

```text
PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py test \
  --test-port 6153 --data-dir /tmp/librefolio-r2-d \
  front-utility pac-planner-component-unit

PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py test \
  --test-port 6153 --data-dir /tmp/librefolio-r2-d \
  front-utility pac-planner
```

**Artifact:** desktop/mobile screenshots sintetici.

**DoD:** PAC spende solo cash selezionato; tabella core completa; target acquisti
vs acquisti reali; no ordini eseguiti.

**Nota piano:** compilare subito il template §14 per Step 8.

### Step 9 — Rebalancer UI e policy

**Owned surfaces**

- `PortfolioRebalancerTool.svelte`;
- Rebalancer-specific editor/presentation;
- Rebalancer component/E2E test via `test-author`.

**Dipendenza:** Step 0/4/5/6/7; ASCII developer-approved.

**Azioni**

1. Collegare invest_only default.
2. Collegare invest_and_sell con aliquota Asset e PMC espliciti.
3. Mostrare lower bound `K*` come diagnostico, non promessa.
4. Mostrare cash usato prima dei SELL.
5. Mostrare inventory, proventi, fee, tax reserve e PMC lordo.
6. Visualizzare no-op/infeasible/incumbent/limit onestamente.
7. Grafici whole-portfolio `Ora/Target/Dopo` su denominatore investito comune,
   con cash KPI separato.

**Specialista:** frontend; `test-author`.

**Validazione futura**

```text
PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py test \
  --test-port 6153 --data-dir /tmp/librefolio-r2-d \
  front-utility rebalancer-planner-component-unit

PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py test \
  --test-port 6153 --data-dir /tmp/librefolio-r2-d \
  front-utility rebalancer-planner
```

**Artifact:** desktop/mobile screenshots sintetici.

**DoD:** nessun SELL implicito/oversell/buy+sell; cassa netta certificata;
K* etichettato correttamente; tabelle Broker complete.

**Nota piano:** compilare subito il template §14 per Step 9.

### Step 10 — Matrice test, property/invariant e runner

**Owned/shared surfaces**

- nuovi file test esclusivi;
- registrazioni runner con lease;
- nessun production file salvo fix autorizzati separatamente.

**Dipendenza:** Step 1–9.

**Azioni test-author**

- schema/discriminanti/extra/nonfinite/cardinalità;
- normalizer/evaluator Decimal indipendente;
- property/invariant:
  - cash conservation;
  - FX debit-credit;
  - gross SELL minus fee/tax equals net once;
  - no oversell;
  - no same-Asset BUY+SELL;
  - no cycle/arbitrage;
  - fee not investment;
  - base immutable;
  - common invested denominator;
- oracle esaustivo;
- equivalenza preset a stesso input normalizzato;
- integer/cash order mode;
- min/max/min-if-operated/required hard min;
- rounding/minor unit/low budget;
- multi-currency/FX stale/spread witness/buffer;
- finite bounds derived from cash/inventory;
- permissions/OWNER0/privacy;
- cancellation/resources;
- registry/catalog/fingerprint/API;
- frontend desktop/mobile/manual/copies/stale;
- onboarding anchors/replay se toccati.

**Specialista:** `test-author`; integratore runner unico; review invarianti Astra.

**Registrazioni proposte**

- `schemas pac-planner`;
- `services pac-planner-core`;
- `services pac-planner-solver`;
- `services pac-tool`;
- `api pac-tool-api`;
- `front-utility pac-planner-component-unit`;
- `front-utility rebalancer-planner-component-unit`;
- `front-utility pac-planner`;
- `front-utility rebalancer-planner`.

La categoria Playwright è `front-utility`; i nomi azione
`pac-planner`/`rebalancer-planner` restano proposti finché il writer verifica il
catalogo runner corrente. Un solo writer registra tutti i selector.

**Validazione futura:** eseguire selector mirati, poi categorie integrate,
sempre seriali nella lane 6153. Nessun test assume posizione, count globale,
sleep o testo tradotto.

**Artifact:** test catalogue diff + pass counts.

**DoD:** tutti i witness obbligatori coperti; nessun file test orfano; nessun
test P1 residuo.

**Nota piano:** compilare subito il template §14 per Step 10.

### Step 11 — Docs, i18n, CHANGELOG e onboarding

**Owned/shared surfaces**

- guide EN PAC/Rebalancer;
- developer Tool guide;
- MkDocs nav;
- quattro cataloghi i18n;
- `CHANGELOG.md`;
- onboarding solo se anchor nuovo.

**Dipendenza:** contratto/UI stabili.

**Azioni**

1. `docs-writer` riscrive guide EN, non traduzioni.
2. Documentare termini, dati, strategie, tabelle, proof/status e limiti.
3. Aggiornare developer Tool guide con snapshot-only compute.
4. Registrare debito traduzioni; tradurre solo su richiesta esplicita.
5. Integratore i18n usa CLI, rimuove chiavi P1 orfane.
6. Aggiungere CHANGELOG user-facing.
7. Verificare guide/replay onboarding se anchor cambia.

**Specialista:** `docs-writer`; integratore i18n/CHANGELOG; `test-author` solo
se onboarding cambia.

**Validazione futura**

```text
PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py mkdocs build
PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py mkdocs check-links
PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py mkdocs translate-validate
PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py i18n audit
```

**Artifact:** docs link report + translation debt.

**DoD:** guide EN corrette; P1 non descritto come attivo; changelog accurato;
nessuna traduzione automatica non richiesta.

**Nota piano:** compilare subito il template §14 per Step 11.

### Step 12 — Gate integrati e review indipendenti

**Owned surfaces:** combined revision, nessuna nuova feature.

**Dipendenza:** Step 1–11.

**Azioni**

1. Static/lint/typecheck mirati.
2. Suite integrate seriali.
3. API sync freshness.
4. Provare che il diff non contiene migration o modelli DB planner.
5. Review indipendente matematica, auth/privacy, worker resource cleanup.
6. `check-orphans`, diff check, generated-file audit.
7. Provare porta libera a fine gate.

**Specialista:** integratore combined; rubber-duck matematica; review auth/privacy
read-only.

**Validazione futura**

```text
PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py test \
  --test-port 6153 --data-dir /tmp/librefolio-r2-d check-orphans

PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py front check
PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py front build
git diff --check
lsof -nP -iTCP:6153 -sTCP:LISTEN
```

**Artifact:** combined gate manifest.

**DoD:** zero finding blocking; nessun runtime residuo; niente private/generated
artifact impropri; prove riferite alla revisione combinata.

**Nota piano:** compilare subito il template §14 per Step 12.

### Step 13 — Review developer e correzioni

**Owned surfaces:** runbook + eventuale piano Round 6 cross-linked; nessun fix
senza nuova autorizzazione.

**Dipendenza:** Step 12.

**Azioni**

1. Eseguire runbook sezione 16 dalla sidebar Tool.
2. Registrare feedback con ID, vista/stato, expected/observed, priorità.
3. Correzioni aprono un piano Round 6 linkato.
4. Rieseguire scenari interessati e gate regressione.
5. Chiudere solo con approvazione developer.

**Specialista:** developer reviewer; coordinatore; specialisti dei soli fix
autorizzati.

**Validazione:** review manuale + gate del piano follow-up.

**Artifact:** feedback log e decisione.

**DoD:** PAC e Rebalancer approvati separatamente; test verdi non sostituiscono
review.

**Nota piano:** compilare subito il template §14 per Step 13.

## 14. Template avanzamento obbligatorio

Dopo ogni step completato:

```text
- [x] Step N — titolo — YYYY-MM-DD
  > **Nota implementazione**: file/simboli cambiati, comportamento consegnato.
  > **Evidenza**: comando esatto, selector, pass count, artifact/hash.
  > **⚠️ Fuori pista**: errore/detour, impatto DB/file/server, recupero e
  > validità delle prove. Omettere solo se nessun detour.
```

Aggiornare immediatamente questo piano; non accumulare note alla fine.

## 15. Matrice di accettazione

| Famiglia | Witness minimo |
|---|---|
| PAC | target×budget, floor whole/monetary, route fallback, unavailable target, residual proportional/min-fragmentation, low budget, zero BUY fee, trapped cash excluded from denominator |
| Rebalancer | no-op, invest-only, zero new cash, sequential invest+sell, overweight zero target |
| Asset/Broker | stesso Asset multi-Broker, priorità uguali/diverse, route esclusa |
| Funding | new, existing, manual, source=trading Broker, partial cash selection |
| Ordini | quote_base_quantity, capability frazioni sì/no, output share quantity/cash amount, order step, min-if-operated, required hard min |
| Inventory | fractional existing holding, integer SELL floor, cash SELL step/residual, no oversell |
| Fee | fixed, rate, min, max, BUY 0/SELL nonzero |
| FX | none, native, auto-buy, stale, spread witness, buffer rate/amount, fixed fee, missing pair |
| Cash | native ledgers, transfer, gross SELL posting, fee, tax reserve, withholding kind, physical/spendable balance, net equivalence, no duplicate contribution |
| Solver | PAC base direct-vector equality; residual/Rebalancer oracle equality, sequential Rebalancer oracle, derived finite bounds, deterministic tie, incumbent/limit, no incumbent/limit |
| Status | no-op for low/blocked usefulness, needs-input, unsupported, hard-constraint infeasible proven, optimal proven |
| Snapshot | manual/copy equivalent, override, stale response, account switch |
| Auth/privacy | OWNER, OWNER0, unauthorized Broker, no personal values in logs |
| UI | desktop/mobile, keyboard, Asset summary + Broker tables, common invested denominator, cash KPI, chart no-data, stale/busy/error |
| Platform | repeated tool items, distinct IDs, output validation, cancellation/cleanup |

Gli esempi `3484.14` e `3493.24` dello studio sono witness aritmetici sotto le
loro assunzioni, non golden di ottimalità.

## 16. Runbook review manuale futura

**Ambiente**

- build/revisione combinata dichiarata;
- lane 6153 e `/tmp/librefolio-r2-d`;
- utente sintetico OWNER;
- fixture senza valori personali;
- porta libera prima/dopo.

**Percorso**

1. Sidebar → Tool.
2. Aprire PAC.
3. Scenario manuale: nuova liquidità, Broker manuale senza frazioni,
   proportional.
4. Copiare conto/Broker/Asset/FX; modificare un campo dopo il fetch; verificare
   che risposta tardiva non sovrascriva.
5. PAC min-fragmentation con due Broker e fee diverse.
6. Rebalancer invest-only con cash parziale.
7. Rebalancer invest-and-sell con aliquote Asset 26% e override.
8. Verificare fee→gain positivo→tax reserve→cash netto.
9. FX stale: age visibile, override consapevole.
10. Low budget/no-route → no-op; hard minimum incompatibile →
    infeasible-proven; limite con/senza incumbent distinto.
11. Confrontare base e optimized; base invariata.
12. Leggere funding, FX e ordini per Broker.
13. Ripetere viewport mobile e tastiera.
14. Replay onboarding Tools se gli anchor sono cambiati.

**Attesi**

- nessun ordine realmente inviato;
- nessun dato fuori scope;
- nessun calcolo frontend autorevole;
- tabelle riconciliano il ledger;
- grafici rappresentano output reale;
- copy e result stale non mutano il draft.

## 17. Rollback e recovery

- Checkpoint per step; niente mega-integrazione senza prove intermedie.
- P1 non viene mantenuto come fallback. Se Round 5 non supera i gate, il Tool
  resta unavailable/feature branch non integrata; non si riattiva `analyze`.
- Nessuna migration DB v1. Se compare una migration planner, fermare e
  ricondurre i parametri allo snapshot per-run.
- API sync fallito: correggere schema e rigenerare; non editare output generato.
- Solver senza benchmark/supporto: bloccare integrazione, non ridurre limiti
  silenziosamente.
- Failure runtime: fermare PID esatto, verificare porta, registrare DB toccato e
  invalidare prove dipendenti.
- Merge conflict shared: risoluzione semantica, conservare contratti integrati,
  rieseguire combined gates; niente scelta wholesale di un lato.

## 18. Rischi e stop condition

| Rischio | Mitigazione | Stop |
|---|---|---|
| formula fiscale o aliquota cambiano | riaprire Step 0 + math review | nessun invest_and_sell |
| solver non prova ottimo | proof/status ortogonali | mai etichetta optimal |
| numeri cross-currency incoerenti | ledger nativi + evaluator | candidate rifiutato |
| budget PAC circolare | direct ledger solve + `B_ref(x)` solo diagnostico | integrazione bloccata |
| ordine cash confonde mid/charge | instruction contract + witness spread | candidate rifiutato |
| free FX/arbitrage | conversione accoppiata single-hop | candidate rifiutato |
| parametro Broker trattato come persistito | schema snapshot + no-DB assertion | integrazione bloccata |
| copy omette missing | typed missing issue | submit bloccato |
| frontend ricrea economia | result-only selectors | review blocking |
| residual riscrive base | delta monotono | optimized coincide con base e delta zero |
| dipendenza solver non disponibile | benchmark prima manifest | nessuna installazione autonoma |
| worker supera risorse | checkpoint + hard limits + cleanup | platform error |
| shared writer collision | lease e checkpoint order | workstream freeze |
| onboarding race | anchor-only change + existing settlement tests | nessuna modifica layout |
| regressione matematica dopo cambio contratto | review nuova obbligatoria | integrazione bloccata |

## 19. Deferred / `TODO_FUTURI.md`

| Estensione differita | Confine v1 |
|---|---|
| distribuzione proporzionale forzata fra Broker | v1 usa route/priorità/policy, nessuna quota Broker target |
| vendita proporzionale fra custodie | v1 minimizza secondo policy/tie-break |
| chiusura Broker | nessun obiettivo “svuota Broker” |
| consolidamento custodia | nessun obiettivo “porta tutto su Broker X” |
| minimizzazione plusvalenze | PMC informativo, non obiettivo |
| compensazione minus | carried losses informative |
| tax-loss harvesting | escluso |
| categorie/scadenze minus | v1 singolo importo Broker |
| fee per mercato | v1 profilo Broker/lato/valuta |
| fee intraday dinamiche/degressive | già registrate nel TODO |
| fee/limiti/tempi bonifico | trasferimenti v1 gratuiti/immediati |
| multi-hop FX e routing globale | v1 single-hop dichiarato |
| margine dinamico per volatilità | v1 `fx_buffer_rate` esplicito |
| persistenza fonti/Broker manuali | v1 scenario-only |
| profilo operativo Broker persistito | v1 parametri per-run |
| aliquota plusvalenze persistita sull'Asset | v1 prefill 26% + override snapshot |
| portafogli/gruppi target | fuori planner v1 |

## 20. Definition of done

Round 5 è implementato solo quando:

1. Contratto corretto Step 0 e formula fiscale sono approvati e testati.
2. P1 è eliminato senza adapter/fallback/dual version.
3. PAC e Rebalancer espongono `plan` su contratto `1.0.0`.
4. Snapshot completo e immutabile rende il worker autonomo da DB/service/provider.
5. Ledger nativi riconciliano cash, trasferimenti, FX, SELL, BUY, fee,
   tax reserve e buffer.
6. Evaluator Decimal indipendente valida ogni candidato solver.
7. Oracle completo coincide sui casi piccoli.
8. Status/proof/stop non fanno false promesse.
9. Base e optimized sono entrambe leggibili e la seconda non riscrive la prima.
10. Parametri Broker/aliquote Asset restano snapshot per-run; nessuna migration
    planner v1.
11. Manual scenario funziona senza Asset/Broker DB.
12. Copy domain è completo, permission-safe, provenance-aware e stale-safe.
13. UI PAC/Rebalancer resta distinta, Svelte 5, mobile, accessibile e privata.
14. Summary Asset conserva target/residui una volta; tabelle Broker contengono
    istruzioni, prezzi, quantità, costi e cash effect core.
15. Grafici/card mostrano output reale `Ora/Target/Dopo` con `Unknown`, più
    funding/cash KPI separati.
16. API sync/fingerprint/codec/renderer sono deterministici e fail-closed.
17. Test-author copre schema/math/oracle/API/component/E2E/runner.
18. Docs-writer consegna EN; i18n/changelog condivisi sono allineati.
19. Gate combinati e review indipendenti non hanno finding bloccanti.
20. Developer approva separatamente PAC e Rebalancer tramite runbook.
21. Porta 6153 è libera e nessun artifact privato/runtime viene integrato.

## 21. Ordine checkpoint

1. Corrected contract freeze.
2. Schema/models.
3. Core evaluator.
4. Domain copies, no DB migration.
5. Solver/oracle/benchmark.
6. Plugin/report.
7. API sync/codec/fingerprint.
8. Shared shell/source copy.
9. PAC UI.
10. Rebalancer UI.
11. Runner/i18n/docs/changelog.
12. Combined gates/reviews.
13. Manual developer review.

Ogni checkpoint dichiara HEAD/base, file, prove, esclusioni, conflitti e commit
message proposto. Nessun checkpoint viene staged dal workstream D senza richiesta
del coordinatore.

→ Follow-up:
[Round 6 — PAC/Rebalancer UI Blueprint](plan-phase00Step2Round6-PacRebalancerUiBlueprint.prompt.md)
