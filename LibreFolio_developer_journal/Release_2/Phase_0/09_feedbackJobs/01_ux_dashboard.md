# 01 — UX & Dashboard

Task di piccola/media dimensione su interfaccia e dashboard. Approvati dall'utente il 07/09/2026
(revisione TODO_FUTURI). Ordine suggerito: il bug prima di tutto.

---

## 🐛 BUG — "Testa configurazione" non si resetta cambiando asset

**Complessità**: S · **Tipo**: bug vero (priorità nel round)

### Segnalazione (utente, 07/09)
Se si fa "Testa configurazione" su un asset e poi se ne cerca un altro, il risultato del test
rimane quello dell'ultimo test invece di resettarsi.

### Dove guardare
- Il risultato del probe vive in `frontend/src/lib/components/assets/resolveProviderError.ts` /
  nella sezione `ProviderAssignmentSection.svelte` (o nella modale asset, verificare dove è lo
  stato `probeResult`/`lastTestResult`).
- Verificare che lo stato si azzeri quando cambia l'asset selezionato (probabilmente uno
  `$state`/`$effect` che non dipende dall'asset id, o un reset mancante su cambio selezione).

### Definizione di fatto
Apri asset A → testa → vedi esito; cerca/seleziona asset B → l'esito di A non deve più
comparire (o deve essere chiaramente marcato come riferito ad A). Test componente (vitest) che
fissa il comportamento.

---

## 🕶️ Modalità privacy nella dashboard

**Complessità**: S–M · **Origine**: nota utente in TODO_FUTURI (07/09)

### Richiesta
Un toggle nella dashboard che **nasconde i valori numerici** e mostra solo le percentuali —
per condividere screenshot senza rivelare il valore del portafoglio.

### Note implementative
- Toggle nel toolbar della dashboard (o nelle impostazioni), stato in `localStorage`
  (convenzione già usata per vista card/table, theme).
- Le card KPI, tabelle posizioni e valori nei grafici mostrano `•••` (o solo %) quando attivo.
- Le percentuali/allocation restano visibili (sono il contenuto condivisibile).
- Decidere se è solo dashboard o globale (header): iniziare dashboard-only.

---

## 📈 Colonna Yield on Cost (YOC) nelle tabelle posizioni

**Complessità**: S–M · **Origine**: feedback @ExpectChaos (utente esterno)

### Richiesta
Una colonna che mostri il **rendimento corrente dell'asset rispetto al costo di acquisto**
(Yield on Cost): utile per chi investe in strumenti a distribuzione e vuole monitorare il
rendimento nel tempo, indipendente dalle fluttuazioni di mercato.

### Note implementative
- YOC = reddito annuo corrente dell'asset (dividendi/interessi) ÷ costo di acquisto (WAC del
  lotto/posizione). Attenzione: serve il reddito *corrente* (ultimo anno o annualizzato), non
  lo storico cumulato — decidere la finestra (TTM consigliata).
- Dove: tabella Holdings in dashboard (`ExposureTable.svelte`) e tabella posizioni nel broker
  detail. Colonna nascosta di default, attivabile dall'icona occhio (convenzione colonne).
- I dati reddito per asset esistono già (`asset_income` / eventi DIVIDEND/INTEREST).

---

## 📁 Filtro utente nella Files page

**Complessità**: S · **Origine**: TODO_FUTURI (più vecchio)

### Richiesta
Nella pagina Files (admin, più utenti): filtro dropdown per utente (accanto al search per
nome) + colonna utente visibile se `users.length > 1`, badge colorati come nel BRIM (stessa
funzione di calcolo colori).

### Note implementative
- Backend: endpoint `GET /api/v1/admin/users` (lista utenti, admin only) — verificare se esiste già.
- Riutilizzare il pattern filtri di `FilesTable`/`urlFilters` (già in uso nella pagina).

---

## 💱 Tooltip esplicativo "Valuta" nel form asset

**Complessità**: S · **Origine**: feedback utente

### Richiesta
Nel form di creazione asset, un tooltip sul campo **Valuta** che chiarisca: indica la
*valuta di negoziazione / esposizione del provider*, non la denominazione né la valuta finale
di portafoglio (quella è gestita dalle conversioni forex).

### Note
- Una riga di i18n ×4 + il componente Tooltip già esistente. Definizione di fatto minima.

---

## ~~🔀 DECISIONE — `mode='duplicate'` del TransactionFormModal~~ ✅ RISOLTA (07/09)

**Decisione utente 07/09**: eliminare come codice morto. **Eseguito** nella stessa sessione.

### Audit svolto (il punto era "tutte le transazioni passano dalla bulk?")

Risposta: le **mutazioni** (edit/clone/delete) passano tutte dalla bulk workspace; il
FormModal singolo resta per **create** e **view** (3 mount point: transactions page, broker
detail, dashboard — tutti view/create). `mode='duplicate'` non era raggiungibile da nessun
punto → quadro già coerente, unico debito il ramo morto.

