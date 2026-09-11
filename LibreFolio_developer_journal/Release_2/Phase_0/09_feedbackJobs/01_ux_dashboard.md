# 01 — UX & Dashboard

Task su interfaccia, dashboard e shell autenticata. Approvati dall'utente il 07/09/2026
(revisione TODO_FUTURI), poi precisati nella stessa data durante l'analisi per sprint.
Stato corrente e dettagli in [06_piano_sprint.md](06_piano_sprint.md). Il bug resta il primo intervento.

> **Chiusura Gruppo E — 2026-09-09:** U1, U4, U5, U7 e U9 sono stati
> implementati, verificati e applicati al checkout `dev_release2`; piano ed
> evidenze in [14_feedbackImportUrgent](../14_feedbackImportUrgent/manifest-integrazione-E.md).
> U2 privacy, U3 YOC e U8 onboarding restano aperti.

---

## 🐛 BUG — "Testa configurazione" non si resetta cambiando asset ✅

**Complessità**: S–M · **Tipo**: bug vero (priorità nel round)

### Segnalazione (utente, 07/09)
Se si fa "Testa configurazione" su un asset e poi se ne cerca un altro, il risultato del test
rimane quello dell'ultimo test invece di resettarsi.

### Dove guardare
- **Verificato 2026-09-07**: `ProviderAssignmentSection.svelte:102-105` conserva
  `testStatus`, `testResults` e durata; `AssetModal.svelte` conserva un altro
  `providerTestStatus`. `resolveProviderError.ts` traduce gli errori, non possiede lo stato.
- Il reset manuale del provider non copre parametri e assegnazioni programmatiche dalla
  ricerca. `applySearchResult` avvia auto-probe e metadata concorrenti senza protezione
  completa contro risposte del contesto precedente.
- Invalidare per identità della configurazione e generazione del draft; proteggere anche
  l'applicazione tardiva della metadata nello stesso flusso.

### Definizione di fatto
Apri asset A → testa → vedi esito; cerca/seleziona asset B → l'esito di A non deve più
comparire (o deve essere chiaramente marcato come riferito ad A). Test componente (vitest) che
fissa il comportamento, comprese risposte fuori ordine, A → B → A, parametri e riapertura.
Il gate "Save without testing" deve usare soltanto lo stato corrente.

**Completato 2026-09-09 (E/U1):** autorita' per generazione di draft/configurazione,
risposte tardive scartate e salvataggio legato al probe corrente; verificati anche
riapertura, metadata concorrenti e modifica manuale.

---

## 🕶️ Modalità privacy globale

**Complessità**: XL · **Origine**: nota utente in TODO_FUTURI (07/09), scope ampliato 2026-09-07

### Richiesta
Un **lucchetto aperto/chiuso nell'header autenticato**, valido nell'intera applicazione.
Nasconde **importi e quantità personali**, lasciando visibili prezzi pubblici di mercato,
cambi, percentuali e rapporti. Questa decisione sostituisce lo scope iniziale dashboard-only.

### Note implementative
- Store/prop globale e primitive condivise vicine ai campi sensibili; preferenza persistita
  per account, senza flash del dato al caricamento o cambio utente.
- Patina decorativa sopra **segnaposto**, mai sopra cifre reali soltanto sfocate. Coprire
  anche testo accessibile e tooltip finanziari, non lasciare numeri sotto un canvas offuscato.
- Tooltip concettuali invariati; quelli che mostrano importi/quantità personali seguono
  la stessa protezione. Log, allegati, API ed export grezzi non vengono anonimizzati.
- Inventario completo: dashboard, broker, posizioni/lotti, transazioni, modali, grafici,
  risk monetario e nuovo Tool. WAC/prezzi di esecuzione personali sono sensibili;
  quotazioni pubbliche e FX no.
- Prima definire comportamento di input/rivelazione ed export; non mostrare un lucchetto
  globale mentre alcune superfici protette rivelano ancora dati.

