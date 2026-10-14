# Round 2 — proposta di organizzazione

> **Stato**: proposta da approvare. Nulla è stato assegnato.
> **Scritta il**: 18 settembre 2026, dopo la review `08-review-post-integrazione.md`.

---

## 1. Cosa è andato storto la volta scorsa, in una frase

**Il round 1 era diviso per componente. Nessuno possedeva ciò che l'utente vede.**

Undici mandati hanno consegnato undici pezzi corretti, e il risultato è che
`RiskMetricCard` ha zero consumatori, tre campi grafico non hanno lettori, ventidue pagine
non hanno link e quattro misure non hanno un livello. **Nessuno ha sbagliato il proprio
lavoro: è mancato il proprietario del confine fra un lavoro e l'altro.**

L'unica eccezione dice già la cura:

> **Il Monte Carlo è fedele al design parola per parola perché H possedeva insieme il
> motore, le chiavi i18n e il pannello.** Una cosa e la sua resa stavano nello stesso albero.

---

## 2. La regola strutturale del round 2

```
Round 1:   un mandato = un componente        →  il confine non era di nessuno
Round 2:   un mandato = una SUPERFICIE       →  il confine è dentro il mandato
```

**Un mandato di superficie possiede tutto ciò che quella superficie mostra**: il dato, la
query, il componente, le quattro traduzioni, il link alla documentazione, il test.
Non consegna finché **l'utente non lo vede**.

E perché le superfici non ricostruiscano ciascuna le proprie primitive, **le primitive si
fanno prima, da sole, e si congelano.**

---

## 3. Le tre fasi

### Fase 0 — una decisione tua, e blocca solo se stessa

|  | cosa | chi |
| --- | --- | --- |
| **W0** | Le quattro misure senza verdetto (§7.3): `ulcer_index`, `worst_realization`, `drawdown_at_risk`, `conditional_drawdown_at_risk`. **Assegnare a un livello o togliere dal contratto.** | **tu** |

Non blocca le altre fasi. Blocca solo il pacchetto L1, se la risposta è «assegnale a L1».

---

### Fase 1 — **FONDAMENTA**. Due mandati, e finché non chiudono non parte nient'altro

> Questa è la parte che nel round 1 non esisteva, ed è la ragione per cui chiedi di
> *«far preparare le primitive e poi farle riusare»*. **Sono l'unica fase con un divieto
> esplicito di parallelismo con le superfici.**

|  | mandato | contenuto | perché prima |
| --- | --- | --- | --- |
| **F1** | **Dati di prova** | `db populate`: ≥ 250 osservazioni comuni su ogni asset posseduto · almeno un asset `is_benchmark=1` | 🔴 **Oggi le analitiche vedono 15 osservazioni contro 20 richieste.** Senza questo ogni superficie si sviluppa e si verifica sul vuoto |
| **F2** | **Primitive e contratto d'uso** | ① rendere `RiskMetricCard` adottabile (oggi 0 consumatori) · ② esporre `seriesType: 'scatter'` in `LineChart` · ③ **scrivere il contratto d'uso** | 🔴 **Cinque superfici devono montare la stessa card e lo stesso grafico.** Se lo decidono da sole, divergono |

**F1 e F2 non si toccano** (backend vs frontend): possono girare **in parallelo fra loro**,
mai in parallelo con la Fase 2.

#### 🔑 Il deliverable di F2 che conta davvero: `PRIMITIVE.md`

Non il codice — **il documento**. Una pagina che ogni mandato di superficie deve leggere
*prima* di scrivere una riga, e che risponde a:

```
Cosa esiste già            LineChart (line · area · bar · band — NON scatter), RiskMetricCard,
                           KpiMetricBar, KpiDivergingFlowBar, CorrelationHeatmap,
                           Tooltip, SingleDatePicker, formatPercent, DocsLink
Come si monta una card     props, slot, cosa passare durante il loading
Come si monta un grafico   quale seriesType per quale forma di dato
Cosa NON si costruisce     nessun toFixed nuovo, nessun date picker nuovo,
                           nessun popover nuovo
```

