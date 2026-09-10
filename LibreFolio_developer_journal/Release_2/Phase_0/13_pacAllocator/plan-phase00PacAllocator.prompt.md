# Piano Phase 0 - Allocatore PAC e analisi iniziale P1

**Stato:** checkpoint D pronto; integrazione runtime manuale non ancora eseguita

**Data checkpoint:** 2026-09-10

**Baseline D:** `4a73f5f63447e01b51993afb2e3c73e2c22a9a28`

**Runtime da incorporare manualmente:** `916f12bddf3eb9b8e834e4b9033eb52ce4bde25a`

## 1. Confine approvato

Il dev ha approvato `P1-N1`, `P1-C1` e `P1-X1`. Il checkpoint implementa solo:

1. codec Pydantic strict per `operation="analyze"`;
2. normalizzazione Decimal deterministica del draft manuale;
3. valutazione della situazione iniziale e scostamenti per riga;
4. fatti parziali tipizzati e stati onesti;
5. test backend schema e service/evaluator;
6. import lazy dei tre package initializer necessari al confine puro.

Restano fuori:

- solver e ricerca di ordini;
- vendite, fee, buffer, riserve, FX di esecuzione;
- copie da Portfolio, Asset, Broker e FX;
- migrazione `allow_fractional_buys`;
- plugin Tool, API, client generato e renderer;
- UI, i18n, MkDocs e CHANGELOG;
- modifiche a FIFO, WAC, fiscalita, Riskfolio o BRIM.

P1 analizza dati numerici espliciti. Non legge DB, provider, portfolio o Broker. Non
produce ordini, raccomandazioni, fattibilita, no-op o prove di ottimalita.

## 2. Decisioni normative

### 2.1 Identita e aggregazione

- Una riga rappresenta un asset in un contesto/custodia.
- `row_key` e opaco, stabile e univoco.
- `instrument_key` collega lo stesso titolo tra righe solo per i futuri vincoli globali.
- Target, peso e scostamento restano per riga asset x contesto.
- Nomi uguali non implicano identita; rinominare una label non cambia le chiavi.
- Cash aggregato per valuta, mai per broker e mai in una cassa unica gia convertita.
- Cassa esistente e nuovi contributi sono vettori separati.

### 2.2 Precisione

- Tutti i numeri finanziari entrano come stringhe.
- Il core usa `Decimal` con contesto locale e non muta il contesto globale.
- Nessuna decisione passa da `float` o da testo formattato.
- Quantita iniziale frazionaria non viene arrotondata al passo dei nuovi acquisti.
- Prezzo, quantita, quote basis, FX, percentuale e passo conservano unita distinte.
- P1 ammette quote basis 1 e 100.
- Target per riga tra 0 e 100; somma esatta 100.
- Tasso identita della valuta report uguale a 1.
- FX P1 serve solo alla valorizzazione: non sposta cassa.

### 2.3 Stati

`availability` ha quattro valori:

| Stato | Significato |
|---|---|
| `ready` | Situazione iniziale valutabile; non implica ordini fattibili |
| `needs_input` | Dati semanticamente mancanti |
| `invalid` | Dati presenti ma invalidi |
| `unsupported` | Dati validi fuori dal dominio P1 |

Precedenza: `invalid` > `unsupported` > `needs_input` > `ready`.

`trade_feasibility="not_evaluated"` e `optimization="not_run"` sono sempre espliciti.
Investito iniziale zero e un totale disponibile, ma pesi e score sono indisponibili:
non diventano zero, no-op o ottimo.

## 3. Delta implementato

### 3.1 Schema e nucleo

| File | Responsabilita |
|---|---|
| `backend/app/schemas/pac_allocator.py` | Input/output strict, union discriminate, limiti, issue e fact |
| `backend/app/services/pac_allocator/models.py` | Modelli interni immutabili e checkpoint |
| `backend/app/services/pac_allocator/numeric.py` | Contesto Decimal, forma canonica, approssimazione rapporto |
| `backend/app/services/pac_allocator/normalize.py` | Parsing completo, issue ordinati, stato normalizzato |
| `backend/app/services/pac_allocator/evaluator.py` | Valori nativi/report, cash, pesi e score |
| `backend/app/services/pac_allocator/report.py` | Proiezione dei fatti e selezione stato |
| `backend/app/services/pac_allocator/__init__.py` | Entry point puro `analyze_initial_state` |

### 3.2 Confine import

| File | Modifica |
|---|---|
| `backend/app/schemas/__init__.py` | Re-export lazy degli export legacy |
| `backend/app/services/__init__.py` | Re-export lazy dei servizi legacy |
| `backend/app/utils/financial/__init__.py` | Re-export lazy di ROI/WAC |

I tre initializer preservano `__all__`, alias, identita degli oggetti e moduli prima
importabili. Attributi sconosciuti sollevano `AttributeError`. Nessuna manipolazione di
`sys.modules`, fallback vuoto o cambio di formule.

### 3.3 Test e registri

| File | Stato |
|---|---|
| `backend/test_scripts/test_schemas/test_pac_analyze_schemas.py` | Scritto; eseguito nel selector schema |
| `backend/test_scripts/test_services/test_pac_analyze.py` | Scritto; non ancora eseguito |
| `scripts/test_runner/_backend_schemas.py` | Registra `schemas pac-analyze`, isolamento `pure` |
| `scripts/test_runner/_backend_services.py` | Registra `services pac-analyze`, isolamento `pure` |

