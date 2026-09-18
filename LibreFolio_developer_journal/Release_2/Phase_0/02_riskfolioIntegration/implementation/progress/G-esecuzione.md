# G — Esecuzione: gerarchia cromatica nei grafici di allocazione

> Piano **vivo**. Il mandato in sola lettura è
> [`../G-frontend-colori-allocazione.md`](../G-frontend-colori-allocazione.md).
> Aggiornato **dopo ogni passo**, non alla fine.

| | |
|---|---|
| Worktree | `LibreFolio-worktrees/e-alfy-solid-couscous` |
| Branch | `e-alfy-risk-g-allocation-colors` ⚠️ rinominato dal runtime (era `e-alfy-solid-couscous`) |
| Baseline | `cc33120ebfbc61efe4c6178218ff8d64dd4adf47` ✅ verificata |
| Lane | porta `6246` · data dir `backend/data/test-risk-g` |
| Autorizzazione | coordinatore, 18 Set 2026 — delega permanente del developer |

---

## Le cinque decisioni ricevute

| # | Verdetto |
|---|---|
| **Tavolozza** | Sfumatura **per colore base**, non per tema: `L<50 → schiarisci, altrimenti scurisci`. ≥50 punti di margine garantiti contro i 17 della regola per tema. Il brief è stato corretto. |
| **G-Q1** | Colore base **per indice** (come oggi). «Stabile per tipo» è funzionalità diversa, non richiesta, e richiederebbe un ponte fra Tailwind ed esadecimale ECharts che invade B. |
| **G-Q2** | `primaryAssetType` su `"Liquidity"`: atteso **verbatim**, conferma da B in arrivo. Non blocca: `resolvePrimary` è iniettato. |
| **G-Q3** | Legenda: **tutte le voci**. Elencare i primari romperebbe il toggle di ECharts, che agisce per nome di serie. |
| **G-Q5** | `_frontend_portfolio.py` **additivo**; `dashboard.spec.ts` +2 righe `__lfChart` **approvato**. |

## I quattro buchi accettati, entrati nella definizione di finito

- **A** — tavolozza dello storico 12 → **14**: `palette[i % 12]` avvolge in silenzio e il
  13° primario prende il colore del 1°, che è la categoria più grande.
- **B** — ordinamento gerarchico **anche** in `AllocationHistoryChart` (`finalizeDataset`):
  con `stack: 'allocation'` l'ordine delle serie **è** l'ordine di impilamento.
- **C** — tutto condizionato a `mode/dimension === 'type'`, con **pin** su `sector`/`geo`:
  `AllocationPieChart` serve anche Asset Detail, che è parcheggiata (D8/D47).
- **D** — sfumatura per colore base (sopra).

---

## Passi

| # | Passo | Stato |
|---|---|---|
| 0 | Apertura piano vivo | ✅ 18 Set 2026 |
| 1 | `hexToHsl` in `colors.ts` + test | ✅ 18 Set 2026 *(test al passo 6)* |
| 2 | `allocationHierarchy.ts` puro + test | ✅ 18 Set 2026 *(test al passo 6)* |
| 3 | Cablaggio `AllocationPieChart` | ✅ 18 Set 2026 |
| 4 | Cablaggio `AllocationHistoryChart` | ✅ 18 Set 2026 |
| 5 | Tooltip con i sottotipi distinti | ✅ 18 Set 2026 |
| 6 | Test unitari + registrazione nel catalogo | ✅ 18 Set 2026 — 68/68 |
| 7 | Statici: lint + `front check` | ✅ 18 Set 2026 |
| 8 | E2E non regressione + `__lfChart` | ✅ 18 Set 2026 — 7/7 |
| 9 | Chiusura: diff backend vuoto, porta libera, handoff | ✅ 18 Set 2026 |

### Passo 0 — Apertura

> **Note implementazione**: verificata la baseline (`cc33120e…`, coincide), letti mandato,
> `README.md` §2.7/§2.8, Q12, D71, D72, D84, istruzioni frontend e la pagina wiki
> `problems/shared-component-option-changed-globally.md`. Analisi consegnata e autorizzata.

> **⚠️ Fuori pista**: al primo controllo `frontend/node_modules` e la cache mathjax
> risultavano **assenti**; non ho installato nulla e l'ho riportato al coordinatore. Sono
> stati seminati subito dopo (635 M + mathjax). Nessuna azione correttiva necessaria.

