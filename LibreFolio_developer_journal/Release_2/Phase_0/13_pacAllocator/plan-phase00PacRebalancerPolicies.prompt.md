# PAC & Rebalancer — policy, funzioni obiettivo e vincoli

**Stato:** TARGET CORRENTE — decisioni di policy approvate, con ragionamento e
controesempi; rilievi della review indipendente incorporati il 2026-09-16.
**Tipo:** specifica normativa del comportamento, non implementazione solver.
**Implementazione:** non autorizzata da questo documento.

**Suite target:** [master](plan-phase00PacRebalancerTargetDesign.prompt.md) ·
[nucleo matematico](plan-phase00PacRebalancerMathematicalCore.prompt.md) ·
[architettura](plan-phase00PacRebalancerArchitecture.prompt.md) ·
[UI completa](plan-phase00PacRebalancerUiTarget.prompt.md).

> Questo piano risponde a quattro domande:
>
> 1. quali candidati sono ammessi;
> 2. come vengono ordinati i candidati ammessi;
> 3. perché ogni tier è in quella posizione;
> 4. quali casi limite hanno escluso pipeline alternative.
>
> Le formule economiche e le unità sono definite nel nucleo matematico. Qui
> vengono composte in policy.

---

## 1. Tre categorie da non confondere

### 1.1 Hard constraint

Un hard constraint separa candidati validi e invalidi.

Esempi:

- cash spendibile finale non negativo;
- SELL non oltre inventario;
- ordine multiplo del quantum;
- nessun BUY+SELL dello stesso Asset;
- FX soltanto su una coppia dichiarata.

Un vincolo non viene “compensato” da uno score migliore.

### 1.2 Objective stage

Un objective stage ordina candidati già hard-feasible.

Esempi:

- minimizzare $L2_{fixed}$;
- minimizzare $U$;
- minimizzare turnover;
- minimizzare numero righe.

La freccia:

```text
f1 → f2 → f3
```

significa:

1. minimizzare `f1`;
2. fra i soli candidati non peggiori su `f1`, minimizzare `f2`;
3. fra i soli candidati non peggiori su `f1` e `f2`, minimizzare `f3`.

Non è:

```text
lambda1*f1 + lambda2*f2 + lambda3*f3
```

e non contiene coefficienti nascosti.

### 1.3 Canonical tie-break

Il tie-break rende deterministica la scelta fra candidati equivalenti su tutti
i tier prodotto. Usa un vettore ordinato stabile di:

- Asset canonical ID;
- Broker ID;
- valuta;
- lato;
- route ID;
- quantum.

Non può cambiare un tier economico. È l'ultima operazione.

---

## 2. Policy compiler

La policy costruisce un programma dichiarativo:

```text
PolicyProgram
├── enabled_variables
├── finite_domains
├── hard_constraints[]
├── objective_stages[]
├── canonical_tie_vector
├── proof_requirements
└── explanation_templates
```

Ogni `ConstraintSpec` deve avere:

- codice stabile;
- scope;
- unità;
- fonte del bound;
- predicato solver;
- predicato Decimal indipendente;
- issue/explanation associata.

Ogni `ObjectiveStage` deve avere:

- nome;
- direzione `min|max`;
- unità;
- funzione evaluator Decimal;
- espressione solver;
- regola di freeze;
- campo report.

Una futura policy è dichiarativa soltanto se usa gli stessi fatti, ledger,
constraint primitives, output e proof contract. Se richiede nuovi dati o un
algoritmo diverso, serve una nuova versione/decisione, non una combinazione
improvvisata di stage.

---

## 3. Catalogo dei vincoli comuni

### 3.1 Input e identità

| Codice concettuale | Vincolo |
|---|---|
| `TARGET_WEIGHTS_EXACT` | pesi non negativi e somma Decimal esatta a uno |
| `CANONICAL_ASSET_UNIQUE` | una sola identità economica per Asset |
| `BROKER_AUTHORIZED` | ogni Broker persistito appartiene allo scope autorizzato |
| `REFERENCE_CURRENCY_VALID` | valuta di valorizzazione valida e presente |
| `PRICE_BASIS_POSITIVE` | prezzo finito e `quote_base_quantity>0` |
| `EXECUTION_MARGIN_EXPLICIT` | margini BUY/SELL route finiti, non negativi e applicati una sola volta anche senza FX |
| `NO_NONFINITE` | nessun NaN/infinito |

