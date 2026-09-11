# H - Yield on Cost da ledger transazioni (U3 / primo incremento SP06)

**Stato:** ✅ **H REFINEMENT DEVELOPER ACCEPTED / FROZEN 2026-09-11**;
implementazione, gate, review e walkthrough completati. Checkpoint pronto per
staging/integrazione manuale coordinator/developer.
**Owner:** workstream H.
**Baseline di analisi:** `f90d9801bd7a2d74aac6a27efe305314c6c004cc`
su `dev_release2`.
**Baseline tecnica Gate 0:** `b22998f218034e470809c58223e38b3ef449038f`,
merge di `3503941d` + `dev_release2@b5ed1a623`, incluso il fix
`cost_basis_currency`.
**Branch di piano:** `e-alfy-h-yield-on-cost`.
**Target di integrazione:** `dev_release2`, tramite checkpoint manuale
developer/coordinator; H non esegue staging, commit o merge.
**Lane di esecuzione:** porta `6156`, data root assoluta
`/tmp/librefolio-r2-h-yoc`.

Fonti:

- [U3 - UX e Dashboard](../09_feedbackJobs/01_ux_dashboard.md)
- [Piano sprint - U3 / SP06](../09_feedbackJobs/06_piano_sprint.md)
- [Decisione FIFO D-1](../../../../LibreFolio_devWiki/wiki/decisions/fifo-v4-income-eligibility-d1.md)
- [Finestra di eligibility D-1](../../../../LibreFolio_devWiki/wiki/concepts/d1-income-eligibility-window.md)

Questo documento prende in carico soltanto U3. Non prende in carico rolling
return G3, istogrammi income G1c o altri incrementi SP06.

## 1. Obiettivo e confini non negoziabili

Yield on Cost (YOC) misura il reddito lordo registrato per unita' rispetto al
PMC/WAC unitario residuo della posizione. La metrica appare nella tabella
Holdings condivisa fra Dashboard e dettaglio Broker.

| Tema | Contratto finale |
|---|---|
| Fonte | Sole `Transaction` asset-linked di tipo `DIVIDEND` o `INTEREST`. |
| Lordo | Gli importi income LibreFolio sono lordi. `TAX` e `FEE` restano transazioni separate e non entrano nel YOC. |
| Scope | Una metrica per `(asset_id, broker_id)`. |
| Finestra | Da `T - 364` a `T`, estremi inclusi, indipendente da `date_from`. |
| Quantita' | Quantita' LONG eleggibile a fine D-1, paying-broker scoped e transfer-aware. |
| Base | WAC/PMC unitario residuo della stessa posizione alla data `T`. |
| FX | Income convertito alla transaction date; WAC convertito a `T`; backward resolution portfolio esistente, senza cap YOC. |
| Split | Ogni payout storico viene riallineato all'unita' corrente tramite gli split-linked ADJUSTMENT canonici. |
| Trasferimenti | Nessun carry automatico dello storico income dal broker source al broker destination. |
| Applicabilita' | Ogni holding, inclusi crypto e asset manuali; nessuna whitelist o `not_applicable`. |
| UI | Colonna visibile di default, accanto ad Annualized Return, 2 decimali, nessun `+`. |

Fuori scope:

- `AssetEvent` DIVIDEND/INTEREST, provider e loro coverage;
- gross-up o associazione TAX/FEE -> income;
- migrazioni DB;
- modifica di `portfolio_engine.py` da parte di H;
- carry dell'income attraverso la lineage dei lotti trasferiti;
- percentuali asset-global o somma income / current cost basis;
- rolling return, income chart, privacy globale e altri refactor portfolio.

## 2. Formula canonica

Per una posizione asset \(a\), broker \(b\), data finale \(T\):

$$
\operatorname{YOC}_{a,b}(T)=
\frac{
\displaystyle\sum_{\substack{i\in I_{a,b}\\T-364\le d_i\le T}}
\frac{\operatorname{FX}(A_i,c_i\rightarrow C,d_i)}
{Q^-_{a,b}(d_i)\,
\displaystyle\prod_{\substack{s\in S_{a,b}\\d_i\le d_s\le T}}r_s}
}
{\operatorname{WAC}^{C}_{a,b}(T)}
$$

Dove:

- \(A_i\) e' l'importo lordo non negativo registrato dalla transaction income;
- \(Q^-_{a,b}(d_i)\) e' la quantita' LONG eleggibile a fine \(d_i-1\);
- \(r_s\) e' il rapporto di uno split-linked ADJUSTMENT applicato alla stessa
  posizione; uno split sul giorno income e' incluso perche' l'eligibility e'
  pre-split;
- \(C\) e' la valuta report;
- \(\operatorname{WAC}^{C}_{a,b}(T)\) e' il WAC unitario residuo a `T`.

Invarianti:

1. Same-day BUY non riceve l'income; same-day SELL resta eleggibile.
2. L'ordine tecnico `date,id` non decide l'entitlement income.
3. Vendita parziale successiva non gonfia la metrica: ogni payout e'
   normalizzato con la quantita' della propria data.
4. La quantita' corrente non divide il numeratore.
5. Gli income sono non negativi per il contratto Pydantic condiviso; zero
   registrato resta distinto dall'assenza di income, mentre YOC non mantiene
   una semantica legacy per importi negativi.
6. Un solo payout non convertibile o non allocabile invalida l'intera metrica;
   non esiste YOC parziale.

### 2.1 Perche' non usare le alternative

| Alternativa | Difetto |
|---|---|
| `sum(income) / current_cost_basis` | Una vendita parziale riduce la base e gonfia il rendimento. E' cash yield su base corrente, non YOC per-unit. |
| `income / current_quantity` | Usa una quantita' diversa da quella che ha generato l'incasso. |
| Quantita' immediatamente prima della riga `date,id` | L'import order decide same-day BUY/SELL. |
| Quantita' EOD D | Include BUY del giorno ed esclude SELL del giorno, contro la decisione FIFO D-1. |
| Asset-global | Mescola broker, fiscalita'/valute e scope; rende la stessa riga diversa fra Dashboard e Broker. |

## 3. Replay quantity, transfer e split

### 3.1 Eligibility D-1

Riutilizzare la semantica gia' implementata nel `FifoLotEngine`:

- LONG lot aperto a fine D-1;
- stesso asset e paying broker;
- frammento `BROKER` sul broker pagante;
- frammento `IN_TRANSIT` ancora eleggibile sul broker source;
- destination eleggibile solo se l'arrivo esiste gia' a D-1.

Non duplicare questa logica con una semplice somma di `Transaction.quantity`.
Per limitare il costo, eseguire il replay puro soltanto per asset aperti che
hanno almeno una transaction income nella finestra. Le coppie senza income
usano soltanto l'age check della sezione 4.

