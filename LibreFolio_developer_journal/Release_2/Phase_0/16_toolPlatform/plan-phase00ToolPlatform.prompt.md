# Piano — Piattaforma Tool atomica

**Stato:** 🟡 CHECKPOINT PRONTO · NON INTEGRATO · NON ARCHIVIATO
**Data checkpoint:** 2026-09-10
**Owner:** C — Piattaforma Tool
**Branch/worktree al checkpoint:** `e-alfy-tool-platform-c-r2` /
`e-alfy-turbo-fortnight`
**Base fisica del worktree:** `4a73f5f63447e01b51993afb2e3c73e2c22a9a28`
**Base runtime da incorporare dopo commit manuale:**
`916f12bddf3eb9b8e834e4b9033eb52ce4bde25a`

← Backlog: [05 — Piattaforma Tool e allocatore PAC](../09_feedbackJobs/05_pac_allocation_tool.md)
← Piano sprint: [06 — SP12–14](../09_feedbackJobs/06_piano_sprint.md)
→ Inventario checkpoint: [manifest-integrazione-C.md](manifest-integrazione-C.md)

## 1. Scopo e decisioni chiuse

La piattaforma ospita plugin Tool atomici e riusabili. Ogni item riceve tutti i dati
espliciti, viene eseguito in un processo posseduto dalla piattaforma e restituisce un
output tipizzato. Il calcolo non riceve utente, sessione DB, provider, service layer
o autorita' implicita sul portafoglio.

Decisioni del developer:

- Tre endpoint autenticati: catalogo completo, compute bulk eterogeneo e diagnostica
  read-only. Nessun endpoint schema, prefill, job, cancel o MCP in questo incremento.
- Diagnostica disponibile a tutti gli utenti attivi autenticati, non solo admin;
  nessuno scenario, risultato personale, trace o log grezzo.
- Modelli Pydantic/TypeAdapter come unica fonte e validatore. Nessuna dipendenza
  `jsonschema` e nessun modello TypeScript finanziario scritto a mano.
- Un processo distinto per ogni item, anche con input identici: niente coalescing,
  cache cross-user o deduplica fisica.
- Plugin autorizzati a creare thread/processi figli soltanto se restano nel dominio
  di cleanup del job e terminano prima del rilascio della capacita'.
- UI custom compilata; nessun path/URL/codice server eseguito dal frontend e nessun
  form finanziario generico di fallback.
- Link documentazione costruito con `DocsLink` e lingua frontend corrente.
- Metriche backend separate dal risultato finanziario; valori non osservati `null`,
  tempi paralleli non sommati come latenza.

Fuori scope: solver PAC completo, copie portfolio, Broker fractional, state machine,
chaining tra Tool, accesso service-layer dai plugin, esecuzione ordini.

## 2. Piano eseguito fino al checkpoint

### ✅ Passo 1 — Contratti e registry (2026-09-08/09)

Creati DTO stretti, base plugin, derivazione schema, registry transazionale, catalogo,
wire JSON Unicode-safe e quarantena. Tutti i distinti contendenti di un codice duplicato
vengono scartati; un import fallito non lascia registrazioni parziali; gli altri Tool
restano disponibili.

> **Note implementazione**: Pydantic genera input schema in validation mode e output
> schema in serialization mode; fingerprint su schemi non adattati + operazioni.
> Discriminatori input obbligatori e senza default. Alias legacy Risk/Signal nel registry
> condiviso restano lazy e API-compatible.

### 🟡 Passo 2 — Worker, executor e API (sorgenti pronti; runtime non validato)

Creati child worker, processo/sessione posseduti, handshake `ready -> ACK`, supervisor,
quote per principal/processo, coda con deadline assoluta, metriche, cleanup di gruppo e
discendenti, route autenticate e mount router/lifespan.

> **Note implementazione**: il processo plugin non entra nel codice del plugin prima
> dell'adozione del gruppo da parte del parent. PID + birth time proteggono dal riuso;
> cleanup non confermato degrada la lane e produce errore piattaforma.
>
> **Limite checkpoint**: nessun processo Tool, timeout, crash o teardown e' stato
> eseguito. I test lifecycle sono scritti ma non lanciati.

### 🟡 Passo 3 — Export e codec (sorgenti pronti; generazione non eseguita)

Preparati documento OpenAPI build-only `paths: {}`, generatore Zod strict, mappa
letterale code/version/fingerprint/UI, adattamento Unicode codepoint, rimozione dei
default soltanto dagli output, type-check virtuale e pubblicazione atomica con lock.
`./dev.py api ... --tools-only` evita l'import dell'app per l'export Tool.