Un dato mancante produce `needs_input`; un dato contraddittorio produce
`invalid`; un caso ben formato fuori dal dominio v1 produce `unsupported`.

### 3.2 Funding

| Codice concettuale | Vincolo |
|---|---|
| `SELECTED_WITHIN_AVAILABLE` | importo selezionato ≤ saldo disponibile dichiarato |
| `FUNDING_WITHIN_SELECTED` | trasferimenti ≤ importo selezionato |
| `NO_SELF_TRANSFER` | nessun trasferimento Broker→stesso Broker |
| `ROUTE_DECLARED` | funding soltanto su route esplicita |
| `NO_DOUBLE_COUNT` | contributo e cash esistente non duplicati |
| `NATIVE_CURRENCY_LEDGER` | ogni cassa vive nella propria valuta |

La priorità di una fonte è objective/tie operativo, non permesso implicito.

### 3.3 FX

| Codice concettuale | Vincolo |
|---|---|
| `FX_EDGE_DECLARED` | gamba FX presente nello snapshot |
| `FX_SINGLE_HOP` | un solo hop per percorso v1 |
| `FX_DEBIT_CREDIT_COUPLED` | credito funzione del debito |
| `FX_RATE_ORDER_SAFE` | `sell <= mid <= charge` |
| `FX_NO_ACTIVE_CYCLE` | nessun ciclo attivo |
| `FX_SOURCE_CASH` | debito+fee+buffer finanziato |
| `FX_NATIVE_QUANTUM` | debito multiplo della minor unit sorgente |

Una route che richiede multi-hop è `unsupported`; non viene ridotta
silenziosamente a una conversione diversa.

### 3.4 Ordini

| Codice concettuale | Vincolo |
|---|---|
| `INSTRUCTION_KIND_EXCLUSIVE` | `whole_quantity` oppure `monetary_amount` |
| `ORDER_QUANTIZED` | quantum intero del passo dichiarato |
| `ORDER_MIN_IF_ACTIVE` | riga attiva ≥ massimo fra minimo condizionale e un quantum positivo |
| `ORDER_REQUIRED_MIN` | minimo obbligatorio indipendente dall'attivazione |
| `ORDER_CAP` | misura ordine entro cap e unità |
| `ORDER_SIDE_ALLOWED` | lato autorizzato per route |
| `NO_IMPLICIT_ROUTE` | nessun routing non dichiarato |
| `NO_INVENTORY_ROUNDING` | holding corrente non arrotondata allo step futuro |

### 3.5 Cash e costi

| Codice concettuale | Vincolo |
|---|---|
| `SPENDABLE_CASH_NONNEGATIVE` | ledger finale spendibile ≥ 0 |
| `PHYSICAL_CASH_RECONCILED` | spendibile+riserve = fisico |
| `COST_NOT_INVESTMENT` | fee/spread/tax/buffer esclusi dal valore Asset |
| `SELL_POSTED_ONCE` | lordo accreditato una volta; fee/tax sottratte una volta |
| `ROUNDING_BOUND` | `A_round` ricostruibile entro bound |
| `ACCOUNTING_IDENTITY` | decomposizione di `U` chiusa |

### 3.6 Holdings e lati

| Codice concettuale | Vincolo |
|---|---|
| `FINAL_QUANTITY_NONNEGATIVE` | quantità finale Asset×Broker ≥ 0 |
| `FINAL_VALUE_NONNEGATIVE` | valore finale Asset aggregato ≥ 0 |
| `SELL_WITHIN_INVENTORY` | SELL ≤ inventario esatto |
| `NO_ASSET_BUY_AND_SELL` | nessun Asset con entrambi i lati |
| `NO_SHORT_OR_LEVERAGE` | nessuna posizione o cassa negativa inventata |
| `REBALANCER_NONEMPTY` | `V0>0` e `F_final>0` |

### 3.7 Bound

Ogni variabile possiede un upper bound derivato da:

- cash raggiungibile;
- cap route;
- prezzo/charge;
- step;
- inventario;
- massimo trasferibile;
- direzione FX.

Se il bound richiede un Big-M arbitrario, il programma non viene compilato.

