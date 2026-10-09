# Piano — K / step 19: l'avvio dell'app (un timeout non è un logout), più il backdrop delle modali e l'Esc del trigger

> Lotto approvato dal developer e assegnato dal coordinator. Viene dallo step 18
> ([`plan-phase00TaxonomySelectStep18CoverageTriage.prompt.md`](plan-phase00TaxonomySelectStep18CoverageTriage.prompt.md)),
> dove il triage dello sweep aveva trovato il timeout di 5 s di `checkAuth`.

| | |
|---|---|
| **Baseline** | `3a8139c29`, cioè lo step 18 (`5fb27fca2`, `d998a8dd7`, `5a9a088b9`, `301906813`) più il merge di `dev_release2` `9d79c2dbe` (treno 10, con S17 di O) |
| **Lane suite** | `--test-port 6155 --data-dir /tmp/librefolio-r2-k`, preambolo `PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc`. Sonde sulla 6165, con la data-dir della corsia. |
| **Ordine** | il piano nel repo, poi i test rossi col test-author, poi il codice (coordinator, 08/10) |
| **Conflitti** | nessun ramo locale tocca dalla merge-base le superfici qui sotto (verificato il 08/10). Il lavoro non committato degli altri worktree non lo vedo. |

## Decisioni

- **Developer** (07/10, testuale): «Sì, nella 1.2: pagina conservata, e un timeout non è un logout».
- **Coordinator** (07/10 e 08/10):
  1. **Solo una risposta 401** di `/auth/me` vale «non autenticato».
     - Si va al login con `goto('/?redirect=<path+query>')`, anche nel redirect reattivo.
     - **Entra anche l'intercettore 401 globale**: niente redirect se si è già sulla root.
  2. **Timeout, errore di rete o 5xx** non sono un logout.
     - La sessione client non si azzera e la pagina chiesta resta.
     - Al loro posto il pannello «The server is not responding» con Riprova.
     - Il timeout resta, ma solo per mostrare quello stato.
  3. **Testi**, con `dev.py i18n add`, in EN, IT, FR ed ES:
     - titolo «The server is not responding»;
     - corpo «This page stays open and you have not been signed out. Try again in a moment.»;
     - il pulsante riusa `common.retry`.
  4. **`safeInternalPath()`**: si esporta e si riusa; la root la applica a `?redirect=`. Approvati anche `checkAuth()` a
     tre stati e il file `layout.authGate.test.ts`.
  5. **`ModalBase`**: `margin: 0` su `.modal-backdrop` (difetto trovato da M).
  6. **`SearchSelect` a tendina**: l'Esc sul trigger a lista aperta chiude la lista e non la modale.
  7. **`tx-split-promote` C3**: nel backlog.

## Stato verificato alla base `3a8139c29`

- **`routes/(app)/+layout.svelte`** (`onMount`, `:62-133`): `Promise.race([auth.checkAuth(), timeout 5000])`.
  - Con `!isAuth` fa `goto('/')`; il timeout entra nel `catch` e fa `goto('/')`.
  - Il redirect reattivo `:137-140` fa `goto('/')` su `$isAuthInitialized && !$isAuthenticated`.
  - Il template (`:202-248`) termina con «Checking authentication...», senza testid.
  - S17 ha aggiunto `i18nBooted` (`:49-50`), lontano da queste righe.
- **`lib/stores/app/auth.ts`** (`checkAuth`, `:166-198`): qualunque errore porta a `transitionClientSession(null)`, utente
  `null` e `isInitialized: true`, quindi anche un 5xx o un timeout fanno scattare il redirect reattivo.
  - Una risposta superata da un'operazione più recente restituisce `false`, e il layout la leggerebbe come «non
    autenticato».
- **`lib/api/zodios-client.ts`** (`:121-136`): l'intercettore fa `goto('/')` su un 401 di **qualunque** chiamata.
- **`routes/+page.svelte`**:
  - `:31` `redirectTo = searchParams.get('redirect') || '/dashboard'`, **senza validazione**;
  - `:50` `const isAuth = await auth.checkAuth()`;
  - `LoginCard` riceve `redirectTo`.
