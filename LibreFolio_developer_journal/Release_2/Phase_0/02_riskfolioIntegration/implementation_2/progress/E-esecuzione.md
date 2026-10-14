# E — esecuzione · uscita dalla beta

> **Mandato**: round 3, campagna Risk Analysis. Togliere il banner beta da L1/L2/L3 e da
> Asset Global, lasciarlo sul **solo gradino simulazione di L4** (D46 / Q4).
> **Baseline**: `032b86959f783aec6ef784ff565027947435c71d` ✅ verificata con `git rev-parse HEAD`.
> **Corsia**: `--test-port 6174` · `--data-dir /tmp/librefolio-r3-e`.
> **Piano d'analisi approvato dal coordinatore.** Opzione **A** per il testo (raccomandata,
> approvata implicitamente con il piano) — **vetabile**, vedi §Decisioni.

---

## Stato

| # | passo | stato |
|---|---|---|
| 1 | Installare e **misurare** i sei cancelli | ✅ 21 Set |
| 2 | Banner sul gradino simulazione (`L4WhatIf`) | ✅ 21 Set |
| 3 | Via da `RiskPanelHeader` | ✅ 21 Set |
| 4 | Via da `AssetSetRiskPanel` | ✅ 21 Set |
| 5 | Testo i18n × 4 lingue (opzione A) | ✅ 21 Set |
| 6 | Spec: 6 righe riscritte + asserzione nuova | ✅ 21 Set |
| 7 | I sei cancelli contro la baseline misurata | ✅ 21 Set |
| 8 | Browser in italiano, poi spegnere e buttare la corsia | ✅ 21 Set |
| 9 | Handoff + `FROZEN` | ✅ 21 Set |

---

## I cancelli: baseline misurata → esito finale

Tutto **misurato eseguendo**, corsia `6174` / `/tmp/librefolio-r3-e`.

| cancello | briefing 🏷️ | **baseline misurata** | **dopo** |
|---|---|---|---|
| `front check` | 3 ereditati, 0 risk | ✅ **3** — stessi file, stesse righe, 0 risk | ✅ **3**, identici |
| `tsc -p tsconfig.e2e.json` (Ⓘ) | 76 tot · 0 in `e2e/portfolio` | ✅ **76 / 0** | ✅ **76 / 0** |
| `vitest` (suite intera) | 46 in 5 file, 0 risk | 🔴 **41 in 3 file**, 0 risk | ✅ **41 / 3**, identici |
| `prettier --check` | pulito | ✅ pulito | ✅ pulito |
| E2E `front-portfolio risk` | 14 | ✅ **14** | ✅ **14** |
| E2E `front-portfolio risk-lab` | 11 | ✅ **11** | ✅ **11** |
| E2E `front-portfolio risk-asset-detail` | 2 | ✅ **2** | ✅ **2** |

🔴 **Divergenza segnalata (vitest)**: **41 rossi in 3 file**, non 46 in 5. I tre sono
`features/tools/pac-allocator/PacAllocatorTool`, `…/PortfolioRebalancerTool` e
`features/tools/registry`, tutti su `invalid_catalog` del codec dei contratti Tool.
**Zero in un file risk**, prima e dopo. Il numero dopo è **identico** a quello prima: non ho
mosso nulla.

