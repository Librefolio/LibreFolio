# Piano D — Compattazione del contratto PAC 1.0.0, prima dell'integrazione

**Stato:** ✅ chiuso il 2026-10-05. Committato in `ac18ce097` e `9e4140376`, unito con `dev_release2` in `68483ddda`, gate finali verdi (§12, S10). Il via era la decisione a) del coordinator, data dopo il checkpoint `946095d58`.
**Baseline:** `946095d58` su `e-alfy-allocatore-pac`, cioè `0900f11fa` fix(pac) più `946095d58` docs(journal).
Verificata il 2026-10-05 alle 10:30: albero pulito, stage vuoto, porte 6151 e 6161 libere.
**Posizione:** `LibreFolio_developer_journal/Release_2/Phase_0/13_pacAllocator/implementation/plan-phase00PacContractCompaction.prompt.md`
← Precedente: [`plan-phase00PacRound5PostMerge.prompt.md`](plan-phase00PacRound5PostMerge.prompt.md) (R14.8).
**Corsia:** suite `6151` + `/tmp/librefolio-r2-d`, un comando per volta. Nessun server di review.

Le righe citate sono misurate alla baseline. Se il codice cambia, prevale il codice.

---

## 0. Perché

Il developer, al round 14 (2026-10-04):

> «se accepted non serve, togliamolo, non sono sicuro di aver capito freshness, e rendere gli zeri
> opzionali non sarebbe male, per rendere il pacchetto più rapido. […] quando poi passeremo al server
> MCP IA, sarà più facile fare il pacchetto di richiesta IA e trasformarlo in questo, evitiamo cose
> che non servono ora che ancora esiste tutto solo su questa macchina.»

**Decisione a) del coordinator.** La slice si fa prima dell'integrazione. In `dev_release2` il
contratto `1.0.0` entra una volta sola, già compattato: così nessun fingerprint `1.0.0` pubblicato
cambia senza cambiare versione.
- La versione resta `1.0.0`: non è mai stata rilasciata.
- Il fingerprint cambia **una volta**, qui.

**Nota MCP**, registrata dal coordinator:
- il compute dipende solo dal pacchetto;
- la UI copia i dati dal dominio solo per comodità dell'utente;
- un chiamante esterno, come un'IA, potrà costruire il pacchetto da sé. Meno campi obbligatori
  significa meno valori da inventare.

## 1. La regola: wire compatto, richiesta risolta

- **Lo schema porta i default**, sempre con `Field(default=…)`.
  - Mai `default_factory`: non emette `default` nel JSON Schema, e il codec non lo vedrebbe.
  - Per i default mutabili non serve la factory: Pydantic copia il default per ogni istanza.
- **Il normalizer lavora sulla richiesta validata**, con i default già riempiti. Motore, evaluator,
  vincoli e oracolo non vedono differenze.
- **La UI spedisce il pacchetto compatto**: omette i valori uguali al default.
  - Le viste del risultato leggono la **richiesta risolta**, cioè l'output del codec (`z.output`), con
    i default riempiti.
  - La regola della piattaforma lo vuole già: si spedisce lo scenario originale del chiamante, mai
    l'output di validazione con i default riempiti (`developer/architecture/patterns/tool_plugins.en.md:197`, `:210`).
  - Il client di C la rispetta: valida col codec (`features/tools/client.ts:319-320`), ma spedisce il
    corpo originale (`:340`, `snapshot.body`). Il default si riempie solo nel processo figlio.
- **`AllocationStrictModel`** (`backend/app/schemas/pac_allocator.py:32-33`) prende
  `json_schema_serialization_defaults_required=True`.
  - In serializzazione ogni campo è sempre presente, perché il worker fa un `model_dump` senza
    `exclude_*` (`worker.py:154`).
  - Così il codec d'uscita resta «tutto obbligatorio».
  - Solo PAC usa questa base.
- **Stessi valori danno lo stesso scenario esatto**, quindi lo stesso `request_fingerprint`, sia in
  forma compatta sia in forma esplicita.
  - Il fingerprint è lo sha256 di `repr(scenario)`: `evaluator.py:174-178`, `planner_report.py:131-143`.

## 2. I campi

Tutte le righe di schema sono in `backend/app/schemas/pac_allocator.py`. Il normalizer è in
`backend/app/services/pac_allocator/normalize.py`, i modelli esatti in `…/models.py`, i codici in `…/issues.py`.

### 2.1 Tolti

| Campo | Schema | Motore | UI |
|---|---|---|---|
| `quote.freshness`: `fresh`, oppure `stale` con `age_days` e `accepted` | `:305-318`, `:362` | normalizer `freshness()` `:164-170`, chiamata `:250`, `build_freshness` `:796-799`, `:865`; models `FreshnessKind` `:30`, `ExactFreshness` `:153`, campo `:244` | `request.ts:259`, `:265`; `OrderDetail.svelte:67-69` |
| codici `allocation.stale_age_negative`, `allocation.stale_observation_not_accepted` | `:186-187` | `issues.py:96-97` | 2 chiavi i18n (§4) |
| `quote.reference_date` | `:361` | normalizer `:864`; models `:243` | `request.ts:264`; `OrderDetail.svelte:63-76` |
| codice **del planner** `allocation.price_date_missing` | `:174` | `issues.py:90`, normalizer `:244` | nessuna: la chiave i18n resta (§4) |
| `source_kind` della cassa (`local_broker_cash`/`manual_cash`) | `:463` | normalizer `:999`; models `:351` | `request.ts:317` |

**Restano:**
- le date del costo medio e delle ritenute (normalizer `:961`, `:981`);
- `as_of`;
- il `source_kind` delle funding route (`existing_cash`/`contribution`), che il motore usa.

### 2.2 Con un default

| Campo | Default |
|---|---|
| order route: `priority` | `0` |
| order route: `minimum_if_active`, `required_minimum` | `{"kind":"none"}` |
| order route: `cap` | `{"kind":"none"}` |
| order route: `execution_margin_rate` | `"0"` |
| funding route: `priority` | `0` |
| `fx_spread_rate` | `"0"` |
| `fx_rates` | `{}` |
| `existing_cash`, `contributions`, `funding_routes`, `capabilities` e `fee_schedules` del broker, `exposures` dell'asset, `holdings`, le 3 liste di `sell_context` | `[]` |
| commissione: `rate` | `"0"` |
| commissione: `variable_cap` | `{"kind":"none"}`, come istanza di `NoFeeCap` |

Le union discriminate prendono come default un'istanza del modello, non un dict. In strict mode il
default non viene validato, e un dict resterebbe un dict.

### 2.3 Facoltativi (`None` = assente)

| Campo | Cosa vuol dire l'assenza |
|---|---|
| funding `transfer_cap` (`:500`) | tutto il selezionato della fonte. Il normalizer riempie il valore esatto (`:471-478`, `:1024`; models `:385-393`) |
| `DomainCopyProvenance.source_label` (`:295`) | nessuna etichetta. Nell'output resta obbligatorio, ma nullable |
| `asset_class` di entrambe le identità (`:340`, `:348`) | classe non nota. `ExactAsset.asset_class` diventa `str \| None` (models `:259`); `PlannerCatalogAsset.asset_class` (`:1119`) diventa obbligatorio e nullable |
| commissione: `fixed_fee`, `variable_floor` (`:436`, `:438`) | zero (§3) |
| `fee_schedule_id` delle route **BUY**, `:559`, con override in `PlannerBuyOrderRouteInput` | commissione zero (§3) |

### 2.4 Restano obbligatori

- `operation`, `snapshot`, `as_of`, `valuation_currency`, `provenance`, `assets`, `brokers`,
  `order_routes`, `target_weights`, `policy`;
- l'oggetto `sell_context`;
- le etichette dei discriminatori;
- `fee_schedule_id` delle route SELL.

I pesi target a zero restano espliciti: ogni asset vuole un peso (`normalize.py:304`, `target_weight_missing`).

## 3. Commissioni: F1 esteso, motore invariato

**Wire**
- In `BrokerFeeScheduleInput`, `fixed_fee` e `variable_floor` diventano `PlannerMoneyInput | None = None`.
  Gli altri default: `rate = "0"`, `variable_cap = NoFeeCap(kind="none")`.
- La valuta di una tabella è quella comune ai suoi campi monetari presenti.
  - Due valute diverse danno `allocation.currency_mismatch`.
  - Una tabella senza campi monetari vale nella valuta di quotazione di ogni route che la usa.
- `fee_schedule_id` diventa facoltativo solo nelle route BUY.
  - L'override sta in `PlannerBuyOrderRouteInput`, che copre anche `PacOrderRouteInput`.
  - Nelle route SELL resta obbligatorio.
  - Un ID BUY che non porta a nessuna tabella dà ancora `allocation.fee_schedule_missing`.

**Normalizer (istanziazione)**

L'istanziazione gira solo nella fase di build, cioè con `availability == "ready"` (`:1086`). Lì ogni
route usata ha già una valuta di quotazione.

1. Una tabella con valuta tiene il suo ID.
2. Una tabella senza valuta produce un'istanza per ogni valuta di quotazione in cui viene usata.
   - L'ID dell'istanza è `{id}~{CUR}`.
   - Una tabella senza valuta che nessuna route usa non produce istanze.
3. Una route BUY senza tabella riceve un'istanza implicita a zero, con ID `~zero~{capability_id}~{CUR}`.
   - Il lato è sempre BUY, quindi l'ID è unico per broker.
