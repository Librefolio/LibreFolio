# Piano generale — fase 01: la 1.3.0 «Cloud-ready core», con un riordino del codice in testa

> **Approvato dal developer il 14/10/2026** (sessione del coordinatore della 1.3, «Release 1.3
> planning»). È il piano generale della fase: lo stato vivo delle sessioni e delle funzioni
> sta nel [README della fase](README.md); il lavoro rimasto dopo la 1.2, voce per voce, in
> [`BACKLOG_POST_1.2.md`](../Phase_0/BACKLOG_POST_1.2.md), dove ogni sessione della 1.3 ha
> la sua sezione.
>
> Fonti: la lista delle funzioni per il cloud (dal repo business: «Feature SaaS Readiness»,
> «Decisioni Aperte», «Piano Operativo», prompt «Milestone v1.3 Cloud-ready core»),
> `Release_2/Phase_0/BACKLOG_POST_1.2.md`, i piani di `Phase_0` (43, 45, 13, 02, 21, 09,
> 53, 55, 56), `TODO_FUTURI.md`, 4 audit del codice in sola lettura (14/10).
>
> Le sigle fra parentesi (F26, PL2, C-79…) servono solo a ritrovare la voce nelle fonti.

## 1. Obiettivo e criterio di rilascio

- **Obiettivo**: rendere possibile LibreFolio Cloud (un'istanza per cliente, stessa
  immagine Docker pubblica, SQLite per istanza, sospensione quando nessuno la usa, backup
  continuo, pannello di controllo privato fuori da questo repo) senza codice «solo cloud»:
  ogni funzione serve anche al self-hosted, ogni variabile nuova ha un default che lascia
  il comportamento attuale, ogni segreto accetta anche la variante `*_FILE`.
- **Prima di tutto un riordino del codice** (decisione del developer, 14/10): tutto il
  riordino del piano 43 (parte 2), backend e frontend, compresi i file più grandi, così
  che le molte sessioni parallele lavorino su cartelle chiare e separate.
- **Si rilascia quando le ondate 1 e 2 sono complete e verdi** (decisione del developer).
  Nessuna data: le stime del business plan sono prudenti e non vincolano.
- **Perimetro del backlog** (decisione del developer): errori che toccano numeri,
  sicurezza o dati, e chiarezza per utenti non esperti. I riordini interni sono dentro
  per scelta esplicita (ondata 0). Dentro anche i `TODO_FUTURI` che vengono facili.

## 2. Stato di partenza (verificato sul codice il 14/10)

| Funzione | Cosa c'è oggi |
|---|---|
| Pausa degli aggiornamenti automatici (F26) | 3 cicli: lista asset 30 s, dettaglio asset 30 s e 60 s; solo uno rispetta la scheda nascosta. Nessun concetto di inattività nel backend |
| Segreti e configurazione (F03) | Segreto di login casuale a ogni avvio se manca (`auth_service.py:104`, scelta consapevole del fondatore: resta). Nessun `*_FILE`. `.env.example` incompleto. Nessun avviso di configurazione non sicura |
| Prontezza e versione (F08) | Solo `/system/health`; la logica della revisione del DB esiste in `main.py` |
| Profilo gestito (F05) | Assente. Popup di donazione spegnibile solo con una variabile nascosta. Nessun interruttore per i fornitori |
| Disclaimer e link legali (F09) | Assenti; non esiste un footer |
| Admin iniziale (F02) | «Il primo che si registra diventa admin» (`auth.py` ~205-238) |
| Inviti e utenti (F13) | Solo `enable_registration` (sì/no); nessuna API né UI di gestione utenti; reset password solo da CLI |
| Email (F04) | Nessun codice email |
| Backup e ripristino (F01) | `/backup/export` e `/backup/restore` rispondono 501 (`api/v1/backup.py:128,146`) |
| Litestream (F25) | Assente; il DB è già in WAL con attesa di 30 s |
| Avvio e risveglio (F07) | Lo scheduler è un ciclo asyncio proprio (giro di 60 s); avvio sequenziale; lo spegnimento non ha un tempo massimo (C-49) |
| Impostazioni dei plugin («⚙️» di `TODO_FUTURI`) | Assenti: nessun posto per chiavi o preferenze dei plugin; nessuna cifratura; `cryptography` non è fra le dipendenze |
| Ordine dei fornitori nella ricerca (F21) | Nessuna priorità: i risultati arrivano in ordine di risposta |
| Cache del frontend (F28) | Già fatta (`main.py:473-480`); resta un dettaglio |
| Limite tentativi di login e header di sicurezza (F15) | Assenti |

## 3. Le ondate

### Ondata 0 — Riordino (tutto il piano 43, parte 2) e punti d'aggancio per il cloud

Ogni sessione riordina **il proprio dominio** prima di costruirci sopra: così nessuno
sposta file che un altro sta modificando. Regole del piano 43: prima la rinomina, poi il
taglio, in due commit; niente shim né barili nuovi; URL, `operationId`, chiavi i18n e
`data-testid` invariati; lotti piccoli, integrati in fretta.

- **Backend**: un registro per famiglia di plugin (PL2) · asset senza shim (PL6) · cambi
  in `services/fx/` (PL4) · import broker in `services/brim/` con icone e report di esempio
  nelle cartelle dei plugin (PL5, U-B3, U-B4) · runtime dei segnali in `services/signals/`
  e fine del ciclo con il rischio (PL1) · router dei segnali (PL7) · router di asset, cambi
  e broker divisi per risorsa · file grandi divisi (evaluator del PAC, sorgente del PAC,
  servizio del rischio, transazioni, broker, prezzi, schemi per dominio, portafoglio dopo
  la sua matematica) · servizi raggruppati per dominio (`accounts/`, `platform/`, `files/`,
  `assets/`, …).
