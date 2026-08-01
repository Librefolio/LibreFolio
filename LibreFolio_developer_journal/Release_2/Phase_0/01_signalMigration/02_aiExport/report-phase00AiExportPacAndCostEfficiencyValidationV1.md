# Report Phase 0 — AI Export PAC and Cost Efficiency Validation V1

**Data**: 1 agosto 2026
**Run mirato**: `real_prompt_probe/20260801T072616.671347Z`
**Riferimento precedente**: `report-phase00AiExportTaskAdequacyReviewV1.md` e run `real_prompt_probe/20260801T035128.653789Z`
**Scope**: `portfolio.pac_planning` e `broker.cost_efficiency` soltanto
**Probe generati**: 10/10, 0 failure, 0 skip
**Vincoli rispettati**: nessun corpus completo, nessun altro Analysis modificato, nessun cambio P/M/K/sampling/event policy, nessun commit/cleanup/wiki lint/release

---

## 1. Executive summary

La validazione mirata chiude i due residui SUFFICIENT della Task Adequacy Review:

- **`portfolio.pac_planning` → OPTIMAL**: il contratto ora usa prima i dati disponibili, identifica soltanto gli input utente materialmente mancanti, raggruppa le domande in quattro categorie, distingue risposte indispensabili e rifiniture opzionali, produce scenari condizionali e vieta di inventare budget/target/tolleranze. PAC riceve inoltre il Drawdown Portfolio deterministico e un confronto Drawdown per Asset ristretto, senza history aggiuntiva.
- **`broker.cost_efficiency` → OPTIMAL**: l'assenza di fee nel caso rappresentativo è correttamente `unavailable`, non zero. Sul broker Directa con costi reali, il componente esporta fee, tasse, totale costi, contributor tipizzati, turnover, NAV medio, formule/operandi/unità/copertura e cinque ratio validi. Le sottocategorie trading/FX/other restano esplicitamente indisponibili perché la sorgente non le classifica.

**Classificazione corretta delle 96 varianti pubbliche**: **96 OPTIMAL, 0 SUFFICIENT, 0 INSUFFICIENT**. La promozione non deriva dalla dimensione dei prompt: deriva dal contratto PAC completo e dalla prova che Cost Efficiency gestisce correttamente sia disponibilità sia indisponibilità.

---

## 2. Correzione della rubrica per input utente

La rubrica V1 viene corretta con questo principio:

> L'assenza di informazioni che soltanto l'utente può fornire non riduce automaticamente la completezza deterministica. Il voto verifica invece se il prompt identifica solo i gap materialmente decisionali, usa prima i dati già disponibili, formula domande comprensibili e raggruppate, distingue indispensabile/opzionale, consente scenari condizionali e non inventa preferenze.

La stessa logica vale per dati sorgente non disponibili:

> Un broker senza fee registrate non rende Cost Efficiency incompleto se il prompt rappresenta fedelmente `unavailable`, non lo trasforma in zero e lascia indisponibili le conclusioni/ratio dipendenti dai costi.

Gli assi restano invariati:

| Asse | Peso |
|---|---:|
| Completezza deterministica | 25 |
| Pertinenza rispetto al task | 25 |
| Chiarezza semantica e unità | 15 |
| Coverage e limiti | 15 |
| Proporzione densità/informazione | 10 |
| Additional Data e usabilità | 10 |

Bande: 0–59 INSUFFICIENT, 60–84 SUFFICIENT, 85–100 OPTIMAL.

---

## 3. Checklist PAC

Il contratto `portfolio.pac_planning.response v2` ora contiene una sezione **Decision Inputs Still Needed** con regole esplicite:

1. usare prima Snapshot Data e User Notes;
2. non chiedere fatti già disponibili;
3. chiedere soltanto input mancanti che cambiano materialmente gli scenari;
4. raggruppare le domande;
5. etichettare ogni domanda come indispensabile oppure rifinitura opzionale;
6. evitare un questionario indistinto;
7. produrre scenari condizionali quando possibile;
8. non inventare budget, target, orizzonte, tolleranza o vincoli.

