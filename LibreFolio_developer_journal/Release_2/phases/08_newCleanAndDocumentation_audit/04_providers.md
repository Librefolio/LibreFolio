# 04 — Provider — verifica 2026-09-02

> Fonte: [report archiviato](../../phases/05_cleanAudit/04_providers.md) (audit 2026-08-05/07, commit di riferimento `be8394bb`)
> Metodo: analisi statica read-only; nessun test eseguito (run full in corso, DB condiviso).
> Working tree con modifiche beta non committate del 02/09 incluso nella verifica
> (`schemas/provider.py` error_details I3, `asset_source.py` full_history + probe, i18n ×4).
> Nota di riproduzione: il set esatto di "regole estese" ruff dell'audit non è documentato
> nel report archiviato; qui si usa `pipenv run ruff check --extend-select TRY,ARG,SIM,S,PIE,PERF,RUF,C901 --ignore TRY003`
> (da `backend/`), che riproduce **esattamente** tutti i conteggi per-file citati dall'audit
> (yahoo 22→20 post-fix, brim_provider 12, scheduled_investment 12, justetf 10).

---

## Sintesi esecutiva

Il giudizio dell'audit — *la parte del progetto che ha scalato meglio* — **regge un mese
dopo**, e i tre interventi "a costo nullo" sono stati **tutti eseguiti** in S1–S3
(commit `be8394bb`, 2026-08-05): docstring FX corretta, log sugli `S110` di
`yahoo_finance.py` e `provider_registry.py`, 6 `pass` superflui rimossi da
`brim_provider.py`. Il pattern registry (auto-discovery + `params_schema` opzionale) è
intatto e rispettato da tutti i provider presenti oggi.

La **duplicazione BRIM (D1) è invariata per scelta**: 35 funzioni sopra soglia allora
(riprodotto su snapshot `be8394bb`), 35 oggi — ma la composizione è peggiorata in cima:
il rework Crédit Agricole del 08–12/08 (commit `571bcde0`, `c0814ee4`) ha prodotto
`_parse_account_movements` a complessità **71**, il nuovo massimo dell'area (allora 33).
Nessun provider aggiunto o rimosso: 30 BRIM registrati, 6 asset, 4 FX banche centrali
(+ MANUAL + 2 mock) — il "29 BRIM" dell'audit era un conteggio impreciso (30 già allora).

**Regressione minore**: un nuovo `S110` (`try/except/pass`) è nato il 13/08 in
`utils/cache_utils.py:82` (commit `c8cd0fb2`), rompendo l'invariante "S110 = 0 in
backend/app" dichiarata da S1–S3. Fuori dal perimetro provider, ma regredisce lo
standard fissato dall'intervento 1 di questo report.