- **Punti d'aggancio nuovi per il cloud** (non nel piano 43): avvio e middleware fuori da
  `main.py`, un modulo di configurazione unico con i segreti, una configurazione pubblica
  dell'istanza letta dal frontend, un'area di avvisi d'istanza nel layout.
- **Frontend**, con il calendario del programma colori (corretto da loro il 14/10, §7).
  **Fino al merge del lotto che li elenca, i file della fattorizzazione dei colori (R) non
  si spostano né si modificano.**
  - subito: `features/auth`, `features/settings`, `features/support` e le cartelle che R
    non tocca;
  - dopo il lotto A dei colori (trasparenze, segni, stati e badge; parte ora): cambi
    (FE4), asset con il taglio di `AssetModal` e della pagina dell'asset (FE5),
    transazioni con il wizard di import diviso per passo (FE8), `ui/feedback`,
    `ui/display`, ritocchi in `features/tools`;
  - dopo il lotto B (grafici): segnali e rischio (FE2), dashboard con `GrowthChart`
    tagliato (FE6), broker e lotti (FE7);
  - dopo il lotto C (tabelle, media, file, dialoghi): file (FE3), `DataTable`;
  - dopo il lotto D: la pagina dei file, `ImportBrokerMismatchModal`,
    `BrokerImportFilesModal`, `CompactCashCell`;
  - per ultimi: utility e store generici (FE9, FE10), suffissi (FE11).
- **Test speculari al codice (TS1)**: si decide a riordino del backend finito (costo alto).

### Ondata 1 — Fondamenta per il cloud (bloccano il pannello di controllo)

Segreti e configurazione (F03) · prontezza e versione (F08) · profilo gestito (F05) ·
disclaimer e link legali (F09) · admin iniziale da variabili (F02) · inviti, modalità di
registrazione e gestione utenti (F13) · pausa degli aggiornamenti e sospensione (F26).
**La pausa degli aggiornamenti parte subito**, prima del riordino: è piccola e urgente.

### Ondata 2 — Dati al sicuro, email, risveglio, plugin

Email facoltativa (F04) · backup e ripristino dalla UI (F01) · backup continuo con
Litestream (F25) · avvio, aggiornamento all'accesso e risveglio (F07) · **impostazioni dei
plugin** per tutte le famiglie, con l'analisi dei rischi delle chiavi · ordine dei
fornitori nella ricerca (F21).

### Ondata 3 — Fornitore di prezzi a pagamento (F06)

Solo quando il fornitore è scelto: diventa un plugin che usa le impostazioni dei plugin.
Non blocca il rilascio.

### In parallelo dall'inizio — numeri giusti, sicurezza, chiarezza

Unificazioni della matematica finanziaria (U1–U10) con i loro bug, difetti di integrità e
sicurezza, testi e messaggi per utenti non esperti: ognuno dentro la sessione che possiede
quel dominio (§4).

### Se c'è spazio

Header di sicurezza con CSP applicata (oltre alla sola segnalazione) · README e
posizionamento «self-hosted oppure gestito in UE» (F16) · immagini anche arm64 (M-1) ·
«Novità dalla tua ultima versione» al login (C-54) · indicatore di attesa del server
(C-85) · frontend di sola presentazione (U8) · test speculari (TS1).

### Fuori dalla 1.3

OIDC, 2FA, snapshot con retention, heartbeat, Data Hub, MCP, notifiche, export per utente,
accesso di supporto, condivisione, token API personali, immagine leggera (dalla 1.4) · il
plugin del fornitore a pagamento finché non è scelto · i lotti di test del PAC (A–C) e il
Rebalancer · le voci di funzionalità del Rischio (A1–A6, B1–B8) · il passaggio di Python.

## 4. Le sessioni (workstream)

Una sessione = un ramo, un worktree, un perimetro, una corsia. Lettere scelte per non
collidere con il programma colori (L, R, G attive; T, C, U, S, P riservate) né con le
sezioni del backlog post-1.2. Corsie: coordinatore 6180 + `/tmp/librefolio-r13-main`;
figli 6181–6189 + `/tmp/librefolio-r13-<lettera>` (confermate dal coordinatore colori,
che usa 6150–6154 e 6160). Piani in `Release_2/Phase_1/<NN_nome>/plan-phase01<Nome>.prompt.md`.

| Lettera | Nome della sessione | Corsia | Piano | Quando parte |
|---|---|---|---|---|
| H | H - Piattaforma | 6181 | `01_platform/plan-phase01Platform.prompt.md` | subito |
| A | A - Account e accessi | 6182 | `02_accounts/plan-phase01Accounts.prompt.md` | subito |
| X | X - Plugin asset e ricerca | 6183 | `03_pluginsAssets/plan-phase01PluginsAssets.prompt.md` | subito |
| W | W - Import e transazioni | 6184 | `04_importTransactions/plan-phase01ImportTransactions.prompt.md` | subito |
| J | J - Numeri e analisi | 6185 | `05_numbersAnalysis/plan-phase01NumbersAnalysis.prompt.md` | subito |
| Z | Z - Sospensione e risveglio | 6186 | `06_sleepWake/plan-phase01SleepWake.prompt.md` | subito |
| B | B - Backup e Docker | 6187 | `07_backupDocker/plan-phase01BackupDocker.prompt.md` | dopo il primo checkpoint di H (configurazione e segreti) |
| E | E - Email | 6188 | `08_email/plan-phase01Email.prompt.md` | dopo il checkpoint di A con token e inviti |
| Y | Y - Cruscotto e grafici | 6189 | `09_dashboardCharts/plan-phase01DashboardCharts.prompt.md` | dopo il lotto B del programma colori |

