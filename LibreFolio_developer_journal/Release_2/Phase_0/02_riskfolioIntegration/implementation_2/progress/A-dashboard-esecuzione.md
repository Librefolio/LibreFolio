# A — Rischio Dashboard · piano vivo del giro UI rischio (Release 2)

> **Segue** [`A-postmerge-esecuzione.md`](./A-postmerge-esecuzione.md) (livelli di Asset Global, integrati
> in `dev_release2` a `f45f0fb4d`).
> **Mandato**: A — il pannello rischio di **Dashboard e Broker Detail** (`levels/*`), insieme al developer.
> **Coordina il giro**: Risk (sessione `0000738d-b7e0-4561-9454-cf5ab2c439ca`). I checkpoint passano da lui.
> **Schede della review**: [`../R5-tempo2-schede.md`](../R5-tempo2-schede.md) (di Risk).
> **Corsie**: suite `6153` · `/tmp/librefolio-r2-a` — copia di prod `6163` · `/tmp/librefolio-r2-a-prodcopy`.

---

## Perimetro (assegnato da Risk, 29/09)

| | file |
|---|---|
| **miei, scrittore unico** | `levels/RiskLevelsPanel.svelte`, `RiskPanelHeader`, `RiskPartialNotice`, `L1HowMuchItHurts` + `levels/l1/*`, `L2Diversification`, `L3Benchmark`, `L3RiskAdjusted` + `l3Helpers`, `l4/L4Shock`, `l4/L4Simulation`, `SimulationProvenance`, `simulationModes`, `driftUncertainty` · `ui/display/RiskMetricCard` + `RiskCardGrid` (usati solo da L1–L3) · E2E `risk-analysis.spec.ts` (meno i test del replay) · chiavi `risk.levels.*` (meno `l4.replay*`) e `risk.analytics.*` |
| **condivisi, miei** | `charts/ScatterChart.svelte` + `scatterChartHelpers.ts` — li usa anche il lab: ricontrollarlo dopo ogni modifica |
| **di F** | la matrice (`CorrelationHeatmap`, `CorrelationPairsList`, `correlationHelpers`) |
| **di Risk** | la cornice e le primitive (`RiskLevelSection`, `levelHelpers`, `warningSentence`, `partialNotice`, `riskPanelController`, `lib/risk/*`) · il replay (`L4Replay`, `scenarioHelpers`, `TornadoChart`, `L4WhatIf`, `RiskBetaBanner`) |
| **fuori dal giro** | `ui/display/KpiDivergingFlowBar.svelte` — lo usa anche il KPI della Dashboard; backlog del coordinator |

**Regola**: le richieste sui miei file le prendo e le faccio; tutto ciò che tocca un pezzo in comune o un file
non mio passa **prima** da Risk. Il via per il codice lo dà il developer.

---

## Il lavoro

| # | voce | stato |
|---:|---|---|
| V1 | **l'avviso unico dei parziali**: tono per causa, badge degli asset, niente lista dei nomi tecnici | 🔶 tono ✅ · «causa → effetto» ✅ (passo 6) · **badge e frase breve** aspettano `AssetChip` di F |
| V1b | **la frase sotto lo scatter di L3** che chiama «liquidità» gli asset senza prezzo | ✅ (passi 1 e 4) |
| V2 | tooltip vero sulle barre dell'istogramma di L1 | ⏳ |
| V3 | aspetto delle card L1–L3: niente troncamenti, `Tooltip` al posto del `title` nativo | ⏳ |
| V4 | ordinamenti per tipo/settore/area nella matrice di L2 | ⏳ aspetta il helper condiviso di F |
| V5 | icone del manuale su L1–L4, come nel lab | ✅ (passo 3) |
| V6 | spazio vuoto a sinistra dello scatter (`scatterChartHelpers.ts:208`) | ⏳ |
| F2b | L3 dichiara i risultati `current_composition` che legge | ✅ (passo 6) |
| M16 | la scheda «non misurato» di L2 non ha un test che ne fissi l'assenza | ✅ T2 (passo 5) |
| — | didascalia di L2 con `.unpriced` e `.cash`, e l'icona `#excluded-weight` sulla scheda | ⏳ proposta di forma al developer |
| — | dove stanno gli avvisi di L4 | decisione del developer |

---

## V1 — perché tutti i risultati erano «parziali», misurato · 29/09

> Domanda del developer: *«in teoria tutti gli asset sono pieni di dati, perché compaiono questi avvisi?»*

**Una causa sola, permanente.** Due crowdfunding senza **nessuna fonte di prezzo e nessun prezzo**
(`missing_price` allora) venivano esclusi dalla preparazione. L'esclusione è **una per richiesta**
(`backend/app/services/risk/service.py:928`, `context.excluded_assets`), quindi ogni risultato della stessa
richiesta diventava `partial`. La lista dei sette nomi diceva «tutti», per la stessa ragione.

**Due reperti per Risk, confermati da lui nel codice e riparati nel suo backend:**
1. i risultati calcolati sulla sola serie TWRR (KPI, VaR, drawdown, confronto) erano «parziali» **senza aver
   perso niente**: il motore valuta quegli asset ogni giorno all'ultimo prezzo di transazione
   (`portfolio_engine.py:1372-1384`, `LAST_TRADE_PRICE`);
2. nella composizione attuale il peso degli asset senza serie finiva in `cash_weight`, cioè era chiamato
   **liquidità** mentre la liquidità reale del developer è zero (candidato F2 del 23/09).

> 🔒 **Le percentuali personali** misurate quel giorno sono state riferite al developer e a Risk, e
> **non** si registrano qui (dati personali; vincolo Ⓕ).

**Decisioni del developer, 29/09**: tono **informativo** se la causa è permanente, **ambra** se è
occasionale · «parziale» solo dove il numero ha perso qualcosa · asset senza prezzo nominati separati dalla
liquidità, con i numeri invariati · badge come nel lab.

> **⚠️ Fuori pista — avevo proposto come strada principale un calcolo nel frontend.** Per distinguere
> permanente da occasionale avevo suggerito di dedurlo da `provider_code` dello store. Risk l'ha fermato:
> è un calcolo, e i calcoli stanno nel backend. Ora la distinzione è il motivo `no_price_source` del
> backend (`7840fa7df`); il frontend legge il codice e basta.

---

## Contratto concordato con Risk (29/09)

**Già nel mio albero a `7840fa7df`** (commit del developer, avanzamento pulito):
- `excluded_weight` su `RiskContributionOutput` (`schemas/risk.py:829`) e `RiskReturnOutput` (`:868`):
  somma dei pesi degli asset senza serie. `cash_weight` **invariato**, resta il residuo a rendimento zero
  (liquidità + in transito + esclusi); la liquidità vera è `cash_weight − excluded_weight`.
- motivo `no_price_source` nel `details.reason` dell'avviso `assets_excluded` e in
  `metadata.excluded_assets[].reason`; chiave `risk.warnings.assets_excluded_no_price_source`.

**In arrivo nel checkpoint di Risk**, con i suoi test:
- `ResultReason.reason?: string`, da `warning.details.reason`; assente se manca, **tolto** sulle voci fuse
  con motivi diversi → nella mia regola **solo `no_price_source` esplicito è permanente, altrimenti ambra**;
- `uncoveredWeight()` → `{total, unpriced, cash} | null` (`total` = `cash_weight` esatto);
- la riga `L2Diversification.svelte:87` la scrive Risk (`?.total ?? null`), **con il mio OK**.
  🔴 **Corretto 29/09 dal coordinator**: fino a quando il checkpoint di Risk non è arrivato nel mio ramo,
  **`L2Diversification.svelte` non si tocca in nessuna riga** — un solo scrittore per file. Quindi anche
  l'icona `#excluded-weight` sulla card di L2 aspetta, insieme alla didascalia.

> **⚠️ Trappola dei nomi**: `excluded_weight` trovava già 25 occorrenze prima del lavoro di Risk. Erano
> tutte `excluded_weight_total` dell'audit del replay. Si verifica il **nome esatto**, mai la sottostringa.

---

## Esecuzione

### Passo 0 — base e client · ✅ 29/09

> **Note implementazione**: HEAD `7840fa7df` = punta di Risk, avanzamento pulito da `ffe41c5ba`, albero
> pulito. Contratto presente: `excluded_weight:` a `schemas/risk.py:829` e `:868`, `no_price_source` 8
> occorrenze, la chiave i18n in 4 lingue. `api sync` → client 29/09 22:33, 6 occorrenze di
> `excluded_weight` nel client, `git status` vuoto.

### Passo 1 — V1b: la frase sotto lo scatter di L3 · 🔶 29/09