**Esito Gate 0:** i gruppi economici FIFO non sono riusabili come numeratore
YOC: applicano `abs()` agli importi e pubblicano pesi, non la quantita'
eleggibile assoluta. La seam raccomandata e' quindi estrarre l'attuale
`_eligible_income_quantity(fragments, broker_id, cutoff)` come helper puro
pubblico, riusato sia dal FIFO sia da YOC. H esegue il replay quantitativo per
asset, legge i `fragment_intervals` e mantiene separato il calcolo
dell'income. Nessuna terza implementazione D-1/transfer-aware.

### 3.2 Split

Il numeratore non usa `AssetEvent` come fonte income. Per gli split riusa
soltanto la classificazione canonica dello split-linked ADJUSTMENT gia'
necessaria ai motori portfolio/FIFO.

- Split su D: applicare il rapporto al payout di D.
- Split successivo: dividere il payout per il prodotto dei rapporti fino a `T`.
- Split per un altro broker: non modifica questa posizione.
- Ratio nullo, non finito, non positivo, duplicato/incoerente o replay non
  riconciliato: `unavailable`, reason tipizzata.
- Se la baseline integrata non espone il rapporto canonico senza creare una
  seconda interpretazione, fermare lo step e chiedere un handoff: non inferire
  il rapporto da trade/transfer same-day.

### 3.3 Transfer

L'eligibility conserva la policy asimmetrica FIFO. Lo storico YOC resta sul
broker che ha registrato l'incasso:

- income sul source durante transit: eleggibile sul source;
- income sul destination prima dell'arrivo D-1: orphan e YOC unavailable;
- income precedente a un transfer non viene copiato nella futura riga del
  destination;
- close/rebuy sullo stesso broker non resetta l'age della coppia.

## 4. Age, zero noto e unavailable

L'age della coppia e' ancorata alla prima `Transaction` storica per
`(asset_id, broker_id)`, qualunque sia il tipo. Non si resetta quando la
quantita' raggiunge zero o la posizione viene riaperta.

Per finestra inclusiva di 365 giorni:

```text
history_sufficient = first_pair_transaction_date <= T - 364
```

| Caso | Status | Value | Rendering |
|---|---|---:|---|
| Income validi | `available` | frazione positiva | `4.27%` |
| Uno o piu' income registrati a zero | `available` + provenance `net_zero` | `0` | `0.00%` |
| Nessun income TTM, age sufficiente | `no_income` | `0` | `-`, senza icona problema |
| Nessun income TTM, coppia giovane | `unavailable` / `insufficient_history` | `null` | `-` + info Tooltip |
| Income senza quantita' D-1 | `unavailable` / `income_without_eligible_quantity` | `null` | `-` + info Tooltip |
| Replay incoerente | `unavailable` / `replay_inconsistent` | `null` | `-` + info Tooltip |
| FX mancante | `unavailable` / `missing_fx` | `null` | `-` + info Tooltip |
| WAC nullo/non positivo | `unavailable` / `missing_wac` o `non_positive_wac` | `null` | `-` + info Tooltip |
| Split invalido | `unavailable` / `invalid_split` | `null` | `-` + info Tooltip |

Assetless DIVIDEND/INTEREST non appartengono a una holding e vengono ignorati
dal YOC. Non rendono indisponibili altre posizioni.

## 5. DTO e provenance

Estendere `PortfolioHolding` con un campo required:

```text
yield_on_cost: YieldOnCostResult
```

Il backend corrente restituisce sempre un oggetto per ogni holding; il campo
outer resta opzionale nel contratto per non invalidare client precedenti e la
fixture reale `frontend/e2e/dashboard-report.json`.

Shape proposta:

```text
YieldOnCostResult
  status: available | no_income | unavailable
  value: Decimal | null                  # fraction, not display percent
  reason: YieldOnCostUnavailableReason | null
  provenance: YieldOnCostProvenance

YieldOnCostProvenance
  source: transactions
  window_start: date
  window_end: date
  first_pair_transaction_date: date | null
  gross_income_transaction_count: int
  gross_income_per_unit: Currency | null
  net_zero: bool
  fx: list[YieldOnCostFxProvenance]

YieldOnCostFxProvenance
  purpose: income | wac
  requested_date: date
  rate_date: date
  from_currency: str
  to_currency: str
```

Per una conversione identity, la provenance la dichiara esplicitamente oppure
la omette secondo una sola policy testata; non inventa una riga FX DB.

Validatore del DTO:

- `available` -> value non negativo; reason null; zero richiede `net_zero=true`;
- `no_income` -> value esattamente zero; reason null;
- `unavailable` -> value null; reason obbligatoria;
- nessun `not_applicable`;
- reason enum stabile, mai testo libero.

## 6. FX e cache portfolio

### 6.1 Contratto F integrato e verificato

La baseline Gate 0 contiene l'implementazione F reale:

```python
async def compute_portfolio_fx_cache_identity(
    db,
    scope_broker_ids: set[int],
    target_currency: str,
    date_to: date,
) -> str:
    ...
```

Contratto osservato:

- sentinel `"no_fx"` quando non esistono coppie non-target;
- un solo SHA-256 deterministico sul payload bounded delle dipendenze FX;
- source currencies da `Transaction.currency`, `Asset.currency` degli asset con
  transaction quantitative e `PriceHistory.currency` fino a `date_to`;
- tutte le righe `FxRate` delle coppie bounded con data `<= date_to`, ordinate;
- tutte le `FXConversionRoute` persistite per le stesse coppie, ordinate, con
  priority, parsed steps e `updated_at`;
- string identity inserita direttamente nel blob key L1 fra price e split
  fingerprint;
- `sync_pairs_bulk` con cambiamenti, manual rate upsert e rate delete effettiva
  puliscono L1/L2; route mutation si invalida per cambio identity.

Test F osservati:

- identity stabile;
- pair/broker/rate futuro irrilevanti non cambiano hash;
- rate insert/update/delete/replacement rilevanti cambiano hash;
- route insert/priority/provider change cambiano hash;
- L1 hit stabile e miss su rate rilevante;
- delete effettiva pulisce entrambe le cache, no-op delete no.

**Fix integrato verificato da H:** la query include ora
`Transaction.cost_basis_currency` insieme a `Transaction.currency`; entrambe
alimentano `source_currencies`. I witness usano una terza valuta presente solo
nel CBO e provano identity non-`no_fx`, cambi su rate/route/provider e L1
hit/miss. H non deve modificare `portfolio_engine.py`.

### 6.2 L2 generale

`PortfolioService.get_report()` deve invocare la stessa
`compute_portfolio_fx_cache_identity(...)` e includere la stringa restituita
nella chiave L2 per **tutti** i report portfolio, anche quando
`include_summary=false`.

