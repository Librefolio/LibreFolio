# Piano — K / step 15: la scansione delle barre e il gutter della scrollbar

> Assegnato dal coordinator il 02/10 (`front-utility toolbar-width-sweep` 13/15 nella sua lane 6157: rossi `dashboard ›
> fr` e `› es`). Viene dopo lo step 14
> ([`plan-phase00TaxonomySelectStep14TooltipTeardownFixture.prompt.md`](plan-phase00TaxonomySelectStep14TooltipTeardownFixture.prompt.md)).
> Test rossi prima (test-author), un solo checkpoint alla fine.

| | |
|---|---|
| **Baseline** | `23828b411` (= `dev_release2`; il merge ha portato solo `CHANGELOG.md` e `TODO_FUTURI.md`: il codice è quello dello step 14) |
| **Lane suite** | `--test-port 6155 --data-dir /tmp/librefolio-r2-k`; ogni comando col preambolo `PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc` |
| **Copia di prod** | non serve per (a); per (b) solo se il developer la vuole |
| **Condivisi** | nessuno per (a): lo spec è di K. La config Playwright e le fixture condivise **non** si toccano (punto 4: solo valutazione) |

## Analisi (02/10, sola lettura, sonde in `/tmp/libreFolio_k15_*.mjs|log`)

**Il rosso dipende dall'host, non dal codice.** Lo stesso codice era 15/15 il 30/09. Oggi l'host usa le scrollbar classiche:
`AppleShowScrollBars = Automatic` con un mouse collegato; in modalità headed il gutter misura 15 px. Il gutter viene da
`scrollbar-gutter: stable` su `html` (`app.css:57`, in vigore da luglio).

**Il meccanismo, misurato.**
- In headless Playwright passa `--hide-scrollbars`. Chromium nasconde la scrollbar ma il layout **riserva comunque** lo
  spessore del tema, 15 px:
  - `documentElement.getBoundingClientRect().width` vale 305;
  - `clientWidth` e `innerWidth` valgono entrambi 320.
- Sulla dashboard vera: la barra è 1347 a vw 1700 e 239 a vw 320, cioè `vw − 338 − 15` e `vw − 66 − 15`.
- Quindi la misura proposta, `innerWidth − clientWidth`, in headless legge **0**: non vede il gutter. La misura che lo vede
  è `innerWidth − documentElement.getBoundingClientRect().width`: 15 sia headless sia headed, anche sulla dashboard vera.
  Vale anche per la cura di S7-E4 di I.
- L'intestazione dello spec (`:17-21`, «headless: no scrollbar gutter») è falsa su un host con scrollbar classiche.
- Anche il controllo della pagina, `scrollWidth − clientWidth`, in headless conta il gutter nascosto come spazio
  disponibile. Su un host così sottostima di g lo sconfinamento della pagina.

**Chi esce dalla barra:** il pulsante `broker-filter-trigger` (`dashboard/+page.svelte:697-708`). Ha `whitespace-nowrap` e
nessun `min-w-0` né `truncate`. Divide la riga impilata con la valuta (`w-28`). La sua etichetta è «Tous les courtiers» /
«Todos los brókers», oppure, **con un solo broker selezionato, il nome del broker** (dato dell'utente, fino a 100
caratteri). Misurato sulla barra di 254 px, cioè un telefono da 320 px senza gutter:

| etichetta | caratteri | pulsante | fuori dalla barra |
|---|---|---|---|
| «Tous les courtiers» | 18 | 146,5 px | no, entra per 0,5 px |
| «Interactive Brokers» (un broker dei mock) | 19 | 153,2 px | **+6,2 px** |
| «Interactive Brokers Ireland Ltd» | 31 | 218,1 px | **+71,1 px**, e ancora +1,1 sulla barra di 324 |

Il difetto (b) quindi non è solo del gutter: un nome di broker appena più lungo dell'etichetta esce dalla barra anche su
un telefono.

**Punto 4: una cura globale nella config Playwright.** Misurato in headless, sulla pagina con `scrollbar-gutter: stable`:

| variante | spazio riservato |
|---|---|
| default (`Desktop Chrome`) | 15 px |
| argomento di lancio `--enable-features=OverlayScrollbar` | 15 px |
| senza `--hide-scrollbars` (`ignoreDefaultArgs`) | 15 px |
| CSS iniettato da fixture `html{scrollbar-gutter:auto}` | 0 |
| CSS iniettato `::-webkit-scrollbar{width:0}` | 0 |
| CSS iniettato `html{scrollbar-width:none}` | 0 |
| progetto `mobile` (iPhone 14 Pro Max) | 0, scrollbar overlay |

