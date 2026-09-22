# B — esecuzione. Gli errori del rischio: quali dei 172 può causarli un utente

> Piano vivo. Aggiornato **dopo ogni passo**, non a fine mandato.
> Worktree `e-alfy-automatic-meme` · ramo `e-alfy-risk-errors-as-codes`
> Baseline `032b86959f783aec6ef784ff565027947435c71d` (= attesa `032b86959`) ✅
> Corsia **6173** · `/tmp/librefolio-r3-b`

---

## Passo 0 — Analisi ✅ 21 Set 2026

> **Note implementazione**: consegnata al coordinatore e approvata. Tre divergenze dal
> briefing, tutte confermate da lui: **D1** `RiskErrorCode` ha 13 valori non 12 (mancava
> `EXECUTION_FAILED`); **D2** non esiste un `ValueError` non catturato nel motore
> (`service.py:259` li cattura tutti → HTTP 200); **D3** *«il resto deve continuare a
> esplodere»* descriveva uno stato inesistente — il resto veniva convertito in
> `UNDEFINED_METRIC` **senza log**.
>
> Classificazione dei 172 per **confine di conversione** (9+8+5+28+8+4+110 = 172):
> 22 non raggiungibili da un utente · 40 già instradati correttamente · **110 nel catch-all**.
>
> **Quinta taglia trovata**: `RiskUnavailableError` è sottoclasse di `ValueError`, quindi
> `raise ValueError(` **non vede i 41 siti già instradati** — erano fuori dal conteggio che
> ne misurava il bisogno.

> **⚠️ Fuori pista — il mio primo criterio era falso, e l'ha ucciso un probe.**
> Avevo dedotto un buco confrontando i vincoli `Field(...)` di `SimulationParams.path_count`
> (`ge=256, le=100_000`, nessuna potenza di due) col guard del motore. **Eseguito**:
> `model_validate({sampling_method:'qmc', path_count:1000})` solleva già `ValidationError`.
> Il contratto esterno **non è `Field(...)`**: è `validate_params()` per intero,
> `model_validator` compresi. *Era un'inferenza travestita da misura, e da sola l'analisi
> statica l'avrebbe consegnata al coordinatore.*

---

## Passo 1 — Cancelli misurati sul mio worktree ✅ 21 Set

| cancello | briefing | **misurato** | esito |
|---|---|---|---|
| `services risk-all` | 437 | **437 passed** | ✅ identico |
| `api risk` | 11 | **11 passed** | ✅ (dopo repopulate, vedi fuori pista) |
| `front check` | 3 ereditati | **3 errori**, `TransactionFormModal.test.ts:787,819` + 1 | ✅ **0 file risk** |
| `vitest` | 46 in 5 file | 🔴 **41 in 3 file** | ✅ **0 file risk** |
| `alembic heads` | — | **una sola testa** `ab290f6b6756` | ✅ |
| `ruff` · `black` | puliti | puliti sui miei file | ✅ |

> **Note implementazione**: `vitest` diverge dal briefing — **41 rossi in 3 file**
> (`pac-allocator/PortfolioRebalancerTool` 20 · `pac-allocator/PacAllocatorTool` 15 ·
> `tools/registry` 6). I due che il briefing nominava in più — `DateRangePicker` e
> `ai-export/promptRenderer` — **sono verdi qui**. Plausibile che li abbia riparati la
> baseline su cui sto (`e-alfy-risk-asset-global-lab`, diversa da `f829cd76b`): **non l'ho
> verificato**, quindi lo riporto come misura, non come spiegazione.

> **⚠️ Fuori pista — Ⓠ colpisce, e più a fondo di com'era scritto.**
> `frontend/node_modules` mancava. Ⓠ prevedeva che tacesse il cancello frontend; **ha fatto
> cadere anche quello backend**: `dev.py server` ricostruisce il frontend, i test `api` hanno
> bisogno di quel server → `❌ Shared backend exited during startup (code 1)`, un sintomo che
> **non nomina né `node_modules` né `typescript`**. Causa vera, riprodotta a mano:
> `Cannot find package 'typescript'`. Nessuno skip esiste (`dev.py server --help` verificato).
> `npm --prefix frontend ci` **autorizzato esplicitamente dal coordinatore** dopo la conferma.
> Mai `install`/`update`/`audit fix`.

