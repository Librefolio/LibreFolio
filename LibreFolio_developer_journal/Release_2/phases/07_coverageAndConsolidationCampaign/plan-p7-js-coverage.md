# Coverage JavaScript — livelli A e B

> **Stato**: piano in attesa di approvazione.
> **Vincolo di partenza**: ~~si comincia solo dopo che l'agente E2E ha finito~~ → **sbloccato il
> 12/08/2026**: l'agente E2E ha consegnato, il committente ha fatto il commit (`52784a3a`),
> l'albero di lavoro è pulito.
> **Fuori scope**: livello C (component test in isolamento). Escluso su indicazione del committente:
> richiederebbe mock e testerebbe il componente fuori dal suo contesto reale.
>
> Il mirror del piano P3 è conservato qui accanto come `plan-p3-mirror.md`.

---

## 1. Il problema

Oggi il progetto misura la coverage **solo di Python**. I due report esistenti sono entrambi Python:

| Cartella | Cosa misura davvero | Guidato da |
|---|---|---|
| `htmlcov-backend` | Python del backend | test backend |
| `htmlcov-frontend` | **Python del backend** | E2E del frontend |
| `htmlcov` | Python, combinato | entrambi |

Su **92.603 righe di `.svelte`** e **41.338 di `.ts`** la visibilità è **zero**. Non esiste alcun
dato che dica quali componenti gli E2E attraversano davvero, né quali non tocca nessuno.

L'obiettivo dichiarato è duplice: trovare i **buchi** e trovare le **aree sovra-testate**.

---

## 2. Cosa ho verificato prima di pianificare

Nessuna di queste è una stima: sono misure fatte sul repository, con uno spike poi rimosso.

| Verifica | Esito | Perché conta |
|---|---|---|
| Gli E2E girano già su un build **debug** | ✅ `cmd_server`: `if test_mode: debug_mode = True` | **Nessuna modifica al build.** Sourcemap e codice non minificato ci sono già |
| Marker su disco | ✅ `frontend/build/.build-debug` = `1` | Il build corrente è già quello giusto |
| Sourcemap risalgono ai `.svelte` | ✅ 83 map, 77 con `sourcesContent`, **196/199** componenti raggiungibili | È la condizione necessaria di tutto il livello B |
| V8 coverage raccolta da Chromium sul build servito | ✅ 14 script, **12 con sourcemap utilizzabile** | La raccolta funziona |
| Remap byte-eseguiti → `src/**/*.svelte` | ✅ percorsi originali corretti | La catena completa regge |
| Entrambi i progetti Playwright sono Chromium | ✅ `desktop` + `mobile` (forzato a chromium) | `page.coverage` è Chromium-only: qui non è un limite |
| `auto_build_frontend` gestisce il mismatch di modalità | ✅ ricostruisce da solo | Nessun rischio di misurare il bundle sbagliato |
| Esecuzione sequenziale | ✅ `workers: 1`, `fullyParallel: false` | Niente contesa in scrittura sui dati di coverage |

> **La conseguenza più importante**: l'ostacolo che credevo maggiore — «bisogna far girare gli E2E
> su un artefatto diverso da quello che si spedisce» — **non esiste**. Il test server costruisce già
> in debug. Il livello B costa molto meno del previsto.

### Strumenti scelti

`monocart-coverage-reports` **2.12.12** (dipendenze contenute, include i reporter istanbul) più
`vitest-monocart-coverage` **4.0.2** per il lato unit. Un solo ecosistema per entrambi i livelli:
è ciò che rende possibile **un report unico** invece di due silos. Esiste anche l'esempio
ufficiale del caso nostro — `merge-code-coverage-vitest` (Vitest unit + Playwright e2e).

---

## 3. Architettura scelta

```
vitest  ──(vitest-monocart-coverage)──▶  coverage-js/unit/raw   ─┐
                                                                 ├─▶ mcr merge ─▶ coverage-js/combined
Playwright ──(fixture page.coverage)──▶  coverage-js/e2e/raw    ─┘
```

Il formato `raw` è il punto d'incontro: la stessa strategia del backend, dove i `.coverage.*` dei
sottoprocessi vengono uniti con `coverage combine`. Il parallelo con `_coverage.py` è deliberato —
chi conosce già il flusso Python ritrova lo stesso schema.

### Decisioni di progetto

1. **Fixture manuale, non `monocart-reporter`.** Il reporter sostituirebbe anche il report dei
   test, che oggi è l'HTML di Playwright e funziona. Una fixture aggiunge coverage senza toccare
   nient'altro.
