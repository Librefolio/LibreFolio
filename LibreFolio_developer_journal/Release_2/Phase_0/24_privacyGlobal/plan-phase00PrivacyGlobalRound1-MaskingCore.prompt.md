# Piano d'implementazione — U2 / SP15 privacy globale, Round 1: nucleo di mascheramento

> **Origine.** Esegue i passi **1-5** di [`analysis-phase00PrivacyGlobal.md` §7.2](./analysis-phase00PrivacyGlobal.md)
> (commit `d2355d341`). L'analisi è la fonte del contratto (§2), delle primitive (§3), del design
> dello store (§4) e delle decisioni D1-D7 (§0). **Questo piano non ridecide**: dove diverge,
> lo dichiara.

| | |
|---|---|
| **Sprint** | SP15 — task **U2** |
| **Workstream** | J — lane **6158**, data dir `/tmp/librefolio-r2-j-onboarding` |
| **Worktree** | `e-alfy-literate-lamp`, branch `e-alfy-onboarding-foundation` |
| **Baseline** | `d2355d341` (`docs(privacy): add U2 global privacy analysis`) |
| **Autorizzato** | passi 1-5; passo 3 a **3 siti su 4**; **passo 6 = toggle nell'header** (sostituisce i grafici) |
| **Creato** | 2026-09-21 |

---

## §0 — Perimetro, e ciò che ne resta fuori

### Autorizzato

| passo | contenuto | §analisi |
|---|---|---|
| 1 | store privacy + chiave nuda `librefolio-privacy` | §4 |
| 2 | `maskable` nei due formattatori di importi, **default sicuro** | §3.2 |
| 3 | falsi negativi — **3 siti su 4** | §1.8 |
| 4 | classificazione dei siti pubblici | §7.2 |
| 5 | `SensitiveValue` | §3.3 |
| **6** | **toggle nell'header** — *nuovo*, prende il posto del passo 6 originale (grafici, vietato) | — |

### 🔴 Fuori, e perché

| escluso | ragione | chi lo sblocca |
|---|---|---|
| `frontend/src/lib/components/dashboard/GrowthChart.svelte:692` | **I ci sta scrivendo ora** (round 2: bucketing, pillbox, area, candele, linea di riferimento) | coordinator, al rientro di I |
| gli altri 13 componenti ECharts (passo 6) | divieto di collisione; il passo 4 può **elencarli**, non editarli | coordinator |
| classe fuori-DOM: clipboard, export, cross-doc | **Q1** e **Q2** aperte al developer | developer |
| gate anti-regressione §1.8 | **proposta non autorizzata**, riformulata in tre righe — *in attesa che il coordinatore la porti al developer* | developer |
| `frontend/src/lib/stores/app/themeStore.ts:51` | buco latente noto (`setItem` con la sola guardia `typeof`) **fuori dal perimetro di U2** | — non si tocca |

### D8 — Il segno resta visibile — *decisione del developer, 2026-09-21*

Arrivata **a passo 2 già chiuso e già coperto da test**, quindi è una regressione deliberata su
codice scritto, non un requisito iniziale. Registrata con l'obiezione accanto, perché fra sei mesi
si deve leggere *«il segno resta visibile, e sappiamo cosa costa»*, non *«il segno resta visibile»*.

| | |
|---|---|
| **decisione** | la cella mascherata rende `+••• $ 🇺🇸 USD` / `-••• $ 🇺🇸 USD` |
| **obiezione posta** | il segno non *accompagna* il valore: è **derivato** da esso, e su un P&L rivela se chi guarda è in guadagno o in perdita — forse il bit più sensibile della cifra |
| **esito** | respinta a favore della leggibilità, **con l'obiezione sul tavolo** |

> *Un argomento respinto con l'obiezione sul tavolo è una decisione; lo stesso argomento non posto è
> un difetto.*

#### Il costo, misurato — ed è più grande di come è stato presentato

Il coordinatore ha nominato il caso zero come *«una fuga piccola e forse accettabile»*. Misurata, la
dimensione è un'altra: **`sign` ha tre valori, non due**, e i siti che li distinguono tutti e tre
sono la maggioranza.

```
showSign: value !== 0    UnifiedLotsTable:192   ExposureTable:136   ContributionTable:171
                         OtherPeriodEffectsTable:95   LotGanttChart:255   LotCustodyModal:84
```

In quei **sei** siti il prefisso è presente **se e solo se** l'importo è diverso da zero. Quindi una
colonna interamente mascherata continua a dire **quali righe hanno un valore e quali no** — su
`ContributionTable` e `OtherPeriodEffectsTable` è una mappa dell'attività per periodo.

> La decisione è stata presa sull'argomento *«su o giù»*. Il contenuto reale è *«su, giù, o piatto —
> riga per riga»*. **Non riapro la decisione**: riporto che ciò che è stato deciso è più di ciò che
> era sul tavolo, e la conferma spetta a chi l'ha presa.

**Applicata** in `frontend/src/lib/utils/currency/currencyFormat.ts:40` e `:62`: il prefisso esce dal
`maskable()`, che ora riceve il solo `abs`. I due docstring di
`frontend/src/lib/utils/privacy/maskable.ts` **affermavano l'opposto** e sono stati riscritti con la
decisione e il suo costo — un modulo che motiva una scelta che non fa più è una specifica falsa nel
punto esatto in cui la classificazione è decisa.

> ⚠️ **Clausola attiva su I.** Il passo 3 tocca
> `frontend/src/lib/components/risk/RiskAnalysisPanel.svelte` e
> `frontend/src/lib/components/brokers/lots/LotComparisonChart.svelte`. Il coordinatore ha misurato
> le hunk di I: nessuna collisione con 3 righe di contesto (distanza minima 24 e 39 righe). **Se I
> annuncia di riaprirli, mi fermo su quei file e lo segnalo** invece di scoprirlo in un conflitto.

### 🔴 Il limite dichiarato di questo round — **risolto dal developer, non più un limite**

Dichiarato prima di iniziare: *a fine passo 5 non esiste nessun interruttore raggiungibile
dall'utente*. Il developer ha deciso di **anticipare il toggle** invece di accettarlo:

> *«Bisogna anticiparlo, necessariamente, ma non vedo perché farlo grezzo, si tratta di un bottone
> in fondo.»* — posizione: **header**, accanto agli altri controlli globali.

**Conseguenza sulla DoD, che cambia il criterio di «fatto»**: a fine passo 6 il developer deve poter
**premere il bottone e vedere i valori sparire** sulle superfici classificate. Non più «verificabile
solo da unit test»: **dimostrazione a mano**, come sta facendo con i grafici.

E la posizione **dissolve Q5 invece di risponderle**. La domanda era *«il toggle è raggiungibile da
tastiera e da mobile?»*; un controllo nell'header è raggiungibile da ogni pagina senza navigare,
che è ciò che chiedeva il requisito di latenza d'uso. La domanda **perde l'oggetto**: non ha una
risposta da cercare.

> ⚠️ Scritta così di proposito. **Una domanda che smette di avere oggetto non è una domanda
> risposta**, e la differenza conta per chi più avanti cercherà la risposta di Q5 e non la troverà.

Restano i dettagli veri — focus da tastiera, area di tocco su mobile, eventuale scorciatoia — e si
decidono con le **convenzioni già in uso nell'header**, non con una domanda nuova al developer.

Collisione misurata dal coordinatore su
`frontend/src/lib/components/layout/Header.svelte`: **0** nel diff committato di I, **0** nel lavoro
in corso. Nessuna clausola.

### 🔴 La proprietà di conformità di questo round è **parziale**

§7.2 dice che dopo i passi 2 **e** 3 il sistema è conforme al contratto. Con `GrowthChart:692`
fuori, **non lo è**: quel sito rende denaro senza passare dal canale e resta in chiaro.

> Non è una dimenticanza: è un **residuo nominato**. Va scritto qui perché al checkpoint
> «passi 1-6 completi» non si legga come «sistema conforme».

---

## §1 — Passi

### Passo 1 — Store privacy — **Stato: ✅ fatto** — 2026-09-21

**File nuovo**: `frontend/src/lib/stores/app/privacyStore.svelte.ts`

Design da §4.3, con la correzione di precedente già applicata all'analisi:

| elemento | forma | precedente misurato |
|---|---|---|
| stato | `boolean` in `$state` | `frontend/src/lib/stores/chartSettingsStore.svelte.ts:132` |
| chiave | `librefolio-privacy`, **nuda** (non `lf_{userId}_`) | §4.2, D2 |
| idratazione | sincrona all'init del modulo | — **non** `themeStore`, che legge pigro |
| guardie | `typeof`/`browser` **+** `try/catch` sui **due** versi | `frontend/src/lib/utils/storage.ts:33-34,47-48` |
| reset di sessione | **nessuno** — sopravvive a logout e cambio account | §4.2 |
| dipendenza reattiva | lettura di `$state` dentro la funzione esportata | `chartSettingsStore.svelte.ts:201` (`void _version;`) |

**Il modo di guasto che vincola la scrittura** (§4.3): un `setItem` che lancia lascia lo stato
**acceso in memoria e spento su disco** ⇒ al reload i valori ricompaiono in silenzio. La scrittura
va protetta **e** il suo esito considerato.

**DoD**: `svelte-check` al pavimento; nessun consumatore ancora.

> **Note implementazione (2026-09-21).** Creato
> `frontend/src/lib/stores/app/privacyStore.svelte.ts`: `PRIVACY_STORAGE_KEY`,
> `isPrivacyEnabled()`, `isPrivacyPersisted()`, `setPrivacyEnabled()`, `togglePrivacy()`.
> `let enabled = $state(readStoredPreference())` a livello di modulo, `persisted` separato.
> Valori `'1'`/`'0'`; chiave assente ⇒ spento (D3). Entrambi i versi con `browser` **e**
> `try/catch`.
>
> Gate: `PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py front check`
> → `3 errors and 41 warnings in 4 files`, **pavimento esatto**. I 3 errori sono preesistenti in
> `frontend/src/lib/components/transactions/modals/TransactionFormModal.test.ts:787,819`.
>
> Verifica del precedente d'import, fatta **prima** di scrivere: un `.ts` semplice può
> value-importare un modulo runes? Sì — `frontend/src/lib/stores/app/auth.ts:18` importa
> `donationPopupStore.svelte.ts`, che dichiara 1 `$state`. *Il primo candidato che avevo trovato,
> `frontend/src/lib/stores/app/notify.svelte.ts`, dichiara **0** `$state`*: un `.svelte.ts` che non
> è un modulo runes. Se l'avessi usato come precedente non avrei provato niente — decimo caso del
> difetto del contenitore, questa volta intercettato dal controllo e non dall'errore.

---

### Passo 2 — `maskable` nei formattatori — **Stato: ✅ fatto** — 2026-09-21

**File**: `frontend/src/lib/utils/currency/currencyFormat.ts`

- `CurrencyAmountFormatOptions` (`:15`) → campo `sensitivity?: 'personal' | 'public'`;
- **omesso ⇒ `personal` ⇒ mascherato** (§3.2, asimmetria del modo di guasto);
- copertura: `formatCurrencyAmountPlain` (`:30`, **47 siti**) e `formatCurrencyAmountHtml`
  (`:51`, **14 siti**);
- **non** tocca `formatCurrencyCodeHtml` (`:75`) né
  `frontend/src/lib/components/assets/providerProbe.ts:72` — **nessuna delle due rende un importo**.

**Conferma di design registrata dal coordinatore**: in entrambe le funzioni l'importo è isolato in
una locale `formatted`, e la versione HTML lo avvolge già in `<span class="currency-amount">`.
Il mascheramento è **una sostituzione sola per funzione**; simbolo, bandiera e codice sopravvivono.
Output atteso: `••• $ 🇺🇸 USD`. **D5 non è un vincolo da rispettare: è la forma naturale del codice.**

**DoD**: unit test via `test-author` — ogni asserzione negativa con il suo **controllo positivo**
(§2.3), e due ordini di grandezza diversi che producono **lo stesso** segnaposto (§2.2.2).

> **Note implementazione (2026-09-21).** File nuovo
> `frontend/src/lib/utils/privacy/maskable.ts`: `PRIVACY_PLACEHOLDER = '•••'`,
> `AmountSensitivity`, `shouldMaskAmount()`, `maskable()`. Separato da
> `currencyFormat.ts` perché il passo 5 (`SensitiveValue`) e i siti di §1.8 usano lo **stesso**
> segnaposto e la **stessa** decisione: un solo luogo in cui la classificazione è decisa.
>
> `currencyFormat.ts`: campo `sensitivity` nell'interfaccia (`:15`) e **una** riga cambiata per
> funzione, `const formatted = maskable(…, sensitivity)` a `:30` e `:51`. `formatCurrencyCodeHtml`
> (`:75`) non toccato.
>
> `shouldMaskAmount` mette `sensitivity !== 'public'` **prima** della lettura dello store: un
> importo pubblico non cambia mai con il flag, quindi registrarne la dipendenza reattiva
> produrrebbe solo invalidazioni incapaci di alterare l'output.
>
> Gate: stesso comando → `3 errors and 41 warnings in 4 files`. Ho confrontato **l'elenco dei
> file**, non solo i conteggi: identico a quello del passo 1 (`BrokerSharingPanel`,
> `GlobalSettingsTab`, `TransactionFormModal.test.ts`, `ToolExecutionMetrics`). *Quattro errori in
> quattro file diversi danno lo stesso numero di quattro errori negli stessi quattro file.*

---

### Passo 3 — Falsi negativi §1.8 — **Stato: ✅ fatto** — 2026-09-21 — 3 siti su 4

**Va prima della classificazione**, non dopo: finché restano fuori, la proprietà di sicurezza del
passo 2 è falsa in modo non visibile.

| # | path completo | forma |
|---|---|---|
| 1 | `frontend/src/lib/components/risk/riskAnalysisHelpers.ts:130` | il **quinto formattatore**: `Intl.NumberFormat({style:'currency'})` fuori da `currencyFormat.ts` |
| 2 | `frontend/src/lib/components/risk/RiskAnalysisPanel.svelte:737` | unico consumatore di #1 (`import * as riskHelpers` a `:46`) |
| 4 | `frontend/src/lib/components/brokers/lots/LotComparisonChart.svelte:245` | `formatAxisCurrency`, asse compatto (`€12K`) |
| ~~3~~ | ~~`.../dashboard/GrowthChart.svelte:692`~~ | **residuo nominato** — I ci sta scrivendo |

`#1` e `#2` sono una **coppia chiusa**: un helper, un solo consumatore, nessun altro riferimento in
`frontend/src`. Si fanno insieme.

Fuori dal passo per decisione dell'analisi:
- `frontend/src/lib/components/charts/MeasurePanel.svelte:257` — `toFixed(4)` **senza valuta**, sito
  di **giudizio**, segue il passo 4;
- `frontend/src/lib/components/transactions/events/EventCreateMiniModal.svelte:73` — scrive un
  `value` di input ⇒ **D7, fuori scope**.

> **Note implementazione (2026-09-21).** Tre siti previsti, **due file toccati**. La coppia chiusa
> si è rivelata più chiusa del previsto: `riskHelpers.formatCurrencyAmount` ha **un solo**
> riferimento in tutto `frontend/src` (misurato, non assunto), quindi mascherare l'helper copre il
> sito 2 **senza editare `RiskAnalysisPanel.svelte`**. Il file più vicino alle hunk di I è finito a
> zero righe modificate.
>
> | file | righe mie | hunk di I più vicina | distanza |
> |---|---|---|---|
> | `frontend/src/lib/components/risk/riskAnalysisHelpers.ts` | docstring + `:130` | — *I non lo tocca* | — |
> | `frontend/src/lib/components/risk/RiskAnalysisPanel.svelte` | **nessuna** | 713 | — |
> | `frontend/src/lib/components/brokers/lots/LotComparisonChart.svelte` | 46, 248-251 | 21 e 201-208 | **25** e **40** |
>
> Misurate con `git diff -U0`, non stimate: con 3 righe di contesto gli intervalli 43-49 e 245-254
> non incontrano 18-24 né 198-211.
>
> **Gate**: `front check` al pavimento, stessi 4 file. Più
> `npm run test:unit -- src/lib/components/risk/riskAnalysisHelpers.test.ts` → **62 passed**.
> Il numero da solo non direbbe nulla: ho verificato che quel file **eserciti** la funzione
> cambiata — `describe('formatCurrencyAmount')` a `:282`, **7 asserzioni** dirette, incluse
> `'$1,234.50'` e i quattro casi di em-dash. *Una suite verde che non tocca la riga cambiata non è
> una prova, è un'omonimia.*