> **⚠️ Fuori pista**: il runtime dell'app ha **rinominato il branch** prima di qualunque
> scrittura. Il **worktree** non è cambiato. Segnalato e confermato dal coordinatore.

### Passo 1 — `hexToHsl` in `colors.ts`

> **Note implementazione**: aggiunta `hexToHsl(hex): {h,s,l} | null` subito prima di
> `hashString`, come inverso esatto di `hslToHex` (`:123`). Accetta `#rrggbb`, `#rgb` e
> entrambe senza `#`. Restituisce valori **non arrotondati**, così spostare la luminosità
> di un passo frazionario e riconvertire non accumula errore. Su input non esadecimale
> restituisce `null`: né nero né eccezione — un errore di battitura non deve diventare una
> fetta invisibile. Il ramo acromatico (`delta === 0`) copre insieme grigi, bianco e nero,
> dove la formula della saturazione dividerebbe per zero.

### Passo 2 — `allocationHierarchy.ts`

> **Note implementazione**: nuovo modulo **puro** in
> `frontend/src/lib/components/charts/allocationHierarchy.ts`. Nessuna runa, nessuna
> dipendenza da `generated.ts`: `resolvePrimary` è **iniettato**, quindi i test unitari non
> richiedono l'artefatto generato né `_ensure_frontend_build()`.
> Espone `buildAllocationHierarchy()`, `shadeForDepth()` e tre interfacce.
> Algoritmo: raggruppa per `resolvePrimary(key).toUpperCase()` → gruppi ordinati per totale
> (ordinamento **stabile**) → dentro il gruppo il membro **puro** apre la scala → colore base
> `palette[groupIndex % palette.length]`, profondità 0 **verbatim**, il resto sfumato.
> Un membro solo **non** viene mai sfumato: una sfumatura significa qualcosa solo accanto al
> colore da cui deriva.

> **⚠️ Fuori pista — misura che ha ribaltato il brief**. Il brief e Q12 sostenevano
> «`PALETTE_LIGHT` è scura, `PALETTE_DARK` è chiara → sfuma rispetto al tema». Convertendo
> **eseguendo** tutte e quattro le tavolozze in HSL:
> `PIE_LIGHT L 18→67 (8/14 sotto 50)` · `PIE_DARK L 50→82 (0/14)` ·
> `HIST_LIGHT L 18→67 (4/12)` · `HIST_DARK L 50→83 (0/12)`.
> Le tavolozze scure sono davvero uniformemente chiare; **quelle chiare no**: `#1a4031`
> (L=18) è l'eccezione, non il rappresentante, e `#6366f1` è a L=67, più chiaro di metà
> della tavolozza scura. Regola adottata — e accettata dal coordinatore al posto della
> propria: **sfumatura per colore base, allontanandosi dall'estremo più vicino**
> (`L<50 → schiarisci, altrimenti scurisci`). Garantisce ≥ **50** punti di margine su ogni
> voce di tutte e quattro le tavolozze, contro **17** della regola per tema.

> **⚠️ Fuori pista — lavoro rimosso eseguendo la mappa K2 invece di leggerla**. I cinque
> sottotipi hanno **cinque genitori distinti** (`STOCK`, `BOND`, `COMMODITY`,
> `REAL_ESTATE`, `CRYPTO`) ⇒ nessun gruppo supera mai **2** membri ⇒ **un solo livello di
> sfumatura basta** ⇒ **D72 (ciambella a due anelli) non serve** e la trappola del
> percorso rapido a `:193` **non si apre mai**. Inoltre `hslToHex` emette sempre 6 cifre
> (`padStart(2,'0')` per canale), quindi la concatenazione `+ '88'` dello storico **non va
> toccata** — a patto che il colore *puro* resti l'esadecimale originale **verbatim**, mai
> un giro `hex→HSL→hex`.

### Passo 3 — `AllocationPieChart`

> **Note implementazione**: il `.map()` è stato separato in `mappedEntries`; la gerarchia si
> applica **solo** con `mode === 'type'`, altrimenti resta il `.sort((a,b) => b.value - a.value)`
> letterale di prima. Il colore viaggia come `itemStyle` **per singolo dato, dentro
> `chartData`**, quindi il percorso rapido `series: [{data: chartData}]` (`:205`) lo porta
> con sé senza modifiche. `color: palette` a livello di serie è rimasto **intatto**: in
> modalità settore il file è funzionalmente identico a prima.
> Aggiunto `__lfChart` sul contenitore (approvato in G-Q5).

