# Dossier — Piattaforma Tool

**Redatto da:** sessione «Piattaforma tool» (branch `e-alfy-tool-platform-c-r2`, HEAD `8e7259ecc`)
**Data:** 2026-09-11
**Destinatari:** developer in revisione · prossimo autore di plugin Tool
**Artefatto recensito:** `dev_release2` — **non** il checkpoint congelato di questa sessione

---

## 0. Avvertenza di lettura — leggere prima di tutto il resto

Questa sessione ha costruito la piattaforma, l'ha congelata a `8e7259ecc` e l'ha consegnata.
La piattaforma **non è entrata in `dev_release2` per conto proprio**: è stata fusa dentro il ramo
dell'allocatore PAC e ha raggiunto il target dentro il merge `3913fe217`. Verificato, non assunto:

```
git rev-list --left-right --count dev_release2...e-alfy-tool-platform-c-r2  →  82   0
```

Zero commit avanti: tutto dentro. Ma il codice che il developer sta per revisionare **non è quello
che ho congelato io**. Fra `8e7259ecc` e `dev_release2` sono atterrate **891 inserzioni / 271
delezioni su 15 file di piattaforma**, più un file nuovo (`backend/app/services/tools/resources.py`,
181 righe) che nel mio checkpoint non esisteva.

Le modifiche post-freeze non sono cosmetiche. Sono tre:

| Cambiamento | Da (mio checkpoint) | A (`dev_release2`) |
|---|---|---|
| ABI del plugin | `ToolPlugin[InputT, OutputT]`, un tool per classe | `ToolPlugin` non generica, `services: tuple[ToolService, ...]` (1–16) |
| Firma di calcolo | `compute(parameters, context)` | `compute(tool_code, parameters, context)` |
| Contenimento memoria | inesistente | `resources.py`, cgroup v2 hard / osservato, `memory_limit` |

Più l'inviluppo di capacità 30 / 44 / 45 / 5 / 59 / 65 s e 1 GiB, che deriva dal report di capacità
che ho prodotto in questa stessa sessione ma che **ho progettato senza implementare**.

