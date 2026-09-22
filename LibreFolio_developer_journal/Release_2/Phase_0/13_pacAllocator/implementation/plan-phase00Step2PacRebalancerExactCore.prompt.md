# Step 2 — normalizzazione, aritmetica esatta, evaluator e oracle

**Stato:** IN PROGRESS — W1 MODELS/ISSUES/NORMALIZER CHECKPOINT VERIFIED, READY FOR SELECTIVE HANDOFF; EVALUATOR/ORACLE FROZEN.
**Dipende da:** Step 1 MCP review + payload witness.
**Non dipende da:** disponibilità del solver durante la prima slice.

← Master: [piano implementativo](plan-phase00PacRebalancerImplementation.prompt.md)
← Precedente: [contratti e capacità](plan-phase00Step1PacRebalancerContractsCapacity.prompt.md)
← Autorità: [nucleo matematico](../plan-phase00PacRebalancerMathematicalCore.prompt.md) ·
[policy](../plan-phase00PacRebalancerPolicies.prompt.md)

## 1. Scopo

Costruire una verità matematica indipendente da SCIP:

- scenario immutabile normalizzato;
- `ExactRatio` e posting monetari deterministici;
- ledger, fee, FX, tax e inventario;
- evaluator di constraint e tuple lessicografiche;
- oracle esaustivo completo per domini piccoli.

Il solver futuro propone candidati; questo core decide se sono validi e come
si ordinano.

## 2. Ownership

Percorsi previsti esclusivi:

```text
backend/app/services/pac_allocator/models.py
backend/app/services/pac_allocator/numeric.py
backend/app/services/pac_allocator/normalize.py
backend/app/services/pac_allocator/ledger.py
backend/app/services/pac_allocator/evaluator.py
backend/app/services/pac_allocator/oracle.py
backend/app/services/pac_allocator/issues.py
```

Test previsti, scritti da `test-author`:

```text
backend/test_scripts/test_services/test_pac_planner_exact.py
backend/test_scripts/test_services/test_pac_planner_evaluator.py
backend/test_scripts/test_services/test_pac_planner_oracle.py
```

Nessun modulo del core importa PySCIPOpt, DB, provider, HTTP o frontend DTO
generati.

### 2.1 Slice A autorizzata prima di G3 — 2026-09-16

Lease writer temporanea:

```text
backend/app/services/pac_allocator/numeric.py
```

È ammessa soltanto implementazione additiva di:

- `ExactRatio` canonico e errori aritmetici tipizzati;
- conversione lossless da `Decimal` finito;
- ordinamento via cross-product e proiezione Decimal esatta;
- posting signed `ROUND_HALF_UP` su quantum esplicito, con rounding delta;
- ceil-to-quantum units;
- formule pure fee/effective-FX/tax con input completi caller-supplied.

Non sono ancora autorizzati `models.py`, `issues.py`, normalizer, ledger
strutturale, evaluator, oracle, report, export, schema pubblico, PySCIPOpt,
DB/API, test o runner. Il currency minor-unit source resta esterno: Slice A
riceve sempre il quantum esplicito.

> **Note implementazione**: analisi Fleet `fleet-exact-core`
> (`406804e6-ef88-43d3-b6c5-1aa1c70775d8`) accettata dal coordinator.
> Confermati gap P1: nessun ratio non terminante, posting HALF_UP, ledger
> Broker×currency, fee/FX/tax, fixed-L2, evaluator o oracle target. Le API P1
> restano importabili e invarianti fino a CP5.
>
> **Note implementazione — Slice A 2026-09-16**: codice numerico additivo
> completato nella lease; test/property test restano assegnati a `test-author`.
> **Evidenza**: `git diff --check` completato con exit `0`; nessun runtime,
> test, server, probe o dependency command eseguito.

## 3. `ExactRatio`

Implementare tipo canonico:

```text
ExactRatio(numerator: int, denominator: positive int)
```

Invarianti:

- riduzione con GCD;
- segno sul numeratore;
- zero canonico `0/1`;
- parsing da stringa Decimal finita lossless;
- nessun percorso via `float`;
- `+`, `-`, `*`, `/`, confronto e ordinamento tramite interi;
- serializzazione stabile;
- limite esplicito su lunghezza/coefficient envelope;
- errore tipizzato per NaN, Infinity, zero denominator e overflow policy.

Le divisioni non terminanti restano rapporti. Decimal viene usato per I/O e
posting, non come context implicito di ranking/proof.

## 4. Normalizzazione

Ordine:

1. validare shape e discriminanti;
2. canonicalizzare ID e ordinamento;
3. parsare stringhe numeriche;
4. verificare currency/minor units;
5. unire riferimenti Asset/Broker/route senza deduplicazione silenziosa;
6. separare holding, existing cash e contribution;
7. costruire prezzi mid/charge/sell e quote basis;
8. costruire griglie whole/monetary;
9. applicare permessi/cap/minimi;
10. costruire grafo FX single-hop;
11. derivare route BUY/SELL;
12. classificare cash reachable/trapped;
13. derivare bound finiti;
14. produrre scenario immutabile e issue ordinate.

Errori:

- fatto mancante → `needs_input`;
- contraddizione/referenza invalida → `invalid`;
- scenario valido fuori envelope v1 → `unsupported`;
- nessun Asset/prezzo/FX viene omesso per rendere il caso risolvibile;
- Rebalancer con `V0 <= 0` → `needs_input` con redirect esplicito al PAC;
  ogni candidato Rebalancer richiede inoltre `F_final > 0`.

## 5. Unità e order instruction

Per route:

```text
whole_quantity:
  decision quantum = 1 quota
  existing fractional inventory remains exact

monetary_amount:
  decision quantum = order_amount_step in native currency
  BUY acquired quantity = ExactRatio(posted notional) / charge_price(route)
  SELL quantity = requested gross credit / sell_price(route)
```

Minimo e cap dichiarano:

- lato BUY/SELL;
- unità quantity/notional;
- `required` oppure `if_active`;
- valore esatto.

Non arrotondare inventario frazionario al passo del nuovo ordine. Per SELL
monetary, la quantità derivata resta limitata dall'inventario e l'importo è il
credito lordo richiesto; non esiste `sell_all` implicito.

## 6. Prezzi, fee, FX e tax

Prezzi:

- mid per valorizzazione;
- charge per debito BUY;
- sell per credito SELL;
- `sell <= mid <= charge`;
- `quote_base_quantity` applicata una volta.

Fee per lato:

```text
fee(N) = 0                                      if N = 0
fee(N) = fixed + min(max(rate*N, floor), cap)  if N > 0
```

FX:

```text
effective_rate = approved_rate * (1 - spread)
credit = ROUND_HALF_UP(source_debit * effective_rate, target_minor_unit)
```

- debit/credit accoppiati;
- fee e buffer separati;
- coppie dichiarate;
- single-hop;
- nessun ciclo attivo.

Tax SELL:

```text
taxable_gain =
  max(gross_sell_proceeds - sell_fee - sold_quantity * PMC, 0)

tax_reserve =
  ROUND_HALF_UP(taxable_gain * asset_tax_rate, currency_minor_unit)
```

`broker_withheld` esce dal conto. `self_reserved` resta fisico ma non
spendibile. Nessuna compensazione minus automatica.

## 7. Ledger

Per Broker×valuta:

```text
spendable_final =
    selected_initial_cash
  + inbound_transfers
  + fx_credits
  + gross_sell_proceeds
  - outbound_transfers
  - fx_debits
  - buy_notional
  - buy_fees
  - sell_fees
  - broker_withheld_tax
  - self_reserved_tax
  - fx_fees
  - fx_buffer
```

```text
physical_final =
  spendable_final + self_reserved_tax + fx_buffer
```

Vincoli:

- ogni posting una volta;
- funding/contribution non duplicati;
- provento SELL lordo accreditato una volta;
- fee/tax sottratte una volta;
- `spendable_final >= 0`;
- riconciliazione per riga e globale;
- nessun costo contato come investimento.

## 8. Holding e nonnegatività

```text
h_final[asset, broker] =
  h_initial + buy_quantity - sell_quantity
```

Hard:

- `h_final >= 0` per Broker×Asset;
- `V_final >= 0` per Asset aggregato;
- SELL non oltre inventario;
- nessun BUY+SELL sullo stesso Asset nel candidato;
- nessuno short o leva;
- identità Asset canonica aggrega Broker diversi;
- custodia e quota economica restano fatti distinti.