Si parte con 6 sessioni (indicazione del developer), poi si sale fino a 9.

### H · Piattaforma

1. Riordino: `services/platform/` (scheduler, container registry, sentinella delle date,
   soglie di qualità dati, servizio di backup), `services/files/` (upload statici,
   anteprime); avvio e registrazione dei middleware fuori da `main.py`; modulo di
   configurazione unico che raccoglie le letture sparse delle variabili d'ambiente.
2. Segreti e configurazione (F03): lettura `NOME` → `NOME_FILE` → default; cartella
   `<DATA_DIR>/secrets/` con la chiave d'istanza creata una volta (permessi 600,
   creazione atomica); `JWT_SECRET_FILE`; `.env.example` completo, diviso in sezioni per
   funzione; avvisi di configurazione non sicura nei log e per l'admin.
3. Configurazione pubblica dell'istanza (endpoint letto all'avvio del frontend) e area
   degli avvisi d'istanza nel layout: le altre sessioni vi registrano i loro avvisi senza
   toccare il layout.
4. Prontezza e versione (F08), con le versioni scritte a mano (C-84) e il file `VERSION`
   stantio (R2, decisione: §10).
5. Profilo gestito, parte di piattaforma (F05): l'interruttore e la sola lettura
   (middleware con elenco di eccezioni, avviso, messaggi chiari).
6. Lotto operativo: fuso orario IANA nell'immagine (P-4), frontend vecchio in una build
   Docker locale (M-25), porta 6041 pubblicata a vuoto (C-37), `PORT` che entra nel
   container (N-8), `docker exec` come root (32-3), tag `test` nel registro (C-26),
   dettaglio della cache del frontend (F28), timeout dei worker di rischio documentati e
   più corti nel profilo gestito (F27), header di sicurezza con CSP in sola segnalazione
   (F15).
7. A riordino del backend finito: decisione sui test speculari (TS1), che toccherebbe H.

### A · Account e accessi

1. Riordino: `services/accounts/` (autenticazione, utenti, impostazioni, impostazioni
   globali, onboarding, popup di donazione); frontend `features/auth/`, `features/settings/`
   (con un registro delle schede che useranno anche B e X), `features/support/`.
2. Admin iniziale da variabili (F02), con la registrazione che resta aperta senza utenti
   anche se chiusa (K-5).
3. Modalità di registrazione `disabled|invite|open`, inviti, gestione utenti dalla UI,
   link di reset, limite utenti (F13 e la parte di F05); cambio o reset della password
   che chiude le sessioni aperte (`TODO_FUTURI`, «🔑 Sessioni»); reset dell'onboarding
   dall'admin (21-5); limite di tentativi di login (F15).
4. Profilo gestito, parte account (F05): niente popup di donazione né avvisi di
   aggiornamento; link «Gestisci abbonamento» e «Supporto».
5. Disclaimer e link legali (F09): onboarding, login e registrazione, Impostazioni ›
   Informazioni, riga nell'output dell'AI Export (modello del frontend).
6. Testi e igiene: errori di rete al login in inglese (O-15), occhio della password
   (K-17), utenti E2E creati admin (L12). Se c'è spazio: «Novità dalla tua ultima
   versione» (C-54).
7. Migrazione Alembic 005 (token e inviti, modalità di registrazione, versione del
   token di sessione, `email_verified_at` già pronto per E).

### X · Plugin, asset e ricerca

1. Riordino: un registro per famiglia (PL2), **per primo e integrato subito** perché
   tocca tutte le famiglie; asset senza shim (PL6); `fx.py` → `services/fx/` (PL4);
   `services/assets/` raggruppato; `price_store` in tre moduli; router di asset e cambi
   per risorsa e router dei segnali (PL7, dopo PL1 di J); frontend cambi (FE4) e asset
   con i tagli di `AssetModal` e della pagina dell'asset (FE5): entrambi **dopo il lotto
   A dei colori** e dopo la pausa degli aggiornamenti di Z su quelle pagine.
2. Elenchi dei fornitori permessi (F05, parte X): asset e cambi, scraper spenti di
   default nel profilo gestito.
