# Mandato J — Chiusura e rilascio

| | |
|---|---|
| **Flusso** | W10 di [`../07-piano-esecutivo.md`](../07-piano-esecutivo.md) §2 |
| **Dominio** | trasversale |
| **Taglia** | S |
| **Lane** | porta `6249` · data dir `backend/data/test-risk-j` |
| **Dipende da** | **tutti** |

> Regole comuni: [`README.md`](./README.md) §5. Finito comune: §6.

---

## 1. Perché questo mandato esiste come mandato separato

Perché **D46** lo richiede: si rilascia **solo a catena completa**, dal worktree
separato. Niente stati intermedi su `dev_release2`.

E perché la chiusura ha un contenuto proprio che nessun altro mandato può fare: il
banner si toglie **una volta sola**, il CHANGELOG si scrive **una volta sola**, e
qualcuno deve verificare che gli undici mandati abbiano davvero consegnato ciò che hanno
dichiarato.

> ⚠️ È anche il mandato in cui è più facile barare, perché arriva quando tutti sono
> stanchi e tutto sembra fatto. **Un cancello che si apre per stanchezza non è un
> cancello.**

---

## 2. Il banner beta — dove va e dove resta

Il banner (`RiskBetaBanner.svelte`, 11 righe) è montato oggi in **3 dei 4** punti
d'ingresso.

> Non è mai stato un giudizio sulla qualità dei calcoli: è **il segnaposto di una
> catena di piano interrotta** ([`../00-…`](../00-analisi-stato-attuale.md) §3).

**La regola** (**D46**, che raffina Q4):

| Livello | Banner | Perché |
|---|:---:|---|
| **L1** Quanto può fare male | ❌ via | Fatti osservati sul campione. Nulla è stimato |
| **L2** Sono diversificato | ❌ via | Struttura calcolata sui dati reali |
| **L3** Sono pagato per il rischio | ❌ via | Confronto con un benchmark reale |
| **L4** — replay storico | ❌ via | Rendimenti reali di un periodo reale |
| **L4** — shock ipotetico | ❌ via | Deterministico, ipotesi dichiarata dall'utente |
| **L4** — **simulazione** | ✅ **resta** | **È un modello.** È lì, e solo lì, che un avvertimento è onesto |

⚠️ **Asset Detail** resta com'è e **conserva il suo banner**: è parcheggiato (**D8**,
**D47**) e si riapre **dopo** questo rilascio, così eredita una grammatica già decisa.

---

## 3. Il CHANGELOG — scrittore unico

`CHANGELOG.md` è **di questo mandato e di nessun altro**, mai.

**Dove**: capitolo `## [Unreleased]`, che oggi esiste e dichiara *«Preparing v1.1.1»*.

⚠️ La sezione `### 🔄 Changed` in quel capitolo **non esiste ancora** — ci sono solo
`### ✨ Added` e `### 🐛 Fixed`. Va creata, con l'emoji, nell'ordine canonico del
formato.

### 3.1 La voce su M2 — quella che non si può omettere

M2 cambia **numeri già mostrati agli utenti**.

> ## 🔴 Corretta il 17 Set 2026 — la formulazione precedente era doppiamente sbagliata
>
> Diceva *«il CVaR cambia … circa lo 0,27%»*. Misurato dal mandato **A** e verificato
> dal coordinatore:
>
> - **cambia anche il VaR**, perché l'off-by-one è lo **stesso indice** che produce
>   entrambi — e la card ne mostra due (`RiskAnalysisPanel.svelte:880-881`);
> - **«0,27%» era una media al 95%**, non un limite: l'utente sceglie
>   `confidence_level`, e al **99%** lo scarto peggiore è di un ordine di grandezza
>   superiore. Più stretta la coda, meno osservazioni, più grande l'errore.

Tre fatti, e nessuna scusa:

1. **VaR e CVaR** mostrati **cambiano leggermente**;
2. cambiano perché la stima precedente era **sistematicamente distorta** — **non**
   perché si sia cambiata convenzione;
3. l'entità **dipende dal livello di confidenza scelto** e cresce al restringersi della
   coda.

⚠️ **Non pubblicare una percentuale unica.** Si dichiara l'ordine di grandezza per il
livello di default e si dice che cresce con la confidenza. Un numero solo
rassicurerebbe chi usa il 99%, cioè proprio chi è più esposto all'errore.

