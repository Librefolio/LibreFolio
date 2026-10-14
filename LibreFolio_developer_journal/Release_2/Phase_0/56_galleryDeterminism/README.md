# 56 · Gallery deterministica (workstream G)

> Aperta il 14/10/2026 dal coordinatore, insieme al [programma colori 55](../55_colorSystem/README.md).
> **Scopo:** la gallery della documentazione è la rete di sicurezza dei lavori sui colori: il workstream R deve
> dimostrare «stesso aspetto» con un diff dello stesso giorno. Oggi la gallery cambia anche da sola: questo lavoro la
> rende ripetibile.

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

## Corsia e confini

- **Corsia:** 6153 + `/tmp/librefolio-r2-g`. Una sola esecuzione per volta; mai `--force`.
- **File propri:** `frontend/e2e/gallery.spec.ts`, `frontend/e2e/fixtures/gallery*.ts` e, se serve, il congelamento
  delle animazioni solo per la gallery.
- **Vietato:** cambiare l'aspetto dell'app per far tornare i conti. Un componente non va modificato per stabilizzare uno
  screenshot senza l'accordo del coordinatore.
- I test li scrive `test-author`.
- **Definition of done:** una nuova misura di rumore (due esecuzioni dello stesso giorno) con le instabili ridotte al
  minimo spiegabile, e i fallimenti sotto carico analizzati, corretti o documentati.
