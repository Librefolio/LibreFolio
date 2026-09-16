# Step 1 — contratti pubblici, dipendenza SCIP e capacità

**Stato:** PENDING PRODUCT AUTHORIZATION.
**Dipende da:** planning checkpoint, autorizzazione prodotto, handshake gruppo C.
**Blocca:** core, shell frontend, solver e client generato.

← Master: [piano implementativo](plan-phase00PacRebalancerImplementation.prompt.md)
← Autorità: [target](../plan-phase00PacRebalancerTargetDesign.prompt.md) ·
[architettura](../plan-phase00PacRebalancerArchitecture.prompt.md)

## 1. Scopo

Congelare prima del codice downstream:

1. handshake con la piattaforma Tool;
2. schema pubblico strict e comprensibile anche da un agente MCP;
3. fixture canoniche;
4. limiti input/output misurati sul prodotto reale;
5. update PySCIPOpt developer-owned;
6. dominio di capacità supportato da SCIP entro il runtime Tool.

Non si usa il vecchio witness audit da circa 289 KB come autorità. Il contratto
nasce dalle tabelle e dagli stati UI approvati.

## 2. Ownership

| Tipo | Percorso/oggetto | Writer |
|---|---|---|
| esclusivo | nuovi DTO in `backend/app/schemas/pac_allocator.py` | contract owner |
| esclusivo | fixture JSON request/result PAC/Rebalancer | contract owner |
| esclusivo | diagnostics capacity PAC/Rebalancer | capacity owner |
| shared | plugin descriptor/service registration | integration owner |
| shared/generated | OpenAPI/JSON Schema/TypeScript client | integration owner |
| developer-only | `Pipfile`, `Pipfile.lock` | developer |

Il contract owner non modifica registry/router generici del gruppo C. I DTO
P1 importati da plugin/test restano additivi e compatibili fino al checkpoint
integrazione CP5; vengono rimossi insieme ai consumer legacy dal solo
integration owner, evitando errori di collection intermedi.

## 3. Handshake gruppo C

Congelare in una tabella firmata dal coordinator:

| Voce | Decisione richiesta |
|---|---|
| service IDs | PAC e Rebalancer distinti e stabili |
| operation | `plan`, non `analyze` |
| schema/service version | bump esplicito e compatibilità non implicita |
| worker entry | funzione importabile e serializzabile |
| renderer key | chiave compilata esatta |
| compute | endpoint bulk autenticato; Tool ripetibili e ID distinti |
| diagnostics | admin-only; nessun dato personale |
| issue codes | namespace stabile, severity e path |
| limits | parameter `131072 B`, result `262144 B`, soft `4 s`, hard `5 s` |
| cancellation | `context.checkpoint()` e cleanup worker |
| generated code | comando ufficiale e writer unico |

Non aggiungere endpoint schema specifici o `/tools/prefill`.

## 4. Wire input

### 4.1 Principi

- root object, `extra="forbid"`;
- object union discriminata, mai tuple posizionali;
- decimal/quantity/rate come stringhe finite;
- ID stabili e reference esplicite;
- unità nel nome o nel type;
- tabelle piatte per Asset, holding, cash, Broker, route e FX;
- nesting solo per dati davvero inseparabili;
- scenario manuale senza ID database valido;
- nessun default economico nascosto;
- nessun campo derivato che il backend possa calcolare senza ambiguità.

### 4.2 Famiglie richieste

```text
PlannerRequest
├── operation = "plan"
├── valuation_currency
├── as_of / source metadata
├── assets[]
├── brokers[]
├── holdings[]
├── existing_cash[]
├── contributions[]
├── order_routes[]
├── fx_routes[]
├── target_weights[]
├── policy
└── solver_budget
```

Ogni riga deve dichiarare:

- ID canonico e foreign key;
- currency/unit;
- provenance quando copiata;
- valore esatto come stringa;
- constraint BUY/SELL separati;
- semantica minimo `required` oppure `if_active`;
- instruction `whole_quantity` oppure `monetary_amount`;
- step/quantum esplicito.

Le famiglie economiche interessate dichiarano inoltre i campi seguenti, senza
default impliciti:

- prezzo sorgente, currency, `quote_base_quantity`, source, as-of e staleness;
- margine esecuzione BUY e SELL per route, incluso zero esplicito;
- fee BUY e SELL per Broker con fixed/rate/floor/cap;
- PMC con valuta fiscale e `withholding_kind`;
- tax rate per Asset;
- fee, spread e buffer delle route FX.

Cash esistente e nuovi contributi sono collezioni diverse. Il cash è
Broker×valuta o sorgente×valuta; non viene aggregato in una cassa convertita.

### 4.3 Prodotti

- PAC: holding iniziali assenti o zero; SELL vietato.
- Rebalancer: holding iniziali obbligatorie e aggregate per identità Asset
  canonica; custodia Broker preservata.
- Un'unica request può mescolare route whole e monetary.
- La quota economica personale è separata dalla quantità custodita intera.

## 5. Wire output

```text
PlannerResult
├── availability
├── outcome / proof / stop_reason
├── scenario_basis
├── primary_solution
├── optional_deployment_solution
├── issues[]
└── provenance
```

Il risultato è product-shaped:

- Asset allocation completa;
- before/target/after e residui;
- esposizioni aggregate;
- funding actions;
- FX actions;
- Broker order rows;
- ledger Broker×valuta;
- cost/fee/tax/reserve totals;
- `F_ref`, `F_final`, `U`, `L2_fixed`;
- confronto e delta variante;
- proof e stop facts.

Entrambe le soluzioni espongono stato finale autorevole completo. È ammesso
condividere una base immutabile o riferimenti ID; il frontend non applica delta
per ricostruire denaro, quantità, ledger o obiettivi.

Issue:

- object tipizzato compatto;
- `code`, `severity`, `path`, `message_key`, `params`;
- nessuna stack trace o payload personale;
- ordine deterministico.

## 6. Status e proof

Congelare una union discriminata, non un record con opzionali arbitrari:

```text
PlannerResult =
    NeedsInputResult
  | InvalidResult
  | UnsupportedResult
  | ReadyNoOpResult
  | ReadyIncumbentResult
  | ReadyInfeasibleResult
  | ReadyNoIncumbentResult
```

Ogni variante possiede un discriminante letterale e soltanto i campi validi
per quello stato. Invarianti:

```text
availability = needs_input | invalid | unsupported | ready
outcome      = no_op | incumbent_found | infeasible_proven | no_incumbent
proof        = optimal_proven | gap_bounded | not_proven | infeasibility_proven
proof_source = exhaustive_oracle | score_lattice_closure | deterministic_conflict
stop_reason  = completed | time_limit | node_limit | cancelled | resource_limit
```

- `outcome` esiste solo per `ready`;
- ogni piano pubblicato ha `decimal_verified`;
- `completed` è stop reason, non prova;
- floating `optimal`/`infeasible` non viene promosso;
- i campi non applicabili sono esclusi dalla variante; nullable è ammesso solo
  per un fatto semanticamente nullable, verificato nel TypeScript generato;
- `SELL_IRREDUCIBILITY_UNRESOLVED` è un issue code stabile prima del freeze.

## 7. Esercizio MCP

Senza leggere codice o docs esterne, un reviewer riceve soltanto JSON Schema e
deve costruire:

1. PAC minimo manuale, una valuta, una route whole;
2. PAC misto whole + monetary, più Broker;
3. Rebalancer multi-custody con `invest_only`;
4. Rebalancer `invest_and_sell` con fee/tax;
5. scenario con contributo separato dal cash;
6. scenario FX;
7. input invalid, missing, unsupported.

Almeno una request usa margine BUY non zero e una fee con floor/cap; almeno una
SELL monetary dichiara importo lordo richiesto, PMC, tax rate e withholding.

Acceptance:

- tutti gli input validi passano il vero TypeAdapter;
- gli invalidi producono codici/path leggibili;
- nessuna domanda richiede conoscenza del DB LibreFolio;
- nessun campo duplicato o ambiguo sopravvive per comodità interna;
- schema e TypeScript preservano discriminanti e precisione.
- nessun campo economico obbligatorio richiede un default implicito.

## 8. Payload witness

### 8.1 Misure

Per request e result:

- JSON UTF-8 compatto e pretty;
- schema export;
- totale per sezione top-level;
- conteggio righe e cardinalità;
- primary vs deployment;
- issues worst valid;
- provenienza;
- percentuale di headroom.

