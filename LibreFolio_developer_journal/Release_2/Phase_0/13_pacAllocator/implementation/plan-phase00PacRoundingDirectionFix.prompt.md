# Piano D — Arrotondamento del PAC sempre contro il piano

**Stato:** ✅ chiuso il 2026-10-09. Iniziato alle 12:03, CHECKPOINT READY alle 16:59, poi i commit
`96283eaa5` `fix(pac)`, `85b2a3125` `docs(pac)` e `9a6974eff` journal; merge `b81b92fd1` nel treno 26
(`dev_release2` = `083ed26dc`). Il S10 chiude il debito di formato lasciato al S8, con uno
`style(pac)` a sé. Il via è del developer, inoltrato dal coordinator:
regola (a) su tutte e 7 le famiglie arrotondate, banda esplicita del validatore, top-up mantenuti come
rete, (e) nel backlog. Sul n. 15 il developer ha scelto «B1: banda + tasso peggiorativo dentro la banda
(Consigliato)». Un solo checkpoint per (a) e B1; il S10 ha il suo.
**Baseline:** `9b2acdd5d` su `e-alfy-allocatore-pac`, cioè `dev_release2` col treno 21 (merge
`95fb05f17` della riga 15, poi `docs(changelog)`). Verificata alle 11:41, 11:50, 11:53, 11:57 e 12:03:
albero pulito, stage vuoto, porta 6151 libera. Carico alle 12:03: 14.26 / 18.47 / 21.83.
**Posizione:** `LibreFolio_developer_journal/Release_2/Phase_0/13_pacAllocator/implementation/plan-phase00PacRoundingDirectionFix.prompt.md`.
Il coordinator ha scritto `13_pacAllocator/plan-…`, ma i piani d'esecuzione stanno in
`implementation/`, come quelli delle righe 13 e 15.
← Precedente: [`plan-phase00PacFxConversionFix.prompt.md`](plan-phase00PacFxConversionFix.prompt.md)
(riga 15 del README).
→ Seguente: analisi del Rebalancer (riga 14), nel backlog. Non parte senza il via del coordinator.
**Corsia:** suite `6151` + `/tmp/librefolio-r2-d`, un comando per volta. Prefisso:
`PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py test --test-port 6151 --data-dir /tmp/librefolio-r2-d …`.
- Niente E2E, nessun server di review, nessun `db populate` senza una nuova concessione.
- Gli script di servizio (kit di riproduzione) girano in-process col prefisso
  `PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python …`: niente DB, niente rete.
- Accanto a ogni tempo annoto il carico della macchina.

Le righe citate sono misurate alla baseline. Se il codice cambia, prevale il codice.

---

## 0. Perché

M, con la correzione della riga 15, ha rimesso in USD il conto esterno della gallery PAC. Il piano si
calcola, ma **l'ottimizzatore sfrutta l'arrotondamento**: `pac-result-plan` contiene passi da pochi
centesimi.

- Passo 4: trasferimento di 0,01 USD da Northwind a DEGIRO, convertito in 0,01 EUR (esatti 0,00893,
  arrotondati per eccesso).
- Passo 6: su IBKR 0,14 USD diventano «about 0,13 EUR» (esatti 0,12507), subito dopo il passo 5 che
  converte EUR in USD sullo stesso broker. Servono a pagare esattamente la ventesima quota del bond.
- Passo 5: 1.101,89 EUR × 1,1193593463 fa esattamente 1.233,4109 USD, ma il credito è «about
  1.233,42».
- «Not invested» mostra Rounding ≈ −0,02 EUR: valore creato dall'arrotondamento.

È contro lo spirito che il coordinator riassume come «nessuna conversione deve creare valore» (§4.4).
La frase non compare alla lettera in nessun piano della suite: il principio è nel MathCore, §7.3
(«nessuna incoerenza di tasso capace di creare arbitraggio sintetico»).

Le parole del developer, inoltrate dal coordinator:

> «si a tutto quello che dici, magari possiamo fare che si arrotonda solo alla fine, non nei passaggi
> intermedi, comuque per 1 centesimo stiamo facendo una questione di stato, il validatore non deve
> essere troppo stretto, una piccola banda per gli arrotondamenti è accettabile, siamo in un dominio
> intero con molte operazioni e conversioni continue, è normale avere alla fine piccoli arrotondamenti,
> comunque bella l'idea di arrotondare in modo pegiorativo»

Le decisioni del coordinator:

- **regola (a) su tutte e 7 le famiglie arrotondate**: crediti per difetto, debiti per eccesso, scritta
  nella tabella del ledger (§2.1);
- **G1** diventa «l'unico arrotondamento economico è al centesimo, sempre contro il piano»;
- **top-up mantenuti** come rete;
- **(e)**, una sola conversione per broker e coppia, va nel backlog;
- **«solo alla fine»**: spiegato in 3 righe (§2.2), qui e nel checkpoint;
- **validatore non troppo stretto**: niente `≥ 0` secco, una banda esplicita e motivata (§2.3).

Sul n. 15, i cambi incrociati quasi coerenti, ho mostrato che la banda dei tassi da sola non è sicura
con la sola (a). Il developer ha scelto l'etichetta «B1: banda + tasso peggiorativo dentro la banda
(Consigliato)» (§2.6).

Le tre garanzie del piano:

| Id | Garanzia |
|---|---|
| G1 | L'unico arrotondamento economico è alla minor unit della valuta (il centesimo per EUR e USD), sempre contro il piano. Il piano resta `optimal_proven` quando il solver chiude ogni obiettivo: il modello e la verifica esatta arrotondano allo stesso modo. Nessun testo dice «non ottimo». |
| G2 | Il validatore ha una banda esplicita: una minor unit per posting arrotondato, valutata nella valuta dello scenario. |
| G3 | Nessuna conversione, nessuno spezzamento e nessun cambio quasi coerente crea valore: Σ val(crediti postati) ≤ Σ val(debiti), e nessun credito supera il proprio arrotondamento per difetto. |

## 1. Problema

### 1.1 Riproduzione minima, oggi

Kit in-process, solo richieste sintetiche: `/tmp/libreFolio_d_pacdust/` (`lib.py`, `repro.py`,
`repro_spread.py`). Tasso r = 1,1193593463 USD per EUR, spread 0, quantum 0,01, un solo broker. Ogni
caso esce `ready_incumbent` con prova `optimal_proven`.

| Caso | Scenario | Oggi (HALF_UP) |
|---|---|---|
| R1 | 11,19 USD di contributo → Asset EUR a 10,00 | esatti 9,996790 EUR → postati 10,00: compra 1 quota |
| R1-ctrl | 11,18 USD | `ready_no_op` |
| R1b (passo 4) | cassa 9,99 EUR + 0,01 USD | 0,008934 → 0,01: compra |
| R2 (passo 5) | cassa 1.101,89 EUR → Asset USD `aaa` 615,63 + `bbb` 617,79 | spezza: 0,13 EUR → 0,15 USD e 1.101,76 → 1.233,27; Σ 1.233,42 contro l'esatto unico 1.233,41087 |
| R3 (passo 6) | 52,26 EUR + 410,15 USD → bond 52,40 EUR + stock 410 USD | andata e ritorno: 0,05 EUR → 0,06 USD e 0,21 USD → 0,19 EUR |
| R4 | Asset EUR a 10,004, cassa 10,00 | debito postato 10,00 |
| CTRL | 10,00 EUR → Asset USD a 11,19 | compra: 10,00 × r = 11,193594 sotto ogni regola |
| R1s | come R1 con 11,20 USD e spread 0,1% | esatti 9,995718 → 10,00: compra, valore creato +0,004282 EUR |
| R2s | come R2 con spread 0,1% | spezza ancora: valore creato +0,006433 EUR |

