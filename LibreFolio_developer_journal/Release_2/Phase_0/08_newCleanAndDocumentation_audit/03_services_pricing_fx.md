# 03 — Pricing & FX — verifica 2026-09-02

> Fonte: [report archiviato](../../phases/05_cleanAudit/03_services_pricing_fx.md) (audit 2026-08-05/07)
> Metodo: analisi statica read-only; nessun test eseguito (run full seriale in corso sul DB condiviso).
> Baseline di confronto: commit `09cbb7e2` (pre-audit); S1–S3 = `be8394bb`; il working tree
> del 02/09 (resolver errori provider localizzati, drawdown full_history) è parte della realtà verificata.

---

## Sintesi esecutiva

Il sottosistema pricing/FX è quello che ha **incassato meno** dalla bonifica: dei 7
interventi raccomandati, solo il n. 7 (log nei `try/except/pass`) è stato completato —
in S1–S3. Tutti i reperti strutturali (C1–C5) sono **ancora validi e fermi**, mentre il
file centrale è **cresciuto**: `asset_source.py` da 4 800 a **5 162 righe** (+362, +7,5 %),
con le complessità di punta aumentate (`bulk_refresh_prices` 59 → **62**, `get_prices_bulk`
46 → **47**) e una nuova funzione sopra soglia (`merge_assets`, 22) arrivata con il rework
dell'import wizard (`571bcde0`). La concentrazione di candidati N+1 è immutata: la mia
riproduzione euristica trova in `asset_source.py` 14 loop con DB nel corpo su 25 totali
backend (**56 %**; 35 query-site su 49, **71 %**) — l'audit misurava 26/38 (68 %) con un
rilevatore diverso, ma la conclusione è la stessa.

Le ondate beta hanno lavorato bene su questo file: il resolver errori localizzato
(`_json_safe_details`, `error_details`) è cablato end-to-end e ha corretto in corsa un
bug minore (`ProbeMetadataResult` perdeva `error_code`); il canale `full_history` per il
drawdown è coerente attraverso quattro file. Un solo rilievo DRY minore (N-03-A).

---

## Tabella di verifica

| Voce vecchia | Stato 2026-08 | Stato verificato oggi | Evidenza (file:riga attuale) | Azione |
|---|---|---|---|---|
| C1 — 26 candidati N+1, 68 % del backend | 🟡 aperto | **ANCORA VALIDO** | Riscansione (script indent-based, vedi sotto): 14 loop / 35 site nel file; blocco principale: `patch_assets_bulk`, loop `asset_source.py:4191` con **7 query per elemento** (`:4195,4252,4255,4265,4276,4283,4284`) + `flush` `:4350` | Task 1, 2 |
| C2 — `ensure_rates_multi_source` mai usato | 🟡 aperto | **ANCORA VALIDO** | `fx.py:389` (C901=30); zero chiamanti produzione, solo `test_fx_rates_persistence.py` (10 call site); nota multi-base ancora a `fx.py:141-150` senza il commento "intentionally unwired" raccomandato | Task 4 |
| C3 — `AssetMetadataService` solo test | 🟡 aperto | **ANCORA VALIDO** | classe a `asset_source.py:4592`; metodi `compute_metadata_diff` `:4600`, `apply_partial_update` `:4646`, `merge_provider_metadata` `:4699`; unici chiamanti in `test_asset_metadata.py` | Task 3 |
| C4 — `get_asset_provider` solo test | 🟢 aperto | **ANCORA VALIDO** | `asset_source.py:1336`; chiamanti solo in `test_asset_source.py:395,683,1701` | Task 5 |
| C5 — `bulk_refresh_prices` (59) / `get_prices_bulk` (46) | 🟢 aperto | **ANCORA VALIDO, peggiorato** | `bulk_refresh_prices` `:2697`, C901=**62**, fasi ancora inline (`:2729,2860,2995`); `get_prices_bulk` `:2161`, C901=**47** | Task 6 |
| C6 — 4 `try/except/pass` silenziosi | 🟢 aperto | **FATTO** | `ruff check app/ --select S110`: 0 nei file di scope; fix S1–S3 documentato in `15_esecuzione_s1_s3.md` r. 99-101; `yahoo_finance.py` ora logga (es. `:147,449,471`) | — |
| Dimensione `asset_source.py` (4 800) | 🟡 nota | **PEGGIORATO: 5 162** | `wc -l` riprodotto sotto; `git diff --stat 09cbb7e2..HEAD`: 732 righe toccate | Task 8 (scissione) |
| Routing FX produzione via `sync_pairs_bulk` | conferma | **CONFERMATO** | `api/v1/fx.py:205`, `scheduler/jobs.py:148` (audit citava `:203` e `:143`) | — |

