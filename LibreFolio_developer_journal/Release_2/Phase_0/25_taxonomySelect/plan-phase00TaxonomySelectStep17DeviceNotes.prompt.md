# Piano — K / step 17: note del developer dai dispositivi (footer di AssetModal, tipo nel confronto col provider; PWA nel backlog)

> Note del developer dalle verifiche sulla nightly `v1.1.0-436-g049d36c8d` (con gli step 13 e 15), inoltrate dal
> coordinator il 06/10 alle 14:33. Viene dopo lo step 16 e il suo round 1
> ([`plan-phase00TaxonomySelectStep16Round1-TreeSelectTeardown.prompt.md`](plan-phase00TaxonomySelectStep16Round1-TreeSelectTeardown.prompt.md)).

| | |
|---|---|
| **Baseline** | `e6f1bee25`, treno 2 (`dev_release2` `ebf4752e2` con la famiglia Risk, più i commit del round 1 `2575aeaf2` e `a86f4a41b`); validata il 06/10 (vedi «Validazione del treno 2») |
| **Lane suite** | `--test-port 6155 --data-dir /tmp/librefolio-r2-k`, preambolo `PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc` |
| **Dati** | solo sintetici (i mock della corsia); nessuna copia di prod |
| **Triage** | coordinator, 06/10, testuale qui sotto |
| **Superfici** | voce 15: `frontend/src/lib/components/assets/AssetModal.svelte` e `frontend/e2e/assets/asset-mobile-layout.spec.ts`; voce 17: `frontend/src/lib/components/assets/ProviderComparisonModal.svelte` e il suo test, più (secondo la decisione del developer) `utils/assetTypes.ts` e `AssetModal.svelte` (`compareStringField`) |
| **Fuori perimetro** | 12 (Android) e 13 (iPhone): backlog, con le domande che porta il coordinator |

## Le note del developer (testuali)

- **12 · Android** (non spuntata): «Fatto ma nulla, nel caricamento purtroppo c'è quel fastidiosoquadrato nero ancora».
- **13 · iPhone** (spuntata): «Sulla home ha sempre funzionato, il problema è quando la apri nel breve momento in cui
  carica.»
- **15 · Telefono** (non spuntata): «Si funziona, ma la lineetta del footer si sposta lievemente in alto e le si guarda
  attraverso. Preferirei poi che attivo e benckmark fossero distribuiti sulla riga con logica giustificata».
- **17 · Borsa Italiana** (spuntata): «Si ma usando `IE00B579F325` mi dice che il provider propone, al posto di etf
  stock, e lo fa senza icone, direi che nella modale del confronto, per il tipo, sia a valore attuale che a valore
  provider se si mette icona e nome del tipo proposto nella lingua impostata è meglio».

## Triage del coordinator (06/10, testuale)

> «**Ora, un checkpoint piccolo per ciascuno**: TreeSelect → **15** → **17**.
> - La variante «giustificata» della 15 è esattamente la richiesta del developer nella nota 15 («toggle
>   Attivo/Benchmark giustificati»): nessuna domanda, procedi.
> - La 17 parte con icona e nome localizzato. La **regola di famiglia** (a/b/c) la chiedo io al developer quando ci
>   arrivi: avvisami e non decidere da solo.
> - **13 e 12 vanno nel backlog** della mia proposta di triage. Le prove per la 12 e il «subito o backlog?» per la 13
>   li chiedo io al developer nel triage; anche le intestazioni `no-cache` restano lì per ora.
> - L'osservazione su IE00B579F325 (ETC sull'oro registrato come `ETF_STOCK`) la riferisco io al developer.»

## Analisi (sola lettura, 06/10)

Sonde sulla corsia 6155 col DB dei mock, in Chromium e WebKit (Playwright locale), a 390 e 360 px, solo dati sintetici.

> **⚠️ Fuori pista**: per le sonde ho avviato un `dev.py server --test` sulla 6155, con la data-dir dei mock della
> corsia.
> - Nessun dato del developer; il server è stato spento e la porta liberata.
> - La regola iniziale riserva la 6155 ai soli `dev.py test`: l'ho segnalato al coordinator.
> - Risposta del coordinator (06/10, testuale): «La deroga va bene: era la tua corsia, con i dati finti, e la porta è
>   stata liberata. Annotala nel piano come fuori pista. Per le prossime sonde usa la **6165** (la tua porta di review),
>   sempre con la data-dir della corsia.»

### Voce 15 — il footer di AssetModal

