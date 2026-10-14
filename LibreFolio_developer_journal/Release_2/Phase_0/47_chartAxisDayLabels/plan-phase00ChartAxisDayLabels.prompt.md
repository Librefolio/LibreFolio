# Piano — fase 00, 47: il giorno sulle etichette dell'asse x dei grafici a linee

> **Stato**: ✅ consegnato il 2026-10-12 col checkpoint (§9, passo 8), in attesa dell'integrazione.
>
> - **Mandato**: coordinatore di Release 2 (`c8328a01-…`). È la prima voce della coda di I dopo M-16: una regressione che il developer ha segnalato durante le verifiche sul server, più la voce 1 del coordinatore (le serie ferme della P&L a linee).
> - **Workstream I**. Ramo `e-alfy-performance-charts-plan`. Base `bdc078efc`. Il coordinatore riallinea al target (`d33fca26f`, treno 52) al checkpoint; nei treni 51–52 non c'è niente di I.
> - **Corsia**: `--test-port 6157 --data-dir /tmp/librefolio-r2-i-charts`, con `PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py test …`, un comando alla volta. Mai le porte 6040 e 6041, mai la galleria.
> - **Origine**: (A) viene da `2d22130bd` (I, 17/09), che ha introdotto `frontend/src/lib/components/charts/responsiveXAxis.ts`; la voce 1 dalle linee dei broker di `8ed7a0f0d` (18/09). Entrambi sono nuovi nella 1.2.

## 0. Autorizzazione (2026-10-12)

- **Developer**, la segnalazione, testuale: «su moltissimi grafici nell'asse x è scomparso il numero del giorno! anche se lo spazio c'è, l'ho visto in abs e % in dashboard, in asset detail e forex detail, mentre è corretto in candele e proventi del P&L. La differenza è che lì sono dei bucket e quindi cerchiamo di dare un nome significativo al cestino, gli altri sono grafici a linee e se si riesce, con lo spazio, a mettere più riferimenti temporali è una cosa buona!»
- **Developer**, sull'analisi di I, testuale:
  1. «**1 ago**: anche il primo del mese col suo giorno, come le altre etichette»;
  2. «**Sì, procedi; e sistema anche il percorso non compatto nello stesso lotto, con un commit a parte**».
- **Coordinatore**, sulle scelte di I:
  - «2026» al 1° gennaio, come da prova;
  - la voce 1 con `seriesKey`;
  - il punto 3 dell'analisi (sotto zoom gli assi a categoria si diradano, difetto preesistente) va nella sezione I del backlog post-1.2, priorità bassa;
  - il piano qui, col numero 47;
  - la frase nella descrizione di `growth-chart-memo` la aggiunge I, in questo lotto;
  - la riga 🔄 del CHANGELOG la scrive il coordinatore all'integrazione, col testo proposto da I (§8). Per la voce 1 niente riga: le linee dei broker non sono mai uscite in una versione.

## 1. I difetti

### 1.1 (A) Il mese ripetuto sugli assi compatti

- `formatCompactXAxisDate` (`responsiveXAxis.ts:35-40`) sceglie il formato dalla sola ampiezza del periodo: oltre l'anno «MMM yy», oltre i 90 giorni «MMM», altrimenti «d MMM».
- La modalità compatta (`:45`) scatta con meno di 480 px utili, o con meno di 24 px per punto. Con punti giornalieri, quindi, quasi su ogni periodo lungo.
- ECharts mette un tick ogni 7–10 giorni, e su un periodo di oltre 90 giorni ognuno stampa solo il mese. È lo screenshot del developer: Crescita in Abs, luglio–ottobre, circa 800 px, «lug lug ago ago ago ago set set set set ott ott ott».
- **Misura**, con una simulazione SSR su ECharts 6 reale: 249 coppie consecutive uguali sugli assi time compatti (96 casi) e 163 sugli assi category compatti (144 casi).

### 1.2 Il percorso non compatto (stesso lotto, commit a parte)

- Fuori dalla modalità compatta la policy restituisce solo `{compact, maxLabels}`, quindi le etichette restano quelle di default di ECharts:
  - sugli assi time sono in inglese, perché ECharts non riceve la lingua: «Feb», «Aug»;
  - sugli assi category sono le date ISO: «2026-07-15».
- I tre grafici dei lotti hanno un formatter loro, `formatAxisDate(…, multiYearAxis)`:
  - su un periodo breve i tick sono orari, e il formatter ripete il giorno: «20 ott | 20 ott | 20 ott | 21 ott …». Nella simulazione sono 28 coppie uguali sull'asse senza margine e 32 su quello col margine delle bolle;
  - su più anni stampa la data intera: «1 gen 2025 | 1 lug 2025».

### 1.3 Voce 1: le serie ferme della P&L a linee (GrowthChart)

