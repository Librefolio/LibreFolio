# S5 — Asset Global ai livelli ridotti · piano di esecuzione

> **Mandato**: `implementation_2/S5-asset-global.md` · **Round 2, fase 2**
> **Worktree**: `e-alfy-super-dollop` · **Branch**: `e-alfy-risk-asset-global-lab`
> **Baseline**: `7d75a9c6c283af4bccf11f6bf380ffaa701d53eb` (verificata, `api sync` già eseguito)
> **Corsia**: `--test-port 6157` · `--data-dir /tmp/librefolio-r2-s5`

## La regola che governa tutto

> **Con i pesi → euro → «io». Senza pesi → percentuali → «questi».**
> Un insieme di asset non ha pesi: **in questa pagina non compare mai un euro**, in nessun pannello.

---

## Stato dei passi

| # | Passo | Stato | Data |
|---|---|---|---|
| 0 | Analisi (consegna 1) | ✅ | 2026-09-18 |
| 1 | Ricollocare la heatmap fuori dal legacy | ✅ | 2026-09-18 |
| — | 🚦 **Cancello**: il coordinatore guarda la superficie nel browser | 🔴 **bloccato**: porta 6157 di un altro worktree (§B3) | — |
| 2 | Smontare `RiskAnalysisPanel` da `AssetSetRiskPanel` | ⏸ bloccato dal cancello | — |
| 3 | Colonna gratuita: correlazione media con il resto dell'insieme | ⏳ **volutamente non iniziato**: il cancello esiste per validare le fondamenta prima che ci si costruisca sopra | — |
| 4 | `L4Replay` con `showMoney={false}` — **mai `L4Shock`** | 🔴 **non eseguibile**: vedi §B1 | — |
| 5 | ~~Nuova chiave i18n «fuori scopo» × 4 lingue~~ | ❌ **decaduto**: la chiave esiste già, il difetto è altrove e non è mio — vedi §R1 | 2026-09-18 |
| 6 | Requisito del cancello-euro a T3 | ⏳ | — |

---

## Passo 0 — Analisi ✅ 2026-09-18

> **Note implementazione**: consegnata al coordinatore e approvata. Ha falsificato **cinque**
> presupposti del briefing, misurati sul codice. I tre più rilevanti:
>
> 1. **«`:285` monta 1 068 righe del muro di metriche»** — vero come riga, **falso come effetto**.
>    Le otto sezioni del legacy sono dietro un cancello derivato dal catalogo *per scope*
>    (`RiskAnalysisPanel:124-130`). Su `asset_set` ne sopravvivono **due su otto**:
>    `correlation` (`:642`, mia) e `stress` (`:724`). **Il muro è su Dashboard e Broker, non sulla mia pagina.**
> 2. **«Togliendo il legacy togli la violazione `sobol_start_index`»** — **falso per la mia pagina**:
>    `:1021` sta dentro `{#if supportsSimulation}` (`:960`), e `simulation` è `ASSET|PORTFOLIO`.
>    Su `asset_set` non è mai renderizzato.
> 3. **«L4° = solo replay»** — il replay **oggi è irraggiungibile**: `:865 {#if scope.kind === 'asset'}`
>    è annidato dentro `{#if supportsStress}` (`:724`). **La pagina mostra lo shock vietato e nasconde
>    il replay permesso: l'esatto contrario del design.**
>
> E il quarto, che ha determinato l'ordine dei passi: **il mio L2 vive dentro ciò che devo rimuovere.**
> `CorrelationHeatmap` ha **un solo punto di montaggio: `RiskAnalysisPanel:646`**. Smontare il legacy
> prima di ricollocare **avrebbe cancellato la consegna del round 1**.

> **Risposta alla domanda d'architettura** (come si esprime la riduzione): **né una prop né una quinta variante.**
> La dicotomia presupponeva che la differenza fosse di presentazione. Misurata, «riduzione» si spacca in due metà
> con risposte opposte:
> - **«niente euro» è già uno stato d'ingresso**, non una modalità: `L1HowMuchItHurts:22-37`, docstring di S1 —
>   *«quando manca, la colonna del denaro semplicemente non appare»*. Una prop `moneyless` sarebbe
>   **«un secondo interruttore per una luce già spenta»**, e due interruttori in disaccordo sono un bug
>   che nessuno dei due autori vede da solo.
> - **«per-asset» non è una riduzione, è una trasposizione**: L1 di S1 prende i risultati di *uno* scope → 3 righe
>   (una *scala*); L1° vuole N asset → N righe (un *asse di asset*). **Una prop non può cambiare l'arietà
>   dell'ingresso. Un booleano che commuta l'arietà è due componenti che condividono un nome.**

---

## Passo 1 — Ricollocare la heatmap ✅ 2026-09-18

**Obiettivo**: la matrice di correlazione smette di dipendere dal legacy, **prima** che il legacy venga tolto.

### Cosa è stato fatto

| File | Natura | Righe |
|---|---|---|
| `components/risk/AssetSetCorrelationSection.svelte` | **nuovo** | 79 |
| `components/risk/AssetSetRiskPanel.svelte` | modificato, **puramente additivo** | `27 +`, `0 −` |

> **Note implementazione**: il nuovo componente possiede il proprio `RiskPanelController` su
> `scope = {kind:'asset_set', asset_ids}` e ricava l'output con `resultByCode(…, 'correlation')` +
> `riskOutput(…, schemas.RiskCorrelationOutput)`. Il pannello gli passa `selectionLabels` e lo monta
> **sopra** il legacy, che in questo passo **resta al suo posto**: il cancello del coordinatore
> vuole vedere la superficie nuova prima che la vecchia sparisca.