- **Le si guarda attraverso.**
  - `ModalBase .modal-content` è una colonna flex con `max-height: 90vh` e `overflow: visible` (`allowOverflow`,
    `AssetModal.svelte:1691`).
  - Il corpo è il `<fieldset>` con `max-h-[70vh] overflow-y-auto` (`:1701-1703`).
  - Su un telefono header (61) + 70vh + footer superano il 90vh, e il flex restringe il box del fieldset.
  - **Chromium** però continua a disegnare (e a colpire col puntatore) il contenuto scrollabile fino a 70vh: sotto il
    footer, che è trasparente. WebKit ritaglia correttamente.
  - A 360×640: box di 376 px contro i 448 di 70vh, cioè 72 px di modulo sotto il footer;
    `document.elementFromPoint` trova il modulo in 13 punti su 621.
  - È la «lineetta che si sposta in alto»: il bordo del footer resta dov'è, e il modulo continua sotto di lui. Gli
    ultimi 40–72 px del modulo si vedono solo attraverso il footer.
  - Un `min-h-0` sul fieldset non cambia nulla. Un contenitore `div` di scorrimento attorno al fieldset porta i punti
    da 13 a 0 su 621.
  - Nessun altro modale ha un fieldset che scorre: il difetto è solo qui.
- **Interruttori non giustificati.**
  - Il gruppo di sinistra è un'unica riga `flex-wrap` di 7 elementi.
  - A 360 px l'interruttore di Benchmark va a capo da solo, 30 px sotto la sua etichetta.
  - A 390 px stanno sulla riga, ma ammassati a sinistra: Benchmark finisce 24 px prima del bordo destro di Salva.
- **Variante scelta (C), provata iniettando il CSS.**
  - Due gruppi indivisibili, ciascuno con informazione, etichetta e interruttore; Benchmark `ml-auto`, allineato a
    destra anche quando va a capo.
  - Spazi più stretti sotto `sm`; separatore nascosto sotto `sm`.
  - A 360 px una riga in tutte e 4 le lingue con i font della sonda.
  - A 320 px Benchmark va sulla seconda riga, a destra.
  - Da `sm` in su l'aspetto è quello di oggi.
- **Font.** `Inter` non è ospitato dall'app: lo stack ricade su `system-ui` (SF su macOS, Roboto su Android, DejaVu
  nella CI Linux).
  - Che stiano «su una riga» dipende dal font. I test fissano solo invarianti valide con ogni font:
    - niente modulo sotto il footer;
    - ogni interruttore sulla riga della sua etichetta;
    - Benchmark allineato al bordo destro di Salva.

### Voce 17 — il tipo nella modale di confronto

- `ProviderComparisonModal.svelte:318` e `:337` mostrano `asset_type` come codice grezzo, in monospace: niente icona,
  niente nome nella lingua.
- La libreria `borsa_italiana_scraping` 0.3.2 ricava il tipo dall'URL (`scheda.py:181-198`): tutto ETFplus, ETC
  compresi, è «etf», cioè `ETF`, la famiglia generica.
  - `compareStringField` (`AssetModal.svelte:1066-1092`, chiamato a `:1129`) segnala la differenza.
  - La modale la preseleziona (`:120`).
  - Così «Applica» declassa un sottotipo (`ETF_STOCK`) alla sua famiglia (`ETF`).
- La migrazione 004 non c'entra: non tocca `asset_type`.
- Cura: icona e `assets.types.*` in entrambi i riquadri, senza chiavi i18n nuove.
  - La regola di famiglia è sospesa: la decide il developer tramite il coordinator.
  - Backend di Borsa invariato: «ETC/ETN» → `ETF` è il residuo corretto.

### Voci 12 e 13 (backlog)

- **12 (Android).**
  - Il quadrato nero non può venire dalle icone attuali, che sono opache.
  - Ipotesi, in ordine:
    1. icona vecchia in cache o nella WebAPK: stessi URL e nessun `Cache-Control` su manifest e icone,
       `backend/app/main.py:450-464`;
    2. lo splash di Android 12+ in tema scuro;
    3. lo splash interno scuro.
  - Servono le prove del developer.
