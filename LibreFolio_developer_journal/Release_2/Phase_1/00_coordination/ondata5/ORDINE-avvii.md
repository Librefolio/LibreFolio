# Ondata 5 — ordine di avvio delle sessioni (coordinatore) — bozza

Base: `dev_release2` = `1fd80c481` (treni 9 e 10 dentro, tutti i worktree già fast-forward). Brief approvato: `BRIEF-ondata5.md`. Regole e kickoff: `kickoff-common.md` e `kickoff-<SESSIONE>.md` (W, W2, X, MF, J, Y, A, B, H, Z) in questa cartella.

**Messaggio di avvio, uguale per tutti** (cambia solo il nome): «Sei la sessione `<S>` dell'ondata 5. Leggi `salvataggi-worktrees-20261021/ondata5/kickoff-common.md` e poi `kickoff-<S>.md`, lavora come l'agente `coordinated-workstream`. Primo turno: analisi breve, poi parti sui lotti marcati PARTI SUBITO.»

## Gruppo 0 — prima di avviare chiunque (il coordinatore, 15 minuti)
1. Verifica che ogni worktree sia a `1fd80c481` e pulito (`git status --porcelain` vuoto): H, W, X, MF, J, Y, A, B, Z.
2. **W2 è nuova**: crea la sessione dall'app con **worktree nuovo** (ramo nuovo da `dev_release2`); il worktree di D (`e-alfy-d-dipendenze`) **non** si riusa: D si archivia come sessione e, se vuoi, il suo worktree si rimuove (OK permanente: lotto tutto in dev). Per W2: `npm ci` (tuo, approvato) e poi `api sync`, **prima** che chieda i test; il suo primo turno è solo lettura, non aspetta.
3. Le corsie in `/tmp` possono non esistere dopo un riavvio: ogni sessione le ricrea da sé (scritto in `kickoff-common.md`).
4. Teniti libero il lucchetto `/tmp/librefolio-heavy.lock` per l'ordine degli slot (sotto).

## Gruppo 1 — subito, percorso critico (5 sessioni, giorno 0)
Sono i percorsi lunghi o quelli da cui dipendono altri: ritardarli allunga tutta l'ondata (~2,5-3 settimane).

