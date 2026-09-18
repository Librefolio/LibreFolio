# F2 — piano di esecuzione

| | |
|---|---|
| Mandato | `../F2-primitive-e-contratto.md` ⚠️ **non ancora consegnato** — lavoro dal kickoff |
| Branch | `e-alfy-risk-primitives-cards` |
| Baseline | `2ec19b8f0644eeab3d1b96efa52e6c183a8f807f` ✅ verificata |
| Lane | porta `6152` · data dir `/tmp/librefolio-r2-f2` |
| Coordinatore | sessione `0000738d-b7e0-4561-9454-cf5ab2c439ca` |

> ⚠️ **Questo file è il punto di ripristino.** Il brief è in sola lettura: se deve
> cambiare, lo cambia il coordinatore.

> 📌 **Perché esiste al passo 0 e non alla fine.** Nel round 1 gli otto `*-esecuzione.md`
> furono gli unici file, su dieci alberi, a vivere fuori da git — perché il piano si
> aggiorna *dopo* il passo, quindi nessun checkpoint ne conteneva mai una versione.
> (Verificato: il mio è poi rientrato, 381 righe identiche fra disco e `HEAD`.)
> **Contromisura**: creato prima di qualunque codice, ed elencato esplicitamente in
> ogni handoff invece di sperare che venga raccolto.

---

## Lo scopo, in una riga

`RiskMetricCard` è fatta bene e ha **zero consumatori**, perché il suo contratto sta
dentro il file che nessuno apre. F2 non la ripara: la rende **trovabile** e **disposta**.

---

## Passi

- [x] **0. Piano vivo** — ✅ 2026-09-18
  > **Note implementazione**: creata `implementation_2/progress/` e questo file, prima
  > di qualunque riga di codice.

- [x] **A. Analisi** — ✅ 2026-09-18, consegnata al coordinatore
  > **Note implementazione**: inventario rifatto sul codice, non sul messaggio. Tre
  > scoperte, di cui una che cambia il mandato. Dettaglio in §Scoperte.
  > **Fuori pista**: il brief `F2-primitive-e-contratto.md` **non esiste ancora**.
  > L'analisi nasce dal kickoff + codice e andrà riconciliata quando il brief arriva.

- [x] **1. `RiskCardGrid.svelte`** — ✅ 2026-09-18, disposizione decisa una volta sola
  > **Note implementazione**: `ui/display/RiskCardGrid.svelte` (56 righe) +
  > `RiskCardGrid.test.ts` (7 test). `repeat(auto-fit, minmax(min(${minWidth}, 100%), 1fr))`,
  > `gap-4` fisso, **nessun breakpoint**. Unica prop `minWidth` (default `16rem`):
  > un secondo pomello sarebbe un secondo asse lungo cui cinque superfici divergono.
  > Registrato nel catalogo `scripts/test_runner/_frontend_utility.py` (additivo: un
  > percorso + una clausola nella `desc`).
  >
  > **Sonda d'ambiente prima del test**: jsdom preserva `grid-template-columns`
  > **verbatim**, `min()` annidata compresa. Senza quella verifica le tre asserzioni
  > sullo stile avrebbero potuto testare la stringa vuota.
  >
  > **Non mi sono fidato del verde** (7/7 al primo colpo): due mutazioni, entrambe
  > rosse come previsto — ① tolta `min(…, 100%)` → **3 rossi**; ② tornato a
  > `grid-cols-1 md:grid-cols-3` → **4 rossi**, incluso *«carries no responsive column
  > variant»*. Ripristinato → 7 passed, exit 0.
  >
  > **⚠️ Fuori pista 1 — il catalogo non è un glob.** Il primo giro ha dato
  > **69 file / 1808 test**, *identico* alla baseline: `component-unit` elenca i file
  > **uno per uno**, quindi il mio spec non era stato raccolto. Un conteggio invariato
  > somiglia a «nessuna regressione» e invece significava «non eseguito».
  >
  > **⚠️ Fuori pista 2 — la baseline è ROSSA, e non per causa mia.** Vedi §Baseline rossa.