> **Note implementazione**:
> - **Rete prima**: in `l3Helpers.test.ts`, 6 casi nuovi per `uncoveredShares()` più un'asserzione nel
>   caso `null`. **Rossa provata**: `TypeError: uncoveredShares is not a function`.
> - `l3Helpers.ts`: `uncoveredShares()` → `{cash, unpriced} | null`. `cash = max(0, cash_weight −
>   excluded_weight)`; un `excluded_weight` **assente** vale 0 (il `.default(0)` dello schema generato non
>   si applica, perché l'helper legge l'output grezzo con `okOutput`); un `excluded_weight` presente ma
>   inutilizzabile dà `null` invece di chiamare liquidità tutto il residuo. `cashWeight()` resta, con un
>   docstring che avverte che non è «liquidità». **Verde**: `Test Files 1 passed (1)` · 19/19.
> - i18n: `risk.levels.l3.scatter.unpriced` aggiunta con `dev.py i18n add`, 4 lingue; diff `+2/−1` per
>   catalogo (la chiave nuova più la virgola sulla precedente).
> - `L3RiskAdjusted.svelte`: la frase «liquidità» compare solo se `cash > 0`; quella nuova sugli asset
>   senza prezzo solo se `unpriced > 0`; ciascuna ha il suo `data-testid` (`risk-l3-scatter-cash`,
>   `risk-l3-scatter-unpriced`).
> - Sui dati del developer: **prima** «La liquidità (31 %…)», falsa; **dopo** niente frase sulla
>   liquidità (è 0 %) e una frase sulle posizioni senza serie di prezzi.
> - **Verifiche**: `svelte-check` (22:36, client 22:33) → i soliti 3 errori, nessuno in un file risk ·
>   E2E `front-portfolio risk "L3 asks for the risk/return pair"` sulla 6153 → **1 passed** (lo stub ha
>   `cash_weight: 0.05` senza `excluded_weight`: compare la frase liquidità, come prima).
>
> ❌ **Correzione, 29/09**: «il `.default(0)` non si applica perché l'helper legge l'output grezzo» è **falso per
> l'app**. I risultati nello store sono già passati da Zod: Zodios, con `transform` al valore predefinito, sostituisce
> la risposta con l'oggetto validato, quindi `excluded_weight` assente è già 0 prima di arrivare a un helper. Solo le
> fixture dei test unitari sono grezze. La stessa frase sta nel docstring di `uncoveredShares()` e nel commento del
> suo test: spariscono con loro (vedi «Una sola regola per il peso non coperto», sotto).

### Passo 2 — V1: l'avviso · 🔶 29/09

**Decisione del developer**: **un badge per asset**, con icona e nome barrato come nel lab, e **una frase
breve con la sola causa**. I nomi escono dalla frase e diventano badge.

**Cosa serve, chiesto a Risk il 29/09:**
1. `ResultReason.assetIds?: number[]` da `warning.details.asset_ids`, con la stessa regola prudente di
   `reason`: assente sulle voci fuse. Senza, un badge non sa a chi riferirsi, e ricavarli dai nomi nella
   frase sarebbe un'euristica.
