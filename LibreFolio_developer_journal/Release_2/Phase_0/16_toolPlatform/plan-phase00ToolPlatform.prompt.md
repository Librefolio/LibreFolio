# Piano — Piattaforma Tool atomica

**Stato:** 🟡 MERGE RISOLTO · BACKEND VALIDATO · FRONTEND/PILOT APERTI
**Data aggiornamento:** 2026-09-10
**Owner:** C — Piattaforma Tool
**Branch/worktree al checkpoint:** `e-alfy-tool-platform-c-r2` /
`e-alfy-turbo-fortnight`
**Primo commit C:** `1656aff6937f08935a902726884fdda4102f46ec`
**MERGE_HEAD risolto, non committato dall'agente:**
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

### ✅ Passo 2 — Worker ed executor (2026-09-10)

Creati child worker, processo/sessione posseduti, handshake `ready -> ACK`, supervisor,
quote per principal/processo, coda con deadline assoluta, metriche, cleanup di gruppo e
discendenti, route autenticate e mount router/lifespan.

> **Note implementazione**: il processo plugin non entra nel codice del plugin prima
> dell'adozione del gruppo da parte del parent. PID + birth time proteggono dal riuso;
> cleanup non confermato degrada la lane e produce errore piattaforma.
>
> **Note implementazione**:62 regressioni lifecycle coprono processi distinti,
> cold deadline, frame parziali, output/alias, figli e nipoti, timeout, crash,
> cancellazione, PID/PGID reuse, escalation, quarantena e rilascio credito.
> Il gruppo leaderless senza identita' viva nota non viene segnalato: resta
> quarantinato finche' il kernel non conferma l'assenza del PGID.
>
> **Limite integrazione**: i tre endpoint sono presenti nell'OpenAPI (121 endpoint
> totali; catalog/compute/diagnostics Tool), ma la suite API condivisa non ha
> raggiunto i test perche' l'avvio server richiede la build frontend e il worktree
> non possiede `node_modules`.

### 🟡 Passo 3 — Export e codec (schema esportato; generazione TS bloccata)

Preparati documento OpenAPI build-only `paths: {}`, generatore Zod strict, mappa
letterale code/version/fingerprint/UI, adattamento Unicode codepoint, rimozione dei
default soltanto dagli output, type-check virtuale e pubblicazione atomica con lock.
`./dev.py api ... --tools-only` evita l'import dell'app per l'export Tool.

> **Note implementazione**: il lock conserva handle + device/inode e ripulisce anche
> una propria inizializzazione parziale senza rimuovere un lock sostituito. Il path
> output Python usa risoluzione lessicale per non seguire una symlink leaf prima del
> rifiuto.
>
> **Note implementazione**: l'export Tool-only Python riesce e produce il documento
> build-only ignorato. Il generatore impone interi safe JS, Unicode codepoint,
> strict objects, discriminatori e rollback atomico.
>
> **Blocco reale**: `api sync --tools-only` si ferma su
> `ERR_MODULE_NOT_FOUND: openapi-zod-client`; `frontend/node_modules` e' assente.
> Nessuna installazione o lettura dell'ambiente Node del checkout principale e'
> stata eseguita. Codec TS, type-check e round-trip restano aperti.

### 🟡 Passo 4 — Frontend generico (integrato nei sorgenti; type-check bloccato)

Creati client tipizzato, compatibilita' descriptor/codec, registry renderer compilati,
hub, host, route `/tools`, metriche e pannelli About/diagnostica. L'allowlist renderer
resta vuota: nessun PAC fittizio viene dichiarato disponibile.

> **Note implementazione**: account generation osservata anche alla prima risoluzione;
> richieste e mount vengono abortiti/rimossi al cambio account. Parametri originali
> vengono inviati dopo validazione strutturale, non il risultato default-expanded
> del parser.
>
> **Note implementazione**: mount About applicato al details Plugin diagnostics E,
> preservando SupportActions/SocialShareModal/currentVersion. Aggiunte102 chiavi
> tramite CLI:2668/2668 in EN/IT/FR/ES. Nav MkDocs aggiornata.
> Il client crea una sola snapshot JSON plain, valida quella snapshot con il codec
> specifico e invia gli stessi byte; getter, Proxy, `toJSON`, cicli, surrogate e
> interi unsafe non possono cambiare lo scenario tra validazione e trasporto.
>
> **Blocco reale**: codec generati assenti; nessun `svelte-check`, Vitest o build
> senza `node_modules`.

### ✅ Passo 5 — Test backend e documentazione EN