**Il 1.233,42.** `build_conversions` (`planner_report.py:549-592`) somma i crediti postati delle azioni
FX di una conversione: 0,15 + 1.233,27 = 1.233,42. Un solo HALF_UP sul totale esatto darebbe 1.233,41.
Il solver ha spezzato la conversione proprio per guadagnare il centesimo.

**Il «Rounding ≈ −0,02 EUR».** È `accounting.rounding_delta`, che riporta il `rounding_adjustment`
dell'evaluator, positivo quando l'arrotondamento costa al piano (`planner_report.py:700-723`,
`KpiCards.svelte:66-71`). Negativo vuol dire valore creato.

### 1.2 Causa vera

1. `ledger.py:73-85` (`_validate_posting`) esige HALF_UP e `ledger.py:114-138`
   (`rounded_money_posting`) posta con `post_half_up`: un credito può salire fino a q/2 per posting.
2. `constraints.py:393-431` (`_posted_units_term`) modella HALF_UP con i pareggi permissivi: SCIP vede
   il guadagno.
3. Con spread 0 e nessun costo per passo, spezzare è gratis; con uno spread dello 0,1% conviene
   ancora (R1s, R2s).
4. `evaluator.py:2272-2282` fissa `ROUNDING_BOUND` a Σ q/2, controllato in modo simmetrico a
   `evaluator.py:2702`: il validatore lo accetta.

## 2. Decisioni

### 2.1 Regola (a): la tabella del ledger

| Famiglia | Verso | Regola |
|---|---|---|
| `fx_credit`, `gross_sell_credit` | credito | per difetto (floor) |
| `buy_debit`, `buy_fee`, `sell_fee`, `broker_withheld_tax`, `self_reserved_tax` | debito | per eccesso (ceiling) |
| `initial_selected`, `funding_in`, `funding_out`, `fx_debit` | — | flussi esatti, non arrotondati |

- SCIP modella solo `fx_credit`, `buy_debit` e `buy_fee` (`constraints.py:309-310`). Le altre famiglie
  arrotondate falliscono chiuse prima del modello (`constraints.py:316-351`), come oggi.
- Σ floor ≤ floor Σ e Σ ceil ≥ ceil Σ: **spezzare non conviene mai**.
- L'aggiustamento di ogni posting, positivo quando costa al piano, sta in [0, q): mai valore creato.

### 2.2 «Arrotondare solo alla fine»: le 3 righe

1. Ogni movimento reale (trasferimento, conversione, acquisto, commissione) si arrotonda una volta
   sola, sul suo importo esatto finale, alla minor unit, contro il piano: è ciò che il broker esegue.
2. I calcoli intermedi restano esatti e si arrotondano solo per mostrarli («≈»): nel motore non c'è
   alcun `quantize` o `ROUND_` fuori dal formatter di visualizzazione (`wire_numbers.py:162`) e dal
   Context di `numeric.py:365`, che intercetta Inexact; `round` e `ceil` del solver lavorano su quanti
   interi.
3. Movimenti prenotati separatamente non si possono fondere, ma con (a) spezzarli non conviene mai,
   quindi il solver non ha motivo di farlo.

Le azioni FX hanno chiave per rotta d'acquisto (`fx_debit` con chiave `route:pool`), ma il credito
finisce nella cella broker/valuta di destinazione (`constraints.py:505-516`) e finanzia ogni ordine
di quel broker in quella valuta. Dove il budget è stretto il solver concentra la conversione su una
sola azione, perché Σ floor ≤ floor Σ; con margine può lasciarne più d'una, ciascuna arrotondata
contro il piano. Chi esegue a mano una sola conversione al broker riceve almeno quanto pianificato.
Fonderle sempre, (e), resta nel backlog. I test non fissano lo spezzamento.

### 2.3 La banda del validatore

- `rounding_bound` = Σ val(q_i) sui posting arrotondati: **una minor unit per posting**, valutata
  nella valuta dello scenario. Oggi è Σ q/2: il cambio è `posting.quantum / _EXACT_TWO` →
  `posting.quantum` (`evaluator.py:2272-2282`).
- I controlli restano simmetrici e invariati nel codice: evaluator `:2702`, schema `:1958` e `:1960`,
  top-up `:3728`. Lo schema limita già ogni top-up a «posting arrotondati × minor unit» (`:1693`,
  `:2114`), quindi la banda è coerente.
- **Motivazione.** Con (a) l'aggregato sta in [0, Σq): la banda accetta ogni arrotondamento normale,
  anche con molte operazioni e conversioni. Il controllo stretto resta per posting
  (`ledger._validate_posting`, esatto): è lui a respingere un arrotondamento a favore del piano.
  Oltre la banda c'è solo un difetto, e la verifica esatta lo respinge (`ExactReplayRejectedError`).
- Un ammanco per pool resta pubblicato come top-up, entro «numero di posting × q».

### 2.4 Codifica SCIP

`_posted_units_term` (`constraints.py:393-431`) riceve il verso:

| Verso | Righe |
|---|---|
| credito | `q·u ≤ esatto ≤ q·u + q` |
| debito | `q·u − q ≤ esatto ≤ q·u` |

- A un multiplo esatto l'unico vicino in più è innocuo. Gli importi postati non entrano in alcun
  obiettivo (`explicit_cost` usa la commissione e lo spread esatti), quindi l'insieme fattibile
  coincide con quello esatto.
- `units_upper = ceil(esatto_max / q) + 1`; la riga `:nonneg` resta.
- Chiamate: debito d'acquisto `:484`, commissione `:494`, credito FX `:511`.
- Docstring da riallineare: `:1-31`, `:81`, `:292`, `:394-425`, `:441-460`.

### 2.5 C-FXPOS: una conversione attiva posta un credito

- Nuova riga `fx_decision ≤ ub · u_credit`, nome `posted_fx_credit:{route}:{pool}:active`, aggiunta da
  un kwarg facoltativo `active_decision` di `_posted_units_term`.
- Rispecchia `FX_CREDIT_POSITIVE` dell'evaluator (`evaluator.py:2420-2455`,
  `satisfied = action is None or posted_credit > 0`). Lo schema pubblica `destination_credit` come
  `PlannerPositiveMoneyInput`: un credito zero non sarebbe pubblicabile comunque.
- Nell'intestazione di `constraints.py`, `FX_CREDIT_POSITIVE` passa dal gruppo 2 («tautologia», `:21`)
  al gruppo 3 (righe vive).
