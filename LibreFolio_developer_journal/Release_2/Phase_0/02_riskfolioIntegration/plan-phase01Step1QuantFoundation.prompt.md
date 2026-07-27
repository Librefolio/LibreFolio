# Step 1 — Quant Foundation (P0)

**Stato**: ✅ COMPLETATO — 27 Luglio 2026; Gate G1 chiuso.

← Master:
[`plan-phase01RiskAnalysisImplementation.prompt.md`](./plan-phase01RiskAnalysisImplementation.prompt.md)

→ Step successivo:
[`plan-phase01Step2CanonicalSeriesMetadata.prompt.md`](./plan-phase01Step2CanonicalSeriesMetadata.prompt.md)

## 1. Obiettivo

Verificare QuantLib e Riskfolio-Lib nell'ambiente reale LibreFolio e adottare
definitivamente solo le capability che superano il gate Python 3.13, Docker, CI,
API e costo operativo.

## 2. Baseline

- Python 3.13 in Pipenv, Docker e CI.
- NumPy/pandas/SciPy già lockati.
- QuantLib, Riskfolio-Lib e CVXPY assenti.
- Docker genera `requirements.txt` dal `Pipfile.lock`.
- P11 dipende dalla decisione QuantLib; P13 dalla decisione Riskfolio.

## 3. Task

### 1.1 — Harness e fixture

**Stato**: ✅ COMPLETATO — 27 Luglio 2026.

Creare:

- `scripts/spikes/risk/`;
- fixture deterministiche sotto `backend/test_scripts/fixtures/risk/`;
- artefatto `spike-phase01QuantLibraries.md`.

Harness deve stampare versioni, API disponibili, solver, seed, shape, tempo e
memoria senza diventare codice production.

> **Note implementazione**: creati harness JSON, fixture deterministica, README e
> Dockerfile probe riproducibili per arm64/amd64. Il report è
> [`spike-phase01QuantLibraries.md`](./spike-phase01QuantLibraries.md).

> **⚠️ Fuori pista**: il binding SWIG richiede di mantenere vivi generatori e
> `sample` fino alla copia in strutture Python; la regola è codificata nel probe.

### 1.2 — Probe QuantLib

**Stato**: ✅ COMPLETATO — 27 Luglio 2026.

Verificare:

- wheel/build su Python 3.13 locale e container;
- import/versione/licenza;
- processo GBM;
- path single e multi-asset;
- Mersenne Twister, Sobol, gaussianizzazione;
- scrambling/RQMC esposto dal binding;
- calendar/day counter/curve;
- bond duration/convexity;
- riproducibilità e serializzabilità del boundary.

> **Note implementazione**: QuantLib 1.43 verde su macOS/Python 3.13 e Linux
> arm64/amd64. Verificati pseudo/QMC/RQMC, single/multi-path, curve/calendari,
> duration/convexity e seed deterministico. RQMC è `PARTIAL`: sequenze Burley
> disponibili, path-generator specializzato assente.

### 1.3 — Probe Riskfolio-Lib

**Stato**: ✅ COMPLETATO — 27 Luglio 2026.

Verificare:

- install/import/versione/licenza;
- dipendenze transitive e conflitti;
- solver open-source disponibili;
- min-risk/max-Sharpe/risk-parity su fixture;
- determinismo/tolleranze;
- timeout/costo avvio.

> **Note implementazione**: Riskfolio-Lib 7.3.0 funziona con NumPy 2.4.6;
> min-risk, max-Sharpe e risk parity sono ripetibili, con cinque solver
> open-source disponibili. Gate respinto: NumPy `<2.5`, circa 1 GiB di layer
> aggiuntivo e warning CVXPY deprecati.

### 1.4 — Docker/CI/costo

**Stato**: ✅ COMPLETATO — 27 Luglio 2026.

Misurare:

- lock riproducibile;
- build image;
- delta dimensione immagine;
- delta durata build;
- comportamento release workflow;
- piattaforme realmente supportate.

> **Note implementazione**: probe wheel/container arm64+amd64 verdi; QuantLib
> aggiunge 86,8–89,4 MiB, lo stack Riskfolio 1.065–1.098 MiB. Lock minimale
> verificato. Il build LibreFolio finale è verde; immagine arm64
> `librefolio:v1.0.1-15-g8346fdc7-dirty` di 2.433.002.858 byte, con import
> container di QuantLib 1.43 riuscito.

> **⚠️ Fuori pista**: un primo `pipenv lock` aveva aggiornato dipendenze
> transitive `*`; recuperato il preimage automatico della sessione e ricostruito
> il lock aggiungendo esclusivamente QuantLib.

### 1.5 — Decisione e adozione

**Stato**: ✅ COMPLETATO — 27 Luglio 2026.

Per ogni libreria:

- `ADOPTED` → manifest, lock, Docker, CI e smoke test;
- `REJECTED` → fallback esplicito, nessuna traccia runtime;
- `PARTIAL` → capability precise + adapter/fallback preciso.

> **Note implementazione**: decisione fissata: QuantLib `ADOPTED`, RQMC QuantLib
> `PARTIAL` con fallback SciPy, Riskfolio `REJECTED` per Release 2. Manifest,
> lock, smoke host e smoke container completati. P13 è chiuso senza
> dipendenze/endpoint/UI morti.

## 4. File candidati

- `Pipfile`, `Pipfile.lock`, `pyproject.toml`;
- `requirements.txt` generato;
- `Dockerfile`;
- `.github/workflows/manual-test-run.yml`;
- `.github/workflows/release.yml`;
- `scripts/spikes/risk/`;
- `backend/test_scripts/test_services/test_risk/`.

## 5. Test e comandi

- probe locale Pipenv;
- `./dev.py install` solo dopo modifica manifest;
- smoke pytest mirato;
- `./dev.py test all-backend`;
- `./dev.py docker build`.

## 6. Gate G1

Completato quando:

- decisione per entrambe le librerie è riproducibile;
- dipendenze adottate sono lockate/importabili nel container;
- CI/smoke verdi;
- fallback P11/P13 determinato;
- impatto Docker registrato.

## 7. Rischi/fallback

- QuantLib non installabile → NumPy/SciPy adapter.
- RQMC non wrappato → `scipy.stats.qmc`.
- Riskfolio troppo pesante/incompatibile → P13 non spedito.
- Nessuna soglia arbitraria nascosta: trade-off registrato nel report.

## 8. Progress rule

Dopo ogni task aggiornare stato/data/note/fuori-pista qui e nel master.
