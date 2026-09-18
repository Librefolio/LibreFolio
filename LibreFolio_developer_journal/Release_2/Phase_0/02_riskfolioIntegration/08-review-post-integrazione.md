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
| **W1** | **Dati di prova** | `db populate` con storia sufficiente e un benchmark marcato | backend |
| **W2** | **Innesto dei costruiti** | `RiskMetricCard` in L1/L2/L3 · i tre campi grafico di A · i sei link a I | frontend, **un solo proprietario** |
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
