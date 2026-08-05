# 13 — AI Export

> Sottosistema escluso dai report 01–12 perché in lavorazione da parte di un altro agente.
> Audit eseguito a lavoro concluso (commit `09cbb7e2 refactor(ai-export): publish V1 contract`),
> con lo **stesso metodo e gli stessi strumenti** applicati agli altri undici sottosistemi.

---

## Sintesi

**Questo è il codice migliore del progetto**, e il divario con il resto non è marginale:
è di un ordine di grandezza su quasi ogni metrica. 18 355 righe di backend e 7 393 di
frontend producono **7 simboli morti**, **0 violazioni della Async I/O Rule**, **0 candidati
N+1**, **0 file frontend orfani**, con una copertura del **93,47 %** e un rapporto
test:codice di **2,42:1** contro lo 0,79:1 del resto del backend.

Non è un giudizio di cortesia: è il risultato di applicare a questo perimetro gli stessi
strumenti che altrove hanno prodotto 15 simboli non referenziati, 38 candidati N+1 e una
funzione di complessità 112.

Ho aperto l'audit con due ipotesi di difetto — un deadlock su ciclo di dipendenze e un
ordinamento delle sezioni non verificato — e **le ho smentite entrambe**: erano già
previste e risolte, con l'invariante scritto nel docstring. Le riporto lo stesso (§ M6),
perché il fatto che un revisore indipendente le abbia cercate e non le abbia trovate è
un'informazione utile.

Restano **tre reperti reali**:

1. 🟡 **Il *DRY orfano*, sesta occorrenza** — stavolta in codice appena scritto, il che
   cambia la diagnosi del pattern per l'intero progetto (§ M4).
2. 🟢 **Tre funzioni realmente morte** su 18 355 righe (§ M3, § M4.2).
3. 🔵 **17 invarianti strutturali affidati a `assert`** — osservazione di stile e
   diagnosticabilità, **non** un rischio di produzione: la CI intercetta lo stesso difetto
   a monte (§ M2, con la correzione di severità).

> **Nota di revisione.** Due valutazioni della prima stesura sono state corrette dopo
> verifica sul codice: la severità di § M2 (da 🟡 a 🔵) e la diagnosi di § M4.2 (non era un
> *DRY orfano*, era una funzione semplicemente inutilizzata). Entrambe le correzioni sono
> documentate in linea nelle rispettive sezioni.

---

## M1 — Il contrasto, in numeri

Stessa configurazione di strumenti, stesso perimetro di regole, stesso scanner N+1 e
async-I/O usati nei report 01–11.

| Metrica | AI Export | Resto del backend | Rapporto |
|---|---:|---:|---|
| Righe di produzione | 18 355 | 74 517 | — |
| Simboli morti (funzione/metodo/classe/proprietà) | **7** | 57 | — |
| Densità simboli morti (per 1 000 righe) | **0,38** | 0,76 | **2× meglio** |
| Candidati N+1 | **0** | 38 | — |
| Violazioni Async I/O Rule | **0** | 1 | — |
| `C901` complessità > 10 | 17 | 121 | — |
| Complessità massima | **22** | **112** | **5× meglio** |
| `TRY400` (log errato in `except`) | **0** | 53 | — |
| `TRY300` / `TRY301` | **0** / **0** | 38 / 37 | — |
| `PIE790` (`pass` superfluo) | **0** | 54 | — |
| `RUF010` (conversione esplicita in f-string) | **0** | 23 | — |
| `PERF401` (comprehension manuale) | 1 | 17 | — |
| `S110` (`except: pass` muto) | **0** | 11 | — |
| Copertura test | **93,47 %** | 89,73 % | — |
| Rapporto test:codice | **2,42:1** | 0,79:1 | **3× meglio** |
| File frontend orfani | **0** | 20 | — |
| Export frontend inutilizzati | 6 | 79 | — |

Gli zeri nella colonna centrale non sono un caso: `TRY400`, `TRY300`, `TRY301`, `PIE790`,
`RUF010`, `S110` sono tutti indicatori di **gestione degli errori scritta per abitudine**.
Il resto del backend ne ha 216 in totale, l'AI Export zero. Qui gli errori non vengono
gestiti a orecchio: ogni fallimento ha un tipo, un `reason_code` e uno status HTTP
dichiarato nella firma dell'endpoint (§ M8).

---

## M2 — 🔵 17 invarianti strutturali affidati a `assert`