Punto di inserimento verificato: nel blocco `if scope_broker_ids`, dopo
risoluzione di access scope, `tx_fp` e `price_fp`, ma prima di costruire
`l2_key` e chiamare `_portfolio_l2_cache.get()`. Invocazione:

```python
fx_cache_identity = await compute_portfolio_fx_cache_identity(
    self.db,
    set(scope_broker_ids),
    base_currency,
    date_to or today,
)
```

La stringa entra una sola volta in `l2_key`. Non derivare hash rate/route
separati e non modificare la helper F.

Regole:

- nessun secondo fingerprint **FX**: la identity F resta unica;
- una identity YOC separata e' necessaria perche' il replay broker-detail legge
  anche ledger visibili cross-broker, transfer esterni, `allow_asset_shorting`
  e split che il `tx_fp` dello scope selezionato non vede;
- il costo pre-cache e' intenzionale: evita di servire un hit stale; il replay
  completo avviene soltanto sul miss;
- nessun fallback alla vecchia key se la helper fallisce;
- errori della helper propagano, salvo futuro stato `uncacheable` esplicitamente
  previsto dal contratto F;
- TTL/capienza L2 invariati;
- `tx_fingerprint` gia' copre income, BUY/SELL/TRANSFER/ADJUSTMENT;
- aggiungere soltanto la dipendenza materiale split-linked che non e' inclusa
  nel fingerprint transaction;
- nessun invalidatore globale dell'app.

Test cache futuri devono provare rate edit/upsert/delete, route edit/delete,
split ratio/type rilevante e un report senza summary. Un cache hit identico
resta un vero hit.

### 6.3 Gate 0 technical refresh - 2026-09-10 (COMPLETE)

- Baseline finale verificata a `b22998f`, parent target `b5ed1a623`.
- Firma, payload, L1 insertion e test F letti dal codice integrato.
- L2 insertion point e uso di `date_to or today` verificati.
- Fingerprint transaction esistente copre ogni `Transaction.id/updated_at`;
  split material fields restano una dipendenza distinta.
- Rate/route mutation cambiano content identity; clear esplicite sono difesa
  aggiuntiva, non la sola invalidazione.
- `cost_basis_currency` e relativi identity/L1 witness sono integrati.
- Reservation H-first/I-after confermata.
- Gate 0 tecnico e' **COMPLETE**. Al checkpoint Gate 0 l'implementazione era
  frozen in attesa dell'autorizzazione developer, poi ricevuta il 2026-09-10.

## 7. Superfici e ownership

### 7.1 File H previsti

| Area | File |
|---|---|
| Calcolo | nuovo `backend/app/services/yield_on_cost.py` |
| Orchestrazione/L2 | `backend/app/services/portfolio_service.py` |
| DTO | `backend/app/schemas/portfolio.py` |
| FIFO eligibility seam | `backend/app/services/fifo_lot_engine.py` |
| Test pure/service | nuovo `backend/test_scripts/test_services/test_financial/test_yield_on_cost.py` |
| Test FIFO seam | `backend/test_scripts/test_services/test_financial/test_fifo_lot_engine.py` |
| Test cache/report | `backend/test_scripts/test_services/test_financial/test_portfolio_service.py` |
| Test API | `backend/test_scripts/test_api/test_portfolio_api.py` |
| UI | `frontend/src/lib/components/dashboard/ExposureTable.svelte` |
| UI problem cell | nuovo `frontend/src/lib/components/dashboard/YieldOnCostCell.svelte` |
| Component test | `frontend/src/lib/components/dashboard/ExposureTable.test.ts` |
| User/theory docs EN | file elencati nella sezione 10 |

### 7.2 File esclusi o condivisi

- F resta owner di `backend/app/services/portfolio_engine.py`.
- H ha ricevuto ownership esclusiva di `portfolio_service.py`,
  `schemas/portfolio.py`, YOC/FIFO seam/test e ExposureTable durante
  l'esecuzione autorizzata.
- Workstream I blocca I20+ su engine/service/schema/report/cache, broker P&L e
  candles finche' H non e' integrato. Il solo G3 signal/backend isolato resta
  non sovrapposto. Sequenza approvata dal coordinator: **H prima, I dopo**.
- H non modifica `backend/app/services/asset_source.py`, provider,
  `backend/app/schemas/assets.py` o pagine Asset.
- Coordinator: `CHANGELOG.md`, quattro cataloghi i18n, API sync/client
  generato, runner registration, MkDocs nav e master backlog.
- Test nuovi/riparati: `test-author`, completati dopo autorizzazione.
- MkDocs EN: `docs-writer`, completati dopo autorizzazione.

## 8. Storyboard ASCII - gate G-UX-DESIGN

**Storyboard v1 APPROVED dal developer il 2026-09-10.** L'approvazione
plan/design ha preceduto la separata autorizzazione esecutiva, poi ricevuta e
attuata sul baseline Gate 0.

### 8.1 Desktop - Dashboard e Broker

Entrambe le pagine montano lo stesso `PositionsPanel/ExposureTable`.

```text
+--------------------------------------------------------------------------------------+
| YOUR POSITIONS                              [Holdings|Performance] [Table|Map] [eye] |
+----------------------+------------+--------------+-----------+----------+------------+
| Asset                | P&L %      | Annualized   | YOC       | Value    | Broker     |
+----------------------+------------+--------------+-----------+----------+------------+
| Global Equity ETF    | +12.18%    |  8.42%       |  4.27%    | ...      | Directa    |
| Manual Bond          |  +1.02%    |  3.11%       |  -        | ...      | Fineco     |
| Young Crypto Income  |  +7.50%    |  6.90%       |  - [i]    | ...      | Kraken     |
| USD Dividend Stock   |  -2.10%    | -1.40%       |  - [i]    | ...      | IBKR       |
+----------------------+------------+--------------+-----------+----------+------------+
```

Semantica righe:

- `4.27%`: available; nessuna icona stato.
- Manual Bond `-`: `no_income`, age >= 1 anno; normale, nessuna icona errore.
- Young Crypto `- [i]`: insufficient history.
- USD Stock `- [i]`: missing FX o altra reason tipizzata.
- La colonna e' visibile su un profilo senza override precedente.
- `[eye]` permette di nasconderla; stessa scelta riappare su Dashboard e Broker.

### 8.2 Header help

`YOC` resta ordinabile. Il normale help di header spiega formula e apre la
pagina teoria; non e' un indicatore di errore riga.

```text
          +--------------------------------------------------------------+
YOC  ---> | Gross recorded DIVIDEND/INTEREST per eligible D-1 unit,     |
          | over the last 365 days, divided by residual unit WAC at T.   |
          | FX uses portfolio backward resolution.  [Open theory]        |
          +--------------------------------------------------------------+
```