- **Rischio residuo.** La tolleranza di SCIP può dare u = 1 mentre la verifica esatta posta 0: finisce
  in `ExactReplayRejectedError` → `execution_failed`. Raro: serve un credito esatto entro la
  tolleranza sotto un multiplo di q.

### 2.6 n. 15, B1: banda dei tassi e tasso peggiorativo

- In `normalize.validate_fx_coherence` (`normalize.py:661-704`) la condizione d'incoerenza
  `cross·kept·to_valuation > direct` diventa `> direct·(1 + β)`.
- β = h · (1/R₁ + 1/R₂ + 1/R₃) sui tre valori salvati del triangolo, con h = 5·10⁻¹¹: metà
  dell'unità della decima cifra, cioè l'errore di `Numeric(24, 10)` (`backend/app/db/models.py:978`).
  β è l'errore relativo al primo ordine del prodotto. La chiave «A/B» con A < B salva B per A.
- **Tasso di pianificazione** = min(approvato · (1 − s), val(origine) / val(destinazione)), dove val è
  il tasso verso la valuta dello scenario V. È uguale al tasso effettivo di oggi se origine o
  destinazione è V, o se i tassi sono coerenti; dentro la banda vale il triangolo attraverso V.
- Un helper esatto in `numeric.py`, condiviso da evaluator, vincoli e obiettivi.
- Lo spot pubblicato resta quello dell'utente; il tasso effettivo pubblicato è quello di
  pianificazione; `spread_loss` vale 0 quando il tasso è al triangolo. I validatori reggono: lo
  schema controlla solo effettivo ≤ spot e `spread_loss` ≥ 0 (`:1215-1218`, `:1245-1248`),
  `:1658` l'uguaglianza fra azione e conversione, `models.py:1018-1019` effettivo ≤ approvato.

Esempio con V = EUR, «EUR/RON» 4,97 e «EUR/USD» 1,085; il triangolo RON→USD è 31/142:

| «RON/USD» salvato | Esito |
|---|---|
| 0,2183098592 | δ 2,06·10⁻¹⁰ ≤ β 2,85·10⁻¹⁰ → valido, tasso al triangolo; 100 RON → 1550/71 → 21,83 USD; `spread_loss` 0 |
| 0,2183098593 | δ 6,65·10⁻¹⁰ > β → `allocation.fx_rate_inconsistent` |
| 0,2183098591 | sotto il triangolo → valido, tasso dell'utente; `spread_loss` 5,06·10⁻⁹ EUR |

### 2.7 Cosa non cambia

- Contratto 1.0.0; nessuna chiave i18n; nessun cambio al frontend oltre un commento.
- `post_half_up` (`numeric.py:235`) resta per chi lo usa; il formatter `wire_numbers` resta HALF_UP:
  è solo visualizzazione.
- `_total_resource_bound` (`evaluator.py:727-761`, `favorable_rounding_bound`): solo un commento. Il
  margine ora è prudente, e tenerlo lascia stabili i box delle decisioni e i domini dell'oracle.
- `calculate_effective_fx_rate` resta; i top-up restano come rete.

### 2.8 Opzioni scartate

| Opzione | Perché no |
|---|---|
| (b) costo minimo per passo | coefficiente nascosto |
| (c) soglia di polvere | l'8,7% degli spezzamenti guadagna ancora; R4 resta |
| (d) niente scambi inversi sullo stesso broker | cura solo R3 |
| (e) una sola conversione per broker e coppia | nel backlog |
| (f) HALF_UP + ammanco ≥ 0 | i pool si coprono a vicenda |
| (a′) pessimismo solo nel solver | prova e verifica esatta divergono |
| B2 (`spread_loss` ≥ −banda) | lascia l'incentivo e i guadagni |
| regola selezionabile | respinta |

### 2.9 Valori attesi con (a)

| Caso | Esatto → postato | Piano atteso |
|---|---|---|
| P1 | 11,18 USD → 9,98 EUR | nessun acquisto |
| P1 | 11,19 USD → 9,99 EUR | `ready_no_op` |
| P1 | 11,20 USD → 10,00572 → 10,00 EUR | compra 1 |
| R1b | 0,01 USD → 0,00 EUR | nessun acquisto e nessuna FX (C-FXPOS) |
| P2 | 1.101,89 EUR → 1.233,41087 → 1.233,41 USD < 1.233,42 | compra un solo asset (oggi due): ogni spezzamento dà Σ floor ≤ 1.233,41; quale asset, lo decide fixed_l2 per uno scarto minimo: il test non lo fissa |
| P2 | 1.101,90 EUR → 1.233,42206 → 1.233,42 USD | compra entrambi (controllo positivo, come oggi): i crediti confluiscono nella cella ib/USD |
| P2 | le conversioni spezzate di oggi, sotto floor | 1.233,40 USD in tutto: spezzare non conviene |
| P3 | 0,15 USD → 0,13401 → 0,13 EUR < 0,14 | solo lo stock (fixed_l2 2738,89 contro 134205,43) |
| P4 | debito 10,004 → 10,01 | nessun acquisto; con cassa 10,01 compra |
| CTRL | 10,00 EUR → 11,19 USD | compra |
| R1s | 11,20 USD, spread 0,1% → 9,99 EUR | nessun acquisto |
| R2s | totale esatto 1.232,177459 → 1.232,17 USD | nessun guadagno dallo spezzamento |

## 3. File e zone

| File | Zona | Cambio |
|---|---|---|
| `backend/app/services/pac_allocator/numeric.py` | `:198-212`, `:235-262`, `:293-325` | `post_floor`, `post_ceiling`, `calculate_planning_fx_rate`; `calculate_fx_credit` coi tassi verso V |
| `backend/app/services/pac_allocator/ledger.py` | `:17`, `:20-55`, `:73-85`, `:114-138` | verso per famiglia, posting contro il piano |
| `backend/app/services/pac_allocator/evaluator.py` | `:8`, `:727-761` (commento), `:1764-1817`, `:2272-2282`, `:2420-2455`, `:3659-3730` | banda Σq, tasso di pianificazione, testi dei top-up |
| `backend/app/services/pac_allocator/constraints.py` | `:1-31`, `:81`, `:126-212`, `:292-351`, `:393-431`, `:434-520` | verso nei posting, C-FXPOS, tasso di pianificazione in `ScenarioFacts` |
| `backend/app/services/pac_allocator/objectives.py` | `:167-205` | `_fx_effective_rate` col tasso di pianificazione |
| `backend/app/services/pac_allocator/normalize.py` | `:611-623`, `:661-704` | banda β |
| `backend/app/services/pac_allocator/models.py`, `planner.py` | `:1384`, `:28` | testi |
| `backend/app/schemas/pac_allocator.py` | `:1444-1446`, `:1482`, `:1553-1554`, `:1707` | descrizioni (fingerprint) |
| `frontend/src/lib/features/tools/pac-allocator/planner/result/StateNotice.svelte` | `:26` | solo commento |
| test in `backend/test_scripts/test_services/`, `test_api/`, `test_schemas/` | §4 S1 | rossi e churn, solo file già registrati |
| `mkdocs_src/docs/user/tools/pac-allocator/index.en.md` | `:226-249` | arrotondamento e banda; lontano dalla `:192` |
| journal `13_pacAllocator/` | questo piano, README, note datate | S6 |

