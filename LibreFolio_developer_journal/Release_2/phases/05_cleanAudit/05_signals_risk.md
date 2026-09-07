# 05 — Signal & Risk Analytics

> `signal_plugins/` (24 file, 4 786 righe), `signal_service.py`, `schemas/signals.py`,
> `risk/` + `risk_plugins/` (28 file, 6 117 righe), `schemas/risk.py`
> Gravità massima: 🟡

---

## Sintesi

I due sottosistemi più recenti del progetto — 22 signal plugin e 9 analitiche di rischio
— sono anche i più puliti sul piano del codice morto: **un solo simbolo inutilizzato in
10 900 righe**. Il pattern a plugin con registry, riusato dai provider, funziona.

Il debito qui non è nel codice esecutivo ma nei **validatori degli schemi**. Sei delle
dieci funzioni più complesse del sottosistema sono metodi `validate_*` di Pydantic, con
`validate_status_matrix` a complessità 32 — la funzione più complessa dell'intero
livello schemi.

Questo audit ha anche prodotto un **falso positivo istruttivo** (reperto E2) che vale la
pena registrare per i prossimi cicli.

---

## Metriche

| Area | File | Righe |
|---|---:|---:|
| `signal_plugins/` | 24 | 4 786 |
| `risk/` + `risk_plugins/` | 28 | 6 117 |

### Funzioni sopra soglia

| Complessità | Funzione | File |
|---:|---|---|
| **32** | `validate_status_matrix` | `schemas/signals.py:1058` |
| 17 | `validate_definition` | `services/risk/base.py:176` |
| 15 | `validate_context` | `schemas/risk.py:519` |
| 15 | `validate_episode_contract` | `schemas/risk.py:1035` |
| 15 | `validate_dimensions` | `risk/quant/models.py:36` |
| 15 | `drawdown_episodes` | `risk/metrics.py:259` |
| 14 | `validate_coverage` | `schemas/signals.py:759` |
| 13 | `validate_alignment` | `schemas/risk.py:434` |
| 11 | `current_buy_and_hold_returns` | `risk/metrics.py:496` |
| 11 | `run_optimization` | `risk/quant/optimization_engine.py:50` |

**Otto su dieci sono validatori.** Solo `drawdown_episodes`, `current_buy_and_hold_returns`
e `run_optimization` sono logica di calcolo.

I file con più rilievi ruff: `signal_plugins/base.py` (10), `signal_service.py` (8),
`obv.py` (7), `risk/scenario_catalog/loader.py` (7), `schemas/signals.py` (7).

---

## Reperti

### 🟡 E1 — `validate_status_matrix`: complessità 32 in un validatore

**Dove**: `backend/app/schemas/signals.py:1058`

```python
def validate_status_matrix(self) -> SignalResult:
    if self.series:
        _validate_series_alignment(self.series)

    if self.status == SignalStatus.OK:
        if self.availability is None or self.warmup is None:
            raise ValueError("ok result requires availability and warm-up metadata")
        if not self.series:
            raise ValueError("ok result requires series")
        if not self.availability.can_compute or not self.warmup.complete:
            raise ValueError("ok result requires computable input and complete warm-up")
        ...
```

Il nome è onesto: è letteralmente una **matrice di stati**, e ogni stato
(`OK`, `PARTIAL`, `UNAVAILABLE`, …) ha il suo blocco di invarianti. La complessità è
intrinseca al dominio, non accidentale.

Ma una matrice espressa come catena di `if` annidati ha due difetti pratici: è difficile
verificare che tutti gli stati siano coperti, ed è difficile capire *quale* regola è
stata violata quando fallisce.

**Rimedio suggerito**: rendere la matrice dichiarativa — un dizionario
`{status: [lista di invarianti]}` dove ogni invariante è una coppia
`(predicato, messaggio)`, e un unico loop che le applica. Il numero di regole non cambia,
ma diventano ispezionabili, testabili singolarmente ed elencabili.

Non urgente: il validatore funziona ed è invocato ad ogni costruzione di `SignalResult`.
È un candidato di qualità, non di correttezza.

---

### 🟡 E2 — Falso positivo dell'audit: `resolve_ai_export_temporal_class`

**Dove**: `backend/app/services/signal_plugins/base.py:120`

Lo scan iniziale l'aveva classificata come *usata solo dai test*. **È sbagliato.**

