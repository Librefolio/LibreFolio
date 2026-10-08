# Performance charts — Proventi: dividendo oro ed etichette dell'asse X (Candele e Proventi)

**Stato:** COMPLETATO il 2026-10-08. Lotto approvato dal developer il 2026-10-07 (via coordinator, 17:37), in corso dal
2026-10-07 18:10. Commit del developer il 2026-10-08 alle 12:18, su `9ea2d519b`: `bc08101d6` (codice, test e
cataloghi), `835c65d7d` (docs) e `e379cff59` (giornale). Poi il merge della punta del treno 12, `ffa72cc2b`, nel ramo:
`56483392c`, alle 12:54. L'integrazione in `dev_release2` è nel treno 13.
**Workstream:** I (grafici performance) · ramo `e-alfy-performance-charts-plan` · coordinatore
`c8328a01-f208-4ade-a352-0486d1f14de2`.
**Baseline:** HEAD = `dev_release2` = `9ea2d519b`, la punta del treno 9, dopo il fast-forward segnalato dal
coordinator. Albero pulito, `6157` e `6167` libere, rimisurato alle 18:08.
**Lane:** suite `6157` + `/tmp/librefolio-r2-i`, solo `dev.py test …`; review `6167` (prima `front build`; dati di
test, nessuna copia di prod senza chiedere al developer). Un comando alla volta.
Preambolo: `PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py …`.

Precedenti e collegati:

- Piano precedente: [plan-phase00PerformanceChartsRound4-PostMergeReview.prompt.md](plan-phase00PerformanceChartsRound4-PostMergeReview.prompt.md),
  che punta qui. Questo piano **sostituisce le regole sul testo di D4 e D4-bis** (§7 e «S7 — passo 0» di quel piano).
  I separatori di D4 restano com'erano.
- Bugfix precedente: [plan-phase00PerformanceChartsBugfix-EventsOnCacheHit.prompt.md](plan-phase00PerformanceChartsBugfix-EventsOnCacheHit.prompt.md).
- Dopo questo lotto M fotografa `growth-pnl-*` per la gallery.
- CHANGELOG: la riga la scrive il coordinator. La frase su cosa vede l'utente è in §11.
- Rosso noto sulla base, non mio: `core-unit` ha 1 file rosso, `optionFilter.test.ts` (R13). Lo corregge L nel
  treno 10. Non lo indago e non lo tocco; al checkpoint lo nomino e ne riporto il conteggio.

## Decisioni del developer (testuali)

1. Colori: «Dividendo oro, anche nel pannello lotti».
2. Etichette: «si, per proventi e candele, riguardo la rotazione, ruotata 1, ruotano tutte, per uniformità».

La specifica del coordinator (17:37), riassunta:

- i costi restano arancio, sotto lo zero; le tonalità esatte le scelgo io;
- uno schema solo per Candele e Proventi, con un testo su ogni bucket:
  - `1D`, `3D`, `1W`, `2W`: il giorno d'inizio, con il mese quando cambia («6 ott · 20 · 3 nov · 17»); l'anno a due
    cifre sul primo bucket e quando cambia (**corretto** dopo il brief, vedi sotto);
  - `1M`: il mese, con l'anno solo a gennaio e sul primo bucket («ott 25 · nov · dic · gen 26»);
  - `3M`: il trimestre, «T4 25 · T1 26», in inglese «Q4 25» (**corretto** in «Q4 '25», vedi sotto), con una chiave
    i18n nuova (`dev.py i18n add`);
  - `6M`: l'intervallo di mesi, «lug–dic 25 · gen–giu 26», non «S1»;
  - `1Y`: l'anno;
- rotazione: se un'etichetta non ci sta in orizzontale, ruotano tutte a 45°;
- diradamento: solo dove nemmeno ruotate ci stanno, cioè nelle Candele molto fitte;
- va aggiornato il contratto in testa a `growthLadderAxis.ts`; i test li aggiorna il test-author, rossi prima.

Su richiesta del developer la sessione si chiama «I - colori e asse dei proventi».

**Risposta del coordinator al brief** (registrata alle 19:01). Approvati l'oro `#b08d00` / `#facc15` e i default
1–5 del brief. Due correzioni:

1. **Scale a giorni.** Il coordinator ritira la sua aggiunta dell'anno sul primo bucket. Su `1D`, `3D`, `1W`, `2W`:
   - il giorno, con il mese quando cambia; il primo bucket ha sempre il mese;
   - l'anno a due cifre **solo** sul primo bucket del nuovo anno, quando l'anno cambia dentro la finestra:
     «29 dic · 5 gen 26»;
   - `1M`, `3M`, `6M` tengono «anno a gennaio e sul primo bucket»; `1Y` è sempre l'anno.
2. **L'inglese.** Decisione del developer, testuale: «Inglese «Oct '25», con l'apostrofo».
   - In inglese l'anno porta l'apostrofo: «Oct '25 · Nov · Jan '26», «Q4 '25», «Jul–Dec '25», «Jan 5 '26».
   - In italiano, francese e spagnolo no: «ott 25», «T4 25».
   - Lo schema dell'anno vive quindi in una chiave i18n, che scelgo io e aggiungo con `dev.py i18n add`. Sostituisce
     il punto del brief sull'«Oct 25» (qui §3.8 e §3.9).

Il resto resta com'era: test rossi dal test-author, poi il codice, poi le docs dal docs-writer.

## Stato di esecuzione

| Step | Contenuto | Stato |
|---|---|---|
| P0 | Baseline e analisi, in sola lettura | ✅ 2026-10-07 18:08 |
| P1 | Questo piano, il «Seguito» nel piano del round 4, il brief al coordinator | ✅ 2026-10-07 18:25 |
| P2 | Chiave `dashboard.pnlAxisQuarter` con `dev.py i18n add` | ✅ 2026-10-07 18:27 |
| P2b | Correzioni del coordinator nel piano; chiave `dashboard.pnlAxisWithYear` | ✅ 2026-10-07 19:13 |
| P3 | Test (test-author), **rossi su HEAD** | ✅ 2026-10-07 20:59 |
| P4 | Pianificatore `growthLadderAxis.ts` e il suo contratto | ✅ 2026-10-07 20:59 |
| P5 | `GrowthChart.svelte` (rung e trimestre nel piano, colore) e `lotComparisonChartHelpers.ts` | ✅ 2026-10-07 21:00 |
| P6 | Verde dei test nuovi, poi i gate | ✅ 2026-10-07 21:12 |
| P7 | Schermate chiaro e scuro su `6167`, poi porta libera | ✅ 2026-10-07 21:55 (difetto `containLabel` confermato: proposta al coordinator, in attesa) |
| P7b | M‴ e k su una riga di 14,3 px: test rossi, correzione e contratto, gate, schermate a 1920 e 2560 | ✅ 2026-10-08 |
| P8 | Docs (docs-writer): un punto in `charts.en.md` `#pnl-width` | ✅ 2026-10-08 11:58 |
| P9 | Pulizia, CHECKPOINT READY, FROZEN | ✅ 2026-10-08 12:03 |
| P10 | Merge del treno 12 (`ffa72cc2b`) nel ramo: i 4 cataloghi in unione, solo loro in stage, gate sulla revisione unita, MERGE RESOLVED | ✅ 2026-10-08 12:37 (merge `56483392c`, 12:54) |
| P11 | Le note del merge in questo piano, in un commit a parte; pulizia di `/tmp`; checkpoint piccolo, FROZEN | ✅ 2026-10-08 12:55 |

## 1. Colori

Il difetto: nei Proventi dividendo (`#0891b2`) e deposito (`#0d9488`) sono due verdi-azzurri, e c'è anche lo
smeraldo del reinvestito. La distanza percettiva dividendo–deposito è ΔE2000 17,3 in chiaro e 16,2 in scuro.

| Tema | Oro scelto | Contrasto sul fondo | ΔE vs costi | ΔE vs deposito | ΔE vs smeraldo |
|---|---|---|---|---|---|
| chiaro | `#b08d00` | 3,16 su bianco | 29,5 vs `#ea580c` | 36,9 | 35,1 |
| scuro | `#facc15` | 9,55 su `#1e293b` | 24,0 vs `#fb923c` | 40,3 | 37,2 |

- Il giallo-600 di Tailwind (`#ca8a04`) dava 2,94:1 su bianco. Sarebbe stato l'unico colore del grafico sotto 3:1,
  la soglia WCAG 1.4.11 per gli oggetti grafici. Tutti gli altri colori sono sopra. `#b08d00` ha la stessa tinta
  dell'oro scuro (48°) ed è più lontano dall'arancio (29,5 contro 21,7).
- Deuteranopia: oro e arancio si somigliano, in chiaro (ΔE 0,8 simulato). Li separano la posizione (sopra e sotto
  lo zero), la legenda e il tooltip.
- In scuro l'oro è vicino all'ambra dei broker (`#fbbf24`, ΔE 5,1), ma l'ambra vive in un altro sottomodo.
- Dove:
  - `GrowthChart.svelte`: `COLORS.dividend`. La tavolozza ciclica dei broker (cyan, ~:346) non si tocca;
  - `lotComparisonChartHelpers.ts`: `incomeEventColor`, ramo DIVIDEND, più il commento «Teal for dividends…».
- Non esiste un modulo di tavolozza condiviso: i due punti si citano a vicenda in un commento.
- Lo script delle metriche è in `/tmp/libreFolio_i_gold/` e si cancella al P9.

## 2. Il contratto nuovo delle etichette

**Testo.** È l'inizio del periodo di calendario del bucket sul rung: `calendarPeriodOf(closingDates[i], rung).start`.
Coincide con `period.start` del bucket e con l'intestazione del tooltip. Il primo bucket parziale porta il suo
inizio di calendario: con i dati da giovedì 1 gennaio, la settimana `1W` si chiama «29 dic».

| Rung | Forma breve | Forma con il mese | Forma con l'anno |
|---|---|---|---|
| `1D` `3D` `1W` `2W` | «20» | «3 nov»: primo bucket, cambio di mese | «5 gen 26», en «Jan 5 '26»: solo cambio d'anno |
| `1M` | «nov» | — | «ott 25», en «Oct '25»: primo bucket, cambio d'anno |
| `3M` | «T2», en «Q2» | — | «T4 25», en «Q4 '25»: primo bucket, cambio d'anno |
| `6M` | «lug–dic» | — | «lug–dic 25», en «Jul–Dec '25»: primo bucket, cambio d'anno |
| `1Y` | — | — | sempre l'anno intero, «2026» |

- «Primo» è il primo bucket etichettato **visibile**; tutti gli altri si confrontano con il bucket etichettato
  precedente.
- Scale a giorni: il primo porta la forma con il mese, **mai l'anno**. Un bucket di un anno diverso dal precedente
  porta la forma con l'anno; altrimenti, se cambia il mese, quella con il mese; altrimenti la breve. L'anno compare
  quindi solo quando cambia dentro la finestra: «29 dic · 5 gen 26».
- Scale a mesi (`1M`, `3M`, `6M`): il primo e ogni cambio d'anno portano la forma con l'anno.
- Le etichette si producono per **tutti** i bucket, perché non cambino a ogni piccolo pan. Solo il primo bucket
  visibile cambia testo quando si sposta la finestra, ed è la regola stessa a volerlo.
- Due bucket etichettati consecutivi non hanno mai lo stesso testo, per costruzione.
- Formati:
  - giorno, mese e anno sono `Intl.DateTimeFormat` in UTC, con la cache che c'è già;
  - `6M` è composto come `mese–mese` con il trattino lungo (non `formatRange`, che in inglese mette gli spazi);
  - il trimestre viene dalla chiave `dashboard.pnlAxisQuarter` («Q{quarter}», «T{quarter}»);
  - la forma con l'anno viene dalla chiave `dashboard.pnlAxisWithYear`: `{label} ''{year}` in inglese,
    `{label} {year}` in italiano, francese e spagnolo. `year` è Intl `{year: '2-digit'}`, passato come stringa,
    così il 2005 resta «05».
- **La trappola dell'apostrofo.** In ICU un apostrofo singolo davanti a `{` apre un testo letterale:
  `{label} '{year}` renderebbe «Oct {year}». Nel catalogo inglese l'apostrofo è quindi doppio, e rende «Oct '25»
  (verificato con intl-messageformat 10.7.18). È l'apostrofo ASCII, come nel testo della decisione. Una guardia
  sui quattro cataloghi lo sorveglia (§5).

Esempi attesi, finestra intera. Li ho ricalcolati alle 19:01 con un modello del contratto
(`/tmp/libreFolio_i_gold/model.mjs`):

```text
2W   it  6 ott · 20 · 3 nov · 17 · 1 dic · 15 · 29 · 12 gen 26
     en  Oct 6 · 20 · Nov 3 · 17 · Dec 1 · 15 · 29 · Jan 12 '26
1M   it  ott 25 · nov · dic · gen 26 · feb
     en  Oct '25 · Nov · Dec · Jan '26 · Feb
3M   it  T4 24 · T1 25 · T2 · T3 · T4 · T1 26 · T2 · T3
     en  Q4 '24 · Q1 '25 · Q2 · Q3 · Q4 · Q1 '26 · Q2 · Q3
6M   it  lug–dic 25 · gen–giu 26 · lug–dic · gen–giu 27
     en  Jul–Dec '25 · Jan–Jun '26 · Jul–Dec · Jan–Jun '27
1Y       2024 · 2025 · 2026
1W   en  dati da giovedì 2026-01-01 (B6):  Dec 29 · Jan 5 '26 · 12 · 19 · 26 · Feb 2 · 9
1W   en  finestra da lunedì 5 gennaio:     Jan 5 · 12 · 19 · 26 · Feb 2   (l'anno non cambia: niente anno)
```

In francese le abbreviazioni di Intl hanno il punto: «oct. 25», «5 janv. 26», «juil.–déc. 25».

**Rotazione.**

- È orizzontale, con un testo su ogni bucket, quando tutte le etichette visibili ci stanno: è la prova di oggi,
  con distanza minima 8 px e gli spostamenti ai bordi di D4.
- Altrimenti ruotano tutte a 45°.
- La decisione si prende sulla finestra visibile, come in D4.

**Diradamento**, solo da ruotate:

- il passo k è il più piccolo intero con k · slot · sin 45° ≥ altezza della riga (14 px), cioè con slot ≥ 19,8 px
  per k = 1;
- sono etichettati i bucket con `(n − 1 − i) % k === 0`, contati dall'ultimo, quindi stabili sotto pan;
- i Proventi non si diradano mai, perché il loro slot minimo è 20,57 px (4,5 / 0,21875). È «cioè nelle Candele molto
  fitte» della decisione.

**Bordo sinistro, da ruotate.** Un'etichetta ruotata scende a sinistra della sua tacca di
w · cos 45° + 7 · sin 45° px (w è la stima prudente: 0,6 · 14 px per carattere).

- Il `containLabel` di ECharts 6 qui è l'algoritmo legacy (`echarts/index.js:261`, `legacyContainLabel.js`), e per
  l'asse X **toglie solo altezza**: non sposta il grafico a destra.
- Allora un bucket visibile la cui etichetta stimata uscirebbe dalla tela a sinistra, oltre 2 px di margine, resta
  senza testo, e la forma del primo passa al successivo: con il mese sulle scale a giorni, con l'anno sulle altre.
  La prova usa la larghezza di quella forma. È il «nemmeno ruotate ci stanno» applicato al bordo.
- Lo stesso a destra, dove sporge solo di 7 · sin 45° px: in pratica non succede mai.
- Da ruotate non ci sono spostamenti ai bordi: il trucco del padding sposta solo le etichette centrate.

**Misura dell'altezza.**

- Il `containLabel` legacy misura le etichette chiamando il formatter su un campione di categorie (una ogni
  ⌈n/40⌉), **senza guardare `interval`**.
- Da ruotata l'altezza di un'etichetta cresce con la sua larghezza. Con il diradamento, un campione fatto solo di
  bucket vuoti riserverebbe circa 10 px a etichette alte circa 60, che uscirebbero dal fondo della tela.
- Il formatter risponde quindi, per i bucket senza etichetta, con il testo più largo del piano. ECharts non li
  disegna (lo filtra `interval`), e il grafico riserva l'altezza giusta.

**Separatori:** invariati (D4, `CANDLE_MIN_SLOT_PX`, regola dell'ancora).

**Tipo del piano:**

- `mode` e `withYear` lasciano il posto a `rotate: 0 | 45` e `step` (> 1 solo da ruotate), più `widestText`;
- la `key` include `rotate`;
- `ladderAxisOption` emette sempre `axisLabel.rotate`, così un aggiornamento parziale riporta anche a 0;
- input nuovi del pianificatore, tutti obbligatori:
  - `rung: LadderRung`;
  - `quarterLabel: (q: 1 | 2 | 3 | 4) => string`;
  - `labelWithYear: (label: string, year: string) => string`;
- `GrowthChart` li riempie con le due chiavi i18n; i test del pianificatore usano funzioni finte, una all'inglese
  (con l'apostrofo) e una all'italiana.

## 3. Interpretazioni e default (non bloccanti, nel brief)

1. Il testo è l'inizio di calendario del periodo, anche per il primo bucket parziale (come il tooltip).
2. «Primo bucket» = il primo bucket etichettato visibile.
3. La regola dell'anno vale anche per `3M` e `6M`; `1Y` mostra sempre l'anno.
4. La rotazione si decide sulla finestra visibile. Un pan può farla scattare, ma solo in una banda stretta di zoom.
   L'alternativa è il caso peggiore sull'intera serie: stabile, ma ruota anche quando la finestra ha spazio.
5. Il diradamento si conta dall'ultimo bucket. Non l'allineo al calendario, che è un'alternativa possibile.
6. La distanza tra etichette ruotate è una riga piena, senza margine: con qualunque margine > 0,55 px anche i
   Proventi al loro slot minimo si diraderebbero.
7. Il bordo sinistro da ruotate: un'etichetta che uscirebbe dalla tela non si disegna (§2).
8. ~~In inglese «Oct 25» si può leggere come 25 ottobre. Tengo il formato ICU; se serve, l'alternativa è
   «Oct '25».~~ **Superato:** il developer ha scelto «Oct '25», con l'apostrofo.
9. ~~La chiave del trimestre porta solo «Q{quarter}» / «T{quarter}». L'anno lo aggiunge il codice, dopo, con uno
   spazio.~~ **Superato:** l'anno lo compone la chiave `dashboard.pnlAxisWithYear`, su tutte le scale tranne `1Y`;
   il codice non assume più l'ordine delle parole.

Esito: il coordinator ha approvato l'oro e i default 1–5 del brief, con le due correzioni riportate in testa (l'anno
sulle scale a giorni, l'apostrofo inglese).

## 4. Superfici

| File | Cosa |
|---|---|
| `frontend/src/lib/components/dashboard/growthLadderAxis.ts` | Contratto in testa, testi, rotazione, diradamento, bordo, `widestText` |
| `frontend/src/lib/components/dashboard/GrowthChart.svelte` | `rung?` sull'entry (`getLadderData`), `rung`, `quarterLabel` e `labelWithYear` in `planLadderFor`, `COLORS.dividend` |
| `frontend/src/lib/components/brokers/lots/lotComparisonChartHelpers.ts` | `incomeEventColor` DIVIDEND, commento |
| `frontend/src/lib/i18n/{en,it,fr,es}.json` | `dashboard.pnlAxisQuarter` e `dashboard.pnlAxisWithYear`, **solo** con `dev.py i18n add` |
| test | §5, del test-author |
| `mkdocs_src/docs/user/dashboard/charts.en.md` | Un punto in `#pnl-width`, del docs-writer (§8) |

La riga `xAxis = {data: entry.dates, ...ladderAxisOption(plan)};` di `updateChartData` resta identica: la fissa
`chartCoreHelpers.test.ts:1411`.

## 5. Test (test-author, rossi prima)

- `growthLadderAxis.test.ts`: riscritto sul contratto di §2, con le funzioni finte all'inglese e all'italiana:
  - i testi per rung;
  - il primo parziale;
  - il primo visibile: con il mese sulle scale a giorni (mai l'anno), con l'anno sulle scale a mesi;
  - l'anno sulle scale a giorni solo quando cambia dentro la finestra;
  - tutto o niente sulla rotazione;
  - il passo k e la soglia 19,8;
  - i Proventi mai diradati;
  - il bordo sinistro;
  - `widestText` nel formatter;
  - `rotate` nell'opzione e nella `key`;
  - nessun testo uguale tra consecutivi;
  - i separatori invariati.
- `GrowthChart.test.ts`. I testi attesi si prendono dal catalogo, mai scritti a mano; le forme di Intl («Dec 29»)
  sono ammesse, come già in B6:
  - B6: le etichette `1W` di FIXTURE_40 diventano `Dec 29 · Jan 5 '26 · 12 · 19 · 26 · Feb 2 · 9`, **in
    orizzontale**. Con le forme corte ci stanno (distanza minima 12,3 px); la forma piena di prima le faceva ruotare;
  - B9 (`1M`, finestra aprile–settembre 2026): `Apr '26 · May · Jun · Jul · Aug · Sep`;
  - nuovo, il cablaggio di `3M` su FIXTURE_730: `Q4 '24 · Q1 '25 · Q2 · Q3 · Q4 · Q1 '26 · Q2 · Q3`;
  - nuovo, la guardia dei cataloghi: nelle quattro lingue le due chiavi, formattate con valori sentinella,
    contengono le sentinelle e nessuna graffa. Coglie la trappola dell'apostrofo.
- `lotComparisonChartHelpers.test.ts:101-102`: `#b08d00` e `#facc15` (fatto al primo giro del test-author).
- `e2e/portfolio/dashboard.spec.ts`:
  - A: due bucket etichettati consecutivi, per indice, non hanno lo stesso testo; oggi il controllo è globale;
  - G: sovrapposizione sui rettangoli orientati (assi separatori), che a 0° si riduce al controllo di oggi;
  - R (nuovo): una rotazione sola, 0° o 45°;
  - E: dentro la tela anche in verticale;
  - H (nuovo): in orizzontale ogni bucket visibile ha un testo;
  - ~~F (il primo testo finisce con due cifre) è sbagliato sulle scale a giorni: va tolto, o reso dipendente dal
    rung.~~ **Corretto alle 19:13:** nello spec di oggi non c'è nessun controllo F (verificato con grep): non c'è
    niente da togliere, e non va aggiunto;
  - a 1440 px ruotano S7-E1 `1w` (k = 2), S7-E1 `1m` ed E2 (Proventi `1m`);
  - H dà i rossi su HEAD: l'asse di oggi non ruota mai e dirada in orizzontale S7-E1 `1w`, S7-E1 `1m`, E2 e il caso
    del telefono;
  - nuovo caso orizzontale, i Proventi `3m` a 1440 px sulla finestra di un anno (4–5 trimestri, offerti a 1440 px):
    rotazione 0 e H. Senza di lui H non girerebbe mai, perché tutti gli altri casi ruotano. È una guardia ed è verde
    anche su HEAD;
  - la banda di S7-E4 resta com'è.

## 6. Gate e comandi

Uno alla volta, nella corsia `6157`:

- `front check`;
- `core-unit` (atteso 1 rosso noto, R13);
- `component-unit`;
- `growth-chart-memo`;
- `asset-unit` (contiene `growthLadderAxis.test.ts`);
- `front-portfolio dashboard`;
- `front-broker detail`;
- prettier sui file toccati;
- per le docs, `mkdocs build` e check-links (rosso noto D28).

## 7. Schermate

Su `6167` con i dati di test, in chiaro e in scuro:

- i Proventi a `1M`;
- le Candele fitte (rotazione e diradamento);
- il pannello lotti con i dividendi.

Vanno al coordinator al checkpoint. Poi stop del server e `lsof -nP -iTCP:6167 -sTCP:LISTEN` vuoto.

## 8. Docs

Un punto in `charts.en.md` `#pnl-width`, via docs-writer, solo in inglese. Deve dire:

- le etichette mostrano l'inizio di ogni periodo;
- mese e anno compaiono solo quando cambiano;
- trimestri, semestri e anni hanno la loro forma;
- quando un'etichetta non ci sta, ruotano tutte a 45°;
- solo le candele molto fitte saltano qualche etichetta.

Le pagine non nominano i colori. Il debito di traduzione delle pagine charts è già registrato.

## 9. Definition of done

- I due colori sono applicati, con le schermate in chiaro e in scuro.
- Le etichette seguono §2 in Candele e Proventi; l'asse a tempo degli altri modi non cambia.
- I test di §5 erano rossi su HEAD e ora sono verdi; i gate di §6 sono verdi, salvo i rossi noti nominati.
- Il contratto in testa a `growthLadderAxis.ts` è aggiornato; la chiave è aggiunta con `dev.py i18n add`.
- Questo piano è aggiornato a ogni step; le porte sono libere; i file temporanei sono cancellati.

## 10. Rischi

- **Altezza ruotata.** Un'etichetta piena ruotata alta circa 60 px toglie altezza al grafico; sui telefoni conta.
- **Banda di S7-E4.** Il grafico non si sposta a destra (§2), quindi la banda [232.5, 328) non dovrebbe muoversi:
  lo dice il run.
- **Rimbalzo del passo k.** Un ridisegno legge la geometria nuova solo a zoom, resize o aggiornamento, mai dopo
  `refreshLadderAxis`. Un rimbalzo di k tra due eventi è possibile in teoria, ma piccolo.
- **I Proventi `1M` su un anno ruotano anche su desktop.** Con la stima prudente (0,6 · 14 px per carattere), a
  1440 px «Oct '25» e «Jan '26» lasciano 2,1 px dalle vicine, e in italiano «ott 25» e «gen 26» 6,3 px: sotto gli 8,
  quindi ruotano. È la vista più comune: la mostro nelle schermate e la segnalo al checkpoint.
- **L'apostrofo ICU** (§2). Un catalogo con l'apostrofo singolo mostrerebbe «{year}» al posto dell'anno; lo coglie
  la guardia dei cataloghi (§5).
- **Il campione del `containLabel` sugli schermi larghi.** L'algoritmo legacy misura il formatter solo su una
  categoria ogni `ceil(visibili / 40)`, e non chiede `interval`. Se tutte le categorie del campione portano
  un'etichetta corta, la più lunga ruotata («5 gen 26») resta fuori. La banda sotto l'asse risulta allora più
  bassa di 16–20 px, e l'etichetta può toccare la legenda nei 30 px in fondo.
  - Succede solo con k = 1 e più di 40 bucket visibili, cioè con un grafico di almeno 812 px circa: solo su
    schermi larghi. A 1440 il grafico è di circa 573 px, e l'E2E non lo vede.
  - Lo verifico in P7 con una schermata larga (circa 2560 px). Se si vede, propongo una correzione, per esempio
    un token rich a larghezza fissa in modo ruotato; il contratto non lo cambio da solo.
  - **Esito di P7**: si vede, già a 1920 px. La proposta è M‴, non il token rich. Vedi il Registro (21:22–21:55)
    e il «Fuori pista» di P7.
- **La fascia del riquadro di 14,28 px.** ECharts confronta le etichette vicine sui loro riquadri, alti 14,28 px,
  mentre il k del contratto usa la dimensione del font, 14 px. Con k · slot tra 19,80 e 20,19 px, cioè in una fascia
  del 2% circa, ECharts può nascondere la prima o l'ultima etichetta ruotata. Nell'inchiostro non si toccano. I
  Proventi non ci cadono mai, perché il loro slot minimo è 20,57 px; le Candele sì, a certe larghezze. La correzione
  sarebbe un'altezza di riga di circa 14,3 px nella formula di k: la propongo al checkpoint, senza applicarla.

## 11. CHANGELOG (frase per il coordinator)

> In the P&L chart, dividends are now gold, also in the lots panel. The axis under Candles and Income names the
> start of every period (day, month, quarter, half-year or year), shows month and year only when they change, and
> turns all labels 45° when one does not fit.

## Registro

- 18:08 — P0 chiuso. Baseline `9ea2d519b` = `dev_release2`, pulito, porte libere.
- 18:10 — Il piano è scritto.
- 18:25 — P1 chiuso. «Seguito» aggiunto nell'intestazione del piano del round 4. Il brief è al coordinator, non
  bloccante: i default di §3, l'oro e il suo contrasto, il punto per le docs.
- 18:27 — P2 chiuso.
  - Comando: `PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py i18n add "dashboard.pnlAxisQuarter"
    --en "Q{quarter}" --it "T{quarter}" --fr "T{quarter}" --es "T{quarter}"`.
  - Il diff è di 4 righe, una per catalogo. La chiave è in coda al namespace `dashboard`, dopo `allocationGeneric`.
    Un altro ramo che aggiunga una chiave in coda allo stesso namespace darebbe un conflitto testuale banale: lo
    segnalo al checkpoint.
- 18:36 — P3, primo giro del test-author (sincrono), all'ora di modifica del file: è tornato **senza risposta**.
  Ha cambiato solo `lotComparisonChartHelpers.test.ts:99-110`, il pin oro con il commento sul perché, ed è corretto.
  Non ha toccato `growthLadderAxis.test.ts`, `GrowthChart.test.ts` né `dashboard.spec.ts`, e non ha lasciato log.
- 19:01 — Registrata la risposta del coordinator al brief (in testa, con la decisione testuale del developer).
  Ricalcolati gli esempi di §2 e §5 con un modello del contratto, `/tmp/libreFolio_i_gold/model.mjs`: B6 ora sta in
  orizzontale; i Proventi `1M` su un anno a 1440 px ruotano ancora (§10).
- 19:13 — P2b chiuso.
  - Comando: `PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py i18n add "dashboard.pnlAxisWithYear"
    --en "{label} ''{year}" --it "{label} {year}" --fr "{label} {year}" --es "{label} {year}"`.
  - Le due chiavi insieme fanno 12 righe in più e 4 in meno, 3 e 1 per catalogo, in coda al namespace `dashboard`.
  - Prova di resa con il formatter dei messaggi: en «LBL '25», it, fr ed es «LBL 25»; il trimestre «Q4» e «T4».
- 19:13 — P3, secondo giro: tre test-author nuovi, in parallelo, uno per file (`growthLadderAxis.test.ts`,
  `GrowthChart.test.ts`, `dashboard.spec.ts`). L'E2E lo lancio io nella corsia.

> **⚠️ Fuori pista** (P3): il primo giro del test-author è tornato senza risposta, con un solo file cambiato. Avevo
> pensato di rimandargli il contratto corretto in due turni. Ho cambiato strada: alle 19:13 ho aperto tre agenti
> nuovi, ciascuno con un file e un compito stretto. Il primo resta fermo.

- 19:31 — P4, bozza fuori dal repo (`/tmp/libreFolio_i_gold/growthLadderAxis.new.ts`): non tocco
  `growthLadderAxis.ts` prima che il test-author registri il rosso su HEAD. La bozza, compilata con esbuild in una
  cartella di prova, rende gli esempi di §2 e §5: B6 in en e in it, B9, 3M in en e in it, 6M, 1Y. I Proventi `1M`
  su 13 mesi a 573 px ruotano con k = 1; i giornalieri su un anno ruotano con k = 13.
- 19:33 — P5, parte dei lotti, anticipata: il suo rosso era già registrato e nessun test-author tocca quel file.
  `incomeEventColor`, ramo DIVIDEND, passa a `#b08d00`/`#facc15`; il commento cita `COLORS.dividend` di
  `GrowthChart.svelte`. `lotComparisonChartHelpers.test.ts`: 80 su 80, prima 79 su 80
  (`/tmp/libreFolio_i_lots_green.log`). Altrove nei componenti nessun altro colore del dividendo.
- 19:45 — P3, `GrowthChart.test.ts` (secondo test-author): B6 e B9 aggiornati; nuovi B6b (3M, Candele e Proventi),
  B6c (Candele `1M` su un telefono, ruotate con k = 2) e S7a (la guardia dei cataloghi, verde per costruzione).
  Rosso verificato da me con `vitest run`: **6 falliti, 121 passati su 127**, esattamente B6, B6b ×2, B6c, B9 ×2
  (`/tmp/libreFolio_i_ta2_red_verify.log`; quello del test-author è `/tmp/libreFolio_i_ta2_red.log`).
- 19:46 — P3, `dashboard.spec.ts` (terzo test-author, senza Playwright): A sulle etichette consecutive, E sui
  quattro angoli, G con il test degli assi separatori sui rettangoli orientati, più R (una rotazione sola, 0° o
  45°) e H (in orizzontale nessun bucket senza etichetta). Nuovo S7-E5: Proventi `3m` a 1440, orizzontale.
  `tsc -p tsconfig.e2e.json`: solo i 2 errori noti (`/tmp/libreFolio_i_ta3_tsc.log`).
- 19:50 — P3, rosso E2E su HEAD, nella corsia:
  - `front build --debug`: rc 0, svelte-check 0 errori e 0 avvisi (`/tmp/libreFolio_i_build_red.log`).
  - `PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py test --test-port 6157 --data-dir
    /tmp/librefolio-r2-i front-portfolio dashboard "S7-"`: **4 falliti, 3 passati** (54,1 s,
    `/tmp/libreFolio_i_e2e_red_s7.log`). Rossi E1-1m, E1-1w, E2 e phone, tutti e quattro **solo su H**; verdi E3,
    E4 ed E5, come previsto.
  - Il digest `[S7]` conferma le premesse del test-author: in piano gli angoli coincidono con il riquadro,
    l'altezza del grafico (il campo `H` del digest, non la lettera H) è 360, l'estensione è [0, 12].
  - A 1440 il riquadro misura 560 px nelle Candele e 569 nei Proventi; il commento di `INCOME_MIN_BAR_PX` dice
    573. Con questi valori il k previsto resta 1 a `1m`, e diventa 2 a `1w` (slot 10,57) e sul telefono (slot
    19,33).

> **⚠️ Fuori pista** (P3): il digest mostra che il riquadro di un'etichetta è alto **14,28 px**, mentre il k del
> contratto usa la dimensione del font, 14 px. Nella fascia k · slot tra 19,80 e 20,19 px i riquadri di due
> etichette ruotate vicine si sovrappongono di meno di 0,3 px, e lì ECharts (`fixMinMaxLabelShow`) può nascondere
> la prima o l'ultima etichetta. Con le misure di oggi nessuno scenario E2E cade nella fascia. Non cambio la
> formula da solo, perché è nel contratto che i test fissano: la registro in §10 con la correzione proposta.

- 19:54 — P5, cablaggio di `GrowthChart.svelte`, senza aspettare il primo test-author (non tocca il suo file):
  - `COLORS.dividend` passa all'oro `#b08d00`/`#facc15`, con il commento che rimanda a `incomeEventColor`; il
    teal del deposito, lo smeraldo del reinvestito e il ciano della tavolozza dei broker restano;
  - `AggregatedResolutionData` riceve `rung`, che `getLadderData` riempie con la larghezza;
  - `planLadderFor` passa `rung`, `quarterLabel` e `labelWithYear`, gli ultimi due da `dashboard.pnlAxisQuarter`
    e `dashboard.pnlAxisWithYear`. La riga `xAxis = {data: entry.dates, ...ladderAxisOption(plan)}` resta com'è,
    perché `chartCoreHelpers.test.ts` la fissa.
  - Il `front check` aspetta P4: il pianificatore vecchio non ha ancora i tre campi nuovi del suo ingresso.
- 20:24 — P3, il primo test-author (`growthLadderAxis.test.ts`) è tornato **senza risposta** dopo circa un'ora.
  Prima del rosso ha registrato la suite vecchia sul pianificatore vecchio: 62 su 62 (19:39,
  `/tmp/libreFolio_i_ta1_oldsuite.log`). Alle 20:02 il file è rimasto di 27 righe: l'intestazione e gli import di
  HEAD, senza il corpo di 943 righe. Non c'è né una bozza né un log del rosso.

> **⚠️ Fuori pista** (P3): il file dei test del pianificatore è rimasto troncato. La causa più probabile è una sola
> scrittura troppo grande, tagliata al limite dell'uscita dell'agente. Non lo ripristino da HEAD e non lo scrivo
> io: il contratto vuole i test dal test-author. Alle 20:26 gli ho chiesto, nello stesso contesto, di finire a
> pezzi di al più 120 righe, senza importare `LadderAxisMode`, e di registrare il rosso in
> `/tmp/libreFolio_i_ta1_red.log`. P4 resta fuori dal repo finché quel rosso non c'è.

- 20:59 — **P3 chiuso.** Il primo test-author ha finito `growthLadderAxis.test.ts`: 1390 righe, formattato con
  prettier, importa solo ciò che il contratto nuovo esporta (niente `LadderAxisMode`). Il suo rosso è
  `/tmp/libreFolio_i_ta1_red.log`; i nomi dei casi rossi sono in `/tmp/libreFolio_i_ta1_red_failed.txt`.
  - Rosso verificato da me con `cd frontend && node_modules/.bin/vitest run
    src/lib/components/dashboard/growthLadderAxis.test.ts`: **94 falliti, 24 passati su 118**, nessun
    TypeError, ReferenceError o SyntaxError (`/tmp/libreFolio_i_ta1_red_verify.log`). Ha toccato solo quel file.
  - I 24 verdi sul pianificatore vecchio sono voluti: la precondizione ICU (L0 ×4), le regole dei separatori che
    il contratto conserva (L11 ×12, L14b), le esportazioni conservate (L13.11), la chiave stabile (L9.5) e i casi
    che esercitano solo l'oracolo indipendente dello sweep (L14a, L14-self ×4).
  - Riepilogo dei rossi di P3: lotti 1 su 80, `GrowthChart.test.ts` 6 su 127, E2E 4 su 7 (solo H),
    `growthLadderAxis.test.ts` 94 su 118.
  - Le ambiguità che il test-author ha risolto da solo le verifico in P4 contro la bozza, una per una.
- 20:59 — **P4 chiuso.** Prima di copiare ho confrontato la bozza con le ambiguità dichiarate dal test-author:
  combaciano tutte. `LadderAxisPlan` ha esattamente i 7 campi, senza `readonly`; `axisLabel.rich` c'è sempre
  (`{}` senza spostamenti), con gli stessi nomi di stile (`lfShiftL6` → `[0, 12, 0, 0]`); spostamenti e scarti
  solo dal lato con lo spazio definito; `widestText` vale `''` senza etichette visibili ed è anche la risposta del
  formatter a un valore sconosciuto; estremi della finestra non finiti → 0 e n − 1; k usa il font dell'ingresso;
  l'anno a due cifre è formattato nel locale dell'ingresso.
  - Comando: copia di `/tmp/libreFolio_i_gold/growthLadderAxis.new.ts` su
    `frontend/src/lib/components/dashboard/growthLadderAxis.ts`, poi `node_modules/.bin/prettier --write` (file
    già formattato, 333 righe), poi `node_modules/.bin/vitest run
    src/lib/components/dashboard/growthLadderAxis.test.ts`.
  - **118 su 118 al primo giro**, 2,5 s; lo sweep da 4160 casi resta veloce grazie alla cache dei formatter
    (`/tmp/libreFolio_i_p4_ladder.log`). Nessun disaccordo fra contratto e test.
- 21:00 — **P5 chiuso** (i verdi): `vitest run` su `GrowthChart.test.ts`, `chartCoreHelpers.test.ts` e
  `lotComparisonChartHelpers.test.ts`: **127 su 127, 150 su 150, 80 su 80**
  (`/tmp/libreFolio_i_p5_green_verbose.log`). `chartCoreHelpers.test.ts` continua a fissare la riga
  `xAxis = {data: entry.dates, ...ladderAxisOption(plan)}`, che resta com'era.
- 21:02 — P6, `PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py front check`: al primo giro
  **1 errore**, `GrowthChart.svelte:2325`, TS2783 «'rotate' is specified more than once»
  (`/tmp/libreFolio_i_p6_front_check.log`). Corretto (sotto); al secondo giro **0 errori e 0 avvisi**
  (`/tmp/libreFolio_i_p6_front_check2.log`). `GrowthChart.test.ts` rilanciato dopo la correzione: 127 su 127.

> **⚠️ Fuori pista** (P6): la costruzione completa dell'asse a categorie scriveva `rotate: 0` prima di
> `...ladderAxis.axisLabel`, un default nato con `69cba356f`. Ora `ladderAxisOption` porta sempre `rotate`, quindi
> il default è morto e TypeScript lo segnala. L'ho tolto e al suo posto c'è un commento di una riga: la rotazione
> la decide sempre il piano. Nessun test fissava quel letterale. `AllocationHistoryChart.svelte:764` ha la stessa
> forma, ma la sua politica d'asse non porta `rotate`: non è toccato.

- 21:03–21:05 — P6, i gate unitari nella corsia (`… dev.py test --test-port 6157 --data-dir /tmp/librefolio-r2-i`):
  - `front-utility core-unit`: 115 file verdi su 116, **3402 passati e 3 saltati**; l'unico rosso è il noto
    **R13** (`optionFilter.test.ts`, «broker_degiro.py, description: expected exactly one definition, found 2»),
    non mio (`/tmp/libreFolio_i_p6_core_unit.log`);
  - `front-utility component-unit`: **2829 su 2829** (`/tmp/libreFolio_i_p6_component_unit.log`);
  - `front-asset growth-chart-memo`: **127 su 127** (`/tmp/libreFolio_i_p6_growth_memo.log`);
  - `front-asset asset-unit`: **710 su 710**, 20 file, compreso `growthLadderAxis.test.ts`
    (`/tmp/libreFolio_i_p6_asset_unit.log`).
- 21:06–21:12 — **P6 chiuso.** Nella corsia, uno alla volta:
  - `front build --debug`: rc 0, svelte-check 0 errori e 0 avvisi (`/tmp/libreFolio_i_p6_build.log`). L'avviso SSL
    sul download di MathJax dal CDN c'era già nel build delle 19:50: è dell'ambiente, non mio.
  - `front-portfolio dashboard`, intero e senza filtro: **27 su 27** (1,6 min,
    `/tmp/libreFolio_i_p6_e2e_dashboard.log`), compresi i 7 casi S7 (E1-1m, E1-1w, E2, E3, telefono, E4, E5). I
    quattro rossi di P3, tutti su H, sono verdi.
  - `front-broker detail` (§6 diceva un nome di selettore sbagliato, ora corretto): **33 su 33** (1,3 min,
    `/tmp/libreFolio_i_p6_e2e_broker_detail.log`). Dopo il run la porta 6157 è libera.
  - `prettier --check` sugli 11 file del frontend toccati: puliti (`/tmp/libreFolio_i_p6_prettier.log`).
    `git diff --check`: pulito. HEAD resta `9ea2d519b`.
  - `dev.py i18n audit`: 4154 chiavi, tutte complete, 0 inutilizzate (`/tmp/libreFolio_i_p6_i18n_audit.log`). I 3
    «non verificati» e la famiglia del backend senza chiavi stanno in namespace che questo lotto non tocca.
  - Il digest `[S7]` del verde:
    - il campo di rotazione è in gradi, 45 o 0, e nel log non c'è nessun valore in radianti (0,785…);
    - in orizzontale gli angoli coincidono con il riquadro (E5), `H` vale 360, le estensioni sono intere;
    - E1-1m, k = 1: «Oct '25, Nov, Dec, Jan '26, Feb … Oct»;
    - E1-1w, k = 2, contato dall'ultimo bucket: «Oct 6, 20, Nov 3, 17, Dec 1, 15, 29, Jan 12 '26, 26, Feb 9 … Oct 5»;
    - E3, zoomato, in orizzontale, la prima etichetta è «Apr '26»;
    - telefono, ruotato: la prima è «Nov '25»;
    - E4, `1d`, ruotato: la prima è «Jul 11», e il riquadro largo 292,57 px resta nella banda [232,5, 328);
    - E5, Proventi `3m`, in orizzontale: «Q4 '25, Q1 '26, Q2, Q3, Q4».
  - **Il costo in altezza della rotazione, misurato** (§10). Riferimento: 297,72 px in orizzontale.
    - `1m` a 1440 perde 27,43 px (270,29);
    - `1w` a 1440 ne perde 41,19 (256,53), con etichette come «Jan 12 '26»;
    - il telefono 29,07 (268,65);
    - E4 21,69 (276,03).
    Sono meno dei circa 60 px stimati per un'etichetta piena: le etichette nuove sono corte.
  - Il bordo sinistro delle Candele (E1, E3, telefono) è passato da 55,25 a 42,02 px; il destro resta a 615,36.
    - Non è il pianificatore: quel bordo lo decide la larghezza delle etichette dell'asse Y, che seguono i dati.
    - Gli scenari S7 leggono il portafoglio vero dell'utente E2E, che cambia con le quotazioni (è già fra i reperti
      del coordinator per il triage).
    - La prova: con la privacy, E3 passa da 46,6 a 41,93 px, circa la larghezza di un «-». Alle 19:50 l'asse aveva
      un tick negativo, ora no.

> **⚠️ Fuori pista** (P0): nell'analisi avevo stimato che il `containLabel` spingesse il grafico a destra di
> 0–15 px con le etichette ruotate. Non è così. Il pacchetto completo `echarts` registra l'algoritmo legacy, che
> per l'asse X toglie solo altezza. Ne vengono due regole del contratto, il bordo sinistro e `widestText` (§2).

- 21:18–21:23 — **P7, le schermate.** Server di review avviato nella corsia alle 21:18, dopo il `front build --debug`
  delle 21:06: `… dev.py server --test --port 6167 --data-dir /tmp/librefolio-r2-i`, con i dati E2E sintetici. Script
  `/tmp/libreFolio_i_p7_shots.mjs`, con il Playwright del lock caricato da `frontend/`, senza npx. Tre giri
  (`/tmp/libreFolio_i_p7_run{1,2,3}.log`; i primi due di prova, su una schermata sola) hanno prodotto 13 PNG
  in `/tmp/libreFolio_i_p7/`, con le misure della scena zrender in `measures.json`. Le copie sono nei file della
  sessione (`p7_shots/`), fuori dal repo. Le schermate:
  - Proventi `1M` su un anno, in italiano e in inglese, chiaro e scuro;
  - gli stessi con deposito e valore di acquisto spenti dalla legenda, in italiano, chiaro e scuro;
  - Candele `1W` su un anno e `3M`, in italiano, chiaro e scuro;
  - il pannello lotti di Apple (utente admin), in italiano, chiaro e scuro, a densità 2;
  - Candele `1W` su un anno a 2560 px, in inglese, chiaro.
  - **Colori**: il dividendo è oro in tutti e due i temi (`#b08d00` chiaro, `#facc15` scuro), nelle barre dei
    Proventi e nei marcatori dei lotti. Gli interessi sono viola, i costi arancio sotto lo zero, il deposito teal:
    nessuna coppia vicina si confonde più.
  - **Misure a 1440**: il grafico è largo 641 px.
    - Proventi `1M`: 13 bucket ruotati, 13 etichette, 10,0 px dalla legenda;
    - Candele `1W`: 53 bucket, k = 2, 27 etichette, 10,0 px;
    - Candele `3M`: 5 bucket in orizzontale, 5,0 px.
  - **A 2560: −2,9 px.** «Jan 5 '26», all'indice 13, entra nella fascia della legenda. Vedi il «Fuori pista» di P7.
- 21:37–21:45 — Due probe SSR in node, fuori dal repo, con l'echarts vero del lock: `/tmp/libreFolio_i_cl/probe.cjs`
  e `probe2.cjs`, con i log accanto. Svg 1300 × 420, la griglia di GrowthChart, 53 categorie, k = 1. Lo scarto
  verso la fascia della legenda, nelle metriche di ripiego di zrender:

  | Caso | Fondo griglia | Scarto | Esito |
  |---|---|---|---|
  | A, oggi: l'etichetta lunga all'indice 13, fuori campione | 348,34 | −11,38 | difetto riprodotto |
  | A2, l'etichetta lunga all'indice 14, nel campione | 332,01 | +4,95 | il riferimento giusto |
  | M‴: `width` W = 56,7 e `lineHeight` (1 o 14) | 332,01 | +4,95 | uguale ad A2 |
  | solo `width` | 348,34 | −11,38 | invariato |
  | `width` e sfondo trasparente | 348,34 | −11,38 | invariato |
  | L′: `grid.bottom` + 16,33 misurati | 332,01 | +4,95 | uguale ad A2 |

  - Il disegno di M‴ e di L′ è identico, con le posizioni prese rispetto al fondo della griglia.
  - Un aggiornamento del solo asse con `{rotate: 0, width: null, lineHeight: null}` toglie le due chiavi, e la
    geometria torna quella di un grafico nuovo in orizzontale.
- 21:52–21:54 — La raggiungibilità, sul server 6167 (`/tmp/libreFolio_i_reach.mjs` e
  `/tmp/libreFolio_i_p7b_shots.mjs`, misure in `/tmp/libreFolio_i_reach.json` e `/tmp/libreFolio_i_p7b/`).
  - Larghezza del grafico, dashboard e dettaglio broker (broker 5): 565,6 e 573,3 px a 1440; 833,4 e 841,2 a
    1920; 1012,0 e 1019,7 a 2240. La soglia di k = 1 con 41 bucket è 41 × 19,8 = 811,8 px.
  - **YTD con Candele `1W` a 1920**: 41 bucket, k = 1, 41 etichette. Lo spazio dalla legenda è **+1,5 px** in
    inglese e **−1,0 px** in italiano, invece di 10. A 1440, con k = 2, è 10,0 in tutte e due le lingue.
- 21:55 — Server fermato (stop della shell). `lsof -nP -iTCP:6167 -sTCP:LISTEN` e lo stesso su 6157: vuoti.

> **⚠️ Fuori pista** (P7): il campione del `containLabel` (§10) taglia la fascia sotto l'asse.
> - **La causa.** ECharts 6.0.0, `legacyContainLabel.js:58-120`: il formatter si misura su una categoria ogni
>   `ceil(visibili / 40)`, a partire dalla prima visibile, e senza chiedere `interval`.
>   - Sulle scale a giorni l'anno compare solo dove cambia, quindi l'etichetta lunga («Jan 5 '26») può stare su un
>     indice fuori campione.
>   - Se tutti gli indici del campione portano un'etichetta, la fascia esce bassa di (w lunga − w massima del
>     campione) · sin 45°.
>   - Il contratto in testa a `growthLadderAxis.ts` (righe 46-49) dice che la fascia è riservata all'etichetta
>     ruotata più alta. In questo regime è falso.
> - **Dove si vede.**
>   - Serve k = 1 con più di 40 bucket visibili, cioè un grafico di almeno 812 px: uno schermo di circa 1890 px o
>     più. Dashboard e dettaglio broker hanno la stessa larghezza (misurata).
>   - A 1920 bastano 41 o 42 bucket visibili, come l'YTD settimanale di inizio ottobre: oggi. A 2560 va da 41 a 59.
>   - Mai a 1440, ed è per questo che l'E2E non lo vede.
>   - Gli altri regimi possibili (k = 2 con passo 4 e 121–160 bucket, e simili) chiedono un grafico di almeno
>     1190 px circa.
> - **Che cosa vede l'utente.** L'etichetta dell'anno scende di qualche pixel nella fascia della legenda. Tocca il
>   testo della legenda solo se sta sotto il suo centro, e nelle schermate non succede.
> - **Smentito.** Né `width` da solo né uno sfondo trasparente cambiano qualcosa: lo stimatore non passa
>   `backgroundColor`. L'idea del token rich di §10 è superata.
> - **Confermato.** M‴ (`axisLabel.width` = la larghezza massima vera delle etichette disegnate, più
>   `lineHeight`, solo con `rotate: 45`) è esatto e non cambia il disegno.
>   - Un'interazione: nella fascia 14–14,28 px, quando la vicina è un giorno di una cifra, ECharts nasconde
>     un'etichetta d'estremo in più (60 → 59 nel probe).
>   - Si chiude con k calcolato sull'altezza vera della riga, circa 14,3 px.
> - Le tre strade vanno al coordinator: M‴ (consigliata), L′ e il rinvio come residuo. **Il contratto non lo
>   tocco prima della decisione.**

- 2026-10-08 10:17 — **Il coordinator approva l'opzione A (M‴)**, e nello stesso step k calcolato su una riga di
  14,3 px. Con le etichette ruotate, `axisLabel.width` è la larghezza vera della più lunga, più `lineHeight`.
  L'ordine:
  1. test rossi dal test-author: SSR con l'ECharts vero, più il pianificatore;
  2. la correzione e il contratto in testa al file;
  3. controlli e schermate a 1920 e 2560;
  4. poi P8 (docs) e P9 (checkpoint). Le prove a 1920 e 2560 vanno nel checkpoint.
- 2026-10-08 10:20–10:40 — Lettura, senza modifiche, del codice di ECharts e zrender che serve a M‴.
  - La misura: `axisLabelModel.getTextRect`, poi il rettangolo ruotato; per un asse x in basso conta solo
    l'altezza dell'unione.
  - Con `width` e `lineHeight` zrender disegna un rettangolo di sfondo senza riempimento, largo W: l'unione di
    ogni etichetta del campione è larga W, quindi la fascia è esatta.
  - `fixMinMaxLabelShow` gira, perché `interval` è una funzione: con box larghi W, due etichette vicine si
    toccano lungo il testo appena si toccano di traverso. La riga di 14,3 px, sopra l'altezza vera di 14,28, le
    separa di traverso.
  - In node, `14 × (14,3 / 14)` vale 14,300000000000002: il passo usa già la tolleranza `− 1e-9`.
  - Il nuovo test SSR va in `growthLadderAxis.test.ts`, che è già in `asset-unit` e gira in ambiente node senza
    mock di ECharts: nessun file nuovo da registrare nel runner, che è del coordinator.
- 2026-10-08 ✅ **P7b, passo 1: i test rossi** (test-author, solo `growthLadderAxis.test.ts` e
  `GrowthChart.test.ts`, nessun file nuovo).
  > **Note implementazione**:
  > - **Pianificatore (L15).** La costante `LADDER_LABEL_ROW_EM`; il `labelBox` (la più larga misurata fra le
  >   etichette visibili, alta una riga di font), escluse le etichette fuori finestra e quelle diradate; nessun
  >   box quando sono orizzontali, senza misura o senza etichette visibili; il box nella `key`. L'opzione porta
  >   sempre `width` e `lineHeight`, null senza box.
  > - **Riga di 14,3 px.** Ripinnati L7.2 (slot 19,9 → k = 2) e L9.1 (slot 10 → k = 3); nuovi L7.9 (20,0 → k = 2)
  >   e L7.10 (20,3 → k = 1). L8.1 passa da 199 a 203 px, con le stesse esclusioni. L'oracolo ha la sua costante
  >   e si ritrova con il pianificatore su tutti i 4160 piani.
  > - **SSR con l'ECharts vero (L16).** 53 settimane da lunedì 6 ottobre 2025, «Jan 5 '26» all'indice 13, fuori
  >   dal campione. Controllo «ECharts changed:»: senza box un'etichetta scende sotto la fascia (−8,12 px). Con il
  >   box sta dentro, e il fondo della griglia vale H − 30 − 8 − (W + 14)·√½. Il disegno resta identico, e un
  >   aggiornamento `{xAxis}` orizzontale toglie il box.
  > - **Componente (B6d, B6e, B9b).** Il finto `echarts` ora ha `format.getTextRect` e `getModel().get`. Ruotate:
  >   `width` = la più larga disegnata, `lineHeight` 14, misurate nel font del grafico. Orizzontali: nessuna delle
  >   due. L'aggiornamento parziale porta i due null presenti.
  > - **Verifica mia**, `vitest run` sui due file: 29 rossi e 241 verdi su 270, nessun TypeError; tutti i rossi
  >   sono asserzioni sulla funzione mancante. Il log è `/tmp/libreFolio_i_p7b_red_verify.log`.
  > - Il test-author ha provato il contratto su copie in `/tmp/libreFolio_i_ta5_sbx`: 289 verdi su 289, e i 13
  >   mutanti che dovevano rompere un test l'hanno rotto. Il sandbox va cancellato in P9.
  > **⚠️ Fuori pista**: `GrowthChart.tooltip.test.ts` ha un finto `echarts` senza `format`. Se il componente legge
  > `echarts.format` al caricamento, i suoi 6 test cadono. Quindi la lettura dev'essere pigra, dentro la misura.
- 2026-10-08 ✅ **P7b, passo 2: la correzione e il contratto.**
  > **Note implementazione**:
  > - **`growthLadderAxis.ts`.** La nuova costante `LADDER_LABEL_ROW_EM = 14.3 / 14`, con il perché. Il passo
  >   ruotato è `k = ceil(font · ROW_EM / (slot · √½) − 1e-9)`.
  >   - L'ingresso ha `measureLabelPx?`; il piano ha `labelBox: {widthPx, lineHeightPx} | null`.
  >   - Il box si calcola solo con `rotate` 45 e una misura. Misura solo le etichette visibili, ogni testo una
  >     volta, e prende il massimo non arrotondato; la riga vale `fontSizePx`. Altrimenti è null, anche nel
  >     piano vuoto.
  >   - Il box è nella `key`. `ladderAxisOption` porta sempre `width` e `lineHeight` (il box, o null).
  >   - `widestText`, le regole d'estremo e `halfLineAcross` non cambiano.
  >   - Nel contratto in testa cambiano la regola di k e il paragrafo su widestText e containLabel, ed entra
  >     il paragrafo labelBox.
  > - **`GrowthChart.svelte`.** `ladderLabelMeasure()` legge la famiglia del font dal modello del grafico alla
  >   prima misura di ogni piano (`'sans-serif'` se non è una stringa) e chiama `echarts.format.getTextRect`
  >   in 14 px solo dentro la misura. `planLadderFor` passa `measureLabelPx`. Nel render completo, `width` e
  >   `lineHeight` passano come `?? undefined`, perché quel render sostituisce l'asse. L'aggiornamento
  >   `{xAxis}` dello zoom porta i null.
  > - **Verifica.** `vitest run` su `growthLadderAxis.test.ts`, `GrowthChart.test.ts`,
  >   `GrowthChart.tooltip.test.ts` e `PerformanceChart.test.ts`: 289 verdi su 289, lo stesso conto del
  >   sandbox del test-author. Log: `/tmp/libreFolio_i_p7b_green4.log`. Prettier non cambia niente.
- 2026-10-08 ✅ **P7b, passo 3a: i controlli** (corsia 6157, `/tmp/librefolio-r2-i`, un comando alla volta,
  prefisso `PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py`).
  > **Note implementazione**:
  > - `front check`: 0 errori e 0 avvisi.
  > - `test front-utility core-unit`: 3402 verdi e 3 saltati; l'unico rosso è R13, `optionFilter.test.ts`,
  >   noto e non mio.
  > - `test front-utility component-unit`: 2829 verdi su 2829, compreso `GrowthChart.tooltip.test.ts`.
  > - `test front-asset growth-chart-memo`: 132 su 132. `test front-asset asset-unit`: 730 su 730.
  > - `front build --debug`: verde.
  > - E2E `test front-portfolio dashboard`: 27 su 27. E2E `test front-broker detail`: 33 su 33.
  > - Prettier `--check` sui 7 file toccati, `git diff --check` e `i18n audit` (4154 chiavi complete):
  >   tutti verdi.
  > - I log: `/tmp/libreFolio_i_p7b_{front_check,core_unit,component_unit,gcmemo,asset_unit,build,e2e_dashboard,e2e_broker_detail,i18n}.log`.
- 2026-10-08 ✅ **P7b, passo 3b: le schermate a 1920 e 2560.** Server di review sulla 6167 con
  `/tmp/librefolio-r2-i`, `--no-scheduler --no-reload`, dopo `front build --debug`; nessuna suite mentre girava.
  Fermato, e `lsof` sulla 6167 e sulla 6157 non trova niente in ascolto.
  > **Note implementazione**: lo scarto è lo spazio fra il fondo dell'etichetta più bassa e la legenda, prima
  > e dopo:
  >
  > | Schermata | Etichette | Scarto (px) | Altezza del grafico (px) |
  > |---|---|---|---|
  > | 2560, 1A, 1S, en (53 settimane, slot 22,36) | 53 → 53 | −2,86 → **10,05** | 274,94 → 262,03 |
  > | 1920, YTD, 1S, en (41 settimane, slot 20,19) | 41 → 21 | +1,55 → **10,05** | 270,54 → 256,53 |
  > | 1920, YTD, 1S, it | 41 → 21 | −0,97 → **10,05** | 274,39 → 257,86 |
  > | Le altre 11 (Proventi 1M, Candele 1S e 3M, chiaro e scuro, 1440) | uguali | uguali | uguali |
  >
  > - A 2560 agisce solo il box: tutte e 53 le etichette restano, e «Jan 5 '26» non scende più sulla legenda.
  > - A 1920 lo slot di 20,19 sta sotto la nuova soglia di 20,2233, e la riga di 14,3 px dirada a k = 2.
  > - I byte dei PNG cambiano anche dove la geometria è identica, compreso il pannello lotti, che non ha
  >   quest'asse: le suite E2E di prima hanno cambiato i dati sotto i grafici. Fa fede la geometria.
  > - Le schermate (17 PNG, misure e tabella) sono nella cartella `files/p7b_shots_after/` della sessione, non
  >   versionate.
- 2026-10-08 11:58 ✅ **P8: il punto nelle docs.** Il docs-writer ha aggiunto il punto «How the periods are labelled.»
  in `mkdocs_src/docs/user/dashboard/charts.en.md`, sezione `#pnl-width`, subito dopo «Calendar periods.». Solo
  inglese, senza colori e senza numeri in pixel.
  > **Note implementazione**:
  > - Il testo è verificato sul codice:
  >   - il contratto in testa a `growthLadderAxis.ts`;
  >   - `growthLadderBuckets.ts`: la settimana parte dal lunedì, quindi l'esempio dell'1 gennaio 2026 porta
  >     «Dec 29»;
  >   - le chiavi `dashboard.pnlAxisQuarter` e `dashboard.pnlAxisWithYear` in `en.json` e `it.json`.
  > - La pagina non ha una riga «Last updated»: non c'era niente da aggiornare.
  > - Nessun `translate-stamp`. Il debito di traduzione è vero, perché it, fr ed es non hanno la sezione P&L, e
  >   resta sulla lista del coordinator.
  > - `dev.py mkdocs build` (strict): verde, nessun avviso.
  > - `dev.py mkdocs check-links`: 89 link validi. L'unico ❌ è D28, noto: `user/assets/detail/chart/#rolling-return`,
  >   assente in it, fr ed es.
  > - `dev.py mkdocs translate-validate --file user/dashboard/charts.en.md`, in sola lettura: 48 errori e 12 avvisi
  >   sulle 3 lingue, quasi tutti preesistenti. Il punto nuovo aggiunge un elemento al divario dei punti elenco.
  > - I log: `/tmp/libreFolio_i_p8_{mkdocs_build,check_links,translate_validate}.log`.
  >
  > **⚠️ Fuori pista**: il codice ha corretto due frasi del brief di §8.
  > - **«Solo le candele molto fitte saltano qualche etichetta» non è assoluto.** Se nessuna larghezza passa la
  >   regola dei 4,5 px, `availableCandleWidths` offre comunque il gradino minimo dei Proventi, `1S`
  >   (`GrowthChart.svelte:486`, da `e7773a143` del 22/09). Con barre così strette anche i Proventi si diradano.
  >   - Succede su un telefono (grafico di circa 279 px) da 14 anni di calendario in su, e a 1440 da 28.
  >   - Il ripiego è preesistente e coerente con la regola: si dirada solo dove nemmeno ruotate le etichette ci
  >     stanno.
  >   - La pagina dice «in practice, only with very dense Candles, not with Income». Va al checkpoint come residuo.
  > - **Il taglio al bordo vale solo per le etichette ruotate.** Esiste solo nel ramo ruotato di
  >   `growthLadderAxis.ts`. Un'etichetta orizzontale si sposta invece verso l'interno, e se così urta la vicina
  >   ruota tutto l'asse. La pagina dice «A turned label…».
- 2026-10-08 12:03 ✅ **P9: pulizia, controlli finali, CHECKPOINT READY.**
  > **Note implementazione**:
  > - **Archivio, poi cancellazione.**
  >   - Le 85 voci `/tmp/libreFolio_i_*` citate come prove sono copiate nella cartella `files/i_tmp_archive_20261008/`
  >     della sessione (2,3 MB, non versionata): log, script, sonde, mutanti. `diff -rq` le ha confrontate una per una
  >     prima di cancellarle.
  >   - Cancellati senza copia:
  >     - le due cartelle delle schermate, già identiche byte per byte in `files/p7b_shots_after/` (`cmp` sui 17 PNG e
  >       sulle due misure);
  >     - i due log del server, mai citati;
  >     - la sandbox del test-author, 103 MB. Il suo `node_modules` era un collegamento simbolico alla worktree: è
  >       sparito solo il collegamento, e `frontend/node_modules` è intatto, compreso `.bin/vitest`.
  >   - `ls -d /tmp/libreFolio_i_*` risponde «No such file or directory». La cartella dati della corsia,
  >     `/tmp/librefolio-r2-i`, resta.
  > - **I percorsi `/tmp` citati in questo Registro non esistono più**: le copie, con lo stesso nome, sono
  >   nell'archivio della sessione, e gli esiti restano scritti qui. Vale anche per i 5 log `evt_*` che il piano
  >   dell'evento sul cache hit diceva «restano come prove».
  > - Le porte 6157 e 6167 sono libere: `lsof -nP -iTCP:<porta> -sTCP:LISTEN` non stampa niente. `git diff --check`
  >   è pulito.
  > - **Previsione dei conflitti.**
  >   - `dev_release2` è avanzato a `58fc35174`, 41 commit con i treni 10 e 11; la base comune resta `9ea2d519b`.
  >   - L'unica sovrapposizione sono i 4 cataloghi. Il conflitto è testuale, un pezzo per file, in coda a
  >     `dashboard` dopo `allocationGeneric`: le mie `pnlAxisQuarter` e `pnlAxisWithYear` contro le
  >     `unrealizedAssetEffect`, `unrealizedFxEffect` e `unrealizedUnsplit` di Risk (`2d8914be4`).
  >   - La soluzione è l'unione, con la virgola. Simulata in `/tmp` con `git merge-file -p`: JSON valido, 4162 chiavi
  >     (le 4160 del target più le mie 2), niente perso e nessun valore cambiato.
  >   - Dei moduli importati dai miei file, il target tocca solo `$lib/i18n`.
  > - Messaggi di commit proposti, ASCII, righe di al massimo 68 caratteri:
  >   1. `/tmp/libreFolio_commit_i_axis_01-feat.msg`, `feat(charts): gold dividends, period-start P&L axis labels`:
  >      codice, test e cataloghi insieme, così nessun commit contiene un test rosso;
  >   2. `/tmp/libreFolio_commit_i_axis_02-docs.msg`, `docs(charts): describe P&L axis period labels`;
  >   3. `/tmp/libreFolio_commit_i_axis_03-journal.msg`, `docs(journal): record income colors and axis labels batch`:
  >      questo piano e il «Seguito» nel piano del round 4.
  >
  > **⚠️ Fuori pista**: il primo giro dello script di pulizia si è fermato alla verifica, prima di cancellare
  > qualsiasi cosa. Il log del `tee` portava il mio stesso prefisso e cresceva mentre lo confrontavo. Ho rifatto
  > l'archivio da zero, con il log fuori da `/tmp`.
- 2026-10-08 12:13 ✅ **Checkpoint verificato dal coordinator.** 14 percorsi, albero `00085452dd4c`, privacy pulita
  su 3403 righe, prova sul clone.
  > **⚠️ Fuori pista**: il coordinator ha accorciato due oggetti a 50 caratteri, la regola del progetto. I corpi non
  > cambiano.
  > - C1: `feat(charts): gold dividends, period axis labels`. Io avevo proposto
  >   `feat(charts): gold dividends, period-start P&L axis labels`, 58 caratteri.
  > - C3: `docs(journal): income colors and axis labels`. Io avevo proposto
  >   `docs(journal): record income colors and axis labels batch`, 57 caratteri.
  > - La regola, per i prossimi messaggi: oggetto di al massimo 50 caratteri, righe del corpo di al massimo 72.
- 2026-10-08 12:18 ✅ **I commit del developer**, su `9ea2d519b`: `bc08101d6` (C1), `835c65d7d` (C2) e `e379cff59`
  (C3), con l'albero uguale a quello rivisto. Nello stesso lotto il treno 12 (K19 e L34) è entrato in `dev_release2`.
  Poi il developer ha avviato il merge della punta del treno 12, `ffa72cc2b`, nel mio ramo, e l'ha lasciato aperto sui
  4 cataloghi.
- 2026-10-08 12:37 ✅ **P10: il merge del treno 12 nel ramo, MERGE RESOLVED.**
  > **Note implementazione**:
  > - **Lo stato.** HEAD `e379cff59`, MERGE_HEAD `ffa72cc2b`, base comune `9ea2d519b`.
  >   - In conflitto solo i 4 cataloghi, un pezzo per file in coda a `dashboard`, dopo `allocationGeneric`: quello
  >     previsto in P9.
  >   - Gli altri 176 percorsi del target (32 aggiunti, 2 cancellati, 142 modificati) li ha fusi Git da solo.
  > - **La soluzione: l'unione, prima le mie.** In ogni catalogo vengono prima `pnlAxisQuarter` e `pnlAxisWithYear`,
  >   con la virgola, poi le tre `unrealized*` di Risk (`2d8914be4`).
  >   - Il perché: rispetto a `dev_release2` è un inserimento puro di 2 righe. Nessuna riga altrui cambia, e la sua
  >     blame resta di chi l'ha scritta. L'unica riga che non appartiene a nessuno dei due genitori è la mia
  >     `pnlAxisWithYear`, con la virgola.
  >   - L'ordine opposto avrebbe modificato la riga `unrealizedUnsplit` di Risk, per aggiungerle la virgola.
  > - **La verifica**, a tre vie sugli stage `:1`, `:2` e `:3`:
  >   - JSON valido, nessuna chiave doppia;
  >   - il risultato appiattito è uguale alla fusione semantica a tre vie di base, mio e target;
  >   - rispetto a MERGE_HEAD, esattamente 2 righe in più, alla 1633;
  >   - chiavi per lingua: base 4152, mio 4154, target 4162, risultato 4164;
  >   - dal target, rispetto alla base: 10 chiavi nuove (`auth.serverUnreachable.{title,body}`,
  >     `dashboard.unrealized{AssetEffect,FxEffect,Unsplit}`, `dataQuality.missingCostBasis` e 4
  >     `risk.errors.resource_limit_*`), 2 valori cambiati (`settings.deleteAccount{Description,Warning}`), nessuna
  >     chiave tolta.
  > - **Lo stage.** `git add` dei soli 4 cataloghi; blob en `10d96ee326c3`, it `befe01828881`, fr `e70bd4a2d5f3`, es
  >   `7d73bc538522`.
  >   - Nessun percorso non fuso, worktree uguale all'indice, nessun file non tracciato.
  >   - `git diff --cached --check` è pulito contro entrambi i genitori, e la regola a tre vie, percorso per percorso,
  >     non trova scarti.
  >   - L'albero in stage è `08b4960930eb`, calcolato con un indice e un archivio di oggetti temporanei.
  > - **I gate sulla revisione unita**, sulla 6157, uno alla volta:
  >
  >   | Gate | Prima del merge (P7b) | Revisione unita |
  >   |---|---|---|
  >   | `front build --debug` | verde | verde |
  >   | `front check` | 0 errori, 0 avvisi | 0 errori, 0 avvisi |
  >   | `core-unit` | 3402 verdi e 3 saltati; rosso R13 | 3430 su 3430 in 117 file, 0 saltati: R13 è verde |
  >   | `component-unit` | 2829 | 2846 in 110 file |
  >   | `growth-chart-memo` | 132 | 132 |
  >   | `asset-unit` | 730 | 730 in 20 file |
  >   | `i18n audit` | 4154 chiavi complete | 4164 complete; 0 incomplete, 0 mancanti, 0 inutilizzate |
  >   | E2E `front-portfolio dashboard` | 27 su 27 | 27 su 27 (1,6 min) |
  >   | E2E `front-broker detail` | 33 su 33 | 33 su 33 (1,4 min) |
  >
  >   - Nell'audit restano i 3 «non verificati» e la famiglia backend di prima.
  >   - Non lanciati, perché fuori dalla lista del coordinator: le suite backend (il mio delta è solo frontend),
  >     `check-orphans`, il `prettier --check` dei cataloghi, `mkdocs build` e `check-links`.
  > - **Il database della corsia.** Il treno 12 non porta migrazioni nuove: `298ed96f3` (L) modifica `001_initial.py`
  >   sul posto, e il pacchetto `backend/app/db/post_migration/` corregge all'avvio i database esistenti.
  >   - Il DB della corsia (Alembic `004`, senza AUTOINCREMENT) è stato convertito al primo avvio del server
  >     dell'E2E, alle 12:30. Il log della corsia, `/tmp/librefolio-r2-i/logs/librefolio.log`, dice «Orphan broker
  >     folders quarantined» (le 3 cartelle `broker_9`), poi «Post-migration fixes applied and verified»,
  >     correzione `autoincrement`, 0,01 s.
  >   - Dopo: 6 tabelle con AUTOINCREMENT, conteggi invariati, integrità ok, 0 violazioni di chiave esterna, nessun
  >     backup e nessuna cartella in quarantena rimasti. Nessun repopulate.
  >   - L'E2E del broker ha poi creato e cancellato i broker 9 e 10. Il 9 riusa l'ID una volta, come prevede il
  >     docstring di `autoincrement.py` (piano `34_accountAndIdReuse` §2.3, decisioni D1 e D4): le vecchie cartelle
  >     erano già sparite.
  >   - Ora la sequenza dei broker vale 10, e in `uploaded`, `parsed` e `failed` restano le cartelle vuote
  >     `broker_9` e `broker_10`: orfane innocue, perché gli ID non tornano più.
  > - Le porte 6157 e 6167 sono libere.
  > - Il messaggio del merge proposto: `/tmp/libreFolio_commit_i_axis_merge.msg`,
  >   `merge(charts): dev_release2 into I for train 13`, 47 caratteri, ASCII, righe del corpo di al massimo 68.
  >
  > **⚠️ Fuori pista**:
  > - **4164 chiavi, non 4162.** La previsione di P9, fatta su `58fc35174`, non poteva contare le 2 chiavi
  >   `auth.serverUnreachable.*` di K (`93fd33702`), arrivate col treno 12. Stanno fuori dal pezzo in conflitto: le
  >   ha fuse Git da solo.
  > - **Due frasi dell'handoff da correggere.**
  >   - «È lo stesso ordine della simulazione del checkpoint (`git merge-file --union`)»: non è verificabile. Lo
  >     script della simulazione di P9 non è archiviato, e P9 qui dice solo `git merge-file -p`. Ritiro la frase:
  >     l'ordine si giustifica da solo, come sopra.
  >   - «Indice invariato dopo ciascuno»: esagerato. Ho controllato indice e worktree dopo la build e alla fine,
  >     sempre sull'albero `08b4960930eb`, non dopo ogni gate.
  > - **`grep -P` non esiste su macOS.** Il primo controllo ASCII del messaggio ha stampato «ascii ok» dopo un
  >   errore di `grep`. L'ho rifatto in Python: 0 byte non ASCII.
- 2026-10-08 12:38 ✅ **Il coordinator verifica il merge.** Lo stage `08b4960930eb` differisce dal merge automatico
  solo nei 4 cataloghi: nessun marcatore, nessuna riga persa da nessuna delle due parti, JSON validi, 4164 chiavi per
  lingua. Il messaggio va bene: il file dello script, `/tmp/libreFolio_commits/i_merge_t12.txt`, è identico al mio.
  Lo script `/tmp/libreFolio_i_merge_t12.sh`, provato su un clone, lo lancia il developer.
- 2026-10-08 12:54 ✅ **Il merge è committato: `56483392c`.** Genitori `e379cff59` e `ffa72cc2b`, albero
  `08b4960930eb`, messaggio identico byte per byte a quello proposto, worktree pulito.
- 2026-10-08 12:55 ✅ **P11: queste note, la pulizia, il checkpoint piccolo.**
  > **Note implementazione**:
  > - Le prove del merge, 23 file, sono nella cartella `files/i_ax_merge_20261008/` della sessione, non versionata:
  >   i 9 log dei gate, i 4 messaggi di commit, gli script e i log della risoluzione e della verifica. Confrontate
  >   con `cmp` prima di cancellare gli originali.
  > - I percorsi `/tmp/libreFolio_i_ax_merge_*.log` e `/tmp/libreFolio_commit_i_axis_merge.msg` citati qui non
  >   esistono più. Il log della corsia resta, con la cartella dati.
  > - Il commit proposto per queste note, a parte: `/tmp/libreFolio_commit_i_t12_journal.msg`,
  >   `docs(journal): record train-12 merge into I`.
  > - Le porte 6157 e 6167 sono libere. FROZEN fino al commit; poi il treno 13, con N e il G3 di M.
