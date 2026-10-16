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

## Sessioni

Ramo di integrazione: `dev_release2` (condiviso con il programma colori). Corsie: preambolo
`PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py test --test-port <PORTA> --data-dir <DIR> …`.

| Lettera | Sessione | Corsia | Data-dir | Ramo | HEAD | Stato |
|---|---|---|---|---|---|---|
| — | Coordinatore 1.3 (in place) | 6180 | `/tmp/librefolio-r13-main` | `dev_release2` | — | attivo |
| H | H - Piattaforma | 6181 | `/tmp/librefolio-r13-h` | `e-alfy-h-piattaforma` | `338eaa240` | ✅ CP1 (`6a605904c`), CP2a (`60f8a35ce`, pacchetto `config/`), CP3 (`d08d9358f`: segreti da `*_FILE`, chiave d'istanza, controlli all'avvio), il lotto `web_link_finder` (`9dda5ccd9`), CP4 (`1b3eb54c7`: router di sistema per risorsa, `/system/instance`, area degli avvisi) e CP5a (`9deb0ea08`: `/system/ready`, `/system/info` minimo senza sessione, R2) integrati; CP5b e CP6 (blocco dell'istanza) committati sul ramo (`5b2b9061f`, con la base), entrano dopo la finestra della galleria; scritti, da provare: CP7a (Docker), C-96 (corsie dei test senza la configurazione del `.env`), filtro dei token nel log d'accesso; CP2b sbloccato: la 1.2.1 è in `dev_release2` (`6c349f907`) (sessione `8490facf`) |
| A | A - Account e accessi | 6182 | `/tmp/librefolio-r13-a` | `e-alfy-a-account-e-accessi` | `5e21149e5` | ✅ A1 (`769cc31cb`), A2 (`76e61889b`, frontend in `lib/features/`), A3 (`90491071d`: registro delle schede, O-15, K-17, L12), A4 (`e476d2ed4`: migrazione 005, token monouso) e A4b (`dbf89cdd5`: versione di sessione `sv`) integrati; A5a committato sul ramo (`7da2cd9a2`, base aggiornata in `8e049474e`); in corso A5b (frontend, token nel frammento dei link); A5a e A5b entrano insieme dopo la finestra della galleria (sessione `119ed166`) |
| X | X - Plugin asset e ricerca | 6183 | `/tmp/librefolio-r13-x` | `e-alfy-x-plugin-asset-e-ricerca` | `e78eb7b6f` | ✅ CP1 (registri per famiglia), CP2a (`services/assets/`, senza shim, `64a5a3fe7`), CP2b (`92b42d796`: asset per tema, router per risorsa, eventi nei loro moduli), CP3 (`8000aba5a`: cambi per tema in `services/fx/` e `api/v1/fx/`), CP3b (`63a1f675c`: test dei cambi senza rete, W-B9, W-B13, X-R5, X-R7), CP4 (`7f4618494`: schemi degli asset per tema), J-5 (`743fca514`) e X-R8 (`173ba19e2`: elenchi delle valute dei fornitori in cache) integrati; committati sul ramo, entrano dopo la finestra con le loro E2E: FE5b-1 (`37532d558`, `AssetModal` in sei pezzi), FE5b-2 (`fc6220d28`, logica in moduli puri), X-R11a (`ac89cea72`), X-R1 e X-R2 (`f8d87ed9c`); disegno del ripristino per B nel CP10 (sessione `ad5f37c8`) |
| W | W - Import e transazioni | 6184 | `/tmp/librefolio-r13-w` | `e-alfy-w-import-e-transazioni` | `9ccbdb3a2` | ✅ W1 e W2 (`998fd2701`), I1 (`dc7e4e48e`: V-23, C-65b, L5, C-79/C-3), K1 (`d915c869f`: O-12, C-89, V-38, P-15), W4 CP6 (`155d9b050`, BRIM in `services/brim/`), W7 (`1cd7300f3`, `schemas/transactions/` per tema), K2a (`62c964242`: rifiuti a codice, L6) ed E0 (`d226bc69e`: eventi distinti per data e tipo, X-R9 per la parte di W, W-B15) integrati; FE8a committato sul ramo a tre pezzi (Form `8a62cea7f`, Bulk `464350cc7`, Wizard `b92e655d9`, quest'ultimo prima delle prove), entra dopo la finestra; N1 committato sul ramo (`6be11ecf3`: cassa del broker al giorno dell'utente, metà spaiate dei trasferimenti, con J), con la correzione post-migrazione N1b-2 (`5e19c6018`, entra solo con il via sul punto 46) e la sua doc (`3f42dda9d`); in corso N1b-3 (W-B22, W-B23); E1 aspetta le decisioni 20–23; CP7, W3 e W5–W6 sbloccati: la 1.2.1 è in `dev_release2` (`6c349f907`) (sessione `e71e0e34`) |
| J | J - Numeri e analisi | 6185 | `/tmp/librefolio-r13-j` | `e-alfy-j-numeri-e-analisi` | `1ce3cc85c` | ✅ CP-1 (`e1fbc801f`: PAC per tema in `schemas/pac_allocator/` e `services/pac_allocator/`, guardia dei confini D-J18), C-93 (`c412f8dad`), G-8 (`c75f08101`) e J-6 (`e2cb55054`: guardia di suite sulle connessioni aiosqlite) integrati; CP-2 e seguenti aspettano le decisioni 26–30 (D-J1, D-J2, D-J3, D-J6, D-J15) (sessione `4c677a01`) |
| Z | Z - Sospensione e risveglio | 6186 | `/tmp/librefolio-r13-z` | `e-alfy-z-sospensione-e-risveglio` | `da07f6366` | analisi consegnata; aspetta le decisioni 31 e 32 del developer (sessione `d401e062`) |
| B | B - Backup e Docker | 6187 | `/tmp/librefolio-r13-b` | `e-alfy-b-backup-e-docker` | `25cd742cf` | avviata il 15/10 alle 11:25, su delega del developer: B0 (divisione di `api/v1/backup.py`, `backup_service.py` → `series_export.py`) e B1 (backup dell'istanza, backend e CLI); B2–B4 aspettano i punti 38–43 e, B4, la finestra delle dipendenze (sessione `5618ecee`) |
| E | E - Email | 6188 | `/tmp/librefolio-r13-e` | `e-alfy-e-email` | `f4f995ce7` | avviata il 15/10 alle 11:25, su delega del developer: E0 ed E1 (configurazione SMTP, invio, testi, limitatore), senza `links.py` e senza la riga in `config_audit.py`; E3 aspetta il punto 45, E5 il 44 (sessione `877410cd`) |
| Y | Y - Cruscotto e grafici | 6189 | `/tmp/librefolio-r13-y` | `e-alfy-y-cruscotto-e-grafici` | `428170b0c` | analisi consegnata il 15/10 alle 12:00, aspetta il via del developer; avviata alle 11:28, dopo l'ingresso dei lotti A–D di R (sessione `17050e81`) |

Corsie del programma colori, da non usare: 6150–6154 e 6160. Lettere riservate ai colori:
L, R, G, T, C, U, S, P.

## Funzioni per il cloud

| Ondata | Funzione | Sessione | Stato |
|---|---|---|---|
| 1 | Pausa degli aggiornamenti e sospensione (F26) | Z | ⏳ analisi pronta; aspetta le decisioni 31 e 32 |
| 1 | Segreti e configurazione (F03) | H | 🟡 backend integrato (CP2a `60f8a35ce`, CP3 `d08d9358f`): segreti da `*_FILE`, chiave d'istanza, avvisi nel log, `.env.example` completo. Gli avvisi per l'admin arrivano con A8. `JWT_SECRET` resta casuale se manca, per la regola del developer sui default (piano H, §2) |
| 1 | Prontezza e versione (F08) | H | 🟡 backend integrato (CP5a, `9deb0ea08`); CP5b dopo la finestra |
| 1 | Profilo gestito (F05) | H, A, X | ⏳ la base c'è (`/system/instance`, CP4 di H); profilo e blocco dell'istanza con il CP6 di H |
| 1 | Disclaimer e link legali (F09) | A | ⏳ |
| 1 | Admin iniziale da variabili (F02) | A | ⏳ |
| 1 | Inviti, registrazione e gestione utenti (F13) | A | ⏳ in corso (A5a e A5b); i token monouso sono già integrati (A4) |
| 2 | Email facoltativa (F04) | E | 🟡 avviata (E0–E1); E3 aspetta il punto 45, E5 il 44 |
| 2 | Backup e ripristino dalla UI (F01) | B | 🟡 avviata (B0–B1); B2–B4 aspettano i punti 38–43 |
| 2 | Backup continuo con Litestream (F25) | B | ⏳ analisi pronta; il codice dopo il lotto Docker di H (CP7a) |
| 2 | Avvio, aggiornamento all'accesso e risveglio (F07) | Z | ⏳ analisi pronta; aspetta le decisioni 31–35 e gli agganci d'avvio di H (CP2b) |
| 2 | Impostazioni dei plugin | X | ⏳ dopo X-R8; migrazione 007, e `cryptography` nella finestra delle dipendenze |
| 2 | Ordine dei fornitori nella ricerca (F21) | X | ⏳ |
| 3 | Fornitore di prezzi a pagamento (F06) | X | quando sarà scelto |

## Riordino (ondata 0)

| Lotto | Sessione | Stato |
|---|---|---|
| Registri per famiglia di plugin (PL2) | X | ✅ X CP1 (`64a5a3fe7`) |
| Asset senza shim (PL6), cambi in `services/fx/` (PL4), router di asset e cambi, router dei segnali (PL7) | X | 🟡 integrati PL6 (CP2a), asset per tema e router per risorsa (CP2b), PL4 e router dei cambi (CP3), schemi degli asset (CP4); PL7 dopo PL1 di J |
| Import broker in `services/brim/` (PL5, U-B3, U-B4), transazioni, broker | W | 🟡 integrati transazioni e broker per tema (W1, W2), BRIM in `services/brim/` (W4 CP6), schemi delle transazioni (W7); restano CP7 (taglio di `brim_provider.py`), W3 e W5–W6 |
| Segnali (PL1), rischio, preparazione delle serie, portafoglio, PAC | J | 🟡 PAC per tema integrato (CP-1); il resto con CP-2 e seguenti, dopo le decisioni 26–30 |
| Piattaforma, file, agganci di `main.py`, configurazione | H | 🟡 integrati `services/platform/` e `services/files/` (CP1) e il pacchetto `config/` (CP2a); il taglio di `main.py` (CP2b) sbloccato dall'ingresso della 1.2.1 |
| Servizi account | A | ✅ A1 (`769cc31cb`) |
| Frontend: auth, settings, support | A | ✅ A2 (`76e61889b`) |
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
| 1 | 14/10 17:41 | Piano della fase, sezioni 1.3 nel backlog | `459131eb8` |
| 2 | 15/10 00:25 | A1: servizi account in `services/accounts/` | `769cc31cb` |
| 3 | 15/10 00:48 | H CP1: `services/platform/` e `services/files/` | `6a605904c` |
| 4 | 15/10 01:03 | A2: frontend di auth, settings e support in `lib/features/` | `76e61889b` |
| 5 | 15/10 01:09 | W1 e W2: transazioni e broker per tema | `998fd2701` |
| 6 | 15/10 01:20 | H CP2a: pacchetto `config/`, guardia sulle letture d'ambiente | `60f8a35ce` |
| 7 | 15/10 02:17 | X CP1 e CP2a: registri per famiglia, `services/assets/` senza shim | `64a5a3fe7` |
| 8 | 15/10 03:01 | W I1: rifiuti d'accesso, pulizia BRIM (V-23, C-65b, L5, C-79, C-3) | `dc7e4e48e` |
| 9 | 15/10 03:17 | A3: registro delle schede di Settings (O-15, K-17, L12) | `90491071d` |
| 10 | 15/10 03:45 | H CP3: segreti da `*_FILE`, chiave d'istanza, controlli all'avvio | `d08d9358f` |
| 11 | 15/10 03:46 | X CP2b: asset per tema, router per risorsa | `92b42d796` |
| 12 | 15/10 04:04 | W K1: chiarezza (O-12, C-89, V-38, P-15) | `d915c869f` |
| 13 | 15/10 04:15 | H: letture di `web_link_finder` in `config/` | `9dda5ccd9` |
| 14 | 15/10 04:29 | J CP-1: PAC per tema, guardia dei confini | `e1fbc801f` |
| 15 | 15/10 04:37 | W4 CP6: BRIM in `services/brim/` | `155d9b050` |
| 16 | 15/10 05:15 | A4: migrazione 005, token monouso | `e476d2ed4` |
| 17 | 15/10 05:24 | X CP3: cambi per tema in `services/fx/` e `api/v1/fx/` | `8000aba5a` |
| 18 | 15/10 05:35 | W7: schemi delle transazioni in `schemas/transactions/` | `1cd7300f3` |
| 19 | 15/10 05:54 | X CP3b: test dei cambi senza rete | `63a1f675c` |
| 20 | 15/10 05:57 | J C-93: connessioni aiosqlite chiuse nei test dell'AI Export | `c412f8dad` |
| 21 | 15/10 05:59 | H CP4: `/system/instance`, area degli avvisi | `1b3eb54c7` |
| 22 | 15/10 06:24 | J G-8: catalogo dei Tool sotto carico | `c75f08101` |
| 23 | 15/10 06:33 | X CP4: schemi degli asset per tema | `7f4618494` |
| 24 | 15/10 06:45 | W K2a: rifiuti a codice, L6 | `62c964242` |
| 25 | 15/10 06:54 | A4b: versione di sessione, uscita degli altri dispositivi al cambio password | `dbf89cdd5` |
| 26 | 15/10 07:12 | X J-5: loop chiuso nel thread dei fornitori | `743fca514` |
| 27 | 15/10 07:17 | H CP5a: `/system/ready`, `/system/info` minimo senza sessione, R2 | `9deb0ea08` |
| 28 | 15/10 07:40 | J-6: guardia di suite sulle connessioni aiosqlite lasciate aperte | `e2cb55054` |
| 29 | 15/10 07:51 | W E0: eventi distinti per data e tipo nel CSV e nel selettore della data (I-11 a e d), X-R9, W-B15 | `d226bc69e` |
| 30 | 15/10 08:18 | X-R8: elenchi delle valute dei fornitori dei cambi in cache per un giorno | `173ba19e2` |
| 31 | 15/10 12:47 | 1.2.1 (rilasciata dal developer alle 12:27): file serviti dentro le loro cartelle, file caricati mai eseguiti, `JWT_SECRET` di soli spazi mai usato come chiave | `6c349f907` |
| 32 | 15/10 13:35 | `cryptography` nell'ambiente condiviso (finestra delle dipendenze, installata dal developer) | `dc9a5d232` |
| 33 | 15/10 14:20 | H CP5b+CP6: blocco dell'istanza (`LIBREFOLIO_BLOCKED`, pagina di blocco, 423), `LIBREFOLIO_PROFILE`, `/system/block` | `83eaa5a28` |
| 34 | 15/10 14:22 | X FE5b (`AssetModal` in sei pezzi, logica in moduli puri), X-R11a, X-R1/R2, D-X4 | `ec0dc7ebd` |
| 35 | 15/10 14:45 | E1: servizio email (SMTP facoltativo, testi in 4 lingue, limitatore comune `rate_window`) | `f46a93ffd` |
| 36 | 15/10 15:12 | Y1: taglio di `GrowthChart` in moduli puri (FE6a), B10; galleria filtrata pulita | `badec1465` |
| 37 | 15/10 15:17 | A5: registrazione a tre modi, inviti e link di reset monouso, API admin degli utenti, limite di utenti | `8bcb23502` |
| 38 | 15/10 15:55 | H: CP7a (Docker: `tzdata-legacy`, una porta, `docker exec` con gosu, versione congelata), C-96, filtro del log d'accesso, G-10, riparazione di `test_instance_block.py` | `744f5a0ee` |
| 39 | 15/10 16:07 | Z1: pausa dei prezzi dal vivo (lista 60 s, dettaglio 30 s in un ciclo, pausa a scheda nascosta o dopo 2 minuti) | `9d2074b2b` |
| 40 | 15/10 16:19 | W: FE8a (Form, Bulk e Wizard divisi), N1 (broker al giorno dell'utente, metà spaiate), N1b-2/3 (`orphan_pair_halves`, punto 46), E1a ed E1c (eventi tutto o niente, `DELETE` per asset, `event_types`) | `14d58cc61` |
| 41 | 15/10 16:55 | J: C-94 (build del server di prova fuori dal timeout di avvio, `--build-only`, controllo di `node_modules`, galleria al 60 % delle CPU) e CP-2 (PAC: C-73…C-76) | `2faa88a34` |
| 42 | 15/10 17:20 | A6a: eliminazione da parte dell'admin, anteprima dell'eliminazione, sonda dell'indirizzo (nonce firmato) | `1840ebd62` |
| 43 | 15/10 17:40 | H: link di fatturazione e rotte dei link di reset a istanza bloccata, H-12 (controllo della porta solo sui listener), contratto `/system/instance` nelle E2E sintetiche, anteprima di A6a in `ALLOWED_WHEN_BLOCKED`, A-15 | `eacc34784` |
| 44 | 15/10 17:40 | Z7a: registro delle pause dei fornitori (`utils/runtime/cooldown.py`, `provider_cooldown`, `config/sleep_wake.py`), non ancora agganciato (X1–X8) | `2ab8a3a43` |
| 45 | 15/10 18:08 | Y2: taglio di `DataTable` (`DataTableColumnHeader`, `DataTableCellContent`), `~split` dichiarato | `c747a74c3` |
| 46 | 15/10 18:13 | W: E1b (salvataggio atomico degli eventi con `delete_ids`, «+ Nuovo evento» che non sovrascrive, pannello `EVENT_EXISTS`) | `fecf88c1a` |
| 47 | 15/10 18:15 | J: CP-4a (rendimenti di periodo, ritorno netto e rapporto G/L in `financial_math/returns.py`) e CP-4b (V-11, decisione 30: grazia dall'ultima quotazione) | `322d55042` |
| 48 | 15/10 18:30 | E2: `GET /email/status`, `POST /email/test`, controlli d'avvio email, `/system/instance.email`, scheda Email (130), scatto `settings/email` (rivisto da G) | `755158aad` |
| 48b | 15/10 18:44 | E2: correzione del gate `htmlInterpolation` (`SMTP_FROM_INVALID` senza `<` né `>`), dopo il rosso di `core-unit` trovato da T | `be7de95b6` |
| 49 | 15/10 18:58 | Z6b parte 1: `LIBREFOLIO_SHUTDOWN_TIMEOUT_SECONDS` (8 s), drenaggio di uvicorn a 3 s da `dev.py server` ed `entrypoint.sh`, grazia del runner e di Playwright a 10 s; watchdog cablato dopo CP2b | `000090aaf` |
| 50 | 15/10 19:07 | B: B0 (`backup.py` diviso, `series_export.py`), B1 (backup dell'istanza, API e CLI), B5a (scheda Backup), B6a (doc CLI), backup a istanza bloccata (`backup_available`), via i 4 segnaposto | `629d63306` |
| 51 | 15/10 19:37 | W: N2 (regola del costo dai metadati; modifiche controllate solo se toccano tipo, quantità, costo, valuta o evento) | `f421e418a` |
| 52 | 15/10 20:00 | H: CP2b (`main.py` diviso in `app_lifespan`, `lifecycle`, `middleware`, `static_site`, `database_bootstrap`; passi nominati; uno spegnimento che fallisce non salta gli altri); `main.py` scongelato | `4fb017a9a` |
| 53 | 15/10 20:24 | B8: token del pannello per i backup (`LIBREFOLIO_BACKUP_DOWNLOAD_TOKEN`, `/backup/panel/jobs`, anche a istanza bloccata) | `56d3d3182` |
| 54 | 15/10 20:33 | A6b: scheda Users (110), eliminazione con anteprima, sonda dell'indirizzo dal browser, A-12; scatto `settings/users` | `09ca36b9d` |
| 55 | 15/10 20:41 | J: CP-4c (`financial_math/portfolio/period.py`: P&L di periodo; costi unitari nella casa; valori identici) | `a180ea0b7` |
| 55b | 15/10 20:56 | B: scatto `settings/backup-ready` (rivisto da G), da solo prima di B2a | `ab2ddf86e` |
| 56 | 15/10 21:04 | X: CP10, impostazioni dei plugin (migrazione 007, segreti cifrati, `/settings/plugins`, confine unico per famiglia, mascheramento), X-R6 | `9fb7fe6c9` |
| 57 | 15/10 21:24 | Y8: correzioni ai grafici (I-01, I-03, O-16, 47-1 etichette sull'asse zoomato, 48-1 pulsanti); CHANGELOG scritto da Y | `160562b56` |
| 58 | 15/10 21:28 | Z6b parte 2: watchdog e scadenza dei passi nel lifespan, processi figli chiusi; spegnimento entro 8 s (decisione 35) | `967094d81` |
| 59 | 15/10 21:31 | E3 + E3s: link nelle email solo da `LIBREFOLIO_PUBLIC_URL`, `POST /email/links`, «password dimenticata» (spenta fino ad A6e, revisione di sicurezza), controllo `email.links` | `8f908623b` |
| 60 | 15/10 21:36 | Z: correzione della E2E del flash dal vivo (attesa del primo poll e orologio in pausa), solo test | `93292909d` |
| 61 | 15/10 22:13 | E3p: sonda dei link della scheda Email dal browser dell'admin (decisione 45) | `e54ae96bb` |
| 62 | 15/10 22:14 | A: G-15 (la barra delle schede di Settings scorre invece di tagliare; `TabBar` `scrollable`) | `369204ab5` |
| 63 | 15/10 22:36 | W: F36 (report BRIM senza broker solo al caricatore e all'admin; `/parse` chiede EDITOR sul broker della richiesta; `file_id` non UUID → 404; `can_delete` nella lista; decisione 36, W-B3/W-B4) | `434af2925` |
| 64 | 15/10 22:38 | J: CP-4d (risolutore MWRR verificato, Newton + Brent, `None` senza radice; via il ritentativo a freddo e `MWRR_SERIES_UNRELIABLE`; golden native-cash rigenerato solo sui `mwrr_*`) | `40f44f364` |
| 65 | 15/10 22:47 | Z: Z2a (presenza dell'utente e richieste in corso, `ActivityMiddleware` in testa a `MIDDLEWARE_STACK`; D-S1; nessun effetto visibile) | `8b2d4782d` |
| 66 | 15/10 23:02 | H: CP-U1 (decisione 36: scopo dei file caricati comune/personale, regola legacy alla lettura, personale altrui → 404, `PATCH` scopo, miniature `private`; I/O su disco fuori dal loop) | `6a3a2a1cc` |
| 67 | 15/10 23:26 | X: X-RL, X1–X8 (pausa dei fornitori su «troppe richieste» sopra Z7a: eccezioni `RATE_LIMITED`, confini `call_provider`/`call_fx_provider`, Yahoo senza ritentativi, `error_code`/`retry_after` nei risultati, la sonda mostra fino a quando; decisione 34) | `da21c48c4` |
| 68 | 15/10 23:38 | E: E5a (verifica dell'email, parti solo di E: servizio `verification.py`, `POST /email/verification/confirm` e `/resend`, pagina `/verify-email`; inerte fino a E5b; decisione 44) | `e9a993e00` |
| 69 | 15/10 23:45 | W: W-B20 (un savepoint per broker nella cancellazione multipla; `begin_writes` in `db/session.py`) | `23ff56b95` |
| 70 | 16/10 00:42 | J: CP-16 (decisione 47 nei lotti: la rettifica in uscita con costo chiude i lotti al costo medio della riga, valore ceduto nei proventi; J-9; etichetta «Valore ceduto al costo») | `240675ad1` |
| 71 | 16/10 00:55 | X: CP11a (impostazioni dei plugin, backend: `configured` nel catalogo, `providers_not_configured` e `error_code` nello stream di ricerca, preferenze justETF/Borsa D-X14, `PROVIDER_ERROR` mascherato; CHANGELOG con CP11b) | `a6453571d` |
| 72 | 16/10 01:38 | W: lotto di doc (A-14 regola dell'ultimo OWNER, W-B10 rotte di accesso, W-B33; tolte due chiavi i18n inutilizzate di W-B27) | `6fa3f8936` |
| 73 | 16/10 01:44 | Z: Z3 (`run_due_jobs` con lock e `busy("scheduler")`, recupero al ritorno, slot perso fino a 7 giorni, istanza bloccata senza job; Z-6 chiusa) | `c0dbc98a0` |
| 74 | 16/10 01:46 | J: CP-15 (totali di controllo del registro per il backup: `financial_math/ledger_totals.py`, versione 1, somme esatte; nessun chiamante ancora) | `fd41a0996` |
| 75 | 16/10 01:48 | E: E4a (parti solo di E: «Invia per email», modulo «password dimenticata», avviso al vecchio indirizzo; non raggiungibili fino a E4b) | `73a68d95f` |
| 76 | 16/10 01:53 | Y: Y7 (tabelle su telefono: colonne di selezione e azioni scorrono sotto 768 px, D-Y17; ridimensionamento con Pointer Events e `min-width`, D-Y18/C-62; galleria mobile 11/11 contro G-13, 174 scatti cambiati, tutti di Y7) | `a613a217c` |
| 77 | 16/10 01:57 | Z: Z4 (`POST /system/wake-sync` con `LIBREFOLIO_WAKE_TOKEN`, 409 `wake_in_progress`, risposta in streaming, ammessa su istanza bloccata; pagina admin «Sleep and Wake»; security-review pulita) | `2980e2a00` |
| 78 | 16/10 02:08 | W: W-B31 + W-B36 (le regole 5–12 leggono `TX_TYPE_METADATA`; tolto `EVENT_COMPATIBLE_TYPES`; i 4 casi di P6 restano eccezioni esplicite; messaggi invariati) | `4e69b5271` |
| 79 | 16/10 02:31 | H: CP-U2 (decisione 36, frontend: colonna Visibilità, condividi/rendi personale, «elimina» solo con `can_delete`, il selettore condivide un'immagine personale scelta; pagina utente dei file aggiornata) | `2d1eee33a` |
| 80 | 16/10 02:45 | A: A6d (nuove istanze su invito, primo account aperto, migrazione 008; impostazioni globali con sessione) + A6e (cambio email con password attuale, chiude le altre sessioni, `email_verified_at` a NULL) | `19dd8a96d` |
| 81 | 16/10 02:52 | Y: Y4b (FE2b, il frontend del rischio in `lib/features/risk/`: 103 rinomine, import, runner, doc, devWiki, baseline dei colori; E2E `risk` 38 e `risk-lab` 44) | `08efa5ac3` |
| 82 | 16/10 02:55 | B: B2 (controllo di un archivio su una copia: `staging.py`, `restore_jobs.py`, `/backup/restore/*`, CLI `restore --dry-run`, `backup_in_progress()`, limite di caricamento; decisioni 40, 42, 43; all-backend 18 359/0) | `5441b96ed` |
| 83 | 16/10 03:00 | E: E-5 (guardia dei testi OpenAPI che il generatore incolla grezzi; regola 4 dei contratti API; 52 componenti latenti, nessuno rotto) | `01598f9ad` |
| 84 | 16/10 03:05 | X: CP11b (scheda Impostazioni › Plugin, «Configura» dal pannello del fornitore e dalla ricerca, legenda 👑, sottosistema i18n `pluginSettings`; E2E 104) | `0241a87e8` |