- **`lib/features/onboarding/appBootstrap.svelte.ts`** (`:25-28`): `safeInternalPath()` privata, con la regola «inizia
  con `/`, non con `//`, niente `\`».
- **Chiamanti di `checkAuth`**: la root `:50`, il layout `:98`, `ProfileTab.svelte:122/183/234` (questi ignorano il
  risultato).
- **`ModalBase.svelte:248-257`**: `.modal-backdrop` (`position: fixed; inset: 0`) non azzera il margine.
  - `AboutTab.svelte:247` è `space-y-8`, e `SocialShareModal` (`:586`) non è l'ultimo figlio.
  - In Tailwind 4 la regola `:where(.space-y-8 > :not(:last-child)) { margin-block-end: 2rem }` accorcia il backdrop di
    32 px in fondo, dove resta un'area cliccabile sotto un dialog `aria-modal`.
  - Le prove di M stanno in un altro worktree, che le mie regole vietano di leggere: riproduco nella mia corsia.
- **`SearchSelect.svelte`** (`handleTriggerKeydown`): a lista aperta senza `inlineSearch` non gestisce nessun tasto.
  - Non c'è un gestore di focusout, quindi Shift+Tab dal box di ricerca porta sul trigger e la lista resta aperta.
  - Lì l'Esc risale a `ModalBase` e chiude la modale.

## Disegno

1. **Util nuovo, senza dipendenze**: `lib/utils/internalPath.ts`. Si evita così un import ciclico fra il client API e
   l'onboarding.
   - `safeInternalPath(value, fallback = '/dashboard')`, che tiene il valore solo se:
     - è una stringa con un solo `/` iniziale;
     - non contiene `//` all'inizio, `\` né caratteri di controllo;
     - risolta contro un'origine fittizia, resta su quella origine.
   - `loginUrl(requested)`: `/` se il percorso non è valido o è la root, altrimenti `/?redirect=<encodeURIComponent>`.
   - `appBootstrap.svelte.ts` importa `safeInternalPath` da qui e cancella la sua copia privata; il comportamento del
     `returnTo` di welcome non cambia.
2. **Store** (`auth.ts`): `checkAuth()` restituisce `AuthCheckResult`.
   - `'authenticated'`: 200.
   - `'unauthenticated'`: **solo 401**. Azzera la sessione come oggi.
   - `'unreachable'`: timeout, rete o 5xx. **Non** tocca utente, sessione né `isInitialized`, quindi il redirect reattivo
     non scatta.
   - Più `'superseded'` per la risposta superata da un'operazione più recente (oggi `false`). Il chiamante non fa
     niente: serve perché Riprova può partire mentre un check lento è ancora in volo.
3. **Layout**: una funzione di partenza unica.
   - Esiti:
     - `authenticated` → il flusso di oggi;
     - `unauthenticated` → `goto(loginUrl(path+query))`;
     - `unreachable` → il pannello;
     - `superseded` → niente.
   - Il timer di 5 s **mostra soltanto** il pannello, mentre il check continua; se poi arriva `authenticated`, il
     pannello sparisce e la pagina parte.
   - Riprova rilancia il check.
   - Il redirect reattivo usa `loginUrl`.
   - Il ramo «Checking authentication...» riceve il testid `app-auth-checking`.
4. **Pannello**: `lib/components/layout/ServerUnreachable.svelte`.
   - Testid: `server-unreachable` (radice, con `data-busy`) e `server-unreachable-retry`.
   - `role="alert"`, i testi i18n, il pulsante disabilitato mentre un check è in volo.
5. **Root**: `redirectTo = safeInternalPath(searchParams.get('redirect'))`; `checkAuth() === 'authenticated'` porta alla
   destinazione.
   - Con gli altri esiti si mostra il form come oggi. Alla root il «pannello» non serve: la pagina chiesta è il login
     stesso.
6. **Intercettore 401**: `goto(loginUrl(location.pathname + location.search))`, ma solo se `location.pathname !== '/'`.
7. **`ModalBase`**: `margin: 0` in `.modal-backdrop`. La regola scoped vince su `:where()`, che ha specificità 0.
8. **`SearchSelect`**: in `handleTriggerKeydown`, a lista aperta senza `inlineSearch`, su Escape `preventDefault`,
   `stopPropagation` e `closeDropdown`. Gli altri tasti restano com'erano.