### 8.2 Gate

- input `<=131072 B`;
- ogni result `<=262144 B`;
- target ingegneristico: almeno 15% di headroom, salvo decisione developer
  esplicita su un witness product-shaped;
- nessuna compressione/base64;
- nessuna paginazione o secondo lookup;
- nessuna omissione di fatti finanziari obbligatori;
- nessun ricalcolo finanziario frontend;
- nessuna riduzione silenziosa del dominio.

Se il witness supera il target:

1. eliminare duplicazione non semantica;
2. condividere cataloghi immutabili e ID;
3. mantenere finali autorevoli completi;
4. quantificare ogni eventuale compromesso di cardinalità;
5. chiedere decisione developer.

## 9. Update PySCIPOpt developer-owned

Con tutte le lane ferme:

```text
PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc \
pipenv install pyscipopt==<versione-approvata>
```

Il developer:

1. seleziona una versione compatibile Python 3.13/macOS/Linux/container;
2. aggiorna `Pipfile` e `Pipfile.lock`;
3. registra hash lock e versioni Python/PySCIPOpt/SCIP;
4. riapre le lane soltanto dopo verifica import.

Gli agenti non installano, non creano venv e non modificano lock.

## 10. Capacity probe

Corpus:

| Famiglia | Asset | Broker | Route | Valute | Scopo |
|---|---:|---:|---:|---:|---|
| oracle-xs | 1–4 | 1–2 | 1–8 | 1–2 | confronto esaustivo |
| small | 8 | 2 | 16 | 2 | tutte le policy |
| medium | 16 | 4 | 32 | 4 | fee/FX/activation |
| candidate-max | dal contract | dal contract | dal contract | dal contract | cap pubblico |
| sell-stress | cap SELL | cap Broker | cap route | multi | controfattuali |

Misurare:

- import cold/warm;
- build MIQP e MIQCP;
- tempo per tier;
- node count/gap;
- replay exact;
- oracle/closure;
- report serialize/revalidate;
- wall totale;
- peak RSS;
- cancel latency;
- cleanup thread/process/file;
- wheel e container.

Eseguire inoltre il bulk envelope reale:

- `max_batch_items=4`;
- `workers=2`;
- `queue_timeout_ms=5000`;
- `job_timeout_ms=5000`;
- quattro item candidate-max con service ID distinti/ripetuti;
- tempi di attesa, esecuzione, timeout e cleanup per ogni item.

Il dominio pubblico viene congelato soltanto se candidate-max rispetta soft
`4 s` e hard `5 s` con margine operativo. In caso contrario si torna al
developer con dati, non con fallback.

## 11. Sequenza esecutiva

- [ ] 1. Verificare baseline, G1 e handshake C.
- [ ] 2. Inventariare P1 e rimuovere assunzioni wire obsolete dal design DTO.
- [ ] 3. Aggiungere input/output strict mantenendo import P1 collezionabili
      fino alla rimozione atomica a CP5.
- [ ] 4. Generare JSON Schema e TypeScript; diff semantico.
- [ ] 5. Eseguire esercizio MCP.
- [ ] 6. Costruire witness min/medium/max e breakdown deterministico.
- [ ] 7. Ottenere update dipendenza developer-owned.
- [ ] 8. Eseguire probe SCIP/capacity nella lane.
- [ ] 9. Eseguire probe bulk 4-item/2-worker e congelare cardinalità,
      envelope, versioni, codici e fingerprint.
- [ ] 10. Ottenere review schema, auth e capacity.

Dopo ogni step aggiornare immediatamente questo file con data, nota,
evidenza e fuori-pista.

## 12. Definition of Done

- handshake C firmato;
- schema strict, semplice, generated-client compatible;
- fixture PAC/Rebalancer complete;
- collection P1 preservata fino alla rimozione atomica CP5;
- esercizio MCP superato;
- witness sotto limiti con headroom riportata;
- update lock developer-owned verificato;
- MIQP/MIQCP/bulk/cancel/cleanup/packaging misurati;
- dominio pubblico supportato dichiarato;
- nessun codice downstream usa DTO non congelati;
- checkpoint CP1 pronto e porta `6153` libera.

→ Step 2: [Core esatto e oracle](plan-phase00Step2PacRebalancerExactCore.prompt.md)
