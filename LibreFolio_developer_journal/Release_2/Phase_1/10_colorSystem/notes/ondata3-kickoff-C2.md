# Brief — programma colori · C2 · rifiniture: DV-11, TC-21, DV-12, DV-13, TC-19, TC-22

> **A cosa serve (per il developer).** Nessuno di questi blocca il tag, ma sono piccoli e tolgono difetti veri:
> - **DV-11**: i colori dei tipi (azioni, ETF, cambi…) vivono in un posto solo invece che in due copie tenute uguali da un test.
> - **TC-21**: in una tabella con colonne fisse, una riga cancellata (sbiadita) lascia intravedere il testo che scorre sotto le colonne fisse: si sbiadisce il contenuto, non lo sfondo.
> - **DV-12**: un test E2E della Dashboard fallisce nelle corse complete perché intercetta la richiesta sbagliata.
> - **DV-13**: un test del Designer Lab presuppone due fonti di colore che ora sono una sola (forse già superato da TC-20: verificalo).
> - **TC-19 / TC-22**: due pagine della documentazione per sviluppatori allineate al codice (banner della qualità dei dati, tinte delle righe delle tabelle).

**Worktree**: `/home/alfy/Documenti/02_myRepo/LibreFolio_prj/LibreFolio-worktrees/e-alfy-congenial-potato` · **Branch**: `e-alfy-dv-colori-dei-grafici`
**HEAD di partenza (da verificare)**: `2879ae3e4` (fast-forward fatto dal coordinatore).
**Corsia**: porta `6188`, cartella dati `/tmp/librefolio-r13-c2`.
**Backlog** (`LibreFolio_developer_journal/Release_2/Phase_0/BACKLOG_POST_1.2.md`): DV-11 ~3334, DV-12 ~3345, DV-13 ~3354, TC-19 ~3115, TC-21 ~3136, TC-22 ~3142.

## In quest'ordine (ognuno piccolo; checkpoint unico alla fine)
1. **DV-11**: il livello `category` del Designer Lab diventa una vista dei ruoli `--lf-cat-*`, e `chartCategories.ts` legge i ruoli tramite `roleColors` (la copia doppia sparisce). `CATEGORY_ROLES_IN_TOKENS` è già acceso (`3dba7f894`). File in `lib/theme/**` e `src/lib/dev/designer-lab/**`.
2. **TC-21**: `tr.row-deleted td` con opacità 0,55 fa vedere il contenuto sotto le colonne fisse di `DataTable`: sbiadire il contenuto, non lo sfondo. CSS del `DataTable` (fuori da `lib/theme`, ma nessun'altra sessione lo tocca: verificalo con `git -C <worktree> status` negli altri worktree prima di iniziare).
3. **DV-12**: `e2e/portfolio/dashboard.spec.ts`, «Positions panel publishes its loading state through data-busy»: `goto('about:blank')` prima della rotta (con `test-author`).
4. **DV-13**: `designer-lab-live.spec.ts` «export JSON, reset all, import back»: verifica se TC-20 l'ha già risolto; se sì, segna superato nel backlog; se no, due elementi con fonti di colore diverse.
5. **TC-19, TC-22**: `docs-writer`, solo inglese: `developer/frontend/data-quality-banner.md` (~:46, regola dei toni `DATA_QUALITY_TONE`) e `core-ui/data-table.md` «Sticky columns» (`--dt-row-tint`, `getRowClass`).

## Non fare
- Non toccare `lib/features/transactions/**` (C1), le pagine di Y-40, `app.css` (C1 toglie solo le regole morte; B6 è un lotto a parte).
- API di `chartTheme.ts` invariata.

## Fatto quando
Gate dei temi, `chartCategories`/`roleColors` e Vitest toccati verdi, `front check` (in `flock`), E2E `dashboard` e `designer-lab-live` nello slot, `mkdocs build` stretto e `check-links` (in `flock`), backlog aggiornato, **CHECKPOINT READY** e **FROZEN**.