Scritti test DTO, registry, wire e lifecycle. Registrate le unita `schemas tools`,
`services tools-registry`, `services tools-lifecycle` esclusiva e `utils tools-wire`.

**Evidenze eseguite sulla lane C6152 / `/tmp/librefolio-r2-c`:**

| Gate | Esito |
|------|-------|
| `utils runtime-isolation` |134 passed |
| `utils tools-wire` | 196 passed |
| `schemas tools` | 214 passed |
| `services tools-registry` |82 passed |
| `services tools-lifecycle` |63 passed |
| `utils container-registry` | 30 passed |
| `test check-orphans` | tutti i file registrati e raggiungibili |
| `lint` | pass |
| `i18n audit` |2668/2668 per tutte le quattro lingue |
| `mkdocs build` / `check-links` | pass /12 link validi |
| `info api` |121 endpoint, inclusi i3 Tool |

Scritte guide EN utente/developer e skill plugin. Nav e build sono integrate;
le traduzioni MkDocs utente IT/FR/ES non sono state avviate.

> **Limite**: backend unit/lifecycle verificato; API HTTP, codec TypeScript,
> UI e pilot PAC non sono validati.

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

## 4. Merge di `dev_release2/916f12bd`

Il developer ha avviato il merge. C ha risolto l'unico UU
`scripts/test_runner/_backend_utils.py` in modo additivo:
`container-registry` + `runtime-isolation` + `tools-wire`.

Gli auto-merge `dev.py` e `scripts/cli_base.py` conservano runtime isolation,
dotenv/lane ID/data-dir/fail-closed ed estensioni Tool per export/freshness.
Indice finale senza conflitti:192 path staged, nessun file unstaged.
Nessun merge commit e' stato creato dall'agente.

Lane usata:

```text
PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py \
  test --test-port 6152 --data-dir /tmp/librefolio-r2-c <categoria> <azione>
```

Mai `--force`; porta occupata => fallimento chiuso.

> **⚠️ Fuori pista**: il primo comando senza il nome venv standard ha creato un
> virtualenv worktree vuoto e si e' fermato su `argcomplete` prima dei test.
> Non e' stato installato o cancellato nulla in quell'ambiente; tutti i comandi
> successivi hanno usato `PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc`.
>
> **⚠️ Fuori pista API**: il primo `info api` leggeva i marker lazy
> `_IncludedRouter` e mostrava9 route. L'utility ora enumera `app.openapi()`:
>121 endpoint, inclusi catalog/compute/diagnostics. Il gate `api system` non ha
> raggiunto i test perche' il server condiviso richiede una build frontend stale,
> bloccata dall'assenza di dipendenze Node nel worktree.

## 4.1 Hardening dopo review

Due review read-only hanno prodotto correzioni e regressioni:

- frame multiprocessing letto incrementalmente con select/deadline, limite prima
  del payload e controllo post-decode;
- assenza PGID confermata dal kernel; gruppo leaderless senza owner vivo non segnalato;
- output con computed field o alias validation/serialization divergenti in quarantena;
- nested TypedDict/dataclass e keyword non supportate dal codegen in quarantena;
- interi JSON limitati all'intervallo safe JS anche nello schema/Zod;
- snapshot client plain unica, validata dal codec Tool-specific e inviata byte-identica;
- elenco endpoint derivato dall'OpenAPI materializzato.

La review successiva ha trovato quattro residui sui confini sopra; sono stati
corretti e coperti da regressioni backend. Il test frontend client/AST resta
pendente per l'assenza delle dipendenze/codecs generati.

## 5. Definition of done residua

- [x] Merge semantico con `916f12bd` risolto senza perdere runtime isolation,
      container registry o registrazioni Tool; merge commit manuale ancora atteso.
- [ ] Handoff D dei modelli/core/plugin e renderer P1 reali.
- [ ] Export/codegen reale + conformance Unicode/defaults/fingerprint.
- [x] Test registry, wire e lifecycle esclusivi.
- [ ] API auth/bulk/diagnostics su server integrato.
- [ ] Type-check, Vitest/build e test host/client.
- [x] Mount About sul file E definitivo e applicazione i18n via CLI.
- [ ] MkDocs traduzioni utente richieste; nav/build/check-links completati.
- [ ] Pilot reale e review operativa desktop/mobile/errori.
- [ ] Aggiornamento CHANGELOG per le superfici osservabili.
- [ ] Debug finale, stato integrato e solo allora archiviazione sotto
      `Release_2/phases/16_toolPlatform/`.

Questo piano e' **merge-resolved e backend-validated**, ma non chiudibile:
codegen/frontend/API e pilot PAC restano aperti.