**Conseguenza operativa per questo dossier:** ogni affermazione al presente («la piattaforma fa X»)
è stata riverificata contro `dev_release2`, non contro il mio HEAD. Dove la distinzione conta —
§1 (l'arco), §4 (i consumatori) — separo esplicitamente ciò che ho progettato io da ciò che è stato
cambiato dopo. Non rivendico il lavoro post-freeze e non lo scarico: lo descrivo come l'ho letto.

**Nessuna suite è stata eseguita in questa sessione.** §8 descrive che cosa i test *asseriscono*,
letto nel sorgente. Non è un rapporto di esecuzione, e non contiene totali verdi.

**Questo documento è autoportante.** La sessione che l'ha scritto viene archiviata subito dopo la
consegna e il suo worktree rimosso: non ci sarà nessuno a cui chiedere che cosa intendeva il
contratto. Perciò dove normalmente rimanderei a un round di piano o a una discussione, qui c'è la
cosa in sé — in particolare le scelte **decise** anziché derivate (§3.3), l'aritmetica da cui
discendono i budget (§2.7.2) e le trappole che il codice non spiega da solo (§2.7.3, §5).
Non richiede alcun altro artefatto per essere usato.

---

## 3. Il confine tracciato — dove la piattaforma smette di rispondere

Comincio da qui perché è la parte che un diff non mostra: una piattaforma si giudica da ciò
che si rifiuta di fare.

### 3.1 Cosa possiede la piattaforma

| Responsabilità | Dove vive |
|---|---|
| Ammissione, code, corsie, capacità | `services/tools/executor.py` |
| Scadenze assolute, soft/hard/cleanup, cancellazione | `executor.py` (`_start_job`, `_run_owned_job`) |
| Ciclo di vita del processo figlio, ACK di pronto, protocollo a frame | `executor.py` + `services/tools/worker.py` |
| Proprietà dell'albero dei discendenti, reaping, rilascio credito | `services/tools/process_tree.py` |
| Contenimento e osservazione memoria | `services/tools/resources.py` |
| Scoperta, quarantena, collisioni di codice | `services/tools/registry.py` |
| Catalogo, clamp delle policy, versioni pubblicate | `services/tools/catalog.py` |
| Contratto di filo, codici d'errore, metriche | `schemas/tools.py` |
| Esportazione schema e codec generati | `services/tools/schema_export.py` + `./dev.py api sync` |
| Trasporto tipizzato, cache catalogo, correlazione risposte | `frontend/src/lib/features/tools/client.ts`, `contracts.ts` |
| Registro dei renderer compilati, host, hub | `frontend/src/lib/features/tools/registry.ts` + `ToolHost` |

### 3.2 Cosa possiede il plugin

Il dominio, e soltanto il dominio: i modelli Pydantic d'ingresso e uscita, la matematica,
il significato finanziario del risultato, il proprio renderer compilato, la propria pagina di
documentazione, le proprie policy dichiarate per operazione.

### 3.3 Dove ho rifiutato responsabilità, e perché

Questi rifiuti sono deliberati. Ciascuno era una richiesta plausibile a cui ho detto di no.

1. **Nessun principal, sessione DB, client provider o autorità di portafoglio nel worker.**
   Il figlio riceve parametri serializzati e nient'altro. L'API autentica; il calcolo no.
   Motivo: un processo che può scrivere è un processo che, quando viene ucciso a metà, lascia
   scritture parziali. La capacità di uccidere duramente e la capacità di scrivere sono
   incompatibili, e ho scelto di conservare la prima.
2. **Nessuna scrittura finanziaria, nessun fetch live da provider dentro il calcolo.**
   Stessa radice. Il chiamante raccoglie i dati tramite le API di dominio autorizzate *prima*
   di sottomettere l'item.
3. **Nessun endpoint di job, di stato o di cancellazione.** Tre endpoint in tutto: catalogo,
   compute eterogeneo in bulk, diagnostica in sola lettura. Un endpoint di cancellazione avrebbe
   richiesto un registro di job persistente e una nozione di proprietà del job attraverso le
   richieste. Abortire l'HTTP ferma l'attesa del client; **non è un ACK di cancellazione lato
   server** — e ho preferito che questo fosse ovvio invece che mascherato da una API che finge.
4. **Nessuna cache dei risultati, nessuna deduplicazione fisica fra utenti o richieste.**
   Due item identici sono due job. Un risultato finanziario riusato fra utenti è una fuga di dati
   in attesa di accadere, e il guadagno era marginale.
5. **Nessun percorso di modulo, URL o codice fornito dal server per la UI.** Il registro dei
   renderer è un elenco di import compilati. Un renderer sconosciuto o incompatibile rende il tool
   *non disponibile*; non fa ripiegare su un form finanziario generico né esegue nulla di remoto.
6. **Nessuna semantica finanziaria nella piattaforma.** Limiti di esecuzione, crash, output non
   valido e cleanup fallito sono **errori di piattaforma**, mai infattibilità fabbricata, mai un
   risultato a zero. La piattaforma non sa cosa sia un piano PAC e non deve impararlo.
7. **Nessuna promessa di memoria su host non delegati.** Poteva essere nascosto dietro un
   booleano `memory_limited: true`. Il contratto invece espone `capabilities.memory.mode` con tre
   valori distinti. Vedi §5.2: la scelta è onesta sul filo ed è resa invisibile dalla UI.
8. **Nessuna schedulazione, persistenza, retry o coda durevole.** La capacità è per processo API,
   non per installazione, e la documentazione lo dice.

### 3.4 Dove la cucitura perde — onestamente

Questi non sono difetti nascosti: sono i punti in cui il confine è una convenzione, non un muro.

**(a) L'isolamento è di processo, non di privilegio.** Il figlio è un processo `spawn` separato,
ma importa il pacchetto dell'applicazione per risolvere il registro dei plugin. Niente impedisce
tecnicamente a un plugin di importare `app.db` o un modulo provider e aprire una connessione.
Non c'è import hook, seccomp, namespace o filesystem in sola lettura. **Ciò che tiene il confine
è la revisione del codice, non la runtime.** La documentazione per sviluppatori lo afferma
esplicitamente («non è una sandbox del sistema operativo»); lo ripeto qui perché è la premessa
di tutto il resto.

**(b) La cancellazione cooperativa dipende dal plugin.** `context.checkpoint()` è l'unico modo in
cui il codice del plugin può accorgersi di aver superato il budget soft. Un plugin fermo dentro una
chiamata nativa lunga (un solver C, per dire) non lo chiamerà mai. Per quel caso resta solo il kill
duro — che funziona, ma è un errore di piattaforma, non una terminazione ordinata. La piattaforma
**non può** fermare un motore nativo; può solo ucciderne il processo.

**(c) Il budget del motore è dichiarato dal plugin e auto-imposto dal plugin.** `engine_timeout_ms`
descrive quanto il plugin *promette* di lasciare al motore. La piattaforma lo limita verso il basso
ma non lo può far rispettare dall'interno. Vedi §5.3 per la trappola concreta.

**(d) La memoria è dichiarata dal plugin ma contenuta dalla piattaforma solo a volte.**
Il plugin scrive `memory_limit_bytes` nella propria policy. Su un host Linux con cgroup v2 delegato
e scrivibile quel numero è un muro; altrove è una soglia campionata. Il plugin non ha modo di sapere
quale dei due riceverà, e non c'è oggi un modo per un plugin di dire «rifiutati di eseguirmi se non
sei in modalità hard».

**(e) Accoppiamento di versione fra servizi fratelli.** Dopo la ristrutturazione multi-servizio,
`contract_version` e `implementation_version` vivono sulla **classe plugin**, mentre `tool_code`
vive sul servizio. Due tool esposti dalla stessa classe condividono quindi le versioni: alzare il
contratto di uno **forza** il bump dell'altro, invalidando le richieste in volo di un tool che non
è cambiato. È un costo reale introdotto dal multi-servizio, ed è la ragione per cui `services` ha un
tetto (`_MAX_SERVICES_PER_PLUGIN = 16`) invece di essere illimitato.

**(f) Il tetto di risultato è per item, non per risposta.** `max_result_bytes` (262 144 di default)
è applicato a ogni item. Un batch di quattro item al limite produce una risposta vicina al megabyte.
Non c'è un tetto aggregato di risposta.

---

## 5. Semplificazioni e modi di fallimento

Apro con la lista che conta: **le cose che producono un risultato plausibile ma sbagliato invece di
fallire in modo visibile.** Sono sei, in ordine di pericolosità.

### 5.1 — La modalità di enforcement della memoria è invisibile all'operatore ⚠️ *la riga più importante del documento*

Il contratto di filo è onesto: `capabilities.memory.mode` vale `cgroup_v2` (contenimento reale),
`process_tree_observed` (campionamento) o `unavailable`, e `metrics.resources.memory` riporta modo,
limite e picco osservato.

**Nessuna di queste informazioni viene renderizzata.** Verificato su `dev_release2`:

```
git grep -in 'memory|capabilit' -- frontend/src/lib/features/tools/**/*.svelte  →  nessuna corrispondenza
grep -c memory frontend/src/lib/i18n/locales/en.json (chiavi tools)             →  nessuna chiave
```

`ToolDiagnosticsPanel.svelte` mostra la tabella delle policy senza riga memoria;
`components/ToolExecutionMetrics.svelte` non è stato toccato dopo il mio freeze e renderizza un
elenco esplicito di chiavi come durate — il campo annidato `resources` semplicemente non compare,
senza alcun errore di tipo che lo segnali.

Risultato: su macOS di sviluppo, o su un container Linux senza delega cgroup, un job può superare
1 GiB fra due campionamenti e **riuscire**. L'operatore vede un successo e una diagnostica che non
menziona mai la memoria. Non c'è modo, dalla UI, di distinguere «contenuto a 1 GiB dal kernel» da
«osservato ogni 50 ms e speriamo bene». Il dato per farlo è già sul filo.

### 5.2 — La somma di RSS sull'albero può fallire un job legittimo

In modalità osservata, `OwnedProcessTree.observe_memory_limit()` somma
`process.memory_info().rss` su tutti i membri vivi. Le pagine condivise fra padre e figli vengono
**contate più volte**: un job multi-processo che usa onestamente 600 MiB reali può essere riportato
a 1,1 GiB e ucciso con `memory_limit`. Fallisce in modo visibile — quindi non è il caso peggiore —
ma la causa attribuita è falsa, e un autore di plugin la inseguirà nel posto sbagliato.
Il simmetrico è peggiore: un picco fra due campioni non viene visto affatto.

Nota di costo, sullo stesso percorso: il campionamento passa da `running_members()` →
`_capture_group()` → `psutil.process_iter(...)`, cioè una **scansione dell'intera tabella dei
processi dell'host**. `_read_exact()` la invoca a ogni iterazione del loop (timeout di `select`
limitato a 50 ms) e di nuovo quando non c'è nulla da leggere: nell'ordine di 20 scansioni al secondo
per job attivo, ~900 per un job da 45 s. Il costo cresce col numero totale di processi della
macchina, ed è esattamente la piattaforma su cui l'enforcement è più debole.

