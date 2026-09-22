# 05 — Grammatica visiva e rappresentazioni

> Blocco UI/UX. Presuppone la tesi e i quattro livelli di
> [`01-tesi-e-quattro-domande.md`](./01-tesi-e-quattro-domande.md) e i verdetti di
> [`02-verdetti-per-strumento.md`](./02-verdetti-per-strumento.md).
> Decisioni prodotte qui: **D14-D19** in
> [`04-decisioni-e-questioni-aperte.md`](./04-decisioni-e-questioni-aperte.md).
>
> Ultimo aggiornamento: 16 Settembre 2026

---

## 1. Perché serviva questo blocco prima dei layout

Il piano iniziale prevedeva di passare dalla mappa livelli × pagine direttamente ai
layout. È stato un errore, emerso da una sola osservazione del developer: la prima
bozza è *«esteticamente ampiamente insufficiente, non segue le regole estetiche del
resto del progetto, non è ottimizzata per gli schermi, non è chiara, non è modulare»*.

La verifica sul codice ha confermato ogni punto e ha rivelato che la causa non è dove
sembrava. Disegnare nuovi layout sopra le primitive attuali avrebbe riprodotto gli
stessi difetti in una disposizione diversa.

---

## 2. Diagnosi estetica

### 2.1 L'idraulica sì, la voce no

Il sottosistema rischio **non** è un'isola stilistica: usa `SimpleSelect`,
`SearchSelect`, `TabBar`, `PageSyncModal`, `InfoBanner`, `DataQualityBanner`,
`LineChart`, `KpiCard`. Ha adottato le primitive **strutturali**.

Non ha adottato **nessuna** di quelle espressive:

| Primitiva | Ruolo | File nel progetto | File nel rischio |
|---|---|---|---|
| `Tooltip` | spiegabilità — bordo punteggiato = «cliccami» | **61** | **0** |
| `DocsLink` | link alla documentazione | 3 | **0** |
| `TweenedValue` | numeri animati | 3 | **0** |
| `KpiMetricBar` | barra etichetta + valore + tooltip | 2 | **0** |
| `KpiDivergingFlowBar` | barra divergente | 1 | **0** |
| `formatCurrencyAmountPlain` | formattatore valuta unico | condiviso | **0** (duplicato) |

I numeri ci sono ma non parlano, non si muovono e non rimandano a nulla. È questa
l'origine dell'impressione di povertà, non la disposizione degli elementi.

Due conseguenze pratiche:

- **`DocsLink` esiste già.** Le ⓘ accanto a VaR e CVaR previste da D4 non vanno
  inventate: vanno collegate.
- **Le barre divergenti sono state riscritte a mano.** `RiskAnalysisPanel:854-870`
  costruisce `<div>` con `absolute left-1/2` e larghezze inline, mentre
  `KpiDivergingFlowBar` fa lo stesso in 55 righe testate e con tooltip. Stessa storia
  per il formattatore valuta, duplicato in `riskAnalysisHelpers.ts:130`.

### 2.2 Incoerenza interna

Nei soli componenti rischio convivono due stili di contenitore:

```
class="bg-white dark:bg-slate-800 rounded-xl border ... shadow-sm p-4"   ← 2 casi
class="rounded-xl border ... bg-white dark:bg-slate-800 p-4"             ← 5 casi
```

Il canone del progetto è `bg-white rounded-xl border border-gray-100 shadow-sm`
(29 occorrenze concordi). Cinque contenitori su nove sono **piatti**. È il motivo per
cui il pannello sembra un wireframe accanto al resto dell'applicazione.

> Nota: `--shadow-card` è definita in `app.css` e usata **zero volte** in tutto il
> progetto. Token morto, da rimuovere o da adottare — non da citare come regola.

### 2.3 «Non ottimizzata per gli schermi», alla radice

```
grid-cols-1 sm:grid-cols-2 xl:grid-cols-5     ← 5 KpiCard
```

Fra `sm` (640px) e `xl` (1280px) non esiste alcun gradino. Su un portatile da 1366px:
due colonne per cinque card, tre righe, una card orfana. Sopra i 1280px: cinque card
in fila dentro una colonna già ridotta dalla sidebar, ciascuna troppo stretta per il
proprio numero.

