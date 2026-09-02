# 11 — Trasversali

> Async I/O Rule, query N+1, migrazione Runes, gestione eccezioni, metadati di progetto
> Gravità massima: 🔴

---

## Sintesi

Questo report raccoglie ciò che non appartiene a un singolo sottosistema: le regole di
progetto e i pattern che attraversano l'intero codebase.

Il quadro è migliore del previsto su due fronti e peggiore su uno.

**Meglio del previsto**: la *Async I/O Rule* — la regola più severa del progetto — ha
**una sola violazione** in 73 721 righe di backend. Su 104 siti sospetti sottoposti a
verifica, 103 sono corretti. È il risultato di disciplina reale, non di fortuna.

**Peggio del previsto**: `pyproject.toml` dichiara **licenza MIT** su un progetto
AGPL-3.0. È l'unico reperto 🔴 dell'audit che riguarda un rischio non tecnico.

Il resto è debito strutturato: 138 funzioni sopra soglia di complessità, 38 candidati
N+1, 101 statement reattivi legacy, 11 eccezioni inghiottite in silenzio.

---

## Metriche

### Rilevazioni ruff (set esteso) — totale **702**, 145 auto-correggibili

| Regola | N | Significato |
|---|---:|---|
| `C901` | **138** | funzione troppo complessa |
| `ARG002` | 77 | argomento di metodo inutilizzato |
| `PIE790` | 54 | statement `pass` superfluo |
| `TRY400` | 53 | `logger.error` dove serve `logger.exception` |
| `RUF100` | 48 | direttiva `noqa` inutile |
| `TRY300` | 38 | `return` da spostare in `else` |
| `TRY301` | 37 | `raise` dentro `try` |
| `SIM108` | 33 | `if/else` esprimibile come ternario |
| `ARG003` | 33 | argomento di classmethod inutilizzato |
| `RUF010` | 23 | conversione esplicita in f-string |
| `PERF401` | 18 | ciclo sostituibile con list comprehension |
| `SIM102` | 14 | `if` annidati unificabili |
| `ARG001` | 14 | argomento di funzione inutilizzato |
| `RUF022` | 12 | `__all__` non ordinato |
| `S110` | **11** | `try`/`except`/`pass` silenzioso |
| `RUF007` | 9 | usare `itertools.pairwise` |

### Altri indicatori

| | Valore |
|---|---:|
| Violazioni Async I/O | **1** su 104 siti verificati |
| Candidati N+1 | **38** |
| Statement `$:` legacy | **101** |
| `TODO`/`FIXME`/`HACK` nel backend | **8** |
| File di test orfani | **0** |

---

## Reperti

### 🔴 K1 — `pyproject.toml` dichiara licenza MIT su un progetto AGPL-3.0

**Dove**: `pyproject.toml`, righe 7-22

```toml
[project]
name = "librefolio"
version = "0.6.x"
requires-python = ">=3.11"
classifiers = [
    "Development Status :: 3 - Alpha",
    "License :: OSI Approved :: MIT License",
    ...
]
```

Quattro incoerenze in sedici righe, di cui una seria:

| Campo | Dichiarato | Realtà |
|---|---|---|
| **Licenza** | `MIT License` | **AGPL-3.0** (`LICENSE`, `README.md`, GitHub) |
| Versione | `0.6.x` | 1.1.0 in uscita — e `0.6.x` non è nemmeno una versione valida |
| Python | `>=3.11` | 3.13 secondo la documentazione |
| Maturità | `Alpha` | 11 release pubblicate |

**La licenza è il problema reale.** MIT e AGPL-3.0 sono agli antipodi: MIT permette l'uso
in software proprietario chiuso, AGPL-3.0 impone la condivisione del sorgente anche per
il solo uso via rete. Un utilizzatore che legga i metadati del pacchetto e integri
LibreFolio in un prodotto chiuso agirebbe in buona fede su un'informazione sbagliata.

Il progetto ha appena completato il lavoro sulla conformità delle licenze di terze parti
(`THIRD_PARTY_LICENSES.md`, attribuzioni nelle pagine crediti in quattro lingue).
Dichiarare male la **propria** licenza vanifica quel lavoro.

**Rimedio** — quattro righe:

```toml
version = "1.1.0"
requires-python = ">=3.13"
classifiers = [
    "Development Status :: 4 - Beta",
    "License :: OSI Approved :: GNU Affero General Public License v3 or later (AGPLv3+)",
    ...
]
```

Costo: nullo. È l'intervento più urgente dell'intero audit, ed è anche il più semplice.

---

### 🟡 K2 — Unica violazione della Async I/O Rule

**Dove**: `backend/app/api/v1/uploads.py:377`

```python
# Read text file window
try:
    with open(file_path, encoding="utf-8") as f:
        if offset:
            f.seek(offset)
        content = f.read(window) if window else f.read()
```

`open()` sincrona dentro un `async def`. Blocca l'intero event loop per la durata della
lettura — l'endpoint di anteprima testuale dei file caricati, dove `window` può essere
`None` e quindi leggere il file **intero**.

L'impatto è proporzionale alla dimensione del file: un CSV BRIM da qualche megabyte
blocca tutte le richieste concorrenti per la durata della lettura.

**Rimedio** — una riga:

```python
content = await asyncio.to_thread(_read_window, file_path, offset, window)
```

**Su 104 siti sospetti, 103 sono corretti.** Questo è il risultato migliore dell'audit e
merita di essere detto: la regola più difficile da rispettare del progetto è rispettata al
99 %. Vale la pena correggere l'ultima.

---

### 🟡 K3 — 38 candidati N+1, due terzi in un solo file

| File | N+1 |
|---|---:|
| `services/asset_source.py` | **26** |
| `api/v1/fx.py` | 6 |
| `services/fx.py` | 3 |
| `services/settings_service.py` | 1 |
| `services/brim_provider.py` | 1 |
| `api/v1/portfolio_api.py` | 1 |

Il dettaglio di `asset_source.py` è nel report [03](03_services_pricing_fx.md), reperto C1.

I sei di `api/v1/fx.py` sono in blocchi distinti (cicli a riga 340, 775, 859, 914), tutti
con `session.execute` nel corpo. Trattandosi di endpoint FX chiamati durante il
caricamento della dashboard, l'effetto è cumulativo con quello del pricing.

**Rimedio standard**: precaricare con `WHERE id IN (...)`, indicizzare in un dizionario,
usarlo nel ciclo. Nessun cambio di logica.