> **⚠️ Fuori pista — perché un componente e non un blocco nel pannello.**
> Avevo pianificato di montare la heatmap direttamente in `AssetSetRiskPanel`. Misurando, non si può:
> `createRiskPanelController` si auto-carica via `$effect` (`riskPanelController:354-356`) e
> **`loadBase` non ha alcuna guardia sul vuoto** (`:181-232`). Un controller dichiarato al livello
> dello script del pannello partirebbe con `asset_ids: []` — che viola `min_length=1` — e il 422 di
> ritorno diventerebbe `loadError = true`, cioè **un errore di caricamento mostrato all'utente ogni
> volta che la selezione è vuota**, che è lo stato iniziale della pagina.
> **Il confine di componente è la guardia**, ed è lo stesso schema che il codice già usa per il problema
> identico: il legacy è montato sotto `{#if selectedAssetIds.length > 0}`. Non è un'invenzione, è la
> convenzione esistente applicata al componente nuovo.

> **⚠️ Fuori pista — una regressione silenziosa evitata sulle etichette.**
> La via ovvia per `assetLabels` era `selectedAssets` (i nomi che il pannello ha già in mano, senza
> giro sullo store). Ma `selectedAssets` (`:77`) **filtra sugli asset di pagina**, e il pannello è
> progettato per tollerare un caso che quel filtro scarta: un id ricordato da una visita precedente e
> non più in elenco — *«presente nell'analisi, invisibile nei controlli»* (docstring `:92-97`).
> Il legacy risolveva quegli id **attraverso lo store** (`:199-201`), quindi **oggi mostrano un nome**.
> Fermarsi a `selectedAssets` li avrebbe degradati a `#42` senza che nessun test se ne accorgesse.
> `selectionLabels` prende i nomi dalla pagina **e poi** interroga lo store solo per ciò che manca:
> superset di entrambe le vie.

### Costo di rete: zero

Due controller convivono in questo passo (il mio e quello del legacy). **Non sono due chiamate**:
`queryRisk` (`riskStore:130-140`) è cachata per **chiave canonica della richiesta** e **deduplica le
richieste in volo**. Stesso scope, stesse date, stessa valuta → stessa chiave.

### Evidenza — comandi esatti ed esiti

```
PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py front check
  → svelte-check found 0 errors and 41 warnings in 2 files
```

I 41 warning sono **preesistenti e non miei**: `BrokerSharingPanel.svelte` e `GlobalSettingsTab.svelte`,
tutti `event_directive_deprecated`. Verificato che i miei file **non compaiono affatto** nel log:

```
grep -c "AssetSetCorrelationSection\|AssetSetRiskPanel\|CorrelationHeatmap" <log>  →  0
```

```
PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py front format
  → AssetSetCorrelationSection.svelte  6ms        (riformattato: attributi ricompattati)
  → AssetSetRiskPanel.svelte          27ms  (unchanged)
```

```
git status --porcelain
  M  frontend/src/lib/components/risk/AssetSetRiskPanel.svelte
  ?? frontend/src/lib/components/risk/AssetSetCorrelationSection.svelte
```

**Prettier non ha toccato nulla fuori dai miei due file** — verificato sull'albero, non sul log.

```
PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py front build
  → ✓ built in 31.93s · Wrote site to "build" · ✅ Frontend build complete!
```

Questa è la prova più forte delle tre: non «compila un file», ma **il bundle di produzione si costruisce**
con il componente nuovo dentro. La build esegue `svelte-check` a sua volta e non si è fermata.

> **⚠️ Fuori pista — il comando del cancello non esiste nella forma data.**
> Il coordinatore aveva prescritto `dev.py test --test-port … --data-dir … front build`.
> `front` **non è una categoria di `test`**: le categorie `front-*` del runner sono suite Playwright.
> ```
> dev.py test: error: argument : invalid choice: 'front'
>   (choose from … 'front-utility','front-broker',…,'front-ai-export','all',…)
> ```
> La forma giusta è **`dev.py front build`**, al primo livello del CLI. Segnalato: quel blocco di
> comandi stava per finire in un template, ed è l'errore che si copia meglio — **sbagliato in un modo
> che sembra coerente con le righe accanto.**

### ⚠️ Cosa questa evidenza NON dimostra

`front check` **non guarda `e2e/`** (`tsconfig.json` esclude `e2e/**`) — lezione del round 1, vale ancora.
E `svelte-check` verde dice che **compila**, non che **renderizza**: la definizione di finito del passo 1
è il coordinatore che guarda la superficie nel browser, in italiano. **Non è ancora avvenuto.**

---

## Blocchi aperti

### 🔴 B1 — Due autorizzazioni riferite a codice che nel mio ramo non esiste

Misurato sul mio albero a `7d75a9c6c`, con `git status --porcelain` a **0 righe**:

```
grep -c showMoney frontend/src/lib/components/risk/levels/l4/L4Replay.svelte   → 0
grep -c showMoney frontend/src/lib/components/risk/levels/l4/L4Shock.svelte    → 0

L2Diversification.svelte = 117 righe
  interface Props { contributionResult; assetNames?; loading?; visibleRows? }
  grep -c correlation → 0
```

- Il `showMoney` di S4 (autorizzato «montalo con `showMoney={false}`») **non è nel mio ramo**.
- Il `correlationResult` di S2 (istruzione: «non duplicare, passa `correlationResult` a `L2Diversification`»)
  **non è nel mio ramo**: la prop non esiste.