- L'aggiornamento parziale (`updateChartData`, `GrowthChart.svelte:1767-1831`) manda le serie con `CHART_SERIES_UPDATE_OPTS` = `{notMerge: false, replaceMerge: ['dataZoom']}` (`:510`). ECharts le fonde per posizione, e la legenda non si tocca: la sua `data` esiste solo nel build completo.
- `renderChart` (`:1997-2072`) sceglie il build completo solo se cambiano la modalità, il tema o il mascheramento (`needsFullInit`, `:2060`). Un cambio dell'insieme dei broker, quindi, passa dal parziale.
- **Riprova sulla stessa ECharts**, rigiocando le chiamate di oggi (`xaxis_evidence/libreFolio_i_stale_series_sim.*` nei file della sessione di I):

| Caso | Broker | Oggi | Col build completo |
|---|---|---|---|
| R1 | A, B, C → A | B e C restano, nelle serie e in legenda (il difetto segnalato) | solo A |
| R2 | A, B → nessuno (la sovrapposizione si spegne sotto i 2 broker) | A e B restano | solo il totale |
| R3 | A, B → A, B, C | C non si disegna: «[ECharts] Unknown series undefined» | A, B, C |
| R4 | A, B → A, C | C prende il posto di B, ma la legenda ha ancora B e non ha C | A, C |
| R5 | lo stesso insieme | giusto | giusto |
| lingua | % in italiano → inglese | la legenda dice «MWRR cumulato», la serie si chiama «Cumulative MWRR», e la voce non si disegna | giusto |

## 2. Le regole (approvate)

### 2.1 Asse time

Il formatter riceve `(value, index, {level})`, come lo chiama ECharts 6. `labelEndpoints` vale `true` in modalità compatta e `false` altrimenti.

| Tick | Etichetta | Esempio |
|---|---|---|
| un estremo dei dati, solo con `labelEndpoints` | «d MMM», più l'anno a 2 cifre se i dati attraversano un anno | «14 lug», «30 mar 25» |
| un tick che non cade a mezzanotte | vuota | i tick orari dei lotti |
| la mezzanotte del giorno dell'ultimo estremo, se questo non cade a mezzanotte (solo con `labelEndpoints`) | vuota | evita «21 ott \| 21 ott» |
| il 1° gennaio | l'anno | «2026» |
| il 1° del mese, se `level > 0` (fra tick giornalieri) | «d MMM» | «1 ago» |
| il 1° del mese, se `level` è 0 (i tick sono i mesi) | «MMM» | «ago» |
| ogni altro giorno | «d MMM» | «15 ago» |

- Senza `labelEndpoints` non c'è la regola degli estremi né la guardia, perché ECharts nasconde comunque le etichette di bordo di un asse time (`showMinLabel` e `showMaxLabel` sono `false` di default). Con la guardia attiva, l'ultimo giorno dei lotti perderebbe l'etichetta.
- Un valore che non è una data torna com'è.

### 2.2 Asse category

- **Compatto** (`interval` noto, `step = interval + 1`):
  - **modo mese** solo se ogni coppia di etichette regolari consecutive cade in un mese diverso: allora «MMM», altrimenti «d MMM»;
  - un'etichetta fuori passo (bordo o zoom) è sempre «d MMM»;
  - l'anno a 2 cifre si aggiunge quando l'anno cambia rispetto all'etichetta regolare precedente, e sugli estremi quando i dati attraversano un anno;
  - l'indice si legge da una `Map(String(valore) → posizione)`; un valore sconosciuto dà «d MMM», con l'anno se i dati lo attraversano; un valore che non è una data torna com'è.
- **Non compatto (N2)**: ECharts sceglie da sé quali etichette mostrare, e il formatter non può saperlo. Per questo ogni etichetta porta tutto ciò che serve:
  - dati mensili (ogni coppia consecutiva in un mese diverso): «MMM», oppure «MMM yy» se i dati attraversano un anno;
  - altrimenti «d MMM», oppure «d MMM yy» se i dati attraversano un anno.

### 2.3 Le garanzie

- Due etichette consecutive non sono mai uguali: 0 coppie in tutte le famiglie simulate (§6).
- Candele e Proventi della P&L restano come sono: il loro asse è quello del ladder dei bucket, non questa policy.
- Le istanze di `Intl.DateTimeFormat` si costruiscono una volta per policy, non a ogni etichetta.

## 3. La cura e la divisione in commit

- **C1, le regole compatte**: `responsiveXAxis.ts` costruisce il formatter compatto con le regole di §2.1 e §2.2. La forma della policy non cambia. Spariscono `formatCompactXAxisDate` e `dateSpanDays`.
- **C2, la voce 1**: `GrowthChart.svelte` calcola `seriesKey`, i nomi delle serie in ordine.
  - Se la chiave cambia rispetto all'ultimo disegno, `renderChart` prende la strada completa, che sostituisce serie e legenda.
  - La chiave si azzera insieme alle altre `lastRendered*` quando l'istanza viene distrutta.
  - `CHART_SERIES_UPDATE_OPTS` non cambia; il ramo della risoluzione (`:1865`) non cambia i nomi.
  - La frase nel runner (`growth-chart-memo`) va in questo commit.