> **Note implementazione (pin legacy)**: con tutti i gruppi singoletti l'output è identico
> **membro per membro** a oggi — il raggruppamento conserva l'ordine di prima apparizione e
> l'ordinamento dei gruppi è stabile, quindi anche i pareggi cadono nello stesso posto.

### Passo 4 — `AllocationHistoryChart`

> **Note implementazione**: tavolozze cresciute **12 → 14**. Le prime 12 voci sono rimaste
> **byte per byte** identiche, quindi ogni grafico con 12 categorie o meno rende esattamente
> come prima.

> **⚠️ Fuori pista — un invariante che il brief non nomina**. Le due tavolozze sono
> **appaiate slot per slot**: slot 0 verde in entrambi i temi, slot 1 blu, slot 2 ambra…
> verificato su tutte e 12 le voci. È ciò che fa sì che una categoria mantenga la propria
> identità quando l'utente cambia tema. Qualunque aggiunta **deve** preservarlo, e questo
> ha deciso quali colori aggiungere. I due nuovi slot sono stati **misurati**, non scelti a
> occhio: il fucsia (~295°) è il varco di tinta più ampio rimasto in **entrambe** le
> tavolozze (distanza 42.9 nella chiara, prima anche nella scura). Quindi
> slot 13 = `#a21caf`/`#e879f9` (fucsia 700/400), slot 14 = `#7e22ce`/`#c084fc`
> (viola 700/400). Il secondo classificato grezzo nella tavolozza chiara era `#0f172a`
> (L=11): **scartato**, avrebbe messo una seconda banda quasi nera accanto a `#1a4031` (L=18).

> **Note implementazione (i quattro punti colore)**: ordine e colore sono ora decisi
> **insieme e una volta sola** in `buildChartOption`, da un unico elenco `styling` che
> alimenta sia le serie sia il tooltip — non possono più divergere. `lineStyle`,
> `areaStyle` (`+ '88'`), `itemStyle` e il colore del tooltip leggono tutti da lì.
> **Deliberatamente non messo in cache** sul dataset: il dataset sopravvive al cambio di
> tema, la tavolozza no. Aggiunto `__lfChart` anche qui.

### Passo 5 — Tooltip

> **Note implementazione**: quando — e **solo** quando — un tipo ha un fratello nel gruppo
> (`groupSize > 1`), la torta aggiunge una riga attenuata `↳ <genitore> <totale>%`. Usa
> l'etichetta `assets.types.<PRIMARIO>` **già esistente**: **nessuna chiave i18n nuova**,
> quindi i quattro cataloghi di traduzione — file condiviso a proprietà rigorosa — non
> vengono toccati. Con un solo membro la riga non compare: ripeterebbe il numero della
> fetta stessa.

### Passo 7 — Statici

> **Note implementazione**: `front check` eseguito **tre volte**, perché la prima lettura era
> inquinata.
>
> | # | Stato albero | Esito |
> |---|---|---|
> | 1 | `generated.ts` **assente** | 285 errori in 72 file |
> | 2 | dopo `api sync` | **2** errori in 4 file |
> | 3 | +shim K2 temporaneo | **0 errori**, 41 warning in 2 file |
>
> Comandi: `PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py api sync`
> poi `… dev.py front check`. Log integrali in `/tmp/libreFolio_front_check_{1,2,3}.log`.
>
> Inoltre: `dev.py lint` → `All checks passed!` · `dev.py front format --check` →
> `All matched files use Prettier code style!`. I 41 warning sono deprecazioni `on:click`
> **preesistenti** in due file che non tocco.

> **⚠️ Fuori pista — i 285 errori non erano miei**. `frontend/src/lib/api/generated.ts` è
> ignorato da git e **assente** da una baseline pulita; `assetTypes.ts:17` esegue
> `schemas.AssetType.options` all'import, quindi la sua assenza rende `any` mezzo progetto.
> 283 dei 285 erano questo. `dev.py api sync` gira **in-process** (`app.openapi()`): niente
> server, niente porta, nessun artefatto tracciato toccato — è esattamente ciò che il
> runner fa da sé prima dei test frontend.

> **Note implementazione — la decisione sull'import K2, validata invece che supposta**.
> Avevo dichiarato in analisi il rischio che l'export mancante producesse una *cascata* che
> annega gli errori veri. **Misurato: non accade.** Esattamente **2** errori, entrambi il
> messaggio pulito e auto-esplicativo
> `Module '"$lib/utils/assetTypes"' has no exported member 'primaryAssetType'`, uno per
> grafico. `allocationHierarchy.ts` e `colors.ts`: **zero**. L'import diretto resta.