**Attenzione ai falsi positivi**: il rilevatore non distingue fra cicli su collezioni
illimitate (fornite dall'utente) e cicli su insiemi piccoli e fissi (i 4 provider FX). I
secondi non sono problemi. Vanno verificati uno per uno, partendo da quelli con N
illimitato.

---

### 🟡 K4 — 11 eccezioni inghiottite in silenzio

| File:riga | Contesto |
|---|---|
| `api/v1/system.py:87,102,136` | informazioni di sistema |
| `api/v1/uploads.py:81` | gestione file |
| `services/asset_source.py:2697,3076` | recupero prezzi |
| `asset_source_providers/yahoo_finance.py:357,630` | **provider prezzi principale** |
| `services/provider_registry.py:460` | auto-discovery plugin |
| `utils/version.py:36,51` | lettura versione da git |

Un `try`/`except`/`pass` senza log significa che il fallimento è **invisibile**. Il
sistema continua a funzionare in modo degradato e nessuno sa perché.

Non tutti sono uguali:

- `version.py` — accettabile: se git non è disponibile, si usa un fallback. Il degrado è
  atteso e innocuo.
- `provider_registry.py:460` — **problematico**: un plugin che fallisce l'import scompare
  silenziosamente dall'elenco. Un utente vedrebbe "provider non disponibile" senza
  spiegazione, e nessuno saprebbe che c'è un errore di import.
- `yahoo_finance.py:357,630` — **il caso peggiore**: il provider prezzi più usato e più
  instabile, con due punti in cui il fallimento sparisce. Quando i prezzi smettono di
  aggiornarsi, non c'è traccia diagnostica.

**Rimedio**: aggiungere `logger.debug(..., exc_info=True)` dove il fallimento è atteso,
`logger.warning` dove non lo è. Undici righe in tutto, nessun cambio di comportamento —
solo visibilità.

Correlato: **53 `TRY400`** (`logger.error` dove servirebbe `logger.exception`). Anche qui
si perde lo stack trace: si registra che qualcosa è fallito, non dove. La correzione è
meccanica, ma va fatta a mano perché ruff non può sapere se il chiamante si aspetta il
formato attuale del log.

---

### 🟡 K5 — 138 funzioni sopra soglia di complessità

Distribuzione per sottosistema:

| Area | C901 |
|---|---:|
| `brim_providers/` | 35 |
| altri servizi | ~40 |
| schemi (validatori) | ~15 |
| resto | ~48 |

Le dieci peggiori:

| Complessità | Funzione | File |
|---:|---|---|
| **112** | `execute_batch` | `transaction_service.py` |
| **97** | `build` | `portfolio_engine.py` |
| 73 | `get_summary` | `portfolio_service.py` |
| 62 | `get_positions_contribution` | `portfolio_service.py` |
| 59 | `bulk_refresh_prices` | `asset_source.py` |
| 54 | `sync_pairs_bulk` | `fx.py` |
| 46 | `get_prices_bulk` | `asset_source.py` |
| 35 | `get_lots_analysis` | `lots_analysis_service.py` |
| 32 | `compute_wac_iterative_multi_broker` | `wac_service.py` |
| 32 | `compute_wac_iterative` | `wac_service.py` |

Le prime due sono di un altro ordine di grandezza rispetto al resto: `execute_batch` a
112 e `build` a 97 contro un terzo posto a 73.

Dettagli nei report [02](02_services_core.md) e [03](03_services_pricing_fx.md).

**Nota sulla soglia**: 10 è il valore predefinito di `mccabe` ed è severo per codice di
dominio finanziario, dove la ramificazione è intrinseca. Un valore realistico per questo
progetto è 20-25. Con soglia 25 i reperti scenderebbero da 138 a una ventina — e quella
ventina sarebbe la lista su cui lavorare davvero.

**Raccomandazione**: fissare `max-complexity = 25` nella configurazione ruff. Non nasconde
il problema: rende il segnale utilizzabile. Una soglia che produce 138 avvisi viene
ignorata; una che ne produce 20 viene affrontata.

---

### 🟡 K6 — `main.py:251`: task asyncio non trattenuto

**Dove**: `backend/app/main.py:251`

```python
# Pre-warm provider caches in background (non-blocking)
asyncio.create_task(_prewarm_provider_caches())

# Start scheduler daemon
shutdown_event = get_shutdown_event()
scheduler_task = asyncio.create_task(scheduler_loop(shutdown_event))
```

Il riferimento al task non viene conservato (`RUF006`). Il garbage collector può
raccoglierlo prima del completamento, e il pre-riscaldamento delle cache si interrompe a
metà — in modo **non deterministico**, quindi non riproducibile.

Il contrasto con la riga successiva è illuminante: `scheduler_task` **è** assegnata a una
variabile, quindi trattenuta. La differenza non è intenzionale, è una svista.

Il sintomo, se si manifesta, è di quelli che fanno perdere giorni: "a volte all'avvio i
prezzi sono lenti la prima volta".

**Rimedio**:

```python
prewarm_task = asyncio.create_task(_prewarm_provider_caches())
```

Una riga. È l'unico bug latente di questo report ed è a costo zero.

---

### 🟢 K7 — 101 statement reattivi `$:` legacy

| Area | N |
|---|---:|
| `components/ui/` | 26 |
| `components/brokers/` | 26 |
| `components/settings/` | 25 |
| `routes/` | 21 |
| `components/layout/` | 3 |
| `charts/` | **0** |

I file più densi: `BrokerSharingPanel.svelte` (20), `brokers/[id]/+page.svelte` (12),
`ImageEditModal.svelte` (10), `PreferencesTab.svelte` (8), `GlobalSettingsTab.svelte` (7).

La regola di progetto impone `$state`/`$derived`/`$effect` nei nuovi componenti; questi
101 sono precedenti alla regola.

Il report [10](10_frontend_charts.md), reperto J2, spiega la distribuzione: la migrazione
è completa dove il guadagno era immediato (catene di derivazione profonde nei grafici) e
arretrata dove è marginale (espressioni singole nei form).

**Rimedio**: migrare file per file quando si tocca il file per altri motivi. Una campagna
dedicata su 101 statement introdurrebbe più rischio di regressione di quanto rimuova
debito — `$:` e `$derived` differiscono nella semantica dell'ordine di esecuzione, e le
differenze si manifestano solo a runtime.

Eccezione: `BrokerSharingPanel.svelte` con 20 statement in un file solo merita una
migrazione dedicata, con test manuale.

---

### 🟢 K8 — Autofix: 77 applicati, 111 deliberatamente non applicati

Su 702 rilevazioni, ruff ne dichiara 145 auto-correggibili. Non tutte le "auto-correzioni"
sono ugualmente innocue, e la distinzione conta.

**Applicate** (Fase F dell'audit, già eseguite):

| Regola | N | Perché è sicura |
|---|---:|---|
| `PIE790` | 54 | rimuove `pass` dove il corpo ha già un docstring — il docstring **è** il corpo |
| `RUF010` | 23 | `f"{str(x)}"` → `f"{x!s}"` — strettamente equivalente |
| **Totale** | **77** | |

Verifica dopo l'applicazione: `./dev.py lint` invariato a **36 errori** (la baseline),
`black --check` pulito, i moduli modificati importano correttamente. Nessuno dei 20 file
toccati appartiene ad `ai_export`.

**Non applicate — `RUF100`, 111 rilevazioni**:

Ruff segnala 111 direttive `# noqa` come inutili. Ma la scomposizione mostra che
**rimuoverle sarebbe una perdita di informazione**, non una pulizia:

| Regola nel `noqa` | N | Stato nella configurazione |
|---|---:|---|
| `ARG001` | 52 | non abilitata |
| `E402` | 45 | in `ignore` |
| `BLE001` | 8 | non abilitata |
| `ARG005` | 4 | non abilitata |

Quelle direttive documentano un'intenzione: *"so che questo argomento è inutilizzato, è
voluto"*. Sono state scritte da chi conosceva il codice, probabilmente con una
configurazione ruff più severa. Rimuoverle:

- non elimina alcun problema — le regole non sono attive, quindi non producono errori;
- cancella l'annotazione che spiega **perché** quel codice è come è;
- va rifatta al contrario se un giorno si abilita `ARG` (cosa che l'audit
  raccomanderebbe, viste le 124 rilevazioni `ARG00*`).

**Decisione**: lasciarle. Il caso `E402` (45 direttive per una regola già in `ignore`) è
effettivamente ridondante e si potrebbe pulire, ma il guadagno è nullo e il rischio di
toccare 45 file per estetica non lo giustifica.

> Nota metodologica: nella prima passata dell'audit i `RUF100` risultavano 48 invece di
> 111, perché lo scan esteso usava `--select` — che **sostituisce** l'elenco delle regole
> del progetto invece di estenderlo, disabilitando `PLC0415` e facendo apparire inutili i
> relativi `noqa`. Usare `--extend-select` dà il numero corretto. È il terzo falso
> positivo metodologico dell'audit, dopo quelli documentati in [INDEX](INDEX.md).

Le restanti auto-correggibili (`SIM108`, `PERF401`, `RUF007`) cambiano la forma del
codice e vanno riviste a mano, anche se il risultato è quasi sempre corretto.

---

## Interventi raccomandati

| Priorità | Intervento | Costo | Rischio |
|---|---|---|---|
| **1** | **Correggere la licenza in `pyproject.toml`** (+ versione, Python, maturità) | nullo | nullo |
| 2 | Trattenere il task di pre-warm in `main.py:251` | nullo | nullo |
| 3 | Correggere l'`open()` bloccante in `uploads.py:377` | basso | basso |
| 4 | Aggiungere log agli 11 `S110`, priorità a `yahoo_finance` e `provider_registry` | basso | nullo |
| 5 | ~~Applicare i 125 autofix sicuri~~ → **77 applicati** (`PIE790`, `RUF010`) | fatto | nullo |
| 6 | Portare `max-complexity` a 25 in `pyproject.toml` | nullo | nullo |
| 7 | Verificare i 38 candidati N+1, partendo dagli endpoint bulk | medio | basso |
| 8 | Convertire i 53 `TRY400` in `logger.exception` | medio | basso |
| 9 | Migrare `BrokerSharingPanel.svelte` (20 `$:`) alle Runes | medio | medio |

**I primi quattro interventi si completano in meno di un'ora e non possono rompere nulla**
(il quinto è già fatto). Insieme risolvono l'unico rischio legale dell'audit, l'unico bug
latente e l'unica violazione della Async I/O Rule.

Se l'audit producesse un solo risultato, dovrebbe essere questo elenco.