Gli indirizzi citati dal coordinatore (`L4Replay:44`, `:138`, `:193`) sono **dell'albero di S4**: i miei
punti di chiamata sono `:124` e `:179`, cioè il file differisce di ~14 righe fra i due alberi.
Passare oggi una delle due prop fallirebbe `svelte-check` o renderebbe nulla.

📌 È **D182 applicato al mandante**: *«il codice si data con lo SHA»*.

### ⚠️ B2 — `L4Shock` su Asset Global: contraddizione da sciogliere

Il coordinatore ha scritto «monta `L4Replay` **e `L4Shock`** con `showMoney={false}`. Ma:
- `03-mappa-livelli-pagine.md` §2 dà ad Asset Global «⚠️ **solo replay storico, in %** · ❌ shock ipotetico»;
- §3.3 ne dà la ragione: *«lo shock ipotetico senza pesi è quasi tautologico: riscrive l'input in forma diversa»*;
- **lui stesso** aveva confermato in precedenza «montare `L4Replay` (mai `L4Shock`)».

**Intenzione dichiarata**: monterò **solo `L4Replay`**, salvo istruzione contraria motivata.

✅ **Sciolto 2026-09-18**: il coordinatore ha dato ragione alle tre fonti contro sé stesso —
**solo `L4Replay`, mai `L4Shock`**. Con la sua motivazione: *«un ridisegno che trasporta il difetto è
peggio di nessun ridisegno, perché gli dà l'aria di una scelta»*.

### 🔴 B3 — La porta della mia corsia è occupata da un altro worktree

```
lsof -nP -iTCP:6157 -sTCP:LISTEN
  Python  84109  …  TCP *:6157 (LISTEN)

ps -o pid,ppid,lstart,command -p 84109
  84109  83673  Fri Sep 18 16:06:47 2026
  … uvicorn … backend.app.main:app --host 0.0.0.0 --port 6157

lsof -a -p 84109 -d cwd
  cwd  DIR  …/LibreFolio-worktrees/e-alfy-crispy-pancake        ← NON è il mio albero
```

Non è un guscio rimasto aperto: **risponde e serve l'app completa**.

```
curl http://127.0.0.1:6157/               →  <!doctype html> … (l'app)
curl http://127.0.0.1:6157/api/v1/health  →  HTTP 404 in 0,0055 s
```

**Non toccato**: niente `--force`, niente kill — è di un altro mandato e il mandato me lo vieta.
**E non è mio**: in questa corsia non ho mai acceso un server.

> 🔑 **Il danno non è il conflitto di risorse, è l'attribuzione.**
> Il cancello di questo passo è *«il coordinatore guarda la pagina nel browser»*. Se avesse aperto
> `localhost:6157` avrebbe visto **la Asset Global di `crispy-pancake`** e l'avrebbe messa nel mio
> verbale. **Una schermata non porta la propria provenienza**: dei tre modi di datare (SHA per il
> codice, il mondo per un numero, fonte+momento per un fatto relayato) **un browser non ne ha
> nessuno** — ed è la sola prova che usiamo come definizione di finito.
>
> **Contromisura proposta e adottata**: quando il server sarà alzato, l'indirizzo viaggia insieme
> all'**impronta dell'albero servito** — `git rev-parse HEAD`, `git status --porcelain | wc -l`, e il
> `cwd` del processo in ascolto.

✅ **Sciolto 2026-09-18**: il coordinatore ha verificato indipendentemente (`6157` → `crispy-pancake`,
albero **estraneo alla campagna**; `6154` → S2, legittimo) e ha **riassegnato la corsia a `6167`**,
cartella dati invariata. **Il protocollo dell'impronta è stato adottato per tutti e sei i mandati.**

---

## Cancello del passo 1 — aperto 2026-09-18

```
http://localhost:6167/assets?tab=correlation        (e2e_test_user / E2eTestPass123!)

pid in ascolto : 41897
cwd            : …/e-alfy-super-dollop        ← il mio albero
HEAD           : 7d75a9c6c
porcelain      : 3 righe (2 nel bundle + 1 journal)
```

### ⚠️ Fuori pista — terzo difetto nella catena di comandi, e il più insidioso

```
❌ dev.py server --test --port 6167 --no-scheduler --no-reload
✅ dev.py server --test --port 6167 --data-dir /tmp/librefolio-r2-s5 --no-scheduler --no-reload
```

Senza `--data-dir` il server **non guarda la cartella appena popolata**. Aggiunto; il log conferma
`db_path: /private/tmp/librefolio-r2-s5/sqlite/app.db`.

> 🔑 **Il `front build` sbagliato falliva rumorosamente** (`invalid choice: 'front'`): impossibile non
> vederlo, costo un minuto. **Questo sarebbe riuscito**: server su, HTTP 200, pagina che carica, e zero
> asset. **Un comando che sbaglia e si ferma costa un minuto; uno che sbaglia e prosegue costa
> un'indagine** — e qui avrebbe prodotto la ritrattazione sbagliata: *«il mio montaggio non funziona»*
> invece di *«sto parlando con l'altro mondo»*.

### 📌 La selezione di default contiene un asset senza prezzi

La scala di D19 senza `localStorage` sceglie i **posseduti**: ids `1,7,6,2,4,3,5,17`.
**`17` (Test KRW Stock) ha 0 quotazioni** — e in tutto **8 asset su 17** hanno storia nulla
(`8,9,12,13,14,15,16,17`). Quindi la matrice di default esce **7×7 o `partial`**, e *quella riga
assente non è il montaggio*. Segnalato al coordinatore **prima** che guardasse: è la stessa
attribuzione errata di `6157`, un livello più in basso.

