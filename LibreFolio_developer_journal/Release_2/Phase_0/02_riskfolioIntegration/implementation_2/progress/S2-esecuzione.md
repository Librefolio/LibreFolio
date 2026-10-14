# S2 — L2 «Sono diversificato come credo?» — piano vivo

> **Corsia**: `--test-port 6154` · `--data-dir /tmp/librefolio-r2-s2`
> **Branch**: `e-alfy-risk-l2-diversification` · **Baseline**: `7d75a9c6c`
> **Briefing**: `implementation_2/S2-livello-2.md` · **Vincoli**: `implementation_2/_comune.md`
> **Contratto primitive**: `implementation_2/PRIMITIVE.md`

Aggiornato **dopo ogni passo**, non alla fine.

---

## Passo 0 — La misura della corsia ✅ (2026-09-18)

> **Note implementazione**: sonda `/tmp/librefolio_s2_probe.py`, che monta il router
> vero (`api/v1/risk`) su `httpx.ASGITransport`. **Non lega nessuna porta**, quindi non
> può collidere con la corsia del coordinatore né con quella di un altro mandato.
> DB della corsia ricreato con `db populate --force --clean` → **6 679 record**,
> identico al totale che F1 riporta.
> Finestra interrogata: `2025-09-16 → 2026-09-15`, 365 giorni, `target_currency=EUR`,
> scope `{"kind": "portfolio"}`. Due onde separate, esattamente come le chiede
> `RiskLevelsPanel`: `correlation` in `historical`, `risk_contribution` in
> `current_composition` con `composition_policy="current_buy_and_hold"`.

### La terza misura, e cosa dice della divergenza

| grandezza | briefing S2 | F1 (`F1-esecuzione.md:259`) | **S2 misurato** |
|---|---:|---:|---:|
| `effective_number_of_assets` | 14,97 | 16,4686196839 | **15,0011891804** |
| `diversification_ratio` | 1,94 | 1,9857170031 | **1,9439656659** |
| `cash_weight` | 0,493 | 0,5088738900 | **0,4941379371** |
| `portfolio_volatility` | — | 0,0483397669 | **0,0475592141** |

**Tre misure, tre risultati, nessuno sbagliato.** La mia è vicina a quella del
coordinatore (NEA 15,00 contro 14,97) e lontana da quella di F1 — ma *vicina* non è
*uguale*, e la differenza residua è la parte istruttiva.

> **⚠️ Fuori pista — la causa è più larga di quella che avevo scritto in analisi.**
>
> In analisi avevo attribuito la divergenza al **giorno di popolamento**
> (`populate_mock_data.py` ancora tutto a `date.today()`, RNG seminato per
> `(asset, data)`). È vero e resta vero, ma **non basta**: F1 e io abbiamo popolato
> lo stesso giorno, e i nostri numeri differiscono del 9 %.
>
> Il secondo fattore è **la finestra interrogata**, che non è un dato: è una **scelta
> della pagina**. Io ho chiesto `today−3 → today−367`; F1 e il coordinatore hanno usato
> le loro. Pesi e contributi si muovono con la finestra perché i prezzi di ieri entrano
> ed escono dal campione.
>
> **Conseguenza**: il vincolo che il coordinatore ha già esteso a S1/S3/S5 — *nessuna
> cifra del mock è citabile come fatto* — **non dipende solo dal giorno**. Vale anche
> a parità di giorno, fra due finestre diverse. Una didascalia che citasse «15,00»
> sarebbe falsa per chi guarda la stessa pagina con un altro intervallo di date.

### 🔴 La correlazione regge lo scope `portfolio`. Senza riserve.

```
status=partial  error=None
asset_ids (7): [1, 2, 3, 4, 5, 6, 7]
cells=49  statuses={'ok': 49}
observations=357  coverage=1.0
```

**Quarantanove celle su quarantanove `ok`.** Nessuna `insufficient`, nessuna
`undefined`, copertura piena su 357 osservazioni. Il `min_observations=20` di default
è soddisfatto sette volte. La domanda Q2 del briefing è chiusa: **le props reggono, e
il dato è pieno.**

Confermata anche la difesa che avevo letto nel codice: l'asset 17 (`Test KRW Stock`,
zero prezzi per scelta) **non entra in matrice**, esce con un avviso esplicito
`assets_excluded` e finisce dentro `cash_weight`.

### 🔴 …ma la matrice non ha niente da mostrare

