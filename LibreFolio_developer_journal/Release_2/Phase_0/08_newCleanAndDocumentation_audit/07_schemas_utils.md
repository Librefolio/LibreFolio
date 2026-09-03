# 07 — Schemi & Utility — verifica 2026-09-02

> Fonte: [report archiviato](../../phases/05_cleanAudit/07_schemas_utils.md) (audit 2026-08-07)
> Metodo: analisi statica read-only; nessun test eseguito, nessun server avviato.
> Tree verificato: branch `dev_release2` + modifiche beta non committate del 2026-09-02
> (incluse `schemas/provider.py` e `schemas/signals.py`, verificate in calce).

---

## Sintesi esecutiva

Esito misto, con una chiusura importante: **G3 (`merge_other_identifiers`) è FATTO** —
la semantica additiva è stata decisa e cablata nel merge asset il giorno dopo l'audit
(commit `571bcde0`, 2026-08-08). **G5 è FATTO** nella parte chirurgica (le due
`get_session_ttl*` rimosse in `be8394bb`).

Restano aperti i due reperti principali: **G1** (11 property orfane — tutte presenti,
zero chiamanti, e nel frattempo le costruzioni inline `Currency(code=…)` sono passate da
"almeno 8" a **190 siti in 50 file**: la bilancia decisionale ora pende verso la
rimozione delle property) e **G2** (9 classi Pydantic mai cablate — tutte presenti,
nessun `response_model` aggiunto; gli endpoint scoperti restano **17 su 110**).

Le modifiche beta del working tree su `provider.py` e `signals.py` **non introducono
nuovi rilievi**: entrambi i campi aggiunti (`error_details`, `full_history`) sono
cablati end-to-end, frontend incluso.

---

## Metriche riprodotte

| Metrica | Audit 2026-08 | Oggi | Comando |
|---|---:|---:|---|
| `schemas/` file | 22 | **22** | `ls backend/app/schemas/*.py \\| wc -l` |
| `schemas/` righe | 11 202 | **11 140** (−62: ondata `BaseModel`→`StrictModel`, −184 nette sui commit + working tree) | `wc -l backend/app/schemas/*.py \\| tail -1` |
| `utils/` file | 15 | **15** (10 top-level + 4 in `financial/` + `__init__.py`) | `find backend/app/utils -name "*.py" -not -path "*__pycache__*" \\| wc -l` |
| `utils/` righe | 2 116 | **2 141** (+25) | `find … -exec wc -l {} + \\| tail -1` |
| Ruff (config progetto) | — | **0 rilievi** | `pipenv run ruff check backend/app/schemas/ backend/app/utils/` |
| Endpoint senza `response_model` | 17 / 97 | **17 / 110** | script python balance-aware sui decoratori router in `api/v1/*.py` |

Il "file con più rilievi ruff" dell'audit (transactions 8, signals 7, prices 6, …) non è
riproducibile alla stessa selezione di regole; con la config di progetto attuale il
conteggio è 0 ovunque.

---

## Tabella di verifica