---

## 4. Obiettivo primario condiviso

Per ogni Asset:

```text
F_ref = current invested value + route-reachable selected funding
T_a = w_a * F_ref
r_a = V_a_final - T_a
L2_fixed = sum(r_a^2)
U = F_ref - sum(V_a_final)
```

Tutti i prodotti iniziano con:

```text
L2_fixed → U
```

### 4.1 Perché `L2_fixed` è primo

Il prodotto vuole prima il piano discreto complessivamente più vicino ai target
monetari fissati sul capitale raggiungibile.

Se `U` fosse primo:

- il solver potrebbe saturare il cash con un Asset molto sovrappesato;
- un quantum economico ma allocativamente distruttivo batterebbe un piano molto
  più vicino al target;
- la variante margine non avrebbe più una funzione distinta.

### 4.2 Perché `U` è secondo

A parità esatta di $L2_{fixed}$ possono esistere:

- route equivalenti;
- target simmetrici;
- quanta di stesso valore;
- posting diversi che producono lo stesso quadrato.

Fra tali candidati, il prodotto preferisce maggiore valore Asset finale.
`U` non è sommato a $L2$ con un lambda: agisce soltanto sulla faccia di pareggio.

### 4.3 Perché non percentuali actual-final

Usare:

```text
V_a_final / F_final - w_a
```

come objective:

- rende il denominatore decision-dependent;
- permette di avvicinare percentuali riducendo capitale;
- introduce struttura frazionaria/MINLP o parametrica;
- richiede anti-liquidazione ulteriore.

Le percentuali restano report facts.

### 4.4 Perché non `Dinf → D1`

$D_\infty$ minimizza il peggior scostamento percentuale; $D_1$ la somma
assoluta. Sono leggibili, ma:

- lavorano su percentuali actual-final;
- non penalizzano come il quadrato la concentrazione di un errore;
- la precedente formulazione parametrica aumenta complessità di closure;
- non esprimono direttamente la policy fixed-reference scelta.

Restano diagnostici.

---

## 5. Matrice delle policy v1

| Prodotto/modalità | Azioni abilitate | Constraint specifici | Pipeline primaria |
|---|---|---|---|
| PAC `proportional` | funding, transfer, FX, BUY | `SELL=0` | `L2 → U → route priority → cost → rows → tie` |
| PAC `min_fragmentation` | funding, transfer, FX, BUY | `SELL=0` | `L2 → U → split Assets → rows → route priority → cost → tie` |
| Rebalancer `invest_only` | funding, transfer, FX, BUY | `SELL=0`, `V0>0`, `F_final>0` | `L2 → U → turnover → cost → rows/splits → tie` |
| Rebalancer `invest_and_sell` fase 1 | stesso dominio `invest_only` | stessi vincoli | calcola/congela baseline |
| Rebalancer `invest_and_sell` fase 2 | baseline congelata + SELL + BUY incrementali | SELL funding-only, eligibility, irreducibilità | `L2 → U → turnover → cost → rows/splits → tie` |

`L2` nella tabella significa sempre $L2_{fixed}$.

---

## 6. PAC `proportional`

Pipeline:

```text
L2_fixed
→ U
→ route priority
→ explicit policy cost
→ active order rows
→ canonical tie
```

### 6.1 Significato

La policy non assegna prima un budget per Asset con floor deterministico. Il
solver sceglie globalmente tutti i quantum BUY.

`proportional` indica che:

- la qualità allocativa globale resta dominante;
- a parità di allocazione e deployment, si rispettano prima le preferenze di
  routing dichiarate;
- poi si preferiscono costi minori;
- infine meno righe.

Non significa split obbligatorio in proporzione fra Broker.

### 6.2 Perché route priority precede cost/rows

La priorità Broker è una scelta esplicita utente. Se due piani hanno stesso
$L2$ e $U$, ignorarla per risparmiare una fee minima cambierebbe il significato
della policy.

Controesempio:

```text
Broker A priority 1, fee 1
Broker B priority 2, fee 0
stesso Asset, stesso valore, stesso L2 e U
```

La policy `proportional` sceglie A. Chi vuole frammentazione/costi come driver
deve selezionare un'altra policy futura, non ricevere un override nascosto.

### 6.3 Perché rows è tardo

