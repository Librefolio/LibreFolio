# G · Gallery deterministica (workstream G)

> Aperta il 14/10/2026 dal coordinatore, insieme al [programma colori](../README.md); fino al 14/10 sera era
> `Phase_0/56_galleryDeterminism`.
> **Scopo:** la gallery della documentazione è la rete di sicurezza dei lavori sui colori: il workstream R deve
> dimostrare «stesso aspetto» con un diff dello stesso giorno. Oggi la gallery cambia anche da sola: questo lavoro la
> rende ripetibile.
>
> **✅ Chiusa il 15/10/2026:** DoD raggiunta con la misura `g-final3`
> ([piano](plan-phase00GalleryDeterminism.prompt.md), passo 6 e §1). Resta nel backlog G-11.
>
> **Riferimento attuale (16/10, G-13):** `g-ref13-r3`, con le maschere e la stabilità della coppia del rumore
> `g-ref13__r1__vs__r2`. Dettagli: [analisi G-13](evidence/analysis-g13-2026-10-16.md).

## Il problema, misurato

**Misura del 14/10/2026** (`27228466c`): due esecuzioni complete e identiche (`baseline-r1`, `baseline-r2`),
confrontate pixel per pixel con `scripts/visual_review/gallery_tool.py`.

- **Immagini:** 2.077 identiche e 715 cambiate, di cui 404 sotto lo 0,1 % dei pixel.
- **Schermate:** **57 stabili, 74 con rumore minimo, 19 medio, 27 instabili.**
  Dettaglio per schermata in [`evidence/stability-2026-10-14.md`](evidence/stability-2026-10-14.md).
- **Cause viste nei confronti:**
  - `auth/*`: lo sfondo animato del login non è congelato; onde e linee sono in una fase diversa a ogni esecuzione
    (11–24 % dei pixel);
  - `*/fifo-lots-panel`, `*/fifo-lots-wac-chart`: tutto il pannello è spostato di pochi pixel in verticale
    (scorrimento), quindi tutto «cambia» (14–38 %);
  - altre instabili da analizzare: `assets/detail-classification` (fino al 60 %), `media/asset-picker-modal`,
    `brokers/import-modal`, `assets/detail-signals`, `brokers/positions-holdings-table`, `settings/user-preferences`,
    `files/static-grid`; 6 immagini cambiano altezza (`brokers/edit-modal`, `settings/global-settings`, `brokers/detail`).
- **Test che falliscono sotto carico** (esecuzioni complete a 10 worker, solo desktop, insieme diverso ogni volta):
  - r1: 5 falliti. Login fermo su «auth-loading» per 30 s in 4 test del primo blocco, più
    `Dashboard Risk › what-if crisis replay`, dove il menu degli scenari contiene la voce ma
    `chooseReplayPreset` non si ferma mai su «Global Financial Crisis»;
  - r2: 4 falliti. Il popup di aggiornamento al login e tre modali delle transazioni (lista, picker, promote-merge).
  - Tutti passati in un secondo tentativo isolato (`--no-populate --desktop-only -w 5`). **Non sono classificati:**
    vanno analizzati con la skill `test-triage` prima di chiamarli instabili.

**Misura finale del 15/10/2026** (`2338aaf79`, `dev_release2` con il checkpoint 1 di G): due esecuzioni complete a 6
worker (`g-final3-r1`, `g-final3-r2`), entrambe pulite per `live_price_check`. Analisi per schermata:
[`evidence/analysis-final-2026-10-15.md`](evidence/analysis-final-2026-10-15.md); numeri grezzi:
[`evidence/stability-2026-10-15.md`](evidence/stability-2026-10-15.md).

- **Immagini:** 2.107 identiche, 717 cambiate, nessuna di altezza diversa.
- **Schermate:** **40 stabili, 112 con rumore minimo, 19 medio, 6 instabili** (erano 27). Delle 27 del 14/10, 8 sono
  ora stabili e 16 con rumore minimo.
- **Le 6 instabili:**
  - 2 di solo contenuto, accettate: l'ordine delle immagini del seed (`media/asset-picker-modal`) e quello dei due file
    del set (`brokers/import-nway-compare`);
  - 4 di inquadratura, corrette nel checkpoint 2 di G: `assets/detail-measures` e `-active` e
    `settings/about-plugin-diagnostics` su mobile, la pagina dietro il modale di `settings/scheduler-config`. Verificate
    da sole due volte: tutte stabili o con rumore minimo, salvo l'header di 1 variante di `detail-measures` (mobile es
    chiaro, backlog G-11).
- **Le 19 medie:** contenuto (orari, account usa e getta, codici casuali, durate, ordine dei file) e due residui di
  resa (le celle fissate della tabella dei lotti, l'antialiasing dei canvas RSI e MACD).
- **Nessun test rosso a 6 worker.** A 10 worker la macchina satura (carico 65, 8 rossi in 10 minuti, che da soli
  passano): il toolkit usa `-- --workers 6`.

## Corsia e confini

- **Corsia:** 6153 + `/tmp/librefolio-r2-g`. Una sola esecuzione per volta; mai `--force`.
- **File propri:** `frontend/e2e/gallery.spec.ts`, `frontend/e2e/fixtures/gallery*.ts` e, se serve, il congelamento
  delle animazioni solo per la gallery.
- **Vietato:** cambiare l'aspetto dell'app per far tornare i conti. Un componente non va modificato per stabilizzare uno
  screenshot senza l'accordo del coordinatore.
- I test li scrive `test-author`.
- **Definition of done:** una nuova misura di rumore (due esecuzioni dello stesso giorno) con le instabili ridotte al
  minimo spiegabile, e i fallimenti sotto carico analizzati, corretti o documentati. ✅ 15/10, con `g-final3`.
