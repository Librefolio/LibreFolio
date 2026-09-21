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

---

# Risveglio — passi ①②③④ sulla revisione fusa `8dc9be198`

> Baseline verificata prima di scrivere: `git rev-parse HEAD` = `8dc9be1989e34341e3fa6c17e6d2dc5105a89475` ✅,
> albero pulito, porta `6167` libera. Sei mandati su sei dentro.

## ① `api sync` — fatto, e il codice d'uscita non è la prova

```
pipenv run python dev.py api sync      → exit 0, porcelain INVARIATO
```

🔑 **E il porcelain invariato non prova niente, per una ragione strutturale.** I tre artefatti
che `api sync` produce — `frontend/src/lib/api/generated.ts`, `openapi.json`,
`tool-contracts.openapi.json` — sono **tutti e tre ignorati e non tracciati**. Quindi:

- il merge **non poteva** aver portato il client rigenerato di S3 e S4 → il sync era **necessario**, non cerimoniale;
- `git status` vuoto dopo il sync è **cieco per costruzione**, non rassicurante;
- l'`mtime` non serve: il generatore riscrive incondizionatamente;
- **solo un hash prima/dopo potrebbe testimoniarlo** → candidato **settima coordinata di provenienza**.

La prova vera è stata `front check` (§④), come il coordinatore aveva avvertito. Inoltre
`front build` **riesegue `api sync` da sé** («Syncing API types before build…»), quindi il
passo è doppiamente soddisfatto.

## ② Cancellato il blocco metadata locale — la prop di S1 è arrivata

`AssetSetCorrelationSection.svelte`:

| | prima | dopo |
|---|---|---|
| import | `{riskMetadata, riskOutput, singleValue}` | `{riskOutput}` |
| import | `{degradedResults, resultReasons}` | `+ levelMetadata` da `levelHelpers` |
| derived | `riskMetadata(result)` | `levelMetadata([result])` |
| markup | `{#if metadata}…<details>…{/if}` (~29 righe) | — cancellato, `{metadata}` passato al telaio |
| helper | `percent()`, `fixed()`, `returnBasisLabel()` | — cancellati |

La porta usata è **`levelHelpers`** (`:17` il tipo, `:18` la funzione), che è la porta unica
che la docstring di S1 chiede ai consumatori.

🔑 **Il sollevamento mi costa zero, per una ragione più netta di quella di S1.** `levelMetadata()`
lascia cadere `method`. Misurato: `correlation.py:128` `method="pearson_post_fx"` è **l'unica
assegnazione** nel plugin. **Un valore che non può variare non è provenienza** — quindi non ho
perso informazione, ho perso una costante.

📌 Misurato anche: **nessuno spec asserisce** `risk-correlation-observations` né
`risk-correlation-section-metadata` → il blocco non era sotto cancello. E la prop di S1 **riusa
il mio `testId`**, quindi `risk-correlation-section-metadata` è **conservato dal telaio**.

> ⚠️ **Fuori pista**: la docstring nuova era finita **dopo** la dichiarazione che documenta, in
> coda allo `<script>`. Trovata **rileggendo il file subito dopo averlo scritto** — la stessa
> difesa che al passo 1e aveva trovato il `{:else}` vuoto. Due edit di riparazione.

## ③ L4 montato su `asset_set` — **solo `L4Replay`**

Nuovo: **`AssetSetCorrelationSection`**'s sister, `AssetSetReplaySection.svelte` (~100 righe),
montato in `AssetSetRiskPanel:313` **dentro il `{#if selectedAssetIds.length > 0}` esistente**,
fra L2 e il legacy.

🔑 **La risposta architetturale l'aveva già costruita S4, e non l'avevo prevista.** `L4WhatIf`
dichiara i tre pioli come **snippet opzionali**, ognuno dietro il proprio `{#if}`, **e l'avviso
beta vive dentro il solo ramo della simulazione**. Quindi *la riduzione si esprime consegnando
meno snippet*: niente prop `variant` su quattro componenti, niente quinto componente, e
**omettere lo shock è strutturalmente impossibile da sbagliare**. È la **quarta volta** in questa
campagna che la riparazione giusta era già scritta a poche righe di distanza.

