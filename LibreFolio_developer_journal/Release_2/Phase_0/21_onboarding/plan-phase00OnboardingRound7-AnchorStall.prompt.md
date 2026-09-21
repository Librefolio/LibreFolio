# Phase 0 - Onboarding Round 7: anchor stall

← Previous:
[Onboarding Round 6 — final UX](plan-phase00OnboardingRound6-FinalUX.prompt.md)

Contesto di review:
[Dossier di review onboarding](onboarding-review-dossier.md)

## Confine e autorizzazione

**Base:** `38d44b7172eb3cc01d86f6aba1147ed1afbd346a` — identica a `dev_release2`, 0 avanti / 0 indietro.

Il riallineamento è avvenuto in **fast-forward**, non in merge: `git log -1 --pretty=%p` mostra un
solo genitore (`e4cc808e8`). Non esiste un merge commit e non esiste una revisione combinata da
validare — il ramo **è** il target, bit per bit. Il rischio "due autori sulla route logic" non si è
materializzato qui; si materializzerà al primo checkpoint con commit propri.

**Branch:** `e-alfy-onboarding-foundation`.

**Lane:** porta 6158, data dir `/tmp/librefolio-r2-j-onboarding`.

**Coordinator:** `c8328a01-f208-4ade-a352-0486d1f14de2`.

**Autorizzazione developer verbatim, 2026-09-21:**
`chat, per me il piano è approvato, manca qualcosa?` e, sulla sequenza,
`Sì, sequenza confermata: R7 / R8 / R9 come proposto`.

**Decisione developer verbatim sul comportamento da implementare:**
`se dopo 3 secondi il componente non diventa disponibile, scriviamo di andare avanti che c'è stato
un problema di caricamento`

Nessun target merge, staging, commit/history, force, dato production o porta 6040/6041.

## Baseline attribuibile

Prima di scrivere una sola riga, con l'albero identico al target e **zero righe proprie**:

```
PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py test \
  --test-port 6158 --data-dir /tmp/librefolio-r2-j-onboarding \
  front-utility onboarding-component-unit
→ 12 file, 371 test, 371 passed, exit 0 reale (24s)
```

Serve a questo: ogni rosso successivo è attribuibile per differenza senza doverlo dimostrare.
L'exit code è stato letto **isolando il comando**, non attraverso `| tee | tail`, che restituisce
lo stato dell'ultimo elemento della pipe e non quello di `dev.py` — errore commesso e corretto
durante questo stesso step.

## Il difetto

Un anchor che non si risolve mai lascia il coachmark in attesa **per sempre**, e l'attesa è
mascherata da caricamento:

| Riga | Cosa fa oggi |
|---|---|
| `OnboardingCoachmark.svelte:117` | `guideState` cade su `'waiting'` |
| `:573` | render mostra `busyLabel` |
| `:376–386` | unico `setTimeout`, a 3000 ms imposta `baseSubdued = true` → **attenua l'overlay** |
| `:79` | `error` è **solo una prop**: il componente non può auto-promuoversi a errore |

L'attenuazione a 3 secondi rafforza l'illusione che qualcosa stia caricando. Non esiste timeout, non
esiste messaggio, non esiste uscita. **L'utente che aspetta, aspetta per sempre.**

È la classe di guasto peggiore fra quelle elencate nel dossier: non fallisce visibilmente, *riesce
in modo plausibile e sbagliato*.

## Contratti da preservare

- 15 flow finali, versionati separatamente.
- Import/Bulk step-managed.
- Nessun auto-advance non richiesto.
- Errori del controller devono restare distinguibili dai guasti di anchor.
- Desktop/mobile coerenti.
- Nessun edit al runner né ai cataloghi i18n (coordinator-owned).
- Chiavi PAC/Rebalancer di D intatte.

---

## Design

### D1 — Il rilevatore sta nel coachmark, non nell'host

Ci sono **due forme di guasto** e l'host ne vede una sola:

1. l'anchor non si registra mai → visibile a entrambi;
2. l'anchor si registra ma non si stabilizza mai → **solo il coachmark** possiede `targetStable`,
   `geometryState` e il settlement a due frame.

Mettere il rilevatore nell'host coprirebbe il caso 1 e lascerebbe scoperto il 2, che è quello che
produce l'attesa infinita più insidiosa (l'elemento c'è, quindi ogni diagnostica dice "tutto bene").

Il rilevatore è armato **solo mentre `guideState === 'waiting'`**.

### D2 — Serve un terzo stato, non il riuso di `error`

`error` è **già occupato**: `OnboardingOverlayHost.svelte:714` lo alimenta con gli errori di
controller e API. Riusarlo renderebbe un anchor mancante **indistinguibile da una transizione
fallita**, e potrebbe mascherare un errore API reale dietro un messaggio di caricamento.

```
guideState = error ? 'error'
           : stalled ? 'stalled'
           : anchored ? 'anchored'
           : 'waiting'

render      {error ?? (stalled ? stalledLabel : waiting ? busyLabel : description)}
```

Precedenza esplicita: **un errore reale batte sempre lo stallo.**

### D3 — Fade e stallo sono mutuamente esclusivi, non sommati

Il fade a `:382` **non può** fare da rilevatore: gira a ogni step, anche quando tutto funziona. E se
girassero entrambi, il pannello **attenuerebbe proprio il messaggio di guasto** — cioè peggiorerebbe
esattamente il sintomo che il round esiste per togliere.

Due costanti separate, entrambe 3000 ms oggi:

```
PANEL_FADE_MS  = 3000   // estetica, ogni step
GUIDE_STALL_MS = 3000   // diagnostica, solo in waiting
```

`stalled = true` è un cambio di dipendenza che **ri-esegue l'effetto fade e lo azzera**. Il messaggio
di stallo non viene mai attenuato.

`suspended` (modale sopra lo step) **mette in pausa** il conteggio dello stallo: un utente che apre
un dialog non sta subendo un guasto.

### D4 — L'arrivo tardivo si auto-guarisce

Fade e stallo hanno la stessa durata, quindi un anchor lento che arriva a 3,5 s **mostra prima il
messaggio di stallo**. L'arrivo dell'anchor porta `guideState` a `'anchored'` e azzera `stalled`, e
il messaggio sparisce da solo.

Uno stallo *latched* sarebbe un nuovo stato silenziosamente sbagliato — la stessa classe di difetto
che questo round elimina. **Va asserito, non dato per scontato** (caso di test 7).

### D5 — Nessun auto-advance, nessuna chiusura automatica, nessun flow abortito

Avanzare da soli sarebbe a sua volta un comportamento plausibile-e-sbagliato: l'utente non saprebbe
di aver saltato qualcosa.

- Il pulsante primario diventa **`Continue anyway`** → `next()` oppure `finish()` sull'ultimo step.
- In un flow step-managed lo step stallato viene registrato **`skipped`, non `completed`** —
  simmetrico alla scelta del developer sulla migrazione: `skipped` è veritiero, `completed` è una
  bugia comoda.

### D6 — Il restart-at-step-1 è un fix separato (R9)

`OnboardingOverlayHost.svelte:639` chiama `dismissHost({restartAtFirst: true})` sul mismatch di
route. È una **decisione di comportamento**, non un guasto, e la route logic ha ora un secondo
autore (`onboardingRouteSettlement.ts`, introdotto da `e38a521f0`, codice che J non ha scritto).
Bundlarlo qui mescolerebbe una correzione di difetto con un cambio di prodotto.

### D7 — i18n: batch misto, già applicato

| Chiave | Tipo |
|---|---|
| `onboarding.guide.loadProblem` | **nuova** |
| `onboarding.actions.continueAnyway` | **nuova** |
| `onboarding.settings.armedAtNextTrigger` | **riformulata** |
| `onboarding.settings.armedToast` | **riformulata** |

226 → **228** per locale. Applicato dal coordinator il 2026-09-21 e verificato al proprio HEAD:
228/228/228/228, `{flow}` intatto in tutte e 8 le riscritture.

Le due riformulazioni servono a togliere una **promessa falsa**: il replay vive in `sessionStorage`
e muore con la scheda, mentre il testo precedente lasciava intendere una durabilità che non esiste.
Dicono "in questa scheda" e non "in questa sessione" perché l'utente sa dove finisce una scheda e
non sa dove finisce una sessione. L'avvertimento sull'annullamento sta nella stringa **inline**, che
persiste in Impostazioni e si può rileggere; il **toast** dice solo dove vale, perché si mostra una
volta sola e non è rileggibile.

---

## Step

### Step 1 — Piano durevole, marcatori stantii, correzioni documentali

Creare questo file. Chiudere i 6 marcatori terminali stantii. Correggere i 2 punti di
documentazione stantii trovati durante l'analisi.

**Stato:** ✅ completato il 2026-09-21.