#### La seconda uscita che l'analisi non aveva contato

`formatAxisCurrency` ha **due** ritorni che rendono denaro: l'`Intl` citato da §1.8 a `:245` e il
fallback del `catch`, `` `${formatAxisNumber(normalized)} ${currency}` ``. Mascherare il primo
avrebbe lasciato in chiaro il secondo **esattamente quando l'API di locale non è disponibile**.

Maschera messa al **confine della funzione**, non alla chiamata `Intl`: copre entrambe le uscite e
costa una riga invece di due.

> §1.8 elencava *righe*, e una riga è il posto dove il difetto si **vede**, non il posto dove
> **finisce**. L'unità che tiene una proprietà di sicurezza è la funzione, perché è ciò che ha un
> contratto; la riga ne è solo l'istanza che qualcuno ha guardato.

#### Un contratto scritto che la maschera violava

`frontend/src/lib/components/risk/riskAnalysisHelpers.ts` dichiara nel docstring *«None of it
touches a store, a canvas, or the DOM»*. Leggere il flag di privacy dentro `formatCurrencyAmount`
rende quella frase **falsa**.

Le due uscite erano: mascherare nel consumatore (docstring salvo, ma la decisione torna al **sito**,
che è ciò contro cui §1.8 argomenta) oppure nell'helper (canale salvo, docstring da correggere).
Scelto il canale — è il quinto formattatore, e il senso di decidere in un formattatore è decidere
**una volta sola**.

Il docstring è stato **riscritto con l'eccezione e la sua ragione**, non lasciato marcire.

> Avrei creato l'undicesimo caso del difetto di questa sessione con le mie mani, e l'unico in cui
> l'affermazione era vera fino al momento in cui l'ho resa falsa. *Un documento che invalidi
> scrivendo è l'unico che hai la certezza di poter correggere.*

#### L'em-dash non si maschera

Il controllo di privacy sta **dopo** i due `return '—'`. Mascherare un'assenza trasformerebbe
*«qui non c'è una cifra»* in *«qui c'è una cifra e non puoi vederla»*: due affermazioni diverse, e
la seconda è falsa. È l'inversione già vista in questa sessione con lo `0` che sembrava un'assenza,
girata: un'assenza che sembrerebbe un valore.

---

### Passo 4 — Classificazione dei siti pubblici — **Stato: ✅ fatto** — 2026-09-21

Il lavoro **L**. Procede per viste, dalle più usate, riducendo la sovra-mascheratura.

**Checklist per sito**:
1. l'importo è **di chi guarda** o **pubblico** (quotazione, tasso)? → `sensitivity`;
2. rischio di **composizione** (D6): una percentuale accanto a un importo visibile;
3. il sito è dentro un `formatter` ECharts? → **elenca, non editare** (passo 6 vietato).

**Sito di giudizio trovato in anticipo, forma D5**:
`frontend/src/lib/utils/transactions/resolveValidationMessage.ts:185` formatta un saldo dentro un
**messaggio di errore di validazione**. Mascherato dà *«saldo insufficiente: •••»* — che non dice
nulla di azionabile. È la stessa forma di guasto dell'argomento sulle quantità che ha battuto il
piano approvato: **la maschera rompe la funzione nel momento in cui serve**. Da decidere nel passo,
con la ragione scritta.
*(La seconda branca, `:188-192`, formatta un saldo **di asset** con `toLocaleString` e 📈/📉: è
strutturale per D5 e resta correttamente fuori dal canale.)*

> **Note implementazione (2026-09-21).** 61 siti riesaminati, **una sola** riga marcata `public` e
> **una sola** riga lasciata di proposito senza marcatura, con il motivo scritto nel codice.
> Il conteggio canonico di §1.1 è stato **riprodotto**, non ripreso: 47 + 14 = 61.
>
> | sito | esito |
> |---|---|
> | `frontend/src/lib/components/assets/AssetTable.svelte:210` | ✅ `sensitivity: 'public'` |
> | `frontend/src/lib/components/dashboard/ExposureTable.svelte:388` | ⛔ **resta mascherato**, benché sia la stessa quotazione |
> | gli altri 58 | default `personal`, nessuna modifica |
>
> **Gate**: `front check` al pavimento, stessi 4 file.

#### Il lavoro **L** non era L, e la ragione è il default

L'analisi prevedeva *«il pezzo più lungo»*: classificare 61 siti. Con il default sicuro, un sito
classificato correttamente **non richiede una riga**. Il passo è diventato una **revisione** di 61
siti con **2 edit**.

> Un default sicuro non sposta solo la direzione del guasto: sposta **dove si trova il lavoro**.
> Con default `public` avrei dovuto toccare 59 siti e sbagliarne qualcuno in silenzio; con default
> `personal` devo giustificare **le eccezioni**, che sono poche e si vedono.

La stima XL dell'analisi resta giusta per il round, ma la sua ripartizione era sbagliata: il costo
non sta nella classificazione, sta in §1.8 e nei grafici.

#### 🔴 La scoperta: **la stessa quotazione è pubblica in una tabella e non nell'altra**

`AssetTable:210` e `ExposureTable:388` rendono la **stessa specie di valore** — il prezzo unitario
di mercato di un asset, identico per ogni utente, che non rivela nulla di chi guarda. La
classificazione ovvia le marca entrambe `public`.

È sbagliato per una sola delle due, e non per ciò che il valore **è**:

```
ExposureTable, stessa riga:
  :364  quantity        visibile      (D5: le quantità non si mascherano)
  :377  price           -> public ?   visibile
  :338  value           MASCHERATO

  quantity × price = value
```

**Una moltiplicazione fra due colonne visibili ricostruisce la colonna mascherata**, sulla stessa
riga, nella tabella di default della dashboard. `AssetTable` non ha il difetto perché non ha un
vicino mascherato: è il registro degli asset — nome, tipo, valuta, prezzo, delta, provider — e
`quoteBaseQuantity` (`:271`, `?? 1`) è l'unità di quotazione, **non** una posizione dell'utente.

> La sensibilità non è una proprietà del valore. È una proprietà del valore **e di ciò che gli sta
> accanto**. Due siti con la stessa semantica ricevono due classificazioni diverse, e chi legge
> solo il valore non può derivarne nessuna delle due.

Questo **limita il criterio meccanico** che avevamo cercato in §1.8. *Da quale formattatore esce?*
resta valido per decidere **cosa passa dal canale**; non basta per decidere **cosa esce dal canale
come `public`**. Quella decisione richiede di guardare i vicini, e l'unico posto dove i vicini sono
visibili è il sito.

Di qui la forma delle due modifiche: entrambe portano la ragione **nel codice**, e quella di
`ExposureTable` documenta un `public` **non messo**. *Una marcatura assente non si distingue da una
dimenticanza, a meno che qualcuno scriva che è una scelta.*

#### Il sito di giudizio: deciso **mascherato**, con l'argomento contrario scritto

`frontend/src/lib/utils/transactions/resolveValidationMessage.ts:185` resta al default.

| a favore del mascheramento | contro |
|---|---|
| è il saldo di cassa dell'utente, il valore personale per eccellenza | il messaggio perde la parte azionabile: si sa *che* manca, non *quanto* |
| il messaggio compare durante l'inserimento dati, superficie a lunga permanenza | l'utente conosce già il proprio saldo |
| il messaggio **continua a nominare la causa**: la funzione degrada, non si rompe | l'asimmetria con la branca asset (`5 📈` visibile) è visibile all'utente |

Differenza da Q3, che è ciò che ribalta l'esito: lì la maschera rendeva la tabella dei lotti
**inutilizzabile**; qui il messaggio resta comprensibile senza la cifra. *Una funzione degradata e
una funzione rotta si somigliano solo finché non si prova a usarla.*

Resta **sovvertibile dal developer** con una riga, come fu per Q3.

#### Un difetto nel conteggio canonico: uno dei 61 è un commento

`frontend/src/routes/(app)/transactions/+page.svelte:166` è una riga di commento che **nomina** i
due formattatori spiegando perché la cache valute va idratata. Il metodo di §1.1 — *«righe che
contengono il simbolo meno le righe di import»* — non esclude i commenti.

I siti di chiamata reali sono **60**, non 61.

Non cambia nessuna conclusione: un commento non si classifica. Cambia un'**affermazione di
copertura** — «61 su 61» conterebbe come coperto qualcosa che non esegue.

