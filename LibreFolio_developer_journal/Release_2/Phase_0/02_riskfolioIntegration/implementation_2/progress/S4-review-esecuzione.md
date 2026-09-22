# S4 — Review post-integrazione · piano vivo

| | |
|---|---|
| Mandato | **S4 — review del developer su L4** (round 3) |
| Worktree | `e-alfy-friendly-bassoon` · ramo `e-alfy-h-monte-carlo` |
| Baseline | `5b16281f766beef7ff4a23e86f24b18ef3508555` ✅ verificata |
| Revisione integrata | `fa38f6747` — `quant/` e `L4Simulation.svelte` **identici**, verificato dal coordinatore |
| Corsia | porta **6156** · data dir **`/tmp/librefolio-r2-s4`** |
| Coordinatore | sessione `0000738d-b7e0-4561-9454-cf5ab2c439ca` |

> Aggiornato **dopo ogni passo**, non alla fine.

---

## Passo 1 — Le due chiavi grezze a schermo ✅ 2026-09-21

**Misura prima della modifica**, su tutte e quattro le lingue:

| percorso | en | it | fr | es |
|---|---|---|---|---|
| `risk.simulation.terminalMean` | ❌ | ❌ | ❌ | ❌ |
| `risk.metrics.terminalMean` | ✅ | ✅ | ✅ | ✅ |
| `risk.simulation.probabilityOfLoss` | ❌ | ❌ | ❌ | ❌ |
| `risk.metrics.probabilityOfLoss` | ✅ | ✅ | ✅ | ✅ |

> **Note implementazione**: il coordinatore ne indicava **due**. Invece di fidarmi
> dell'elenco ho validato **ogni** `$t(...)` del file contro `en.json` — 12 chiavi, 10
> risolte, **esattamente quelle due** non risolte. Poi ho esteso la validazione a
> **tutto `components/risk/`**: **2 su tutto il sottoalbero**. Il difetto è isolato, non
> è la punta di una classe.
>
> Percorso corretto da `simulation.` a `metrics.`. **Nessuna chiave nuova creata**:
> esistevano già tutte e quattro. `+2/-2`.

**Cancelli**: validatore chiavi → `non risolte: 0` · `npx prettier --check` → pulito.

---

## Passo 2 — I numeri impossibili della simulazione ✅ 2026-09-21 (ANALISI)

**Le tre ipotesi del mandato, con l'esito accanto.**

### ❌ Ipotesi 1 — «il fattore di annualizzazione entra due volte» · FALSIFICATA due volte

1. **Strutturalmente**: `annualization_factor` è un parametro di
   `estimate_gbm_parameters`, che sta **solo** sul ramo parametrico
   (`_build_parametric_request`). Il default è il block bootstrap, che passa da
   `align_simple_returns` → **la matrice grezza, nessuna scala**. Il docstring di
   `estimation.py:1` lo dice: *«for the first GBM simulation model»*.
2. **Per misura**: ho dato al motore matrici con σ **nota** e ho riletto la σ implicita
   da `terminal_asset_log_covariance`.

| σ in ingresso | blocco | attesa `σ·√365` | implicita | rapporto |
|---:|---:|---:|---:|---:|
| 2,000 % | 1 | 0,3265 | 0,3235 | **0,9906** |
| 4,545 % | 1 | 0,7421 | 0,7351 | **0,9906** |
| 8,686 % | 1 | 1,4182 | 1,4048 | **0,9906** |
| 8,686 % | 5 | 1,4182 | 1,4803 | **1,0438** |

> Il motore restituisce la dispersione che riceve. Il **+4,4 %** con blocchi da 5 è
> l'inflazione di varianza del ricampionamento a blocchi, non un fattore ripetuto: un
> fattore ripetuto darebbe **√252 ≈ 15,9** o **252**.

### ❌ Ipotesi 2 — «la media non converge coi cammini» · NON RIPRODOTTA, e non indipendente

Sul router vero, corsia pulita, stessa finestra e stesso orizzonte:
`512 → +41,5 %` · `2048 → +41,4 %` · `4096 → +41,8 %` · `16384 → +41,9 %`. **Scarto 1 %**.

Il 19× del mandato **non esiste sui dati puliti**. Ma esiste **appena un punto anomalo
entra nella finestra**, e il discriminante dice perché:

| | media | mediana |
|---|---|---|
| dati puliti | 706 → 761 % (**+8 %**) | 491 → 502 % (**+2 %**) |
| un punto ×3,13 | 257 360 → 555 728 → 300 289 % (**oscilla 2,2×**) | 5 243 → 4 121 % (**converge**) |

