# 05 — Piattaforma Tool e allocatore PAC / ribilanciamento

**Complessità**: L piattaforma + XL allocatore completo · **Tipo**: feature-faro del round
**Origine**: nota utente · **Studio di riferimento**: `Release_2/guida_allocazione_pac_multi_etf.md`

> **Analisi e decisioni 2026-09-07**: lo scope è stato ampliato durante la pianificazione.
> La stima M–L del solo PAC euro buy-only non descrive più la richiesta completa.
> Fonte operativa: [06_piano_sprint.md](06_piano_sprint.md), T0/T1/T2 e SP12–14.
> La piattaforma C e il pilot PAC P1 sono integrati. Il redesign Round 2 completo
> resta attivo sul branch D; il solo `monetary_step` non ne costituisce la chiusura.
>
> **Piano C attivo:** [Piattaforma Tool atomica](../16_toolPlatform/plan-phase00ToolPlatform.prompt.md)
> — base generica completa; [handoff PAC D](../16_toolPlatform/handoff-pac-D.md)
> pubblicato, pilot reale aperto.

> **Raccordo decisioni 2026-09-08**: C/D hanno ripreso la progettazione, non il codice.
> Le scelte successive confermano righe/target asset-broker separati, copia OWNER-only
> a custodia intera e alternative A/B. Il passo monetario operativo è configurabile
> e generico; non è una preferenza di visualizzazione.

> **Autorizzazioni successive 2026-09-08, 15:48/15:51**: C può implementare la piattaforma
> completa nei propri file; D il solo nucleo iniziale P1 e i relativi test backend.
> Hub/About C approvati con link documentali locale-aware. Diagnostics Tool per tutti
> gli autenticati, job separato per item e tempi osservabili; niente nuova dipendenza
> `jsonschema`. Il server E resta riservato alla review manuale del dev. UI PAC, solver,
> copie e migrazione Broker non vengono autorizzati dal solo avvio del nucleo D.

## Motivazione originale

Un tool per aiutare nell'allocazione del PAC (Piano di Accumulo), usando lo studio di riferimento
pensato per Directa — che ha **vincolo di acquisto intero** (quote intere) e **allocazione in euro**.

Lo studio resta la base numerica, non una lista di costanti di prodotto. La sua parte finale
modifica obiettivi, budget e pesi rispetto all'inizio: esempi originari e criterio aggiornato
vanno distinti.

## T0 — Piattaforma backend a plugin

- Tutti i tool vivono come **plugin backend**, con modelli input/output, JSON Schema completi,
  versioni, capacità e limiti espliciti.
- **Revisione 2026-09-08**: catalogo completo, **compute bulk** e diagnostics; tutti
  autenticati, diagnostica sanitizzata accessibile a tutti gli utenti autenticati.
  Questo supera il precedente vincolo admin-only. Schemi già nel catalogo:
  nessun endpoint schema separato, nessun prefill sotto `/tools`.
- **Custom-first approvato**: il descriptor indica una chiave UI conosciuta; frontend
  seleziona componenti compilati, mai codice/URL/path arbitrari dal backend. UI standard
  automatica rinviata finché un secondo tool concreto non la giustifica.
- Servizio di esecuzione condiviso: validazione per item, correlation ID e ordine,
  risultati/errori isolati, output validato, CPU/queue/timeout/cancel limitati e dichiarati.
- Modelli Pydantic/TypeAdapter come fonte e validazione; schemi sempre derivati.
  Nessuno schema plugin manuale e nessuna dipendenza `jsonschema` aggiunta. Conservare
  i controlli di export supportato, riferimenti locali, strictness e descriptor.
- Il futuro **MCP** chiamerà gli stessi servizi passando parametri e principal autenticato.
  Server e librerie MCP non fanno parte di questo round.
- Plugin matematico separato dagli adapter di accesso al portafoglio: niente DB, HTTP,
  ricerca provider o scritture finanziarie durante il calcolo puro.

### Catalogo e letture dei dati
`GET /api/v1/tools/catalog` contiene ciò che serve per popolare hub/selettori e configurare
le UI custom: identità/versioni, nomi/descrizioni e chiavi i18n, icona/categoria, capacità,
schemi input/output completi, parametri/default/enum/unità/vincoli, limiti e chiave/versione
del renderer compilato. I default non sono prezzi correnti o dati personali.

I pulsanti "copia dal portafoglio" della UI interrogano **gli endpoint esistenti dei domini**
Portfolio/Broker/Asset/FX. Se manca un dato o un raggruppamento riusabile, estendere quella
API/servizio, non creare un secondo accesso Tool al portafoglio. Aggregazione economica,
conversioni e normalizzazione dei target restano backend; UI orchestra richieste e copia.
Questo stesso confine è riusabile dal futuro MCP.

### Compute eterogeneo e isolamento per item
`POST /api/v1/tools/compute` accetta anche più istanze dello stesso tool, con correlation ID
distinti. Una sola richiesta non equivale a un unico problema matematico: scenari diversi
richiedono calcoli distinti, isolati e limitati.