Le barre del contributo usano
`grid-cols-[minmax(7rem,1fr)_minmax(10rem,2fr)_5rem]`: 22rem di minimi rigidi che su
mobile sfondano il contenitore.

La causa profonda non è la mancanza di breakpoint. È che la dashboard risolve il
problema in modo **diverso e migliore** — vedi §4.

### 2.4 Deriva tecnica

`CorrelationHeatmap` si è scritto in proprio ciò che il progetto già fornisce:
`ResizeObserver` e `MutationObserver` a mano invece di `createResizeWatcher`;
`animation: false` invece di `CHART_ANIMATION_CONFIG`; nessun uso di
`tooltipPositionAboveFinger` né `scheduleFirstRenderStabilityFix`, che ogni altro
grafico del progetto adotta.

**Conclusione (D15)**: i componenti rischio attuali sono una bozza da sostituire, non
da rattoppare.

---

## 3. Il contratto di primitive — tre gradini, in quest'ordine

### Gradino 1 — Promuovere il generico

`KpiMetricBar` e `KpiDivergingFlowBar` vivono in `components/dashboard/` ma di
dashboard non hanno nulla: sono barre. Vanno in `components/ui/`.

Questo è il *«non è modulare»* nella sua forma concreta: non è il rischio a essere
poco modulare, è che le primitive riusabili sono parcheggiate in una cartella che ne
scoraggia il riuso. Chi scrive un componente rischio non pensa di cercare una barra
dentro `dashboard/`.

### Gradino 2 — Definire il vocabolario del rischio

Una sola card metrica, usata ovunque, costruita sopra le primitive promosse.
Anatomia in §4.

### Gradino 3 — Solo dopo, i layout per zona

Saltare 1 e 2 significa ridisegnare sopra gli stessi mattoni storti.

---

## 4. Anatomia della card — cosa copiare dalla dashboard

Da `KpiSection.svelte`, la card che funziona:

| Elemento | Implementazione | Perché conta |
|---|---|---|
| Tipografia fluida | `@container` + `text-[clamp(0.95rem,8cqw,1.5rem)]` | Il numero si ridimensiona col **contenitore**, non col viewport |
| Striscia d'accento | `absolute top-0 h-0.5`, colorata per segno | Stato leggibile prima di leggere la cifra |
| Link documentazione | `DocsLink` nell'intestazione | Già pronto, già stilato |
| Numero animato | `TweenedValue` + `tabular-nums` | Le cifre non ballano durante la transizione |
| Etichetta | `text-xs font-medium uppercase tracking-wide text-gray-400` | Canone del progetto |
| Skeleton | `class:invisible={loading}` sopra un placeholder assoluto | Il valore resta nel DOM: **nessuno spostamento di layout** |
| Sotto-metriche | righe `KpiMetricBar` | Gerarchia interna alla card |

La tipografia fluida è la vera risposta al punto 2.3: risolve il problema alla radice
invece di aggiungere gradini a una griglia.

Due aggiunte specifiche del rischio:

- **Etichetta doppia** — frase in lingua naturale come titolo, nome tecnico in piccolo
  accanto. *«Giornata brutta (1 su 20)»* con `VaR 95%` sottotitolo. Chi non sa cos'è il
  VaR legge la frase; chi lo sa trova il termine; chi vuole capire clicca la ⓘ.
- **Slot sparkline** — opzionale, popolato solo dove una serie esiste davvero.

---

## 5. Il vincolo sullo storico

`SignalDomain` ha due soli valori: `ASSET` e `FX`
(`backend/app/schemas/signals.py:84`). **Non esiste un dominio portafoglio.** Tutti e
sei i segnali rischio dichiarano `compatible_domains = (SignalDomain.ASSET,)`.

Quindi:

- sparkline su **Asset Detail** ≈ gratis, i segnali già girano;
- su **Dashboard e Broker Detail** il rolling di portafoglio **non esiste in tutto il
  codice**. Crearlo richiederebbe `SignalDomain.PORTFOLIO` e toccherebbe l'intera
  piattaforma segnali.