> **⚠️ Fuori pista — ho violato Ⓖ io stesso.** Avevo incatenato `api risk` **dopo**
> `services risk-all`, che fa `db create-clean`: 3 test su 11 rossi, tutti quelli che
> asseriscono contro il portafoglio di `db populate`. **Non un rosso di prodotto.**
> Riparato con `db populate --force` sulla mia cartella dati → **11/11**.
> *L'ordine Ⓖ vale fra invocazioni, non solo dentro una.*

---

## Passo 2 — B4, il cancello i18n ✅ 21 Set

> **Note implementazione**: due test in
> `backend/test_scripts/test_schemas/test_risk_schemas.py` (file **già registrato** come
> `schemas risk` → **nessuna modifica al catalogo del runner**):
> `test_every_risk_error_code_has_a_sentence_in_every_official_language` e
> `test_risk_error_catalogues_agree_across_languages`.
> Usano `RISK_SCENARIO_OFFICIAL_LANGUAGES` invece di quattro letterali, così una lingua
> aggiunta là è seguita qui. Un catalogo mancante è un **rosso**, mai uno skip: un test che
> passa perché non trova i file sarebbe lo stesso difetto col nome del test.
>
> **4 mutazioni su 4 catturate**: chiave enum rimossa · frase vuota · fallback `unknown`
> rimosso · **membro enum nuovo senza traduzione** (la direzione in cui il difetto viaggia
> davvero). File ripristinati, `git diff` = 0 righe.

---

## Passo 3 — B1(b), togliere la falsa rassicurazione ✅ 21 Set

> **Note implementazione**: rimosso il ramo `except (ValueError, ArithmeticError) →
> UNDEFINED_METRIC` da `service.py`. Quelle eccezioni cadono ora nel ramo generico già
> presente: `logger.exception` + `EXECUTION_FAILED` + `status=FAILED`.
>
> **Due misure che giustificano (b) e che non erano nel briefing**:
> ① l'**unico** emettitore di `UNDEFINED_METRIC` era il catch-all stesso (`service.py:262`) —
> **nessun plugin lo dichiarava**; ② una metrica genuinamente indefinita **non si esprime
> sollevando**: è `RiskValueStatus.UNDEFINED` per valore (`correlation.py:84`). Quindi
> un'eccezione che arrivava lì **non ha mai significato «metrica indefinita»**.
>
> `str(exc)` non è più propagato: la prosa interna resta nel log, dov'è azionabile; sul filo
> passa il codice. Test: `test_undeclared_value_error_is_reported_as_ours_while_a_declared_one_survives`
> — **coppia deliberata**, perché rimuovere la *presunzione* non deve rimuovere la
> *capacità*: un plugin che dichiara `UNDEFINED_METRIC` lo riceve ancora.
> **Mutazione M8** (reintroduzione del ramo) → rosso sulla riga giusta.

---

## Passo 4 — B2, guardie dichiarate ✅ 21 Set