2. **`sourceFilter` limitato a `src/`.** Nello spike sono emersi 47 falsi positivi: file
   `src/runtime/client/*.js` che sono il runtime interno di SvelteKit, non codice nostro. Vanno
   esclusi o il report mente.
3. **`all` (file mai eseguiti a 0%) solo sul report combinato.** Sul report unit elencare 199
   `.svelte` a 0% sarebbe rumore: vitest non può eseguirli per costruzione. Sul combinato invece è
   esattamente l'informazione richiesta — «cosa non tocca nessuno».
4. **Nessuna soglia bloccante.** Svelte 5 compila i template in closure: il remap dice bene *se* un
   componente o un ramo è stato attraversato, ma le percentuali per-riga non sono affidabili al
   punto da farci passare o fallire una build.

---

## 4. Piano di lavoro

### Fase 0 — Baseline e prerequisiti

- **0.0** ✅ **Fatta.** Corsa di riferimento con la macchina di coverage attuale (solo Python).
  Esito e conseguenze qui sotto.
- **0.1** ~~Attendere la consegna degli spec E2E.~~ ✅ **Fatto.** Consegnati e committati.
  La superficie è cresciuta: **60 spec** (+3), **64 file** che importano da `@playwright/test`
  (era 61), **56 file unit** vitest (era 54).
- **0.2** Allineare `vitest` (oggi **4.1.0**) alla `4.1.x` richiesta da `@vitest/coverage-v8 ^4.1.2`,
  che `vitest-monocart-coverage` porta con sé. Vitest verifica la corrispondenza di versione fra sé
  e il provider di coverage.
- **0.3** Installare `monocart-coverage-reports` e `vitest-monocart-coverage` come devDependency.

#### Risultato della baseline (12/08/2026)

15/15 categorie eseguite. Copertura **Python**:

| Report | Statement | Non coperti | Copertura |
|---|---|---|---|
| `htmlcov-backend` — guidato dai test backend | 37.331 | 3.252 | **91,29 %** |
| `htmlcov-frontend` — guidato dagli E2E | 37.331 | 21.228 | **43,14 %** |
| `htmlcov` — combinato | 37.331 | 3.237 | **91,33 %** |

> **Il numero che decide il piano**: passando da 91,29 % a 91,33 % gli **oltre 60 spec E2E
> aggiungono 15 statement Python** su 37.331 — lo **0,04 %**. Praticamente nulla.
>
> Non è una critica agli E2E: è la prova che stiamo misurando la cosa sbagliata. Quegli spec non
> esistono per esercitare il backend — lo fanno già i test backend, e meglio. Esistono per
> esercitare il **frontend**, e di quel lavoro oggi non registriamo **niente**: 199 componenti
> `.svelte` (92.553 righe) e 180 moduli `.ts` (41.498 righe), **134.051 righe non misurate**.
>
> La domanda «quanto vale il resto del piano» ha quindi una risposta quantitativa: la coverage
> guidata dagli E2E oggi produce lo 0,04 % di informazione nuova; il livello B la farebbe puntare
> sulle 134.051 righe su cui quegli spec agiscono davvero.

#### Due rossi, entrambi causati dalla coverage stessa

La corsa ha prodotto 2 rossi. Entrambi **passano senza `--coverage`** e falliscono **con**
`--coverage` — verificato rilanciando i singoli spec:

| Spec | Con coverage | Senza coverage | Natura |
|---|---|---|---|
| `assets/asset-classification.spec.ts` | 0/3 | **3/3** | difetto di **prodotto** |
| `transactions/tx-wac-bulk.spec.ts` (WB5) | 9/10 | **10/10** | difetto di **test** |

- **`asset-classification`** — `DistributionEditor.addEntry()` sceglie la chiave di default da
  `countries`, popolato **asincronamente** da `ensureCountriesLoaded()`. Se il click su «+Add»
  precede la risposta, la chiave è `''` e la riga viene poi scartata in silenzio. Con il backend
  rallentato dall'instrumentazione la finestra si allarga e il caso diventa sistematico — ma può
  colpire un utente vero su macchina carica o rete lenta. **Da segnalare come bug a sé.**
- **`tx-wac-bulk` WB5** — il test fa `allRows.count()` senza attendere il popolamento della
  tabella: se il backend è lento conta zero righe. Qui il difetto è nel test, non nel prodotto.

