# 06 — Database & Models

> `backend/app/db/` (4 file, 1 264 righe), `backend/alembic/`
> Gravità massima: 🟡

---

## Sintesi

Il livello dati è il più piccolo del backend e il meno problematico: **8 rilievi ruff in
1 264 righe**. Non ci sono funzioni sopra soglia di complessità, non c'è codice
irraggiungibile.

Il valore di questo report sta altrove: è qui che si concentrano i **falsi positivi** più
istruttivi degli strumenti automatici. Le 12 rilevazioni "al 100 % di confidenza" di
vulture su `models.py` sono **tutte** false, e capire perché è più utile che rimuoverle.

L'unico reperto reale è una coppia di property del modello che nessuno usa — mentre la
loro logica viene riscritta a mano in sei punti diversi fra backend e frontend.

---

## Metriche

| File | Righe | Rilievi ruff |
|---|---:|---:|
| `db/models.py` | 1 004 | 5 |
| `db/session.py` | 154 | 1 |
| `db/base.py` | 53 | 1 |
| `db/__init__.py` | 53 | 1 |
| **Totale** | **1 264** | **8** |

Migrazioni Alembic: **2** (`001_initial.py`, `002_identifier_other_json_list.py`).

Funzioni sopra soglia di complessità: **0**.

---

## Reperti

### 🟡 F1 — `is_chain` e `providers_used`: DRY scritto e mai usato

**Dove**: `backend/app/db/models.py:903` e `:909`

```python
@property
def is_chain(self) -> bool:
    """True if this route has more than 1 step (multi-step chain)."""
    return len(self.parsed_steps) > 1

@property
def providers_used(self) -> set[str]:
    """Set of provider codes used in this route's chain."""
    return {step["provider"] for step in self.parsed_steps}
```

Entrambe referenziate **solo** da `test_model_validators.py` (righe 236-244).

> **Tracciatura della logica** — questo è il caso più interessante dell'audit, perché la
> logica **non è né persa né assorbita: è duplicata a mano**.

`is_chain` viene ricalcolato inline nel frontend:

| Dove | Codice |
|---|---|
| `FxPairAddModal.svelte:113` | `!(i.chain_steps?.length === 1 && i.chain_steps[0].provider === 'MANUAL')` |
| `fx/[pair]/+page.svelte:670` | stessa espressione, ripetuta |
| `FxProviderConfig.svelte:75,219,240` | `chainSteps.length > 1` — **ma il file è morto**, vedi [09](09_frontend_components.md) reperto I1 |

`providers_used` viene ricalcolato inline nel backend:

| Dove | Codice |
|---|---|
| `fx.py:1000` | `[s["provider"] for s in steps if s["provider"].upper() != "MANUAL"]` |
| `fx.py:1108` | `[s["provider"] for s in steps]` |