Infine: un errore di campionamento (`psutil.AccessDenied`, `OSError`) viene convertito in
`service_unavailable` per quell'item — un problema di permessi sulle metriche diventa un errore di
disponibilità della piattaforma, ritentabile, invece di una metrica mancante.

### 5.3 — `claim_engine_window` è inutilizzabile con la policy dei tool spediti

`ToolExecutionContext.claim_engine_window(post_engine_reserve_ms=N)` solleva `execution_limit` a
meno che `soft_deadline - now >= engine_timeout_ms + N`.

Con la policy dichiarata dai due servizi PAC spediti (`job=5000`, `soft=4000`), il clamp del
catalogo produce `soft=4000` **e** `engine=min(4000, 30000, 4000)=4000`. Il budget del motore
uguaglia il budget soft: qualunque riserva positiva fallisce all'istante, e anche `N=0` fallisce non
appena è trascorso un millisecondo. Un autore di plugin che segue la documentazione e chiama
`claim_engine_window` riceve un `execution_limit` immediato che *sembra* un problema di scadenza e
invece è un vincolo aritmetico della sua stessa policy. Il plugin PAC lo aggira non chiamandolo:
passa `context.checkpoint` ai kernel.

**Regola per il prossimo autore:** se usi `claim_engine_window`, dichiara `engine_timeout_ms`
strettamente minore di `soft_timeout_ms` meno la tua riserva di post-elaborazione.

### 5.4 — Il frontend ignora il timeout client per operazione

`contracts.ts:343` legge `clientTimeoutMs: context.policy.client_timeout_ms`, cioè il valore di
**piattaforma** (oggi 65 000 ms). `git grep client_timeout_ms` sul frontend di `dev_release2` non
trova il valore per-operazione in nessun punto fuori dai test e dall'elenco etichette della
diagnostica.

Conseguenza: un tool che dichiara 25 s nella propria operazione, se si blocca, tiene la UI in attesa
**65 secondi**. Il campo per-operazione esiste nel contratto, viene clampato correttamente dal
backend, e non ha alcun effetto sull'esperienza. L'utente non vede un errore sbagliato — vede
un'attesa lunga il triplo di quella promessa.

### 5.5 — La documentazione utente pubblica ancora i budget vecchi

`mkdocs_src/docs/user/tools/index.en.md` (righe 94–100 su `dev_release2`) pubblica: coda 5 s,
job 5 s, soft 4 s, cleanup 2 s, richiesta 20 s, client 25 s. I default di `ToolPlatformPolicy`
spediti sono invece 5 / 45 / 44 / 5 / 59 / 65 s più 1 GiB di memoria. I due tool spediti dichiarano
ancora 5/4, quindi il comportamento *per-tool* corrisponde; ma la tabella è descritta come limiti di
piattaforma, ed è sbagliata. Non c'è alcuna menzione della memoria né del codice d'errore
`memory_limit` per gli utenti.

### 5.6 — Precedenza degli esiti: un successo può diventare `memory_limit` a posteriori

In `_run_owned_job` la precedenza è `cleanup_failed` > `memory_limit` > valore calcolato, e
`cleanup()` esegue un'ultima `observe_memory_limit()` inghiottendo l'eccezione. Una violazione
rilevata soltanto alla fine converte un successo nominale in `memory_limit` **con `value = None`**:
il calcolo era finito e il risultato viene buttato. È la scelta corretta (non si pubblica un
risultato prodotto fuori inviluppo), ma va saputa: un job può «riuscire e poi fallire».

### 5.7 Versionamento e compatibilità

Tre versioni indipendenti viaggiano con ogni item: `contract_version` e `implementation_version` del
plugin, e il `schema_fingerprint` degli schemi pubblicati. La richiesta **fissa** la versione
d'implementazione viva. Un disallineamento produce `version_mismatch`, marcato ritentabile, e viene
verificato due volte: dall'executor prima di spendere una corsia, e di nuovo dentro il figlio.
Il catalogo è passato a `catalog_version = "2"` e il manifest a `manifestVersion: 2` quando
`ToolUIDescriptor.ui_contract_version: int` è diventato `version: ToolVersion` (semver).
I codec generati sono Zod strict: un client vecchio contro un catalogo nuovo **rompe rumorosamente**
in fase di parsing, che è il comportamento voluto.

### 5.8 Cosa succede quando un plugin sbaglia

| Evento | Esito | Note |
|---|---|---|
| `raise` nel `compute` | `execution_failed` | nessun traceback, nessun input rimandato al client |
| Superamento soft budget | `execution_limit` | solo se il plugin chiama `checkpoint()` |
| Superamento hard budget | `execution_timeout` | include avvio a freddo, import, validazione, output |
| Attesa in coda scaduta | `queue_timeout` | origine coda = ammissione del batch, non rinnovata per onda |
| Output fuori contratto | `invalid_output` | rivalidato al confine di processo |
| Output troppo grande | `output_limit_exceeded` | per item |
| Crash / kill duro | errore di piattaforma | **mai** infattibilità finanziaria |
| Cleanup fallito | `cleanup_failed` | precede ogni altro esito; corsia non rilasciata finché non è vuota |
| Registrazione doppia (stessa classe) | no-op | ri-registrare lo stesso oggetto classe non è un nuovo claimant |
| Due servizi, stesso codice | **tutti** i claimant in quarantena | i fratelli sani restano disponibili |
| Registrazione dopo la scoperta | `RuntimeError` | le claim sono private finché lo snapshot non è pubblicato |
| Import del modulo plugin fallito | quarantena | gli altri plugin restano pubblicati |

### 5.9 Cosa è davvero isolato, e cosa lo sembra soltanto