> Un metodo di conteggio si giudica su ciò che esclude. §1.1 fu scritto per correggere un perimetro
> che escludeva i `.ts`; nel farlo ha incluso tutto il resto, commenti compresi. **La correzione di
> un filtro troppo stretto tende a produrne uno troppo largo**, e il secondo errore è più difficile
> da vedere perché il numero cresce e sembra più prudente.

---

### Passo 5 — `SensitiveValue` — **Stato: ⏸ sospeso** — 2026-09-21 — *nessun consumatore misurato*

Primitiva di componente per il denaro che **non** passa dai formattatori (§3.3). Firma da §3.3;
default `personal`; segnaposto a forma stabile.

**Superato da D5/D7**: la motivazione originale citava le quantità e i campi di input. Le quantità
sono **visibili** (D5) e gli input **fuori scope** (D7). Resta il caso delle celle costruite a mano.

> **Note implementazione (2026-09-21) — non implementato, e la ragione è misurata.** §3.3 nomina
> **tre** casi d'uso. Al momento in cui il passo è stato aperto, tutti e tre erano chiusi o coperti:
>
> | caso d'uso di §3.3 | stato oggi |
> |---|---|
> | quantità (`formatQuantity`, 25 siti) | **Q3 chiusa: visibili.** Non si mascherano |
> | campi di input | **D7: fuori scope** |
> | celle costruite a mano | sono i 6 siti di §1.8 — 4 risolti **al formattatore** nel passo 3 |
>
> Dei due residui di §1.8, nessuno può consumare un componente Svelte:
> `frontend/src/lib/components/dashboard/GrowthChart.svelte:692` è un template literal **dentro un
> `formatter` ECharts** (non c'è un albero di componenti dove montarlo, ed è comunque vietato);
> `frontend/src/lib/components/charts/MeasurePanel.svelte:257` è `toFixed(4)` **senza valuta**,
> sito di giudizio la cui natura monetaria non è decisa.
>
> **Consumatori misurati: zero.**

> ⚠️ **E un reperto che la non-costruzione ha evitato**: §3.3:567 dà a `SensitiveValue` il default
> `'••••'` — **quattro** punti — mentre il canale rende `'•••'`, tre. Due segnaposto di forma
> diversa sulla stessa schermata, e nessuno dei due sbagliato rispetto al proprio paragrafo.
> Costruendo il componente con il suo default avrei realizzato l'incoerenza; importando l'unica
> costante `PRIVACY_PLACEHOLDER` la questione non si pone. *Un valore ripetuto in due punti di una
> specifica è una promessa di divergenza: non è ancora un difetto solo perché non è ancora codice.*

#### Perché «costruirlo comunque» è la scelta peggiore, e non la più prudente

È lo stesso argomento che il coordinatore ha ratificato per l'enum a due valori:

> *un valore d'enum non raggiungibile correttamente è raggiungibile scorrettamente*

Un `SensitiveValue` senza chiamante legittimo non resta inerte: diventa **lo strumento con cui
qualcuno maschererà un importo che sarebbe dovuto passare dal canale**, saltando la
classificazione — e la chiamata avrà l'aria di essere corretta, perché usa la primitiva della
privacy.

> Una primitiva non documenta una possibilità: la **offre**. E ciò che è offerto viene usato, tanto
> più quanto più sembra pertinente.

La differenza con un'astrazione prematura ordinaria è che qui il costo non è il codice morto: è che
il codice morto **compete con il canale** che è l'unica cosa che rende verificabile la copertura.

**Decisione richiesta al developer**, non presa qui. Tre uscite:

| uscita | costo | conseguenza |
|---|---|---|
| **non costruirlo** finché un sito lo richiede | 0 | §3.3 resta una proposta; il passo 5 sparisce da questo round |
| costruirlo e lasciarlo senza chiamanti | ~1h | affordance disponibile prima del criterio per usarla |
| costruirlo **quando** si sblocca `GrowthChart` | 0 ora | ma il residuo è un `formatter`, non un componente: probabilmente non servirà nemmeno allora |

Raccomandazione: **la prima.** Il round resta coerente senza, e §3.3 resta scritta nell'analisi per
il giorno in cui un sito la chiederà davvero.

---

### Passo 6 — Toggle nell'header — **Stato: ✅ fatto** — 2026-09-21 — *sostituisce i grafici*

**File**: `frontend/src/lib/components/layout/Header.svelte` (+ eventuale componente dedicato).

Non è un interruttore grezzo: il developer ha rifiutato esplicitamente lo sconto. Costo reale
dichiarato: *«un bottone in fondo»*.

| vincolo | origine |
|---|---|
| posizione **header**, accanto ai controlli globali | developer |
| raggiungibile da ogni pagina **senza navigare** | requisito di latenza d'uso (Q5, metà dissolta) |
| focus da tastiera, area di tocco mobile | **convenzioni già in uso nell'header**, non domande nuove |
| etichette i18n | chiavi nuove → superficie del coordinatore, da richiedere |

**Dipendenze tecniche**: ha bisogno del passo 1 (stato) e di almeno un consumatore visibile
(passi 2-5), altrimenti è un interruttore che non accende niente.

**DoD del round**: il developer preme il bottone e **vede i valori sparire**. Dimostrazione a mano.

> **Note implementazione (2026-09-21).** Nuovo
> `frontend/src/lib/components/ui/PrivacyToggle.svelte`, innestato in
> `frontend/src/lib/components/layout/Header.svelte` **prima** di `<ThemeToggle />`.
> Runes (`$derived`), icone `Eye`/`EyeOff` a `size={20}`, `data-testid="privacy-toggle"`, classi
> copiate da `ThemeToggle`.
>
> **Gate**: `front check` al pavimento, stessi 4 file; `front build` ✅ (la generazione dei
> contratti API **non** ha modificato file tracciati — verificato con `git status`).

#### La dipendenza da te è sparita, e non perché l'abbia aggirata

Il piano dava le chiavi i18n come superficie del coordinatore. Misurato prima di chiederle:
**`ThemeToggle` non usa i18n affatto.** `aria-label` e `title` sono stringhe inglesi nel sorgente
(`frontend/src/lib/components/ui/ThemeToggle.svelte:41,46`), e `mobile-menu-toggle`
(`Header.svelte:224`) fa lo stesso con `aria-label="Toggle menu"`.

Due bottoni-icona su due. La convenzione dell'header **è** questa, quindi il toggle la segue e non
serve nessuna chiave.

⚠️ **Ma la convenzione contraddice una regola di progetto** — *«UI multilingue in EN/IT/FR/ES»*. Lo
scrivo invece di risolverlo: promuovere le tre stringhe a i18n costa una riga qui e **quattro voci
di catalogo** che sono tue. È un buco latente **nominato**, come `themeStore.ts:51`.

> Ho seguito il vicino, non la regola, e la differenza va detta. *Un difetto ereditato per coerenza
> resta un difetto: la coerenza spiega perché è lì, non perché dovrebbe restarci.*

#### Q5, la parte che restava: risolta dalle convenzioni, con una misura

| residuo Q5 | esito |
|---|---|
| focus da tastiera | `<button>` nativo: focusabile e attivabile con Invio/Spazio **senza codice** |
| stato annunciato | aggiunto `aria-pressed={hidden}` — **`ThemeToggle` non ce l'ha**, ed è l'unica cosa in cui non l'ho imitato: un toggle che non annuncia il proprio stato lascia un lettore di schermo senza la risposta alla sola domanda che conta |
| area di tocco | `p-2` + icona 20px = **36px**, sotto i 44px raccomandati, **identico ai vicini**. Allargarlo solo qui romperebbe l'allineamento della riga: va cambiato per tutta la barra o per nessuno |

#### 🔴 Il limite della dimostrazione, dichiarato prima della dimostrazione

Al click il developer vedrà sparire gli importi di **tabelle e template**, non quelli dei **grafici**.

Meccanismo, verificato e non assunto: la dipendenza reattiva si registra nel **contesto chiamante**.
`frontend/src/lib/components/ui/TweenedValue.svelte:50` chiama `{format($displayValue)}` **nel
template** ⇒ il KPI della dashboard si ridisegna al toggle. I `formatter` di ECharts invece vengono
invocati **da ECharts**, fuori da ogni contesto reattivo: producono la stringa giusta alla
*prossima* chiamata, ma un tooltip già dipinto e un asse già reso **non si aggiornano da soli**.

È §3.4 (invalidazione), che non è in questo round — e il passo 6 originale, i grafici, è vietato.

> Serve dirlo **ora**: se il developer prova il bottone su una pagina con un grafico e vede i numeri
> restare, il difetto atteso è quello, non un guasto dello store. *Una dimostrazione senza il suo
> confine dichiarato trasforma un limite noto in una sorpresa, e una sorpresa in un dubbio sul
> resto.*

---

### Passo 7 — Gate anti-regressione §1.8 — **Stato: ✅ fatto** — 2026-09-21 — *autorizzato dal developer*

Approvato nella forma delle tre righe: **enumera** i siti del sorgente che rendono denaro,
fallisce quando ne compare uno fuori dall'insieme registrato, **non giudica**.
File: `frontend/src/lib/utils/privacy/moneyRenderSites.test.ts` — 5 test, verdi.

> **Note implementazione**: due forme osservabili, misurate e non supposte.
> **Forma A** — `Intl.NumberFormat` con `style: 'currency'`: esatta, 3 occorrenze.
> **Forma B** — un template literal che interpola una valuta accanto a un token numerico:
> euristica, e il suo costo è stato pagato per intero in fase di taratura.
> Rumore misurato su tre versioni successive dello scanner: **62 → 24 → 8** candidati.
> La terza forma possibile — `toLocaleString(… currency …)` — **oggi non esiste**: zero occorrenze,
> verificato, e registrato come assenza misurata e non come forma dimenticata.

> **Note implementazione**: il registro è indicizzato **per contenuto**, non per `file:riga`.
> Una riga cambia quando qualcuno modifica il codice sopra di essa, e un gate che diventa rosso
> per una ragione che non riguarda il suo oggetto insegna ad aggiornare il registro **senza leggerlo** —
> che è lo stesso guasto del rumore, ottenuto con un altro meccanismo.
> Chiave = path + testo trovato a spazi normalizzati.

> **Note implementazione**: **il gate è stato dimostrato fallire.** Un gate mai fallito non è
> un gate verificato, è un gate non provato. Aggiunto un file mutante con entrambe le forme,
> eseguito, verificato l'errore — che nomina path, riga e forma per ciascuna —, rimosso il file,
> verificato il ritorno a 5/5. Le due righe del mutante sono state **entrambe** intercettate.

> **Note implementazione**: il gate porta il proprio **controllo positivo**.
> «Nessun sito non registrato» è vero anche quando lo scanner legge la directory sbagliata o
> quando le regex non corrispondono a nulla: l'asserzione che protegge la proprietà è esattamente
> quella il cui fallimento è silenzioso. Il test `finds the sites it is supposed to find`
> pretende che entrambe le forme trovino qualcosa, che il totale non scenda sotto il registro,
> e che un file canonico sia presente.

> **Note implementazione**: `GrowthChart.svelte:692` è registrato come **residuo noto** con la sua
> ragione, come richiesto: il gate non fallisce su di esso e non tace su di esso. Il file **non è
> stato aperto in scrittura** — I ci sta lavorando. Registrato per path e riga, leggendolo soltanto.

> **Note implementazione**: fuori dal gate **per scelta dichiarata** — `MeasurePanel:257` e
> `AssetEventPicker:179`, denaro senza marcatore di valuta. Intercettarli significa inseguire
> `toFixed` su numeri arbitrari, e *un gate che scatta su numeri arbitrari è un gate che qualcuno
> spegne*. L'esclusione è scritta nel file, non lasciata al silenzio.

> **Note implementazione**: nota aggiunta a `.github/skills/devpy-tools/testing-frontend/SKILL.md`,
> sezione `## Conventions` — path **verificato prima di scrivere**, non dedotto. Dice ciò che il
> developer ha chiesto: quando la regola cresce, le forme enumerate devono crescere con essa,
> perché un gate le cui forme sono in ritardo sulla regola **riporta verde su una domanda che ha
> smesso di fare**. Dopo il fix del punto cieco è stato aggiunto un secondo capoverso —
> *un'euristica a token è sconfitta da un sinonimo* — con la misura del rumore (`symbol` 1,
> `sign` 29) e la frase che spiega il guasto a chi non c'era: **la copertura era un a-capo,
> non un aggancio.** 538 → 548 righe, intestazioni invariate (10 `##`, 14 `###`, 2 `####`).