> ## ✅ **LE CIFRE SONO ARRIVATE — 18 Set 2026, da A. Non cercarle, non inventarle.**
>
> 2000 campioni, T = 750, oracolo riskfolio.
>
> | confidenza | VaR mediana | VaR peggiore | **CVaR mediana** | CVaR peggiore | CVaR sempre in su |
> |---|---|---|---|---|---|
> | 90 % | +0,435 % | **+4,587 %** | +0,364 % | +0,476 % | **2000/2000** |
> | 95 % | **0,000 %** | **0,000 %** | **+0,267 %** | +0,404 % | **2000/2000** |
> | 99 % | **0,000 %** | **0,000 %** | **+0,727 %** | +1,748 % | **2000/2000** |
>
> Prima: delta medio `−5,97e-05`, il nostro più basso **2000 volte su 2000**.
> Dopo: **`−4,27e-18`**, e testa-o-croce su chi è più basso. **Da distorsione
> strutturale a rumore di arrotondamento.**
>
> ### Le tre frasi vere
>
> 1. **Il CVaR sale a ogni livello.** Stavamo **sottostimando la coda**; la correzione
>    va nella **direzione prudente**. Il numero nuovo non è «diverso»: è **meno ottimista**.
> 2. **Cresce con la confidenza** — +0,27 % a 95 %, +0,73 % a 99 % — perché con meno
>    osservazioni in coda **il peso frazionario conta di più**.
> 3. **Nella configurazione predefinita il VaR NON cambia.**
>
> ### 🔴 CORRETTO il 18 Set 2026 — «il VaR non cambia» è FALSO PER LA MAGGIORANZA DEGLI UTENTI
>
> La versione precedente diceva *«nella configurazione predefinita il VaR non cambia»*, e gli
> `0,000 %` a 95 % e 99 % **sembravano dimostrarlo**. **Significano solo «non cambia a T = 750».**
>
> **A l'ha misurato**: 24 combinazioni confidenza × lunghezza di storia, 300 campioni ciascuna,
> **7 200 prove**.
>
> | conf | T=740 | 745 | 750 | 760 | 800 | 1000 | 1250 | 2000 |
> |---|---|---|---|---|---|---|---|---|
> | **90 %** | **100 %** | 0 % | **100 %** | **100 %** | **100 %** | **100 %** | **100 %** | **100 %** |
> | **95 %** | **100 %** | 0 % | 0 % | **100 %** | **100 %** | **100 %** | 0 % | **100 %** |
> | **99 %** | 0 % | 0 % | 0 % | 0 % | **100 %** | **100 %** | 0 % | **100 %** |
>
> **Sempre 100 % o 0 %, mai una via di mezzo.** Non è una tendenza statistica, è una regola
> deterministica:
>
> > ## **Il VaR si sposta esattamente quando `(1 − confidenza) × osservazioni` è un INTERO.**
>
> Il VaR è una **funzione a gradini** di un indice di statistica d'ordine: quando il prodotto
> cade su un intero, vecchia e nuova formula indicano **due osservazioni diverse**, e il salto
> è **un'intera statistica d'ordine** — da cui il **+4,587 %** peggiore. Quando cade fra due
> interi, entrambe arrotondano allo stesso posto e **il VaR non si muove di un bit**.
>
> ### 🔴 E la parte contro-intuitiva, che è quella che decide la voce di CHANGELOG
>
> La condizione è una **divisibilità**: al 90 % morde quando T è multiplo di **10**, al 95 %
> di **20**, al 99 % di **100**.
>
> > **Quindi gli utenti colpiti sono quelli con la storia più «pulita».** Chi chiede esattamente
> > **1 000** giorni è colpito a **tutti e tre** i livelli. Un anno (250), due (500), tre (750)
> > sono **tutti multipli di 10** → colpiti al 90 %. Chi ne ha 1 003 **non è colpito a nessuno**.
>
> ⚠️ **Il ragionamento ingenuo — *«è un caso di bordo, capiterà a pochi»* — è ROVESCIATO**: i
> numeri tondi sono esattamente i divisibili, **e i numeri tondi sono ciò che un'interfaccia
> propone**. *«Non è una coda rara, è il centro della distribuzione d'uso.»*
>
> ✅ **E questo riconcilia due misure di A che sembravano contraddirsi**: **21/400** divergenze
> al 95 % nell'analisi iniziale (a **T = 740**, `0,05 × 740 = 37`, **intero**) contro **0/2000**
> nella tabella (a **T = 750**, `37,5`, **non intero**). **Due misure indipendenti che concordano
> solo sotto questa regola.**

### ✅ Le TRE affermazioni da scrivere — nessuna contiene un numero che valga solo per un T

1. **Il CVaR sale sempre** — **2000/2000 a ogni livello**. Stavamo **sottostimando** il rischio
   di coda; la correzione va **nella direzione prudente**. Entità tipica **+0,27 % … +0,73 %**,
   **cresce con la confidenza** (meno osservazioni in coda → il peso frazionario pesa di più);
   al 99 % il peggiore misurato è **+1,748 %**.
2. **Anche il VaR cambia**, non solo il CVaR — **contrariamente a quanto dice `06` §3**. Cambia
   **a intermittenza**, secondo la regola dell'intero, e **quando cambia si sposta di un'intera
   osservazione**: fino a **+4,587 %** misurato.
3. **Nessun utente vede il numero peggiorare in senso ottimistico.** Entrambe le grandezze,
   quando si muovono, si muovono **verso l'alto**: **il rischio dichiarato prima era troppo basso.**

⚠️ **Da correggere ovunque compaia: il «0,27 %» è la MEDIANA a 95 %, T = 750 — non un limite.**
I massimi misurati sono **+1,748 %** sul CVaR e **+4,587 %** sul VaR.

📌 **Per I**: la regola dell'intero va **per esteso** nella pagina. *«È l'unica cosa che permette
a un utente di capire perché il suo VaR è cambiato e quello di un collega no. Una pagina che
dicesse solo "abbiamo corretto lo stimatore" lascerebbe quella domanda senza risposta — e quella
domanda arriverà.»*

---

## 🔴 La seconda voce di CHANGELOG che muove numeri: **A9, il tasso privo di rischio**

Indipendente da M2 e **più larga**: tocca **ogni Sharpe e Sortino di ambito titolo con
tasso privo di rischio non nullo**.

| rf | Sharpe lusingato | Sortino lusingato |
|---|---|---|
| **0 %** | **+0,0000** | — |
| 2 % | **+0,038** | **+0,053** |
| 5 % | **+0,094** | **+0,130** |

- **A rf = 0 l'errore è esattamente zero** → invisibile a chi lascia il tasso al default:
  è per questo che è sopravvissuto alla migrazione dal 252.
- **Il totale di portafoglio non è distorto, mai** (delta `1,4e-16`): il difetto vive
  **solo sul ramo titolo/fetta**.
- ⚠️ **Mai una percentuale**: vicino allo zero il rapporto esplode. La formulazione è
  **«circa 0,03–0,13 di Sharpe/Sortino lusingato, in ambito titolo, con tasso privo di
  rischio non nullo»**.