### Confronto UI richiesto — 2026-09-07
Prima della realizzazione: viste ASCII desktop/mobile di header, campi/regioni, input e
modali nei due stati, con approvazione del dev. Dopo: percorso operativo per attivare la
privacy, cambiare account/pagina e verificare le superfici; feedback registrato e risolto.
Regola comune G-UX-DESIGN/G-UX-REVIEW nel [piano](06_piano_sprint.md).

---

## 📈 Colonna Yield on Cost (YOC) nelle tabelle posizioni

**Complessità raffinata 2026-09-10**: M per metrica/fonti + S per colonna/docs · **Origine**: feedback @ExpectChaos (utente esterno)

**Stato 2026-09-10:** ✅ **PLAN/DESIGN APPROVED, non implementato**.
Contratto finale, storyboard desktop/mobile, dipendenza cache FX e passi nel
[piano H dedicato](../19_yieldOnCost/plan-phase00YieldOnCost.prompt.md).
L'approvazione non autorizza ancora l'esecuzione.

### Richiesta
Una colonna che mostri il **rendimento corrente dell'asset rispetto al costo di acquisto**
(Yield on Cost): utile per chi investe in strumenti a distribuzione e vuole monitorare il
rendimento nel tempo, indipendente dalle fluttuazioni di mercato.

### Note implementative
- **Decisione finale 2026-09-10**: fonte esclusiva sono le `Transaction`
  asset-linked DIVIDEND/INTEREST, i cui importi LibreFolio sono lordi. TAX/FEE,
  provider e AssetEvent income non entrano. Ogni incasso viene normalizzato per
  quantita' LONG eleggibile a fine D-1, broker-scoped e transfer-aware; la somma
  per-unit da `T - 364` a `T` inclusi viene divisa per PMC/WAC unitario residuo.
  Nessun carry automatico dell'income fra broker dopo un transfer.
- Dove: tabella Holdings in dashboard (`ExposureTable.svelte`) e tabella posizioni nel broker
  detail. Colonna **visibile di default**, accanto ad Annualized Return. L'utente
  puo' nasconderla con l'occhio; il normale override user-scoped e' condiviso
  fra entrambe le superfici.
- Dashboard e broker usano già lo stesso `PositionsPanel`/`ExposureTable`: una sola colonna.
- `asset_income`/`cash_yield` sono cumulativi, non YOC. Gli incassi importati
  via BRIM contano soltanto quando diventano Transaction asset-linked; non si
  divide il loro totale per il cost basis corrente. Ogni riga usa la propria
  quantita' D-1; split e FX riallineano unita' e valuta.
- La baseline H `b22998f` contiene la shared FX identity F, L1 e fix
  `cost_basis_currency` con witness identity/L1. H deve riusare la funzione
  identica nella L2, senza seconda implementazione. Gate 0 tecnico e' complete;
  resta soltanto l'autorizzazione esecutiva.

### Dato mancante, zero e coppia giovane — decisione 2026-09-10
- Nessun income TTM = YOC numerico 0 soltanto se la prima transaction storica
  della coppia `(asset, broker)` e' almeno `T - 364`; close/rebuy non resetta
  l'age. Coppia piu' giovane = `unavailable/insufficient_history`.
- Ogni holding e' applicabile, inclusi crypto e asset manuali; nessun
  `not_applicable` o whitelist per tipo.
- Income senza quantita' D-1, replay/split incoerente, FX o WAC mancanti:
  unavailable con reason tipizzata; mai calcolo parziale/fallback.
- UI `-` per no-income e unavailable; solo i problemi unavailable mostrano
  l'icona info con custom Tooltip. Il normale zero/no-income non appare come
  errore. Percentuali disponibili: due decimali, senza `+`.
- La policy FX e' quella portfolio corrente, senza cap YOC; provenance e
  tooltip espongono la data effettiva del tasso.
- La colonna YOC non e' ancora implementata.

