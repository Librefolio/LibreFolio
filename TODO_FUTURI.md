# TODO FUTURI

Questo file documenta miglioramenti futuri, migrazioni pianificate, e note tecniche importanti per il progetto LibreFolio.
I TODO completati sono in `TODO_Completati.md`.

---

## 📦 TanStack Table v9 Migration

**Data aggiunta**: 22 Gennaio 2026  
**Status**: ⏳ IN ATTESA (v9 in alpha)  
**Priorità**: Bassa (fino a release stabile)

### Contesto

Abbiamo scelto di usare **TanStack Table v8** con un **adapter custom Svelte 5** invece dell'adapter ufficiale `@tanstack/svelte-table` per i seguenti motivi:

1. **v8 adapter ufficiale** (`@tanstack/svelte-table`): Non compatibile con Svelte 5 (usa API interne Svelte 3/4)
2. **v9 con supporto Svelte 5**: Ancora in versione **alpha** (`9.0.0-alpha.x`)

### Soluzione Attuale

- **Libreria**: `@tanstack/table-core@^8.21.3` (stabile)
- **Adapter**: Custom in `frontend/src/lib/tanstack-table/`

### Azione Futura

Quando TanStack Table v9 sarà **rilasciato come stabile** con supporto ufficiale Svelte 5:

1. Installare l'adapter ufficiale `@tanstack/svelte-table`
2. Aggiornare import in tutti i componenti
3. Rimuovere la cartella `src/lib/tanstack-table/` (adapter custom)
4. Testare tutte le tabelle (Files, Assets, Transactions, FX)

---

## 🪵 Riorganizzazione Livelli di Log Backend

**Data aggiunta**: 11 Marzo 2026  
**Status**: 📋 PIANIFICATO  
**Priorità**: Media

### Contesto

I livelli di log del backend sono cresciuti in modo organico e presentano inconsistenze:
- Alcuni log dettagliati (es. backward-fill FX, aggiornamento rate singolo) sono finiti a livelli troppo alti
- Non esiste un livello TRACE formale — usiamo `logger.log(5, ...)` ad-hoc per messaggi sotto DEBUG
- I log dei provider HTTP (httpx/httpcore) sono stati silenziati individualmente in `logging_config.py`
- I log di sincronizzazione e refresh generano molto "rumore" anche in modalità INFO

### Azione Futura

1. **Definire una policy di log livelli** chiara per tutto il backend:
   - **CRITICAL/ERROR**: errori che richiedono intervento
   - **WARNING**: situazioni anomale ma gestite
   - **INFO**: operazioni significative dell'utente (sync completata, import file, login)
   - **DEBUG**: dettagli operativi (provider usato, query SQL, risultati intermedi)
   - **TRACE (5)**: dati granulari massivi (singolo rate, singolo backward-fill, singolo punto dati)
2. **Registrare un livello TRACE formale** con `logging.addLevelName(5, "TRACE")` e, se possibile, estendere structlog con un metodo `.trace()`
3. **Audit completo**: scorrere tutti i `logger.info/debug/warning` nel backend e verificare che il livello sia coerente con la policy
4. **Documentare** la policy in un commento in `logging_config.py`

---

## 📱 Mobile Column Reorder (DataTable)

**Data aggiunta**: 23 Gennaio 2026  
**Status**: 📋 PIANIFICATO  
**Priorità**: Bassa

### Contesto
Il riordinamento colonne nella DataTable funziona con drag & drop su desktop, ma su mobile usiamo bottoni su/giù. Potrebbe essere migliorato con touch drag nativo.

### Azione Futura
1. Verificare comportamento su dispositivi touch reali (iOS Safari, Android Chrome)
2. Se necessario, implementare touch drag con `touchstart`, `touchmove`, `touchend`
3. Oppure integrare libreria come SortableJS con opzione `handle`

---

## 👥 Filtro Utente nella Files Page

