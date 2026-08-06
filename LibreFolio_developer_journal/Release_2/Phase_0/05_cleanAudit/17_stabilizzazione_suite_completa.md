# 17 — Stabilizzazione: la prima esecuzione completa della suite

> Seguito operativo del [report 12](12_test_coverage.md) e della chiusura
> [15](15_esecuzione_s1_s3.md). Nasce da una richiesta precisa dell'utente dopo il commit
> `be8394bb`: **eseguire tutti i test, backend e frontend, fino in fondo**, prima di aprire
> la sessione con i dati del beta tester.
>
> Comando di partenza:
> `./dev.py test --coverage --cov-clean-backend --cov-clean-frontend --fresh-run all`

---

## Sintesi

La suite si è fermata tre volte. Le tre cause sono state trovate, datate e corrette. Al
termine: **15/15 categorie verdi**, copertura combinata **90,66 %**.

Il risultato che conta più del verde finale è un altro:

> **Nessuna delle tre cause era stata introdotta dalla banda di pulizia S1–S3.** Tutte e tre
> erano regressioni *preesistenti*, vecchie da uno a tre mesi, invisibili perché la suite
> completa non era mai arrivata in fondo.

La domanda che l'utente aveva posto prima di lanciare i test — *«dopo tutta questa pulizia
il sistema rischia di essere instabile?»* — ha quindi trovato una risposta empirica: la
pulizia non ha rotto nulla, ma ha **fatto arrivare l'esecuzione abbastanza lontano da
scoprire cose rotte da mesi**.

| # | Blocco | Natura | Introdotto | Scoperto perché |
|---|---|---|---|---|
| **B1** | Suite API sotto `test all` | Difetto del *runner* | ≤ 2026-05-04 | Il DB dei fixture veniva distrutto prima dell'uso |
| **B2** | `asset-event-delete.spec.ts` | **Bug di prodotto** | 2026-07-23 (`5f4fabd05`) | Gli eventi sparivano su cache dei prezzi |
| **B3** | 7 spec transazioni | Selettore di test marcito | 2026-06-05 (`ee84e078`) | Un `input[type="number"]` che non esiste più |

---

## B1 — 🔴 Il runner distruggeva il database che gli serviva

### Il sintomo

Due test di `test_risk_api.py` fallivano con `NoResultFound` cercando l'utente
`e2e_test_user`, ma **solo dentro `test all`**: eseguiti da soli, passavano.

### La causa

L'ordine delle categorie backend è fisso:

```python
_BACKEND_CATEGORIES = ("external", "db", "services", "utils", "schemas", "api", "e2e")
```

- `db_all()` semina i fixture con `db_populate(force=True)`.
- `services_all()` chiama `db_create()` (`_backend_services.py:612`), che fa
  `TEST_DB_PATH.unlink()` e ricostruisce il DB **vuoto** dalle migrazioni Alembic.
- `api` gira **dopo** `services`.

Quindi la suite API trovava sistematicamente un database senza fixture. **Per costruzione
`test all` non poteva passare**: non era intermittenza, era determinismo.

### La prova forense

Nell'esecuzione fallita il primo utente in tabella era `wipe_user_1785955918623` con
`id = 1` — un utente creato *da un test di services*. La sequenza degli id era ripartita da
capo: prova diretta che la tabella era stata ricreata vuota. Dopo un populate corretto,
`id = 1` è `e2e_test_admin` e `id = 2` è `e2e_test_user`.

### Il rimedio

Il pattern giusto **esisteva già nel progetto**, nel runner frontend:
`_frontend_common.py:46 _ensure_db_populated()`. La suite API era l'unica categoria a non
averlo. È stato replicato in `api_test()` (`_backend_api.py`).

Contestualmente, la ricerca dell'utente fixture in `test_risk_api.py` è passata da
`.one()` a un helper condiviso `fixture_user_id()` che usa `scalar_one_or_none()` e fallisce
con il comando di rimedio esatto invece di un `NoResultFound` opaco. Effetto collaterale
gradito: −20 righe di boilerplate duplicato fra i due test.

> **Nota di merito sui test coinvolti.** I due test di `test_risk_api.py` non erano deboli:
> verificano che i pesi sommino a 1, che `CVaR ≥ VaR ≥ 0`, che i contributi sommino a 1, la
> determinismo del seed e l'igiene dello schema. Il difetto stava tutto nella **precondizione
> non dichiarata**, non nelle asserzioni. Per questo è stato irrobustito il setup, non
> l'assert.