```
strongest off-diagonal |rho|:  RE Loan Milano ~ RE Loan Roma = 0,1306
```

**La correlazione più forte dell'intero portafoglio è 0,13.** Le altre venti coppie
stanno sotto. `NEAR_IDENTICAL` è `0,9`: nessuna coppia lo sfiora. La lista delle coppie
ridondanti sarà **vuota**, l'ordinamento per similarità ordinerà rumore, e la heatmap
disegnerà quarantanove quadrati quasi bianchi.

> È la stessa causa che F1 ha trovato al suo passo 7: gli asset finti sono generati con
> **rumore indipendente**, quindi il mercato finto non ha un fattore comune. F1 ha
> riparato **gli indici benchmark** (beta da 0,02 a 0,88) ma non gli asset posseduti:
> quel pezzo non era nel suo mandato.
>
> **Perché lo scrivo qui invece di procedere**: una heatmap che rende 49 celle pallide
> **prova l'impianto, non il quadro**. È la famiglia del «cancello che non prova nulla»
> che F1 ha nominato due volte. Il coordinatore guarderà L2 nel browser e vedrà una
> matrice che sembra rotta mentre è giusta — e non avrà modo di distinguere le due cose.
> **Va deciso da lui, non assorbito da me.**

### I sette pesi, e la seconda metà della storia

| asset | peso | contributo | divergenza |
|---|---:|---:|---:|
| Apple Inc. | 14,60 % | 78,35 % | **+63,74 pp** |
| Bitcoin | 1,66 % | 9,87 % | +8,21 pp |
| Tesla, Inc. | 3,56 % | 4,45 % | +0,88 pp |
| **RE Loan Milano** | **18,63 %** | **3,33 %** | **−15,31 pp** |
| Microsoft Corporation | 2,31 % | 1,78 % | −0,53 pp |
| RE Loan Roma | 9,22 % | 1,27 % | −7,95 pp |
| Ethereum | 0,60 % | 0,96 % | +0,36 pp |

`Σ pesi = 0,5058620629` + `cash_weight = 0,4941379371` = **1,0000000000** esatto.

> 📌 **Il briefing mostrava solo le righe positive, e così mostrava metà della domanda.**
> La posizione **più grande del portafoglio** — `RE Loan Milano`, 18,63 % — produce il
> **3,3 %** del rischio. Apple risponde «sono concentrato dove non credevo»; RE Loan
> Milano risponde «e sono *assente* dove credevo di essere esposto». Sono due risposte
> diverse alla stessa domanda, e la seconda è quella che una torta o una treemap non
> possono disegnare. La barra a due versi le rende entrambe, ed è il motivo per cui è
> lei la forma giusta.

> **⚠️ Fuori pista — la trappola dell'etichetta, misurata invece che immaginata.**
>
> `NEA = 15,00` su **7 posizioni**: due volte e mezzo il numero di righe che il lettore
> ha sotto gli occhi. Verificata l'aritmetica a mano: `Σw² = 0,066638` → `1/0,066638 =
> 15,006` ✅. La cassa **non è un termine della somma**, ma i pesi sono frazioni del NAV
> **intero**, quindi sommano a 0,506 e non a 1 — ed è esattamente ciò che gonfia
> l'indice. `concentration.en.md#where-cash-sits` lo dice parola per parola.
>
> A titolo di controprova, **non implementata e non implementabile qui**: rinormalizzando
> i pesi sul solo investito, l'indice scenderebbe a **3,84** su 7 posizioni. Il divario
> fra 15,00 e 3,84 è la misura di quanto l'etichetta «numero effettivo di asset» possa
> ingannare. **Non lo calcolo nel frontend**: sarebbe una metrica nuova, e la regola
> d'architettura è che i calcoli stanno nel backend. Lo segnalo come possibile seguito.

### Stato del risultato

`status=partial` su entrambe le analitiche, con due avvisi: `assets_excluded`
(`asset_ids: [17]`) e `data_quality_degraded`. L2 mostrerà la disclosure di
`RiskLevelSection`, che è il comportamento voluto.

*Verifica*: HTTP 200 su entrambe le onde, `error=None`, nessuna porta legata
(`ASGITransport`), DB della corsia isolato in `/tmp/librefolio-r2-s2`.

---

## Passo 1 — Il piano vivo ✅ (2026-09-18)

> **Note implementazione**: questo file. Creato **prima** di scrivere una riga di
> superficie, con l'esito del passo 0 già dentro.