| Voce vecchia | Stato 2026-08 | Stato verificato oggi | Evidenza | Azione |
|---|---|---|---|---|
| G1 — 11 property `*_cur`/conteggi orfane | 🟡 aperto | **ANCORA VALIDO** (aggravato) | Tutte presenti: `prices.py:168,173,178,183` (close/open/high/low_cur), `:280` (value_cur); `common.py:290` (to_dict), `:409` (actual_rate_date_str), `:718` (failed_count); `brokers.py:196,201`; `fx.py:168` (conversion_date_str). `grep "\.<prop>"` su backend/app + frontend/src → **0 chiamanti** per ciascuna. Inline `Currency(code=` oggi: **190 siti / 50 file** (`grep -rn "Currency(code=" backend/app/ \\| wc -l`) | Task T1 |
| G2 — 9 classi Pydantic mai referenziate | 🟡 aperto | **ANCORA VALIDO** | Tutte e 9 presenti e non referenziate: `auth.py:34`, `auth.py:116`, `fx.py:495`, `portfolio.py:71,79,273,282`, `prices.py:378`, `wac.py:24`. Nessun `response_model=` le cita (`grep` su `api/v1/`). Endpoint senza `response_model` ancora 17 | Task T2 |
| G3 — `merge_other_identifiers` mai applicata | 🟡 aperto | **FATTO** | Cablata in `services/asset_source.py:4475` dentro `merge_assets` (:4382), import a :130. Commit `571bcde0` (2026-08-08): "an asset recognised under a second name is reused and its import keys folded in rather than duplicated". Coperta via `test_asset_merge.py` (integrazione) | nessuna |
| G4 — `cache_utils` senza interfaccia | 🟢 aperto | **ANCORA VALIDO** | `clear_cache:136`, `clear_all_caches:145`, `list_caches:185` (era :120/:129/:169); zero chiamanti di produzione (`grep` su backend/app escluso il modulo); nessun endpoint admin cache in `api/v1/`. Solo test (`test_cache_utils.py`) | Task T3 |
| G5 — `get_session_ttl*` assorbite | 🟢 aperto | **FATTO** (parziale) | `settings_service.py` non contiene più `get_session_ttl`/`get_session_ttl_sync` (`grep` → 0 hit; file 242→221 righe); la viva è `global_settings_service.py:75` `get_session_ttl_hours`, usata da `api/v1/auth.py:117`. Rimozione in `be8394bb`. **Consolidamento dei due servizi MAI FATTO** (221+102 righe) | Task T4 |
| G6 — `get_version_info` solo test | 🟢 aperto | **ANCORA VALIDO** | `utils/version.py:60` (era :56); chiamanti: solo `test_version.py` e il runner `scripts/test_runner/_backend_utils.py:178`. La versione esposta all'utente passa da `get_git_version` (`api/v1/system.py:20`, `main.py:223`) | Task T5 |
| Int.1 — decidere semantica additiva import | raccomandato | **FATTO** | decisa: additiva, applicata nel merge endpoint (G3) | nessuna |
| Int.2 — cablare `*Response` + `api sync` | raccomandato | **MAI FATTO** | vedi G2 | Task T2 |
| Int.3 — rimuovere ttl assorbite | raccomandato | **FATTO** | vedi G5 | nessuna |
| Int.4 — decidere sulle 11 property | raccomandato | **MAI FATTO** | vedi G1 | Task T1 |
| Int.5 — endpoint admin cache o rimozione | raccomandato | **MAI FATTO** | vedi G4 | Task T3 |
| Int.6 — valutare `get_version_info` per 1.1.0 | raccomandato | **MAI FATTO** | nessun endpoint la usa | Task T5 |
| Int.7 — consolidare i due settings service | raccomandato | **MAI FATTO** | entrambi presenti | Task T4 |

---

## Dettaglio reperti ancora aperti / regrediti

### G1 — 11 property orfane: ANCORA VALIDO, decisione cambiata di segno

Verifica puntuale (righe odierne):

```text
backend/app/schemas/prices.py:168   def close_cur(self) -> Currency:
backend/app/schemas/prices.py:173   def open_cur(self) -> Optional[Currency]:
backend/app/schemas/prices.py:178   def high_cur(self) -> Optional[Currency]:
backend/app/schemas/prices.py:183   def low_cur(self) -> Optional[Currency]:
backend/app/schemas/prices.py:280   def value_cur(self) -> Currency:
backend/app/schemas/common.py:290   def to_dict(self) -> dict:            # Currency.to_dict
backend/app/schemas/common.py:409   def actual_rate_date_str(self) -> str:
backend/app/schemas/common.py:718   def failed_count(self) -> int:
backend/app/schemas/brokers.py:196  def total_cash_positions(self) -> int:
backend/app/schemas/brokers.py:201  def total_asset_positions(self) -> int:
backend/app/schemas/fx.py:168       def conversion_date_str(self) -> str:
```