3. **Impostazioni dei plugin** (idea «⚙️» di `TODO_FUTURI`, decisione del developer):
   - ogni famiglia (prezzi, cambi, import broker, strumenti) può dichiarare dei campi;
     **ogni campo dichiara se è personale o di sistema** (di sistema = solo admin) e se è
     segreto;
   - Impostazioni costruisce da sola una zona per plugin; nel pannello del fornitore in
     «Aggiungi asset» un pulsante «Configura»;
   - valori nel DB, i segreti cifrati con la chiave d'istanza; una variabile d'ambiente
     o `*_FILE` vince e blocca il campo; nel profilo gestito il campo è bloccato e
     invisibile; l'API non restituisce mai un segreto;
   - **prima del codice, un'analisi dei rischi scritta** (cosa protegge la cifratura e
     cosa no: chiave d'istanza sullo stesso volume, backup che contengono entrambi,
     log, AI Export, admin che non deve leggere i segreti personali, rotazione), poi una
     revisione di sicurezza a fine lavoro;
   - primo uso: justETF e Borsa Italiana con paese e valuta preferiti (feedback
     dell'utente C); traduzioni dei plugin montati a runtime se servono (U-B1);
   - migrazione Alembic 006; dipendenza nuova `cryptography` (finestra delle dipendenze,
     §6).
4. Ordine dei fornitori nella ricerca (F21): priorità e livello (premium, community)
   dichiarati dal plugin e sovrascrivibili; premium in testa con badge; «Non lo trovi?
   Segnalacelo» e «Prezzo manuale / import»; sezione chiusa «Fonti non premium» con
   avviso alla prima attivazione per asset. Con la nota di «Testa configurazione» (C-90).
5. Voci del dominio: filtri persi tornando alla lista (K-19), date ripristinate
   cambiando scheda (K-20), doppio sync alla creazione (O-20), testi inglesi nell'editor
   dei dati (O-8), parametri di justETF senza traduzione (O-9), avviso prima che un sync
   sovrascriva (C-66), link alle transazioni dalla modale di cancellazione, ETC/ETN di
   Borsa Italiana (K-16).

### W · Import e transazioni

1. Riordino: `brim_provider.py` e i suoi file → `services/brim/` (PL5), con icone e
   report di esempio dentro le cartelle dei plugin (U-B3, U-B4); transazioni (servizio,
   stadi del batch, contesto) → `services/transactions/`; broker → `services/brokers/`;
   router dei broker per risorsa; schemi delle transazioni; frontend transazioni (FE8),
   **dopo il lotto A dei colori**: wizard di import diviso per passo, modali Bulk e Form
   divise per sezione; i 4 file del lotto D dei colori solo dopo quel lotto.
2. Integrità e sicurezza: cancellazione di eventi per id fuori dall'asset (I-12), errore
   500 su un tipo di evento non valido (I-09), «+ Nuovo evento» che modifica un evento
   esistente (V-22), bulk editor e broker in sola lettura (V-23), file letti sull'event
   loop (L5), lock e cartelle vuote dopo la cancellazione di un broker (C-79, C-3).
3. Chiarezza: rifiuti dei plugin di import solo in inglese (C-70), plurale del wizard
   (O-12), le due date del cambio valuta (C-89), etichette inglesi (P-15), percentuali
   non localizzate (P-13), «broker» in spagnolo (P-14), messaggi del modulo (V-37,
   V-38), suggerimento degli eventi collegabili nel bulk (`TODO_FUTURI`, backend già
   fatto), collegamento evento → transazione (C-65).

### J · Numeri e analisi

1. Riordino backend: runtime dei segnali e fine del ciclo con il rischio (PL1, insieme
   all'unificazione dei rendimenti U4), servizio del rischio diviso, preparazione delle
   serie divisa, portafoglio in `services/portfolio/` (dopo U4), sorgente del PAC in
   `pac_allocator/source/`, evaluator del PAC in `pac_allocator/evaluation/`, schemi di
   PAC, rischio, portafoglio e segnali per dominio.
2. Unificazioni della matematica finanziaria (U1–U10; l'ordine lo propone l'analisi),
   con i bug collegati: data del lotto più vecchio dopo uno split (T-B4 con U6), P&L FIFO
   con valute miste (T-B5, decisione), fonte del prezzo «exact» (T-B6), colonne nulle e
   sintesi FIFO dell'AI Export (T-B7, T-B8), residuo sotto l'unità (T-B9), prezzo dei
   contributi (B8), giorni «dirty» e cambi (B11), custodia calcolata due volte (B15),
   TRANSFER orfano (V-3), messaggio «nessun prezzo da 2 settimane» (V-11), SPLIT
   riclassificato (P-10, decisione), costo medio dei trasferimenti (C-33, da verificare).
3. Difetti piccoli del PAC: percentuali con pareggi (C-73), aiuto di «Value after the
   plan» (C-74), «-0» del solutore (C-75), controlli di segno e zero (C-76).
4. Due «Rolling Return» con lo stesso nome (C-71).

### Z · Sospensione e risveglio

1. **Subito**: un solo aiuto di polling per tutti i cicli, fermo a scheda nascosta e
   dopo ~10 minuti senza input, avviso «Aggiornamento in pausa», aggiornamento immediato
   alla ripresa (F26, frontend), sulle pagine di oggi.
2. Dopo i punti d'aggancio di H: tracciamento dell'attività dell'utente (esclusi
   controlli di salute e polling) e sospensione richiesta a Fly dall'interno (F26,
   backend).
3. Avvio veloce, recupero dei prezzi in background con «Aggiornamento prezzi…»,
   `POST /system/wake-sync` con token, `next_wake_at`, jitter e attesa crescente sui
   429, spegnimento con tempo massimo (F07, C-49). Dopo lo spostamento dello scheduler
   fatto da H, lo scheduler è di Z.

### B · Backup e Docker

1. Backup e ripristino dalla UI e da CLI (F01): zip coerente con manifest; ripristino con
   controllo della revisione, prova su copia, backup automatico prima, scambio applicato
   all'avvio prima delle migrazioni, uscita per il riavvio; scheda Backup per l'admin;
   guida «Porta il tuo LibreFolio a casa».
