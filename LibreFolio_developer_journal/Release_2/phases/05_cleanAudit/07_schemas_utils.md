# 07 — Schemi & Utility

> `backend/app/schemas/` (22 file, 11 202 righe), `backend/app/utils/` (15 file, 2 116),
> `backend/app/core/`
> Gravità massima: 🟡

---

## Sintesi

Qui si concentra la maggior parte del codice inutilizzato del backend: **9 classi Pydantic
mai referenziate**, **11 property di comodo mai chiamate**, e tre gruppi di funzioni di
utilità orfane.

Ma il conteggio è fuorviante. Analizzando ogni reperto emergono **tre storie diverse**,
che richiedono tre risposte diverse:

1. **Comodità scritte e mai adottate** — property che convertono un valore grezzo in un
   oggetto tipizzato, mentre il codice di produzione fa la stessa conversione a mano. La
   logica non è morta, è *duplicata*.
2. **Schemi scritti e mai cablati** — classi di richiesta/risposta che avrebbero dovuto
   comparire negli endpoint e non ci sono mai arrivate. Si collegano direttamente ai
   17 endpoint senza `response_model` del report [01](01_api_layer.md).
3. **Una funzionalità mancante** — `merge_other_identifiers` implementa una semantica di
   import *additiva* che il codice di produzione non applica da nessuna parte.

Solo il terzo caso è potenzialmente un problema funzionale.

---

## Metriche

| Area | File | Righe |
|---|---:|---:|
| `schemas/` | 22 | 11 202 |
| `utils/` | 15 | 2 116 |

**Simboli inutilizzati**: 9 classi, 11 property/metodi, 6 funzioni.

File con più rilievi ruff: `transactions.py` (8), `signals.py` (7), `prices.py` (6),
`fx.py` (6), `assets.py` (6).

---

## Reperti

### 🟡 G1 — 11 property di conversione: DRY scritto, mai adottato

**Dove**: `schemas/prices.py:171-186,292`, `schemas/common.py:263,325,601`,
`schemas/brokers.py:200,205`, `schemas/fx.py:167`

```python
@property
def close_cur(self) -> Currency:
    """Get close price as Currency object for internal calculations."""
    return Currency(code=self.currency, amount=self.close)
```

Undici property dello stesso stampo (`close_cur`, `open_cur`, `high_cur`, `low_cur`,
`value_cur`, `conversion_date_str`, `actual_rate_date_str`, `to_dict`, `failed_count`,
`total_cash_positions`, `total_asset_positions`), nessuna con chiamanti di produzione.

> **Tracciatura della logica**: esattamente come `is_chain` nel report
> [06](06_db_models.md), **la logica non è persa: è riscritta a mano**. La costruzione
> `Currency(code=…, amount=…)` compare inline in almeno otto punti:
>
> `transactions.py:476,486` · `broker_service.py:386,426,429,439` ·
> `brim_providers/broker_fineco.py:357`

Il pattern è ricorrente in tutto il progetto e merita un nome: **DRY orfano**. Qualcuno
scrive l'astrazione corretta, poi chi implementa non la trova (o non sa che esiste) e
riscrive l'espressione a mano. Il risultato è il peggiore dei due mondi: la duplicazione
resta *e* si accumula codice non usato.

**Rimedio**: due strade opposte, entrambe accettabili — l'importante è sceglierne una.

- **Adottare**: sostituire le costruzioni inline con le property. Costo basso, riduce la
  duplicazione, elimina 11 reperti.
- **Rimuovere**: cancellare property e relativi test, accettando la costruzione esplicita
  come stile del progetto.

La prima è preferibile per le property che incapsulano una regola (`failed_count`,
`total_cash_positions`), la seconda per quelle puramente sintattiche.

---

### 🟡 G2 — 9 classi Pydantic mai referenziate

| Classe | File:riga |
|---|---|
| `AuthPasswordResetRequest` | `schemas/auth.py:34` |
| `AuthErrorResponse` | `schemas/auth.py:116` |
| `FXPairsListResponse` | `schemas/fx.py:503` |
| `PortfolioSummaryQuery` | `schemas/portfolio.py:81` |
| `PortfolioHistoryQuery` | `schemas/portfolio.py:91` |
| `AllocationHistoryQuery` | `schemas/portfolio.py:299` |
| `AllocationHistoryResponse` | `schemas/portfolio.py:310` |
| `FAEventDeleteResult` | `schemas/prices.py:401` |
| `WACConversionInfo` | `schemas/wac.py:24` |

> **Tracciatura**: nessuna logica da assorbire — sono contenitori di dati, non
> comportamento. Ma la loro assenza ha una **conseguenza concreta**: i `*Response`
> corrispondono a endpoint privi di `response_model`, quindi il client TypeScript
> generato da OpenAPI **non ha i tipi** per quelle risposte. Il frontend riceve `any`.

Il collegamento è diretto: il report [01](01_api_layer.md) conta **17 endpoint su 97
senza `response_model`**. Le classi `AllocationHistoryResponse`, `FXPairsListResponse` e
`AuthErrorResponse` sono esattamente i tipi mancanti di alcuni di quegli endpoint.

Le classi `*Query` raccontano la storia opposta: sono state scritte per raggruppare i
parametri di query in un unico modello, ma gli endpoint li dichiarano ancora uno per uno
nella firma.

**Rimedio**: **cablarle**, non rimuoverle. Aggiungere `response_model=…` agli endpoint
corrispondenti e rieseguire `./dev.py api sync` restituisce i tipi al frontend. È
l'intervento con il miglior rapporto valore/rischio del report — non tocca la logica, e
il beneficio (tipizzazione end-to-end) è quello per cui Zodios è stato adottato.