2. **La frase breve è mia**: chiavi `risk.levels.notice.excluded.<reason>`, **scritte come letterali, un
   ramo per motivo** (così l'audit i18n le vede). La frase completa di Risk resta come alternativa se
   manca `reason`: un motivo sconosciuto non sparisce mai.
3. **Il badge**: oggi è uno snippet nel file di F (`AssetSetRiskPanel.svelte:554-586`). Riusarlo senza
   copiarlo richiede un componente condiviso: chi lo scrive lo decide Risk con F.

**Adesso, senza aspettare**: la disposizione (due toni, titolo per causa, via la lista dei 7 nomi) e l'icona
del manuale sull'avviso (`#exclusion-reasons`) e sui livelli L1, L3 e L4. Quella di L2 aspetta con
`L2Diversification.svelte`.

> **⚠️ Fuori pista — i test di `uncoveredShares` li ho scritti io, senza una test list approvata.** La
> regola del giro per la UI è sottoporre la test list al developer. Erano 6 casi di un helper puro, in un
> file di test esistente, scritti rossi prima: li dichiaro qui invece di farli passare in silenzio. Per
> l'avviso, che è UI, la test list la sottopongo prima di scriverla.

> 📌 **Nota di progetto sull'icona di L2**: l'icona del **livello** 2 (nell'intestazione della cornice) si
> passa da `RiskLevelsPanel` con `docsPath`, non da `L2Diversification.svelte`. Quella si può fare subito.
> Aspetta solo l'icona `#excluded-weight` sulla **card** «non misurato», che sta dentro `L2Diversification`.

> ⏸️ **Stato dell'avviso**: la parte visibile del ridisegno (tono, titolo per causa, frase breve, badge)
> dipende da tre cose in arrivo: `reason` e `assetIds` dal checkpoint di Risk, e il componente condiviso
> del badge (Risk con F). Finché mancano, l'avviso ricadrebbe sulla frase completa del backend: rifarlo
> ora vorrebbe dire rifarlo due volte nello stesso file.

### Passo 3 — V5: le icone del manuale su L1–L4 · ✅ 29/09

> **Scelta del developer, 29/09**: mentre l'avviso aspetta le sue dipendenze, prima le icone.

> **Note implementazione**:
> - `RiskLevelsPanel.svelte`: `docsPath="financial-theory/technical-analysis/risk-metrics/"` sulle quattro
>   `RiskLevelSection`, **come letterale** (lo scanner di `check-links` legge i letterali, non le espressioni).
>   La cornice (di Risk) le posiziona già: accanto al pulsante su L4, che si chiude. Indice senza ancora:
>   mappatura del coordinator finché l'indice non è tradotto. L'indice esiste in 4 lingue.
> - L'icona del **livello** 2 si passa da `RiskLevelsPanel`, non da `L2Diversification.svelte` (congelato):
>   fatta. Aspetta solo l'icona `#excluded-weight` sulla **card**, dentro L2.
> - **Verifiche**:
>   - `check-links` → exit 0, **83 validi**. ⚠️ *Il conteggio non provava niente*: i miei letterali hanno lo
>     stesso percorso di quelli del lab e il checker li deduplica per percorso. **Prova diretta**:
>     `scripts.docs_links.collect_frontend()` trova **esattamente 4** link con origine
>     `RiskLevelsPanel.svelte` (`:249, :253, :257, :270`), tutti `confident`. Riverificato dopo prettier,
>     che ha spezzato su più righe la sezione L4.
>   - `svelte-check` → i soliti 3 errori, **0** in file risk · `prettier --check` pulito · diff solo sulle
>     mie quattro sezioni più un commento.
>   - E2E `front-portfolio risk` sulla 6153 → **13 passed**, nessuno skipped o fallito.

> **⚠️ Fuori pista — 14 contro 13.** Sul merge validato il 25/09 erano 14; qui 13. **Non è una regressione**:
> lo spec nella base ha 13 `test(` contro 14 (`git show f45f0fb4d:` / `HEAD:`). Uno l'ha tolto Risk,
> `7d6c9a60c test(risk): drop the Asset Global broker test`. Misurato prima di attribuirlo.

### Il badge — il componente e la mappa · 29/09

- **Il componente**: F estrae il chip del lab in `risk/AssetChip.svelte` (suo), varianti `default`/`warning`/
  `excluded`, `help` e `trailing` facoltativi. Arriva con F → Risk → me.
- **La mappa id → nome, icona, tipo, chiesta da Risk: esiste già.** Lo store degli asset carica **tutti** gli
  asset accessibili (`GET /assets/query` senza filtro, `assetStore.ts:8`: quindi anche i crowdfunding), e
  `AssetInfo` ha esattamente `id`, `display_name`, `asset_type`, `icon_url` (i quattro campi del chip).
  `RiskLevelsPanel` usa già `getAssetInfo()` con `$assetStoreVersion` per i nomi (`:196-217`). **Nessuna
  mappa nuova e nessuna richiesta nuova.**

### La regola del tono, fissata con Risk · 29/09 23:30

```ts
tone = reasons.length > 0 && reasons.every((r) => r.reason === 'no_price_source') ? 'info' : 'warning'
```

- **Non serve il campo `code`**: la regola non guarda il tipo della voce. Una voce qualunque senza quel `reason`
  esplicito (dati vecchi, un'altra esclusione, una voce fusa) rende l'avviso ambra. Il prefisso di `key` non si
  legge mai: è un'identità, non un contratto.
- Gli avvisi `data_quality_degraded` hanno `asset_ids` (quindi badge) ma la causa sta in `details.cause`: niente
  `reason` → ambra, correttamente.
- Valori decisi da Risk: `reason` ripulito dagli spazi; `assetIds` tutto o niente; nelle voci fuse gli insiemi
  di asset si confrontano senza badare all'ordine.

> **⚠️ Fuori pista — una duplicazione introdotta da me stasera.** `uncoveredShares()` (`l3Helpers.ts`, per la
> frase di L3) e `uncoveredWeight()` di Risk (`levelHelpers.ts`, per la card di L2) fanno **lo stesso conto**,
> `max(0, cash_weight − excluded_weight)`, su due output diversi. Chiesto a Risk se il suo helper legge l'output
> grezzo, e quindi funziona anche su `RiskReturnOutput`, o lo interpreta con lo schema Zod di `contribution`. Nel
> primo caso L3 userà il suo e il mio va cancellato con i suoi test; nel secondo resta, e la duplicazione è una
> riga. Comportamento identico in ogni caso: un `excluded_weight` assente vale 0 in tutti e due.
>
> ❌ **Correzione, 29/09: l'ultima frase era falsa.** Risk: con `excluded_weight` assente il suo helper restituisce
> `unpriced: null, cash: null` (la divisione non si conosce), e `total` c'è sempre. Il mio invece lo contava 0.
> L'avevo supposto invece di chiederlo.

### Una sola regola per il peso non coperto: si usa quello di Risk · 29/09

**Risposta di Risk**: `uncoveredWeight()` legge l'output **grezzo** (`okOutput()`, poi `finite()` su `cash_weight` ed
`excluded_weight`), senza Zod e senza controllare `kind`: quindi funziona anche su `asset_risk_return`.
**Decisione (mia, su file miei): L3 passa al suo.** Motivi:
- una regola sola per L2 e L3, nel file di chi possiede il contratto;
- la sua è la più prudente: con la divisione sconosciuta non dichiara «tutta liquidità», e questo è proprio il
  principio che abbiamo fissato per la didascalia;
- nel suo checkpoint Risk aggiunge un test che fissa la lettura dell'output di `asset_risk_return` (se un giorno
  qualcuno controlla `kind`, quel test lo ferma) e rinomina il parametro con un nome neutro.

**Da fare nel mio checkpoint, dopo che il suo è arrivato nel mio ramo** (fino ad allora il mio `uncoveredShares()`
resta, altrimenti l'albero non compila):
- `L3RiskAdjusted.svelte`: `uncoveredWeight(riskReturnResult)` da `./levelHelpers`, con le condizioni
  `uncovered?.cash != null && uncovered.cash > 0` e l'equivalente per `unpriced`;
- da cancellare: `uncoveredShares()` più i suoi 6 casi e l'asserzione nel caso `null`; **e anche `cashWeight()`**
  (`l3Helpers.ts:189`) con le sue asserzioni (`l3Helpers.test.ts:140`, `:193`). Dopo il cambio nessuno la importa:
  il grep sul frontend trova solo i suoi test.
- **Divisione sconosciuta** (`unpriced`/`cash` a `null`): nessuna delle due frasi, resta la nota di base.

**Perché nell'app il `null` non arriva mai (misurato nel codice, 29/09):**
- la richiesta passa da `zodiosApi` (`riskStore.svelte.ts:151`), che ha `validate: 'response'`
  (`zodios-client.ts:170`); `transform` resta al valore predefinito `true`, e `@zodios/core` sostituisce la risposta
  con l'oggetto già validato da Zod (`S(e)&&(s.data=r.data)`, dove `S(o)` è `[true, "response", "all"].includes(o)`:
  letto nel sorgente installato, `node_modules/@zodios/core/lib/index.js`);
- **è l'unica strada**: le sole chiamate di produzione a `queryRisk` sono in `riskPanelController.svelte.ts`
  (`:278`, `:280`, `:345`), e l'unica chiamata a `query_risk_api_v1_risk_query_post` è quella di `queryRisk`. La
  cache (`queryCache`, `:153`) tiene in memoria la risposta già interpretata; `localStorage` conserva solo la scelta
  del benchmark (`riskBenchmarkStore`), mai un risultato. Nessun risultato grezzo può quindi rientrare da un
  salvataggio precedente;
- `output` è un `discriminatedUnion('kind')` (`generated.ts:16847`): `RiskReturnOutput` ha
  `excluded_weight: z.number().gte(0).optional().default(0)` (`:16585`). Se manca → 0; se è negativo la risposta
  viene rifiutata con `ZodiosError`.
- Al `null` ci arrivano solo le fixture grezze dei test unitari.

> **⚠️ Fuori pista — un «0 %» dal rumore dei numeri in virgola mobile, trovato scrivendo la risposta.** `max(0, …)`
> taglia solo il rumore **negativo**. Il backend calcola `cash_weight = max(0, 1 − Σ usabili)` (`service.py:832`)
> ed `excluded_weight = Σ esclusi` (`:862`), cioè due somme separate. Simulazione su 100 000 portafogli casuali
> (pesi `v_i/Σv`):
> - senza liquidità, con asset esclusi (il caso del developer): differenza **> 0 nel 28 %** (massimo 2,2e-16),
>   < 0 nel 28 %, = 0 nel 44 %;
> - tutto investito, nessun escluso: `1 − Σ usabili` **> 0 nel 13 %** (massimo 2,2e-16).
>
> Con una differenza positiva, `cash` vale circa 1e-16 e la frase di L3 dice «0 % in liquidità». Era già vero
> **prima** del mio lavoro, con il vecchio `cashWeight() > 0` su un portafoglio tutto investito. **Proposto a Risk**:
> una tolleranza assoluta (`1e-9`) su `cash` dentro `uncoveredWeight()`, con tre test (rumore positivo, residuo
> tutto rumore, liquidità vera piccola che resta). Se non la vuole, la metto io nella visualizzazione di L2 e L3.
>
> ✅ **Accettata da Risk (29/09 23:36), nel suo checkpoint.** La soglia è **`1e-9`, la stessa che il servizio del
> rischio usa già sui pesi**: verificato, `service.py:515` (`asset_weight > 1 + 1e-9`, la leva) e `:524`
> (`abs(cash_weight − explicit_cash_weight) < 1e-9`, il confronto col residuo in transito). Nel frontend non nasce
> quindi una soglia nuova. Regola: un `cash` sotto `1e-9` vale `+0`, e **sostituisce** anche il taglio del negativo;
> `total` resta esattamente `cash_weight`, `unpriced` non cambia. I tre test li scrive test-author, rossi prima
> tranne l'ultimo, che controlla che la liquidità vera resti: `0.30000000000000004`/`0.3` → `0`;
> `1.1102230246251565e-16`/`0` → `0` con `total` invariato; `0.001`/`0` → `0.001`. Da me, **niente soglia**: L2 e
> L3 leggono `cash > 0` dal suo helper.

**Per la test list da portare al developer** (non ancora scritta):
- **jsdom, nuovo `L2Diversification.test.ts`** (mio; selettore `risk-levels-component`) — **un mutante sopravvissuto,
  trovato da Risk il 29/09 23:42** nella sua passata:
  - **Il mutante**: `?.total ?? 0` al posto di `?? null` sulla riga 87 (la versione che Risk scrive nel suo
    checkpoint). **Sopravvive: 13 E2E su 13 verdi.** Verificato: l'unica asserzione su `risk-l2-uncovered` è la
    presenza con `data-uncovered="0.05"` (`risk-analysis.spec.ts:1143`), e lo stub risponde sempre `ok`. Nessun
    test fissa l'assenza: il buco c'era già prima.
  - **Non è equivalente**: senza un contributo utilizzabile (`null`, `unavailable`, `failed`), `?? 0` mostra la
    scheda e `data-uncovered="0"`, cioè il falso «niente di scoperto» che il commento sopra la riga 87 vieta.
  - **Casi**:
    - presenza, `ok` con `cash_weight: 0.05`: `risk-l2-uncovered` con `data-uncovered="0.05"` e
      `risk-l2-card-uncovered` presenti (proposta di test-author, via Risk);
    - presenza, **`partial`** (aggiunta mia): è il caso reale del developer, contributo parziale per i due
      crowdfunding esclusi. `okOutput` accetta `partial` (`levelHelpers.ts:56`); il test ferma chi condizionasse il
      componente a `status === 'ok'`;
    - assenza, con `contributionResult: null` e con un risultato `unavailable` o `failed` che porta ancora un vecchio
      output: `toHaveCount(0)` su `risk-l2-uncovered`, `risk-l2-card-uncovered` **e `risk-l2-metrics`** (aggiunta
      mia). Senza contributo anche `buildConcentration` è `null` (passa da `okOutput`, `levelHelpers.ts:531-532`),
      quindi la griglia sparisce; con il mutante compare con la sola scheda: un terzo segnale che lo uccide.
      `toHaveCount(0)` e non `not.toBeVisible`, perché il template li toglie con `{#if}` (`:225`, `:252`, `:271`).
  - **Fixture senza ECharts**: `correlationResult: null` (la matrice si monta solo `{#if correlation}`, `:326`) e
    `items: []` (le barre solo `{#if rows.length > 0}`, `:280`, quindi niente `KpiDivergingFlowBar`, fuori giro).
    Restano `RiskCardGrid` e `RiskMetricCard`, già montati in jsdom dai loro test. Harness `$test/component`, come
    `RiskLevelSection.test.ts`.
  - **Rosso**: il test fissa un comportamento già giusto, quindi il rosso si prova sul mutante `?? 0` applicato per
    il tempo della prova.
  - **Catalogo**: `risk-levels-component` elenca i file per nome (`scripts/test_runner/_frontend_portfolio.py:290`):
    un file nuovo non entra da solo. Lo dichiaro nell'handoff; la riga del catalogo non è mia.
  - **Quando**: nel mio checkpoint, insieme alla riga 87 e alla didascalia. Il test fissa il comportamento, non la
    forma della riga. Lo scrive test-author, dopo l'approvazione della lista.
- E2E, `risk-analysis.spec.ts`, test di L3 (mio), **approvato come idea da Risk**: lo stub di `asset_risk_return`
  non ha `excluded_weight`, quindi `risk-l3-scatter-cash` **visibile** e `risk-l3-scatter-unpriced` **assente**
  provano che nell'app il `default(0)` viene applicato davvero. Con l'helper di Risk è una prova piena: senza il
  `default(0)` la divisione non si conosce, e la frase della liquidità sparisce. Oggi il test controlla solo che ci
  sia il `<p>`, che c'è sempre, e il suo commento (`:2229-2233`) dice che la clausola della liquidità non aveva un
  `data-testid`: adesso ce l'ha.
- **Da decidere con il developer (visualizzazione, mio)**: `digits: 0` stampa «0 %» per una quota vera sotto lo
  0,5 %, **in tutte e due le frasi**: una liquidità piccola, ma anche una posizione senza prezzo di peso minimo. Non
  è rumore, è arrotondamento, e la soglia `1e-9` non lo tocca. Si può mostrare un decimale sotto l'1 %, oppure
  accettarlo.

---

### Passo 4 — sulla punta di Risk: L3 sul suo helper · ✅ 30/09

> **Note implementazione**:
> - **Avanzamento verificato da me** (dopo quello di Risk e del coordinator): HEAD `d618e80ed` = `91e91346c` (il
>   checkpoint piccolo di Risk: `reason`, `assetIds`, `uncoveredWeight()` con la tolleranza `1e-9`, la riga 87 di
>   L2) + `d618e80ed` (suo journal). I miei 9 file: `shasum -a 256 -c` sugli hash presi prima del congelamento →
>   **9 OK**; la patch dei file tracciati è **identica byte per byte** (`cmp`). `api sync` non serve: il backend non
>   è cambiato da `7840fa7df` (client del 29/09 22:54).
> - **L3 su `uncoveredWeight()`**: `L3RiskAdjusted.svelte` importa il helper di Risk; `cashShare`/`unpricedShare`
>   valgono `null` se la divisione non si conosce, e allora **nessuna** delle due frasi: resta la nota di base.
> - **Cancellati**, come concordato con Risk: `uncoveredShares()` e `cashWeight()` da `l3Helpers.ts` (−35 righe); dal
>   test, il blocco di `uncoveredShares` (6 casi) e le sue asserzioni nel caso `null`, più le due di `cashWeight`
>   (`:140`, `:193`). Dopo: `l3Helpers.test.ts` differisce dalla base **solo** per quelle (1 riga in più, 4 in meno:
>   import e asserzioni); nessun riferimento rimasto in `src/` ed `e2e/`.
> - **Verifiche**:
>   - `vitest` su `l3Helpers.test.ts` + `levelHelpers.test.ts` → `Test Files 2 passed (2)` · **155** test;
>   - `prettier --check` sui 3 file → pulito;
>   - `front check` (30/09 10:10, client 29/09 22:54) → **i soliti 3 errori** (`TransactionFormModal.test.ts:787,819`,
>     `ToolExecutionMetrics.svelte:44`), **0** in file risk;
>   - E2E `front-portfolio risk "L3 asks for the risk/return pair"` sulla 6153 → **1 passed**; porta libera dopo.

### Test list da far approvare al developer · 30/09

| # | dove | cosa fissa | rosso |
|---|---|---|---|
| **T1** | `RiskPartialNotice.test.ts` (jsdom, già nel selettore `risk-levels-component`) | **il tono**, pubblicato come `data-tone` sulla radice dell'avviso: `info` se **tutte** le voci hanno `reason === 'no_price_source'` (con e senza misure parziali); `warning` se a una voce `no_price_source` se ne aggiunge una con un'altra causa (`missing_price`), o una senza causa (una nota di qualità dei dati); `warning` con misure parziali e nessuna voce; `warning` con sole voci senza causa (le fixture di oggi). Nessuna asserzione esistente cambia | vero: `data-tone` oggi non c'è |
| **T2** | **nuovo** `L2Diversification.test.ts` (jsdom) — M16 | la scheda «non misurato» c'è con un contributo `ok` e con uno `partial` (`data-uncovered="0.05"`); **non c'è** (`toHaveCount(0)` su riga, scheda e griglia) con `null`, `unavailable` e `failed` che portano ancora un vecchio output. Dettagli e perché: sezione «Una sola regola…», sopra | sul mutante `?.total ?? 0`, applicato per la sola prova |
| **T3** | `risk-analysis.spec.ts`, test «L3 asks for the risk/return pair» (E2E) | lo stub ha `cash_weight: 0.05` senza `excluded_weight`: `risk-l3-scatter-cash` **visibile** e `risk-l3-scatter-unpriced` **assente** provano che nell'app il `default(0)` di Zod si applica davvero. Aggiorna il commento `:2229-2233` (la clausola della liquidità ora ha un `data-testid`) | sul mutante che scambia le due quote |
| — | `l3Helpers.test.ts` | **tolti con il codice**: i casi di `uncoveredShares()` e `cashWeight()` (fatto, passo 4) | — |

- **Chi**: test-author, con file distinti, **senza** eseguire suite (la corsia 6153 è mia; le esecuzioni le faccio io,
  una per volta).
- **Catalogo**: T2 è un file nuovo; `risk-levels-component` elenca i file per nome
  (`_frontend_portfolio.py:290`): la riga la aggiunge chi possiede il catalogo. Lo dichiaro nell'handoff.
- **Fuori da questa lista, perché aspettano una decisione di aspetto**: la didascalia di L2 (`.unpriced` e `.cash`),
  il titolo per causa e la frase breve dell'avviso (questa aspetta anche i badge, `AssetChip` di F: senza badge la frase
  breve perderebbe i nomi).