> 🔴 **Il numero era giusto, la mia spiegazione era sbagliata — corretta il 21 Set a valle
> della fusione, dal coordinatore, che ha falsificato la mia ipotesi.**
>
> Avevo proposto che il delta `46 → 41` fosse **la firma di `api sync`**, perché `api sync`
> rigenera i contratti Tool e i tre file rossi falliscono proprio sul codec di quei contratti.
> **Non è così.** Il coordinatore aveva già rigenerato, e un `npm ci` fresco non muoveva il
> numero. La causa vera:
>
> ```
> ENOENT: no such file or directory, open '<worktree>/src/app.css'
> DateRangePicker.test.ts:511   legge src/app.css RELATIVO ALLA CWD
> ```
>
> Invocava `npx --prefix frontend vitest run --root frontend` **dalla radice del worktree**:
> `--prefix` cambia il prefisso di npm, **non la cwd**. Invocato da `frontend/`, come fa
> `dev.py`: **3 file, il mio numero esatto.**
>
> 🔑 **Non uno strumento interrogato male, ma uno strumento interrogato dal posto sbagliato:
> la risposta era corretta e descriveva un mondo in cui chi chiedeva non era.** `ENOENT` non
> mentiva — quel file davvero non esisteva, **da lì**.
>
> ⚠️ **E la lezione per me non è «ho sbagliato la causa», è più stretta**: la mia storia
> causale era credibile **perché puntava a una cosa che avevo davvero fatto**. Avevo eseguito
> `api sync`, avevo visto l'hash dei contratti stampato, e i file rossi erano *quelli dei
> contratti*. Tre fatti veri allineati per coincidenza di tempo.
>
> 🔑 **Una spiegazione che indica una tua azione è più pericolosa di una che non lo fa: sei tu
> a fornirle la plausibilità.** È R2-19 in forma riflessiva — non «un artefatto esiste, quindi
> è usato», ma «*io* ho fatto una cosa, quindi è la causa».
>
> ✅ **Ciò che ha retto è il processo, non l'intuizione**: il numero era etichettato
> **misurato**, la causa etichettata **«sospetto»**, e avevo consegnato il falsificatore
> insieme all'ipotesi (*«se sul tuo albero lo rilanci e scendi a 41/3, è confermato»*).
> **Il coordinatore l'ha eseguito ed è tornato negativo.** Un'ipotesi che viaggia col proprio
> test si lascia uccidere; una che viaggia da sola diventa una riga di documentazione.

📌 **E il `46` non è mai stato il numero di nessuno**: stava nei briefing di A, di B e del
coordinatore come *«baseline ereditata»*, cioè **come un fatto da non riverificare**.
È sopravvissuto perché era scritto, non perché fosse vero.

---

## Analisi (chiusa, approvata)

### I quattro montaggi, verificati contro il codice

| montaggio | pagina | vive? | destino |
|---|---|:--:|---|
| `RiskPanelHeader:77` | Dashboard + Broker Detail | ✅ | ✅ rimosso |
| `AssetSetRiskPanel:276` | Asset Global | ✅ | ✅ rimosso |
| `AssetRiskScenariosView:62` | Asset Detail | ✅ | 🔴 **intatto** |
| `RiskAnalysisPanel:562` | Asset Detail | ❌ **mai** | 🔴 non toccato |

🔑 **`RiskAnalysisPanel:562` non renderizza mai**: è dietro `{#if showBetaBanner}` e il suo
unico consumatore (`AssetRiskScenariosView:89`) passa `showBetaBanner={false}`. Quindi
`toHaveCount(1)` su Asset Detail non osserva un doppio montaggio evitato per fortuna —
**tiene chiusa** una porta che una singola prop può riaprire.

### Il cassetto L4 è chiuso per default ✅

```
RiskLevelSection.svelte   manuallyOpen = $state(false) · open = $derived(!collapsible || manuallyOpen) · {#if open}
RiskLevelsPanel.svelte    <RiskLevelSection level={4} collapsible …>   ← unico collapsible
risk-analysis.spec.ts:1563  await expect(panel.getByTestId('risk-l4')).toHaveCount(0);
```

Il corpo **non è nel DOM** da chiuso. La condizione di stop del briefing non scatta.
**Riconfermato dal vivo**: Dashboard aperta su `?tab=risk` → `betaBanners: 0`,
`l4Open: "false"`, `l4Body: 0`.

### Asset Global: nessun gradino simulazione ✅ (punto 6 confermato **dal vivo**)

```
RiskLevelsPanel:256-266      → replay + shock + simulation   → banner
AssetSetReplaySection:95-99  → replay soltanto               → nessun banner
```

Misurato nel browser con il cassetto L4 di Asset Global **aperto**:
`rungs: ["risk-l4-replay:observed"]`, `hasSimulationRung: false`, `bannersWholePage: 0`.
`{#if simulation}` in `L4WhatIf` è una **garanzia strutturale**, non una convenzione.

---

## Note implementazione

### Passo 1 — installare e misurare

> **⚠️ Fuori pista (trovato prima di iniziare)**: `frontend/node_modules` e `frontend/build`
> **mancavano**. Worktree mai installato. Quindi **nessun cancello frontend era eseguibile**,
> e il primo tentativo l'ha detto nel modo peggiore:
>
> ```
> npx tsc -p tsconfig.e2e.json --noEmit  →  "Use npm install typescript to first add TypeScript"
> grep -c "error TS"                     →  0
> ```
>
> 🔑 **`0 errori` era la risposta giusta alla domanda sbagliata.** Uno strumento assente
> restituisce lo stesso numero di uno strumento verde. È la forma Ⓘ/Ⓛ in una terza veste:
> là il cancello non guardava il file, qui **il cancello non esisteva** e il suo silenzio
> si leggeva come assoluzione.