Esclusi dai commit: `openapi.json`, `tool-contracts.openapi.json`, `tool-contract-map.generated.ts`,
`generated-tools.ts`, log, build, `.svelte-kit`.

## 4. Passi

### S0 — Piano e README ✅ 2026-10-09

> **Nota implementazione**: piano scritto alle 12:03 su `9b2acdd5d`, nel formato della riga 15.

> **⚠️ Fuori pista** (12:39): rileggendo `constraints.py:505-516` e `evaluator.py:765-786` prima di S1,
> lo script `p2_routes.py` del kit risulta sbagliato: finanziava ogni rotta con la sua conversione,
> mentre i crediti FX confluiscono nella cella broker/valuta. Corretti §2.2 e §2.9: P2 a 1.101,90 EUR
> compra entrambi; a 1.101,89 uno solo, per Σ floor ≤ floor Σ. Nessun effetto sulla cura.

| Comando | Ora, carico | Esito | Log |
|---|---|---|---|
| `git log -1`, `git status --porcelain`, `lsof -nP -iTCP:6151 -sTCP:LISTEN` | 12:03, 14.26 / 18.47 / 21.83 | `9b2acdd5d`, 0 righe, porta libera | — |

### S1 — Rossi col test-author ✅ 2026-10-09

Solo file già registrati nel runner. Il test-author scrive e compila; le suite le lancio io, una per
volta sulla 6151, per vedere i rossi.

| Selettore | File | Rossi e churn |
|---|---|---|
| `services pac-planner-core` | `test_pac_planner_exact.py`, `test_pac_planner_normalize.py` | `post_floor`, `post_ceiling`, `calculate_planning_fx_rate`; `calculate_fx_credit` coi nuovi kwarg (`:508-517`, `:548-556`); banda RON |
| `services pac-planner-evaluator` | `test_pac_planner_evaluator.py` | famiglie di posting `:2127-2180` (crediti per difetto, debiti per eccesso, aggiustamento in [0, q)); `rounding_bound` = Σq; top-up `:4637-5070`; tasso al triangolo dentro la banda |
| `services pac-planner-service` | `test_pac_planner_planner.py` | P1–P4, R1b, CTRL, R1s, R2s, `optimal_proven`, G3; R3 `:1137` e V2 `:1138`; R13 `:886-941`; pareggi `:375-476` |
| `services pac-planner-policies` | `test_pac_planner_policies.py` | A1 `:883-923`, A2 `:932-981`, A4 `:1028-1047` |
| `services pac-planner-oracle` | `test_pac_planner_oracle.py` | pareggio `:640-676` (40 fattibili, ottimo b = 3, fixed_l2 1); G3 sulla griglia |
| `services pac-planner-solver` | `test_pac_planner_solver.py` | C-FXPOS; docstring `:197-224` |
| `services pac-planner-report` | `test_pac_planner_report.py` | conversioni multiple `:759-800`; `:616` |
| `api pac-planner-tool` | `test_pac_planner_tool_api.py` | pareggio `:189-280` |
| `schemas pac-planner` | `test_pac_planner_schemas.py` | fingerprint `:3841-3855` |

> **Punto di ripresa** (15:50): i tre brief del test-author (A exact, normalize ed evaluator; B policies,
> oracle, solver e report; C planner, API e docstring dello schema) sono tornati; 11 file di test
> modificati, nessun file di produzione. Prossima azione: rossi per selettore sulla 6151, uno alla
> volta, poi revisione del diff e nota di S1.

> **⚠️ Fuori pista** (15:50): la pausa del coordinator (14:21) è arrivata mentre i tre test-author
> lavoravano, solo in-process e senza corsia; non ho potuto rispondere prima del loro ritorno. La
> ripresa è arrivata insieme: nessun comando sulla 6151 nel frattempo, porta libera.

> **Nota implementazione**: 95 rossi, tutti per la ragione attesa; nessun file di produzione toccato.
> I nomi nuovi passano da `NUM.<nome>` dentro i test, così un nome mancante fa fallire il suo test e
> non la raccolta del file. Ho riletto i diff di ogni brief e rifatto a mano l'aritmetica: ottimo
> dell'oracle, R3 110,007065 CHF, V2 110,005236 → 110,00, debiti del report da 2 a 4.

| Selettore | Rossi / verdi | Causa dei rossi | Log |
|---|---|---|---|
| `services pac-planner-core` | 45 / 185 | 40 `AttributeError` (`post_floor`, `post_ceiling`, `calculate_planning_fx_rate`), 4 `TypeError` (kwarg di `calculate_fx_credit`), 1 banda RON (`'invalid' == 'ready'`) | `_s1_core.log` |
| `services pac-planner-evaluator` | 14 / 156 | 7 famiglie, 2 posting malformati, tasso al triangolo, debito d'acquisto al soffitto, shortfall, 2 top-up | `_s1_evaluator.log` |
| `services pac-planner-policies` | 6 / 44 | A1, A2, C-FXPOS (riga attiva e replay a 0,8 USD), SCIP inammissibile ×2 | `_s1_policies.log` |
| `services pac-planner-oracle` | 4 / 20 | ottimo a mano e G3 sulla griglia ×3 | `_s1_oracle.log` |
| `services pac-planner-solver` | 0 / 40 | solo testi | `_s1_solver.log` |
| `services pac-planner-report` | 1 / 41 | conversioni multiple: credito GBP 4 contro 3 | `_s1_report.log` |
| `services pac-planner-service` | 24 / 56 | pareggi ×3, R13, R3 e V2, P1–P4, R1b, R1s, R2s, RON, G3 | `_s1_service.log` |
| `api pac-planner-tool` | 1 / 11 | pareggio: 3 unità invece di 2 | `_s1_api.log` |
| `schemas pac-planner` | 0 / 552 | solo docstring | `_s1_schemas.log` |

Comandi: `PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py test --test-port 6151
--data-dir /tmp/librefolio-r2-d <selettore>`, uno alla volta dalle 15:49 alle 15:54, con carico da
14 a 66 (load average a 1 minuto). Log in `/tmp/libreFolio_pacround_s1_*.log`, diff dei test in
`/tmp/libreFolio_pacround_s1_tests.diff`.

