# C — piano di esecuzione

| | |
|---|---|
| Mandato | [`../C-backend-affettamento-portafoglio.md`](../C-backend-affettamento-portafoglio.md) — sola lettura |
| Branch | `e-alfy-risk-c-portfolio-slicing` ⚠️ rinominato dal runtime (era `e-alfy-crispy-journey`) |
| Baseline | `cc33120ebfbc61efe4c6178218ff8d64dd4adf47` ✅ verificata |
| Lane | porta `6242` · data dir `backend/data/test-risk-c` |
| Autorizzazione | coordinatore, sotto delega permanente del developer |
| Contratto in uscita | **K4** → E |

---

## Le decisioni che governano questo piano

| # | Decisione | Fonte |
|---|---|---|
| **D57** | Il plugin riceve la lista **già risolta**, non il filtro | `04` |
| **D58** | Il filtro va su `PortfolioRiskScope`, lo scope resta `portfolio` | `04` |
| **D59** | Affettando, i pesi si **rinormalizzano** al 100% della fetta | `04` |
| **Q-C1 → (a)** | In `HISTORICAL` con filtro attivo si prende il **ramo pesato** già esistente (`service.py:608`), non il TWRR | coordinatore |
| **F4** | Con i pesi si riducono anche `scope_value` e `asset_values` | analisi C |
| **F5** | Scelta dell'utente → rinormalizza · dato indisponibile → residuo a rendimento zero (G6) | analisi C + devWiki |
| **F7** | Il campo si chiama esattamente `asset_ids` | analisi C |

### I due obblighi di dichiarazione verso la UI (K4)

1. **I pesi sono rinormalizzati**: la stessa percentuale significa due cose diverse a
   seconda di cosa la genera.
2. **In `HISTORICAL` la fetta cambia significato**: non più TWRR (*com'è andata
   davvero*) ma composizione pesata sui pesi correnti (*come sarebbe andata la
   composizione di oggi*). È un backtest, non un resoconto.

---

## Passi

- [x] 0. Baseline della lane — `services risk-all` prima di toccare alcunché — ✅ 18 Set 2026
  > **Note implementazione**: `134 passed in 31.07s`. Lane `6242` operativa, venv condiviso
  > `LibreFolio-SAUMUTtc` presente, `.env` e `node_modules` assenti come previsto dal kickoff.
  > **Fuori pista**: il baseline era stato tentato durante l'analisi ma la plan mode lo ha
  > bloccato (scrive su disco). Eseguito come primo comando dopo l'autorizzazione.

- [x] 1. Piano vivo aperto — ✅ 18 Set 2026

- [x] 2. Campo `asset_ids` su `PortfolioRiskScope` — ✅ 18 Set 2026
  > **Note implementazione**: `schemas/risk.py:555-583`. Campo opzionale, `1..100`,
  > `PositiveInt`, con validatore `normalize_asset_ids` gemello di quello dei broker
  > (unicità + ordinamento). Il validatore di `broker_ids` è rimasto **intatto**: non ho
  > fuso i due in un unico decoratore per non cambiare messaggi d'errore esistenti.
  > **Fuori pista**: nessuna classe nuova ⇒ **`__all__` non è stato toccato**, come previsto
  > da F3. Conflitto di C su `schemas/risk.py`: zero.

- [x] 3. Risoluzione nel servizio — intersezione con `summary.holdings` — ✅ 18 Set 2026
  > **Note implementazione**: `service.py:361-380`. La fetta si risolve **intersecando** il
  > filtro con gli holding del report, che sono già ristretti ai broker accessibili: nessuna
  > interrogazione diretta su `Asset`, quindi nessun oracolo di esistenza su asset altrui.
  > Intersezione vuota → `RiskScopeNotFoundError` esplicito (404). Asset richiesti ma non
  > posseduti → warning `slice_assets_not_held` con la lista, e si prosegue (Q-C5).
  > **Fuori pista**: trovato un `KeyError` latente. Il ciclo che accumula `asset_values`
  > iterava su **tutti** gli holding indicizzando un dict inizializzato sui soli
  > `requested_asset_ids`: identici prima della fetta, non più dopo. Aggiunta la guardia
  > `if holding.asset_id in asset_values`. Sarebbe esploso al primo uso reale del filtro.

