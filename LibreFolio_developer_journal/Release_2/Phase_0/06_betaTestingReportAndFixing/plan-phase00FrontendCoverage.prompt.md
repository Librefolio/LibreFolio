# P7 — Coverage JavaScript: misurare il frontend, non solo il backend

> **Nasce da** [`plan-phase00AssetIdentityAndIdentifiers.prompt.md`](plan-phase00AssetIdentityAndIdentifiers.prompt.md)
> (P3). Durante il beta testing e la successiva correzione è emerso che **quasi tutti i difetti
> si nascondevano in codice frontend che nessuna misura sorvegliava**. Questo piano chiude quel
> buco.
>
> **Stato**: 🟢 Fasi 0, A, B, C, E completate. Fase D (analizzatore dei buchi lato JS) **aperta**,
> in attesa di decisione.
>
> **Fuori scope**: livello C (component test in isolamento). Escluso su indicazione del
> committente: richiederebbe mock e testerebbe il componente fuori dal suo contesto reale.

---

## 1. Il problema

Il progetto misurava la coverage **solo di Python**. I tre report esistenti erano tutti Python:

| Cartella | Cosa misura davvero | Guidato da |
|---|---|---|
| `htmlcov-backend` | Python del backend | test backend |
| `htmlcov-frontend` | **Python del backend** | E2E del frontend |
| `htmlcov` | Python, combinato | entrambi |

Il nome `htmlcov-frontend` è il sintomo: suggeriva di misurare il frontend, e non l'ha mai fatto.
Su **92.553 righe di `.svelte`** e **41.498 di `.ts`** la visibilità era **zero**.

### Il numero che decide il piano

Corsa di riferimento completa (12/08/2026, 15/15 categorie verdi):

| Report | Statement | Non coperti | Copertura |
|---|---|---|---|
| `htmlcov-backend` — test backend | 37.331 | 3.252 | **91,29 %** |
| `htmlcov-frontend` — E2E | 37.331 | 21.228 | 43,14 % |
| `htmlcov` — combinato | 37.331 | 3.237 | **91,33 %** |

Passando da 91,29 % a 91,33 %, gli **oltre 60 spec E2E aggiungono 15 statement Python** su
37.331 — lo **0,04 %**.

Non è una critica agli E2E: è la prova che si stava misurando la cosa sbagliata. Quegli spec non
esistono per esercitare il backend — lo fanno già i test backend, e meglio. Esistono per
esercitare il **frontend**, e di quel lavoro non si registrava **niente**.

---

## 2. Cosa è stato verificato prima di pianificare

Nessuna stima: misure fatte sul repository con uno spike poi rimosso.

| Verifica | Esito | Perché conta |
|---|---|---|
| Gli E2E girano già su un build **debug** | ✅ `cmd_server`: `if test_mode: debug_mode = True` | **Nessuna modifica al build**: sourcemap e codice non minificato ci sono già |
| Sourcemap risalgono ai `.svelte` | ✅ 83 map, **196/199** componenti raggiungibili | Condizione necessaria di tutto il livello B |
| V8 coverage sul build servito | ✅ 12 script su 14 con sourcemap utilizzabile | La raccolta funziona |
| Entrambi i progetti Playwright sono Chromium | ✅ `desktop` + `mobile` | `page.coverage` è Chromium-only: qui non è un limite |
| Esecuzione sequenziale | ✅ `workers: 1` | Niente contesa in scrittura |

> **La conseguenza più importante**: l'ostacolo che sembrava maggiore — «bisogna far girare gli
> E2E su un artefatto diverso da quello che si spedisce» — **non esiste**.

---

## 3. Architettura

```text
vitest    ──(vitest-monocart-coverage)──▶ coverage-js/unit/<pid>/raw ─┐
                                                                      ├─▶ mcr merge ─▶ combined
Playwright ──(fixture page.coverage)─────▶ coverage-js/e2e/raw       ─┘
```

