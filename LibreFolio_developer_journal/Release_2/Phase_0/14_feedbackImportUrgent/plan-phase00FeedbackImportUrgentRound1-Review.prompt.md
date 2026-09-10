# Round 1 - Correzioni dopo la review operativa E

**Data:** 2026-09-08.
**Origine:** feedback diretto del dev alle 16:34 e approvazioni UX aggiornate alle 17:08.
**Piano precedente:** [Feedback import urgente](plan-phase00FeedbackImportUrgent.prompt.md).
**Seguito U7:** [Round 2 - social icons and Copy and go](plan-phase00FeedbackImportUrgentRound2-Share.prompt.md).
**Stato:** completato 2026-09-09; dati originali ripristinati e build finale R2 disponibile per la review.

> **Ripresa 2026-09-09:** il dev riprende dopo perdita connessione/cambio postazione.
> Sorgenti, traduzioni, changelog e fixture consegnate sono presenti nel worktree,
> HEAD invariato `4a73f5f6`. La 6041 risponde ancora con PID 72570 del worktree E e
> hash build `3f50bf24...`: non contiene ancora R1/U4/U7/U9. Riattivato soltanto
> l'author con lavoro residuo U4 (il precedente seguito era una promessa senza file)
> e avviata review read-only Astra/max dell'integrazione. Gli altri writer hanno
> gia' consegnato e non sono riavviati per evitare sovrapposizioni. Chiesto nuovo
> stato/rilascio corsia a D e coordinatore; nessuna lease di ieri assunta valida.

La review della build `3f50bf24fd7bd5c89e804b3f7d7ffc01589724588772423312ea5503fc057389`
ha confermato le correzioni principali, ma ha richiesto semplificazioni UI e ulteriori
fix. Non e' una chiusura della corsia. Nessun dato del ledger privato entra in questo
round, nei test o nelle note.

## Risorse e ownership

- **Backup stato manuale: ✅ completato 2026-09-09.** Autorizzazione nuova del
  coordinatore prima di qualsiasi populate/reset. Snapshot privato fuori repository
  negli artifact di sessione (`private-e-test-backup-20260909-resume`): SQLite
  acquisito tramite backup API read-only/WAL-aware; uploads/report/sidecar, build
  e file manuali preservati. Nessun cambio DB/file osservato durante la cattura;
  archivio e hash verificati, directory 700 e file 600. Manifest SHA256
  `ddbf51c1b08d0a5b71693a358bb51fd3f8cfe9cda16ad5fa46dd46d6a6a59196`.
  Esclusi i soli log e i file SQLite live/journal, sostituiti dallo snapshot coerente.
  Nessuna riproduzione del ledger originale; build/runtime ancora invariati.
- E puo' modificare applicazione, documentazione e i18n via CLI.
- Fino alla restituzione esplicita dello slot dopo D: niente suite, build, API sync,
  riavvio server, DB/reset o modifiche all'istanza manuale esistente.
- Main E: ImportWizard, AssetModal, ModalBase, DataTable, BrokerModal, pagina broker,
  ChangelogModal, traduzioni, runner, changelog e integrazione.
- U4: FilesTable/pagina Files e filtro colonna condiviso solo se necessario, senza
  modificare DataTable o BrokerSharingPanel.
- U7: componenti supporto, DonationPopup e About; nessun social in header/login pubblico.
- U9: Header, menu e layout; il nuovo mandato include anche il desktop.
- Test nuovi/riparati tramite test-author. Nessuna suite delegata.
- Nessun commit, staging, push, migrazione o aggiornamento automatico.

## 1. File broker nel wizard - ✅ completato 2026-09-09

- **R1-01:** paginazione per tabella quando supera cinque file; default cinque,
  opzioni standard a partire da cinque, tramite DataTablePagination esistente.
- **R1-02:** entrando dopo upload, espandere i broker che hanno ricevuto i file e
  ripiegare gli altri; non perdere selezioni fra pagine o pannelli.

> **Note implementazione (2026-09-08):** R1-01/02 implementati nei sorgenti: pagine
> da cinque file, opzioni 5/10/25/50/100/tutti, pannelli aperti solo per upload
> riusciti della sessione corrente. Se non ci sono nuovi upload resta il comportamento
> precedente. Verifica esecutiva differita fino alla liberatoria D.