- [x] 4. Rinormalizzazione: pesi, `scope_value`, `asset_values` — ✅ 18 Set 2026
  > **Note implementazione**: `service.py:383-410`. Con fetta attiva il denominatore diventa
  > la **somma della fetta**, non il patrimonio netto: i pesi sommano a 1, `cash_weight` è 0,
  > e `scope_value`/`asset_values` restano coerenti con quei pesi — senza questo
  > `stress.py:419,564` avrebbe gonfiato l'impatto in € del rapporto NAV/fetta (F4).
  > Messaggio d'errore distinto per fetta a valore nullo («positive slice value»), perché
  > «positive scope NAV» su una fetta è fuorviante.
  > **Fuori pista**: il warning `zero_risk_residual_includes_in_transit` sarebbe partito
  > **a sproposito** su ogni fetta (confronta `cash_weight`, ora 0, con `cash_total/valore
  > della fetta`, non nullo). Soppresso quando la fetta è attiva: una fetta non ha residuo a
  > rendimento zero, quindi quel warning non la descrive. La convenzione **G6** — asset
  > inutilizzabile ⇒ residuo a rendimento zero — resta intatta e ora convive dichiarata
  > accanto a D59 (F5), con commento nel codice.

- [x] 5. Identità: `_scope_reference` — ✅ 18 Set 2026
  > **Note implementazione**: `service.py:906-921`. Ora emette
  > `portfolio:<broker>/assets:<id,…>` sulla fetta **effettiva**, coerente con la convenzione
  > già in uso per i broker (si riferisce a ciò che è stato calcolato, non a ciò che è stato
  > chiesto). Due fette diverse non collidono più.

- [x] 6. `HISTORICAL` con fetta → ramo pesato (Q-C1) — ✅ 18 Set 2026
  > **Note implementazione**: `service.py:619-623`. Aggiunta la sola condizione
  > `and not scope_inputs.slice_asset_ids` al ramo TWRR: con la fetta la richiesta cade nel
  > ramo pesato **che esisteva già**. Zero codice di calcolo nuovo, come indicato dal
  > coordinatore. `primary_return_basis` resta `PRICE_ONLY` invece di `TWRR`: la differenza
  > di significato è così leggibile dal contratto, senza nuovi valori d'enum.

- [x] 7. Dichiarazione nei metadati — ✅ 18 Set 2026
  > **Note implementazione**: `RiskResultMetadata.sliced_asset_ids` (`schemas/risk.py:457-460`),
  > validatore di unicità e invariante «richiede scope portfolio», gemelli di `broker_ids`.
  > Propagato via `RiskExecutionContext.sliced_asset_ids` (`base.py:105`, campo additivo con
  > default: **nessun plugin toccato**) e `_metadata` (`service.py:831`).
  > I **due** obblighi di dichiarazione della UI sono così entrambi serviti da campi esistenti
  > o da questo solo campo nuovo: `sliced_asset_ids` non nullo ⇒ pesi rinormalizzati;
  > `return_basis` ⇒ resoconto (TWRR) o backtest della composizione di oggi (`price_only`).

- [x] 8. `api sync` — ⚠️ **eseguito a metà** — 18 Set 2026
  > **Note implementazione**: `dev.py api schema` ✅ — `openapi.json` e `tool-contracts`
  > rigenerati, e verificato sul contratto esportato che `PortfolioRiskScope` espone
  > `['kind','broker_ids','asset_ids']` e che `RiskResultMetadata` espone `sliced_asset_ids`.
  > **Fuori pista**: `api sync` è `api schema` + `npm run generate-api`
  > (`dev.py:635-650`). La seconda metà richiede `frontend/node_modules`, **assente** in questo
  > worktree backend, e le regole vietano `npm install`. Riportato al coordinatore. Nessun
  > danno al checkpoint: `openapi.json`, `generated.ts` e `tool-contracts.openapi.json` sono
  > **tutti e tre gitignorati**, quindi non entrano comunque nel commit e i mandati a valle li
  > rigenerano.

