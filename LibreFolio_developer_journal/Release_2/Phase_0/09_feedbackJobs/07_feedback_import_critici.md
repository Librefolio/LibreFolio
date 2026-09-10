# 07 - Feedback urgente: importazione, asset, FX e aggiornamenti

**Data:** 2026-09-08. **Origine:** nuovo feedback utente, successivo alla prima analisi.
**Stato:** ✅ completato dal **Gruppo E - Import e UX urgenti** e applicato al
checkout target `dev_release2` il 2026-09-09; commit/SHA manuale pendente.
**Baseline:** branch locale `dev_release2`, commit `4a73f5f6`.

Questo report apre una corsia urgente prima del restante backlog. Non dichiara gia
riprodotti o risolti i sintomi: cause, prove e avanzamento per-step appartengono al
[piano esecutivo E](../14_feedbackImportUrgent/plan-phase00FeedbackImportUrgent.prompt.md),
pubblicato e completato attraverso cinque round. Manifest:
[integrazione E](../14_feedbackImportUrgent/manifest-integrazione-E.md).

Rimandi: [piano generale](06_piano_sprint.md), [UX](01_ux_dashboard.md),
[BRIM/import](04_brim_import.md), [futuro deliberato](../../../../TODO_FUTURI.md).

## 1. Ordine e ownership

| Priorita | ID | Lavoro | Criterio di chiusura |
|---|---|---|---|
| Bloccante | E1 | Inspector asset del wizard si blocca su modifica/salvataggio | Flusso reale raggiungibile, save valido efficace e validazione non silente; nessun bypass delle protezioni. |
| Bloccante | E2 | Distribuzioni recuperate dal provider spariscono alla riapertura | Payload, persistenza, lettura e stato riaperto coerenti senza nuovo provider sync. |
| Bloccante | E3 | Applica/Verifica ora disabilitati su FX_CONVERSION apparentemente completa | Condizioni di completezza e pairing corrette, compreso il percorso locale dentro la bulk. |
| Bloccante | E4 | ISIN nel Generic CSV non associati ad asset esistenti | Estrazione/candidati/matching/riapertura corretti con fixture sintetiche e gestione esplicita dell'ambiguita. |
| Urgente, dopo E1-E4 | E7 | Diagnostica cassa negativa cita/evidenzia solo una riga | Tutte le righe effettivamente coinvolte sono elencate e raggiungibili/evidenziate con identita stabili. |
| Urgente, dopo E1-E4 | E8 | Inserimento storico resta in fondo alla tabella | Ordine stabile per giorno ASC/DESC anche con filtri; pairing e identita preservati. |
| Urgente, dopo E1-E4 | E9 | Nightly dichiarata aggiornata nonostante release stabile successiva | Scelta/confronto remoti corretti e banner che mostra la versione online realmente rilevata; errori non presentati come aggiornato. |
| Quick fix | E5 | Errore nome broker duplicato poco azionabile | Istruzione di rimedio esplicita, backend EN e UI nelle quattro lingue, stesso contratto/status/scope errore. |
| Quick fix | E6 | Specifica Generic CSV non evidenzia il vincolo per broker | Warning nella guida sviluppatori e nota devWiki pertinente, senza vietare multi-file o multi-valuta legittimi. |

**Chiusura 2026-09-09:** tutti gli ID E1-E9 sono implementati e verificati; il
dev ha completato la review operativa delle superfici richieste. La review
indipendente ha inoltre rilevato e fatto correggere il challenge pubblico GHCR
di E9 nel [Round 5](../14_feedbackImportUrgent/plan-phase00FeedbackImportUrgentRound5-GHCRAuth.prompt.md).
Il pacchetto e' nel checkout principale; non e' ancora committato o archiviato.

**Integrazione 2026-09-08:** E7/E8 ricevuti e presi in carico nel piano14 come task
distinti da E3. E9 aggiunto nella stessa data per il controllo aggiornamenti. Prima
E1-E4, poi E7/E8/E9 e quick fix; nessuna chiusura dichiarata dalla
sola segnalazione. L'ordine tra interventi sulla stessa tabella resta all'integratore E.