- [x] **2. `scatterChartHelpers.ts`** — ✅ 2026-09-18, l'aritmetica dello scatter
  > **Note implementazione**: `components/charts/scatterChartHelpers.ts` +
  > `scatterChartHelpers.test.ts` (**23 test**). Entrambi gli assi `type: 'value'` —
  > è l'unica parola che giustifica il file, quindi ha un test suo.
  >
  > **Il raggio va con la RADICE del peso**, perché una bolla si legge per *area*:
  > un raggio lineare farebbe sembrare 16× una posizione 4×. `symbolSizeForWeight`
  > interpola fra `MIN_SYMBOL_PX = 8` e `MAX_SYMBOL_PX = 44` su `√min(1, w)`. Peso
  > assente/non finito/≤ 0 → dimensione base: *«nessun peso fornito»* non è
  > *«posizione di dimensione zero»*.
  >
  > Punti non finiti **scartati, non clampati**, con `droppedCount` restituito: un
  > `NaN` che arriva a ECharts viene saltato in silenzio e l'estensione dell'asse
  > cambia senza che nessuno lo veda.
  >
  > **⚠️ Fuori pista — il catalogo giusto non è `component-unit`.** I test di helper
  > puri stanno in `front_utility_unit` (`core-unit`) accanto agli altri sette
  > `charts/*Helpers.test.ts`; `component-unit` ospita i `.svelte` montati. Baseline
  > di *quella* categoria: **82 file / 2070 test** → ora **83 / 2093** (+1 file,
  > +23 test, nessuna asserzione aggiunta a test esistenti).
  >
  > **Non mi sono fidato del verde**: due mutazioni, entrambe rosse esattamente dove
  > previsto — ① `Math.sqrt` tolto (raggio lineare) → **1 rosso**, *«scales area, not
  > radius, with the weight»*; ② `xAxis.type: 'value'` → `'category'` → **1 rosso**,
  > *«puts both coordinates on a numeric axis, never a category one»*. Ripristinato →
  > 23 passed, exit 0.

- [x] **3. `ScatterChart.svelte`** — ✅ 2026-09-18, il disegno
  > **Note implementazione**: `components/charts/ScatterChart.svelte` sul modello
  > approvato di `CorrelationHeatmap` — `attachChartReady`, `createResizeWatcher`,
  > `scheduleFirstRenderStabilityFix`, `tooltipPositionAboveFinger`,
  > `CHART_ANIMATION_CONFIG` + `CHART_SET_OPTION_OPTS`, `MutationObserver` sul dark.
  > Nessun test proprio: **nessuno dei sei chart in repo ne ha uno**, l'aritmetica è
  > nell'helper. Nessuna dipendenza i18n: `labels` arriva già tradotta dal chiamante,
  > che è anche ciò che mi tiene fuori dal catalogo i18n (non mio).
  >
  > Il contenitore pubblica `data-point-count` e `data-dropped-count` — copiato da
  > `data-asset-order` di `CorrelationHeatmap`: un punto perso per un `NaN` è
  > invisibile dentro una canvas, e un test che non lo vede non può fallirci sopra.
  >
  > **Due difetti trovati rileggendo, non dal compilatore**:
  > ① gli assi avrebbero disegnato le frazioni grezze (`0.1`, non `10.0%`) — il
  > `formatter` sta nel componente, non nell'helper, così i test dell'opzione restano
  > asserzioni su numeri; ② al passaggio *vuoto → pieno → vuoto* l'istanza ECharts
  > restava legata a un nodo staccato dal DOM e il grafico successivo disegnava nel
  > nulla, **senza errori da nessuna parte**: ora si fa `dispose()` sul vuoto.