> **⚠️ Fuori pista — il rosso rendeva `any` i miei call-site**. Con `primaryAssetType`
> irrisolto, TypeScript **non controlla** gli usi: un errore mio sarebbe stato invisibile
> dietro quello di B. Ho quindi applicato uno **shim temporaneo** con la firma K2 esatta in
> fondo ad `assetTypes.ts`, rieseguito il check → **0 errori**, e poi **ripristinato il file
> dall'originale**, verificando `git diff --stat frontend/src/lib/utils/assetTypes.ts`
> **vuoto**. Il file di B non è stato modificato. Duplicare la sua mappa in modo permanente
> sarebbe stata la divergenza stessa che B sta curando.

### Passo 6 — Catalogo test

> **Note implementazione**: registrazione **puramente additiva** in
> `scripts/test_runner/_frontend_portfolio.py` (condiviso con E ed F, additivo approvato in
> G-Q5): nuova funzione `front_portfolio_allocation_unit` e una riga `add_test` con chiave
> `allocation-unit`. **Nessuna riga esistente toccata.** Sul modello di
> `front_portfolio_store_unit`: niente `_ensure_frontend_build()`, quindi l'azione non
> richiede l'artefatto generato. Le due cartelle `__tests__` di destinazione esistono già.

### Passo 8 — E2E

```
PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py test \
  --test-port 6246 --data-dir backend/data/test-risk-g front-portfolio dashboard
→ 7 passed (16.7s)
```

> **Note implementazione**: nuovo test `dashboard.spec.ts:156` — *«Allocation by type
> carries a per-slice colour derived from its primary type»*. Legge l'opzione ECharts via
> `__lfChart` (una tela non ha DOM su cui asserire un colore) e verifica: tavolozza a
> **14** voci, `itemStyle.color` esadecimale su **ogni** fetta, **nessun colore duplicato**,
> membri di uno stesso primario **contigui**, e il **pin legacy osservato end-to-end**
> (senza sottotipi l'ordine resta per valore decrescente e i colori sono la tavolozza in
> ordine). Diff sullo spec: **+83 −0**, puramente additivo — nessun conflitto testuale con
> E e D.

> **Note implementazione — ho mutato anche il mio test**. Cambiando il gate
> `mode === 'type'` in un valore che non corrisponde mai, il test **5 diventa rosso**
> all'asserzione attesa e gli altri **6 restano verdi**: prova che osserva la mia modifica
> e nient'altro. Log: `/tmp/libreFolio_e2e_mutation.log`. Il test **4** preesistente resta
> **verde** sotto la mutazione — conferma che non copriva i colori, ed è il motivo per cui
> il mio serviva.

> **⚠️ Fuori pista — l'E2E non può girare senza B**. Il build fallisce sull'export
> mancante, quindi ho rieseguito il ciclo shim → esegui → **ripristina**, con
> `git diff --stat frontend/src/lib/utils/assetTypes.ts` **vuoto** a valle. L'evidenza E2E
> è quindi ottenuta **contro una simulazione locale del contratto K2** e **va rieseguita
> dopo la fusione di B**. Dichiarato, non nascosto.

> **⚠️ Fuori pista — una mia svista, riparata**. Un primo edit sullo spec aveva cancellato
> una riga di commento del test vicino. Rilevata subito con
> `git diff -U0 … | grep '^-[^-]'` e ripristinata: il diff finale è **+83 −0**.

### Test unitari — 68 asserzioni, mutation-tested

```
… dev.py test --test-port 6246 --data-dir backend/data/test-risk-g \
  front-portfolio allocation-unit
→ Test Files 2 passed (2) · Tests 68 passed (68)
```

`test-author` non si è fidato del verde al primo colpo e ha **mutato le proprie
asserzioni** per dimostrare che nessuna è a vuoto:

| mutazione | esito | cosa prova |
|---|---|---|
| soglia ΔL 15 → 25 | 11 rossi | il ΔL reale è **esattamente 20.000** su tutte e quattro le tavolozze |
| tolleranza di tinta 1° → 0.0001° | 5 rossi | la deriva reale è 0.048–0.270°, non zero |
| ordine legacy `STOCK,BOND` → `BOND,STOCK` | 1 rosso | il pin legge davvero l'output |
| round-trip ±1 → ≤ −1 | 4 rossi | i cicli sulle tavolozze eseguono; round-trip **esatto** |