> ⚠️ **Nel round 1 questo documento esisteva in forma di commento dentro `RiskMetricCard`,
> ed era eccellente — ma stava dentro il file che nessuno ha aperto.** Un contratto va dove
> lo si legge *prima* di aver bisogno del file, non dentro.

✅ **Verifica d'uscita della Fase 1, che eseguo io sull'app in esecuzione:**
`risk_contribution` esce da `unavailable`, il beta mostra un numero, e la card è montata
in almeno un posto.

---

### Fase 2 — **SUPERFICI**. Cinque mandati in parallelo, un proprietario ciascuno

Ogni mandato possiede **un file di livello** e tutto ciò che serve perché quel livello si veda.

|  | superficie | file posseduto | contenuto |
| --- | --- | --- | --- |
| **S1** | **L1 — Quanto può fare male** | `L1HowMuchItHurts.svelte` | underwater chart (7.1) · istogramma VaR (7.2) · card al posto della `<ul>` · le misure di W0 se assegnate |
| **S2** | **L2 — Sono diversificato** | `L2Diversification.svelte` | heatmap in L2 (7.4) · peso/contributo su card (7.3 già reso, da riformattare) |
| **S3** | **L3 — Sono pagato per il rischio** | `L3RiskAdjusted.svelte`, `L3Benchmark.svelte` | scatter rischio-rendimento (7.5) · beta · **selettore che si riposiziona invece di troncare** |
| **S4** | **L4 — Cosa succede se** | `levels/l4/*` | `SingleDatePicker` e controlli di progetto · bottoni allineati · **avanzamento del Monte Carlo** |
| **S5** | **Asset Global** | `AssetSetRiskPanel.svelte` | i livelli ridotti `L2 + L1° + L3° + L4°` al posto del pannello legacy |

**I cinque file sono disgiunti.** È la proprietà che rende il parallelismo sicuro, e va
verificata prima di avviare, non dopo.

---

### Fase 3 — **TRASVERSALI**. Dopo, perché toccano tutti i livelli insieme

|  | mandato | perché non prima |
| --- | --- | --- |
| **T1** | **Avvisi come segnali** — codici dal backend (17 messaggi) + ⚠️ sul numero con `Tooltip` | Tocca **tutti e cinque** i livelli: in parallelo sarebbe cinque volte lo stesso conflitto |
| **T2** | **Link alla documentazione** — i 6 rotti + **il cancello che impedisce il prossimo** | Va fatto quando le superfici sanno quali metriche mostrano |
| **T3** | **Ricombinazione degli spec** — 18 test unici nella struttura di D sui contenuti di E | Gli spec seguono le superfici, non le precedono |
| **T4** | *(opzionale)* separatore decimale — scelta di progetto, poi i 16 `toFixed` | Difetto **preesistente**, non del rischio |

---

## 4. Come impedisco che si perdano pezzi — il mio ruolo, concreto

Hai chiesto che io sia più centrale. Ecco **in cosa**, in modo verificabile.

### 4.1 Tre registri che tengo io, e nessun altro scrive

| registro | a cosa serve | come lo uso |
| --- | --- | --- |
| **Registro delle primitive** | *«questo esiste già»* | ogni mandato che vuole creare un componente me lo chiede: rispondo con il nome di quello che esiste, o autorizzo |
| **Registro delle superfici condivise** | i18n · catalogo runner · `RiskLevelsPanel` · spec E2E | **un solo scrittore per superficie, nominato prima di avviare** |
| **Registro dei campi del contratto** | ogni campo → chi lo rende | un campo senza consumatore **è un rosso di fine fase**, non una scoperta di sei mesi dopo |

### 4.2 La definizione di finito cambia

```
Round 1:  finito = il mio codice è scritto e i test passano
Round 2:  finito = LO VEDO IO sull'app in esecuzione, in italiano,
                   con il link che porta a una pagina che esiste
```

**Nessun mandato chiude senza che io abbia guardato la sua superficie nel browser.** È la
cosa che ha trovato tutti e tre i delta di questa review, e nel round 1 l'ho fatta **dopo**
l'integrazione invece che prima di ogni chiusura.

