# 05 — Signal & Risk Analytics — verifica 2026-09-02

> Fonte: [report archiviato](../../phases/05_cleanAudit/05_signals_risk.md) (audit 2026-08-05/07, commit di riferimento `be8394bb`)
> Metodo: analisi statica read-only; nessun test eseguito (run full in corso, DB condiviso).
> Working tree con modifiche beta non committate del 02/09 incluso nella verifica
> (`signal_plugins/drawdown.py` full_history E1, `signal_service.py` requires_full_history,
> `schemas/signals.py` SignalWarmupRequirement.full_history, `schemas/provider.py` I3).
> Comando ruff usato per le riproduzioni (da `backend/`):
> `pipenv run ruff check --extend-select TRY,ARG,SIM,S,PIE,PERF,RUF,C901 --ignore TRY003`
> — riproduce **esattamente** tutti e 5 i conteggi per-file citati dall'audit
> (base.py 10, signal_service.py 8, obv.py 7, loader.py 7, schemas/signals.py 7).

---

## Sintesi esecutiva

Il sottosistema **conferma il titolo di area più pulita**, e l'unico orfano segnalato è
stato rimosso: **zero simboli inutilizzati oggi su 10 923 righe** (vulture
`--min-confidence 80` su signal+risk: 0 reperti; `unique_computation_count` eliminata in
S1–S3 con i test aggiornati esattamente come prescritto dall'audit). Il conteggio
strutturale è stabile: **22 signal plugin** e **9 analitiche di rischio**, identici.

La **beta drawdown full_history del 02/09** (working tree) è ben costruita: contratto a
plugin rispettato (registrazione, attributi obbligatori, `extra="forbid"`, retrocompatibilità
dello schema via default), propagazione completa fino al fetch path
(`asset_source.py:2200`), chiavi i18n presenti nelle 4 lingue, test dedicati (+161 righe),
CHANGELOG aggiornato. **Un'eccezione alla policy documentata**: `implementation_version`
resta `"1.0.0"` nonostante la guida prescriva di incrementarlo al cambio di comportamento
numerico (`signal_plugin_guide.md:586`) — e il default `full_history=True` cambia l'output
per richieste senza parametri espliciti.

Il debito sui validatori (E1) è **invariato per scelta** (`validate_status_matrix` ancora
32, ancora catena di `if`): il backlog 6.7 lo posticipa volutamente. Due inesattezze del
report originale emergono dalla riproduzione: la tabella delle complessità ometteva
funzioni più alte del suo #2 (`prepare_plan` 20 e `validate_definition` di
`signal_plugins/base.py` 21 esistevano già), e "sei/otto su dieci validatori" non torna
con la tabella stessa (7). La regola metodologica di E2 (esclusione ai_export) **non è
mai stata registrata** in alcuna skill o instruction — intervento 1 mai fatto, e la
stessa struttura a report separato si ripete in questa tornata (13_ai_export.md).

---

## Tabella di verifica