2. Litestream nell'immagine, spento di default (F25), coordinato con il ripristino.
3. Facoltativo: immagini anche arm64 (M-1). I file Docker passano da H a B dopo il lotto
   operativo di H.

### E · Email

1. Email facoltativa via SMTP (F04): configurazione solo da variabili o file, limite di
   invii, modelli nelle 4 lingue, «email di prova» per l'admin.
2. Password dimenticata, inviti via email, verifica dell'email, sui token di A.

### Y · Cruscotto e grafici

Parte quando il programma colori integra il suo lotto B: segnali e rischio (FE2),
dashboard con `GrowthChart` tagliato (FE6), broker e lotti (FE7); frontend di sola
presentazione (U8) con i campi del backend di J; indicatore di attesa del server (C-85);
bandiere nei grafici (K-13); tooltip sanificati (K-15, C-34, C-15); voci dei grafici
(I-01, I-03, 47-1, 54-1, B10, 48-1, O-16). Dopo il lotto C dei colori: file (FE3),
`DataTable` tagliata, intestazione Azioni su mobile (C-38 e difetti 2 e 5 del PAC),
ridimensionamento delle colonne (C-62). Per ultimi FE9, FE10, FE11. **Il riordino delle
cartelle toccate dai colori non blocca il rilascio**: se i lotti B e C arrivano tardi,
quella parte passa dopo la 1.3.

## 5. Schede delle funzioni per il cloud

Per il piano generale nel journal. Peso relativo: piccolo, medio, grande. Righe di codice
dall'audit del 14/10: ogni sessione le riverifica nell'analisi.

| Funzione | Sessione | File principali | Migrazione | Variabili nuove (default = come oggi) | Test | Peso |
|---|---|---|---|---|---|---|
| Pausa degli aggiornamenti e sospensione (F26) | Z | aiuto di polling nuovo; le pagine lista e dettaglio asset; tracciamento attività e sospensione nella piattaforma | no | `LIBREFOLIO_IDLE_SUSPEND_MINUTES` (0 = spento), `LIBREFOLIO_IDLE_SUSPEND_MODE=none\|fly`, minuti di inattività del client | Vitest con timer finti; pytest su esclusioni, orologio finto, socket Fly finto | medio-piccolo |
| Segreti e configurazione (F03) | H | `config.py` e modulo segreti, `auth_service.py`, `web_link_finder.py`, `.env.example`, doc admin `configuration` | no | `JWT_SECRET_FILE`, `*_FILE` per ogni segreto, chiave d'istanza (`LIBREFOLIO_INSTANCE_KEY(_FILE)` o file generato) | precedenza, permessi, file mancante → errore chiaro | piccolo-medio |
| Prontezza e versione (F08) | H | `api/v1/system.py`, servizio di prontezza estratto da `main.py` | no | `LIBREFOLIO_METRICS_ENABLED` (spento) | pytest pronto / non pronto | piccolo |
| Profilo gestito (F05) | H, A, X | interruttore e sola lettura (H); popup, aggiornamenti, link, limite utenti (A); elenchi dei fornitori (X) | no | `LIBREFOLIO_PROFILE`, `LIBREFOLIO_ASSET_PROVIDERS_ALLOWED`, `LIBREFOLIO_FX_PROVIDERS_ALLOWED`, `LIBREFOLIO_BILLING_URL`, `LIBREFOLIO_SUPPORT_URL`, `LIBREFOLIO_MAX_USERS`, `LIBREFOLIO_READ_ONLY` | pytest per ogni default e per la sola lettura su ogni metodo; Vitest dei link; E2E dell'avviso | medio |
| Disclaimer e link legali (F09) | A | onboarding, login e registrazione, Informazioni, modello dell'AI Export | no | `LIBREFOLIO_TOS_URL`, `LIBREFOLIO_PRIVACY_URL` | Vitest; controllo del testo nell'export | piccolo |
| Admin iniziale (F02) | A | servizi account, `auth.py`, pagina `/setup` | no | `LIBREFOLIO_ADMIN_EMAIL`, `LIBREFOLIO_ADMIN_USERNAME` (admin), `LIBREFOLIO_ADMIN_BOOTSTRAP_TOKEN(_FILE)` | pytest: idempotenza, token monouso e scaduto | piccolo |
| Inviti e utenti (F13) | A | servizi account, router utenti admin, scheda Utenti, pagina d'invito | sì (005) | `LIBREFOLIO_REGISTRATION=disabled\|invite\|open` | pytest del ciclo di vita dei token; Vitest; E2E invito → registrazione e reset | medio-grande |
| Email (F04) | E | servizio email nuovo, modelli nelle 4 lingue, flussi di A | no (campi già in 005) | `LIBREFOLIO_SMTP_HOST`, `_PORT`, `_USER`, `_PASSWORD(_FILE)`, `_FROM`, `_TLS`, limite di invii | server SMTP finto; E2E del reset | medio |
| Backup e ripristino (F01) | B | servizio di backup, `api/v1/backup.py` (oggi 501), avvio (ripristino in attesa), CLI, scheda Backup, guida | no | limite di caricamento per il ripristino; eventuale token per scaricare i backup (§10) | pytest: andata e ritorno, revisione vecchia e nuova, percorsi nell'archivio; E2E stessi totali | grande |
| Litestream (F25) | B | `Dockerfile`, `entrypoint.sh`, doc Docker avanzato | no | destinazione della replica, credenziali (`_FILE`), chiave SSE-C facoltativa | prova Docker con replica su cartella o S3 locale; SIGTERM attraverso la catena | medio |
| Avvio e risveglio (F07) | Z | scheduler, avvio, `wake-sync`, stato «Aggiornamento prezzi…» | no | `LIBREFOLIO_WAKE_TOKEN(_FILE)`, jitter, attesa sui 429, tempo massimo di spegnimento | pytest del prossimo orario (fusi e ora legale), spegnimento entro il limite; E2E dello stato | medio |
| Impostazioni dei plugin | X | contratti delle famiglie, archivio delle impostazioni, API, zona in Impostazioni, «Configura» | sì (006) | sovrascritture per campo da variabile o `*_FILE` | pytest: scope, cifratura, segreti mai restituiti, blocco da env; Vitest del modulo generato; E2E | grande |
| Ordine dei fornitori (F21) | X | contratto dell'asset, ricerca in streaming, `AssetSearchAutocomplete`, `AssetModal` | no | eventuale priorità da configurazione | pytest dell'ordine; Vitest dei gruppi; E2E della ricerca | medio |