- [x] **4. `PRIMITIVE.md`** — ✅ 2026-09-18, il deliverable che conta
  > **Note implementazione**: `implementation_2/PRIMITIVE.md`. Quattro domande e
  > nient'altro. **Non sposta** l'intestazione di `RiskMetricCard`: il *perché* resta
  > nel file (è là che serve a chi la modifica), qui c'è il *come adottarla* (è questo
  > che serve a chi la usa). Due sorgenti che dicono la stessa cosa divergono.
  >
  > **⚠️ Fuori pista — due righe dell'inventario erano sbagliate.** ① `currencyFormat`
  > **non è una funzione**, è il modulo: le funzioni sono `formatCurrencyAmountPlain`,
  > `formatCurrencyAmountHtml`, `formatCurrencyCodeHtml`. Chi importasse
  > `{currencyFormat}` importerebbe un simbolo inesistente. ② `utils/currency/index.ts`
  > **non esiste**: il file è `utils/currency/currencyFormat.ts`.
  >
  > Verificati con `ls` **tutti e 14** i percorsi pubblicati, e le **4** pagine docs
  > citate nell'esempio (`volatility`, `correlation`, `conditional-value-at-risk`,
  > `current-drawdown`): esistono tutte. Sarebbe stato il difetto peggiore pubblicare
  > un percorso rotto nella pagina che impone di verificarli.
  >
  > La regola sull'URL dei docs non è asserita ma **mostrata**, col contrasto fra un
  > link che oggi funziona (`user/dashboard/kpi-cards/#card-1-period-pl`) e uno rotto
  > (`user/analysis/risk.md#beta`): stessa riga di codice, due forme, una sola giusta.
  >
  > **⚠️ Fuori pista — ho verificato le esistenze e non le misure, e mi è costato tre
  > cifre sbagliate.** Il coordinatore ha notato che avevo scritto `SingleDatePicker`
  > **389** righe dopo avergli fatto notare **a voce** che erano 388: l'errore è entrato
  > nel documento che esiste per impedire agli errori di propagarsi, **passando per
  > l'unica persona che l'aveva già individuato**. Corretto in **due** punti, non uno.
  >
  > Rileggendo *ogni* cifra ne sono emerse altre due, entrambe mie:
  > ① **`toFixed`**: avevo riportato «16 in repo» dal briefing. Misurati: **26** in
  > `components/risk/`, **164** in `src/lib`+`src/routes`. Nessuno dei due è 16 — il
  > briefing conta un perimetro più stretto che non ho visto. **Non li riconcilio**:
  > scrivo le mie misure col loro perimetro e mando a T4 chi deve agire.
  > ② **«i sei grafici senza spec»**: *giusto nella sostanza, verificabile come falso*.
  > In `components/charts/` ci sono **20** `.svelte` e **due hanno un test**
  > (`ChartSignalsSection`, `MeasurePanel`). Non sono contro-esempi — **non disegnano**.
  > Il discrimine non è la cartella ma `echarts.init`: **sette** componenti lo chiamano,
  > **nessuno** ha uno spec. Riscritto così, e la regola ne esce più netta di prima.
  >
  > 🔑 **Un numero giusto ma verificabile come falso è peggio di uno sbagliato**: chi
  > avesse contato i file nella cartella avrebbe trovato i due contro-esempi e concluso
  > che la regola non vale. La regola per cui questa pagina esiste vale anche per questa
  > pagina — **cita il perimetro insieme alla misura**, perché è lì che si nascondevano
  > tutte e tre.

- **Passo 6ter — il paragrafo diagnostico ratificato, e una verifica che temevo fallisse.**
  Il coordinatore ha deciso di tenere il paragrafo «Un rosso che sembra tuo e non lo è»
  (`PRIMITIVE.md:266-285`), respingendo il mio paragone con `aria-busy`: là si aggiungeva
  **una capacità a un componente** (criterio: coesione), qui **un avvertimento a una guida**
  (criterio: cosa impedisce di sbagliare a chi legge). Regola che ne esce, sua:
  *un vincolo operativo va dove si costruisce anche se duplica il registro — duplicare un
  vincolo non è come duplicare una definizione, perché non ha contenuto proprio da far
  divergere.*

  Verificato che il paragrafo fosse sopravvissuto ai miei edit di audit: **sì, intatto**.
  Ma rileggendolo mi sono accorto che **consegna a cinque mandati un rimedio**, e un rimedio
  sbagliato in una guida è peggio dell'assenza di guida. Due dubbi, misurati invece che
  supposti:

  | dubbio | misura | esito |
  |---|---|---|
  | `api sync` binda una porta? → cinque mandati in collisione di corsia | `dev.py:645` → `api schema` + `api client`; il primo importa l'app **in-process** (`list_api_endpoints.py`), il secondo è codegen **offline** | ❌ **timore infondato**, nessuna porta |
  | il rimedio è completo? | `git check-ignore` su **entrambi**: `generated.ts` **e** `openapi.json` sono ignorati | ⚠️ **è stantia tutta la catena**, non solo l'ultimo anello — il che *rafforza* il paragrafo |

  > **Fuori pista utile**: il paragrafo diceva `dev.py api sync` **nudo**. È l'invocazione
  > contro cui la campagna ha una regola permanente — da un worktree può crearsi un venv
  > vuoto proprio invece di usare quello condiviso. Corretto nella forma canonica, con
  > annotato che **non tocca la corsia** (così nessuno rinvia la rigenerazione credendo di
  > dover chiedere una finestra). Il paragrafo passa da 17 a 25 righe.
  >