| Voce vecchia | Stato 2026-08 | Stato verificato oggi | Evidenza | Azione |
|---|---|---|---|---|
| Struttura: `signal_plugins/` 24 file / 4 786 righe; `risk/`+`risk_plugins/` 28 file / 6 117; `signal_service.py`, `schemas/signals.py`, `schemas/risk.py` | misura | **RIPRODOTTO / EVOLUTO** | Al commit d'audit (`git ls-tree be8394bb` + `git show`): 24/4 786 ✅ e 28/6 117 ✅. Oggi: signal_plugins 24 file / **4 806** righe (+20 = beta drawdown); risk+risk_plugins 28 file / **6 117** — identici al byte | — |
| "22 signal plugin e 9 analitiche di rischio" | misura | **ANCORA VALIDO** | `grep -rln "register_plugin(SignalPluginRegistry)" signal_plugins/` → 22; `grep "analytic_code = " risk_plugins/*.py` → 9 | — |
| "Un solo simbolo inutilizzato in 10 900 righe" | misura | **SUPERATO (in positivo)** | 4 786+6 117=10 903 ✅; l'unico orfano (E3) rimosso → oggi 0 simboli morti su 10 923 righe. `pipenv run vulture <perimetro> --min-confidence 80` → 0 reperti | — |
| Tabella complessità (10 funzioni) | misura | **RIPRODOTTA (tutte e 10), ma INCOMPLETA GIÀ ALLORA** | Oggi (`ruff --extend-select C901`): `validate_status_matrix` 32 (`schemas/signals.py:1069`, era :1058), `validate_definition` risk 17 (`risk/base.py:176`, identica), `validate_context` 15 (`schemas/risk.py:495`, era :519), `validate_episode_contract` 15 (`:972`, era :1035), `validate_dimensions` 15 (`risk/quant/models.py:36`, identica), `drawdown_episodes` 15 (`risk/metrics.py:259`, identica), `validate_coverage` 14 (`schemas/signals.py:770`, era :759), `validate_alignment` 13 (`schemas/risk.py:412`, era :434), `current_buy_and_hold_returns` 11 (`risk/metrics.py:496`, identica), `run_optimization` 11 (`risk/quant/optimization_engine.py:50`, identica). **Ma**: su snapshot `be8394bb` estratto con `git show`, `prepare_plan` era già 20 (`signal_service.py:155`) e `validate_definition` di `signal_plugins/base.py:285` già 21 — entrambe sopra il #2 della tabella (17) e assenti | Registrare il comando di scan nei prossimi audit |
| "Sei delle dieci… validate_*" / "Otto su dieci sono validatori" | testo | **ERRATO (internamente incoerente)** | La tabella stessa elenca 7 validatori + 3 funzioni di calcolo. Oggi: invariato (7+3) | Correzione storica |
| File con più rilievi: base.py 10, signal_service.py 8, obv.py 7, loader.py 7, schemas/signals.py 7 | misura | **ANCORA VALIDO (tutti identici)** | Set equivalente: 10 / 8 / 7 / 7 / 7 oggi | — |
| E1 — `validate_status_matrix` 32, matrice come catena di if | aperto | **ANCORA VALIDO / MAI FATTO** | Oggi a `schemas/signals.py:1069`, ancora 32, ancora if-chain (vista :1069-1120, blocchi OK/PARTIAL/UNAVAILABLE/FAILED). Backlog 6.7 posticipato per scelta ("solo quando diventeranno un ostacolo") | Task T4 sotto |
| E2 — falso positivo `resolve_ai_export_temporal_class` (uso reale in ai_export escluso) | registrato | **ANCORA VALIDO** | Definita a `signal_plugins/base.py:121`; chiamata di produzione invariata a `ai_export/components/technical_shared.py:943` (+ 8 usi test). Nella nuova tornata ai_export ha di nuovo report dedicato (`13_ai_export.md`): stessa struttura di esclusione → stessa trappola metodologica | — |
| E2 — intervento 1: registrare la regola sugli esclusi nella skill | raccomandato | **MAI FATTO** | `grep -rn "esclus" .github/skills/ .github/instructions/ .github/agents/` → nessuna occorrenza della regola "escludere dalla reportistica, non dalla raccolta dei riferimenti" | Task T1 sotto |
| E3 — `unique_computation_count` usata solo dai test | aperto | **FATTO** | Rimossa in `be8394bb` (S1–S3); `grep -rn "unique_computation_count" backend/ scripts/` → 0. I due test aggiornati **come prescritto**: `test_signal_service.py:342` e `test_signal_plugin_matrix.py:309` ora `assert len(plan.computations) == …` | — |
| E4 — nessun altro codice morto; il pattern a plugin si autopulisce | osservazione | **ANCORA VALIDO** | Vulture min-80 sul perimetro: 0. Le "false morte" a confidence 60 sono classi plugin raggiunte via registry e validatori Pydantic — conferma strutturale. Le aggiunte beta sono tutte consumate: `requires_full_history` → `asset_source.py:2200`; `full_history` → `signal_service.py:274,316` | — |
| E5 — `risk/scenario_catalog/loader.py` 7 rilievi; `validate_definition` (risk/base.py:176) 17 | aperto | **ANCORA VALIDO / MAI FATTO** | loader.py oggi 7 (identico); `validate_definition` ancora 17 a `risk/base.py:176`. Intervento 3 (TRY/SIM in loader/obv/mfi): obv.py 7, mfi.py 6 — invariati | Task T5 sotto |
| Intervento 2 (rimuovere o usare `unique_computation_count`) | raccomandato | **FATTO** | vedi E3 | — |
| Intervento 4 (matrice dichiarativa `validate_status_matrix`) | raccomandato | **MAI FATTO** | vedi E1 | Task T4 |
| Intervento 5 (stessa trasformazione per `schemas/risk.py`) | raccomandato | **MAI FATTO** | Validatori risk invariati (complessità identiche, righe spostate dal dedupe `e2f488cf`) | Task T4 |
| Nota finale: "va riverificato fra qualche release" | impegno | **QUESTA VERIFICA** | A un mese: pulizia mantenuta (0 morti, conteggi stabili); unica eccezione la policy di versioning (N1) | — |