`AuthPasswordResetRequest` va invece verificata a parte: se il reset password non è
implementato, è uno schema in attesa di funzionalità.

---

### 🟡 G3 — `merge_other_identifiers`: semantica additiva non applicata

**Dove**: `backend/app/utils/identifier_utils.py:51`

```python
def merge_other_identifiers(existing: Any, new: Any) -> Optional[List[str]]:
    """Additively merge two soft-identifier inputs, de-duplicated, existing first.

    Used when new labels for an already-known asset must be *added* rather than
    replace the current ones (the additive import semantics).
    """
```

> **Tracciatura — questo è il reperto da discutere.** Il docstring descrive un requisito
> preciso: durante l'import, i nuovi identificativi di un asset già noto vanno
> **aggiunti**, non sostituiti. Ma in produzione l'unico uso degli identificativi passa
> da `normalize_other_identifiers` (`db/models.py:553`), che ha semantica di
> **sostituzione**.

La funzione additiva non è chiamata da nessuna parte al di fuori dei test. Le
interpretazioni possibili sono due, e portano a conclusioni opposte:

- **La semantica additiva è un requisito reale e non è implementata** → è un difetto
  funzionale: importando due volte lo stesso asset da broker diversi, il secondo import
  cancella gli identificativi del primo.
- **La semantica additiva è stata abbandonata** → la funzione e il suo docstring sono
  fuorvianti e vanno rimossi.

Non è determinabile dal codice: dipende da cosa deve succedere quando lo stesso asset
arriva da due sorgenti. **Va deciso con chi conosce il requisito di import.**

Nel frattempo vale la pena verificare empiricamente il comportamento attuale: importare
lo stesso asset da due broker con identificativi diversi e osservare se il secondo
sovrascrive il primo.

---

### 🟢 G4 — `cache_utils`: tre funzioni di gestione cache senza interfaccia

**Dove**: `utils/cache_utils.py:120,129,169` — `clear_cache`, `clear_all_caches`,
`list_caches`

> **Tracciatura**: non esiste alcun endpoint amministrativo di gestione cache. La logica
> non è duplicata altrove — semplicemente **non c'è modo di invocarla**.

Sono l'infrastruttura di una funzionalità mai esposta. Le opzioni:

- Esporre un endpoint admin `POST /admin/cache/clear` + `GET /admin/cache` — utile in
  produzione quando un prezzo resta bloccato in cache e serve forzare il refresh senza
  riavviare il container;
- Rimuoverle.

La prima ha valore operativo concreto: oggi l'unico modo per invalidare una cache è
riavviare il servizio.

---

### 🟢 G5 — `settings_service` e `global_settings_service`: due servizi sovrapposti

**Dove**: `settings_service.py:224,234` — `get_session_ttl_sync`, `get_session_ttl`

> **Tracciatura**: **assorbite**. `global_settings_service.get_session_ttl_hours` è la
> versione viva, usata da `auth.py:128`. Le due varianti in `settings_service` sono i
> residui della migrazione.

Il problema più ampio è che esistono **due servizi di impostazioni** (242 + 102 righe)
con responsabilità sovrapposte. Chi aggiunge un'impostazione oggi deve indovinare quale
usare.

**Rimedio**: rimuovere le due funzioni assorbite (rischio nullo, sostituto verificato) e
poi decidere se consolidare i due servizi in uno. Il secondo passo è più invasivo e va
pianificato a parte.

Vedi anche il report [02](02_services_core.md), reperto B4, per il problema correlato di
`is_registration_enabled` — un'impostazione dichiarata, esposta nell'interfaccia, ma mai
applicata.

---

### 🟢 G6 — `version.get_version_info` usata solo dal test runner

**Dove**: `backend/app/utils/version.py:56`

L'unico riferimento fuori dai test è in `scripts/test_runner/_backend_utils.py:154`, che
è **infrastruttura di test**, non produzione.

> **Tracciatura**: nessuna duplicazione trovata. La versione mostrata all'utente arriva
> per altre vie.

Candidata alla rimozione, ma prima vale la pena verificare se un endpoint `/version` o un
banner di avvio dovrebbero usarla — con la 1.1.0 in uscita, esporre la versione è una
richiesta plausibile.

---

## Interventi raccomandati

| Priorità | Intervento | Costo | Rischio |
|---|---|---|---|
| 1 | **Decidere su `merge_other_identifiers`**: requisito reale o abbandonato | — | — |
| 2 | Cablare le classi `*Response` come `response_model` + `./dev.py api sync` | basso | basso |
| 3 | Rimuovere `get_session_ttl`/`get_session_ttl_sync` (assorbite) | basso | nullo |
| 4 | Decidere sulle 11 property: adottare o rimuovere | basso | basso |
| 5 | Esporre un endpoint admin per `cache_utils`, o rimuoverlo | medio | basso |
| 6 | Verificare se `get_version_info` va esposta con la 1.1.0 | basso | nullo |
| 7 | Valutare il consolidamento dei due `*settings_service` | alto | medio |

L'intervento 1 è l'unico che potrebbe nascondere un difetto funzionale con impatto sui
dati degli utenti, ed è quello su cui serve la decisione prima di toccare qualsiasi cosa.

L'intervento 2 è il più redditizio: ripristina la tipizzazione end-to-end che è la ragione
per cui il progetto usa Zodios.
