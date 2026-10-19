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
> 53; le cartelle 55 e 56 del programma colori, ora in `Phase_1/10_colorSystem/`), `TODO_FUTURI.md`, 4 audit del codice
> in sola lettura (14/10).
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
- **E quando la conversione dei neutri e degli stati è completa** (decisione del developer del 14/10, riportata dal
  coordinatore colori e da lui precisata alle 22:05). Prima del tag devono essere entrati, del workstream T:
  - le ondate W1–W6 per neutri e stati: primitivi, aree libere, stati e mappe, cambi/asset/transazioni, portafoglio e
    grafici, stili propri (tabelle, file, media, dialoghi);
  - B2 (gli stati diventano ruoli), B4 per i soli neutri e guadagno/perdita dei grafici, B5 (le variabili `--lf-cmp-*`
    degli stili propri passano ai ruoli);
  - quindi anche tutti i lotti A–D della fattorizzazione dei colori (R), che quelle ondate aspettano.

  Non bloccano solo le palette per categoria e dei dati, che aspettano un giro della designer. I tagli di file della
  1.3 su quelle aree (FE5 di X, FE8a di W, FE6 e `DataTable` di Y) vanno prima della conversione quando possibile, ma
  non bloccano il tag (regola «chi parte prima», §7).
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
  - dopo il lotto B (grafici): segnali e rischio (FE2), dashboard (FE6; il taglio di
    `GrowthChart` dopo il lotto D, che lo ritocca), broker e lotti (FE7);
  - dopo il lotto C (tabelle, media, file, dialoghi): file (FE3), `DataTable`;
  - dopo il lotto D: la pagina dei file, `ImportBrokerMismatchModal`,
    `BrokerImportFilesModal`, `CompactCashCell`;
  - per ultimi: utility e store generici (FE9, FE10), suffissi (FE11);
  - i tagli di file su cui T aspetta (FE5, FE8a, FE6, `DataTable`) hanno la precedenza nel loro lotto e si annunciano
    al coordinatore colori: la conversione dei colori di quelle aree, necessaria al rilascio, li aspetta se sono già
    annunciati (§7). `AssetModal` e le tre modali delle transazioni sono già fuori dai lotti di R: il loro taglio può
    partire prima del lotto A.
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
| MF | MF - Matematica finanziaria | 6190 | `11_financialMath/plan-phase01FinancialMath.prompt.md` | 16/10, dopo l'audit (decisione del developer su P21) |

Si parte con 6 sessioni (indicazione del developer), poi si sale fino a 9; il 16/10 la decima, MF.

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
7. Migrazione Alembic 005 in A4, solo backend (tabella `account_tokens`, colonne nuove di `users`,
   `email_verified_at` già pronto per E, `NULL` sugli utenti esistenti); 006 in A5, la conversione di
   `enable_registration` in `registration_mode`, con il suo codice e la sua interfaccia (coordinatore, 15/10).

### X · Plugin, asset e ricerca