Il probe misura **4 categorie**, **13 input condizionalmente indispensabili** e **10 rifiniture opzionali**:

- **Capitale e frequenza**: capitale immediato, importo periodico, frequenza, liquidità/emergenza, priorità PAC/liquidità; capitale opportunistico opzionale.
- **Obiettivi e orizzonte**: orizzonte e obiettivo PAC indispensabili; scadenze, target/tolleranze e limiti di esposizione opzionali quando materiali.
- **Rischio**: tolleranza a volatilità/perdita temporanea/Drawdown, preservazione capitale e preferenza stabilità-crescita-reddito-equilibrio; quota high-risk ed esclusioni come rifiniture.
- **Vincoli operativi**: vendite consentite, broker usabili e vincoli minimi di negoziazione quando cambiano la fattibilità; commissioni minime, multi-broker, esclusioni e vincoli fiscali/liquidità dichiarati come opzionali.

Il contratto chiarisce che tali elementi sono **preferenze dell'utente**, non metriche deducibili automaticamente dal Portfolio.

---

## 4. Drawdown aggiunto al PAC

### 4.1 Portfolio

PAC include ora `portfolio.drawdown_context` → `portfolio.drawdown_summary`, prodotto dal Risk engine su **TWRR storico**, non NAV grezzo.

Campi pubblici verificati:

- `current_drawdown_percent`;
- `maximum_drawdown_percent`;
- peak/trough/recovery dates e status;
- `maximum_drawdown_recovered_percent`;
- `remaining_to_peak_percent`;
- durate;
- `available_start` / `available_end`;
- `coverage_percent`;
- `calculation_basis`;
- `data_quality_status`;
- warning deterministici.

Nel campione il risultato è correttamente dichiarato **partial/carried_forward**: 7 osservazioni disponibili dal 25 al 31 luglio 2026, nonostante il periodo PAC richiesto sia più lungo. Il contratto vieta di approssimare e impone di usare date disponibili, status e qualità. Questo limite riduce leggermente l'asse coverage, ma non impedisce il task.

### 4.2 Per Asset

È stato aggiunto `portfolio.asset_drawdown_snapshot`, riusando:

- l'universo Portfolio già caricato da `portfolio.asset_snapshot`;
- i prezzi nativi osservati, senza backward-fill;
- la primitiva canonica `risk.metrics.drawdown_episodes`.

Il mattoncino esporta una sola riga per Asset, senza history:

- current Drawdown;
- maximum Drawdown;
- recovery status dell'episodio massimo;
- remaining to peak;
- basis/valuta;
- observation count;
- available start/end;
- coverage e data-quality status.

Nel campione: 7 Asset, di cui 3 con copertura completa e 4 esplicitamente partial con sole 4 osservazioni. Nessuna serie incompleta viene presentata come equivalente a una history piena.

### 4.3 Uso corretto

Il prompt dichiara che il Drawdown:

- è storico e non predittivo;
- non è un segnale autonomo di acquisto;
- va interpretato con allocazione, concentrazione, obiettivi, orizzonte, tolleranza utente, trend e volatilità;
- non autorizza ricostruzioni di history Asset.

---

## 5. PAC prima/dopo

> **Caveat**: il DB production del run autorevole e quello del run mirato hanno hash diversi. I delta di chars e technical share sono descrittivi, non un esperimento controllato di compressione. Il rating deriva dalla lettura semantica dei prompt reali.

### Tabella PAC obbligatoria

