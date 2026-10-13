# Piano — fase 00, 50: il dettaglio broker sotto carico (C-58)

> **Stato**: ✅ chiuso il 2026-10-13, checkpoint al coordinatore (§7, passo 8).
> - **C-58 è chiusa** (passo 6). Con ogni risposta dell'API ritardata di 2,5 s la base scade a 30,0 s e la cura passa in 23,1 s; a 3,8 s il budget di 60 s del blocco FIFO fa il suo lavoro (passo 3).
> - **La spec intera** è verde a 1 e a 4 worker sotto carico, e i 25 test del blocco esterno non ricaricano più la lista (passo 4).
> - **Il test di `:120`**, che passava a vuoto, ora clicca la card e verifica la pagina del broker (passo 4).
> - La sonda e la cura sono passate da `test-author`; la sonda non è nel diff.
>
> - **Mandato**: coordinatore di Release 2 (`c8328a01-…`), lotto 50. **Origine**: la voce C-58 di `BACKLOG_POST_1.2.md`, sezione C.
> - **Workstream I**. Ramo `e-alfy-performance-charts-plan`. Base `e501b9615` (treno 77).
> - **Corsia**: `--test-port 6157 --data-dir /tmp/librefolio-r2-i-charts`, con `PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py test …`; un comando alla volta. Mai le porte 6040 e 6041, mai la galleria, mai `front build`.
> - **Tocca**: solo `frontend/e2e/brokers/brokers-detail.spec.ts`, più il journal: questo piano, la riga della scansione nel piano 49 (§5) e la voce C-58 del backlog.
> - **La cartella** `50_brokerDetailBudget` è una mia proposta: il coordinatore ha dato il numero del lotto, non il nome.

## 0. Autorizzazione (2026-10-13)

Il coordinatore, dopo la scansione del lotto 49: «Scansione chiara: 0 corse reali, niente da assegnare. **Lotto 50, piccolo, test e journal:**

1. Nel piano 49, §5, una riga con l'esito della scansione (metodo, 43 finestre lette a mano, 0 corse reali, i limiti) e i rimandi ai tuoi log.
2. **C-58**: `brokers/brokers-detail.spec.ts` `:410` sfora i 30 s sotto carico. Nel gate del treno 59 è caduto a 40,1 s con carico 56, poi da solo è passato in 2,9 s. Segui `test-triage`: un budget esplicito per quel passo, o una navigazione in meno, senza allentare le asserzioni. Verifica sotto carico, a 1 e a 4 worker. La spec è tua.
3. Chiudi C-58 nella sezione C del backlog solo con la prova; altrimenti aggiornala.

Test via test-author. Poi checkpoint FROZEN.»

## 1. Il reperto

- La voce C-58 (`BACKLOG_POST_1.2.md`, sezione C): nel gate del treno 59, con carico ~56, il test «the lot detail modal renders its three sections and the net breakdown» (`brokers-detail.spec.ts:410`) è scaduto **durante la navigazione, prima del pannello**, a 40,1 s. Rilanciato con carico 30 è passato in 2,9 s.
- **I 40,1 s non sono la catena**: sono i 30 s del test più lo smontaggio delle fixture dopo la scadenza, che Playwright fa con un budget suo.
- Il log del gate non è nella mia `/tmp`: il reperto viene dalle parole del coordinatore e dalle misure di questo lotto.

## 2. La catena del test

Playwright 1.61, `frontend/playwright.config.ts`: timeout del test 30 s (`:110`), che copre anche gli hook `beforeEach` e le fixture; timeout delle `expect` 3 s (`:111`); nessun retry in locale.

I numeri di riga della spec, dal §1 al §4, sono quelli della base `e501b9615`. Nel file curato il test della card è a `:133`, il blocco FIFO a `:267` e il test di C-58 a `:429`.

Nel blocco esterno `Broker Detail Page` (`:114`) ogni test fa, in ordine:

1. **`login`** (`fixtures/auth-helpers.ts:7-39`), nel `beforeEach` (`:115-118`): `goto('/')`, il form, il submit, l'attesa che il form sparisca. La pagina atterra sulla Dashboard.
2. **`ensureBrokerExists`** (`:16-37`), nello stesso `beforeEach`: `navigateTo('/brokers')` (`goto`, `domcontentloaded`, `html[data-i18n-ready="true"]`), poi l'attesa di `[data-testid="brokers-page"][data-busy="false"]` (20 s). **Lascia la pagina sulla lista dei broker, caricata.**
3. **Di nuovo `navigateTo('/brokers')`**, dentro `goToFirstBrokerDetail` (`:57-67`, 11 test) o `goToBrokerWithHoldings` (`:84-93`, i 13 test del blocco FIFO), e nel test di `:120`: un secondo caricamento completo della pagina che il passo 2 ha appena lasciato pronta.
4. Il click sulla card, la pagina del broker, `broker-name`.
5. Solo nel blocco FIFO (`:256`): la scheda Posizioni, la prima riga, l'azione «Analyze lots», il pannello dei lotti con la tabella e i grafici, e nel test di `:410` il menu contestuale e il modale.

- **Il costo del passo 3**: la lista chiama `refreshAllBrokers()` e un `fetchReport` di tutti i broker dell'utente (`frontend/src/routes/(app)/brokers/+page.svelte:175`), cioè un calcolo del portafoglio sul backend. Ogni test del blocco esterno lo paga due volte.
- **Chi chiama gli helper fuori dal blocco esterno**: `resolveAllOpenLotsAsset` (`:715`, blocco «Lots charts axisBuilder guard», senza `beforeEach`) e `openBrokerGrowthChart` (`:1002`, blocco «GrowthChart P&L mode»). Lì la pagina è sulla Dashboard dopo il login: la navigazione serve.
- **I budget già espliciti nel file**: 60 s nei blocchi axisBuilder (`:855`, `:871`, `:892`, «Login, the broker page, the probe requests and a full panel load before the action»), P&L (`:1032`, nel `beforeEach`), import (`:1234`, `:1320`) e Bulk (`:1486`, `:1509`); 45 s nel blocco del badge della quota (`:1645`, `:1656`). Il blocco esterno e il blocco FIFO restano sui 30 s di default.

## 3. Il triage (skill `test-triage`)

- **La forma della risposta**: no. Nessuna asserzione sui dati è fallita; il test è scaduto prima del pannello.
- **L'orologio**: sì, nella forma del budget. Il test non ha `waitForTimeout`; ha un budget implicito di 30 s per una catena di login, due caricamenti della lista (uno ridondante), la pagina del broker, il pannello dei lotti e il modale. Da solo la catena prende pochi secondi; con carico 56 su 10 core ne ha presi più di 30.
- **Lo stato condiviso**: no. Il test non legge dati scritti da altri; da solo passa, e sotto carico cade per tempo, non per un valore.
- **L'ambiente**: no. Il setup del gate era sano: gli altri test del file sono passati.
- **La lentezza del prodotto**: no come difetto. La catena è lenta solo sotto un carico 5 volte i core; il `fetchReport` della lista è lo stesso che l'utente paga una volta, mentre il test lo paga due.
- **Il verdetto**: **assunzione** (tempo). Il test dà per scontato che la catena stia in 30 s, e ne spreca una parte in una navigazione che non verifica niente.

## 4. La cura (via `test-author`)