### 🔴 Ⓠ ha una **terza** ramificazione, e travolge il rimedio del vincolo ①

**Aggiunto il 21 Set alle 23:00**, dopo che il coordinatore mi ha girato la metà trovata da B
(*«`dev.py server` ricostruisce il frontend quando il build manca → senza `node_modules` non
gira nemmeno un test backend che passa dalla rete»*, sintomo:
`ERR_MODULE_NOT_FOUND: Cannot find package 'typescript' … tools-codec-ast.mjs`).

**Verificato sul mio albero**: quello stesso pacchetto mancante rompe anche **`api sync`**.

```
dev.py api sync → npm run generate-api
   → node scripts/tools-fix-main-discriminators.mjs
   → import {fixMainToolDiscriminators} from './tools-codec-ast.mjs'
   → tools-codec-ast.mjs:3   import ts from 'typescript'
```

```
node_modules assente
  ├─→ tsc TACE            (metà mia)      → 0 errori, indistinguibile dal verde
  ├─→ server NON PARTE    (metà di B)     → «Shared backend exited during startup»
  └─→ api sync NON GIRA   (terza, mia)    → generated.ts manca → tsc ACCUSA risk-lab.spec.ts
```

> 🔑 **E la terza è la peggiore delle tre, perché non tace e non si ferma: accusa.**
> Le prime due producono un silenzio o un guasto d'avvio. Questa produce **10 errori
> circostanziati in un file che non hai toccato** — `risk-lab.spec.ts`, di A, non mio.
> *Un cancello che tace lo si impara a non credere; uno che accusa un collega lo si crede.*

🔴 **E il vincolo ① è a valle di sé stesso.** ① prescrive `api sync` *«dopo ogni aggiornamento
di baseline»* come rimedio a un `generated.ts` mancante — **ma `api sync` è esso stesso
downstream dello stesso pacchetto mancante**. Su un worktree fresco, eseguire ① per primo,
come ① letteralmente istruisce, **fallisce con l'errore opaco di B**.

✅ **L'ordine è forzato, e nessuno dei due vincoli lo dice:**

```
npm --prefix frontend ci   →   dev.py api sync   →   qualunque cancello
```

**Tre sintomi, una causa, e nessuno dei tre la nomina.**

> **⚠️ Fuori pista — il vincolo ① era necessario, e senza di esso il cancello Ⓘ mentiva.**
> Dopo `npm ci`, `tsc` dava **97 errori, 10 dei quali in `e2e/portfolio/`** — tutti e 10 in
> `risk-lab.spec.ts`, tutti a cascata da `Cannot find module '../../src/lib/api/generated'`.
> `generated.ts` è in `.gitignore` e **non viaggia col ramo**. Dopo
> `dev.py api sync`: **76 totali, 0 in `e2e/portfolio`** — la baseline del briefing, esatta.
> Senza quel passo avrei attribuito a me stesso 10 rossi di un file che non ho toccato.

> **⚠️ Fuori pista — Ⓚ misurata, e sulla mia corsia non morde. Previsione confermata
> dall'esecuzione.** Sonda `urlopen` nel venv condiviso, prima del build:
>
> | risorsa | `vendor_dir_key` | consumatore | esito |
> |---|---|---|---|
> | `noto-color-emoji` | `fonts` | **frontend** | ✅ 200 OK |
> | `mathjax` | `mkdocs` | mkdocs | 🔴 `CERTIFICATE_VERIFY_FAILED` |
>
> La metà «politica» è **già riparata su questa baseline**: `dev.py:561` chiama
> `update_js_cache(strict=True, required_for="frontend")` e `CONSUMERS` instrada un guasto
> `mkdocs` su `deferred`. **Verificato eseguendo**: il primo E2E ha scaricato i font
> (`22:17:29`, 12 file) e prodotto `frontend/build` (`22:18:42`), è passato verde, e
> `mkdocs_src/docs/javascripts/vendor/` è rimasto **vuoto**.
>
> 🔑 **Un build frontend verde con mathjax assente è la prova del differimento.**
> La causa SSL resta reale ma è confinata a mkdocs: **la metà frontend di Ⓚ è scaduta.**