Nota di metodo emersa: `./dev.py` usa lo shebang `python3`. Se in PATH `python3` non è
l'interprete del venv, il `webServer` di Playwright non parte (`ModuleNotFoundError: pydantic`).
Va lanciato con il venv in PATH, non invocando l'interprete del venv su `dev.py`.

#### Cosa ha consegnato l'altro agente (rilevante per questo piano)

23 test backend nuovi, 29 vitest, 34 E2E nuovi o riallineati; `--fresh-run all` verde su 15/15
categorie. Tre spec nuovi coprono proprio l'area P3: `tx-import-asset-identity.spec.ts`,
`asset-merge.spec.ts`, `tx-import-ca-contract.spec.ts`, e `tx-import-resolution.spec.ts` è stato
riallineato ai 7 step — il disallineamento che avevo segnalato nell'handoff è quindi **risolto**.

I 4 difetti che i suoi test hanno trovato dicono però qualcosa di utile su cosa aspettarsi da
questo piano:

| Difetto trovato | La coverage l'avrebbe segnalato? |
|---|---|
| `AssetMergeModal` non scrollabile, footer fuori viewport | ❌ codice **eseguito**, ma resa sbagliata |
| `tx-brim-import` ignorava lo step «Unifica strumenti» | ❌ è il *test* a essere incompleto, non il codice |
| Evidenza CA senza `comment` | ❌ dato mancante, non ramo morto |
| Flake su `risk-analysis` | ❌ problema di attesa |

**Nessuno dei quattro.** Conferma sperimentale dell'avvertenza al §5: la coverage indirizza dove
guardare, non sostituisce chi guarda. Ragione in più per tenerla come mappa e non come voto.

### Fase A — Coverage unit (vitest)

- **A.1** ✅ `vitest.config.ts`: `coverage.provider: 'custom'` +
  `customProviderModule: 'vitest-monocart-coverage'`; output in `coverage-js/unit`, report
  `raw`. **`enabled: process.env.COVERAGE_JS === '1'`**.
- **A.2** ~~Script `test:unit:coverage` in `package.json`.~~ **Non serve** — vedi sotto.
- **A.3** ~~Cablare il flag in ogni invocazione vitest.~~ **Ridotto a una riga** — vedi sotto.
- **A.4** ✅ Verifica sul campione di controllo: `assetSimilarity` risulta al **96,26 %** di
  statement. Il cablaggio è corretto.
- **A.5** ⚠️ **`cleanCache: false` non basta** — vedi «L'accumulo unit» qui sotto.

> **Note implementazione (Fase A)**: fatta. Il provider custom si aggancia senza toccare i
> call site.

> **⚠️ Fuori pista — l'accumulo unit non funziona con la cache.** `cleanCache: false` conserva
> la `.cache`, ma **non** il risultato: `vitest-monocart-coverage` chiama `generate()` alla fine
> di **ogni** processo vitest, e `generate()` **consuma** la cache. Con 8 invocazioni, l'ottava
> cancellava le prime sette (misurato: 12 file raw → 4).
>
> Soluzione: **`outputDir` per processo** — `coverage-js/unit/${Date.now().toString(36)}-${pid}`
> con `reports: ['raw']`, e `mcr merge` a fine corsa. Verificato: due corse consecutive
> producono due cartelle coesistenti, e il merge le unisce (241 statement da entrambi i file).
>
> Nota: sul lato **E2E vale l'opposto** — lì la fixture chiama solo `add()`, quindi la cache
> accumula fra i 60+ processi Playwright e basta un `generate()` finale. Due strategie opposte
> che arrivano allo stesso risultato, ognuna dal lato da cui il vincolo lo consente.

#### Una variabile d'ambiente al posto di 8 modifiche

Verificato leggendo il runner: **non esiste un entry point unico** per i test unit. `vitest` è
invocato da **8 punti** (`_frontend_asset.py`, `_broker`, `_fx`, `_portfolio` ×2, `_transaction`,
`_user`, `_utility`, `_ai_export`) ognuno con la propria lista esplicita di file.

Modificarli tutti sarebbe fragile. Ma `run_command` chiama `subprocess.run(..., env=None)` per i
comandi non-pytest: **i sottoprocessi ereditano `os.environ`**. Basta quindi impostare la variabile
una volta sola in `_cli.py`, dove la modalità viene già calcolata:

```python
if mode in ('js', 'all'):
    os.environ['COVERAGE_JS'] = '1'
```

e leggerla nei due soli posti che la consumano — `vitest.config.ts` (`coverage.enabled`) e la
fixture Playwright. Risultato: **8 call site vitest invariati, 77 firme invariate, zero script npm
nuovi.**

