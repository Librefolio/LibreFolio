# Report di Audit della Documentazione - Transactions & Events

**Data:** 18 Giugno 2026
**Area:** Transactions & Events (modals, validation, Batch pipelines, Context Menus, Table UX, transfers, DraftRow vs PendingOp)

## Metodologia e Risultati dell'Esplorazione
L'analisi si è concentrata sulle directory `mkdocs_src/docs/user/transactions/` (per la documentazione utente, limitatamente ai file in lingua inglese `.en.md`) e `mkdocs_src/docs/developer/` (backend e frontend).

Di seguito viene riportata la valutazione dettagliata per ogni singolo argomento richiesto.

---

### 1. Modals
* **Stato:** Assente (lato Developer) / Completa ma da migliorare esteticamente (lato User)
* **Analisi:** Il file utente `form.en.md` descrive bene i campi e le tipologie di transazione che compaiono nel form modale, tuttavia un arricchimento visuale con screenshot o video-pillole renderebbe la guida esteticamente più appagante e chiara per gli utenti. Lato sviluppatore, non esiste alcuna documentazione tecnica su come i modali siano implementati nel frontend (gestione dello stato, chiusura, sovrapposizioni).
* **Proposta:**
  - *Developer:* Creare una documentazione per il componente modale in `mkdocs_src/docs/developer/frontend/components/modal.md`.
  - *User:* Aggiungere asset visuali in `form.en.md`.

### 2. Validation
* **Stato:** Completa e allineata agli standard estetici
* **Analisi:** Eccellente copertura. Lato utente, `form.en.md` espone in modo conciso i requisiti di validazione del form. Lato backend, l'architettura della validazione (che raccoglie tutti gli errori senza interrompersi subito - *never fail-fast*) è documentata minuziosamente in `backend/transactions/service.md` e `backend/transactions/balance_validation.md`, includendo l'algoritmo del *balance walk* e i ruoli.
* **Proposta:** Nessuna azione critica richiesta.

### 3. Batch pipelines
* **Stato:** Completa e allineata agli standard estetici
* **Analisi:** Ottimamente documentata nel backend (`service.md`). L'architettura dell'endpoint centralizzato `execute_batch()`, con il suo ordine stretto di esecuzione e la semantica dei commit/rollback, è spiegata molto chiaramente. Lato utente, la possibilità di azioni in "bulk" è menzionata sia in `index.en.md` che nella sezione dedicata alle importazioni dal broker (`import/index.md`).
* **Proposta:** Nessuna azione richiesta.

### 4. Context Menus
* **Stato:** Assente
* **Analisi:** Nessuna traccia di documentazione riguardante i menu contestuali, né nel frontend (sviluppo) né nelle guide utente. Il file `data-table.md` parla di "Row Actions" ma non menziona l'esistenza o l'implementazione di un vero *Context Menu* (clic destro).
* **Proposta:**
  - *Developer:* Inserire l'implementazione tecnica (gestione dell'evento di right-click, posizionamento) all'interno di `mkdocs_src/docs/developer/frontend/components/context-menu.md` (o integrare in `data-table.md`).
  - *User:* Aggiungere in `mkdocs_src/docs/user/transactions/index.en.md` un paragrafo illustrato sull'uso dei menu contestuali per accedere rapidamente alle azioni sulle transazioni.

### 5. Table UX
* **Stato:** Completa e allineata agli standard estetici
* **Analisi:** Ottima. Lato sviluppatore, `data-table.md` copre ampiamente sorting, filter, pagination, selection, state persistence e cell types con esempi di codice Svelte 5. Lato utente, `index.en.md` guida chiaramente sull'utilizzo di queste feature (ordinamento e ricerca).
* **Proposta:** Nessuna azione richiesta.

### 6. Transfers (Transazioni Composite, Split & Promote)
* **Stato:** Completa e allineata agli standard estetici
* **Analisi:** Perfettamente coperta. Il documento tecnico `split_promote.md` è chiarissimo nel definire le logiche di collegamento tra i "legs" (`link_uuid`) e le regole di trasformazione. Lato utente, la guida `index.en.md` guida passo passo su come e perché dividere o unire le transazioni, e il WAC in queste casistiche è spiegato.
* **Proposta:** Nessuna azione richiesta.

### 7. DraftRow vs PendingOp
* **Stato:** Assente
* **Analisi:** Questi due concetti tecnici, legati alla fase transitoria in cui una transazione è creata/modificata prima di essere persistita sul database, non sono documentati da nessuna parte. È presente solo un piccolo accenno a un campo `is_pending` per il WAC preview all'interno del file `wac.md`.
* **Proposta:**
  - *Developer:* Scrivere un documento dedicato (es. `mkdocs_src/docs/developer/frontend/state/transaction-draft.md`) o aggiungere un blocco sostanziale nel file di architettura del frontend, per spiegare la differenza tra `DraftRow` (UI transitoria) e `PendingOp` (gestione delle queue/operazioni in sospeso) in relazione al form e alla validazione real-time.

## 🏁 Recap Attività (Sessione 18 Giugno)
Partendo da questo audit, abbiamo svolto le seguenti attività:
1. **Context Menu & Table UX**: 
   - Aggiunta la documentazione tecnica del *Context Menu* in `data-table.md` (riconoscendo che è una feature globale della tabella e non limitata alle transazioni).
   - Inserito un carosello illustrativo in `data-table.md` per mostrare la tabella nei vari contesti (Assets, FX, Transazioni, Files).
2. **Automazione Screenshot (Playwright)**: 
   - Estesi i test E2E (`gallery.spec.ts`) per catturare automaticamente le schermate "Grid" e "Table" per Assets e FX, più le modali.
3. **MkDocs UI & Gallery Carousels**: 
   - Sviluppato da zero un componente carosello personalizzato in CSS/JS per MkDocs (`lf-screenshot-carousel`).
   - Riscritto le pagine `gallery/desktop.en.md` e `gallery/mobile.en.md` convertendo le serie di immagini statiche in caroselli interattivi (es. viste dashboard, form modali, visualizzatori file).
   - Perfezionato il layout responsive mobile: altezza vincolata (`65vh`), effetto cover-flow 3D laterale per 3+ elementi e flip a 180° (dietro) per caroselli a 2 elementi.
   - Risolto conflitti CSS tra l'hover effect delle immagini e lo zoom dei contenitori Deep-Dive.

**Rimane da fare (Prossime Sessioni)**:
- Inserire materialmente gli screenshot generati *all'interno* di `form.en.md` (attualmente sono solo nella Gallery).
- Creare il documento developer per le Modals (`modal.md`).
- Creare il documento developer per `DraftRow vs PendingOp`.
