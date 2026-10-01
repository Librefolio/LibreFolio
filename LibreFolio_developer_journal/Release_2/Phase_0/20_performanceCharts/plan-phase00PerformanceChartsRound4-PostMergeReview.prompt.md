# Performance charts — round 4: review d'uso post-merge (R5–R11, R21, §2.5, P4-11, emoji K) + prosecuzione

**Stato:** IN ESECUZIONE — piano v3 presentato il 2026-09-23, approvato il 2026-09-24. C1 committato il 2026-09-24
alle 14:18: 8 commit per slice, `cb7ae3476`…`804bc9903`. C2 committato alle 14:51: `980dee4bf` (gallery) e
`6a88561fd` (registro). C3 committato alle 15:39: `671d4ab49` (docs di S11 in parte: memoria, privacy e candele) e
`4d885f1e8` (registri). Il 25/09 il developer ha deciso tutto nella chat di I: D4 (via coordinator), poi D16, D17, D18
e l'OK sulla test list di S10, con E8 ed E9 in più (§7; registro «Pausa e ripresa dopo il riavvio»). S7, S7b, S8 e S10
sono sbloccate. `needs_engine` va per primo, in un commit a sé (coordinator, 15:24 e 15:37; registro «Triage del
contratto di `/portfolio/report`»). Pausa dal 24/09 alle 18:35 al 25/09 alle 09:09, con un riavvio in mezzo.
C4 committato il 2026-09-28 alle 11:41 (`00bb1ac75`…`472f51498`), poi il merge di `dev_release2` (`9016bb0d1`).
C5 committato il 2026-09-29 alle 10:02 (`026bc20fb`…`5e638a2ed`), poi il merge di `dev_release2` con K
(`b2112ba61`, 12:37). C6 committato il 2026-09-29 alle 22:26: 6 commit, `6d8b951bc`…`602ea299e` (emoji, tipi E2E,
due margini, la guardia dei grafici dei lotti, journal), poi il merge di `dev_release2` (`921f1fc05`, 22:31).
D23 con D23b ✅ il 2026-09-30 alle 00:03; C7 committato il 2026-09-30 alle 10:01: `9d8fb520b` e `039baea22`.
Poi S7 (coordinator, 10:04).
**Workstream:** I (grafici performance) · ramo `e-alfy-performance-charts-plan` · coordinatore
`c8328a01-f208-4ade-a352-0486d1f14de2`.
**Baseline:** `dev_release2` = `f1047f766` (fast-forward), albero pulito, rimisurata il 2026-09-23 prima di ogni
versione del piano e il 2026-09-24 dopo l'approvazione. Poi, sul ramo: C0 di J (`2a5927c48`, fast-forward, 11:16),
C1 (`804bc9903`, 14:18), C2 (`6a88561fd`, 14:51) e C3 (`4d885f1e8`, 15:39); C4 (`472f51498`, 28/09 11:41), il
merge `9016bb0d1` (11:45); C5 (`5e638a2ed`, 29/09 10:02), il merge con K `b2112ba61` (12:37); C6 (`602ea299e`,
22:26), il merge `921f1fc05` (22:31).
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
| S5 | R21 Crescita | S1b | ✅ 2026-09-24 (verifica live in S6). Fix della gallery: commit a sé dopo C1 (opzione B), riga G |
| S6 | Riproduzione R8/R10 sulla copia | S5 | ✅ 2026-09-24 12:05: R8 = 3 cause + 1, R10 = il moncone di coda; R21, S9 e privacy verificati dal vivo; reperto nuovo (tacche Y doppie → D18) |
| C1 | Checkpoint unico (D14): S0–S6 + S9 + S2 | S2c, S6 | ✅ pronto 2026-09-24 12:21 · ✅ **committato 14:18**: 8 commit per slice, `cb7ae3476`…`804bc9903` (registro «C1 committato») |
| G | Gallery: Abs esplicito prima dello scatto `main` | C1 (opzione B) | ✅ 2026-09-24: hunk scritto e verificato staticamente (registro «G»); ✅ **committato in C2**: `980dee4bf` |
| C2 | Checkpoint: G + registro di C1 | G | ✅ **committato 2026-09-24 14:51**: `980dee4bf`, `6a88561fd` (registro «C2 committato») |
| C3 | Checkpoint: docs di S11 in parte + registri di C2, del triage e di S11 | S11 in parte | ✅ autorizzato dal coordinator 2026-09-24 15:24 · ✅ **committato 15:39**: `671d4ab49` docs, `4d885f1e8` registri (registro «C3 committato») |
| C4 | Checkpoint: S10 backend e unit, registri | S10 passi 1–10 | ✅ **committato 2026-09-28 11:41**: 8 commit, `00bb1ac75`…`472f51498`; merge `9016bb0d1` (registro «Checkpoint C4 — committato») |
| C5 | Checkpoint: S10 E2E (brief 03, E7) e registri | C4 | ✅ **committato 2026-09-29 10:02**: `026bc20fb`…`5e638a2ed`; merge con K `b2112ba61` (registro «Checkpoint C5 — committato») |
| C6 | Checkpoint: emoji, tipi E2E, margini della Crescita e dei lotti, guardia `axisBuilder`, registri | C5 + merge con K | ✅ pronto 2026-09-29 15:27 · ✅ **committato 22:26**: 6 commit, `6d8b951bc`…`602ea299e`; merge `921f1fc05`, gate rapido verde (registri «Checkpoint C6 — committato» e «Gate rapido sulla revisione combinata `921f1fc05`»). Dopo: D23 con D23b |
| C7 | Checkpoint: D23 + D23b (il segno del locale nei grafici, il colore dello zero), registri | C6 + merge `921f1fc05` | ✅ pronto 2026-09-30 00:07 · ✅ **committato 10:01**: `9d8fb520b`, `039baea22`; `dev_release2` già contenuto, nessun merge (registro «Checkpoint C7 — committato») |
| C8 | Checkpoint: S7 (asse a scala di Candele e Proventi, riga «parziale» con `escapeHtml`), registri | S7 | ✅ pronto 2026-09-30 23:51: 3 commit su `039baea22` (il pianificatore; la cura di S7; il journal), il runner diviso fra i commit 1 e 2; prima la `desc` del runner e i doc di tre helper di test (registri «Checkpoint C8 — preparazione» e «Checkpoint C8 — pronto») · ✅ **committato 2026-10-01 11:04**: `7bfa064f0`, `69cba356f`, `de5349e46`; merge `851d3a5cf` con `dev_release2` (`8f18416df`: il passo 13 di K e le scelte di L), una regione risolta in `GrowthChart.svelte`, gate verde (registri «Checkpoint C8 — committato», «Allineamento a `dev_release2` — merge `851d3a5cf`» e «Gate sulla revisione combinata `851d3a5cf`»). Dopo: S7b |
| C9 | Checkpoint: S7b (tacche del denaro esatte e distinte, il meno del locale sugli assi, il bordo senza etichetta), registri | S7b | ✅ pronto 2026-10-01 15:02: 2 commit su `cd6502084` (la cura con i test; il journal); proposte al coordinator la `desc` di `growth-chart-memo` e la riga del CHANGELOG (registro «S7b — passo 6») |
| S7 | Asse dei bucket (R8 dopo D4, R10) | S6 | ✅ **2026-09-30 23:05** (avviata dal coordinator alle 10:04): il pianificatore `growthLadderAxis.ts` e la cura di `GrowthChart.svelte`; la riga «parziale» passa per `escapeHtml` (fuori pista, registro «S7 — passo 6»). Unit, build, E2E seriale e con 4 worker verdi. Decisioni: D4 ✅, D16 = (ii)+(i) ✅, D17 = (a) ✅ (§7) |
| S7b | Tacche Y doppie (reperto N1) | S7 | 🔓 D18 = sì ✅ 2026-09-25: assi del denaro di Crescita e Performance; `%` escluso · ▶️ avviata 2026-10-01 (coordinator, dopo `cd6502084`): analisi ✅ 13:19; D25 = B ✅ 13:51; test rossi ✅ 14:46; cura ✅ 14:50; gate ✅ 15:00 · ✅ **2026-10-01 15:02**, in C9 (registro «S7b») |
| S8 | R11 valore di acquisto | S7 | ⏳ legge soltanto il motore (risposta al coordinator, 12:25): prima di iniziare rimisuro per simbolo |
| S8b | Guida del Rendimento mobile nel dettaglio asset (D24) | S8, D24 | ⏳ approvato dal developer (2026-09-30 11:52): «?» in fondo alla riga della finestra, solo in Rendimento mobile, verso la guida utente; commit a sé dopo S8 |
| S9 | R9 didascalia | S1 | ✅ 2026-09-24 (scorrimento a 375 px: verifica live in S6) |
| S10 | Debiti e test residui | S1 | 🔄 **OK del developer sulla test list, 2026-09-25**, con E8 ed E9 in più (D8 ✅ 2026-09-24). Ordine: `needs_engine` per primo, in un commit a sé (coordinator, 15:24 e 15:37), poi il contratto di `/portfolio/report` (registro «Triage del contratto di `/portfolio/report`») e il resto di §4. **Passo 1 ✅ 2026-09-25 10:38**: `needs_engine` corretto (6 rossi → verdi), contratto a 13 chiavi, `api portfolio` 55/55, `services roi-fifo-utils` 507/507 (registro «S10 passo 1»). **Passo 2 ✅ 11:10**: D20, il test dei Proventi pulisce i suoi dati, misurato con un controllo positivo; `api portfolio` 55/55 (registro «S10 passo 2»). **Passo 3 ✅ 11:37**: `chartCoreHelpers.test.ts` 159 → 145 (D19: −14), i 7 specchi ri-pinnati ognuno col suo perché, C4 convertito sulla copia fedele; 145/145, 0 falliti (registro «S10 passo 3»). Reperti del passo → D21, ✅ deciso dal developer (§7). **Passo 4 ✅ 11:59**: `AllocationPanel.test.ts` (3 casi) e `allocationTypeEmoji.test.ts` (8 casi), nuovi, 11/11 (registro «S10 passo 4»). **Passo 5 ✅ 12:15**: `GrowthChart.test.ts` 6 → 17 casi (S2a, S5, S9) e la `why` di D13, 23/23 (registro «S10 passo 5»). **Passo 6 ✅ 12:15**: i 3 file nuovi registrati nel runner, nome visibile di `growth-chart-memo`; `check-orphans` pulito (registro «S10 passo 6»). **Passo 7 ✅ 12:27**: la pulizia di `…positions_contribution_is_date_aware`, assegnata sotto D20, misurata con un controllo positivo: nessuna perdita; `api portfolio` 55/55 (registro «S10 passo 7»). **Passo 8 ✅ 12:30**: `PerformanceChart.test.ts`, nuovo, 6/6 (registro «S10 passo 8»). **Passo 9 ✅ 12:30**: D21 e D22 su `chartCoreHelpers.test.ts`, 145 → 142 → 144, 144/144, 0 falliti (registro «S10 passo 9»). **Passo 10 ✅ 12:33**: `front check` al floor, 3 errori e 41 avvisi, nessuno nei miei file (registro «S10 passo 10»). **C4 ✅ 2026-09-28 11:41** (8 commit, `00bb1ac75`→`472f51498`), poi il merge di `dev_release2` (`9016bb0d1`) e i gate sulla revisione combinata, tutti verdi (registro «Validazione sulla revisione combinata»). **Brief 03 ✅ 13:00**: dashboard 15/5 → **18/18**, broker detail 28/1 → **28/28**, in seriale e con `--workers 4` (registro «S10 — brief 03»). **E7 ✅ 13:52**: asset detail 28/1 → **28/28**, in seriale e con `--workers 4`; la coda risvegliata è verde (registro «S10 — E7 completato»). **C5 ✅ committato 2026-09-29 10:02** (registro «Checkpoint C5 — committato»). **C6 ✅ committato 22:26**, merge `921f1fc05` e gate rapido verde (registro «Checkpoint C6 — committato»). **D23 con D23b ✅ 2026-09-30 00:03**: il segno del locale in `fmtCurrency` e `shortMoney`, una sola forma per le righe con segno, il colore dello zero; test ri-pinnati e nuovi, corsia verde (registro «D23 + D23b»). **C7 pronto 2026-09-30 00:07** (registro «Checkpoint C7 — pronto») |
| S11 | Docs (docs-writer) | S2b, S3, S4b, S8, S9 | 🔄 in parte, ✅ 2026-09-24 (autorizzata dal coordinator alle 14:45; registro «S11 in parte»): `charts.en.md` (memoria della vista, privacy di Crescita, didascalia delle candele, candele senza broker, memoria di Allocazione) e `positions.en.md` (privacy di Performance). Accettato dal coordinator (15:24) ed entrato in C3 (`671d4ab49`). Il resto dopo S7/S8, più due voci aggiunte (coordinator, 16:07): `index.en.md`, che conta tre schede invece di quattro (reperto di J), e la deriva dei nomi, che c'è anche nella mia frase di C3 (registro «S11-finale — voci aggiunte») |
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

✅ **OK del developer, 2026-09-25** (`ask_user` nella chat di I): «OK alla test list, con E8 ed E9 aggiunti a S10».

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
| S7 | `GrowthChart.test.ts` + `dashboard.spec.ts` | **Bucket (D16-ii)**:<br>• l'ultimo bucket finisce sull'ultima data e ha N giorni<br>• se `length % N ≠ 0` il parziale è il **primo**, marcato con i suoi giorni<br>• numero di bucket = `ceil(length / N)`, come oggi<br>• una fixture di 93 giorni a 1M dà 4 bucket: 3 + 30 + 30 + 30<br>**Etichette**:<br>• nessuna etichetta mostrata compare due volte, per ogni gradino di una fixture da 2 anni<br>• mai il formato ISO<br>• se entrano tutte, ognuna è la data di chiusura del suo bucket; oltre l'anno porta anche l'anno<br>• se non entrano, una per mese al massimo, sul bucket che contiene il 1°, quando così nella finestra visibile restano almeno 2 etichette<br>• altrimenti (D4-bis, finestra corta): date di chiusura, una ogni k bucket, ancorate all'ultimo bucket della serie; nessuna doppia, e almeno 2 etichette a 1M a 1G su un plot da telefono<br>**Separatori**:<br>• `splitLine.interval` è una funzione, non `'auto'`<br>• slot ≥ T → tutti i confini; slot < T → solo il primo bucket di ogni mese<br>**Proventi**:<br>• `xAxis.type = 'category'`<br>• costi nello stack dei proventi (D17-a)<br>• `barCategoryGap` e `barGap` fissati nell'opzione, non derivati dai dati<br>**Offerta**: con una fixture da 2A, in Proventi 1S non è offerto e 2S sì (D17-a); le candele non cambiano<br>**E2E** (lane suite): la larghezza di una barra dei Proventi, letta con `getItemLayout` via `__lfChart`, è la stessa prima e dopo un `datazoom` a 0–99 %. È il sintomo di R10, misurato come in S6. I test Income esistenti restano verdi |
| S7b | `GrowthChart.test.ts` + `PerformanceChart.test.ts` | **Solo se D18 = sì.** Formatter Y a privacy OFF:<br>• tacche 5000…8000 a passo 500 → 7 etichette distinte<br>• 1000…2500 a passo 500 → 4 distinte (oggi `1k, 2k, 2k, 3k`)<br>• i valori interi restano senza decimali (`2k`, non `2,0k`)<br>**Privacy ON**: invariato, nessuna cifra (`•••`, `-•••`) |
| S8 | `GrowthChart.test.ts` | nome e stack condivisi; legenda una volta; 900 + 300 → riga totale 1,200.00; identità di somma |
| S9 | `GrowthChart.test.ts` + `dashboard.spec.ts` | **jsdom**: la didascalia c'è solo in candele, porta la classe `overflow-scroll-marquee` e la chiave corta. Il `ResizeObserver` inerte di `$test/component` basta: l'overflow qui non si prova.<br>**E2E a 375 px**: `data-overflowing="true"` sulla didascalia. L'attributo lo mette l'azione, quindi non serve nessuna attesa a tempo.<br>`dev.py i18n audit` pulito. Gli specchi rotti da S9 sono già convertiti (registro S9) |
| S10 | `chartCoreHelpers.test.ts` / `dashboard.spec.ts` / `brokers-detail.spec.ts` / `test_portfolio_api.py` | **Cancellazioni** a mano, per nome, una alla volta, contando prima e dopo (−N esatto):<br>• C6, C9, C10, C11 → −4 su 159; **con D19 (developer, 2026-09-25) anche i 10 verdi del blocco di C10/C11, che provano solo una copia locale di una funzione uscita dal prodotto: −14, 159 → 145**, insieme alla copia e agli helper rimasti senza chiamanti. **C8 non si cancella più**: è guarito in S9, perché la didascalia consuma di nuovo la chiave corta. La causa di C9 è cambiata: la coppia corta/lunga non esiste più (registro S9)<br>• E1–E3, un solo `for` → −3 su 15; con loro vanno gli helper rimasti senza chiamanti<br>**Ri-pin**, ognuno col suo perché scritto:<br>• i 7 specchi<br>• E4 sulla scala: in linea nessuna scala e nessun badge; in candele la scala c'è e il gradino premuto non è `1d`<br>• E5/E6 con un'àncora a segno opzionale, soglia 3 (Dividend, Interest, Total: righe sempre rese)<br>• **E8/E9** (trovati nella misura «prima» del 2026-09-25, registro «Pausa e ripresa dopo il riavvio»; aggiunti dal developer): `dashboard.spec.ts:467` conta gli importi **con segno** (Totale più uno per broker), e `:496` riconosce l'OHLC contando quelli **senza segno**. Sotto il puntatore oggi c'è 2026-08-09, dove Coinbase vale `EUR 0.00`, e lo zero non ha segno per scelta (`e7773a143`). Rimedio come E5/E6: le righe si contano per segno opzionale, e l'OHLC si riconosce per riga, non per assenza di segno<br>• **E7** (trovato in S3; rimedio raffinato il 2026-09-24, registro «C1 committato»): la data dell'evento del peer, **solo per MAX**, ricavata dal range accettato invece che cercata nella fixture fissa (`:1970`). `successorReadyEvents` (`:769`) resta com'è, perché lo leggono anche il mock condiviso (`:2157`, `:2165`) e sezioni dello stesso test oggi verdi, a range assoluto (`:6088`, `:6241`). La correzione riaccende 61 `expect(` e 3 `expect.poll(` fermi dal 18/09: un rosso che ne esce va attribuito, non è per forza E7. Prima dell'edit lo annuncio al coordinator<br>• **Contratto di `/portfolio/report`** (`test_portfolio_api.py`, triage del 2026-09-24, registro omonimo; verdetto «assumption» accettato dal coordinator alle 15:24): `test_report_allocation_source_authenticated_contract` allarga l'insieme a mondo chiuso di `:767` da 7 a 13 chiavi, come il gemello di servizio `test_portfolio_service.py:3767` allargato nel merge `b7a0b1e1a`. **Non** a `⊇`: un sovrainsieme renderebbe il test cieco a una sezione di troppo. In più `is None` per ognuna delle 6 sezioni, perché il test esiste per dire «senza eseguire le altre viste». La coda (59 `assert` dopo `:767`, ferma dal 21/09) gira per la prima volta: un rosso che ne esce va attribuito prima di correggerlo<br>• **`needs_engine`** (difetto latente, registro omonimo; ✅ deciso dal coordinator alle 15:24: mio, in un **commit a sé**; alle 15:37: aspetta l'OK come il resto di S10, poi va **per primo**, perché è la parte più piccola e la meno legata alle altre). Prima il test API: chiede `allocation_source` insieme a una delle 6 sezioni, senza le 4 viste originali, e vuole la sezione piena e il suo nome in `included_features`. Oggi è rosso: la sezione torna `null` e `included_features` vale `["allocation_source"]`. Poi la correzione, una sola istruzione: i 6 flag in `needs_engine` (`portfolio_service.py:2404`; con 300 colonne black la spezzerà su più righe). Il test diventa verde. La cache L2 non chiede altro: la sua chiave contiene già i 6 flag (`:2375-2380`, letto il 2026-09-24), quindi un report del ramo corto non può rispondere a una richiesta diversa. Nessun conflitto con Risk: `a766a9d5d` tocca il file solo a `:694-695`, un import (misura del coordinator)<br>**Copertura mancante**: nessun E2E sulla scala `growth-candle-width-*`. Proposta: la scala è offerta in candele e in income e non in linea; un clic sposta `aria-pressed` e ridisegna (`data-chart-renders` +1)<br>**Registro (D13, deciso da J):** quando esiste il test privacy di GrowthChart (S2a), aggiorno la `why` della riga P&L totale del tooltip perché lo citi. Oggi la `why` non lo cita, perché il test non c'è<br>**Seguito non bloccante (J, S2c):** a privacy OFF `sv-SE` perde il meno U+2212 (reperto 11). J l'ha risolto con `maskFormattedNumber`, identico byte per byte da smascherato, nel suo C1 `176f19707`. **Solo quando** quel C1 è nel target e la mia base è aggiornata: `fmtCurrency`, `yAxisFormatter`, `shortMoney` e `axisTickAmount` passano su quella primitiva. Prima no: non è nel mio albero |

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
| **Risk** | R12 `AllocationPieChart.svelte`, forse props `AllocationPanel`; test allocazione in `dashboard.spec.ts`; usa i miei 12 rossi per sottrazione; ha già risolto un conflitto su `AllocationHistoryChart` (`7fd660846`) | `AllocationPanel.svelte` (S4), `AllocationHistoryChart.svelte` (S4b, un solo hunk in `getCategoryEmoji`), `dashboard.spec.ts`, lista rossi | testuale + semantico | 🟢 (era 🟡) | **Verificato dal coordinator (2026-09-24)**: R12 è `a34d2b4d8` e tocca solo `AllocationPieChart.svelte`, `allocationRings.ts` e il suo test. `AllocationPanel` è intatto, con le stesse props. La torta non ha una mappa tipo→emoji: usa le PNG (`getAssetTypeIconUrl`) e le emoji di settore del backend. Non c'è niente da condividere. Resta: lista rossi riannunciata a ogni modifica. **R12 rivista (2026-09-24):** la torta raggruppa ora per veicolo, con `charts/allocationFamily.ts` (solo nel ramo di Risk). Il mio `AllocationHistoryChart.svelte:596` passa ancora `primaryAssetType`: scelta in **D15**, una riga all'integrazione. **Palette (2026-09-24 11:09):** il coordinator ha girato a **Risk** il mio reperto sulle copie delle palette in `colors.test.ts` e `allocationHierarchy.test.ts`: sono nate in `420b90ebd` (famiglia D71; provenienza verificata con `git log --diff-filter=A`). Non va in S10. Il mio `AllocationHistoryChart.svelte` verrebbe solo letto, e i miei due hunk non toccano `PALETTE_*`. La torta ha a `:197` lo stesso `resolvePrimary: primaryAssetType` che Risk porta su `allocationFamily`: è la stessa mossa di D15. **D24 (2026-09-30):** nel suo ramo Risk ha messo `docs_path` sul mio `calendar_rolling_return.py`. Io quel file non lo tocco: nessun conflitto, il metadato arriva col merge |
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
| D4 | developer, dopo S6 | R8: regola di etichette e separatori, soglia T | **Storyboard v2 in §2**, sulle misure di S6. Raccomandazione:<br>• etichette con la data di chiusura quando entrano tutte, altrimenti il mese sul bucket che contiene il 1°;<br>• separatori su ogni confine sopra T = `CANDLE_MIN_SLOT_PX` (8 px, soglia già esistente), solo ai confini di mese sotto.<br>Nessuna etichetta doppia per costruzione, niente ISO, semantica N-giorni invariata<br>✅ **Approvata dal developer (2026-09-25, via coordinator, testuale: «sì, approvo quello che sta suggerendo I»)**<br>**Addendum D4-bis (developer, 2026-09-30, `ask_user` nella chat di I):** nelle finestre corte la regola del mese dà una sola etichetta, o nessuna (1M o MTD a 1G o 3G, 1S sul telefono, uno zoom sotto i 2 mesi circa), mentre oggi se ne vedono diverse. Se nella finestra **visibile** la regola del mese darebbe **meno di 2 etichette**, si passa alle date di chiusura, **una ogni k bucket**: k è il più piccolo che entra, e le etichette sono ancorate all'ultimo bucket della serie (`(n−1−i) % k = 0`), così l'ultimo bucket è sempre etichettato e le etichette restano ferme quando si scorre. Restano le garanzie di D4: nessuna etichetta doppia (sono date diverse), niente ISO, separatori invariati. Esempio: 1M a 1G, plot 527 px, slot 17 px → «2 set, 6 set … 26 set, 30 set».<br>✅ **Scelta del developer, testuale: «Sì, aggiungi il ripiego sulle date di chiusura diradate (Raccomandato)»** |
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
| D16 | developer (da S6, 2026-09-24) | il bucket parziale, cioè il resto di `length % N`, che oggi sta in coda: dove va e come si vede | Storyboard §2. **(ii) + (i)**:<br>• bucket ancorati alla fine: l'ultima candela chiude sull'ultima data ed è sempre piena;<br>• il parziale, che diventa il più vecchio, è marcato (corpo o barra chiari, tooltip «parziale: N gg su 30»).<br>Stesso numero di bucket; vale per candele e Proventi.<br>Sconsigliati: (iii) fonderlo nel penultimo (fino a 2N−1 giorni); (iv) scartarlo<br>✅ **Deciso dal developer (2026-09-25, `ask_user` nella chat di I): (ii)+(i)** |
| D17 | developer (da S6, 2026-09-24) | geometria dei Proventi: quante colonne per bucket | **(a) 3 colonne**:<br>• i costi, già negativi, scendono sotto lo zero nella colonna dei proventi (entrate sopra, uscite sotto), con gap 10 %;<br>• per colonna: 0,281 × slot, contro 0,163 × slot di oggi con 4 colonne e gap di default (tabella in §2 R10);<br>• legenda e tooltip invariati;<br>• si lega a S8: la terza colonna è il valore di acquisto (D2 = A).<br>Alternative:<br>• **(b)** 4 colonne con gap 10 %: 0,209 × slot; 1A/1S e 2A/2S restano, al limite (2,1 px);<br>• **(c)** 4 colonne con i gap di default: 1A/1S e 2A/2S escono dall'offerta<br>✅ **Deciso dal developer (2026-09-25, `ask_user` nella chat di I): (a), 3 colonne**, costi sotto lo zero nella colonna dei proventi, gap al 10 % |
| D18 | developer (da S6, 2026-09-24) | tacche Y doppie (reperto N1, fuori dal piano approvato): entrano nel round? | **Sì, come S7b**: stesse righe dei formatter già toccati da S2, stesso owner, un test piccolo. Regola: i decimali minimi che rendono esatta la tacca, così due tacche diverse non danno mai la stessa etichetta.<br>Il `%` (`toFixed(1)`) ha la stessa forma, latente sotto un passo di 0,1 % e mai osservata. L'indicazione «in % non va toccato» riguardava la privacy, ma la rispetto alla lettera: lo includo solo se il developer lo chiede<br>✅ **Deciso dal developer (2026-09-25, `ask_user` nella chat di I): sì, come S7b, sugli assi del denaro; il `%` resta escluso** |
| D19 | developer (da S10, 2026-09-25) | i 10 test verdi del blocco di C10/C11 («P&L zoom-window selector», `chartCoreHelpers.test.ts:2793-2929`) provano solo una copia locale di `computeZoomWindowRange`, uscita dal prodotto al round 3. Cancellato C10, non provano più nulla del prodotto: si cancellano? | **Sì**, con le regole di D8, insieme alla copia e agli helper rimasti senza chiamanti: −14 invece di −4, 159 → 145. C12 resta e si ri-pinna sulla scala delle larghezze. Per l'utente non cambia niente; un verde che non prova nulla è una garanzia falsa<br>✅ **Deciso dal developer (2026-09-25, `ask_user` nella chat di I): sì, −14** |
| D20 | developer (da S10, 2026-09-25) | il mio `test_report_income_history_flag_gates_section_and_reconciles_with_summary` (`8ed7a0f0d`, 18/09) non pulisce i suoi dati: a ogni corsa lascia nel DB della lane un utente, un broker, un asset e 3 transazioni. Non era nella test list: entra in S10? | **Sì, in un commit a sé**: `try/finally` che cancella broker, asset e utente, con lo schema del test del contratto accanto (`:900-945`). Il test vicino con lo stesso difetto (`…positions_contribution_is_date_aware`, `13052a006`) non è mio: al coordinator<br>✅ **Deciso dal developer (2026-09-25, `ask_user` nella chat di I): sì, in S10, commit a sé** |
| D21 | developer (da S10 passo 3, 2026-09-25) | reperti di `chartCoreHelpers.test.ts` fuori dalla test list (registro «S10 passo 3»). **(a)** test verdi che descrivono le candele con l'overlay per broker, tolto il 21/09, e `toPositionalValue` del prodotto senza più chiamanti: si allineano? **(b)** `splitBySign`, la correzione dell'area che spariva al cambio di segno, non ha test; al suo posto i 6 `signCrossingScenarios` provano la versione di prima e affermano metà lunghe come la sorgente, falso con la correzione: si convertono? | **(a) sì**, prodotto compreso: `toPositionalValue` esce dal prodotto in S7 (tocca già il file); escono i suoi 3 test e i 2 letterali che la pinnano; la fixture ECharts reale del crash delle candele prende la forma vera (la candela da sola); `:1998` perde la metà broker; il titolo di `:2361` si corregge. 145 → 142. **(b) sì**: gli stessi 6 casi, su una copia fedele di `splitBySign` legata alla sorgente come C4. Conteggio invariato<br>✅ **Deciso dal developer (2026-09-25, `ask_user` nella chat di I): (a) sì, prodotto compreso; (b) sì, convertiti**<br>**Principio del developer, da applicare d'ora in poi (stessa risposta):** il prodotto per ora va bene; i test devono provare il prodotto di oggi, non i passi intermedi. Se scrivendo i test saltano fuori test vecchi, si tolgono; se scrivendo i nuovi saltano fuori pezzi del prodotto che non servono più, è corretto toglierli. Le domande al developer vanno fatte in italiano |
| D22 | developer (da D21b, 2026-09-25) | `signCrossingScenarios` convertito su `splitBySign` (142/142): test-author, con le mutazioni sulla copia, trova due rami del prodotto che nessuna riga esercita. (1) Lo zero accanto a un valore positivo: il titolo promette «niente inventato a uno zero», ma nessuna riga lo prova. (2) Un incrocio fra ampiezze diverse: tutti gli incroci sono fra ±5 e ±20, quindi un peso preso dal lato sbagliato resta verde. In più 3 asserzioni sulla linea di riferimento non possono fallire, perché il test la costruisce da sé. Aggiungo le 2 righe e tolgo le 3 asserzioni? | **Sì**: righe `[5, 0, -5]` (0 incroci) e `[30, -10]` (incrocio alle 18:00); la terza colonna diventa la lista degli istanti scritta a mano; via le 3 asserzioni vuote. 142 → 144. I nomi «pari» e «dispari», scambiati, li correggo io: stessi casi, nome giusto<br>✅ **Deciso dal developer (2026-09-25, `ask_user` nella chat di I): sì, 2 righe e via le 3 asserzioni** |
| D23 | developer (da S10, dopo la privacy di J, 2026-09-28) | I quattro formatter degli importi nei grafici scrivono il meno ASCII: `fmtCurrency` e `yAxisFormatter` in `GrowthChart.svelte`, `shortMoney` e `axisTickAmount` in `PerformanceChart.svelte`. Li porto su `maskFormattedNumber` di J (`maskable.ts:133`), che lascia il segno come lo scrive il locale del browser? Il segreto non cambia in nessuno dei due casi: cifre e k/M mascherati, il segno visibile. Cambia solo il glifo. Dalla sonda (`files/d23_probe/`): U+2212 solo in sv, fi, nb, et, lt, sl, hr, eu e fa; en, it, fr ed es (le lingue dell'interfaccia), e anche de, nl e pt, usano il trattino ASCII | **Restare ASCII**: il formatter principale (`formatCurrencyAmountPlain`/`Html`, schede KPI e tabelle) scrive sempre `-`, e prima della privacy solo `fmtCurrency` seguiva il locale; gli assi e `shortMoney` erano già ASCII. Migrare vuol dire due convenzioni nella stessa app<br>✅ **Deciso dal developer (2026-09-28, `ask_user` nella chat di I), testuale: «Migrare tutti e quattro i formatter: il meno segue il locale del browser anche su assi ed etichette».** Conseguenza, da segnalare al coordinator: i grafici seguono il locale, le schede KPI e le tabelle restano ASCII (`currencyFormat.ts`, non mio). Esecuzione: dopo C5, in un commit a sé; gli assi insieme a S7b (D18), che riscrive le stesse righe. Da conservare: `EUR 0,00` per lo zero (S2a), lo zero dell'asse mascherato (D12), e in `shortMoney` la forma segno, simbolo, `•••`. I ri-pin degli unit (`PerformanceChart.test.ts` caso 6, `GrowthChart.test.ts`) vanno al test-author |
| D23b | developer (da D23, 2026-09-29, `ask_user` nella chat di I) | Nel tooltip della Crescita quattro righe con segno scrivono il segno a mano, prima della valuta, con il meno tipografico U+2212 fisso in tutte le lingue: il P&L totale (`GrowthChart.svelte:1957`), le righe P&L della linea (`:1973`), le righe per broker (`:2000`) e le righe di Income (`:2015`). Esempi: «+EUR 5,00», «−EUR 12,00». Con D23 il resto dei grafici scriverà il meno della lingua, dopo la valuta: «EUR -12,00» in it/en/fr/es. Senza intervento, nello stesso tooltip ci sarebbero due trattini e due posizioni. Opzioni proposte: il meno segue la lingua e la posizione resta (consigliata); U+2212 fisso; stessa forma del resto anche per la posizione | ✅ **Deciso dal developer (2026-09-29), testuale: «voglio che li uniformi, non puoi modificare l'helper?»**. Lo leggo così: una sola forma, prodotta dall'helper. `fmtCurrency` di `GrowthChart.svelte`, locale al grafico e mio (non `maskFormattedNumber` di J, che resta com'è), prende un'opzione «con segno» (`signDisplay: 'exceptZero'`): `+` per i guadagni, il meno della lingua per le perdite, niente segno per lo zero. Le quattro righe lo chiamano invece di scrivere il segno a mano. Risultato: «EUR +5,00» e «EUR -12,00» in it/en/fr/es, come le altre righe; mascherato «EUR +•••» e «EUR -•••». `maskFormattedNumber` tiene già il `+` iniziale (`LEADING_SIGN`, `maskable.ts`). Esecuzione insieme a D23, dopo C6. Il ri-pin di S2a in `GrowthChart.test.ts` (oggi «+EUR •••» sulla riga P&L) va al test-author |
| D24 | developer (richiesta del coordinator, 2026-09-30 11:40, senza urgenza) | Risk ha messo `docs_path` (la pagina teorica `financial-theory/fundamentals/returns/`) sul mio `ASSET_CALENDAR_ROLLING_RETURN`. Il plugin però ha `catalog_visible = False` (`calendar_rolling_return.py:125`), e il catalogo pubblica solo i visibili (`provider_registry.py:328`), quindi il `docs_path` non arriva a nessuna API. Il dettaglio asset disegna la modalità Rendimento mobile fuori dal catalogo, e oggi non ha nessun «?». Si mostra? Dove, e verso quale pagina? Opzioni: «?» in fondo alla riga della finestra, solo in modalità Rendimento mobile, verso la guida utente del grafico con un'ancora stabile (consigliata); stessa posizione verso la pagina teorica di Risk; nessun pulsante | ✅ **developer, 2026-09-30 11:52**: «Sì: «?» in fondo alla riga della finestra, solo in Rendimento mobile, verso la guida utente del grafico (consigliata)». → S8b, commit a sé; l'ancora e il rimando alla teoria in S11-finale; il test via test-author |
| D25 | developer (da S7b passo 1, 2026-10-01; il «−888» rimandato da S6) | La tacca di bordo non è una tacca regolare: ECharts la mette sul bordo che il grafico fissa (Crescita: minimo dei dati − 8 %, `GrowthChart.svelte:2245`; Performance: ±105 % della barra più lunga, `PerformanceChart.svelte:987-988`). Oggi `toFixed` la arrotonda e la nasconde; con D18 diventa esatta e illeggibile: `9,752k`, `93,64k`, `1,17344M`, `−2,55465K` (sonda ECharts 6, registro «S7b»). Nei Proventi senza costi è il «−888». Che cosa ci va? | **(B) solo tacche tonde (consigliata)**:<br>• linee, candele e `%` della Crescita: il bordo resta dov'è, senza etichetta (`showMinLabel: false`);<br>• Proventi: l'asse parte da 0, o dalla prima tacca tonda sotto i costi, come ogni grafico a barre;<br>• Performance: le due etichette di bordo spariscono (`showMinLabel`/`showMaxLabel: false`), le barre restano larghe come oggi.<br>Alternative:<br>• **(A)** bordo tondo: l'asse arriva a una tacca tonda; più spazio vuoto (P&L da −3,2k: asse a −6k), barre della Performance più corte (2.433: dal 95 % all'81 %);<br>• **(C)** com'è: il bordo stampa il valore esatto e resta il «−888»<br>✅ **B** (developer, 2026-10-01 13:51), dopo una domanda: nel P&L da −3,2k a 8,7k la tacca più bassa è −3k. Chiarito che l'asse parte da −4,15k: −3,2k è il punto più basso della linea, appena sotto la riga −3k, nella fascia senza etichetta; nulla è tagliato. Una tacca con etichetta sempre sotto il minimo è A, con la fascia vuota (qui fino a −6k): scartata |

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
- **Girato a J** (coordinator, 2026-09-24 15:24): le etichette di `PrivacyToggle` sono in inglese fisso («Hide
amounts» / «Show amounts», `:13`), senza i18n; nate in `b66e93003`. Le docs EN le citano alla lettera: se J cambia
il testo inglese, quella frase delle docs va riallineata.
- **CHANGELOG (proposte)**: 🐛 privacy: assi, etichette e tooltip di Crescita e Performance nascondono gli importi · 🐛 separatori/etichette candele allineati ai bucket · 🐛 l'ultima candela chiude sempre sull'ultima data, il bucket parziale è marcato (D16) · 🐛 barre Income piene dal primo render · ✨ Income mostra il valore di acquisto con la quota reinvestita in cima · 🔄 didascalia candele breve, scorre se non entra · ✨ Crescita e Allocazione ricordano la vista · 🐛 Allocazione storica: emoji corrette per materie prime, immobiliare e tipo ignoto · 🐛 tacche dell'asse Y sempre distinte (se D18).
- **Commit proposti**, in ordine indicativo (li esegue il developer). I commit di privacy vengono dopo il merge del gate-prep:
  - ⏭️ **Superata per C1** (2026-09-24): C1 è entrato come 8 commit per slice (registro «C1 committato»). Restano da
    fare il 7, il 7b, l'11, il 13 e il 14, più il commit della gallery (riga G) e quelli del registro.
  - ⏭️ **E per C2** (2026-09-24 14:51): il commit della gallery e il registro di C1 sono entrati come C2 (registro «C2
    committato»). Restano il 7, il 7b, l'11, il 13, il 14 e i registri successivi.
  - ⏭️ **E per C3** (committato 2026-09-24 15:39): 2 commit, `671d4ab49` con le docs di S11 in parte (una parte del
    14), poi `4d885f1e8` con i registri di C2, del triage e di S11 in questo file (registro «C3 committato»). Restano
    il 15 (S10, per primo quando arriva l'OK), il 7, il 7b, l'11, il 13, il resto del 14 (S11-finale, dopo S7/S8) e
    i registri successivi.
  - ⏭️ **E per C4** (committato 2026-09-28 11:41): 8 commit, `00bb1ac75`→`472f51498`, con il 15 per primo, il 13 e
    gli unit di S10 (registro «C4 committato»). Restano l'E2E di S10 ed E7 (C5, proposto: brief 03, E7 e registri),
    D23 (commit a sé, dopo C5), il 7, il 7b, l'11, il resto del 14 e i registri successivi.
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
  15. `fix(portfolio): run engine for every report flag` (proposta; S10, commit a sé con il suo test API)
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
- ⏭️ **Rimedio raffinato (2026-09-24):** derivare da `end` la fixture condivisa romperebbe sezioni oggi verdi. Il
  rimedio nuovo e la coda di asserzioni che E7 nasconde sono nel registro «C1 committato», voce E7.

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
>   - ⏭️ **Superato dalla decisione (B) del coordinator (2026-09-24):** il hunk arriva in un commit a sé dopo C1, e il
>     ramo di I entra nel target solo con quel hunk (riga G, registro «G»).
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

### Checkpoint C1 — committato ✅ 2026-09-24 14:18

> **Decisioni del coordinator su C1** (arrivate dopo la consegna delle 12:21):
> - **Gallery: (B).** C1 si committa subito e il hunk della gallery arriva nel commit successivo (riga G). La finestra
>   non tocca il target: il mio ramo non entra prima che il hunk ci sia, e dal mio ramo nessuno rigenera la gallery.
>   Nella lista d'integrazione del coordinator: *il ramo di I entra solo con il hunk della gallery*.
> - **Commit: (1), per slice.** Patch in `/tmp`, verificate fuori dal repository, e uno script con guardie: HEAD
>   `2a5927c48` e stage vuoto; i percorsi esatti, con `LC_ALL=C` da entrambi i lati; un digest del contenuto; `git
>   status` vuoto alla fine. Messaggi a 72 colonne, niente attribuzioni AI, nessun dato del developer. Il coordinator
>   rivede lo script prima di darlo al developer.
> - D4, D16, D17, D18 e l'OK sulla test list sono del developer. Non bloccano il checkpoint.
> - Il CHANGELOG lo scrive il coordinator all'integrazione, sotto `#### 📈 Dashboard charts`.
> - E7 va in S10, ed è mio.
>
> **Note implementazione:**
> - Dopo l'unica correzione autorizzata (§5, npx, 13:02) l'albero è rimasto fermo: il digest lo fotografa. Da lì il
>   bundle è stato costruito senza scrivere nel repository:
>   - gli stati di confine 0…8, generati dal `git diff -U0` di HEAD con una tabella esplicita blocco → commit (24
>     blocchi in `GrowthChart.svelte`, 8 in `PerformanceChart.svelte`; il primo blocco di GrowthChart diviso per riga).
>     Asserito: confine 0 = HEAD, confine 8 = albero di lavoro;
>   - le 8 patch, prodotte da un indice e da un object store temporanei sotto `/tmp`;
>   - lo script `run_commits.sh`, che il developer lancia due volte: `--dry-run`, poi senza opzioni.
> - **Le guardie dello script, nell'ordine:** posizione e toplevel; nessuna variabile `GIT_*` che reindirizzi il
>   repository; ramo e HEAD completo; nessun merge, rebase, cherry-pick, revert, bisect o `index.lock` in corso; stage
>   vuoto; i 14 percorsi esatti (porcelain v1); il digest; sha256 di patch e messaggi, e i subject; identità presente,
>   `core.hooksPath` non impostato, nessun hook attivo; una simulazione completa in un indice e un object store
>   temporanei (8 alberi, più `add -A` = albero 8). Per ogni commit: stage vuoto → `apply --cached` → `write-tree` =
>   atteso → `commit -F` → albero di HEAD = atteso → un solo genitore → messaggio identico byte per byte. Alla fine:
>   status vuoto, esattamente 8 commit, albero finale = albero 8.
>
> | verifica | come | esito |
> |---|---|---|
> | A — patch semplici | `git apply` in sequenza su una copia di HEAD, fuori da ogni repository; poi `cmp` con l'albero di lavoro | 14/14 identici, nessun file in più |
> | B — patch in stage | `git apply --cached` in un indice temporaneo, `write-tree` dopo ogni patch | gli 8 alberi attesi; l'albero di lavoro messo in stage con `add -A` dà l'albero 8 |
> | ogni confine 0…8, misurato su `2a5927c48` | copia scratch di `frontend/`; svelte-check, vitest intero, prettier sui file cambiati | svelte-check: **le stesse 44 diagnostiche** (3 errori, 41 warning) a ogni confine, confrontate per tipo, file e messaggio; nessuna in un mio file · vitest: confini 0–6, **gli stessi 12 nomi**; confini 7–8, 11 nomi, un sottoinsieme (0 nuovi, 1 guarito: *«consumes dashboard.pnlCandlesHypotheticalShort through $_()»*); `chartCoreHelpers` passa da 162 a 159 test al confine 7, come nel registro di S9 · prettier pulito a tutti e 9 |
> | digest del contenuto | `git diff --binary --full-index` con le opzioni fissate, su una **copia** dell'indice; poi i file nuovi in ordine, path e contenuto separati da NUL | `beb2b947…a446`, identico con git 2.53, 2.54 e 2.55 e con bash 3.2 e 5.3 |
> | dry-run sul repository reale | `run_commits.sh --dry-run` | rc 0 in tutte e 7 le prove: git 2.53, 2.54 e 2.55; bash 3.2 e 5.3; anche in `env -i` e dalla copia di backup. Byte e mtime dell'indice, oggetti, HEAD, refs e worktree invariati |
> | commit veri, in un clone usa-e-getta | `git clone --shared` sotto `/tmp`; lo script con due sole righe cambiate (worktree e bundle) | 8 commit lineari; alberi e messaggi byte per byte; i 14 file finali identici all'albero di lavoro. Le guardie scattano davvero: file manomesso → digest; path in più → lista; argomento sconosciuto → rc 2; secondo lancio → HEAD, e restano 8 commit; patch o messaggio manomessi in una copia del bundle → guardia del bundle. Clone cancellato |
> | messaggi | `awk 'length > 72'` e un controllo in Python | nessuna riga oltre 72; subject da 35 a 49 caratteri, corpo ≤ 70; solo ASCII; nessuna attribuzione AI; nessun dato del developer |
>
> - **Il coordinator ha rifatto le verifiche da sé** (13:37): sha256 dello script, HEAD, i 14 percorsi, stage vuoto,
>   subject e colonne, e il dry-run (rc 0). Dopo il dry-run HEAD, stage e albero erano invariati.
> - **Il developer ha committato alle 14:18.** La mia verifica dopo il commit, in sola lettura: ogni albero è quello
>   atteso, ogni messaggio è identico byte per byte al suo file, ogni commit ha un solo genitore; 0 merge; `git status`
>   vuoto.
>
> | # | commit | subject | albero |
> |---|---|---|---|
> | 1 | `cb7ae3476` | `docs(journal): plan round-4 chart review` | `828e3e25c076` |
> | 2 | `a1df69f21` | `chore(charts): expose growth/perf chart instances` | `8f1119869916` |
> | 3 | `ff9038487` | `fix(assets): read missing sync detail as cancel` | `ae601b522cc3` |
> | 4 | `08e9625d2` | `feat(dashboard): remember allocation view` | `38143947c8e9` |
> | 5 | `58101f08f` | `fix(dashboard): map every asset type to an emoji` | `2b74f1070d93` |
> | 6 | `4d8900a24` | `feat(dashboard): remember growth chart view` | `d760c573aab9` |
> | 7 | `99f7d15ec` | `fix(charts): shorten candle caption` | `3d8ab0d300ea` |
> | 8 | `804bc9903` | `fix(privacy): mask growth and performance amounts` | `f57579354549` |
>
> Il bundle resta in `/tmp/libreFolio_i_c1_commits/`, con una copia nella cartella di sessione di I: non è versionato,
> e si cancella in S12.

> **⚠️ Fuori pista (il mio ambiente non è quello del developer):** la shell dell'agente imposta
> `GIT_OPTIONAL_LOCKS=0`, un `GIT_EXEC_PATH` e un `GIT_CONFIG_SYSTEM` che puntano al git incorporato (2.53), e spegne
> `core.fsmonitor` con `GIT_CONFIG_*`. Nel repository invece `core.fsmonitor=true`, e il daemon sorveglia già questo
> worktree.
> - Le prime prove di sola lettura descrivevano quindi il mio ambiente, non il terminale del developer.
> - Rifatte in `env -i`, con i soli `HOME`, `PATH`, `USER`, `TERM`, `LANG` e `TMPDIR`: tre dry-run (git 2.55 di
>   Homebrew, git 2.54 di Apple, e la bash 5.3 di Homebrew) e i commit veri nel clone (git 2.55, bash 3.2). Tutto
>   verde, e il repository reale è rimasto invariato.
> - Lo script non dipende da quella variabile: passa `--no-optional-locks` in modo esplicito e calcola il digest su una
>   copia dell'indice. Il motivo della copia l'ho misurato in un repo di prova: `git diff` aveva riscritto la cache
>   degli stat dell'indice anche con `--no-optional-locks`.

> **⚠️ Fuori pista (messaggio 02 corretto dopo la prima consegna):** il corpo diceva che i commit 06 e 08 «si
> appoggiano» all'hook `__lfChart`. Non lo usano: lo useranno i test di S10. Il testo nuovo dice che lo leggeranno i
> test previsti. Dopo la correzione ho aggiornato gli hash nello script e rifatto tutte le verifiche della tabella.

> **⚠️ Fuori pista (npx: la correzione è arrivata prima dell'avviso che correggeva):** la correzione del coordinator
> («`--no-install` non protegge») mi è arrivata alle 12:14:56, l'avviso originale («usa `npx --no-install`») alle
> 12:30:26. Gli orari sono quelli degli eventi `user.message` della mia sessione.
> - **Il meccanismo, letto nel codice di npm 11.19.1 e non eseguito:** `npx-cli.js:82-83` traduce `--no-install` in
>   `--yes=false`; `libnpmexec/lib/index.js:292-295` si ferma con `npx canceled due to missing packages` quando
>   servirebbe un'installazione; `:298-300`: senza TTY, un `npx` semplice installa e scrive solo un avviso.
> - **Le date di nascita in `~/.npm/_npx`:** vitest 5.0.1 installata il 2026-09-18 alle 12:01; tsx 4.23.15 il
>   2026-09-24 alle 11:58; prettier 3.9.6 il 2026-09-10 alle 20:32. Il lock ha vitest 4.1.11 e prettier 3.8.3.
> - **La mia lane:** le 29 esecuzioni `npx` del round 4 partono tutte da `frontend/`, quindi hanno usato il binario
>   locale. Nei round 1–2, tre `npx prettier --check` di sub-agent erano partiti dalla radice del worktree e avevano
>   usato il prettier 3.9.6 della cache; i controlli successivi, con il prettier del lock, li hanno superati.
> - **Esito:** il coordinator ha mandato a tutte le lane un messaggio definitivo e ha corretto istruzioni e skill (non
>   sono file miei). La regola nuova sulle correzioni: vanno mandate con la stessa modalità di consegna, oppure devono
>   dire che valgono «anche se il vecchio arriva dopo». La mia §5 è stata corretta alle 13:02, ed è nel commit
>   `cb7ae3476`.

> **S8 — la domanda del coordinator delle 12:25, in sola lettura:** S8 **legge soltanto** il motore.
> - Il dato è `AcquisitionFundingContribution` (`from_new_capital`, `from_reinvested`; `portfolio_engine.py:497-508`
>   quel giorno), esposto dallo schema `AcquisitionFundingPoint` (`schemas/portfolio.py:686-687`) e già consumato da
>   GrowthChart. Nessuna modifica a backend, schema o API. Nessuna delle slice che restano (S7, S7b, S8, S10, S11)
>   modifica il motore.
> - Risk aggiunge 2 righe di import al motore nel tempo ②: prima di S8 rimisuro **per simbolo**, non per riga.
> - Nel controllo ho trovato due puntatori a riga stantii nel codice:
>   - `AllocationHistoryChart.svelte` (oggi `:124`) cita `portfolio_engine.py:1041` per il bucket sintetico
>     «Liquidity». Alla nascita (`420b90ebd`) puntava all'iniezione giusta: `:1040` il tipo, `:1041` (la riga citata)
>     il settore. Il commento è nato sul ramo di Risk, parallelo al mio. Poi il merge di Risk `7fd660846` ha portato i
>     miei commit del round 3 `8ed7a0f0d` e `d5e834de4`, che sopra quel punto aggiungono 213 righe e ne tolgono 17: 196
>     di scarto, senza toccare il commento. L'iniezione oggi è a `:1236-1237`. Lo riscrive il commit d'integrazione di
>     D15, che tocca quel commento;
>   - `asset_sources/price_store.py:206` cita `portfolio_engine.py:2182` per `_compute_price_fingerprint`: era
>     sbagliato già alla nascita (`3c85866dd`, dove la funzione stava a `:2225`). Oggi sta a `:2550`. Non è mio: l'ho
>     solo segnalato.
> - Il rimedio è citare il simbolo e non la riga. Tutti gli altri puntatori a riga verso il motore stanno nel journal
>   (nel devWiki nessuno), dove sono misure datate, cioè storia.

> **E7 — confermato da K (12:48), e la coda che nasconde:** K l'ha trovato da solo con test-triage: stesso messaggio,
> stesso range `2026-08-10..2026-09-24`. È l'E7 già registrato in S3 e nella riga S10. Misurato in più:
> - il test va da `:486` a `:7795` e si ferma a `:7636`: l'`await` della promessa creata a `:7612`, mentre il guard
>   lancia a `:1972`;
> - **61 `expect(` e 3 `expect.poll(` fra `:7636` e `:7795` non girano in nessuna lane dal 2026-09-18**: la parte
>   finale del FX-sync standalone su MAX e la sezione MAX corta da 6 giorni. Gli 8 `expect(` fra `:7612` e `:7635`
>   girano ancora. Quando E7 sarà corretto, quella coda girerà per la prima volta dopo una settimana di modifiche di più
>   lane ad Asset detail: un rosso che ne esce va attribuito, non è per forza E7 né mio;
> - **nessuna seconda bomba a orologeria**: tutti gli altri range del test sono letterali assoluti (`:804-866`).
>   L'unica finestra relativa a oggi è MAX (`resolvedMaxSpanDays = 45`, `:7201-7202`);
> - **il rimedio scritto in S3 era impreciso.** Derivare da `end` la fixture condivisa `successorReadyEvents` (`:769`)
>   porterebbe gli eventi fuori dai range assoluti che leggono il mock condiviso (`:2157`, `:2165`) e sezioni dello
>   stesso test che oggi girano verdi (`:6088`, `:6241`). Il punto fragile è più stretto: il guard (`:1970`) cerca
>   nella fixture fissa una data dentro il range MAX accettato. Da quella data dipendono la data di mezzo
>   (`:1974-1978`: la data dell'evento, oppure `start + 1` se coincide con un estremo) e la risposta sintetica, che già
>   sposta prezzi ed eventi dentro il range (`:2145-2150`, `:2159-2164`). Candidato: ricavare quella data dal range
>   accettato stesso, **solo per MAX**. Da progettare in S10 con test-author;
> - lo spec è condiviso: prima dell'edit lo annuncio al coordinator, che l'ha chiesto di nuovo alle 14:18.

> **Residui di Git, non miei:** `git count-objects -v` segnala la cartella vuota
> `.git/worktrees/e-alfy-crispy-pancake/refs` (2026-09-10) e `.git/objects/pack/tmp_pack_liULRD` (2026-09-17).
> Allo script non danno fastidio. Il coordinator li ha girati al developer.

### G — Gallery: Abs esplicito prima dello scatto `main` ✅ 2026-09-24

> **Perché:** con S5, GrowthChart ricorda l'ultimo modo per utente (`dashboard-growth-mode`). Il test della gallery
> «main dashboard - all languages and themes» gira le 8 combinazioni di lingua e tema nella stessa pagina, e a ogni giro
> clicca % per lo scatto `main-pct`. Dal secondo giro in poi, quindi, lo scatto `main` sarebbe uscito in %. Per
> l'opzione (B) il hunk è un commit a sé dopo C1, e il mio ramo entra nel target solo con questo hunk.
>
> **Note implementazione:**
> - Scritto da test-author, che ha toccato solo `frontend/e2e/gallery.spec.ts`: un hunk, +9/−1. Prima dello scatto
>   `main` clicca `growth-toggle-eur`, aspetta `aria-pressed="true"` e lascia 500 ms di ridisegno, come fa già il
>   toggle % subito sotto. Un commento dice perché. Se il modo è già Abs, il clic non cambia niente.
> - La guardia `isVisible(...).catch(() => false)` è quella che il file usa già per `kpiRow`, `growthChart` e
>   `pctToggle`.
> - Le verifiche sono solo statiche, perché la gallery non si lancia da questo ramo (vedi il Fuori pista
>   dell'opzione (A) in «Checkpoint C1»):
>
> | verifica | comando (da `frontend/`) | esito |
> |---|---|---|
> | prettier 3.8.3, quella del lock | `node_modules/.bin/prettier --check e2e/gallery.spec.ts` | pulito, prima e dopo il hunk |
> | svelte-check (il `tsconfig` include `e2e/**/*`) | `node_modules/.bin/svelte-check --tsconfig ./tsconfig.json --output machine` | 3 errori, 41 warning, 4 file: le stesse diagnostiche del confine 8 di C1, per tipo, file e messaggio; nessuna in `gallery.spec.ts` |
> | spazi | `git diff --check` | pulito |
>
> - **Consegna:** checkpoint C2, fatto di due commit: prima la gallery, poi questo registro. L'evidenza del bundle va
>   nel registro dopo il commit, come per C1.

> **⚠️ Fuori pista (rischio residuo, segnalato da test-author):** `locator.isVisible()` ignora l'opzione `timeout` e
> guarda solo l'istante. La guardia nuova salta quindi solo quando salta anche quella di `growth-chart` subito sopra,
> cioè se il grafico non è ancora disegnato. In quel caso `main` può ancora uscire in %, senza errore: è la stessa
> debolezza del toggle % che c'era già. La versione rigida (`expect(eurToggle).toBeVisible()` senza `if`) andrebbe
> contro lo stile del file, e irrobustire va fatto per tutte le guardie insieme. Resta fuori dal round: lo segnalo
> nell'handoff di S12.

### Checkpoint C2 — committato ✅ 2026-09-24 14:51

> **Note implementazione:**
> - **Contenuto:** 2 commit su `804bc9903`: il hunk della gallery (riga G), poi il registro di C1 in questo file. Come
>   per C1, il bundle è stato costruito in `/tmp/libreFolio_i_c2_commits/` senza scrivere nel repository:
>   - le 2 patch, prodotte da un indice e da un object store temporanei: `01-gallery.patch` (+9/−1) e
>     `02-journal.patch` (+183/−7);
>   - lo script `run_commits.sh`, derivato da quello di C1 da un generatore che asserisce quante volte scatta ogni
>     sostituzione. Fra i due script cambiano 100 righe, solo tabelle e conteggi. Il controllo sui residui di C1
>     esclude i subject, perché quello del registro nomina C1 di proposito.
> - **Le guardie** sono quelle di C1 (registro «C1 committato»), con i 2 percorsi e i 3 alberi di C2.
>
> | verifica | come | esito |
> |---|---|---|
> | A — patch semplici | `git apply` in sequenza su copie di HEAD, fuori da ogni repository; poi `cmp` con l'albero di lavoro | 2/2 identici, nessun file in più |
> | B — patch in stage | `git apply --cached` in un indice temporaneo, `write-tree` dopo ogni patch | alberi 0 `f5757935` = HEAD, 1 `9d040f30`, 2 `a580198b` = l'albero di lavoro messo in stage con `add -A` |
> | digest del contenuto | come in C1 | `9b095bf2…c107`, identico con git 2.55 e 2.54 |
> | dry-run sul repository reale | `run_commits.sh --dry-run` | rc 0 in 7 prove su 7 (bash 3.2 e 5.3; git 2.55, 2.54 e 2.53; tre in `env -i`), più una dalla copia di backup. Indice, HEAD, refs, oggetti e worktree invariati |
> | commit veri, in 3 cloni usa-e-getta | come in C1: git 2.55 con bash 3.2, git 2.53 con bash 5.3, git 2.54 in `env -i` | 9/9 PASS in ognuno: 2 commit lineari, clone pulito; le guardie scattano (file manomesso, path in più, path in stage; argomento sconosciuto → rc 2); il secondo lancio è rifiutato e restano 2 commit |
> | messaggi | `awk 'length > 72'` e un controllo in Python | subject di 49 e 48 caratteri, nessuna riga oltre 72, niente attribuzioni AI, nessun dato del developer. Scansione privacy delle righe aggiunte: 0 |
>
> - sha256: script `4582f48b…5cac`; patch `8cc9c4bf…61fd` e `985baeec…8071`; messaggi `45ca7964…5776` e
>   `7ae17312…bd8d`. Backup di 61 file nella cartella di sessione di I.
> - **Il coordinator ha rifatto le verifiche da sé** (14:45): sha256 dello script, HEAD `804bc9903`, i 2 percorsi,
>   stage vuoto, subject e colonne, e il dry-run (rc 0, alberi attesi, stato invariato).
> - **Il developer ha committato alle 14:51.** La mia verifica dopo il commit, in sola lettura: ogni albero è quello
>   atteso, ogni messaggio è identico byte per byte al suo file, ogni commit ha un solo genitore; `git status` e stage
>   vuoti. Il vincolo d'integrazione dell'opzione (B) è soddisfatto: il hunk della gallery è nel ramo.
>
> | # | commit | subject | albero |
> |---|---|---|---|
> | 1 | `980dee4bf` | `fix(e2e): select Abs before the main gallery shot` | `9d040f3019f0` |
> | 2 | `6a88561fd` | `docs(journal): record C1 commits and gallery fix` | `a580198baca5` |
>
> Il bundle resta in `/tmp/libreFolio_i_c2_commits/`, con una copia nella cartella di sessione di I: non è versionato,
> e si cancella in S12.

> **⚠️ Fuori pista (messaggio 02 corretto prima della consegna):** il corpo diceva che i puntatori a riga dei due
> commenti verso il motore «no longer point at their target». Per `price_store.py` non è vero: era sbagliato già alla
> nascita (registro «C1 committato», voce S8). Il testo nuovo dice «miss their target». Dopo la correzione ho
> aggiornato gli hash nello script e rifatto tutte le verifiche della tabella.

> **⚠️ Fuori pista (finché C2 non era committato, il worktree era fermo):** le guardie 6 e 7 dello script confrontano
> i percorsi esatti e il digest del contenuto. Qualunque scrittura nel worktree, anche una nota di questo registro,
> avrebbe fatto fallire il comando del developer (senza danni: lo script si ferma prima di committare). Per questo il
> registro di C2 e i file di S11 li ho scritti solo dopo il segnale del coordinator; prima, per S11, solo letture.

### Triage del contratto di `/portfolio/report` — attribuito, va in S10 (2026-09-24)

> **Note implementazione:**
> - **Il rosso**, segnalato dal coordinator: `backend/test_scripts/test_api/test_portfolio_api.py::TestPortfolioReportEndpoint::test_report_allocation_source_authenticated_contract`.
>   L'asserzione di `:767` chiede `set(report) == {7 chiavi}`.
> - **Riprodotto su `6a88561fd`**, nella lane, con un solo test:
>   `PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py test --test-port 6157 --data-dir /tmp/librefolio-r2-i-charts api portfolio test_report_allocation_source_authenticated_contract`
>   → 1 fallito, 48 deselezionati, `Extra items in the left set: 'cost_history', 'deposit_history', 'broker_pnl_history',
>   'pnl_candles', 'acquisition_funding'…`. Log completo in `/tmp/libreFolio_i_s10/report_contract_red.log`. Porta 6157
>   libera dopo il comando.
>
> | domanda | come | risposta |
> |---|---|---|
> | chi ha scritto il pin | `git log -S` sul test | il PAC: `8273335ff` (11/09) e `8504f0528` (12/09) |
> | chi ha aggiunto le 6 chiavi | `git log -S "<campo>:"` su `schemas/portfolio.py` | io. `8ed7a0f0d` (18/09, G1a/G1b/G1c) per `broker_pnl_history`, `pnl_candles` e `income_history`; `d5e834de4` (18/09, batch 2) per `cost_history`, `deposit_history` e `acquisition_funding` |
> | dove si sono incontrati | `merge-base --is-ancestor`, poi il primo commit, in ordine topologico, che li contiene tutti e due | il mio merge `b7a0b1e1a` (21/09, 15:57), senza conflitto testuale: il primo genitore ha i campi e non il test, il secondo ha il test e non i campi |
> | cosa ho fatto in quel merge | `git show` dei due genitori e del merge | ho allargato a 13 il gemello di servizio (`test_portfolio_service.py:3767`, §6.0.9 del piano principale). Questo no |
> | è cambiato qualcosa dopo | `git diff b7a0b1e1a HEAD --stat` su test, schema e servizio | niente: il rosso è quello nato nel merge |
> | le 6 chiavi sono vuote | lettura del ramo senza motore (`portfolio_service.py:2404-2421`), che costruisce la risposta solo con `metadata` e `allocation_source` | sì, sono `None` per default. FastAPI le serializza come `null`, quindi entrano in `set(report)` |
> | la coda | conteggio fino alla fine della funzione (`:926`) | 60 `assert` da `:767`: i 59 dopo il primo non girano dal 21/09. Gli insiemi annidati (source 5, asset 11, quote 6, context 8, le due fonti di cassa 7) sono identici a quelli del gemello di servizio. Quindi reggono sulla carta, ma i valori non li ho provati |
>
> **Verdetto: assumption.** È un pin a mondo chiuso scaduto dopo un'estensione voluta del contratto. Il prodotto è giusto:
> le 6 sezioni sono documentate («Only when include_X=True»), e a flag spenti valgono `null`. Si corregge il test in S10,
> via test-author, dopo l'OK sulla test list (riga S10 di §4).

> **⚠️ Fuori pista (la lezione di §6.0.9 applicata a metà):** nel merge ho trovato e allargato il gemello di servizio, ma
> non ho cercato gli altri pin dello stesso insieme. Il gate combinato di quel merge (507/507 backend) non poteva
> comprendere `api portfolio`, perché su quell'albero questo test è rosso per costruzione. Bastava una riga:
> `git grep -n '"positions_contribution",' -- backend/test_scripts`. Sull'albero del merge dà 3 risultati: il gemello,
> il pin di `included_features` (`test_portfolio_service.py:2064`, corretto) e questo test.
> **Regola per i merge futuri:** quando un merge allarga un pin a mondo chiuso, cerco ogni altro pin dello stesso
> insieme prima di chiudere il gate.

> **Reperto (difetto latente, nato nello stesso incontro):** `needs_engine` (`portfolio_service.py:2404`, nato in
> `8273335ff`) elenca solo le 4 viste originali; le mie 6 non ci sono.
> - **Il sintomo:** una richiesta con `allocation_source` e, per esempio, `include_income_history: true`, senza le altre 4
>   viste, prende il ramo senza motore. `income_history` torna `null` e `included_features` vale `["allocation_source"]`:
>   la richiesta è ignorata in silenzio.
> - **Oggi non è raggiungibile dall'interfaccia.** Lo store (`portfolioStore.svelte.ts:274`) manda sempre
>   `include_summary: true`, e il PAC (`allocationSource.ts:190-195`) non chiede nessuna delle 6. Nessun chiamante
>   interno del backend passa `allocation_source`. Ci arriva solo un client diretto dell'API.
> - **Correzione proposta**, una riga, da autorizzare perché il file è condiviso: aggiungere i 6 flag a `needs_engine`,
>   con il test API proposto in §4. In alternativa, le 3 serie che non usano il motore (income, cost, deposit) si
>   potrebbero servire anche nel ramo corto. Decidono il coordinator e il developer.
>
> ⏭️ **Deciso dal coordinator (2026-09-24 15:24):**
> - il verdetto «assumption» è accettato. In S10, via test-author: da 7 a 13 chiavi esatte, più `is None` per le 6
>   sezioni. I 59 `assert` che si risvegliano li attribuisco prima di correggerli;
> - la regola sui pin gemelli nei merge il coordinator la aggiunge alle note per chi integra;
> - `needs_engine` è mio, in S10. È un difetto dell'API anche se l'interfaccia non ci arriva: i 6 flag li ho introdotti
>   io, e il ramo corto li ignora. Correzione: i 6 flag in `needs_engine`, più un test API che fallisce prima della
>   correzione, in un commit a sé. L'alternativa (le 3 serie senza motore servite nel ramo corto) non si fa;
> - nessun conflitto con Risk: `a766a9d5d` tocca `portfolio_service.py` solo a `:694-695` (un import), lontano da
>   `:2404`.
>
> Letto dopo la decisione: la chiave della cache L2 contiene già i 6 flag (`:2375-2380`). Un report del ramo corto in
> cache risponde quindi solo alla stessa richiesta, e la correzione resta una sola istruzione.

### S11 in parte — docs del comportamento consegnato ✅ 2026-09-24

> **Note implementazione:**
> - **Chi e cosa:** scritte da docs-writer, solo EN, su due pagine; io ho rivisto ogni frase contro il codice di
>   `6a88561fd`. Il perimetro è quello autorizzato dal coordinator (14:45, più `positions.en.md` dopo): solo il
>   comportamento già consegnato. Nessun titolo nuovo, e titoli e ancore sono invariati.
> - **`mkdocs_src/docs/user/dashboard/charts.en.md`** (+23/−5):
>   - un paragrafo sulla memoria della vista di Crescita (modo e sottomodo; per utente e per browser; condivisa con il
>     dettaglio broker; default Abs e Linea);
>   - uno sul ripiego del `%` ripristinato senza dati;
>   - un tip «Hiding the amounts»: assi `•••`/`-•••` con k/M nella maschera, tooltip con valuta e segno, `%` non
>     mascherato, ridisegno dal vivo nei due versi, colori invariati, preferenza del browser e non dell'account;
>   - la didascalia delle candele citata alla lettera, una riga che scorre, ferma con movimento ridotto; tolta la frase
>     sulla nota nel tooltip, che non c'è più;
>   - le candele disegnano solo il totale; il tooltip elenca i broker alla chiusura del periodo, se sono almeno 2. La
>     frase vecchia sull'overlay tratteggiato era falsa dal 21/09;
>   - un paragrafo sulla memoria di Allocazione (Now/History e dimensione; History ripristinato carica i dati).
> - **`mkdocs_src/docs/user/dashboard/positions.en.md`** (+4): un tip «Hiding the amounts» in «📈 Performance View»
>   (etichetta netta `+€•••` o `+••• CHF`, tacche e zero `•••`, tooltip con segno e valuta, percentuali visibili,
>   barre con lunghezza e colori veri, etichette verdi o rosse).
> - **Nessuno stamp:** le pagine it/fr/es restano indietro, e il debito si vede. Oltre a quello che avevano già,
>   ora mancano i paragrafi nuovi di `charts` (introduzione di Crescita, tip, candele, Now/History) e il tip di
>   `positions`.
>
> | verifica | comando | esito |
> |---|---|---|
> | build strict | `PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py mkdocs build` (log `/tmp/libreFolio_i_s11/build3.log`) | passa in 22.84 s: nessun WARNING o ERROR, a parte il banner del team Material |
> | link | `… dev.py mkdocs check-links` (log `check_links3.log`) | 80 validi, le 3 eccezioni di ancora note (pagine assets), 9 risolti a runtime. Nessuno riguarda le due pagine |
> | asset copiati dalla build | `git status --porcelain=v1` | favicon e icone PWA rigenerate identiche: stato invariato, come prevedeva la prova in `/tmp` (probe `copy_docs_assets`) |
> | stato | `git status --porcelain=v1` | solo questo piano e le due pagine |
> | spazi | `git diff --check` | pulito |

> **⚠️ Fuori pista (il brief aveva tre imprecisioni, corrette in revisione):**
> - «il `%` torna da solo quando la storia ha i dati» era vero a metà. Il controllo del ripiego gira **una volta per
>   montaggio** (`restoredPctUnchecked`, `GrowthChart.svelte:111` e `:690-694`), quindi il `%` torna al montaggio
>   successivo. La pagina ora dice così. Anche il commento del codice (`:687-689`, «comes back once the history can
>   draw it») è impreciso: lo correggo in S7, che tocca già il file.
> - L'esempio `EUR -•••` vale solo per le righe senza segno proprio. Le righe con segno (P&L totale, broker,
>   proventi) si leggono `+EUR •••`. La pagina enuncia la regola senza un esempio letterale.
> - «nasconde gli importi in tutta l'app» era un'affermazione non verificata: è il contratto dichiarato di
>   `PrivacyToggle.svelte:3`, non una proprietà misurata. La pagina promette solo quello che verifica.
>
> In più, in revisione ho aggiunto una cosa che il brief non diceva: nel tooltip Abs, **Asset Cost**, **Returns** e
> **Capital** mostrano `—` quando valgono zero, mascherati o no (`fmtOrDash`, `:1959`). È la divulgazione accettata
> in D8, quindi va scritta.

> **⚠️ Fuori pista (un mio puntatore sbagliato):** per «le barre tengono il loro colore» avevo dato `PerformanceChart.svelte:827`,
> ripreso dal primo rapporto di docs-writer. Ma `:827` è il colore dell'**etichetta netta**
> (`signValueColor(row.net)`). Le barre sono colorate per **componente** (`:690`, `:725`, `:743-760`), non per
> guadagno o perdita. docs-writer se n'è accorto e ha scritto la frase giusta: lunghezza e colori veri, etichette
> verdi o rosse.

> **Reperti per S11-finale e S12:**
> - **Deriva di nomi, preesistente, per S11-finale:** «Tooltip breakdown» dice **Asset Cost** e **NAV**; l'interfaccia
>   dice «Assets at Cost» (`dashboard.assetsAtCostTooltip`) e «Net Asset Value».
> - **Possibile difetto, preesistente, solo da lettura del codice, per S12:** se sono già sul `%` e cambio periodo verso
>   uno senza dati `%`, il bottone resta premuto ma disabilitato, e il grafico è probabilmente vuoto. Il
>   `disabled={!hasPctData}` c'è da `c9013c496` (2026-06-11); il ripiego di S4 copre solo il `%` ripristinato. Va
>   verificato dal vivo prima di chiamarlo difetto.
> - **Per J, via coordinator:** le etichette di `PrivacyToggle` sono in inglese fisso («Hide amounts» / «Show
>   amounts», `:13`), senza i18n. Le docs EN le citano.
>
> ⏭️ **Accettato dal coordinator (2026-09-24 15:24):** le tre correzioni del brief e gli zeri come `—` (D8). Il reperto
> su `PrivacyToggle` viene da `b66e93003` di J, e il coordinator lo ha girato a J (§9). Le due pagine entrano in C3,
> con i registri.

### Checkpoint C3 — autorizzato (2026-09-24 15:24)

> **Note implementazione:**
> - **Contenuto:** 2 commit su `6a88561fd`. Prima le docs di S11 in parte (`charts.en.md` e `positions.en.md`), poi
>   questo file, con i registri di C2, del triage e di S11 e le decisioni delle 15:24.
> - **Come:** lo stesso protocollo di C1 e C2 (registri «C1 committato» e «C2 committato»). Patch e script si
>   costruiscono in `/tmp/libreFolio_i_c3_commits/` senza scrivere nel repository; lo script deriva da quello di C2
>   con sostituzioni contate; le verifiche sono le stesse (A, B, digest, dry-run, 3 cloni, messaggi).
> - **Questa è l'ultima scrittura nel worktree prima del digest.** I numeri del bundle (alberi, sha256, digest)
>   dipendono da questo file, quindi qui non ci sono: li registro dopo il commit, come per C2.

### Checkpoint C3 — committato ✅ 2026-09-24 15:39

> **Note implementazione:**
> - **Contenuto:** 2 commit su `6a88561fd`: le docs di S11 in parte, poi questo file con i registri di C2, del triage
>   e di S11 e le decisioni delle 15:24. Come per C1 e C2, il bundle è stato costruito in
>   `/tmp/libreFolio_i_c3_commits/` senza scrivere nel repository:
>   - le 2 patch, prodotte da un indice e da un object store temporanei: `01-docs.patch` (2 file, +27/−5) e
>     `02-journal.patch` (+203/−8);
>   - lo script `run_commits.sh`, derivato da quello di C2 dallo stesso generatore a sostituzioni contate. Fra i due
>     script cambiano 33 righe: tabelle, base, digest e i 3 percorsi. Anche gli script di verifica sono derivati
>     così: fra 8 e 22 righe di diff ciascuno.
> - **Le guardie** sono quelle di C1 e C2 (registro «C1 committato»), con HEAD `6a88561fd`, i 3 percorsi e i 3 alberi
>   di C3.
>
> | verifica | come | esito |
> |---|---|---|
> | A — patch semplici | `git apply` in sequenza su copie di HEAD, fuori da ogni repository; poi `cmp` con l'albero di lavoro | 3/3 identici, nessun file in più |
> | B — patch in stage | `git apply --cached` in un indice temporaneo, `write-tree` dopo ogni patch | alberi 0 `a580198b` = HEAD, 1 `3e852060`, 2 `f3c114b4` = l'albero di lavoro messo in stage con `add -A` |
> | digest del contenuto | come in C1 | `7f4f2149…18bb`, identico con git 2.55 e 2.54 |
> | dry-run sul repository reale | `run_commits.sh --dry-run` | rc 0 in 7 prove su 7 (bash 3.2 e 5.3; git 2.55, 2.54 e 2.53; tre in `env -i`), più una dalla copia di backup. Indice, HEAD, refs, oggetti e worktree invariati in tutte le 8 istantanee, prese prima e dopo ogni fase del bundle |
> | commit veri, in 3 cloni usa-e-getta | come in C1 e C2: git 2.55 con bash 3.2, git 2.53 con bash 5.3, git 2.54 in `env -i` | 9/9 PASS in ognuno: 2 commit lineari, clone pulito; le guardie scattano (file manomesso, path in più, path in stage; argomento sconosciuto → rc 2); il secondo lancio è rifiutato e restano 2 commit |
> | messaggi | `check_messages.py` | subject di 50 e 47 caratteri, righe al massimo di 69 e 68 colonne, solo ASCII, niente attribuzioni AI, nessun dato del developer. Scansione privacy delle righe aggiunte: 0 nelle docs; 2 nel registro, tutte e due falsi positivi (la parola «backup») |
> | docs | build strict e check-links (registro «S11 in parte») | lanciati dopo l'ultima modifica delle docs (15:19:51): build alle 15:20:29, link alle 15:20:44 |
>
> - sha256: script `d7475a3b…f6cb`; patch `ca5e8f61…e405` e `eef2744c…7bbb`; messaggi `ed450357…5620` e
>   `801e119f…1e1d`. Backup di 57 file nella cartella di sessione di I, identico al bundle file per file
>   (ricontrollato dopo il commit).
> - **Il coordinator ha rifatto le verifiche da sé** (15:37): sha256 dello script, HEAD `6a88561fd`, i 3 percorsi,
>   stage vuoto, subject e colonne, nessuna attribuzione AI e nessun importo, e il dry-run (rc 0, stato invariato).
> - **Il developer ha committato alle 15:39.** La mia verifica dopo il commit, in sola lettura:
>   - ogni albero è quello atteso, e ogni messaggio è identico byte per byte al suo file;
>   - ogni patch è identica byte per byte al diff fra il commit e il suo genitore
>     (`git diff-tree -p --binary --full-index`);
>   - ogni commit ha un solo genitore, e nessuna operazione è in corso;
>   - `git status` e stage vuoti; porte 6157 e 6167 libere.
>
> | # | commit | subject | albero |
> |---|---|---|---|
> | 1 | `671d4ab49` | `docs(dashboard): document chart memory and privacy` | `3e8520609e0f` |
> | 2 | `4d885f1e8` | `docs(journal): record C2, S11 and report triage` | `f3c114b4d481` |
>
> - **Rispetto al target**, rifatto su `4d885f1e8`: `dev_release2` è ancora `2a23b7ad3`. `git merge-tree --write-tree`
>   fra il ramo e il target, con un object store temporaneo: rc 0, nessun conflitto. Dal merge-base `f1047f766` il
>   ramo tocca 18 percorsi e il target 4, nessuno in comune.
> - Il bundle resta in `/tmp/libreFolio_i_c3_commits/`, con la copia nella cartella di sessione di I: non è
>   versionato, e si cancella in S12.

> **⚠️ Fuori pista (un nome riservato nel builder):** nella prima stesura di `build_patches.sh` i percorsi di ogni
> commit stavano in un array `GROUPS`. Bash riserva quel nome ai gruppi dell'utente: con bash 3.2 l'assegnamento fa
> uscire lo script con rc 1, senza messaggio; con bash 5.3 non ha effetto, e l'array tiene i numeri dei gruppi.
> Riprovato dopo il commit, su tutte e due. L'ho rinominato `COMMIT_PATHS`, con un commento che lo ricorda
> (`build_patches.sh:13`). Tutte le prove della tabella sono state fatte sulle patch del builder corretto.

> **⚠️ Fuori pista (come per C2, fino al commit il worktree era fermo):** le guardie 6 e 7 dello script confrontano i
> percorsi esatti e il digest del contenuto. Questo registro l'ho scritto solo dopo il segnale del coordinator
> (15:40); prima, solo letture.

> ⏭️ **Dopo C3** (coordinator, 15:37 e 15:40): aspetto il developer, cioè D4, D16, D17 e D18 (S7, S7b, S8) e l'OK
> sulla test list (S10). Quando arriva l'OK, `needs_engine` va **per primo**, in un commit a sé: prima il test rosso,
> poi la correzione, poi il verde. È la parte più piccola di S10 e la meno legata alle altre slice.

### S11-finale — voci aggiunte (2026-09-24 16:07)

> **Note implementazione** (solo letture su `4d885f1e8`; nessun edit alle docs, che restano per S11-finale via
> docs-writer):
> - **`mkdocs_src/docs/user/dashboard/index.en.md:13-17`** (reperto di J, girato dal coordinator alle 16:07; nessun
>   altro worktree tocca il file, quindi la correzione è mia). La pagina dice «three primary tabs» ed elenca Overview,
>   Positions & Analysis e Transactions. Le schede sono quattro:
>   - `DASHBOARD_TAB_IDS = ['panoramica', 'posizioni', 'rischio', 'transazioni']` (`+page.svelte:232`), con etichette
>     Overview, Positions, **Risk** (`risk.title`) e Transactions (`:241-246`);
>   - manca Risk, che c'è da `16ff0eb57` (2026-07-28): la deriva è preesistente;
>   - la scheda Risk mostra `RiskLevelsPanel` sull'intero portafoglio anche con un filtro broker attivo, e in quel
>     caso compare il sottotitolo `risk.dashboardFullPortfolio` (`:813-833`, sottotitolo a `:827`);
>   - nella mia base non c'è nessuna pagina utente sul rischio (`git ls-files 'mkdocs_src/docs/user/**/*risk*'` è
>     vuoto). L'ho chiesto al coordinator: la risposta è nel ⏭️ in fondo a questo registro;
>   - anche «In this section», in fondo alla pagina, non nomina Risk. E la voce Transactions non ha link, mentre la
>     scheda è descritta in `positions.en.md:161` («💸 Transactions Tab»).
> - **La deriva dei nomi**, già in lista (registro «S11 in parte»), ora con i puntatori esatti. L'interfaccia usa due
>   nomi per la stessa area, uno nella legenda e uno nel tooltip (`GrowthChart.svelte:518-526`):
>
> | dove, in `charts.en.md` | cosa dice | cosa dice l'interfaccia |
> |---|---|---|
> | `:42`, tabella della legenda | Area — **Asset Cost** | «Purchase Cost» (`dashboard.assetsAtCost`, nome della serie a `:1342` e `:1402`) |
> | `:45`, tabella della legenda | Line — **NAV** | «Net Asset Value» (`dashboard.navValue`, `:1345` e `:1437`) |
> | `:54`, «Tooltip breakdown» | **NAV** | «Net Asset Value» (`:1961`) |
> | `:57`, «Tooltip breakdown» | **Asset Cost** / **Returns** / **Capital** — «the three cash components» | «Assets at Cost» (`dashboard.assetsAtCostTooltip`, `:1969`); «Returns» e «Capital» sono giusti (`:1970-1971`). Da verificare anche «cash»: secondo la tabella della stessa pagina (`:42-44`) la prima riga è il costo delle posizioni, non cassa |
> | `:29`, il tip privacy (C3, mio) | **Asset Cost**, **Returns**, and **Capital** show `—` | «Assets at Cost» (`:1969`) |
> | `:61`, `:63`, il tip sui portafogli a reddito | «NAV ≈ Asset Cost», «the Asset Cost area» | prosa: decide docs-writer se allinearla alla legenda |

> **⚠️ Fuori pista (la deriva l'ho ripetuta io, in C3):** la frase del tip privacy entrata in `671d4ab49`
> (`charts.en.md:29`) chiama **Asset Cost** la prima riga del tooltip Abs, che nell'interfaccia si chiama «Assets at
> Cost» (`GrowthChart.svelte:1969`). Avevo segnalato la deriva come preesistente, e intanto la frase nuova la
> ripeteva: in revisione ho controllato il comportamento (`fmtOrDash`, `:1959`), non l'etichetta. Si corregge in
> S11-finale con le altre. Regola per la revisione delle docs: ogni nome in grassetto va confrontato con la sua
> chiave i18n, non solo con la pagina che lo usa già.

> ⏭️ **Deciso dal coordinator (2026-09-24 16:13):**
> - **La pagina utente per la scheda Rischio non esiste, e nessuno la sta scrivendo.** Non è in nessun ramo, Risk non
>   ha docs modificate, e il suo piano non la prevede: l'icona docs di Risk punta alle pagine di teoria, una per
>   metrica. Il coordinator mette la pagina mancante nel backlog.
> - **Quindi in S11-finale la voce di Risk è testo semplice**, con la riga ricavata dal codice. `index.en.md` resta
>   mio. Se serve un rimando, c'è l'indice di teoria
>   `mkdocs_src/docs/financial-theory/technical-analysis/risk-metrics/index.en.md`: è nella mia base, con le 3
>   traduzioni, e da `user/dashboard/` il link è `../../financial-theory/technical-analysis/risk-metrics/index.md`,
>   come i rimandi di «Related theory» della stessa pagina.
> - **«Asset Cost» contro «Assets at Cost»** si corregge in S11-finale con le altre righe. La regola del confronto con
>   la chiave i18n è accettata.

### Pausa e ripresa dopo il riavvio (2026-09-24 18:35 → 2026-09-25 09:09)

> **Note implementazione:**
> - **Pausa** (24/09, 18:35), chiesta dal developer tramite il coordinator. Stato mandato: HEAD `4d885f1e8`, modificato
>   solo questo piano (+122/−12), stage vuoto, porte 6157 e 6167 libere. Nessun comando fino alla ripresa.
> - **Ripresa** (25/09, 09:09). Durante la pausa il Mac si è riavviato, e `/tmp` è stato svuotato:
>   - sono sparite le due lane (`/tmp/librefolio-r2-i-charts` e `/tmp/librefolio-r2-i-charts-prodcopy`), i bundle
>     `/tmp/libreFolio_i_c1_commits/`, `…_c2_…` e `…_c3_…`, e le cartelle di scarto `/tmp/libreFolio_i_s6_shots/`,
>     `…_s10/` e `…_s11/`. Restano 12 script sciolti `/tmp/libreFolio_i_*.py`, da cancellare in S12;
>   - i log citati nei registri precedenti non esistono più. I numeri scritti restano quelli misurati allora; se serve
>     una prova, si rigenera;
>   - i backup dei bundle nella cartella di sessione di I ci sono: C1 204 file, C2 61, C3 57, e `shasum -c` di C3
>     passa. Non servono più per committare, perché C1, C2 e C3 sono nel ramo: restano come prova;
>   - il worktree è intatto: HEAD `4d885f1e8`, stage vuoto, modificato solo questo piano; `frontend/node_modules/.bin`
>     ha ancora vitest e playwright; porte 6157 e 6167 libere.
> - **Il target** è ora `33b7ce564`, 2 commit dopo `2a23b7ad3`: `bbc622952` (istruzioni: mai `npx`, binari del lock;
>   in un worktree nuovo, `npm ci` approvato prima dei test frontend) e `33b7ce564` (journal: le proprietà incrociate
>   del 24/09). Toccano `.github/copilot-instructions.md`, la skill `lint-format-frontend` e
>   `08_review_visiva_20260922.md`, nessuno dei miei 18 percorsi. Dal secondo, due cose mi riguardano:
>   - la voce di `index.en.md` (tre schede invece di quattro) è registrata come mia, in S11-finale;
>   - J (C6) passerà le etichette di `PrivacyToggle` e `ThemeToggle` su chiavi nuove, in 4 lingue. Le docs EN citano
>     «Hide amounts» e «Show amounts» alla lettera: se il testo inglese cambia, in S11-finale le riallineo.
> - **La snapshot** delle 09:05 era sbagliata: copiata intera, con il marcatore di produzione, `logs/` e i file
>   `-shm`/`-wal` (trovato da A). Il coordinator l'ha rifatta alle 09:15 con la procedura del 23/09. Da quella delle
>   09:05 non ho fatto copie e non l'ho aperta; la procedura di §5 si sarebbe fermata sul marcatore. La mia copia serve
>   solo per S7, e userà quella delle 09:15.
> - **Le decisioni del developer.** Il coordinator mi ha chiesto di porgliele con `ask_user`, una alla volta. La prima
>   (D4) ha avuto la risposta automatica «l'utente non è disponibile e rivedrà il lavoro più tardi». Non decido al suo
>   posto: D4, D16, D17, D18 e l'OK alla test list restano aperti, quindi S7, S7b e S10 (compreso `needs_engine`)
>   restano fermi. Le 5 domande, ognuna con la mia raccomandazione e l'effetto per l'utente, le ho mandate al
>   coordinator perché le giri al developer.
> - **Nel frattempo**, solo lavoro fuori dai gate: questo registro, la bozza del brief di S10 per test-author (nella
>   cartella di sessione) e la misura «prima» di S10 nella lane suite, un comando alla volta.

> ⏭️ **Decisioni del developer (2026-09-25).**
> - **D4**, girata dal coordinator, testuale: «sì, approvo quello che sta suggerendo I».
> - Poi il coordinator ha passato la mia sessione in modalità interactive, e le altre le ho chieste io con `ask_user`,
>   una alla volta, ognuna con la mia raccomandazione e l'effetto per l'utente. Il developer ha scelto la
>   raccomandata ogni volta:
>   - **D16** = (ii)+(i): ancorare alla fine e marcare il parziale;
>   - **D17** = (a): 3 colonne, costi sotto lo zero nella colonna dei proventi, gap al 10 %;
>   - **D18** = sì, come S7b, sugli assi del denaro, `%` escluso;
>   - **test list di S10**: «OK alla test list, con E8 ed E9 aggiunti a S10».
> - Registrate in §7, in §4 e nella tabella di stato. S7, S7b e S10 sono sbloccate; S8 segue S7.

> **⚠️ Fuori pista (una risposta automatica letta come l'assenza del developer):** la risposta «l'utente non è
> disponibile e rivedrà il lavoro più tardi» non veniva dal developer. Veniva dalla modalità autopilot della mia
> sessione, che risponde da sé a `ask_user`. L'ha scoperto il coordinator, che mi ha passato in interactive. La mia
> reazione era giusta nel merito: non ho deciso al posto del developer, e ho girato le domande. Ma ho scritto come un
> fatto una cosa dedotta, «il developer non è disponibile». La lezione: una risposta di `ask_user` che non sceglie
> nessuna opzione e non risponde alla domanda va trattata come «nessuna risposta», non come un'informazione
> sull'utente, e va detta così al coordinator.

**Misura «prima» di S10 (lane suite, 2026-09-25, un comando alla volta; log in `/tmp/libreFolio_i_s10/`).** Il DB e
la cartella della lane li ha ricreati il runner al primo comando, come previsto. Stessa HEAD `4d885f1e8`, stesso
codice di prodotto dell'ultima misura del 24/09 (registro S2b).

| # | comando | esito | confronto |
|---|---|---|---|
| 1 | `… dev.py test --test-port 6157 --data-dir /tmp/librefolio-r2-i-charts api portfolio` | 1 fallito su 49 | il solo rosso del contratto di `/report` (`:767`), già attribuito |
| 2 | `… front-portfolio dashboard` | **7 falliti su 15** | il 24/09 erano 5 (E1–E5). **Due nuovi**: `:467` e `:496` → E8 ed E9, sotto |
| 3 | `… front-broker detail` | 1 fallito su 28 | `:710`, cioè E6: come il 24/09 |
| 4 | `… front-asset asset-detail` | 1 fallito su 28 | `:486`, cioè E7, con lo stesso messaggio: la finestra MAX accettata è ora `2026-08-11..2026-09-25` e non contiene gli eventi fissi del peer (`2026-08-01`, `2026-08-03`) |
| 5 | `cd frontend && node_modules/.bin/vitest run src/lib/components/charts/chartCoreHelpers.test.ts --reporter=json` | 11 falliti su 159 | gli 11 della baseline (C1–C12 senza C8, guarito in S9): come il 24/09 |
| 6 | `node_modules/.bin/vitest run …/GrowthChart.test.ts …/privacy/moneyRenderSites.test.ts --reporter=json` | 12/12 | `GrowthChart.test.ts` 6/6, gate 6/6 |

Vitest è quello del lock (4.1.11), chiamato da `node_modules/.bin`, mai con `npx`. Il runner chiama `npx` dentro
(`_frontend_asset.py:59`), ma qui `node_modules/.bin` c'è, quindi npx si ferma al primo passo e usa quello. Dopo ogni
comando la porta 6157 è libera.

**E8 ed E9: triage** (`test-triage`, prima ipotesi: la forma di quello che il test riceve).
- **Cosa hanno ricevuto** (`error-context.md` di Playwright, cioè il DOM al momento del rosso): il tooltip è quello
  di **2026-08-09**.
  - In linea: Total P&L `+EUR 386.03`, Interactive Brokers `+EUR 386.03`, Coinbase `EUR 0.00`.
  - In candele: Open, Close, High e Low `EUR 386.03`, poi Interactive Brokers `+EUR 386.03` e Coinbase `EUR 0.00`.
  - I conti tornano: il totale è la somma dei broker.
- **Cosa contano i test.** `:467` vuole `SIGNED_AMOUNT` = broker + 1 = 3, e ne trova 2. `:496` vuole `PLAIN_AMOUNT`
  = 4, cioè il quartetto OHLC, e ne trova 5. In tutti e due i casi l'intruso è lo stesso: lo **zero di Coinbase**,
  che dal `e7773a143` non ha segno per scelta, come in E5 ed E6. Per `:467` è un importo che manca fra quelli con
  segno; per `:496` è un importo in più fra quelli senza segno.
- **Perché il 24/09 erano verdi.** Il codice è lo stesso. Sono cambiati la data e il DB, che dopo il riavvio è nuovo.
  Il puntatore cade su una data che dipende da tutti e due: il 24/09 cadeva su un giorno in cui Coinbase non valeva
  zero. Quale dei due l'abbia spostato non serve per il rimedio: un test che regge solo se sotto il puntatore non c'è
  uno zero è sbagliato comunque.
- **Verdetto: assumption.** Il conteggio per segno era un modo per dire «c'è una riga per ogni serie». Rimedio in S10
  (§4, aggiunto dal developer): contare le righe con il segno opzionale, come E5/E6, e riconoscere l'OHLC per riga,
  non per assenza di segno.

### S10 passo 1 — `needs_engine` e contratto di `/portfolio/report` ✅ 2026-09-25 10:38

> **Note implementazione:**
> - **Test (test-author, solo file).** Brief nella cartella di sessione (`s10_briefs/01-…`): nessuna lane, solo
>   `ruff` e `black --check`, un solo file toccato, `test_portfolio_api.py` (+102/−0). Due parti separate, a circa
>   630 righe di distanza, così i commit si dividono:
>   - **A**, il test nuovo, ultimo metodo di `TestPortfolioReportEndpoint`:
>     `test_report_allocation_source_with_one_chart_flag_includes_exactly_that_section`, parametrizzato sui 6 flag.
>     Chiede `allocation_source` con **un solo** flag di sezione acceso; gli altri 9 li scrive `False` nel corpo,
>     così «uno solo» lo dice la richiesta e non i default dello schema. Vuole la sezione piena,
>     `included_features == ["allocation_source", <sezione>]` esatto (l'ordine è quello di `:2437-2607`: prima
>     `allocation_source`, poi le sezioni), `allocation_source` pieno e le 4 viste originali `None`. `data_quality`
>     non è fissato, e il test dice perché: il ramo del motore lo costruisce comunque. Utente, broker e dati suoi,
>     finestra fissa nel passato (2025-07), pulizia in `finally` (broker con `force`, poi utente);
>   - **B**, il contratto: `:767` passa da 7 a 13 chiavi esatte (mai `⊇`), più `is None` per ognuna delle 6
>     sezioni. Nient'altro cambia in quel test.
> - **Rosso prima della correzione** (lane suite): `… dev.py test --test-port 6157 --data-dir
>   /tmp/librefolio-r2-i-charts api portfolio with_one_chart_flag` → **6 falliti**, 49 deselezionati. Tutti per la
>   ragione attesa, alla prima asserzione: `include_<flag>=true was ignored: included_features=['allocation_source']`.
> - **Correzione**: `portfolio_service.py:2404`, i 6 flag dentro `needs_engine`. Black la spezza in 10 righe, un
>   operando per riga; sopra, un commento di una riga: ogni flag di sezione va lì, perché il ramo corto restituisce
>   solo `allocation_source`. È la trappola che ha prodotto il difetto: sei sezioni aggiunte, e il ramo corto non le
>   conosceva. `include_breakdown` resta fuori: conta solo dentro `summary`. `black` e `ruff` puliti sul file (black
>   era pulito anche su HEAD). Niente `api sync`: lo schema non cambia.
> - **Verde dopo**: lo stesso comando → 6 passati.
> - **Suite intere dopo la correzione**:
>
> | comando | esito | prima |
> |---|---|---|
> | `… api portfolio` | **55/55** | 1 fallito su 49 (`:767`) |
> | `… services roi-fifo-utils` | 507/507 | — (gemello di servizio `test_portfolio_service.py:3767` e ramo corto a livello di servizio) |
>
>   Il contratto di `:767` è verde, e la sua coda di 59 `assert`, ferma dal 21/09, ha girato per la prima volta:
>   **nessun rosso** da attribuire. 49 + 6 = 55.
> - **Effetto sull'interfaccia: nessuno.** L'unico chiamante che manda `allocation_source`
>   (`features/tools/pac-allocator/allocationSource.ts:188-199`) non accende nessuno dei 6 flag: resta sul ramo
>   corto. Il difetto era dell'API, non di una schermata.
> - Porta 6157 libera dopo ogni comando.

> **⚠️ Fuori pista (black sul file dei test):** `black --check` sull'intero `test_portfolio_api.py` fallisce, ma
> fallisce uguale su HEAD: 8 blocchi di deriva scritti da `0088748a8` («feat(pac): redesign FX/funding…», 18/09), a
> `:1675-2320` di HEAD. Non sono miei e non li riformatto: aggiungerebbero 8 blocchi estranei ai miei due commit. Le mie
> due parti sono pulite (`black --check --line-ranges 767-795 --line-ranges 1421-1510`). Lo segnalo al coordinator.

> **Reperti di test-author (lettura, nessuna modifica):**
> - nel contratto, `usage_scope == "other_users"` è fissato per un asset scambiato solo sul broker OWNER del
>   chiamante: il codice conta l'uso proprio solo sui broker OWNER con quota > 0, e il test mette quella quota a 0 %.
>   Il pin è fedele al codice, l'etichetta inganna. È semantica di `allocation_source` (PAC), non mia: al coordinator;
> - due test vicini creano dati e non li puliscono. `…positions_contribution_is_date_aware` non è mio
>   (`13052a006`, 06/07): al coordinator. `…income_history_flag_gates_section_and_reconciles_with_summary` è **mio**
>   (`8ed7a0f0d`, 18/09, G1c): a ogni corsa lascia nel DB della lane un utente, un broker, un asset e 3 transazioni.
>   Non è nella test list approvata: chiedo al developer se entra in S10.

> ⏭️ **Decisione nuova del developer (2026-09-25, `ask_user` nella chat di I) → D19.** Aprendo
> `chartCoreHelpers.test.ts` per le cancellazioni: il blocco di C10 e C11, «P&L zoom-window selector:
> selectZoomWindow date maths» (`:2793-2929`), contiene altri **10 test verdi**. Provano una copia di
> `computeZoomWindowRange` scritta dentro il test, mentre la funzione vera è uscita dal prodotto al round 3 con la
> finestra 1W/1M/1Y/All. C10 era l'unico legame fra copia e sorgente: cancellato lui, i 10 restano verdi senza provare
> nulla del prodotto. Il developer ha scelto la raccomandata: **si cancellano anche loro**, con le regole di D8 (per
> nome, uno alla volta, contando prima e dopo), insieme alla copia e agli helper rimasti senza chiamanti. Totale **−14**
> invece di −4: **159 → 145**. C12, nello stesso blocco, non si cancella: si ri-pinna sulla scala delle larghezze.

> ⏭️ **Decisione nuova del developer (2026-09-25, `ask_user` nella chat di I) → D20.** Il mio test dei Proventi che
> non pulisce i dati entra in S10, **in un commit a sé**: `try/finally` che cancella broker, asset e utente, con lo
> schema del test del contratto. L'altro test vicino con lo stesso difetto non è mio: lo giro al coordinator.

### S10 passo 2 — D20: il test dei Proventi pulisce i suoi dati ✅ 2026-09-25 11:10

> **Note implementazione:**
> - **Test (test-author, solo file, nessuna lane).** Un solo test toccato:
>   `test_report_income_history_flag_gates_section_and_reconciles_with_summary`, ora a `:1377-1445`.
>   - Subito dopo `create_test_user` prende `user_id`, poi dichiara `broker_id` e `asset_id` a `None` prima del `try:`.
>   - Il `finally` ha la forma della pulizia del contratto: broker con `force` e controllo `success` per id, poi
>     asset e controllo per id, poi `delete_current_test_user`. **L'ordine conta**: il `force` del broker toglie il
>     DIVIDEND, che altrimenti bloccherebbe l'asset. Il prodotto lo fa rispettare (`delete_assets_bulk`,
>     `crud.py:308`, risponde `HAS_TRANSACTIONS`), quindi un ordine invertito darebbe un rosso, non una perdita
>     silenziosa.
>   - Tutte le asserzioni sono invariate e nello stesso ordine; quelle dopo il blocco `async with` restano lì.
>     `git diff -w` mostra solo tre aggiunte: una frase nella docstring, 4 righe di setup e il `finally`. Il resto è
>     solo rientro.
>   - Le parti A e B di S10 passo 1 non sono toccate; A comincia 26 righe più in basso, a `:1447`.
> - **Misura della perdita, con un controllo positivo.** Il DB della lane prima della corsa era vuoto (0 utenti,
>   broker, asset e transazioni). Contare zero dopo un test da solo non avrebbe provato niente: sarebbe vero anche se
>   il runner svuotasse il DB alla fine. Quindi ho fatto girare insieme al mio test
>   `…positions_contribution_is_date_aware`, che sappiamo perdere dati (non è mio: già girato al coordinator). La
>   previsione l'ho scritta prima della corsa (`/tmp/libreFolio_i_s10/d20_prediction.txt`, 11:01:48): dopo, 1 utente,
>   1 broker, 1 asset e 6 transazioni, tutte del controllo; 0 transazioni con le date del mio test.
>
> | misura (sola lettura, `mode=ro`, tutte le 15 tabelle) | prima | dopo |
> |---|---|---|
> | `users` / `brokers` / `assets` / `transactions` | 0 / 0 / 0 / 0 | 1 / 1 / 1 / **6** |
> | `broker_user_access` / `price_history` | 0 / 0 | 1 / 1 |
> | transazioni per tipo e data | — | DEPOSIT 01-01, BUY 01-02, SELL 02-15, INTEREST 02-20, FEE 02-21, BUY 03-10 (2025): tutte del controllo |
> | transazioni del mio test (2025-07-01, 07-10, 07-20) | — | **0** |
>
>   La previsione è confermata. Il residuo del controllo prova che la misura non è cieca; l'assenza delle mie date
>   prova che il mio test non lascia niente.
> - **Suite intera dopo**: `… api portfolio` → **55/55**. `ruff` pulito su `test_portfolio_api.py` e
>   `portfolio_service.py`; `black --check --line-ranges 767-800 --line-ranges 1377-1445 --line-ranges 1447-1536`
>   pulito. `git diff --check` pulito. Porta 6157 libera.
>
> | comando | esito |
> |---|---|
> | `… dev.py test --test-port 6157 --data-dir /tmp/librefolio-r2-i-charts api portfolio income_history_flag_gates positions_contribution_is_date_aware` | 2 passati, 53 deselezionati |
> | `… api portfolio` | 55/55 |
>
> Log in `/tmp/libreFolio_i_s10/` (`d20_run.log`, `d20_api_portfolio.log`, `d20_counts_*.json`).

> **⚠️ Fuori pista (ho creato due file nella cartella della lane):** aprire il DB in sola lettura ha fatto nascere
> `app.db-shm` e un `app.db-wal` vuoto accanto ad `app.db`. SQLite li crea anche in `mode=ro` quando la cartella è
> scrivibile. Il contenuto del DB non cambia, e la cartella è della mia lane. Lo scrivo perché è una scrittura, anche
> se innocua.

> **Reperto di test-author (lettura), da tenere per la pulizia generale:** oltre al controllo, altri 19 test del file
> creano un utente e non lo cancellano (`:219-541`, i test di summary e history; `TestLotsAnalysisEndpoint`,
> `:1554-1755`). Non sono miei: vanno insieme al reperto del controllo, al coordinator. Per questo il conteggio si fa
> attorno a una corsa filtrata, non attorno all'intera categoria.

### S10 passo 3 — `chartCoreHelpers.test.ts`: −14 e 7 ri-pin ✅ 2026-09-25 11:37

> **Note implementazione:**
> - **Test (test-author, solo file, nessuna lane).** Brief nella cartella di sessione (`s10_briefs/02-…`). Un solo
>   file toccato, `frontend/src/lib/components/charts/chartCoreHelpers.test.ts` (+129/−222). Solo `vitest` sul file e
>   `prettier`, da `frontend/node_modules/.bin/`; niente `npx`, niente `dev.py`, niente Playwright.
> - **Cancellazioni (D8, D19)**, per nome, una alla volta, con una corsa JSON dopo ognuna:
>   - i 4 rossi C6, C9, C10, C11: 159 → 155, i rossi da 11 a 7;
>   - i 10 verdi del blocco «P&L zoom-window selector» (D19), insieme alla copia di `computeZoomWindowRange` e agli
>     helper rimasti senza chiamanti: 155 → 145, i rossi restano 7. Nessun verde è diventato rosso per strada.
> - **Ri-pin, i 7 specchi**, ognuno con un commento `// Why (re-pin, S10): …` che dice quale cambio del prodotto lo ha
>   rotto e che cosa il pin continua a garantire:
>
> | specchio | dove | che cosa pinna adesso |
> |---|---|---|
> | C1 | `:908` | il range conservato è la lettura dal vivo o `null`, mai un bound ricordato; il gate `periodChanged` aggiunge solo un ramo `null` (round 2, §6.0.17) |
> | C2 | `:1189` | fuori dalla scala, lo zoom della ricostruzione piena si rifà dal range logico vivo: si pinna solo quell'operando del ternario scala/cascata |
> | C3 | `:1570` | stesso operando, più `renderChart(true)` sempre sul ramo pieno; i trigger della ricostruzione (privacy compresa) si controllano come insieme |
> | C4 | `:1780` | la copia porta il corpo nuovo (`e7773a143`): 7 letterali più il negativo `p.bucketEnd >= referenceDate` dietro di loro (vedi «Fuori pista») |
> | C5 | `:1964` | `splitLine` non è più tema condiviso: ogni ramo dichiara la chiave **una volta**; si conta la chiave, non il valore (S7 la cambierà) |
> | C7 | `:2206`, `:2226` | le due metà vengono da **una** chiamata a `splitBySign`; in candele il return contiene la candela totale **da sola** (overlay per broker tolto il 2026-09-21) |
> | C12 | `:2812` | al posto del selettore 1W/1M/1Y/All c'è la scala: gli 8 gradini in ordine, un bottone per gradino con testid, handler e `aria-pressed` sulla stessa variabile, nessuna traccia del selettore vecchio |
>
> - **Conteggi** (JSON in `/tmp/libreFolio_i_s10/`):
>
> | passo | totali / passati / falliti | file |
> |---|---|---|
> | prima | 159 / 148 / 11 | `cch_00_before.json` |
> | dopo i 4 rossi | 155 / 148 / 7 | `cch_04_c11.json` |
> | dopo i 10 verdi (D19) e gli helper | 145 / 138 / 7 | `cch_12_helpers_b.json` |
> | dopo 6 ri-pin (tutti tranne C4) | 145 / 144 / 1 | `cch_99_final.json` |
> | dopo C4 | **145 / 145 / 0** | `cch_c4_02_after.json` |
> | mia verifica indipendente | **145 / 145 / 0** | `cch_parent_verify_c4.json` |
>
>   `prettier --check` pulito sul file. Ogni ri-pin torna rosso se si rimette il vecchio corpo: test-author l'ha
>   provato per C4 (copia vecchia → 2 rossi; corpo vecchio nel prodotto → C4 rosso sui positivi e sul negativo).
> - Comando: `cd frontend && node_modules/.bin/vitest run src/lib/components/charts/chartCoreHelpers.test.ts
>   --reporter=json --outputFile=/tmp/libreFolio_i_s10/<passo>.json`.

> **⚠️ Fuori pista (C4, decisione mia dentro D8):** test-author si è fermato su C4, e ha fatto bene. Lo specchio
> legava alla sorgente una copia **vecchia**: `findReferenceTotalPnl` è stato riscritto in `e7773a143` per leggere la
> serie **giornaliera** e mai un giorno successivo (il reperto del developer: a giugno la linea stava a ~600 invece
> che a 0). Ri-pinnare i letterali lasciando la copia vecchia avrebbe tenuto verdi 2 test che descrivono un
> comportamento uscito dal prodotto. Ho scelto la conversione fedele, perché C4 è uno dei 7 ri-pin approvati (D8,
> «ognuno col suo perché scritto») e il conteggio resta 145:
> - la copia ora è il corpo del prodotto, parola per parola (17 righe confrontate da script), con la firma che
>   riceve `aggregationInputs`, che nel prodotto sta nella closure;
> - i call site dei 6 test di `describe('findReferenceTotalPnl')` e di `signCrossingScenarios` passano la forma nuova;
> - **2 test cambiano valore atteso**, perché ora descrivono il prodotto: una data fra due giorni si ancora al giorno
>   **prima** (100, non 150); una data dopo tutti i giorni si ancora all'**ultimo** (200, non il primo, 100). Con loro
>   2 titoli cambiano solo parola («exact day», «located day»). Ognuno ha il suo `why`;
> - il commento dell'intestazione della sezione Income non cita più «the window-preset date maths»: quei test sono
>   usciti con D19.
>
> Non ho toccato altro: le cose che seguono sono del developer (D21).

> **Reperti del passo (lettura), → D21 al developer:**
> - (a) restano verdi test che modellano l'overlay per broker delle candele, tolto dal prodotto il 2026-09-21: il
>   describe a `:1949`/`:1970`, il blocco SSR `candlesSubmodeOption` a `:2027` e i test della legenda a `:2097`,
>   `:2141`, `:2151`;
> - (b) `toPositionalValue` (`GrowthChart.svelte:1236`) non ha più chiamanti nel prodotto; lo pinnano ancora
>   `describe('toPositionalValue')` (3 test) e due letterali di C4;
> - (c) `signCrossingScenarios` (6 casi) afferma che le metà hanno la stessa lunghezza della sorgente: con
>   `splitBySign` è falso, perché gli attraversamenti dello zero aggiungono punti. `splitBySign` stesso non ha test;
> - (d) il titolo a `:2334` dice «unlike line/candles», che non è più vero;
> - (e) prodotto: il docblock «Batch 2 — Income submode window selector (1W/1M/1Y/All)» (~`GrowthChart.svelte:1130`)
>   descrive un selettore che non c'è più. Lo correggo in S7, che tocca quel file;
> - (f) prodotto, da verificare in S7: sulla scala `renderChart` forza sempre lo zoom 0–100, quindi un nuovo rendering
>   (privacy, tema scuro, resize, refresh dello stesso periodo) potrebbe azzerare lo zoom interno scelto dall'utente.

> **Ordine dei passi che restano in S10:** prima i test unitari (GrowthChart e `why` di D13, PerformanceChart,
> AllocationPanel, emoji), in parallelo, poi l'E2E da solo. Il motivo: ogni corsa E2E ricostruisce il frontend quando
> un file sotto `frontend/src/` (anche un test) è più recente di `build/index.html` (`check_frontend_needs_build`,
> `scripts/cli_base.py:540`), e la ricostruzione rigenera `src/lib/api/generated.ts` (761 KB). `currencyStore`,
> `countryStore` e `sectorStore` importano `$lib/api` a runtime: una corsa vitest in parallelo potrebbe leggere il
> file a metà.

### S10 passo 4 — S4 e S4b: `AllocationPanel.test.ts` e `allocationTypeEmoji.test.ts` ✅ 2026-09-25 11:59

> **Note implementazione:**
> - **Test (test-author, solo file, nessuna lane).** Brief nella cartella di sessione (`s10_briefs/06-…`). Due file
>   nuovi, nessun altro file toccato:
>   - `frontend/src/lib/components/dashboard/AllocationPanel.test.ts`: 210 righe, jsdom, 3 casi;
>   - `frontend/src/lib/components/dashboard/allocationTypeEmoji.test.ts`: 218 righe, ambiente node, 8 casi.
> - **AllocationPanel (S4, R21).** Si sostituiscono solo tre cose:
>   - `localStorage`: una `Map`, svuotata prima di ogni caso, con le chiavi costruite da `getUserStorageKey` del
>     prodotto;
>   - `echarts`: un `init` che registra;
>   - `$lib/api`: liste vuote, perché l'`onMount` del grafico storico altrimenti chiama `localhost:3000`.
>
>   I casi:
>   1. vista History salvata, tab `sector`: History e `sector` premuti, grafico non nascosto, richiesta fatta **una**
>      volta con `('sector', [7, 9])`. Il conteggio si legge dopo che il mount si è assestato, così una seconda
>      richiesta da un altro percorso si vede;
>   2. vista sconosciuta: Now premuto, grafico nascosto, nessuna richiesta. Il tab `sector` premuto prova che lo
>      storage è stato letto, quindi Now viene dal ripiego e non da uno storage vuoto;
>   3. tab sconosciuto: `type` premuto, e la richiesta parte con `('type', [7, 9])`. Test-author mi lasciava togliere
>      l'asserzione sugli argomenti; la tengo, perché è il comportamento di oggi: il genitore riceve il tab di ripiego.
> - **Emoji (S4b, D11).** L'enum si legge da `models.py` per regex. `read`, `assertScraped` e `readAssetTypes` sono
>   copiati parola per parola da `assetTypeTables.test.ts` (il gate di K), con la fonte citata. Nessun conteggio: ogni
>   ciclo ha davanti una guardia contro la lista vuota. I casi:
>   - la lettura dell'enum, con 4 valori àncora;
>   - una voce esplicita e non vuota per ogni valore, più `LIQUIDITY` e `UNKNOWN`;
>   - COMMODITY e REAL_ESTATE diversi dall'emoji ETF;
>   - la regola dei sottotipi, in 3 test. La famiglia è il prefisso più lungo che è a sua volta un valore dell'enum:
>     `ETF_REAL_ESTATE` → ETF, perché `ETF_REAL` non è un valore; all'integrazione `CROWDFUND_REAL_ESTATE` → 🤝, senza
>     casi speciali. Ogni `ETF_*` porta 📊 (D11). REAL_ESTATE resta fuori dalla regola;
>   - maiuscole indifferenti, e Unknown = ❓ (U+2753: l'ho controllato nei byte, nel prodotto e nel test);
>   - un valore non mappato dà `''`, anche `constructor`, che è un nome del prototipo.
> - **Verifica mia:**
>   - 11/11, 0 falliti (`/tmp/libreFolio_i_s10/u06_parent_verify.json`); `prettier --check` pulito;
>   - ho riletto ogni `why` e le àncore di prodotto citate: `AllocationPanel.svelte:43-44`, `:48-55`, `:57-58`,
>     `:69-71`, `:86-88`, `:111`/`:118`/`:130`, `:142`. Tornano tutte;
>   - l'intestazione del file emoji dice che la tabella sostituita aveva 10 chiavi e ricadeva sull'emoji ETF. È vero:
>     `58101f08f`, `?? '📊'`;
>   - test-author ha fatto anche una corsa con `--sequence.shuffle` sul file jsdom: verde, quindi nessun caso
>     dipende dall'ordine.
> - Comando: `cd frontend && node_modules/.bin/vitest run src/lib/components/dashboard/AllocationPanel.test.ts
>   src/lib/components/dashboard/allocationTypeEmoji.test.ts --reporter=json
>   --outputFile=/tmp/libreFolio_i_s10/u06_parent_verify.json`.

> **⚠️ Fuori pista:** test-author aveva messo nel primo caso dell'emoji un controllo «niente duplicati» che il brief
> non prevedeva. L'ha tolto da sé prima di consegnare: un alias legittimo di un enum Python l'avrebbe fatto fallire
> con un messaggio fuorviante. Il conteggio resta 8.

> **Reperti:**
> - **Registrazione nel runner**, del coordinator: oggi i due file non girano in nessuna suite. La mia proposta
>   (messaggio al coordinator dopo il passo 3): `AllocationPanel.test.ts` in `component-unit`, accanto a
>   `KpiSection`, `ExposureTable` e `ContributionTable`; `allocationTypeEmoji.test.ts` in `asset-unit`, accanto a
>   `assetTypeTables.test.ts`, che legge l'enum nello stesso modo. Test-author proponeva `core-unit`: decide il
>   coordinator.
> - **Prodotto, non bloccante, per S12:** il contenitore del grafico storico (`AllocationPanel.svelte:142`) non ha né
>   un testid né un attributo di stato. La visibilità esiste solo come classe Tailwind `invisible`, e il test deve
>   leggere quella. Se il prodotto passasse a `{#if}` o a `hidden`, il caso 2 diventerebbe rosso con un comportamento
>   ancora giusto. Un `data-testid` con uno stato `data-*` farebbe della visibilità un contratto stabile. È una scelta
>   d'interfaccia, del developer; per il principio di D21 («il prodotto per ora va bene») non la faccio e la porto
>   nel handoff.
> - Non girati, come da brief: `dev.py` (nessuna lane) e `svelte-check`, che entra nel `front check` unico dopo i
>   test unitari.

### S10 passo 5 — S2a, S5 e S9: `GrowthChart.test.ts` e la `why` di D13 ✅ 2026-09-25 12:15

> **Note implementazione:**
> - **Test (test-author, solo file, nessuna lane).** Brief nella cartella di sessione (`s10_briefs/04-…`). Due file
>   toccati; `GrowthChart.svelte` no (`git diff` vuoto):
>   - `frontend/src/lib/components/dashboard/GrowthChart.test.ts`: da 6 a 17 casi, +528/−4. I 6 casi del memo sono
>     intatti. Il `beforeEach` del file ora svuota anche lo storage finto, perché ogni clic scrive davvero;
>   - `frontend/src/lib/utils/privacy/moneyRenderSites.test.ts`: la `why` della voce della riga P&L totale (D13)
>     guadagna una frase, che cita il titolo esatto del caso di GrowthChart che blocca la maschera di quella riga. Il
>     resto del registro non cambia.
> - **Come il test legge il grafico.** Usa lo stesso registratore del memo.
>   - I formatter si prendono dal registro delle chiamate a `setOption`, mai da `getOption()`: il finto fonde in modo
>     superficiale e non dice quale chiamata ha installato che cosa. L'opzione completa è l'unica che porta `yAxis` e
>     `tooltip` insieme.
>   - Le viste si riconoscono dalla forma, cioè dai tipi delle serie, e non da nomi tradotti. I pulsanti si leggono da
>     `aria-pressed`.
>   - Le righe del tooltip si leggono come coppie `<span>`/`<b>`, con l'etichetta risolta via i18n come la risolve il
>     componente. Così il controllo su una riga non può essere soddisfatto da un'altra.
> - **S2a, privacy (5 casi):**
>   1. asse del denaro in Abs e in P&L linea: `20000` → `•••`, `-5000` → `-•••`, `0` → `•••` (D12); mai cifre, mai
>      `k`/`M` (D8);
>   2. l'asse `%` resta leggibile (`12.3%`): mascherare un rendimento sarebbe anche questo un difetto;
>   3. tooltip: ogni importo di Abs è `EUR •••`. La riga P&L totale porta `+` sul giorno in guadagno e il meno
>      tipografico U+2212 sul giorno in perdita. Nelle candele i negativi sono `EUR -•••`. Per ogni giorno, nessuna
>      cifra formattata della fixture compare nell'HTML;
>   4. privacy spenta, parità: asse `-5k`, `1.3M`, `0`, e `0` anche per `-0`; tooltip nel formato `toLocaleString`
>      della macchina; l'apertura `-0.00` diventa `EUR 0.00` (reperto 11);
>   5. il toggle consegna una nuova opzione completa, in tutte e due le direzioni.
> - **S5, persistenza (5 casi):**
>   - Income ripristinato già al primo frame: la prima chiamata è completa, ed è a barre;
>   - valori sconosciuti → Abs e linea;
>   - `%` ripristinato su una storia senza dati `%` → Abs, senza riscrivere lo storage;
>   - un clic durante il caricamento vince sul ripiego;
>   - le chiavi si scrivono solo al clic, mai al mount.
>
>   Le chiavi sono scritte come letterali (`lf_anon_dashboard-growth-mode` e `…-pnl-submode`), non ricostruite con
>   `getUserStorageKey`. Una rinomina farebbe perdere le preferenze già salvate nei browser, e un test che deriva la
>   chiave dallo stesso codice resterebbe verde.
> - **S9, didascalia (1 caso):** compare solo nelle candele, porta il marcatore della marquee
>   (`OVERFLOW_MARQUEE_SELECTOR`) e il testo della chiave corta risolta. Una guardia, prima del confronto, esclude che
>   la chiave sia tornata non risolta.
> - **Verifica mia:**
>   - 23/23, 0 falliti (`/tmp/libreFolio_i_s10/u04_parent_verify.json`: `GrowthChart.test.ts` 17,
>     `moneyRenderSites.test.ts` 6); `prettier --check` pulito sui due file;
>   - ho riletto le 11 `why` nel diff: ognuna dice che cosa intercetta. Il segno è asserito, non tollerato (D8).
> - Comando: `cd frontend && node_modules/.bin/vitest run src/lib/components/dashboard/GrowthChart.test.ts
>   src/lib/utils/privacy/moneyRenderSites.test.ts --reporter=json
>   --outputFile=/tmp/libreFolio_i_s10/u04_parent_verify.json`.

> **Reperti:**
> - **Prodotto, non bloccante, per S12:** l'effect di render non traccia `loading`. La lettura è in `renderChart`
>   (`if (!chartContainer || loading || history.length === 0) return;`), che gira dentro `tick().then(...)`, fuori dal
>   tracciamento. Oggi è innocuo: tutti e due i chiamanti passano `loading` derivato da `… && history.length === 0`
>   (dashboard: `historyLoading`; broker: `reportLoading && portfolioHistory.length === 0`). Quindi `loading` cambia
>   sempre insieme a `history`, che l'effect traccia. Un chiamante che passasse `loading` da solo non vedrebbe il
>   grafico ridisegnarsi alla fine del caricamento. Per D21 non lo tocco; va nel handoff.
> - Il titolo del caso 4 dice «come prima», ma `-0` → `EUR 0.00` è il comportamento nato con S2a (reperto 11). La
>   `why` parla di «oggi», ed è giusta. Lo lascio: è il prodotto di oggi (D21).

### S10 passo 6 — i 3 file nuovi nel runner, e il nome visibile di `growth-chart-memo` ✅ 2026-09-25 12:15

> **Note implementazione:**
> - **Chi:** io, su assegnazione del coordinator. Vale la sua risposta più recente, che prevale sulla prima: i tre
>   file nuovi li registro io, e solo in aggiunta.
> - `scripts/test_runner/_frontend_utility.py`, `front_component_unit`: `PerformanceChart.test.ts` e
>   `AllocationPanel.test.ts` dopo `ContributionTable.test.ts`, accanto a `KpiSection` ed `ExposureTable`. Due righe in
>   più, nessun riordino.
> - `scripts/test_runner/_frontend_asset.py`:
>   - `front_asset_unit`: `allocationTypeEmoji.test.ts` dopo `assetTypeTables.test.ts`, che legge l'enum nello stesso
>     modo. La `desc` di `asset-unit` guadagna una voce in coda («an explicit emoji for every asset type in the
>     historical allocation chart»);
>   - `growth-chart-memo`: la chiave resta. Cambiano il `name` («GrowthChart Component Tests (Vitest + jsdom)»), la
>     `desc` (in coda: privacy di assi e tooltip con la parità a privacy spenta, persistenza di modo e sottomodo con i
>     ripieghi, didascalia delle candele), la docstring (un paragrafo in più) e le tre stringhe stampate. Nessun altro
>     punto del repo cita quei testi (`git grep`); il journal cita solo la chiave, che non cambia.
> - **Verifica:** `py_compile` dei due file; `… dev.py test check-orphans` → 245 test unitari, tutti registrati e
>   tutti raggiungibili da un `all` (log `/tmp/libreFolio_i_s10/orphans_after_runner.log`). `PerformanceChart.test.ts`
>   c'era già, perché brief 05 l'aveva appena creato: il conteggio lo include.
> - I comandi di `front_asset_unit` e `front_growth_chart_memo` usano `npx` internamente. È preesistente e non è mio:
>   lo lascio, e lo segnalo nel handoff.

> **⚠️ Fuori pista (`check-orphans` scrive):** alla fine archivia un'istantanea del DB di test in
> `.testLog/00_archive/test-db_20260925_120840.tar.xz`. Senza `--data-dir` prende il DB di test di default del
> worktree (un file del 15/09), non quello della mia lane. La cartella è ignorata da Git (`.gitignore:119`) ed è nel
> mio worktree: innocuo, ma è una scrittura, e un comando che credevo di sola lettura.

### S10 passo 7 — pulizia di `…positions_contribution_is_date_aware`, assegnata sotto D20 ✅ 2026-09-25 12:27

> **Note implementazione:**
> - **Chi l'ha deciso.** Il test non è mio: è il controllo positivo del passo 2, quello che perdeva dati. Il
>   coordinator me l'ha assegnato sotto D20: stessa forma della pulizia del test dei Proventi, nello stesso commit C,
>   e il messaggio del commit lo deve dire.
> - **Test (test-author, brief 07, solo file, nessuna lane).** Un solo metodo toccato, ora a `:1304-1402` (+27 righe).
>   - Subito dopo `create_test_user` prende `user_id`, poi dichiara `broker_id` e `asset_id` a `None` prima del
>     `try:`.
>   - Il `finally` ha la forma di D20: broker con `force` e `success` per id, poi asset e `success` per id, poi
>     `delete_current_test_user`.
>   - Le asserzioni sono invariate e nello stesso ordine, dopo il blocco `async with`. La docstring guadagna una frase:
>     che cosa il test possiede, e in che ordine lo cancella.
>   - Tutto quello che segue scende di 27 righe: il test dei Proventi (D20) comincia ora a `:1404`, il test
>     parametrizzato (parte A del passo 1) a `:1485`, `TestLotsAnalysisEndpoint` a `:1566`. I numeri di riga dei passi
>     1 e 2 descrivono il file di allora.
> - **Perché quell'ordine basta, verificato nel codice:**
>   - il `force` del broker passa da `broker_service.py:706-707` a `delete_by_broker`, che toglie le 6 transazioni;
>   - senza, `delete_assets_bulk` (`services/asset_sources/crud.py:308`) rifiuterebbe l'asset con `HAS_TRANSACTIONS`
>     (`:361`);
>   - il prezzo se ne va in cascata: `price_history` ha `ON DELETE CASCADE` verso `assets` (`001_initial.py:242`), e
>     le chiavi esterne sono accese (`db/session.py:52`, `PRAGMA foreign_keys=ON`).
> - **Misura della perdita, con un controllo positivo.** Il DB della lane non era vuoto (21 utenti, 15 broker,
>   11 asset, 36 transazioni, residui delle corse intere), quindi si misurano i delta, non gli assoluti. Il controllo
>   è `test_summary_structure_with_data`: crea un utente, un broker e un DEPOSIT del 2025-01-15, e non cancella niente.
>   La previsione l'ho scritta prima della corsa (`/tmp/libreFolio_i_s10/pc_prediction.txt`, 12:22:08).
>
> | misura (sola lettura, `mode=ro`, tutte le 15 tabelle) | previsto | misurato |
> |---|---|---|
> | `users` / `brokers` / `broker_user_access` / `transactions` | +1 / +1 / +1 / +1 | +1 / +1 / +1 / +1 |
> | transazioni per tipo e data | solo DEPOSIT 2025-01-15 | solo DEPOSIT 2025-01-15 |
> | `assets` / `price_history` / `asset_provider_assignments` | 0 / 0 / 0 | 0 / 0 / 0 |
> | le 6 transazioni del test (DEPOSIT 01-01 … BUY 03-10, 2025) | +0 | +0 |
>
>   La previsione è confermata. Senza la pulizia il delta sarebbe stato +2 utenti, +2 broker, +1 asset,
>   +7 transazioni e +1 prezzo. Il residuo del controllo prova che la misura non è cieca.
> - **Suite intera dopo**: `… api portfolio` → **55/55**. `ruff` pulito sul file. `black --check` limitato ai 13 hunk
>   del diff (`--line-ranges` calcolati da `git diff -U0`, elenco in `pc_hunk_ranges.txt`): pulito. Porta 6157 libera.
>
> | comando | esito |
> |---|---|
> | `… dev.py test --test-port 6157 --data-dir /tmp/librefolio-r2-i-charts api portfolio positions_contribution_is_date_aware test_summary_structure_with_data` | 2 passati, 53 deselezionati |
> | `… api portfolio` | 55/55 |
>
> Log e conteggi in `/tmp/libreFolio_i_s10/` (`pc_run.log`, `pc_full_run.log`, `pc_counts_*.json`, `pc_tx_*.json`).

> **Reperto collaterale (misurato, non attribuito test per test):** la corsa intera ha aggiunto al DB della lane
> 19 utenti, 13 broker, 9 asset e 24 transazioni. I due test puliti (D20 e questo) non contribuiscono: sono misurati.
> Il resto è coerente con il reperto del passo 2 sui test del file che non puliscono. Non è mio: resta al coordinator,
> insieme a quel reperto.

### S10 passo 8 — S2b: `PerformanceChart.test.ts` ✅ 2026-09-25 12:30

> **Note implementazione:**
> - **Test (test-author, brief 05, solo file, nessuna lane).** File nuovo, 502 righe, 6 casi. `PerformanceChart.svelte`
>   non è toccato (`git diff` vuoto).
> - **Che cosa è finto, e perché.** Tre cose, una per ogni lacuna dell'ambiente:
>   - `echarts` è un registratore delle chiamate a `setOption`, con lo schema di `GrowthChart.test.ts`;
>   - `getCurrencyInfo` è finto solo per l'EUR. La cache vera è vuota nel test, e il suo ripiego dà `symbol = code`:
>     il ramo con il simbolo di `shortMoney` sarebbe irraggiungibile. Il CHF tiene il ripiego, ed è proprio quello che
>     lo manda nel ramo senza simbolo;
>   - il contesto 2D del canvas misura un pixel per carattere. Senza, la stima del componente lascerebbe fuori il
>     suffisso `(±x,x%)` da ogni etichetta del file.
>
>   Tutto il resto è vero: il componente, le rune, lo store della privacy, `maskable`, `formatCurrencyAmountPlain`,
>   svelte-i18n.
> - **Come legge il grafico.** Le righe si trovano per nome dell'asset o per descrizione dell'effetto, passati come
>   prop, attraverso il formatter dell'asse y: mai per posizione. Nessun numero localizzato è scritto come letterale.
>   Ogni atteso si costruisce con la stessa chiamata `Intl` o `toLocaleString` del componente.
> - **I 6 casi**, ognuno con il suo perché:
>
> | caso | che cosa intercetta |
> |---|---|
> | tacche dell'asse x, zero compreso | `maskable` tolto dal ramo dello zero (D12) o da quello compatto; suffisso fuori dalla maschera; meno dentro |
> | etichetta EUR `+€•••` con il rendimento | `maskable` tolto dal ramo con simbolo; `€•••K`; segno o simbolo inghiottiti (D8); rendimento perso. Solo l'uguaglianza esatta rifiuta `€•••K` |
> | etichetta CHF `-••• CHF` con il rendimento | l'altro ramo di `shortMoney`, che ha un letterale suo |
> | nessun importo del tooltip in chiaro, su una riga asset e su una riga effetto | un importo che aggira la maschera (`sensitivity: 'public'`, o formattato in un altro modo). Con una barriera: a privacy spenta ogni ago è davvero stampato, quindi la sua assenza non può passare per un ago costruito male |
> | nuova opzione completa al toggle, nei due versi | l'effect che perde la dipendenza dalla privacy (`void shouldMaskAmount()` tolto, o la lettura spostata dentro `tick().then`) |
> | privacy spenta: esattamente l'output di prima | `maskable` incondizionato; compattazione, segno o composizione cambiati; rendimento perso. Il meno ASCII sui locali con U+2212 è fissato com'è oggi |
>
> - **Verifica mia:** 6/6, 0 falliti, `success` true (`/tmp/libreFolio_i_s10/u05_parent_verify.json`); Prettier
>   pulito. Nel file non resta nessun `TEMP`, `.only`, `.skip` o `console.log`: la sonda temporanea dell'agente
>   (un'opzione completa al mount, una in più a ogni toggle, entrambe con `notMerge`) è stata tolta.
> - **Robustezza, dall'agente:** verde anche con i locali `de_DE`, `sv_SE` e `fr_FR`, e con l'ordine rimescolato
>   (semi 3, 7 e 20260925).
> - La registrazione nel runner c'è già (passo 6). Resta `front check`, una volta dopo tutte le unità.

> **Reperto per J (via coordinator) e per S12, dell'agente, verificato da me sul gate:** il gate `moneyRenderSites`
> applica `SAFE_CALL` alla riga intera (`if (SAFE_CALL.test(line)) return hits;`). I due rami di `shortMoney` stanno
> nello stesso `return`, su una riga sola (`PerformanceChart.svelte:170`). Se uno dei due perdesse `maskable`, il
> `maskable(` dell'altro terrebbe la riga `SAFE_CALL`, e il gate tacerebbe. `axisTickAmount` il gate non lo vede
> affatto (reperto 7 di §1). Per queste due uscite, quindi, gli unici guardiani sono i casi 1–3 di questo file.

### S10 passo 9 — D21 e D22: `chartCoreHelpers.test.ts` prova il prodotto di oggi ✅ 2026-09-25 12:30

> **Note implementazione:**
> - **Test (test-author, solo file, nessuna lane).** Un solo file toccato. `GrowthChart.svelte` non è toccato
>   (`git diff` vuoto): la parte di prodotto di D21 (via `toPositionalValue`) va in S7. Il conteggio è misurato con un
>   JSON di vitest a ogni passo (`/tmp/libreFolio_i_s10/cch_d21_*.json`, `cch_d22_*.json`).
> - **D21 (a), 145 → 142.** I reperti del passo 3, per contenuto:
>   - `toPositionalValue` senza chiamanti: escono i 3 test di `describe('toPositionalValue')`, uno per volta
>     (145 → 144 → 143 → 142), poi il `describe` rimasto vuoto, e i 2 letterali di C4 che la pinnavano;
>   - i test che modellavano l'overlay per broker delle candele ora descrivono la candela da sola: il test degli slot
>     perde la metà broker, e la fixture reale di ECharts del crash delle candele prende la forma vera, con il solo
>     totale. Il controllo SSR lancia ancora;
>   - il titolo che diceva «unlike line/candles» è corretto.
> - **D21 (b), conteggio invariato.** I 6 `signCrossingScenarios` girano su `splitBySignImpl`, una copia fedele di
>   `splitBySign`. Ho confrontato la copia con `GrowthChart.svelte:1273-1304` riga per riga, dopo aver annullato le
>   rinomine (`cmp_splitbysign.py`): identica. C4 la lega alla sorgente con 10 letterali.
> - **D22, 142 → 144**, tutto dentro `signCrossingScenarios`:
>   - i nomi «pari» e «dispari», scambiati, sono corretti (mia decisione: stessi casi, nome giusto);
>   - la terza colonna, che prima era un conteggio, ora è la lista degli istanti attesi, scritta a mano e non calcolata
>     con la regola in prova. Il controllo condizionale sul punto medio esce: la lista lo copre per ogni riga;
>   - riga nuova `[5, 0, -5]` → nessun incrocio, per la guardia dello zero;
>   - riga nuova `[30, -10]` → `2026-01-01T18:00:00.000Z`, per il peso dell'interpolazione;
>   - escono le 3 asserzioni vuote sulla linea di riferimento, con le loro variabili rimaste senza uso. La linea resta
>     provata altrove: la forma piatta dai letterali del test degli slot, il valore da `describe('findReferenceTotalPnl')`;
>   - la `why` di D21b guadagna la riga di D22.
>
> | passo | modifica | totale / passati / falliti |
> |---|---|---|
> | prima | — | 142 / 142 / 0 |
> | a | nomi scambiati | 142 / 142 / 0 |
> | b | colonna → istanti; via il controllo sul punto medio | 142 / 142 / 0 |
> | c1 | + riga `[5, 0, -5]` | 143 / 143 / 0 |
> | c2 | + riga `[30, -10]` | 144 / 144 / 0 |
> | d | via le 3 asserzioni; riga di D22 nella `why` | 144 / 144 / 0 |
> | e | finale, dopo Prettier | 144 / 144 / 0 |
>
> - **Mutazioni vere sulla copia, poi ripristinata** (`cmp` byte per byte con l'istantanea del passo d). Le previsioni
>   erano scritte prima di ogni corsa:
>
> | mutazione | previsto | osservato |
> |---|---|---|
> | (i) via la guardia dello zero | rosso solo `[5, 0, -5]`, al controllo della lunghezza | 1 rosso, quello: lunghezza 4 invece di 3, perché (5, 0) prende t = 1 e un incrocio a `2026-01-02T00:00:00.000Z`. Ogni altro zero confina con un negativo o con un buco |
> | (ii) peso dal lato sbagliato (`Math.abs(next)` al numeratore) | rosso solo `[30, -10]`, sulla lista degli istanti | 1 rosso, quello: `06:00` invece di `18:00`. Le righe ad ampiezze uguali restano verdi, perché lì t = 0,5 in tutti e due i casi |
>
> - **Verifica mia:**
>   - 144/144, 0 falliti, 23 suite, `success` true (`/tmp/libreFolio_i_s10/cch_d22_parent_verify.json`); Prettier
>     pulito;
>   - il delta di D22 da solo, ricalcolato da me: +32/−27 in 9 hunk, tutti dentro `signCrossingScenarios`;
>   - gli istanti rifatti a mano: nella riga con i buchi solo 20 → −20 fa incrocio, a mezzogiorno del 7; 30 → −10
>     arriva a zero a t = 30/40 = 0,75, cioè alle 18:00;
>   - i JSON delle due mutazioni hanno 1 rosso ciascuno, sul caso previsto.
> - Cumulativo di S10 sul file, contro HEAD: 296 righe aggiunte e 320 tolte.

> **⚠️ Fuori pista (un verde che il JSON chiama fallito):** dopo la terza cancellazione di D21 il JSON segnava
> 142/142 e 0 falliti, ma `success: false` e il file `failed`, senza messaggio. È coerente con il
> `describe('toPositionalValue')` rimasto vuoto. Il passo dopo ha tolto il guscio, ed è tornato `success: true`. Da qui
> in avanti leggo `success`, non solo il numero dei falliti.

> **Reperti, per S7 e per il handoff:**
> - **S7:** la fetta di sorgente che C4 legge per `clipToSign` ora comprende la sua JSDoc. Se la docstring corretta in
>   S7 contenesse il testo `return null`, C4 diventerebbe rosso.
> - **Resta aperto da D21, fuori da D22:** la guardia `Number.isFinite(x0/x1)` (date non valide) non è esercitata da
>   nessuna riga, e non è fra i 10 letterali di C4. Non lo aggiungo: va nel handoff.

### S10 passo 10 — `front check` al floor ✅ 2026-09-25 12:33

> **Note implementazione:**
> - `… dev.py front check` → **3 errori e 41 avvisi in 4 file**, esattamente il floor di S1. I 4 file non sono miei:
>   `BrokerSharingPanel.svelte`, `GlobalSettingsTab.svelte`, `TransactionFormModal.test.ts`,
>   `ToolExecutionMetrics.svelte`. Nessuno dei 6 file di test di S10 compare nel log, e svelte-check i `.test.ts` li
>   legge (uno dei 4 lo è). Log: `/tmp/libreFolio_i_s10/front_check_s10.log`.
> - Con questo le unità di S10 sono chiuse. Il prossimo passo è C4.

> **⚠️ Fuori pista (anche una corsa `api` ricostruisce il frontend, in silenzio):** `generated.ts` ha l'ora 12:24:06 e
> `build/index.html` 12:25:16, cioè durante la corsa intera di `api portfolio` del passo 7. Il meccanismo:
> - il backend condiviso dei test è `dev.py server --test` (`scripts/test_runner/_server.py:220-229`), con l'output
>   mandato a `DEVNULL` (`:269-270`);
> - `dev.py server` chiama `auto_build_frontend()` (`dev.py:216`), che ricostruisce quando un file sotto
>   `frontend/src/` è più recente della build. Qui lo erano i file di test che test-author stava scrivendo;
> - quindi nessuna riga del mio log parla di build.
>
> La regola del passo 3 («prima le unità in parallelo, poi l'E2E da solo») presupponeva che ricostruisse solo l'E2E.
> Non è così: **ogni** comando della lane che avvia il backend può ricostruire. I passi b, c1, c2 e d di D22
> (12:24:01 → 12:25:16) hanno girato durante la ricostruzione, e `generated.ts` è stato riscritto mentre girava c1.
> Non ho visto danni: ogni passo ha dato il conteggio previsto, e il passo finale (12:27:13) e la mia verifica
> (12:28:25) sono venuti dopo. Da qui in avanti nessun comando della lane parte mentre gira vitest nel worktree.
> `generated.ts` e la build sono ignorati da Git, quindi il digest di C4 non li vede.

### Checkpoint C4 — pronto (2026-09-25 12:42)

> **Note implementazione:**
> - **Contenuto:** 8 commit su `4d885f1e8`, tutti di S10, in quest'ordine:
>
> | # | commit | percorsi |
> |---|---|---|
> | 1 | `needs_engine`: la correzione e il suo test parametrizzato (passo 1, parte A) | `portfolio_service.py`; in `test_portfolio_api.py` solo il test nuovo |
> | 2 | il contratto di `/portfolio/report` a 13 chiavi (passo 1, parte B) | `test_portfolio_api.py`: i 2 blocchi del contratto |
> | 3 | D20 e la pulizia di `…positions_contribution_is_date_aware`, che il coordinator mi ha assegnato sotto D20, nello stesso commit (passi 2 e 7) | `test_portfolio_api.py`: il resto |
> | 4 | `chartCoreHelpers.test.ts`: D19, i 7 ri-pin, D21 e D22 (passi 3 e 9) | il file intero |
> | 5 | `GrowthChart.test.ts`, la `why` di D13 e il nome visibile di `growth-chart-memo` (passi 5 e 6) | `GrowthChart.test.ts`, `moneyRenderSites.test.ts`; in `_frontend_asset.py` i blocchi di `growth-chart-memo` |
> | 6 | `PerformanceChart.test.ts`, con la sua riga nel runner (passi 8 e 6) | il file nuovo; in `_frontend_utility.py` la sua riga |
> | 7 | `AllocationPanel.test.ts` e `allocationTypeEmoji.test.ts`, con le loro righe nel runner (passi 4 e 6) | i 2 file nuovi; in `_frontend_asset.py` la riga dell'elenco e la `desc` di `asset-unit`; in `_frontend_utility.py` la sua riga |
> | 8 | questo file | il journal |
>
> - `needs_engine` viene per primo, in un commit a sé, come ha chiesto il coordinator (24/09, 15:24 e 15:37). Il suo
>   rosso prima della correzione è nel registro del passo 1: 6 falliti, poi 6 passati.
> - **Come:** lo stesso protocollo di C1–C3. Tre file si dividono fra più commit: `test_portfolio_api.py` (1, 2 e 3),
>   `_frontend_asset.py` (5 e 7) e `_frontend_utility.py` (6 e 7). Gli stati intermedi li costruisce il generatore di
>   C1 dai blocchi di `git diff -U0`, con una tabella esplicita blocco → commit. È asserito che il confine 0 è HEAD e
>   il confine 8 è l'albero di lavoro. Lo script deriva da quello di C1, che ha già 8 commit, con sostituzioni contate.
>   Le verifiche sono quelle di C3 (A, B, digest, dry-run, 3 cloni, messaggi), più un controllo per confine dei file
>   divisi.
> - **Questa è l'ultima scrittura nel worktree prima del digest.** I numeri del bundle (alberi, sha256, digest)
>   dipendono da questo file, quindi qui non ci sono: li registro dopo il commit, come per C3.
> - **Dopo C4:** l'E2E di brief 03, da solo nella lane; poi E7.

### ⏸️ Pausa — la macchina si spegne (2026-09-25 13:00)

> **Stato di S10:** i passi 1–10 sono fatti e registrati sopra. Nel worktree le unità sono verdi: vitest intero
> 6131/6131 (245 file), `api portfolio` 55/55, `services roi-fifo-utils` 507/507, `front check` al floor (3 errori,
> 41 avvisi). Dopo C4 restano l'E2E di brief 03 (da solo nella lane), E7, C5, S7, S7b, S8, S11-finale e S12.
>
> **Stato di C4: il bundle è a metà, e il titolo «pronto» qui sopra era prematuro.**
> - **Fatto e valido.** Il bundle sta in `/tmp/libreFolio_i_c4_commits/`, con una copia nella cartella di sessione,
>   fuori dal repo, perché lo spegnimento svuota `/tmp`. Contiene:
>   - gli stati 0–8 (0 = HEAD, 8 = albero di lavoro) e i controlli per confine dei file divisi, che danno
>     `BOUNDARY CHECKS OK`: mappa AST blocco → metodo, compilazione, ruff come delta su HEAD, test registrati
>     presenti a ogni confine;
>   - le 8 patch, gli 8 messaggi (`MESSAGES OK`) e lo script, derivato da quello di C1 con sostituzioni contate;
>   - il digest, uguale con 3 git (2.55, 2.54, 2.53);
>   - la scansione privacy: nelle righe aggiunte gli importi sono esempi sintetici, oppure vengono dal DB di test
>     della lane (il triage di E8/E9, con i broker del mock).
> - **Fatto ma non valido: i controlli frontend per confine.** Lo scratch non era equivalente al worktree, per due
>   cause:
>   1. `node_modules` era un link simbolico al worktree. Vite risolve il percorso reale, che cade fuori da
>      `server.fs.allow` dello scratch, e così 86–88 file di component test non si caricano («Cannot find module
>      '/@fs/…/@testing-library/svelte/src/vitest.js'»). Fra questi ci sono `GrowthChart.test.ts`,
>      `PerformanceChart.test.ts` e `AllocationPanel.test.ts`: quei confini non provano i miei test;
>   2. mancava `backend/app/db/models.py`, che `allocationTypeEmoji.test.ts` e `assetTypeTables.test.ts` leggono come
>      testo. Il risultato sono 5 rossi d'ambiente al confine 7. La mia scansione delle dipendenze fuori da
>      `frontend/` cercava solo `new URL(…)`, mentre questi test costruiscono il percorso in un altro modo.
>
>   Restano validi svelte-check (3 errori e 41 avvisi a ogni confine) e prettier (rc 0), perché non passano dal
>   runner dei test.
> - **Questa nota cambia il journal.** Vanno quindi rigenerati lo stato 8, la patch 08, il digest e lo script. Gli
>   alberi 1–7 non cambiano, perché il journal entra solo nel commit 8.
>
> **Alla ripartenza, in ordine:**
> 1. rigenerare lo stato 8, la patch 08, il digest (con 2 git) e lo script;
> 2. ricostruire lo scratch: `node_modules` clonato con `cp -cR`, non linkato, e `backend/app/db/models.py` preso da
>    HEAD. Prima di leggere i rossi, confrontare il numero di file e di test con quello del worktree. Poi rilanciare
>    i confini 0, 4, 5, 6 e 7 e confrontare i rossi per nome con il confine 0. Atteso: gli 11 rossi di
>    `chartCoreHelpers` al confine 0, e nessun rosso dal 4 in poi;
> 3. le verifiche di C3: applicazione su copie e `cmp`, `verify_cached`, dry-run su 7 combinazioni, e2e in 3 cloni,
>    backup e dry-run dal backup;
> 4. `git merge-tree` contro `dev_release2`;
> 5. `CHECKPOINT READY` al coordinator.
>
> **⚠️ Fuori pista:**
> - **Lo scratch rotto.** Ho scritto «pronto» prima di aver visto un confine frontend verde con tutti i file caricati.
>   Il conteggio lo mostrava già: 3766 test al confine 0, contro i 6131 del worktree. D'ora in poi confronto i conteggi
>   dello scratch con quelli del worktree **prima** di leggere i rossi.
> - **La cache di vitest.** Le corse con il link hanno scritto `results.json` e `_svelte_metadata.json` in
>   `frontend/node_modules/.vite/vitest/` del worktree. È un percorso ignorato da Git, lo stesso in cui scrive vitest
>   quando gira nel worktree, e cambia solo l'ordine in cui vitest esegue i file.

### ▶️ Ripresa (2026-09-28 10:31)

> **Note implementazione:**
> - **Stato alla ripartenza:** HEAD `4d885f1e8`, gli stessi 11 percorsi, stage vuoto, porte 6157 e 6167 libere.
>   Lo spegnimento ha svuotato `/tmp`. Il bundle l'ho ripristinato dalla copia in sessione (201 file, sha256
>   identici); i DB di test della lane si ricreano da soli.
> - **Ordine:** quello della nota di pausa. Questa è di nuovo l'ultima scrittura nel worktree prima del digest. Gli
>   alberi, il digest, i confini frontend rifatti e il `merge-tree` li registro dopo il commit, nel registro di C4,
>   come per C1–C3.
> - **Per le E2E dopo C4** (indicazione del coordinator): prima `front build --debug`, perché il server di test
>   compila in debug.

### Checkpoint C4 — committato ✅ 2026-09-28 11:41

> **Note implementazione:**
> - **Contenuto:** 8 commit su `4d885f1e8`, tutti di S10, nell'ordine del registro «Checkpoint C4 — pronto». Il
>   bundle è in `/tmp/libreFolio_i_c4_commits/`, costruito senza scrivere nel repository, con la copia nella cartella
>   di sessione (471 file, identica file per file).
> - **Le guardie** sono quelle di C1–C3, con HEAD `4d885f1e8`, gli 11 percorsi e i 9 alberi di C4. Tre file si
>   dividono fra più commit: gli stati intermedi li genera `gen_states.py` dai blocchi di `git diff -U0`, con la
>   tabella blocco → commit.
>
> | verifica | come | esito |
> |---|---|---|
> | confini, backend e runner | `boundary_checks.py` sugli stati generati, mai sul worktree | `BOUNDARY CHECKS OK`, rilanciato il 28/09 con lo stesso esito del 25/09: mappa AST blocco → metodo, compilazione, nessuna violazione ruff oltre HEAD (`_frontend_asset.py` ne ha 22 già a HEAD), test registrati presenti a ogni confine |
> | confini, frontend | una copia completa della repository a HEAD (`git archive` verificato byte per byte e modo per modo; `node_modules` clonato APFS, non linkato); per confine svelte-check, vitest intero e prettier | cancello: b7 = worktree test per test (245 file, 6131 test, stessi nomi e stati). b0 6118 test con gli 11 rossi preesistenti di `chartCoreHelpers`; b4 6103, b5 6114, b6 6120, b7 6131, tutti senza rossi e senza file non caricati: gli 11 rossi spariscono a b4. svelte-check 3 errori e 41 avvisi, identici a ogni confine e nessuno nei file di C4; prettier rc 0 |
> | A — patch semplici | `git apply` in sequenza su copie di BASE, poi `cmp` | 11/11 identici, nessun file in più |
> | B — patch in stage | indice temporaneo, `write-tree` dopo ogni patch | alberi 1–8 quelli attesi; `add -A` dell'albero di lavoro dà l'albero 8 |
> | digest del contenuto | come in C1 | `5649b33d…7776`, identico con git 2.55 e 2.54 (Apple) |
> | dry-run sul repository reale | `run_commits.sh --dry-run` | rc 0 in 7 prove su 7, più una dalla copia di backup. Indice, HEAD, refs, oggetti e worktree invariati |
> | commit veri, in 3 cloni usa-e-getta | git 2.55 con bash 3.2, git 2.53 con bash 5.3, Apple git 2.54 in `env -i` | 9/9 PASS in ognuno: 8 commit lineari, alberi e messaggi attesi; le guardie scattano; il secondo lancio è rifiutato |
> | messaggi | `check_messages.py` | subject da 42 a 50 caratteri, righe ≤ 72, solo ASCII, niente attribuzioni AI. La scansione privacy trova la parola «backup» e i `386.03` del triage di E8/E9, sintetici: vengono dall'E2E della lane, sul DB popolato dal runner |
> | revisione combinata, prima del merge | `merge-tree` di `dev_release2` con l'albero 8 in uno store di oggetti usa-e-getta, estratto in una seconda copia completa | 0 conflitti. vitest 6273/6273 su 256 file, 0 non caricati; i 5 file solo di C4 identici a b7 test per test. svelte-check 3 errori e 41 avvisi, nessuno nei file di C4; prettier rc 0; `py_compile` dei due runner; `check-orphans` pulito (256 unit, 83 spec, 223 file backend, tutti raggiungibili da un `all`) |
>
> - sha256 dello script `f8a17fc8…e1a3`; patch e messaggi nel bundle (`files.sha256`).
> - **Non rilanciati, e perché:** i test backend confine per confine. I metodi toccati sono indipendenti (mappa
>   AST); b1 porta ancora il rosso preesistente del contratto, chiuso a b2; lo stato finale è verde
>   (`api portfolio` 55/55, `services roi-fifo-utils` 507/507, registro «S10 passo 7»).
> - **Il coordinator ha rifatto le verifiche da sé** (10:58): HEAD, gli 11 percorsi, stage vuoto; nessuna chiave
>   i18n, 0 password, nessun valore del dizionario dei dati reali; `diff --check`; nessun `.only` né `.skip`;
>   subject solo ASCII; in `portfolio_service.py` solo `needs_engine`; digest e dry-run in it_IT e en_US.
> - **Il developer ha committato** (segnale del coordinator alle 11:41). La mia verifica dopo il commit, in sola
>   lettura:
>   - ogni albero è quello atteso, e ogni messaggio è identico byte per byte al suo file;
>   - ogni patch è identica byte per byte al diff fra il commit e il suo genitore (`git diff-tree -p --binary
>     --full-index`, con le stesse opzioni del builder);
>   - un solo genitore per commit, in fila su `4d885f1e8`; nessuna operazione in corso; stage vuoto.
>
> | # | commit | subject | albero |
> |---|---|---|---|
> | 1 | `00bb1ac75` | `fix(portfolio): honor all report section flags` | `a145aa35c5e3` |
> | 2 | `1b3a20fb0` | `test(portfolio): pin all 13 report top-level keys` | `be103ebd60fc` |
> | 3 | `266cebe8c` | `test(portfolio): clean up report test data` | `1701610e654f` |
> | 4 | `2e4c8589f` | `test(charts): retire stale chart helper mirrors` | `42316a229df9` |
> | 5 | `a3205800b` | `test(dashboard): pin growth chart privacy, memory` | `829f876e250f` |
> | 6 | `f3fdbd8aa` | `test(dashboard): pin performance chart privacy` | `92c987630999` |
> | 7 | `60e01ecda` | `test(dashboard): pin allocation memory, type emoji` | `4ce9adad2de8` |
> | 8 | `472f51498` | `docs(journal): record S10 tests and checkpoint C4` | `a0644d300bfb` |

> **⚠️ Fuori pista (il conteggio dei conflitti di `merge_forecast.sh`):** la prima versione contava come conflitti le
> righe «Auto-merging». Con `--name-only --messages` i percorsi in conflitto vengono prima della prima riga vuota, i
> messaggi informativi dopo. Ho corretto il parser e rilanciato: 0 conflitti, stessi alberi.

> **⚠️ Fuori pista (le due copie di prova):** da tutte e due ho lasciato fuori `LibreFolio_devWiki/corpus`: 106 dei
> suoi 107 link simbolici sono assoluti e puntano al checkout principale, e nessun test frontend lo legge. Nelle
> copie `vite.config.ts` non trova git e scrive la versione «unknown»: innocuo, perché vitest usa `vitest.config.ts`.

### Allineamento a `dev_release2` — merge `9016bb0d1` ✅ 2026-09-28 11:45

> **Note implementazione:**
> - Deciso dal developer per D, I e K. Lo script l'ha preparato il coordinator e l'ha lanciato il developer; io non
>   ho toccato Git.
> - `9016bb0d1`: genitori `472f51498` (C4) e `ea30d5ccf` (`dev_release2`), albero `4d9243fb0bc2`, **identico** a
>   quello della mia previsione (`merge_forecast.sh`, caso b) e alla simulazione del coordinator. Nessun conflitto.
>   Fusi in automatico, in righe diverse: i 4 cataloghi i18n, `moneyRenderSites.test.ts` e `_frontend_utility.py`.
>   Albero di lavoro pulito dopo il merge.
> - **Cosa porta** (32 commit dal merge base `2a5927c48`): J (privacy: `maskFormattedNumber` e `maskCurrencyParts`
>   in `maskable.ts`, `privacy-masking.spec.ts`, le etichette di `PrivacyToggle` in i18n con lo stesso inglese), A
>   (onboarding e titolo della finestra) e le registrazioni del runner.
>   - Nel backend solo `populate_mock_data.py` (righe di onboarding) e `test_db_referential_integrity.py`: nessun
>     codice dell'app, niente in `schemas/` né in `api/`, quindi niente `api sync`.
>   - Nessun cambio a `package.json` né al lock: niente `npm ci`.
>   - Nessun file che le mie E2E leggono: `dashboard.spec.ts`, `brokers-detail.spec.ts`, `asset-detail.spec.ts`,
>     `GrowthChart.svelte`, `PerformanceChart.svelte`, `Header.svelte` e `Sidebar.svelte` sono invariati.
> - **Conseguenza per S10:** `176f19707` di J adesso è nella mia base, quindi il seguito condizionato della riga S10
>   (i formatter su `maskFormattedNumber`) si può fare. Lo analizzo dopo la validazione.

### Validazione sulla revisione combinata `9016bb0d1` — backend e unit ✅ 2026-09-28 11:52

> **Note implementazione:** nella lane 6157 / `/tmp/librefolio-r2-i-charts` (svuotata dal riavvio: la ricrea il
> runner), un comando alla volta, nell'ordine chiesto dal coordinator. Log completi in `/tmp/libreFolio_i_postmerge/`.
> Porta 6157 libera dopo ogni comando.
>
> | # | gate | esito | atteso |
> |---|---|---|---|
> | 1 | `api portfolio` | 55/55 | 55/55 (registro S10 passo 7) |
> | 2 | `services roi-fifo-utils` | 507/507 | 507/507 |
> | 3 | `front-utility core-unit` | 2531/2531 su 96 file | la copia di prova sullo stesso albero |
> | 4 | `front-utility component-unit` | 2042/2042 su 83 file | idem |
> | 5 | `front-asset asset-unit` | 439/439 su 18 file | idem |
> | 6 | `vitest run …/moneyRenderSites.test.ts` | 6/6 | 6/6 |
>
> - **Confronto con la copia di prova** (`compare_units.py`): per ognuna delle tre categorie ho letto dal runner
>   (AST) i file registrati e sommato i loro test nel `vitest.json` misurato sulla copia di prova del merge previsto
>   (albero `4d9243fb`, lo stesso di `9016bb0d1`). File e test coincidono nelle tre categorie; nessun file registrato
>   manca dal riferimento, e nel riferimento nessuno è rosso.
>
> | 7 | `front build --debug` | rc 0; svelte-check 3 errori e 41 avvisi in 4 file, gli stessi dei confini di C4 (`TransactionFormModal.test.ts` ×2, `ToolExecutionMetrics.svelte`; avvisi in `BrokerSharingPanel.svelte` e `GlobalSettingsTab.svelte`), nessuno nei miei file | come la copia di prova |
>
> - **Brief 03 aggiornato alla base** prima di consegnarlo (nella cartella di sessione): HEAD `9016bb0d1`, build
>   già fatta, righe di GrowthChart riverificate (badge `:2264`, `reconcileCandleWidth` `:1152`,
>   `availableCandleWidths` `:390-406`), più due dettagli della regola della scala che il 25/09 non aveva scritto:
>   in income la scala parte da `1W` (`INCOME_MIN_WIDTH`), e se nessun gradino entra resta il più basso da solo
>   (`:405`). Percorsi corretti di `privacy-toggle` (`PrivacyToggle.svelte:22`), dello store e di
>   `scrollOnOverflow.ts`. La spec di J non copre i due grafici, quindi la Parte 3.2 non la duplica. Per il segno
>   negativo sotto privacy la spec accetta anche U+2212: il seguito `maskFormattedNumber` potrà tenere il meno
>   della locale, e il contratto è «mascherato, segno tenuto».
> - Se la misura «prima» sulla nuova base non dà 15/7 e 28/1, il test-author si ferma e riporta i nomi: il merge
>   ha portato anche l'onboarding persistente di A.

### S10 — brief 03 (E2E dashboard e broker), primo giro: fermo alla base ⏸️ 2026-09-28 12:20

> **Note implementazione:** il test-author ha misurato la base su `9016bb0d1` e si è fermato, come chiedeva la regola
> che avevo scritto nel brief, perché la dashboard non dava 15/7. Nessuna modifica alle spec.
>
> | azione | totale | rossi | log |
> |---|---|---|---|
> | `front-portfolio dashboard` | 15 | **5**: E1, E2, E3, E4, E5 | `/tmp/libreFolio_i_s10/e2e_p1_baseline_dashboard.log` |
> | `front-broker detail` | 28 | 1: E6 (la metà income, `:742`) | `/tmp/libreFolio_i_s10/e2e_p1_baseline_broker_detail.log` |
>
> - Nessun clic intercettato né overlay di onboarding nei log: la causa che avevo indicato per prima (A) è esclusa.
> - La tooltip dell'income copre la settimana 09/08–15/08; Dividend, Interest e Total valgono `EUR 0.00`, quindi
>   sono senza segno: E5 ed E6 confermano l'**assunzione** del triage del 25/09.

> **⚠️ Fuori pista (E8 ed E9 verdi per il calendario):** il puntatore sta a un 55% fisso della tela, e la finestra
> predefinita (3M) finisce oggi. Il giorno sotto il puntatore quindi si sposta ogni giorno (oggi − 47 circa), e con
> lui cambia se una riga broker vale zero, cioè è senza segno per scelta di prodotto. Il 25/09 il puntatore era su una
> domenica; oggi è su un mercoledì. Il meccanismo del weekend (FX solo nei giorni feriali nel seed) l'ha dedotto il
> test-author e non è misurato. Non cambia niente: il verdetto resta **assunzione, latente**, e i re-pin di E8/E9 sono
> ancora dovuti.

> **⚠️ Fuori pista (l'ancora di E4 nel brief era falsa):** avevo scritto che la scala vede tutta la storia del seed.
> Invece conta i giorni serviti per la finestra scelta (`dates.length`, `GrowthChart.svelte:391`). A 3M il gradino 1D
> è disegnabile, quindi le candele aprono giornaliere: la scala offre 1D (premuto), 3D, 1W, 2W e 1M. È il prodotto di
> oggi, non un difetto. Il contratto «candele più grossolane della linea alla stessa finestra» resta vero, ma solo per
> una finestra abbastanza lunga.

> **Decisioni mie, dentro lo scope approvato** (lista test di S10: «E4 re-pin sulla scala, misura prima»), scritte
> nel brief come «Addendum A»:
> 1. Base accettata: 15/5 e 28/1.
> 2. **E4 sul preset `1Y`**, titolo invariato. L'intervallo sta in sessionStorage, quindi è per contesto. Si misura
>    prima (giorni serviti e larghezza della tela). La precondizione è ricavata dai dati: `giorni × 2.5 > larghezza
>    della tela`. Linea senza scala e senza badge (il badge esiste solo se la linea aggrega, `ResolutionBadge.svelte:17`);
>    candele senza `1d`.
> 3. **E8 ed E9 accoppiano ogni valore alla riga**:
>    - E8 conta anche il `—` di un broker senza valore;
>    - E9 conta come OHLC le righe con un'etichetta che non è di un broker; se sotto il puntatore non c'è una
>      candela, lo scrive nel messaggio.
> 4. `--workers 4` una volta per azione alla fine, dentro la lane.

### S10 — brief 03 (E2E dashboard e broker) ✅ 2026-09-28 13:00

> **Note implementazione:** un secondo test-author ha ripreso il brief con l'Addendum A (il primo girava in modalità
> sync e non poteva ricevere il seguito). Ha modificato solo `dashboard.spec.ts` e `brokers-detail.spec.ts`.
>
> | corsa | dashboard | broker detail | log (`/tmp/libreFolio_i_s10/`) |
> |---|---|---|---|
> | base (accettata) | 15, 5 rossi (E1–E5) | 28, 1 rosso (E6) | `e2e_p1_baseline_*.log` |
> | dopo le Parti 1 e 2 | **12**/12 (15 − 3) | 28/28 | `e2e_p2_*.log` |
> | dopo la Parte 3 | 18/18 (12 + 6) | — | `e2e_p3_dashboard.log` |
> | finale, seriale | **18/18** (48,5 s) | **28/28** (1,0 min) | `e2e_final_*.log` |
> | finale, `--workers 4` | **18/18** (21,6 s) | **28/28** (40,2 s) | `e2e_final_w4_*.log` |
>
> - **Parte 1.** Tolti esattamente i 3 test E1–E3; il confronto dei titoli ordinati dice che non ne è sparito un
>   altro. Tolti anche gli helper rimasti orfani (`ZOOM_WINDOWS`, `selectZoomWindow`, `recascadeUnderCandleGrammar`
>   e `SIGNED_AMOUNT`). Il commento sopra `type PnlSubmode` ora parla della scala e dice che il badge esiste solo in
>   Valore, % e linea P&L. Il test-author ha riscritto anche il paragrafo «NOT asserted», che negava l'esistenza di
>   `__lfChart`: era diventato falso anche quello.
> - **E4, misurato prima:**
>
>   | | 3M (predefinito) | 1Y |
>   |---|---|---|
>   | giorni serviti | 93 | 364 |
>   | tela | — | 545 px (area del grafico 435 px) |
>   | gradini candele | 1D (premuto), 3D, 1W, 2W, 1M | 3D (premuto), 1W, 2W, 1M, 3M, 6M |
>   | gradini income | 1W (premuto), 2W, 1M | 1W (premuto), 2W, 1M, 3M, 6M |
>
>   Il conto: 364 × 2,5 = 910 > 545, quindi a 1Y un corpo giornaliero non entra; la linea resta giornaliera
>   (0,67 bucket/px ≤ 1,3). Il test controlla la linea con un punto per giorno servito (letto da `__lfChart`),
>   senza scala né badge; le candele senza `1d` e con meno corpi che giorni; poi il ritorno alla linea. Titolo
>   invariato.
> - **E5, E6, E8, E9:** verdetto **assunzione** per tutti. E5 ed E6 contano gli importi col segno facoltativo, almeno
>   3. E8 ed E9 accoppiano ogni valore alla sua etichetta (`div > span + b`):
>   - E8: ogni broker servito etichetta una riga, e c'è una sola riga di un non-broker (il Totale, mai cercato per
>     testo); le celle valore sono esattamente broker + 1, e ognuna è un importo o `—`;
>   - E9: prima una barriera sul grafico (la serie candlestick ha corpi veri), poi le righe senza etichetta di un
>     broker, esattamente 4 importi. Se sotto il puntatore non c'è una candela, il messaggio lo dice.
>   - In E6 la metà «linea» vuole ora esattamente una cella valore, e che sia un importo.
> - **Parte 3, sei test nuovi:** la scala (il gradino da cliccare lo legge dall'offerta; il numero di bucket si sposta
>   nella direzione giusta; in income niente `1d` né `3d`); la privacy dell'asse y di GrowthChart (Abs, P&L, e `%`
>   come controllo di troppo mascheramento) e dell'asse x di PerformanceChart, zero compreso, con `finally`; S4 al
>   ricaricamento; S5 con la navigazione nell'app (`nav-assets` → `nav-dashboard`); S9 a 375 px (`nowrap` e
>   `data-overflowing`). Più il test `:130`, che ora sceglie «now» invece di darlo per predefinito.
> - **La mia verifica:**
>   - ho letto tutto il diff, e le due assunzioni strutturali tengono: tutte le righe valore sono
>     `<div><span>…</span><b>…</b></div>` (`buildTooltipRow`, `echartsTooltipHelpers.ts:56`, compreso il `—`);
>     le intestazioni sono `div` semplici con la data ISO;
>   - totali ricontati nei 4 log finali; prettier `--check` pulito; `diff --check` pulito;
>   - nessun `waitForTimeout`, `.only`, `.first()` nudo né resto dello scratch. `test.setTimeout(60_000)` è già lo
>     stile della casa (8 spec);
>   - porta 6157 libera.
> - `LADDER_MIN_BODY_PX = 2.5` nella spec è una copia della costante di prodotto, che è marcata PROVISIONAL
>   (`GrowthChart.svelte:183`). Se il prodotto la alza, la precondizione resta sufficiente; se la abbassa, E4 fallisce
>   con un messaggio che lo dice. Accettato così.

> **⚠️ Fuori pista (lo spegnimento del backend oltre i 5 s):** nelle due corse finali della dashboard il runner
> scrive «Shared backend ignored SIGTERM for 5s — killing its process group». Non è un rosso: le corse sono verdi, e
> la corsa successiva è ripartita pulita (28/28). Nel log del backend, 94 ms prima di «Shutting down» si chiude un
> calcolo del portafoglio di 364 stati (`2025-09-30..2026-09-28`): un calcolo pesante era ancora in corso a fine
> corsa. Non succede a ogni corsa (in `e2e_p3`, con gli stessi 18 test, non c'è). È lo stesso comportamento già
> registrato nei round precedenti (`plan-phase00PerformanceCharts.prompt.md:3548`, `:3750`, `:4212`). Va nei
> residui di S12.

> **⚠️ Fuori pista (errori di tipo fuori dai miei file):** `tsc -p tsconfig.e2e.json` segnala 4 errori già presenti:
> `asset-detail.spec.ts:1395` e `:1397`, `onboarding-tour.spec.ts:863` e `src/lib/types/files.ts:9`. I primi due sono
> nella spec di E7, di cui sono l'unico autore, ma non sono E7: li annoto per S12 e non li correggo.

### S10 — E7: annunciato e affidato (brief 08) 🔄 2026-09-28 13:12

> **Note implementazione:**
> - **Annunciato al coordinator** prima dell'edit (13:10), come chiesto: file, righe, base attesa e protocollo per i
>   rossi della coda. Con una domanda: gli errori di tipo a `asset-detail.spec.ts:1395` e `:1397` sono miei (G3,
>   `2d22130bd`, verificato con `git blame`); il brief 08 non li tocca, e senza un sì restano nei residui di S12.
> - **Riverificato sulla base `9016bb0d1`** (il merge non tocca la spec: `git diff 472f51498 9016bb0d1` vuoto; Prettier
>   pulito): la finestra accettata nasce a `:1843-1848` come `subtractDays(end, 45)..end`; il controllo a
>   `:1970-1973`; la data interna a `:1974-1978`; lo spostamento di prezzi ed eventi a `:2145-2150` e `:2159-2164`.
>   `acceptedCurrentMaxStandaloneEventDate` si legge solo lì. La coda letta (`:7595-7795`) conta `📈3` e `💰2` e
>   cerca l'etichetta del marcatore: non legge la data interna.
> - **Il rimedio, più stretto di quello di S3:** la data interna diventa `start + 1`, ricavata dalla finestra. È
>   quello che la regola vecchia dava il 17/09, l'ultimo giorno verde (finestra `2026-08-03..2026-09-17`, evento
>   `08-03` = inizio → `start + 1`), quindi la risposta sintetica ha la forma di quando il test è nato. Il controllo
>   resta, ma si ferma solo se la finestra non ha un giorno interno. `successorReadyEvents` (`:769`) non si tocca.
> - **Test-author in background** (`s10-brief08-e7`), brief in `files/s10_briefs/08-e2e-asset-detail-e7.md`: base
>   attesa 28/1 (`:486`, finestra `2026-08-14..2026-09-28`), poi il rimedio, poi la coda risvegliata con il protocollo
>   di test-triage (corregge solo le assunzioni; per difetti di prodotto, ambiente o stato condiviso si ferma), poi
>   28/28 in seriale e con `--workers 4`.
> - Candidati per un rosso della coda, da guardare per primi: `ff9038487` (il mio commit 3 di C1: sync mancante letto
>   come annullamento; la coda fa un sync FX con esito `partial`), `00d8c735b` e `daa03c0f2` di Risk (la coda
>   aggiunge `risk-rolling-volatility` da `signal-tree-group-risk`), privacy e onboarding.

### S10 — E7 completato ✅ 2026-09-28 13:52

> **Note implementazione:** il test-author (`s10-brief08-e7`, in background) ha modificato solo `asset-detail.spec.ts`:
> +12/−9, ora a `:1970-1981`.
>
> | corsa | esito | log (`/tmp/libreFolio_i_s10/`) |
> |---|---|---|
> | base | 27 passed, 1 failed a `:486`, con il messaggio del controllo per la finestra `2026-08-14..2026-09-28` | `e2e_e7_p1_baseline.log` |
> | rimedio, il solo test | 1 passed (1,2 min) | `e2e_e7_p2_1.log` |
> | finale, seriale | **28/28** (1,8 min) | `e2e_e7_final.log` |
> | finale, `--workers 4` | **28/28** (1,4 min) | `e2e_e7_final_w4.log` |
>
> - **Il rimedio, come annunciato:**
>   - via `acceptedCurrentMaxStandaloneEventDate` e la ricerca nella fixture;
>   - la data interna è `start + 1`, ricavata dalla finestra, con un commento che dice perché;
>   - il controllo si ferma solo se `start + 1 >= end` («too short to hold a strictly interior date»);
>   - `successorReadyEvents` (`:769`) non è toccato.
> - **La coda risvegliata** (61 `expect(` e 3 `expect.poll(`, ora a `:7598-7798`) è verde al primo giro: nessun rosso
>   da attribuire. I candidati annotati (`ff9038487`, Risk, privacy, onboarding) non hanno dato segni.
> - **La mia verifica:**
>   - ho letto il diff;
>   - Prettier `--check` pulito, `diff --check` pulito;
>   - `tsc -p tsconfig.e2e.json` dà solo i 4 errori noti (`tsc_e7.log`);
>   - ho ricontato i totali nei 2 log finali;
>   - porta 6157 libera.

> **⚠️ Fuori pista (lo spegnimento oltre i 5 s, contato):** il messaggio compare in 4 corse su 14 di oggi:
> `e2e_final_dashboard`, `e2e_final_w4_dashboard`, `e2e_e7_final` ed `e2e_e7_final_w4`. Non compare mai nelle corse
> broker, né nelle corse precedenti con lo stesso contenuto (`e2e_p3_dashboard`, gli stessi 18 test;
> `e2e_e7_p1_baseline`, gli stessi 28). Dipende da cosa è ancora in volo alla fine, non dai test. La ❌ del messaggio è
> fuorviante: tutte e 4 le corse sono verdi. Resta un residuo di S12; runner e backend sono del coordinator.

> **⚠️ Fuori pista (D23, deciso durante E7):** mentre E7 girava ho chiesto al developer del meno nei formatter dei
> grafici (§7, D23). Ha scelto di migrare tutti e quattro. La sonda è in `files/d23_probe/` della sessione. Esecuzione
> dopo C5, in un commit a sé.

### Decisioni del coordinator dopo l'esito (2026-09-28 13:58)

> **Note implementazione:**
> - **C5:** va bene la mia proposta, 4 commit, uno per file; la dashboard resta in un commit solo.
> - **Gli errori di tipo a `asset-detail.spec.ts:1395` e `:1397`:** sì, in un commit a sé dopo C5. Un suo messaggio
>   precedente, che diceva «prima di C5», è superato da questo.
> - **Dopo il commit di C5** il coordinator mi allinea a `dev_release2`, che ora contiene K (`7c61dd924`). Dopo il
>   merge verifico il test delle emoji con il tipo nuovo `CROWDFUND_REAL_ESTATE`, che per la regola della famiglia
>   deve avere 🤝. Poi D23b, D23 e il resto, nell'ordine già scritto.
> - **D23b** lo chiedo io al developer.
> - **Nel backlog del coordinator, fuori dal mio perimetro:** la doppia convenzione del meno (KPI e tabelle ASCII in
>   `currencyFormat.ts`) e «Shared backend ignored SIGTERM for 5s», con la causa che ho trovato: un calcolo del
>   portafoglio ancora in volo a fine corsa.

### Checkpoint C5 — pronto (2026-09-28 14:01)

> **Note implementazione:**
> - **Contenuto:** 4 commit su `9016bb0d1`, uno per file, solo test E2E e questo registro:
>
> | # | commit | percorso |
> |---|---|---|
> | 1 | brief 03, la dashboard: via i 3 test dello zoom (E1–E3) e i loro helper; E4 rimisurato; E5, E8 ed E9 senza assunzioni; il test `:130` sceglie «now»; 6 test nuovi | `frontend/e2e/portfolio/dashboard.spec.ts` |
> | 2 | brief 03, E6 | `frontend/e2e/brokers/brokers-detail.spec.ts` |
> | 3 | E7 | `frontend/e2e/assets/asset-detail.spec.ts` |
> | 4 | questo file | il journal |
>
> - **La dashboard sta in un commit solo:** le tre parti del brief (rimozioni, ri-pin e copertura nuova) condividono
>   gli helper e il commento di testa, e lo stato intermedio non è mai stato salvato né provato.
> - **Le prove per confine:** le 3 spec non si importano a vicenda, quindi ogni confine ha già la sua corsa E2E, in
>   seriale e con `--workers 4` (registri «S10 — brief 03» ed «S10 — E7 completato»). Nella copia di prova completa
>   rifaccio a ogni confine `tsc -p tsconfig.e2e.json`, Prettier sui file cambiati e l'elenco dei test di Playwright
>   (`--list`, che non avvia né il server né il setup globale).
> - **Come:** lo stesso protocollo di C1–C4: patch e messaggi, script a guardie derivato da quello di C4 con
>   sostituzioni contate, digest, dry-run in it_IT ed en_US, un clone di prova, `merge-tree`. Nessun file si divide
>   fra più commit.
> - **Esclusi:** i log in `/tmp`, `test-results/`, `playwright-report/`, la build del frontend e i file generati.
> - **Questa è l'ultima scrittura nel worktree prima del digest.** I numeri del bundle (alberi, sha256, digest)
>   dipendono da questo file, quindi qui non ci sono: li registro dopo il commit.
> - **Dopo C5:** l'allineamento a `dev_release2` con K e il controllo delle emoji; poi D23b, la domanda al developer;
>   poi D23 in un commit a sé, e gli errori di tipo in un altro.

### Checkpoint C5 — committato ✅ 2026-09-29 10:02

> **Note implementazione:**
> - **Il bundle**, costruito il 28/09 senza scrivere nel repository, sta in `/tmp/libreFolio_i_c5_commits/`, con la
>   copia nella cartella di sessione (`files/c5_commit_bundle/`). Le guardie sono quelle di C4, con HEAD `9016bb0d1`,
>   i 4 percorsi e i 4 alberi di C5. Nessun file si divide fra più commit.
>
> | verifica | come | esito |
> |---|---|---|
> | patch semplici | `git apply` in sequenza su copie di BASE, poi `cmp`, con git Apple e Homebrew | 4/4 identici, nessun file in più |
> | digest del contenuto | come in C1–C4 | `3e626783…1f26`, identico con 4 git: Apple 2.54, Homebrew 2.55, 2.53 del bundle dell'app, e ambiente vuoto in it_IT con bash 5 |
> | dry-run sul repository reale | matrice di 9 configurazioni (bash 3.2 e 5; git Apple, Homebrew e del bundle; `env -i`; it_IT ed en_US), più una dalla copia di backup | rc 0 in 9 su 9, «would commit 4/4». Fuori da `refs/copilot/` refs invariati; nessuno degli 11 oggetti propri del bundle nel repository |
> | commit veri, in 3 cloni usa-e-getta | git Homebrew con bash 3.2, git 2.53 con bash 5, git Apple in `env -i` | 9/9 PASS in ognuno; il secondo lancio è rifiutato, i commit restano 4 |
> | messaggi | `check_messages.py` | `MESSAGES OK`: subject ASCII, righe ≤ 72, niente attribuzioni AI. La scansione privacy segnala solo righe del journal già registrate come sintetiche o citazioni di controlli |
> | revisione combinata, prima del merge | `merge-tree` con `dev_release2` (`7c61dd924`) in uno store di oggetti usa-e-getta | 0 conflitti; albero `744125fb2428`. Fusi in automatico: i 4 cataloghi i18n e `_frontend_utility.py` |
>
> - sha256 dello script `ce71ab36…508c`.
> - **Il coordinator ha rifatto le verifiche da sé**, poi il developer ha committato alle 10:02 (segnale alle 10:09).
>   La mia verifica dopo il commit, in sola lettura: ogni albero è quello di `trees.txt` del bundle; ogni messaggio è
>   identico byte per byte al suo `.msg`; ogni commit tocca un file solo e ha un solo genitore, in fila su
>   `9016bb0d1`; albero di lavoro pulito e stage vuoto; porte 6157 e 6167 libere.
>
> | # | commit | subject | albero |
> |---|---|---|---|
> | 1 | `026bc20fb` | `test(dashboard): re-pin and extend chart e2e` | `04fa202bb651` |
> | 2 | `5b395204f` | `test(brokers): accept unsigned zero in P&L e2e` | `a1ecad0fd619` |
> | 3 | `f70b9c3ba` | `test(assets): derive MAX interior date from window` | `e31f73117e8f` |
> | 4 | `5e638a2ed` | `docs(journal): record S10 e2e and checkpoint C5` | `a92703eaa3f2` |

> **⚠️ Fuori pista (la prima matrice di dry-run vedeva il repository cambiare):** nella prima versione l'hash delle
> refs e il conto degli oggetti cambiavano (454 → 455). Non era lo script: durante la corsa le sessioni dell'app
> (il coordinator e altre due) scrivevano i loro checkpoint in `refs/copilot/checkpoints/…`, nello store condiviso.
> La seconda versione confronta le refs fuori da `refs/copilot/` e controlla che nessuno degli 11 oggetti propri del
> bundle (10 alberi e il blob del journal) sia entrato nel repository: invariato.
> Resta un effetto innocuo di git: quando scrive un oggetto che esiste già, anche attraverso gli alternates, ne
> aggiorna la data di modifica (il file sciolto o l'intero `.pack`). Il contenuto e l'insieme degli oggetti non
> cambiano; la data conta solo per il periodo di grazia di `gc`/`prune`. Vale per ogni dry-run da C1, anche per
> quelli del coordinator. Il commento dello script («nothing written to the index, objects or refs») vale per il
> contenuto, non per le date; il testo revisionato non l'ho cambiato.

### Compiti nuovi: il margine sinistro dei grafici (2026-09-29 10:22–10:30)

> **Note implementazione:**
> - **Il developer, nella mia chat, alle 10:22**, con uno screenshot dal telefono della Crescita in P&L/Income: «In
>   mobile il grafico ha un po' troppo spazio a sinistra vuoto […] riesci a fare che tutti i grafici non hanno così
>   tanto spazio sprecato a sinistra?».
> - **La causa, nella Crescita, è una mia regressione.** `GrowthChart.svelte:1921` mette
>   `grid.left: CHART_PLOT_LEFT_PX` (52, `:449`) con `containLabel: true`: con `containLabel` il `left` è il bordo
>   esterno, e le etichette Y si disegnano dentro. Quindi 52 px restano vuoti prima delle etichette.
>   - Il valore l'ho introdotto io in `ef7cce61c` (18/09), per allineare lo strato sopra il grafico; prima era `'3%'`.
>   - È superato da `e7773a143` (21/09, fetta del round 3): da allora lo strato legge il bordo misurato, `plotLeftPx`
>     (`:1662`, `:2211`).
> - **Gli altri 12 componenti ECharts, letti:**
>
> | componente | margine sinistro | esito |
> |---|---|---|
> | `PerformanceChart` | 4 su telefono; 260 su desktop, voluto | a posto |
> | `AllocationHistoryChart` | `'3%'` | a posto |
> | `PriceChartFull`, `CandlestickChart`, `LineChart` | 10 (o 5) con `containLabel` | a posto |
> | torte, ciambella, mappa, treemap | nessun asse cartesiano | — |
> | `CorrelationHeatmap` | calcolato dalle etichette | a posto |
> | `scatterChartHelpers.ts:208` | 64 con `containLabel` | stesso difetto; lo usano `AssetSetRiskReturnSection` e `L3RiskAdjusted` |
> | `LotComparisonChart.svelte:1158` | 24 con `containLabel` | stesso difetto |
> | `LotGanttChart` / `LotWacPriceChart` | `GRID_LEFT_PX = 56`, senza `containLabel` | allineati fra loro, da misurare |
>
> - **La decisione del developer** (con `ask_user`): per la Crescita **`'3%'`**, come prima del 18/09 e come
>   l'Allocazione.
> - **L'assegnazione del coordinator (10:30):**
>   - la Crescita: `'3%'` in un commit a sé dopo `:1395`/`:1397`, con un caso unit del test-author;
>   - **i tre grafici dei lotti sono miei** (nessun ramo attivo li tocca). Un commit a sé dopo la Crescita.
>     `LotComparisonChart`: si corregge il valore. La coppia Gantt/WAC: **prima si misura**, si cambia solo se lo spazio
>     sprecato è misurato, e i due grafici restano allineati. I test li scrive il test-author, dove un test fissa il
>     margine;
>   - **`scatterChartHelpers.ts` è di A** (tabella dei proprietari del giro della UI, approvata dal developer): lo
>     porta il coordinator nel giro della UI tramite Risk, con la mia misura (64 px vuoti);
>   - **l'ordine dopo il merge:** gate → emoji → `:1395`/`:1397` → margine della Crescita → margine dei lotti → D23b.
> - **La mia risposta sui lotti (letti senza modifiche):**
>   - `LotComparisonChart` va a **10 px**, la convenzione dei grafici con `containLabel`. `'3%'` su un desktop largo
>     1000 px darebbe 30 px, più dei 24 di oggi.
>   - Il Gantt non disegna etichette Y (`axisLabel.show: false` nelle due griglie): i suoi 56 px servono solo ad
>     allinearlo al WAC. Nel WAC le etichette vengono da `formatAxisNumber` (`lotChartShared.ts:78-85`): al massimo 6
>     caratteri (`999.99`, `123.4K`), o interi con `%`. Con gli 8 px di ECharts fra etichetta e asse fanno circa 48 px:
>     il gioco nel caso peggiore è di circa 8 px. Il Gantt ha `min-w-[720px]`: su telefono scorre in orizzontale.
>   - La misura: una sonda non committata nella 6157, sul pannello dei lotti del broker a 375 e 1280 px, in modalità
>     assoluta e %, confrontando la prima colonna disegnata della tela del WAC con 56.
>   - Nessun test fissa i margini dei lotti, e non c'è un harness che registri l'opzione di questi componenti.
> - **Visto nello screenshot, e rimandato:** un'etichetta «-888» sotto lo zero, che viene dalla funzione `min`
>   dell'asse y (`:2115`). Va in S7b; lì chiedo al developer.

### Allineamento a `dev_release2` con K — merge `b2112ba61` ✅ 2026-09-29 12:37

> **Note implementazione:**
> - Lo script l'ha preparato il coordinator (`/tmp/libreFolio_merge_target_into_i3.sh`) e l'ha lanciato il developer;
>   io non ho toccato Git.
> - `b2112ba61`: genitori `5e638a2ed` (C5) e `4ce1dc35f` (`dev_release2`), albero `f275c8d109f7`, quello della
>   simulazione del coordinator. Nessun merge in corso, albero di lavoro pulito, stage vuoto.
> - **Perché l'albero non è `744125fb`, quello previsto con C5:** fra la mia previsione e il merge il target è
>   avanzato di un commit, `4ce1dc35f` («the next release is v1.2.0»), che cambia una riga di `CHANGELOG.md` e
>   nient'altro. Nel merge `CHANGELOG.md` è identico a quello del target.
> - **Cosa porta** (19 commit dal merge base `ea30d5ccf`): K, cioè la selezione del tipo a due livelli, le icone
>   composte, il tipo `CROWDFUND_REAL_ESTATE`, le correzioni dell'import (duplicati, scelte del resolver), le icone
>   dei broker e l'ordine delle righe del bulk; più le voci del CHANGELOG.
>   - Nel backend solo `models.py` (il valore nuovo dell'enum e la sua docstring) e due scenari di stress, che danno
>     uno shock al tipo nuovo. Niente in `api/`, `schemas/` o `alembic/`, né in `Pipfile*`, `package.json` o nel
>     lock: niente `npm ci`.
>   - Il runner: le 6 righe di K in `_frontend_utility.py`, in righe diverse dalle mie (`moneyRenderSites` a `:91`,
>     `PerformanceChart` e `AllocationPanel` a `:225-226`); `_frontend_asset.py` invariato (`allocationTypeEmoji` a
>     `:34`).
>   - Nessuno dei miei file cambia: la cartella `components/dashboard`, i grafici dei lotti, le tre spec E2E, `utils/privacy`.
> - `front build --debug` (prima di ogni suite che avvia il backend, come chiesto): rc 0. svelte-check 3 errori e 41
>   avvisi in 4 file, gli stessi, riga per riga, della build su `9016bb0d1`, nessuno nei miei file. L'`api sync` della
>   build non lascia file tracciati cambiati. Log in `/tmp/libreFolio_i_postmerge3/`.

### Gate sulla revisione combinata `b2112ba61` ✅ 2026-09-29 12:50

> **Note implementazione:** nella 6157 / `/tmp/librefolio-r2-i-charts`, un comando alla volta, dopo la build di
> debug. Log in `/tmp/libreFolio_i_postmerge3/` (`02_…` → `12_…`). Porta 6157 libera dopo ogni comando.
>
> | # | gate | esito | atteso |
> |---|---|---|---|
> | 1 | `api portfolio` | 55/55 | 55/55 |
> | 2 | `services roi-fifo-utils` | 507/507 | 507/507 |
> | 3 | `front-utility core-unit` | 2646/2646 su 98 file | cresciuto con K |
> | 4 | `front-utility component-unit` | 2122/2122 su 87 file | idem |
> | 5 | `front-asset asset-unit` | 460/462 su 18 file: i **2 rossi attesi** di `allocationTypeEmoji.test.ts` | i 2 rossi annunciati |
> | 6 | `vitest run …/moneyRenderSites.test.ts` | 6/6 | 6/6 |
> | 7 | E2E `front-portfolio dashboard` | 18/18 | 18 |
> | 8 | E2E `front-broker detail` | 28/28 | 28 |
> | 9 | E2E `front-asset asset-detail` | 28/28 | 28 |
> | 10 | `tsc -p tsconfig.e2e.json` | 4 errori: `asset-detail.spec.ts:1395` e `:1397` (miei), `onboarding-tour.spec.ts:863` e `files.ts:9` (estranei) | gli stessi |
>
> - I due rossi di (5) sono la regola della famiglia sul tipo nuovo di K, `CROWDFUND_REAL_ESTATE`: l'emoji non
>   c'era. Nessun altro rosso: i due noti del target (`dashboard` e `brokers-detail:710`) restano chiusi.

### Emoji di `CROWDFUND_REAL_ESTATE` ✅ 2026-09-29 12:51

> **Note implementazione:**
> - `allocationTypeEmoji.ts`: una costante `CROWDFUND_EMOJI = '🤝'`, usata da `CROWDFUND` e dal sottotipo
>   `CROWDFUND_REAL_ESTATE`, come `ETF_EMOJI` per i sottotipi ETF. Il commento ora dice la regola per tutte e due le
>   famiglie: il sottotipo prende l'emoji della famiglia.
> - `asset-unit` dopo: 462/462 (`11_asset_unit_after_emoji.log`).
> - Il test-author (brief 09, parte A) ha tolto dall'intestazione di `allocationTypeEmoji.test.ts` i numeri di riga
>   della copia da `assetTypeTables.test.ts`, invecchiati col merge di K: ora nomina i pezzi copiati (le quattro
>   costanti di percorso, `read`, `assertScraped`, `readAssetTypes`). Ha confrontato i 7 pezzi con l'originale:
>   identici byte per byte. Solo commento, 8/8.
>
> **⚠️ Fuori pista:** nel brief 09 avevo scritto che K aveva solo inserito `scrapeRecordKeys` fra i pezzi copiati.
> Sbagliato, e l'ha notato il test-author: `scrapeRecordKeys` c'era già prima del merge (primo genitore `5e638a2ed`,
> `:76`). K ha allungato l'intestazione di 13 righe, aggiunto 3 costanti di percorso e una riga di commento fra
> `MODELS_PY` e `read`, e un helper `readRecord` dopo `expectNoGaps`, sotto il blocco copiato. La modifica non
> cambia: i pezzi copiati sono intatti.

### `asset-detail.spec.ts:1395` e `:1397` — i due errori di tipo ✅ 2026-09-29 13:04

> **Note implementazione:**
> - Test-author, brief 09 parte B. Il tipo `CalendarSignalResultFixture` (`:641-678`) ha ora il membro
>   `availability`, esattamente quello che costruisce `buildCalendarResult`: 9 campi, `input_coverage` con i suoi 13.
>   I tipi seguono `SignalAvailability` e `SignalInputCoverage` di `backend/app/schemas/signals.py`. Le due firme
>   indicizzate restano.
> - Solo tipi: nessuna riga tolta, nessun cast, nessuna espressione nuova. Il JS che esce è identico.
> - `tsc`: da 4 errori a 2, i due estranei (`onboarding-tour.spec.ts:863`, `files.ts:9`).

### Margine sinistro della Crescita ✅ 2026-09-29 13:10

> **Note implementazione:**
> - `GrowthChart.svelte`: `grid.left: '3%'` con `containLabel: true`, come l'Allocazione e come prima del 18/09. La
>   costante px diventa `PLOT_LEFT_FALLBACK_PX = 52`: serve solo come bordo del grafico finché ECharts non ha fatto il
>   primo layout; poi gli strati sopra il grafico leggono `plotLeftPx` misurato. Commenti riscritti di conseguenza.
> - Test-author (brief 09, parte C): un caso nuovo in `GrowthChart.test.ts`, «GrowthChart grid left inset», che fissa
>   `grid.left === '3%'` e `containLabel === true` sulla prima vista (Valore) e su P&L/Income, la vista dello
>   screenshot. Sul prodotto di HEAD è rosso per costruzione (`52` non è mai `'3%'`). L'intestazione del file dice ora
>   «quattro» soggetti. 18/18.
> - **Misura sulla copia della produzione (6167)**, prima colonna disegnata del grafico:
>
> | larghezza | `left: 52` | `left: '3%'` |
> |---|---|---|
> | 375 | x 82.6, piano largo 214 | x 39.8, piano largo 257 |
> | 1280 | — | x 46.9, piano largo 476 |
>
> - `front build --debug` di questo stato (13:04), per la sonda e per le E2E seguenti.

### Margine sinistro dei grafici dei lotti ✅ 2026-09-29 13:30

> **Note implementazione:**
> - **La sonda** (`files/probe/libreFolio_i_margin_probe.mjs`, 6167, 5 asset con più lotti, it-IT ed en-US, 375 e
>   1280 px): prima colonna disegnata, in px dal bordo della tela.
>   - `LotComparisonChart`, `left: 24`: vuoto di 24–34 px prima delle etichette.
>   - `LotWacPriceChart`, `GRID_LEFT_PX = 56`: vuoto di 17–29 px.
>   - `LotGanttChart`: nessuna etichetta Y; le corsie partono a 46–47 px, l'asse a 53–55.
> - `LotComparisonChart.svelte`: `grid.left` **24 → 10**, con un commento sul perché (`containLabel`: il `left` è solo
>   il vuoto prima delle etichette). 10 è la convenzione dei grafici con `containLabel` (`PriceChartFull`,
>   `CandlestickChart`, `LineChart`).
> - **WAC e Gantt: il developer, con `ask_user`, sceglie «Lascia WAC e Gantt a 56 px (Consigliato)».** Il gioco del
>   WAC è di pochi px nel caso peggiore, e i due grafici restano allineati fra loro. Nessuna modifica.
> - Nessun test fissa i margini dei lotti: niente test-author per questo passo.
>
> **⚠️ Fuori pista 1 — `horizontalPadding`:** `LotComparisonChart` (`:1240`) e `LotWacPriceChart` (`:1619`) passano alla
> policy dell'asse X `horizontalPadding: 42`, che non viene dalla griglia: in `LotComparisonChart` era `24 + 18`,
> nel WAC il sinistro è 56. Lo spazio vero, etichette comprese, è circa 74 px, quindi la policy crede di avere
> circa 32 px in più e le etichette X escono un po' più fitte. Non l'ho toccato: sposta la soglia «compatta», ed è
> un comportamento che nessuno ha chiesto. Va nel backlog del coordinator.
>
> **⚠️ Fuori pista 2 — la sonda trova un crash:** durante la misura a 375 px, la pagina ha dato
> `TypeError: Cannot read properties of undefined (reading 'axisBuilder')`. Vedi la sezione seguente.

### Il crash `axisBuilder` dei grafici dei lotti — misura, decisione, rosso affidato 🔄 2026-09-29 13:34

> **Note implementazione:**
> - **Chi crasha.** Nel chunk di ECharts, solo nella copia del browser, ho messo una sonda che nomina il
>   contenitore del modello che crasha (`files/probe/libreFolio_i_axisbuilder_diag.mjs` e
>   `…_gantt_diag.mjs`; log `/tmp/libreFolio_i_axisbuilder_diag.log` e `…_gantt_diag.log`). Il modello ha **un
>   solo `xAxis` e nient'altro** (0 grid, 0 yAxis, 0 series).
> - **Il meccanismo**, uguale nei tre grafici: l'istanza non ha un'opzione completa (appena creata, o `clear()` da
>   `renderChart()` perché non c'è niente da disegnare). Il ResizeObserver calcola la policy responsiva dell'asse X;
>   se è «compatta» (larghezza utile < 480) applica una patch lazy `setOption({xAxis: {splitNumber, axisLabel}})`. Al
>   frame seguente l'asse X non ha una griglia: `CartesianAxisView.render` lancia. Origine: `2d22130bd` (17/09,
>   l'asse X responsivo).
>
> | come ci si arriva | larghezza | chi crasha | esito |
> |---|---|---|---|
> | aprire il pannello dei lotti | 375 | `lot-comparison-echart` | 3 asset su 5: una corsa |
> | filtro del Gantt su un solo stato che non lascia corsie («solo chiusi» con soli lotti aperti) | 1280 | `lot-gantt-sticky-axis` | 5 su 5 |
> | lo stesso filtro | 375 | `lot-gantt-sticky-axis` e `lot-comparison-echart` | 5 su 5 |
> | l'altro stato («solo aperti», le corsie restano) | tutte e due | — | nessun errore |
>
> - **Il Gantt è raggiungibile anche da desktop**, con un filtro normale. Senza corsie, `LotGanttChart` smonta i due
>   contenitori (`{#if chartHasData}`) e `renderChart()` fa `clear()` sull'asse; il ResizeObserver guarda ancora il
>   nodo rimosso e scatta con larghezza 0, che è «compatta». Il WAC non l'ho mai visto crashare: il suo `clear()`
>   serve un grafico senza punti nella modalità scelta. In % senza dati il componente torna all'assoluto
>   (`:1728-1731`); in assoluto vuol dire un asset senza nessun punto.
> - **La decisione del coordinator (13:30):** la correzione entra in C6, commit a sé; tutti e tre i punti con la
>   stessa cura; **prima il rosso**, un'E2E del test-author senza pageerror, poi la correzione e il verde, anche con
>   `--workers 4`. La misura sulla 6167 va bene. Nessun'altra corsia tocca `brokers-detail.spec.ts` né
>   `chartCoreHelpers.test.ts` (conferma del coordinator, 13:40).
> - **La correzione prevista** è la guardia di casa, già in `LineChart`, `PriceChartFull` e `CandlestickChart`:
>   `chartOptionSet` in `LotComparisonChart` e nel WAC, `axisOptionSet` per l'asse del Gantt su tutti e due i rami
>   del ResizeObserver. Il flag va a `false` a ogni `init`, `clear` e `dispose`, e a `true` dopo la `setOption`
>   completa.
> - **Gli altri 5 grafici con la stessa patch lazy, verificati: nessun buco.** Candlestick, Line e PriceChartFull
>   hanno già la guardia. `AllocationHistoryChart` non crea l'istanza prima dei dati. In `GrowthChart` il contenitore
>   non viene mai distrutto e non c'è `clear()`; `renderChart()` esce prima di `init` se la storia è vuota, e dopo
>   `init` la `setOption` completa arriva nella stessa chiamata: il `return` su `logicalRange` (`:1810`) è
>   irraggiungibile, perché `dates` deriva da `history` (`:472`, `:702`).
> - **Brief 10 al test-author** (`files/c6_briefs/10-lots-axisbuilder-red.md`), nella 6157, solo i due file di test:
>   - A: E2E deterministica col filtro, su desktop e a 375 px, zero pageerror;
>   - B: il percorso d'apertura a 375 px, tenendo ferma la richiesta della selezione; la tiene o la scarta lui, con
>     la ragione;
>   - C: contratto sul sorgente dei tre grafici in `chartCoreHelpers.test.ts`, l'unico che copre il WAC;
>   - prova del rosso (due giri seriali, vitest rosso sul contratto), poi si ferma.
>
> **⚠️ Fuori pista — la ricompilazione automatica (13:50–14:08).** Al primo turno il test-author non ha lanciato
> nulla nella corsia, e aveva ragione.
> - Ogni `dev.py test front-*` passa da `_ensure_frontend_build()` (`scripts/test_runner/_frontend_common.py:43`).
>   Se `check_frontend_needs_build()` (`scripts/cli_base.py:540`) trova sotto `frontend/src`, o nei file di
>   configurazione, un file più recente di `build/index.html`, ricompila **senza debug**, `api sync` compresa.
> - La build delle 13:04 era più vecchia di `GrowthChart.test.ts` e di `LotComparisonChart.svelte`, quindi non
>   aveva il margine `left: 10`.
> - Ha fatto solo i controlli che non toccano la corsia, log in `/tmp/libreFolio_i_c6/`:
>   - vitest `chartCoreHelpers.test.ts`: 144/144;
>   - tsc: solo i 2 errori noti;
>   - prettier: pulito;
>   - 6157 libera.
> - **Rimedio.** Alle 14:07 ho lanciato io `front build --debug`: rc 0, svelte-check al floor (3 errori, 41
>   warning in 4 file), `git status` identico prima e dopo. Poi `check_frontend_needs_build()` risponde `False`, e
>   il chunk costruito contiene `left: 10` di LotComparison (log `/tmp/libreFolio_i_c6/b1_front_build_debug.log`).
> - **Ordine nuovo, approvato:**
>   1. Parte 0;
>   2. A e B (`frontend/e2e/` non entra nel controllo);
>   3. rosso E2E, due giri per caso;
>   4. solo allora la parte C, che sta sotto `frontend/src`;
>   5. vitest rosso lanciato direttamente;
>   6. controlli, poi stop.
>
>   Dopo la parte C non si lanciano più corse `front-*` fino alla mia prossima `front build --debug`.
> - **Regola che resta:** prima di ogni corsa E2E, la build di debug deve essere più recente di tutto
>   `frontend/src`. Chi modifica `frontend/src` ricompila prima di rientrare nella corsia.
>
> **Stato:** rosso provato alle 14:52, correzione alle 15:01: vedi le due sezioni seguenti.

### Il crash `axisBuilder` — rosso provato ✅ 2026-09-29 14:52

> **Note implementazione** (test-author, brief 10; log in `/tmp/libreFolio_i_c6/`):
> - **Parte 0, la base:** `front-broker detail` 28/28 verde in 58,1 s (`p0_baseline.log`).
> - **Diff:** solo i suoi due file, +490 righe e nessuna tolta.
>   - `e2e/brokers/brokers-detail.spec.ts`, +350: un describe nuovo, «Lots charts axisBuilder guard», con A1
>     (desktop), A2 (375 px) e B (375 px, con la richiesta della selezione tenuta ferma).
>   - `chartCoreHelpers.test.ts`, +140: il contratto `LOT_X_AXIS_PATCH_GUARDS`, 2 × 3 casi.
> - **L'asset** è scelto in sola lettura sul mock IB: il primo, per `asset_id` crescente, con tutti i lotti aperti e
>   una storia di valore. In ogni corsa è uscito Microsoft Corporation (asset 2). Il nome e l'id finiscono nei
>   messaggi d'errore.
> - **`--workers 4` è sicuro.** Nessun test di `brokers-detail.spec.ts` scrive transazioni o lotti IB: fa solo
>   `ensureBrokerExists`. Gli altri spec `front-broker` toccano solo i propri broker.
> - **Il rosso:**
>   - 6 corse su 6 (A1, A2 e B, due giri ciascuno), ognuna con un solo pageerror,
>     `Cannot read properties of undefined (reading 'axisBuilder')` in `CartesianAxisView2.render`;
>   - fallisce alle righe `:863`, `:884` e `:919`;
>   - file intero in seriale: 31 test, 28 passano, 3 falliscono, esattamente i nuovi (`p_d1_full_file_serial.log`).
> - **La metà «confronto» di A2 è una corsa:** in 4 giri non ha mai lanciato. Per `LotComparisonChart` il pin
>   affidabile è B.
> - **Vitest:** `6 failed | 144 passed (150)`, e fallisce solo sulle asserzioni del flag (`p_d2_unit_red.log`). La
>   sua prova (`p_d2_contract_selfcheck.log`): le varianti corrette passano, quelle incomplete restano rosse.
> - **Controlli:** prettier pulito; tsc con i soli 2 errori noti; `diff --check` pulito; 6157 libera.
>
> **La mia review del diff.**
> - L'E2E usa solo `data-testid`, `aria-pressed` e `data-chart-*`. Nessuna posizione e nessun conteggio globale:
>   l'unico `toHaveCount(0)` è sulle corsie del proprio asset, con un messaggio che dice cosa è cambiato se fallisce.
> - Le attese sono condizioni, più i frame rAF approvati.
> - La richiesta tenuta ferma lascia passare quella principale e quelle dopo il rilascio.
> - Il contratto verifica tre cose:
>   - una scrittura protetta dentro `if (policy.axisLabel) {`, con `responsiveXAxisCompact = policy.compact;` subito
>     prima, fuori dalla guardia;
>   - `flag = false;` come riga successiva a ogni `init` e `clear` (per il Gantt anche a ogni `dispose`, dopo
>     `axisInstance = undefined;`);
>   - una sola `setOption` completa, seguita da `flag = true;`.

### Il crash `axisBuilder` — correzione nei tre grafici, contratto verde ✅ 2026-09-29 15:01

> **Note implementazione:**
> - **`LotComparisonChart.svelte`**:
>   - `let chartOptionSet = false;` accanto a `chartInstance`, con un commento che rimanda alla guardia di `LineChart`;
>   - nel callback del ResizeObserver, `if (chartOptionSet)` davanti alla patch lazy;
>   - in `renderChart()`: `false` dopo `init` e dopo `clear()`, `true` dopo la `setOption` completa.
> - **`LotWacPriceChart.svelte`**: le stesse quattro modifiche.
> - **`LotGanttChart.svelte`**:
>   - `let axisOptionSet = false;`;
>   - la guardia su **tutte e due** le scritture del ResizeObserver dell'asse: la patch lazy e la ricostruzione
>     compatta → larga;
>   - `false` dopo i due `clear()`, dopo `dispose` (dopo `axisInstance = undefined;`) e dopo `init`;
>   - la `setOption` completa dell'asse ora sta in `if (axisInstance) { …; axisOptionSet = true; }`, così il flag non
>     dice «opzione completa» quando l'istanza non c'è.
>   - L'istanza delle corsie non viene mai toccata dal ResizeObserver e resta senza flag.
> - **Gli altri percorsi, verificati: nessun buco.**
>   - `updateHoverDots` (`LotComparisonChart`, l'unica altra `setOption` parziale) esce subito su un grafico
>     svuotato, perché `renderChart()` riporta `lastHoverDotAxisValue` a `null` prima di ogni opzione.
>   - `syncResolutionToViewport` non ha una `setOption` sua.
> - **Esito:**
>   - vitest `chartCoreHelpers.test.ts` 150/150, prima 144 + 6 rossi (`f1_unit_green.log`);
>   - prettier `--check` pulito sui 3 file (`f1_prettier.log`).
>
> **Prossimo:** `front build --debug`, poi il verde E2E nella 6157, in seriale e con `--workers 4`, poi le sonde
> sulla 6167.

### Il crash `axisBuilder` — verde E2E e sonde sulla copia ✅ 2026-09-29 15:12

> **Note implementazione** (log in `/tmp/libreFolio_i_c6/`):
> - **`front build --debug`** alle 15:03: rc 0, svelte-check al floor (3 errori, 41 warning in 4 file),
>   `git status` identico prima e dopo. `check_frontend_needs_build()` risponde `False`, e la guardia è nei chunk
>   costruiti (`b2_front_build_debug.log`).
> - **`front-broker detail` in seriale**: 31/31 in 1,0 min; i tre test nuovi sono verdi e il runner scrive
>   «Frontend build is up to date» (`g1_e2e_serial.log`).
> - **Con `--workers 4`**: 31/31 in 38,7 s (`g2_e2e_workers4.log`).
> - **Sonda del Gantt sulla 6167**, sugli stessi 5 asset × 2 larghezze della misura (chunk di ECharts nuovo,
>   `BksFbP3h.js`, patchato 6 volte per larghezza):
>   - «solo chiusi» smonta le corsie in ogni caso (`mounted=0`);
>   - 0 LFPROBE e 0 PAGEERROR, contro le 36 righe di prima (`/tmp/libreFolio_i_axisbuilder_gantt_diag_after.log`).
> - **Sonda dei margini** (`/tmp/libreFolio_i_margin_probe2.json`, confronto in `/tmp/libreFolio_i_margin_compare.log`):
>   - pageerror da 7 (`axisBuilder` all'apertura del pannello dei lotti) a 0;
>   - Crescita, WAC e Gantt identici;
>   - il confronto dei lotti ha 14 px in meno ovunque, cioè 24 → 10, in tutte e due le larghezze e i due locali.
>   - Nota: la prima sonda girava sulla build delle 13:04, senza `left: 10`. Questo confronto è quindi anche la
>     conferma del margine sulla copia.
> - **Server 6167 fermato**; `lsof` libero su 6167 e 6157.

### Gate finale di C6 ✅ 2026-09-29 15:19

> **Note implementazione:**
> - Nella 6157 / `/tmp/librefolio-r2-i-charts`, un comando alla volta, sulla build di debug delle 15:03. Il runner
>   scrive «Frontend build is up to date» a ogni E2E.
> - Log in `/tmp/libreFolio_i_c6/gate/` e `/tmp/libreFolio_i_c6/g*_e2e_*.log`.
> - Il backend non si rilancia: C6 non tocca il backend, e `api portfolio` 55/55 e `roi-fifo-utils` 507/507 sono
>   quelli del gate delle 12:50, sullo stesso HEAD.
>
> | # | gate | esito | atteso |
> |---|---|---|---|
> | 1 | `front-utility core-unit` | 2646/2646 su 98 file | invariato |
> | 2 | `front-utility component-unit` | 2122/2122 su 87 file | invariato |
> | 3 | `front-asset asset-unit` | 468/468 su 18 file | 462 + 6 casi del contratto (`chartCoreHelpers.test.ts`); i 2 rossi delle emoji ora verdi |
> | 4 | `front-asset growth-chart-memo` | 18/18 | 18 (con il describe del margine) |
> | 5 | `vitest run …/moneyRenderSites.test.ts` | 6/6 | 6/6 |
> | 6 | E2E `front-portfolio dashboard` | 18/18 in 44,4 s | 18 |
> | 7 | E2E `front-broker detail` | 31/31 in seriale e con `--workers 4` | 28 + 3 nuovi |
> | 8 | E2E `front-asset asset-detail` | 28/28 in 1,8 min | 28 |
> | 9 | `tsc -p tsconfig.e2e.json` | 2 errori: `onboarding-tour.spec.ts:863` e `files.ts:9`, fuori dal mio perimetro | `:1395` e `:1397` spariti |
> | 10 | prettier `--check` sui 10 file del frontend | pulito | pulito |
> | 11 | `git diff --check` | pulito; nessun `.only` né `.skip` | pulito |
>
> - Porte 6157 e 6167 libere.

### Checkpoint C6 — pronto (2026-09-29 15:27)

> **Note implementazione:**
> - **Contenuto:** 6 commit su `b2112ba61`, 11 percorsi:
>
> | # | subject | contenuto | percorsi |
> |---|---|---|---|
> | 1 | `fix(dashboard): emoji for CROWDFUND_REAL_ESTATE` | 🤝 per la regola della famiglia; i 2 rossi del test ora verdi | `allocationTypeEmoji.ts`, `allocationTypeEmoji.test.ts` |
> | 2 | `test(assets): type calendar fixture availability` | `:1395` e `:1397`: solo tipi, innocui a runtime | `frontend/e2e/assets/asset-detail.spec.ts` |
> | 3 | `fix(dashboard): shrink growth chart left gutter` | `grid.left '3%'` e il caso unit del test-author (brief 09) | `GrowthChart.svelte`, `GrowthChart.test.ts` |
> | 4 | `fix(brokers): shrink lot comparison left gutter` | `left: 24` → `10`, con il commento | `LotComparisonChart.svelte` (solo il margine) |
> | 5 | `fix(brokers): stop lot chart axisBuilder crash` | la guardia nei tre grafici dei lotti; i test del test-author (brief 10) | `LotComparisonChart.svelte` (il resto), `LotWacPriceChart.svelte`, `LotGanttChart.svelte`, `frontend/e2e/brokers/brokers-detail.spec.ts`, `chartCoreHelpers.test.ts` |
> | 6 | `docs(journal): record checkpoint C6 review fixes` | questo file | il journal |
>
> - **Un file si divide fra due commit:** `LotComparisonChart.svelte`. Il commit 4 prende la copia salvata dopo il
>   margine e prima della guardia; il commit 5 aggiunge solo la guardia. `gen_states.py` lo prova (`check_split`):
>   la copia differisce da BASE solo nelle righe del margine (−1 +4); il commit 5 non tocca quelle righe; l'ultimo
>   confine è il file del worktree, byte per byte.
> - **Le prove per confine:** i commit 1–5 toccano il frontend, quindi rifaccio a ogni confine, nella copia di prova
>   completa (tutto l'albero di BASE, `node_modules` clonato, mai un link verso il worktree): svelte-check, l'intera
>   suite vitest, `tsc -p tsconfig.e2e.json`, Prettier sui 10 file e l'elenco di Playwright delle due spec (`--list`,
>   che non avvia né il server né il setup globale). Il commit 6 tocca solo il journal: il suo frontend è quello del
>   commit 5, e lo script lo verifica prima di partire.
> - **Come:** lo stesso protocollo di C1–C5. Patch e messaggi; script a guardie derivato da quello di C5, con
>   sostituzioni contate; digest; dry-run in it_IT ed en_US; un clone usa-e-getta per i commit veri; `merge-tree`
>   con `dev_release2`.
> - **Esclusi:** i log in `/tmp`, `test-results/`, `playwright-report/`, la build del frontend, i file generati e
>   le sonde nella cartella di sessione.
> - **Questa è l'ultima scrittura nel worktree prima del digest.** I numeri del bundle (alberi, sha256, digest)
>   dipendono da questo file, quindi qui non ci sono: li registro dopo il commit.
> - **Dopo C6:** D23 con D23b (un'opzione «con segno» in `fmtCurrency`, commit a sé, ri-pin via test-author); poi
>   S7 (con la parte di D21 nel prodotto, `toPositionalValue`) e S7b, S8, la verifica sulla copia, S11-finale
>   (docs-writer), S12.

### Checkpoint C6 — committato ✅ 2026-09-29 22:26

> **Note implementazione:**
> - **Il bundle**, costruito fra le 15:35 e le 15:50 senza scrivere nel repository, sta in
>   `/tmp/libreFolio_i_c6_commits/`, con la copia nella cartella di sessione (`files/c6_commit_bundle/`). Le guardie
>   sono quelle di C5, con HEAD `b2112ba61`, gli 11 percorsi e i 6 alberi di C6. Un file si divide fra due commit,
>   `LotComparisonChart.svelte` (commit 4 e 5), e `check_split` lo prova.
>
> | verifica | come | esito |
> |---|---|---|
> | patch semplici | `git apply` in sequenza su copie di BASE, poi `cmp` | 6/6 identici, nessun file in più |
> | prove per confine | nella copia di prova completa (5220 file tracciati uguali a BASE, `node_modules` clonato): svelte-check, l'intera suite vitest, `tsc -p tsconfig.e2e.json`, Prettier sui 10 file, `playwright --list` | svelte-check al floor a ogni confine (3 errori, 41 avvisi, 4 file). vitest: b0 solo i 2 rossi delle emoji (6495/6497), b1–b4 verdi, b5 6504/6504. tsc: 4 errori a b0 e b1, 2 da b2 (`:1395` e `:1397` spariti). `--list`: asset-detail 28; brokers-detail 28, 31 a b5. Per il frontend b6 = b5 (10 percorsi) |
> | digest del contenuto | come in C1–C5 | `3e053bc8…9ad6`, identico con 4 git: 2.53 del bundle dell'app, Apple 2.54, Homebrew 2.55, e ambiente vuoto in it_IT con bash 5 |
> | dry-run sul repository reale | matrice di 9 configurazioni (bash 3.2 e 5; git Apple, Homebrew e del bundle; `env -i`; it_IT ed en_US) | rc 0 in 9 su 9, «would commit 6/6». Fuori da `refs/copilot/` refs invariati; nessuno dei 35 oggetti propri del bundle nel repository |
> | commit veri, in 3 cloni usa-e-getta | git Homebrew 2.55 con bash 3.2, git 2.53 con bash 5, git Apple in `env -i` | 9/9 PASS in ognuno; il secondo lancio è rifiutato, i commit restano 6 |
> | messaggi | `check_messages.py` | `MESSAGES OK`: subject ASCII fra 46 e 48 caratteri, righe ≤ 68. La scansione privacy segnala solo 2 righe del journal, già note: la riga di D23b nella tabella delle decisioni (importi d'esempio) e una riga della verifica di C5 |
> | revisione combinata, prima del merge | `merge-tree` con `dev_release2` (`5068b706c`) in uno store di oggetti usa-e-getta | 0 conflitti; albero `c6099a997801`. Fuso in automatico: `_frontend_utility.py` |
>
> - sha256 dello script `5ea70fc3…139d`.
> - **Il developer ha committato alle 22:26** (segnale del coordinator alle 22:28). La mia verifica dopo il commit,
>   in sola lettura:
>   - 6 commit in fila su `b2112ba61`, ognuno con un solo genitore;
>   - ogni albero è quello di `trees.txt` del bundle;
>   - ogni messaggio è identico byte per byte al suo `.msg`;
>   - i 35 oggetti propri del bundle ora sono tutti nel repository (35 su 35);
>   - `merge-tree` sul HEAD reale con `5068b706c` dà ancora `c6099a997801`;
>   - albero di lavoro pulito, stage vuoto; porte 6157 e 6167 libere.
>
> | # | commit | subject | albero |
> |---|---|---|---|
> | 1 | `6d8b951bc` | `fix(dashboard): emoji for CROWDFUND_REAL_ESTATE` | `573e9a48609e` |
> | 2 | `efb1ce6c7` | `test(assets): type calendar fixture availability` | `28cdab6d2ec6` |
> | 3 | `cda9408d4` | `fix(dashboard): shrink growth chart left gutter` | `78466d2be615` |
> | 4 | `1d5975542` | `fix(brokers): shrink lot comparison left gutter` | `e95791e3555c` |
> | 5 | `0e4de83f7` | `fix(brokers): stop lot chart axisBuilder crash` | `7a2997232b76` |
> | 6 | `602ea299e` | `docs(journal): record checkpoint C6 review fixes` | `bf4a87b2a990` |

> **⚠️ Fuori pista (tre, mentre costruivo il bundle; nessuno cambia il contenuto dei commit):**
> 1. **La prima matrice di dry-run era un falso verde.** `ro_snapshot2.sh`, lo script che fotografa refs e oggetti
>    prima e dopo, non era nella cartella di lavoro del bundle. Le due fotografie erano quindi vuote, e il confronto
>    fra due file vuoti diceva «invariato». Ho copiato gli script nella cartella, ho fatto fermare la matrice su una
>    fotografia vuota e l'ho rilanciata. La corsa valida è la seconda, quella della tabella.
> 2. **`e2e_test.sh` non cancellava il suo clone**, anche se il suo commento dice di sì. L'ho cancellato a mano dopo
>    i tre giri.
> 3. **Una password su file.** Le sonde sulla copia di prod (la 6167) leggevano la password da
>    `/tmp/libreFolio_i_margin_pw` (permessi 600), contro la regola che vieta le credenziali su file. Il file è
>    cancellato; le sonde salvate in sessione contengono solo il percorso, non la password.

### Allineamento a `dev_release2` — merge `921f1fc05` ✅ 2026-09-29 22:31

> **Note implementazione:**
> - Lo script l'ha preparato il coordinator (`/tmp/libreFolio_merge_target_into_i5.sh`) e l'ha lanciato il
>   developer; io non ho toccato Git.
> - `921f1fc05`: genitori `602ea299e` (C6) e `5068b706c` (`dev_release2`), albero `c6099a997801`. È l'albero previsto
>   dal mio `merge-tree` di C6 e dalla simulazione del coordinator. Nessun merge in corso, albero di lavoro pulito,
>   stage vuoto.
> - **Cosa porta** (6 commit dal merge base `4ce1dc35f`, 34 file): i seguiti della review di K (passo 12) e i
>   registri.
>   - Le bandiere: un font solo per le bandiere, `'LF Flags'` (`app.css`, `static/lf-flags.css`, `offline.html`),
>     con il gate `src/flagFont.gate.test.ts` e l'E2E `fx-flag-font.spec.ts`.
>   - La selezione delle transazioni si svuota dopo il salvataggio (`transactions/+page.svelte`, E2E
>     `tx-selection-after-bulk.spec.ts`).
>   - Il titolo dell'app resta su ogni pagina (`(app)/+layout.svelte`). Il test passa da `layout.gate.test.ts` (da 4
>     a 2 casi) al nuovo `documentTitle.guard.test.ts` (5 casi), più l'E2E `document-title.spec.ts`.
>   - `scripts/update_js_cache.py`, con il suo test backend.
>   - Il CHANGELOG, il journal del PAC e di K, il devWiki e due file di istruzioni.
>   - Il runner: `_frontend_fx.py`, `_frontend_transaction.py` e `_frontend_utility.py` (la guardia del titolo in
>     core-unit), in righe diverse dalle mie.
> - **Le istruzioni cambiate** (`.github/copilot-instructions.md`, `frontend.instructions.md`): la faccia `'LF Flags'`
>   apre ogni pila di font, e nessuna `font-family` nomina un font di emoji. Nei miei file (la cartella
>   `components/dashboard`, i grafici dei lotti, `utils/privacy`) non c'è nessuna `font-family` né `fontFamily`:
>   nulla da adeguare.
> - **Nessuno dei miei file cambia**: la cartella `components/dashboard`, i grafici dei lotti, le tre spec E2E,
>   `chartCoreHelpers.test.ts`. Niente in `backend/app/`, `alembic/`, `Pipfile*`, `package.json` o nel lock: niente
>   `npm ci`, e i gate del backend del portafoglio non si rilanciano.

### Gate rapido sulla revisione combinata `921f1fc05` ✅ 2026-09-29 22:37

> **Note implementazione:** nella 6157 / `/tmp/librefolio-r2-i-charts`, un comando alla volta. Log in
> `/tmp/libreFolio_i_m5/` (da `01_…` a `05_…`). Alla fine porte 6157 e 6167 libere; albero di lavoro pulito prima e
> dopo.
>
> | # | gate | esito | atteso |
> |---|---|---|---|
> | 1 | `front build --debug` (22:32–22:33) | rc 0; svelte-check 3 errori e 41 avvisi in 4 file; l'`api sync` non lascia file tracciati cambiati | il floor |
> | 2 | `front-utility core-unit` | 2651/2651 su 99 file | 2646 su 98 prima del merge. I +5 casi e il file in più sono tutti di `documentTitle.guard.test.ts` (K, passo 12c), registrato in core-unit |
> | 3 | `front-utility component-unit` | 2122/2122 su 87 file | invariato. Il merge porta `layout.gate.test.ts` da 4 a 2 casi, ma quel file sta in `front_onboarding_component_unit` (`_frontend_utility.py:285`), non in component-unit |
> | 4 | `front-asset asset-unit` | 468/468 su 18 file | invariato |
> | 5 | E2E `front-portfolio dashboard` | 18/18 in 47,5 s; «Frontend build is up to date» | 18 |
>
> - A fine E2E il runner scrive «Shared backend ignored SIGTERM for 5s». È la voce già nel backlog del runner del
>   coordinator (un calcolo del portafoglio ancora in volo a fine corsa), non un rosso.
> - **Prossimo:** D23 con D23b, in un commit a sé.

### D23 + D23b — il segno del locale nei grafici ✅ 2026-09-30 00:03 (dal 2026-09-29 22:40)

> **Note implementazione (prodotto):** due file, nessun altro.
>
> - `GrowthChart.svelte`, `fmtCurrency(v, signed = false)`: il numero, segno compreso, esce da una sola chiamata
>   `toLocaleString` (`signDisplay: signed ? 'exceptZero' : 'auto'`), su `v === 0 ? 0 : v` perché `auto` scrive
>   `-0.00` per uno zero negativo. La maschera passa a `maskFormattedNumber` di J (`maskable.ts:133`), che lascia il
>   segno fuori dai `•••`.
>   - Le quattro famiglie di righe con segno (il P&L totale di Abs, `pnlRow` della linea P&L, le righe dei broker
>     nelle candele, `signedRow` dell'Income) chiamano `fmtCurrency(v, true)`, al posto del segno scritto a mano
>     prima della valuta con U+2212 fisso. Forma unica (D23b): `EUR +5,00` / `EUR -12,00`, lo zero senza segno;
>     mascherata `EUR +•••` / `EUR -•••`.
>   - Le righe OHLC restano senza segno forzato (`EUR -12,34`, col meno del locale).
> - `PerformanceChart.svelte`, `shortMoney`: il segno viene dalla stessa chiamata Intl delle cifre
>   (`signDisplay: showSign ? 'exceptZero' : 'auto'`, `-0` normalizzato), staccato con la stessa regex del segno
>   iniziale di `maskable.ts` (copiata in locale: là è privata). La riga di ritorno è identica byte per byte: in en-US
>   l'etichetta non cambia (`+€1,2K`, `-1,2K CHF`); cambia solo il glifo del meno nei locale che usano U+2212.
> - Non toccati, come deciso: gli assi (`yAxisFormatter`, `axisTickAmount`) vanno con S7b, che riscrive le stesse
>   righe; `currencyFormat.ts` (KPI e tabelle) resta ASCII, nel backlog del coordinator.
>
> | controllo | esito |
> |---|---|
> | `prettier --check` sui 2 file | pulito |
> | `front build --debug` (22:50) | rc 0; svelte-check 3 errori e 41 avvisi in 4 file, il floor; nessuno nei due file (gli errori stanno in `TransactionFormModal.test.ts` e `ToolExecutionMetrics.svelte`). Log `/tmp/libreFolio_i_d23/02_front_build_debug.log` |
> | rossi misurati prima del ri-pin (`vitest run` dei 3 file) | 3 su 30, esattamente quelli attesi: il caso S2a di `GrowthChart.test.ts:701` (asserzione `:720`: atteso `+EUR •••`, ricevuto `EUR +•••`) e i due casi del registro di `moneyRenderSites.test.ts` (riga nuova non registrata, snippet vecchio). `PerformanceChart.test.ts` è verde solo perché in en-US il meno ASCII coincide con il `-` scritto nel test. Log `/tmp/libreFolio_i_d23/01_red_before_repin.log` |
>
> **⚠️ Fuori pista (E2E):** D23b cambia anche due spec E2E mie. I pattern di `dashboard.spec.ts:376-387` e
> `brokers-detail.spec.ts:949-958` fissano la forma vecchia (`+EUR …` / `−EUR …`). In più, `brokers-detail.spec.ts:1122`
> contava le righe con segno per dire «nessuna riga P&L per broker»: con la forma unica una riga OHLC negativa e una
> riga P&L negativa sono lo stesso testo, quindi quel conteggio diventerebbe rosso a ogni candela sotto zero. Va
> sostituito con un controllo strutturale (le righe valore del tooltip sono esattamente le quattro OHLC), come già a
> `:1094`.
>
> - **Ri-pin ✅ 2026-09-29 23:37** (test-author `d23-repin`, rivisto da me riga per riga). Non ha lanciato `dev.py`:
>   le suite della corsia le lancio io.
>   - `GrowthChart.test.ts`: il caso S2a ri-pinnato (`EUR +•••` / `EUR -•••`, il meno preso dalla stessa chiamata
>     Intl); il caso «privacy off» fissa il P&L totale con segno e una riga OHLC negativa senza `+`. Un `describe`
>     nuovo (D23, D23b) percorre le quattro famiglie in 4 viste (locale della macchina e sv-SE, in chiaro e
>     mascherate), con righe intere e numero esatto di righe. Le viste sv-SE forzano `toLocaleString` e fissano
>     U+2212 come letterale: il glifo è il soggetto. Una guardia finale verifica che il giro abbia incontrato un
>     guadagno, una perdita e uno zero con segno, e una perdita senza segno.
>   - `PerformanceChart.test.ts`: `compactNet` prende il valore con segno e restituisce `{sign, digits}` dalla
>     stessa chiamata di `shortMoney`; casi 2, 3 e 6 senza segni letterali; commento del caso 6 riscritto (etichetta
>     risolta, assi a S7b, tooltip ASCII per convenzione di `currencyFormat.ts`). Un `it.each` sv-SE copre i due
>     template di `shortMoney`, con simbolo e senza.
>   - `moneyRenderSites.test.ts`: la voce di `GrowthChart.svelte:1968` ri-chiavata, `why` aggiornato; stato `masked`.
>   - E2E: i pattern di `dashboard.spec.ts` e `brokers-detail.spec.ts` alla forma nuova; `BROKER_SIGNED_AMOUNT`
>     rimosso; il controllo «nessuna riga per broker» nelle candele è ora strutturale (le righe valore sono
>     esattamente le quattro OHLC).
>   - `vitest run` dei 3 file: 36/36. `tsc -p tsconfig.e2e.json`: i 2 errori di base, fuori dai miei file.
>
> **⚠️ Fuori pista (il colore dello zero, difetto introdotto da D23b):** il test-author ha notato che una somma di
> bucket dell'Income può essere un residuo float (0,1 + 0,2 − 0,3 = 5,55e-17). Con D23b la riga stampa `EUR 0.00`
> senza segno, ma `signedValueColor` decideva ancora sul valore grezzo, e la dipingeva di verde: proprio il difetto
> «uno zero verde si legge come un guadagno» che il suo commento descrive. Prima di D23b segno e colore erano
> d'accordo (`+EUR 0.00` in verde, sbagliati tutti e due). Corretto nello stesso commit: lo zero è ciò che la riga
> stampa come zero, `Math.abs(v) < 0.005`. La sonda `/tmp/libreFolio_i_d23/probe_half_cent.mjs` lo verifica
> equivalente a «`fmtCurrency` stampa 0.00 senza segno» su 208.013 double, ±2000 ulp attorno a ±0,005 compresi: 0
> discrepanze. Il test-author aggiunge un caso relativo sul colore (residuo = zero esatto ≠ guadagno ≠ perdita).
>
> - **Non corretto, osservazione:** una riga senza segno (`signDisplay: 'auto'`) stamperebbe `-0.00` per un
>   negativo minuscolo come −0,004. Era così anche prima (`'-'` + `abs`). Non è raggiungibile: le righe senza segno
>   (OHLC e Abs) leggono livelli dall'API a due decimali, e la composizione delle candele usa primo, massimo, minimo e
>   ultimo, senza somme; il `-0.00` reale è già normalizzato. `signDisplay: 'negative'` lo risolverebbe, ma è solo
>   Intl v3 e sui motori più vecchi lancia `RangeError`.
>
> - **Caso del colore ✅ 2026-09-29 23:41** (test-author, rivisto): `GrowthChart.test.ts:1151-1198`, in fondo al
>   `describe` D23. Un render in chiaro, Income; precondizioni: l'interesse disegnato non è 0 ma stampa zero, il
>   reinvestito è uno 0 esatto, le due righe stampano lo stesso `EUR 0.00`. I colori si leggono dallo `style.color`
>   del `<b>` di ogni riga e si confrontano solo fra loro, nessun letterale esadecimale: neutro ≠ guadagno ≠ perdita,
>   poi residuo = zero esatto. Con `v === 0` il residuo prenderebbe il colore del guadagno (5,55e-17 > 0) e il caso
>   andrebbe rosso all'ultima asserzione: il test-author l'ha dimostrato seguendo il codice (il valore del tooltip è
>   lo stesso array delle serie, `ladderFlowMetric`), senza toccare il prodotto. Per farlo ha estratto
>   `tooltipRowElements` (stessa definizione di riga dei controlli di testo; `tooltipRows` restituisce ciò che
>   restituiva) e la precondizione del residuo in `expectDrawnInterestResidue()`, usata da entrambi i casi.
>   `vitest run` dei 3 file: 37/37 (GrowthChart 23, PerformanceChart 8, moneyRenderSites 6).
>
> **Corsia 6157 dopo il caso del colore** (2026-09-29 23:43–23:48), `/tmp/librefolio-r2-i-charts`, uno alla volta:
>
> | # | comando | esito | nota |
> |---|---|---|---|
> | 1 | `front build --debug` | rc 0; svelte-check 3 errori e 41 avvisi in 4 file, il floor | gli errori restano in `TransactionFormModal.test.ts:787`/`:819` e `ToolExecutionMetrics.svelte:44`; nessuno nei miei file, test compresi. Log `03_front_build_debug.log` |
> | 2 | `front-asset growth-chart-memo` | 23/23 | 18 → 23: le 4 viste D23 e il caso del colore |
> | 3 | `front-utility component-unit` | 2124/2124 su 87 file | 2122 → 2124: l'`it.each` sv-SE di `PerformanceChart.test.ts` (2 template). Il file aveva 6 casi, non 5: 6 + 2 = 8 |
> | 4 | `front-utility core-unit` | 2651/2651 su 99 file | invariato (il registro ri-chiavato, stessi casi) |
> | 5 | `front-asset asset-unit` | 468/468 su 18 file | invariato |
> | 6 | `front-portfolio dashboard` (E2E) | 18/18 | i pattern nuovi, ancorati (`^…$`): la forma vecchia `+EUR …` non passerebbe più |
> | 7 | `front-broker detail` (E2E) | 31/31 | compreso il controllo strutturale delle candele (le quattro righe OHLC e nient'altro) |
>
> `git diff --check` pulito; `prettier --check` sui 7 file frontend pulito; nessun `.only`, `.skip`, `fixme` o
> `waitForTimeout` fra le righe aggiunte; 6157 e 6167 libere. Log in `/tmp/libreFolio_i_d23/`.
>
> **⚠️ Fuori pista (il ramo compatto di `shortMoney` senza prova, osservazione 3 del test-author):** l'`it.each`
> sv-SE forza `Number.prototype.toLocaleString`, cioè solo il ramo corto (< 1000). Il ramo compatto costruisce il suo
> `Intl.NumberFormat` e la spia non lo raggiunge; nel locale della macchina un meno scritto a mano coincide col
> trattino, quindi nessun caso lo distingue. Eppure è il ramo delle etichette più comuni (`+€1,2K`). Affidato allo
> stesso test-author (23:50): una spia su `Intl.NumberFormat` che porta in sv-SE solo le chiamate senza locale, con
> guardie contro il vuoto (U+2212 nel compatto svedese; la spia chiamata con `notation: 'compact'`), etichetta intera
> in chiaro e mascherata, il suffisso svedese dentro la maschera. Dopo: `component-unit` e `front build --debug`
> di nuovo nella corsia.
>
> - **Chiuso ✅ 2026-09-29 23:58** (test-author, rivisto): in `PerformanceChart.test.ts`, un `it.each` fratello sui
>   due template, sul ramo compatto con una perdita ≥ 1000. EUR usa una fixture nuova, `EUR_LOSS_EFFECT` (−3456,78):
>   l'unica posizione EUR è un guadagno. CHF riusa la posizione esistente (−1876,54), quindi l'etichetta porta anche
>   il rendimento.
>   - `inNumberFormatLocale` spia `Intl.NumberFormat`. Solo le chiamate senza locale vanno in sv-SE; le altre passano
>     intatte. L'implementazione è una `function`, perché il prodotto chiama con `new`, e la spia si ripristina nel
>     `finally`.
>   - `RealNumberFormat` è preso prima di ogni spia e costruisce le attese: la spia non può alimentare i due lati di
>     un confronto.
>   - Due guardie contro il vuoto. Nel compatto svedese reale il segno è U+2212, e il suffisso è una parola (`tn`).
>     In chiaro e mascherata, la lettura dell'etichetta ha chiesto al locale di default un numero `compact`.
>   - Etichetta intera in chiaro (`\u2212` + simbolo o codice + cifre svedesi + suffisso) e mascherata
>     (`\u2212€•••` / `\u2212••• CHF (…)`), senza `tn`.
>   - Il commento del caso sul ramo corto ora rimanda a questo, invece di dire che il compatto non è raggiunto.
>   - Rosso per costruzione, dimostrato seguendo il codice: con un segno scritto a mano nel ramo compatto le cifre
>     diventano svedesi e il segno resta ASCII (`-€3,5 tn` contro `\u2212€3,5 tn`), in entrambi i template. Il caso
>     prende anche una maschera che inghiotte il segno, un `LEADING_SIGN` senza U+2212, una locale esplicita sulla
>     chiamata compatta (guardia) e un suffisso lasciato fuori dalla maschera.
>   - `vitest run` dei 3 file: 39/39 (GrowthChart 23, PerformanceChart 10, moneyRenderSites 6). Log
>     `/tmp/libreFolio_i_d23/ta_vitest_compact.log`.
>
> **Corsia 6157 dopo il ramo compatto** (2026-09-29 23:59 – 2026-09-30 00:03):
>
> | # | comando | esito | nota |
> |---|---|---|---|
> | 1 | `front build --debug` | rc 0; svelte-check 3 errori e 41 avvisi in 4 file, il floor | gli stessi 3 errori (`TransactionFormModal.test.ts:787`/`:819`, `ToolExecutionMetrics.svelte:44`); la tipizzazione della spia su `Intl.NumberFormat` passa. Log `12_front_build_debug.log` |
> | 2 | `front-utility component-unit` | 2126/2126 su 87 file | 2124 → 2126: i 2 casi compatti. Log `13_component_unit.log` |
>
> Le altre suite non si rilanciano: dopo la corsia delle 23:43–23:48 è cambiato solo `PerformanceChart.test.ts`, che
> gira in `component-unit`. Prodotto, specifiche E2E e registro sono gli stessi. `git diff --check` pulito;
> `prettier --check` sui 7 file frontend pulito; nessun `.only`, `.skip`, `fixme` o attesa a orologio fra le righe
> aggiunte del frontend; 6157 e 6167 libere.
>
> **Stato finale di D23 + D23b** (HEAD `921f1fc05`, non committato; 8 file):
>
> | file | cosa |
> |---|---|
> | `GrowthChart.svelte` | `fmtCurrency(v, signed)`: segno e cifre da una sola chiamata Intl, maschera con `maskFormattedNumber`; le quattro famiglie con segno la usano; `signedValueColor` decide lo zero su ciò che la riga stampa |
> | `PerformanceChart.svelte` | `shortMoney`: il segno dalla stessa chiamata Intl, in entrambi i rami |
> | `GrowthChart.test.ts` | S2a ri-pinnato; `describe` D23 (4 viste) e il caso del colore: 18 → 23 |
> | `PerformanceChart.test.ts` | casi 2, 3 e 6 ri-pinnati; sv-SE sui due rami e i due template: 6 → 10 |
> | `moneyRenderSites.test.ts` | la voce della riga del P&L totale ri-chiavata |
> | `dashboard.spec.ts`, `brokers-detail.spec.ts` | pattern alla forma nuova, ancorati; il controllo strutturale delle candele |
> | questo journal | il registro |
>
> Fuori da D23, come deciso: gli assi (`yAxisFormatter`, `axisTickAmount`) con S7b; `currencyFormat.ts` (KPI,
> tabelle, tooltip di Performance) resta ASCII, nel backlog del coordinator.

### Checkpoint C7 — pronto (2026-09-30 00:07)

> **Note implementazione:**
> - **Mandato** (coordinator, 00:05): via al bundle di C7, 2 commit come proposti, con il solito protocollo. La voce
>   di `moneyRenderSites.test.ts` va bene così: solo la mia, ri-chiavata, come concordato con J. Il `-0.00` non
>   raggiungibile va nel suo backlog.
> - **Contenuto:** 2 commit su `921f1fc05`, 8 percorsi:
>
> | # | subject | contenuto | percorsi |
> |---|---|---|---|
> | 1 | `fix(charts): follow locale sign in chart amounts` | D23 + D23b: il segno dalla stessa chiamata Intl delle cifre in `fmtCurrency` e `shortMoney`, la forma unica delle quattro righe con segno, il colore dello zero; i test ri-pinnati e nuovi, la voce del registro, i pattern E2E | `GrowthChart.svelte`, `GrowthChart.test.ts`, `PerformanceChart.svelte`, `PerformanceChart.test.ts`, `moneyRenderSites.test.ts`, `frontend/e2e/portfolio/dashboard.spec.ts`, `frontend/e2e/brokers/brokers-detail.spec.ts` |
> | 2 | `docs(journal): record C6 merge and D23` | questo file | il journal |
>
> - **Nessun file si divide fra due commit.**
> - **Le prove per confine:** il commit 1 tocca il frontend, quindi rifaccio b0 (= BASE) e b1 nella copia di prova
>   completa (tutto l'albero di BASE, `node_modules` clonato, mai un link verso il worktree): svelte-check, l'intera
>   suite vitest, `tsc -p tsconfig.e2e.json`, Prettier sui 7 file e l'elenco di Playwright delle due spec (`--list`,
>   che non avvia né il server né il setup globale). Il commit 2 tocca solo il journal: il suo frontend è quello del
>   commit 1, e lo script lo verifica prima di partire.
> - **Come:** lo stesso protocollo di C1–C6. Patch e messaggi; lo script a guardie derivato da quello di C6 (sha256
>   `5ea70fc3…139d`), con sostituzioni contate; il digest con 4 git; il dry-run in 9 configurazioni; 3 cloni
>   usa-e-getta per i commit veri; `merge-tree` con `dev_release2`.
> - **Esclusi:** i log in `/tmp`, `test-results/`, `playwright-report/`, la build del frontend, i file generati, le
>   sonde di D23 (`/tmp/libreFolio_i_d23/`, `files/d23_probe/` nella cartella di sessione).
> - **Pulizia:** `/tmp/libreFolio_i_c6_commits` (991 MB) è cancellata: C6 è committato e verificato, e la sua copia
>   sta in `files/c6_commit_bundle/` (script identico, confrontato con `cmp` prima di cancellare).
> - **Questa è l'ultima scrittura nel worktree prima del digest.** I numeri del bundle (alberi, sha256, digest)
>   dipendono da questo file, quindi qui non ci sono: li registro dopo il commit.
> - **Dopo C7:** S7 (asse dei bucket, con la parte di D21 nel prodotto, `toPositionalValue`) e S7b (tacche Y doppie,
>   gli assi di D23, «-888»); poi S8 (R11), la verifica sulla copia, S11-finale (docs-writer), S12.

### Checkpoint C7 — committato ✅ 2026-09-30 10:01

> **Note implementazione:**
> - **Il bundle**, costruito fra le 00:05 e le 00:20 senza scrivere nel repository dopo il registro «pronto», stava
>   in `/tmp/libreFolio_i_c7_commits/`, con la copia nella cartella di sessione (`files/c7_commit_bundle/`). Le
>   guardie sono quelle di C6, con HEAD `921f1fc05`, gli 8 percorsi e i 3 alberi di C7. Nessun file si divide fra
>   due commit.
>
> | verifica | come | esito |
> |---|---|---|
> | patch semplici | `git apply` in sequenza su copie di BASE, poi `cmp`, con git Homebrew e Apple | 8/8 identici ai 3 confini, nessun file in più. Patch 01: 7 file, +721 −67, sha256 `bd84e1fe…e8c8`; patch 02: +282 −5, sha256 `0da13eec…4b0e` |
> | prove per confine | nella copia di prova completa (5226 file tracciati uguali a BASE, `node_modules` clonato): svelte-check, l'intera suite vitest, `tsc -p tsconfig.e2e.json`, Prettier sui 7 file, `playwright --list` | svelte-check al floor a b0 e b1 (3 errori, 41 avvisi, 4 file). vitest: b0 6520, b1 6529 (+9: `GrowthChart.test.ts` 18 → 23, `PerformanceChart.test.ts` 6 → 10), 0 falliti. tsc: i 2 errori della base, invariati. `--list`: dashboard 18, brokers-detail 31, invariati |
> | digest del contenuto | come in C1–C6 | `ae1d9ce0…8fe4`, identico con 4 git: 2.53 del bundle dell'app, Apple 2.54, Homebrew 2.55, e ambiente vuoto in it_IT con bash 5 |
> | dry-run sul repository reale | matrice di 9 configurazioni (bash 3.2 e 5; git Apple, Homebrew e del bundle; `env -i`; it_IT ed en_US) | rc 0 in 9 su 9, «would commit 2/2». Fuori da `refs/copilot/` refs invariati; nessuno dei 7 oggetti propri del bundle nel repository |
> | commit veri, in 3 cloni usa-e-getta | git Homebrew 2.55 con bash 3.2, git 2.53 con bash 5, git Apple in `env -i` | PASS in ognuno; il secondo lancio è rifiutato, i commit restano 2; ogni clone cancellato dallo script |
> | messaggi | `check_messages.py` | `MESSAGES OK`: subject ASCII di 48 e 38 caratteri, righe ≤ 70. La scansione privacy segnala solo righe attese: importi d'esempio in EUR nei test, «token» nella `why` del registro, «password» nel registro di C6, che descrive il file cancellato |
> | revisione combinata, prima del merge | `merge-tree` con `dev_release2` (`5068b706c`) | 0 conflitti; nessuno degli 8 percorsi è toccato dal target |
>
> - sha256 dello script `485cbd92…ad58`, derivato da quello di C6 (`5ea70fc3…139d`) con sostituzioni contate.
> - **Il developer ha committato alle 10:01** (segnale del coordinator alle 10:04). La mia verifica dopo il commit,
>   in sola lettura:
>   - 2 commit in fila su `921f1fc05`, ognuno con un solo genitore, nessun merge;
>   - ogni albero è quello del bundle;
>   - ogni messaggio è identico byte per byte al suo `.msg`;
>   - gli 8 file del worktree hanno lo sha256 registrato nel bundle;
>   - i 7 oggetti propri del bundle ora sono tutti nel repository (7 su 7);
>   - `dev_release2` (`5068b706c`) è antenato di HEAD: nessun allineamento da fare;
>   - albero di lavoro pulito, stage vuoto; porte 6157 e 6167 libere, nessun processo del worktree.
>
> | # | commit | subject | albero |
> |---|---|---|---|
> | 1 | `9d8fb520b` | `fix(charts): follow locale sign in chart amounts` | `3069699e08aa` |
> | 2 | `039baea22` | `docs(journal): record C6 merge and D23` | `2b6e7b98bba9` |
>
> - **Dopo l'aggiornamento notturno dell'app** (coordinator, 10:04) ho controllato la corsia: nessun server né
>   comando rimasto a metà, le due cartelle dati intatte (suite 29/09 23:48, copia 29/09 15:12). Il test-author di
>   D23 non c'è più: l'aggiornamento ha chiuso tutti gli agenti in background. Non si perde niente, perché il suo
>   lavoro è tutto in C7; per S7 ne apro uno nuovo.
> - **Pulizia:** cancellate `/tmp/libreFolio_i_c7_commits` (967 MB), `/tmp/libreFolio_i_c4_commits` e
>   `/tmp/libreFolio_i_c5_commits`, dopo il confronto con `cmp` fra la copia in sessione e quella in `/tmp` (script,
>   digest, patch e messaggi). Cancellato anche `libreFolio_i_chunk_6.js`, una sonda di S6.
> - **Mandato** (coordinator, 10:04): «Via a S7», poi S7b, S8, la verifica sulla copia, S11-finale e S12, come da
>   piano. `front build --debug` prima della prima suite che avvia il backend.

### S7 — analisi (lettura) ✅ 2026-09-30

> **Note implementazione (sola lettura, nessun edit al prodotto):**
> - **Letto:** `GrowthChart.svelte` in tutte le zone di S7:
>   - costanti e scala `:125-260`, stato `:360-470`, costruttori dei bucket `:690-830`;
>   - dati e zoom `:960-1330`, serie, aggiornamento e render `:1330-1830`;
>   - `applyFullOption` `:1830-2170`, markup della scala `:2277-2300`.
>
>   Poi `responsiveXAxis.ts`, `timeSeriesAggregation.ts` ed ECharts 6.0.0 in `node_modules`.
> - **ECharts 6, verificato sul sorgente** (prima lo sapevo a memoria):
>   - `coord/axisTickLabelBuilder.js:166-200` (`makeCategoryTicks`). Con `interval` a funzione chiama
>     `fn(indice, etichettaGrezza)` per ogni categoria della finestra. Con `'auto'`, tick e `splitLine` prendono
>     l'intervallo delle **etichette**: è la causa B di R8, ora letta nel codice;
>   - `coord/Axis.js:238` (`fixOnBandTicksCoords`). Con `boundaryGap: true` ogni tick si sposta di mezza banda a
>     sinistra: la linea i sta sul bordo sinistro del bucket i. Il separatore di mese cade quindi al bordo del bucket
>     che contiene il 1°, come nello storyboard;
>   - `component/axis/AxisBuilder.js:647` (`fixMinMaxLabelShow`). Si salta solo con intervallo `0`. Con una
>     funzione, e `showMinLabel`/`showMaxLabel` non impostati, nasconde un'etichetta estrema solo se tocca la vicina.
>     Nessun valore forzato, come chiede D4;
>   - `component/dataZoom/AxisProxy.js:112` più `Ordinal.parse`. Su un asse category la finestra dello zoom si
>     **arrotonda** all'indice, e a 0–99 % restano tutte le categorie finché sono ≤ 50. Per l'E2E di R10 la larghezza
>     si confronta quindi esatta a 1M (13 bucket a 1A, 25 a 2A). Oltre i 50 bucket esce una categoria, e lo slot
>     cambia di 1/n.
> - **Piano di S7, passo per passo** (ognuno si registra quando è fatto):
>   - (a) **D16.** `buildLadderBuckets` si ancora alla fine: il resto `length % N` diventa il primo bucket, marcato
>     `partial` con i giorni che copre. Il numero di bucket (`ceil`) non cambia. Corpo e barra chiari, con
>     l'`itemStyle` del singolo punto. La riga del tooltip va in `buildTooltipBucketHeader`, sotto l'intestazione,
>     per candele e Proventi.
>   - (b) **Asse dei bucket.** Un modulo puro nuovo, `dashboard/growthLadderAxis.ts` (precedente:
>     `growthChartRange.ts`), con la regola di etichette e separatori di §2 R8.
>     - Lo usano i tre punti che oggi scrivono l'asse: `applyFullOption`, `updateChartData` e il resize watcher.
>     - La regola dipende dallo slot, quindi si ricalcola anche quando lo zoom cambia il numero di bucket visibili:
>       in `syncResolutionToViewport`, e solo se cambia la modalità.
>     - La larghezza delle etichette è stimata, non misurata con il canvas: jsdom non ha canvas, e il test deve
>       essere deterministico.
>     - Anno: «24 set 25» e «lug 25» se la finestra supera l'anno, e «gen 26» sempre a gennaio. È la lettura di
>       ««gen 26» a gennaio e oltre l'anno» coerente con la regola 1 e con `formatCompactXAxisDate`, che gli altri
>       grafici già usano.
>     - Diradamento dei mesi a 1/2/3/6/12, allineato al calendario. Oltre i 12 uso multipli di 12, per uno storico
>       lungo su telefono: è un'estensione della stessa regola, e la registro come nota.
>   - (c) **Proventi.** Asse category e dati posizionali, allineati ai bucket. I costi vanno in `stack: 'income'`.
>     `barCategoryGap` e `barGap` valgono `'10%'` su tutte e sei le serie, perché ECharts li condivide fra le serie a
>     barre dello stesso asse. Un gradino si offre se la colonna, slot × 0,9/3,2, è ≥ 2,0 px, con le stesse costanti
>     dell'opzione.
>   - (d) **Pulizie.** Il commento di `LADDER_MIN_BODY_PX` (la costante misura lo slot), `toPositionalValue` fuori
>     (D21a) e il docblock stantio «Batch 2 — Income submode window selector» (`:1119-1124`, D21 e).
>   - (e) **Reperto (f), confermato staticamente.**
>     - Sotto la scala `renderChart` impone `{start: 0, end: 100}`. Ogni rendering completo azzera quindi lo zoom
>       interno dell'utente: privacy, tema, resize con `renderChart(true)`, refresh dello stesso periodo, locale e
>       cambio di gradino.
>     - In più `getLogicalRangeFromChart` torna `null` sotto la scala, perché la risoluzione dei suoi dati
>       (`daily`/`weekly`) non è `currentResolution`.
>     - Il docblock di `selectCandleWidth` promette già «This does NOT move the visible range», quindi allineo il
>       prodotto a ciò che dichiara: la finestra dello zoom si ricava dalle date visibili, sui bucket della scala.
>     - Prima il rosso (test-author), poi la cura.
> - **Specchi di `chartCoreHelpers.test.ts` che S7 rompe.** Si ri-pinnano via test-author, ognuno col suo perché:
>   - resize watcher `:2076-2099`; asse di `applyFullOption` `:2102-2143`;
>   - i 6 slot dei Proventi `:2515-2574` (costi da `stack: null` a `'income'`);
>   - i letterali dell'acquisizione `:2576-2582`, che S8 cambia comunque;
>   - tooltip dei Proventi `:2853-2880`;
>   - blocco degli helper `:1916-1960`, da cui esce `toPositionalValue`;
>   - zoom sotto la scala `:1175-1200` e `:1547-1590`;
>   - `updateChartData` `:1345`, `getLogicalRangeFromChart` `:752`, `flowBlock` `:2753`;
>   - markup della scala `:3018-3045`.
>
>   Altri file leggono il componente: `GrowthChart.test.ts`, `moneyRenderSites.test.ts:193` (registro di J),
>   `timeSeriesAggregation.test.ts:509` e `candlestickChartHelpers.test.ts`.
> - **i18n.** La riga «parziale» vuole una chiave nuova, e i cataloghi sono del coordinator. Propongo
>   `chart.tooltip.partialBucket`, con `{days}` e `{total}`:
>   - en «Partial: {days} of {total} days», it «Parziale: {days} su {total} giorni»;
>   - fr «Partiel : {days} sur {total} jours», es «Parcial: {days} de {total} días».
>
>   Il plurale sta sul totale, che in un bucket parziale vale almeno 3 (il gradino 3G; 1G non ha mai un bucket
>   parziale): così «1 su 3 giorni» è corretto in ogni lingua, mentre «1 giorni su 3» non lo sarebbe. Nessuna
>   chiave esistente fa lo stesso lavoro.
>
>   Lo stile è quello delle chiavi vicine: maiuscola, due punti, spazio prima dei due punti in francese. La chiedo
>   al coordinator insieme alla misura della barra qui sotto.
>
>   **Decisione (coordinator, 2026-09-30):** la aggiungo io, in aggiunta, nei 4 cataloghi con `dev.py i18n`, nel
>   commit di S7, come in `99f7d15ec`. Testi approvati così, plurale sul totale compreso. L'unione la verifica il
>   coordinator al merge.
>
>   *Correzione del 2026-09-30:* la prima stesura diceva «almeno 7 (settimana o mese)». Il gradino 3G dà un totale
>   di 3. La scelta del plurale resta giusta.
> - **Comandi previsti** (lane 6157):
>   1. `front build --debug`;
>   2. baseline di `front-asset growth-chart-memo` e `core-unit`;
>   3. dopo gli edit, `front-utility component-unit` e di nuovo `front build --debug`;
>   4. E2E `front-portfolio dashboard`, seriale e con `--workers 4`;
>   5. `front check` al floor (3 errori, 41 avvisi).

> **Reperto nuovo, dal developer via coordinator (2026-09-30).** Nel dettaglio asset, su telefono, la barra del
> grafico del prezzo (linea/candele, Abs/%, chip «Mensile») copre l'etichetta più alta dell'asse Y («400.0%»).
> - Il componente è `PriceChartFull.svelte`: la barra è `absolute top-2 left-12 … flex-wrap … pr-24` (`:1062`), la
>   griglia `{top: 20, …, left: 10, containLabel: true}` (`:890`).
> - I miei margini di C6 non lo toccano: l'ultimo commit sul file è `2d22130bd`.
> - Lo misuro a larghezza telefono prima di metterlo nel piano. Il coordinator non vuole risposta prima della misura.

### Barra sopra il grafico del prezzo — misura ✅ 2026-09-30 10:40

> **Note implementazione**: misura sola, nessun edit di prodotto. La sovrapposizione è geometrica e **non dipende
> dalla larghezza**: la stessa in px a 320 e a 1280. Il telefono aggiunge l'andata a capo della barra.
>
> **Comandi** (lane 6157, DB sintetico):
> - server: `PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py server --test --port 6157
>   --data-dir /tmp/librefolio-r2-i-charts --no-scheduler --no-reload --host 127.0.0.1`, pronto in 6 s;
> - sonda di sessione `libreFolio_i_toolbar_probe.mjs` (Playwright da `frontend/node_modules`, mai `npx`), che
>   entra con l'utente E2E documentato e legge i rettangoli dal display list di ZRender. Tre giri:
>   1. prova: asset 6, 375 e 1280, it;
>   2. matrice: asset 6 e 1 × 3M/MAX × 360/375/390/412/768/1280 × it/en × linea/candele × Abs/% = 192 misure;
>   3. chip e FX: asset 6 e `EUR-USD` × MAX/3M × 320/340/375/1280 × it/en = 96 misure.
> - Esito: 288 misure, 0 errori di pagina. Server fermato, `lsof -nP -iTCP:6157 -sTCP:LISTEN` vuoto.
>
> **Misura** (px CSS, relativi al canvas):
> - Invarianti su tutte le 288 misure:
>   - l'etichetta più alta dell'asse Y occupa y 12,9–27,1 e finisce a `grid.x − 8` (griglia `left: 10`,
>     `containLabel`);
>   - la prima riga della barra occupa y 8–36 e parte da x = 48 (`left-12`).
>   - Quindi l'etichetta è coperta appena è larga più di 38 px, **a ogni larghezza**, desktop compreso.
> - Quanto copre:
>
>   | modo | etichetta | coperti |
>   |---|---|---|
>   | % | «500.0%» | 14,1 px |
>   | % | «120.0%», «100.0%» | 9,5 px |
>   | % | «20.0%», «15.0%» | 1,7 px |
>   | Abs | «340.00», «360.00» (asset 1) | 4,8 px |
>   | Abs | «90.0k» (34,2 px) | libera |
>   | FX `EUR-USD` | «1.12», «4.0%» (≤ 36,6 px) | libere |
>
>   Nell'FX la barra ha solo Abs/% (`disableCandlestick`), sempre a x 48. Un'etichetta FX più larga, come
>   «150.00», sarebbe coperta: è dedotto, non misurato, perché il DB sintetico non ha una coppia simile.
> - Sul telefono la barra va a capo (`flex-wrap`, e `pr-24` = 96 px riservati alla barra destra della pagina).
>   Lo spazio utile è canvas − 144.
>   - 320 e 340 (canvas 254 e 274): Abs/% scende in riga 2 (y 42–68), il chip in riga 3 (y 74–102). La riga 2
>     copre anche la seconda etichetta («90.0%», «400.0%»).
>   - Da 360 a 412 (canvas 294–346): una riga senza chip. Con il chip si va in riga 2, tranne a 412 in inglese: è
>     dedotto dalle larghezze misurate (contenuto 199–223 px contro 150–202 disponibili). «Settimanale» misura
>     81,6 px, «Weekly» 57.
>   - Sul DB sintetico il chip non compare da 360 in su: un anno di storia resta giornaliero, perché la
>     risoluzione usa `chartInstance.getWidth()`, cioè il canvas intero. Lo screenshot del developer, con
>     «Mensile», è il caso della storia lunga.
>
> **Origine**, pre-esistente dal 2026-07-30:
> - la barra (`:1062-1096`) viene da `d42a7f19d` (Risk G6, 2026-07-30);
> - la griglia (`:890`) da `aefb764ed` (2026-06-01);
> - il font di 14 px dell'etichetta da `95e91d18b` (2026-07-08), il formato da `aefb764ed`.
> - Il mio `2d22130bd` (G3) sullo stesso file aggiunge solo l'asse X responsivo.
>
> **Opzioni** (da decidere, nessuna eseguita):
> - **A. Una fascia sopra il canvas.** La barra esce dal grafico e sta in una riga con la barra destra della
>   pagina.
>   - Pro: niente di coperto, niente che si sposta.
>   - Contro: la pagina cresce di 36 px (72 quando va a capo, a ≤ 390 con il chip in italiano).
>   - Tocca `PriceChartFull` e le due pagine, dettaglio asset e FX.
> - **B. La barra agganciata al bordo del grafico.** `left` = `grid.x + 4`, letto dopo ogni render, come fa
>   `syncPlotGeometry` della Crescita.
>   - Pro: le etichette sono sempre libere, e il grafico non perde px.
>   - Contro: la barra si sposta con il bordo del grafico (13–18 px nel passaggio Abs↔%). A 360 in % va a capo
>     (124 px disponibili contro 135,8), e la riga 2 cade sul grafico.
>   - Tocca solo `PriceChartFull`.
> - **C. `grid.top` = fondo della barra + 6**, misurato con un ResizeObserver.
>   - Pro: niente di coperto.
>   - Contro: il grafico perde 22 px con una riga (−6,5%), 54 con due (−16%), 88 con tre (−26%).
>
> **⚠️ Fuori pista**:
> - **Lane.** Ho misurato nella lane della suite (6157, DB sintetico) e non sulla copia (6167), che vorrebbe le
>   credenziali del developer. La geometria non dipende dai dati, salvo la larghezza dell'etichetta, e il DB
>   sintetico la copre da 34 a 52 px.
> - **Una scrittura nel DB della suite.** Aprire il dettaglio asset aggiorna il prezzo dal vivo. L'asset 6
>   (Bitcoin) ha ora una riga del 2026-09-30, `provider:yfinance`, scritta alle 08:34 UTC e aggiornata alle 08:37.
>   - È il comportamento del prodotto, sul DB della suite.
>   - Il valore vero (83 044) cade su una serie sintetica intorno a 20 000: a 3M l'ultimo punto passa da +41% a
>     +484%, da cui l'etichetta «500.0%».
>   - Nessun'altra scrittura: `fx_rates` non ha righe di oggi.

### Barra sopra il grafico del prezzo — chiusa dal developer ✅ 2026-09-30

> **Decisione** (developer via coordinator): la barra di `PriceChartFull` è già considerata risolta, con la stessa
> soluzione della Crescita. Era una delle voci della sua lista già fatte, e va segnata completata.
> - Nessun lavoro su `PriceChartFull`, in S7 né dopo.
> - La misura qui sopra resta come nota. Il coordinator la tiene nel suo backlog con le opzioni A/B/C, nel caso la
>   voce si riapra.
> - Il fuori pista del prezzo dal vivo va nel backlog del coordinator, fra i temi di isolamento dei test. Nel DB
>   della suite l'asset 6 ha un provider vero, quindi una E2E che apre il suo dettaglio chiama la rete e sposta i
>   suoi valori.

### S7 — passo 0: etichette nelle finestre corte (D4-bis) ✅ 2026-09-30

> **Note implementazione** (sola lettura, nessun edit al prodotto):
> - Rileggendo lo storyboard di D4 contro i preset (`DateRangePicker.svelte:211-236`: 1W, 1M, MTD, WTD…) ho
>   trovato un caso che non copriva. A 1M a 1G le candele sono 31. Su un plot da telefono di 527 px lo slot è di
>   17 px, e una data di chiusura come «30 set» ne vuole circa 58. Le date di chiusura non entrano tutte, e la
>   regola del mese dà una sola etichetta, o nessuna. Oggi l'asse responsivo ne mostra diverse: sarebbe una
>   regressione. Lo stesso vale a 3G, in MTD e WTD, e per ogni zoom sotto i 2 mesi circa.
> - **Decisione del developer** (`ask_user`, testuale): «Sì, aggiungi il ripiego sulle date di chiusura diradate
>   (Raccomandato)». Registrata come addendum D4-bis in §7, e la riga S7 di §4 è aggiornata.
> - La condizione si valuta sulla regola del mese **dopo** il diradamento (1/2/3/6/12…): se nella finestra
>   visibile restano meno di 2 etichette, si passa alle date di chiusura ogni k bucket.

### S7 — passo 1: il modulo dell'asse, due regole di dettaglio ✅ 2026-09-30 18:45 (contratto e stub; il codice vero arriva dopo i rossi)

> **Note implementazione**:
> - **Un bucket con due «primi del mese» porta il mese più vecchio.** Il journal non lo fissava: lo storyboard dice
>   solo «mai una doppia». Esempio a 1M: il bucket dal 31 gen al 1 mar contiene l'1 feb e l'1 mar, ed è di fatto
>   febbraio. Porta «feb»; il bucket dopo (2–31 mar) resta vuoto, poi «apr».
>   - Con il diradamento conta il più vecchio fra i mesi **allineati**: a k=2 lo stesso bucket porta «mar», l'unico
>     allineato.
>   - Ogni primo del mese cade in un solo bucket, quindi nessun mese compare due volte. A 3M il mese più vecchio è
>     anche il primo mese intero del bucket.
> - **Nuovo modulo puro** `frontend/src/lib/components/dashboard/growthLadderAxis.ts`, sullo stile di
>   `growthChartRange.ts`:
>   - `planLadderAxis(input)` decide etichette, separatori e spostamenti ai bordi;
>   - `ladderAxisOption(plan)` li traduce in opzione ECharts, con chiave sulla stringa grezza della categoria e mai
>     sull'indice.
>
> **⚠️ Fuori pista — `containLabel` non contiene il bordo destro.** Nelle note di lavoro avevo scritto che
> `containLabel: true` passa per `layOutGridByOuterBounds`, che misura anche lo sbordo orizzontale delle etichette x.
> Per questo build è falso.
> - L'import completo di `echarts` registra `LegacyGridContainLabel` (`node_modules/echarts/index.js:261`). Il ramo
>   legacy (`lib/coord/cartesian/legacyContainLabel.js`), per l'asse orizzontale, toglie solo l'altezza delle
>   etichette.
> - Sonda SSR (solo sessione, `files/probe/libreFolio_i_s7_edge_probe.mjs`): su una tela da 340 px, «30 set»
>   centrata sull'ultima banda cade a x = 321 ed esce dalla tela di qualche px. Con D4-bis l'ultima candela porta
>   sempre un'etichetta: sul telefono l'ultima data verrebbe tagliata.
> - **Cura, dentro il modulo.** Se l'etichetta più a destra (o più a sinistra) della finestra visibile esce dallo
>   spazio fra il plot e il bordo della tela, meno 2 px di sicurezza, si sposta verso l'interno del minimo
>   necessario.
>   - Lo spostamento usa un token rich con `padding` su un solo lato. Nella sonda `padding: [0, 16, 0, 0]` sposta il
>     testo di 8 px a sinistra (`x="-8"`), ed eredita colore e corpo 14 px.
>   - Il controllo della distanza fra etichette tiene conto dello spostamento, così `fixMinMaxLabelShow` non nasconde
>     l'etichetta del bordo.
>   - Lo spazio viene dalla geometria misurata: a sinistra `plotLeftPx`, a destra
>     `larghezza − plotLeft − plotWidth`.

### D24 — la guida del Rendimento mobile: stato reale e decisione del developer ✅ 2026-09-30 11:52

> **Richiesta del coordinator (11:40, senza urgenza).** Risk ha messo un `docs_path` sul mio
> `ASSET_CALENDAR_ROLLING_RETURN`. Il plugin però è nascosto: il percorso non arriva a nessuna API, e il dettaglio
> asset non mostra il pulsante della guida. Decido io se mostrarlo e dove, eventualmente col developer.
>
> **Stato reale** (HEAD `039baea22`, sola lettura):
> - Il `docs_path` di Risk non c'è né nel mio ramo né in `dev_release2` (`3d625e703`): arriverà col merge di Risk.
>   `calendar_rolling_return.py` non lo tocco, quindi non c'è conflitto.
> - Oggi il percorso di una guida passa per questa catena:
>   - il `docs_path` del plugin;
>   - `catalog_definition()` (`base.py:111`);
>   - il catalogo, che però contiene solo i plugin `catalog_visible` (`provider_registry.py:328`);
>   - `catalogMapper.ts:133`;
>   - il `DocsLink` della lista dei segnali (`ChartSignalsSection.svelte:538-539`).
>
>   Il Rendimento mobile invece è una modalità primaria (`assets/[id]/+page.svelte:2932-2990`), non un segnale del
>   catalogo. Il suo `docs_path` non lo legge nessuno; lo controlla solo il gate dei link (`scripts/docs_links.py:66`).
> - **Precedenti.**
>   - Le KPI della dashboard portano alla guida utente, con un'ancora esplicita presente nelle 4 lingue
>     (`KpiSection.svelte:239`, `{: #card-1-period-pl }`).
>   - I grafici di Risk portano alla teoria (`ReturnHistogram.svelte:61`, `UnderwaterChart.svelte:56`).
> - **Pagine candidate.**
>   - **La guida utente** `user/assets/detail/chart.en.md:13-49`. Spiega le modalità, la finestra (preset e Custom),
>     il calcolo, il lookback, la valuta, gli stati parziale e non disponibile e la provenienza: risponde proprio alle
>     domande che il grafico pone. Le copie it/fr/es (58 righe contro 123) non hanno ancora questa sezione. È un
>     debito di traduzione che esiste già, non lo crea D24.
>   - **La teoria** `financial-theory/fundamentals/returns.en.md`, cioè la pagina di Risk. Esiste nelle 4 lingue e
>     tratta il rendimento semplice e logaritmico, il CAGR e le convenzioni sui giorni. Non dice nulla delle
>     finestre mobili né dei giorni di calendario.
>
> **Proposta (consigliata al developer):**
> - Un «?» a sola icona (`DocsLink`, 14 px) in fondo alla riga della finestra (`asset-calendar-window-controls`),
>   visibile solo in modalità Rendimento mobile, con `testId` `asset-calendar-return-docs`.
> - Porta a `user/assets/detail/chart/#rolling-return`.
>   - L'ancora esplicita sull'intestazione inglese la aggiunge il docs-writer in S11-finale, e sceglie lui su quale
>     intestazione.
>   - La sezione «Related» rimanda alla teoria per la formula.
> - L'etichetta del tooltip usa la chiave esistente `signals.riskRollingReturn.description`. Nessuna chiave nuova,
>   nessuna API, nessuna modifica al backend.
> - Il percorso è scritto come letterale nel markup, così `mkdocs check-links` lo verifica (`_DOCSLINK_PROP`,
>   `docs_links.py:61`).
> - **Conflitti.** `+page.svelte` è il file caldo condiviso con F. L'edit è additivo e sta nel blocco di G3, che è mio.
>   Prima di toccarlo chiedo al coordinator lo stato di F su quel file.
> - **Ordine.** S8b viene dopo S8 e prima della verifica sulla copia, in un commit a sé. Il test E2E va in
>   `asset-detail.spec.ts`, via test-author: il «?» è visibile solo in Rendimento mobile, e l'URL segue la lingua
>   attiva.
>
> **Decisione del developer (11:52), testuale:** «Sì: «?» in fondo alla riga della finestra, solo in Rendimento mobile,
> verso la guida utente del grafico (consigliata)».
> - **S8b**, dopo S8, in un commit a sé:
>   - il `DocsLink` nel blocco G3;
>   - l'E2E via test-author.
> - **S11-finale**, via docs-writer:
>   - l'ancora `#rolling-return` sull'intestazione inglese;
>   - il rimando «Related» alla teoria `financial-theory/fundamentals/returns`;
>   - il timbro solo se la modifica resta puntuale.
> - La traduzione della sezione in it/fr/es resta un debito del developer (pipeline Aphra). Non la avvio io.
>
> **Risposta del coordinator (2026-09-30, dopo le 11:52):**
> 1. **`assets/[id]/+page.svelte`.** Né F né A hanno commit o modifiche in corso; nemmeno Risk, D e L.
>    - **K lo toccherà a breve**, nello Step 13 approvato stamattina: `:124-127` (le icone delle schede), `:474-477`
>      (`isManualOnly` durante il caricamento) e la riga della soglia della barra.
>    - Sono righe lontane dal blocco G3 (`:2956-2990`), e la mia modifica è solo un'aggiunta. All'integrazione il
>      merge lo simula il coordinator. **S8b può procedere quando ci arrivo.**
> 2. **Il `docs_path` di Risk**: lo ricevo al merge.
> 3. **Il debito di traduzione** della sezione Rendimento mobile (it/fr/es di 58 righe contro 123): è nella lista
>    del debito di traduzione del coordinator. Il giro Aphra parte solo se lo chiede il developer.

### ⏸️ PAUSA del venv Python condiviso — due giri: 11:54–12:08 e 12:12–12:24 ✅ 2026-09-30

> **Richiesta del coordinator.** Il developer lancia `pipenv update borsa-italiana-scraping` (la correzione della
> libreria di K) nel worktree di K, e l'aggiornamento cambia il venv condiviso.
> - **Fino al RESUME** non parte nessun comando Python: niente `dev.py test`, pytest, `dev.py server` né `api sync`.
>   Il `front build --debug` e l'E2E rosso di S7 passano per `dev.py`: aspettano anche loro.
> - Possono continuare vitest, col binario del lock, e le modifiche al frontend: il brief S7 e la lettura del
>   componente.
> - **Stato al FROZEN (11:54)**: 6157 e 6167 senza listener (`lsof` vuoto), nessun processo `python`, `pytest`,
>   `uvicorn` o `dev.py` della corsia, nessuna shell attiva. Il FROZEN è stato mandato al coordinator.
> - **Durante la pausa** (solo lettura, nessun comando Python): ho riletto il componente, l'harness di
>   `GrowthChart.test.ts` e ECharts (`AxisProxy.calculateDataWindow`: sullo zoom category l'indice è
>   `Math.round(p/100 × (n−1))`). Una sonda Node sui formati `Intl` (sessione, `/tmp/libreFolio_i_s7_intl_probe.mjs`)
>   dà per it/en/fr/es: «30 set»/«Sep 30»/«30 sept.»/«30 sept»; con l'anno «24 set 25»/«Sep 24, 25»; il mese
>   «lug»/«Jul»/«juil.»/«jul»; gennaio «gen 26»/«Jan 26»/«janv. 26»/«ene 26».
>
> **▶️ RESUME (coordinator, 2026-09-30 12:08).** Il venv è aggiornato e verificato: cambia solo
> `borsa-italiana-scraping` (0.3.1 → 0.3.2), con le stesse dipendenze. I comandi Python riprendono. Al RESUME: HEAD
> `039baea22`, sporchi solo il journal e lo stub `growthLadderAxis.ts`, 6157 e 6167 libere.
> - Dopo il RESUME: `front build --debug` → EXIT 0 (`/tmp/libreFolio_i_s7/build_debug_resume.log`, 12:08-12:10).
>
> **⏸️ FREEZE, secondo giro (coordinator, 2026-09-30 12:12).** Il developer rifà l'aggiornamento con `pipenv update`
> invece della modifica a mano: cambiano borsa, `idna` e `soupsieve` nel venv condiviso. Stato al FROZEN (12:12):
> 6157 e 6167 senza listener, nessun processo `python`/`pytest`/`uvicorn`/`dev.py`/`vitest` della corsia, nessuna
> shell attiva. Il build di prima era già finito. Durante la pausa: solo lettura e il brief S7 nei file di sessione.
>
> **▶️ RESUME, secondo giro (coordinator, 2026-09-30 ~12:24).** L'aggiornamento del venv è finito e verificato; i
> comandi Python riprendono. Al RESUME (`date` 12:24:14): HEAD `039baea22`, sporchi solo il journal e lo stub
> `growthLadderAxis.ts` (`??`), 6157 e 6167 libere.
> - Il `frontend/build` di debug delle 12:08-12:10 resta valido: dopo è cambiato solo il venv Python, non il frontend.
> - **Nello stesso messaggio il coordinator riconferma D24/S8b**: nessun worktree (F, A, Risk, K, D, L, J) tocca
>   `assets/[id]/+page.svelte`. K ci arriverà più avanti, alle schede (`~:124-127`, punto 7) e a `isManualOnly`
>   (`~:474-477`, punto 6b), lontano dal blocco G3; il merge lo simula il coordinator. Il `docs_path` di Risk arriva
>   al merge; il debito di traduzione della sezione Rendimento mobile è nella lista di fine giro, e Aphra parte solo
>   se lo chiede il developer.

### S7 — passo 1, seguito: runner, sweep ridotto, punti A e B del coordinator ✅ 2026-09-30 14:13

> **Note implementazione — registrazione nel runner (approvata dal coordinator).**
> - `growthLadderAxis.test.ts` va in `front-asset asset-unit`
>   (`scripts/test_runner/_frontend_asset.py`, lista `front_asset_unit`).
> - L'aggiunta è **una** riga dopo `allocationTypeEmoji.test.ts`, più la sua voce `desc`.
> - K scrive nello stesso file, quindi resto nelle mie due righe.
> - La riga la aggiungo io, dopo la consegna del test-author. Il test-author non tocca il runner.
>
> **Note implementazione — dimensionamento dello sweep ridotto.**
> - Sonda di sessione `/tmp/libreFolio_i_s7/reduced_sweep.mjs` sul riferimento `files/s7_ref/ladderRef.mjs`, con le
>   proprietà P1/P2/P3/P4/P7/P8/P11/D4-bis/P9. Il log è `reduced_sweep.log`.
> - **La griglia:**
>   - rung `[1,3,7,30,180,365]`;
>   - finestre `[full, last30, mid50, last2, single, reversed, outOfRange]`;
>   - plot `[327,1100]`;
>   - 4 lingue;
>   - margini `{}`, `{L40,R12}`, `{L0,R0}`.
>
>   In totale **1008 casi, 0 fallimenti**.
> - **Modi:** `month/6` 161, `month/2` 168, `month/1` 135, `month/3` 31, `closing/1` 513.
>   - **`closing` con passo ≥ 2 non compare mai.** In questa griglia la proprietà d'ancora di D4-bis sarebbe vuota, quindi
>     D4-bis si copre con i casi espliciti del telefono (Ex1, passi 6–9).
> - **Altri conteggi:**
>   - `withYear` vero in 648 casi, falso in 360;
>   - spostamenti ai bordi in 61 casi: 21 ne hanno uno positivo e 52 uno negativo, e alcuni li hanno tutti e due;
>   - separatori su tutti i bucket in 744 casi, parziali in 264.
> - **Guard di non-vacuità per il brief:**
>   - ≥ 500 casi `closing/1`;
>   - ≥ 300 casi `month` con passo ≥ 2;
>   - almeno uno spostamento per segno;
>   - `withYear` presente in entrambi gli stati.
> - **Tempo.** Il riferimento senza memo ha impiegato 7475 ms, quindi il tetto di ≤ 3 s non è realistico.
>   - Il brief dà un timeout generoso (30 s) e non fissa il tempo.
>   - Il port memorizza i formatter `Intl`.
>
> **Messaggio 1 del coordinator: due punti nuovi, A e B, da fare dopo S7 e prima di S8.**
> - **A (XSS nel tooltip):** me l'aveva assegnato, poi il messaggio 2 l'ha ritirato (sotto).
> - **B: i rossi preesistenti nella corsia di K** (6155, su `8bd6be663`). I log sono
>   `/tmp/libreFolio_k13_lane_{5,8,18,19}.log`, la mia sintesi è `/tmp/libreFolio_i_s7/k13_failures.log`.
>   - **B1:** `chartCoreHelpers.test.ts`, 12 rossi.
>   - **B2:** la dashboard, 4 rossi sulla finestra di zoom.
>   - **B3:** rossi che dipendono dalla data, col puntatore al 55%: la dashboard `:467/:496/:534` e `brokers-detail:710`
>     (righe del target). Il coordinator ha chiesto di avvisarlo prima di toccare lo zero senza segno, se mi fosse
>     sembrato un difetto del prodotto.
>   - **B4:** `asset-detail.spec.ts:486`. Gli eventi della fixture sono fissi all'1–3/08, ma la finestra è oggi − 45
>     giorni.
>
> **Messaggio 2 del coordinator: A corretto.**
> - **K corregge l'XSS del GrowthChart**, con il suo test e il gate `htmlInterpolation.gate.test.ts`, che ha la
>   allow-list vuota.
> - **La mia parte.** Al primo aggiornamento della base dopo l'arrivo di K avrò un conflitto: tengo le mie righe e
>   aggiungo `escapeHtml` negli stessi punti. Nel mio ramo sono, in `GrowthChart.svelte`:
>   - `:1993`, `pnlRow(broker.brokerName)`;
>   - `:2016`, lo `<span>` delle candele;
>   - `:2060`, `buildTooltipRow(p.seriesName)` nella vista %.
>
>   Controllo anche le mie righe in più: `ohlcRow` `:2001` e il `signedRow` dei Proventi `:2031`.
> - **Regole per il codice nuovo di S7:**
>   - il contenuto dell'utente passa solo per `escapeHtml(`, importato da `$lib/utils/core/escapeHtml`, mai per un
>     `esc(` locale;
>   - una variabile che contiene HTML si chiama `…Html` o `…Badge`, una che contiene un URL `…Url` o `…Src`;
>   - un template con markup non contiene mai `name`, `notes`, `label` o `url` grezzi.
>
>   Il testo i18n del bucket parziale passa per `escapeHtml`, in `partialHtml`/`headerHtml`.
>
> **Verifica di B nella 6157, oggi, su `039baea22`.** Tutte le corse sono finite, e dopo la porta era libera (`lsof`
> vuoto). I log sono in `/tmp/libreFolio_i_s7/`.
>
> | punto | corsa | esito | log |
> |---|---|---|---|
> | B2, B3 dashboard | `front-portfolio dashboard` | **18/18** | `b2_dashboard_baseline.log`, DB `00_archive/test-db_20260930_140804.tar.xz` |
> | B1 | `front-asset asset-unit` | **468/468**, 18 file | `b1_asset_unit.log` |
> | B3 broker | `front-broker detail "GrowthChart P&L mode"` | **3/3**; `:1069` è il `:710` del target | `b3_brokers_pnl.log` |
> | B4 | `front-asset asset-detail "calendar-return primary mode"` | **1/1** a `:486` (1,2 min) | `b4_asset_detail_486.log` |
>
> - **Verdetto (test-triage): nel mio ramo non c'è nessun rosso da correggere.** La base di K contiene il cambio del
>   prodotto, `e7773a143` (antenato sia di `dev_release2` sia di `8bd6be663`). Non contiene però nessuna delle mie
>   cure dei test, verificato con `git merge-base --is-ancestor`:
>   - **B1:** `2e4c8589f` (C4, D19/D21/D22, «retire stale chart helper mirrors»). In questo ramo nessuno chiama più
>     `computeZoomWindowRange`: le sole 3 menzioni sono guard negativi, in `chartCoreHelpers.test.ts:3022-3043`.
>   - **B2 e B3 (dashboard):** `026bc20fb` (C5, il re-pin).
>   - **B3 (broker):** `5b395204f` (C5). I test contano le righe, con il segno facoltativo:
>     `PNL_AMOUNT`/`BROKER_AMOUNT` `/^[A-Z]{3}\s[+\-\u2212]?[\d.,]+$/`.
>   - **Lo zero senza segno è D23b** (`signDisplay:'exceptZero'`, deciso dal developer il 29/09, in `9d8fb520b`, C7):
>     è voluto, non è un difetto. Non serve ancorare il puntatore.
>   - **B4:** `f70b9c3ba` (C5, cioè E7): la data interna è `start + 1`, ricavata dalla finestra intercettata (registro
>     «S10 — E7 completato»).
> - **Risposta al coordinator mandata:** B si chiude con l'integrazione di I. B4 esce dal mio ordine, che torna a essere
>   S7 → S7b → S8 → S8b → la copia di prova → S11-finale → S12.
> - **Nel gate d'integrazione (S12):** `asset-unit`, la dashboard, il describe P&L dei broker, `:486`, e dopo K il suo
>   test con `htmlInterpolation.gate.test.ts`.

### S7 — passo 2: chiave i18n, pin, sonde, contratto dello stub, brief 11 e 12 ✅ 2026-09-30 18:45

> **Note implementazione — la chiave del bucket parziale.**
> - `chart.tooltip.partialBucket` nei 4 cataloghi, con `dev.py i18n add` (log `/tmp/libreFolio_i_s7/i18n_add.log`):
>   EN «Partial: {days} of {total} days», IT «Parziale: {days} su {total} giorni», FR «Partiel : {days} sur
>   {total} jours», ES «Parcial: {days} de {total} días».
> - Il testo entra nel tooltip solo attraverso `escapeHtml` (è nella lista dei gate di K: `htmlInterpolation`).
>
> **Note implementazione — sweep esteso del riferimento** (`files/s7_ref/ladderRef.mjs`, sonde in
> `files/s7_briefs/pins/`).
> - `sweep_ext.mjs`: **3168 casi, 0 fallimenti** (26 s). Con la cache di `Intl` (`sweep_ext_memo.mjs`): stessi 3168/0
>   in 2,2 s, stessi conteggi.
> - Modi: `closing/1` 1389, `month/≥2` 1054, **`closing/≥2` 144** (qui D4-bis non è più vuoto, a differenza dello
>   sweep ridotto), spostamenti al bordo 96 positivi e 169 negativi, anno sì 1800 / no 1368.
> - **Tabella ICU** (Node 26.8.2, ICU 78.3; `pins/icu_table.log`): mese corto, mese+anno, chiusura e chiusura+anno nelle
>   4 lingue. Il francese ha il punto dell'abbreviazione («sept.») e caratteri non ASCII («févr.», «août», «déc.»):
>   la stima della larghezza conta i caratteri, non i byte.
>
> **Note implementazione — come si legge un'etichetta vera** (sonda zrender, `pins/zr_probe.log`).
> - In un'etichetta rich `el.style.text` è la **stringa rich grezza** (`{edgeR5|30 set}`); il testo in chiaro sta nei
>   figli `tspan`.
> - Il rettangolo del testo è l'unione dei tspan (x 297,1, w 38,4 a corpo 14). Il riquadro vero del glifo è quindi il
>   rettangolo del tspan trasformato con `getComputedTransform()`: mai ricostruirlo dall'ancora più una larghezza,
>   perché il padding rich sposta il glifo.
> - Misura reale: circa 0,457 × corpo per carattere; la stima del modulo (0,6 × corpo) sovrastima, quindi «entra» è
>   prudente.
>
> **Note implementazione — lo zoom su un asse a categorie** (sorgente ECharts 6.0.0).
> - `AxisProxy` converte la percentuale in valore con `scale.parse`; `OrdinalScale.parse` fa `Math.round`: la finestra
>   scatta a bucket interi. Uno zoom che arrotonda a tutto l'intervallo degli indici non cambia nulla.
> - Sull'asse a bande `fixOnBandTicksCoords` aggiunge un ultimo tick con valore `extent[1] + 1`. Gli `anid`: etichette
>   `label_<tick>`, separatori `line_<tick>`, linea dell'asse `line`, tick `tick_<tick>`, minori `minor_line_<tick>`.
> - Oggi `renderChart` forza `{start: 0, end: 100}` quando `ladderActive` (`GrowthChart.svelte:1823`): ogni ridisegno
>   (per esempio la privacy) butta via lo zoom dell'utente. È il caso E3 del brief 12.
>
> **Note implementazione — lo stub `growthLadderAxis.ts`** (non tracciato, 120 righe, importato da nessuno).
> - Il docblock è il contratto dei test: bucket `(c[i-1], c[i]]`, il bucket 0 `[primo giorno, c0]`; decisioni sulla
>   finestra **visibile**; modo `closing` se tutte le chiusure visibili entrano, altrimenti `month` con k
>   1/2/3/6/12/24… allineato al calendario (gennaio porta sempre l'anno); D4-bis con ancora sull'ultimo bucket
>   (`(n-1-i) % k === 0`); anno se la finestra visibile copre ≥ 365 giorni; distanza minima 8 px; separatori su ogni
>   bucket con slot ≥ 8 px, altrimenti solo sui bucket che contengono un primo del mese; bordi spostati con il padding
>   rich `lfShift{L|R}{px}`, 2 px di sicurezza.
> - `ladderAxisOption` restituisce solo `interval`: nell'opzione vera `splitLine.show: true` resta a carico del grafico.
>
> **Note implementazione — pin e brief 11 (unit, rosso).**
> - `files/s7_briefs/11-pins.md`: i valori attesi, ricavati dal riferimento e non scritti a mano.
> - Brief 11 (`files/s7_briefs/11-s7-ladder-axis-red-unit.md`) lanciato al test-author in background verso le 18:03:
>   `growthLadderAxis.test.ts` nuovo, casi nuovi in `GrowthChart.test.ts`. Part 0: `GrowthChart.test.ts` **23/23**
>   (`/tmp/libreFolio_i_s7/p0_growth_r1.log`, 18:03).
> - `front build --debug` alle 18:02, exit 0 (`/tmp/libreFolio_i_s7/build_debug_s7.log`).
>
> **Note implementazione — brief 12 (E2E della dashboard, rosso).** Scritto in `files/s7_briefs/12-s7-ladder-e2e-red.md`,
> parte solo quando il brief 11 è finito.
> - Un describe nuovo, `GrowthChart ladder x axis (S7)`, fra quello della privacy e il docblock di S9; 5 test:
>   `S7-E1-1m`, `S7-E1-1w` (candele), `S7-E2` (Income), `S7-E3` (zoom attraverso la privacy), `S7-phone`. Da 18 a 23.
> - L'oracolo è ciò che il backend ha servito: le date di `history` dell'ultimo report con
>   `include_income_history === true`. La chiamata pigra delle candele ha quel flag a `false`
>   (`dashboard/+page.svelte:478`), e i bucket delle candele si costruiscono proprio su quelle date (`:472`, `:1014`).
> - La lettura è la scena zrender: testo in chiaro dai tspan, riquadro del glifo trasformato, `getRawIndex` come indice
>   del bucket (il `filterMode 'filter'` rinumera).
>
> **⚠️ Fuori pista — il runner ricostruisce anche per un test.** `check_frontend_needs_build`
> (`scripts/cli_base.py:540`) confronta con `build/index.html` **ogni** file sotto `frontend/src/`, test compresi. I file
> del brief 11 sono più recenti del build delle 18:02, quindi la prima suite E2E ricostruirebbe da sola, e senza
> `--debug` (`_frontend_common.py:93`). Cura: rilancio io `front build --debug` fra il brief 11 e il brief 12, e il brief
> 12 riporta qualsiasi «Frontend sources changed».
>
> **⚠️ Fuori pista — l'FYI di Risk, corretto.** Il fill-between di `buildBandSeries` cambia il contratto di
> `lineChartHelpers.test.ts` › «maps a date absent from the signal to null across all three series»: Lower
> `[0,1,2]`, Band `[10,10,10]`, middle `[5,null,7]`. Non tocco né l'helper né quel test senza dirlo prima al coordinator
> (todo `risk-bandseries-merge-note`).

### S7 — passo 3: brief 11, i rossi unit ✅ 2026-09-30 19:35

> **Note implementazione — l'esito** (test-author, agente `bce27b03`, circa 93 minuti; HEAD invariata `039baea22`).
> - `growthLadderAxis.test.ts` (nuovo, 905 righe) — Part A: **45 rossi, 10 verdi** (55), identici fra r1 e r2
>   (`/tmp/libreFolio_i_s7/a_ladder_r1.log`, `a_ladder_r2.log`). I verdi sono esattamente quelli previsti: A0 (ICU
>   nelle 4 lingue), il piano vuoto (Empty e le 4 geometrie non misurate: 0, −5, NaN, Infinity) e la stima della
>   larghezza.
> - `GrowthChart.test.ts` (+635/−9, 2008 righe) — Part B: **22 rossi nuovi, 2 verdi nuovi**; i 23 casi di prima
>   restano verdi (47: 22 rossi, 25 verdi; identici fra r1 e r2, `b_growth_r1.log`, `b_growth_r2.log`). Part 0 prima
>   di tutto: 23/23 (`p0_growth_r1.log`).
> - Ogni rosso è un `AssertionError`: nessun crash, nessun TypeError, nessun timeout di vitest. Lo sweep A10 è rosso con
>   `P4 x2808, P5 x3168, P7 x3168, P8 x1800, guard x5`.
> - `npm run check`: 3 errori, 41 avvisi, il pavimento, nessuno nei file nuovi (`check_r1.log`). Prettier pulito sui
>   due file, niente `.only`/`.skip`, 6157 libera. Verificato da me sui log.
>
> **Note implementazione — l'imbragatura della Part B.** Il finto ECharts guadagna `emit`, `setZoom` e un `getModel`
> **opt-in** (`fakeGeometry.measured`: griglia di 527 px a x 40), azzerato dopo ogni caso da un `afterEach` di file
> insieme ai timer veri. Senza di lui ogni caso di prima resta com'era: larghezza 0, tutti i gradini offerti. Fixture
> nuove da 730, 90 e 93 giorni, una istanza ciascuna (un array nuovo sarebbe da solo un reset del grafico).
>
> **Note implementazione — i due verdi nuovi della Part B.**
> - **B8 Candles** è verde oggi, e il brief lo ammetteva («non forzare il rosso»): il primo render misura la griglia
>   subito dopo l'aggiornamento completo (`GrowthChart.svelte:2131-2134`), e la riconciliazione del gradino parte solo
>   col ladder attivo (`:1821`). A 527 px su 730 giorni il 1D non si disegna, quindi l'offerta è già
>   {1W, 2W, 1M, 3M, 6M} con 1W premuto. Il difetto di B8 sta solo in Income, che oggi usa la regola delle candele e
>   tiene 1W.
> - **B11 controllo** (un periodo diverso riporta la finestra a tutto l'intervallo) è verde per costruzione: è il
>   comportamento da conservare.
>
> **Note implementazione — rossi a metà, per disegno.** In B4 e B5 la metà «niente segnato» (1D, 90 giorni, la
> settimana 5) passa già oggi; ciascun test è rosso sulla metà che si aspetta il segno. In B6 le etichette
> `Jan 5 … Feb 9` coincidono per caso con quelle dell'asse temporale di oggi: il rosso viene da `data` (null) e dalle
> due callback che ancora non esistono, sostituite da un valore segnaposto con nome (`GrowthChart.test.ts:1562`) perché
> falliscano come asserzione e non come TypeError. Quelle stringhe sono uscite di `Intl`, non traduzioni (commento WHY a
> `:1861`).
>
> **⚠️ Fuori pista — due errori nei miei brief, trovati dal test-author.** Corretti nei file di sessione con una nota
> «Erratum»:
> - `11-pins.md:250` diceva «358 giorni» per Ex5 [1..52]. P8 conta dall'inizio coperto del bucket 1, dal 2025-10-02 al
>   2026-09-30, cioè 364 giorni. Tutti e due sono sotto 365: i valori fissati non cambiano.
> - Brief 11 `:256` diceva che lo sweep fallisce solo su P4 e sulle guardie: sul piano vuoto falliscono anche P5, P7 e
>   P8. La conclusione, rosso, resta.
>
> **⚠️ Fuori pista — una deviazione del test-author, accettata.** P3, P10a e P11 dell'oracolo tollerano 1e-9 px al
> confine (`growthLadderAxis.test.ts:31-33`): i centri sono multipli in virgola mobile di plot/conteggio, e un intervallo
> che vale esattamente un intero può cadere di un pelo da una parte o dall'altra. Un miliardesimo di pixel non può
> nascondere un pixel vero. Con `EPS = 0` torna esatto.
>
> **Da fare nel passo della cura:** registrare `growthLadderAxis.test.ts` in `front_asset_unit`
> (`scripts/test_runner/_frontend_asset.py`, dopo `allocationTypeEmoji.test.ts`, con la `desc`): fino ad allora
> `check-orphans` lo segnala. I numeri di riga di `GrowthChart.test.ts` citati nel brief 11 sono quelli della HEAD.
>
> **Note implementazione — il build prima del brief 12.** `front build --debug` dalle 19:37:45 alle 19:38:57, exit 0
> (`/tmp/libreFolio_i_s7/build_debug_s7b.log`; `build/index.html` 19:38:56). Dopo, nessun file sotto `frontend/src/` è
> più recente del build, quindi il runner non ricostruisce da solo. Fino alla fine del brief 12 non tocco nulla sotto
> `frontend/src/`: la cura la preparo fuori dal worktree.

### S7 — passo 4: i rossi E2E del brief 12, la cura in laboratorio, la regola dell'ancora ✅ 2026-09-30 21:28

> **Note implementazione — brief 12, l'esito** (test-author `8b791a1f`; HEAD invariata `039baea22`).
> - Describe nuovo `GrowthChart ladder x axis (S7)` in `e2e/portfolio/dashboard.spec.ts` (`:1425`), 5 test.
> - Due corse sul solo describe, identiche (`/tmp/libreFolio_i_s7/p_red_r1.log` 20:08, `p_red_r2.log` 20:11): **4 rossi,
>   1 verde**. File intero (`p_file_r1.log`, 20:13): **19 passati + 4 falliti** = 23; i 18 di prima tutti verdi.
> - Le lettere rosse, lette nel log (sonda `[S7]` di ogni test):
>   - E1-1m: C (bucket ancorati all'inizio, `2025-10-29…` al posto di `2025-10-05…`), D (etichette ISO grezze),
>     B (separatori ogni 3 bucket, `[0,3,6,9,12,13]`), P (nessuna candela traslucida);
>   - E1-1w: C, A (`Sep` due volte, `label_48` e `label_52`), B, P;
>   - E2: T (Income su asse `time`), C, B, W (barre di 1,86 px su uno slot di 43), Z (dopo lo zoom 3–97 le barre
>     passano a 9,32 px e restano 10 bucket su 13: escono lo 0 a sinistra, l'11 e il 12 a destra);
>   - E3: Z (dopo la privacy lo zoom torna `{0, 100}`: extent `[0,12]` al posto di `[6,12]`).
> - **S7-phone è verde già oggi**: guarda solo le etichette (`Oct Feb Jun Sep`, grafico largo 309 px). Resta come guardia di non
>   regressione. Il caso telefono che la cura cambia davvero, lo zoom rado qui sotto, lo copre il nuovo E4.
> - tsc e2e: solo i 2 errori di prima (`onboarding-tour.spec.ts(863,21)`, `types/files.ts(9,23)`); prettier pulito.
>
> **Note implementazione — la cura, in laboratorio** (`/tmp/libreFolio_i_s7/fixlab/`, fuori dal worktree). Nel worktree
> resta lo stub finché il rosso di E4 non è registrato.
> - `growthLadderAxis.ts`: il pianificatore vero, al posto dello stub. Il contratto è il docblock.
> - `GrowthChart.svelte`, 14 voci (diff sulla base in `/tmp/libreFolio_i_s7/lab_growthchart.diff`: 33 hunk, +240/−121):
>   1. import del modulo;
>   2. tipi: `partial` su `BucketInfo`, `ladder` su `AggregatedResolutionData` (identità della voce, non del modo);
>   3. `buildLadderBuckets` ancorato alla fine (D16): il resto `length % N` diventa il primo bucket, con
>      `partial {days, total}`; il numero di bucket non cambia;
>   4. `PARTIAL_BUCKET_OPACITY = 0.5` sulla candela e sulle 6 serie Income del bucket parziale;
>   5. riga «Parziale» nel tooltip, per candele e Income (`chart.tooltip.partialBucket`, via `escapeHtml`);
>   6. Income: costi in `stack: 'income'`, `barGap` e `barCategoryGap` `'10%'` su tutte le serie, costanti condivise
>      con l'offerta;
>   7. offerta dei gradini: Income per colonna (`slot × 0,9/3,2 ≥ 2 px`), candele `slot ≥ 2,5 px`; tolta la dicitura
>      «PROVISIONAL», resta il perché;
>   8. un effect riconcilia il gradino quando l'offerta non lo contiene più;
>   9. `plotRightRoomPx` in `syncPlotGeometry`;
>   10. `planLadderFor`, `refreshLadderAxis` e `lastLadderPlanKey`: un `setOption({xAxis})` solo quando la chiave del
>       piano cambia; nello zoom sotto la scala prende il posto del `return` anticipato;
>   11. i tre punti che scrivono l'asse (resize watcher, `updateChartData`, `applyFullOption`): sotto la scala asse
>       category con il piano, fuori la politica `time` di prima;
>   12. `getLogicalRangeFromChart` legge anche le voci della scala;
>   13. `buildZoomWindow(entry, …)`: `renderChart` ricostruisce la finestra dalle date visibili, al posto del
>       `{0, 100}` forzato (reperto (f), E3);
>   14. pulizie: `toPositionalValue` morta, il docblock orfano «Batch 2», i commenti stantii.
> - Prettier, con la configurazione del worktree (`frontend/.prettierrc`), pulito su entrambi i file del laboratorio.
>   Il pianificatore aveva una riga vuota doppia (1 byte, 20:35).
> - Il pianificatore contro il test del brief 11, in laboratorio (`fixlab/run2.log`, 20:32): **53 verdi, 2 rossi** su
>   55. Tutti e due vengono dalla regola qui sotto: la riga A8 «Ex1 plot 40 it» e lo sweep A10 (P7 ×12).
>
> **⚠️ Fuori pista — l'ancora del separatore (affinamento del contratto di S7).**
> - ECharts 6.0.0, `coord/Axis.js:238-297` (`fixOnBandTicksCoords`), su un asse a bande con `boundaryGap`:
>   - con **un solo** tick lo sposta all'inizio dell'asse, e ne aggiunge uno alla fine;
>   - con due o più li sposta tutti di mezza banda a sinistra: ognuno sul bordo sinistro del suo bucket.
> - Dove morde: scala rada (slot < 8 px) con **un solo** 1° del mese nella finestra visibile, non sul primo bucket
>   visibile. Il separatore del mese finirebbe sul bordo sinistro del grafico, non dove comincia il mese. In pratica
>   il 1G su telefono con uno zoom di 38–61 giorni; gli altri gradini, e il desktop, hanno sempre almeno due 1° visibili.
> - Regola (a1), nel pianificatore e nel riferimento indipendente: in quel caso riceve il separatore anche il primo
>   bucket visibile. Il suo bordo sinistro è il bordo del grafico, dove una linea c'è già: a occhio non cambia nulla, e
>   con due tick ognuno torna al suo posto.
>   `ancora = rado && bucket visibili con un 1° === 1 && il primo visibile non ne ha ? vs : −1`
> - Riferimento aggiornato (`files/s7_ref/ladderRef.mjs`; la versione di prima è `ladderRef.pre-a1.mjs`). Laboratorio =
>   riferimento sui pin nuovi (`/tmp/libreFolio_i_s7/anchor_pins.log`): Ex1 plot 40 passa da `[1]` a `[0, 1]`; lo
>   sweep mette l'ancora in esattamente 12 casi (`1/last45/327/{it,en,fr,es}/{noRooms,L40R12,L0R0}`).
> - Alternativa scartata: lasciarlo come limite noto. S7 esiste proprio per mettere il separatore del mese dove comincia
>   il mese.
>
> **Note implementazione — i due seguiti al test-author** (inviati alle 21:00, in parallelo, su file diversi).
> - Unit (`bce27b03`): A8 Ex1 a `[0, 1]`; P7 dell'oracolo con l'ancora ricavata dai suoi `firsts`; un describe nuovo
>   A8-bis con 2 righe obbligatorie e 5 facoltative, letterali trascritti. Corsa **solo in laboratorio**, perché nel
>   worktree c'è ancora lo stub.
> - E2E (`8b791a1f`): **S7-E4**. Telefono 375×800, preset 3M, candele 1G, zoom su una finestra con un solo 1°, non sul
>   primo bucket. Lettera M: una sola linea interna, a ±1 px dal bordo del bucket del 1°. `openLadder` riceve `preset`,
>   la fotografia della scena riceve `lineXs`. Atteso a HEAD: precondizioni verdi e M rossa, perché oggi `splitLine`
>   segue l'intervallo delle etichette. Senza (a1) la cura darebbe 0 linee interne, con (a1) una.
> - Ordine: la cura entra in `src` solo dopo il rosso di E4 a HEAD. Un file sotto `src` più recente del build fa
>   ricostruire il runner senza `--debug` (passo 2): il brief E4 ricontrolla `find -newer` subito prima della corsa.
>
> **Note implementazione — il re-pin unit, l'esito** (test-author `bce27b03`, 21:07; verificato da me alle 21:12).
> - `growthLadderAxis.test.ts`, da 905 a 970 righe; nessun altro file toccato:
>   - A8 «Ex1 plot 40 it» ora pinna `[0, 1]`;
>   - `oracleAnchor(sc)` ricava l'ancora dai `firsts` del calendario, con lo slot calcolato come in P7 e mai dal piano.
>     La copertura conta `coverage.anchor` con la guardia `> 0`;
>   - il describe A8-bis ha 7 righe, le 2 obbligatorie e le 5 facoltative. I 21 frammenti letterali dell'addendum ci
>     sono tutti, parola per parola, compresi modo e passo di ogni riga.
> - In laboratorio (`/tmp/libreFolio_i_s7/repin_lab.log`) **62/62 verdi**, contro i 53/55 di `run2.log`. Tornano verdi
>   i due rossi dell'ancora; `repin_lab_verbose.log` elenca tutti i 62 ✓.
> - La copia del laboratorio è uguale al file del worktree (`cmp`; sha256 `80e63dfd…b21a`), e prettier è pulito.
>   Pianificatore e componente del laboratorio sono invariati (stessa ora, 20:35 e 20:27).
> - Tipi: `PinRow.fixture` è `readonly [number, string, string]`, quindi i letterali nuovi diventano tuple dal contesto.
>   La conferma arriva da `front check`, dopo la cura.
>
> **⚠️ Fuori pista — E4 bloccato su una precondizione: la dashboard apre su 3M, non su MAX** (test-author `8b791a1f`,
> 21:15; letto da me alle 21:20).
> - Premessa sbagliata, ed era mia: nel brief E4 scrivevo che la dashboard apre su MAX. Apre invece sul default dello
>   store, **3M**. `resolveInitialRange` (`src/lib/stores/dateRangeStore.svelte.ts`) guarda i parametri dell'URL, poi
>   `sessionStorage`, e alla fine usa 3M. Un contesto di test nuovo non ha né gli uni né l'altro.
> - Effetto: in `openLadder` la precondizione `date-preset-3m data-active=false` cade subito. **M non è mai stata
>   valutata** e non c'è nessuna riga `[S7] E4`. Gli altri 5 verdetti sono quelli di prima: E1-1m C,D,B,P; E1-1w
>   C,A,B,P; E2 T,C,B,W,Z; E3 Z; telefono verde (`/tmp/libreFolio_i_s7/p_red_e4_r1.log`, 5 rossi e 1 verde, 1,3 min).
> - I test 1Y funzionavano solo perché, con il default 3M, 1Y parte inattivo. Il docblock di `openLadder` ripeteva la
>   premessa sbagliata («opens on MAX»).
> - Scelta: il preset segue la regola del gradino. Si preme solo se non è già attivo.
>   - **Non attivo** (1Y): la barriera di prima resta intera.
>   - **Già attivo** (3M): nessun clic. L'oracolo è la panoramica d'apertura, registrata perché `recordReports` si
>     installa prima di `page.goto`. C'è una precondizione in più: almeno una panoramica registrata.
>   - In E4, `xData.length === n` lega già il grafico a quella lista.
> - Scartate:
>   - passare da un altro preset: una navigazione in più, e il test dipende da un secondo preset;
>   - usare i parametri dell'URL: non è il percorso di un utente.
> - Accettate come sono le 4 scelte che il test-author mi lasciava da confermare:
>   - M conta come rotta anche una linea senza x misurabile;
>   - i controlli sulle date servite vengono prima dello zoom;
>   - le fotografie E4 si stampano nel `finally`, dopo la scelta della finestra;
>   - i due slot diversi nelle fotografie.
> - Seguito inviato alle 21:22: correzione di `openLadder` e del docblock, poi la corsa
>   `front-portfolio dashboard S7-` in `p_red_e4_r2.log`. Atteso: E4 con le precondizioni verdi e **solo M** rossa.
>   Previsione per 93 giorni serviti: F = [1, 32, 63], finestra [2, 62], m = 32, 61 bucket.
>
> **Note implementazione — E4 rosso a HEAD, solo M** (test-author `8b791a1f`, corsa delle 21:23; il log l'ho verificato io
> alle 21:30).
> - `openLadder`: il preset si preme solo se non è già attivo, con la stessa regola del gradino.
>   - 1Y non è attivo: la barriera resta intera.
>   - 3M è già attivo: la precondizione è che la panoramica d'apertura sia stata registrata.
>   - In tutti e due i casi, alla fine si controlla `data-active` true.
>   - Il docblock ora dice 3M e cita `resolveInitialRange`.
>   - La spec resta un'aggiunta pura: +652 righe, 0 tolte. Prettier pulito, `diff --check` pulito.
> - tsc e2e (`tsc_e2e_r4.log`): solo i 2 errori noti.
> - Build: `find frontend/src -newer build/index.html` vuoto, quindi niente ricostruzione. Il runner dice «Frontend
>   build is up to date».
> - Esito (`/tmp/libreFolio_i_s7/p_red_e4_r2.log`, 1,3 min): **5 rossi, 1 verde**. Le lettere, rilette nel log e
>   confrontate con `p_red_e4_r1.log`, sono identiche:
>   - E1-1m: B, C, D, P;
>   - E1-1w: A, B, C, P;
>   - E2: B, C, T, W, Z;
>   - E3: Z;
>   - telefono: verde;
>   - **E4: solo M**. Tutte le precondizioni dure sono verdi.
> - La previsione, confrontata con la misura:
>   - `F = [1, 32, 63]`, `n = 93`, finestra `[2, 62]`, `m = 32` (2026-08-01) e 61 bucket visibili: **tutto come
>     previsto**;
>   - lo slot è 4,20 px, non 4,1. All'apertura su 3M l'area del grafico è larga 256,01 px e parte da x = 40,63. Su 1Y
>     partiva da x = 45,29, perché la colonna dell'asse y è più stretta.
> - Il rosso, testuale: «interior split lines at [170.5, 292.5], expected exactly one at 166.54 ± 1px».
>   - A HEAD la linea del mese cade sul bordo del bucket 33 (2026-08-02), un bucket in ritardo, a +4 px.
>   - In più c'è una linea sul bucket 62 (2026-08-31).
>   - Le due linee sui bordi del grafico (40,5 e 296,5) non contano.
>   - Con la cura e la regola (a1), i separatori sono 32 (il 1° del mese) e l'ancora 2 (il bordo sinistro). Resta una
>     sola linea interna, a 166,54.
> - Corsia: `lsof -nP -iTCP:6157 -sTCP:LISTEN` vuoto. Nessuna modifica Git, nessun file toccato oltre alla spec.
> - Prossimo: la cura entra nel worktree con `/tmp/libreFolio_i_s7/apply_fix.sh`. Lo script controlla che nel worktree
>   ci sia ancora la base del laboratorio, lo stub e la stessa copia del test.

### S7 — passo 5: la cura nel worktree, unit verdi, specchi misurati ✅ 2026-09-30 22:30

> **Note implementazione — la cura nel worktree** (21:35).
> - `/tmp/libreFolio_i_s7/apply_fix.sh` (log `apply_fix.log`). Le tre guardie passano: la base del laboratorio, lo stub
>   e la copia del test sono quelli attesi.
> - Gli sha256 sono uguali a quelli del laboratorio: `growthLadderAxis.ts` `2ac35a45e345…`, `GrowthChart.svelte`
>   `df2a41b94121…`. Il componente cambia di +239/−120.
> - Runner, con la registrazione approvata (`:3953-3960`). Solo due righe di `scripts/test_runner/_frontend_asset.py`:
>   - `:35`: `growthLadderAxis.test.ts` entra in `asset-unit`, dopo `allocationTypeEmoji.test.ts`;
>   - `:164`: la `desc` di `asset-unit` nomina il pianificatore dell'asse della scala e il suo riferimento indipendente.
>
>   `py_compile` pulito.
> - Vitest diretto su `growthLadderAxis.test.ts` e `GrowthChart.test.ts`: **109/109** (62 + 47), con tutti i B1–B11
>   verdi (`green_unit_r1.log`, `green_unit_r1_verbose.log`).
> - `dev.py front check` (`front_check_r1.log`): svelte-check dà **3 errori e 41 avvisi in 4 file**, il floor, e nessuno
>   è nei miei file. `front check` esegue solo svelte-check, non prettier: prettier `--check` l'ho lanciato io sui 9 file
>   toccati (`prettier_green_r1.log`), ed è pulito.
>
> **Note implementazione — gli specchi, misurati** (21:36).
> - Vitest diretto sui 4 file che leggono il componente (`mirrors_after_cure_r1.log`; il dettaglio dei rossi in
>   `mirrors_after_cure_r1.failures.log`): **11 rossi e 222 verdi**, tutti in `chartCoreHelpers.test.ts`.
>   `moneyRenderSites`, `timeSeriesAggregation` e `candlestickChartHelpers` sono verdi.
> - I cataloghi del runner sull'albero curato, prima del ri-pin, uno alla volta (`run_units_after_cure.out`, un log per
>   catalogo `units_cure_*.log`). Nessun server; la 6157 è libera alla fine.
>
>   | Catalogo | Esito | Floor |
>   |---|---|---|
>   | `front-asset asset-unit` | 519/530 su 19 file: **11 rossi** | 468 su 18 file + i 62 di `growthLadderAxis.test.ts` = 530 su 19 ✓ |
>   | `front-asset growth-chart-memo` | 47/47 | 47 ✓ |
>   | `front-utility core-unit` | 2651/2651 su 99 file | 2651 ✓ |
>   | `front-utility component-unit` | 2126/2126 su 87 file | 2126 (`:3515`) ✓ |
>   | `front-ai-export unit` | 342/353 su 22 file: **11 rossi** | gli stessi 11 |
>
>   I nomi dei rossi di `asset-unit` e di `ai-export unit` coincidono: il diff è vuoto.
> - **Reperto**: `chartCoreHelpers.test.ts` e `timeSeriesAggregation.test.ts` sono anche in `front-ai-export unit`
>   (`scripts/test_runner/_frontend_ai_export.py:22-23`), oltre che in `asset-unit`. Così un rosso di quei file compare
>   due volte in una corsa completa. Il catalogo è del coordinator: lo segnalo, non lo tocco.
> - Gli 11 rossi, con la voce della cura che li causa:
>
>   | Riga | Test | Cosa fissava | Voce |
>   |---|---|---|---|
>   | `:761` | falls back to the new full domain… | la guardia `activeChartData.resolution !== currentResolution` in `getLogicalRangeFromChart` | 12 |
>   | `:1200` | uses the latest live zoom… | `buildZoomWindow(currentResolution, …)` in `renderChart` | 13 |
>   | `:1341` | GrowthChart imports and applies the shared policy… (la riga di Growth dell'`it.each` sugli 8 grafici) | `...(xAxisPolicy.axisLabel ?? {})` | 11 |
>   | `:1363` | routes every GrowthChart compact-to-desktop data update… | in `updateChartData` `isCandlesSubmode`, il blocco `wasCompact` e il ternario `xAxis: isCandlesSubmode`; più la guardia di `:761` | 11, 12 |
>   | `:1577` | forces GrowthChart compact-to-desktop resize… | `buildZoomWindow(currentResolution, …)`, `xAxis: isCandlesSubmode` e il merge con `.` | 13, 11 |
>   | `:2086` | resize watcher keeps the splitNumber/axisLabel update unconditional… | `isCandlesSubmode` nel resize watcher | 11 |
>   | `:2114` | applyFullOption completes the category-vs-time xAxis ternary… | l'ancora `xAxis: isCandlesSubmode` | 11 |
>   | `:2390` | mirrors the exact buildChartUpdateSeries / buildFullSeries series-shape contract… | il `return` delle candele | 4 |
>   | `:2547` | emits exactly the 6 expected slots… | i percorsi dei dati, ora dentro `faded(...)` | 4 |
>   | `:2566` | buildFullSeries consumes seriesData[0..5]… | lo stack dei costi, `null` | 6 |
>   | `:2584` | reuses the EUR-mode capital/returns pool colors… | i due letterali delle acquisizioni, senza `...gaps` | 6 |
>
>   Le voci della cura:
>   - 4: il primo bucket parziale è sbiadito;
>   - 6: Income su 3 colonne. I costi entrano nello stack `income` e, con la regola dello stesso segno, stanno sotto lo
>     zero: `costValues` è negativo per costruzione (`GrowthChart.svelte:612-618`). Ogni serie dichiara
>     `barGap`/`barCategoryGap`;
>   - 11: la scala possiede l'asse x, e la politica responsive resta al solo asse time;
>   - 12: una voce della scala si legge a qualunque risoluzione della cascata, e i bordi della finestra si arrotondano
>     come li aggancia ECharts;
>   - 13: la finestra si calcola sulla voce attiva, quindi sotto la scala niente più `{0, 100}` forzato (E3).
> - **Fuori previsione: 2 rossi su 11.** La previsione (`:3667-3680`) ne copriva 9.
>   - `:1341`: nomina solo `updateChartData` `:1345`, il test accanto; la riga di Growth dell'`it.each` le sfugge.
>   - `:2390`: il test sta nel blocco della Linea, ma l'asserzione rossa è quella sulle candele, che la voce 4 cambia.
> - **Previsti rossi e rimasti verdi**, e perché:
>   - tooltip di Income `:2853-2880`: i pezzi che cerca con `toContain` ci sono ancora;
>   - blocco degli helper `:1916-1960`: la cura toglie `toPositionalValue` (a HEAD `GrowthChart.svelte:1229`), e il
>     ri-pin di S10 (`:1934`) non lo cercava già più;
>   - `flowBlock` `:2753` e il markup della scala `:3018-3045`: non cambiano.
> - Prossimo: il ri-pin degli 11, via test-author, nel solo `chartCoreHelpers.test.ts`. Poi di nuovo i cataloghi,
>   `front build --debug` e l'E2E.
>
> **Note implementazione — il ri-pin degli 11** (22:20).
> - Via test-author, nel solo `chartCoreHelpers.test.ts`. Il test-author del brief 11 non c'è più, quindi ne ho lanciato
>   uno nuovo (`s7-mirror-repin`) con il brief completo: gli 11 rossi, le voci della cura e la regola «si converte, non si
>   indebolisce».
> - Esito: da **11 rossi / 139 verdi / 150** (`repin_before.log`) a **150/150** (`repin_after.log`). Il conteggio non
>   cambia: nessun test aggiunto né tolto. I 6 file che leggono il componente (i 4 specchi, `GrowthChart.test.ts` e
>   `growthLadderAxis.test.ts`): **342/342** (`repin_mirrors_after.log`). Diff +142/−41.
> - prettier: una riga da riformattare, corretta dal test-author con `--write` sul solo suo file (`repin_prettier*.log`);
>   poi pulito. `git diff --check` pulito.
> - **Prova per mutazione** (del test-author, fuori dal repo: `mutation_check.mjs` e `.log`). Per i rossi 6, 7, 8 e 11 i
>   pin passano sul sorgente vero, e 7 mutazioni li fanno tornare rossi:
>   - `setOption` biforcato su `ladderActive` (6);
>   - il merge della politica che finisce sull'asse della scala, e il ramo time che lo perde (7);
>   - la dispersione per broker che torna nelle candele, e una candela che salta `toCandlestickPoint` (8);
>   - i colori delle due acquisizioni scambiati, e un colore inventato (11).
> - Cosa fissa ora ciascuno (righe dopo il ri-pin):
>
>   | Riga | Prima | Ora fissa |
>   |---|---|---|
>   | `:751` | `:761` | in `getLogicalRangeFromChart`: `const entry = activeChartData;`, la guardia che conosce la scala e quella dei bucket vuoti. La simulazione nel test prende `ladder: false` e le due guardie |
>   | `:1187` | `:1200` | `buildZoomWindow(activeData, …)` in `renderChart` |
>   | `:1354` | `:1341` | la riga di Growth: `const xAxisPolicy = ladderActive ? null : buildResponsiveXAxisPolicy({` e `...(xAxisPolicy?.axisLabel ?? {})`. Gli altri 7 grafici restano sul letterale stretto |
>   | `:1374` | `:1363` | 5 pin convertiti: il ramo `if (entry.ladder) … else` con la politica sul solo asse time; il passaggio da compatto a desktop (`applyFullOption`, poi `return`); i due `xAxis = …`, più un pin **nuovo** che `xAxis` arrivi davvero a `setOption`; la guardia nuova; `xAxis: ladderAxis ? {` |
>   | `:1596` | `:1577` | `buildZoomWindow(activeData, …)`, `xAxis: ladderAxis` e il merge con `?.` |
>   | `:2135` | `:2086` | la guardia `… && !ladderActive) {` e `axisType: 'time',`; `ladderActive` compare una volta sola |
>   | `:2169` | `:2114` | l'ancora `xAxis: ladderAxis ?`; un solo merge di `axisLabel` per ramo (politica o scala); `axisLine` 2, `splitLine` 2 |
>   | `:2427` | `:2390` | le candele: `toCandlestickPoint` su ogni punto e un solo `return`, con la serie del totale |
>   | `:2632` | `:2547` | `` dataPath: `faded(${dataPath})` `` |
>   | `:2645` | `:2566` | in `EXPECTED_SLOTS` (`:2626`) i costi hanno `stack: 'income'` |
>   | `:2675` | `:2584` | due regex, una per acquisizione: nome, slot dei dati (`[4]`, `[5]`) e colore sulla stessa riga; `...gaps` ammesso |
>
> - **Titoli rinominati** (rossi 6 e 7), perché i vecchi promettevano una garanzia che non vale più:
>   - `:2134` describe «…unconditional off the ladder»; `:2135` it «keeps the ladder out of buildResponsiveXAxisPolicy
>     (time axis only), but does not fork the actual setOption call on the submode»;
>   - `:2169` it «…merging one axisLabel source per branch, sharing the axisLine and declaring splitLine exactly once per
>     branch».
> - **Ancore in più rispetto all'uno-a-uno** (rossi 1, 3 e 4). Il codice ora è diviso su più istruzioni, e l'invariante
>   di prima si fissa solo con più di un letterale. Nessuna indebolisce un'invariante: le accetto.
> - **Commenti**: i Why di S10 restano verbatim, con sotto un Why di S7 (lo stile di casa). Nel rosso 7 però il Why di
>   S10 era diventato falso: diceva che sul ramo time i separatori si disegnano «solo sotto la scala» e che «S7 lo
>   rimodellerà». Un secondo test-author (`s7-repin-comment`, solo commento) ha aggiunto sotto 4 righe di Why S7
>   (`:2214-2217`): il ramo category prende l'intervallo dal piano della scala, il ramo time non disegna separatori, e il
>   pin resta una chiave `splitLine` per ramo. Poi 150/150 (`repin_after2.log`); prettier e `diff --check` puliti.
> - **Verificato, non toccato**: il test fratello `:908` («does not reuse history A bounds…») simula ancora il lettore
>   con la guardia vecchia (`:961-966`) e `buildZoomWindow(currentResolution, …)`. Resta un modello corretto, perché
>   simula solo voci della cascata, senza `ladder`. Per queste la guardia nuova si riduce alla vecchia, e la finestra
>   sulla voce attiva coincide con quella sulla risoluzione corrente. Il test è verde e fuori dagli 11. La stessa
>   garanzia sotto la scala sarebbe copertura nuova, non un ri-pin: resta fuori da S7.
> - Prossimo: di nuovo i cataloghi (attesi `asset-unit` 530/530 e `ai-export unit` 353/353, gli altri invariati), poi
>   `front build --debug` e l'E2E del file dashboard, seriale e con `--workers 4`.
>
> **Note implementazione — cataloghi, build ed E2E dopo il ri-pin** (22:21–22:30; log in `/tmp/libreFolio_i_s7/`).
> - I cataloghi nella 6157, uno alla volta (`run_units_after_repin.out`, un log per catalogo `units_repin_*.log`):
>
>   | Catalogo | Esito |
>   |---|---|
>   | `front-asset asset-unit` | **530/530** su 19 file |
>   | `front-asset growth-chart-memo` | 47/47 |
>   | `front-utility core-unit` | 2651/2651 su 99 file |
>   | `front-utility component-unit` | 2126/2126 su 87 file |
>   | `front-ai-export unit` | **353/353** su 22 file |
>
>   Come atteso: gli 11 rossi di `asset-unit` e di `ai-export unit` sono verdi, e gli altri cataloghi non cambiano.
> - `front build --debug` (`build_debug_fix.log`), poi l'E2E nella 6157:
>   - il describe `GrowthChart ladder x axis (S7)` (`--grep S7-`): **6/6** in 29,6 s (`e2e_green_s7.log`);
>   - `dashboard.spec.ts` intero: **24/24** in seriale (1,2 min, `e2e_green_dashboard_serial.log`) e **24/24** con
>     `--workers 4` (30,0 s, `e2e_green_dashboard_w4.log`).
> - Controlli finali (`final_checks.sh`, `final_checks.out`):
>   - `front check`: svelte-check dà 3 errori e 41 avvisi in 4 file, il floor;
>   - `tsc -p tsconfig.e2e.json`: i 2 errori noti (`onboarding-tour.spec.ts:863`, `types/files.ts:9`);
>   - `check-orphans`: ogni test registrato è raggiungibile da un `all`;
>   - `i18n audit`: 3417 chiavi in ogni catalogo, nessuna traduzione mancante;
>   - prettier `--check` sui file del frontend toccati e `git diff --check`: puliti;
>   - `lsof` sulla 6157: vuoto.
> - Prossimo: il bundle di C8. Preparandolo ho trovato il fuori pista del passo 6.

### S7 — passo 6: la riga «parziale» del tooltip passa per `escapeHtml` ✅ 2026-09-30 23:05

> **⚠️ Fuori pista — la regola XSS di S7 non era applicata** (22:34, preparando C8).
> - Ho confrontato il mio diff di `GrowthChart.svelte` (`/tmp/libreFolio_i_s7/s7_growth_diff.txt`) con quello di K,
>   estratto in sola lettura per la previsione del merge (`/tmp/libreFolio_i_s7/k_ref/`).
> - La riga del bucket parziale metteva `$_('chart.tooltip.partialBucket', …)` nell'HTML del tooltip **senza**
>   `escapeHtml`. La regola del coordinator (`:4018`) lo chiedeva.
> - Il passo 2 (`:4053`) e il passo 4 (`:4202`) lo davano per fatto. Erano affermazioni false, scritte senza rileggere
>   il codice. `:4053` aggiunge anche che il gate `htmlInterpolation` di K lo controlla: falso anche questo.
> - Nessun gate lo avrebbe visto:
>   - `htmlInterpolation.gate.test.ts` di K accetta le chiamate i18n (`$_`, `$t`) senza escape, e `days`/`total` non
>     hanno il nome di un campo di testo;
>   - `htmlSink.gate.test.ts` guarda solo `{@html}` nel markup, e GrowthChart non ne ha.
>
>   Serve un test di comportamento.
> - Nei 4 cataloghi di oggi la chiave non contiene markup, quindi l'utente non vedeva nulla di diverso. Il rischio era
>   una traduzione futura con `<` o `&`: sarebbe diventata HTML.
>
> **Note implementazione — prima il rosso** (test-author, sync; solo `GrowthChart.test.ts`).
> - Il caso è `it.each(SUBMODES)` «B5 $title, 40 days, 1W: the partial line shows its translation as written, never
>   as markup» (`:1891-1902`), cioè 2 casi: Candele e Proventi.
> - L'helper `withPartialBucketMessage` (`:1873`) sostituisce la foglia del catalogo con `addMessages`. Nel `finally`
>   rimette il testo originale e controlla che il ripristino sia avvenuto.
>   - svelte-i18n svuota la cache del locale a ogni `addMessages` (`node_modules/svelte-i18n/dist/runtime.js:85-91`);
>   - con `ignoreTag: true`, il default (`:232`), il markup del messaggio arriva intatto.
> - Il messaggio di prova è `S7-ESCAPE-LOCK &lt;b&gt; {days}/{total} <i>x</i>` (`:1862-1865`).
>   - Una precondizione controlla che si risolva con i valori dentro e il markup intatto.
>   - Poi il testo della riga, filtrato sul marcatore, deve essere il messaggio **come scritto**.
> - L'import di `svelte-i18n` (`:181`) prende anche `addMessages`. Due righe nel commento del describe S7
>   (`:1523-1524`).
> - Il rosso sul codice di prima (`/tmp/libreFolio_i_s7_escape_red.log`, 22:50): in entrambi i casi
>   «exactly one partial line, shown as written: expected `[ 'S7-ESCAPE-LOCK <b> 5/7 x' ]`». L'atteso era
>   `S7-ESCAPE-LOCK &lt;b&gt; 5/7 <i>x</i>`: il browser aveva letto la traduzione come HTML. Il file intero dà
>   47 verdi e 2 rossi (`escape_file.log`).
>
> **Note implementazione — la cura** (22:53, `GrowthChart.svelte`).
> - `import {escapeHtml} from '$lib/utils/core/escapeHtml';` alla `:21`, la prima riga dopo `<script lang="ts">`. È la
>   stessa riga, nella stessa posizione, dell'hunk di K: al merge i due lati coincidono.
> - `buildPartialBucketLine` (`:1264-1267`): `const partialText = $_(…)`, poi `${escapeHtml(partialText)}`. Il doc
>   spiega perché: la traduzione è un dato dentro l'HTML del tooltip.
> - `buildTooltipBucketHeader` (`:1270-1286`):
>   - `partialHtml` si calcola una volta sola, in cima, e serve ai due rami (un giorno e scala);
>   - `header` diventa `headerHtml`, per la regola dei nomi;
>   - `contextLine` non cambia.
> - **Prova per mutazione** (`/tmp/libreFolio_i_s7_mutation.sh`, log `/tmp/libreFolio_i_s7_mutation_run.log`):
>   - senza `escapeHtml(` tornano rossi esattamente i 2 casi nuovi, e gli altri 47 restano verdi;
>   - il file ripristinato è identico byte per byte: sha256 `6b15587b…94d9`.
>
> **Note implementazione — la verifica dopo la cura** (22:53–23:01; log `/tmp/libreFolio_i_s7_fix_*.log`).
> - `GrowthChart.test.ts`: **49/49**. I 6 file che leggono il componente (i 4 specchi, `GrowthChart.test.ts` e
>   `growthLadderAxis.test.ts`): **344/344** (`fix_mirrors.log`).
> - I cataloghi nella 6157, uno alla volta:
>
>   | Catalogo | Esito |
>   |---|---|
>   | `front-asset growth-chart-memo` | **49/49** (47 + i 2 casi nuovi) |
>   | `front-asset asset-unit` | 530/530 |
>   | `front-utility core-unit` | 2651/2651 |
>   | `front-utility component-unit` | 2126/2126 |
>   | `front-ai-export unit` | 353/353 |
>
> - `front build --debug`, poi `dashboard.spec.ts` intero: **24/24** in seriale (1,2 min) e **24/24** con
>   `--workers 4` (28,6 s).
> - `front check` è al floor (3 errori, 41 avvisi). Prettier `--check` sui 10 file del frontend nel delta e
>   `git diff --check` sono puliti. La 6157 è libera.
> - Le due frasi sull'escape (`:4053`, `:4202`) adesso sono vere; quella sul gate di K a `:4053` no. Le lascio come
>   sono: la correzione è questo fuori pista.
>
> **Note implementazione — lasciati fuori, da segnalare** (note del test-author; nessuna azione).
> - Nello stesso formatter del tooltip altre traduzioni entrano nell'HTML senza escape: `dashboard.totalPnl`,
>   `eurLabels.*`, `pnlLabels.*` e le `dataEditor.col.*` di `ohlcRow`. Il gate di K le accetta, e la regola del
>   coordinator riguarda solo la riga «parziale»: non allargo il perimetro.
> - I doc di `partialLine()` e `partialLinePattern()` e quello di `htmlText`, nel file di test, dicono che la riga
>   parziale passa da `htmlText`. Dopo la cura sono un po' imprecisi, ma restano verdi con i cataloghi veri. È una
>   pulizia facoltativa.
> - La `desc` di `growth-chart-memo` (`scripts/test_runner/_frontend_asset.py:165`) non nomina D23, il margine della
>   griglia né S7. È una superficie condivisa del runner: la segnalo al coordinator e non la tocco.
> - Prossimo: il risultato di S7 e la divisione di C8 al coordinator; il bundle parte al suo via.

### Checkpoint C8 — preparazione (2026-09-30 23:08)

> **Note implementazione — il mandato** (coordinator, 23:08): via al bundle di C8, con il protocollo di C7, base
> `039baea22`, 3 commit come proposti. Prima del bundle, due ritocchi:
> - **Grant del runner.** La `desc` di `growth-chart-memo` (`scripts/test_runner/_frontend_asset.py:165`) nomina D23,
>   il margine della griglia e S7. Va nel commit 2. Il commit 1 prende `_frontend_asset.py` in una versione
>   intermedia: la registrazione (`:35`) e la `desc` di `asset-unit` (`:164`), nient'altro. Controllo ogni confine:
>   il commit 1 da solo deve passare `asset-unit` e `check-orphans`.
> - **I doc di tre helper di test** (`partialLine()`, `partialLinePattern()`, `htmlText`): sì, via test-author, solo
>   commenti. Poi di nuovo `growth-chart-memo` e Prettier.
>
> Il resto del messaggio:
> - **La simulazione dell'allineamento**, fatta dal coordinator (albero WIP `421363d78` × `8f18416df`, base del merge
>   `5068b706c`): 10 file toccati dai due lati, **una sola regione in conflitto**, la riga del broker sotto la candela
>   in `GrowthChart.svelte`. La risoluzione tiene il mio `fmtCurrency(v, true)` e l'`escapeHtml(broker.brokerName)` di
>   K. L'import della `:21` e gli altri 2 siti di K si fondono da soli.
> - **Avviso da Risk.** Il suo commit (a) `840bdbc0d`, con il grant del coordinator, cambia il mio `lineChartHelpers.ts`
>   (fa da ponte a `Lower`/`Band` fra le sessioni) e il mio test `'maps a date absent…'` (contratto nuovo: Lower
>   `[0,1,2]`, Band `[10,10,10]`). Mi arriva con l'integrazione di Risk. **Nel frattempo non tocco quei due file.**
> - Le traduzioni senza escape nel formatter, e i `$_` che il gate di K accetta, vanno nel backlog del coordinator, per
>   il triage di fine giro con K.
> - Nel passaggio di consegne: una riga di CHANGELOG proposta per S7.
>
> **Note implementazione — la `desc` del runner** (23:11–23:12).
> - Prima di toccarla ho salvato il file così com'era: è la versione intermedia del commit 1
>   (`/tmp/libreFolio_i_c8_commits/work/snap/_frontend_asset.b1.py`, sha256 `7176aa89…338c`). Contro BASE sono 2 hunk,
>   la `:35` e la `:164`, e tutti e due parlano solo del pianificatore.
> - La `:165` tiene il testo di prima e aggiunge, con le parole dei doc dei describe (`:1048-1065`, `:1479-1484`,
>   `:1515-1534`): una forma sola per ogni importo con segno nel tooltip, con il segno del locale (D23, D23b); il
>   margine sinistro della griglia; l'asse a scala di Candele e Proventi (S7), cioè i bucket ancorati alla fine su un
>   asse a categorie, etichette e separatori del pianificatore, il bucket corto più vecchio traslucido e spiegato nel
>   tooltip (con escape), la finestra dello zoom che resta ai cambi di gradino e ai ridisegni.
> - `python3 -m py_compile` passa. Dalla versione intermedia a quella finale cambia 1 riga, la `:165`.
>
> **⚠️ Fuori pista — il turno interrotto** (23:33). Un errore del servizio ha chiuso il mio turno, e quello di D alla
> stessa ora. Alla ripresa (23:37) il coordinator mi ha mandato lo stato, e l'ho ricontrollato da solo:
> - HEAD `039baea22`, il ramo giusto, gli stessi 12 percorsi (10 modificati, 2 nuovi), stage vuoto, nessun merge,
>   cherry-pick o lock in corso;
> - la 6157 e la 6167 libere, nessun processo mio rimasto;
> - la `desc` del runner e la nota qui sopra c'erano; i doc degli helper no, e il bundle non era partito;
> - la divisione del runner è esatta: da BASE alla versione intermedia cambiano solo la `:35` e la `:164`, da lì al
>   worktree solo la `:165`;
> - il test di Risk `'maps a date absent…'` sta in `charts/__tests__/lineChartHelpers.test.ts:271`, fuori dal mio
>   delta: nessuna sovrapposizione.
>
> **Note implementazione — i doc dei tre helper di test** (23:38–23:46; test-author `c8-helper-docs`, sync, solo
> `GrowthChart.test.ts`).
> - Prima ho salvato il file (`work/snap/GrowthChart.test.pre-docs.ts`, sha256 `10c1d211…0713`).
> - I tre commenti adesso dicono cosa succede davvero:
>   - `htmlText` (`:661-663`): serve per l'HTML che il componente costruisce con il testo grezzo di `$_()`
>     (etichette delle righe, intestazioni); una traduzione con escape, come la riga parziale, si legge come è scritta;
>   - `partialLine()` (`:1641-1643`): il componente fa l'escape di questa riga; `htmlText` restituisce lo stesso
>     testo finché la voce del catalogo non ha markup né entità, come oggi nei 4 locali; il caso col markup è il
>     blocco B5 dell'escape (`withPartialBucketMessage`);
>   - `partialLinePattern()` (`:1650-1651`): passa da `htmlText`, quindi vale con la stessa condizione.
> - Il test-author ha preso le mie parole, con una modifica: «B5's» è diventato «B5's escape block».
> - La mia verifica:
>   - `diff -U0` con la copia di prima: 3 hunk, solo righe di commento (`/tmp/libreFolio_i_c8_docs.diff`);
>   - `front-asset growth-chart-memo` nella 6157: **49/49** in 10 s (`/tmp/libreFolio_i_c8_memo_postdocs.log`);
>   - Prettier `--check` e `git diff --check` puliti, la 6157 libera;
>   - il nuovo sha256 di `GrowthChart.test.ts`: `510703ef…f025`.
> - La pulizia sposta le righe del file: +1 da `:663`, +3 da `:1641`, +4 da `:1648` (numeri di prima). I riferimenti a
>   `GrowthChart.test.ts` nel passo 6 e qui sopra valgono per la copia di prima. Per esempio il blocco B5 `:1891-1902`
>   adesso è `:1895-1906`, e i doc dei describe sono `:1049-1066`, `:1480-1485` e `:1516-1535`.

### Checkpoint C8 — pronto (2026-09-30 23:51)

> **Note implementazione:**
> - **Mandato** (coordinator, 23:08; ripreso alle 23:35, dopo l'interruzione): via al bundle di C8, 3 commit come
>   proposti, con il protocollo di C7. Prima la `desc` del runner e i doc dei tre helper di test: fatti (registro
>   «preparazione»).
> - **Contenuto:** 3 commit su `039baea22`, 12 percorsi:
>
> | # | subject | contenuto | percorsi |
> |---|---|---|---|
> | 1 | `feat(charts): add ladder axis planner` | il pianificatore della scala, puro e senza i18n, con i suoi test; nel runner la registrazione e la `desc` di `asset-unit` | `growthLadderAxis.ts` e `growthLadderAxis.test.ts` (nuovi), `scripts/test_runner/_frontend_asset.py` (versione intermedia) |
> | 2 | `fix(charts): rebuild candle and income bucket axis` | la cura di S7 in `GrowthChart.svelte`: asse a categorie, etichette e separatori dal pianificatore, il bucket corto traslucido, la riga «parziale» con `escapeHtml`, lo zoom che resta. La chiave `chart.tooltip.partialBucket`; i test unit, gli 11 specchi ri-pinnati, il describe E2E; la `desc` di `growth-chart-memo` | `GrowthChart.svelte`, `GrowthChart.test.ts`, `chartCoreHelpers.test.ts`, `frontend/e2e/portfolio/dashboard.spec.ts`, i 4 cataloghi, `_frontend_asset.py` (versione finale) |
> | 3 | `docs(journal): record C7 and S7` | questo file | il journal |
>
> - **Un file si divide fra due commit:** `_frontend_asset.py`. Il commit 1 prende la versione intermedia salvata
>   (sha256 `7176aa89…338c`: la `:35` e la `:164`), il commit 2 aggiunge la `:165`. Le patch vanno solo nell'indice
>   (`git apply --cached`), quindi il worktree resta alla versione finale per tutta la corsa.
> - **Le prove per confine**, nella copia di prova completa (tutto l'albero di BASE, `node_modules` clonato, mai un
>   link verso il worktree), a b0 (= BASE), b1 e b2:
>   - svelte-check, l'intera suite vitest, `tsc -p tsconfig.e2e.json`, Prettier sui file del frontend presenti,
>     `playwright --list` di `dashboard.spec.ts`;
>   - in più, come chiede il mandato, dalla radice della copia: `front-asset asset-unit` e `check-orphans` con
>     `dev.py`, nella 6157, e `py_compile` del runner. Il confine che conta è b1, il commit 1 da solo;
>   - prima controllo che `pipenv --venv`, dalla copia, indichi il venv condiviso: non ne creo uno.
>
>   Il commit 3 tocca solo il journal: il suo frontend è quello del commit 2, e lo script lo verifica.
> - **Come:** lo stesso protocollo di C1–C7. Patch e messaggi; lo script a guardie derivato da quello di C7 (sha256
>   `485cbd92…ad58`), con sostituzioni contate; il digest con 4 git; il dry-run in 9 configurazioni; 3 cloni
>   usa-e-getta per i commit veri; `merge-tree` con `dev_release2`, per HEAD e per l'albero finale.
> - **L'allineamento viene dopo il commit.** La simulazione del coordinator dà una sola regione in conflitto, la riga
>   del broker sotto la candela in `GrowthChart.svelte`: restano il mio `fmtCurrency(v, true)` e
>   l'`escapeHtml(broker.brokerName)` di K. La risolvo solo se me lo chiedono.
> - **Non tocco** `lineChartHelpers.ts` né `__tests__/lineChartHelpers.test.ts` (avviso di Risk): non sono nel delta.
> - **Esclusi:** i log in `/tmp`, `test-results/`, `playwright-report/`, la build del frontend, i file generati, i
>   laboratori e le sonde di S7 (`/tmp/libreFolio_i_s7/`, `/tmp/libreFolio_i_s7_*`), le copie in `work/snap/`.
> - **Pulizia:** `/tmp/libreFolio_i_c7_commits` è già cancellata: C7 è committato e verificato, e la sua copia sta in
>   `files/c7_commit_bundle/`.
> - **Questa è l'ultima scrittura nel worktree prima del digest.** I numeri del bundle (alberi, sha256, digest)
>   dipendono da questo file, quindi qui non ci sono: li registro dopo il commit.
> - **Dopo C8:**
>   - l'allineamento con `dev_release2` (oggi `8f18416df`, con K);
>   - sulla revisione combinata, i gate di K (`htmlInterpolation.gate.test.ts`, `htmlSink.gate.test.ts`,
>     `GrowthChart.tooltip.test.ts`), con `growth-chart-memo`, `component-unit` e `asset-unit`;
>   - poi S7b (tacche Y doppie, gli assi di D23, «-888»), S8 (R11), S8b (D24), la verifica sulla copia nella 6167,
>     S11-finale (docs-writer), S12.

### Checkpoint C8 — committato ✅ 2026-10-01 11:04

> **Note implementazione:**
> - **Il bundle**, costruito fra le 23:52 e le 00:12 senza scrivere nel repository dopo il registro «pronto», stava
>   in `/tmp/libreFolio_i_c8_commits/`, con la copia nella cartella di sessione (`files/c8_commit_bundle/`). Le
>   guardie sono quelle di C7, con HEAD `039baea22`, i 12 percorsi e i 3 alberi di C8. Un file si divide fra due
>   commit, `_frontend_asset.py`: le patch vanno solo nell'indice, e il worktree resta alla versione finale.
>
> | verifica | come | esito |
> |---|---|---|
> | patch semplici | `git apply` in sequenza su copie di BASE, poi `cmp`, con git Homebrew 2.55 e Apple 2.54 | identici a ogni confine (10/10 percorsi a BASE, 12/12 dopo), nessun file in più. Patch 01: 3 file (2 nuovi), +1282 −1, sha256 `5a080a4c…1d93`; patch 02: 9 file, +1735 −179, sha256 `7207215c…8a31`; patch 03: il journal, +1105 −6, sha256 `6d5dea3e…1774` |
> | prove per confine | nella copia di prova completa (tutto l'albero di BASE, `node_modules` clonato; `pipenv --venv` indica il venv condiviso): svelte-check, l'intera suite vitest, `tsc -p tsconfig.e2e.json`, Prettier, la parità dei cataloghi, `playwright --list` di `dashboard.spec.ts`; dalla radice della copia, `py_compile` del runner, `front-asset asset-unit` e `check-orphans` | svelte-check al floor a b0, b1 e b2 (3 errori, 41 avvisi, 4 file). vitest: b0 6529, b1 6591 (+62, `growthLadderAxis.test.ts`), b2 6617 (+26), 0 falliti. tsc: i 2 errori della base, invariati. Cataloghi: 3416, 3416, 3417 chiavi (+1, `chart.tooltip.partialBucket`). `--list` di dashboard: 18, 18, 24. Prettier pulito su 8, 10 e 10 file. Runner: rc 0 ai tre confini; a b1, cioè il commit 1 da solo, `check-orphans` trova 265 unit registrati e raggiungibili (264 a b0) |
> | digest del contenuto | come in C1–C7 | `ef9600f2…9100c`, identico con 4 git: 2.53 del bundle dell'app, Homebrew 2.55, Apple 2.54, Apple 2.54 in ambiente vuoto |
> | dry-run sul repository reale | matrice di 9 configurazioni (bash 3.2 e 5; git Apple, Homebrew e del bundle; `env -i`, anche in it_IT) | rc 0 in 9 su 9, «would commit 3/3». Fuori da `refs/copilot/` refs invariati; nessuno dei 19 oggetti propri del bundle nel repository |
> | commit veri, in 3 cloni usa-e-getta | git Homebrew 2.55 con bash 3.2, git 2.53 con bash 5, git Apple in `env -i` | PASS 16 in ognuno: le guardie, il dry-run, 3 commit lineari, il runner intermedio nel commit 1 e finale nel 2, il secondo lancio rifiutato. Ogni clone cancellato dallo script, repository reale invariato |
> | messaggi | `check_messages.py` | `MESSAGES OK`: subject ASCII di 37, 50 e 31 caratteri, righe ≤ 69. La scansione privacy segnala 2 righe del journal, attese: la riga «messaggi» del registro di C7 e il «token rich» di ECharts |
> | revisione combinata, prima del merge | `merge-tree` con `dev_release2` (`8f18416df`, base del merge `5068b706c`), per HEAD e per l'albero di C8, in un archivio di oggetti usa-e-getta | una sola regione in conflitto, in `GrowthChart.svelte`, come nella simulazione del coordinator. Il target tocca altri 5 percorsi di C8 (i 4 cataloghi, `_frontend_asset.py`), che si fondono da soli |
>
> - sha256 dello script `1310bc9a…55cb`, derivato da quello di C7 (`485cbd92…ad58`) con sostituzioni contate.
> - **Il developer ha committato alle 11:04** (ora d'autore 11:03:59; segnale del coordinator alle 11:12). Il
>   coordinator ha confrontato alberi e messaggi con il bundle. La mia verifica, in sola lettura, fatta dopo il merge
>   (`/tmp/libreFolio_i_c8_postcommit_check.sh`, 12:28):
>   - 3 commit in fila su `039baea22`, ognuno con un solo genitore;
>   - ogni albero è quello del bundle;
>   - ogni messaggio è identico byte per byte al suo `.msg`;
>   - i 12 file nell'albero di `de5349e46` hanno lo sha256 registrato nel bundle;
>   - i 19 oggetti propri del bundle ora sono tutti nel repository (19 su 19);
>   - `dev_release2` (`8f18416df`) è antenato di HEAD, con il merge del registro qui sotto.
>
> | # | commit | subject | albero |
> |---|---|---|---|
> | 1 | `7bfa064f0` | `feat(charts): add ladder axis planner` | `8a8d09f8e6a8` |
> | 2 | `69cba356f` | `fix(charts): rebuild candle and income bucket axis` | `e2b708b78638` |
> | 3 | `de5349e46` | `docs(journal): record C7 and S7` | `741865f8a6e9` |
>
> - **Pulizia:** cancellata `/tmp/libreFolio_i_c8_commits` (1,9 GB), dopo il confronto con `cmp` fra la copia in
>   sessione e quella in `/tmp`: script, digest, patch e messaggi. Nella copia in sessione mancava lo script della
>   risoluzione, `resolve_worktree.py`: l'ho aggiunto prima di cancellare (`files/c8_commit_bundle/work/`).

### Allineamento a `dev_release2` — merge `851d3a5cf` ✅ 2026-10-01 12:15

> **Note implementazione:**
> - **L'apertura.** Lo script del coordinator, `/tmp/libreFolio_merge_target_into_i8_open.sh`, lanciato dal developer
>   dopo il commit di C8, ha riconosciuto C8 dagli alberi e ha aperto il merge con `8f18416df`. Il merge base è
>   `5068b706c`. È rimasto in conflitto il solo `GrowthChart.svelte`, nessun file non tracciato.
> - **Il commit.** Lo script del coordinator, `/tmp/libreFolio_commit_i8_merge.sh`, con guardia sull'albero (dry run
>   GUARDS_OK), lanciato dal developer alle 12:15; segnale del coordinator alle 12:19. La mia verifica, in sola
>   lettura:
>   - `851d3a5cf`, genitori `de5349e46` e `8f18416df`, albero `6b4a1dd90394`: lo stesso che stava in stage durante
>     il gate del registro qui sotto, quindi il gate vale per il commit;
>   - subject `merge(charts): dev_release2 into I (K step 13, L picks)`;
>   - nessun merge in corso, albero di lavoro pulito, 0 file non tracciati; porte 6157 e 6167 libere.
> - **Cosa porta**: 21 commit e 144 file, +7460 −355.
>   - **Il passo 13 di K** (`80f1d9155`, CHANGELOG in `8f18416df`).
>     - L'escape del testo utente nei sink HTML (`53219bc00`) e i gate `htmlInterpolation.gate.test.ts` e
>       `htmlSink.gate.test.ts`, entrambi in core-unit.
>     - `GrowthChart.tooltip.test.ts`, in component-unit, con tre casi: linea, candele, percentuale.
>     - Gli escape nei grafici: `echartsTooltipHelpers.ts`, `signalLabel.ts`, `PriceChartFull`, `ExposureTreemap` e
>       altri. Nessuno di questi file l'ho toccato io dal merge base.
>   - **STALE_PRICE con la CTA di sincronizzazione** (`f1fe176a2`).
>     - `portfolio_service.get_report` costruisce `stale_prices` dalle `end_positions` (MARKET_PRICE, asset con
>       provider).
>     - In `portfolio_engine.py` la `cta_action` passa da `navigate_asset` a `sync_asset_prices`.
>     - Test: +253 righe in `test_portfolio_service.py`, +45 in `test_data_quality_report.py`.
>   - **Borsa Italiana**.
>     - La valuta viene dall'API dei prezzi (`fa03e116a`).
>     - `borsa-italiana-scraping` sale a 0.3.2 (`3c9f78b50`: `Pipfile` e lock, dipendenza git `ref` `95d6a59d…`).
>     - Il venv condiviso l'ha già aggiornato il developer sotto freeze. Misurato al gate: borsa 0.3.2, idna 3.20,
>       soupsieve 2.10, gli stessi del lock. Nessuna azione mia.
>   - **Le scelte di L**, prese con cherry-pick dal suo ramo:
>     - la correzione dell'upload, `0743b9f44`: il form manda il `broker_id` (CHANGELOG `b1835949e`);
>     - dal passo 1: i CSV in cp1252 (`cc4ae7aeb`), i plugin CSV con il lettore di base (`8efbbed14`), la `desc` del
>       runner per `brim-provider-base` (`c1108c9d0`), gli ID d'asset finti nei doc (`e4dfb6d55`); CHANGELOG
>       `1622a7a38`;
>     - cambiano anche un file di istruzioni BRIM e lo skill BRIM: non è il mio dominio.
>   - **Il resto**:
>     - PWA: icone opache e una maskable vera (`b4f425226`), service worker ritimbrato (`3d625e703`);
>     - i nomi dei campi per i password manager (`f23f68e2e`);
>     - il layout da telefono della scheda asset (`007528dc6`);
>     - le cinque toolbar (`3e5313d3e`);
>     - le pagine developer del banner e della PWA, `user/dashboard/index.en.md` (+2);
>     - TODO (`8bd6be663`, `b8bfd0cac`) e CHANGELOG.
>   - Niente in `alembic/`, `app/db`, `app/schemas`, nel client API o nel `package.json`/lock del frontend: niente
>     `npm ci`, niente ripopolamento del DB.
> - **La risoluzione**: una regione sola, `GrowthChart.svelte:2146` (5 righe → 1), la riga del broker nel tooltip
>   delle candele.
>   - Tengo la mia (`fmtCurrency(v, true)`, D23b) con l'`escapeHtml(broker.brokerName)` di K.
>   - L'ha scritta `resolve_worktree.py` (copia in `files/c8_commit_bundle/work/`), che scrive solo se lo sha
>     coincide. Lo sha256 è `98dfee0a…fca5`: uguale alla prova preliminare e alla risoluzione rifatta dal
>     coordinator.
>   - Ho messo in stage solo quel file. L'albero in stage, calcolato con indice e oggetti usa-e-getta, è
>     `6b4a1dd90394`, quello previsto dalla prova del coordinator su un clone.
>   - Gli escape nel file risolto:
>     - l'import `:21`;
>     - `partialText` `:1267` (S7);
>     - il nome del broker in `pnlRow` `:2123`;
>     - la riga delle candele `:2146`;
>     - `seriesName` nella vista % `:2190`.
>   - Le altre `<span>${label}</span>` (`:2119`, `:2131`, `:2161`) ricevono etichette già passate per escape o fisse.
> - **I 10 file toccati da entrambi i lati**: Git ha fuso da solo tutti tranne `GrowthChart.svelte`.
>   - Verifica: ogni riga aggiunta da un lato rispetto al merge base dev'essere nel risultato in stage. Script
>     `/tmp/libreFolio_i_m8_shared_lines.py`, log `/tmp/libreFolio_i_m8_shared_lines.log`.
>   - Mancano solo le due versioni della riga risolta, come atteso.
>
> | file | righe mie presenti | righe del target presenti |
> |---|---|---|
> | `backend/app/services/portfolio_service.py` | 13/13 | 16/16 |
> | `frontend/e2e/brokers/brokers-detail.spec.ts` | 348/348 | 111/111 |
> | `GrowthChart.svelte` | 361/362 | 3/4 (la riga risolta, su entrambi i lati) |
> | i18n `en`/`it`/`fr`/`es` | 2/2 ciascuno | 2/2 ciascuno |
> | `routes/(app)/assets/[id]/+page.svelte` | 3/3 | 17/17 |
> | `scripts/test_runner/_frontend_asset.py` | 11/11 | 29/29 |
> | `scripts/test_runner/_frontend_utility.py` | 2/2 | 30/30 |
>
> - **`portfolio_service.py`: le due modifiche sono indipendenti.**
>   - La mia allarga `needs_engine` in `get_report` (`:2422` nel file unito) a tutte le sezioni.
>   - Quella del target aggiunge STALE_PRICE nel percorso del motore (`:1248`).
>   - Con la mia, una richiesta di sole candele o proventi passa dal motore e riceve anche il nuovo avviso. È
>     coerente.
> - **Per i passi successivi**:
>   - nel codice nuovo valgono i gate di K: `escapeHtml(` per il testo utente, `…Html`/`…Badge` per le variabili con
>     HTML, `…Url`/`…Src` per gli URL;
>   - per S11-final, `user/dashboard/index.en.md` ha 2 righe nuove del target.

### Gate sulla revisione combinata `851d3a5cf` ✅ 2026-10-01 11:48 (dalle 11:17; merge aperto, albero `6b4a1dd90394`)

> **Note implementazione:**
> - Corsia: 6157, `/tmp/librefolio-r2-i-charts`, un comando alla volta, con merge aperto e albero in stage
>   `6b4a1dd90394`, prima del commit. Il commit ha lo stesso albero (registro qui sopra): il gate vale per
>   `851d3a5cf`.
> - Log: `/tmp/libreFolio_i_m8_*.log`.
> - A fine giro:
>   - porte 6157 e 6167 libere;
>   - albero in stage ricalcolato, `6b4a1dd90394`;
>   - 0 voci in conflitto, albero di lavoro uguale all'indice, 0 file non tracciati;
>   - `diff --cached --check` pulito.
>
> | # | gate | esito | atteso |
> |---|---|---|---|
> | 1 | `front build --debug` (11:17) | rc 0 | la build, più nuova di ogni sorgente, serve agli E2E |
> | 2 | `front check` | 3 errori e 41 avvisi in 4 file, rc 1 | il floor: `TransactionFormModal.test.ts` ×2, `ToolExecutionMetrics.svelte` ×1; `BrokerSharingPanel` 27, `GlobalSettingsTab` 14 |
> | 3 | `front-utility core-unit` | 2684/2684 su 102 file | dentro: `htmlInterpolation.gate.test.ts` 18/18, `htmlSink.gate.test.ts` 7/7 (K) |
> | 4 | `front-asset asset-unit` | 530/530 su 19 file | dentro: `growthLadderAxis.test.ts` 62/62, `chartCoreHelpers.test.ts` 150/150. I 12 rossi di `computeZoomWindowRange` di `dev_release2` qui non ci sono |
> | 5 | `front-utility component-unit` | 2195/2195 su 94 file | dentro: `GrowthChart.tooltip.test.ts` 6/6 (K) |
> | 6 | `front-asset growth-chart-memo` | 49/49 | |
> | 7 | vitest completo (`/tmp/libreFolio_i_m8_vitest_full.sh`) | 6719/6719, 1564 suite, 0 falliti, 108 s | per file: flagFont 13/13, layout.gate 2/2 |
> | 8 | `check-orphans` | rc 0: 92 E2E, 275 unit, 224 backend raggiungibili | il runner scrive l'istantanea del DB (`test-db_20261001_113135.tar.xz`), comportamento normale |
> | 9 | `i18n audit` | rc 0: 3418 chiavi in ognuno dei 4 cataloghi, nessuna traduzione mancante | `chart.tooltip.partialBucket` non è fra le «likely unused» |
> | 10 | `services roi-fifo-utils` | 518/518 | dentro: i test STALE_PRICE del target, tutti verdi |
> | 11 | `services portfolio-engine` | 42/42 | |
> | 12 | `services portfolio-allocation-source` | 69/69 | |
> | 13 | `services fx-core` | 23/23 | |
> | 14 | `api portfolio` | 55/55 | server di prova sulla 6157, poi libera |
> | 15 | `services ai-export` | 922/922, 3 avvisi, 220 s | i 3 avvisi: `PytestUnhandledThreadExceptionWarning` di aiosqlite («Event loop is closed») alla chiusura di `test_ai_export_components_fx.py::TestPairIdentity::test_direct_pair`. Nessuno dei due lati tocca `ai_export`, FX o i conftest |
> | 16 | E2E `front-portfolio dashboard` | 24/24, 1 worker, 1,5 min | le righe di D23/S7 e i tooltip ancorati alla fixture (C5) |
> | 17 | E2E `front-asset asset-detail` | 28/28, 1 worker, 2,0 min | `:486` «calendar-return primary mode» verde in 1,2 min, come al gate B4 (budget 180 s di `2d22130bd`) |
> | 18 | E2E `front-broker detail` | 32/32, 1 worker, 1,2 min | `:1072` «line and income submodes render this broker own figures» verde. Il blocco di L, «import history upload» (`0743b9f44`), sta in fondo allo spec (`:1205`) ed è verde a `:1219` |
>
> - Nessun retry e nessun flaky nei tre log E2E. Dei rossi noti di `dev_release2` dipendenti dalla data non ne
>   resta nessuno sulla revisione combinata: `asset-detail :486`, il P&L di `brokers-detail`, `dashboard`.
> - **Non lanciato: `services risk-all`.**
>   - È pesante (QuantLib, Riskfolio, worker) e appartiene a Risk.
>   - L'unico punto di contatto è `risk/service.py:362`, che chiama `PortfolioService.get_report`, e
>     `test_risk_service.py` lo sostituisce con un finto.
>   - Il `get_report` combinato lo coprono già `api portfolio` e `test_portfolio_service.py`, dentro
>     `roi-fifo-utils`.
>   - Il coordinator (12:05) conferma che non serve: nessuno dei due lati lo tocca.
> - **Il registro arriva dopo il commit.** La regola del piano chiede di aggiornarlo a ogni passo, ma con il merge
>   aperto lo script del coordinator verifica l'albero: tutti e tre i registri li ho scritti dopo il commit, come per
>   `921f1fc05`.
> - **Prossimo:** S7b (tacche Y doppie, D18), poi S8.

### S7b — Tacche Y distinte (D18, D23 sugli assi) e tacca di bordo (D25) ✅ 2026-10-01 15:02

**Passo 1 — analisi, sola lettura ✅ 2026-10-01 13:19**

> **Note implementazione:**
> - Base: `cd6502084` (il journal di C8, sul merge `851d3a5cf`), albero pulito, porte 6157 e 6167 libere. Avvio:
>   il coordinator, dopo la verifica di `cd6502084`.
> - Le righe da cambiare, entrambe mie:
>   - `GrowthChart.svelte:1999-2008`, `yAxisFormatter`, ramo del denaro: `toFixed(0)` per i k, `toFixed(1)` per
>     gli M, il meno ASCII scritto a mano, poi `maskable(compact)`. Il ramo `%` (`toFixed(1)`) resta (D18);
>   - `PerformanceChart.svelte:183-188`, `axisTickAmount`: il compatto di Intl con `maximumFractionDigits: 0` da
>     100 in su, il meno ASCII a mano, lo zero `maskable('0')`.
> - Progetto, un solo commit come da piano (`fix(charts): keep Y axis ticks distinct`):
>   - Crescita: la scala resta quella di oggi (k da 1.000, M da 1.000.000, suffisso scritto da noi); il valore
>     scalato passa per `toLocaleString(undefined, {maximumSignificantDigits: 15})` e la stringa intera per
>     `maskFormattedNumber` di J;
>   - Performance: `Intl.NumberFormat(undefined, {notation: 'compact', maximumSignificantDigits: 15})` sul valore
>     con il segno, poi `maskFormattedNumber`;
>   - in entrambi lo zero entra come `v === 0 ? 0 : v`, perché Intl scrive `-0` per lo zero negativo.
> - Perché 15 cifre significative: una tacca di ECharts è già arrotondata alla precisione del passo, quindi il
>   valore scalato è il double più vicino a un decimale corto, e 15 cifre lo stampano esatto, senza zeri in coda né
>   rumore. Vale con qualunque scala compatta del locale (`5 tn` in svedese, `5 mil` in spagnolo).
> - Sonda in Node, ECharts 6.0.0 dal `frontend/node_modules` di questo worktree, in SSR (nessun browser, nessun
>   server). Script e log: `/tmp/libreFolio_i_s7b_probe.{cjs,log}`, copiati nei file della sessione.
>   - D18 in en-US: `5k | 5.5k | 6k | 6.5k | 7k | 7.5k | 8k` (7 distinte) e `1k | 1.5k | 2k | 2.5k` (4 distinte,
>     oggi `1k | 2k | 2k | 3k`); gli interi senza decimali (`2k`, `20k`, `1M`); la Performance uguale, con `K`.
>   - Un cambiamento voluto: un milione tondo diventa `1M`, non più `1.0M`, per la regola di D18.
>   - D23 in sv-SE: `−5k`, `−1,5 tn` con U+2212, venuto dalla stessa chiamata delle cifre; it, fr ed es scrivono
>     `-` e la virgola decimale.
>   - I doppioni di oggi, misurati sulle tacche vere: Abs fra 9,8k e 10,4k → 8 etichette tutte `10k`; fra 1,18M e
>     1,26M → `1.2M` ×5 e `1.3M` ×2; il caso di N1 → `3k`, `2k` ×4, `1k`, `900`. Con D18 sono tutte distinte.
>
> **⚠️ Fuori pista: la tacca di bordo (D25).**
> - Causa, in ECharts 6.0.0 (`echarts/lib/scale/Interval.js:126-136`, `getTicks`): se un bordo dell'asse è
>   fissato, la tacca su quel bordo è il valore grezzo, non un multiplo del passo. Un bordo libero, ECharts lo
>   arrotonda al passo.
>   - La Crescita fissa il minimo (`GrowthChart.svelte:2245`): minimo dei dati − 8 % dell'escursione, arrotondato
>     all'intero.
>   - La Performance fissa entrambi i bordi (`PerformanceChart.svelte:987-988`): ±105 % della barra più lunga.
> - Oggi `toFixed(0)` arrotonda il bordo e lo nasconde, a volte creando un doppione. Con D18 diventa esatto e
>   illeggibile: misurati `9.752k`, `93.64k`, `1.17344M`, `-4.152k`, `-2.55465K`, `-1.29629535M`.
> - Nei Proventi senza costi il bordo è il «−888» visto in S6: le barre partono da 0, sotto resta una fascia
>   vuota.
> - Nessun test fissa la funzione `min` né i bordi (`grep` su unit ed E2E). L'E2E `axisLabels` chiama il formatter
>   con valori dati, quindi non vede quali tacche ECharts disegna.
> - In S6 era scritto «Va in S7b; lì chiedo al developer». Va al developer come **D25** (§7), con le etichette
>   misurate per ogni opzione.
>
> **Passi:**
> 1. ✅ analisi;
> 2. ✅ D25 al developer: B (13:51);
> 3. ✅ test rossi e ri-pin via test-author: GrowthChart.test.ts, PerformanceChart.test.ts (14:46);
> 4. ✅ la cura: GrowthChart.svelte, PerformanceChart.svelte (14:50);
> 5. ✅ gate nella 6157, un comando alla volta (15:00);
> 6. ✅ registro, poi `CHECKPOINT READY` al coordinator e FROZEN (15:02).

**Passo 2 — D25 al developer ✅ 2026-10-01 13:51**

> **Note implementazione:**
> - Due `ask_user` nella chat di I. La prima presentava A, B e C con le etichette misurate (§7, D25). Il developer ha
>   chiesto: nel P&L da −3,2k a 8,7k la tacca più bassa è −3k? Chiarito che l'asse parte da −4,15k: −3,2k è il punto
>   più basso della linea, appena sotto la riga −3k, nella fascia senza etichetta; nulla è tagliato.
> - Risposta, testuale: «B così: la linea scende appena sotto −3k, il bordo resta senza etichetta (Consigliata)».
> - Che cosa cambia, per modo:
>   - Crescita, linee (€ e P&L), candele e `%`: `min` resta la funzione di oggi (minimo − 8 % dell'escursione,
>     `GrowthChart.svelte:2245`); in più `axisLabel.showMinLabel: false`;
>   - Crescita, Proventi: nessun minimo fissato e `showMinLabel` al default di ECharts. Con `scale: false`, il
>     default, l'asse comprende lo 0: senza costi `0 2k … 12k`, con −1,2k di costi `−3k 0 3k … 12k`;
>   - Performance: `showMinLabel: false` e `showMaxLabel: false` in `xAxis.axisLabel`; i bordi restano ±105 %
>     della barra più lunga (`axisBound`), con `splitNumber: 4`.
> - Limite accettato con B: una tacca tonda che cade proprio sul bordo fissato perde anche lei l'etichetta.
>
> **⚠️ Fuori pista: l'asse y della Crescita si fonde, non si sostituisce.**
> - La ricostruzione completa passa `CHART_FULL_UPDATE_OPTS` (`GrowthChart.svelte:505`): `replaceMerge` copre
>   `series` e `xAxis`, non `yAxis`. Una chiave assente dal nuovo `yAxis` conserva il valore di prima. Il cambio di
>   sottomodo forza la ricostruzione (`renderedModeKey`, `:1948`), ma passando dalla linea P&L ai Proventi la
>   funzione `min` e `showMinLabel: false` resterebbero.
> - Sonda in Node, ECharts 6.0.0 in SSR, linea e poi barre con le opzioni del componente. Script e log:
>   `/tmp/libreFolio_i_s7b_merge.{cjs,log}` e `/tmp/libreFolio_i_s7b_merge2.{cjs,log}`.
>   - Chiavi omesse: estensione `[-888, 12000]`; nel modello restano `min` (la funzione) e `showMinLabel: false`.
>   - `min` e `showMinLabel` espliciti, a `null` o a `undefined`: estensione `[0, 12000]`, etichette
>     `0 | 2k | … | 12k`; nel modello `null` o `undefined`.
> - Scelgo `undefined` esplicito. I tipi di ECharts non ammettono `null` né per `min` (`ScaleDataValue`, `'dataMin'`
>   o una funzione) né per `showMinLabel` (`boolean`), e il frontend compila in `strict`. Il test deve quindi provare
>   che la chiave c'è (`toHaveProperty`), non solo che vale `undefined`: un'opzione che la omette passerebbe.
> - Scartata: `'yAxis'` in `replaceMerge`. Cambierebbe la ricostruzione di ogni modo per un caso solo.
> - La Performance chiama `setOption(…, true)`, cioè `notMerge`: nessun residuo.
> - Nessun altro test fissa l'asse y della Crescita. I `showMinLabel` di `chartCoreHelpers.test.ts` (`:276-732`)
>   riguardano l'asse x della policy responsiva (`responsiveXAxis.ts`). Gli E2E `AXIS_*`
>   (`dashboard.spec.ts:898-900`) accettano già `-` e U+2212, e chiamano il formatter con 20.000, −5.000 e 0:
>   nessun cambio.

**Passo 3 — test rossi e ri-pin, via test-author ✅ 2026-10-01 14:46**

> **Note implementazione:**
> - Test-author (sync), solo `GrowthChart.test.ts` (+257/−16) e `PerformanceChart.test.ts` (+168/−25); nessun
>   componente toccato. Due esecuzioni Vitest nella 6157, una alla volta, nessun server.
> - Ri-pin dei casi esistenti:
>   - S2a, asse mascherato: il segno del negativo viene dalla stessa `toLocaleString` del formatter (helper nuovo
>     `axisNumber`); in più sv-SE forzato, `\u2212•••`;
>   - S2a, privacy spenta: `['-5k','1.3M','0','0']` ora sotto `inLocale('en-US')`, commento «`toFixed`, non
>     `toLocaleString`» riscritto;
>   - S2b: `tickNumber(value, locale?)` rifà la nuova chiamata sul valore con segno; i casi mascherato, toggle e
>     privacy spenta la seguono (`tickNumber(-1500)` al posto di `-${tickNumber(1500)}`, lo zero `'0'` sotto en-US
>     forzato); sv-SE mascherato `\u2212•••`. `SWEDISH` sale al livello del file;
>   - invariati: `'12.3%'` (il ramo `%`) e i `'20k'` di S2a.
> - Casi nuovi, due describe «… axis ticks (S7b: D18, D23, D25)»:
>   - Crescita: le cinque sequenze di D18 in en-US, esatte e distinte, in Abs e nella linea P&L; gli interi (`2k`,
>     `20k`, `1M`, `1.3M`, `900`, `-5k`, `0`, `-0` → `0`); D23 sv-SE in chiaro (`\u22125k`, `\u22121,5k`, `1,5k`)
>     e mascherato; D25 nei quattro modi: `min` funzione, `min({min: -3200, max: 8700}) === -4152`,
>     `showMinLabel: false`; D25 nei Proventi, entrati dalla linea: `toHaveProperty('min', undefined)` su `yAxis` e
>     `toHaveProperty('showMinLabel', undefined)` su `axisLabel` (la chiave deve esserci), poi di nuovo la linea,
>     con funzione e `false`;
>   - Performance: la sequenza −2K…2K esatta e distinta, più `12.5K`, `1.25M`, `2.5`, `0.75`, `-0` → `0`, `2K`;
>     D23 sv-SE in chiaro (`\u22121,5\u00a0tn`) e mascherato; D25: `showMinLabel` e `showMaxLabel` a `false`,
>     `min === -max`, `max` ≈ barra più lunga × 1,05.
> - Rossi, ciascuno per la ragione voluta; nessuno per fixture, setup o tipi:
>   - `growth-chart-memo`: 6 falliti / 48 passati (54). sv-SE mascherato `-•••`; i doppioni `5k 6k 6k …` e
>     `1.0M`; sv-SE in chiaro `-5k -2k 2k`; `showMinLabel` `undefined` nei quattro modi; nei Proventi `min` è
>     ancora la funzione e la chiave `showMinLabel` manca; tornati alla linea, `showMinLabel` `undefined`;
>   - `component-unit PerformanceChart`: 6 falliti / 7 passati / 2185 saltati (2198). `2K` invece di `1.5K` (i
>     tre casi S2b e D18), `13K`, `1M`; sv-SE `-2\u00a0tn`; `showMinLabel` e `showMaxLabel` `undefined`. Due casi
>     S2b si fermano alla prima tacca: le loro righe successive girano solo dopo la cura.
> - Verdi prima e dopo, voluti: S2a a privacy spenta (in en-US vecchio e nuovo formatter scrivono uguale; il caso
>   prova che la privacy spenta non cambia nulla); dentro i rossi, il bordo `-4152`, i limiti della Performance,
>   gli zeri e gli interi già giusti, cioè «il bordo non si sposta».
> - Ho riletto io i due diff e i log: i messaggi d'errore coincidono con le ragioni sopra.
> - Comandi, uno alla volta (log in `/tmp/` e copiati in `files/s7b_probe/` della sessione):
>   - `PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py test --test-port 6157 --data-dir
>     /tmp/librefolio-r2-i-charts front-asset growth-chart-memo` → `/tmp/libreFolio_i_s7b_red_gcm.log`;
>   - stesso prefisso, `front-utility component-unit PerformanceChart` → `/tmp/libreFolio_i_s7b_red_perf.log`;
>   - `frontend/node_modules/.bin/prettier --write`, poi `--check`, sui due file: nessun cambio, pulito.
>
> **⚠️ Fuori pista:**
> - Il test-author ha lanciato anche `svelte-check` in sola lettura, fuori dalla concessione e senza
>   `svelte-kit sync`: nessun problema nei due file; 3 errori e 41 avvisi, quelli noti del pavimento, in altri file.
>   Log: `/tmp/libreFolio_i_s7b_svelte_check.log`.
> - Il caso D25 della Performance fissa anche `max` ≈ barra più lunga × 1,05, il margine di oggi. Lo tengo: è
>   l'oracolo «il bordo non si sposta», come il `-4152` della Crescita.

**Passo 4 — la cura ✅ 2026-10-01 14:50**

> **Note implementazione:**
> - `GrowthChart.svelte` (+21/−9), ramo del denaro di `yAxisFormatter` (`:1999-2012`): scala e suffisso da una
>   tupla (`[1_000_000, 'M']`, `[1_000, 'k']`, `[1, '']`), poi `scaled.toLocaleString(undefined,
>   {maximumSignificantDigits: 15})` e `maskFormattedNumber`:
>   - cifre esatte, quindi nessun doppione e nessun decimale sugli interi (D18);
>   - separatore e meno del locale (D23); lo zero negativo scrive `0`;
>   - segno fuori dalla maschera, `k`/`M` dentro (D8); lo zero mascherato (D12);
>   - quindici cifre significative, non diciassette: assorbono il rumore binario (`0.1 + 0.2` → `0.3`);
>   - tolto l'import di `maskable`: lo usava solo il vecchio formatter.
> - Asse y della Crescita (`:2246-2258`): la costante `incomeBars` (P&L, sottomodo Proventi) decide due chiavi.
>   - Linee, candele e `%`: `min` resta la funzione, più `axisLabel.showMinLabel: false` (D25 = B).
>   - Proventi: `min` e `showMinLabel` presenti a `undefined`, per il fuori pista del passo 2 (`yAxis` si fonde).
>   - Leggere `pnlSubmode` nel costruttore non aggiunge dipendenze: `renderChart` lo legge già in
>     `renderedModeKey` (`:1949`).
> - `PerformanceChart.svelte` (+10/−5):
>   - `axisTickAmount` (`:183-189`) passa l'importo con segno a un solo `Intl.NumberFormat` compatto, con
>     `maximumSignificantDigits: 15`, e poi a `maskFormattedNumber`; `maskable` resta per `shortMoney`;
>   - `xAxis.axisLabel` (`:999-1006`): `showMinLabel` e `showMaxLabel` a `false`; `±axisBound` e `splitNumber: 4`
>     invariati.
> - Un solo consumatore per ciascun formatter: `axisTickAmount` solo l'asse x (`:1001`), `yAxisFormatter` solo
>   l'asse y (`:2258`). Nessuna etichetta non tonda, come una markLine, diventa lunga per le cifre esatte.
> - Verdi nella 6157, uno alla volta, nessun server:
>   - `growth-chart-memo`: 54/54 → `/tmp/libreFolio_i_s7b_green_gcm.log`;
>   - `component-unit PerformanceChart`: 13 passati / 2185 saltati (2198) →
>     `/tmp/libreFolio_i_s7b_green_perf.log`.
> - Prettier `--write` sui due componenti: nessun cambio; `--check` sui quattro file: pulito. Diff della cura:
>   `/tmp/libreFolio_i_s7b_fix.diff`.
> - Comandi: gli stessi del passo 3, con i log `green` al posto dei `red`.
> - Nessun fuori pista.

**Passo 5 — gate nella 6157 ✅ 2026-10-01 15:00**

> **Note implementazione:** un comando alla volta, con `PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run
> python dev.py`; i `test` con `--test-port 6157 --data-dir /tmp/librefolio-r2-i-charts`. Log in
> `/tmp/libreFolio_i_s7b_{build,check,core,comp,assetunit,orphans,e2e_dashboard,e2e_broker}.log`.
>
> | # | gate | esito |
> |---|---|---|
> | 1 | `front build --debug` (14:52) | rc 0 |
> | 2 | `front check` | 3 errori e 41 avvisi in 4 file, rc 1: il floor |
> | 3 | `front-utility core-unit` | 2684/2684 su 102 file |
> | 4 | `front-utility component-unit` | 2198/2198 su 94 file |
> | 5 | `front-asset asset-unit` | 530/530 su 19 file |
> | 6 | `front-asset growth-chart-memo` | 54/54, il verde del passo 4 |
> | 7 | `check-orphans` | rc 0: 92 E2E, 275 unit, 224 backend raggiungibili |
> | 8 | E2E `front-portfolio dashboard` | 24/24, 1 worker, 1,3 min |
> | 9 | E2E `front-broker detail` | 32/32, 1 worker, 1,1 min |
>
> - 1: la build rigenera i contratti OpenAPI e TypeScript; nessun file tracciato è cambiato. Serve agli E2E.
> - 2: `BrokerSharingPanel` 27, `GlobalSettingsTab` 14, `TransactionFormModal.test.ts` 2,
>   `ToolExecutionMetrics` 1; nessuna riga su GrowthChart o PerformanceChart.
> - 3: dentro, i gate di K `htmlInterpolation.gate.test.ts` e `htmlSink.gate.test.ts`.
> - 4: tre casi in più del gate del merge (2195): quelli nuovi di `PerformanceChart.test.ts`.
> - 6: non rilanciato. Il verde del passo 4 è finito alle 14:48:55; i due componenti sono fermi alle 14:48:04 e
>   14:48:23, i due test alle 14:34 e 14:38.
> - 8: `:948` e `:983`, gli assi in privacy (S2a e S2b), verdi senza toccare lo spec: gli `AXIS_*`
>   (`:898-900`) accettano già `-` e U+2212. `:1530`, S7-E2: i Proventi sulla scala.
> - 9: `:1072`, linea e Proventi del P&L del broker: il sottomodo Proventi, ora con i default di ECharts, in un
>   render reale.
> - Nessun retry, nessun flaky. A fine giro: porte 6157 e 6167 libere (`lsof`); `git diff --check` pulito; stage
>   vuoto; 0 file non tracciati; 5 file tracciati modificati.
> - Non lanciati, fuori dal delta: il vitest completo; l'`i18n audit` (nessuna chiave); il backend (nessun file
>   Python); l'E2E `asset-detail`, che non ha assi del denaro (`asset-detail.spec.ts:2352-2370` legge l'asse
>   delle date).

**Passo 6 — registro e `CHECKPOINT READY` (C9) ✅ 2026-10-01 15:02**

> **Note implementazione:**
> - Base `cd6502084`. Delta: 5 file tracciati modificati, nessun file nuovo, stage vuoto:
>   - `frontend/src/lib/components/dashboard/GrowthChart.svelte` (+21/−9);
>   - `frontend/src/lib/components/dashboard/PerformanceChart.svelte` (+10/−5);
>   - `frontend/src/lib/components/dashboard/GrowthChart.test.ts` (+257/−16);
>   - `frontend/src/lib/components/dashboard/PerformanceChart.test.ts` (+168/−25);
>   - questo piano.
> - Esclusi: la build, i log, l'istantanea del DB (`00_archive/test-db_20261001_145647.tar.xz`), le sonde in
>   `/tmp/`.
> - Commit proposti, due, come in C7:
>   1. `fix(charts): keep money axis ticks distinct`, i quattro file del frontend. Il soggetto del piano (`:580`)
>      diceva «Y axis», ma l'asse del denaro della Performance è l'x;
>   2. `docs(journal): record S7b and D25`, questo piano.
> - Proposte per i registri del coordinator:
>   - `desc` di `growth-chart-memo` (`scripts/test_runner/_frontend_asset.py:189`), in coda: «, and the money
>     axis ticks (S7b): exact, distinct labels (D18), the locale's minus (D23), the auto-scaled lower edge
>     unlabelled while Income keeps ECharts' zero-based defaults (D25)»;
>   - CHANGELOG, 🐛 Fixed: «The amount axes of the Growth and Performance charts no longer show the same label
>     twice (`5.5k` printed as `6k` next to a real `6k`, `1.25M` as `1.3M`) and use the minus sign of the
>     browser's language. An axis edge placed automatically beyond the data is no longer labelled as if it were
>     a regular step, and the Income bars stand on an axis that starts at zero.»
> - Conflitti attesi: nessuno. Il delta non tocca `lineChartHelpers.ts` né il suo test (Risk, `840bdbc0d`), né
>   file condivisi o registri del coordinator.
> - Stato: FROZEN, nessun edit, test, server o Git fino al prossimo messaggio del coordinator.