Da notare che le due versioni inline in `fx.py` **non sono equivalenti fra loro** (una
filtra `MANUAL`, l'altra no) e **nessuna delle due** è equivalente alla property del
modello (che restituisce un `set`, non una `list`). Tre semantiche leggermente diverse
per lo stesso concetto.

Lato frontend la situazione è analoga: la regola "catena = più di uno step" è scritta a
mano in `FxPairAddModal.svelte:113` e in `fx/[pair]/+page.svelte:670` con un'espressione
identica, copiata.

Per contrasto, `parsed_steps` — la property su cui entrambe si appoggiano — è usata in
**8 punti di produzione** (`api/v1/fx.py:875,990,995`, `portfolio_service.py:991`,
`fx.py:832,938,952`). La property base è viva; le due derivate no.

**Rimedio**: non rimuoverle. Usarle.
- Backend: sostituire i due list comprehension in `fx.py` con `route.providers_used`,
  decidendo esplicitamente se `MANUAL` va incluso (verosimilmente serve una seconda
  property `real_providers_used`).
- Frontend: esporre `is_chain` nella risposta API, così il client smette di reimplementare
  la regola "più di uno step = catena". Oggi quella regola vive in tre posti vivi (più uno
  morto); se domani diventasse "più di uno step non-MANUAL", andrebbe corretta in tutti.

---

### 🟢 F2 — I 12 "100 % confidenza" di vulture sono tutti falsi positivi

Vulture segnala 12 variabili inutilizzate al massimo livello di confidenza in
`models.py`:

```
backend/app/db/models.py:353: unused variable 'cls' (100% confidence)
backend/app/db/models.py:526: unused variable 'cls' (100% confidence)
backend/app/db/models.py:532: unused variable 'cls' (100% confidence)
... (righe 543, 551, 556, 704, 750, 799, 841, …)
```

Sono tutte lo stesso caso: il parametro `cls` dei **validator Pydantic**.

```python
@field_validator("...")
def validate_something(cls, v):   # ← cls non usato nel corpo
    ...
```

La firma è imposta dal decoratore: Pydantic invoca il validator come classmethod e passa
`cls` sempre, che serva o no. Rimuoverlo romperebbe la validazione.

**Questo è il dato più importante sull'affidabilità degli strumenti in questo audit**: la
"confidenza 100 %" di vulture significa *"sintatticamente certo che il simbolo non è
letto"*, non *"certo che sia rimuovibile"*. Su un codebase pieno di framework
dichiarativi, le due cose divergono sistematicamente.

Sono già coperti dalla configurazione `[tool.vulture]` in `pyproject.toml`; nessun
intervento necessario. Vengono documentati qui perché ricompariranno ad ogni nuovo scan.

---

### 🟢 F3 — 3 `ARG001` su listener SQLAlchemy — falsi positivi anch'essi

```
backend/app/db/models.py:1002:27: ARG001 Unused function argument: `mapper`
backend/app/db/models.py:1002:35: ARG001 Unused function argument: `connection`
backend/app/db/session.py:21:35:  ARG001 Unused function argument: `connection_record`
```

Firme di event listener SQLAlchemy (`@event.listens_for`). Il contratto impone la firma
completa; gli argomenti non usati vanno tenuti.

**Rimedio (opzionale)**: rinominarli con prefisso underscore (`_mapper`, `_connection`)
per silenziare la regola documentando l'intenzione, oppure aggiungere un `# noqa: ARG001`
mirato. La prima è preferibile perché è auto-esplicativa.

---

### 🟢 F4 — `N805` su `models.py:556`

```
backend/app/db/models.py:556:40: N805 First argument of a method should be named `self`
```

Stessa famiglia di F2: è un validator Pydantic con `cls`. Falso positivo della regola di
naming, che non riconosce il decoratore.

---

### 🟢 F5 — 2 `RUF022` (`__all__` non ordinato) e 2 `RUF100`

- `db/__init__.py:29` e `db/base.py:32` — liste `__all__` non in ordine alfabetico.
- `models.py:52` e `models.py:558` — direttive `# noqa: PLC0415` inutili, perché la regola
  `PLC0415` non è abilitata nella configurazione del progetto.

Entrambe correggibili automaticamente. I `RUF100` rientrano negli autofix della Fase F;
l'ordinamento di `__all__` è cosmetico e va valutato se si vuole renderlo permanente
(altrimenti riemergerà ad ogni aggiunta di modello).

---

### 🟢 F6 — Alembic: solo 2 migrazioni

`001_initial.py` e `002_identifier_other_json_list.py`.

Coerente con la regola di progetto: le tabelle mai rilasciate si modificano in
`001_initial.py`, le altre richiedono una migrazione incrementale. Con la 1.0.1 già
distribuita, ogni cambio di schema da qui in avanti deve produrre un `003_*`.

Nessun rilievo. Vale però la pena di verificare, prima della 1.1.0, che
`002_identifier_other_json_list.py` sia effettivamente applicabile su un database 1.0.1
popolato — è l'unica migrazione che gli utenti esistenti eseguiranno.

---

## Interventi raccomandati

| Priorità | Intervento | Costo | Rischio |
|---|---|---|---|
| 1 | Verificare `002_identifier_other_json_list.py` su un DB 1.0.1 reale | basso | — |
| 2 | Usare `providers_used` in `fx.py:1000,1108`, chiarendo la semantica `MANUAL` | basso | basso |
| 3 | Esporre `is_chain` via API e togliere il calcolo inline dal frontend | medio | basso |
| 4 | Prefissare con `_` gli argomenti dei listener SQLAlchemy | basso | nullo |
| 5 | Rimuovere i 2 `RUF100` (autofix) | nullo | nullo |

L'intervento 1 non nasce dall'audit del codice ma dal contesto di release: è l'unica
migrazione che toccherà installazioni esistenti, e vale più di qualunque pulizia stilistica.

Gli interventi 2 e 3 non riducono le righe di codice — le spostano. Il guadagno è che la
definizione di "catena" torna a esistere in un posto solo.