### La regola dell'euro, provata con una ricerca

| superficie | siti di denaro |
|---|---|
| `L4WhatIf.svelte` | **nessuno** |
| `RiskLevelSection.svelte` | **nessuno** |
| `L4Replay.svelte` | `:147` `rowAmount`, `:202` `amount` — **entrambi dietro `!showMoney \|\| …`** |

Con `showMoney={false}` entrambi restituiscono `''`, e `TornadoChart:48` rende l'importo solo
`{#if amount && amount(row)}`. **Nessun euro può comparire.** Passato esplicito benché S4 lo
derivi già da `metadata.scope`, che `service.py:840` popola su **ogni** risultato — la
derivazione è davvero fail-closed, ma un `false` esplicito non va alla deriva se quel campo si sposta.

### 🔴 Due frasi di `L4Replay` parlano ancora come se ci fossero i pesi

Misurato in `stress.py::_historical`:

```
:480  weighted_scope = scope_kind == PORTFOLIO
:483  if weighted_scope … :488 elif scope_kind == ASSET …   →  asset_set CADE FUORI
      ⇒ portfolio_return = None ; excluded_weight_total = 0.0 ; treatment = OMITTED_FROM_REPLAY
```

✅ Il replay **gira** su `asset_set` e rende i rendimenti composti per asset, senza aggregato —
esattamente giusto per una pagina senza pesi.

| | riga | cosa rende | su `asset_set` |
|---|---|---|---|
| 🔴 1 | `L4Replay:198` | `replayTotal`: «…would have ended the period at {percent} {amount}» | `percent='—'` → **«…ended the period at —»** |
| 🔴 2 | `L4Replay:212` | `replayAudit`: «({weight} of the scope, carried at zero return)» | peso **sempre 0.0 %**, e il backend li marca `OMITTED_FROM_REPLAY`, **non** portati a zero |

🔑 **La prima è il difetto contro cui la docstring di S4 stessa argomenta**, sull'altro slot:
*«il `—` … è giusto dentro una card e sbagliato dentro una frase — "…at −12.30% —" si legge come
un numero che non si è caricato, non come uno che non si applica.»* S4 l'ha risolto per
l'**importo** e l'ha lasciato identico sulla **percentuale**, perché su `portfolio`
`portfolio_return` è **sempre** un numero.

⚠️ **E la seconda è la via probabile, non quella rara**: 8 asset su 17 non hanno storia, quindi il
flusso «escluso» è il flusso normale.

**Entrambe sono nel file di S4, che è `FROZEN` e non è mio.** Montaggio consegnato, perdite
**riportate al coordinatore**, non spedite in silenzio.

## ④ I cancelli, sulla revisione fusa — nessuno riusato

| comando | esito |
|---|---|
| `front check` | **0 errori, 41 warning in 2 file** — identico alla baseline presa *prima* di editare; i miei 3 file compaiono **0 volte** |
| `front format` | **3 file riscritti, nessuno mio** (v. sotto) |
| `front format --check` | **exit 0** — «All matched files use Prettier code style!» |
| `front build` | **exit 0** — «Frontend build complete!» |
| `front-portfolio risk-controller-unit` | **PASSED** |
| `front-portfolio risk-levels-unit` | **171 passed** |
| `front-portfolio risk-unit` | **17 passed** (`riskStore.test.ts`, il file auto-fuso) |
| `api risk` | **11 passed** |
| `services risk-all` | **413 passed** |

> ⚠️ L'`exit 1` della prima riga del cancello di tipo era del `grep -c` finale che non trovava
> nulla, **non del cancello**: verificato invece che assunto.

### 🔑 Reperto — `front format` ha una metà rossa, dietro un flag, e il default non ce l'ha

`package.json:14-15` espone **due** comandi:

```
format        prettier --write   ← MUTA, non può mai essere rosso
format:check  prettier --check   ← RIPORTA, può essere rosso
```

`dev.py:604-610`: `--check` è **opt-in**; il default è quello che muta. Ogni mandato (io compreso,
fino a oggi) ha eseguito `front format` nudo → **ripara in silenzio**.