4. Le route vengono riscritte sugli ID delle istanze.
5. Le istanze vengono ordinate per `(capability_id, side, id)`, come vuole `ExactBroker` (models `:323`).

Il carattere `~` non è ammesso in `_PLANNER_ID` (`backend/app/schemas/pac_allocator.py:48`):
nessuna collisione con gli ID del chiamante è possibile.

`fee_schedule_id` non compare nell'output. Le istanze restano interne allo scenario esatto, dove le
leggono:
- l'indice dell'evaluator (`evaluator.py:369`, `:408`, `:1893`);
- i vincoli (`constraints.py:203`, `:389`, `:613`).

**Validazione**
- Il controllo di valuta a livello di route (`normalize.py:548`) vale solo per le tabelle con valuta.
- `validate_fee_schedule` (`:361-379`) controlla l'insieme delle valute dei campi monetari presenti:
  `fixed_fee`, `variable_floor` e l'importo del tetto. Un insieme vuoto va bene.
- Un campo monetario assente vale zero nei controlli di segno e nel controllo minimo ≤ tetto.

**Effetto sul fingerprint**
- Stessi default danno lo stesso scenario, quindi lo stesso `request_fingerprint`.
- Una tabella a zero esplicita e una omessa danno ID di istanza diversi, quindi fingerprint diversi.
  Succede già oggi con due ID scelti diversamente dall'utente, ed è accettabile.
- Ordini, commissioni e obiettivo invece coincidono. Un test lo dimostra (§7, S1).

**Alternative scartate**
- **F2**, un `fee_schedule_id` esatto nullable: tocca evaluator, vincoli e oracolo.
- **`fixed_fee` obbligatorio** come portatore della valuta: lascia nel pacchetto proprio gli zeri che
  il developer vuole togliere.

## 4. Correzioni rispetto al via

1. **`source_label`** sta su `DomainCopyProvenance` (`pac_allocator.py:290-296`), non su
   `ManualProvenance`, che ha un `label` obbligatorio (`:284-287`).
2. **Le chiavi i18n da togliere sono 4, non 5.**
   - `allocation.price_date_missing` resta, perché lo emette ancora l'API allocation-source:
     - è nella `PortfolioPlannerSourceIssueCode` (`backend/app/schemas/portfolio.py:1612`);
     - viene emesso in `portfolio_allocation_source.py:885-895`;
     - la UI lo rende con la chiave dinamica di `issues.ts:138`.
   - È lo stesso schema seguito da `allocation.currency_spec_missing` (C0b.1, `test_pac_planner_schemas.py:1160-1163`).
   - Le 4 chiavi tolte, tutte sotto `tools.pacAllocator.` e presenti in en/it/fr/es:
     - `planner.issues.allocation.stale_age_negative`;
     - `planner.issues.allocation.stale_observation_not_accepted`;
     - `planner.result.detail.staleQuote`;
     - `planner.result.detail.priceDate`.
   - `assetEditor.priceDate` è un'altra chiave, e resta.

## 5. Fuori scope

- `snapshot_id`, exposures su richiesta, ID derivati, provenance implicita.
- `ticker`, `fiscal_currency`, il `side` della commissione, i pesi target a zero.
- L'API allocation-source, `source.ts`, `copies.ts`, `allocationSource.ts`.
- La staleness mostrata nella bozza (`referenceDate`, `AgeLabel`), che resta.
- `fx_cost`, voce del TODO del coordinator. Anche `provenance_stale_confirmed`.
- Le altre 113 chiavi i18n inutilizzate.
- La pagina MkDocs utente `user/tools/pac-allocator/index.en.md`. È vecchia («No interface yet»,
  `Backend/API 2.0.0 · UI 2.0.0`), ma la sua riscrittura è già rimandata da Round5PostMerge §4.7.
- `TODO_FUTURI.md` e `CHANGELOG.md`: sono del coordinator.

## 6. Conseguenze verificate

- **I pin del fingerprint** (`test_pac_planner_schemas.py:3410-3423`: PAC `bd84ef14…`, Rebalancer
  `0b43bd19…`) si aggiornano solo **dopo** l'implementazione (S4), con i valori misurati.
  - Nessun test fissa un `request_fingerprint` di produzione: le fixture usano `"fixture-…-not-a-production-hash"`.
- **È il primo `default` reale in un contratto Tool.**
  - Il codegen di C sembra pronto: `tools-codec-ast.mjs:120`, `:319`, `:344`; `tools-schema-document.mjs:321`
    toglie `default` in modalità serializzazione.
  - Lo verifico sul codec generato in S4.
  - Se il codegen non regge, mi fermo e lo segnalo: il codegen è di C.
- **Tipi TS** (`planner/types.ts`). I file generati non si toccano.
  - Restano `PacPlannerRequest` (wire, `z.input`) e i tipi `PacRequest*` del builder, come
    `NonNullable<…>[number]` dove la lista diventa facoltativa.
  - Si aggiunge `PacResolvedRequest = z.output<ToolContractMap['pac_allocator']['1.0.0']['input']>`,
    con `PacResolvedAsset`, `PacResolvedOrderRoute` e `PacResolvedFundingRoute`.
  - `ToolContractMap` è già esportato da `features/tools/contracts.ts:6`.
- **`BuiltRequest`** (`request.ts:35-41`) prende `resolved` = `parsed.data`.
  - `run.svelte.ts:65` continua a spedire `built.request`, cioè la forma compatta.
  - Passano a `resolved` le letture del risultato:
    - `ResultView.svelte:49`, `:113`;
    - `model.ts:9`, `:252-294` (`planLookup`, `requiredMinimumRoutes`);
    - `text.ts:12`, `:42-43`;
    - `StateNotice.svelte`.
- **`OrderDetail.svelte`**: la riga «Price date» (`:63-76`) sparisce, perché `quote.reference_date`
  non esiste più.
  - Il badge di origine del prezzo (`OriginBadge`, `:70-72`) si sposta nella riga «Source price» (`:61-62`).
  - Quel `dd` prende `sm:col-span-3`, così le coppie successive restano allineate nella griglia a 4 colonne.
  - Spariscono gli import ora inutili `formatPlannerDate` e `HINT`.
  - Il testid `pac-planner-order-detail-price-date` non ha consumatori, né in `src` né in `e2e`.
  - La data del prezzo resta visibile nella bozza, al passo Asset.
- **`request.ts`**: l'import `daysBetween` (`:12`) diventa inutile. `priceIsCopied` resta, perché decide
  ancora la provenance del prezzo (`:258`, `:266`).
- **Le fixture di risultato** (`pac_plan_result.*`, `rebalancer_plan_result.*`) non cambiano. Contengono
  solo `asset_class` e `source_label`, che nell'output restano.
- **Il test dell'evaluator costruisce i modelli esatti a mano** (`test_pac_planner_evaluator.py:65`,
  `:97-98`, `:118-123`, `:401`), e scrive anche una richiesta JSON (`:488-539`: `freshness` a `:495`,
  `source_kind` della cassa a `:539`). Va adeguato insieme ai modelli: lo fa il test-author in S1.
- **Nessuno spec E2E legge il pacchetto di compute.** `e2e/tools/allocation-tool-fixtures.ts` non ha
  consumatori, e il suo `SourceQuoteWire.reference_date` (`:45`) è il tipo dell'API allocation-source,
  che resta.

## 7. Passi

**S0 — Il piano.** Questo file, il link in avanti in Round5PostMerge e la riga 11 nel README
dell'implementazione.

**S1 — I test, prima rossi (test-author).** Solo file di test e fixture. I pin restano dove sono.
- *Schema*:
  - i default vengono accettati e riempiti;
  - i campi tolti vengono rifiutati (strict);
  - i 3 codici tolti finiscono in `SUPERSEDED_PLANNER_ISSUE_CODES` (`:1139`) ed escono da
    `EXPECTED_PLANNER_ISSUE_CODES` (`:1102`, `:1114-1115`): il conteggio a `:1180` passa da 79 a **76**;
  - i casi del normalizer a `:1626-1627` vengono tolti;
  - `fixed_fee`/`variable_floor`, `asset_class` e `source_label` sono facoltativi;
  - `PlannerCatalogAsset.asset_class` accetta `null`;
  - la SELL senza `fee_schedule_id` viene rifiutata.
- *Normalizer*:
  - senza `transfer_cap` si trasferisce tutta la fonte;
  - una BUY senza tabella paga zero;
  - una tabella senza valuta viene istanziata per valuta, e una tabella con due valute dà
    `currency_mismatch`;
  - una BUY con un ID che non punta a niente dà ancora `fee_schedule_missing`;
  - in `test_pac_planner_normalize.py` spariscono i test della staleness, `:599-629` e `:632-675`;
  - l'helper `_stale_source_warning()` (`:160-171`) resta, perché lo usa il test di precedenza
    (`:352-359`). Il suo percorso passa da `quote.freshness` a un campo che esiste ancora.
    `provenance_stale_confirmed` è un codice della fonte, e la produzione non lo emette;
  - il conteggio a `:953-954` passa da 79 a **76**.