> **Note implementazione**: baseline attribuibile misurata prima di ogni edit (371/371, exit 0
> reale). Chiusi i 6 marcatori — base S13 (L607), R1 S7 (L197), R3 S9 (L452), R4 S10 (L425),
> R5 S11 (L405), R6 S9 (L186) — preservando lo stile di ciascun file (la base plan **non** usa ✅,
> i round sì). Corretto il docstring di `_grandfather_onboarding_for_test_users` in
> `populate_mock_data.py`, che descriveva la 003 come "grandfathers into every current flow as
> completed" mentre al target semina `welcome=completed` e guide/step `skipped`. Corretti il §3.3 e
> lo scenario E2 del dossier.
>
> **⚠️ Fuori pista**: il §3.3 del dossier non era solo stantio, era **stantio su un punto che il
> developer aveva già approvato**. Aveva letto che gli utenti esistenti ricevono il tour e ha
> risposto che va bene che *non* lo ricevano — cioè ha detto sì al comportamento giusto leggendo la
> descrizione di quello opposto. Le due cose coincidono per fortuna. Scritto nel dossier come
> avvertimento esplicito, perché fra sei mesi quella riga sembrerebbe una conferma informata e non
> lo è: è una decisione non validata che si dà il caso sia corretta.
>
> **⚠️ Fuori pista**: primo tentativo di baseline fallito con `invalid choice: 'front'` — la
> categoria è `front-utility`. La pipe `| tee | tail` ha restituito **exit 0** su un comando
> fallito, terza occorrenza in giornata di un numero reale che misura la cosa accanto. Rilanciato
> isolando lo stato.
>
> **⚠️ Fuori pista**: il mio primo script di ri-audit cercava `completato` e riportava 2 step
> aperti. Uno dei due era R2 S7, che scrive `completata` al femminile. **Lo stesso identico difetto
> che avevo denunciato nel §1 sul `grep '✅'`**, commesso da me mentre verificavo di averlo
> risolto: un controllo che funziona per una proprietà accidentale del caso — lì il simbolo scelto
> dall'autore, qui la desinenza. Rifatto con block-parse su ogni `### Step` e match su `complet`.
>
> **Evidenze di gate**: `dev.py lint` → exit 0 reale, *All checks passed*.
> `black --check` su `populate_mock_data.py` → exit 0, *1 file would be left unchanged*.
> Marcatori stantii residui: **0**. Audit finale su 7 piani:
> **71 step, 69 completi, 2 superseded per decisione, 0 realmente aperti.**
> Cross-link `→ Follow-up` aggiunto in Round 6 secondo la convenzione dei round precedenti.

### Step 2 — Batch i18n

**Stato:** ✅ completato il 2026-09-21 dal coordinator (shared writer). 226 → 228 × 4, verificato
al proprio HEAD dopo il fast-forward, non dedotto dalla riuscita del riallineamento.

### Step 3 — `OnboardingCoachmark.svelte`

Stato `stalled`, effetto di stallo armato solo in `waiting`, pausa su `suspended`, mutua esclusione
col fade, `guideState = 'stalled'`, precedenza di render, fallback centrato quando
`anchorRect === null`.

> Da confermare all'implementazione, non assumere: che `resolvePanelGeometry()` centri davvero
> quando `anchorRect` è `null`. Va asserito.

**Stato:** ✅ completato il 2026-09-21.

> **Note implementazione**: 7 modifiche su `OnboardingCoachmark.svelte` (26 ins / 4 del).
> Props `stalledLabel?: string` e `onstall?: () => void`; stato `stalled = $state(false)`;
> costanti separate `PANEL_FADE_MS` / `GUIDE_STALL_MS` (entrambe 3 000 ms, ma nomi distinti
> perché misurano cose diverse: una è estetica e vale per ogni step, l'altra è diagnostica e
> si arma solo in attesa). `guideState` ora verifica `anchored` **prima** di `stalled`, così
> un anchor che arriva tardi si auto-guarisce per struttura invece che per reset. L'effetto di
> stallo legge `anchorRect`/`targetStable`, quindi si ri-esegue e azzera `stalled` da solo
> quando la geometria si assesta: nessun residuo di stato. Scrive `stalled` senza leggerlo →
> nessun loop reattivo. L'effetto di fade ora legge `stalled` ed esce subito: il pannello non
> attenua mai il messaggio di guasto, che era il punto di partenza del round.
>
> **Ipotesi del piano verificata, non assunta**: `resolvePanelGeometry()` centra davvero con
> `anchorRect === null` — riga 183, `if (!target || viewportWidth === 0 || viewportHeight === 0) return centered;`.
>
> **Verifica che valeva più della precedente**: `anchorId` è dichiarato `anchorId: string`
> (obbligatorio, `OnboardingOverlayHost.svelte:17`), e `intro.scene` — l'unico step di apertura
> che poteva essere legittimamente senza anchor — è renderizzato da `OnboardingIntroScene.svelte`
> e non dalla coachmark (`:691`, escluso anche da `activeSteps` a `:569`). Quindi **non esiste
> uno step coachmark senza anchor per disegno**, e lo stallo non può mai accusare di guasto uno
> step che funziona. Se `anchorId` fosse stato opzionale, questo fix avrebbe prodotto
> esattamente il "plausibile ma sbagliato" che il dossier §5 elenca come classe peggiore.
>
> Gate statici: `prettier --check` sul file exit 0; `svelte-check` 0 errori su onboarding.

> **⚠️ Fuori pista**: 4 test rossi su `OnboardingCoachmark.test.ts`, tutti nel blocco
> *message opacity lifecycle*, tutti `data-subdued` atteso `true` e ricevuto `false` a 3 000 ms:
> 1. `keeps the base panel fresh through 2,999ms and subdues it at 3,000ms`
> 2. `restores opacity for hover/focus, then immediately re-subdues on leave/blur without another timer`
> 3. `resets the base state and the full 3-second deadline when the step or error changes`
> 4. `keeps the same timer and interaction state under reduced motion`
>
> Causa **provata dalla suite esistente**, non dedotta: montando *con* anchor il componente è
> `data-guide-state='waiting'` e `data-target-stable='false'`, e resta instabile anche dopo due
> rAF (`OnboardingCoachmark.test.ts:444-449`) — la stabilità richiede il `transitionend`. Quei
> 4 test non assestano mai la geometria, quindi restano in `waiting` per tutti e 3 i secondi:
> una condizione che per uno step sano **non può durare così a lungo in un browser vero**,
> dove la geometria si assesta in millisecondi. Lo stallo scatta e sopprime il fade, che è il
> comportamento voluto.
>
> Quindi il prodotto è corretto in entrambi i casi reali e sono i test a codificare il mondo
> precedente: vanno fatti assestare prima di avanzare a 3 s. Riparazione delegata a
> `test-author` nello Step 6 insieme ai casi nuovi, per non passare due volte sugli stessi file.
> Fino ad allora la suite ha **esattamente questi 4 rossi nominati**: un quinto rosso è nuovo
> ed è mio. Baseline attribuibile per nome, non per totale.