---

## Dettaglio reperti ancora aperti / regrediti

### E1/E5 — debito congelato per scelta, nessuna regressione

Tutti i validatori citati hanno **esattamente** la complessità di un mese fa; le righe
spostate (`schemas/risk.py` −24/−63/−22; `schemas/signals.py` +11) riflettono il dedupe
di `e2f488cf` (28/08) e la beta del 02/09, non nuova complessità. Il rischio segnalato
dall'audit (matrice if non ispezionabile) è invariato, così come la sua priorità: bassa.

### La tabella delle complessità era un campione, non il top-10

Su snapshot `be8394bb` (estrazione `git show` + `ruff --extend-select C901`):
`prepare_plan` 20 (`signal_service.py:155`), `validate_definition` 21
(`signal_plugins/base.py:285`), `_execute_planned_signal` 16 (`signal_service.py:690`)
esistevano già e avrebbero occupato le posizioni 2-3. Oggi `prepare_plan` è salito a 21
(la beta aggiunge il ramo `if requirement.full_history` a `signal_service.py:273-274`).
Nessun impatto sui reperti (il massimo E1=32 era e resta corretto); va però letta così
la tabella originale.

---

## Verifica beta 02/09 — contratto signal del plugin drawdown

**Contratto rispettato.** Checklist contro `SignalPlugin.validate_definition`
(`signal_plugins/base.py:284-330`):

| Requisito | Stato | Evidenza |
|---|---|---|
| Registrazione | ✅ | `@register_plugin(SignalPluginRegistry)` invariato (`drawdown.py:56-57`) |
| Attributi obbligatori | ✅ | `signal_code="RISK_DRAWDOWN"`, `implementation_version`, `category`, `display_name_key`, `description_key`, `semantic_id`, `semantic_description`, `icon`, `params_model`, `input_requirements`, `output_specs` (aggregation_profile esplicito), `compatible_domains` — tutti presenti (`drawdown.py:60-99`) |
| `params_model` `extra="forbid"` | ✅ | `DrawdownParams` mantiene `ConfigDict(extra="forbid")` (`drawdown.py:44`) |
| Retrocompatibilità schema | ✅ | `SignalWarmupRequirement.full_history` default `False` (`schemas/signals.py:372-377`): tutti gli altri 21 plugin invariati |
| Propagazione plan → fetch | ✅ | `signal_service.py:129,195,273-274,316` → `SignalExecutionPlan.requires_full_history` → `asset_source.py:2200-2210` |
| i18n nuovo parametro | ✅ | `chartSettings.params.fullHistory` + `signals.tooltips.riskFullHistory` presenti e coerenti in **en/it/fr/es**; rendering generico via `charts/signals/schemaMapper.ts` (x-i18n-key) — nessun codice frontend per-parametro |
| Test | ✅ (statico) | `test_risk_signal_plugins.py` +92 righe (default True, opt-out, propagazione plan: `:362-378`); `test_ai_export_components_drawdown_context.py` +71 |
| Documentazione release | ✅ | `CHANGELOG.md:131` (comportamento pre/post documentato) |

