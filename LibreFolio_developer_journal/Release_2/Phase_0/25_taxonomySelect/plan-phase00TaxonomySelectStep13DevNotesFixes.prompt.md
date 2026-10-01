# Piano — K / step 13: difetti dagli appunti del developer (10–30/09) e XSS

> Difetti della lista di appunti del developer, assegnati a K il 30/09 (le migliorie della stessa lista sono in
> `TODO_FUTURI.md`), più una **XSS memorizzata** trovata da F con priorità massima. Analisi del 30/09, domande D1–D8 fatte
> direttamente al developer. Viene dopo lo step 12
> ([`plan-phase00TaxonomySelectStep12ReviewFollowups.prompt.md`](plan-phase00TaxonomySelectStep12ReviewFollowups.prompt.md)).
> Test rossi prima (test-author), un commit per voce, un solo checkpoint alla fine.

| | |
|---|---|
| **Baseline** | `8bd6be663` (= `dev_release2`) |
| **Lane suite** | `--test-port 6155 --data-dir /tmp/librefolio-r2-k`; `front build --debug` prima della prima suite che avvia il backend |
| **Copia di prod** | porta 6165, `/tmp/librefolio-r2-k-prodcopy`, fresca dalla snapshot `5c0a681bc4e4b59c` (schema `004`); solo verifiche e review |
| **Repo esterno** | `/Users/ea_enel/Documents/00_My/LibreFolio_subRepo/borsaItaliana-scraping` (voce 3a, autorizzata dal developer il 30/09) |
| **Condivisi** | `dev.py` (solo `generate_pwa_icons`, scrittore K), i 4 cataloghi i18n (una chiave nuova, voce 9), `Pipfile.lock` (voce 3a, aggiornato dal developer), registrazioni nel runner (in aggiunta) |

## Decisioni del developer (30/09)

- **D1 (PWA)**: gli angoli neri sono nella **schermata di avvio di Android**, prima che l'app carichi. Sfondo dell'icona
  maskable: **beige `#f5f4ef`**, lo stesso della schermata di avvio.
- **D2 (login)**: allineare **tutti e tre** i moduli: login, registrazione, cambio password.
- **D3 (Borsa Italiana)**: prima si corregge **la libreria** (K scrive il commit message, il developer committa e aggiorna
  le dipendenze; K verifica lock e pacchetto installato), **poi** il plugin. L'ETC dell'oro non è nel prod della
  snapshot: il developer lo aggiungerà dopo la cura, per la verifica.
- **D4**: la schermata del 19/09 è il piede di «Aggiungi asset» (Salva fuori schermo): stessa causa del 6a.
- **D5 (barre)**: tarare **tutte e 5** le barre, **ciascuna sulla lingua con le etichette più lunghe** (tendenzialmente il
  francese). Il sintomo del 21/09: pulsanti che uscivano dalla barra a larghezze intermedie.
- **D6 (schede)**: `LineChart` per Panoramica, `Shield` per Rischio, più la rete di sicurezza in `TabBar`.
- **D7 (segnali)**: era un segnale di rischio. **Voce 8 tolta da K**: il developer ha chiesto al coordinator di
  riassegnarla a chi possiede le guide di rischio.
- **D8 (prezzi fermi)**: regola confermata (provider + prezzo di mercato + posizione aperta + più di 7 giorni) ed effetto
  sul Rischio confermato (parziale solo mentre un asset filtrato è fermo). Azione del banner: **«Sincronizza»**, che
  aggiorna i prezzi degli asset segnalati.
- **Coordinator**: piano qui (la cartella `26_…` è di L); gate sul timbro di `sw.js` nella voce 1; docstring di
  `asset_sources/core.py` nella voce 3; frase di `data-quality.en.md` scritta da Risk (se K entra per secondo, K manda il
  diff al coordinator).

## Voci

### 0. XSS memorizzata nella tabella Asset — priorità massima
- `AssetTable.svelte:143`: la cella del nome interpola `${row.display_name}` crudo in una cella `html`; `DataTable` la rende
  con `{@html}` (`:1384-1403`). Il backend accetta qualunque stringa (`schemas/assets.py:622` creazione, `:837`
  modifica); gli asset sono globali (`models.py:599`), quindi il nome viene eseguito nel browser di chiunque apra la
  lista, admin compreso. È nella v1.1.0 rilasciata.
- Cura: `escapeHtml` (`$lib/utils/core/escapeHtml.ts`), come già fa `$lib/utils/providerHelpers.ts:82-85`.
- **Audit** di ogni template `html` e di ogni `{@html}` che porti testo scritto da un utente o da un provider (nomi di
  asset e broker, note, tag, nomi di file, testi dei file importati). Mappa di partenza (template `html` / `escapeHtml`):
  `TransactionBulkModal` 39/2, `ImportWizardModal` 33/0, `UnifiedLotsTable` 11/14, `AssetTable` 9/0, `DataEditor` 8/0,
  `FxTable` 7/0, `TransactionsTable` 6/7, tabelle della Dashboard 5/4, 5/4, 3/2, `MeasurePanel` 3/0,
  `DistributionEditor` 2/1; più ~25 `{@html}` fuori da `DataTable` e i formatter dei tooltip ECharts. Ogni punto
  classificato (utente/provider → escape; numeri, formati, i18n → sicuro) in una tabella in questo piano.
- **Gate** sul sorgente: nessun campo di testo dell'utente interpolato in un template `html` senza `escapeHtml`
  (lista dei campi, allow-list vuota).
- Nessun nome nel DB del developer contiene `<`, `>` o `&`: la resa dei suoi dati non cambia.
- Test rosso: un asset col nome `<img src=x onerror=…>` resta testo in vista tabella e card, e non esegue niente.

### 1. PWA: angoli neri sulla schermata di avvio di Android
- `manifest.json`: la maskable è lo stesso `icon-512.png` delle «any»; il logo arriva a 0,47 della larghezza dal centro
  (zona sicura 0,40); `dev.py:2089-2111` produce pixel semitrasparenti (alpha fino a 198: 12,6% dell'icona 192);
  `app.html:8` usa `icon-192.png` come icona iOS.
- Cura: icone opache (RGB); maskable 192/512 dedicate, sfondo beige `#f5f4ef` pieno, logo dentro r ≤ 0,38;
  `apple-touch-icon.png` 180×180 opaca; `manifest.json` e `app.html`; PNG rigenerate.
- **Gate del timbro**: `stamp_service_worker()` scrive in `sw.js` `md5(offline.html)[:8]`; il `d1c081102` ha cambiato
  `offline.html` senza il timbro (oggi `450af3dd` contro `3e7bd439`; lo corregge il coordinator su `dev_release2`). Il gate
  fallisce quando i due non coincidono.
- Test rosso: pytest su manifest, icone, `app.html` e timbro.

### 2. Login: Chrome non propone le credenziali sul campo utente
- `LoginCard.svelte:63-72` senza `name`/`id`; `PasswordInput.svelte` senza `name`, con `id=""`; stesso difetto, minore,
  in `RegisterCard` e `PasswordChangeModal`.
- Cura: `id`/`name` e `autocomplete` coerenti, etichette nascoste, `autocapitalize="none"`, `spellcheck="false"`;
  `PasswordInput` con `name` e `id` opzionali.
- Test rosso: test di componente (login, registrazione, cambio password). Verifica manuale sul Chrome del developer.

### 3. Borsa Italiana: la valuta dei metadati non è quella dei prezzi
- Riprodotto dal vivo: la pagina italiana ha solo «Valuta di Denominazione USD» e la libreria la legge come valuta di
  negoziazione (`scheda.py:243-270`, ripiego «Valuta» + confronto per sottostringa `:108`). I prezzi (API grafici) sono in
  EUR. Colpiti anche iShares Core MSCI World e S&P 500; non colpiti ENEL (nessuna riga) e il T-Bond USD («Valuta di
  negoziazione USD»).
- **3a, libreria** (repo esterno): `_estrai_valuta` non prende più la denominazione come negoziazione; campo separato per
  la denominazione; test con fixture HTML; versione 0.3.2. Il developer committa; aggiorna le dipendenze con
  `PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv update borsa-italiana-scraping`; K verifica `Pipfile.lock`, il
  commit installato e la riproduzione.
- **3b, plugin**: la valuta dei metadati e di `resolve_url` viene dalla stessa API dei prezzi (`_storico_con_mic_retry`);
  se l'API fallisce, `None`. Doc `provider_borsa_italiana.md:26-28` («All data is returned in EUR», falso).
- **3c, docstring** di `asset_sources/core.py:290-295`: il core salva i punti così come arrivano (nessun riempimento in
  scrittura); i buchi si riempiono solo in lettura (`asset_sources/price_query.py`, `backward_fill_info`) e nel motore
  (`price_resolver.py`).
- Test rosso (test-author, con fixture): ETC dell'oro in EUR, T-Bond in USD, API assente → `None`.

### 4 + 6a. «Salva» / «Crea» fuori schermo su mobile
- Piede di `AssetModal.svelte:2180-2250` su una riga sola senza `flex-wrap`; l'interruttore del benchmark (`00d8c735b`,
  18/09) l'ha allungato. Misurato a 390 px: modifica, Salva a 434–531 px; creazione, a 434–503 px.