Nessuna ha chiamanti di produzione (ciclo `grep "\.<nome>"` su `backend/app/` +
`frontend/src/` → vuoto per tutte). Sono tenute in vita dai propri test
(`test_schemas/test_schema_computed_fields.py`, 32 riferimenti; `test_common_schemas.py:349`
per `to_dict`).

**Dato nuovo che ribalta il rapporto costo/beneficio**: le costruzioni inline
`Currency(code=…)` oggi sono **190 in 50 file** (l'audit ne citava 8:
`schemas/transactions.py:473,483`; `broker_service.py:386,426,429,439`;
`broker_fineco.py:357` — tutte confermate, più `transaction_service.py:1177` e decine
di nuove nei provider BRIM e in ai_export). La costruzione esplicita è diventata **lo
stile de facto del progetto**: adottare le 5 property `*_cur` non è più realistico.
Raccomandazione aggiornata: **rimuovere** le property puramente sintattiche
(`*_cur`, `*_date_str`, `to_dict`) **con i loro test**, e valutare singolarmente solo
`failed_count`, `total_cash_positions`, `total_asset_positions` (incapsulano una regola).

### G2 — 9 classi mai cablate: ANCORA VALIDO

| Classe | Audit | Oggi |
|---|---|---|
| `AuthPasswordResetRequest` | auth.py:34 | `auth.py:34` — nessun endpoint reset password (`grep` su `api/v1/auth.py` → 0 hit): schema in attesa di feature |
| `AuthErrorResponse` | auth.py:116 | `auth.py:116` |
| `FXPairsListResponse` | fx.py:503 | `fx.py:495` — **aggravante**: l'endpoint `GET /currencies/pairs` citato nel docstring **non esiste**; anche `FXPairItem` è orfano |
| `PortfolioSummaryQuery` | portfolio.py:81 | `portfolio.py:71` |
| `PortfolioHistoryQuery` | portfolio.py:91 | `portfolio.py:79` |
| `AllocationHistoryQuery` | portfolio.py:299 | `portfolio.py:273` |
| `AllocationHistoryResponse` | portfolio.py:310 | `portfolio.py:282` |
| `FAEventDeleteResult` | prices.py:401 | `prices.py:378` |
| `WACConversionInfo` | wac.py:24 | `wac.py:24` — importata solo come re-export morto: `schemas/transactions.py:37` con `# noqa: E402, F401` |

Endpoint senza `response_model`: **17 su 110** (era 17/97): i 13 endpoint aggiunti dalle
ondate beta sono tutti cablati, i 17 scoperti sono gli stessi. Il rimedio dell'audit
(cablare + `./dev.py api sync`) è intatto e ancora il più redditizio del report.

### G3 — `merge_other_identifiers`: FATTO

`utils/identifier_utils.py:51` (riga invariata). La funzione è ora chiamata da
`services/asset_source.py:4475` dentro `merge_assets` (:4382), con la semantica
esatta del docstring: `target.identifier_other` + `[source.identifier_other, *demoted]`,
deduplicata, existing-first. Il requisito è stato deciso: **additivo**, ma applicato nel
flusso di **merge esplicito** (endpoint nato dal piano asset-identity del 2026-08-08),
non come merge automatico a import. Il wizard oggi intercetta i duplicati
(`brim_provider.py:1184-1250` legge `identifier_other` per il matching) e offre il
merge. Comportamento coerente con il requisito; reperto chiuso.

### G4 — `cache_utils`: ANCORA VALIDO (con un fix intermedio)

Le tre funzioni restano senza interfaccia. Nota positiva: durante il beta fixing
`NamedCache.clear()` (`cache_utils.py:65-82`) è stato corretto per un bug reale di
theine 2.0.0 (il W-TinyLFU rifiutava ogni `set()` dopo un clear a cache piena) — il
modulo è mantenuto, solo mai esposto.

### G5/G6 — vedi tabella

