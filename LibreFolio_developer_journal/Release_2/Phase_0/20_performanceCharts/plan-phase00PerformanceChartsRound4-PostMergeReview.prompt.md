# Performance charts — round 4: review d'uso post-merge (R5–R11, R21, §2.5, P4-11, emoji K) + prosecuzione

**Stato:** IN ESECUZIONE — piano v3 presentato il 2026-09-23, approvato il 2026-09-24. S2 (privacy) 🔒 in attesa del gate-prep di J.
**Workstream:** I (grafici performance) · ramo `e-alfy-performance-charts-plan` · coordinatore
`c8328a01-f208-4ade-a352-0486d1f14de2`.
**Baseline:** `dev_release2` = `f1047f766` (fast-forward), albero pulito, rimisurata il 2026-09-23 prima di ogni
versione del piano e il 2026-09-24 dopo l'approvazione.
**Lane:** copia di prod `6167` + `/tmp/librefolio-r2-i-charts-prodcopy` (server, verifica visiva, review) · suite
`6157` + `/tmp/librefolio-r2-i-charts` (solo `dev.py test …`). **Mai** `dev.py test` sulla copia.
Preambolo: `PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py …`.

Precedenti e collegati:

- Piano madre: [plan-phase00PerformanceCharts.prompt.md](plan-phase00PerformanceCharts.prompt.md) — §6.0.20 punta
  qui. Review precedenti di I: round 1 = §6.0.15, round 2 = §6.0.17, round 3 = §6.0.18; inventario dei 12 rossi =
  §6.0.19.
- Review d'uso del developer: [08_review_visiva_20260922.md](../09_feedbackJobs/08_review_visiva_20260922.md)
  (R1…R21; §8 secondo passaggio).
- Analisi statica: [09_reperti_analisi_statica_20260922.md](../09_feedbackJobs/09_reperti_analisi_statica_20260922.md)
  — **leggere la §9 prima di fidarsi della §1**: due voci sono state smentite dalla review.

## Stato di esecuzione

Indicatore di lettura rapida: va riletto **a ogni consegna**, non a ogni sospetto (§6.0.11 del piano madre).

| Step | Contenuto | Dipende da | Stato |
|---|---|---|---|
| S0 | Journal: questo file + §6.0.20 e indicatori del piano madre | approvazione | ✅ 2026-09-24 |
| S1 | Baseline nella lane suite, prima di ogni edit | S0 | ✅ 2026-09-24 |
| S1b | Hook `__lfChart` in `GrowthChart` e `PerformanceChart` | S1 | ✅ 2026-09-24 |
| S2 | Privacy Growth (S2a) + Performance (S2b) | **gate-prep di J fuso dal developer** + S1b | 🔓 C0 fuso 2026-09-24 11:16 (ff `f1047f766..2a5927c48`) · S2-pre ✅ · S2a ✅ · S2b ✅ 2026-09-24 (verifica live in S6) |
| S2c | Review di J sul diff privacy | S2b | ✅ 2026-09-24 11:45: **J approva** (D1/D14). Parola della `why` di D13 cambiata come chiesto; gate 6/6 |
| S3 | §2.5: omissione = annullamento | S1 | ✅ 2026-09-24 |
| S4 | R21 Allocazione | S1 | ✅ 2026-09-24 (verifica live in S6) |
| S4b | Emoji per ogni tipo asset | S4 | ✅ 2026-09-24 (❓ per Unknown: decisione del developer, 10:28) |
| S5 | R21 Crescita | S1b | ✅ 2026-09-24 (verifica live in S6; fix gallery in test list, da consegnare con C1) |
| S6 | Riproduzione R8/R10 sulla copia | S5 | ✅ 2026-09-24 12:05: R8 = 3 cause + 1, R10 = il moncone di coda; R21, S9 e privacy verificati dal vivo; reperto nuovo (tacche Y doppie → D18) |
| C1 | Checkpoint unico (D14): S0–S6 + S9 + S2 | S2c, S6 | ✅ pronto 2026-09-24 12:21 (registro «Checkpoint C1»), consegnato al coordinator; `FROZEN` |
| S7 | Asse dei bucket (R8 dopo D4, R10) | S6 | ⏳ aspetta **D4, D16, D17** (e D18 se entra nel round): storyboard v2 in §2 |
| S8 | R11 valore di acquisto | S7 | ⏳ |
| S9 | R9 didascalia | S1 | ✅ 2026-09-24 (scorrimento a 375 px: verifica live in S6) |
| S10 | Debiti e test residui | S1 | ⏳ (D8 ✅ 2026-09-24) |
| S11 | Docs (docs-writer) | S2b, S3, S4b, S8, S9 | ⏳ |
| S12 | Handoff | S10, S11, S2c | ⏳ |

## 0. Come si è arrivati a questa versione

Il piano è stato presentato in chat tre volte; le prime due sono state rimandate con un feedback che è parte della
storia delle decisioni, non un dettaglio di processo.

- **v1 → v2** (coordinatore): aggiungere P4-11 (privacy di `PerformanceChart`, montato in dashboard **e** in
  broker), precisare D1 (chi scrive la privacy), chiudere D10 (copia di prod da snapshot) e la segnalazione di K
  sulle emoji di Allocazione storica.
- **v2 → v3** (coordinatore, su dimostrazione di J, proprietario del gate `moneyRenderSites.test.ts`):
  - il test 5 del gate («sees both branches of a two-branch money line») usa `PerformanceChart` come esemplare:
    mascherare `shortMoney` con `maskable(` lo fa diventare rosso;
  - una voce di registro mascherata si **cancella**, non cambia stato;
  - le liste attese del gate sono toccate da entrambi → **ordine nuovo**: prima il gate-prep di J (solo
    `moneyRenderSites.test.ts`: test 5 su fixture sintetica, `EventCreateMiniModal` riclassificato, stato
    `public`), poi il developer lo fonde nel ramo di I, solo dopo S2;
  - l'alternativa v2 (mascherare a monte lasciando intatti i letterali) è **ritirata**: rendeva la maschera
    invisibile al gate — la stessa forma del «gate verde che non misura niente» di 09 §1.6.
- **Misurato, non dedotto.** Per v3 un probe ha **eseguito** le regex del gate stesso, lette dal file del gate,
  sugli edit proposti applicati in memoria (sostituzioni *exactly-once*: si ferma da solo se un letterale non si
  trova più). Lo script vive nella cartella di sessione di I e **non è versionato**; i suoi esiti sono i reperti
  8, 10 e 11 qui sotto, e verrà rieseguito in S2-pre contro il gate fuso.

Credenziali della copia di prod: **mai** trascritte in questo file (versionato) né altrove; solo in env al momento
dell'uso.

---

## 1. Stato reale e cause

| # | Sev | Causa | Certezza | Rimedio proposto |
|---|---|---|---|---|
| R5/R6/R7 | 🔴 | `GrowthChart.svelte` ha due sole uscite di denaro: il ramo `else` di `yAxisFormatter` `:1815-1822` (`k`/`M` in chiaro) e `fmtCurrency` `:1834` (1 definizione + 8 consumi = tutti i tooltip). I formatter ECharts non sono reattivi, quindi il toggle non ridisegna | statica, completa | **Asse**: segno fuori + `maskable(compact)`, con `k`/`M` **dentro** la maschera (`-5k` → `-•••`; `0` → `•••` per D12). **`fmtCurrency`**: `${baseCurrency} ${v < 0 ? '-' : ''}${maskable(Math.abs(v).toLocaleString(…))}`, la stessa forma di `formatCurrencyAmountPlain`; copre gli 8 consumi (tooltip Abs, linea, candele, Income). Privacy nella chiave di full-rebuild e nelle dipendenze dell'effect di render. `%` invariato. **Registro**: la voce della definizione diventa stantia e si cancella; `:1899` resta un hit → D13 |
| **P4-11** | 🔴 | `PerformanceChart.svelte`: vista Performance di Posizioni, montata da `PositionsPanel.svelte:210` sia in dashboard **sia** in broker. Due uscite in chiaro:<br>• `shortMoney` `:161-168` → etichetta del P&L netto per posizione (`netValueText` `:233`, desktop `:823`, mobile `:884`)<br>• `axisTickAmount` `:170-175` → asse dei valori `:987`<br>Il **tooltip è già mascherato**: 4 chiamate a `formatCurrencyAmountPlain` (`:198`, `:501`, `:532`, `:533`, rimisurate). L'effect di render `:1107-1123` non dipende dalla privacy e disegna in `tick().then(...)`, fuori dal tracciamento, quindi il toggle non ridisegna | statica, completa | **`shortMoney`**: `maskable(compact)` **dentro entrambi i letterali di ritorno** (`${sign}${symbol}${maskable(compact)}` / `${sign}${maskable(compact)} ${currency}`). La riga diventa `SAFE_CALL` e le 2 voci diventano stantie: si cancellano (dopo il gate-prep il test 5 non dipende più da questo file). Resa `+€•••` / `-••• CHF`; il suffisso compatto sta dentro la maschera; `(±x,x%)` resta (una percentuale non è patrimonio). **`axisTickAmount`**: segno fuori + `maskable(compact)`; lo zero diventa `maskable('0')` (D12). **Effect**: legge `shouldMaskAmount()`. Nessun importo `public` → sensitivity di default |
| R8 | 🟠 | ECharts 6 (`axisTickLabelBuilder.js`): `splitLine.interval:'auto'` **segue l'intervallo delle label** → separatori ogni k+1 bucket. Label solo-mese + `showMaxLabel:true` → «set», «set». Commento `:2023-2026` vero solo a intervallo 0 | meccanismo certo; **da riprodurre** sui dati reali | separatori disaccoppiati dalle label; label solo sul bucket che contiene l'inizio di mese (trimestre/anno su span lunghi); niente `showMin/MaxLabel` forzati. Semantica N-giorni (§6.0.16) invariata. Override locale: `responsiveXAxis.ts` ha 8 consumatori |
| R10 | 🟠 | Asse **time**: `barGrid.js` dimensiona sul **gap minimo** fra le x; l'ultimo bucket parziale (`length % span`) crea un gap minuscolo → barre sottili. Zoom (`filterMode` default `'filter'`) scarta il bucket di bordo → barre larghe | statica, spiega entrambi i sintomi | **R10-A**: Income su asse **category** come le candele (alternative B `barWidth` px, C x virtuali) |
| R11 | 🟠 | Il dato esiste: `from_new_capital + from_reinvested` = uscita cassa BUY **per costruzione** (`portfolio_engine.py:497-508`, `schemas/portfolio.py:679-687`). Manca nome e totale | statica | **R11-A** colonna flusso (storyboard §2), nessun backend; alt. **R11-B** livello `open_cost_basis` (`schemas/portfolio.py:529`) |
| R9 | 🟡 | Didascalia `:2244` = chiave lunga; `pnlCandlesHypotheticalShort` orfana | certa | testo corto + marquee esistente (`use:scrollOnOverflow` + `overflowScrollTextClass`) |
| R21 | 🟡 | `viewMode`/`pnlSubmode` `:81/:85`, `allocationTab`/`allocationView` `AllocationPanel.svelte:30-31` sono `$state` locali | certa | pattern `PositionsPanel.svelte:68-104` + normalizzazione |
| §2.5 | 🔴(09) | `assets/[id]/+page.svelte:2174` default `{accepted: true}`; call site `:3533`, `:3558` passano sempre il detail | certa | `{accepted: false}` |
| **K-emoji** | 🟡 | `AllocationHistoryChart.svelte:164-181`: mappa locale di **10** chiavi (STOCK, ETF, BOND, CRYPTO, FUND, HOLD, CROWDFUND, INDEX, OTHER, LIQUIDITY), fallback `📊` = **l'emoji dell'ETF**. Il motore raggruppa per `asset_type.value` grezzo (`portfolio_engine.py:1684-1685`) → arrivano tutti i 17 valori dell'enum + `Unknown` + `Liquidity`. Il backend non fornisce emoji di tipo (`portfolio_engine.py:1931`, solo settori) | statica; **confermato e più largo** del reperto | vedi §2 e D11: mappa esplicita su tutto `ASSET_TYPES`, in un modulo testabile |

### Reperti nuovi (misurati, non ereditati)

1. **4 casi E2E probabilmente stantii** in `e2e/portfolio/dashboard.spec.ts` (`growth-zoom-window-*` assente dal componente). Da misurare in S1.
   → **Misurato in S1 (2026-09-24)**: i 4 sono rossi, ma solo 3 sono da cancellare. Il quarto ha un contratto ancora vivo, da
   ri-pinnare. In più ci sono **2 rossi non previsti** (E5, E6). Vedi il registro S1.
