# P1‑bis — Ristrutturazione del flusso di import: correzione prima del confronto

> **Stato**: 📋 piano, nessuna riga di codice scritta.
> **Origine**: collaudo del checkpoint di Fase A ([`plan-phase00BrimCreditAgricoleTrades.prompt.md`](./plan-phase00BrimCreditAgricoleTrades.prompt.md)) — 07/08/2026.
> **Collegato a**: [`plan-phase00AssetIdentityAndIdentifiers.prompt.md`](./plan-phase00AssetIdentityAndIdentifiers.prompt.md) (WS‑C, nuovo Step «Unifica asset»)
> · [`plan-phase00ImportWizardUx.prompt.md`](./plan-phase00ImportWizardUx.prompt.md)
> **⚠️ Conflitto attivo**: WS‑C è in mano a un altro agente **sullo stesso file** `ImportWizardModal.svelte`. Vedi §6.

---

## 1. Il difetto, in una riga

**Il confronto con il database avviene prima che l'utente possa correggere le righe che il
plugin non ha capito — e non viene mai rifatto dopo.**

## 2. Perché non è un'opinione

Catena verificata nel codice:

| Passo | Dove | Cosa succede |
|---|---|---|
| 1 | `backend/app/api/v1/brokers.py:720` `POST /files/{id}/parse` | è **questo** endpoint a produrre `duplicates` |
| 2 | `backend/app/services/brim_provider.py:1237-1354` | `tx_likely_duplicates` / `tx_possible_duplicates` calcolati **sulle transazioni appena parsate** |
| 3 | `ImportWizardModal.svelte:730-760` | il frontend legge `resp.duplicates` e congela `duplicateStatus` per riga |
| 4 | `TransactionBulkModal` | l'utente corregge la riga **dopo**: nessuno rilancia il confronto |

Conseguenza concreta sul caso Crédit Agricole: le 4 righe `COMPRAVENDITA` arrivano al
confronto come **prelievi di cassa senza titolo**. Il rilevatore le confronta quindi contro i
movimenti di cassa del DB, non contro gli acquisti che sono davvero. Quando l'utente le
converte in acquisto nel bulk modal, il verdetto «unica / probabile duplicato» resta quello
calcolato sui dati sbagliati.

> Il difetto è **più grave** di come è stato riportato: non avviene «allo step 4», avviene
> allo **step 3**, ancora prima che l'utente veda la tabella.

## 3. Il principio da ristabilire

> Nessun confronto prima che il dato sia completo.

Da cui l'ordine obbligato: **capire → unificare → correggere → confrontare → rivedere**.
Ogni passo produce l'input del successivo; invertirne due significa confrontare rumore.

## 4. Struttura degli step proposta

| # | Step | Auto-salto | Nota |
|---|---|---|---|
| 1 | Carica file | — | invariato |
| 2 | Seleziona file | — | invariato |
| 3 | Analisi | — | parse; **non** produce più il verdetto duplicati |
| 4 | **Unifica asset** | sì, se nulla da unificare | 🔴 **WS‑C, altro agente** |
| 5 | **Correggi le righe segnalate** | sì, se nessun todo `blocker` | 🆕 questo piano |
| 6 | **Duplicati** | sì, se nessun gruppo e nessun match DB | 🆕 questo piano — oggi è un riquadro dentro lo step 3 |
| 7 | Revisione e import | — | ex step 4 |

Tre step nuovi su quattro esistenti: senza l'auto‑salto il flusso diventerebbe più lungo per
tutti per servire una minoranza di casi. **L'auto‑salto non è un abbellimento, è la condizione
che rende accettabile la struttura.**

## 5. Cosa serve davvero

### 5.1 Scorporare il confronto duplicati dal parse — *è la vera modifica*

`POST /files/{id}/parse` oggi fa due cose: interpreta il file **e** lo confronta col DB. Vanno
separate.

- Nuovo endpoint `POST /brokers/import/duplicates` che riceve le transazioni **come sono ora**
  (dopo unificazione asset e correzioni) e restituisce lo stesso `BRIMDuplicateReport`.
- `parse` continua a restituire `duplicates` finché non è migrato tutto il frontend
  (retro‑compatibilità: la risposta è già nel contratto pubblico).
- Il rilevatore esistente (`brim_provider.py:1225+`) **non cambia**: cambia solo chi lo chiama
  e con quali dati. Rischio contenuto.

> Senza questo punto gli step nuovi sono cosmetici: si sposta la UI ma il verdetto resta
> calcolato sui dati sbagliati.

### 5.2 Step 5 «Correggi le righe segnalate»

Alimentato dai `field_todos` con `severity === 'blocker'` — l'infrastruttura esiste già da
Fase A (`BRIMFieldTodo.evidence`, `BrimEvidenceTable`, il cancello di salvataggio
`hasTodoBlockers`).

Per ogni riga: evidenza della riga sorgente, il commento del plugin, e i campi da compilare
(tipo transazione, titolo, quantità). Uscita consentita solo a todo risolti — oppure con un
«procedi comunque» che li lascia come blocker fino al bulk modal, che è la rete di sicurezza
già in piedi.

Il banner rosso del `TransactionBulkModal` **resta**: diventa la rete, non la prima linea.

### 5.3 Step 6 «Duplicati»

Trasloco del riquadro attuale (`ImportWizardModal.svelte:3216+`), già ristrutturato il
07/08/2026 in due pannelli per grado di sovrapposizione con badge di stato. Il contenuto non
cambia; cambia il momento in cui viene calcolato e il fatto che ha una pagina sua.