> **Note implementazione — 🔴 il punto cieco trovato dal coordinatore, e chiuso dentro lo stesso commit.**
> Il coordinatore ha chiesto perché `axisTickAmount` (`PerformanceChart:170`, rende a `:174`) non
> fosse nell'elenco. Risposta misurata: **la forma B ha rifiutato correttamente** — nessun token di
> valuta, cioè l'esclusione dichiarata. Ma la domanda ha scoperto altro:
>
> ```js
> :167  return symbol ? `${sign}${symbol}${compact}` : `${sign}${compact} ${currency}`;
>                       └─ PRIMARIO: nessun token di valuta ─┘  └─ RIPIEGO: agganciato ─┘
> ```
>
> Il gate aveva preso `PerformanceChart` **dal ramo di ripiego** — quello usato solo quando il
> simbolo non è noto. Il ramo primario, che rende per dollaro ed euro, non era mai stato agganciato:
> il sito risultava coperto **solo perché i due rami condividono la riga**.
> *Una copertura che dipende da dove il sorgente è andato a capo non è una copertura.*
>
> Rimedio: `CURRENCY_TOKEN` estratto in costante e allargato a `/currency|symbol/i`.
> Misurato prima di applicarlo: `symbol` ⇒ **1 hit nuovo, zero rumore**; aggiungere `sign` ⇒ **29**,
> quasi tutti percentuali (`formatSignedPercent`) e nomi di classe CSS (`signedToneClass` ×8).
> `sign` **escluso per misura**, non per intuizione.

> **Note implementazione — le cinque misure della dimostrazione**, nell'ordine in cui provano cose diverse:
>
> | | stato | atteso | esito |
> |---|---|---|---|
> | **A** | mutante col **solo** ramo primario, regex vecchia | verde = il cieco esiste | **5/5 verde** |
> | **B** | stessa mutante, regex nuova | rosso su mutante **e** sito reale | rosso su entrambi |
> | **C** | sito reale registrato, mutante ancora lì | rosso **solo** sulla mutante | esatto |
> | **D** | mutante rimossa | verde | **6/6** |
> | **E** | regex ri-ristretta a `/currency/i` | il test nuovo rosso | rosso, nominando il ramo mancante |
>
> **A e E sono le due che contano.** A prova che il difetto c'era: senza di essa, «1 hit nuovo»
> dimostrerebbe che la regex aggancia *qualcosa*, non che aggancia *quel ramo*. E prova che il test
> nuovo non è vacuo. Le altre tre confermano la meccanica.
>
> Ripristino dopo E **per copia di byte, non `git checkout`**: il file era già stagiato nella versione
> *pre-fix*, quindi Git avrebbe restituito il difetto spacciandolo per ripristino. md5 identico.

> **Note implementazione**: aggiunto il sesto test, `sees both branches of a two-branch money line`.
> È una regressione **sul gate**, non sul prodotto: pretende che entrambi i rami della riga 167
> compaiano fra gli hit, così che restringere di nuovo `CURRENCY_TOKEN` fallisca invece di tacere.

> **🔴 Limite dichiarato, e la dichiarazione precedente era incompleta.** L'esclusione «denaro senza
> marcatore di valuta» l'avevo giustificata **sul costo** — inseguire `toFixed` su numeri arbitrari.
> Regge, ma taceva la conseguenza: **una funzione il cui nome stesso dice che rende un importo
> (`axisTickAmount`), a nove righe da una che il gate prende, nello stesso file, è invisibile.**
> Il costo era l'argomento giusto; la dichiarazione era la metà comoda di esso.

### Passo 8 — Merge del target e coda post-merge — **Stato: ✅ fatto** — 2026-09-21

Merge `d59051977` (`9a6dd2015` + `7fd660846`: D allocatore PAC, I grafici performance, Risk asset
global). Un solo conflitto, `riskAnalysisHelpers.test.ts:19–44`, risolto **additivamente** — il
blocco conteneva solo import e setup di modulo, quindi nessun comportamento da arbitrare. Verificato
per aritmetica (base 62 + 7 miei + 9 di Risk = **78 misurati**) e per sopravvivenza dei simboli.

