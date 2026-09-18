# Step 4 — copie read-only dai domini Asset/Portfolio/Broker/FX

**Stato:** IN PROGRESS — OWNERSHIP/AUTH CONTRACT FROZEN, SYMBOL ALIGNMENT G3 OPEN.
**Dipende da:** autorizzazione prodotto e audit API corrente.
**Può procedere in parallelo con:** core esatto, input condiviso e shell fixture-driven.

← Master: [piano implementativo](plan-phase00PacRebalancerImplementation.prompt.md)
← Precedente: [solver e policy](plan-phase00Step3PacRebalancerSolverPolicies.prompt.md)

## 1. Scopo

Fornire al planner copie esplicite, modificabili e autorizzate dei fatti già
posseduti dai domini LibreFolio. Il planner deve funzionare anche senza tali
copie e senza Asset persistiti nel DB.

Le API di dominio raccolgono fatti; il Tool compute riceve uno snapshot
autosufficiente e non accede a DB/provider.

## 2. Ownership

Percorso primario:

```text
backend/app/services/portfolio_allocation_source.py
```

Percorsi additivi assegnati dopo audit:

```text
backend/app/api/v1/assets.py
backend/app/api/v1/portfolio_api.py
backend/app/api/v1/brokers.py
backend/app/api/v1/fx.py
backend/app/schemas/assets.py
backend/app/schemas/portfolio.py
```

Frontend source client:

```text
frontend/src/lib/features/tools/pac-allocator/planner/source-copy.ts
frontend/src/lib/features/tools/pac-allocator/planner/source-types.ts
```

API schema/client generati restano al writer integrazione. Nessun secondo
writer modifica questi file.

Lease produzione esclusiva `fleet-domain-copy`
(`2cece106-1dfb-45b6-b381-a420959c8e74`):

```text
backend/app/services/portfolio_allocation_source.py
backend/app/schemas/portfolio.py
backend/app/api/v1/portfolio_api.py
```

Frontend source client resta bloccato fino a G3/generated client e non è
incluso in questa slice.

## 3. Audit iniziale obbligatorio

Per ogni fatto richiesto indicare:

| Fatto | API/service esistente | Completo | Auth | Azione |
|---|---|---:|---:|---|
| Asset canonical ID | da verificare | sì/no | principal | riuso/estensione |
| holding per Broker | da verificare | sì/no | principal | riuso/estensione |
| quantità custodita | da verificare | sì/no | principal | riuso/estensione |
| quota economica | da verificare | sì/no | principal | riuso/estensione |
| cash Broker×valuta | da verificare | sì/no | principal | riuso/estensione |
| prezzo mid/valuta | da verificare | sì/no | principal | riuso/estensione |
| `quote_base_quantity` | da verificare | sì/no | principal | riuso/estensione |
| PMC | da verificare | sì/no | principal | riuso/estensione |
| type/sector/geography | da verificare | sì/no | principal | riuso/estensione |
| Broker capability/fee/tax | da verificare | sì/no | principal | riuso/estensione |
| FX rate/source/date | da verificare | sì/no | principal | riuso/estensione |

Prima di creare un endpoint, dimostrare che nessuna API/service esistente
fornisce già il fatto con semantica corretta.

> **Note implementazione 2026-09-16**: audit completato. Riutilizzabili:
> Asset ID canonico, holding OWNER per Broker, custodia, cash nativo,
> ultimo PriceHistory salvato, tipo Asset. Gap: economic quantity/cash,
> PMC/WAC, classificazioni, FX salvati e issue strutturate. Il target non
> riusa `/portfolio/report` cached né `/assets/prices/current`.

## 4. Azioni di copia

La UI espone pulsanti indipendenti:

1. copia scenario/holding iniziali;
2. copia cash esistente;
3. copia prezzi;
4. usa distribuzione corrente come base modificabile del target;
5. copia Broker/capability;
6. copia FX salvati.

Una response unica può trasportare più sezioni, ma:

- nessuna sezione viene applicata implicitamente;
- nessun refresh live;
- la distribuzione corrente è base, non consiglio;
- l'utente vede preview e staleness;
- il manuale resta sempre possibile.

## 5. Asset e holding

Regole:

- aggregazione economica per identità Asset canonica, non nome/simbolo;
- custodia per Broker preservata;
- quantità e valore con unità;
- inventario frazionario non arrotondato;
- OWNER `0%`: quantità custodita intera, quota economica separata;
- PMC Asset×Broker/lote secondo dominio esistente, senza cambiare FIFO/WAC;
- prezzo con currency, source, as-of e `quote_base_quantity`;
- type/sector/geography espliciti o missing issue;
- Asset senza prezzo non viene eliminato.