### Documentazione, tooltip e confronto UI
- Aggiungere **in inglese**, tramite docs-writer, una pagina nella teoria finanziaria:
  percorso proposto
  `mkdocs_src/docs/financial-theory/technical-analysis/performance-metrics/portfolio-engine/yield-on-cost.en.md`.
  Collegare indice/nav e guide posizioni; nessuna traduzione documentale automatica.
- Spiegare formula/unita, finestra, fonti, casi del trattino, split/bond/FX e differenze
  rispetto a dividend yield di mercato, cash yield cumulativo e CAGR.
- Tooltip nell'**header YOC** della tabella, riusando `ColumnDef.headerTooltip`:
  sintesi formula transaction-ledger/D-1/365 giorni e accesso alla teoria.
  Testo UI EN/IT/FR/ES.
- Microvista ASCII di header/tooltip e righe con percentuale o `-`,
  **APPROVED 2026-09-10**; l'implementazione UI resta congelata.
  Dopo: walkthrough su dashboard e broker, visibilita' default/override condiviso, motivi dei trattini,
  pagina teoria e raccolta feedback operativo.

---

## 📁 Filtro utente nella Files page ✅

**Complessità**: S · **Origine**: TODO_FUTURI (più vecchio)

### Richiesta finale
Nella pagina Files: colonna **Caricato da** ordinabile e filtro colonna
multi-selezione con avatar/nome, secondo il pattern Asset. Lista, griglia e URL
condividono lo stesso stato; assente, non risolto e ID noto restano distinti.

### Note implementative
- **Verifica 2026-09-07**: `/admin/users` non esiste, ma non serve crearlo.
  `GET /api/v1/users/search?q=` restituisce gli utenti attivi; riusare `UserSearchSelect`.
- `uploaded_by_user_id` è già disponibile per upload statici e BRIM: il filtro riguarda
  l'uploader, non il proprietario del broker.
- Riutilizzare `FilesTable`/`urlFilters` e `getIndexColor`; stesso filtro in lista/griglia,
  refresh e cambio tab. Uploader sconosciuti/disattivati/null non fanno sparire file.
- Nessun ampliamento dei permessi correnti sui file.

**Confronto UI 2026-09-07:** microvista ASCII toolbar/colonna prima; dopo, istruzioni per
provare uploader, URL, lista/griglia e casi sconosciuti con feedback del dev.

**Completato 2026-09-09 (E/U4):** variante colonna approvata e verificata in
desktop/mobile, senza ampliare i permessi sui file.

---

## 💱 Tooltip esplicativo "Valuta" nel form asset ✅

**Complessità**: S · **Origine**: feedback utente

### Richiesta
Nel form di creazione asset, un tooltip sul campo **Valuta** che chiarisca in una
frase che e' la valuta in cui vengono salvati i prezzi.

### Note
- Una riga di i18n ×4 + il componente Tooltip già esistente. Definizione di fatto minima.

**Completato 2026-09-09 (E/U5):** testo breve localizzato nelle quattro lingue.

---

## ~~🔀 DECISIONE — `mode='duplicate'` del TransactionFormModal~~ ✅ RISOLTA (07/09)

**Decisione utente 07/09**: eliminare come codice morto. **Eseguito** nella stessa sessione.

### Audit svolto (il punto era "tutte le transazioni passano dalla bulk?")

Risposta aggiornata al 2026-09-07: le azioni principali **create/edit/clone/delete** usano la
bulk workspace. I tre mount di pagina (transactions, broker detail, dashboard) usano il
FormModal per **view**; il form resta vivo anche come editor locale dentro la bulk.
`mode='duplicate'` non era raggiungibile → quadro coerente, unico debito il ramo morto.

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

## ☕ Pagina/area "Supporta il progetto" — caffè + condivisione social ✅

**Complessità**: S · **Origine**: utente 07/09