**Conseguenza misurata**: `front format` ha riscritto **tre file che non sono miei** —
`L1HowMuchItHurts.svelte` e `levelHelpers.test.ts` (di S1), `e2e/portfolio/risk-analysis.spec.ts`.
Due sono cosmetici. Il terzo **non è una preferenza di stile**:

```
async function installRiskMocks(…): Promise<RiskRequest[]> {    const requests: RiskRequest[] = [];
```

Un **a-capo mangiato**, con 4 spazi spuri. Tracciato:

| commit | stato |
|---|---|
| `bf34f3a0a` | **pulito** |
| `6aba9e48d` (S1) | **già mangiato** |
| `ff8769520` (S2) | ancora mangiato |
| merge `8dc9be198` | ancora mangiato |

**Ha attraversato due commit e un merge a sei, invisibile**, perché:
- è **TypeScript valido** → nessun compilatore protesta;
- `tsconfig.json:17-19` **esclude `e2e/**/*`** → `front check` è **cieco per costruzione** su quel file;
- e il solo strumento che l'avrebbe visto, `format:check`, **non è il default**.

> 🔑 **È il gemello di R2-100 sull'altro asse.** R2-100: *un cancello esercitato solo sulla metà
> in cui scatta.* Questo: **un cancello il cui default non ha una metà in cui scatta.**
>
> 🔑 **Regola proposta**: *un cancello che ripara non può accumulare prove.* Riparare e riportare
> sono atti diversi: chi ripara in silenzio converte un difetto in un diff che vedrai **solo** se
> il tuo albero era pulito e **solo** se ti capita di leggerlo.

📌 `frontend/tsconfig.e2e.json` **esiste** e — verificato con una ricerca — **nessun cancello lo
usa**. Il reperto del round 1 regge.

### 🔑 Reperto — il cancello distrugge lo stato che il cancello dopo legge

La domanda che S1 mi lascia in eredità («su quali dati?») costa un `count(*)`. Misurata **prima**:

| | prima di `services risk-all` | dopo |
|---|---:|---:|
| assets | 17 | **0** |
| price_history | 2 615 | **0** |
| transactions | 75 | **0** |
| arco v2 | **0,1 s** (pulita ✅) | — |

`services risk-all` fa **`db create-clean`**: rimuove il DB della corsia. È il motivo per cui
l'ordine del coordinatore («`api risk` **prima**, o `db populate --force` in mezzo») esiste — e
ora è **misurato**, non solo obbedito.

> **Terzo membro della famiglia di oggi**: R2-98 *la scheda scrive dopo lo sguardo*;
> qui *il cancello svuota la corsia*. **L'atto di verificare muta ciò che la verifica dopo leggerà.**

⚠️ **Quindi la corsia `6167` è ora VUOTA**: il cancello visivo dovrà ripopolare prima, che è
già la regola del coordinatore.

---

# ⓶ Le due frasi di `L4Replay` — assegnate e riparate

> Assegnazione: *«il file vive in casa tua adesso, il difetto si manifesta solo sulla tua
> superficie, e tu hai la misura»*. Vincoli: riparazione **additiva**, `portfolio` **byte per byte
> invariato e provato**, chiavi nuove **solo se non esistono**.

## Prima le chiavi, perché le prime due volte esistevano già

| cercato | esito |
|---|---|
| `replayExcluded` «Left out:» | **esiste** (`en.json:3351`), già usata a `L4Replay:175` |
| una frase per «omesso / lasciato fuori / non incluso» | **nessuna** — cercata con regex su tutto `en.json` |

⇒ **una** chiave nuova, `replayAuditOmitted`, in **quattro** lingue, col vocabolario già in casa
(`Sostituti/Substituts/Sustitutos`, `Esclusi/Exclus/Excluidos`).

## 🔑 Il difetto vero: la stringa ricodificava come costante un valore che il payload porta

`stress.py:530` mette `"treatment": exclusion_treatment.value` nell'audit, e
`schemas/risk.py:238` lo tipizza per ogni asset escluso. **Il backend dice già quale trattamento
ha applicato.** La frase lo ignorava e ne cablava uno solo.

