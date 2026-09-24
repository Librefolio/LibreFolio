# Piano d'implementazione — U2 / SP15 privacy globale, Round 2: correzioni dalla review d'uso

← Previous:
[Round 1 — nucleo di mascheramento](plan-phase00PrivacyGlobalRound1-MaskingCore.prompt.md)

Piano gemello, stesso round di review:
[Onboarding Round 8 — correzioni dalla review d'uso](../21_onboarding/plan-phase00OnboardingRound8-PostReview.prompt.md)

Fonti:
[review d'uso 22/09](../09_feedbackJobs/08_review_visiva_20260922.md) ·
[reperti dell'analisi statica](../09_feedbackJobs/09_reperti_analisi_statica_20260922.md) ·
[backlog P4](../09_feedbackJobs/00_backlog_strutturale_P4.md) (P4-10, P4-11)

## Confine e autorizzazione

| | |
|---|---|
| **Workstream** | J — privacy e onboarding |
| **Worktree** | `e-alfy-literate-lamp`, branch `e-alfy-onboarding-foundation` |
| **Baseline** | `f1047f766` (`fix(db): widen enum columns to VARCHAR(32)`), verificata 2026-09-23 10:33, albero pulito |
| **Lane copia prod** | porta `6168`, `/tmp/librefolio-r2-j-onboarding-prodcopy`, **solo dalla snapshot** `/tmp/librefolio-r2-prod-snapshot` |
| **Lane suite** | porta `6158`, `/tmp/librefolio-r2-j-onboarding` — **solo** `dev.py test …` |
| **Coordinator** | `c8328a01-f208-4ade-a352-0486d1f14de2` |

**Autorizzazione developer verbatim, 2026-09-23:** `Plan approved! Exited plan mode.`

**Decisione developer verbatim su Q1, 2026-09-23:**
*«Mascherate solo dove si affiancano a un prezzo (posizioni, lotti), visibili nelle transazioni»*.

**Decisioni di perimetro del developer (22/09), vincolanti:**

1. *«Il patrimonio entra in gioco quando da quel numero si riesce a risalire a quanto possiede
   l'utente, e generalmente quindi ha a che fare con le transazioni e le quantità possedute.»*
   Un prezzo di mercato **non** è patrimonio.
2. Il **WAC** è ammissibile; il **numero di movimenti** in Asset è mostrabile.
3. *«Il privacy deve nascondere il numero, non la valuta, quindi se lo fa è un errore.»*

Nessuna migrazione. Nessuna chiave i18n rimossa. Nessun `git commit`/`merge`/`rebase`/`push`.

## Premesse corrette prima di scrivere

Misurate durante l'analisi del 2026-09-23 e **accolte dal coordinator**:

- **08 §3.2 / 09 §9.2** (*«la privacy non nasconde la valuta — già corretto»*): vero per le
  primitive D8 di `currencyFormat.ts`, falso per i **soli due** siti che le aggirano, entrambi
  miei: `riskAnalysisHelpers.ts:160` e `LotComparisonChart.svelte:261`.
- **09 §1.3 Dual View asimmetrica** (voce mia): non è un difetto. `AssetTable.svelte:211` passa
  `{sensitivity: 'public'}`; il mio «2 chiamate mascherate» contava la riga di `import`.
- **09 §1.5 «4 patrimonio su 9»** (voce mia): con i criteri del developer, **0 difetti su 9** —
  3 quotazioni (1) · 2 fallback WAC (2) · 2 `CompactCashCell` che sono un `<input
  value={amountStr}>` (D7, regola mia del Round 1) · 2 importi di **eventi asset** (`models.py`:
  *«Events are NOT transactions — they describe what happens to the asset globally»*).

## Inventario

| # | difetto | causa | file | scrittore |
|---|---|---|---|---|
| ③a | rischio: `•••` **senza valuta** | `riskAnalysisHelpers.ts:160` ritorna il segnaposto nudo; pinnato di proposito a `.test.ts:387` (*«the currency labels the column, not the cell»*, scelta del Round 1 che la decisione 3 rovescia) | `riskAnalysisHelpers.ts` + `.test.ts` | **J**, unico per tutto il round (file interi) |
| ③a′ | rischio: segno nascosto | `.test.ts:379` *«hides the sign of a loss»*, senza motivazione scritta; D8 tiene il segno fuori | idem | J — Q7 |
| ③b | lotti: `•••` senza valuta | `LotComparisonChart.svelte:261` | `LotComparisonChart.svelte` | **J**, unico per `:261` |
| R20 | Broker globale non si riscopre | ignota — ipotesi H1/H2 sotto | `BrokerCard.svelte`, `brokers/+page.svelte` | J (nessun owner attivo) |
| R5/R6/R7 | Growth: asse Y (`eur`, `pnl`, `income`, `candles`) e tooltip | `yAxisFormatter:1815`, `axisLabel:2051`, `fmtCurrency:1834` | `GrowthChart.svelte` | **I** — J fa review |
| R5b | Performance: P&L netto e asse valori | `shortMoney:161` → `netValueText:234`; `axisTickAmount:170` | `PerformanceChart.svelte` | **I** — J fa review |
| D5′ | quantità in posizioni e lotti | la regola D5 le lasciava visibili | 5 file, §Passo 7 | **J**, unico scrittore per il round (coordinator, 2026-09-24) |

**R20 — ipotesi e osservazione che le separa.** `BrokerCard` e `brokers/+page.svelte` sono
entrambi in **modalità legacy** (`export let`, `$:` ×2, zero rune); la catena `{@html}` →
`maskable` → `$state` è reattiva nei due versi *sulla carta*, e il §9.1 del foglio 09 insegna
che è proprio il ciclo di vita dello stato ciò che la rilettura non vede.

| ipotesi | predizione |
|---|---|
| H1 — il template legacy non ridipinge al toggle | `/brokers` caricata con privacy **off**, toggle **on** sul posto: **non** nasconde. L'«occultamento» visto era al montaggio |
| H2 — guasto locale a un solo verso | on sul posto nasconde, off sul posto no |
| controllo | `brokers/[id]/+page.svelte:606,777` è legacy con la stessa forma: se lì il ritorno funziona, H1 è falsa |

Già falsificate: `scrollOnOverflow` (sta sul nome, `:107`); cache nel formatter (nessuna).

## Decisioni

| Q | decisione | fonte |
|---|---|---|
| Q1 | **D5′**: quantità mascherate dove si affiancano a un prezzo (posizioni, lotti), visibili nelle transazioni | developer, verbatim sopra |
| Q3 | asse di valore sotto privacy: tacche → `•••` | default approvato |
| Q4 | AI Export fuori perimetro per D4 («export grezzi») | default approvato |
| Q7 | il formatter del rischio mascherato mostra il **segno**, come D8 | default approvato |
| Q8 | cella lotto «aperta / originale» sotto privacy → `••• (60 %)` | default approvato |

⚠️ **Residuo accettato da D5′**: in Transazioni quantità × prezzo resta ricostruibile. È una
scelta del developer, non una svista.

## Passi

Ogni passo aggiorna questo file dopo il completamento: stato con data, `Note implementazione`,
`Fuori pista` per ogni deviazione, comando ed evidenza.

### Passo 1 — Piano durevole — **Stato: ✅ fatto** — 2026-09-23

Questo file, il gemello onboarding, cross-link dal Round 1 (§5) e dal Round 7 onboarding.

> **Note implementazione.** Scritti questo piano e
> `21_onboarding/plan-phase00OnboardingRound8-PostReview.prompt.md`; aggiunto `→ Follow-up` nel
> §5 del Round 1 e in testa al Round 7. Verifica: ogni link relativo dei quattro file risolve
> (5 + 4 + 3 + 3 link, 0 rotti); nessun titolo senza riga vuota prima.

### Passo 2 — Gate-prep — **Stato: ✅ fatto** — 2026-09-24 — *checkpoint C0*

`moneyRenderSites.test.ts`:

- il test *«sees both branches of a two-branch money line»* usa `PerformanceChart` come
  **esemplare**. Quando I la maschera con `maskable(`, la riga entra in `SAFE_CALL`, smette di
  essere un hit, e il controllo positivo perde il soggetto: il ramo di I non resterebbe verde.
  Il test passa su una **fixture sintetica**, estraendo dallo scanner la logica per riga;
- nuovo stato `public`, allineato a `AmountSensitivity`; `EventCreateMiniModal` da `unmasked` a
  `public` (importo di un evento asset).

Con questo integrato, I tocca soltanto le sue 4 voci (da **cancellare**: una riga con `maskable(`
non è più un hit) e le due liste letterali `residual` / `unmasked`.

> **⚠️ Fuori pista — perimetro modificato dal coordinator, 2026-09-23.** (1) Il gate-prep è il
> **checkpoint C0, da solo**: il primo commit dopo `f1047f766`, con dentro soltanto
> `moneyRenderSites.test.ts` e le righe di registrazione nel runner; I lo riceve con un merge del
> **commit** C0, non della punta del ramo. I file del journal restano fuori da C0. (2) La
> registrazione dei 5 test privacy orfani nel runner è **a carico mio**, dentro C0: se la facesse
> il coordinator all'integrazione, nel ramo di I il gate resterebbe fuori dal runner fino a fine
> round. (3) D13 di I: la voce `GrowthChart:1899` resta un hit (il gate non segue una closure
> locale) e passerà da `residual` a `masked` nel commit di I, con una `why` che cita la
> definizione mascherata e il test di I che la blocca; I cancella quindi **3** voci, non 4.
> (4) I cinque file di D5′ sono assegnati a J come unico scrittore.

> **Note implementazione — registrazione nel runner (C0).** `scripts/test_runner/_frontend_utility.py`,
> azione `front-utility core-unit` (Vitest in **node**: i 5 file non dichiarano
> `@vitest-environment`, e il default di `vitest.config.ts` è node): +5 righe, ciascuna accanto ai
> vicini della stessa cartella, nulla riordinato, la riga `desc` **non** toccata (è una sola riga di
> ~2000 caratteri che altri workstream allungano: aggiungerci testo garantirebbe un conflitto).
> Un'azione registrata gira per costruzione nel `all` della categoria (`_get_category_tests_for_all`).
> Evidenza: elenco `core-unit` 94 percorsi, 0 inesistenti, 0 duplicati; `check-orphans` nella lane
> 6158 → exit 0, 242/242 registrati e raggiungibili da `all`. **Controllo positivo**: la stessa
> regola ricalcolata sul catalogo di `HEAD` dà **5 orfani, esattamente i 5 file privacy** → ora 0.

> **Note implementazione — gate (C0), 2026-09-24.** Scritto via `test-author`, riletto e rieseguito
> da me. `moneyRenderSites.test.ts` +62/−18: `scanLine()` estratta da `scan()` senza cambiare
> semantica (dump degli hit prima/dopo identico, sha256 `7881aac8…`, misurato dall'agente); il test
> dei due rami gira su una fixture sintetica di `PerformanceChart.shortMoney` attraverso la stessa
> `scanLine`; stato `public` con `EventCreateMiniModal` riclassificata; liste `residual`,
> `unmasked`, `public` un elemento per riga, tenute spezzate da un commento di riga (0
> `prettier-ignore` nel repo, e resta 0). Evidenza, eseguita da me:
>
> | comando | esito |
> |---|---|
> | `npx vitest run …/moneyRenderSites.test.ts` | `Test Files 1 passed (1)`, `Tests 6 passed (6)` |
> | suite privacy, 6 percorsi | `Test Files 6 passed (6)`, `Tests 126 passed (126)` |
> | controllo negativo su **copia** con `CURRENCY_TOKEN = /currency/i` | 3 rossi: i due rami, controllo positivo, marcio. Copia rimossa, file vero con sha invariato |
> | `dev.py test --test-port 6158 --data-dir /tmp/librefolio-r2-j-onboarding front-utility core-unit "money rendered outside the masking channel"` | exit 0 · `Test Files 1 passed \| 93 skipped (94)` · `Tests 6 passed \| 2433 skipped (2439)` |
> | `npx prettier --check`, `git diff --check` sui due file di C0 | puliti, exit 0 |
>
> Il controllo negativo mostra anche una cosa da tenere a mente: oggi il restringimento fa cadere
> **tre** test perché la riga vera di `PerformanceChart` è ancora sul disco. Quando I la maschera,
> il test della fixture resta **l'unico** a vedere la regressione — che è la ragione del passo.

> **⚠️ Fuori pista — `core-unit` senza filtro è rosso, e non per C0.** Stesso comando senza il
> filtro di nome: exit 1, `Test Files 2 failed | 92 passed (94)`, `Tests 33 failed | 2406 passed`.
> I due file rossi sono `components/risk/assetSetLevels.test.ts` (26) e
> `features/tools/registry.test.ts` (7), entrambi già nell'elenco a `HEAD`, nessuno dei due importa
> un file di C0. Causa misurata: il client generato di questa worktree è del **22/09 00:02**
> (ignorato da git, `generated.ts` sha `f2d51864cd7b`) e non contiene né
> `RiskAssetSetVarCvarOutput` (backend `d3afb92b6`, 0 occorrenze) né il contratto
> `pac_allocator 2.0.0` (0 occorrenze in `tool-contract-map.generated.ts`) — gli errori lo dicono
> alla lettera: *«the compiled pac_allocator 2.0.0 contract must be generated»*, e `schema`
> `undefined` in `riskOutput`. È la trappola dell'artefatto derivato scaduto (09 §3.1). Rimedio:
> `dev.py api sync`, statico; **non eseguito** in attesa dell'OK del coordinator.
>
> **⚠️ Fuori pista — errore mio di invocazione.** Il primo lancio con `--verbose` è uscito con
> exit 2 da argparse, prima della raccolta: nessun test, nessun DB, nessuna porta. Il verbose è già
> il default (`-q` lo spegne).

> **Note implementazione — C0 committato `2a5927c48` (genitore `f1047f766`), 2026-09-24 10:02.**
> Poi `dev.py api sync` con l'OK del coordinator: exit 0, nessuna porta aperta (6158/6168 libere
> dopo), `git status` **identico** prima e dopo (confronto con `cmp`), tre file ignorati
> rigenerati (`generated.ts` `f2d51864cd7b` → `a085da1c8dac`). `RiskAssetSetVarCvarOutput`: 0 → 6
> occorrenze. `core-unit` senza filtro, lane 6158: exit 0, **`Test Files 94 passed (94)`,
> `Tests 2439 passed (2439)`** — i 33 rossi erano tutti del client scaduto.
>
> **⚠️ Fuori pista — una delle due prove di C0 era cieca.** Per il contratto `pac_allocator 2.0.0`
> avevo dichiarato «0 occorrenze» con un grep su riga singola; nel file le chiavi stanno su righe
> diverse (`"pac_allocator": {` / `"2.0.0": {`), e sul client **nuovo**, dove il contratto c'è, lo
> stesso grep dà ancora 0. Quel grep non poteva trovarlo in nessun caso: non provava nulla. La
> conclusione regge per un'altra via — il test stesso diceva *«the compiled pac_allocator 2.0.0
> contract must be generated»*, ed è verde dopo il sync — ma la misura che avevo messo accanto era
> una sonda senza controllo positivo. Il file vecchio è sovrascritto e non si può rimisurare.

### Passo 3 — Primitiva `maskCurrencyParts` — **Stato: ✅ fatto** — 2026-09-24 — *C1*

In `utils/privacy/maskable.ts`: riceve le parti di `Intl.NumberFormat#formatToParts` e sostituisce
la corsa numerica (`integer`, `group`, `decimal`, `fraction`, `compact`, `exponent*`) con **un**
segnaposto; conserva `currency`, `literal`, `minusSign`, `plusSign`. `compact` sta dentro la
maschera: `€•••K` rivelerebbe l'ordine di grandezza. Serve ai soli formatter `Intl` con
`style: 'currency'`; a I bastano `maskable()` e le primitive D8.

> **Note implementazione.** `maskable.ts`: `MAGNITUDE_PARTS` e `maskCurrencyParts(parts,
> sensitivity?)`. La corsa va dalla prima all'ultima parte di grandezza e include i `literal`
> interni, perché il compatto tedesco è `1,2 Mio. €` — `integer`, `decimal`, `fraction`,
> `literal`, `compact`, `literal`, `currency` — e mascherare solo le parti numeriche lascerebbe
> un doppio spazio. Misurato con `formatToParts` su sei casi prima di scrivere: `en-US` → `-$•••`,
> `it-IT` → `••• €`, `de-DE` compatto → `••• €`, `en-US` compatto → `-$•••`, `fr-FR` CHF →
> `-••• CHF`, `ja-JP` → `￥•••`. Una parte `currency` dentro la corsa viene conservata: per
> nessuna locale misurata succede, ma se succedesse perderla violerebbe la decisione 3.

### Passo 4 — ③a rischio — **Stato: ✅ fatto** — 2026-09-24 — *C1*

`riskAnalysisHelpers.ts:160` via primitiva. Test: invertire `:387` (valuta presente, USD e EUR
mascherati diversi) e `:379` (segno presente, Q7); aggiornare le asserzioni a `:330…:402`.
Gate: contratto Risk + suite privacy, `Test Files N` = N. **Poi avvisare il coordinator**: il pin
privacy di F su `risk-lab` dipende da questo output.

> **Note implementazione.** `formatCurrencyAmount` → `maskCurrencyParts(…formatToParts(amount))`
> dopo i due controlli di assenza invariati; import ridotto a `maskCurrencyParts` (0 residui di
> `PRIVACY_PLACEHOLDER` / `shouldMaskAmount` nel file, nessun re-export). Docstring: la vecchia
> ragione (*«the currency labels the column»*) è citata come superata dalla regola del developer.
> Rossi attesi dopo il cambio, misurati: **7**, tutti nel blocco privacy. Due hanno un nome che
> non torna — *«still says em-dash…»* — e ho letto perché cadono invece di presumerlo: le
> asserzioni sull'assenza passano, cade il **controllo positivo** in fondo, che si aspettava `•••`
> e riceve `$•••`. Test riscritti via `test-author`.

### Passo 5 — ③b lotti — **Stato: ✅ fatto** — 2026-09-24 — *C1*

`LotComparisonChart.svelte:261` via primitiva, e il ramo `catch` con il segno fuori dalla maschera.

> **Note implementazione.** Il formatter è uscito dal componente: `formatAxisCurrency(value,
> currency, locale?)` in `lotComparisonChartHelpers.ts`, accanto a `formatAxisPercent`, così il
> ramo `catch` si prova in node con un codice valuta invalido (`'EURO'` → `RangeError`). Le due
> uscite si mascherano ciascuna per sé: `Intl` con `maskCurrencyParts`, il fallback con
> `maskable` sul solo numero e il codice fuori. Il controllo unico al confine della funzione, che
> nel Round 1 copriva entrambe le uscite, restituiva il segnaposto nudo: era la forma della
> violazione. Il componente tiene un wrapper di una riga. Registro del gate aggiornato: voce
> `riskAnalysisHelpers` con lo snippet nuovo, voce di forma A spostata su
> `lotComparisonChartHelpers.ts`, voce del `catch` **cancellata** (la riga contiene `maskable(`,
> quindi `SAFE_CALL` la salta: non è più un hit). Gate 6/6, `REGISTRY` 9 = hit 9.

> **⚠️ Fuori pista — un buco nuovo nello stesso grafico: l'asse del modo valore.** Il formatter
> dell'asse Y (`:1241` a `HEAD`), in modo `value`, usava `formatAxisNumber(value)`: il **valore
> dei lotti**, cioè
> patrimonio, in chiaro sotto privacy. È la classe di R5 in un file mio. Né il gate né la mia rete
> larga del 22/09 potevano vederlo: nessun token di valuta sulla riga, e nessun identificatore di
> denaro. Aggiunto `formatAxisAmount(value, locale?)`, mascherato con il segno fuori (Q3: tacche →
> `•••`). Trovato leggendo la riga che chiamava il formatter che stavo cambiando, non da una
> ricerca: *una verifica che non trova ciò che cercava può trovare ciò che nessuno cercava*.

> **⚠️ Fuori pista — il toggle non ridisegnava l'asse.** ECharts chiama i formatter d'asse fuori
> dall'effect di render, quindi la lettura del flag non era tracciata: a privacy cambiata l'asse
> restava com'era fino al rebuild successivo (il limite §3.4 del Round 1). L'effect elenca le sue
> dipendenze con `void …`: aggiunto `void isPrivacyEnabled();`. Una riga, con il commento sul
> perché.
>
> Perimetro: il coordinator mi ha assegnato `:261`; queste modifiche stanno nello stesso grafico
> (`:1241`, l'effect, gli import) e in `lotComparisonChartHelpers.ts`, fermo dal 30/08 e senza
> owner. Dichiarato nell'handoff.

> **⚠️ Fuori pista — una regressione mia, trovata dal `test-author`: il segno.** La prima
> versione dei due helper ricostruiva il segno come `'-'` ASCII davanti al valore assoluto. Così
> cambiava anche l'output **non mascherato**: `formatAxisNumber` scrive il meno come lo scrive la
> locale. Misurato con `formatToParts(-1234)`: U+2212 in `sv-SE`, `fi-FI` e `fa-IR`, e in `ar`,
> `he-IL` e `fa-IR` il meno viene **dopo** un segno bidi (parte 1 di 5, non 0). Nuova primitiva
> `maskFormattedNumber(formatted)` in `maskable.ts`: non mascherato restituisce la stringa
> invariata; mascherato tiene la corsa iniziale `/^[\p{Cf}+\-\u2212]*/u` (segno e marcature bidi,
> esattamente come le ha scritte la locale) e sostituisce il resto con un solo segnaposto. I due
> helper la usano; l'output non mascherato torna identico byte per byte a `formatAxisNumber`.
> `maskFormattedNumber\(` entra in `SAFE_CALL`: è un export fissato da test che si romperebbero
> togliendo la maschera, il prezzo che la docstring di `SAFE_CALL` chiede.

> **Limite dichiarato — `maskCurrencyParts` in `pt-CV`.** Misurato con `formatToParts(1234.56)`:
> `integer 1234` · `decimal "$"` · `fraction 56` · `literal U+00A0` · `currency U+200B`. ICU tipizza
> come **separatore decimale** il segno dell'escudo, e la parte `currency` è uno spazio a larghezza
> zero. Mascherata, la cifra perde quindi l'unico simbolo visibile. È un caso limite dei dati CLDR,
> non fissato da test; lo scrivo perché chi lo incontra non lo scambi per un difetto della regola.

> **Note implementazione — evidenza dei passi 3–5 (C1), 2026-09-24.** Test scritti via
> `test-author` in due giri, rieseguiti da me:
>
> | comando | esito |
> |---|---|
> | set di 8 percorsi (6 privacy + `lotComparisonChartHelpers` + `lotChartShared`) | `Test Files 8 passed (8)` · `Tests 241 passed (241)` |
> | contratto Risk, `riskAnalysisHelpers.test.ts` | **78** prima e dopo: nessun test aggiunto o tolto, 3 rinominati, 7 riscritti al contratto nuovo |
> | `maskable.test.ts` · `lotComparisonChartHelpers.test.ts` | 11 → 27 · 70 → 80 |
> | controlli negativi dell'agente (primitiva riportata al segnaposto nudo, poi ripristinata con sha identico) | 18 rossi, poi 8 rossi, tutti nominati |
> | `dev.py test … front-utility core-unit`, lane 6158, senza filtro | exit 0 · `Test Files 94 passed (94)` · `Tests 2465 passed (2465)` = 2439 + 16 + 10, come previsto |
> | gate | 6/6, `REGISTRY` 9 = hit 9 |
> | `dev.py front check` (client `generated.ts` `a085da1c8dac`, 09-24 10:02) | `3 errors and 41 warnings in 4 files` = il pavimento noto; per nome: errori in `TransactionFormModal.test.ts:787,819` e `ToolExecutionMetrics.svelte:44`, warning in `BrokerSharingPanel` e `GlobalSettingsTab`. **Nessuno** dei 4 file è nel mio delta |
> | prettier, `git diff --check` | puliti |
>
> **Non coperto da un test automatico, dichiarato:** il cablaggio di `LotComparisonChart.svelte`
> (wrapper con `currency`, asse del modo valore, `void isPrivacyEnabled()` nell'effect). Nessun test
> unitario, di componente o E2E monta quel grafico: le occorrenze trovate sono commenti e la
> galleria della doc. Lo coprono `svelte-check` pulito, la review manuale sulla copia prod e l'E2E
> privacy del passo 9.
>
> Anche `currencyFormat.test.ts` è cambiato, solo nel commento che dichiarava l'asimmetria con il
> rischio e i lotti *«da non armonizzare»*: la regola del developer l'ha armonizzata, e il
> commento l'ha trovato il `test-author`.

### Passo 6 — R20 — **Stato: ✅ fatto** — 2026-09-24 — *C2*

Prima un test di componente su `BrokerCard` (off→on→off, e montaggio con privacy attiva poi off):
è insieme la sonda che separa H1 da H2 e la regressione. Poi la riproduzione sulla copia prod,
con il controllo di `brokers/[id]`. Il fix si decide dopo la misura, non prima.

> **Note implementazione — la misura, prima del fix.**
>
> **Dal vivo**, copia prod su 6168 (`v1.1.0-230-g176f19707`), sonda Playwright usa-e-getta, login
> `alfy`, letture del DOM a 400 ms e 2 s da ogni click:
>
> | scenario | esito |
> |---|---|
> | `/brokers`, privacy **spenta** al caricamento | `aria-pressed` commuta, **le cifre restano in chiaro** (`<importo>`, `<importo>`, …) |
> | `/brokers`, privacy **accesa** al caricamento | `aria-pressed` commuta, **`•••` resta** |
> | `/brokers/2`, importo della pagina (controllo) | `0.00` fisso in entrambi gli stati |
>
> 🔴 **Più grave di come è stato riportato.** Le card non reagiscono **mai**: decide lo stato al
> montaggio. *«Si nascondono ma non si riscoprono»* era il percorso di chi arriva con la privacy già
> accesa; nel verso opposto — accendere la privacy sulla pagina — **i dati restano visibili**. E il
> «controllo» non era un controllo: anche gli importi propri della pagina di dettaglio (`:606`
> saldi, `:777` totale) sono congelati; il developer ha visto funzionare le **tabelle figlie**, che
> sono componenti runes.
>
> **In jsdom**, `BrokerCard.test.ts` via `test-author`, tre test: **3 rossi**, tutti nel componente,
> con i controlli positivi verdi (`isPrivacyEnabled()` e una chiamata fresca del formatter seguivano il
> flag). Il `test-author` ha trovato il meccanismo **compilando** il componente con `svelte/compiler`
> 5.48.0: in modalità legacy una chiamata dentro un'espressione del template diventa
> `$.untrack(() => formatCurrencyAmountHtml(…))`, e si tracciano solo i valori nominati
> (`$.deep_read_state(summary())`). Il flag letto dentro `maskable` non viene mai tracciato.
>
> **Perimetro misurato**: fra i componenti che chiamano un formatter mascherato, classificati per uso
> reale delle rune e non per `export let`, i legacy sono **esattamente due** — `BrokerCard.svelte`
> (3 siti) e `brokers/[id]/+page.svelte` (2 siti). Nessun `runes: true` a livello di compilatore.
>
> **Fix**: `ui/display/CurrencyAmount.svelte`, componente runes di una riga di template che rende
> l'importo con `formatCurrencyAmountHtml`; i 5 siti legacy lo usano. Migrare a runes una pagina di
> 830 righe con 12 `$:` per due importi sarebbe stato sproporzionato. **`BrokerCard.test.ts`,
> invariato, passa da 3 rossi a 3/3.**

> **Note implementazione — evidenza dopo il fix.**
>
> **Dal vivo, stessa sonda e stessa copia**, server riavviato con la build delle 11:24
> (`v1.1.0-230-g176f19707-dirty`, cioè con C2):
>
> | scenario | prima | dopo |
> |---|---|---|
> | `/brokers`, privacy spenta al caricamento, tre click | cifre sempre in chiaro | `•••` → cifre → `•••` |
> | `/brokers`, privacy accesa al caricamento, tre click | `•••` sempre | cifre → `•••` → cifre |
> | `/brokers/2`, importo della pagina | `0.00` fisso | `•••` → `0.00` → `•••` |
>
> Ogni lettura a 400 ms dal click. `+•••` sul guadagno: il segno resta fuori per D8.
>
> **Test** (via `test-author`, rieseguiti da me): `BrokerCard.test.ts` 3; `CurrencyAmount.test.ts` 6,
> montato **dentro un genitore legacy** (`__tests__/harness/CurrencyAmountLegacyHost.svelte`, legacy
> per costruzione: il compilatore rifiuta `export let` in modalità runes), che rende anche la vecchia
> chiamata inline come controllo congelato. Controllo negativo: `untrack(…)` dentro `CurrencyAmount`
> → 8 rossi nominati, ripristino con sha identico.
>
> | comando | esito |
> |---|---|
> | set di 7 file (i 6 di C2 + gate) | `Test Files 7 passed (7)` · `Tests 85 passed (85)` |
> | `check-orphans`, lane 6158 | 245/245 registrati e raggiungibili da `all` |
> | `front-utility component-unit` | exit 0 · `76 passed (76)` · `2008 passed` |
> | `front-utility onboarding-component-unit` | exit 0 · `13 passed (13)` · `400 passed` |
> | `front-utility core-unit` | exit 0 · `94 passed (94)` · `2465 passed`, invariato da C1 |
> | `dev.py front check` (client `a085da1c8dac`) | `3 errors and 41 warnings in 4 files`, gli stessi 4 file; **nessuno** nel mio delta |
>
> Runner: `BrokerCard.test.ts` e `CurrencyAmount.test.ts` in `component-unit`,
> `DeferredAppPopups.test.ts` in `onboarding-component-unit` (lista della funzione e tupla di
> `add_test`); 0 percorsi fantasma, 0 duplicati.
>
> 📌 **La regola che ne esce, per chi scrive dopo**: in un componente **legacy**, una funzione che
> legge uno stato runes dentro un'espressione del template **non viene tracciata**. Vale per ogni
> formatter mascherato. Oggi i legacy del canale sono zero; un sesto sito legacy nascerebbe
> congelato, e né il gate né un test di formatter lo vedrebbero. Va detto nella skill e nella doc
> sviluppatore (passo 10).

### Passo 7 — Quantità D5′ — **Stato: ⏳** — *i 5 file assegnati a J dal coordinator, 2026-09-24*

La classe di una quantità dipende ora dal **contesto**: la stessa `formatQuantity` va mascherata
in un lotto e resta visibile in una transazione. La regola sta quindi al sito di chiamata.

1. Inventario per contenuto, con controllo positivo. Punto di partenza misurato:
   `ExposureTable:374`, `UnifiedLotsTable` (5 `formatQuantity`), `LotCustodyModal` (8),
   `LotGanttChart` (2 + tooltip), `LotWacPriceChart` (69 menzioni, 0 `formatQuantity`).
   Fuori: `AssetTable` `quote_base_quantity` (base di quotazione) e `formatTxQuantity`.
2. Primitiva `maskableQuantity(formatted)`, con nome distinto perché la distinzione resti
   cercabile; docstring aggiornato a D5′. `SensitiveValue` (Round 1, passo 5) resta sospeso: i
   siti sono stringhe HTML e tooltip, cioè il livello formattatore.
3. Applicazione: cella lotto per Q8; tooltip ed etichette dei grafici con ricostruzione
   dell'`option` al toggle. Le grafiche restano, lunghezza delle barre inclusa.
4. Nota in testa a D5 nell'analisi, senza cancellare il testo originale.

### Passo 8 — Review del diff privacy di I — **Stato: ⏳**

Via coordinator, prima del checkpoint di I: `fmtCurrency` maschera il numero e tiene
`${baseCurrency}`; asse per Q3, `compact` dentro la maschera; `isPrivacyEnabled()` letto nello
scope reattivo che costruisce l'`option` — le etichette d'asse non si ridipingono da sole
(limite §3.4 del Round 1). J non tocca le righe di I nel registro.

### Passo 9 — E2E privacy — **Stato: ⏳**

Spec nuovo: ogni rotta, toggle nei due versi, navigazione con privacy attiva; importi con valuta
visibile; quantità mascherate in posizioni e lotti e visibili in transazioni. Registrazione nel
runner a carico del coordinator. Nessun E2E oggi nomina la privacy.

### Passo 10 — Documentazione — **Stato: ⏳**

Via `docs-writer`: cosa nasconde la privacy (numero e quantità in posizioni/lotti) e cosa no
(valuta, percentuali, prezzi, WAC, conteggi, eventi asset, tassi). Sezione in una pagina
esistente. Contratto per i renderer dei tool (D: denaro solo via primitive D8) nella guida
sviluppatore.

### Passo 11 — Review manuale e FROZEN — **Stato: ⏳**

Runbook sotto, sulla copia prod rinfrescata dalla snapshot.

## Previsione conflitti

| file | owner | intervento J | stato |
|---|---|---|---|
| `GrowthChart.svelte`, `PerformanceChart.svelte` | I | review | deciso |
| `moneyRenderSites.test.ts` | J | gate-prep e voci proprie | I scrive le sue 4 voci: ordine gate-prep → I |
| `maskable.ts` (+ test) | J | primitive | primitive per I su richiesta via coordinator |
| `riskAnalysisHelpers.ts` + `.test.ts` | J (round) | ③a | deciso |
| `LotComparisonChart.svelte:261` | J | ③b | deciso |
| `BrokerCard.svelte`, `brokers/+page.svelte`, `brokers/[id]/+page.svelte` | — | R20 | dopo la misura |
| `ExposureTable`, `UnifiedLotsTable`, `LotCustodyModal` | **J** (round) | D5′ | assegnati; K cita `LotCustodyModal` solo in analisi e ne è avvisato |
| `LotGanttChart`, `LotWacPriceChart` | **J** (round) | D5′ | assegnati: il v3 di I non li include (S1b tocca solo Growth e Performance); I ne è avvisato |
| `risk-lab.spec.ts` | F | nessuno | F dopo il mio avviso su ③a |

## Test list — approvata con il piano

| # | livello | asserzione |
|---|---|---|
| T1 | unit | `maskCurrencyParts`: `en-US` → `$•••`, `-$•••`; `it-IT` → `••• €`; compact senza `K/M`; valuta sempre presente |
| T2 | unit | rischio: `:387` e `:379` invertiti; `:330…:402` aggiornati; `—` e guardia di scope invariati |
| T3 | unit | lotti: formatter mascherato con simbolo, anche il ramo `catch` |
| T4/T5 | review | test di I su Growth e Performance |
| T6 | gate | test dei due rami su fixture sintetica; stato `public`; controllo positivo; totali per stato |
| T7 | componente | `BrokerCard`: off→on→off, montaggio con on→off |
| T12 | E2E | privacy su ogni rotta, due versi, navigazione; quantità per D5′ |
| T13 | unit | `maskableQuantity` |
| T14 | unit/componente | cella lotto Q8; custodia senza cifre; tooltip Gantt/WAC mascherati |

## Runbook review manuale — copia prod `6168`

| rotta | col toggle | difetto se |
|---|---|---|
| `/dashboard` Crescita, modi `eur/pnl/income/candles` | asse Y e tooltip | una cifra in chiaro |
| `/dashboard` Crescita, modo `pct` | asse | `•••` al posto delle % |
| `/dashboard` Posizioni, vista Performance | etichette nette e asse | cifre in chiaro |
| `/dashboard` Posizioni, vista detenzioni | colonna quantità | cifra in chiaro (D5′) |
| `/brokers` | caricare off, on sul posto, off sul posto; ricaricare on, off sul posto | un verso non risponde (R20) |
| `/brokers/[id]` | saldi `:606` e totale `:777` contro le tabelle figlie; lotti, custodia, Gantt, WAC | comportamento diverso fra i gruppi; quantità in chiaro; cella lotto senza `%` |
| rischio L1/L4, scope portafoglio | importi | `•••` senza simbolo; segno sparito |
| `/transactions` | colonna quantità | mascherata = sovra-mascheratura |
| controlli negativi | prezzi (card e tabella), tassi FX, WAC, n. movimenti, eventi asset, % | mascherati = sovra-mascheratura |

## Definition of done

- Privacy attiva: nessuna cifra di patrimonio su dashboard (assi e tooltip in ogni modo), broker,
  rischio, lotti; **valuta sempre visibile** accanto a un importo mascherato; segno per D8/Q7.
- D5′: quantità mascherate in posizioni e lotti, visibili in transazioni; cella lotto per Q8.
- Toggle nei due versi su ogni rotta, anche dopo navigazione con privacy attiva.
- Gate a 0 rossi; suite privacy verde con `Test Files N` = N; contratto Risk verde.
- Gate-prep integrato prima del commit di I; review del diff di I consegnata.
- Coordinator avvisato a ③a pronta.
- Nessuna migrazione, nessuna chiave rimossa, porte 6158/6168 provate libere al FROZEN.

## CHANGELOG proposto — lo scrive il coordinator

- 🐛 Privacy: il simbolo della valuta resta visibile accanto a un importo mascherato anche nei
  pannelli di rischio e nel confronto lotti.
- 🐛 Privacy: la pagina Broker torna a mostrare gli importi quando la privacy viene disattivata.
- 🔄 Privacy: con la privacy attiva sono nascoste anche le quantità possedute nelle posizioni e
  nei lotti; restano visibili nelle transazioni.