## 9. Fixed reference

```text
F_ref = V0 + K_reachable
T_a = w_a * F_ref
r_a = V_final_a - T_a
L2_fixed = sum_a r_a^2
F_final = sum_a V_final_a
U = F_ref - F_final
```

- PAC: `V0 = 0`;
- Rebalancer: `V0` è il valore mid iniziale investito;
- cash strutturalmente unreachable è `K_trapped`;
- cash sotto minimo ma raggiungibile resta in `F_ref` e riappare in `U`;
- fee/spread/tax/buffer non si sottraggono da `F_ref`;
- proventi SELL non aumentano `F_ref`;
- `L2_fixed` ha unità valuation-currency²;
- percentuali, `Dinf`, `D1` sono diagnostici.

Identità:

```text
sum_a r_a = -U
L2_fixed >= U^2 / count(assets)
U = free_cash + physical_reserves + economic_losses + rounding_adjustment
```

Un `U < 0` è ammesso soltanto entro il bound deterministico di rounding.

## 10. Evaluator

Input: scenario + candidate actions.
Output:

- posting canonici;
- holding finali;
- ledger;
- constraint results con code/path;
- objective tuple exact;
- Asset/Broker/FX facts per reporter;
- candidate validity.

L'evaluator:

- non ripara il candidato;
- non usa tolleranza solver;
- non classifica proof globale;
- ordina righe e issue deterministicamente;
- rifiuta azioni extra, duplicate o fuori griglia;
- verifica ogni constraint compilata;
- verifica freeze primario della variante.

## 11. Oracle esaustivo

L'oracle:

1. enumera l'intero dominio finito di funding, FX, BUY e SELL ammessi;
2. include activation, fee, minimi e cap;
3. valuta ogni candidato col vero evaluator;
4. confronta tuple lessicografiche esatte;
5. produce optimum/infeasible witness completo;
6. non chiama compiler search o solver;
7. non è un algoritmo add-only mascherato.

Dominio oracle:

- 1–4 Asset;
- 1–2 Broker;
- 1–8 route;
- 1–2 valute;
- bound quantum piccoli ma completi.

Casi obbligatori:

- whole, monetary e misti;
- contributi/cash;
- FX/fee/tax;
- no-op/infeasible;
- min required/if-active;
- inventory frazionario;
- BUY/SELL conflict;
- budget basso;
- permutazione ID;
- tutte le policy con gli stessi input normalizzati;
- sequenza Rebalancer `invest_only -> invest_and_sell`;
- variante BUY-only con freeze primario;
- caso promotion/restart quando la variante domina un primario non provato.

## 12. Sequenza

- [x] 1. Congelare modelli interni immutabili. — 2026-09-16
  > **Note implementazione — Slice W1/G3**: aggiunti in modo esclusivamente
  > additivo i fatti normalizzati esatti e immutabili per snapshot, provenance,
  > valute, Asset, Broker, holding/cash/contributi, route funding/order/FX,
  > target e contesto SELL. Congelata inoltre la frontiera data-only
  > solver-neutral accettata nell'handshake W0/W1 (`ExactUnit`, ref
  > decision/constraint/objective/tie/proof/gate, policy view, candidate ed
  > evaluation), con quanta decisionali interi e unità monetarie sempre
  > qualificate dalla valuta. I modelli P1 e le relative import restano
  > invariati.
  > **Evidenza**: review statica di
  > `backend/app/services/pac_allocator/models.py`; nessun test, server, probe,
  > install o comando runtime eseguito per la lane serializzata D-main.
  > **⚠️ Fuori pista — riallineamento W0**: la seconda lettura field-by-field
  > del wire congelato ha corretto lo scaffold prima del normalizer: policy PAC
  > mantenuta come `proportional|min_fragmentation`, capability/FX mode e
  > minimum/cap usano i discriminanti W0, entrambe le minimum order restano
  > distinte e i fatti label/source/reference-date/withholding non vengono
  > persi. Nessuna API P1 né comportamento eseguibile è stato modificato.
- [ ] 2. Implementare e property-testare `ExactRatio`.
  - [x] 2A. Implementare kernel additivo `ExactRatio`. — 2026-09-16
  - [ ] 2B. Property test tramite `test-author`.
  > **Note implementazione**: aggiunti rapporto canonico GCD/sign/zero,
  > conversione lossless da `Decimal` finito, aritmetica e confronto
  > cross-product interi, serializzazione frazionaria stabile e proiezione
  > `Decimal` soltanto per denominatori terminanti. Le API P1 sono rimaste
  > invariate.
  > **Evidenza**: review statica di
  > `backend/app/services/pac_allocator/numeric.py`; nessun comando runtime o
  > test eseguito perché non autorizzato. Envelope di lunghezza/coefficienti
  > e relativo errore overflow tipizzato restano intenzionalmente rinviati al
  > freeze G3/G5: Slice A non dichiara completato tale invariante.
  > **⚠️ Fuori pista**: la review statica ha rilevato che l'uguaglianza
  > supportata con `int` richiede hash coerente; `ExactRatio(n, 1)` ora usa lo
  > stesso hash di `n`.
  > **⚠️ Fuori pista — formattazione selettiva 2026-09-16**: il checkpoint
  > selettivo ha trovato Ruff verde ma Black non conforme su
  > `backend/app/services/pac_allocator/numeric.py`. Su autorizzazione del
  > coordinator, il numeric owner ha eseguito esclusivamente
  > `PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python -m black backend/app/services/pac_allocator/numeric.py`;
  > Black ha riformattato un file. Nessuna modifica comportamentale/API/test;
  > verifiche scoped finali verdi con
  > `PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python -m ruff check backend/app/services/pac_allocator/numeric.py`,
  > `PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python -m black --check backend/app/services/pac_allocator/numeric.py`
  > e
  > `git --no-pager diff --check -- backend/app/services/pac_allocator/numeric.py`.
  > Nessun test o comando runtime eseguito; D-main riesegue i selector.
  > **Evidenza aggiuntiva del checkpoint**: il controllo Black whole-file
  > segnala anche `scripts/test_runner/_backend_services.py`, ma `black --diff`
  > modifica soltanto righe preesistenti e non correlate intorno alla 956; la
  > copia del file a baseline `HEAD` è identicamente Black-red e la hunk del
  > selector non compare nel formatter diff. Il runner è D-main-owned, non è
  > stato modificato da questo workstream e D-main documenterà l'eccezione di
  > baseline.
