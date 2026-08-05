# Report Phase 0 — AI Export final audit and closure V1

**Data**: 2026-08-05  
**Baseline codice**: `54a15b42`  
**Baseline probe**: `20260804T214400.268752Z`  
**Candidate autorevole**: `20260804T224056.073291Z`

## 1. Decisione

AI Export V3 è chiuso con un solo runtime component-based.

Il catalogo pubblico resta invariato:

- Snapshot wire schema V2;
- Catalog/selection V3;
- 8 Dataset pubblici;
- 11 Analysis pubbliche;
- 67 componenti e 40 dataset nel registry interno;
- stessi ID, versioni, prompt, P/M/K, eventi, scope e semantica
  zero/unavailable/not-applicable.

Il candidate è dichiarato autorevole perché tutti i gate tecnici sono verdi e
il confronto reale ha classificato **114/114 prompt come invariati**.

## 2. Riduzione architetturale

### 2.1 Runtime eliminato

È stato rimosso l'intero stack storico profile/assembler:

| Area | Eliminazione |
|---|---|
| Orchestrazione V1 | `service.py`, `resolver.py` |
| Modelli/schema V1 | `models.py`, `backend/app/schemas/ai_export.py` |
| Profili | `profiles/**` |
| Assembler | `assemblers/**` |
| Logica legacy | `sampling.py`, `coverage.py`, `technical.py`, `normalization.py` |
| Test legacy | 9 file service/schema |
| Fixture legacy | 4 fixture `legacy_semantics` |
| Analysis interne | 11 spec non pubbliche e non selezionabili |

La modifica sorgenti/test/runner coinvolge 64 file:

- **890 righe aggiunte**;
- **21.901 righe eliminate**;
- saldo **-21.011 righe**.

### 2.2 Runtime rimasto

Il percorso live è ora unico:

```text
API V1
  -> AiExportRuntimeService
     -> component registry
     -> dataset registry
     -> public analysis registry
     -> ComponentComposer
     -> Snapshot V2
```

Gli helper FIFO usati dal runtime V3 sono stati spostati in
`components/payloads/portfolio_broker.py`. `telemetry.py` conserva solo
serializzazione JSON canonica e stima token chars/4. Il package
`ai_export/__init__.py` non importa più moduli legacy.

## 3. Duplicazioni valutate

| Duplicazione | Decisione | Motivo |
|---|---|---|
| Runtime profile/assembler vs component runtime | Rimossa | Il primo non era raggiunto dall'API |
| 11 Analysis interne legacy | Rimosse | Non componibili né selezionabili |
| Count registry duplicato in test Drawdown | Rimosso | Stale e già coperto dal test catalogo canonico |
| Catalogo pubblico backend/frontend | Conservato | Handshake fail-closed contro drift incompatibile |
| Test frontend catalog drift + metadata | Conservati | Coprono responsabilità differenti |
| Entity directory/applicability dispatch | Non rifattorizzati | Trasversali, coperti e senza beneficio netto di chiusura |

## 4. Ottimizzazioni exact-output

| Misura | Baseline | Candidate | Delta |
|---|---:|---:|---:|
| Cold import mediano | 1.429,93 ms | 1.345,97 ms | -5,9% |
| Catalogo per chiamata | 0,295 ms | 0,00082 ms | -99,7% |
| Full JSON dump per stats | 3 | 1 | -66,7% |
| Stats snapshot 500 KB | 5,20 ms | 2,22 ms | -57,3% |
| Output misurato | 501.065 | 501.065 | invariato |

Le ottimizzazioni applicate sono:

- registry e composer default condivisi e immutabili;
- catalogo statico cacheato;
- fixed-point intero sulla lunghezza dei contatori;
- un solo dump canonico completo;
- costruzione envelope API dal payload interno già validato, senza
  `model_dump -> model_validate` profondo.

Il cold import resta dominato dagli import generali del backend; non è stato
introdotto lazy-loading speculativo.

## 5. Audit test

### 5.1 Runner e orphan

Sono stati registrati:

- `test_ai_export_components_broker_adequacy.py`;
- `test_ai_export_components_drawdown_context.py`;
- `test_ai_export_components_portfolio_income.py`.

Il runner ora riporta zero orphan in backend e frontend.

### 5.2 Gate finali

| Gate | Esito |
|---|---:|
| Backend service AI Export | 835 passed |
| Backend schema AI Export | 16 passed |
| Backend API AI Export | 15 passed |
| Probe utility | 56 passed |
| Temporal contract | 182 passed |
| Frontend unit AI Export | 199 passed |
| Playwright AI Export | 34 passed |
| Frontend typecheck | 0 error, 0 warning |
| i18n audit | 2.332/2.332 per EN/IT/FR/ES |
| Orphan audit | 0 orphan |

