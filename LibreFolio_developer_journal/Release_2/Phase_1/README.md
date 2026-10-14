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
4. I vincoli del programma colori (cartelle 55 e 56 in `Phase_0`): il §7 del piano.
5. Le voci chiuse dalla 1.3 che nascono in `Phase_0` si marcano ✅ anche lì (decisione del
   developer): le marca il coordinatore a ogni treno.

## Sessioni

Ramo di integrazione: `dev_release2` (condiviso con il programma colori). Corsie: preambolo
`PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py test --test-port <PORTA> --data-dir <DIR> …`.

| Lettera | Sessione | Corsia | Data-dir | Ramo | HEAD | Stato |
|---|---|---|---|---|---|---|
| — | Coordinatore 1.3 (in place) | 6180 | `/tmp/librefolio-r13-main` | `dev_release2` | — | attivo |
| H | H - Piattaforma | 6181 | `/tmp/librefolio-r13-h` | `e-alfy-h-piattaforma` | `459131eb8` | analisi (sessione `8490facf`) |
| A | A - Account e accessi | 6182 | `/tmp/librefolio-r13-a` | `e-alfy-a-account-e-accessi` | `459131eb8` | analisi (sessione `119ed166`) |
| X | X - Plugin asset e ricerca | 6183 | `/tmp/librefolio-r13-x` | `e-alfy-x-plugin-asset-e-ricerca` | `459131eb8` | analisi (sessione `ad5f37c8`) |
| W | W - Import e transazioni | 6184 | `/tmp/librefolio-r13-w` | `e-alfy-w-import-e-transazioni` | `459131eb8` | analisi (sessione `e71e0e34`) |
| J | J - Numeri e analisi | 6185 | `/tmp/librefolio-r13-j` | `e-alfy-j-numeri-e-analisi` | `459131eb8` | analisi (sessione `4c677a01`) |
| Z | Z - Sospensione e risveglio | 6186 | `/tmp/librefolio-r13-z` | `e-alfy-z-sospensione-e-risveglio` | `459131eb8` | analisi (sessione `d401e062`) |
| B | B - Backup e Docker | 6187 | `/tmp/librefolio-r13-b` | — | — | dopo il primo checkpoint di H |
| E | E - Email | 6188 | `/tmp/librefolio-r13-e` | — | — | dopo token e inviti di A |
| Y | Y - Cruscotto e grafici | 6189 | `/tmp/librefolio-r13-y` | — | — | dopo il lotto B dei colori |

Corsie del programma colori, da non usare: 6150–6154 e 6160. Lettere riservate ai colori:
L, R, G, T, C, U, S, P.

## Funzioni per il cloud

| Ondata | Funzione | Sessione | Stato |
|---|---|---|---|
| 1 | Pausa degli aggiornamenti e sospensione (F26) | Z | ⏳ |
| 1 | Segreti e configurazione (F03) | H | ⏳ |
| 1 | Prontezza e versione (F08) | H | ⏳ |
| 1 | Profilo gestito (F05) | H, A, X | ⏳ |
| 1 | Disclaimer e link legali (F09) | A | ⏳ |
| 1 | Admin iniziale da variabili (F02) | A | ⏳ |
| 1 | Inviti, registrazione e gestione utenti (F13) | A | ⏳ |
| 2 | Email facoltativa (F04) | E | ⏳ |
| 2 | Backup e ripristino dalla UI (F01) | B | ⏳ |
| 2 | Backup continuo con Litestream (F25) | B | ⏳ |
| 2 | Avvio, aggiornamento all'accesso e risveglio (F07) | Z | ⏳ |
| 2 | Impostazioni dei plugin | X | ⏳ |
| 2 | Ordine dei fornitori nella ricerca (F21) | X | ⏳ |
| 3 | Fornitore di prezzi a pagamento (F06) | X | quando sarà scelto |

## Riordino (ondata 0)

| Lotto | Sessione | Stato |
|---|---|---|
| Registri per famiglia di plugin (PL2) | X | ⏳ |
| Asset senza shim (PL6), cambi in `services/fx/` (PL4), router di asset e cambi, router dei segnali (PL7) | X | ⏳ |
| Import broker in `services/brim/` (PL5, U-B3, U-B4), transazioni, broker | W | ⏳ |
| Segnali (PL1), rischio, preparazione delle serie, portafoglio, PAC | J | ⏳ |
| Piattaforma, file, agganci di `main.py`, configurazione | H | ⏳ |
| Servizi account | A | ⏳ |
| Frontend: auth, settings, support | A | ⏳ |
| Frontend: cambi (FE4), asset (FE5) — dopo il lotto A dei colori | X | ⏳ |
| Frontend: transazioni (FE8) — dopo il lotto A dei colori | W | ⏳ |
| Frontend: segnali e rischio (FE2), dashboard (FE6), broker e lotti (FE7) — dopo il lotto B | Y | ⏳ |
| Frontend: file (FE3), `DataTable` — dopo il lotto C | Y | ⏳ |
| Frontend: utility, store, suffissi (FE9–FE11) | Y | ⏳ |
| Test speculari (TS1) | H | da decidere a riordino del backend finito |

## Treni

| # | Data | Cosa | Commit |
|---|---|---|---|
| 1 | 2026-10-14 | Piano della fase, sezioni 1.3 nel backlog | (questo commit) |
