# Ondata 4 — brief del coordinatore (22/10/2026), da strutturare in piano

Base: `dev_release2` = `e2d3b8a51` (treni 7 e 8, 80 commit non pushati). La 1.3 non esce prima di novembre: niente fretta,
meglio un'ondata corposa e ben ordinata come la 3 (10 lavori in parallelo, un comando pesante alla volta con `flock`).
Il developer vuole il piano prima di qualunque avvio.

## A. Decisi dal developer, da fare nella 1.3

| # | Lavoro | A cosa serve | Proprietario proposto | Note e dipendenze |
|---|---|---|---|---|
| A1 | **H-55 CDN + hash** | I PDF con caratteri cinesi, giapponesi e coreani si leggono anche con la CSP, senza fidarsi ciecamente del CDN. | **H** | Decisione del developer: le risorse del visore PDF le serviamo noi dall'immagine, come altre; il CDN resta solo come ripiego, e nel codice c'è l'hash atteso di ogni file scaricato (versione del pacchetto fissata, hash calcolati in build dalla copia in `node_modules`). Il ripiego del *motore* (uno script) va tolto. Rende verde `files.spec.ts:826`, l'unico rosso noto. Peso dei font CJK: ~47 MB Regular+Bold (H, ondata 3) → decidere quali servire noi e quali lasciare al CDN verificato. |
| A2 | **H-55 R4** | Anche i worker (visore PDF, calcoli del rischio) hanno una politica: uno script iniettato non può caricare codice da fuori neanche lì. | **H** | Stesso lotto di A1: R4 cambia proprio ciò che il worker del visore può scaricare. Serve una corsa completa. |
| A3 | **H-55-docs (R5)** | Swagger e ReDoc non caricano più librerie da jsDelivr senza versione né SRI. | **H** | Consiglio di H: servirle noi + spegnerle nel profilo managed. **Domanda ancora aperta al developer.** |
| A4 | **Y-41 completo** | Confrontare un asset con un cambio funziona davvero, dal dettaglio dell'asset e da quello del cambio (e nelle schede). | **Y** (store, schede, liste) + **X** (pagine di dettaglio) | Oggi le impostazioni delle schede dei cambi offrono un confronto con un asset, ma la scheda non lo disegna. Prima un'analisi: cosa manca in lista cambi, lista asset, dettaglio asset, dettaglio cambio. Un solo scrittore per file (X i dettagli, Y lo store e le liste). |
| A5 | **Q-N78-1k** | Una coppia di rettifiche collegate fra due broker tuoi non fa sparire il costo dal totale. | **W** (+ revisione di **MF**: la matematica finanziaria ha una sola casa) | Decisione: se diventa TRANSFER si tratta come tale; due rettifiche non collegate non si danno per la stessa cosa; per una coppia collegata, con entrambi i broker selezionati il totale fa 0, con uno solo si vede il movimento (= uscita al PMC). |
| A6 | **Testi E-25/E-26/E-7** | Le frasi di verifica email e del badge sono quelle scelte dal developer. | **E** (+ **A** per `UserRow`) | Confermato E-26-q3 (a). Aspettano risposta: E-26-q1 (testo A o B), E-26-q2 (riquadro verde o giallo), E-25-q1 (link «Torna all'accesso»), E7-Q4 (solo hover o anche pannello), E7-Q5 (testi fr/es). Lotto piccolo, parte appena il developer risponde. |

## B. Backup del cloud — L3 da rivedere a fondo

Decisioni del developer: `LibreFolio_developer_journal/Release_2/Phase_1/07_backupDocker/notes/BACKUP-decisioni-20261022.md` (Opzione 1 nella 1.3), schema e attacchi in
`BACKUP-schema-20261021.md`. Il vecchio piano L3 sta in
`LibreFolio/LibreFolio_developer_journal/Release_2/Phase_1/07_backupDocker/plan-phase01BackupDocker.prompt.md`
(7 602 righe, scritto prima delle decisioni): va **rivisto a fondo** alla luce del disegno nuovo, non applicato com'è.

Lavoro lato prodotto (§7 delle decisioni, ~13-17 giorni): L3 (busta a chiave pubblica, `kid`, keygen) · modo
«ripristino in corso» su volume vuoto · rotta di ripristino del pannello solo con biglietto L2 `backup:restore` (mai il
token L1) · ripristino da «busta + chiave del file» · rapporto di stage (amministratori nel backup, avviso sulle
credenziali, avviso forte se chi conferma non esiste nel backup) · documentazione self-hosted (zip in cartella +
backrest/restic) · test E2E di ripristino. La CSP `script-src` applicata, citata nel §7, **è già fatta** (H-55 v2, treno 8).

Richieste del coordinatore cloud, da mettere nella specifica:
- **specifica della busta con vettori di prova, come primo prodotto del lotto**: layout dell'intestazione, scambio di
  chiavi (X25519? HKDF con quale salt e info?), avvolgimento della chiave del file (AES-GCM? nonce?), calcolo del `kid`,
  nome e formato della variabile con la chiave pubblica;
- forma della rotta di ripristino (percorso, metodo, corpo in streaming?, campo della chiave, avanzamento a job,
  codici d'errore, limite di dimensione);
- variabile del modo «ripristino in corso», come si esce, cosa risponde `GET /api/v1/panel/status`;
- `sha256` dell'archivio in `GET /api/v1/backup/panel/jobs/{id}` a fine lavoro;
- la chiave d'istanza data dal pannello resta fuori dal backup (decisione 39).

Proprietario proposto: **B** (worktree `e-alfy-miniature-telegram`, branch `e-alfy-b-backup-e-docker`, 309 commit
indietro rispetto a dev, pulito) per L3 e il ripristino; **H** per rotta del pannello, biglietti L2 e modo «ripristino
in corso» (codice del pannello suo); revisione di sicurezza indipendente (Opus) prima del treno; **MF** no.
> _(parte del servizio gestito: nel repo privato `librefolio-cloud`)_

## C. Rimasti dall'inventario del 21/10, ancora da fare per la 1.3

| # | Lavoro | Proprietario proposto | Note |
|---|---|---|---|
| C1 | **N69c/N69d**: modo d'iscrizione in Utenti, pulsante «Guida» | **A** | Piano `02_accounts`, righe ~8352-8562; dipende dalla mappa delle guide (in dev). |
| C2 | **J-68**: un trasferimento nello stesso giorno ha solo l'arrivo (rimedio nel backend) | **J** | Backlog ~7956. |
| C3 | **R1 di J** | **J** | Aspettava Q1 di X: verificare se c'è ancora. |
| C4 | **J-71**: due copie in linea di `buildSyncTargets` rimaste | **J** | Seguito di TC-23. |
| C5 | **P4 / D-P4** (motore a segmenti, `daily_states` pigri) e **formule veloci di X** (X-Q1…Q3/S1) | MF / X | Consigliati dopo la 1.3: il piano dica se li tiene fuori. |

## D. Seguiti piccoli (nessuno blocca la 1.3)

- Un `data-testid` sul pulsante delle impostazioni di `AssetCard`, per un E2E di Z-29d (**Z**).
- X-N64b/c/d, dalla consegna di N64 (**X**).
- L'helper che scrive righe legacy, copiato in due spec, va in `frontend/e2e/fixtures/` (**W**).
- Y-43 (tassi ridotti sulle schede dei cambi): consigliato dopo la 1.3 (**Y**).
- Debito di traduzione delle pagine toccate nelle ondate 2-4: solo su richiesta del developer (pipeline Aphra).

## E. Fuori dall'ondata 4

- B6, la chiusura del programma colori (69 classi categoriali per la designer), la galleria G-22…G-27 e i cancelli
  finali (coverage completa, galleria completa, aggiornamento da DB 1.2, immagine Docker, revisione di sicurezza,
  CHANGELOG `[1.3.0]`, tag): **aspettano la designer**.
- I lotti di `PROSSIMI_LAVORI.md` (W3, W4/CP7, W5-W6, K2b/K2c, V-37b, Crédit Agricole, CP5, CP7/FE4, FE5a, CP12): li sta
  filtrando una sessione a parte con il developer; il piano li lasci fuori, salvo ciò che quella sessione rimette dentro.

## Sessioni e agenti disponibili

- Sessioni collegate, inattive, con il contesto della loro ondata: **Y**, **Z**, **H**, **C1**, **C2**, **W** (W-back).
- Sotto-agenti dell'ondata 3, chiusi ma riprendibili con il loro contesto: **E**, **A**, **J**, **X**.
- Mai aperte in queste ondate: **B** (backup e Docker), **MF** (matematica finanziaria), **G** (galleria).
- Corsie usate: Y 6189, Z 6186, H 6181, X 6191, J 6190, W 6183, C1/C2 dalla loro ondata; il gate usa 6180.
- Regole che restano: un solo scrittore per file; i figli non fanno git (committa il coordinatore dopo aver rilanciato le
  prove); ogni brief dice «a cosa serve»; domande importanti → si ferma solo quel pezzo; `npm ci` nei worktree nuovi;
  `LC_ALL=en_US.UTF-8` per il frontend; log fuori da `/tmp` (è un tmpfs).

## Domande aperte che il piano deve tenere presenti

A3 (docs dell'API), A6 (cinque testi),
l'immagine nightly con la 005 fusa (solo il developer può pushare su `dev`), i lotti di `PROSSIMI_LAVORI.md` da confermare.

## Aggiunte del developer (22/10, dopo il brief)
- **Plugin BRIM e impostazioni** (precisato dal developer): per i BRIM i segreti sono improbabili, i parametri molto più probabili; ma il sistema deve **supportare tutto**, parametri e segreti, se un giorno arrivano. Quindi l'interfaccia delle impostazioni di un plugin BRIM va **predisposta per entrambi**, sul modello di «Plugin settings, the foundation» dei provider di prezzi e cambi (personali e d'istanza, segreti cifrati con la chiave d'istanza), senza realizzare ora impostazioni concrete. Proprietario suggerito: W.
