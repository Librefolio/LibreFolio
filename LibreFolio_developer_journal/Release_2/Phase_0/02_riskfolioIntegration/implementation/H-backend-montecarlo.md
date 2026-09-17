# Mandato H — Rifondazione del Monte Carlo

| | |
|---|---|
| **Flusso** | W8 di [`../07-piano-esecutivo.md`](../07-piano-esecutivo.md) §2 |
| **Dominio** | backend simulazione + selettore frontend |
| **Taglia** | **XL** |
| **Lane** | porta `6247` · data dir `backend/data/test-risk-h` |
| **Dipende da** | nulla — **e va lanciato presto proprio per questo** |
| **Consegna** | contratto **K6** a **E** |

> Regole comuni: [`README.md`](./README.md) §5. Finito comune: §6.

---

## 1. Perché lanciarlo per primo anche se sembra secondario

È un **XL che non aspetta nessuno e non blocca nessuno**. Tocca il worker QuantLib e il
plugin `simulation`, che nessun altro mandato apre.

> Se parte tardi, diventa lui il percorso critico. Il piano non ha un secondo posto
> dove questo lavoro possa nascondersi.

---

## 2. Perché il Monte Carlo va rifondato, non buttato

Il motore attuale genera migliaia di traiettorie sotto **moto browniano geometrico**,
con drift e covarianza stimati dallo storico.

**Il problema è epistemico, non implementativo.** Il risultato è determinato **quasi
interamente dalle assunzioni, non dai dati**. Il GBM assume rendimenti log-normali,
volatilità costante, correlazione costante, nessuna coda grassa e nessun cambio di
regime — cioè **precisamente tutto ciò che rende i mercati pericolosi**.

Conseguenza pratica: il cono **sottostima sistematicamente le code**. E visivamente è
l'oggetto più convincente della pagina, quindi il danno cognitivo è massimo.

> Il ventaglio insegna però una cosa vera — *«non esiste un numero, esiste una
> distribuzione»* — e per questo **si rifonda invece di cancellarlo** (**D7**). Ciò che
> non può fare è stare accanto a metriche osservate **come se fosse della stessa
> natura**.

---

## 3. Cosa leggere prima

1. [`../02-verdetti-per-strumento.md`](../02-verdetti-per-strumento.md) **§ Monte
   Carlo** — la scaletta a cinque livelli e la tabella comparativa.
2. [`../01-tesi-e-quattro-domande.md`](../01-tesi-e-quattro-domande.md) **§3 L4** — il
   gradiente interno di L4 e perché la simulazione sta **in fondo**.
3. [`../05-…`](../05-grammatica-visiva-e-rappresentazioni.md) **§7.7** — il cono.
4. **D7** e **D22** nel registro.
5. Nell'archivio, da **non** riaprire ma da citare:
   [`../_archive-backendFirst-G0G6/spike-phase01SimulationAdapters.md`](../_archive-backendFirst-G0G6/spike-phase01SimulationAdapters.md)
   (oracle analitici GBM) e
   [`../_archive-backendFirst-G0G6/benchmark-phase01SimulationScale.md`](../_archive-backendFirst-G0G6/benchmark-phase01SimulationScale.md)
   (misure di scala).

---

## 4. La scaletta — livelli 1-3 in ambito, 4-5 rinviati

| # | Approccio | Cattura | Calibrabile? | Spiegabile | Ambito |
|---|---|---|---|---|:---:|
| 1 | **Block bootstrap** | code grasse, asimmetria, cluster di volatilità, sequenze di crisi — *sono dati veri* | non serve | ⭐⭐⭐ *«rimescolo a blocchi la storia vera»* | ✅ |
| 2 | **GJR-GARCH** (nativo QuantLib) | cluster di volatilità + effetto leva | ✅ dalla sola serie prezzi | ⭐⭐ | ✅ |
| 3 | **Preset di regime prescritti** | fasi di mercato con vol, correlazioni e drift propri | ❌ dichiarati, non stimati | ⭐⭐⭐ se l'ipotesi è a schermo | ✅ |
| 4 | Markov-switching calibrato | idem, stimato | ⚠️ overfitta su 3-5 anni | ⭐ | 🔴 TODO |
| 5 | Heston / Bates / Merton | vol stocastica, salti | ❌ richiede dati di opzioni | ⭐ | 🔴 TODO |

> ## Il block bootstrap diventa il default
>
> Batte il GBM **su ogni asse**: più onesto, più realistico, più facile da spiegare e
> **più economico da implementare**. Non è un compromesso — è semplicemente migliore.

Il GBM **resta disponibile**, etichettato come *«modello classico: sottostima le
code»*, marcato avanzato.

---

## 5. Il selettore presenta modalità, non parametri

```text
Come simulo?
 ● Storia rimescolata   — uso i tuoi rendimenti reali, riordinati a blocchi  [consigliato]
 ○ Mercato calmo        — ipotesi: volatilità ridotta del 30%
 ○ Crisi prolungata     — ipotesi: vol ×2,5 · correlazioni → 0,9 · drift −20%/anno · 14 mesi
 ○ Shock e recupero     — ipotesi: −35% in 2 mesi, poi ritorno al regime normale
 ○ Curva normale (GBM)  — modello classico: sottostima le code  [avanzato]
```