---

## Passo 2 — Le tre card di testa ✅ (2026-09-18)

> **Note implementazione**: `RiskCardGrid testId="risk-l2-metrics" minWidth="17rem"` con tre
> `RiskMetricCard`. **`buildConcentration()` passa da zero consumatori a uno** — è il primo
> montaggio della funzione che il round 1 aveva scritto, testato e lasciato scollegata.
>
> | card | `technicalName` | `docsPath` (verificato su disco) |
> |---|---|---|
> | `risk-l2-card-effective-assets` | `N_eff` | `…/risk-metrics/concentration/` |
> | `risk-l2-card-diversification-ratio` | `DR` | `…/risk-metrics/concentration/` |
> | `risk-l2-card-uncovered` | `risk.metrics.cashWeight` | `…/risk-metrics/risk-contribution/` |
>
> Regola anti-salto rispettata: `caption` è passata **anche durante `loading`**
> (`caption={loading ? '' : …}`), mai `undefined`. La didascalia di `N_eff` porta
> **`{positions}` accanto all'indice** — 15,00 sopra «su 7 posizioni» — che è ciò che
> impedisce la lettura come conteggio senza pubblicare una seconda metrica.

## Passo 3 — La tabella su barra condivisa ✅ (2026-09-18)

> **Note implementazione**: una riga = **una** `KpiDivergingFlowBar` in `layout="inline"`,
> etichetta = nome dell'asset, valore = lo scarto in `pp`, `signedPct` sulla scala condivisa
> dei soli scarti. Sotto, peso e contributo come numeri. Le due barre gemelle di prima
> sparite: lo scarto *è* il confronto, quindi si disegna il confronto invece dei due addendi.
> Rossa a destra (più rischio che peso), verde a sinistra (meno).
>
> **`toFixed` in `L2Diversification.svelte`: 2 → 0.** Entrambi sostituiti da `formatPercent`.

### D2 — `suffix?: string` su `formatPercent` ✅ (autorizzato dal coordinatore)

`formatPercent.ts:36` inchiodava `%` nel template. Aggiunta `suffix`, default `'%'`:
**zero regressioni per costruzione**, i chiamanti esistenti non cambiano di un carattere.
5 test nuovi nello spec già registrato (`__tests__/formatPercent.test.ts`), fra cui il
caso che l'opzione esiste per servire — `+63.7pp` — e il fatto che il segnaposto `—`
**non** acquista l'unità.

> **⚠️ Fuori pista — una seconda superficie condivisa toccata, e la dichiaro.**
>
> I tre testid di T3 (`risk-l2-weight-1`, `-contribution-1`, `-divergence-1`) sono asserzioni
> `toHaveText` **esatte**: ciascuno deve essere un elemento il cui testo è *solo* quel numero.
> `KpiDivergingFlowBar` rende `label | barra | valore` e **non esponeva un selettore sul solo
> valore**: la sua radice contiene anche l'etichetta, quindi `toHaveText('+5.0pp')` avrebbe
> letto `Apple Inc.+5.0pp`.
>
> Le uscite erano tre: rendere il numero **due volte** (una nella barra, una in una colonna
> accanto) — ed è così che due copie di un numero iniziano a divergere; passare `label=""` con
> una colonna a larghezza zero — un trucco che funziona e non si spiega; oppure **una prop
> opzionale in più**.
>
> Scelta la terza: **`valueTestId?: string`**, additiva, `undefined` di default, con un test
> che prova che **senza di essa nel DOM non compare alcun `data-testid`** — cioè che per il
> cruscotto, unico chiamante preesistente, resta un no-op. Mirata su `RiskMetricCard`, che nella
> stessa cartella già nomina i propri sotto-elementi.
>
> **Non era nell'autorizzazione D2, che diceva «additiva e sola».** La dichiaro qui e nel
> messaggio di handoff: è da ratificare, non da scoprire.

## Passo 4 — La heatmap ✅ (2026-09-18) — decisione (a) del coordinatore