- **C3, il percorso non compatto** (il «commit a parte» del developer):
  - la policy porta sempre `formatter`; `axisLabel` resta solo compatto, e lì `axisLabel.formatter === formatter` (forma «Y»);
  - ogni grafico mette `formatter: xAxisPolicy.formatter` prima di `...(xAxisPolicy.axisLabel ?? {})`;
  - l'aggiornamento parziale di GrowthChart manda il formatter nuovo anche fuori dalla modalità compatta, perché la chiusura dipende dalle date;
  - i tre grafici dei lotti usano `xAxisPolicy.formatter` al posto di `formatAxisDate(…, multiYearAxis)`, e `multiYearAxis` sparisce;
  - le callback di resize non cambiano: da non compatto a non compatto la chiusura resta valida, perché le date non cambiano; da compatto a non compatto ricostruiscono già tutto.
- **C4, il journal**: questo piano e la voce Q3 nella sezione I di `BACKLOG_POST_1.2.md`.

`chartCoreHelpers.test.ts` e `GrowthChart.svelte` cambiano in due commit ciascuno. Per questo, dopo ogni commit verde, I salva lo stato dei suoi file nei file della sessione (`xaxis_commit_bundle/stage_C{n}/`), e il manifest del checkpoint dà un blob per stadio.

## 4. Superfici

| File | Cosa | Commit | Chi |
|---|---|---|---|
| `frontend/src/lib/components/charts/responsiveXAxis.ts` | le regole; poi `formatter` sempre presente | C1, C3 | I |
| `frontend/src/lib/components/dashboard/GrowthChart.svelte` | `seriesKey`; poi il formatter nel build completo e nel parziale | C2, C3 | I |
| `frontend/src/lib/components/charts/LineChart.svelte`, `PriceChartFull.svelte`, `CandlestickChart.svelte` | il formatter nel build completo | C3 | I |
| `frontend/src/lib/components/dashboard/AllocationHistoryChart.svelte` | il formatter nel build completo | C3 | I |
| `frontend/src/lib/components/brokers/lots/LotWacPriceChart.svelte`, `LotGanttChart.svelte`, `LotComparisonChart.svelte` | `xAxisPolicy.formatter` al posto del formatter proprio | C3 | I |
| `frontend/src/lib/components/charts/chartCoreHelpers.test.ts` | i rossi di C1 e di C3, e i pin che cambiano | C1, C3 | `test-author` |
| `frontend/src/lib/components/dashboard/GrowthChart.test.ts` | il rosso di C2 | C2 | `test-author` |
| `scripts/test_runner/_frontend_asset.py` | una frase nella descrizione di `growth-chart-memo` | C2 | I |
| questo piano; `BACKLOG_POST_1.2.md` (solo la sezione I) | il journal | C4 | I |

- **Fuori**: le chiavi i18n (non servono: i testi vengono da `Intl`), il backend, la galleria, il ladder di Candele e Proventi, l'asse nascosto del Gantt (`LotGanttChart.svelte:1028`, `show: false`) e il diradarsi degli assi category sotto zoom (Q3, nel backlog).
- **Considerato e scartato**: cambiare i parametri di default di `buildLotXAxisPolicy()` nelle callback di resize. Nel Gantt e nel confronto i default leggono già `xAxisRange`, cioè il `computedRange` di `LotsAnalysisPanel`, sempre presente quando ci sono dati; senza dati l'asse non si tocca (le guardie `axisOptionSet` e `chartOptionSet`). Il cambio non correggerebbe niente e allargherebbe il lotto.

## 5. I test

Tutti via `test-author`, rossi prima della cura. Due giri, perché `chartCoreHelpers.test.ts` cambia sia in C1 sia in C3 e ogni commit deve avere i suoi test verdi.

- **Giro A, C1 e C2**:
  - il caso dello screenshot, su ECharts reale in SSR: dati giornalieri da luglio a ottobre, circa 800 px, modalità compatta. Nessuna coppia consecutiva uguale, il giorno presente, «1 ago» sul tick di livello > 0;
  - gli assi category compatti su 3 e 6 mesi, giornalieri;
  - il test DST: gli estremi compatti diventano «d MMM yy»;
  - un asse dei lotti che finisce a un'ora qualsiasi: niente doppioni del giorno;
  - il test della lingua che oggi importa `formatCompactXAxisDate` passa per la policy;
  - **C2**: GrowthChart in P&L a linee, l'insieme dei broker cambia (R1, R3, R4). Le chiamate registrate dal finto ECharts si rigiocano su un'istanza vera (`vi.importActual('echarts')`), e alla fine serie e legenda corrispondono ai broker nuovi.