**Decisione 2026-09-08:** dati già preconfezionati e un worker per item, con parallelismo
reale entro i limiti dichiarati. In questa versione gli item identici non vengono
accorpati fisicamente, superando la precedente proposta di deduplica `analyze`.
Figli/processi/thread di un plugin sono ammessi solo se terminano con il job.
Restituzione sempre uno-a-uno, con ID/stato e tempi backend definiti e osservabili
anche nel frontend. Nessuna cache cross-user o nuova orchestrazione stateful futura.

### Diagnostics: cosa farebbe
`GET /api/v1/tools/diagnostics`, read-only per tutti gli autenticati, mostrerebbe plugin caricati/scartati,
errori di import/registrazione, codici duplicati o schemi non validi, versioni/capacità e
stato/limiti del pool (attivi/coda/disponibilità). Riusa i dati di discovery e dell'executor.

Non esegue tool o probe, non scarica prezzi, non resetta o ripara nulla; niente input/output
personali, credenziali o log grezzi dei job. Statistiche locali al worker dichiarate come
tali in deployment multi-processo, non spacciate per totali globali. Il backend non può
certificare da solo la presenza di un renderer nel bundle frontend.

Pannello nella sezione Plugin diagnostics di About. Hub e About riusano i link
documentali secondo la lingua frontend; verificare destinazioni/fallback effettivi,
senza avviare implicitamente una campagna di traduzione. Mount About dopo handoff E.

## T1 — Un solo modello matematico

- **PAC puro**: patrimonio iniziale zero e target scelto dall'utente.
- **Ribilanciamento**: patrimonio iniziale valorizzato.
- **PAC ribilanciante**: patrimonio iniziale più nuovo versamento.
- Input e target separati per **asset-broker**, anche per lo stesso asset su più broker.
  Chiave di riga opaca e stabile; identità dello strumento esplicita per vietare buy/sell
  dello stesso asset anche fra broker diversi. Non raggruppare dai nomi.
- Liquidità aggregata **per valuta**: EUR dai broker con EUR, USD dai broker con USD, ecc.
  Nessun vincolo di instradamento per broker; non trasformare tutto in una sola cassa.
- Liquidità aggiuntiva non ancora nel sistema: **lista valuta/importo**, separata da quella
  copiata dal portafoglio.
- Quote intere/frazionarie con passo esplicito; inserimento in quantità/valori con unità
  chiare. Percentuali iniziali richiedono un totale, non bastano da sole.
- **Vendite opzionali**, con minimo/massimo per titolo; distinguere minimo obbligatorio da
  minimo applicato soltanto se si vende. Nessuno short/leva implicito.
- **Conversioni FX opzionali** fra casse, con tassi, costi/margini, importi debitati/accreditati
  e liquidità finale per valuta. Disabilitate → nessun finanziamento incrociato implicito.
- Costi, buffer, riserve, bande target e vincoli non vanno inventati o rilassati silenziosamente.
  Nessun acquisto/vendita simultaneo dello stesso titolo o arbitraggio FX artificiale.
- Gate numerico prima del solver: precisione/quantizzazione, spareggi, limiti,
  commissioni e modello FX, fattibilità, no-trade, ottimalità provata e limiti operativi.
  Massimizzare gli acquisti non è un obiettivo corretto quando le vendite li possono finanziare.

### Passo monetario operativo e alternative — decisione 2026-09-08

**Parametro generico:** passo monetario positivo, decimale esatto, espresso nella valuta
della soglia operativa interessata. `0.01`, `0.1`, `1`, `10`, `100`, `1000` e valori
superiori sono esempi, non un enum né una restrizione alle potenze di dieci. Il passo
non va dedotto dai decimali di display o dalle sole unità minori ISO della valuta.

**Scope:** riguarda soglie operative usate dal calcolo, non l'arrotondamento grafico.
Il piano D deve mappare i campi interessati e lo scope della configurazione. Non implica
arrotondare indistintamente prezzi, FX, cash, quantità o tutti i min/max; il passo delle
quote intere/frazionate resta un vincolo diverso. Nessuna nuova colonna broker dedotta
automaticamente da questo parametro.

**Obiettivi riconfermati:** A minimizza prima il peggior scostamento delle righe target
in punti percentuali, poi l'errore quadratico complessivo. B massimizza l'investito nel
problema condizionale già deciso: A conservata come baseline immutabile, acquisti solo
mantenuti/aumentati, vendite congelate e vincoli hard originari preservati.

Il dev accetta sia arrotondamento per difetto sia HALF_DOWN: prevalgono gli obiettivi,
non una trasformazione cieca a posteriori della soluzione. Il solver deve considerare
valori ammissibili secondo il passo e valutarli con dati canonici esatti. Nessuna
tolleranza di spesa o fee conteggiata come investimento; nessuna pretesa di ottimalità
globale per B oltre il suo problema condizionale.