> **Note implementazione — ΔL esattamente 20.000 ovunque**: conferma che la regola
> «allontanati dall'estremo più vicino» **non satura mai** su nessuna delle 52 voci delle
> quattro tavolozze. Il `shadeStep = 20` predefinito è realizzato per intero ovunque —
> che è precisamente ciò che la regola per tema *non* garantiva.

> **Note implementazione — ambiguità di contratto risolta a favore del codice**: avevo
> chiesto un test in cui `'Liquidity'` e `'LIQUIDITY'` **non** collidono. Lo specialista ha
> osservato che l'implementazione li **fonde di proposito** (`sameKey()` è insensibile al
> caso proprio per il secchio sintetico) e ha fissato il comportamento documentato invece
> di inseguire la mia formulazione. **Ha ragione lui**: la richiesta era scritta male, il
> codice è corretto. Nessuna modifica.

---

## Raggio d'impatto — chiuso enumerando, non assumendo

`mode` ha default **`'sector'`**. I tre soli call-site di `AllocationPieChart`:

| call-site | `mode` | tocco? |
|---|---|---|
| `AllocationPanel.svelte:117` | `"type"` | ✅ **solo questo** |
| `AllocationPanel.svelte:121` (settore) | default `'sector'` | ❌ intatto |
| `routes/(app)/assets/[id]/+page.svelte:2415` (Asset Detail) | default `'sector'` | ❌ intatto |

Il tab *geo* usa un componente diverso (`GeographyMap`). Lo storico è condizionato a
`dimension === 'type'`. Il precedente `problems/shared-component-option-changed-globally.md`
è quindi neutralizzato **per costruzione**, non per fiducia.

---

## Stato dell'albero

```
 M frontend/e2e/portfolio/dashboard.spec.ts          (+83 −0, puramente additivo)
 M frontend/src/lib/components/charts/AllocationPieChart.svelte
 M frontend/src/lib/components/dashboard/AllocationHistoryChart.svelte
 M frontend/src/lib/utils/colors.ts
 M scripts/test_runner/_frontend_portfolio.py        (additivo)
?? frontend/src/lib/components/charts/allocationHierarchy.ts
?? frontend/src/lib/components/charts/__tests__/allocationHierarchy.test.ts
?? frontend/src/lib/utils/__tests__/colors.test.ts
?? LibreFolio_developer_journal/.../progress/G-esecuzione.md
```

Backend: **nessuna modifica** (`git diff --stat backend/` vuoto).
`git diff --check` pulito · `dev.py lint` → `All checks passed!` ·
`dev.py front format --check` → pulito · `front check` → **2 errori** (solo la dipendenza B).
`lsof -nP -iTCP:6246 -sTCP:LISTEN` → nessun listener.

---

## Due cose che consegno senza averle risolte

1. **Gli screenshot della galleria sono ora stantii.** `e2e/gallery.spec.ts:605`
   (*«dashboard allocation charts — all languages and themes»*) fotografa proprio i colori
   che ho cambiato. **Non li ho rigenerati**: produrrei immagini di uno stato intermedio,
   prima che B fonda. La rigenerazione è di **J**, dopo l'integrazione (D84).

2. **Due PNG non tracciati che non sono miei.**
   `mkdocs_src/docs/static/icons/asset-types/{commodity,real-estate}.png` risultano `??`
   nel mio albero. **Non li ho creati**: hanno il timestamp del seeding e sono
   **byte-identici** (sha256) ai corrispondenti in `frontend/static/`, che sono **tracciati
   dal commit di baseline `cc33120eb`**. Il mirror della documentazione ne traccia **10 su
   12**: i due tipi nuovi non sono nel mirror committato. Non li metto in stage — non sono
   miei. Ma quando B fonderà, la documentazione resterà **senza icona** per `COMMODITY` e
   `REAL_ESTATE`, e **nessun cancello lo rileva**: sono risorse statiche, non collegamenti,
   quindi né `mkdocs build` né `check-links` protestano.

---

## Messaggio di commit proposto