> **Note implementazione.** Dopo il merge il gate è andato **rosso a 3**, tutti e tre previsti e
> tutti e tre *veri*: due voci PAC diventate stantie perché D ha mascherato quei pannelli, e lo
> snippet `totalPnl` di `GrowthChart` riscritto da I. La coda eseguita in un commit separato dal
> merge, perché **un merge commit che modifica anche il gate non è bisecabile**.

| voce | esito |
|---|---|
| voci PAC | rimosse dal `REGISTRY` **e** dalla lista letterale di `listOf('unmasked')` |
| snippet `totalPnl` | aggiornato **in loco** al nuovo ternario di I |
| `why` della prima voce `GrowthChart` | riscritto: la condizione «mentre I riscrive il file» è finita |
| `SAFE_CALL` | de-qualificato e **ancorato**; aggiunta `formatScopedCurrencyAmount` |
| siti di Risk | **non registrabili** — vedi fuori pista 14 |
| copertura `fmtCurrency` | **1 su 8** — vedi fuori pista 15 |

Esito: `REGISTRY` **10**, hit **10**, gate **6/6**; suite privacy **126/126** su `Test Files 6`.

> **⚠️ Fuori pista.** Il coordinatore aveva previsto `12 − 2 + 1 = 11` voci. Sono **10**: la voce
> stantia di `GrowthChart` e il sito non registrato *sono lo stesso sito con il testo cambiato*, un
> aggiornamento in loco e non una rimozione più un'aggiunta. A 11 il controllo positivo
> (`hits.length >= REGISTRY.length`) sarebbe fallito, e il gate avrebbe segnalato **la riparazione**.

## §2 — Verifica

| gate | comando | soglia |
|---|---|---|
| tipi | `PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py front check` | pavimento **`3 errors and 41 warnings in 4 files`** — **meno di 3 è rosso** |
| build | `… dev.py front build` | verde |
| unit | via `test-author`, dopo ogni passo completo | ogni negativa con positiva |
| **gate §1.8** | `… npm run test:unit -- src/lib/utils/privacy/moneyRenderSites.test.ts` | 6/6 — **e dimostrato cieco prima del fix, rosso dopo**, non solo verde |

**Vietati**: E2E, suite lunghe, `dev.py mkdocs serve`, porta ≠ 6158, `--force`, staging, commit.

> ⚠️ **Il pavimento è un pavimento, non un soffitto.** *Meno* di 3 errori è rosso: significa che il
> comando non ha misurato ciò che doveva. È la stessa trappola dell'asserzione negativa di §2.3.

---

## §3 — Note d'implementazione e fuori pista

*(aggiornato dopo ogni passo, non alla fine)*

### Fuori pista 1 — La baseline attesa non esisteva ancora

Il kickoff citava passi 1-5 «liberi». Erano liberi davvero, ma per tre giorni il workstream è stato
fermo su un blocco che riguardava **un solo passo** (il gate UX, passo 9). La mia §7.2:911 lo
diceva. **Avevo la misura e non l'ho applicata a me stesso.**

### Fuori pista 2 — Due citazioni sbagliate nell'analisi, trovate dall'intenzione di usarle

`themeStore` era citato **tre volte per tre domande diverse**, e solo la prima era vera:

| citazione | domanda | esito |
|---|---|---|
| `themeStore.ts:11` | dove vive la chiave | ✅ vera |
| `themeStore:29` come `try/catch` | come si protegge | ❌ **falsa** — è una guardia `typeof`, `catch: 0` nel file |
| «come fa già `themeStore`» | quando si legge | ❌ **falsa** — nessuna lettura di modulo, tutte pigre |

Corrette nell'analisi prima del commit `d2355d341`. **Le ha trovate il tentativo di copiarle, non la
rilettura**: quattro giorni di revisioni non le avevano viste.

### Fuori pista 3 — Il verificatore aveva il difetto che cercava

Lo script di controllo dei path risolveva per `basename` ⇒ un file omonimo in un'altra cartella
sarebbe passato per buono. È la trappola del contenitore **dentro lo strumento che la cerca**.
Corretto a risoluzione per **suffisso di path** su `git ls-files`, con controllo positivo e negativo.
Un verificatore che condivide l'assunzione del documento non è un controllo: è un'eco.

### Fuori pista 4 — Il divieto sui grafici era largo, non misurato

Bloccava 2 dei 4 siti del passo 3. Misurate le hunk di I: solo `GrowthChart` collide davvero.
Passo 3 riportato a 3 siti su 4. **Un perimetro generalizzato non si sente come un errore, perché il
caso vero è dentro: costa solo ciò che esclude in più, e quello non si vede a meno che qualcuno lo
chieda.**

### Fuori pista 5 — Il piano è nato stantio, e la data di nascita non l'ha protetto

Scritto mentre arrivava la decisione del developer sul toggle. Al momento della lettura del
coordinatore portava ancora tre affermazioni del mondo precedente: il toggle fra gli **esclusi**,
*«a fine passo 5 non esiste nessun interruttore»*, e §1 con **cinque** passi invece di sei.

Il caso è **innocente**: nessuno ha sbagliato, la decisione è arrivata dopo la scrittura. L'effetto è
identico a quello di un record scritto male.

> **Un documento scritto mentre le decisioni si muovono nasce stantio.** La domanda utile non è
> *«era vero quando l'ho scritto?»* ma *«è vero adesso che qualcuno lo leggerà?»*

Più stretto della regola che avevo per i record di stato — *rileggerli nel commit che cambia lo
stato*: qui vanno riletti **quando arriva la decisione**, che può precedere il commit di ore.

### Fuori pista 6 — Una decisione in coda da me, non dal developer

Il piano elencava il gate anti-regressione di §1.8 come *«proposta non autorizzata»* in attesa del
developer. Il coordinatore ha verificato: **non gli era mai stata portata.** Stessa forma dei tre
giorni di fermo — una decisione che aspetta un intermediario e che il decisore non sa di dover
prendere.

Rimedio adottato: la proposta è stata riformulata in **tre righe** (cosa gaterebbe, costo, cosa
succede senza) invece di un rimando a §1.8. *Se per porre una domanda bisogna leggere 1 081 righe,
la domanda non parte.*

### Fuori pista 7 — Il segno è parte del valore, e l'analisi non l'aveva nominato

§3.2 dice *«decidere, prima di produrre la stringa, se restituire il valore o il segnaposto»*, ma
non dice **quale** stringa. Il codice lo ha reso concreto: a
`frontend/src/lib/utils/currency/currencyFormat.ts:36` la locale `formatted` è

```ts
`${sign}${amount < 0 ? '-' : ''}${abs}`
```

cioè segno **più** cifre. L'implementazione ovvia — mascherare `abs` e lasciare `sign` — produce
`+•••` e `-•••`, che è leggibile e sembra perfino più informativo.

> Conserverebbe **il bit più sensibile di una cifra di P&L**: se chi guarda è in guadagno o in
> perdita. Il segno non accompagna il valore, è **derivato** dal valore; mascherare le cifre e
> tenere il segno significa pubblicare la risposta alla sola domanda che un estraneo farebbe.

Scelta applicata: `maskable()` riceve la stringa **intera**, segno incluso. `+1.234,00 $ 🇺🇸 USD`
diventa `••• $ 🇺🇸 USD`, non `+••• $ 🇺🇸 USD`.

È §2.2.2 — *il segnaposto non deve dipendere dal valore reale* — applicata a un attributo che non
sembra un valore. La larghezza fissa era prevista, il segno no: nel documento l'importo era
un'entità sola, nel codice sono due concatenazioni.

### Fuori pista 8 — Ho rotto un'intestazione scrivendo i fuori pista 5 e 6

L'inserimento ha consumato la riga `## §4 — Cross-link`: i due punti elenco finali sono rimasti
attaccati a §3, dentro l'ultimo fuori pista. Trovato rileggendo la struttura dopo l'edit, non
durante.

> Un `edit` che àncora `old_str` a un separatore più l'intestazione seguente **cancella
> l'intestazione** se `new_str` non la riscrive. Il testo inserito è corretto, il documento no, e la
> diff sembra un'aggiunta pura.

Per questo il controllo delle `##`/`###` dopo ogni modifica non è una formalità di consegna: è
l'unico modo in cui un danno *strutturale* si manifesta, dato che nessun conteggio di righe cala —
la riga persa è compensata da quelle aggiunte.

### Fuori pista 9 — L'asimmetria segnalata dai test era la forma corretta, e la correzione attesa era un difetto