### Rimosso
- Ramo `mode='duplicate'` dal type `Mode` + il ramo di draft-seeding + il titolo.
- Le 2 prop usate solo da quel flusso (`highlightFields`, `titleOverride`) + la funzione
  `hl()` + il CSS `hl-match`/keyframes (7 call sites mai attivi).
- Chiave i18n orfana `transactions.form.titleDuplicate` ×4.
- Test T3 del duplicate-mode (il T3 vero è coperto dalla E2E tx-clone sulla bulk).
- `transactions/+page.svelte`: tipo `formMode` senza 'duplicate'.

svelte-check 0/0, prettier pulito, test del FormModal verdi.

> **Nota 07/09 (verifica richiesta)**: create/edit singolo **già** è un fast-open della bulk —
> `transactions/+page.svelte`: `onAddTransaction`/`handleEditRow`/`handleCloneRow` aprono la
> `TransactionBulkModal` con `bulkIntent` (create/edit/clone/delete); il FormModal singolo è
> usato solo per **view** (e come modale nidificata dentro la bulk per l'edit di una riga).
> Nessuna azione: il comportamento voluto è già quello implementato.

---

## ☕ Pagina/area "Supporta il progetto" — caffè + condivisione social

**Complessità**: S · **Origine**: utente 07/09

### Richiesta
Nella pagina del supporto (l'area con il "offri un caffè"), oltre al caffè, proporre **in
alternativa la condivisione del progetto sui social** per aiutarlo a crescere.

### Dettagli
- Social attuali del progetto:
  - X: `https://x.com/librefolio`
  - Reddit: `https://www.reddit.com/user/Far_Psychology_6271/`
- Ogni social ha un **hook** che apre la piattaforma con un **messaggio pre-compilato nella
  lingua corrente** dell'utente (es. intent di condivisione X `https://twitter.com/intent/tweet?text=…`
  con testo localizzato; per Reddit un submit link con titolo localizzato).
- **Dove vive oggi il "caffè"** (tutti i punti da toccare):
  - `DonationPopupModal.svelte` — la **modale al login** che compare a cadenza (il backend
    segnala via `AuthLoginResponse.show_donation_popup`, `auth.py:111`; cadenza gestita da
    `record_login_and_maybe_show_popup`). Va aggiunta qui la sezione social (è il punto a
    più alta visibilità).
  - About tab (settings) — la pagina "supporta".
  - **NON** l'header (`layout/Header.svelte` / `HelpMenu.svelte`) né la pagina pubblica di
    login (`routes/+page.svelte`): lì resta solo il caffè (decisione utente 07/09).
- Decidere se i social vanno **ovunque** appare il caffè (popup incluso) o solo nella pagina
  supporto + popup; la raccomandazione è almeno popup + About.
- i18n: i messaggi pre-compilati vanno nelle 4 lingue, usando la lingua attiva al click.

### Definizione di fatto
- Sezione "oppure condividi" con i 2 social + hook pre-compilati (testo localizzato, link al
  sito/repo), presente **solo** nella **modale di login** (DonationPopup) e nella pagina
  supporto (About). Header e pagina di login pubblica restano solo-caffè. Nessuna chiamata
  al backend; tutto statico + i18n.

---

## 🧭 Onboarding al primo login (nuovo utente)

**Complessità**: M · **Origine**: utente 07/09 — da dettagliare insieme

### Obiettivo
Quando un utente appena registrato fa il **primo login**, guidarlo a scegliere subito le
impostazioni di base (icona profilo/avatar, lingua, valuta) e proporgli un **rapido tour**
delle funzioni principali.

### Da dettagliare (da fare insieme)
- **Dove**: modale post-login una-tantum (flag `has_onboarded` per utente) o una pagina di
  benvenuto; decidere se skippabile.
- **Cosa chiede**: avatar (ImagePicker), lingua (4), valuta base (default da Global Settings).
- **Tour**: le 3-4 superfici principali (dashboard, aggiungi broker, importa, asset) — formato
  da decidere (tooltip guidati vs. slide).
- Backend: un flag per-utente (UserSettings o tabella) che registra l'avvenuto onboarding;
  endpoint per marcarlo. Decidere se offrirlo anche "di nuovo" dalle impostazioni.
- UX: non bloccante, non ripetitivo; chiudibile e riapribile.

> Scrivo l'ossatura qui; i dettagli (cosa chiede, come è il tour, come si marca "fatto")
> li definiamo insieme prima di partire.

> **Nota 07/09 (verifica richiesta)**: create/edit singolo **già** è un fast-open della bulk —
> `transactions/+page.svelte`: `onAddTransaction`/`handleEditRow`/`handleCloneRow` aprono la
> `TransactionBulkModal` con `bulkIntent` (create/edit/clone/delete); il FormModal singolo è
> usato solo per **view** (e come modale nidificata dentro la bulk per l'edit di una riga).
> Nessuna azione: il comportamento voluto è già quello implementato.