> **⚠️ Fuori pista** (15:55): differenze dal piano emerse nei brief, tutte accolte.
> - I test di C-FXPOS stanno in `test_pac_planner_policies.py`, non nella suite solver: il solver
>   resta solo testi.
> - L'oracle conta 40 candidati fattibili invece di 46, e 137 invece di 151. L'ottimo è {buy 3,
>   funding 4, fx 4}, con fixed_l2 1.
> - Il report si basa sulla precondizione R(9) e su una nuova mappa dei debiti: i debiti passano da
>   2 a 4, perché con 2 Σ floor = floor Σ e il test non distinguerebbe nulla.
> - Test in più: debito d'acquisto arrotondato a zero (ora 0,01, BUY_DEBIT_POSITIVE soddisfatto);
>   divisione del top-up in `:5120` (banda, rosso) e `:5140` (limite fabbricato, controllo verde);
>   credito di 0,8 USD che va a zero; validazione del tasso di pianificazione.
> - BUY_DEBIT_POSITIVE resta come difesa in profondità, anche se con (a) non può più scattare.
>   `_total_resource_bound` mantiene il suo margine, con solo un commento.
> - I test-author hanno corretto alcuni valori del §2.9: R3 vale 110,007065; P1-11.20 è già rosso
>   oggi; R2s è rosso solo tramite G3; il test di giunzione `:490` è verde in entrambi i casi.

### S2 — Cura (a), banda e C-FXPOS ✅ 2026-10-09

`numeric.py` → `ledger.py` → `evaluator.py` (banda, testi) → `constraints.py` (verso, C-FXPOS,
intestazione).

> **Nota implementazione**: 95 rossi → 27, e i 27 rimasti sono tutti B1/β (S3); nessun rosso nuovo.
> - `numeric.py`: `post_floor` e `post_ceiling`, in aritmetica intera sul quanto, con la stessa
>   validazione di `post_half_up`; docstring di `PostedAmount` riscritta. `post_half_up` resta.
> - `ledger.py`: tabella esplicita `_PLAN_ROUNDING` (2 floor, 5 ceiling) col commento sul perché
>   spezzare non conviene; `_ROUNDED_FAMILIES` ne deriva; validazione e posting usano la regola della
>   famiglia; messaggio «must post its floor/ceiling against the plan».
> - `evaluator.py`: banda Σq (`posting.quantum` al posto di `/ _EXACT_TWO`) col commento sulla
>   motivazione; testi della docstring e dei top-up («safety net»); su `_total_resource_bound` solo
>   un commento, il margine resta.
> - `constraints.py`: `_posted_units_term(side=…)` con le coppie non strette del §2.4,
>   `units_upper = ceil(max/q) + 1`; `active_decision` aggiunge la riga
>   `posted_fx_credit:{route}:{pool}:active`; `FX_CREDIT_POSITIVE` passa al gruppo 3; docstring
>   riallineate.

| Selettore | Rossi / verdi dopo S2 | Rossi rimasti | Log |
|---|---|---|---|
| `services pac-planner-core` | 24 / 206 | 23 del tasso di pianificazione e dei kwarg di `calculate_fx_credit`, 1 banda RON | `_s2_core.log` |
| `services pac-planner-evaluator` | 1 / 169 | tasso al triangolo | `_s2_evaluator.log` |
| `services pac-planner-policies` | 0 / 50 | — | `_s2_policies.log` |
| `services pac-planner-oracle` | 0 / 24 | — | `_s2_oracle.log` |
| `services pac-planner-solver` | 0 / 40 | — | `_s2_solver.log` |
| `services pac-planner-report` | 0 / 42 | — | `_s2_report.log` |
| `services pac-planner-service` | 2 / 78 | RON e banda di coerenza (`allocation.fx_rate_inconsistent`) | `_s2_service.log` |
| `api pac-planner-tool` | 0 / 12 | — | `_s2_api.log` |

Comandi come in S1, uno alla volta dalle 15:58 alle 16:00; porta 6151 libera dopo l'API.

### S3 — B1 e β ✅ 2026-10-09

`numeric.py` (tasso di pianificazione) → `normalize.py` (β) → evaluator, vincoli e obiettivi.

> **Nota implementazione**: 27 rossi → 0; tutte le suite PAC del backend verdi.
> - `numeric.py`: `calculate_planning_fx_rate` = min(`calculate_effective_fx_rate`, val(origine) /
>   val(destinazione)); approvato e spread validati dal tasso effettivo, i tassi verso V devono essere
>   `ExactRatio` positivi. `calculate_fx_credit` ha i due kwarg obbligatori e usa il tasso di
>   pianificazione.
> - `normalize.py`: `_FX_STORED_RATE_HALF_UNIT` = 1/(2·10¹⁰) col riferimento a `FxRate.rate`
>   `Numeric(24, 10)`; `_stored_fx_rate` ricava il valore salvato dietro un tasso orientato; la
>   condizione diventa `cross·kept·to_valuation > direct·(1 + β)`. Docstring riscritta.
> - `evaluator.py`: `_valuation_rate_of` (stesso errore di contratto di `_to_valuation`, che ora lo
>   usa); `_evaluate_fx` pubblica come `effective_rate` il tasso di pianificazione e il credito esatto
>   ne deriva, `approved_rate` resta lo spot; `spread_loss` invariato nella formula, vale 0 al
>   triangolo. `_fx_constraint_facts` passa gli stessi tassi verso V. Import di
>   `calculate_effective_fx_rate` tolto, non serve più.
> - `constraints.py`: `planning_fx_rate(facts, …)` in float, specchio dell'helper esatto, esportato;
>   lo usano il credito FX del ledger e `credit_upper`.
> - `objectives.py`: `_fx_effective_rate` tolto, lo stadio dei costi usa `planning_fx_rate`; import
>   di `fx_rate` tolto.

| Selettore | Rossi / verdi dopo S3 | Log |
|---|---|---|
| `services pac-planner-core` | 0 / 230 | `_s3_core.log` |
| `services pac-planner-evaluator` | 0 / 170 | `_s3_evaluator.log` |
| `services pac-planner-service` | 0 / 80 | `_s3_service.log` |
| `services pac-planner-policies` | 0 / 50 | `_s3_policies.log` |
| `services pac-planner-oracle` | 0 / 24 | `_s3_oracle.log` |
| `services pac-planner-solver` | 0 / 40 | `_s3_solver.log` |
| `services pac-planner-report` | 0 / 42 | `_s3_report.log` |
| `api pac-planner-tool` | 0 / 12 | `_s3_api.log` |

Comandi come in S1, uno alla volta dalle 16:03 alle 16:06; porta 6151 libera dopo l'API.

### S4 — Testi dello schema, fingerprint, commenti, `api sync` ✅ 2026-10-09

Prova con uno script di revert che solo i testi approvati spostano le fingerprint, come per la riga 15.