- **Passo 6quater — il mio «7» era sbagliato, e la correzione rende la regola molto più forte.**
  Il coordinatore ha misurato il mio numero come io avevo preteso lui misurasse il suo:
  `echarts.init` in `components/charts/` → **6**, in tutto `src/lib` → **14**, io dichiaravo
  **7**. Nessuno dei suoi due. Misurato per **file**, non per occorrenza:

  | misura | perimetro | |
  |---|---|---:|
  | file catturati da `grep -rl echarts.init` | tutto `src/lib` | 17 |
  | occorrenze | tutto `src/lib` | 19 |
  | di cui **solo in un commento** | `echartsDataZoomTouchPan.ts`, `echartsTooltipHelpers.ts` | 2 |
  | **componenti che disegnano davvero** | tutto `src/lib` | **15** |
  | di questi, con uno spec sul `.svelte` | | **0** |

  Da dove veniva il mio 7: `charts/*.svelte` (7, **inclusa la mia `ScatterChart`**) — che
  spiega anche il 6 del coordinatore: ha misurato nel **suo** albero, dove la mia non
  esiste ancora. *Stessa sonda, due alberi, due numeri, ed entrambi corretti nel proprio.*

  > **⚠️ Fuori pista — ho commesso l'errore contro cui stavo scrivendo la regola, nel
  > paragrafo in cui la scrivevo.** Avevo corretto «sei grafici» in «sette» e **il sette
  > era il conteggio di un perimetro che non avevo dichiarato**. Il terzo numero sbagliato
  > e il quarto sono lo stesso numero, sbagliato due volte.

  🔑 **Ma la misura ha trovato una cosa che vale più della correzione.** Dei 17 file, **uno
  solo ha uno spec**: `echartsTooltipHelpers.ts` — e **non è un'eccezione, è la conferma**.
  Non disegna, è aritmetica estratta, ed è testato *proprio per quello*. Cioè:
  **la coppia «disegno non testato + helper testato» che credevo di aver deciso io per
  `ScatterChart` + `scatterChartHelpers` era già la convenzione del repo.**

  Riscritta §3 così: non «la regola che ho deciso», ma «la regola che il repo già segue,
  con il file che sembra violarla e invece la dimostra». Per un mandato di superficie è
  un argomento incomparabilmente più forte. Aggiunte le **tre** trappole di conteggio
  (cartella · occorrenze-vs-file · le 5 che disegnano **fuori** da `charts/`).

- [x] **5. Gate** — ✅ 2026-09-18, in corsia `6152` / `/tmp/librefolio-r2-f2`
  > **Note implementazione**: vedi §Evidenza. Due categorie, non una:
  > `core-unit` **82 → 83 file, 2070 → 2093 test**, exit 0;
  > `component-unit` **69 → 70 file, 1808 → 1815 test**, exit 1 con i **2 rossi
  > pre-esistenti**. **Nessuna asserzione aggiunta a test esistenti.**
  >
  > ⚠️ Il nome `RiskCardGrid` **non compare** nel log di `component-unit`: vitest
  > stampa i falliti e il sommario, non i file passati. La prova che è stato eseguito
  > è il **delta** (+7 test, esattamente i suoi), non il nome nel log.
  >
  > **⚠️ Fuori pista — la categoria non è `front-component`.** Entrambe le azioni
  > stanno sotto `front-utility`: `front-utility core-unit` e
  > `front-utility component-unit`. Il primo tentativo è uscito con **exit 2**
  > (`invalid choice`), non con un rosso di prodotto.