- [x] 3. Implementare normalizer e issue taxonomy. — 2026-09-16
  - [x] 3A. Congelare taxonomy interna completa e precedenza. — 2026-09-16
  - [x] 3B. Implementare normalizer v2. — 2026-09-16
  - [x] 3C. Completare test normalizzati tramite `test-author`. — 2026-09-16
  > **Note implementazione — taxonomy W1/G3**: il nuovo `issues.py` deriva dal
  > `Literal` pubblico l'universo canonico di 89 code e fallisce su drift, ma
  > non inventa default kind/severity per code non prodotti da W1. Ogni issue
  > del normalizer passa invece da una `IssueDefinition` esplicita
  > `w1_normalizer`; una definizione assente fallisce chiusa. Path/param,
  > deduplica e ordine sono tipizzati e deterministici. La precedenza degli
  > errori di input è `needs_input` > `invalid` > `unsupported`; warning/info
  > non controllano availability. I warning source vengono importati e
  > preservati; l'escalation operativa del Broker inattivo aggiunge una nuova
  > issue con lo stesso code, `unsupported/error`, senza mutare il warning e
  > senza riusare `broker_execution_profile_unsupported`.
  > **Evidenza**: review statica di
  > `backend/app/services/pac_allocator/issues.py`; nessun runtime/test eseguito
  > e nessun file W0/shared modificato.
  > **⚠️ Fuori pista — primo lint statico W1**: il comando
  > `PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python -m ruff check backend/app/services/pac_allocator/models.py backend/app/services/pac_allocator/issues.py backend/app/services/pac_allocator/normalize.py`
  > è terminato prima di qualsiasi collection/runtime con exit `1`: un import
  > block da ordinare, un loop variable inutilizzato, due closure B023 e sei
  > segnalazioni C901 nei pass di validazione appena aggiunti. Nessun DB, file
  > dati o server è stato toccato; i pass complessi vengono ora scomposti prima
  > del nuovo check, senza suppressions globali.
  > **⚠️ Fuori pista — Black W1**: il successivo
  > `PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python -m black --check backend/app/services/pac_allocator/models.py backend/app/services/pac_allocator/issues.py backend/app/services/pac_allocator/normalize.py`
  > ha segnalato soltanto `normalize.py` da riformattare (exit `1`, nessun file
  > toccato). È stato quindi applicato Black esclusivamente ai tre file leased
  > con lo stesso prefisso ambiente; un solo file riformattato, nessuna modifica
  > comportamentale. Ruff scoped, dopo la scomposizione, è verde.
  > **Note implementazione — normalizer W1/G3**: aggiunti entry point v2
  > separati (`normalize_planner_request`, `normalize_pac_plan`,
  > `normalize_rebalancer_plan`) senza alterare `normalize_pac`/
  > `normalize_rebalance` P1. Il mapping `FiniteDecimal|ExactRatio` usa
  > esclusivamente `Decimal` finito e interi; i fatti validi vengono
  > canonizzati in tuple immutabili esatte. I pass coprono ID/reference/
  > provenance/currency, freshness, price/exposure/target, Broker/capability/
  > fee, holding/cash/contribution/funding, order/FX e SELL tax/WAC/
  > withholding. Un warning source per Broker domain inattivo resta
  > non-controlling in sola custodia; capability, route o cash selezionato
  > aggiungono la distinta escalation unsupported/error e il cash inattivo non
  > diventa spendibile. La availability usa precedenza needs_input > invalid >
  > unsupported. Il cap pubblico di 192
  > caratteri per gli interi ExactRatio protegge il confine di mapping senza
  > troncamento; limiti di cardinalità server-side restano il gate G5 e non
  > sono stati inventati qui.
  > **Evidenza statica**:
  > `PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python -m ruff check backend/app/services/pac_allocator/models.py backend/app/services/pac_allocator/issues.py backend/app/services/pac_allocator/normalize.py`
  > e
  > `PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python -m black --check backend/app/services/pac_allocator/models.py backend/app/services/pac_allocator/issues.py backend/app/services/pac_allocator/normalize.py`
  > verdi prima dell'addendum; il confronto shell del catalogue aveva confermato
  > i 89 code pubblici. I check finali devono essere rieseguiti dopo il
  > riallineamento additivo. Nessun test/runtime/server/probe/install eseguito;
  > la lane 6153 resta a D-main.
  > **⚠️ Fuori pista — addendum issue-map 2026-09-16**: una comunicazione W0
  > intermedia ha contraddetto HEAD/relay dichiarando 88 code e classificazione
  > diversa per stale-not-accepted; W1 e `test-author` sono stati congelati e
  > il conflitto è stato escalato. L'addendum autoritativo successivo ha
  > confermato l'universo committed a 89, stale-not-accepted invalid/error,
  > mapping soltanto per producer W1 espliciti, warning source importati e
  > precedenza needs_input→invalid→unsupported→ready. Produzione riallineata
  > senza edit W0. Nel controllo statico del producer map, il primo comando
  > shell ha trovato `rg: command not found` prima dell'analisi; nessun DB,
  > file dati o server toccato. Il retry equivalente con `grep` ha confermato
  > zero code W1 usati senza definizione; le tre definizioni non viste come
  > literal diretti sono due branch dinamici fee/sell-fee e il gate capacity
  > predisposto per G5.
  > **Riconciliazione autoritativa**: il coordinator ha poi fissato come unica
  > autorità il committed HEAD
  > `921ad7eaa05ec463d11e794002ff7557a62ee6ce`; import probe diretto:
  > `PlannerIssueCode=89`, `allocation.planning_quantity_negative` presente,
  > `NotProvenReasonCode` composto esclusivamente da
  > `allocation.exact_proof_not_established` e
  > `portfolio_rebalancer.sell_irreducibility_unresolved`,
  > `allocation.stale_observation_not_accepted=invalid/error`. Il report W0
  > 88/unsupported è formalmente superseded e ritirato. W1 ha ripreso senza
  > modifica di baseline, policy o test.
  > **⚠️ Fuori pista — review duplicati W1 2026-09-16**: una fresh review dopo
  > i selector consolidati D-main (`126/126`, P1 `97/97`) ha rilevato tre
  > invarianti non coperti dal primo checkpoint. Correzione chirurgica:
  > `DomainAssetIdentity.source_asset_id` e
  > `DomainBrokerIdentity.source_broker_id` sono unici indipendentemente dagli
  > ID planner locali; `(dimension, category_id)` è unico per le exposure di
  > un Asset; `(asset_id, broker_id)` è unico per le holding. Ogni collisione
  > usa `allocation.duplicate_id`, path deterministico ancorato all'ID locale
  > minimo e param tipizzati; nessun grouping per alias/nome. Il binding SELL
  > non costruisce più un dict last-wins: le coppie holding ambigue vengono
  > fermate dal duplicate error e non alimentano WAC/inventory diagnostics.
  > `ExactAsset` e `ExactPlannerScenario` replicano gli stessi fail-closed
  > invariants per impedire costruzioni interne non normalizzate. Nessuna
  > modifica a issue policy, W0, P1, evaluator o oracle; runtime non eseguito.
  > **Evidenza review duplicati**: il primo comando scoped Ruff+Black si è
  > fermato prima di Black con exit `1` per il solo `I001` introdotto dagli
  > import dei param tipizzati; nessuna collection/runtime né DB/file
  > dati/server toccato. Applicato il solo safe fix Ruff a `normalize.py`;
  > successivi Ruff scoped su `models.py`/`normalize.py` e Black `--check`
  > sugli stessi file verdi, due file unchanged.
  > **⚠️ Fuori pista — static check test normalizer**: dopo l'handoff
  > `test-author` (13 dichiarazioni/43 casi, nessun test eseguito), il comando
  > `PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python -m ruff check backend/app/services/pac_allocator/models.py backend/app/services/pac_allocator/issues.py backend/app/services/pac_allocator/normalize.py backend/test_scripts/test_services/test_pac_planner_normalize.py`
  > è terminato prima della collection con exit `1`: soltanto nel nuovo file
  > test, `I001`, `B010` e `C901`; nessun DB/file dati/server toccato.
  > Produzione rimasta frozen; il medesimo `test-author` ha ricevuto la
  > correzione statica owner-only, senza creare un nuovo agente e senza
  > autorizzazione runtime.
  > **⚠️ Fuori pista — Black test normalizer**: dopo la correzione owner-only,
  > Ruff scoped è verde ma
  > `PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python -m black --check backend/app/services/pac_allocator/models.py backend/app/services/pac_allocator/issues.py backend/app/services/pac_allocator/normalize.py backend/test_scripts/test_services/test_pac_planner_normalize.py`
  > termina con exit `1` perché riformatterebbe soltanto il nuovo file test; i
  > tre file produzione sono conformi. Nessuna collection/runtime né DB/file
  > dati/server toccato; chiesta allo stesso test owner la sola formattazione
  > scoped.
  > **Note implementazione — test normalizzati**: il `test-author` esistente
  > `pac-numeric-tests` (`2b823683-8a4f-4573-9bbd-3d6ffab7658f`) ha aggiunto
  > esclusivamente
  > `backend/test_scripts/test_services/test_pac_planner_normalize.py`: 13
  > dichiarazioni/43 casi per exact-number mapping, scenario canonico
  > immutabile, universo 89 code e producer map fail-closed, precedenza,
  > source-warning passthrough, freshness, Broker inattivo su tutte le
  > superfici eseguibili, path/range, deduplica deterministica e fixture
  > Rebalancer semanticamente invalida. Nessun test è stato eseguito per
  > assenza di lane grant.
  > **Evidenza finale statica**:
  > `PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python -m ruff check backend/app/services/pac_allocator/models.py backend/app/services/pac_allocator/issues.py backend/app/services/pac_allocator/normalize.py backend/test_scripts/test_services/test_pac_planner_normalize.py`,
  > `PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python -m black --check backend/app/services/pac_allocator/models.py backend/app/services/pac_allocator/issues.py backend/app/services/pac_allocator/normalize.py backend/test_scripts/test_services/test_pac_planner_normalize.py`
  > e `git --no-pager diff --check` verdi. Black: quattro file unchanged.
  > **Evidenza finale D-main — 2026-09-16**: il runner è stato consolidato dal
  > coordinator: una sola action `services pac-planner-core` esegue exact +
  > normalize, senza action normalize duplicata. Risultati:
  > `services pac-planner-core` **137 collected / 137 passed** (83 exact + 54
  > normalize) in **0.53s**; `services pac-analyze` **97/97 passed** in
  > **0.49s**. Ruff scoped su models/issues/normalize/nuovo test/runner verde;
  > Black scoped su models/issues/normalize/nuovo test verde, quattro file
  > unchanged; `git diff --check` whole-worktree verde. Il Black whole-runner
  > resta rosso soltanto sul blocco baseline identico `tools-lifecycle`
  > (`HEAD` circa riga 956, worktree circa riga 988), estraneo a W1; la hunk
  > PAC consolidata non compare nel formatter diff. Il primo post-test Black
  > rosso e la correzione owner-only sono registrati sopra.
  >
  > **Review finale read-only**: CLEAN dopo i fix. Confermati tuple
  > immutabili/canoniche e unicità semantiche; mapping ExactNumber lossless via
  > Decimal/interi; universo 89 code con producer map esplicita fail-closed;
  > warning importati preservati e non controlling; escalation Broker inattivo
  > distinta per capability/funding/FX/BUY/SELL/cash selezionato; precedenza
  > needs_input > invalid > unsupported; pass completi reference/FK/duplicate
  > inclusa assenza di binding SELL ambiguo. I body P1 sono invariati
  > (soltanto import e blocchi v2 additivi) e il core non importa solver, DB,
  > provider o rete. Checkpoint W1 pronto per handoff selettivo; evaluator e
  > oracle restano esplicitamente frozen.