> ✅ **Test list approvata dal developer, 30/09** («Approvata: via con test-author, poi il tono»).

### Passo 5 — T1–T3 scritti, poi il tono dell'avviso · ✅ 30/09

> **Note implementazione**:
> - **test-author** (solo vitest, niente corsia): T1 in `RiskPartialNotice.test.ts` (+67 righe, solo aggiunte: 6 casi
>   e 4 fixture con `key` distinte; una barriera verifica prima che l'avviso contenga tutte le voci e le misure date);
>   T2 nuovo `L2Diversification.test.ts` (106 righe, 5 casi, nessun mock: l'import di `echarts` regge in jsdom); T3 in
>   `risk-analysis.spec.ts` (commento della proprietà 3 dello stub, `:427-434`; paragrafo «no testid» riscritto,
>   `:2237-2240`; due asserzioni con il loro commento, `:2242-2258`). Nessun valore dello stub cambiato.
> - **Rossi**:
>   - T1 vero: `Tests 6 failed | 10 passed (16)`, ogni caso nuovo con `data-tone … Received: null`;
>   - T2 sul mutante `?? 0` della riga 87: `3 failed | 2 passed`, i tre casi di assenza falliscono su tutte e tre le
>     asserzioni (`expect.soft`, primo uso nel repo); ripristino provato (`git diff --quiet` → `REVERTED`, sha256
>     uguale);
>   - T3 sul mutante che scambia le due quote in `L3RiskAdjusted.svelte`, eseguito da me sulla 6153
>     (`/tmp/libreFolio_a_t3_mutant.sh`): **1 failed**, esattamente su `risk-l3-scatter-cash` `toBeVisible`
>     (`:2257`); file ripristinato byte per byte (sha256 `2575cd22d8bf…` prima e dopo).
> - **Il tono** (`RiskPartialNotice.svelte`): `data-tone` sulla radice, `info` se e solo se ci sono voci e **tutte**
>   hanno `reason === 'no_price_source'`, altrimenti `warning`. Blu con l'icona `Info`, come la variante `info` di
>   `InfoBanner`; l'ambra resta con le classi di prima. Gli stessi pesi di colore nei due toni. Titolo, misure e
>   frasi invariati: sono il prossimo argomento con il developer.
> - **Verdi**:
>   - vitest `RiskPartialNotice` + `L2Diversification` + `RiskLevelSection` + `L4Replay` → `Test Files 4 passed (4)`
>     · **33**;
>   - E2E T3 da solo → 1 passed; poi **`front-portfolio risk` intero → 13 passed**, sulla 6153, porta libera dopo;
>   - `front check` (30/09 10:43) → i soliti 3 errori, **0** in file risk · `prettier --check` pulito sui file
>     toccati · `diff --check` pulito.
> - **Da dichiarare nell'handoff**: `L2Diversification.test.ts` va aggiunto al selettore `risk-levels-component`
>   (`_frontend_portfolio.py`, lista file `:167`, `tests=` `:290`), e la sua `desc` può citare la regola del tono. Il
>   mutante **M16** di Risk è ucciso da T2.

> **⚠️ Fuori pista — una discrepanza nelle istruzioni, trovata da test-author.** 
> `.github/instructions/frontend-testing.instructions.md` indica `front_component_unit` in `_frontend_utility.py` come
> posto dei test di componente; quelli dei livelli del rischio stanno invece in `risk-levels-component`
> (`_frontend_portfolio.py`). Non è un mio file: lo segnalo a Risk con l'handoff.

> **⚠️ Da misurare prima di dire al developer «l'avviso diventa blu»**: la regola è `every`. Se sui suoi dati
> contributo e rischio/rendimento portano anche la nota del residuo in transito
> (`zero_risk_residual_includes_in_transit`, senza `reason`), l'avviso **resta ambra**, correttamente secondo la
> regola, ma forse non come il developer se lo aspetta. Risk ha scritto che quella nota c'era sui risultati TWRR dei
> suoi dati: non so se resta su quelli della composizione attuale. Si misura sulla copia di prod (6163), quando il
> developer chiede di vedere.
>
> **Verificato nel codice (30/09)**: la nota **resta** sui risultati della composizione attuale. Il backend la toglie
> solo a chi legge il TWRR da solo (`_COMPOSITION_WARNING_CODES` con `assets_excluded` e la nota del transito,
> `service.py:1143`; `_reads_the_twrr_alone`, `:1146`). E il contributo **entra** nell'avviso
> (`RiskLevelsPanel.svelte:135`). La nota però nasce solo con un valore in transito diverso da zero (`:524`). Sulla
> copia di prod del 29/09 la causa era **una sola** (sezione V1), quindi lì l'avviso dovrebbe essere blu. Sui dati di
> oggi del developer non lo so: l'output della sonda del 29/09 non è salvato. Lo si vede sulla 6163 quando lo chiede.

### Passo 6 — l'avviso «causa → effetto», e F2b · 🔶 30/09

**Scelta del developer (30/09)**: fra «causa → effetto» e l'alternativa minima (solo la lista raggruppata per
livello), **causa → effetto**. Prima, alla domanda «vuoi vedere il tono sulla 6163?», ha risposto «passiamo alla parte
dei risultati parziali»: la 6163 resta spenta.

**Perché oggi non è chiara** (sui suoi dati, dopo il backend di Risk): il titolo dice «Alcuni risultati sono parziali»,
sotto «Correlazione · Contributo al rischio»; non dice cosa manca a quelle misure, dove stanno nella pagina, né che la
causa è la riga sotto. Ed è **incompleta**: lo scatter di L3 e Sortino/Sharpe della composizione attuale perdono le
stesse due posizioni, ma l'avviso non li legge (F2b: `RiskLevelsPanel.svelte:135` passa solo il KPI **storico** a L3,
mentre L3 disegna quello della composizione attuale, scelto da `selectKpiWave`).

**Disposizione**:
1. **Prima la causa, poi l'effetto**: le voci (`risk-partial-reasons`) salgono sopra le misure.
2. **Titolo dalla causa**: tono informativo con misure parziali → chiave nuova `risk.levels.notice.noPriceSourceTitle`
   («Posizioni senza prezzi, escluse da alcune misure»); altrimenti i due titoli di oggi. Nessun conteggio nel titolo:
   i badge diranno quanti.
