# Mandato A — Oracolo di test e migrazione matematica

| | |
|---|---|
| **Flussi** | W0 + W1 di [`../07-piano-esecutivo.md`](../07-piano-esecutivo.md) §2 |
| **Dominio** | backend, matematica del rischio |
| **Taglia** | L |
| **Lane** | porta `6240` · data dir `backend/data/test-risk-a` |
| **Dipende da** | nulla — parte subito |
| **Consegna** | contratto **K1** a **E** |

> Regole comuni (Git, runtime, test, piano vivo): [`README.md`](./README.md) §5.
> Definizione di finito comune: [`README.md`](./README.md) §6.

---

## 1. Perché questo mandato esiste

Il sottosistema rischio possiede **661 righe di matematica scritta in casa**
(`services/risk/metrics.py`), mai confrontate con un riferimento esterno. Il test che
le copre (`test_risk_metrics.py`, 297 righe) importa solo `math` e verifica **proprietà
interne**: additività del PCTR, identità con tracking error nullo. Test buoni, ma tutti
autoreferenziali.

La conseguenza non è teorica. Il **CVaR è sbagliato** — più basso del valore corretto
2 000 volte su 2 000, in media dello 0,27%, a sette deviazioni standard dallo zero — e
nessun test se n'è accorto per un anno. Analisi completa in
[`../06-matematica-librerie-e-reimplementazioni.md`](../06-matematica-librerie-e-reimplementazioni.md)
§3.2.

> Il mandato non è «velocizzare `metrics.py`». È **smettere di possedere matematica che
> possiamo sbagliare da soli**, e mettere una rete sotto quella che continuiamo a
> possedere. Il criterio è **D36**, che ha revocato D30: non la velocità, il possesso.

---

## 2. Cosa leggere prima di toccare qualunque cosa

Nell'ordine, e per intero:

1. [`../06-…`](../06-matematica-librerie-e-reimplementazioni.md) **§7.-1** — il piano
   M1-M6 in una pagina, con l'ordine vincolato e la sua motivazione.
2. [`../06-…`](../06-matematica-librerie-e-reimplementazioni.md) **§3.2** e
   **§3.2.1** — la distorsione del CVaR e le sue *due* cause (denominatore e
   off-by-one). Sono due difetti distinti: correggerne uno solo lascia l'altro.
3. [`../06-…`](../06-matematica-librerie-e-reimplementazioni.md) **§4.1** — le misure
   di rallentamento, e soprattutto il riquadro sulla **semantica dei buchi**.
4. [`../06-…`](../06-matematica-librerie-e-reimplementazioni.md) **§7.3 ⚠️ il Sortino**
   — il caso che insegna perché nome uguale non significa grandezza uguale.
5. **D24**, **D25**, **D28**, **D29**, **D32**, **D36**, **D40**, **D44** in
   [`../04-…`](../04-decisioni-e-questioni-aperte.md).

Poi `wiki-search` sui domini con storia: metriche di rischio, segnali rolling, FIFO.

---

## 3. W0 — L'oracolo, prima di tutto

### 3.1 Indirizzo, e perché non è dove sembrerebbe ovvio

| Cosa | Valore |
|---|---|
| File **nuovo** | `backend/test_scripts/test_services/test_risk_metrics_oracle.py` |
| Categoria | `services` |
| Selettore **nuovo** | `risk-oracle` |
| Registrazione | `add_test(cat, "risk-oracle", …)` in `scripts/test_runner/_backend_services.py` |
| Aggiunta a | `RISK_SERVICE_TEST_PATHS` (`_backend_services.py:69-81`) |

⚠️ **Non va dentro `test_risk_metrics.py`.** Quel file importa solo `math` ed è
istantaneo; è la prima cosa che si lancia quando si tocca una formula. Importare
riskfolio costa **4 722 ms a freddo** — misurato, attribuito per strato in
[`../07-piano-esecutivo.md`](../07-piano-esecutivo.md) §5. Mescolarli renderebbe lento
il file che deve restare veloce.

Il costo è **già pagato** dentro `risk-all`, perché `test_risk_optimization.py` importa
già riskfolio ed è nello stesso gruppo.