Il CSV e il primo ingresso di indagine richiesto dal dev. E1/E2 e U1/U5 condividono
AssetModal/wizard: un solo owner. E3 puo procedere nei propri form/helper; E4 nel parser
e matching, con integrazione del wizard concordata. Non duplicare scritture sullo stesso
componente solo per parallelizzare i quattro numeri del report.

**Scope ereditato da A:** U1, U5, U4, U7, U9 / SP01-SP02. Prima i blocchi; poi le altre
attivita UX. A resta fermo e i suoi piani/ASCII sono materiale di handoff, non un secondo
cantiere. Per U4/U7/U9 e ogni nuova/heavy UI resta necessaria approvazione ASCII del dev.
Il ripristino puntuale dei flussi esistenti non va trasformato in un redesign.

B resta in attesa della propria review operativa; il suo diff non e incorporato in questa
base E. **Ripresa autorizzata, 2026-09-08 11:30 CEST:** C/D tornano a contratti,
minimo pilota PAC `analyze`, dettagli numerici e ASCII nei propri artifact; nessuna
implementazione o chiusura implicita dei gate ancora aperti. E mantiene priorita urgente,
runtime e writer condivisi. About/supporto e relativa guida passano in sequenza **E -> C**.

## 2. Input reale e protezione dei dati

Il dev ha fornito un CSV locale. Percorso e hash di integrita sono nel kickoff/artifact
privato della sessione E, non nel repository. Il file originale rimane read-only.

Prima ispezione strutturale del coordinatore:

- UTF-8 senza BOM, separatore virgola; colonne `date,type,quantity,amount,currency,asset,description`.
- 34 righe; 22 celle asset non vuote, quattro identificativi distinti.
- Le 22 celle hanno forma ISIN dopo strip/upper; nessuna whitespace esterna o carattere
  invisibile rilevato, nessuna riga con campi eccedenti.
- Nessuna colonna broker: la sola forma del file non dimostra l'appartenenza a un unico conto.

Questi dati escludono alcune ipotesi banali ma **non provano la causa** del mancato matching.
Il parser attuale gia normalizza gli ISIN. L'indagine deve arrivare a candidati, stato
del catalogo e selezione del wizard.

**Prima esecuzione locale del parser da E (2026-09-08):** 24 transazioni accettate,
10 violazioni di validazione, zero warning e quattro gruppi asset. I quattro ISIN
originari restano esatti negli hint `extracted_isin`. Coerenza del CSV e validita
transazionale non sono equivalenti: le dieci violazioni vanno spiegate separatamente,
senza allentare il contratto e senza attribuire loro automaticamente il mancato matching.

Non committare il ledger reale, ne trasformarlo in un fixture soltanto togliendo il nome.
Usare nuovi dati sintetici con la stessa struttura/relazione che riproduce il difetto;
nessun import del ledger privato in produzione. Non inviare righe, descrizioni o importi
a provider, servizi esterni o issue pubbliche.

## 3. E1 - Freeze dell'inspector asset nel wizard

**Sintomo:** ultimo step import; Ispeziona/Modifica apre l'asset, ma cambi valuta/edit
manuali lasciano Salva Modifiche inerte, senza mutazione/API valida.

**Prima traccia codice:** `ImportWizardModal.svelte:2479-2501`, `openAssetInspector`,
legge `/assets/query` e assegnazioni; il mount a `4721` passa `AssetModal` in edit e
`zIndex=90`. Gli stati provider, metadata e salvataggio vivono anche in AssetModal.

Verificare binding/revisione del draft, validazioni, eventi, scheduler e overlay annidati
(z-index/focus compresa AssetCurrencyChangeModal). Le conferme comuni hanno gia z-index
relativo: non attribuire il problema a tutte le modali senza riproduzione.

**Riproduzione browser riferita da E, 2026-09-08:** con un prezzo salvato su un asset
sintetico proprio, il cambio valuta e il Save sono raggiungibili; il PATCH restituisce
il `409` previsto dalla protezione dei market data. La conferma esiste a z-index 50,
sotto l'inspector a 90: il punto centrale del pulsante intercetta contenuto
dell'inspector, non la conferma. Il salvataggio del solo nome invece funziona.
E1 e quindi delimitato a una conferma annidata irraggiungibile, non a un freeze
generico delle validazioni. Nessuna conferma forzata o cancellazione dei dati.