**D18**: non serve per la v1. Non per rinuncia, ma perché le rappresentazioni scelte
in §7 usano dati che il backend già produce — e per la volatilità l'istogramma della
distribuzione dice *più* di una sparkline del suo rolling.

---

## 6. Il backend emette più di quanto la UI mostri

Non è un caso isolato, è un pattern con tre occorrenze verificate:

| Dato calcolato e spedito al browser | Destino nella UI |
|---|---|
| `RiskDrawdownOutput` — 11 campi narrativi | **mai richiesto** |
| `RiskComparisonPoint.primary_drawdown` — serie completa | **scartata** |
| `RiskContributionItem.weight` | **scartato** |

Il secondo caso abbassa il costo di **D14**: la serie di drawdown è già calcolata
dentro `comparison` per entrambe le gambe e già spedita a ogni confronto. Esporla in
`drawdown_summary` è un refactor, non matematica nuova.

Il terzo abilita la proposta §7.3 a **costo zero**.

---

## 7. Le sei rappresentazioni

### 7.1 L1 — Underwater chart

```
  0 ┼──────────────────────────────────────────────────
    │ ╲        ╱‾╲              ╱‾‾‾╲         ╱‾╲
    │  ╲__╱‾╲_╱   ╲            ╱     ╲_______╱   ╲___
    │            ▓▓▓▓▓▓▓▓▓▓▓▓▓▓                   ▲
    │            ▲         ▲                      │
    │          picco     minimo                oggi −4,2%
    │        6 mar 22   14 ott 22          serve +4,4%
 −20%┼──────────────────────────────────────────────────
```

Area ECharts sempre ≤ 0. `markArea` sull'episodio peggiore, `markPoint` su
picco / minimo / recupero.

La distanza verticale fra la linea e lo zero **è** `remaining_to_peak_ratio`: il numero
più istruttivo del sottosistema diventa una lunghezza che si guarda invece di una
cifra da interpretare.

> Lezione che il grafico insegna da solo: perdere il 10% non richiede +10% per
> tornare al punto di partenza, ma +11,1%. A −50% servono +100%. L'asimmetria fra
> perdita e recupero è il motivo per cui il drawdown conta più della volatilità.

**Costo**: serie dal backend (D14, refactor) + grafico.

> **Nessuna generalizzazione dei segnali necessaria.** `DrawdownPlugin.compute` scarta
> `context` e `event_points` e lavora solo su `price_points`: è già agnostico rispetto
> alla sorgente. Soprattutto, importa `underwater_drawdown` **da**
> `services/risk/metrics.py` — la matematica vive già nel layer rischio, è il segnale a
> prendere in prestito. L'analytic deve solo chiamare la funzione direttamente, come già
> fa in `metrics.py:234`, `:283`, `:590-591`.
>
> `drawdown_episodes()` calcola già `underwater = underwater_drawdown(wealth)` in una
> variabile locale e ne restituisce solo gli scalari. Esporre la serie significa
> restituire ciò che la funzione ha già in mano. `compatible_domains` non governa la
> matematica: è un filtro di catalogo (`api/v1/assets.py:737`, `fx.py:521`).

### 7.2 L1 — Istogramma della distribuzione

```
         │                    ▁▄█
         │                  ▂████▆
   ▁▂▃  │▁▂▄▆████████▆▄▂▁
 ██████▓▓│
 ▲    ▲  │
 │    └─ VaR 95% : −1,7%  ·  1 giorno su 20 va peggio di qui
 └────── CVaR 95%: −2,7%  ·  media di quando va peggio
   ▓ = coda (5% dei giorni)
```

Bin dei rendimenti giornalieri, barre a sinistra del taglio in rosso, `markLine` sul
VaR e una seconda sul baricentro della coda.

Rende visibile la **definizione**: il CVaR *è* la media della parte rossa. Nessun testo
lo spiega meglio.

**Costo**: nuovo campo sull'output VaR con i bin. Payload piccolo, e **la regola di
binning non va implementata: NumPy la espone già** — vedi
[`06`](./06-matematica-librerie-e-reimplementazioni.md) §6 R5. Unico costo backend di
L1 oltre alla serie.