- ⚠️ E **«può invertire il segno» va detto con cautela**: è vero per ogni Sharpe vero in
  `(−0,05 ; 0)` — banda stretta, **ma è esattamente la banda in cui la domanda conta**,
  cioè *«ho battuto il tasso privo di rischio?»*.

## 🔴 Terza voce: **`effective_number_of_assets` non si etichetta come un conteggio**

Misurato da N sul portafoglio di test: **11,44 su 2 posizioni**, cioè **5,7×**. Non è un
difetto — la cassa sta nel denominatore **senza essere un termine**, ed è **la stessa
forma che usa AI Export** (verificato). **È il nome che promette un conteggio**, e un
conteggio non può superare il totale. Se compare in una nota di rilascio, va con la cassa
dichiarata o con un'etichetta da **indice di concentrazione**.

## ⚠️ GJR-GARCH: la spiegazione da usare è quella corretta

Non *«QuantLib espone GARCH solo come engine di opzioni»* — **il motore non passa affatto
da un engine**: usa `GeometricBrownianMotionProcess` → `StochasticProcessArray` →
`GaussianMultiPathGenerator`. Versione giusta: **la generazione di cammini richiede uno
`StochasticProcess`, e i binding Python non espongono alcun processo della famiglia
GARCH** — i nomi GARCH esistenti sono **engine di pricing**, che non si innestano nel
generatore.

> *«Una pagina che spiega male il motivo giusto è la cosa che poi nessuno ricontrolla.»*

> La frase che rende la voce onesta senza spaventare: lo stimatore coerente
> (Acerbi-Tasche) **è** «la media delle giornate peggiori», con l'ultima contata in
> proporzione a quanto rientra nel 5%. La definizione non cambia. Cambia che ora la
> calcoliamo bene.

Si coordina con la pagina CVaR del mandato **I**.

### 3.2 Il resto del capitolo

Le altre voci arrivano dai mandati, **user-facing soltanto**: i quattro livelli, il
laboratorio, il catalogo dei benchmark, i sottotipi di asset, il Monte Carlo rifondato,
l'affettamento del portafoglio.

**Non** entrano: M1, M3, M5, M6 (velocità e possesso, nessun effetto osservabile), la
promozione delle primitive, l'oracolo di test.

---

## 4. La verifica finale — cancello G-C

L'unico cancello del piano che blocca **tutti**.

### 4.1 Verifica per mandato

Per ciascuno degli **undici**: la definizione di finito è soddisfatta, l'evidenza è nel
suo piano vivo (`implementation/progress/<LETTERA>-esecuzione.md`), e il piano è
aggiornato fino all'ultimo passo.

⚠️ Non si accetta «verde» come risposta. Si accetta **il comando eseguito e il suo
esito**.

### 4.2 Verifica trasversale — le cose che nessun singolo mandato poteva vedere

| # | Verifica | Come |
|---|---|---|
| 1 | **La regola dei pesi** regge | Nessun simbolo di valuta in Asset Global, in nessun pannello |
| 2 | **Dashboard e Broker Detail sono lo stesso componente** | Ispezione: se sono diventati due, E ha fallito anche con i test verdi |
| 3 | **Un pannello, un livello** | Nessun file del rischio oltre le 600 righe |
| 4 | **Enum ↔ tabelle** | Il test di B passa: ogni `AssetType` ha icona, etichetta ×4 e secchio di scenario |
| 5 | **`undefined_windows` intatto** | L'avviso utente sui segnali rolling esiste ancora |
| 6 | **TE, IR e `sobol_start_index` spariti dalla UI** | Ricerca nel frontend |
| 7 | **`check-links` verde** | Nessun `DocsLink` appeso |
| 8 | **Nessuna porta della banda 6240 in ascolto** | `lsof` su ciascuna, `6240`-`6250` |
| 9 | **La convenzione di segno regge** | I campi acquisiti da N (`WR`, `DaR`, `CDaR`, `UCI`) hanno **la stessa convenzione** di `max_drawdown` dentro lo stesso oggetto. Riskfolio restituisce magnitudini positive: due convenzioni nello stesso output passerebbero ogni test |
| 10 | **NEA coincide con AI Export** | `NEA == 10000 / herfindahl_index_points` sullo stesso portafoglio. Se divergono, l'applicazione dice due numeri sulla concentrazione |
| 11 | **NEA non è mai mostrato da solo** | Ispezione della UI di L2: NEA senza diversification ratio dice «diversificato» a un portafoglio correlato 0,95 |
| 12 | **I due test di Asset Detail sono verdi e non riscritti** | `portfolio/risk-asset-detail.spec.ts` — sono la **rete** che prova che E ed F non hanno toccato la pagina parcheggiata (**D8**, **D47**). Verdi perché intatti, non perché adattati: `git log` su quel file deve mostrare **solo** lo spostamento di D |
| 13 | **La galleria è rigenerata** | **Due** mandati la muovono, non uno: **G** ha cambiato i colori dei grafici di allocazione, e **B** ha dato una classe esplicita alle pastiglie `INDEX` e `OTHER` (prima cadevano nel ripiego). La rigenerazione è **di questo mandato**, dopo l'integrazione: farla prima avrebbe fotografato uno stato intermedio. ⚠️ **`gallery.spec.ts` non è un test**: `EXCLUDED_SPECS` lo esclude dal runner in due punti — è **uno strumento di documentazione** invocato da `./dev.py mkdocs gallery`, e **non confronta immagini: le genera**. Non c'è un rosso da trovare, solo screenshot che diventano stantii |

### 📌 Il delta visivo atteso della galleria — da leggere PRIMA di rigenerare

Misurato da **B**, che ha verificato quali pagine la galleria cattura: `assets/list`,
`assets/list-table`, `assets/list-filtered`. Alla rigenerazione **le immagini cambieranno**,
e **non per un artefatto di merge**:

- `INDEX` e `OTHER` hanno ora una pastiglia **esplicita** invece del ripiego grigio;
- compaiono **sei sottotipi ETF** con etichette nuove in **quattro lingue**;
- il filtro per tipo elenca **17 voci** invece di 9, con l'intestazione di sezione ETF;
- `HOLD` ha un'etichetta diversa in **tutte e quattro** le lingue;
- **G** cambia separatamente i colori dei grafici di allocazione.

> ⚠️ **Il delta è atteso e corretto.** Se J lo tratta come regressione perde tempo; se non
> lo vede affatto, **le immagini della documentazione restano indietro rispetto al
> prodotto**. Va ricevuto **prima** di rigenerare, non dopo.

**Prova che la galleria non asserisce sull'aspetto**, misurata da B sul file:

| misura | valore |
|---|---|
| `toHaveScreenshot` / `toMatchSnapshot` | **0** |
| `await screenshot(...)` | **102** |
| `expect(...)` | 157, **tutti di navigazione** |

→ **Non esiste un'asserzione che possa diventare rossa per un colore.** L'unico modo di
romperla è **far sparire un `data-testid`**.

> ### ⚠️ Una nota che evita un falso allarme in §4.1
>
> Le definizioni di finito di **C** e **G** dichiarano `git diff` vuoto su
> `risk_plugins/` e sul backend. Sono corrette **nel loro worktree**.
>
> Sulla revisione combinata, però, `risk_plugins/` **avrà** modifiche: sono di **N**,
> che aggiunge campi additivi a `historical_kpi.py` e `risk_contribution.py`. È lavoro
> previsto, non una violazione.

### 4.3 Gate di integrazione

```bash
PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc \
  pipenv run python dev.py test --test-port 6249 --data-dir backend/data/test-risk-j \
  services risk-all
```

Più: `api risk`, `schemas risk`, lint e `svelte-check` sul frontend, gli spec E2E dei
mandati E, F, G, e `mkdocs build` in modalità stretta.

⚠️ **Sulla revisione combinata**: gli undici mandati hanno lavorato in worktree separati.
Due file possono fondersi senza conflitto testuale e **contraddirsi semanticamente** —
è esattamente ciò che [`README.md`](./README.md) §2.2 e §2.4 esistono per prevenire, ma
prevenire non è verificare. Le superfici condivise (`schemas/risk.py`, le quattro
lingue, il catalogo dei test) vanno **rilette a mano** sulla revisione combinata, non
solo testate.

---

## 5. Cosa si riapre dopo, e va lasciato scritto

Chiudere bene significa anche **non far sparire** ciò che è stato rimandato.

| Cosa | Dove | Stato atteso |
|---|---|---|
| **Asset Detail** | **D47** | Riaperto subito dopo, con le sue due lacune note: `risk_contribution` è `PORTFOLIO`-only, e la card rolling mostra un valore puntuale invece della forma nel tempo |
| Tracking error / information ratio | `TODO_FUTURI.md` | Ancora registrato, priorità bassa |
| Portfolio optimization | `TODO_FUTURI.md` | Ancora registrato, priorità molto bassa |
| Monte Carlo livelli 4-5 | `TODO_FUTURI.md` | Ancora registrato |
| Stimatori robusti di covarianza | `TODO_FUTURI.md` | Ancora registrato |
| Contributi al rischio su misure non-MV | [`../04-…`](../04-decisioni-e-questioni-aperte.md) Q7 | Deciso quando si ridisegna la card, col blocco dei contributi negativi |
| `SignalDomain.PORTFOLIO` | **D18** | Non serviva per la v1; se la sparkline di portafoglio diventasse desiderabile, il costo è la piattaforma segnali intera |

---

## 6. Archiviazione

A rilascio avvenuto, la catena di piani va archiviata secondo la skill `plan-archive`:
`LibreFolio_developer_journal/Release_2/Phase_0/02_riskfolioIntegration/` diventa una
fase archiviata, con il suo `README.md` indice e lo stato di ciascun mandato.

⚠️ **Non si archivia prima del rilascio**, e **non si cancella nulla**: l'archivio della
prima campagna (`_archive-backendFirst-G0G6/`) è servito a ricostruire cosa fosse stato
deciso davvero — e a scoprire che **una cosa data per decisa non lo era mai stata**
([`../06-…`](../06-matematica-librerie-e-reimplementazioni.md) §2.4).

---

## 7. Definizione di finito

- [ ] Gli **undici** mandati verificati uno per uno, con evidenza;
- [ ] le otto verifiche trasversali di §4.2 passate;
- [ ] banner rimosso da L1, L2, L3, replay e shock; **mantenuto sulla sola simulazione**;
- [ ] Asset Detail invariato e ancora col suo banner;
- [ ] `### 🔄 Changed` creata in `[Unreleased]`, con la voce M2 nei suoi tre fatti;
- [ ] gate di integrazione verdi sulla **revisione combinata**;
- [ ] superfici condivise **rilette a mano**, non solo testate;
- [ ] nessuna porta della banda `6240` in ascolto;
- [ ] i rinvii di §5 ancora registrati e visibili;
- [ ] messaggio di commit proposto — ⚠️ **il commit lo esegue il developer**.


---

## 🔴 Lo stato reale del CHANGELOG — verificato dal coordinatore il 18 Set 2026

**Non parti da zero, e non parti da un capitolo vuoto.**

### Cosa c'è già, e che questa campagna rende parzialmente falso

Il capitolo **`[1.1.0]`** contiene una sezione **«📉 Risk Analysis — new subsystem»** con:

- il banner beta per esteso (*«Analytic parameters, result shapes and the `/api/v1/risk`
  contract may still change… **always read the reported data-quality status alongside the
  numbers**»*);
- **«9 risk analytics»** — ⚠️ **numero che questa campagna cambia**;
- l'elenco per nome delle nove, incluse *Historical VaR / CVaR*, *Drawdown summary*,
  *Risk contribution*, *Comparison*, *Portfolio allocation*;
