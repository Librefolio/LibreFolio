# Ondata 2 — piano proposto (21/10/2026, coordinatore Opus) — NON avviato

## Stato verificato
- `dev_release2` = `89e8b2e61` (il tuo «Claude rule update» sopra il journal del treno 6 `15a669d7c`). Treno 6 dentro, gate verde su `861a38567`. **30 commit non pushati** rispetto a `origin/dev_release2` (`b844f83f2`).
- Le tre sessioni dell'ondata 1 (y-39a, h-61-cp1, z-29s-a) e il vecchio coordinatore sono **archiviati**: servono sessioni nuove.
- Tutti i branch dei workstream hanno **0 commit fuori da dev**: si portano avanti in fast-forward, nessun merge.
- Lavoro sporco ancora nei worktree, già salvato in `salvataggi-worktrees-20261021/` (identico): piani di T, X, A, MF; i 3 test non tracciati di CP2 in H.
- Docker: la sessione non ha ancora il gruppo `docker` (serve che tu esca e rientri).

## Colori: quanto manca (misura del 21/10, ratchet `--check` pulito)
| Cosa | Quante | File |
|---|---|---|
| Neutri (grigi, bianco, nero) | 189 classi | 28 |
| Stati (rosso, verde, giallo, blu…) | 235 classi | 27 |
| Categoriali (viola, indaco, rosa, teal…) — aspettano la designer | 147 classi | 19 |
| `libre-*` e simili | 19 classi | 10 |
| **Totale legacy (m1)** | **590** | 45 |
| Interruttori (dentro i numeri sopra) | ~55-67 classi (non 109) | 9 |
| Serie dei grafici in `chartTheme.ts` (non misurate dal ratchet) | 153 letterali | 1 (+137 negli altri file di `lib/theme`) |

Esempio: `UnifiedLotsTable.svelte` ha 60 classi, di cui 42 di stato (verde/rosso dei lotti). Il cancello «neutri e stati» vuol dire ~424 classi in ~35 file; i 147 categoriali non si chiudono senza la designer.

## Sessioni proposte: 7 (più sotto-agenti)
| # | Sessione | Lotto | Worktree | Modello | Corsia |
|---|---|---|---|---|---|
| 1 | **Y** | Y-39b | `e-alfy-redesigned-spork` | Sonnet | 6189 |
| 2 | **Z** | O1, poi Z-29b | `e-alfy-potential-sniffle` | Sonnet | 6186 |
| 3 | **H** | H-61 CP2 (biglietti firmati) | `e-alfy-sturdy-memory` | Opus (codice di sicurezza) | 6181 |
| 4 | **W-back** | Fineco (commissioni + guida), poi avvisi dei plugin (W-B86 + D-W85-4) | `e-alfy-fluffy-meme` | Sonnet | 6183 |
| 5 | **W-front** | issue #58 (riproduzione), poi K3a | `w-bulk-form` (nuovo) | Sonnet | 6184 |
| 6 | **C1** | colori: neutri, stati, interruttori di broker, impostazioni, strumenti, UI condivisa (~265 classi) | `e-alfy-expert-barnacle` | Sonnet | 6187 |
| 7 | **C2** | colori: serie dei grafici (DV-10), `toneClasses`, ruoli nuovi | `e-alfy-congenial-potato` | Sonnet | 6188 |

Perché così:
- **Mai due scrittori sullo stesso file**: Y tocca solo `LineChart:450` + prop, Z solo la soglia di densità; C1 non tocca transazioni (K3a), asset/fx (Y/Z), `lib/theme` (C2); C2 è l'unico su `tokens.css`; W-back non tocca il frontend delle transazioni, W-front non tocca i plugin.
- **Rimandati** a dopo questa ondata: colori delle transazioni (dopo K3a) e di asset/fx (dopo Y-39b e Z-29b), B6 (pulizia di `app.css`), galleria.
- **Sotto-agenti**: ogni figlio usa `haiku` per letture e conteggi, `sonnet` per test/doc/patch (C1 divide per area). Io uso `haiku`/`sonnet` per verificare le consegne e un agente `security-review` indipendente (Opus) per CP2 prima del commit.
- **Uno slot pesante alla volta** (`flock`): ordine previsto degli E2E: #58 → Y (`fx-settings`, `fx-list`, `asset-list`) → Z (`asset-list`) → K3a → `theme-roles`. Con 7 sessioni la RAM (8 GB liberi ora) è il rischio: se scende sotto 2 GB fermo l'ultima sessione partita.

## Preparazione (io, prima di avviare; con il tuo via)
1. Fast-forward a `89e8b2e61` dei branch di Y, Z, H, W, T, DV (nessun commit loro fuori da dev; il lavoro sporco non viene toccato).
2. Worktree nuovo `LibreFolio-worktrees/w-bulk-form`, branch `e-alfy-w-bulk-e-form` da `dev_release2`.
3. `npm ci` in `frontend/` di W, w-bulk-form, T, DV (uno alla volta, in `flock`): hanno ancora i `node_modules` del Mac.
4. `api sync` in ognuno dei 7 worktree.

## Commit e treno 7
Ogni CHECKPOINT READY: rilancio io le prove del figlio, commit sul suo branch con percorsi espliciti. Quando ci sono 2-4 lotti pronti: candidato in `gate-coord`, gate completo (come il treno 6), e solo col tuo via fast-forward di `dev_release2`.

## Brief
`kickoff-common.md`, `kickoff-Y.md`, `kickoff-Z.md`, `kickoff-H.md`, `kickoff-WB.md`, `kickoff-WF.md`, `kickoff-C1.md`, `kickoff-C2.md` (questa cartella).

## Promemoria per gli agenti
- **Fineco**: l'utente `@Xgialippo` (discussione #49) il 21/10 ha confermato che le immagini vanno bene così e che può essere citato; il developer gli ha promesso **il nome nel CHANGELOG**. Scritto nel brief di W-back.