### 8.3 Tooltip problema desktop

Solo una cella `unavailable` mostra `[i]`.

```text
      - [i]
         |
         v
+------------------------------------------------------------+
| Yield on Cost unavailable                                  |
| Reason: insufficient history                               |
| Pair history starts: 2026-02-12                            |
| Required window starts: 2025-09-11                         |
| Source: gross DIVIDEND/INTEREST transactions                |
+------------------------------------------------------------+
```

Caso FX:

```text
+------------------------------------------------------------+
| Yield on Cost unavailable                                  |
| Reason: missing FX                                         |
| Requested: USD -> EUR on 2026-09-07                        |
| No portfolio backward-resolved rate is available.          |
+------------------------------------------------------------+
```

Caso FX disponibile: la provenance/tooltip formula puo' mostrare la data
effettiva usata senza trasformarla in warning:

```text
Income date 2026-09-07 -> FX rate date 2026-09-05
```

### 8.4 Mobile

La tabella conserva lo scroll orizzontale esistente; nessuna card YOC separata.

```text
+--------------------------------------+
| Positions                    [eye]   |
| [Holdings] [Performance]             |
| [Table]    [Map]                     |
+--------------------------------------+
| Asset        Annualized | YOC        |---->
+--------------------------------------+
| Equity ETF      8.42%   | 4.27%      |
| Manual Bond     3.11%   | -          |
| Young Crypto    6.90%   | - [i]      |
+--------------------------------------+
```

Tap su `[i]`:

```text
+--------------------------------------+
| Yield on Cost unavailable            |
| Insufficient history                 |
| First pair transaction: 2026-02-12   |
| Window start: 2025-09-11             |
|                              [Close]  |
+--------------------------------------+
```

Requisiti mobile/accessibilita':

- usare il custom `Tooltip`, non native `title`;
- hover desktop e tap-to-pin mobile;
- trigger tastiera/focusabile con `aria-label` reason-specific;
- dismiss secondo comportamento Tooltip esistente;
- `-` no-income non riceve icona problema;
- sorting e column visibility restano raggiungibili;
- nessun assertion E2E su testo tradotto.

### 8.5 Stati non ridisegnati

- Loading: usa `PositionsPanel[data-busy]` e skeleton esistenti.
- Empty holdings: usa empty state esistente; nessuna colonna senza righe.
- Error report: resta errore pagina/report esistente.
- Dark mode, row highlight e azioni lotti restano invariati.

## 9. Piano incrementale e progress tracking

| Step | Scope | Stato |
|---|---|---|
| H00 | Baseline, contratto, piano, cross-link e storyboard ASCII | ✅ 2026-09-10 - plan/storyboard v1 approved |
| H01 | Gate 0 post-F: helper FX/L1/L2, seam FIFO/UI e collisioni | ✅ 2026-09-10 - technically complete |
| H02 | Test-author: oracle e casi replay/formula/cache prima del wiring | ✅ 2026-09-10 - 36 regressions authored, runtime validation in H09 |
| H03 | DTO typed + calcolatore YOC transaction-ledger | ✅ 2026-09-10 - implementation complete, validation in H09 |
| H04 | D-1/transfer/split replay e integrazione summary | ✅ 2026-09-10 - implementation complete, validation in H09 |
| H05 | Shared FX identity nella L2 generale + dipendenze YOC | ✅ 2026-09-10 - implementation complete, validation in H09 |
| H06 | API contract/client e i18n tramite coordinator | ✅ 2026-09-11 - sync strict + 2587/2587 catalogs |
| H07 | ExposureTable + component test secondo storyboard approvato | ✅ 2026-09-10 - implementation/tests authored, validation in H09 |
| H08 | Docs EN tramite docs-writer + nav coordinator | ✅ 2026-09-10 - EN complete; nav handed to coordinator |
| H09 | Gate mirati/integrati nella lane H | ✅ 2026-09-10 - backend/API/component/type/build green |
| H10 | Walkthrough Dashboard/Broker e feedback developer | ✅ 2026-09-11 - developer accepted |
| H11 | Checkpoint finale, integrazione e chiusura documentale | ✅ 2026-09-11 - frozen checkpoint ready |

> **Note implementazione** (H00, 2026-09-10): creati esclusivamente piano e
> storyboard, con backlink U3/SP06 ora marcati PLAN/DESIGN APPROVED. Nessun file applicativo,
> test, schema runtime, i18n, generated client o migration e' stato modificato.
> L'implementazione resta bloccata sia dall'integrazione del checkpoint F sia
> da una nuova autorizzazione esplicita. Il developer ha approvato coerenza del
> piano e storyboard v1 il 2026-09-10; questa e' approvazione PLAN/DESIGN, non
> autorizzazione a eseguire H01-H11.

> **Note Gate 0 / H01 (2026-09-10, complete tecnicamente):** baseline
> `b22998f`, F identity/L1/test e L2 insertion point verificati. DTO/service/test
> split resta valido; aggiunti il seam FIFO eligibility e una cella UI dedicata
> per Tooltip accessibile. Coordinator ha riservato H prima di I sui file
> portfolio condivisi. Il merge target `b5ed1a623` ha incluso
> `cost_basis_currency` con witness identity e L1 verdi. Unico blocco residuo:
> autorizzazione esecutiva developer.

> **Note autorizzazione esecutiva (2026-09-10):** il developer ha autorizzato
> H02-H11 sulla baseline `b22998f`, con ownership esclusiva delle superfici H
> elencate nella sezione 7 e sequenza H prima di I20+.

> **⚠️ Fuori pista statico (2026-09-10):** il primo controllo produzione non
> ha eseguito test. Python compila, ma Ruff segnala C901 sul nuovo orchestratore
> YOC e Black richiede formattazione di schema/servizio; il refactor e la
> formattazione restano H-owned. Il check Prettier non e' partito: `node_modules`
> manca e `prettier-plugin-svelte` non e' risolvibile. Nessun file frontend e'
> stato formattato; richiesto al coordinator l'eventuale `npm ci` consentito.

> **Note implementazione** (H03, 2026-09-10): aggiunti status/reason/provenance
> strict e campo holding inizialmente opzionale, poi reso required dal
> rifinimento 2026-09-11; il calcolatore bulk usa solo gross
> DIVIDEND/INTEREST asset-linked, age della coppia, conversioni FX con rate date
> reale e nessun fallback parziale. Import applicativi verificati.

> **Note implementazione** (H04, 2026-09-10): estratta la seam pura pubblica
> `eligible_income_quantity`, riusata dal FIFO esistente e da YOC. Il replay
> carica anche la controparte transfer fuori scope, conserva D-1/source transit,
> normalizza split same-day/successivi e propaga reason fail-closed nel summary.

