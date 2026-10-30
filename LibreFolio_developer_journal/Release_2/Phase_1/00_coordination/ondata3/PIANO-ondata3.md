# Ondata 3 — piano (21/10/2026, coordinatore Opus) — APPROVATO dal developer, lavoro notturno

Base: `dev_release2` = `2879ae3e4` (treno 7, 22 commit non pushati).

## Decisioni del developer (21/10 sera)
- Fino a **10 sessioni** in parallelo (le 7 dell'ondata 2 hanno retto bene).
- **Y-42 dentro questa ondata** (sessione X).
- **B6 e i cancelli finali aspettano la designer.**
- **E-7 in 1.3** (A, dopo A-62): badge anche a link scaduto, testi en «Waiting for verification» / it «In attesa di verifica», niente segno in `user list`.
- **Q-G29-1 = (a)**, tooltip su tutti i segni del Gantt, in 1.3 (J, dopo TC-23 e L1b).
- **N64 in 1.3** (X, dopo Y-42), con Q1 sì e Q2 sì.
- Assunto dal coordinatore, coerente col sì a V-9 del 20/10: **Z-29fx e la parte cambi di Y-40 in 1.3**. Se non lo vuoi, si ferma al checkpoint di Z.
- Notte: le domande importanti mettono in pausa solo quel pezzo; l'agente va avanti con altro; domattina un file di recap con il lavoro fatto e le domande pendenti. Nessun merge in `dev_release2` senza il via del developer: al massimo il candidato del treno 8 provato.

## Le 10 sessioni e a cosa servono
| # | Sessione | Lotto | A cosa serve | Blocca il tag? |
|---|---|---|---|---|
| 1 | **Y** (esistente) | test di `OtherPeriodEffectsTable`, Y-40 asset, poi Y-40 cambi | Le schede mostrano a scelta assoluto, percentuale o rendimento mobile; il dettaglio si apre nella stessa vista. Il test smette di fallire sui computer in italiano. | no |
| 2 | **Z** (esistente) | Z-29fx (backend), poi Z-29d ridotto | Schede dei cambi leggere come quelle degli asset, con il rendimento mobile (serve a Y-40 cambi). | no |
| 3 | **H** (esistente, Opus) | H-55 v2, CSP sempre attiva | Il browser blocca gli script iniettati da proxy, CDN o estensioni; l'admin vede l'avviso. | sì (sicurezza) |
| 4 | **E** (nuova) | E-25, poi E-26 (b) | I filtri anti-phishing non verificano più l'email al posto del proprietario; dopo la registrazione diciamo la verità se l'email è trattenuta. | no |
| 5 | **A** (nuova) | A-62, revisione di E-26, E-7 | Menu letto nella lingua dell'utente; segnale per test e galleria; badge «In attesa di verifica» in Utenti. | no |
| 6 | **J** (nuova) | TC-23 (a), L1b, Q-G29-1 (a) | Aggiungere il cambio mancante senza uscire dall'analisi; lotti più veloci a numeri identici; tooltip sui segni del Gantt. | no |
| 7 | **C1** (esistente) | Colori delle transazioni | L'ultimo pezzo del cancello colori. | **sì** |
| 8 | **C2** (esistente) | DV-11, TC-21, DV-12, DV-13, TC-19, TC-22 | Colori dei tipi in un posto solo, righe cancellate pulite, due E2E che falliscono a torto, due pagine di doc. | no |
| 9 | **X** (nuova) | Y-42, poi N64 | Dettagli di asset e cambi disegnano gli indicatori con lo stesso codice di lista e anteprima; poi gli indicatori in cache come i prezzi. | no |
| 10 | **W** (esistente, W-back) | N78-1, solo analisi | Ti prepara la decisione «a che valore esce un'unità in una rettifica in uscita», con un esempio numerico e una raccomandazione. | no |

Modelli: H Opus (sicurezza); gli altri Sonnet; io verifico ogni consegna rilanciando le prove; revisione di sicurezza indipendente (Opus) per H-55.

## Dipendenze e file condivisi (un solo scrittore per file)
- Y-40 cambi dopo il commit di Z-29fx (Z solo backend, Y la pagina dei cambi).
- Le pagine di dettaglio (`assets/[id]`, `fx/[pair]`) sono di **X** in questa ondata; Y definisce nello store la vista d'apertura e X la legge dopo il commit di Y.
- `chartSignalRendering.ts` resta di Y; richieste di X passano da me.
- N64 dopo Y-42 e senza sovrapporsi ai file sporchi di Y.
- E-26 dopo A-62 (A rivede) e dopo il commit di H su `backend/app/api/v1/auth.py`.
- C1 solo `lib/features/transactions/**` più le regole morte di `app.css`; C2 `lib/theme/**`, Designer Lab, CSS del `DataTable`, due spec, due pagine di doc.
- File comuni additivi (li risolvo io al treno): `scripts/test_runner/*`, cataloghi i18n, baseline dei colori, backlog.

## Ordine degli slot pesanti (uno alla volta, `flock`)
Inventario CSP di H (~1 h) → E2E di C1 (`theme-roles`, `front-transaction all`) → E2E di Y (`asset-list`, `fx-settings`) → E2E di X (dettagli) → C2 (`dashboard`, `designer-lab-live`) → E/J se servono → passo 5 di H (corsa completa sotto la politica) → gate del treno 8.

## Preparazione
1. Fast-forward a `2879ae3e4` di Y, Z, H, T (C1), DV (C2), W, E, J.
2. A e X: commit della loro sezione di piano rimasta sporca, poi merge di `dev_release2`.
3. `npm ci` in E, A, J, X.
4. Brief alle 6 sessioni esistenti (Y, Z, H, C1, C2, W); 4 sessioni nuove (E, A, J, X).

## Rimandati
B6, chiusura del programma colori, galleria G-22…G-27 e cancelli finali (coverage completa, galleria completa, aggiornamento da DB 1.2, immagine Docker, revisione di sicurezza, CHANGELOG `[1.3.0]`, tag): dopo la designer.

## Brief
`kickoff-common.md` e `kickoff-{Y,Z,H,E,A,J,C1,C2,X,W}.md` in questa cartella. Recap della notte: `RECAP-notte-20261022.md`.