- **13 (iPhone).** Non c'è nessun `apple-touch-startup-image`, quindi iOS mostra uno schermo vuoto fino al primo
  paint. La cura (immagini d'avvio dal generatore) è di taglia M.

### Conflitti

- `AssetModal.svelte`, `ProviderComparisonModal.svelte`, `ModalBase.svelte` e `asset-mobile-layout.spec.ts`: nessun
  ramo attivo li tocca.
- `assetTypes.ts`: la famiglia Risk cambia solo il commento di `:61-62`.

## Validazione del treno 2 (`e6f1bee25`, 06/10 21:15–21:45)

Corsia 6155, un comando per volta, prima di toccare la voce 15.

- **`front check`**: 0/0 al secondo giro.
  - **⚠️ Fuori pista**: il primo giro ha dato 50 errori in 17 file, tutti per tipi della famiglia Risk mancanti
    (`RiskEligibilityLevel`, `asset_eligibility_api_v1_risk_eligibility_post`, `message_i18n_key`…).
  - Verdetto: **ambiente**. Il client API generato (`generated.ts` e `openapi.json`, ignorati da git) era del
    `front build` delle 20:35, prima del merge della famiglia.
  - `front check` non lo rigenera, `front build` sì (`cmd_fe_build` → `cmd_api_sync`, export in-process).
  - Segnalato al coordinator: dopo un merge che cambia l'API, `front build --debug` prima di `front check`.
- **`front build --debug`**: ok, svelte-check 0/0.
- **`component-unit`**: exit 0, 108 file, 2721/2721, nessun errore non gestito.
- **`core-unit`**: exit 0, 113 file, 3336/3336.
- **E2E**: `select` 17/17, `asset-modal` 17/17, `asset-detail` 29/29, `asset-browse` 8/8, `asset-list` 28/28.
- La sovrapposizione di `assetScope` è chiusa dalla famiglia (`863834086`): `asset-browse` è verde sulla revisione
  combinata.
- Log: `/tmp/libreFolio_k_t2_*.log`.

## Passi

### Voce 15 (checkpoint a sé)

- [x] **17.1 Rosso** (test-author, solo `asset-mobile-layout.spec.ts`). ✅ 2026-10-06.
  - Niente modulo sotto il footer a 360×640 e 360×800.
  - Interruttori giustificati: it 390 con Attivo acceso, it e es 360 con Attivo spento, es 320.
  - Controllo a 1280×720.
  > **Note implementazione**:
  > - Sezione nuova in fondo allo spec, «… (K step 17, item 15)», 7 test; voce `17.15` nell'intestazione.
  >   `openAssetModal` accetta una `lang` facoltativa (`setLanguage` prima di aprire il modale).
  >   - Una barriera di stabilità, `settleModal`, senza attese a tempo.
  >   - Le misure finiscono allegate al report.
  > - Comandi: `dev.py test … front-asset asset-mobile-layout "K step 17, item 15"`, poi lo spec intero.
  > - Esiti sulla baseline:
  >   - grep: 6 rossi e 1 verde (due giri);
  >   - spec intero: 6 rossi e 15 verdi. I 14 test esistenti restano verdi.
  > - **I rossi, ciascuno per la ragione attesa:**
  >   - 360×640: 175 punti su 475 della fascia dei controlli del footer contengono il modulo (`elementsFromPoint`);
  >     box 376 px contro 448 di 70vh.
  >   - 360×800: 100 su 475, con 40 px di fuoriuscita. È rosso, non una semplice guardia.
  >   - it 390, Attivo acceso: Benchmark finisce a x 326,4 e Salva a 350,0.
  >   - it e es 360, Attivo spento: l'interruttore di Benchmark sta 32 px sotto la sua etichetta (682 contro 650) e
  >     finisce a x 84 contro 320.
  >   - es 320, Attivo spento: solo il bordo di Salva (162,3 contro 280). Con i font di questo Mac l'etichetta va a
  >     capo con il suo interruttore, mentre l'icona d'informazione resta da sola sulla prima riga.
  > - Il controllo a 1280×720 è verde: finestra di 504 px (70vh), contenuto di 620 px, nessun punto sotto il footer.
  > - Prettier pulito; `tsc` non segnala nulla in questo file.
  >
  > **⚠️ Fuori pista**: i chip dei provider sotto «Cerca online» arrivano dopo `data-snapshot-ready`. A 360 px
  > cambiano lo `scrollHeight` (759 contro 827) e quali campi finiscono sotto il footer, mai il verdetto.
- [x] **17.2 Cura** in `AssetModal.svelte`. ✅ 2026-10-06.
  - Un `div` di scorrimento attorno al fieldset (il blocco cambia rientro: `git diff -w` mostra solo le righe vere).
  - Due gruppi di interruttori; Benchmark `ml-auto`; `gap-1.5 sm:gap-2`; separatore `hidden sm:block`.
  > **Note implementazione**:
  > - **Corpo**: `<div class="min-h-0 max-h-[70vh] overflow-y-auto">` attorno al fieldset, con un commento sul perché.
  >   - Il fieldset tiene testid e attributi e perde `max-h`/`overflow`.
  >   - Prettier ha reindentato il blocco e messo il tag d'apertura del fieldset su una riga (`printWidth` 300).
  > - **Footer**:
  >   - contenitore degli interruttori `w-full sm:w-auto`;
  >   - due gruppi `shrink-0 gap-1.5 sm:gap-2` (informazione, etichetta, interruttore), quello di Benchmark `ml-auto`;
  >   - separatore `hidden sm:block`.
  >   - Da `sm` in su gli spazi sono quelli di prima: 8 px dentro i gruppi e 8 + separatore fra i gruppi.
  > - **Diff**: 463+/461−. Con `git diff -w` è 15+/13−: quasi tutto rientro.
  >
  > **⚠️ Fuori pista**: `asset-modal.spec.ts:190` («modal form is scrollable») verificava il `overflow-y` calcolato
  > del fieldset stesso, cioè l'elemento che la cura sposta di proposito. È diventato rosso (16/17).
  > - Verdetto del triage: test accoppiato alla struttura, non un difetto. Il comportamento (il modulo scorre in un
  >   riquadro di 70vh) resta.
  > - Il test-author l'ha riparato: il riquadro di scorrimento ora viene cercato risalendo dal modulo, deve stare
  >   dentro il modale ed essere limitato a 70vh. Risultato: 17/17.
  > - La mia ricerca preliminare non l'aveva visto, perché un `| head -20` aveva troncato i risultati di `e2e/`. La
  >   seconda ricerca, senza troncare, ha trovato soltanto usi di visibilità e attributi; la galleria usa
  >   `scrollIntoViewIfNeeded`, che vale con qualunque riquadro.
- [x] **17.3 Verifica e handoff.** ✅ 2026-10-06.
  - Comandi: `front check`, vitest `AssetModal*.test.ts`, `front build --debug`, E2E `asset-mobile-layout` e
    `asset-modal`.
  - CHECKPOINT READY.
  - Il corpo del commit dice che il diff è quasi tutto rientro, con il numero di righe vere secondo `git diff -w`
    (richiesta del coordinator, 06/10: «Nel corpo del commit scrivi che è quasi tutto rientro e quante sono le righe
    vere con `git diff -w`, così chi fa `blame` lo sa»).
  - Sonde future: sulla **6165**, con la data-dir della corsia.
  > **Note implementazione** (corsia 6155, un comando per volta):
  > - vitest `AssetModal*.test.ts`: 2 file, 66/66.
  > - `front build --debug`: ok, svelte-check 0/0. `front check`: 0/0.
  > - E2E:
  >   - `asset-mobile-layout`: 21/21, i 6 rossi diventati verdi;
  >   - `asset-modal`: 17/17 dopo la riparazione;
  >   - `tx-import-asset-inspector`: 5/5 (il modale dentro l'import).
  > - **Controllo visivo** sulla 6165 con la data-dir della corsia, come chiesto dal coordinator; screenshot
  >   `k17_shots/cured-*.png` nei file di sessione di K.
  >   - it 360×640 e 360×800, Attivo spento: nessun punto del modulo sotto il footer (0/204); Benchmark allineato a
  >     Salva (320/320); interruttori su una riga.
  >   - it 390, Attivo acceso: una riga, 350/350.
  >   - es 320: Benchmark va a capo con la sua icona, allineato a destra (280/280).
  >   - 1280×720: aspetto di prima (separatore visibile, Benchmark accanto ad Attivo).
  > - **Due commit proposti**, con i messaggi in `/tmp/libreFolio_commits/` e il manifesto `k-17-15-manifest.txt`:
  >   - `k-44-assetmodal-footer` per il codice e i due spec;
  >   - `k-45-journal-17-15` per il journal.
  > - **CHANGELOG proposto** (🐛, «Sign-in, app icons and small screens»): «On phones, the asset dialog no longer
  >   shows its form through the footer on Android, and the Active and Benchmark switches spread across the row —
  >   Benchmark on the right, also when it wraps.»

### Voce 17 (checkpoint a sé)

- [ ] **17.4 Domanda sulla regola di famiglia**, tramite il coordinator; la risposta del developer va scritta qui,
  testuale.
- [ ] **17.5 Rosso** (test-author): `ProviderComparisonModal.test.ts`, più l'helper e `providerLifecycle` se passa la
  regola.
- [ ] **17.6 Cura.**
- [ ] **17.7 Verifica e handoff.**

## Definizione di fatto

1. Ogni voce è rossa sulla baseline e verde dopo la cura, sui mock della 6155.
2. Le regressioni sono verdi e i controlli statici restano a 0/0 (`front check`).
3. Porte libere, nessun venv del worktree, nel worktree solo i file previsti.