2. `GrowthChart` **e** `PerformanceChart` non espongono `__lfChart` (lo fanno Candlestick, AllocationPie, PriceChartFull, AllocationHistory). Entrambi hanno già `attachChartReady` → `data-chart-renders` per attendere un ridisegno senza orologio.
3. `AllocationPanel` view/tab e i toggle Abs/%/P&L **senza `aria-pressed`**.
4. `GrowthChart`/`AllocationPanel`/`PositionsPanel` montati **due volte** (dashboard, broker): una chiave per componente, condivisa (precedente `PositionsPanel`).
5. Abs mostra già il livello di acquisto (`bookAssetLike`): argomento per R11-A.
6. Refuso journal §6.0.19: «Quattro (6, 8, 9, 10, 11)» → **cinque**.
7. **Il gate di J non vede i formatter d'asse** (`yAxisFormatter`, `axisTickAmount`): nessun marcatore di valuta → nessun hit → **nessuna voce registrabile** (il controllo «rotting» la segnalerebbe come stantia). Unica guardia: test di comportamento. Da dire a J, è il limite dichiarato del suo gate. Vale anche dopo `maskable()`: quelle righe non erano un hit nemmeno prima.
8. **L'autotest del gate è ancorato al mio file**: «sees both branches» filtra gli hit di `PerformanceChart.svelte`. Con `maskable(` sulla riga di `shortMoney` il file non ha più hit e il test diventa rosso (**confermato dal probe**). L'ordine nuovo lo risolve: nel gate-prep J porta il test su una fixture sintetica. Io non lo tocco.
9. **K-emoji più largo**: oltre a COMMODITY/REAL_ESTATE (icone proprie `assetTypes.ts:28-29` → oggi mostrate come ETF) anche `Unknown` cade su `📊` (ignoto mostrato come ETF). ETF_MONETARY e gli altri 5 sottotipi ETF cadono su `📊` = ETF, **coerente** con la regola di K (`assetTypes.ts:33-42`: i sottotipi condividono l'icona ETF) ma **per caso**, non per decisione. Un valore d'enum nuovo oggi scompare in silenzio nel fallback.
10. **3 + 1, non 4** (probe, con le regex lette dal gate stesso):
    - `GrowthChart` passa da 2 hit a 1. La definizione di `fmtCurrency` `:1834` sparisce. Il consumo `:1899` **resta un hit**:
      nello stesso letterale ci sono `pnlColor`, il ternario su `totalPnlVal` e `fmtCurrency(…)`, e il gate non segue la chiamata
      dentro una closure locale.
    - `PerformanceChart` passa da 2 hit a 0.
    - Gli altri 7 consumi di `fmtCurrency` non sono mai stati hit (nessun token numerico accanto) e sono coperti dalla definizione.
    - La `why` attuale di `:1899` diceva già «Covered by masking fmtCurrency».
11. **Parità con privacy OFF** (probe, 31 valori × 6 locali):
    - Asse di Growth, asse di Performance e `shortMoney` producono un output identico.
    - `fmtCurrency` cambia solo in due casi, entrambi allineati a `formatCurrencyAmountPlain`:
      - `-0` → `EUR 0,00` (prima era `EUR -0,00`);
      - nei locali con il meno tipografico U+2212 (per esempio `sv-SE`) il meno diventa `-`, come fa già `formatCurrencyAmountPlain`.
    - `fmtCurrency` usa il locale **del browser** (`toLocaleString(undefined, …)`), non quello dell'app. Con it/en/fr/es e
      `de-CH` l'output è identico, salvo `-0`.
    - **Con privacy ON**: nessuna cifra e nessun suffisso compatto fuori dalla maschera; valuta e segno restano fuori.
12. **Il gate di J non sembra raggiunto dal runner**: nessuna unità di `scripts/test_runner/` nomina `utils/privacy/`, quindi
    `dev.py test … all` probabilmente non lo esegue. Lo misuro in S1 con `dev.py test check-orphans`. Il catalogo è condiviso:
    lo segnalo al coordinator, non lo registro io.
    → **Misurato in S1**: confermato, ed è **più largo**. Gli orfani sono 5: tutti i test privacy di J e `currencyFormat`.
    Il coordinator lo sapeva già, perché Risk l'aveva trovato. Li registra J.

---

## 2. Storyboard (gate: nessuna implementazione della slice prima dell'OK)

### R8 — candele · v2, sulle misure di S6 (gate D4 + D16)

Le misure sono sulla copia, a 1440×900 con plot da 527 px (registro S6). Le date d'esempio dipendono solo da oggi e
dal periodo scelto, non dai dati.

```
6M con 1S — 27 bucket, slot 19,7 px
OGGI                                              PROPOSTA
 ┆ ▮ ▮ ▮ ┆ ▮ ▮ ▮ ┆ ▮ ▮ ▮ ┆ … ┆ ▮ ▮ ┆▮┆              ┆▮┆▮┆▮┆▮┆▮┆▮┆▮┆▮┆▮┆▮┆▮┆ … ┆▮┆▮┆▮┆   separatore su OGNI confine (slot ≥ T)
 mar     apr     mag   …  set  set                    apr       mag       giu   …   set         il mese, sul bucket che contiene il 1°
 └ separatori ogni k+1 = 3 bucket (causa B)        └ separatori ed etichette disaccoppiati
 └ «giu giu», «set set» (causa A)                  └ un mese = un'etichetta, per costruzione

3M con 1G — slot 5,7 px < T                         (idem 2A/1S 5,0 · 1A/3G 4,4 · 6M/1G 2,9)
 ┆▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮┆▮▮▮▮▮▮▮▮▮▮▮▮▮▮┆▮▮▮▮▮▮▮┆            separatori solo sul primo bucket di ogni mese
  lug              ago             set                  etichette diradate a 2/3/6/12 mesi, allineate al calendario

3M con 2S — 7 bucket, slot 76 px: le etichette brevi entrano tutte
OGGI  2026-07-07 · 2026-08-04 · 2026-09-01 · 2026-09-24     ISO grezzo (causa D), una ogni due più l'ultima forzata
PROP. ┆  ▯  ┆  ▮  ┆  ▮  ┆  ▮  ┆  ▮  ┆  ▮  ┆  ▮  ┆           con D16-ii: il parziale (9 gg) è il primo
        2 lug 16 lug 30 lug 13 ago 27 ago 10 set 24 set      la data di chiusura breve; oltre l'anno «24 set 25»
```

**Etichette: una regola sola, per tutti i gradini.**
1. Se **tutte** le etichette entrano nello slot (larghezza stimata), ogni bucket porta la sua **data di chiusura
   breve**: «24 set», oppure «24 set 25» se il periodo supera l'anno. Il valore di categoria è già la data di
   chiusura (`buildLadderBuckets` `:759`), quindi l'etichetta dice di che bucket si tratta.
2. Altrimenti porta **il mese**, sul bucket che contiene il 1° («lug»; «gen 26» a gennaio e oltre l'anno),
   diradato a 2/3/6/12 mesi allineati al calendario finché entra.

Tutte e due sono distinte per costruzione:
- le date di chiusura sono diverse fra loro;
- fino a 2S un bucket contiene al più un 1° del mese.

Da 1M in su (30 giorni) un bucket può contenerne due, e allora un mese resta senza etichetta: **mai una doppia**.
Niente `showMinLabel`/`showMaxLabel` forzati, niente ISO. La semantica N-giorni di §6.0.16 non cambia.

**Separatori:** su ogni confine di bucket se lo slot è ≥ **T**; sotto T, solo sul primo bucket di ogni mese. Il
separatore separa bucket, non taglia mai una candela: il confine di mese cade al bordo del bucket che contiene il 1°.
- T = `CANDLE_MIN_SLOT_PX` = 8 px (`timeSeriesAggregation.ts:60`, «corpo + 2 bordi + spazio fra candele»). La soglia
  esiste già: non ne invento una.
- Sotto T cadono 4 casi misurati: 6M/1G 2,9 · 1A/3G 4,4 · 2A/1S 5,0 · 3M/1G 5,7 px. Tutti gli altri sono ≥ 8,58 px.
- Override locale nel componente: `responsiveXAxis.ts` ha 8 consumatori e non si tocca.

### D16 — il bucket parziale (misurato: in coda da 1M in su, cause C di R8 e radice di R10)

```
3M con 1M: 93 giorni = 3 × 30 + 3
OGGI — ancorati all'inizio                     (ii) ancorati alla fine + (i) parziale marcato   ← raccomandata
 │    ▮    │    ▮    │    ▮    │ ▮ │              │ ▯ │    ▮    │    ▮    │    ▮    │
  07-23     08-22     09-21     09-24              26 giu   26 lug    25 ago    24 set
                                └ 3 giorni,         └ 3 giorni: corpo chiaro,          └ l'ultima candela chiude
                                  largo come          tooltip «parziale: 3 gg su 30»     sull'ultima data ed è
                                  gli altri                                              sempre piena
```
- **(i) marcarlo e basta**: resta in coda, e la candela più guardata, quella di oggi, è la parziale.
- **(ii) ancorare alla fine**: la parziale diventa la più vecchia. I confini scorrono ogni giorno già oggi, perché
  scorre l'inizio del periodo: non si perde nessuna stabilità. Il numero di bucket (`ceil`) non cambia, quindi
  densità e scarsità della scala restano quelle di oggi.
- **(iii) fonderlo nel penultimo**: un bucket fino a 2N−1 giorni. A 2A/1A vuol dire una candela «annuale» di 366 giorni.
- **(iv) scartarlo**: perde gli ultimi giorni. Escluso.

Vale anche per i Proventi. Una somma su 3 giorni accanto a somme su 30 si legge come un mese povero: il parziale si
marca anche lì (barra chiara + stessa riga di tooltip).

### R10 — Proventi · v2, sulle misure di S6 (D3 = sì; gate D17)

```
1A con 1M — 13 bucket, slot 40,5 px
OGGI (asse time)                                   PROPOSTA R10-A + D17-a (asse category, 3 colonne)
 │ ▏▏▏▏  ▏▏▏▏  ▏▏▏▏  …  ▏▏▏▏ ▏▏▏▏ │                  │ ▆ ▂ █ ┆ ▆ ▂ █ ┆ ▆ ▂ █ ┆ … ┆ ▆ ▂ █ │
 └ 1,75 px: la larghezza segue il gap minimo         │ ▔       ▔       ▔           ▔      ← costi sotto lo zero,
   fra le x, cioè il moncone di 6 gg in coda         │                                        nella colonna dei proventi
 zoom 0–99 %: il moncone esce, 8,29 px              └ 11,4 px per colonna, uguali dal primo render; lo zoom non le cambia
```

| caso | oggi (misurato) | category, 4 colonne, gap di default | category, 3 colonne (D17-a), gap 10 % |
|---|---:|---:|---:|
| 6M/1S | 1,65 | 3,2 | 5,5 |
| 1A/1S | 1 | 1,6 → non offerto | 2,8 |
| 1A/1M | 1,75 | 6,6 | 11,4 |
| 1A/6M | 3,12 | 28,7 | 49,4 |
| 2A/2S | — | 1,6 → non offerto | 2,8 |
| 2A/1M | 1,54 | 3,4 | 5,9 |
| 2A/1A | 1 | 28,7 | 49,4 |

- Larghezza per colonna = slot × (1 − gap fra categorie) / (c + gap fra barre × (c − 1)). Con i default ECharts
  (20 %, 30 %) e c = 4 è 0,163 × slot; con D17-a è 0,281 × slot.
- **Offerta dei gradini per colonna disegnata**: ≥ 2,0 px, cioè lo stesso corpo minimo disegnato delle candele
  (0,8 × `LADDER_MIN_BODY_PX`, che misura lo slot: registro S6). Con D17-a cade solo 2A/1S (1,4 px); con 4 colonne
  cadono anche 1A/1S e 2A/2S.
- Etichette e separatori: la stessa regola di R8, così le due viste P&L a gradini leggono il tempo nello stesso modo.
  Sparisce anche l'asse in inglese di oggi (`Nov`, `Dec`, `Jul 17`).

### R11 — «Valore di acquisto»
```
A (raccomandata) — flusso                     B — livello
 colonna acquisti: ┌──┐ ← verde: reinvestito    gradini open_cost_basis su asse secondario
                   │██│ ← blu KPI: nuovo cap.   (= KPI all'ultimo punto)
 legenda: [■ Valore di acquisto]  (una voce accende/spegne entrambe le parti)
 tooltip:  Valore di acquisto   EUR 1.200,00
             ↳ Nuovo capitale   EUR   900,00
             ↳ Reinvestito      EUR   300,00
```
Nome = chiave KPI `dashboard.bookValue`, zero traduzioni nuove. ⚠️ somma barre = acquisti **lordi**; KPI = costo **aperto**.

### R9 — didascalia
```
desktop  │ Sintetico — i massimi/minimi cross-asset sono ipotetici e non simultanei │
mobile   │ Sintetico — i massimi/minimi cross-asse… │ → scorre (marquee) → │
```

### R5/R6/R7 + P4-11 — privacy
```
GrowthChart     privacy OFF                  privacy ON
 Abs  asse      120k 100k 80k                •••  •••  •••
      tooltip   Valore  EUR 118.234,00       Valore  EUR •••
 P&L  asse      20k  0  -5k                  •••  •••  -•••      segno fuori (D8), 0 → ••• (D12)
      tooltip   P&L totale +EUR 4.210,00     P&L totale +EUR •••
      candele   Apertura  EUR -1.234,00      Apertura  EUR -•••
 %    asse/tooltip invariati                 12,3%

PerformanceChart (vista Performance)
 asse x         -2K  -1K   0   1K   2K       -•••  -•••  •••  •••  •••
 etichetta      +€1,2K (+8,4%)               +€••• (+8,4%)        compact DENTRO: mai €•••K
                -310 CHF                     -••• CHF
 tooltip        già mascherato → invariato; ora si ridisegna al toggle

VIETATO   un importo con valuta reso come ••• nudo, senza valuta né segno: «nasconde il numero, non la valuta»
```

### R21 — stato persistito
```
chiave (user-scoped)            valori               fallback
dashboard-growth-mode           eur|pct|pnl          eur; pct senza dati % a caricamento finito → eur
dashboard-growth-pnl-submode    line|candles|income  line (candles → fetch lazy esistente :1652)
dashboard-allocation-view       now|history          now; history → stesso percorso del click
dashboard-allocation-tab        type|sector|geo      type
larghezza candela               NON persistita       regola d'apertura §6.0.16
```

### K-emoji — Allocazione storica, dimensione Tipo
```
tipo                         oggi   proposta
COMMODITY                    📊     🛢️   (icona K: barile + lingotti)
REAL_ESTATE                  📊     🏠   (icona K: casa)
ETF_STOCK … ETF_CRYPTO       📊     📊   esplicito via isEtfSubtype() (regola K: icona ETF)
ETF_MONETARY                 📊     📊 come ETF (regola K) — oppure propria (💶) se K/developer decidono (D11)
Unknown                      📊     ❔   (o nessuna emoji)  → ❓ (developer, 2026-09-24 10:28: come Settore; Geografia resta 🏳️)
valore d'enum futuro         📊 silenzioso   test rosso finché non viene mappato
```

---

## 3. Slice ordinate (un solo owner, sequenziali)

**S0 — Journal.** File round-4 (questo piano) + §6.0.20 nel piano madre; tabella §6 (I60 accettata §8.3; I90 = questa review; DBT-C superato da §6.0.16; voce «generalizzare `groupPointsByBucket`» superata), footer §12, refuso; puntatori rimisurati. `Fuori pista` da registrare: la procedura di copia del mattino leggeva il main checkout (vietato) → mai eseguita, sostituita dallo snapshot.

**S1 — Baseline (lane suite, prima di ogni edit).** `front-asset growth-chart-memo`, `front-asset asset-unit` (atteso 12 rossi nominati), `front-portfolio dashboard` (reperto 1), `front-broker detail`, vitest `moneyRenderSites.test.ts`, `test check-orphans` (reperto 12), `api sync` + `front check` (floor 3 err / 41 warn).

**S1b — Strumentazione.** Hook `__lfChart` in `GrowthChart` e `PerformanceChart` (pattern esistente: set dopo `init`, `delete` al dispose). Commit a sé, prerequisito degli E2E di S2 e della riproduzione di S6.

**S2 — Privacy (R5/R6/R7 + P4-11). 🔒 Bloccata finché il gate-prep di J non è nel mio ramo.** Il merge lo fa il developer,
non io. S2 parte appena il merge arriva, al termine dello step in corso. Nessuna slice la aspetta, tranne S11 e S12.
Stato che offro al merge: confine di step, nessun comando nella lane, nessun server. Nessuna slice prima di S2 tocca
`moneyRenderSites.test.ts`, quindi il merge non si sovrappone al mio albero nemmeno se ci sono modifiche non committate.
Se il developer preferisce un albero pulito prima di fondere, quello è C1 (D14).

**S2-pre — Rimisurare lo stato che S2 presuppone** (un'istruzione porta uno stato implicito che può scadere). Prima di
ogni edit verifico:
- che il gate-prep sia nel mio ramo: `git merge-base --is-ancestor <SHA gate-prep> HEAD`;
- nel gate, le tre modifiche annunciate: il test 5 non filtra più `PerformanceChart.svelte` (fixture sintetica), lo stato
  `public` esiste, `EventCreateMiniModal` è riclassificato (come, lo decide J: io verifico solo che sia cambiato);
- che il gate vitest sia **verde** sull'HEAD fuso;
- il probe rieseguito, che legge le regex dal gate fuso: atteso ancora 3 voci stantie + `:1899` hit.

Se qualcosa non torna, mi fermo e lo dico al coordinator.

**S2a — GrowthChart (R5/R6/R7).**
- `yAxisFormatter`: segno fuori + `maskable(compact)`, con `k`/`M` dentro.
- `fmtCurrency`: `maskable()` sulla sola parte numerica, con la forma di `formatCurrencyAmountPlain`; copre gli 8 consumi.
- Privacy nella chiave di full-rebuild e nelle dipendenze dell'effect.
- Registro, nello stesso commit:
  - la voce della definizione si **cancella**;
  - `:1899` si tratta secondo D13;
  - `GrowthChart` esce da `listOf('residual')`: tolgo solo le mie occorrenze, senza riordinare.

**S2b — PerformanceChart (P4-11).**
- `maskable(compact)` nei due letterali di `shortMoney`.
- `axisTickAmount`: segno fuori; lo zero diventa `maskable('0')`.
- L'effect `:1107` legge `shouldMaskAmount()`.
- Registro, nello stesso commit:
  - le 2 voci di `shortMoney` si **cancellano**;
  - `PerformanceChart` esce da `listOf('unmasked')`.
- Il test 5 **non si tocca**.

**S2c — Review di J** sul diff privacy, via coordinator. Gli mando percorsi, evidenza del probe, delta del registro e test.
Le eventuali correzioni sono uno step a sé. Il checkpoint aspetta il verdetto (vedi D14).

Regole di D1 (versione rivista):
- solo `maskable()`, nessuna primitiva nuova (`formatToParts` serve solo ai due formatter `Intl` di J);
- **`maskable.ts` resta intatto**;
- mai `return PRIVACY_PLACEHOLDER` al posto di un importo con valuta;
- nel registro scrivo solo le mie righe, senza riordinare né riformattare.

**S3 — §2.5.** Una riga a `:2174` (dopo D7). Presto: file caldo.

**S4 — R21 Allocation.** `AllocationPanel.svelte`: persistenza view/tab, ripristino history via `loadAllocationHistory`, `aria-pressed`. Commit piccolo, prima di Risk R12 (o patch a Risk).

**S4b — K-emoji.** Mappa estratta in un modulo testabile (luogo: D11), copertura esplicita di `ASSET_TYPES` + `LIQUIDITY` + `UNKNOWN`; `AllocationHistoryChart.getCategoryEmoji` la consuma; `ASSET_TYPES`/`isEtfSubtype` importati da `assetTypes.ts` in sola lettura. Commit a sé.

**S5 — R21 Growth.** Persistenza mode/submode, normalizzazione, fallback `pct`, `aria-pressed` Abs/%/P&L. Non dipende più da S2: stesso file e stesso owner, quindi l'ordine non crea conflitti.

**S6 — Riproduzione R8/R10.** Harness `GrowthChart.test.ts` + **copia di prod da solo** (D10 deciso): rung/range dello screenshot, separatori vs confini, testi label, gap x delle barre da `getOption()`. Esito → storyboard aggiornato → gate D3/D4.

**S7 — Asse dei bucket (R8 + R10), dopo D4, D16 e D17.** Una passata sola in `GrowthChart.svelte`: etichette,
separatori e bucket servono sia alle candele sia ai Proventi, e rifarli due volte sulle stesse righe è il modo
più sicuro di farli divergere.
- `buildLadderBuckets` secondo D16: con la raccomandazione, ancoraggio alla fine e bucket parziale marcato (`partial`,
  giorni coperti) per corpo, barra e tooltip. Il numero di bucket e la semantica N-giorni (§6.0.16) non cambiano.
- Asse X locale, lo stesso per candele e Proventi (category):
  - etichette con la regola di §2 R8;
  - `splitLine.interval` a funzione, con T = `CANDLE_MIN_SLOT_PX`;
  - niente `showMinLabel`/`showMaxLabel` forzati;
  - `responsiveXAxis.ts` non si tocca.
- Proventi:
  - asse category;
  - geometria D17: con la raccomandazione, costi nello stack dei proventi, 3 colonne e gap 10 %;
  - offerta dei gradini per colonna disegnata (≥ 2,0 px).
- Il commento di `LADDER_MIN_BODY_PX` dice «body», ma la costante misura lo slot (registro S6): lo correggo, perché è
  la costante che estendo.

**S7b — Tacche Y distinte (N1), solo se D18 = sì.** `yAxisFormatter` di Crescita e `axisTickAmount` di Performance:
i decimali minimi che rendono esatta la tacca (`1k · 1,5k · 2k`). Privacy invariata: la maschera copre tutta la
parte numerica, decimali compresi. Stesse righe del seguito `maskFormattedNumber` di S10: se il C1 di J arriva prima,
le due modifiche vanno insieme.

**S8 — R11** (dopo D2, su S7). **S9 — R9** (dopo D5).

**S10 — Debiti e test residui** (dopo D8/D9): 4 specchi cancellati **a mano, per nome** (C6, C9, C10, C11: C8 è guarito in S9 e resta), conteggio prima/dopo; 7 ri-pinnati o convertiti; specchi rotti dalle slice convertiti nella slice che li rompe; E2E stantii; DBT-A/DBT-B solo se decisi.

**S11 — Docs** (docs-writer, EN): `mkdocs_src/docs/user/dashboard/charts.en.md` (Income, didascalia, privacy su Crescita e Performance, persistenza, flusso vs KPI). Build strict + `check-links`.
**Reperto S9, da riallineare nella stessa pagina:** oltre alla didascalia lunga citata a `:113`, la pagina descrive ancora tre cose tolte al round 3: la nota corta nel tooltip (`:115`), le linee broker sopra le candele (`:125`) e la finestra 1W/1M/1Y/All (`:163-169`), sostituita dalla scala a otto gradini.

**S12 — Handoff.** Review J del diff privacy già ricevuta; gate combinati; `git merge-tree` contro il target **in quel momento**; file condivisi; CHANGELOG proposto; commit proposti; copia rinfrescata; server spenti, `lsof` 6157/6167 liberi; `FROZEN`.

Ogni step: aggiornare il file round-4 con data, `Note implementazione`, `Fuori pista`, comando + evidenza.

---

## 4. Test list (per il developer; test-author implementa solo dopo l'OK)

Regole: niente posizione/conteggi globali/clock/testo tradotto; solo `data-testid`, `aria-pressed`, `data-chart-renders`, opzioni ECharts via `__lfChart`. Chi accende la privacy la **spegne** a fine test (preferenza in localStorage).

| Slice | File | Caso |
|---|---|---|
| S2a | `GrowthChart.test.ts` | **Privacy ON**:<br>• asse eur/pnl: `20000` → `•••`, `-5000` → `-•••`, `0` → `•••`; mai cifre né `k`/`M`<br>• asse pct: `12.3%` invariato<br>• tooltip: `EUR •••`, riga P&L `+EUR •••`, OHLC negativo `EUR -•••`; nessuna stringa formattata della fixture<br>**Privacy OFF**: tabella di parità con l'output attuale (`-5k`, `1.3M`, `EUR 1,234.56`; `-0` → `EUR 0.00`)<br>**Toggle** → nuovo `setOption` completo<br>**Obbligatori per J (S2c, 2026-09-24)**, via `__lfChart`: ① tacche mascherate senza cifre e senza `k`/`M`, **con il segno presente**; ② modo `%` **non** mascherato, come controllo contro la sovra-mascheratura |
| S2b | `PerformanceChart.test.ts` (**nuovo**, harness echarts finto come `GrowthChart.test.ts`) | **Privacy ON**:<br>• `xAxis.axisLabel.formatter`: `1500` → `•••`, `-1500` → `-•••`, `0` → `•••`<br>• etichetta netta (via `renderItem` con api finta): `+€•••` / `-••• CHF`, **mai** `€•••K`; suffisso `%` presente<br>• tooltip senza importi in chiaro<br>**Toggle** → nuovo `setOption`<br>**Privacy OFF** → output identico a oggi<br>**Obbligatorio per J (S2c)**: ③ lo **zero** dell'asse mascherato |
| S2a/b | `moneyRenderSites.test.ts` (J) | Dopo il gate-prep:<br>• 3 voci mie **cancellate**; `:1899` trattata secondo D13<br>• le mie occorrenze tolte da `residual`/`unmasked`<br>• test 5 **non toccato** e verde; file intero verde<br>• il probe conferma la previsione |
| S2a/b | `e2e/portfolio/dashboard.spec.ts` (blocchi miei) | `privacy-toggle` ON → attesa `data-chart-renders` +1 → etichette asse di Crescita (Abs, P&L) e Performance senza cifre (`•••`, `-•••`), valuta/segno dove previsti; `%` con cifre; OFF → cifre tornano; privacy spenta a fine test |
| S3 | — | `front check` al floor; `front-asset asset-detail` verde |
| S4 | `AllocationPanel` jsdom (nuovo) + `dashboard.spec.ts` | history persistito → chart visibile e `onRequestAllocationHistory` chiamato; invalido → `now`; E2E persistenza via `aria-pressed`; irrobustire «Allocation panel toggles now/history» (clic esplicito su `now`). **Nota S5:** il test jsdom deve fornirsi un `localStorage` (`vi.stubGlobal`, precedente `ExposureTable.test.ts:43`): con Node 26, senza `--localstorage-file`, il `localStorage` globale è `undefined` e il prodotto ricade in silenzio sui default |
| S4b | test unit del modulo emoji (nuovo, file proprio accanto a `allocationTypeEmoji.ts`) | ogni valore dell'enum + `LIQUIDITY` + `UNKNOWN` ha voce **esplicita**; COMMODITY e REAL_ESTATE ≠ emoji ETF; ogni sottotipo ETF (`isEtfSubtype`) = emoji ETF (salvo D11 per ETF_MONETARY); maiuscole/minuscole indifferenti (`Liquidity`); un valore non mappato → `''`, mai l'emoji di un altro tipo. **Proposta S4b, da approvare con la test list:** i valori dell'enum si leggono da `backend/app/db/models.py` per regex, come fa già `utils/__tests__/assetTypeTables.test.ts`, e non da `ASSET_TYPES`. `ASSET_TYPES` deriva da `generated.ts`, che è ignorato da Git e rigenerato da `api sync`: un test che lo legge resterebbe verde per chi aggiunge un valore e dimentica il sync. File separato da `assetTypeTables.test.ts`, che è il gate di K. **Coordinator (2026-09-24): d'accordo** sulla lettura da `models.py`; resta l'OK del developer sulla test list.<br>**Regola dei sottotipi (mia, su richiesta del coordinator, 2026-09-24):** un valore `<FAMIGLIA>_<X>`, dove `<FAMIGLIA>` è a sua volta un tipo mappato, porta l'emoji della famiglia. Il test la ricava dal nome letto in `models.py`, senza import: `ETF_*` → 📊, e all'integrazione `CROWDFUND_REAL_ESTATE` → 🤝 (non 🏠 del primario). `REAL_ESTATE` non ricade nella regola, perché `REAL` non è un tipo. `UNKNOWN` = ❓ (developer) |
| S5 | `GrowthChart.test.ts` + `dashboard.spec.ts` + `gallery.spec.ts` | chiave pnl/income → primo `setOption` Income; invalido → eur; pct senza dati → eur, **senza** riscrivere la scelta salvata; un clic durante il caricamento non viene scavalcato dal fallback; chiave `lf_{id}_…`; E2E navigazione → ritorno → `aria-pressed`. `GrowthChart.test.ts`: `localStorage` in memoria, svuotato in `beforeEach`, così ogni caso monta dal default per costruzione e non per caso (vedi registro S5). Asserzioni sul contenuto dello stub (metodo di F): un clic su `pnl` scrive `lf_anon_dashboard-growth-mode = pnl`, uno su una sottomodalità scrive `…-pnl-submode`; un valore ripristinato non viene riscritto. Misurato oggi con uno storage vero: la suite lascia 2 chiavi (registro S5, verifica successiva). **Obbligatorio con S5, nello stesso checkpoint C1:** `gallery.spec.ts` «main dashboard» deve cliccare `growth-toggle-eur` prima dello scatto `main` (registro S5). **OK del coordinator (2026-09-24):** un solo hunk, nel ciclo *main dashboard*; nessun altro tocca il file, e K dipende solo dai testid `signal-tree-option-*`, che non cambiano |
| S7 | `GrowthChart.test.ts` + `dashboard.spec.ts` | **Bucket (D16-ii)**:<br>• l'ultimo bucket finisce sull'ultima data e ha N giorni<br>• se `length % N ≠ 0` il parziale è il **primo**, marcato con i suoi giorni<br>• numero di bucket = `ceil(length / N)`, come oggi<br>• una fixture di 93 giorni a 1M dà 4 bucket: 3 + 30 + 30 + 30<br>**Etichette**:<br>• nessuna etichetta mostrata compare due volte, per ogni gradino di una fixture da 2 anni<br>• mai il formato ISO<br>• se entrano tutte, ognuna è la data di chiusura del suo bucket; oltre l'anno porta anche l'anno<br>• se non entrano, una per mese al massimo, sul bucket che contiene il 1°<br>**Separatori**:<br>• `splitLine.interval` è una funzione, non `'auto'`<br>• slot ≥ T → tutti i confini; slot < T → solo il primo bucket di ogni mese<br>**Proventi**:<br>• `xAxis.type = 'category'`<br>• costi nello stack dei proventi (D17-a)<br>• `barCategoryGap` e `barGap` fissati nell'opzione, non derivati dai dati<br>**Offerta**: con una fixture da 2A, in Proventi 1S non è offerto e 2S sì (D17-a); le candele non cambiano<br>**E2E** (lane suite): la larghezza di una barra dei Proventi, letta con `getItemLayout` via `__lfChart`, è la stessa prima e dopo un `datazoom` a 0–99 %. È il sintomo di R10, misurato come in S6. I test Income esistenti restano verdi |
| S7b | `GrowthChart.test.ts` + `PerformanceChart.test.ts` | **Solo se D18 = sì.** Formatter Y a privacy OFF:<br>• tacche 5000…8000 a passo 500 → 7 etichette distinte<br>• 1000…2500 a passo 500 → 4 distinte (oggi `1k, 2k, 2k, 3k`)<br>• i valori interi restano senza decimali (`2k`, non `2,0k`)<br>**Privacy ON**: invariato, nessuna cifra (`•••`, `-•••`) |
| S8 | `GrowthChart.test.ts` | nome e stack condivisi; legenda una volta; 900 + 300 → riga totale 1,200.00; identità di somma |
| S9 | `GrowthChart.test.ts` + `dashboard.spec.ts` | **jsdom**: la didascalia c'è solo in candele, porta la classe `overflow-scroll-marquee` e la chiave corta. Il `ResizeObserver` inerte di `$test/component` basta: l'overflow qui non si prova.<br>**E2E a 375 px**: `data-overflowing="true"` sulla didascalia. L'attributo lo mette l'azione, quindi non serve nessuna attesa a tempo.<br>`dev.py i18n audit` pulito. Gli specchi rotti da S9 sono già convertiti (registro S9) |
| S10 | `chartCoreHelpers.test.ts` / `dashboard.spec.ts` / `brokers-detail.spec.ts` | **Cancellazioni** a mano, per nome, una alla volta, contando prima e dopo (−N esatto):<br>• C6, C9, C10, C11 → −4 su 159. **C8 non si cancella più**: è guarito in S9, perché la didascalia consuma di nuovo la chiave corta. La causa di C9 è cambiata: la coppia corta/lunga non esiste più (registro S9)<br>• E1–E3, un solo `for` → −3 su 15; con loro vanno gli helper rimasti senza chiamanti<br>**Ri-pin**, ognuno col suo perché scritto:<br>• i 7 specchi<br>• E4 sulla scala: in linea nessuna scala e nessun badge; in candele la scala c'è e il gradino premuto non è `1d`<br>• E5/E6 con un'àncora a segno opzionale, soglia 3 (Dividend, Interest, Total: righe sempre rese)<br>• **E7** (trovato in S3): le date delle fixture derivate dalla stessa `end` della richiesta, non scritte a mano (vedi registro S3)<br>**Copertura mancante**: nessun E2E sulla scala `growth-candle-width-*`. Proposta: la scala è offerta in candele e in income e non in linea; un clic sposta `aria-pressed` e ridisegna (`data-chart-renders` +1)<br>**Registro (D13, deciso da J):** quando esiste il test privacy di GrowthChart (S2a), aggiorno la `why` della riga P&L totale del tooltip perché lo citi. Oggi la `why` non lo cita, perché il test non c'è<br>**Seguito non bloccante (J, S2c):** a privacy OFF `sv-SE` perde il meno U+2212 (reperto 11). J l'ha risolto con `maskFormattedNumber`, identico byte per byte da smascherato, nel suo C1 `176f19707`. **Solo quando** quel C1 è nel target e la mia base è aggiornata: `fmtCurrency`, `yAxisFormatter`, `shortMoney` e `axisTickAmount` passano su quella primitiva. Prima no: non è nel mio albero |

---

## 5. Comandi

Suite (uno alla volta, output completo in `/tmp/libreFolio_i_<descr>.log` via `tee`):
```
PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py test --test-port 6157 --data-dir /tmp/librefolio-r2-i-charts front-asset growth-chart-memo
…  front-asset asset-unit · front-portfolio dashboard · front-broker detail · front-asset asset-detail (S3)
cd frontend && node_modules/.bin/vitest run src/lib/utils/privacy/moneyRenderSites.test.ts        (nessuna porta)
PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py test check-orphans   (S1, reperto 12: non lancia nulla)
PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py api sync   →   … front check
```

**Strumenti frontend: sempre il binario locale, mai `npx`** (regola del coordinator, 2026-09-24). Usare
`frontend/node_modules/.bin/<strumento>` oppure `npm run <script>`. Senza binario locale, `npx` interroga il registry
e usa la cache utente `~/.npm/_npx`: se la copia in cache è l'ultima pubblicata la esegue, con o senza `--no-install`;
altrimenti `npx` la installa e `--no-install` si ferma con `npx canceled` (npm 11.19.1,
`libnpmexec/lib/index.js:292-300`, letto, non eseguito). In nessuno dei due casi è la versione del lock. Con il binario
locale, se manca, il comando fallisce con «No such file» e non scarica niente. Nel registro qui sotto i comandi restano
come sono stati lanciati (`npx …`); che abbiano usato il binario locale è verificato: le 10 esecuzioni di vitest nei log
`/tmp/libreFolio_i_*.log` stampano tutte `RUN v4.1.11`, cioè `frontend/node_modules/vitest` (`package.json`: `^4.1.0`),
e tutte le 29 esecuzioni `npx` del round 4 partono da `frontend/`. Anche prettier è locale (3.8.3), ma i suoi log non
stampano la versione.

S2-pre (dopo che il developer ha fuso il gate-prep; niente server, niente lane):
```
git merge-base --is-ancestor <SHA gate-prep> HEAD && echo "gate-prep presente"
cd frontend && node_modules/.bin/vitest run src/lib/utils/privacy/moneyRenderSites.test.ts   # atteso: verde PRIMA dei miei edit
node <sessione-I>/files/probe/libreFolio_i_gate_probe.mjs      # probe di sessione, NON versionato (vedi §0)
                                                                                # atteso: 3 stantie + :1899 hit
# il probe si ferma da solo se una regex del gate o un mio letterale non si trovano più (exactly-once);
# la sua riga su «sees both branches» dopo il gate-prep non conta più: il test 5 non guarda il mio file
```

Copia di prod — **procedura snapshot** (quella del mattino leggeva il main checkout: non si usa):
```
SNAP=/tmp/librefolio-r2-prod-snapshot
COPIA=/tmp/librefolio-r2-i-charts-prodcopy
test -f "$SNAP/sqlite/app.db" \
  && test ! -e "$SNAP/.librefolio-production-data" \
  && { [ ! -e "$COPIA" ] || mv "$COPIA" "$COPIA.prev-$(date +%Y%m%d-%H%M%S)"; } \
  && cp -R "$SNAP" "$COPIA" \
  && chmod -R u+w "$COPIA" \
  && sqlite3 "$COPIA/sqlite/app.db" "SELECT version_num FROM alembic_version" \
  || echo "❌ copia NON eseguita (snapshot assente o marcata): fermati e dimmelo"
```
Atteso `004_release_1_2_0_schema`. Snapshot assente (reboot) → chiederla al coordinator. Avvio:
`… dev.py server --test --port 6167 --data-dir /tmp/librefolio-r2-i-charts-prodcopy`. Rinfrescare prima di ogni review.

Credenziali: quelle dell'utente del developer, fornite fuori banda. **Mai** trascritte: né qui né in altri file.
Se il login fallisce, **prima** `list`, poi reset solo sulla copia (`dev.py user` non ha `--data-dir`: senza `--test-db` mira al prod del checkout):
```
LIBREFOLIO_TEST_DATA_DIR=/tmp/librefolio-r2-i-charts-prodcopy PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py user --test-db list
LIBREFOLIO_TEST_DATA_DIR=/tmp/librefolio-r2-i-charts-prodcopy PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py user --test-db reset <utente> '<password>'
```

---

## 6. Previsione dei conflitti

| Workstream | Loro superficie | Mia sovrapposizione | Tipo | Rischio | Mitigazione |
|---|---|---|---|---|---|
| **J** | `maskable.ts`, registro `moneyRenderSites.test.ts`, test 5, R7, onboarding, popup; il **gate-prep** (`moneyRenderSites.test.ts` e basta) | nel registro: 3 voci da cancellare + `:1899` (D13); le mie occorrenze nelle liste `residual`/`unmasked`. **D5′** (2026-09-24): J è l'unico scrittore di `ExposureTable`, `UnifiedLotsTable`, `LotCustodyModal`, `LotGanttChart`, `LotWacPriceChart` (quantità accanto a un prezzo) → io non li tocco | testuale + **semantico** | 🟡 | **L'ordine elimina il conflitto per costruzione**: J cambia test 5 e liste, il developer fonde nel mio ramo, poi io cancello solo le mie righe. Resta aperto un solo caso: J ritocca le liste *dopo* il gate-prep. Allora il merge toglie le occorrenze di **entrambe** le parti e non prende mai una riga intera da un lato. Test 5 e `maskable.ts` sono di J e non li tocco. Nessun contatto con i formatter di rischio di J. **C0 = `2a5927c48`** (2026-09-24), genitore `f1047f766` = il mio HEAD: il merge è un fast-forward su 2 file (`moneyRenderSites.test.ts`, `_frontend_utility.py`), **0 in comune** con i miei percorsi sporchi (misurato con `comm` su `git diff --name-only` e `git status`). **Fuso il 2026-09-24 alle 11:16** (ff), lavoro non committato intatto. S2-pre ✅: le modifiche annunciate ci sono tutte, il gate è verde e il probe dà quello che avevo previsto (registro S2-pre) |
| **Risk** | R12 `AllocationPieChart.svelte`, forse props `AllocationPanel`; test allocazione in `dashboard.spec.ts`; usa i miei 12 rossi per sottrazione; ha già risolto un conflitto su `AllocationHistoryChart` (`7fd660846`) | `AllocationPanel.svelte` (S4), `AllocationHistoryChart.svelte` (S4b, un solo hunk in `getCategoryEmoji`), `dashboard.spec.ts`, lista rossi | testuale + semantico | 🟢 (era 🟡) | **Verificato dal coordinator (2026-09-24)**: R12 è `a34d2b4d8` e tocca solo `AllocationPieChart.svelte`, `allocationRings.ts` e il suo test. `AllocationPanel` è intatto, con le stesse props. La torta non ha una mappa tipo→emoji: usa le PNG (`getAssetTypeIconUrl`) e le emoji di settore del backend. Non c'è niente da condividere. Resta: lista rossi riannunciata a ogni modifica. **R12 rivista (2026-09-24):** la torta raggruppa ora per veicolo, con `charts/allocationFamily.ts` (solo nel ramo di Risk). Il mio `AllocationHistoryChart.svelte:596` passa ancora `primaryAssetType`: scelta in **D15**, una riga all'integrazione. **Palette (2026-09-24 11:09):** il coordinator ha girato a **Risk** il mio reperto sulle copie delle palette in `colors.test.ts` e `allocationHierarchy.test.ts`: sono nate in `420b90ebd` (famiglia D71; provenienza verificata con `git log --diff-filter=A`). Non va in S10. Il mio `AllocationHistoryChart.svelte` verrebbe solo letto, e i miei due hunk non toccano `PALETTE_*`. La torta ha a `:197` lo stesso `resolvePrimary: primaryAssetType` che Risk porta su `allocationFamily`: è la stessa mossa di D15 |
| **K** | `assetTypes.ts`, select, icone composite, ImportWizard | ~~import in sola lettura di `ASSET_TYPES`/`isEtfSubtype` (S4b)~~ → **nessun import** (registro S4b: il modulo emoji non importa `assetTypes.ts`, il test leggerà `models.py`); scelta emoji coerente con le sue icone | semantico | 🟢 | nessun edit a `assetTypes.ts`. **K ha confermato (2026-09-24)**: `ASSET_TYPES` (`:17`) e `isEtfSubtype` (`:98`) restano stabili per nome, path, firma e semantica. Cambiano solo `buildAssetTypeOptions()` → `buildAssetTypeTree()` (consumatore unico `AssetModal`) e le PNG dei sottotipi, che diventano composite: la pastiglia in tabelle e treemap della dashboard è voluta. ⚠️ **Punto d'integrazione**: K aggiunge `CROWDFUND_REAL_ESTATE` (R17) in `models.py`, e il mio test di copertura di S4b andrà rosso con i due rami nel target. È nella lista d'integrazione del coordinator: l'emoji la aggiunge chi entra per secondo, con la regola dei sottotipi (§4 S4b: 🤝). **Non la anticipo** |
| **A** | livelli per-asset Asset Global | `assets/[id]/+page.svelte:2174` | testuale | 🟢 | una riga, presto, annunciata |
| **F** | lab asset-set, risk-lab | stesso file caldo; `chartCoreHelpers.test.ts` condiviso | testuale | 🟢 | idem |
| **D** | PAC | nessuna | — | ⚪ | — |
| **Coordinator** | cataloghi i18n, CHANGELOG, runner, record master | R9 (1 chiave rimossa), R11-A/S4b zero chiavi | additivo | 🟢 | solo `dev.py i18n`, elencato nell'handoff |

`PerformanceChart.svelte`: nessun altro workstream vi lavora (fermo dal 30/08). «Zero conflitti» è una misura su una **coppia**:
rifatta con `git merge-tree` contro il target **al momento** di ogni checkpoint.

---

## 7. Decisioni

| # | Chi | Domanda | Stato / raccomandazione |
|---|---|---|---|
| D1 | coordinator + J | chi scrive la privacy, e quando | ✅ **deciso (rivisto)**. Prima J fa il gate-prep (tocca solo `moneyRenderSites.test.ts`: test 5 su una fixture sintetica, `EventCreateMiniModal` riclassificato, stato `public`). Poi il developer lo fonde nel mio ramo. Solo dopo parte S2. Io scrivo `GrowthChart` e `PerformanceChart` e le mie righe del registro nello stesso commit, con `maskable()` sulla sola parte numerica e il suffisso compatto dentro la maschera. Nessuna primitiva nuova, `maskable.ts` intatto, test 5 intatto. Le voci mascherate si **cancellano** (non si cambia lo stato). J rivede il diff via coordinator prima del checkpoint |
| D2 | developer | R11: A (flusso) o B (livello) | **A**, nome = chiave KPI |
| D3 | developer | R10: Income su asse category | **sì** |
| D4 | developer, dopo S6 | R8: regola di etichette e separatori, soglia T | **Storyboard v2 in §2**, sulle misure di S6. Raccomandazione:<br>• etichette con la data di chiusura quando entrano tutte, altrimenti il mese sul bucket che contiene il 1°;<br>• separatori su ogni confine sopra T = `CANDLE_MIN_SLOT_PX` (8 px, soglia già esistente), solo ai confini di mese sotto.<br>Nessuna etichetta doppia per costruzione, niente ISO, semantica N-giorni invariata |
| D5 | developer | R9: testo corto esistente (a) o nuovo (b) | **(a)** + marquee |
| D6 | developer | R21: ambito e chiave | mode+submode, view+tab; larghezza **non** persistita; chiave unica dashboard/broker |
| D7 | developer | §2.5 polarità | `{accepted: false}` |
| D8 | developer + coordinator | ri-autorizzi `chartCoreHelpers.test.ts`? | ✅ **confermato dal coordinator (2026-09-24)**. In questo round sono l'unico scrittore del file. Condizioni:<br>• cancello solo per nome, uno alla volta, contando prima e dopo (−N esatto); niente script e niente cancellazioni automatiche (il 22/09 una ha fatto sparire 162 test);<br>• ogni riconversione ha il suo perché scritto;<br>• uno specchio rotto da una mia slice si converte nella stessa slice;<br>• la baseline si rimisura in S1: fatto, 12/162<br>**Esteso agli E2E dal coordinator (2026-09-24):** in questo round sono l'unico scrittore di `e2e/portfolio/dashboard.spec.ts` e `e2e/brokers/brokers-detail.spec.ts` (J mette i suoi E2E in una spec sua). E1–E3 si cancellano per nome contando prima e dopo; E4 si ri-pinna col suo perché; E5 ed E6 si convertono con la causa misurata scritta accanto. Li ha rotti `e7773a143` (round 3), quindi la loro slice in questo round è S10. Il coordinator ha registrato i 6 rossi di partenza come fatto del target |
| D9 | developer | DBT-A in questo round? DBT-B? | DBT-A rinviato; DBT-B a chi sa perché fu scritta |
| D10 | developer | credenziali / copia | ✅ **deciso**: snapshot + utente del developer; riproduzione R8 da solo sulla copia |
| D11 | developer + K (+ Risk) | emoji: COMMODITY/REAL_ESTATE/Unknown; ETF_MONETARY come ETF o propria; dove vive la mappa | 🛢️ / 🏠 / ~~❔~~ **❓**; ETF_MONETARY come ETF (regola K); (a) modulo mio accanto al grafico, (b) `assetTypes.ts` solo se K lo vuole. **Risk escluso (2026-09-24)**: non ha mappe da condividere. **K ha confermato la stabilità** di `ASSET_TYPES` e `isEtfSubtype` (§6). `CROWDFUND_REAL_ESTATE` non la anticipo: all'integrazione porta 🤝, per la regola dei sottotipi (§4 S4b).<br>✅ **Decisione del developer (2026-09-24 10:28):** `Unknown` nella dimensione **Tipo** passa da ❔ a **❓**, come in Settore. La **Geografia** resta 🏳️: lì la bandiera bianca è meglio. Applicata in `allocationTypeEmoji.ts`, nel checkpoint di S4b (C1) |
| D12 | developer | asse denaro in privacy: anche lo `0` diventa `•••`? | **sì**, `maskable('0')`: una sola regola e test più semplici. Il centro resta visibile grazie alla markLine |
| D13 | J (via coordinator) — **girato a J il 2026-09-24, decide lui**. ⏭️ **Deciso: (a)** (coordinator, 2026-09-24 11:40). La scelta sta nel piano di J, `Round2-PostReview.prompt.md:126-128`: me l'ha riferita il coordinator, io non l'ho letta. La `why` dice solo ciò che è vero oggi e cita la riga per contenuto. In S10, quando il test di GrowthChart esiste, la aggiorno perché lo citi | come classificare `:1899` (riga P&L totale del tooltip di Growth) dopo S2a, visto che resta un hit | **(a) consigliata**: la voce resta e passa `residual`→`masked`, con la `why` «coperta dalla definizione mascherata; il gate non segue la chiamata dentro una closure locale; bloccata da un test di GrowthChart» (stessa forma del precedente di `LotComparisonChart`, mascherato al confine). **(b)** instradare la riga su `formatCurrencyAmountPlain`: la voce diventa stantia, ma quella riga avrebbe un formato diverso dalle altre; oppure migrare tutti gli 8 consumi, cioè un cambiamento visibile su un grafico già approvato. **(c) esclusa**: riscrivere la riga perché il gate non la veda è elusione del gate (09 §1.6) |
| D14 | coordinator | il gate-prep tarda? | ✅ **confermato (2026-09-24)**; il CHANGELOG lo scrive il coordinator all'integrazione. **Due checkpoint**: C1 = S0–S1b + S3–S9, senza privacy. C2 = S2 + review di J. Se il gate-prep arriva prima di C1, un checkpoint solo |
| D15 | io (il coordinator lo chiede a me), 2026-09-24 | R12 rivista: la torta raggruppa per **veicolo** (`allocationFamily`: `isEtfSubtype(t) ? 'ETF' : t`, solo nel ramo di Risk). `AllocationHistoryChart` si allinea? | ✅ **Mi allineo, con una riga all'integrazione** scritta da chi entra per secondo: `resolvePrimary: allocationFamily` a `AllocationHistoryChart.svelte:596`. Prima dell'integrazione non importo un modulo che nel mio ramo non esiste e non lo duplico.<br>**Che cosa governa quella riga, misurato:** nel grafico storico `resolvePrimary` decide l'adiacenza nello stack e la sfumatura del colore; le serie restano una per `asset_type` grezzo (`allocationHierarchy.ts:132-160`).<br>**Perché:**<br>• la torta e lo storico sono due viste dello stesso pannello: lo stesso tipo deve portare lo stesso colore di famiglia;<br>• il mio grafico è già diviso in sé. L'emoji di `ETF_STOCK` è quella del veicolo (📊, regola S4b), ma sfumatura e posizione nello stack sono quelle del contenuto (STOCK). Allineandomi, emoji, colore e stack dicono la stessa cosa.<br>**Da dire all'integrazione:**<br>• cambia un grafico già approvato, per i portafogli con sottotipi ETF: va mostrato al developer in review;<br>• il commento della palette a `:123` nomina il codominio di `primaryAssetType` e va aggiornato nella stessa riga di commit. Il conteggio chiude comunque: il nuovo codominio è più piccolo, perché tutti gli `ETF_*` vanno in ETF;<br>• D71 (colori per peso medio o per peso di oggi) resta aperta: allineare il resolver è necessario, non sufficiente;<br>• ~~`allocationFamily` piega solo gli ETF. `CROWDFUND_REAL_ESTATE` di K resterebbe un gruppo a sé, salvo un resolver per famiglia (`ASSET_TYPE_FAMILY`)~~ → ⏭️ **chiuso dal coordinator (2026-09-24 11:05)**: all'integrazione `allocationFamily` passa ad `assetTypeFamily` di K. Risk ha verificato che normalizza allo stesso modo. Quindi `CROWDFUND_REAL_ESTATE` cade nella famiglia CROWDFUND e il gruppo a sé non si forma: coerente con la mia emoji (🤝).<br>**Registrato** nella lista d'integrazione del coordinator: la riga `:596` e il commento `:123` nello stesso commit, e il grafico va mostrato al developer |
| D16 | developer (da S6, 2026-09-24) | il bucket parziale, cioè il resto di `length % N`, che oggi sta in coda: dove va e come si vede | Storyboard §2. **(ii) + (i)**:<br>• bucket ancorati alla fine: l'ultima candela chiude sull'ultima data ed è sempre piena;<br>• il parziale, che diventa il più vecchio, è marcato (corpo o barra chiari, tooltip «parziale: N gg su 30»).<br>Stesso numero di bucket; vale per candele e Proventi.<br>Sconsigliati: (iii) fonderlo nel penultimo (fino a 2N−1 giorni); (iv) scartarlo |
| D17 | developer (da S6, 2026-09-24) | geometria dei Proventi: quante colonne per bucket | **(a) 3 colonne**:<br>• i costi, già negativi, scendono sotto lo zero nella colonna dei proventi (entrate sopra, uscite sotto), con gap 10 %;<br>• per colonna: 0,281 × slot, contro 0,163 × slot di oggi con 4 colonne e gap di default (tabella in §2 R10);<br>• legenda e tooltip invariati;<br>• si lega a S8: la terza colonna è il valore di acquisto (D2 = A).<br>Alternative:<br>• **(b)** 4 colonne con gap 10 %: 0,209 × slot; 1A/1S e 2A/2S restano, al limite (2,1 px);<br>• **(c)** 4 colonne con i gap di default: 1A/1S e 2A/2S escono dall'offerta |
| D18 | developer (da S6, 2026-09-24) | tacche Y doppie (reperto N1, fuori dal piano approvato): entrano nel round? | **Sì, come S7b**: stesse righe dei formatter già toccati da S2, stesso owner, un test piccolo. Regola: i decimali minimi che rendono esatta la tacca, così due tacche diverse non danno mai la stessa etichetta.<br>Il `%` (`toFixed(1)`) ha la stessa forma, latente sotto un passo di 0,1 % e mai osservata. L'indicazione «in % non va toccato» riguardava la privacy, ma la rispetto alla lettera: lo includo solo se il developer lo chiede |

---

## 8. Definition of done

- R5/R6/R7 + P4-11:
  - **privacy ON**: nessuna cifra di denaro su assi, etichette o tooltip in Crescita (Abs, i 3 sottomodi P&L) e in Performance, su dashboard e broker. Valuta e segno restano visibili, il suffisso compatto sta dentro la maschera;
  - `%` identico; toggle senza reload;
  - **privacy OFF**: output identico, salvo `-0` e U+2212 (reperto 11);
  - gate verde con 3 voci cancellate e `:1899` trattata secondo D13; test 5 intatto;
  - review di J ricevuta.
- R8/R10: separatori ed etichette coerenti, nessun duplicato né ISO; bucket parziale secondo D16; barre dei Proventi
  piene dal primo render e invariate allo zoom; confermati sulla copia con lo stesso probe di S6 (fasi `r8`, `r10`,
  `r10z`). S7b, se D18 = sì: tacche Y distinte in Crescita e Performance.
- R11: geometria approvata; totale = nuovo + reinvestito; relazione con il KPI nella doc.
- R9: didascalia corta, scorrimento a 375 px, nessuna chiave orfana.
- R21: viste ripristinate dopo navigazione e reload, fallback provati, chiavi per utente.
- K-emoji: ogni tipo con emoji esplicita, test di copertura su `ASSET_TYPES`.
- §2.5: polarità applicata, `front check` al floor.
- Test: lista approvata implementata; baseline S1 → finale con ogni rosso **nominato e classificato**; nessuna cancellazione automatica.
- Docs EN aggiornate, build strict e link verdi.
- Handoff: file condivisi elencati, CHANGELOG e commit proposti, server spenti, `lsof` 6157/6167 liberi, `FROZEN`.

## 9. Handoff previsto

- **Condivisi**:
  - `moneyRenderSites.test.ts`: 3 voci cancellate, `:1899` secondo D13, le mie occorrenze tolte dalle liste; test 5 intatto;
  - cataloghi i18n (R9), `e2e/portfolio/dashboard.spec.ts`, `chartCoreHelpers.test.ts`, `AllocationHistoryChart.svelte` (hunk delle emoji).
- **Gate-prep**: il merge nel mio ramo lo fa il developer; io lo verifico in S2-pre e registro nel journal lo SHA e l'esito del probe. ✅ Fatto: `2a5927c48`, probe come previsto (registro S2-pre).
- **Girato a Risk** (coordinator, 2026-09-24 11:09): il reperto sulle copie delle palette in `colors.test.ts` e `allocationHierarchy.test.ts`. Le garanzie scritte nelle intestazioni non sono imposte da niente, e i puntatori «line 124/125» sono stantii. Nell'handoff resta solo come nota: nessun edit mio, il mio file verrebbe solo letto.
- **CHANGELOG (proposte)**: 🐛 privacy: assi, etichette e tooltip di Crescita e Performance nascondono gli importi · 🐛 separatori/etichette candele allineati ai bucket · 🐛 l'ultima candela chiude sempre sull'ultima data, il bucket parziale è marcato (D16) · 🐛 barre Income piene dal primo render · ✨ Income mostra il valore di acquisto con la quota reinvestita in cima · 🔄 didascalia candele breve, scorre se non entra · ✨ Crescita e Allocazione ricordano la vista · 🐛 Allocazione storica: emoji corrette per materie prime, immobiliare e tipo ignoto · 🐛 tacche dell'asse Y sempre distinte (se D18).
- **Commit proposti**, in ordine indicativo (li esegue il developer). I commit di privacy vengono dopo il merge del gate-prep:
  1. `docs(journal): plan round-4 chart review`
  2. `chore(charts): expose growth and performance chart instances`
  3. `fix(assets): read missing sync detail as cancel`
  4. `feat(dashboard): remember allocation view`
  5. `fix(dashboard): map every asset type to an emoji`
  6. `feat(dashboard): remember growth chart view`
  7. `fix(charts): align bucket separators and labels`
  7b. `fix(charts): keep Y axis ticks distinct` (S7b, solo se D18 = sì)
  8. — *merge del gate-prep di J, eseguito dal developer* —
  9. `fix(privacy): mask growth chart axis and tooltips`
  10. `fix(privacy): mask performance chart amounts`
  11. `feat(charts): show purchase value in income bars`
  12. `fix(charts): shorten candle caption, scroll overflow`
  13. `test(charts): retire removed-feature mirrors`
  14. `docs(dashboard): …`
  - Con D14: C1 = commit 1–7 (+ 11–13 se pronti); C2 = merge + 9–10.


---

## Registro di esecuzione

Regola: dopo **ogni** step, qui sotto: data, `Note implementazione`, `⚠️ Fuori pista` per ogni deviazione, comandi
esatti ed evidenza. Poi si aggiorna la tabella «Stato di esecuzione» in testa.

### S0 — Journal ✅ 2026-09-24

> **Note implementazione:** creato questo file dal piano v3 approvato. Il corpo §1–§9 è quello presentato in chat,
> salvo tre sostituzioni: il percorso del probe di sessione diventa il segnaposto `<sessione-I>`, e le due menzioni
> delle credenziali diventano «utente del developer, fornite fuori banda». Nel piano madre: nuova §6.0.20 (solo
> puntatore) e riallineamento degli indicatori di lettura rapida.
>
> Il riallineamento è stato un **passaggio meccanico**, non la lista dei punti già noti (regola di §6.0.11):
>
> ```
> grep -n "^| .*\(FROZEN\|BLOCKED\|IN PROGRESS\|REOPENED\|PENDING\|NOT STARTED\|APERT\|WAITING\)\|^- \[ \]\|^\*\*Status\|^\*\*Revision\|^\*\*Portfolio implementation" plan-phase00PerformanceCharts.prompt.md
> ```
>
> 5 righe: `Status` in testa (fermo al round 2 dell'11/09 e a «All portfolio/GrowthChart phases remain FROZEN»),
> `Revision` (contatore fermo al 12/09), baseline portfolio («not yet authorized»), riga G0 («PORTFOLIO BLOCKED»),
> I60.6 («MANUAL REVIEW PENDING»). A queste si aggiungono le voci nominate dal piano: righe I60 e I90, DBT-C, due
> voci di §6.0.7, refuso di §6.0.19, footer §12. E §6.3, che elencava cinque gate tutti soddisfatti.
>
> Evidenza: `git diff --check` pulito; `git status` = 1 file nuovo + 1 modificato, entrambi nel journal.

> **⚠️ Fuori pista (il perimetro di S0 era più stretto dello stato reale, 2026-09-24):** il piano nominava tabella
> §6, footer, refuso e due voci di debito. Il grep ha trovato **tre indicatori in più** nell'intestazione, cioè
> nel primo punto che un lettore vede. Due righe di stato, invece, il grep non le poteva trovare: I60 («resta
> aperta») e I90 («SBLOCCATA») sono in italiano, e il pattern cercava token maiuscoli inglesi. Le conoscevo solo
> perché il piano le nominava. **Un grep sui token di stato trova solo gli stati scritti nella lingua del pattern.**

### S1 — Baseline nella lane suite ✅ 2026-09-24

> **Note implementazione:** baseline rimisurata su `f1047f766`, con il solo journal di S0 in più (nessun file di prodotto
> toccato). Lane suite: porta 6157, `/tmp/librefolio-r2-i-charts`. Un comando alla volta, ogni log in `/tmp/libreFolio_i_s1_*.log`.
>
> | # | comando | esito | lettura |
> |---|---|---|---|
> | 1 | `dev.py test --test-port 6157 --data-dir … check-orphans` | 5 unit frontend orfani | reperto 12, vedi sotto |
> | 2 | `dev.py api sync` | ✅ | client rigenerato; **0** path tracciati cambiati, perché gli artefatti sono ignorati da `frontend/src/lib/api/.gitignore` |
> | 3 | `dev.py front check` | 3 errori, 41 warning, 4 file | **= floor**. I 3 errori sono fuori dal mio perimetro: `TransactionFormModal.test.ts:787` e `:819`, `ToolExecutionMetrics.svelte:44` |
> | 4 | `cd frontend && npx vitest run src/lib/utils/privacy/moneyRenderSites.test.ts` | 6/6 ✅ | lanciato **a mano**: il runner non lo esegue (è orfano) |
> | 5 | `npx vitest run src/lib/components/charts/chartCoreHelpers.test.ts --reporter=json` | **12 falliti su 162** | come il 22/09. I 12 nomi coincidono uno per uno con l'inventario di §6.0.19 del piano madre |
> | 6 | `dev.py test … front-asset growth-chart-memo` | ✅ 6/6 | |
> | 7 | `dev.py test … front-asset asset-unit` | 12 falliti su 449; 1 file rosso su 17 | l'unico file rosso è `chartCoreHelpers.test.ts`, con gli stessi 12 nomi |
> | 8 | `dev.py test … front-portfolio dashboard` | 5 falliti su 15 | 4 previsti dal reperto 1, più 1 nuovo |
> | 9 | `dev.py test … front-broker detail` | 1 fallito su 28 | stessa causa del rosso nuovo del #8 |
>
> A fine step le porte 6157 e 6167 sono libere (`lsof` vuoto). Lo snapshot del DB del runner è archiviato in `.testLog/00_archive/`
> (ignorato).

**Rossi nominati e classificati** (verdetti di `test-triage`; nessuno è un difetto di prodotto):

| # | test | verdetto | causa | destino (S10) |
|---|---|---|---|---|
| C1–C12 | i 12 di `chartCoreHelpers.test.ts` (§6.0.19) | assumption | specchi sul testo sorgente, rotti da firme cambiate su richiesta | 5 da cancellare per nome (C6, C8, C9, C10, C11); 7 da ri-pinnare, ognuno col suo perché (D8 ✅). ⏭️ S9: C8 è guarito e resta (registro S9) |
| E1–E3 | `dashboard.spec.ts:577`, un caso per sottomodo: «the zoom-window selector is present and operative in the {line,candles,income} submode» | assumption: **descrive una feature tolta** | i `growth-zoom-window-*` non esistono più. Il selettore di finestra è stato sostituito dalla scala a otto gradini (`e7773a143`) | da cancellare: −3 con un solo `for`. Con loro vanno `ZOOM_WINDOWS`, `selectZoomWindow` e `recascadeUnderCandleGrammar`, che restano senza chiamanti |
| E4 | `dashboard.spec.ts:607`: «candles aggregate coarser than the line at the very same window» | assumption: contratto vivo, àncora morta | Il contratto è ancora vero: le candele diventano più grossolane dove la linea resta giornaliera. Ma il test lo legge da `chart-resolution-badge`, che in candele **non viene più montato**: con la scala attiva il badge è spento (`{#if !ladderActive}`). E fissa la finestra con un pulsante che non esiste più | da ri-pinnare sulla scala |
| E5 | `dashboard.spec.ts:534`: «the income submode receives all six of the channels it plots» | assumption | L'àncora è «almeno 3 importi **con segno**». Dal `e7773a143` lo zero non ha segno né colore, per scelta: uno zero verde si legge come un guadagno. Nel tooltip della settimana sotto il puntatore (2026-08-05 → 08-11) Dividend, Interest e Total valgono `EUR 0.00`, e resta un solo importo con segno (`+EUR 405.96`, nuovo capitale). **Le tre righe ci sono**: il test le cerca per segno | da ri-pinnare su un'àncora a segno opzionale |
| E6 | `brokers-detail.spec.ts:710`: «line and income submodes render this broker own figures» | assumption | identica a E5: stesso tooltip, stessa settimana, stesso `EUR 0.00` tre volte | come E5 |

- Il **reperto 1** è confermato e **corretto**. I rossi zoom-window sono davvero 4 (E1–E4), ma E4 non è da cancellare.
- E5 ed E6 non erano previsti. Il journal non registra nessun run degli E2E di dashboard e broker dopo `e7773a143`: in
  §6.0.15–§6.0.19 non compaiono mai E2E, Playwright o nomi di spec.
- **Copertura mancante** (va nella test list di S10, non è una riparazione): la scala `growth-candle-width-*` di `e7773a143` non
  ha nessun E2E; in `e2e/` ci sono 0 occorrenze. E1–E3 erano l'unico E2E sul controllo di finestra, e il controllo che l'ha
  sostituito non ne ha nessuno.
- **Reperto 12** (`check-orphans`): 5 unit frontend che il runner non esegue mai: `privacyStore.test.ts`,
  `privacyStoreSsr.test.ts`, `currencyFormat.test.ts`, `maskable.test.ts`, `moneyRenderSites.test.ts`. Il coordinator lo
  sapeva già (l'aveva trovato Risk): li registra J, io non registro niente. Finché non sono registrati, in S2-pre «gate verde»
  vuol dire il comando #4 lanciato a mano.

> **Decisioni ricevute dal coordinator durante S1 (2026-09-24):**
> - Il v3 l'ha approvato il developer.
> - D8 confermato con quattro condizioni (§7).
> - D13 girato a J.
> - D5′: J è l'unico scrittore di 5 componenti di lotti ed esposizione (§6).
> - Risk non si sovrappone a S4 e S4b.
> - K: la stabilità di `ASSET_TYPES` la chiede il coordinator; `CROWDFUND_REAL_ESTATE` non la anticipo.
> - D14 confermato; il CHANGELOG lo scrive il coordinator.
>
> Riportate in §6 e §7.

> **⚠️ Fuori pista (una data del journal presa dalla conversazione invece che dall'orologio, 2026-09-24):** avevo datato S0
> 2026-09-23, cioè il giorno in cui il piano era stato presentato, non quello in cui è stato approvato ed eseguito. Me ne sono
> accorto dal nome dell'archivio del runner (`logs_20260924_093417`), non da un controllo. Ho corretto 5 date in questo file e
> 10 nel piano madre. Restano al 09-23 solo le due menzioni che parlano davvero della presentazione.

> **⚠️ Fuori pista (due rossi che nessuno aveva previsto, E5 ed E6):** non erano nel reperto 1 né nell'inventario del 22/09.
> La causa è una mia slice del round 3 (`e7773a143`), quindi per la regola di D8 la conversione è mia e va in S10. La lezione
> è la stessa del reperto 1, vista dall'altro lato: **un inventario fatto sugli unit non vede i rossi degli E2E**. Il 22/09
> «12 rossi» era vero per il perimetro che avevo misurato, non per il ramo.

### S1b — Hook `__lfChart` ✅ 2026-09-24

> **Note implementazione:** `GrowthChart.svelte` e `PerformanceChart.svelte` espongono l'istanza sul contenitore
> (`__lfChart`), con lo stesso nome e la stessa forma di `PriceChartFull`, `CandlestickChart`, `AllocationPieChart` e
> `AllocationHistoryChart`.
> - L'hook si scrive subito dopo `echarts.init` + `attachChartReady`.
> - Si **cancella** prima di ogni `dispose()`: sia nel ramo di re-init (contenitore cambiato) sia nel cleanup di `onMount`,
>   come fa `CandlestickChart`. Il nodo da ripulire lo dà `chartInstance.getDom()`, non `chartContainer`: nel ramo di
>   re-init il nodo vecchio non è più `chartContainer`, e allo smontaggio il `bind:this` può essere già stato azzerato.
> - +4 righe di codice per file, più il commento. Nessun cambiamento di comportamento.
>
> Evidenza:
>
> | comando | esito |
> |---|---|
> | `npx vitest run chartCoreHelpers.test.ts GrowthChart.test.ts moneyRenderSites.test.ts --reporter=json` | 12 falliti su 174. **Stessi 12 nomi** della baseline S1, confrontati sui nomi: 0 nuovi, 0 spariti. Gate 6/6, `GrowthChart.test.ts` 6/6 |
> | `dev.py front check` | 3 errori, 41 warning: invariato, nessuna riga sui due file |
> | `npx prettier --check` sui due file | pulito |
>
> La verifica dal vivo dell'hook è S6: la riproduzione R8/R10 sulla copia legge `__lfChart.getOption()`, cioè proprio il
> consumo per cui l'hook esiste. Un test dedicato non è nella test list: lo coprono i test di S2, S4 e S5, che lo usano.

### S3 — §2.5: un'omissione vale come annullamento ✅ 2026-09-24

> **Note implementazione:** in `assets/[id]/+page.svelte`, `handlePageSyncComplete` ha ora il default `{accepted: false}` al
> posto di `{accepted: true}` (D7). Il default è rimasto, come chiedeva §2.5; è cambiata solo la polarità, e un commento di
> due righe spiega perché. Il commento cita il simbolo e non la riga, per la lezione di §2.6.
>
> **Catena rimisurata prima dell'edit**, non ereditata da §2.5:
> - `PageSyncModal` dichiara `onsynced: (detail: PageSyncCompletion) => void` e chiama sempre `onsynced({accepted})`.
> - `RiskAnalysisPanel` (firma `:50`, propagazione `:525`) passa il detail a `AssetRiskScenariosView` (`:21`, `:103`).
> - I call site sono `+page:3533` e `:3558`, entrambi come prop. Non esiste nessuna chiamata senza argomento.
> - L'omonima `fx/[pair]/+page.svelte:1030` è un'altra funzione e non l'ho toccata.
>
> Le righe di `PageSyncModal` citate da §2.5 (`:27,40`) nel frattempo sono diventate `:40,77`: un'altra prova che conviene
> citare il simbolo.
>
> Evidenza:
>
> | comando | esito |
> |---|---|
> | `dev.py front check` | 3 errori e 41 warning, invariati; nessuna riga su `assets/[id]/+page.svelte` |
> | `npx prettier --check` | pulito |
> | `dev.py test --test-port 6157 --data-dir … front-asset asset-detail` | **1 fallito su 28** (E7, sotto) |
> | lo stesso test, da solo, sul codice di `HEAD` (senza S3) | **stesso rosso, stesso messaggio**. S3 non c'entra |

**E7 — un rosso nuovo, e la sua causa è il calendario:**

| # | test | verdetto | causa | destino |
|---|---|---|---|---|
| E7 | `asset-detail.spec.ts:486`: «calendar-return primary mode queries exact windows and restores price controls» | **assumption (clock)** | Il mock costruisce la finestra MAX accettata come `subtractDays(end, 45)..end`, dove `end` è la data della richiesta, cioè **oggi** (`:1844`). Gli eventi del peer però sono scritti a mano: `2026-08-01` e `2026-08-03` (`:769`). Il 2026-09-17, giorno del commit `2d22130bd` (mio, G3), la finestra partiva dal `2026-08-03` e conteneva l'evento. Dal **2026-09-18** parte dal `08-04` e non lo contiene più; oggi è `2026-08-10..2026-09-24`. Il test si ferma da solo con *«contains no ready-peer event fixture»*. È un guard scritto bene: dice perché si ferma, invece di fallire tre asserzioni dopo | S10: le date delle fixture vanno **derivate** dalla stessa `end`, non scritte. Di conseguenza si spostano con loro anche i prezzi del peer allineati a quegli eventi (`:760-767`) |

- Il test era verde il giorno in cui è stato scritto ed è rosso **da una settimana senza che nessuna riga sia cambiata**.
- È la stessa classe dello `sleep` (test-triage §2), con il tempo di calendario al posto dei millisecondi: un orologio che il
  test non controlla, trattato come una costante.
- **Previsione di conflitto per S10**: `asset-detail.spec.ts` è uno spec condiviso (A ci lavora sui livelli di confronto
  per-asset). Prima di toccarlo lo annuncio al coordinator.

> **⚠️ Fuori pista (per assolvere S3 ho rimesso temporaneamente il codice di `HEAD`):** per sapere se E7 dipendesse da S3 ho
> seguito questa procedura:
> 1. copiato il file con S3 in `/tmp`;
> 2. sovrascritto il file con `git show HEAD:<file>` (niente `stash` né `checkout`, nessuna mutazione Git);
> 3. rilanciato il solo test;
> 4. ripristinato la copia e verificato con `git diff` che S3 ci fosse di nuovo (+3/−1).
>
> Il ragionamento («il default non lo esercita nessuno») diceva già che S3 non c'entrava. **La misura lo ha dimostrato.**

### S4 — R21 Allocazione: vista e dimensione ricordate ✅ 2026-09-24

> **Note implementazione:** in `AllocationPanel.svelte` la vista (`now`/`history`) e la dimensione (`type`/`sector`/`geo`)
> sono ora ricordate per utente. Le chiavi sono quelle dello storyboard R21: `dashboard-allocation-view` e
> `dashboard-allocation-tab`. Come voleva D6, sono le stesse per Dashboard e Dettaglio broker: il componente è unico, come
> per `PositionsPanel`.
>
> Scelte fatte, e perché:
> - **Helper del progetto, non il pattern locale.** Uso `getUserStorage`/`setUserStorage` di `utils/storage.ts`, già usati
>   da `ViewModeToggle`, `Sidebar` e `files/+page.svelte`. Il `loadPref` di `PositionsPanel` ne è una copia locale.
> - **Scrittura al click, non in un `$effect`.** `selectView`/`selectTab` impostano lo stato, lo salvano e, se serve,
>   chiedono lo storico. Così il salvataggio avviene solo per una scelta dell'utente, e il percorso del click è uno solo.
> - **Normalizzazione.** Un valore salvato che questa versione non conosce torna al default (`now`, `type`), invece di
>   lasciare il pannello senza un bottone selezionato.
> - **Storico ripristinato come un click.** Al mount, se la vista salvata è `history`, il pannello chiama
>   `loadAllocationHistory(allocationTab)`, cioè lo stesso percorso del click.
>   - Dashboard: non passa `onRequestAllocationHistory`, quindi la chiamata non fa nulla; lo storico arriva già nel report.
>   - Broker: la chiamata diventa `loadOverview()` senza `force`. `fetchReport` la deduplica con il caricamento iniziale
>     della pagina (stessa chiave, `reportInflight`) oppure la serve dalla cache. Non parte una seconda richiesta.
> - **`aria-pressed`** sui due bottoni della vista e sui tre della dimensione: è lo stato che il test E2E di persistenza
>   leggerà (§4, riga S4).
> - Il commento in testa al file ora dice che vista e dimensione sono persistite, e con quali chiavi condivise.
>
> Evidenza:
>
> | comando | esito |
> |---|---|
> | `dev.py front check` | 3 errori e 41 warning in 4 file, invariati; nessuna riga su `AllocationPanel` |
> | `npx prettier --check` | pulito |
> | `dev.py test --test-port 6157 --data-dir … front-portfolio dashboard` | **5 falliti su 15**, gli stessi di S1 (E1–E5). Passano i tre test d'allocazione, compreso «Allocation panel toggles now/history…» |
> | `dev.py test --test-port 6157 --data-dir … front-broker detail` | **1 fallito su 28**, lo stesso di S1 (E6) |
>
> **Non ancora provato dal vivo** che la vista sopravviva a un cambio pagina o a un reload. Lo verifico in S6, sulla copia
> di prod, insieme a S5 e all'hook di S1b. I test della riga S4 di §4 aspettano l'OK del developer sulla test list.
>
> **Nota per S5, verificata e non ereditata.** Sul broker, `loadOverview()` azzera `pnlCandles`. Con la vista `history`
> ripristinata, questo succede anche al mount. Non è un rischio: l'effetto di fetch lazy in `GrowthChart` rilegge
> `pnlCandles`, si riattiva quando torna `null` a candele attive, e `loadPnlCandles` viene servito dalla cache. La stessa
> corsa esisteva già fra il caricamento iniziale della pagina e il fetch delle candele.

### S4b — Allocazione storica: un'emoji esplicita per ogni tipo ✅ 2026-09-24

> **Note implementazione:** la mappa tipo→emoji esce da `AllocationHistoryChart.svelte` e diventa un modulo testabile,
> `components/dashboard/allocationTypeEmoji.ts`: è la variante (a) di D11, «modulo mio accanto al grafico».
> `getCategoryEmoji` lo consuma nella dimensione Tipo con una riga; settore e geografia restano come prima.
>
> Contenuto, come da storyboard K-emoji:
> - **Voci invariate**: STOCK 📈, ETF 📊, BOND 🏛️, CRYPTO 🪙 (con il commento sul ₿), FUND 💼, HOLD ⏸️, CROWDFUND 🤝,
>   INDEX 📉, OTHER 📦, LIQUIDITY 💰.
> - **Voci nuove**: COMMODITY 🛢️, REAL_ESTATE 🏠, UNKNOWN ❔.
> - **I sei sottotipi ETF** hanno ora una voce esplicita, uguale all'emoji ETF, per la regola di K (l'icona dice che cosa
>   *è* lo strumento, l'etichetta che cosa contiene). ETF_MONETARY segue la regola, come proposto in D11.
> - **Fallback**: un valore non mappato riceve `''`, cioè nessuna emoji. Prima riceveva `📊`, l'emoji dell'ETF, ed è così
>   che materie prime, immobiliare e tipo ignoto finivano disegnati come ETF. Con `''` la legenda mostra la sola etichetta
>   e l'area resta senza label (`showLabel` richiede un'emoji).
> - `CROWDFUND_REAL_ESTATE` **non** è anticipata, come concordato con il coordinator.
>
> Evidenza:
>
> | comando | esito |
> |---|---|
> | `dev.py front check` | 3 errori e 41 warning in 4 file, invariati; nessuna riga sui due file |
> | `npx prettier --check` sui tre file toccati da S4/S4b | pulito |
> | sonda usa-e-getta in `/tmp` (non un test): enum letto da `models.py` per regex | **17 valori**, più `Liquidity` e `Unknown`: nessuno senza emoji. Sottotipi ETF = ETF: sì. COMMODITY 🛢️, REAL_ESTATE 🏠, Unknown ❔: diversi dall'ETF. Un valore futuro → `""` |
> | `dev.py test --test-port 6157 --data-dir … front-portfolio dashboard` | **5 falliti su 15**, gli stessi di S1 (E1–E5); verdi i test d'allocazione, che disegnano la dimensione Tipo |
>
> **⚠️ Fuori pista (gli import da `assetTypes.ts` sono finiti nel test, non nel modulo):** la slice diceva
> «`ASSET_TYPES`/`isEtfSubtype` importati da `assetTypes.ts` in sola lettura». Il modulo però è una mappa esplicita e non
> ne ha bisogno. Importarli nel codice di produzione avrebbe solo legato il grafico a un file che K sta cambiando. Il
> legame con la regola di K lo farà il test (`isEtfSubtype`). Per l'elenco dei tipi propongo di leggere `models.py`, come
> il gate esistente (§4, riga S4b). Esito verso K: **zero edit e zero import** su `assetTypes.ts`.
>
> **Un'osservazione per il developer, non una deviazione.** Nello stesso grafico, `Unknown` vale già ❓ nella dimensione
> Settore (emoji del backend, `SECTOR_EMOJIS`) e 🏳️ in Geografia. Ho tenuto ❔ perché è quello approvato. Se il developer
> preferisce ❓, come in Settore, è un solo carattere.
>
> ⏭️ **Seguito (2026-09-24):** il developer ha scelto ❓ alle 10:28 (D11). Applicato in `allocationTypeEmoji.ts`, con un
> commento di una riga che ne dice il motivo (lo stesso glifo di un settore ignoto, `portfolio_engine.py:80`, verificato).
> Geografia invariata (🏳️, in `getCategoryEmoji`). Verifica: `prettier --check` pulito; `front check` nel registro S6.

### S5 — R21 Crescita: modalità e sottomodalità ricordate ✅ 2026-09-24

> **Note implementazione:** in `GrowthChart.svelte` la modalità (`eur`/`pct`/`pnl`) e la sottomodalità P&L
> (`line`/`candles`/`income`) sono ora ricordate per utente. Le chiavi sono quelle dello storyboard:
> `dashboard-growth-mode` e `dashboard-growth-pnl-submode`, condivise fra Dashboard e Broker come in S4. Uso gli stessi
> helper (`getUserStorage`/`setUserStorage`) e la stessa forma: `selectMode`/`selectSubmode` scrivono solo al click.
>
> - **Normalizzazione.** Un valore sconosciuto torna a `eur` o a `line`.
> - **Larghezza della candela: non persistita**, come deciso in D6. Non ho toccato niente: `candleWidthPending` parte
>   `true`, e il primo `renderChart` con la scala attiva applica la regola d'apertura (§6.0.16) anche quando le candele
>   sono ripristinate al mount.
> - **Candele ripristinate.** Il fetch lazy parte da solo: l'effetto esistente vede `pnl` + `candles` + `pnlCandles == null`
>   e chiama `onRequestPnlCandles`.
> - **Fallback `pct`.** Una vista % ripristinata viene verificata una volta sola, al primo caricamento concluso: se la
>   storia non ha dati %, la vista passa ad Abs. Il passaggio vale **solo per la visualizzazione**: la scelta salvata
>   resta `pct` e torna quando i dati ci sono. Tre dettagli verificati sul codice:
>   - entrambi i genitori partono con `reportLoading = true` (Dashboard `:95`, Broker `:70`), quindi il controllo non
>     può scattare prima che il caricamento cominci;
>   - un clic dell'utente durante il caricamento azzera il controllo, così il fallback non scavalca una scelta esplicita;
>   - la modalità iniziale è letta in una costante, non dallo `$state`, per non introdurre il warning
>     `state_referenced_locally` (la prima stesura l'aveva, e `front check` era salito a 42 warning).
> - **`aria-pressed`** su Abs, % e P&L. Le tre sottomodalità lo avevano già.
>
> Evidenza:
>
> | comando | esito |
> |---|---|
> | `dev.py front check` | 3 errori e 41 warning in 4 file, invariati (dopo la correzione del warning) |
> | `npx prettier --check GrowthChart.svelte` | pulito |
> | `npx vitest run GrowthChart.test.ts` | 6/6 |
> | `npx vitest run …/privacy/moneyRenderSites.test.ts` (gate, esplicito) | 6/6 |
> | `dev.py test --test-port 6157 --data-dir … front-portfolio dashboard` | **5 falliti su 15**, gli stessi di S1 (E1–E5) |
> | `dev.py test --test-port 6157 --data-dir … front-broker detail` | **1 fallito su 28**, lo stesso di S1 (E6) |
>
> **Non ancora provato dal vivo**: lo verifico in S6, sulla copia di prod, insieme a S4 e S1b.

> **⚠️ Fuori pista (una regressione che nessuna suite vede: la gallery):** cercando chi usa i controlli di Crescita ho
> letto `e2e/gallery.spec.ts:526-569`. Il test «main dashboard» cicla lingue e temi **nella stessa pagina**. A ogni giro
> scatta `main` («absolute mode (default)») e poi clicca `growth-toggle-pct` per scattare `main-pct`. Con S5 quel clic
> viene ricordato, quindi **dal secondo giro in poi lo scatto `main` uscirebbe in %**. Non lo vede nessuna delle mie
> suite: la gallery gira solo su richiesta.
> - **Rimedio**: un clic esplicito su `growth-toggle-eur` prima dello scatto `main`. Aggiunto alla test list (§4, riga
>   S5) come obbligatorio e **da consegnare nello stesso checkpoint di S5**, così il target non ha mai una finestra con la
>   gallery rotta.
> - `gallery.spec.ts` è un file condiviso: lo annuncio al coordinator.
> - Il ciclo dell'allocazione (`:605-667`) invece clicca già ogni stato prima di scattare, quindi S4 non lo tocca.
>
> **⚠️ Fuori pista (Node 26 e `localStorage` nei test unitari):** dopo S5, `GrowthChart.test.ts` stampa
> *«ExperimentalWarning: localStorage is not available because --localstorage-file was not provided»*. Nei log di S1/S1b
> non c'era. Misurato con `node -e`: su Node 26, senza il flag, `globalThis.localStorage` è `undefined`. Nell'ambiente
> jsdom di vitest vince quello di Node, quindi `getUserStorage` va in eccezione, la cattura e restituisce il default.
> - Conseguenza: **nei test unitari la persistenza è inerte**. I 6 casi di `GrowthChart.test.ts` non si passano stato
>   l'uno all'altro, ma per un accidente dell'ambiente e non per costruzione.
> - Il progetto ha già la risposta: i test che ne hanno bisogno si forniscono un `localStorage` (`ExposureTable.test.ts:43`
>   con `vi.stubGlobal`, `chartSettingsStore.test.ts:108`). L'ho scritto nelle righe S4 e S5 della test list.
> - Il warning è rumore, non un rosso.

> **Verifica successiva (metodo di F, 2026-09-24 11:23):** ho fatto girare la suite con uno storage vero e poi ho letto
> le chiavi rimaste. Il metodo me l'ha girato il coordinator durante il `FROZEN` di C0.
>
> ```
> NODE_OPTIONS=--localstorage-file=/tmp/libreFolio_ls_i_growth npx vitest run …/GrowthChart.test.ts
> node --localstorage-file=/tmp/libreFolio_ls_i_growth -e "<elenco delle chiavi>"
> ```
>
> | misura | esito |
> |---|---|
> | test | 6/6 verdi anche con lo storage vero |
> | chiavi rimaste | **2**: `lf_anon_dashboard-growth-mode = "pnl"`, `lf_anon_dashboard-growth-pnl-submode = "income"` |
>
> - **La previsione era questa**, scritta prima della misura: due chiavi, modalità `pnl` e l'ultima sottomodalità
>   cliccata. L'ultimo caso dell'`it.each` è un Income, quindi `income`.
> - **Che cosa prova.** Con uno storage vero, ogni caso dopo il primo monta già in P&L, nella sottomodalità del caso
>   precedente. Oggi passano lo stesso, perché ognuno clicca esplicitamente `pnl` e la sua sottomodalità. Ma l'isolamento
>   non è per costruzione: lo garantisce l'ordine dei clic. È il caso descritto da F: nell'ambiente di default la suite è
>   verde perché la scrittura non avviene.
> - **Cura invariata**, già nella test list (§4, riga S5): uno stub in memoria svuotato in `beforeEach`. A quella riga
>   aggiungo le asserzioni sul contenuto dello stub, così la scrittura è **provata**, non soltanto tollerata.
> - File temporaneo cancellato subito dopo la lettura. Nessun edit a codice o test.

### S9 — R9: didascalia corta, su una riga, che scorre ✅ 2026-09-24

> **Note implementazione:** sotto le candele la didascalia usa ora la chiave corta
> `dashboard.pnlCandlesHypotheticalShort` (D5 = a). Sta su una riga sola, con il marquee che il progetto ha già:
> `use:scrollOnOverflow` + `overflowScrollTextClass`, come in `KpiCard` e `BrokerCard`. Nessuna primitiva nuova.
>
> - **Chiave lunga rimossa** con `dev.py i18n remove dashboard.pnlCandlesHypothetical`, dopo un `--dry-run`. Il diff è
>   di 4 righe, una per lingua; la chiave corta è intatta in tutte e quattro.
> - **`text-center` resta.** Quando il testo non entra, CSS allinea il contenuto all'inizio, e il marquee parte da lì.
> - **Un commento falso, riscritto.** Nel tooltip delle candele un commento descriveva ancora la nota corta tolta al
>   round 3 («Compact form for the tooltip…»). Ora dice in una riga come stanno le cose. Nei commenti non c'è nessuna
>   chiamata `$_()` d'esempio: uno sweep che legge il sorgente come testo la prenderebbe per codice (§6.0.19).
> - **Il testid non cambia.** I due E2E che lo guardano (`dashboard.spec.ts:531`, `brokers-detail.spec.ts:707`) restano
>   verdi.
>
> **Specchi (D8).** Ho misurato in due tempi, così ogni rosso ha una causa sola. Poi ho cancellato a mano, per nome, uno
> alla volta, confrontando gli elenchi dei nomi e non solo i totali:
>
> | momento | test | rossi | che cosa cambia |
> |---|---|---|---|
> | prima di S9 | 168 (162 + 6) | 12 | nessun cambiamento rispetto a S1: stessi nomi, quindi S3–S5 non hanno rotto nessuno specchio |
> | dopo il markup | 168 | 12 | +1 `consumes dashboard.pnlCandlesHypothetical through $_()`; **−1 C8** (`…HypotheticalShort`), guarito |
> | dopo `i18n remove` | 168 | 14 | +2: `dashboard.pnlCandlesHypothetical is a real translation…` e `keeps the LONG value a strict extension of the SHORT one…` |
> | cancellazione 1: l'elemento `'dashboard.pnlCandlesHypothetical'` di `WIRED_KEYS` | 166 | 12 | −2 esatti: i due casi `it.each` della chiave lunga, e nient'altro |
> | cancellazione 2: `it('keeps the LONG value a strict extension…')` | 165 | 11 | −1 esatto |
>
> - **Perché si cancellano.** I tre test descrivono una coppia di chiavi che non esiste più, e riparare un test che
>   descrive una feature tolta vorrebbe dire rimetterla.
> - Il titolo «never reintroduces hardcoded English for any of the seven» resta invariato. Vieta ancora sette letterali,
>   compresa la frase lunga, che non deve tornare scritta a mano.
> - **Esito:** `chartCoreHelpers.test.ts` passa da 162 a 159 test e da 12 a 11 rossi. Gli 11 sono tutti nella baseline
>   S1; nessuno è nuovo.
>
> Evidenza:
>
> | comando | esito |
> |---|---|
> | `npx vitest run chartCoreHelpers.test.ts GrowthChart.test.ts --reporter=json` | 165 test, 11 falliti, tutti della baseline S1. `GrowthChart.test.ts` 6/6 |
> | `npx vitest run …/privacy/moneyRenderSites.test.ts` (gate, esplicito) | 6/6 |
> | `dev.py i18n audit` | da 3403 a 3402 chiavi, complete nelle quattro lingue. L'elenco delle inutilizzate è identico (422, nessuna mia) |
> | `dev.py front check` | 3 errori e 41 warning in 4 file: il floor |
> | `npx prettier --check` sui 6 file | pulito |
> | `dev.py test --test-port 6157 --data-dir … front-portfolio dashboard` | 5 falliti su 15, gli stessi nomi di S5 (E1–E5). `:496`, che vede la didascalia, è verde |
> | `dev.py test --test-port 6157 --data-dir … front-broker detail` | 1 fallito su 28, lo stesso nome (E6). `:670`, che vede la didascalia, è verde |
> | `git diff --check` | pulito |
>
> **Non ancora provato: lo scorrimento a 375 px.** jsdom non ha layout, e `$test/component` fornisce apposta un
> `ResizeObserver` inerte («Overflow is E2E territory»). Lo verifico dal vivo in S6.
>
> **File condivisi toccati:** i quattro cataloghi i18n (−1 chiave ciascuno, solo via `dev.py i18n`). Vanno nell'handoff.

> **⚠️ Fuori pista (C8 non va più cancellato):** §6.0.19 del piano madre e la riga S10 della test list lo davano da
> cancellare, perché la chiave non era più consumata. Con D5 = (a) la didascalia la consuma di nuovo, e il test è
> tornato verde da solo. Cancellarlo in S10 avrebbe tolto una guardia vera, eseguendo un'istruzione scaduta. Ho
> aggiornato:
> - la riga S10 della test list: −4 su 159, non più −5 su 162;
> - il destino di C1–C12 nel registro S1;
> - l'inventario del piano madre, con una nota datata.
>
> Resta la domanda se C9 andasse cancellato qui, visto che la sua coppia la scioglie S9. Ho tenuto la regola stretta:
> S9 converte solo ciò che S9 rompe, e C9 era rosso da prima. Resta a S10, con la causa aggiornata.

> **⚠️ Fuori pista (la doc utente descrive tre cose tolte):** cercando la didascalia in `charts.en.md` ho trovato la
> frase lunga citata a `:113`, come previsto, e tre passaggi fermi a prima del round 3:
> - la nota corta nel tooltip (`:115`);
> - le linee broker sopra le candele (`:125`), mentre `brokers-detail.spec.ts:746` verifica proprio che non ci siano;
> - la finestra 1W/1M/1Y/All (`:163-169`), sostituita dalla scala a otto gradini.
>
> Non li ho toccati: sono doc, e la doc la scrive docs-writer in S11. Li ho aggiunti al perimetro di S11 (§3). Le
> traduzioni hanno lo stesso debito, e le traduzioni partono solo su richiesta esplicita.

> **⚠️ Fuori pista (un probe temporaneo nel sorgente):** l'azione crea il suo `ResizeObserver` senza controllare che
> esista (`scrollOnOverflow.ts:134`), e jsdom non ne ha uno. Per capire perché il test non esplodeva ho messo in
> `src/lib/` dei test sonda temporanei e li ho cancellati subito. Non ne ho annotato il nome, quindi la prova è
> l'assenza: `git status --ignored -- frontend/src` non mostra niente di non mio, e le sole sonde in `src` sono quelle
> tracciate del progetto. Risposta: nell'ambiente jsdom `ResizeObserver` è `undefined`, e lo stub arriva da
> `src/__tests__/component.ts:96`, che `GrowthChart.test.ts` importa tramite `$test/component`.

### S6 — Riproduzione R8/R10 sulla copia ✅ 2026-09-24

> **Note implementazione (parziale, 2026-09-24):**
>
> - **La copia è stata creata con la procedura snapshot di §5**:
>   - versione `004_release_1_2_0_schema`, nessun marcatore di produzione;
>   - lo sha256 di `app.db` coincide con quello della snapshot, cioè con il valore annunciato dal coordinator: la copia
>     viene dalla snapshot intatta. Il valore non si trascrive: è un hash che identifica i dati del developer;
>   - dopo la lettura di `sqlite3` ci sono un `app.db-wal` vuoto e un `app.db-shm`. È atteso.
> - **Il comando utenti mira alla copia**: `dev.py user --test-db list`, con `LIBREFOLIO_TEST_DATA_DIR` sulla copia, mostra
>   un solo utente, quello del developer. Prima ho letto come risolve il percorso (`scripts/cli_base.py:241-253`,
>   `backend/app/config.py:280`).
> - **Credenziali**: me le ha girate il coordinator, fuori banda. Non sono trascritte da nessuna parte, e il reset non
>   serve.
> - **Non ancora fatto**: server non avviato, nessuna misura R8/R10.
> - **Prima della pausa, due voci d'ingresso chiuse:**
>
>   | voce | che cosa ho fatto | verifica |
>   |---|---|---|
>   | ❓ (D11) | applicato | `front check` 3 errori / 41 warning / 4 file = floor, 0 righe sui miei file (i 4 file sono di altri). `prettier --check` pulito |
>   | D15 | deciso | una riga all'integrazione |

> **⚠️ Fuori pista (credenziali perse nella compattazione del contesto):** la password girata in precedenza non era più
> nel mio contesto.
> - Ho chiesto al developer con `ask_user`, ma non era disponibile. Allora ho scelto il ripiego del piano: reset **solo
>   sulla copia**, che avrebbe anche tenuto la password vera fuori dalla trascrizione. Ho verificato che il comando
>   risolve sulla copia, ma non l'ho eseguito: nel frattempo sono arrivate le credenziali dal coordinator.
> - Sulla copia non è cambiato nulla.
> - Il messaggio era partito prima della mia domanda e mi è arrivato dopo: di nuovo il ritardo del canale, questa volta
>   su un'informazione che esisteva già.

> **⚠️ Fuori pista (due percorsi diversi nei messaggi del coordinator):** i messaggi sulla copia e sul gate usano
> `/tmp/librefolio-r2-i-prodcopy` e `/tmp/librefolio-r2-i`. Il kickoff del 23/09 e questo piano usano
> `/tmp/librefolio-r2-i-charts-prodcopy` e `/tmp/librefolio-r2-i-charts`. Tengo i percorsi del kickoff, che dice «Non
> usarne altre», e ho chiesto conferma al coordinator.
> - ⏭️ **Risolto (coordinator, 11:05):** l'errore era nei suoi messaggi. Valgono i percorsi del kickoff, anche per il gate
>   di S2-pre.

> **Pausa, 2026-09-24 11:01:** FROZEN per il merge di C0 (`2a5927c48`, fast-forward). Al momento del FROZEN: nessun test
> in corso, nessun server, 6157 e 6167 liberi. Si riprende da S2-pre, poi da questa slice.
>
> **Ripresa, 2026-09-24 11:16:** merge fatto (ff `f1047f766..2a5927c48`), il lavoro non committato non è stato toccato.
> Ordine del coordinator: S2-pre, poi S2, poi questa slice.
>
> **Ripresa della slice, 2026-09-24 11:36** (dopo S2a/S2b):
> - Il build del frontend servito dal backend è fresco: `frontend/build/index.html` è delle 11:34. I miei ultimi edit
>   sono delle 11:26 (GrowthChart) e 11:30 (PerformanceChart). Il backend serve `frontend/build/` (`backend/app/main.py:346`),
>   quindi il server della copia mostra S2a/S2b.
> - Server avviato alle 11:39: `… dev.py server --test --port 6167 --data-dir /tmp/librefolio-r2-i-charts-prodcopy`.
>   Ascolta su `6167`, `/` risponde 200, lo scheduler gira (refresh dei prezzi correnti: 11 ok, 0 errori).

> **⚠️ Fuori pista (credenziali perse una seconda volta):** una nuova compattazione del contesto ha cancellato di nuovo
> la password che il coordinator mi aveva girato.
> - Non l'ho chiesta una terza volta. Ho eseguito il ripiego approvato in §5: reset **solo sulla copia**.
> - Prima `list` (`LIBREFOLIO_TEST_DATA_DIR` sulla copia, `--test-db`): «Operating on TEST database», un solo utente,
>   quello del developer. Poi `reset`, con una password usa-e-getta generata in un file `/tmp` a permessi `600`. Il reset
>   l'ha letta da quel file, e non compare in nessun log (verificato con `grep -c`: 0).
> - Effetto: sulla copia l'hash della password del developer non è più il suo. Il rinfresco dalla snapshot, obbligatorio
>   prima di ogni review (§5), rimette quello vero. Il file della password si cancella in S12.
> - Sulla copia non cambia altro.
> - La lezione: un'informazione che vive solo nel contesto sparisce alla compattazione. La password non va scritta, per
>   regola, quindi l'unica difesa è una procedura che non ne abbia bisogno, cioè questo reset.

> **Privacy dal vivo (S2, protocollo di J), 2026-09-24 11:55** — sulla copia, utente del developer, 1440×900, contesto
> del browser nuovo (privacy spenta per assenza della chiave). Ogni modo: spenta → **accesa sul posto** → spenta sul
> posto, senza navigare. Lo script è di sessione, non versionato (`files/probe/libreFolio_i_s6_probe.mjs`); legge gli
> assi e il tooltip vero dall'istanza (`__lfChart`: `getViewLabels()`, `showTip`). A privacy spenta registro solo la
> **forma** delle stringhe (cifre → `9`), non i valori del developer.
>
> | grafico · modo | spenta → accesa: ridisegno | tacche accese | tooltip acceso | accesa → spenta |
> |---|---|---|---|---|
> | Growth · `eur` | ✅ render 2 → 3 | 7/7 `•••`; 0 cifre, 0 `k`/`M` | nessun importo in chiaro; `•••` presente | ✅ 4 → 5, cifre tornate (`99k`) |
> | Growth · `pnl` linea | ✅ 8 → 9 | 8/8 `•••` | idem | ✅ 10 → 11 |
> | Growth · `pnl` candele | ✅ 13 → 14 | 7/7 `•••` | idem | ✅ 15 → 16 |
> | Growth · `pnl` proventi | ✅ 18 → 19 | `-•••`, `•••`… : **segno presente** sulla tacca negativa, zero = `•••` | idem | ✅ 20 → 21 |
> | Growth · `%` (controllo) | ✅ 23 → 24 | **invariate**: forma `-9.9%` … `99.9%`, 7/7 con cifre e `%` | nessun importo, nessun `•••` | ✅ 25 → 26 |
> | Performance (Posizioni → Performance → mappa) | ✅ 3 → 4 | 7/7: `-•••` ×3, `•••` ×4; **zero = `•••`** | — (non richiesto; già mascherato prima di S2) | ✅ 4 → 5 |
>
> - Etichette nette di Performance, accese, nella forma `-€••• (-9.9%)` e `+€••• (+99.9%)`. Segno e simbolo fuori,
>   percentuale intatta. Delle 15 stringhe con un segno di valuta, **una sola** ha cifre fuori dalla parentesi: il nome
>   di un asset che contiene «EURO» e un numero. Il mio filtro l'ha presa perché «EURO» contiene «EUR». Non è un importo.
> - I tre obblighi di J per S10 (§4) sono veri dal vivo: tacche senza cifre né `k`/`M` e col segno; `%` non mascherato;
>   zero di Performance mascherato.
> - Console: un solo errore, un 401 prima del login (il controllo di sessione). Nessun `pageerror`.
> - Log e JSON: `/tmp/libreFolio_i_s6_privacy.{log,json}`, `/tmp/libreFolio_i_s6_perf2.{log,json}`.

> **⚠️ Fuori pista (dati del developer in un file versionato, 2026-09-24 12:00):** rileggendo questo registro prima di
> aggiungere R8/R10 ho trovato tre cose che non dovevano esserci:
> - due rendimenti per posizione e l'intervallo dell'asse `%` del developer;
> - il nome di un suo asset;
> - un prefisso dello sha256 del suo `app.db`.
>
> Il journal è versionato in un repository pubblico. Ho sostituito i valori con forme (`-9.9%`) e descrizioni, e ho
> scansionato tutto il delta: nient'altro. La regola «cifre → `9`» l'avevo applicata agli importi, non a percentuali,
> nomi e hash. **I dati del developer non sono solo il suo denaro.** Da qui in avanti, in questo file e nei messaggi,
> gli esempi numerici sono sintetici.

> **R8 dal vivo: tre cause, più una** (2026-09-24 11:49–11:51). Copia, 1440×900, plot 527 px, P&L → candele, ogni periodo e
> ogni gradino offerto. JSON `/tmp/libreFolio_i_s6_r8.json`, schermate `r8_*.png`. Gradini offerti: 3M `1G 3G 1S 2S 1M`;
> 6M lo stesso più `3M`; 1A da `3G` a `6M` (1G tolto dalla densità); 2A da `1S` a `1A`.
>
> | causa | meccanismo | casi misurati |
> |---|---|---|
> | **A · mesi doppi** | etichette solo-mese con intervallo numerico k (politica compatta), più `showMinLabel`/`showMaxLabel` | 3M/1G (k=10): `giu, lug, lug, lug, ago, ago, ago, set, set, set`. 6M/1S (k=2): `mar, apr, mag, giu, giu, lug, ago, ago, set, set`. Anche 6M/1G, 6M/3G, 1A/3G, 1A/1S, 1A/2S |
> | **B · separatori ogni k+1 bucket** | `splitLine.interval` non impostato, quindi segue le etichette | 6M/1S: separatori a `[0,3,6,…,24,26,27]` con slot di 19,7 px, cioè tre candele sotto un'etichetta sola. 3M/1S (non compatta, slot 38 px): `[0,3,6,9,12,14]`. `showMaxLabel` aggiunge in coda una cella irregolare |
> | **C · l'ultimo bucket è un moncone** | bucket di N giorni ancorati all'**inizio** del periodo: il resto (`length % N`) finisce in **coda** ed è disegnato largo come gli altri | 3M/1M: `07-23, 08-22, 09-21, 09-24` (3 giorni). 1A/6M: `03-22, 09-18, 09-24`. 2A/1A: `2025-09-23, 2026-09-23, 2026-09-24`, cioè una candela «annuale» di un giorno. Da 1M in su ogni gradino ha **esattamente un mese con due bucket**: è alla lettera «più bucket nello stesso mese» |
> | **D · date ISO grezze** | fuori dalla politica compatta il formatter restituisce il valore di categoria così com'è | 3M/1S e 3M/1M: `2026-06-30`, `2026-07-23` (schermata `r8_default_1m.png`) |
>
> - Corpi uniformi, 80 % dello slot (19,7 → 15,76 px). Slot misurati da 2,88 a 177 px: servono per scegliere T.
> - **`LADDER_MIN_BODY_PX` misura lo slot, non il corpo disegnato.** A 6M/1G lo slot è 2,88 px e il corpo 2,30 px:
>   sotto i 2,5 che il nome promette, eppure il gradino è offerto (`availableCandleWidths` confronta `1 / density`,
>   cioè lo slot). È la taratura voluta dal developer («1G ancora disponibile a 6 mesi»), quindi il comportamento
>   resta. Il commento a `:189-195` confonde però le due misure («2.93px per body»). Lo correggo in S7, dove la stessa
>   costante diventa la soglia per colonna dei Proventi (D17): una soglia confusa non si estende.
> - La deriva dei 30 giorni sui periodi lunghi c'è ma è rara: un mese senza bucket ogni ~68 mesi, quindi mai entro 2A.
>   Non è una causa.
> - 2A usa «mmm aa» e nelle candele non ha duplicati.

> **R10 dal vivo: la larghezza la decide il moncone** (2026-09-24 11:53). Proventi, privacy accesa. JSON
> `/tmp/libreFolio_i_s6_r10.json`, schermate `r10_*.png`. L'asse è `time` in tutti i casi, e nessuna serie imposta
> `barWidth`, `barGap` o `barCategoryGap`.
>
> | periodo/gradino | bucket | slot (px) | barra oggi (px) | gap min / mediano (gg) |
> |---|---:|---:|---:|---|
> | 6M/1S | 27 | 19,5 | 1,65 | 3 / 7 |
> | 6M/3M | 3 | 175,7 | 5,01 | 5 / 90 |
> | 1A/1S | 53 | 9,9 | 1 | 2 / 7 |
> | 1A/1M | 13 | 40,5 | 1,75 | 6 / 30 |
> | 1A/6M | 3 | 175,7 | 3,12 | 6 / 180 |
> | 2A/1M | 25 | 21,1 | 1,54 | 11 / 30 |
> | 2A/1A | 3 | 175,7 | 1 | 1 / 365 |
>
> - Barre da 1 a 5 px **ovunque**, con slot fino a 176 px. La larghezza segue il gap **minimo** fra le x, cioè l'ultimo
>   bucket parziale, non lo slot: **la stessa radice della causa C di R8**.
> - **Il sintomo dello zoom, provato** (fase `r10z`, JSON `/tmp/libreFolio_i_s6_r10z.json`). 1A/1M: finestra 0–100 % →
>   1,75 px; 0–99 %, il moncone esce dalla finestra → **8,29 px** (×4,7 ≈ 30/6); 0–60 % → 12,99. 6M/1S: da 1,65 a 3,82
>   (×2,3 ≈ 7/3). È il «zoomando si ricalcolano e si vedono» del developer.
> - Anche senza moncone le barre restano strette: **4 colonne per slot** (Dividendo+Interesse · Costi e tasse ·
>   Deposito · Nuovo capitale+Reinvestito). Con i gap di default ECharts (20 % fra le categorie, 30 % fra le barre)
>   a ogni barra resta il 16 % dello slot.
> - A margine: l'asse `time` dei proventi usa le etichette di default di ECharts, **in inglese** (`Nov`, `Dec`, un
>   `2026` in grassetto; a 6M/3M `Jul 17 Aug 17`), non la lingua dell'app. Con 1S e 2S le etichette sono invece in
>   italiano. L'asse category di R10-A lo elimina.
> - Schermate: `r10_1y_1m.png` (barre sottili come un capello), `r10_6m_3m.png` (tre gruppi schiacciati ai bordi; il
>   terzo è il moncone di 5 giorni).

> **R21 dal vivo (S4/S5), 2026-09-24 12:00** — due percorsi, ognuno in un contesto nuovo:
> - **ricarica** (`page.goto`): scelti P&L → proventi e Allocazione → storico → settore. Dopo `/transactions` e il
>   ritorno, tutti e quattro sono premuti e la prima serie è `bar`. Chiavi: `lf_1_dashboard-growth-mode`,
>   `…-growth-pnl-submode`, `…-allocation-view`, `…-allocation-tab`;
> - **navigazione SPA dalla sidebar** (`nav-transactions` → `nav-dashboard`), il caso del developer. Che sia lo stesso
>   documento è verificato con un marcatore su `window`. Scelti P&L → candele e storico → geografia: al ritorno tutti
>   premuti, prima serie `candlestick`.
> - JSON: `/tmp/libreFolio_i_s6_persist{,spa}.json`.
>
> **S9 dal vivo** — didascalia delle candele: a 375 px `data-overflowing="true"` (scrollWidth 408 > clientWidth 294); a
> 1440 px l'attributo è assente (632 = 632). La classe del marquee c'è in entrambi i casi. Schermata `s9_mobile375.png`.

> **⚠️ Fuori pista (reperto nuovo, fuori dal piano approvato): tacche Y doppie.** Nella schermata a 375 px l'asse Y
> delle candele ripete le etichette a coppie. La privacy era spenta, perché la fase gira in un contesto nuovo.
> - **Causa statica, certa**: `yAxisFormatter` compatta con `(abs / 1_000).toFixed(0)`. Con tacche a passo 500, metà
>   delle etichette si arrotonda sulla vicina: `1000, 1500, 2000, 2500` → `1k, 2k, 2k, 3k`. L'esempio è sintetico: i
>   valori della schermata non si trascrivono.
> - Precede S2a, che ha solo avvolto `compact` in `maskable`.
> - La stessa forma è **latente** in `PerformanceChart.axisTickAmount`: `maximumFractionDigits: 0` da 100 in su, quindi
>   1500 e 2000 danno entrambi `2K`. Non l'ho osservata.
> - A privacy accesa non si vede: ogni tacca è `•••`.
> - Non corretto: è fuori dal piano. Va al developer come **D18**, con la proposta di chiuderlo in S7.

> **Esito: S6 ✅ 2026-09-24 12:05.** R8 e R10 riprodotti, con le cause misurate; R21 e S9 verificati dal vivo.
> Storyboard R8/R10 aggiornati in §2 (v2), decisioni nuove D16–D18 in §7.
> - S7 aspetta D4, D16 e D17; S7b aspetta D18. R10-A è deciso (D3), ma le sue etichette dipendono da D4, i suoi
>   bucket da D16 e le sue colonne da D17: lo faccio nella stessa passata di R8, non due volte sulle stesse righe.
> - Il server resta acceso fino al FROZEN. Poi: spento, copia rinfrescata dalla snapshot (torna l'hash vero della
>   password), 6157 e 6167 provate libere.
>   ⏭️ **Fatto alle 12:17–12:21**, prima del checkpoint (registro «Checkpoint C1»).

### S2-pre — Rimisurare lo stato che S2 presuppone ✅ 2026-09-24

> **Note implementazione:** il developer ha fuso C0 alle 11:16 (fast-forward `f1047f766..2a5927c48`). Prima di eseguire
> l'istruzione ho misurato lo stato che presuppone. Torna tutto:
>
> | verifica | comando | esito |
> |---|---|---|
> | gate-prep nel ramo | `git merge-base --is-ancestor 2a5927c48 HEAD` | ✅ HEAD = `2a5927c48`; lavoro non committato intatto (11 M + 2 ??, stage vuoto) |
> | stato `public` | `git show 2a5927c48` | ✅ nell'unione `Status`, specchio di `AmountSensitivity = 'public'` in `maskable.ts` |
> | `EventCreateMiniModal` riclassificato | idem | ✅ da `unmasked` a `public`, con la `why`: è un evento dell'asset, non dell'utente (`AssetEvent` in `models.py`) |
> | test 5 su fixture sintetica | idem | ✅ `scanLine('fixture', shortMoneyLine, 0)`: non legge più `PerformanceChart.svelte`. `scanLine` è estratta da `scan()`, quindi la fixture passa dallo stesso codice dei file veri |
> | liste, un elemento per riga | idem | ✅ `residual` = GrowthChart ×2, `unmasked` = PerformanceChart ×2, `public` = EventCreateMiniModal |
> | 5 righe nel catalogo del runner | idem | ✅ in `front_utility_unit`: `privacyStore`, `privacyStoreSsr`, `currencyFormat`, `maskable`, `moneyRenderSites` |
> | gate vitest, prima dei miei edit di S2 | `cd frontend && npx vitest run src/lib/utils/privacy/moneyRenderSites.test.ts` | ✅ 6/6 |
> | gate dal runner, col filtro | `… dev.py test --test-port 6157 --data-dir /tmp/librefolio-r2-i-charts front-utility core-unit "money rendered outside the masking channel"` | ✅ PASSED: 1 file, 6 test, 93 file esclusi dal filtro, exit 0. Lane `6157`, data `/private/tmp/librefolio-r2-i-charts` |
> | probe | `node <sessione-I>/files/probe/libreFolio_i_gate_probe.mjs` | ✅ come previsto: 3 voci stantie (`fmtCurrency` a `:1885`; `shortMoney` a `:167`, 2 rami) + 1 hit che resta (`:1950`, la riga P&L totale del tooltip: D13). Dal 23/09 cambiano solo i numeri di riga (+51, i miei S1b/S5/S9); le sezioni privacy OFF e privacy ON sono identiche |
>
> - Il probe dal gate legge solo le regex; la logica di scansione è una mia copia. L'estrazione di `scanLine` in C0 non
>   cambia quella logica: le righe tolte sono il corpo di `scanLine`, salvo `return` → `return hits`. Quindi la previsione
>   resta equivalente. La misura vera resta il gate dopo i miei edit, non il probe.
> - La riga del probe su «sees both branches» dice ancora RED. È atteso e non conta più: il test 5 non guarda il mio file.
> - Il `:1899` delle pagine precedenti è oggi `:1950` nel mio albero. D13 resta di J: in S2a applico l'opzione consigliata
>   (a) come proposta, e la decisione arriva con la review di S2c.

> **⚠️ Fuori pista (un log «completo» troncato dalla regola che doveva proteggerlo):** ho lanciato il probe con
> `2>&1 | tee <log> | head -n 16`. Il log aveva 37 righe su 42: mancavano le 5 righe finali, cioè la forma a privacy ON.
> L'exit del probe era 0.
> - Causa, riprodotta 3 volte su 3: `head` chiude la pipe dopo 16 righe. Alla scrittura successiva verso la pipe, `tee`
>   riceve SIGPIPE e termina, e quello che non ha ancora scritto nel file non ci arriva più. Con `tail` non succede,
>   perché `tail` legge fino in fondo.
> - La regola del progetto dice di fare `tee` prima di troncare, ed elenca proprio `head` e `grep -m`. Con quei due, il
>   log che dovrebbe essere completo può non esserlo, e niente lo segnala.
> - Rimedio: prima scrivo il file (`> log 2>&1`), poi lo leggo. Rilanciato così: 42 righe, exit 0.
> - Nessuna evidenza di questo journal viene da `tee … | head` (verificato con grep).
> - Segnalato al coordinator alle 11:26: la regola è sua.
> - ⏭️ **Confermato dal coordinator (2026-09-24, 11:40):** l'ha riprodotto lui. Con `seq 1 200000 | tee log | head -n 5`
>   il log ha fra 14 139 e 22 331 righe su 200 000; con `tail`, e con `{ head; cat >/dev/null; }`, ne ha 200 000.
>   Avvisa le altre lane e propone al developer la correzione della regola in `copilot-instructions.md`.

### S2a — Privacy in GrowthChart (R5/R6/R7) ✅ 2026-09-24

> **Note implementazione:** in `GrowthChart.svelte` le cifre di un importo passano da `maskable()`; valuta e segno
> restano leggibili (D8). Le forme sono **esattamente** quelle modellate dal probe il 23/09: un `grep -F` le trova una
> volta ciascuna. Quindi i risultati di parità del probe valgono per il codice vero.
>
> - **Asse Y** (Abs e P&L; il ramo `%` non cambia): `const abs`, `compact` calcolato sul valore assoluto con `k`/`M`,
>   poi `${v < 0 ? '-' : ''}${maskable(compact)}`. Il suffisso sta **dentro** la maschera: `•••k` rivelerebbe l'ordine
>   di grandezza. Lo zero diventa `•••` (D12).
> - **`fmtCurrency`**, usata da tutte le righe del tooltip: `${baseCurrency} ${v < 0 ? '-' : ''}${maskable(abs)}`.
>   Cifre e segno sono separati come in `formatCurrencyAmountPlain`. Copre tutti i consumi, compresi quelli che S8 aggiungerà.
> - **Ridisegno al toggle.** L'effect di render legge `shouldMaskAmount()` nel corpo: il disegno avviene dentro
>   `tick().then`, dove una lettura non registra dipendenze. `renderChart` confronta lo stato con quello dell'ultimo
>   disegno (`lastRenderedMasked`, azzerato al dispose come `lastRenderedDark`) e, se cambia, rifà l'opzione completa.
>   Il motivo: ECharts mette in cache le etichette dell'asse, mentre il formatter del tooltip legge lo stato a ogni hover.
> - **Registro** (`moneyRenderSites.test.ts`, solo righe mie):
>   - la voce della definizione di `fmtCurrency` è **cancellata**;
>   - la riga P&L totale del tooltip (`:1965` ora) passa da `residual` a `masked` (D13, opzione (a), **proposta**: decide J
>     in S2c). La `why` ora dice che la maschera sta nella definizione, che il gate non segue una chiamata dentro una
>     closure, e che la riga resta un hit per i token `totalPnlVal`/`pnlColor`;
>   - `listOf('residual')` è ora `[]`. Ho tolto solo le mie due righe e ho lasciato il commento.
>
> Evidenza:
>
> | comando | esito |
> |---|---|
> | `npx prettier --check GrowthChart.svelte moneyRenderSites.test.ts` | pulito |
> | `npx vitest run …/moneyRenderSites.test.ts …/GrowthChart.test.ts` | **12/12** (gate 6/6, GrowthChart 6/6) |
> | `npx vitest run …/chartCoreHelpers.test.ts` | 148/159: **gli stessi 11 rossi** di S9, confrontati per nome (0 nuovi, 0 guariti) |
> | `dev.py front check` | 3 errori e 41 warning in 4 file, invariati; 0 righe citano i miei file |
> | scan post-edit (`<sessione-I>/files/probe/libreFolio_i_gate_scan.mjs`, regex lette dal gate) | GrowthChart: **1 hit**, la riga P&L totale (`:1965`). Rimettere in chiaro la definizione, in memoria, fa tornare **1 hit** su quella riga: il confine è sorvegliato dal gate stesso |
> | parità a privacy OFF (probe del 23/09, stesse forme) | asse Y identico su tutti i valori e le lingue; `fmtCurrency` diverso solo per `-0` (`EUR 0,00`) e per il segno U+2212 di `sv-SE`, che diventa `-`: le differenze accettate del reperto 11 |
> | forma a privacy ON (idem) | asse `•••`, `-•••`; tooltip `EUR •••`, `EUR -•••`; nessuna cifra e nessun suffisso fuori dalla maschera |
>
> **Non ancora provato dal vivo.** Lo verifico in S6 sulla copia di prod: privacy accesa, poi
> `__lfChart.getOption().yAxis[0].axisLabel.formatter(20000)` e un tooltip reale.

> **⚠️ Fuori pista (D13: la `why` proposta prometteva un test che non c'è):** il testo di D13 per l'opzione (a) diceva
> «bloccata da un test di GrowthChart». Quel test non esiste: è nella lista di S10. Scriverlo nella `why` avrebbe
> registrato una garanzia falsa, la stessa famiglia dei registri verdi e falsi.
> - La garanzia vera l'ho misurata. Se qualcuno toglie `maskable` dalla definizione di `fmtCurrency`, quella riga torna
>   nel gate come hit non registrato, e il gate va rosso. Il precedente `LotComparisonChart.formatAxisCurrency` regge
>   sullo stesso argomento.
> - Il test di S10 aggiunge un'altra cosa: prova il **comportamento reso** (il tooltip), che il gate non vede.
> - La `why` scritta dice solo la prima cosa. Lo segnalo a J in S2c.

### S2b — Privacy in PerformanceChart (P4-11) ✅ 2026-09-24

> **Note implementazione:** in `PerformanceChart.svelte` le forme sono di nuovo quelle modellate dal probe.
>
> - **`shortMoney`**, l'etichetta netta a fine riga: `maskable(compact)` in entrambi i rami. Segno, simbolo e valuta
>   restano leggibili (`+€•••`, `-••• CHF`); il suffisso compatto sta dentro (mai `€•••K`). Il suffisso `%` accanto
>   all'importo non cambia: una percentuale non è patrimonio.
> - **`axisTickAmount`**: segno fuori; lo zero diventa `maskable('0')` (D12).
> - **Ridisegno al toggle**: l'effect legge `shouldMaskAmount()` nel corpo, prima di `tick().then`. `renderChart` fa già
>   sempre `setOption(…, true)`, quindi qui non serve una chiave come `lastRenderedMasked`.
> - Il tooltip era già mascherato (`formatCurrencyAmountPlain`): non cambia, ma ora si ridisegna anche lui.
> - **Registro**, solo righe mie:
>   - le 2 voci di `shortMoney` sono **cancellate**;
>   - `listOf('unmasked')` è ora `[]`, con il commento lasciato;
>   - il test 5 non è toccato, e resta verde sulla sua fixture.
>
> Dopo S2a e S2b, `residual` e `unmasked` sono entrambe vuote.
>
> Evidenza:
>
> | comando | esito |
> |---|---|
> | scan post-edit (`libreFolio_i_gate_scan.mjs`) | PerformanceChart: **0 hit**. GrowthChart: 1 hit, la riga di D13 |
> | revert in memoria | `shortMoney` rimesso in chiaro → tornano **2 hit**; `fmtCurrency` → **1 hit**. Entrambi i confini sono sorvegliati dal gate |
> | `npx prettier --check` sui 3 file | pulito |
> | `npx vitest run src/lib/utils/privacy/ src/lib/utils/currency/ …/GrowthChart.test.ts` | **42/42**: gate 6/6, `maskable` 11/11, `currencyFormat` 16/16, `fxConversionHelper` 3/3, GrowthChart 6/6 |
> | `… dev.py test --test-port 6157 --data-dir /tmp/librefolio-r2-i-charts front-utility core-unit "money rendered outside the masking channel"` | PASSED: 1 file, 6 test, 93 file esclusi dal filtro; lane `6157`, data `/private/tmp/librefolio-r2-i-charts` |
> | `dev.py front check` | 3 errori e 41 warning in 4 file, invariati; 0 righe citano i miei file |
> | `… dev.py test --test-port 6157 --data-dir /tmp/librefolio-r2-i-charts front-portfolio dashboard` | 5 falliti su 15: **gli stessi di S9** (E1–E5), confrontati per nome con `diff`. Passa il test che monta `PerformanceChart` («Performance view mounts … PerformanceChart (map)»): il codice nuovo gira senza errori a privacy spenta |
> | porte | 6157 e 6167 libere dopo i run |
>
> **Non ancora provato dal vivo**: nessun test accende la privacy (gli E2E di S2 sono nella test list). Lo verifico in S6
> sulla copia di prod.

> **⚠️ Fuori pista (due mascherature che il gate non può sorvegliare):** `axisTickAmount` di PerformanceChart e
> `yAxisFormatter` di GrowthChart non sono mai stati hit del gate, né prima né dopo. Le loro template literal non hanno un
> token di valuta: la valuta non compare sull'asse.
> - Quindi, se qualcuno togliesse `maskable` da uno dei due assi, **nessun gate diventerebbe rosso**. Li proteggeranno
>   solo i test di S10: il `PerformanceChart.test.ts` nuovo e i casi privacy di `GrowthChart.test.ts`, entrambi già
>   nella §4.
> - Non allargo il gate per coprirli: è di J, e un token numerico senza valuta scatterebbe su ogni asse di percentuali.
>   Lo segnalo nel pacchetto per J.

### S2c — Review di J sul diff privacy ✅ 2026-09-24

> **Note implementazione:** verdetto di J arrivato dal coordinator alle 11:45. J ha letto il diff riga per riga, in sola
> lettura: `fmtCurrency`, `yAxisFormatter`, `shortMoney`, `axisTickAmount`, `netValueText`, la `markLine`, e il ridisegno
> con `void shouldMaskAmount()` più `lastRenderedMasked`. **Approvato** (D1/D14).
>
> | punto del pacchetto | verdetto |
> |---|---|
> | D13 | (a), scelta anche nel piano di J (riferito dal coordinator, 11:40). **Una parola da cambiare**: «would bring *that line* back here» si leggeva come la riga del P&L totale, che è già un hit. Ora dice «would bring the **definition** line back as an unregistered hit». Il test di GrowthChart entra nella `why` solo in S10 |
> | assi non sorvegliati dal gate | il gate non si allarga: d'accordo tutti e due. Li proteggono i test di S10, con 3 obblighi (§4): tacche senza cifre né `k`/`M` e con il segno; `%` non mascherato; zero di Performance mascherato |
> | zero come `—` nel tooltip Abs | accettato: è lo stesso costo già accettato in D8 |
> | ridisegno dal vivo | da fare in S6 con la lezione di R20: entrambi i versi **sul posto**, senza navigare, soprattutto **da spenta ad accesa**; per Growth ogni modo (`eur`, `pnl` in linea, candele, proventi) più `%` come controllo |
>
> Evidenza della correzione:
>
> | comando | esito |
> |---|---|
> | `cd frontend && npx vitest run src/lib/utils/privacy/moneyRenderSites.test.ts > /tmp/libreFolio_i_s2c_gate.log 2>&1` | 6/6, exit 0 |
> | `npx prettier --check src/lib/utils/privacy/moneyRenderSites.test.ts` | pulito |
>
> - **Seguito non bloccante (S10, condizionato):** `maskFormattedNumber` di J risolve la perdita di U+2212 in `sv-SE`
>   (reperto 11). Sta nel C1 di J, `176f19707`, che non è nel mio albero. Ci passo sopra i quattro formatter solo dopo
>   che quel C1 è nel target e la mia base è aggiornata. Registrato nella riga S10 della §4.
> - Il checkpoint di S2 si può preparare. Lo mando dopo la verifica dal vivo di S6, che J ha chiesto e che fa parte
>   dell'evidenza del checkpoint.

### Checkpoint C1 (unico, D14) — pronto ✅ 2026-09-24 12:21

> **Note implementazione:** il gate-prep di J è arrivato prima di C1, quindi per D14 il checkpoint è uno solo:
> S0–S6, S9 e S2 (S2a, S2b, S2c). Restano fuori S7, S7b, S8, S10 e S11. Le misure sono delle 12:17–12:21.
>
> **Stato runtime, chiuso prima di consegnare:**
>
> | verifica | esito |
> |---|---|
> | server della copia | fermato; il processo non c'è più; `lsof` su 6157 e 6167 vuoto |
> | copia di prod | rinfrescata dalla snapshot con la procedura di §5. La vecchia, con l'hash usa-e-getta, è in `…-prodcopy.prev-20260924-121740`, spostata e non cancellata. `cmp`: `app.db` è identico byte per byte alla snapshot. Versione `004_release_1_2_0_schema`, nessun marcatore. Sulla copia torna l'hash vero della password |
> | file della password usa-e-getta | cancellato ora, prima di S12 (registro S6) |
> | `git diff --check` | pulito |
> | stage | vuoto; 12 file modificati e 2 nuovi |
> | build servito | `frontend/build/` delle 11:34, successivo a ogni mio edit di prodotto (l'ultimo alle 11:30). Un server riacceso mostrerebbe il codice del checkpoint |
>
> **La coppia, rimisurata e non ereditata:**
> - Target `dev_release2` = `2a23b7ad3`, merge-base `f1047f766`, HEAD `2a5927c48`. C0 non è ancora nel target, come
>   previsto.
> - Il target tocca 4 path, fra journal e istruzioni. I miei sono 15: i 14 sporchi più `_frontend_utility.py` di C0
>   (`moneyRenderSites.test.ts` sta in entrambi i gruppi). **Intersezione vuota** (`comm`).
> - `git merge-tree --write-tree dev_release2 HEAD`: pulito, exit 0. I 14 path sporchi non si possono simulare senza
>   un commit, ma senza path in comune un conflitto testuale non può esserci.
>
> **Mappa degli hunk**, per chi fa lo stage (`git diff` con contesto 3):
>
> | file | hunk → slice |
> |---|---|
> | `GrowthChart.svelte` (17) | 1 (import): S5 e S2a su righe adiacenti, servono `e`; S9 si separa con `s` · 2, 4, 13–16: S5 · 3, 6, 8–11: S2a · 5: S1b · 7: S1b / S2a / S1b, si separa con `s` · 12, 17: S9 |
> | `PerformanceChart.svelte` (6) | 1, 2, 6: S2b · 3, 4, 5: S1b |
> | `moneyRenderSites.test.ts` (2) | S2a e S2b insieme; J li ha rivisti come un diff solo |
> | tutti gli altri | una slice per file |
>
> **Commit proposti, due opzioni** (li esegue il developer; nessun file `/tmp/libreFolio_commit_*`, i messaggi stanno
> qui):
> - **(1) Per slice, nell'ordine di esecuzione.** Ogni confine di commit è uno stato che ho misurato davvero: S1b → S3 →
>   S4 → S4b → S5 → S9 → S2.
>   1. `docs(journal): plan round-4 chart review`
>   2. `chore(charts): expose growth/perf chart instances`
>   3. `fix(assets): read missing sync detail as cancel`
>   4. `feat(dashboard): remember allocation view`
>   5. `fix(dashboard): map every asset type to an emoji`
>   6. `feat(dashboard): remember growth chart view`, più il hunk della gallery se è pronto
>   7. `fix(charts): shorten candle caption`
>   8. `fix(privacy): mask growth and performance amounts`
>
>   Richiede lo stage per hunk su GrowthChart (1 e 7) e PerformanceChart. Su richiesta preparo le patch in `/tmp` e le
>   verifico fuori dal repository: applicate in sequenza a una copia dei file di HEAD, poi confrontate con `cmp` con
>   l'albero. Così lo stage diventa `git apply --cached` e nessuno fa `add -p` a mano.
> - **(2) Per file, senza chirurgia.** 1 journal · 2 S3 · 3 S4 · 4 S4b · 5 `feat(charts): privacy, view memory, short caption`
>   con i 9 file restanti (S1b, S2, S5, S9). Gli stati dopo i commit 2–4 non li ho misurati da soli: sono file disgiunti
>   dal resto, ed è l'unico argomento.
>
> **CHANGELOG proposto per questo checkpoint** (lo scrive il coordinator; §9 ha l'elenco completo del round). S1b e S3
> non hanno voce: non cambiano niente di osservabile.
> - 🐛 privacy: assi, etichette e tooltip di Crescita e Performance nascondono gli importi;
> - ✨ Crescita e Allocazione ricordano la vista;
> - 🐛 Allocazione storica: emoji proprie per materie prime, immobiliare e tipo ignoto;
> - 🔄 la didascalia delle candele è breve e scorre se non entra.

> **⚠️ Fuori pista (l'opzione (A) prometteva una verifica che non si può fare):** avevo scritto che il hunk della
> gallery l'avrei verificato «con un run mirato nella lane suite». Non si può, per tre motivi:
> - `gallery.spec.ts` è escluso dal runner: `scripts/test_runner/_inventory.py:54` lo definisce «a docs tool, not a
>   test»;
> - `dev.py mkdocs gallery` non ha `--data-dir` (`dev.py:2355-2376`), quindi girerebbe sul DB di default del worktree,
>   fuori dalla mia lane;
> - scrive PNG versionati in `mkdocs_src/docs/gallery/` (`gallery.spec.ts:28`).
>
> Quindi la verifica del hunk, quando esiste, è solo statica: `prettier --check` e la lettura del diff. La prova vera è
> la prossima rigenerazione della gallery, che per costruzione è un'operazione del developer. Glielo dico nel
> checkpoint, insieme alla finestra dell'opzione (B): esiste solo se la gallery viene rigenerata prima che il hunk
> entri.