---

## Scoperte dell'analisi

### 🔴 1. `seriesType:'scatter'` non dà uno scatter rischio-rendimento

| evidenza | dove |
|---|---|
| `xAxis: {type:'category', data: dates}`, nessuna prop per cambiarlo | `LineChart:600-602` |
| lo scatter interno converte **data → indice di categoria** (`dates.indexOf(d.date)`) | `LineChart:399` |
| `seriesType` **non è una prop di `LineChart`**: è su `RenderedSignal`, overlay su serie storiche | `charts/signals/ChartSignal.ts:226` |
| §7.5 vuole X=volatilità, Y=rendimento numerici, bolla ∝ peso, CML. **Nessuna data** | `05-grammatica §7.5` |

→ Esporlo darebbe **rombi su una serie storica**. La stessa frase errata è già in
`00-proposta-organizzazione.md:72` — **del coordinatore, non mia**.

Correzione minore alla stessa riga: `seriesType` ha **quattro** modi
(`'line' \| 'area' \| 'bar' \| 'band'`), non tre. Il commento a `LineChart:419` dice
tre e dimentica `area`.

**Materiale riusabile trovato**: `LotWacPriceChart:1146-1173` ha già la **bolla a raggio
variabile** (`symbolSize`/colore per punto, `symbolOffset`, `emphasis`, tooltip per item).
Manca il tipo d'asse e l'idraulica, non l'idioma.

### 🔑 2. Il cancello `check-links` è cieco su metà dei link rotti

| file | forma | visto? |
|---|---|---|
| `L3RiskAdjusted:51,59,74` | `path="…"` quotato | ✅ 3 |
| `L1HowMuchItHurts:56-60` → `:78` | mappa `DOC_PATHS` → `path={DOC_PATHS[row.id]}` | ❌ **3 invisibili** |

Il conto non è «sei»: è **3 presi e 3 mai visti**. Di **T2**.

### ⚠️ 3. I sei link sono sbagliati **due volte**

`user/analysis/` non esiste **e** `.md` è sbagliata: `mkdocs.yml` non imposta
`use_directory_urls` → default `true`, quindi vale l'URL a directory
(✅ `user/dashboard/kpi-cards/#card-1-period-pl`). Le pagine vere sono **una per metrica**
sotto `financial-theory/technical-analysis/risk-metrics/`, non ancore di un `risk.md`.

---

## Decisioni prese (mie, nel mio perimetro)

### La griglia → **componente**, non stringa documentata

~20 griglie distinte già divergenti in `components/risk/`, fra cui
`RiskAnalysisPanel:632` `grid-cols-1 sm:grid-cols-2 xl:grid-cols-5` — **il salto
`1 → sm:2 → xl:5` che l'intestazione della card denuncia, ancora lì.**

> Una stringa documentata **è copia-incolla**: è il meccanismo con cui sono nate quelle
> venti. Cinque mandati che copiano una stringa producono cinque varianti.

Rinforzo tecnico: la card si dimensiona con `@container` (`8cqw`) → la griglia **non deve
enumerare breakpoint**. `repeat(auto-fit, minmax(…,1fr))` non enumera. Il salto era il
*sintomo* dell'enumerazione.

### `PRIMITIVE.md` non *sposta* l'intestazione

L'intestazione risponde a «**perché** è fatta così»; il documento a «**cosa** esiste e
**come** si usa». Duplicare il perché creerebbe due fonti che divergono — il difetto che
sto chiudendo. Si solleva **solo la metà rivolta al chiamante**: props + regola anti-salto.

---

## Domande aperte — bloccano i passi 2 e 3

1. 🔒 **Posso creare `components/charts/ScatterChart.svelte`?** Fuori dal perimetro
   assegnato, ma il criterio di riuscita («S3 monta lo scatter senza costruire un grafico
   nuovo») lo richiede **prima** di S3.
2. `00-proposta:72` lo corregge il coordinatore?
3. K5 va marcato **storico**, con `PRIMITIVE.md` fonte per l'uso?

---

## 🔴 Baseline rossa — `2ec19b8f0`, non causata da F2