**Come si costruiscono i bin.**

- **Larghezza secondo Freedman-Diaconis**: `2 · IQR / n^(1/3)`, con guardrail su numero
  minimo e massimo di bin. Sturges e Scott vanno scartate perché usano la deviazione
  standard o presuppongono normalità, e la deviazione standard dei rendimenti
  finanziari è gonfiata **proprio dagli outlier che vogliamo guardare**: userebbero la
  coda per decidere come disegnare la coda. L'intervallo interquartile è robusto.
  In pratica è una stringa: `np.histogram(x, bins='fd')`. Verificato su 750
  osservazioni → 21 bin, `sum(counts) == 750`.
- **Un bordo di bin forzato sul quantile del VaR.** Altrimenti il taglio cade dentro un
  bin e l'area rossa è *circa* il 5%: il grafico direbbe una cosa lievemente falsa.
  Forzando il bordo, l'area rossa è **esattamente** il 5% delle osservazioni.
  È l'unica parte scritta da noi: `np.histogram_bin_edges` dà la larghezza, noi
  trasliamo la griglia. Cinque righe.
- **Stessa serie di rendimenti del VaR.** `RiskVarCvarOutput` espone `horizon_days`: se
  l'orizzonte supera il giorno, i rendimenti da raggruppare sono quelli a `h` giorni.
  Altrimenti barre e linea raccontano due cose diverse — lo stesso errore evitato
  rifiutando il drawdown lato client (D14).
- **Attenzione al pavimento a zero.** `historical_var_cvar` calcola le perdite con
  `max(-value, 0.0)`: il VaR non può essere negativo. Su una serie che sale in modo
  molto stabile la linea rossa cadrebbe sullo zero e non su un quantile dei dati.
  Caso raro ma da gestire, non da scoprire in produzione.

Payload: ~50 terne `(bordo_inf, bordo_sup, conteggio)`.

> **Niente gaussiana sovrapposta** (Q6 chiusa). Il VaR mostrato è `historical_var`, un
> quantile empirico: nessuna assunzione di normalità entra nel calcolo. Disegnare la
> campana confronterebbe i dati con un modello che non stiamo usando, e suggerirebbe
> che la campana sia il comportamento atteso e lo scarto un'anomalia — mentre per i
> rendimenti finanziari le code grasse *sono* la norma. La lezione resta valida ma
> appartiene alla pagina wiki sul VaR. L'unico punto dove si guadagnerebbe il posto è
> **L4**, dove un modello lo stiamo davvero scegliendo: mostrare cosa assume il GBM
> contro cosa produce il bootstrap è lì decision-relevant.

### 7.3 L2 — Peso contro contributo al rischio — **gratis**

```
                peso ▏ contributo al rischio
  NVDA      ████ 8%  ▏ ██████████████ 23%   ← 2,9×
  BTC       ███ 6%   ▏ █████████ 15%        ← 2,5×
  VWCE      ████████████████ 41% ▏ ████████████████ 38%   ← 0,9×
  Oro       ██████ 12% ▏ ██ 4%              ← 0,3×
```

Il contributo al rischio da solo non risponde alla domanda di L2. La risposta è lo
**scarto** fra quanto pesa un asset e quanto rischio produce.

Ordinamento per scarto decrescente: in cima finisce sempre ciò che sta rischiando più
di quanto si creda. Titolo generato dai dati: *«NVDA pesa l'8% ma produce il 23% del
rischio»*.

`weight` e `percentage_contribution` sono **già entrambi nel payload**. Solo frontend.

Variante da valutare: *dumbbell* (due punti uniti da un segmento) — lo scarto diventa
la lunghezza del segmento, ancora più diretto. Barre appaiate come prima scelta.

### 7.4 L2 — Heatmap delle correlazioni

Dossier completo in §8.

### 7.5 L3 — Scatter rischio-rendimento

```
 rend │        ⬤ portafoglio
      │      ╱
      │    ╱ ◇ benchmark          ⬤ = tu (bolla ∝ peso)
      │  ╱   · · ·                ◇ = benchmark
      │╱  ·   ·                   ·  = singoli asset
      ┼──────────────────  volatilità
```