> 🔑 **La mediana converge, la media no, sugli stessi cammini e con lo stesso seme.**
> Se il motore fosse instabile, oscillerebbero entrambe. Quindi non è un secondo
> difetto: è **la media campionaria di una distribuzione con σ orizzonte ≈ 3**, che non
> è stimabile con i cammini che il prodotto può permettersi. **Il difetto è nella
> statistica pubblicata, non nel codice che la calcola.**

### ✅ Ipotesi 3 — «manca la guardia finestra/orizzonte» · CONFERMATA, e quantificata

La guardia esistente è `min_observations = 30` (`risk_plugins/simulation.py:185`): **un
fondo assoluto, senza alcun riferimento a `horizon_days`**.

Il criterio giusto non è un fondo, è **un rapporto**. Il bootstrap ripesca ogni
osservazione `horizon_days / n_osservazioni` volte per cammino:

| n_oss | ripetizioni su 365 g | un punto ×3,13 diventa | deriva spostata |
|---:|---:|---:|---:|
| 93 | **3,92** | ×88 (**+8 708 %**) | +1,227 %/g |
| 360 | **1,01** | ×3,18 (+218 %) | +0,317 %/g |

**Stessa contaminazione, stesso motore, 40× di danno in più** solo per la finestra.
Misurato end-to-end sul portafoglio a pesi uguali:

| finestra | pulita | +1 punto ×3,13 | amplificazione |
|---|---:|---:|---:|
| 3 mesi (66 oss) | +754 % | **+312 428 %** | **414×** |
| 1 anno (261 oss) | +25 % | +337 % | 13× |

> **⚠️ Fuori pista — il difetto si vede anche SENZA contaminazione.** Sugli stessi dati
> puliti e con lo stesso orizzonte: **3 mesi → +754 %**, **1 anno → +25 %**. Trenta volte,
> per la sola finestra. La contaminazione non crea il difetto: lo rende spettacolare.

### 🔴 Quello che NON si riproduce: i numeri del developer

| caso | misura del coordinatore | mia corsia pulita |
|---|---:|---:|
| 3 mesi · h365 | +25 690 872 % | **+41,4 %** |
| 1 anno · h365 | +117 % | +10,7 % |
| 3 mesi · h30 | +16,4 % | +1,0 % |

E nemmeno le sue σ:

| asset | sua misura | mia corsia pulita |
|---|---:|---:|
| Microsoft | 8,686 % | **1,831 %** |
| Apple | 4,545 % | **1,813 %** |
| Ethereum | 2,920 % | **4,874 %** |
| Bitcoin | 2,046 % | **4,583 %** |
| prestiti | 0,270 % | 0,273 % ✅ |

> Solo i prestiti coincidono. E nei suoi numeri **un'azione è quattro volte più volatile
> di Bitcoin**; nella corsia pulita è il contrario. Rilevatore di contaminazione sulla
> mia corsia: `SELECT COUNT(*) FROM price_history WHERE close = ROUND(close,2)` → **0**.

### L'incertezza che la banda non mostra

La banda `p05…p95` è la dispersione dei cammini **condizionata alla deriva della
finestra**. Ma la deriva è **essa stessa una stima**, con errore standard `σ/√n`:

| asset | finestra | n | ES della deriva su 365 g | fattore al 95 % |
|---|---|---:|---:|---:|
| BTC-USD | 3 mesi | 92 | 1,744 | **×/÷ 30,5** |
| BTC-USD | 1 anno | 365 | 0,875 | ×/÷ 5,6 |
| MSFT | 3 mesi | 66 | 0,823 | ×/÷ 5,0 |

> Con 92 osservazioni la proiezione a un anno di Bitcoin è incerta **di un fattore 30 in
> su e in giù**, e **la banda mostrata non contiene questa incertezza**.

**Stato**: nessuna modifica al motore. In attesa della revisione del coordinatore.

---

## Comandi e artefatti

| cosa | dove |
|---|---|
| fedeltà del motore alla σ | `/tmp/libreFolio_s4_sigma.py` |
| riproduzione end-to-end | `/tmp/libreFolio_s4_repro.py` |
| sensibilità a un punto anomalo | `/tmp/libreFolio_s4_outlier.py` |
| convergenza media contro mediana | `/tmp/libreFolio_s4_converge.py` |
| σ grezze dalla corsia | `/tmp/libreFolio_s4_rawsigma.log` |

