# Step 1 — Quant Foundation (P0)

**Stato**: ✅ COMPLETATO — 27 Luglio 2026; 🔁 RIVALUTATO E RI-CHIUSO —
28 Luglio 2026.

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

> **⚠️ Revisione 28 Luglio 2026**: la conclusione sopra era specifica a
> Riskfolio-Lib 7.3.0 e alla sua dipendenza packaging `vectorbt`. Rivalutato
> Riskfolio-Lib **7.0.1** con Python 3.13 + NumPy **2.5.1**: host macOS arm64 e
> container Linux arm64/amd64 verdi; `vectorbt` e `numba` assenti; CLARABEL
> completa min-risk, max-Sharpe, risk parity, covariance `hist`/Ledoit/OAS,
> bound lineari, frontiera e infeasible detection. RSS massima del probe:
> ~256 MiB host, ~288 MiB arm64, ~352 MiB amd64 emulato.

### 1.4 — Docker/CI/costo

**Stato**: ✅ COMPLETATO — 27 Luglio 2026; 🔁 REVISIONATO — 28 Luglio 2026.

Misurare:

- lock riproducibile;
- build image;
- delta dimensione immagine;
- delta durata build;
- comportamento release workflow;
- piattaforme realmente supportate.

> **Note implementazione — revisione**: probe wheel/container arm64+amd64 verdi;
> QuantLib aggiunge 86,8–89,4 MiB; Riskfolio 7.0.1 oltre QuantLib aggiunge
> 644,4 MiB arm64 / 672,9 MiB amd64. Il build LibreFolio finale arm64
> `librefolio:g5-quantlib-riskfolio-final` è verde: 2.756.004.428 byte, digest
> `sha256:fd8d79d6584dd7cf8087f54508f8c73cc66bbcacebe5a206bf46821117bd7999`.
> Smoke container: QuantLib 1.43, NumPy 2.5.1, Riskfolio 7.0.1, FastAPI app,
> nessun `vectorbt`/`numba`.

> **⚠️ Fuori pista**: un primo `pipenv lock` aveva aggiornato dipendenze
> transitive `*`; recuperato il preimage automatico della sessione e ricostruito
> il lock aggiungendo QuantLib e la sola closure Riskfolio 7.0.1 sulla baseline.

### 1.5 — Decisione e adozione

**Stato**: ✅ RIVALUTATO E COMPLETATO — 28 Luglio 2026.

Per ogni libreria:

- `ADOPTED` → manifest, lock, Docker, CI e smoke test;
- `REJECTED` → fallback esplicito, nessuna traccia runtime;
- `PARTIAL` → capability precise + adapter/fallback preciso.

> **Note implementazione**: decisione fissata: QuantLib `ADOPTED`, RQMC QuantLib
> `PARTIAL` con fallback SciPy, Riskfolio `REJECTED` per Release 2. Manifest,
> lock, smoke host e smoke container completati. P13 è chiuso senza
> dipendenze/endpoint/UI morti.

> **Note implementazione — revisione**: Riskfolio-Lib **7.0.1 ADOPTED** e pinata
> nel runtime. Il lock mantiene NumPy **2.5.1** anche nella sezione develop e
> aggiunge solo il closure transitivo Riskfolio; nessun `vectorbt`, nessun
> `numba`. La precedente decisione `REJECTED` è superseded. RQMC viene rimosso
> dal prodotto: P11 production espone soltanto QuantLib MC/QMC. P13 è riaperto
> come analytic backend senza UI in questo round.

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

- QuantLib non installabile → stop del gate; nessun adapter production alternativo.
- QMC QuantLib non conforme agli oracle → stop e confronto utente, nessun
  fallback production silenzioso.
- Riskfolio 7.0.1 incompatibile → stop e confronto utente, nessun cambio
  versione/downgrade NumPy silenzioso.
- Nessuna soglia arbitraria nascosta: trade-off registrato nel report.

## 8. Progress rule

Dopo ogni task aggiornare stato/data/note/fuori-pista qui e nel master.