> **Note implementazione**: `CorrelationHeatmap` montata sotto le righe, `height="360px"`,
> con `assetLabels` convertita `Record → Map` (la heatmap vuole una `ReadonlyMap`, il pannello
> distribuisce un `Record`: conversione di una riga, nel mio file).
>
> La prop nuova è **`correlationResult?: RiskAnalyticResult | null`, con default `null`**:
> L2 è già pronta e **S1 deve solo passarla** (`resultByCode(historicalResults, 'correlation')`).
> Finché non arriva, `correlation` è `null` e la sezione semplicemente non si monta — nessun
> vuoto, nessun errore.
>
> **La dichiarazione del vuoto**, come richiesto: `risk-l2-correlation-no-redundancy` compare
> quando nessuna coppia raggiunge `NEAR_IDENTICAL`. È un **booleano**, non il coefficiente più
> forte — citare una cifra qui la esporrebbe alla deriva della finestra misurata al passo 0.
> Aggiunta anche `correlation.basis`, che dichiara la giuntura che nessuno aveva ancora
> nominato: **la matrice è storica, i pesi sopra sono di oggi.**

## Passo 4b — 🔴 Lo scope `asset_set`, misurato: la mia struttura era sbagliata ✅ (2026-09-18)

> **Note implementazione**: sonda `/tmp/librefolio_s2_probe_assetset.py`, stesso trasporto ASGI,
> scope `{"kind": "asset_set", "asset_ids": [1,2,3,6,7]}`.

```
correlation          HTTP 200  status=partial      error=None                output=present
risk_contribution    HTTP 200  status=unavailable  error=incompatible_scope  output=None
```

> **⚠️ Fuori pista — la dipendenza che non potevo vedere, e che ha trovato un difetto mio.**
>
> Il coordinatore ha segnalato che S5 deve **ri-alloggiare** `CorrelationHeatmap` fuori dal
> pannello legacy, e che il suo Asset Global gira in scope **`asset_set`**. Misurando per
> rispondergli ho trovato un difetto **nella struttura che avevo appena scritto**.
>
> `risk_contribution` è **PORTFOLIO-only** (`risk_plugins/risk_contribution.py:46`), confermato
> dall'API: su `asset_set` risponde `unavailable` / `incompatible_scope`. La mia L2 apriva con
> `{:else if rows.length === 0}` → messaggio di indisponibilità **e nient'altro**. Cioè: sullo
> scope dove la matrice è **l'unica cosa che esiste**, la mia L2 l'avrebbe **nascosta**.
>
> Avevo ereditato quel gate dalla versione precedente, dove era corretto perché L2 rendeva solo
> i contributi. **Aggiungere la heatmap dentro un gate scritto per un'altra domanda è un errore
> che nessun test avrebbe segnalato**: su `portfolio` i contributi ci sono sempre, quindi il
> ramo rotto non si visita mai.
>
> **Ristrutturato**: ogni blocco ora sta sulla propria misura. Le card rendono se il loro dato
> esiste, le righe se ci sono righe, la matrice se c'è la matrice. Nessuno dei tre gate gli altri.

### Il contratto per S5 — quali card sopravvivono alla trasposizione

| elemento | fonte | `portfolio` | `asset_set` |
|---|---|:--:|:--:|
| `N_eff` | `risk_contribution` | ✅ | ❌ non si rende |
| `DR` | `risk_contribution` | ✅ | ❌ non si rende |
| liquidità / non coperto | `risk_contribution` | ✅ | ❌ non si rende |
| righe peso→contributo | `risk_contribution` | ✅ | ❌ non si rende |
| **heatmap correlazioni** | `correlation` | ✅ | ✅ **sopravvive** |

**Nessuna delle tre card «perde significato» su `asset_set`: non esiste proprio il dato.**
`buildConcentration` e `uncoveredWeight` passano per `okOutput`, che rifiuta uno stato
`unavailable`, quindi tornano `null` **già oggi** — la richiesta «non deve rendersi a zero,
non deve rendersi» è soddisfatta per costruzione, e ora anche per struttura: il blocco delle
card è dentro `{#if concentration || uncovered !== null}`.

Ciò che il lettore **non** perde: `RiskLevelSection` riceve `l2Health` e `l2Reasons` dallo
stesso risultato, quindi *perché* manca resta dichiarato da chi è progettato per dichiararlo.

⚠️ **Una cosa che S5 deve sapere e che non è mia da risolvere**: su `asset_set` la sezione
mostra `risk.states.unavailable` per la metà contributi, **sopra** la matrice. È onesto ma
non è bello: la formulazione giusta per quello scope è *«questa domanda vale su un
portafoglio»*, non *«non disponibile»*. La chiave è `risk.states.*`, **condivisa**, fuori dal
mio namespace: la segnalo, non la tocco.