### Fase B — Coverage E2E (Playwright)

- **B.1** `e2e/fixtures/playwright.ts`: barrel che ri-esporta `expect` e i tipi da `@playwright/test`
  ed estende `test` con una fixture `page` che, **solo se `COVERAGE_JS=1`**, apre
  `startJSCoverage({resetOnNavigation: false})`, e a fine test chiude e consegna i dati a MCR.
  A flag spento il costo è nullo.
- **B.2** Riscrittura meccanica degli import negli spec: `from '@playwright/test'` → barrel.
  Sono **64 file** (dopo la consegna dell'altro agente). Il barrel ri-esporta esattamente i 9
  simboli che gli spec usano oggi — `test`, `expect`, `Browser`, `BrowserContext`, `Page`,
  `Locator`, `Request`, `Response` — quindi cambia **solo il percorso del modulo**.
  Verifica con `./dev.py front check`.
  ⚠️ **Eccezione da gestire**: `verbatimModuleSyntax: true` è attivo. Tre file
  (`broker-sharing.spec.ts`, `multi-user.spec.ts`, `fixtures/auth-helpers.ts`) importano
  `Page`/`Browser`/`BrowserContext` come **valori** anziché con `import type`. Vanno convertiti,
  altrimenti il barrel — che li ri-esporta come tipi — romperebbe a runtime.
- **B.3** `mcr.config.js`: `entryFilter` / `sourceFilter` per tenere solo `src/`, e
  `sourcePath` per normalizzare i percorsi.
- **B.4** Generazione a fine corsa. `_run_playwright` viene invocato **una volta per suite**: i dati
  si accumulano nella `.cache` di MCR fra processi e il report si genera una sola volta alla fine,
  esattamente come `_finalize_coverage` fa con i `.coverage.*`.
- **B.5** ✅ Verifica mirata. Vedi «Note implementazione (Fase B)».

> **Note implementazione (Fase B)**: fatta. La riscrittura degli import ha toccato **64 file**
> ed è stata fatta a macchina; `./dev.py front check` chiude con **0 errori, 0 warning**.
> I 3 file che importavano tipi come valori sono stati convertiti a `import type` inline.
>
> Verifica B.5 (12/08/2026, spec `auth.spec.ts`, 16 test): il report contiene **318 file —
> 175 `.svelte` e 143 `.ts`**, tutti sotto `src/`, zero rumore. La catena regge fino ai
> componenti.

> **⚠️ Fuori pista 1 — le sourcemap esterne non vengono seguite.** Il primo report E2E era
> **vuoto**: le entry avevano `sourcePath` tipo `localhost-6041/_app/immutable/chunks/X.js` e
> nessuna risoluzione. Indagando: i `.js.map` sono serviti correttamente (HTTP 200), 66/66 chunk
> hanno il commento `sourceMappingURL`, e `stopJSCoverage()` restituisce `source` per 23/23
> entry. Il problema è a valle: **monocart non scarica i `.map` esterni**. L'esempio ufficiale
> funziona perché i dev server li incorporano *inline*.
>
> Soluzione: un `sourceMapResolver` in `mcr.shared.js` che legge le map **da disco** da
> `frontend/build/_app/…`. Leggerle da disco non è un'ottimizzazione ma un requisito: la
> generazione del report avviene **dopo** che Playwright ha già spento il test server.

> **⚠️ Fuori pista 2 — il codice di terze parti non si esclude per prefisso.** Dopo il fix i
> file erano 106, ma **78 erano il runtime di Svelte** (`src/internal/client/…`): le sourcemap
> npm conservano i percorsi *interni al pacchetto*, indistinguibili dai nostri. Il
> `sourceFilter` è quindi diventato un **controllo di esistenza su disco** contro il contenuto
> reale di `frontend/src`. Risultato: da 106 a **26 file** puliti su un semplice caricamento
> della pagina di login.
>
> Escluso anche il documento HTML dall'`entryFilter` (i suoi script inline comparivano come un
> file fantasma `localhost-6041`), limitando la regola agli URL `http(s)` perché le entry
> `file://` di vitest devono continuare a passare.

