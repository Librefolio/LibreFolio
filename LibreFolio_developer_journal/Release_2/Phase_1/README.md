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
| 85 | 16/10 03:07 | Z: Z7b (lo scheduler rimanda gli elementi `RATE_LIMITED` fino a `retry_at` e aspetta 1, 2, 4… minuti dopo un errore; campi nuovi nello stato e nella risposta del risveglio) | `e5e2595e7` |
| 86 | 16/10 03:52 | H: CP7b-1 (F15 sempre attivo: `nosniff` e `Referrer-Policy` su ogni risposta; F28: solo `_app/immutable/` immutabile; tipi MIME registrati dall'app; all-backend 17 084/0) | `1f4c5aeca` |
| 87 | 16/10 03:55 | J: CP-6 (decisione 28: giorni «dirty» anche per i soli cambi dei titoli, per le quotazioni e per il primo giorno di un prezzo vecchio; `native_cash.change_days` unica; golden W1 rigenerato; J-20; B11 chiusa) | `628e3e49e` |
| 88 | 16/10 04:24 | Z: Z2b (sospensione dopo l'inattività su Fly: `idle_monitor`, `FlySuspender`, attesa crescente fino a 10 min; spento di default) | `812ca49cc` |
| 89 | 16/10 04:42 | W: coda della notte per cherry-pick, senza la 47 (W-B37 cancellazione multipla dei report che salta i file bloccati; C-34 `escapeHtml` nel Bulk; W-B35 docstring dell'accesso; W-B12 MULTI-008d pulisce i suoi broker) | `8129f8176` |
| 90 | 16/10 04:48 | A: A6c (decisione 37: regole della password in `password_policy.py`, classi Unicode, `PASSWORD_TOO_WEAK` su register/change/reset e CLI, `accounts.password_rules`; all-backend 0 rossi, E2E 129) | `3b3f6a1f0` |
| 91 | 16/10 04:49 | X: CP11c (mascheramento N15 e campo personale N16, sonda senza URL col segreto, E2E `front-utility plugin-settings` 5/5, pagina `user/settings/plugins`, scatto `settings/plugins`) + escape del tooltip della sonda (ultimo LOW della revisione CP10–CP11) | `2f1d77a23` |
| 92 | 16/10 04:52 | H: CP7b-2 (`PROFILE_DEFAULTS` del profilo gestito, `LIBREFOLIO_FRAME_PROTECTION` e `LIBREFOLIO_CSP_REPORT_ONLY`; all-backend 17 792/0) | `d8549c69a` |
| 93 | 16/10 04:56 | Z: cura del rosso `services config-package` (1/693 da Z2b): `fly_machine_identity()` in `config/sleep_wake.py`, `suspend.py` senza `os.environ`; trovato da H | `3648a6155` |
| 94 | 16/10 06:47 | X: X-R12 (eventi del fornitore datati oggi arrivano lo stesso giorno) + X-R13 (emoji morta dei settori nella pagina asset, primo pezzo di FE5c) | `92a0d4daf` |
| 95 | 16/10 06:47 | W per cherry-pick: W-B41 (test multiutente puliscono i broker), W-B29 (E2E eventi con asset propri), W-B38 (messaggi delle regole impacchettate col tipo) | `5eb8e4103` `09e7d5a4e` `b89ddbba9` |
| 96 | 16/10 06:54 | X per cherry-pick: K-16 (ETC/ETN di Borsa Italiana come `ETF_COMMODITY`) + O-9 (etichette dei parametri di justETF e css_scraper in 4 lingue) | `bfc0db8aa` |
| 97 | 16/10 07:09 | Z: Z7c-2 (pannello dello scheduler: elementi rinviati ⏸, `retry_at`, riga di stato del nuovo tentativo; api scheduler 16, component-unit 4006) | `0dfc7cbbe` |
| 98 | 16/10 07:27 | W per cherry-pick: W-B39 (split/promozione rifiutati con toast d'errore e i problemi tradotti; E2E `tx-split-refusal` 2/2) + W-B42 (scenari 3–4 di `asset-event-delete` con dati propri, 4/4) | `c881237a9` `9df17ef20` |
| 99 | 16/10 07:43 | W per cherry-pick: W-B44 (test id unici in `PromoteMergeModal`; Vitest 4/4) | `df6e2df10` |
| 100 | 16/10 08:17 | J: CP-10a (decisione 29: un solo Rolling Return in giorni di calendario, `price_return` in `financial_math/returns.py`, impostazioni dei grafici v3, J-13 finestre in osservazioni; C-71 chiusa; asset E2E 34/34, all-backend 17 204/0, mirate sulla revisione unita) | `82e9c5305` |
| 101 | 16/10 08:17 | W per cherry-pick: W-B32 (i report senza broker non compaiono più sotto ogni broker; `api brim` 118/118; dentro la decisione 36, da rivedere) | `84d24ed03` |
| 102 | 16/10 08:24 | W per cherry-pick: W-B45 (T13 di `transactions-modals` con il budget di 60 s dei vicini) | `72ac088fc` |
| 103 | 16/10 08:29 | E: E5b (verifica email alla registrazione, limiti 3/h per casella e 10/h per rete, revisione di sicurezza, merge con A6c; E2E 5/5, mirate sulla revisione unita) | `dbe232723` |
| 104 | 16/10 08:33 | Y: Y3 (FE6b dashboard in `features/`), Y9 (font delle bandiere e testo sicuro nei grafici), Y10 (decisione 49, liquidità negativa nell'allocazione), Y5 (broker e lotti in `features/brokers`), Y6 (file in `features/files`), C-34 (guardia), cura dell'attesa in `brokers-detail.spec.ts`; E2E unica 223/224 + 37/37, leggere sulla revisione unita | `4447814ed` |
| 105 | 16/10 10:39 | Z: Z7c-1 (attesa crescente dei prezzi dal vivo dopo errori e pause dei fornitori; E2E `live-pause` 8/8, flash 4/4) + Z-9 (doc admin delle pause dei fornitori) | `dd4a97e01` |
| 106 | 16/10 10:49 | W per cherry-pick: W-B17 (una FX_CONVERSION su due broker è rifiutata, `pairBrokerMismatch`) | `4647c4af4` |
| 107 | 16/10 11:17 | J: CP-7a (decisione 26: ogni gamba del lotto convertita alla sua data, via il ripiego di CP-16, lotti short corretti, T-B6, J-14; all-backend 17 898/1 rosso estraneo — timeout del fornitore in `search-to-prices`, ripassato 3/3) — T-B5, T-B6 chiuse | `4f9e94420` |
| 108 | 16/10 11:18 | W per cherry-pick: docstring di `list_accesses` (P4 del developer: la lista degli accessi resta aperta) | `02f08057f` |
| 109 | 16/10 12:05 | W per cherry-pick: W-B43 (gli spec dell'editor dei dati e dell'import CSV dei cambi verificano invece di sondare; `asset-data-editor` 26/26, `fx-csv-import` 21/22 con il test 19 scaduto a carico ~140 e ripassato da solo in 3 s) | `a59593570` |
| 110 | 16/10 12:47 | H: note di X, card del backup nella pagina di blocco, H-17, b-doc-notes, lotto 2, H-3 B (H-15 incluso); all-backend 18 266/5 timeout estranei (triage: ricerca → X, parse BRIM → W), combinato verde (front check, `InstanceBlockedPage` 36, `api instance-block` 62, `api system` 118) | `0ecc5ed27` |
| 111 | 16/10 12:48 | W per cherry-pick: W-B30 (P5, lettura B: svuotare un costo manuale richiesto è rifiutato, mai tenuto in silenzio; `null` esplicito toglie il costo solo dove il tipo lo ammette) | `54880598b` |
| 112 | 16/10 14:25 | W per cherry-pick: W-B36b (P6: in aggiornamento valgono le regole dei tipi sul campo che cambia; `cashNonzero`; 0 righe fuori regola sui dati demo) + seguito W-B30 (test come guardie); gate su dev: `schemas transactions` 106, `services transaction` 96, `cost-basis-rule` 73, `i18n check`, mkdocs strict. Prima, `ed500643f`: ancora mancante in `wac.md` dopo il treno 111 | `277d26cd0`, `b51bb3663` |
| 113 | 16/10 15:05 | E per cherry-pick: il finto SMTP parla `SMTPUTF8` (fixture di test, sblocca i test di P18) | `7d51c21af` |
| 114 | 16/10 15:05 | H: P17, `LIBREFOLIO_CLIENT_IP_HEADER` (indirizzo del visitatore dietro un proxy fidato; il cloud mette `Fly-Client-IP`), i tre limiti per client su `client_address()` | `b1df87bd4` |
| 115 | 16/10 15:06 | Z: Z5 (avviso «Aggiornamento prezzi…» durante un recupero, `GET /system/price-refresh`) + Z-13 (Dashboard e broker si ricaricano a fine recupero); combinato verde da Z su `41b44fb64` | `12cd3c2e0` |
| 116 | 16/10 15:20 | Z: Z-13b (la ricarica dopo un recupero non tocca `refreshVersion`, così Y11 non gira) | `26dda1a26` |
| 117 | 16/10 16:15 | H: TC-16 (attese del visore dei file robuste sotto carico; `component-unit` 4041 ×2 a carico 66–106) | `65fc63e7e` |
| 118 | 16/10 16:28 | Z: Z-12 (commento di `scheduler_state.json` in 4 lingue) + Z-5 (lo storico riparte dall'ultima data salvata, fino a 365 giorni); gate su dev: scheduler-jobs 73, catchup 73, price-refresh 44, mkdocs strict | `ebe9eb346` |
| 119 | 16/10 16:50 | X: FE5c (pagina asset 3603 → 2757 righe; galleria di G identica entro il rumore), F21, CP13 (`LIBREFOLIO_SUPPORT_URL`, regola unica degli URL, livello premium), X-R21, correzioni del prezzo dal vivo, icone in Impostazioni › Plugin; combinato verde da X (core 6783, component 4079); CHANGELOG risolto dal coordinatore | `a44951cf5` |
| 120 | 16/10 16:56 | Z: Z-17 + prova su Fly (`admin/sleep_wake.en.md#check-it-works`) + chiusura del piano 06 (foglio delle 43 decisioni da rivedere) | `4f0a5d323` |
| 121 | 16/10 17:08 | J: J-17 (P2: una rettifica non è mai un prezzo; senza alcun prezzo si valuta al costo, stima dichiarata); all-backend su `54c5f8f95` 6/7, 2 rossi API = avvio a freddo del pool BRIM (J-30 a W) | `94321d7db` |
| 122 | 16/10 18:16 | X: X-R27 + X-R28 (una sola chiave di cache per le risposte dei fornitori; i piani programmati e gli asset con stesso URL/ISIN non si scambiano più il prezzo dal vivo; decisione del developer: solo cura + 🐛, niente riparazione); gate del coordinatore sul tip verde (24 passi) | `ccfabfd6d` |
| 123 | 16/10 18:32 | W: C-97a (issue #43: quantità a 10 decimali, prezzi e costo per unità a 12, oltre il limite rifiutato; somme in Python; D5/D6 = N51/N52), cherry-pick di `5c4426e75` | `bab52635d` |
| 124 | 16/10 18:41 | H: H-12 (l'output del backend di test condiviso va in `shared-backend.log`; un avvio fallito ne mostra la coda); all-backend 18 487/0 | `7ac8b17de` |
| 125 | 16/10 18:41 | J: CP-13a (P19: il guadagno che recupera un drawdown calcolato in `financial_math`, campo `maximum_drawdown_trough_to_peak_ratio`; perdita totale = null con avviso) | `0452e592c` |
| 126 | 16/10 19:26 | H: H-21 (= W-B54: un'azione `api` da sola rifà il seed se il DB della corsia non ha gli utenti di fixture); gate su dev: reseed una volta, poi no | `946e02d55` |
| 127 | 16/10 19:29 | X: O-20 (una sola sincronizzazione dei prezzi alla creazione di un asset, `onsynced` della modale; i piani programmati creati da modulo o wizard hanno subito lo storico) | `967ddbda4` |
| 128 | 16/10 19:42 | MF: ondata 1b (M, G1 somme del PAC in Python; N + F2 AI Export v2 di `broker.cost_efficiency` e `portfolio.income_timeline`; K2 + N54 una regola MWRR per card e linea; O2 Yield on Cost negativo); all-backend 6/7, 2 rossi External di Crédit Agricole a W (C-97a) | `8d244d1c6` |
| 129 | 16/10 19:48 | W: correzione di C-97a (D6): `round_computed_value` quantizza solo oltre la scala (i valori calcolati dai plugin non escono più con 12 zeri); gate su dev: real-decimal 96, brim-providers 736 | `0c3275057` |
| 130 | 16/10 19:59 | Y: Y12a, Y-12, Y11 passi 1–4b (un solo «Aggiorna» per pagina che aspetta `pageBusy`; `join` per i pannelli, N55); E2E combinata 121/121 | `0c79932a7` |
| 131 | 16/10 20:06 | A: P18 (email uniche senza distinzione di maiuscole, revisione 009), A-24, A-27 (link di reset revocati al cambio di email o password), A7a (admin iniziale da variabili; la pagina `/setup` arriva con A7b), A7c, A-22; all-backend 20 767/0, combinato verde | `68355911f` |
| 132 | 16/10 20:20 | A: A-25 (Impostazioni › Profilo non chiede la password per un cambio di sole maiuscole) | `b7e50b359` |
| 133 | 16/10 20:33 | W: W-B53 (riscaldamento facoltativo del pool di analisi BRIM, `LIBREFOLIO_BRIM_PREWARM`, spento in produzione e acceso in test; N56), cherry-pick con 3 risoluzioni di W | `618d7208e` |
| 134 | 16/10 20:58 | J: J-24 (P21: un ADJUSTMENT in uscita con prezzo esce al valore dichiarato al cambio del giorno; differenza dal costo medio realizzata); all-backend su J-24 + MF 1b 6/7 (solo i 2 rossi CA già curati) | `31a59bdb1` |
| 135 | 16/10 20:59 | MF: lotto C (pesi e HHI in `financial_math/weights.py`; peso su NAV «—» con patrimonio ≤ 0; D-MF7) | `0eb85aa9b` |
| 136 | 16/10 21:00 | MF: I2 (un solo lettore dei frazionamenti per i ricalcoli del costo medio, `split_linked_ids`; nessun numero cambia) | `3741b95b0` |
| — | 16/10 21:05 | Z: journal Z-18, Z-19 (N58) | `27994759a` |
| 137 | 16/10 21:20 | H: H-22 (tolte le funzioni di `client_address` usate solo dai test; N58: nessun record scritto da LibreFolio contiene l'indirizzo di un client) | `fa16ce787` |
| 138 | 16/10 21:30 | X: C-66 (l'avviso nella finestra di sincronizzazione quando l'intervallo ha già dati, modifiche manuali comprese); E2E combinata con Y11: asset-list 30, page-busy 12 | `4b2e0df80` |
| 139 | 16/10 21:40 | E: E4b (password dimenticata per email, invio dei link per email, avviso di cambio email), E6, E6.8, E4c-H, E6.9 (revisione di sicurezza: nessuna vulnerabilità), E4c (`same_email`); all-backend 21 506/0; `log.md` della devWiki per unione | `56759b2c8` |
| 140 | 16/10 21:42 | Y: Y12b (P19: la riga del recupero di L1 legge il campo del backend) + spec dei tooltip di L3 resa robusta; L4 lento sotto carico → Y-21 | `23f71e739` |
| 141 | 16/10 21:36 | B: B3 ripristino (CLI e scheda Backup, B5b), P7 (mai applicato a istanza bloccata), B5c biglietto dell'esito (N53), B-17, B-13 totali di controllo, B6a-bis guida, ordine d'avvio N57; all-backend 7/7 | `0cd910a7e` |
| 142 | 16/10 21:55 | W: decisione 47 (la metà che cede va al costo medio; gambe sole convertite all'avvio) provata con J-24; all-backend 7/7 su `6162dfc0f` | `ea72346b7` |
| 143 | 16/10 22:08 | H: docstring di `instance_block.py` (rotte pubbliche fuori lista, pagine dei link) | `3f561e204` |
| 144 | 16/10 22:10 | Y: Y-14 («Aggiorna» della lista dei broker ricalcola le schede) | `47ed8ebc4` |
| — | 16/10 22:15 | E: E-4 (nome non deprecato del 422 in `settings.py`) | `07700355f` |
| 145 | 16/10 22:25 | J: CP-7b (riferimento dei lotti aperti da un ADJUSTMENT dalla serie della casa, al cambio del giorno d'apertura; giorni al costo come il Dashboard; chiude J-28) | `48da9bf3c` |
| 146 | 16/10 22:24 | Z: lotto B, Z-18 (la ricarica in sottofondo non svuota la pagina; `pageBusy`) | `30483ec38` |
| 147 | 16/10 22:29 | X: C-90 (nota sull'ambito della sonda) | `cd617824e` |
| 148 | 16/10 22:32 | Y: Y-19 (la durata della peggior caduta legge la fonte del backend) | `90b84ac9c` |
| 149 | 16/10 22:45 | Y: Y-20 (riferimenti del laboratorio del rischio) | `b89985a8b` |
| 150 | 16/10 23:03 | E: E-10 (la verifica dell'email su istanza bloccata) | `476da8470` |
| 151 | 16/10 23:05 | B: H-17 e doc del ripristino | `b2c488a34` |
| 152 | 16/10 23:12 | H: H-23 (l'azione `pure` singola tiene il DB della corsia) | `9eb934218` |
| 153 | 16/10 23:15 | MF: MF-B (le schede dei broker leggono la fetta del motore) + MF-H (uno split non azzera la finestra di detenzione) | `bcc644491`, `a621bf89e` |
| 154 | 16/10 23:24 | W: FE8b (il frontend delle transazioni in `features/`; congelamento annunciato e tolto) | `31335fe26` |
| 155 | 16/10 23:28 | J: J-27 (`ledger_totals` legge solo decimali semplici) + ponte della sonda AI Export col plugin Svelte; J-26 chiusa | `e221a0544` |
| 156 | 16/10 23:36 | X: P20 sotto-lotto 1 (indirizzo di supporto `mailto:`); conflitto su `hosting_providers.en.md` risolto unendo i due punti | `db506eb21` |
| 157 | 16/10 23:41 | H: H-24 (file nascosti e di test non fanno ricostruire il frontend) | `4bf824362` |
| 158 | 16/10 23:46 | W: C-97a seguito, il costo Auto non passa dal controllo dei decimali (trovato dagli E2E di FE8b) | `c91bd41b2` |
| 159 | 16/10 23:51 | Z: lotto A, Z-3 (giorno dell'utente), Z-8 (niente poll senza fornitore), Z-19 (N58) | `0f55265a1`, `ac9671fd3` |
| — | 16/10 23:24–23:46 | Colori: W FE8b in tandem; L audit fuori metrica `70e798a4e`; G `backup ready` `778156983`; T tabelle e 23 ruoli mancanti `9016f47c3` | — |
| 160 | 16/10 23:55 | Z: wiki-file `utc-today-vs-user-calendar` (Z-3), Z-20 = disaccoppiare `zodios-client` da `instanceNotices`, vecchia Z-20 → Z-21 | `91d89bce6` |
| 161 | 17/10 00:00 | E: revisioni di sicurezza R13-SEC e R13-SEC2 nel journal (W-B58 MEDIUM, W-B59, X-R35/36, A-32..35, B-19) | `6cadaf427` |
| 162 | 17/10 00:05 | Y: Y-21 (scadenze reali dei test del rischio, blocco «functional integration» a 90 s), Y-5, sezione `pageBusy` | `149157025` |
| 163 | 17/10 00:10 | H: H-25 (il passaggio parallelo solo per la categoria intera) | `9839ea00b` |
| 164 | 17/10 00:15 | A: A7b (pagina `/setup`, avviso registrazione aperta, admin in attesa, A-13) + CHANGELOG A7a/A7b | `3e5336a0a`, `0e83e1cd5` |
| 165 | 17/10 00:20 | X: F21 + P20 sotto-lotto 3 (fonti premium in testa, «Non lo trovi? Faccelo sapere») | `4469f37b6` |
| 166 | 17/10 00:25 | J: CP-9a (servizio del rischio diviso per tema, T-R1 metà rischio); `devWiki/log.md` per unione; TODO_FUTURI allineato | `c4eeaef14`, `67e795edb` |
| 167 | 17/10 00:35 | Y: Y-22 (scadenza dell'aiuto L3), Y-23 (mock `onNavigate`, rosso di dev da `ec018afdf`), riferimenti di riga | `d7f3a49c3` |
| 168 | 17/10 00:38 | X: X-R22 (l'avviso del segreto illeggibile dice l'ordine: prima la chiave vecchia) | `618563949` |
| 169 | 17/10 01:06 | MF: MF-P (variazione del giorno e gruppi) e MF-A (tabella Performance dal motore); journal MF | `536501541`, `151488582`, `5c9ad06d7` |
| 170 | 17/10 01:12 | X: X-R37 (link al report in managed, N61) | `908fe6c90` |
| 171 | 17/10 01:23 | X: X-R35 (le impostazioni URL rifiutano user info) | `67668f5ce` |
| 172 | 17/10 01:33 | J: CP-10b (runtime dei segnali in `services/signals`) | `b36e3873f` |
| 173 | 17/10 01:45 | H: H-26, residuo di H-24, H-28 (file nascosti della build) | `40a76bf1a`, `5beecac3d` |
| 174 | 17/10 01:50 | E: E-9 (alias delle caselle, nessun testo di estranei) | `49c07a95a`, `3a5ff5194` |
| 175 | 17/10 01:57 | Z: Z-14 (cache dei prezzi dopo il recupero); W: W-B58 (limite dei decimali), W-B59 (precarico BRIM) | `2765773f5`, `6e02e56ec`, `4e9d1815f` |
| 176 | 17/10 02:02 | Z: Z-21 (aiuti solo-test rimossi) | `ffd58ffbd` |
| 177 | 17/10 02:04 | MF: MF-E1 (riepilogo dei lotti in casa, riepilogo FIFO v3); X: O-8 (messaggi del data editor) | `e43dfae68`, `f32a04f46`, `b1b4960c4` |
| 178 | 17/10 02:40 | H: H-27 (tipi dei default di profilo) | `bfdc1f72c` |
| 179 | 17/10 02:50 | E: E-11 (reinvio con istanza bloccata) | `bca4bd6d3`, `2818924b7` |
| 180 | 17/10 03:07 | E: journal R13-SEC4 ed E-12 | `110125350`, `dfb1fcafd` |
| 181 | 17/10 03:09 | H: H-29, H-30 (file nascosti) | `1b11869f7`, `8ef48dedb` |
| 182 | 17/10 03:11 | A: A7b-2 (ritiro del link di setup, 422 senza input); ⚠️ marcatori in `overview.md` corretti | `90219770c`, `81b8db4e1`, `28059249a` |
| 183 | 17/10 03:17 | J: CP-10c (taglio del servizio dei segnali) | `69e1c58e9` |
| 184 | 17/10 03:28 | B: B4 (backup sicuri `.lfbk`) | `339a59142`, `0a45e45de` |
| 185 | 17/10 03:38 | Z: Z-20 (client senza moduli runes) | `3f654c4da` |
| 186 | 17/10 03:40 | MF: MF-P4b (frazioni dei periodi), MF-J1 (un solo replay) | `d93de2899` |
| 187 | 17/10 03:58 | E: journal R13-SEC5 | `7d3012e3b` |
| 188 | 17/10 04:05 | Z: Z-22 (listener HMR di instanceBlock) | `22d46da6e` |
| 189 | 17/10 04:17 | H: H-32 (float delle richieste finiti) | `ec6aa2007` |
| 190 | 17/10 04:45 | H: H-33 (log della validazione delle risposte) | `5bba93280` |
| 191 | 17/10 04:48 | Y: Y11 lotto assets (pageBusy sulle pagine asset) | `d32d0f3d9` |
| 192 | 17/10 04:50 | B: B4b (residui dopo un crash, correzioni ai backup) | `c7dd3934a`, `8b15a6c6c` |
| 193 | 17/10 04:51 | H: wiki-file della notte; ⚠️ marcatori in `devWiki/index.md` corretti | `1937e6cf4`, `333cead4d` |
| 194 | 17/10 04:54 | X: X-R24/25, X-R38, X-R40/W-B62, X-R50 | `fd6886bb0` |
| 195 | 17/10 04:56 | Z: Z-10 (spegnimento del server di sviluppo) | `a38d6bdfe`, `75a1107a7` |
| 196 | 17/10 05:01 | J: CP-14a (casa degli interessi, P-10, V-4) | `03101ddad`, `39dd2ef5c` |
| 197 | 17/10 05:08 | X: X-R51 (quotazione live rifiutata, nominata) | `b3cae6e0e` |
| 198 | 17/10 05:11 | MF: MF-W56 (arrotondamento WAC), MF-J2 (il trasferimento tiene i rendimenti); conflitto del runner risolto a mano | `04a5088ff`, `611b07074` |
| 199 | 17/10 05:13 | E: journal R13-SEC6; W: C-97b (input decimale) | `3f664ae37`, `b2462042d`, `b214c8200` |
| 200 | 17/10 05:16 | MF: MF-D1 (rendimenti in casa), MF-D2 (drawdown con perdita totale, v2) | `aca75c7ca`, `1c37ad0f0` |
| 201 | 17/10 05:25 | X: X-R52 (un giorno BCE non numerico salta solo quel giorno) | `56d13a448` |
| 202 | 17/10 05:27 | Y: R17/W8/P4 (cifre della Dashboard dal backend) | `1565b6bbb`, `a3662b3ef` |
| 203 | 17/10 05:32 | Z: journal, piano Z-14b/Z-15 | `1a937b93e` |
| 204 | 17/10 05:38 | Z: Z-16 (albero di `admin/filesystem` in it/fr/es) | `737972ef5` |
| 205 | 17/10 05:41 | J: CP-14b (ACT/ACT ISDA, liquidazione, soglia del righello); backlog T-D9, T-U8, J-44 | `4111239a7`, `252835dce` |
| 206 | 17/10 05:48 | B: B-28 (il ripristino rifiuta oggetti estranei nello schema) | `01f36e79d`, `1c2bac918` |
| 207 | 17/10 05:56 | E: journal, rossi di E-13, R13-SEC7 | `d5126c19a` |
| 208 | 17/10 05:57 | MF: MF-P2 (endpoint delle variazioni a periodo fisso) | `aa4370905` |
| 209 | 17/10 06:08 | Y: Y-2 (linea settimanale), Y-16 (test delle candele); B: B-29 (totali illeggibili della copia) | `14072c03d`, `006773c99`, `abf8391fb` |
| 210 | 17/10 06:16 | H: H-36 (proxy locale non fidato, N70) | `d107b6f26` |
| 211 | 17/10 06:31 | Z: Z-11 (lock dei job fra i worker, N71); B: B-16 (il riavvio che non avviene lo dice) | `c5e3c199d`, `3896cb6b3`, `47405701f` |
| 212 | 17/10 06:38 | Z-11 runner descriptions | `3d13fbcdc` |
| 213 | 17/10 06:40 | W-B60 amounts and event values read exactly | `484c71afb` |
| 214 | 17/10 06:47 | H-37 missing profile entry fails closed | `b37e926af` |
| 215 | 17/10 06:48 | MF R13-SEC7-2 SI bounds, closed-form late interest | `7198d8028` |
| 216 | 17/10 06:56 | X-R47 split ratio at write, X-R47b P-10 fails closed | `952c68cd5` |
| 217 | 17/10 07:07 | H Z-24 scheduler lock guard, H-39 review rule | `36a487e84` |
| 218 | 17/10 07:07 | J-43 share mismatch notice, R13-SEC7-1 bounded ranges | `09cb9231a` |
| 219 | 17/10 07:10 | MF-SI1 first sync from min, aligned late interest | `16f8c74ed` |
| 220 | 17/10 07:21 | A8a login limit + security checks, N70 untrusted proxy, E-13 | `440616c61` |
| 221 | 17/10 07:23 | G banner comments | `fd536787f` |
| 222 | 17/10 07:30 | E journal, N70 review, E-14 | `e985a4f8a` |
| 223 | 17/10 07:31 | X-R43 plugin settings integers past 2^53 | `3e7948446` |
| 224 | 17/10 07:37 | B-9 backup startup checks | `997dc7ecf` |
| 225 | 17/10 07:39 | Y-8 arrows re-aimed on zoom settle | `823a2f6bc` |
| 226 | 17/10 07:42 | J F5 P-10 message, J-44 tooltip delta | `b6b615c3d` |
| 227 | 17/10 07:43 | H-34 non-finite numbers in free JSON | `75bfac237` |
| 228 | 17/10 07:46 | MF-D4 invalid split ratio counts as missing | `c2feaf3e4` |
| 229 | 17/10 07:57 | E-14 limiter evicts fewest live hits | `70dccc16f` |
| 230 | 17/10 08:01 | B-30 full disk at short starts | `af9b7f482` |
| 231 | 17/10 08:15 | H-39 managed frame/CSP checks, docs | `0403b5eb7` |
| 232 | 17/10 08:29 | J-45 engine off the event loop | `15d414a69` |
| 233 | 17/10 08:30 | X-R55 query date range ceiling | `ab7711f04` |
| 234 | 17/10 08:39 | X-R53 delta columns from the server | `78708660f` |
| 235 | 17/10 08:46 | W-B69 auto cost refuses unreadable pool | `c61a2db4d` |
| 236 | 17/10 08:46 | B-31 coded confirm/cancel/restart failures | `997c358f5` |
| 237 | 17/10 08:54 | Y-25 arrow re-aim costs, Y-3, Y-4 | `73443c6db` |
| 238 | 17/10 09:10 | A8b Administration group + Security tab, A-21a usernames | `6e2b2c8b7` |
| 239 | 17/10 09:24 | B-19 decrypt as data dir owner | `e96158e9b` |
| 240 | 17/10 09:25 | H-35 config audit after A8a and B-9 | `d28a6d7df` |
| 241 | 17/10 09:43 | X-R48 wipe refuses costless split adjustments | `2ea54ff76` |
| 242 | 17/10 09:53 | G point-33 run | `8a9e8c6d6` |
| 243 | 17/10 09:56 | E-8 invitation language, Administration paths | `2aab994b8` |
| 244 | 17/10 10:02 | W SEC7-3 input bounds, H-41, event-store fix | `e609082ab` |
| 245 | 17/10 10:02 | H-19 address probe 503 | `9b23bdbfe` |
| 246 | 17/10 10:04 | J-10 scope-edge transfer reading, E2 params | `ba612882a` |
| 247 | 17/10 10:05 | MF-SEC8-2 replay floor 1900 | `e119c71bc` |
| 248 | 17/10 10:20 | Y-27 DataTable keeps absent column prefs | `542c0e8b5` |
| 249 | 17/10 10:28 | B-32 refused cancel, unreadable restore state | `7af21a5c1` |
| 250 | 17/10 10:28 | Z-25 bulk caps on price and FX queries | `d0bc7a547` |
| 251 | 17/10 10:29 | MF-P2b period-changes bounds | `c9b1162d4` |
| 252 | 17/10 10:41 | E-8.5 email Vitest cure | `b49a2a716` |
| 253 | 17/10 10:43 | J-47 transfers in transit at date_to, P-10 docs | `647efcc28` |
| 254 | 17/10 10:45 | X-R44 test-only providers withheld outside test mode | `5a8c64c5c` |
| 255 | 17/10 10:59 | Y V11 + P5 lots values and declared aggregates | `d4ecfb692` |
| 256 | 17/10 11:00 | B-18 restore --instance-key-file, B-20 | `5c4d7456a` |
| 257 | 17/10 11:03 | X Y-28 C-66 test past period, X-R57 | `8aafffad8` |
| 258 | 17/10 11:05 | Z-26 scheduler lock wait bound, FX at-least | `8c362c1f3` |
| 259 | 17/10 11:10 | A9 legal notice and managed profile | `ba8f3b06e` |
| 260 | 17/10 11:14 | W-B71 date windows at the calendar edge | `1431e20df` |
| 261 | 17/10 11:18 | Y-29 gate annualizing flag | `ce2452615` |
| 262 | 17/10 11:22 | W-B69 batch half, N74 shared floor | `eee5dad17` |
| 263 | 17/10 11:28 | E-15 login limit restored per test | `da02ed816` |
| 264 | 17/10 11:36 | H-42 page policy on HTML responses | `3b0af4094` |
| 265 | 17/10 11:45 | J-50 oversized price loads refused with a code | `5bfdbe0af` |
| 266 | 17/10 11:47 | Z-28 lock files refuse symlinks | `2b9786ae5` |
| 267 | 17/10 11:51 | T theme-roles (c) | `c1578a8bf` |
| 268 | 17/10 11:52 | B-18 repair, BZ part 1 records | `279c1bc1c` |
| 269 | 17/10 11:54 | H-46 test mode outside test lanes | `b7dcd3a25` |
| 270 | 17/10 12:02 | A9 fix-forward forgot-password on failed config | `cd52e25fc` |
| 271 | 17/10 12:04 | W-B74 balances refuse unreadable rows | `80cee9c2d` |
| 272 | 17/10 12:14 | E R13-SEC9 review | `c2021cb52` |
| 273 | 17/10 12:24 | E-16 forgot page docs | `ac3c03177` |
| 274 | 17/10 12:25 | X-R49 plan change refuses costless split adjustments | `e710cf552` |
| 275 | 17/10 12:35 | H-45 page policy on XML docs, none on 304 | `d617cb406` |
| 276 | 17/10 12:35 | X TS2769 e2e point type | `9e8f6e8dc` |
| 277 | 17/10 12:42 | B-35 restore unpack cap | `9fafc79b5` |
| 278 | 17/10 12:43 | E-17 e2e tsc clean | `fc979d0b4` |
| 279 | 17/10 12:52 | J-12 backend and AI Export half | `2fa8ec1a8` |
| 280 | 17/10 12:52 | Y J-12 panel half | `46b5fbc0e` |
| 281 | 17/10 12:52 | J-12 log graph line, CHANGELOG | `4e11fabec` |
| 282 | 17/10 13:07 | X-R44c test_only guard | `e41427916` |
| 283 | 17/10 13:08 | B-39 CSV formula escaping | `25d00f192` |
| 284 | 17/10 13:09 | W-B72 refuse stray cost basis N78 | `7bc66c7ca` |
| 285 | 17/10 13:10 | Z-27 web batching, SEC9-2 1M budget | `726d90d72` |
| 286 | 17/10 13:10 | H-49 lane id bounds | `96da36422` |
| 287 | 17/10 13:15 | H B-35 review fixes | `c7f414827` |
| 288 | 17/10 13:17 | A-42/A-43 setup link lifecycle | `7156a24af` |
| 289 | 17/10 13:33 | B-36/B-37 quoted tables, untrusted schema | `d1976bca8` |
| 290 | 17/10 13:42 | X-R60 freshest Δ answer, no needless periods | `cb05410a5` |
| 291 | 17/10 13:45 | MF X-R59 range change, SEC8-2a/2b, SEC9-1, D3, SI2, J45a | `482343eb3` |
| 292 | 17/10 13:55 | J-50b one remedy table | `ef74ff9fc` |
| 293 | 17/10 13:56 | SEC8-1b risk and replay date bounds | `a565e06d0` |
| 294 | 17/10 13:57 | Y-31 E2E J12 locale rule, WAC state (pick) | `8aa8a821e` |
| 295 | 17/10 13:57 | B-38 secret files read as root | `c2a09b960` |
| 296 | 17/10 14:00 | W-B67 Auto cost on its own row N84 | `ac92e6fae` |
| 297 | 17/10 14:02 | A profile helper, A-50, SC-LANE-01 | `d7641f368` |
| 298 | 17/10 14:04 | E journal, MF-SEC9b analysis | `c3dc19fd9` |
| 299 | 17/10 14:10 | B-34 missing instance key message | `202849800` |
| 300 | 17/10 14:12 | X-R62 coded provider removal refusal | `907fb3b97` |
| 301 | 17/10 14:14 | W-B72 html gate fix | `5603a23a7` |
| 302 | 17/10 14:26 | J-33 lots performance at cost | `104333567` |
| 303 | 17/10 14:38 | MF-SEC9a bulk writes chunked | `dd416f5bb` |
| 304 | 17/10 14:39 | X-R64 batched period changes and live poll | `15132b448` |
| 305 | 17/10 14:39 | W-B75 BRIM plain-data params (H) | `9ba7ef9d3` |
| 306 | 17/10 14:41 | A-46/A-47 username rules | `abbe19d37` |
| 307 | 17/10 14:49 | W-B66 pasted exponents | `e820279e1` |
| 308 | 17/10 14:53 | J-51 YoC unseen-broker arrivals | `1becf502f` |
| 309 | 17/10 14:53 | X-R65 stored date bounds (Z) | `c726b9d89` |
| 310 | 17/10 14:53 | E-18 strict ISO currency on writes | `73366626e` |
| 311 | 17/10 14:54 | B-41/B-42 outcome log noise | `d46113236` |
| 312 | 17/10 15:00 | J-36 lots reference-price texts | `e5a975c8b` |
| 313 | 17/10 15:06 | MF-SEC9a rest + MF-SEC9c | `29e30b6cc` |
| 314 | 17/10 15:11 | W-B68 provider event values truncated | `06e9d2c20` |
| 315 | 17/10 15:19 | J-49 range seam check | `e2e883136` |
| 316 | 17/10 15:39 | Z-30 full-history load floored at 1900 | `fb514073b` |
| 317 | 17/10 15:40 | risk Intl guard (J) | `b13ed7944` |
| 318 | 17/10 15:47 | MF-SEC9e exact delete counts, A2 docs | `4507f7507` |
| 319 | 17/10 15:48 | H-51 untrusted schema on every connection | `70ab2fcc6` |
| 320 | 17/10 15:55 | H-47 design and B-37 clause | `13b6cfde1` |
| 321 | 17/10 15:57 | Z-30 follow-up (plural, comments) | `80cef0e43` |
| 322 | 17/10 16:01 | X-R58 bulk refusal toasts | `1bef78be1` |
| 323 | 17/10 16:01 | X-R71 manual upload currency all-or-nothing (B) | `1c7937984` |
| 324 | 17/10 16:04 | H backlog reconciliation | `c3600c247` |
| 325 | 17/10 16:04 | C-97c-1 price and quantity digits | `f1bfa1e31` |
| 326 | 17/10 16:05 | A-51 setup cancel under the lock, A-45 | `180be0ff1` |
| 327 | 17/10 16:15 | E-19a stored currency audit and guards | `c7c6f94f0` |
| 328 | 17/10 16:16 | T-B7 all-null columns named (J) | `36d24e7d2` |
| 329 | 17/10 16:17 | docs(journal): close T-B7 | `81e177e45` |
| 330 | 17/10 16:21 | X-R59 lots A/B range change from backend (Y) | `f317e3a9f` |
| 331 | 17/10 16:28 | MF-J45b single-flight, A4 docs | `a228b9d30` |
| 332 | 17/10 16:41 | B-43/B-44 unreadable copy refused | `fc4d5eab4` |
| — | 17/10 00:05–00:45 | Colori: AF file, media e menu `9d3607eb6`; T `CompactCashCell` `b58108665` | — |
