# Mandato N — Acquisizioni backend per L1, L2 e L3

| | |
|---|---|
| **Flusso** | W11 — aggiunto dopo la verifica dei mandati, vedi §1 |
| **Dominio** | backend, metriche acquisite da riskfolio |
| **Taglia** | M |
| **Lane** | porta `6248` · data dir `backend/data/test-risk-n` |
| **Dipende da** | nulla — parte appena il developer smaltisce le analisi di ondata 1 |
| **Consegna** | contratto **K8** a **E** |

> Regole comuni (Git, runtime, test, piano vivo): [`README.md`](./README.md) §5.
> Definizione di finito comune: [`README.md`](./README.md) §6.

---

## 1. Perché questo mandato è nato dopo gli altri

Non era previsto. È emerso dalla **verifica dei dieci mandati**, e la sua assenza era
il difetto più grave del piano.

Il registro decide quattro acquisizioni di metriche. Nessun mandato le implementava, e
il mandato **A** le **espelle esplicitamente**:

> «qualunque **acquisizione** (NEA, `Sharpe(rm=)`, UCI): sono funzionalità nuove, non
> migrazione» — [`A-…`](./A-backend-oracolo-e-migrazione.md) §6, sezione *Fuori*

Mentre il mandato **E** costruisce L1, L2 e L3 **assumendo che quei campi arrivino nel
payload**. Verificato con `grep` su tutto `backend/app`:

| Cerco | Trovato nel sottosistema rischio |
|---|---|
| `diversification` | 🔴 **zero occorrenze in tutto il backend** |
| `worst_realization`, `worst_day`, `worst_return` | 🔴 **zero** in `risk/`, `risk_plugins/`, `schemas/risk.py` |
| `herfindahl` | 🟡 esiste, ma **solo in AI Export** — mai nel rischio |

> Senza questo mandato, **E** scoprirebbe a metà lavoro che tre dei KPI che deve
> disegnare non esistono, e **A** sarebbe già chiuso.

### 1.1 Cosa è di questo mandato e cosa no

| Decisione | Cosa dice | Qui? |
|---|---|:---:|
| **D38** | `NEA` + diversification ratio come KPI di **L2** | ✅ |
| **D45** | `WR` come KPI di **L1** | ✅ (`RG` come colonna è del mandato **F**) |
| **D56** | `MDD`, `DaR`, `CDaR`, `UCI` in variante **`_Rel`** | ✅ |
| **D39** | `Sharpe(rm=…)` — Calmar, Martin — come risposta a **L3** | ❌ **resta ad A** |

⚠️ **Perché D39 non è qui.** `Sharpe(rm=…)` pretende la **matrice dei rendimenti**,
mentre a quel livello passiamo solo covarianza e pesi. È **esattamente** l'idraulica
mancante già registrata per **M5** in
[`../06-…`](../06-matematica-librerie-e-reimplementazioni.md) §7.-1. Chi fa M5 ha già
pagato metà di D39: duplicarla qui sarebbe farla due volte.

---

## 2. Cosa leggere prima

1. [`../04-…`](../04-decisioni-e-questioni-aperte.md) **D38**, **D45**, **D56** — per
   intero, comprese le misure riportate nella colonna di motivazione.
2. [`../06-…`](../06-matematica-librerie-e-reimplementazioni.md) **§7.1** (la famiglia
   drawdown e la differenza `_Abs`/`_Rel`) e **§7.3** (il setaccio delle 42 funzioni).
3. [`../01-…`](../01-tesi-e-quattro-domande.md) **§3** — a quale domanda risponde
   ciascuna delle quattro.
4. [`../02-verdetti-per-strumento.md`](../02-verdetti-per-strumento.md) per gli
   strumenti toccati: senza, si espone una metrica senza sapere cosa chiede l'utente.

Poi `wiki-search` su: metriche di rischio, concentrazione, drawdown.

---

## 3. ⚠️ La trappola di segno — da leggere prima di scrivere una riga

**Misurato**, non dedotto. Su una serie di 750 rendimenti:

```text
WR(r)       = +0,03851726      min(r) = −0,03851726
MDD_Rel(r)  = +0,5498945…
DaR_Rel(r)  = +0,5208000…
CDaR_Rel(r) = +0,5307924…
UCI_Rel(r)  = +0,3490355…
```

> ## 🔑 Riskfolio restituisce **magnitudini positive**. Il nostro schema usa **negativi**.
>
> `RiskKpiOutput.max_drawdown` è dichiarato `Field(..., le=0)`
> (`schemas/risk.py:644`): **deve essere negativo o zero**.
>
> Le cinque funzioni sopra restituiscono il **valore assoluto**. Passarne una
> direttamente al campo fa fallire la validazione — che è il caso **fortunato**.

Il caso sfortunato è peggiore e va nominato: se qualcuno «risolve» invertendo il
vincolo su un campo solo, dentro **lo stesso oggetto** convivono due convenzioni di
segno opposte, la UI ne disegna una sotto l'altra, e nessun test se ne accorge perché
ogni campo è internamente coerente.

**Regola**: una sola convenzione per output, dichiarata nel contratto **K8**, e un test
che la afferma per **ogni** campo nuovo. È la stessa classe di difetto del CVaR — una
grandezza plausibile e sbagliata, che nessuno controlla perché sembra a posto.

---

## 4. Gesto 1 — L2: concentrazione (D38)

### 4.1 Dove va, e perché lì non costa nulla

`RiskContributionOutput` (`schemas/risk.py:676-680`) è l'output di L2 e porta già
`portfolio_volatility`, `cash_weight` e gli `items` con i pesi.

E il plugin che lo produce legge **già** ciò che serve:

```python
# risk_plugins/risk_contribution.py:49-56
asset_ids = context.scope_asset_ids
weights   = [context.weights[asset_id] for asset_id in asset_ids]
```

> **Zero idraulica nuova.** I pesi sono già in mano al plugin, e `NEA` vuole solo
> quelli. Il diversification ratio vuole in più la covarianza, che lo stesso plugin
> calcola già per i contributi.

### 4.2 Le due metriche

| Metrica | Formula | Costo | Cosa aggiunge |
|---|---|---|---|
| **NEA** | `1/Σwᵢ²` — inverso di Herfindahl | 0,0025 ms | Quante posizioni *contano davvero*: su «3 grosse + 20 briciole» dà **4,12 su 23** |
| **Diversification ratio** | `Σ(wᵢσᵢ) / σ_portafoglio` | tre righe di NumPy sulla covarianza già calcolata | Quanto la correlazione sta *effettivamente* aiutando |

⚠️ **Vanno insieme, e la ragione è la loro debolezza reciproca** (**D38**): NEA è
**cieco alla correlazione**. Tre portafogli di dieci asset equipesati con ρ = 0 / 0,5 /
0,95 danno NEA **10,00 in tutti e tre**, mentre la volatilità reale va da 0,0038 a
0,0116. Il diversification ratio nello stesso test fa **3,15 → 1,35 → 1,02**: è lui a
vedere ciò che NEA non vede.

> Esporre NEA da solo produce un numero che **dice «sei diversificato» a un portafoglio
> che non lo è**. È il difetto esatto che L2 esiste per smascherare.

### 4.3 ⚠️ La coerenza con AI Export, che è un vincolo e non una cortesia

AI Export calcola **già** l'Herfindahl, in
`services/ai_export/components/portfolio_financial.py:208`, con questa semantica
dichiarata nel campo:

> *«Sum of squared nav_weight_percent across all positions. 10000 is fully concentrated
> in one position.»*
> *«Cash is included in the denominator but is not itself an HHI term.»*

L'identità è esatta, **verificata numericamente** su `w = [0,5 · 0,3 · 0,15 · 0,05]`:

```text
NEA(w)                    = 2,73972602739726
1/Σwᵢ²                    = 2,73972602739726
10000 / HHI_points        = 2,73972602739726      (HHI_points = 3 650)
```