> **Note implementazione** (H05, 2026-09-10): la L2 globale invoca direttamente
> `compute_portfolio_fx_cache_identity` prima del cache lookup per ogni report e
> aggiunge `compute_yield_on_cost_dependency_identity` per ledger cross-broker,
> transfer esterni, shorting e split material-field che il `tx_fp` dello scope
> non vede. Nessun wrapper/hash FX alternativo e nessuna modifica a
> `portfolio_engine.py`.

> **Note implementazione** (H07 parziale, 2026-09-10): aggiunta cella YOC
> accessibile e colonna default-visible accanto ad Annualized, con sorting
> zero/null e Tooltip senza icona per available/no-income, icona info soltanto
> per unavailable. Component test ancora in ownership test-author.

> **⚠️ Fuori pista frontend** (2026-09-10): il check Prettier diretto iniziale
> ha fallito prima della formattazione per `node_modules` assente. Dopo
> autorizzazione coordinator e un unico `npm --prefix frontend ci` dal lock,
> Prettier repo-installed ha formattato/verificato i due file H. Nessun
> `npm audit fix`, update o modifica package/lock.

> **⚠️ Fuori pista API gate** (2026-09-10): il comando
> `PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py test
> --test-port 6156 --data-dir /tmp/librefolio-r2-h-yoc --fresh-run api
> portfolio yield_on_cost` e' fallito **prima della collection**: shared backend
> exited during startup con code 1. Il runner ha creato/archiviato soltanto
> artifact TEST nella lane; nessun test prodotto e' partito e la porta 6156 e'
> stata verificata libera. Il runner non ha conservato stderr fuori dal suo
> output; richiesto al coordinator un singolo avvio diagnostico autorizzato,
> senza installazioni o workaround. **Risolto il 2026-09-10** dal bootstrap
> canonico MathJax autorizzato e dal retry API verde registrato sotto.

> **⚠️ Fuori pista diagnostica/API** (2026-09-10): l'avvio foreground
> autorizzato, log completo `/tmp/libreFolio_h_server_diag.log`, ha confermato
> una causa infrastrutturale pre-server: MathJax ignorato assente e download
> Python fallito per `CERTIFICATE_VERIFY_FAILED`; frontend build abortita,
> backend mai avviato, porta 6156 libera. Nessun test raccolto e nessun dato
> prodotto toccato. **Risolto il 2026-09-10** dopo disattivazione VPN: download
> HTTPS/TLS verificato senza bypass dei certificati.

> **⚠️ Fuori pista component gate** (2026-09-10): il primo component-unit ha
> raccolto zero test H; 39 suite sono fallite in import per assenza del file
> coordinator-owned `$lib/api/generated`, 26 suite/650 test sono rimasti
> skipped. Non e' un red prodotto. `npm ci` era gia' riuscito dal lock; nessun
> audit fix/update. Il bootstrap MathJax e' ora risolto; API sync/client
> coordinator-owned resta l'unico prerequisito condiviso prima del retry.

> **⚠️ Fuori pista component gate 2** (2026-09-10): dopo la materializzazione
> del client generato, il runner ha raccolto i quattro test H ma tutti sono
> falliti nel `beforeEach`, prima del render, per
> `TypeError: Cannot read properties of undefined (reading 'clear')` su
> `localStorage.clear()`. Vitest/Node ha segnalato che localStorage non e'
> disponibile senza `--localstorage-file`; 64 suite/1748 test non selezionati
> sono rimasti skipped. Il prodotto non e' stato esercitato: correzione fixture
> restituita al `test-author`, senza workaround runner da H. **Risolto il
> 2026-09-10** con lo storage stub module-local canonico: retry **4 passed,
> 1748 skipped**.

> **Note implementazione** (H08, 2026-09-10): docs-writer ha creato la teoria
> YOC e aggiornato gli indici EN, Dashboard Positions e Broker Positions.
> Formula transaction-ledger, age solo no-income, split cross-broker
> fail-closed, FX provenance e confronti metrici sono allineati al codice.
> MkDocs strict build e link check 12/12 verdi; nav esatta consegnata al
> coordinator, nessuna traduzione avviata.

> **⚠️ Fuori pista review produzione** (2026-09-10): review read-only ha
> trovato un `yieldOnCost` dichiarato per errore fuori dal row mapper
> (ReferenceError della tabella), denominator guard applicata solo al WAC
> nativo e fallback i18n header inefficace sui key mancanti. Corretti spostando
> la normalizzazione nel mapper, validando anche il WAC convertito e usando il
> confronto `translated === key`. La review ha inoltre confermato D-1, split,
> transfer, sorting null-last, default visibility e DTO status/value.

> **⚠️ Fuori pista review 2** (2026-09-10): review finale ha rilevato due
> interazioni cross-broker non visibili nei casi semplici: lo stesso AssetEvent
> SPLIT poteva scalare due volte un fragment in transit tramite le righe source
> e destination; inoltre un errore broker-locale invalidava tutto l'asset.
> Il replay YOC passa ora l'identita' evento al FIFO, che applica ogni corporate
> event una sola volta per fragment, e viene eseguito per componente di broker
> connessa da transfer. Errori/split invalidi restano fail-closed soltanto nelle
> posizioni connesse. Aggiunta anche la guardia sul WAC convertito non positivo.
> Due rilievi non richiedono codice: l'age minima e' deliberatamente limitata
> al caso senza income (decisione developer), mentre `ExposureTable` disabilita
> i number filter; la route help viene creata da H08 prima del gate UI.

> **⚠️ Fuori pista review 3** (2026-09-10): la review read-only conclusiva ha
> rilevato due incoerenze reali. La L2 usava `None` nella chiave per un report
> senza `date_to`, pur calcolando con `today`, e poteva quindi attraversare la
> mezzanotte con una entry del giorno precedente. Ora una sola
> `effective_date_to` entra in chiave e in tutti i consumer del report. Inoltre
> numerator YOC/FIFO era ratio-driven mentre il WAC portfolio e' guidato dalla
> quantita' della ADJUSTMENT split-linked: il replay espone ora snapshot passivi
> pre-evento per scope/custody e H verifica la coerenza
> `delta = quantity * (ratio - 1)`, con tolleranza Decimal e supporto alle righe
> duplicate source/destination durante transit. Mismatch e ratio editato
> falliscono `invalid_split` soltanto nella componente transfer connessa.
> L'ipotesi che un orphan income debba invalidare tutte le coppie connesse e'
> stata respinta: il contratto approvato rende unavailable l'intera singola
> posizione `(asset, broker)`, mentre soltanto replay/split sono
> component-scoped.

