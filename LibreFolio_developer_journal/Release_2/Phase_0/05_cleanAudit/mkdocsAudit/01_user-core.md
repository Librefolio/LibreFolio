# 01 — Manuale utente: core (Getting Started, Dashboard, Assets, Files, Settings, Misc)

> **Release 2 · Phase 0 · 05_cleanAudit · mkdocsAudit**
>
> Sola verifica. Nessuna correzione di codice, documentazione o dati di test fa
> parte di questo report. Baseline condivisa con [00_INDEX](00_INDEX.md):
> commit `09cbb7e28f4e4e4bba9f9d40748b98e1876f5103`, branch `dev_release2`,
> worktree dirty (elenco in `00_INDEX.md`), acquisita `2026-08-05T10:54:55+02:00`.

## Ambito di questo report

28 pagine EN pubblicate, esattamente:

- `user/index.en.md`, `user/getting-started.en.md`, `user/installation.en.md`,
  `user/pwa.en.md` (4)
- `user/dashboard/**/*.en.md` (4: `index`, `charts`, `kpi-cards`, `positions`)
- `user/assets/**/*.en.md` (15: `index`, `create-edit`, `detail/{index,chart,
  classification,data-editor,events,measures,signals}`,
  `providers/{index,borsa-italiana,css-scraper,justetf,scheduled-investment,
  yahoo-finance}`)
- `user/files/index.en.md` (1)
- `user/settings/**/*.en.md` (3: `index`, `about`, `preferences`)
- `user/misc/image-crop.en.md` (1)

