# 08 — Nuova tornata clean & documentation audit — Indice

> **Release 2 · Phase 0 · 08_newCleanAndDocumentation_audit**
> Data: 2026-09-02 · Branch: `dev_release2` · HEAD: `f4698da7` (2026-09-02 11:45)
> Worktree: **dirty (63 file)** — la tornata di consolidamento beta P2/P4/P5/P6 non
> committata fa parte della realtà verificata.
> Fonte verificata: [`../phases/05_cleanAudit/`](../../phases/05_cleanAudit/INDEX.md)
> (audit del 2026-08-07, 17 report + `mkdocsAudit/`).

---

## Cos'è questa tornata

Riverifica **integrale** dell'audit di un mese fa contro i sorgenti attuali. Per ogni
voce dei vecchi report: **stato reale oggi** (fatto / parziale / mai fatto / superato /
ancora valido) con evidenza `file:riga` verificata sul codice e sui docs correnti —
mai dedotta dal vecchio report. Più: caccia alle **nuove discrepanze** nate dalle due
ondate beta di agosto–settembre (import wizard, modali transazioni, segnali/drawdown,
AI export, condivisione broker, Docker).

### Metodo e limiti

- **Sola analisi statica read-only** (grep/glob/view, git log/show read-only, knip).
  **Nessun test eseguito, nessun server avviato**: una run full seriale era in corso
  durante l'audit e condivide l'unico database/backend di test. I numeri di copertura
  (90,48 % / 90,66 %) sono quindi marcati *non verificabili staticamente* — è stata
  verificata la **struttura** (registrazione test, guardie, selettori), non la misura.
- Ogni claim numerico è stato **riprodotto con un comando** citato nel report d'area.
- Dieci agenti di verifica paralleli, uno per area; ogni `file:riga` citato è stato
  riaperto sul sorgente. Spot-check incrociati del coordinatore sui reperti critici
  (B1 `portfolio_engine.py:1967`, S110 `cache_utils.py:82`, Pillow `uploads.py`,
  catalogo AI export asset vs `signals.en.md`) — tutti confermati.
- Le pagine EN non-developer sono ancora **182** (come alla baseline del 05/08);
  backend 244 file `.py`, frontend 611 file `.svelte/.ts`.

---

## Il verdetto in una pagina

**L'esecuzione S1–S3 del 2026-08-05 è tenuta quasi ovunque: 31 interventi su 32
reggono.** Le grandi pulizie non sono regredite: 0 file frontend morti (erano 20),
13 barrel eliminati e non rinati, licenza corretta, registrazione utenti protetta,
task di pre-warm trattenuto, `LiveTicker` rimosso consapevolmente.

**Ma i tre bug 🔴 che l'audit aveva messo in cima sono ancora tutti aperti**, e i
livelli «zero» raggiunti il 05/08 si stanno erodendo per mancanza di gate automatici.

> **Aggiornamento in giornata (02/09)**: i reperti 2 e 4 (lo stesso bug su due facce)
> sono stati chiusi poche ore dopo questo audit — vedi nota in cima a
> [99_task_riesumati.md](99_task_riesumati.md) §P0. Il reperto 6 (WAC multi-broker)
> resta aperto ed è nel piano P1 come decisione già presa dall'utente? → resta da
> pianificare (vedi P2-2: è una decisione di prodotto, endpoint o rimozione).

### I sei reperti che contavano — stato oggi