- [x] 9. `git diff` vuoto su `backend/app/services/risk_plugins/` — 2026-09-18
  > **Nota implementazione**: `git diff --stat backend/app/services/risk_plugins/` non produce
  > alcuna riga. Nove plugin, zero modifiche: è il collaudo di **D57**. Il filtro vive sullo
  > scope, lo scope resta `portfolio`, e la propagazione è trasparente. Superficie totale del
  > mandato: **tre** file di produzione (`schemas/risk.py`, `risk/service.py`, `risk/base.py`).

- [x] 10. Test — compreso il **duale** di F2 — 2026-09-18
  > **Nota implementazione**: scritti da `test-author` nella lane 6242. **12 nuovi** in
  > `test_risk_service.py`, **2** appesi in coda a `test_risk_schemas.py` (file condiviso:
  > solo aggiunte, nessun riordino). `test_risk_api.py` **non toccato** (vedi *Fuori pista 3*).
  > Il duale di F2 è coperto due volte, in `current_composition` e in `historical`: una fetta
  > propria **deve** dare un numero diverso dal portafoglio intero. È l'unico test che
  > accorgerebbe del difetto F1 se qualcuno lo reintroducesse.
  > Coperti anche: rinormalizzazione (Σ pesi = 1, `cash_weight` = 0, `scope_value` = valore
  > della fetta), non-regressione del caso non affettato, ramo pesato in `historical` con
  > `return_basis` `price_only`, residuo a rendimento zero per asset senza storia **dentro**
  > la fetta (G6 intatto accanto a D59 — le due convenzioni opposte ora sono asserite fianco
  > a fianco), assenza di oracolo di esistenza (`ForbiddenDb` fa fallire qualsiasi query su
  > `Asset`), identità di `scope_reference`, avviso `slice_assets_not_held`, intersezione
  > vuota → `RiskScopeNotFoundError`, e metadato `sliced_asset_ids`.

- [x] 11. Gate + consegna di **K4** — 2026-09-18
  > **Nota implementazione**: `lint` ✅, `schemas risk` ✅ `16 passed`, `services risk-all` ✅
  > `146 passed in 28.37s` (134 di baseline + 12). Porta 6242 libera a fine lavoro.
  > **K4 consegnato** al coordinatore per E.
  > Prima dei gate ho corretto un'asimmetria che `test-author` ha segnalato nel mio stesso
  > codice: in `_metadata`, `sliced_asset_ids` era l'unica riga del blocco priva della guardia
  > `scope_kind == PORTFOLIO` che hanno `broker_ids` e `composition_as_of`. Oggi irraggiungibile,
  > ma sarebbe emersa come 500 dalla validazione del metadato invece che come `None` pulito.

---

## Evidenza

| Comando | Esito |
|---|---|
| `… dev.py test --test-port 6242 --data-dir backend/data/test-risk-c services risk-all` (baseline) | ✅ `134 passed in 31.07s` |
| `… dev.py lint` | ✅ `All checks passed!` |
| `… dev.py test … schemas risk` | ✅ passed |
| `… dev.py test … services risk-all` (dopo i passi 2-7) | ✅ `134 passed in 27.65s` |
| `… dev.py api schema` | ✅ contratto esportato e verificato |
| `… dev.py api client` | ⛔ non eseguito: manca `frontend/node_modules` |
| `… dev.py test … schemas risk` (finale) | ✅ `16 passed in 0.17s` (14 + 2 nuovi) |
| `… dev.py test … services risk-all` (finale) | ✅ `146 passed in 28.37s` (134 + 12 nuovi) |
| `… dev.py lint` (finale) | ✅ `All checks passed!` |
| `… dev.py test … api risk` | ⛔ **infrastruttura**: il backend condiviso non parte |
| `git diff --stat backend/app/services/risk_plugins/` | ✅ **vuoto** |
| `git diff --check` | ✅ nessun errore di spazio |
| `lsof -nP -iTCP:6242 -sTCP:LISTEN` | ✅ nessun listener |
| `…test … db populate --force --clean` | ✅ (sulla **mia** data dir) |
| `…test … api risk` (dopo popolamento) | ✅ **`10 passed in 13.81s`** |
| `…test … services risk-all` (su DB popolato) | ✅ `146 passed in 27.00s` |