**Correzione al report originale**: `get_provider` non era "usato da nessuno" — i test
esterni lo chiamano dal 2025-11-10 (`test_external/test_fx_providers.py:91`,
`test_asset_providers.py:87`, presenti identici al commit d'audit). La deriva
documentale segnalata (docstring FX) era reale ed è stata corretta.

**Beta 02/09 (working tree)**: il resolver errori provider localizzati è coerente
end-to-end (backend `error_details` → resolver frontend → chiavi `providerErrors.*`
presenti e identiche nelle 4 lingue). Nessun debito introdotto.

---

## Tabella di verifica

| Voce vecchia | Stato 2026-08 | Stato verificato oggi | Evidenza | Azione |
|---|---|---|---|---|
| Struttura: `asset_source_providers/` 7 file, `fx_providers/` 7, `brim_providers/` 32, + `brim_provider.py`, `provider_registry.py` | misura | **ANCORA VALIDO** | `ls`: 7/7/32 file `.py` oggi; identico al commit d'audit (`git ls-tree be8394bb`) | — |
| "29 provider BRIM, 6 asset, 4 FX" | misura | **PARZIALE (conteggio impreciso)** | Oggi **30** classi BRIM registrate (`grep -c "@register" brim_providers/broker_*.py` → 30 file, incl. `GenericCSVBrokerProvider` broker_generic_csv.py:306-307); al commit d'audit erano già 30. Asset: 6 registrazioni ✅. FX: 7 registrazioni = ECB/FED/BOE/SNB + MANUAL + MOCKFX×2 (boe.py:23, ecb.py:22, fed.py:25, snb.py:55, manual.py:28, mockfx.py:34,98) | Correggere il numero a 30 nella memoria storica |
| Righe: brim 11 700 / asset 3 745 / fx 1 568 | misura | **RIPRODOTTO / EVOLUTO** | Al commit d'audit: brim 11 700 ✅, fx 1 568 ✅, asset 3 743 (le 2 righe di delta sono gli S110 fix del commit stesso). **Oggi**: brim **12 440** (+740, rework CA), asset 3 743, fx 1 568 | — |
| Rilievi ruff ~60 / ~51 / ~20 | misura | **NON RIPRODUCIBILE ALLA LETTERA** (regole non documentate) | Con il set equivalente documentato sopra: brim 80, asset 61, fx 26. I per-file citati dall'audit riproducono tutti (vedi righe sotto) | Registrare il comando esatto nei prossimi audit |
| 35 metodi sopra soglia in `brim_providers/` | misura | **ANCORA VALIDO (35 = 35), composizione cambiata** | `ruff --extend-select C901` su snapshot `be8394bb`: 35; oggi su working tree: 35 | — |
| Tabella D1: max 26 (`broker_swissquote.py:177`) | misura | **ERRATA GIÀ ALLORA** | Al commit d'audit il massimo era 33 (`_parse_securities` credit_agricole) e 32 (`cointracking parse`); la tabella ometteva le 3 voci più alte. Le 12 righe citate: tutte verificate identiche oggi (stesso valore, stessa riga) | Nota metodologica |
| D1 — 35 `parse` stessa forma, rimedio helper in base | aperto | **ANCORA VALIDO / MAI FATTO** (confermato saggio) | I 12 `parse` citati: complessità identiche oggi (`swissquote:177`=26, `trading212:186`=24, `xtb:194`=23, `saxo:187`=23, `rabobank:149`=23, `investimental:186`=23, `schwab:221`=22, `parqet:138`=22, `traderepublic:133`=21, `revolut:339`=15, `revolut:458`=12, `relai:118`=11). Base senza helper di parsing nuovi (`grep "def " brim_provider.py`) | Task T2 sotto |
| D1 — parziale: dedupe `is_fiat_currency` | — | **FATTO (post-audit, fuori piano)** | Unica copia in `schemas/common.py:312`; importata da 4 broker (bitvavo, cointracking, cryptocom, delta). Commit `e2f488cf` 28/08: le 4 copie celavano 2 bug reali (AttributeError su input non-stringa) | — |
| D2 — docstring `fx_providers/__init__.py` indicava `get_provider` | aperto | **FATTO** | Riga 8 oggi: "use FXProviderRegistry.get_provider_instance(code)". Backlog 14 voce 1.3 ✅, commit `be8394bb` | — |
| D2 — `get_provider` "usato da nessuno" | aperto | **PREMESSA ERRATA / SUPERATO** | Usato dai test esterni dal 2025-11-10 (`test_fx_providers.py:91`, `test_asset_providers.py:87` — verificato con `git show be8394bb:...`); alias ancora presente (`provider_registry.py:233-234`), senza commento classe-vs-istanza nel codice, ma documentato correttamente in `mkdocs_src/.../registry_pattern.md:54-55` | Opzionale: commento di 1 riga sull'alias |
| D2 — `list_plugin_classes` mai esercitata | aperto | **ANCORA VALIDO (orfano)** | Definita a `provider_registry.py:89`; grep globale (backend+scripts+frontend): unico risultato è la definizione. Decisione backlog 5.9 ("rimuovere o documentare") mai presa | Task T3 sotto |
| D3 — `yahoo_finance.py` 22 rilievi, S110 ×2 (357, 630) | aperto | **S110 FATTO / resto INVARIATO** | Oggi 20 rilievi (set equivalente): TRY301 5 ✅, ARG002 5 ✅, TRY300 4 ✅, SIM108 3 ✅, C901 2 ✅ — S110 **0** (fixati in `be8394bb`; backlog 2.6 ✅) | — |
| D3 — `get_history_value` complessità 31 | aperto | **ANCORA VALIDO / MAI FATTO** | Oggi a `yahoo_finance.py:284`, ancora 31 (`ruff --extend-select C901`). Backlog 6.6 aperto | Task T4 sotto |
| D4 — 6 `pass` superflui in `brim_provider.py` (PIE790) | aperto | **FATTO** | `grep -n "^\s*pass\s*$" brim_provider.py` → zero risultati; nessun PIE790 nel file (autofix Fase F, PIE790×54 globali) | — |
| D5 — `scheduled_investment.py` 12, `justetf.py` 10 | aperto | **ANCORA VALIDO / MAI FATTO** | Oggi: 12 e 10 (identici, set equivalente). Debito di stile diffuso TRY/SIM/ARG come da descrizione | Bassa priorità |
| Intervento 1 (log S110 yahoo) | raccomandato | **FATTO** | `be8394bb`; S110 oggi 0 nel file | — |
| Intervento 2 (docstring FX) | raccomandato | **FATTO** | `fx_providers/__init__.py:8` | — |
| Intervento 3 (rimuovere 6 `pass`) | raccomandato | **FATTO** | vedi D4 | — |
| Intervento 4 (decidere `get_provider`/`list_plugin_classes`) | raccomandato | **PARZIALE** | Alias tenuto e oggi giustificato dai test esterni + doc mkdocs; `list_plugin_classes` ancora orfano senza decisione | Task T3 |
| Intervento 5 (ridurre `get_history_value` 31) | raccomandato | **MAI FATTO** | `yahoo_finance.py:284` = 31 | Task T4 |
| Intervento 6 (helper BRIM condivisi, un provider alla volta) | raccomandato con cautela | **MAI FATTO (mass refactoring) / PARZIALE (dedupe puntuale)** | Solo `is_fiat_currency` deduplicata (`e2f488cf`). Il consiglio dell'audit ("non in un ciclo di pulizia generale") è stato rispettato | Task T2 |
| Registry: auto-discovery + `params_schema` per form dinamiche | assunto | **ANCORA VALIDO** | `auto_discover` via importlib (`provider_registry.py:101-130`); `params_schema` default `[]` in `asset_source.py:693-703`, override in 4 provider (borsa_italiana:314, css_scraper:75, justetf:219, scheduled_investment:687); yahoo_finance senza → default coerente (no params); FX senza (contratto `fx.py` non lo richiede); 30 BRIM tutti con `@register_provider` | — |

---

## Dettaglio reperti ancora aperti / regrediti

### D1 — invariato per scelta, ma il tetto è salito: 33 → 71

Comando: `pipenv run ruff check --extend-select C901 --output-format concise app/services/brim_providers/`

All'audit (riprodotto su snapshot `be8394bb` estratto con `git show`): 35 funzioni,
massimo `_parse_securities` (credit_agricole) 33. Oggi: 35 funzioni, massimo
**`_parse_account_movements` (broker_credit_agricole.py:929) = 71** — nata nel rework
CA del 08–12/08 (`571bcde0`, `c0814ee4`), più che doppia rispetto al massimo storico.
`_parse_securities` è scesa 33 → 32 (`:522`). Il totale costante (35) maschera un
peggioramento in coda: la funzione più complessa dell'area provider è ora quasi 3× il
`parse` mediano. È il candidato naturale per il primo giro di estrazione helper "un
provider alla volta" raccomandato dall'audit.

### D2 — coda residua: solo `list_plugin_classes`

`provider_registry.py:89-92`: nessun chiamante in tutto il repository (comando:
`grep -rn "list_plugin_classes" --include="*.py" backend/ scripts/`). Alias
`get_provider` (`:233`) invece è vivo nei test esterni dal 2025-11 e la documentazione
sviluppatori è allineata — il reperto D2 si riduce oggi alla sola decisione su
`list_plugin_classes` (backlog 5.9, mai schedulata).

### Regressione S110 (fuori perimetro, segnalata)

> ✅ **Risolto 02/09** (P0-2): swallow convertito in `logger.debug(..., exc_info=True)` +
> test. Gate anti-ricaduta lo stesso giorno (P0-3): `S110` nella `select` ruff.

`backend/app/utils/cache_utils.py:81-83` — `clear()` con `try: old.close() /
except Exception: pass` (commento presente, nessun log). Nata il 13/08 in `c8cd0fb2`,
**dopo** la bonifica S1–S3 che aveva dichiarato `S110 = 0` in `backend/app`
(verificato: su `be8394bb` il file passa ruff S110; oggi
`ruff check --extend-select S110 app/` → 1 occorrenza). Stessa classe di problema dei
due `S110` di yahoo_finance risolti: silenzio senza `logger.debug`.

---

## Task riesumati (numerati, evidenza, stima S/M/L)

- **T1 (S)** — Loggare l'`S110` di `cache_utils.py:82` (`logger.debug(..., exc_info=True)`),
  ripristinando l'invariante S110=0 dichiarata da S1–S3. Evidenza: `ruff check
  --extend-select S110 app/` → 1. Costo identico all'intervento 1 dell'audit (2 righe).
  > ✅ **Fatto 02/09** (P0-2): `logger.debug("Cache close failed during clear",
  > exc_info=True)` al posto del `pass` + test del log. E il 02/09 è arrivato anche il
  > gate (P0-3): `S110` nella `select` ruff di `pyproject.toml` (puntuale).
- **T2 (L, alto rischio — un provider alla volta)** — Estrazione helper condivisi BRIM,
  iniziando da `broker_credit_agricole.py` (`_parse_account_movements` 71 a :929,
  `_parse_securities` 32 a :522). Evidenza: comandi C901 sopra. La raccomandazione
  originale (mai refactoring di massa) resta valida; `e2f488cf` ha mostrato il metodo
  giusto (dedupe puntuale con bug trovati a conferma del valore).
- **T3 (S)** — Decidere `list_plugin_classes` (`provider_registry.py:89`): rimozione
  banale (nessun chiamante) oppure commento "API di introspezione riservata". Backlog 5.9.
  > ✅ **Fatto 03/09** (P1-15, Lane B): decisione = **rimozione** — `list_plugin_classes`
  > **e** l'alias `get_provider` sono stati tolti dal registry; i test esterni che usavano
  > l'alias dal 2025-11 sono migrati a `get_provider_instance` (verificato:
  > `test_fx_providers.py`, `test_asset_providers.py`). Il commento `# Intentionally
  > unwired` su `ensure_rates_multi_source` (fx.py:389) è arrivato nella stessa corsa.
- **T4 (M)** — Ridurre `get_history_value` (`yahoo_finance.py:284`, complessità 31,
  invariata dall'audit). Backlog 6.6. Rischio medio: provider più usato e più instabile.
- **T5 (S)** — Chiudere il debito di stile D5 (scheduled_investment 12, justetf 10)
  abilitando in permanenza le regole TRY/SIM/ARG, come già suggerito dall'audit.

---

## Nuovi rilievi

- **N1 🟡** — `_parse_account_movements` complessità **71** (`broker_credit_agricole.py:929`),
  nata post-audit (08–12/08). Oggi è la funzione più complessa di tutta l'area provider;
  il file è cresciuto di +740 righe nette in un mese (11 700 → 12 440). Da affrontare
  prima che diventi il modello copiato dal prossimo broker (è così che nasce la
  ripetizione misurata da D1).
- **N2 🟢** — `S110` riapparso in `cache_utils.py:82` (vedi sopra): lo standard
  "nessun except silenzioso" non ha una guardia automatica (`S110` non è nel `select`
  del `pyproject.toml`, solo nello scan esteso) → senza enforcement CI, la regressione
  è entrata inosservata 20 giorni dopo la bonifica.
  > ✅ **Entrambe le metà chiuse il 02/09**: sito loggato (P0-2) e guardia creata (P0-3 —
  > `S110` in `select` a `pyproject.toml:81`).
- **N3 🟢 (positivo)** — Resolver errori provider localizzati (beta 02/09, working tree):
  catena completa verificata — `schemas/provider.py:360` (`error_details`),
  `_json_safe_details` (`asset_source.py:239-255`) sui 3 path probe (`:1959`, `:1998`,
  `:2027`) + `error_code="TIMEOUT"` aggiunto ai timeout; produttore reale del caso
  documentato (`borsa_italiana.py:505-507`: `NO_DATA` con `{"nav_date": ...}`);
  resolver frontend `resolveProviderError.ts` consumato da
  `ProviderAssignmentSection.svelte`; chiavi `providerErrors.*` (9: FETCH_ERROR,
  MISSING_PARAMS, NOT_FOUND, NOT_IMPLEMENTED, NO_DATA, NO_DATA_STALE, PARSE_ERROR,
  SCRAPE_ERROR, TIMEOUT) **presenti e identiche in en/it/fr/es**; client API rigenerato
  (`generated.ts` contiene `error_details`; il file è gitignored da `c70c46ca`, quindi
  non appare in `git status` — sincronizzazione avvenuta). Test Vitest dedicato
  (`resolveProviderError.test.ts`) presente. Approccio incrementale dichiarato nel
  docstring (solo i codici della superficie "Test Configuration") — coerente.
- **N4 🟢 (nota)** — I mock provider (`mockfx.py` ×2, `mockprov.py`) restano registrati
  nel registry di produzione via auto-discovery e solo "nascosti" dalla lista API
  pubblica ("Hidden from public API list", `mockfx.py:16`). Situazione invariata
  dall'audit, documentata in-file; nessuna azione.

---

## Cross-reference

- [14 — Backlog](../../phases/05_cleanAudit/14_backlog_per_complessita.md): 1.3 ✅ docstring FX; 2.6 ✅ S110; 5.9 aperta (`get_provider`/`list_plugin_classes`); 6.6 aperta (`get_history_value`).
- [15 — Esecuzione S1–S3](../../phases/05_cleanAudit/15_esecuzione_s1_s3.md): fix S110 (yahoo ×2, provider_registry ×1) e rimozioni verificati in `be8394bb`.
- Report gemello di questa tornata: `05_signals_risk.md` (stessa cartella) per `signal_service` ↔ provider FX (consumatore del plan), e `13_ai_export.md` per l'uso AI Export dei provider.
- Beta 02/09 correlate: `signal_plugins/drawdown.py` full_history tocca `asset_source.py:2200-2210` (fetch path) — vedi report 05.