**Severità rivista al ribasso dopo verifica** — vedi il riquadro di correzione più sotto.
La prima stesura classificava questo reperto 🟡 sostenendo che potesse produrre un guasto
in produzione; l'analisi successiva ha dimostrato che **la suite di test intercetta lo
stesso difetto a monte**, rendendolo un'osservazione di stile e diagnosticabilità.

### Il fatto tecnico

`assert` **non è un `if`**. Quando Python gira con `PYTHONOPTIMIZE=1` (o con `-O`), le
righe `assert` non vengono disabilitate: vengono **fisicamente rimosse** in fase di
compilazione. Prova eseguita, stesso file e stessi dati sbagliati:

```python
COMPONENTI = ["a", "b", "c"]          # ne mancano 2 per errore
ATTESI = 5

assert len(COMPONENTI) == ATTESI, f"attesi {ATTESI}, trovati {len(COMPONENTI)}"
print("APP AVVIATA con", len(COMPONENTI), "componenti")
```

```console
$ python demo.py
AssertionError: attesi 5, trovati 3          → exit 1

$ PYTHONOPTIMIZE=1 python demo.py
APP AVVIATA con 3 componenti                  → exit 0
```

Nel primo caso l'app si rifiuta di partire e dice esattamente cosa non torna. Nel secondo
**parte con i dati sbagliati**, senza una riga di log.

### Dove questo tocca l'AI Export

Il sottosistema contiene **51 `assert`**, di cui **17 esprimono invarianti strutturali** —
16 a livello di modulo, eseguiti all'import, più uno dentro `build_dataset_registry()`,
eseguito alla costruzione del registry. Non sono asserzioni di comodo: sono il **contratto
strutturale del catalogo**.

| File | Riga | Quando | Invariante |
|---|---:|---|---|
| `components/catalog.py` | 221–223 | import | `ALL_FOUNDATION_COMPONENTS`, `ALL_REAL_COMPONENTS`, `ALL_COMPONENTS` valgono esattamente 67 |
| `components/asset_fx_registry.py` | 140–143 | import | conteggi Asset/FX corretti **e non sovrapposti** |
| `components/portfolio_broker_registry.py` | 146–148 | import | conteggi Portfolio/Broker corretti |
| `datasets/catalog.py` | 867 | import | 8 dataset pubblici |
| `datasets/catalog.py` | 973 | build registry | 40 dataset totali |
| `analyses/catalog.py` | 241 | import | 11 analisi pubbliche |
| `temporal/policy.py` | 78–79 | import | la policy copre **ogni** membro di `BucketDetailLevel` e `SignalTemporalClass` |
| `dependencies.py` | 112–113 | import | la mappa `DetailLevel → BucketDetailLevel` è **totale e suriettiva** |

Gli altri 34 sono `assert … is not None`, restringimenti di tipo per il type checker: lì
l'idioma è corretto e può restare.

### Lo scenario, e perché la CI lo intercetta

Qualcuno aggiunge un componente e dimentica di aggiornare il conteggio da 67 a 68.

| | `assert` attivi | Con `PYTHONOPTIMIZE` |
|---|---|---|
| In CI (`pytest`) | L'errore emerge | **L'errore emerge comunque** — pytest non usa mai `PYTHONOPTIMIZE`, e i test verificano i conteggi per conto proprio |
| In locale, all'import | Errore immediato e chiaro | Nessun feedback fino al `./dev.py test` |
| In produzione | Rifiuto all'avvio | Nessun controllo — ma il difetto non è arrivato fin qui, la CI lo ha bloccato |

La riga che conta è la prima: **il cancello vero è la suite di test**, non l'assert nel
modulo di produzione.

Lo stesso vale per `temporal/policy.py:78`: senza quell'assert, un `BucketDetailLevel`
non coperto dalla policy diventerebbe un `KeyError` a runtime invece di un errore
all'avvio — ma anche questa totalità è statica e viene esercitata da qualunque test che
importi il modulo (59 file di test importano `ai_export`).

### ⚠️ Correzione di severità — questo reperto era sovrastimato

La prima stesura di questa sezione sosteneggiava che, con `PYTHONOPTIMIZE` attivo, un
catalogo incoerente potesse **raggiungere la produzione**. **Non è vero, ed è un errore
d'analisi.** La verifica successiva ha mostrato che gli stessi conteggi sono controllati
in modo **indipendente dalla suite di test**:

| Test | Riga | Verifica |
|---|---:|---|
| `test_ai_export_dataset_analysis_catalogs.py` | 181–183 | `len(ALL_FOUNDATION_COMPONENTS/ALL_REAL/ALL) == 67` |
| `test_ai_export_dataset_analysis_catalogs.py` | 146–147 | `EXPECTED_DATASET_COUNT == 40`, `EXPECTED_PUBLIC_DATASET_COUNT == 8` |
| `test_ai_export_dataset_analysis_catalogs.py` | 206 | `EXPECTED_ANALYSIS_COUNT == 11` |
| `test_ai_export_composer.py` | 344 | `len(registry) == 67` |
| `test_ai_export_components_portfolio_broker_integration.py` | 621, 681, 686 | 67 / 40 / 11 |

E **pytest non gira mai con `PYTHONOPTIMIZE`**: la CI vede sempre gli assert attivi. Quindi
un conteggio sbagliato **non può essere rilasciato**, indipendentemente da come è
configurata la produzione.

**Il modello mentale sbagliato che la prima stesura induceva.** Un `assert` è un rilevatore
di fumo: rimuoverlo **non provoca l'incendio**, toglie soltanto l'allarme per un incendio
che ha acceso qualcos'altro. Togliere gli assert non rompe un programma funzionante — rende
soltanto invisibile un guasto già presente. E qui quel guasto è già intercettato altrove.

**Cosa resta vero.** Gli assert **non sono codice di test**: vivono in 7 moduli di
produzione sotto `backend/app/services/ai_export/`, copiati nell'immagine da
`COPY backend/ ./backend/` nel `Dockerfile`, ed eseguiti all'import in produzione. Ma sono
**difesa in profondità ridondante rispetto alla CI**, non l'unica linea.

**Rischio residuo reale, piccolo:**

- chi modifica il catalogo in locale con `PYTHONOPTIMIZE` impostato non riceve il
  feedback all'import — ma la CI lo blocca comunque prima del rilascio;
- i 34 `assert … is not None` stanno su percorsi a runtime: rimossi, un `None` prosegue e
  fallisce più in basso come `AttributeError: 'NoneType' object has no attribute …`, senza
  più dire *quale* invariante è saltato. È un problema di **diagnosticabilità**, non di
  correttezza: a quel punto il programma era già in errore.

**Severità corretta: 🔵 informativo**, non 🟡. Resta l'osservazione di stile — un invariante
di contratto non è un'asserzione di debug, ed è la stessa distinzione che il sottosistema
applica già ovunque altrove (`DatasetSpecError`, `ComponentSpecError`,
`ComponentDependencyCycleError` sono eccezioni tipizzate, non `assert`).

### Contesto di produzione, verificato

Il `Dockerfile` **non** imposta `PYTHONOPTIMIZE`, e il `CMD` è
`uvicorn backend.app.main:app` senza `-O`.

Se `PYTHONOPTIMIZE` venisse impostato da un self-hoster, l'effetto sarebbe: i 17 controlli
strutturali e i 34 restringimenti di tipo smettono di essere eseguiti. Dato che la CI ha già
validato il catalogo, l'impatto pratico si riduce alla **perdita di diagnosticabilità** dei
secondi.

### Rimedio

**A — Guardia esplicita (2 righe).** In `main.py`, all'avvio:

```python
if not __debug__:
    raise RuntimeError(
        "LibreFolio must not run with PYTHONOPTIMIZE/-O: the AI Export catalog "
        "invariants are enforced by module-level assert statements."
    )
```

Costo trascurabile. **Igiene, non correzione di un rischio attivo**: rende esplicito che il
progetto non supporta quella modalità, invece di degradare in silenzio.

**B — Convertire i 17 invarianti strutturali in `if ... raise` (17 righe).** Coerente con lo
stile del resto del sottosistema. I 34 restringimenti di tipo possono restare `assert`: lì
l'idioma è corretto.

**Raccomandazione**: entrambe opzionali e a bassa priorità. B quando si tocca il catalogo.

---

## M3 — 🟢 Codice morto: 7 simboli su 18 355 righe

Scansione differenziale `./dev.py lint --dead-code` con lo scope di produzione completo
(`backend/app` + `scripts` + `dev.py`). Ogni simbolo tracciato secondo la regola
dell'audit: *se la logica non è riassorbita, non si rimuove — si discute.*