---

## Riapertura 2026-09-18 — terzo membro di `RiskReturnBasis`

Riaperto dal coordinatore su scoperta di **E**: `price_only` e `twrr` non bastano a dichiarare
un backtest a composizione pesata, e il frontend potrebbe solo **inferirlo** dalla presenza della
fetta — una congettura del client che sembra un fatto riportato.

### ⚠️ Presupposto del brief di riapertura: FALSO

> *«oggi una corsa `HISTORICAL` affettata riporta `TWRR`, che è falso»*

**Non è vero, e l'avevo già implementato e testato.** Verificato su tutti e nove i plugin:
nessuno scrive `TWRR` a mano — propagano `context.primary_return_basis`, che la mia guardia
lascia a `price_only`. Il metadato **non mentiva: era ambiguo.** `price_only` è lo stesso valore
che riportano una corsa ad asset singolo e una a composizione corrente, quindi E non poteva
distinguere «rendimenti di prezzo» da «backtest a pesi correnti».
Il bisogno di E era **reale**; la diagnosi no. La cura richiesta resta la stessa.

### Implementato

- `RiskReturnBasis.CURRENT_COMPOSITION_BACKTEST = "current_composition_backtest"`
  (`schemas/risk.py:43`). Nome scelto sulla **serie consumata**, non sullo scope, come richiesto.
- Impostato nel ramo pesato di `_build_context`, **dentro** `if rows and composition_error is None`:
  la base dichiara un backtest solo se la serie è stata davvero prodotta.
- `__all__` **ancora intatto**: è un membro di un enum già esportato, non un simbolo nuovo.

### Le due verifiche richieste: entrambe con esito positivo, una più grave del previsto

1. **Consumatori esaustivi — SÌ, due, nessuno dei quali è un `match`:**
   - 🔴 `frontend/src/lib/api/generated.ts:11361` — `z.enum(['price_only','twrr'])` **valida a
     runtime**: un terzo valore dal backend faceva **fallire la risposta nel client** finché non
     si rigenerava. `node_modules` ora esiste ⇒ ho eseguito `api sync`: l'enum è a tre valori e
     `PortfolioRiskScope.asset_ids` è nel contratto Zod con la descrizione di D59.
   - 🟠 `RiskResultFrame.svelte:108` — `$t(\`risk.returnBasis.${metadata.return_basis}\`)`, chiave
     i18n **dinamica**. Il blocco `returnBasis` in `en/it/fr/es.json:2973` ha esattamente due
     chiavi ⇒ senza traduzione lo schermo mostra la chiave grezza. **Quattro lingue, a carico di E.**
2. **AI Export — SÌ, lo legge**: `drawdown_context.py:264` (`output.return_basis.value`), campo
   `return_basis: str | None` **libero**, quindi nessuna rottura di validazione; ma è
   **obbligatorio in stato SUCCESS** e il valore nuovo entra nel payload fattuale esportato.
   Arriva lì attraverso `drawdown_summary.py`, che è **di A**.

### Raggio d'impatto, misurato non stimato

Prima esecuzione dopo la modifica: **2 failed, 144 passed** — e i due rossi erano **i miei**
test che fissavano il valore vecchio. **Nessun altro mandato disturbato.**