**Eccezione — versioning**: `implementation_version = "1.0.0"` invariato
(`drawdown.py:61`). La guida prescrive "Increment `implementation_version` when
numerical behavior changes" (`mkdocs_src/docs/developer/architecture/patterns/signal_plugin_guide.md:586`).
Con default `full_history=True` l'output numerico cambia per richieste senza parametri
espliciti; il valore fluisce nei metadati dei risultati (`signal_service.py:585`
`algorithm_version=...implementation_version`) e negli snapshot AI Export → export
pre/post beta risultano entrambi "1.0.0" con semantica diversa. Mitigazioni: il
parametro è registrato in `normalized_params` e i segnali sono computati on-demand
(nessuna cache persistente nel path signal). Nessun precedente di bump nella storia dei
plugin (`git log -S 'implementation_version = "'` → solo commit di introduzione). 🟡 basso.

---

## Task riesumati (numerati, evidenza, stima S/M/L)

- **T1 (S)** — Registrare la regola E2 ("l'esclusione va applicata alla reportistica,
  non alla raccolta dei riferimenti") nella skill di audit/testing o nelle instructions.
  Evidenza: grep vuoto su `.github/skills|instructions|agents`; la trappola si è
  ripetuta identica in questa tornata (ai_export di nuovo a report separato).
- **T2 (S)** — Bump `implementation_version` di drawdown a `"1.1.0"` (policy
  `signal_plugin_guide.md:586`), oppure emendare la guida se il default-driven change
  è considerato coperto da `normalized_params`. Evidenza: `drawdown.py:61`.
- **T3 (S)** — Allineare la documentazione storica: tabella complessità del report 05
  era un campione (mancavano `prepare_plan` 20, `validate_definition` base 21).
- **T4 (M, posticipabile)** — Matrice dichiarativa per `validate_status_matrix`
  (`schemas/signals.py:1069`, 32) ed eventualmente validatori `schemas/risk.py`.
  Resta il trigger: aggiunta di un nuovo `SignalStatus`.
- **T5 (S)** — Ripulisti TRY/SIM in `loader.py` (7), `obv.py` (7), `mfi.py` (6):
  identici a un mese fa, mai schedulato.

---

## Nuovi rilievi

- **N1 🟡 basso** — Versioning drawdown non bumpato (dettaglio sopra): prima violazione
  della policy di `implementation_version` dall'introduzione dei plugin.
- **N2 🟢** — `prepare_plan` 20 → 21 per il ramo full_history (`signal_service.py:273-274`).
  Variazione trivia, segnalata perché la funzione è già la #2 del sottosistema e cresce
  ad ogni feature di warm-up: il prossimo ramo la porterà verso la soglia di E1.
- **N3 🟢 (positivo)** — La beta non ha introdotto debito morto: ogni simbolo nuovo
  (`full_history`, `requires_full_history`) ha un consumatore di produzione; i18n e test
  alineati; `schemas/signals.py` cresce di 6 righe senza nuovi rilievi ruff (7 = 7).

---

## Cross-reference

- [14 — Backlog](../../phases/05_cleanAudit/14_backlog_per_complessita.md): 6.7 (matrice dichiarativa) aperta e volutamente posticipata.
- [15 — Esecuzione S1–S3](../../phases/05_cleanAudit/15_esecuzione_s1_s3.md): rimozione `unique_computation_count` (riga 119 del report) verificata.
- Report gemelli di questa tornata: `04_providers.md` (fetch path `asset_source.py:2200`, regression S110 cross-area), `12_test_coverage.md` (guardia `params_schema` L2.1), `13_ai_export.md` (lato AI Export del drawdown full_history, `drawdown_context.py`).
- Consumatori del plan fuori perimetro verificati vivi: `api/v1/fx.py:593` (`max_history_points_before_visible`), `ai_export/components/technical_shared.py:656`.