9. **i18n**: `auth.serverUnreachable.title` e `auth.serverUnreachable.body`, ×4, con `dev.py i18n add`.

## Test (rossi prima, test-author)

- **Lotto A, unit e componente** (vitest diretto, senza corsia):
  1. `utils/__tests__/internalPath.test.ts`, registrato in `core-unit`, su `safeInternalPath` e `loginUrl`:
     - tenuti: `/assets/34?tab=risk`;
     - scartati, cioè fallback: `//evil.example`, `https://evil.example`, `/\evil`, `/\t/evil.example`,
       `javascript:alert(1)`, vuoto e `null`.
  2. `stores/app/auth.test.ts` (`front-user user-unit`):
     - 401 → `unauthenticated`, con sessione `null`;
     - 500, errore di rete e timeout di axios → `unreachable`, con utente, sessione e `isInitialized` invariati;
     - lento ma poi 200 → `authenticated`;
     - superata → `superseded`.
  3. `routes/(app)/layout.authGate.test.ts`, nuovo, con `browser: true` e timer finti, registrato in `component-unit`:
     - 401 → `goto('/?redirect=…')` con path e query;
     - `unreachable` → pannello e nessun `goto`; Riprova → `authenticated` → nessun `goto`, il pannello sparisce;
     - check oltre 5 s → pannello e nessun `goto`; poi `authenticated` → nessun `goto`;
     - redirect reattivo → `loginUrl`.
  4. `ModalBase.escapeLayers.test.ts`: un caso in più, select a tendina aperta col focus sul trigger → Escape → la lista
     si chiude e la modale resta.
- **Lotto B, E2E** (corsia 6155, build `--debug` aggiornata):
  1. `e2e/layout/app-start-auth.spec.ts`, nuovo, registrato:
     - caricamento completo di una pagina dell'app con `/auth/me` trattenuto oltre 5 s → il pannello appare e l'URL resta;
       sbloccato → la pagina si carica;
     - senza sessione → `/?redirect=…` → login → la pagina chiesta;
     - 401 a metà sessione (cookie cancellato, poi una navigazione) → `/?redirect=…`.
  2. Il backdrop: in Impostazioni → Info apro una condivisione social; il backdrop copre il viewport fino al bordo
     inferiore, ed `elementFromPoint` negli ultimi px trova il backdrop. Spec: `support-copy-and-go.spec.ts`, oppure un
     file nuovo registrato.

## Passi

- [x] **19.1 Base** `3a8139c29`: verificata pulita, blob dello step 18 uguali al manifesto, il runner fuso con la riga di
  `dev_release2`. ✅ 2026-10-08.
- [x] **19.2 Decisioni**: vedi sopra. ✅ 2026-10-08.
- [x] **19.3 Rosso**: lotto A, poi lotto B. ✅ 2026-10-08.
  > **Note implementazione**:
  > - **Lotto A** (test-author, vitest diretto): 59 test, 47 rossi e 12 verdi sulla base.
  >   - `internalPath.test.ts`: 25 rossi, perché il modulo manca. Il caricamento sta dentro ogni test, quindi ogni test
  >     fallisce da sé.
  >   - `auth.test.ts`, 16 rossi:
  >     - gli esiti erano ancora booleani;
  >     - un 5xx, un errore di rete o un timeout svuotano lo store: lo store freddo diventa «inizializzato e uscito», e da
  >       quello caldo spariscono l'utente e la sessione;
  >     - l'asserzione intenzionale del test sulla risposta superata passa da `false` a `'superseded'`.
  >   - `layout.authGate.test.ts`: 5 rossi e una guardia verde.
  >     - `unauthenticated` letto come entrato;
  >     - nessun pannello;
  >     - il timeout di 5 s fa `goto('/')`;
  >     - `superseded` avvia l'app;
  >     - il redirect reattivo va a `/`.
  >   - `layout.gate.test.ts` resta 3/3.
  >   - Il caso dell'Esc sul trigger in `ModalBase.escapeLayers.test.ts` è rosso: la lista resta aperta e la modale si
  >     chiude.
  >   - **Verifica di qualità**: il test-author ha provato i test su una cura usa e getta fuori dal worktree (59/59 verdi)
  >     e su cure sbagliate di proposito, e ognuna fa diventare rosso il test previsto.
  >   - Registrazioni: `internalPath.test.ts` in `core-unit`, `layout.authGate.test.ts` accanto a `layout.gate.test.ts`
  >     (`onboarding-component-unit`).
  > - **Lotto B** (test-author, corsia 6155): 4 test nuovi, tutti rossi sulla base.
  >   - `app-start-auth`, voce nuova in `front-utility`:
  >     - (a) `/auth/me` trattenuto: alla soglia dei 5 s la scia va a `/` e il pannello non c'è;
  >     - (b) senza sessione: `redirect` vale `null`;
  >     - (c) 401 a metà sessione: `redirect` vale `null`.
  >   - Backdrop in `support-copy-and-go.spec.ts`: finisce a 688 di 720 px su desktop e 708 di 740 su mobile (margine
  >     32 px), e il punto 2 px sopra il fondo colpisce la pagina sotto la modale.
  >   - I 12 test esistenti restano verdi.
  >
  > **⚠️ Fuori pista**:
  > - Il runner considera vecchia la build quando un file sotto `frontend/src` è più recente, test compresi.
  > - Per i rossi del lotto B il test-author ha portato avanti l'mtime di `build/index.html` e poi l'ha rimesso esatto al
  >   nanosecondo: la build corrispondeva già al prodotto di HEAD.
  > - Con la cura ho ricostruito io.
  > - **Decisioni prese in corso**:
  >   - Riprova è disabilitato solo mentre un check ha meno di 5 s; dopo torna disponibile, e una nuova Riprova supera il
  >     check in volo.
  >   - Un 401 all'avvio fa due `goto` allo stesso URL (la gestione dell'esito più il redirect reattivo), come i due
  >     `goto('/')` di oggi.