Minimizzare righe prima di route/costi potrebbe:

- concentrare tutto su una route meno desiderata;
- cambiare il Broker pur senza beneficio allocativo;
- fare apparire “proporzionale” una policy di consolidamento.

Rows è spareggio operativo.

---

## 7. PAC `min_fragmentation`

Pipeline:

```text
L2_fixed
→ U
→ number of split Assets
→ active order rows
→ route priority
→ explicit policy cost
→ canonical tie
```

### 7.1 Definizione di split

Un Asset è splittato quando BUY positivi sono distribuiti su più di una route
Broker.

```text
split_asset(a) = 1 if active_buy_routes(a) > 1 else 0
```

Il tier minimizza:

```text
sum_a split_asset(a)
```

e poi il numero totale di righe.

### 7.2 Perché dopo `L2` e `U`

La policy riduce frammentazione **senza** sacrificare qualità target o
deployment sulla loro faccia ottima.

Se split fosse prima di $L2$:

- un unico ordine su un Asset potrebbe battere un piano ben allocato;
- il risultato diventerebbe “compra meno cose”, non “alloca con meno split”.

### 7.3 Perché route priority dopo rows

Questa policy dichiara che, a parità di risultato economico, ridurre
frammentazione è più importante della preferenza Broker. È la differenza
prodotto rispetto a `proportional`.

### 7.4 Controesempio

```text
Piano X: L2=10, U=5, Asset splittati=0, righe=4
Piano Y: L2=9,  U=5, Asset splittati=2, righe=6
```

Vince Y perché $L2$ domina.

```text
Piano X: L2=9, U=5, split=0, righe=4
Piano Y: L2=9, U=5, split=1, righe=3
```

Vince X perché il numero di Asset splittati precede le righe.

---

## 8. Rebalancer `invest_only`

Pipeline:

```text
L2_fixed
→ U
→ turnover
→ explicit cost
→ active rows/splits
→ canonical tie
```

Constraint:

```text
SELL = 0
V0 > 0
F_final > 0
```

### 8.1 Turnover

$$
turnover=\sum_a(I_a^{BUY}+I_a^{SELL})
$$

valorizzato a mid. In `invest_only`, la parte SELL è zero.

### 8.2 Perché turnover dopo `U`

Sulla stessa faccia $L2$:

- prima si preferisce maggiore valore investito;
- poi il tier turnover mantiene una pipeline uniforme fra le due modalità.

Con `SELL=0`, dopo avere congelato $U$ vale
$turnover=K_{reachable}-U$: il tier è quindi costante e non può scegliere “meno
movimenti”. In `invest_only` tale scelta appartiene al successivo tier
righe/split. Il turnover diventa discriminante in `invest_and_sell`, dove BUY e
SELL possono variare a parità di valore finale.

Mettere turnover prima di $U$ favorirebbe il no-op o un piano sottoutilizzato.

### 8.3 Perché cost dopo turnover

Fee e spread influenzano già $U$ quando riducono $F_{final}$. Il tier costo
esplicito serve soltanto per distinguere candidati con stesso $L2$, $U$ e
turnover ma diversa composizione del costo.

Non deve ripostare costi nel ledger né creare una seconda penalità weighted.

### 8.4 No-op

Il no-op è candidato ammesso quando:

- non viola required minimum;
- non esiste debito/azione obbligatoria;
- holding iniziali restano valide.

Può vincere soltanto se la tupla lo rende migliore. Il fatto che non faccia
turnover non gli consente di saltare $L2$ e $U$.

---

## 9. Rebalancer `invest_and_sell`

Questa modalità non apre direttamente un dominio BUY/SELL globale.

### 9.1 Fase 1 — baseline

Risolvere esattamente la policy `invest_only`. Congelare:

- funding;
- trasferimenti;
- FX;
- BUY;
- ledger risultanti.

Se non esiste un incumbent Decimal per la baseline, non si procede con SELL.

### 9.2 Eligibility SELL

Un Asset è SELL-eligible soltanto se:

```text
V_a_baseline - T_a > 0
```

e non possiede BUY nella baseline congelata.

Il divieto globale BUY+SELL prevale sempre.

### 9.3 Funding-only

Ogni SELL deve finanziare BUY incrementali. Sono vietati:

- vendita per lasciare cash;
- vendita per pagare soltanto fee/tax;
- vendita senza almeno un BUY incrementale;
- liquidazione dell'intero portafoglio;
- vendita di Asset underweight;
- vendita dell'Asset comprato nella baseline.

Formula minima:

$$
\sum_a I_a^{SELL}>0
\Longrightarrow
\sum_a I_a^{incrementalBUY}>0.
$$

### 9.4 Cassa fungibile

Non si lega artificialmente una SELL a uno specifico BUY. Tutto il cash
spendibile del Broker×valuta, incluse fonti baseline e netto SELL, resta
fungibile entro route e FX.

La prova di necessità SELL deve quindi riesaminare le assegnazioni non-SELL
tramite il publication gate esatto descritto sotto.

### 9.5 Irreducibilità locale

Il `SellIrreducibilityVerifier` possiede questo gate. Per ogni riga SELL attiva:

1. sottrarre un quantum;
2. ricostruire fee, tax e netto;
3. disattivare la riga se necessario;
4. compilare un sottoproblema che riapre soltanto funding/FX dichiarati
   mutabili;
5. mantenere lo stesso vettore BUY incrementale;
6. verificare che diventi non finanziabile.

Ripetere ponendo l'intera riga a zero.

Sono quindi al massimo due sottoproblemi per riga SELL attiva, con early exit al
primo controesempio. Il candidato è `invalid` se emerge un'alternativa
Decimal-feasible con meno SELL. È pubblicabile soltanto se tutti i
controfattuali sono chiusi da conflict witness Decimal completo o oracle
esaustivo; `floating infeasible` non basta. Timeout, cancel o closure mancante
scartano quel candidato SELL con `SELL_IRREDUCIBILITY_UNRESOLVED`. Il report
mantiene l'ultimo candidato verificato, almeno la baseline `invest_only`, come
`incumbent_found/not_proven`; usa `no_incumbent/not_proven` soltanto se non ne
esiste alcuno.

### 9.6 Minimalità globale

La minimalità globale dei SELL, a stesso vettore BUY, ordinerebbe:

```text
gross SELL mid
→ incremental tax/fee/spread
→ SELL rows/splits
→ canonical SELL/funding vector
```

Può essere `proven`, `gap_bounded` o `not_proven`. `local_irreducible` non viene
mai mostrato come prova globale.

### 9.7 Obiettivo fase 2

Sul dominio baseline congelata + SELL/BUY incrementali:

```text
L2_fixed
→ U
→ turnover
→ cost
→ rows/splits
→ tie
```

La baseline non è un lower bound cosmetico: è parte dei constraint della fase 2.

---

## 10. Variante margine comune

La variante è un secondo prodotto visibile, non un repair del primario.

### 10.1 Freeze hard

Restano uguali al primario:

- importi funding;
- trasferimenti;
- debiti/crediti FX;
- ordini BUY già presenti;
- ordini SELL;
- route e attivazioni primarie.

Sono ammesse soltanto quantità BUY addizionali:

```text
BUY_variant >= BUY_primary
```

su route già finanziabili dal cash spendibile risultante. La policy può
permettere l'attivazione di una nuova riga BUY, ma non nuove fonti o FX.

### 10.2 Pipeline

```text
U
→ resulting L2_fixed
→ incremental cost
→ incremental rows
→ canonical tie
```

### 10.3 Perché `U` è primo qui

La variante risponde a una domanda diversa:

> “Dopo avere congelato il piano target-first, quanto altro cash posso
> trasformare in Asset senza ridurre nessuna azione?”

Quindi l'impiego è normativo prima dello score.

### 10.4 Perché $L2$ è secondo

A pari deployment massimo, più allocazioni possono usare lo stesso importo.
$L2$ seleziona quella che danneggia meno il target e impedisce concentrazione
gratuita dell'overweight.

### 10.5 Peggioramento ammesso

Esempio:

```text
Primario: U=12, L2=5
Variante A: U=2, L2=9
Variante B: U=2, L2=12
```

Vince A. Entrambe possono peggiorare il primario; il report mostra:

- investimento aggiunto;
- delta $U$;
- delta $L2$;
- fee/righe incrementali;
- diagnostici percentuali.

### 10.6 Promozione

Esempio:

```text
Primario non provato: L2=10
Variante trovata:      L2=8
```