## 2. Form asset e testi - ✅ completato 2026-09-09

- **R1-03:** avviso della prima creazione molto piu' breve; manualita' prevista e
  riconoscimento successivo, senza lunga spiegazione dei codici.
- **R1-04:** precompilare il nome iniziale mancante con ISIN/ticker disponibile,
  mantenendolo modificabile e senza sovrascrivere un nome manuale. Non inventare
  altri metadati o dati finanziari. Rendere leggibili eventuali requisiti mancanti.
- **R1-05:** correggere i placeholder delle conferme cambio valuta, compresi prezzi
  e transazioni collegate; distinguere parametro della traduzione e valore passato.
- **R1-11:** tooltip Valuta in una frase: valuta in cui vengono salvati i prezzi.
- **R1-18:** confronto distribuzioni indipendente dall'ordine delle chiavi, rilievo
  emerso nell'audit read-only successivo alla prima integrazione.

> **Note implementazione (2026-09-08):** R1-04/05/18 implementati nei sorgenti:
> fallback nome iniziale ISIN/ticker e requisito visibile, parametri `n` corretti
> per prezzi e transazioni collegate, confronto distribuzioni condiviso e indipendente
> dall'ordine. Nessuna sovrascrittura reattiva del nome manuale.
>
> **Note implementazione (2026-09-08):** R1-03/11 e nuovi messaggi R1-04/06/09/10/13
> applicati via CLI nelle quattro lingue. Banner prima creazione e tooltip Valuta
> abbreviati; traduzioni del drawer e pannello rimossi eliminate, senza editing JSON.

> **Note implementazione (2026-09-08):** la domanda sul nome non ha raccolto una
> risposta esplicita (dev non disponibile nel canale ask). Si adotta il fallback
> piu' conservativo: solo identificativo gia' noto, non un nome finanziario inventato.

## 3. Broker - ✅ completato 2026-09-09

- **R1-06:** toast verde dopo cancellazione effettivamente riuscita, non al semplice
  click o in caso di blocco/errore.
- **R1-10:** errore di nome duplicato interamente localizzato nel canale esistente,
  mantenendo contratto testuale backend, status e informazione di ownership.
  Nessun nuovo error_code o DTO.

> **Note implementazione (2026-09-08):** R1-06/10 implementati nei sorgenti.
> Stessi messaggi testuali backend riconosciuti nel form e localizzati integralmente
> (proprio broker, altro proprietario, proprietario non disponibile, collisione 409).
> Toast verde solo dopo DELETE riuscita, con conteggio transazioni se eliminate.
> Riferimento broker catturato prima della chiusura del dialogo; nomi nei toast escaped.
>
> **⚠️ Fuori pista (2026-09-08):** test-author ha distinto i campi gia' esistenti
> `transaction_count` (blocco) e `transactions_deleted` (successo cascade). Il toast
> usa ora il conteggio corretto e cerca il risultato per broker ID, non per posizione.

## 4. Diagnostica e tabella bulk - ✅ completato 2026-09-09

- **R1-07:** rimuovere il nuovo pannello esplicativo delle righe coinvolte. Conservare
  il gruppo completo di evidenziazioni e navigare alla prima riga secondo l'ordine
  visualizzato; identita', pairing e filtri non devono produrre riferimenti errati.
- **R1-08:** con stickyActions=false anche l'header Azioni deve restare alla fine
  della tabella, non bloccato sul bordo destro.
- **R1-09:** rendere esplicito che 1a/1b sono numeri di riga visuali, variabili con il
  sort, distinti dagli ID persistenti e dagli identificativi interni stabili.

> **Note implementazione (2026-09-08):** R1-07/08/09 implementati nei sorgenti.
> Drawer eliminato; highlight completo e salto al primo ID nell'ordine filtrato/
> ordinato della DataTable, con pagina corretta. Se i filtri nascondono tutto si
> avvisa senza alterarli. Header Azioni vincolato a destra solo quando sticky;
> numerazione visuale indicata come Riga, con tooltip breve.

## 5. Aggiornamenti - ✅ completato 2026-09-09