- [ ] 4. Implementare posting/rounding.
  - [x] 4A. Implementare posting signed `ROUND_HALF_UP` su quantum esplicito,
        rounding delta e ceil-to-quantum units. — 2026-09-16
  - [x] 4B. Rivalidare baseline, fonti normative e API evaluator/ledger. —
        2026-09-16
  - [x] 4C. Integrare le sette famiglie di posting nel replay evaluator. —
        2026-09-16
  - [ ] 4D. Testare posting/rounding tramite `test-author`.
  > **Note implementazione**: `PostedAmount`, `post_half_up()` e
  > `ceil_to_quantum_units()` operano soltanto su `ExactRatio`; nessuna lookup
  > valuta/default minor-unit è stata introdotta.
  > **Evidenza**: review statica del percorso leased; nessun comando runtime o
  > test eseguito perché non autorizzato.
  > **Note implementazione — avvio ledger/evaluator**: verificati worktree,
  > branch e HEAD `509929ab3e151e796fe5807cb6db77b8fb4480fb` (parent
  > `921ad7eaa05ec463d11e794002ff7557a62ee6ce`), con staged/unmerged `0/0` e
  > superfici W1 leased pulite. Riletti Step 2, Target Design, Mathematical
  > Core, Policies, Architecture e gli attuali `models.py`, `numeric.py`,
  > `normalize.py` ed `evaluator.py`; confermato che `evaluator.py` P1 va
  > esteso solo additivamente e che `ledger.py` non esiste ancora. Congelata
  > la direzione dipendenze: modelli esatti data-only → ledger puro → evaluator
  > puro; nessun import solver/compiler/DB/provider/rete.
  > **⚠️ Fuori pista — graph lookup non disponibile**: `wiki-search` non ha
  > potuto interrogare il grafo perché l'interprete locale
  > `LibreFolio_devWiki/graphify-out/.graphify_python` non è presente. La
  > rivalidazione è proseguita soltanto sui piani e sulle pagine devWiki
  > committed del worktree, senza leggere o copiare artifact da altri
  > checkout.
  > **Note implementazione — integrazione posting 4C**: BUY debit, SELL gross
  > credit, fee BUY/SELL, credito FX, fee FX, buffer FX e tax reserve vengono
  > costruiti da importi exact e postati una volta al quantum della valuta. I
  > flow già discreti (cash iniziale, funding e debito FX) restano a delta
  > zero. Il replay conserva sia il delta raw `posted-exact` sia
  > `A_round` debit-positive/credit-negated.
- [ ] 5. Implementare fee, FX e tax.
  - [x] 5A. Implementare formule numeriche pure fee/effective-FX/credito FX e
        taxable-gain/tax reserve. — 2026-09-16
  - [x] 5B. Collegare formule a route, posting e withholding. — 2026-09-16
  > **Note implementazione**: tutti gli input economici sono obbligatori e
  > caller-supplied; `cap=None` significa soltanto cap percentuale assente.
  > Le formule restituiscono valori esatti pre-posting, quindi il chiamante
  > applicherà una sola volta `post_half_up()` col quantum valuta esplicito.
  > `approved_rate > 0` e `0 <= tax_rate <= 1` sono assunzioni policy correnti
  > da congelare in G3, non nuovi bound pubblici dichiarati da Slice A.
  > **Evidenza**: review statica del percorso leased; nessun comando runtime o
  > test eseguito perché non autorizzato.
  > **Note implementazione — integrazione 5B**: fee per singola route attiva,
  > rate FX diretto destinazione-per-sorgente, spread, fixed fee, buffer,
  > taxable gain non negativo, WAC convertito esplicitamente e withholding
  > `broker_withheld|self_reserved` sono ora collegati senza doppia
  > applicazione. Carried loss resta fatto snapshot non compensato in v1.
- [ ] 6. Implementare ledger e inventory.
  - [x] 6A. Congelare record posting/ledger e riconciliazione nativa pura. —
        2026-09-16
  - [x] 6B. Integrare funding, inventory e vincoli nel replay evaluator. —
        2026-09-16
  > **Note implementazione — ledger 6A**: aggiunto `ledger.py` puro con due
  > ingressi distinti: flow già quantizzati (`initial_selected`, funding e
  > debito FX) a delta zero e famiglie monetarie postate una sola volta con
  > `ROUND_HALF_UP`. Ogni `ExactLedgerPosting` conserva `posted-exact` grezzo;
  > la proprietà accounting mantiene il segno per i debit e lo nega per i
  > credit. La riconciliazione rifiuta ID duplicati, direzioni/famiglie
  > incoerenti e produce righe Broker×valuta canoniche con identità
  > spendibile/fisica esatta. I record data-only additivi in `models.py`
  > rendono espliciti source balance, funding, FX, order, holding, Asset,
  > accounting e costi senza import solver o schema pubblico.
  > **Note implementazione — review posting**: la riconciliazione rivalida ora
  > anche ogni posting monetario costruito direttamente: `posted_amount` e
  > `rounding_delta` devono coincidere con un'unica applicazione signed
  > `ROUND_HALF_UP(exact_amount, quantum)`. Non basta più presentare quantum e
  > delta aritmeticamente coerenti ma non canonici.
  > **Evidenza**: review locale dei soli file leased; Ruff/Black/py_compile
  > restano da eseguire al freeze del sotto-slice, nessun runtime/test/server.
  > **Note implementazione — ledger/inventory 6B**: ogni sorgente conserva
  > `selected = transferred + remaining`; il cash esistente compare una sola
  > volta come saldo Broker e il contributo una sola volta fra residuo esterno
  > e funding in. Le righe native aggregano trasferimenti, FX, ordini,
  > fee/tax/riserve; le holding usano
  > `planning_quantity + BUY - SELL` per Asset×Broker senza rounding quantità.
  > I vincoli exact coprono source capacity/conservation, ledger non negativo,
  > inventario, cap/minimi/required minima, BUY+SELL, grafo FX e riconciliazione.
  > **Note implementazione — review SELL netto**: aggiunto il constraint
  > canonico `SELL_NET_POSITIVE` per ogni route SELL. Una riga inattiva è
  > neutra; una riga attiva è feasible soltanto quando accredito lordo postato
  > meno fee postata e tax reserve postata è strettamente positivo, prima che
  > il ricavo possa finanziare BUY incrementali.