Nessun argomento di lancio basta su macOS. Funziona solo un CSS iniettato da una fixture condivisa, ma cambia il layout
sotto test: tutti gli E2E misurerebbero un layout che chi ha scrollbar classiche (Windows, Linux, Mac col mouse) non
vede. Linux in CI non misurato.

## Decisioni

- **Coordinator (02/10)**:
  - (a) autorizzata, solo test, nello spec di K;
  - (b) prodotto, decide il developer;
  - (4) solo valutazione, ci vuole un permesso.
- **(a), correzione della misura**: il gutter si legge con `innerWidth − documentElement.getBoundingClientRect().width`, non
  con `innerWidth − clientWidth`, perché in headless quest'ultima legge 0 (misurato).
- **(b), developer (02/10)**: **sì, il pulsante si stringe e tronca l'etichetta con i puntini** (raccomandazione di K).
  Scartate: andare a capo (non risolve un nome singolo più lungo della riga) e lasciare così. Precisazione dopo la
  domanda: nel menu a tendina i nomi molto lunghi sono **già** troncati oggi (`w-56`, `span.truncate`); il nome intero
  resta nel DOM e quindi nel nome accessibile.

## Voci

### a. Lo spec misura il gutter e resta nell'intervallo che dichiara

Al caricamento lo spec misura il gutter `g`, poi scandisce da 1700 a `320 + g`: le barre restano nell'intervallo
dichiarato (pavimento 254) su ogni host. Il report e l'intestazione dicono quanto vale `g`.

Anche il controllo della pagina misura contro la larghezza del layout, non contro `clientWidth`, con un controllo positivo:
una scatola appesa oltre il layout ma dentro `innerWidth` deve risultare. Su questo host è rossa prima e verde dopo.

### b. Il pulsante del broker non esce più dalla barra (se il developer dice sì)

Raccomandazione: il pulsante si stringe e tronca l'etichetta con i puntini (`min-w-0` sulla catena, `truncate`
sull'etichetta, `max-w-full`). Il nome intero resta nel menu a tendina, e il nome accessibile non cambia. Test rosso
prima: un broker del test con un nome lungo, selezionato, a 320 px, su qualunque host.

## Passi