⚠️ Le sonde girano **in processo**, senza server e senza consumare la corsia. Richiedono
la guardia `if __name__ == "__main__":` — il worker `spawn` reimporta il modulo, e senza
guardia la sonda si riesegue ricorsivamente (13,5 MB di output al primo tentativo).

---

## Passo 3 — Il verdetto richiesto dallo sviluppatore ✅ 2026-09-21

> **Regola posta dallo sviluppatore**: «se il problema sono i dati sintetici ce ne
> freghiamo, al massimo rifaccio i dati; se invece è un problema matematico va risolto».
> Il discriminante: la `p50` pubblicata coincide con l'estrapolazione ingenua del
> realizzato, oppure il motore **aggiunge** deriva?

> **Nota implementazione**: non ho ricostruito gli ingressi del motore, li ho
> **intercettati**. Monkeypatch di `run_simulation` dentro `risk_plugins/simulation.py`
> che registra la `SimulationEngineRequest` vera — matrice storica, pesi, peso di cassa,
> orizzonte — e poi delega all'originale. Realizzato e simulato poggiano così sulla
> **stessa matrice**, e nessuna divergenza può nascere da una mia ricostruzione.
> Sonda: `/tmp/libreFolio_s4_verdict.py`.

### ③ contro ② — il motore estrapola fedelmente, ed è una **legge**

Sei finestre, stesso orizzonte 365, stesso portafoglio, stesso seme.
«Ingenua (2b)» = `cassa + Σ wᵢ·(Πₜ(1+rᵢₜ))^(365/n) − 1`, cioè la struttura esatta di
`resampling.py:190`, non un'estrapolazione a livello di portafoglio.

| finestra | n_oss | ripetizioni | ingenua (2b) | p50 pubblicata | **p50/ingenua** | media | media/mediana |
|---|---:|---:|---:|---:|---:|---:|---:|
| 95 giorni | 93 | 3,92× | +31,57 % | +33,22 % | **1,0126** | +42,19 % | 1,0673 |
| 140 giorni | 138 | 2,64× | +8,54 % | +10,28 % | **1,0160** | +12,56 % | 1,0206 |
| 190 giorni | 188 | 1,94× | +1,97 % | +2,92 % | **1,0093** | +3,47 % | 1,0053 |
| 250 giorni | 248 | 1,47× | +8,21 % | +9,49 % | **1,0118** | +10,40 % | 1,0083 |
| 365 giorni | 360 | 1,01× | +8,76 % | +9,93 % | **1,0108** | +10,80 % | 1,0078 |
| 540 giorni | 360 | 1,01× | +8,76 % | +9,93 % | **1,0108** | +10,80 % | 1,0078 |

🔑 **Il rapporto sta fra 1,009 e 1,016 su tutte e sei**, mentre le ripetizioni vanno da
1,01× a 3,92×. **Il motore aggiunge l'1 % e non di più, indipendentemente dalla finestra.**
Due punti sarebbero stati una coincidenza; sei che non si muovono sono una legge.

> **③ ≈ ②. L'aritmetica è corretta. Non è matematica rotta.**

### ④ Il rapporto media/mediana sulla corsia pulita

**1,005 – 1,067.** Il `2 751` del referto originale era **interamente contaminazione**.
L'inflazione lognormale attesa con σ portafoglio 0,494 %/g su 365 giorni è
`exp(σ²h/2) = 1,004`; il resto è la coda destra della fetta crypto.

### ⚠️ Fuori pista — correzione di una mia misura precedente

Nel referto del passo 2 avevo scritto «stessi dati puliti, 3 mesi → **+754 %**,
1 anno → **+25 %**, trenta volte». Quei due numeri vengono dalla mia sonda a
**pesi uguali**, non dal portafoglio del prodotto. Sul portafoglio vero —
49,3 % cassa, 2,4 % crypto — gli stessi due casi danno **+42,2 %** e **+10,8 %**,
cioè **3,9×**, non trenta.

> **Ho riportato un soggetto sintetico con l'autorità di quello reale.** È la stessa
> forma che questa campagna insegue, commessa da me nell'atto di riferirla.

### 🔴 Ma il difetto si riproduce su dati puliti — in **scope asset**

Il portafoglio nasconde il difetto perché è per metà liquido. Il motore però serve
anche lo scope asset (`supported_scopes` include `ASSET`). Bitcoin, finestra 95 giorni,
**corsia pulita, nessuna contaminazione**:

| orizzonte | ripetizioni | p05 | **p50** | p95 | media | prob. perdita |
|---:|---:|---:|---:|---:|---:|---:|
| 30 g | 0,32× | −11,7 % | +24,4 % | +78,8 % | +27,6 % | 15,58 % |
| 93 g | 1,00× | +9,1 % | +100,2 % | +271,0 % | +113,9 % | 3,10 % |
| 180 g | 1,94× | +61,9 % | +281,9 % | +779,6 % | +333,7 % | 0,59 % |
| **365 g** | **3,92×** | **+348,7 %** | **+1 400,4 %** | **+5 020,3 %** | +1 888,0 % | **0,01 %** |

**L'assurdità è monotona nel rapporto `orizzonte / n_osservazioni`**, e il quinto
percentile arriva a dire che nel caso peggiore si quadruplica il capitale.

### 🔴 E il controllo che nessuna delle due misure precedenti conteneva

**Stesso asset, stesso orizzonte, stesso giorno, stesso motore.** Cambia solo la finestra:

| finestra | n_oss | p05 | **p50 a 365 g** | p95 | **prob. perdita** |
|---|---:|---:|---:|---:|---:|
| 95 giorni | 93 | +348,7 % | **+1 400,4 %** | +5 020,3 % | **0,01 %** |
| 365 giorni | 360 | −85,9 % | **−39,1 %** | +167,0 % | **70,74 %** |

> 🔑 **La mediana passa da +1 400 % a −39 %, e la probabilità di perdita da 0 % a 71 %,
> per una tendina che l'utente legge come «quanta storia guardo».** Entrambi i numeri,
> presi da soli, sembrano plausibili. Nessuno dei due si annuncia come sbagliato.

### ⑤ L'incertezza: **non è inventata**, ed è più grande della banda

`σ/√n` è l'errore standard della media. Il worker riceve già `historical_returns`
(la matrice intera) — **σ e n sono entrambi in mano sua, zero ingressi nuovi**. L'ho
calcolato dentro l'intercettazione della richiesta vera, non da dati miei.

Fattore al 95 % sulla sola deriva = `exp(1,96 · H · σ/√n)`, contro l'ampiezza
`(1+p95)/(1+p05)` della banda che oggi pubblichiamo:

| scope | finestra | n | σ | ampiezza banda | **incertezza deriva** |
|---|---|---:|---:|---:|---:|
| portafoglio | 95 g | 93 | 0,492 %/g | ×1,79 | **×/÷ 1,44** ⚠️ |
| portafoglio | 365 g | 360 | 0,501 %/g | ×1,22 | **×/÷ 1,21** |
| solo Bitcoin | 95 g | 93 | 4,581 %/g | ×11,41 | **×/÷ 29,90** |
| solo Bitcoin | 365 g | 360 | 4,593 %/g | ×18,92 | ×/÷ 5,65 |
| solo Apple | 95 g | 67 | 1,811 %/g | ×3,33 | **×/÷ 4,87** |
| solo Apple | 365 g | 258 | 1,797 %/g | ×3,05 | ×/÷ 2,23 |

> **In quattro casi su sei l'incertezza non mostrata è comparabile o maggiore
> dell'intera banda mostrata.** La banda non è una finzione: è **metà** della storia,
> ed è la metà più stretta.

### Osservazione minore

Finestra 540 giorni → n_oss **360**, identica a quella da 365: i dati non arrivano più
indietro. Chiedere più storia restituisce in silenzio la stessa storia. Non un difetto
del motore, ma chiunque tari una guardia sul rapporto deve saperlo.

### Sonde di questo passo

| cosa | dove |
|---|---|
| realizzato, ingenua, p50, media/mediana, σ/√n | `/tmp/libreFolio_s4_verdict.py` |
| la legge su sei finestre + banda contro deriva | `/tmp/libreFolio_s4_law.py` |
| monotonia nel rapporto e controllo di finestra | `/tmp/libreFolio_s4_guard.py` |

**Stato**: nessuna modifica al motore. In attesa della decisione di prodotto.

---

## Passo 4 — La forma dell'incertezza, e una cecità del cancello i18n ✅ 2026-09-21

Decisione dello sviluppatore: **si fa l'incertezza**; la guardia sull'orizzonte va nel
backlog; la media non si tocca. Condizione posta: *«solo se non te lo devi inventare»* —
soddisfatta, `σ/√n` è l'errore standard della media e il worker ha già la matrice.

### La forma approvata