Per una matrice informativa: **6+7** (cripto, 373 punti), **10+11** (S&P 500 e MSCI World, la coppia
che dovrebbe correlare) — **10 e 11 non sono nella selezione di default** perché non sono posseduti.

### Cautela consegnata a S1 sulla riparazione di R1

`levelHelpers:123-127` dichiara per progetto: *«Nothing is translated. These are backend strings…
Verbatim, or nothing»*, citando `RiskResultFrame:108` dove *«un valore non previsto ha stampato la
propria chiave sullo schermo»*. Chi include `result.error` nei `reasons` **deve portarsi anche la
difesa** di `RiskResultFrame:29` — `return translated === key ? $t(fallbackKey) : translated` —
altrimenti un codice d'errore nuovo del backend stampa `risk.errors.qualcosa` all'utente.
**Il file sa già che è successo una volta.**

---

## Passo 1b — la riparazione della dichiarazione (2026-09-18)

Il cancello del coordinatore ha **confermato la parità dei valori** (stesse coppie, stessi ordini,
stessi numeri, **una sola chiamata HTTP per due montaggi**) e ha trovato **tre capacità perse**:
badge `Parziale`, avvisi, metadata.

### 🔑 Il metadata non manca alla mia sezione: manca a **tutto il ridisegno**

Misurato, non dedotto:

```bash
grep -rn "riskMetadata\|n_observations\|annualization" levels/
# → una sola riga: l4/L4Replay.svelte:62, ed è historical_replay_audit,
#   non le osservazioni.

grep -rln "RiskResultFrame" .
# → RiskAnalysisPanel.svelte   (il legacy)
#   levels/levelHelpers.ts     (solo citato in una docstring)
```

`RiskLevelSection` — **il telaio del ridisegno** — rende `health` (`:108`) e `reasons` (`:117`).
**Non rende metadata.** Quindi *nessun livello di S1–S4, su nessuna pagina*, mostra
«Osservazioni 93».

> L'argomento del coordinatore (la stessa coppia legge **93** qui, **257** da N, **353-360** da S3)
> **non è locale alla mia sezione: è di campagna.** Ripararlo solo da me farebbe della mia sezione
> l'unica superficie del ridisegno che data i propri numeri.

### La forma della riparazione: l'idioma del ridisegno, non un quinto telaio

| capacità | da dove viene ora |
|---|---|
| badge `Parziale` | `degradedResults([result])` → `health` di `RiskLevelSection` |
| avvisi verbatim | `resultReasons([result])` → `reasons` di `RiskLevelSection` |
| metadata | **blocco locale sollevabile**, in attesa che il telaio abbia lo slot |

Import in sola lettura da `levels/` — **nessun file di S1 toccato**. E il vantaggio che decide:
quando S1 riparerà `resultReasons` per includere `result.error` (reperto R1), **la mia sezione
lo eredita senza una riga**.

> **Note implementazione**: il `description` statico **non** è passato come `lead`. La docstring di
> `RiskLevelSection:21-27` dice che il lead è *«the one-line answer, generated from the data»* e che
> *«an invented lead is worse than none»*. Prosa di catalogo in quello slot si leggerebbe come un
> titolo generato dai dati. Reso dentro i children: nessuna perdita, nessun abuso del contratto.

> **Fuori pista — una difesa aggiunta che il legacy non ha.** `RiskResultFrame:96` rende
> `$t(\`risk.returnBasis.${metadata.return_basis}\`)` **senza guardia**: un enum nuovo del backend
> stamperebbe la propria chiave a schermo. Nella mia sezione `returnBasisLabel()` porta
> `translated === key ? basis : translated` — **con il valore grezzo come ripiego, che è
> un'informazione, mentre la chiave è un difetto**.

### 🔴 Fuori pista — la finestra di coesistenza rompe il MIO spec

`CorrelationHeatmap` è montata **due volte** finché il legacy resta. Rende 3 testid
(`risk-correlation-heatmap`, `-layout`, `-ordering-{mode}`) più le coppie: **tutti duplicati**.

```
risk-lab.spec.ts:753,783,803,810   expectChartCanvas(page, 'risk-correlation-heatmap')
risk-lab.spec.ts:768              page.getByTestId('risk-correlation-heatmap')
```

Nessun `.first()`, nessun `.nth()` → **strict mode violation, `resolved to 2 elements`.**
È la classe di rosso che B ha appena riparato su `asset-merge`.

> **Conseguenza operativa, e va detta invece di scoprirla**: `front-portfolio risk-lab` **non è
> eseguibile in modo significativo finché il legacy è montato**. L'evidenza che posso dare oggi è
> statica più browser, **non lo spec**. La finestra di coesistenza non è neutra: costa la mia rete
> di sicurezza, e questo è un argomento per tenerla corta.

Duplicati oggi: `risk-correlation-section`, `risk-correlation-section-metadata`,
`risk-correlation-heatmap`, `-layout`, `-ordering-*`, e le coppie. **Tutti si risolvono da soli al
passo 2.** I miei `risk-correlation-error|loading|empty|content` **non** collidono: il legacy usa
il prefisso `risk-correlation-section-`.

### Cancelli del passo 1b

