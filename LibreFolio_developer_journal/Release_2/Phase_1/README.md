# Fase 01 — la 1.3.0 «Cloud-ready core»

> Aperta il 14/10/2026, dopo l'uscita della 1.2.0. **Punto d'ingresso** della fase: lo stato
> vivo delle sessioni e delle funzioni. Il perché e il come stanno nel
> [piano generale](plan-phase01Release13.prompt.md); il lavoro rimasto voce per voce in
> [`BACKLOG_POST_1.2.md`](../Phase_0/BACKLOG_POST_1.2.md), dove ogni sessione della 1.3 ha
> la sua sezione.

## 🧭 Ripartire da qui

1. Le regole del progetto: [`.github/copilot-instructions.md`](../../../.github/copilot-instructions.md)
   (git: locale sì, remoto solo il developer).
2. Il [piano generale](plan-phase01Release13.prompt.md): ondate, sessioni, schede delle
   funzioni, superfici condivise, cancelli, decisioni aperte.
3. Questo README: chi lavora dove, su quale corsia, a che punto.
   Le decisioni che aspettano il developer: [decisioni-analisi-20261014.md](decisioni-analisi-20261014.md).
4. I vincoli del programma colori: il §7 del piano. Il programma ha la sua cartella, [`10_colorSystem/`](10_colorSystem/README.md),
   scritta solo dal coordinatore colori.
5. Le voci chiuse dalla 1.3 che nascono in `Phase_0` si marcano ✅ anche lì (decisione del
   developer): le marca il coordinatore a ogni treno.

## Stato al 30/10 (ondata 6)

Le ondate 1–5 sono in `dev_release2` (treni 5–11, tabella «Treni» qui sotto). Le carte di lavoro del coordinatore delle
ondate 1–5 (piani, recap, kickoff, controlli) sono in [`00_coordination/`](00_coordination/README.md), senza le parti del
servizio gestito. L'ondata 6 è in corso su rami `claude/o6-*`, ciascuno nel suo worktree sotto `.claude/worktrees/`; le
sue carte si aggiungono a `00_coordination/` a fine ondata. Base: `dev_release2` = `485796ce1`.