> **⚠️ Fuori pista 3 — un falso allarme che è costato tempo.** Dopo il fix un report sembrava
> ancora vuoto perché `index.html` pesava 1 KB. In realtà **è normale**: il report `v8` mette i
> dati in `coverage-data.js` (2,2 MB) e `index.html` è solo il guscio. Il report davvero vuoto
> era un altro, e la causa era banale: la cache era stata scritta da processi Playwright avviati
> **prima** della modifica a `mcr.shared.js`. Le sourcemap vengono risolte in `add()`, non in
> `generate()` — quindi una cache scritta con la configurazione vecchia resta inservibile anche
> se si rigenera con quella nuova. **Dopo aver toccato i filtri, la cache va buttata.**

### Fase C — Unione, CLI e nomi

- **C.1** `mcr merge --inputDir coverage-js/unit/raw,coverage-js/e2e/raw --outputDir
  coverage-js/combined`, con `all` attivo per far emergere i file mai eseguiti.
- **C.2** **Nuova semantica del flag**: `--coverage [py|js|all]`, con **`all` come default** quando
  il valore è omesso.
- **C.3** Estendere `./dev.py test coverage show` con i nuovi bersagli JS.
- **C.4** **Disambiguare i nomi.** Il titolo HTML è già corretto («Frontend E2E → Backend
  Coverage»): è il nome della cartella a ingannare. `htmlcov-frontend` → `htmlcov-backend-e2e`,
  con aggiornamento di `.gitignore`, del CLI e dei riferimenti nella documentazione.
- **C.5** Aggiungere `coverage-js/` a `.gitignore`.

#### `all` significa «tutto il misurabile *in quella suite*»

> **Note implementazione (Fase C)**: fatta. `_finalize_js_coverage()` orchestra tre passaggi —
> merge di `unit/*/raw` → `unit-combined`, generazione di `e2e` dalla cache, merge dei due →
> `combined` con `--all src` e report `json` (che abilita la Fase D).
>
> Non esiste un `mcr generate` da CLI (il comando `merge` legge i file raw, non la cache):
> serve quindi `frontend/scripts/mcr-generate.js`, invocato dal runner.

> **⚠️ Fuori pista 4 — `nargs='?'` ha rotto una sintassi documentata.** Rendendo il flag
> `--coverage [py|js|all]`, argparse ha cominciato a mangiarsi il token successivo:
> `./dev.py test --coverage api all` — la forma che compare **9 volte** nella skill
> `testing-backend` — veniva letta come «linguaggio `api`». argparse **non ha lookahead**:
> `nargs='?'` prende il token seguente e basta.
>
> Soluzione: `normalize_coverage_argv()`, che inserisce `all` quando il token dopo `--coverage`
> non è un linguaggio valido. Tutte e cinque le forme d'invocazione sono state riverificate.

> **⚠️ Fuori pista 5 — e il normalizzatore ha rotto il webServer.** La stessa funzione riscriveva
> anche la riga di comando che Playwright usa per il server
> (`./dev.py server --test --force --workers N --coverage`), producendo
> `unrecognized arguments: all`. Aggiunta una guardia `only_command="test"`: `server --coverage`
> **deve** restare booleano, perché un server può misurare solo Python.
>
> Morale: un normalizzatore di argv è comodo ma è un'azione a distanza. Va sempre limitato al
> sotto-comando che lo richiede.

Non «tutto sempre». `--coverage` è già usato dalle suite **backend** — `./dev.py test --coverage
api all` compare in più punti della skill `testing-backend` — dove il JS non esiste nemmeno:

| Suite eseguita | Cosa raccoglie `all` |
|---|---|
| backend (`api`, `db`, `services`, `schemas`, `utils`, `external`) | solo Python |
| E2E Playwright | Python **+ JS** |
| unit vitest | solo JS |

Chiedere esplicitamente qualcosa di inapplicabile (`--coverage js` su una suite backend) deve
produrre un errore chiaro, non un report vuoto.

> `./dev.py server --coverage` resta **booleano**: il server può misurare solo Python. Non va
> generalizzato.

#### L'impianto esiste già: non serve toccare 77 firme

Il valore va tenuto in `_common._COVERAGE_MODE`, la globale **già cablata** in tutto il runner
(`_cli.py:116, 479, 538, 626`). I ~77 parametri `coverage: bool = False` sparsi nei moduli
`_frontend_*.py` restano **invariati**: continuano a funzionare da interruttore acceso/spento,
perché una stringa non vuota è vera. È solo `_run_playwright` a leggere la modalità e decidere
quali variabili d'ambiente esportare:

```python
if mode in ('py', 'all'):  env['COVERAGE_BACKEND'] = '1'
if mode in ('js', 'all'):  env['COVERAGE_JS'] = '1'
```

Il che riduce una modifica apparentemente invasiva a **una globale più un helper**.