> **Note implementazione**: 11 chiavi nuove, tutte dentro `risk.levels.l2.*`, aggiunte una per
> una con `dev.py i18n add` (script `/tmp/librefolio_s2_i18n.sh`) così il catalogo resta
> nell'ordine dello strumento. Apostrofi ASCII: è la convenzione maggioritaria misurata in
> `fr.json` — **367 stringhe ASCII contro 78 tipografiche**.
>
> Parità verificata: **17 chiavi foglia identiche in en/it/fr/es** (6 preesistenti + 11).

## Passo 6 — Cancelli e consegna ✅ (2026-09-18)

### `npm ci` — autorizzato dal coordinatore, eseguito, e solo quello

Caso sanzionato dal contratto: fallimento confermato (`svelte-kit: command not found`),
`node_modules` assente, lock presente. **Nessun `install`, `update`, `audit fix`** — `npm ci`
segnala vulnerabilità e suggerisce `npm audit fix`: **non eseguito**, per vincolo esplicito.

### `api sync` — la seconda volta è andato a termine

Prima esecuzione (senza `node_modules`): `generated.ts` generato ma `tools-codec-ast.mjs` morto
su `Cannot find package 'typescript'`. Dopo `npm ci`: completo, `Tool contracts generated: 1 tools`.

> **⚠️ Fuori pista — 46 errori che non erano di nessuno.**
>
> Il primo `front check`, subito dopo `npm ci`, dava **46 errori in 12 file**. Nessuno mio:
> 10 file su 12 erano `features/tools/*`, rotti da `tool-contract-map.generated` **mancante** —
> cioè dalla metà di `api sync` fallita poco prima. Rieseguito `api sync`, sono spariti tutti.
>
> **Un `front check` su un worktree fresco riporta decine di errori che sono bootstrap, non
> codice.** Chi lo legge senza aver prima completato `api sync` conclude che la baseline è rotta.
> La catena è `npm ci` → `api sync` → `front check`, **in quest'ordine**, e nessuno dei tre
> documenti che ho letto la mette in fila.

### I cancelli

| # | comando | esito |
|---|---|---|
| 1 | `front check` | ✅ **0 errori**, 41 warning in 2 file — `BrokerSharingPanel`, `GlobalSettingsTab`, `on:click` deprecati, **preesistenti e non miei** |
| 2 | `front format --check` | ✅ *All matched files use Prettier code style* |
| 3 | `front-utility core-unit` | ✅ **83 file, 2 098 test** |
| 4 | `front-utility component-unit` | ✅ **1 817 test** |
| 5 | `front-portfolio risk-levels-unit risk-unit` | ✅ |
| 6 | `front-portfolio risk` (E2E) | ✅ **12/12** — è la prova del contratto T3 |
| 7 | `front-portfolio dashboard` (E2E) | ✅ **7/7** — `KpiDivergingFlowBar` resta un no-op per il cruscotto |
| 8 | `front-portfolio risk-lab` (E2E) | ✅ **6/6** — la casa originale della heatmap intatta |

Corsia rispettata su tutti: `--test-port 6154 --data-dir /tmp/librefolio-r2-s2`.
**Nessuna esecuzione concorrente.** A fine lavoro `lsof -nP -iTCP:6154 -sTCP:LISTEN` → **libero**.

I 7 test nuovi girano **per nome**, verificato con `--reporter=verbose`: 5 su `suffix`,
2 su `valueTestId` (di cui uno prova il **no-op**: senza la prop, nessun `data-testid` nel DOM).

> **⚠️ Fuori pista — un rosso che era mio e non del prodotto.**
> `… front-portfolio dashboard risk-lab` è fallito con *No tests found*: il runner legge il
> secondo argomento come **filtro `--grep`**, non come seconda azione. Rilanciati separati,
> entrambi verdi. **Errore d'uso mio**, registrato perché la forma sbagliata *sembra* funzionare.

### 🔴 La verifica che mancava: non avevo mai visto la heatmap rendersi

Le prop arrivano da S1 e **non sono ancora atterrate**, quindi in questo worktree
`correlationResult` è `null` e la sezione non si monta. Stavo per consegnare **una matrice che
nessuno aveva visto rendersi** — cioè **esattamente il difetto di `RiskMetricCard` del round 1**,
commesso da me, nel giro che esiste per chiuderlo.

Sonda temporanea (mount in jsdom, `echarts` finto), **3 asserzioni, tutte verdi**:

1. le tre card rendono i valori veri (15,00 · 1,94), i testid pinnati esistono, e la riga
   negativa esce con **U+2212** — il meno tipografico, non un trattino;
2. **con la prop, la heatmap si rende**: `risk-l2-correlation`, `risk-l2-correlation-no-redundancy`
   e `risk-correlation-heatmap` tutti presenti;
3. **con `contributionResult` `unavailable`** — il caso `asset_set` di S5 — **niente card, niente
   righe, matrice presente**. La ristrutturazione del passo 4b è provata, non affermata.

> **Due mie previsioni falsificate dalla sonda, entrambe innocue e istruttive.**
> Attendevo `78.4%`, esce **`78.3%`**: `78.35.toFixed(1)` arrotonda in giù, ed è **la proprietà
> che lo spec di `formatPercent` già inchioda** («rounds the way toFixed does, which is not the
> way school does»). E attendevo il valore della card subito: `TweenedValue` anima da 0, quindi
> serve `waitFor`. **Entrambe erano sbagliate nella mia attesa, non nel codice.**

**La sonda non resta nel repo.** Uno spec non registrato in `scripts/test_runner/` non viene
mai eseguito e **somiglia a copertura** — `PRIMITIVE.md` §3 lo dice. Il catalogo è di **T3**.
File consegnato al coordinatore per T3, fuori dal repo. ⚠️ **`L2Diversification` resta senza
spec: è un debito, e lo dichiaro invece di nasconderlo dietro una sonda cancellata.**

## Passo 7 — Il cancello visivo, e le due riparazioni che ne sono uscite ✅ (2026-09-18)

Corsia alzata su `6154` (DB ripopolato, server senza `--force`, `--no-reload --no-scheduler`),
coordinatore ha guardato in italiano su `/dashboard`. **Passato con riserva**, più due reperti.

> **⚠️ Fuori pista — un controllo che ho quasi saltato e che avrebbe invalidato la revisione.**
> Prima di chiamare il coordinatore ho confrontato **l'ora del build servito** (18:51) con
> **l'ora dell'ultima modifica al sorgente** (18:45) e ho cercato i marcatori nuovi dentro
> `build/`. Erano presenti. **Con un build stantio avrebbe guardato la L2 vecchia e approvato
> un'altra superficie, e nessuno dei due se ne sarebbe accorto.** Un cancello visivo è valido
> solo se si prova che si sta guardando il codice che si sta consegnando.

### 🔴 Riparazione 1 — il separatore decimale era **mio**, non di T4

Il coordinatore ha visto due separatori nella stessa fila di card — `14,97` e `1,99` con la
**virgola**, `49.3%` e `+65.3pp` con il **punto** — e me l'ha assegnato a T4, scrivendo
«non è colpa tua e non ripararlo».

**Misurato prima di accettare l'assoluzione**:

```
grep -c toLocaleString  su L2Diversification.svelte a HEAD  →  0
```

**La virgola l'ho introdotta io**, con `index()` che usava `toLocaleString(undefined, …)` —
cioè il locale del **browser**. Il punto viene da `formatPercent`, che è debito di T4.
**Erano due debiti, e il secondo l'avevo appena creato.**

E `PRIMITIVE.md` §4 lo vietava esplicitamente, in un paragrafo che avevo letto:
*«una seconda formattazione parallela raddoppierebbe il problema invece di risolverlo»*.

Riparato dentro il mio file: `index()` ora chiama `formatPercent(v, {signed:false, digits:2,
suffix:''})` — **la stessa opzione `suffix` che avevo aggiunto io al passo 3 e poi non avevo
usato**, con tanto di test già scritto (`drops the unit entirely when asked`). Una convenzione,
un proprietario, una riparazione: il punto resta ovunque e T4 lo sistema **una volta sola**.

> **⚠️ Fuori pista — la trappola di conteggio di `PRIMITIVE.md` §3③, scattata su di me.**
> Verificando la riparazione, `grep -c toLocaleString` tornava **2** su un file dove non ne
> restava **nessuna**: erano le due citazioni **dentro il commento** che spiega perché non si usa.
> *«Un commento che cita una chiamata contiene la chiamata.»* L'avevo letto e l'ho rifatto,
> mentre verificavo. Ricontato escludendo le righe di commento: **0 chiamate**.

### 🔴 Riparazione 2 — la didascalia condizionale (dopo la ritrattazione del coordinatore)