- [x] 7. Implementare fixed-reference/objective facts. — 2026-09-16
  > **Note implementazione**: classificazione strutturale
  > reachable/trapped, `F_ref = V0 + K_reachable`, target monetari fissi,
  > residui, `L2_fixed`, `F_final`, `U`, turnover, costi espliciti,
  > route-priority, split e row count sono ExactRatio. La decomposizione usa
  > cash libero, riserve fisiche, perdite economiche once-only e `A_round`;
  > SELL non aumenta il riferimento.
  > **Note implementazione — review conversioni**: il contract check
  > evaluator verifica ora i riferimenti holding/cash/SELL, valuta e unità di
  > funding, capability/minimi/cap/fee/gross SELL. Una conversione di
  > valorizzazione fra due valute entrambe non-`valuation_currency` viene
  > rifiutata invece di sintetizzare un cross-rate a due gambe; PMC, provento,
  > tax e withholding di una SELL devono chiudere nella stessa valuta fiscale
  > nativa rappresentabile. Le azioni FX restano esclusivamente sulle quote
  > dirette dichiarate. Ogni risultato ordine conserva separatamente valuta e
  > `quote_base_quantity` sorgente dal prezzo mid/esecuzione nella valuta
  > nativa, così il mapper downstream non deve indovinare l'unità del prezzo
  > originale né riapplicare la base.
  > **Note implementazione — review bound BUY**: l'upper bound di ogni BUY è
  > ora il minimo fra cap route e misura acquistabile dal bound globale di
  > risorse raggiungibili, convertito al charge price per capability
  > `whole_quantity` o lasciato in notional per `monetary_amount`. Restano
  > inclusi step, cap, inventario SELL e tolleranza massima dei posting
  > favorevoli su credito **e** debit (cash, fee, tax e buffer per tutte le
  > route potenzialmente attive); nessun Big-M arbitrario e nessun candidato
  > feasible viene tagliato da rounding favorevole.
- [x] 8. Implementare evaluator completo. — 2026-09-16
  > **Note implementazione**: aggiunti `build_exact_policy_view()` ed
  > `evaluate_exact_candidate()` senza modificare i body P1. Le view
  > distinguono primary, baseline invest-only, estensione SELL e deployment:
  > freeze/additive-only sono espressi in `DecisionAccess`. Il replay rifiuta
  > mismatch, decisioni mancanti/extra/duplicate, quanta non interi,
  > accesso/bound violati; valuta ogni `ConstraintRef` canonico, emette
  > conflict code/ref deterministici e produce objective tuple/tie vector
  > esatti. I checkpoint cooperativi coprono costruzione view, replay,
  > posting, ledger, holdings, constraint e objective. Static gate e handoff
  > test restano pendenti.
  > **Note implementazione — review cancellation**: anche scansione
  > quadratica multi-hop e DFS del grafo FX controllano ora il checkpoint a
  > ogni arco/nodo; anche la costruzione dei ref funding/FX/order/
  > position/global controlla ogni riga. Non resta un loop graph o catalogue
  > candidate-dependent senza cooperazione col budget.
  > **Note implementazione — review invarianti data-only**:
  > `ExactPolicyView` porta ora lo scopo di fase esplicito (`primary`,
  > baseline invest-only, SELL extension, deployment) invece di inferirlo
  > dalla forma degli obiettivi; le view non-SELL non possono portare
  > gate/proof SELL e `additive_only` parte esattamente dal baseline
  > congelato; primary e baseline invest-only partono obbligatoriamente dal
  > vettore azioni zero. Lo scenario richiede target per tutti e soli gli Asset
  > normalizzati. `ExactEvaluation` chiude inoltre `feasible`, constraint,
  > conflict catalogue e presenza/assenza del replay economico in un'unica
  > identità immutabile. Anche product/policy e metadata proof/gate
  > (ID, ordine e unicità delle decisioni riaperte/congelate) sono chiusi
  > localmente nei record data-only. Gli stessi record vietano ID fee
  > duplicati nel Broker e ambiguità last-wins su valuta sorgente dei rate di
  > valorizzazione o coppia diretta delle quote FX.
  > Le fasi SELL-off `primary`/`invest_only_baseline` neutralizzano soltanto il
  > `required_minimum` delle route SELL che la policy ha disabilitato; la
  > stessa soglia torna hard nell'estensione SELL. In questo modo una richiesta
  > SELL non rende impossibile la baseline che deve precederla.
  > Prima di aprire `sell_extension`, il builder ricostruisce inoltre la view
  > invest-only con lo stesso `view_id` e richiede che il candidato baseline
  > completo sia exact-feasible; una baseline soltanto formalmente completa
  > ma con ledger/constraint rossi non può determinare eligibility SELL. Per
  > `deployment` resta precondizione dichiarata un primario già verificato.
  > **Note implementazione — review unità constraint**:
  > `ORDER_SIDE_ALLOWED` e `NO_IMPLICIT_ROUTE` dichiarano ora unità booleana;
  > quantizzazione/minimi/cap mantengono invece quantità Asset o moneta nativa.
  > Fact e ref non possono più descrivere lo stesso predicato con dimensioni
  > discordanti. Il boundary evaluator rifiuta inoltre una capability
  > `whole_quantity` con step non intero, evitando istruzioni pubblicabili che
  > il wire `PlannerPositiveWholeDecimal` non potrebbe rappresentare.
  >
  > **Riesame tie totale:** il `TieBreakRef` espone ora gli ID decisionali nel
  > vero ordine canonico semantico (Asset canonico, Broker, valuta, lato, route,
  > con sentinelle stabili per funding/FX), invece di dipendere dall'ordine
  > lessicale accidentale dei prefissi degli ID. `ExactEvaluation` associa
  > esplicitamente lo stesso vettore di ID ai quanta, così il pareggio totale è
  > verificabile senza conoscenza implicita del consumer.
  >
  > **Riesame sequenza SELL:** anche la validazione di una policy view
  > ricostruita riesegue esattamente la baseline invest-only incorporata, non
  > soltanto il builder originale. `SELL_FUNDS_INCREMENTAL_BUY` richiede ora
  > sia almeno un BUY incrementale sia che il medesimo vettore non sia
  > finanziabile azzerando tutte le SELL; ciò chiude sale-to-idle al livello
  > candidato. La necessità di ogni singolo quantum/riga SELL resta
  > correttamente una proof requirement dell'oracle successivo.
  >
  > **Difesa del boundary normalizzato:** il contratto evaluator rifiuta anche
  > snapshot costruiti manualmente che reintroducano funding, FX, ordini o
  > cash selezionato su un Broker domain inattivo. Il normalizer resta il
  > produttore autorevole dell'issue pubblica; questo controllo non muta né
  > duplica la relativa warning/escalation policy. Per funding vengono
  > controllati sia il Broker destinazione sia l'eventuale Broker sorgente del
  > cash esistente, anche quando l'importo selezionato è zero.
  >
  > **Identità delle view baseline-dependent:** gli ID default di
  > `sell_extension` e `deployment` includono l'hash SHA-256 non troncato del
  > vettore baseline canonico. Due baseline economiche diverse dello stesso
  > snapshot/scopo non possono quindi condividere accidentalmente
  > l'identificatore di policy; gli ID espliciti del caller restano ammessi.
  > La validazione baseline controlla direttamente anche molteplicità degli ID
  > e natura intera/non negativa dei quanta prima della conversione a mappa:
  > perfino un record costruito bypassando le dataclass non può ottenere
  > semantica last-wins.
  > I gate/proof SELL vengono emessi soltanto per decisioni eleggibili con
  > dominio finito effettivamente positivo: una route con upper bound zero non
  > crea debito di prova per un'azione impossibile.
  > `fx_mode=native_currency_required` vieta inoltre una route ordine la cui
  > valuta quote Asset differisca dalla valuta capability; soltanto
  > `conversion_allowed` può usare la conversione esatta esplicitamente
  > rappresentabile, senza introdurre FX implicito nel ledger.
  > I constraint `BUY_DEBIT_POSITIVE` e `FX_CREDIT_POSITIVE` impediscono che
  > un'azione con quanta positivi venga arrotondata a un posting autorevole
  > zero: ogni ordine BUY/credito FX feasible resta rappresentabile dai campi
  > pubblici `PlannerPositiveMoneyInput`. SELL usa già il più forte
  > `SELL_NET_POSITIVE`.
  > **⚠️ Fuori pista — primo Ruff ledger/evaluator**: il comando scoped
  > `PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python -m ruff check backend/app/services/pac_allocator/models.py backend/app/services/pac_allocator/numeric.py backend/app/services/pac_allocator/ledger.py backend/app/services/pac_allocator/evaluator.py`
  > è terminato prima di qualunque collection/runtime con exit `1`: un blocco
  > candidato era stato inserito dopo il return finale producendo tre errori
  > syntax, più un `C420` nel ledger e un `C901` nell'invariante
  > `DecisionAccess`. Nessun DB, file dati o server toccato; il blocco è stato
  > ricollocato e i due rilievi statici vengono corretti senza suppression.
  > **⚠️ Fuori pista — secondo Ruff ledger/evaluator**: il retry dello stesso
  > comando scoped è terminato ancora prima di collection/runtime con exit
  > `1`: sintassi corretta, ma restavano import order/unused, un `C420`, due
  > import locali e cinque funzioni C901 (`_build_scenario_index`,
  > `_decision_upper_bounds`, `_build_constraint_refs`, `_constraint_facts`,
  > `build_exact_policy_view`, più la validazione candidato). Nessun DB, file
  > dati o server toccato; il codice viene scomposto in helper deterministici,
  > senza `noqa`.
  > **⚠️ Fuori pista — terzo Ruff ledger/evaluator**: dopo la scomposizione,
  > lo stesso comando scoped è terminato con exit `1` per il solo `I001`
  > residuo (`ExactConflict` fuori ordine); nessuna collection/runtime né
  > artifact toccato. Corretto manualmente il solo import order.
  > **⚠️ Fuori pista — Black ledger/evaluator**: dopo Ruff verde, il comando
  > scoped `PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python -m black --check backend/app/services/pac_allocator/models.py backend/app/services/pac_allocator/numeric.py backend/app/services/pac_allocator/ledger.py backend/app/services/pac_allocator/evaluator.py`
  > è terminato con exit `1`, indicando soltanto `models.py`, `ledger.py` ed
  > `evaluator.py` da riformattare (`numeric.py` unchanged). Nessun
  > runtime/test/DB/file dati/server; verrà applicato Black soltanto ai tre
  > file leased indicati.
  > **⚠️ Fuori pista — Ruff post-review semantica**: il comando scoped Ruff
  > sui quattro moduli exact è terminato prima di collection/runtime con exit
  > `1` per il solo `C901` (`_validate_policy_view`, 11 > 10) introdotto dal
  > controllo canonico completo della view. Nessun DB, file dati, server o
  > artifact toccato; il check viene scomposto in helper senza suppression.
  > **⚠️ Fuori pista — Black post-review semantica**: Ruff scoped è tornato
  > verde, poi lo stesso Black scoped `--check` è terminato con exit `1`
  > indicando esclusivamente `models.py`, `ledger.py`, `evaluator.py`;
  > `numeric.py` resta unchanged. Nessuna collection/runtime/DB/file dati o
  > server. Si applica Black soltanto ai tre file leased e si ripetono
  > entrambi i gate statici.
  > **⚠️ Fuori pista — Ruff final hardening**: il comando scoped Ruff sui
  > quattro moduli exact è terminato prima di collection/runtime con exit `1`:
  > import mancante `CandidateDecision` e due soli `C901` introdotti dal check
  > step intero e dall'integrità referenziale gate/tie. Nessun DB, file dati,
  > server o artifact toccato; i controlli vengono estratti in helper puri
  > senza suppression. Retry dello stesso comando: `All checks passed!`;
  > nessuna collection/runtime/DB/file dati/server.
  > **⚠️ Fuori pista — Black final hardening**: il successivo Black scoped
  > `--check` è terminato prima di runtime/test con exit `1`: riformatterebbe
  > soltanto `models.py` ed `evaluator.py`, mentre `numeric.py` e `ledger.py`
  > restano unchanged. Nessun DB, file dati, server o artifact toccato; Black
  > viene applicato esclusivamente ai due file leased indicati e i gate
  > statici verranno ripetuti. Applicazione scoped: exit `0`, due file
  > riformattati; nessun'altra superficie toccata. Retry finale Ruff:
  > `All checks passed!`; Black `--check`: quattro file unchanged.
  > **⚠️ Fuori pista — Black dopo chiusura output positivo**: Ruff scoped
  > resta verde; Black scoped `--check` termina con exit `1` indicando soltanto
  > `evaluator.py` dopo i nuovi predicati BUY/FX e check inactive-source;
  > altri tre moduli unchanged. Nessuna collection/runtime/DB/file dati/server;
  > applicazione Black limitata al solo evaluator: exit `0`, un file
  > riformattato. Ultimo retry: Ruff `All checks passed!`; Black `--check`
  > quattro file unchanged; `py_compile` exit `0`; diff-check path owned e
  > whole-worktree entrambi exit `0`.
  > **Evidenza statica post-review**:
  > `PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python -m ruff check backend/app/services/pac_allocator/models.py backend/app/services/pac_allocator/numeric.py backend/app/services/pac_allocator/ledger.py backend/app/services/pac_allocator/evaluator.py`
  > → `All checks passed!`;
  > `PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python -m black --check backend/app/services/pac_allocator/models.py backend/app/services/pac_allocator/numeric.py backend/app/services/pac_allocator/ledger.py backend/app/services/pac_allocator/evaluator.py`
  > → quattro file unchanged;
  > `PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python -m py_compile backend/app/services/pac_allocator/models.py backend/app/services/pac_allocator/numeric.py backend/app/services/pac_allocator/ledger.py backend/app/services/pac_allocator/evaluator.py`
  > → exit `0`. Nessun test/runtime/server/DB.
  > **Evidenza finale ledger/evaluator — 2026-09-16**: dopo l'ultimo
  > hardening semantico, Ruff scoped sui quattro moduli exact:
  > `All checks passed!`; Black scoped `--check`: quattro file unchanged;
  > `py_compile` scoped: exit `0`; `git diff --check` sui path owned inclusa
  > questa Step 2: exit `0`; `git diff --check` whole-worktree: exit `0`.
  > Nessun test, server, DB, probe, install o comando runtime di prodotto
  > eseguito; lane D-main `6153`/`/tmp/librefolio-r2-d` mai usata.
  > **Checkpoint selettivo:** simboli produzione ledger/evaluator frozen e
  > pronti per il test-author/D-main. Oracle, compiler/SCIP, mapper/plugin,
  > report e integrazione runner restano esplicitamente bloccati. Manifest
  > owner: tre file tracked modificati (`models.py`, `evaluator.py`, Step 2) e
  > un nuovo file non tracked (`ledger.py`); `numeric.py` invariato.
  > Staged/unmerged `0/0`. `lsof -nP -iTCP:6153 -sTCP:LISTEN` non ha prodotto
  > output (exit `1`): nessun listener sulla lane al freeze. Diff-check
  > whole-worktree finale: exit `0`.