`AssetModal.providerLifecycle.test.ts` → **2 test rossi**, una sola causa.

```
save PATCH: captured request must stay immutable:
expected [ { asset_id: 8101, …(15) } ] to strictly equal [ { …(14) } ]
+       "is_benchmark": false,
```

| fatto | evidenza |
|---|---|
| **non è mio codice** | il primo giro girava col catalogo **senza** i miei file; `git status` mostrava solo 3 percorsi **untracked** |
| **è deterministico** | in isolamento: `1 failed \| 1807 skipped`. **Fallisce da solo** → non è ordinamento né parallelismo |
| **causa** | `00d8c735b feat(assets): add benchmark flag and risk taxonomy` aggiunge `is_benchmark` al payload (`AssetModal.svelte:1341,:1479`) |
| **lo spec non lo sa** | `grep -c is_benchmark AssetModal.providerLifecycle.test.ts` → **0** |
| **il 2º rosso è a cascata** | l'assert a `:1033` lancia → il click che farebbe partire `save assignment` non avviene mai → risulta «unconsumed» |

**Non è nel mio perimetro** (`components/assets/`, `routes/(app)/assets/[id]/`, client
generato): riportato, non riparato.

### ⚠️~~Aggiornamento — non è un test stantio. È perdita di dati.~~ **RITIRATA il 2026-09-18**

> 🔴 **Questa diagnosi era SBAGLIATA. La lascio visibile, barrata, perché l'errore
> insegna più della conclusione.** Sotto, prima la catena che avevo costruito, poi
> l'anello che l'ha spezzata.

Avevo concluso che il flag `is_benchmark` venisse **azzerato in silenzio** al salvataggio.
La catena era questa, e **ogni anello dal secondo in poi è tuttora vero**:

| passo | verifica | esito |
|---|---|---|
| il client generato conosce il campo? | `grep -rn is_benchmark frontend/src/lib/api/` | **nessun risultato** ← 🔴 **l'anello falso** |
| lo schema lascia passare gli extra? | `FAinfoResponse` è `z.object({…})` senza `.passthrough()` | no |
| Zodios valida le risposte? | `zodios-client.ts:170` → `validate: 'response'` | sì |
| Zod 3.24.1 scarta davvero? | sonda eseguita | sì, scarta |
| `undefined` diventa un `false` deciso? | `AssetModal.svelte:615` → `=== true` | sì |

**L'anello falso è il primo, e non era falso: era *vecchio*.**

```
il mio albero, allora:  generated.ts  18887 righe · is_benchmark = 0
il mio albero, adesso:  generated.ts  19107 righe · is_benchmark = 11
```

```ts
generated.ts:11729
  is_benchmark: z.boolean()…optional().default(false)   // Zod lo RIEMPIE, non lo scarta
```

`.optional().default(false)` significa *«assente → `false`; presente → quello che arriva»*:
un `true` **sopravvive**. Non c'è nessuna perdita di dati.

### 🔑 Perché non me ne sono accorto, e cosa cambia nel metodo

```
$ git check-ignore -v frontend/src/lib/api/generated.ts
frontend/.gitignore:13
```

**`generated.ts` è ignorato**, quindi non viaggia col merge e **`git status` non può
mostrarlo**. Il coordinatore mi aveva portato a `2ec19b8f0` con un fast-forward pulito,
e il client era rimasto quello di prima. Sei worktree su otto erano nello stesso stato.

> Avevo controllato che **`git status` fosse pulito** e ne avevo dedotto che l'albero
> fosse *aggiornato*. Sono due cose diverse: **`git status` prova l'assenza di modifiche
> tracciate, non l'assenza di differenze.** È la stessa forma dell'osservazione del
> coordinatore — *«un grep prova l'assenza della stringa cercata, non quella della cosa»* —
> e del mio stesso «delta di zero»: **il numero non mentiva, era muto.**
>
> **E la prima diagnosi era giusta, la seconda no, senza che il rigore cambiasse.** La
> sonda su Zod è stata eseguita davvero e ha dato davvero quel risultato: era corretta
> *sul mio albero* e falsa *sul prodotto*. Nel round 1 avevo verificato che l'ambiente
> **sapesse vedere** ciò che mi serviva (jsdom e `grid-template-columns`); qui ho
> verificato tutto **tranne che l'artefatto che stavo leggendo fosse quello corrente**.
>
> **Regola che ne esce** (ora nel registro del coordinatore): *dopo ogni aggiornamento
> di baseline, `api sync` va rieseguito in ogni worktree — un fast-forward pulito non
> basta.* Corollario mio: **prima di diagnosticare su un file generato, misurarne
> l'età, non solo il contenuto.**