> **⚠️ Fuori pista review 4** (2026-09-10): il pass di verifica dei fix ha
> individuato due collisioni residue. La chiave L2 conserva ora sia
> `requested date_to` sia `effective_date_to`, evitando collisioni fra richiesta
> implicita ed esplicita dello stesso giorno; la tolleranza split viene
> calcolata separatamente per ciascun candidato scope/custody, cosi' uno scope
> enorme non maschera un delta custody incoerente. I tre witness dedicati hanno
> completato **3 passed, 361 deselected**. Il successivo pass read-only non ha
> rilevato finding ad alta confidenza.

> **Note implementazione** (H02/H07, 2026-09-10): test-author ha consegnato
> 36 regressioni fra nuovo oracle YOC, seam FIFO, integrazione service/L2,
> serializzazione API e `ExposureTable`. Coperti anche split globale su fragment
> in transit applicato una volta, isolamento per componente broker, giovane con
> income valido e WAC convertito non positivo. Nessun test e' stato eseguito
> dallo specialist; la lane resta di H per H09.

> **Note verifica** (H09 backend mirato, 2026-09-10): comando lane
> `PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py test
> --test-port 6156 --data-dir /tmp/librefolio-r2-h-yoc --fresh-run services
> roi-fifo-utils <selettori YOC>` completato con **36 passed,
> 321 deselected**. Copre oracle YOC, D-1, transfer, split deduplicato,
> isolamento componenti broker, FX/WAC, status e identita' L2. H09 resta
> aperto per API, component, type/build e regressioni integrate.

> **Note verifica** (H09 backend integrato/API, 2026-09-10): dopo le correzioni
> review 3/4, i witness mirati split/cache hanno completato prima **6 passed,
> 356 deselected**, poi **3 passed, 361 deselected**. La suite condivisa
> ROI/FIFO/portfolio finale ha completato **364 passed in 3.87s**. Dopo bootstrap
> canonico di `mathjax@3/es5/tex-mml-chtml.js` con `curl --fail --location`,
> protocollo e redirect HTTPS-only e TLS 1.2, il backend condiviso si e'
> avviato sulla lane 6156. L'unico retry autorizzato
> `dev.py test --test-port 6156 --data-dir /tmp/librefolio-r2-h-yoc
> --fresh-run api portfolio yield_on_cost` ha completato infine **1 passed,
> 23 deselected in 1.90s**. Log API completo:
> `.testLog/api__Portfolio-API-tests.log`.

> **Note verifica** (H09 frontend, 2026-09-10): il component-unit filtrato
> `ExposureTable.*(YOC|Yield on Cost)` ha completato **4 passed,
> 1748 skipped** dopo la correzione fixture specialist-owned. `front check` ha
> completato con **0 errori** e 41 warning preesistenti in due file fuori scope;
> il build produzione ha completato con successo, incluso client API ignorato
> generato automaticamente dal workflow. Prettier e' verde sui tre file H.
> H09 e' completo; la persistenza dei cataloghi/client/nav resta H06
> coordinator-owned e non produce delta H.

> **Note verifica** (H10 walkthrough tecnico, 2026-09-10): server test avviato
> nella lane isolata 6156 con mock data. Dashboard e Broker Positions mostrano
> YOC visibile accanto ad Annualized; valori `0.05%`/`0.36%`, dash unavailable,
> icona info e tooltip accessibile includono reason, first pair date e actual FX
> rate date. Nascondere YOC nel broker lo nasconde anche nel Dashboard tramite
> la chiave condivisa; riabilitarlo lo ripristina. La route help apre la nuova
> pagina teoria YOC. Un probe Playwright headless a `430x932` ha confermato
> entrambe le route mobile, nessun overflow documento, header YOC unico, valori
> e info control accessibili con aria-label completo. Un secondo probe ha
> aperto il Tooltip da tastiera con `Enter` e lo ha mantenuto visibile in dark
> mode. Server arrestato e porta 6156 verificata libera. Resta soltanto il
> feedback developer sul build integrato.

> **Note checkpoint** (H11, 2026-09-10): H e' frozen su baseline
> `b22998f` con 16 file modificati e 4 nuovi, nessuna superficie vietata,
> nessun file generated/catalog/nav/CHANGELOG e nessuna Git mutation.
> `git diff --check` e' verde; Black/Ruff/py_compile, API, suite
> ROI/FIFO/portfolio, component-unit, Svelte check, build, docs strict/link e
> walkthrough desktop/mobile sono verdi. Il client OpenAPI ignorato generato
> dal workflow contiene il DTO YOC e ha consentito i gate locali, ma il delta
> persistente resta coordinator-owned. Manifest, chiavi i18n e nav sono stati
> consegnati al coordinator; porta 6156 libera.