### 3.2 Cosa deve contenere

Non «dei test»: la **guardia di D40** resa eseguibile. Tre blocchi.

**(a) Le coppie del caso A** — nostra funzione contro gemella di libreria, uguaglianza
numerica dichiarata con tolleranza esplicita. L'elenco è in
[`../06-…`](../06-matematica-librerie-e-reimplementazioni.md) § *Caso A*.

**(b) I composti del caso B** — `summarize_drawdown` contro `MDD_Rel`, e le altre otto
di **D44**. Qui l'oracolo non sostituisce: **sorveglia**. Se un giorno il nostro
drawdown divergesse, il test lo dice subito. È esattamente la protezione che al CVaR è
mancata.

**(c) Le quattro trappole nome/grandezza** — e questo è il blocco che vale di più.
Vanno codificate come test che **falliscono se qualcuno le scambia**, non come
commenti:

| Trappola | Il rischio concreto |
|---|---|
| `MDD_Abs` contro `MDD_Rel` | `cumsum` invece di `cumprod`: 0,33 invece di 0,30, **11% di scarto senza errore visibile** |
| `numBins` | è Hacine-Gharbi per la mutua informazione, **non** per un istogramma |
| `SemiDeviation` contro il nostro Sortino | scarti sotto la **media** ÷ `T−1`, non sotto il **MAR** ÷ `T` |
| `Kurtosis` | è `sqrt(m₄)`, **non standardizzata**: 0,00034 dove la kurtosi vera è 2,99 |

> Un commento che avverte non impedisce lo scambio. Un test sì.

### 3.3 Cancello G-A

L'oracolo copre **ogni** funzione che W1 toccherà. Non «le principali».
Finché non è vero, W1 non comincia.

---

## 4. W1 — La migrazione, nell'ordine vincolato

```text
M2 ─► M1 ─► M3 ─► M6 ─► M5
```

Motivazione dell'ordine in
[`../06-…`](../06-matematica-librerie-e-reimplementazioni.md) §7.-1. Non va cambiato:
M2 è l'unica che corregge un errore invece di spostare codice, e M1 è quella che gira
a ogni caricamento di grafico.

### M2 — CVaR allo stimatore coerente 🔴

**Cosa**: `historical_var_cvar` (`metrics.py:608`) adotta Acerbi-Tasche /
Rockafellar-Uryasev.

**Due difetti, non uno.** Il secondo si dimentica facilmente:

1. il **denominatore**: dividiamo per il conteggio reale (38) invece che per `α·T`
   (37,5), pesando intera l'osservazione che andrebbe pesata per la sua frazione;
2. l'**off-by-one** all'indice del quantile, che morde **solo quando `α·T` è intero** —
   cioè nei casi che sembrano più semplici, dove lo scarto **raddoppia**.

**Non serve chiamare riskfolio a runtime**: la formula sono quattro righe di NumPy.
Riskfolio serve come **oracolo nel test**, che è il modo di non sbagliarla una seconda
volta.

⚠️ **Il pavimento a zero è una decisione separata.** `max(-value, 0.0)` significa che
il VaR non può essere negativo
([`../06-…`](../06-matematica-librerie-e-reimplementazioni.md) §3.3). È una scelta di
presentazione, **non fa parte di questo difetto**: va mantenuta o rimossa
consapevolmente, non trascinata dentro la correzione. Se si tiene, va segnalata a **E**,
perché su una serie molto stabile la linea del VaR cadrebbe sullo zero invece che su un
quantile dei dati.

**Ha un effetto visibile all'utente** → alimenta la voce di CHANGELOG del mandato **J**
([`../07-piano-esecutivo.md`](../07-piano-esecutivo.md) §6). Comunicarlo.

### M1 — Segnali rolling a pandas 🔴

**Cosa**: `risk/signal_helpers.py:69-108` — `rolling_single_values` e
`rolling_pair_values` — da ciclo Python a `pandas.rolling`.

**Perché per prima fra le migrazioni di sola velocità**: gira a ogni caricamento di
grafico, su ogni asset, per ogni utente. Da **43×** a **1 514×** più veloce, a valori
identici (`np.allclose` verificato).