Il planner non assume che due record con label uguale siano lo stesso Asset.

## 6. Cash, contributi e Broker

- cash esistente copiato per Broker×valuta;
- contributi nuovi non vengono inventati dalla copy e restano input separato;
- nessuna cassa unica convertita;
- Broker ID/currency/capability autorizzati;
- fee BUY/SELL e tax mode separati;
- un Broker non autorizzato causa failure atomica;
- non restringere silenziosamente la response ai Broker visibili;
- scenario manuale può usare Broker locali alla request, senza DB ID.

## 7. Prezzi e FX

Le copy leggono soltanto dati salvati.

Vietato usare automaticamente:

```text
/assets/prices/current
```

perché può attivare fetch e scrivere OHLC.

Ogni prezzo/FX riporta:

- valore;
- coppia/currency;
- source/provider;
- timestamp/as-of;
- staleness;
- base quantity;
- eventuale missing/unsupported.

FX manca/incoerente:

- non omettere Asset o cash;
- restituire issue strutturata;
- lasciare al draft la decisione manuale;
- nessun provider call durante Tool compute.

## 8. Autorizzazione e privacy

Ogni endpoint/service:

- riceve il principal standard;
- verifica Portfolio/Broker/Asset;
- non restituisce subset “best effort” se una selezione contiene entità
  non autorizzate;
- non logga quantità, valori o payload;
- non inserisce valori personali in diagnostics;
- non restituisce route/order consigliati;
- non modifica record.

Test obbligatori:

- utente proprietario;
- admin secondo policy esistente;
- altro utente;
- Broker misto autorizzato/non autorizzato;
- Asset mancante/stale;
- account switch durante request;
- nessun side effect DB.

### 8.1 Contratto auth e endpoint congelato — 2026-09-16

- endpoint dedicato uncached:
  `POST /api/v1/portfolio/allocation-source`;
- request senza `user_id`/`as_user`;
- v1 OWNER-only, incluso OWNER `0%`;
- admin senza bypass globale implicito;
- selezione Broker validata atomicamente prima di leggere fatti privati;
- set misto autorizzato/non autorizzato → `403`, mai intersezione parziale;
- response priva di target, route, ordini o raccomandazioni.

Fix adiacente accoppiato:

- `POST /portfolio/wac` richiede utente autenticato;
- ogni Broker×Asset deve superare almeno l'accesso read esistente;
- anonimo `401`, non correlato `403`, autorizzato `200`;
- nessuna esposizione delle transazioni.

Questi tre file sono nella lease dello stesso writer; nessun altro workstream
li modifica in parallelo.

### 8.2 Fatti target congelati

- holding: `custody_quantity` completa e
  `economic_quantity = custody_quantity * share_percentage`, esatta e senza
  rounding;
- cash: Broker×currency full custody + economic amount separato; la scelta
  utente è esplicita e non supera custody; mai duplicata nei contributi;
- OWNER `0%`: custodia visibile, quota economica zero;
- `selected_cash_balances` aggregato resta legacy-only;
- prezzo: solo saved `PriceHistory`, con source/date/age; missing resta riga
  con issue;
- `quote_base_quantity` null/invalid non usa fallback `1` nel nuovo response;
- type/sector/geography da dati persistiti; unknown/missing/invalid produce
  issue, nessun refresh provider;
- Broker: identity/access/share/valute osservate e fact persisted obbligatori
  `active`, `allow_cash_overdraft`, `allow_asset_shorting`; `opened_at` escluso.
  I flag sono descrittivi: `active=false` resta visibile con issue source
  `allocation.broker_inactive`, `kind=unsupported`, `severity=warning`, una
  volta per Broker sul field path `brokers/broker/<id>/active`, params vuoti;
  holdings/cash non vengono nascosti e l'issue non riusa
  `broker_execution_profile_unsupported`. Overdraft/short non abilitano mai
  debito, short, capability o route nel planner v1. Capability, fee e tax non
  vengono inferiti dalla storia;
- FX: sole coppie dirette richieste, latest `<= as_of`, inversione esatta,
  source/date/age; identity `1` esplicita; missing pair come issue; nessuna
  chain o sync provider;
- PMC: riuso `compute_wac_iterative` soltanto dopo auth OWNER; provenance
  minima `runtime_wac`, target/fiscal currency, as_of e prove FX rate/date/
  missing; nessun provider source non dimostrato;
- issue deterministiche per Asset/Broker/pair/field, senza valori personali
  nel testo o nei log;
- numeri come Decimal string.

`_load_usage_counts` e qualsiasi esistenza other-user sono esclusi dalla nuova
response; il comportamento legacy resta intatto.