> **Note rifinimento contratto** (2026-09-11): il developer ha confermato che
> `DIVIDEND`/`INTEREST` non hanno semantica signed negativa e che non esiste una
> release pubblica con tale comportamento. Avviato il rifinimento: rimossi
> negativo available e fallback service per YOC assente; ogni
> `PortfolioHolding` richiede ora un risultato YOC typed. Un successivo probe ha
> confermato zero come input valido, mantenuto tramite `net_zero`.
> Il server manual-review sulla lane 6156 e' stato arrestato prima degli edit.
>
> **⚠️ Fuori pista rifinimento** (2026-09-11): il primo Ruff statico ha
> segnalato soltanto C901 sul validator DTO dopo il rafforzamento delle
> invarianti. Le verifiche `available`, `no_income` e `unavailable` sono state
> estratte in helper puri senza cambiare il contratto.
>
> **Note implementazione rifinimento backend** (2026-09-11): `available`
> richiede ora valore e reddito unitario non negativi; `net_zero` distingue uno
> o piu' income registrati a importo zero dal vero `no_income`. Il supporto
> signed negativo resta rimosso e ogni holding richiede un
> risultato YOC non nullo. `PortfolioService` indicizza direttamente il
> risultato per ogni posizione aperta. Black, Ruff e py_compile sono verdi;
> nessuna modifica a `portfolio_engine.py`, FIFO o schema DB.
>
> **Note implementazione rifinimento frontend** (2026-09-11): rimossi il
> rendering legacy e i rami speciali per valori negativi; risultato/provenance sono
> richiesti. I Tooltip usano copy breve, date localizzate, helper importo con
> decimali non significativi rimossi e metadata valuta con bandiere. La colonna
> YOC usa la nuova modalita' header opt-in: click/tap mostra il Tooltip, doppio
> click desktop e long press mobile da 500 ms aprono la guida; gli altri header
> conservano il link diretto. Prettier e' verde sui quattro file produzione.
>
> **Note documentazione rifinimento** (2026-09-11): docs-writer ha corretto i
> tre file EN interessati al contratto non-negativo, rimuovendo signed income e
> negative YOC. D-1, broker, transfer, split e FX restano
> rigorosi. MkDocs strict build e link check sono verdi; il debito traduzioni
> resta intenzionalmente rinviato.
>
> **Note verifica rifinimento backend** (2026-09-11): il contratto transazioni
> esistente e' confermato da **73 passed** nello schema suite; la regressione
> ROI/FIFO/portfolio aggiornata ha completato **375 passed in 3.35s**, inclusi
> DTO strict e YOC required. Il conteggio precede il ripristino di `net_zero`
> per income zero e verra' rieseguito.
> Le fixture `PortfolioHolding` usate da AI Export sono state riallineate senza
> modificare output o composizione: la suite service AI Export ha completato
> **922 passed in 246.57s**. Il gate API YOC ha completato **1 passed,
> 23 deselected in 1.87s** e conferma campo required/non-null. Questo primo
> conteggio precede la decisione developer di mantenere `net_zero` per income
> registrati a zero e verra' rieseguito.
>
> **⚠️ Fuori pista component rifinimento** (2026-09-11): la prima invocation
> combinata ha confermato **5 test YOC verdi**, ma i 10 test header sono
> falliti tutti nel `beforeEach` prima del render per `localStorage.clear()`
> non disponibile nel processo Node. Causa identica alla precedente fixture
> ExposureTable e non red prodotto; riparazione restituita al `test-author`
> tramite storage stub module-local.
>
> **⚠️ Fuori pista contratto zero** (2026-09-11): la review finale e un probe
> diretto hanno mostrato che il validator transazioni accetta esplicitamente
> `DIVIDEND/INTEREST cash=0`, perche' il controllo segno salta gli importi zero.
> Su decisione developer, `net_zero` e il rendering `0.00%` restano quindi per
> income registrati a zero; soltanto importi negativi e storni signed sono
> rimossi.
>
> **⚠️ Fuori pista review rifinimento** (2026-09-11): la review ha inoltre
> evidenziato provenance FX potenzialmente ripetuta/lunga e assenza di un gesto
> tastiera per aprire la guida. Le righe FX sono ora deduplicate per
> coppia/rate-date e limitate a tre con contatore `… (+N)`; `Shift+Enter`
> apre la guida senza cambiare Enter/Space, click/tap, doppio click o long press.
> La verifica conclusiva ha inoltre corretto il testo `missing_fx`: la
> conversione assente puo' riguardare un income oppure il PMC a T, quindi il
> Tooltip parla neutralmente di cambio richiesto dal calcolo alla data indicata,
> senza inventare un pagamento.
>
> **⚠️ Fuori pista sorting zero** (2026-09-11): il gate component aggiornato ha
> completato 17 test e ne ha fallito uno perche' il test imponeva un ordine
> relativo fra `no_income` e `available net_zero`, entrambi con sort value zero.
> Il prodotto ha mantenuto correttamente i due zeri prima dei positivi e i null
> unavailable in fondo; la correzione specialist-owned rimuove soltanto
> l'assunzione sull'ordine del pareggio.
>
> **⚠️ Fuori pista type-check rifinimento** (2026-09-11): il primo
> `front check` ha trovato un solo errore: il client Zodios mantiene unioni
> array/optional sui campi interni di `YieldOnCostResult`, pur avendo correttamente
> reso `yield_on_cost` outer required e non nullo. Il mirror raw di
> `ExposureTable` e' stato allineato alle sole unioni generate; il risultato
> outer resta obbligatorio e il renderer legacy non e' stato ripristinato.
>
> **Note verifica rifinimento frontend/shared** (2026-09-11): dopo lo stub
> `localStorage` specialist-owned, i test YOC + DataTable header hanno completato
> **15 passed, 1745 skipped**. `front check` e build produzione sono verdi con
> **0 errori** e 41 warning preesistenti fuori scope. L'audit i18n e' verde con
> **2587/2587** chiavi per EN/IT/FR/ES, zero missing e zero backend keys; API
> sync conferma YOC required/non-null; il sync verra' rieseguito dopo il
> ripristino di `net_zero`.

> **Note EOD freeze** (2026-09-11): completati contratto backend non-negativo,
> YOC holding required, UI/gesture, sync API, cataloghi EN/IT/FR/ES, docs EN e
> gate eseguiti prima del freeze: schema transazioni **75 passed**,
> ROI/FIFO/portfolio **384 passed**, API YOC **1 passed / 23 deselected**,
> AI Export **922 passed**, component YOC/header **18 passed / 1745 skipped**,
> `front check` e build verdi, i18n **2587/2587** per lingua, MkDocs strict e
> link **12/12**. La review read-only finale si e' conclusa senza finding
> significativi. Nessun nuovo gate o server verra' avviato; porta 6156
> verificata libera.
>
> **Note resume/manual review** (2026-09-11): dopo resume coordinator, la review
> finale e' stata ripetuta senza finding. Ricostruite e verificate cinque
> fixture reali: positive 10% con FX fallback, mature no-income, recorded-zero
> `0.00%`, insufficient-history e missing-FX. Server test avviato con
> `--no-scheduler --no-reload` sulla porta 6156, HTTP 200, PID 97650.
>
> **Note accettazione developer** (2026-09-11): walkthrough completato; il
> developer ha dichiarato `testato, mi pare perfetto, non vedo altro, hai il
> mio ok`. Server H arrestato dopo l'accettazione; checkpoint congelato senza
> staging, commit o integrazione.

Dopo ogni step implementativo autorizzato:

1. aggiornare subito questa tabella;
2. aggiungere `Note implementazione` con evidenza e revisione;
3. aggiungere `Fuori pista` per ogni detour/failure;
4. registrare comando esatto e risultato;
5. non avanzare allo step dipendente se il gate e' rosso.

## 10. Test strategy e risultati

Tutti i nuovi test passano da `test-author`. Nessun test usa posizione fissa,
conteggio globale, clock wait, rete terza o testo tradotto.

### 10.1 Backend

| Famiglia | Casi minimi |
|---|---|
| Finestra | T-364 e T inclusi; T-365 escluso; `date_from` largo/stretto uguale. |
| Age | first pair tx su T-364 -> no_income 0; giorno successivo -> insufficient; close/rebuy non resetta. |
| D-1 | same-day BUY escluso; SELL incluso; buy+sell D escluso. |
| Broker | due broker stesso asset, income/WAC separati; scope Dashboard/Broker coerente. |
| Transfer | source in-transit eleggibile; destination pre-arrival orphan; post-arrival eleggibile; niente carry. |
| Quantita' | vendite parziali e buy successivi non deformano payout storici. |
| Split | same-day, forward, reverse; ratio invalido/missing/incoerente fail-closed. |
| Income | DIVIDEND + INTEREST lordi non negativi; TAX/FEE ignorati; assetless ignorato; zero registrato distinto da no-income. |
| FX | identity, same-day, backward-resolved con rate date reale, missing; WAC FX a T. |
| Base | WAC null/zero/negativo; holding chiusa non produce riga. |
| Cache | L2 usa la string identity F per tutti i report; i witness F includono `cost_basis_currency`; rate/route/split changes miss; identical input hit; no stale fallback. |
| DTO | matrice status/value/reason/provenance; outer field required e non nullo. |