### 4.3 Due cancelli automatici nuovi, perché la vigilanza non basta

1. **Un test che verifica che ogni `DocsLink` punti a una pagina esistente.** Sei link rotti
   sono passati attraverso `front check`, `front build` e l'intera suite E2E.
2. **Un test che verifica che ogni campo reso disponibile abbia un consumatore**, oppure sia
   in un elenco esplicito di campi deliberatamente spenti. Tre campi di A sono arrivati fino
   al client generato senza che nessun rosso lo segnalasse.

> 🔑 **Perché servono entrambi, e perché i cancelli vengono prima della disciplina**: nel round
> 1 io *sapevo* che K1 era spento — l'avevo scritto in `J §12`. **Saperlo non è servito a
> niente**, perché non c'era niente che lo chiedesse al momento giusto. Un cancello chiede
> sempre; una persona chiede quando si ricorda.

---

## 5. Che fine fanno i dieci mandati esistenti

Proposta, da decidere insieme. **Il lavoro è integrato e committato**: nessuna sessione
contiene più lavoro unico, quindi archiviare non perde niente.

|  | proposta | perché |
| --- | --- | --- |
| **D** `solid-engine` | 🔄 **riusare per F2** | Ha costruito `RiskMetricCard` e ne conosce ogni decisione. È la persona giusta per renderla adottabile e scrivere `PRIMITIVE.md` |
| **E** `vigilant-adventure` | 🔄 **riusare per S1 o S3** | Conosce i quattro livelli meglio di chiunque. Ma **non tutti e quattro**: sarebbe di nuovo un mandato senza confini |
| **F** `super-dollop` | 🔄 **riusare per S5** | Asset Global è già la sua superficie |
| **H** `friendly-bassoon` | 🔄 **riusare per S4** | Il Monte Carlo è suo, e l'avanzamento è lavoro di piattaforma sul suo motore |
| **N** `miniature-train` | 🔄 **riusare per F1** | Conosce i dati e le convenzioni; e W0 riguarda le sue quattro misure |
| **A** `improved-meme` | 💬 **consulente** | La matematica è chiusa. Ma è l'unico che sa perché il bordo VaR è `−∞`, e S1 lo renderà |
| **I** `shiny-broccoli` | 🔄 **riusare per T2** | Ha scritto le 22 pagine: sa a quale pagina ogni metrica deve puntare |
| **B**, **C**, **G** | 📦 **archiviare** | Lavoro chiuso e integrato, nessuna coda |

⚠️ **Una cautela sul riuso**: un mandato riusato porta con sé il proprio contesto, che è un
vantaggio, **e le proprie assunzioni, che è un rischio**. In questo round oltre settanta
assunzioni dei briefing sono risultate false alla misura. **Un mandato riusato va riavviato
con un'analisi dello stato attuale, non con "continua da dove eri".**

---

## 6. Ordine di avvio proposto

```
riguardoggi        W0 — la tua decisione sulle quattro misure

poi         F1 + F2 in parallelo fra loro, soli
            └── cancello: le analitiche escono da `unavailable`, la card è montata

poi         S1 · S2 · S3 · S4 · S5 in parallelo, cinque file disgiunti
            └── cancello: guardo ciascuna superficie nel browser, in italiano

infine      T1 → T2 → T3, in serie perché attraversano tutto
            └── cancello: i due test nuovi passano
```

**Durata stimata**: non la stimo. Il round 1 mi ha insegnato che una stima fatta prima
dell'analisi dello stato attuale è un numero inventato — undici mandati su undici hanno
trovato falsa almeno un'assunzione del proprio briefing.

---

## 7. Le tre domande che ti faccio prima di dettagliare

1. **W0** — le quattro misure senza verdetto: assegnare o rimuovere?
2. **S1/S3** — E può possedere una sola superficie: quale preferisci, L1 (i grafici mancanti)
   o L3 (il benchmark, che ha costruito lui)?
