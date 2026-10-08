# Piano — fase 00, Danske Bank, passo 9: il frontend vecchio dalla cache (#26, «non funziona su Chromium»)

> **Stato**: ✅ pronta per il checkpoint (2026-10-08, §7.3). Via del developer per l'header e per la proposta UX (§0).
>
> - Viene da: [plan-phase00BrimDanskeBankStep8MobileCard.prompt.md](plan-phase00BrimDanskeBankStep8MobileCard.prompt.md).
> - Workstream L, issue #26. Base `9eb01c756` (`dev_release2`, treno 14).

## 0. La segnalazione e le decisioni

- **@jaska087**, nightly dell'08/10, cioè il treno 14: «Plugin does not work on chromium. 2 file(s) could not be parsed», con, per ognuno dei due export, «… is one export of a report set: upload it together with the other exports and import the set». «However plugin does work as intended with Firefox.»
- **Coordinatore**: prima solo analisi e riproduzione. Le 4 domande all'utente sono nella risposta: versione nella sidebar, come apre l'app, Ctrl+Shift+R, ricaricare insieme.
- **Developer** (testuale): «riguardo alla risoluzione, si facciamolo». Il coordinatore lo traduce così:
  1. `Cache-Control: no-cache, must-revalidate` su `GET /` (`main.py:442`) e su ogni altra rotta che serve `index.html` o `200.html` senza header; i chunk `immutable` di `/_app` restano come sono;
  2. un test di regressione via test-author, rosso prima, sulla radice e sul fallback SPA;
  3. il suggerimento UX per i membri di un set rimasti senza batch: prima la proposta (testo, posto, chiavi ×4), che il developer approva;
  4. gate: il test nuovo, la categoria `api` che lo ospita, un E2E che carica l'app dalla radice. Il CHANGELOG lo scrive il coordinatore («Fixed: dopo un aggiornamento il browser non riusa più l'interfaccia vecchia»).
- **Developer, sulla proposta UX** (testuale): «Chiaro, approvo la proposta di L». Va implementata com'è (§5), con la chiave aggiunta via `dev.py i18n add`.
- **Coordinatore**: la frase per `danske-bank.en.md` **non la scrivo io**. Il treno 15 porta la riscrittura della pagina fatta da Q, e poi M ci mette le immagini. Il testo va nel checkpoint, e la inserisce chi tocca la pagina dopo il treno.

## 1. Stato verificato (2026-10-08, sul codice a `9eb01c756`)

- **Il messaggio** viene da `ensure_parseable` (`brim_report_sets.py:404-411`): il backend rifiuta *ogni* originale letto da solo con un plugin di report set. Risponde 422 `set_required` e non sposta il file in `failed` (`brokers.py:803-811`).
- **Quando il wizard di oggi legge un membro da solo**: `setPluginFor` (`importReportSets.ts:135-141`) lascia fuori dai set:
  - un file senza `batch_id`;
  - un file in stato `failed`;
  - tutti i file, se il catalogo dei plugin non ha `report_roles`.

  A quel punto `pickBestPlugin` (`ImportWizardModal.svelte:3396-3421`) sceglie `compatible_plugins[0]`, cioè `danske_bank`, e Parse parte.
- **Tutti e tre i percorsi di upload** mandano un `batch_id` con `generateUUID`, che ha il fallback per HTTP (`utils/core/uuid.ts`):
  - il wizard (`:222`, `:2526`, `:3201`);
  - `BrokerImportFilesModal.svelte:121`;
  - la pagina globale `routes/(app)/files/+page.svelte:503`.

  Con questo frontend, due export caricati oggi formano un set.