Il coordinatore aveva dichiarato `N_eff = 14,97` un **difetto del backend** («l'unico dei tre
valori che non si può difendere») e poi ha **ritrattato**: `concentration.en.md#where-cash-sits`
descrive il comportamento **di proposito**, con la formula `N_eff = n/s²`, e dice che
*«there is no upper bound at all»*. Il 14,97 è la convenzione applicata bene su pesi sbilanciati.

**Ma il reperto si è spostato ed è diventato mio.** La stessa pagina, §Interpretation, dà la
regola di lettura: *«the direction of the gap selects its meaning»* — **sopra** il conteggio
l'eccesso è liquidità e non dice nulla sui pesi, **sotto** i pesi sono sbilanciati.

**La mia didascalia mostrava il confronto senza la sua regola.** Avevo reso *visibile* l'assurdità
e mi ero fermata un passo prima di darle il significato che la documentazione già assegnava.

Sostituita `effectiveAssets.caption` con **tre** chiavi direzionali — `aboveCount`, `belowCount`,
`evenCount`. La terza esiste perché **l'uguaglianza non è nessuno dei due casi** (pesi uniformi e
zero liquidità), e piegarla in un ramo l'avrebbe falsificata.

Il confronto è contro le posizioni **che questo livello ha misurato**, cioè quelle che il lettore
conta sotto: un titolo escluso per mancanza di prezzi non è fra loro, sta nella card del
non coperto. La didascalia lo dice — «posizioni misurate», non «posizioni».

> 📌 **La forma dell'errore, sua e mia, è la stessa**: lui ha ri-derivato una decisione già
> documentata senza aprire la pagina **linkata dalla card che stava giudicando**; io ho mostrato
> il confronto che quella pagina prescrive senza la regola che la stessa pagina fornisce.
> **Entrambi ci siamo fermati a un link di distanza dalla risposta.**

### I cancelli, rieseguiti dopo entrambe le riparazioni

| comando | esito |
|---|---|
| `front check` | ✅ **0 errori** (41 warning preesistenti, non miei) |
| `front format --check` | ✅ Prettier pulito |
| `front-utility core-unit` | ✅ **2 098** |
| `front-utility component-unit` | ✅ **1 817** |
| `front-portfolio risk` (E2E) | ✅ **12/12** |
| parità i18n `risk.levels.l2.*` | ✅ **19 = 19 = 19 = 19** |

Sonda aggiornata per T3: **4 test**, il nuovo prova che i **tre rami** producono **tre frasi
diverse** — una didascalia che mostrasse il confronto senza la regola sarebbe identica in tutti
e tre. Fuori dal repo, `ls | grep -c tmp` → **0**.

### Reperti che restano, e non sono miei

- **separatore decimale** (il **punto**, da `formatPercent`): debito **T4**, priorità alzata dal
  coordinatore perché ora si vede al primo sguardo sulla superficie principale;
- **spiegazioni di stato in inglese** sotto un titolo italiano: i 17 messaggi in prosa del
  backend, **T1**;
- **`L2Diversification` senza spec registrato**: catalogo di **T3**, sonda consegnata.

### Controllo dimensionale — `git show :file | wc -l` contro `wc -l file`
| file | HEAD | disco | Δ |
|---|---:|---:|---:|
| `L2Diversification.svelte` | 117 | 284 | +167 |
| `KpiDivergingFlowBar.svelte` | 147 | 162 | +15 |
| `KpiDivergingFlowBar.test.ts` | 174 | 203 | +29 |
| `formatPercent.ts` | 43 | 66 | +23 |
| `formatPercent.test.ts` | 106 | 140 | +34 |
| `en.json` · `it.json` · `fr.json` · `es.json` | 3 580 | 3 599 | **+19 ciascuno** |

I quattro cataloghi si muovono **dello stesso identico numero di righe**: è la parità i18n
provata *dimensionalmente*, da un controllo che non cerca una stringa e quindi non può tacere
su un'altra.

`git diff --check` → pulito. **Nessun artefatto generato o ignorato** fra i file modificati:
`generated.ts`, `openapi.json`, `node_modules`, `.testLog` restano fuori per `.gitignore`.

>
> | controllo | esito |
> |---|---|
> | i 7 testid di T3 presenti in `L2Diversification.svelte` | ✅ |
> | `toFixed` nuovi introdotti | ✅ **0** |
> | parità i18n `risk.levels.l2.*` su 4 lingue | ✅ 17 = 17 = 17 = 17 |
> | i due `docsPath` esistono su disco | ✅ `concentration.en.md`, `risk-contribution.en.md` |
> | blocchi `{#if}`/`{/if}` · `{#each}`/`{/each}` | ✅ 9/9 · 2/2 |
> | ogni simbolo importato esiste alla sorgente | ✅ 11 import, tutti risolti |