La variante non può essere etichettata “deployment del primario”: domina un
tier precedente. Deve diventare nuova incumbent primaria, quindi:

1. rivalutare Decimal;
2. riavviare la cascata;
3. ricostruire una variante coerente;
4. oppure pubblicare solo il nuovo primario se scade il budget.

---

## 11. Costi, righe e priorità

### 11.1 Costo policy

Il costo esplicito usa la contabilità once-only:

```text
economic loss
+ self-reserved tax
```

Include:

- fee BUY/SELL;
- fee FX;
- differenza charge/sell rispetto al mid;
- tax reserve;

ed esclude:

- cash libero finale per Broker×valuta, mai attribuito artificialmente a un
  Asset o a una route;
- buffer FX;
- valore investito;
- rounding.

La decomposizione $U$ non viene modificata dal tier costo.

### 11.2 Righe

Una riga ordine esiste se l'attivazione è positiva. Funding/FX rows possono
avere conteggi separati nel report, ma non vengono sommati a ordini senza una
decisione esplicita.

### 11.3 Route priority

La priorità è:

- esplicita nello snapshot;
- stabile;
- totale o completata dal tie canonico;
- applicata soltanto dopo i tier che la precedono.

Non è un permission bit e non crea route.

---

## 12. Casi limite — avvocato del diavolo

### 12.1 “Sono già al target con un acquisto minimo”

Scenario:

- percentuali perfette con un piccolo acquisto di ogni Asset;
- grande cash ancora disponibile.

Errore di una policy percentuale actual-final:

- percentuali possono restare perfette;
- deployment non viene penalizzato;
- $D_\infty=0$ con quasi tutto il cash idle.

Risposta target:

- $T_a=w_aF_{ref}$ usa tutto il capitale raggiungibile;
- il cash idle crea residui monetari;
- $L2_{fixed}$ non è zero;
- il primario continua a cercare quantum che riducono lo scostamento.

### 12.2 “Investiamo tutto a qualunque costo”

Scenario:

- resta cash sufficiente per una quota enorme di un solo Asset;
- comprarla peggiora molto il target.

Se `U` fosse primo nel primario, la quota verrebbe comprata.

Risposta:

- primario target-first: $L2$ prima di $U$;
- variante margine: $U$ prima di $L2$, ma come secondo risultato esplicito;
- l'utente vede entrambe le scelte.

### 12.3 “Meno righe è sempre meglio”

Scenario:

- una singola riga concentra il 90% su un Asset;
- quattro righe seguono quasi perfettamente i target.

Rows non può precedere $L2$. `min_fragmentation` riduce split soltanto sulla
faccia economicamente ottima.

### 12.4 “La route più economica deve vincere”

Scenario:

- route prioritaria costa leggermente di più;
- stessa allocazione e deployment.

`proportional` rispetta prima la priorità dichiarata. Un futuro
`minimum_cost` potrebbe invertire tier, ma non si altera la policy corrente.

### 12.5 “Vendere migliora le percentuali”

Scenario:

- vendita di un Asset overweight;
- nessun BUY utile;
- risultato lascia cash.

Pur potendo avvicinare percentuali, la vendita è vietata:

- target monetario fixed-L2 penalizza il valore mancante;
- vincolo SELL funding-only impedisce sale-to-idle-cash;
- $F_{final}>0$ impedisce liquidazione completa.

### 12.6 “Un quantum SELL in più costa poco”

Una SELL addizionale può:

- attivare fee fissa;
- cambiare tax reserve;
- cambiare FX;
- liberare un quantum BUY.

Per questo la necessità non si verifica sottraendo un valore aggregato; si
ricostruisce il modello controfattuale.

### 12.7 “Il solver dice infeasible”

Lo status floating può dipendere da:

- tolleranza;
- numerica;
- limite;
- formulazione;
- assenza di incumbent.

Senza conflict witness Decimal o oracle completo, il prodotto dice
`no_incumbent/not_proven`, non `infeasible_proven`.

### 12.8 “Il solver dice optimal”

Uno status `optimal` floating non prova:

- score esatto `ExactRatio`/scaled-integer;
- closure di tutti i tier;
- correttezza del freeze;
- ledger dopo posting.