- **La cache**:
  - `GET /` serve `index.html` **senza** `Cache-Control` (`main.py:442`);
  - il ramo «file esatto» del catch-all (`:494-496`) serve `index.html`, `200.html` e gli altri `.html` del build senza header;
  - solo il fallback SPA (`:507-510`) ha `no-cache, must-revalidate`, aggiunto in `f82adc0d7` per una segnalazione beta («build vecchia fino a F5»);
  - `/_app` è `immutable` per un anno (`:461-468`).

  Così un browser che ha già visto `/` può riprendere dalla cache euristica (il 10% dell'età del `Last-Modified`) l'`index.html` della versione prima, e con lui tutti i chunk vecchi.
- **Il frontend 1.1** spiega tutto il testo citato:
  - carica senza `batch_id` (zero occorrenze in `v1.1.0`);
  - sceglie `compatible_plugins[0]`;
  - il suo `extractErrorMessage` mostra `detail.message`;
  - il titolo «{n} file(s) could not be parsed» c'era già.

  E i file che carica restano senza batch per sempre: anche col frontend nuovo, ri-spuntati, danno lo stesso errore.

## 2. Il contratto (header)

- Ogni documento HTML che il backend serve dal build del frontend ha `Cache-Control: no-cache, must-revalidate`. Sono: `GET /`, il fallback SPA e i file `.html` esatti come `/index.html`, `/200.html` e `/offline.html`. Così il browser rivalida a ogni caricamento. Costa un 200 di circa 5 KB (2 KB in gzip): un `FileResponse` restituito da una rotta, in Starlette, ignora `If-None-Match` (nota del test-author).
- Lo stesso vale per le pagine HTML della documentazione (`/mkdocs`, `/mkdocs/…`), che servono un `index.html` senza header.
- Non cambia niente per `/_app` (`immutable`, con l'hash nel nome), né per i file non HTML del build (favicon, manifest, `sw.js`).

## 3. I test, rossi prima (test-author)

In `backend/test_scripts/test_api/test_http_compression_api.py` (voce `api http-compression`), che già serve il frontend da un server vero e ne verifica il contratto di cache:
- `GET /`, `GET /index.html` e `GET /200.html`: rossi oggi;
- una rotta SPA, cioè il fallback: verde oggi, come guardia;
- `/_app` resta `immutable`: c'è già GZIP-003.

## 4. Superfici

| File | Cosa |
|---|---|
| `backend/app/main.py` | un header comune per le risposte HTML: radice, catch-all (solo `.html`), fallback, mkdocs |
| `backend/test_scripts/test_api/test_http_compression_api.py` | il test (test-author) |
| `frontend/src/lib/utils/transactions/importReportSets.ts` (+ `.test.ts`, test-author) | la regola `ungroupedSetFiles` (§5) |
| `frontend/src/lib/components/transactions/modals/ImportWizardModal.svelte` | il blocco del passo ② e l'avviso `ungrouped` |
| `frontend/src/lib/i18n/{en,it,fr,es}.json` | la chiave `importWizard.reportSet.ungroupedBlocks`, via `dev.py i18n add` |
| `frontend/e2e/transactions/tx-import-report-set.spec.ts` | U1 (test-author) |
| questo piano; il rimando in Step8 | — |

## 5. La proposta UX (✅ approvata)

- **La regola** (`importReportSets.ts`): `ungroupedSetFiles(units, plugins)` dà i file selezionati che l'analisi leggerebbe da soli (`kind: 'file'`) con un plugin di report set, nell'ordine della selezione. È ciò che il backend rifiuta (`ensure_parseable`), qualunque sia la causa: niente batch, o `failed`.
- **Passo ②**:
  - Continue (`import-wizard-parse`) è disattivato finché un file così è spuntato;
  - l'avviso è `import-wizard-set-blocks` con `data-reason="ungrouped"` e `data-file-ids` (gli id, separati da virgola);
  - la precedenza è `partly-selected` (R6), poi `ungrouped`, poi `incomplete`.
- **La chiave** `importWizard.reportSet.ungroupedBlocks`, con `{files}` (i nomi, separati da virgola), nei testi approvati ×4.
- **Doc**: la frase per `danske-bank.en.md` va al coordinatore (§0).
- **Fuori**: il raggruppamento automatico dei file senza batch (D-S22) e un'azione «unisci in un set», che chiederebbe un'API nuova.

## 6. Gate

- Il test nuovo, poi `api http-compression` intera.
- Un E2E che carichi l'app dalla radice.
- La prova della cache su Chromium, prima e dopo, da un'origine HTTP non localhost (`/tmp/lf-repro/cache.cjs`).
- ruff e black; `git diff --check`; porte libere.

## 7. Avanzamento

### 7.0 ✅ L'analisi (2026-10-08)

> **Note implementazione**: §1. Al coordinatore sono andati l'ipotesi e le 4 domande per l'utente, e lui li ha verificati.
>
> **⚠️ Fuori pista**: il primo messaggio l'avevo mandato come `progress`, e non arriva al coordinatore. L'ho rimandato come `needs_input`.

### 7.1 ✅ La cura dell'header (2026-10-08)

> **Note implementazione**:
> - **Il rosso** (test-author, `test_http_compression_api.py`, +87/−4):
>   - **CACHE-001**: `/`, `/index.html`, `/200.html`, una rotta SPA unica e `/offline.html` sono l'HTML dell'app, e hanno `no-cache` e `must-revalidate`;
>   - **CACHE-002**: i chunk `immutable` nominati da `/` non diventano mai `no-cache`.
>
>   `api http-compression` sulla 6156: **1 failed, 9 passed**, con ✘ su `/`, `/index.html`, `/200.html` e `/offline.html` (`Cache-Control: None`) e ✓ sulla rotta SPA. Log: `files/step9/cache-red.log`.
> - **La cura** (`main.py`):
>   - `REVALIDATE_HTML` e `_revalidated_file(path)`, che mettono l'header solo sui `.html`;
>   - usati dalla radice, dal ramo «file esatto» del catch-all, dal fallback `200.html` e `index.html`, e dalle due rotte di mkdocs;
>   - `/_app` non cambia.
>
>   Ruff e black puliti. `api http-compression`: **10 passed**. Log: `cache-green.log`.
> - **La prova su Chromium**, da un'origine HTTP non localhost: `http://lf.test:6156` mappato su 127.0.0.1 con `--host-resolver-rules`, quindi `isSecureContext=false` e `crypto.randomUUID` assente. Script `/tmp/lf-repro/cache.cjs`, profilo persistente.
>   - Il metodo: la prima visita trova la versione A, con `Last-Modified` di 30 giorni prima; poi il server passa alla B.
>   - **Prima della cura**, su `/`: la seconda visita vede ancora A, con `transferSize=0`. Il frontend vecchio viene dalla cache, senza chiedere niente al server. `/dashboard` (`no-cache`) vede B.
>   - **Dopo la cura**, su `/`: la seconda visita vede B (`transferSize=2102`).
>   - Log: `files/step9/cache-{before,after}.json`. I file del build sono sempre ripristinati, contenuto e mtime.
>
> **⚠️ Fuori pista — Firefox non provato**. Playwright vuole `firefox-1532`, ma è installato il `1497`, e installare browser non è concesso. Anche Firefox applica la cache euristica (RFC 9111): la differenza fra i due browser la fa la storia del profilo, non il motore.
>
> **⚠️ Fuori pista — `/_app/version.json`** è `immutable` per un anno, ma non ha l'hash nel nome. L'app non usa il controllo di versione di SvelteKit (niente `pollInterval`, niente `updated`). Il controllo interno di SvelteKit manda comunque `cache-control: no-cache` nella richiesta. Lasciato com'è, come deciso per `/_app`.
>
> **⚠️ Fuori pista — `HEAD`**. `curl -I` riceve 405, perché le rotte sono solo `GET`. Per leggere gli header ho usato una `GET`.

### 7.2 ✅ La proposta UX: i rossi e la cura (2026-10-08)

> **Note implementazione**:
> - **Lo stub**, prima dei rossi: `ungroupedSetFiles` con la firma definitiva, che restituisce `[]`. Poi `front build --debug`.
> - **I rossi** (test-author):
>   - unit, `describe('ungroupedSetFiles')` in `importReportSets.test.ts`, 9 test, compresa la pipeline `groupBrokerFiles → buildParseUnits`. `tx-unit`: **4 failed, 681 passed**, tutti su `AssertionError` («expected [] …»), cioè i casi «è nella lista»;
>   - E2E **U1** in `tx-import-report-set.spec.ts`, solo desktop. Due export caricati via API **senza batch** e spuntati come singoli, nell'ordine inverso a quello della tabella. Il rosso: «holds the analysis back — Expected: disabled, **Received: enabled**». Tutte le premesse passano: senza batch, Danske preselezionato, nessuna card del broker spuntata. **È la variante (c) riprodotta sul frontend di oggi.**
> - **La cura**:
>   - la regola in `importReportSets.ts`;
>   - nel wizard, `ungroupedFiles` e `setBlockReason` (la precedenza R6 → ungrouped → incompleto), `step2CanParse` che richiede `ungroupedFiles.length === 0`, e l'avviso con `data-reason`, `data-file-ids` e il testo della chiave nuova;
>   - la chiave nelle 4 lingue via `dev.py i18n add` (script `/tmp/libreFolio_i18n_ungrouped.sh`).
>   - Prettier: c'era da sistemare solo la riga d'import del wizard, troppo lunga dopo l'aggiunta. `--write` su quel file, poi di nuovo `front build --debug`.
> - **Verdi**: `tx-unit` 685/685; U1 passed.
>
> **⚠️ Fuori pista — la premessa «nessuna card del broker»**. Il test-author non l'ha scritta: un id di broker riusato da un run precedente può arrivare con dei file avanzati, e una card non spuntata la renderebbe rossa senza un difetto. Ha controllato invece che ogni export sia una riga singola, e che nessun set del broker sia spuntato. Accettato.

### 7.3 ✅ I gate (2026-10-08)

> | Gate (corsia 6156, un comando alla volta; log `files/step9/`) | Esito |
> |---|---|
> | `api http-compression` (CACHE-001/002 e GZIP) | 10 passed |
> | `front-transaction tx-unit` | 685/685 |
> | `tx-import-report-set`, intera, desktop e mobile. Il `login()` apre `/`: è l'E2E che carica l'app dalla radice | **32 passed, 32 skipped**, U1 compreso |
> | `front-utility app-start-auth`, l'avvio dell'app da `/` | 3 passed |
> | `tx-import-report-set-guide` | 2 passed |
> | `front-utility core-unit` / `component-unit` | 3435/3435 / 2850/2850, exit 0 |
> | `i18n audit` | 4166 chiavi complete, 0 mancanti, 0 inutilizzate |
> | svelte-check (dentro `front build --debug`) | 0 errori, 0 avvisi |
> | `check-orphans`; ruff e black (`main.py`, il test); prettier; `git diff --check` | puliti |
> | porte 6156 e 6166 | libere |
>
> **La frase per `danske-bank.en.md`**, che inserirà chi tocca la pagina dopo il treno 15: «Exports uploaded with a LibreFolio version before 1.2 are in no set and cannot be read on their own: the wizard keeps Continue disabled while one of them is selected. Upload all the exports of the set again together, in one go, then select that set; the old copies can be deleted.»

### 7.4 ✅ Integrato (2026-10-08)

> **Note implementazione**:
> - I commit: `333bfc985` fix(server): HTML entry points always revalidate; `38dd5d1b4` fix(import): block set exports read alone; `a683b884b` docs(journal): plan 26 step 9, stale frontend. Il messaggio di C3 è stato reso ASCII: le virgolette «» sono diventate `"`.
> - Merge `9055293c7` nel treno 16; `dev_release2` = `cf4248bd9`.
> - I controlli del treno li fa girare il coordinatore: `api http-compression`, `tx-unit`, gli E2E dei report set e `app-start-auth`.
> - La frase per `danske-bank.en.md` è passata a M, che la inserisce nel suo lotto delle pagine utente.