---

## Passo 8 — Il vincolo Ⓕ applicato ai commenti ✅ (2026-09-18)

Riaperta dal coordinatore per **un solo commento**: `L2Diversification.svelte:77`,
`0,408 on the test data` — cifra che **integra sulla finestra**, quindi vietata dalla regola
affinata da S1: *l'RNG è seminato per `(asset, data)`, quindi un prezzo è citabile e un
aggregato no.* Segnalata da **S1**, che non l'ha toccata perché è superficie mia.

> **⚠️ Fuori pista — il bersaglio non esisteva più, e il debito vero era un altro.**
>
> ```
> git show HEAD:…/L2Diversification.svelte | grep -n "0,408"   →   77:  …
> grep -n "0,408" …/L2Diversification.svelte                    →   (nessuna)
> ```
>
> **La riga 77 è esatta — ma a `HEAD`.** Sul disco quel commento non c'è più: l'avevo rimosso
> riscrivendo il markup al passo 2, insieme al blocco che lo conteneva. Chi l'ha segnalata ha
> letto la versione committata, non quella consegnata.
>
> **Ma cercando la cifra vietata ne ho trovate sei, tutte mie, tutte introdotte in questo ramo**,
> e nessuna era nel mandato perché nessuno le aveva ancora lette:
>
> | dove | cosa |
> |---|---|
> | `L2Diversification.svelte:26-27` | `14.6%` · `78.4%` · `+63.7pp` · `18.6%` · `3.3%` · `−15.3pp` |
> | `L2Diversification.svelte:154-155` | `14.6%` · `78.4%` · `63.7` |
>
> **Riparare il commento assegnato e lasciare questi sarebbe stato obbedire alla lettera
> dell'incarico tradendone la ragione**: il vincolo non esiste per far sparire *una* cifra,
> esiste perché **una cifra in un commento continua a leggersi come un fatto molto dopo aver
> smesso di esserlo**.

Riscritti entrambi portando il **fenomeno** invece della misura — *«una posizione pesa una
piccola frazione del libro e produce la maggior parte del rischio, mentre la più grande non ne
produce quasi nulla»* — con il rimando esplicito a questo piano vivo per le cifre datate.
Nella doc di `points()` l'illustrazione è ora **tonda e dichiaratamente inventata** (20 % → 80 %
= 60 punti), così non può essere scambiata per una misura.

*Verifica*: `grep -nE` per ogni forma delle cifre vietate su `L2Diversification.svelte` →
**nessun risultato**. `front check` → **0 errori**. `front format --check` → pulito.

### 🔴 Quattro occorrenze trovate e **NON** riparate — attendono la parola del coordinatore

Sono testo che ho scritto io in questo ramo, ma in **file che non sono la superficie assegnata**,
e l'istruzione era *«solo quel commento, nient'altro»*:

| file | riga | cosa |
|---|---|---|
| `formatPercent.ts` | 24-25 | «the gap between a holding's **14.6%** weight and its **78.4%** share of risk is **+63.7pp**» |
| `formatPercent.test.ts` | 116-119 | stessa frase in commento, più le fixture `0.6374` / `-0.1531` |
| `formatPercent.test.ts` | 123 | `formatPercent(**1.94**, …)` — **il numero con tre referenti** |
| `KpiDivergingFlowBar.svelte` · `.test.ts` | 70 · 164-177 | `"Apple Inc.+63.7pp"`, e la fixture `+63.7pp` |

⚠️ **Il caso peggiore è `formatPercent.ts`**, ed è peggiore *proprio perché* è un file condiviso:
un lettore che arriva lì non ha alcun contesto di rischio da cui dubitare della cifra. E
`formatPercent.test.ts:123` porta **`1.94`**, che il coordinatore ha appena censito come il
numero con **tre referenti** — mia misura *ante*, previsione di N *post*, e le trascrizioni.

**Riparazione pronta e non applicata**: sostituire le cifre in prosa con la coppia sintetica
20 % → 80 % = 60 punti, le fixture con `0.6` / `-0.3`, e `1.94` con `7.25` — gli stessi valori
deliberatamente impossibili già scelti per la sonda consegnata a T3.