Il candidato è `decimal_verified`; la proof resta `gap_bounded` o
`not_proven` senza oracle o `score_lattice_closure` coefficient-safe definita
nel [nucleo matematico §19.2.1](plan-phase00PacRebalancerMathematicalCore.prompt.md).

---

## 13. `no_op`, infeasible e timeout

### 13.1 `no_op`

Piano vuoto hard-feasible:

- budget zero;
- budget sotto ogni minimo;
- nessun quantum migliora il primario;
- tutte le azioni opzionali.

È `no_op/optimal_proven` soltanto con prova esatta.

### 13.2 `infeasible_proven`

Il piano vuoto viola almeno un vincolo obbligatorio e nessun altro piano è
ammesso, dimostrato tramite:

- conflict witness completo; oppure
- oracle esaustivo.

Esempio:

```text
required minimum = 1000 EUR
cash massimo raggiungibile = 800 EUR
nessuna SELL/FX/fonte alternativa ammessa
```

### 13.3 Timeout con incumbent

Pubblicare piano Decimal-valido con:

- `incumbent_found`;
- `gap_bounded` o `not_proven`;
- `stop_reason=time_limit|node_limit`;
- bound e tolleranze se comparabili.

### 13.4 Timeout senza incumbent

Pubblicare:

```text
no_incumbent / not_proven
```

Nessuna tabella ordini e nessuna falsa infeasibility.

---

## 14. Domini supportati e unsupported

Sono candidati `unsupported` v1:

- FX multi-hop;
- route cicliche;
- coefficiente envelope non sicuro;
- bound finito non derivabile;
- fee dinamica giornaliera non modellata;
- tax/netting non rappresentabile;
- PMC non riconciliabile;
- instruction kind non supportato;
- cardinalità oltre il dominio dichiarato.

Il Tool non:

- elimina righe;
- riduce Asset/Broker;
- cambia valuta;
- ignora FX;
- allenta minimi;
- sostituisce policy;
- aumenta timeout in modo nascosto.

---

## 15. Estensione futura delle policy

### 15.1 Policy dichiarativa ammissibile

Una nuova policy può riordinare/aggiungere stage se:

- usa stessi input;
- usa stessi ledger;
- usa constraint esistenti;
- produce stesso output;
- conserva proof contract;
- possiede evaluator Decimal.

Esempi potenziali:

- `minimum_cost` sulla faccia $L2/U$;
- `minimum_rows` sulla faccia $L2/U$;
- priorità Broker alternativa.

### 15.2 Policy che richiede nuovo contratto

Richiede decisione/versione separata:

- tax-loss harvesting;
- compensazione minus;
- chiusura Broker;
- settlement temporale;
- profili fee dinamici;
- target per Broker;
- FX multi-hop;
- Pareto frontier multi-risultato;
- obiettivo risk-based.

### 15.3 Policy deterministica

Il dispatcher deterministico è ammesso soltanto quando esiste una soluzione
chiusa che:

- produce lo stesso scenario normalizzato;
- rispetta gli stessi constraint;
- passa lo stesso evaluator;
- ha proof dichiarabile.

Non può essere usato per reintrodurre il vecchio floor PAC come primario.

---

## 16. Decisioni chiuse

- target monetario su $F_{ref}$ fisso;
- $L2_{fixed}$ primo tier primario;
- $U$ secondo tier primario;
- percentuali/$D_\infty$/$D_1$ diagnostici;
- PAC globale discreto, non floor deterministico;
- due policy PAC con differente ordinamento operativo;
- due modalità Rebalancer;
- `invest_and_sell` sequenziale e funding-only;
- variante margine frozen-action BUY-only;
- frecce lessicografiche, nessuna somma weighted;
- hard nonnegativity per quantità e valore;
- proof semantics A.

Dettagli contrattuali futuri non possono riaprire queste decisioni in silenzio.

---

## 17. Gate prima del piano implementativo

- review della matrice policy contro il nucleo matematico;
- conferma che ogni constraint abbia unità e predicate Decimal;
- conferma che ogni objective stage abbia freeze e campo report;
- esempi/counterexample per ogni riordinamento;
- oracle completo sui casi piccoli;
- benchmark delle cascade MIQP/MIQCP;
- mapping esatto policy→UI explanation;
- nessun default o coefficiente non visibile.