```
dev.py front check   → svelte-check found 0 errors and 41 warnings in 2 files
                       grep -c "AssetSetCorrelationSection|AssetSetRiskPanel" log → 0
dev.py front format  → AssetSetCorrelationSection 7ms (unchanged)
                       AssetSetRiskPanel         21ms (unchanged)
                       grep -c "(reformatted)" → 0      ← nulla riformattato in tutto l'albero
dev.py front build   → Wrote site to "build" · ✅ Frontend build complete!
git status --porcelain → 3 righe: 1 M (AssetSetRiskPanel) + 2 ?? (sezione nuova, questo piano)
```

### 📌 Sesta coordinata di provenienza — il bundle servito

Il server era stato alzato **prima** della ricostruzione. Un server che serve asset vecchi mostra
la sezione **pre-riparazione**, e il sintomo sarebbe *«la riparazione non ha funzionato»* — la
ritrattazione sbagliata, di nuovo.

```bash
shasum -a 256 frontend/build/index.html   → 2cf11c56acc23f7e…
curl -s http://localhost:6167/ | shasum   → 2cf11c56acc23f7e…      ← identici
```

> **Alle cinque coordinate va aggiunta la sesta: il bundle servito è quello costruito.** Le altre
> cinque datano l'*albero*; questa data ciò che l'occhio vede davvero.

---

## Reperto R2 — «Nessun risultato» su una risposta perfetta (2026-09-18)

Il coordinatore ha osservato **entrambe** le sezioni vuote su una risposta `200` con **16 celle su
16 `ok`**. Cade anche il legacy → **a monte di entrambi**. Domanda posta: *«cosa fa il codice fra le
16 celle ricevute e lo stato vuoto reso? Se è una soglia, dimmi quale e dove.»*

### Risposta: **non è una soglia. La risposta non arriva mai al componente.**

Percorso condiviso, identico nei due (`AssetSetCorrelationSection` e `RiskAnalysisPanel:133`):

```ts
resultByCode(historicalResults, 'correlation')   →   riskOutput(result, RiskCorrelationOutput)
```

#### Cosa ho escluso, misurando

| ipotesi | esito | come |
|---|---|---|
| `safeParse` fallito sullo schema | **escluso** | payload vivo: `kind:'matrix'`, 16 celle, tutte `status:'ok'`, `observations:32`, `coverage:1.0`, `value` numerici |
| capability di catalogo negata | **escluso** | `/api/v1/risk/catalog` → `supported_scopes:['asset_set','portfolio']`, `supported_modes:['historical','current_composition']` → **`True`** |
| `finally` che spegne il caricamento di una generazione superata | **escluso** | `riskPanelController:232-236` — il `finally` **è** guardato da `generation === requestGeneration` |
| errore HTTP o di validazione Zodios | **escluso** | produrrebbe `loadError` → il ramo `risk-correlation-error`, non `-empty` |
| lista analitiche vuota | **escluso** | non partirebbe nessuna XHR, e l'XHR c'è |

#### 🔑 Il ramo che resta, per eliminazione: **il terzo esito di `queryRisk`**

```ts
// riskStore.svelte.ts:148
const response = await zodiosApi.query_risk_api_v1_risk_query_post(canonicalRequest);
if (!isClientSessionCurrent(requestSessionGeneration) || requestCacheGeneration !== cacheGeneration)
    return null;                      // ← né successo né errore: NULL silenzioso
```

```ts
// riskPanelController.svelte.ts:228
historicalResults = historical?.items ?? [];        // ← null e «vuoto» diventano la stessa cosa
```

> ## `queryRisk` ha **tre** esiti — riuscito, sollevato, **scartato**. `loadBase` ne conosce **due**.
> Il terzo viene rappresentato come *«non ci sono dati»*, che è un'affermazione **sul mondo** quando
> il fatto è **sul client**.

#### Come si arma da solo al ricaricamento della pagina

```ts
// clientSession.ts:42-49  — PRIMA risoluzione dell'identità
if (!this.hasResolvedIdentity) {
    this.hasResolvedIdentity = true;
    this.generation += 1;      // ← la generazione sale…
    return true;               // ← …e i resetter NON vengono eseguiti
}
```

Unico chiamante di produzione: `auth.ts:176`, dentro `checkAuth()`, che **attende** `GET /auth/me`.
Il layout lo lancia in `onMount` (`(app)/+layout.svelte:84`) e **il markup non ha guardia**: l'unico
`{#if}` di primo livello è `{#if $i18nLoading}`. **I figli montano e interrogano in parallelo.**

```
reload → componenti montano → loadBase → queryRisk cattura generation = 0
       → /auth/me risponde → transitionClientSession() → generation = 1
       → la XHR del rischio risponde → isClientSessionCurrent(0) = false → return null
       → historicalResults = []     ·  nessun errore  ·  caricamento spento
       → applyBaseSignature non rivede la firma → NON ricarica → vuoto PERMANENTE
```

**E spiega entrambi i cancelli**: al primo aveva fatto **login** (`auth.ts:63` risolve l'identità
*prima* di navigare → generazione già `1` → nessuna corsa → la matrice si vedeva). Al secondo ha
**ricaricato** — e lo dice lui stesso: *«`assetGlobal.riskSelection.v1` sopravvive al ricaricamento»*.

#### 🔑 Perché la suite non l'ha mai visto — e il meccanismo lo prova un loro test che passa

`riskStore.test.ts:246` **«drops stale responses after an account transition»** prova che lo scarto
funziona. Ma guarda l'ordine, che è lo stesso in **tutti** i test del file:

```ts
transitionClientSession(301);      // identità PRIMA
const stale = queryRisk(...);      // interrogazione POI
```