- *Equivalenze*:
  - per ogni fixture di richiesta: `model_dump(mode="json", exclude_defaults=True)`, poi una nuova
    validazione, dà lo stesso modello e lo stesso scenario esatto (o le stesse issue, se non è
    `ready`). Per le due richieste PAC anche lo stesso risultato e lo stesso `request_fingerprint`.
    La richiesta Rebalancer non ha un planner (il Tool accetta solo `PacPlannerRequest`,
    `tool_plugins/pac_allocator.py:154`): per lei bastano modello e scenario;
  - `min` è un `no_op` (5 € contro un prezzo intero di 10 €). Un confronto fra `min` e il gemello
    sarebbe vero anche a vuoto, quindi si confrontano **dopo la stessa modifica** di
    `_incumbent_payload()` (`test_pac_planner_planner.py:126`, cassa a 50 €), con un controllo
    positivo: almeno un ordine. Stessi ordini, commissioni e obiettivo; il fingerprint può
    differire, perché la tabella a zero è omessa (§3);
  - una commissione **non nulla** senza valuta (solo `rate`) e la stessa tabella con i campi
    monetari espliciti in EUR danno gli stessi ordini, commissioni e obiettivo. È l'unico caso
    che esercita l'istanza `{id}~{CUR}` con un costo vero.
- *API*:
  - in `test_pac_planner_tool_api.py:270-288` sparisce la tupla `price_date_missing` (`:287`);
  - un compute sul gemello compatto passa attraverso la validazione della piattaforma e dà gli stessi
    ordini di `min`, tutti e due con la stessa modifica della cassa e lo stesso controllo positivo.
- *Dove*: nessun nuovo file di test backend, così non si tocca il registro condiviso. Le prove
  stanno nei file esistenti (schemi, normalizer, planner, API).
- *Fixture* (`backend/test_scripts/fixtures/pac_allocator/`):
  - le tre richieste esistenti restano esplicite, senza i campi tolti. Lo vogliono i loro consumatori
    in 4 file di test: schemi `:161`, `:165`, `:638-642`, `:954`; normalizer `:49-50`; planner;
    API `:55`. La candidate-max serve per il budget di byte (`:640`, `:954`);
  - si aggiunge `pac_plan_request.compact.v2.json`, cioè `min` nella forma che spedirebbe la UI: niente
    valori di default e la tabella a zero omessa.
- *Evaluator*: i costruttori dei modelli esatti e la richiesta JSON del test vengono adeguati (§6).
- *Frontend*:
  - un nuovo `planner/request.test.ts`: il builder omette i default, e `resolved` li ha riempiti;
  - `StateNotice.test.ts` usa il tipo risolto;
  - la registrazione nel runner è un'aggiunta in `scripts/test_runner/_frontend_utility.py`. Core o
    component lo decide il test-author: `draft.svelte.ts` usa le rune.
  - La registrazione è obbligatoria: `check-orphans` cerca i test unitari del frontend non registrati
    (`scripts/test_runner/_cli.py:230`).
- *Prova del rosso*: una volta per suite, prima di S2, con i comandi della §8.

**S2 — Lo schema.** Le §2 e §3, più `json_schema_serialization_defaults_required`.

**S3 — Il motore.** Normalizer, modelli e codici. Evaluator, vincoli e oracolo non si toccano.

**S4 — Contratti e codec.** Viene prima della UI. Il builder valida col codec generato
(`request.ts:415`): finché il codec non ha i default, una richiesta compatta non passa.
- `api sync`;
- controllo dei `.default(…)` nel codec generato e di quello che arriva al client;
- nuovi pin misurati;
- `16_toolPlatform/handoff-pac-D.md` §0: fingerprint, generazione e i nuovi default.

**S5 — La UI.**
- il builder: omissioni, freshness e `source_kind` tolti, commissioni compatte;
- i tipi, `resolved` e le viste del risultato;
- `OrderDetail`.
Regola del builder per le commissioni:
- un modo BUY con tutte le commissioni a zero omette la tabella e il `fee_schedule_id` della route;
- un modo BUY con commissioni spedisce la tabella senza i campi a zero;
- il builder spedisce solo route e tabelle BUY (`request.ts:303-306`, `:376`). Una route SELL, se un
  giorno arrivasse dalla UI, vorrebbe sempre il suo `fee_schedule_id`.

**S6 — Documentazione.**
- Nessuna pagina MkDocs EN cita i campi tolti.
  - `developer/architecture/patterns/tool_plugins.en.md:197`, `:210` descrive già la regola su cui si
    regge la slice (§1).
  - Se serve una frase sul wire compatto, la scrive il docs-writer, poi `mkdocs build`.
- Una nota datata in testa ai progetti autorevoli che descrivono i campi tolti.
  - Oggi solo `plan-phase00PacRebalancerUiTarget.prompt.md:770` (`source_kind`).
  - Non riscrivo i progetti.

**S7 — Le chiavi i18n.**
- Prima una scansione del sorgente e del catalogo che dimostri che le 4 chiavi non hanno più
  consumatori.
- Poi `dev.py i18n remove`, solo su `tools.pacAllocator.*`, e `i18n audit`.

**S8 — I gate**, nella §8.

**S9 — Il checkpoint.**
- `git diff --check`;
- cancello `/tmp/libreFolio_d_slice/probe_*.py`, `classify.py*` e `orig_*.json`;
- CHECKPOINT READY al coordinator;
- poi FROZEN.

## 8. Selettori e gate

Tutti con questo prefisso, un comando per volta:
`PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py test --test-port 6151 --data-dir /tmp/librefolio-r2-d …`

1. Prima di ogni gate che avvia il backend (lezione R14.8):
   - `front build --debug`;
   - `mkdocs build`, se è cambiato un `.md` di MkDocs.
   - La build è vecchia appena cambia un file qualsiasi sotto `frontend/src`, test compresi, o un `.py`
     sotto `backend/app/schemas` (`scripts/cli_base.py:540-583`). Quindi la build si rifà dopo l'ultima
     modifica, e un gate col backend non va mai lanciato a metà di un passo.
2. Backend:
   - `schemas pac-planner`, `schemas tools`;
   - le 9 suite `services pac-planner-*`;
   - `api pac-planner-tool`, `api tools`, `api portfolio`;
   - `services tools-lifecycle`, `utils tools-wire`, `services tools-registry`,
     `services portfolio-allocation-source`.
3. Frontend:
   - `front-utility core-unit`, `component-unit`, `document-title`.
4. Statici:
   - `check-orphans`;
   - `i18n audit`;
   - `front check`, senza warning nei file PAC;
   - `front build` di produzione, **per ultimo**.

## 9. Definition of done

- [x] Schema, motore e UI seguono le §1–§3. Evaluator, vincoli e oracolo sono invariati: `git diff` vuoto sui tre file.
- [x] Per ogni fixture di richiesta, la forma `exclude_defaults` e quella esplicita danno lo stesso scenario esatto, e per le PAC lo stesso risultato e `request_fingerprint`. Il gemello compatto dà gli stessi ordini di `min` con la stessa cassa aumentata (almeno un ordine), anche via API.
- [x] La UI spedisce il pacchetto compatto e legge il risolto. Nessuna vista legge `freshness` o `reference_date` del prezzo.
- [x] Il codec generato ha i default. Pin, handoff §0 e fingerprint sono aggiornati con valori misurati.
- [x] Le 4 chiavi sono tolte con `dev.py i18n`, la scansione è registrata e `i18n audit` è pulito.
- [x] Tutti i gate della §8 sono verdi, e `front check` non segnala niente nei file PAC.
- [x] Il piano è aggiornato a ogni passo, con «Note implementazione» e «Fuori pista».
- [x] Checkpoint: 6151 libera (prova con `lsof`), `git diff --check` pulito, probe cancellato, FROZEN.

> Spuntata il 2026-10-05 a fine S9. Le prove sono nella §12, passo per passo.

## 10. Conflitti previsti

- **i18n**: gli altri rami scrivono altri namespace negli stessi 4 cataloghi. Si risolve al merge.
- **I file generati** del client sono ignorati da git: si rigenerano dopo ogni merge, prima di `front check`.
- **La cartella `16_toolPlatform/` di C** è ferma. Tocco solo la §0 di `handoff-pac-D.md`, col permesso già dato.
- **La correzione di svelte-check** in arrivo su `dev_release2` (pavimento 0/0) non tocca file PAC.
- **`_frontend_utility.py`** è condiviso. Lo modifico solo con un'aggiunta alla lista dei file vitest.

## 11. Rischi

- **Il codegen** con il primo `default`: in caso di guasto mi fermo e lo segnalo a C (§6).
- **La validazione stretta** di un default non validato: un default dict in una union resterebbe un dict.
  Lo copre il test «default accettati e riempiti».
- **Il budget di byte**: la candidate-max resta esplicita, quindi il tetto continua a essere misurato
  sul caso peggiore.
- **Fingerprint diversi** fra una tabella a zero esplicita e una omessa (§3): è un comportamento atteso,
  e lo dichiaro.
- **Il dettaglio dell'ordine perde la data del prezzo** (§6). Se il developer la rivuole, può tornare da
  un'istantanea lato UI dentro `BuiltRequest`, senza toccare il wire.

---

## 12. Avanzamento

- ✅ **S0 — 2026-10-05.** Piano scritto, link in avanti in Round5PostMerge, riga 11 nel README.
  > **Note implementazione**: sopralluogo di sola lettura alla baseline `946095d58`, con 0 file
  > modificati. Le righe delle §2–§6 sono verificate con `grep`/`sed` sul codice, il 2026-10-05.
  > Una seconda passata, prima di S1, ha trovato 3 siti in più: la richiesta JSON nel test
  > dell'evaluator (`:488-539`), il secondo conteggio 79 (`test_pac_planner_normalize.py:953-954`) e
  > l'uso di `_stale_source_warning()` nel test di precedenza (`:359`). Sono nella §6 e in S1.
  > Nessuno spec E2E consuma il pacchetto. I pin del fingerprint esistono solo in
  > `test_pac_planner_schemas.py:3415`, `:3421` e in `handoff-pac-D.md:64-65`. I file generati del
  > client sono ignorati da git.