Mappatura per segnale in
[`../06-…`](../06-matematica-librerie-e-reimplementazioni.md) § M1. Un solo punto da
ricordare: `rolling_return` va con `expm1(log1p(s).rolling(W).sum())`, **non**
`.apply(prod)`, che resterebbe interpretato e vanificherebbe la migrazione.

> ## ⚠️ Il lavoro vero non è la matematica, è la semantica dei buchi.
>
> Il ciclo attuale restituisce `None` per le finestre indefinite e ne **tiene il
> conteggio** (`undefined_windows`), che alimenta un avviso all'utente.
> `annualized_sharpe` restituisce `None` quando la volatilità è nulla; pandas
> produrrebbe `inf` o `NaN`.
>
> La versione vettorializzata deve riprodurre **esattamente** `None` e il conteggio.
> Altrimenti sparisce un avviso e **nessun test se ne accorge**: è la stessa classe di
> difetto del CVaR, in un punto diverso.

È qui che va speso il tempo di revisione. Le formule coincidono già.

### M3 — Matrici a NumPy 🟠

**Cosa**: `correlation_matrix`, `covariance_matrix`, e il doppio ciclo di
`risk_plugins/correlation.py:72`.

**NumPy, non riskfolio**, con quattro ragioni in
[`../06-…`](../06-matematica-librerie-e-reimplementazioni.md) § M3. La sintesi: per la
matrice storica `covar_matrix('hist')` **è** `np.cov` con un guscio che costa 2-3× e
pretende un `DataFrame`; sulla correlazione riskfolio non ha nemmeno una funzione
diretta.

**La firma non cambia, ed è il punto.** NumPy resta **dentro** la funzione e non risale
mai nei plugin: il giorno in cui servisse Ledoit-Wolf si sostituisce il corpo e
nient'altro se ne accorge. Scegliere NumPy ora non chiude la porta a riskfolio dopo.

⚠️ **Il costo nascosto è `coverage`.** `pairwise_correlation` restituisce anche
`observations` e `coverage`, che gestiscono i calendari disallineati. Serve una
**maschera di validità**, non un `np.corrcoef` crudo. E dove la varianza è nulla noi
diamo `None`, NumPy dà `nan`: stessa classe di problema di M1, da ritradurre a mano.

### M6 — I nove composti a NumPy 🟡

`summarize_drawdown`, `drawdown_episodes`, `pairwise_correlation`,
`comparison_summary`, `wealth_index`, `period_returns_from_cumulative`,
`horizon_compounded_returns`, `current_buy_and_hold_returns`, `annualized_sortino`.

**Firma e semantica invariate.** Restano **nostre** — ci appartiene la composizione,
non l'aritmetica (**D44**) — ma vettorializzate e sotto oracolo.

⚠️ Su `annualized_sortino` vale la guardia di **D40**: il nostro misura gli scarti
sotto il **MAR** dividendo per `T`, `SemiDeviation` sotto la **media campionaria**
dividendo per `T−1`. Verificato: 1,66294 contro 1,57093. **Il nostro è corretto per il
suo scopo**: si vettorializza, non si sostituisce.

### M5 — Contributi al rischio 🟡 bassa priorità

Doppione accertato contro `Risk_Contribution(rm="MV")`. Si migra per principio, ma per
ultimo: riskfolio vuole la **matrice dei rendimenti**, noi passiamo solo covarianza e
pesi. Far arrivare i rendimenti a quel livello è idraulica, e va a preventivo.

Il valore vero non è il numero — identico — ma il `rm=` che si sblocca dopo
([`../06-…`](../06-matematica-librerie-e-reimplementazioni.md) §7.1). **Non fa parte di
questo mandato**: i contributi su misure non-MV possono essere **negativi**, il che
rompe l'assunto della UI, e la decisione è rimandata
([`../04-…`](../04-decisioni-e-questioni-aperte.md) Q7).

---

## 5. La consegna fuori piano: i due campi di schema — contratto K1

Non fanno parte di M1-M6, ma sono **l'unica parte di questo mandato che blocca qualcun
altro**. Il mandato **E** non può disegnare due delle sei rappresentazioni finché non
arrivano.