- **Giro B, C3**:
  - fuori dalla modalità compatta la policy porta un formatter in lingua: time e category, con e senza cambio d'anno, dati mensili;
  - i pin che oggi vogliono `{compact: false, maxLabels}`, un formatter `undefined` dopo la ricostruzione, la riga esatta del parziale di GrowthChart e il `formatAxisDate(…, multiYearAxis)` dei lotti.

## 6. Prove già raccolte (prima del codice)

Simulazioni SSR con l'ECharts 6 del progetto e le regole di §2 portate in JS. Gli script e i log sono nei file della sessione di I, in `xaxis_evidence/`.

| Famiglia | Oggi | Con le regole |
|---|---|---|
| time compatto, 96 casi | 249 coppie uguali | 0 |
| category compatto, 144 casi | 163 coppie uguali | 0 |
| lotti, periodi brevi, senza e con margine (28 casi ciascuno) | 28 e 32 coppie uguali | 0 |
| time non compatto | default inglesi («Feb», «Aug») | in lingua, 0 coppie uguali |
| category non compatto | date ISO | in lingua, 0 coppie uguali |

Nessun asse resta vuoto in nessuna famiglia. Esempi dell'anno:

- time: «… 31 dic | 2026 | 3 gen …», «apr | lug | ott | 2025 | …»;
- category: «nov 24 | gen 25 …», «17 dic 25 | … | 8 gen 26»;
- lotti su 2 anni: «2025 | apr | lug | ott | 2026 …», dove oggi è «1 gen 2025 | 1 lug 2025 …»;
- lotti su un giorno: «21 ott», dove oggi è «20 ott» tre volte e «21 ott» tre volte.

Altre verifiche:

- la prima etichetta vera non si perde col `showMinLabel: false` di default;
- ogni `setOption` parziale riceve un formatter fresco. Fa eccezione solo l'aggiornamento parziale di GrowthChart, che C3 corregge;
- le opzioni scartate:
  - **N1**, il compatto con passo 1 anche fuori dalla modalità compatta: l'anno a metà asse si perde se ECharts salta proprio quel punto;
  - **N3**, un `interval` esplicito fuori dalla modalità compatta: rischio di sovrapposizioni senza `hideOverlap`, e confonde le due modalità;
  - **la forma X**, `axisLabel` sempre presente: costringe a cambiare otto callback di resize e molti più pin.

## 7. Definizione di fatto

- Le regole di §2 sono nel codice, e i rossi di §5 sono verdi.
- Selettori, uno alla volta sulla 6157:
  - Vitest: `front-asset asset-unit`, `front-asset growth-chart-memo`;
  - E2E: `front-portfolio dashboard`, `front-asset asset-detail`, `front-fx fx-detail`, `front-broker detail`;
  - statici: `front check` e `prettier --check` sui file toccati.
- La galleria non si lancia.
- Il backlog contiene Q3, e il runner la frase.
- Il checkpoint ha manifest, partizione in C1–C4 e messaggi. La porta 6157 è libera.

## 8. CHANGELOG (lo scrive il coordinatore)

Proposta per la riga 🔄: «Line charts label their time axis by the gap between ticks: the day when ticks are less than a month apart, the month otherwise, the year at its turn; labels follow the app language and never repeat».

## 9. Avanzamento

