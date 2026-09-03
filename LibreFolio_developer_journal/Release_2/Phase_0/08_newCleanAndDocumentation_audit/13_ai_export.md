# 13 — AI Export — verifica 2026-09-02

> Fonte: [report archiviato](../../phases/05_cleanAudit/13_ai_export.md) (audit 2026-08-07, commit `09cbb7e2`)
> Metodo: analisi statica read-only; nessun test eseguito (run full in corso, DB condiviso).
> Working tree con modifiche beta non committate del 02/09 incluse nella verifica
> (`drawdown_context.py` full_history, `signal_plugins/drawdown.py`, test, CHANGELOG).

---

## Sintesi esecutiva

Il giudizio del vecchio report — *il codice migliore del progetto* — **regge un mese dopo**,
e l'esecuzione S1–S3 ha chiuso **tutti i reperti azionabili**: i 2 simboli morti reali
(`transitive_dependencies`, `summary_position_count`), il *DRY orfano* del default detail
level (fattorizzato sui 5 siti, **nessun nuovo sito nato a mano**), `isDatasetCatalogEntry`,
i 3 helper di staleness, `AI_EXPORT_DOMAIN_ORDER`. L'unico reperto lasciato aperto è quello
che il report stesso aveva **declassato a igiene** (guardia `__debug__` / conversione dei
17 `assert` strutturali): mai applicato, ancora valido come proposta opzionale.

Metriche strutturali riprodotte: **17 errori C901, complessità massima 22 — identici**;
conteggi catalogo invariati (67 componenti / 40 dataset / 8 pubblici / 11 analisi);
registry ancora costruito e verificato all'avvio (`runtime_service.py:120` →
`registry.py:54 _detect_cycles`). Righe: 18 225 backend / 7 383 frontend (25 608 totale,
−140 dal report, coerente con le rimozioni). **Due numeri del vecchio report non si
riproducono**: "56 file di test / 44 386 righe / 2,42:1" e "59 file importano ai_export"
— al commit d'audit i file di test che menzionano `ai_export` erano 23 (25 944 righe);
il perimetro originale non è ricostruibile per grep (probabile conteggio transitivo).

**Nuovo rilievo** (beta 02/09, working tree): il cambio semantico drawdown full_history è
coerente e ben documentato (docstring, test +69 righe, CHANGELOG, `DrawdownParams.full_history`),
ma i 4 `ComponentSpec` drawdown restano `version=1` e `period_behavior=WINDOWED` mentre il
loader ora ignora `period_start` per il picco. Mitigazione: AI Export V1 non è ancora
taggata (ultimo tag `v1.0.1`), quindi nessun consumatore esterno — va deciso prima del tag.

---

## Tabella di verifica