`test-author` ha chiuso il proprio rapporto con due osservazioni non richieste. La prima:

> `formatCurrencyAmount` (risk) **perde del tutto la valuta** quando maschera — `•••` nudo, dove
> `formatCurrencyAmountPlain` rende `••• $ 🇺🇸 USD`. Difendibile, ma è un'asimmetria fra due
> formattatori ed è ora fissata da un test.

Aveva ragione sul fatto, e il fatto era peggiore di come lo descriveva: le forme sono **tre**
formattatori e **due** shape. E l'avevo prodotta io **un passo dopo** aver scritto, al passo 5,
che due valori in due punti di una specifica sono una promessa di divergenza.

La correzione ovvia — ricostruire la stringa con `Intl.NumberFormat.formatToParts()` e sostituire
solo le parti numeriche — sembrava giusta, gratuita e conforme a D5. **Misurata sul terzo sito, è
un difetto di sicurezza.**

```
notation:'compact'  $1.2K -> ["currency:$","integer:1","decimal:.","fraction:2","compact:K"]
                    $1.2M -> [...                                   "compact:M"]
notation standard  -$1,234.50 -> ["minusSign:-","currency:$","integer:1","group:,",...]   nessun 'compact'
```

`formatAxisCurrency` (`frontend/src/lib/components/brokers/lots/LotComparisonChart.svelte:246`) usa
`notation:'compact'`. Preservare «i marcatori non numerici» vi avrebbe prodotto `$•••K` contro
`$•••M` — cioè **esattamente l'ordine di grandezza** che il docstring di `PRIVACY_PLACEHOLDER`
dichiara di non trasportare. Il suffisso compatto *è* una cifra, travestita da unità.

**Decisione: le tre implementazioni restano come sono**, e la regola che le spiega è meccanica:

| se nella stringa sorgente il marcatore di valuta è… | esito |
|---|---|
| un token **separato**, concatenato attorno all'importo (`currencyFormat.ts`) | sopravvive: `••• $ 🇺🇸 USD` |
| **fuso** con le cifre da `Intl` (`riskAnalysisHelpers`, `formatAxisCurrency`) | sostituita l'intera stringa: `•••` |

Due shape, non tre: preservare il simbolo solo dove è sicuro ne avrebbe create tre per guadagnare
uniformità su una.

> D5 — *«simbolo, bandiera e codice sopravvivono»* — è stata **osservata** su due funzioni in cui
> l'importo era già isolato in una locale, e registrata dal coordinatore come *«la forma naturale
> del codice»*. Vera lì. Il passaggio da osservazione a **contratto universale** è avvenuto nella
> mia testa, non in una decisione: applicarla al terzo sito l'avrebbe rotto.

È la stessa forma del difetto del contenitore, spostata sulle proprietà: *una regola verificata dove
è gratuita viene assunta valida dove costa, e il costo non è il lavoro — è ciò che la regola rompe.*

La seconda osservazione di `test-author` — `setPrivacyEnabled(true)` lato server lascia
`isPrivacyEnabled()` vero e `isPrivacyPersisted()` falso — è inerte (nessuna chiamata in SSR) ed è
stata fissata **com'è**, non come la volevo: *un test che asserisce la cosa più debole ma più
comoda copre di meno sembrando coprire di più.*

### Fuori pista 10 — Lo stesso ancoraggio, lo stesso confine, un guasto diverso

Appendendo §5 ho ancorato `old_str` alla **coda dell'ultima cosa che avevo scritto** — la fine del
fuori pista 9 — credendo che fosse la fine di §3. Non lo era: §3 finisce dove comincia §4, e il
testo nuovo è entrato **fra le due**. Risultato: ordine fisico §0, §1, §2, §3, **§5, §4**.

È il secondo danno su **quello stesso confine**, con **lo stesso ancoraggio**, e di forma opposta:
la fuori pista 8 ha *cancellato* l'intestazione di §4, questa l'ha *scavalcata*. Nessuno dei due
tocca il conteggio di righe; nessuno dei due appare nella diff come un errore.

> *La coda dell'ultima cosa che ho scritto non è la fine della sezione che la contiene.* Le due
> coincidono solo finché non c'è niente dopo — cioè esattamente fino alla prima volta in cui
> l'ancoraggio conta.

**Rimedio applicato, non solo annotato**: quando si appende una sezione, `old_str` e `new_str`
devono **contenere entrambi l'intestazione seguente**. Così l'ancoraggio è il confine, non il
contenuto, e il fallimento è un `old_str` non trovato — rumoroso — invece di un documento
riordinato in silenzio.

Rinumerato: Test = §4, Cross-link = §5. Verificato prima che nessun riferimento interno usasse i due
numeri (le occorrenze di «§4» e «§5» nel piano puntano all'**analisi** e al **piano di sprint**, non
a sé stesso) — rinumerare senza quel controllo avrebbe prodotto il terzo difetto sullo stesso
confine.

---

### Fuori pista 11 — 🔴 I falsi negativi di §1.8 non erano sei: erano dieci

Il gate si è giustificato **prima di girare**. Costruendo l'elenco da uno scanner invece che dalla
lista di §1.8, sono emersi **quattro siti che rendono denaro e che l'analisi non aveva contato**:

| sito | perché §1.8 non l'aveva visto |
|---|---|
| `PerformanceChart.svelte:167` (`shortMoney`, reso da `:234`) | **non chiama mai `Intl` con `style:'currency'`** — §1.8 era ancorata a quell'API, quindi era *strutturalmente cieca* a questa forma. E usa `notation:'compact'`: rivela la magnitudine, cioè esattamente ciò che il segnaposto esiste per nascondere |
| `EventCreateMiniModal.svelte:157` | §1.8 aveva elencato la **riga 73 dello stesso file** come valore d'ingresso, escluso da D7, e si era fermata lì. La riga 157 rende |
| `PacResultPanel.svelte:38` | **proprietà del workstream D (Tool/PAC)** — registrato, non corretto |
| `RebalancerResultPanel.svelte:30` | idem |

E il residuo noto non è un sito ma **due**: `GrowthChart.svelte:741` è un consumatore di
`fmtCurrency` nello stesso file, accanto a `:692`.

> **Il meccanismo è quello che conta, non il conteggio.** §1.8 aveva cercato *una forma* — la
> chiamata a `Intl` con `style:'currency'` — e aveva trovato tutti i siti che la usano. La lista
> non era incompleta per disattenzione: era **completa rispetto alla domanda che era stata posta**,
> e la domanda era più stretta della proprietà. Un elenco compilato cercando una forma non dice
> nulla sui siti che ne usano un'altra, **e ha esattamente lo stesso aspetto di un elenco esaustivo.**

Ed è la ragione per cui la nota nella skill dice che le forme sono un pavimento e non una prova:
lo scanner di oggi conosce due forme perché oggi ne esistono due, non perché due sia il numero
delle forme in cui si può rendere una cifra.

### Fuori pista 12 — L'elenco della suite ricostruito a memoria, e l'aritmetica che l'ha smentito

Eseguita «la suite privacy completa, cinque file»: **47 test**. La volta prima erano **111**.
Avevo ricostruito l'elenco dei file a memoria e sostituito `riskAnalysisHelpers.test.ts` (69 test,
quello del passo 3) con il gate nuovo (5). Il totale tornava — 11+13+2+16+5 = 47 — quindi la
somma *interna* era coerente: nulla nell'esito segnalava la sostituzione.

> A trovarlo è stato **il numero della volta prima**, non il numero di questa volta. Un risultato
> coerente con sé stesso non dice nulla sul proprio perimetro; solo il confronto con una misura
> precedente rivela che il perimetro è cambiato. È lo stesso di `porcelain`: un output plausibile
> che non dichiara su cosa è stato calcolato.

Eseguiti tutti e sei: **116 = 111 + 5**, esatto.

### Fuori pista 13 — 🔴 Il controllo positivo non vede una forma che aggancia **meno** del dovuto

Il gate era stato consegnato con un controllo positivo costruito apposta contro l'asserzione
negativa: pretende `hits >= registro`, forma A ≠ ∅, forma B ≠ ∅, e un file canonico presente.

**Tutte e quattro reggevano mentre la forma B mancava il ramo primario di `shortMoney`.**