| Campo | Per | Costo reale |
|---|---|---|
| Serie underwater su `drawdown_summary` | grafico underwater ([`../05-…`](../05-grammatica-visiva-e-rappresentazioni.md) §7.1) | **quasi nullo**: `drawdown_episodes()` calcola già `underwater = underwater_drawdown(wealth)` in una variabile locale e ne butta via tutto tranne gli scalari (**D14**, **D20**) |
| Bin dell'istogramma su `RiskVarCvarOutput` | istogramma ([`../05-…`](../05-grammatica-visiva-e-rappresentazioni.md) §7.2) | basso: `np.histogram(x, bins='fd')` **è** Freedman-Diaconis nativo (**D21**) |

Sui bin ci sono **tre** dettagli che se saltati producono un grafico lievemente falso:

1. un **bordo forzato sul quantile del VaR** — altrimenti il taglio cade dentro un bin
   e l'area rossa è *circa* il 5% invece che esattamente il 5%. È l'unica parte scritta
   da noi: cinque righe che traslano la griglia;
2. **la stessa serie del VaR** — se `horizon_days` supera il giorno, i rendimenti da
   raggruppare sono quelli a `h` giorni, o barre e linea raccontano due cose diverse;
3. **non usare `AuxFunctions.numBins`** — è Hacine-Gharbi per la mutua informazione
   (**D35**). Darebbe un numero plausibile e sbagliato.

Payload atteso: ~50 terne `(bordo_inf, bordo_sup, conteggio)`.

> Nomi, tipi e unità vanno **concordati con E prima di scrivere il codice**, tramite il
> coordinatore. Un campo consegnato con un nome diverso da quello atteso costa a E una
> riscrittura che nessuno aveva preventivato.

Dopo la modifica di schema: **`./dev.py api sync`**.

---

## 6. Confini

**Di questo mandato**, e di nessun altro:

- `backend/app/services/risk/metrics.py`
- `backend/app/services/risk/signal_helpers.py`
- `backend/app/services/risk_plugins/correlation.py` (il solo doppio ciclo a `:72`)
- `backend/test_scripts/test_services/test_risk_metrics.py` e il file oracolo nuovo
- `scripts/test_runner/_backend_services.py` — **scrittore unico**: se H chiede un
  selettore, lo registra questo mandato

**Condiviso**: `backend/app/schemas/risk.py` con i mandati **C** e **N** — **tre
scrittori**, non due. Le regioni sono misurate e lontane:

| Regione | Scrittore |
|---|---|
| classi di **scope** `:537-585` | **C** |
| `RiskKpiOutput` `:640-647` · `RiskContributionOutput` `:676-680` | **N** |
| `RiskVarCvarOutput` `:820-835` · `RiskDrawdownOutput` `:945-1018` | **questo mandato** |
| **`__all__` `:1067-1126`** | 🔴 tutti e tre |

⚠️ **Il conflitto vero è `__all__`**, non le classi: il file finisce con una lista di
sessanta nomi **ordinata alfabeticamente**, e chi aggiunge una classe deve inserire un
nome in mezzo. È **l'unica regione dell'intera campagna** dove è autorizzata una
risoluzione meccanica del conflitto — **unione dei nomi + riordino alfabetico**.
Ovunque altro vale [`README.md`](./README.md) §2.2: **non riformattare, non riordinare
gli import, non toccare una classe non propria**.

> ### ⚠️ `RiskDrawdownOutput` è di questo mandato, la famiglia scalare no
>
> Il mandato **N** aggiunge `MDD`, `DaR`, `CDaR`, `UCI` e `WR` — ma su
> **`RiskKpiOutput`**, non qui. La divisione è deliberata:
>
> | Classe | Contenuto | Scrittore |
> |---|---|---|
> | `RiskKpiOutput` `:640` | la **famiglia scalare** di L1 | **N** |
> | `RiskDrawdownOutput` `:945` | il **racconto per episodi** + la serie underwater di K1 | **questo mandato** |
>
> N deve verificare che `max_drawdown` coincida con `MDD_Rel`. Se scopre che **non**
> coincide, la scoperta riguarda `summarize_drawdown`, che è **nostro**: arriverà dal
> coordinatore e va trattata come un difetto di questo mandato, non respinta come «roba
> di N».