| # | Reperto (2026-08-07) | Stato oggi | Evidenza |
|---|---|---|---|
| 1 | Licenza MIT su progetto AGPL | ✅ **FATTO** (S1–S3) | `pyproject.toml`: AGPL-3.0, v1.1.0, Python ≥3.13, Beta |
| 2 | `get_global_setting()` argomenti invertiti → TypeError | ✅ **FATTO 02/09** | `portfolio_engine.py:1967` → `get_effective_base_currency(self.db, user_id)`; ramo `target_currency=None` ora coperto da test (`test_settings_service.py`) |
| 3 | Toggle registrazione mai verificato da `/auth/register` | ✅ **FATTO** (S1–S3) | `auth.py:189-191` → 403 + esenzione primo utente + test REG-006 |
| 4 | Chiave `base_currency` inesistente → sempre «EUR» | ✅ **FATTO 02/09** (giorno dell'audit) | 3 call site: `portfolio_engine.py:1967`, `lots_analysis_service.py:581`, `portfolio_service.py:719` → helper `get_effective_base_currency` (per-utente → globale → EUR) |
| 5 | `create_task()` senza riferimento | ✅ **FATTO** (S1–S3) | `_background_tasks` in `main.py:263-265` |
| 6 | WAC multi-broker cablato a nulla | 🔴 **MAI FATTO** | `portfolio_service.py:347`, solo test la chiamano |

I reperti 2 e 4 sono **lo stesso bug su due facce** (la riga 1967 è uno dei 3 call
site del reperto 4): un intervento solo li chiude entrambi. Vedi
[02](02_services_core.md) e [99](99_task_riesumati.md) P0-1.

### Backlog residuo dell'audit (42 voci al 2026-08-05)

| Esito nel mese | Voci |
|---|---:|
| Chiuse | 3 (4.10, 4.12, 5.1 `merge_other_identifiers` ora in produzione) |
| Parziali | 4 (3.8, 4.9, 5.11, 6.1: response_model 17→6) |
| Ancora aperte | **35** |
| Regredite | 1 (S110 → `cache_utils.py:82`, commit `c8cd0fb2` del 2026-08-13) |

Nessuna delle 14 voci S6 (refactor strutturali) è stata avviata; 4 sono **peggiorate**
(6.5 TRY400 53→55, 6.9, 6.10 `$:` 101→109, 6.13 `asset_source.py` 4 800→5 162 righe).

### Audit mkdocs (64 reperti del 2026-08-07)

| Blocco | Stato oggi |
|---|---|
| Implementazioni codice Blocco 1 (5 voci, S1–S3) | ✅ **reggono tutte** (auth, `--workers`, FX header reject, chart settings) |
| Remediation manuale EN Blocco 3 (23 voci «✅») | ⚠️ **sovrastimata**: 4 parziali (A4/A5, B9, R-04) + 1 «già allineato» che non regge (06A R-06 mai corretto) |
| Reperti mai toccati | 34 ancora validi (19 area admin/teoria, 15 area utente) |
| Nuove discrepanze agosto–settembre | **18** (12 area utente, 6 area admin/sito) |
| Igiene sito | eccellente: 0/526 link rotti, 0 orfane su 287 voci nav |

Dettaglio: [mkdocs/01](mkdocs/01_user_e_flussi.md) · [mkdocs/02](mkdocs/02_admin_teoria_sito.md).

---

## Tabella sinottica per report

| # | Report | Cosa resta valido | Cosa è decaduto / fatto | Task |
|---|---|---|---|---|
| 01 | [API layer](01_api_layer.md) | N+1 ×3, 17→6 endpoint senza `response_model`, 8 classi orfane, TRY400 28 | A1 registrazione ✅, A6/A7 ✅ | 6 |
| 02 | [Servizi core](02_services_core.md) | **B1/B2/B3 🔴 aperti**, B7 | B4 pre-engine rimosso ✅, B8 alias ✅, C6 S110 ✅ | 9 |
| 03 | [Pricing & FX](03_services_pricing_fx.md) | C1–C5 fermi; `asset_source.py` peggiorato (5 162 righe) | — | 8 |
| 04 | [Provider](04_providers.md) | D1 invariato per scelta; nuovo tetto C901 CA=71; S110 regredito | 3 quick win ✅; registry intatto (30 BRIM/6 asset/4 FX) | 5 |
| 05 | [Signals & Risk](05_signals_risk.md) | area ancora la più pulita (0 morti/10 923 righe) | orfano unico rimosso ✅; drawdown beta coerente ma **version non bumpata** | 5 |
| 06 | [DB & modelli](06_db_models.md) | F1 DRY orfano (aggravato: label `CHAIN:` ×3) | F3 ✅; F5 ritirato (premessa errata); Alembic regola rispettata | 4 |
| 07 | [Schemi & utils](07_schemas_utils.md) | G1 esploso (190 siti inline), G2/G4/G6 aperti | G3 `merge_other_identifiers` in produzione ✅; G5 chirurgico ✅ | 5 |
| 08 | [Stato & API frontend](08_frontend_state_api.md) | H2/H3/H4/H5/H7 aperti; nuovi orfani beta | H1 bandiere ✅ (nessuna rinata), H8 dipendenze ✅ | 9 |
| 09 | [Componenti frontend](09_frontend_components.md) | I4 (~30 tipi) | I1/I2/I3/I5 ✅ — knip oggi: **0 file morti**; rimozione `TransactionDeleteModal` pulita al 100 % | 5 |
| 10 | [Grafici frontend](10_frontend_charts.md) | G3 regressione `$:` (BrokerSharingPanel 24) | J1 adozione ✅, 0 `$:` nei charts ✅ | 2 aperti |
| 11 | [Trasversale](11_crosscutting.md) | N+1 mai misurati; C901 138→**157**; TRY400 53→55 | K1 licenza ✅, K6 pre-warm ✅, K8 autofix ✅; **nuovo**: Pillow bloccante `uploads.py:423-440` sfuggito al 1° audit | 7 |
| 12 | [Test & copertura](12_test_coverage.md) | 42 test-only: campione confermato; 2 interventi mai fatti | L2.1/L2.2 ✅; **buco copertura frontend chiuso** (istanbul) | 7 |
| 13 | [AI Export](13_ai_export.md) | M2 mai fatto (igiene); drawdown: versione/metadati da decidere pre-tag | tutti i reperti azionabili chiusi; M4.1 regge, zero fallback rinati | 4 |
| 14/15/16 | [Backlog, esecuzione, feature perse](14_backlog_ed_esecuzione.md) | 31/32 interventi reggono; A1/A2/C1 corretti | 3 residue chiuse; A3–A6 test ancora container-only; B1 attenuato | 26 |
| 17 | [Stabilizzazione suite](17_stabilizzazione.md) | B1/B2/B3 fix presenti e stabili; 0 orfani di registrazione (196 file, 68 spec) | spec beta rafforzate, nessuna tautologia nuova | 5 |
| mk | [Area utente](mkdocs/01_user_e_flussi.md) | 15 reperti + 3 parziali; Blocco 1 in-scope regge | 1 decaduta (wizard ormai a 7 step); **12 nuove discrepanze** | 19+9 |
| mk | [Admin/teoria/sito](mkdocs/02_admin_teoria_sito.md) | 19 reperti; 5 implementazioni Blocco 1 reggono | Block 3 sovrastimato (4 parziali + 1 falso); **6 nuove discrepanze** | 18 |

---

## Le tre sorprese peggiori

1. **Il bug più economico è sopravvissuto a tutto.** `portfolio_engine.py:1967` —
   argomenti invertiti, TypeError garantito, fix da una riga, priorità 1 dell'audit —
   è identico a un mese fa, dopo S1–S3 *e* due ondate beta. Il ramo
   (`target_currency=None`) non è coperto da alcun test, quindi nessuna suite può
   inciamparci. Con lui, la chiave `base_currency` fantasma (reperto 4).
2. **I livelli «zero» non si tengono senza gate.** S110 era stato azzerato il 05/08;
   il 13/08 un `except Exception: pass` è rientrato in `cache_utils.py:82` — lo stesso
   file della voce 5.5 del backlog. S110 non è nella `select` ruff di progetto, quindi
   nulla lo intercetta. Stessa erosione: 4 devDep npm inutilizzate (istanbul),
   `$:` 101→109, C901 138→157, TRY400 53→55. La pulizia senza recinzione dura una
   settimana.
3. **La remediation documentale Block 3 era sovrastimata, e i docs continuano a
   promettere ciò che non esiste.** 4 voci «✅ Aggiornato» sono parziali e una «già
   allineato» non era mai stata corretta; nel frattempo `signals.en.md` promette 5
   task AI Export Asset di cui 4 inesistenti nel catalogo, e la pagina Docker del
   backup conserva lo snippet `cp app.db` a container attivo che il fix WAL aveva
   corretto solo altrove.

### Buone notizie (per onestà di bilancio)

- La rimozione beta di `TransactionDeleteModal` è **chirurgica**: zero riferimenti
  residui in codice, i18n (4 lingue) ed e2e. Le spec transazioni riscritte sono più
  forti di prima, nessuna asserzione tautologica nuova.
- Il buco di misurazione più grande del progetto è chiuso: esiste ora copertura JS
  (istanbul + `frontend/coverage-js/`).
- `merge_other_identifiers` — il reperto-simbolo «mai eseguito» — è oggi in
  produzione dentro `merge_assets`.
- L'area signals resta la più pulita del progetto anche dopo il rework drawdown.

---

## Report di questa tornata

| # | Report | Ambito |
|---|---|---|
| 01 | [API layer](01_api_layer.md) | `backend/app/api/v1/` |
| 02 | [Servizi core](02_services_core.md) | portfolio, FIFO, lots, transactions |
| 03 | [Pricing & FX](03_services_pricing_fx.md) | `asset_source.py`, `fx.py` |
| 04 | [Provider](04_providers.md) | plugin asset / FX / BRIM |
| 05 | [Signals & Risk](05_signals_risk.md) | signal plugin, risk analytics |
| 06 | [DB & modelli](06_db_models.md) | `db/`, `alembic/` |
| 07 | [Schemi & utils](07_schemas_utils.md) | `schemas/`, `utils/` |
| 08 | [Stato & API frontend](08_frontend_state_api.md) | store, client Zodios |
| 09 | [Componenti frontend](09_frontend_components.md) | componenti, route |
| 10 | [Grafici frontend](10_frontend_charts.md) | `charts/`, `signals/` |
| 11 | [Trasversale](11_crosscutting.md) | Async I/O, N+1, `$:`, config |
| 12 | [Test & copertura](12_test_coverage.md) | salute suite, struttura |
| 13 | [AI Export](13_ai_export.md) | catalogo, composer, frontend |
| 14 | [Backlog & esecuzione](14_backlog_ed_esecuzione.md) | verifica report 14/15/16 |
| 17 | [Stabilizzazione](17_stabilizzazione.md) | verifica report 17 |
| mk1 | [mkdocs — utente e flussi](mkdocs/01_user_e_flussi.md) | pagine user, import, FX, AI export |
| mk2 | [mkdocs — admin, teoria, sito](mkdocs/02_admin_teoria_sito.md) | installazione, teoria, gallery |
| **99** | [**Task riesumati**](99_task_riesumati.md) | **backlog consolidato, deduplicato, prioritizzato** |

> I report 15 e 16 dell'audit originale (cronaca e caccia alle feature perse) non
> hanno un equivalente numerato: la loro verifica è nelle sezioni A/C del
> [report 14](14_backlog_ed_esecuzione.md).

## Cross-link con l'audit archiviato

Ogni report linka la propria fonte in [`../phases/05_cleanAudit/`](../../phases/05_cleanAudit/INDEX.md).
I file archiviati **non sono stati modificati**. Chi legge l'audit vecchio deve
sapere che la fotografia del 2026-08-07 è corretta come storia, ma gli stati
operativi aggiornati sono **qui**.
