# Rosso della run completa (treno 18): `fx-add-pair.spec.ts:40`, la pagina FX attesa per 3 s

> Lotto di N, 08/10. Coordinator: c8328a01. Base `70d02cd8e` (treno 18), worktree pulito. Corsia 6159/6169,
> `/tmp/librefolio-r2-n`. Fino alle 22 la 6150 ospita la run completa: solo giri leggeri.

## 1. Il rosso

- **Il test**: la variante «provider creation closes promptly and links to its owned pair after leaving FX», in
  desktop, 2 worker, 10,9 s.
- **L'errore**: `expect(getByTestId('fx-page')).toBeVisible()` scaduto dopo 3000 ms (`:167`), subito dopo
  `page.goto('/fx?start=…&end=…')` (`:165`).

## 2. Triage (`test-triage`, ipotesi 2: l'orologio). Verdetto: **assumption**

- `:165-168` fa un `page.goto` completo e poi dà all'avvio dell'app i 3 s predefiniti di `expect`, quelli «for
  localhost assertions» (`playwright.config.ts:109`). Gli altri 3 s vanno a `data-busy`.
- `fx-page` (`fx/+page.svelte:955`) non sta sotto nessun `{#if}`. Compare quando il layout `(app)` lascia passare la
  pagina: i18n, sessione, `appBootstrap.ready`, onboarding (`(app)/+layout.svelte:226-245`). È una condizione vera,
  che sotto carico richiede più di 3 s.
- L'helper del progetto `goToFxPage` (`e2e/fx/fx-helpers.ts:16-21`) aspetta la stessa condizione con le tolleranze
  giuste: `navigateTo` (con `data-i18n-ready`, 15 s), `fx-page` 15 s, `data-busy="false"` 20 s. Però non accetta
  query param.
- Le due varianti sorelle, nella stessa invocazione, erano verdi (23,9 s e 24,4 s); stamattina, con meno carico,
  lo erano tutte e tre.
- **Ricerca dello stesso schema negli spec FX** (`e2e/fx/*.spec.ts`: un `goto` completo seguito da un `expect` coi
  3 s predefiniti): c'è **solo** `fx-add-pair.spec.ts:165-168`.
  - `fx-detail.spec.ts:287`, `:1605`, `:1652` e `fx-flag-font.spec.ts:309`, `:364`, `:371`, `:404`, `:421`
    aspettano già 10-30 s.
  - `fx-detail.spec.ts:1119` (`reload`) aspetta `waitForSettled` per 20 s.
  - `fx-flag-font.spec.ts:213` apre una pagina statica, intercettata.
- **Fuori schema, non toccati**: in questo file, le attese predefinite che seguono una navigazione **interna**
  (`fx-card` → dettaglio `:219`, sidebar → impostazioni `:236`, ritorno `:284`, link del toast `:322`).
  L'app è già avviata, quindi niente bootstrap. Non è un difetto: nessun rosso osservato, quindi nessun rinvio
  (allineamento del 09/10).

## 3. Correzione (test-author)

1. `goToFxPage(page, search = {})`: accetta i query param (`URLSearchParams`), con le stesse attese di prima. I 35
   chiamanti esistenti non cambiano.
2. `fx-add-pair.spec.ts:165-168`: `await goToFxPage(page, range)` al posto di `goto` + i due `expect` predefiniti.
3. Nessuna riga nel runner, nessun codice di prodotto.

## 4. Passi

1. ✅ (08/10) Triage e verdetto.
2. ✅ (08/10) Correzione (test-author), +7 −5 in due file.
   > **Note implementazione**:
   > - `goToFxPage(page, search = {})`: senza argomento naviga su `/fx` esattamente come prima (35 chiamanti
   >   invariati); con `range` la query è `start=2024-03-01&end=2024-03-31`, identica a prima.
   > - Lo spec chiama `await goToFxPage(page, range)` al posto di `goto` + i due `expect` predefiniti; in più
   >   aspetta `data-i18n-ready`.
   > - Le tolleranze dell'helper (15/15/20 s) sono limiti dentro i 30 s del test, non tempo aggiunto.
3. ✅ (08/10) Verde in corsia:
   - `front-fx fx-add-pair`: **11/11 a 1 worker** (33,4 s) e **11/11 a 2 worker** (25,2 s);
   - `front-fx all`: **102/102 E2E** (4,4 min) e **126/126 unit** (4 file).
   - Prettier pulito sui due file. `tsc -p tsconfig.e2e.json`: 0 errori nei due file; i 2 errori presenti sono già
     su HEAD, in altri file.
   > **Senza rosso deterministico.** È un'attesa a orologio che cede solo sotto carico: il rosso è quello della run
   > completa, e la cura sostituisce l'orologio con la condizione vera (`test-triage` §2).
4. ✅ (08/10) Checkpoint: 2 commit proposti in `/tmp/libreFolio_commits/libreFolio_commit_n_fxnav_C1..C2.txt`. Liste
   in `n_fxnav_paths_C1..C2.txt`, blob in `n_fxnav_blobs.txt`, albero in `n_fxnav_final_tree.txt`. Stato: FROZEN.
   > **Integrato** (allineamento del 09/10): `49d6f5324` (helper e spec), `55019a641` (questo piano), treno 19
   > (`f2409810b`). Nessun residuo.