### Metriche riprodotte

```bash
wc -l backend/app/services/asset_source.py backend/app/services/fx.py
# 5162 / 1633   (audit: 4800 / 1643)
git show 09cbb7e2:backend/app/services/asset_source.py | wc -l   # 4800 — baseline audit confermata

cd backend && pipenv run ruff check app/services/asset_source.py app/services/fx.py --select C901 --output-format concise
# asset_source.py: 16 funzioni sopra soglia · fx.py: 5
#   bulk_refresh_prices 62 (:2697) · get_prices_bulk 47 (:2161) · merge_assets 22 (:4382)
#   sync_pairs_bulk 54 (fx.py:768) · ensure_rates_multi_source 30 (fx.py:389) · convert_bulk 23 (fx.py:1215)
```

> **Discrepanza di baseline**: l'audit dichiarava 8 funzioni sopra soglia per
> `asset_source.py`, ma la stessa misura **al commit dell'audit** (`09cbb7e2`, file da
> 4 800 righe esatti) ne dà già **15** — sottostima originaria, non una crescita 8 → 16.
> La crescita reale post-audit è 15 → 16 (`merge_assets`, nuovo). Stessa cautela per il
> totale "62 rilievi ruff": non riproducibile con i selettori documentati; con le 4
> famiglie del report 02 oggi misuro 28 rilievi su `asset_source.py` e 9 su `fx.py`.

Riproduzione N+1 (euristica indent-based su `await session.{execute,scalar,scalars,get,delete,flush,commit}` dentro `for/while`):

```
asset_source.py: 14 loop, 35 site — loop@944 (3, bulk_assign_providers), @1197 (2,
refresh_assets_from_provider), @1394 (4, bulk_upsert_prices), @1634 (2), @1674 (1),
@2260 (1, get_prices_bulk), @3554 (1), @3636 (1, query_events_bulk), @3769 (4,
delete_events_bulk), @3840 (2, create_assets_bulk), @4092 (3, delete_assets_bulk),
@4191 (8, patch_assets_bulk), @4489 (1, merge_assets), @4507 (2, merge_assets)
backend/app totale: 25 loop, 49 site → asset_source.py = 56 % loop, 71 % site
```

---

## Dettaglio reperti ancora aperti / regrediti

### C1 — il caso scolastico è intatto

> ✅ **Risolto 02/09** (P0-5): preload unico `IN (...)` + conteggi aggregati `GROUP BY` +
> lookup in memoria — 20 patch senza valuta → **1 SELECT**, 3 con valuta → **4** (pinnato
> in test). Nella stessa tornata fixato anche il wedge FX quadratico scoperto nel collaudo
> E1 (dedup O(1) + tetto 10). I due N+1 verbatim secondari (`portfolio_api.py:49`,
> `api/v1/fx.py`) sono stati fixati il 03/09 (Lane B). Gli **altri** loop di questa
> riproduzione (`bulk_upsert_prices`, `delete_events_bulk`, `bulk_assign_providers`, …)
> restano da lavorare → Task 2 sotto.

Il bulk patch (`patch_assets_bulk`, `asset_source.py:4169`) esegue ancora il
`select(Asset).where(Asset.id == patch.asset_id)` dentro il ciclo (`:4191-4195`), seguito
da altre 6 query per elemento (conteggi prezzi `:4252`, eventi manuali `:4255`, eventi
provider `:4265`, transazioni collegate `:4276`, min/max data `:4283-4284`) più un
`flush` per elemento (`:4350`). Un batch da 50 asset genera ancora ~350 round-trip. Il
rimedio indicato (preload `WHERE id IN (...)` + dizionario) non è stato applicato.

Gli altri blocchi citati dall'audit, mappati sulle righe attuali: vecchio loop `1354` →
oggi `bulk_upsert_prices` loop `:1394` (3-4 query); vecchio `3635` → `delete_events_bulk`
loop `:3769` (3 query + delete); vecchio `918` → `bulk_assign_providers` loop `:944`
(3 query). Nessuno risolto.