- Cura: il piede va a capo (interruttori su una riga, pulsanti sotto, a destra).
- Test rosso: E2E a 390 e 360 px, creazione e modifica: `asset-modal-save` nella finestra e toccabile.

### 5. Barre in alto: soglie in ritardo di 10–30 px
- Scansione da 1500 a 320 px sui dati del developer, in italiano: Asset (fino a 14 px; filtri `w-44` sotto 370 px),
  dettaglio Asset (2 px; pagina larga a 330 px), Dashboard (fino a 11 px), dettaglio Broker (schede, 8 px), lista FX
  (fino a 25 px).
- Cura: `denseRow`/`stackFilters` ritarati **nella lingua più lunga per ogni barra** con margine; soglia propria per le
  schede del Broker; filtri a tutta larghezza in `oneColumn`. Solo le righe delle soglie (`assets/+page.svelte:1235`,
  non le righe `onfitperiod` di F).
- Test rosso: E2E che scansiona le larghezze attorno alle soglie, nella lingua più lunga: nessun discendente fuori dalla
  barra, nessuno scorrimento orizzontale.

### 6b. «Sincronizza» barrato e più piccolo durante il caricamento
- `assets/[id]/+page.svelte:474-477`: `isManualOnly = !providerAssignment` è vero finché l'assegnazione non arriva;
  `PageToolbar.svelte:241` allarga il contenitore del `Tooltip`, non il pulsante. Misurato: 107 px contro 159, barrato.
- Cura: flag «assegnazione caricata»; blocco solo ad assegnazione nota; `Tooltip` e pulsante a tutta la cella.
- Test rosso: E2E che trattiene `/assets/provider/assignments`, più un asset manuale.

### 7. Schede del dettaglio asset vuote su mobile
- `assets/[id]/+page.svelte:124-127` senza icone; sotto `labelHideTabs` 370 le etichette spariscono (misurato: 2 × 178 px
  vuoti, senza nome accessibile).
- Cura: `LineChart` e `Shield`; `TabBar` non nasconde l'etichetta di una scheda senza icona e dà `aria-label` quando la
  nasconde.
- Test rosso: E2E a 390 px e test di componente di `TabBar`.

### 9. Banner «prezzi non aggiornati» (`STALE_PRICE`) mai emesso
- `portfolio_service.py:1248-1257` non passa mai `stale_prices_dto` (dal `77b976ebc`, 19/06); il motore marca fermi anche i
  prezzi di transazione (`portfolio_engine.py:1429`).
- Cura: `StalePriceAsset` dalle posizioni di fine periodo con la regola di D8; azione **`sync_asset_prices`** («Sincronizza»,
  chiave `dataQuality.cta.sync_asset_prices` nelle 4 lingue) gestita dalla Dashboard con `sync_prices_bulk` sugli asset
  segnalati, poi ricarica.
- Misura sulla copia: 22/09 → 0 asset (senza filtro: i 2 crowdfunding); 30/09 simulato → 7 asset.
- Effetto voluto: `CARRIED_FORWARD` → risultati di portafoglio del Rischio parziali mentre un asset filtrato è fermo.
- Doc: `developer/frontend/data-quality-banner.md:94,125`, `user/dashboard/index.en.md:67`; `data-quality.en.md` a Risk.
- Test rosso: servizio (segnalato / non segnalato: manuale, fresco, chiuso, prezzo di transazione) ed E2E della Dashboard
  con «Sincronizza».

## Passi

- [x] **13.0 Piano** — ✅ 2026-09-30: questo file, con il rimando dallo step 12. Approvato dal developer il 30/09
  («approvo il piano»), che chiede anche di tenere aggiornati il piano dell'agente e i task SQL della sessione.
  > **Note implementazione**:
  > - Domande D1–D8 fatte direttamente al developer, una alla volta; decisioni nella sezione in alto.
  > - Prove dell'analisi con dati reali cancellate dopo l'approvazione e verificate con `ls`: `/tmp/libreFolio_k13_probe/`,
  >   la copia `/tmp/librefolio-r2-k-prodcopy`, i log della misura. Gli script delle sonde, senza dati, restano nei file di
  >   sessione.
  >
  > **Fuori pista**: la voce 8 è tolta su decisione del developer (riassegnazione via coordinator); la XSS (voce 0), il
  > gate del timbro di `sw.js` (voce 1) e la docstring di `asset_sources/core.py` (voce 3c) sono entrate durante l'analisi.