| domanda | risposta |
|---|---|
| **dove** | nella riga della banda (`:205`, `risk-simulation-band-range`), non sotto il cono, non in `SimulationProvenance` |
| **come** | il fattore **applicato** (`mediana +33,2 % → fra +10,7 % e +60,3 %`), mai nudo; moltiplicativo perché la grandezza è composta |
| **cosa dice** | che **la deriva è essa stessa una stima, da N osservazioni** — non «il risultato è incerto», che la banda dice già |
| **quando supera** | cambia **natura**, non dimensione: da nota grigia ad avvertimento, e la banda viene qualificata |

Il confronto è fra `exp(1,96·H·σ/√n)` e `(1+p95)/(1+p05)`: **entrambe moltiplicative,
quindi la soglia è il rapporto fra le due e non un numero da scegliere.** È la differenza
con la guardia sull'orizzonte, che una soglia arbitraria ce l'ha — ed è la ragione per cui
quella è andata nel backlog e questa no.

### 🔴 Fuori pista — l'`i18n audit` è cieco su un terzo del catalogo

Cercando se la chiave esistesse ho trovato `risk.simulation.regimeTruncated`: presente in
**quattro lingue**, **zero riferimenti** in `.svelte`/`.ts`, introdotta da `e7836b46a`.
Una divulgazione scritta, tradotta e mai resa. Ma l'audit non la elenca fra le 122.

**Misurato importando la funzione dell'audit, non leggendo la regex:**

```
RiskResultFrame.svelte:27    const key = `risk.${prefix}.${code}`;
                                          ↑ interpolazione al PRIMO segmento
audit  ->  prefisso "risk."  ->  rstrip(".")  ->  "risk"
is_key_potentially_used:  key.startswith("risk")  ->  True per tutte le 282
```

| | |
|---|---:|
| prefissi radice **nudi** | **12** |
| chiavi da essi schermate | **954 su 2 886 = 33,1 %** |
| `importWizard` · `risk` · `signals` · `common` · `chartSettings` | 273 · 282 · 148 · 120 · 102 |

> **L'audit non può far comparire una chiave `risk.*` fra gli inutilizzati. Mai.**
> Il `0 risk.* inutilizzate` del round 2 era vero **come uscita** e non misurava nulla.

⚠️ **Ipotesi del coordinatore falsificata**: la cecità non nasce dal sottoalbero
`risk.simulation.mode.*` di `L4Simulation.svelte` ma dalla **radice nuda** di un **altro
file**, e non copre un sottoalbero ma **l'intero namespace**.

⚠️ **E una mia sovrastima, non registrata**: la regola ancorata al punto dà **63** orfane
`risk.*`. Non lo sono. `translatedCode(prefix: 'errors' | 'warnings', …)` è un'**unione
tipizzata**: almeno 14 sono legittimamente dinamiche. **L'unica orfana provata per grep
resta `regimeTruncated`**; le altre 48 sono *non verificate*, non *morte*.

🔑 **E la stessa riga dice come si ripara**: l'insieme esatto dei prefissi è già scritto
nel tipo. **L'audit lo butta via e ripiega sul troncamento — la cecità è una rinuncia,
non un limite.**

**Stato**: forma approvata, chiavi in attesa di ratifica, nessuna riga sul motore.

---

## Passo 5 — Implementazione dell'incertezza di stima ✅ 2026-09-21