| Voce vecchia | Stato 2026-08 | Stato verificato oggi | Evidenza | Azione |
|---|---|---|---|---|
| M2-A: guardia `if not __debug__: raise` in `main.py` | 🟡 raccomandata (declassata a igiene) | **MAI FATTO** | `grep -rn "PYTHONOPTIMIZE\|__debug__" backend/app/ Dockerfile` → 0 occorrenze | Task 1 (S, opzionale) |
| M2-B: 17 invarianti strutturali su `assert` | 🔵 informativo, opzione B opzionale | **ANCORA VALIDO** (mai fatto) | 51 assert totali (`grep -c "^\s*assert "` = 51), 34 `is not None`, 17 strutturali invariati: `catalog.py:219-221`, `asset_fx_registry.py:140-143`, `portfolio_broker_registry.py:146-148`, `datasets/catalog.py:867,973`, `analyses/catalog.py:241`, `temporal/policy.py:80-81`, `dependencies.py:111-112` | Task 2 (S, opzionale) |
| M3: `transitive_dependencies` morta (`registry.py:97`) | 🟡 morto reale, rimozione proposta | **FATTO** | 0 occorrenze in `backend/app` + `backend/test_scripts`; `registry.py` −18 righe nel diff `09cbb7e2..HEAD` | — |
| M3: `summary_position_count` morta (`portfolio_broker.py:877`) | 🟡 morto reale | **FATTO** | 0 occorrenze ovunque | — |
| M3: 5 falsi positivi dichiarati (`for_domain` ×2, `requested_day_count`, `db_lock`, `build_count`) | 🟢 conservare | **ANCORA VALIDO** | `datasets/spec.py:228`, `analyses/spec.py:247`, `temporal/plan.py:93`, `dependencies.py:351` (`db_lock`), `dependencies.py:363` (`build_count`) — tutti presenti con docstring-seam | — |
| M4.1: `AI_EXPORT_DEFAULT_DETAIL_LEVEL` orfano → `resolveDefaultDetailLevel` su 5 siti | ✅ applicato durante l'audit | **FATTO — regge, nessun nuovo sito** | helper a `catalog/shared.ts:47-48`; siti: `aiExportMemory.ts:138` (costante), `:149` (helper), `aiExportOptions.ts:184`, `AiExportOptionsPanel.svelte:103,124`; `grep "includes('standard')"` in `features/ai-export` → 0 risultati | — |
| M4.2: `isDatasetCatalogEntry` rimossa | ✅ rimossa durante l'audit | **FATTO** | 0 occorrenze in `frontend/src` + `frontend/e2e` | — |
| M4.3: `AI_EXPORT_DOMAIN_ORDER` inutilizzata | 🟢 rimozione/adozione | **FATTO** (rimossa) | 0 occorrenze in `frontend/src` + `frontend/e2e` | — |
| M4.4: 3 helper staleness superati (`aiExportOptions.ts:200-210`) | 🟢 rimozione sicura | **FATTO** | `aiExportStatsContextFingerprint`, `isAiExportStatsRequestCurrent`, `getMatchingAiExportStats`: 0 occorrenze; `aiExportOptions.ts` −23 righe nette nel diff | — |
| M5: complessità max 22, 17 funzioni C901, tutta in validatori | misura | **ANCORA VALIDO — riprodotto** | `ruff check backend/app/services/ai_export --select C901` → "Found 17 errors", max `__post_init__` 22 (`datasets/spec.py`), poi `_validate_status_invariants` 19, `_validate_success`/`build_indicator_table_payloads` 17 | Task 4 (opzionale: `max-complexity` 25) |
| M5: `TRY003` 515 rilievi — mettere in ignore se si adotta TRY | 🟢 1 riga config | **SUPERATO** | `pyproject.toml:72-80`: `select` non include `TRY` — la regola non è stata adottata, nulla da ignorare | — |
| M6: nessun deadlock su ciclo dipendenze / `section_order` solo presentazione | 🟢 smentite | **ANCORA VALIDO** | `_detect_cycles` a `registry.py:56`, chiamata da `__init__` (`:54`); self-dependency rifiutata in `spec.py:100-101`; `_DEFAULT_COMPONENT_REGISTRY = build_component_registry()` a `runtime_service.py:120` (import-time → avvio) | — |
| M7: copertura 93,47 % | misura | **NON RIPRODUCIBILE** | vietato eseguire test (run full in corso); nessuna fonte statica | — |
| M7: 56 file di test / 44 386 righe / 2,42:1 | misura | **NON RIPRODUCIBILE (perimetro)** | al commit `09cbb7e2`: name-match 22 file / 25 111 righe, content-match 23 file / 25 944 righe; oggi content-match 29 file / 28 771 righe → rapporto 28 771/18 225 = **1,58:1** su quel perimetro. Anche "59 file importano ai_export" (§M2) non si riproduce (23 all'epoca) | nota di metodo |
| M7: 4 spec E2E Playwright dedicate | misura | **ANCORA VALIDO** | `frontend/e2e/ai-export/`: `ai-export-catalog`, `ai-export-contract`, `ai-export-memory`, `ai-export-panel` `.spec.ts` (+ `helpers.ts`) | — |
| M8: endpoint `ai_export.py` 183 righe, 7 eccezioni su 6 status | 🟢 osservazione | **PARZIALE** (imprecisione origine) | file ancora 183 righe; `get_ai_export_catalog` `def` sync a `:91` ✓; ma i blocchi `except AiExport*` sono **6** su **5** status (403/404/409/422/503) — e lo erano anche a `09cbb7e2` (verificato con `git show`): il "sette su sei" era impreciso già allora | — |
| M8: budget token 20 000/60 000 nel frontend | 🟢 nessun intervento | **ANCORA VALIDO** | `aiExportOptions.ts:7-8` (`AI_EXPORT_TOKEN_WARNING_THRESHOLD = 20_000`, `..._LARGE_THRESHOLD = 60_000`); gate di copia in `AiExportMenu.svelte:191-192` | — |
| M8: nessun rate limit su `POST /ai-export/snapshot` | 🟢 segnalazione | **ANCORA VALIDO** | `ai_export.py:95-126`: nessun limiter/timeout applicativo | — |
| "~30 righe di rimozioni proposte" | piano | **FATTO** | backend `09cbb7e2..HEAD` su `ai_export/`: 22 file, +294/−452; frontend ai-export: 5 file, +23/−33; righe totali 25 748 → 25 608 | — |
| Catalogo: id/versione/dipendenze verificati all'avvio | affermazione | **ANCORA VALIDO** | import chain `api/v1/router.py:33` → `runtime_service.py:120` → `ComponentRegistry.__init__` → `_detect_cycles`; assert di modulo all'import | — |
| Nuovi componenti nell'ultimo mese | — | **NESSUNO** | assert di conteggio invariati a 67/67/67 (`catalog.py:219-221`); unico file nuovo: `_int_validation.py` (+69, banda S1-S3); commit ai_export post-audit: `be8394bb` (S1-S3), `603099d2`, `e2f488cf`, `c1755d19`, `6ab295d8` | — |

---

## Dettaglio

### M2 — guardia `__debug__`: mai applicata, e il report lo aveva previsto

Il rimedio A ("igiene, non correzione di un rischio attivo") **non è mai stato eseguito**:
nessuna occorrenza di `__debug__` o `PYTHONOPTIMIZE` in `backend/app/` né nel `Dockerfile`.
Anche l'opzione B (17 `assert` strutturali → `if ... raise`) è intatta: il censimento di oggi
riproduce **esattamente** i numeri del report — 51 `assert` totali, 34 `is not None`,
17 strutturali — con due spostamenti di riga: `catalog.py:221-223 → 219-221`,
`temporal/policy.py:78-79 → 80-81`, `dependencies.py:112-113 → 111-112`.
Gli assert restano difesa in profondità ridondante rispetto alla CI: la diagnosi del report
è ancora corretta e la severità 🔵 confermata.

### M4.1 — la fattorizzazione regge; nessun sito nato a mano

`resolveDefaultDetailLevel` vive in `catalog/shared.ts:47-48` accanto alla costante
(`:38`). Tutti e cinque i siti passano dall'astrazione; le righe sono scivolate di 1-5
posizioni per l'import aggiunto (`aiExportOptions.ts:189 → :184`, pannello `:102/:123 →
:103/:124`). Verifica anti-regressione esplicita: `grep "includes('standard')"` su tutto
`features/ai-export` → **zero** fallback manuali, incluse le ondate beta di fine agosto.

### Metriche riprodotte

```console
$ ruff check backend/app/services/ai_export --select C901
Found 17 errors                      # max: __post_init__ 22 (datasets/spec.py)

$ find backend/app/services/ai_export -name "*.py" | xargs wc -l | tail -1
   18225 total                       # audit: 18 355 (riprodotto esatto al commit 09cbb7e2)

$ find frontend/src/lib/features/ai-export -type f \( -name "*.ts" -o -name "*.svelte" \) | xargs wc -l | tail -1
    7383 total                       # audit: 7 393
```

Conteggi catalogo (invariati, assert al loro posto): 67/67/67 componenti
(`components/catalog.py:219-221`), 40 dataset / 8 pubblici (`datasets/catalog.py:43-44`),
11 analisi pubbliche (`analyses/catalog.py:26-27`). Il commit `66a6d351` "analysis count
to 17" è **pre-audit** (03/08): il catalogo V3 focalizzato (`54a15b42`, 04/08) lo riportò
a 11 prima dell'audit — nessuna contraddizione.

### Drawdown full_history (working tree 02/09) — coerenza verificata

- **Componente** (`drawdown_context.py`): docstring aggiornato (`:14-18`), loader
  full-history (`:307-336`): ASSET → `Date.min`, PORTFOLIO/BROKER →
  `resolve_date_sentinels(OpenDateRangeModel(start="min", …))` con fallback
  `min(inception, period_start)`. Import reali e verificati: `resolve_date_sentinels`
  (`date_sentinel.py:20`), `OpenDateRangeModel` (`schemas/common.py:493`),
  `Date` (`:43`, `from datetime import date as Date`).
- **Signal plugin** (`signal_plugins/drawdown.py`): `DrawdownParams.full_history`
  default `True`, i18n keys, warmup `full_history=params.full_history`; docstring dichiara
  "AI export paths always request the full-history behavior" — coerente col componente.
- **Test**: `test_ai_export_components_drawdown_context.py` +69 righe con fake di
  `resolve_date_sentinels` e casi E1 (inception < period_start, residuo senza transazioni).
- **CHANGELOG**: riga 131 documenta il cambio per l'utente.
- **⚠️ Contratto componenti**: i 4 spec drawdown restano `version=1`
  (`drawdown_context.py:553,562,572,581`) e `period_behavior=WINDOWED`
  (`:557,567,576,585`), dove WINDOWED è definito "spans the inclusive
  [period.start, snapshot_as_of] range" (`types.py:62`) — ma il loader ora ignora
  `period_start` per il picco. Il docstring di `spec.py:60-62` assegna a
  `component_id`/`version` l'identità della *logica*: un cambio semantico senza bump è una
  deviazione dal contratto interno. **Mitigazione reale**: AI Export V1 non è ancora
  rilasciata (ultimo tag `v1.0.1`; il V1 esce con questa release), quindi nessun
  consumatore esterno può aver osservato la semantica vecchia — il bump è una decisione
  da prendere consapevolmente **prima del tag**, non un debito urgente.

---

## Task riesumati

1. **Guardia `if not __debug__: raise RuntimeError(...)` in `main.py`** — M2-A.
   Evidenza: assente oggi (`grep` → 0). 2 righe in avvio app. **S**. Priorità bassa (igiene).
2. **Convertire i 17 invarianti strutturali in `if ... raise` tipizzati** — M2-B.
   Evidenza: posizioni verificate nella tabella sopra (8 siti in 7 file).
   Coerente con `DatasetSpecError`/`ComponentSpecError` già usati ovunque. **S** (17 righe).
   Fare quando si tocca il catalogo.
3. **Decidere versione/metadati dei componenti drawdown prima del tag V1** — nuovo.
   Evidenza: `drawdown_context.py:553,562,572,581` (`version=1`) e `:557,567,576,585`
   (`WINDOWED`). Opzioni: bump a `version=2`, o nota esplicita che V1 nasce già
   full-history; riesaminare se `WINDOWED` descrive ancora il payload. **S**.
4. **`max-complexity` 10 → 25 in ruff** (K5/M5 del vecchio report) — archivierebbe i 17
   C901 tutti validatori senza perdere segnale. **S** (1 riga config). Opzionale.

## Nuovi rilievi

1. **🟡 Versione/metadato drawdown non aggiornati al cambio semantico** — vedi Dettaglio.
   Bloccante solo in senso procedurale: decidere prima del tag della release.
2. **🔵 Due metriche del vecchio report non riproducibili** ("56 file / 44 386 righe /
   2,42:1" e "59 file importano ai_export" contro i 23/25 944 misurabili al commit d'audit).
   Non cambia il giudizio (il rapporto resta il migliore del progetto anche sul perimetro
   conservativo: 1,58:1 vs 0,79:1), ma i numeri andavano documentati col perimetro.
3. **🔵 Imprecisione d'origine su M8**: gli `except` di dominio sono 6 su 5 status, non
   "sette su sei" — verificato anche al commit d'audit; il report andava emendato.

## Cross-reference

- Report origine: `../../phases/05_cleanAudit/13_ai_export.md`; commit audit `09cbb7e2`.
- Esecuzione S1–S3: commit `be8394bb chore(release2): code audit remediation — bands S1 to S3` (05/08).
- Ondate beta: `603099d2`, `e2f488cf`, `c1755d19` (27-28/08), `6ab295d8` (01/09).
- Cambio drawdown E1: working tree 02/09 su `components/drawdown_context.py`,
  `signal_plugins/drawdown.py`, `test_ai_export_components_drawdown_context.py`, `CHANGELOG.md:131`.
- Istruzioni AI Export lette prima della valutazione: `.github/instructions/ai-development.instructions.md`
  (conforme: nessuna modifica a docs fuori scope, nessun probe lanciato).

---

## Riepilogo finale

- Reperti azionabili del vecchio report: **tutti chiusi** (2 simboli morti, DRY orfano
  M4.1, type guard M4.2, costante M4.3, helper M4.4) — rimozioni confermate da grep a 0 occorrenze.
- Guardia `__debug__` / assert→raise: **mai fatti**, come da declassamento a igiene; ancora validi, task S.
- Fattorizzazione `resolveDefaultDetailLevel`: **regge**, zero fallback manuali rinati dopo un mese e due ondate beta.
- Metriche: C901 riprodotto identico (17 errori, max 22); righe 25 608 (−140); conteggi catalogo invariati (67/40/8/11);
  "56 file/44 386 righe/2,42:1" **non riproducibile** — perimetro mai documentato, oggi 29 file/28 771 righe (1,58:1).
- Registry verificato all'avvio: ancora vero (`runtime_service.py:120` → `_detect_cycles`); nessun nuovo componente.
- Drawdown full_history (02/09): coerente ovunque (docstring, test, CHANGELOG, plugin), **ma** `version=1` e
  `WINDOWED` non aggiornati — decidere prima del tag V1.
- Imprecisioni d'origine trovate: "7 eccezioni su 6 status" (reali: 6 su 5) e il perimetro test di M7.
- Nessun test eseguito, nessun server avviato, nessuna operazione git mutante: solo analisi statica.