> **Fuori pista 5** — avevo poi aggiunto un'asserzione sbagliata: pretendevo la base nuova anche
> sul risultato di `risk_contribution`. Rosso istruttivo: quel plugin **non consuma la serie
> composita** — legge la base dalla serie **per-asset** (`:89`), dove `price_only` è onesto.
> Corretto il test, non il codice. Il valore nuovo è visibile solo ai risultati che consumano
> davvero la serie pesata (`comparison`, `drawdown_summary`, `historical_kpi`, `historical_var`)
> — cioè esattamente dove serve a E.

### Segnalazioni ad A, non corrette da me

`historical_kpi.py:109` e `drawdown_summary.py:54` derivano ancora le stringhe
`historical_close_returns` / `price_only_close` da `== TWRR`. Con la base nuova cadono nel ramo
`else` e restano verdi, ma **quelle etichette ora descrivono male** un backtest a pesi correnti.
Sono file di **A**: segnalato, non toccato.

### Cancelli dopo la riapertura

| comando | esito |
|---|---|
| `…schemas risk` | ✅ `16 passed in 0.15s` |
| `…services risk-all` | ✅ `146 passed in 31.15s` |
| `db populate --force --clean` → `…api risk` | ✅ `10 passed in 13.66s` |
| `dev.py lint` | ✅ `All checks passed!` |
| `dev.py api sync` | ✅ **completo** (schema + client Zod + tool contracts) |
| `git diff --stat …/risk_plugins/` | ✅ **vuoto** |
| `lsof -nP -iTCP:6242 -sTCP:LISTEN` | ✅ libera |

---

## Contratti

| # | Verso | Stato |
|---|---|---|
| K4 | E | ✅ consegnato al coordinatore |

**K4 — errata corrige 2026-09-18.** Alla consegna K4 portava **due** obblighi di dichiarazione
(rinormalizzazione dei pesi D59; base dei rendimenti `price_only` = backtest, non resoconto).
Ne resta un **terzo**, che nasce fuori dal mio mandato ma atterra sulla mia schermata:

3. Finché **A9** non è fuso, Sharpe e Sortino **di ogni fetta** sono lusingati quando il tasso
   privo di rischio è non nullo (`f ≈ 252` usato come `365`): +0,038 a `rf = 2 %`, +0,094 a
   `rf = 5 %`. **Non** «solo le fette con mercati misti» — quella era una mia caratterizzazione
   errata, corretta il 2026-09-18. A `rf = 0 %` lo scarto è esattamente nullo.
   Il totale (ramo TWRR non affettato) **non** è distorto: `c = 1,0` esatto.
   ⇒ Il confronto *fetta contro totale* in L3 accosta un numero distorto a uno esatto.
   **A9 è prerequisito di L3**, non pulizia indipendente.
4. **`coverage` non è un indice di qualità da mostrare accanto a questi numeri**: vale ≈ 1,000
   proprio quando `f` è massimamente sbagliato. Presentarlo come «qualità dei dati» rassicura
   l'utente esattamente quando dovrebbe metterlo in guardia.
   **La cura (coordinatore, D102)**: il campo che sa la verità è **`annualization_factor`**,
   già nel payload — `252` contro `365` è il campanello diretto, senza inferenze.
   Tre precisazioni mie, verificate sul codice:
   - posizioni in **questo** worktree: `annualization_factor` a `:450`, `coverage` a `:451`
     (il coordinatore citava `:449`/`:450`: scarto di una riga, come già accaduto con H — vale
     il **vicino di riga**, non il numero);
   - il campo è **`Optional`** (`Field(None, gt=0)`): è `None` **se e solo se**
     `n_observations == 0` (`observed_annualization`, `:71-72`), caso in cui anche
     `calendar_days == 0` (`schemas/risk.py:512`). Quindi il ramo nullo per E non è ambiguo:
     *nessuna osservazione, niente da mostrare*;
   - **la cura è più forte di come è stata formulata**: `schemas/risk.py:518` **valida già
     l'invariante** `annualization_factor == n_observations * 365 / calendar_days`. E non legge
     un indizio, legge una grandezza **garantita dal contratto** — quindi il confronto con `365`
     è affidabile per costruzione, non per convenzione.