> **Nota implementazione**: autorizzato dallo sviluppatore («ok aggiungere l'incertezza»)
> con la condizione *«solo se non te lo devi inventare»*, soddisfatta: `σ/√n` è l'errore
> standard della media e il worker ha già la matrice. Nessun ingresso nuovo.

### Superfici, tutte additive

| file | delta | cosa |
|---|---|---|
| `quant/estimation.py` | +45 | `estimate_drift_uncertainty()`, costante `_NORMAL_95_PERCENT`, `import math`, `__all__` |
| `quant/__init__.py` | +2 | riesporto |
| `schemas/risk.py` | +16 | due campi `Optional = None` + `validate_drift_uncertainty_disclosure` |
| `risk_plugins/simulation.py` | +33 | import, `_drift_uncertainty()`, due kwargs all'unica costruzione |
| `l4/driftUncertainty.ts` | **nuovo** | `buildDriftUncertainty()` — la vista, pura |
| `l4/L4Simulation.svelte` | +37/−6 | due stati, `data-exceeds-band` |
| `en/it/fr/es.json` | +2 ciascuno | `driftUncertainty`, `driftUncertaintyWide` |
| `test_risk_simulation.py` | +237 | 6 test (test-author) |
| `l4/driftUncertainty.test.ts` | **nuovo** | 14 test (test-author) |

### ⚠️ Fuori pista 1 — l'esempio ratificato era misurato su un portafoglio inesistente

La sonda faceva `matrix @ weights / weights.sum()`: **rinormalizzava sulla fetta
rischiosa**, ma la fixture è **49,31 % cassa**.

```
fetta rischiosa    ×/÷ 1,44  →  −7,5 % … +91,8 %   ← ratificato, FALSO
portafoglio vero   ×/÷ 1,20  →  +10,7 % … +60,3 %  ← implementato
```

La versione a fetta **lascia rimpicciolire anche la metà che non si muove**. Corretto in
`§ forma` sopra. **Scope asset invariato** (pesi `[1.0]`) — verificato: è il controllo che
*non* doveva muoversi, e infatti non si è mosso.

### ⚠️ Fuori pista 2 — la mia sonda stampava una soglia inventata

Tre stati (`stretto / comparabile / LARGO`) con `comparabile = fattore > banda × 0,6`.
**Quel `0,6` l'ho scelto io scrivendo la sonda.** Nella UI ne sono arrivati **due**:
`fattore ≤ banda` / `fattore > banda`, l'unico confronto senza numero scelto.

> Una sonda che stampa tre stati insegna che gli stati sono tre. Il difetto sarebbe
> migrato dalla sonda alla UI attraverso la mia stessa tabella di misure.

### ⚠️ Fuori pista 3 — ho consegnato allo specialista una fixture ricostruita come misurata

Nel prompt a `test-author` ho scritto «real measured fixtures» per tre righe, ma i
`p05`/`p95` di Apple **non li avevo mai misurati**: la sonda stampava solo `p50` e lo
span. Li avevo ricostruiti. Il test-author ha ricomputato e ha trovato l'incoerenza
(`×3,386` contro il mio `×3,33`) **senza sapere che era una ricostruzione**.

✅ Riparato misurando davvero: fixture sostituite con i valori grezzi del backend.

🔑 **E la misura vera ha aggiunto un fatto che nessuno dei due sapeva**: i letterali
**non sono stabili**. Dopo un `db populate --force` la stessa domanda dà `n` 93→96,
Bitcoin `29,90`→`27,46`, Apple `4,87`→`4,76`. **I verdetti no**: stretto / LARGO / LARGO
in entrambe le popolazioni. Il commento del file adesso lo dice, così nessuno tenta di
«aggiornarli» credendoli costanti.

### ⚠️ Fuori pista 4 — anche `services risk-simulation` svuota la corsia

Il vincolo registrato riguardava `services risk-all`. **Vale anche per
`risk-simulation`**: dopo la corsa del test-author, `e2e_test_user` non esisteva più e la
sonda è morta con `NoResultFound`. Ripopolato con `db populate --force`.

### Cancelli — comandi esatti ed esiti

```
ruff check  (4 file backend)                              All checks passed!
black --check (4 file backend)                            4 files unchanged
api risk                                                  11 passed
api sync                                                  generated.ts: 4 occorrenze drift_uncertainty
front check (svelte-check)                                0 errors, 41 warnings in 2 file NON miei
prettier --check (svelte, .ts, .test.ts, 4 json)          clean
validatore chiavi $t() su L4Simulation.svelte             13 chiavi, 0 irrisolte, placeholder coerenti 4/4
vitest driftUncertainty + 3 sorelle                       65 passed (4 file)
services risk-simulation                                  35 passed (29 + 6 nuovi)
services risk-all                                         406 passed (400 + 6)
lsof -nP -iTCP:6156 -sTCP:LISTEN                          nessun listener
git diff --check                                          pulito
```

### Debito dichiarato, non nascosto

- `driftUncertainty.test.ts` **non è nel catalogo** (`check-orphans` lo elenca). Non
  possiedo `_frontend_portfolio.py`: va nella stessa riga 117 dove mancano già
  `simulationModes.test.ts` e `simulationParameters.test.ts`. **Finché non c'è, per la
  definizione del progetto quel test non esiste.**
- Nessun test monta `L4Simulation.svelte`: i due stati sono coperti come funzione pura,
  non come DOM. Servirebbe jsdom + store, altro file e altra azione del runner.
- `risk.simulation.regimeTruncated` resta orfana (debito di S4, round 2).

**Stato**: implementato, tutti i cancelli verdi, **`FROZEN`**. Nulla stageato.