| Simbolo | Dove | Verdetto |
|---|---|---|
| `transitive_dependencies` | `components/registry.py:97` | 🟡 **Morto reale.** Vedi sotto |
| `summary_position_count` | `components/payloads/portfolio_broker.py:877` | 🟡 **Morto reale.** Zero riferimenti ovunque, test inclusi |
| `for_domain` (DatasetRegistry) | `datasets/spec.py:234` | 🟢 **Conservare.** Solo test, ma gemello simmetrico di `for_visibility`, che è in produzione a `runtime_service.py:385` |
| `for_domain` (AnalysisRegistry) | `analyses/spec.py:253` | 🟢 **Conservare.** Idem, `runtime_service.py:388` |
| `requested_day_count` | `temporal/plan.py:92` | 🟢 **Conservare.** Porta la definizione T = (end−start).days+1, con test dedicato `test_inclusive_requested_day_count_definition` |
| `db_lock` | `dependencies.py:350` | 🟢 **Conservare.** Il docstring lo dichiara: *"Exposed for introspection/tests only"* |
| `build_count` | `dependencies.py:363` | 🟢 **Conservare.** Docstring: *"test/diagnostic seam"*, serve ad asserire la memoizzazione "at most once per request" |

**Cinque su sette sono falsi positivi dichiarati.** `db_lock` e `build_count` spiegano nel
proprio docstring perché esistono senza chiamanti di produzione: è la differenza fra codice
morto e **seam diagnostico**, e qui è scritta, non da indovinare.

### `transitive_dependencies` — l'unico reperto interessante

`components/registry.py:97` implementa una DFS topologica che restituisce le dipendenze
transitive di un componente in ordine dipendenza-prima. È corretta, è documentata, e non la
chiama nessuno.

**Tracciatura.** Il design ha scelto un'altra strada: `DatasetSpec.section_order` è una
tupla **dichiarata esplicitamente**, validata in `datasets/spec.py:151-154` come
permutazione esatta di `required + optional`. Il `Composer` la scorre in ordine e chiama
`context.resolve(component_id)`; le dipendenze reali vengono risolte **pigramente** da
`BuildContext._build`, che ricorre su `spec.dependencies` prima di invocare il builder.

Quindi `section_order` governa solo l'**ordine di presentazione**, mai la correttezza —
e un risolutore topologico non serve.

Ma c'è di più: la stessa classe contiene **una seconda DFS**, `_detect_cycles`
(`registry.py:56`), che è in produzione e attraversa lo stesso grafo. Due traversate,
una viva e una morta, a quaranta righe di distanza.

**Verdetto: logica riassorbita** (da `section_order` + risoluzione pigra) **e traversata
duplicata** (da `_detect_cycles`). Rimozione sicura, 14 righe.

`summary_position_count` (`portfolio_broker.py:877`) non ha invece alcuna storia: zero
riferimenti, nemmeno nei test. Rimozione sicura.

---

## M4 — 🟡 *DRY orfano*: sesta e settima occorrenza, in codice appena scritto

Il pattern coniato in `INDEX.md` era stato osservato in cinque sottosistemi. *DRY* è
*Don't Repeat Yourself*; *orfano* significa che l'astrazione esiste ma non ha utilizzatori.
La sequenza è sempre questa:

> 1. Qualcuno scrive la cosa giusta — una costante, una property, un helper.
> 2. Un secondo sviluppatore ha bisogno di quel valore. Non sa che l'astrazione esiste, o è
>    più veloce riscriverlo a mano. Lo riscrive.
> 3. Un terzo, uguale. Un quarto, uguale.
> 4. Risultato: l'astrazione ha **zero riferimenti** (sembra codice morto) **e** il valore è
>    duplicato in N punti.
>
> Si ottiene il **peggio dei due mondi**: la duplicazione che si voleva evitare *e* del
> codice non usato. Per questo la risposta giusta quasi mai è "rimuovere": è **adottare**.

Finora l'avevo attribuito alla stratificazione storica: codice vecchio, autori diversi,
astrazioni dimenticate. **Questo report smentisce quella diagnosi.** Il pattern si presenta
identico nel codice più recente e più curato del progetto.

### M4.1 — `AI_EXPORT_DEFAULT_DETAIL_LEVEL`

`frontend/src/lib/features/ai-export/catalog/shared.ts:38`

```ts
export const AI_EXPORT_DEFAULT_DETAIL_LEVEL = 'standard' satisfies AiExportDetailLevel;
```

Zero riferimenti. Nel frattempo il letterale `'standard'` è re-inlinato in **cinque punti**,
e in quattro di essi con la **stessa identica espressione di fallback**:

| File | Riga | Espressione |
|---|---:|---|
| `aiExportMemory.ts` | 138 | `detailLevel: 'standard'` |
| `aiExportMemory.ts` | 149 | `supportedDetailLevels.includes('standard') ? 'standard' : supportedDetailLevels[0]` |
| `aiExportOptions.ts` | 189 | idem |
| `AiExportOptionsPanel.svelte` | 102 | idem |
| `AiExportOptionsPanel.svelte` | 123 | idem |

La regola "usa `standard` se supportato, altrimenti il primo disponibile" è scritta
**quattro volte**, due delle quali nello stesso file a 21 righe di distanza. Cambiare il
default richiede oggi cinque modifiche, e la costante che dovrebbe governarle sta due file
più in là, inutilizzata. Dimenticarne una produce un comportamento incoerente; nel frattempo
il linter segnala la costante come morta e ne suggerisce la rimozione — che è esattamente la
mossa sbagliata.

**Rimedio ✅ APPLICATO** — esportato l'helper accanto alla costante, in
`catalog/shared.ts`:

```ts
export function resolveDefaultDetailLevel(supportedDetailLevels: readonly AiExportDetailLevel[]): AiExportDetailLevel {
    return supportedDetailLevels.includes(AI_EXPORT_DEFAULT_DETAIL_LEVEL) ? AI_EXPORT_DEFAULT_DETAIL_LEVEL : supportedDetailLevels[0];
}
```

Tutti e cinque i punti sono stati convertiti: 4 a `resolveDefaultDetailLevel(...)`, 1
(`aiExportMemory.ts:138`, che non ha una lista di livelli supportati) alla costante
`AI_EXPORT_DEFAULT_DETAIL_LEVEL`. Verificato: `svelte-check` 0 errori / 0 warning,
106/106 test vitest verdi, knip non segnala più `AI_EXPORT_DEFAULT_DETAIL_LEVEL` fra gli
orfani. Cambiare il default ora richiede **una sola modifica**.

Una costante nuda invita a re-inlinare il valore; una funzione che incapsula *la regola*
no. È la lezione trasversale delle occorrenze del pattern.

### M4.2 — `isDatasetCatalogEntry` — ⚠️ diagnosi corretta: **non** era un *DRY orfano*

`templates/promptRenderer.ts:419` definiva il type guard:

```ts
export function isDatasetCatalogEntry(entry: ...): entry is AiExportDatasetCatalogEntry {
    return entry.kind === 'dataset';
}
```

La prima stesura lo classificava come *DRY orfano*, sostenendo che il confronto
`kind === 'dataset'` fosse re-inlinato in tre punti. **Tentando di applicare il rimedio, la
diagnosi si è rivelata sbagliata**: i tre punti non sono equivalenti.

| Sito | Tipo dell'operando | Il guard è applicabile? |
|---|---|---|
| `catalog/compatibility.ts:64` | `AiExportCatalogEntry` | Sì, ma **inutile** — vedi sotto |
| `aiExportClipboard.ts:87` | `AiExportCompatibleSelection` | **No**: tipo diverso, la firma non lo accetta |
| `templates/promptRenderer.ts:382` | `AiExportCompatibleSelection` | **No**: idem, e serve solo a scegliere una stringa |

E anche nell'unico sito compatibile il guard non aggiunge nulla: `AiExportCatalogEntry` è
un'**unione discriminata** su `kind`, e TypeScript restringe già nativamente con
`entry.kind === 'dataset'`. Un type guard esplicito serve solo dove il narrowing non è
inferibile — tipicamente dentro una callback di `.filter()`. Verificato: **non esiste alcun
`.filter()` su catalog entry** che ne trarrebbe beneficio.

**Verdetto corretto: funzione realmente inutilizzata, logica riassorbita dal compilatore.**
Zero riferimenti in tutto `frontend/src` e `frontend/e2e`, test inclusi.

**✅ RIMOSSA** (3 righe), insieme all'import di tipo `AiExportDatasetCatalogEntry` rimasto
inutilizzato in `promptRenderer.ts`. Verificato: `svelte-check` 0 errori, 106/106 test verdi,
knip non la segnala più.

> **Lezione di metodo**: questo errore è emerso solo *tentando la correzione*. Un reperto
> d'audit basato su corrispondenza testuale (`kind === 'dataset'` appare 3 volte) può
> nascondere tipi diversi. Prima di dichiarare una duplicazione, verificare che gli operandi
> siano dello stesso tipo.

### M4.3 — `AI_EXPORT_DOMAIN_ORDER`