- [x] 8a. Riconciliare il core exact con il wire W0 corretto. ✅ 2026-09-17
  > **⚠️ Fuori pista — correzione contratto W0 2026-09-17:** il commit
  > autorevole `958527e0b0075e921aeb2b5ec739b1762c91ffea` ha rimosso
  > `gross_amount_requested` dal request SELL: il lordo monetario è una
  > decisione del solver pari a quanta interi per `order_amount_step`, non un
  > input o un secondo cap. La riconciliazione è autorizzata prima dei test
  > evaluator; oracle, compiler e plugin restano congelati.
  > **Note implementazione — modello interno:** rimosso
  > `gross_amount_requested` da `ExactOrderRoute` insieme alla relativa
  > validazione. Minimi, cap route, inventario e step capability restano le
  > sole autorità del dominio SELL.
  > **Note implementazione — normalizer:** rimossi validazione e mapping del
  > campo SELL non più rappresentabile. `PlannerWholeQuantityStep` viene
  > convertito losslessly da stringa intera canonica a `ExactRatio`;
  > `allocation.nonpositive_quantity_step` continua a classificare zero e
  > negativi shape-valid. Nessun nuovo issue noninteger viene introdotto.
  > **Note implementazione — evaluator:** rimosso ogni uso del lordo SELL
  > richiesto come validazione o cap aggiuntivo; il dominio monetario usa ora
  > esclusivamente quanta per `order_amount_step`, minimi, cap notional e
  > inventario. `build_exact_policy_view` inoltra il `checkpoint` al catalogo
  > constraint; il tie canonico usa `ExactFundingRoute.broker_id` e risolve le
  > capability tramite `(broker_id, capability_id)`, consentendo ID locali
  > uguali su Broker distinti senza cross-binding. Replay baseline,
  > fingerprint esatto e assenza di proof ereditata restano invariati.
  > **Note implementazione — evidenza statica:** ricerca scoped su
  > `models.py`, `normalize.py`, `evaluator.py` e `ledger.py`: nessun
  > `gross_amount_requested`; nessun accesso
  > `route.destination_broker_id`; tutte le lookup capability di route
  > nell'evaluator sono Broker-qualified. Ruff scoped: `All checks passed!`;
  > Black scoped `--check`: quattro file unchanged; `py_compile` scoped:
  > exit `0`; `git diff --check` sui path W1 e questa Step 2: exit `0`.
  > `ledger.py` non ha richiesto modifiche. Nessun test runtime, server, DB,
  > install, schema, fixture, runner, API, plugin, oracle, SCIP/compiler,
  > generated client o sync eseguito.
  > **Note implementazione — runner D-main:** registrata una sola azione
  > `services pac-planner-evaluator`, isolata dal checkpoint core, che esegue
  > esclusivamente `test_pac_planner_evaluator.py`. Il selector esistente
  > `pac-planner-core` resta limitato a exact+normalize: nessun file test è
  > duplicato fra azioni e le registrazioni concorrenti W2 sono preservate.
  > **Note implementazione — gate evaluator:** comando lane D-main
  > `PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py
  > test --test-port 6153 --data-dir /tmp/librefolio-r2-d services
  > pac-planner-evaluator` → `148/148 passed` in `0.86 s`, exit `0`.
  > Collection, setup DB test isolato e suite completati; nessun server resta
  > in ascolto per questa unità pure.
  > **Note implementazione — regressione core:** comando lane D-main
  > `PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py
  > test --test-port 6153 --data-dir /tmp/librefolio-r2-d services
  > pac-planner-core` → `137/137 passed` in `0.56 s`, exit `0`; exact
  > primitives e normalizer W1 restano verdi dopo la correzione wire.
  > **Note implementazione — regressione P1:** comando lane D-main
  > `PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py
  > test --test-port 6153 --data-dir /tmp/librefolio-r2-d services
  > pac-analyze` → `97/97 passed` in `0.51 s`, exit `0`; P1 coesiste senza
  > regressioni con il core v2. Le tre suite sono state eseguite serialmente
  > sulla sola lane assegnata.
  > **⚠️ Fuori pista — Black runner:** Ruff scoped su produzione, test e
  > runner è verde; Black `--check` sui sei path termina con exit `1` soltanto
  > perché riformatterebbe il blocco preesistente `tools-lifecycle` nel
  > runner condiviso. Il diff Black corrente non contiene né il nuovo selector
  > PAC né la registrazione W2; la stessa identica trasformazione compare
  > applicando la config repo al runner di `HEAD` (linea storica circa 967).
  > Nessun file viene formattato: produzione e test risultano cinque file
  > unchanged, il debito runner resta escluso dal lease.
  > **Note implementazione — statico D-main:** Ruff sui quattro moduli,
  > test evaluator e runner: `All checks passed!`; Black sui cinque path
  > owned produzione/test: unchanged; `py_compile` sui medesimi più runner:
  > exit `0`; whole-worktree `git diff --check`: exit `0`. Porta 6153 libera
  > dopo i gate. Nessun formatter applicato.
  > **⚠️ Fuori pista — review matematica indipendente:** ledger, segni,
  > conservation, decision bounds, obiettivi/L2/U/tie, SELL/WAC/tax,
  > baseline replay/deployment e coesistenza P1 risultano corretti; nessun
  > blocker matematico. La review ha però trovato tre gap correctness
  > non-blocking da chiudere prima del checkpoint: una route cross-currency
  > schema-valid può superare il normalizer e fallire nel boundary evaluator
  > invece di produrre issue tipizzata; `_global_constraint_facts` non inoltra
  > il checkpoint nei suoi scan; la chiave stringa `asset_id:broker_id` può
  > collidere perché `:` è ammesso negli ID. Segnalato inoltre un gap test per
  > funding strutturalmente trapped ma trasferito. La preparazione di un
  > contesto evaluator riusabile è performance work della fase solver/envelope,
  > non una correzione matematica corrente. Produzione/test restano frozen in
  > attesa di autorizzazione coordinator e mapping issue esplicito.