> **È l'inverso esatto del reperto di ②**: là una costante (`method`) era trattata come
> provenienza; qui **una variabile è trattata come costante**. Stessa confusione, segno opposto.

### Sito 1 — `replayTotal`: la frase si **trattiene**, non si degrada

```svelte
{#if output.portfolio_return != null}
    {@const total = output.portfolio_return}
```

La ragione è quella che la docstring di `showMoney` **già dà per l'importo**: *«un `—` è giusto
dentro una card e sbagliato dentro una frase»*. Una fetta di asset non ha un rendimento di
composizione: non c'è nulla da dire e nulla da scusare, e le barre per-asset **sono** la risposta.

### Sito 2 — `replayAudit`: il predicato chiede se la frase ha un soggetto che mentirebbe

```svelte
{@const omitted = (audit.excluded_assets ?? []).some((item) => item.treatment === 'omitted_from_replay')}
```

**Non** un confronto sullo scope — che sarebbe ri-derivare nel frontend un fatto che il payload
porta, cioè lo stesso errore in un posto nuovo. Con zero esclusioni **non c'è soggetto**, quindi
resta la frase di prima: è ciò che rende il ramo **irraggiungibile su `portfolio`**.

## 🔑 La prova era già in casa, e l'aveva scritta S4

| test | scope | asserzione |
|---|---|---|
| `test_historical_replay_exclusion_preserves_zero_return_residual_weight` `:868` | pesato | `portfolio_return == approx(0.05)` · `treatment == "zero_return_residual"` |
| **`test_historical_replay_asset_set_exclusion_is_omitted_not_zero_weighted`** `:980` | `ASSET_SET` | **`portfolio_return is None`** · **`treatment == "omitted_from_replay"`** |

Entrambi **PASSED** sull'albero riparato (`services risk-all`, 413).

> 🔑 **Il nome del test È la specifica della riparazione.** S4 ha scritto
> `..._is_omitted_not_zero_weighted` — il test asserisce che il backend **non** pesa a zero
> l'esclusione — **e ha lasciato la frase dire «carried at zero return».** Il backend era già
> corretto e già asserito: **solo la frase lo contraddiceva.**
>
> **Quinta volta** che la riparazione giusta era già scritta a poche righe. È la più netta: qui non
> era codice vicino, era **un test il cui nome enuncia il fatto che l'interfaccia negava.**

📌 **E questo è il motivo per cui l'autore non se n'era accorto**: `portfolio` è l'unico scope in
cui `portfolio_return` **non può** mancare (`:488` `else: portfolio_return = 0.0`). *Chi formula la
regola e non l'applica al campo accanto non è distratto: sta guardando l'unico caso in cui il
campo non può mancare.*

## ⚠️ Allargamento di perimetro, dichiarato e non silenzioso

`stress.py:492`: anche lo scope **`ASSET`** non è pesato → `treatment = OMITTED_FROM_REPLAY` e
`excluded_weight_total = 0.0`. **Oggi la pagina dettaglio asset dice la stessa falsità.** Guidare
dal `treatment` invece che da `scope === 'asset_set'` la ripara **anche là**. Mi era stata
assegnata la superficie `asset_set`; il predicato onesto ne copre due. **Dichiarato, non spedito
di nascosto** — e `front-portfolio risk-asset-detail` è «di nessuno», quindi nessuno spec cambia.

## I cancelli

| comando | esito |
|---|---|
| `front check` | **0 errori, 41 warning in 2 file** — identico alla baseline; `L4Replay` **0 volte** |
| `front format --check` | **exit 0** |
| `i18n audit` | **2934 chiavi, Complete 2934, Incomplete 0** |
| `front build` | **exit 0** |
| `front-portfolio risk-levels-unit` | **171 passed** |
| `api risk` (su corsia popolata) | **11 passed** |
| `services risk-all` | **413 passed**, i due test-prova **PASSED** per nome |

✅ **Lo scanner i18n vede le chiavi dentro un ternario**: nessuna delle due compare fra le 122
«unused». Verificato con **controprova** (due chiavi certamente usate si comportano identicamente),
perché «assente dall'elenco» poteva voler dire «non cercata».

