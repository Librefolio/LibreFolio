# H - Yield on Cost da ledger transazioni (U3 / primo incremento SP06)

**Stato:** ✅ **PLAN/DESIGN APPROVED 2026-09-10**; implementazione FROZEN e
non autorizzata.
**Owner:** workstream H.
**Baseline di analisi:** `f90d9801bd7a2d74aac6a27efe305314c6c004cc`
su `dev_release2`.
**Branch di piano:** `e-alfy-h-yield-on-cost`.
**Target di integrazione futuro:** `dev_release2`, dopo checkpoint/integration
del workstream F e nuova autorizzazione esplicita.
**Lane futura:** porta `6156`, data root assoluta
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

- \(A_i\) e' l'importo lordo **signed** registrato dalla transaction income;
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
5. Nessun `abs()` sugli income: eventuali storni legacy negativi riducono
   algebricamente il numeratore.
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

L'implementazione potra':

1. estrarre un helper puro/pubblico minimo dall'attuale eligibility FIFO; oppure
2. leggere il risultato del replay FIFO e i suoi gruppi di allocazione.

La scelta deve conservare un solo algoritmo D-1/transfer-aware e non introdurre
una terza nozione di quantita'.

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
| Income validi e somma diversa da zero | `available` | frazione signed | `4.27%` / `-0.35%` |
| Income e storni esistono ma si compensano | `available` + provenance `net_zero` | `0` | `0.00%` |
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

Estendere `PortfolioHolding` con un campo additive/backward-compatible:

```text
yield_on_cost?: YieldOnCostResult
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

- `available` -> value non-null; reason null;
- `no_income` -> value esattamente zero; reason null;
- `unavailable` -> value null; reason obbligatoria;
- `net_zero=true` soltanto per `available` value zero con transaction count > 0;
- nessun `not_applicable`;
- reason enum stabile, mai testo libero.

## 6. FX e cache portfolio

### 6.1 Dipendenza bloccante F

F ha preparato, ma non ancora integrato sulla baseline H:

```python
async def compute_portfolio_fx_cache_identity(
    db,
    scope_broker_ids: set[int],
    target_currency: str,
    date_to: date,
) -> str:
    ...