- [x] 8b. Ridisegnare FX/funding su mappa canonica (`fx_rates`+`fx_spread_rate`) e chiudere i tre gap della review. ✅ 2026-09-18
  > **Note implementazione — modello FX/funding:** rimossi `ExactValuationRate`,
  > `ExactFxQuote`, `ExactFxRoute` e il capability `fx_mode`
  > (`native_currency_required`/`conversion_allowed`); introdotto
  > `ExactFxRate` (coppia ordinata alfabeticamente + rate) e
  > `fx_spread_rate` scalare unico di scenario. La valutazione M2M usa
  > sempre il mid ufficiale; ogni conversione reale (BUY multi-source o
  > funding-to-order) applica lo spread esattamente una volta; un
  > round-trip lo paga due volte. Il funding preserva sempre la valuta
  > (nessuna `destination_currency`/conversione a funding time). BUY può
  > attingere a più pool di cassa per valuta allo stesso Broker: ogni
  > pool diverso dalla valuta ordine produce una riga FX esplicita
  > `fx_debit[order_route_id, source_currency]`, mai incatenata
  > (anti-cascade strutturale: un credito già convertito non può
  > alimentare una seconda conversione). SELL non converte mai: il netto
  > resta nella valuta quote dell'Asset. La chiusura delle coppie dirette
  > richieste (`validate_fx_pair_closure`) copre nativo↔valuation per
  > ogni valuta referenziata, WAC↔fiscal per ogni SELL, e
  > pool-currency↔quote per ogni BUY; nessuna composizione A/B+B/C.
  > **Note implementazione — bug 1 (canonicalizzazione FX):**
  > `ExactEvaluation.__post_init__` canonicalizzava `self.fx` tramite
  > `item.route_id`, campo inesistente su `ExactFxEvaluation` (che ha solo
  > `order_route_id`/`source_currency`); chiave corretta in
  > `(item.order_route_id, item.source_currency)`. Scoperto da
  > test-author come `xfail(strict, raises=AttributeError)` su 3 test,
  > confermato fix tramite `XPASS(strict)` (fallimento atteso = prova che
  > il bug non c'è più) prima di toccare il file di test.
  > **Note implementazione — bug 2 (reachable/trapped negativi):**
  > `_source_reachability` calcolava `reachable = min(remaining, capacity)`
  > senza clamp; una source overcommitted (`remaining < 0`) produceva un
  > `reachable` negativo che faceva fallire l'invariante
  > `ExactFundingSourceEvaluation.__post_init__`. Introdotto
  > `effective_remaining = max(remaining, 0)` usato in entrambi i rami
  > (early-return e capacity-based); l'invariante del modello ora
  > riconcilia `structurally_reachable_amount + structurally_trapped_amount`
  > contro `max(remaining, 0)`, non `remaining` — `remaining` resta libero
  > di essere negativo perché è il segnale corretto per
  > `FUNDING_WITHIN_SELECTED`/`FUNDING_SOURCE_CONSERVATION`, calcolati da
  > `selected`/`transferred`/`remaining` direttamente, non da
  > reachable/trapped. Verificato: `selected=10, transferred=11,
  > remaining=-1` → `reachable=0, trapped=0`, confermato empiricamente da
  > test-author (non solo predetto).
  > **Note implementazione — bug 3 (fx_rate divisione per zero):**
  > `normalize.py`'s `fx_rate()` calcolava il ramo reciproco
  > (`ExactRatio(1)/rate`) senza guardia; una rate memorizzata
  > non-positiva (già segnalata separatamente da `validate_fx_rates` come
  > `nonpositive_fx_rate`) che richiede inversione (`source > destination`)
  > causava un crash di divisione per zero/negativo invece di restituire
  > `None` come il chiamante (`validate_current_portfolio`) già si
  > aspettava (`if rate is None or rate <= 0: complete = False`). Scoperto
  > da test-author riconciliando `test_pac_planner_normalize.py`; risolto
  > restituendo `None` per qualunque rate memorizzata `<= 0`, prima del
  > ramo reciproco.
  > **Note implementazione — bug 4 (fiscal_currency vs quote_currency):**
  > `_validate_sell_route_context` (evaluator, boundary contract)
  > richiede `asset_tax.fiscal_currency == quote_currency` e
  > `withholding.fiscal_currency == quote_currency`, ma il normalizer non
  > validava questa uguaglianza — richiedeva solo la coppia FX diretta
  > WAC↔fiscal (`require_fx_pair`), permettendo uno scenario
  > schema-valid con `fiscal_currency != quote_currency` di superare la
  > normalizzazione come `ready` e poi far crashare l'evaluator con
  > `ExactScenarioContractError` invece di un issue tipizzato — stessa
  > classe dei tre gap già chiusi nella review precedente. Aggiunta la
  > verifica in `validate_sell_route_requirement`: se
  > `tax.fiscal_currency != quote_currency` emette
  > `allocation.currency_mismatch` su `policy.asset.<id>.fiscal_currency`;
  > combinata con il controllo di netting broker già esistente (che
  > forza `withholding.fiscal_currency == tax.fiscal_currency` per
  > singolo Broker) copre transitivamente anche il lato withholding.
  > Nessun nuovo issue code introdotto (riuso di `allocation.currency_mismatch`,
  > già usato per lo stesso pattern nel fee schedule, regola #12).
  > **Note implementazione — riconciliazione test (tre file):**
  > `test_pac_planner_evaluator.py` (nuovo, test-author): 140 passed, 0
  > xfailed, 0 failed — import-fix, ~15+ funzioni riscritte, 4 eliminate
  > (concetti FX-route/fx_mode non più rappresentabili), 2 aggiunte
  > (multi-source pool-sharing, SELL-never-converts), 4 xfail rimossi
  > dopo i bug fix con asserzioni numeriche reali.
  > `test_pac_planner_schemas.py`: 448 passed — pulizia fixture (righe
  > morte `fx_fees`/`fx_buffer`), fingerprint pac/rebalancer ricalcolati,
  > eccezione mirata dell'invariante closed-schema per il solo campo
  > `fx_rates` (unica mappa aperta per decisione di prodotto).
  > `test_pac_planner_normalize.py`: 135 passed — 16 fallimenti pre-round
  > (54 raccolti, 38 passing), tutti stale test/fixture (campi morti
  > `valuation_rates`/`fx_quotes`/`fx_routes`, guardia issue-count
  > 89→80, fixture fee-schedule EUR su Asset USD, caso `fx-route` non
  > più rappresentabile eliminato); zero bug di produzione in
  > `normalize.py` da questa riconciliazione. Combinato con
  > `test_pac_planner_exact.py` (83, invariato): 135 totali nella
  > categoria `pac-planner-core`.
  > **Note implementazione — evidenza gate finale D-main (lane
  > 6153/`/tmp/librefolio-r2-d`):** `services pac-planner-core` →
  > `135/135`; `services pac-planner-evaluator` → `140/140`; `schemas
  > pac-planner` → `448/448`; `schemas pac-analyze` (P1, invariato) →
  > `112/112`. Statico sui nove file toccati (sei produzione:
  > `pac_allocator.py`/`evaluator.py`/`issues.py`/`models.py`/`normalize.py`/`ledger.py`,
  > tre test): Ruff `All checks passed!`; Black `--check` nove file
  > unchanged; `py_compile` exit `0`. `git diff --check` whole-worktree:
  > exit `0`; staged `0`; HEAD invariato `958527e0`; `lsof
  > -nP -iTCP:6153 -sTCP:LISTEN` senza output (nessun listener). Oracle,
  > compiler/SCIP, plugin, mapper, report, runner-integrazione restano
  > esplicitamente bloccati.
  > **⚠️ Fuori pista — correzione nomenclatura P1:** la nota precedente
  > riportava erroneamente `services pac-analyze` (97/97, categoria
  > "PAC Initial-State Analyze", non-P1) come il gate P1; il gate P1
  > reale è `schemas pac-analyze` ("Strict P1 draft/result codecs...",
  > `test_pac_analyze_schemas.py`) → `112/112`. Corretto sopra; entrambe
  > le categorie restano comunque verdi e invariate.
  > **Note implementazione — checkpoint threading `_source_reachability`/
  > `_can_reach_buy` (stessa classe di `_global_constraint_facts`):**
  > entrambe le funzioni scansionavano `scenario.order_routes`/
  > `scenario.target_weights`/`scenario.funding_routes` senza
  > `check_budget` interno (solo i chiamanti esterni avevano il check
  > per-iterazione, non gli scan annidati dentro queste due funzioni,
  > potenzialmente O(funding_routes × order_routes) per singola
  > chiamata). Aggiunto parametro `checkpoint: Checkpoint | None` a
  > entrambe; `check_budget(checkpoint)` in testa a ogni loop
  > (convertito anche il set-comprehension `positive_targets` in
  > `_can_reach_buy` in loop esplicito, stesso pattern già usato in
  > `_global_constraint_facts`); propagato `checkpoint` a tutti i 3 call
  > site esterni di `_source_reachability` (2 già in loop con
  > `check_budget` proprio, 1 dentro un `sum()` su generator
  > convertito in loop esplicito per lo stesso motivo). Nessun altro
  > cambio di comportamento; verificato staticamente
  > (py_compile/ruff/black puliti) e dinamicamente (`pac-planner-core`
  > 135/135, `pac-planner-evaluator` 140/140, `schemas pac-planner`
  > 448/448, `schemas pac-analyze` 112/112, tutti invariati). Nota:
  > `_buy_pool_currencies` ha la stessa classe di scan non
  > checkpointato ma non era nello scope autorizzato di questo giro —
  > segnalato al coordinator, non modificato.
  > **Note implementazione — checkpoint threading `_buy_pool_currencies`
  > (autorizzato dal coordinator dopo la segnalazione sopra) e cascata
  > nei suoi 2 chiamanti:** aggiunto `checkpoint: Checkpoint | None` a
  > `_buy_pool_currencies`, convertiti i 3 `set.update(genexpr)` in loop
  > espliciti con `check_budget` in testa (stesso motivo delle
  > conversioni precedenti); propagato ai 7 call site. Ruff (`F821
  > Undefined name checkpoint`) ha rivelato che 2 di questi 7 call site
  > erano dentro funzioni che non avevano ancora `checkpoint` in scope:
  > `_expected_decision_rows(scenario, index)` e, attraverso
  > `_canonical_tie_breaks`, `_canonical_tie_decision_ids(*, scenario,
  > index)` — nessuna delle due riceveva/propagava checkpoint prima
  > d'ora, pur avendo entrambe 3 scan su `scenario.funding_routes`/
  > `scenario.order_routes` (stessa classe di difetto, semplicemente non
  > ancora scoperta). Aggiunto `checkpoint` a entrambe le firme,
  > `check_budget` in testa a tutti e 3 i loro loop, e propagato dai
  > loro chiamanti (`build_exact_policy_view`, `_validated_policy_decisions`
  > per la prima; entrambi i call site di `_canonical_tie_breaks` per la
  > seconda) — tutti già con `checkpoint` proprio in scope. Nessun altro
  > cambio di comportamento. Verificato: Ruff `All checks passed!`
  > (prima catturava esattamente i 2 gap), Black/py_compile puliti;
  > dinamicamente invariato `pac-planner-core` 135/135,
  > `pac-planner-evaluator` 140/140, `schemas pac-planner` 448/448,
  > `schemas pac-analyze` 112/112. HEAD invariato `958527e0`, 0 staged,
  > porta 6153 libera.
- [ ] 9. Implementare oracle indipendente.
- [ ] 10. Confrontare fixture esaustive e permutation invariance.
- [ ] 11. Eseguire review matematica indipendente.

Selector:

```text
services pac-planner-core
services pac-planner-oracle
```

## 13. Stop conditions

- unità non determinabile;
- rounding rule non univoca;
- bound non finito;
- ledger non riconciliabile;
- evaluator dipende dal solver;
- oracle non enumera una variabile decisionale;
- un esempio storico viene usato come golden optimum;
- una policy richiede coefficiente/default non deciso.

## 14. Definition of Done

- tutti i numeri autorevoli attraversano `ExactRatio`/posting espliciti;
- normalizer immutabile e deterministicamente ordinato;
- ledger, fee, FX, tax e holding riconciliati;
- evaluator indipendente dal solver;
- oracle completo sui domini dichiarati;
- oracle copre baseline SELL, variante e promotion sui domini piccoli;
- test unit/property/oracle verdi;
- review matematica senza blocker;
- CP2 pronto, nessun artifact runtime, porta libera.

→ Step 3: [Solver e policy](plan-phase00Step3PacRebalancerSolverPolicies.prompt.md)