- [x] **13.1 Voce 0 — XSS**: test rosso, cura in `AssetTable`, audit con tabella, gate. ✅ 2026-09-30.
  > **Avanzamento (30/09)** — rossi validi (rifatti dopo le due finestre del venv, dalle 12:25:55):
  > - E2E nuova `e2e/assets/asset-name-xss.spec.ts` (azione `front-asset asset-name-xss`): AX-001 vista tabella **rossa**
  >   (6/6 controlli: `img[src="x"]` nella riga del nome e in quella dell'icona, 2 `onerror`, `window.__k13Xss = 1` e
  >   `window.__k13XssIcon = 1`: anche l'`icon_url` esce dall'attributo `src`); AX-002 vista card verde (controllo).
  > - Gate `src/htmlInterpolation.gate.test.ts` (core-unit): 12/13 controlli del parser verdi, la regola **rossa con 33
  >   violazioni** (AssetTable, signalLabel, AllocationPieChart, MeasurePanel, PriceChartFull, ScatterChart,
  >   Contribution/ExposureTable, GrowthChart, KpiSection, TransactionsTable, ImportWizardModal, TransactionBulkModal,
  >   providerHelpers, resolveValidationMessage).
  > - Buchi che il gate non vedeva, segnalati dal test-author: gli `esc` locali di `ImportWizardModal` (4 varianti, alcune
  >   senza `"`) usati dentro `title="…"`; i toast (`{@html toast.message}`).
  > - Estensione chiesta prima della cura (rossa): solo `escapeHtml` accettato; contesto HTML anche con variabili
  >   `*Html`/`*Icon`; gate sui `{@html}` (sanificati o in una lista rivista con motivo); test di `sanitizeHtml`, dei toast,
  >   del `Tooltip` e di `resolveValidationMessage`.
  >
  > **Cura (30/09)** — regola: si escapa **alla fonte** con `escapeHtml` (`& < > " '`) il dato che entra in una stringa
  > HTML. `sanitizeHtml` (nuovo `utils/core/sanitizeHtml.ts`, DOMPurify già dipendenza) si usa solo sui pochi sink che
  > ricevono markup misto: toast, `Tooltip`, messaggi di validazione, banner dei risultati, testo della richiesta di
  > identificativo del wizard. Convenzione di nome, pretesa dal gate 1: una variabile che contiene HTML finisce in
  > `Html`/`Badge`, una che contiene un URL in `Url`/`Src`.
  >
  > | area | siti | cura |
  > |---|---|---|
  > | Tabella asset (il caso segnalato) | `AssetTable`: nome, icona (`src`), valuta | `escapeHtml` |
  > | Celle HTML delle tabelle | `TransactionsTable` (nome, icona, stile dei tag), `ContributionTable`, `ExposureTable`, `UnifiedLotsTable` (`transitBadge`), `MeasurePanel`, `DataEditor` (tooltip, link doc), `ProfileTab` | `escapeHtml`; variabili rinominate `*Html`/`*Badge` |
  > | Modali transazioni | `ImportWizardModal` (4 `esc` locali tolti → `escapeHtml`, 11 chiamate; nomi, icone, file originali), `TransactionBulkModal` (asset, broker, icone, note degli eventi), `TransactionPickerModal`, `WacPreviewSection` | `escapeHtml` |
  > | Messaggi di validazione | `resolveValidationMessage`: parametri stringa, nomi broker/asset, URL delle icone, `formattedBalance`, messaggio grezzo, etichetta del campo | `escapeHtml` + i 9 sink `{@html}` di `TransactionFormModal` (4), `TransactionBulkModal` (4), `ParseDetailModal` (1) in `sanitizeHtml` |
  > | Sink a markup misto | `ToastContainer`, `Tooltip`, `TransactionResultBanner`, richiesta di identificativo del wizard | `sanitizeHtml` (e valori escapati) |
  > | Helper condivisi | `signalLabel` (icone), `entityLink` (href), `providerHelpers` (icone, nomi), `echartsTooltipHelpers` (topN/soglia), `importCompare` (`escHtml` tolto → `escapeHtml`) | `escapeHtml` |
  > | Tooltip ECharts (HTML) | `AllocationPieChart`, `CandlestickChart`, `LineChart`, `PriceChartFull`, `ScatterChart`, `ExposureTreemap`, `KpiSection` (`GrowthChart`: a I, vedi sotto) | `escapeHtml` sui nomi utente interpolati |
  >
  > **Sink `{@html}` tenuti senza `sanitizeHtml`** (lista rivista del gate 2, 16 voci, ognuna col motivo nel test):
  > `DataTable` (celle, piè, intestazioni: l'HTML lo costruiscono le definizioni di colonna, coperte dal gate 1); i
  > formattatori di valuta (5: numeri e codici ISO); `ChangelogModal` (markdown del CHANGELOG del repo, nel bundle);
  > `FilePreviewModal` (già DOMPurify); `SignalOptionContent` (sottotitolo escapato prima di KaTeX); `PriceDataImportModal`
  > (solo `$t`); `TxLinksCell`, `TxTooltipCell`, `TransactionCompareModal` (costruttori di celle coperti dal gate 1).
  >
  > **Revisione a mano dei formatter ECharts** — il gate 1 non li vede quando la stringa non contiene markup statico.
  > Regole verificate: i formatter di assi, legende e rich text disegnano su canvas (niente HTML, niente XSS); i template
  > stringa come `'{b}: {c}%'` ECharts li codifica da sé (`encodeHTML`, `TooltipView.js:566`); una **funzione**
  > formatter invece finisce in `innerHTML` così com'è. Controllati tutti i chiamanti di `buildTooltipRow` e
  > `buildTooltipHeader` (etichetta già escapata per convenzione) e ogni `params.name`/`seriesName` interpolato.
  >
  > **Fuori pista**: la seconda passata sui formatter ha trovato **due siti in più**, che il gate 1 non poteva vedere
  > (foglie `label` e `broker`, fuori lista per disegno: quasi tutte le etichette sono traduzioni):
  > - `signalLabelToHtml` escapava le icone ma non il **testo**: `title="${info.label}"` e `${displayLabel}` ricevono il
  >   nome dell'asset grezzo da `PriceChartFull`, `CandlestickChart` e `MeasurePanel`;
  > - `ExposureTreemap`: `buildTooltipHeader(meta.broker)` e `if (!meta) return params.name`, grezzi.
  >
  > Cura tolta di nuovo per un rosso onesto, poi rimessa:
  > - `src/lib/charts/__tests__/signalLabel.test.ts` (core-unit, jsdom, output letto in un `<template>` inerte): **rossi**
  >   il nome con markup (1 `<img>` con `onerror`, `title` tagliato), le virgolette (`title` = `'x'` più un attributo
  >   `onmouseover`) e il taglio su un tag (`AAAAAAAAAAAAA<b>BB`, n = 15). Verdi il controllo e il taglio su una `&`, che
  >   protegge l'ordine della cura: si tronca il testo grezzo, **poi** si escapa (al contrario uscirebbe `&a…`).
  > - `src/lib/components/dashboard/ExposureTreemap.test.ts` (component-unit): il componente vero, con echarts sostituito
  >   dal registratore di `GrowthChart.test.ts`; formatter e nodi presi dall'ultimo `setOption`. **Rossi** la tessera del
  >   broker, quella dell'asset e il nodo senza `_meta` (1 `<img>` con `onerror`, testo vuoto); verde il controllo. Il
  >   controllo legge l'intestazione stessa del tooltip: la prima versione passava anche sul codice vulnerabile, perché il
  >   nome del broker compare, già escapato, anche nella riga «Asset».
  > - Dopo la cura: 5 file, **41/41 verdi** (A, B, `importCompare`, i due gate). Il `describe('escHtml')` obsoleto di
  >   `importCompare.test.ts` è tolto (attribuzione test-triage: helper tolto; la regola «virgolette intatte» è proprio
  >   quella eliminata), 9/9. svelte-check torna ai 3 errori della baseline, nessun warning sui file toccati.
  >
  > Anche un errore di tipo mio
  > (`PriceChartFull:783`, `originalCurrency` opzionale) e l'indentazione del blocco del wizard (Prettier) sono corretti.
  > Le valute sono validate ISO dal backend (`Currency.validate_code`): lì l'escape è solo difesa in profondità.
  >
  > **Rossi preesistenti, non miei**: `chartCoreHelpers.test.ts`, blocco «GrowthChart P&L mode (G1a/G1b/G1c)», 8 test.
  > Cercano nel sorgente stringhe assenti già su HEAD `8bd6be663` (`pnlCandlesHypotheticalShort`,
  > `computeZoomWindowRange`, `const points = entry.pnl.total.points;`); il test non è modificato nel worktree.
  > svelte-check: restano solo i 3 errori della baseline (`TransactionFormModal.test.ts` ×2, `ToolExecutionMetrics`)
  > più quello del test obsoleto di `escHtml`, che il test-author toglie. knip: nessun rilievo sui file toccati.
  >
  > **Regressioni in corsia (30/09, 13:20-13:55, 6155)** — `front build --debug`, poi 23 comandi uno alla volta; log in
  > `/tmp/libreFolio_k13_lane_<n>.log`:
  > - `asset-name-xss` **2/2 verde** (anche AX-001, la vista tabella); core-unit 2682/2682, component-unit 2128/2128
  >   (gate, `signalLabel`, `ExposureTreemap`, `Tooltip`, `sanitizeHtml`, `ToastContainer`), tx-unit 375/375;
  > - E2E verdi: asset-list 28, asset-data-editor 23, transactions-table 25, transactions-modals 19, tx-bulk-operations 10,
  >   tx-bulk-diagnostics 2, tx-import-flow 10, tx-import-resolution 12, tx-wac 7, tx-tooltips 2, fx-list 12, tooltip 9,
  >   settings 45; check-orphans pulito (89 spec, 267 file unit raggiungibili da `all`);
  > - nessun doppio escape: nessuna istantanea di fallimento contiene `&amp;`, `&#39;`, `&lt;` o `&quot;`.
  >
  > **Rossi preesistenti** (22, tutti uguali su HEAD, fuori dal diff; segnalati al coordinator per i proprietari):
  > `chartCoreHelpers.test.ts` 12 (deriva tra test e `GrowthChart`: cercano `computeZoomWindowRange`,
  > `selectZoomWindow`, `pnlCandlesHypotheticalShort`…); dashboard 4 (pulsanti `growth-zoom-window-*` assenti) e 3
  > (puntatore al 55% fisso, la data si sposta col calendario); `brokers-detail.spec.ts:710` (idem);
  > `asset-detail.spec.ts:486` (eventi della fixture fissati al 2026-08-01/03, scaduto il 17/09). ruff/black su
  > `_frontend_asset.py`: 22 rilievi e formattazione, identici su HEAD, nessuno sulle righe nostre.
  >
  > **Fuori pista — altri due siti** che il gate 1 non poteva vedere:
  > - `GrowthChart.svelte:1920` (trovato dal test-author): il tooltip P&L *line* passa il nome del broker grezzo a
  >   `pnlRow(label, …)`, che lo mette in `<span>${label}</span>`; il ramo *candles* era già curato;
  > - `DataEditor.svelte`: quattro celle `html` rendono `r.values[col.key]` grezzo (`:236` stringa in sola lettura,
  >   `:280` ripiego dell'enum, `:305` valuta in sola lettura, `:332` ramo non modificabile, cioè ogni colonna quando
  >   l'editor è in sola lettura). Esposizione reale: le note degli eventi asset (`AssetDataEditorSection.svelte:99`),
  >   in sola lettura sugli eventi automatici (`is_auto`); gli asset sono globali.
  > - Test rossi chiesti al test-author (tooltip di `GrowthChart`, `DataEditor.test.ts`) e una regola nuova del gate 1:
  >   un accesso calcolato (`x[…]`) in contesto HTML va escapato, salvo i formati numerici (`.toFixed`,
  >   `toLocaleString`). Oggi colpisce solo i 3 siti su una riga del `DataEditor`.
  > - **Decisione del coordinator (30/09, 14:02): `GrowthChart` esce dal perimetro di K.** I ha già riscritto quelle
  >   righe nel suo ramo: la cura e il suo test rosso li fa I, in un commit a sé. Tolte quindi anche le mie modifiche
  >   precedenti (import, `:1943` candles, `:1987` vista percentuale): il file è di nuovo identico a HEAD, e il mio
  >   diff è in `/tmp/libreFolio_k13_growthchart_k_diff.patch` per I. Siti consegnati: `:1915`/`:1919` (`pnlRow`),
  >   `:1943` (candles), `:1987` (`buildTooltipRow(p.seriesName, …)`: in vista percentuale i nomi di serie vengono da
  >   `name: s.name`, `:1445`, cioè anche dai broker). Non è nella v1.1.0: è entrato con `8ed7a0f0d` (18/09).
  >   Conseguenza: sul mio ramo il gate 1 segnala `GrowthChart.svelte:1943` finché la cura di I non c'è; chiesta al
  >   coordinator la scelta (fast-forward su `dev_release2` prima dei gate finali, oppure un'esclusione temporanea).
  >   `DataEditor` resta mio.
  > - **Decisione corretta dal coordinator (30/09, ~14:15): la cura di `GrowthChart` torna nella voce 0, a K;
  >   allow-list vuota.** Motivo: con un'esclusione temporanea, se I integrasse senza cura il gate resterebbe verde e la
  >   XSS andrebbe in release; aspettare I invece bloccherebbe la voce 0, che corregge una XSS già rilasciata. Con la
  >   cura di K il gate blocca ogni interpolazione grezza, anche nella versione di I, che risolve il conflitto al suo
  >   prossimo aggiornamento di base. Tre siti, con test rosso sulle tre modalità del tooltip P&L (linea, candele,
  >   percentuale): `:1919` `pnlRow(broker.brokerName, …)` (il `label` di `pnlRow` è HTML per contratto, perché riceve
  >   anche `<b>${pnlLabels.total}</b>`, quindi l'escape va nella chiamata), `:1943` candele, `:1987`
  >   `buildTooltipRow(p.seriesName, …)`. `ohlcRow` e `signedRow` ricevono solo etichette i18n. Rinforzo facoltativo del
  >   gate: `.brokerName`/`.seriesName` come primo argomento di `pnlRow`/`buildTooltipRow` sono violazioni. Il file per I
  >   non serve più.
  > - **Rossi e cure del seguito (30/09, dopo il fast-forward su `b1835949e`)**:
  >   - `GrowthChart.tooltip.test.ts` (nuovo, registrato in component-unit): **3 rossi**, uno per modalità. Linea
  >     `["Total P&L","","Rossi & Figli"]`, candele `[…,"Low","","Rossi & Figli"]`, percentuale `[…,"ROI",""]`: il nome
  >     ostile diventa un `<img>` con `onerror`. Controlli verdi: `Rossi & Figli` resta `&` (niente doppio escape) e la
  >     riga totale resta in grassetto. Nota del test-author: in vista percentuale oggi nessun nome dell'utente arriva
  >     davvero (le serie sono le tre `pctSeries` tradotte e il cambio di vista sostituisce l'intera lista), quindi lì la
  >     cura è difesa in profondità; linea e candele sono percorsi reali con 2+ broker.
  >   - `DataEditor.test.ts` (esteso): **4 rossi** (a)-(d), cioè stringa in sola lettura, enum senza opzione, valuta in
  >     sola lettura, editor in sola lettura. Controlli verdi: `Paid & reinvested`, `💰 Dividend`, il badge 🔒 resta un
  >     elemento.
  >   - Gate 1 esteso: accessi calcolati (`x[…]`) in contesto HTML, esenti i formati numerici (`toFixed`,
  >     `toLocaleString`); primo argomento di `buildTooltipRow`/`buildTooltipHeader`/`pnlRow`, con le raccolte di
  >     etichette `labels.*`/`…Labels.*` ammesse. Rosso esattamente sui 6 siti (3 `GrowthChart`, 3 `DataEditor`);
  >     `LineChart:768` resta verde per l'esenzione (senza `toFixed` lo trova). Punto cieco dichiarato nel file: il
  >     ripiego dell'enum a `:280`, che passa per la variabile `label` (lo copre il test (b)).
  >   - **Cure**: `GrowthChart` (import, `pnlRow(escapeHtml(broker.brokerName), …)`, candele, percentuale con
  >     `escapeHtml(String(p.seriesName ?? ''))`), `DataEditor` (`:236`, `:280`, `:305`, `:332` con `escapeHtml`).
  >     **Verde**: 5 file, 85/85 (tooltip, memo di `GrowthChart`, `DataEditor`, i due gate); Prettier pulito.
  > - **Evidenza finale in corsia (30/09, dopo tutte le voci)**: core-unit **2684/2684** (gate estesi, `signalLabel`),
  >   component-unit 2182/2182 (con `GrowthChart.tooltip`, `DataEditor`, `ExposureTreemap`), E2E `asset-name-xss` 2/2 e
  >   `asset-data-editor` 23/23; `dashboard` con i soli 7 rossi noti; check-orphans pulito; `git diff --check` pulito.
- [x] **13.2 Voce 3a — libreria**: test con fixture, cura, versione 0.3.2, commit message; il developer committa e
  aggiorna le dipendenze; verifica di lock, pacchetto installato e riproduzione. ✅ 2026-09-30.
  > **Avanzamento (30/09)** — cura pronta nel clone della libreria, in attesa del commit del developer:
  > - **Rosso prima**: `test/test_scheda_valuta.py` nuovo, 10 test offline con le righe HTML reali (catturate dal sito il
  >   30/09: «Valuta di Denominazione» / «Currency Denomination» sull'ETC, «Valuta di negoziazione» / «Trading currency»
  >   sul T-Bond). Sulla libreria originale: errore di import (funzione nuova assente) e, sul comportamento, la riga
  >   italiana di denominazione dava `('USD', None)`.
  > - **Cura**: `_trova_valore(…, esatta=False)`; `_estrai_valuta` senza il ripiego «Valuta» per sottostringa (ora
  >   «Valuta»/«Currency» solo se coincidono con la cella); `_estrai_valuta_denominazione` e il campo
  >   `SchedaStrumento.valuta_denominazione`; versione 0.3.2 (`pyproject.toml`, `__init__.__version__`); test di
  >   integrazione sull'ETC dell'oro (it/en) in `test_scheda.py`.
  > - **Verde**: offline 10/10; suite intera della libreria (rete compresa) **58/58**. ruff: nessun errore nuovo (gli 8
  >   sono preesistenti); black: pulito il file nuovo (`tipi.py` era già non formattato su HEAD).
  > - Commit message: `/tmp/libreFolio_commits/k-21-lib-valuta-denominazione.txt` (stile del repo della libreria).
  > - Protocollo del lock (coordinator): commit e push del developer su `main` → il coordinator ferma le corsie Python →
  >   il developer lancia nel worktree di K `PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv update
  >   borsa-italiana-scraping` → K verifica che `Pipfile.lock` cambi solo il `ref` e che il venv abbia quel commit.
  >
  > **Chiusura (30/09)**:
  > - Il developer ha committato e pushato su `main` della libreria: `95d6a59d1b91c8b8dd360562cf4dbe00658fe0bc` (i 6 file
  >   della cura, con un suo messaggio).
  > - Protocollo del venv condiviso: pausa di tutte le corsie data dal coordinator (opzione 2: la corsia di K non era
  >   garantita ferma perché il test-author era a metà turno; ogni suo risultato Python nella finestra si scarta e si rifà).
  >   Il developer ha lanciato l'aggiornamento nel worktree di K; **finestra 11:57:21–12:03:22**.
  > - Verifiche: `git diff Pipfile.lock` = una riga, il `ref` `b3a8058…` → `95d6a59…`; nel venv versione 0.3.2 e
  >   `direct_url.json` `commit_id` `95d6a59…`; riproduzione dal vivo: ETC oro, MSCI World e S&P 500 → EUR in italiano e in
  >   inglese, T-Bond → USD, ENEL → EUR.
  > - Il lock va in un commit a sé del checkpoint.
  >
  > **Fuori pista**: la sonda della riproduzione spiava `_trova_valore` con la firma vecchia e ha dato `TypeError` alla
  > prima corsa dopo l'aggiornamento; corretta la spia (accetta `esatta`), non il prodotto.
  >
  > **Secondo aggiornamento (30/09, 12:13–12:23)**: il developer non ha voluto la modifica del lock fatta a mano e l'ha
  > rifatta con `git restore Pipfile.lock` e `PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv update
  > "borsa-italiana-scraping@ git+https://github.com/Librefolio/borsaItaliana-scraping.git@main"` nel worktree di K
  > (finito alle 12:18:52; RESUME del coordinator alle 12:23). Verifiche di K:
  > - `Pipfile`: 1 riga, solo l'ordine delle chiavi `{ref = "main", git = …}`;
  > - `Pipfile.lock`: 14 righe — `ref` di borsa `b3a8058…` → `95d6a59…`; `idna` 3.19 → 3.20 solo in `default` (in
  >   `develop` resta 3.19); `soupsieve` 2.9.2 → 2.10; `_meta.hash` invariato (`e77e697e10bd`);
  > - venv: borsa 0.3.2 `commit_id` `95d6a59…`, `idna` 3.20, `soupsieve` 2.10, import di `requests`/`httpx`/`bs4`/`idna` ok;
  > - riproduzione dal vivo di nuovo verde (ETC ed ETF → EUR, T-Bond → USD, ENEL → EUR).
  > - Nel checkpoint `Pipfile` e `Pipfile.lock` vanno insieme, in un commit a sé.
  > - I risultati Python del test-author nelle due finestre (11:57–12:03 e 12:13–12:23) si scartano e si rifanno.
- [x] **13.3 Voce 3b/3c — plugin e docstring**. ✅ 2026-09-30.
  > **Avanzamento (30/09)** — cura applicata e verde; doc del provider riallineata (docs-writer).
  > - **Rosso prima** (test-author, `test_borsa_italiana_errors.py`, sezione «Metadata currency = price-API currency»):
  >   6 funzioni, 10 casi, rossi per la ragione giusta sul codice di HEAD. ETC dell'oro `'USD' == 'EUR'`; T-Bond sul `mic`
  >   memorizzato `'EUR' == 'USD'` (con il registro delle chiamate `[(isin, None), (isin, "ETLX")]`, lo stesso ripiego del
  >   prezzo); API che fallisce → `None` (`DatiNonDisponibili`, `StrumentoNonRisolto`, `RuntimeError`: un errore di
  >   instradamento nella ricerca della valuta non deve diventare `UNSUPPORTED_PAGE`); risposta senza valuta → `"EUR"` come
  >   lo storico, e uguale alla valuta dello storico; `resolve_url` → righe in EUR con **una** chiamata all'API per
  >   risoluzione; `resolve_url` con l'API che fallisce → righe con `None`, restituite lo stesso.
  > - Aggiornate le attese obsolete (valuta presa dalla scheda) di 3 test dello stesso file e di 2 di
  >   `test_borsa_italiana_funds.py` (`test_resolve_url_bond_scheda_page`, `…_eurotlx_scheda_page`): ognuno ha ora il suo
  >   doppio dell'API dei grafici. Il test-author ha provato l'insieme con un simulatore della cura, poi cancellato.
  > - **Cura** (`asset_source_providers/borsa_italiana.py`): nuovo `_price_api_currency(identifier, mic)` =
  >   `_storico_con_mic_retry(identifier, "1M", mic).valuta or "EUR"`, `None` su qualunque errore; usato da
  >   `fetch_asset_metadata` e da `_scheda_search_items_all_langs` (una chiamata per tutte le righe). Fondi, ricerca e
  >   prezzi invariati.
  > - **3c**: in `asset_sources/core.py` la docstring dei passi 4-5 diceva che il core riempie i buchi e salva i punti
  >   riempiti: falso. Il core salva i punti così come arrivano; i buchi si riempiono solo in lettura
  >   (`price_query.py`, `backward_fill_info`) e nel motore (`price_resolver.py`, ultima osservazione portata avanti).
  > - Evidenza: i tre file Borsa **77/77** con pytest diretto (puri: nessun DB, nessun server, cartella dati usa e getta mai
  >   creata); ruff e black puliti su plugin, `core.py` e test.
  > - **Dal vivo** (libreria 0.3.2, sola lettura, 30/09): metadati/storico ETC dell'oro EUR/EUR, MSCI World EUR/EUR,
  >   ENEL EUR/EUR, T-Bond USD/USD; `resolve_url` sulla pagina canonica dell'ETC
  >   (`…/etc-etn/scheda/IE00B579F325-ETFP.html`) → righe IT/EN in EUR.
  >
  > **Fuori pista**:
  > - **Valuta sconosciuta ≠ «svuotala».** `FAAssetPatchItem` applica ogni campo presente, anche `None`, e il refresh
  >   dei metadati costruisce la patch con `exclude_unset=True` (`metadata.py:158`). Un `currency=None` esplicito
  >   avrebbe quindi provato a svuotare la valuta di un asset esistente quando l'API non risponde. La cura lascia il
  >   campo **non impostato**; un'asserzione rossa-prima lo fissa: rossa su HEAD e rossa anche sul simulatore che
  >   metteva `None`.
  > - La stessa affermazione falsa sul riempimento stava in altri tre punti di `core.py` (docstring del modulo, delle
  >   responsabilità e di `get_history_value`): corretti tutti insieme.
  > - La prima prova dal vivo di `resolve_url` dava `None`: l'URL l'avevo scritto io (`/borsa/etf/scheda/…`), e non esiste.
  >   Sulla pagina canonica funziona. Non è una regressione.
  > - Effetto sugli asset **già creati** con la valuta di denominazione (prezzi EUR salvati come USD): il refresh dei
  >   metadati ora propone EUR e la guardia esistente (`CURRENCY_CHANGE_BLOCKED_BY_MARKET_DATA`) lo blocca, perché ci sono
  >   prezzi. Si corregge a mano. **Misurato sulla copia di prod (30/09)**: il developer ha un solo asset Borsa Italiana,
  >   il BTP Più (id 8), EUR sia salvata sia dall'API dei prezzi. Nessun suo asset è colpito.
  >
  > **Doc** (docs-writer, solo EN: la pagina developer non ha traduzioni): `provider_borsa_italiana.md`, sezione
  > «💱 Currency» riscritta («All data is returned in EUR» era falso) con la regola «la valuta dei metadati è quella
  > dei prezzi», il caso denominazione/negoziazione, la valuta sconosciuta lasciata non impostata, ricerca e fondi
  > invariati, la nota sulla libreria 0.3.2 (vale anche per il prezzo corrente, che ripiega sullo scraping della scheda
  > quando l'API fallisce: verificato in `tempo_reale.py`). Ritoccate la riga «Currency» dei metadati e quella di
  > `resolve_url`. `mkdocs build` strict verde (24 s), `check-links` verde (i 3 ancoraggi rotti sono noti, in pagine
  > utente non toccate).
  >
  > **Fuori pista (corsia)**: la modifica al plugin è caduta mentre il giro E2E della voce 0 era in corso (passi 8-15).
  > Il server E2E carica il backend del worktree a ogni comando, ma il plugin Borsa non entra in quelle E2E (nessuna
  > rete). Da qui in poi, finché un giro E2E è in corso, **niente modifiche di prodotto**: il runner ricostruisce il
  > frontend se un file di `frontend/src/` è più recente della build (`check_frontend_needs_build`), e il backend
  > dell'E2E è quello del worktree.
  >
  > **Fuori pista (`sw.js`)**: il `mkdocs build` del docs-writer ha chiamato `copy_docs_assets()`, che rigenera le icone
  > (byte identici) e ritimbra `frontend/static/sw.js` da `450af3dd` a `3e7bd439`: lo stesso cambio del commit
  > `3d625e703 fix(pwa): restamp the service worker` del coordinator, già su `dev_release2`. Riportato a mano al
  > contenuto di HEAD (`git diff --quiet` pulito): il ritimbro è del coordinator, e un file sporco bloccherebbe il suo
  > fast-forward. Solo `mkdocs build/serve/deploy` e Docker ritimbrano, non `front build`. `dev_release2` è avanti di
  > tre commit (`3d625e703`, `0743b9f44` BRIM, `b1835949e` CHANGELOG), senza sovrapposizioni con i file dello Step 13. Il
  > gate del timbro (voce 1) sarà verde sul mio ramo solo dopo quel fast-forward, da chiedere a corsia libera.
- [x] **13.4 Voce 9 — prezzi fermi e «Sincronizza»**. ✅ 2026-09-30.
  > **Sui dati reali** (copia fresca della snapshot, `get_summary` col codice nuovo): al 22/09 e al 26/09 nessun asset
  > segnalato (stato `ok`); al **30/09**, 8 giorni dopo l'ultima sincronizzazione della snapshot, **7 asset** (6 ETF e il
  > BTP Più, ultimo prezzo 22/09), stato `carried_forward`, CTA `sync_asset_prices`: la stessa lista della simulazione
  > dell'analisi. Nessun asset manuale (crowdfunding) segnalato.
  > **Avanzamento (30/09)**:
  > - **Rosso prima** (test-author): puro `test_stale_price_cta_syncs_asset_prices` (`'navigate_asset' ==
  >   'sync_asset_prices'`); servizio con DB `TestStalePriceDataQuality` (7 casi: rossi 1, 1b e 7; verdi i controlli 2-6,
  >   ognuno dei quali verifica prima la riga della posizione, così non passa su un portafoglio vuoto); E2E
  >   `e2e/portfolio/stale-price-banner.spec.ts` (account usa e getta, `mockprov` su un identificativo che il provider
  >   rifiuta, quindi nessuna sincronizzazione rinfresca il prezzo di 10 giorni fa), rosso al controllo del report dopo
  >   seed, login e navigazione verdi. Corsia: azione `services roi-fifo-utils` filtrata, 4 rossi / 7 verdi; E2E 1
  >   rosso; registrata `front-portfolio stale-price-banner`.
  > - **Cura**:
  >   - `portfolio_service.get_summary`: `StalePriceAsset` dalle posizioni aperte di fine periodo con la regola D8
  >     (`valuation_stale`, `MARKET_PRICE`, asset con provider), una voce per asset, passata come `stale_prices_dto`;
  >   - `portfolio_engine`: la CTA di `STALE_PRICE` diventa `sync_asset_prices`;
  >   - frontend: icona nel banner, ramo nella Dashboard (`POST /assets/prices/sync`, stato occupato, un toast per
  >     risultato con il nome escapato, ricarica), chiave `dataQuality.cta.sync_asset_prices` ×4 via `dev.py i18n add`
  >     («Sync prices», «Sincronizza», «Synchroniser», «Sincronizar»).
  >   Lo schema API non cambia (`cta_action` è una stringa libera): nessun `api sync`.
  > - Test puro 38/38; ruff e black puliti su `portfolio_service.py` e `portfolio_engine.py`; Prettier pulito.
  >
  > **Fuori pista**: il corpo della sincronizzazione usa `start: 'resume'` (il giorno dopo l'ultimo prezzo salvato, la
  > regola di ogni sincronizzazione automatica, `refresh.py:159`) e come fine la data della Dashboard, invece
  > dell'intero intervallo della Dashboard come avevo scritto nella specifica del test: prende esattamente il buco del
  > prezzo fermo e funziona anche con l'intervallo «tutto». L'asserzione dell'E2E è aggiornata dal test-author.
  >
  > **Verde in corsia (30/09, 6155)**: `services roi-fifo-utils` filtrata 11/11 e intera **518/518** (con
  > `TestTransactionImpliedDataQuality` 3/3, `TestStalePriceDataQuality` 8/8); `services risk-all` **454/454**;
  > `front build --debug`; E2E `stale-price-banner` **verde**, senza residui nel DB della corsia; `banners` 15/15; `risk`
  > 14/14; `dashboard` 8 verdi + i **7 rossi già noti** (4 selettore di zoom, 3 tooltip legati al calendario: stessi
  > nomi e stessi valori nel log archiviato delle 13:49, prima della cura). `check-orphans`: due file ancora da
  > registrare del test-author dei layout mobile (voci 4-7), non della voce 9.
  > - Nei dati di prova ogni asset con provider ha prezzi fino a oggi: il `STALE_PRICE` e l'effetto «rischio parziale»
  >   li vede solo lo spec della voce 9, sul suo account.
  > - Da archiviare nella devWiki a fine sessione (test-author): la pagina `/assets` interroga i prezzi correnti e
  >   scrive il prezzo di oggi per ogni asset il cui provider risponde, quindi un E2E che vuole un prezzo fermo deve
  >   usare `mockprov` con `INVALID_TICKER_12345`; `valuation_stale` vale anche per le posizioni valutate al prezzo di
  >   una transazione, non solo di mercato.
  > - **Doc** (docs-writer): `developer/frontend/data-quality-banner.md` (azione `sync_asset_prices`, la regola in
  >   quattro condizioni con le esclusioni, come riprodurlo: senza la colonna `last_price_date`, che non esiste,
  >   con l'intercettazione della sincronizzazione nello spec; i test nuovi) e un paragrafo in
  >   `user/dashboard/index.en.md`. Build strict e check-links verdi; icone e `sw.js` intatti dopo la build (verificato
  >   byte per byte). **Debito di traduzione**: un paragrafo della pagina utente in IT/FR/ES (`translate-diff`: grassetti
  >   29 contro 27); nessuno stamp. Decisione per il developer: traduzione a mano delle tre lingue o pipeline.
  > - Imprecisioni vecchie della pagina developer, fuori perimetro, per il backlog: mancano `MISSING_FX_RATES` e
  >   `MWRR_SERIES_UNRELIABLE` fra i codici e `sync_fx_pair` fra le CTA; il modo «grouped» è descritto male; il diagramma
  >   cita `POST /portfolio/summary` invece di `/portfolio/report`; «5 codici» contro 6. Nella pagina utente «valued at
  >   purchase cost» è impreciso (il motore usa l'ultimo prezzo di transazione).
- [x] **13.5 Voce 2 — login, registrazione, cambio password**. ✅ 2026-09-30.
  > **Note implementazione**:
  > - **Rosso prima** (test-author, vitest diretto): `LoginCard.test.ts` e `PasswordInput.test.ts` nuovi, `RegisterCard.test.ts`
  >   e `PasswordChangeModal.test.ts` estesi; **27 rossi** per le ragioni giuste (`id=""`, `name` assente, nessuna
  >   `<label for>`, niente `autocapitalize`/`spellcheck`, nessun campo utente nel cambio password), 82 test esistenti
  >   verdi. Il test-author ha provato la cura su copie in `/tmp` e quattro rotture volute, ognuna presa dal suo test.
  > - **Cura**:
  >   - `PasswordInput`: prop `name`; `id`/`name` resi solo se non vuoti; `autocapitalize="none"` e `spellcheck="false"`,
  >     che contano quando l'occhio mostra la password come testo;
  >   - `LoginCard`: `login-username`/`username` e `login-password`/`password`, più etichette `sr-only` con le stesse chiavi
  >     dei placeholder;
  >   - `RegisterCard`: `name` sui quattro campi (`username`, `email`, `new-password`, `confirm-password`), `id` alle due
  >     password, etichette `sr-only`;
  >   - `PasswordChangeModal`: campo utente nascosto (`type="text"`, `hidden`, `readonly`, `autocomplete="username"`,
  >     valore `$currentUser?.username ?? ''`, che segue anche un cambio di nome) e `name` sulle tre password.
  >   I `data-testid` non cambiano.
  > - **Verde**: i 5 file (con `ProfileTab.test.ts`) **160/160**; Prettier pulito; registrati `LoginCard.test.ts` e
  >   `PasswordInput.test.ts` in component-unit (ruff/black puliti).
  > - Verifica manuale sul Chrome del developer nella lista dei dispositivi: Chrome potrebbe chiedere di salvare di nuovo
  >   le credenziali, perché la firma del modulo è cambiata.
  >
  > **Fuori pista**: la voce 2 è entrata prima della 9 perché i test della 9 avevano bisogno della corsia, occupata dal
  > giro della voce 0. Il test-author segnala, senza test, che il pulsante «occhio» di `PasswordInput` ha un `title`
  > inglese fisso e `tabindex="-1"`: fuori perimetro, nel backlog.
- [x] **13.6 Voce 1 — icone PWA e gate del timbro**. ✅ 2026-09-30.
  > **Note implementazione**:
  > - **Rosso prima** (test-author): `backend/test_scripts/test_utilities/test_pwa_assets.py`, pytest puro, 20 test, **13
  >   rossi** (icone RGBA con il 12,6 % di pixel traslucidi, maskable e apple-touch assenti, manifest che riusa
  >   `icon-512` come maskable, link iOS a `icon-192`, timbro `450af3dd` contro `3e7bd439`).
  > - **Cura** (`dev.py` `generate_pwa_icons`, di cui K è lo scrittore): logo ridimensionato premoltiplicato (`RGBa`) e
  >   composto con `alpha_composite` (niente alone scuro, niente alfa mescolata), tutte le icone in RGB opaco; «any»
  >   192/512 bianche come prima; maskable 192/512 sul beige `#f5f4ef` con il logo a 0,37 del lato dal centro (misurato:
  >   0,380 e 0,373, sotto 0,40); `apple-touch-icon.png` 180 bianca. `manifest.json` con quattro voci, `app.html` col
  >   link `sizes="180x180"`, copie nella doc (`mkdocs_src/docs/static/icons/`).
  > - Generazione deterministica: rigenerata due volte, byte identici; nessun rilievo ruff nuovo su `dev.py` (43 come HEAD)
  >   e nessuna differenza black nella funzione.
  > - **Verde**: 19/20 subito, **20/20 dopo il fast-forward** su `dev_release2` (`b1835949e`), che porta il timbro
  >   `3e7bd439`. Registrato come `utils pwa-assets` (puro).
  > - **Doc** (docs-writer, solo EN): `developer/frontend/pwa.md` riallineata (schema, tabella dei file, manifest, regole
  >   della generazione, nota «Icons and the splash screen», comando del gate). Corrette anche quattro righe che parlavano di
  >   una cache `offline-v1/v2` mai esistita: `sw.js` usa `offline-fallback` più il timbro.
  >
  > **Fuori pista**: ogni `mkdocs build` chiama `copy_docs_assets()` e ritimbrava `sw.js`, che sul ramo prima del
  > fast-forward aveva ancora il timbro vecchio. L'ho riportato a HEAD a mano due volte. Dopo il fast-forward il timbro
  > coincide e il problema non si ripresenta.
- [x] **13.7 Voci 4 + 6a — piede della modale asset**. ✅ 2026-09-30.
  > **Verde in corsia (30/09)** per le tre voci mobile: `asset-mobile-layout` **11/11** (anche con `--workers 4`),
  > component-unit 2182/2182 (con `TabBar`), `asset-modal` 17/17, `settings` 45/45, `files` 21/21 (consumatori di
  > `TabBar`: le etichette delle schede senza icona non spariscono più su mobile), `onboarding-tour` 10/10;
  > `asset-detail` e `broker detail` con i soli rossi già noti (`asset-detail.spec.ts:486` fixture scaduta,
  > `brokers-detail.spec.ts:713` tooltip legato al calendario); check-orphans pulito.
  > **Avanzamento (30/09)** — rosso visto, cura applicata, giro verde in corso. Un solo spec E2E per le tre voci mobile
  > (`e2e/assets/asset-mobile-layout.spec.ts`, 11 test, azione `front-asset asset-mobile-layout`), più
  > `TabBar.test.ts` (component-unit).
  > - **Rosso** (fase B in corsia): creazione e modifica a 390×844 e 360×800, Annulla a x 341–420 e Salva a x 432–522,
  >   fuori dalla finestra (spec `:287`); controlli a 1280 verdi (interruttori e pulsanti sulla stessa riga).
  > - **Cura** (`AssetModal.svelte`): la riga del piede va a capo (`flex-wrap`, `gap-3`); il gruppo dei pulsanti è
  >   `flex-wrap justify-end ml-auto`, quindi scende sotto gli interruttori, allineato a destra, solo quando non ci sta.
  >   Anche il gruppo degli interruttori può andare a capo: a 360 px in inglese occupa già 289 px su 280 disponibili
  >   (misura del test-author), e in una lingua più lunga non ci starebbe.
- [x] **13.8 Voce 6b — «Sincronizza» durante il caricamento**. ✅ 2026-09-30 (verde: vedi 13.7).
  > **Avanzamento (30/09)**:
  > - **Rosso**: con l'assegnazione del provider trattenuta, Sync è barrato e largo 69,9 px contro 159 di Aggiorna; per
  >   un asset manuale, dopo il caricamento, disattivato e barrato come deve, ma stretto (69,9 px).
  > - **Cura** (`assets/[id]/+page.svelte`): flag `providerAssignmentLoaded` (azzerato al cambio di asset, impostato
  >   nel `finally` del caricamento); `isManualOnly = providerAssignmentLoaded && !providerAssignment`, perché
  >   «sconosciuto» non è «manuale», e vale anche per il messaggio del grafico vuoto; il pulsante normale è disattivato
  >   finché l'assegnazione non è nota; quello bloccato ha `w-full`, così riempie il wrapper del `Tooltip` che
  >   `PageToolbar` allarga (`*:w-full` si applica a ogni livello, non solo in `oneColumn`).
- [x] **13.9 Voce 7 — icone delle schede e rete di sicurezza**. ✅ 2026-09-30 (verde: vedi 13.7).
  > **Avanzamento (30/09)**:
  > - **Rosso**: a 390 e 360 px le schede non hanno l'icona (`svg` assente, spec `:431`). Il nome accessibile invece
  >   c'era già grazie a `title` (il test-author l'ha verificato nel codice di Playwright): l'`aria-label` è rosso nel
  >   test di componente di `TabBar` (3 rossi: etichetta di una scheda senza icona nascosta con `showLabels=false` e con
  >   `hideLabelOnMobile`, `aria-label` assente).
  > - **Cura**: `ChartLine` (il nome attuale di `LineChart` in lucide, già importato nella pagina) per la Panoramica e
  >   `Shield` per il Rischio; `TabBar` nasconde l'etichetta solo di una scheda con icona e allora mette
  >   `aria-label={tab.label}`.
  > - Verdi i test diretti: `TabBar` + test di `AssetModal` 72/72; Prettier pulito; svelte-check alla baseline.
- [x] **13.10 Voce 5 — soglie delle 5 barre** (per ultima: la taratura vede le icone e i pulsanti nuovi). ✅ 2026-09-30.
  > **Avanzamento (30/09)**:
  > - **Taratura sui dati reali** (copia fresca della snapshot, server di test sulla 6165, sonda
  >   `/tmp/libreFolio_k13_calib.cjs`): per ogni barra, livello e lingua, la larghezza minima che il contenuto chiede
  >   (max di larghezza barra + sconfinamento), da 1920 a 320 px, con la lingua del profilo cambiata **sulla copia**
  >   (`user_settings.language`; la lingua salvata vince su `localStorage` al login, come ha mostrato una prima scansione
  >   che era rimasta in italiano). Nei livelli sbagliati lo sconfinamento cresce linearmente fino al cambio di livello:
  >   fino a 118 px nella lista asset.
  > - **La lingua più lunga non è sempre il francese: per quasi tutte le barre è lo spagnolo.** Come da D5, per ogni
  >   soglia il massimo sulle quattro lingue + 16 px, arrotondato alla decina:
  >
  >   | barra | denseRow | stackFilters | labelHideTabs |
  >   |---|---|---|---|
  >   | assetsList | 850 → 1020 (es 999, fr 970) | 440 → 520 (es 497) | — |
  >   | assetDetail | 780 → 850 (es 830) | 400 → 510 (es 485) | — |
  >   | dashboard | 810 → 950 (es 929) | 430 → 510 (es 485) | 370 → 460 (es 440) |
  >   | brokerDetail | 800 → 840 (es 824) | 470 → 530 (es 512) | 370 → 660 (es 635, it 622) |
  >   | fxList | 930 → 1030 (es 1011) | 440 → 560 (fr 535) | — |
  >
  >   `oneRow` resta com'è: nessuno sconfinamento in `oneRow` fino a 1920 px. I numeri `oneColumn` sono inerti.
  > - **Verifica dal vivo** delle soglie nuove (sovrascritte via `window.__lfLayouts`) nelle quattro lingue: nessuno
  >   sconfinamento in nessuna barra, salvo due casi che non sono soglie: i quattro filtri `w-44 min-w-[160px]` della
  >   lista asset in `oneColumn` sotto una barra di 311 px (telefoni sotto i 377 px), e la pagina del dettaglio asset
  >   sotto 341 px di finestra, per l'intestazione `asset-detail-info` (titolo `max-w-[15ch]` in contenitori flex senza
  >   `min-w-0`). Cure previste: filtri `flex-1 min-w-0` in `oneColumn`; `min-w-0` sui due contenitori dell'intestazione.
  > - **Rosso prima**: E2E `e2e/layout/toolbar-width-sweep.spec.ts` (test-author; 5 barre × fr/it/es, da 1700 a 320 px,
  >   assestamento del layout con l'orologio di Playwright, una sonda che verifica che la misura funzioni); in corsia.
  >   Sui dati di prova **15/15 rossi** con le soglie di oggi. Il «ci sta da» coincide con la taratura sui dati veri entro
  >   pochi px (per esempio `assetsList` denseRow 1002 contro 999; `fxList` 1012 contro 1011; schede del broker 634
  >   contro 635); in più le schede della Dashboard (fino a 434 in spagnolo). Nessuno sconfinamento in `oneRow`.
  > - **Cure**: le soglie della tabella nelle 5 pagine; i quattro filtri della lista asset `flex-1 min-w-0` in
  >   `oneColumn` (`{@const filterWidthClass}` in testa allo snippet dei filtri, lontano dalle righe `onfitperiod` di F).
  >   Dopo la ricostruzione, **14 barre su 15 verdi**; resta rosso solo il dettaglio asset, per la pagina più larga della
  >   finestra, e in **due fasce**: 330→320 px e 1060→1030 px, appena sopra i 1024, dove il titolo passa a
  >   `lg:max-w-none` (visto dopo che il test-author ha preso come soggetto un asset col nome lungo). Cura: `min-w-0` sui
  >   due contenitori dell'intestazione, così il titolo si restringe e scorre.
  >
  > **Fuori pista**: il test-author ha trovato che un controllo di autenticazione lento perde il link profondo:
  > `(app)/+layout.svelte` mette `auth.checkAuth()` in gara con un timeout di 5 s e, se perde, manda a `/`, che a sua
  > volta porta l'utente autenticato alla Dashboard. È emerso sotto carico, con quattro scansioni in parallelo. Fuori
  > perimetro: va nell'handoff come segnalazione.
  >
  > **Verde (30/09)**:
  > - Corsia 6155: `toolbar-width-sweep` **15/15** (5 barre × fr/it/es, 1700→320 px, 4 worker, 1,2 min); `asset-list`
  >   28/28; `fx-list` 12/12; `asset-mobile-layout` 11/11; `header-scroll` 4/4; `asset-detail`, `dashboard` e `broker
  >   detail` con i soli rossi già noti (il test-author ha verificato il testo dell'errore: con denseRow 950 la Dashboard
  >   a 1280 px passa in `stackFilters`, ma i test del selettore di zoom guardano i pulsanti del grafico, non quelli
  >   della barra); check-orphans pulito.
  > - **Dati reali** (copia della snapshot, build finale, le quattro lingue, 1920→320 px, nessuna sovrascrittura):
  >   nessuno sconfinamento dalle barre e nessuna pagina più larga della finestra. Unico residuo: in spagnolo, a 320 px,
  >   l'etichetta «Inactivos» dell'interruttore della lista asset è ritagliata di 4 px dentro il proprio controllo
  >   (`overflow-hidden`); non esce dalla barra, e la scansione E2E ignora giustamente i contenuti ritagliati. Lasciato
  >   così, documentato.
  > - **Voci mobile sui dati reali** (es e fr, 390 e 360 px): Sync largo quanto Aggiorna (159 e 144 px), schede con
  >   icona e nome, nessuna pagina più larga della finestra, Salva e Annulla dentro la finestra (a 360 px in spagnolo
  >   anche gli interruttori vanno a capo).
  > - Server della copia spento, porte 6155 e 6165 libere; copia, password e log con dati reali cancellati e verificati
  >   con `ls`. Le sonde, senza dati, restano nei file di sessione.
- [x] **13.11 Handoff** — lista dei controlli sui dispositivi (Android e iPhone per la PWA, Chrome per le credenziali,
  telefono per le voci 4/6/7), voci di CHANGELOG, CHECKPOINT READY. ✅ 2026-09-30.
  > **Controlli sui dispositivi del developer** (sull'immagine della sua pipeline, dopo l'integrazione):
  > 1. **Android**: aggiornare la PWA (o reinstallarla) e aprirla: la schermata di avvio mostra il logo sul beige, senza
  >    angoli neri; l'icona sulla home è intera dentro la maschera (cerchio o squircle).
  > 2. **iPhone**: «Aggiungi a Home»: icona bianca col logo, senza bordi neri.
  > 3. **Chrome (desktop)**: pagina di login, clic sul **campo utente**: Chrome propone le credenziali salvate. Se non lo
  >    fa, un login e «Salva/Aggiorna la password» una volta sola (la firma del modulo è cambiata). Poi Impostazioni →
  >    Cambia password: Chrome propone di aggiornare la password dell'account giusto.
  > 4. **Telefono (390/360 px)**: modale asset in creazione e modifica, Salva e Annulla visibili; dettaglio asset con
  >    «Sincronizza» non barrato durante il caricamento, e le due schede con icona; le cinque barre in alto (Asset,
  >    dettaglio asset, Dashboard, dettaglio broker, FX) in italiano e in una lingua lunga (spagnolo), su telefono e su
  >    tablet: nessun pulsante fuori dalla barra.
  > 5. **Dashboard**: con prezzi fermi da più di 7 giorni (per esempio dopo qualche giorno senza sincronizzazione) compare
  >    «N asset con prezzi obsoleti» con **Sincronizza**; dopo la sincronizzazione il banner sparisce. Gli asset manuali
  >    (crowdfunding) non compaiono mai.
  > 6. **Borsa Italiana**: aggiungere l'ETC dell'oro `IE00B579F325` (dalla ricerca o dall'URL): valuta EUR, prezzi EUR.
  > 7. **XSS**: niente di visibile cambia; i nomi con `&` (per esempio «S&P 500») si leggono come prima.
  >
  > **CHANGELOG proposto** (lo scrive il coordinator):
  > - 🐛 Sicurezza: un nome di asset, broker o nota con del markup non esegue più codice nelle tabelle, nei tooltip dei
  >   grafici, nei toast e nei messaggi di validazione (XSS memorizzata, presente dalla v1.1.0).
  > - 🐛 Borsa Italiana: ETF ed ETC prendono la valuta in cui sono quotati (EUR), non quella di denominazione del fondo.
  > - ✨ Il banner «prezzi non aggiornati» ora compare, per gli asset con provider fermi da più di 7 giorni, con il pulsante
  >   **Sincronizza**.
  > - 🐛 Chrome propone le credenziali salvate anche sul campo utente; il cambio password aggiorna l'account giusto.
  > - 🐛 PWA: niente più angoli neri nella schermata di avvio di Android e nell'icona di iPhone.
  > - 🐛 Telefono: nella modale asset Salva resta raggiungibile; «Sincronizza» non appare barrato mentre la pagina carica;
  >   le schede del dettaglio asset hanno un'icona.
  > - 🐛 Le barre in alto non fanno più uscire i pulsanti a larghezze intermedie, in tutte le lingue.
  > - 🔄 Dipendenza `borsa-italiana-scraping` 0.3.2.
  >
  > **Decisioni aperte per il developer**: traduzione del paragrafo nuovo di `user/dashboard/index` (IT/FR/ES) a mano
  > adesso o con la pipeline; nessuno stamp fatto.
  >
  > **Segnalazioni per il backlog** (non curate, fuori perimetro):
  > - tooltip ECharts: avvolgere tutti i formatter in `sanitizeHtml`, con un gate (difesa in profondità);
  > - un controllo di autenticazione lento perde il link profondo (`(app)/+layout.svelte`, timeout di 5 s);
  > - rossi preesistenti girati a I: `chartCoreHelpers` (12), `dashboard` (7), `asset-detail.spec.ts:486` (fixture
  >   scaduta il 17/09), `brokers-detail.spec.ts:713`;
  > - `developer/frontend/data-quality-banner.md`: codici e CTA mancanti, modo «grouped» descritto male, endpoint
  >   `/portfolio/summary` invece di `/portfolio/report`; pagina utente: «valued at purchase cost» impreciso;
  > - `PasswordInput`: il pulsante «occhio» ha un `title` inglese fisso e `tabindex="-1"`;
  > - spagnolo a 320 px: «Inactivos» ritagliato di 4 px dentro il suo interruttore;
  > - Borsa Italiana mappa gli ETC/ETN su `ETF` generico, anche se esiste `ETF_COMMODITY`; gli asset creati prima della
  >   cura con la valuta di denominazione si correggono a mano (nessuno nel prod del developer);
  > - devWiki: le due scoperte del test-author (la pagina `/assets` scrive il prezzo di oggi; `valuation_stale` anche per
  >   i prezzi di transazione), il metodo di taratura delle barre e le regole di escape con i due gate.
  >
  > **Commit**: nove, uno per voce, in quest'ordine: voce 0 (XSS), lock, 3b/3c, 9, 2, 1, mobile (4 + 6a, 6b, 7, che
  > condividono uno spec E2E), 5, journal. Quattro file toccano più voci (`_frontend_utility.py`, `_frontend_asset.py`,
  > `assets/[id]/+page.svelte`, `dashboard/+page.svelte`): per ognuno c'è una versione intermedia per commit, generata e
  > verificata (l'ultima coincide col worktree), in `/tmp/libreFolio_commits/k-13-split/` col manifesto.

## Definizione di fatto (per ogni voce)

1. Test rosso sulla base, verde dopo la cura.
2. Regressioni verdi nella 6155 dopo `front build --debug`; statici come la baseline (svelte-check 3 errori noti, knip,
   ruff/black sulle righe nuove).
3. Doc EN con docs-writer; debito di traduzione dichiarato o timbrato.
4. Voci 3, 5, 9 e quelle su mobile verificate anche sulla copia di prod, con le sonde dell'analisi.

## Prove dell'analisi

`/tmp/libreFolio_k13_probe/` (sonde Playwright, log, screenshot) e `/tmp/libreFolio_k_13_stale_measure_2026-09-*.log`
contenevano dati reali: cancellati dopo l'approvazione e verificati con `ls` (13.0). Anche la copia di prod usata per
le verifiche dello Step 13, la sua password e i log con dati reali sono cancellati e verificati (13.10).