- **R1-13:** nessun risultato persistente dentro Changelog. Ripristinare il toast
  verde quando aggiornato, con la versione remota realmente rilevata nella seconda
  riga. Conservare errori, assenza di release e immagine non verificabile distinti
  da un controllo riuscito; nessun ritorno al falso "latest" da null.

> **Note implementazione (2026-09-08):** pannello risultato rimosso dai sorgenti.
> Esito aggiornato produce toast verde a due righe, con tag remoto realmente letto;
> errori e release/immagine non disponibile restano avvisi distinti. Interpolazioni
> escaped per il canale toast HTML. Force refresh e versione backend restano invariati.

## 6. Documentazione e release - ✅ completato 2026-09-09

- **R1-12: ✅ completato 2026-09-08.** Ricomporre la tabella colonne Generic CSV: l'admonition interposta
  spezzava le righe successive.
- **R1-14:** iniziare il capitolo di preparazione per 1.1.1 in CHANGELOG.md; elencare
  modifiche effettivamente consegnate, senza dichiarare la release gia' pubblicata.
- Aggiornare le note di review e rieseguire le fixture modificate tardivamente dagli
  author prima della chiusura finale.

> **Note implementazione (2026-09-08):** docs-writer ha spostato l'admonition dopo
> la tabella intera, senza cambiare testi, nome guida o contratto Generic CSV.
> Nessun comando docs/runtime eseguito durante lo slot D.
>
> **Note implementazione (2026-09-08):** R1-14: aperto `[Unreleased]` con destinazione
> esplicita v1.1.1 e nota "in preparation". Include i fix E consegnati e le correzioni
> del round; nessuna data di pubblicazione, versione applicativa o tag inventati.

## 7. U4 - colonna uploader, variante approvata - ✅ completato 2026-09-09

Il dev sostituisce la precedente toolbar dedicata con una colonna uploader
ordinabile e filtrabile: avatar/icona, nome e selezione multipla nel filtro colonna,
come per gli asset. Riusare il filtro gia' generalizzato; estenderlo solo se manca
una capacita' necessaria, mantenendo i default degli altri consumer.

Identita' uploader diversa dal proprietario broker; utenti non risolvibili e uploader
assente non fanno sparire file. Nessun ampliamento dei permessi.

> **Note implementazione (2026-09-08):** colonna uploader implementata per risorse e
> report, con avatar/nome, ordinamento e filtro enum multiplo gia' esistente. URL
> `uploader` e filtri mantenuti passando lista/griglia. Lookup utenti autenticato:
> errori espliciti, ID non risolvibili e assenza distinti, risposta tardiva ignorata
> dopo unmount/cambio sessione. Nessun cambio a UserSearchSelect/BrokerSharingPanel.
>
> **Note implementazione (2026-09-08):** il lookup segue anche i cambi identita'
> del clientSession store: svuota subito nomi vecchi, refetch per nuova identita',
> stato idle a logout e unsubscribe a unmount. Risolve il busy sospeso che il
> test-author ha segnalato per un'istanza mantenuta tra due sessioni.
>
> **⚠️ Fuori pista (2026-09-08):** integrazione ha rimosso una nuova rune da una
> pagina ancora legacy (evitando la mescolanza con `$:`), sostituito un catch silenzioso
> e riusato renderer immagini/colori condivisi anziche' un secondo percorso HTML/hash.
> Verifica esecutiva ancora vincolata alla liberatoria D.
>
> **Note implementazione (2026-09-09):** autore U4 ripreso e consegna residua
> effettiva: lifecycle cambio identita'/logout/unsubscribe e nuovo E2E
> `files-uploader` (URL, lista/griglia, reload e avatar), registrato nel runner.
> **⚠️ Fuori pista:** l'avatar da 20 px incontrava un `min-width:32px` del renderer
> DataTable, diventando ovale. Rimossa la soglia fissa: le dimensioni esplicite e
> il default 32 px del renderer restano intatti, con flex-shrink disabilitato.

## 8. U7 - prima variante verificata, raffinamento richiesto nel Round 2

Implementare il blocco condiviso popup/About e la seconda modale di recupero manuale.
Le schede social non chiudono l'origine. Nessuna pubblicazione automatica o diagnosi
cross-origin; callback caffe'/Non ora invariati. Raffinamenti dopo la nuova prova.