```text
feat(charts): shade asset subtypes inside their primary type's colour

Both allocation charts coloured categories by index, so ETF_STOCK read as
"the fourth thing" rather than as equity. Subtypes now take a lightness-shifted
variant of their primary's palette entry, and sit next to it: on the pie two
similar colours on opposite sides of the circle read as an accident, and on the
stacked history chart the series order IS the stacking order, so shading without
reordering would let the geometry contradict the parentage the colour claims.

Shade direction is chosen per base colour — away from the nearer lightness
extreme — not per theme. Measuring all four palettes shows the light ones are not
uniformly dark (#1a4031 is the outlier at L=18, while #6366f1 sits at L=67), so a
per-theme rule would wash those entries out. The per-colour rule guarantees 50
points of lightness headroom on every entry instead of 17.

Grow the history palette 12 -> 14: there are 13 possible primaries, so
palette[i % 12] wrapped and handed the 13th category the colour of the first —
a silent collision, not a crowded legend. The first 12 entries are unchanged and
the two additions preserve the existing slot-by-slot pairing between the themes.

Gated on mode/dimension === 'type': the sector and geography dimensions share
these components, and the pie also draws the out-of-scope Asset Detail chart.
With no subtype present the output is identical, member for member, to the
previous value-ordered, index-coloured result.

Depends on primaryAssetType (contract K2); front check reports exactly two
errors until it lands.
```

---

## Passo 10 — Riapertura autorizzata dal coordinatore (2026-09-18)

Unica riapertura da stato `FROZEN`, autorizzata esplicitamente e limitata a **due**
modifiche. Nate da un difetto che ho trovato **ritirando una mia chiusura**: avevo
dichiarato chiuso il wrap della tavolozza, e non lo era.

> **⚠️ Fuori pista — avevo chiuso un difetto ancora aperto.** Cresciuta la tavolozza
> 12 → 14, avevo concluso «conto chiuso». Misurando su sollecitazione del
> coordinatore: `SECTOR_KEYS_FALLBACK` ha **14** voci e `portfolio_engine.py:1041`
> inietta `"Liquidity"` **anche in `by_sector`** → **15 chiavi contro 14 colori**.
> Ho portato le collisioni **da 3 a 1, non a zero**. In modalità *tipo* il conto
> chiude davvero (13 ≤ 14); in modalità *settore* no. Il commento che avevo scritto
> descriveva il meccanismo con precisione **e lo dichiarava risolto in una sola
> delle due dimensioni**.

**Note implementazione**:

1. **Commento della tavolozza riscritto** (`AllocationHistoryChart.svelte`). Ora
   dichiara le due cardinalità separatamente (tipo 13, settore 15), la collisione
   superstite, il fatto che *la fetta più piccola veste il colore della più grande*,
   e che **nessun numero è dimostrabile sufficiente** perché `getSectorKeysList()`
   legge lo store API e ripiega sui 14 solo se vuoto. Motivo: una documentazione
   che rassicura a torto è peggio del silenzio.
2. **Avviso di wrap in sola modalità sviluppo**, nei due punti dove calcolo io
   l'indice: `AllocationHistoryChart.svelte` (ramo non gerarchico, il caso vivo) e
   `allocationHierarchy.ts` (ramo gerarchico, latente). Usa `debug.warn` da
   `$lib/debug`, **idioma già esistente nel progetto**, eliminato dal minifier in
   produzione: muto per l'utente, udibile a chi può agire.

> **Scelta di progetto da segnalare**: `debug.warn` invece di `console.warn`
> guardato a mano. Costo: `allocationHierarchy.ts` acquisisce una dipendenza da
> `$lib/debug` (quindi da `import.meta.env`). Resta senza rune, senza `generated.ts`
> e senza il file di B — le proprietà che lo rendono testabile e immune restano
> intatte.

**Verificato che nessun test esercita il wrap** prima di aggiungere l'avviso: tutti
usano `PIE_PALETTE_LIGHT` (14 voci) con pochi ingressi, e il caso `palette: []`
ritorna prima della guardia. Nessun rumore nell'output — confermato dall'esecuzione.

**Evidenza**:

```
front format --check   → segnalava esattamente i miei 2 file; dopo `front format`
                         nessun file estraneo toccato (git status invariato)

PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py test \
  --test-port 6246 --data-dir backend/data/test-risk-g front-portfolio allocation-unit
→ Test Files 2 passed (2) · Tests 68 passed (68)      [zero skipped]

PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py test \
  --test-port 6246 --data-dir backend/data/test-risk-g front-portfolio dashboard
→ 7 passed (16.3s)                                     [zero skipped]

git diff --stat cc33120eb -- frontend/src/lib/utils/assetTypes.ts  → vuoto
grep -c 'primaryAssetType|__K2_PRIMARY' assetTypes.ts              → 0
git diff --check                                                   → pulito
git diff --stat backend/                                           → vuoto
lsof -nP -iTCP:6246 -sTCP:LISTEN                                    → nessun listener
```

