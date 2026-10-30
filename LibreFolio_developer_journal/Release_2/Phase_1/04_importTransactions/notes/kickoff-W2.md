# Kickoff W2 · Il form delle transazioni — ondata 5 — bozza (sessione NUOVA)

Regole comuni: `kickoff-common.md` (leggilo per primo).

> **A cosa serve (per il developer).** Il form per inserire una transazione diventa più chiaro e più comodo. (1) **V-37b**: «⚡ Validate now» è sempre cliccabile; al clic controlla prima i campi obbligatori, poi il formato; mette il rosso su **tutte** le celle sbagliate e il fuoco sulla prima; **nessuna chiamata al server finché c'è un errore**; vale per transazione singola, coppia e FX. Esempio: Qty vuota e data «abc»: oggi il pulsante è disabilitato e non dice perché; domani è cliccabile e le due celle diventano rosse. (2) **#47**: si sceglie «Importo totale / Prezzo unitario» con un selettore a badge (come «PMC manuale/auto»); l'altro valore si calcola e l'importo resta visibile e modificabile. Esempio: 12 azioni a 83,40: scrivi il prezzo e l'importo 1 000,80 compare da solo.

**Perché una sessione nuova.** Il form (`TransactionFormModal.svelte`, `txPayloadHelpers.ts`) e i plugin di import (W) sono due famiglie di file disgiunte: con W2 i 7-9+ giorni di W e i 2,5-3,5 di W2 corrono in parallelo.

**Modello**: Sonnet. **Giorni**: 2,5-3,5 (V-37b 1,5-2; #47 1-1,5).
**Worktree**: **il worktree che l'app ti ha dato; ramo nuovo da `dev_release2`** (NON quello di D `e-alfy-d-dipendenze`, che si archivia). Scrivi nel tuo piano il percorso e il nome del ramo che trovi.
**HEAD di partenza (da verificare)**: `1fd80c481` (= `dev_release2`, treni 9 e 10 dentro).
**Corsia**: porta `6194`, cartella dati `/tmp/librefolio-r13-w2` (la porta era di D, ora libera: il coordinatore ha chiuso D).
**Attenzione, worktree nuovo**: non ha `node_modules` e `generated.ts` aggiornati. **Non lanciare `npm ci`** (divieto comune): il primo turno è solo lettura e analisi; prima del primo `front check` o Vitest chiedi al coordinatore `npm ci` + `api sync` e chiudi il turno. Il venv Python è quello condiviso (`PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc`, mai `pipenv run` nudo da un worktree nuovo).
**Piano**: **file nuovo tuo**, in `LibreFolio_developer_journal/Release_2/Phase_1/04_importTransactions/` accanto al piano di W, ma **non** dentro il piano di W (un solo scrittore per file): `plan-phase01Step2TransactionForm-W2.prompt.md` (nome provvisorio, il coordinatore può rinominarlo), con link al piano di W (`plan-phase01ImportTransactions.prompt.md`). Riferimenti: `PROSSIMI_LAVORI.md:129-143` (V-37b) e `:567-580` (#47); backlog V-37b ~2104. Skill: `design-system`, `devpy-i18n`, `testing-frontend`.

## Cosa fare
1. **V-37b** (**11a**, PARTI SUBITO per l'analisi; il codice dopo `npm ci`/`api sync`). Una parte c'è già: `validateNow` salta il server con errori locali e porta al primo (`TransactionFormModal.svelte:1106-1137`) e il pulsante è `disabled={!isFormComplete}`. Da fare: pulsante sempre cliccabile; al clic prima gli obbligatori, poi il formato; rosso su tutte le celle sbagliate, fuoco sulla prima; zero chiamate al server con un errore; singola, coppia, FX. Un **helper puro nuovo** (obbligatori + formato → elenco di celle) con Vitest; 2-4 chiavi i18n (`i18n/transactions/*`, 4 lingue, con `./dev.py i18n`); doc `user/transactions/form.en.md` (docs-writer, solo inglese); `tx-fx-completeness.spec.ts` (e, se serve, `transactions-modals.spec.ts`). **Prima i rossi** (con `test-author`): Qty vuota + data «abc» → due celle rosse, fuoco sulla prima, nessuna richiesta di rete (verificabile nello spec).
2. **#47** (**11b**, **dopo V-37b**, stesso form). Selettore a badge «Importo totale / Prezzo unitario» come «PMC manuale/auto»; l'altro valore si calcola; l'importo resta visibile e modificabile; **regola dei decimali già in uso** (W-B64, N63): non inventarne un'altra. Il calcolo è **presentazione/ingresso**: se per il prezzo unitario serve una moltiplicazione con arrotondamento, cerca prima in `financial_math/` e nell'utility di decimali già usata dal form: **mai una copia locale** della formula. Rossi: 12 × 83,40 → 1 000,80; modifica dell'importo → prezzo ricalcolato coerente; round-trip senza scarti di arrotondamento. Doc del form.
3. **Avviso di B2** (solo se W lo chiede nel suo checkpoint, dopo il commit di W): se il form deve mostrare l'avviso «arrivo prima della partenza» con un testo suo, lo aggiungi tu; nessun file in comune con W.

## Dipendenze da altre sessioni
Nessuna per V-37b/#47. **W** (B2): vedi sopra. Il coordinatore ti scrive quando `npm ci` e `api sync` sono fatti.

## File condivisi
- **Tuoi**: `frontend/src/lib/features/transactions/form/TransactionFormModal.svelte`, `utils/transactions/txPayloadHelpers.ts`, `i18n/transactions/*.json`, `mkdocs_src/docs/user/transactions/form.en.md`, `frontend/e2e/transactions/tx-fx-completeness.spec.ts`, `transactions-modals.spec.ts`, un helper puro nuovo accanto al form.
- **Di altri**: i plugin di import e il Bulk (**W**); `routes/(app)/transactions/+page.svelte` (**X**, bottone «Ricollega eventi»); `financial_math/**` (**MF**).

## Non fare
- Non toccare i file di W, X, MF. Nessun colore a mano. Nessun calcolo finanziario nuovo nel componente.
- #47 non inizia prima che V-37b sia committato.

## Domande
Nessuna.

## Fatto quando
V-37b (checkpoint a parte, **11a**): rossi→verdi, Vitest dell'helper, `front-transaction form` e `modals` nello slot (~15 min), `front check` 0/0 dopo `api sync`, `i18n check`, ratchet dei colori pulito, doc, piano. #47 (checkpoint a parte, **11b**): idem. Righe CHANGELOG proposte: ✨ «Il form delle transazioni: «Validate now» sempre attivo, controlla tutti i campi e li segna in rosso» (V-37b); ✨ «Importo totale o prezzo unitario: scegli quale scrivere, l'altro si calcola» (#47). **CHECKPOINT READY** e **FROZEN** a ciascun checkpoint.