**K4 — emendamento 2026-09-18 (riapertura enum).** La dichiarazione n. 2 cambia portatore:

2-bis. Non più *«`price_only` significa backtest»* — che era **ambiguo**, perché `price_only`
   è anche la base di un asset singolo. Ora esiste un valore dedicato:
   **`return_basis == "current_composition_backtest"`** ⇒ *pesi di oggi riproiettati
   all'indietro sui rendimenti passati*: **un backtest, non un resoconto**.
   E lo legge come **fatto riportato dal server**, senza inferirlo dalla presenza della fetta.
   Compare sui risultati che consumano la serie pesata (`comparison`, `drawdown_summary`,
   `historical_kpi`, `historical_var`); `risk_contribution` e `correlation` continuano a
   riportare la base **per-asset**, che per loro è quella giusta.
   **Due adempimenti a carico di E**:
   - rigenerare `generated.ts` — l'enum Zod **valida a runtime**: con due soli valori la
     risposta del backend **fallisce nel client** (già rigenerato in questo worktree, ma è
     un file gitignorato);
   - aggiungere `risk.returnBasis.current_composition_backtest` in **en/it/fr/es** (`:2973`),
     altrimenti `RiskResultFrame.svelte:108` mostra la chiave grezza.

---

## Fuori pista

**0. Rischio residuo CHIUSO (2026-09-18).** A ha verificato sul `git diff` di `metrics.py` che
`current_buy_and_hold_returns(returns_by_asset, weights, *, cash_weight)` ha **firma invariata**
e semantica confermata: **residuo a rendimento zero, non rinormalizzato internamente**. La
rinormalizzazione a monte di C **non è doppia**. Era l'unico rischio non chiuso alla consegna.

**0-bis. ⚠️ Interazione fra il difetto del tasso privo di rischio (A) e l'affettamento (C).**
A ha trovato `365.0` cablato in `metrics.py:144` con `f = 365 × coverage` algebricamente:
errore nullo su dati sani, si attiva quando la copertura peggiora, e **lusinga sempre lo Sharpe**.
Verificato sul mio codice che la cosa mi tocca più di quanto sembri — e non per il motivo ovvio:

> Fetta e portafoglio intero non prendono `coverage` da due **valori** diversi, ma da due
> **sorgenti** diverse. In HISTORICAL non affettato il ramo TWRR **sovrascrive** `coverage`
> con quella del report di portafoglio (`service.py:625-632`). Affettato, `coverage` resta
> `prepared.calendar_coverage`, cioè il calendario congiunto **della sola fetta**.

Conseguenza: in L3 il confronto *fetta contro totale* — la domanda d'utente per cui esiste
questo mandato — accosta due numeri la cui distorsione da tasso privo di rischio nasce da due
provenienze diverse. **Parte della differenza visibile potrebbe essere un artefatto del difetto,
non del portafoglio.**

**Aggiornamento 2026-09-18 — le due formule, lette.** La mia prima attesa («la fetta appare
peggiore») e la controproposta del coordinatore («la fetta appare migliore») **sono entrambe
troppo semplici**. Le due `coverage` non misurano la stessa grandezza:

| ramo | formula | cosa misura |
|---|---|---|
| non affettato | `min(1, len(returns)/calendar_days)` (`service.py:881-901`) | completezza **di calendario** |
| affettato | `n_observations / len(coverage_candidates)` (`series_preparation.py:344-345`) | completezza **sulle date di quotazione candidate** |

Sul ramo non affettato, se `report.history` è una griglia giornaliera (scoperta di I) **e** ogni
punto ha `twrr` non nullo — il codice filtra `points = [p for p in history if p.twrr is not None]` —
allora `len(returns) = calendar_days` e viene **esattamente `1,0`**, con `f = 365` esatto: il `365`
cablato è giusto lì, distorsione nulla. **Riserva mia, da girare ad A**: un buco di `twrr` in un
solo giorno rompe l'uguaglianza e riporta la distorsione **anche sul ramo non affettato**.