## 🔴 Il rosso, e la sua causa: l'eredità di S1 consegnata da un cancello

```
api risk  →  3 failed, 8 passed
  test_risk_query_runs_all_analytics_against_populated_test_database
  test_risk_query_simulates_with_canonical_names_and_no_seed
  test_portfolio_optimization_supports_all_scopes_and_strategies

E  Failed: Test database is not populated: user 'e2e_test_user' is missing.
E  Seed them with: ./dev.py test db populate --force
```

**Nessun file di backend toccato.** Causa: `services risk-all` aveva fatto `db create-clean`.

> 🔑 **Sono gli stessi tre su undici che S1 aveva trovato svuotando il DB apposta.** Lui ha dovuto
> **costruire** lo stato malato per scoprire la dipendenza; a me **l'ha consegnata un cancello**.
> **`services risk-all` lascia la corsia esattamente nello stato che fa diventare rosso `api risk`**:
> l'ordine del coordinatore non è igiene, **è obbligatorio** — sbagliarlo fallisce sempre, non spesso.

✅ **E il messaggio di quei test è la forma giusta**: si rifiutano invece di passare a vuoto, e
**dicono la cura** (`Seed them with: …`), non solo la mancanza.

Dopo `db populate --force`: **11 passed**.

## ⏸ Quello che manca, e perché non l'ho fatto

**Un test di componente su `L4Replay`** che asserisca i due rami (pesato → frase presente + stringa
`replayAudit`; non pesato → frase assente + stringa `replayAuditOmitted`). L'infrastruttura
**esiste** (`$test/component`, `@testing-library/svelte@5.4.2`, `// @vitest-environment jsdom`,
già usata da `DataEditor.test.ts`).

🔴 **Bloccato da una superficie condivisa**: `_frontend_portfolio.py:136` passa a vitest una
**lista esplicita di file**, non un glob. Un file nuovo **non verrebbe mai eseguito** senza una riga
in un file del coordinatore. `dev.py front` non ha un esecutore generico.

> 🔑 **E quella lista esplicita è la quarta cecità della serata**: un test non registrato non è un
> cancello debole, **è un cancello che non esiste** — verde in locale, invisibile a chiunque.

**Chiesto al coordinatore.** Non ho spedito un test che nessun cancello esegue.

## Stato della corsia

```
db populate --force  →  17 asset · 2615 righe · 9 con storia · arco v2 = 0,1 s (PULITA)
porta 6167           →  LIBERA  (il runner spegne il backend condiviso da sé)
```

⚠️ **Ordine provato, non dedotto**: `api risk` → `services risk-all` **svuota** → `db populate
--force` → pronta. Il cancello visivo trova la corsia popolata.

---

# Passo ⓷ — il test di componente di `L4Replay`, e l'azione nuova che lo esegue

✅ **Completato 2026-09-19.**

> **Note implementazione**: scritto con `test-author`, registrato come azione **nuova**
> `risk-levels-component`. Nove test in tre `describe`, entrambi i rami asseriti.

## ⓪ ⚠️ Fuori pista — **la mia affermazione del turno precedente era falsa**

Avevo scritto, e il coordinatore l'aveva adottata:

> ~~«un test non registrato non è un cancello debole, è un cancello che non esiste»~~

**È falsa, e l'ho scoperta andando a misurare la baseline prima di agire.**
`check-orphans` esiste, e fa **due** controlli indipendenti:

```
🔍  ogni file di test è REGISTRATO       →  218 front-unit · 207 backend · 80 e2e
🔍  ogni test registrato è RAGGIUNGIBILE da un'azione 'all'
```

Un file di test che nessuno registra **viene preso**, ed è verde da entrambe le parti.

🔑 **L'affermazione vera è più stretta e più affilata:**

> **La registrazione è imposta da un cancello. La registrazione *veritiera* no.**
> `check-orphans` **conta i file**; non può leggere se il `name` e la `desc` dell'azione
> descrivono ancora ciò che l'azione esegue.

