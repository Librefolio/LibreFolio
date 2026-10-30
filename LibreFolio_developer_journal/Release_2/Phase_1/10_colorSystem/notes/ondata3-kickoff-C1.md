# Brief — programma colori · C1 · le transazioni sui ruoli di colore (l'ultimo pezzo del cancello)

> **A cosa serve (per il developer).** È l'**ultimo pezzo che blocca il tag 1.3.0** sul fronte colori: il piano dice «niente 1.3 con neutri e stati convertiti a metà», e quasi tutti quelli rimasti stanno nelle schermate delle transazioni (Bulk, unione dei lotti, anteprima del costo medio, import). Dopo questo lotto il tema scuro è coerente anche lì. Esempio: la finestra «Promuovi e unisci» oggi ha ancora grigi e verdi fissi che nel tema scuro stonano.

**Worktree**: `/home/alfy/Documenti/02_myRepo/LibreFolio_prj/LibreFolio-worktrees/e-alfy-expert-barnacle` · **Branch**: `e-alfy-t-tokens-theme`
**HEAD di partenza (da verificare)**: `2879ae3e4` (fast-forward fatto dal coordinatore).
**Corsia**: porta `6187`, cartella dati `/tmp/librefolio-r13-c1`.
**Regole**: come nell'ondata 2 (skill `design-system` e `theme-roles`, solo ruoli, mai `dark:` su un ruolo, ruolo più vicino con `colour: closest role, to review`).

## Misura (21/10, albero di `dev_release2`): m1 243 classi in 25 file
Nelle transazioni (`frontend/src/lib/features/transactions/**`): **12 file, 138 classi** (neutri 25, stati 41, categoriali 72):
`bulk/PromoteMergeModal.svelte` 62 (8/18/36), `wac/WacPreviewSection.svelte` 21 (6/8/7), `events/AssetEventPicker.svelte` 12 (4/6/2), `bulk/TransactionBulkModal.svelte` 9 (cat), `import/AssetGroupStep.svelte` 8 (1/7/0, la stella ambra), `form/TxFormOptionalSection.svelte` 6 (cat), `bulk/TxBulkToolbar.svelte` 4 (cat), `form/TxFormPairSection.svelte` 4 (cat), `import/GapFixToggle.svelte` 4 (interruttore), `import/TransactionCompareModal.svelte` 4 (interruttore), `bulk/TxBulkBanners.svelte` 2 (cat), `import/pairCellHtml.ts` 2 (cat).

## Cosa fare
1. **Neutri, stati e interruttori** dei 12 file: obbligatori (cancello). Interruttori sui ruoli Q2 come nell'ondata 2.
2. **Categoriali** (72): restano fuori dal cancello e aspettano i ruoli di categoria. Se esiste già un ruolo `--lf-cat-*` che corrisponde in modo ovvio (per esempio il colore di un tipo di transazione), usalo; altrimenti lasciali e mettili nell'elenco per la designer.
3. Quando le classi spariscono, **cancella da `frontend/src/app.css` le regole di rimappatura rimaste senza usi** (oggi: `html.dark .bg-white`, `.bg-gray-100`, `.text-gray-600`, `.border-gray-100`, se a quel punto non hanno più usi). Nient'altro in `app.css` (il resto è B6, lotto a parte).
4. Gate: `theme-roles --check` e `--update` solo per i tuoi file; i gate Vitest dei temi; i Vitest dei componenti toccati (cartella `transactions`); `front check` (in `flock`); E2E nello slot: `front-utility theme-roles` e `front-transaction all` (la categoria intera: K3a ha appena cambiato questi file).

## Non fare
- Fuori dalle transazioni non tocchi niente (le pagine di Y-40, `lib/theme/**` di C2).
- Nessun cambio di comportamento: solo classi di colore. Se un test asserisce una classe di colore, sostituiscilo con un `data-*` di stato (come hai fatto per `asset-list`).

## Fatto quando
Neutri, stati e interruttori delle transazioni a 0 nel ratchet, regole morte di `app.css` tolte, gate verdi, E2E verdi nello slot, elenco «to review» per la designer, piano di T aggiornato, riga per la voce unica 🔄 del CHANGELOG, **CHECKPOINT READY** e **FROZEN**.