| Sessione | Ramo | Committato sul ramo (30/10) | In corso |
|---|---|---|---|
| W (poi H) | `claude/o6-w-credit-agricole-a23dc5` | W5-7 Crédit Agricole 2.0.0; H cp1 (CL-1, CL-6, CL-9, CL-10, FB-23, TC-5) | H cp2 (FB-27, H6-2), poi CL-13, CL-M1, H6-1, H6-3 |
| MF | `claude/o6-mf-motore-2af5ba` | MF6-1, K3, A3, MF-C2, MF6-2, change-days, B3 + MF-J3 | W-B94 (strada b), poi FB-14, MF6-3 |
| W2 | `claude/o6-w2-transazioni-32f333` | MF-L, W6-7, W6-5, W-B63, FB-16, FB-17, W6-1…W6-9, W6-6, W6-2, W2-6, FB-18 | FB-18b, W6-12, W6-11 |
| X | `claude/o6-x-asset-341e2f` | cp1–cp4: conferma del sync delle card sui prezzi salvati, import degli eventi con `source`, FB-11 (Rolling Return fra tipi), FB-30 (modale del formato di export), FB-19 (Relink events), MF-A13 (`fx_rate`), FB-7b backend (`min`) | FB-7b frontend |
| Y | `claude/o6-y-cruscotto-9f5341` | FB-7 (storia dal primo movimento), banner dei cambi vecchi, scheletro delle candele, avviso dei buchi, Y6-1 (Δ live sulle card), FB-12, FB-13 | FB-12b, FB-15, Y6-6; poi Y6-2, Y6-3, Y-9, Y6-7 (pagina unica Dashboard/broker) |
| Y2 | `claude/o6-y2-grafici-e84a7d` | giorno della settimana nei tooltip, puntatore agganciato al giorno, zoom delle posizioni, selettore degli asset (cp1–cp2), FB-6 (livello annuale), FB-3 (forma delle linee), MF-C2 lato frontend | Y2-I63 (test di non regressione della issue #63), FB-10 |

Da aprire: J, A, T, G, AIX, WT, D, B. Treno 12: non ancora costruito (manca J).

## Sessioni (stato al 19/10, storico)

Ramo di integrazione: `dev_release2` (condiviso con il programma colori). Corsie: preambolo
`PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py test --test-port <PORTA> --data-dir <DIR> …`.

| Lettera | Sessione | Corsia | Data-dir | Ramo | HEAD | Stato |
|---|---|---|---|---|---|---|
| — | Coordinatore 1.3 (in place) | 6180 | `/tmp/librefolio-r13-main` | `dev_release2` | `de0823b81` | attivo; slot pesanti: 2 (vedi «Ripartenza del 19/10») |
| H | H - Piattaforma | 6181 | `/tmp/librefolio-r13-h` | `e-alfy-h-piattaforma` | `99c0f3892` | 10/11 lotti in `dev_release2` (manca TS1, decisione P23); analisi del 19/10 consegnate (indici del DB, testi dei controlli, H-55 per direttiva); H-55 parcheggiato; FROZEN |
| A | A - Account e accessi | 6182 | `/tmp/librefolio-r13-a` | `e-alfy-a-account-e-accessi` | `a0fea6983` | 10/11 lotti in `dev_release2` (manca A10, il giro finale di doc); analisi N69 consegnata; **in corso A-57** (solo test, via del developer 19/10) |
| X | X - Plugin asset e ricerca | 6183 | `/tmp/librefolio-r13-x` | `e-alfy-x-plugin-asset-e-ricerca` | `9bd05e1c3` | 11/17 lotti (aperti CP5, CP6, CP7, CP8, CP12, finale: domande al developer); analisi N64/N92 consegnate; **in corso X-R16** (approvata 19/10), poi N83 e N92 (i) |
| W | W - Import e transazioni | 6184 | `/tmp/librefolio-r13-w` | `e-alfy-w-import-e-transazioni` | `0c97dde20` | lotti pianificati: mancano W3, W4 CP7, W5–W6, K2b/c (domanda al developer); K3a parcheggiato; analisi N78-bis, inventario delle regole, N74 consegnate; FROZEN |
| J | J - Numeri e analisi | 6185 | `/tmp/librefolio-r13-j` | `e-alfy-j-numeri-e-analisi` | `57e09437a` | 11/13 CP (aperti CP-8, CP-11); analisi J-57 consegnata; **in corso J-48** (approvata 19/10) |
| Z | Z - Sospensione e risveglio | 6186 | `/tmp/librefolio-r13-z` | `e-alfy-z-sospensione-e-risveglio` | `4fef69544` | piano originale 100 %; Z-29 parcheggiata (N90 in ridisegno); **in corso Z-33 ridotta** (togliere la riparazione e la 011, decisione del developer 19/10) |
| B | B - Backup e Docker | 6187 | `/tmp/librefolio-r13-b` | `e-alfy-b-backup-e-docker` | `94d771da9` | 9/11 lotti (aperti B7 Litestream, D1–D10 del developer; BZ parte 2); **in corso B-15 e B-8** (approvate 19/10) |
| E | E - Email | 6188 | `/tmp/librefolio-r13-e` | `e-alfy-e-email` | `2edbdcd8b` | 7/7 lotti in `dev_release2`; C-70b parcheggiato; FROZEN |
| Y | Y - Cruscotto e grafici | 6189 | `/tmp/librefolio-r13-y` | `e-alfy-y-cruscotto-e-grafici` | `1a54a8d74` | 11/13 lotti; Y-30 entrata (`de0823b81`); analisi N65 consegnata; FROZEN |
| MF | MF - Matematica finanziaria | 6190 | `/tmp/librefolio-r13-mf` | `e-alfy-mf-matematica-finanziaria` | `47299b76f` | 14/16 lotti (aperti E2, L); analisi N74 consegnata; **in corso J-1** (voci 1, 4, 8a, approvata 19/10) |

### Ripartenza del 19/10

Il 17/10 alle 21:45 il developer ha fermato tutto. Il 19/10 ha letto il resoconto, ha deciso punto per punto e ha fatto
ripartire i figli con regole nuove:
- nessuna decisione di prodotto dai figli né dal coordinatore: ogni scelta diventa una domanda per il developer;
- si implementa solo dopo il via esplicito;
- prima della ripartenza, ogni lavoro a metà è stato messo da parte come patch nella cartella di sessione del figlio,
  il giornale committato e la base portata a `dev_release2` (`de0823b81`);
- poi contabilità (tabelle dei lotti e ✅ del backlog, con la prova del commit) e un'analisi in sola lettura per figlio.

Le decisioni e le domande del giorno sono raccolte nel file del coordinatore `risposte-resoconto-20261019.md` (cartella
di sessione) e riportate nel §12 del [piano generale](plan-phase01Release13.prompt.md). Slot pesanti: 2 alla volta,
lavori leggeri solo con carico a 1 minuto sotto 50.

Corsie del programma colori, da non usare: 6150–6154 e 6160. Lettere riservate ai colori:
L, R, G, T, C, U, S, P.

### Ripresa del 21/10 (Linux)

Il 20/10 alle 14:36 il coordinatore Copilot si è fermato (errore 403) e con lui le sessioni figlie. Il lavoro è ripreso su
Linux con un coordinatore Claude Code, in sola lettura prima: analisi e piano a ondate in `ANALISI-ripresa-LibreFolio.md`
(accanto al repo). Ondata 0 fatta il 21/10: copia dei diff dei worktree sporchi, `.claude/` nel git, treno 5. I figli
restano fermi finché il developer non dà il via all'ondata 1 (Y, H, Z).

## Funzioni per il cloud

| Ondata | Funzione | Sessione | Stato (19/10) |
|---|---|---|---|
| 1 | Pausa degli aggiornamenti e sospensione (F26) | Z | ✅ in `dev_release2`; manca la prova vera su Fly (protocollo A1–A9, developer o pannello) |
| 1 | Segreti e configurazione (F03) | H | ✅ |
| 1 | Prontezza e versione (F08) | H | ✅ |
| 1 | Profilo gestito (F05) | H, A, X | 🟡 parti di H e di A ✅; manca quella di X (CP6, elenchi dei fornitori permessi: domanda al developer) |
| 1 | Disclaimer e link legali (F09) | A | ✅ (A9) |
| 1 | Admin iniziale da variabili (F02) | A | ✅ (A7) |
| 1 | Inviti, registrazione e gestione utenti (F13) | A | ✅ (A5, A6) |
| 1 | Limite dei tentativi di accesso e header di sicurezza (F15) | A, H | ✅ (A8; CSP solo segnalata, H CP7b); la CSP applicata (H-55) è in decisione |
| 2 | Email facoltativa (F04) | E | ✅ |
| 2 | Backup e ripristino dalla UI (F01) | B | ✅ |
| 2 | Backup continuo con Litestream (F25) | B | ⏳ non iniziato: aspetta le risposte D1–D10 del developer e Docker acceso |
| 2 | Avvio, aggiornamento all'accesso e risveglio (F07) | Z | ✅ |
| 2 | Impostazioni dei plugin | X | ✅ (CP10, CP11); per BRIM e Tool (CP12) proposta dopo la 1.3 |
| 2 | Ordine dei fornitori nella ricerca (F21) | X | ✅ (CP13) |
| 3 | Fornitore di prezzi a pagamento (F06) | X | quando sarà scelto |

## Riordino (ondata 0)

| Lotto | Sessione | Stato |
|---|---|---|
| Registri per famiglia di plugin (PL2) | X | ✅ X CP1 (`ea666b511`) |
| Asset senza shim (PL6), cambi in `services/fx/` (PL4), router di asset e cambi, router dei segnali (PL7) | X | 🟡 integrati PL6 (CP2a), asset per tema e router per risorsa (CP2b), PL4 e router dei cambi (CP3), schemi degli asset (CP4); PL7 dopo PL1 di J |
| Import broker in `services/brim/` (PL5, U-B3, U-B4), transazioni, broker | W | 🟡 integrati transazioni e broker per tema (W1, W2), BRIM in `services/brim/` (W4 CP6), schemi delle transazioni (W7); restano CP7 (taglio di `brim_provider.py`), W3 e W5–W6 |
| Segnali (PL1), rischio, preparazione delle serie, portafoglio, PAC | J | 🟡 PAC per tema integrato (CP-1); il resto con CP-2 e seguenti, dopo le decisioni 26–30 |
| Piattaforma, file, agganci di `main.py`, configurazione | H | 🟡 integrati `services/platform/` e `services/files/` (CP1) e il pacchetto `config/` (CP2a); il taglio di `main.py` (CP2b) sbloccato dall'ingresso della 1.2.1 |
| Servizi account | A | ✅ A1 (`ea1f73618`) |
| Frontend: auth, settings, support | A | ✅ A2 (`b569b4119`) |
| Frontend: cambi (FE4), asset (FE5) — dopo il lotto A dei colori | X | ⏳ |
| Frontend: transazioni (FE8) — dopo il lotto A dei colori | W | ⏳ |
| Frontend: segnali e rischio (FE2), dashboard (FE6), broker e lotti (FE7) — dopo il lotto B | Y | ⏳ |
| Frontend: file (FE3), `DataTable` — dopo il lotto C | Y | ⏳ |
| Frontend: utility, store, suffissi (FE9–FE11) | Y | ⏳ |
| Test speculari (TS1) | H | da decidere a riordino del backend finito |

## Treni

Ogni ingresso in `dev_release2` è un treno: checkpoint del figlio, aggiornamento di base, validazione della
revisione combinata, merge. Prove e note di ciascuno nel §12 del [piano generale](plan-phase01Release13.prompt.md).
Sono tutti locali: la push la fa il developer.

| # | Data | Cosa | Commit in `dev_release2` |
|---|---|---|---|
| 1 | 14/10 17:41 | Piano della fase, sezioni 1.3 nel backlog | `b5317cb6e` |
| 2 | 15/10 00:25 | A1: servizi account in `services/accounts/` | `ea1f73618` |
| 3 | 15/10 00:48 | H CP1: `services/platform/` e `services/files/` | `3cea9aaac` |
| 4 | 15/10 01:03 | A2: frontend di auth, settings e support in `lib/features/` | `b569b4119` |
| 5 | 15/10 01:09 | W1 e W2: transazioni e broker per tema | `24776d89c` |
| 6 | 15/10 01:20 | H CP2a: pacchetto `config/`, guardia sulle letture d'ambiente | `434e5ea30` |
| 7 | 15/10 02:17 | X CP1 e CP2a: registri per famiglia, `services/assets/` senza shim | `ea666b511` |
| 8 | 15/10 03:01 | W I1: rifiuti d'accesso, pulizia BRIM (V-23, C-65b, L5, C-79, C-3) | `0e314caf6` |
| 9 | 15/10 03:17 | A3: registro delle schede di Settings (O-15, K-17, L12) | `332c30dec` |
| 10 | 15/10 03:45 | H CP3: segreti da `*_FILE`, chiave d'istanza, controlli all'avvio | `089113ce0` |
| 11 | 15/10 03:46 | X CP2b: asset per tema, router per risorsa | `53e3cdd39` |
| 12 | 15/10 04:04 | W K1: chiarezza (O-12, C-89, V-38, P-15) | `0a5b05666` |
| 13 | 15/10 04:15 | H: letture di `web_link_finder` in `config/` | `abd0b9d0c` |
| 14 | 15/10 04:29 | J CP-1: PAC per tema, guardia dei confini | `ab3b1dc71` |
| 15 | 15/10 04:37 | W4 CP6: BRIM in `services/brim/` | `956a4ab6c` |
| 16 | 15/10 05:15 | A4: migrazione 005, token monouso | `a57229f36` |
| 17 | 15/10 05:24 | X CP3: cambi per tema in `services/fx/` e `api/v1/fx/` | `80b6ecf14` |
| 18 | 15/10 05:35 | W7: schemi delle transazioni in `schemas/transactions/` | `6e17be873` |
| 19 | 15/10 05:54 | X CP3b: test dei cambi senza rete | `2eaed604f` |
| 20 | 15/10 05:57 | J C-93: connessioni aiosqlite chiuse nei test dell'AI Export | `72e4eb588` |
| 21 | 15/10 05:59 | H CP4: `/system/instance`, area degli avvisi | `5512afc8e` |
| 22 | 15/10 06:24 | J G-8: catalogo dei Tool sotto carico | `fc97aea3c` |
| 23 | 15/10 06:33 | X CP4: schemi degli asset per tema | `7ab687bc8` |
| 24 | 15/10 06:45 | W K2a: rifiuti a codice, L6 | `2055f257a` |
| 25 | 15/10 06:54 | A4b: versione di sessione, uscita degli altri dispositivi al cambio password | `0640cd9c1` |
| 26 | 15/10 07:12 | X J-5: loop chiuso nel thread dei fornitori | `addc90a46` |
| 27 | 15/10 07:17 | H CP5a: `/system/ready`, `/system/info` minimo senza sessione, R2 | `cf4ce0e71` |
| 28 | 15/10 07:40 | J-6: guardia di suite sulle connessioni aiosqlite lasciate aperte | `e43d689b2` |
| 29 | 15/10 07:51 | W E0: eventi distinti per data e tipo nel CSV e nel selettore della data (I-11 a e d), X-R9, W-B15 | `f0a5feaa9` |
| 30 | 15/10 08:18 | X-R8: elenchi delle valute dei fornitori dei cambi in cache per un giorno | `2ccbcda54` |
| 31 | 15/10 12:47 | 1.2.1 (rilasciata dal developer alle 12:27): file serviti dentro le loro cartelle, file caricati mai eseguiti, `JWT_SECRET` di soli spazi mai usato come chiave | `a1d27756b` |
| 32 | 15/10 13:35 | `cryptography` nell'ambiente condiviso (finestra delle dipendenze, installata dal developer) | `e910074cc` |
| 33 | 15/10 14:20 | H CP5b+CP6: blocco dell'istanza (`LIBREFOLIO_BLOCKED`, pagina di blocco, 423), `LIBREFOLIO_PROFILE`, `/system/block` | `260e3a137` |
| 34 | 15/10 14:22 | X FE5b (`AssetModal` in sei pezzi, logica in moduli puri), X-R11a, X-R1/R2, D-X4 | `e2653c2d1` |
| 35 | 15/10 14:45 | E1: servizio email (SMTP facoltativo, testi in 4 lingue, limitatore comune `rate_window`) | `99096768a` |
| 36 | 15/10 15:12 | Y1: taglio di `GrowthChart` in moduli puri (FE6a), B10; galleria filtrata pulita | `d2e2b7763` |
| 37 | 15/10 15:17 | A5: registrazione a tre modi, inviti e link di reset monouso, API admin degli utenti, limite di utenti | `9ef1f6123` |
| 38 | 15/10 15:55 | H: CP7a (Docker: `tzdata-legacy`, una porta, `docker exec` con gosu, versione congelata), C-96, filtro del log d'accesso, G-10, riparazione di `test_instance_block.py` | `f8b36d4de` |
| 39 | 15/10 16:07 | Z1: pausa dei prezzi dal vivo (lista 60 s, dettaglio 30 s in un ciclo, pausa a scheda nascosta o dopo 2 minuti) | `47ee29a34` |
| 40 | 15/10 16:19 | W: FE8a (Form, Bulk e Wizard divisi), N1 (broker al giorno dell'utente, metà spaiate), N1b-2/3 (`orphan_pair_halves`, punto 46), E1a ed E1c (eventi tutto o niente, `DELETE` per asset, `event_types`) | `e81a7ba9a` |
| 41 | 15/10 16:55 | J: C-94 (build del server di prova fuori dal timeout di avvio, `--build-only`, controllo di `node_modules`, galleria al 60 % delle CPU) e CP-2 (PAC: C-73…C-76) | `52df1480d` |
| 42 | 15/10 17:20 | A6a: eliminazione da parte dell'admin, anteprima dell'eliminazione, sonda dell'indirizzo (nonce firmato) | `8a1c100a2` |
| 43 | 15/10 17:40 | H: link di fatturazione e rotte dei link di reset a istanza bloccata, H-12 (controllo della porta solo sui listener), contratto `/system/instance` nelle E2E sintetiche, anteprima di A6a in `ALLOWED_WHEN_BLOCKED`, A-15 | `db87623e4` |
| 44 | 15/10 17:40 | Z7a: registro delle pause dei fornitori (`utils/runtime/cooldown.py`, `provider_cooldown`, `config/sleep_wake.py`), non ancora agganciato (X1–X8) | `758c881c8` |
| 45 | 15/10 18:08 | Y2: taglio di `DataTable` (`DataTableColumnHeader`, `DataTableCellContent`), `~split` dichiarato | `c0dc85fbb` |
| 46 | 15/10 18:13 | W: E1b (salvataggio atomico degli eventi con `delete_ids`, «+ Nuovo evento» che non sovrascrive, pannello `EVENT_EXISTS`) | `b71a72ee0` |
| 47 | 15/10 18:15 | J: CP-4a (rendimenti di periodo, ritorno netto e rapporto G/L in `financial_math/returns.py`) e CP-4b (V-11, decisione 30: grazia dall'ultima quotazione) | `d94bf0d11` |
| 48 | 15/10 18:30 | E2: `GET /email/status`, `POST /email/test`, controlli d'avvio email, `/system/instance.email`, scheda Email (130), scatto `settings/email` (rivisto da G) | `570fd34e9` |
| 48b | 15/10 18:44 | E2: correzione del gate `htmlInterpolation` (`SMTP_FROM_INVALID` senza `<` né `>`), dopo il rosso di `core-unit` trovato da T | `2621200a0` |
| 49 | 15/10 18:58 | Z6b parte 1: `LIBREFOLIO_SHUTDOWN_TIMEOUT_SECONDS` (8 s), drenaggio di uvicorn a 3 s da `dev.py server` ed `entrypoint.sh`, grazia del runner e di Playwright a 10 s; watchdog cablato dopo CP2b | `558aed788` |
| 50 | 15/10 19:07 | B: B0 (`backup.py` diviso, `series_export.py`), B1 (backup dell'istanza, API e CLI), B5a (scheda Backup), B6a (doc CLI), backup a istanza bloccata (`backup_available`), via i 4 segnaposto | `47816493e` |
| 51 | 15/10 19:37 | W: N2 (regola del costo dai metadati; modifiche controllate solo se toccano tipo, quantità, costo, valuta o evento) | `e2803b875` |
| 52 | 15/10 20:00 | H: CP2b (`main.py` diviso in `app_lifespan`, `lifecycle`, `middleware`, `static_site`, `database_bootstrap`; passi nominati; uno spegnimento che fallisce non salta gli altri); `main.py` scongelato | `2f1cbd0bc` |
| 53 | 15/10 20:24 | B8: token del pannello per i backup (`LIBREFOLIO_BACKUP_DOWNLOAD_TOKEN`, `/backup/panel/jobs`, anche a istanza bloccata) | `fe3fed78e` |
| 54 | 15/10 20:33 | A6b: scheda Users (110), eliminazione con anteprima, sonda dell'indirizzo dal browser, A-12; scatto `settings/users` | `33e58aef3` |
| 55 | 15/10 20:41 | J: CP-4c (`financial_math/portfolio/period.py`: P&L di periodo; costi unitari nella casa; valori identici) | `026a7a66f` |
| 55b | 15/10 20:56 | B: scatto `settings/backup-ready` (rivisto da G), da solo prima di B2a | `1cf926658` |
| 56 | 15/10 21:04 | X: CP10, impostazioni dei plugin (migrazione 007, segreti cifrati, `/settings/plugins`, confine unico per famiglia, mascheramento), X-R6 | `6d3398cb5` |
| 57 | 15/10 21:24 | Y8: correzioni ai grafici (I-01, I-03, O-16, 47-1 etichette sull'asse zoomato, 48-1 pulsanti); CHANGELOG scritto da Y | `b2830c7ed` |
| 58 | 15/10 21:28 | Z6b parte 2: watchdog e scadenza dei passi nel lifespan, processi figli chiusi; spegnimento entro 8 s (decisione 35) | `311d57d4c` |
| 59 | 15/10 21:31 | E3 + E3s: link nelle email solo da `LIBREFOLIO_PUBLIC_URL`, `POST /email/links`, «password dimenticata» (spenta fino ad A6e, revisione di sicurezza), controllo `email.links` | `6e87fe24f` |
| 60 | 15/10 21:36 | Z: correzione della E2E del flash dal vivo (attesa del primo poll e orologio in pausa), solo test | `65624c963` |
| 61 | 15/10 22:13 | E3p: sonda dei link della scheda Email dal browser dell'admin (decisione 45) | `63bbb9c55` |
| 62 | 15/10 22:14 | A: G-15 (la barra delle schede di Settings scorre invece di tagliare; `TabBar` `scrollable`) | `3fbfb0e65` |
| 63 | 15/10 22:36 | W: F36 (report BRIM senza broker solo al caricatore e all'admin; `/parse` chiede EDITOR sul broker della richiesta; `file_id` non UUID → 404; `can_delete` nella lista; decisione 36, W-B3/W-B4) | `6b85fa634` |
| 64 | 15/10 22:38 | J: CP-4d (risolutore MWRR verificato, Newton + Brent, `None` senza radice; via il ritentativo a freddo e `MWRR_SERIES_UNRELIABLE`; golden native-cash rigenerato solo sui `mwrr_*`) | `71680e5b1` |
| 65 | 15/10 22:47 | Z: Z2a (presenza dell'utente e richieste in corso, `ActivityMiddleware` in testa a `MIDDLEWARE_STACK`; D-S1; nessun effetto visibile) | `f20a37f48` |
| 66 | 15/10 23:02 | H: CP-U1 (decisione 36: scopo dei file caricati comune/personale, regola legacy alla lettura, personale altrui → 404, `PATCH` scopo, miniature `private`; I/O su disco fuori dal loop) | `a1e4a5b8e` |
| 67 | 15/10 23:26 | X: X-RL, X1–X8 (pausa dei fornitori su «troppe richieste» sopra Z7a: eccezioni `RATE_LIMITED`, confini `call_provider`/`call_fx_provider`, Yahoo senza ritentativi, `error_code`/`retry_after` nei risultati, la sonda mostra fino a quando; decisione 34) | `e87a23ca6` |
| 68 | 15/10 23:38 | E: E5a (verifica dell'email, parti solo di E: servizio `verification.py`, `POST /email/verification/confirm` e `/resend`, pagina `/verify-email`; inerte fino a E5b; decisione 44) | `20445f297` |
| 69 | 15/10 23:45 | W: W-B20 (un savepoint per broker nella cancellazione multipla; `begin_writes` in `db/session.py`) | `f328f7991` |
| 70 | 16/10 00:42 | J: CP-16 (decisione 47 nei lotti: la rettifica in uscita con costo chiude i lotti al costo medio della riga, valore ceduto nei proventi; J-9; etichetta «Valore ceduto al costo») | `5dd832c52` |
| 71 | 16/10 00:55 | X: CP11a (impostazioni dei plugin, backend: `configured` nel catalogo, `providers_not_configured` e `error_code` nello stream di ricerca, preferenze justETF/Borsa D-X14, `PROVIDER_ERROR` mascherato; CHANGELOG con CP11b) | `456aec74f` |
| 72 | 16/10 01:38 | W: lotto di doc (A-14 regola dell'ultimo OWNER, W-B10 rotte di accesso, W-B33; tolte due chiavi i18n inutilizzate di W-B27) | `608a21750` |
| 73 | 16/10 01:44 | Z: Z3 (`run_due_jobs` con lock e `busy("scheduler")`, recupero al ritorno, slot perso fino a 7 giorni, istanza bloccata senza job; Z-6 chiusa) | `b5b66ea5f` |
| 74 | 16/10 01:46 | J: CP-15 (totali di controllo del registro per il backup: `financial_math/ledger_totals.py`, versione 1, somme esatte; nessun chiamante ancora) | `5403e203d` |
| 75 | 16/10 01:48 | E: E4a (parti solo di E: «Invia per email», modulo «password dimenticata», avviso al vecchio indirizzo; non raggiungibili fino a E4b) | `6141b8e6a` |
| 76 | 16/10 01:53 | Y: Y7 (tabelle su telefono: colonne di selezione e azioni scorrono sotto 768 px, D-Y17; ridimensionamento con Pointer Events e `min-width`, D-Y18/C-62; galleria mobile 11/11 contro G-13, 174 scatti cambiati, tutti di Y7) | `352f70d7c` |
| 77 | 16/10 01:57 | Z: Z4 (`POST /system/wake-sync` con `LIBREFOLIO_WAKE_TOKEN`, 409 `wake_in_progress`, risposta in streaming, ammessa su istanza bloccata; pagina admin «Sleep and Wake»; security-review pulita) | `c55671542` |
| 78 | 16/10 02:08 | W: W-B31 + W-B36 (le regole 5–12 leggono `TX_TYPE_METADATA`; tolto `EVENT_COMPATIBLE_TYPES`; i 4 casi di P6 restano eccezioni esplicite; messaggi invariati) | `c97c09e6c` |
| 79 | 16/10 02:31 | H: CP-U2 (decisione 36, frontend: colonna Visibilità, condividi/rendi personale, «elimina» solo con `can_delete`, il selettore condivide un'immagine personale scelta; pagina utente dei file aggiornata) | `b9c76e457` |
| 80 | 16/10 02:45 | A: A6d (nuove istanze su invito, primo account aperto, migrazione 008; impostazioni globali con sessione) + A6e (cambio email con password attuale, chiude le altre sessioni, `email_verified_at` a NULL) | `2ad76de52` |
| 81 | 16/10 02:52 | Y: Y4b (FE2b, il frontend del rischio in `lib/features/risk/`: 103 rinomine, import, runner, doc, devWiki, baseline dei colori; E2E `risk` 38 e `risk-lab` 44) | `0e140cf8e` |
| 82 | 16/10 02:55 | B: B2 (controllo di un archivio su una copia: `staging.py`, `restore_jobs.py`, `/backup/restore/*`, CLI `restore --dry-run`, `backup_in_progress()`, limite di caricamento; decisioni 40, 42, 43; all-backend 18 359/0) | `8c4b1da7e` |
| 83 | 16/10 03:00 | E: E-5 (guardia dei testi OpenAPI che il generatore incolla grezzi; regola 4 dei contratti API; 52 componenti latenti, nessuno rotto) | `939dd745b` |
| 84 | 16/10 03:05 | X: CP11b (scheda Impostazioni › Plugin, «Configura» dal pannello del fornitore e dalla ricerca, legenda 👑, sottosistema i18n `pluginSettings`; E2E 104) | `ba60162d5` |
| 85 | 16/10 03:07 | Z: Z7b (lo scheduler rimanda gli elementi `RATE_LIMITED` fino a `retry_at` e aspetta 1, 2, 4… minuti dopo un errore; campi nuovi nello stato e nella risposta del risveglio) | `b6362cca8` |
| 86 | 16/10 03:52 | H: CP7b-1 (F15 sempre attivo: `nosniff` e `Referrer-Policy` su ogni risposta; F28: solo `_app/immutable/` immutabile; tipi MIME registrati dall'app; all-backend 17 084/0) | `183437c6a` |
| 87 | 16/10 03:55 | J: CP-6 (decisione 28: giorni «dirty» anche per i soli cambi dei titoli, per le quotazioni e per il primo giorno di un prezzo vecchio; `native_cash.change_days` unica; golden W1 rigenerato; J-20; B11 chiusa) | `6f5c4968d` |
| 88 | 16/10 04:24 | Z: Z2b (sospensione dopo l'inattività su Fly: `idle_monitor`, `FlySuspender`, attesa crescente fino a 10 min; spento di default) | `8b8cd9328` |
| 89 | 16/10 04:42 | W: coda della notte per cherry-pick, senza la 47 (W-B37 cancellazione multipla dei report che salta i file bloccati; C-34 `escapeHtml` nel Bulk; W-B35 docstring dell'accesso; W-B12 MULTI-008d pulisce i suoi broker) | `8cc111827` |
| 90 | 16/10 04:48 | A: A6c (decisione 37: regole della password in `password_policy.py`, classi Unicode, `PASSWORD_TOO_WEAK` su register/change/reset e CLI, `accounts.password_rules`; all-backend 0 rossi, E2E 129) | `2eb914aee` |
| 91 | 16/10 04:49 | X: CP11c (mascheramento N15 e campo personale N16, sonda senza URL col segreto, E2E `front-utility plugin-settings` 5/5, pagina `user/settings/plugins`, scatto `settings/plugins`) + escape del tooltip della sonda (ultimo LOW della revisione CP10–CP11) | `2b85f8fc5` |
| 92 | 16/10 04:52 | H: CP7b-2 (`PROFILE_DEFAULTS` del profilo gestito, `LIBREFOLIO_FRAME_PROTECTION` e `LIBREFOLIO_CSP_REPORT_ONLY`; all-backend 17 792/0) | `96c5fb135` |
| 93 | 16/10 04:56 | Z: cura del rosso `services config-package` (1/693 da Z2b): `fly_machine_identity()` in `config/sleep_wake.py`, `suspend.py` senza `os.environ`; trovato da H | `88a99a732` |
| 94 | 16/10 06:47 | X: X-R12 (eventi del fornitore datati oggi arrivano lo stesso giorno) + X-R13 (emoji morta dei settori nella pagina asset, primo pezzo di FE5c) | `0f0efa6c5` |
| 95 | 16/10 06:47 | W per cherry-pick: W-B41 (test multiutente puliscono i broker), W-B29 (E2E eventi con asset propri), W-B38 (messaggi delle regole impacchettate col tipo) | `7e8e918ec` `590205669` `2b1ac27ee` |
| 96 | 16/10 06:54 | X per cherry-pick: K-16 (ETC/ETN di Borsa Italiana come `ETF_COMMODITY`) + O-9 (etichette dei parametri di justETF e css_scraper in 4 lingue) | `39ae1cd4b` |
| 97 | 16/10 07:09 | Z: Z7c-2 (pannello dello scheduler: elementi rinviati ⏸, `retry_at`, riga di stato del nuovo tentativo; api scheduler 16, component-unit 4006) | `e04fbb700` |
| 98 | 16/10 07:27 | W per cherry-pick: W-B39 (split/promozione rifiutati con toast d'errore e i problemi tradotti; E2E `tx-split-refusal` 2/2) + W-B42 (scenari 3–4 di `asset-event-delete` con dati propri, 4/4) | `7be9dbe6b` `db12b3ad8` |
| 99 | 16/10 07:43 | W per cherry-pick: W-B44 (test id unici in `PromoteMergeModal`; Vitest 4/4) | `dc89bf527` |
| 100 | 16/10 08:17 | J: CP-10a (decisione 29: un solo Rolling Return in giorni di calendario, `price_return` in `financial_math/returns.py`, impostazioni dei grafici v3, J-13 finestre in osservazioni; C-71 chiusa; asset E2E 34/34, all-backend 17 204/0, mirate sulla revisione unita) | `fc9eead38` |
| 101 | 16/10 08:17 | W per cherry-pick: W-B32 (i report senza broker non compaiono più sotto ogni broker; `api brim` 118/118; dentro la decisione 36, da rivedere) | `fe3176208` |
| 102 | 16/10 08:24 | W per cherry-pick: W-B45 (T13 di `transactions-modals` con il budget di 60 s dei vicini) | `6098781bb` |
| 103 | 16/10 08:29 | E: E5b (verifica email alla registrazione, limiti 3/h per casella e 10/h per rete, revisione di sicurezza, merge con A6c; E2E 5/5, mirate sulla revisione unita) | `3649d733b` |
| 104 | 16/10 08:33 | Y: Y3 (FE6b dashboard in `features/`), Y9 (font delle bandiere e testo sicuro nei grafici), Y10 (decisione 49, liquidità negativa nell'allocazione), Y5 (broker e lotti in `features/brokers`), Y6 (file in `features/files`), C-34 (guardia), cura dell'attesa in `brokers-detail.spec.ts`; E2E unica 223/224 + 37/37, leggere sulla revisione unita | `07b095fef` |
| 105 | 16/10 10:39 | Z: Z7c-1 (attesa crescente dei prezzi dal vivo dopo errori e pause dei fornitori; E2E `live-pause` 8/8, flash 4/4) + Z-9 (doc admin delle pause dei fornitori) | `e57f6850e` |
| 106 | 16/10 10:49 | W per cherry-pick: W-B17 (una FX_CONVERSION su due broker è rifiutata, `pairBrokerMismatch`) | `33124dd9d` |
| 107 | 16/10 11:17 | J: CP-7a (decisione 26: ogni gamba del lotto convertita alla sua data, via il ripiego di CP-16, lotti short corretti, T-B6, J-14; all-backend 17 898/1 rosso estraneo — timeout del fornitore in `search-to-prices`, ripassato 3/3) — T-B5, T-B6 chiuse | `e29ecca10` |
| 108 | 16/10 11:18 | W per cherry-pick: docstring di `list_accesses` (P4 del developer: la lista degli accessi resta aperta) | `92d75dfa5` |
| 109 | 16/10 12:05 | W per cherry-pick: W-B43 (gli spec dell'editor dei dati e dell'import CSV dei cambi verificano invece di sondare; `asset-data-editor` 26/26, `fx-csv-import` 21/22 con il test 19 scaduto a carico ~140 e ripassato da solo in 3 s) | `4d68a375d` |
| 110 | 16/10 12:47 | H: note di X, card del backup nella pagina di blocco, H-17, b-doc-notes, lotto 2, H-3 B (H-15 incluso); all-backend 18 266/5 timeout estranei (triage: ricerca → X, parse BRIM → W), combinato verde (front check, `InstanceBlockedPage` 36, `api instance-block` 62, `api system` 118) | `46ffd23de` |
| 111 | 16/10 12:48 | W per cherry-pick: W-B30 (P5, lettura B: svuotare un costo manuale richiesto è rifiutato, mai tenuto in silenzio; `null` esplicito toglie il costo solo dove il tipo lo ammette) | `d5511c3ad` |
| 112 | 16/10 14:25 | W per cherry-pick: W-B36b (P6: in aggiornamento valgono le regole dei tipi sul campo che cambia; `cashNonzero`; 0 righe fuori regola sui dati demo) + seguito W-B30 (test come guardie); gate su dev: `schemas transactions` 106, `services transaction` 96, `cost-basis-rule` 73, `i18n check`, mkdocs strict. Prima, `b6a3f1499`: ancora mancante in `wac.md` dopo il treno 111 | `ca09c5895`, `34e742ae4` |
| 113 | 16/10 15:05 | E per cherry-pick: il finto SMTP parla `SMTPUTF8` (fixture di test, sblocca i test di P18) | `0d0314e62` |
| 114 | 16/10 15:05 | H: P17, `LIBREFOLIO_CLIENT_IP_HEADER` (indirizzo del visitatore dietro un proxy fidato; il cloud mette `Fly-Client-IP`), i tre limiti per client su `client_address()` | `b9e3fdbeb` |
| 115 | 16/10 15:06 | Z: Z5 (avviso «Aggiornamento prezzi…» durante un recupero, `GET /system/price-refresh`) + Z-13 (Dashboard e broker si ricaricano a fine recupero); combinato verde da Z su `77a0719b8` | `e8a09774d` |
| 116 | 16/10 15:20 | Z: Z-13b (la ricarica dopo un recupero non tocca `refreshVersion`, così Y11 non gira) | `b06f4a0f8` |
| 117 | 16/10 16:15 | H: TC-16 (attese del visore dei file robuste sotto carico; `component-unit` 4041 ×2 a carico 66–106) | `de435c565` |
| 118 | 16/10 16:28 | Z: Z-12 (commento di `scheduler_state.json` in 4 lingue) + Z-5 (lo storico riparte dall'ultima data salvata, fino a 365 giorni); gate su dev: scheduler-jobs 73, catchup 73, price-refresh 44, mkdocs strict | `6d80129f7` |
| 119 | 16/10 16:50 | X: FE5c (pagina asset 3603 → 2757 righe; galleria di G identica entro il rumore), F21, CP13 (`LIBREFOLIO_SUPPORT_URL`, regola unica degli URL, livello premium), X-R21, correzioni del prezzo dal vivo, icone in Impostazioni › Plugin; combinato verde da X (core 6783, component 4079); CHANGELOG risolto dal coordinatore | `03a0c761f` |
| 120 | 16/10 16:56 | Z: Z-17 + prova su Fly (`admin/sleep_wake.en.md#check-it-works`) + chiusura del piano 06 (foglio delle 43 decisioni da rivedere) | `2f859fa72` |
| 121 | 16/10 17:08 | J: J-17 (P2: una rettifica non è mai un prezzo; senza alcun prezzo si valuta al costo, stima dichiarata); all-backend su `892ac2db9` 6/7, 2 rossi API = avvio a freddo del pool BRIM (J-30 a W) | `155d64a8c` |
| 122 | 16/10 18:16 | X: X-R27 + X-R28 (una sola chiave di cache per le risposte dei fornitori; i piani programmati e gli asset con stesso URL/ISIN non si scambiano più il prezzo dal vivo; decisione del developer: solo cura + 🐛, niente riparazione); gate del coordinatore sul tip verde (24 passi) | `7fc972661` |
| 123 | 16/10 18:32 | W: C-97a (issue #43: quantità a 10 decimali, prezzi e costo per unità a 12, oltre il limite rifiutato; somme in Python; D5/D6 = N51/N52), cherry-pick di `2a3c1bd60` | `3ba393915` |
| 124 | 16/10 18:41 | H: H-12 (l'output del backend di test condiviso va in `shared-backend.log`; un avvio fallito ne mostra la coda); all-backend 18 487/0 | `40d925c38` |
| 125 | 16/10 18:41 | J: CP-13a (P19: il guadagno che recupera un drawdown calcolato in `financial_math`, campo `maximum_drawdown_trough_to_peak_ratio`; perdita totale = null con avviso) | `cb3b2e32d` |
| 126 | 16/10 19:26 | H: H-21 (= W-B54: un'azione `api` da sola rifà il seed se il DB della corsia non ha gli utenti di fixture); gate su dev: reseed una volta, poi no | `4a224923d` |
| 127 | 16/10 19:29 | X: O-20 (una sola sincronizzazione dei prezzi alla creazione di un asset, `onsynced` della modale; i piani programmati creati da modulo o wizard hanno subito lo storico) | `ca3e64b58` |
| 128 | 16/10 19:42 | MF: ondata 1b (M, G1 somme del PAC in Python; N + F2 AI Export v2 di `broker.cost_efficiency` e `portfolio.income_timeline`; K2 + N54 una regola MWRR per card e linea; O2 Yield on Cost negativo); all-backend 6/7, 2 rossi External di Crédit Agricole a W (C-97a) | `324348aac` |
| 129 | 16/10 19:48 | W: correzione di C-97a (D6): `round_computed_value` quantizza solo oltre la scala (i valori calcolati dai plugin non escono più con 12 zeri); gate su dev: real-decimal 96, brim-providers 736 | `ffaf1c5d9` |
| 130 | 16/10 19:59 | Y: Y12a, Y-12, Y11 passi 1–4b (un solo «Aggiorna» per pagina che aspetta `pageBusy`; `join` per i pannelli, N55); E2E combinata 121/121 | `d4202021d` |
| 131 | 16/10 20:06 | A: P18 (email uniche senza distinzione di maiuscole, revisione 009), A-24, A-27 (link di reset revocati al cambio di email o password), A7a (admin iniziale da variabili; la pagina `/setup` arriva con A7b), A7c, A-22; all-backend 20 767/0, combinato verde | `e7d2daa94` |
| 132 | 16/10 20:20 | A: A-25 (Impostazioni › Profilo non chiede la password per un cambio di sole maiuscole) | `cdc0bd6ea` |
| 133 | 16/10 20:33 | W: W-B53 (riscaldamento facoltativo del pool di analisi BRIM, `LIBREFOLIO_BRIM_PREWARM`, spento in produzione e acceso in test; N56), cherry-pick con 3 risoluzioni di W | `b28a9342c` |
| 134 | 16/10 20:58 | J: J-24 (P21: un ADJUSTMENT in uscita con prezzo esce al valore dichiarato al cambio del giorno; differenza dal costo medio realizzata); all-backend su J-24 + MF 1b 6/7 (solo i 2 rossi CA già curati) | `35a48deac` |
| 135 | 16/10 20:59 | MF: lotto C (pesi e HHI in `financial_math/weights.py`; peso su NAV «—» con patrimonio ≤ 0; D-MF7) | `c5e721a29` |
| 136 | 16/10 21:00 | MF: I2 (un solo lettore dei frazionamenti per i ricalcoli del costo medio, `split_linked_ids`; nessun numero cambia) | `fbc641ead` |
| — | 16/10 21:05 | Z: journal Z-18, Z-19 (N58) | `4a62135ee` |
| 137 | 16/10 21:20 | H: H-22 (tolte le funzioni di `client_address` usate solo dai test; N58: nessun record scritto da LibreFolio contiene l'indirizzo di un client) | `b524ba9c8` |
| 138 | 16/10 21:30 | X: C-66 (l'avviso nella finestra di sincronizzazione quando l'intervallo ha già dati, modifiche manuali comprese); E2E combinata con Y11: asset-list 30, page-busy 12 | `425ba07aa` |
| 139 | 16/10 21:40 | E: E4b (password dimenticata per email, invio dei link per email, avviso di cambio email), E6, E6.8, E4c-H, E6.9 (revisione di sicurezza: nessuna vulnerabilità), E4c (`same_email`); all-backend 21 506/0; `log.md` della devWiki per unione | `19d4d90d4` |
| 140 | 16/10 21:42 | Y: Y12b (P19: la riga del recupero di L1 legge il campo del backend) + spec dei tooltip di L3 resa robusta; L4 lento sotto carico → Y-21 | `b71ba8b60` |
| 141 | 16/10 21:36 | B: B3 ripristino (CLI e scheda Backup, B5b), P7 (mai applicato a istanza bloccata), B5c biglietto dell'esito (N53), B-17, B-13 totali di controllo, B6a-bis guida, ordine d'avvio N57; all-backend 7/7 | `1d9709ec4` |
| 142 | 16/10 21:55 | W: decisione 47 (la metà che cede va al costo medio; gambe sole convertite all'avvio) provata con J-24; all-backend 7/7 su `ebbd2025a` | `4b40ca5a0` |
| 143 | 16/10 22:08 | H: docstring di `instance_block.py` (rotte pubbliche fuori lista, pagine dei link) | `b9b468ae2` |
| 144 | 16/10 22:10 | Y: Y-14 («Aggiorna» della lista dei broker ricalcola le schede) | `e47a0dee3` |
| — | 16/10 22:15 | E: E-4 (nome non deprecato del 422 in `settings.py`) | `17021ea3c` |
| 145 | 16/10 22:25 | J: CP-7b (riferimento dei lotti aperti da un ADJUSTMENT dalla serie della casa, al cambio del giorno d'apertura; giorni al costo come il Dashboard; chiude J-28) | `d4284390b` |
| 146 | 16/10 22:24 | Z: lotto B, Z-18 (la ricarica in sottofondo non svuota la pagina; `pageBusy`) | `5e68a19b2` |
| 147 | 16/10 22:29 | X: C-90 (nota sull'ambito della sonda) | `3865f8e3e` |
| 148 | 16/10 22:32 | Y: Y-19 (la durata della peggior caduta legge la fonte del backend) | `e9f2fd019` |
| 149 | 16/10 22:45 | Y: Y-20 (riferimenti del laboratorio del rischio) | `0d471c5d6` |
| 150 | 16/10 23:03 | E: E-10 (la verifica dell'email su istanza bloccata) | `3fc8a5715` |
| 151 | 16/10 23:05 | B: H-17 e doc del ripristino | `38c0966c5` |
| 152 | 16/10 23:12 | H: H-23 (l'azione `pure` singola tiene il DB della corsia) | `64d1b4c36` |
| 153 | 16/10 23:15 | MF: MF-B (le schede dei broker leggono la fetta del motore) + MF-H (uno split non azzera la finestra di detenzione) | `049d4c8bb`, `66839ec73` |
| 154 | 16/10 23:24 | W: FE8b (il frontend delle transazioni in `features/`; congelamento annunciato e tolto) | `af6cd2899` |
| 155 | 16/10 23:28 | J: J-27 (`ledger_totals` legge solo decimali semplici) + ponte della sonda AI Export col plugin Svelte; J-26 chiusa | `8042271e1` |
| 156 | 16/10 23:36 | X: P20 sotto-lotto 1 (indirizzo di supporto `mailto:`); conflitto su `hosting_providers.en.md` risolto unendo i due punti | `127299d5f` |
| 157 | 16/10 23:41 | H: H-24 (file nascosti e di test non fanno ricostruire il frontend) | `f76f7d0c7` |
| 158 | 16/10 23:46 | W: C-97a seguito, il costo Auto non passa dal controllo dei decimali (trovato dagli E2E di FE8b) | `e50f85b5f` |
| 159 | 16/10 23:51 | Z: lotto A, Z-3 (giorno dell'utente), Z-8 (niente poll senza fornitore), Z-19 (N58) | `f8e78b003`, `50945715e` |
| — | 16/10 23:24–23:46 | Colori: W FE8b in tandem; L audit fuori metrica `d7f52fcf4`; G `backup ready` `9990d7f03`; T tabelle e 23 ruoli mancanti `3680c4010` | — |
| 160 | 16/10 23:55 | Z: wiki-file `utc-today-vs-user-calendar` (Z-3), Z-20 = disaccoppiare `zodios-client` da `instanceNotices`, vecchia Z-20 → Z-21 | `98fc97a9e` |
| 161 | 17/10 00:00 | E: revisioni di sicurezza R13-SEC e R13-SEC2 nel journal (W-B58 MEDIUM, W-B59, X-R35/36, A-32..35, B-19) | `79154f73b` |
| 162 | 17/10 00:05 | Y: Y-21 (scadenze reali dei test del rischio, blocco «functional integration» a 90 s), Y-5, sezione `pageBusy` | `0c86b22f0` |
| 163 | 17/10 00:10 | H: H-25 (il passaggio parallelo solo per la categoria intera) | `a061ce205` |
| 164 | 17/10 00:15 | A: A7b (pagina `/setup`, avviso registrazione aperta, admin in attesa, A-13) + CHANGELOG A7a/A7b | `531889efc`, `a168f2dfd` |
| 165 | 17/10 00:20 | X: F21 + P20 sotto-lotto 3 (fonti premium in testa, «Non lo trovi? Faccelo sapere») | `9e9a529f0` |
| 166 | 17/10 00:25 | J: CP-9a (servizio del rischio diviso per tema, T-R1 metà rischio); `devWiki/log.md` per unione; TODO_FUTURI allineato | `aefe89c43`, `601ef56c0` |
| 167 | 17/10 00:35 | Y: Y-22 (scadenza dell'aiuto L3), Y-23 (mock `onNavigate`, rosso di dev da `7fc594f8d`), riferimenti di riga | `572b58058` |
| 168 | 17/10 00:38 | X: X-R22 (l'avviso del segreto illeggibile dice l'ordine: prima la chiave vecchia) | `cac1a3ac5` |
| 169 | 17/10 01:06 | MF: MF-P (variazione del giorno e gruppi) e MF-A (tabella Performance dal motore); journal MF | `d7557b79e`, `5d50114f3`, `3bde7df80` |
| 170 | 17/10 01:12 | X: X-R37 (link al report in managed, N61) | `894118b95` |
| 171 | 17/10 01:23 | X: X-R35 (le impostazioni URL rifiutano user info) | `32ec5efbc` |
| 172 | 17/10 01:33 | J: CP-10b (runtime dei segnali in `services/signals`) | `2d25d0a94` |
| 173 | 17/10 01:45 | H: H-26, residuo di H-24, H-28 (file nascosti della build) | `e905f2b5d`, `eb209ff8d` |
| 174 | 17/10 01:50 | E: E-9 (alias delle caselle, nessun testo di estranei) | `ae9680133`, `d0a163747` |
| 175 | 17/10 01:57 | Z: Z-14 (cache dei prezzi dopo il recupero); W: W-B58 (limite dei decimali), W-B59 (precarico BRIM) | `80f861d9a`, `87e6cf5d0`, `df1d9c2e4` |
| 176 | 17/10 02:02 | Z: Z-21 (aiuti solo-test rimossi) | `6a0f0110d` |
| 177 | 17/10 02:04 | MF: MF-E1 (riepilogo dei lotti in casa, riepilogo FIFO v3); X: O-8 (messaggi del data editor) | `393fcf577`, `b360f3774`, `f35e8ef01` |
| 178 | 17/10 02:40 | H: H-27 (tipi dei default di profilo) | `8c489753c` |
| 179 | 17/10 02:50 | E: E-11 (reinvio con istanza bloccata) | `9da99ad70`, `bd229d1c6` |
| 180 | 17/10 03:07 | E: journal R13-SEC4 ed E-12 | `db1093a7d`, `8faa0574d` |
| 181 | 17/10 03:09 | H: H-29, H-30 (file nascosti) | `7ef6d738a`, `0cc482a53` |
| 182 | 17/10 03:11 | A: A7b-2 (ritiro del link di setup, 422 senza input); ⚠️ marcatori in `overview.md` corretti | `7e0b8d468`, `e4fe1e6c2`, `1063a0771` |
| 183 | 17/10 03:17 | J: CP-10c (taglio del servizio dei segnali) | `180d50d25` |
| 184 | 17/10 03:28 | B: B4 (backup sicuri `.lfbk`) | `4fc5187f4`, `6df5413ba` |
| 185 | 17/10 03:38 | Z: Z-20 (client senza moduli runes) | `7f6278f4a` |
| 186 | 17/10 03:40 | MF: MF-P4b (frazioni dei periodi), MF-J1 (un solo replay) | `0f5077d17` |
| 187 | 17/10 03:58 | E: journal R13-SEC5 | `b5d2dae47` |
| 188 | 17/10 04:05 | Z: Z-22 (listener HMR di instanceBlock) | `ac42ff00d` |
| 189 | 17/10 04:17 | H: H-32 (float delle richieste finiti) | `409d4dff8` |
| 190 | 17/10 04:45 | H: H-33 (log della validazione delle risposte) | `aabbb7b2c` |
| 191 | 17/10 04:48 | Y: Y11 lotto assets (pageBusy sulle pagine asset) | `33040d454` |
| 192 | 17/10 04:50 | B: B4b (residui dopo un crash, correzioni ai backup) | `1db2d6415`, `d70dc34f9` |
| 193 | 17/10 04:51 | H: wiki-file della notte; ⚠️ marcatori in `devWiki/index.md` corretti | `aff170af1`, `91152b34d` |
| 194 | 17/10 04:54 | X: X-R24/25, X-R38, X-R40/W-B62, X-R50 | `3759677aa` |
| 195 | 17/10 04:56 | Z: Z-10 (spegnimento del server di sviluppo) | `6aa2bdd47`, `98e06cfd1` |
| 196 | 17/10 05:01 | J: CP-14a (casa degli interessi, P-10, V-4) | `31ddab1a4`, `65f2949ec` |
| 197 | 17/10 05:08 | X: X-R51 (quotazione live rifiutata, nominata) | `aef812c47` |
| 198 | 17/10 05:11 | MF: MF-W56 (arrotondamento WAC), MF-J2 (il trasferimento tiene i rendimenti); conflitto del runner risolto a mano | `68d662266`, `5fe686634` |
| 199 | 17/10 05:13 | E: journal R13-SEC6; W: C-97b (input decimale) | `743c7ef8e`, `7d864f053`, `8fb618fc5` |
| 200 | 17/10 05:16 | MF: MF-D1 (rendimenti in casa), MF-D2 (drawdown con perdita totale, v2) | `6a6bc7a1f`, `c0378cdd0` |
| 201 | 17/10 05:25 | X: X-R52 (un giorno BCE non numerico salta solo quel giorno) | `ea6085000` |
| 202 | 17/10 05:27 | Y: R17/W8/P4 (cifre della Dashboard dal backend) | `d7b84ebac`, `9606a90f7` |
| 203 | 17/10 05:32 | Z: journal, piano Z-14b/Z-15 | `1da1b3123` |
| 204 | 17/10 05:38 | Z: Z-16 (albero di `admin/filesystem` in it/fr/es) | `ef1f02d47` |
| 205 | 17/10 05:41 | J: CP-14b (ACT/ACT ISDA, liquidazione, soglia del righello); backlog T-D9, T-U8, J-44 | `33b8c3aae`, `b090055f0` |
| 206 | 17/10 05:48 | B: B-28 (il ripristino rifiuta oggetti estranei nello schema) | `641f8714f`, `9464ea750` |
| 207 | 17/10 05:56 | E: journal, rossi di E-13, R13-SEC7 | `6e06bf896` |
| 208 | 17/10 05:57 | MF: MF-P2 (endpoint delle variazioni a periodo fisso) | `0f3e20be2` |
| 209 | 17/10 06:08 | Y: Y-2 (linea settimanale), Y-16 (test delle candele); B: B-29 (totali illeggibili della copia) | `fe83783f1`, `3164cf31e`, `61eb3cb36` |
| 210 | 17/10 06:16 | H: H-36 (proxy locale non fidato, N70) | `ab60cff17` |
| 211 | 17/10 06:31 | Z: Z-11 (lock dei job fra i worker, N71); B: B-16 (il riavvio che non avviene lo dice) | `f8a6ab22c`, `7976d82a2`, `a6cd8b9b5` |
| 212 | 17/10 06:38 | Z-11 runner descriptions | `c4742a661` |
| 213 | 17/10 06:40 | W-B60 amounts and event values read exactly | `6d402550d` |
| 214 | 17/10 06:47 | H-37 missing profile entry fails closed | `564f50635` |
| 215 | 17/10 06:48 | MF R13-SEC7-2 SI bounds, closed-form late interest | `3a24efc66` |
| 216 | 17/10 06:56 | X-R47 split ratio at write, X-R47b P-10 fails closed | `4ac8018f6` |
| 217 | 17/10 07:07 | H Z-24 scheduler lock guard, H-39 review rule | `6a28515a3` |
| 218 | 17/10 07:07 | J-43 share mismatch notice, R13-SEC7-1 bounded ranges | `42d00b0d8` |
| 219 | 17/10 07:10 | MF-SI1 first sync from min, aligned late interest | `5bd95341e` |
| 220 | 17/10 07:21 | A8a login limit + security checks, N70 untrusted proxy, E-13 | `cafe7e645` |
| 221 | 17/10 07:23 | G banner comments | `fa622cc5a` |
| 222 | 17/10 07:30 | E journal, N70 review, E-14 | `6d96e5fb4` |
| 223 | 17/10 07:31 | X-R43 plugin settings integers past 2^53 | `a0addb818` |
| 224 | 17/10 07:37 | B-9 backup startup checks | `17207cacd` |
| 225 | 17/10 07:39 | Y-8 arrows re-aimed on zoom settle | `b2964834c` |
| 226 | 17/10 07:42 | J F5 P-10 message, J-44 tooltip delta | `a4667defe` |
| 227 | 17/10 07:43 | H-34 non-finite numbers in free JSON | `2f6c9dc66` |
| 228 | 17/10 07:46 | MF-D4 invalid split ratio counts as missing | `59ab2b8ae` |
| 229 | 17/10 07:57 | E-14 limiter evicts fewest live hits | `f96b7b91f` |
| 230 | 17/10 08:01 | B-30 full disk at short starts | `03240f7cb` |
| 231 | 17/10 08:15 | H-39 managed frame/CSP checks, docs | `e1a9a78c5` |
| 232 | 17/10 08:29 | J-45 engine off the event loop | `592b5ca3b` |
| 233 | 17/10 08:30 | X-R55 query date range ceiling | `994f3bae0` |
| 234 | 17/10 08:39 | X-R53 delta columns from the server | `24305083a` |
| 235 | 17/10 08:46 | W-B69 auto cost refuses unreadable pool | `b3b0c0583` |
| 236 | 17/10 08:46 | B-31 coded confirm/cancel/restart failures | `de4fb606d` |
| 237 | 17/10 08:54 | Y-25 arrow re-aim costs, Y-3, Y-4 | `acad94499` |
| 238 | 17/10 09:10 | A8b Administration group + Security tab, A-21a usernames | `e7d4a4162` |
| 239 | 17/10 09:24 | B-19 decrypt as data dir owner | `7a475674e` |
| 240 | 17/10 09:25 | H-35 config audit after A8a and B-9 | `0018f2692` |
| 241 | 17/10 09:43 | X-R48 wipe refuses costless split adjustments | `83b56fbc5` |
| 242 | 17/10 09:53 | G point-33 run | `c825c4714` |
| 243 | 17/10 09:56 | E-8 invitation language, Administration paths | `5fa1ee0f2` |
| 244 | 17/10 10:02 | W SEC7-3 input bounds, H-41, event-store fix | `d18e20c73` |
| 245 | 17/10 10:02 | H-19 address probe 503 | `d9cd65d0b` |
| 246 | 17/10 10:04 | J-10 scope-edge transfer reading, E2 params | `135ba8c01` |
| 247 | 17/10 10:05 | MF-SEC8-2 replay floor 1900 | `7acb12d17` |
| 248 | 17/10 10:20 | Y-27 DataTable keeps absent column prefs | `3e926ccf4` |
| 249 | 17/10 10:28 | B-32 refused cancel, unreadable restore state | `4226cef79` |
| 250 | 17/10 10:28 | Z-25 bulk caps on price and FX queries | `bdaaaee4f` |
| 251 | 17/10 10:29 | MF-P2b period-changes bounds | `dd5471a64` |
| 252 | 17/10 10:41 | E-8.5 email Vitest cure | `d6c930aeb` |
| 253 | 17/10 10:43 | J-47 transfers in transit at date_to, P-10 docs | `29438a1ca` |
| 254 | 17/10 10:45 | X-R44 test-only providers withheld outside test mode | `296187488` |
| 255 | 17/10 10:59 | Y V11 + P5 lots values and declared aggregates | `62a7e8c40` |
| 256 | 17/10 11:00 | B-18 restore --instance-key-file, B-20 | `f038c75e6` |
| 257 | 17/10 11:03 | X Y-28 C-66 test past period, X-R57 | `7976f187c` |
| 258 | 17/10 11:05 | Z-26 scheduler lock wait bound, FX at-least | `6841e0325` |
| 259 | 17/10 11:10 | A9 legal notice and managed profile | `5c1806198` |
| 260 | 17/10 11:14 | W-B71 date windows at the calendar edge | `22296d87e` |
| 261 | 17/10 11:18 | Y-29 gate annualizing flag | `3b87cf7ea` |
| 262 | 17/10 11:22 | W-B69 batch half, N74 shared floor | `62faa88aa` |
| 263 | 17/10 11:28 | E-15 login limit restored per test | `7f1eec6ff` |
| 264 | 17/10 11:36 | H-42 page policy on HTML responses | `ac307e05d` |
| 265 | 17/10 11:45 | J-50 oversized price loads refused with a code | `0392b233f` |
| 266 | 17/10 11:47 | Z-28 lock files refuse symlinks | `85a8549c4` |
| 267 | 17/10 11:51 | T theme-roles (c) | `6c260d327` |
| 268 | 17/10 11:52 | B-18 repair, BZ part 1 records | `e2d763959` |
| 269 | 17/10 11:54 | H-46 test mode outside test lanes | `0369806c2` |
| 270 | 17/10 12:02 | A9 fix-forward forgot-password on failed config | `104278401` |
| 271 | 17/10 12:04 | W-B74 balances refuse unreadable rows | `734f7689b` |
| 272 | 17/10 12:14 | E R13-SEC9 review | `f26da25df` |
| 273 | 17/10 12:24 | E-16 forgot page docs | `3d5a12af3` |
| 274 | 17/10 12:25 | X-R49 plan change refuses costless split adjustments | `97cc158ad` |
| 275 | 17/10 12:35 | H-45 page policy on XML docs, none on 304 | `b019307bd` |
| 276 | 17/10 12:35 | X TS2769 e2e point type | `7d70723d9` |
| 277 | 17/10 12:42 | B-35 restore unpack cap | `a17b08230` |
| 278 | 17/10 12:43 | E-17 e2e tsc clean | `ef66e0e01` |
| 279 | 17/10 12:52 | J-12 backend and AI Export half | `eab21833a` |
| 280 | 17/10 12:52 | Y J-12 panel half | `20005dc94` |
| 281 | 17/10 12:52 | J-12 log graph line, CHANGELOG | `6bf596033` |
| 282 | 17/10 13:07 | X-R44c test_only guard | `bc9f95233` |
| 283 | 17/10 13:08 | B-39 CSV formula escaping | `e7f6d51c1` |
| 284 | 17/10 13:09 | W-B72 refuse stray cost basis N78 | `27fd71603` |
| 285 | 17/10 13:10 | Z-27 web batching, SEC9-2 1M budget | `7eb7d706a` |
| 286 | 17/10 13:10 | H-49 lane id bounds | `ce4bcefbc` |
| 287 | 17/10 13:15 | H B-35 review fixes | `1e2141a91` |
| 288 | 17/10 13:17 | A-42/A-43 setup link lifecycle | `21d9172e9` |
| 289 | 17/10 13:33 | B-36/B-37 quoted tables, untrusted schema | `25e4a06bb` |
| 290 | 17/10 13:42 | X-R60 freshest Δ answer, no needless periods | `e052d2907` |
| 291 | 17/10 13:45 | MF X-R59 range change, SEC8-2a/2b, SEC9-1, D3, SI2, J45a | `b284dd624` |
| 292 | 17/10 13:55 | J-50b one remedy table | `99a21e338` |
| 293 | 17/10 13:56 | SEC8-1b risk and replay date bounds | `e6affb02b` |
| 294 | 17/10 13:57 | Y-31 E2E J12 locale rule, WAC state (pick) | `8550bc3a8` |
| 295 | 17/10 13:57 | B-38 secret files read as root | `2d2a5bc7c` |
| 296 | 17/10 14:00 | W-B67 Auto cost on its own row N84 | `0734125e2` |
| 297 | 17/10 14:02 | A profile helper, A-50, SC-LANE-01 | `4323a203f` |
| 298 | 17/10 14:04 | E journal, MF-SEC9b analysis | `dc31bd7ec` |
| 299 | 17/10 14:10 | B-34 missing instance key message | `2bab9fbe9` |
| 300 | 17/10 14:12 | X-R62 coded provider removal refusal | `c90d72f38` |
| 301 | 17/10 14:14 | W-B72 html gate fix | `a8dc4ac7e` |
| 302 | 17/10 14:26 | J-33 lots performance at cost | `dd967e079` |
| 303 | 17/10 14:38 | MF-SEC9a bulk writes chunked | `65ed62147` |
| 304 | 17/10 14:39 | X-R64 batched period changes and live poll | `34236283d` |
| 305 | 17/10 14:39 | W-B75 BRIM plain-data params (H) | `c2c63fdf7` |
| 306 | 17/10 14:41 | A-46/A-47 username rules | `40f90d9c7` |
| 307 | 17/10 14:49 | W-B66 pasted exponents | `5634c9649` |
| 308 | 17/10 14:53 | J-51 YoC unseen-broker arrivals | `241565aa3` |
| 309 | 17/10 14:53 | X-R65 stored date bounds (Z) | `6408e5553` |
| 310 | 17/10 14:53 | E-18 strict ISO currency on writes | `988805031` |
| 311 | 17/10 14:54 | B-41/B-42 outcome log noise | `affcbfab9` |
| 312 | 17/10 15:00 | J-36 lots reference-price texts | `60ee958fe` |
| 313 | 17/10 15:06 | MF-SEC9a rest + MF-SEC9c | `24b52f8e4` |
| 314 | 17/10 15:11 | W-B68 provider event values truncated | `7b2e2c6f3` |
| 315 | 17/10 15:19 | J-49 range seam check | `cd32b1229` |
| 316 | 17/10 15:39 | Z-30 full-history load floored at 1900 | `97fa29126` |
| 317 | 17/10 15:40 | risk Intl guard (J) | `c933b42d6` |
| 318 | 17/10 15:47 | MF-SEC9e exact delete counts, A2 docs | `3dfd5490f` |
| 319 | 17/10 15:48 | H-51 untrusted schema on every connection | `49e0a97a6` |
| 320 | 17/10 15:55 | H-47 design and B-37 clause | `24ac82f8b` |
| 321 | 17/10 15:57 | Z-30 follow-up (plural, comments) | `0a9e2bbce` |
| 322 | 17/10 16:01 | X-R58 bulk refusal toasts | `0fa46aaa8` |
| 323 | 17/10 16:01 | X-R71 manual upload currency all-or-nothing (B) | `3cc5b2184` |
| 324 | 17/10 16:04 | H backlog reconciliation | `da505ac28` |
| 325 | 17/10 16:04 | C-97c-1 price and quantity digits | `66917cfb6` |
| 326 | 17/10 16:05 | A-51 setup cancel under the lock, A-45 | `f6863a208` |
| 327 | 17/10 16:15 | E-19a stored currency audit and guards | `d44616c3b` |
| 328 | 17/10 16:16 | T-B7 all-null columns named (J) | `dff3e6b21` |
| 329 | 17/10 16:17 | docs(journal): close T-B7 | `4fa3cb108` |
| 330 | 17/10 16:21 | X-R59 lots A/B range change from backend (Y) | `d2f489be8` |
| 331 | 17/10 16:28 | MF-J45b single-flight, A4 docs | `c2f1d2c1c` |
| 332 | 17/10 16:41 | B-43/B-44 unreadable copy refused | `15909dd77` |
| 333 | 17/10 16:55 | C-97c-2 lot digits | `117762058` |
| 334 | 17/10 17:00 | X-R74 generic 500s on asset and FX routes | `88611daf5` |
| 335 | 17/10 17:04 | MF-SEC9g BRIM classification off the loop | `932cec524` |
| 336 | 17/10 17:08 | J-54 null-means-none columns | `b0d1db26d` |
| 337 | 17/10 17:08 | docs(journal): close T-B9 as verified | `021af3bd6` |
| 338 | 17/10 17:11 | J-53 lot-less banner lines (Y) | `c6f44c54d` |
| 339 | 17/10 17:11 | docs(changelog,journal): J-53 banner lines | `217d38540` |
| 340 | 17/10 17:28 | E-19a step-order fix-forward | `cbce7ab59` |
| 341 | 17/10 17:35 | MF-A5 closed position base | `428123a87` |
| 342 | 17/10 17:39 | J-52 stress replayed window | `da6a4b218` |
| 343 | 17/10 17:43 | Y-33 asset-detail navigation wait | `55753d807` |
| 344 | 17/10 17:47 | C-54 what's new after an update (A) | `70bccb5d2` |
| 345 | 17/10 17:48 | docs(changelog,journal): C-54 what's new | `742bbcd61` |
| 346 | 17/10 17:57 | MF-J45d failed build fails waiters | `86e120a43` |
| 347 | 17/10 17:59 | Z-32 (c) pence quote warning | `ea1eaddf7` |
| 348 | 17/10 18:02 | C-97c-3 asset and chart price digits | `22ba32954` |
| 349 | 17/10 18:03 | W-B55 decision 47 in USD (J) | `1123282d9` |
| 350 | 17/10 18:03 | docs(journal): close W-B55 | `1d8bbf2da` |
| 351 | 17/10 18:24 | MF-A8 received units at arrival value | `df36d80c7` |
| 352 | 17/10 18:26 | CP-10d market_series rename (J) | `a3a49265b` |
| 353 | 17/10 18:31 | X-R75 atomic route replace (B) | `b58786ecb` |
| 354 | 17/10 18:36 | X-R66 probe rate limit i18n (A) | `17bbd533f` |
| 355 | 17/10 18:36 | docs(changelog,journal): X-R66 probe limit | `7625f9b39` |
| 356 | 17/10 18:46 | MF-A9 open received rows | `2c4fb76ae` |
| 357 | 17/10 19:00 | X-R46 data editors name refused values | `fc8ea34e0` |
| 358 | 17/10 19:15 | H-43 phase 1: managed test lane, CSP collector | `ae4e9b845` |
| 359 | 17/10 19:15 | H-43 runner tests (follow-up) | `7bd2d2eb5` |
| 360 | 17/10 19:16 | MF-A7 dust residual not an open lot | `3753c01dd` |
| 361 | 17/10 19:17 | W-B70 field error params, merge limit (+ W-B77, W-B73) | `14bd65469` |
| 362 | 17/10 19:30 | J-21 signal gaps, J-16, docs batch J-18/J-23/J-38 | `c6edabeab` |
| 363 | 17/10 19:32 | docs(skills): wiki-file example matches RealDecimal | `0fb31ce0a` |
| 364 | 17/10 19:41 | Y-24 bounded lazy report retries | `81970e873` |
| 365 | 17/10 19:45 | C-97c-4 weak-currency FX rate digits (X) | `5e0bfbeff` |
| 366 | 17/10 19:46 | MF-J45c L2 report sharing guard | `0c866ff73` |
| 367 | 17/10 19:54 | E-19b1 non-ISO currency suggestions, restore warning | `9955157aa` |
| 368 | 17/10 19:56 | A-11/A-16/A-40/A-26 accounts fixes | `3cedf7c71` |
| 369 | 17/10 19:58 | A journal: A-54..A-58 filed | `e00b93381` |
| 370 | 17/10 20:00 | W-B48 testid selectors, W-B51 BRIM quantity duplicates | `7ac28d903` |
| — | 17/10 00:05–00:45 | Colori: AF file, media e menu `a4bf32a44`; T `CompactCashCell` `e9e1fb1eb` | — |
| 20/10-T1 | 20/10 09:17 | Z-29a v3 + Z-29r, B-8 rifinitura, N69a, X-R45b-ui + N61-form, L1a | `ad869d2ea` |
| 20/10-T2 | 20/10 10:10 | H-60, E-AI503/E-20/E-24, X wac-inf, Z-29d-0 + Y-38, B-50, B-52, MF-P1b, J-57, Z-32 (d) backend | `1feacc35e` |
| 20/10-T3 | 20/10 11:31 | Z-32 (d) frontend, J-66 + §29, W-B89 + B-51, E-24.2, B-53/54/55, MF-E2, mappa guide + N70, P3 (X) + Z-39 | `283259261` |
| 20/10-T4 | 20/10 13:34 | E-23, Z-29a-f, J-67, MF-E2b + P3 consumatore, N69b | `8fd43a901` |
| — | 20/10 14:15 | G: note N69, G-28 fixture sicurezza «ok» | `b417fbd95` |
| 21/10-T5 | 21/10 | `.claude/` + CLAUDE.md; J-60 + J-70; A: `admin_setup_status` (H-61); E: galleria Email + traduzioni | `1f8a42b6d` |
| 21/10-T6 | 21/10 | Y-39a (un solo modulo per i segnali di card e anteprima), H-61 R1 (`GET /api/v1/panel/status`), Z-29s-a (segnali ridotti sui secchi del prezzo) | `b766a5170` |
| 21/10-T7 | 21/10 | Ondata 2 (7 sessioni): Y-39b (anteprima come il dettaglio, colore della base sulle schede), O1 + Z-29b (serie dei segnali allineate, schede ridotte nella lista Assets), H-61 CP2 (biglietti Ed25519 del pannello), Fineco W-B92 (commissioni non più contate due volte, guida a 6 immagini, beta tolta), W-B86/W-B87 (avvisi sulle righe lasciate fuori), K3a + #58 (Bulk e Form sicuri, asset e broker bloccati in modifica), colori C1 (broker, impostazioni, PAC, dettaglio asset e cambi) e C2 (serie dei grafici sui ruoli) | `c3771f6e4` |
| 22/10-T8 | 22/10 | Ondata 3 (10 lavori): Y-40 (vista Rolling Return su liste asset e cambi, dettaglio nella vista della scheda), Z-29fx + Z-29d (conversioni dei cambi campionate), H-55 v2 (CSP applicata ovunque, revisione di sicurezza) + Esc dei modali, E-25 + E-26 (verifica email al clic, email trattenuta detta), A-62 + E-7 (menu tradotto, badge «In attesa di verifica»), TC-23 + L1b + Q-G29-1 (aggiungi coppia dal rischio, lotti a gradini, tooltip del Gantt), Y-42 + N64 (dettagli sul modulo comune, indicatori in cache), N78-1 (rettifica in uscita senza valore), colori C1 (transazioni) e C2 (tipi dai ruoli) | `6049158b1` |
| 22/10-T9 | 22/10 | Ondata 4 (10 sessioni: MF, D, Y, Z, X, A, J, W, H) | `8b0375db1` |
| 23/10-T10 | 23/10 | Ondata 4, coda: backup L3 e H-62 (H + B), contatori e attese delle email (A) | `96e8db455` |
| 26–27/10-T11 | 26–27/10 | Ondata 5 (MF, J, Z, Y, X, W, A, B, H), D-P4 L4–L5 (niente pavimento del 1900), integrazione | `befd4e3fe` |
| 27–28/10 | 27–28/10 | Base dell'ondata 6: chiave della cache CI, regola BRIM della data dell'ordine, `tzdata` nel Pipfile, J-39 e ribilanciatore del PAC nei TODO futuri | `bc1d4c06c` |
| 30/10 | 28–30/10 | Annotazioni OCI delle immagini su GHCR, test della chiave della cache | `485796ce1` |