### 10.2 Frontend

- colonna visibile di default e accanto ad Annualized;
- override hide/show persistente e condiviso Dashboard/Broker;
- available positivo oppure `0.00%` con income zero registrato;
- no-income `-` senza icona problema;
- unavailable `- [i]` con reason e FX rate date;
- null sort last; zero resta zero;
- header tooltip + link teoria;
- custom Tooltip desktop/mobile/tastiera;
- campo DTO assente nella fixture legacy non rompe il render.

### 10.3 Selettori/comandi eseguiti

Eseguiti dopo autorizzazione nella lane assegnata:

```bash
PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc \
  pipenv run python dev.py test \
  --test-port 6156 \
  --data-dir /tmp/librefolio-r2-h-yoc \
  services roi-fifo-utils yield_on_cost
```

```bash
PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc \
  pipenv run python dev.py test \
  --test-port 6156 \
  --data-dir /tmp/librefolio-r2-h-yoc \
  api portfolio yield_on_cost
```

```bash
PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc \
  pipenv run python dev.py test \
  --test-port 6156 \
  --data-dir /tmp/librefolio-r2-h-yoc \
  front-utility component-unit "ExposureTable.*(YOC|Yield on Cost)"
```

Eventuale E2E condivisa, soltanto dopo approvazione storyboard:

```bash
PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc \
  pipenv run python dev.py test \
  --test-port 6156 \
  --data-dir /tmp/librefolio-r2-h-yoc \
  front-portfolio dashboard "Yield on Cost"
```

Non modificare `frontend/e2e/dashboard-report.json`: e' una fixture reale. Se
una futura shape required la invalida, serve nuova cattura developer; il campo
outer opzionale evita questa rottura.

## 11. Documentazione, i18n e generated ownership

`docs-writer` aggiorna soltanto English:

- nuovo
  `mkdocs_src/docs/financial-theory/technical-analysis/performance-metrics/portfolio-engine/yield-on-cost.en.md`;
- `.../portfolio-engine/index.en.md`;
- `.../performance-metrics/index.en.md`;
- `mkdocs_src/docs/user/dashboard/positions.en.md`;
- `mkdocs_src/docs/user/brokers/index.en.md` solo se serve chiarire lo scope
  identico.

Contenuti minimi:

- formula transaction-ledger, lordo e D-1;
- age della coppia e close/rebuy;
- split, transfer e FX rate date;
- differenza da dividend yield, cash yield, total income/current cost basis e
  CAGR;
- status e significato di percentuale positiva, `-`, info problem.

Coordinator:

- aggiunge chiavi UI EN/IT/FR/ES;
- esegue API sync/client generation;
- integra MkDocs nav;
- aggiorna CHANGELOG e master records dopo implementazione reale;
- gestisce eventuale runner registration.

Nessuna traduzione MkDocs automatica senza richiesta esplicita.

## 12. Definition of done

Backend:

- formula per income/unit e finestra esatta;
- age della coppia stabile attraverso close/rebuy;
- D-1 e transfer identici al FIFO canonico;
- split current-unit coerente col WAC;
- income lordo, TAX/FEE/provider/assetless esclusi;
- FX backward-resolved con rate date reale;
- nessuna somma parziale o fallback;
- DTO strict con YOC required e non nullo;
- L2 globale riusa l'identita' F esatta;
- nessun cambiamento H a `portfolio_engine.py` o DB schema.

Frontend:

- YOC visibile di default accanto ad Annualized su Dashboard e Broker;
- preference hide/show shared, user-scoped e persistente;
- 2 decimali, nessun `+`;
- no-income normale senza error affordance;
- unavailable con custom info Tooltip accessibile;
- sorting zero/null corretto;
- loading/empty/dark/mobile invariati.

Qualita' e consegna:

- test mirati e punti condivisi verdi nella lane H;
- API client/i18n/docs/nav integrati dai rispettivi owner;
- storyboard approvato prima del codice UI;
- walkthrough operativo developer completato dopo integrazione;
- piano aggiornato step-by-step con note/detour;
- nessun artifact runtime/private/generated fuori contratto;
- porta 6156 libera al checkpoint;
- commit/merge/staging ordinario eseguiti solo dal developer/coordinator.

## 13. Runbook review UI

Con H09 verde, eseguire e consegnare una revisione su build/revisione esatta:

1. Dashboard -> Positions -> Holdings: vedere YOC gia' visibile.
2. Ordinare YOC; verificare percentuali, no-income e unavailable.
3. Aprire Tooltip di insufficient history, orphan/replay e missing FX.
4. Verificare la actual FX rate date nella provenance/help.
5. Nascondere YOC dall'occhio; aprire Broker -> Positions e verificare che sia
   nascosto; riabilitare e tornare Dashboard.
6. Ripetere viewport mobile, tastiera, light/dark.
7. Aprire la teoria YOC dal help header.

Feedback:

| ID | Revisione | Viewport/stato | Azione | Atteso | Osservato | Decisione |
|---|---|---|---|---|---|---|
| H-UI-001 | `b22998f` + H dirty | Desktop Dashboard | YOC default | visibile | Visibile dopo Annualized; valori e unavailable distinti | technical pass |
| H-UI-002 | `b22998f` + H dirty | Mobile Dashboard/Broker `430x932` | Tooltip unavailable | accessibile/pinnable | No document overflow; Enter apre Tooltip, aria-label completo, dark mode stabile | technical pass |
| H-UI-003 | `b22998f` + H dirty | Dashboard -> Broker -> Dashboard | hide override | condiviso | Hide broker propagato al Dashboard; re-enable propagato | technical pass |

## 14. Stato handoff del piano

Il piano/storyboard e Gate 0 sono approvati; l'esecuzione H e' stata
esplicitamente autorizzata il 2026-09-10 sulla baseline `b22998f`. Il
rifinimento richiesto dal developer e' implementato e i gate automatici sono
verdi. API sync, cataloghi EN/IT/FR/ES, MkDocs nav e CHANGELOG coordinator-owned
sono presenti nel worktree. Il developer ha accettato il build raffinato dopo
review delle cinque fixture reali. H e' frozen; restano coordinator/developer:
staging selettivo, commit manuale, integrazione e aggiornamento dei record
release finali.