Il coordinatore ha rifiutato `risk-levels-unit` perché la sua `desc` comincia con *«Four-level
pure logic»* e un montaggio in jsdom non è logica pura. **Quel disallineamento non è guardato
da nulla**: l'ha preso **leggendo**. È esattamente la famiglia di difetti che questa campagna
insegue — un nome che smette di descrivere il contenuto — e il cancello che sembrava coprirla
copre l'altra metà.

📌 **E il modo in cui è emersa è lo stesso del reperto su v1**: non l'ho cercata, me l'ha
consegnata la procedura di misurare la baseline **prima** di agire. Due volte in due turni.

## ① L'azione nuova — additiva per costruzione, non per lettura

```
git diff --numstat  scripts/test_runner/_frontend_portfolio.py  →  20    0
                                                                   ^^   ^^
                                                             inserite  cancellate
git diff -U0 … | grep -c '^-[^-]'      →  0
git diff -U0 … | grep 'risk-levels-unit' →  (nessuna riga +/-)
```

**Zero cancellazioni** prova l'additività meglio di qualunque rilettura: la lista a sette file
e la sua `desc` fusa da quattro mandati non possono essere state toccate.

La raggiungibilità da `all` non è dichiarata ma **derivata**: `_common.py:347`
`_get_category_tests_for_all` la ricava dal registro, saltando solo `all` e `in_all=False`.

## ② I tre rami, e il quarto che non avevo chiesto

| caso | `portfolio_return` | `treatment` | atteso |
|---|---|---|---|
| ponderato | `-0.0612` | `zero_return_residual` | totale **presente** · chiave originale |
| **ponderato e piatto** | **`0`** | — | totale **presente** |
| non ponderato | `null` | `omitted_from_replay` | totale **assente** · chiave nuova |
| nessuna esclusione | `-0.0612` | — | chiave originale |
| campo `excluded_assets` assente | `-0.0612` | — | chiave originale (`?? []`) |
| **misto** | `null` | uno e uno | chiave **nuova** (`.some`, non `.every`) |

🔑 **Il caso «ponderato e piatto» non era nel mio brief e lo aggiungo al merito di
`test-author`**: `portfolio_return: 0` passa con `!= null` e **fallirebbe con un controllo di
verità**. Fissa la scelta dell'operatore, non solo il comportamento.

## ③ Il problema i18n, e perché non è risolto asserendo testo

I due rami differiscono **solo per quale chiave rendono**. La regola del progetto vieta di
asserire testo tradotto. La soluzione adottata: **risolvere entrambe le candidate dal catalogo
spedito**, con gli stessi valori, e asserire che il reso **è** l'una e **non è** l'altra.

⚠️ **Il buco che quella coppia da sola avrebbe**: se una chiave sparisse, `svelte-i18n`
ne rieccheggia l'id — e **il componente eccheggerebbe lo stesso id**, quindi i due lati
andrebbero d'accordo. Chiuso da un test d'imbragatura che prova che (a) ogni chiave risolve
a qualcosa di **diverso dal proprio id** e (b) le due **non risolvono uguale**. Quella seconda
asserzione chiude anche il caso della stringa vuota.

## ④ La barriera anti-vacuità

`riskOutput`/`riskMetadata` tornano `null` su un payload che non passa Zod, e un output nullo
**non rende nulla** — momento in cui *«il totale è assente»* è vero **per la ragione sbagliata**.
Ogni caso chiama prima `expectPayloadRendered()`, che asserisce le righe del tornado **in ordine
ordinato** mentre la fixture le dichiara in ordine **inverso**: un payload rieccheggiato
fallirebbe.

## ⑤ 🔑 Il rosso provato mutando il componente, non dichiarato

`test-author` ha temporaneamente rimesso i due difetti (`!= null` → `!== undefined`,
`.some(…)` → `false && .some(…)`) e ha ottenuto **3 falliti su 9**, esattamente i tre
intenzionali. Poi ha ripristinato, con `shasum` uguale prima e dopo.

**Verificato da me, non sulla sua parola:**

```
grep "!== undefined\|false &&"  L4Replay.svelte   →  nessuno ✅
git diff --numstat L4Replay.svelte                →  37  9   (solo la mia riparazione)
:207 {#if output.portfolio_return != null}   :237 {@const omitted = …some(…)}
```