- l'isolamento di processo QuantLib/Riskfolio in worker `spawn`.

> ⚠️ **La riga *«always read the reported data-quality status alongside the numbers»* è ora
> pericolosa**, e la campagna sa perché: **D102** — `coverage` vale ≈ 1,000 **esattamente
> quando la distorsione è massima**, e **D144** — `min_coverage` è uno slider che **non può
> fare nulla**. Il CHANGELOG **manda l'utente a leggere il campo sbagliato.** Se `[1.1.1]`
> non lo corregge, quella frase resta in piedi.

### Dove scrivere

Il capitolo **`[Unreleased]`** (*«Preparing v1.1.1»*) ha già la struttura:

```
### ✨ Added
### 🐛 Fixed
    #### 🤖 AI Export and signal contracts
    #### 📥 Imports and transaction editing
    #### 🧩 Asset providers and feedback
### 🔄 Changed
```

**Nessuna voce di rischio.** Serve un `#### 📉 Risk Analysis` sotto `### 🐛 Fixed` — e
probabilmente anche sotto `### 🔄 Changed`, perché **M2 e A9 cambiano numeri già mostrati**.

### ⚠️ Le tre voci che DEVONO esserci, e che nessun altro scriverà

1. **Il CVaR sale a ogni livello di confidenza** (cifre in §2 qui sopra) — e **il VaR non
   cambia nella configurazione predefinita**.
2. **Sharpe e Sortino di ambito titolo con tasso privo di rischio non nullo erano lusingati**
   di **0,03–0,13** — **mai una percentuale**, e **a rf = 0 l'errore è esattamente zero**.
3. **La tassonomia passa da 9 a 17 tipi** con la bandiera benchmark, e `HOLD` era tradotto
   *«Liquidity»* in tre lingue — **rendendo un bene posseduto indistinguibile dal secchio
   sintetico della cassa nello stesso anello di allocazione**.

---

# 8. 🔴 I quattro cancelli che J eredita — nessun altro mandato può farli

> Scoperti **dopo** che questo brief è stato scritto, fra il 17 e il 18 Set. Tutti e quattro
> hanno la stessa forma: **un cancello valida l'artefatto che produce, non quello che l'utente
> riceve** — la tesi che questa campagna ha trovato nove volte.
>
> **Sono di J perché toccano `dev.py` e la configurazione di progetto, che non appartengono a
> nessun mandato di prodotto.**

## 8.1 Contare i `$$` grezzi nell'HTML costruito, **per lingua**

**Stiamo pubblicando LaTeX rotto in tre lingue.** Verità a terra misurata da I:

| | en | it | fr | es |
|---|---:|---:|---:|---:|
| `$$` crudi nell'HTML | **0** | **4** | **22** | **22** |

**Tre meccanismi distinti, un solo sintomo, e sono tutti WHITESPACE:**

1. due blocchi display su righe **adiacenti** → fusi, i `$$` interni finiscono **dentro** il
   LaTeX (`volatility`, ×4 lingue — **preesistente alla baseline**);
2. indentazione a **5 spazi** invece di 4 in un'admonition → reso come **testo**
   (`fifo-lot-analysis.es/.fr`, **20 ciascuna**);
3. **riga vuota inserita** fra formula e `$$` di chiusura → blocco spezzato
   (`fifo-lot-analysis.it`).

> *«Il 2 è uno spazio di troppo, il 3 una riga vuota di troppo, l'1 una riga vuota **mancante**:
> tre modi opposti di sbagliare la stessa cosa.»*

🔑 **Perché nessun controllo sul sorgente può vederlo**: produce **HTML perfettamente ben formato
che contiene LaTeX malformato**. La rottura avviene **nel browser, a tempo di parsing MathJax**.

✅ **Gate**: contare i `$$` nell'HTML costruito, **per lingua**; **zero è l'unico valore
accettabile**. Agnostico al meccanismo, consapevole della lingua **per costruzione**, costo una
lettura di un artefatto già prodotto.

⚠️ **E la regola di scrittura corretta**, che sostituisce quella sbagliata («mai `$$` in
un'admonition» **vieta ciò che funziona** — `fifo-lot-analysis.en` lo fa 20 volte a 4 spazi — **e
permette ciò che rompe**): **indentazione multipla di 4 · riga vuota FRA blocchi adiacenti ·
NESSUNA riga vuota DENTRO un blocco.**

## 8.2 `ruff format` riformatta file mai toccati, **irreversibilmente**

`pyproject.toml` configura **due** formattatori a `line-length = 300`: `[tool.black]` e
`[tool.ruff]`. Ma **`dev.py:1698` esegue `black backend/`** e **`dev.py:1705` esegue `ruff check
backend/`** — **`ruff format` non è invocato da nessun comando.** La configurazione lo fa
**sembrare sanzionato**.

🔴 **Misurato**: `black --check --line-length 300` sulla baseline → **EXIT=0, pulita**;
`ruff format --diff` sulla **stessa** baseline → **66 righe**. Dopo `ruff format` + `black`, il
file resta **a 50 righe dall'originale** e `black --check` dà **EXIT=0**.

> **Entrambe le forme sono conformi a black. `./dev.py format` non ripristinerà mai l'originale,
> e `./dev.py lint` non se ne accorgerà mai.**

⚠️ **È già successo**: **7 file fuori scopo dentro il checkpoint `1aaea6949` di N**
(`config.py`, `api/v1/system.py`, `schemas/common.py`, `schemas/prices.py`, `test_brokers_api.py`,
`test_scheduler_leader.py`, `test_scheduler_loop.py`). **I file di scopo di N sono integri.**

