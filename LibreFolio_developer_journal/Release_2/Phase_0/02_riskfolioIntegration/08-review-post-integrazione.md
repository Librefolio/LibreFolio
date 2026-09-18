# Review post-integrazione — il pannello Rischio a undici mandati fusi

> **Data**: 18 settembre 2026 · **Revisione**: `106bdb86a` + `abf31d160`
> **Metodo**: osservazione diretta sull'app in esecuzione (`localhost:6150`, DB di test seminato),
> più misura sul codice. **Ogni affermazione qui sotto ha accanto il comando che l'ha prodotta.**
> Nulla è dedotto dai rapporti dei mandati.

---

## 1. Cosa è riuscito, e va detto per primo

**La direzione c'è, ed è la cosa che mancava.** Il muro di metriche indistinte è sostituito da
quattro livelli, ciascuno con una domanda in testa:

```
L1  Quanto può fare male?
L2  Sono diversificato come credo?
L3  Sto venendo pagato per questo rischio?
L4  Cosa succede se…?
```

**Quattro successi misurati:**

| | prova |
|---|---|
| **Le quattro lingue reggono** | `i18n audit`: **2 880 chiavi complete × 4 lingue**, 0 incomplete |
| **Dashboard e Broker Detail montano lo stesso pannello** | `RiskLevelsPanel` unico, nessuna copia divergente |
| **L1 insegna l'asimmetria** | «durata 19 giorni · recupero richiesto **+4,7 %**» dopo una caduta del −4,5 % — il numero che spiega perché una perdita costa più di quanto sembri |
| **Il denaro sta accanto alla percentuale** | `−1,3 %` → `−175,91 €`: la domanda «quanto fa male» ha una risposta in euro |

**E l'impianto sotto è solido**: 679 test API, 4 117 servizi, 2 192 schemi e rischio,
`front check` a **0 errori**. Il backend calcola; il contratto tiene.

> **Il problema non è ciò che è stato costruito. È ciò che non è stato collegato.**

---

## 2. 🔴 La scoperta che spiega quasi tutte le altre

Tre mandati hanno **costruito**, uno doveva **consumare**, e l'innesto non è mai avvenuto.
Non è un'opinione: sono tre `grep`.

| chi ha costruito | cosa | consumatori oggi |
|---|---|---:|
| **D** | `RiskMetricCard` — 131 righe + **187 di test** | 🔴 **0** |
| **A** | `underwater_series`, `return_bins`, `var_bin_edge` (contratto K1) | 🔴 **0 su 3** |
| **I** | **22 pagine** di documentazione per metrica | 🔴 **0 link** |

E i sei `DocsLink` che **E** ha scritto puntano tutti a `user/analysis/risk.md#…` —
**una cartella che non esiste**:

```bash
$ ls mkdocs_src/docs/user/analysis/
ls: No such file or directory
```

> 🔑 **La forma del fallimento è sempre la stessa**: ogni mandato vedeva **solo il proprio albero**.
> D non poteva vedere che E non lo avrebbe importato; I non poteva vedere che E stava scrivendo i
> link; A non poteva vedere che i suoi campi sarebbero rimasti spenti. **Il difetto non è in nessuno
> dei quattro lavori: è nella loro relazione** — la stessa cosa che, a livello di file, aveva già
> prodotto il conflitto D↔E sugli spec (§36 di `STATO.md`).
>
> 📌 **Conseguenza per la pianificazione**: il prossimo giro non va diviso per *componente*. Va
> diviso per **superficie visibile**, e chi possiede una superficie possiede anche l'innesto di
> tutto ciò che quella superficie mostra.