> **Ogni test stabilisce l'identità prima di interrogare — cioè l'ordine sicuro.** L'ordine insicuro
> è l'opposto, ed è quello che l'avvio fa. Il test esistente dimostra che **la guardia è giusta**;
> nessuno ha provato **il momento in cui l'identità non esiste ancora**.

### Livello di prova, dichiarato

**Eliminazione strutturale + misura dal vivo del payload e del catalogo.** Non ho catturato la corsa
in un browser: non ho quello strumento. Il *meccanismo* però non ha bisogno della mia prova — lo
prova un loro test che passa; ciò che ho stabilito leggendo è che **al boot si arma da solo**.

### Tre predizioni falsificabili, da cinque secondi ciascuna

1. Dopo il vuoto, **cambia le date o la selezione** → la matrice compare. *(la firma cambia →
   `applyBaseSignature` ricarica, ora a generazione 1)* ⚠️ **Se questa fallisce, la mia diagnosi è
   sbagliata.**
2. **Naviga nell'app senza ricaricare** → non è mai vuoto.
3. Nel pannello di rete: `/api/v1/auth/me` si chiude **dopo** che `/api/v1/risk/query` è partita.

### Non è mio da riparare

`riskStore.svelte.ts` e `riskPanelController.svelte.ts` sono infrastruttura condivisa. Le due cuciture
candidate, **senza sceglierne una**:

- **stretta** — `loadBase` distingue `null` (scartato) da `{items: []}` (davvero vuoto) e **si
  riarma** sotto la generazione corrente;
- **a monte** — il controller riascolta la generazione di sessione e rilancia quando l'identità si
  risolve.

> La guardia **non va tolta**: scartare la risposta di un altro account è corretto. Il difetto è che
> **una guardia che protegge scartando deve poter dire di aver scartato**, o la protezione diventa
> indistinguibile da un'assenza di dati.

---

## Passo 1c — la riparazione dei tre esiti ✅ (2026-09-18)

> **Note implementazione.** Assegnata dal coordinatore dopo la ratifica della diagnosi R2.
> Forma «stretta»: la guardia di `queryRisk` **non è stata toccata**.

### Cosa è cambiato

| file | delta | cosa |
|---|---|---|
| `riskPanelController.svelte.ts` | +34 / −3 | `loadDiscarded`, `loadBase(force, reAskedAfterDiscard)`, il ramo di scarto, il getter |
| `AssetSetCorrelationSection.svelte` | +12 / −0 | quinto ramo `risk-correlation-discarded` con `risk-correlation-retry` |
| `riskStore.test.ts` | +1 test | l'ordine insicuro (`test-author`) |
| `riskPanelController.test.ts` | +2 test | il riarmo e la resa onesta (`test-author`) |

**Il nodo che il piano non prevedeva**: `null` in `loadBase` aveva **già due significati** — «non ho
chiesto» (i ternari su `analytics.length`) e «ho chiesto e me l'hanno scartata» (`queryRisk`). Senza
le lunghezze delle analitiche i due nulli sono **indistinguibili**, quindi la condizione di scarto le
usa entrambe. Non è decorazione difensiva: è l'unica informazione che li separa.

### Il precedente che ha deciso la forma

`riskPanelController.svelte.ts:429` porta già `catalogState`, con la docstring:
*«`ready` | `error` | `pending` — the attribute that separates "slow" from "failed", which a single
`pending` could not say.»*

> **Lo stesso difetto era già stato riparato per il catalogo e lasciato sulla query.** `loadDiscarded`
> non inventa un'idea: applica alla risposta la distinzione che il file faceva già sul catalogo.

### Nessuna chiave i18n creata — e nessuna serviva

Misurato su tutte e quattro le lingue: `common.retry` = `Retry` · `Riprova` · `Réessayer` · `Reintentar`.

> Il coordinatore chiedeva un messaggio che dicesse **«ricarico»** invece di «nessun risultato»,
> *«perché la cura è riprovare, non spiegare»*. Portata alle sue conseguenze, la regola **elimina la
> stringa**: il ramo non ha bisogno di una spiegazione, ha bisogno del **pulsante**. E il pulsante
> esiste già in quattro lingue.

`loadBase` era **già esposto** dal controller, quindi nemmeno l'azione ha richiesto una API nuova.

### ⚠️ Fuori pista — mi sono cancellato un ramo da solo

Una `edit` il cui `old_str` attraversava il confine `{:else}` + corpo ha lasciato in piedi
`{:else}` **vuoto** seguito da `{/if}`. **Svelte lo accetta**: zero errori di sintassi, zero errori
di `svelte-check`. Sarebbe passato ogni cancello e la pagina avrebbe reso **il nulla** al posto di
«Nessun risultato».

> **Un difetto che nessun controllo di tipo può vedere, introdotto da me, nello stesso turno in cui
> stavo riparandone uno introdotto da altri.** Trovato rileggendo il file subito dopo la scrittura —
> che è l'unica difesa che c'era.

### Passo 1d — l'allarme piantato, disinnescato come chiedeva ✅

`riskStore.test.ts:102` conteneva un allarme **deliberato**, piantato a `bf34f3a0a`:

```js
// This assertion is deliberately the wrong-looking one. It goes red the day the
// field lands, and that red is the signal to assert the real invariant instead
```

**Presupposto verificato nel mio albero prima di eseguire l'istruzione** (`generated.ts:14356`):
`PortfolioRiskScope` porta ora `asset_ids` opzionale → Zod non lo strappa più.

🔑 **E la prova che l'allarme era rosso è che la sostituzione è verde**: vecchia e nuova asserzione
sono **la negazione l'una dell'altra sugli stessi ingressi**. Se il campo non fosse atterrato,
`.not.toBe` sarebbe fallita.