## 6. Regole comuni

### Git (regole del 14/10)

- **Il coordinatore gestisce il git locale** di tutte le sessioni della 1.3: commit dei
  checkpoint (dopo `FROZEN`, solo percorsi rivisti), aggiornamenti di base (target → figlio),
  integrazione finale (figlio → `dev_release2`). **La push la fa il developer**, quando
  vuole. I figli non toccano mai la storia.
- **Checkout condiviso con il coordinatore colori** (protocollo concordato il 14/10):
  percorsi espliciti e propri in ogni commit, mai `git add -A`; avviso reciproco prima di
  ogni merge, rebase o reset di `dev_release2`; file modificati altrui → non si toccano,
  si scrive all'altro. Prima e dopo ogni operazione: HEAD e `git status --porcelain`
  registrati.
- **Sessioni nuove**: nascono da `origin/dev_release2`; se la base locale è avanti (oggi di
  6 commit, in attesa di push), subito `git -C <figlio> merge --ff-only <base>` e verifica.
- **Integrazione senza conflitti nel checkout condiviso**: prima si aggiorna la base del
  figlio (i conflitti si risolvono nel suo worktree), poi il merge in `dev_release2`.

### Superfici condivise: un solo scrittore

| Superficie | Scrittore |
|---|---|
| `main.py`, modulo di configurazione, `system.py`, area avvisi e `routes/(app)/+layout.svelte` | H (la riga di L in `routes/+layout.svelte` è già concordata) |
| `.env.example` | H crea le sezioni per funzione; ogni sessione riempie solo la sua |
| `provider_registry.py` e contratti delle famiglie | X |
| Scheduler | H lo sposta, poi è di Z |
| Registro delle schede di Impostazioni | A; B e X aggiungono la loro scheda con una riga |
| File Docker | H fino al lotto operativo, poi B |
| Catena delle migrazioni Alembic | ordine assegnato dal coordinatore: 005 A, 006 X; chi integra dopo rimette `down_revision` all'aggiornamento di base |
| Client API generato | rigenerato con `./dev.py api sync` da chi integra, mai unito a mano |
| Cataloghi i18n | ognuno scrive solo le sorgenti del proprio sottosistema; i cataloghi generati si ricostruiscono |
| Catalogo del runner dei test | ognuno le voci del proprio dominio, in aggiunta; i test speculari (TS1), se decisi, a H |
| Navigazione MkDocs, `CHANGELOG.md` (`[Unreleased]`), piano generale in `Phase_1` | coordinatore (i figli propongono il testo nel loro handoff) |
| `BACKLOG_POST_1.2.md` | ogni sessione 1.3 scrive solo la propria sezione; le chiusure (✅ con data e commit) delle voci di altre sezioni e i rimandi nei piani d'origine di `Phase_0` li scrive il coordinatore a ogni treno; le sezioni L/R/G sono del coordinatore colori |
| devWiki | `project-historian` su richiesta; ogni lotto di riordino aggiorna i percorsi nella doc per sviluppatori, nelle istruzioni `.github` e nelle tabelle delle fonti (`check_source_paths.py` non peggiora) |

### Regole di ogni lotto di riordino (dal piano 43)

Rinomina e taglio in due commit; niente shim; grep dei vecchi percorsi a zero in
`backend/`, `scripts/`, `.github/`, `mkdocs_src/docs/developer/`; suite del dominio e
poi backend intera con gli stessi conteggi della base; `ruff`, `black`, codice morto senza
reperti nuovi; `api sync` senza differenze; `mkdocs build` stretto e `check-links`; le
rinomine con somiglianza ≥ 95 % in `git diff -M`; i `patch` dei test sui nuovi percorsi.

### Nuove schermate (regole del programma colori, fino ai token)

Nessun esadecimale nuovo, niente `!important`, nessuna palette nuova; i pattern esistenti
(card `bg-white dark:bg-slate-800`, bordi `border-gray-200 dark:border-slate-700`, testi
gray-900/700/500 con il dark, bottone primario `bg-libre-green`); stati e badge con le
funzioni condivise di R appena entra il suo lotto A; grafici solo da `chartTheme.ts` dopo
il lotto B; `app.css` non si tocca; ogni schermata nuova entra nella galleria con lo
scatto assestato di G.

### Dipendenze Python