### 5.4 Macchina a stati

`STEPS` (`:86`) è un array di 4 elementi con `currentStep` numerico e confronti `>`/`<` sparsi
(`goToStep`, `goNext`, `goBack`, `maxReachedStep`). Con step che si auto‑saltano, i numeri nudi
diventano fragili: `goBack` da 7 deve atterrare su 3 se 4/5/6 sono saltati.

Servono step **identificati per nome**, con `visibleSteps` derivato dalle condizioni di
attivazione, e navigazione che si muove su quell'elenco. È rifattorizzazione, non funzionalità,
ma è il prerequisito perché il resto non diventi un campo minato di `if`.

## 6. ⚠️ Il vincolo che decide la sequenza

WS‑C (Step «Unifica asset») e questo piano toccano **le stesse 200 righe** di
`ImportWizardModal.svelte` — la macchina a stati e il markup degli step. Un altro agente ci sta
lavorando ora.

Tre modi di procedere, in ordine di rischio crescente:

| | Approccio | Costo | Rischio |
|---|---|---|---|
| **A** | **§5.1 subito** (backend, endpoint separato); gli step dopo WS‑C | basso | quasi nullo: il backend non è conteso |
| **B** | Chi fa WS‑C introduce **anche** la macchina a stati per nome; gli step nuovi si innestano dopo | medio | nullo, ma richiede coordinamento |
| **C** | Entrambi gli agenti sullo stesso file insieme | — | **alto**: conflitti garantiti sul markup |

Raccomandato: **A**, poi **B**. Il valore vero è in §5.1 e non richiede di toccare il file
conteso.

## 7. Verifica

| # | Prova | Atteso | Esito |
|---|---|---|---|
| 1 | I 3 file CA, correggo le 4 righe allo step 5 | il confronto duplicati dello step 6 le tratta da **acquisti** | ⏳ collaudo manuale |
| 2 | File senza blocker e senza asset da unificare | il flusso resta a 4 pagine: 4/5/6 saltati | ✅ `tx-brim-import` 8/8 |
| 3 | Indietro dallo step 7 con 4/5/6 saltati | atterra sullo step 3, non su una pagina vuota | ✅ `tx-brim-import` T8 |
| 4 | Doppio import dello stesso file | i duplicati DB si vedono ancora, calcolati dopo le correzioni | ✅ API‑015 + `tx-import-resolution` IWR‑007 |
| 5 | Procedi comunque allo step 5 | il banner del bulk modal continua a bloccare il salvataggio | ✅ invariato (fuori dal perimetro dello step) |

## 7.1 Stato di esecuzione

| Passo | Descrizione | Stato |
|---|---|---|
| 5.1 | `POST /brokers/import/duplicates` + `refreshDuplicateReport()` lato wizard | ✅ 2026‑08‑07 |
| — | Test API `TestDuplicateCheckEndpoint` (API‑014/015/016) | ✅ 3 passed |
| 5.4 | Macchina a stati con id di step e auto‑skip (`StepId`, `visibleSteps`, `enterNextActiveStep`) | ✅ 2026‑08‑07 |
| 5.2 | Step «Correzioni» (`FixFlaggedStep.svelte` + handler) | ✅ 2026‑08‑07 |
| 5.3 | Step «Duplicati»: risolutore cross‑file **+ riepilogo collisioni DB** | ✅ 2026‑08‑07 |
| — | 16 chiavi i18n × 4 lingue | ✅ |
| — | `front check` 0/0 · `front build` · prettier | ✅ |
| — | `test api brim` 27 · `test external brim-providers` 463 | ✅ |
| — | `tx-brim-import` 8/8 · `tx-import-resolution` 10/10 | ✅ |

> **Note implementazione**: la vera scoperta è stata che `duplicateGroups` cataloga **solo** le
> sovrapposizioni *fra i file dell'import*, mentre le collisioni col **database** vivono sul
> `duplicateStatus` di ogni riga. Attivare lo step sui soli gruppi lo faceva sparire proprio nel
> caso più comune — il re‑import dello stesso file. Ora `stepIsActive('duplicates')` guarda
> entrambi e lo step mostra un riepilogo compatto delle righe già presenti a DB, rimandando alla
> tabella di revisione (già collaudata) per il confronto riga per riga.
>
> **⚠️ Fuori pista**: lo step «Correzioni» era nato per *tutti* i blocker; con i blocker
> `cost_basis_override` (WAC) il pulsante Avanti restava disabilitato per sempre, perché l'editor
> dello step non ha quel campo. Ristretto a `DUP_RELEVANT_FIELDS` — lo step esiste per le correzioni
> che **cambiano il verdetto sui duplicati**; il costo di carico resta al bulk editor, che ha gli
> strumenti per unità.
>
> **⚠️ Fuori pista**: aggiungere `TXCreateItem` a un *body di richiesta* ha fatto sdoppiare lo
> schema dal generatore in `_Input`/`_Output`; i tipi frontend sono stati riallineati a `_Output`
> seguendo la prassi già presente (`Currency_Output`, `FAPricePoint_Input/_Output`).

## 8. Fuori perimetro

- La riparazione del plugin CA (Fase B di P1) — indipendente.
- Il motore di similarità asset (WS‑C/C‑01) — altro piano.
- Il rilevatore di duplicati in sé: si sposta, non si riscrive.