- ✅ **S1 — 2026-10-05.** Test e fixture scritti dal test-author, poi rivisti da me riga per riga.
  Sono tutti rossi, e per il motivo giusto.
  > **Note implementazione**:
  > - **Toccati solo test e fixture**: 12 file modificati e 2 nuovi.
  >   - Il nuovo `pac_plan_request.compact.v2.json` è `min` senza default e senza tabella.
  >   - Il nuovo `planner/request.test.ts` ha 7 test.
  >   - L'unica riga fuori dai test è in `scripts/test_runner/_frontend_utility.py:258`, nella
  >     lista jsdom di `component-unit`.
  >   - I pin `:3415`/`:3421` sono fermi.
  > - **I fingerprint dei fixture di risultato** sono segnaposto (`fixture-…-not-a-production-hash`):
  >   non si rimisurano.
  > - **Revisione** (diff in `/tmp/libreFolio_d_slice/s1_*.diff`). Ho controllato sul codice che:
  >   - il percorso del mismatch interno alla tabella è `brokers/broker/<id>/fee_schedules`
  >     (`normalize.py:362`, `:380`);
  >   - i campi di `ExactFeeSchedule` sono quelli usati dai test (`models.py:280-287`);
  >   - `quote` accetta `null` (schema `:377`);
  >   - il `request_fingerprint` è lo sha256 del `repr` dello scenario esatto (`evaluator.py:174-178`).
  >     Quindi la forma `exclude_defaults` e quella esplicita danno lo stesso fingerprint;
  >   - `route-c-alpha-buy` è bloccata solo dalla valuta della commissione: la capability
  >     `whole_quantity` non ha valuta, e broker-alpha è `automatic` con `EUR/USD`;
  >   - una route di cassa sullo stesso broker non ha controlli contrari nel normalizer
  >     (`:464-498`), né in `ExactFundingRoute` (`models.py:389-395`);
  >   - il builder rende già `1.50` come `1.5` (`wireDecimal`, `request.ts:307`). Con il campo
  >     vuoto oggi spedisce la fonte intera (`:338`), che è il nuovo significato dell'assenza.
  > - **Prova del rosso** (log in `/tmp/libreFolio_d_slice/`):
  >
  >   | Selettore | Rossi | Verdi | Log |
  >   |---|---|---|---|
  >   | `schemas pac-planner` | 50 | 493 | `s1_schemas.log` |
  >   | `services pac-planner-core` | 76 | 101 | `s1_core.log` |
  >   | `services pac-planner-evaluator` | 120 | 39 | `s1_evaluator.log` |
  >   | `services pac-planner-service` | 24 + 13 errori | 4 | `s1_service.log` |
  >   | `api pac-planner-tool` | 7 | 0 | `s1_api.log` |
  >   | `front-utility component-unit` | 6, tutti in `request.test.ts` | 2217 | `s1_component_unit.log` |
  >
  >   - **API**: tutti e 7 i test sono rossi per lo stesso motivo. I fixture espliciti non hanno più
  >     `reference_date`, `freshness` e `source_kind`, che oggi sono obbligatori: il compute risponde
  >     `invalid_parameters` con `missing`.
  >   - **Il test verde in `request.test.ts`** è la guardia del ticker `null` e del peso zero, che
  >     restano sul wire: è verde anche prima, come previsto.
  >   - **Le suite oracolo, politiche, prova, report e solver** non le ho lanciate. Sono rosse di
  >     riflesso (fixture senza i campi), e tornano verdi in S3.
  >   - Prima del gate API: `dev.py front build --debug` (exit 0, `s1_front_build_debug.log`).
  >     La build rilancia anche l'export dei contratti e la generazione dei tipi. 6151 libera dopo il
  >     gate (`lsof` exit 1).
  >
  > **⚠️ Fuori pista** — correzioni al brief, trovate dal test-author o in revisione:
  > - **`issues.py:49-50` fissa 79 codici nel codice di produzione**, non solo nei test. S3 lo porta a 76.
  > - **`reference_date` e `freshness` stanno su `ExactAssetQuote`** (`models.py:243-244`), non su `ExactAsset`.
  > - **Del funding si tiene `source: {kind}`.** Esce solo il `source_kind` della cassa.
  > - **`/tools/compute` accetta al massimo 4 voci** (`schemas/tools.py:67`). Il test dei campi tolti
  >   manda 5 casi, in lotti da 2.
  > - **`request.test.ts` vuole jsdom.** In node Svelte compila il draft per il server, e i `$derived`
  >   restano fermi alla prima lettura.
  > - **`route-c-alpha-buy` nel fixture medium ha già una commissione EUR su un Asset USD.** Il test della
  >   tabella senza valuta la rimette apposta: è il caso che la tabella senza valuta risolve.
  > - **`_stale_source_warning()` ora punta a `quote.provenance_id`.**
  > - **S9 cancella più file**: tutto `/tmp/libreFolio_d_slice/probe_*.py`, `classify.py*` e
  >   `orig_*.json`, non solo `probe_defaults.py`.
- ✅ **S2 — 2026-10-05.** Lo schema segue le §2 e §3. Tocca solo `backend/app/schemas/pac_allocator.py`.
  > **Note implementazione**:
  > - **Tolti**:
  >   - i 3 codici dal `PlannerIssueCode`;
  >   - `FreshObservation`, `AcceptedStaleObservation` e `ObservationFreshness`;
  >   - `reference_date` e `freshness` dal prezzo;
  >   - il `source_kind` della cassa.
  > - **`ReferenceDate` resta**: lo usano `as_of`, il costo medio e le ritenute.
  > - **Default**: tutti con valore diretto (`= []`, `= "0"`, `= NoOrderCap(kind="none")`), mai factory.
  > - **Due `description` nuove**: «assente = tutta la fonte» su `transfer_cap`, e «assente = BUY senza
  >   commissioni» sull'override BUY di `fee_schedule_id`. Una docstring su `BrokerFeeScheduleInput`
  >   spiega lo zero e la valuta presa dalla route.
  > - **`AllocationStrictModel`** prende `json_schema_serialization_defaults_required=True`, con un commento.
  > - **Sonda** (`/tmp/libreFolio_d_slice/probe_s2.py`):
  >   - l'ordine dei campi della route resta quello di prima, anche con l'override BUY;
  >   - un default su union esce come `{"$ref": …, "default": {"kind": "none"}}`;
  >   - un facoltativo esce come `anyOf […, null]` con `default: null`;
  >   - `PlannerCatalogAsset` ha `asset_class` fra i `required`, ed è nullable.
  > - **Gate**: `schemas pac-planner` dà 541 verdi e 2 rossi (`s2_schemas.log`). I 2 rossi sono i pin
  >   del fingerprint, come previsto: PAC `bd84ef14…` → `4f061103…`, Rebalancer `0b43bd19…` → `be2bb19d…`.
  >   Si fissano in S4, dopo `api sync`.
- ✅ **S3 — 2026-10-05.** Il motore segue lo schema compatto. Toccati solo `issues.py`, `models.py` e
  `normalize.py`; `evaluator.py` e `constraints.py` hanno `git diff` vuoto, e l'oracle vive solo nei test.
  > **Note implementazione**:
  > - **`issues.py`**: i codici scendono da 79 a 76, e il messaggio dice «frozen 76-value G3 universe».
  >   Tolti `allocation.price_date_missing`, `allocation.stale_age_negative` e
  >   `allocation.stale_observation_not_accepted`. Il codice `price_date_missing` resta nell'API della
  >   fonte (`portfolio.py`, `portfolio_allocation_source.py`), che non cambia.
  > - **`models.py`**:
  >   - tolti `FreshnessKind`, `ExactFreshness`, e `reference_date`/`freshness` dal prezzo esatto;
  >   - tolto `ExactExistingCash.source_kind`; il `source_kind` delle funding route resta;
  >   - `ExactAsset.asset_class` diventa `str | None`.
  > - **`normalize.py`**:
  >   - **Prezzo**: niente data e niente freschezza, quindi tolti `freshness()`, `build_freshness()`,
  >     l'emissione di `price_date_missing` e le righe del prezzo esatto.
  >   - **`transfer_cap` assente**: si salta la validazione del tetto, e in costruzione vale tutto il
  >     `selected` della cassa o tutto l'importo del contributo (`build_transfer_cap`).
  >   - **Commissioni, F1 esteso**:
  >     - `fee_schedule_currencies()` dà le valute dei campi presenti, in ordine e senza doppioni;
  >     - un campo di denaro assente vale zero;
  >     - due valute nella tabella danno `currency_mismatch` sul percorso `fee_schedules`;
  >     - per la route, `validate_order_route_fee_schedule()` esce subito se manca l'ID, e confronta con
  >       la valuta del prezzo solo la prima valuta presente, come faceva prima `fixed_fee.currency`.
  >   - **Istanze** (`build_fee_instances()`):
  >     - una tabella con valuta tiene il suo ID;
  >     - una tabella senza valuta diventa `{id}~{CUR}` per ogni valuta del prezzo delle route che la
  >       usano, e nessuna istanza se nessuna route la usa;
  >     - una BUY senza tabella prende `~zero~{capability_id}~{CUR}`;
  >     - le route puntano alle istanze, e ogni Broker le ordina per
  >       `(capability_id, side, fee_schedule_id)`.
  > - **Gate**:
  >   - `services pac-planner-core` 177/177 (`s3_core2.log`);
  >   - gli altri otto `services pac-planner-*`, cioè service, evaluator, oracle, policies, solver,
  >     proof, wire-numbers e report: 41, 159, 21, 40, 20, 30, 39 e 25, tutti verdi (`s3_<sel>.log`);
  >   - `schemas pac-planner` 541 verdi e 2 rossi, sempre e solo i pin, con fingerprint identici a S2:
  >     PAC `4f061103…`, Rebalancer `be2bb19d…` (`s3_schemas.log`).
  >
  > **⚠️ Fuori pista**: il primo giro di core dava 3 rossi su 177, tutti nel test di S1 che prova il
  > `currency_mismatch` delle commissioni: arrivava `needs_input` dove il test voleva `invalid`.
  > - **Causa**: il denaro USD nella tabella passa da `money()`, che registra USD fra le valute usate.
  >   Il motore chiede quindi il cambio EUR/USD e segnala `fx_rate_missing`, di tipo `missing`, che vince
  >   su `invalid` (`issues.py:193-198`).
  > - **Non è un difetto del motore**: prima della slice il denaro delle commissioni passava già da
  >   `money()`. Mancava il cambio nel payload del test.
  > - **Sonda** (`probe_s3_mismatch.py`): con `"EUR/USD": "1.10"` nei cambi, i 3 casi danno `invalid`
  >   con un solo errore, `currency_mismatch`, sul percorso atteso.
  > - **Correzione del test-author**: aggiunge quel cambio con un commento, e rafforza l'asserzione: ora
  >   il mismatch dev'essere l'**unico** errore. Nessun altro file toccato, come mostrano le impronte
  >   prima e dopo.