La suite temporal è una vista mirata inclusa nell'audit service e non va
sommata al totale service.

Sul change set finale, Ruff e Black passano per tutti i 26 file Python
modificati, Prettier passa sul frontend e `git diff --cached --check` è pulito.
Il lint Ruff globale del worktree segnala 36 violazioni preesistenti in file
fuori dal change set AI Export; non sono state modificate.

### 5.3 Nuova copertura aggiunta

- clipboard `NotAllowedError` trasformato in errore tipizzato;
- renderer redditi con conversione parziale e reason code, senza zero inventati;
- E2E clipboard fiscale con manifest FIFO, inventario minusvalenze, cassetto
  fiscale, scadenze e strategie condizionali;
- classificazione/cutoff/residuo/helper FIFO;
- identità registry condivisi e cache catalogo;
- fixed-point stats su soglie digit-count, Unicode e snapshot grandi;
- equivalenza envelope precedente/ottimizzato;
- vecchi Analysis ID non selezionabili;
- input mini-history uniformi e relativi invarianti.

### 5.4 Coverage

| Area | Coverage |
|---|---:|
| Moduli AI Export live | 77,78–100% |
| Core finanziari | circa 97–99% |
| `runtime_service.py` | 90,88% |
| Schema runtime | 91,71% |

I branch residui sono prevalentemente guard difensivi o combinazioni di
validator già coperte semanticamente. Non sono stati aggiunti test artificiali
per inseguire una percentuale.

## 6. Probe reale

| Misura | Baseline | Candidate |
|---|---:|---:|
| Prompt richiesti | 114 | 114 |
| Successi | 114 | 114 |
| Failure/skip | 0 | 0 |
| Prompt retained | 36 | 36 |
| Secret scan | passed | passed |
| DB primario/source | invariato | invariato |

Confronto:

- **114/114 stable key `unchanged`**;
- 0 regressioni;
- 0 delta caratteri;
- 0 delta byte;
- 0 delta composizione;
- 0 delta eventi;
- 0 delta stato.

La review manuale ha incluso minimo, mediana, P90, massimo, FIFO fiscale, FX e
dati parziali. Non sono emersi payload vuoti, manifest incoerenti, zero
inventati o omissioni semantiche.

## 7. Task Adequacy

Il catalogo finale contiene 11 Analysis, ciascuna verificata su:

- periodi 3M e 1Y;
- detail Compact, Standard e Full.

Totale: **66 varianti**.

- 54 review sono state riusate dal run autorevole precedente perché
  selezione, composizione e contratto sono invariati;
- 12 varianti `portfolio.fiscal_lots` e `broker.fiscal_lots` sono state
  rilette sul nuovo contratto;
- risultato: **66 OPTIMAL, 0 SUFFICIENT, 0 INSUFFICIENT**.

Le Analysis fiscali ora chiedono esplicitamente inventario ufficiale delle
minusvalenze, giurisdizione, regime, categoria, origine/scadenza, importi
usati/residui e regole di compensazione prima di confrontare scenari
condizionali. Il FIFO economico resta distinto dal trattamento fiscale legale.

## 8. Documentazione

Sono state aggiornate solo le fonti inglesi relative a:

- runtime unico component-based;
- composizione 67/40/11;
- comandi runner, coverage e orphan audit;
- rimozione del runtime profile/assembler.

La build MkDocs è verde. `mkdocs check-links` trova 18 link statici validi e un
solo falso positivo/preesistente `${lang` in `AboutTab.svelte:145`, non legato
ad AI Export.

Le traduzioni e gli hash della pipeline parallela non fanno parte di questo
task e non devono essere inclusi nello staging sorgenti.

## 9. Rischi residui accettati

1. Il cold import include ancora il costo generale del backend; il beneficio di
   un lazy-loading più aggressivo non giustifica ora la complessità.
2. Il catalogo frontend duplica intenzionalmente il contratto pubblico per
   bloccare drift incompatibili.
3. Dati provider o fiscali non disponibili restano dichiarati come parziali o
   unavailable; il sistema non tenta inferenze legali.
4. Il link dinamico `${lang` resta un falso positivo fuori scope.
5. Il worktree parallelo conserva 36 lint violation Ruff fuori dal change set;
   nessuna riguarda i file AI Export in staging.

## 10. Chiusura

Il candidate `20260804T224056.073291Z` è il run autorevole di chiusura.

AI Export è ora più piccolo, con un solo runtime, tutti i test registrati,
algoritmi più efficienti a output identico e copertura mirata delle failure
mode osservabili. Non sono necessarie ulteriori modifiche architetturali per
chiudere questo task.

Lo staging finale contiene solo 64 file sorgenti/test/runner
(`+890/-21.901`). MkDocs, journal, devWiki, traduzioni e probe restano
intenzionalmente unstaged.