3. **L'effetto**: `risk.levels.notice.affected` («Misure interessate»), poi un gruppo per livello
   (`risk-partial-level`, `data-level`), intitolato con la domanda del livello, cioè le chiavi già esistenti
   `risk.levels.lN.title`, perché i livelli nella pagina si riconoscono da quella (la cornice non mostra «L2»). Ogni
   misura è un'etichetta (`risk-partial-measurement`, `data-instance`) al posto dei nomi uniti dal punto. Una misura
   senza livello finisce in un gruppo in fondo, **mai persa**.
4. **La mappa istanza → livello** la costruisce `RiskLevelsPanel` (mio) dalle stesse fette dei livelli, nell'ordine
   L1 → L2 → L3: vince il primo che la rivendica (`historical_kpi` storico → L1). I nomi dei livelli sono chiavi
   letterali, un ramo per livello.
5. **F2b**: la fetta di L3 diventa `comparison` + il KPI dell'onda che L3 disegna (`selectKpiWave`) +
   `asset_risk_return` della composizione attuale. Vale per l'avviso, la riga di salute, gli errori e i metadati di L3,
   perché un livello dichiara quello che disegna. Etichetta nuova `risk.levels.l3.rows.kpi` («Sortino, Sharpe e
   volatilità») per il KPI della composizione attuale: il nome di catalogo, «Metriche di rischio storiche», in L3
   sarebbe falso.
   ⚠️ **Effetto visibile**: il piè di L3 descriverà il KPI della composizione attuale invece di quello storico. È una
   correzione, perché descrive quello che L3 mostra, ma cambia.
6. **Invariati**, perché l'E2E li legge: `risk-partial-notice` (`data-partial-count`, `data-tone`),
   `risk-partial-title`, `risk-partial-measurements` (`data-count`), `risk-partial-reasons` (`data-count`),
   `risk-partial-reason` (`data-occurrences`).
7. **Dopo, con `AssetChip` di F**: badge barrati e frase breve per causa, dentro ogni voce.

**Chiavi nuove (4 lingue, solo aggiunte)**: `risk.levels.notice.noPriceSourceTitle`, `risk.levels.notice.affected`,
`risk.levels.l3.rows.kpi`.

**Test list (da approvare)**:

| # | dove | cosa fissa | rosso |
|---|---|---|---|
| **N1a** | `RiskPartialNotice.test.ts` | prima le cause, poi le misure (ordine nel DOM) | vero |
| **N1b** | idem | gruppi per livello nell'ordine 1 → 2 → 3, con `data-level`; il titolo di ogni gruppo è la domanda del livello presa dal catalogo; ogni misura è un'etichetta con il suo nome (etichetta, poi nome di catalogo, poi codice); una misura senza livello resta, in fondo; `data-count` = numero delle misure | vero |
| **N1c** | idem | titolo dalla causa: informativo con misure parziali → il titolo nuovo; informativo senza misure parziali → quello delle note; ambra → come oggi | vero |
| **N1d** | idem | le due chiavi nuove dell'avviso ci sono nei 4 cataloghi, non vuote, senza argomenti, e i tre titoli sono diversi fra loro | vero |
| **N1e** | idem, **riscrittura di un pin di Risk** | «names each measurement by label, by catalogue name, by code»: si leggono le etichette una per una, in ordine, invece del testo unito dal punto | vero (oggi non ci sono etichette) |
| **N2a** | `risk-analysis.spec.ts` (E2E), F2b | lo scatter della composizione attuale torna `partial` → l'avviso lo nomina **nel gruppo di L3** e lo conta in `data-partial-count` | vero (oggi non entra nell'avviso) |
| **N2b** | idem | il KPI della composizione attuale torna `partial` → etichetta con `data-instance="base-current_composition-historical_kpi"` nel gruppo di L3; il KPI storico non compare nel gruppo di L3 | vero |
| — | E2E esistenti dell'avviso (`:1305-1313`, `:1955-1981`) e di L3 (`:1133`, `:1324`) | restano verdi senza modifiche | — |

> ✅ **Test list approvata dal developer (30/09)**, con una richiesta: **vederla con i suoi occhi prima di test-author**.
> Quindi, in questo passo, il codice viene **prima** dei test: i rossi si provano poi **sulla copia di oggi** dei due
> componenti, salvata prima di toccarli (`files/pre-step6/`, sha256 `RiskPartialNotice.svelte` `599fc8ec…`,
> `RiskLevelsPanel.svelte` `98bf45bf…`), messa al posto di quella nuova solo per la prova e poi ripristinata.

> **Risk, 30/09**: OK alla riscrittura del pin, e `RiskPartialNotice.test.ts` **passa a me** insieme al componente
> (un proprietario per file). Tre condizioni per la riscrittura:
> 1. le tre regole del nome (etichetta, nome di catalogo, codice), ciascuna con la sua misura, più un'asserzione che
>    nessuna etichetta sia una chiave;
> 2. `data-count` uguale al numero delle `risk-partial-measurement`;
> 3. rossa sul componente di oggi, e sull'asserzione, non per un errore del test.
>
> **Decisione esplicita** (mia, comunicata a Risk): una misura letta da due livelli si conta una volta
> (`uniqueByInstance`) e si mostra nel gruppo del **primo** livello che la disegna. Con F2b succede solo nel ripiego,
> quando L3 disegna il KPI storico: va in L1.
>
> **Precisione su F2b**, mandata a Risk: la riga di salute di L3 porta solo ciò che non è tornato affatto
> (`levelErrorHealth`, dal 24/09). La prova si divide in due:
> - **N2a** `asset_risk_return` della composizione attuale `partial` → nell'avviso, gruppo di L3, e non nella riga
>   di salute;
> - **N2c** (nuovo) lo stesso `unavailable` → nella riga di salute di L3 (`risk-level-3-health`, `data-count` 1), e
>   non nell'avviso.

> **Note implementazione (passo 6, codice)**:
> - **i18n**: 3 chiavi con `dev.py i18n add`, 4 lingue: `risk.levels.notice.noPriceSourceTitle`,
>   `risk.levels.notice.affected`, `risk.levels.l3.rows.kpi`. **Provato che sono solo aggiunte**: in ogni catalogo le
>   2 righe tolte ricompaiono uguali con la sola virgola in più.
> - `RiskPartialNotice.svelte`: prop `levelOf` (istanza → livello); titolo dalla causa; **prima le voci, poi «Misure
>   interessate»** con un gruppo per livello (`risk-partial-level`, `data-level` 1/2/3, oppure `none` in fondo),
>   intitolato con la domanda del livello (un ramo letterale per livello); ogni misura è un'etichetta
>   (`risk-partial-measurement`, `data-instance`) con i colori del tono. Testid e attributi letti dall'E2E invariati.
> - `RiskLevelsPanel.svelte`: `l1Results` e `l3Results` con un nome; **F2b**: `l3Results = [comparison, KPI dell'onda
>   scelta da selectKpiWave, asset_risk_return della composizione attuale]`, usato per salute, errori, metadati e
>   avviso; `L3_CODES` tolto; l'etichetta `risk.levels.l3.rows.kpi` va sul KPI di L3 solo se non è quello di L1;
>   `levelOf` rivendicato in ordine di pagina, vince il primo.
> - **Verifiche**:
>   - `prettier --write` sui due componenti → invariati;
>   - vitest su 7 file dei livelli → `1 failed | 200 passed`. L'**unico** rosso è il pin che si riscrive (N1e,
>     «names each measurement… joined by ' · '»), atteso;
>   - `front check` (30/09 11:00) → i soliti 3 errori, 0 errori e 0 avvisi nei miei file;
>   - E2E `front-portfolio risk` sulla 6153 → **13 passed**: gli E2E esistenti dell'avviso e di L3 restano verdi
>     con F2b e la forma nuova;
>   - il build servito (`frontend/build`, 30/09 11:01:49) contiene `risk-partial-level`, «Misure interessate», il
>     titolo nuovo e `data-tone`.

> **Server per il developer, 30/09 11:05**:
> - copia **rinfrescata dalla snapshot** (`/tmp/libreFolio_a_prodcopy_refresh.sh`): snapshot senza marcatore, app.db
>   `5c0a681bc4e4b59c`, 71 file; copia identica, `004_release_1_2_0_schema`, scrivibile, senza marcatore; la
>   precedente in `…prodcopy.prev-20260930-110318`;
> - **impronta presa prima dell'avvio** (`files/prodcopy-fingerprint-20260930.txt`): 1 utente, 15 asset, conteggi dei
>   prezzi per asset **identici** a quelli del 25/09;
> - `dev.py server --test --port 6163 --data-dir /tmp/librefolio-r2-a-prodcopy`, **staccato**, di proposito →
>   HTTP 200 dopo ~10 s; il log dichiara `db_path /private/tmp/librefolio-r2-a-prodcopy/sqlite/app.db`, 15 tabelle,
>   schema aggiornato. **Resta mio**: lo spengo e provo la porta libera quando il developer ha finito.
>
> ⚠️ **Fuori pista — il mio primo script di rinfresco è uscito con un errore dopo la copia**: nei conteggi di
> controllo avevo supposto nomi di tabella (`asset`, `user`) che non esistono (`assets`, `users`). La copia era già
> fatta e giusta: hash uguale alla snapshot, 71 file, `004`. I controlli li ho rifatti a parte con i nomi veri.
> Nessun dato toccato oltre alla copia.

> ✅ **Visto dal developer sulla 6163 (30/09)**: «Va bene così: via con test-author». Server **spento subito dopo**
> (`stop_bash`, 6163 e 6153 provate libere): gli E2E ricostruiscono lo stesso `frontend/build` che la 6163 serve, e la
> prova del rosso lo avrebbe ricostruito con il pannello vecchio. Si riaccende quando il developer chiede.