### Passi 2-4 — i tre montaggi

`L4WhatIf`: banner dentro `{#if simulation}`, **sopra** `risk-l4-model-warning`.
`RiskPanelHeader`: via il blocco, la prop `showBetaBanner` e l'import — **zero chiamanti
espliciti**, verificato con grep su tutto `frontend/src`.
`AssetSetRiskPanel`: via la riga e l'import, nient'altro.

### Passo 6 — le spec, e la falsificazione

> 🔑 **La prova che l'asserzione nuova serviva davvero — misurata, non argomentata.**
>
> Ho rimosso di proposito `<RiskBetaBanner />` da `L4WhatIf` e rilanciato `front-portfolio risk`:
>
> ```
> 1 failed, 13 passed
> ✘ risk-analysis.spec.ts:1556 › level 4 pays for its catalogue once…   at :1614
> ```
>
> **I tre `toHaveCount(0)` che avevo appena scritto sono rimasti verdi con il banner
> cancellato dal prodotto.** Esattamente il buco che il briefing aveva previsto: *«togliere
> da tre posti e non asserire dove è finito significa poter cancellare il banner del tutto
> senza che nulla diventi rosso»*. **Un'assenza non nomina la propria causa.**
>
> Solo la riga nuova l'ha preso. Poi ripristinato dal backup di sessione (**mai
> `git checkout --`**, Ⓟ) e riverificato: **14 passed**.

### 🔴 Passo 8 — un difetto che ho introdotto io, trovato guardando e non testando

> **⚠️ Fuori pista, il più importante del mandato.** `RiskBetaBanner` **non ha un solo
> consumatore**: lo montano anche `AssetRiskScenariosView:62` (Asset Detail) e
> `RiskAnalysisPanel:562`. Riscrivendo `risk.betaBanner.{title,description}` avevo cambiato
> **il testo di Asset Detail** — una pagina che non possiedo, parcheggiata in beta **per
> intero** — facendole dichiarare *«Tutti gli altri livelli sono usciti dalla beta»*.
> Su quella pagina è **falso**: è lei a non esserne uscita.
>
> 🔑 **E nessun cancello poteva vederlo.** Le spec asseriscono la *presenza* del banner, mai
> il testo, perché il testo è tradotto — e la regola che lo vieta è giusta. Quindi i
> **18 test E2E erano verdi** mentre il significato era rotto. *Un'asserzione di presenza non
> è un'asserzione di senso.*
>
> **Riparato restando dentro il perimetro**: `RiskBetaBanner` (mio) prende una prop
> `scope?: 'subsystem' | 'simulation'`, **default `subsystem`**; `L4WhatIf` (mio) passa
> `scope="simulation"`. `AssetRiskScenariosView` **non è stato toccato** e riceve il default.
> I letterali `risk.betaBanner.{title,description}` sono **ripristinati byte-identici**
> (`git diff` → sole aggiunte, 5 righe in più e 1 in meno per la virgola), il testo nuovo vive
> sotto `risk.betaBanner.simulation.*`.
>
> ✅ **E ho reso il difetto assertibile**: `data-scope` sul nodo, e la spec verifica
> `toHaveAttribute('data-scope', 'simulation')`. Un default scambiato diventa rosso invece
> di restare una frase sbagliata in quattro lingue.
>
> 📌 **Verificato dal vivo su entrambe le superfici**:
> Dashboard → L4 → `totalBanners: 1`, `scope: "simulation"`, testo italiano corretto.
> Asset Detail → `?tab=risk` → `banners: 1`, `scope: "subsystem"`, **testo originale**.

### Passo 8 — la superficie, guardata

In **italiano**, corsia `6174`, ordine Ⓓ rispettato (**ripopola → guarda → spegni → butta**):

| superficie | esito |
|---|---|
| Dashboard `?tab=risk`, L4 chiuso | `betaBanners: 0` · `l4Open: false` · `l4Body: 0` |
| Dashboard, L4 aperto | `total: 1` · `inSim: 1` · `inReplay: 0` · `inShock: 0` · `scope: simulation` |
| ordine dentro il gradino | `h4` → `p` → **banner (blu)** → `risk-l4-model-warning` (ambra) → `risk-simulation` |
| Asset Global, L4 aperto | `rungs: [risk-l4-replay:observed]` · `hasSimulationRung: false` · **`banners: 0`** |
| Asset Detail `?tab=risk` | `banners: 1` · `scope: subsystem` · testo originale |