- **(a) Una navigazione in meno, per struttura e non per sonda.** La prima idea era un helper che riusa la lista se `count()` la trova caricata, altrimenti naviga; la regola 6 di `frontend-testing.instructions.md` («Never let a probe decide whether to act») la scarta. La forma adottata:
  - `goToFirstBrokerDetail` e `goToBrokerWithHoldings` **non navigano più**: aprono il broker dalla lista che è già sullo schermo, e prima ne **asseriscono l'indirizzo** (`toHaveURL(/\/brokers(?:[?#]|$)/)`, la regex di `onboarding-guides.spec.ts:584`), con un messaggio che dice di aprire la lista prima;
  - nel blocco esterno la lista c'è per costruzione: la lascia caricata `ensureBrokerExists`, nel `beforeEach`;
  - i due chiamanti che partono dalla Dashboard, `resolveAllOpenLotsAsset` (`:715`) e `openBrokerGrowthChart` (`:1002`), fanno `navigateTo(page, '/brokers')` esplicito prima dell'helper: per loro non cambia niente;
  - il test di `:120` perde la sua navigazione, e il suo `if (count > 0)` diventa un'asserzione sulla prima card (regola 6). Oggi passa a vuoto: conta le card prima che la lista arrivi (§5, la base);
  - `BrokerCard` (`broker-card-{id}`) vive solo nella pagina della lista (`brokers/+page.svelte:415`): la card visibile prova già la lista caricata. L'asserzione sull'indirizzo serve al messaggio: chi parte dalla pagina sbagliata lo sa subito, invece di aspettare 8 s una card che non arriverà.
  - **Perché l'indirizzo e non `brokers-page` visibile**: l'indirizzo non cambia nessun tempo, su nessun percorso.
    - `brokers-page` avrebbe chiesto 8 s e non i 3 di default: dalla Dashboard `navigateTo` torna appena c'è `data-i18n-ready`, prima che l'app abbia montato la pagina (`auth.checkAuth()`, poi `appBootstrap.load()`).
    - Così i 6 test che partono dalla Dashboard avrebbero aspettato la card fino a 16 s invece di 8: un'attesa allentata.
    - Con l'indirizzo, chi è sulla pagina giusta ma non vede la lista cade sull'asserzione della card, il cui messaggio («an empty list means the page never loaded») è proprio quello giusto.
  - Le asserzioni degli helper restano tutte: la card visibile (8 s), l'URL, la pagina del broker, `broker-name`.
- **(b) Un budget esplicito per il blocco FIFO**: `test.describe.configure({timeout: 60_000})` dentro il `describe` di `:256`, con un commento sulla catena, come i blocchi axisBuilder e P&L più avanti nel file.
  - Il budget del `describe` vale dall'inizio del test, quindi copre anche il `beforeEach` esterno; un `test.setTimeout` nel corpo del test arriverebbe dopo il login e la lista.
  - Il blocco intero e non il solo `:410`: i 13 test fanno la stessa catena fino al pannello, e il gate ha colpito `:410` per caso.
  - I timeout dei singoli passi (8, 5, 10 s) e tutte le asserzioni restano invariati.
- **Le alternative scartate**:
  - togliere `ensureBrokerExists` dal `beforeEach`: cambia la rete di sicurezza dei test esterni;
  - riusare la lista con una sonda `count()` (la prima idea): la regola 6;
  - alzare il timeout globale in `playwright.config.ts`: nasconde la lentezza di tutti i test, non di questa catena.

## 5. Le prove

- **La base**, misurata prima della cura: `front-broker detail` a 1 e a 4 worker, con il carico (`uptime`) prima e dopo. Dal rapporto HTML di Playwright estraggo la durata di ogni test e dei passi: il `beforeEach`, la seconda navigazione, la pagina del broker, il pannello.
  - Lo strumento: `/tmp/libreFolio_i_l50_pwsteps.py`, che legge lo zip del rapporto (`frontend/playwright-report/index.html`, copiato in `/tmp` dopo ogni giro).