**Data aggiunta**: 20 Febbraio 2026  
**Status**: ⏳ IN ATTESA (richiede API backend)  
**Priorità**: Media  
**Dipendenza**: Endpoint `/api/v1/users` o `/api/v1/admin/users`

### Contesto
L'UploadedFile ha il campo `uploaded_by_user_id` ma non esiste un endpoint per risolvere gli ID utente in username/email. Serve per:
- Aggiungere colonna "Uploaded by" nella tabella files (come la colonna Broker in BRIM)
- Filtro dropdown per utente in modalità grid (accanto al search per nome)
- Badge colorati come nel BRIM (stessa funzione calcolo colori)

### Azione Futura
1. Creare endpoint backend `GET /api/v1/admin/users` (lista utenti, admin only)
2. Nel frontend, colonna utente visibile se `users.length > 1`
3. Filtro frontend-only con dropdown
4. Riutilizzare pattern filtri di `FilesTable`/`urlFilters`

---

## 🔒 Ripensare struttura di accesso ai broker Utente-SuperUtente per essere GDPR compliant

**Data aggiunta**: Gennaio 2026  
**Status**: 📋 PIANIFICATO → Architettura definita in `plan-phase05-to-08-upgrade.md` §10 (GDPR/Sharing)  
**Priorità**: Media

### Contesto
La visibilità dei dati di altri utenti da parte del superuser deve essere ripensata per essere GDPR compliant.