> **Note implementazione (2026-09-08):** U7 integrato in DonationPopup/About con
> blocco condiviso, link X/Reddit in nuova scheda e fallback manuale in seconda
> modale. Solo messaggio localizzato e URL pubblico del progetto, mai dati dell'utente.
> Focus trap/restore opt-in su ModalBase; chiusure caffe'/Non ora e relativo
> selettore esistente preservati. Nessun social aggiunto a header/login pubblico.
>
> **⚠️ Fuori pista (2026-09-08):** integrazione ha aggiunto guardie alle risposte
> clipboard tardive (chiusura, cambio piattaforma/sessione e unmount), stato pending
> osservabile e contenuto popup scrollabile con footer sempre disponibile su schermi
> bassi. Il fallback clipboard condiviso esistente non controlla l'esito di
> execCommand: qui il rifiuto resta esplicito, con testo/link selezionabili a mano.

## 9. U9 - header su desktop e mobile, variante approvata - ✅ completato 2026-09-09

Il dev approva hide-down/show-up anche su desktop, superando il precedente vincolo
desktop invariato. Conservare geometria, controlli, safe-area, pin focus/menu/modali,
isteresi, reduced motion e cleanup; nessun salto o flicker.

> **Note implementazione (2026-09-08):** sorgenti U9 integrati per entrambi i
> formati: scroll documento normalizzato e rAF, isteresi 8/4 px, pin focus/sidebar/
> menu/body-lock modali, reset route/resize e cleanup observer/listener/frame.
> Transform mantiene l'altezza del layout; reduced motion disabilita la transizione.
> Pubblicati `data-scroll-state` e stati dei pin. Icona Help originale conservata.
> Verifica geometria/interazione differita alla disponibilita' runtime.

## 10. Verifica e seconda review - ✅ handoff completato 2026-09-09

Per ogni gruppo completato aggiornare subito questo piano con data, nota e detour.
Usare selettori mirati e una sola coda; confrontare payload reali, persistenza e
riapertura, non soltanto visibilita' o contatori. Poi nuova checklist operativa nella
chat E e handoff esplicito al coordinatore.

> **Note implementazione (2026-09-08):** author R1 import e bulk/update terminati:
> regressioni nome/distribuzioni/interpolazione/duplicati, file selection a pagine,
> broker delete reale e fallimenti, highlight/goto/sort e toast update. Nuovi selettori
> `tx-import-file-selection`, `broker-recovery` e BrokerModal component registrati.
> Author U4/U9 e U7 ancora sui soli file test; nessuna suite delegata/eseguita.
>
> **Note implementazione (2026-09-08):** integrati anche test autore U4/U9
> (FilesTable, Header, helper scroll e geometria browser) e U7 (URL, azioni,
> clipboard, popup e focus ModalBase), registrati in core-unit/component-unit e
> `header-scroll`. Piccolo seguito U4 ancora delegato: refetch identita' e
> composizione URL/lista/griglia. Esecuzione sempre bloccata sulla liberatoria D.

### Ripresa esecutiva 2026-09-09

- Nuova corsia E completa concessa esplicitamente dal coordinatore: non dipende
  piu' dal vecchio grant D. Backup privato completo prima delle prove.
- Primo `front check`: due errori circoscritti, attributo textarea non supportato e
  import `notify` mancante. Entrambi corretti; nuova esecuzione ancora da registrare.
- Componenti mirati: 470 passati, quattro fallimenti in tre file e dodici errori
  asincroni del filtro. Non e' un verde finale: author focus incaricato della
  diagnosi; mirror URL probe reso reattivo; misura rAF del filtro cancellata a
  unmount con regressione dedicata in authoring.
- Core mirati: **120 passati**, incluse classificazioni, matching, release,
  support links e lettura scroll. Log e nuovi snapshot automatici del runner
  conservati in area privata fuori repository.
- Review read-only Astra/max completata: una regressione confermata nel controllo
  duplicati finale, registrata sotto come R1-19.
- Al checkpoint senza comandi E attivi, ceduta esplicitamente a D una sola
  invocazione PURE `schemas pac-analyze`, su richiesta del coordinatore. E continua
  soli sorgenti e riprende il turno alla restituzione di quel comando; nessuna
  risorsa 6041/DB/build ceduta a D.