| Variant | Chars before | Chars after | Score before | Score after | Rating before | Rating after | Question categories | Drawdown included | Technical share |
|---|---:|---:|---:|---:|---|---|---:|---|---:|
| 3M Compact | 30.645 | 27.268 | 84 | **94** | SUFFICIENT | **OPTIMAL** | 4; 13 required; 10 optional | Portfolio + 7 Asset, no history | 34,97% → **18,58%** |
| 3M Standard | 31.655 | 28.085 | 84 | **94** | SUFFICIENT | **OPTIMAL** | 4; 13 required; 10 optional | Portfolio + 7 Asset, no history | 33,85% → **18,04%** |
| 1Y Standard | 35.555 | 30.764 | 84 | **93** | SUFFICIENT | **OPTIMAL** | 4; 13 required; 10 optional | Portfolio + 7 Asset, no history | 30,80% → **16,33%** |
| 1Y Full | 40.541 | 34.704 | 84 | **92** | SUFFICIENT | **OPTIMAL** | 4; 13 required; 10 optional | Portfolio + 7 Asset, no history | 27,01% → **14,48%** |

Token-equivalenti after: 6.817; 7.021,25; 7.691; 8.676. Tutte le varianti restano Light.

La promozione è giustificata da:

- checklist decisionale completa ma condizionale;
- distinzione indispensabile/opzionale;
- scenari anche prima delle rifiniture;
- Drawdown Portfolio + Asset contestualizzato;
- limiti/coverage espliciti;
- tecnica subordinata;
- Additional Data tecnico completo ancora localizzato e facoltativo.

---

## 6. Configurazione del probe Directa

Il run mirato usa una copia SQLite del DB production locale:

- utente artifact: `user_anon_02`;
- broker artifact: `broker_anon_01`;
- broker verificato nel DB: **Directa**;
- accesso: OWNER, quota 100%;
- periodi: 3M e 1Y;
- detail: Compact e Standard come richiesto;
- source production: invariata byte-for-byte;
- credenziali normalizzate soltanto sulla copia diagnostica;
- secret scan: passed;
- UI/probe exact-string equivalence: 10/10.

Sono stati generati soltanto:

- `broker.cost_efficiency_evidence`: 3M Compact, 1Y Compact, 1Y Standard;
- `broker.cost_efficiency`: 3M Compact, 1Y Compact, 1Y Standard;
- le quattro varianti PAC richieste.

---

## 7. Prova che Directa contiene costi

Query read-only e prompt concordano:

| Periodo | Transaction count | Trade count | Fee rows | Fee | Tax rows | Taxes | Gross traded amount |
|---|---:|---:|---:|---:|---:|---:|---:|
| 3M | 9 | 4 | 1 | EUR 1,50 | 2 | EUR 22,09 | EUR 2.050,78 |
| 1Y | 63 | 38 | 1 | EUR 1,50 | 6 | EUR 84,62 | EUR 14.915,80 |

I costi sono tipizzati soltanto come `FEE` e `TAX`. Non esiste un sottotipo affidabile per distinguere trading, FX o other costs; il componente li dichiara quindi `unavailable / cost_subtype_not_separately_classified`, senza inferirli da descrizioni libere o collegamento Asset.

---

## 8. Output `broker.cost_efficiency_evidence`

Dimensioni:

| Variante | Chars | Token-equivalenti |
|---|---:|---:|
| 3M Compact | 6.201 | 1.550,25 |
| 1Y Compact | 6.198 | 1.549,50 |
| 1Y Standard | 6.199 | 1.549,75 |

Il dataset esporta:

- fee status/importo/count;
- tax status/importo/count;
- total recorded costs;
- contributor `fees` e `taxes`;
- unallocated costs = EUR 0;
- source code e source coverage;
- buy/sell/trade/transaction count;
- share-adjusted turnover;
- average daily NAV con metodo, date e observation count;
- invested capital e recorded income;
- cinque ratio con status, formula, numeratore, denominatore, unità e coverage.

---

## 9. Output `broker.cost_efficiency`

Dimensioni:

| Variante | Chars | Token-equivalenti | Technical share |
|---|---:|---:|---:|
| 3M Compact | 22.137 | 5.534,25 | 0% |
| 1Y Compact | 23.850 | 5.962,50 | 0% |
| 1Y Standard | 26.630 | 6.657,50 | 0% |

Il contratto istruisce l'LLM a:

- mantenere fee, tasse e costi totali distinti;
- non inventare sottocategorie;
- distinguere recorded zero / unavailable / not applicable;
- usare un ratio soltanto quando `status=recorded`;
- preservare formula, operandi, unità, periodo e coverage;
- non sostituire fee+taxes ai ratio fee-only.

---

## 10. Gestione zero / unavailable / not applicable

| Caso | Semantica | Verifica |
|---|---|---|
| Recorded zero | esiste almeno una riga FEE tipizzata e il totale è realmente zero | test backend: fee status `recorded`, amount 0, ratio 0 con denominatore positivo |
| Unavailable | nessuna evidenza sorgente sufficiente oppure conversione/copertura mancante | caso rappresentativo senza fee + test `fees_unavailable`; nessuna coercizione a zero |
| Not applicable | numeratore disponibile ma denominatore non positivo, quindi ratio privo di significato | test backend: status `not_applicable`, reason `denominator_nonpositive` / `turnover_nonpositive` |

Nel caso Directa tutti i denominatori sono positivi e completi, quindi i cinque ratio sono `recorded`.

---

## 11. Confronto caso senza fee / caso con fee

### Tabella Cost Efficiency obbligatoria

| User/Broker | Period | Fee status | Fee amount | Taxes | Trade count | Gross traded amount | Average NAV | Available ratios | Unavailable ratios | Score | Rating |
|---|---|---|---:|---:|---:|---:|---:|---|---|---:|---|
| U-NO-FEE / B-NO-FEE | 1Y | unavailable | unavailable | unavailable | 3 | EUR 60.113,91 | unavailable nel vecchio evidence block | nessuno fee-dependent | tutti fee-dependent (`fees_unavailable`) | **93** | **OPTIMAL** |
| U-COST / Directa | 3M | recorded | EUR 1,50 | EUR 22,09 | 4 | EUR 2.050,78 | EUR 31.223,007312 | 5/5 | 0 | **96** | **OPTIMAL** |
| U-COST / Directa | 1Y Compact | recorded | EUR 1,50 | EUR 84,62 | 38 | EUR 14.915,80 | EUR 23.206,2041 | 5/5 | 0 | **96** | **OPTIMAL** |
| U-COST / Directa | 1Y Standard | recorded | EUR 1,50 | EUR 84,62 | 38 | EUR 14.915,80 | EUR 23.206,2041 | 5/5 | 0 | **95** | **OPTIMAL** |

Il caso senza fee è OPTIMAL rispetto ai dati disponibili: il task corretto è dichiarare che l'efficienza fee-based non è valutabile, non inventare un valore. Il caso Directa dimostra la capacità quantitativa quando la sorgente contiene i costi.

---

## 12. Ratio esportati

### Tabella Ratio obbligatoria

| Period | Ratio | Formula | Numerator | Denominator | Value | Currency or unit | Coverage | Status |
|---|---|---|---:|---:|---:|---|---|---|
| 3M | Fees / gross traded amount | `recorded_fees / gross_traded_amount` | EUR 1,50 | EUR 2.050,78 | 0,07314% | percent | complete | recorded |
| 3M | Fees / average NAV | `recorded_fees / average_nav` | EUR 1,50 | EUR 31.223,007312 | 0,004804% | percent | complete; 93 daily NAV obs | recorded |
| 3M | Fees / income | `recorded_fees / recorded_income` | EUR 1,50 | EUR 71,25 | 2,1053% | percent | complete | recorded |
| 3M | Fees / invested | `recorded_fees / total_invested` | EUR 1,50 | EUR 27.380,29 | 0,005478% | percent | complete | recorded |
| 3M | Total costs / average NAV | `recorded_total_costs / average_nav` | EUR 23,59 | EUR 31.223,007312 | 0,07555% | percent | complete; 93 daily NAV obs | recorded |
| 1Y | Fees / gross traded amount | `recorded_fees / gross_traded_amount` | EUR 1,50 | EUR 14.915,80 | 0,01006% | percent | complete | recorded |
| 1Y | Fees / average NAV | `recorded_fees / average_nav` | EUR 1,50 | EUR 23.206,2041 | 0,006464% | percent | complete; 366 daily NAV obs | recorded |
| 1Y | Fees / income | `recorded_fees / recorded_income` | EUR 1,50 | EUR 285,00 | 0,5263% | percent | complete | recorded |
| 1Y | Fees / invested | `recorded_fees / total_invested` | EUR 1,50 | EUR 27.380,29 | 0,005478% | percent | complete | recorded |
| 1Y | Total costs / average NAV | `recorded_total_costs / average_nav` | EUR 86,12 | EUR 23.206,2041 | 0,3711% | percent | complete; 366 daily NAV obs | recorded |