**Ed è la spiegazione diretta di due osservazioni del developer**: *«l'estetica mi pare un po'
basica»* (la card c'è, non è usata) e *«nel primo blocco non vedo il grafico del drawdown»*
(i dati ci sono, il grafico no).

---

## 3. I rilievi, in ordine di gravità

### 🔴 P1 — bloccanti per la prossima review

#### P1.1 · `RiskMetricCard` esiste e nessuno la usa

L1 rende una `<ul>` con `<li class="flex justify-between">`: etichetta a sinistra, numeri a destra,
**a tutta larghezza**. Su uno schermo ampio i due lati si allontanano e in mezzo resta il vuoto —
*«3 numeri e occupa tutta la pagina, è un casino»*.

La card che D ha costruito **risolve esattamente questo**, e lo dice nella propria intestazione:

> *«`@container` + `text-[clamp(…)]` — il numero scala con **il suo contenitore**, non col viewport.
> Questa è la vera risposta a "non ottimizzato per gli schermi": la vecchia griglia saltava
> `1 → sm:2 → xl:5` senza nulla in mezzo, quindi un portatile da 1366px otteneva due colonne per
> cinque card e un orfano sulla terza riga.»*

Porta anche **la doppia etichetta** che il developer ha chiesto senza sapere che esisteva già:
*«la label deve essere più tecnica, il tooltip discorsivo»* →
la card ha `title` (la domanda in lingua piana) **e** il nome tecnico accanto, più la ⓘ.

**Lavoro**: montare L1, L2 e L3 su `RiskMetricCard`. Non è un rifacimento: è un innesto.

#### P1.2 · I tre campi grafico di A sono nel client generato e non vengono resi

```
underwater_series   nel contratto ✅   nel client generato ✅   reso nei livelli 🔴 0
return_bins         nel contratto ✅   nel client generato ✅   reso nei livelli 🔴 0
var_bin_edge        nel contratto ✅   nel client generato ✅   reso nei livelli 🔴 0
```

`underwater_series` **è** il grafico del drawdown che manca in L1. `return_bins` + `var_bin_edge`
sono l'istogramma della distribuzione con la barra del taglio VaR.

⚠️ **Una nota che serve a chi lo implementerà**: `var_bin_edge` va letto con `=== null`, mai con
`?? 0` — uno zero è un taglio legittimo, e il ripiego lo renderebbe indistinguibile dall'assenza.
La barra va trovata **per disuguaglianza** su intervalli semiaperti, non per uguaglianza.

#### P1.3 · I sei link alla documentazione sono tutti rotti

E 22 pagine scritte da **I** non sono raggiungibili da nessun punto dell'interfaccia.
Le corrispondenze sono ovvie e già disponibili:

| link rotto | pagina che esiste |
|---|---|
| `user/analysis/risk.md#value-at-risk` | `risk-metrics/value-at-risk` |
| `user/analysis/risk.md#drawdown` | `risk-metrics/max-drawdown` o `current-drawdown` |
| `user/analysis/risk.md#sortino` | `risk-metrics/sortino-ratio` |
| `user/analysis/risk.md#sharpe` | `risk-metrics/sharpe-ratio` |
| `user/analysis/risk.md#beta` | `risk-metrics/beta-active-return` |

📌 **E manca un cancello**: nessun test verifica che un `DocsLink` punti a una pagina esistente.
Sei link rotti sono passati attraverso `front check`, `front build` e l'intera suite E2E.

#### P1.4 · L4 ignora il design system

```
SingleDatePicker usato in L4:  0
```

Il progetto ha `ui/date/SingleDatePicker.svelte` (389 righe, con la giunzione digitato/calendario) e
L4 usa un input nativo. Stesso discorso per i bottoni e le dimensioni dei preset: L4 è *«una grande
lista di componenti standard»* perché non passa dai componenti del progetto.

⚠️ **E il selettore di L3 tronca invece di riposizionarsi**: il progetto ha già la logica di
apertura verso lo spazio disponibile — `Tooltip.svelte` la implementa con `position` e il calcolo
del bordo. Il selettore del confronto non la usa.

#### P1.5 · Il Monte Carlo non dice a che punto è

Nessun canale di avanzamento: l'utente clicca e aspetta senza sapere se il calcolo procede.
**Serve uno stream** (SSE o websocket) con percentuale di percorsi completati e una barra.
Da valutare insieme: il worker QuantLib gira in un processo separato, quindi l'avanzamento va
propagato dal worker al processo web e da lì al client — **è lavoro di piattaforma, non di UI**.

---

### 🟠 P2 — degradano l'esperienza, non la bloccano

#### P2.1 · Gli avvisi sono righe arancioni in cima, e dovrebbero essere triangoli sul numero

Oggi ogni livello apre con un blocco del tipo:

```
1 avviso/i
Metriche di rischio storiche: Parziale · Una giornata storta: Parziale · …
One or more scope assets were excluded from risk calculations.
```

**Proposta del developer, che condivido**: un ⚠️ giallo **accanto al numero interessato**, con
`Tooltip.svelte` che spiega. L'avviso segue il dato invece di precederlo, e chi non ha problemi non
legge niente.

#### P2.2 · 🔴 Le frasi in inglese non sono traduzioni mancanti: sono stringhe del backend

```
backend/app/services/risk/service.py:608   message="One or more scope assets were excluded…"
backend/app/services/risk/service.py:765   message="Risk result uses incomplete or carried-forward…"
```

Cercate nei quattro cataloghi i18n: **zero occorrenze**. Non c'è una chiave da tradurre — **c'è
prosa inglese che il backend produce e il frontend rende alla lettera**. Nel solo sottosistema
rischio ci sono **17 messaggi** di questa forma.

> 🔑 **Quindi non è un lavoro di traduzione, è un cambio di contratto**: il backend deve emettere
> un **codice** (`scope_assets_excluded`, `carried_forward_source_data`) e il frontend deve tradurlo.
> Il messaggio inglese può restare come ripiego per i log, mai come testo mostrato.

#### P2.3 · L'etichetta e il tooltip dicono la stessa cosa

Osservazione del developer, e la diagnosi è sua: *«credo che il problema sia la label»*. Esatto —
l'etichetta oggi è già discorsiva («Una giornata storta (peggiori 5 %)»), quindi il tooltip non ha
niente da aggiungere. **La doppia etichetta di `RiskMetricCard` risolve la causa**: domanda piana
come titolo, **nome tecnico** accanto (`VaR 95 %`), discorso nel tooltip. Tre registri, tre posti.

#### P2.4 · L2 dice «non disponibile per i dati selezionati» e non è vero

Il messaggio accusa i dati. Le cause vere sono **due, e nessuna delle due è quella**:

```json
mode=historical            → {"code":"incompatible_mode",
                              "message":"Analytic 'risk_contribution' does not support mode 'historical'"}
mode=current_composition   → {"code":"insufficient_history", "observations":15, "required":20}
```

**Il pannello chiede `historical`**, che `risk_contribution` non supporta
(`risk_contribution.py:47  supported_modes = (RiskMode.CURRENT_COMPOSITION,)`).

✅ **Il developer aveva ragione**: il banner FX su EUR/KRW **non c'entra**. Riguarda 1 data.

---

### 🟡 P3 — da sistemare, ma non urgenti

#### P3.1 · Due separatori decimali nella stessa riga

In italiano: `−1.3%` (punto) accanto a `−175,91 €` (virgola).

⚠️ **Non è una regressione**: la panoramica mostra lo stesso miscuglio (`-9.47%` / `-392,75 €`).
`utils/core/formatPercent.ts` usa `toFixed`, che stampa sempre il punto. **È un difetto di progetto,
preesistente**, e va affrontato come tale — non dentro il lavoro sul rischio.

📌 Nei livelli ci sono comunque **16 `toFixed` grezzi** che scavalcano anche il formattatore
esistente: quelli vanno ricondotti a `formatPercent` a prescindere da come si decida sul separatore.

#### P3.2 · `risk-mocks.ts` rischia di restare senza lettori

575 righe scritte da D. Dopo la ricombinazione degli spec potrebbe avere **zero** consumatori,
perché E e F si sono scritti i propri mock. **Da decidere, non da lasciare andare alla deriva.**

#### P3.3 · Il filtro broker del laboratorio non è più coperto

Risolvendo il conflitto add/add su `risk-lab.spec.ts` ha vinto la versione di F (6 test), che **non
tocca** `risk-broker-filter`. La copertura sopravvive dentro `risk-analysis.spec.ts`, ma finirà nel
file sbagliato: va portata nel laboratorio con la ricombinazione.

---

## 4. 🔴 Il vincolo che precede ogni altro lavoro: **i dati di prova non riempiono il pannello**

Questo non è un rilievo sull'interfaccia. È la ragione per cui **metà della review si è svolta su
pannelli vuoti**, e va risolto *prima* del lavoro estetico.

```
price_history           1 549 righe, 373 date distinte  (2025-09-11 → 2026-09-18)
asset posseduti         9
  con ≥ 20 punti        5
  con ≤ 1 punto         🔴 4     (asset 4, 5, 17 e uno senza asset_id)
osservazioni viste
  dalle analitiche      🔴 15    contro le 20 richieste
```

**Il dato esiste** — 373 date — **ma il portafoglio di prova possiede quattro asset praticamente
senza storico**, e la serie di portafoglio collassa. Da lì discendono, tutte insieme:

- lo stato `partial` su L1 e L3;
- l'avviso *«carried-forward source data»*;
- il **beta a `—`** (`comparison` → `insufficient_history`, 15 < 20);
- l'indisponibilità di L2 anche nel modo corretto.

> 📌 **E c'è un secondo buco nello stesso posto**: `db populate` non marca **nessun** asset come
> benchmark (`is_benchmark=1` → **0 righe su 17**). B ha costruito il flag, il popolatore non lo usa.
> Quindi anche a storia sufficiente, il selettore del confronto partirebbe senza candidati naturali.

**Prima voce del prossimo piano**: estendere `db populate` perché il portafoglio di prova abbia
almeno 250 osservazioni comuni su ogni asset posseduto, e almeno un asset marcato benchmark.
**Senza questo, ogni review successiva misura il vuoto invece dell'interfaccia.**

---

## 5. I pacchetti di lavoro proposti

Ordinati per dipendenza, non per gravità. **W1 abilita tutto il resto.**

| | pacchetto | contenuto | specialista |
|---|---|---|---|
| **W0** | **Decisione di prodotto** | le 4 misure di N senza verdetto (§7.3): assegnare a un livello o togliere dal contratto | **developer** |
| **W1** | **Dati di prova** | `db populate` con storia sufficiente e un benchmark marcato | backend |
| **W2** | **Innesto dei costruiti** | `RiskMetricCard` in L1/L2/L3 · i tre campi grafico di A · i sei link a I | frontend, **un solo proprietario** |
| **W2b** | **Le quattro rappresentazioni mancanti** | underwater (7.1) · istogramma VaR (7.2) · heatmap in L2 (7.4) · scatter rischio-rendimento (7.5, **unico con costo backend**) | frontend + backend |
| **W3b** | **Asset Global ai livelli ridotti** | `L2 + L1° + L3° + L4°` al posto del pannello legacy (`03` §2) | frontend |
| **W3** | **Allineamento al design system** | `SingleDatePicker` e i controlli di progetto in L4 · riposizionamento del selettore di L3 | frontend |
| **W4** | **Avvisi come segnali** | ⚠️ sul numero + `Tooltip` · codici al posto della prosa inglese (**backend + frontend insieme**) | misto |
| **W5** | **Ricombinazione degli spec** | 18 test unici nella struttura di D sui contenuti di E · filtro broker nel laboratorio · destino di `risk-mocks.ts` | `test-author` |
| **W6** | **Avanzamento del Monte Carlo** | stream worker → web → client, con barra | piattaforma |
| **W7** | **Separatore decimale** | scelta di progetto su `formatPercent`, poi i 16 `toFixed` dei livelli | trasversale |

### Due cancelli nuovi, perché questi difetti non tornino

1. **Un test che verifica che ogni `DocsLink` punti a una pagina esistente.** Sei link rotti sono
   passati indenni attraverso ogni cancello esistente.
2. **Un test che verifica che ogni campo del contratto reso disponibile abbia un consumatore**, o
   almeno un elenco esplicito di quelli deliberatamente spenti. Tre campi di A sono arrivati fino
   al client generato senza che nessuno li rendesse, **e nessun rosso lo ha segnalato.**

---

## 6. Una nota sul metodo, perché riguarda il prossimo giro

Il developer ha scritto: *«mi pare che rispetto a prima una forte e chiara direzione sia stata
presa»*. È vero, ed è il risultato che contava.

Ma il modo in cui questa review è andata dice qualcosa sul **come** proseguire. Le tre scoperte
maggiori — la card mai usata, i grafici mai innestati, i link mai validi — **non erano trovabili da
nessuno dei mandati**, perché ciascuno vedeva un solo albero e ciascuno aveva ragione sul proprio.
Sono diventate visibili **solo guardando l'app in esecuzione**, dopo la fusione.

📌 **Quindi il prossimo giro va organizzato all'inverso**: non «un mandato per componente, poi si
fonde», ma **«un proprietario per superficie visibile, che innesta tutto ciò che la superficie
mostra»** — e una revisione sull'app **prima** di dichiarare finito un pacchetto, non dopo.

---

# 7. Delta fra i piani di **design** e ciò che è stato costruito

> Aggiunto il 18 settembre su richiesta del developer: *«se già lato UI la resa è stata così
> diversa dal progettato, forse anche nei livelli sottostanti le differenze non sono trascurabili»*.
>
> **Metodo**: confronto fra i documenti **`00`–`03`, `05`** (design) e il codice fuso. **Non** i
> piani implementativi, **non** i rapporti dei mandati. Il sospetto era fondato: i delta ci sono,
> e uno va **nella direzione opposta** a quella che il developer si aspettava.

---

## 7.1 🔴 Le sette rappresentazioni: **tre rese su sette**

`05` §7 prescriveva sette grafici. Stato reale nel pannello a quattro livelli:

| | rappresentazione | livello | stato |
|---|---|---|---|
| 7.1 | **Underwater chart** | L1 | 🔴 **assente** — `underwater_series` nel contratto, 0 lettori |
| 7.2 | **Istogramma della distribuzione** | L1 | 🔴 **assente** — `return_bins` + `var_bin_edge`, 0 lettori |
| 7.3 | Peso contro contributo al rischio | L2 | ✅ reso |
| 7.4 | **Heatmap delle correlazioni** | L2 | 🔴 **non in L2** — vive solo nel pannello legacy e nel laboratorio |
| 7.5 | **Scatter rischio-rendimento** | L3 | 🔴 **assente** — nessun componente |
| 7.6 | Tornado degli scenari | L4 | ✅ reso (`TornadoChart`) |
| 7.7 | Cono della simulazione | L4 | ✅ reso (`percentile_bands`, `seriesType: 'band'`) |

> ## 🔑 E c'è uno schema che nessuno aveva notato
>
> **L4 — l'unico livello che parte chiuso — è l'unico completo.** L1, L2 e L3, che l'utente
> incontra aperti appena apre la pagina, sono quelli cui mancano i grafici.
>
> 📌 **Il che ribalta la percezione**: *«il "cosa succede se" è l'unico pannello che parte
> foltado»* — ma è anche **l'unico che ha ciò che il design gli aveva assegnato**. I tre livelli
> che formano la prima impressione sono quelli incompleti.

⚠️ **Correzione a una mia misura precedente**: avevo dato 7.7 per assente cercando `band_points`.
**Il campo si chiama `percentile_bands`.** Il cono c'è, ed è fatto bene. *Un grep sul nome
sbagliato prova l'assenza del nome, non quella della cosa.*

---

## 7.2 🔴 Otto campi calcolati e spediti che nessuno mostra

Misurato sul contratto contro `components/risk/levels/`:

| campo | chi lo ha costruito | letto nei livelli |
|---|---|---:|
| `underwater_series` | **A** (K1) | 🔴 0 |
| `return_bins` | **A** (K1) | 🔴 0 |
| `var_bin_edge` | **A** (K1) | 🔴 0 |
| `ulcer_index` | **N** | 🔴 0 |
| `drawdown_at_risk` | **N** | 🔴 0 |
| `conditional_drawdown_at_risk` | **N** | 🔴 0 |
| `worst_realization` | **N** | 🔴 0 |
| `primary_drawdown` | preesistente | 🔴 0 |

✅ **Due sono legittimi**: `tracking_error` e `information_ratio` non sono resi **perché il
developer li ha tagliati** (`02` § *«Tracking error e Information ratio → tagliati»*). Restano nel
contratto e fuori dalla pagina: **è esattamente la decisione presa.**

🔴 **`primary_drawdown` è il caso più imbarazzante**: `05` §6 lo aveva **già** elencato fra i tre
dati «calcolati, spediti e scartati» — *prima* che l'implementazione cominciasse. Degli altri due
che nominava, `RiskDrawdownOutput` e `RiskContributionItem.weight`, **entrambi sono stati recuperati**.
Questo no. **Il design aveva scritto l'avvertimento, e l'avvertimento è sopravvissuto al giro.**

---

## 7.3 🔴 Il delta nella direzione opposta: **quattro misure che nessun design ha mai chiesto**

Qui non manca qualcosa di previsto. **C'è qualcosa che non era previsto.**

```
ulcer_index                   → mai citato in 00, 01, 02, 03, 05
worst_realization             → mai citato in 00, 01, 02, 03, 05
drawdown_at_risk (DaR)        → mai citato in 00, 01, 02, 03, 05
conditional_drawdown_at_risk  → mai citato in 00, 01, 02, 03, 05
```

*(verificato per `grep -i`; i match apparenti su «drawdown» erano il termine generico)*

**La tabella dei verdetti di `02` elenca 15 strumenti. Nessuno dei quattro c'è.** Sono arrivati dal
**catalogo di riskfolio**, non dal disegno di prodotto: N li ha *acquisiti* perché la libreria li
offriva, e li ha implementati bene — con le due convenzioni piegate correttamente (segno e baseline).

> 🔑 **Ma una misura senza verdetto non ha un livello dove stare**, e infatti non ne ha uno: sono
> tutte e quattro a zero lettori. **Non sono spente per dimenticanza: sono spente perché nessuno
> ha mai deciso a quale domanda rispondessero.**
>
> 📌 **E questa è la forma di spreco opposta a quella di §2**: là qualcuno costruisce e nessuno
> innesta; qui **qualcuno costruisce ciò che nessuno aveva chiesto**. La prima si ripara con un
> innesto; la seconda richiede **una decisione di prodotto** — tenere e assegnare, oppure togliere.

**Domanda aperta per il developer**, e non me la prendo in carico: *Ulcer index* e *worst
realization* meritano un posto in L1 accanto al drawdown, o vanno rimossi dal contratto?
Sono buone misure — l'Ulcer index misura **quanto a lungo e quanto sotto**, non solo l'ampiezza —
ma «buona misura» non è ancora «risponde a una delle quattro domande».

---

## 7.4 🔴 Asset Global non ha ricevuto i livelli ridotti

`03` §2 prescriveva una composizione per pagina:

```
Dashboard      = L1 + L2 + L3 + L4          (€)
Broker Detail  = L1 + L2 + L3 + L4          (€)   stesso codice, scope diverso
Asset Global   = L2 + L1° + L3° + L4°       (%)   L2 primario, gli altri ridotti
```

**Realtà misurata:**

| pagina | monta |
|---|---|
| Dashboard | ✅ `RiskLevelsPanel` (225 righe) |
| Broker Detail | ✅ `RiskLevelsPanel` — **stesso componente**, come prescritto |
| Asset Global | ⚠️ `AssetSetRiskPanel` di F → heatmap ✅ **+ `RiskAnalysisPanel` legacy** per il resto |
| Asset Detail | ✅ `RiskAnalysisPanel` legacy — **corretto: era fuori scopo** |

✅ **Correzione a un mio sospetto**: avevo scritto che il muro di metriche «è ancora quello che
vedono due superfici su quattro», insinuando un fallimento. **Per Asset Detail è falso**: `03`
dice testualmente *«Fuori scopo in questo giro: Asset Detail, parcheggiato in beta»*. **Il legacy
lì è la decisione, non il residuo.**

🔴 **Per Asset Global invece il delta è reale**: F ha consegnato la **casa primaria della
correlazione** — che era la parte più importante della mappa — ma L1°, L3° e L4° arrivano dal
pannello vecchio, in percentuali mescolate alla grammatica che il ridisegno voleva sostituire.

---

## 7.5 ✅ Il Monte Carlo è il pezzo **più fedele al design** di tutta la consegna

Vale la pena dirlo, perché è l'eccezione che mostra cosa succede quando un mandato ha il disegno
completo davanti. `02` §*Monte Carlo* prescriveva un selettore di **modalità, non parametri**, con
l'ipotesi scritta inline. Consegnato, in quattro lingue:

| chiave | etichetta italiana | ipotesi inline |
|---|---|:---:|
| `block_bootstrap` | **Storia rimescolata** *(consigliata)* | ✅ |
| `calm` | **Mercato calmo** | ✅ |
| `prolonged_crisis` | **Crisi prolungata** | ✅ |
| `shock_recovery` | **Shock e recupero** | ✅ |
| `gbm` | **Curva normale (GBM)** *(avanzata)* | ✅ |

**Le cinque etichette coincidono parola per parola con il testo del design.** E il divieto è
rispettato: *«`sobol_start_index` esce dalla UI in ogni caso»* → in `L4Simulation` compare **solo**
nel costruttore della richiesta, mai come controllo.

⚠️ **Ma è ancora un controllo visibile nel pannello legacy** (`RiskAnalysisPanel:1013-1021`, con
etichetta e `data-testid`) — che è quello servito ad Asset Detail e al laboratorio. **Il divieto
vale sulla superficie nuova e non su quella vecchia**, e finché convivono vale a metà.

---

## 7.6 Il quadro complessivo del delta

| area | previsto | consegnato |
|---|---:|---:|
| Rappresentazioni grafiche | 7 | **3** |
| Campi del contratto resi | — | **8 spenti** |
| Misure senza verdetto di design | 0 | **4** |
| Pagine con la composizione prescritta | 3 | **2** |
| Fedeltà del selettore Monte Carlo | — | ✅ **piena** |

> ## 🔑 La lettura che tiene insieme i tre delta
>
> **Non è un problema di esecuzione: ogni singolo pezzo è fatto bene.** L'underwater chart manca
> ma la serie è calcolata correttamente; l'Ulcer index non ha un posto ma è implementato con le
> convenzioni giuste; Asset Global usa il pannello vecchio ma la heatmap nuova è la migliore parte
> della consegna.
>
> **È un problema di chiusura.** Un mandato finisce quando *il suo* lavoro è finito — e nessun
> mandato aveva come definizione di finito *«l'utente lo vede»*. Il Monte Carlo è fedele **perché
> H possedeva contemporaneamente il motore, le chiavi i18n e il pannello**: l'unico caso in cui
> una cosa e la sua resa stavano nello stesso albero.
>
> 📌 **La regola che ne esce, e che vale per `implementation_2`**: *un pacchetto non è finito
> quando il dato esiste. È finito quando il dato è sullo schermo, in quattro lingue, con un link
> che porta a una pagina che esiste.*