### Possibili Approcci
- Superuser non vede dati personali di altri utenti senza consenso esplicito
- Log di accesso ai dati di altri utenti
- Anonimizzazione dei dati visualizzati (solo statistiche aggregate)
- Meccanismo di "data request" invece di accesso diretto (utente concede accesso all'assistenza per x tempo)

---

## 📈 Asset Page — Prezzo e Transazioni

**Data aggiunta**: 20 Febbraio 2026  
**Status**: 📋 PIANIFICATO  
**Priorità**: Alta (Phase 6)

### Contesto
La pagina dell'asset dovrebbe mostrare il prezzo corrente in alto con la possibilità, cliccando su un punto del grafico, di aprire un'interfaccia piccola per modificare il valore di quel giorno. Sotto il grafico, per ogni transazione (slot per slot), mostrare il prezzo d'acquisto e la variazione rispetto ad oggi (guadagno/perdita), con uno storico del guadagno di quella transazione.

### Dettagli UI
- Prezzo in alto, editabile cliccando sul punto nel grafico
- Sotto: lista slot transazioni con prezzo d'acquisto, variazione %, storico
- Grafico ECharts con click-to-edit

---

## 🔄 Import Transazioni — Matching Asset

**Data aggiunta**: 20 Febbraio 2026  
**Status**: 📋 PIANIFICATO → Phase 6 §6.4 + Phase 7 §7.6 (vedi `plan-phase05-to-08-upgrade.md`)  
**Priorità**: Alta (Phase 7)

### Contesto
All'import delle transazioni (BRIM), per ogni riga deve essere ricercato un asset corrispondente. Se non viene trovato, all'utente viene chiesto di selezionare tra:
1. Asset già esistenti nel database
2. Asset trovati con query di ricerca ai vari provider plugin (yfinance, JustETF, etc.)

Se l'utente seleziona un asset da un provider esterno, deve essere creato automaticamente l'asset associato nel database.

### Flusso
```
Import riga → Cerca asset matching
  ├─ Trovato → Link automatico
  └─ Non trovato → Modale selezione:
       ├─ Asset esistenti
       ├─ Risultati ricerca provider
       └─ Creazione manuale
```

---

## 💱 FX Page — Grafico e Priorità Provider

**Data aggiunta**: 20 Febbraio 2026  
**Status**: 📋 PIANIFICATO  
**Priorità**: Alta (Phase 5)

### Contesto
La pagina dei tassi di cambio dovrebbe avere un grafico editabile come quello dell'asset:
- Click su un punto per modificare il valore di quel giorno
- Sotto il grafico, una tabella con le priorità dei provider (ECB, FED, BOE, SNB)
- Parametri configurabili per ciascun provider

---

## 📊 Aggiornamento Automatico Prezzi/FX

**Data aggiunta**: 20 Febbraio 2026  
**Status**: 📋 PIANIFICATO  
**Priorità**: Media

### Contesto
Sia per i prezzi degli asset che per i tassi di cambio, il grafico deve avere un pulsante per richiedere l'aggiornamento automatico dei valori. Nella finestra di dialogo:
- Scegliere un frame temporale di richiesta
- Warning che l'operazione sovrascrive tutti i valori attuali nel range
- Progress bar durante l'aggiornamento

---

## 🏦 Regime Fiscale — Metodo di Vendita (FIFO, LIFO, PMC, Select ID)

**Data aggiunta**: 20 Febbraio 2026  
**Status**: 📋 PIANIFICATO  
**Priorità**: Alta (architettura core)

### Contesto
Diverse giurisdizioni usano metodi diversi per determinare quale lotto vendere in caso di vendita parziale:
- **Italia**: Prezzo Medio di Carico (PMC)
- **USA**: FIFO, LIFO, Select ID (scelta specifica dell'utente)
- **Altre**: HIFO (Highest In First Out), etc.

### Requisiti
1. **Impostazioni Broker**: Nella zona short/long del broker, selettore per il metodo di vendita supportato (FIFO, LIFO, PMC, Select ID)
2. **Preferenze Utente**: Impostazioni di default per metodo di vendita
3. **Impostazioni Admin**: Default globale per nuovi utenti
4. **Collegamento Transazioni**: Il sell deve essere collegato ai buy tramite `link_transactions_id`:
   - FIFO/LIFO: collegamento algoritmico
   - Select ID: scelto dall'utente
   - PMC: nessun collegamento (calcolo on-the-fly)

### Note Tecniche
- Analizzare le strade per lo split dei buy: slittare buy e connettere la parte residua, tabella di appoggio, lista di link
- Deve essere possibile identificare transazioni già importate per evitare doppio import
- Per PMC il problema del collegamento non sussiste, basta calcolare il valore on-the-fly
- I plugin BRIM in fase di vendita devono fornire un dizionario di remap con le transazioni linkate più probabili
- Il vincolo di over-sell va esteso nell'import

---

## ✂️ Split Cash In/Out nelle Transazioni

**Data aggiunta**: 20 Febbraio 2026  
**Status**: 📋 PIANIFICATO  
**Priorità**: Media

### Contesto
L'import delle transazioni deve permettere di fare split nel cash-in e cash-out per tracciare le varie fonti dei soldi. A database lo split non deve far perdere la transazione padre (per evitare doppio import).

### Implementazione
- Tabella di supporto per legare le transazioni split
- UI: box unico dove le righe sono gli split
- In fase di creazione, i totali degli split devono rispettare quelli della transazione padre
- Anche in modifica questo vincolo deve essere mantenuto

---

## 📁 Import Multi-File Multi-Broker

**Data aggiunta**: 20 Febbraio 2026  
**Status**: 📋 PIANIFICATO  
**Priorità**: Alta (Phase 7)

### Contesto
Deve essere possibile parsare contemporaneamente più file, anche di diversi broker. L'interfaccia deve permettere di muoversi tra i vari fogli e impostare i collegamenti.

### Requisiti
- Pulsante "Check" per validare le regole e ottenere in risposta elenco di errori e warning
- Superamento soglie di check
- Navigazione tra fogli/broker

---

## 📉 Grafico Guadagni per Transazione

**Data aggiunta**: 20 Febbraio 2026  
**Status**: 📋 PIANIFICATO  
**Priorità**: Media (Phase 8)

### Contesto
Nel diagramma dei guadagni dalle varie transazioni:

- **Asse Y sinistra**: scala dei valori/percentuali dell'asset
- **Asse Y destra**: scala di guadagno/perdita delle singole transazioni di buy
- Per ogni evento di buy, un nuovo grafico parte da 0 in y a quella data
- Una linea con area che rappresenta la sommatoria cumulativa dei guadagni
- Evento di vendita + tasse + commissione: doppia freccia verso il basso (da definire)

### Sotto al Grafico
- Tabella con i buy in ogni riga
- Colonne: valore attualmente investito
- Sotto: barra con valore stimato + guadagnato
- Deve distinguere tra valore potenziale e realizzato (vendite parziali/totali)
- Selettore metodo di analisi (FIFO, LIFO, PMC, etc.)

---

## 🤖 QuarkAI — Assistente AI (MCP Server)

**Data aggiunta**: 20 Febbraio 2026  
**Status**: 📋 PIANIFICATO  
**Priorità**: Bassa (futuro)

### Contesto
Creare un assistente AI basato su MCP server chiamato "QuarkAI".

### Funzionalità Future
- Raccolta automatizzata notizie mercati azionari
- Notifiche su Telegram (o simili) quando rileva eventi che richiedono attenzione
- Recap giornaliero (es. alle 20:00) con sommario eventi rilevanti

---

## 📁 Template per Nuovi TODO

```markdown
## 📌 [Titolo]

**Data aggiunta**: [Data]  
**Status**: [⏳ IN ATTESA | 📋 PIANIFICATO | 🔄 IN CORSO | ✅ COMPLETATO]  
**Priorità**: [Alta | Media | Bassa]

### Contesto
[Descrizione del problema o motivazione]

### Azione Futura
[Passi da eseguire quando sarà il momento]

### Riferimenti
[Link a documentazione, issue, PR]
```

---

## 🖼️ Client-side Image Preview Cache (LazyImage)

**Data aggiunta**: 23 Febbraio 2026  
**Status**: 📋 PIANIFICATO  
**Priorità**: Media

### Contesto

Quando si passa dalla modalità **griglia** (preview 120x120) alla modalità **lista** (preview 48x48) nella pagina files, il browser fa nuove richieste al backend per le stesse immagini a risoluzione inferiore. Questo succede perché le URL sono diverse (`?img_preview=120x120` vs `?img_preview=48x48`).

Sarebbe più efficiente riutilizzare la risorsa già caricata a risoluzione maggiore e lasciare al browser il ridimensionamento CSS, evitando chiamate network ridondanti.

### Azione Futura

1. Creare un **Map globale** lato client (`imagePreviewCache: Map<fileId, {maxSize: number, objectUrl: string}>`)
2. Nel componente `LazyImage`, prima di fare fetch, controllare se il fileId è già in cache a risoluzione >= quella richiesta
3. Se sì, usare l'objectUrl già disponibile e fare `object-fit: cover` CSS
4. Se no, fare la richiesta normale e salvare in cache
5. Gestire la pulizia cache con `URL.revokeObjectURL()` quando i componenti vengono distrutti
6. Eventuale Service Worker per intercettare le richieste `?img_preview=` e servire versioni cached

### Note

- La cache backend (50MB, TTL 1h) già mitiga il problema server-side
- Questa ottimizzazione è puramente client-side per evitare roundtrip network
- Valutare l'impatto su memoria del browser se molte immagini sono in griglia

---

### 📊 Aggiungere al componente Linea altri stili della line al segnale

Oltre l'attuale visualizzazione a segmenti spezzati, indagare se si possono mostrare le linee anche come spilne smoot, ed in quanti modi, e se si, renderlo un parametro estetico configurabile

---

### 📊 Grafico Asset con rendimento a N
Con i dati degli asset ha senso mostrare i grafici oltre che per abs e % da P0, anche il rendimento a N (anni o giorni, parametrico) con il significato che ogni punto rappresenta il guadagno/perdita di valore percentuale dell'asset se vosse stato comprato N giorni prima e venduto nel giorno attuale.
Questo da applicare sia all'asset principale che a quelli di confronto messi nel grafico, da mettere nella pagina di detail per le analisi di dettaglio.

---

## 🪵 Riorganizzazione livelli di log backend

**Data aggiunta**: 12 Marzo 2026  
**Status**: ⏳ Da fare  
**Priorità**: Media

Analizzare tutti i log generati dal backend e riorganizzarli in una struttura sensata con livelli appropriati. Attualmente i log del servizio FX (sync, backfill, convert) usano livelli inconsistenti:
- Log informativi di routine (es. "Syncing FX rates...") sono a INFO ma dovrebbero essere a DEBUG
- I log di backward-fill ripetitivi sono già stati spostati a DEBUG/livello 5, ma servono ulteriori verifiche
- I log di sync per singola coppia/currency generano molto output anche a INFO

**Azione**: Fare un audit completo dei livelli di log (DEBUG, INFO, WARNING, ERROR) in tutto il backend, definire una policy chiara e applicarla uniformemente.

---

## 📚 Documentazione Per-Plugin FX Provider

**Data aggiunta**: 15 Marzo 2026  
**Status**: 📋 PIANIFICATO  
**Priorità**: Bassa

### Contesto
Attualmente esiste solo una pagina generica che elenca tutti i provider FX:
- `/mkdocs/developer/backend/fx/providers_list/`

Ogni provider (ECB, FED, BOE, SNB) dovrebbe avere una **pagina dedicata** nella documentazione MkDocs con:
- Descrizione dettagliata del provider
- URL dell'API sorgente e formato dati
- Base currency e valute supportate
- Frequenza di aggiornamento (giornaliera vs mensile)
- Eventuali limitazioni note (es. SNB solo mensile, nessun dato giornaliero)
- Parametri di configurazione
- Esempio di risposta API

### Azione
1. Creare una pagina MkDocs per ogni provider in `mkdocs_src/docs/developer/backend/fx/providers/`
2. Aggiornare la property `docs_url` in ogni provider per puntare alla pagina specifica
3. Il frontend già usa `docs_url` per il link nell'info bar del FxProviderSelect (cliccando sull'icona del provider)

---

## 📊 CandlestickChart / VolumeBar — Phase 6 (Assets)

**Data aggiunta**: 16 Marzo 2026
**Status**: 📋 PIANIFICATO
**Priorità**: Media (Phase 6)

### Contesto
Per FX si hanno solo close rate giornalieri — non esiste OHLC reale.
CandlestickChart e VolumeBar saranno implementati quando avremo dati OHLC
reali dagli asset source provider (yfinance, JustETF).

### File
- `frontend/src/lib/components/charts/CandlestickChart.svelte` (stub)
- `frontend/src/lib/components/charts/VolumeBar.svelte` (stub)

### Note
- Per FX il toggle Line/Candlestick resta disabilitato (`disableCandlestick={true}`)
- L'OHLC sintetizzato (O=prev close) non ha valore informativo per FX



## Ripulire tutte le traduzioni non usate con i18n prima di aggiungere nuove lingue

**Status**: ⏳ DA FARE  
**Nota**: Lo Step 2 del `plan-fxTestingCleanup.prompt.md` ha tradotto alcune stringhe hardcoded (MeasurePanel, FxDetail, BrokerDetail), ma la pulizia completa delle 146+ chiavi potenzialmente non usate e la razionalizzazione delle categorie NON è stata eseguita.

**Attività pendenti**:
1. Verificare e poi eliminare le chiavi che il tool da noi scritto crede non siano usate da i18n (distinguendo falsi positivi da chiavi davvero morte)
2. Fare un lavoro di razionalizzazione delle chiavi, dividendole per categorie, eliminando quelle completamente sovrapponibili e duplicando, se serve, quelle che compaiono in parti di codice completamente diverse
3. Cercare tutte le frasi hardcodate nel codice e trasformarle in traduzioni
   - System Broker creation (backend)
   - Eventuali altre stringhe trovate con grep