### Cosa resta vero

I **due rossi di `component-unit` sono reali**: verificati dal coordinatore nel suo
albero fresco, falliscono anche lì. La **prima** diagnosi regge — lo spec non conosce
`is_benchmark`, 15 chiavi contro 14.

E la riparazione «ovvia» che avevo sconsigliato **è quella giusta**: `AssetModal:1341`
mette `is_benchmark` **subito dopo `active`, incondizionato** — è un booleano sempre
inviato, trattato esattamente come `active`. Col client fresco il valore spedito è
quello vero, quindi aggiungerlo all'atteso non cementa nulla. Riparato dal coordinatore
(2 righe) → 23 passed.

**Verifica finale nel mio albero**, dopo l'`api sync`:

| gate | prima | dopo |
|---|---|---|
| `front check` | exit 1, **2 errori** | ✅ **exit 0, 0 errori, 41 avvisi** — baseline esatta |
| `component-unit` | `2 failed \| 1813 passed` | `2 failed \| 1813 passed` — **invariato** |

Le due metà si separano con precisione: i **2 errori di tipo** erano **solo** il client
stantio e sono spariti; i **2 rossi di test** no, perché la riparazione dello spec è un
file **tracciato** e vive nell'albero del coordinatore — arriverà con la prossima
baseline. *Con un client fresco il test fallisce comunque*, il che è a sua volta la prova
che quel rosso non dipendeva dalla staleness.

> 🔑 **E questo spec è costruito bene, non male.** Asserisce che la richiesta catturata
> resti **strettamente uguale** — uguaglianza esatta, non sottoinsieme. È *per questo*
> che ha visto un campo aggiunto al prodotto. Un matcher parziale sarebbe rimasto verde
> e la deriva sarebbe stata invisibile.
>
> È il **contro-esempio** dell'avvertimento K5 su `resultFor`: là dicevo *«un mock stantio
> non fallisce: rassicura»*. Qui il mock stantio **ha fallito** — perché l'asserzione era
> esatta. La differenza fra i due casi non è la fortuna: è il tipo di confronto.



---

## Evidenza

| Comando | Esito |
|---|---|
| `git rev-parse HEAD` | `2ec19b8f0644eeab3d1b96efa52e6c183a8f807f` ✅ combacia |
| `… front-utility component-unit` *(prima della registrazione)* | ❌ **69 file / 1808 test**, 2 rossi — identico alla baseline: **i miei file non erano raccolti** |
| `… component-unit "saves with pending verification and pending metadata"` | ❌ `1 failed \| 1807 skipped` — **il rosso di baseline fallisce anche da solo** |
| `… component-unit "RiskCardGrid"` | ✅ **`7 passed`** · `1 passed \| 69 skipped (70)` · exit 0 |
| mutazione ① *(tolta `min(…,100%)`)* | ❌ **3 failed** — attesi e ottenuti |
| mutazione ② *(`grid-cols-1 md:grid-cols-3`)* | ❌ **4 failed**, incl. *no responsive column variant* |
| ripristino | ✅ `7 passed`, exit 0 |
| sonda Zod 3.24.1 *(`z.object` + chiave extra)* | `{id, display_name, is_benchmark:true}` → `{"id":1,"display_name":"ETF"}` — **scartata** |
| `… front-utility core-unit "scatterChartHelpers"` | ✅ **`23 passed`** · `1 passed \| 82 skipped (83)` · exit 0 |
| mutazione ③ *(`Math.sqrt` tolto)* | ❌ **1 failed** — *scales area, not radius, with the weight* |
| mutazione ④ *(`xAxis.type` → `'category'`)* | ❌ **1 failed** — *puts both coordinates on a numeric axis…* |
| ripristino | ✅ `23 passed`, exit 0 |
| `npx prettier --write` *(5 file miei)* | 2 riformattati, 3 già conformi · `git status`: **nient'altro toccato** |
| `… front-component component-unit` | ⚠️ **exit 2**, `invalid choice: 'front-component'` — non un rosso di prodotto |
| **`… front-utility core-unit`** *(intero)* | ✅ **`83 passed (83)` file · `2093 passed (2093)` test** · exit 0 |
| **`… front-utility component-unit`** *(intero)* | ⚠️ **`1 failed \| 69 passed (70)`** file · **`2 failed \| 1813 passed (1815)`** — i **2 rossi pre-esistenti** |
| **`dev.py front check`** | ⚠️ **exit 1**, 2 errori · `grep -c` sui miei 3 file nel log → **0** |
| **`dev.py front check`** *(dopo `api sync`, 2026-09-18)* | ✅ **exit 0 · 0 errori · 41 avvisi** — baseline esatta |
| **`… front-utility component-unit`** *(dopo `api sync`)* | ⚠️ `2 failed \| 1813 passed (1815)` — **invariato**: la riparazione dello spec è tracciata e vive nell'albero del coordinatore |
| `wc -l frontend/src/lib/api/generated.ts` | **18887 → 19107** · `is_benchmark`: **0 → 11** |
| `git check-ignore -v …/generated.ts` | `frontend/.gitignore:13` — **invisibile a `git status` per costruzione** |
| `git diff --check` | ✅ pulito |
| `lsof -nP -iTCP:6152 -sTCP:LISTEN` | ✅ **nessun listener** — corsia libera |