> **Stop aggiuntivo**: DB migration, provider I/O, modifica algoritmo WAC/FIFO,
> cache `portfolio_service.py`, auth non atomica o mancato allineamento
> ID/unità/cardinalità con G3.

### 8.3 Mapping source → planner congelato

- `ownership_share` source → `economic_share` planner;
- `economic_quantity` propone `planning_quantity`, ma il draft la mantiene
  esplicitamente confermabile/modificabile; `custody_quantity` resta separata;
- il mapper compone le righe flat Asset + Price + Classification nel
  `PlannerAssetInput` annidato, senza derivazioni finanziarie client-side;
- gli FX identity source sono evidenza di completezza/display e vengono esclusi
  dagli array pubblici di rate diretti/operativi quando il contract vieta
  `source_currency == destination_currency`;
- placeholder source `null` non diventano mai fact strict: generano issue
  tipizzate/incompletezza draft, da risolvere con input/override prima del
  submit;
- ogni fact copiato o sovrascritto conserva il proprio `provenance_id`;
- l'identity pubblica del Broker persisted conserva `active` + provenance; UI
  e normalizer impediscono route ordini su Broker inattivo. Il normalizer può
  riusare `allocation.broker_inactive` a severity error sul submit invalido.
  `DomainBrokerIdentity.active` è required/no-default; un
  `ManualBrokerIdentity` non inventa il flag persisted e segue l'input scenario
  esplicito. `allow_cash_overdraft`, `allow_asset_shorting` ed
  `execution_profile_status` restano diagnostica source/UI e non entrano nel
  request planner strict;
- il cash esistente usa il `cash_id` deterministico nel funding source
  discriminato `existing_cash`; i contributi usano `contribution_id` e restano
  input draft/user, mai output domain-copy;
- `invest_and_sell` senza fiscal currency, tax rate o withholding fact è
  bloccato come needs-input; non si assume mai
  `fiscal_currency = valuation_currency/target_currency`.

Queste regole sono obblighi di integrazione W0/frontend successiva; non
richiedono ulteriori modifiche ai tre file W2 congelati.

## 9. Lifecycle frontend della copy

Ogni request cattura:

```text
account_generation
component_instance_id
request_sequence
draft_revision
target_section
```

La response è applicabile soltanto se tutti coincidono. Inoltre:

- `AbortController` per nuova request/unmount/account switch;
- risposte vecchie ignorate;
- nessuna sovrascrittura silenziosa di campi modificati;
- preview diff e conferma quando la sezione non è pristine;
- applicazione atomica della sezione scelta;
- source metadata resta visibile nel draft.

Il backend fornisce fatti; questa logica non calcola valori finanziari.

## 10. Sequenza

- [x] 1. Verificare baseline e file ownership. ✅ 2026-09-16
- [x] 2. Compilare matrice fatto→API/service. ✅ 2026-09-16
- [x] 3. Identificare gap reali e ottenere approvazione dei file. ✅ 2026-09-16
- [x] 4. Implementare estensioni domain-level minime. ✅ 2026-09-16
- [x] 5. Implementare schema response read-only. ✅ 2026-09-16
- [ ] 6. Scrivere test auth/missing/provenance/no-side-effect. ⏳ test-author
      `domain-copy-tests` (`c0d965b1-8aa1-4217-bc06-4f7e1b6c3d29`)