> **⚠️ Fuori pista — segnalazione mia, poi RITRATTATA: i 130 errori non esistono nel prodotto**.
> `npm run check` sul mio albero dava 130 errori / 41 warning in 18 file, zero onboarding, quasi
> tutti `features/tools/*` e `pac-allocator/*`. L'avevo segnalato al coordinator come debito del
> target a `38d44b717`, da girare a D. **Era falso.** Sullo stesso SHA, nel checkout del
> developer, svelte-check dà **3 errori / 41 warning / 4 file**.
>
> Causa, verificata da me nel mio albero e non solo riferita: `frontend/src/lib/api/generated-tools.ts`
> è **ignorato** (`frontend/src/lib/api/.gitignore:2`) e **non tracciato**. Il mio ne aveva 668
> righe contro 1 017 del target: il file generato nel mio worktree non sa che quel tool esiste,
> da cui tutti gli errori
> `Type '"portfolio_rebalancer"' does not satisfy the constraint '"pac_allocator"'`. Un file
> ignorato non viaggia col merge, quindi non ha affatto una "versione del target": ogni worktree
> ha la propria, dipendente da quando ci è passato un `api sync`.
>
> **La regola**: un SHA identifica l'albero *versionato*, non l'*ambiente*. Dove un file generato
> e ignorato entra nel risultato, due checkout allo stesso commit misurano cose diverse, e il
> commit non può dirlo — perché il file in questione è esattamente quello di cui git non tiene
> conto.
>
> **E il difetto di metodo, che è peggiore del numero sbagliato.** Avevo applicato la disciplina
> giusta: ho rifiutato di attribuire per differenza e sono andato a guardare file per file,
> proprio perché svelte-check non era nel baseline `371/371`. La disciplina era corretta e mi ha
> portato lo stesso a una conclusione falsa, perché presuppone una cosa che non avevo verificato:
> **che l'albero su cui misuro sia l'albero che credo**. Avevo `git status --porcelain` pulito e
> l'ho letto come "allineato" — ma `status` per costruzione **non riporta i file ignorati**,
> quindi lo strumento con cui certificavo l'allineamento è cieco proprio alla classe di file che
> mi aveva disallineato.
>
> E i **41 warning identici** hanno fatto da garante ai 130 errori: una coincidenza parziale su
> una misura lunga chiude la domanda "sto misurando la cosa giusta?" prima che venga posta. È la
> stessa forma del `63` coincidente del coordinator. La coincidenza parziale è l'unico segnale
> che abbiamo per dire "siamo allineati" e **non distingue fra allineamento e coincidenza**.
>
> **E la prova che avevo portato era vuota — ritrattata anche quella, non solo il numero.**
> Avevo scritto al coordinator: «`grep -c portfolio_rebalancer` → 0, è la prova diretta». Quel
> grep **non poteva dare altro che zero, in nessun file, mai**: in `generated-tools.ts` i nomi dei
> tool sono **esadecimati** dentro gli identificatori generati
> (`ToolC7061635f616c6c6f6361746f72V312e302e30Input`, dove `7061635f616c6c6f6361746f72` è
> `pac_allocator`). La stringa in chiaro non compare nel file nemmeno quando il tool c'è.
>
> Il controllo che sarebbe bastato, e che non avevo fatto, è di una riga: **girare il matcher su
> qualcosa che so essere presente.** Misurato dopo:
>
> ```
> grep -o 'pac_allocator'                        generated-tools.ts →   0
> grep -o '7061635f616c6c6f6361746f72'           generated-tools.ts → 353
> grep -o '706f7274666f6c696f5f726562616c616e636572' generated-tools.ts →   0
> ```
>
> Il matcher in chiaro dà **0 anche per `pac_allocator`**, che nel file c'è 353 volte. Un
> matcher che risponde `0` alla cosa che so esserci non può dirmi niente sulla cosa che sto
> cercando. La conclusione resta giusta — il Rebalancer nel mio file davvero non c'è, misurato
> col matcher esadecimale verificato — ma **lo era per un fatto sul mondo, non per la prova che
> avevo portato**.
>
> **La forma del difetto**: due ragioni distinte producevano lo stesso `0` — la codifica (il
> grep non poteva trovare la stringa comunque) e il fatto (quel tool lì non c'è davvero). Dall'output
> **sono indistinguibili**, e nessuna rilettura più attenta dello stesso numero le separa: serviva
> una misura *diversa*, non una lettura migliore. Un numero non porta scritto quale delle due
> cose sta dicendo.
>
> **Regola riusabile**: un matcher va validato su un positivo noto prima di credere a un suo
> negativo. Un `0` da un matcher mai validato non è una misura, è l'assenza di una misura — e le
> due si scrivono identiche.
>
> **Corollario operativo su `status`**: la versione utile della regola dei file ignorati è
> `git status --porcelain --ignored` prima di ogni checkpoint. `--porcelain` da solo risponde a
> una domanda più piccola di quella che sembra, e la differenza non si vede dall'output.
>
> Conseguenza pratica: nessun debito da assegnare a D, e la segnalazione è stata fermata dal
> coordinator prima di arrivargli — D avrebbe cercato per ore qualcosa che non esiste. I 3
> errori veri (`ToolExecutionMetrics.svelte:44:55` e due in `TransactionFormModal.test.ts`) non
> sono miei. Per R7 non serve un `api sync` locale: i file onboarding sono puliti in **entrambe**
> le misure, che è l'unica cosa che il checkpoint deve dimostrare.

### Step 4 — `OnboardingOverlayHost.svelte`

Gestione `onstall`, `Continue anyway` → `next()` / `finish()`, skip per step in flow step-managed,
wiring delle label.

> Da confermare all'implementazione: che il percorso di skip per singolo step sia raggiungibile
> direttamente per il caso "step stallato dentro flow step-managed".

**Stato:** ✅ completato il 2026-09-21.

> **Note implementazione**: `stalledStepId = $state<GuideStepId | null>(null)` più
> `stalled = $derived(active != null && stalledStepId === active.stepId)`. Scelta deliberata
> di tracciare **quale** step è andato in stallo invece di un booleano con effetto di reset:
> così il flag si auto-invalida quando lo step cambia, senza un secondo effetto che possa
> sfasarsi. `handleStall()` registra lo step corrente; `onstall={handleStall}` sulla coachmark.
>
> **Il caso peggiore trovato durante l'implementazione, non previsto dal piano**: in
> `import_guide` la derived `showNext` era `false` per ogni step tranne `import.bulk`. Quindi
> uno step in stallo dentro la guida import non offriva **nessun** comando di avanzamento —
> solo Chiudi. È la forma più grave del blocco descritto dal coordinator, ed era invisibile
> finché non si guardava la derived. `showNext` ora è `stalled || …`: il pulsante compare
> comunque quando serve davvero.
>
> `nextLabel` diventa `onboarding.actions.continueAnyway` in stallo; `showNextArrow` è
> disattivata perché la freccia promette una sequenza che qui non si sta seguendo.
> `stalledLabel={translate('onboarding.guide.loadProblem')}`.
>
> **Persistenza — simmetrica alla scelta del developer sulla migrazione 003**: in `handleNext`,
> se `stalled && isStepManagedFlow(flow)` si chiama `onboardingGuide.skip()` invece di
> proseguire verso `finish()`. Ragione: `lastStep` è sempre `true` per i flussi step-managed
> (`:580`), quindi senza questo ramo un passo fallito sarebbe stato registrato come
> `completeStep` — cioè marcato **completato** uno step che l'utente non ha mai visto.
> `skip()` instrada su `controller.skipStep` (`onboardingGuide.svelte.ts:388`), quindi il passo
> resta `skipped`: vero, e distingue "saltato per guasto" da "fatto". `completed` sarebbe stata
> una bugia comoda, esattamente quella che il developer ha rifiutato per il backfill.
>
> **Domanda aperta del piano, ora risolta misurando**: sì, esiste un percorso di skip per
> singolo step raggiungibile da un flusso step-managed — è il ramo `isStepManagedFlow` dentro
> `skip()`. Non andava assunto e infatti non lo era.
>
> Per i flussi a sequenza il comportamento resta quello naturale (`next()` / `finish()`): lì la
> persistenza è a livello di flusso, e saltare il flusso intero perché un passo non si è
> ancorato sarebbe stato sproporzionato.
>
> L'`actionHint` non richiede modifiche: era già vincolato a `guideState === 'anchored'`
> (`OnboardingCoachmark.svelte`), quindi in stallo sparisce da solo. Verificato leggendo la
> riga, non dedotto — un suggerimento del tipo "usa l'azione nel wizard" riferito a un elemento
> che non esiste sarebbe stato peggio del silenzio.
>
> Gate: `prettier --check` su entrambi i file exit 0. Suite `onboarding-component-unit`
> **367 passati, esattamente i 4 rossi già nominati nello Step 3, nessun quinto**. È la
> differenza che conta: l'assenza di regressione è affermata per nome dei test, non per totale.

> **⚠️ Fuori pista — il coordinator chiede di misurare il simmetrico di `handleRecover()`
> incondizionato; il simmetrico non c'è, ma la misura ne scopre un altro che c'è.**
>
> Domanda posta: avendo tolto la guardia `stalledStepId === active.stepId`, un `onrecover`
> proveniente da uno step già abbandonato può azzerare lo stallo dello step *corrente*?
>
> **Misurato, non ragionato.** Il coachmark è **un'istanza sola** (`OnboardingOverlayHost.svelte:708`),
> **non** dentro un `{#key}`: al cambio step i prop si aggiornano sotto la stessa istanza. Lo stallo
> vive in **un solo `$effect`**, il cui corpo esegue in quest'ordine:
> `stalled = false` → `if (wasStalled) onrecover?.()` → `setTimeout(GUIDE_STALL_MS)`.
> Quindi il recover dello step abbandonato e l'armamento del timer del nuovo step avvengono nello
> **stesso corpo sincrono**, recover per primo, e comunque **3 000 ms prima** che un nuovo stallo
> possa esistere; il timer vecchio lo chiude il cleanup dell'effect stesso. Non esiste
> interleaving in cui un recover stantio atterri dopo uno stallo fresco. **Impossibile per
> struttura, non per fortuna** — ed è la ragione per cui vale la pena averlo misurato: una
> risposta "non può succedere" senza il *perché* strutturale invecchia al primo `{#key}` che
> qualcuno aggiunge.
>
> **Ma la stessa misura scopre il caso realmente rotto, che nessuno aveva chiesto.** Il coachmark
> si **smonta** quando `active` diventa `null` (`:707 {:else if active && step}`) o quando lo step
> passa a `intro.scene` (`:705`). Allo smontaggio Svelte esegue il **cleanup** dell'effect — che è
> `clearTimeout` e **basta**: `onrecover` **non parte**. E l'host non è effimero: è montato in
> `routes/(app)/+layout.svelte:230`, quindi `stalledStepId` sopravvive per l'intera sessione
> autenticata, attraverso chiusure e riavvii della guida.
>
> Sequenza reale: step A va in stallo → l'utente **esce** dalla guida (`showClose={true}`) →
> `stalledStepId` resta `'A'` → **replay da Impostazioni** → si torna su A →
> `stalled = $derived(active != null && stalledStepId === active.stepId)` è **vero dal primo
> frame, senza alcuno stallo**. Il pannello mostra subito il messaggio di problema di caricamento
> e «Continua comunque», `showNextArrow` è falso, e `handleNext()` prende il ramo di skip:
> **persiste `skipped` uno step che in questo giro non è mai stato nemmeno tentato.**
>
> È esattamente la classe che nel dossier avevo indicato come la più costosa — *produce
> silenziosamente un comportamento plausibile e sbagliato invece di fallire visibilmente* — e
> peggiora per **dove** capita: mente sul **percorso di replay**, cioè quello che il developer
> userà per rivedere la feature. Un difetto che si manifesta solo durante l'ispezione è il
> peggiore che si possa lasciare in giro.
>
> **Forma del difetto**: sempre la stessa, terza volta oggi — **due proprietari di un solo fatto**
> (`stalled` nel coachmark, `stalledStepId` nell'host) e un cammino che ne azzera uno solo. Le
> prime due volte il cammino era `suspended` e il cambio step; questa è lo **smontaggio**.
>
> **Correzione progettata (implementazione dopo il rientro di `test-author`, per non scrivere
> sotto i piedi di chi sta scrivendo i test):** l'host possiede `stalledStepId`, quindi l'host
> deve invalidarlo quando cambia l'identità a cui è agganciato — non delegarlo al figlio, che
> allo smontaggio non può più parlare.
>
> **La guardia non è cosmetica, ed è il punto che conta.** La forma ingenua
> — un `$effect` che fa `void active?.stepId; stalledStepId = null;` — **reintroduce la classe di
> bug che sta correggendo**: `active` è un oggetto derivato, e se viene sostituito con uno nuovo
> che porta lo *stesso* `stepId` (aggiornamento di `progress`, di `actionPending`) l'effect
> ri-esegue e **azzera uno stallo legittimo e in corso**; il coachmark non ri-arma, perché il suo
> timer è già scattato. Risultato: pannello in attesa per sempre — il bug di partenza, rientrato
> dalla porta della correzione. Il confronto va fatto **sugli id**, con `untrack` per non leggere
> in modo reattivo lo stato che l'effect stesso scrive:
>
> ```js
> $effect(() => {
>     const current = active?.stepId ?? null;
>     const marked = untrack(() => stalledStepId);
>     if (marked !== null && marked !== current) stalledStepId = null;
> });
> ```
>
> **⚠️ SUPERATA — questa §4 è stata scartata dopo una controproposta del coordinator, verificata
> da me riga per riga.** La lascio scritta perché la trappola che descrive resta vera e perché
> l'errore di progetto che conteneva è più istruttivo della soluzione.
>
> **L'incoerenza fra la mia diagnosi e la mia cura.** Avevo appena scritto *«non sto trovando tre
> bug, sto trovando tre volte lo stesso, perché la correzione sposta il confine invece di
> toglierlo»* — e poi ho proposto **un quarto confronto nell'host**, cioè l'ennesimo spostamento
> del confine. Lasciava in piedi i **due proprietari** e affidava la coerenza a una condizione da
> mantenere vera per sempre: il quinto cammino che nessuno ha ancora immaginato l'avrebbe trovata
> di nuovo scoperta. **Avevo la diagnosi giusta in mano e ho curato il sintomo.**
>
> **Controproposta adottata: la morte dello stallo la dichiara chi la nascita l'ha annunciata.**
> Il cleanup dell'`$effect` di stallo, nel coachmark, chiude anche il fatto:
>
> ```js
> return () => {
>     window.clearTimeout(timer);
>     if (untrack(() => stalled)) onrecover?.();
> };
> ```
>
> e il corpo perde `wasStalled`, riducendosi a `stalled = false;`: il cleanup gira **prima** del
> corpo a ogni ri-esecuzione, quindi la dichiarazione nel corpo era ridondante. **Un solo
> proprietario, un solo punto di dichiarazione per ciascuna transizione** — il confine è tolto,
> non spostato. La trappola dell'`active` rinnovato con lo stesso `stepId` **non si pone**:
> `stepId` è un prop primitivo, stesso valore ⇒ nessuna ri-esecuzione, e comunque non c'è più
> nessun confronto di id da sbagliare.
>
> **Le tre domande che decidevano, verificate e non accettate:**
>
> 1. *Il cleanup è di quell'effect?* Sì, ed è protetto da un invariante misurato: `stalled` ha
>    **esattamente tre siti** (`:116` dichiarazione, `:405` `false`, `:409` `true`), e il solo
>    scrittore di `true` è il timer, che **esiste unicamente sul cammino che registra il
>    cleanup**. Quindi `stalled === true` ⟹ **un cleanup è registrato**, sempre. Il ramo di
>    early-return non può mai lasciare uno stallo senza cleanup, perché ogni ri-esecuzione
>    azzera `stalled` *prima* di poter uscire.
> 2. *`onrecover?.()` allo smontaggio è sicuro?* Sì. L'host **non** passa alcun prop `stalled` al
>    coachmark — usa il proprio solo per `nextLabel` (`:724`) e `showNextArrow` (`:725`), che non
>    sono dipendenze dell'effect di stallo. **Nessun anello di retroazione.** Che il teardown
>    giri allo smontaggio non lo prendo dalla documentazione ma dal codice stesso: l'effect del
>    click sull'anchor (`:378-384`) affida a quel teardown il `removeEventListener`, e se non
>    girasse quel listener resterebbe appeso — cioè il progetto esistente **già scommette** su
>    quella semantica.
> 3. *Esiste uno smontaggio senza che l'utente esca?* **Sì, due**, e qui la verifica ha cambiato
>    il verdetto rispetto all'attesa: `dismissHost()` fa `replaceActive(null)`
>    (`onboardingGuide.svelte.ts:301`), ed è chiamato sia dal disallineamento di rotta
>    (`OnboardingOverlayHost.svelte:641`, con `restartAtFirst`) sia da `suspend()` (`:307`). In
>    **entrambi** azzerare è il comportamento **giusto**: la guida riparte dal primo step o viene
>    congedata, e conservare lo stallo farebbe apparire lo step *già fallito* alla ripresa, senza
>    aver atteso nulla. Le due eccezioni **rafforzano** la proposta invece di affondarla — ed è
>    la ragione per cui andavano cercate: una domanda posta per confutare che torna a favore vale
>    più di una conferma cercata.
>
> **Limite dichiarato**: tutto sopra è verificato **staticamente**. La prova comportamentale è il
> test *stallo → smontaggio → rimontaggio sullo stesso step*, che deve mostrare lo step
> **normale** al primo frame. È un test sul **comportamento**; il test che avrebbe accompagnato
> la §4 sarebbe stato un test sul **confronto di id**, cioè sull'implementazione — e sarebbe
> rimasto verde anche il giorno in cui il confronto diventa quello sbagliato.

### Step 5 — `OnboardingReplaySection.svelte`

Copy di conferma veritiero. Possibile che non serva alcun edit di codice se le chiavi riformulate
bastano: **verificare, non presumere**.

**Stato:** ✅ completato il 2026-09-21 — **nessuna modifica di codice necessaria**.

> **Note implementazione**: verificato estraendo tutte le chiavi `onboarding.*` usate dal
> componente e risolvendole contro `en.json`. Il batch i18n ha cambiato **valori**, non nomi di
> chiave, quindi `onboarding.settings.armedToast` e `onboarding.settings.armedAtNextTrigger`
> continuano a risolvere e mostrano la formulazione nuova senza toccare il `.svelte`.
> L'ipotesi del piano era corretta, ma è stata confermata misurando.

> **⚠️ Fuori pista (falso positivo mio, vale la pena registrarlo)**: il primo scan ha riportato
> due chiavi mancanti, `onboarding.replay.armed` e `onboarding.replay.cancelled`, con
> `onboarding.replay` effettivamente vuoto in `en.json`. Sembrava un difetto vivo: UI che
> mostra il nome grezzo della chiave. Non lo è. Alle righe 81 e 101 quelle stringhe sono il
> campo `name:` di `notify()` — **identificatori di evento**, non chiavi di traduzione; le
> traduzioni vere stanno nel `toast.message` accanto. Il mio scan aveva cercato *letterali che
> somigliano a chiavi* e io avevo letto il risultato come *chiavi mancanti*: la stessa forma
> del file-contro-contenuto e dell'edit-contro-cancellazione, cioè una misura reale che risponde
> alla domanda adiacente. Ero a una frase dal segnalarlo al coordinator come difetto.

### Step 6 — Test via `test-author`

- **A — componente, 7 casi**: anchor mai registrato; anchor registrato mai stabile; stallo non
  attenuato; errore controller batte stallo; `suspended` mette in pausa; Continue chiama
  `next()`/`finish()`; **arrivo tardivo azzera lo stallo**.
- **B — host, 3 casi**: step stallato in flow step-managed persiste `skipped`; ultimo step chiama
  `finish()`; errore reale non sostituito.
- **C — E2E, 1 caso × desktop/mobile**: anchor che non arriva mai.

Il caso "anchor che non arriva mai" è **la classe che gli unit test attuali non vedono**: vanno
montati con un target che non si registra, non con uno che tarda.

**Stato:** ✅ completato il 2026-09-21. E2E inizialmente rinviato, poi **eseguito e verde** nello
Step 7 (10/10): vedi la nota di superamento in fondo.

> **Note implementazione**: due delegazioni a `test-author`, entrambe con lane 6158 e
> restrizioni esplicite. Prima tornata: riparazione dei 4 rossi nominati nello Step 3 più
> 14 casi nuovi (11 componente + 3 host). Suite da `4 failed | 367 passed` a
> **`12 file / 385 test passati`, exit 0 isolato**.
>
> La riparazione dei 4 non è stata un adeguamento delle asserzioni: `test-author` ha aggiunto
> `settleCoachmarkGeometry()`, che **asserisce** `anchored` + `target-stable` + `geometry-state
> stable` come precondizione invece di darla per scontata, e `advanceFakeClockTo(instant)`, che
> avanza a un istante assoluto invece che di un delta. Il secondo helper chiude un difetto
> reale che avevo mancato io: l'assestamento consuma due o più frame dei 3 000 ms sotto esame,
> quindi un `advanceTimersByTime(2_999)` dopo l'assestamento sarebbe atterrato a ~3 095 ms e non
> avrebbe più misurato il confine. Il confine 2 999/3 000 è preservato, non ammorbidito.
>
> - **A — componente, 11 casi** (previsti 7): i 7 del piano più stallo non attenuato anche a
>   12 s, `onstall` una volta sola e non di nuovo a 15 s, errore tardivo che scavalca uno stallo
>   già presente, e `actionHint` assente in stallo **ma presente una volta ancorato** — la
>   barriera di presenza che impedisce al negativo di passare a vuoto.
> - **B — host, 3 casi**: uno step `import.analyze` in stallo passa da *nessun comando di
>   navigazione* a un pulsante `onboarding.actions.continueAnyway` senza freccia, e il clic
>   chiama `skip()` una volta sola, mai `finish()`/`next()`; uno step a flusso cambia solo la
>   formulazione e chiama `next()`; uno step **ancorato** allo stesso istante 3 000 ms non
>   ottiene alcun comando — cioè il controllo dev'essere causato dallo stallo, non dall'orologio.
>
> Non c'è file di test dedicato all'host: i suoi unit test vivono già dentro
> `OnboardingCoachmark.test.ts`, quindi i casi host stanno lì.
>
> **Nessuna categoria di test registrata**: i casi nuovi stanno in un file già coperto da
> `onboarding-component-unit`, quindi `scripts/test_runner/_frontend_utility.py` **non è
> toccato** — verificato con `git status --porcelain scripts/test_runner/` = 0 path. La
> superficie contesa segnalata dal coordinator resta libera.
>
> **Terza tornata (2026-09-21), dopo il cambio di contratto**: riusato l'agente esistente invece
> di aprirne uno nuovo — divergenza dalla preferenza del coordinator, **dichiarata e argomentata,
> non applicata in silenzio**. Ragione: la conoscenza di harness accumulata (`rerender` che
> **fonde** i prop, rAF escluso dai fake timer, `geometry-state` che riporta `stable` ~32 ms
> **dopo** il recupero reale, più i due helper) era costata due rossi, e un agente nuovo avrebbe
> dovuto riscoprirla. Rischio di appiattimento mitigato **specificando il contratto invece del
> tema**: smontaggio reale e non `rerender`, asserzione sul **fronte** di smontaggio e non sullo
> stato al rimontaggio.
>
> Esito: **12 file / 395 test passati, exit 0 isolato**, prettier pulito, solo file di test —
> verificato da me con `git diff --stat`, che mostra i due `.svelte` modificati da me e nessun
> altro file di produzione toccato.
>
> - **Rinomina**: 41 siti (38 identificatori + 3 menzioni in prosa). Rinominato anche il blocco
>   `— stall recovery` → **`— stall end protocol`**, con la docstring riscritta per elencare
>   **destroy** come quinto modo in cui uno stallo finisce.
> - **La verifica che contava**: gli 8 test di fronte preesistenti hanno asserzioni esatte
>   `toHaveBeenCalledTimes`, e **tutte e 8 restano identiche e verdi** sotto la forma nel
>   cleanup. Era la domanda che avevo posto — *uno scostamento di uno sarebbe stata una
>   scoperta vera* — e la risposta è che il cambio è **conservativo su ogni cammino coperto**.
> - **Due casi nuovi di ciclo di vita** (393 → 395): stallo → `view.unmount()` **reale** →
>   `onstallend` una volta sola **sullo smontaggio**, poi istanza nuova sullo stesso `stepId` con
>   `waiting` a `+2_999` e `stalled` a `+3_000`, cioè **scadenza fresca intera**. E il negativo
>   con barriera di presenza: uno step ancorato vive fino a `+6_000` (il doppio della propria
>   scadenza) e smonta in silenzio — senza il quale *«scatta sullo smontaggio»* e *«scatta su
>   ogni smontaggio»* sarebbero indistinguibili.
>
> **Una sua asserzione corretta da lui stesso, e la correzione è il test migliore**: aveva
> asserito che il pannello rigiocato mostra `DESCRIPTION_TOKEN`; mostra `BUSY_LABEL_TOKEN`,
> perché il messaggio ordinario di uno step non ancorato **è** l'etichetta d'attesa e la
> descrizione compare solo una volta ancorati. La tesi che conta è il **contrasto fra i due
> messaggi ad anchor assente**: il replay deve mostrare `waiting`, non `loadProblem`. Asserire
> l'etichetta d'attesa fissa esattamente quello, e tornerebbe rossa se un flag stantio
> riarmasse la formulazione di stallo.

> **⚠️ Fuori pista — difetto di produzione mio, trovato da `test-author` e corretto**:
> `stalledStepId` non veniva mai azzerato quando lo step si auto-guariva. La coachmark azzera il
> proprio `stalled` appena la geometria si assesta (per costruzione, `anchored` è valutato prima
> di `stalled`), ma non esisteva alcun controcanto di `onstall`: l'host restava con
> `stalled === true` per sempre su quello step. Raggiungibile davvero, non teorico —
> `guideAnchors.revision` è `$state`, quindi un anchor che monta tardi si propaga.
>
> Conseguenza grave: `handleNext()` continuava a instradare su `onboardingGuide.skip()`, cioè
> **persisteva come `skipped` uno step che l'utente poteva ormai eseguire**. È la stessa
> categoria di bugia che il developer ha rifiutato per il backfill della 003, col segno
> invertito: là si sarebbe marcato `completed` ciò che non fu mai offerto, qui si marcava
> `skipped` ciò che l'utente stava per fare.
>
> Correzione: prop `onrecover?: () => void` simmetrica a `onstall`, innescata solo sulla
> transizione vera stallo→assestato — `const wasStalled = untrack(() => stalled);` perché
> leggere `stalled` dentro l'effetto che lo scrive creerebbe un ciclo reattivo. Lato host,
> `handleRecover()` azzera `stalledStepId`.
>
> **Decisione d'interfaccia presa da me, e va attribuita**: allo sblocco si torna
> *completamente* alla normalità — etichetta, freccia e percorso di `handleNext()`. Tre ragioni.
> La coachmark ripristina già `description` da sola, quindi lasciare "Continue anyway" avrebbe
> reso il pannello contraddittorio con sé stesso: il testo dice che lo step funziona, il
> comando dice che qualcosa è andato storto. Il risultato persistito deve seguire l'azione
> reale. E l'obiezione "non togliere un comando che l'utente sta per premere" è circoscritta,
> perché lo sblocco è già una transizione visibile (torna la descrizione, compaiono highlight e
> puntatore): il comando che cambia insieme al resto è coerente, non sorprendente.
>
> **Alternativa valutata e scartata**: una guardia difensiva lato host che rifiuti lo skip
> quando `anchor != null`. Avrebbe sbagliato bersaglio sulla seconda forma di guasto — anchor
> che si registra ma non si stabilizza mai — trasformando uno stallo genuino in un `completed`.
> Una guardia con semantica sbagliata è peggio di nessuna guardia: la difesa giusta è un test
> che diventa rosso se il wiring marcisce, ed è la seconda delegazione.

> **⚠️ Fuori pista — il buco che avevo appena introdotto correggendo il buco precedente**:
> la prima versione di `onrecover` era `if (wasStalled && settled) onrecover?.()`, cioè innescata
> solo sulla transizione stallo→assestato. Rivedendola a freddo prima che i test la fissassero,
> ho trovato una sequenza raggiungibile che la aggira: step in stallo → l'utente apre una modale
> → `suspended` diventa vero → l'effetto si ri-esegue e azzera il proprio `stalled`, ma `settled`
> è ancora falso quindi `onrecover` **non parte** → la modale si chiude, l'anchor arriva e si
> assesta → `wasStalled` è ormai falso → `onrecover` **non parte più affatto**, e l'host resta
> in stallo per sempre.
>
> Cioè: esattamente il difetto segnalato da `test-author`, spostato di un passo. La forma è
> sempre la stessa — **due proprietari di un solo fatto che divergono** — e correggere il
> sintomo lasciando in piedi la forma sarebbe stata una risposta scadente a una buona
> segnalazione.
>
> Correzione: `if (wasStalled) onrecover?.()`. `onrecover` ora significa **"lo stato di stallo è
> finito"**, per qualunque ragione — assestamento, sospensione, cambio step, errore — e non
> "l'anchor è diventato disponibile". È l'host a decidere quanto vale.
>
> Di conseguenza `handleRecover()` diventa **incondizionato**. La guardia precedente
> `stalledStepId === active.stepId` sembrava più prudente e non lo era: al cambio step l'`active`
> dell'host è già avanzato, quindi la guardia falliva e `stalledStepId` restava appeso — un
> flusso che tornasse su uno step già stallato (Back, `setStep`, `startImportAt`) si sarebbe
> riacceso come in stallo senza alcuno stallo. Step attivo ce n'è uno solo, quindi l'azzeramento
> incondizionato non può danneggiare altro.
>
> Registrato anche il metodo, perché è il terzo caso odierno: la prima correzione l'avevo
> verificata **eseguendo la suite**, che era verde, e la suite non poteva vedere il buco perché
> nessuno aveva ancora scritto quel caso. Verde non vuol dire coperto.

> **⚠️ Fuori pista — E2E non eseguito in questo round**: il caso C (anchor che non arriva mai,
> desktop e mobile) richiede backend e browser sulla lane. Rinviato allo Step 7 come decisione
> esplicita e non come dimenticanza: la classe di guasto è già coperta a livello di componente e
> di host con un target che **non si registra affatto**, che è la forma che gli unit test
> precedenti non vedevano. Va detto però che l'E2E coprirebbe una cosa che gli unit non possono:
> che un anchor reale di una pagina reale si registri davvero. Resta scoperto e va dichiarato
> nel checkpoint, non taciuto.
>
> **↑ SUPERATA il 2026-09-21 nello Step 7: l'E2E è stato eseguito, 10/10, `EXIT=0`.** Lascio
> scritta la decisione originale perché il *motivo* del ribaltamento è la cosa da ricordare: il
> cambio di contratto ha introdotto una **rinomina di prop**, che è esattamente la classe che
> fallisce in silenzio (`?.()` su prop assente = no-op) e che gli unit test **non possono**
> vedere perché girano contro dei mock. Non è che la valutazione di prima fosse sbagliata: è che
> il lavoro è cambiato sotto di lei, e una decisione di rinvio va riesaminata quando cambia la
> classe di rischio, non solo quando cambia il tempo a disposizione.

> **⚠️ Fuori pista — la rinomina `onrecover` → `onstallend` e il controllo che NON scade.**
> Il coordinator ha segnalato che in Svelte 5 questa rinomina fallisce in silenzio dal lato
> consumatore: `onstallend?.()` con il prop non passato è un no-op, e un prop non dichiarato
> viene ignorato senza diagnostica. Quindi `expect(mock).not.toHaveBeenCalled()` resta **verde**
> sia quando il comportamento è corretto sia quando il cablaggio è rotto. Il meccanismo è reale.
>
> Il controllo proposto — `grep -c 'onrecover'` atteso `0`, più il positivo `grep -c 'onstallend'`
> atteso `> 0` — è giusto e va eseguito **prima** di leggere il numero dei test passati, perché un
> conteggio fatto dopo un verde già letto diventa una formalità che si conferma invece di una
> misura che può smentire. Ma ha due limiti che vanno scritti:
>
> 1. **Ha falsi positivi**, in direzione sicura: `const onrecover = vi.fn()` passato come
>    `onstallend={onrecover}` è cablaggio **corretto** con il nome vecchio come variabile locale.
> 2. **Scade.** Risponde a *«questa rinomina è stata completata?»*, che smette di essere una
>    domanda appena la risposta è sì. Non intercetta la rinomina successiva.
>
> **Il controllo permanente, misurato.** Non sono «i prop» a rendere il guasto silenzioso: è
> **`?.()`**. Siti di chiamata opzionale nel coachmark:
>
> ```
> :280 onclose?.()   :381 ontargetactivate?.()   :408 onstall?.()   :412 onstallend?.()
> ```
>
> Quattro, non tutti i prop. `onnext`, `onback`, `onskip` sono legati nel markup, e un legame rotto
> lì produce un bottone inerte ⇒ l'asserzione **positiva** diventa rossa, cioè visibile. Da cui la
> regola ricontrollabile in qualunque momento, senza sapere quale rinomina sia in corso:
>
> > **Ogni callback invocato con `?.()` deve avere almeno una asserzione positiva nel proprio file
> > di test.** Un mock con sole negative su una chiamata opzionale non misura niente, e non esiste
> > output che lo distingua da uno che misura.
>
> Verificato su tutti e quattro: `onclose` (`:660 :737 :2133`), `ontargetactivate` (`:821 :834`),
> `onstall` (`:1118` e seguenti), `onstallend` (`:1392 :1409 :1461` e seguenti). Il file è salvo
> per una **proprietà del file**, non perché in quei casi le negative fossero seguite da una
> positiva vicina.
>
> **⚠️ La regola sopra è giusta, il matcher con cui l'avevo scritta aveva DUE buchi.** Entrambi
> trovati dopo, uno dal coordinator e uno da me:
>
> 1. **Default no-op nel destructuring** (coordinator). Un callback assente **non lancia** se ha
>    un default inerte: `OnboardingOverlayHost.svelte:32` ha
>    `onrequestsidebar = () => {}`, chiamato a `:636 :646 :665 :676` **senza `?.`**. Effetto
>    identico a `?.()`, forma completamente diversa, e il mio grep restituiva **zero** su quel
>    file — uno zero corretto per la sintassi e sbagliato per la domanda. Ed è la forma
>    **peggiore** delle due: `?.()` dichiara la propria opzionalità **dove viene invocata**, il
>    default la dichiara 600 righe più su. *La sintassi del punto di chiamata mente sul
>    comportamento del punto di chiamata.* Non è isolata: almeno 8 file del progetto la usano
>    (`ModalBase`, `Header`, `ImageCropper`, `HelpMenu`, `BrokerSharingModal`,
>    `LanguageSelector`, `SocialShareModal`, `SupportActions`).
>    Verificato: `onrequestsidebar` **ha** una positiva (`:2807`,
>    `toHaveBeenCalledWith(opensSidebar)`), quindi il file soddisfa la regola anche nella forma
>    completa — non solo in quella rotta.
> 2. **Il prefisso `on` nel mio pattern** (mio). Avevo scritto `on[a-z]+\?\.\(`, cioè **ho
>    codificato una convenzione di naming dentro un controllo di correttezza**: un callback
>    `handleDone` o `callback` invocato con `?.()` mi sarebbe sfuggito. Misurato il generico
>    `\?\.\(` sulla directory: **gli stessi 5 risultati**, quindi qui il buco non costa niente.
>    Ma è la distinzione che il coordinator mi aveva appena insegnato, applicata a me: **il file
>    è salvo per una proprietà, il matcher è salvo per fortuna** — il prefisso `on` è una
>    convenzione, non una garanzia, e il primo resta vero domani mentre il secondo no.
>
> **Forma definitiva della regola:**
>
> > Ogni callback che può essere assente **senza errore** — per `?.()` **o** per default inerte
> > nel destructuring — deve avere almeno **una asserzione positiva** nel proprio file di test.
> > Un mock con sole negative su un callback di quella classe non misura niente, e non esiste
> > output che lo distingua da uno che misura.
>
> ```bash
> grep -nE '\?\.\('                        # chiamata opzionale — QUALSIASI nome, non solo on*
> grep -nE '= *\(\) *=> *\{\}|= *noop'     # default inerte nel destructuring
> ```
>
> **Una regola incompleta è più dannosa di nessuna regola**: chi la esegue ottiene un verde e
> smette di guardare.

> **⚠️ Fuori pista — errore mio: ho riletto lo zero della codifica esadecimale, un messaggio dopo
> averlo diagnosticato.** Chiamato `read_agent` con l'ID troncato `f6481aca` invece dell'UUID
> completo. Risposta: *«No agent found with agent_id: f6481aca. The agent may have been cleared or
> never existed.»* Ho concluso **«l'agente non esiste più»** e l'ho annunciato. `list_agents` lo
> mostrava `Running` da 2 051 s: era vivo e stava lavorando.
>
> La risposta negativa non diceva *«l'agente è sparito»*, diceva *«quell'identificatore non
> risolve»* — due cose diverse scritte identiche, come il `0` del grep sul file esadecimale.
>
> È **peggiore** del caso esadecimale sotto un aspetto, e per questo va registrato: lì lo strumento
> non dava alcun indizio, qui lo strumento **ha dichiarato la propria ambiguità** (*«may have been
> cleared **or never existed**»*) e io ho collassato le due branche su quella allarmante, senza
> fare la chiamata da una riga che le distingue.
>
> > **Uno strumento che ti dice di non sapere è più utile di uno che tace, ma solo se leggi la
> > parte in cui te lo dice.**

> **⚠️ Fuori pista — «lane 6158 sua» era una mia affermazione sbagliata.** Riferito al coordinator
> che non potevo eseguire nulla perché `test-author` occupava la porta. Misurato:
> `lsof -nP -iTCP:6158 -sTCP:LISTEN` → nessun listener. `onboarding-component-unit` è **Vitest**:
> non apre porte. La contesa reale è **il file di test** che l'agente sta riscrivendo, non la
> porta. L'astensione resta corretta, la ragione no — e una **porta libera non prova che la lane
> sia libera**. Terza misura odierna che risponde alla domanda vicina, e la prima intercettata
> prima di usarla.

### Step 7 — Gate

Selettori mirati → `front-utility onboarding-component-unit` → `front-utility onboarding-tour` →
prettier/check/build/ruff/black → parity i18n.

Lane 6158. **Leggere sempre l'exit code isolato**, mai attraverso una pipe.

**Stato:** ✅ completato il 2026-09-21.

> **Note implementazione — tutti i gate eseguiti, exit code letti isolati:**
>
> | gate | esito | exit |
> |---|---|---|
> | `front-utility onboarding-component-unit` | 12 file / **395 test passati**, 0 rossi | `0` |
> | `front-utility onboarding-tour` (E2E) | **10/10 in 54,6 s** | `0` |
> | `prettier --check` sui 3 file toccati | pulito | `0` |
> | `ruff check populate_mock_data.py` | `All checks passed!` | `0` |
> | `black --check populate_mock_data.py` | `1 file would be left unchanged` | `0` |
> | `i18n audit` | 3187 complete / 0 incomplete / 0 missing backend | `0` |
> | `front check` (svelte-check) | **3 errori / 41 warning in 4 file**, nessuno in onboarding | `1` |
>
> **L'E2E è stato eseguito, non rinviato — cambio di decisione rispetto a quanto scritto sopra.**
> Ragione: una rinomina di prop è **esattamente** la classe che fallisce in silenzio (`?.()` su
> prop assente = no-op), e gli unit test girano contro dei mock. Solo l'E2E prova che il
> cablaggio regga in un browser reale. La voce che avevo dichiarato scoperta è quindi **chiusa**,
> non rinviata: una delle poche correzioni odierne in direzione buona.

> **⚠️ Fuori pista — i 130 errori `svelte-check`: la mia attribuzione era sbagliata nella CAUSA,
> e l'esperimento controllato si è eseguito da solo.** Avevo riportato *«130 errori, tutti in
> `tools/pac-allocator` ⇒ superficie di D, non mia»*, con controllo positivo sul log
> (`pac-allocator` 124, `Error` 135) e zero sui miei tre file.
>
> Il coordinator ha contestato la **causa**, non la conclusione, e aveva ragione al numero esatto.
> La misura, prima e dopo, sullo stesso albero e sugli stessi sorgenti:
>
> ```
> pre-rigenerazione    svelte-check found 130 errors and 41 warnings in 18 files
> post-rigenerazione   svelte-check found   3 errors and 41 warnings in  4 files
> ```
>
> **127 erano fantasma**, prodotti da `frontend/src/lib/api/generated-tools.ts` stantio — file
> **ignorato** (`frontend/src/lib/api/.gitignore:2`, verificato con `git check-ignore -v`) e
> quindi invisibile a `git status --porcelain`. Si è rigenerato da solo durante i miei gate
> (`mtime 2026-09-21 17:31`, 668 → 1017 righe), quasi certamente per la build dell'E2E: non
> l'ho chiesto io, e la seconda misura è stata possibile per quello.
>
> **Il difetto di metodo, che è la parte che vale:**
>
> > **Il luogo in cui un errore si manifesta non è la sua causa.** Un artefatto generato stantio
> > produce errori **nei file che lo consumano**, mai nel file che è. `tools/pac-allocator`
> > compariva nel log come **vittima**, e io l'ho letto come **origine**.
>
> E il mio controllo positivo era vero e **insufficiente**: certificava che il matcher sapesse
> leggere il log, non che il log dicesse quello che gli facevo dire. Nessun grep su un log
> distingue *«questo file è rotto»* da *«questo file è compilato contro un contratto sbagliato»*.
>
> **Correzione a una mia formulazione troppo larga**: avevo scritto che *«l'attribuzione per file
> è più forte di quella per tempo, perché non dipende da quando ho misurato»*. Vale per **dove
> intervenire**, non per **cosa ha causato**. Su un errore mediato da un artefatto generato, per
> file non attribuisce affatto.
>
> E il costo non sarebbe rimasto qui: D sarebbe andato a cercare 130 errori su file che sta
> cancellando, non avrebbe trovato niente, e **lo zero da interrogare l'avremmo generato noi**.
> *Un'attribuzione sbagliata non resta ferma: viaggia e costa a qualcun altro.*
>
> **Regola operativa per il merge, valida per tutti i worktree:** `svelte-check` **non è
> misurabile** in un worktree il cui client generato non sia stato rigenerato. Un numero uscito da
> quel gate non va riportato come baseline né confrontato con misure fatte altrove. Rigenerare
> **prima** di credere a qualunque misura che attraversi un artefatto generato.
>
> **Avvertenza sulla provenienza dei numeri**: il coordinator aveva anticipato «3 reali, 127
> fantasma» misurando sul target. Non l'ho scritto come fatto finché non l'ho misurato qui: il
> `3` qui sopra è **mio**, e coincide. I 3 residui stanno in `BrokerSharingPanel`,
> `GlobalSettingsTab`, `TransactionFormModal.test.ts`, `ToolExecutionMetrics` — **zero in
> onboarding**, con controllo positivo sul log nuovo (`Error` 5).
>
> **Una premessa del coordinator che qui non reggeva più**: mi aveva detto che il mio
> `generated-tools.ts` era «668 righe, 14/09». Alla mia misura era già 1017 righe e `mtime` di
> pochi minuti prima. Aveva misurato a T1 e concluso sul mio stato a T2 — la stessa forma della
> `003` di stamattina, *il file c'era davvero, il contenuto no*. La conclusione restava giusta,
> la prova no.

> **⚠️ Fuori pista — ri-armatura del timer di stallo: scoperta, misurata, NON corretta in R7.**
> Segnalata dal coordinator, verificata da me, e il dominio reale è **più stretto** di come
> l'avevamo formulata entrambi. La registro qui perché lo Step 7 è la lista delle cose che
> dichiaro scoperte, non di quelle che dichiaro risolte.
>
> **Prima: una mia affermazione da correggere.** Avevo scritto che la trappola della §4
> «sparisce». È vero **solo per `stepId`** (prop primitivo, stesso valore ⇒ nessuna
> ri-esecuzione). L'effect dipende però anche da `anchorRect` e `targetStable` (`:403`), e su
> quelli l'affermazione non vale. Se restava scritta così, il prossimo lettore concludeva che il
> ciclo di vita dello stallo è chiuso: è chiuso **per lo smontaggio**, non per la ri-armatura.
>
> **Il meccanismo**: ogni ri-esecuzione dell'effect esegue `stalled = false` e **riarma il timer
> da capo** (`:405`, `:408`). Quindi una dipendenza che cambia ripetutamente può rimandare lo
> stallo all'infinito.
>
> **Ma il dominio non è «una pagina che si muove».** Misurato leggendo la macchina a stati della
> geometria (`refreshPosition` `:230-270`, effect geometria `:283-340`):
>
> - **Anchor che non arriva mai** — `!anchor?.isConnected` ⇒ `anchorRect = null`,
>   `targetStable = false` (`:236-239`), riscritti **con gli stessi valori** a ogni frame dal
>   loop rAF `measureUntilStable`. Stesso valore su uno `$state` non produce reattività ⇒
>   **nessuna ri-esecuzione, nessuna ri-armatura, lo stallo scatta**. Il caso principale è salvo.
> - **Anchor presente che non si stabilizza** — finché `stableFrames < 2` e `anchorRect` è null,
>   il ramo `else` scrive `targetStable = false` (`:266-267`), di nuovo lo stesso valore ⇒
>   costante ⇒ **lo stallo scatta**. Salvo anche questo, che è il secondo modo di guasto per cui
>   la feature esiste.
> - **Anchor che si muove** — qui `anchorRect` è non-null e `targetStable` è **pinned a true**
>   (`:263-264`, `:305-306`, `:331-332`): quindi `settled` è vero e l'effect **esce prima di
>   armare qualunque timer** (`:407`). Non c'è nessun timer da riarmare. E `rectsMatch` (`:259`)
>   impedisce perfino la riassegnazione quando il rect è identico.
>
> **Dominio residuo reale**: un anchor che **si connette e si disconnette ciclicamente** con
> periodo inferiore a `GUIDE_STALL_MS` — cioè `anchorRect` che fa non-null → null → non-null.
> Ogni ciclo riarma. Conseguenza osservabile: lo stallo non scatta mai, **ma il pannello si
> ancora a intermittenza**, quindi il guasto è *visibile* e non è l'attesa silenziosa che R7
> corregge. Gravità minore, e classe diversa.
>
> **Perché non lo correggo qui**: è **preesistente** (`:405-406` fa già così oggi, la modifica
> adottata non lo peggiora di un'unità) e la scelta è **di prodotto, non mia**. Le due semantiche
> sono:
>
> - *«3 s dall'ultimo cambiamento»* — ciò che il codice fa oggi;
> - *«3 s da quando questo step è diventato attivo»* — probabilmente ciò che l'utente crede di
>   vedere, e che richiederebbe di agganciare il timer a `stepId` invece che alle dipendenze di
>   geometria.
>
> La seconda è quasi certamente quella giusta, ma cambia il significato della feature e va decisa
> dal developer, non dedotta da me a valle di un bugfix. **Resta valida indipendentemente da
> tutto quanto sopra**: è vera anche in assenza di qualunque difetto.
>
> **La formulazione sbagliata, conservata apposta.** Il coordinator l'aveva descritta così:
> *«su una pagina che si muove, un utente già in stallo vede il pannello sparire e tornare dopo
> altri 3 s, e in un caso abbastanza agitato potrebbe non vederlo mai»*. **Non può accadere**, per
> le tre righe sopra. Ma la deduzione da cui nasceva è ragionevole e la rifarà chiunque legga la
> lista delle dipendenze dell'effect senza leggere chi le scrive — quindi la lascio scritta con
> accanto la ragione per cui è falsa, invece di cancellarla e lasciare la trappola intatta per il
> prossimo.
>
> **La regola che la spiega**, e che vale oltre questo caso:
>
> > Le dipendenze di un `$effect` dicono quando **può** ri-eseguire, non **se** ri-eseguirà né
> > **cosa accadrà** se lo fa. Fermarsi alle dipendenze produce sempre un **sovrainsieme** — e un
> > sovrainsieme di rischi si presenta con l'aspetto di un elenco di rischi.
>
> Nel caso specifico l'errore è stato scambiare *«questa variabile è un oggetto»* per *«questa
> variabile cambia identità»*, senza guardare chi la scrive: `rectsMatch` (`:259`) è una difesa
> deliberata, e stava **dentro una riga già letta**.
>
> **E il difetto sopravvalutato è più insidioso di quello sottovalutato**, per una ragione che non
> è tecnica: **un falso allarme non viene quasi mai contestato.** Chi segnala un rischio sembra
> prudente, chi lo mette in discussione sembra negligente — quindi l'asimmetria protegge l'errore
> invece di esporlo, e il costo si scarica su chi fra sei mesi cercherà per ore un difetto che non
> esiste, con una firma autorevole sotto. L'unico modo per cui la contestazione non degrada in
> opinione contro opinione è **portare una misura**, che è ciò che è stato fatto qui.
>
> **Nota sul mio argomento del teardown** («o è vera o abbiamo un leak da mesi»): il coordinator
> ha ragione a metterci l'asterisco. Prova che **qualcuno ci ha scommesso**, non che **abbia
> vinto** — un listener appeso è precisamente il guasto che nessuno nota. Resta un buon argomento
> perché è interno al repo e misurabile, ma non è una dimostrazione: *«falsificabile e non
> falsificato» non è «dimostrato» — è solo il posto giusto dove mettere un test.*

> **⚠️ Fuori pista — quattro voci che avevo dichiarato al coordinator e che NON erano in questo
> file.** Scoperte dopo lo stage, rileggendo lo Step 7 per intero perché un messaggio antecedente
> del coordinator mi chiedeva di scrivere la prima *«come proponi»* — e stavo per rispondere «già
> fatto». Misurato: il checkpoint dichiarava **4 voci di scope differito**, il piano ne conteneva
> **2** (E2E, chiusa; ri-armatura, qui sopra). Le altre esistevano solo nei messaggi di chat.
>
> > **Il difetto, ed è di classe nuova rispetto agli altri di oggi**: gli altri erano numeri veri
> > che rispondevano alla domanda accanto. Questo è **una descrizione del contenuto più ricca del
> > contenuto**. Avevo verificato che le voci esistessero *da qualche parte*, non *dove servono* —
> > e il checkpoint è un messaggio, che fra sei mesi non c'è. Il piano è il punto di recupero.
>
> **1. Finestra «errore + non ancorato» — domanda di prodotto, due opzioni.**
> Durante un errore del controller, uno step `import_guide` non ancorato resta con il **solo
> Chiudi**: `showNext` include `stalled` ma **non** `error`, e la guardia dell'effect (`:407`)
> esce *mentre* l'errore è presente. Il timer è quindi **sospeso, non perso** (`error` è
> dipendenza a `:401`): la via d'uscita ricompare `GUIDE_STALL_MS` dopo che l'errore si risolve.
>
> - *Oggi*: la via d'uscita non sopravvive all'errore. **Ragione a favore**: l'errore ha la
>   propria precedenza di rendering, e «Continua comunque — problema di caricamento» mostrato
>   sotto un errore che parla d'altro sarebbe **fuorviante**, non utile.
> - *Alternativa*: la via d'uscita sopravvive all'errore, con etichetta propria.
>
> Decisione del developer, non mia. **La ragione dell'attuale è scritta qui apposta**: fra sei
> mesi qualcuno troverà questo comportamento e lo chiamerà bug — trovare l'argomento già scritto
> gli risparmia l'indagine.
>
> **2. Perché `showNext = stalled || error != null` (proposta B) era una trappola — misurato, non
> valutato sulla descrizione.** Letto `handleNext()` (`OnboardingOverlayHost.svelte:652-660`, **non**
> nel coachmark — il grep nel file sbagliato dà `0` e sembra una risposta):
>
> ```js
> if (stalled && isStepManagedFlow(active.flow)) { await onboardingGuide.skip(); return; }
> if (!lastStep) { onboardingGuide.next(); return; }
> ```
>
> Il ramo di skip richiede `stalled`. Con B, il pulsante comparirebbe con `stalled === false`,
> **mancherebbe** quel ramo, cadrebbe in `finish()` e per un flow step-managed all'ultimo step
> persisterebbe **`completed`** su uno step che l'utente non poteva eseguire, sotto un'etichetta
> «Finish».
>
> > **Un controllo mancante diventa un falso successo persistito.** La cura era peggiore della
> > malattia: il difetto lascia l'utente fermo e visibile, B lo lascia convinto di aver finito.
>
> La forma corretta richiede **una sola** derived `unreachable = stalled || error != null` che
> alimenti insieme `showNext`, `nextLabel`, `showNextArrow` **e** il ramo di `handleNext` — cioè
> la decisione di prodotto del punto 1. Non è autorizzata in questo round.
>
> **3. Proposta A (`onstallchange(stalled)` — riportare lo stato, non i fronti) — differita per
> una ragione specifica, non conservativa.** È la forma migliore a lungo termine: un solo
> callback che riporta lo stato rende impossibile la deriva fra `onstall` e `onstallend` per
> costruzione, invece di impedirla per disciplina. Non adottata qui perché la forma del teardown
> **chiude già** la classe di deriva, e A costerebbe l'intera superficie di asserzioni esistente
> (41 siti rinominati, 8 test di bordo byte-identici) per un guadagno strutturale senza cambio di
> comportamento. Candidata a un round di refactor, non a un bugfix.
>
> **4. Composizione dell'host attraverso l'uscita dalla guida — NON osservabile con l'harness
> attuale.** `fakeGuideState` è un oggetto semplice letto tramite getter: mutarlo a metà test
> **non invalida** il `$derived` dell'host, quindi la transizione `active → null` (che è
> esattamente ciò che smonta il coachmark in produzione) non è riproducibile a livello di host.
> I due test di ciclo di vita consegnati girano perciò sul **componente**, con `view.unmount()`
> reale. La via più economica per chiudere il buco è un doppio basato su `$state` in un helper
> `.svelte.ts` — **modifica di harness**, fuori dallo scope di R7.
>
> **Nessun `it.skip` seminato**, deliberatamente: *un segnaposto verde è peggio di un buco
> dichiarato* — il buco si vede in questa lista, il segnaposto si conta fra i passati.
>
> **Nota per chi scriverà l'asserzione del punto 4**: `data-geometry-state` riporta `stable`
> **~32 ms dopo** il riancoraggio reale (misurato: +3 024 vs +3 056). Asserire sullo stato
> anziché sul fronte produce un test che passa nove volte su dieci, e il decimo viene archiviato
> come *flaky* da chi non ha questa riga.

### Step 8 — Review read-only e checkpoint FROZEN

Manifesto esatto in inclusione, mai "tutto tranne". Nessuno staging, nessun commit.

**Stato:** ✅ completato il 2026-09-21.

> **Note implementazione — review read-only del diff completo, nessun rilievo.** Riletti i tre
> file di produzione riga per riga contro i contratti del §«Contratti da preservare»:
>
> - **D3 rispettata**: l'effect del fade ha `void stalled` **e** `|| stalled` nella guardia, quindi
>   un pannello in stallo non attenua mai; al recupero il fade riarma una scadenza fresca (coperto
>   dal test `recovered panel + fade deadline`, `data-subdued` falso a `+2_999`, vero a `+3_000`).
> - **`actionHint` non può comparire in stallo**: la guardia è `guideState === 'anchored'`, e in
>   stallo `guideState` vale `'stalled'`. Verificato sul markup, non dedotto.
> - **`error` batte `stalled`** in entrambi i punti: nel `$derived guideState` e nel messaggio
>   (`error ?? (…)`), coerente con D2.
> - **`handleNext`**: il ramo di skip è **prima** di `!lastStep`, quindi uno step in stallo di un
>   flusso step-managed persiste `skipped` e non può cadere su `finish()`. È esattamente il
>   cammino la cui assenza rendeva pericolosa la proposta B.
> - **`showNextArrow={!checkpoint && !stalled}`**: nessuna freccia avanti su un comando che
>   significa «rinuncia», coerente con D5 (nessun auto-advance).
>
> Checkpoint:
>
> ```
> git diff --check                       EXIT=0   (nessun whitespace/conflict marker)
> lsof -nP -iTCP:6158 -sTCP:LISTEN        EXIT=1   (nessun listener: lane libera)
> git rev-parse HEAD                      38d44b7172eb3cc01d86f6aba1147ed1afbd346a
> git rev-list --left-right --count       0  0     (identico a dev_release2)
> git status --porcelain | wc -l          12       (11 tracciati + 1 non tracciato)
> ```

---

## Definition of done

Un anchor che non si registra mai **e** uno che non si stabilizza mai producono entrambi, entro
`GUIDE_STALL_MS`, un messaggio visibile e un `Continue` funzionante. Un anchor in ritardo azzera il
messaggio da solo. Il messaggio non viene mai attenuato. Un errore di controller lo batte sempre.
Uno step stallato in un flow step-managed persiste `skipped`. 228 chiavi `onboarding.*` in tutte e
quattro le lingue. E2E verde desktop e mobile. Nessun edit di J al runner o ai cataloghi.

## Fuori scope, per decisione

- **R8** — replay in `sessionStorage` che non sopravvive a scheda chiusa o cambio dispositivo.
- **R9** — guida che riparte da step 1 lasciando la route; 9 flow su 15 mai provati contro una
  pagina reale.

Sequenza R7 → R8 → R9 confermata dal developer il 2026-09-21.