**Integrazione riportata da E, 2026-09-08 12:41:** correzione dello stack e loader E2
integrati nel worktree, chiusura ancora pendente. Conservare il `409` e la conferma
esplicita; stack relativo al padre anche fuori wizard, senza bypass delle protezioni.

**DoD:** salvataggio valido produce l'effetto previsto nel contesto corretto; input
invalido ha motivo visibile. Nessun bypass di protezione cambio-valuta/market-data,
nessuna conferma nascosta, nessun risultato vecchio applicato al nuovo draft.

## 4. E2 - Distribuzioni perse o non ricaricate

**Sintomo:** Chiedi al provider mostra settori/geografia; dopo save e riapertura la
distribuzione e vuota e serve ripetere la sincronizzazione.

Seguire tutta la catena: provider response -> draft -> patch/create payload -> DB ->
nuova lettura API -> store/cache -> `editData` e controlli. Distinguere mancata
persistenza, risposta parziale e cache/rehydration obsolete.

Il callback inspector attuale chiude e invoca `refreshAllAssets` senza await: e una
superficie da verificare, non una causa gia accertata.

**Riproduzione browser riferita da E, 2026-09-08:** su baseline E/TEST, con account,
broker, asset e CSV interamente sintetici, il GET completo contiene descrizione,
settori e geografia. L'inspector del wizard mostra quei campi vuoti pur conservando
la quote base. Modificando solo il nome, un PATCH riuscito invia
`classification_params:null`; un nuovo GET conferma nome aggiornato e classificazione
cancellata nel DB. **L'omissione nel modello di lettura diventa quindi una scrittura
distruttiva**, non soltanto una visualizzazione vuota o una cache obsoleta.

**Coupling backend riprodotto da E via API, 2026-09-08 12:41:** un PATCH con il solo
`sector_area:null` cancellava anche geografia e descrizione. La serializzazione con
`exclude_none=True` riduceva il blocco a `{}`, interpretato come cancellazione totale.
Fix riportato limitato alla serializzazione classification, preservando null espliciti.
Guardia richiesta: conservare anche i campi omessi, senza materializzare altri null
dai default del modello.

Loader completo condiviso wizard/list e payload frontend field-aware sono ora integrati
nel worktree E: classificazione invariata omessa, soli blocchi modificati inviati,
clear parziale/totale distinti. Chiusura integrata ancora pendente. Vietare ogni `null`
indistintamente non sarebbe una soluzione corretta; nessuna nuova migrazione/contratto
richiesti dal fix. Nessuna riproduzione sul server del dev o con il ledger privato.

**DoD:** round-trip dimostrato con nuova richiesta dopo save e riapertura; valori uguali
a quelli memorizzati senza contattare nuovamente il provider. Annullamento, errore,
risposte tardive ed edit concorrenti non perdono o sovrascrivono dati.

## 5. E3 - Form FX paired bloccato

**Sintomo:** broker, date DA/A e importi EUR/USD apparentemente completi; Applica e
Verifica ora restano disabilitati.

`TransactionFormModal.svelte:732` usa `isDraftReadyForValidation(draft)` e richiede anche
`dualTo.broker_id`. `setBroker:1142` sincronizza il lato TO quando il layout e gia FX;
i pulsanti a `2050/2079` dipendono da completezza, sign e `dualValidationError`.

Indagare inizializzazione/cambio tipo, broker precompilato o nascosto, parsing decimale
locale, date e valori del partner, non soltanto i campi disegnati a schermo.

**Checkpoint sorgenti da E, 2026-09-08 11:40 CEST:** `buildDualCreatePayloads(fx)`
usa `TO.date || FROM.date`; date esplicite diverse sono quindi legittime. E ha corretto
il detour che imponeva una data comune: il derivato FX riguarda solo il broker nascosto,
non sovrascrive data TO o swap delle date. Normalizzazione dei segni senza conversione
`Number()` per preservare le stringhe decimali; nessuna normalizzazione dello storico
in view. Implementazione riportata, chiusura integrata ancora pendente nel piano14.