### R1-19 - conferma della selezione finale import - ✅ completato 2026-09-09

Il recheck finale poteva togliere righe selezionate diventate `likely` e passare
subito al bulk con un insieme ridotto, perfino vuoto. Il wizard resta ora in review
con avviso esplicito se la selezione cambia; controlla recheck concluso e
ammissibilita'/non-vuoto di nuovo prima dell'handoff. Nessuna selezione ambigua
forzata o validazione finanziaria rimossa.

> **Note implementazione (2026-09-09):** guardie e avviso nelle quattro lingue
> implementati; test-author matching riattivato esclusivamente per la regressione
> single-file con dati sintetici di proprieta'. Nessuna chiusura dichiarata prima
> della prova effettiva.

### Esiti effettivi 2026-09-09

> **Note implementazione:** build/API sync completati sul worktree E e frontend
> servito realmente, non dedotto dalla sola salute del processo. Typecheck:
> zero errori e warning. Core mirati 120 passati; componenti interessati verificati
> con retry circoscritti, inclusi 33 provider/broker e 20 paginazione.

| Percorso | Esito effettivo |
|----------|----------------|
| Inspector asset | 5 E2E: PATCH, GET, persistenza/riapertura, provider offline, partial clear e conferma valuta |
| FX manuale | 4 E2E: staging preciso, date indipendenti, commit finanziato, rifiuto senza scritture parziali |
| Matching e recheck | 4 casi candidati + 2 casi reali di selezione finale ridotta/vuota, poi scelta esplicita e payload corretto |
| Bulk | E7 gruppo completo/ordinamento/filtri/pagine/checkbox indipendenti; E8 pairing e payload immutati, header Azioni corretto |
| Selezione file | 2 E2E: pagine da cinque, folding e persistenza selezioni |
| Broker recovery | 5 E2E: successo vuoto/cascade e tre fallimenti senza falso toast verde |
| Uploader | 6 E2E desktop/mobile: URL, lista/griglia, identita' ignota/assente, avatar e fallback |
| Header | 4 E2E desktop/mobile: geometria, pin, flusso invariato e reduced motion |

> **⚠️ Fuori pista:** i rossi focus erano test DOM con shim `browser=false`;
> un errore broker a forma array non appartiene al DTO reale; un nodo testo vuoto
> non implica DOM senza figli. Corretti i contratti delle fixture. Il menu taglia
> pagina aveva invece un difetto reale: opzione cinque fuori dall'area ritagliata
> del bulk. Ora usa il posizionamento fixed condiviso e il click reale funziona.
> Reduced motion era gia' effettivo tramite `transition-property:none`: il test
> chiedeva erroneamente `duration=0`. Nessun aumento timeout o click forzato.

> **Note implementazione:** dopo scomparsa degli handle degli author in registry,
> E ha ripreso direttamente gli edit residui senza duplicare writer. Originale TEST
> fermo e preservato in area privata; ogni populate ha agito solo sul temporaneo.
> Restano controlli backend/documentazione/catalogo, prova operativa U7 e ripristino
> degli originali mantenendo la nuova build, prima dell'handoff finale.

> **Note implementazione finali (2026-09-09):** API classificazioni 4 passate,
> API duplicati broker 2 passate, equivalenza candidati BRIM 7 passate. Lint,
> catalogo/raggiungibilita', locale complete, build MkDocs strict e link controllati.
> Tabella Generic CSV verificata nel vero HTML generato: sette righe nello stesso
> elemento table, admonition dopo la chiusura.
>
> U7 ha ricevuto un ulteriore feedback del dev: implementato e verificato nel
> Round 2 collegato, che sostituisce la prima variante. Originale TEST ripristinato
> integralmente a processi temporanei fermi; CSV manuali invariati. Nuova build R2
> effettivamente servita su 6041/PID 68600, hash `ab8b1458...`.
> Nessun punto di implementazione resta aperto; la prossima prova del dev e'
> feedback operativo sulla consegna, non una validazione automatica dichiarata.
>
> **Debito fuori scope:** il controllo globale Source files della devWiki rileva
> riferimenti storici/generati gia' mancanti; corretta la riga obsoleta del parse API
> nella sola pagina toccata. Nessun rebuild globale wiki/graph, come richiesto.