Schema finale:

| Cartella | Misura | Guidato da |
|---|---|---|
| `htmlcov-backend` | Python | test backend |
| `htmlcov-backend-e2e` | Python | E2E |
| `htmlcov` | Python combinato | entrambi |
| `coverage-js/unit` | **JS/Svelte** | vitest |
| `coverage-js/e2e` | **JS/Svelte** | E2E |
| `coverage-js/combined` | **JS/Svelte** combinato | entrambi |

### Fase D — Analisi dei buchi ✅ *(fatta)*

Esiste già `./dev.py test coverage-report` (`scripts/coverage_analysis.py`, 544 righe): legge la
chiave `functions` del JSON di coverage e classifica per priorità le funzioni non coperte. È
**esattamente** lo strumento che serve all'obiettivo dichiarato, ma parlava solo il formato
Python.

- **D.1** ✅ Il merge e i report singoli emettono anche `json` (istanbul), così l'input esiste
  sempre senza passaggi manuali.
- **D.2** ✅ `scripts/coverage_js.py`: riconoscimento del formato, conversione, e regole di
  classificazione frontend. I due classificatori dell'analizzatore sono diventati **iniettabili**;
  `--lang` serve solo a scegliere il percorso di default, il formato si riconosce dalla forma.

> **Note implementazione (Fase D)**: fedeltà della conversione verificata — 9354 funzioni in
> ingresso, 9354 in uscita. Percorso Python invariato (stesso output di prima).
> Due limiti dichiarati in chiaro nella documentazione: i componenti Svelte non hanno nomi di
> funzione (voci rinominate `block@142`) e le istruzioni sono attribuite per intervallo di righe,
> quindi le closure annidate contano due volte (scarto misurato: 3,5 %).

### Fase E — Documentazione, skill e verifica

- **E.1** ✅ Aggiornate `developer/test-walkthrough/front-overview.md`, `index.md` e
  `runner_architecture.md`: nuova sintassi del flag, rinomina `htmlcov-frontend` →
  `htmlcov-backend-e2e`, bersagli `show js|js-unit|js-e2e`.
- **E.2** ✅ Nuova pagina `developer/test-walkthrough/coverage-model.md` sui due assi (**quale
  linguaggio** si misura, **quale suite** lo guida), aggiunta alla `nav` di `mkdocs.yml`.
- **E.3** ✅ Aggiornate le tre skill: `testing-backend` (il flag prende un linguaggio
  opzionale e perché `--coverage api all` continua a funzionare), `testing-frontend` (il barrel
  obbligatorio negli import, il livello JS, i file chiave), `devpy-server` (perché lì il flag
  resta booleano). Le `engineering-skills` di terze parti **non** sono state toccate.
- **E.4** Verifica finale: `./dev.py front check` ✅ 0 errori 0 warning; corsa
  `--coverage all front-transaction all` in corso.

> **Note implementazione (Fase E)**: fatta. Depositato anche il piano nel journal come
> `plan-phase00FrontendCoverage.prompt.md` (P7), con cross-link bidirezionale a P3 e voce
> in `INDEX.md`.

### Fase F — I due difetti della baseline *(change set isolato)*

- **F.1** ✅ `DistributionEditor.addEntry()` ora attende i dati di riferimento se non sono
  ancora arrivati e **non aggiunge righe senza chiave**. Il difetto era di prodotto, non di test.
- **F.2** ✅ `tx-wac-bulk.spec.ts` WB5: aggiunta l'attesa del popolamento della tabella prima
  di `allRows.count()`. Verificato verde nella corsa `front-transaction all`.
- **F.3** ✅ **Secondo difetto di prodotto, scoperto risalendo il primo**: dopo il salvataggio
  la pagina di dettaglio ricarica i dati in modo asincrono, ma il pulsante «Modifica» restava
  attivo per tutta la durata della ricarica. Riaprendo la modale in quella finestra si
  ripresentavano i valori **pre-salvataggio**. Corretto disabilitando il pulsante finché la
  ricarica non è conclusa (`classificationLoaded` azzerato all'*inizio* di `reloadMetadata()`,
  non a metà). Spec `asset-classification` ora **3/3 sotto coverage**.
- **F.4** ✅ **`gracefulShutdown` a 5 s scartava in silenzio la coverage Python.** Playwright
  manda SIGTERM al test server e dopo 5 s passa a SIGKILL: se il flush del file SQLite di
  `coverage` non fa in tempo, l'intera corsa perde i dati backend — senza errori, solo un
  «No `.coverage.*` files found» a fine corsa. Finestra portata a 30 s **solo** quando
  `COVERAGE_BACKEND` è attivo. Verificato: stessa spec, da «nessun dato» a **40,36 %**.