Questa specifica appartiene al contratto operativo completo. Il primo pilota `analyze`
descrive lo stato iniziale senza proporre ordini, soglie o settlement: può essere
progettato separatamente, senza attendere solver, copie portfolio o migrazione Broker.

## T2 — Hub, copie dal portafoglio e UI custom

- Voce **Tool sotto Transazioni** nel primo blocco della sidebar, quello dell'utente.
  `/tools` con griglia di card da catalogo; pagine dei singoli tool, senza una gallery vuota
  presentata come calcolatore funzionante.
- Input manuale sempre possibile, anche senza asset DB. Pulsanti espliciti e indipendenti
  per copiare situazione iniziale, prezzi o distribuzione corrente come base del target.
- Snapshot modificabili con preview delle sostituzioni; niente binding live, polling o
  risposte tardive che sovrascrivono modifiche dell'utente.
- Le copie usano i client delle API di dominio descritti sopra, senza route Tool di prefill.
- Copia solo da broker con ruolo **OWNER**, incluso OWNER con quota 0%; percentuale
  mostrata ma quantità/cash a **custodia intera**, senza scala di possesso. Scope
  richiesto autorizzato integralmente; dati mancanti non diventano zero e titoli non
  vengono esclusi silenziosamente.
- Righe asset-broker separate dai valori non arrotondati, denominatore del target chiaro,
  prezzo/valuta/quote-base/fonte/data conservati; cash contato una volta per broker/valuta.
- Grafici prima/target/dopo, scostamenti/bande, buy/sell e flussi cash/FX, accompagnati
  da tabella completa e diagnostica. Tutti i calcoli economici restano backend.
- Privacy globale sui valori personali del tool; nessun pulsante di esecuzione ordini,
  stima fiscale o raccomandazione automatica della strategia.

### Confronto UI obbligatorio — 2026-09-07
Prima della realizzazione: viste ASCII di hub/card, incompatibilità, editor, copie dal
portafoglio, vincoli, contributi per valuta, report/grafici e stati invalid/infeasible/busy/stale,
desktop/mobile. Annotare controlli e interazioni; raccogliere feedback misurato e ottenere
approvazione del dev prima del codice delle viste.

Dopo implementazione integrata: runbook dalla sidebar Tool agli scenari manuali/copiati,
calcolo e lettura del risultato, con ambiente/ruolo/dati di test e risultati attesi.
Raccogliere feedback operativo, correggere e riproporre prima di dichiarare conclusa la UI.
Non basta mostrare un mock funzionante o un esito dei test.

### Parallelismo
Concordati catalogo/compute e I/O PAC, possono procedere separatamente piattaforma backend,
modello/evaluator/solver, hub e UI/copiatore su fixture di contratto. Integrazione finale
su backend reale; un owner per file condivisi, client generato e i18n. Il calcolatore non
attende P4-1/BRIM/execute_batch. Mappa e risorse condivise nella sezione 11 del [piano](06_piano_sprint.md).

## Stato reale e dipendenze — 2026-09-07

Il PAC Planning di AI Export è un prompt, l'optimizer risk produce pesi continui da storia
rendimenti, Scheduled Investment è pricing di strumenti a rendimento programmato:
**nessuno è questo allocatore**.

Le primitive registry/schema/bulk/worker/controlli UI sono riusabili, non la semantica di quei
tre sottosistemi. Il tool non dipende dai grandi refactor P4; dipende dal suo contratto plugin,
dal modello numerico e dagli adapter di copia autorizzati.

| ID | Esito e taglia | Sprint |
|---|---|---|
| T0 | ✅ Piattaforma Tool custom-first integrata (`570beb386`). | SP12 |
| T1 — specifica/evaluator | 🟡 P1 integrato; Phase A numerica e contratto Round 2 preservati su D, integrazione/finalizzazione pendenti. | SP13 |
| T2 — snapshot | 🟡 Allocation source OWNER iniziale presente su D; catalogo completo, cash broker, privacy e fatti locked ancora in implementazione. | SP13 |
| T1 — solver | Aperto: solver buy/sell/FX e prova di ottimalità non iniziati. | SP14 |
| T2 — editor/report | 🟡 P1 integrato; redesign Round 2 completo riaperto dopo review respinta. Grafici/solver output restano aperti. | SP14 |

> **Aggiornamento 2026-09-11:** il primo server di review Round 2 mostrava solo
> il controllo contributi `monetary_step`; la review è stata respinta perché non
> rappresentava il redesign approvato. D sta eseguendo l'intera matrice gap
> (cash broker, funding-first, catalogo Owned/Other/Observed, fatti importati
> locked, editor current/target, quote base e polish) prima di una nuova review.

DoD, esempi numerici, superfici file:riga, rischi e oracoli indipendenti sono nel
[piano sprint](06_piano_sprint.md). Nessun server MCP o cambiamento dei motori FIFO/WAC
richiesto per consegnare il tool.