> «Entrambe le forme trovano qualcosa» è vero anche quando una ne trova **meno del dovuto**.
> Il controllo verifica che lo scanner *stia guardando*; non può verificare che stia *vedendo tutto*,
> e le due proprietà hanno **lo stesso esito osservabile**. Un conteggio non nullo ha la stessa
> forma di un conteggio corretto.

È l'undicesimo contenitore della serie — `0`, la riga-directory di `porcelain`, il `.svelte.ts`
senza `$state` — e stavolta è **dentro la cosa costruita per accorgersene**. La contromisura non è
un controllo positivo migliore: è che un controllo di presenza non può sostituire un caso noto.
Il sesto test fissa **due snippet nominati**, non un conteggio.

E il difetto non l'ha trovato una misura: l'ha trovato una **domanda su un altro sito**. Il
coordinatore chiedeva di `axisTickAmount`, che si è rivelato un'esclusione corretta; la risposta
ha attraversato `shortMoney` e lì c'era il guasto. *Una verifica che non trova ciò che cercava può
trovare ciò che nessuno cercava, e solo se la si esegue davvero invece di argomentarla.*

### Fuori pista 14 — 🔴 Il registro non può contenere un sito che lo scanner non vede

La voce 3 della coda chiedeva di registrare sei siti di Risk più `formatScopedCurrencyAmount`.
**Non è eseguibile**, e non per una scelta: per la struttura del test di marcio.

```ts
const stale = REGISTRY.filter((s) => !found.has(key(s)));   // found è costruito da hits
```

Una voce che lo scanner non produce è **immediatamente stantia**. Misurato con una sonda
temporanea su `L4Replay.svelte`: **2 rossi** — il marcio *e* il controllo positivo, perché le voci
diventano 11 contro 10 hit. File ripristinato per copia di byte, md5 identico, gate di nuovo 6/6.

> **Il registro è indicizzato sul contenuto, ma popolato dallo scanner.** Può ospitare solo ciò che
> il gate già vede — quindi serve a impedire che un sito *noto* cambi in silenzio, **non** a
> ricordare un sito invisibile. I due lavori si assomigliano e hanno bisogno di due posti diversi:
> il secondo è questo piano.

Siti di Risk, triati con la domanda **quale parte è cambiata, e la ragione parla di quella parte?**

| sito | verdetto | perché non è un hit |
|---|---|---|
| tre di `l4/` | `not-money` | rendono conteggi e percentuali, non importi |
| tre condizionali | coperti | delegano a `formatCurrencyAmount`, mascherata a `:160` |
| `formatScopedCurrencyAmount` | coperto | delega alla stessa, dopo due guardie che rendono `—` |

Le ultime quattro righe sono ora **in `SAFE_CALL`**, che è il posto giusto: dichiarano una promessa
verificabile, invece di chiedere al registro di ricordare un'assenza.

### Fuori pista 15 — 🔴 Il gate vede **1** degli **8** consumatori di `fmtCurrency`

Misurato su `GrowthChart.svelte` fuso (2246 righe): definizione `:1834`, consumatori a
`:1893, :1895, :1896, :1899, :1915, :1927, :1943, :1958`. **Il gate ne aggancia uno solo**, `:1899`,
l'unico che sia una forma B completa. Gli altri sette compongono l'importo senza marcatore di valuta
sulla stessa riga.

> **Un rosso piccolo su un file che contiene otto siti di denaro è più allarmante di uno grande.**
> La dimensione del rosso misura quanto il gate *vede*, non quanto il file *espone*, e le due
> quantità divergono esattamente dove il file è peggiore. Un file con un solo sito visibile e sette
> invisibili produce lo stesso segnale di un file quasi pulito.

La voce residua resta una riga sola da mascherare — la definizione — ma il numero che la accompagna
nel registro non va letto come copertura.

### Fuori pista 16 — Due difetti di misura miei, entrambi presi da una contromisura e non da un sospetto

**Path fantasma.** `chartCoreHelpers.test.ts` l'ho cercato sotto `utils/charts/`; sta sotto
`components/charts/`. `vitest` non ha stampato né `Test Files` né `Tests`, e la regola «N path
dentro ⇒ `Test Files` dice N» l'ha preso al primo colpo. Con un path valido accanto sarebbe
**sparito in silenzio, exit 0**.

**Stato altrui scaduto.** Ho riportato l'indice del merge come «211 M · 199 A · 30 R · 26 D» mentre
il developer aveva già creato `d59051977`, che l'aveva consumato. Ero FROZEN e non avevo mosso
nulla — ed è il punto: *l'immobilità garantisce che non cambi io, non che non cambi il mondo*.
Uno stato altrui va **riletto all'uso**, non trasportato dal momento in cui lo si è osservato.

## §4 — Test

### Unit test — 2026-09-21 — via `test-author`

| file | test |
|---|---|
| `frontend/src/lib/utils/privacy/maskable.test.ts` | 11 |
| `frontend/src/lib/stores/app/privacyStore.test.ts` | 13 |
| `frontend/src/lib/stores/app/privacyStoreSsr.test.ts` | 2 |
| `frontend/src/lib/utils/currency/currencyFormat.test.ts` | 14 → **16** *(riparati per D8)* |
| `frontend/src/lib/components/risk/riskAnalysisHelpers.test.ts` | 62 → **69** |
| `frontend/src/lib/utils/privacy/moneyRenderSites.test.ts` | **6** *(gate §1.8, passo 7)* |

`cd frontend && npm run test:unit -- <i sei file>` ⇒ **117 passed**. `front check` dopo
l'aggiunta: **`3 errors and 41 warnings in 4 files`**, il pavimento — i file di test non
introducono errori di tipo.

> 🔴 **Questa tabella è stata trovata stantia al passo 7**, e va detto come: diceva `14` e
> `109 passed`, cioè i numeri di *prima* della riparazione D8 — che era stata fatta, registrata al
> passo 2, e mai riportata qui. Il record non si era rotto: **si era fermato**, e una tabella ferma
> ha la stessa forma di una tabella aggiornata. È lo stesso guasto dell'elenco-suite di Fuori
> pista 12, un piano più in là: ciò che non viene ricontato resta scritto.

**La prova che il verde è reale non è il conteggio.** `test-author` ha mutato l'implementazione
undici volte e verificato che ogni proprietà diventasse rossa, ripristinando poi i sorgenti
(md5 identici). Fra le mutanti uccise: segnaposto di larghezza proporzionale all'importo (6 test),
`sensitivity` omessa che fallisce **aperta** (8), maschera spostata **prima** dei due `return '—'`
(esattamente i 2 test di assenza), scrittura fallita dichiarata persistita (1). Tre ordini
rimescolati (`--sequence.shuffle`, tre semi) ⇒ 109/109, quindi lo stato di modulo condiviso non
passa fra test.

> Un conteggio di test verdi misura che il codice non esplode. Una mutante che **non** diventa rossa
> misura che il test non guardava. Sono due domande diverse e solo la seconda difende una proprietà
> di sicurezza.

### Non testato, e dichiarato

| proprietà | perché non è coperta |
|---|---|
| **reattività** — il toggle ridipinge davvero le superfici | un test node chiama la funzione e ottiene un valore; non può osservare se una dipendenza è stata *registrata*. Serve un test di componente o E2E, fuori dal perimetro concesso |
| invalidazione dei `formatter` ECharts (§3.4) | stessa ragione, ed è il limite già dichiarato al passo 6 |
| `PrivacyToggle.svelte` | componente, non coperto da questo giro |
| cifre raggruppate per locale | l'atteso è costruito con la stessa `toLocaleString`, quindi il test fissa composizione e ordine, **non** il raggruppamento: un letterale `1,234.50` diventerebbe rosso su un runner `de-DE`. Gli attesi *mascherati* sono letterali esatti, perché un segnaposto non ha locale |
| **il gate stesso** — che intercetti una forma che non conosce | per costruzione: lo scanner enumera **due** forme misurate. Un sito che compone l'importo su più istruzioni, o che lo rende senza marcatore di valuta, non è visto. Dichiarato nel file e nella skill, **non** lasciato implicito |

---

## §5 — Cross-link

- **Analisi**: [`analysis-phase00PrivacyGlobal.md`](./analysis-phase00PrivacyGlobal.md) — contratto §2,
  primitive §3, store §4, trappole §5, domande aperte §6, ordine §7.2, falsi negativi §1.8
- **Fonte**: [`../09_feedbackJobs/06_piano_sprint.md`](../09_feedbackJobs/06_piano_sprint.md) §5 U2 (riga 311)