### Richiesta
Nella pagina del supporto (l'area con il "offri un caffè"), oltre al caffè, proporre **in
alternativa la condivisione del progetto sui social** per aiutarlo a crescere.

### Dettagli finali
- Social: X, Reddit, Facebook, Instagram e TikTok.
- Ogni icona apre una modale condivisa con testo nella lingua UI, URL pubblico
  del progetto sempre copiato e flusso **Copia e vai**. X/Reddit usano le
  capacita' di composizione disponibili; Facebook condivide il link, mentre
  Instagram/TikTok spiegano onestamente i passaggi manuali e i requisiti media.
- **Superfici concordate**:
  - `DonationPopupModal.svelte` — la **modale al login** che compare a cadenza (il backend
    segnala via `AuthLoginResponse.show_donation_popup`, `auth.py:111`; cadenza gestita da
    `record_login_and_maybe_show_popup`). Va aggiunta qui la sezione social (è il punto a
    più alta visibilità).
  - About tab (settings) — **verifica 2026-09-07: la sezione caffè non c'è ancora**;
    aggiungerla insieme alla condivisione, riusando lo stesso blocco di azioni.
  - **NON** l'header (`layout/Header.svelte` / `HelpMenu.svelte`) né la pagina pubblica di
    login (`routes/+page.svelte`): lì resta solo il caffè (decisione utente 07/09).
- Scope confermato: **solo popup + About**, non ovunque appare il caffè.
- i18n: i messaggi pre-compilati vanno nelle 4 lingue, usando la lingua attiva al click.
- URL condiviso pubblico del progetto, mai l'hostname locale dell'istanza; apertura della
  bozza social senza pubblicazione automatica o tracking. Cadenza backend invariata.

### Definizione di fatto
- Sezione "oppure condividi" nei soli DonationPopup e About. Nessun social
  nell'header globale o nella pagina login pubblica.
- Clipboard negata e popup bloccato hanno errori distinti; l'origine resta aperta.
  Nessuna pubblicazione automatica, tracking o hostname dell'istanza condiviso.

**Gate UX 2026-09-07:** prima ASCII del popup e di About, approvati dal dev; dopo,
istruzioni per raggiungere entrambe le superfici e provare lingua, link e dismiss,
registrando il feedback. Non cambiare la cadenza reale per facilitare la review.

**Completato 2026-09-09 (E/U7):** cinque social, modale e fallback verificati.
L'indagine su Instagram non ha trovato un ingresso web affidabile a Crea; il limite
e' documentato, non mascherato da una falsa funzionalita'.

---

## 🧭 Onboarding al primo login (nuovo utente)

**Complessità**: L dopo confronto utente · **Origine**: utente 07/09

> **Analisi 2026-09-07**: la stima iniziale M è stata sospesa prima del confronto.
> Formato, skip e replay sono ora concordati; stato/migrazione e dettagli delle tappe
> saranno fissati nel piano esecutivo. Nessuna implementazione avviata.

### Obiettivo
Quando un utente appena registrato fa il **primo login**, guidarlo a scegliere subito le
impostazioni di base (icona profilo/avatar, lingua, valuta) e proporgli un **rapido tour**
delle funzioni principali.

### Decisioni concordate 2026-09-07
- **Pagina di benvenuto dedicata**, con saluto, lingua/valuta dai default amministratore e
  avatar opzionale. Tema dal default già esistente; non inventare un default globale avatar.
- **Tour breve in overlay**, poi **guida contestuale all'import** quando serve.
  Riferimento: [Getting Started](../../../../mkdocs_src/docs/user/getting-started.en.md) e
  [Import how-to](../../../../mkdocs_src/docs/user/transactions/import/how-to.en.md).
- Percorso introduttivo proposto: Transazioni/Importa, Broker, Asset, Dashboard;
  import-first perché broker e asset possono nascere nel wizard. Niente dati demo.
- Guida import segue i passi realmente presenti, inclusi quelli condizionali, e spiega
  consegna alla bulk/Save All senza premere automaticamente azioni che scrivono dati.
- Benvenuto e tour **skippabili definitivamente**, senza riproposta ai login successivi;
  riavvio manuale da Settings.
- Backend: stato/versione distinto per welcome, tour introduttivo e import, non inferito
  dal contatore login. `UserSettings` è a colonne: migrazione incrementale se si estende.
- Riusare controlli preferenze, non l'intera GlobalSettingsTab; coordinare focus/mobile,
  header, donation/update popup, refresh e cambio account.

**Gate UX 2026-09-07:** storyboard ASCII di welcome, tour breve, import condizionale,
skip/replay ed errori, desktop/mobile, prima delle viste. Dopo implementazione integrata:
runbook per nuovo account, interruzione/refresh e replay; feedback del dev e relativo
giro di correzione prima della chiusura.

---

## 📱 Header desktop/mobile: scompare in discesa, ricompare in salita ✅

**Complessità**: S–M · **Origine**: nuova richiesta utente 2026-09-07

### Richiesta finale
Su desktop e mobile, scorrendo verso il basso l'header scompare; appena si torna
a scorrere verso l'alto ricompare, senza dover raggiungere l'inizio della pagina.

### Analisi 2026-09-07
`Header.svelte:16-24` usa intenzionalmente flusso normale su mobile e `lg:sticky` su desktop.
Il commento ricorda un precedente toggle scroll con flicker: non ripristinarlo senza guardie.

### Definizione di fatto
Sticky/trasformazione senza salti di layout, direzione con isteresi, safe-area e resize;
reset su navigazione e cima pagina, cleanup listener. Header visibile con focus/menu/tour.
Coordinare il futuro lucchetto privacy sullo stesso componente.

**Gate UX 2026-09-07:** prima ASCII di stati visibile/nascosto e pin menu/focus/tour;
dopo review su pagina lunga con gesti reali mobile, cambio route e resize, con istruzioni
e feedback operativo. Un'immagine statica non chiude il comportamento di scroll.

**Completato 2026-09-09 (E/U9):** comportamento approvato anche su desktop,
con pin per interazioni, cleanup, reduced motion e assenza di salti di layout.

## Analisi per task — 2026-09-07

Baseline `a9138140`; superfici, dipendenze, rischi e DoD completi in
[06_piano_sprint.md](06_piano_sprint.md).

| ID | Esito | Sprint |
|---|---|---|
| U1 | ✅ Completato da E: stato/generazioni del probe e metadata concorrente. | SP01 |
| U2 | Scope globale concordato, non solo dashboard; primitive condivise. XL. | SP15 |
| U3 | ✅ [PLAN/DESIGN + GATE 0 APPROVED/COMPLETE](../19_yieldOnCost/plan-phase00YieldOnCost.prompt.md), non implementato: baseline `b22998f`; M backend + S UI/docs, attende solo autorizzazione esecutiva. | SP06 |
| U4 | ✅ Completato da E: colonna uploader ordinabile e filtro multi-selezione. | SP02 |
| U5 | ✅ Completato da E: tooltip breve localizzato. | SP01 |
| U6 | ✅ Rimozione duplicate-mode e fast-open bulk confermati; form vivo da preservare. | Nessun codice |
| U7 | ✅ Completato da E: supporto condiviso in DonationPopup/About e cinque social. | SP02 |
| U8 | Requisiti discussi; L per welcome, tour breve e guida import, con skip/replay. | SP11 |
| U9 | ✅ Completato da E: header auto-hide desktop/mobile con guardie lifecycle. | SP02 |

La [mappa nel piano](06_piano_sprint.md) separa corsie indipendenti da file condivisi:
supporto/About, Files e migrazione Preferences possono avanzare separatamente. Header,
root layout, AssetModal e integrazione dei cataloghi mantengono un owner alla volta.
Le UI soggette ai gate non sono finite finché manca il feedback operativo del dev.