- ✅ **S4 — 2026-10-05.** Contratti e codec rigenerati, pin fissati, handoff aggiornato.
  > **Note implementazione**:
  > - **`api sync`**: rc=0 (`s4_api_sync.log`). Una sola Tool; generazione `f636854e…`. I cinque
  >   file generati restano ignorati da git.
  > - **Codec** (`generated-tools.ts`):
  >   - 23 `.optional().default(…)`, fra cui `[]` per le liste, `"0"` per `rate`, `fx_spread_rate` ed
  >     `execution_margin_rate`, `{}` per `fx_rates`, `{kind: "none"}` per cap, minimi e
  >     `variable_cap`, `0` per `priority`, e `null` per `fee_schedule_id`, `fixed_fee`,
  >     `variable_floor`, `transfer_cap`, `asset_class` e `source_label`;
  >   - zero occorrenze di `freshness`, `age_days`, `accepted`, `source_kind` e dei 3 codici tolti;
  >   - la mappa espone `schemaFingerprint: "4f061103…"`, e `ToolInput`/`ToolOutput` sono
  >     `z.input`/`z.output`: il client può mandare la forma compatta e leggere quella risolta.
  > - **Nessun `reference_date` nel codec**, ed è giusto: la Tool espone solo il PAC, e la data resta
  >   solo nel `sell_context` del Rebalancer, che non è una Tool.
  > - **Pin** (`test_pac_planner_schemas.py:3765,3771`): PAC `4f061103…`, Rebalancer `be2bb19d…`.
  >   Coincidono coi valori di S2 e S3, quindi il motore non ha toccato lo schema.
  > - **`handoff-pac-D.md` §0**:
  >   - una nota sulla compattazione;
  >   - le righe dello schema spostate di −14 (`:600,634`, `:2332-2343,2396-2420,2492-2503`,
  >     `:2519-2520`), verificate sul testo;
  >   - fingerprint e generazione nuovi, con i vecchi;
  >   - un paragrafo sul wire compatto: cosa è stato tolto e cosa significa ora un campo assente.
  > - **Gate**:
  >   - `schemas pac-planner` 543/543 (`s4_schemas.log`);
  >   - `front build --debug` rc=0, 12:28:53–12:30:30 (`s4_front_build_debug.log`);
  >   - `api pac-planner-tool` 7/7, 12:30:50–12:31:10 (`s4_api_tool.log`); dopo, la porta 6151 era
  >     libera.
  > - **svelte-check nella build debug**: 40 errori e 41 warning.
  >   - I 41 warning e 3 errori sono il pavimento fuori PAC: `TransactionFormModal.test.ts` ×2 e
  >     `ToolExecutionMetrics.svelte`.
  >   - Gli altri 37 errori sono tutti PAC, nei file che riscrive S5: `types.ts`, `model.ts`,
  >     `text.ts`, `OrderDetail.svelte`, e i due test di S1.
- ✅ **S5 — 2026-10-05.** La UI spedisce il wire compatto e le viste leggono la richiesta risolta.
  > **Note implementazione**:
  > - **`planner/types.ts`**:
  >   - `PacResolvedRequest` è lo `z.output` del contratto `pac_allocator@1.0.0`, preso da
  >     `ToolContractMap`. Ci sono anche `PacResolvedAsset`, `PacResolvedFundingRoute` e
  >     `PacResolvedOrderRoute`;
  >   - lato input, le liste ora facoltative si leggono con `NonNullable<…>[number]`: capability,
  >     tabelle, cassa, contributi, funding route ed esposizioni.
  > - **`planner/request.ts`**, il builder:
  >   - quattro helper dopo `wireInteger`:
  >     - `field(key, value)` dà `{}` per `null`, così la chiave manca e non vale `undefined`, e il
  >       giro JSON resta identico;
  >     - `nonZero()` usa `decimalSign`;
  >     - `nonEmpty()`;
  >     - `feeSchedule()` dà `null` per un modo BUY con tutte le commissioni a zero. Altrimenti spedisce
  >       solo `fixed_fee`, `rate` e `variable_floor` diversi da zero, e `variable_cap` solo se
  >       compilato (§3);
  >   - prezzo senza `reference_date` né `freshness`, cassa senza `source_kind`, `source_label` solo se
  >     c'è;
  >   - omessi ai default: `priority` (route e funding), `execution_margin_rate`, minimi e cap `none`,
  >     `fx_spread_rate` a zero, `fx_rates` vuoto, liste vuote. `fee_schedule_id` va sulla route solo se
  >     la sua tabella è stata spedita;
  >   - `transfer_cap` solo se l'utente l'ha scritto. Il vecchio ripiego sull'importo della fonte non
  >     c'è più: senza tetto il motore trasferisce tutta la fonte (S3, `build_transfer_cap`);
  >   - `BuiltRequest.request` resta il corpo compatto, ed è quello che parte (`run.svelte.ts:65`). Il
  >     nuovo `BuiltRequest.resolved` è `parsed.data`, la stessa validazione del codec che c'era già.
  > - **Viste del risultato**: `model.ts` (`PlanLookup`, `planLookup`, `requiredMinimumRoutes`),
  >   `text.ts`, `StateNotice.svelte` e `ResultView.svelte` usano i tipi risolti e
  >   `outcome.built.resolved`. Sul corpo compatto priorità, cap e margini sarebbero `undefined`.
  > - **`OrderDetail.svelte`**:
  >   - tolta la riga «Price date», cioè `quote.reference_date`, `quote.freshness` e la chiave
  >     `staleQuote`, col testid `pac-planner-order-detail-price-date`. Nessun test lo usava (grep su
  >     `src` ed `e2e`);
  >   - `OriginBadge` passa nel dd di «Source price», che prende tutta la riga (`sm:col-span-3`);
  >   - tolti gli import morti `formatPlannerDate` e `HINT`; `locale` resta, per `provenanceWhen`.
  > - **Consumatori controllati, nessuna modifica**:
  >   - le issue puntano alle entità per `entity_kind`/`entity_id` (`issues.ts:66-110`), non per
  >     indice, quindi le tabelle omesse non spostano nulla;
  >   - il risultato non legge `fee_schedule_id`, nemmeno le istanze `{id}~{CUR}` e `~zero~…` di S3;
  >   - `review.ts:90` legge il draft, non la richiesta;
  >   - `daysBetween` resta per `AgeLabel.svelte`, `review.ts` e `draft.svelte.ts`. Da `request.ts`
  >     è sparito solo l'import.
  > - **Gate**:
  >   - `front check`: 3 errori e 41 warning in 4 file, tutti fuori PAC (`BrokerSharingPanel` 27,
  >     `GlobalSettingsTab` 14, `TransactionFormModal.test.ts` 2, `ToolExecutionMetrics` 1, di C,
  >     `8e7259ecc`). Zero in `pac-allocator`; prima di S5 erano 37 (`s5_front_check.log`);
  >   - `front-utility component-unit`: 97 file, 2223/2223 (`s5_component_unit.log`);
  >   - controllo positivo, `component-unit "buildRequest:"`: 1 file, 7 passati e 2216 saltati. È la
  >     spec di S1, prima rossa (`s5_component_unit_request.log`);
  >   - `front-utility core-unit`: 104 file, 2878/2878 (`s5_core_unit.log`).