Eseguito: rinomina · commento sostituito · **`bf34f3a0a` citato** · e **una seconda asserzione** che
il commento originale temeva davvero (*«the unsliced portfolio, served under a sliced heading»*) ma
che l'istruzione non nominava: una fetta non deve ricevere la chiave del **portafoglio intero**.
Rimosso anche il `as unknown as` che esisteva **solo** perché il tipo non aveva il campo.

### Evidenza — comandi esatti

```
front-portfolio risk-unit             → Test Files 1 passed · Tests 17 passed   (baseline 16, +1)
front-portfolio risk-controller-unit  → Test Files 1 passed · Tests 16 passed   (baseline 14, +2)
front check                           → 0 errors, 41 warnings in 2 files · miei file: 0 occorrenze
front format                          → 0 (reformatted) ovunque
front build                           → ✅ Frontend build complete!
```

Il runner unit è `npx vitest run` puro (`_frontend_portfolio.py:79`): **nessuna porta, nessun DB**,
quindi il server vivo su `6167` non interferisce — verificato prima di eseguire, non dopo.

### Cosa NON è stato fatto, e va detto

- ⚠️ **Nessuna riproduzione nel browser.** La corsa identità/interrogazione resta provata per
  **eliminazione strutturale**; il riarmo è provato dai test unitari.
- ⚠️ **`front-portfolio risk-lab` resta non eseguibile** durante la coesistenza (duplicazione di
  testid), invariato dal passo 1b.
- ⚠️ **La corsia `6167` è contaminata**: sette asset hanno ora **un solo prezzo**, quello di oggi.
  Prima del prossimo cancello visivo va **ripopolata**.

---

## Reperti consegnati al coordinatore, non riparati da me

### R1 — La chiave i18n «fuori scopo» esiste già, e non è quello il difetto

Compito assegnato: *«aggiungi una nuova chiave in quattro lingue per il caso fuori scopo, perché
`risk.states.unavailable` si legge come un guasto»*. **Misurato prima di scrivere: non va scritta.**

```
risk.errors.incompatible_scope      ← esiste in TUTTE e quattro le lingue
  it  "Questa analitica non supporta lo scope selezionato."
```

E il cablaggio esiste: `RiskResultFrame:25-30` traduce **il codice d'errore** e ricade sulla stringa
generica **solo se la chiave manca**.

Il difetto vero è che **`error` non ha alcun percorso verso le superfici dei livelli**:

```
grep -rn "\.error\b" components/risk/   (esclusi loadError / console.error)
  → levels/l4/scenarioHelpers.ts:196
  → RiskResultFrame.svelte:22
  → dentro levels/*.svelte: NESSUNA
```

Peggio: i tre componenti che mostrano la frase generica **non guardano nemmeno lo stato**.
`L2Diversification:73` decide con `{:else if rows.length === 0}`, cioè **dalla forma delle righe
derivate** — perciò *fuori scopo*, *storia insufficiente*, *nessun risultato* e *risposta non ancora
arrivata* rendono **la stessa frase**. E `resultReasons` (`levelHelpers:135-149`) itera **solo
`result.warnings`**, mai `result.error`: la superficie del *perché* **tace proprio quando il perché è
tutta la storia**.

> 🔑 `RiskResultFrame` è usato **solo da `RiskAnalysisPanel`, il legacy**. Il ridisegno ha **perso** una
> capacità che il vecchio ha: il legacy dice *«questa analitica non supporta lo scope selezionato»*,
> i livelli nuovi dicono *«non disponibile per i dati selezionati»* — **che accusa i dati dell'utente
> di un limite dell'analitica.**

📌 **Forma generale**: *«manca la parola giusta»* e *«la parola giusta non ha una strada per arrivare
allo schermo»* si presentano **identici all'utente** e hanno riparazioni **opposte**. Il primo si
chiude in un catalogo; il secondo no — e chi chiude il primo credendo di aver chiuso il secondo
**lascia il difetto in piedi con una prova di averlo risolto.**

⚠️ **Non riparabile da me**: `levels/L1HowMuchItHurts`, `L2Diversification`, `L3RiskAdjusted` sono di
**S1 e S2**. Instradato al coordinatore.

---

## Passo 1e — decontaminazione della corsia ✅ 2026-09-18

> **Note implementazione**: il coordinatore ha **revocato** l'istruzione permanente «lascia il server su»
> e ordinato `spegni → prova la porta → ripopola`. Eseguito in quest'ordine, con l'impronta presa
> **prima** dello spegnimento, perché le prove di provenienza si raccolgono da vivo.

### ⚠️ Fuori pista 1 — la corsia veniva scritta **durante** la misura

L'impronta del «prima» ha mostrato una raffica tarda a `18:43:47Z`, **non** quella che conoscevo
(`18:22:45Z`). Lo scheduler è provato spento:

```
"Scheduler disabled via LIBREFOLIO_NO_SCHEDULER — loop not started"   server.log:1097
```

Quindi non è il server che agisce da solo. Il log nomina l'autore:

```
POST /api/v1/assets/prices/current   da 8 porte effimere distinte (61241…62572)
18:44:15.902Z  "Current-price persist: processing 14 fresh provider quote(s) … (existing rows today: 14)"
18:44:15.903Z  14 righe "[Intra-day price extend] … patch_fields=['close']"
18:44:15.907Z  "commit OK (14 row(s) written/updated)"
allo spegnimento: 2 connessioni ESTABLISHED su 6167
```