```

Contratto atteso:

- un solo SHA-256 deterministico sul payload bounded delle dipendenze FX;
- `FxRate` selezionati rilevanti;
- persisted custom `FXConversionRoute` rilevanti;
- stringa identity inclusa nella cache L1;
- mutation/delete FX mancanti invalidano L1/L2.

Prima dell'implementazione H:

1. ricevere SHA/checkpoint F integrato;
2. riallineare la baseline tramite operazione developer;
3. leggere firma e test reali;
4. riusare la helper senza wrapper o seconda query/fingerprint divergente.

### 6.2 L2 generale

`PortfolioService.get_report()` deve invocare la stessa
`compute_portfolio_fx_cache_identity(...)` e includere la stringa restituita
nella chiave L2 per **tutti** i report portfolio, anche quando
`include_summary=false`.

Regole:

- nessun fingerprint YOC-only;
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

## 7. Superfici e ownership

### 7.1 File H previsti

| Area | File |
|---|---|
| Calcolo | nuovo `backend/app/services/yield_on_cost.py` |
| Orchestrazione/L2 | `backend/app/services/portfolio_service.py` |
| DTO | `backend/app/schemas/portfolio.py` |
| FIFO helper, solo se necessario | `backend/app/services/fifo_lot_engine.py` |
| Test pure/service | nuovo `backend/test_scripts/test_services/test_financial/test_yield_on_cost.py` |
| Test cache/report | `backend/test_scripts/test_services/test_financial/test_portfolio_service.py` |
| Test API | `backend/test_scripts/test_api/test_portfolio_api.py` |
| UI | `frontend/src/lib/components/dashboard/ExposureTable.svelte` |
| Component test | `frontend/src/lib/components/dashboard/ExposureTable.test.ts` |
| User/theory docs EN | file elencati nella sezione 10 |

### 7.2 File esclusi o condivisi

- F resta owner di `backend/app/services/portfolio_engine.py`.
- H non modifica `backend/app/services/asset_source.py`, provider,
  `backend/app/schemas/assets.py` o pagine Asset.
- Coordinator: `CHANGELOG.md`, quattro cataloghi i18n, API sync/client
  generato, runner registration, MkDocs nav e master backlog.
- Test nuovi/riparati: `test-author` dopo autorizzazione implementativa.
- MkDocs EN: `docs-writer` dopo autorizzazione implementativa.

## 8. Storyboard ASCII - gate G-UX-DESIGN

**Storyboard v1 APPROVED dal developer il 2026-09-10.** L'approvazione copre
solo piano e design; nessuna UI puo' iniziare finche' F non e' integrato, H non
e' riallineato e manca una separata autorizzazione esecutiva.

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
| H01 | Integrare baseline F e caratterizzare helper FX/cache condivisa | ⛔ BLOCKED - attende checkpoint F + autorizzazione implementativa |
| H02 | Test-author: oracle e casi replay/formula/cache prima del wiring | ⏳ PENDING |
| H03 | DTO typed + calcolatore YOC transaction-ledger | ⏳ PENDING |
| H04 | D-1/transfer/split replay e integrazione summary | ⏳ PENDING |
| H05 | Shared FX identity nella L2 generale + dipendenze YOC | ⏳ PENDING |
| H06 | API contract/client e i18n tramite coordinator | ⏳ PENDING |
| H07 | ExposureTable + component test secondo storyboard approvato | ⏳ PENDING |
| H08 | Docs EN tramite docs-writer + nav coordinator | ⏳ PENDING |
| H09 | Gate mirati/integrati nella lane H | ⏳ PENDING |
| H10 | Walkthrough Dashboard/Broker e feedback developer | ⏳ PENDING |
| H11 | Checkpoint finale, integrazione e chiusura documentale | ⏳ PENDING |

> **Note implementazione** (H00, 2026-09-10): creati esclusivamente piano e
> storyboard, con backlink U3/SP06 ora marcati PLAN/DESIGN APPROVED. Nessun file applicativo,
> test, schema runtime, i18n, generated client o migration e' stato modificato.
> L'implementazione resta bloccata sia dall'integrazione del checkpoint F sia
> da una nuova autorizzazione esplicita. Il developer ha approvato coerenza del
> piano e storyboard v1 il 2026-09-10; questa e' approvazione PLAN/DESIGN, non
> autorizzazione a eseguire H01-H11.

Dopo ogni step implementativo autorizzato:

1. aggiornare subito questa tabella;
2. aggiungere `Note implementazione` con evidenza e revisione;
3. aggiungere `Fuori pista` per ogni detour/failure;
4. registrare comando esatto e risultato;
5. non avanzare allo step dipendente se il gate e' rosso.

## 10. Test strategy futura

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
| Income | DIVIDEND + INTEREST lordi; TAX/FEE ignorati; assetless ignorato; legacy signed; net-zero. |
| FX | identity, same-day, backward-resolved con rate date reale, missing; WAC FX a T. |
| Base | WAC null/zero/negativo; holding chiusa non produce riga. |
| Cache | L2 usa la string identity F per tutti i report; rate/route/split changes miss; identical input hit; no stale fallback. |
| DTO | matrice status/value/reason/provenance; outer field backward-compatible. |

### 10.2 Frontend

- colonna visibile di default e accanto ad Annualized;
- override hide/show persistente e condiviso Dashboard/Broker;
- available positivo/negativo/net-zero;
- no-income `-` senza icona problema;
- unavailable `- [i]` con reason e FX rate date;
- null sort last; zero resta zero;
- header tooltip + link teoria;
- custom Tooltip desktop/mobile/tastiera;
- campo DTO assente nella fixture legacy non rompe il render.

### 10.3 Selettori/comandi futuri

Solo dopo autorizzazione e nella lane assegnata:

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
- status e significato di percentuale, `0.00%`, `-`, info problem.

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
- DTO strict e backward-compatible;
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

## 13. Runbook review UI futuro

Quando H09 e' verde, consegnare una revisione su build/revisione esatta:

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
| H-UI-001 | da compilare | Desktop Dashboard | YOC default | visibile | - | pending |
| H-UI-002 | da compilare | Mobile Broker | Tooltip unavailable | accessibile/pinnable | - | pending |
| H-UI-003 | da compilare | Dashboard -> Broker | hide override | condiviso | - | pending |

## 14. Stato handoff del piano

Il piano e lo storyboard v1 sono **PLAN/DESIGN APPROVED 2026-09-10**.
L'implementazione resta FROZEN finche':

1. F consegna e il developer integra la shared FX identity/helper con relativi
   test cache;
2. H viene riallineato alla nuova baseline;
3. coordinator/developer autorizzano esplicitamente l'esecuzione di questo
   piano.

L'approvazione plan/design non autorizza codice, specialisti, test o runtime.