- [x] **15.0 Analisi** — sola lettura e sonde: baseline `23828b411` (pulita), meccanismo misurato, offender e punto 4.
  ✅ 2026-10-02.
  > **⚠️ Fuori pista**: la prima sonda delle varianti misurava `innerWidth − clientWidth` e dava 0 ovunque in headless: era
  > la misura sbagliata, non l'assenza del gutter. Rifatta con `getBoundingClientRect` (risultati sopra). Due server
  > della lane avviati da K per le sonde (lettura sola, login dell'utente E2E), fermati; porta 6155 libera dopo ognuno.
- [x] **15.1 (a) rosso** (test-author) — lo spec com'è nella lane: 13/15, rossi `dashboard › fr|es`. ✅ 2026-10-02.
  > **Note implementazione**: `/tmp/libreFolio_k15_sweep_before.log`: 13/15, rossi `dashboard › fr` (+4,5 px a vw 330,
  > +14,5 a vw 320) e `› es` (+4,2, +14,2); l'offender è il wrapper del pulsante del broker, `div.relative «Tous les
  > courtiers»`. Stessi numeri del coordinator.
- [x] **15.2 (a) cura nello spec** (test-author) — gutter misurato, scansione fino a `320 + g`, controllo della pagina sulla
  larghezza del layout con il suo controllo positivo, intestazione corretta; 15/15. ✅ 2026-10-02.
  > **Note implementazione** (solo `toolbar-width-sweep.spec.ts`, +155/−51):
  > - `g = innerWidth − <html>.getBoundingClientRect().width`, letto dopo il caricamento e prima dell'orologio; fuori da
  >   0–30 px è una precondizione rossa che dice il valore;
  > - larghezze: da 1700 ogni 10 px finché `vw ≥ 320 + g`, poi esattamente `320 + g`; con `g = 0` sono le 139 di prima
  >   (verificato); titoli invariati; report e allegato dicono `1700 → 335 px (320 + gutter 15)`;
  > - controllo della pagina: il bordo è quello del box di `<html>`; lo sconfinamento è la scatola più lontana oltre quel
  >   bordo, con le regole di salto già usate per i colpevoli, testi compresi (prima li vedeva `scrollWidth`); i
  >   pseudo-elementi restano un punto cieco, dichiarato nell'intestazione;
  > - controllo positivo della pagina: una scatola `g/2 + 4` px oltre il layout (qui 11,5 px, ancora dentro la finestra) deve
  >   risultare per nome. **Rossa** con la misura vecchia (`/tmp/libreFolio_k15_page_control_red.log`: «page +-3 px»),
  >   verde con la nuova (`…_green.log`);
  > - **dopo**: 15/15 in 3,7 min (`/tmp/libreFolio_k15_sweep_after.log`); gutter 15, 138 larghezze tutte assestate; ogni
  >   barra misura 1347 a 1700 e **254 (oneColumn) a 335**; nessuno sconfinamento. Prettier e `tsc -p tsconfig.e2e.json`
  >   puliti.
  >
  > **⚠️ Fuori pista**: nel brief K aveva scritto che `scrollWidth` non scende mai sotto `clientWidth`. Il test-author ha
  > misurato il contrario: headless, dietro il gutter, `clientWidth` vale 320 e `scrollWidth` 305 (il −3 del controllo
  > rosso viene da lì). La misura sulle scatole resta quella giusta; quella frase non è entrata nell'intestazione.
- [x] **15.3 (b)** — secondo la decisione del developer: troncare. ✅ 2026-10-02.
  > **Note implementazione**:
  > - **test rosso** (test-author): `frontend/e2e/portfolio/dashboard-broker-filter-label.spec.ts`, registrato come
  >   `front-portfolio broker-filter-label` in `_frontend_portfolio.py` (solo in aggiunta). Un broker del test con un nome
  >   di 57–61 caratteri, selezionato da solo; layout di 320 px (viewport `320 + g`, barra 254) e 2560 px (oneRow), con
  >   quattro controlli positivi; il broker è cancellato per id alla fine. **Rosso** sulla base
  >   (`/tmp/libreFolio_k15_broker_label_red.log`): solo l'ultima asserzione del test a 320, pulsante **+264,6 px** oltre la
  >   barra, nessun puntino; il test a 2560 verde. `check-orphans` pulito (93 spec); `tsc -p tsconfig.e2e.json` con 4
  >   errori preesistenti in altri file (`asset-detail.spec.ts:1395/:1397`, `onboarding-tour.spec.ts:863`,
  >   `src/lib/types/files.ts:9`), nessuno nello spec nuovo;
  > - **cura** (`dashboard/+page.svelte`): wrapper `relative min-w-0`, pulsante `min-w-0 max-w-full`, etichetta in
  >   `span.truncate`, freccia `shrink-0`, con un commento sul perché. Prettier pulito; `front build --debug` exit 0
  >   (svelte-check interno: 3 errori e 41 warning, la baseline);
  > - **verde** (`…_green.log`): 2/2.
  >
  > **⚠️ Fuori pista**: il controllo «nome intero» a 1280 px, come chiesto nel brief, sarebbe stato rosso anche con la cura
  > giusta: a 1280 la dashboard è in stackFilters e la riga valuta + broker è limitata a 390 px. Il test-author l'ha
  > spostato a 2560 (oneRow). Il primo test usava un viewport di 320 px, cioè un layout di 305 su questo host, sotto il
  > pavimento dichiarato; portato a `320 + g` prima del rosso.
- [x] **15.4 Regressioni** — prettier sui file toccati; `front check` (pavimento 3 errori); lo spec intero. ✅ 2026-10-05
  (in pausa dal 02/10 al 05/10, su richiesta del developer tramite il coordinator).
  > **Fatto**: sweep intero con (a) + (b) **15/15** (`/tmp/libreFolio_k15_sweep_final.log`, 3,8 min); prettier pulito sui
  > tre file frontend; nessun altro spec usa `broker-filter-trigger`.
  > `front-portfolio dashboard` (`/tmp/libreFolio_k15_dashboard.log`): 10 passati, **5 rossi, tutti in GrowthChart P&L**:
  > - 4 del gruppo noto «zoom-window»: «the 1W preset is offered» non visibile in line, candles e income (`:577`), più
  >   `:607` «candles aggregate coarser…», che va in timeout cliccando lo stesso preset;
  > - 1 del gruppo noto che dipende dal calendario: `:534` «income submode receives all six channels», `Expected: >= 3,
  >   Received: 1`.
  > Il 30/09 i rossi noti erano 7 (4 zoom-window + 3 di calendario): oggi due di calendario passano. Nessuno tocca la barra
  > dei filtri.
  >
  > **Alla ripresa (05/10)**:
  > - il coordinator conferma che i 5 rossi sono di I: i 4 «zoom-window» cercano helper che hanno lasciato
  >   `GrowthChart.svelte` con `e7773a143`, `:534` è nel gruppo di calendario noto. Le due cure sono in `dev_release2`
  >   (`6de5646a1`), dove il gate di I dava `front-portfolio dashboard` 24/24. La prova arriva sulla revisione combinata,
  >   dopo il merge di `dev_release2` in K;
  > - `front check` (`/tmp/libreFolio_k15_front_check.log`): «svelte-check found 3 errors and 41 warnings in 4 files», la
  >   riga della baseline; i 3 errori sono quelli noti (`TransactionFormModal.test.ts:787`, `:819`,
  >   `ToolExecutionMetrics.svelte:44`);
  > - `_frontend_portfolio.py`: righe solo aggiunte (`:31-42`, `:289-296`). ruff dà gli stessi 19 risultati, per regola, su
  >   HEAD e sul worktree, nessuno sulle righe nuove; black propone lo stesso riformattamento preesistente (121 righe) sulle
  >   due versioni, quindi niente viene dal codice nuovo;
  > - la lane è sopravvissuta alla pulizia di `/tmp` di macOS delle 00:01 (`app.db` del 02/10 presente); build più recente
  >   di ogni sorgente, quindi nessun rebuild.
- [x] **15.5 Handoff** — CHECKPOINT READY, FROZEN. ✅ 2026-10-05.
  > **Note implementazione**: tre commit proposti, messaggi e liste dei percorsi in `/tmp/libreFolio_commits/`
  > (`k-34-sweep-gutter`, `k-35-broker-filter-label`, `k-36-journal-15`, più `k-15-manifest.txt` con gli hash).
  > - **CHANGELOG proposto** (lo scrive il coordinator): 🐛 Dashboard: con un solo broker selezionato, un nome lungo
  >   nel filtro dei broker viene accorciato con i puntini invece di uscire dalla barra sugli schermi stretti.
  > - **Per il backlog del coordinator**: durante i 2 s di debounce il pulsante nomina già il broker, mentre la pagina mostra
  >   ancora i totali di tutti i broker, e niente dice che un ricaricamento è in arrivo (osservazione del test-author).
  > - **Privacy (richiesta del coordinator, 02/10)**: `/tmp/libreFolio_k_review_server.log`, il log del server di review
  >   sulla copia di prod del 29/09, **non esiste più** quando K arriva a cancellarlo (05/10, 09:48): con ogni probabilità
  >   l'ha rimosso la pulizia di `/tmp` di macOS delle 00:01, perché era fermo dal 29/09. K non l'ha toccato. Verificato con
  >   `ls` (nessun file con quel nome), nessun altro file di review rimasto in `/tmp`, nessuna cartella
  >   `librefolio-r2-k-prodcopy*`.

## Definizione di fatto

1. Lo spec verde su questo host (con scrollbar classiche) e invariato su un host senza gutter (`g = 0`).
2. (b): rosso prima, verde dopo, se approvata.
3. Porta 6155 libera, worktree con i soli file previsti.

## Commit

1. `test(e2e): measure gutter in toolbar width sweep` — `toolbar-width-sweep.spec.ts` (voce a, verde da solo: 15/15
   prima della cura b).
2. `fix(ui): truncate a long broker filter label` — `dashboard/+page.svelte`, `dashboard-broker-filter-label.spec.ts`,
   `_frontend_portfolio.py` (registrazione, solo in aggiunta).
3. `docs(journal): record K step 15` — questo piano.

Integrazione: il coordinator unisce il nuovo `dev_release2` in K dopo il checkpoint; sulla revisione combinata devono
essere verdi `front-portfolio dashboard`, `front-utility toolbar-width-sweep` e `front-portfolio broker-filter-label`
(ogni rosso passa prima da `test-triage`).