> **Nota implementazione**: «HALF_UP» sparisce dai testi del PAC; restano solo `post_half_up` e
> `wire_numbers.py:162`, che riguardano la visualizzazione.
> - `schemas/pac_allocator.py`:
>   - commento di `:1444`, «rounding against the plan»;
>   - docstring di `PlannerRoundingTopUp` (`:1482`);
>   - descrizione di `rounding_top_ups` (`:1707`);
>   - nuova descrizione di `rounding_bound` (`:1554`): «One minor unit per rounded posting, in the
>     valuation currency: each posting rounds against the plan by less than its unit.»
> - `models.py:1384` (docstring di `ExactRoundingTopUp`), `planner.py:28` (docstring del modulo,
>   riallineata a 78 colonne), `StateNotice.svelte:26` (solo commento).
> - Impronte nuove: PAC `cd7e7ef7…c365` (era `a999932e…cbad`), Rebalancer `9440a5e6…debba` (era
>   `a1daf513…7822`). Il test-author ha cambiato solo i due valori e il commento del motivo in
>   `test_pac_planner_schemas.py:3842`.
> - **Prova di revert**, `/tmp/libreFolio_pacround_fingerprints.py`, exit 0:
>   - il modulo dello schema preso da `HEAD` (`git show`, caricato in memoria) ritrova i valori
>     congelati;
>   - il diff strutturale HEAD → worktree degli schemi generati tocca solo i nodi approvati: 4 nel PAC
>     (la descrizione di `rounding_top_ups` compare in `PacDeploymentSolution` e
>     `PacIncumbentSolution`, che la ereditano), 1 nel Rebalancer (`rounding_bound`);
>   - annullati quei nodi, entrambe le impronte tornano ai valori congelati.
> - `schemas pac-planner`: 2 rossi attesi (le impronte), 550 verdi; dopo il test-author, 552 verdi.
> - `api sync` alle 16:14, exit 0: `tool-contracts.openapi.json` ha i testi nuovi e nessun «HALF_UP».
>   I file generati sono ignorati da git.
>
> **⚠️ Fuori pista**:
> - Lo script, come lo avevo scritto, cercava la descrizione di `rounding_top_ups` sotto la
>   definizione `PacPlanSolution`, che non compare negli schemi generati. Ora attribuisce i campi
>   ereditati attraverso le sottoclassi vere, e non per nome.
> - La docstring di `PlannerRoundingTopUp` elencava i posting arrotondati in modo incompleto: «BUY
>   debit, nonzero fee, FX credit». Ora dice «BUY debit, SELL credit, fee, tax, FX credit», le 7
>   famiglie del ledger, e precisa «nonzero», perché un importo zero non genera un posting. È la
>   stessa docstring approvata, e quindi la stessa impronta.

### S5 — Kit di riproduzione e suite PAC ✅ 2026-10-09

`repro.py` e `repro_spread.py` devono dare i valori del §2.9; poi tutte le suite PAC, una per volta.