Sopra la retta = pagato bene per il rischio preso. È la Capital Market Line senza
pronunciarne il nome.

**Costo medio-alto**: richiede volatilità e rendimento per ogni asset dell'insieme.
Unica proposta con un costo backend non marginale.

### 7.6 L4 — Tornado degli scenari

```
  2008 Lehman        ████████████████ −18.400 €
  Covid mar 2020     ██████████ −11.200 €
  Tassi +200bp       ████ −4.100 €
```

Barre orizzontali in euro, ordinate per severità. Sostituisce due tabelle HTML.
Dati già nel payload di `stress`.

### 7.7 L4 — Cono della simulazione

`RiskSimulationOutput.percentile_bands` espone già `p05 / p50 / p95` per ogni giorno
dell'orizzonte. `buildBandSeries` (usata per le Bollinger) rende le bande.
**Costo basso**, riuso puro.

---

## 8. Dossier heatmap

### 8.1 Correzione preliminare

La heatmap **è già** ECharts nativa e la scala **è già** divergente
(`#b91c1c → #f8fafc → #1d4ed8`, min −1 max +1). Una precedente proposta di «migrare a
ECharts con scala divergente» era sbagliata: entrambe le cose esistono.

### 8.2 Difetti verificati

**Il tooltip non mostra i nomi.**

```js
formatter: (params) => `${valueLabel}<br/>${observations}<br/>${coverage}`
```

Gli indici di riga e colonna sono in `value[0]` e `value[1]`, e `labels` è nello scope
della funzione. I nomi mancano perché nessuno li ha scritti nel template. Senza i due
nomi, un numero di correlazione non ha alcun significato utilizzabile.

**I nomi sono troncati due volte.**

```js
grid:  {left: 110, right: 40, top: 30, bottom: 95}   // margini fissi in px
xAxis: axisLabel: {overflow: 'truncate', width: 100}
yAxis: axisLabel: {overflow: 'truncate', width: 95}
```

Lo spazio riservato è una costante, non una misura: un nome lungo viene tagliato anche
quando lo spazio ci sarebbe. Esiste `truncateName` in `$lib/utils/text`, già usata da
`LineChart` — qui no.

**La rotazione esiste ma è neutralizzata.** `rotate: labels.length > 5 ? 35 : 0`.
Ruotare a 35° e poi tagliare a 100px si annullano a vicenda: la rotazione serve
proprio a far stare nomi lunghi, e va accompagnata dal calcolo del margine
(`larghezza · sin(angolo)`).

**La diagonale è rumore puro.** Sempre ρ = 1, quindi sempre il colore più saturo
dell'intera matrice: la riga più appariscente del grafico dice che un asset è
correlato con sé stesso.

**Il triangolo superiore è un riflesso.** La correlazione è simmetrica: metà
dell'inchiostro, zero informazione.

> Diagonale spenta + solo triangolo inferiore: su 10 asset si passa da 100 celle a
> **45**, senza perdere nulla.

**Il seed a cento asset.**

```js
selectedAssetIds = assets.filter(a => a.active !== false).slice(0, 100)
```

All'apertura la pagina seleziona fino a cento asset: una matrice 100×100 sono
**diecimila celle**, e sopra i 12 asset i numeri nelle celle spariscono
(`label.show: length <= 12`). La vista nasce illeggibile per costruzione.

Per tornare a sei asset servono **novantaquattro click** sulla X: non esiste
«deseleziona tutto» né «inverti». L'unico strumento di massa è il filtro broker,
proprio quello semanticamente ambiguo (§ regola dei pesi, D3).

Non è che scegliere sia difficile: **il sistema sceglie male al posto dell'utente e non
gli dà modo di disfare.**

> **E costa anche in prestazioni.** Misurato in
> [`06`](./06-matematica-librerie-e-reimplementazioni.md) §4: la matrice di
> correlazione è O(N²·T) in Python puro. Su dieci asset costa 37 ms, su cento
> **3 682 ms** — contro 0,2 ms della versione NumPy. Il default della pagina è il
> caso peggiore della curva.
>
> L'event loop non si blocca (`risk/base.py:242` usa `asyncio.to_thread`), ma il
> Python puro trattiene la GIL dove NumPy la rilascia: sono quasi quattro secondi in
> cui ogni altra richiesta del processo rallenta, senza una richiesta colpevole
> evidente.
>
> D19 e D26 correggono lo stesso difetto dai due lati: meno asset selezionati di
> default, e una matrice che non costa comunque quattro ordini di grandezza in più
> del necessario.