### C2 — invariato, e la raccomandazione a costo zero non è stata colta

> ✅ **Risolto 03/09** (P1-15, Lane B): il commento `# Intentionally unwired: no
> production caller invokes this function …` ora marca `fx.py:389`. Nella stessa corsa la
> decisione `get_provider`/`list_plugin_classes` (report 04 T3): **entrambi rimossi**
> dal registry, test esterni migrati a `get_provider_instance`.

`ensure_rates_multi_source` (`fx.py:389`) resta codice per il futuro multi-base: nessun
chiamante produzione, 10 call site di test. L'opzione 1 dell'audit ("una riga di commento
`# Intentionally unwired`") non è stata applicata: la nota architetturale esiste
(`fx.py:141-150`) ma non marchia la funzione, quindi il prossimo audit la ripescherà di
nuovo — com'è puntualmente successo.

### C3 — invariato

`AssetMetadataService` (`:4592`) resta un DRY orfano: tre metodi testati, diff
campo-per-campo mai cablato nel percorso di produzione. Il tipo di ritorno
`list[FAMetadataChangeDetail]` continua a suggerire un'intenzione UI mai realizzata.

### C4 — invariato

> ✅ **Deciso 03/09** (P1-4/P1-17): `get_asset_provider` è **tenuto** — riclassificato da
> orfano ad API pubblica del manager (usata da 3 test). Nessuna rimozione né adozione
> forzata nei chiamanti inline.

`get_asset_provider` (`:1336`) resta duplicato degli accessi inline; i chiamanti di
produzione continuano a non usarlo.

### C5 — peggiorato

Le 3 fasi di `bulk_refresh_prices` (`:2729` PREPARE, `:2860` FETCH, `:2995` PERSIST)
restano inline; la complessità è salita a 62. I sotto-metodi `_fetch_single` (`:2864`,
22) e `_persist_single` (`:3043`, 21) **esistevano già all'audit** (introdotti con la
pipeline, commit `808323fe`) — l'estrazione parziale c'è stata a suo tempo, ma il corpo
principale no.

---

## Task riesumati

| # | Task (evidenza) | Stima |
|---|---|---|
| 1 | **C1-primo**: eliminare l'N+1 del bulk patch (`asset_source.py:4191-4284`): preload `Asset` con `IN (...)`, conteggi aggregati con `GROUP BY`, dizionari di lookup. Miglior rapporto valore/costo dell'audit, confermato | **S/M** |
| 2 | **C1-altri**: passata sui restanti loop per N atteso — prima i bulk utente (`bulk_upsert_prices :1394`, `delete_events_bulk :3769`, `bulk_assign_providers :944`, `create/delete_assets_bulk :3840/:4092`), poi gli interni | **M** |
| 3 | **C3**: decidere `AssetMetadataService` (`:4592`): cablare `compute_metadata_diff` nel percorso update per l'audit trail promesso dal docstring, oppure rimuovere classe + test | **S** |
| 4 | **C2**: aggiungere a `fx.py:389` il commento `# Intentionally unwired: see ARCHITECTURAL NOTE multi-base` (riga 141) | **S** (una riga) |
| 5 | **C4**: far usare `get_asset_provider` (`:1336`) ai chiamanti inline, o rimuoverlo | **S** |
| 6 | **C5**: estrarre le 3 fasi di `bulk_refresh_prices` (`:2697`) in metodi privati; la struttura è già dichiarata nel docstring | **M** |
| 7 | **N-03-A**: valutare la convergenza dei tre helper "JSON-safe" (vedi sotto) | **S** |
| 8 | **Dimensione**: `asset_source.py` a 5 162 righe — pianificare la scissione (provider management / prezzi / metadata / bulk ops) come intervento dedicato, più urgente di un mese fa | **L** |