🔑 **Un browser abbandonato continua a scrivere dopo che lo sguardo è finito.** La regola di fase
diceva *«misurare e guardare sono incompatibili»*: è troppo debole. L'atto che scrive non è la
decisione di guardare, è **la connessione che resta aperta**. Per questo spegnere il server non è
igiene, è **il rimedio**: la contaminazione finisce quando finisce la connessione, non quando finisce
l'osservatore.

### 🔴 Fuori pista 2 — la premessa del rilevatore di N è falsa

N lo giustificava così: *«il generatore scrive 13-16 cifre significative; il negozio prezzi
esattamente due»*. **Il log del negozio prezzi smentisce la seconda metà**, riga per riga:

| asset | close riscritto | decimali | `close = ROUND(close,2)` |
|---|---|---:|---|
| 1 | `335.715` | 3 | ❌ non visto |
| 8 | `219.325` | 3 | ❌ non visto |
| 3 | `363.565` | 3 | ❌ non visto |
| 12 | `10936.84931506849315068493154` | 26 | ❌ non visto |
| 10 | `7635.1` | 1 | ✅ visto |
| altri 9 | `159.51`, `80955.46`, `4383.60`… | 2 | ✅ visti |

**10 su 14** — e combacia esattamente col `10` misurato. Il negozio prezzi non arrotonda: **ricopia
ciò che il provider gli dà**, con 1, 2, 3 o 26 decimali.

> 🔑 **E il numero cambia a ogni visita**: 13 → 12 → 10 su una raffica che è **sempre di 14 righe**.
> Non sono «due punti ciechi fissi su due provider», come l'avevamo registrato: sono **quattro su
> quattordici oggi, e domani un altro numero**, perché il rilevatore interroga il *valore* estratto a
> caso invece dell'*atto* che l'ha scritto.
>
> **Un rilevatore il cui tasso di errore è sorteggiato dai dati che ispeziona può provare la presenza,
> mai l'assenza — e non può mai dire «solo N righe sono state toccate».**

### 🔴 Fuori pista 3 — **il mio rilevatore v1 sbaglia, e sbaglia dalla parte peggiore**

Su corsia **appena ripopolata e incontaminata**, v1 conta **2 raffiche**:

```
2026-09-18 18:45:52   1331 righe
2026-09-18 18:45:53   1284 righe
```

Non c'è nessun secondo atto: **2615 righe non entrano in un secondo di orologio**, e la mia chiave di
raggruppamento ha risoluzione al secondo. La regola *«una raffica = pulita, due o più = qualcuno ha
guardato»* **dichiara contaminata la corsia pulita**.

🔑 È il difetto peggiore per un cancello che *autorizza a guardare*: **grida al lupo sullo stato sano,
e si impara a ignorarlo.** Un falso positivo su ciò che deve dare il via costa più di un falso
negativo su ciò che deve fermare.

**Correzione — v2: l'ARCO, non il conteggio.**

```sql
SELECT ROUND((julianday(MAX(fetched_at)) - julianday(MIN(fetched_at))) * 86400, 1) FROM price_history;
```

| corsia | arco | lettura |
|---|---:|---|
| ripopolata (misurato) | **0,1 s** | un atto solo |
| contaminata (derivato da `17:05:42` → `18:43:47` registrati) | **5 885 s** | due atti, a 98 minuti |

**Tre ordini di grandezza separano un atto da due**, e non c'è aritmetica di grappoli da tarare.
Il conteggio chiedeva *«quanti istanti distinti?»*, che è una proprietà dell'orologio; l'arco chiede
*«quanto tempo separa la prima scrittura dall'ultima?»*, che è una proprietà dell'atto.

### Esito del ripopolamento — provato, non dichiarato

```
kill 41897 → lsof -nP -iTCP:6167          ✅ nessun listener, nessuna connessione
dev.py test --test-port 6167 --data-dir /tmp/librefolio-r2-s5 db populate --force --clean
                                          ✅ 6679 record · 2615 price history · 8s
```

| misura | contaminata | ripopolata |
|---|---:|---:|
| arco (v2) | 5 885 s | **0,1 s** ✅ |
| rilevatore di N | 10 | **0** ✅ |
| asset con **un solo** prezzo | 7 | **0** ✅ |
| asset con storia | 16 / 17 | **9 / 17** ✅ |

✅ **Il ripopolamento ha restituito il fatto che la visita aveva distrutto**: 8 asset su 17 senza
prezzi, che è la proprietà del generatore su cui il coordinatore aveva scelto gli asset del cancello.

⚠️ **Da rimisurare**: la nota «0 coppie su 21 superano 0.3» in coda è **anteriore a questo
ripopolamento** e non è più garantita.

---

## Coda, datata

| cosa | dipende da | stato |
|---|---|---|
| Passo 2 (smontare il legacy) | cancello browser del coordinatore | ⏸ |
| Passo 4 (`L4Replay`) | `showMoney` di S4 **nel mio ramo** | 🔴 B1 |
| L2 di S2 | prop `correlationResult` **nel mio ramo** | 🔴 B1 |
| `onsynced` | oggi va al legacy; al passo 2 il legacy sparisce **e con lui `risk-sync-button`** → decidere se la callback resta viva | ⚠️ da non dimenticare |
| `risk-broker-filter` | copertura persa nel file sbagliato, **è di T3** | 📌 segnalato |

📌 **Se la matrice esce pallida non è il montaggio, è il dato**: oggi **0 coppie su 21** superano `0.3`.
N è stato riaperto per seminare un fattore comune.