`catalog/shared.ts:39` — zero riferimenti. Nessuna duplicazione manuale (l'unico gemello è
l'enum Zod in `generated.ts`, autogenerato). È semplicemente inutilizzata: rimozione sicura,
o adozione dove l'ordine dei domini viene deciso.

### M4.4 — Tre helper di staleness superati

knip segnala in `aiExportOptions.ts:200-210`:

| Simbolo | Verdetto |
|---|---|
| `aiExportStatsContextFingerprint` | ✅ riassorbito da `capturePreparationContext` (`AiExportMenu.svelte:146`) |
| `isAiExportStatsRequestCurrent` | ✅ riassorbito da `isPreparationContextCurrent` (`:159`) |
| `getMatchingAiExportStats` | ✅ riassorbito dalla coppia `pending` / `pendingContext` |

**Tracciato e verificato.** Il sostituto non è solo equivalente, è **più forte**:
`isAiExportStatsRequestCurrent` confrontava due valori (generazione + fingerprint),
`isPreparationContextCurrent` ne confronta sei — `contextEpoch`, `operationId`, generazione
di sessione, utente di sessione, chiave di memoria e fingerprint delle opzioni.

Il nome della vecchia costante lo conferma: `'ai-export-stats-context-v3'`. Erano alla
terza iterazione del protocollo quando è stato sostituito. **Rimozione sicura**, 11 righe.

---

## M5 — 🟢 Complessità: tutta nei validatori

17 funzioni oltre soglia 10, massimo **22**. Ma è la loro *natura* a distinguerle.

| Funzione | Compl. | Tipo |
|---|---:|---|
| `datasets/spec.py:112 __post_init__` | 22 | validatore |
| `portfolio_income.py:282 _validate_status_invariants` | 19 | validatore |
| `drawdown_context.py:192 _validate_success` | 17 | validatore |
| `technical_shared.py:917 build_indicator_table_payloads` | 17 | costruttore |
| `analyses/spec.py:134 __post_init__` | 16 | validatore |
| `components/spec.py:88 __post_init__` | 14 | validatore |
| `types.py:183 __post_init__` | 14 | validatore |
| `temporal/aggregators.py:102 __post_init__` | 14 | validatore |
| `technical_shared.py:1346 build_breadth_payload` | 14 | costruttore |
| `*_registry.py validate_replacements_against_placeholders` (×2) | 12 | validatore |
| … altre 6 | 12–13 | 5 validatori, 1 costruttore |

**Quattordici su diciassette sono validatori.** Il confronto con il resto del backend è netto:

| | AI Export | Resto del backend |
|---|---|---|
| Funzione più complessa | `__post_init__` **22** | `execute_batch` **112** |
| Natura | verifica di contratto | logica di business |
| Effetto del debito | il contratto è verificato | il ramo non è coperto |

Questa è **complessità che previene i difetti**, non complessità che li causa. Un
`__post_init__` di complessità 22 è 22 modi di rifiutare uno spec malformato all'avvio: è
esattamente il posto dove la si vuole. Nessun intervento.

Vale però la nota di § K5: alzare `max-complexity` da 10 a 25 archivierebbe tutti e 17
questi avvisi senza perdere segnale, lasciando visibili solo i mostri veri del resto del
backend.

### Il caso `TRY003` — 515 rilievi che non significano nulla

`TRY003` (*messaggio lungo dentro `raise`*) da solo vale 515 dei 695 rilievi ruff estesi
del sottosistema, cioè il **74 %**. Esempio tipico:

```python
raise DatasetSpecError(f"{self.dataset_id}: section_order must be exactly a permutation of required+optional component IDs")
```

La regola esiste per scoraggiare messaggi costruiti ad hoc al posto di eccezioni
tipizzate. Qui l'eccezione **è** tipizzata (`DatasetSpecError`) e il messaggio è
diagnostico: dice quale spec, quale campo e quale regola. È il messaggio che uno
sviluppatore leggerà alle 2 di notte quando l'app non parte.

**Rilievo respinto.** Se si adottasse `TRY` nella configurazione del progetto, `TRY003`
andrebbe messa in `ignore`. Registrarlo qui evita che qualcuno, un domani, "ripulisca"
515 messaggi diagnostici per far tacere un linter.

---

## M6 — 🟢 Due ipotesi di difetto, entrambe smentite

Le riporto perché un'ipotesi cercata e non trovata dice qualcosa sul codice.

### Ipotesi 1 — Deadlock su ciclo di dipendenze

`BuildContext._build` (`dependencies.py:456`) risolve ricorsivamente `spec.dependencies`
attraverso `resolve`, che usa un `asyncio.Lock` per componente. Con un ciclo A→B→A, il
secondo `resolve(A)` dallo stesso task troverebbe `_results[A]` ancora vuoto e tenterebbe
di riacquisire un lock non rientrante: **hang permanente**, non errore.

**Smentita.** `ComponentRegistry.__init__` chiama `_detect_cycles()` (`registry.py:56`), una
DFS con tracciamento del cammino che solleva `ComponentDependencyCycleError` riportando il
ciclo completo. L'auto-dipendenza è rifiutata a monte in `ComponentSpec.__post_init__`
(`spec.py:106`). Il grafo non può contenere cicli al momento della costruzione.

### Ipotesi 2 — `section_order` non verificato contro il grafo delle dipendenze

`section_order` è dichiarato a mano e validato solo come permutazione di
`required + optional`. Nessuno verifica che rispetti l'ordine topologico.

**Smentita come difetto**: la risoluzione è pigra e memoizzata, quindi l'ordine dichiarato
non può produrre una dipendenza non ancora costruita. Governa solo la presentazione. Resta
vero — ed è § M3 — che `transitive_dependencies` sarebbe stato il verificatore naturale di
quell'ordine, se il progetto avesse deciso di volerlo.

### E una che ho trovato già risolta

Il caso più difficile del modulo è la **rientranza del lock DB**: un loader `db_resource`
che ne chiama un altro dallo stesso task si bloccherebbe su un `asyncio.Lock` non
rientrante. Il docstring lo enuncia esplicitamente sotto *"Reentrancy invariant"* e lo
risolve con `_db_lock_owner` + `_db_lock_depth`.

Il docstring di `dependencies.py` è **60 righe di invarianti dichiarati** — semantica
successo/fallimento, separazione cache componenti / cache risorse, serializzazione della
sessione condivisa, rientranza. È il pezzo di documentazione tecnica migliore del progetto,
e spiega perché gli strumenti qui non trovano nulla: i problemi difficili sono stati
pensati prima, non scoperti dopo.

---

## M7 — Copertura e impianto di test

**93,47 %** su 7 407 statement (49 file), contro l'89,73 % del resto del backend.

| File | Stmt | Copertura |
|---|---:|---:|
| `temporal/aggregators.py` | 229 | 83,8 % |
| `api/v1/ai_export.py` | 54 | 85,2 % |
| `components/fx_payloads.py` | 341 | 85,3 % |
| `components/fx_timing_context.py` | 235 | 86,4 % |
| `components/drawdown_context.py` | 230 | 87,4 % |
| `analyses/spec.py` | 170 | 87,6 % |
| `components/technical_payloads.py` | 307 | 87,9 % |

Nessun file sotto l'83 %. Per confronto, il resto del backend ha nove file sotto il 79 %.

**56 file di test per 44 386 righe** — rapporto **2,42:1** contro lo **0,79:1** del resto
del backend, più 4 spec E2E Playwright dedicate (catalogo, contratto, memoria, pannello).

Il report 12 aveva rilevato 14 funzioni AI Export a copertura zero, lasciate fuori scope.
Riviste ora: sono `__hash__`/`__eq__` di `ResourceKey`, property di `BuildContext`
(`registry`, `db_lock` — vedi § M3), `map_*_row` e `_build_*_context_events`. **Nessuna è
codice morto**; sono rami di adattatori raggiunti solo da combinazioni di dominio che i
test non esercitano. 28 statement su 7 407: irrilevanti.

---

## M8 — Osservazioni operative

### 🟢 L'endpoint meglio scritto del progetto

`api/v1/ai_export.py` (183 righe) mappa **sette** eccezioni di dominio su sei status HTTP,
ciascuno con un `Problem` tipizzato, un `code` stabile e un `response_model` dichiarato
nella firma. Il contrasto con i reperti del report 01 sull'API layer è totale.

Da notare: `get_ai_export_catalog` è dichiarata `def` e non `async def` — corretto secondo
la Async I/O Rule del progetto, perché non fa I/O. È l'unico punto del codebase dove ho
visto quella regola applicata *nella direzione difficile*.

### 🟢 Budget dei token: input limitati, dimensione dichiarata, utente avvisato

`estimate_tokens_chars_div_4` calcola `estimated_tokens`, che finisce nella risposta ma
**non viene mai confrontato con una soglia lato backend**. Sembrava una lacuna; non lo è.

Il design limita gli **input** (`indicator_history_row_limit` per `detail_level`,
`_STANDARD_MAX_ROWS = 60`) invece di troncare l'output, e delega l'avviso al frontend, che
lo implementa su tre livelli (`aiExportOptions.ts:6-7`): soglia 20 000 token → `warning`,
60 000 → `large`, con blocco della copia automatica e conferma esplicita
(`AiExportMenu.svelte:191`).

È coerente con il confine architetturale dichiarato dal progetto — *il backend possiede i
fatti versionati, il frontend il rendering sicuro*. Nessun intervento.

Una nota, non un difetto: il limite di righe è **per entità**, quindi la dimensione totale
cresce linearmente col numero di posizioni. Su un portafoglio molto grande l'avviso
`large` diventa lo stato normale, e il costo di costruzione lo si paga comunque prima di
vederlo. Se un domani si volesse una stima *preventiva*, il posto giusto è il catalogo
(numero di componenti × righe attese), non un troncamento a valle.

### 🟢 Nessun limite di richiesta su `POST /ai-export/snapshot`

È l'endpoint più costoso del progetto: fino a 67 costruttori di componenti, con tutto
l'I/O DB serializzato su un singolo lock per richiesta. Non ha rate limit né timeout
applicativo.

Per un'applicazione self-hosted e autenticata è una scelta difendibile, e va detto che il
lock singolo *limita già* il danno che una singola richiesta può fare al database. Lo
segnalo per completezza, non come intervento.

---

## Interventi raccomandati

| # | Intervento | Costo | Priorità |
|---|---|---|---|
| 1 | Guardia `if not __debug__: raise` in `main.py` (§ M2) | 2 righe | 🟡 **Fare** |
| 2 | Rimuovere `transitive_dependencies` (`registry.py:97`) e `summary_position_count` (`portfolio_broker.py:877`) | −14 righe | 🟢 |
| 3 | Rimuovere i 3 helper di staleness superati in `aiExportOptions.ts:200-210` (§ M4.4) | −11 righe | 🟢 |
| 4 | Sostituire il fallback `'standard'` triplicato con `resolveDetailLevel()` (§ M4.1) | ~6 righe | 🟢 |
| 5 | Usare `isDatasetCatalogEntry` nei 3 punti che inlinano `kind === 'dataset'`, o rimuoverlo (§ M4.2) | ~4 righe | 🟢 |
| 6 | Rimuovere o adottare `AI_EXPORT_DOMAIN_ORDER` (§ M4.3) | 1 riga | 🟢 |
| 7 | Convertire i 17 `assert` strutturali in `if ... raise` tipizzati (§ M2, opzione B) | 17 righe | 🟢 quando si tocca il catalogo |
| 8 | Se si adotta `TRY` in ruff, mettere `TRY003` in `ignore` (§ M5) | 1 riga di config | 🟢 |

**Nessun intervento su architettura, concorrenza, complessità o copertura.** Il totale
delle rimozioni proposte è **30 righe su 25 748**.

---

## Nota per il resto del progetto

Il valore di questo report non è nei suoi otto interventi minori. È nell'aver misurato,
con gli stessi strumenti e nello stesso codebase, **cosa produce un contratto esplicito**.

Il report 05 aveva già osservato che *registry + contratto astratto si autopuliscono*:
`charts/` aveva 1 orfano in 4 288 righe, i plugin signal+risk 1 in 10 903, contro i 26 in
6 665 di `lib/stores/`. L'AI Export porta la stessa evidenza su una scala dieci volte
maggiore e su codice scritto ieri: 0,38 simboli morti per 1 000 righe, zero N+1, zero
violazioni async, complessità massima 22.

La differenza non è la bravura di chi scrive. È che qui **ogni componente deve dichiararsi**
— id, versione, dipendenze, livelli di dettaglio, visibilità, applicabilità — e ogni
dichiarazione è verificata all'avvio. Un componente che nessuno usa non passa inosservato:
non compare in nessun `section_order`, e il conteggio non torna.

Dove questa disciplina manca — `lib/stores/`, `schemas/`, `components/ui/` — il codice
morto si accumula perché **nulla obbliga a dichiarare cosa esiste e perché**.

E l'eccezione conferma la regola: l'unico difetto ricorrente sopravvissuto anche qui è il
*DRY orfano* (§ M4), che colpisce **costanti e helper liberi**, cioè esattamente gli unici
oggetti del sottosistema che non passano da un contratto dichiarato.

---

*Report 13 di 13 — Audit AI Export, eseguito a lavoro dell'altro agente concluso.
Torna a [`INDEX.md`](INDEX.md).*