> **Nota sull'E2E**: rieseguito con lo shim K2 riscritto con la semantica **corretta**
> (`(type ?? '').trim().toUpperCase()`, vuoto → `OTHER`), dopo la correzione del
> coordinatore. La misura precedente usava la grafia verbatim che mi era stata
> relayata per errore. Shim rimosso e assenza provata, come sopra.

### Debito registrato, NON risolto qui

**Modalità settore: 15 chiavi, 14 colori, 1 collisione viva.** Invisibile ai test
perché richiede un portafoglio con ≥15 bucket di settore simultanei. La cura
concordata è **riusare `shadeForDepth` sullo slot avvolto**, così la collisione
diventa *visibile e distinta* invece che silenziosa — la macchina esiste già ed è
provata. Rinviata a un secondo giro: tocca la modalità settore (che D71 non nomina)
e il grafico a torta (che non ho toccato). Assegnata a G.

### Rimasta senza risposta

La correzione dello **stub K2** in `allocationHierarchy.test.ts:68` — oggi verbatim,
mentre il contratto vero rialza. **Divergenza provata inerte** (il `.toUpperCase()`
a `:140` la assorbe; nessun test esercita `null`/vuoto), ma lo stub è l'unico record
eseguibile di K2 nel repository finché B non atterra, e il suo docstring disinforma.
Correzione pronta, **non applicata**: non autorizzata.

---

## Passo 11 — Stub K2 riallineato al contratto (2026-09-18)

Autorizzato dal coordinatore. Lo stub e il suo docstring ora riproducono la semantica
**reale** di K2: rialza *prima* della ricerca e restituisce il valore normalizzato
**anche quando la ricerca fallisce** (`"Liquidity"` → `"LIQUIDITY"`); solo
`null`/`undefined`/vuoto ripiegano su `OTHER`. Firma allargata a
`string | null | undefined` per combaciare con K2 (assegnabile all'interfaccia, che
chiede `(key: string) => string`).

**Motivo**: finché B non atterra, quello stub è l'**unico record eseguibile** di K2 nel
repository. Un test verde che descrive male il proprio contratto disinforma con più
autorità della prosa.

```
front-portfolio allocation-unit → Test Files 2 passed (2) · Tests 68 passed (68)
front format --check            → All matched files use Prettier code style!
```

**E2E non rieseguito, deliberatamente**: la modifica è confinata in un file di test
unitario e non ha alcuna portata in produzione. L'evidenza E2E del passo 10 resta
valida — ed era già stata raccolta con lo shim dalla semantica corretta.

> **⚠️ Fuori pista — la correzione ha tolto una copertura, e la scoperta vale più
> della correzione.** Non fidandomi del verde l'ho **mutato**: tolto il
> `.toUpperCase()` da `:140` e rieseguito. Atteso un rosso; ottenuti **68 verdi**.
>
> Diagnosi: con lo stub verbatim quel `.toUpperCase()` era **portante nei test**
> (toglierlo li faceva fallire); con lo stub corretto **non lo è più**, perché è il
> contratto stesso a normalizzare. La copertura che ho rimosso era **finta** —
> proteggeva da un ingresso che il contratto vieta.
>
> Ma resta un fatto scomodo: `:140` è oggi una **difesa senza guardia**. Protegge
> da una deriva di K2 (se un giorno smettesse di rialzare) che **nessun test
> rileverebbe**. Non la rimuovo: è difesa vera contro deriva contrattuale.
> **L'invariante giusto — «K2 restituisce sempre maiuscolo» — appartiene al file di
> B** (`assetTypeTables.test.ts`), accanto agli altri suoi. Segnalato al
> coordinatore.

---

## Passo 12 — il commento a `:140`, la difesa dichiarata ✅ 2026-09-18

**Autorizzato dal coordinatore** dopo richiesta esplicita (terzo scongelamento da
`FROZEN`, e ultimo). Superficie: `allocationHierarchy.ts`, cinque righe di commento
sopra `:140`, **zero cambiamenti di comportamento**.