| # | Sessione | Perché subito | Prima cosa |
|---|---|---|---|
| 1 | **MF** (Opus) | P4 è il prerequisito di J5-1 (#48), di Y5-2 (via J), dei pavimenti N74/SEC8, di B5 e P1c; 4,5-6,5 giorni | analisi e **rossi di P4**; primo messaggio sulla **forma dei segmenti** (sblocca il contratto di J) |
| 2 | **Z** | Q1…S1 (3-4 giorni, **blocca il tag**) sblocca R1 di J e tre pavimenti di MF; Z è altrimenti ferma | analisi + 7 scenari di parità; l'accordo «ultimo prezzo ≤ d al tasso di d» con J |
| 3 | **X** | Z-35 **blocca il tag** (dati sbagliati in produzione); il **contratto di CP12** sblocca W5-8; C-65a e N68 senza dipendenze | Z-35 (analisi con MF), contratto CP12, C-65a |
| 4 | **W** | è il percorso più lungo (8,5-11 giorni); W-B88 senza dipendenze | inventario W-B88 sui 12 plugin senza il generico |
| 5 | **W2** (nuova) | corre in parallelo a W invece che in fila (risparmia ~2,5-3,5 giorni) | analisi di V-37b (poi codice dopo `npm ci`) |

## Gruppo 2 — subito, ma lotti piccoli e leggeri (4 sessioni, giorno 0)
Nessuna attesa di altri; la maggior parte **blocca il tag** perché li aspetta il coordinatore cloud. Leggeri sul lucchetto.

| # | Sessione | Contenuto | Nota |
|---|---|---|---|
| 6 | **B** | `backup pending --json`/`--recover` (cloud), M-1 arm64 (Haiku), poi B5-1 | B5-1 solo dopo la **firma di A**; per B5-1 serve **Opus** (cambia il modello quando ti dice «pronto per B5-1») |
| 7 | **A** | A5-1 (admin protetto, revisione Opus), poi A5-2 | A5-2: la **firma** della funzione va a B **subito**, prima del codice |
| 8 | **H** | `users_used/users_limit` (Haiku), X-R84, DOC-2 (analisi), DOC-1 (inventario e proposta) | DOC-1 **non ristruttura** finché non dici tu |
| 9 | **Y** | Z-14b + Z-15, ritocchi F1-F3, F4 | Y5-2 (#48) aspetta il contratto di J: Y intanto disegna su dati finti |

## Gruppo 3 — quando c'è qualcosa da leggere (1 sessione)
| # | Sessione | Quando | Perché |
|---|---|---|---|
| 10 | **J** (Sonnet) | al **primo messaggio di MF sulla forma dei segmenti** (giorno 1-2) | non ha niente da scrivere prima di P4 (J5-1) e di Q1 (R1): aprirla prima costa solo sessione ferma. Primo turno: contratto della serie per posizione (serve subito a Y) + 7 scenari di R1; il punto «ultimo prezzo ≤ d al tasso di d» va girato a Z **prima** che scriva Q1, quindi se Z e J si parlano, avvia J già il giorno 0 |

(Se preferisci non aspettare, avvia J anche nel gruppo 1: costa solo il primo turno di analisi.)

## Sblocchi durante l'ondata (cosa committare, e a chi dire «via»)
Un solo scrittore per file: il coordinatore committa il checkpoint, aggiorna il worktree di chi aspetta, poi scrive «via».

| Quando hai committato… | Scrivi «via» a… | Per… |
|---|---|---|
| contratto di CP12 (X5-4a) | **W** | W5-8, campo «ordine della data» |
| **Y5-1** (Z-14b + Z-15) | **X** | X5-F1 in `fx/[pair]/+page.svelte` (file di Y fino a lì) |
| messaggio di MF sui segmenti (non è un commit) | **J**, poi **Y** (contratto) | contratto della serie per posizione, componente su dati finti |
| **P4** | **J** (J5-1), **MF** (N74, SEC8, B5, P1c) | #48 backend; pavimenti; B5 **prima** di J nei file `portfolio_api.py`/`schemas/portfolio.py` |
| **B5** di MF | **J** | J5-1 negli stessi file |
| **J5-1** | **Y** | collega i dati veri di #48 |
| **Q1…S1** di Z (con revisione di X) | **J** (R1), **MF** (N75/X-R55, Z-30, AI Export) | R1; pavimenti |
| **R1** di J | **MF** | pavimento SEC8-1b |
| **firma di A5-2**, poi **funzione + modale di A** | **B** | B5-1 contro la firma, poi montaggio vero |
| **W5-1, W5-2, W5-5** | **W** (E-21 con Haiku) | W5-6 sugli stessi `plugin.py` |
| **V-37b** | **W2** | #47 (stesso form) |
| commit di W su B2 | **W2** (solo se W lo chiede) | testo dell'avviso nel form |
| **tutti** i commit che toccano le pagine admin (B, H5-1, X) | **H** | DOC-1: ristrutturazione, ultimo |

Revisioni incrociate da girare (sola lettura): MF rivede **W-B87**, **X5-2**, **J5-1**; X rivede **Z (Q1…S1)**, **Y5-F4**, **W5-8**; Opus rivede **A5-1** (sotto-agente di A); MF firma i numeri prima del gate 11b.

## Treni
- **Treno 11a** (appena verdi, senza aspettare i motori): H (`users_used/limit`, X-R84, DOC-2), B (pending/recover, M-1, B5-1), A (A5-1, A5-2), Y (Z-14b/Z-15, F1-F4), X (Z-35/Z-32, C-65a, X5-F1), W (W-B88, B2, C-70b), W2 (V-37b), Z (Z5-F1). Gate ~1 h 40. Così Z-35 e `backup pending` non aspettano P4.
- **Treno 11b** (motori e lotti larghi): MF (P4, pavimenti, B5, P1c), Z (Q1…S1), J (#48, R1), Y5-2 (#48 frontend), X (N68, CP12), W (W-B87 con lo split, E-21 + W-B80, campo CP12), W2 (#47), H (DOC-1). **Revisione dei numeri di MF prima del gate** (~1 h 40).

## Ordine degli slot pesanti (uno alla volta, `flock`; 15 GB di RAM)
Quando due sessioni chiedono lo slot insieme, vince quella più in alto. Tempi dalle ondate 3-4: `all-frontend` ~1 h, `all-backend` ~27 min.
1. **MF** (`services financial-math`, `portfolio-engine`, parità `get_report`: ~20 min per checkpoint; i più pesanti in RAM: **mai insieme a un `all-frontend`**; **durante la misura di memoria di P4 (copia con la data al 1500) nessun altro slot pesante**).
2. **W** (`external brim-row-skips` puro, test dei plugin, `api brim` ~2 min, `front-transaction import` ~10 min).
3. **W2** (`front-transaction form`/`modals` ~15 min, Vitest del form).
4. **X** (`api assets`, `services asset-providers`, `front-asset asset-modal`/`asset-detail` ~15 min; i test di Yahoo con `history` finta, leggeri).
5. **Z** (Q1…S1: `services price-query`, `api prices`, `api fx`, `services signals`, parità ~15 min).
6. **Y** (`front-portfolio`, `front-asset asset-list`, `front-fx fx-list`, `price-refresh-reload` ~15 min).
7. **J** (`services risk-*` + parità ~10 min; `services portfolio-*`).
8. **A** (`api users-admin`, `api email-*`, E2E `settings` ~10 min) e **B** (`services backup-*`, `api backup-*`, `utils backup-cli*`, `api backup-roundtrip` ~10 min; M-1 non ha test locali).
9. **H** (`api panel-status`, `api hosting-panel-routes` ~3 min; X-R84 Vitest + uno spec; `mkdocs build` per DOC-1/DOC-2).
10. **Gate 11a**, poi **gate 11b**.
Corsie: H 6181 · W 6183 · A 6185 · Z 6186 · Y 6189 · J 6190 · X 6191 · B 6192 · MF 6193 · **W2 6194** (data dir `/tmp/librefolio-r13-w2`) · gate 6180.
Se dopo un riavvio un lavoro in background sembra fermo: il lucchetto in `/tmp` e le cartelle delle corsie possono essere spariti (scritto nel comune).

## Da ricordare
- Prima del tag restano i **debiti dichiarati**: traduzione delle pagine toccate (form, Yahoo, backup, CLI, dashboard, guida admin riordinata: giro unico con Aphra, su tua richiesta); designer (colori categoriali di #48, galleria G-22…G-27); D6 e H-3 nell'ondata 6; J-58 scartata.
- Fuori dall'ondata: H-18 (già fatto), D6, X-R48b (scartata), B6/B7, D-P4/P4b, Y-43, 2FA admin.