> **Stato 03/09 (esecuzione P0/P1)**:
> - **T1** ✅ (P0-5, 02/09): N+1 del bulk patch eliminato (preload + `GROUP BY`; 20 patch
>   senza valuta → 1 SELECT, pinnato in test).
> - **T4** ✅ (P1-15, 03/09): commento `# Intentionally unwired` applicato a `fx.py:389`.
> - **T7** ⚠️ **Parziale** (P1-17, 03/09): il giro «igiene minore» è chiuso nel 99, ma la
>   **convergenza dei 3 helper JSON-safe non è stata applicata** — verificato sul codice:
>   `_json_safe_details` (`asset_source.py:239`) e le due `_ensure_json_safe`
>   (`schemas/signals.py:48`, `schemas/ai_export_runtime.py:37`) restano separate.
>   Interpretazione: valutata e lasciata com'è; se non è così, il debito DRY è ancora aperto.
> - T3 (C3, `AssetMetadataService`) resta **aperto**: decisione di prodotto P2-3.
> - **T5** ✅ (P1-4/P1-17, 03/09): decisione presa — `get_asset_provider` **tenuto** (è API
>   pubblica del manager, usata da 3 test; non più «da adottare o rimuovere»).

---

## Nuovi rilievi

### N-03-A — Terza variante di helper "JSON-safe" (🟢, DRY)

> ⚠️ **Parziale 03/09** (P1-17): il giro d'igiene è marcato fatto nel 99, ma i tre helper
> **restano non convergati** (verificato: `_json_safe_details` in `asset_source.py:239`,
> `_ensure_json_safe` in `schemas/signals.py:48` e `schemas/ai_export_runtime.py:37`).
> Nessuna modifica applicata a questo rilievo specifico.

La tornata beta (resolver errori provider localizzati, working tree 02/09) ha introdotto
`_json_safe_details` (`asset_source.py:239-255`), cablata correttamente nei tre probe
(`:1959,1998,2027`) e consumata dal frontend (`resolveProviderError.ts`, i18n `TIMEOUT`
presente). Esistono però già due `_ensure_json_safe` quasi identiche:
`schemas/signals.py:48` e `schemas/ai_export_runtime.py:37` (duplicazione **preesistente**).
La nuova ha semantica diversa (sanitizer che stringifica invece di validatore che
solleva), quindi non è una copia — ma tre helper per lo stesso problema in tre moduli
chiedono una decisione DRY, non urgente.

### N-03-B — `merge_assets` porta nuovi loop con DB per-riga (🟢, bounded)

Nuovo dal rework import (`571bcde0`, C901=22, `:4382`): loop con `await session.delete`
per riga prezzi (`:4491`) e `update` per evento (`:4511`). N è limitato (righe di **un**
asset sorgente, non una lista utente) e l'operazione è singola, non un endpoint bulk:
osservazione da tenere d'occhio, non un blocco. Da includere nella passata del Task 2.

### Note positive dalle ondate beta (ambito pricing/FX)

- **Bug minore corretto in corsa**: il ramo `except` di `ProbeMetadataResult` non
  propagava `error_code`; ora sì (diff working tree `asset_source.py:2016-2027`).
- **E1 — drawdown full_history**: catena coerente in quattro file —
  `signal_plugins/drawdown.py` (`DrawdownParams.full_history` default True, `:104-115`),
  `schemas/signals.py:378` (`SignalWarmupRequirement.full_history`),
  `signal_service.py:126,273,316` (`requires_full_history` nel piano),
  `asset_source.py:2196-2206` (warm-up da `date.min`). Il `min()` ridondante a `:2205-2208`
  nel ramo full-history è volutamente difensivo e commentato.
- **AI export drawdown** (`drawdown_context.py:307-336`): ASSET scope da `Date.min`,
  PORTFOLIO scope da prima transazione accessibile via `resolve_date_sentinels`
  (`date_sentinel.py:20`) — riuso di un helper esistente, nessuna duplicazione introdotta;
  chiavi i18n del parametro presenti (`en.json:1131`, `it.json:1131`, tooltip `:2347`).
- Nessun codice morto nato da questi refactor rilevato nei file di ambito.

---

## Cross-reference

- Report 02 (servizi core) per B1/B2 — `base_currency` compare anche qui via
  `portfolio_engine.py:1967` — e per la regressione S110 in `cache_utils.py:82`.
- Report 04 (providers) dell'audit originale per i due `except/pass` di
  `yahoo_finance.py` (ora FATTO, verificato qui).
- Esecuzione S1–S3: [15_esecuzione_s1_s3.md](../../phases/05_cleanAudit/15_esecuzione_s1_s3.md) (r. 99-101: fix S110).
- Commit rilevanti post-audit su questo ambito: `be8394bb` (S1–S3), `571bcde0`
  (import wizard: `merge_assets`, asset identity), `0c319f14` (upsert ON CONFLICT).