> **Note implementazione**: il passo 11 aveva lasciato `:140` in uno stato che il
> lettore non può decifrare — un `.toUpperCase()` che **sembra portante** e non lo è
> più. Il commento dichiara le tre cose che servono a chi lo trova: (1) è ridondante
> dato il contratto K2, che rialza già *prima* della ricerca e restituisce il
> normalizzato anche al fallimento; (2) è **tenuto apposta** come guardia a costo
> nullo contro una deriva contrattuale; (3) l'invariante che lo renderebbe superfluo
> — *«`primaryAssetType` restituisce sempre maiuscolo»* — **appartiene a K2**, quindi
> va pinnato in `assetTypeTables.test.ts` e non duplicato qui.

**Perché questa modifica da fermo**: è la stessa malattia del passo 11, nella riga
accanto. Lì un docstring verde disinformava sul proprio contratto; qui una riga senza
commento fa **assumere** una copertura che la mutazione del passo 11 ha dimostrato
inesistente. In entrambi i casi il codice afferma, con l'autorità del verde, qualcosa
che non è vero.

```
front-portfolio allocation-unit → Test Files 2 passed (2) · Tests 68 passed (68) · 789ms
front format --check            → All matched files use Prettier code style!
```

**E2E non rieseguito, deliberatamente**: modifica di solo commento, portata nulla in
produzione, nessun byte di comportamento toccato.

> **📌 Instradato a B, non implementato qui.** Due asserzioni in
> `assetTypeTables.test.ts`: *l'uscita è sempre `=== output.toUpperCase()`* e
> *`null`/`undefined`/`''` → `OTHER`*. Chiudono la deriva **dove nasce**, per tutti i
> consumatori. Scriverle da me sarebbe stato il secondo guardiano della stessa
> proprietà, nel posto sbagliato.

---

## FROZEN

Nessuna ulteriore modifica, esecuzione, server o operazione Git da parte mia.

**Debito registrato, mio, secondo giro** — non parte di questo mandato:

1. **Il perimetro della modalità settore.** `SECTOR_KEYS_FALLBACK` ha **14** voci più
   `"Liquidity"`, iniettata in `by_sector` da `portfolio_engine.py:1041` → **15 chiavi
   contro 14 colori**. La crescita 12 → 14 ha portato le collisioni **da 3 a 1, non a
   zero**. Invisibile ai test: serve un portafoglio con **≥15 bucket di settore
   simultanei**, plausibile per un utente vero e mai nelle fixture. E nessun numero è
   dimostrabile sufficiente, perché `getSectorKeysList()` legge lo store API e ripiega
   sui 14 **solo se vuoto**.
2. **La cura: `shadeForDepth` sullo slot avvolto.** La quindicesima riceve una
   *sfumatura* dello slot 0 invece di una copia identica → la collisione diventa
   **visibile e distinta invece che silenziosa**. Cura il meccanismo invece del caso,
   e la macchina è già scritta e provata (52 voci, ΔL misurato, mai satura).
   ❌ Il cancello `palette.length ≥ fallback + 1` **non** va prima della cura: sarebbe
   rosso oggi (14 ≥ 15 è falso), e un cancello rosso che nessuno può chiudere viene
   aggirato.
3. **Il ripiego silenzioso dentro il motore stesso** — `allocationHierarchy.ts:109`.

   ```ts
   const hsl = hexToHsl(base);
   if (!hsl) return base;      // ← padre e figlio dello stesso colore
   ```

   Se un letterale di tavolozza smette di essere esadecimale, `shadeForDepth`
   restituisce la base: padre e figlio identici, cioè **D71 — il difetto che questo
   mandato ripara — reintrodotto dal suo stesso motore**. Tre qualificazioni, tutte
   necessarie per valutarlo:

   - **raggiungibile** solo se un letterale smette di essere esadecimale — dato di
     modulo, **non varia a runtime**;
   - **coperto** su tutti e **28** gli slot (14 × 2 temi) **da un test, non da un
     cancello**: il pavimento ΔL va rosso perché misura un *numero* sull'uscita;
   - **difendibile**: in un render di grafico, restituire la base è meglio che
     sollevare.

   > **Come è stato trovato**, perché dice a chi lo raccoglie come cercarne altri:
   > *«Mi avevano avvisato di non **consumare** un ripiego silenzioso altrui. La
   > misura ne ha trovato uno **mio**, cinque righe sopra il punto che stavo
   > controllando.»*

   Stessa famiglia dei punti 1 e 2, stessa cura: **rendere udibile ciò che oggi tace.**
   Registrato anche dal coordinatore come **D197** in
   `04-decisioni-e-questioni-aperte.md` — ma quello è l'indice della campagna, **questo
   è il punto di ripristino del lavoro**: chi riprende i colori dell'allocazione rilegge
   qui.