> **Nota implementazione**: uno script di servizio, in processo, senza DB né server, riusa le stesse
> richieste del kit HALF_UP (`repro.py`, `repro_spread.py`) e aggiunge le 3 righe B1 del §2.6. Su ogni
> caso valido controlla G1 (`optimal_proven`, `completed`), I1 (ogni posting arrotondato va contro il
> piano), I2 (l'arrotondamento non crea valore) e I3 (ogni credito FX è diverso da zero). Esito: 80
> controlli su 80, exit 0 (`/tmp/libreFolio_pacround_s5_repro.log`).
>
> | Caso | Prima (HALF_UP, senza β) | Ora, (a) e B1 |
> |---|---|---|
> | P1 11.18 USD | nessun acquisto | 9.98 EUR, `ready_no_op` |
> | P1 11.19 USD | comprava | 9.99679 → 9.99 EUR, `ready_no_op` |
> | P1 11.20 USD | comprava | 10.00572 → 10.00 EUR, compra 1 |
> | R1b | convertiva 0.01 USD → 0.01 EUR | `ready_no_op`, nessun FX |
> | P2 1101.89 EUR | 2 conversioni, 1233.42 USD | 549.99 EUR → 615.63 USD, compra un solo titolo |
> | P2 1101.90 EUR | — | 1233.42206 → 1233.42 USD, compra entrambi |
> | P2 spezzata | 0.15 + 1233.27 = 1233.42 | 0.14 + 1233.26 = 1233.40: spezzare non conviene |
> | P3 | andata e ritorno | solo l'azione, nessun FX; `fixed_l2` 2738.889722 |
> | P4 10.00 EUR | comprava a 10.00 | debito 10.004 → 10.01, `ready_no_op` |
> | P4 10.01 EUR | — | compra, debito 10.01 |
> | CTRL | compra | 10.00 EUR → 11.19 USD, compra (invariato) |
> | R1s, spread 0.1% | comprava | 9.995718 → 9.99 EUR, `ready_no_op` |
> | R2s, spread 0.1% | 2 conversioni | 551.37 EUR → 616.56 USD, un solo titolo; ≤ 1232.17 accreditati |
> | B1 0.2183098592 | `fx_rate_inconsistent` | valido; tasso 31/142; 100 RON → 21.83 USD; `spread_loss` 0 |
> | B1 0.2183098593 | `fx_rate_inconsistent` | `invalid`, `allocation.fx_rate_inconsistent` |
> | B1 0.2183098591 | valido | tasso dell'utente; `spread_loss` 5.063·10⁻⁹ EUR |
>
> Suite PAC sulla 6151, una per volta (`/tmp/libreFolio_pacround_s5_suites.sh`, log
> `/tmp/libreFolio_pacround_s5_<selettore>.log`), tutte exit 0:
>
> - `services pac-planner-core` 230, `-evaluator` 170, `-oracle` 24, `-policies` 50, `-solver` 40,
>   `-proof` 30, `-wire-numbers` 39, `-report` 42, `-service` 80: 705 verdi;
> - `schemas pac-planner` 552;
> - `api pac-planner-tool` 12; porta 6151 libera dopo (`lsof` exit 1).
>
> Nessun churn: i test non cambiano in questo passo. Le vecchie impronte restano solo in un `.pyc`
> ignorato; i «HALF_UP» rimasti nei test sono racconto storico o la regola di visualizzazione, non
> asserzioni sulla regola vecchia. Nessun test della piattaforma Tool fissa un digest del catalogo.

### S6 — Journal ✅ 2026-10-09

Note datate «Aggiornamento del 2026-10-09» in `plan-phase00PacRebalancerMathematicalCore.prompt.md`,
`plan-phase00PacRebalancerTargetDesign.prompt.md` (§4.4) e `review/PAC_ALLOCATOR_REVIEW_DOSSIER.md`;
README.

> **Nota implementazione**: tre note datate, ciascuna subito dopo quella del 2026-09-25 e nello stesso
> stile; ognuna prevale sul testo sotto e sulla nota del 2026-09-25. Il testo storico resta com'è.
> - **MathCore**, in italiano: regola (a) con le 7 famiglie, «solo alla fine», bound
>   $0\le A_{round}<\sum_j\mu_{c_j}\rho_{c_j\to v}$ e banda Σq, QX1-b ora prudente coi top-up come
>   rete, C-FXPOS, B1 con β e il tasso di pianificazione. Sezioni toccate: §2.2, §6.2, §7.1, §7.3,
>   §12.2 e §13.
> - **TargetDesign**, in italiano, più breve, rimanda al MathCore. Sezioni toccate: §4.4 (ultimo
>   paragrafo) e §6.5 (riserva fiscale per eccesso).
> - **Dossier**, in inglese, col perché: l'esempio 1.101,89 EUR, cioè 1.233,41087… USD; spezzato,
>   valeva 0,15 + 1.233,27 = 1.233,42 USD con HALF_UP, ora 0,14 + 1.233,26 = 1.233,40. Ho rifatto i
>   conti in `Decimal`. Sezioni toccate: §1 (la correzione del 2026-10-09 della riga 15, che B1
>   affina), §3.2 e §5.7.
> - README: riga 16 «🔄 S0–S6 ✅».
>
> I «HALF_UP» rimasti nei tre documenti sono storia: il difetto del modello trovato dal gate
> d'accordo (dossier §5.6, §9.2), il testo sotto le note e la nota del 2026-09-25. Le fee e i buffer
> FX in HALF_UP (MathCore §7.2) non vanno più fatti dal 02/10.
>
> **⚠️ Fuori pista** (16:27): il §0 di questo piano attribuiva al §4.4 del TargetDesign la frase
> «nessuna conversione deve creare valore». Non c'è, né lì né altrove nella suite: è la parafrasi
> del coordinator. Il §4.4 del TargetDesign parla di sintassi lessicografica e, in chiusura, di
> HALF_UP; l'unico «§4.4 FX» è nella bozza archiviata `drafts/pac-rebalancer-end-to-end-design.md`.
> Corretto il §0: il principio è nel MathCore, §7.3.

### S7 — Pagina utente col docs-writer ✅ 2026-10-09

`index.en.md:243-249` (arrotondamento contro il piano) e una frase sulla banda in `:226-241`. Gate:
`mkdocs build` strict e `check-links`.

> **Nota implementazione**: il docs-writer ha toccato solo il passo FX di `index.en.md`, +17 −3,
> lontano dalla `:192` (righe 186–202 intatte). La pagina è solo EN, quindi niente stamp.
> - Dopo «…covers the difference.» (`:241`): la banda dei dieci decimali, poi il tasso usato
>   $\min\big(x_{\text{CHF}\to\text{USD}}(1-s),\ x_{\text{CHF}\to\text{EUR}}/x_{\text{USD}\to\text{EUR}}\big)$,
>   che vale $x(1-s)$ quando i tassi sono coerenti.
> - Al posto di «rounded half up»: ogni importo si arrotonda una volta alla minor unit, contro il
>   piano. Ciò che il piano riceve va per difetto, ciò che paga per eccesso. Quindi spezzare non
>   conviene, e la parte «Rounding» di **Not invested** non è mai negativa: è `accounting_rounding_adjustment`
>   (`models.py:927-931`), positiva sui debiti; il segno l'ho verificato.
> - La frase su «≈ −0.0022» resta com'è. Nella colonna del ledger un credito per difetto è negativo,
>   e il testo non dice il contrario.
>
> Gate:
> - `PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py mkdocs build` → exit 0,
>   nessun WARNING/ERROR (`/tmp/libreFolio_pacround_s7_mkdocs_build.log`).
> - `… dev.py mkdocs check-links` → exit 1: 89 link validi, fra cui `user/tools/pac-allocator`, e 1 rotto
>   (`/tmp/libreFolio_pacround_s7_check_links.log`).
>
> **⚠️ Fuori pista**:
> - La frase del docs-writer «The rate shown stays the one you set…» era ambigua: il piano mostra due
>   tassi, «spot» e «effective» (`OperationalPlan.svelte:139-145`). L'ho riscritta io: «Your rates are
>   not changed: each conversion of the plan shows the rate it starts from as *spot* and the rate it
>   uses as *effective*.»
> - Il link rotto c'era già e non è di D: `user/assets/detail/chart/#rolling-return`, da
>   `frontend/src/routes/(app)/assets/[id]/+page.svelte:3012`. L'ancora `{: #rolling-return }` c'è in
>   `chart.en.md:22`, ma manca nelle pagine it/fr/es. I due file sono intatti a `9b2acdd5d`
>   (`git status` vuoto), quindi non lo correggo: lo segnalo al coordinator.

### S8 — Gate della corsia ✅ 2026-10-09

`api sync` → `front build --debug` → `front check` → `core-unit` → `component-unit` → `i18n audit` →
`check-orphans` → `lint`; poi `lsof -nP -iTCP:6151 -sTCP:LISTEN`.

> **Nota implementazione**: script sequenziale `/tmp/libreFolio_pacround_s8_gates.sh`, un comando per
> volta, sulla base `9b2acdd5d`. Riassunto in `/tmp/libreFolio_pacround_s8_summary.txt`, log in
> `/tmp/libreFolio_pacround_s8_*.log`. Il carico della macchina era alto, fra 24 e 129.
>
> | Comando | Ora, durata | Esito |
> |---|---|---|
> | `api sync` | 16:45, 14 s | exit 0; contratti tool `efe2e307…` |
> | `front build --debug` | 16:45, 151 s | exit 0 |
> | `front check` | 16:48, 92 s | 0 errori, 0 avvisi |
> | `front-utility core-unit` | 16:49, 74 s | 118 file, 3452 passati |
> | `front-utility component-unit` | 16:51, 198 s | 111 file, 2899 passati |
> | `i18n audit` | 16:54, 17 s | 4199 chiavi, tutte complete; 0 inutilizzate; 0 chiavi backend mancanti |
> | `check-orphans` | 16:54, 7 s | 245 file backend, tutti raggiungibili da `all` |
> | `lint` | 16:54, 5 s | «All checks passed!» |
> | `lsof -nP -iTCP:6151 -sTCP:LISTEN` | 16:55 | nessun listener |
>
> - Vitest e i18n danno gli stessi conti della riga 15: il frontend cambia solo per un commento, e
>   nessuna chiave è cambiata.
> - `git diff --check` pulito. Delta: 25 file tracciati modificati più questo piano, nuovo. I file
>   generati da `api sync` restano ignorati: `openapi.json`, `tool-contracts.openapi.json`,
>   `generated.ts`, `generated-tools.ts`, `tool-contract-map.generated.ts`.
>
> **⚠️ Fuori pista**: controllo di formato in sola lettura (`/tmp/libreFolio_pacround_s8_format.sh`):
> `black --check` su ogni file Python toccato e Prettier su `StateNotice.svelte`, worktree contro
> `HEAD`.
> - Una sola regressione mia: `test_pac_planner_exact.py:699-720`, il rosso B1 del S1, con gli
>   `assert (…) == …` fra parentesi. `HEAD` era pulito, quindi ho passato `black` su quel solo file.
>   Cambiano solo le righe 704–720 → 704–714, a parità di semantica.
>   - Poi `services pac-planner-core`: 230 passati (`/tmp/libreFolio_pacround_s8_09_core_after_black.log`).
>   - Poi `lint`: «All checks passed!». Porta libera.
> - `test_pac_planner_schemas.py` resta fuori formato in due blocchi, con corpo identico a `HEAD`:
>   `:2028` e `:3924` a `HEAD`, `:2028` e `:3925` nel worktree, perché le impronte del S4 allungano il
>   file di una riga. È debito ereditato: non lo tocco. Prova in
>   `/tmp/libreFolio_pacround_s8_schemas_{wt,head}.diff`.
> - Gli altri file sono puliti sia nel worktree sia a `HEAD`.

### S9 — Record dei commit e checkpoint ✅ 2026-10-09

`/tmp/libreFolio_commits/d-pacround-C1..C3.txt` (solo ASCII, soggetto ≤ 50, righe ≤ 72), `.paths` e
`d-pacround-blobs.txt`; CHECKPOINT READY al coordinator, poi FROZEN.

> **Nota implementazione** (16:59, carico 50.73 / 66.85 / 53.42):
> - Record in `/tmp/libreFolio_commits/`, con una copia nella cartella di sessione
>   (`files/pacround/records/`):
>   - `d-pacround-C1.txt` e `.paths`: `fix(pac): round postings against the plan`. 20 percorsi: 9 di
>     produzione backend, 10 test e il commento di `StateNotice.svelte`.
>   - `d-pacround-C2.txt` e `.paths`: `docs(pac): rounding never favours the plan`. 1 percorso, la
>     pagina utente EN.
>   - `d-pacround-C3.txt` e `.paths`: `docs(journal): row 16 PAC rounding direction`. 5 percorsi:
>     questo piano (nuovo), README, MathCore, TargetDesign e dossier.
>   - `d-pacround-blobs.txt`: `git hash-object` e percorso dei 26 file, calcolato dopo quest'ultima
>     modifica.
> - 20 + 1 + 5 = 26, cioè i 25 file tracciati modificati più il piano. Stage vuoto; nessun file
>   generato, log, build o `.testLog` nei record.
> - Messaggi in ASCII: «≈» diventa «approx (~)». Controllo automatico di soggetto ≤ 50, righe ≤ 72 e
>   assenza di byte non ASCII.
> - Riga del README: «🔄 S0–S9 ✅ … CHECKPOINT READY, in attesa degli SHA», come la riga 15 al suo
>   checkpoint. Il ✅ con gli SHA lo mette il coordinator.
> - `git diff --check` pulito; porta 6151 libera. CHECKPOINT READY al coordinator, poi FROZEN.

### S10 — Chiusura: SHA e debito di formato ✅ 2026-10-09

Via del coordinator alle 18:15, base `083ed26dc` (treno 26). Due commit in un solo checkpoint:
`style(pac)` passa `black` sul solo `test_pac_planner_schemas.py`; `docs(journal)` chiude la riga 16
con gli SHA.

> **Nota implementazione** (18:17–18:19, carico alle 18:19: 45.02 / 38.90 / 26.24):
> - Base verificata: `HEAD` `083ed26dc`, albero pulito, stage vuoto, porta 6151 libera.
> - `black --check --diff` sul file dà gli stessi due blocchi del S8, `@@ -2028,18 +2028,11 @@` e
>   `@@ -3925,17 +3918,11 @@`, con corpo identico a `/tmp/libreFolio_pacround_s8_schemas_wt.diff`.
>   Sono due comprehension su più righe che `black` riporta su una, dentro le 300 colonne di
>   `pyproject.toml`. Secondo `git blame`, le 15 righe tolte vengono tutte da `ac18ce097` (riga 11).
> - `black` sul solo file (26.5.1, configurazione del progetto). Delta: 1 file, +2 −15, AST identico a
>   `HEAD`; `black --check`, `ruff check` e `git diff --check` puliti.
> - `schemas pac-planner` sulla 6151: 552 passati, come al S4 (`/tmp/libreFolio_pacclose_schemas.log`).
> - Journal: riga 16 del README con gli SHA e paragrafo «Stato»; qui lo stato, il S10 e il §8.
> - Record in `/tmp/libreFolio_commits/d-pacclose-*`.

## 5. Commit proposti

1. `fix(pac): round postings against the plan` — codice, test, testi dello schema, commento di
   `StateNotice.svelte`.
2. `docs(pac): rounding never favours the plan` — pagina utente EN.
3. `docs(journal): row 16 PAC rounding direction` — questo piano, README, note datate.

## 6. CHANGELOG

Voce PAC (`CHANGELOG.md:18`), la scrive il coordinator; niente «Fixed», il tool non è uscito. Testo
proposto, al posto della frase sull'arrotondamento:

> Every booked amount is rounded to the smallest unit of its currency against the plan — amounts
> received are rounded down, amounts paid up — so rounding never improves a plan and splitting a
> conversion gains nothing; the plan shows the rounding difference with the digits it needs, marked ≈
> when the figure shown is rounded.

E, dopo la frase sui cambi coerenti:

> A gap small enough to come from storing rates with ten decimals is tolerated, and the conversion
> then uses the rate through the valuation currency.

## 7. Definizione di fatto

- [x] (a) su tutte e 7 le famiglie, nel ledger, nell'evaluator e nel modello SCIP (S2).
- [x] Banda Σq; controlli simmetrici invariati; top-up come rete (S2).
- [x] C-FXPOS come riga viva (S2).
- [x] B1 con β; spot pubblicato invariato; contratto 1.0.0 (S3).
- [x] Valori del §2.9 riprodotti dal kit; tutti i casi `optimal_proven` o `ready_no_op` (S5, 80/80).
- [x] Rossi visti rossi, poi verdi; churn spiegato riga per riga (S1: 95 rossi → S2: 27 → S3: 0).
- [x] Fingerprint spostate solo dai testi approvati (prova di revert, S4).
- [x] Pagina utente EN e `mkdocs build` strict verde (S7). `check-links` è rosso solo per un link
      che c'era già e non è di D (`#rolling-return` in it/fr/es); quello del PAC è valido.
- [x] Gate della corsia verdi; porta 6151 libera (S8).
- [x] Record dei commit, CHECKPOINT READY, FROZEN (S9).

## 8. Avanzamento

| Passo | Stato |
|---|---|
| S0 piano | ✅ 2026-10-09 12:03 |
| S1 rossi | ✅ 2026-10-09 15:55 — 95 rossi, 0 inattesi |
| S2 cura (a) | ✅ 2026-10-09 16:00 — 95 → 27 rossi, tutti B1 |
| S3 B1 | ✅ 2026-10-09 16:06 — 27 → 0 rossi; 8 selettori verdi |
| S4 schema | ✅ 2026-10-09 16:15 — impronte mosse solo dai 3 testi approvati; 552 verdi; `api sync` |
| S5 kit e suite | ✅ 2026-10-09 16:23 — kit 80/80 sul §2.9 e §2.6; 705 + 552 + 12 verdi |
| S6 journal | ✅ 2026-10-09 16:29 — note datate in MathCore, TargetDesign e dossier; README |
| S7 pagina utente | ✅ 2026-10-09 16:44 — `index.en.md` +17 −3; build strict verde; check-links: 1 rosso preesistente non di D (`#rolling-return` it/fr/es) |
| S8 gate | ✅ 2026-10-09 16:57 — 8 gate verdi (check 0/0, core 3452, component 2899, i18n 4199); black su `exact.py`, core 230; porta libera |
| S9 checkpoint | ✅ 2026-10-09 16:59 — record C1–C3 (20 + 1 + 5 percorsi) e blob; CHECKPOINT READY; FROZEN in attesa degli SHA |
| S10 chiusura | ✅ 2026-10-09 18:19 — `style(pac)` su `test_pac_planner_schemas.py` (AST identico, 552 verdi); SHA della riga 16 nel README e nello stato |