Un solo ecosistema — [`monocart-coverage-reports`](https://github.com/cenfun/monocart-coverage-reports)
— per entrambi i livelli: è ciò che rende possibile **un report unico** invece di due silos. Il
formato `raw` è il punto d'incontro, lo stesso ruolo che i `.coverage.<pid>` hanno lato Python
prima di `coverage combine`.

### Decisioni di progetto

1. **Fixture manuale, non `monocart-reporter`.** Il reporter sostituirebbe anche il report dei
   test, che oggi è l'HTML di Playwright e funziona.
2. **Nessuna soglia bloccante.** Svelte 5 compila i template in closure: il dato è affidabile su
   «attraversato / non attraversato», meno su «riga X coperta».
3. **`--all src` solo sul report combinato.** Elencare 199 `.svelte` a 0 % nel report unit
   sarebbe rumore; nel combinato è esattamente l'informazione richiesta.
4. **Il valore vive in una globale, non in 77 firme.** I ~77 parametri `coverage: bool` restano
   invariati: una stringa non vuota è vera.

### Schema finale dei report

| Cartella | Misura | Guidato da |
|---|---|---|
| `htmlcov-backend` | Python | test backend |
| `htmlcov-backend-e2e` *(ex `htmlcov-frontend`)* | Python | E2E |
| `htmlcov` | Python combinato | entrambi |
| `frontend/coverage-js/unit-combined` | **JS/Svelte** | vitest |
| `frontend/coverage-js/e2e` | **JS/Svelte** | E2E |
| `frontend/coverage-js/combined` | **JS/Svelte** combinato | entrambi |

---

## 4. Il flag

`--coverage [py|js|all]`, con **`all` come default** quando il valore è omesso, e `all`
interpretato come «tutto il misurabile *in quella suite*»:

| Suite | Cosa raccoglie `all` |
|---|---|
| backend (`api`, `db`, `services`, `schemas`, `utils`, `external`) | solo Python |
| E2E Playwright | Python **+** JS |
| unit vitest | solo JS |

> `./dev.py server --coverage` resta **booleano**: un server può misurare solo Python.

---

## 5. Cosa è stato fatto

### File nuovi

| File | Ruolo |
|---|---|
| `frontend/mcr.shared.js` | Filtri e risoluzione dei sorgenti condivisi dai due livelli |
| `frontend/mcr.config.js` | Livello unit — caricato automaticamente da `vitest-monocart-coverage` |
| `frontend/mcr.e2e.config.js` | Livello E2E — importato esplicitamente dalla fixture |
| `frontend/e2e/fixtures/playwright.ts` | Barrel + fixture di raccolta |
| `frontend/scripts/mcr-generate.js` | Trasforma la cache accumulata in report (non esiste un `mcr generate` da CLI) |
| `mkdocs_src/docs/developer/test-walkthrough/coverage-model.md` | La pagina sui due assi |

### File modificati

`vitest.config.ts`, `package.json`, `playwright.config.ts` (finestra di spegnimento del server),
**64 spec/helper E2E** (import verso il barrel),
`scripts/test_runner/{_common,_frontend_common,_cli,_coverage,_suites}.py`, `dev.py`,
`.gitignore`, tre pagine di documentazione, tre skill.

Più i tre file corretti come conseguenza dei difetti trovati:
`DistributionEditor.svelte`, `routes/(app)/assets/[id]/+page.svelte`, `tx-wac-bulk.spec.ts`.

### Le sei cose andate fuori pista

> **1 — L'accumulo unit non funziona con la cache.** `cleanCache: false` conserva la `.cache` ma
> **non** il risultato: `vitest-monocart-coverage` chiama `generate()` alla fine di **ogni**
> processo, e `generate()` consuma la cache. Con 8 invocazioni l'ottava cancellava le prime sette
> (misurato: 12 file raw → 4). Soluzione: **`outputDir` per processo** + `mcr merge`.
> Sul lato E2E vale l'opposto — la fixture chiama solo `add()`, quindi la cache accumula fra i
> 60+ processi e basta un `generate()` finale. Due strategie opposte, ognuna dal lato da cui il
> vincolo lo consente.

> **2 — Le sourcemap esterne non vengono seguite.** Il primo report E2E era vuoto. I `.map` sono
> serviti correttamente, 66/66 chunk hanno il commento `sourceMappingURL`, e `stopJSCoverage()`
> restituisce `source` per 23/23 entry: **monocart non scarica i `.map` esterni**. L'esempio
> ufficiale funziona solo perché i dev server li incorporano *inline*. Risolto con un
> `sourceMapResolver` che legge le map **da disco** da `frontend/build/_app/…` — da disco e non
> via HTTP perché la generazione avviene **dopo** che Playwright ha spento il test server.

> **3 — Il codice di terze parti non si esclude per prefisso.** Dopo il fix i file erano 106, ma
> **78 erano il runtime di Svelte** (`src/internal/client/…`): le sourcemap npm conservano i
> percorsi *interni al pacchetto*, indistinguibili dai nostri. Il `sourceFilter` è diventato un
> **controllo di esistenza su disco** contro il contenuto reale di `frontend/src`. Da 106 a **26
> file** puliti sul solo caricamento della pagina di login.

> **4 — `nargs='?'` ha rotto una sintassi documentata.** `./dev.py test --coverage api all` — la
> forma che compare **9 volte** nella skill `testing-backend` — veniva letta come «linguaggio
> `api`». argparse **non ha lookahead**. Risolto con `normalize_coverage_argv()`, che inserisce
> `all` quando il token successivo non è un linguaggio valido.

> **5 — E il normalizzatore ha rotto il webServer.** La stessa funzione riscriveva anche la riga
> di comando che Playwright usa per il server, producendo `unrecognized arguments: all`.
> Aggiunta una guardia `only_command="test"`. Morale: un normalizzatore di argv è un'azione a
> distanza, va limitato al sotto-comando che lo richiede.

> **6 — Il primo fix era corretto ma insufficiente, e si è visto solo guardando il database.**
> Dopo aver corretto `addEntry()` la spec falliva ancora **nello stesso punto**. Interrogando
> `backend/data/test/sqlite/app.db` si vedeva però che il dato **era stato salvato**
> (`{"geographic_area": {"distribution": {"AFG": "1.0000"}}}`): funzionava la scrittura, era la
> **rilettura** a mostrare i valori vecchi (vedi il terzo difetto qui sotto). Quando un
> round-trip fallisce, la prima domanda non è «perché non si vede» ma «il dato c'è?»: sono due
> bug distinti e si correggono in due punti distinti.

### I difetti trovati grazie alla coverage

La corsa di riferimento ha prodotto 2 rossi. Entrambi **passano senza `--coverage`**:

| Spec | Con coverage | Senza | Natura |
|---|---|---|---|
| `assets/asset-classification.spec.ts` | 0/3 | **3/3** | **due** difetti di **prodotto** |
| `transactions/tx-wac-bulk.spec.ts` (WB5) | 9/10 | **10/10** | difetto di **test** |

- **`DistributionEditor.addEntry()`** sceglieva la chiave di default da `countries`, popolato
  **asincronamente**. Se il click su «+Add» precedeva la risposta, la chiave era `''` e la riga
  veniva scartata in silenzio. Con il backend rallentato dall'instrumentazione il caso diventa
  sistematico, ma può colpire un utente vero su macchina carica. **Corretto**: `addEntry` attende
  i dati di riferimento e non aggiunge righe senza chiave. Introdotto in `aed456b1` — **non** è
  una regressione di P1/P3.
- **Riapertura della modale su dati stantii** *(emerso solo dopo aver corretto il primo)*. Dopo
  il salvataggio, `handleAssetUpdated()` chiude la modale e **poi** ricarica i dati; il pulsante
  «Modifica» però restava attivo per tutta la ricarica. Chi lo premeva in quella finestra
  riapriva la modale con i valori **pre-salvataggio** — e un salvataggio successivo li avrebbe
  riscritti, annullando la modifica appena fatta. **Corretto** disabilitando il pulsante finché
  la ricarica non è conclusa, con `classificationLoaded` azzerato all'*inizio* di
  `reloadMetadata()` e non a metà (altrimenti la finestra resta aperta durante `loadAssetInfo()`).
- **`tx-wac-bulk` WB5** faceva `allRows.count()` senza attendere il popolamento della tabella.
  **Corretto** con l'attesa mancante.

### Un difetto della macchina di coverage stessa
`playwright.config.ts` mandava SIGTERM al test server e passava a SIGKILL dopo **5 s**. Sotto
`coverage run` il flush del file dati non sempre rientra in quella finestra: quando non ci rientra
l'intera corsa perde la coverage **backend**, senza alcun errore — solo un «No `.coverage.*` files
found» in coda, facile da scambiare per un problema di configurazione. Finestra portata a **30 s**
**solo** quando `COVERAGE_BACKEND` è attivo (fuori dalla coverage non c'è niente da scaricare, e i
5 s restano). Verificato sulla stessa spec: da «nessun dato» a **40,36 %**.

> **Un effetto collaterale inatteso e utile**: girare sotto coverage funziona anche da **prova di
> resistenza in ambiente lento**. Non era fra le motivazioni iniziali del piano, ed è ciò che ha
> fatto emergere entrambi i difetti di prodotto.

### Verifica di non regressione

Le due correzioni di prodotto toccano la pagina di dettaglio asset, che è il punto d'ingresso di
più spec: andava provata, non dedotta. `front-asset all` → **8/8 suite verdi**.

### E quattro test che mentivano

Verificando che le mie modifiche al dettaglio asset non rompessero nulla, `front-utility` è
risultata rossa: **4 fallimenti già presenti**, indipendenti dal mio lavoro. Erano tutti attese
di test rimaste indietro rispetto all'API:

| Test | Cosa era cambiato |
|---|---|
| `country list has ISO codes` | la lista finisce con un'entry «Other» voluta, il cui `iso3` è la stringa `"Other"` |
| `sector list has standard sectors` | `items` è ora una lista di oggetti `{key, emoji}`, non di stringhe |
| `sector list with Other included` | idem |
| `Asset modal currency selector` | `.first()` su `[role="combobox"]` non pescava più il selettore valuta |

Il caso più istruttivo è il quinto, che **passava**: `sector list without Other` asseriva
`not.toContain('Other')` su una lista di oggetti — vero per costruzione, quale che fosse il
contenuto. Un verde che non verificava nulla, cioè esattamente il tipo di punto cieco che questo
piano dovrebbe illuminare. Corretto insieme agli altri: `front-utility` ora **16/16**.

> Un test ancorato a `.first()` o a una forma di payload non dichiarata non fallisce quando il
> prodotto cambia: **smette di misurare**. La coverage non lo segnala — quel codice viene pur
> sempre eseguito.

---

## 6. Rischi e limiti dichiarati

| Rischio | Portata | Mitigazione |
|---|---|---|
| **La coverage cambia i tempi** | ⚠️ Confermato sperimentalmente (vedi sopra) | La corsa con coverage va trattata come ambiente *lento*, non come riferimento |
| **Precisione per-riga su Svelte 5** | I template diventano closure | Nessuna soglia bloccante |
| **2 bundle su 14 senza sourcemap** | Piccola zona cieca (service worker) | Documentata, non risolta |
| **Il service worker non è coperto** | `page.coverage` non vede il contesto del SW | Documentato |
| **Falsa sicurezza** | Trova codice **non eseguito**, non codice **sbagliato** | Vedi sotto |

### L'avvertenza che conta

Sui difetti realmente trovati in P3, la coverage ne avrebbe segnalati circa la metà:

| Difetto | L'avrebbe visto? |
|---|---|
| «Tieni com'è» non azzerava | ✅ ramo mai eseguito |
| Step condizionali | ✅ probabile |
| Ricerca dalla 4ª lettera | ❌ la funzione girava — era sbagliata, non morta |
| Raggruppamento dopo le correzioni | ❌ bug di ordine |
| Dizionario suffissi hard-coded | ❌ scelta di design |

E sui 4 difetti trovati dagli spec dell'altro agente: **nessuno dei quattro** sarebbe stato
segnalato (modale non scrollabile, spec incompleto, dato mancante, flake di attesa).

Conferma sperimentale: la coverage **indirizza** dove guardare, non sostituisce chi guarda. Il
guadagno vero di P3 non è stato un numero di copertura, ma l'aver estratto la logica pura in
moduli `.ts` testabili senza UI.

---

## 7. Cosa resta

- **Prima misura vera**: una corsa `--fresh-run --coverage all all` per avere la fotografia
  iniziale della copertura frontend, da cui far partire il lavoro sui buchi. Non fatta di
  proposito: ha senso solo dopo che l'altro agente ha finito di scrivere i test E2E, altrimenti
  nasce già vecchia.

Tutto il resto del piano è **fatto e verificato**: livelli A e B, unione, CLI, analizzatore dei
buchi, rinomina dei report, documentazione, skill, e i cinque difetti emersi durante la verifica
— tre nel prodotto, due nello strumento di misura stesso.

### Le verifiche che chiudono il piano

| Verifica | Esito |
|---|---|
| `front-fx all` con `--coverage all` — unica suite con vitest **e** Playwright | 8/8, tre report JS |
| `front-asset all` — regressione dei due fix alla pagina di dettaglio | 8/8 |
| `front-utility utilities` | 16/16 |
| `asset-classification` sotto coverage, con dato backend presente | 3/3, 40,36 % |
| `./dev.py front check` | 0 errori, 0 warning |
| `./dev.py mkdocs build` | pulito |

---

## 8. Fase D — l'analizzatore dei buchi, esteso al JS

Un report HTML dice **quanto**. Non dice **cosa vale la pena testare**. Quel lavoro lo faceva già
`scripts/coverage_analysis.py` (544 righe) per il backend: legge la coverage a livello di
funzione, classifica per area e priorità, e separa ciò che è davvero da coprire da ciò che è
inutile coprire (interfacce astratte, metadati dei provider, codice di avvio).

Estenderlo al frontend è costato **un modulo di adattamento**, non una riscrittura:

- `scripts/coverage_js.py` — riconosce il formato istanbul, lo converte nella forma che
  l'analizzatore già capisce, e fornisce le regole di classificazione frontend.
- `coverage_analysis.py` — i due classificatori sono diventati **iniettabili**; il formato è
  riconosciuto dalla forma del file, quindi `--lang` serve solo a scegliere il percorso di
  default. Il percorso Python è invariato (verificato: stesso output di prima).
- `_coverage.py` — i report singoli ora emettono anche `json`, così l'input dell'analizzatore
  esiste sempre senza passaggi manuali.

```bash
./dev.py test coverage-report --lang js --summary
./dev.py test coverage-report --lang js --category js_store
```

Le categorie frontend seguono la struttura reale del progetto: `JS_FEATURE` (`src/lib/features/`
— export AI, wizard di import, raggruppamento asset), `JS_STORE`, `JS_API`, `JS_UTILITY`,
`JS_CHART`, `SVELTE_UI`, `JS_ROUTE`, `JS_ACTION`, più le tre di servizio.

### Due limiti dichiarati, non nascosti

**I componenti Svelte non hanno nomi di funzione.** Il compilatore trasforma il markup in
closure, quindi istanbul restituisce solo `(anonymous_N)`. Invece di fingere, le voci sono
rinominate in `block@142`: la riga è comunque ciò che serve per trovare il codice. I file `.ts`
conservano i nomi veri — ed è per questo che `JS_UTILITY` e `JS_STORE` sono le sezioni più
leggibili e il punto da cui conviene partire.

**Le istruzioni sono attribuite per intervallo di righe.** istanbul non dice quale istruzione
appartiene a quale funzione, quindi una closure annidata viene contata due volte: per sé e per
il genitore. Misurato sui dati reali: 8237 funzioni con contatore a zero contro 7952 allo 0 % di
istruzioni coperte — uno scarto del 3,5 %. Serve a **ordinare** il codice non testato per peso,
non a citare una percentuale.

> **Perché la fedeltà della conversione è stata verificata e non data per buona**: 9354 funzioni
> in ingresso, 9354 in uscita. Un adattatore di formato che perde silenziosamente delle voci
> produrrebbe un rapporto ottimista — esattamente il difetto che questo strumento dovrebbe
> aiutare a trovare.

> **⚠️ Fuori pista 8 — il report combinato conteneva una sola delle due fonti.** Il merge era
> a due passi: prima `unit/*/raw` → `unit-combined`, poi `unit-combined/raw` + `e2e/raw` →
> `combined`. Solo che **`mcr merge` non riemette il report `raw`**: lo chiedevo, non protestava,
> e la cartella semplicemente non nasceva. Il secondo merge leggeva quindi un percorso
> inesistente e produceva un «combinato» fatto di solo E2E.
>
> Passava inosservato perché il report *sembra* giusto: si genera, ha 376 file, le percentuali
> sono plausibili. L'ho visto solo confrontando lo stesso file nei tre report: `EditBuffer.ts`
> stava a **61/74** negli unit e a **0/0** nel combinato — presente unicamente perché `--all`
> elenca i file mai eseguiti. Un file coperto che risultava scoperto.
>
> Corretto passando al merge finale i **raw originali** (`unit/*/raw` + `e2e/raw`) invece
> dell'output intermedio. Controprova: `fxStoreRegistry.ts` passa da 90/174 (unit) e 73/131
> (e2e) a **95/177** nel combinato — più di entrambe, che è ciò che significa unire.
>
> La lezione è la stessa del test che mentiva: uno strumento di misura che **non fallisce**
> quando perde metà dei dati è più pericoloso di uno che si rompe.

---