> **Note implementazione**: **non** ho allargato il `try`, e il coordinatore ha accettato la
> correzione. La sua ricetta («copia `portfolio_optimization.py:221`») avrebbe convertito
> anche i **12 predicati C3** in `INVALID_PARAMETERS` — *«covariance must be symmetric»* come
> parametro dell'utente. **Un `try` allargato è un `except` che presume.**
>
> Classificati uno per uno i 29 di `quant/models.py`: **C1** 6 (già catturati a monte,
> provato) · **C2** 2 provati + 3 non provati · **C3** 12 · resto forma/coerenza interna.
>
> Due guardie esplicite in `simulation.py`, **prima** della costruzione:
> `block_length_days > observations` → **`INVALID_PARAMETERS`** (non `INSUFFICIENT_HISTORY`:
> abbassare il blocco è un'azione disponibile, trovare storia no) ·
> `assets × horizon > MAX_SOBOL_DIMENSION` sotto QMC → **`RESOURCE_LIMIT`**.
>
> **Provati per costruzione con controllo discriminante**: `block_length_days=900` rifiutato
> contro 30 osservazioni e **accettato contro 1000**; al massimo orizzonte **5 asset accettati,
> 6 rifiutati** — cioè un portafoglio ordinario, non un input patologico.
> **I tre non provati (`:108` `:84` `:86`) restano fuori**: fuori è il default onesto.
> **3 mutazioni su 3 catturate**, inclusa la guardia resa incondizionata (perdita su MC).

> **⚠️ Fuori pista — mi sono cancellato il lavoro con `git show HEAD:`.**
> Per ripristinare dopo una mutazione ho usato `git show HEAD:<path> > <path>` (la forma Ⓟ).
> **Ⓟ ripristina lo stato COMMITTATO**: su un file con lavoro **non committato** quella riga
> non annulla la mutazione, **cancella le modifiche**. Perso e riscritto per intero il
> contenuto di `simulation.py`. **Nessuna perdita silenziosa**: se ne è accorto il banco di
> mutazioni, perché M6 ha fatto fallire *anche* il test di M5.
> ✅ **Protocollo corretto, usato dopo**: `cp` del file in `session-state/files/` **prima**
> di mutare, e ripristino da lì. Ⓟ resta giusta per i file **di altri** toccati da
> `dev.py format`, dove HEAD *è* lo stato corretto.

---

## Passo 5 — B3 in `TODO_FUTURI.md` ✅ 21 Set

> **Note implementazione**: registrato **il metodo**, non il risultato — perimetro coi sette
> confini, criterio C1/C2/C3, il banco `sys.settrace`, l'obbligo del controllo discriminante,
> e **perché va fatto dopo B1(b)**: da adesso quei 110 siti loggano, quindi chi lo farà parte
> da occorrenze reali invece che da payload immaginati.
>
> Registrate anche due conseguenze da non «riparare» per sbaglio: `undefined_metric` **non ha
> più un emettitore di produzione** (e la sua chiave va tenuta viva in ×4 — cancellarla
> riaprirebbe il fallback silenzioso), e `portfolio_optimization.py:221` **ha lo stesso
> difetto latente**, segnalato e non riparato perché fuori perimetro.

---

## Passo 6 — Cancelli finali ✅ 21 Set

| cancello | prima | **dopo** | delta |
|---|---|---|---|
| `schemas risk` | 24 | **26 passed** | +2 (B4) |
| `services risk-all` | 437 | **441 passed** | +4 (B1 ×1, B2 ×3) |
| `api risk` | 11 | **11 passed** | invariato |
| `front check` | 3, zero risk | **3, zero risk** | invariato |
| `vitest` | 41 in 3 file, zero risk | **invariato** | non tocco il frontend |
| `ruff` · `black` | — | **puliti sui miei 5 file** | — |
| `git diff --check` | — | **pulito** | — |
| porta 6173 | — | **nessun listener** | — |

> **Note implementazione**: perimetro provato **dimensionalmente**, che è la forma accettata
> dal coordinatore: `git status --short -- frontend/` è **vuoto**. Zero file frontend toccati,
> quindi `front check` e `vitest` non possono essere stati alterati da me — una prova più
> forte, qui, di una suite che su questo worktree ha 41 rossi ereditati.
>
> Diff: **6 file modificati + 1 nuovo** (questo piano). `node_modules` è ignorato e non
> compare. Nessun artefatto generato, nessun dato privato, nessun `.testLog`.

> **⚠️ Fuori pista minore**: `ruff` ha trovato `I001` (blocco import non ordinato) su
> `test_risk_simulation.py` — avevo inserito `risk.base` dopo `risk.quant`. Riparato con
> `ruff check --fix` **puntato sul singolo file**, non con `dev.py format`, che non ha
> perimetro (Ⓟ). File rieseguito dopo: 38/38.

---

## Stato finale: **FROZEN** ✅ 21 Set 2026

Nessun server attivo, porta 6173 libera, nessuna operazione Git eseguita.
File nuovi dichiarati al coordinatore per il catalogo del runner: **nessuno** — i test
vivono in file **già registrati** (`schemas risk`, `services risk-all`).