- ✅ **S6 — 2026-10-05.** Documentazione: una nota nel journal, MkDocs invariato.
  > **Note implementazione**:
  > - **MkDocs**: nessuna pagina cita i campi tolti. Il grep di `freshness`, `reference_date`,
  >   `source_kind`, `age_days` e dei 3 codici su `mkdocs_src/docs` trova solo Aroon,
  >   `risk-metrics/data-quality` e `transactions/price_resolver.md`, che parlano d'altro. Nessuna
  >   pagina descrive i campi del wire PAC. `tool_plugins.en.md:197` e `:210` dicono già la regola
  >   della slice: non spedire al posto della richiesta l'output validato con i default. Niente
  >   docs-writer e niente `mkdocs build`, perché MkDocs non cambia.
  > - **`plan-phase00PacRebalancerUiTarget.prompt.md:56-67`**: una nota datata in coda agli errata,
  >   che prevale sul testo sotto. Dice tre cose:
  >   - la versione: il `2.0.0` dell'erratum del 24/09 è ora `1.0.0`;
  >   - i campi tolti: `source_kind` del §18.1 (`:784`), e prezzo senza data né freschezza;
  >   - il wire compatto con la richiesta risolta.
  >
  >   Non riscrivo il progetto.
  >
  > **⚠️ Fuori pista**:
  > - **Erratum sulla versione**: la nota corregge anche il «contratto vivo `2.0.0`» dell'erratum del
  >   24/09. Era rimasto vecchio quando, il 02/10, solo l'handoff §0 era stato riportato a `1.0.0`.
  > - **Visti e lasciati**, perché sono cronache e non progetti:
  >   - `review/PAC_ALLOCATOR_REVIEW_DOSSIER.md:402,429-434`, la fotografia del 19/09, con le sue note
  >     di aggiornamento in testa. Descrive ancora il prezzo stale accettato con `accepted` e
  >     `age_days`;
  >   - le bozze e i piani di implementazione dei round passati;
  >   - in `16_toolPlatform`, la cartella ferma di C: `manifest-integrazione-C.md` e
  >     `plan-phase00ToolPlatform.prompt.md`. Delle 3 occorrenze in `handoff-pac-D.md:79-81`, tutte
  >     sono la nota di S4.
  > - **Segnalato, non toccato** (fuori dalla slice): `developer/frontend/state/app-state.md:260`
  >   dice ancora che `planner/format.ts` «is not in the source tree yet».