**Davvero:** processo `spawn` separato con proprio gruppo di processi; ACK di pronto emesso *prima*
di eseguire codice del plugin (quindi l'avvio a freddo è dentro il budget hard, non fuori);
discendenti tracciati e uccisi; credito di capacità rilasciato **solo dopo** che l'albero è
osservato vuoto; su cgroup v2 delegato, `memory.oom.group=1` uccide l'intero gruppo.

**Solo in apparenza:** nessuna sandbox di filesystem, rete o syscall; il plugin gira con gli stessi
privilegi dell'applicazione; «1 GiB» su macOS è una somma campionata di RSS (§5.2); e il pool di
thread che regge i job è quello di default condiviso dal resto dell'applicazione (§5.10).

### 5.10 Sicurezza dell'event loop

La regola del progetto — I/O sincrona dentro `async def` va avvolta — è rispettata sui percorsi che
ho verificato: catalogo, diagnostica, `effective_catalog_entries`, `resource_capabilities`,
`batch_request_timeout_ms`, `get_snapshot`, `_run_owned_job` e `tree.cleanup` passano tutti per
`asyncio.to_thread`. Il loop bloccante `select`/`os.read` vive in un thread worker, non sul loop.

**Residuo da sapere:** ogni job tiene occupato un thread dell'executor **di default** per l'intera
durata di parete, ora fino a 45 s. Con due corsie sono due thread a lungo termine, condivisi con
ogni altro chiamante di `asyncio.to_thread` dell'applicazione. È limitato e non è un bug, ma il
dimensionamento del pool di default non è stato scelto pensando a job da 45 secondi.

---

## 1. L'arco — cosa è stato chiesto, cosa è diventato, dove ha biforcato

**Stato ereditato.** Questa sessione è la sostituzione di una precedente sessione «C» archiviata,
la cui compattazione falliva ripetutamente. Non ho importato la sua conversazione: ho ricevuto un
handoff autoportante, il suo `plan.md` come riferimento legacy, e la baseline
`4a73f5f63447e01b51993afb2e3c73e2c22a9a28`. Del progetto precedente ho conservato la struttura della
proposta (tabella sorgenti, worker, codegen); ho invece scartato due punti già superati: la
proprietà della sezione About (l'ordine corretto è E → C, non A → C) e il vecchio handoff PAC.

**La richiesta iniziale** era solo pianificazione. È diventata, con autorizzazione esplicita del
developer, l'implementazione completa della piattaforma, chiusa con il checkpoint `8e7259ecc`,
fusa in D e arrivata a `dev_release2` dentro `3913fe217`.

**Le decisioni, non solo la destinazione:**

1. **Tre endpoint, definitivamente.** Catalogo autenticato completo; compute eterogeneo in bulk;
   diagnostica di sola lettura. Rifiutati: endpoint di schema separato, di prefill, di job, di
   cancellazione. Lo schema completo e versionato viaggia dentro il catalogo.
2. **Pydantic come unica sorgente di verità degli schemi.** Nessuna dipendenza `jsonschema`
   aggiuntiva, nessun JSON Schema scritto a mano. I codec TypeScript sono **derivati dai modelli
   reali impacchettati** attraverso la pipeline `./dev.py api sync` esistente — non da un dizionario
   generico di schemi, che sarebbe stato più veloce e avrebbe perso letterali richiesti, union
   discriminate e `extra=forbid` annidato.
3. **Un processo fresco per item, non un pool caldo.** Ho scelto l'atomicità contro la latenza:
   un pool caldo riusa memoria e stato fra utenti diversi, e rende il kill duro una perdita di
   capacità invece che una pulizia.
4. **Registro transazionale con politica «perdono tutti».** Sui registri provider esistenti una
   collisione di codice è vinta dal primo. Qui **ogni claimant distinto di un codice in collisione
   viene messo in quarantena**: se due plugin rivendicano lo stesso nome, nessuno dei due è quello
   che l'utente crede. Ho riusato la meccanica del registro senza copiarne il retry sul `TypeError`
   del costruttore né la fuga di registrazione parziale.
5. **UI custom-first con allowlist compilata.** Nessun percorso di modulo dal server. Un renderer
   sconosciuto rende il tool non disponibile.
6. **Diagnostica sanificata**, senza valori di scenario, probe o reset, e non esposta attraverso la
   rotta di sistema pubblica esistente.
7. **Nessun plugin dimostrativo.** Ho spedito il registro dei renderer **vuoto**. Un plugin finto
   avrebbe fatto sembrare la piattaforma «completa» e avrebbe reso verde un pilota che non
   esercitava nulla di reale. Il primo consumatore doveva essere vero.

**La biforcazione, e cosa è cambiato dopo di me.** Il report di capacità che ho prodotto su
richiesta del coordinatore — 30 s riservati al motore, muro item 44/45 s, 5 s di cleanup, 59 s di
richiesta server, 65 s di client, 1 GiB per job e ~2 GiB di pool su due corsie, cgroup v2 dove
delegato e fallback osservato altrove — è stato **accettato e implementato da altri**, quasi alla
lettera, dentro `ToolPlatformPolicy`, `ToolOperationPolicy` e il nuovo `resources.py`. Nello stesso
intervallo l'ABI del plugin è stata ristrutturata da un tool per classe a *n* servizi per classe
(§4.2). Io ho progettato quell'inviluppo; non l'ho scritto, e §5 è il mio giudizio da lettore su
com'è stato realizzato.

---

## 2. Il contratto — come si scrive un plugin Tool

Scritto per il prossimo autore, contro l'ABI **attuale** di `dev_release2`.
Prima di iniziare, leggere il codice: è la fonte autorevole.
`backend/app/services/tools/base.py`, `backend/app/schemas/tools.py`,
`backend/app/services/tools/registry.py`, e la pagina
`mkdocs_src/docs/developer/architecture/patterns/tool_plugins.en.md`.

### 2.1 I modelli

Definisci ingresso e uscita come modelli Pydantic reali nel modulo di schema appropriato.
Tutti i modelli annidati vietano campi extra. Un modello strict o una union a discriminatore
richiesto sono supportati; un dizionario di schema libero **non è un contratto**.

Il campo `operation` è **richiesto ed esplicito, senza default**. Non annunciare operazioni che non
hai finito: ogni valore dichiarato deve avere la sua `ToolOperationPolicy`.

### 2.2 La classe plugin

```python
@register_plugin(ToolPluginRegistry)
class MyToolPlugin(ToolPlugin):
    contract_version = "1.0.0"
    implementation_version = "1.0.0"
    services = (
        ToolService(
            tool_code="my_tool",            # minuscolo, stabile, unico nell'installazione
            name=..., description=...,       # più name_i18n_key / description_i18n_key opzionali
            category=..., icon_key=...,      # icona compilata
            input_type=MyInput, output_type=MyOutput,
            ui=ToolUIDescriptor(kind="custom", component_key="my-tool", version="1.0.0"),
            documentation=ToolDocumentation(path="user/tools/my-tool.md", version="1.0.0"),
            operations=(ToolOperationPolicy(operation="analyze", ...),),
        ),
    )

    def compute(self, tool_code, parameters, context):   # sincrono
        ...
        return MyOutput(...)
```

Da 1 a 16 servizi per classe. **Ricorda l'accoppiamento di §3.4(e):** le versioni stanno sulla
classe, quindi servizi fratelli condividono il ciclo di vita del contratto. Se due tool evolvono
davvero in modo indipendente, dagli due classi.

`compute` è **sincrona**, riceve il `tool_code` e smista su di esso. Restituisce un modello
completo: l'uscita viene serializzata e **rivalidata** al confine di processo, quindi
`model_construct` non aggira nulla. Inoltra `context.checkpoint` ai kernel numerici puri, invece di
importare la runtime dei Tool dentro di essi.

L'inizializzazione non prende parametri utente ed è tentata **una volta sola**. Non calcolare, non
scaricare dati e non eseguire self-test all'import o alla registrazione.

### 2.3 Cosa il contesto ti dà, e cosa non ti dà

Ti dà: `checkpoint()` (solleva se hai superato il soft budget), `remaining_soft_ms`,
`claim_engine_window(post_engine_reserve_ms)` — con l'avvertenza di §5.3.

Non ti dà: sessione DB, principal, client provider, richiesta, cookie, autorità di portafoglio.
Raccogli **prima** ogni dato necessario attraverso le API di dominio autorizzate e passalo nei
parametri.

### 2.4 Le policy

`ToolOperationPolicy` porta: `operation`, `max_result_bytes`, `queue_timeout_ms`, `job_timeout_ms`,
`soft_timeout_ms`, e i campi aggiunti dopo il mio freeze — `engine_timeout_ms` (default 4 000),
`cleanup_timeout_ms`, `request_timeout_ms`, `client_timeout_ms`, `memory_limit_bytes`.

Sono **massimi richiesti**, non concessioni: `catalog.effective_operation()` li limita tutti verso
il basso contro `ToolPlatformPolicy` e rifiuta un'operazione il cui limite server complessivo
(ingresso + coda + hard + cleanup + risposta) eccede il proprio budget di richiesta.
I default di operazione restano 5 000 / 4 000 ms: **un tool esistente che non tocchi nulla non
cambia comportamento**, anche se i default di piattaforma sono saliti a 45 / 44 s.

### 2.5 Codegen e UI

Dopo una modifica autorizzata ad API o schema, usa la pipeline esistente:
`./dev.py api sync` (e `--tools-only` quando pertinente). Esporta le radici dei modelli reali
impacchettati e la mappa codice/versione → codec. Non scrivere a mano campi TypeScript di dominio né
un endpoint finto per forzare la generazione.

Lato UI, registra **solo import compilati**, in
`frontend/src/lib/features/tools/registry.ts`. La compatibilità verifica in modo esatto codice,
versione di contratto, impronta di schema e chiave/versione della UI; la richiesta fissa
separatamente l'implementazione viva. Usa il componente `DocsLink` esistente perché il link segua la
lingua del frontend. Tutti i calcoli finanziari restano nel backend. Proteggi l'applicazione del
risultato con generazione dell'account, identità del componente, sequenza di richiesta e revisione
della bozza.

Attenzione a Unicode: le lunghezze JSON Schema/Pydantic contano **code point**, non unità UTF-16.
Rifiuta i surrogati spaiati prima di codificare.

### 2.6 Prove di completamento

Test nuovi o riparati passano da `test-author`; le pagine MkDocs da `docs-writer`.
Esercita il plugin **vero** attraverso catalogo, compute, worker, codec e la sua UI approvata.
Verifica correlazione, ordine e cardinalità esatte e l'isolamento dei fallimenti — non conteggi
globali di DB. Un pilota non è completo se dimostrato con un registro vuoto o un plugin usa e getta.

---

## 2.7 Cablare una **nuova operazione** su un tool esistente

Questa sezione esiste perché il caso è già reale e non risolto: il pianificatore PAC v2
(`backend/app/services/pac_allocator/planner.py`, funzione `plan_pac_allocation`, schemi con
`operation: Literal["plan"]`) **è scritto e non è raggiungibile**. Verificato da me su
`dev_release2`: `plan_pac_allocation` non ha alcun chiamante di produzione — solo
`test_scripts/test_services/test_pac_planner_planner.py` — e nulla in `tool_plugins/` o in `api/`
lo nomina. Chi lo collegherà non potrà chiedermelo. Quindi qui c'è la procedura, i numeri da cui
derivare e le trappole, scritte per esteso.

### 2.7.1 Che cosa va toccato, in ordine

1. **`ToolOperationPolicy`** aggiuntiva nella tupla `operations` del `ToolService` esistente.
2. **Modelli d'ingresso e uscita** che includano il nuovo letterale `operation`. Se ingresso o
   uscita diventano una union, deve essere **discriminata su `operation`** con discriminatore
   richiesto, e ogni variante deve vietare campi extra.
3. **Dispatch** dentro `compute(tool_code, parameters, context)`: smista su `tool_code` **e** su
   `parameters.operation`. Non dedurre l'operazione dalla forma dei parametri.
4. **`implementation_version`** della classe: sale sempre. **`contract_version`**: sale se cambiano
   gli schemi pubblicati — e ricorda §3.4(e), sale **anche per i servizi fratelli** della stessa
   classe.
5. **Codegen**: `./dev.py api sync` (`--tools-only` quando pertinente), per rigenerare codec e mappa
   versione → codec dalle radici reali dei modelli.
6. **Renderer**: il componente compilato deve gestire il nuovo stato di risultato; se cambia la sua
   forma, alza `ToolUIDescriptor.version` (semver, non intero).
7. **Documentazione** (`ToolDocumentation.path` + pagina MkDocs) e chiavi i18n.
8. **Test** attraverso `test-author`, sul percorso reale catalogo → compute → worker → codec → UI.

### 2.7.2 Da cosa derivare i numeri, invece di indovinarli

**Un solo numero è una decisione di prodotto: quanto tempo serve al motore.** Tutti gli altri
discendono da identità aritmetiche imposte dai validatori. Non sceglierli a occhio: risolvili.

Le costanti di piattaforma spedite (`ToolPlatformPolicy`, `backend/app/schemas/tools.py`):

```
workers 2 · queue 5 000 · engine 30 000 · job 45 000 · soft 44 000
output_reserve 1 000 · cleanup 5 000 · ingress 2 000 · response 2 000
request 59 000 · client 65 000 · memory 1 073 741 824
```

Il clamp (`catalog.effective_operation`) è **sempre verso il basso** — la tua policy è un massimo
*richiesto*, mai una concessione:

```
hard    = min(policy.job,     platform.job)
soft    = min(policy.soft,    platform.soft,   hard - platform.output_reserve)
engine  = min(policy.engine,  platform.engine, soft)
cleanup = min(policy.cleanup, platform.cleanup)
queue   = min(policy.queue,   platform.queue)
request = min(policy.request, platform.request)
client  = min(policy.client,  platform.client)

server_bound = ingress + queue + hard + cleanup + response
if soft <= 0 or server_bound > request:  →  ToolDefinitionError("invalid_operation_policy")
```

Da cui le regole di derivazione, in quest'ordine:

1. Scegli **`engine`** (decisione di prodotto: il budget del solver).
2. **`soft` ≥ `engine`** + la tua riserva di post-elaborazione (replay Decimal, serializzazione).
3. **`hard` = `soft` + `output_reserve`** almeno, cioè `soft + 1 000`.
4. **`request` ≥ ingress + queue + hard + cleanup + response** = `9 000 + hard` con i default.
5. **`client` > `request`**, strettamente.

Applicate a un'operazione `plan` che voglia i 30 s di motore accettati:

| Campo | Valore | Perché |
|---|---|---|
| `engine_timeout_ms` | 30 000 | decisione di prodotto sul solver |
| `soft_timeout_ms` | 44 000 | 30 000 di motore + 14 000 di riserva post-motore |
| `job_timeout_ms` | 45 000 | `soft` + `output_reserve` (1 000) |
| `cleanup_timeout_ms` | 5 000 | tetto di piattaforma |
| `queue_timeout_ms` | 5 000 | tetto di piattaforma |
| `request_timeout_ms` | 59 000 | `2 000 + 5 000 + 45 000 + 5 000 + 2 000` |
| `client_timeout_ms` | 65 000 | > 59 000 |
| `memory_limit_bytes` | 1 073 741 824 | tetto di piattaforma |

> **`server_bound` risulta esattamente 59 000 contro un `request` di 59 000.** Il confronto è
> `>`, quindi passa — **con margine zero**. Non è una coincidenza: il 59 s accettato è stato
> derivato proprio per contenere questa somma. Conseguenza pratica: **non puoi alzare `queue`,
> `cleanup` o `job` di un solo millisecondo** per un'operazione a budget pieno senza far fallire la
> validazione. Se ti serve più tempo di cleanup, devi toglierlo al job.

### 2.7.3 Le cinque trappole

**(1) Una policy d'operazione invalida spegne l'INTERO tool, non l'operazione.**
La più importante. `effective_descriptor` calcola `effective_operation` su **tutte** le operazioni
del descrittore in una list comprehension: se una sola solleva `ToolDefinitionError`, l'eccezione
propaga, il descrittore **non** entra nel catalogo, e il tool finisce in `unavailable` con
`filename="operation_policy"`. Aggiungere un `plan` mal dimensionato a un tool che spedisce
`analyze` **fa sparire anche `analyze`**.
Nota il contrasto con la quarantena del registro (§5.8), che invece isola i servizi fratelli:
**la quarantena isola i servizi, la validazione delle policy no — non isola le operazioni.**
Regola: dopo aver aggiunto un'operazione, apri il catalogo e verifica che il tool ci sia **ancora**.

**(2) La larghezza del batch è limitata dal numero di worker, per le operazioni lunghe.**
`admitted_at` è calcolato **una volta per batch** (`executor.py:474`) e passato identico a ogni
item; la scadenza di coda è `min(admitted_at + queue_timeout, request_deadline - (cleanup +
response_reserve))` (`executor.py:401`). **L'origine della coda non viene rinnovata per ondata.**
Con `workers = 2` e un job da 45 s, gli item dal terzo in poi non possono ottenere una corsia prima
di `admitted_at + 5 s` e falliscono con `queue_timeout`. Quindi: **al più `workers` item di
un'operazione lunga per batch.** Anche mescolare è rischioso — un `plan` accodato dietro un
`analyze` da 5 s arriva alla corsia esattamente sul confine dei 5 s di coda. Non è un difetto da
correggere di nascosto alzando `queue`: la trappola (1) lo impedisce comunque a budget pieno.

**(3) `claim_engine_window` qui funziona, al contrario che su `analyze`.**
Con `engine = 30 000` e `soft = 44 000`, `claim_engine_window(post_engine_reserve_ms=N)` riesce
finché `44 000 - trascorso ≥ 30 000 + N`, cioè con `N` fino a ~14 s. È esattamente il caso per cui
la primitiva è stata progettata. Su `analyze` (engine 4 000 = soft 4 000) è invece inutilizzabile:
vedi §5.3. Un autore che copia la policy di `analyze` e poi chiama `claim_engine_window` riceve un
`execution_limit` immediato.

**(4) Il solver nativo non risponde a `checkpoint()`.**
Se il motore è una libreria nativa che non torna al Python per decine di secondi,
`context.checkpoint()` non verrà mai chiamato e il budget soft non avrà effetto: resterà solo il
kill duro a 45 s, che è un **errore di piattaforma** (§5.8), non una terminazione ordinata e **non**
un'infattibilità finanziaria. Se il motore espone un proprio limite di tempo interno, impostalo a
`engine_timeout_ms` e non affidarti al soft budget.

**(5) L'attesa del client resterà 65 s comunque.**
Finché §5.4 non è risolto, il frontend usa il `client_timeout_ms` di **piattaforma** per ogni tool.
Dimensionare bene il `client_timeout_ms` dell'operazione è corretto e contrattualmente giusto, ma
oggi non cambia l'esperienza utente.

### 2.7.4 Prima di dichiararla fatta

Verifica che il tool compaia **ancora** nel catalogo (trappola 1); che un batch di ampiezza `workers`
riesca e uno più largo fallisca in modo pulito con `queue_timeout` (trappola 2); che un superamento
del budget produca `execution_timeout` o `execution_limit` e **mai** un risultato a zero; e che la
diagnostica riporti le durate di fase non nulle. Non dichiarare completa un'operazione dimostrata
con un plugin usa e getta.

---

## 4. I consumatori, visti dal mio lato

Descritti senza coordinamento con D, come richiesto.

### 4.1 Cosa consumano davvero

In `dev_release2` c'è **un solo file plugin**: `backend/app/services/tool_plugins/pac_allocator.py`,
111 righe. Una classe, **due servizi** — `pac_allocator` e `portfolio_rebalancer` — che condividono
una `_ANALYZE_POLICY` (5 000 / 4 000 ms) e smistano per codice dentro `compute`, chiamando
`analyze_pac_budget` e `analyze_rebalancing` con `checkpoint=context.checkpoint`.

Entrambi usano oggi **solo `analyze`**. Il bilancio del motore da 30 s che ho progettato non è
esercitato da nulla di spedito: nessuna operazione `plan` con solver esiste ancora nel target.

Del mio lato consumano: registrazione e scoperta, clamp delle policy, catalogo, esecuzione isolata,
codec generati, registro dei renderer compilati, host, hub, `DocsLink`, diagnostica.

### 4.2 Cosa hanno richiesto che non avevo previsto

Quattro cose, e la prima è sostanziale.

1. **Due tool da un solo pacchetto.** La mia ABI era *un tool per classe*: `ToolPlugin[InputT,
   OutputT]` con `tool_code`, `input_type`, `output_type` a livello di classe. PAC e Rebalancer
   condividono modelli e kernel, e ottenerne due avrebbe richiesto due classi con metadati
   duplicati. La risposta è stata ristrutturare l'ABI attorno a `ToolService`: `compute` ha
   guadagnato il parametro `tool_code`, il registro espande ogni servizio in una definizione
   indipendente, `_get_plugin_code_attr()` restituisce `"services"`, e le collisioni si calcolano su
   **tutte** le claim di servizio. **La mia tipizzazione generica è sparita**: `ToolPlugin` non è più
   parametrizzata, e la corrispondenza ingresso/uscita si controlla per servizio invece che nel tipo.
   È il prezzo pagato, e va detto perché un autore di plugin che legga vecchi documenti cercherà
   ancora `ToolPlugin[Input, Output]`.
2. **Budget per operazione di tempo e memoria.** Discendono dal mio report di capacità; li avevo
   progettati ma non implementati.
3. **Versione UI semantica.** `ui_contract_version: int` → `version: ToolVersion`, propagato a
   `schema_export.py` (`uiVersion`), al manifest (`manifestVersion: 2`), a `registry.ts` e a
   `contracts.ts`; `catalog_version` da `"1"` a `"2"`.
4. **Disponibilità sincrona del catalogo.** La navigazione hub/host aveva bisogno di sapere *subito*
   se un tool esiste. Sono stati aggiunti una cache allineata alla generazione con coalescenza delle
   richieste in volo, `peekToolCatalog()`, `invalidateToolCatalogCache()` e un'opzione `reload`,
   più memoizzazione dei componenti e `peek()` nel registro dei renderer. Avevo progettato solo un
   recupero asincrono.

### 4.3 Cosa **non** hanno richiesto

Non hanno chiesto accesso a DB o provider dal worker, né deduplicazione, né un endpoint di
cancellazione. Il rifiuto di §3.3 ha retto contro il primo consumatore reale — che è l'unica prova
che conta.

---

## 6. Cosa non è fatto

1. **Nessuna operazione `plan` con solver.** Entrambi i servizi spediti sono `analyze` a 5 000 /
   4 000 ms. L'inviluppo 30 / 44 / 45 s esiste nel contratto e **non è esercitato da nulla**.
   Il pianificatore v2 (`plan_pac_allocation`) è **scritto e non raggiungibile**: zero chiamanti di
   produzione, nessuna `ToolService`/`ToolOperationPolicy` che lo esponga. **La procedura completa
   per collegarlo, con i numeri derivati e le cinque trappole, è in §2.7** — scritta lì perché
   questa sessione viene archiviata e chi farà quel lavoro non potrà chiedere.
2. **Memoria invisibile in UI** (§5.1). Manca il rendering di `capabilities.memory`,
   `pool.resources` e `metrics.resources`, e mancano le chiavi i18n corrispondenti.
3. **Timeout client per operazione inerte nel frontend** (§5.4).
4. **Documentazione utente disallineata** (§5.5): tabella budget vecchia, nessuna menzione di
   memoria o di `memory_limit`. Da verificare anche se la pagina developer copre il nuovo inviluppo.
5. **Il percorso cgroup non è mai stato provato su un host delegato reale.** I test usano filesystem
   finti (§8). Su macOS di sviluppo la modalità hard non si attiva mai.
6. **Nessun benchmark eseguito.** La matrice falsificabile che ho proposto nel report di capacità
   richiede un compilatore rappresentativo, che non esiste ancora.
7. **Nessun tetto aggregato di risposta** per batch (§3.4f).
8. **Accoppiamento di versione fra servizi fratelli** (§3.4e) non esercitato: oggi i due servizi
   evolvono insieme, quindi il problema non si è ancora manifestato.
9. **Non POSIX** (Windows) → `service_unavailable`, per progetto.
10. **Costo di campionamento in modalità osservata** (§5.2) non ottimizzato.

---

## 7. Scenari di prova per un umano

**Nessun server è stato avviato da questa sessione e nessuna porta è stata occupata.** La corsia di
revisione 6152 appartiene alla sessione PAC e serve l'intero target; 6157 è di un'altra sessione
viva. Questi scenari vanno eseguiti su quella corsia, non su una nuova.

Ordine consigliato. Ogni scenario ha un esito atteso: uno scenario senza esito atteso è un clic.

| # | Scenario | Esito corretto | Fiducia |
|---|---|---|---|
| 1 | Aprire l'hub Tool | Esattamente due tool: allocatore PAC e ribilanciatore. Ogni scheda ha un link alla documentazione che segue la lingua della UI | alta |
| 2 | Eseguire un `analyze` PAC valido | Successo, risultato renderizzato dal componente compilato, metriche con durate di fase non nulle (coda/avvio/calcolo/output) | alta — *i numeri finanziari li giudica D, non io* |
| 3 | Aprire About → diagnostica Tool | 2 plugin caricati, 0 fallimenti, contatori del pool, tabella delle policy. **Atteso che la tabella mostri i valori di piattaforma 45 000 / 59 000 / 65 000, non 5 000, e che non ci sia alcuna riga memoria** (§5.1, §6.2) | media — non ho verificato le etichette esatte a schermo |
| 4 | Input non valido (numero fuori range, campo extra) | `invalid_parameters` con le issue, nessun traceback, nessun eco dei parametri | alta |
| 5 | Batch misto: un item valido e uno non valido | L'item valido riesce, l'altro fallisce, **correlazione e ordine preservati**, cardinalità esatta | alta |
| 6 | Disallineamento di versione: tenere una scheda aperta, invalidare il catalogo, rieseguire | `version_mismatch` ritentabile, **nessun calcolo avviato** | media — dipende dal modo in cui si forza lo stato stantio |
| 7 | Renderer mancante: de-registrare temporaneamente il componente compilato | Il tool risulta **non disponibile**; nessun caricamento arbitrario, nessun form finanziario generico | media — richiede un'edit temporanea, non una manovra da UI |
| 8 | Cancellazione: avviare un run e abbandonare la pagina | Il client smette di attendere; il server completa o reap-a; i contatori pending della diagnostica tornano a 0. **Abortire non è un ACK di cancellazione** | alta |
| 9 | Timeout: far superare il budget a un tool | `execution_timeout` (o `execution_limit` se coopera), **mai** un risultato a zero o un'infattibilità | media — con i tool spediti serve un input artificialmente pesante |
| 10 | **Violazione di memoria** | `memory_limit` con byte riportati | ⚠️ **bassa — non verificabile onestamente su macOS.** Serve un host Linux con cgroup v2 delegato e scrivibile; altrove il percorso è campionato e §5.2 si applica |
| 11 | **Dipendenza mancante** | Plugin in quarantena, altri tool ancora disponibili, diagnostica che riporta il fallimento | ⚠️ **bassa — non riproducibile con i tool spediti**, che sono Python puro senza dipendenze opzionali. Servirebbe rompere deliberatamente un import |
| 12 | Collisione di codice | **Entrambi** i claimant in quarantena, tool sani intatti | bassa — richiede un plugin usa e getta, che ho deliberatamente evitato di spedire |

Gli scenari 10, 11 e 12 sono quelli su cui ho **meno fiducia** e li segnalo come tali: sono i
comportamenti che il codice afferma e che l'ambiente di sviluppo corrente non permette di
falsificare.

---

## 8. Copertura automatica

**Non ho eseguito alcuna suite in questa sessione.** Quanto segue è ciò che i test *asseriscono*,
letto nel sorgente di `dev_release2`. Non è un rapporto di esecuzione e non contiene un totale verde.

### 8.1 Cosa esiste

| Suite | Cosa asserisce davvero |
|---|---|
| `backend/test_scripts/test_services/test_tools_executor.py` | Ammissione, corsie, aritmetica delle scadenze, cancellazione, precedenza degli esiti, proprietà dell'albero dei processi. Include test nominati per la memoria: hard annunciato **solo dopo prova di delega scrivibile**; fallback osservato che **non rivendica mai hard senza prova**; nome del cgroup digest-safe e limite **riletto**; delta OOM → `memory_limit` tipizzato con byte; rimozione **una sola volta** della directory vuota; cleanup che **attende** il sottoalbero vuoto; gruppo memoria preparato e **agganciato prima dell'ACK** del worker; precedenza errori e metriche annidate |
| `backend/test_scripts/test_schemas/test_tools_schemas.py` | Coerenza del contratto: modalità memoria, intervalli di campionamento, validatori delle policy, riserva del pool |
| `backend/test_scripts/test_api/test_tools_api.py` | Endpoint, forma della diagnostica, e `test_disconnect_cancels_compute_before_any_engine_start` |
| `backend/test_scripts/test_services/test_tools_registry.py` | Scoperta, quarantena, collisioni |
| `backend/test_scripts/test_api/test_pac_tool_api.py` | Fra gli altri, `test_catalog_publishes_both_services_with_shared_backend_versions` — cioè l'accoppiamento di §3.4(e) è **asserito come voluto**, non solo subito |
| Vitest frontend (feature `tools`) | Trasporto, cache del catalogo, codec, registro dei renderer |

La copertura della memoria è sostanziale e ben mirata: distingue in modo esplicito «annunciare hard»
da «provare hard», che è la distinzione giusta.

### 8.2 Le lacune, nominate

1. **Nessun test gira su un cgroup v2 reale.** Tutta la copertura hard usa filesystem finti su
   `tmp_path`. Provano la logica di scoperta e di scrittura, **non** che il kernel contenga davvero
   un processo a 1 GiB.
2. **Nessun test esercita il costo del campionamento in modalità osservata** (§5.2): la somma di RSS
   è testata con un `memory_info` finto, quindi né il doppio conteggio delle pagine condivise né il
   costo di `process_iter` sono sotto test.
3. **Nessun test di un job realmente lungo** (45 s) o di una finestra motore usata con successo:
   `claim_engine_window` non è esercitato da alcun tool spedito (§5.3).
4. **Nessun test frontend sulla selezione del timeout client per operazione** — perché la funzione
   non esiste (§5.4). L'assenza di test qui non è una lacuna di copertura: è una lacuna di prodotto.
5. **Nessun test che asserisca che la UI mostri la capacità di memoria** — stessa ragione (§5.1).
6. **Nessun benchmark**, quindi nessuna prova falsificabile che l'inviluppo scelto regga un solver
   reale (§6.6).
7. **Nessun test di dipendenza mancante** su un plugin reale (scenario 11).

### 8.3 Cosa non proverebbe un totale verde

Che i due tool spediti passino non dimostra che la piattaforma contenga la memoria, perché nessuno
dei due la avvicina; non dimostra che l'inviluppo da 30 s funzioni, perché nessuno dei due lo usa;
e non dimostra che la modalità hard si attivi, perché sulla macchina di sviluppo non si attiva mai.

---

## Riferimenti di file

| Area | Percorso |
|---|---|
| Contratto plugin | `backend/app/services/tools/base.py` |
| Contratto di filo | `backend/app/schemas/tools.py` |
| Esecuzione | `backend/app/services/tools/executor.py`, `worker.py` |
| Albero processi e cleanup | `backend/app/services/tools/process_tree.py` |
| Memoria | `backend/app/services/tools/resources.py` *(nuovo dopo il freeze C)* |
| Scoperta | `backend/app/services/tools/registry.py` |
| Catalogo e clamp | `backend/app/services/tools/catalog.py` |
| Export schema | `backend/app/services/tools/schema_export.py` |
| API | `backend/app/api/v1/tools.py` |
| Unico consumatore | `backend/app/services/tool_plugins/pac_allocator.py` |
| Trasporto FE | `frontend/src/lib/features/tools/client.ts`, `contracts.ts` |
| Registro renderer | `frontend/src/lib/features/tools/registry.ts` |
| Diagnostica FE | `frontend/src/lib/features/tools/ToolDiagnosticsPanel.svelte` |
| Doc sviluppatore | `mkdocs_src/docs/developer/architecture/patterns/tool_plugins.en.md` |
| Doc utente | `mkdocs_src/docs/user/tools/index.en.md` *(budget disallineati, §5.5)* |
| Skill | `.github/skills/tool-plugin/SKILL.md` |

Documentazione per sviluppatori e skill sono **già allineate** all'ABI multi-servizio: descrivono
`ToolService`, `compute(tool_code, ...)`, `uiVersion` e i due servizi impacchettati. Non è un
disallineamento. Il disallineamento è solo sulla pagina utente (§5.5).
