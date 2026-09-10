# Contratto PAC P1-r3 - analisi della situazione iniziale

**Stato:** N1/C1/X1 approvati; implementazione D integrata con runtime a
`d018e8a677289b9bc38e65b437a86e1f2684caa7`. Verifica combinata: 816 test schema,
194 test service/evaluator e statiche mirate verdi. Codec/codegen C/D end-to-end
restano pendenti. Due tentativi infrastrutturali pre-pytest sono registrati nelle
evidenze; nessuna dipendenza installata.

## 1. Scopo

P1 riceve un draft manuale e restituisce:

- valori iniziali nativi e in valuta report;
- cash esistente e contributi, separati e combinati per valuta;
- pesi correnti per riga;
- target per riga e scostamenti;
- score iniziale esatto;
- input normalizzato solo quando pronto;
- issue tipizzate e fatti parziali per draft incompleti.

P1 non accetta ordini, fee, vendita, riserve, FX di esecuzione o solver. Non interroga
DB, Portfolio, Broker, Asset, FX provider o clock.

## 2. Versioni e seam piattaforma

| Campo | Valore |
|---|---|
| `tool_code` | `pac_allocator` |
| `contract_version` | `1.0.0` |
| `implementation_version` | `1.0.0` |
| `component_key` | `pac-allocator` |
| `ui_contract_version` | `1` |
| operazione P1 | `analyze` |

`operation` e un discriminatore obbligatorio senza default. I veri modelli Pydantic e
TypeAdapter sono la fonte di verita. Nessun JSON Schema scritto a mano o endpoint schema
separato.

Il futuro wrapper usa la base C reale:

- `ToolPlugin[I, O]`;
- `input_type` e `output_type`;
- metadata `name_i18n_key` e `description_i18n_key`;
- `compute(parameters, context)`;
- `context.checkpoint()` come hook atomico;
- tempi nel response envelope C, non nel risultato finanziario.

Ogni item compute ha il proprio worker. Nessun coalescing fisico in questa versione.

## 3. Input

### 3.1 Root

`PacAnalyzeInput`:

| Campo | Tipo/limite |
|---|---|
| `operation` | literal `"analyze"` |
| `report_currency` | stringa draft max 8 o null |
| `as_of_date` | ISO draft max 10 o null |
| `rows` | max 32, default vuoto |
| `cash_balances` | max 4 o null |
| `contributions` | max 4 o null |
| `valuation_rates` | max 4, default vuoto |

`null` significa non fornito. Un array vuoto di cash/contributi e una dichiarazione
completa di nessun importo. Nessun `null` diventa zero.

### 3.2 Righe

`PacAnalyzeRowInput`:

- `row_key`: ASCII stampabile U+0021..U+007E, 1..256;
- `instrument_key`: stesso dominio, 1..128;
- `name`: Unicode scalar valido, max 128;
- `initial_quantity`: stringa Decimal draft o null;
- `quote`: prezzo nativo, valuta, quote basis, data;
- `target_percent`: stringa Decimal draft o null;
- `buy_grid`: `whole|fractional` e passo quantita.

Il nome e solo label. Il core non decodifica broker da `row_key`.

### 3.3 Denaro e tassi

- Cash e contributi sono vettori chiusi separati.
- Duplicati di valuta sono invalidi, non sommati.
- Cash negativo e fuori dominio P1; contributo negativo e invalido.
- Tasso `rate_to_report` = valore in valuta report di una unita nativa.
- Tassi devono essere positivi.
- Identita report/report e sempre 1.
- Un tasso estero mancante non diventa 1.
- Un tasso non usato resta dichiarato e produce issue informativa.

## 4. Dominio numerico

| Regola | P1 |
|---|---|
| righe | max 32 |
| valute attive | max 4 incl. report |
| testo numerico | max 64 caratteri |
| cifre | max 12 intere + 12 frazionarie significative |
| quote basis | 1 o 100 |
| inventario | finito, non negativo |
| prezzo/FX/passo | finito e positivo |
| target riga | 0..100 |
| totale target | esattamente 100 |
| contesto Decimal | precisione locale 256 |
| approssimazione rapporto | 28 decimali, truncation verso zero |
| parametri | max 128 KiB |
| risultato | max 256 KiB |
| issue non-ready | max 384 |
| issue ready | max 80, solo informative |

Sintassi ammessa: fixed-point ordinario. Spazi esterni e zeri ridondanti possono essere
normalizzati senza cambiare valore. Esponente, `NaN`, infinito, bool e testo misto sono
invalidi. Precisione eccedente e `unsupported`, mai arrotondata nel dominio.

## 5. Output

`PacAnalyzeOutput` e una union discriminata per `availability`.

Campi root sempre presenti:

- `operation="analyze"`;
- `result_kind="initial_state_analysis"`;
- `numeric_policy_id="pac-initial-state-v1"`;
- `trade_feasibility="not_evaluated"`;
- `optimization="not_run"`;
- `rows`, `cash_pools`, `totals`, `issues`;
- `normalized` non-null solo per `ready`.

Fatti:

- available: `value` presente, `reason_codes=[]`;
- unavailable: `value=null`, un solo reason primario.

Reason chiuse:

- `input_missing`;
- `input_invalid`;
- `outside_p1_domain`;
- `dependency_unavailable`;
- `zero_initial_invested_value`.

Le issue usano path max 4 con token chiusi e indici 0..31. `related_row_indices` e
ordinato, univoco e max 32. Nessuna label, input raw, eccezione o HTML entra nelle issue.

## 6. Calcoli

Per riga:

$$
N_i = q_i^0 \frac{p_i}{Q_i},
\qquad
V_i = N_i r_{c_i},
\qquad
E_0 = \sum_i V_i.
$$

Per valuta:

$$
C_c = b_c + a_c.
$$

Cash e contributi vengono contati una volta ciascuno. I costi non esistono in P1 e non
possono essere confusi con investimento.

Quando $E_0 > 0$:

$$
w_i = \frac{100 V_i}{E_0},
\qquad
n_i = 100 V_i - t_i E_0,
\qquad
e_i = \frac{n_i}{E_0}.
$$

Score per righe asset x contesto:

$$
D_\infty = \frac{\max_i |n_i|}{E_0},
\qquad
D_2 = \frac{\sum_i n_i^2}{E_0^2}.
$$

Numeratori e denominatori restano esatti. `approximation` e presentazione, non tolleranza
di fattibilita o uguaglianza.

Se una riga non puo essere valorizzata, il denominatore completo resta indisponibile.
Non si rinormalizza il sottoinsieme noto.

## 7. Classificazione

### Missing

`rows_required`, `field_required`, `incomplete_decimal`, `quote_required`,
`grid_required`, `cash_vector_required`, `valuation_rate_required`.

### Invalid

`invalid_decimal_syntax`, `invalid_currency`, `invalid_date`,
`reference_after_asof`, `nonpositive_price`, `nonpositive_fx_rate`,
`invalid_quote_basis`, `target_percent_out_of_range`, `target_total_not_100`,
`nonpositive_quantity_step`, `noninteger_whole_step`, `negative_contribution`,
`duplicate_row_key`, `duplicate_currency`, `identity_rate_mismatch`.

### Unsupported

`numeric_domain_exceeded`, `currency_domain_exceeded`, `quote_basis_unsupported`,
`short_inventory_unsupported`, `initial_debt_unsupported`.

### Info

`inventory_off_buy_grid`, `reference_date_unspecified`,
`unused_valuation_reference`, `identity_rate_redundant`.

## 8. Unicode e wire

- Serializzazione compatta UTF-8 equivalente a `ensure_ascii=False`.
- Coppie valide/non-BMP accettate.
- Surrogati isolati rifiutati in valori e chiavi oggetto.
- Nessuna normalizzazione NFC/NFD.
- Nessuna sostituzione `TextEncoder`.
- Nessun risultato JSON doppiamente codificato.
- Le lunghezze Tool generate devono contare code point come Pydantic, non code unit
  UTF-16.

Witness codegen futuri: nome 128/129 non-BMP, cella raw 64/65, surrogate valido/isolato,
escaping controlli, bytes reali 128/256 KiB.

## 9. Witness normativi

| Caso | Atteso |
|---|---|
| draft vuoto | `needs_input`, nessun portfolio zero inventato |
| q=10.125, prezzo 10, grid whole 1 | q preservata, valore 101.25, issue off-grid |
| q=3.25, prezzo 98.5 per 100 | valore 3.20125 |
| stessa Alfa su X/Y, target 50/50, valori 101.25/0 | pesi 100/0, gap +50/-50, Dinf 50, D2 5000 |
| cash EUR0.005 + USD10, contributo EUR5, USD/EUR0.9 | cash report 9.005, contributi 5, totale 14.005 |
| FX USD mancante | nativi visibili, totale report indisponibile |
| investito zero | totale 0 disponibile, pesi/score indisponibili |
| `"1e3"` | invalid syntax, mai 1000 |
| 13a cifra frazionaria non zero | unsupported, mai rounding |

## 10. Fuori P1

Full solver futuro mantiene:

- stessa riga asset x contesto;
- divieto globale buy+sell dello stesso `instrument_key`;
- nessuna vendita oltre inventario;
- nessun ciclo FX/arbitraggio;
- A: minimo scostamento peggiore, poi errore quadratico;
- B: stessa origine, score A preservato, sell congelati, buy solo crescenti,
  massimo capitale investito;
- no-op, infeasible provato e limit/timeout distinti;
- quantum monetario operativo positivo e generico, separato da precisione display.

Queste regole non autorizzano o descrivono un solver gia implementato.