> **Note implementazione (realignment FX)** — 2026-09-19
> Il redesign FX/funding a mappa canonica (Step2 §8b: `fx_rates`+`fx_spread_rate`,
> niente route/buffer/fee/step/priority) impone di riallineare il layer prefill/copy
> già costruito qui (item 4-5, 2026-09-16) al nuovo modello — era ancora sul vecchio
> schema "directed pair" (`source_currency`/`destination_currency`/`inverted`/`identity`).
> File toccati (stesso perimetro Step4, nessun file W1-core):
> - `backend/app/schemas/portfolio.py`: nuovo `_validate_canonical_fx_pair()` +
>   `PortfolioPlannerSourceFxPair` (coppia non ordinata `AAA/BBB`, alfabetica, via
>   `Currency.validate_code`); `PortfolioPlannerSourceRequest.fx_pairs` ora
>   `List[PortfolioPlannerSourceFxPair]`; `PortfolioPlannerSourceFxQuote` ha un solo
>   campo `pair` (rimossi `source_currency`/`destination_currency`/`inverted`/`identity`).
>   Il tipo `PortfolioPlannerSourceWacFxEvidence` (evidenza fiscale per-holding, path
>   distinto) resta intatto — usa ancora coppie direzionate a ragion veduta.
> - `backend/app/services/portfolio_allocation_source.py`: `_fx_key()` ridotto a un
>   solo argomento `pair` (rimossa sentinella `"identity"`); `_build_planner_fx_quotes()`
>   riscritta senza inversione né sintesi identity-row (la tabella `FxRate` impone già
>   `base < quote` alfabetico, quindi la coppia canonica combacia sempre con l'ordine
>   di storage — mai serve invertire). `_normalized_fx_pair()`/`_load_latest_planner_fx_rows()`
>   restano invariate (condivise col path WAC, ancora direzionato).
> - I codici issue `allocation.saved_fx_missing`/`allocation.saved_fx_invalid` restano
>   invariati (non rinominati a `fx_rate_*`): riguardano l'assenza di dati storici per il
>   prefill, concetto distinto dalla validazione lato planner.
> - Difetto trovato e corretto durante la riconciliazione test (test-author): la
>   validazione precedente chiamava `.partition("/")` prima di controllare il tipo, per
>   cui un elemento non-stringa in `fx_pairs` (es. `True`) sollevava un `AttributeError`
>   non gestito invece di un `ValidationError` pulito — stessa classe di bug del
>   `CurrencyCode` esistente (`Currency.validate_code` già fa il check `isinstance`).
>   Aggiunto `if not isinstance(value, str): raise ValueError(...)` in testa a
>   `_validate_canonical_fx_pair`; riverificato con un caso diretto (`fx_pairs=[True]`)
>   → ora `ValidationError` pulito, non più crash.
> - Test: riconciliati interamente da test-author (69/69 verdi, stabili su fresh-run/
>   re-run/`--workers 4`); rinominati/ridisegnati 2 test sul nuovo modello canonico;
>   nessun altro file toccato dal test-author.
> - Gate finali su tutto il set W2 (schema+service+test): ruff/black/py_compile puliti
>   sui 3 file; `services portfolio-allocation-source` 69/69; `schemas pac-planner`
>   448/448; `schemas pac-analyze` (P1) 112/112 — nessuna regressione; `git diff --check`
>   pulito, 0 staged, HEAD invariato `958527e0`, porta 6153 libera.
> - Item 6 lasciato `[ ]`: questo intervento copre solo la porzione FX del layer
>   prefill, non l'intero perimetro auth/missing/provenance/no-side-effect del
>   dispatch `domain-copy-tests` originale.

- [ ] 7. Rigenerare client tramite writer integrazione.
- [ ] 8. Implementare source-copy client e lifecycle.
- [ ] 9. Collegare pulsanti indipendenti nella shell.
- [ ] 10. Review auth/privacy e checkpoint.

Selector:

```text
services portfolio-allocation-source
front-utility component-unit
```

I selector Playwright `front-utility pac-tool` e
`front-utility rebalancer-tool` restano vietati fino al doppio `APPROVED`
della review umana in Step 5.

> **Note implementazione — W2 2026-09-16**: baseline riconciliata su
> `22cb18d1d60c8b1197627e6e8eff9cb55f001d3e`; i tre path esclusivi sono
> `schemas/portfolio.py`, `services/portfolio_allocation_source.py` e
> `api/v1/portfolio_api.py`. Implementati endpoint read-only/no-store,
> preflight OWNER atomico senza bypass admin, fatti saved-only exact,
> custody/economic separation, CLDR quantum, identity FX, WAC con fiscal
> currency nullable/prove FX e auth del legacy `/portfolio/wac`.
> Ruff format/lint, compile, schema/OpenAPI smoke e diff-check statici verdi.

> **Note implementazione — test gate 2026-09-16**: test-author dedicato
> autorizzato sull'intera matrice schema/service/API/auth/privacy/side-effect.
> `D-main` registrerà il solo selector mancante
> `services portfolio-allocation-source`; `api portfolio` resta il selector API.

## 11. Stop conditions

- serve modificare FIFO/WAC o schema DB;
- manca un principal check standard;
- un endpoint di prezzo ha side effect;
- il dato richiede provider I/O durante compute;
- non è possibile distinguere custodia/quota economica;
- una response parziale nasconderebbe entità non autorizzate;
- la UI dovrebbe ricostruire PMC, FX o valore.

Ogni caso torna al coordinator; nessuna scorciatoia.

## 12. Definition of Done

- audit fatto→source completo;
- sole estensioni necessarie;
- manual scenario ancora indipendente;
- sei copy action indipendenti;
- canonical identity e multi-custody corretti;
- cash nativo e contributi separati;
- prezzi/FX con provenance/staleness;
- auth fail-closed;
- zero side effect;
- stale-response protection verificata;
- CP3 domain-copy pronto e porta libera.

→ Step 5: [Frontend e review umana](plan-phase00Step5PacRebalancerFrontendReview.prompt.md)