### Passo 6 — i test N1–N2 · ✅ 30/09

> **Note implementazione**:
> - **test-author** (solo vitest): `RiskPartialNotice.test.ts` → **418 righe, 27 casi** (16 di prima + 11 nuovi), con
>   N1a–N1d e **N1e riscritto** secondo le tre condizioni di Risk. Il pin legge un'etichetta alla volta con
>   `queryAllByTestId` + `expect` (rosso su un'asserzione, non su un errore) e asserisce che nessuna etichetta sia una
>   chiave né il testo restituito tale e quale. `risk-analysis.spec.ts`: opzione dello stub **`instanceStatus`** (per
>   istanza, perché `historical_kpi` c'è in tutte e due le onde; se è assente il payload resta identico byte per byte;
>   `unavailable` porta `output: null` e un `error` con un codice valido), e un `describe` con **N2a, N2b, N2c**.
> - **Rossi**:
>   - N1 sulla copia di oggi del componente (`pre-step6`, `599fc8ec…`) → **5 failed | 22 passed**, tutti su
>     asserzioni: N1e, N1a, N1b ×2, N1c (informativo con parziali). Ripristino provato: `e7ef59d5…` → `RESTORED`;
>   - N2 sul pannello di prima di F2b (`pre-step6`, `98bf45bf…`), eseguiti da me sulla 6153
>     (`/tmp/libreFolio_a_n2_red.sh`) → **3 failed**, ciascuno sull'asserzione di F2b e **dopo** le sue barriere:
>     l'etichetta dello scatter nel gruppo di L3 (`:2343`), quella del KPI della composizione attuale (`:2369`), la riga
>     di salute di L3 (`:2394`). Ripristino provato: `1a37ddf0…` → `RESTORED`.
> - **Verdi**:
>   - E2E `front-portfolio risk` intero → **16 passed** (13 + 3), due volte: prima del rosso, e dopo, anche per
>     ricostruire `frontend/build` con il codice di oggi (il build contiene `risk.levels.l3.rows.kpi`, che esiste solo
>     nel pannello nuovo);
>   - vitest su 7 file dei livelli → `Test Files 7 passed (7)` · **212**;
>   - `front check` (30/09 11:32) → i soliti 3 errori, 0 in file risk;
>   - `i18n audit` → **3487 chiavi, tutte complete**, e nessuna delle mie 4 chiavi nuove fra le «potentially unused»;
>   - `prettier --check` pulito sugli 8 file toccati · `diff --check` pulito.
>   - Gli spec E2E **non passano da un controllo dei tipi**: `tsconfig.json` esclude `e2e/**/*`, e Playwright
>     traspila senza controllare. Per loro la prova è l'esecuzione.

> **Rilievi di test-author, da non perdere (non corretti ora: non sono di questo passo)**:
> - **citazione vecchia** `schemas/risk.py:1056` per il contratto «`unavailable`/`failed` senza output»: oggi è
>   `RiskAnalyticResult.validate_status_payload` (`:1620`). Compare nel docstring di `RiskLevelsPanel.svelte` e nei
>   commenti dello spec E2E (tutti e due miei): **da correggere in un passo di pulizia**;
> - **descrizione vecchia nel catalogo**: `risk-levels-component` (`_frontend_portfolio.py:290`) dice ancora «joined by a
>   middle dot». **Da dichiarare nell'handoff**, insieme a `L2Diversification.test.ts` da aggiungere e alla regola del
>   tono da citare;
> - **copertura**: la riga «Misure interessate» (`risk.levels.notice.affected`) è verificata solo nei cataloghi; nessun
>   test prova che sia disegnata. Non era nella lista approvata: la propongo al developer insieme alla prossima lista.

### Passo 7 — i tre link del manuale che `check-links` non vedeva, in L1 · ✅ 30/09

> **Reperto di F, controllato da Risk (30/09)**: in `L1HowMuchItHurts.svelte` lo snippet `measure` riceve il percorso come
> argomento posizionale, e le tre misure di coda (`worst-realization`, `drawdown-at-risk`,
> `conditional-drawdown-at-risk`) non avevano una forma che il gate legga.

> **Note implementazione**:
> - **Misurato prima**: `collect_frontend()` vedeva in questo file 4 link (3 via `DOC_PATHS` e `current-drawdown`) più
>   `{docsPath}` a runtime (la definizione dello snippet). **Le tre pagine di coda non comparivano affatto.**
> - **Rimedio senza cambiare il DOM**: `TAIL_DOCS`, con i tre percorsi sotto una chiave `docsPath` (la forma che il gate
>   legge, la stessa dei descrittori del progetto); le tre chiamate passano `TAIL_DOCS.<misura>.docsPath`. Snippet,
>   `href` e testid invariati.
> - **Verifiche**:
>   - `collect_frontend()` → le tre pagine come link `confident` (`:128-130`); resta solo `{docsPath}` a `:139`, cioè la
>     definizione dello snippet, correttamente a runtime;
>   - `dev.py mkdocs check-links` → exit 0, **86 validi** (erano 83: +3, quindi viste davvero e non assorbite nella
>     deduplica), le tre elencate `✅` (righe 20–22 del log);
>   - `front check` → i soliti 3 errori · `prettier --check` pulito · E2E `front-portfolio risk` sulla 6153 → **16
>     passed**, porta libera dopo.

> **⚠️ Fuori pista — il gate legge anche i commenti, e il mio commento era diventato un link.** Nel docstring avevo
> scritto «\`docsPath:\` entries because that is the form \`check-links\`…». La regex `docsPath\s*[:=]\s*\`…\``
> l'ha preso come percorso («entries because that is the form »): sarebbe stato un **falso link rotto**. Visto nella
> scansione diretta, prima di lanciare il gate, e riscritto («under a \`docsPath\` key»). Lezione: in un file che il gate
> legge, un commento non deve contenere `docsPath:` o `docsPath=` seguiti da un testo fra apici.

> **Nota di prettier**: va lanciato **da `frontend/`**. Dalla radice non trova `prettier-plugin-svelte` («Cannot find
> package»). Non era un errore del file.

> ⏸️ **30/09 11:52 — PAUSA del venv condiviso** (coordinator): il developer lancia `pipenv update
> borsa-italiana-scraping` nel worktree di K. Risposto **FROZEN** dopo aver verificato: nessuna shell attiva, 6153 e
> 6163 libere, nessun processo python/pipenv/uvicorn del mio worktree o delle mie corsie. **Nessun comando `dev.py`
> fino al RESUME**; le modifiche al frontend sono consentite.
> ▶️ **30/09 12:04 — RESUME** (coordinator): venv condiviso aggiornato e verificato, cambiato solo
> `borsa-italiana-scraping` 0.3.1 → 0.3.2, con le stesse dipendenze. Comandi Python di nuovo consentiti.

> ⏸️ **30/09 12:12 — PAUSA del venv, secondo giro** (coordinator): `pipenv update` al posto della modifica a mano;
> cambiano borsa, `idna` e `soupsieve`. **FROZEN** dopo la verifica: nessuna shell attiva, 6153 e 6163 libere, nessun
> processo Python mio. Nessun `dev.py` fino al RESUME.
> ▶️ **30/09 12:23 — RESUME** (coordinator): venv aggiornato e verificato (borsa 0.3.2, idna 3.20, soupsieve 2.10). Comandi
> Python di nuovo consentiti.

> 🔒 **30/09 13:49 — due righe del mio `risk-analysis.spec.ts` a Risk** (checkpoint del calendario, cura di C3, approvata
> dal developer): `:104` di HEAD, la copia di `MONTHLY_VAR_HORIZON_DAYS` da `21` a `30` (nel mio albero è `:125`), e
> `:482` di HEAD, il mock di `var_cvar` con `horizon_observations: longHorizon ? 21 : 1` (nel mio albero è vicino a
> `:510`). Le scrive test-author nel suo checkpoint. **Risposto OK. Fino all'arrivo del suo checkpoint non tocco quelle
> due righe.**
> - **Verificato prima di rispondere**: i miei pezzi non committati nello spec non le toccano. Il più vicino è il blocco
>   `instanceStatus` inserito dopo `:93`, con 10 righe invariate prima di `:104`; il commento dello stub a `:427-429`
>   dista 50 righe da `:482`. La fusione non dovrebbe avere conflitti testuali.
> - **Effetto sul mio lavoro**: `horizon_days` diventa in giorni di calendario, e `RiskVarCvarOutput` guadagna
>   `horizon_observations` (obbligatorio). Facoltativo e non richiesto: «30 giorni ≈ n osservazioni» sulla scheda del
>   mese di L1. Dopo il suo checkpoint serve un `api sync` nella mia corsia.

> 🔒 **30/09 17:33 — lo scatter condiviso concesso una tantum a F** (richiesta del developer nella review del L3° di F:
> un clic sulla tabella o sul grafico seleziona la riga o il puntino, con un colore). Prop solo additive su
> `charts/ScatterChart.svelte`: `selectedId?: string | null` (il punto con quell'id più grande e verde `#22c55e`) e
> `onpointclick?: (id) => void`. La mia L3, che non le passa, resta identica.
> - **Risposto (a)**: non ho niente di non committato sotto `charts/`, verificato. **Precisato**: lo stile del puntino si
>   costruisce in `scatterChartHelpers.ts:136-166` (`symbolSize`/`itemStyle`), quindi la concessione deve coprire anche
>   quel file.
> - **Conseguenza per me**: **V6** (`grid` a `scatterChartHelpers.ts:208`, non cominciato) si fa solo **dopo** che il
>   lavoro di F è arrivato nel mio ramo: uno scrittore per file. Verifiche: E2E `risk` (lo scatter di L3,
>   `data-point-count` 3) e `risk-lab`.

### Passo 8 — il benchmark condiviso: posseduto ammesso, scelta sempre visibile, id morto ignorato · 🔶 01/10

**Decisione del developer (01/10, via Risk), testuale**: «credo che matematicamente può avere senso usare come
benchmark un asset posseduto […] Vorrei che ovunque serve scegliere un benchmark ci sia un selettore che permette di
farlo e che al momento del caricamento della pagina, esso mostri il benchmark attuale, vuoto non deve mai essere,
eccetto quando non c'è nessun asset impostato». **La regola** (uguale per Dashboard/Broker, lab e pagina dell'asset):
si esclude solo ciò che viene misurato; il selettore mostra sempre la scelta corrente; un id salvato che non
corrisponde più a nessun asset vale come «non impostato» (segnaposto, nessun calcolo). La pagina dell'asset è di Risk,
il lab di F; a me `L3Benchmark` e `RiskLevelsPanel`.

**Stato misurato nel codice (01/10)**:
- `RiskLevelsPanel.svelte:283` passa `excludeAssetIds={assetIds}`, e `L3Benchmark` lo usa come `filter` di `AssetSelect`.
  `SearchSelect` cerca il valore **solo fra le opzioni** (`selectedOption = options.find(…)`, `:98`), quindi un
  benchmark posseduto salvato mostra il segnaposto (`:440`), mentre `run()` confronta proprio contro di lui.
  **Difetto vero, oggi**: il Broker esclude solo i propri asset, quindi un benchmark scelto lì può essere posseduto in
  un altro broker, e la Dashboard poi lo nasconde.
- L'E2E esistente (`risk-analysis.spec.ts`, «a benchmark chosen on the Dashboard is the benchmark in force on Broker
  Detail») **non vede il difetto**: controlla `data-benchmark-id` (l'attributo), non quello che il selettore mostra, e
  `chooseBenchmark` sceglie la prima opzione, che sulla Dashboard oggi non è mai un asset posseduto.
- **Id morto**: oggi `run()` parte con qualunque id salvato. Nessun controllo di esistenza.
- `L3Benchmark` è usato **solo** da `RiskLevelsPanel` (gli altri `excludeAssetIds` sono del monolite di Asset Detail e
  di `SignalAssetParamControl`, non miei e non toccati).

**Fatti che decidono il disegno**:
- `GET /assets/query` senza filtri restituisce **tutti** gli asset: niente `limit`/`offset`, e `user_id` serve solo ai
  contatori `tx_count_own` (`services/asset_sources/crud.py:149`). Quindi un id **assente da una lista caricata** è un
  asset che non esiste più.
- Lo store degli asset **non esporta `isLoaded`**: si sa che la lista è arrivata solo aspettando `ensureAssetsLoaded()`.
  Se il caricamento fallisce, la promessa si risolve lo stesso con la mappa vuota (`entityStore.ts:88-111`).
- ⚠️ **`assets.id` è `INTEGER PRIMARY KEY` senza AUTOINCREMENT** (verificato sullo schema reale della copia di prod):
  SQLite riassegna `max(id)+1`. Se si cancella l'asset con l'id più alto e se ne crea un altro, **il nuovo prende lo
  stesso id**, e un benchmark salvato «morto» tornerebbe vivo su un asset diverso.

**Disegno (mio, nei miei file)**:
1. `RiskLevelsPanel`: via `excludeAssetIds={assetIds}`; `L3Benchmark`: via la prop e il `filter`. Nessuno lo passa più, e
   su questi perimetri si misura il portafoglio, non un asset.
2. `L3Benchmark` distingue quattro stati, pubblicati in `data-benchmark-state`: `none` (niente salvato), `pending`
   (salvato, lista degli asset non ancora arrivata), `set` (salvato e presente), `unknown` (salvato, lista arrivata, id
   assente). **Solo `set` calcola**: l'effetto di avvio **e** il callback di `run()` (che il controller può richiamare
   da solo) rifiutano un id che non è `set`. Il selettore riceve l'id solo se `set`, altrimenti `null`, quindi
   segnaposto. `data-benchmark-id` diventa l'id **in vigore** (vuoto se `none`/`pending`/`unknown`).