### Effetto collaterale da sorvegliare

Dopo il populate, l'utente `id = 1` **è** un superuser. Il test
`test_broker_access_api.py:565`, che prima si auto-escludeva con *«First user is not
superuser (DB not clean)»*, ora **viene eseguito davvero**. Ha passato.

---

## B2 — 🔴 Bug di prodotto: gli eventi sparivano quando i prezzi erano in cache

### Il sintomo

`asset-event-delete.spec.ts:129` — *«Apple must have events»*. L'editor mostrava
**"No data"** su un asset che nel DB ha 5 eventi.

### La causa

`frontend/src/routes/(app)/assets/[id]/+page.svelte`, funzione `loadChartData()`:

- Se lo store dei prezzi copre già l'intervallo richiesto, la funzione riempiva `chartData`
  dalla cache, marcava `pricesFromCache = true` e — **se non c'erano segnali da calcolare —
  usciva subito**.
- Ma `events` viene assegnato **solo sul percorso di rete** (`events = result.events ?? []`),
  perché gli eventi viaggiano nella *stessa* risposta dei prezzi (`include_events: true`).

Risultato: **cache dei prezzi + nessun segnale attivo ⇒ gli eventi svanivano in silenzio**
dal grafico e dall'editor. Nessun errore, nessun log: solo dati che non c'erano.

### La datazione

`git blame` → `5f4fabd05` (2026-07-23), il commit che ha introdotto la cache dei prezzi.
**Non appartiene alla banda di pulizia.** È una regressione di tre settimane che la suite E2E
non aveva mai eseguito abbastanza a lungo da intercettare.

### Il rimedio

Rimosso il ritorno anticipato: l'esecuzione prosegue fino alla richiesta con
`include_price: false, include_events: true, signals: []`, cioè un payload minimo di soli
eventi. Tracciato che il fall-through è sicuro:

- `loading = !pricesFromCache` vale già `false`, quindi nessuno spinner spurio;
- `chartData` è protetto da `if (!pricesFromCache)`, quindi la cache non viene sovrascritta;
- il `catch` imposta `error` solo `if (chartData.length === 0)`, quindi un errore di rete su
  una cache piena non svuota un grafico già disegnato.

Verificato che il difetto **non ha fratelli**: `loadComparisonData.ts` usa
`include_events: true` ma non ha alcun percorso di cache, quindi fetcha sempre.

### Debito di test emerso di contorno

`asset-event-delete.spec.ts` conteneva tre imprecisioni, corrette:

- i commenti dichiaravano *«Apple has 3 DIVIDEND events»*; il conteggio autorevole, letto dal
  DB dopo `populate --force`, è **5**: 4 DIVIDEND (≈270/180/90/3 giorni fa) + 1 SPLIT (≈13
  giorni fa), di cui **3 collegati** a transazioni;
- il primo test è **distruttivo**: consuma uno dei due DIVIDEND non collegati;
- il secondo test resta di proposito sul range 3M, dove ogni evento è collegato: così **non
  dipende** dalla distruzione operata dal primo. Ora è scritto.

---

## B3 — 🟠 Un selettore marcito da due mesi, in sette file

### Il sintomo

4 test su 17 di `transactions-modals.spec.ts` fallivano con *«Apply button disabled»*, e uno
andava in timeout a 30 s su `tx-form-validate-now` disabilitato.

### La causa

Lo screenshot di fallimento mostrava il form compilato ovunque **tranne il campo Cash, fermo
a `0.00`**. L'helper faceva:

```ts
// The CompactCashCell has input[type="number"] for the amount
const cashInput = cashWrap.locator('input[type="number"]').first();
if (await cashInput.isVisible({timeout: 1_000}).catch(() => false)) {
    await cashInput.fill('100');
}
```

Ma `CompactCashCell` usa `<input type="text" inputmode="decimal">` — scelta **deliberata**,
documentata nel componente stesso: *«Locale-safe text input keeps browser number controls
from…»*.

Il selettore non trovava nulla, la guardia `if (isVisible)` **inghiottiva il fallimento**, il
form restava incompleto e il test moriva molto più tardi con un messaggio che non nominava la
causa.

### La datazione