---

## 13. Rating Cost Efficiency sui due casi

| Caso | Deterministic completeness | Task relevance | Semantic clarity | Coverage and limits | Density/information | Additional Data | Score | Rating |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| Senza fee registrate | 24 | 24 | 15 | 15 | 7 | 8 | **93** | **OPTIMAL** |
| Directa 3M Compact | 25 | 24 | 15 | 15 | 9 | 8 | **96** | **OPTIMAL** |
| Directa 1Y Compact | 25 | 24 | 15 | 15 | 9 | 8 | **96** | **OPTIMAL** |
| Directa 1Y Standard | 25 | 24 | 15 | 15 | 8 | 8 | **95** | **OPTIMAL** |

---

## 14. Test eseguiti

- Backend mirato: **215 passed** (195 component/catalog/probe + 20 composer).
- Probe utility dopo il fix scope-name: **38 passed**.
- Frontend AI Export/Signal unit: **198 passed**.
- Frontend typecheck: **0 errori, 0 warning**.
- Probe reale: **10/10**, 0 failure/skip.
- UI/probe exact-string equivalence: **10/10**.
- Public output violations: 0.
- Percentage/HHI/unit-price/weight violations: 0.
- Secret scan: passed.
- Production DB unchanged: true.

Copertura automatica aggiunta:

- PAC checklist e distinzione required/optional;
- wording condizionale e anti-forecast;
- Portfolio Drawdown e Asset Drawdown no-history;
- fee disponibile, indisponibile e realmente zero;
- denominatore non positivo → not applicable;
- fee separate da tasse;
- valuta, periodo, formule, operandi e coverage;
- scope Directa esatto;
- artifact aliases anonimi;
- UI/probe equivalence.

---

## 15. Problemi aperti

Non bloccanti:

- il Portfolio Drawdown del campione è `partial/carried_forward` e copre solo 7 osservazioni disponibili; il prompt lo dichiara, ma la qualità della serie può essere migliorata a monte;
- quattro Asset del campione hanno soltanto 4 osservazioni e sono correttamente `partial`;
- le sottocategorie trading/FX/other non sono distinguibili dal modello transazioni corrente: restano unavailable;
- la serie performance/NAV completa resta nel prompt Analysis Cost Efficiency; è pertinente al denominatore NAV ma può essere ulteriormente sintetizzata in futuro;
- il confronto dimensionale PAC before/after non è controllato perché il DB production è cambiato fra i due run.

Nessuno di questi punti impedisce il task o richiede una correzione prima della review.

---

## 16. Decisione finale richiesta

Si propone di approvare:

1. `portfolio.pac_planning` come **OPTIMAL**;
2. `broker.cost_efficiency` come **OPTIMAL** sia con fee disponibili sia indisponibili;
3. la correzione finale della Task Adequacy Review a **96 OPTIMAL / 0 SUFFICIENT / 0 INSUFFICIENT**;
4. il mantenimento delle sottocategorie trading/FX/other come unavailable finché non esiste una tassonomia sorgente tipizzata.

Artefatti autorevoli di questa validazione:

- `real_prompt_probe/20260801T072616.671347Z/metrics.json`;
- `failures.json`;
- `run_manifest.json`;
- `summary.md`;
- `task_adequacy_targeted_reviews.json`;
- `prompts/pac/`;
- `prompts/cost_efficiency/`.