> **Tracciatura**: la funzione è chiamata in produzione da
> `ai_export/components/technical_shared.py:943`. Non è emersa perché
> `backend/app/services/ai_export/**` è **escluso dall'audit** su richiesta — è in
> carico a un altro agente. Escludendo il consumatore, il produttore appare orfano.

Nessun intervento sul codice. Ma la lezione va registrata:

> **Regola per i prossimi audit**: quando si esclude una directory dallo scan, i simboli
> che *quella* directory consuma appaiono falsamente morti. L'esclusione va applicata
> alla **reportistica**, non alla **raccolta dei riferimenti**.

Questa è la stessa classe di errore già corretta in fase preparatoria con `scripts/`:
le funzioni di `user_service` sembravano morte finché non si è incluso `scripts/user_cli.py`
nello scope di produzione. Due occorrenze dello stesso errore metodologico in un solo
audit — vale la pena scriverlo nella skill.

---

### 🟢 E3 — `unique_computation_count` usata solo dai test

**Dove**: `backend/app/services/signal_service.py:127`

```python
@property
def unique_computation_count(self) -> int:
    return len(self.computations)
```

Verificata in tutto il repository (backend, `scripts/`, frontend, **incluso** ai_export):
zero riferimenti di produzione. Usata in `test_signal_service.py:342` e
`test_signal_plugin_matrix.py:309`.

> **Tracciatura della logica**: la property *è* `len(self.computations)`. Il campo
> `computations` è pubblico e vivo. **Nessuna logica andrebbe persa** rimuovendola: i
> test possono scrivere `len(plan.computations)` ottenendo lo stesso identico risultato.

È l'unico caso dell'audit in cui la rimozione è banale e priva di conseguenze: si
elimina la property e si aggiornano due asserzioni. Se invece si preferisce tenerla come
API leggibile del piano di calcolo, basta un commento — ma allora andrebbe usata anche
in produzione, per esempio nei log diagnostici del signal service, dove "quante
computazioni uniche ha prodotto questo piano" è esattamente l'informazione utile.

---

### 🟢 E4 — Nessun altro codice morto in 10 900 righe

Vale la pena dirlo esplicitamente, perché è il risultato migliore dell'audit: sui 22
signal plugin e sulle 9 analitiche di rischio, gli scan non hanno prodotto **alcun**
reperto di codice inutilizzato oltre a E3.

Il motivo è strutturale: i plugin sono raggiunti via registry con auto-discovery e ogni
metodo pubblico fa parte di un contratto astratto. Non c'è spazio perché si accumuli
codice orfano — se un metodo non serve al contratto, non viene scritto.

È la conferma che il pattern a plugin, oltre a scalare, **si autopulisce**.

---

### 🟢 E5 — `risk/scenario_catalog/loader.py`: 7 rilievi

Il caricatore del catalogo scenari concentra 7 rilievi ruff, principalmente della
famiglia `TRY` (gestione eccezioni) e `SIM`. È il punto in cui si leggono definizioni da
file esterni, quindi la gestione errori è legittimamente ramificata.

`validate_definition` (`risk/base.py:176`, complessità 17) è il validatore corrispondente
lato servizio. Stessa osservazione di E1: complessità di dominio, non accidentale.

---

## Interventi raccomandati

| Priorità | Intervento | Costo | Rischio |
|---|---|---|---|
| 1 | Registrare nella skill la regola sugli esclusi (E2) | nullo | nullo |
| 2 | Rimuovere `unique_computation_count` **o** usarla nei log diagnostici | basso | nullo |
| 3 | Ripulire i rilievi `TRY`/`SIM` in `loader.py` e `obv.py`/`mfi.py` | basso | basso |
| 4 | Rendere dichiarativa la matrice di `validate_status_matrix` | medio | medio |
| 5 | Valutare la stessa trasformazione per i validatori di `schemas/risk.py` | medio | medio |

Gli interventi 4 e 5 sono miglioramenti di leggibilità su codice che funziona. Vanno
affrontati solo se e quando quei validatori diventeranno un ostacolo — per esempio
all'aggiunta di un nuovo `SignalStatus`.

**Nota**: questo sottosistema è quello introdotto più di recente (Risk Analysis è in beta
nella 1.1.0). Che sia già il più pulito è un dato positivo, ma va riverificato fra
qualche release: la pulizia del codice giovane è la norma, mantenerla è il risultato.
