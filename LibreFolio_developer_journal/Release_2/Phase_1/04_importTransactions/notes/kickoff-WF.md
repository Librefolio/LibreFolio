# Brief — workstream W (frontend) · K3a (sicurezza dei dati del Bulk e del Form) + riproduzione della issue #58

**Worktree**: `/home/alfy/Documenti/02_myRepo/LibreFolio_prj/LibreFolio-worktrees/w-bulk-form` (nuovo, creato dal coordinatore)
**Branch**: `e-alfy-w-bulk-e-form` (nuovo, da `dev_release2`)
**HEAD di partenza (da verificare)**: `89e8b2e61`.
**Corsia**: porta `6184`, cartella dati `/tmp/librefolio-r13-wf`.
**Piano**: `LibreFolio_developer_journal/Release_2/Phase_1/04_importTransactions/plan-phase01ImportTransactions.prompt.md`, sezione «K3a — sicurezza dei dati del Bulk e del Form» (righe ~6890-6938) e le decisioni D-K3-1…7 (~6867-6878, approvate il 17/10). `Phase_1/PROSSIMI_LAVORI.md` ~74-90.
**Materiale parcheggiato**: `/home/alfy/Documenti/02_myRepo/LibreFolio_prj/copilot-enel/session-state/e71e0e34-fd06-4b55-960d-41fe8b7764ec/files/parked/`: `k3a-reds-20261019.patch` (10 file, `git apply --check` pulito su `89e8b2e61`), `k3a_cure.py` (la cura, mai applicata), `k3a_light.sh`, `README.md`, hash e stato. Ignora i file `._*` del Mac. Percorsi del Mac negli script: adattali.
**Un'altra sessione di W lavora in parallelo** sul backend (Fineco, avvisi dei plugin) in un altro worktree: tu non tocchi `backend/app/services/brim_providers/**`, `mkdocs_src/docs/user/transactions/import/**`, i cataloghi `importWizard`.

## Passo A — riproduzione della issue #58 (prima di tutto, è leggera)
Issue https://github.com/Librefolio/LibreFolio/issues/58 («Editing transactions asset type does not trigger save button»). Leggila con `gh issue view 58 --repo Librefolio/LibreFolio --comments` (**solo lettura**: non commentare). Ipotesi del coordinatore: Salva/Applica è disattivo perché i campi non rispettano le regole del nuovo tipo, e la richiesta «scartare le modifiche?» usa una condizione diversa dal pulsante.
- Form singolo (`frontend/src/lib/features/transactions/form/TransactionFormModal.svelte`): pulsante `tx-form-save` disattivo a ~:1608 con `committing || loadingPartner || hasLocalErrors || (!commitOnSave && !isFormComplete)`; `hasLocalErrors` ~:838; `isFormComplete` ~:725-740.
- Bulk (`bulk/TransactionBulkModal.svelte`): `commitDisabled` ~:2227 (`committing || ops.length === 0 || actionCount === 0 || hasTodoBlockers`), pulsante `tx-bulk-commit` ~:3338.
- Con `test-author` scrivi un E2E (accanto a `frontend/e2e/transactions/tx-bulk-operations.spec.ts` o in un file nuovo) che provi le due letture: (1) modifica singola, cambio del tipo, campi validi per il nuovo tipo → Salva attivo?; (2) Bulk, cambio del tipo, «Applica», campi validi → Salva-tutto attivo? Se uno dei due resta grigio con campi validi **è un bug vero**: fermati, riferisci con i dati (quale condizione è falsa) e non curarlo senza il via.
- L'E2E si lancia **solo con lo slot** del coordinatore (in `flock`, `LC_ALL=en_US.UTF-8`). Consegna un checkpoint intermedio (A) col verdetto.

## Passo B — K3a
1. Applica la patch dei rossi (`git apply`, è lavoro tuo e non una operazione di storia). Il **secondo giro** del test-author (K-3b, PC5 diviso, i sei casi portati nel dominio) è descritto nel piano ma «mai girato»: verifica se è dentro la patch; se no, riscrivilo con `test-author`. **Le tre scelte di W sono confermate dal developer (21/10)**: PC5 diviso (la guardia di C-46 nel Vitest del Bulk, l'E2E PC5 diventa quello di B-48), valori di test nel dominio (≤ 15 cifre significative), K-3b nello stesso lotto.
2. Rilancia i rossi (26 Vitest + 1 E2E, più quelli del secondo giro) e confermane la causa.
3. La cura: rileggi `k3a_cure.py` (dry run pulito su 8 file il 19/10), confrontala col codice di oggi, applicala a mano o con lo script adattato. Contratto nel piano: K-4 (`TransactionBulkModal.svelte` ~:487, lingua con `untrack`), B-47 (`CompactCashCell` emette solo se cambia per valore esatto), K-2 (apertura automatica una volta sola), K-3 (`resetAll` salta `inaccessible`), B-48 + D-K3-6 (15 cifre significative, prop `maxSignificantDigits` su `ExactQuantityInput` e `CompactCashCell`, chiave `transactions.errors.significantDigitsExceeded` già nelle 4 lingue), K-3b.
4. Verdi leggeri: i Vitest toccati (più di 3 file → `flock`), `front check` (dopo `api sync`, in `flock`), registrazione di `bulk/TransactionBulkModal.test.ts` in `component-unit` (`scripts/test_runner/_frontend_utility.py`, riga additiva).
5. E2E nello slot: `tx-bulk-operations`, `tx-bulk-promote-cost-basis`, `tx-fx-completeness` (nomi esatti delle azioni dal runner `front-transaction`).
6. Backlog: K-2…K-4 in `38_postReleaseBacklog`, B-47 e B-48 nella sezione di B (chiusura chiesta al coordinatore). Doc utente se il comportamento visibile cambia (solo inglese, `docs-writer`). Righe 🐛 proposte per il CHANGELOG.

## Non fare
- **Colori**: i file di `lib/features/transactions/**` hanno classi di palette, ma la loro conversione è rimandata a dopo K3a: non convertirle tu e non aggiungerne di nuove (ratchet `theme-roles --check`).
- Niente decisioni di prodotto; niente commenti su GitHub.

## Fatto quando
A: E2E di #58 scritto, eseguito nello slot, verdetto chiaro (bug sì/no, quale condizione). B: rossi verdi per la causa giusta, `front check` 0/0, E2E verdi nello slot, backlog e piano aggiornati, **CHECKPOINT READY** e **FROZEN**.