> ## 🔑 L'ipotesi si scrive *inline*, accanto alla scelta
>
> Non in un tooltip, non in una nota a piè di pagina. Un preset di regime è
> **dichiarato, non stimato**: se l'utente non vede l'ipotesi, sta leggendo un numero
> che crede derivato dai dati.

⚠️ **`sobol_start_index` esce dalla UI in ogni caso** (`RiskAnalysisPanel:1224`). È un
controllo da quant, non da utente — e vale a prescindere da quale modalità si
implementi.

---

## 6. L'unico posto dove la gaussiana ha senso

**D22** ha escluso la curva normale sovrapposta all'istogramma di L1, perché lì il VaR
è un quantile empirico e la campana confronterebbe i dati con un modello che non stiamo
usando.

> **L4 è l'eccezione.** Qui un modello lo stiamo **davvero scegliendo**, quindi
> mostrare *cosa assume il GBM* contro *cosa produce il bootstrap* è
> decision-relevant — è letteralmente la differenza fra le due modalità che l'utente ha
> davanti.

Se c'è un posto dove disegnare la campana, è questo. Da concordare con **E**.

---

## 7. Il cono, lato frontend — costo basso

`RiskSimulationOutput.percentile_bands` espone **già** `p05 / p50 / p95` per ogni
giorno dell'orizzonte, e `buildBandSeries` — quella usata per le Bollinger — rende già
le bande.

**Riuso puro.** Il lavoro è far arrivare le nuove modalità dentro quella struttura, non
inventare una rappresentazione.

---

## 8. Confini

**Di questo mandato**:

- `backend/app/services/risk/quant/quantlib_worker.py`
- `backend/app/services/risk_plugins/simulation.py`
- gli schemi di parametri della simulazione
- il **selettore di modalità** nella UI — ⚠️ concordato con **E**, che possiede
  `components/risk/**`
- i18n: **solo** il sotto-blocco `risk.simulation.*`, che E apre

**Fuori**:

- `metrics.py` e tutto il mandato **A**;
- il worker **Riskfolio** (`riskfolio_worker.py`) — è dell'ottimizzatore, non della
  simulazione;
- `portfolio_optimization`, che è **rinviata** (**D6**) e non va né tolta né riattivata.

**Vincoli architetturali che non si riaprono** ([`../01-…`](../01-tesi-e-quattro-domande.md) §7):

- l'obbligo di calcolo in processi **`spawn`**;
- il contratto matematico archiviato;
- il modello di qualità del dato.

⚠️ **Nota sul worker**: `quantlib_worker.py:33` **solleva** su matrice di covarianza
non semidefinita positiva. Con molti asset e poca storia la matrice diventa singolare
— un utente non ottiene numeri imprecisi, **ottiene un errore**. Se il bootstrap
elimina la dipendenza dalla covarianza in certe modalità, va detto esplicitamente quali
e perché: è un miglioramento che merita di essere dichiarato, non scoperto.

---

## 9. Contratto K6 → mandato E

- i nomi delle modalità e la forma del selettore;
- il testo dell'ipotesi per ciascun preset, che è **parte del contratto**, non
  decorazione;
- la forma del payload del cono, se cambia rispetto a `percentile_bands`;
- dove resta il banner beta: **solo** su questo gradino di L4 (**D46**).

---

## 10. Test

| Cosa | Comando |
|---|---|
| Simulazione | `services risk-simulation` |
| Worker | `services risk-workers` |
| Runtime QuantLib | `services quantlib-runtime` |
| Integrazione | `services risk-all` |

```bash
PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc \
  pipenv run python dev.py test --test-port 6247 --data-dir backend/data/test-risk-h \
  services risk-simulation
```

⚠️ **Riproducibilità**: i test esistenti verificano la riproducibilità dei percorsi a
seme fissato. Il bootstrap introduce un **nuovo** campionamento casuale: va seminato in
modo che la riproducibilità resti verificabile, altrimenti ogni test diventa flaky per
costruzione — e nessun `test-triage` potrà salvarlo.

Se serve un selettore nuovo nel catalogo, si **chiede al mandato A**, che possiede
`scripts/test_runner/_backend_services.py`.

---

## 11. Definizione di finito

- [ ] Block bootstrap implementato e **default**;
- [ ] GJR-GARCH disponibile, calibrato dalla sola serie prezzi;
- [ ] preset di regime prescritti, con **l'ipotesi scritta inline**;
- [ ] GBM ancora disponibile, etichettato «avanzato» e con il suo limite dichiarato;
- [ ] `sobol_start_index` **fuori dalla UI**;
- [ ] riproducibilità a seme fissato verificata **anche per il bootstrap**;
- [ ] calcolo ancora in processi `spawn`;
- [ ] livelli 4-5 **non** implementati e ancora registrati in `TODO_FUTURI.md`;
- [ ] `services risk-simulation`, `risk-workers` e `risk-all` verdi;
- [ ] **K6 consegnato e comunicato a E**;
- [ ] nessun processo in ascolto su `6247`.