3. **L'id morto non si cancella dalla memoria, si ignora.** Il frontend non distingue con certezza «cancellato» da
   «lista non arrivata» o «caricamento fallito» (lo store non dice se ha caricato, e un fallimento lascia la mappa
   vuota): cancellare toglierebbe al lettore una scelta valida per un problema di rete. Una scelta nuova lo
   sovrascrive.
   - **Limite noto, da segnalare a Risk** (lo store è suo, lo schema è del backend): per la riassegnazione degli id,
     un id ignorato può tornare valido su un asset diverso. Il selettore lo mostrerebbe per nome, quindi non è
     invisibile, ma non è una scelta del lettore. Cancellarlo ridurrebbe la finestra, non la chiuderebbe. La cura vera
     è fuori dal mio perimetro: AUTOINCREMENT, oppure salvare più dell'id.
4. **`SYMBOL_BY_ROLE`** (`scatterChartHelpers.ts:79`, dichiarato e mai applicato, quindi il benchmark esce come cerchio
   e non come il rombo che promettono i commenti e la guida di F): **decisione mia, applicarlo**. Il rombo distingue il
   benchmark per forma e non solo per colore. Si fa con V6, **dopo** che il lavoro di F sul file è arrivato nel mio
   ramo.

**Test list proposta (E2E, `risk-analysis.spec.ts`, mio; non tocco le due righe concesse a Risk)**:

| # | cosa fissa | rosso oggi |
|---|---|---|
| **B1** | un benchmark **posseduto** già salvato: al caricamento della Dashboard **e** del Broker il selettore lo **mostra** (il trigger contiene il nome dell'asset, letto dai dati e non tradotto) e il confronto parte con quell'id | sì: oggi segnaposto |
| **B2** | la lista del selettore **contiene** gli asset posseduti, sulla Dashboard e sul Broker (l'opzione con l'id posseduto c'è) | sì: oggi esclusi |
| **B3** | un id **morto** salvato (un intero positivo che non corrisponde a nessun asset): `data-benchmark-state="unknown"` come barriera, segnaposto, `data-benchmark-id` vuoto e **nessuna** richiesta di confronto con quell'id | sì: oggi la richiesta parte |
| **B4** | gli E2E esistenti del benchmark (Dashboard→Broker, cambio di periodo) restano verdi; si aggiorna il commento di `chooseBenchmark`, vecchio su due punti (l'esclusione, e il `-trigger` che oggi esiste perché `AssetSelect` inoltra il `testid`) | — |

> ✅ **Test list approvata dal developer (01/10)**: «Approvata: via con test-author».

> **Note implementazione (passo 8, test)**:
> - **test-author** ha scritto in `risk-analysis.spec.ts` un `describe` nuovo, «the shared benchmark: a held asset is
>   allowed, the choice is always shown, a dead id is ignored» (`:2642` e seguenti), con 5 test (B1 e B2 su Dashboard e
>   Broker, B3), più gli helper (`:1073-1266`):
>   - `seedRiskBenchmark` (chiave dell'utente scritta con `addInitScript`);
>   - `heldBenchmarkCandidate`: un asset posseduto da un broker di cui l'utente ha una quota, la stessa regola della
>     Dashboard;
>   - `openDashboardRiskWithHoldings` / `openBrokerRiskWithHoldings`: aspettano che le posizioni siano arrivate;
>   - `openBenchmarkPicker` / `closeBenchmarkPicker`.
>
>   B4: il commento di `chooseBenchmark` è riscritto (niente più esclusione; `-trigger` esiste), il comportamento è
>   invariato. **Le due righe riservate a Risk sono identiche byte per byte** (`:125`, `:510`).
> - **Reperti di test-author, giusti**:
>   - **senza aspettare le posizioni, i rossi dipenderebbero dai tempi**: l'elenco da escludere arriva *dopo* la lista
>     degli asset, e in quella finestra l'asset posseduto è mostrato e offerto. Sulla Dashboard la lista degli asset
>     carica prima ancora che il report sia chiesto. Per questo ci sono i due «opener» che aspettano le posizioni;
>   - `openFirstBrokerRisk` sceglie per posizione, e un broker creato da un altro spec può venire prima e non possedere
>     niente. I test nuovi aprono un broker che possiede qualcosa, per id;
>   - la Dashboard chiede il report per i broker **di cui l'utente ha una quota**, non per tutti: l'helper usa la stessa
>     regola.
> - **Rossi sul codice di oggi** (sulla 6153, `/tmp/libreFolio_a_e2e_bench_red.log`) → **5 failed**, ciascuno sulla
>   clausola sostanziale e mai su una barriera:
>   - B1 Dashboard e Broker: il trigger mostra il segnaposto e non il nome dell'asset posseduto salvato (asset 1 del DB
>     di test); più `data-benchmark-state` assente;
>   - B2 Dashboard e Broker: `search-select-option-1` non c'è;
>   - B3: `data-benchmark-state` assente, `data-benchmark-id="2000000000"`, e l'id morto **mandato al server**
>     (`[2000000000]`).
>
>   Porta libera dopo.

> ⏸️ **01/10 — la parte del selettore è FERMA, per Risk.** Risk scrive una primitiva condivisa,
> `components/risk/BenchmarkSelect.svelte`, con `resolveRiskBenchmark()` nello store, perché la regola vale su tre
> superfici e il difetto di oggi nasce da filtri decisi pagina per pagina. Interfaccia: `measuredAssetIds`;
> `bind:value` (la scelta risolta, un id morto vale `null`); `onchange(id)`, chiamata dopo la scrittura nello store;
> `testid`, `placeholder`; le sezioni «benchmark / altri asset».
> **Il mio cambiamento diventa**: `L3Benchmark` monta la primitiva con `measuredAssetIds={[]}`; **via** la mia
> idratazione e la mia `riskBenchmark.set`; resta la logica del controller (`run`, epoche, `bumpGeneration`). Il disegno
> dei quattro stati, sopra, passa alla primitiva. **Nessun codice di prodotto scritto** per il passo 8.
> ⚠️ **I 5 test B sono rossi di proposito** finché la primitiva non arriva e non la monto. Un checkpoint prima di allora
> deve dichiararli, oppure metterli in `test.fixme` con il motivo. Mai consegnarli rossi in silenzio.

> 🤝 **Contratto della primitiva, fissato con Risk (01/10 13:32)**: ha accolto tutti e quattro i punti.
> - **Stato**: `state` come prop `$bindable` (`none` | `pending` | `set` | `unknown`, esattamente i valori dei test), e
>   gli attributi `data-benchmark-state`, `data-benchmark-id` (valore risolto, `''` se null) e `data-measured` sulla
>   radice della primitiva, `data-testid="${testid}-control"`.
> - **DOM invariato**: la primitiva avvolge `AssetSelect` così com'è. `${testid}-trigger`, `${testid}-search`,
>   `search-select-option-<id>` e il `div` della scelta restano come oggi. Il ⚠ sta fuori dal trigger, solo se la scelta
>   è fra i `measuredAssetIds`: per me non compare mai (`[]`).
> - **Tempi**: con `measuredAssetIds={[]}` non c'è un filtro tardivo; la finestra trovata da test-author non esiste più
>   sulle mie pagine (gli «opener» che aspettano le posizioni restano: non costano e proteggono i rossi).
> - **Id morto**: `resolveRiskBenchmark()` restituisce `{state, assetId}` **senza mai scrivere nello store**. `unknown`
>   vuol dire segnaposto, `null` e nessuna richiesta; l'id salvato resta finché l'utente non sceglie. Il riuso degli id
>   (niente AUTOINCREMENT) lo porta Risk al coordinator: tocca anche gli altri riferimenti ad asset salvati nel client.
> - **`SYMBOL_BY_ROLE` con V6**: confermato.
>
> **Come lo collegherò** (deciso ora, così i test restano com'è): `L3Benchmark` monta la primitiva con
> `measuredAssetIds={[]}`, `bind:value` e `bind:state`, e **ripubblica** `data-benchmark-id` e `data-benchmark-state`
> sul suo wrapper `risk-l3-benchmark`, che gli E2E esistenti e i B già leggono. Effetto di avvio e callback di `run()`
> partono solo con `state === 'set'`. Via l'idratazione, `riskBenchmark.set` e il `filter`. Poi i 5 B devono passare
> da rossi a verdi senza toccarli, e restare verdi gli E2E `risk` esistenti.

---

## Checkpoint 1 del giro — tutto ciò che è finito e verde, **senza** il benchmark · 01/10 16:00

> **Richiesta di Risk (01/10 15:50)**: mentre la primitiva arriva con il suo prossimo checkpoint, consegnare FROZEN la
> parte finita e verde che non riguarda il benchmark, per tenere piccola la fusione. I rossi del benchmark restano fuori.

**Come ho tenuto fuori i test B**: erano nello stesso file degli N2/T3 (`risk-analysis.spec.ts`), e il coordinator mette
in stage i file interi.
- Salvate fuori dal worktree due versioni dello spec, in `files/bench-hold/`: **full** (con i B, sha256 `d5bbe80c…`) e
  **base** (questo checkpoint, `e9c57f20…`). Script: `/tmp/libreFolio_a_split_bench.py`.
- Tolte tre regioni: il commento di `chooseBenchmark`, riportato a quello di HEAD, perché il nuovo dice «nessuna
  esclusione», che sarà vero solo con la primitiva; gli helper; il `describe` annidato.
- **Rientro provato**: `git merge-file` (fusione a tre vie, solo sull'albero di lavoro) da base a full **ricostruisce
  full byte per byte**. Dopo la fusione della punta di Risk, che porta le sue due righe dello spec, lo stesso comando
  riapplica i B senza toccarle.
- Lo spec del checkpoint, rispetto a HEAD, ha **solo i 7 pezzi di T3/N2**; le righe riservate a Risk (`:125`, `:510`)
  sono identiche. Prettier voleva togliere una riga vuota lasciata dal taglio: tolta, e base salvata di nuovo.

**Delta**: 12 file tracciati modificati, 2 nuovi.
- `levels/`: `RiskPartialNotice.svelte` (+ `.test.ts`, ora mio), `RiskLevelsPanel.svelte`, `L3RiskAdjusted.svelte`,
  `L1HowMuchItHurts.svelte`, `l3Helpers.ts` (+ `.test.ts`); nuovo `L2Diversification.test.ts`;
- `e2e/portfolio/risk-analysis.spec.ts` (T3, N2, opzione `instanceStatus`);
- i18n ×4: **solo aggiunte**, 4 chiavi (`risk.levels.l3.scatter.unpriced`, `risk.levels.notice.noPriceSourceTitle`,
  `risk.levels.notice.affected`, `risk.levels.l3.rows.kpi`);
- questo piano (nuovo).
- `L2Diversification.svelte` **non** cambia: è ancora quello del checkpoint di Risk (`91e91346c`).

**Prove sull'albero del checkpoint (01/10)**:
- vitest su 7 file dei livelli → `Test Files 7 passed (7)` · **212**;
- `front check` (15:55, client 30/09 11:36) → i soliti 3 errori, 0 in file risk;
- E2E `front-portfolio risk` sulla 6153 → **16 passed**;
- `check-links` → exit 0, **86 validi**;
- `i18n audit` → 3487 chiavi, complete;
- `prettier --check` sui 9 file del frontend → pulito · `diff --check` → pulito.
- **Rossi provati prima del codice**, nei passi sopra: T1 (6), T2 sul mutante M16 (3), T3 sul mutante delle quote (1),
  N1 (5), N2 sul pannello di prima di F2b (3); per L1, la scansione di `check-links` prima e dopo.
- **Non eseguiti**: E2E `risk-lab` e `risk-asset-detail` (nessuno dei due monta i componenti cambiati); test del
  backend (nessun cambiamento lì); `mkdocs build` (nessuna pagina cambiata).

**Da dichiarare** (non miei):
- **catalogo**: `L2Diversification.test.ts` va aggiunto a `risk-levels-component` (`_frontend_portfolio.py`, lista
  file `:167`, `tests=` `:290`). La sua `desc` è vecchia: dice ancora «joined by a middle dot» (ora sono etichette
  raggruppate per livello) e non cita la regola del tono;
- `frontend-testing.instructions.md` indica `front_component_unit` per i test di componente, ma quelli dei livelli
  stanno in `risk-levels-component`;
- **CHANGELOG** (condiviso): due voci proposte, sotto «📉 Risk Analysis leaves beta, except the simulation»; il testo è
  nel messaggio di handoff.
- **Pulizia rimandata, nei miei file**: la citazione vecchia `schemas/risk.py:1056` (oggi
  `validate_status_payload`, `:1620`) nel docstring di `RiskLevelsPanel` e nei commenti dello spec.

**Commit proposto**: `/tmp/libreFolio_commits/A-dashboard-ckpt1.txt` (`feat(risk): cause-first notice, honest L3
residual`).
**Stato**: **FROZEN**. Nessun server; 6153 e 6163 libere. Dopo il commit e la fusione, i B rientrano con
`git merge-file` e diventano verdi con la primitiva.

### Checkpoint 1 — la registrazione nel catalogo · 01/10 16:10

> **Concessione del coordinator, via Risk (01/10 16:05)**, testuale: in `_frontend_portfolio.py`
> `L2Diversification.test.ts` nella lista di `front_portfolio_risk_levels_component`, lo stesso file nel `tests=` di
> `risk-levels-component`, e la correzione della `desc` (etichette raggruppate per livello e regola del tono, al posto
> di «joined by a middle dot»). «Nothing else in the file. The commit has to pass `check-orphans` on its own.»

> **Note implementazione**:
> - Le tre modifiche, su **due righe** (`:167` e `:290`; `git diff --numstat` → `2 2`). La `desc` ora descrive l'avviso
>   (prima le cause, poi le misure; il tono; il titolo dalla causa; le etichette raggruppate per livello, in ordine di
>   pagina, quelle senza livello in fondo e mai perse) e la scheda «non misurato» di L2 (c'è con un contributo ok o
>   parziale; sparisce, con la riga e la griglia, quando manca, non è disponibile o è fallito).
> - **Verifiche**:
>   - `py_compile` OK;
>   - `dev.py test check-orphans` → exit 0, «all 274 reachable from 'all'»;
>   - `front-portfolio risk-levels-component` sulla 6153 → **`Test Files 4 passed (4)`** · 44 test (erano 3 file).
>   - Lint: **identico a HEAD**. ruff 19 errori (18 `E701`, 1 `PLC0415`) e black «would reformat», tanto su HEAD quanto
>     sull'albero, confrontati via stdin con il nome vero del file perché valga la configurazione del repo. Già presenti
>     prima, e la concessione dice «nothing else in the file».

> **⚠️ Fuori pista — `--verbose` non esiste**: il primo lancio del selettore è uscito con exit 2 prima di partire
> («unrecognized arguments: --verbose»). Era un errore d'uso, nessun DB, file o server toccato. Nel runner la verbosità
> è il valore predefinito, e `-q` la toglie. Rilanciato senza.
> **⚠️ Fuori pista — un confronto di lint invalido**, corretto prima di usarlo: black lanciato su una copia in `/tmp`
> non legge `pyproject.toml` (lunghezza di riga predefinita 88 invece di 300). Rifatto via stdin con
> `--stdin-filename`.