G5: parte chirurgica FATTA in `be8394bb`; consolidamento dei due servizi (221+102 righe)
mai pianificato. G6: immutato.

---

## Modifiche beta del working tree (02/09) — verifica nuovi rilievi

| File | Diff | Esito |
|---|---|---|
| `schemas/provider.py` | +5/−1: nuovo campo `BaseProbeOperationResult.error_details` (:360) + docstring di `error` | **NESSUN RILIEVO**: popolato in `services/asset_source.py:1959,1998,2027` via `_json_safe_details`; consumato dal frontend `resolveProviderError.ts:41` (file nuovo); `generated.ts` già sincronizzato (:5041,5087,5133,11020+) → `api sync` eseguito |
| `schemas/signals.py` | +6: nuovo campo `SignalWarmupRequirement.full_history` (:377) | **NESSUN RILIEVO**: letto in `signal_service.py:273-274`, propagato in `:316`, consumato in `asset_source.py:2200`; parametro plugin corrispondente in `signal_plugins/drawdown.py:46` usato a `:115` |

Nessun campo morto, nessuna duplicazione introdotta dalle modifiche beta in scope.

---

## Task riesumati

| # | Task | Evidenza | Stima |
|---|---|---|---|
| T1 | **Rimuovere** le 11 property orfane + test dedicati (decisione aggiornata: l'adozione non è più economica — 190 siti inline). Eccezione da valutare: `failed_count`, `total_cash_positions`, `total_asset_positions` | G1 sopra | **S** |
| T2 | Cablare `AllocationHistoryResponse`, `FXPairsListResponse`, `AuthErrorResponse` (se l'endpoint torna) come `response_model` + `./dev.py api sync`; rimuovere `FXPairItem`/`FXPairsListResponse` se l'endpoint `/currencies/pairs` non tornerà; decidere `AuthPasswordResetRequest` (feature o rimozione); rimuovere il re-export morto di `WACConversionInfo` (`transactions.py:37`) | G2 sopra | **M** |
| T3 | Decidere `cache_utils`: endpoint admin `POST /admin/cache/clear` + `GET /admin/cache` (valore operativo reale: oggi l'unica invalidazione è il riavvio) oppure rimozione delle 3 funzioni | cache_utils.py:136,145,185 | **M** |
| T4 | Consolidamento `settings_service` (221 righe) vs `global_settings_service` (102): un solo punto d'ingresso per le impostazioni | G5 | **L** |
| T5 | Decidere `get_version_info`: esporla in un endpoint `/version` arricchito o rimuoverla tenendo `get_git_version` | version.py:60 | **S** |

---

## Nuovi rilievi

- **N1 — `FXPairItem`/`FXPairsListResponse` doppiamente orfani**: il docstring cita
  `GET /currencies/pairs` ma l'endpoint non esiste (`grep "@router_currencies.get" fx.py`
  → solo `/signals`). O l'endpoint manca, o lo schema è residuo: da risolvere in T2.
- **N2 — Re-export morto**: `schemas/transactions.py:37` importa `WACConversionInfo` con
  `# noqa: E402, F401` e nessun consumatore lo importa da lì — rumore da una riga.
- **N3 — Decisione G1 da registrare**: qualunque strada si scelga (rimozione
  raccomandata), va scritta nelle istruzioni `backend-schemas` per fermare la
  ricrescita di property di comodo non adottate.

---

## Cross-reference

- Report [06](06_db_models.md): F1 (stesso pattern DRY orfano su `is_chain`/
  `providers_used`); F6 per lo stato Alembic.
- Report 01 dell'audit originale: i 17 endpoint senza `response_model` — riprodotti
  oggi a 17/110 (script balance-aware, vedi 06 § Cross-reference).
- Commit chiave: `be8394bb` (2026-08-05, S1–S3: G5 chirurgico),
  `571bcde0` (2026-08-08: G3 FATTO, asset identity + merge endpoint).
- Working tree beta (02/09): `provider.py`, `signals.py` — verificati, nessun rilievo.