- ✅ **S7 — 2026-10-05.** Le 4 chiavi i18n tolte con `dev.py i18n remove`, dopo la scansione.
  > **Note implementazione**:
  > - **Scansione del sorgente**, prima di togliere:
  >   - i 2 codici `stale_age_negative` e `stale_observation_not_accepted` restano solo nei test, come
  >     assenze volute: l'insieme dei superati in `test_pac_planner_schemas.py:1197-1198` e l'asserzione
  >     di assenza in `test_pac_planner_normalize.py:872`. Zero in `backend/app`, `frontend/src`,
  >     `scripts` e nel codec (S4);
  >   - `staleQuote`: zero usi dopo S5. A HEAD l'unico consumatore era `OrderDetail.svelte:63-68`;
  >   - `result.detail.priceDate`: zero usi. Gli altri `priceDate` del sorgente sono proprietà di oggetti
  >     e non chiavi: `ProviderAssignmentSection.svelte:78,343`, `providerProbe.ts:86,114`,
  >     `providerProbe.test.ts:131`;
  >   - nessun template dinamico su `result.detail`: l'unico `KEY` di quel ramo è `OrderDetail.svelte:23`,
  >     senza `${KEY}.${…}`.
  > - **Scansione del catalogo**: le 4 chiavi c'erano in en/it/fr/es, 4377 chiavi per lingua e parità
  >   piena (`s7_catalog_scan.py`).
  > - **Rimozione**: `dev.py i18n remove "tools.pacAllocator.<chiave>" -f`, una chiave per volta, tutte
  >   con exit 0 e «✓ removed» nelle 4 lingue (`s7_remove.log`).
  >   - `git diff --stat`: 4 righe tolte per ognuno dei 4 cataloghi, nient'altro;
  >   - dopo: 4373 chiavi per lingua, parità piena, nessuna occorrenza nel sorgente. Restano solo i
  >     `.pyc` in `__pycache__`, ignorati da git.
  > - **Restano**, verificate nelle 4 lingue: `planner.assetEditor.priceDate`,
  >   `planner.issues.allocation.price_date_missing` (§4) e `planner.problems.priceDateMissing`.
  > - **`i18n audit`**, prima e dopo (`s7_audit_before.log`, `s7_audit_after.log`):
  >   - prima: 523 chiavi probabilmente inutilizzate. Le 2 in più del gate R14 erano proprio
  >     `result.detail.priceDate` e `staleQuote`, rese orfane da S5;
  >   - dopo: 521, nessuna traduzione mancante, 0 chiavi di backend mancanti. L'insieme coincide **riga per
  >     riga** con quello del gate R14 sulla revisione unita (`/tmp/libreFolio_d_r14m/gate_i18n-audit.log`):
  >     la slice non lascia nuove chiavi orfane.
  >
  > **⚠️ Fuori pista**:
  > - **L'audit non poteva provare i 2 codici**: non sono mai stati nella lista delle inutilizzate. Il
  >   rilevatore li conta come usati per il prefisso dinamico `issues.${code}`. La prova che sono morti è
  >   la scansione del sorgente, non l'audit.
  > - **Il numero delle altre chiavi**: il via ne contava 113. L'audit di oggi ne conta 521, di cui 297
  >   sotto `tools.pacAllocator` (129 in `planner.`, 168 dell'interfaccia precedente). Sono misure, non
  >   azioni: restano tutte, come deciso.
  > - **Controllo sbagliato, poi corretto**: il mio script cercava `tools.pacAllocator.assetEditor.priceDate`,
  >   ma la chiave vera è `tools.pacAllocator.planner.assetEditor.priceDate`. L'ho trovata con
  >   `dev.py i18n search "priceDate" -k`, prima di togliere.
  > - **`problems.priceDateMissing` e `priceDateAfterReference`**: già orfane a HEAD (`git grep` vuoto su
  >   `frontend/src`). Non le ha create la slice, e restano fra le altre.
- ✅ **S8 — 2026-10-05.** Tutti i gate della §8 verdi, nella corsia 6151, un comando per volta.
  > **Note implementazione**:
  > - **Prima dei gate col backend**: `front build --debug`, exit 0 (`s8_front_build_debug.log`).
  >   `mkdocs build` non serve: nessun `.md` più nuovo di `mkdocs_src/site/index.html` (09:51), che è
  >   il controllo di `auto_build_mkdocs` (`dev.py:2049-2068`). La build non ha sporcato file tracciati:
  >   32 percorsi sporchi prima e dopo, tutti della slice.
  > - **Script**: `/tmp/libreFolio_d_slice/s8_gates.sh`, sequenziale, con `lsof` su 6151 prima e dopo.
  >   Sintesi in `s8_gates.summary`, un log per gate (`s8_gate_<categoria>_<azione>.log`).
  >   Confronto con il gate R14 sulla revisione unita (`/tmp/libreFolio_d_r14m/`):
  >
  >   | Gate | R14 | Slice | Δ |
  >   |---|---:|---:|---:|
  >   | `api pac-planner-tool` | 6 | 7 | +1 |
  >   | `api tools` | 7 | 7 | = |
  >   | `api portfolio` | 58 | 58 | = |
  >   | `schemas pac-planner` | 522 | 543 | +21 |
  >   | `schemas tools` | 271 | 271 | = |
  >   | `services pac-planner-core` | 164 | 177 | +13 |
  >   | `services pac-planner-service` | 36 | 41 | +5 |
  >   | `services pac-planner-evaluator` · `oracle` · `policies` · `solver` | 159 · 21 · 40 · 20 | uguali | = |
  >   | `services pac-planner-proof` · `wire-numbers` · `report` | 30 · 39 · 25 | uguali | = |
  >   | `services tools-lifecycle` · `utils tools-wire` | 91 · 196 | uguali | = |
  >   | `services tools-registry` · `portfolio-allocation-source` | 93 · 89 | uguali | = |
  >   | `front-utility core-unit` | 2878 | 2878 | = |
  >   | `front-utility component-unit` | 2216 | 2223 | +7 |
  >   | `front-utility document-title` | 22 | 22 | = |
  >
  >   I +40 backend e i +7 frontend sono i test di S1, prima rossi e ora verdi. Tutti con rc=0.
  > - **Statici**:
  >   - `check-orphans`: «Every registered test is reachable from an 'all' action»;
  >   - `i18n audit`: 4373 chiavi, 521 probabilmente inutilizzate, lo stesso insieme di R14 (S7);
  >   - `front check`: rc=1 per il pavimento, cioè 3 errori e 41 warning in 4 file, nessuno PAC:
  >     `BrokerSharingPanel.svelte` 27, `GlobalSettingsTab.svelte` 14, `TransactionFormModal.test.ts` 2,
  >     `ToolExecutionMetrics.svelte` 1. Zero occorrenze di `pac-allocator` nel log;
  >   - `front build` di produzione, per ultimo: exit 0.
  > - **Invarianti della §9**:
  >   - `git diff --stat` vuoto su `evaluator.py`, `constraints.py`, `solver.py`, `objectives.py`,
  >     `compiler.py`, `ledger.py`, `_pac_exhaustive_oracle.py` e `test_pac_planner_oracle.py`;
  >   - il motore cambia solo in `schemas/pac_allocator.py`, `issues.py`, `models.py` e `normalize.py`;
  >   - `git diff --check` pulito. I 3 file nuovi non hanno spazi in coda e finiscono con un a capo.
  > - **6151 libera** a fine script.
- ✅ **S9 — 2026-10-05.** Checkpoint pronto, poi FROZEN.
  > **Note implementazione**:
  > - **Pulizia**: cancellati 26 file di lavoro in `/tmp/libreFolio_d_slice/`: `probe_*.py` e
  >   `probe_medium.log`, `classify.py*`, `orig_*.json`, e gli aiuti di modifica `patch_s3_normalize.py`,
  >   `run_s3_services.sh` e `s5_retype.py`. Restano i log, i diff, `s7_catalog_scan.py` e `s8_gates.sh`,
  >   citati qui come prova e in sola lettura.
  > - **Porte**: `lsof -nP -iTCP:6151 -sTCP:LISTEN` → rc=1, niente in ascolto. Libera anche 6161. La copia
  >   del prod `/tmp/librefolio-r2-d-prodcopy` non esiste più: è stata cancellata in R5PostMerge
  >   (`plan-phase00PacRound5PostMerge.prompt.md:3619-3623`).
  > - **Delta**: 32 percorsi, 29 modificati e 3 nuovi; stage vuoto. 27 vanno nel commit del codice e dei
  >   test, 5 in quello del journal.
  > - **Esclusi, tutti ignorati da git** (`git check-ignore -v`): i 5 generati di `frontend/src/lib/api/`,
  >   `frontend/build` (di produzione, da S8), `mkdocs_src/site`, `__pycache__`, i log in `/tmp`, il DB
  >   della corsia.
  > - **Previsione dei conflitti** (sola lettura): da `dd538d650` `dev_release2` (`c8daff33f`) cambia 97
  >   file. In comune con la slice ci sono solo i 4 cataloghi i18n. `git merge-file` su copie temporanee:
  >   0 conflitti, JSON valido, parità a 4498 chiavi, e le 4 chiavi restano tolte.
  > - **Messaggi di commit proposti**: `/tmp/libreFolio_commit_d_slice_code.txt` e
  >   `/tmp/libreFolio_commit_d_slice_journal.txt`, in ASCII.
  >
  > **⚠️ Fuori pista**:
  > - **Nessun E2E esercita il calcolo PAC.** Il solo spec sulla pagina Tools è `document-title`, verde in
  >   S8. `frontend/e2e/tools/allocation-tool-fixtures.ts` non ha importatori: è un resto del prototipo
  >   del Round 4. Il suo `reference_date` (`:45`) è della quotazione del report, non della richiesta PAC.
  >   Visto e lasciato.
- ✅ **S10 — Integrazione, 2026-10-05.** Commit, merge di `dev_release2` e gate finali sulla revisione unita.
  > **Note implementazione**:
  > - **Commit e merge**, lanciati dal developer con lo script del coordinator
  >   (`/tmp/libreFolio_ORDER_0510_d_slice.sh`):
  >   - `ac18ce097` refactor(pac) e `9e4140376` docs(journal), albero `9b644227c`;
  >   - merge `68483ddda`, genitori `9e4140376` e `c8daff33f`, albero `ac51b11ab` come simulato.
  >
  >   Verificato in sola lettura: worktree pulito, `c8daff33f` antenato di HEAD.
  > - **Verifica del merge** (`/tmp/libreFolio_d_int/verify_merge.py`). Dalla base `dd538d650` il mio
  >   lato cambia 162 file, `dev_release2` 97. In comune ce ne sono 5, uniti da soli: i 4 cataloghi i18n
  >   e `scripts/test_runner/_backend_services.py`.
  >   - Cataloghi: 4498 chiavi per lingua, lo stesso insieme nelle 4, nessuna modifica dei due lati
  >     persa. Le 4 chiavi tolte in S7 restano assenti; `dev_release2` ne aggiunge 125.
  >   - `_backend_services.py`: ci sono tutte le 6 righe aggiunte dal mio lato e le 22 del loro.
  > - **Sovrapposizioni indirette**, cioè file diversi che arrivano al PAC:
  >   - `ToolExecutionMetrics.svelte` di C, importato da `result/ProofPanel.svelte`: cambia solo il tipo
  >     del parametro di `duration()`, ora `number | null`. Le props restano;
  >   - `fx.py`, PR #30 (`convert_bulk`): nessun file PAC, del plugin o dell'allocation-source lo importa.
  >     `portfolio_allocation_source.py` legge `FxRate` dal DB. Arriva al PAC solo attraverso il report
  >     del portafoglio, coperto da `api portfolio`;
  >   - `brim.py` e `brokers.py` cambiano solo l'OpenAPI generale;
  >   - il runner aspetta l'avvio del backend condiviso fino a 300 s (`9db350102`).
  > - **Build**, nella corsia, un comando per volta:
  >   - `api sync`, rc=0. I contratti Tool non cambiano: `tool-contracts.openapi.json` `f636854eda8d`,
  >     `generated-tools.ts` `4a788406f7b7`, `tool-contract-map.generated.ts` `81f2e4ba27a6`. Cambiano
  >     solo `openapi.json` (`bc42b919c60c` → `f18d0740d294`) e `generated.ts` (`a81d34d13a35` →
  >     `2702784e5d61`), per BRIM e broker;
  >   - `front build --debug`, rc=0: svelte-check 0 errori e 0 warning;
  >   - `mkdocs build` (strict), rc=0. Serviva: il merge portava 12 `.md` e `mkdocs.yml` più nuovi di
  >     `site/index.html`. Dopo, nessun `.md` è più nuovo del sito.
  > - **Gate**, con `/tmp/libreFolio_d_int/int_gates.sh`: è una copia di `s8_gates.sh`, cambiano solo
  >   l'intestazione e i percorsi dei log. Tutti rc=0, sintesi in `int_gates.summary`:
  >
  >   | Gate | S8 | Unita | Δ |
  >   |---|---:|---:|---:|
  >   | `api pac-planner-tool` · `tools` · `portfolio` | 7 · 7 · 58 | uguali | = |
  >   | `schemas pac-planner` · `tools` | 543 · 271 | uguali | = |
  >   | `services pac-planner-core` · `pac-planner-service` | 177 · 41 | uguali | = |
  >   | `services pac-planner-evaluator` · `oracle` · `policies` · `solver` | 159 · 21 · 40 · 20 | uguali | = |
  >   | `services pac-planner-proof` · `wire-numbers` · `report` | 30 · 39 · 25 | uguali | = |
  >   | `services tools-lifecycle` · `utils tools-wire` | 91 · 196 | uguali | = |
  >   | `services tools-registry` · `portfolio-allocation-source` | 93 · 89 | uguali | = |
  >   | `front-utility core-unit` | 2878 | 2898 | +20 |
  >   | `front-utility component-unit` · `document-title` | 2223 · 22 | uguali | = |
  >
  >   - `check-orphans` verde;
  >   - `i18n audit`: 522 chiavi probabilmente inutilizzate, una più di S8;
  >   - `front check`: **rc=0, 0 errori e 0 warning**, il nuovo pavimento;
  >   - `front build` di produzione, per ultimo, rc=0.
  > - **I due Δ vengono da `dev_release2`**:
  >   - `core-unit` +20: sono i casi nuovi di `importMerge.test.ts` (31 → 39) e `importRowState.test.ts`
  >     (22 → 34), entrambi nella lista `core-unit` (`_frontend_utility.py:55`, `:62`). Gli altri due
  >     file della lista che hanno cambiato, `OnboardingCoachmark.test.ts` e `TransactionFormModal.test.ts`,
  >     hanno gli stessi casi di prima (84 e 13). Nessun file PAC della lista è cambiato dopo S8;
  >   - la chiave in più è `importWizard.reportSet.gapFix.stepTitle`, di `9336c0e9b` «feat(import): align
  >     imports with bank truth». La usa un `titleKey` relativo (`ImportWizardModal.svelte:143`), che
  >     l'audit non risolve: è un falso positivo. Quel file è uguale su `dev_release2` e sul merge.
  > - **6151 libera** a fine script: `lsof -nP -iTCP:6151 -sTCP:LISTEN` → rc=1.
  > - **Prove** in `/tmp/libreFolio_d_int/` (chmod 700): `verify_merge.log`, `gen_before.sha`,
  >   `gen_after.sha`, `int_*.log`, `int_gates.summary`, `int_unused.txt`, `fu_listed.txt`.
  >
  > **⚠️ Fuori pista**:
  > - **Avviso SSL di MathJax** durante la build: viene dall'ambiente, come in S4, S8 e R14.
  > - **Le pagine utente e il CHANGELOG dicono ancora «nessuna interfaccia».** L'ho visto preparando la
  >   riga di CHANGELOG. La UI PAC non è su `dev_release2` (`PacPlannerTool.svelte` manca in
  >   `c8daff33f`): la porta per la prima volta il fast-forward. Diventano false:
  >   - `CHANGELOG.md:18`, «Its interactive interface is not ready yet»;
  >   - `user/tools/pac-allocator/index.en.md`: `:3`, `:12-25`, `:27-42` (card non cliccabile e
  >     `Backend/API 2.0.0 · UI 2.0.0`, oggi `1.0.0`), `:58`, `:89`, `:104`;
  >   - `user/tools/index.en.md:49`, «This is the PAC allocator's current state».
  >
  >   È il ritocco `r5-user-doc-punctual` del Round 5 (`plan-phase00PacRound5PostMerge.prompt.md:466-470`,
  >   `:3812-3813`), mai eseguito. Le due pagine esistono solo in EN. Segnalato al coordinator nel
  >   checkpoint, senza toccarle: non è fra i passi autorizzati.
  >
  > **Handoff finale**:
  > - **Stato**: HEAD `68483ddda` più il commit di journal di questo passo. `dev_release2` (`c8daff33f`)
  >   è già contenuto: l'integrazione è un fast-forward, più la riga di CHANGELOG del coordinator.
  > - **Consegnato**: il contratto PAC `1.0.0` compatto (§1–§3). La UI spedisce il pacchetto compatto
  >   e legge la richiesta risolta; 4 chiavi `tools.pacAllocator.*` tolte. Il compute usa solo il
  >   pacchetto.
  > - **Inventario**: la slice è in `ac18ce097` (27 percorsi di codice e test) e `9e4140376` (5 di
  >   journal). Questo passo tocca 2 file di journal: questo piano e la riga 11 del README.
  > - **`handoff-pac-D.md` §0 resta valida**: dopo l'`api sync` sul merge i tre file dei contratti Tool
  >   hanno gli stessi hash, quindi fingerprint `4f061103…` e generazione `f636854e…` non cambiano.
  > - **Review manuale**: la slice non ne ha avuta una nel browser, e il coordinator non l'ha chiesta.
  >   Nella UI cambia solo il dettaglio dell'ordine (riga «Price date» tolta, badge d'origine spostato),
  >   coperto dai test di componente. La review del developer è quella dei round 5–14.
  > - **Rinviato**, già registrato altrove:
  >   - le pagine utente e la riga di CHANGELOG, qui sopra;
  >   - gli E2E del calcolo PAC (Round 5, §4 punto 7);
  >   - `fx_cost` sempre zero, nel gate del TODO del coordinator;
  >   - `allocation-tool-fixtures.ts` senza importatori, `app-state.md:260` e le chiavi probabilmente
  >     inutilizzate, nel backlog di fine round del coordinator.
  > - **Ignorati da git, fuori dal commit**: i 5 file generati di `frontend/src/lib/api/`,
  >   `frontend/build`, `mkdocs_src/site`, `__pycache__`, i log in `/tmp`, il DB della corsia.