✅ **Due azioni**: **(a)** ripristinare i 7 percorsi prima del commit di N — *azione dello
sviluppatore*; **(b)** decidere se rimuovere `[tool.ruff] line-length` o aggiungere `ruff format`
al comando, **ma non lasciare due formattatori configurati che non concordano.**

## 8.3 `verbose` di `SharedBackend` non è impostabile

`scripts/test_runner/_server.py:161` lo accetta come parametro, `:269-270` lo usa per scegliere
fra `None` e `subprocess.DEVNULL` — **ma nessun chiamante lo imposta a `True`, e `dev.py test` non
espone `--verbose`.**

> **L'errore di avvio del backend condiviso è strutturalmente inosservabile dal runner.** Chi lo
> incontra vede `❌ Shared backend exited during startup (code 1)` **e nient'altro**, e deve
> ricostruire il comando a mano per leggere il traceback. *(Il coordinatore l'ha dovuto fare:
> era `Cannot find package 'typescript'`.)*

✅ **Gate**: esporre `--verbose` su `dev.py test`, **oppure** far confluire stdout/stderr del
backend in `.testLog/` sempre. **Un errore che non si può leggere non è un errore: è un silenzio.**

## 8.4 Le 42 ancore solo-inglesi, e l'inversione che le rende prevedibili

| pagina | tradotta? | ancore `en` | ancore `it` |
|---|---|---:|---:|
| `index` · `volatility` · `sharpe-ratio` · `sortino-ratio` · `max-drawdown` | **sì** | **42** | **0** |
| le altre **17** | **no** | 116 | — ✅ **sane in 4 lingue** |

🔑 **L'ancora è SANA dove la pagina NON è tradotta, ROTTA dove lo è**: il fallback i18n serve il
corpo inglese **intero, ancore comprese**; una traduzione **parziale** serve invece una pagina
tradotta **priva** dell'ancora.

> **Le 17 pagine nuove sono al sicuro proprio perché sono in debito di traduzione. Sarà il blocco
> di traduzione a metterle a rischio, non la sua assenza.**

⚠️ **41 sono innescate e mute**; MkDocs ne segnala 9 perché **una sola** è oggi bersaglio di un
link. **Diventano rosse nell'istante in cui E, F o H scrivono un `DocsLink` ancorato verso
`sharpe-ratio` o `volatility`** — cioè le metriche che l'app già calcola, **le prime che
cableranno**.

✅ **I ha già consegnato il gate delle ancore in quattro lingue** (`dev.py`, +133/−46, sonde
**6/6** sul modo di fallire). **Quello che resta a J**: decidere se anticipare la traduzione
— che le chiude tutte insieme — o mitigare con **`<div id="…"></div>`**, l'unica tecnica del
progetto che sopravvive **perché non è prosa**.

📌 **E una regola di nav trovata da I**: in `mkdocs.yml` **un'etichetta di nav È una chiave di
`nav_translations`**. Rinominarla è **sempre un'operazione a quattro voci**; farne una lascia
**tre voci mute senza errore di build**.

---

# 9. 📌 I due rename di schema — **un solo proprietario, perché sono lo stesso difetto di segno opposto**

| | indirizzo | difetto | proposta |
|---|---|---|---|
| **`coverage`** | `schemas/risk.py:451` | nome **troppo generico** — il nome giusto sta **cinquanta righe più su**, `:400` | **`calendar_coverage`** |
| **`percentage_contribution`** | `schemas/risk.py:673` | nome **sbagliato**: dice «percentage», porta una **frazione** | **`fraction_contribution`** + `description` |

**Perché `coverage` è una riparazione e non una decisione**: `:397-401` e `:448-452` portano la
**stessa sequenza di quattro campi**, e il quinto ha due nomi diversi. **Il file contiene già il
nome giusto.** *(Evidenza **strutturale**: chi esegue il rename lo confermi sul servizio che
popola il campo.)*

🔴 **Perché `percentage_contribution` non può essere difeso da uno schema**: un contributo può
**legittimamente** essere **negativo** (posizione correlata negativamente) **e superare 1,0**
(quando altre sono negative). → **Non esiste un `ge`/`le` corretto. Il solo guardiano possibile è
il nome — ed è il nome a mentire.** E il difetto ha già colpito: **E ci è cascato leggendo il
nome**, e i suoi 51 test unitari erano verdi perché le fixture erano scritte con la stessa
premessa.

> **La `description` è l'unica cosa che lo schema può portare**: *«frazione, somma 1,0, può essere
> negativa»*.

⚠️ **Terzo omonimo da non dimenticare**: `coverage` compare **tre volte con tre denominatori
diversi** — `:451` (calendario di **una serie**), `:656` (sovrapposizione **di coppia**), `:967`
(finestra **disponibile**). Il rename di `:451` non li chiude.

---

# 10. 🔴🔴 Il primo comando dopo l'integrazione del backend: **`api sync`**

> **Se non lo esegui, quattro pannelli di rischio si spengono e il rosso accusa il codice invece del
> disco.** Misurato da E, verificato dal coordinatore eseguendo gli schemi Zod.

## Il meccanismo, in due righe opposte

Il client usa **`validate: 'response'`** (`zodios-client.ts:170`). Quindi:

| cosa cambia nel backend | cosa fa Zod | sintomo |
|---|---|---|
| **un campo nuovo** (K1, K8 — A e N) | `z.object()` **senza `.passthrough()`** lo **cancella** | `success: true`, il lettore vede **`undefined`** — **silenzio** |
| **un valore d'enum nuovo** (K4 — C) | enum **chiuso** su un campo **obbligatorio** | 🔴 **l'intera `RiskQueryResponse` è rifiutata** |

**Misurato, con controllo positivo:**

```
RiskReturnBasis.safeParse('twrr')                          →  OK
RiskReturnBasis.safeParse('current_composition_backtest')  →  REJECTED (invalid_enum_value)
RiskKpiOutput + worst_realization + ulcer_index            →  success:true, tenute 4 chiavi su 6
```