> **Note implementazione**: il lock conserva handle + device/inode e ripulisce anche
> una propria inizializzazione parziale senza rimuovere un lock sostituito. Il path
> output Python usa risoluzione lessicale per non seguire una symlink leaf prima del
> rifiuto.
>
> **Limite checkpoint**: nessun file generato, compile, round-trip P1 o codegen eseguito.

### 🟡 Passo 4 — Frontend generico (sorgenti pronti; type-check non eseguito)

Creati client tipizzato, compatibilita' descriptor/codec, registry renderer compilati,
hub, host, route `/tools`, metriche e pannelli About/diagnostica. L'allowlist renderer
resta vuota: nessun PAC fittizio viene dichiarato disponibile.

> **Note implementazione**: account generation osservata anche alla prima risoluzione;
> richieste e mount vengono abortiti/rimossi al cambio account. Parametri originali
> vengono inviati dopo validazione strutturale, non il risultato default-expanded
> del parser.
>
> **Limite checkpoint**: codec generati assenti, nessun `svelte-check`, Vitest, build
> o mount nel file About definitivo E.

### 🟡 Passo 5 — Test e documentazione

Scritti test DTO, registry, wire e lifecycle. Registrate le unita `schemas tools`,
`services tools-registry` e `utils tools-wire`; la registrazione lifecycle esclusiva
resta in artifact di handoff.

**Evidenza eseguita:** `schemas tools --workers 1` → **214 passed in 0.17s**,
exit0, fingerprint sorgenti invariato, DB C test/prod assenti prima e dopo.

Scritte guide EN utente e developer e skill plugin. Nav MkDocs, traduzioni utente
IT/FR/ES, build e check-links non eseguiti.

> **Limite checkpoint**: i214 test coprono soltanto i DTO Pydantic; non dimostrano
> registry, wire, process tree, API, codec TypeScript, UI o pilot PAC.

### ⏳ Passo 6 — Primo pilot PAC reale

Dipende dall'handoff D dei modelli/core/thin plugin e dal renderer PAC approvato:

```text
PacAnalyzeInput reale
  -> normalizzatore/evaluator D
  -> thin plugin D su base C
  -> catalogo + compute C
  -> worker e output validato
  -> codec generati
  -> host C + componente P1 D
```

Nessuna registry vuota o demo plugin puo' chiudere questo passo.

## 3. Politica iniziale da verificare dopo integrazione

| Limite | Valore |
|--------|--------|
| Item per batch | 1–4 |
| Lane per processo API | 2 |
| Item pendenti per processo | 8 |
| Per principal | 1 batch / 4 item |
| Parametri / risultato item | 128 KiB / 256 KiB |
| Coda / hard / soft | 5s / 5s / 4s |
| Cleanup | 2s, lane ancora occupata |
| Request server / client Tool | 20s / 25s |

Sono limiti di ammissione, non benchmark/SLA o garanzia RAM globale. Con piu' worker
ASGI la capacita' e' per-processo.

## 4. Rientro su `dev_release2`

Il developer esegue commit e merge manualmente; l'agente non esegue
merge/rebase/cherry-pick/commit/reset/stash. Prima del riallineamento:

1. Commit checkpoint C sul delta attuale.
2. Incorporare `dev_release2/916f12bd` con merge manuale del developer.
3. Risolvere semanticamente i tre file overlap nel manifest, senza scegliere un lato.
4. Raccordare successivamente il pacchetto E committato: About definitivo, i18n e
   registro utility.
5. Eseguire soltanto nella lane C isolata, dopo VIA:

```text
./dev.py test --test-port 6142 --data-dir /tmp/librefolio-r2-c <categoria> <azione>
./dev.py server --test --port 6142 --data-dir /tmp/librefolio-r2-c
```

Mai `--force`; porta occupata => fallimento chiuso.

## 5. Definition of done residua

- [ ] Merge semantico con `916f12bd` e successivo commit E, senza perdere runtime
      isolation, container registry o registrazioni Tool.
- [ ] Handoff D dei modelli/core/plugin e renderer P1 reali.
- [ ] Export/codegen reale + conformance Unicode/defaults/fingerprint.
- [ ] Test registry e wire; test lifecycle esclusivi; API auth/bulk/diagnostics.
- [ ] Type-check, Vitest/build e test host/client.
- [ ] Mount About sul file E definitivo e applicazione i18n tramite writer coordinato.
- [ ] MkDocs nav, traduzioni utente richieste, build e check-links.
- [ ] Pilot reale e review operativa desktop/mobile/errori.
- [ ] Aggiornamento CHANGELOG per le superfici osservabili.
- [ ] Debug finale, stato integrato e solo allora archiviazione sotto
      `Release_2/phases/16_toolPlatform/`.

Questo piano e' **ready per checkpoint commit**, non integrato e non archiviabile.