**DoD:** validazioni e pairing restano rigorosi; nessun semplice sblocco forzato del
bottone. Applica dentro bulk aggiorna il draft e non viene scambiato per un commit DB;
Save All/validate usano il percorso reale. Input incompleto/invalido viene spiegato.

## 6. E4 - Auto-matching ISIN

`broker_generic_csv.py:622-643` gia classifica stringhe ISIN e le converte in maiuscolo;
`_parse_row:548-619` produce hint/fake ID e usa un broker per file.

Verificare ricerca locale per identificatori primari e alternativi, attivi/inattivi,
formato degli hint, candidati e regola di selezione automatica, cache last-parse e
invalidazione dopo creazione/modifica asset. Conservare il contratto corrente
`FAKE_ASSET_ID_BASE`: non introdurre ID fittizi incompatibili seguendo documenti vecchi.

**Contratto verificato sui sorgenti da E, 2026-09-08 11:40 CEST:**
`brim_provider.search_asset_candidates` combina primary EXACT e alias HIGH sul medesimo
ISIN, deduplica lo stesso asset e restituisce selezione `null` se restano piu asset
distinti. La ricerca fuzzy ticker/nome avviene solo in assenza di quei candidati ISIN;
il percorso bulk segue la stessa regola. Il fallback frontend sovrascriveva invece
quel `null` deliberato scegliendo il solo EXACT. Il fix deve ripristinare il contratto
backend, non introdurre una diversa gerarchia di confidence. Ricerca di primari,
alias e asset inattivi gia funzionante secondo E; snapshot last-parse congelati per
design. Nessuna modifica backend/parser/versione giustificata da queste evidenze;
correzione frontend in corso, non ancora chiusa.

**Controprova browser baseline E, 2026-09-08:** nel percorso sintetico usato per E2,
un ISIN primario univoco viene gia autoassociato prima dei fix. Non e dimostrato un
fallimento generale dell'estrazione/matching ISIN: delimitare E4 ai casi di refresh,
snapshot/stato obsoleto e autorita della selezione/ambiguita effettivamente riprodotti.

**DoD:** asset esistente prima del parse riconosciuto; comportamento coerente dopo
riapertura/aggiornamento catalogo; candidati ambigui non selezionati arbitrariamente.
Fixture di regressione sintetiche, dati propri del test, nessuna dipendenza dal DB reale.
Se cambia output parser, gestire versione/staleness; niente correzione ad hoc dei
sidecar o delle righe di produzione.

## 7. E5/E6 - Quick fix

**Broker duplicato:** aggiungere il rimedio alla stringa esistente, preservando
contratto, status e scope della verifica:

> To resolve this, rename the existing broker or choose a different name for the broker you are adding.

UI italiana richiesta:

> Per risolvere rinomina il broker esistente o cambia il nome di quello che stai provando ad aggiungere.

**Precisazione da codice E, 2026-09-08:** `BRCreateResult` espone un `error` testuale
inglese, con varianti owner/self/no-owner; non espone `error_code` e non esiste un
resolver broker dedicato. Usare il canale errore esistente e chiavi i18n per il rimedio,
aggiornando EN/IT/FR/ES via CLI. Nessuna migrazione o nuovo protocollo errore per questo
fix; non inserire HTML non fidato o cambiare la regola di unicita.

**Generic CSV:** warning EN nella guida esistente
`mkdocs_src/docs/developer/backend/brim/generic_csv.md`:

> IMPORTANT: Generic CSV input must use one separate file per broker. A single flat CSV containing transactions from multiple brokers is not supported.

Un file per broker **non** significa un file per valuta: righe in valute diverse dello
stesso broker e import multi-file con broker diversi restano supportati dove gia previsti.
Usare docs-writer per MkDocs e project-historian per la nota devWiki pertinente; nessuna
campagna globale o rigenerazione completa del grafo per questa puntualizzazione.

## 8. E7 - Tutte le righe coinvolte nella diagnostica di cassa