| Data | Commit | Evento |
|---|---|---|
| 2026-05-12 | `b0e223c05` | Helper scritto, quando il campo *era* davvero `type="number"` |
| 2026-06-05 | `ee84e078` | Il campo diventa `type="text" inputmode="decimal"` |

**Due mesi** in cui quel passo di test non ha fatto nulla.

### L'ampiezza reale

Il difetto non era in un file ma in **sette**: `transactions-modals`, `tx-wac-formmodal`,
`tx-wac-bulk`, `tx-commit-all-types`, `tx-crud-full` (×2), `tx-fx-implied-rate`. Le spec
successive non erano ancora state raggiunte dal runner: sarebbero cadute una dopo l'altra.

### Il rimedio

Il pattern corretto **esisteva già nel repo**: `tx-commit-all-types.spec.ts` usava
`page.getByTestId('tx-form-cash-to-amount')` per il form duale. Solo gli helper del cash
singolo erano rimasti indietro.

Tutti i siti ora usano `input[data-testid$="-amount"]`, che funziona per ogni prefisso
(`tx-form-cash`, `tx-form-cash-from`, `tx-form-cash-to`) e rispetta la convenzione di
progetto — selettori su `data-testid`, mai su classi CSS.

### Un bug latente scoperto di conseguenza

In `tx-fx-implied-rate.spec.ts` la tendina valuta veniva cercata con
`cashWrap.locator('input[type="text"]').first()`. Ora che **anche il campo importo è
`type="text"`**, e viene renderizzato prima, quel `.first()` selezionava l'importo: il test
avrebbe digitato il codice valuta dentro il campo dell'importo. Il selettore è stato limitato
a `.currency-wrap`.

---

## Il filo che lega i tre blocchi

Tutti e tre condividono la stessa forma, già incontrata nella banda S1–S3 con la regressione
half-donut:

> **Una verifica che non può fallire non è una verifica.**

- B1: una precondizione **mai dichiarata** (il DB popolato), quindi mai controllata.
- B2: un percorso di codice che **non assegnava** un dato, senza che nulla lo notasse.
- B3: una guardia `if (await x.isVisible().catch(() => false))` che trasforma un selettore
  rotto in un **no-op silenzioso**.

È esattamente la famiglia del difetto documentato in [15](15_esecuzione_s1_s3.md): il test
`ownership-chart-section` che asseriva il contenitore invece del contenuto, e le due
asserzioni `toHaveCount(await count())` che confrontavano un valore con sé stesso.