### 8.3 Interventi

**Tooltip:**

```
┌──────────────────────────────────────────┐
│  NVIDIA Corp.   ×   Bitcoin              │
│                                          │
│  ρ = +0,62        correlazione alta      │
│  ▸ si muovono quasi sempre insieme       │
│                                          │
│  748 osservazioni · copertura 98,3%      │
└──────────────────────────────────────────┘
```

Con banda qualitativa, perché `0,62` non dice nulla a chi comincia:

| \|ρ\| | Banda | Frase |
|---|---|---|
| > 0,7 | alta | si muovono quasi sempre insieme |
| 0,3 – 0,7 | moderata | si muovono spesso nella stessa direzione |
| < 0,3 | bassa | si muovono in modo largamente indipendente |
| negativa | inversa | tendono a compensarsi |

**Etichette**: margine calcolato dalla lunghezza reale al netto della rotazione,
rotazione a 45°, `truncateName` con soglia generosa, nome completo sempre nel tooltip.

**Celle**: diagonale spenta, solo triangolo inferiore.

**Riordino per similarità**: clustering su `1−|ρ|`, così i blocchi di asset che si
muovono insieme diventano quadrati adiacenti. Si *vede* la mancata diversificazione
invece di doverla cercare cella per cella. Solo frontend, dati già presenti.

**Filtri e azioni di massa:**

```
Tipo    [ETF ✓] [Azioni ✓] [Crypto] [Bond] [Obbl.]
Settore [ Tech ▾ ]   Area [ ▾ ]   Valuta [ ▾ ]
                                                    12 asset selezionati
[ Tutti ]  [ Nessuno ]  [ Inverti ]  [ ↺ I miei ]
```

`asset_type` è già su `AssetOption`; `sectorStore` e `countryStore` esistono e sono già
popolati. Si seleziona per **criterio**, non per elenco.

**Selezione iniziale (D19)**: ultima selezione dell'utente da `localStorage`, con
fallback agli asset posseduti. La pagina deve aprirsi su qualcosa di leggibile.

**Oltre ~20 asset, cambiare domanda.** Nessuno legge 400 celle, ma la domanda dietro
resta valida e ha una risposta migliore in forma di lista:

```
Coppie più correlate                          ρ
  MSCI World  ×  S&P 500                   +0,97   ⚠ quasi identici
  VWCE        ×  MSCI World                +0,94   ⚠
  Oro         ×  Bitcoin                   +0,11
Coppie che si compensano
  Oro         ×  S&P 500                   −0,23
```

Le coppie quasi-identiche sono **il** risultato che si cerca: due prodotti pagati per
una sola esposizione. La matrice lo nasconde, la lista lo dichiara.

---

## 9. Layout per zona

### 9.1 Dashboard e Broker Detail — stessa grammatica (D10)

```
┌─ RISCHIO ───────────────────────────── periodo [3A ▾] ────┐
│                                                            │
│ ① QUANTO PUÒ FARE MALE?                                    │
│ ┌──────────────────────┬───────────────────────────────┐   │
│ │ Sotto del            │      underwater chart          │   │
│ │  −4,2%               │                                │   │
│ │  −5.240 €            │                                │   │
│ │ dal picco 12 mar     │                                │   │
│ │ (38 giorni)          │                                │   │
│ └──────────────────────┴───────────────────────────────┘   │
│ Peggio: −18,7% · 6 mar → 14 ott 2022 · recuperato 112 gg    │
│ Per tornare al picco serve +4,4%                            │
│                                                             │
│ Giornata brutta (1 su 20)   −2.100 €   −1,7%   VaR 95% ⓘ   │
│ Se va peggio, in media      −3.400 €   −2,7%   CVaR 95% ⓘ  │
│ [ istogramma della distribuzione ]                          │
│                                                             │
│ ② SONO DIVERSIFICATO COME CREDO?                            │
│ «NVDA pesa l'8% ma produce il 23% del rischio»              │
│ [ barre appaiate peso/contributo ]   [ heatmap ]            │
│                                                             │
│ ③ STO VENENDO PAGATO PER QUESTO RISCHIO?                    │
│ vol 14,2% · Sortino 0,91 · Sharpe 0,74 · β 1,08             │
│ [ scatter rischio-rendimento ]                              │
│                                                             │
│ ▸ ④ COSA SUCCEDE SE…?            (chiuso · qui vive il beta)│
└─────────────────────────────────────────────────────────────┘
```