**Segnalazione e presa in carico, 2026-09-08:** il messaggio di liquidita insufficiente
indica soltanto una riga iniziale, ma nella stessa giornata altre transazioni pertinenti
contribuiscono al problema. Il click deve evidenziare tutte le righe coinvolte, non solo
quella iniziale. Task separato dal completamento del form FX E3.

**Superfici candidate:** risultato di validazione e sua mappatura nel draft, diagnostica
cash/broker/valuta, messaggio e azione di navigazione/evidenziazione nella tabella bulk.
Seguire il percorso reale del checker prima di decidere dove correggere il contratto.

**Vincoli:** ricostruire l'insieme completo dei contributori effettivi al problema,
rispettando data, broker e valuta. Identita transazione/draft stabili, non indici della
vista; nessuna inclusione indiscriminata di righe dello stesso giorno appartenenti ad
altri broker/valute. Ordinamento, filtri e paginazione non devono rendere il click
parziale o silente: tutte le righe coinvolte devono restare raggiungibili ed evidenziate.

**DoD:** scenario sintetico con piu righe pertinenti nella stessa data e righe estranee;
messaggio completo e click coerente prima/dopo filtri e ASC/DESC. Distinguere una gamba
coinvolta dalla mera presenza della sua controparte; pairing/identita conservati.
Checker e criteri finanziari invariati: la correzione riguarda la spiegazione e la
navigazione, non l'accettazione di un saldo negativo.

## 9. E8 - Ordine cronologico stabile dopo inserimento storico

**Segnalazione e presa in carico, 2026-09-08:** una conversione aggiunta con data
precedente resta in fondo alla tabella. L'ordine deve seguire il giorno ASC/DESC, anche
con filtri cash/broker/asset; l'ordine d'inserimento non puo dominare la data.

**Superfici candidate:** proiezione delle righe bulk e delle coppie, stato sort,
filtri e integrazione locale con DataTable. E7/E8 condividono questa superficie:
un solo owner, non due riscritture concorrenti.

**Vincoli:** ordinamento deterministico con tie-break stabile dentro il giorno,
identita delle transazioni/draft e ghost row preservata. Per coppie con date diverse
rendere esplicita la semantica del raggruppamento, senza perdere o duplicare le gambe.
Non riordinare il ledger logico o il payload per aggirare la validazione, non cambiare
indiscriminatamente i default globali di DataTable.

**DoD:** nuove righe storiche nella posizione cronologica corretta in ASC e DESC,
anche dopo applicazione/rimozione dei filtri; righe dello stesso giorno stabili.
Modifica, selezione, diagnostica E7 e pairing continuano a riferirsi alle identita
corrette, non alla precedente posizione visuale.

**Confine comune E7/E8:** osservazioni manuali del dev su produzione, non autorizzazione
per E ad accedere a `6040`. Riproduzione solo nel runtime TEST assegnato, con scenari
sintetici. Date, importi e indicazioni finanziarie private non entrano in piani,
repository, fixture o log; nessun agente crea cash o transazioni nel DB di produzione.

## 10. E9 - Controllo aggiornamenti nightly/stable e versione remota visibile

**Segnalazione e assegnazione, 2026-09-08:** il dev riporta un'installazione server alla
nightly visualizzata come `1.0.1-114`. Il controllo manuale dichiara che e aggiornata,
nonostante la release online `1.1.0` segnalata dal dev. Causa ancora da dimostrare,
nessun accesso all'installazione del dev autorizzato.

**Richiesta UI:** quando il banner dichiara aggiornato, mostrare anche la versione
effettivamente rilevata online, per esempio:

> Versione online rilevata: {version}

Il valore proviene dal risultato remoto usato da quel controllo, non dalla versione
installata o da una costante. Conservare coerenza con il banner di aggiornamento
disponibile. Errore, assenza di release o dato obsoleto non sono un controllo riuscito.

