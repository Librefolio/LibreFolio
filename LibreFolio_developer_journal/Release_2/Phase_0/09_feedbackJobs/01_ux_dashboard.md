# 01 — UX & Dashboard

Task su interfaccia, dashboard e shell autenticata. Approvati dall'utente il 07/09/2026
(revisione TODO_FUTURI), poi precisati nella stessa data durante l'analisi per sprint.
Stato corrente e dettagli in [06_piano_sprint.md](06_piano_sprint.md). Il bug resta il primo intervento.

---

## 🐛 BUG — "Testa configurazione" non si resetta cambiando asset

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

**Complessità**: L per metrica/fonti + S per colonna · **Origine**: feedback @ExpectChaos (utente esterno)

### Richiesta
Una colonna che mostri il **rendimento corrente dell'asset rispetto al costo di acquisto**
(Yield on Cost): utile per chi investe in strumenti a distribuzione e vuole monitorare il
rendimento nel tempo, indipendente dalle fluttuazioni di mercato.

### Note implementative
- **Precisazione 2026-09-07**: YOC = somma delle distribuzioni lorde **per quota** nei
  **365 giorni** fino alla data finale del report ÷ PMC/WAC **unitario** residuo.
  Non dividere gli incassi complessivi del conto per un prezzo unitario. Finestra da
  `T - 364` a `T` inclusi, indipendente dal `date_from`; non dodici mesi di calendario.
- Dove: tabella Holdings in dashboard (`ExposureTable.svelte`) e tabella posizioni nel broker
  detail. Colonna nascosta di default, attivabile dall'icona occhio (convenzione colonne).
- Dashboard e broker usano già lo stesso `PositionsPanel`/`ExposureTable`: una sola colonna.
- `asset_income`/`cash_yield` sono cumulativi, non YOC. Gli incassi personali BRIM non
  garantiscono una storia per-quota completa: mancanza di dati → non disponibile con motivo,
  non zero o annualizzazione di pochi incassi.
- Fonte, split, quote-base bond, FX e completezza TTM sono il gate prima del calcolo backend.

### Dato mancante, zero e titolo giovane — decisione 2026-09-07
- UI **`-`** sia per nessun reddito sia per storia insufficiente, con spiegazione distinta.
- Storia completa e base valida ma dividendi/interessi zero: zero noto nel contratto,
  stato `no_income` proposto; visualizzazione `-`, non confusione con dato mancante.
- Strumento non distributivo: non applicabile. Storia troppo giovane/incompleta,
  base nulla o FX mancante: valore non disponibile e motivo specifico.
- La sola assenza di incassi personali o la presenza di 365 giorni di prezzi non provano
  copertura completa delle distribuzioni. Un acquisto recente non impone `-` se lo
  strumento ha già storia sufficiente e il PMC è disponibile.
- Sono requisiti del piano: la colonna YOC non è ancora implementata.

### Documentazione, tooltip e confronto UI
- Aggiungere **in inglese**, tramite docs-writer, una pagina nella teoria finanziaria:
  percorso proposto
  `mkdocs_src/docs/financial-theory/technical-analysis/performance-metrics/portfolio-engine/yield-on-cost.en.md`.
  Collegare indice/nav e guide posizioni; nessuna traduzione documentale automatica.
- Spiegare formula/unita, finestra, fonti, casi del trattino, split/bond/FX e differenze
  rispetto a dividend yield di mercato, cash yield cumulativo e CAGR.
- Tooltip nell'**header YOC** della tabella, riusando `ColumnDef.headerTooltip`:
  sintesi formula/365 giorni/trattino e accesso alla teoria. Testo UI EN/IT/FR/ES.
- Microvista ASCII di header/tooltip e righe con percentuale o `-`, approvata prima della UI.
  Dopo: walkthrough su dashboard e broker, attivazione dall'occhio, motivi dei trattini,
  pagina teoria e raccolta feedback operativo.

---

## 📁 Filtro utente nella Files page

**Complessità**: S · **Origine**: TODO_FUTURI (più vecchio)

### Richiesta
Nella pagina Files (admin, più utenti): filtro dropdown per utente (accanto al search per
nome) + colonna utente visibile se `users.length > 1`, badge colorati come nel BRIM (stessa
funzione di calcolo colori).

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
- Sezione "oppure condividi" con i 2 social + hook pre-compilati (testo localizzato, link al
  sito/repo), presente **solo** nella **modale di login** (DonationPopup) e nella pagina
  supporto (About). Header e pagina di login pubblica restano solo-caffè. Nessuna nuova
  chiamata backend per le azioni social; tutto statico + i18n. Dismiss delle nuove azioni
  esplicito e compatibile con la chiusura volontaria del popup.

**Gate UX 2026-09-07:** prima ASCII del popup e di About, approvati dal dev; dopo,
istruzioni per raggiungere entrambe le superfici e provare lingua, link e dismiss,
registrando il feedback. Non cambiare la cadenza reale per facilitare la review.

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

## 📱 Header mobile: scompare in discesa, ricompare in salita

**Complessità**: S–M · **Origine**: nuova richiesta utente 2026-09-07

### Richiesta
Su mobile, scorrendo verso il basso l'header scompare; appena si torna a scorrere verso
l'alto ricompare, senza dover raggiungere l'inizio della pagina. Desktop invariato.

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

## Analisi per task — 2026-09-07

Baseline `a9138140`; superfici, dipendenze, rischi e DoD completi in
[06_piano_sprint.md](06_piano_sprint.md).

| ID | Esito | Sprint |
|---|---|---|
| U1 | Bug di stato e risposte tardive confermato; includere metadata concorrente. S–M. | SP01 |
| U2 | Scope globale concordato, non solo dashboard; primitive condivise. XL. | SP15 |
| U3 | YOC per-quota/WAC residuo su 365 giorni, `-` con motivi distinti, teoria EN e tooltip header; fonte completa non garantita. L + S colonna. | SP06 |
| U4 | Filtro assente; API utenti e campo uploader già disponibili. S. | SP02 |
| U5 | Tooltip assente sul campo a `AssetModal.svelte:1735`. XS–S. | SP01 |
| U6 | ✅ Rimozione duplicate-mode e fast-open bulk confermati; form vivo da preservare. | Nessun codice |
| U7 | Caffè nel popup presente; About e social da aggiungere. S. | SP02 |
| U8 | Requisiti discussi; L per welcome, tour breve e guida import, con skip/replay. | SP11 |
| U9 | Nuova richiesta header mobile auto-hide, con guardia anti-flicker. S–M. | SP02 |

La [mappa nel piano](06_piano_sprint.md) separa corsie indipendenti da file condivisi:
supporto/About, Files e migrazione Preferences possono avanzare separatamente. Header,
root layout, AssetModal e integrazione dei cataloghi mantengono un owner alla volta.
Le UI soggette ai gate non sono finite finché manca il feedback operativo del dev.
