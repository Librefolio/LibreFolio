# Step 2 — normalizzazione, aritmetica esatta, evaluator e oracle

**Stato:** IN PROGRESS — SLICE A CODE COMPLETE, TESTS PENDING; G3 REQUIRED FOR LATER SLICES.
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

- [ ] 1. Congelare modelli interni immutabili.
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
- [ ] 3. Implementare normalizer e issue taxonomy.
- [ ] 4. Implementare posting/rounding.
  - [x] 4A. Implementare posting signed `ROUND_HALF_UP` su quantum esplicito,
        rounding delta e ceil-to-quantum units. — 2026-09-16
  - [ ] 4B. Integrare le sette famiglie di posting e testarle tramite
        `test-author` dopo G3.
  > **Note implementazione**: `PostedAmount`, `post_half_up()` e
  > `ceil_to_quantum_units()` operano soltanto su `ExactRatio`; nessuna lookup
  > valuta/default minor-unit è stata introdotta.
  > **Evidenza**: review statica del percorso leased; nessun comando runtime o
  > test eseguito perché non autorizzato.
- [ ] 5. Implementare fee, FX e tax.
  - [x] 5A. Implementare formule numeriche pure fee/effective-FX/credito FX e
        taxable-gain/tax reserve. — 2026-09-16
  - [ ] 5B. Collegare formule a route, posting e withholding dopo G3.
  > **Note implementazione**: tutti gli input economici sono obbligatori e
  > caller-supplied; `cap=None` significa soltanto cap percentuale assente.
  > Le formule restituiscono valori esatti pre-posting, quindi il chiamante
  > applicherà una sola volta `post_half_up()` col quantum valuta esplicito.
  > `approved_rate > 0` e `0 <= tax_rate <= 1` sono assunzioni policy correnti
  > da congelare in G3, non nuovi bound pubblici dichiarati da Slice A.
  > **Evidenza**: review statica del percorso leased; nessun comando runtime o
  > test eseguito perché non autorizzato.
- [ ] 6. Implementare ledger e inventory.
- [ ] 7. Implementare fixed-reference/objective facts.
- [ ] 8. Implementare evaluator completo.
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