Quindi **non c'è alcuna libertà di definizione**: sono la stessa grandezza in due unità.
Ma c'è una scelta semantica vera, e va presa **esplicitamente**:

> ## 🔑 La cassa entra o no nel denominatore?
>
> AI Export la mette nel denominatore ma non come termine. `RiskContributionOutput` ha
> un campo `cash_weight` separato.
>
> Se il rischio sceglie diversamente da AI Export, **la stessa applicazione dice due
> numeri diversi sulla concentrazione dello stesso portafoglio**, e l'utente non ha
> modo di sapere quale credere.

Si adotta la convenzione di AI Export, **oppure** si diverge con una ragione scritta e
una nota nella documentazione (mandato **I**). Non si decide per distrazione.

---

## 5. Gesto 2 — L1: la peggior giornata vissuta (D45)

`WR` è la peggior giornata **realmente accaduta**: non una stima, non un quantile.

Sta accanto al VaR **per contrasto**, ed è questo il suo valore:

```text
VaR 95%   «una giornata su venti va peggio di così»     ← soglia stimata sul campione
WR        «e la peggiore è stata questa»                ← fatto, accaduto, datato
```

**Dove va**: `RiskKpiOutput` (`schemas/risk.py:640-647`), che oggi porta `volatility`,
`max_drawdown`, `max_drawdown_duration_days`, `sharpe`, `sortino`.