- ✅ **S11 — Pagine utente PAC (`r5-user-doc-punctual`), 2026-10-05.** Le due pagine EN descrivono il
  planner reale, prima del fast-forward.
  > **Note implementazione**:
  > - **Il via**: il developer sceglie l'opzione (a) del checkpoint S10, cioè prima le pagine e poi
  >   l'integrazione. Docs-writer, solo EN. Niente stamp, perché le pagine non hanno traduzioni. Un solo
  >   controllo incrociato col testo di CHANGELOG proposto.
  > - **`user/tools/pac-allocator/index.en.md`** (111 → 191 righe):
  >   - la descrizione (`:3`) e l'apertura (`:13-16` della pagina nuova): la card apre il planner
  >     guidato; è una simulazione e nessun ordine parte;
  >   - `## 🗺️ Using the planner`, con la coppia `Backend/API 1.0.0 · UI 1.0.0`. La mostrano la card
  >     (`ToolsHub.svelte:237-241`) e l'intestazione del tool aperto (`ToolHost.svelte:274-279`);
  >   - la tabella dei 9 passi, con FX solo quando serve (`draft.svelte.ts:691`, `:700`), e i limiti
  >     della versione (`brokerEditor.notYetSupported`, `fx.limitsHelp`);
  >   - `### 📋 Copied or typed values`: azioni esplicite, origine e data, rilettura dei copiati
  >     invariati prima del calcolo (`copies.ts:610`, `refreshPlan` a `:637`, `refreshCopiedFacts` a
  >     `:700`);
  >   - `### ⏳ While it calculates`, e `## 📊 Reading the result` con l'ancora `#reading-the-result`:
  >     i 7 esiti, «Verified in Decimal», gli errori di piattaforma rimandati alla panoramica, le 7
  >     sezioni del risultato e la privacy;
  >   - le sezioni motore, target, «never does» e dati della vecchia pagina (`:58`, `:61-74`, `:84-85`,
  >     `:89`, `:94-95`, `:104`), e un link in Related.
  > - **`user/tools/index.en.md`**: `:17-19` diventa due righe, «Its card opens a guided planner»;
  >   `:49` perde solo «This is the PAC allocator's current state.»
  > - **La mia review**, contro il codice e il catalogo EN. Sette ritocchi:
  >   1. Scenario: la valuta di valutazione parte dalla Base Currency delle preferenze
  >      (`PacPlannerTool.svelte:283-289`);
  >   2. FX: con una coppia senza tasso, **Add the pair** e **Download the rates** aprono le finestre
  >      della pagina FX, e nulla si aggiunge o si scarica senza conferma (`FxStep.svelte:112-211`);
  >   3. «Nothing stays linked to the source» → «A copy does not follow its source while you edit»,
  >      perché i copiati invariati si rileggono al calcolo;
  >   4. §🎯: «changing what you hold cannot change what this tool plans» era falso per la cassa
  >      copiata, che si rilegge. Ora parla delle posizioni, e dice che i pesi di «Copy current
  >      distribution» non seguono i cambi;
  >   5. e 6. i due link alla privacy, senza ancora (vedi Fuori pista);
  >   7. la descrizione `:3`: «in whole units or amounts» → «in whole or fractional units or in
  >      amounts». È la stessa omissione delle frazioni che c'era nella mia proposta di CHANGELOG.
  > - **Verificati e lasciati**:
  >   - «minus the spread» della UI corrisponde al motore, tasso × (1 − spread) (`numeric.py:293-305`,
  >     `constraints.py:508`);
  >   - uscire o ricaricare con una bozza modificata chiede conferma (`PacPlannerTool.svelte:250-266`).
  >     Logout e cambio di account non chiedono niente, perché la sessione cambia prima della
  >     navigazione (`auth.ts:137-160`, `contracts.ts:146-150`);
  >   - `tools/index.en.md:110`, la frase sui budget effettivi, è vera. Il limite effettivo è il minimo
  >     fra la policy dell'operazione e quella della piattaforma (`catalog.py:26-27`). I 256/512 KiB
  >     dichiarati dal PAC (`pac_allocator.py:87-88`) scendono quindi a 128/256 KiB
  >     (`schemas/tools.py:72-73`). I test di schema misurano le fixture contro 128/256 KiB
  >     (`test_pac_planner_schemas.py:66-67`, `:643-648`); nessun test fissa il minimo per il PAC.
  > - **Controllo incrociato col CHANGELOG proposto**: coerenti su solo acquisti, nessun ordine, esiti,
  >   copie rilette e privacy. Due frasi vanno corrette nel testo che applica il coordinator:
  >   - «in whole units or in amounts» omette le frazioni (Increment 0.001);
  >   - «Where a broker allows it, an order can be paid with cash in another currency» non corrisponde:
  >     la conversione la decide il calcolo, al tasso FX meno lo spread.
  > - **Gate**, nella corsia, un comando per volta (log in `/tmp/libreFolio_d_docs/`):
  >   - `git diff --check` pulito;
  >   - `mkdocs build` strict: rc=1 al primo giro (vedi Fuori pista). rc=0 e 0 warning al secondo, e al
  >     terzo dopo il ritocco 7 (21.77 s, `mkdocs_build3.log`);
  >   - `mkdocs check-links`, uguale ai due giri: 81 link validi, 3 eccezioni note, 1 rotto. È D28
  >     (`#rolling-return` in it/fr/es), l'unico rosso accettato. `user/tools/pac-allocator` ✅.
  > - **Journal**: la riga 11 del README cita S11, e `plan-phase00PacRound5PostMerge.prompt.md:471-472`
  >   collega il passo `r5-user-doc-punctual` a questo S11.
  > - **6151 libera**: `lsof -nP -iTCP:6151 -sTCP:LISTEN` → rc=1.
  >
  > **⚠️ Fuori pista**:
  > - **`tools/index.en.md:17-19` mancava** nella lista del mio checkpoint S10. Viene dallo stesso commit
  >   di `:49`, `154182295`.
  > - **Ho ritrattato la segnalazione su `tools/index.en.md:110`**: la frase è vera, come sopra.
  > - **Strict build rosso al primo giro.** Il link `../../settings/preferences.md#privacy-mode` funziona
  >   in EN. Ma la pagina PAC, che esiste solo in EN, ricade anche in it/fr/es, e lì le pagine
  >   `preferences` non hanno la sezione sulla privacy: sono tradotte al `757aac84a`, l'EN è al
  >   `b643afb31`. Con i link senza ancora la build è verde. Il debito resta alla prossima traduzione.
  > - **«Copy FX rates» non è un pulsante.** `steps/SourceCopyDialog.svelte`, 134 righe, è orfano dal mio
  >   `6f29ec1cf`: lì `AssetsStep` e `FxStep` hanno smesso di importarlo (in `0210f9848` lo importavano).
  >   Va nel backlog delle cose senza consumatori.
  > - **Due chiavi i18n dicono ancora «Not in 2.0.0»**: `brokerEditor.notIn200` e `fx.notInVersion`.
  >   Sono già nel backlog delle chiavi inutilizzate del coordinator.
  > - **`assets.noAutoPrice` contraddice il planner attuale**: «Adding an Asset copies its identity
  >   only», mentre `assets.priceAuto` dice che l'Asset arriva col suo ultimo prezzo. Nessun sorgente la
  >   usa, come le due sopra. La propongo per lo stesso backlog.
  > - **La mia proposta di CHANGELOG aveva due frasi imprecise**, le frazioni e la conversione (sopra).
  >   Le correzioni vanno al coordinator col checkpoint.
  > - **Un'osservazione, non un difetto**: il PAC dichiara 256/512 KiB, ma la piattaforma lo limita a
  >   128/256 KiB.