Una sola finestra, eseguita dal developer a corsie ferme, dopo le prime analisi:
`cryptography` (impostazioni dei plugin) e quelle che le analisi motiveranno (per esempio
uno zip con password per il backup, un server SMTP finto per i test). Nessun figlio
installa pacchetti.

### Corsie e carichi pesanti

Una sola invocazione di test per corsia. Galleria completa e run completa con coverage:
una alla volta fra i due programmi, sempre con avviso reciproco. Server di revisione
fermati all'handoff, porta verificata libera.

## 7. Coordinamento con il programma colori (sessione «UI color analysis»)

- Ordine dei loro merge: galleria deterministica (G) → Designer Lab (L, indipendente) →
  fattorizzazione dei colori (R) a lotti A (alfa, segni, stati, badge), B (grafici),
  C (tabelle, media, file, dialoghi), D; poi i token della fase B, dopo il report della
  designer. `app.css` congelato per tutti.
- I miei spostamenti e le mie modifiche nei file di R aspettano il lotto che li elenca
  (§3; elenco esatto dei file del lotto A nel loro messaggio del 14/10, da copiare nei
  prompt d'avvio di X, W, J e Y). Mi avvisa all'ingresso di G e di ogni lotto di R
  (A, B, C, D); io lo avviso prima di ogni merge in `dev_release2`.
- Se un conflitto nasce comunque (il developer: «aiutalo a risolvere o rimappare»), lo
  risolve la sessione figlia che possiede il file, nel suo worktree, all'aggiornamento di
  base.

## 8. Traguardi, in ordine di dipendenza

| # | Traguardo | Sblocca |
|---|---|---|
| M0 | Piano generale in `Phase_1` e sezioni 1.3 nel backlog, committati dal coordinatore: è la base delle sessioni | le 6 sessioni iniziali (solo analisi) |
| M1 | Analisi di H, A, X, W, J, Z approvate dal developer; finestra delle dipendenze | il codice |
| M2 | Pausa degli aggiornamenti (Z, frontend) integrata | la funzione più urgente per il cloud |
| M3 | Primo treno del riordino: registri per famiglia (X), punti d'aggancio e configurazione (H), servizi account (A) | B, la sospensione nel backend (Z), le funzioni di A |
| M4 | Riordino del backend completato (famiglie, servizi per dominio, file grandi) e cartelle frontend fuori dai colori | impostazioni dei plugin, ricerca, decisione sui test speculari |
| M5 | Ondata 1 integrata | proposta al developer: passaggio su `dev`, così l'immagine `nightly` serve al pannello di controllo |
| M6 | Ondata 2 integrata | cancelli di rilascio |
| M7 | Cancelli verdi → 1.3.0 (tag e push del developer) | — |

Indipendenti dai traguardi: il lavoro di J, W e Y, che entra a ogni treno quando è
pronto, e i lotti frontend legati ai lotti B e C dei colori.

## 9. Cancelli

- **Checkpoint di una sessione**: test del dominio verdi, statici puliti, piano aggiornato
  passo per passo (✅, «Note implementazione», «Fuori pista»), handoff `FROZEN`.
- **Prima dell'integrazione in `dev_release2`**: aggiornamento di base, validazione della
  revisione combinata, nessun file condiviso scritto da due sessioni.
- **Rilascio**:
  - run completa con coverage anche sotto carico (4 worker con un'altra corsia attiva,
    C-82);
  - galleria completa (con G, mai insieme a un'altra);
  - upgrade da un DB della 1.2 con le migrazioni nuove; ripristino di un backup della 1.2
    con la prova su copia;
  - immagine Docker: avvio con Litestream spento e acceso, `docker stop` entro il limite;
  - revisione di sicurezza delle superfici nuove (agente `security-review`): inviti,
    reset, sola lettura, token di risveglio, backup, segreti dei plugin;
  - documentazione: `mkdocs build` stretto, `check-links`; traduzione delle pagine nuove
    con la pipeline **solo su tua richiesta esplicita**;
  - `CHANGELOG.md`: capitolo `[1.3.0]` con le voci rivolte all'utente;
  - facoltativo, tuo: prova su un'app Fly di test (sospensione entro N+1 minuti,
    risveglio, ripristino da Litestream).

## 10. Decisioni aperte, con la proposta predefinita

Si confermano o correggono quando arrivano le analisi delle sessioni; nessuna blocca
l'avvio.

| # | Domanda | Proposta |
|---|---|---|
| 1 | In sola lettura, cosa resta permesso? | Letture, export, download del backup, login e logout, lingua e tema personali; il resto risponde con un messaggio chiaro. Lo scheduler continua a scrivere i prezzi (dati di mercato, non dell'utente) |
| 2 | Il limite utenti conta i disattivati? | No: utenti attivi + inviti in attesa, come da specifica |
| 3 | Ruolo di un invito | Utente o admin; nessuna condivisione di broker dentro l'invito |
| 4 | «Istanza raggiungibile da fuori» per l'avviso sulla registrazione aperta | Host della richiesta diverso da localhost e rete locale |
| 5 | Segreti personali nelle impostazioni dei plugin | Ammessi, visibili e modificabili solo dal proprietario; l'admin non li legge mai; nel profilo gestito i campi con override da variabile sono bloccati e invisibili |
| 6 | Zip del backup con password | Sì, facoltativa, se approvi la dipendenza; altrimenti avviso forte che lo zip contiene segreti |
| 7 | Backup scaricabile dal pannello di controllo (zip giornalieri decisi in D-03) | Sì, con un token d'istanza separato, spento se non impostato |
| 8 | Ripristino senza supervisore (installazione senza Docker) | L'app si ferma e chiede un riavvio manuale |
| 9 | Litestream e file (upload, report dei broker) | Litestream copre solo il DB; i file viaggiano negli zip di backup; documentato |
| 10 | `next_wake_at`: lo spinge l'istanza o lo legge il pannello? | Lo legge il pannello: risposta di `wake-sync` e un GET con lo stesso token |
| 11 | Registrare l'accettazione dei termini? | No: la registra il checkout del cloud |
| 12 | File `VERSION` stantio (R2) | Scritto solo nella build dell'immagine; ignorato quando c'è `.git` |
| 13 | Test speculari al codice (TS1) | Si decide a riordino del backend finito, con i numeri in mano |
| 14 | P&L FIFO con valute miste (T-B5) e SPLIT riclassificato (P-10) | Nell'analisi di J, con un test rosso prima |
| 15 | Strumento del grafo della devWiki rotto (graphify 0.9.54) e capitolo 1.2.0 del CHANGELOG (C-92) | Tue decisioni; il grafo serve agli agenti, proposta: fissare graphify alla 0.8.x nella finestra delle dipendenze |

## 11. Primi passi dopo l'approvazione

1. Scrivo il piano generale in `Release_2/Phase_1/` (README con lo stato delle funzioni e
   la tabella delle corsie, più questo piano) e le sezioni H, A, X, W, J, Z, B, E, Y in
   `BACKLOG_POST_1.2.md`; li committo io con percorsi espliciti (base delle sessioni).
2. Creo le 6 sessioni iniziali (H, A, X, W, J, Z): worktree separato, agente
   `coordinated-workstream`, modo piano, prima consegna = solo analisi. Le porto alla
   base locale con un fast-forward e verifico HEAD e file degli agenti.
3. Ti porto le analisi una per volta; la prima autorizzazione al codice è sempre tua e la
   inoltro alla lettera. Z parte per prima sul codice (pausa degli aggiornamenti).
4. Raccolgo le dipendenze nuove e ti chiedo una sola finestra a corsie ferme.
5. Treni: checkpoint, aggiornamenti di base, integrazioni in `dev_release2` (con avviso
   al coordinatore colori), chiusure in `Phase_0`; a ogni treno ti riporto lo stato e i
   commit locali pronti per la tua push.

### Prompt d'avvio di ogni sessione (schema)

Identità del coordinatore; nome e lettera della sessione; perimetro e voci assegnate
(§4); superfici possedute e vietate (§6); ramo `dev_release2` e SHA di base; percorso del
piano (`Release_2/Phase_1/<NN_nome>/plan-phase01<Nome>.prompt.md`); dipendenze e
cancelli; corsia (porta e data-dir) con il preambolo
`PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py test --test-port <PORTA> --data-dir <DIR> …`;
regole delle nuove schermate (§6); avvio del worktree (`.env`, `node_modules` e grafo
assenti per scelta, niente copie da altri checkout, `npm ci` solo dopo un errore
confermato e con il mio via); **prima consegna: solo l'analisi, nessun codice**.


## 12. Avanzamento (coordinatore)

### Piano approvato ✅ (2026-10-14)

> **Note implementazione**: il developer ha approvato il piano il 14/10. Decisioni raccolte
> nella sessione di pianificazione: rilascio quando le ondate 1 e 2 sono complete e verdi;
> le stime del business plan non vincolano; impostazioni dei plugin generiche (ogni campo
> dichiara se è personale o di sistema), con un'analisi dei rischi delle chiavi nel DB; il
> plugin del fornitore a pagamento quando sarà scelto; 6 sessioni per iniziare, poi a
> salire; tutto il riordino del piano 43, backend e frontend; piano in `Release_2/Phase_1`,
> con le chiusure riportate anche in `Phase_0`; tutti e due i programmi integrano in
> `dev_release2`; git locale al coordinatore, push al developer (regola del 14/10,
> `cc7a94501`).
>
> **Fuori pista**: il coordinatore colori ha corretto il calendario delle cartelle frontend
> (il suo lotto A parte subito e tocca anche cambi, asset e transazioni); il §3 e il §7
> riportano il calendario corretto.

### Sessioni iniziali avviate ✅ (2026-10-14)

> **Note implementazione**: base della fase `459131eb8` (piano generale, README, sezioni H…Y del
> backlog). Avviate in modo piano, agente `coordinated-workstream`, prima consegna = solo analisi:
> H (`e-alfy-sturdy-memory`, 6181), A (`e-alfy-legendary-winner`, 6182), X (`e-alfy-cuddly-engine`,
> 6183), W (`e-alfy-fluffy-meme`, 6184), J (`e-alfy-crispy-goggles`, 6185), Z
> (`e-alfy-potential-sniffle`, 6186). Ogni worktree è nato da `origin/dev_release2` (`6d0b1266c`) ed
> è stato portato alla base con `merge --ff-only`; verificati HEAD, pulizia e presenza del file
> dell'agente e del piano.
>
> **Fuori pista**: gli endpoint degli eventi degli asset stanno in `api/v1/assets.py` (di X), ma le
> voci sugli eventi (I-09…I-12, V-22, C-65) sono di W. Deciso: X mette gli eventi in un modulo proprio
> quando divide il router e lo integra presto; da lì il modulo è di W (messaggio a X, perimetro di W).