⚠️ **Non** su `RiskVarCvarOutput` (`:820-835`), che è del mandato **A**: sarebbe il
posto semanticamente più vicino, ma metterebbe due scrittori sulla stessa classe. E il
mandato **E** ricompone comunque i livelli a partire da output diversi (§3.1 del suo
file: *«l'output di `historical_kpi` va spezzato»*), quindi la vicinanza a schermo non
richiede vicinanza nello schema.

> Se `WR` porta con sé **la data** in cui è accaduta, il numero smette di essere una
> statistica e diventa un episodio. Da concordare in **K8**: costa un campo.

⚠️ `MAD` **resta fuori** (D45): misura la stessa cosa della volatilità.

---

## 6. Gesto 3 — L1: la famiglia drawdown (D56)

Quattro misure, **tutte in variante `_Rel`**, e la variante non è un dettaglio.

| Misura | Cosa dice |
|---|---|
| **MDD** | la discesa peggiore dal picco |
| **DaR** | il quantile delle discese: «il 95% dei giorni sei sceso meno di così» |
| **CDaR** | ⚠️ **NON** la media delle discese oltre quel quantile — è la forma **Rockafellar-Uryasev**, normalizzata per **`alpha × T`** e non per il numero di osservazioni in coda |
| **UCI** | l'indice di ulcera: penalizza le discese **lunghe**, non solo quelle profonde |


> ### 🔴 Correzione del 18 Set — questa riga portava **il difetto**, non la definizione
>
> Diceva *« la media delle discese **oltre** quel quantile »*: **è la media aritmetica della coda,
> cioè esattamente lo stimatore che M2 corregge per il CVaR.**
>
> 🔑 **E N l'aveva già confutata, parola per parola, senza che nessuno glielo dicesse.**
> `acquired.py:128-131` (checkpoint `1aaea6949`) porta:
>
> > *« This is **not** the arithmetic mean of the worst `alpha` share of observations. It is the
> > Rockafellar-Uryasev form, whose tail integral is normalized by `alpha * T`… Writing the naive
> > mean here **reproduces exactly the historical CVaR defect this subsystem is being corrected
> > for**. »*
>
> e `:143` implementa `quantile + excess / (alpha * len(ordered))`.
>
> ⚠️ **La docstring di N è la confutazione del brief di N — e il disaccordo non l'ha visto
> nessuno, perché nessun gate confronta un brief col codice.**
>
> ### 🔴 Perché una specifica sbagliata che l'implementazione evita è pericolosa
>
> **Non danneggia nessuno oggi — ed è per questo che sopravvive.** La catena, e **ogni passo è
> localmente ragionevole**:
>
> 1. un revisore confronta codice e brief → conclude *« il codice è sbagliato »*;
> 2. lo corregge **verso il naive**;
> 3. il test **differenziale** di N (`assert computed != approx(naive_mean)`) diventa **rosso**;
> 4. un rosso differenziale **dopo una correzione plausibile** si legge come *« il test è sbagliato »*;
> 5. si rilassa l'asserzione → **si spedisce esattamente il difetto M2 per cui esiste questa campagna.**
>
> 🔑 **E il test che avevamo appena dichiarato salvo è l'anello che cede.**
>
> ### ✅ Perché proprio questa riga, e solo questa
>
> **Risultato nullo misurato da I**: **zero** occorrenze, in tutto il journal, che descrivano
> l'UCI come deviazione standard campionaria o Bessel. **Il trasporto non è sistematico: è
> specifico.** E delle quattro righe di questa tabella, **MDD, DaR e UCI sono giuste**; l'unica
> sbagliata è **l'unica la cui definizione corretta non ha forma breve**.
>
> > **Si trasportano le trappole che hanno una frase sbagliata fluente a disposizione.**
> > *« La media della coda peggiore »* è la frase che viene in mente per il CDaR. L'UCI non ne ha
> > una seducente — e infatti è intatto.
>
> 📌 **E l'ironia va nominata**: **due righe sotto** questa definizione c'è l'avvertimento
> `_Rel`/`_Abs`, *« verificato sul sorgente e ricostruito a mano »*, con l'11 % di scarto.
> **Siamo stati squisitamente attenti a una trappola di questa tabella e abbiamo scritto l'altra
> nella colonna delle definizioni.**

⚠️ **`_Rel` contro `_Abs` — verificato sul sorgente e ricostruito a mano** (D56, e la
trappola è già nell'oracolo di **A**): `_Abs` usa `cumsum` e misura in punti di
rendimento cumulato; `_Rel` usa `cumprod` e misura in **percentuale dal picco** — che è
l'unica cosa che la gente intende quando dice «ho perso il 30%». Sulla stessa serie:
`MDD_Abs` 0,227822 contro `MDD_Rel` 0,212860. **Scambiarle dà l'11% di scarto senza
alcun errore visibile.**

**Dove vanno**: su `RiskKpiOutput`, insieme a `WR`.

> ## ⚠️ Perché NON su `RiskDrawdownOutput`
>
> Sarebbe la casa naturale, ma `RiskDrawdownOutput` (`:945-1018`) **è del mandato A**,
> che vi aggiunge la serie underwater del contratto K1.
>
> La divisione che si adotta, e che va rispettata:
>
> | Classe | Contenuto | Scrittore |
> |---|---|---|
> | `RiskKpiOutput` `:640-647` | la **famiglia scalare** di L1: MDD, DaR, CDaR, UCI, WR | **N** |
> | `RiskDrawdownOutput` `:945-1018` | il **racconto per episodi** + la serie underwater | **A** |
>
> `max_drawdown` esiste già su `RiskKpiOutput` ed **è** MDD: va verificato che coincida
> con `MDD_Rel` prima di affiancargli le altre tre. Se non coincide, è una scoperta e va
> riportata, non aggiustata in silenzio.

---

## 7. Dove vive il calcolo

**Modulo nuovo**: `backend/app/services/risk/acquired.py`.

⚠️ **Non** `metrics.py`: è di **A**, che ci sta facendo M2, M1, M3, M6 e M5. Un secondo
scrittore su quel file durante la migrazione è il modo più rapido di rovinare entrambi
i lavori.

Il modulo nuovo:

- espone funzioni con **la nostra convenzione di segno**, non quella di riskfolio;
- riceve `numpy.ndarray`, mai `DataFrame` — le firme del rischio non cambiano;
- è coperto da test propri (§10).

---

## 8. ⚠️ `schemas/risk.py` — il terzo scrittore, e dove collide davvero

Tre mandati scrivono questo file da 1 126 righe. **Misurato dove collide, e non è dove
sembrava**:

| Regione | Scrittore | Righe |
|---|---|---|
| Classi di **scope** | **C** | `:537-585` |
| `RiskKpiOutput` (famiglia L1) | **N** | `:640-647` |
| `RiskContributionOutput` (concentrazione L2) | **N** | `:676-680` |
| `RiskVarCvarOutput` (bin istogramma) | **A** | `:820-835` |
| `RiskDrawdownOutput` (serie underwater) | **A** | `:945-1018` |
| **`__all__`** | 🔴 **tutti e tre** | **`:1067-1126`** |

> ## 🔑 Il conflitto vero è `__all__`, non le classi.
>
> Il file **finisce** con una lista `__all__` di sessanta nomi **ordinata
> alfabeticamente**. Chi aggiunge una classe deve inserire un nome **in mezzo** a
> quella lista.
>
> Appendere in coda al file — di solito il pattern multi-scrittore più sicuro — **qui
> non funziona**, perché in coda c'è `__all__`.

**Regola di risoluzione**, valida per A, C e N:

> `__all__` è **l'unica regione dell'intera campagna** dove una risoluzione meccanica
> del conflitto è autorizzata: **unione dei nomi + riordino alfabetico**. È
> semanticamente sempre corretta, perché è una lista ordinata di nomi esportati e
> nessuno dei tre ne rimuove uno.
>
> Ovunque altro vale la regola opposta: mai «ours», mai «theirs», mai un merge
> meccanico. Vedi [`README.md`](./README.md) §2.2.

**Buona notizia misurata**: N tocca `:640-680`, A tocca `:820-1018`. Le due regioni
sono **lontane 140 righe**, e nessuna delle due confina con l'altra: Git fonde senza
attrito. L'unico punto dichiarato è `__all__`.

---

## 9. Confini

**Di questo mandato**:

- `backend/app/services/risk/acquired.py` — **file nuovo**
- `backend/app/services/risk_plugins/historical_kpi.py` — aggiunte **additive**
- `backend/app/services/risk_plugins/risk_contribution.py` — aggiunte **additive**
- `backend/app/schemas/risk.py` → **solo** `RiskKpiOutput` e `RiskContributionOutput`
- i test propri

⚠️ **Additive significa additive**: nessun campo esistente cambia nome, tipo, unità o
segno. Un client che ignora i campi nuovi deve continuare a funzionare identico.

**Fuori**, tassativamente:

- `metrics.py`, `signal_helpers.py`, `correlation.py` → mandato **A**
- `RiskVarCvarOutput` e `RiskDrawdownOutput` → mandato **A**
- le classi di **scope** → mandato **C**
- `Sharpe(rm=…)` / D39 → mandato **A**, coda di M5
- gli altri **sette** plugin: `comparison`, `drawdown_summary`, `historical_var`,
  `portfolio_optimization`, `simulation`, `stress`, `correlation`
- qualunque cosa nel frontend: i campi si **espongono**, non si disegnano

> ### Nota per il mandato C, da non fraintendere
>
> La definizione di finito di **C** chiede che `git diff` su `risk_plugins/` sia
> **vuoto**. Resta vera: C lavora nel **proprio** worktree e non tocca alcun plugin.
>
> Ma dopo l'integrazione `risk_plugins/` **avrà** le modifiche di N su due file. Chi
> verifica in **J** deve saperlo, o scambierà un lavoro previsto per una violazione.

---

## 10. Test

L'oracolo di **A** (`test_risk_metrics_oracle.py`, selettore `risk-oracle`) è il posto
giusto per le coppie nostra/libreria — ma **è di A**. Questo mandato:

- scrive i propri test in un file proprio;
- se serve un selettore nuovo nel catalogo, lo **chiede ad A**, che possiede
  `scripts/test_runner/_backend_services.py` ([`README.md`](./README.md) §2.5).

| Cosa | Comando |
|---|---|
| Schemi | `schemas risk` |
| KPI e contributi | `services risk-all -k kpi`, `services risk-all -k contribution` |
| API | `api risk` |
| Integrazione | `services risk-all` |

```bash
PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc \
  pipenv run python dev.py test --test-port 6248 --data-dir backend/data/test-risk-n \
  services risk-all
```

I test che contano più degli altri, perché coprono i due modi di sbagliare
silenziosamente:

1. **il segno** — per **ogni** campo nuovo, un test che afferma la convenzione (§3);
2. **l'identità con AI Export** — `NEA == 10000 / herfindahl_index_points` sullo stesso
   portafoglio, così la divergenza fallisce invece di passare inosservata (§4.3);
3. **`max_drawdown == MDD_Rel`** — se non coincide, è una scoperta (§6);
4. **NEA cieco alla correlazione** — tre portafogli con ρ 0 / 0,5 / 0,95 danno lo stesso
   NEA e diversification ratio **diversi**. È il test che impedisce di esporre NEA da
   solo in futuro.

Per scrivere o riparare test si invoca **`test-author`**. Prima di dichiarare flaky un
rosso: **`test-triage`**.

---

## 11. Contratto K8 → mandato E

Da concordare **prima** di scrivere il codice, tramite il coordinatore:

- i **nomi** dei campi nuovi su `RiskKpiOutput` e `RiskContributionOutput`;
- la **convenzione di segno**, dichiarata una volta per output (§3);
- l'**unità** di NEA: numero di posizioni equivalenti, non una percentuale;
- se `WR` porta con sé **la data** (§5);
- la convenzione sulla **cassa** in NEA (§4.3), che E deve poter scrivere a schermo;
- la nota che **NEA e diversification ratio vanno mostrati insieme** — E non deve poter
  mostrarne uno solo senza saperlo.

Dopo la modifica di schema: **`./dev.py api sync`**.

---

## 12. Definizione di finito

Oltre a quella comune ([`README.md`](./README.md) §6):

- [ ] `acquired.py` esiste, con la **nostra** convenzione di segno, e non tocca `metrics.py`;
- [ ] NEA e diversification ratio su `RiskContributionOutput`, **insieme**;
- [ ] la convenzione sulla **cassa** è decisa, scritta e coerente con AI Export — o la
      divergenza è motivata per iscritto;
- [ ] il test `NEA == 10000 / herfindahl_index_points` passa;
- [ ] `WR` su `RiskKpiOutput`, con il segno dichiarato e testato;
- [ ] MDD, DaR, CDaR, UCI in variante **`_Rel`**, con il test che fallisce allo scambio
      con `_Abs`;
- [ ] verificato che `max_drawdown` **coincida** con `MDD_Rel`, o la differenza è
      riportata;
- [ ] **nessun campo esistente modificato** — solo aggiunte;
- [ ] `git diff` limitato ai cinque file di §9;
- [ ] `api sync` eseguito;
- [ ] `services risk-all`, `schemas risk`, `api risk` verdi;
- [ ] **K8 consegnato e comunicato a E**;
- [ ] nessun processo in ascolto su `6248`.

---

## 13. Quello che può andare storto in questo mandato

| Rischio | Sintomo | Cosa fare |
|---|---|---|
| Segno invertito su un campo solo | Due convenzioni **dentro lo stesso oggetto**, test tutti verdi | Un test di segno per **ogni** campo nuovo, §3 |
| `_Abs` invece di `_Rel` | 11% di scarto, nessun errore | Il test che fallisce allo scambio, §6 |
| NEA esposto da solo | Un portafoglio correlato 0,95 sembra diversificato | Il test dei tre ρ, §10.4 |
| Divergenza da AI Export | Due numeri diversi sulla stessa concentrazione | Il test di identità, §4.3 |
| Si tocca `metrics.py` «solo un attimo» | Conflitto con la migrazione di A | È di A. Si chiede, non si tocca |
| Si tira dentro D39 | Serve la matrice dei rendimenti, cioè M5 | È di A. Si riporta al coordinatore |