- [x] **0. Analisi e prove** (2026-10-12): §1, §2 e §6.
- [x] **1. Giro A di `test-author`**: i rossi di C1 e C2, verificati rossi (2026-10-12).
  > **Note implementazione**: `test-author` ha scritto i rossi nei due file di test, senza toccare il codice di prodotto. I li ha rilanciati da sé, un file alla volta (`./node_modules/.bin/vitest run <file>`):
  > - `chartCoreHelpers.test.ts`: 11 rossi e 146 verdi (prima 150 su 150). 7 test nuovi, «(plan 47, C1)», e 4 attese compatte adattate: i due casi DST, il ritorno al desktop su più anni e il formatter dei lotti. Il caso dello screenshot, renderizzato in SSR, dà oggi `lug | lug | ago | ago | ago | ago | set | set | set | set | ott | ott | ott | ott`. La category giornaliera dà `apr | apr | mag | mag | …`. Le asserzioni desktop e i pin di C3 restano come sono;
  > - `GrowthChart.test.ts`: 3 rossi e 133 verdi (prima 132 su 132). Sono R1, R3 e R4 col meccanismo (oggi passa ancora l'aggiornamento parziale: `fullRebuild: false`, legenda vuota) e col comportamento, rigiocato su un ECharts vero. Quando un broker esce, C resta disegnato e in legenda; nello scambio la legenda tiene B; quando un broker entra, C manca. Il controllo, cioè gli stessi broker con importi nuovi, resta sul parziale ed è verde;
  > - log: `/tmp/libreFolio_i_xaxis_red_chartcore.log` e `/tmp/libreFolio_i_xaxis_red_growth.log`.
  >
  > **Fuori pista**:
  > - nel render SSR di Node, con le regole nuove, il caso dello screenshot dà 11 etichette e non 14 come nella simulazione di §6: zrender misura il testo con larghezze di ripiego e `hideOverlap` ne nasconde di più. Le asserzioni non dipendono dal numero esatto;
  > - nel caso category su 6 mesi l'`interval` è 11 e non 10, perché i giorni feriali sono 131;
  > - nel caso su 12 mesi l'ultimo indice è un'etichetta regolare, quindi si attende «set 26» e non «30 set 26». Il test lo ricava dall'`interval` della policy.
- [x] **2. C1**: le regole compatte (2026-10-12).
  > **Note implementazione**:
  > - `responsiveXAxis.ts` ha ora due costruttori:
  >   - `buildTimeAxisFormatter` segue l'ordine di §2.1: gli estremi dei dati, poi niente etichetta fuori dalla mezzanotte, poi il giorno, il 1° gennaio come anno, e il 1° del mese come mese solo al livello 0;
  >   - `buildCategoryAxisFormatter` segue §2.2: il mese solo se ogni coppia di etichette regolari cade in mesi diversi, l'anno dove cambia e agli estremi di un asse che lo attraversa, e il giorno fuori dalla griglia.
  > - I formati `Intl` si costruiscono una volta per policy.
  > - Il tipo `ResponsiveXAxisFormatter` accetta il terzo argomento di ECharts (`time.level` e l'alias `level`).
  > - La forma della policy non cambia. `formatCompactXAxisDate` e `dateSpanDays` spariscono: li importava solo il test.
  > - Prettier: invariato.
  > - Verifica, un file alla volta:
  >   - `chartCoreHelpers.test.ts`: 157 su 157 (`/tmp/libreFolio_i_xaxis_c1_chartcore.log`);
  >   - `GrowthChart.test.ts`: 133 verdi e i soli 3 rossi di C2 (`/tmp/libreFolio_i_xaxis_c1_growth.log`).
  > - Gli altri test che leggono `axisLabel` sono assi di importi (`PerformanceChart`, `ScatterChart`), l'asse a scala di candele e proventi (galleria, `dashboard.spec.ts`) o i dati grezzi dell'asse (`asset-detail.spec.ts`), quindi C1 non li tocca.
  > - Istantanea: `files/xaxis_commit_bundle/stage_C1/` nella sessione, con i blob `a747bb14` (`responsiveXAxis.ts`) ed `e5d6bf10` (test).
- [x] **3. C2**: `seriesKey` e la frase del runner (2026-10-12).
  > **Note implementazione**:
  > - In `renderChart`, `seriesData` sale sopra `needsFullInit`. È lo stesso calcolo, che prima veniva subito dopo.
  > - `seriesKey` sono i nomi delle serie in ordine, uniti da `\u0000`, e diventa il quinto innesco del build completo (`lastRenderedSeriesKey !== seriesKey`).
  > - `lastRenderedSeriesKey` si azzera insieme agli altri `lastRendered*` quando l'istanza viene rifatta, e si aggiorna dopo il disegno.
  > - `updateChartData` non cambia. Il cambio di risoluzione (`syncResolutionToViewport`) passa di lì, ma i broker vengono dalla stessa `inputs.pnlBrokerSeriesRaw` in ogni risoluzione (`:1088`, `:1137`), quindi lì l'insieme non cambia.
  > - Il pin `chartCoreHelpers.test.ts:1944-1946` legge gli inneschi come insieme, quindi regge.
  > - Il runner: la frase sulla P&L a linee ricostruita quando cambia l'insieme dei broker, in coda alla descrizione di `growth-chart-memo` (`_frontend_asset.py:202`). Il file si analizza e la voce compare nell'aiuto di `dev.py test front-asset`.
  > - Prettier: invariato.
  > - Verifica:
  >   - `GrowthChart.test.ts`: 136 su 136 (`/tmp/libreFolio_i_xaxis_c2_growth.log`);
  >   - `chartCoreHelpers.test.ts`: 157 su 157 (`/tmp/libreFolio_i_xaxis_c2_chartcore.log`).
  > - Istantanea: `stage_C2/`, con `GrowthChart.svelte` `3a7ac33a`, il test `fa2be2b4` e il runner `b4f94248`.
- [x] **4. Giro B di `test-author`**: i rossi di C3, verificati rossi (2026-10-12).
  > **Note implementazione**:
  > - `test-author` ha scritto solo in `chartCoreHelpers.test.ts`. Gli altri quattro file e il runner hanno gli stessi blob delle istantanee C1 e C2.
  > - 16 test nuovi, «(plan 47, C3)», tutti costruiti da un helper (`policyFormatter`) che prima verifica `compact` e il tipo di `policy.formatter`, così il rosso nomina il campo che manca:
  >   - time non compatto, 6 test: un tick per tipo (giorno, mese al livello 0, «1 ago» al livello > 0 anche col solo `time.level` o col solo alias `level`, fuori dalla mezzanotte, non leggibile); gli estremi di un asse che attraversa l'anno, senza anno (in compatto con l'anno); il 1° gennaio come anno; la mezzanotte dell'ultimo giorno dei lotti, nominata (in compatto vuota); la lingua; i due cambi d'ora di Europe/Rome;
  >   - category non compatto, 5 test: giornaliero con e senza cambio d'anno (il 1° del mese e il 1° gennaio compresi), mensile con e senza cambio d'anno, settimanale, irregolare, un valore solo, un valore non leggibile, un valore fuori dai dati, la lingua;
  >   - compatto, 2 test: un solo formatter, lo stesso in cima e in `axisLabel`, per time e category;
  >   - SSR con ECharts vero, 3 test: giornaliero a cavallo di un mese, mensile su tre anni, category giornaliero a cavallo dell'anno. Etichette solo in lingua, nessuna data ISO, nessuna coppia consecutiva uguale.
  > - 20 casi riscritti, cioè i pin del vecchio contratto: la policy desktop con `formatter`, l'ordine di fusione dei grafici, i due rigiochi di GrowthChart (`toBe(desktopPolicy.formatter)` al posto di `toBeUndefined()`), la regex sorgente sugli 8 grafici, la riga esatta del parziale, il build completo al resize e i tre lotti senza `multiYearAxis`.
  > - Verifica di I (`./node_modules/.bin/vitest run`, `/tmp/libreFolio_i_xaxis_red_c3.log`): 36 rossi e 137 verdi su 173. I rossi sono i 16 nuovi e i 20 riscritti, i verdi sono i 157 di prima meno i 20 riscritti. Prettier `--check`: ok.
  >
  > **Fuori pista**:
  > - per provare che i rossi diventano verdi, `test-author` ha avvolto per una sola corsa la policy nel file di test con un formatter scritto da lui. Con quell'involucro: 160 verdi; restavano rossi solo i 13 pin sorgente, che aspettano i file dei grafici. Poi l'ha tolto: il grep non ne trova traccia;
  > - il controllo facoltativo degli estremi desktop nel test DST esistente non è stato aggiunto: in C3 entrambi gli estremi di un periodo di 365 giorni sono «30 mar», contro il titolo del test («distinct endpoints»). Fuori dalla modalità compatta ECharts non disegna gli estremi di un asse time (`showMinLabel`/`showMaxLabel` falsi di default), e il 30 non è un tick di una griglia mensile, quindi a schermo non c'è doppione. Il caso desktop lo coprono i due test DST nuovi;
  > - il test SSR mensile verifica l'anno al 1° gennaio 2025 e 2026, non 2024: è il primo punto, che ECharts non disegna di default;
  > - fino a C3, `front check` dà TS2339 su `policy.formatter`. Vitest non controlla i tipi, quindi le corse non ne risentono;
  > - `test-author` ha usato qualche comando di sola lettura fuori dall'elenco concesso (`git log`, `wc`, `cat -n`, `git hash-object`). Nessuna modifica.
- [x] **5. C3**: il percorso non compatto (2026-10-12).
  > **Note implementazione**:
  > - `responsiveXAxis.ts` è la bozza C3 dei file della sessione (`drafts/responsiveXAxis.C3.ts`, identica). La policy porta sempre `formatter`: fuori dalla modalità compatta è esattamente `{compact: false, maxLabels, formatter}`, in compatto lo stesso riferimento sta in cima e in `axisLabel`.
  >   - time: il 1° gennaio si controlla prima del livello; gli estremi dei dati e la mezzanotte di un ultimo giorno che finisce a metà giornata valgono solo in compatto;
  >   - category non compatta (`interval` nullo, passo 1): i dati sono «mensili» se hanno almeno due valori, tutti leggibili, e ogni coppia consecutiva cade in mesi diversi. Allora il mese, con l'anno se il primo e l'ultimo valore cambiano anno; altrimenti giorno e mese, con l'anno nello stesso caso, su ogni etichetta. Un valore fuori dai dati segue la stessa regola.
  > - Gli otto grafici mettono il formatter della policy subito prima di `...(xAxisPolicy.axisLabel ?? {})`, così in compatto le chiavi di `axisLabel` restano sopra:
  >   - `LineChart.svelte`, `PriceChartFull.svelte`, `CandlestickChart.svelte`, `AllocationHistoryChart.svelte`, e GrowthChart nel build completo del ramo time (`xAxisPolicy?.formatter`, `:2370`);
  >   - il parziale di GrowthChart (`:1806`) manda `{axisLabel: {formatter: xAxisPolicy.formatter}}` fuori dalla modalità compatta, dove prima mandava `{}`;
  >   - i tre lotti usano `xAxisPolicy.formatter` al posto di `formatAxisDate(…, multiYearAxis)`, e `multiYearAxis` sparisce. `LotComparisonChart` non importa più `formatAxisDate`; Gantt e WAC sì, perché lo usano ancora (l'asse nascosto del Gantt a `:1028`, l'helper e il tooltip del WAC a `:287` e `:873`). Il commento del WAC sui limiti grezzi ora parla della policy.
  > - Prettier `--write` e `--check` sugli 11 file: invariato, ok.
  > - Verifica, un file alla volta (`./node_modules/.bin/vitest run`):
  >   - `chartCoreHelpers.test.ts`: 173 su 173 (`/tmp/libreFolio_i_xaxis_c3_core.log`). I 36 rossi del giro B sono verdi, compresi i 13 pin sorgente;
  >   - `GrowthChart.test.ts`: 136 su 136 (`/tmp/libreFolio_i_xaxis_c3_growth.log`);
  >   - gli altri 22 file di test che nominano i grafici toccati o `responsiveXAxis` (gli helper dei lotti, di LineChart, delle candele e dei prezzi, `AllocationHistoryChart`, `moneyRenderSites` e altri), in una corsa: 955 su 955 (`/tmp/libreFolio_i_xaxis_c3_related.log`).
  > - Istantanea: `stage_C3/`, con `responsiveXAxis.ts` `b8033088`, il test `f4a8ab8a`, `GrowthChart.svelte` `1a1ec57a`, `LineChart.svelte` `1a70d8b7`, `PriceChartFull.svelte` `c62aa5c0`, `CandlestickChart.svelte` `ebe53571`, `AllocationHistoryChart.svelte` `ba4fe0e0`, `LotGanttChart.svelte` `0699cc1f`, `LotComparisonChart.svelte` `80def5bc` e `LotWacPriceChart.svelte` `a6837540`. `GrowthChart.test.ts` e il runner restano ai blob di C2.
  >
  > **Fuori pista**:
  > - §3 motiva il parziale di GrowthChart con «la chiusura dipende dalle date». Fuori dalla modalità compatta, sull'asse time, non è così: gli estremi non contano e il formatter dipende solo dalla lingua. Il passaggio da compatto a non compatto ricostruisce già tutto (`:1801-1803`), e un cambio di lingua ridisegna il grafico, quindi il parziale non compatto segue sempre un disegno col formatter della stessa lingua. L'invio è coerenza, perché ogni `setOption` porta il suo formatter come negli altri grafici, ed è il pin del giro B; non cura un difetto visibile. La frase di §3 vale per la category e per il compatto.
- [x] **6. I selettori** di §7 (2026-10-12).
  > **Note implementazione**:
  > - Sulla 6157, un comando alla volta, tutti verdi:
  >   - Vitest: `front-asset asset-unit`, 20 file e 757 test (`/tmp/libreFolio_i_xaxis_sel_asset_unit.log`); `front-asset growth-chart-memo`, 136 (`…_sel_growth_memo.log`);
  >   - E2E: `front-portfolio dashboard` 27, `front-asset asset-detail` 32, `front-fx fx-detail` 17, `front-broker detail` 37 (`…_sel_dashboard.log`, `…_sel_asset_detail.log`, `…_sel_fx_detail.log`, `…_sel_broker_detail.log`).
  > - Statici, sullo stato finale: `dev.py front check` con 0 errori e 0 avvisi (`…_front_check2.log`); `prettier --check` sugli 11 file del frontend: ok (`…_prettier_final.log`).
  > - Dopo la correzione qui sotto, `front-asset asset-unit` rilanciato sul test finale: 757 su 757 (`…_sel_asset_unit2.log`). Gli E2E non leggono quel file.
  > - Ogni commit compila da solo. Gli stati C1 e C2, rimessi nella worktree uno dopo l'altro (HEAD più le istantanee `stage_C1/` e `stage_C2/`), passano `svelte-check` con 0 errori (`…_svcheck_C1.log`, `…_svcheck_C2.log`). Poi gli 11 file sono tornati allo stato C3, coi blob verificati (`…_stagecheck.log`).
  >
  > **Fuori pista**:
  > - la prima corsa di `dev.py front check` ha dato 2 errori TS2783 nel codice di test del giro B, `chartCoreHelpers.test.ts:611` e `:641` (`…_front_check.log`). Le due righe scrivevano `{...x, formatter: compact.formatter, ...compactPolicyAxisLabel}`, ma l'helper `responsiveAxisLabel` (`:58`) dà un `axisLabel` non nullo: il suo `formatter` è obbligatorio e sovrascrive sempre quello esplicito. Vitest non controlla i tipi, quindi tutte le corse erano verdi;
  > - `test-author` ha corretto le due righe in `...(compact.axisLabel ?? {})`, come fanno i grafici, e ha verificato vitest (173 su 173), prettier e `svelte-check` (`…_ts2783_vitest.log`, `…_ts2783_svcheck.log`). Il diff sono esattamente quelle due righe;
  > - il blob del test passa da `f4a8ab8a` (passo 5) a `b4944a3d`, e l'istantanea `stage_C3/` è aggiornata. Il codice di prodotto non cambia: i grafici spargono `axisLabel ?? {}`, un'unione in cui `formatter` non è obbligatorio, e TypeScript la accetta.
- [x] **7. Il journal**: Q3 nel backlog, questo piano (2026-10-12).
  > **Note implementazione**:
  > - `BACKLOG_POST_1.2.md`, sezione I: la voce **47-1**, bassa e preesistente, in fondo all'elenco. Nell'intro della sezione la nomina la riga sui numeri di riga. Nel backlog «Q3» diventa «47-1», come le voci 32-1…32-5 della sezione Q, così non si confonde con quella sezione.
  > - Prima di scriverla, I ha verificato il meccanismo nel codice e con una prova SSR (`files/xaxis_evidence/libreFolio_i_xaxis_q3zoom.{cjs,log}` nella sessione):
  >   - in compatto l'`interval` degli assi category si calcola su tutti i punti (`responsiveXAxis.ts:149`, da `2d22130bd` del 17/09);
  >   - i gestori del `dataZoom` dei tre grafici category (`CandlestickChart.svelte:249`, `LineChart.svelte:358`, `PriceChartFull.svelte:579`) non lo ricalcolano sulla finestra visibile;
  >   - un anno giornaliero a 800 px, con spazio per 12 etichette, ne mostra 12 senza zoom, 7 con metà periodo, 4 con un quinto, e su una finestra di 33 punti solo i due bordi;
  >   - gli assi time non ne soffrono, perché ECharts rifà i tick sulla finestra.
  > - La coda di I dopo questo lotto, come da coordinatore: la rifinitura UI (con M-20, i pulsanti di copia su `http://`), poi M-18. Il CHANGELOG localizzato è passato a T.
- [x] **8. Checkpoint** (2026-10-12).
  > **Note implementazione**:
  > - Base `bdc078efc`, niente in stage, porta 6157 libera. Al checkpoint il target è `bd14ec61d` (treno 58), non più `d33fca26f`:
  >   - dei 166 file che cambiano fra la base e il target, l'unico in comune col lotto è `BACKLOG_POST_1.2.md`, toccato fuori dalla sezione I. La fusione a tre vie (`git merge-file -p`, sola lettura) non ha conflitti, e la 47-1 resta in fondo alla sezione I;
  >   - i file che importano `responsiveXAxis` sono gli stessi nove in base e nel target. I due ritocchi del target a `dashboard/+page.svelte` aggiungono `refreshVersion += 1` dopo la sincronizzazione dei cambi e dei prezzi: va a `LotsAnalysisPanel` e a `RiskLevelsPanel`, non a GrowthChart. I grafici dei lotti rifanno la policy a ogni disegno, quindi il refresh li ridisegna col formatter di C3.
  > - La partizione, coi blob per stadio ricalcolati con `git hash-object` sulle istantanee:
  >   - **C1**: `responsiveXAxis.ts` `a747bb14`, `chartCoreHelpers.test.ts` `e5d6bf10`;
  >   - **C2**: `GrowthChart.svelte` `3a7ac33a`, `GrowthChart.test.ts` `fa2be2b4`, `_frontend_asset.py` `b4f94248`;
  >   - **C3**: i 10 file di `stage_C3/`, uguali alla worktree (passo 5, col test a `b4944a3d` dal passo 6);
  >   - **C4**: questo piano, nuovo, e `BACKLOG_POST_1.2.md`, solo la sezione I.
  > - `git diff --check` pulito, anche sul piano nuovo. Le righe aggiunte non contengono percorsi assoluti, indirizzi, IBAN, segreti, numeri lunghi né nomi di file privati (`…_privacy.log`).
  > - Restano fuori: `.svelte-kit`, `build`, `test-results`, `playwright-report`, i client generati, i `__pycache__`, la corsia `/tmp/librefolio-r2-i-charts` e le istantanee della sessione.
  > - I messaggi sono in `/tmp/libreFolio_commit_i_xaxis_msg_C{1..4}.txt`, coi percorsi e i blob accanto. I log di `/tmp` citati nei passi 1–8 sono archiviati nei file della sessione, in `xaxis_commit_bundle/evidence/`; le simulazioni restano in `xaxis_evidence/`.