### Delta, per categoria

| categoria | baseline | ora | delta |
|---|---|---|---|
| `component-unit` | 69 file / 1808 test | **70 / 1815** | `+1` file, `+7` test *(`RiskCardGrid`)* |
| `core-unit` | 82 file / 2070 test | **83 / 2093** | `+1` file, `+23` test *(`scatterChartHelpers`)* |

**Nessuna asserzione aggiunta a test esistenti.** Nessun test rimosso o rinominato.

> ⚠️ I **2 rossi** di `component-unit` sono **pre-esistenti a F2**: nessuno tocca un file
> mio. I **2 errori** di `front check` erano invece un artefatto del **mio albero stantio**
> e sono spariti con `api sync`. Vedi §Baseline rossa — dove c'è anche la diagnosi che
> avevo sbagliato, lasciata visibile e barrata.

### ⏱️ L'età delle misure — quali numeri misurano quale albero

Il coordinatore ha rigenerato `generated.ts` nel mio albero **alle ~15:20**. Una misura
presa prima di quel momento descrive un albero **diverso** da questo. Dichiarato, non rifatto:

| misura | quando | vale ancora? |
|---|---|---|
| `component-unit` — `70 file / 1815 test`, 2 rossi | **prima** *e* **dopo** | ✅ **rieseguita dopo: numeri identici.** Nessuna riserva |
| `front check` — 2 errori | prima | ❌ **superata**: dopo → `exit 0 · 0 errori · 41 avvisi` |
| `core-unit` — `83 file / 2093 test`, exit 0 | **prima** | ⚠️ **non rieseguita per intero.** I suoi 23 test dello scatter sì — il coordinatore li ha rilanciati dopo la rigenerazione, coi 7 della griglia: **30 passed**. Gli altri 82 file sono helper puri, che non importano il client a runtime: motivo per cui la misura *dovrebbe* reggere — ma «dovrebbe» non è «misurato», e questa riga esiste per non far passare la differenza |
| le 4 mutazioni e i 4 rossi attesi | prima | ✅ indipendenti dal client: mutano codice mio e falliscono su asserzioni mie |

> 📌 La distinzione che rende utile questa tabella non è *vecchio/nuovo*: è
> **«rimisurato» contro «argomentato che non serva rimisurare»**. Il secondo può essere
> ragionevole e restare sbagliato — è *esattamente* così che ho concluso una perdita di
> dati inesistente.

---

## Contratti

| # | Verso | Stato |
|---|---|---|
| `PRIMITIVE.md` | S1 · S2 · S3 · S4 · S5 | ⏳ in lavorazione |