- **La cura**, con gli stessi comandi e la stessa estrazione: la seconda navigazione deve sparire dai passi, e le durate devono stare sotto i budget con margine.
- **Il limite**: il carico 56 del gate non si riproduce senza caricare la macchina, che è condivisa. E la base è già verde a 1 e a 4 worker nella mia corsia (passo 2): il verde della cura, da solo, non prova niente.
- **La prova deterministica** (temporanea, via `test-author`, mai nel checkpoint): nel `beforeEach` esterno, solo se c'è `LF_PROBE_API_DELAY_MS`, un `page.route('**/api/v1/**')` che ritarda ogni risposta dell'API dello stesso tempo, poi `route.fallback()`.
  - Il modello: un backend lento in modo uniforme, come sotto carico. Le richieste parallele non si sommano, quelle in catena sì.
  - Il giro: solo il test di `:410`, a 1 worker, prima sulla base e poi sulla cura, con lo stesso ritardo. Atteso: la base scade a 30 s, la cura passa sotto i 60 s.
  - Un terzo giro, sulla cura con un ritardo maggiore, mette al lavoro il budget di 60 s del blocco FIFO: il test deve passare oltre i 30 s.
  - Poi la sonda esce dalla spec, e il diff finale contiene solo la cura.

## 6. Fuori da questo lotto

- La riga della scansione del lotto 49 va nel piano 49, §5 (punto 1 del mandato): passo 7 qui sotto.
- Il test di `:120` entra nella cura (§4 a), ma solo per la navigazione e per il suo `if`: il resto del test resta com'è.
- I test esterni che non sono del blocco FIFO restano sui 30 s: il più lento, a 4 worker con carico 54, ne ha presi 13 (passo 2).
- **Il prossimo limite, solo osservato**: con un backend ancora più lento cede l'attesa di `brokers-page[data-busy="false"]` in `ensureBrokerExists`, che ha 20 s (passo 3, la sonda a 3,8 s ne ha usati 16,4). Non è nel mandato, non è mai caduta, e la spec non ha un rosso che la chieda: la segnalo al coordinatore, senza voce nel backlog.

## 7. Avanzamento

- [x] **1. Analisi** (2026-10-13): la voce C-58, la catena (§2), il triage (§3), la cura (§4).
  > **Note implementazione**:
  > - La base è `e501b9615`, uguale al target; worktree pulita, porta 6157 libera, carico 12–18 su 10 core.
  > - Lette: la spec (`:16-118`, `:256-535`, `:700-720`, `:849-1040`), gli helper di login e navigazione, la config di Playwright, il runner (`scripts/test_runner/_frontend_common.py:213-330`, selettore `front-broker detail` a `_frontend_broker.py:54`, `:102`), la pagina della lista.
  > - Le card della lista hanno `data-testid="broker-card-{id}"` (`BrokerCard.svelte:85`); i broker non accessibili usano `broker-discovery-card-{id}`, quindi il selettore `[data-testid^="broker-card-"]` non li prende.
  >
  > **⚠️ Fuori pista**: il log del gate del treno 59 non è nella mia `/tmp`; lavoro sulle parole del coordinatore e sulle mie misure.
- [x] **2. La base, a 1 e a 4 worker** (2026-10-13).
  > **Note implementazione**:
  > - **1 worker**: `front-broker detail`, 37/37 verdi in 2,2 min (157 s di orologio), carico 27,2 → 21,0. Il test di `:410` prende 3,12 s, di cui 1,45 s di `beforeEach`; il più lento 5,57 s.
  > - **4 worker** (`--workers 4`): 37/37 verdi in 1,6 min (135 s), carico 39,7 → 54,3. Il test di `:410` prende 6,47 s: `beforeEach` 4,23 s (login 1,9, la prima lista 0,97 + `data-busy` 1,33), la seconda lista 0,88 s. Il più lento 13,07 s, il primo test di un worker a freddo (`beforeEach` 11,25 s).
  > - **Il costo della seconda lista**, sui 25 test del blocco esterno (`goToFirstBrokerDetail` 11, `goToBrokerWithHoldings` 13, `:120`): mediana 0,18 s e massimo 0,30 s a 1 worker; mediana 0,91 s e massimo 1,44 s a 4 worker, 20,4 s in tutto. È solo il tempo che il test aspetta (il `goto`, l'i18n, la prima card): il `fetchReport` di tutto il portafoglio che la lista lancia resta in volo sul backend mentre il test è già sulla pagina del broker.
  > - **Il test di `:120` passa a vuoto, misurato**: in entrambi i giri conta le card subito dopo `html[data-i18n-ready]`, ne trova 0 e finisce senza cliccare (il passo «Query count», poi gli hook di chiusura).
  > - **Nel blocco P&L** la navigazione di `goToBrokerWithHoldings` parte dalla Dashboard: è vera, e la cura non la tocca.
  > - Le prove: `/tmp/libreFolio_i_l50_base_w{1,4}.log`, `…_load.txt`, `…_report.html`, `…_steps_d1.txt`, `…_navcost.txt`; lo script `/tmp/libreFolio_i_l50_navcost.py`.
  >
  > **⚠️ Fuori pista**:
  > - La base è verde a 1 e a 4 worker anche con carico 54, vicino ai 56 del gate: il rosso del gate non si riproduce nella mia corsia. Per questo la prova deterministica del §5.
  > - Rileggendo `frontend-testing.instructions.md`, la regola 6 scarta l'helper con la sonda `count()` del §4: la cura (a) diventa strutturale (§4 riscritto).
- [x] **3. La cura** (`test-author`), con la prova deterministica (2026-10-13).
  > **Note implementazione**:
  > - **La sonda** (fase 1 di `test-author`): 8 righe nel `beforeEach` esterno, prima del login, attive solo con `LF_PROBE_API_DELAY_MS`; marcate `TEMP PROBE lot 50`. Senza la variabile la spec non cambia. Prettier rc 0, tsc e2e con le sole 2 righe della base.
  > - **La base con la sonda**, `LF_PROBE_API_DELAY_MS=2500`, solo `:410` a 1 worker (carico 15,7 → 12,9): **rossa**, «Test timeout of 30000ms exceeded» a 30,0 s, mentre aspetta la prima riga della tabella dei lotti. I passi: `beforeEach` 17,4 s; la seconda lista 8,2 s (la card arriva dopo 7,8 s); la pagina del broker 2,8 s; il pannello dei lotti a 28,6 s; fine a 30,2 s. Prove: `/tmp/libreFolio_i_l50_probe_base{.log,_load.txt,_report.html,_steps_d3.txt}`.
  > - Una nota di `test-author` sul modello: in Playwright 1.61 qualunque `page.route` spegne la cache HTTP della pagina, quindi con la sonda ogni navigazione riscarica anche i file statici. Il confronto resta onesto perché la sonda c'è nei due giri; il tempo assoluto no, e non lo uso come misura del gate.
  > - **La cura** (fase 2 di `test-author`, sonda ancora dentro), come nel §4: i due helper senza `navigateTo`, la precondizione, il test di `:120` senza navigazione e senza `if`, `describe.configure({timeout: 60_000})` come prima istruzione del blocco FIFO, e `navigateTo(page, '/brokers')` esplicito in `resolveAllOpenLotsAsset` e `openBrokerGrowthChart`, subito prima dell'helper. `expect(` passa da 182 a 185, nessuna tolta o allentata. Nessun timeout di passo cambiato.
  >   - Verificato da `test-author` in `node_modules` (1.61): il `configure({timeout})` di un `describe` annidato non tocca il `mode: 'parallel'` del file, e vince il timeout dell'antenato più vicino, che vale dall'inizio del test, `beforeEach` compreso.
  > - **La cura con la sonda**, 2500 ms, solo `:437` a 1 worker (era `:410`; `:437` con la sonda nel file, `:429` nel file finale), carico 12,3 → 13,7: **verde in 23,1 s**.
  >   - `beforeEach` 17,2 s; la precondizione e la card 0,00 s: la seconda lista non c'è più.
  >   - La pagina del broker 2,8 s; il pannello dei lotti a 20,3 s invece di 28,6 (−8,4 s, quasi tutta la seconda lista della base); la prima riga dei lotti 2,9 s; fine a 23,2 s.
  >   - Prove: `/tmp/libreFolio_i_l50_probe_cure{.log,_load.txt,_report.html,_steps_d3.txt,_steps_d6.txt}`.
  > - **Il budget del blocco FIFO, sul campo**: la cura con la sonda a 3800 ms, carico 10,5 → 11,4, **verde in 34,6 s**.
  >   - Ha passato i 30 s sul pannello dei lotti (30,57 s): senza i 60 s del `describe` sarebbe caduta lì, sulla prima riga dei lotti.
  >   - `beforeEach` 25,9 s, di cui 16,4 s per `brokers-page[data-busy="false"]`, che ha un limite di 20 s (`ensureBrokerExists`). Con un backend ancora più lento cede quello, non i 60 s.
  >   - Prove: `/tmp/libreFolio_i_l50_probe_cure_d3800{.log,_load.txt,_report.html,_steps_d3.txt,_steps_d6.txt}`.
  > - **La forma finale** (fase 3 di `test-author`): la precondizione dei due helper diventa l'indirizzo, `toHaveURL(/\/brokers(?:[?#]|$)/)` col timeout di default, e la sonda esce. Il `beforeEach` esterno torna identico a HEAD, e il diff non ha più un pezzo lì.
  >   - Un'uscita per logout non passa il controllo: `loginUrl` scrive l'indirizzo come `/?redirect=%2Fbrokers`.
  >   - Il diff: +37/−14, solo la spec. `expect(` passa da 182 a 185: le due precondizioni e la card del test di `:120`.
  >   - Nessuna riga `expect(` tolta: le due del test di `:120` (l'URL e la pagina del broker) tornano identiche, fuori dall'`if`. Aggiunti solo `60_000` (il `describe`) e `8_000` (la card del test di `:120`); nessun `setTimeout` né `waitForTimeout`.
  >   - Prettier rc 0, tsc e2e con le sole 2 righe della base, `git diff --check` pulito (rifatti da me al passo 5).
  > - **Il limite di queste prove**: i giri con la sonda avevano la precondizione della fase 2 (`brokers-page` visibile). La forma finale cambia solo quella riga, e sulla lista costa quanto la precedente, 0,00–0,02 s (passo 4); le due differiscono solo per chi parte dalla Dashboard, che naviga prima. La forma finale non è passata sotto la sonda: l'hanno messa al lavoro i giri del passo 4.
  >
  > **⚠️ Fuori pista**:
  > - Il primo `test-author` era sincrono e non accetta messaggi; la fase 2 e la fase 3 le fa un secondo `test-author`, con il brief completo.
  > - Nella fase 2 `test-author` ha messo la precondizione su `brokers-page` visibile, con 8 s e non i 3 di default, per i test che partono dalla Dashboard, e mi ha proposto l'indirizzo come alternativa. Ho scelto l'indirizzo (§4 a): non cambia nessun tempo. Lo applica la fase 3, che toglie anche la sonda.
  > - `test-author` ha tolto anche il vecchio JSDoc doppio di `goToFirstBrokerDetail` («Returns false if no brokers exist»): contraddiceva l'helper già prima della cura, che non restituisce niente.
  > - La sessione si è interrotta verso le 01:2x per un errore di rete, dopo la fase 3 e prima del passo 4. Nessun giro era in volo: l'ultimo, la sonda a 3800 ms, era finito alle 01:18 con rc 0. Alla ripresa (01:46) ho riverificato HEAD, i 3 file, il diff, la porta e i processi: nessun giro da rifare.
- [x] **4. La cura, a 1 e a 4 worker, sotto carico** (2026-10-13).
  > **Note implementazione**:
  > - **1 worker** (`front-broker detail`): 37/37 verdi in 1,8 min (136 s di orologio; base 157 s), carico 16,5 → 44,4: durante il giro è partito altro lavoro sulla macchina. Il test di C-58 prende 3,27 s (base 3,12 s): `beforeEach` 2,53 s, poi la precondizione e la card a 0,00 s. Il più lento 4,68 s (base 5,57 s).
  > - **4 worker** (`--workers 4 front-broker detail`): 37/37 verdi in 1,0 min (92 s; base 135 s), carico 45,9 → 33,9, più alto della base all'avvio (39,7). Il test di C-58 prende 4,79 s (base 6,47 s): `beforeEach` 3,06 s (base 4,23 s), la precondizione e la card 0,02 s (base: la seconda lista, 0,88 s). Il più lento 7,00 s (base 13,07 s).
  > - **Una navigazione in meno, nei passi**: nessuno dei 25 test del blocco esterno naviga più verso `/brokers` nel corpo, a 1 e a 4 worker. La ricarica dopo gli hook resta in 3 test su 37, quelli del blocco P&L, che partono dalla Dashboard (base: 28). I 3 test axisBuilder navigano nel corpo dopo il login, come nella base.
  > - **Il test di `:120`** (ora `:133`) clicca la card e verifica l'URL e la pagina del broker, a 1 e a 4 worker. Nella base contava 0 card e finiva lì.
  > - **Le durate sono indicative**: il carico non si controlla, e a 1 worker la seconda lista costava solo 0,18 s di mediana. La prova del guadagno è quella deterministica del passo 3; qui conta che la spec intera, nella forma finale, sia verde sotto carico.
  > - Prove: `/tmp/libreFolio_i_l50_cure_w{1,4}{.log,_load.txt,_report.html,_steps_d1.txt,_navcost.txt}`.
- [x] **5. Gli statici** (2026-10-13), rifatti da me dopo la fase 3, da `frontend/` con i binari del lock.
  > **Note implementazione**:
  > - `prettier --check e2e/brokers/brokers-detail.spec.ts`: rc 0.
  > - `tsc -p tsconfig.e2e.json --noEmit`: rc 2 con le sole 2 righe della base, `e2e/onboarding-tour.spec.ts(863,21)` e `src/lib/types/files.ts(9,23)`.
  > - `git diff --check`: rc 0. Questo piano è nuovo e `git diff --check` non lo vede: nessuno spazio a fine riga, controllato con grep.
  > - Nessun percorso assoluto nei file del checkpoint; `expect(` 182 → 185. Il diff della spec è in `/tmp/libreFolio_i_l50_cure.diff`.
- [x] **6. C-58 nel backlog** (2026-10-13): chiusa con la prova del passo 3 e i giri del passo 4. Il testo originale resta dopo «Era:».
- [x] **7. La riga della scansione nel piano 49**, §5 (2026-10-13).
  > **Note implementazione**: una voce in fondo al §5 del piano 49: il metodo, il conto (32 file, 94 attese, 43 finestre lette tutte a mano, più i 29 LATE, i 2 FACTORY e il tracker di `risk-mocks.ts`), 0 corse reali, i limiti, i log `/tmp/libreFolio_i_l49m_*`. I numeri vengono dal totale di `…_scan.log` e dal mio rapporto del lotto 49.
- [x] **8. Il checkpoint** (2026-10-13): manifest con i blob, due commit proposti (la spec; il journal), messaggi in ASCII. Gli 8 punti del §8 sono fatti. Porta 6157 libera; poi FROZEN.
  > **⚠️ Fuori pista**: rileggendo il messaggio della spec contro il diff, «come i blocchi fratelli» non era esatto. Il blocco FIFO è annidato nel blocco esterno, mentre axisBuilder e P&L sono al primo livello. Ora il §4 (b) e la voce C-58 del backlog dicono «i blocchi axisBuilder e P&L», come il commento nella spec.

## 8. Definizione di fatto e selettori

- **I selettori**, uno alla volta sulla 6157, col prefisso `PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py test --test-port 6157 --data-dir /tmp/librefolio-r2-i-charts`:
  - la spec intera a 1 worker: `front-broker detail`;
  - la spec intera a 4 worker: `--workers 4 front-broker detail`.
  - Se un E2E scade sotto carico, si rilancia da solo prima di indagare.
- **Fatto quando**:
  1. la base è misurata a 1 e a 4 worker, con le durate dei passi e il carico;
  2. la cura è quella del §4, e le asserzioni sono invariate o più strette: nessuna riga `expect(` tolta o allentata nel diff;
  3. la spec intera è verde a 1 e a 4 worker sotto carico, e i passi mostrano una navigazione in meno;
  4. la prova deterministica del §5: con lo stesso ritardo, la base scade a 30 s e la cura passa; la sonda non è nel diff finale;
  5. tsc e2e non aggiunge errori alle 2 righe della base, `prettier --check` dà rc 0, `git diff --check` è pulito;
  6. C-58 è chiusa con la prova, oppure aggiornata con le misure;
  7. la riga della scansione è nel piano 49, §5;
  8. la porta 6157 è libera, e il checkpoint è consegnato con manifest e messaggi.
- **Il CHANGELOG**: nessuna riga, il lotto tocca solo un test.