3. **T4** — il separatore decimale è un difetto di progetto: lo affrontiamo in questo round o
   lo mettiamo in `TODO_FUTURI`?

---

# 8. Le tre risposte, e le decisioni che ne seguono

> Aggiornato il 18 Set 2026 dopo le risposte dello sviluppatore.

## 8.1 ✅ W0 — le quattro misure **si assegnano**, e vanno tutte in L1

> *«se riusciamo ad assegnarle e farle sarebbe meglio»*

Tutte e quattro rispondono alla domanda di L1 — **«quanto può fare male?»** — e nessuna
apre una domanda nuova. **Ma non diventano quattro righe in più**: ciascuna si aggancia come
**seconda riga di una che già esiste**, perché una misura da sola non dice niente e accanto
alla sua sorella dice molto.

```text
Una giornata storta (VaR 95 %)            −1,3 %      ← c'è già
  └ e la peggiore vissuta davvero          −x %       ← worst_realization
Un mese storto (VaR 95 %)                 −3,7 %      ← c'è già
La peggior discesa (max drawdown)         −4,5 %      ← c'è già
  └ che non superi nel 95 % dei casi       −y %       ← drawdown_at_risk
  └ e se la superi, in media               −z %       ← conditional_drawdown_at_risk
Underwater chart                                       ← rappresentazione 7.1
  └ Ulcer index: quanto a lungo e quanto sotto         ← ulcer_index, didascalia del grafico
```

**Il criterio di accoppiamento, che è la parte che conta:**

| misura | si accoppia a | perché |
|---|---|---|
| `worst_realization` | la giornata storta **statistica** | è la sua **controparte realizzata**: «il modello dice −1,3 %, la storia ha fatto −x %» |
| `drawdown_at_risk` | il max drawdown | è **VaR applicato alle discese** invece che ai rendimenti |
| `conditional_drawdown_at_risk` | `drawdown_at_risk` | sta a DaR come CVaR sta a VaR: **la media oltre la soglia** |
| `ulcer_index` | l'**underwater chart** | non è un punto su una scala: è **l'area sotto la curva** che il grafico disegna. Numero e grafico dicono la stessa cosa in due modi |

> 🔑 **E c'è una ragione in più per cui l'Ulcer index deve stare accanto al grafico e non in una
> riga sua**: da solo è un numero senza unità che nessuno sa leggere. **Sotto la curva che lo
> genera diventa la sua didascalia**, e si spiega da sé.

⚠️ **Vincolo per S1**: le quattro misure **non hanno una pagina di documentazione**. Le 22 di I
coprono il catalogo del design, e queste non c'erano. **S1 deve richiederle a T2**, oppure
consegnare senza `DocsLink` — mai con un link che punta al nulla, che è l'errore del round 1.

---

## 8.2 ✅ E prende **L1**, e L3 va a una sessione nuova full-stack

> *«scegli tu, se credi sia meglio farli in serie assegna entrambi ad E»*

**Scelgo di separarli**, e la ragione non è il carico ma **la natura del lavoro**:

| | S1 · L1 | S3 · L3 |
|---|---|---|
| dati | ✅ **tutti già nel contratto** | 🔴 **lo scatter richiede backend nuovo** — volatilità e rendimento **per ogni asset** |
| natura | cablaggio frontend puro, denso | **full-stack** |
| citazione dal design | — | `05` §7.5: *«Unica proposta con un costo backend non marginale»* |

**E è un mandato frontend.** Dargli L3 significherebbe dargli un pezzo di backend che non ha mai
toccato, oppure spezzare L3 fra due persone — **che è esattamente l'errore del round 1.**

✅ **Assegnazione**:
- **S1 → E** (`vigilant-adventure`): il più denso di cablaggio, e conosce `levelHelpers.ts` meglio
  di chiunque.
- **S3 → sessione nuova**, full-stack, **con A come consulente** sulla matematica per-asset.

📌 **E in serie sarebbe stato peggio, non solo più lento**: S1 e S3 non condividono file, quindi
la serialità non comprerebbe sicurezza — comprerebbe solo attesa.

---