> **⚠️ Fuori pista 6 — il primo fix era corretto ma insufficiente, e l'ho scoperto solo
> guardando il database.** Dopo F.1 la spec falliva ancora nello stesso punto. Interrogando
> `backend/data/test/sqlite/app.db` si vedeva però che il dato **era stato salvato**
> (`{"geographic_area": {"distribution": {"AFG": "1.0000"}}}`): il salvataggio funzionava, era
> la **rilettura** a mostrare valori vecchi. Senza quella verifica sul dato persistito avrei
> continuato a cercare il bug dal lato sbagliato della catena.
>
> Vale come metodo: quando un round-trip fallisce, la prima domanda non è «perché non si vede»
> ma «il dato c'è?». Sono due bug diversi e si correggono in due posti diversi.

### Fase G — Verifica di non regressione ✅

- **G.1** ✅ `front-asset all` → **8/8** dopo le modifiche al prodotto (il pulsante disabilitato
  è il punto d'ingresso di 4 spec: andava provato, non dedotto).
- **G.2** ✅ `front-utility utilities` era **rossa già prima**: 4 fallimenti su attese di test
  rimaste indietro rispetto all'API — `items` è ora una lista di oggetti `{key, emoji}`, la lista
  paesi termina con un'entry «Other» voluta, e `.first()` su `[role="combobox"]` non pescava più
  il selettore valuta. Corretti → **16/16**.

> **⚠️ Fuori pista 7 — un test che passava senza misurare nulla.**
> `expect(data.items).not.toContain('Other')` su una lista di oggetti è vero per costruzione,
> qualunque cosa contenga la lista. Verde, inutile, e **invisibile alla coverage**: quel codice
> veniva pur sempre eseguito. È il limite dichiarato del piano visto dal vivo — la coverage trova
> il codice che non gira, non il test che non verifica.

- **G.3** ✅ Corsa `--coverage all front-fx all` (unica suite con **sia** vitest sia Playwright):
  8/8 verde e i tre report JS generati. È qui che è emerso il difetto qui sotto.

> **⚠️ Fuori pista 8 — il report combinato conteneva una sola delle due fonti.** Il merge era a
> due passi (`unit/*/raw` → `unit-combined`, poi `unit-combined/raw` + `e2e/raw` → `combined`),
> ma **`mcr merge` non riemette il report `raw`**: lo chiedevo, non protestava, e la cartella non
> nasceva. Il secondo merge leggeva un percorso inesistente e produceva un «combinato» di solo E2E.
>
> Invisibile a occhio — il report si genera, ha 376 file, le percentuali sono plausibili. L'ho
> visto solo confrontando lo stesso file nei tre report: `EditBuffer.ts` a **61/74** negli unit e
> **0/0** nel combinato, dove compariva solo perché `--all` elenca i file mai eseguiti.
> Corretto passando al merge finale i **raw originali**. Controprova: `fxStoreRegistry.ts` da
> 90/174 (unit) e 73/131 (e2e) a **95/177** nel combinato — più di entrambe, che è ciò che
> significa unire.
>
> Uno strumento di misura che **non fallisce** quando perde metà dei dati è più pericoloso di uno
> che si rompe.

---

## 5. Rischi e limiti dichiarati

| Rischio | Portata | Mitigazione |
|---|---|---|
| **La coverage cambia i tempi** | ⚠️ **Confermato sperimentalmente**: `asset-classification.spec.ts` passava 3/3 **senza** coverage e falliva 3/3 **con** coverage. L'instrumentazione Python rallenta il backend quanto basta a trasformare **due** race latenti in errori deterministici (F.1 e F.3) | La corsa con coverage va trattata come un ambiente *lento*, non come la corsa di riferimento. **Ha già ripagato**: due difetti di prodotto reali trovati così |
| **Precisione per-riga su Svelte 5** | I template diventano closure: il dato è affidabile su «attraversato / non attraversato», meno su «riga X coperta» | Nessuna soglia bloccante; il report si legge come mappa, non come voto |
| **Riscrittura di 64 import** | Tocca ogni spec | Il barrel ri-esporta tutto, cambia solo il percorso; `front check` verifica; l'albero è pulito e committato, quindi un `git diff` isola l'intera modifica |
| **2 bundle su 14 senza sourcemap** | Piccola zona cieca (service worker) | Documentata, non risolta |
| **Il service worker non è coperto** | `page.coverage` non vede il contesto del SW | Documentato |
| **Rallentamento degli E2E** | Da misurare alla fase B.5 | Il flag è opt-in: la corsa normale non paga nulla |
| **Falsa sicurezza** | La coverage trova codice **non eseguito**, non codice **sbagliato** | Vedi sotto |

### Un effetto collaterale inatteso, e utile

Il rosso di `asset-classification` sotto coverage **non è un falso positivo**: è un difetto vero che
la corsa normale non vede.

`DistributionEditor.addEntry()` sceglie la chiave di default da `countries`, che viene popolato
**in modo asincrono** da `ensureCountriesLoaded()`. Se il click su «+Add» arriva prima che quella
chiamata risolva, l'array è vuoto, la chiave risulta `''`, e la riga viene poi scartata: sparisce
senza dire niente. Con il backend rallentato dall'instrumentazione la finestra si allarga e il caso
diventa sistematico — ma la stessa cosa può capitare a un utente vero su una macchina carica o con
una rete lenta.

Ne segue una conclusione che vale la pena tenere: **girare sotto coverage funziona anche da prova
di resistenza in ambiente lento**. È un beneficio che non era nelle motivazioni iniziali del piano
e che va oltre la semplice misura di quali righe vengono attraversate.

### L'avvertenza che conta

Sui difetti realmente trovati in P3, la coverage ne avrebbe segnalati circa la metà:

| Difetto | L'avrebbe visto? |
|---|---|
| «Tieni com'è» non azzerava | ✅ ramo mai eseguito |
| Step condizionali | ✅ probabile |
| Ricerca dalla 4ª lettera | ❌ la funzione girava — era sbagliata, non morta |
| Raggruppamento dopo le correzioni | ❌ bug di ordine |
| Dizionario suffissi hard-coded | ❌ scelta di design |

Il guadagno vero di P3 non è stato un numero di copertura, ma l'aver estratto la logica pura in
moduli `.ts` testabili senza UI. La coverage serve a **indirizzare** quel lavoro, non a sostituirlo.

---

## 6. Punti aperti

1. ~~**Semantica dei flag.**~~ **Deciso**: `--coverage [py|js|all]`, con `all` come default se il
   valore è omesso, e `all` interpretato come «tutto il misurabile in quella suite» (vedi C.2).
2. ~~**Fase D**, l'analizzatore dei buchi lato JS: dentro o fuori da questo giro?~~ **Fatta**:
   era la parte che più direttamente serviva all'obiettivo dichiarato — «trovare i buchi e le
   aree sovra-testate» — ed è costata un modulo di adattamento (`scripts/coverage_js.py`), non
   una riscrittura. `./dev.py test coverage-report --lang js --summary`.
3. **Prima misura vera**: resta da fare una corsa `--fresh-run --coverage all all` per la
   fotografia iniziale, da cui far partire il lavoro sui buchi. **Volutamente non fatta ora**:
   il committente ha chiesto di aspettare che l'altro agente finisca di scrivere i test E2E,
   altrimenti la baseline nascerebbe già vecchia.

---

## Stato finale

Tutte le fasi sono **fatte e verificate**, Fase D compresa.

| Verifica | Esito |
|---|---|
| `front-fx all` con `--coverage all` (unica suite vitest **+** Playwright) | 8/8, tre report JS |
| `front-asset all` (regressione dei due fix di prodotto) | 8/8 |
| `front-utility utilities` | 16/16 |
| `asset-classification` sotto coverage, con dato backend | 3/3, 40,36 % |
| `./dev.py front check` | 0 errori, 0 warning |
| `./dev.py mkdocs build` | pulito |
| `ruff check` / `format` | allineati alla baseline (già rossa su righe non mie) |

Otto fuori pista in totale, di cui **tre difetti di prodotto** e **due difetti dello strumento di
misura** (la finestra di `gracefulShutdown` e il merge a due passi). Entrambi questi ultimi
producevano dati mancanti *senza fallire*, ed è il motivo per cui la verifica finale non si è
fermata al «verde» ma ha confrontato gli stessi file fra i tre report.

---

## 7. Nota di metodo

A piano approvato, questo documento va anche depositato nel journal come
`plan-phase00FrontendCoverage.prompt.md`, con cross-link al piano P3 (da cui nasce l'esigenza) e
il consueto aggiornamento passo-per-passo durante l'esecuzione.