**Raccomandazione trasversale**: nelle spec E2E, il pattern
`if (await locator.isVisible().catch(() => false)) { … }` va usato **solo** dove il ramo è
davvero opzionale nel prodotto. Dove l'elemento *deve* esserci, va usato `await
expect(locator).toBeVisible()`, che fallisce dove sta il problema e non 40 righe dopo.

---

## Copertura — analisi

### I tre numeri, e cosa significano davvero

| Misura | Valore | Che cosa misura |
|---|---:|---|
| Backend (unit + services + API + e2e backend) | **90 %** | Il codice esercitato dai test Python |
| Frontend E2E → backend | **47 %** | Il backend esercitato dai *percorsi utente reali* |
| **Combinata** | **90,66 %** | 36 891 statement, 3 437 scoperti |

> ⚠️ **La "copertura frontend" di questo progetto non è copertura JavaScript.**
> `./dev.py test coverage show frontend` misura *quanto backend viene toccato dagli E2E*.
> Non esiste alcuno strumento di copertura JS/Svelte installato: `@vitest/coverage-*` non è
> fra le dipendenze e nessuna configurazione `coverage` esiste in `vite.config.ts`.
> **Della copertura del codice frontend non sappiamo nulla.** È il buco di misurazione più
> grande del progetto, e va detto esplicitamente perché il nome del comando suggerisce il
> contrario.

Il 90,66 % conferma il **90,48 %** misurato dal [report 12](12_test_coverage.md) prima della
banda di pulizia: la rimozione di ~290 righe di test non ha spostato l'ago. Conferma anche,
di nuovo, la trappola documentata in `12 § L1`: la stessa esecuzione, interrotta a metà,
aveva riportato **86,57 %**. Una misura parziale mente sempre al ribasso.

### I moduli più deboli in percentuale (≥ 20 statement)

| Copertura | Scoperti | Modulo | Lettura |
|---:|---:|---|---|
| 59,0 % | 103 | `services/fx_providers/snb.py` | **Il peggiore del progetto.** Coerente con il gap "SNB daily" già noto nel Blocco 2 mkdocs |
| 70,5 % | 90 | `asset_source_providers/justetf.py` | Provider di rete: rami di parsing HTML mai esercitati |
| 73,5 % | 70 | `asset_source_providers/yahoo_finance.py` | Idem |
| **73,9 %** | **72** | **`api/v1/assets.py`** | **Il più preoccupante: è API, non rete esterna** |
| 74,1 % | 7 | `utils/identifier_utils.py` | 27 statement in tutto: **la vittoria più facile del backlog** |
| 75,6 % | 43 | `brim_providers/broker_cryptocom.py` | Famiglia BRIM, vedi sotto |
| 76,8 % | 82 | `asset_source_providers/borsa_italiana.py` | Provider di rete |
| 78,3 % | 33 | `main.py` | Lifespan, scheduler, pre-warm: difficile da esercitare |
| 79,6 % | 56 | `risk/quant/spawn_worker.py` | Processo figlio: la copertura non lo segue |

### I buchi più grandi in valore assoluto

| Scoperti | Copertura | Modulo |
|---:|---:|---|
| 167 | 88,9 % | `services/asset_source.py` (1 509 stmt) |
| 106 | 88,3 % | `services/lots_analysis_service.py` (904 stmt) |
| 103 | 59,0 % | `fx_providers/snb.py` |
| 75 | 93,1 % | `services/portfolio_engine.py` |
| 75 | 93,2 % | `services/portfolio_service.py` |
| 72 | 73,9 % | `api/v1/assets.py` |
| 68 | 91,2 % | `schemas/risk.py` |
| 63 | 92,3 % | `services/transaction_service.py` (822 stmt) |

### Che cosa se ne ricava

1. **Il debito di copertura è quasi tutto ai bordi I/O**, non nel cuore finanziario. I motori
   — `portfolio_engine`, `portfolio_service`, `transaction_service`, `fifo`/`wac` — stanno
   tutti fra il 92 % e il 95 %. È il profilo giusto per un tracker di portafoglio.
2. **Un'eccezione va guardata**: `api/v1/assets.py` al 73,9 % con 72 statement scoperti. Non
   è un provider di rete, è superficie API. Merita un giro di test mirato.
3. **La famiglia BRIM è sistematicamente fra il 75 % e l'82 %** (`cryptocom`,
   `cointracking`, `investimental`, `bitvavo`, `investengine`). Sono i rami di errore dei
   parser: file malformati, colonne mancanti, encoding. Sono anche esattamente i casi che un
   beta tester incontrerà per primo caricando i propri estratti conto reali.
4. **`identifier_utils.py`** — 7 statement scoperti su 27. Costo quasi nullo, chiude un
   modulo intero.
5. **Il vero rischio non è il 9 % scoperto del backend, è il 100 % non misurato del
   frontend.** Tre dei difetti di questo report vivevano nel frontend o nei suoi test.

---

## Stato finale verificato

| Controllo | Esito |
|---|---|
| `./dev.py test --coverage --resume all` | **15/15 categorie** — 🎉 ALL TESTS PASSED |
| Categorie backend | external · db · services · utils · schemas · api · e2e — tutte verdi |
| Categorie frontend | utility · broker · user · fx · asset · transaction · portfolio · ai-export — tutte verdi |
| `./dev.py front check` | 0 errori · 0 warning |
| Copertura combinata | **90,66 %** su 36 891 statement |

---

## Da riprendere

| Priorità | Voce |
|---|---|
| 🔴 | **Introdurre la copertura JS/Svelte** (`@vitest/coverage-v8`). Oggi metà del prodotto non è misurata |
| 🟠 | Test mirati su `api/v1/assets.py` (73,9 %) |
| 🟠 | Rami di errore dei parser BRIM (75–82 %): sono la prima superficie che il beta tester tocca |
| 🟡 | `fx_providers/snb.py` al 59 %, il modulo peggiore |
| 🟡 | `utils/identifier_utils.py`: 7 statement, vittoria immediata |
| 🟡 | Rileggere le spec E2E alla ricerca di altre guardie `isVisible().catch(() => false)` su elementi obbligatori |
| ⚪ | `cleanup_test_database()` in `backend/test_scripts/test_db_config.py:50` — **zero chiamanti**, trovato durante l'indagine su B1. Codice morto non censito nei report 01–14 |
