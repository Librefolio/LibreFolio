# F1 — Dati di prova che riempiono il pannello

> **Fase 1 · fondamenta.** Gira insieme a F2 e a nient'altro.
> **Sessione**: N `e-alfy-risk-n-backend-acquisizioni` (riuso)
> **Baseline**: `2ec19b8f0` — **verificala prima di leggere oltre**
> **Corsia**: `--test-port 6151` · `--data-dir /tmp/librefolio-r2-f1`

---

## 1. Perché questo mandato è il primo di tutti

Il 18 settembre il coordinatore ha guidato l'app con il DB di test seminato, e **metà del
pannello rischio non poteva mostrare niente**. Non per un difetto dell'interfaccia: perché
il portafoglio di prova non ha abbastanza storia perché le analitiche calcolino.

Finché questo non è risolto, **ogni mandato di superficie svilupperebbe e verificherebbe sul
vuoto**, e ogni review misurerebbe l'assenza invece dell'interfaccia.

---

## 2. Cosa è stato misurato — e con quali comandi

Tutto ciò che segue è misurato sul DB prodotto da
`dev.py test --test-port 6150 db populate --force --clean`, il 18 Set 2026.

### 2.1 La storia esiste, ma non dove serve

```sql
SELECT COUNT(*), COUNT(DISTINCT date) FROM price_history;
-- 1 549 righe · 373 date distinte · 2025-09-11 → 2026-09-18
```

```sql
SELECT t.asset_id, COUNT(*), (SELECT COUNT(*) FROM price_history p WHERE p.asset_id=t.asset_id)
FROM transactions t GROUP BY t.asset_id;
```

| asset | transazioni | punti prezzo | |
|---|---:|---:|---|
| *(nullo)* | 30 | **0** | 🔴 |
| 17 | 1 | **0** | 🔴 |
| 4 | 2 | **1** | 🔴 |
| 5 | 1 | **1** | 🔴 |
| 1 | 25 | 267 | ✅ |
| 2 | 3 | 267 | ✅ |
| 3 | 1 | 267 | ✅ |
| 6 | 5 | 373 | ✅ |
| 7 | 6 | 373 | ✅ |

**Quattro asset posseduti su nove hanno zero o un punto prezzo.**

### 2.2 La conseguenza, misurata sull'API in esecuzione

```bash
POST /api/v1/risk/query   scope=portfolio  mode=current_composition
  analytics=[{instance_id:"a", analytic_code:"risk_contribution"}]
```
```json
{"code":"insufficient_history",
 "message":"Analytic 'risk_contribution' requires at least 20 observations",
 "details":{"observations":15,"required":20}}
```

Stesso esito per `comparison` (**il beta**):
```json
{"code":"insufficient_history","message":"Comparison has insufficient common observations",
 "details":{"observations":15,"required":20}}
```

> 🔑 **373 date esistono, le analitiche ne vedono 15.** Capire *perché* la serie di portafoglio
> collassa a 15 è **il primo compito dell'analisi**, e il coordinatore non ha la risposta:
> l'ipotesi è che l'intersezione delle date disponibili crolli sui quattro asset senza storia,
> con il riporto in avanti a coprire il resto. **Va verificata, non ereditata.**

### 2.3 Nessun asset è marcato benchmark

```sql
SELECT COUNT(*) FROM assets WHERE is_benchmark = 1;   -- 0   (su 17)
```

**B** ha costruito il flag e la migrazione `003_asset_benchmark_flag_and_taxonomy`; il
popolatore non lo usa. Senza almeno un benchmark, il selettore del confronto di L3 nasce
senza candidati naturali anche a storia sufficiente.

---

## 3. Cosa deve essere vero alla fine

| | condizione | come si verifica |
|---|---|---|
| **1** | Ogni asset **posseduto** ha ≥ 250 osservazioni di prezzo | query su `price_history` per `asset_id` con transazioni |
| **2** | Le analitiche vedono ≥ 250 osservazioni comuni | `risk_contribution` esce da `insufficient_history` |
| **3** | Almeno un asset ha `is_benchmark = 1` | query, **e** il selettore di L3 lo propone |
| **4** | `risk_contribution` e `comparison` tornano `ok` o `partial` | chiamata API reale, non test unitario |
| **5** | Il beta mostra **un numero** | osservazione sull'app |

⚠️ **La condizione 5 è quella che conta**: le prime quattro sono strumentali. Un mandato non
è finito quando la query dà il numero giusto — **è finito quando il numero è sullo schermo**.

---

## 4. Perimetro

**Possiedi:**
```
backend/test_scripts/test_db/populate_mock_data.py     ← il seeder
scripts/test_runner/_backend_db.py                     ← solo se serve un'opzione nuova
```

**Non toccare:**
- qualunque cosa sotto `frontend/`
- `backend/app/schemas/` e `backend/app/services/risk/` — **le soglie sono di prodotto**
- 🔴 **in particolare: non abbassare la soglia delle 20 osservazioni.** Il difetto è nei dati
  di prova, non nella soglia. Abbassarla farebbe passare i cancelli e lascerebbe il prodotto
  a calcolare rischio su una manciata di punti.

**Corsia**: `--test-port 6151`, `--data-dir /tmp/librefolio-r2-f1`. Il coordinatore tiene un
server di review su **6150** con la cartella dati predefinita: **non usarla**, la riscriveresti.

```bash
PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py test \
  --test-port 6151 --data-dir /tmp/librefolio-r2-f1 db populate --force --clean
```

---

## 5. Primo deliverable: **analisi, non codice**

Prima di scrivere una riga, consegna:

1. **Perché la serie collassa a 15.** Misurato, non ipotizzato.
2. Quali asset del mock hanno transazioni ma non prezzi, e **perché** — è una lacuna del
   generatore o una scelta deliberata per coprire un caso limite?
3. Se allungare la storia rompe test esistenti che dipendono dai numeri attuali —
   **cercali prima**, sono il vero costo di questo mandato.
4. Quale asset marcare benchmark, e perché quello.
5. I passi, con la verifica di ciascuno.

⚠️ **Non scrivere codice prima che l'analisi sia rivista.**

---

## 6. Due avvertimenti che vengono dal round 1

> **Non fidarti di questo documento.** Nel round 1, **undici mandati su undici** hanno trovato
> falsa almeno un'assunzione del proprio briefing, e oltre settanta in totale. Le misure qui
> sopra sono state prese il 18 settembre su una revisione precisa: **rifalle.** Se divergono,
> **dillo subito**: una divergenza segnalata è un'informazione, una taciuta è un difetto.

> **Aggiorna il piano dopo ogni passo, non alla fine.** E sappi perché: nel round 1 i file
> `*-esecuzione.md` sono risultati **gli unici otto file su dieci alberi a esistere solo sul
> disco**, fuori da ogni oggetto git. La causa è strutturale — il piano si aggiorna **dopo**
> il passo, quindi nessun checkpoint automatico lo contiene mai. **Il documento che registra
> il lavoro è quello che si perde per primo.**