## 8.3 ⚠️ Separatore decimale → **`TODO_FUTURI`**, ma non per la ragione che sembrava

> *«credo ci sia già un helper in tal senso, se non esiste mettilo in TODO_FUTURI altrimenti
> usiamolo»*

**L'helper esiste** — `currencyFormat.ts` usa `toLocaleString`, ed è per questo che il denaro ha
la virgola. **Ma non si può adottare così com'è.**

```ts
currencyFormat.ts:36   Math.abs(amount).toLocaleString(undefined, {…})
                                                       ^^^^^^^^^
```

🔴 **`undefined` = la lingua del BROWSER, non quella scelta nell'app.**

| lingua app | lingua browser | denaro |
|---|---|---|
| 🇮🇹 | 🇮🇹 | `175,91 €` ✅ |
| 🇮🇹 | 🇬🇧 | **`175.91 €`** 🔴 |

> **Usarlo in `formatPercent` propagherebbe un secondo difetto invece di chiuderne uno.**

Il lavoro vero è legare **entrambi** i formattatori al locale dell'app, e aggiornare **2**
asserzioni unitarie e **~23 E2E**. **Registrato in `TODO_FUTURI.md` con la misura completa**:
è un lavoro di progetto, non un pezzo di un pacchetto di superficie.

---

# 9. La griglia finale dei mandati

| | mandato | superficie / contenuto | sessione | stato |
|---|---|---|---|---|
| **F1** | Dati di prova | `db populate`: storia + benchmark | **N** `miniature-train` | 🔄 riuso |
| **F2** | Primitive + `PRIMITIVE.md` | card adottabile · `seriesType: 'scatter'` · contratto d'uso | **D** `solid-engine` | 🔄 riuso |
| **S1** | **L1** — Quanto può fare male | underwater · istogramma · card · **le 4 misure di W0** | **E** `vigilant-adventure` | 🔄 riuso |
| **S2** | **L2** — Sono diversificato | heatmap in L2 · peso/contributo su card | **nuova** | ➕ |
| **S3** | **L3** — Sono pagato per il rischio | **scatter (backend+frontend)** · beta · selettore | **nuova**, A consulente | ➕ |
| **S4** | **L4** — Cosa succede se | design system · **avanzamento Monte Carlo** | **H** `friendly-bassoon` | 🔄 riuso |
| **S5** | **Asset Global** | livelli ridotti al posto del legacy | **F** `super-dollop` | 🔄 riuso |
| **T1** | Avvisi come segnali | 17 messaggi → codici · ⚠️ sul numero | **nuova** | ➕ |
| **T2** | Link doc + cancello | i 6 rotti · **le pagine per le 4 misure di W0** · il test | **I** `shiny-broccoli` | 🔄 riuso |
| **T3** | Ricombinazione spec | 18 test unici nella struttura di D | `test-author` | ➕ |
| — | consulente matematica | perché il bordo VaR è `−∞`, vol/rendimento per asset | **A** `improved-meme` | 💬 |
| — | — | lavoro chiuso, nessuna coda | **B**, **C**, **G** | 📦 archiviare |

### Gli scrittori unici delle superfici condivise — nominati **prima** di avviare

| superficie | scrittore unico | gli altri |
|---|---|---|
| `RiskLevelsPanel.svelte` (contenitore) | **E** (S1) | chiedono a E |
| `levelHelpers.ts` | **E** (S1) | chiedono a E |
| `frontend/src/lib/i18n/*.json` | **ciascuno nel proprio namespace** `risk.levels.lN.*` | il coordinatore verifica l'unione |
| `scripts/test_runner/_frontend_portfolio.py` | **T3** `test-author` | nessun altro lo tocca |
| `frontend/e2e/portfolio/*.spec.ts` | **T3** `test-author` | nessun altro lo tocca |

> ⚠️ **Nel round 1 questa tabella non esisteva, e il catalogo del runner ha conflittato tre volte
> su quattro merge.** Nominare lo scrittore costa una riga; non nominarlo è costato tre
> risoluzioni manuali, una delle quali stava per cancellare silenziosamente il lavoro di D.