## ⑥ Tre presupposti del **mio** brief trovati falsi da `test-author`

1. **La ragione del `jsdom` non è la stessa** del file gemello. Là toglierlo produce un
   **verde silenzioso** (gli effetti non scattano, i negativi passano a vuoto); qui produce un
   **rosso rumoroso** (`render()` non ha `document`). Documentate entrambe le metà invece di
   ripetere la ragione del vicino.
2. 🔑 **`RiskResultMetadata['historical_replay_audit']` non si può indicizzare.**
   `generated.ts:4797` lo tipizza `(T | null) | Array<T | null>`, quindi
   `NonNullable<…>['excluded_assets']` non compila — uno dei due errori di `front check`.
   **Ed è la ragione per cui il componente chiama `singleValue()` su quel campo.**
   Vale per ogni mandato che scriva fixture di rischio.
3. `InterpolationValues` di `svelte-i18n` esige un index signature implicito: TypeScript lo
   concede a un **type alias** e non a una **interface**. Annotato nel file perché nessuno
   lo «riordini» indietro.

+ derive minori nei numeri di riga che avevo relayato (`stress.py:491` non `~488`; i due test
backend a `:870`/`:981`; `Props` `:26-52`) — nessuna materiale, tutte verificate.

## ⑦ La proposta che `test-author` ha dichiarato invece di spedire

> `data-treatment={omitted ? 'omitted_from_replay' : 'zero_return_residual'}` sul `<p>`
> dell'audit — che già porta due `data-*` — trasformerebbe il confronto di stringhe in uno
> **strutturale**, e servirebbe anche all'E2E.

**Non aggiunto**: esporre un segnale nuovo è una decisione d'interfaccia, non un dettaglio di
test. **Proposta al coordinatore.**

## ⑧ I cancelli, rieseguiti da me sull'albero finale — nessuno riusato

| comando | esito |
|---|---|
| `front-portfolio risk-levels-component` | `Test Files 1 passed (1)` · `Tests 9 passed (9)` · exit **0** |
| `check-orphans` | registrati **218**/218 · raggiungibili **218**/218 · 207 backend · 80 e2e · exit **0** |
| `front check` | **0 errori, 41 warning in 2 file** — identico alla baseline · exit **0** |
| `front format --check` | *All matched files use Prettier code style!* · exit **0** |

✅ **217 → 218**: il numero **sale di esattamente uno**. È la stessa forma di prova che il
cancello dei `DocsLink` impone, e vale qui per la stessa ragione.

📌 **E `front check` ha dato 2 errori sul file nuovo** prima della correzione: è la prova
**empirica** che copre `src/**/*.test.ts`. La cecità è solo `e2e/**`, come misurato al round 1.

---

# Referto di chiusura — i cancelli **rigirati il 21/09**, non ereditati

✅ **Tre giorni dopo il congelamento**, al momento dello stage. Autorizzato dal coordinatore.

> **Note implementazione**: il referto del 19 non era riutilizzabile, e la ragione non è
> prudenziale ma misurabile.

## ① Perché un albero identico non basta

```
L4Replay.test.ts:112   type ExcludedAsset = z.infer<typeof schemas.RiskHistoricalReplayExcludedAsset>;
L4Replay.test.ts:113   type Audit         = z.infer<typeof schemas.RiskHistoricalReplayAudit>;

git ls-files --error-unmatch src/lib/api/generated.ts
  →  error: pathspec … did not match any file(s) known to git
```

> 🔑 **Il test compila contro un file che git non traccia.** Un albero tracciato byte-identico
> **non prova** che il cancello sia ancora verde: parte dell'ingresso è invisibile a `git status`.

**La settima coordinata di provenienza smette di essere una formalità e diventa un vincolo:**
dove un test compila contro `generated.ts`, **un verde non si eredita da un albero pulito —
si rigira.**

## ② I tre cancelli, sulla revisione di oggi