Esclusi esplicitamente da questo report (di competenza di altri report
dell'indice): `docs/developer/**`, traduzioni, AI Export, transazioni/broker/
import, FX, admin, teoria finanziaria, community, gallery. Dove una pagina in
scope contiene una sezione che rientra in uno di questi domini esclusi (es. il
box AI Export in `assets/detail/signals.en.md`, o la sezione Import Wizard in
`getting-started.en.md`), quella sezione è marcata **fuori standard di
codice** e non tracciata nel codice, ma il resto della pagina resta in scope.
Le superfici di funzionalita' beta non sono valutate come omissioni della
documentazione pubblica.

Confrontate solo le claim presentate come comportamento **implementato**
(nomi di tab/route, formule riprodotte da codice, colonne di tabella, valori
di default, vincoli). Il testo puramente descrittivo/marketing senza legame
verificabile con una feature concreta non è trattato come reperto.

## Copertura (28/28 pagine)

| # | Pagina | Esito |
|---:|---|---|
| 1 | `user/index.en.md` | Pulita — pagina indice/link, nessuna claim implementativa propria |
| 2 | `user/getting-started.en.md` | Pulita per la parte in scope (registrazione, primo utente admin, login); la sezione Import Wizard/duplicate-detection è fuori standard di codice (dominio transazioni/broker/import escluso) |
| 3 | `user/installation.en.md` | Pulita — healthcheck, porta, primo utente admin, backup verificati |
| 4 | `user/pwa.en.md` | Pulita — nessuna cache offline, pulsante Install nel menu Help verificati |
| 5 | `user/dashboard/index.en.md` | Pulita per le funzionalita' pubbliche in scope |
| 6 | `user/dashboard/charts.en.md` | Pulita — colori/etichette serie growth chart verificati 1:1 |
| 7 | `user/dashboard/kpi-cards.en.md` | 🔴 **R-02**, 🔴 **R-03** |
| 8 | `user/dashboard/positions.en.md` | 🔴 **R-04**, 🔴 **R-05** |
| 9 | `user/assets/index.en.md` | 🔴 **R-06** — Time Delta Selector |
| 10 | `user/assets/create-edit.en.md` | Pulita — flussi creazione, Smart Search Borsa Italiana verificati |
| 11 | `user/assets/detail/index.en.md` | Pulita per le funzionalita' pubbliche in scope |
| 12 | `user/assets/detail/chart.en.md` | Pulita — preset date range e toggle valuta/percentuale verificati |
| 13 | `user/assets/detail/signals.en.md` | Pulita per indicatori (EMA/MACD/RSI/Bollinger/Asset Comparison); box AI Export fuori standard di codice (dominio escluso) |
| 14 | `user/assets/detail/measures.en.md` | Pulita — nessuna claim contraddetta (tool generico, comportamento coerente con `chart.en.md`) |
| 15 | `user/assets/detail/classification.en.md` | Pulita — fonti provider (Yahoo Finance, justETF) coerenti |
| 16 | `user/assets/detail/data-editor.en.md` | 🟡 **R-08** (minore) |
| 17 | `user/assets/detail/events.en.md` | Pulita — tipi evento e formula Scheduled Investment verificati |
| 18 | `user/assets/providers/index.en.md` | Pulita — tabella comparativa provider coerente con il codice |
| 19 | `user/assets/providers/yahoo-finance.en.md` | Pulita — nessuna claim contraddetta |
| 20 | `user/assets/providers/justetf.en.md` | 🔴 **R-09** |
| 21 | `user/assets/providers/borsa-italiana.en.md` | Pulita — NAV/ISIN/codice interno verificati coerenti con le note dev collegate |
| 22 | `user/assets/providers/css-scraper.en.md` | Pulita — parametri e default verificati 1:1 |
| 23 | `user/assets/providers/scheduled-investment.en.md` | Pulita — formula di valorizzazione verificata |
| 24 | `user/files/index.en.md` | Pulita — due tab, sicurezza upload, limite dimensione verificati |
| 25 | `user/settings/index.en.md` | 🔴 **R-10** — "tre aree" non riflette i 4 tab reali |
| 26 | `user/settings/preferences.en.md` | 🔴 **R-11** — campo "Date Format" inesistente |
| 27 | `user/settings/about.en.md` | 🟡 **R-12** (minore) |
| 28 | `user/misc/image-crop.en.md` | 🟡 **R-13** (minore) — preset "Asset Icon" omesso |

**Navigazione/link**: non è stato eseguito un controllo automatico esaustivo
dei link interni delle 28 pagine in questo report (nessun reperto di tipo
Navigazione/link registrato; i link puntualmente seguiti durante la verifica
— es. `dashboard/kpi-cards.md#card-1-period-pl` da `KpiSection.svelte:242`,
`assets/detail/data-editor` da `PriceDataImportModal.svelte:47` — risolvono
correttamente).

**Candidato segnalato da `./dev.py mkdocs check-links`** (validazione
strutturale centrale, non parte di questo report ma verificato per
completezza in quanto tocca un file citato in R-12): il tool segnala link
frontend→docs rotto `` ${lang `` da
`frontend/src/lib/components/settings/tabs/AboutTab.svelte:145` ("File not
found"). Tracciata la riga (JS/Svelte, template literal annidato):

```js
return `/mkdocs/${lang === 'en' ? '' : `${lang}/`}${pathWithSlash}`;
```

(funzione `mkdocsUrl()`, righe 140-145, usata alle righe 488-492 per i link
"Installed Signals" dell'About tab). **Confermato falso positivo del
checker**, non un reperto: il parser di `check-links` (`dev.py:1010`,
`dev.py:1013-1017`) estrae con la regex `` /mkdocs/([^'"`,\s)]+) `` il testo
dopo `/mkdocs/` fino al primo spazio/virgola/apice/parentesi; poiché
l'espressione ternaria `${lang === 'en' ? ...}` contiene uno spazio interno
e un template literal annidato, il match si interrompe prematuramente su
`` ${lang `` e la successiva pulizia `` \$\{[^}]+\} `` (pensata per casi
semplici come `${prefix}user/assets`, senza spazi né annidamento) non trova
una parentesi di chiusura da rimuovere, quindi il frammento tronco viene
trattato come un percorso letterale inesistente. A runtime la funzione
risolve invece correttamente in `/mkdocs/{lang}/{docsPath}` (o
`/mkdocs/{docsPath}` per `en`), dove `docsPath` proviene dai segnali
installati (es.
`financial-theory/technical-analysis/indicators/ema/` da
`backend/app/services/signal_plugins/ema.py:79`, o
`financial-theory/technical-analysis/synthetic-benchmarks/linear/` da
`frontend/src/lib/charts/signals/LinearSignal.ts:22`) — pagine verificate
esistenti (`mkdocs_src/docs/financial-theory/technical-analysis/indicators/
ema.en.md`,
`.../synthetic-benchmarks/linear.en.md`, entrambe presenti sul filesystem).
Nessun link rotto reale per l'utente; nessuna azione richiesta su
documentazione o codice da parte di questo report (l'eventuale correzione
del parser di `check-links` per gestire template literal annidati con spazi
è una questione di tooling, fuori dall'ambito "sola verifica documentazione"
di questo audit).

---

## 🔴 Reperti

### R-02 — `dashboard/kpi-cards.en.md`: percentuale sotto Card 1 (Period P&L) — denominatore errato

- **Pagina/riga**: `user/dashboard/kpi-cards.en.md`, sezione "### The number
  below the hero".
- **Claim**: *"The percentage expresses it as a share of **yesterday's**
  Period P&L — it tells you how much today's move 'weighed' on the period
  result you're currently viewing."*
- **Controprova**: `frontend/src/lib/components/dashboard/KpiSection.svelte:
  118-122` definisce
  `pnlDeltaDayVsPrevTotalPct = (pnlDeltaDay / prevTotalPnl) * 100`, dove
  `prevTotalPnl = parseFloat(prevHistoryPoint.total_pnl.amount)` — cioè il
  **Total P&L di ieri** (guadagno/perdita cumulato da sempre), non lo
  `period_pnl` di ieri. Questa variabile è quella effettivamente renderizzata
  nella Card 1 (`data-testid="kpi-pnl-delta-day"`, righe 259-263):
  `{pnlDeltaDayVsPrevTotalPct}%`. Non esiste, nel componente, alcun calcolo
  che usi `period_pnl` di ieri come denominatore per questa percentuale.
- **Classificazione**: Contraddizione.
- **Gravità**: major · **Confidenza**: alta.
- **Impatto / direzione di correzione**: un utente che legge "% del Period
  P&L di ieri" interpreta il numero come "quanto ha pesato oggi sul risultato
  del periodo", ma il numero reale è "quanto ha pesato oggi sul Total P&L
  cumulato di ieri" — una base di confronto molto più grande, quindi la
  percentuale mostrata è tipicamente molto più piccola di quanto la
  descrizione lasci intendere. Correzione: sostituire "yesterday's Period
  P&L" con "yesterday's Total P&L" nel testo.

### R-03 — `dashboard/kpi-cards.en.md`: percentuale sotto Card 3 (Net Worth) — non è una variazione giornaliera

- **Pagina/riga**: `user/dashboard/kpi-cards.en.md`, sezione "### The number
  below Net Worth".
- **Claim**: *"The percentage in parentheses expresses the **day-over-day**
  (today vs. yesterday) change of this Total P&L, as a share of
  **yesterday's** Total P&L."*
- **Controprova**: `frontend/src/lib/components/dashboard/KpiSection.svelte:
  124-129` definisce `simpleRoiPct` da `summary.simple_roi_percent`
  (`parseFloat(summary.simple_roi_percent) * 100`), **non** da un confronto
  ieri/oggi. È la stessa metrica usata per la riga "ROI" della Card 2
  (`roiVal`, riga 196: `parseFloat(summary.simple_roi_percent) * 100`),
  renderizzata a riga 338-341
  (`data-testid="kpi-total-pnl-delta"` → `{simpleRoiPct}%`).
  Il backend conferma: `backend/app/services/portfolio_service.py:1490`
  calcola `simple_roi = calculate_simple_roi(engine_nav,
  period_net_invested)`, e `calculate_simple_roi()` in
  `backend/app/utils/financial/roi_utils.py:149-152` è
  `(current_nav - total_invested) / total_invested` — un ROI di periodo
  rispetto al capitale investito netto, non un delta giorno-su-giorno di
  Total P&L.
- **Classificazione**: Contraddizione.
- **Gravità**: major · **Confidenza**: alta (formula tracciata end-to-end
  frontend → backend → funzione di calcolo).
- **Impatto / direzione di correzione**: la pagina descrive un indicatore
  "pulse check" giornaliero che in realtà è il ROI cumulato/di periodo (la
  stessa cifra già spiegata altrove nella pagina per la Card 2). Correzione:
  riscrivere la sezione per descrivere `simple_roi_percent` come ROI del
  periodo selezionato (identico al valore della riga ROI di Card 2), non come
  variazione giorno su giorno.

### R-04 — `dashboard/positions.en.md`: colonne della vista "Performance" completamente diverse da quelle documentate

- **Pagina/riga**: `user/dashboard/positions.en.md`, sezione "#### 📈
  Performance View" (tabella con `Total Value`, `Unrealized P&L`, `ROI %`,
  `Total P&L`).
- **Claim**: la tabella elenca esattamente questi 4 metriche come contenuto
  della vista Performance/Table.
- **Controprova**: `frontend/src/lib/components/dashboard/
  ContributionTable.svelte` (usato per `semanticMode === 'performance' &&
  visualMode === 'table'` in `PositionsPanel.svelte:198-199`) definisce le
  colonne reali (righe 264-448): **Asset**, **Δ P&L vs yesterday** (285),
  **Δ P&L %** (298), **Period P&L** (311), **Annualized** (324),
  **Unrealized Δ** (337), **Realized Sales** (349), **Income** (361),
  **Costs** (373), **Broker** (385), **Start Value** (408), **End Value**
  (421), **Oldest open lot** (434), **Status** (448). Nessuna colonna si
  chiama "Total Value", "ROI %" o "Total P&L" (verificato con grep mirato,
  zero occorrenze di queste tre stringhe come header in
  `ContributionTable.svelte`).
- **Classificazione**: Contraddizione.
- **Gravità**: major · **Confidenza**: alta.
- **Impatto / direzione di correzione**: un utente che cerca le colonne
  descritte nella vista Performance non le trova; le colonne reali sono più
  numerose e usano nomi/concetti diversi (Period P&L invece di Total P&L,
  Annualized invece di ROI %, più Start/End Value, Broker, Status). Correzione:
  riscrivere la tabella con le 13 colonne reali elencate sopra (o un
  sottoinsieme rappresentativo esplicitamente marcato come non esaustivo).

### R-05 — `dashboard/positions.en.md`: colonne della vista "Holdings" più numerose di quelle documentate

- **Pagina/riga**: `user/dashboard/positions.en.md`, sezione "#### 📋
  Holdings View" (tabella con `Quantity`, `Market Price`, `Market Value`,
  `Average Price (WAC)`, `Weight`).
- **Claim**: la tabella presenta queste 5 metriche come contenuto della vista
  Holdings/Table.
- **Controprova**: `frontend/src/lib/components/dashboard/
  ExposureTable.svelte` (usato per `semanticMode === 'holdings' &&
  visualMode === 'table'`) definisce, oltre alle 5 documentate (Quantity
  riga 325, Price riga 338 = "Market Price", Value riga 299 = "Market
  Value", PMC riga 352 = "Average Price/WAC" ma con etichetta UI **"PMC"**,
  Weight riga 312), anche: **Asset** (180), **Broker** (202), **Δ P&L vs
  yesterday** (230), **Δ P&L %** (244), **Unrealized P&L** (258),
  **Unrealized P&L %** (271), **Annualized** (285), **Oldest open lot**
  (367) — 8 colonne aggiuntive non menzionate.
- **Classificazione**: Omissione.
- **Gravità**: minor · **Confidenza**: alta.
- **Impatto / direzione di correzione**: la tabella documentata non è
  sbagliata (le 5 colonne esistono davvero) ma è fortemente incompleta
  rispetto a quanto un utente vede realmente nella vista Holdings; inoltre
  l'etichetta UI per "Average Price (WAC)" è **"PMC"**, non "Average Price"
  (dettaglio minore di naming). Correzione: aggiungere le 8 colonne mancanti
  alla tabella, o esplicitare che è un sottoinsieme non esaustivo, e
  allineare il nome colonna a "PMC" oppure segnalare che l'etichetta UI
  differisce dal testo descrittivo.

### R-06 — `assets/index.en.md`: esempi del Time Delta Selector non corrispondono ai periodi reali

- **Pagina/riga**: `user/assets/index.en.md`, sezione "## 📋 Asset List",
  voce "⏱️ Time Delta Selector".
- **Claim**: *"Change the timeframe used to calculate price changes (e.g.,
  `1D`, `1W`, `1M`, `YTD`, `ALL`)."*
- **Controprova**: `frontend/src/lib/utils/assetPriceDerived.ts:104-113`
  definisce `DELTA_PERIODS = [{key:'1W',days:7}, {key:'1M',days:30},
  {key:'3M',days:91}, {key:'6M',days:182}, {key:'1Y',days:365},
  {key:'2Y',days:730}, {key:'3Y',days:1095}, {key:'5Y',days:1825}]` — usato
  direttamente in `frontend/src/routes/(app)/assets/+page.svelte:278-283`
  (`visiblePeriods = DELTA_PERIODS.filter(...)`). Non esiste alcuna chiave
  `1D`, `YTD` o `ALL` in questo selettore: i periodi reali sono `1W, 1M, 3M,
  6M, 1Y, 2Y, 3Y, 5Y`. (Da non confondere con il time-range picker generico
  della Dashboard/Asset Detail — `DateRangePicker.svelte:179-205` — che
  *quello* sì espone `YTD`/`MAX`, ma è un controllo diverso, non il "Time
  Delta Selector" della lista asset.)
- **Classificazione**: Contraddizione.
- **Gravità**: major · **Confidenza**: alta.
- **Impatto / direzione di correzione**: nessuno dei tre esempi citati come
  rappresentativi (`1D`, `YTD`, `ALL`) esiste per questo controllo specifico.
  Correzione: sostituire l'esempio con i valori reali, ad es. "e.g., `1W`,
  `1M`, `3M`, `6M`, `1Y`, up to `5Y`".

### R-08 — `assets/detail/data-editor.en.md`: formato CSV documenta solo `;`, il parser accetta anche `,`

- **Pagina/riga**: `user/assets/detail/data-editor.en.md`, sezioni "### CSV
  Import Format" (Prices ed Events) — entrambe mostrano solo esempi con `;`
  come separatore.
- **Claim**: implicita, il formato CSV è presentato come esclusivamente
  punto-e-virgola.
- **Controprova**: `frontend/src/lib/components/ui/data-editor/
  CsvEditor.svelte:145-159` (`detectSeparator()`) rileva automaticamente sia
  `;` sia `,` come separatore valido (`if (t.startsWith('date;')) return
  ';'; if (t.startsWith('date,')) return ',';` più euristica di fallback).
- **Classificazione**: Omissione.
- **Gravità**: info · **Confidenza**: alta.
- **Impatto / direzione di correzione**: nessun rischio di errore per
  l'utente (il formato documentato funziona), ma la pagina non menziona che
  la virgola è ugualmente supportata. Correzione: aggiungere una riga
  informativa opzionale ("comma-separated CSV is also auto-detected").

### R-09 — `assets/providers/justetf.en.md`: limitazione "Real-time price not available" per USD/CHF/GBP è imprecisa

- **Pagina/riga**: `user/assets/providers/justetf.en.md`, sezione "## ⚠️
  Limitations" → "!!! warning 'Current Price: EUR Only'".
- **Claim**: *"For non-EUR currencies (USD, CHF, GBP): ✅ Historical data is
  available... ❌ Real-time price is **not** available — the asset sync
  will show 'current value unavailable'."*
- **Controprova**: `backend/app/services/asset_source_providers/
  justetf.py:256-314` (`get_current_value()`). Il commento di metodo (righe
  258-264) descrive esplicitamente una strategia a due passi: "1. EUR only:
  real-time gettex quote... 2. Fallback for all currencies: the daily
  `latestQuote` from the performance-chart API (this is how USD/CHF/GBP get
  a current price, since the gettex feed only provides EUR)". Il codice
  (righe 291-303) implementa questo fallback: per valute non-EUR, se il
  primo ramo non fornisce un prezzo, il metodo chiama `load_raw_chart` e
  restituisce `FACurrentValue` con il prezzo `latestQuote` — **un prezzo
  corrente viene effettivamente restituito**, non viene sollevato
  `AssetSourceError("...not found...")` a meno che anche il fallback non
  trovi dati. L'eccezione "No current price available" (righe 302-305)
  scatta solo se **entrambi** i passi falliscono, non "sempre" per le valute
  non-EUR.
- **Classificazione**: Contraddizione.
- **Gravità**: major · **Confidenza**: alta (verificato codice del metodo
  end-to-end, incluso il commento di implementazione che descrive
  esplicitamente il comportamento contrario alla claim).
- **Impatto / direzione di correzione**: un utente che configura un asset
  justETF in USD/CHF/GBP si aspetta, secondo la pagina, che il sync di
  "current value" fallisca sempre; in realtà ottiene un valore (il close
  giornaliero via performance-chart), semplicemente non aggiornato in
  tempo reale infragiornaliero come per l'EUR. Correzione: riformulare da
  "Real-time price is not available" a qualcosa come "Real-time intraday
  price is EUR-only; for USD/CHF/GBP the current value falls back to the
  latest daily quote from the performance-chart API (not intraday
  real-time)", rimuovendo l'affermazione di indisponibilità totale.

### R-10 — `settings/index.en.md`: "tre aree principali" non riflette i 4 tab reali della pagina Settings

- **Pagina/riga**: `user/settings/index.en.md`, corpo pagina: *"Settings are
  split into three main areas: User Preferences... Global Settings...
  About."*
- **Controprova**: `frontend/src/routes/(app)/settings/+page.svelte:5-9,
  19-27, 49-56` importa e monta **quattro** componenti tab distinti:
  `ProfileTab` (id `'profile'`), `PreferencesTab` (id `'preferences'`),
  `AboutTab` (id `'about'`), `GlobalSettingsTab` (id `'admin'`, "Admin
  visible to everyone but editable only by superuser", commento riga 18).
  Il tab **Profile** è un tab di primo livello separato da Preferences, non
  una sotto-sezione di quest'ultimo. La pagina `preferences.en.md` (vedi
  copertura #26) descrive "Profile" come una sotto-sezione della stessa
  pagina "User Preferences", il che non riflette la struttura reale a 4 tab
  paritetici.
- **Classificazione**: Omissione.
- **Gravità**: major · **Confidenza**: alta.
- **Impatto / direzione di correzione**: un utente non trova un tab
  "Profile" separato cercandolo nel manuale, e può aspettarsi che le
  informazioni di profilo (nome, avatar) siano dentro "Preferences" invece
  che in un tab dedicato. Correzione: aggiornare `settings/index.en.md` a
  "four main areas" aggiungendo Profile, e in `preferences.en.md` chiarire
  che "Profile" è un tab separato (non una sezione della stessa pagina
  Preferences).

### R-11 — `settings/preferences.en.md`: campo "Date Format" non esiste nel codice

- **Pagina/riga**: `user/settings/preferences.en.md`, tabella iniziale, riga
  *"**Date Format** | DD/MM/YYYY, MM/DD/YYYY, or ISO YYYY-MM-DD"*.
- **Claim**: l'utente può configurare un formato data tra le proprie
  preferenze.
- **Controprova**: nessuna occorrenza di `date_format`/`dateFormat` in
  `frontend/src/lib/components/settings/tabs/PreferencesTab.svelte` (che
  espone solo `language`, `default_currency`, `theme` — righe 28-121),
  né in `backend/app/schemas/settings.py`, né in `backend/app/schemas/
  users.py` (grep ricorsivo su tutto `frontend/src/lib` e sui due file
  schema backend: zero risultati). Il campo descritto non esiste in nessuno
  strato dell'applicazione.
- **Classificazione**: Contraddizione (funzionalità inesistente
  documentata come disponibile).
- **Gravità**: major · **Confidenza**: alta.
- **Impatto / direzione di correzione**: un utente cerca un'impostazione
  che non esiste da nessuna parte nell'interfaccia. Correzione: rimuovere la
  riga "Date Format" dalla tabella (o implementare la feature, se prevista a
  roadmap — non verificabile da questo audit).

---

## 🟡 Reperti minori/info

### R-12 — `settings/about.en.md`: "version numbers (backend + frontend)" — esiste un solo numero di versione unificato

- **Pagina/riga**: `user/settings/about.en.md`: *"The About tab shows:
  Current LibreFolio version (backend + frontend)..."*
- **Controprova**: `frontend/src/lib/components/settings/tabs/
  AboutTab.svelte:25, 220, 293` espone un solo campo `app_version`
  (nessun `frontend_version` separato). Backend:
  `backend/app/schemas/system.py:22` (`app_version: str`) e
  `backend/app/api/v1/system.py:159` (`app_version=get_git_version()`)
  confermano un'unica versione derivata da git, coerente con il deploy
  monolitico a singola immagine Docker (backend serve il frontend come
  file statici, come da istruzioni di progetto).
- **Classificazione**: Dettaglio obsoleto.
- **Gravità**: minor · **Confidenza**: alta.
- **Impatto / direzione di correzione**: nessun rischio funzionale; la
  parentesi "(backend + frontend)" lascia intendere due numeri distinti
  quando ce n'è uno solo. Correzione: rimuovere "(backend + frontend)" o
  chiarire che è un'unica versione applicativa unificata.

### R-13 — `misc/image-crop.en.md`: preset "Asset Icon" (256×256) omesso dalla tabella dei preset

- **Pagina/riga**: `user/misc/image-crop.en.md`, sezione "## 📐 Presets"
  (tabella con solo `Avatar`, `Broker Icon`, `Custom`).
- **Controprova**: `frontend/src/lib/utils/files/imageCrop.ts:53-84`
  (`IMAGE_PRESETS`) definisce un quarto preset `'asset-icon'` (256×256px,
  1:1, PNG, quality 0.9), effettivamente usato in
  `frontend/src/lib/components/assets/AssetModal.svelte:2041`
  (`<ImagePickerWrapper ... preset="asset-icon" .../>`) per l'upload
  dell'icona personalizzata di un asset in fase di creazione/modifica.
- **Classificazione**: Omissione.
- **Gravità**: minor · **Confidenza**: alta.
- **Impatto / direzione di correzione**: un utente che carica un'icona
  personalizzata per un asset non trova quel caso d'uso nella tabella preset.
  Correzione: aggiungere una riga "Asset Icon | 256 × 256 px | 1:1 (square) |
  Custom asset icons" alla tabella.

---

## ✅ Claim verificate e correttamente implementate

Elenco delle claim più significative controllate positivamente (codice
coerente con la pagina), a beneficio di eventuale futura manutenzione:

| Claim | Pagina | Verificata in |
|---|---|---|
| Il primo utente registrato diventa automaticamente amministratore | `getting-started.en.md`, `installation.en.md` | `backend/app/api/v1/auth.py:193-217` (`is_superuser=is_first_user`) |
| Healthcheck Docker su `/api/v1/system/health`, porta `6040` | `installation.en.md` | `docker-compose.prod.yml` (endpoint citato coerente con route montata) |
| PWA: nessuna modalità offline reale (solo pagina di fallback) | `pwa.en.md` | `frontend/static/sw.js:1-27` (cache solo `offline.html`, nessun caching applicativo) |
| Pulsante "Install App" nel menu Help & Support | `pwa.en.md` | `frontend/src/lib/components/layout/HelpMenu.svelte` |
| Formula `Period P&L = NAV_end − NAV_start − Net Flows` | `kpi-cards.en.md` (Card 1 hero) | `backend/app/schemas/portfolio.py:455` (`period_pnl: ... "Period P&L = nav_end - nav_start - net_flows"`) |
| Percentuale sotto Timing Effect (Card 2) = variazione Total P&L come quota del Net Worth di ieri | `kpi-cards.en.md` (Card 2) | `KpiSection.svelte:80-84` (`pnlDeltaDayPct = pnlDeltaDay / prevNav * 100`, dove `prevNav = prevHistoryPoint.nav_value`) |
| Riga sotto Card 1 appare solo con ≥2 punti storici giornalieri | `kpi-cards.en.md` (Card 1) | `KpiSection.svelte:79-84` (`pnlDeltaDay` richiede sia `lastHistoryPoint` sia `prevHistoryPoint`) |
| Ordine blocchi FIFO Lots Analysis: WAC/Market Price → Lot Life & Custody → Unified Lots Table → Value/Return Comparison → Lot Detail Modal; pannello inline con transizione verticale (non slide-over laterale) | `dashboard/positions.en.md` | `frontend/src/lib/components/brokers/lots/LotsAnalysisPanel.svelte:400 (transition:slide), 425-503` (ordine componenti) |
| Holdings/Performance × Table/Map: 4 combinazioni via toggle persistito | `dashboard/positions.en.md` | `frontend/src/lib/components/dashboard/PositionsPanel.svelte:65-90, 190-207` |
| Colori/etichette Growth Chart: Asset Cost blu, Returns verde smeraldo, Capital grigio-verde, NAV verde scuro continuo, Deposited Capital tratteggiato grigio | `dashboard/charts.en.md` | `frontend/src/lib/components/dashboard/GrowthChart.svelte:73-77, 484-485` |
| Preset date range Dashboard/Asset Detail: 1W, 1M, 3M, 6M, 1Y, YTD, MAX(="All") | `dashboard/index.en.md`, `assets/detail/chart.en.md` | `frontend/src/lib/components/ui/date/DateRangePicker.svelte:179-187`; i18n `datePicker.presets.max = "All"` |
| Live Ticker: polling ogni 30s | `assets/index.en.md` | `frontend/src/lib/components/layout/LiveTicker.svelte:42, 166` (`pollInterval = 30_000`) |
| Scheduler prezzi correnti: default 10 minuti, configurabile in Global Settings | `assets/index.en.md` | `backend/app/services/scheduler/settings.py:93` (default `10`), chiave `scheduler_current_price_frequency_minutes` |
| Cache prezzo corrente con TTL 120s | `assets/index.en.md` | `backend/app/services/asset_source.py:136` (`ttl=120`) |
| Formula Scheduled Investment: `price(d) = initial_value + accrued_interest − Σ(INTEREST) + Σ(PRICE_ADJUSTMENT)` | `assets/detail/events.en.md`, `assets/providers/scheduled-investment.en.md` | `backend/app/services/asset_source_providers/scheduled_investment.py:500-520` |
| CSS Scraper: parametri `current_css_selector`, `currency`, `decimal_format` (`us`/`eu`), `timeout` (default 30s), `user_agent` | `assets/providers/css-scraper.en.md` | `backend/app/services/asset_source_providers/css_scraper.py:75-101, 172-176, 306-311` |
| justETF: 4 valute supportate (EUR/USD/CHF/GBP), quote gettex real-time solo in EUR | `assets/providers/justetf.en.md` | `backend/app/services/asset_source_providers/justetf.py:215-216, 281` (ma vedi R-09 per l'imprecisione sul fallback) |
| Files: 2 tab (Static/Broker Reports), visibilità diversa | `files/index.en.md` | `frontend/src/routes/(app)/files/+page.svelte:46, 60-101` (`type Tab = 'static' \| 'brim'`) |
| Limite upload di default 10MB, configurabile da admin | `files/index.en.md` | `backend/app/schemas/settings.py:99-103` (`max_file_upload_mb: "10"`) |
| Estensioni eseguibili bloccate + validazione MIME server-side | `files/index.en.md` | `backend/app/services/static_uploads.py:91-92 (BLOCKED_EXTENSIONS ⊇ ".exe"), 223, 227-266` |
| Password: minimo 8 caratteri + almeno un numero, enforcement lato form | `settings/preferences.en.md` | `frontend/src/lib/components/settings/PasswordChangeModal.svelte:35,38,42-43` (`canSubmit` richiede `passwordMeetsRules`); backend `min_length=8` in `backend/app/schemas/auth.py:44-45` |
| Preset Image Crop: Avatar 200×200, Broker Icon 64×64, rotazione a step di 15° | `misc/image-crop.en.md` | `frontend/src/lib/utils/files/imageCrop.ts:54-68`; `frontend/src/lib/components/ui/media/ImageCropper.svelte:515-519,776-779` (title `"-15°"/"+15°"`) |
| Slider qualità output JPEG/WebP: 10%–100% | `misc/image-crop.en.md` | `frontend/src/lib/components/ui/media/ImageEditModal.svelte:245-250` (`Math.min(100, ...)`, `Math.max(10, ...)`) |

---

## 🔵 Fuori standard di codice / non verificabile

- **`getting-started.en.md`**, sezione "3. Import Your First Statement":
  l'intero flusso wizard (parser, duplicate detection a 4 livelli di
  confidenza, asset mapping) appartiene al dominio transazioni/broker/import
  esplicitamente escluso da questo report; non tracciato nel codice.
- **`assets/detail/signals.en.md`**, sezione "## 🧠 AI Export": elenco delle
  5 task AI Export per asset appartiene al dominio AI Export esplicitamente
  escluso; non tracciato nel codice.
- **`assets/create-edit.en.md`**, sezione "🔎 Smart Search Details": la
  claim su comportamento del web-link-search per Borsa Italiana è coerente a
  grandi linee con `borsa_italiana.en.md`, ma il dettaglio implementativo del
  resolver non è stato tracciato riga per riga nel modulo
  `borsa_italiana.py` (fuori dal budget di questo report; nessuna
  contraddizione riscontrata nei punti effettivamente ispezionati).
- **`assets/detail/measures.en.md`**: tool generico "click due punti sul
  grafico → delta/percentuale/giorni/rendimento annualizzato"; comportamento
  plausibile e coerente con `chart.en.md`, ma il componente `MeasurePanel`
  non è stato aperto riga per riga: nessuna claim controllata puntualmente
  a livello di formula (basso rischio, nessun'anomalia notata durante la
  navigazione del codice circostante).
- **`assets/providers/borsa-italiana.en.md`**: il link "Developer
  Documentation" punta a `developer/backend/assets/provider_borsa_italiana.
  md`, esplicitamente fuori scope (developer guide sospesa).
- **PerformanceChart.svelte** (vista Performance/Map, alternativa a
  `ContributionTable`/Performance-Table coperta da R-04): non ispezionato
  colonna per colonna; la pagina descrive la vista Map con lo stesso testo
  generico della vista Table (stesse 4 metriche), quindi condivide
  potenzialmente lo stesso problema di R-04 ma non è stato verificato
  direttamente in questo passaggio — segnalato come incertezza, non come
  reperto separato per evitare doppio conteggio non verificato.

---

## Sintesi e conteggi

| Metrica | Valore |
|---|---:|
| Pagine in scope | 28/28 |
| Pagine con almeno un reperto | 8 |
| Pagine verificate pulite (incl. copertura parziale per dominio escluso) | 20 |
| Reperti totali | 11 |
| — Contraddizione | 6 (R-02, R-03, R-04, R-06, R-09, R-11) |
| — Omissione | 4 (R-05, R-08, R-10, R-13) |
| — Dettaglio obsoleto | 1 (R-12) |
| — Limite non documentato | 0 |
| — Navigazione/link | 0 |
| Gravità major | 7 (R-02, R-03, R-04, R-06, R-09, R-10, R-11) |
| Gravità minor | 3 (R-05, R-12, R-13) |
| Gravità info | 1 (R-08) |
| Claim verificate correttamente implementate (tabella dedicata) | 21 |

Pattern ricorrente: le tre contraddizioni sulle Card KPI e sulle tabelle
Positions (R-02, R-03, R-04)
condividono un'altra causa comune: la UI è stata rifattorizzata (rinominando
metriche, aggiungendo colonne, cambiando denominatori) più velocemente della
documentazione corrispondente, che è rimasta ancorata a una versione
precedente della Card/tabella.