**Indagine:** versione locale effettiva e sua normalizzazione; repository/endpoint e
metadati pubblici della release; policy canali stable/nightly/prerelease; scelta della
candidata; cache/TTL/refresh; confronto; risposta API e rendering/stato del banner.
Secondo SemVer `1.1.0` e successiva a `1.0.1-114`: non confrontare un contatore nightly
prima di major/minor/patch. Questo non prova da solo che il bug sia nel comparatore.
Riutilizzare helper/librerie esistenti e non cambiare implicitamente la policy canali.

**Baseline da distinguere:** ispezionare anche la revisione corrispondente alla nightly
rilasciata, se identificabile via Git/API read-only. Un fix nella versione nuova non
modifica il vecchio deployment: riportare separatamente eventuale limite bootstrap e
passaggio manuale necessario, senza fingere che il server del dev sia stato corretto.

**Superfici candidate:** servizio/API del version check, provider/cache delle release,
helper di versione, banner e integrazione About. Un solo writer del banner/About in E,
coordinato con U7; nessuna modifica collaterale ai componenti B o al futuro pannello C.
La semplice informazione aggiuntiva non richiede un redesign.

**DoD:** caso riportato, uguaglianza, locale piu recente e prerelease coerenti con
la policy; metadati mancanti/malformati, errori e refresh osservabili; versione remota
reale visibile nel banner. Regressioni deterministiche via test-author con risposte
sintetiche, non dipendenti dalla release live. EN/IT/FR/ES via CLI; API typed/codegen
solo se serve, nella coda E. Nessuna migrazione DB o dipendenza aggiunta per ipotesi.

**Chiusura E9 / Round 5, 2026-09-09:** la review indipendente ha dimostrato che
GHCR richiede il normale challenge Bearer anche per l'immagine pubblica e che il
browser non puo' completarlo in modo affidabile via CORS. Il probe immagine e'
quindi un endpoint same-origin autenticato: repository/tag fissi, challenge e
realm verificati, token pubblico senza credenziali, errori auth/manifest distinti
e nessun fallback di successo. Il client mantiene cache/dismissal e mostra la
versione remota reale. Passano 30 casi backend, 30 core frontend e 24 componenti;
API sync idempotente, type-check/build verdi.

**Confini:** sola lettura dei metadati pubblici GitHub, nessun token nei log; nessun
accesso a `6040` o al server del dev, deploy, auto-update, cambio canale o riavvio
produzione. E1-E4 mantengono priorita e tutte le operazioni runtime restano seriali.

## 11. Cosa NON va implementato in questo hotfix

I tre approfondimenti multicurrency/esposizione sono aggiunti a
[TODO_FUTURI.md](../../../../TODO_FUTURI.md), con gate economici separati:
settlement multicurrency implicito, proposte FX automatiche opt-in e valuta
base/esposizione valutaria.

Niente FX nel parser BRIM, transazioni di cassa inventate o consistency checker
indebolito per far passare un import. Nessuna nuova colonna Asset o torta di esposizione
in E. Un ETF sul Giappone non dimostra da solo una valuta base JPY o esposizione JPY pura.

La configurazione broker `allow_fractional_buys` resta nel piano D: migrazione
incrementale, default whole-only per gli esistenti, senza riscrivere transazioni
storiche. Il dev l'ha ribadita; non viene duplicata in E.

## 12. Esecuzione, risorse e chiusura

Durante l'esecuzione E e' stato l'unico owner di runtime/test/build/API sync,
generated client, runner e i18n. Le verifiche sono state serializzate e le fixture
sono sintetiche. Il pacchetto finale e' ora nel checkout target; eventuali nuove
prove appartengono alla validazione integrata, non riaprono automaticamente E.

Bootstrap dipendenze soltanto dopo mancanze osservate, dai lock senza upgrade impliciti.
API cambiate -> api sync; i18n via CLI; codice/commenti inglesi. Nessun commit/push,
rebase/reset/staging o bonifica di dati reali.

Pubblicare il piano esecutivo 14, aggiornarlo dopo ogni step con data/nota/detour e
collegarlo a questo report. Per nuove/heavy UI approvazione ASCII prima, review
operativa dopo con percorso, ruolo, fixture, click, attesi e feedback. Non chiamare
risolto un bug solo perche un container e visibile o un'API generica risponde.