- [x] **19.4 Cura**: util, store, layout, pannello, root, intercettore, i18n, backdrop, Esc del trigger. ✅ 2026-10-08.
  > **Note implementazione**:
  > - `lib/utils/internalPath.ts` (nuovo):
  >   - `safeInternalPath`: un solo `/` iniziale, niente `\` né caratteri di controllo, e la stessa origine una volta
  >     risolto;
  >   - `loginUrl`.
  >   - `appBootstrap.svelte.ts` lo importa e perde la sua copia privata.
  > - `auth.ts`: tipo `AuthCheckResult`. Solo un `isAxiosError` con stato 401 azzera la sessione; ogni altro errore
  >   lascia lo store com'era, salvo `isLoading: false`.
  > - `(app)/+layout.svelte`:
  >   - la partenza unica è `checkAuthAndStart()`;
  >   - il timer dei 5 s mostra solo il pannello;
  >   - `superseded` è ignorato, e `startAuthenticatedApp()` contiene il flusso di oggi;
  >   - il redirect reattivo usa `loginUrl`;
  >   - nuovi rami `ServerUnreachable` e `app-auth-checking`, dopo quelli autenticati.
  > - `lib/components/layout/ServerUnreachable.svelte` (nuovo): `role="alert"`, testid e `data-busy`.
  > - `routes/+page.svelte`: `redirectTo = safeInternalPath(...)`; procede solo con `'authenticated'`.
  > - `zodios-client.ts`: 401 → `goto(loginUrl(path+query))`, salvo sulla root.
  > - `ModalBase.svelte`: `margin: 0` in `.modal-backdrop`.
  > - `SearchSelect.svelte`: Esc sul trigger a lista aperta, senza `inlineSearch`.
  > - i18n: `auth.serverUnreachable.title` e `.body` ×4 con `dev.py i18n add`; il registro è neutro rispetto al genere
  >   («la tua sessione non è stata chiusa»).
  > - **Esiti**:
  >   - vitest del lotto A: 5 file, 59/59;
  >   - `front build --debug` ok;
  >   - E2E `app-start-auth` 3/3, `support-copy-and-go` 14/14.
- [x] **19.5 Verifica** ✅ 2026-10-08, corsia 6155, un comando per volta.
  - `front build --debug`, `front check`;
  - `component-unit`, `core-unit`, `user-unit`;
  - E2E nuovi, più `auth`, `document-title`, `onboarding-tour`, `support-copy-and-go` e `select`.
  > **Note implementazione**:
  > - **Primo giro** (`/tmp/libreFolio_k19_gates.sh`):
  >   - `front check` 0/0;
  >   - `core-unit` 3430/3430, `component-unit` 2840/2840, `onboarding-component-unit` 418/418, `user-unit` 21/21;
  >   - E2E `document-title` 22, `onboarding-tour` 10, `select` 17, `multi-user` 2;
  >   - `check-orphans` ok;
  >   - **E2E `auth` 3 rossi su 28.**
  >
  > **⚠️ Fuori pista: una regressione introdotta dalla cura, trovata dal gate.**
  > - Un logout esplicito portava a `/?redirect=%2Fdashboard` invece che a `/`.
  > - Causa: `auth.logout()` gira lo store, e il redirect reattivo del layout scatta prima del `goto('/')` del logout,
  >   con `loginUrl`. Così la pagina dell'utente uscito passerebbe a chi entra dopo.
  > - Falliti: `logout returns to login page`, `3a` e `3b`, tutti in `auth-helpers.ts:47`.
  > - **Verdetto: difetto introdotto dalla cura.** Si conserva il comportamento di oggi per il logout voluto e quello
  >   approvato per una sessione finita.
  >   - Rosso (test-author): 6 casi in `auth.test.ts` e uno in `layout.authGate.test.ts`, più i 3 E2E già rossi.
  >   - Cura: `isSignOutRequested()` in `auth.ts`:
  >     - vero da `logout()`, impostato prima che lo store giri;
  >     - falso dopo un login, un check `authenticated` o un `reset()`;
  >     - un 401 non lo imposta.
  >   - Il redirect reattivo fa `goto(isSignOutRequested() ? '/' : loginUrl(...))`.
  >   - Il `$:` legacy compilato legge alla montatura tutti gli identificatori che nomina, quindi
  >     `layout.gate.test.ts` (di J e O) ha avuto bisogno di una voce nel mock: `isSignOutRequested: () => false`.
  >     L'ha aggiunta il test-author, senza toccare asserzioni.
  >
  > **Secondo giro**, dopo la cura del logout (`/tmp/libreFolio_k19_gates2.sh`, carico 15–20):
  > - `front build --debug` ok;
  > - `user-unit` 27/27, `onboarding-component-unit` 419/419, `component-unit` 2840/2840, nessun errore non gestito;
  > - E2E `auth` 28/28, `app-start-auth` 3/3, `document-title` 22/22, `onboarding-tour` 10/10.
  > - Prima della regressione erano già verdi: `support-copy-and-go` 14/14, `select` 17/17, `multi-user` 2/2,
  >   `core-unit` 3430/3430.
- [x] **19.6 Handoff**: CHECKPOINT READY, una frase di CHANGELOG per ciascun comportamento, FROZEN. ✅ 2026-10-08.
  > **Note implementazione**:
  > - Quattro commit proposti, con i messaggi in `/tmp/libreFolio_commits/` e il manifesto `k-19-manifest.txt`:
  >   1. `k-52`, auth;
  >   2. `k-53`, backdrop;
  >   3. `k-54`, Esc del trigger;
  >   4. `k-55`, journal.
  > - **File condivisi**:
  >   - `scripts/test_runner/_frontend_utility.py`: solo aggiunte, cioè 2 registrazioni più la voce `app-start-auth`;
  >   - i 4 cataloghi i18n: +4 righe ciascuno sotto `auth`. `dev_release2` (`58fc35174`) li ha cambiati dopo la mia
  >     base (+11/−3); `git merge-file` dà rc=0 su tutti e quattro, con JSON valido e la chiave presente.
  > - `layout.gate.test.ts` (di J e O): una sola voce nel mock.
  > - I passaggi `auth.serverUnreachable.*` sono testi nuovi per IT, FR ed ES: niente debito di traduzione nella doc.

## Definizione di fatto

1. Ogni test nuovo è rosso sulla base, per la ragione attesa, e verde dopo la cura.
2. I gate sono verdi e `front check` resta a 0/0.
3. Porte libere, nessun venv del worktree, nel worktree solo i file previsti.

## Seguito

- Lo step 20 estende l'Esc a SimpleSelect:
  [`plan-phase00TaxonomySelectStep20SimpleSelectEscape.prompt.md`](plan-phase00TaxonomySelectStep20SimpleSelectEscape.prompt.md).