## ✅ Ma non c'è nessun ordine di merge da decidere

```
git check-ignore -v frontend/src/lib/api/generated.ts  →  frontend/.gitignore:13
dev.py:563-566   →  il build chiama api sync e ABORTA se fallisce
```

> **`generated.ts` non è versionato, e il build lo rigenera sempre.** **Produzione e CI sono
> protetti per costruzione**: un frontend non può essere buildato contro uno schema stantio.

## 🔴 Il rischio è negli alberi, e il sintomo accusa la cosa sbagliata

**Ogni worktree ha un `generated.ts` stantio sul disco.** Dopo l'integrazione del backend:

> chi esegue un gate frontend **senza rigenerare** vede **Dashboard, Broker Detail, Asset Detail e
> Risk Lab tutti in errore** — perché `queryRisk` lancia e **l'errore va in cache** — e conclude
> che **qualcuno ha rotto il codice**.

**È un difetto di diagnosi, non di prodotto.** Chi lo incontra per primo **perde un pomeriggio
prima di sospettare `generated.ts`.**

## ✅ Cosa fare, e in che ordine

```bash
# 1. il backend integrato è nell'albero
# 2. PRIMA di qualunque gate frontend:
PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py api sync
# 3. e solo allora i gate di §4
```

⚠️ **Verifica che sia servito**, invece di darlo per fatto:

```bash
grep -c "current_composition_backtest" frontend/src/lib/api/generated.ts   # atteso: >= 1
grep -c "ulcer_index"                  frontend/src/lib/api/generated.ts   # atteso: >= 1
```

📌 **E un corollario per i contratti**: finché `generated.ts` non conosce un campo, **una fixture
che lo porta non esercita il ramo «presente» — lo esercita come assente, e passa**. È il mock
stantio **prodotto dal client invece che dal mock**, e vale per **K1, K8 e il ramo K4 di E**.

---

# 11. 🔴 I quattro vincoli operativi che J eredita — **ognuno è un errore già misurato**

> Nessuno di questi è teorico: ciascuno è stato **trovato eseguendo**, durante la campagna.

## 11.1 ⛔ `git add -u` da solo perde fino al **65 %** del lavoro

`git add -u` vede **solo i file tracciati**. Misurato su tutti e dieci i mandati:

| mandato | tracciati | **nuovi** | perso |
|---|---:|---:|---:|
| **E** · **I** · **D** · **F** | 13 · 10 · 6 · 10 | **24 · 19 · 12 · 13** | 🔴 **57-66 %** |
| B · A · H · N · C | 25 · 14 · 15 · 11 · 5 | 3 · 2 · 2 · 2 · 1 | 11-17 % |

> **La perdita è proporzionale a quanto un mandato ha *creato* invece che modificato: il lavoro di
> maggior valore è quello che `git add -u` non vede.**

```bash
W=<worktree>
git -C "$W" add -u
git -C "$W" ls-files --others --exclude-standard \
  | grep -v 'static/icons/asset-types/.*\.png$' \
  | xargs -r git -C "$W" add
git -C "$W" status --short          # nessun '??' oltre ai 2 PNG
```

⚠️ **I due PNG** `mkdocs_src/docs/static/icons/asset-types/{commodity,real-estate}.png` sono
**non tracciati e NON ignorati in nove worktree su dieci**. `H` è l'unico pulito.

## 11.2 ⛔ Dopo ogni fusione che tocca un `StrEnum`: **«è ancora esaustivo?»**

**Un difetto assente da entrambi i genitori e creato dalla loro unione.** `RiskReturnBasis` ha due
membri; **due** siti lo consumano con un ternario `else`-fallthrough — **esaustivi e corretti** su
due valori. C ne aggiunge **un terzo, altrove nel file**.

> **Zero conflitto testuale. Fusione pulita. Una stringa che chiama «close returns» un backtest a
> pesi correnti.** Nessuno dei due autori può vederlo dal proprio albero.

| sito | proprietario | terzo ramo |
|---|---|---|
| `historical_kpi.py:109` | **N** | `current_composition_backtest` |
| `drawdown_summary.py` *(`:54` baseline · `:58` albero di A)* | **A** | idem |

➕ **E lo stesso enum ha un consumatore muto sul frontend**: `RiskResultFrame.svelte:108` costruisce
**una chiave i18n dinamica** — `i18n audit` **non sa quali chiavi nascono a runtime**.

```bash
grep -rn "RiskReturnBasis" backend/app/              # sul RISULTATO FUSO, non su un genitore
grep -rn 'risk\.[a-zA-Z]*\.\${' frontend/src         # chiavi costruite a runtime
```

## 11.3 ⛔ **Non eseguire `black` su `scripts/`**

`dev.py:1698` formatta **`backend/`**, `:1705` lint **`backend/`**. **`scripts/` è fuori da
entrambi**, e `black --check scripts/test_runner/_backend_services.py` **fallisce già alla
baseline**, committato.

> **Ci vive il file che il maggior numero di mandati modifica** (il nodo di catalogo F/G/D) **ed è
> l'unico di quell'insieme che né `format` né `lint` guarderanno mai.** Riformattarlo durante
> l'integrazione produce **un conflitto gratuito e grande**. **Il divario va saputo, non chiuso.**

## 11.4 ⚠️ Le prove per SHA **scadono**: `cat-file` non basta

**Misurato su tutti e tre gli SHA usati per il relay:**

```
git branch -a --contains 1aaea6949 (N) · 1a537f9cb (D) · 590f32ae6 (B)   →  0 rami, tutti
```

Vivono **solo** sotto `refs/copilot/checkpoints/`. **Un ref di checkpoint è cancellabile, e alla
cancellazione il commit è potabile dal GC.**