1. Riordino: un registro per famiglia (PL2), **per primo e integrato subito** perché
   tocca tutte le famiglie; asset senza shim (PL6); `fx.py` → `services/fx/` (PL4);
   `services/assets/` raggruppato; `price_store` in tre moduli; router di asset e cambi
   per risorsa e router dei segnali (PL7, dopo PL1 di J); frontend cambi (FE4) e asset
   con i tagli di `AssetModal` e della pagina dell'asset (FE5). Gli spostamenti di cartella vengono **dopo il lotto
   A dei colori** e dopo la pausa degli aggiornamenti di Z su quelle pagine. Il taglio FE5 ha la precedenza e si
   annuncia (§7): `AssetModal` è già fuori dai lotti di R, quindi il suo taglio può partire prima del lotto A (dopo la
   pausa di Z); la pagina dell'asset dopo la riga di G. La conversione dei colori di asset e cambi (W4 di T,
   necessaria al rilascio) viene dopo; FE4, spostamento puro, si fonde con la conversione in qualunque ordine.
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
   - migrazione Alembic 007; dipendenza nuova `cryptography` (finestra delle dipendenze,
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
   router dei broker per risorsa; schemi delle transazioni; frontend transazioni (FE8a): wizard di import diviso per
   passo, modali Bulk e Form divise per sezione. Lo spostamento della cartella viene **dopo il lotto A dei colori**
   (`transactions/import/` ne fa parte); le tre modali da tagliare sono già fuori dai lotti di R, quindi i tagli
   possono partire prima, senza toccare i file del lotto A. I tagli hanno la precedenza e si annunciano (§7): la
   conversione dei colori delle transazioni (W4 di T, necessaria al rilascio) viene dopo. I 4 file del lotto D dei
   colori solo dopo quel lotto (FE8b, non serve alla W4: i colori delle due modali passano dal B5 di T).
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
dashboard (FE6; il taglio di `GrowthChart` dopo il lotto D, che lo ritocca), broker e lotti (FE7); frontend di sola
presentazione (U8) con i campi del backend di J; indicatore di attesa del server (C-85);
bandiere nei grafici (K-13); tooltip sanificati (K-15, C-34, C-15); voci dei grafici
(I-01, I-03, 47-1, 54-1, B10, 48-1, O-16). Dopo il lotto C dei colori: file (FE3),
`DataTable` tagliata, intestazione Azioni su mobile (C-38 e difetti 2 e 5 del PAC),
ridimensionamento delle colonne (C-62). Per ultimi FE9, FE10, FE11.

**Il riordino di queste cartelle (grafici, dashboard, rischio, broker, file) non blocca il rilascio; la loro
conversione dei colori sì** (W5 e W6 di T, §1):
- il taglio di `DataTable` è il primo lotto di Y dopo il lotto C dei colori, quello di `GrowthChart` (FE6) il primo
  dopo il lotto D; entrambi si annunciano (§7), così arrivano prima della conversione; se tardano, vale la regola
  «chi parte prima» (§7);
- gli spostamenti puri (FE2, FE3, FE7) si fondono con la conversione in qualunque ordine;
- se al tag il riordino di Y non è finito, il resto passa dopo la 1.3.

### MF · Matematica finanziaria

Nasce il 16/10 dalla decisione del developer su P21: «verifica che tutta la matematica sia fattorizzata in
`financial_math` e rivedi gli algoritmi troppo contorti». L'audit in sola lettura
(`11_financialMath/audit-matematica-finanziaria-20261016.md`) ha trovato circa 15 duplicati che possono dare numeri
diversi e propone 16 lotti (A–P). **Il developer li vuole tutti nella 1.3**, in un workstream dedicato accanto a J.
- Il più grosso è A: il contributo per posizione (tabella Performance della Dashboard, pesi tecnici dell'AI Export)
  letto dal motore invece che ricalcolato.
- J il più contorto: `DailyStateBuilder.build`, con le regole dei pool scritte due volte.
- Il lotto C prende da J i due difetti dei pesi segnalati da Y (`portfolio_service.py:852/856`).
- La parte frontend del lotto P la consuma Y; MF prepara i campi del backend.
- MF non tocca i file aperti di J finché i lotti di J non sono entrati.

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
| Inviti e utenti (F13) | A | servizi account, router utenti admin, scheda Utenti, pagina d'invito | sì (005, 006) | `LIBREFOLIO_REGISTRATION=disabled\|invite\|open` | pytest del ciclo di vita dei token; Vitest; E2E invito → registrazione e reset | medio-grande |
| Email (F04) | E | servizio email nuovo, modelli nelle 4 lingue, flussi di A | no (campi già in 005) | `LIBREFOLIO_SMTP_HOST`, `_PORT`, `_USER`, `_PASSWORD(_FILE)`, `_FROM`, `_TLS`, limite di invii | server SMTP finto; E2E del reset | medio |
| Backup e ripristino (F01) | B | servizio di backup, `api/v1/backup.py` (oggi 501), avvio (ripristino in attesa), CLI, scheda Backup, guida | no | limite di caricamento per il ripristino; eventuale token per scaricare i backup (§10) | pytest: andata e ritorno, revisione vecchia e nuova, percorsi nell'archivio; E2E stessi totali | grande |
| Litestream (F25) | B | `Dockerfile`, `entrypoint.sh`, doc Docker avanzato | no | destinazione della replica, credenziali (`_FILE`), chiave SSE-C facoltativa | prova Docker con replica su cartella o S3 locale; SIGTERM attraverso la catena | medio |
| Avvio e risveglio (F07) | Z | scheduler, avvio, `wake-sync`, stato «Aggiornamento prezzi…» | no | `LIBREFOLIO_WAKE_TOKEN(_FILE)`, jitter, attesa sui 429, tempo massimo di spegnimento | pytest del prossimo orario (fusi e ora legale), spegnimento entro il limite; E2E dello stato | medio |
| Impostazioni dei plugin | X | contratti delle famiglie, archivio delle impostazioni, API, zona in Impostazioni, «Configura» | sì (007) | sovrascritture per campo da variabile o `*_FILE` | pytest: scope, cifratura, segreti mai restituiti, blocco da env; Vitest del modulo generato; E2E | grande |
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

### Forma comune del riordino (C1–C7, decise dal coordinatore dopo le analisi, 14/10)

- **C1 — Nomi.** Un file che entra in un pacchetto di dominio tiene il suo nome; cambia solo il pacchetto
  (`services/accounts/auth_service.py`, `services/platform/container_registry.py`). Meno righe toccate, e nessun
  modulo nascosto da una variabile locale con lo stesso nome (`users` in `scripts/user_cli.py:130`). I moduli nuovi
  nati da un taglio prendono nomi brevi per tema, senza ripetere il dominio (`services/fx/sync.py`,
  `services/brim/parsing.py`). Un file esistente si rinomina solo se serve davvero, in un commit a parte con il motivo.
- **C2 — Router divisi.** Un router diviso diventa il pacchetto `api/v1/<dominio>/`, con un modulo per risorsa.
  - L'`__init__.py` contiene solo la composizione dei sotto-router e gli oggetti router che `router.py` già usa:
    `router.py` resta intatto, e una patch su un nome che non c'è fallisce in modo esplicito.
  - L'ordine di registrazione delle rotte resta quello di oggi.
  - Prove: `api sync` (o i JSON di `dev.py api schema`, escluso `info.version`) senza differenze, più una verifica
    che percorsi d'esempio arrivino allo stesso endpoint di prima: un `openapi.json` canonico non prova l'ordine di
    corrispondenza.
- **C3 — Schemi divisi.** Un modulo di schemi sopra le ~1 000 righe diventa il pacchetto `schemas/<dominio>/`, con
  moduli per tema e un `__init__.py` con la sola docstring (niente barile). L'hub `schemas/__init__.py` resta e
  continua a esportare i nomi pubblici; chi importa una classe la prende dal modulo che la definisce. Nomi di classe
  invariati, quindi OpenAPI e impronte dei Tool invariati.
- **C4 — Classi di servizio grandi.** Si tagliano in mixin per tema, composti nella classe del servizio, che resta nel
  suo file con il suo nome (C1: per esempio `services/transactions/transaction_service.py`); metodi pubblici e patch
  sui metodi restano invariati. Le funzioni di modulo vanno nei moduli per tema e le patch puntano al
  modulo che le definisce. Guardia contro le patch mute: uno script AST usa e getta in `/tmp`, oppure un test di
  `test-author` dove serve.
- **C5 — `npm ci`.** Permesso a ogni sessione, solo dal lock e solo nel proprio worktree, quando serve a un controllo.
  Mai `npm install`, `npm update`, `npm audit fix` o `npx`. Per i lotti di solo riordino del backend bastano i JSON
  di `dev.py api schema`.
- **C6 — devWiki.** Le tabelle «Source files» le aggiorna la sessione che sposta i file, nello stesso lotto;
  `check_source_paths.py` non deve peggiorare.
- **C7 — Migrazioni.** 005 e 006 di A (A4: token e colonne degli utenti; A5: `registration_mode`), 007 di X
  (impostazioni dei plugin), poi le correzioni dei dati di W. Chi integra dopo riallinea `down_revision` all'aggiornamento
  di base, e se entra prima di una migrazione con il numero più basso prende quel numero (coordinatore, 15/10).

### Superfici condivise: un solo scrittore

| Superficie | Scrittore |
|---|---|
| `main.py`, modulo di configurazione, `system.py`, area avvisi e `routes/(app)/+layout.svelte` | H (la riga di L in `routes/+layout.svelte` è già concordata) |
| `.env.example` | H crea le sezioni per funzione; ogni sessione riempie solo la sua |
| `provider_registry.py` e contratti delle famiglie | X |
| Scheduler | H lo sposta, poi è di Z |
| Registro delle schede di Impostazioni | A; B e X aggiungono la loro scheda con una riga |
| File Docker | H fino al lotto operativo, poi B |
| Catena delle migrazioni Alembic | ordine assegnato dal coordinatore: 005 e 006 A, 007 X; chi integra dopo rimette `down_revision` all'aggiornamento di base |
| Client API generato | rigenerato con `./dev.py api sync` da chi integra, mai unito a mano |
| Cataloghi i18n | ognuno scrive solo le sorgenti del proprio sottosistema; i cataloghi generati si ricostruiscono |
| Catalogo del runner dei test | ognuno le voci del proprio dominio, in aggiunta; i test speculari (TS1), se decisi, a H |
| Navigazione MkDocs, `CHANGELOG.md` (`[Unreleased]`), piano generale in `Phase_1` | coordinatore (i figli propongono il testo nel loro handoff) |
| `BACKLOG_POST_1.2.md` | ogni sessione 1.3 scrive solo la propria sezione; le chiusure (✅ con data e commit) delle voci di altre sezioni e i rimandi nei piani d'origine di `Phase_0` li scrive il coordinatore a ogni treno; le sezioni L/R/G sono del coordinatore colori |
| devWiki | `project-historian` su richiesta; ogni lotto di riordino aggiorna i percorsi nella doc per sviluppatori, nelle istruzioni `.github` e nelle tabelle delle fonti (`check_source_paths.py` non peggiora) |
| Baseline del cricchetto dei colori (dopo T-1) | T, del programma colori; le sessioni 1.3 la toccano solo con lo script di T, nel commit di un taglio (§6, «Taglio dichiarato») |

### Regole di ogni lotto di riordino (dal piano 43)

Rinomina e taglio in due commit; niente shim; grep dei vecchi percorsi a zero in
`backend/`, `scripts/`, `.github/`, `mkdocs_src/docs/developer/`; suite del dominio e
poi backend intera con gli stessi conteggi della base; `ruff`, `black`, codice morto senza
reperti nuovi; `api sync` senza differenze; `mkdocs build` stretto e `check-links`; le
rinomine con somiglianza ≥ 95 % in `git diff -M`; i `patch` dei test sui nuovi percorsi.

**Rinomina e taglio nello stesso commit** (chiarimento del coordinatore, 14/10, caso del PL2 di X). Sono ammessi
insieme solo se:
- nessun file è insieme rinominato e tagliato;
- ogni rinomina resta ≥ 95 % in `git diff --cached -M`, che il coordinatore controlla allo staging;
- il messaggio di commit elenca a parte le rinomine e i tagli.

Altrimenti servono due checkpoint in fila.

**`npm ci` prima della prima run di test**: anche i test del solo backend avviano il server condiviso, che costruisce il
frontend se manca. Senza `node_modules`, la build chiama `npx` (vietato). Regola C5. Poi, una volta, `dev.py front
build --debug` e `dev.py mkdocs build` (trovato da J): il limite d'avvio del server condiviso (300 s,
`scripts/test_runner/_server.py:48`) comprende anche la build di debug e il sito, che in un worktree nuovo non ci stanno.

**Taglio dichiarato** (dal programma colori, 14/10). Dopo l'ingresso di T-1, il cricchetto dei colori vuole i file
nuovi senza classi di palette e tollera solo le rinomine. Un taglio crea file nuovi con le classi del file di
partenza, quindi:
- nello stesso commit del taglio, la sessione aggiorna la baseline del cricchetto con lo script di T, che sposta i
  conteggi dal file vecchio ai nuovi;
- il totale non deve salire;
- il coordinatore ne controlla il diff prima del commit.

**Conflitti sulla baseline** (`frontend/src/themeRoles.baseline.tsv`, una riga per file, chiavi ordinate: rami che
toccano file diversi non vanno in conflitto). Sulla stessa riga:
- vince il lato più stretto: il conteggio delle classi minore e i soli colori letterali presenti in tutti e due i lati;
- una riga tolta da un lato resta tolta; una riga aggiunta da un taglio resta;
- lo fa `node frontend/scripts/theme/theme-roles.mjs --resolve` dagli stage dell'indice, poi
  `git add frontend/src/themeRoles.baseline.tsv`;
- poi `node frontend/scripts/theme/theme-roles.mjs --check` (o `core-unit`) deve passare sull'albero fuso; se non passa,
  c'è una regressione vera o manca un taglio dichiarato: non si allarga la baseline per farlo passare.

**Il comando del taglio dichiarato** (da qualunque cartella; percorsi relativi a `frontend/src`, ammessi anche con
`frontend/src/` o `src/` davanti):

```bash
node frontend/scripts/theme/theme-roles.mjs --split lib/components/assets/AssetModal.svelte:lib/components/assets/AssetModalPrices.svelte,lib/components/assets/AssetModalProvider.svelte
```

- Il file vecchio può restare come una delle parti.
- Le parti, insieme, non possono superare le classi del vecchio né avere colori letterali che il vecchio non aveva;
  altrimenti il comando esce con un errore e non scrive.
- Aggiunge una riga `~split` alla baseline.

Le rinomine pure non ne hanno bisogno.

### Nuove schermate (regole del programma colori)

**Decisione del developer (14/10, riportata dal coordinatore colori)**: si va subito ai ruoli `--lf-*` e alle utility
semantiche pubblicate dal workstream T dei colori. Le scale di Tailwind non vengono ritinte.

**In vigore da T-1** (`2018fd853`, in `dev_release2` dal 14/10 alle 23:10 con `4e024dfe8`). Due gate in `core-unit`,
`themeRoles` e `themeTokens`, fanno rispettare le regole:
- **un file frontend nuovo nasce a zero**: nessuna classe di palette (`bg-white`, `text-gray-*`, `dark:bg-slate-*`…) né
  colori scritti a mano; solo le utility `*-lf-*` (sezione «Design System» di
  `.github/instructions/frontend.instructions.md`, skill `.github/skills/design-tools/theme-roles/`);
- **un file esistente non può salire**, né nelle classi legacy né nei colori letterali;
- **le rinomine pure** (`git mv` più import) non richiedono nulla;
- mai `dark:` sui ruoli, e mai classi di ruolo e di palette sullo stesso elemento.

Sempre:
- nessun esadecimale nuovo, niente `!important`, nessuna palette nuova;
- stati e badge con le funzioni condivise di R (`lib/theme/toneClasses.ts`) appena entra il suo lotto A;
- grafici solo da `chartTheme.ts` dopo il lotto B;
- `app.css` non si tocca;
- ogni schermata nuova entra nella galleria con lo scatto assestato di G.

### Dipendenze Python

Una sola finestra, eseguita dal developer a corsie ferme, dopo le prime analisi:
`cryptography` (impostazioni dei plugin) e quelle che le analisi motiveranno (per esempio
uno zip con password per il backup, un server SMTP finto per i test). Nessun figlio
installa pacchetti.

### Corsie e carichi pesanti

Una sola invocazione di test per corsia. Galleria completa e run completa con coverage:
una alla volta fra i due programmi, sempre con avviso reciproco. Server di revisione
fermati all'handoff, porta verificata libera.

### Manuale admin: la struttura finale (decisione del developer, 16/10)

Il developer, testuale nella sostanza: tutto il lavoro per LibreFolio Cloud si documenta **nel manuale admin**;
l'alberatura va ristrutturata, e le variabili d'ambiente, che stanno crescendo, vanno divise **in più file per
categoria o funzionalità** invece di una sola pagina grande. Oggi `admin/configuration.md` ha 533 righe e 38 variabili,
`admin/hosting_providers.md` 385; H, A, B, E e Z le stanno ampliando.

**Struttura proposta dal coordinatore** (da confermare col developer prima del lotto):
- 🐳 **Installazione ed esposizione**: installazione sull'host, Docker avanzato, esposizione sicura, controllo delle
  connessioni.
- ⚙️ **Configurazione**:
  - una pagina d'ingresso: come si legge la configurazione (`.env`, segreti `_FILE`, quale valore vince, controlli
    d'avvio, arresto) e **una tabella di tutte le variabili**, una riga ciascuna, col link alla pagina che la spiega;
  - una pagina per categoria: server e rete, sicurezza e segreti (chiave d'istanza, sessione), account e iscrizioni (con
    il primo admin F02), email, dati di mercato e plugin (scheduler, impostazioni dei plugin, ricerca web), backup,
    sospensione e risveglio.
- ☁️ **Ospitare per altri (LibreFolio Cloud)**: il contratto fra l'istanza e il pannello di controllo, il profilo
  gestito, il blocco, i backup per il pannello, il primo admin dal pannello, limiti e link di supporto e pagamento.
- 👥 **Utenti e inviti**, **impostazioni globali**.
- 🧹 **Operazioni**: backup e ripristino, strumenti CLI, struttura delle cartelle.

**Quando e chi**: **un solo lotto di documentazione**, del coordinatore, eseguito dal docs-writer quando i lotti cloud
di H, A, B, E e Z sono entrati e nessuno ha pagine admin aperte. Nello stesso lotto:
- i link vecchi devono continuare a funzionare (redirect o pagine ponte), compresi quelli della app (`DocsLink`);
- un controllo che ogni `LIBREFOLIO_*` letta dal codice stia in `.env.example` e in una sola pagina di categoria;
- `.env.example` diviso con le stesse categorie.

Le traduzioni (it, fr, es) si fanno dopo, su richiesta del developer, con la pipeline Aphra.

**Fino ad allora, regola per i figli**: una variabile nuova si spiega per intero nella pagina della sua funzionalità
(`email.md`, `sleep_wake.md`, `backup_restore.md`, `hosting_providers.md`…). In `configuration.md` va solo una riga
nella tabella, col link. Così il lotto sposta pagine, non riscrive testo.

## 7. Coordinamento con il programma colori (sessione «UI color analysis»)

- Il programma colori vive in `Phase_1/10_colorSystem/` (spostato da `Phase_0/55` e `56` il 14/10, su richiesta del
  developer), con il suo README e i suoi registri: li scrive solo il coordinatore colori. Le cartelle della 1.3 usano
  i numeri 01–09.
- Le schermate di accesso (`auth/LoginCard`, `RegisterCard`, `ui/input/PasswordStrength`), giro 1 della designer:
  le modifiche visive le fa per primo il workstream T dei colori (strada (a), scelta dal coordinatore 1.3 il 14/10),
  compresa la rimozione della chiave `auth.registerTitle` dalle sorgenti i18n di `auth`. A le sposta e ci fa le
  modifiche funzionali (inviti, setup) dopo il merge di T. Se T tarda, A sposta i file con un `git mv` puro e T
  applica le sue modifiche sui percorsi nuovi.
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
- **Avvisi di merge: file del programma colori** (richiesta del coordinatore colori, 15/10). Ogni avviso di merge in
  `dev_release2` elenca i file toccati sotto `scripts/visual_review/`, `frontend/scripts/theme/`,
  `frontend/src/themeRoles*`, `frontend/e2e/gallery.spec.ts`, `scripts/test_runner/_frontend_utility.py` e
  `Phase_1/10_colorSystem/`, anche quando cambia solo un commento: G, R e T li modificano nei loro checkpoint. Prima
  dell'avviso, il coordinatore 1.3 li cerca con `git diff --name-only <target> <ramo> -- <quei percorsi>`.
  `_frontend_utility.py` si è aggiunto il 15/10, dopo A3, su richiesta del coordinatore colori.
- **Regola «chi parte prima»** (concordata fra i due coordinatori il 14/10 alle 22:05). Serve perché nessun riordino
  della 1.3 blocchi il tag.
  - Vale per i tagli di file della 1.3 su un'area che T converte (tabella sotto).
  - Se il taglio non è iniziato quando T arriva a quel file, T converte il file di oggi; il taglio si fa dopo, sul file
    convertito, partendo da una base aggiornata.
  - Se il taglio è iniziato, T lascia quel file per ultimo nella sua ondata.
  - Mai i due sullo stesso file nello stesso momento.
  - **«Iniziato» vuol dire annunciato.** Chi inizia a lavorare su uno di questi file lo annuncia all'altro
    coordinatore, e lo annuncia di nuovo quando il file è entrato in `dev_release2`. Prima di iniziare si controlla che
    l'altra parte non abbia un annuncio aperto. Nella 1.3 la sessione chiede il via al coordinatore, che controlla e
    annuncia.
  - Gli spostamenti puri (`git mv` più import) si fondono con le modifiche di T in qualunque ordine e non si
    annunciano.
  - Ogni taglio fatto dopo T-1 è un taglio dichiarato (§6).

  | Taglio | Sessione | File | Fuori dai lotti di R | Annuncio aperto |
  |---|---|---|---|---|
  | FE5 | X | `assets/AssetModal.svelte`, `routes/(app)/assets/[id]/+page.svelte` | `AssetModal` già oggi; la pagina dopo la riga di G | ~~X, FE5b (`AssetModal`), dal 15/10 alle 08:20~~ **chiuso: entrato in `dev_release2` il 15/10 alle 14:22 (`ec0dc7ebd`)**. La pagina (FE5c) dopo il lotto di Z sul polling |
  | FE8a | W | `transactions/modals/{ImportWizardModal,TransactionBulkModal,TransactionFormModal}.svelte` | già oggi (i passi in `transactions/import/` dopo il lotto A) | ~~W, dal 15/10 alle 07:55~~ **chiuso: entrato il 15/10 alle 16:19 (`14d58cc61`)** (via libera del coordinatore colori: nessun annuncio loro; T li converte nell'ondata W4, sui pezzi già tagliati) |
  | FE6 | Y | `dashboard/GrowthChart.svelte` | dopo il lotto D (è nei lotti A, B e D) | ~~Y, FE6a, dal 15/10 alle 12:47~~ **chiuso: entrato il 15/10 alle 15:12 (`badec1465`)** (via libera del coordinatore colori: nessun annuncio loro; T lo converte in W5; restano `data-testid="growth-chart"` e la forma dell'opzione ECharts, letta dalla E2E del Lab) |
  | `DataTable` | Y | `table/DataTable.svelte` | dopo il lotto C | ~~Y, Y2 (due figli: `DataTableColumnHeader`, `DataTableCellContent`), dal 15/10 alle 15:24~~ **chiuso: entrato il 15/10 alle 18:08 (`c747a74c3`)** (via libera del coordinatore colori; le 4 classi di `editable-checkbox` passano al figlio con il record ereditato) |

## 8. Traguardi, in ordine di dipendenza

| # | Traguardo | Sblocca |
|---|---|---|
| M0 | Piano generale in `Phase_1` e sezioni 1.3 nel backlog, committati dal coordinatore: è la base delle sessioni | le 6 sessioni iniziali (solo analisi) |
| M1 | Analisi di H, A, X, W, J, Z approvate dal developer; finestra delle dipendenze | il codice |
| M2 | Pausa degli aggiornamenti (Z, frontend) integrata | la funzione più urgente per il cloud |
| M3 | Primo treno del riordino: registri per famiglia (X), punti d'aggancio e configurazione (H), servizi account (A) | B, la sospensione nel backend (Z), le funzioni di A |
| M4 | Riordino del backend completato (famiglie, servizi per dominio, file grandi) e cartelle frontend fuori dai colori | impostazioni dei plugin, ricerca, decisione sui test speculari |
| M5 | Ondata 1 integrata | proposta al developer: passaggio su `dev`, così l'immagine `nightly` serve al pannello di controllo |
| M5b | Tagli di asset (X, FE5) e transazioni (W, FE8a) integrati, annunciati e dichiarati; spostamenti di cartella dopo il lotto A dei colori; FE4 in qualunque ordine | l'ondata W4 della conversione dei colori (T), regola «chi parte prima» se tardano |
| M5c | Lotti B, C e D della fattorizzazione dei colori (R) integrati; tagli di `GrowthChart` (FE6) e `DataTable` di Y, se partiti | le ondate W5 e W6 e i passi B4 e B5 della conversione (T) |
| M6 | Ondata 2 integrata e conversione dei neutri e degli stati completa (W1–W6, B2, B4 per neutri e guadagno/perdita, B5) | cancelli di rilascio |
| M7 | Cancelli verdi → 1.3.0 (tag e push del developer) | — |

Indipendenti dai traguardi: il lavoro di J, W e Y, che entra a ogni treno quando è
pronto, e il riordino frontend legato ai lotti B e C dei colori (la loro conversione dei colori, invece, è in M6).

## 9. Cancelli

- **Checkpoint di una sessione**: test del dominio verdi, statici puliti, piano aggiornato
  passo per passo (✅, «Note implementazione», «Fuori pista»), handoff `FROZEN`.
- **Prima dell'integrazione in `dev_release2`**: aggiornamento di base, validazione della
  revisione combinata, nessun file condiviso scritto da due sessioni.
- **Rilascio**:
  - conversione dei neutri e degli stati completa in `dev_release2`: ondate W1–W6 di T, B2, B4 (neutri e
    guadagno/perdita dei grafici), B5; fuori solo le palette per categoria e dei dati (decisione del developer, §1);
  - run completa con coverage anche sotto carico (4 worker con un'altra corsia attiva,
    C-82);
  - galleria completa (con G, mai insieme a un'altra);
  - upgrade da un DB della 1.2 con le migrazioni nuove (il ripristino di uno zip fatto a mano è escluso dalla
    decisione 42: dalla 1.2 si passa con l'aggiornamento sul posto); ripristino di un backup della 1.3 con la prova
    su copia;
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
> H (`e-alfy-h-piattaforma`, 6181), A (`e-alfy-a-account-e-accessi`, 6182), X
> (`e-alfy-x-plugin-asset-e-ricerca`, 6183), W (`e-alfy-w-import-e-transazioni`, 6184), J
> (`e-alfy-j-numeri-e-analisi`, 6185), Z (`e-alfy-z-sospensione-e-risveglio`, 6186); l'app rinomina
> i rami dal nome della sessione poco dopo la creazione. Ogni worktree è nato da `origin/dev_release2` (`6d0b1266c`) ed
> è stato portato alla base con `merge --ff-only`; verificati HEAD, pulizia e presenza del file
> dell'agente e del piano.
>
> **Fuori pista**: gli endpoint degli eventi degli asset stanno in `api/v1/assets.py` (di X), ma le
> voci sugli eventi (I-09…I-12, V-22, C-65) sono di W. Deciso: X mette gli eventi in un modulo proprio
> quando divide il router e lo integra presto; da lì il modulo è di W (messaggio a X, perimetro di W).

### Sei analisi consegnate ✅ (2026-10-14)

> **Note implementazione**: H, A, X, W, J e Z hanno consegnato l'analisi (testo completo nelle cartelle di sessione) e
> sono ferme in attesa del via del developer. Le scelte sono raccolte in
> [decisioni-analisi-20261014.md](decisioni-analisi-20261014.md): 35 decisioni di prodotto con la raccomandazione, più
> le regole comuni del riordino prese dal coordinatore. Il coordinatore colori ha dato gli elenchi esatti dei lotti
> A–D: le cartelle di asset, cambi e transazioni si spostano dopo il suo lotto A, quelle dei grafici dopo il lotto B.
>
> **Fuori pista**:
> - Alle 18:10 il developer ha chiesto una pausa; un riavvio dell'app ha poi interrotto tutte le sessioni, riprese
>   alle 19:13.
> - Due regole del §6 cambiano con le analisi:
>   - i file spostati in un pacchetto tengono il loro nome (proposta di A: meno righe toccate, nessun modulo nascosto
>     da una variabile locale);
>   - router, schemi e configurazione diventano pacchetti per dominio.
> - Voci già chiuse trovate dalle analisi:
>   - C-33, corretta nel treno 28: marcata ✅;
>   - «📈 Gestione Stock Splits» di `TODO_FUTURI`: il FIFO applica già gli split, marcata superata;
>   - la voce 5 dell'indice di luglio: la chiude X;
>   - B12: la verifica J con il lotto dei contributi.

### Cancello dei colori sul rilascio (2026-10-14)

> **Note implementazione**: il developer ha deciso che la 1.3 non esce con la conversione dei neutri e degli stati a
> metà. Il coordinatore colori l'ha prima tradotta in «ondate W1–W4 di T» (`e41e0e2b1`), poi l'ha precisata: servono
> W1–W6, B2, B4 per neutri e guadagno/perdita, B5, e quindi tutti i lotti A–D di R. Per la W4 basta FE8a: le due
> modali di FE8b passano dal B5. Aggiornati §1, §3, §4 (X, W, Y), §7, §8, §9.
>
> **Fuori pista**: la conversione dei colori diventa un secondo percorso critico, parallelo alle ondate 1 e 2 (stima
> di T: ~11.500 classi in 276 file, 30–40 lotti di sotto-agenti). Per non legarle anche il riordino, il coordinatore
> 1.3 ha proposto la regola «chi parte prima» (§7). Segnalato al developer in `decisioni-analisi-20261014.md` §3.
>
> Alle 22:05 il coordinatore colori ha confermato la regola con due aggiunte:
> - annuncio fra coordinatori sui quattro file dei tagli (tabella del §7);
> - taglio dichiarato per il cricchetto di T (§6).
>
> Verificando i lotti di R per la tabella:
> - `GrowthChart` è anche nel lotto D, quindi il taglio FE6 viene dopo quel lotto, non dopo il B;
> - `AssetModal` e le tre modali delle transazioni sono già fuori dai lotti di R, quindi X e W possono tagliarle
>   prima del lotto A.

### Via parziale al codice ✅ (2026-10-14, 22:55)

> **Note implementazione**: il developer, a metà lettura delle decisioni (finite le 11 di Account e accessi, con note
> sue), ha delegato al coordinatore: «vedi tu se aspettare che leggo tutto, o intanto grazie a queste riesci ad avviare
> qualche lavoro». Partono solo i primi checkpoint, tutti di riordino puro e senza decisioni di prodotto aperte:
> H CP1 (`platform/`, `files/`), X0 e CP1 (registri per famiglia), A1 (`accounts/`), W0 e W1 (transazioni e broker),
> J-0 e CP-1 (PAC). Base portata a `c9bb8f257` (regole C1–C7 nel §6) con un fast-forward dei cinque worktree, puliti.
> Approvazione in modalità interattiva, con le parole del developer alla lettera e le risposte di coordinamento.
> Z resta fermo: la sua prima parte dipende dalle decisioni 31 e 32.
>
> **Fuori pista**: le note del developer cambiano il perimetro di A (registrate nel piano di A alla fine di A1):
> - D-A16 respinta: l'invito non vincola l'email;
> - niente `LIBREFOLIO_SUPPORT_URL`;
> - limite dei tentativi disattivabile solo da variabile, più una zona «controlli di sicurezza» per l'admin;
> - scheda Utenti confermata.
>
> Restano aperti, con una proposta del coordinatore:
> - scadenza del token di setup;
> - dove l'admin vede l'abbonamento;
> - meccanismo delle sessioni;
> - cancellazione di un utente da parte dell'admin;
> - `LIBREFOLIO_PUBLIC_URL`.
>
> Le note restano nel file delle decisioni, non committate, finché il developer legge.
>
> **Fuori pista**: il testo che accompagnava l'approvazione dei piani (parole del developer, perimetro, base, risposte di
> coordinamento) non è arrivato alle sessioni. L'app consegna solo «piano approvato».
> - W è rimasto FROZEN, come vuole il protocollo, e ha chiesto il testo.
> - H, A, X e J sono partiti, credendo a un'approvazione diretta del developer. Il loro perimetro coincideva comunque
>   con il primo checkpoint, perché lo dicevano già i loro piani.
> - Il testo è stato rimandato a tutte e cinque come messaggio alle 23:01.
> - **Regola da qui in poi**: a ogni approvazione di un piano, il testo va mandato anche come messaggio.
>
> Programma colori: finestra della galleria domani, 15/10, dalle 09:00, per circa 2 ore. Nella finestra, niente suite
> complete né build pesanti nelle corsie della 1.3; inizio e fine li conferma il coordinatore colori. G-8 (catalogo dei
> Tool oltre i 2 s sotto carico, `schemas/tools.py:83`) va a J, dopo il suo primo checkpoint.

### Primo treno: A1 integrato ✅ (2026-10-15, 00:40)

> **Note implementazione**:
> - checkpoint committati sui rami dei figli:
>   - J-0 (`faa8ce01b`);
>   - A1 (`b53dfd705`, `fc66f19c8`, validazione `29ee87484`);
>   - W CP1 (`9a44bdcec`, `64e3d0a7d`);
>   - H CP1 (`a52018fd7`, `7366c0355`).
> - Ogni base misurata con `all-backend`: 12 965 passati, 28 saltati.
> - Entra per primo A1, il primo validato sulla revisione combinata con `dev_release2` (T-1, T-2, G). Merge
>   `769cc31cb`, albero uguale alla simulazione, codice identico alla revisione validata.
> - H segue: l'aggiornamento di base è aperto con 6 conflitti d'import, che H risolve nel suo worktree.
>
> **Fuori pista**:
> - Due trappole del primo avvio dei test in un worktree nuovo, trovate da H e da J: `npm ci` mancante e build oltre i
>   300 s del server condiviso. Scritte in `.github/copilot-instructions.md` e nel §6.
> - Nel piano di H una riga di tabella è stata resa neutra prima del commit.
> - Dalla verifica di A1 è nata la decisione 36, cosa vede un utente dei dati degli altri.
> - L'ID T-B4 compare due volte nel backlog: il coordinatore colori rinomina la sua voce.
>
> **Aggiornamento (00:55)**: entra anche H CP1 (`6a605904c`). Prima l'aggiornamento di base con A1: H ha risolto 6
> conflitti d'import e rivalidato (`all-backend` uguale alla base). Il CP2 di H si divide:
> - CP2a: pacchetto `config/`, letture d'ambiente e `api/v1/system/`, senza tagliare `main.py`;
> - CP2b: il taglio di `main.py`, dopo il commit del coordinatore.
>
> Così CP3 (segreti) e CP4 (configurazione pubblica) non aspettano più la release.

### Riordino del backend: sette lotti integrati ✅ (2026-10-15, 02:20)

> **Note implementazione**: in `dev_release2`, nell'ordine:
> - A1 (`769cc31cb`);
> - H CP1 (`6a605904c`);
> - A2, il frontend in `lib/features/` (`76e61889b`);
> - W1 e W2, transazioni e broker per tema (`998fd2701`);
> - H CP2a, il pacchetto `config/` con la guardia sulle letture d'ambiente (`60f8a35ce`);
> - X CP1 e CP2a, registri per famiglia e `services/assets/` senza shim (`64a5a3fe7`).
>
> Ogni ingresso dopo un aggiornamento di base e la validazione della revisione combinata nel worktree del figlio:
> - `all-backend` uguale alla base, più i test nuovi;
> - `api schema` invariato;
> - ricerca dei vecchi percorsi a zero;
> - per X, anche la ricerca degli import vecchi che si fondono senza conflitto.
>
> **Fuori pista**:
> - X, partito con due lotti dalla base iniziale, ha avuto 35 conflitti d'import, tutti risolti nel suo worktree.
> - Gli ingressi frontend seguono la finestra della galleria del 15/10: prima delle 08:45 o dopo la chiusura.

### W I1, integrità, integrato ✅ (2026-10-15, 03:01)

> **Note implementazione**: `dc7e4e48e`, merge di `625e3dacc` su `ae998da78`. Il commit è creato con `git commit-tree`
> sull'albero della simulazione (`1153296e3`), così l'avviso al coordinatore colori porta già lo SHA; poi
> `merge --ff-only`. Validazione di W sulla revisione combinata `123c21efc`:
> - `all-backend` 13 458 passed, 28 skipped, 0 failed;
> - `api schema` cambia solo `asset_event_id` di `GET /api/v1/transactions`.
>
> CHANGELOG `[Unreleased]` aggiornato; chiuse V-23, C-79, la ricerca inversa di C-65, L5 e C-3; W-B9 nella sezione X.
>
> **Fuori pista**: due avvisi di aiosqlite sotto carico in un test dell'AI Export, non rossi: C-93, a J.

### A3, schede di Settings e accesso, integrato ✅ (2026-10-15, 03:25)

> **Note implementazione**: `dev_release2` avanza veloce a `90491071d` (A3 `755eaa27d` e journal, base aggiornata con
> W I1 in `d851c39bc`). Registro delle schede di Settings, O-15 (errori di login come chiavi di catalogo), K-17
> (`PasswordInput` da tastiera, nome tradotto), L12 (`user_cli.py create-user`, `dev.py user create … --role`).
> Validazione di A:
> - revisione `35f1e0a16` completa: `all-backend` 13 440 passed, 28 skipped, 0 failed; E2E auth 29, settings 45,
>   app-start-auth 3, onboarding-guides 24;
> - revisione `d851c39bc` mirata dopo W I1: build e `front check` 0/0; core-unit 4 261, component-unit 3 192;
>   `theme-roles` pulito; `check-orphans` 265 file backend; `dev-cli-image` 39, `gate-event-loop-io` 14; E2E auth
>   29, settings 45, `tx-broker-access` 5.
>
> Chiusure di O-15, K-17 e L12 nel README del 38, scritte da A; CHANGELOG con tre righe. Il controllo di L12 sul DB
> di test popolato: `populate_mock_data.py` crea già come utenti normali tutti tranne `e2e_test_admin`, e nessuna
> spec entra come alice…eve.
>
> **Ordine dei prossimi ingressi** (deciso dal coordinatore, 15/10 03:25): X CP2b prima di J CP-1. X ha la coda
> più lunga (CP3 e CP4, e gli eventi che passano a W), mentre il CP-2 di J aspetta comunque le decisioni del
> developer. La risoluzione statica degli import sull'albero combinato X + W I1 + A3 + J dà 0 irrisolti su 9 459
> nomi; J valida poi una sola volta, sopra X.

### H CP3, segreti e chiave d'istanza, integrato ✅ (2026-10-15, 03:50)

> **Note implementazione**: `d08d9358f`, merge di `751bf9ab3` su `ed29f77c2`. Quattro commit di H: due correzioni in
> commit separati (`8f9e8f018`, un segreto vuoto o di soli spazi vale come assente; `7640313a4`, una corsia di test
> usa segreti suoi), poi CP3 (`54fd32def`: `env_secret()` con `*_FILE`, chiave d'istanza e `derive_key`, controlli
> all'avvio, `.env.example` completo) e il journal. Aggiornamento di base `751bf9ab3` con X CP1/CP2a, W I1 e A3: due
> conflitti additivi risolti da H (`main.py`, `test_dev_cli_image.py`). Validazione di H sulla revisione combinata:
> `all-backend` 12 125 passed, 3 skipped, 0 failed; `api schema` invariato; `config-package` 475.
>
> **Ordine**: H era pronto prima di X, quindi entra prima; X lo assorbe con un controllo leggero (guardia delle
> letture d'ambiente sui suoi moduli nuovi, raccolta, `api schema`). La run completa sulla combinazione X + H la fa
> J, che aggiorna la base sopra tutti e due.

### X CP2b, asset per tema e router per risorsa, integrato ✅ (2026-10-15, 04:00)

> **Note implementazione**: `dev_release2` avanza veloce a `92b42d796`. CP2b è `870c9956f` (124 file): rinomina pura
> `schemas/assets.py` → `schemas/assets/assets.py` (R099, l'unica coppia di git) e tagli nello stesso commit (§6,
> opzione 1); `services/assets/core` → `base` + `core`, `price_store` → `price_store` + `currency_change` +
> `event_store`, `api/v1/assets.py` → pacchetto per risorsa, schemi degli eventi in `schemas/assets/events.py`.
> Controllo indipendente del coordinatore sull'AST: definizioni spostate identiche, salvo docstring, percorsi e 6
> richiami a `EventStoreOperations`; 50 file con soli import, 8 rivisti a mano. Validazione di X: revisione
> `eb245b624` (con W I1 e A3) `all-backend` 13 476 passed, 28 skipped, 0 failed; 139 rotte e `api schema`
> identici; poi, sopra H CP3 (`92b42d796`), controllo leggero: guardia 485 (+10, i moduli nuovi), raccolta, schema
> e rotte identici.
>
> Gli eventi passano a W (lotto E1): moduli, contratti e righe che restano a X nel messaggio del coordinatore a W del
> 15/10. Le impostazioni dei plugin di X diventano la migrazione 007.

### W K1, chiarezza, integrato ✅ (2026-10-15, 04:10)

> **Note implementazione**: `dev_release2` avanza veloce a `d915c869f` (K1 `532a1fd9c`, base aggiornata con A3, H CP3
> e X CP2b in `1d1c7e67d`). O-12 (plurale), C-89 (le due date del cambio), V-38 (i problemi di saldo sotto il loro
> titolo), P-15 parte W e W-B8 (testi tradotti dell'editor dei dati). I-10 S3 chiusa senza codice, per decisione del
> coordinatore: il contratto documentato permette di cancellare gli eventi automatici. Validazione di W sulla
> revisione combinata: build 0/0, `i18n check` stretto, `core-unit` 4 266, `component-unit` 3 198, `tx-unit` 887,
> `theme-roles` pulito, E2E `transactions-modals` 25, `asset-data-editor` 26, `fx-csv-import` 21, `fx-editor` 4.
> Con l'ingresso, `ui/data-editor` è libera per T. W-B13 passa a X.
>
> **Prossimo di W**: W4 (`services/brim/`). W3 (`api/v1/brokers/`) e W5–W6 (`uploads.py`) aspettano un commit del
> coordinatore su quei file, come dice il piano di W.

### H, letture di `web_link_finder` in `config/`, integrato ✅ (2026-10-15, 04:25)

> **Note implementazione**: `dev_release2` avanza veloce a `9dda5ccd9` (lotto `fd873f366`, base aggiornata con X CP2b
> e W K1). Le 7 letture d'ambiente di `services/assets/web_link_finder.py` passano in `config/plugins.py`, la sezione
> di X, con la stessa semantica; la chiave API vale anche da `..._API_KEY_FILE`. La guardia `config-package` non ha più
> eccezioni: nessun modulo di `backend/app` fuori da `config/` legge l'ambiente. Validazione di H: `all-backend` 12 185
> passed, 3 skipped, 0 failed sulla sua base; sopra X CP2b, controllo leggero (guardia 540 = 530 + 12 − 2, raccolta,
> `api schema`, `mkdocs build` stretto). Le note su `web_link_finder` per X le gira il coordinatore.

### J CP-1, il PAC per tema, integrato ✅ (2026-10-15, 04:35)

> **Note implementazione**: `dev_release2` avanza veloce a `e1fbc801f`. CP-1A (rinomina) e CP-1B (taglio del PAC e
> guardia dei confini D-J18, allargata a `sqlmodel` e `backend.app.db`), poi quattro aggiornamenti di base. Sulla
> revisione `b17f8fb85` (con W I1, A3, H CP3 e X CP2b) J ha fatto la prima run completa sulla combinazione X CP2b +
> H CP3: `all-backend` 13 810 passed, 28 skipped, 0 failed; `openapi.json` identico. Sull'ultima base (`b8d604086`,
> con W K1 e il lotto di H) un controllo leggero: guardia 567, raccolta +61, API identica.
>
> **Strumenti nuovi per i merge**, scritti da J: `patch_effect.py` (bersagli di `patch`/`monkeypatch` che nessuno
> legge più) e `guard_strings.py` (percorsi nelle stringhe delle guardie che non portano più a niente). Con la
> risoluzione statica degli import del coordinatore, sono i controlli di ogni aggiornamento di base. J-2 diventa C-94
> nella sezione C; C-93 non si è ripresentato.

### W4 CP6, BRIM in `services/brim/`, integrato ✅ (2026-10-15, 04:45)

> **Note implementazione**: `dev_release2` avanza veloce a `155d9b050`. Rinomina pura `548a0688d` (C1): i 4 moduli
> `brim_provider`, `brim_report_sets`, `brim_parse_pool`, `brim_gap_fix` in `services/brim/` (R098–R100), import nei 33
> plugin, costanti del cancello `gate-event-loop-io`, `applyTo`, skill, doc e devWiki; U-B8 (passo «Capacity table»
> tolto dalla guida). Validazione di W: `all-backend` 13 749 passed, 28 skipped, 0 failed sulla base `0229dbc6a`;
> sopra J CP-1 e il lotto di H, controllo leggero (guardia 567, raccolta identica file per file, API identica) e i
> tre controlli statici del coordinatore puliti. Il taglio (CP7), W3 e W5–W6 aspettano un commit del coordinatore su
> `brokers.py` e `uploads.py`; intanto W7 e K2.

### A4, migrazione 005 e token monouso, integrato ✅ (2026-10-15, 05:20)

> **Note implementazione**: `dev_release2` avanza veloce a `e476d2ed4` (A4 `75a8af5a7`, base aggiornata con H CP3,
> X CP2b, W K1, il lotto di H, J CP-1 e W4 in `3ebf4c043`). Migrazione 005 (`005_accounts_invites`, dopo la 004):
> tabella `account_tokens` (solo lo SHA-256, uno scopo per token, scadenza, consumo e revoca) e tre colonne di `users`
> (`session_version`, `email_verified_at` a `NULL` senza riempimento, `last_seen_version`), con `ALTER TABLE` semplice:
> un batch ricostruirebbe `users` e con `foreign_keys=ON` cancellerebbe a cascata. `token_service` con consumo atomico.
> Validazione di A sulla revisione combinata: `all-backend` 13 960 passed, 28 skipped, 0 failed; `db migration-005`
> 25, `account-tokens` 64, `config-package` 568. Prima del commit il coordinatore ha corretto un'attribuzione: la
> scelta su `email_verified_at` è sua, non del developer. Nessuna riga nel CHANGELOG: non c'è ancora niente di
> visibile. Poi A4b, la versione di sessione `sv` (D-A17).

### X CP3, i cambi per tema, integrato ✅ (2026-10-15, 05:30)

> **Note implementazione**: `dev_release2` avanza veloce a `8000aba5a`. CP3 `b991d5e26` (PL4): `services/fx/fx.py` →
> `base`, `storage`, `conversion`, `sync`; `api/v1/fx.py` → `api/v1/fx/` (`providers`, `currencies`). Nessuna rinomina
> a −M95 %. Controllo del coordinatore sull'AST: 32/32 e 20/20 definizioni identiche. Validazione di X: run completa
> sulla revisione con J CP-1 e W4 (`d1ef3ddeb`): `all-backend` 13 875 passed, 28 skipped, 0 failed; rotte (139) e
> `api schema` identici. Sopra A4 (`9a3ba752a`) controllo leggero: guardia 573, raccolta e schema identici.
>
> **Decisioni del coordinatore**: CP3b = W-B9 (contratto e filtri sui fornitori a elenco statico; la BCE dal vivo
> solo in `test_external`), W-B13, X-R5 (salvo `AssetModal` e le fixture di G, girate al coordinatore colori) e X-R7.
> X-R8, proposta: cache di 24 ore dell'elenco delle valute dei fornitori, con l'ultimo elenco noto in caso d'errore.

### W7, gli schemi delle transazioni come pacchetto, integrato ✅ (2026-10-15, 05:40)

> **Note implementazione**: `dev_release2` avanza veloce a `1cd7300f3`. Due commit, perché il nucleo resta sotto la
> soglia di somiglianza di git: W7a `00a19bf72`, la rinomina pura (`R100`) di `schemas/transactions.py` in
> `schemas/transactions/transactions.py`; W7b `e28aad42f`, il taglio in `batch`, `event_suggest`, `promotion` e
> `type_metadata` (59/59 nomi identici al controllo del coordinatore). Validazione di W: revisione con A4 (`304e6d176`)
> `all-backend` 13 965 passed, 28 skipped, 0 failed, API identica; sopra X CP3 controllo leggero (guardia 578, raccolta
> e schema identici). Poi K2a (codici dei rifiuti di DEGIRO e del Generic CSV, L6); K2b dopo un commit del
> coordinatore su `brokers.py` e `uploads.py`.

### X CP3b, test dei cambi senza rete, integrato ✅ (2026-10-15, 06:00)

> **Note implementazione**: `dev_release2` avanza veloce a `63a1f675c` (CP3b `cea5ce859`). W-B9: il contratto e i
> filtri dei fornitori di cambi provati su FED e BOE, che hanno elenchi statici; la SNB va anch'essa in rete, quindi
> resta con la BCE in `test_external` (scostamento motivato dalla decisione delle 05:20, che citava anche la SNB).
> W-B13, X-R5 (percorsi vecchi in commenti e docstring, compresi una riga di A e 2 di `TODO_FUTURI.md`) e X-R7.
> Validazione di X: `api fx` 21/21 anche senza rete; raccolta identica sopra W7. W-B15 (un selettore per testo in una
> spec di W) nella sezione di W; X-R9 con il FE4.

### J C-93, connessioni aiosqlite lasciate aperte, integrato ✅ (2026-10-15, 06:05)

> **Note implementazione**: `c412f8dad`, merge di `3a03a1b2c` su `c81670354`. Causa trovata con la skill
> `test-triage`: 7 test dell'AI Export lasciavano aperte connessioni aiosqlite, e un GC in un thread con un loop corrente
> chiuso ne uccideva il thread di lavoro; pytest attribuiva l'avviso al test in corso, estraneo. Curato nei test.
> Validazione di J sulla revisione con A4, X CP3 e W7: `services ai-export` 1 025, raccolta +4; prima `all-backend
> --workers 2` con la sonda: 0 connessioni aperte. **Senza nuovo controllo di J** dopo X CP3b: nessun file in comune
> salvo il backlog, test da entrambe le parti, controlli statici del coordinatore puliti.
>
> J-5 (un loop chiuso lasciato come corrente in `services/assets/core.py`) passa a X, dopo il CP4; J-6 (una guardia
> di suite per le connessioni aperte) a J, dopo G-8.

### H CP4, `/system/instance` e area degli avvisi, integrato ✅ (2026-10-15, 06:10)

> **Note implementazione**: `dev_release2` avanza veloce a `1b3eb54c7`. Cinque commit di H: la rinomina pura
> `api/v1/system.py` → `api/v1/system/__init__.py` (`c43ea0460`, R100), il taglio per risorsa (`27a29af09`, 16/16
> definizioni identiche al controllo del coordinatore), l'endpoint pubblico `GET /api/v1/system/instance` con
> `LIBREFOLIO_PROFILE` (`42af16d54`), lo store `instanceConfig`, il registro e l'area `InstanceNotices` nel layout
> (`2069c75cd`), il journal. Validazione di H sulla revisione con J CP-1, W4 e A4: E2E 181 verdi (comprese le spec che
> contano le richieste), `all-backend` 12 343 passed, 3 skipped, 0 failed; senza avvisi l'area non disegna niente, e
> la galleria resta invariata. Sopra X CP3, W7, X CP3b e J C-93: controllo leggero (guardia 584, raccolta, `api
> schema` con il solo endpoint nuovo, build e `core-unit`). CHANGELOG con l'endpoint; `LIBREFOLIO_PROFILE` con CP6.

### J G-8, il catalogo dei Tool sotto carico, integrato ✅ (2026-10-15, 06:30)

> **Note implementazione**: `c75f08101`, merge di `47e0f9eec` su `6d67fdaac` (fix `6ce5ea180`). FastAPI risolve
> `get_current_user` prima che l'endpoint sposti la scadenza, quindi il login del catalogo girava dentro la finestra
> d'ingresso di 2 s: sotto carico 503. Le rotte senza corpo partono con il loro budget di 20 s; il compute tiene la
> finestra. Rosso prima e verde dopo (`api tools` 12); `api schema` identico. Senza nuovo controllo di J: H CP4 non
> tocca il router dei Tool. Entra prima della galleria delle 09:00, così la misura finale di G ne tiene conto; la
> riga G-8 nella sezione G è chiusa dal coordinatore. CHANGELOG con una riga in «🐛 Fixed».

### X CP4, gli schemi degli asset per tema, integrato ✅ (2026-10-15, 06:40)

> **Note implementazione**: `7f4618494`, merge di `805f2f112` su `78043417` (CP4 `b31ae0fce`). `schemas/assets/assets.py`
> (1 001 righe, l'unico modulo di schemi di X sopra la soglia di C3) cede `metadata.py` e `scheduled_investment.py`;
> via l'`__all__` che faceva da barile. Controllo del coordinatore sull'AST: 49/49 nomi identici. Validazione di X:
> `all-backend` 13 972 passed, 28 skipped, 0 failed; `openapi.json` identico. Senza nuovo controllo di X: nessun file
> in comune con J C-93, H CP4 e J G-8, controlli statici del coordinatore puliti. `schemas/fx.py` e gli altri restano
> interi, sotto soglia. Poi J-5 e X-R8.

### W K2a, rifiuti a codice e L6, integrato ✅ (2026-10-15, 06:50)

> **Note implementazione**: `dev_release2` avanza veloce a `62c964242` (K2a `0eac8e1b6`, base aggiornata con J C-93,
> H CP4, J G-8 e X CP4 in `388a20f65`). C-70 parte a: DEGIRO e il Generic CSV rifiutano con codici tradotti nel
> wizard (7 chiavi `importWizard.parseRefusal.*`); L6: il 400 del parse nomina plugin e file con i nomi visibili.
> Validazione di W: `all-backend` 14 027 passed, 28 skipped, 0 failed sulla base `58be885a9`; sopra il fuso, controllo
> leggero con le E2E `tx-import-broker-mismatch` e `tx-import-degiro` sul layout nuovo di H. CHANGELOG con due righe.
> C-95 nuova (l'albero degli schemi nelle istruzioni). W prepara E1 in sola lettura; K2b, CP7, W3 e W5–W6 aspettano
> un commit del coordinatore su `brokers.py` e `uploads.py`.

### A4b, versione di sessione, integrato ✅ (2026-10-15, 07:05)

> **Note implementazione**: `dbf89cdd5`, merge di `3d6ecb2fe` su `e7cf1ae80` (A4b `3ac4114d5`, decisione D-A17). Il
> JWT porta `sv`, la versione di sessione dell'account; un token senza `sv` vale 0, quindi l'aggiornamento non
> disconnette nessuno. Il cambio della password alza la versione e riemette il cookie del dispositivo corrente; un
> reset da CLI, una disattivazione o un declassamento la alzano. A-3 chiusa (bcrypt in un thread); la voce «🔑
> Sessioni» passa da `TODO_FUTURI.md` a `TODO_Completati.md`. Validazione di A sulla revisione con X CP3, W7, X CP3b,
> J C-93 e H CP4: `all-backend` 14 046 passed, 28 skipped, 0 failed; E2E auth 29, settings 46, con un test nuovo che
> invia davvero il cambio password e prova il secondo dispositivo. **Senza nuovo controllo di A** dopo J G-8, X CP4 e
> W K2a: nessun test nuovo conia token (quelli dei Tool sostituiscono `get_current_user`); `models.py`,
> `TODO_FUTURI.md` e il backlog si fondono da soli; controlli statici puliti. CHANGELOG con due righe in «🔄 Changed».

### X J-5, il loop chiuso nel thread dei fornitori, integrato ✅ (2026-10-15, 07:20)

> **Note implementazione**: `743fca514`, merge di `cb0bac88d` su `ee5d81a6f` (J-5 `7794e2fb0`). Una riga in
> `services/assets/core.py`: `asyncio.set_event_loop(None)` prima di `loop.close()`, come `asyncio.Runner.close()`;
> un test di test-author, rosso prima e verde dopo. Validazione di X: `all-backend` 14 003 passed, 29 skipped,
> 0 failed sulla base `786f3e216` (lo skip in più è lo scraper CSS di Borsa Italiana a mercato chiuso). Senza nuovo
> controllo di X: con W K2a e A4b condivide solo il backlog; controlli statici puliti. Niente CHANGELOG: non si
> vede da fuori. Poi X-R8 (cache di 24 ore degli elenchi delle valute dei fornitori).

### B, Backup e Docker, avviata in sola analisi (2026-10-15, 07:10)

> **Note implementazione**: sessione `5618ecee`, worktree `e-alfy-miniature-telegram`, corsia 6187 +
> `/tmp/librefolio-r13-b`, base `ee5d81a6f` (fast-forward da `origin/dev_release2`, file dell'agente presente).
> Condizione del §4 soddisfatta: segreti e configurazione di H sono in `dev_release2` dal CP3. Nodi affidati
> all'analisi: i segreti nello zip (specifica F01, D-X2, note di H-3), dove vive il backup dell'istanza rispetto agli
> export per asset di `backup.py`, l'aggancio all'avvio dopo il CP2b di H, le decisioni 6–9 del §10, come si prova
> lo scambio all'avvio. E parte dopo il checkpoint A5a (inviti), Y dopo il lotto B dei colori.

### H CP5a, prontezza e versione, integrato ✅ (2026-10-15, 07:30)

> **Note implementazione**: `9deb0ea08`, merge di `5d1242ae5` su `4fdc0d9c5`. Commit di H: `e8ceda504`
> (`GET /system/ready`: 200 se il DB risponde ed è alla head delle migrazioni, 503 altrimenti, un codice per
> controllo; `/system/info` senza sessione risponde solo `app_version`, decisione 15), `6e78b8c96` (R2: in un checkout
> vince `git describe`; prima di tutto `LF_APP_VERSION`, come in `vite.config.ts`; `pyproject.toml` a 0.0.0, metà di
> C-84), `d80c0a091` (la head delle migrazioni si legge in un thread, non nel ciclo di eventi: correzione chiesta dal
> coordinatore all'handoff), più i log. Base aggiornata con G-8, X CP4, W K2a e A4b in `cf6f08856`. Validazione di
> H: `all-backend` 12 436 passed, 3 skipped, 0 failed sulla base `6d67fdaac`; sopra il fuso, controllo leggero
> (`platform-readiness` 14, `api system` 116, `api auth` 60, `session-revocation` 3, `utils version` 51,
> `config-package` 592, `config-env-example` 36, `check-orphans`, `mkdocs build` stretto, `check-links` 95; `api
> schema` con le sole aggiunte di CP5a). X J-5 entrato nel frattempo tocca solo file di X: niente nuovo controllo.
> Il client generato non è versionato: si rifà alla prossima build in ogni corsia (avvisato il coordinatore colori).
> CHANGELOG con tre righe; R2 chiusa (sezione 09 e piano d'origine), C-84 per metà; H-5 nuova (debito di
> traduzione delle pagine admin). Note per gli altri: a Z, per Z2, `/system/ready`, `/system/health` e `/system/info`
> anonimo non contano come attività dell'utente; ad A, `signed_in_user` chiama `get_current_user` direttamente, quindi
> un override in `dependency_overrides` non arriva a `/system/info`. Poi CP5b dopo la finestra della galleria, e CP6.

### J-6, guardia di suite sulle connessioni aiosqlite, integrato ✅ (2026-10-15, 07:40)

> **Note implementazione**: `e2cb55054`, merge di `e6016fca7` su `2c699f85c` (J-6 `b49a54645`). Una fixture
> autouse nel `conftest.py` condiviso: un test che lascia aperta una connessione aiosqlite creata da lui, nel thread
> principale, va in ERROR al proprio teardown, con lo stack di creazione. Elenco delle eccezioni esplicito e vuoto;
> self-test in `utils gate-aiosqlite-leak` (9). Base aggiornata dal coordinatore in `c7a2b050e`, con un conflitto nel
> backlog (la chiusura di J-5 accanto a J-6) risolto tenendo le due righe. Validazione di J sul fuso: `all-backend
> --workers 2` 14 199 passed, 29 skipped, 0 failed, nessun rapporto della guardia; raccolta +9, i soli self-test.
> Senza nuovo controllo: dopo la validazione sono entrati solo la versione fissata nelle gallerie e i record. La
> regola è la n. 7 di `.github/instructions/backend-testing.instructions.md`, con il testo proposto da J. Fragilità
> segnalata da test-author: cinque file dell'AI Export creano motori in memoria senza `dispose()`; passano perché non
> eseguono SQL, e se un giorno lo faranno la guardia nominerà il test. Niente CHANGELOG: è interno ai test. Il lavoro di
> J autorizzato dopo il CP-1 è chiuso (C-93, G-8, J-6); CP-2 e seguenti aspettano le decisioni 26–30.

### W E0 committato, FE8a annunciato (2026-10-15, 07:55)

> **Note implementazione**: E0 (`692fbae39`: eventi distinti per data e tipo nel CSV e nel selettore della data,
> X-R9, W-B15), base aggiornata in `2bf015afa`; entra dopo la finestra della galleria. FE8a (tagli delle tre modali
> delle transazioni) annunciato al coordinatore colori, che ha dato via libera: nessun loro annuncio aperto, T li
> converte nell'ondata W4 sui pezzi già tagliati. Annuncio aperto nella tabella del §7 (`2c699f85c`).

### B, analisi consegnata; punti 38–43 per il developer (2026-10-15, 08:05)

> **Note implementazione**: analisi di B (13 sezioni, nella cartella della sessione `5618ecee`, `plan.md`; andrà in
> `07_backupDocker/` al primo via). Zip con la forma della cartella dei dati (`VACUUM INTO`, elenco d'inclusione
> esplicito, `manifest.json`); ripristino sempre su una copia (revisione più nuova o sconosciuta rifiutata, più
> vecchia migrata sulla copia), conferma con backup automatico, scambio per rinomine all'avvio con giornale e ritorno
> indietro, uscita ordinata; sessioni chiuse; Litestream v0.5 spento finché la variabile è vuota. Nessuna migrazione,
> nessuna dipendenza nuova con la busta cifrata (`cryptography`, già nella finestra di X). Lotti B0–B9 più la
> revisione finale; percorso minimo per il cloud B1 → B2 → B3 → B5 (+B4) → B7. Scelte per il developer nei punti
> 38–43 del file delle decisioni; quelle di coordinamento lì sotto: B0 (divisione di `backup.py`) entra prima di E1
> di W; `backup_service.py` → `series_export.py`; prova «stessi totali» in un sottoprocesso; M-1 alla fine.
> Richieste a H (passi d'avvio di CP2b, percorsi dell'isolamento, funzioni di `instance_key.py` per H-3), ad A (una
> riga nel registro delle schede), a X (ricifratura nel CP10), a J (totali di controllo in sola lettura): le gira il
> coordinatore al via. B resta in modo piano, fermo, senza messaggi accodati.
>
> **Fuori pista**: nel file delle decisioni la riga delle migrazioni (§3) diceva ancora «la 006 delle impostazioni dei
> plugin»: riallineata alla C7 (005 e 006 di A, 007 di X).

### W E0, gli eventi per data e tipo, integrato ✅ (2026-10-15, 07:51)

> **Note implementazione**: `d226bc69e`, merge di `2326624c1` su `989991f78` (E0 `692fbae39`). `CsvColumnDef.matchKey`:
> nel CSV degli eventi due righe sono doppioni solo con la stessa data e lo stesso tipo (la riga 38 di
> `EventDataImportModal.svelte`, di X, scritta da W col via del coordinatore); il selettore della data blocca solo i
> giorni con un evento dello stesso tipo. Più i due test-id di X-R9 in `DataImportModal.svelte` e W-B15. Validazione
> di W sul fuso `2bf015afa`: build, `core-unit` con la guardia dei colori, `component-unit`, E2E `asset-data-editor`,
> `fx-csv-import`, `fx-editor`, `tx-bulk-operations`, `mkdocs build` stretto. Entrato prima della finestra della
> galleria, su richiesta del coordinatore colori, così R, L e T non devono rifondere; dopo la validazione erano entrati
> solo la guardia di J-6 e dei record, nessun file frontend. CHANGELOG con una riga; chiuse I-11 a e d (README del 38)
> e W-B15; X-R9 fatta per la parte di W (restano a X le quattro righe della spec, con il FE4).

### Decisioni di coordinamento della mattina (2026-10-15, 08:10)

> - **H CP6, il blocco dell'istanza**: `router.py` (la riga della dipendenza) e `zodios-client.ts` (il ramo 423) concessi
>   ad H. Niente cancellazione dell'account nella pagina di blocco finché A non estrae il dialogo da `ProfileTab.svelte`
>   (l'API resta permessa); il reset della password resta fuori dai permessi, come nella decisione 12. Dalla revisione di
>   sicurezza di H: da fuori, chi non ha sessione può capire che l'istanza è bloccata, perché le rotte pubbliche fuori
>   dall'elenco rispondono 401; nessun dato esce. Scelta (a): resta così, con la garanzia scritta più stretta. L'altra
>   strada, aggiungere all'elenco le GET pubbliche di soli dati di riferimento, non chiuderebbe il segnale (la
>   registrazione resta) e cambierebbe l'elenco deciso dal developer.
> - **W FE8a**: taglio del template in figli con props esplicite; stato, effetti e handler restano nel padre. Cartelle
>   `components/transactions/{form,bulk,wizard}/` (`wizard/` confluisce in `import/` con FE8b). Tre sotto-checkpoint.
>   Lo stato in una classe resta fuori dalla 1.3.
> - **J C-94**: `dev.py server --build-only` prima del tempo massimo, nel server condiviso dei test e, col via del
>   coordinatore colori, anche in `dev.py mkdocs gallery`, con `LF_APP_VERSION` passata alla build. Senza
>   `node_modules`, `dev.py` si ferma subito, senza `npx`. La doppia build (produzione per le categorie frontend, debug
>   per il server) va in J-7.
> - **Finestra della galleria**: 5 gallerie complete in fila (r1, r2, le candidate di R, L e T), fino alle 12:30 circa.
>   Dopo: prima R e L, poi i lotti della 1.3 (H CP5b, H CP6, FE8a, A5), poi T.

### X-R8, le valute dei fornitori dei cambi in cache, integrato ✅ (2026-10-15, 08:18)

> **Note implementazione**: `173ba19e2`, merge di `849c98dda` su `1dac6b326` (X-R8 `1dfd4e657`). `services/fx/catalog.py`:
> l'elenco delle valute di ogni fornitore resta 24 ore nella cache `fx_provider_currencies` (visibile nel pannello
> delle cache); un fornitore che fallisce o supera i 5 s risponde con l'ultimo elenco noto, riprovato dopo 5 minuti.
> API invariata. Validazione di X: `all-backend` 14 119 passed sulla base `4fdc0d9c5`; sul fuso `38b913df3` (con H
> CP5a, J-6, W E0) controllo leggero con la guardia di J-6 attiva: `fx-catalog` 8, `api fx-unit` 29, `api fx` 21,
> `config-package` 593, `check-orphans`, `openapi.json` identico, `mkdocs build` stretto. Entrato prima delle 08:45:
> dalle 08:45 alla fine delle gallerie r1 e r2 (verso le 10:15), che girano nel checkout principale, `dev_release2`
> resta fermo (richiesta del coordinatore colori). CHANGELOG con una riga. La docstring con `services/fx.py` in
> `api/v1/fx/providers.py` è X-R1: cambia `openapi.json`, la corregge X col CP6. Poi FE5b (taglio di `AssetModal`,
> annuncio aperto nel §7).

### E, Email, avviata in sola analisi; checkpoint sui rami dei figli (2026-10-15, 08:40)

> **Note implementazione**: sessione `877410cd`, worktree `e-alfy-stunning-fortnight`, corsia 6188 +
> `/tmp/librefolio-r13-e`, base `380a3e768`. Condizione del §4 soddisfatta: i token monouso di A4 sono in
> `dev_release2`, e il contratto di inviti e reset è nel checkpoint A5a (`2d4708578`, sul ramo di A), che E legge con
> `git show`. Nodi affidati all'analisi: invio fuori dal ciclo di eventi, server SMTP finto per i test, link senza
> `LIBREFOLIO_PUBLIC_URL`, enumerazione, limite di invii, lingua, avvisi di configurazione, blocco dell'istanza.
>
> Committati sui rami dei figli, non integrati: A5a (`7da2cd9a2`: migrazione 006, inviti, `registration_mode`, API
> admin, CLI; l'aggiornamento di base è aperto nel worktree di A con un conflitto in `test_system_api.py`, che risolve
> A), W FE8a-1 (`8a62cea7f`: il form delle transazioni tagliato per sezione), X FE5b-1 (`37532d558`: `AssetModal` in sei
> pezzi). Entrano dopo la finestra della galleria, dopo R e L. Decisione su A-9: la corsia dei test toglie le quattro
> variabili di account, come fa già con i segreti (in A5b). `billing_url` nella pagina di blocco: lotto piccolo di H
> dopo l'ingresso di A5.
>
> **Finestra della galleria**: dalle 08:45 a fine r2 (verso le 10:15) `dev_release2` resta fermo; poi i lotti solo
> backend possono rientrare con l'avviso, quelli frontend dopo la fine della finestra (verso le 12:30).

### Finestra della galleria, prima parte (2026-10-15, 08:45–10:20)

> **Note implementazione**: `dev_release2` fermo a `2338aaf79` dalle 08:38 alle 10:16 (gallerie r1 e r2 del programma
> colori nel checkout principale; r1 rilanciata alle 09:15 con meno worker; tutte e due pulite). Nel frattempo, solo
> commit sui rami dei figli:
> - **H**: CP5b e CP6 (`87be1e2d8`…`0326a1d02`, base in `5b2b9061f`); scritti CP7a, C-96 e un filtro che maschera i
>   token nel log d'accesso di uvicorn (i link di A5b portano ora il token nel frammento). CP6 entrerà dal commit
>   `5b2b9061f`, validato con il worktree staccato lì; i tre lotti nuovi restano sul ramo finché non sono provati.
> - **A**: A5a committato e base aggiornata (`8e049474e`, conflitto in `test_system_api.py` risolto da A); A5b in corso.
> - **X**: FE5b-1, FE5b-2, X-R11a, X-R1 e X-R2 committati; il contratto del ripristino per B nel disegno del CP10
>   (il `key_id` di ogni segreto fa da valore di controllo H-3: B non deve riscrivere niente).
> - **W**: FE8a in tre pezzi committati (il Wizard prima delle prove); avviato N1: la cassa e le posizioni della pagina
>   broker al giorno dell'utente (verificato da J: è la regola della Dashboard) e le metà spaiate dei trasferimenti
>   (V-3). Decisioni del coordinatore: CASH_TRANSFER e FX_CONVERSION come la divisione di una coppia (deposito o
>   prelievo); le metà già nei DB con una correzione dopo le migrazioni (non Alembic: il log di ogni riga si vede
>   anche in Docker), che entra solo con l'ok del developer (punto 46); le gambe in uscita restano come oggi fino al
>   punto 47 (proposta di J: rettifica in uscita al costo). D-J4 aggiornata: i rossi su lotti e Dashboard li scrive il
>   test-author di W, J ne rivede i numeri.
> - **E**: analisi consegnata, senza dipendenze nuove; scelte di prodotto nei punti 44 (la verifica dell'email) e 45
>   (link solo con `LIBREFOLIO_PUBLIC_URL`), le altre del coordinatore nello stesso blocco. Trovata C-96, assegnata a
>   H; A-9 di A ne fa parte.
> - **J**: C-94 scritto (prove dopo la finestra, con una categoria della galleria e `LF_APP_VERSION` concordata col
>   coordinatore colori); rivista la V-3 di W.
>
> Punti nuovi per il developer nel file delle decisioni: 44–47.

### R in `dev_release2`, avvio di B, E e Y (2026-10-15, 11:10–11:30)

> **Note implementazione**: il coordinatore colori ha fuso i lotti A–D di R (`8fd8e494b`, più `23f6578f3`: timbro di
> `sw.js`); `dev_release2` fermo per loro dalle 11:17 alle 11:22. Sbloccati gli spostamenti di cartella legati ai lotti di
> R (FE4 e FE5a di X, FE8 di W; FE2, FE3, FE6, FE7 e `DataTable` di Y). Coda dei lotti frontend: L, poi i nostri, poi T.
> - **B ed E avviati** su delega del developer («riguardo b ed e sei tu il coordinatore, a meno che non devo qualcosa
>   in particolare, e allora aggiornami, avviali tu»), base `23f6578f3`. B: B0 (divisione di `api/v1/backup.py`, prima
>   dell'E1 di W, che partirà dal pacchetto nuovo; D-B8, la rinomina `backup_service.py` → `series_export.py`) e B1;
>   D-B7 e D-B9 come proposte, D-B10 dopo B7. E: E0 ed E1, con `links.py` spostato in E3 (aspetta il punto 45) e la
>   registrazione in `config_audit.py` in E2 (il file ha modifiche in attesa sul ramo di H); l'aggancio a `cli_base.py`
>   non serve più, lo copre C-96 di H; D-E1, D-E2, D-E4…D-E6, D-E8…D-E14 come proposte.
> - **Y avviato** in sola analisi (sessione `17050e81`, corsia 6189), base `23f6578f3`: i tagli di `DataTable` e
>   `GrowthChart` devono arrivare prima delle ondate W5 e W6 di T.
> - **W**: committati la doc di N1b-2 (`3f42dda9d`) e il journal (`eb3bb0529`). W-B20 riscritta con i reperti di X:
>   `delete_assets_bulk` è già atomico (un `UPDATE` vuoto prima del primo savepoint); il listener `begin` generale è
>   scartato (`SQLITE_BUSY_SNAPSHOT`). Cura decisa: un aiuto mirato in `db/session.py`, lotto piccolo di W dopo N1.
>   W-B22 e W-B23 (quadro delle correzioni post-migrazione) assegnate a W come N1b-3: W-B22 è legata a N1b-2, perché
>   una violazione di FK già nel DB ferma il giro prima di `orphan_pair_halves`.

### La 1.2.1 pubblicata e riportata in `dev_release2` (2026-10-15, 12:00–12:50)

> **Note implementazione**: il developer ha deciso di pubblicare la 1.2.1 subito, separata dal restyle dei colori, con
> una terza correzione: un `JWT_SECRET` di soli spazi non è più la chiave che firma le sessioni (`c73d5d56a`, test
> `utils jwt-secret-blank` rosso 9/15 prima, verde 15/15 dopo). Ramo `hotfix-1.2.1` = `064fb4fc2` (9 commit su v1.2.0);
> `main` avanzato e release v1.2.1 pubblicata dal developer alle 12:27 (pipeline `38720357465`). Nessuna advisory né CVE
> (decisione del developer). Riportata in `dev_release2` con il merge `6c349f907`, preparato in un worktree a parte:
> conflitti solo in `CHANGELOG.md` e `services/accounts/auth_service.py` (tenuta la versione 1.3: `env_secret()` di H
> scarta già il segreto vuoto); il test del segreto adattato alla 1.3 dal test-author; prove sull'albero fuso: i 4 test
> della 1.2.1 (23, 26, 36, 15), `config-package` 594, ruff pulito. Sbloccati il CP2b di H e i lotti CP7, W3 e W5–W6 di W.
> `dev_release2` si può pushare.
>
> **⚠️ Fuori pista**: avevo detto al developer che la pipeline di rilascio rifà i test; non è così: fa build, controlli
> della documentazione, galleria e immagini. Il giro completo sull'hotfix (`utils all`, `api auth`) lo faccio dopo la
> finestra della galleria.

### Y e Z avviati, decisioni 19–25 girate (2026-10-15, 12:40–12:50)

> **Note implementazione**: su delega del developer («Sì: avvia tu Y (i due tagli) e Z (Z6a subito, Z1 quando decido il
> 31)») approvati i piani di Y e Z, base `1e9e567f7`. Y: Y1 (taglio di `GrowthChart`, FE6a, annunciato e accettato dal
> coordinatore colori) e Y2 (`DataTable`, da annunciare); D-Y1…D-Y9 decise dal coordinatore; D-Y10…D-Y12 (C-85, 54-1,
> difetto 5 del PAC) vanno nel file delle decisioni. Z: Z6a (prove su C-49); Z1 aspetta il punto 31. Decisioni del
> developer girate alla lettera: 19 a X (scraper fuori dalla ricerca nel profilo gestito, assegnabili a mano con un
> avviso), 20–25 a W (20 subito in E1: errore e «Modifica questo»/«Usa questo»/«Annulla», niente «Crea comunque»; 23:
> i tipi sconosciuti già salvati si cancellano); E1 di W autorizzato, la parte sull'export degli eventi dopo B0.

### Finestra delle dipendenze e treni 32–35 (2026-10-15, 13:05–14:45)

> **Note implementazione**: chiusa la finestra della galleria (13:01). Il carico della macchina è salito a 84, poi a
> 110–139, per troppe prove «leggere» in parallelo (categorie Vitest con un worker per core, build, svelte-check) più le
> gallerie del programma colori. Regole nuove: al massimo 3 suite pesanti sulla macchina, 2 della 1.3 e 1 del programma
> colori, assegnate dai coordinatori; le categorie Vitest contano come pesanti; le corsie non in integrazione lanciano
> solo test di file singoli. Finestra delle dipendenze (13:08–13:36): tutte le corsie ferme, il developer ha installato
> `cryptography` (lock: + `cryptography 50.0.2`, `pycparser` 3.0 → 3.11), commit `dc9a5d232`.
> Treni: 32 `dc9a5d232` (dipendenze); 33 H CP5b+CP6 (`83eaa5a28`, validato da H sulla revisione combinata:
> `all-backend` 12 725, core-unit 4 407, component-unit 3 240, E2E auth/app-start-auth/settings); 34 X FE5b, X-R11a,
> X-R1/R2, D-X4 (`ec0dc7ebd`, validato da X su `2fb577588`, che differisce solo per `Pipfile`; due rossi di
> `asset-browse` da saturazione, la spec da sola 8/8; sull'albero H+X `npm run check` 0/0 dopo `api sync`); 35 E1
> (`f46a93ffd`, validato nella corsia del coordinatore: email-* 516, config-package 639). Basi aggiornate e committate:
> A (`246863005`), X (`2fb577588`), E (`fc99e9bfe`), W (`06459c1b3`), H riattaccato (`aa0e3a49a`); Y in corso.
> Checkpoint committati: B0 (`be6206c0d`), B1 (`d37736d05`), E1 (`918e8d4f0`), W E1c (`87a034a89`), Y1 (`374dcca8a`).
>
> **⚠️ Fuori pista**: `--resolve` del cricchetto dei colori perde un `~accept` presente da un solo lato (R-8); ripetuto
> l'`--accept` D3 di `themeStore.ts` nei merge di X e W, con l'ok del coordinatore colori (TC-7 di T per la cura).

### Treni 36–38 e decisioni 18–37 (2026-10-15, 15:00–15:55)

> **Note implementazione**: entrati Y1 (`badec1465`, galleria filtrata contro `g-final3-r1` senza differenze dal
> taglio, 96/96 scatti del grafico di crescita), A5 (`8bcb23502`, validato da A sulla revisione combinata con CP6 e E1)
> e i quattro lotti di H (`744f5a0ee`: CP7a, C-96, filtro del log d'accesso, G-10, più la riparazione di
> `test_instance_block.py`, rosso in `dev_release2` per un conflitto semantico CP6 × A5a). Prova Docker parziale: il
> build si ferma a `pip install` per il proxy TLS della rete (H-11); `tzdata-legacy` e i compose verificati a parte; la
> prova a runtime dell'immagine resta al developer, fuori dalla VPN, con gli script di H. Decisioni 18–35 scritte nel
> file (`8fc44558c`); 37 girata ad A (lotto A6c); 36 in discussione (file comuni e personali, registrazione «su invito»
> di default). Avviati A6 (scheda Utenti; verifica dell'indirizzo con un nonce firmato al posto del CORS su
> `/system/instance`) e Y2 (`DataTable`). Checkpoint committati: E2a (`c1d1c3c2d`), Z1 (`a6199d0e7`, base aggiornata
> `4618a2116`).

### Treni 39–40, punto 46 (2026-10-15, 16:00–16:20)

> **Note implementazione**: entrati Z1 (`9d2074b2b`) e W (`14d58cc61`: FE8a, N1, N1b-2/3, E1a, E1c). Punto 46
> deciso dal developer: la correzione `orphan_pair_halves` entra; una metà senza costo resta «costo mancante». Verificato
> poi sul codice che una metà ricevuta senza costo nasce solo da chiamate dirette all'API (il modulo e il Bulk, import
> compresi, richiedono la modalità di costo: `cost_basis_pair` del TRANSFER ricevuto = `required_qty_pos`) o da dati
> precedenti alla 1.0; il developer: «una protezione in caso di chiamate dirette dalle api, ma non certo metterci a fare
> bonifiche» → lotto N2 di W. E1b: `delete_ids` nella richiesta di upsert, salvataggio atomico (decisione 22).
>
> **⚠️ Fuori pista**: al developer avevo detto che gli import creano trasferimenti senza costo; era sbagliato (avevo
> letto i plugin, non il Bulk che li completa). Corretto in chat e ritirata la voce di backlog a W.
>
> **⚠️ Fuori pista (2)**: anche «nasce solo da chiamate dirette all'API» era sbagliato. L'analisi N2 di W (16:25) mostra
> che il backend la regola la controlla già: `validate_cost_basis` (`batch_costs.py`) gira dopo il WAC su ogni percorso
> di `execute_batch` (validate, commit, `promote-transfer`) e una creazione senza costo dà `costBasisRequired`, con il
> batch non committato. Le righe senza costo nascono dai dati vecchi, dalle due conversioni di N1, dall'Auto senza
> media (P-1) e dalle ADJUSTMENT di uno SPLIT. Il controllo sulle modifiche è invece più stretto del deciso: rifiuta
> anche la modifica delle sole note di una riga senza costo, che con N1b-2 esistono. **N2 ridefinito**: la regola letta
> da `TX_TYPE_METADATA` (`cost_basis_required(type, quantity)`), e il controllo sulle modifiche solo quando cambiano
> tipo, quantità (segno compreso) o costo, confrontando i valori con la riga salvata. Auto senza media e split restano
> fuori. Parte dopo E1b.

### Treno 41, decisioni 38–39 (2026-10-15, 16:40–16:55)

> **Note implementazione**: entrato J (`2faa88a34`: C-94 e CP-2). `copilot-instructions.md` aggiornato con il testo di J
> sul build in primo piano (`--build-only`). Decisioni del developer: 38, «ok all'idea della busta» (`.lfbk`,
> scelta dal developer alle 17:00 al posto di `.lfbackup`; scrypt + AES-256-GCM, solo `cryptography`; lo zip con password classico avrebbe richiesto `pyzipper`); 39, «così
> l'utente sceglie se fare un backup in "chiaro" o un backup "sicuro" e nel messaggio gli viene detto la differenza».
> B4 dopo B3 e B5: è l'unico pezzo di B che può slittare. Z7a autorizzato dal developer («Sì, Z parta con Z7a»).

### Treni 42–44, decisione 40, Z6b (2026-10-15, 17:15–17:40)

> **Note implementazione**: entrati A6a (treno 42), H (`eacc34784`) e Z7a (`2ab8a3a43`). Decisione 40 del developer: le sessioni
> si chiudono con l'ora del ripristino (non si rigenera `JWT_SECRET`), l'anteprima elenca gli admin del backup e blocca
> se non ce n'è nessuno; nel cloud il recupero dell'admin passa da «password dimenticata» via email, nei casi gravi
> dall'assistenza con `dev.py user reset-link`. Z6b autorizzato dal developer («Sì, Z parta con Z6b»).
> Scatti nuovi di galleria (`settings/users` di A6b, `settings/backup-ready` di B): li scrivono A e B con la checklist di
> G, che li rivede prima dell'ingresso.

### Treno 45, decisioni 36–46 scritte (2026-10-15, 17:40–18:10)

> **Note implementazione**: entrato Y2 (`c747a74c3`), con la ripresa della galleria a carico basso (10 su 10; i 10 rossi
> del primo giro erano carico). Il file delle decisioni è committato con le righe «Decisione» 36–46 (`a718e5281`); 47
> attende il «sì» del developer. 41: la copia di sicurezza prima del ripristino si cancella se il primo avvio va bene;
> 42 respinta (solo backup di LibreFolio); 43 approvata; 44 approvata; 45: solo `LIBREFOLIO_PUBLIC_URL`, con il
> controllo dal browser dell'admin tramite la sonda di A6a. `main.py` congelato per CP2b di H. Scatti nuovi di galleria
> (A6b, B, E) con la checklist di G.

### Treni 48–49, gate i18n (2026-10-15, 18:30–19:00)

> **Note implementazione**: entrati E2 (`755158aad`), la sua correzione (`be7de95b6`) e Z6b parte 1 (`000090aaf`).
> Decisioni 48–50 del developer scritte (`bcd680868`); delega del developer sui lotti di Y («Sì, e d'ora in poi decidi tu
> l'avvio dei lotti di Y»).
>
> **⚠️ Fuori pista**: E2 è entrato senza `core-unit` e ha portato un rosso in `dev_release2`
> (`htmlInterpolation.gate.test.ts`, la chiave `email.problems.SMTP_FROM_INVALID` con `<`), trovato da T nella sua
> validazione. Corretto in 15 minuti riformulando nelle 4 lingue. **Regola d'ingresso nuova**: un lotto che cambia
> cataloghi i18n porta `front-utility core-unit` verde (gate di markup, ICU, lingua).

### Treni 50–60, pause per le gallerie, deleghe (2026-10-15, 19:00–21:40)

> **Note implementazione**: entrati B, H CP2b, W N2, B8, A6b, J CP-4c, lo scatto di B, X CP10, Y8, Z6b parte 2, E3
> con E3s e la correzione del flash. Due pause delle corsie 1.3 per le gallerie dei colori (20:49–20:53 e 21:00–21:08):
> i rossi di DV erano saturazione, i tre scatti nuovi sono stabili (6 su 6 in due run). Il developer ha delegato al
> coordinatore l'avvio dei lotti di Y e di Z. Decisione 36 completata (scopo dei file, D36-1…3 approvate).
>
> **⚠️ Fuori pista**: la revisione di sicurezza di E3 ha trovato che il cambio dell'email non chiede la password; con
> «password dimenticata» diventava una presa dell'account. La rotta anonima resta spenta (409) fino ad A6e (password
> attuale per cambiare l'email, chiusura delle altre sessioni). J ha trovato un MWRR sbagliato in circa il 4 % dei
> portafogli simulati (CP-4d, risolutore verificato). G ha trovato G-15 (barra delle schede di Settings che trabocca
> in spagnolo), affidato ad A.

### Lacuna 16/10 → 18/10, e lo STOP del developer (17/10, 21:45)

Il registro qui sopra si ferma al 15/10. Dal 16/10 sera al 17/10 sono entrati in `dev_release2` circa 280 lotti, con le
decisioni notturne del coordinatore N53–N92. Il 17/10 alle 21:45 il developer ha fermato tutto. Il resoconto completo
(stato, decisioni, errori di metodo) è nel file di sessione del coordinatore `resoconto-20261017.md`; la storia dei
lotti è nei piani dei figli e nel log di `dev_release2`.

### Ripartenza ✅ (2026-10-19)

**Regole nuove** (developer):
- nessuna decisione di prodotto dai figli né dal coordinatore: ogni scelta diventa una domanda per il developer;
- si implementa solo dopo il via esplicito;
- due slot pesanti alla volta; i lavori leggeri solo con carico a 1 minuto sotto 50.

**Pulizia:**
- ogni lavoro a metà è stato parcheggiato come patch nella cartella di sessione del figlio;
- il giornale di ogni figlio è committato;
- tutte le basi sono state aggiornate a `dev_release2` `ede7adf75`, che comprende Y-30;
- contabilità: tabelle dei lotti e ✅ del backlog con la prova del commit, per tutti i figli; le voci di Phase_0
  chiuse dalla 1.3 sono in corso di marcatura.

**Decisioni del developer, 19/10:**
- **Z-33**: resta solo la correzione del plugin Yahoo (la data locale). Escono la riparazione D″ e la migrazione 011,
  senza colonne, con i comandi manuali per la nightly del developer e per il suo DB di produzione (già alla 011,
  nessuna assegnazione Yahoo). Sulla 010 decide il developer.
- **J-57**: resta. Lo 0 manuale è permesso, il messaggio suggerisce «Manuale e 0» per un regalo, nel form e nel wizard.
  Aperte: Q-J57-1, Q-J57-3 (0 o costo del donante), Q-J57-4, J-60.
- **N68**: niente blocco; gli split sopravvivono al cambio di valuta; un bottone «Ricollega eventi» in Transazioni. Il
  ricollegamento automatico va in `TODO_FUTURI`, da analizzare.
- **N73, N76, N77, N84, N54, N87, N89**: confermate. Anche le tecniche N53…N82 sono confermate.
- **N74**: limite in avanti = domani del server. Aperta Q-N74-1: Fineco data le righe T+2.
- **N78**: la regola del costo esposta già calcolata dal backend, più un inventario degli endpoint con regole (W).
- **N81**: A. **MF-E2**: (b), cioè gli short nello storico con segni giusti e flussi completi.
- **N83**: per prezzi e cambi solo il limite in avanti (domani).
- **N92**: i prezzi negativi non si accettano (i). Per il «cancella» dell'OHLC c'è una proposta (`null` solo per l'API
  manuale) in attesa.
- **Lotti approvati e partiti**: J-1 (MF), X-R16 (X), J-48 (J), B-15 e B-8 (B), A-57 (A).
- **Sospesi in attesa del developer**: N90 (Z-29, da ridisegnare con `max_points` dal frontend), N91 (K3a, V-37b),
  H-55 (CSP applicata per direttiva), C-70b, i lotti di riordino di W non fatti (W3, W4 CP7, W5–W6, K2b/c), i lotti
  aperti di X (CP5, CP6, CP7, CP8, CP12).
- **Nuove analisi consegnate**: indici del DB (13 da togliere su 44), N74 (il motore salta già i giorni fermi), N64
  (cache dei segnali), N65 (il righello), N69 (amministrazione), testi dei controlli.

> **⚠️ Fuori pista**: il registro dei treni del README di Phase_1 si ferma al 370, e la tabella delle sessioni era ferma
> al 15/10: aggiornata oggi. Il backlog sottostimava il lavoro fatto (W: 7 ✅ invece di 56). Una mia affermazione su
> N92 («l'API accetta i prezzi negativi») era sbagliata: corretta da X.