Poi: **server spento** (la connessione aperta è l'atto che scrive, non lo sguardo) e
`/tmp/librefolio-r3-e` **buttata**.

---

## Consegna

| file | |
|---|---|
| `risk/RiskBetaBanner.svelte` | prop `scope`, default `subsystem`, `data-scope` pubblicato |
| `risk/levels/L4WhatIf.svelte` | banner `scope="simulation"` sopra il model warning |
| `risk/levels/RiskPanelHeader.svelte` | via banner, prop e import |
| `risk/AssetSetRiskPanel.svelte` | via banner e import |
| `i18n/{en,it,fr,es}.json` | `risk.betaBanner.simulation.*` aggiunto; i letterali esistenti **invariati** |
| `e2e/portfolio/risk-analysis.spec.ts` | 6 asserzioni riscritte, 4 nuove |

🔴 **`e2e/portfolio/risk-asset-detail.spec.ts` NON è modificato** — `git status` lo conferma.
Le 6 righe di Asset Legacy Detail nelle due copie restano **byte-identiche** fra loro
(`diff` sui due blocchi → identico).

📌 **Nessun file spec nuovo. Conteggi 14 / 11 / 2 invariati. Nulla da registrare nel
catalogo.**

---

## 🔴 Il blocco di B dentro il mio file — verificato, non assunto

**Richiesta del coordinatore, 21 Set ore 22:57**, dopo che **B ha dichiarato** che il proprio
consegnato dipende da `risk-analysis.spec.ts:2111-2121` — il cancello che prova che un codice
d'errore **arriva a schermo tradotto** (`not.toContain('risk.errors.')` con testo non vuoto).
B sta convertendo **110 siti** da un codice che incolpa i dati dell'utente a uno che ammette
un guasto nostro: quelle righe sono l'unica prova che le frasi risultanti **si vedano**
invece di restare chiavi crude.

✅ **Non l'ho toccato. Misurato, non dedotto:**

| verifica | esito |
|---|---|
| le 11 righe, `HEAD:2111-2121` vs `ora:2152-2162` | `diff` → **byte-identico** |
| **l'intero test** che le contiene (90 righe) | `diff` → **byte-identico** |
| spostamento | `+41` righe, **esattamente** quante ne ho aggiunte (2 269 → 2 310) |
| gira e passa? | ✅ `✓ 13 … risk-analysis.spec.ts:2128:5 … never says it in keys (1.3s)` |

🔑 **Le mie sei modifiche stanno tutte prima di riga 1 620**, quindi il blocco di B trasla e
basta. **Ma «traslato» non è una conclusione che si possa trarre dal fatto che non lo si è
mirato**: un `edit` mal ancorato colpisce righe che non si stavano guardando. L'ho quindi
diffato contro `HEAD` invece di dedurlo dall'intenzione.

> 🔑 **E la traslazione da sola non bastava comunque.** `diff` prova che il *testo* non è
> cambiato; **non** prova che il test giri ancora, perché una modifica altrove nel file — una
> parentesi, un `describe` — può romperne l'esecuzione senza toccarne una riga. Per questo le
> due prove sono due: **`diff` per il contenuto, la corsa verde per l'esistenza.**

⚠️ **E c'è una cosa che non trasla, e che B deve sapere**: ho aggiunto tre `toHaveCount(0)`
su `risk-beta-banner` e uno `data-scope`. Nessuno tocca `risk.errors.*` né
`risk-level-1-error`. **Nessun conflitto testuale né semantico previsto con la sua
conversione.** L'unica intersezione fra noi due resta `i18n/*.json`, dove `risk.betaBanner`
(3255) e `risk.errors` (3193) distano 62 righe, e dove **le mie modifiche sono sole
aggiunte annidate** — quindi non spostano le righe su cui lavora lui.

---

## Decisioni — chiuse

1. ✅ **Testo del banner: opzione A, eseguita e fusa.** A nomina il difetto registrato
   (`TODO_FUTURI:1401`); B diceva solo «può cambiare». Motivo di A: quel TODO si dichiara
   *«non blocca il rilascio — la funzione è dietro banner beta»*, quindi **D46 e quel TODO
   si reggono a vicenda**, e un banner che tace il difetto non regge il TODO. Rispetta **Ⓕ**:
   si descrive la *forma* (orizzonte ≫ finestra), mai `+1 400 %` o `−39 %`.
2. ✅ **CHANGELOG — scritto dal coordinatore**, come da sua riserva: un capoverso sotto
   `[Unreleased] → 🔄 Changed` che **nomina il difetto della simulazione con le stesse parole
   del banner** — così chi incontra l'uno non è sorpreso dall'altro — e dichiara
   esplicitamente che Asset Detail tiene il proprio avviso, invece di lasciarlo dedurre
   dall'assenza altrove. ⚠️ `## [1.1.0]` è rilasciato: la sua `### 🧪 Beta` resta storia.
3. ⚪ **`RiskPanelHeader.showActions`** è anch'essa senza chiamanti espliciti. **Non toccata**
   — fuori mandato. Segnalata perché trovata rimuovendo la sua gemella.
4. ⚪ **Il default `subsystem` non è asserito da nessun test.** Proteggerlo richiederebbe di
   editare i due test di Asset Detail — parcheggiati, e in duplice copia. **Non l'ho fatto.**
   Oggi lo protegge il fatto di *essere* il default: nessun chiamante passa uno scope tranne
   `L4WhatIf`.

## Segnalazioni (nessuna azione)

- 🔴 **I due test Asset Detail sono duplicati byte-identici**:
  `risk-analysis.spec.ts:1436-1554` ≡ `risk-asset-detail.spec.ts:47-165` (`diff` → identico).
  Una rete rapida separata è sensata, ma **le copie non sono legate da nulla**: chi modifica
  una lascerà l'altra indietro, e il verde di un selettore parlerà di un file che l'altro non
  ha letto. Non agisco: romperebbe `risk` 14 → 12 e il catalogo è del coordinatore.
- 🔴 **Le asserzioni banner erano 12, non 10** (9 in `risk-analysis`, 3 in `risk-asset-detail`,
  contate con `grep -c`). Errore di somma nel briefing, nessuna riga sfuggita.
- 🟡 **`dev.py server` non accetta `--test-port`**, ma `--port`. Chi copia la forma della
  corsia dal briefing per *guardare* invece che per *testare* sbatte su
  `unrecognized arguments`.
- 🟡 **Il runner difende bene la corsia**: con il mio server manuale su `6174` ha risposto
  *«Test port 6174 is already owned by PID(s) … refusing to reuse or terminate another lane»*
  e si è fermato. **Guardare e testare non possono condividere la porta** — è Ⓓ dal lato
  della porta invece che da quello dei dati.
- 🟡 **Conflitto con B: basso.** `risk.betaBanner` (riga 3255) contro `risk.errors` (3193),
  62 righe di distanza nello stesso oggetto `risk`, identico in tutti e quattro i file. Le mie
  modifiche i18n sono **sole aggiunte annidate**, quindi non spostano le righe di B.
  ⚠️ Dipendenza *semantica*, non testuale: se B introducesse un codice d'errore sul rapporto
  orizzonte/finestra, direbbe la stessa cosa del mio banner in due posti. Da confrontare a valle.

---

## FROZEN

**21 Settembre 2026.** Baseline `032b86959`. Nessun commit, merge, rebase, push, reset o
`checkout --` eseguito dal mandato. Lavoro messo in stage e commesso dal coordinatore.
Corsia `6174` / `/tmp/librefolio-r3-e`: **server spento, cartella dati buttata.**

### Atterraggio

```
c57fc7ef2   feat(risk): take the beta banner off the levels that have left beta   (10 file, +476 / −23)
7d50fe4fe   linea di integrazione, tutto il round 3 dentro
```

Cancelli rimisurati dal coordinatore **sulla revisione fusa**: `front check` 3 ereditati, zero
in un file risk · `tsc e2e` 0 in `e2e/portfolio/` · **14 · 11 · 2** (Asset Detail ferma) ·
`check-orphans` zero orfani · `api risk` 11 · `services risk-all` 441.

⚠️ **Una modifica non commessa resta sopra `c57fc7ef2`**: la correzione qui sopra all'ipotesi
`api sync`, falsificata dopo la fusione. **Riguarda solo questo file**, nessun file di
prodotto. Da mettere in stage al prossimo giro — **o da lasciare, ma non da dimenticare**: una
causa falsificata lasciata in un documento permanente è esattamente il debito che Ⓗ descrive,
e questa volta sarei io a fabbricarlo.