> **`git cat-file -t` prova l'ESISTENZA; serve `git branch --contains` per la STORIA.** Due domande
> diverse, e **il primo comando non accenna che la seconda esista.**

✅ **Il commit dei mandati non è il passo successivo: è ciò che trasforma una prova temporanea in
una permanente.** Chi consegna dopo la potatura **deve rimisurare da zero**.


---

# 12. ⛔ **Tre contratti sono «costruiti, provati e SPENTI»** — non contarli come resi

> **Trovato da E, generalizzato dal coordinatore su tutti e tre gli alberi d'origine.**

I campi di **K1**, **K6** e **K8** **non esistono in nessuna baseline**: vivono solo nel worktree del
mandato che li ha scritti.

| campo | baseline | albero d'origine |
|---|---:|---:|
| `RiskSimulationRegime` · `bootstrap_seed` · `block_length_days` | **0** | **H: 4 · 1 · 5** |
| `return_bins` · `var_bin_edge` · `underwater_series` | **0** | **A: 4 · 2 · 1** |
| `worst_realization` · `ulcer_index` · `diversification_ratio` | **0** | **N: 2 · 2 · 1** |

## 🔴 Conseguenza: `api sync` prima della fusione è **un verde a vuoto**

> *« `api sync` legge **la mia** OpenAPI, non quella di H. Girerebbe, **uscirebbe verde e produrrebbe
> zero tipi nuovi**. **Non è che non serve: è che sembrerebbe servito.** »*

**Stessa famiglia del gate cieco e del mock stantio**, applicata a un comando di sincronizzazione.

## ⚠️ E il lato frontend è già costruito, ma cieco

`SimulationProvenance` (K6) è **costruita e testata unitariamente**. Ma **Zod cancella i campi che
non sono nello schema**, quindi oggi il componente rende le voci che ha e **omette in silenzio**
regime, seme e lunghezza del blocco.

> *« I miei unitari passano perché **costruiscono l'output direttamente, scavalcando il filo**. »*

## ✅ Cosa deve fare J

1. **Non contare K1, K6, K8 come resi** finché non li ha **visti sul filo**, non nei test unitari.
2. `api sync` **dopo** la fusione di A, H e N — **mai prima**, e **mai in un albero che non contiene
   il backend che dichiara i campi**.
3. **Verificare che sia servito**, invece di fidarsi dell'uscita verde:

```bash
for f in RiskSimulationRegime bootstrap_seed block_length_days          return_bins var_bin_edge underwater_series          worst_realization ulcer_index diversification_ratio; do
  printf '%-24s %s\n' "$f" "$(grep -c "$f" frontend/src/lib/api/generated.ts)"
done      # ogni riga deve essere >= 1
```

📌 **Regola che ne esce, e vale oltre questi tre**: **un comando di sincronizzazione che non
ha nulla da sincronizzare esce verde.** Il suo esito non dice se è servito — **lo dice solo il
contenuto dell'artefatto che ha prodotto.**


---

# 13. 🔴 Una coppia **atomica su due alberi** — da applicare nella stessa revisione

**F** ha collassato in un passo il flusso di aggiunta asset e **rimosso** `risk-asset-add-button`.
**E** ha uno spec che **clicca quel bottone**.

```
togliere la riga di E  PRIMA  di innestare F   →  🔴 rosso
innestare F  SENZA  togliere la riga di E      →  🔴 rosso
```

> **Non c'è un ordine sicuro: c'è solo la simultaneità.** Le due modifiche vanno nello **stesso
> commit di integrazione**.

⚠️ **I numeri di riga del rapporto di F non valgono**: lo spec di E è cresciuto da 817 a **1748**
righe (**offset +438**). La riga da togliere è **`:1092` nell'albero di E**, non `:654`.
**Cercare il simbolo `risk-asset-add-button`, non saltare alla riga.**

✅ **E la cancellazione è sicura per costruzione**: l'asserzione successiva (`:1093`) **nomina il
risultato, non il meccanismo** — se l'aggiunta non avviene, diventa rossa da sola. **Non serve
verificare il pannello di F prima di togliere la riga.**

📌 **Distinta da §11.2**: là un difetto **nasce dall'unione**; qui **due modifiche sono ciascuna
rossa da sola e verdi solo insieme.** Un cancello non basta — **serve che chi fonde le applichi
insieme.**


---

# 14. ⚠️ Una chiave i18n condivisa da due superfici — decidere all'integrazione

**E** ha cambiato `risk.metrics.cashWeight` da *«Cash weight»* a *«Cash and uncovered»*, e la
chiave **è usata da due file**:

| superficie | come legge il campo | effetto del testo nuovo |
|---|---|---|
| `L2Diversification.svelte` *(nuovo)* | **`!== null`** | ✅ corretto |
| `RiskAnalysisPanel.svelte:859` *(legacy)* | **`?? 0`** | 🔴 un dato assente diventa **«Cash and uncovered: 0,0 %»** |

> **«Uncovered» afferma che si è verificato che nulla è scoperto.** *«Cash weight: 0,0 %»* si
> legge come un peso nullo; **il testo nuovo sulla superficie sbagliata afferma una verifica che
> non è avvenuta.**

📌 **E il legacy serve Asset Detail e il laboratorio di F** — cioè **il difetto che E ha impedito
a L2 è spedito oggi altrove**, con lo stesso campo e la stessa lettura.

## ✅ Due opzioni, entrambe difendibili

1. **Separare le chiavi** — `risk.metrics.cashWeight` per il legacy, una nuova per L2;
2. **riparare il `?? 0` del legacy** insieme al cambio di testo — una riga, e chiude entrambe.

⚠️ **La seconda tocca il pannello legacy**, che è stato **preservato byte per byte di proposito**
da E. **Non è una decisione da prendere durante una risoluzione di conflitto.**