Sul ramo affettato il denominatore **non** è «giorni di calendario»: sono le date candidate di
quotazione.

**Correzione 2026-09-18 (coordinatore + A), verificata da me sul codice — la mia conclusione qui
sopra era SBAGLIATA.** Ragionavo su `coverage`, ma la distorsione **non è governata da `coverage`**:
è governata da `f`, e sul ramo preparato le due hanno **denominatori diversi che non convergono mai**.

| grandezza | formula | denominatore |
|---|---|---|
| `coverage` | `n_observations / len(coverage_candidates)` — `series_preparation.py:345` | date di quotazione **fresche** (`_price_is_fresh`, `:122-124`: scarta i riporti all'indietro) |
| `f` | `n_observations * 365 / calendar_days` — `observed_annualization`, `:78` | **span di calendario** |

Per un portafoglio azionario: candidati ≈ 252/anno ⇒ `coverage ≈ 1,000`; `D = 365` ⇒ `f ≈ 252`.

> ⚠️ **Il campo che il sistema espone come indice di qualità segna il massimo esattamente mentre
> il difetto è al massimo.** `coverage` è in `RiskResultMetadata` (`schemas/risk.py:451`), quindi
> è renderizzabile: mostrarlo come «qualità» accanto a uno Sharpe distorto **rassicura l'utente
> proprio quando il numero è più sbagliato**.

Quindi sul ramo affettato la distorsione è **strutturale, non condizionata alla composizione**.
Il disallineamento dei calendari la peggiora (meno date comuni ⇒ N minore ⇒ f minore), ma il caso
base è **già** distorto. Misure di A con le funzioni vere, `f = 252`: a `rf = 0 %` scarto
**esattamente nullo** (ecco perché nessuno l'aveva visto), a `rf = 2 %` Sharpe **+0,038**, a
`rf = 5 %` Sharpe **+0,094** e Sortino **+0,130**, stabile su 1/2/3 anni.

**Ricaduta su K4**: la dichiarazione a schermo non riguarda «le fette con mercati misti» ma
**ogni fetta con tasso privo di rischio non nullo**. Vedi la riga K4 aggiornata.

**La mia riserva su `twrr is not None` è stata sciolta** dal coordinatore, a favore di A: i `None`
sono un **suffisso contiguo** (`lots_analysis_service.py:1013`) e il filtro `:1007` taglia un
**prefisso contiguo**; `calculate_twrr_series` emette un punto per snapshot NAV e gli snapshot
*sono* la griglia ⇒ **nessun buco interno possibile** ⇒ contiguità salva ⇒ `c = 1,0` e `f = 365`
esatti sul ramo non affettato (delta misurato `1,4e-16`). **Il totale non è mai distorto.**
Non modifico nulla: `metrics.py` è di A. Ma la sua correzione è un **prerequisito** perché L3
fetta-contro-totale sia attendibile, non una pulizia indipendente.

**0-ter. Secondo scrittore su `RiskResultMetadata`.** H aggiunge `bootstrap_seed` alla stessa
classe. Posizioni esatte di C in questo worktree, per la previsione di fusione:
campo `sliced_asset_ids` a **`:456-459`** (fra `broker_ids` e `composition_as_of`), validatore
`normalize_sliced_asset_ids` a **`:498-503`**. Entrambi additivi, nessun riordino, nessuna
riformattazione. Fonde pulito se H inserisce fra i parametri di simulazione (`:471-474`) o più
in basso; l'unico attrito sarebbe un inserimento subito dopo `broker_ids`. Non posso verificarlo:
leggere il worktree di H è vietato. Segnalato al coordinatore.

**1. `_load_scope_inputs` aveva un `KeyError` latente.** `asset_values` veniva inizializzato
dagli asset richiesti ma il ciclo di accumulo iterava **tutte** le posizioni. Identico prima
dell'affettamento, divergente dopo: sarebbe esploso al primo uso reale del filtro. Protetto
con `if holding.asset_id in asset_values`. Non era nel brief.

**2. Avviso spurio `zero_risk_residual_includes_in_transit`.** Confronta `cash_weight` (0 su una
fetta) con `cash_total/scope_value` (non nullo): sarebbe scattato su ogni fetta con valore in
transito. Soppresso quando si affetta — una fetta non ha residuo a rendimento zero da descrivere.

**3. ⛔ Il gate `api` non è eseguibile in nessun worktree coordinato.** Non è un rosso di
prodotto: il backend di test esce con codice 1 **prima** di pytest. La catena è
`dev.py server --test` → build del frontend → `update_js_cache` → download di `mathjax` da
`cdn.jsdelivr.net` → `SSL: CERTIFICATE_VERIFY_FAILED`. La cartella di destinazione
(`mkdocs_src/docs/javascripts/vendor/`) è gitignorata (`.gitignore:78`), quindi in un worktree
fresco il file non c'è e va scaricato. Si somma a `frontend/node_modules` assente. Due lacune
di bootstrap indipendenti, entrambe fuori dal mio mandato e dalle mie regole (`npm install` e
`pipenv install` vietati). Riportato al coordinatore come limite di campagna: la definizione
comune di finito (§6) chiede un gate che **nessun** mandato può soddisfare così com'è.

**3. ⛔→✅ Il gate `api` era bloccato dal bootstrap, poi riaperto dal coordinatore.** Diagnosi
originale: il backend di test usciva con codice 1 **prima** di pytest, perché `dev.py server --test`
ricostruisce il frontend e `update_js_cache` non riusciva a scaricare `mathjax`
(`SSL: CERTIFICATE_VERIFY_FAILED`) in una cartella gitignorata (`.gitignore:78`), oltre a
`node_modules` assente. Il coordinatore ha riparato cache e dipendenze — **non io**: le regole mi
vietano `npm install`. Il gate è poi risultato **verde: `10 passed`**.

**3-bis. ⚠️ I gate `services` e `api` si distruggono a vicenda nella stessa lane. L'ordine conta.**
Provato in tre esecuzioni, non dedotto:

1. `api risk` su DB di sola migrazione → **2 failed** (`user 'e2e_test_user' is missing`)
2. `db populate --force --clean` → `api risk` → **10 passed**
3. `services risk-all` → ricrea un DB pulito (*«Clean test database created»*) → `api risk`
   di nuovo → **2 failed**, stessa causa

`services risk-all` ha come prerequisito un database pulito e lo **ricrea**, cancellando le
fixture di cui `api risk` ha bisogno; il runner **non** ripopola da solo. Ordine obbligato per
chiudere entrambi:

> `services risk-all` → `db populate --force --clean` → `api risk`

Chi li esegue nell'ordine inverso vede un rosso che **non ha nulla a che fare col proprio codice**.
Vale per ogni mandato della campagna, e per chiunque riverifichi i gate a valle.

**3-ter. Due PNG non tracciati, non miei, da NON mettere in staging.**
`mkdocs_src/docs/static/icons/asset-types/` contiene **12** file ma ne ha **10** tracciati:
`commodity.png` e `real-estate.png` sono non tracciati e **non gitignorati**. Alle 00:48
`git status` non li vedeva; compaiono dopo la riparazione di bootstrap del coordinatore, con
`mtime` pari all'ora di creazione del worktree (compatibile con una copia che preserva i
timestamp). Non ho mai usato `--with-static` né scritto in quella cartella. **Fuori dal mio
checkpoint.**

**4. Una fetta che nomina *tutti* gli asset rinuncia comunque al TWRR.** Conseguenza voluta di
Q-C1(a): la condizione guarda `slice_asset_ids`, non la sua estensione. È difendibile — la
fetta rinormalizza via la cassa, quindi il TWRR del portafoglio non la descrive più — ed è
dichiarata da `return_basis`. Comportamento fissato da un test perché un cambiamento sia
deliberato. **Decisione di prodotto**, segnalata al coordinatore per E.