> ### 🔴 `Sharpe(rm=…)` (**D39**) è di questo mandato, ed è la coda di M5
>
> Il mandato **N** prende le acquisizioni di L1 e L2, ma **non** D39: Calmar
> (`rm="MDD"`) e Martin (`rm="UCI"`) pretendono la **matrice dei rendimenti**, che è
> esattamente l'idraulica mancante di **M5**.
>
> Chi fa M5 ha già pagato metà del lavoro. Quindi: **dopo M5**, e solo allora, si
> valuta se far salire i rendimenti fino a quel livello. Se M5 viene rinviata, D39 la
> segue — e va **dichiarato**, non lasciato cadere.

**Fuori**, e non per sfioramento:

- i **nove analytic** di `risk_plugins/` — nessuno cambia firma, scope o contratto;
- i **17 plugin di analisi tecnica** (**D31**): delegano già a TA-Lib in C, sono il
  modello, non il debito;
- gli **stimatori robusti di covarianza** (**D34**): sono qualità della stima, non
  velocità, e tre sono già cablati nell'ottimizzatore dove devono stare
  ([`../06-…`](../06-matematica-librerie-e-reimplementazioni.md) §7.0.1);
- qualunque **acquisizione** di L1 o L2 (NEA, diversification ratio, WR, `UCI`, `DaR`,
  `CDaR`): sono funzionalità nuove, non migrazione, e sono del **mandato N**
  ([`N-backend-acquisizioni.md`](./N-backend-acquisizioni.md)).
  ⚠️ **Unica eccezione: `Sharpe(rm=…)` / D39, che resta qui** come coda di M5 — vedi §6.

---

## 7. Test

| Momento | Comando |
|---|---|
| Durante, sull'oracolo | `services risk-oracle` |
| Durante, sulle formule | `services risk-all -k metrics` |
| Dopo ogni M | `services risk-all` |
| Se tocca i segnali (M1) | anche `services signal-contracts` e `services signal-service` |

```bash
PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc \
  pipenv run python dev.py test --test-port 6240 --data-dir backend/data/test-risk-a \
  services risk-all
```

Per scrivere o riparare test si invoca **`test-author`**, passandogli la lane e i file
consentiti. Prima di dichiarare flaky un rosso: **`test-triage`**.

---

## 8. Definizione di finito

Oltre a quella comune ([`README.md`](./README.md) §6):

- [ ] `risk-oracle` verde, e **copre ogni funzione toccata da W1**;
- [ ] le quattro trappole nome/grandezza sono test che falliscono allo scambio;
- [ ] M2 fatto, con **entrambi** i difetti corretti, e l'effetto utente comunicato a J;
- [ ] M1 fatto, con **prova esplicita** che `undefined_windows` non è cambiato;
- [ ] M3 fatto, con `coverage` e `observations` identici a prima;
- [ ] M6 fatto, a firme e semantica invariate;
- [ ] M5 fatto **o** dichiarato rinviato con la ragione;
- [ ] i due campi di schema consegnati, `api sync` eseguito, **K1 comunicato a E**;
- [ ] `services risk-all` verde;
- [ ] nessun processo in ascolto su `6240`.

---

## 9. Quello che può andare storto in questo mandato

| Rischio | Sintomo | Cosa fare |
|---|---|---|
| M1 perde `undefined_windows` | un avviso utente sparisce, nessun test fallisce | Coprirlo **esplicitamente** in W0 prima di scrivere M1 |
| Si sostituisce il Sortino con `SemiDeviation` | numeri leggermente diversi, tutti i test verdi | La guardia D40 è già nell'oracolo se W0 è fatta bene |
| Si migra per velocità invece che per possesso | si tocca `summarize_drawdown`, che è **4× più veloce** di `MDD_Rel` | Il criterio è **D36**: il possesso, non i millisecondi |
| Il pavimento a zero viene rimosso di straforo dentro M2 | il VaR diventa negativo su serie stabili | È una **decisione separata**: si prende, si dichiara, si comunica a E |