## 4. Verifica prima del checkpoint

| Prova | Risultato |
|---|---|
| `schemas pac-analyze` eseguito dal coordinatore | 816 passed, 2.48 s |
| DB `backend/data/test/sqlite/app.db` | Assente prima e dopo |
| Fingerprint schema | Invariato |
| `git diff --check` sui file tracked | Nessun errore |
| Residui generati nelle directory P1 | Nessuno |
| `services pac-analyze` | Non eseguito |
| Import compatibility legacy-heavy | Non eseguito |
| Codec reale C/D e codegen | Non eseguito |
| Revisione combinata con `916f12bd` | Non testata |

Il verde schema non certifica evaluator, compatibilita import completa, runner nuovo o
integrazione Tool.

## 5. Checkpoint Git e raccordo runtime

D non esegue commit, merge, rebase, cherry-pick, reset, stash o staging.

Confronto statico:

- merge-base tra baseline D e runtime: `4a73f5f6`;
- runtime contiene due commit successivi: `ef722b55` e `916f12bd`;
- overlap tra i path D e `4a73f5f6..916f12bd`: zero;
- i cinque file tracked modificati da D hanno blob identico a baseline e runtime;
- i nove path P1 nuovi non esistono nel runtime.

Non sono attesi conflitti testuali. Sono possibili raccordi semantici:

1. `916f12bd` cambia isolamento/lifecycle del runner, quindi i selector vanno rieseguiti;
2. la piattaforma C deve usare i veri TypeAdapter P1 e i metadata finali;
3. il wrapper Tool deve usare `context.checkpoint()` e non importare DB/provider;
4. il client generato deve preservare conteggio Unicode per code point e bounds condizionali.

## 6. File da includere ed escludere

Includere tutti i 14 path codice/test elencati sopra e questi artifact di piano.

Non includere:

- file sotto `.copilot/session-state`;
- log `source-*.log`;
- `p1-import-boundary.patch`;
- cache Python/pytest/coverage;
- DB o data directory di test;
- output codegen, frontend, i18n o docs non prodotti da questo slice.

Al checkpoint non risultano file generati indesiderati nel worktree.

## 7. Messaggio commit proposto

```text
feat(pac): add initial-state analysis core

Establish strict Decimal codecs and deterministic partial-fact evaluation
before solver and UI integration. Lazy package exports keep pure PAC imports
detached from DB and BRIM startup.
```

L'agente non esegue il commit.

## 8. Ripresa dopo integrazione manuale

Prerequisito: il dev comunica la revisione combinata effettiva.

Usare solo lane D:

```text
./dev.py test --test-port 6143 --data-dir /tmp/librefolio-r2-d schemas pac-analyze
./dev.py test --test-port 6143 --data-dir /tmp/librefolio-r2-d services pac-analyze
```

Regole:

- un comando/suite alla volta;
- mai `--force`;
- porta 6143 occupata deve fallire chiusa;
- nessun uso di 6041;
- verificare assenza di scritture fuori `/tmp/librefolio-r2-d`;
- fermarsi se manca una dipendenza, senza installarla;
- non espandere a solver/UI/Broker.

Poi eseguire compatibilita import e codec C/D solo con lease esplicito.

## 9. Gate

| Gate | Stato checkpoint | Sblocca |
|---|---|---|
| P1-N1 | Approvato; schema verificato | Core numerico iniziale |
| P1-C1 | ABI approvata; codec integrato ancora pendente | Wrapper C/D futuro |
| P1-X1 | Approvato; codice/test scritti | Verifica backend isolata |
| P1-U1 | Aperto | Solo UI manuale P1 |
| P1-R1 | Aperto | Configurazione runtime/deployment |
| Full contract | Aperto e non bloccante | Solver/copie/UI estesa |

## 10. Passi completati

1. [x] 2026-09-08 - Letto il corpus obbligatorio e fissata baseline.
   > **Nota implementazione**: identita riga/strumento/cassa e scope P1 separati dal solver.
2. [x] 2026-09-08 - Concordato P1-r3 con piattaforma C.
   > **Nota implementazione**: union discriminate, bounds, Unicode e ownership file congelati.
3. [x] 2026-09-09 - Implementati schema, normalizer, evaluator e report.
   > **Nota implementazione**: nucleo puro, Decimal, nessun DB/provider/solver.
4. [x] 2026-09-09 - Implementati test e import boundary lazy.
   > **Nota implementazione**: schema verificato; service/legacy-heavy ancora pendenti.
5. [x] 2026-09-10 - Preparato checkpoint prima del runtime.
   > **Nota implementazione**: overlap path zero; nessun residuo generato; piano reso portabile.
6. [ ] Integrazione manuale del dev con `916f12bd`.
7. [ ] Riesecuzione schema/service nella lane D.
8. [ ] Checkpoint C/D su wrapper e codec reali.

## 11. Artifact collegati

- [Contratto P1-r3](pac-allocator-contract.md)
- [Evidenze checkpoint](pac-allocator-evidence.md)
- [ASCII P1-U1 non ancora approvato](pac-allocator-ux.md)

Questi file descrivono P1. Le sezioni full solver degli appunti precedenti restano
proposte separate e non sono recepite come comportamento implementato.
