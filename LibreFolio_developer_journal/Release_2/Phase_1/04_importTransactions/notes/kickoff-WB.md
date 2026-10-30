# Brief — workstream W (backend) · Fineco (commissioni + guida) poi W-B86/D-W85-4 (avvisi sulle righe ignote)

**Worktree**: `/home/alfy/Documenti/02_myRepo/LibreFolio_prj/LibreFolio-worktrees/e-alfy-fluffy-meme`
**Branch**: `e-alfy-w-import-e-transazioni`
**HEAD di partenza (da verificare)**: `89e8b2e61` (= `dev_release2`, fast-forward fatto dal coordinatore).
**Corsia**: porta `6183`, cartella dati `/tmp/librefolio-r13-wb`.
**Piano**: `LibreFolio_developer_journal/Release_2/Phase_1/04_importTransactions/plan-phase01ImportTransactions.prompt.md`. Leggi solo: «W-B85 · Noto in silenzio, ignoto con avviso: analisi» (righe ~7583-7733, con la tabella K/U/E ~7650 e l'aiuto `RowSkips` ~7688), la cura Danske (~7734-7788), B-52 Fineco (~7916-8010). `Phase_1/PROSSIMI_LAVORI.md` righe ~107-134 (W-B86/W-B87). Backlog `Phase_0/BACKLOG_POST_1.2.md` sezione W (~6048; voci W-B85…W-B91 ~6762-6825).
**Un'altra sessione di W lavora in parallelo** sul frontend (K3a, #58) in un altro worktree: tu non tocchi `frontend/src/lib/features/transactions/**` né `frontend/e2e/transactions/**`.

## Passo A — Fineco (decisione del developer del 21/10: soluzione B)

### A1. Il conteggio doppio delle commissioni (`backend/app/services/brim_providers/broker_fineco/plugin.py`)
Oggi (variante B, più di 11 colonne, `has_commissions` ~:309) BUY e SELL prendono il **Controvalore** tal quale e, se `_sum_commissions(row) > 0`, si aggiunge una **FEE** a parte (~:418-436, `asset_id` della riga, stessa data, `FEE_CURRENCY="EUR"`). Ma nell'Excel vero di Fineco il Controvalore **contiene già** la commissione (acquisto) o l'ha già tolta (vendita). Cura decisa:
- **BUY** cash = −(Controvalore − commissioni), più la FEE −commissioni (asset della riga: va mantenuto);
- **SELL** cash = +(Controvalore + commissioni), più la FEE −commissioni;
- dividendi già netti: invariati; righe senza commissione: invariate; **variante A** (senza colonne di commissione, `fineco_variant_a.csv`): invariata.
Esempi veri (dall'Excel dell'utente, discussione #49):
| Riga | Prezzo | Controvalore | Commissione | Oggi | Dopo |
|---|---|---|---|---|---|
| BUY 27 ISH MSCI GLB | 18,07526 (eseguito 17,966) | 488,03 | 2,95 | −488,03 e FEE −2,95 = −490,98 | −485,08 e FEE −2,95 = −488,03 |
| SELL 2 Leonardo | 58,385 (lordo 59,86) | 116,77 | 2,95 | +116,77 e FEE −2,95 = +113,82 | +119,72 e FEE −2,95 = +116,77 |
| BUY 2 Leonardo, senza commissione | 57,26 | 114,52 | 0 | −114,52 | −114,52 |
| Dividendo | — | 0,93 netto (lordo 1,26, tassa 0,33) | — | +0,93 | +0,93 |
- **Prima i rossi** (`test-author`), in `backend/test_scripts/test_external/test_brim_providers.py`, classe `TestFinecoSafeRows` (~:2949): le righe sopra come fixture (**decisione del developer, 21/10: numeri SCALATI**: stessa struttura e stessa aritmetica — Controvalore = prezzo eseguito × quantità ± commissione, dividendo netto = lordo − tassa — ma quantità, prezzi e importi diversi da quelli dell'Excel dell'utente, che era per uso interno; nessun nome di persona), più: più colonne di commissione sulla stessa riga; `Rimborso` e obbligazioni con premio a scadenza (`io.model_bond_maturity` usa il Controvalore, ~:371-415); commissione maggiore del controvalore; «Aumento capitale»; i file senza colonne di commissione. Ogni caso che resta dubbio è una **domanda**, non una scelta tua.
- I `sample_reports/fineco*.csv` con commissioni hanno Controvalore = quantità × prezzo: erano una supposizione. Correggili perché rispecchino l'Excel vero e dillo nel checkpoint.
- `plugin_version` in su (oggi 1.3.0; il test `test_fineco_plugin_version_is_1_3_0` ~:3339 va aggiornato).
- Verdi: `external brim-providers` (contiene Fineco e il contratto per tutti i plugin), `services` della suite dei report set se esiste (`test_brim_report_sets.py`).
- Backlog: nuova voce **W-B92** nella sezione W (peso alto, numeri sbagliati), con il riferimento alla discussione #49.
- **Citazione dell'utente (impegno del developer, 21/10)**: l'utente GitHub **`@Xgialippo`** (discussione #49, https://github.com/Librefolio/LibreFolio/discussions/49) ha dato il permesso di essere citato e il developer gli ha promesso che **il suo nome sarà nel CHANGELOG**. Nelle righe proposte per il CHANGELOG (la 🐛 delle commissioni e la ✨/🔄 della guida) metti il ringraziamento, per esempio «thanks to [@Xgialippo](https://github.com/Xgialippo) for the real export and the screenshots (#49)». Nella guida una riga breve in fondo alle immagini («Screenshots courtesy of @Xgialippo»).
- CHANGELOG: proponi una riga 🐛 che dica che **i dati già importati restano sbagliati** e come correggerli (cancellare le transazioni di quel file e reimportarlo).

### A2. La guida in inglese (`mkdocs_src/docs/user/transactions/import/fineco.en.md`, agente `docs-writer`)
Riscrivi «How to Export» con il percorso vero, una immagine per passo, in `mkdocs_src/docs/static/broker-guides/fineco/Fineco_1.png … Fineco_6.png` (copiate da `/home/alfy/Documenti/02_myRepo/LibreFolio_prj/00_Materiale_Utenti/20261020_xgiallipo/immaginiperguidalibrefolio/Parte1.png … Parte6.png`, così come sono: **l'utente ha confermato il 21/10 alle 14:24 che vanno bene senza altre sfocature**; tieni comunque un file per immagine):
1. Home → **PORTAFOGLIO** (menu in alto) — Parte1; 2. barra a sinistra → **Reports** — Parte2; 3. **Ordini e contabili** — Parte3; 4. scheda **Titoli** (di default «Ultimi 3 mesi») → icona del **filtro** — Parte4; 5. periodo (per esempio «Ultimo Anno») → **Cerca** — Parte5; 6. in fondo **Esporta excel** → `Lista Titoli.xlsx` — Parte6.
Stile come `directa.en.md` (righe 11 e 17: `![…](../../../static/broker-guides/directa/Directa_1.png){ style="border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.15);" }`), didascalie e alt in inglese. Aggiorna il passo «save it as CSV» (il plugin oggi legge solo `.csv`), la tabella «What Gets Imported» (riga delle commissioni secondo A1) e una nota per chi ha importato con 1.2 o prima. **Non** usare l'immagine `SOLO-USO-INTERNO_*`. Solo inglese; le pagine it/fr/es non si toccano. Verifica: `mkdocs build` (stretto, in `flock`) e `mkdocs check-links`.

Consegna **CHECKPOINT READY (A)** e **FROZEN**: il coordinatore committa A prima di farti partire con B.

## Passo B — «noto in silenzio, ignoto con avviso» (solo dopo il via del coordinatore su A)
- **Aiuto condiviso** in `backend/app/services/brim_providers/_brim_io.py` (oggi senza aiuti di avviso): due codici comuni `rows_not_recognized` e `rows_unreadable`, con prova (righe, esempi) e `report_issue` nel `context` (come Danske, `broker_danske_bank/plugin.py:1551`; schema `BRIMNotice` in `backend/app/schemas/brim.py:502`). Un **test di contratto** parametrizzato su tutti i plugin (file nuovo, per esempio `test_brim_row_skips.py`).
- **W-B86 solo sui 4 plugin stabili** (decisione del 19/10): DEGIRO (`_notices` ~:487-498, `degiro_unknown_rows`: aggiungere `report_issue`), Crédit Agricole (`ca_securities_unknown_causale` ~:1085, `ca_unknown_causale` ~:1628; testi fissati dai test ~:1585, ~:1862), Scalable (`_scalable.py` `_NOTICES` ~:73-125; separare in `scalable_not_executed` ~:343 gli stati noti dagli ignoti), Directa (4 avvisi a stringa ~:260-277 da convertire in codici).
- **D-W85-4 versione minima** (approvata dal developer il 21/10): Revolut (`SKIP_TYPES` ~:90-93, salto ~:358), Trading 212 (~:87-92, ~:211), eToro (~:75-79, ~:235) emettono **un avviso aggregato con `report_issue`** per le righe saltate con effetto economico (split, distribuzioni di azioni, conversioni di valuta, commissioni notturne, rimborsi, SDRT); Trade Republic, Swissquote, IBKR passano dagli avvisi a stringa a un codice. L'import vero di quelle righe è dopo la 1.3.
- Le chiavi i18n nuove (`importWizard.brimNotice.*`, 4 lingue × 2 chiavi) sono un file condiviso: **chiedi al coordinatore prima di scriverle**; i frammenti i18n dei plugin (`broker_*/i18n/*.json`) sono tuoi. `BrimNoticeList.svelte` non dovrebbe cambiare: se serve, chiedi.
- Skill `brim-plugin` (regola 10, già scritta per Danske) e `brim_plugin_guide.md` (~:910) aggiornati; `plugin_version` in su per ogni plugin toccato.
- Verdi: `external brim-providers`, `external brim-degiro`, `external brim-scalable`, il contratto nuovo, `test_i18n_catalog_gate.py`.

## Non fare
- Nessuna decisione di prodotto (per esempio leggere `.xlsx` direttamente, la casella «di cui commissione» nel form, togliere l'etichetta Beta di Fineco): sono proposte del coordinatore al developer.
- Non toccare dati reali, non usare la 6040.

## Fatto quando
A: rossi verdi per la causa giusta, guida con 6 immagini e `mkdocs build` stretto verde, W-B92 nel backlog, riga CHANGELOG proposta, checkpoint A. B: aiuto + 4 plugin + avvisi minimi dei 6 plugin, contratto verde, doc e skill aggiornate, **CHECKPOINT READY** e **FROZEN**.
