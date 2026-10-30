# Brief — workstream Y · Cruscotto e grafici · Y-40 (tre viste sulle schede) + test di `OtherPeriodEffectsTable`

> **A cosa serve (per il developer).** Dalla lista Assets (e poi dalla lista dei cambi) l'utente sceglie con un tocco come vedere le schede: **valore assoluto**, **percentuale** o **rendimento mobile**; il dettaglio si apre nella stessa vista. Esempio: imposti «rendimento mobile» in alto e tutte le schede mostrano il rendimento a 1 anno, finestra per finestra. Il test di `OtherPeriodEffectsTable` invece è manutenzione: oggi fallisce su un computer in italiano per colpa del test, non dell'app.

**Worktree**: `/home/alfy/Documenti/02_myRepo/LibreFolio_prj/LibreFolio-worktrees/e-alfy-redesigned-spork` · **Branch**: `e-alfy-y-cruscotto-e-grafici`
**HEAD di partenza (da verificare)**: `2879ae3e4` (= `dev_release2`, treno 7; fast-forward fatto dal coordinatore).
**Corsia**: porta `6189`, cartella dati `/tmp/librefolio-r13-y`.
**Piano**: `LibreFolio_developer_journal/Release_2/Phase_1/09_dashboardCharts/plan-phase01DashboardCharts.prompt.md`: analisi Y-40 (righe ~7739-7935, V-1…V-9), decisioni (~7905-7916), riga di stato ~496.

## Passo 0 — il test che dipende dalla lingua (piccolo, prima di tutto)
`frontend/src/lib/features/dashboard/OtherPeriodEffectsTable.test.ts:85`: `plainAmount` costruisce l'importo atteso con `toLocaleString(undefined, …)` (lingua del sistema), mentre il componente usa `formatCurrencyAmountPlain` con `uiLocale()` (`currencyFormat.ts:41`). Su un sistema `it_IT` 3 test falliscono. Cura nel test (passare la stessa lingua del componente), **senza** `LC_ALL`: prova che passa sia con `LC_ALL=it_IT.UTF-8` sia con `en_US.UTF-8`. Consegna questo pezzo nel checkpoint finale (non serve un checkpoint a parte).

## Passo 1 — Y-40, parte asset (in 1.3)
Contratto deciso (V-1…V-8 tutti (a)): `primaryView: 'absolute' | 'percentage' | 'calendar-return'` nello store delle impostazioni dei grafici (globale e per scheda, localStorage, **con migrazione** e test `.migration.test.ts`); selettore triplo nella barra in alto; il pulsante della scheda cicla % → mobile → assoluto; il dettaglio si apre nella vista scelta; il rendimento mobile per scheda con i bersagli dei confronti; finestra = `calendarReturnWindow`, primo avvio = il preset più grande che copre il periodo mostrato. I dati ridotti ci sono già (Z-29s-a e Z-29b in dev: `reducedPriceQuery.ts` manda già i segnali con `max_points`).
- File probabili: `routes/(app)/assets/+page.svelte`, `AssetCard`, `PriceChartCompact`, `ChartSettingsModal`, `chartSettingsStore` (+ test di migrazione), `calendarReturnWindow.ts`.
- **Le pagine di dettaglio (`assets/[id]`, `fx/[pair]`) in questa ondata sono della sessione X** (fa Y-42 sugli stessi file). Tu **non le tocchi**: definisci nello store il contratto della vista d'apertura (`primaryView` letto dal dettaglio) e scrivilo nel checkpoint; la lettura nel dettaglio la fa X dopo il tuo commit.
- `chartSignalRendering.ts` resta tuo: se X ti chiede un'aggiunta tramite il coordinatore, la fai tu.
- Prima i rossi (store e migrazione, ciclo del pulsante, vista d'apertura), poi la cura.
- E2E nello slot: `front-asset asset-list` (i test «global Abs/% controls…» e «one AssetCard can override…» vanno riscritti), poi `front-fx fx-settings`.
- Consegna **CHECKPOINT READY (asset)** e FROZEN.

## Passo 2 — Y-40, parte cambi (solo dopo il via del coordinatore)
V-9 = sì in 1.3, ma il rendimento mobile dei cambi ha bisogno del backend di **Z-29fx** (sessione Z, in parallelo). Il coordinatore ti dà il via quando Z-29fx è committato. File: `routes/(app)/fx/+page.svelte`, `FxCard`; E2E `front-fx fx-list`. Y-41 (il confronto con un asset nella lista cambi è offerto ma non disegnato): proponi «nascondere» o «caricare le serie», non decidere.

## Non fare
- Non toccare `lib/features/transactions/**` (colori, C1), `lib/theme/**` (C2), i file del backend di Z-29fx, le pagine di dettaglio oltre al parametro della vista.
- Le condizioni di DV su `LineChart.svelte` valgono sempre (`echarts.init(…, chartInitOptions(chartContainer))` intatto, nessun colore scritto a mano).
- Niente galleria (si fa alla fine, a macchina ferma).

## Fatto quando
Passo 0 verde in entrambe le lingue; passo 1 con rossi→verdi, migrazione provata, E2E verdi nello slot, doc (`charts.md`, pagine utente delle impostazioni dei grafici, solo inglese) e piano aggiornati, righe CHANGELOG proposte, **CHECKPOINT READY** e **FROZEN**.