| comando (corsia `6167` · `/tmp/librefolio-r2-s5`) | esito |
|---|---|
| `front-portfolio risk-levels-component` | `Test Files 1 passed (1)` · `Tests 9 passed (9)` · exit **0** |
| `front check` | `svelte-check found 0 errors and 41 warnings in 2 files` · exit **0** |
| `front format --check` | `All matched files use Prettier code style!` · exit **0** |

🔑 **La prova non è «0 errori» due volte** — due esecuzioni possono dire lo stesso numero su
insiemi di warning diversi:

```
cmp  check_final.log (19/09)  ↔  check_d3.log (21/09)   →  IDENTICI byte per byte
     tolte le sole due righe   [DEBUG] loaded svelte.config.js …?ts=<epoch>
```

**Stessi 41 warning, stessi 2 file, stesso ordine. Non «altrettanti»: gli stessi.**

⚠️ **`check-orphans` non rigirato oggi.** L'ha girato il coordinatore in sola lettura:
`218 · 80 · 207`, coincidente con la misura del 19. **Due misure indipendenti, stesso numero** —
dichiarato invece di lasciato dedurre.

## ③ ⚠️ Fuori pista — **lo strumento di misura ha scritto**

```
sqlite3 /tmp/librefolio-r2-s5/librefolio.db "select count(*) …"
  → "no such table: asset"          ← sembrava un DB vuoto
  → il DB vive in  sqlite/app.db :  percorso sbagliato
  → e sqlite3 apre in SCRITTURA  :  ha materializzato un file da 0 byte
```

**Rimosso**; poi reinterrogato con `file:…?mode=ro`, che scrittura non ammette.

> **Quarto membro della famiglia «l'atto di verificare muta ciò che la verifica dopo leggerà»** —
> e **il primo in cui la causa è lo strumento di misura invece del comando misurato.**
> Gli altri tre: `services risk-all` che svuota, la scheda che riscrive dopo lo sguardo,
> il ripopolamento che cancella l'arco.

## ④ La corsia **non è vuota: è scaduta**

```
assets  17    price_history  2615    con storia  9    users  11
v2 (arco di fetched_at)  0,127 s   →  PULITA
max(date)                2026-09-18
```

> 🔑 **Ripopolare non serve perché la corsia è contaminata né perché è vuota: serve perché
> la finestra si è mossa e i dati no.**

Il cancello visivo su questi dati mostrerebbe **tre giorni mancanti in coda che non sono un
difetto del codice** — il tipo esatto di cosa che fa sbagliare un verbale.

## ⑤ Un reperto perso, e dove non va tenuto

`server.log` — l'unica prova della scheda che scrive dopo lo sguardo — **non esiste più.**
Era in `/tmp`, **l'unica directory che garantisce di non conservarlo**; il log applicativo
della corsia ha `0` righe POST e non lo supplisce.

**La conoscenza sopravvive (R2-98 registrata). Il reperto no.** Il coordinatore ha preso il
vincolo a suo nome: un artefatto irriproducibile non va in `/tmp` né nella data dir.

## ⑥ Consegna

**Quattro commit**, divisione accettata per intero:

| # | messaggio | contenuto |
|---|---|---|
| 1 | `S5-prettier-deroga.txt` | i tre file di altri mandati riparati dal cancello — **da solo e per primo** |
| 2 | `S5-asset-global-l4.txt` | `AssetSetReplaySection` (nuovo) · `AssetSetRiskPanel` +2 · `AssetSetCorrelationSection` +15/−68 |
| 3 | `S5-l4replay-scope.txt` | `L4Replay.svelte` +37/−9 · `en/it/fr/es.json` +1 |
| 4 | `S5-l4replay-test.txt` | `L4Replay.test.ts` (nuovo, 376) · `_frontend_portfolio.py` +20/−0 · **questo piano** |

La deroga va **prima** perché i tre successivi nascano su una base già formattata, e **da sola**
perché `git log --follow` su un file di un altro mandato deve rispondere con un soggetto che
**spieghi quel file** — che è la forma di difetto inseguita da due giorni, applicata a sé stessa.

**`FROZEN`.** Porta `6167` libera. Il ripopolamento avverrà **subito prima** del cancello visivo,
che si farà insieme allo sviluppatore, con le sette coordinate e la **scheda chiusa** alla fine.