Tre regole implicite nel disegno:

1. **Un blocco = un livello, non un analytic.** L'output di `historical_kpi` viene
   *spezzato*: `max_drawdown` sale a L1, `sharpe`/`sortino`/`volatility` scendono a L3.
   Il backend non cambia: cambia chi aggrega. L'analytic è un'unità di **offerta**, il
   livello un'unità di **domanda**; oggi la UI è organizzata per offerta, ed è questa
   l'origine della piattezza.
2. **Peso visivo proporzionale al livello.** L1+L2 sempre aperti, L3 aperto, L4 chiuso
   dietro un'azione esplicita.
3. **La frase precede il grafico.** In ② il titolo è generato dai dati e il grafico lo
   *dimostra*. Oggi c'è solo il grafico e la domanda resta implicita.

Broker Detail è identico con scope ristretto: se la grammatica è la stessa, si impara
una volta sola.

### 9.2 Asset Global — è una pagina di tabelle

Conclusione strutturale: **senza pesi non esiste un «il mio rischio» da mettere in
cima.** Esistono N asset confrontabili, cioè colonne; e la correlazione, cioè una
matrice.

```
[ Miei ] [ Di altri ] [ Osservati ]      ← 3 pannelli già a baseline
┌──────┬────────┬──────┬────────┬────────┐
│ Nome │ Prezzo │ Vol  │ MaxDD  │ Corr.  │  ← colonne rischio, opzionali
└──────┴────────┴──────┴────────┴────────┘
     ordinabili · unità dichiarate in intestazione

tab [Correlazione] → matrice + filtri + lista coppie (§8)
```

Obbligo: il filtro broker qui deve dichiararsi come filtro **d'insieme**, non di
portafoglio. Oggi la stessa parola significa due cose opposte su due pagine e nulla lo
segnala.

---

## 10. Riepilogo dei costi

| Intervento | Backend | Frontend | Note |
|---|---|---|---|
| Barre appaiate peso/contributo | — | basso | dati già nel payload |
| Tornado scenari | — | basso | dati già nel payload |
| Heatmap: tooltip, etichette, diagonale, triangolo | — | basso | correzioni locali |
| Heatmap: filtri, azioni di massa, `localStorage` | — | medio | usa store esistenti |
| Heatmap: riordino per similarità | — | medio | clustering su matrice piccola |
| Lista coppie oltre ~20 asset | — | basso | stessa sorgente |
| Cono simulazione | — | basso | `buildBandSeries` esistente |
| Underwater chart | **trascurabile** | medio | la serie è già in una variabile locale di `drawdown_episodes()` |
| Istogramma distribuzione | **basso** | medio | bin via Freedman-Diaconis, bordo forzato sul quantile |
| Scatter rischio-rendimento | **medio-alto** | medio | serve vol+rendimento per asset |
| Promozione primitive in `ui/` | — | basso | spostamento + import |
| Card metrica del rischio | — | medio | nuova, sopra le primitive promosse |

Osservazione: la maggior parte del valore è a costo basso e **senza** lavoro backend,
perché sfrutta dati già prodotti e scartati (§6).

---

## 11. Fuori portata

- Asset Detail, parcheggiato in beta (D8).
- `SignalDomain.PORTFOLIO` (D18).
- Tracking error, information ratio, ottimizzazione di portafoglio, Monte Carlo
  livelli 4-5 — tutti in `TODO_FUTURI.md`.
- L'ordine di esecuzione e i gate: sono materia del piano esecutivo, non di questo
  documento.
